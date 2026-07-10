# Heat Treatment Data Source Mapping

## Record Facts

| Fact | Table | Field | Description |
| --- | --- | --- | --- |
| `heat_record_id` | `mes_heat_treatment_record` | `id` | Heat-treatment record primary key |
| `heat_record_no` | `mes_heat_treatment_record` | `record_no` | Heat-treatment record number |
| `heat_status` | `mes_heat_treatment_record` | `status` | Current heat-treatment status |
| `heat_equipment_id` | `mes_heat_treatment_record` | `equipment_id` | Equipment id snapshot |
| `heat_equipment_code` | `mes_heat_treatment_record` | `equipment_code` | Equipment code snapshot |
| `heat_equipment_name` | `mes_heat_treatment_record` | `equipment_name` | Equipment name snapshot |
| `heat_bound_items` | `mes_heat_treatment_record` | `items_json` | Bound product/basket list JSON |
| `heat_remark` | `mes_heat_treatment_record` | `remark` | Remark |
| `heat_created_by` | `mes_heat_treatment_record` | `created_by` | Creator |
| `heat_created_time` | `mes_heat_treatment_record` | `created_time` | Creation time |
| `heat_started_by` | `mes_heat_treatment_record` | `started_by` | Starter |
| `heat_started_time` | `mes_heat_treatment_record` | `started_time` | Start time |
| `heat_finished_by` | `mes_heat_treatment_record` | `finished_by` | Finisher |
| `heat_finished_time` | `mes_heat_treatment_record` | `finished_time` | Finish time |
| `heat_void_reason` | `mes_heat_treatment_record` | `void_reason` | Void reason field |
| `heat_update_by` | `mes_heat_treatment_record` | `update_by` | Updater |
| `heat_update_time` | `mes_heat_treatment_record` | `update_time` | Update time |

## Bound Product / Batch Facts

| Fact | Table | Field | Description |
| --- | --- | --- | --- |
| `heat_bind_type` | `mes_heat_treatment_record` | `items_json[*].bindType` | `PRODUCT_BATCH` or `CONTAINER` |
| `heat_bind_code` | `mes_heat_treatment_record` | `items_json[*].bindCode` | Product/basket binding code |
| `heat_item_code` | `mes_heat_treatment_record` | `items_json[*].productCode` | Product/item code used by traceability query |
| `heat_product_name` | `mes_heat_treatment_record` | `items_json[*].productName` | Product name |
| `heat_specification` | `mes_heat_treatment_record` | `items_json[*].specification` | Product specification |
| `heat_item_lot_id` | `mes_heat_treatment_record` | `items_json[*].itemLotId` | Item lot id |
| `heat_batch_no` | `mes_heat_treatment_record` | `items_json[*].batchNo` | Batch number, used by backend lot resolution |
| `heat_lot_code` | `mes_heat_treatment_record` | `items_json[*].lotCode` | Lot code, used by backend lot resolution |
| `heat_original_lot_code` | `mes_heat_treatment_record` | `items_json[*].originalLotCode` | Original lot code, used by backend lot resolution |
| `heat_quantity` | `mes_heat_treatment_record` | `items_json[*].quantity` | Bound quantity |
| `heat_scanned_by` | `mes_heat_treatment_record` | `items_json[*].scannedBy` | Scanner |
| `heat_scanned_time` | `mes_heat_treatment_record` | `items_json[*].scannedTime` | Scan time |

Note: `items_json` field-level mapping is based on `HeatTreatmentItemVO` and JSON search in mapper XML. It is not a normalized table.

## Status Facts

| Fact | Source | Field | Description |
| --- | --- | --- | --- |
| `heat_status_created` | `HeatTreatmentStatusEnum` | `CREATED` | 已创建 |
| `heat_status_running` | `HeatTreatmentStatusEnum` | `RUNNING` | 进行中 |
| `heat_status_finished` | `HeatTreatmentStatusEnum` | `FINISHED` | 已完成 |
| `heat_status_transferred` | `HeatTreatmentStatusEnum` | `TRANSFERRED` | 已转序 |
| `heat_status_ended` | `HeatTreatmentStatusEnum` | `ENDED` | 已结束 |
| `heat_status_cancelled` | `HeatTreatmentStatusEnum` | `CANCELLED` | 已作废 |

## Equipment Facts

| Fact | Table | Field | Description |
| --- | --- | --- | --- |
| `heat_equipment_master_id` | `mes_equipment` | `equipment_id` | Equipment master id |
| `heat_equipment_master_code` | `mes_equipment` | `equipment_code` | Equipment master code |
| `heat_equipment_master_name` | `mes_equipment` | `equipment_name` | Equipment master name |
| `heat_equipment_master_type` | `mes_equipment` | `equipment_type` | Device type before normalization |
| `heat_device_status` | derived | UNKNOWN | Derived as `ACTIVE` or `IDLE` from running heat-treatment records |
| `heat_running_record` | `mes_heat_treatment_record` | `status = RUNNING` by equipment | Basis for active equipment display |
| `heat_plc_status` | UNKNOWN | UNKNOWN | Not present in scanned admin/frontend/backend chain |

## Parameter Facts

| Fact | Table | Field | Description |
| --- | --- | --- | --- |
| `heat_param_submit_id` | `mes_heat_treatment_param_submit` | `submit_id` | Submit batch id |
| `heat_param_submit_record_id` | `mes_heat_treatment_param_submit` | `heat_treatment_record_id` | Parent record id |
| `heat_param_submit_no` | `mes_heat_treatment_param_submit` | `submit_no` | Submit batch number |
| `heat_param_submit_time` | `mes_heat_treatment_param_submit` | `submit_time` | Submit time |
| `heat_param_submit_by` | `mes_heat_treatment_param_submit` | `submit_by` | Submitter |
| `heat_param_submit_by_name` | `mes_heat_treatment_param_submit` | `submit_by_name` | Submitter display name |
| `heat_param_submit_photo_ids` | `mes_heat_treatment_param_submit` | `photo_ids` | Associated photo ids |
| `heat_param_submit_item_count` | `mes_heat_treatment_param_submit` | `item_count` | Submitted parameter count |
| `heat_param_submit_changed_count` | `mes_heat_treatment_param_submit` | `changed_count` | Changed parameter count |
| `heat_param_record_id` | `mes_heat_treatment_param_record` | `param_record_id` | Parameter row id |
| `heat_param_record_submit_id` | `mes_heat_treatment_param_record` | `submit_id` | Submit batch id |
| `heat_param_record_equipment_code` | `mes_heat_treatment_param_record` | `equipment_code` | Equipment code |
| `heat_param_record_device_type` | `mes_heat_treatment_param_record` | `device_type` | Device type |
| `heat_param_record_product_code` | `mes_heat_treatment_param_record` | `product_code` | Product code |
| `heat_param_record_product_name` | `mes_heat_treatment_param_record` | `product_name` | Product name |
| `heat_param_record_bind_code` | `mes_heat_treatment_param_record` | `bind_code` | Bind code |
| `heat_param_stage_code` | `mes_heat_treatment_param_record` | `stage_code` | Parameter stage code |
| `heat_param_stage_name` | `mes_heat_treatment_param_record` | `stage_name` | Parameter stage name |
| `heat_param_code` | `mes_heat_treatment_param_record` | `param_code` | Parameter code |
| `heat_param_name` | `mes_heat_treatment_param_record` | `param_name` | Parameter name |
| `heat_param_unit` | `mes_heat_treatment_param_record` | `unit` | Unit |
| `heat_param_input_type` | `mes_heat_treatment_param_record` | `input_type` | Input type |
| `heat_param_value` | `mes_heat_treatment_param_record` | `param_value` | Submitted value |
| `heat_param_old_value` | `mes_heat_treatment_param_record` | `old_value` | Previous latest value |
| `heat_param_changed_flag` | `mes_heat_treatment_param_record` | `changed_flag` | Whether value changed |
| `heat_param_photo_ids` | `mes_heat_treatment_param_record` | `photo_ids` | Associated photo ids |

## Parameter Template Facts

| Fact | Table | Field | Description |
| --- | --- | --- | --- |
| `heat_param_template_id` | `mes_heat_treatment_param_template` | `template_id` | Template id |
| `heat_param_template_name` | `mes_heat_treatment_param_template` | `template_name` | Template name |
| `heat_param_template_product_code` | `mes_heat_treatment_param_template` | `product_code` | Product code match |
| `heat_param_template_product_name` | `mes_heat_treatment_param_template` | `product_name` | Product name match |
| `heat_param_template_equipment_code` | `mes_heat_treatment_param_template` | `equipment_code` | Equipment code match |
| `heat_param_template_device_type` | `mes_heat_treatment_param_template` | `device_type` | Device type match |
| `heat_param_template_enabled` | `mes_heat_treatment_param_template` | `enabled` | Enabled flag |
| `heat_param_template_program_no` | `mes_heat_treatment_param_template` | `program_no` | Program number template value |
| `heat_param_template_process_values` | `mes_heat_treatment_param_template` | many process fields | See `HeatTreatmentParamTemplate` for field list |

## Photo Facts

| Fact | Table | Field | Description |
| --- | --- | --- | --- |
| `heat_photo_id` | `mes_heat_treatment_photo` | `id` | Photo id |
| `heat_photo_record_id` | `mes_heat_treatment_photo` | `record_id` | Parent record id |
| `heat_photo_stage` | `mes_heat_treatment_photo` | `photo_stage` | Photo stage |
| `heat_photo_file_url` | `mes_heat_treatment_photo` | `file_url` | Original image URL |
| `heat_photo_watermarked_url` | `mes_heat_treatment_photo` | `watermarked_url` | Watermarked image URL |
| `heat_photo_shoot_time` | `mes_heat_treatment_photo` | `shoot_time` | Shoot time |
| `heat_photo_upload_time` | `mes_heat_treatment_photo` | `upload_time` | Upload time |
| `heat_photo_upload_by` | `mes_heat_treatment_photo` | `upload_by` | Uploader |
| `heat_photo_source` | `mes_heat_treatment_photo` | `source` | `CAMERA` or `ALBUM` |
| `heat_photo_watermark_text` | `mes_heat_treatment_photo` | `watermark_text` | Watermark text snapshot |
| `heat_photo_remark` | `mes_heat_treatment_photo` | `remark` | Photo remark |

## Traceability Facts

| Fact | Table | Field | Description |
| --- | --- | --- | --- |
| `heat_trace_candidate_record` | `mes_heat_treatment_record` | record fields | Candidate rows from traceability query |
| `heat_trace_item_code_match` | `mes_heat_treatment_record` | `items_json[*].productCode` | JSON search exact match |
| `heat_trace_lot_match` | `mes_heat_treatment_record` | `items_json[*].batchNo/lotCode/originalLotCode` | JSON search exact match |
| `heat_trace_product_name_match` | `mes_heat_treatment_record` | `items_json` | SQL `LIKE` against JSON |
| `heat_trace_equipment_type_match` | `mes_equipment` / record snapshot | `equipment_name`, `equipment_type`, `equipment_name` | Normalized device type match |
| `heat_trace_related_overlap` | `mes_heat_treatment_record` | `coalesce(finished_time, update_time, now())` and `coalesce(started_time, created_time)` | Same-equipment time-window overlap |

## Unknowns

| Fact | Table | Field | Reason |
| --- | --- | --- | --- |
| `heat_quality_result` | UNKNOWN | UNKNOWN | No quality/inspection linkage confirmed in scanned heat-treatment chain |
| `heat_warehouse_status` | UNKNOWN | UNKNOWN | No warehouse state linkage confirmed in scanned chain |
| `heat_plc_runtime_status` | UNKNOWN | UNKNOWN | Frontend explicitly says device status is not PLC acquisition state |
| `heat_erp_product_source_table` | UNKNOWN | UNKNOWN | Product info uses `MoReceiptRequistionMapper`; exact ERP table mapping needs separate focused scan |
