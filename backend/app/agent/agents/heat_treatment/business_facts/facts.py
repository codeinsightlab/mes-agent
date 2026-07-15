from app.agent.reasoning.capability_reasoning.models import BusinessFacts


BUSINESS_FACT_VERSION = "heat-treatment-business-facts-v1"


HEAT_TREATMENT_BUSINESS_FACTS = BusinessFacts(
    facts=[
        "热处理追溯编号、热处理记录号、TRACE 编号、HT 编号都可作为 record_no。",
        "状态、做到哪一步、进度、是否完成对应 heat_current_stage。",
        "设备、炉子、哪台炉对应 heat_device_trace。",
        "完成多少批、完成数量、本月完成对应 heat_completion_count_monthly。",
        "只问这个热处理怎么样时必须澄清。",
    ]
)
