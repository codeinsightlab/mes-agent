# Heat Treatment Business Facts

This document separates system facts from user capabilities. A fact is a deterministic statement backed by code, SQL, Entity, Mapper, DTO, VO, or Enum.

## Fact: heat_treatment_record

Description: A single heat-treatment process record.

Evidence:

- Entity: `HeatTreatmentRecord`
- Table: `mes_heat_treatment_record`
- Mapper: `HeatTreatmentRecordMapper.xml`
- Detail VO: `HeatTreatmentRecordDetailVO`

Fields:

| Field | Source | Meaning |
| --- | --- | --- |
| `id` | `mes_heat_treatment_record.id` | Record primary key |
| `recordNo` | `record_no` | Heat-treatment record number, generated as `HTyyyyMMdd-###` |
| `equipmentId` | `equipment_id` | Equipment id snapshot |
| `equipmentCode` | `equipment_code` | Equipment code snapshot |
| `equipmentName` | `equipment_name` | Equipment name snapshot |
| `status` | `status` | Current heat-treatment status |
| `itemsJson` | `items_json` | Bound product/basket list JSON |
| `remark` | `remark` | Remark |
| `createdBy` / `createdTime` | `created_by` / `created_time` | Creation actor/time |
| `startedBy` / `startedTime` | `started_by` / `started_time` | Start actor/time |
| `finishedBy` / `finishedTime` | `finished_by` / `finished_time` | Finish actor/time |
| `voidReason` | `void_reason` | Void reason field exists in schema/entity |
| `updateBy` / `updateTime` | `update_by` / `update_time` | Last update actor/time |

Rules:

- Creating a record sets status to `CREATED`.
- Starting a record is only allowed from `CREATED` and requires at least one bound item.
- Finishing a record is only allowed from `RUNNING` and requires at least one bound item.
- Voiding/cancelling is only allowed from `CREATED` or `RUNNING`.
- Remark update is blocked for final statuses.
- Deleting a record also deletes related parameter records, parameter submits, and photos.

## Fact: heat_treatment_record_status

Source of truth:

- Java enum: `HeatTreatmentStatusEnum`
- Database field: `mes_heat_treatment_record.status`
- Frontend display options: `GET /mes/heat-treatment/status-options`

| Code | Java label | Confirmed meaning from code |
| --- | --- | --- |
| `CREATED` | 已创建 | Record created, can start, can bind, can save program no, can void |
| `RUNNING` | 进行中 | Record started, can save params, upload photo, finish, void |
| `FINISHED` | 已完成 | Record finished, can transfer next |
| `TRANSFERRED` | 已转序 | Source record transferred into a new created target record |
| `ENDED` | 已结束 | Final status used by same-flow completion after tempering |
| `CANCELLED` | 已作废 | Cancelled/voided final status |

Final status helper:

- `FINISHED`, `TRANSFERRED`, `ENDED`, `CANCELLED` are treated as final by `HeatTreatmentStatusEnum.isFinal`, though `FINISHED` still supports `transferNext`.

## Fact: heat_equipment_assignment

Description: Heat-treatment records carry equipment snapshots and device status is derived from equipment master data plus running records.

Sources:

- `mes_heat_treatment_record.equipment_id`
- `mes_heat_treatment_record.equipment_code`
- `mes_heat_treatment_record.equipment_name`
- `mes_equipment`, via `MesEquipmentMapper.selectHeatTreatmentDeviceList`
- `HeatTreatmentDeviceStatusVO`

Device status values:

| Status | Label | Source logic |
| --- | --- | --- |
| `ACTIVE` | 活跃 | At least one `RUNNING` heat-treatment record exists for the equipment |
| `IDLE` | 空闲 | No running heat-treatment record found |
| `RISK` | UNKNOWN | Frontend has display handling, but backend scanned code sets only `ACTIVE` or `IDLE` |

Important boundary:

- Admin page text says device status is derived from heat-treatment process records and does not represent PLC acquisition state.

## Fact: heat_batch_products

Description: Product/basket binding facts stored in `items_json`.

Source:

- Field: `mes_heat_treatment_record.items_json`
- Runtime type: `List<HeatTreatmentItemVO>`
- Bind type enum: `HeatTreatmentBindTypeEnum`

Bind types:

| Code | Label |
| --- | --- |
| `PRODUCT_BATCH` | 产品批次 |
| `CONTAINER` | 篮筐 |

Fields in bound item:

- `bindType`
- `bindTypeName`
- `bindCode`
- `detailId`
- `itemId`
- `itemBusinessId`
- `productCode`
- `productName`
- `specification`
- `itemLotId`
- `batchNo`
- `lotCode`
- `originalLotCode`
- `quantity`
- `scannedBy`
- `scannedTime`
- `createdBy`
- `createdTime`

Traceability lot matching:

- SQL candidate search checks `batchNo`, `lotCode`, and `originalLotCode` inside JSON.
- Service `resolveItemLotNo` returns first non-empty of `batchNo`, `lotCode`, `originalLotCode`.
- This is existing backend behavior, not a recommendation for new UI fallback.

## Fact: heat_parameter_record

Description: Per-parameter submitted values for heat-treatment records.

Sources:

- Table: `mes_heat_treatment_param_record`
- Entity: `HeatTreatmentParamRecord`
- Mapper: `HeatTreatmentParamRecordMapper.xml`
- Submit batch table: `mes_heat_treatment_param_submit`

Per-parameter fields:

- `param_record_id`
- `heat_treatment_record_id`
- `submit_id`
- `submit_no`
- `submit_time`
- `submit_by`
- `submit_by_name`
- `equipment_code`
- `device_type`
- `product_code`
- `product_name`
- `bind_code`
- `stage_code`
- `stage_name`
- `param_code`
- `param_name`
- `unit`
- `input_type`
- `param_value`
- `old_value`
- `changed_flag`
- `photo_ids`

Rules:

- Saving params is only allowed when record status is `RUNNING`.
- `bindCode` is required for normal parameter saving.
- `stageCode`, `stageName`, `paramCode`, `paramName`, and `inputType` are required per item.
- `oldValue` is loaded from the latest previous value by key.
- `changedFlag` is true when latest previous value exists and differs.

## Fact: heat_parameter_submit

Description: One submitted batch of parameter rows.

Source:

- Table: `mes_heat_treatment_param_submit`
- Entity: `HeatTreatmentParamSubmit`
- Mapper: `HeatTreatmentParamSubmitMapper.xml`

Fields:

- `submit_id`
- `heat_treatment_record_id`
- `submit_no`
- `submit_time`
- `submit_by`
- `submit_by_name`
- `photo_ids`
- `item_count`
- `changed_count`
- `create_by`
- `create_time`

## Fact: heat_parameter_template

Description: Parameter template values by product/equipment/device type.

Sources:

- Table: `mes_heat_treatment_param_template`
- Entity: `HeatTreatmentParamTemplate`
- Mapper: `HeatTreatmentParamTemplateMapper.xml`
- Service: `buildParamTemplateGroup`

Template matching:

- Enabled template only: `enabled = '1'`
- Product match by `product_code` or `product_name`
- Equipment match by `equipment_code` or `device_type`

Device-stage mapping:

| Device type | Stage codes |
| --- | --- |
| 加热炉 | `BASIC`, `CARBURIZING`, `DIFFUSION`, `QUENCHING`, `ATMOSPHERE_MEDIUM`, `QUENCHING_PROCESS` |
| 清洗机 | `SOAKING`, `ALKALINE_SPRAY`, `WATER_SPRAY`, `VACUUM` |
| 回火炉 | `TEMPERING` |

## Fact: heat_photo_evidence

Description: Heat-treatment photo evidence.

Sources:

- Table: `mes_heat_treatment_photo`
- Entity: `HeatTreatmentPhoto`
- Mapper: `HeatTreatmentPhotoMapper.xml`
- Enum: `HeatTreatmentPhotoStageEnum`
- Enum: `HeatTreatmentPhotoSourceEnum`

Fields:

- `id`
- `record_id`
- `photo_stage`
- `file_url`
- `watermarked_url`
- `shoot_time`
- `upload_time`
- `upload_by`
- `source`
- `watermark_text`
- `remark`

Photo stages:

- `EVIDENCE` = 证据照片
- `HEATING` = 加热炉
- `CLEANING` = 清洗机
- `TEMPERING` = 回火炉

Photo sources:

- `CAMERA` = 实时拍照
- `ALBUM` = 相册上传

Rules:

- Uploading a photo is only allowed when record status is `RUNNING`.
- `photoStage`, `source`, and `fileUrl` are required.
- Watermark text is generated from the record and photo stage in service code.

## Fact: heat_lifecycle_trace

Description: Product batch heat-treatment lifecycle.

Source:

- API: `GET /mes/heat-treatment/traceability/lifecycle`
- Service: `selectHeatTreatmentLifecycle`
- Query: `HeatTreatmentTraceabilityQuery`
- VO: `HeatTreatmentLifecycleTraceVO`

Identity:

- Direct: `itemCode + lotNo`
- Indirect: `recordNo` resolves one bound product batch from that record.

Output:

- `itemCode`
- `lotNo`
- `itemName`
- `productName`
- `specification`
- `sourceRecordNo`
- `selectedRecordNo`
- lifecycle `records`

Record output includes:

- `recordId`
- `recordNo`
- `equipmentCode`
- `equipmentName`
- `equipmentType`
- `status`
- `statusName`
- `startTime`
- `endTime`
- `operatorName`
- `remark`
- `matchedItems`
- `sourceRecordNo`

## Fact: heat_traceability_related_products

Description: Products related to a traceability result by same batch or same equipment time overlap.

Source:

- API: `GET /mes/heat-treatment/traceability`
- Service: `buildRelatedProducts`
- Mapper: `selectTraceabilityRelatedRecords`

Relation labels:

- `同批次`
- `同设备同期`

Boundary:

- Same-device relation is based on overlapping time window from record start/end/update/current time.
- It is not a direct proof of workflow dependency.

## Fact: heat_operation_log

Description: Operation logs returned by traceability are derived from parameter submit batches.

Source:

- Service: `buildTraceabilitySubmitLogs`
- VO: `HeatTreatmentTraceabilityLogVO`

Observed action:

- `参数提交`

Boundary:

- No independent operation-log table was confirmed in this scan.
