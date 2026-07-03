from typing import Literal

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, ConfigDict, model_validator

from app.agent.catalog.heat_treatment import HEAT_STATUS_NAMES


class HeatToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str | None = None
    record_no: str | None = None
    object_id: str | None = None
    item_code: str | None = None
    lot_code: str | None = None

    @model_validator(mode="after")
    def require_record_identifier(self):
        if not self.record_id and not self.record_no and not self.object_id:
            raise ValueError("record_id, record_no, or object_id is required.")
        return self

    def resolved_record_no(self) -> str:
        return self.record_no or self.object_id or self.record_id or "UNKNOWN"


def heat_current_stage(
    record_id: str | None = None,
    record_no: str | None = None,
    object_id: str | None = None,
    item_code: str | None = None,
    lot_code: str | None = None,
) -> dict:
    args = HeatToolInput(
        record_id=record_id,
        record_no=record_no,
        object_id=object_id,
        item_code=item_code,
        lot_code=lot_code,
    )
    resolved = args.resolved_record_no()
    status = "FINISHED" if resolved in {"TRACE-HTR-K2-T-FG-001", "HT001"} else "RUNNING"
    return {
        "found": True,
        "record_no": resolved,
        "status": status,
        "status_name": HEAT_STATUS_NAMES[status],
    }


def heat_equipment_assignment(
    record_id: str | None = None,
    record_no: str | None = None,
    object_id: str | None = None,
    item_code: str | None = None,
    lot_code: str | None = None,
) -> dict:
    args = HeatToolInput(
        record_id=record_id,
        record_no=record_no,
        object_id=object_id,
        item_code=item_code,
        lot_code=lot_code,
    )
    return {
        "found": True,
        "record_no": args.resolved_record_no(),
        "equipment_id": "mock-equipment-001",
        "equipment_code": "FURNACE-01",
        "equipment_name": "一号热处理炉",
        "running_record_no": None,
    }


def heat_batch_products(
    record_id: str | None = None,
    record_no: str | None = None,
    object_id: str | None = None,
    item_code: str | None = None,
    lot_code: str | None = None,
) -> dict:
    args = HeatToolInput(
        record_id=record_id,
        record_no=record_no,
        object_id=object_id,
        item_code=item_code,
        lot_code=lot_code,
    )
    items = [
        {
            "item_code": item_code or "K2-T-FG",
            "lot_code": lot_code or "LOT-001",
            "quantity": 12,
        }
    ]
    return {
        "found": True,
        "record_no": args.resolved_record_no(),
        "items": items,
        "relation_type": "bound_items",
    }


def build_langchain_tools() -> dict[str, StructuredTool]:
    return {
        "heat_current_stage": StructuredTool.from_function(
            func=heat_current_stage,
            name="heat_current_stage",
            description="查询热处理记录当前所处阶段。",
            args_schema=HeatToolInput,
        ),
        "heat_equipment_assignment": StructuredTool.from_function(
            func=heat_equipment_assignment,
            name="heat_equipment_assignment",
            description="查询热处理记录分配设备和设备占用。",
            args_schema=HeatToolInput,
        ),
        "heat_batch_products": StructuredTool.from_function(
            func=heat_batch_products,
            name="heat_batch_products",
            description="查询热处理记录绑定产品和批次。",
            args_schema=HeatToolInput,
        ),
    }
