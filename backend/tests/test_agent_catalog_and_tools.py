import pytest

from app.agent.catalog.heat_treatment import CAPABILITY_BY_NAME, HEAT_STATUS_NAMES
from app.agent.exceptions import ToolExecutionError
from app.agent.tools.registry import ToolRegistry
from tests.heat_tool_test_utils import build_heat_treatment_test_registry


def test_heat_treatment_catalog_contains_enabled_planned_and_blocked_capabilities():
    assert CAPABILITY_BY_NAME["heat_current_stage"].status == "enabled"
    assert CAPABILITY_BY_NAME["heat_equipment_assignment"].status == "planned"
    assert CAPABILITY_BY_NAME["heat_batch_products"].status == "planned"
    assert CAPABILITY_BY_NAME["heat_param_submitted"].status == "blocked"
    assert HEAT_STATUS_NAMES["FINISHED"] == "已完成"


def test_registry_executes_enabled_tool_and_returns_status_mapping():
    result = build_heat_treatment_test_registry().execute(
        "heat_current_stage",
        {"record_no": "HT20260603-007"},
    )

    assert result["found"] is True
    assert result["record_no"] == "HT20260603-007"
    assert result["status"] == "RUNNING"
    assert result["status_name"] == "进行中"
    assert "_trace" not in result


def test_registry_returns_not_found_without_default_status():
    result = build_heat_treatment_test_registry().execute(
        "heat_current_stage",
        {"record_no": "NOT_EXIST_HT001"},
    )

    assert result == {
        "found": False,
        "record_no": "NOT_EXIST_HT001",
        "status": None,
        "status_name": None,
    }


def test_registry_rejects_blocked_capability():
    with pytest.raises(ToolExecutionError):
        ToolRegistry().execute(
            "heat_param_submitted",
            {"record_no": "TRACE-HTR-K2-T-FG-001"},
        )


def test_registry_rejects_planned_mock_capability():
    with pytest.raises(ToolExecutionError):
        ToolRegistry().execute(
            "heat_equipment_assignment",
            {"record_no": "TRACE-HTR-K2-T-FG-001"},
        )


def test_registry_argument_schema_requires_record_identifier():
    schema = ToolRegistry().argument_schema("heat_current_stage")

    with pytest.raises(ValueError):
        schema()
