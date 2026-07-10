# Heat Treatment Capability Catalog V1

This catalog is generated from current MES frontend and backend code. It is a discovery asset, not Tool code.

## heat_record_list

### Business Description

Query heat-treatment records for admin management.

### User Questions

- 查询热处理记录列表
- HT 单号对应的记录是什么状态
- 某设备最近有哪些热处理记录

### Input

- `recordNo`
- `status`
- `equipmentCode`
- `bindCode`
- `beginTime`
- `endTime`
- pagination from frontend table

### Output

- `id`
- `recordNo`
- `status`
- `statusName`
- `equipmentCode`
- `equipmentName`
- `itemCount`
- `bindCodeSummary`
- `photoCount`
- `remark`
- `createdBy`
- `createdTime`
- `startedTime`
- `finishedTime`

### Data Source

Table:

- `mes_heat_treatment_record`
- `mes_heat_treatment_photo` for photo count

Fields:

- `record_no`, `status`, `equipment_code`, `items_json`, `created_time`

### Execution Type

Catalog candidate. Future runtime type may be Tool or read-only SQL capability.

### Related API

- `GET /mes/heat-treatment/list`
- `HeatTreatmentRecordController.list`
- `HeatTreatmentServiceImpl.queryRecordList`
- `HeatTreatmentRecordMapper.selectRecordList`

### Related Frontend

- `src/views/md/heatTreatment/index.vue`

### Boundary

Does not infer quality state, warehouse state, PLC state, or process completion beyond `status`.

## heat_current_stage

### Business Description

Return the current heat-treatment stage/status for one record.

### User Questions

- HT20260603-007 现在什么状态
- 这个热处理做到哪一步

### Input

- `recordNo`

### Output

- `recordNo`
- `status`
- `statusName`
- optional timing fields when detail/list APIs are used

### Data Source

Table:

- `mes_heat_treatment_record`

Fields:

- `record_no`
- `status`

### Execution Type

Tool candidate.

### Related API

- `GET /mes/heat-treatment/list?recordNo=...`
- Existing mes-agent tool already reads `mes_heat_treatment_record` directly.

### Related Frontend

- `src/views/md/heatTreatment/index.vue`
- `src/views/md/heatTreatment/detail.vue`
- `src/views/md/heatTreatment/traceability/index.vue`

### Boundary

Does not answer transfer result, inspection result, or warehouse result unless additional facts are added.

## heat_record_detail

### Business Description

Query one heat-treatment record with bound products, photos, current parameters, and parameter submit history.

### User Questions

- 查看 HT 记录详情
- 这炉绑定了哪些产品
- 参数和照片是否已经提交

### Input

- `id`

### Output

- record base fields
- `items`
- `photos`
- `paramSummary`
- `paramStages`
- `paramSubmits`
- warning fields for active record at create time

### Data Source

Tables:

- `mes_heat_treatment_record`
- `mes_heat_treatment_photo`
- `mes_heat_treatment_param_submit`
- `mes_heat_treatment_param_record`
- `mes_heat_treatment_param_template`

### Execution Type

Tool candidate.

### Related API

- `GET /mes/heat-treatment/{id}`
- `GET /mobile/heat-treatment/{id}`

### Related Frontend

- `src/views/md/heatTreatment/detail.vue`
- `src/views/md/heatTreatment/traceability/index.vue`

### Boundary

Requires internal `id`, not only `recordNo`, unless a lookup step is added.

## heat_status_options

### Business Description

Return backend-owned heat-treatment status options.

### User Questions

- 热处理有哪些状态
- 状态枚举是什么

### Input

None.

### Output

- `label`
- `value`

### Data Source

- Java enum `HeatTreatmentStatusEnum`

### Execution Type

Reference/catalog capability.

### Related API

- `GET /mes/heat-treatment/status-options`

### Related Frontend

- `src/views/md/heatTreatment/index.vue`
- `src/views/md/heatTreatment/traceability/index.vue`

### Boundary

Does not invent frontend-only statuses.

## heat_device_status

### Business Description

Show heat-treatment equipment status derived from MES records.

### User Questions

- 哪些热处理设备正在运行
- 某设备当前炉次是什么
- 设备是否空闲

### Input

- Admin: none
- Mobile: optional `deviceType`

### Output

- `equipmentId`
- `equipmentCode`
- `equipmentName`
- `deviceType`
- `active`
- `status`
- `statusLabel`
- `runningRecordId`
- `runningRecordNo`
- `runningStartTime`
- `runningItemCount`
- `lastRecordId`
- `lastRecordNo`
- `lastEndTime`
- risk flags

### Data Source

Tables:

- `mes_equipment`
- `mes_heat_treatment_record`

### Execution Type

Tool candidate, with warning label.

### Related API

- `GET /mes/heat-treatment/device-status`
- `GET /mobile/heat-treatment/equipment-list`

### Related Frontend

- `src/views/md/heatTreatment/index.vue`

### Boundary

Not PLC telemetry. Backend scanned code currently emits `ACTIVE` and `IDLE`; frontend has risk rendering but backend `RISK` emission is UNKNOWN.

## heat_batch_lifecycle

### Business Description

Query all heat-treatment records for one product batch lifecycle.

### User Questions

- 这个批次经历过哪些热处理
- 当前在哪一步
- 哪台设备处理过

### Input

- `itemCode` + `lotNo`
- or `recordNo` to resolve product batch identity

### Output

- lifecycle context: `itemCode`, `lotNo`, `productName`, `specification`
- lifecycle records with record id/no, equipment, status, start/end time, operator, matched items

### Data Source

Tables:

- `mes_heat_treatment_record`
- `mes_equipment`

Fields:

- `items_json.productCode`
- `items_json.batchNo`
- `items_json.lotCode`
- `items_json.originalLotCode`
- record timing/status/equipment fields

### Execution Type

Tool candidate.

### Related API

- `GET /mes/heat-treatment/traceability/lifecycle`
- `HeatTreatmentServiceImpl.selectHeatTreatmentLifecycle`
- `HeatTreatmentRecordExtraMapper.selectTraceabilityCandidates`

### Related Frontend

- `src/views/md/heatTreatment/traceability/index.vue`

### Boundary

Does not replace single-record detail. Deep params/photos still come from `GET /mes/heat-treatment/{id}` and traceability detail calls.

## heat_traceability_candidates

### Business Description

Find candidate heat-treatment records by product, batch, record, equipment, time, or status.

### User Questions

- 按产品名称找热处理记录
- 按设备和时间定位候选记录
- 这个热处理单号对应哪个产品批次

### Input

- `itemCode`
- `lotNo`
- `productName`
- `recordNo`
- `equipmentType`
- `equipmentCode`
- `beginTime`
- `endTime`
- `status`

### Output

- candidate `records`
- `total`
- when detail query: summary, lifecycle, batch overview, params, photos, related products, logs

### Data Source

Tables:

- `mes_heat_treatment_record`
- `mes_equipment`
- parameter/photo tables for detail aggregation

### Execution Type

Tool candidate.

### Related API

- `GET /mes/heat-treatment/traceability`

### Related Frontend

- `src/views/md/heatTreatment/traceability/index.vue`

### Boundary

When multiple matches exist and query is not detail-level, backend returns candidate records only.

## heat_related_products

### Business Description

Find products related to a selected heat-treatment record by same batch or same-equipment overlapping time window.

### User Questions

- 同设备同时间还有哪些产品
- 这个批次同期处理了什么

### Input

- traceability query, usually current selected `recordNo` or `itemCode + lotNo`

### Output

- `recordNo`
- `itemCode`
- `productName`
- `lotNo`
- `equipmentCode`
- `equipmentName`
- `processName`
- `inTime`
- `outTime`
- `status`
- `statusName`
- `relationType`

### Data Source

- `mes_heat_treatment_record`
- `items_json`

### Execution Type

Tool candidate.

### Related API

- `GET /mes/heat-treatment/traceability`

### Related Frontend

- `src/views/md/heatTreatment/traceability/index.vue`

### Boundary

Relation is not proof of workflow order. `同设备同期` means overlapping same-equipment time window.

## heat_param_history

### Business Description

Query current and historical heat-treatment parameter submissions.

### User Questions

- 热处理参数是否完整
- 哪些参数改过
- 某次提交记录了什么

### Input

- `recordId`
- Optional product/bind context when using template APIs

### Output

- `paramStages`
- `paramSubmits`
- per-param `oldValue`, `paramValue`, `changedFlag`, submit actor/time

### Data Source

Tables:

- `mes_heat_treatment_param_submit`
- `mes_heat_treatment_param_record`
- `mes_heat_treatment_param_template`

### Execution Type

Tool candidate.

### Related API

- `GET /mes/heat-treatment/{id}`
- `GET /mobile/heat-treatment/{id}/params`
- `POST /mobile/heat-treatment/{id}/params`

### Related Frontend

- `HeatTreatmentParameterCard.vue`
- detail page
- traceability page

### Boundary

Does not infer pass/fail quality. `changedFlag` only means value changed from latest previous value.

## heat_photo_evidence

### Business Description

Query heat-treatment photo evidence for one record.

### User Questions

- 这条热处理有没有照片
- 照片是什么阶段上传的
- 谁上传了证据照片

### Input

- `recordId`

### Output

- `photoId` / `id`
- `recordNo`
- `photoStage`
- `photoStageName`
- `fileUrl`
- `watermarkedUrl`
- `shootTime`
- `uploadTime`
- `uploadBy`
- `source`
- `sourceName`
- `watermarkText`
- `remark`

### Data Source

Table:

- `mes_heat_treatment_photo`

### Execution Type

Tool candidate.

### Related API

- `GET /mes/heat-treatment/{id}`
- `POST /mobile/heat-treatment/{id}/upload-photo`

### Related Frontend

- `HeatTreatmentEvidenceCard.vue`
- detail page
- traceability page

### Boundary

Photo existence is evidence presence, not automatic quality approval.

## heat_record_create

### Business Description

Create a heat-treatment record for equipment.

### User Questions

- 新建热处理记录
- 为某设备开一条热处理单

### Input

- `equipmentCode`
- `programNo`
- `remark`

### Output

- `HeatTreatmentRecordDetailVO`
- warning fields if equipment already has running record

### Data Source

Tables:

- `mes_heat_treatment_record`
- `mes_heat_treatment_param_submit`
- `mes_heat_treatment_param_record`

### Execution Type

Action capability. Not a read-only Tool unless explicitly authorized.

### Related API

- `POST /mes/heat-treatment`
- `POST /mobile/heat-treatment/create`

### Related Frontend

- `src/views/md/heatTreatment/index.vue`

### Boundary

Requires write authorization. Not part of read-only runtime without explicit phase approval.

## heat_record_state_transition

### Business Description

Start, finish, cancel/void, or transfer a heat-treatment record.

### User Questions

- 开始热处理
- 完成热处理
- 作废热处理
- 转到下一道热处理设备

### Input

- `id`
- transition-specific body: remark, void reason, target equipment, items, program no, reminders

### Output

- detail VO or transfer result

### Data Source

Table:

- `mes_heat_treatment_record`

### Execution Type

Action capability. Not read-only.

### Related API

- `POST /mobile/heat-treatment/{id}/start`
- `POST /mobile/heat-treatment/{id}/finish`
- `POST /mobile/heat-treatment/{id}/transfer-next`
- `POST /mobile/heat-treatment/{id}/void`
- `POST /mobile/heat-treatment/{id}/cancel`
- `POST /mes/heat-treatment/{id}/void`

### Related Frontend

- Admin detail and index only expose void/remark.
- Mobile controller exposes production transitions.

### Boundary

Must enforce backend status rules. Do not let LLM decide state transitions.

## heat_product_info_lookup

### Business Description

Lookup product information for heat-treatment binding.

### User Questions

- 扫码后这个产品是什么
- 这个单据有哪些产品明细

### Input

- `code`

### Output

- `HeatTreatmentProductInfoVO`
- product fields including product code/name/specification/lot/quantity

### Data Source

- `MoReceiptRequistionMapper.selectReceiptRequisitionProductByDocNo`
- `MoReceiptRequistionMapper.selectReceiptRequisitionProductListByDocNo`

### Execution Type

Tool candidate, but ERP source mapping is partial in this scan.

### Related API

- `GET /mobile/heat-treatment/product-info`
- `GET /mobile/heat-treatment/product-info-list`

### Related Frontend

- Not in `ktg-mes-ui` admin pages scanned.

### Boundary

ERP table mapping remains partial here. Mark exact ERP source fields as UNKNOWN unless mapper evidence is added.
