import pytest

from app.agent.catalog.heat_treatment import CAPABILITY_BY_NAME, HEAT_STATUS_NAMES
from app.agent.exceptions import ToolExecutionError
from app.agent.tools.registry import ToolRegistry


def test_heat_treatment_catalog_contains_enabled_and_blocked_capabilities():
    assert CAPABILITY_BY_NAME["heat_current_stage"].status == "enabled"
    assert CAPABILITY_BY_NAME["heat_equipment_assignment"].status == "enabled"
    assert CAPABILITY_BY_NAME["heat_batch_products"].status == "enabled"
    assert CAPABILITY_BY_NAME["heat_param_submitted"].status == "blocked"
    assert HEAT_STATUS_NAMES["FINISHED"] == "已完成"


def test_registry_executes_enabled_tool_and_returns_status_mapping():
    result = ToolRegistry().execute(
        "heat_current_stage",
        {"record_no": "TRACE-HTR-K2-T-FG-001"},
    )

    assert result["found"] is True
    assert result["status"] == "FINISHED"
    assert result["status_name"] == "已完成"


def test_registry_rejects_blocked_capability():
    with pytest.raises(ToolExecutionError):
        ToolRegistry().execute(
            "heat_param_submitted",
            {"record_no": "TRACE-HTR-K2-T-FG-001"},
        )


def test_registry_argument_schema_requires_record_identifier():
    schema = ToolRegistry().argument_schema("heat_current_stage")

    with pytest.raises(ValueError):
        schema()
