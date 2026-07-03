import json
import re

from langchain_core.language_models.chat_models import BaseChatModel

from app.agent.text_to_sql.models import (
    HeatTreatmentSchemaPackage,
    TextToSqlGeneration,
)


PROMPT_VERSION = "heat-treatment-text-to-sql-v1"


class TextToSqlGenerator:
    def __init__(self, chat_model: BaseChatModel, max_limit: int):
        self._chat_model = chat_model.with_structured_output(TextToSqlGeneration)
        self._fallback_model = chat_model
        self._max_limit = max_limit

    def generate(
        self,
        user_query: str,
        schema_package: HeatTreatmentSchemaPackage,
    ) -> TextToSqlGeneration:
        prompt = _build_prompt(user_query, schema_package, self._max_limit)
        try:
            result = self._chat_model.invoke(prompt)
            if isinstance(result, TextToSqlGeneration):
                return result
            return TextToSqlGeneration.model_validate(result)
        except Exception:
            response = self._fallback_model.invoke(
                prompt
                + "\n\n必须只返回 JSON 对象，字段为 sql, used_tables, query_intent, assumptions。不要使用 Markdown 代码块。"
            )
            return TextToSqlGeneration.model_validate(
                _normalize_generation_payload(
                    _extract_json_object(str(response.content))
                )
            )


def _build_prompt(
    user_query: str,
    schema_package: HeatTreatmentSchemaPackage,
    max_limit: int,
) -> str:
    return f"""
你是 MES 热处理领域 Text-to-SQL 生成器。

只允许基于下面的固定 Schema 生成 MySQL SELECT 查询。你只生成候选 SQL，不执行 SQL。

硬性约束：
- 只能生成单条 SELECT。
- 不得生成 INSERT、UPDATE、DELETE、DDL、存储过程、变量赋值、多语句。
- 只能访问 allowed_columns 中列出的表和字段。
- 不得访问 forbidden_columns 中的字段。
- 必须添加 LIMIT，LIMIT 不得超过 {max_limit}。
- 常规统计应排除 status = 'CANCELLED'。
- 完成类问题应使用 finished_time IS NOT NULL，并优先使用 status IN ('FINISHED','TRANSFERRED','ENDED')。
- 不存在的字段不要臆造；如果问题依赖当前 Schema 没有的字段，仍返回一个可安全执行的近似查询，并在 assumptions 说明限制。
- 输出 SQL 不要以分号结尾。

Schema Package:
{schema_package.model_dump_json(indent=2)}

用户问题：
{user_query}
""".strip()


def _extract_json_object(content: str) -> dict:
    cleaned = re.sub(r"<think>.*?</think>", "", content, flags=re.S)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("Text-to-SQL response did not contain a JSON object.")
    return json.loads(cleaned[start : end + 1])


def _normalize_generation_payload(payload: dict) -> dict:
    for field in ("used_tables", "assumptions"):
        value = payload.get(field)
        if value is None:
            payload[field] = []
        elif isinstance(value, str):
            payload[field] = [value]
    return payload
