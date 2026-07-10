import textwrap

import pytest

from app.agent.capability.loader import CapabilityLoader
from app.agent.capability.validator import (
    CapabilityCatalogLoadError,
    CapabilityCatalogValidationError,
    CapabilityNotExecutableError,
)


def write_catalog(tmp_path, body: str):
    definitions_dir = tmp_path / "definitions"
    definitions_dir.mkdir()
    catalog_path = definitions_dir / "test.yaml"
    catalog_path.write_text(textwrap.dedent(body), encoding="utf-8")
    return definitions_dir


def test_runtime_loads_heat_current_stage_from_default_catalog():
    registry = CapabilityLoader().load()

    capability = registry.require("heat_current_stage")

    assert capability.name == "heat_current_stage"
    assert capability.domain == "heat_treatment"
    assert capability.status == "enabled"
    assert capability.catalog_version == "v2"
    assert capability.execution_type == "tool"
    assert capability.executor == "heat_current_stage"
    assert capability.required_entities == ["record_no"]
    assert "capability_name" in capability.trace_fields
    assert capability.legacy_source == "old python constant"


def test_loader_fails_when_required_field_is_missing(tmp_path):
    definitions_dir = write_catalog(
        tmp_path,
        """
        capabilities:
          - name: broken_capability
            domain: heat_treatment
            description: missing execution_type
            intent: []
            status: enabled
            executor: heat_current_stage
            input_schema:
              required: []
            output_schema:
              required: []
        """,
    )

    with pytest.raises(CapabilityCatalogLoadError, match="execution_type"):
        CapabilityLoader(definitions_dir, executor_names={"heat_current_stage"}).load()


def test_loader_fails_when_executor_does_not_exist(tmp_path):
    definitions_dir = write_catalog(
        tmp_path,
        """
        capabilities:
          - name: unknown_executor_capability
            domain: heat_treatment
            description: invalid executor
            intent: []
            status: enabled
            execution_type: tool
            executor: unknown_tool
            input_schema:
              required:
                - record_no
            output_schema:
              required:
                - found
        """,
    )

    with pytest.raises(CapabilityCatalogValidationError, match="unknown executor"):
        CapabilityLoader(definitions_dir, executor_names={"heat_current_stage"}).load()


def test_planned_capability_loads_but_is_not_executable(tmp_path):
    definitions_dir = write_catalog(
        tmp_path,
        """
        capabilities:
          - name: planned_heat_capability
            domain: heat_treatment
            description: planned capability
            intent: []
            status: planned
            execution_type: tool
            executor: heat_current_stage
            input_schema:
              required:
                - record_no
            output_schema:
              required:
                - found
        """,
    )
    registry = CapabilityLoader(definitions_dir, executor_names={"heat_current_stage"}).load()

    assert registry.require("planned_heat_capability").status == "planned"
    with pytest.raises(CapabilityNotExecutableError, match="planned"):
        registry.require_executable("planned_heat_capability")


def test_runtime_registry_can_query_heat_current_stage():
    registry = CapabilityLoader().load()

    assert "heat_current_stage" in registry.names()
    assert "heat_completion_count_monthly" in registry.names()
    assert "heat_device_trace" in registry.names()
    assert "work_order_status" in registry.names()
    assert "inspection_status" in registry.names()
    assert registry.get("heat_current_stage").executor == "heat_current_stage"
    assert registry.get("heat_device_trace").status == "planned"
    assert registry.require_executable("heat_current_stage").name == "heat_current_stage"
    assert registry.require_executable("heat_completion_count_monthly").execution_type == "readonly_sql"
    with pytest.raises(CapabilityNotExecutableError, match="planned"):
        registry.require_executable("work_order_status")
