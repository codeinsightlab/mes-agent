# Heat Treatment API Mapping

## Admin Frontend Mapping

| Capability | Frontend | API | Controller | Service | Mapper / Source |
| --- | --- | --- | --- | --- | --- |
| `heat_record_list` | `src/views/md/heatTreatment/index.vue` | `GET /mes/heat-treatment/list` | `HeatTreatmentRecordController.list` | `queryRecordList` | `HeatTreatmentRecordMapper.selectRecordList`, `HeatTreatmentPhotoMapper.countByRecordIds` |
| `heat_status_options` | `src/views/md/heatTreatment/index.vue`, `traceability/index.vue` | `GET /mes/heat-treatment/status-options` | `HeatTreatmentRecordController.statusOptions` | `queryStatusOptions` | `HeatTreatmentStatusEnum` |
| `heat_device_status` | `src/views/md/heatTreatment/index.vue` | `GET /mes/heat-treatment/device-status` | `HeatTreatmentRecordController.deviceStatus` | `queryDeviceStatus` | `MesEquipmentMapper.selectHeatTreatmentDeviceList`, `HeatTreatmentRecordMapper.selectRunningHeatTreatmentRecords` |
| `heat_record_detail` | `src/views/md/heatTreatment/detail.vue` | `GET /mes/heat-treatment/{id}` | `HeatTreatmentRecordController.detail` | `queryRecordById` | record, photo, parameter, template mappers |
| `heat_trace_by_bind_code` | API module only | `GET /mes/heat-treatment/trace` | `HeatTreatmentRecordController.trace` | `queryTraceByBindCode` | `HeatTreatmentRecordMapper.selectRecordList` with JSON bindCode search |
| `heat_traceability_candidates` | `src/views/md/heatTreatment/traceability/index.vue` | `GET /mes/heat-treatment/traceability` | `HeatTreatmentRecordController.traceability` | `selectHeatTreatmentTraceability` | `HeatTreatmentRecordExtraMapper.selectTraceabilityCandidates` |
| `heat_batch_lifecycle` | `src/views/md/heatTreatment/traceability/index.vue` | `GET /mes/heat-treatment/traceability/lifecycle` | `HeatTreatmentRecordController.lifecycle` | `selectHeatTreatmentLifecycle` | `HeatTreatmentRecordExtraMapper.selectTraceabilityCandidates` |
| `heat_record_create` | `src/views/md/heatTreatment/index.vue` | `POST /mes/heat-treatment` | `HeatTreatmentRecordController.create` | `createRecord` | `HeatTreatmentRecordMapper.insertRecord`, param submit/record insert |
| `heat_record_remark_update` | `src/views/md/heatTreatment/index.vue`, `detail.vue` | `POST /mes/heat-treatment/{id}/remark` | `HeatTreatmentRecordController.remark` | `updateRemark` | `HeatTreatmentRecordMapper.updateRemark` |
| `heat_record_void` | `src/views/md/heatTreatment/index.vue`, `detail.vue` | `POST /mes/heat-treatment/{id}/void` | `HeatTreatmentRecordController.voidRecord` | `voidRecord` / `cancelRecord` | `HeatTreatmentRecordMapper.updateStatusFromCreatedOrRunningToCancelled` |
| `heat_record_delete` | `src/views/md/heatTreatment/index.vue` | `DELETE /mes/heat-treatment/{ids}` | `HeatTreatmentRecordController.remove` | `deleteHeatTreatmentRecordByIds` | record, photo, param submit, param record delete mappers |

## Traceability Page Request Flow

| User operation | Frontend behavior | Backend calls |
| --- | --- | --- |
| Query by `recordNo` | Load lifecycle directly | `GET /mes/heat-treatment/traceability/lifecycle?recordNo=...`, then selected detail calls |
| Query by `itemCode + lotNo` | Load lifecycle directly | `GET /mes/heat-treatment/traceability/lifecycle?itemCode=...&lotNo=...`, then selected detail calls |
| Query by partial product/equipment/status/time | Load candidate records | `GET /mes/heat-treatment/traceability?...` |
| Select candidate | Load lifecycle by selected `recordNo` | `GET /mes/heat-treatment/traceability/lifecycle?recordNo=...` |
| Select lifecycle record | Load deep detail for one record | `GET /mes/heat-treatment/{recordId}` and `GET /mes/heat-treatment/traceability?recordNo=...` |
| Select related product | Load lifecycle by related `itemCode + lotNo` | `GET /mes/heat-treatment/traceability/lifecycle?itemCode=...&lotNo=...` |

## Mobile / Production API Mapping

| Capability | API | Controller | Service | Notes |
| --- | --- | --- | --- | --- |
| `heat_mobile_record_list` | `GET /mobile/heat-treatment/list` | `MobileHeatTreatmentController.list` | `queryMobileRecordList` | Excludes default statuses when no status supplied |
| `heat_mobile_create` | `POST /mobile/heat-treatment/create` | `MobileHeatTreatmentController.create` | `createRecord` | Creates `CREATED` record |
| `heat_my_running` | `GET /mobile/heat-treatment/my-running` | `MobileHeatTreatmentController.myRunning` | `queryMyRunning` | Current user running/created records |
| `heat_my_recent` | `GET /mobile/heat-treatment/my-recent` | `MobileHeatTreatmentController.myRecent` | `queryMyRecent` | Delegates to mobile list |
| `heat_equipment_list_by_type` | `GET /mobile/heat-treatment/equipment-list` | `MobileHeatTreatmentController.equipmentList` | `queryDeviceStatus(deviceType)` | Record-derived status |
| `heat_product_info_lookup` | `GET /mobile/heat-treatment/product-info` | `MobileHeatTreatmentController.productInfo` | `queryProductInfo` | Uses `MoReceiptRequistionMapper` |
| `heat_product_info_list_lookup` | `GET /mobile/heat-treatment/product-info-list` | `MobileHeatTreatmentController.productInfoList` | `queryProductInfoList` | Uses `MoReceiptRequistionMapper` |
| `heat_mobile_detail` | `GET /mobile/heat-treatment/{id}` | `MobileHeatTreatmentController.detail` | `queryRecordById` | Same detail model |
| `heat_param_template` | `GET /mobile/heat-treatment/param-template` | `MobileHeatTreatmentController.paramTemplate` | `queryParamTemplate` | Product/equipment matched template |
| `heat_params_by_record` | `GET /mobile/heat-treatment/{id}/params` | `MobileHeatTreatmentController.params` | `queryParamsByRecordId` | Existing values overlaid on template |
| `heat_save_params` | `POST /mobile/heat-treatment/{id}/params` | `MobileHeatTreatmentController.saveParams` | `saveParams` | Only `RUNNING` records |
| `heat_save_program_no` | `POST /mobile/heat-treatment/{id}/program-no` | `MobileHeatTreatmentController.saveProgramNo` | `saveProgramNo` | Only `CREATED` records |
| `heat_bind_item` | `POST /mobile/heat-treatment/{id}/bind-item` | `MobileHeatTreatmentController.bindItem` | `bindItem` | Final statuses rejected |
| `heat_bind_items` | `POST /mobile/heat-treatment/{id}/bind-items` | `MobileHeatTreatmentController.bindItems` | `bindItems` | `CREATED`/`RUNNING` only |
| `heat_start` | `POST /mobile/heat-treatment/{id}/start` | `MobileHeatTreatmentController.start` | `startRecord` | `CREATED` only, requires items |
| `heat_upload_photo` | `POST /mobile/heat-treatment/{id}/upload-photo` | `MobileHeatTreatmentController.uploadPhoto` | `uploadPhoto` | `RUNNING` only |
| `heat_reminder` | `POST /mobile/heat-treatment/{id}/reminder` | `MobileHeatTreatmentController.reminder` | `submitReminder` | Reminder scheduling only |
| `heat_mobile_remark` | `POST /mobile/heat-treatment/{id}/remark` | `MobileHeatTreatmentController.remark` | `updateRemark` | Final statuses rejected |
| `heat_finish` | `POST /mobile/heat-treatment/{id}/finish` | `MobileHeatTreatmentController.finish` | `finishRecord` | `RUNNING` only, requires items |
| `heat_transfer_next` | `POST /mobile/heat-treatment/{id}/transfer-next` | `MobileHeatTreatmentController.transferNext` | `transferNext` | `FINISHED` only |
| `heat_mobile_void` | `POST /mobile/heat-treatment/{id}/void` | `MobileHeatTreatmentController.voidRecord` | `voidRecord` | `CREATED`/`RUNNING` only |
| `heat_mobile_cancel` | `POST /mobile/heat-treatment/{id}/cancel` | `MobileHeatTreatmentController.cancelRecord` | `cancelRecord` | `CREATED`/`RUNNING` only |
| `heat_mobile_trace` | `GET /mobile/heat-treatment/trace` | `MobileHeatTreatmentController.trace` | `queryTraceByBindCode` | bind code trace |

## Request / Response Field Notes

`HeatTreatmentQueryRequest` supports:

- `recordNo`
- `status`
- `equipmentCode`
- `createdBy`
- `bindCode`
- `beginTime`
- `endTime`
- `excludeStatuses`

`HeatTreatmentTraceabilityQuery` supports:

- `itemCode`
- `lotNo`
- `productName`
- `recordNo`
- `equipmentType`
- `equipmentCode`
- `beginTime`
- `endTime`
- `status`
- `limitSize`

`HeatTreatmentRecordDetailVO` includes:

- record base fields
- `items`
- `photos`
- `photoCompleteness`
- `paramSummary`
- `paramStages`
- `paramSubmits`
- warning fields

Unknown or partial:

- Exact ERP product-source tables behind `MoReceiptRequistionMapper` are not fully mapped in this document.
- Frontend admin pages do not call mobile production transition APIs except shared detail/read behavior.
