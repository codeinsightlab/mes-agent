from sqlglot import exp, parse, parse_one
from sqlglot.errors import ParseError

from app.agent.text_to_sql.models import HeatTreatmentSchemaPackage, SqlValidationResult


FORBIDDEN_EXPRESSIONS = (
    exp.Delete,
    exp.Drop,
    exp.Insert,
    exp.Update,
    exp.Create,
    exp.Alter,
    exp.Command,
)


class SqlValidator:
    def __init__(self, max_limit: int):
        self._max_limit = max_limit

    def validate(
        self,
        sql: str,
        schema_package: HeatTreatmentSchemaPackage,
    ) -> SqlValidationResult:
        generated_sql = sql.strip()
        if not generated_sql:
            return self._error(generated_sql, "empty_sql", "SQL 不能为空。")

        try:
            statements = parse(generated_sql, read="mysql")
            if len(statements) != 1:
                return self._error(generated_sql, "multiple_statements", "只允许单条 SQL。")
            expression = parse_one(generated_sql, read="mysql")
        except ParseError as exc:
            return self._error(generated_sql, "parse_error", f"SQL 解析失败：{exc}.")

        if not isinstance(expression, exp.Select):
            return self._error(generated_sql, "non_select_sql", "只允许 SELECT 查询。")
        if any(expression.find(forbidden) for forbidden in FORBIDDEN_EXPRESSIONS):
            return self._error(generated_sql, "forbidden_statement", "禁止执行写入、DDL 或命令类 SQL。")

        allowed_tables = schema_package.allowed_table_names()
        used_tables = sorted(
            {
                table.name
                for table in expression.find_all(exp.Table)
                if table.name
            }
        )
        if not used_tables:
            return self._error(generated_sql, "missing_table", "SQL 必须访问白名单表。")
        forbidden_tables = [table for table in used_tables if table not in allowed_tables]
        if forbidden_tables:
            return self._error(
                generated_sql,
                "forbidden_table",
                f"SQL 访问了非白名单表：{', '.join(forbidden_tables)}。",
            )

        if any(isinstance(projection, exp.Star) for projection in expression.expressions):
            return self._error(generated_sql, "wildcard_column", "禁止使用 SELECT *。")

        forbidden_columns = schema_package.forbidden_column_names()
        allowed_columns_by_table = schema_package.allowed_column_names()
        table_aliases = _table_aliases(expression)
        projection_aliases = _projection_aliases(expression)
        for column in expression.find_all(exp.Column):
            column_name = column.name
            if column_name in forbidden_columns:
                return self._error(
                    generated_sql,
                    "forbidden_column",
                    f"SQL 访问了禁止字段：{column_name}。",
                )
            table_name = _resolve_table_name(column.table, table_aliases)
            if table_name:
                allowed_columns = allowed_columns_by_table.get(table_name)
                if allowed_columns is not None and column_name not in allowed_columns:
                    return self._error(
                        generated_sql,
                        "unknown_column",
                        f"字段 {table_name}.{column_name} 不在开放 Schema 内。",
                    )
            elif (
                column_name not in projection_aliases
                and not _column_allowed_in_any_table(column_name, allowed_columns_by_table)
            ):
                return self._error(
                    generated_sql,
                    "unknown_column",
                    f"字段 {column_name} 不在开放 Schema 内。",
                )

        if _is_unbounded_row_scan(expression):
            return self._error(
                generated_sql,
                "unbounded_scan",
                "禁止无条件明细大表扫描，请添加 WHERE、聚合或分组条件。",
            )

        expression = self._enforce_limit(expression)
        return SqlValidationResult(
            generated_sql=generated_sql,
            validated_sql=expression.sql(dialect="mysql"),
            used_tables=used_tables,
            status="validated",
        )

    def _enforce_limit(self, expression: exp.Select) -> exp.Select:
        limit = expression.args.get("limit")
        if limit is None:
            return expression.limit(self._max_limit, copy=True)

        current_limit = _literal_limit_value(limit)
        if current_limit is None or current_limit > self._max_limit:
            return expression.limit(self._max_limit, copy=True)
        return expression

    @staticmethod
    def _error(sql: str, code: str, message: str) -> SqlValidationResult:
        return SqlValidationResult(
            generated_sql=sql,
            status="rejected",
            error_code=code,
            error_message=message,
        )


def _table_aliases(expression: exp.Expression) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for table in expression.find_all(exp.Table):
        if table.name:
            aliases[table.name] = table.name
        alias = table.alias
        if alias:
            aliases[alias] = table.name
    return aliases


def _projection_aliases(expression: exp.Select) -> set[str]:
    aliases: set[str] = set()
    for projection in expression.expressions:
        alias = projection.alias
        if alias:
            aliases.add(alias)
    return aliases


def _resolve_table_name(table: str, aliases: dict[str, str]) -> str | None:
    if not table:
        return None
    return aliases.get(table, table)


def _column_allowed_in_any_table(
    column_name: str,
    allowed_columns_by_table: dict[str, set[str]],
) -> bool:
    return any(column_name in columns for columns in allowed_columns_by_table.values())


def _literal_limit_value(limit: exp.Limit) -> int | None:
    expression = limit.expression
    if isinstance(expression, exp.Literal) and expression.is_int:
        return int(expression.this)
    return None


def _is_unbounded_row_scan(expression: exp.Select) -> bool:
    has_where = expression.args.get("where") is not None
    has_group = expression.args.get("group") is not None
    has_aggregate = any(expression.find_all(exp.AggFunc))
    return not has_where and not has_group and not has_aggregate
