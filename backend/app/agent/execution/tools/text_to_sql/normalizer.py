from app.agent.execution.tools.text_to_sql.models import (
    NormalizedTextToSqlResult,
    SqlExecutionResult,
    SqlValidationResult,
    TextToSqlGeneration,
)


class ResultNormalizer:
    def normalize_success(
        self,
        generation: TextToSqlGeneration,
        validation: SqlValidationResult,
        execution: SqlExecutionResult,
        schema_version: str,
    ) -> NormalizedTextToSqlResult:
        return NormalizedTextToSqlResult(
            status=execution.status,
            generated_sql=generation.sql,
            validated_sql=validation.validated_sql,
            used_tables=validation.used_tables or generation.used_tables,
            columns=execution.columns,
            rows=execution.rows,
            row_count=execution.row_count,
            duration_ms=execution.duration_ms,
            schema_version=schema_version,
            query_intent=generation.query_intent,
            assumptions=generation.assumptions,
            error=_error(execution.error_code, execution.error_message),
        )

    def normalize_validation_error(
        self,
        generation: TextToSqlGeneration,
        validation: SqlValidationResult,
        schema_version: str,
    ) -> NormalizedTextToSqlResult:
        return NormalizedTextToSqlResult(
            status="rejected",
            generated_sql=generation.sql,
            validated_sql=None,
            used_tables=generation.used_tables,
            schema_version=schema_version,
            query_intent=generation.query_intent,
            assumptions=generation.assumptions,
            error=_error(validation.error_code, validation.error_message),
        )

    def normalize_generation_error(
        self,
        schema_version: str,
        error_code: str,
        error_message: str,
    ) -> NormalizedTextToSqlResult:
        return NormalizedTextToSqlResult(
            status="failed",
            schema_version=schema_version,
            error={"code": error_code, "message": error_message},
        )


def _error(code: str | None, message: str | None) -> dict[str, str] | None:
    if not code and not message:
        return None
    return {
        "code": code or "unknown_error",
        "message": message or "Text-to-SQL 执行失败。",
    }
