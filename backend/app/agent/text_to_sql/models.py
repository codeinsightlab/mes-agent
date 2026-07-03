from typing import Any

from pydantic import BaseModel, Field


class SchemaColumn(BaseModel):
    name: str
    description: str
    data_type: str
    allowed: bool = True


class SchemaTable(BaseModel):
    name: str
    description: str
    primary_key: str
    columns: list[SchemaColumn]


class HeatTreatmentSchemaPackage(BaseModel):
    schema_version: str
    tables: list[SchemaTable]
    relationships: list[str]
    status_semantics: dict[str, str]
    business_rules: list[str]
    allowed_columns: dict[str, list[str]]
    forbidden_columns: dict[str, list[str]]
    examples: list[str]

    def allowed_table_names(self) -> set[str]:
        return {table.name for table in self.tables}

    def allowed_column_names(self) -> dict[str, set[str]]:
        return {
            table_name: set(columns)
            for table_name, columns in self.allowed_columns.items()
        }

    def forbidden_column_names(self) -> set[str]:
        names: set[str] = set()
        for columns in self.forbidden_columns.values():
            names.update(columns)
        return names


class TextToSqlGeneration(BaseModel):
    sql: str
    used_tables: list[str] = Field(default_factory=list)
    query_intent: str
    assumptions: list[str] = Field(default_factory=list)


class SqlValidationResult(BaseModel):
    generated_sql: str
    validated_sql: str | None = None
    used_tables: list[str] = Field(default_factory=list)
    status: str
    error_code: str | None = None
    error_message: str | None = None


class SqlExecutionResult(BaseModel):
    status: str
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0
    duration_ms: int = 0
    error_code: str | None = None
    error_message: str | None = None


class NormalizedTextToSqlResult(BaseModel):
    route: str = "text_to_sql"
    status: str
    generated_sql: str | None = None
    validated_sql: str | None = None
    used_tables: list[str] = Field(default_factory=list)
    columns: list[str] = Field(default_factory=list)
    rows: list[dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0
    duration_ms: int = 0
    error: dict[str, str] | None = None
    schema_version: str
    query_intent: str | None = None
    assumptions: list[str] = Field(default_factory=list)
