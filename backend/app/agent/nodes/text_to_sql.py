import logging

from app.agent.state import AgentState
from app.agent.text_to_sql.executor import ReadonlySqlExecutor
from app.agent.text_to_sql.generator import TextToSqlGenerator
from app.agent.text_to_sql.normalizer import ResultNormalizer
from app.agent.text_to_sql.schema_provider import HeatTreatmentSchemaProvider
from app.agent.text_to_sql.validator import SqlValidator


logger = logging.getLogger(__name__)


class TextToSqlNode:
    def __init__(
        self,
        schema_provider: HeatTreatmentSchemaProvider,
        generator: TextToSqlGenerator,
        validator: SqlValidator,
        executor: ReadonlySqlExecutor,
        normalizer: ResultNormalizer,
    ):
        self._schema_provider = schema_provider
        self._generator = generator
        self._validator = validator
        self._executor = executor
        self._normalizer = normalizer

    def __call__(self, state: AgentState) -> AgentState:
        schema_package = self._schema_provider.load()
        try:
            generation = self._generator.generate(state["user_query"], schema_package)
        except Exception:
            logger.exception("Text-to-SQL generation failed")
            normalized = self._normalizer.normalize_generation_error(
                schema_version=schema_package.schema_version,
                error_code="text_to_sql_generation_error",
                error_message="Text-to-SQL 生成失败。",
            )
            return self._with_result(state, normalized.model_dump())

        validation = self._validator.validate(generation.sql, schema_package)
        if validation.status != "validated":
            normalized = self._normalizer.normalize_validation_error(
                generation,
                validation,
                schema_version=schema_package.schema_version,
            )
            return self._with_result(state, normalized.model_dump())

        execution = self._executor.execute(validation.validated_sql or generation.sql)
        normalized = self._normalizer.normalize_success(
            generation,
            validation,
            execution,
            schema_version=schema_package.schema_version,
        )
        return self._with_result(state, normalized.model_dump())

    @staticmethod
    def _with_result(state: AgentState, result: dict) -> AgentState:
        next_state: AgentState = {
            **state,
            "text_to_sql_status": result.get("status"),
            "tool_result": result,
        }
        error = result.get("error")
        if error:
            next_state["error_code"] = error.get("code")
            next_state["error_message"] = error.get("message")
        return next_state
