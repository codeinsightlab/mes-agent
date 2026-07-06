import logging
from typing import cast

from pydantic import BaseModel

from app.agent.state import AgentState
from app.agent.text_to_sql.executor import ReadonlySqlExecutor
from app.agent.text_to_sql.generator import TextToSqlGenerator
from app.agent.text_to_sql.normalizer import ResultNormalizer
from app.agent.text_to_sql.schema_provider import HeatTreatmentSchemaProvider
from app.agent.text_to_sql.validator import SqlValidator
from app.core.type_defs import JsonObject


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
            return self._with_result(state, _model_json_object(normalized))

        validation = self._validator.validate(generation.sql, schema_package)
        if validation.status != "validated":
            normalized = self._normalizer.normalize_validation_error(
                generation,
                validation,
                schema_version=schema_package.schema_version,
            )
            return self._with_result(state, _model_json_object(normalized))

        execution = self._executor.execute(validation.validated_sql or generation.sql)
        normalized = self._normalizer.normalize_success(
            generation,
            validation,
            execution,
            schema_version=schema_package.schema_version,
        )
        return self._with_result(state, _model_json_object(normalized))

    @staticmethod
    def _with_result(state: AgentState, result: JsonObject) -> AgentState:
        status = result.get("status")
        next_state: AgentState = {
            **state,
            "text_to_sql_status": status if isinstance(status, str) else None,
            "tool_result": result,
        }
        error = result.get("error")
        if error:
            error_payload = error if isinstance(error, dict) else {}
            code = error_payload.get("code")
            message = error_payload.get("message")
            next_state["error_code"] = code if isinstance(code, str) else None
            next_state["error_message"] = message if isinstance(message, str) else None
        return next_state


def _model_json_object(model: BaseModel) -> JsonObject:
    return cast(JsonObject, model.model_dump(mode="json"))
