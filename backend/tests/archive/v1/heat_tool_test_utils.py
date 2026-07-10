from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from app.agent.execution.tools.registry import ToolRegistry
from app.agent.execution.tools.repository.heat_treatment_repository import HeatTreatmentRepository


def build_heat_treatment_test_repository() -> HeatTreatmentRepository:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE TABLE mes_heat_treatment_record (
                    record_no TEXT PRIMARY KEY,
                    status TEXT
                )
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO mes_heat_treatment_record (record_no, status)
                VALUES
                    ('TRACE-HTR-K2-T-FG-001', 'FINISHED'),
                    ('HT001', 'FINISHED'),
                    ('HT20260603-007', 'RUNNING')
                """
            )
        )
    return HeatTreatmentRepository(engine=engine)


def build_heat_treatment_test_registry() -> ToolRegistry:
    return ToolRegistry(heat_treatment_repository=build_heat_treatment_test_repository())
