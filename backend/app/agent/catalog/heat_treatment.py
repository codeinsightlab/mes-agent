from app.agent.models import CapabilitySpec


TOOL_VERSION = "heat-treatment-tools-v1"

HEAT_STATUS_NAMES = {
    "CREATED": "已创建",
    "RUNNING": "进行中",
    "FINISHED": "已完成",
    "TRANSFERRED": "已转序",
    "ENDED": "已结束",
    "CANCELLED": "已作废",
}

ARGUMENT_SCHEMA = {
    "record_id": "热处理记录内部标识，可选",
    "record_no": "热处理记录编号，可选，例如 TRACE-HTR-K2-T-FG-001 或 HT001",
    "object_id": "用户提供的对象标识，可选",
    "item_code": "产品或物料编码，可选，仅 heat_batch_products 使用",
    "lot_code": "批次号，可选，仅 heat_batch_products 使用",
}

RECORD_IDENTIFIER_GROUPS = [["record_id"], ["record_no"], ["object_id"]]

CAPABILITIES = [
    CapabilitySpec(
        name="heat_current_stage",
        business_object="heat_treatment",
        description="查询热处理记录当前所处阶段、状态、是否完成或是否结束。",
        applicable_when=[
            "热处理当前阶段",
            "热处理做到哪一步",
            "热处理是否完成或结束",
            "热处理编号对应记录状态",
            "炉子处理是否完成",
        ],
        not_applicable_when=[
            "转序单状态",
            "交接状态",
            "物料批次完整路线",
            "热处理参数是否提交",
        ],
        required_argument_groups=RECORD_IDENTIFIER_GROUPS,
        optional_arguments=[],
        argument_schema=ARGUMENT_SCHEMA,
        result_schema={"found": "bool", "record_no": "str", "status": "str", "status_name": "str"},
        examples=[
            "TRACE-HTR-K2-T-FG-001到哪了",
            "TRACE-HTR-K2-T-FG-001处理完没",
            "这个炉子处理完没 TRACE-HTR-K2-T-FG-001",
        ],
        confusing_with=["transfer_status", "trace_route_by_item_lot", "heat_param_submitted"],
        version=TOOL_VERSION,
        status="enabled",
    ),
    CapabilitySpec(
        name="heat_equipment_assignment",
        business_object="heat_treatment",
        description="查询热处理记录分配的设备、炉子及当前设备占用情况。",
        applicable_when=["分配了哪台设备", "使用哪个炉子", "设备编码或设备名称", "设备是否有运行中的热处理记录"],
        not_applicable_when=["热处理记录当前阶段", "产品批次绑定", "参数是否提交"],
        required_argument_groups=RECORD_IDENTIFIER_GROUPS,
        optional_arguments=[],
        argument_schema=ARGUMENT_SCHEMA,
        result_schema={
            "found": "bool",
            "record_no": "str",
            "equipment_id": "str",
            "equipment_code": "str",
            "equipment_name": "str",
            "running_record_no": "str | None",
        },
        examples=["TRACE-HTR-K2-T-FG-001分配到了哪个炉子", "HT001当前绑定的设备是什么"],
        confusing_with=["heat_current_stage", "heat_batch_products"],
        version=TOOL_VERSION,
        status="enabled",
    ),
    CapabilitySpec(
        name="heat_batch_products",
        business_object="heat_treatment",
        description="查询热处理记录绑定的产品、批次和数量。",
        applicable_when=["绑定了哪些产品", "包含哪些批次", "产品和批次数量"],
        not_applicable_when=["热处理当前状态", "设备分配", "参数是否提交"],
        required_argument_groups=RECORD_IDENTIFIER_GROUPS,
        optional_arguments=["item_code", "lot_code"],
        argument_schema=ARGUMENT_SCHEMA,
        result_schema={"found": "bool", "record_no": "str", "items": "list", "relation_type": "bound_items"},
        examples=["TRACE-HTR-K2-T-FG-001绑定了哪些产品", "HT001里有哪些产品"],
        confusing_with=["trace_route_by_item_lot", "heat_current_stage"],
        version=TOOL_VERSION,
        status="enabled",
    ),
    CapabilitySpec(
        name="heat_param_submitted",
        business_object="heat_treatment",
        description="判断热处理参数是否提交。当前没有唯一稳定业务口径，暂不可执行。",
        applicable_when=["热处理参数是否提交", "参数有没有提交"],
        not_applicable_when=["热处理当前阶段", "设备分配", "绑定产品批次"],
        required_argument_groups=RECORD_IDENTIFIER_GROUPS,
        optional_arguments=[],
        argument_schema=ARGUMENT_SCHEMA,
        result_schema={"status": "blocked", "reason": "str"},
        examples=["TRACE-HTR-K2-T-FG-001参数提交了吗"],
        confusing_with=["heat_current_stage"],
        version=TOOL_VERSION,
        status="blocked",
        blocked_reason="当前 submitted 没有唯一稳定业务口径",
    ),
]

CAPABILITY_BY_NAME = {capability.name: capability for capability in CAPABILITIES}
