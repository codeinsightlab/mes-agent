# MES Heat Treatment Capability Discovery V1

Discovery date: 2026-07-10

## Scope

This discovery extracts heat-treatment business facts from current code only.

Frontend scanned:

- `/Users/user/work/heri/ktg-mes-ui/src/router/index.js`
- `/Users/user/work/heri/ktg-mes-ui/src/api/md/heatTreatment.js`
- `/Users/user/work/heri/ktg-mes-ui/src/views/md/heatTreatment/index.vue`
- `/Users/user/work/heri/ktg-mes-ui/src/views/md/heatTreatment/detail.vue`
- `/Users/user/work/heri/ktg-mes-ui/src/views/md/heatTreatment/traceability/index.vue`
- `/Users/user/work/heri/ktg-mes-ui/src/views/md/heatTreatment/components/HeatTreatmentParameterCard.vue`
- `/Users/user/work/heri/ktg-mes-ui/src/views/md/heatTreatment/components/HeatTreatmentEvidenceCard.vue`

Backend scanned:

- `HeatTreatmentRecordController`
- `MobileHeatTreatmentController`
- `IHeatTreatmentService`
- `HeatTreatmentServiceImpl`
- `HeatTreatmentRecordMapper.xml`
- `HeatTreatmentRecordExtraMapper.xml`
- `HeatTreatmentParamRecordMapper.xml`
- `HeatTreatmentParamSubmitMapper.xml`
- `HeatTreatmentPhotoMapper.xml`
- `HeatTreatmentParamTemplateMapper.xml`
- heat-treatment DTO / VO / Entity / Enum classes
- heat-treatment SQL migration files

## Frontend Capability Entry Points

The MES admin frontend exposes these heat-treatment routes:

| Route | Frontend | User-facing purpose |
| --- | --- | --- |
| `/mes/heat-treatment/index` | `src/views/md/heatTreatment/index.vue` | Heat-treatment record management, list filters, device status, create, remark, void, delete, detail navigation |
| `/mes/heat-treatment/detail/:id` | `src/views/md/heatTreatment/detail.vue` | Single heat-treatment record detail, bound products, photos, parameters, remark, void |
| `/mes/heat-treatment/traceability` | `src/views/md/heatTreatment/traceability/index.vue` | Product batch lifecycle traceability and single-record detail drilldown |

## Backend Capability Surfaces

Admin API:

- `GET /mes/heat-treatment/list`
- `GET /mes/heat-treatment/status-options`
- `GET /mes/heat-treatment/device-status`
- `GET /mes/heat-treatment/{id}`
- `GET /mes/heat-treatment/trace`
- `GET /mes/heat-treatment/traceability`
- `GET /mes/heat-treatment/traceability/lifecycle`
- `POST /mes/heat-treatment`
- `POST /mes/heat-treatment/{id}/remark`
- `POST /mes/heat-treatment/{id}/void`
- `DELETE /mes/heat-treatment/{ids}`

Mobile / production API discovered in backend:

- `/mobile/heat-treatment/list`
- `/mobile/heat-treatment/create`
- `/mobile/heat-treatment/my-running`
- `/mobile/heat-treatment/my-recent`
- `/mobile/heat-treatment/equipment-list`
- `/mobile/heat-treatment/product-info`
- `/mobile/heat-treatment/product-info-list`
- `/mobile/heat-treatment/{id}`
- `/mobile/heat-treatment/param-template`
- `/mobile/heat-treatment/{id}/params`
- `/mobile/heat-treatment/{id}/program-no`
- `/mobile/heat-treatment/{id}/bind-item`
- `/mobile/heat-treatment/{id}/bind-items`
- `/mobile/heat-treatment/{id}/start`
- `/mobile/heat-treatment/{id}/upload-photo`
- `/mobile/heat-treatment/{id}/reminder`
- `/mobile/heat-treatment/{id}/remark`
- `/mobile/heat-treatment/{id}/finish`
- `/mobile/heat-treatment/{id}/transfer-next`
- `/mobile/heat-treatment/{id}/void`
- `/mobile/heat-treatment/{id}/cancel`
- `/mobile/heat-treatment/trace`

## Core Model

The heat-treatment module centers on one record table:

- `mes_heat_treatment_record`

Supporting fact tables:

- `mes_heat_treatment_photo`
- `mes_heat_treatment_param_submit`
- `mes_heat_treatment_param_record`
- `mes_heat_treatment_param_template`
- `mes_equipment`
- ERP product information is read through `MoReceiptRequistionMapper`; exact ERP tables are outside this frontend/admin scan except mapper references.

## Confirmed Boundaries

- Heat-treatment status truth is `HeatTreatmentStatusEnum`: `CREATED`, `RUNNING`, `FINISHED`, `TRANSFERRED`, `ENDED`, `CANCELLED`.
- Device status shown in the admin frontend is derived from heat-treatment process records and equipment master data. It is not PLC device telemetry.
- Product batch lifecycle identity is resolved by `itemCode + lotNo`, or by `recordNo` to locate one bound product batch.
- Bound product/basket data is stored inside `mes_heat_treatment_record.items_json`, not a normalized heat-treatment item table in the scanned code.
- Traceability related products are same-equipment overlapping-window products, plus matching same-batch products. They are not proof of a separate workflow relation.
- Parameter persistence is append-style: `mes_heat_treatment_param_submit` records a submit batch; `mes_heat_treatment_param_record` records per-parameter rows.

## Not Confirmed

- PLC real-time equipment state: UNKNOWN in this scan.
- Quality inspection result linkage: UNKNOWN in this scan.
- Warehouse / transfer completion outside `mes_heat_treatment_record.status`: UNKNOWN in this scan.
- Full ERP source schema for product info: partially known via mapper references, not fully mapped here.
