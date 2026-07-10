from app.agent.execution.tools.text_to_sql.schema_provider import HeatTreatmentSchemaProvider
from app.agent.execution.tools.text_to_sql.validator import SqlValidator


def validate(sql: str):
    schema = HeatTreatmentSchemaProvider().load()
    return SqlValidator(max_limit=100).validate(sql, schema)


def test_validator_accepts_safe_aggregate_and_adds_limit():
    result = validate(
        """
        SELECT equipment_name, COUNT(*) AS batch_count
        FROM mes_heat_treatment_record
        WHERE status IN ('FINISHED', 'TRANSFERRED', 'ENDED')
          AND finished_time >= DATE_FORMAT(CURDATE(), '%Y-%m-01')
        GROUP BY equipment_name
        """
    )

    assert result.status == "validated"
    assert result.validated_sql is not None
    assert "LIMIT 100" in result.validated_sql
    assert result.used_tables == ["mes_heat_treatment_record"]


def test_validator_rejects_non_select_sql():
    result = validate("DELETE FROM mes_heat_treatment_record WHERE id = 1")

    assert result.status == "rejected"
    assert result.error_code == "non_select_sql"


def test_validator_rejects_multiple_statements():
    result = validate("SELECT id FROM mes_heat_treatment_record LIMIT 1; SELECT 1")

    assert result.status == "rejected"
    assert result.error_code == "multiple_statements"


def test_validator_rejects_forbidden_table():
    result = validate("SELECT id FROM agent_conversation LIMIT 10")

    assert result.status == "rejected"
    assert result.error_code == "forbidden_table"


def test_validator_rejects_forbidden_column():
    result = validate("SELECT created_by FROM mes_heat_treatment_record WHERE id = 1 LIMIT 10")

    assert result.status == "rejected"
    assert result.error_code == "forbidden_column"


def test_validator_rewrites_oversized_limit():
    result = validate(
        """
        SELECT record_no
        FROM mes_heat_treatment_record
        WHERE status = 'FINISHED'
        LIMIT 10000
        """
    )

    assert result.status == "validated"
    assert result.validated_sql is not None
    assert "LIMIT 100" in result.validated_sql


def test_validator_rejects_unbounded_detail_scan():
    result = validate("SELECT record_no FROM mes_heat_treatment_record LIMIT 10")

    assert result.status == "rejected"
    assert result.error_code == "unbounded_scan"


def test_validator_rejects_select_star():
    result = validate("SELECT * FROM mes_heat_treatment_record WHERE id = 1 LIMIT 10")

    assert result.status == "rejected"
    assert result.error_code == "wildcard_column"
