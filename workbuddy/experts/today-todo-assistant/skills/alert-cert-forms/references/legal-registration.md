# 社会组织法人登记证书 — 字段与提交

> 本文件是 `alert-cert-forms` skill 的 reference，描述**社会组织法人登记证书**（`cert_type=1`）的 K-V 字段清单、OCR ↔ proto 映射与提交前校验。
> 完整字段契约见同目录 [`tools/org_cert_update_review_input.md`](./tools/org_cert_update_review_input.md)。

## OCR 云返回字段（K-V）

`alert-ocr` 走 `cloud_cert_pipeline` 引擎（`ocr_type=0`，公有桶），云OCR 返回的 K-V 字段（示意，实际字段名以云OCR 响应为准）：

| K-V 键（云 OCR）| 说明 |
|-----------------|------|
| 证书文件URL | alert-ocr Step 1 上传后拼接的 CDN 访问链接（**非 OCR 返回，由 Skill 层记录**）|
| 有效期起 | `YYYY-MM-DD`，若识别为"长期"则可为空 |
| 有效期止 | `YYYY-MM-DD`，若识别为"长期"则应为空 |
| 是否长期 | 从原文"长期有效"/"有效期至YYYY-MM-DD"判定 |
| 业务主管单位 | 自由文本 |
| 业务主管单位所在地 | 自由文本 |
| 业务范围 | 自由文本（可能较长）|

## K-V → proto 字段映射

对应 proto `CharitablePersonCert`（在 `update_org_cert.charitable_person` 字段块）：

| K-V 键 | proto 字段 | 类型转换 |
|-------|-----------|---------|
| 证书文件URL | `charitable_person_file_url` | string原样 |
| 有效期起 | `certificate_validity_start_date` | string `YYYY-MM-DD`；长期时空 |
| 有效期止 | `certificate_validity_end_date` | string `YYYY-MM-DD`；**长期时必须为空** |
| 是否长期 | `certificate_validity_permanent` | int32：是→ `1`、否→ `2` |
| 业务主管单位 | `competent_unit` | string 原样 |
| 业务主管单位所在地 | `competent_unit_location` | string 原样 |
| 业务范围 | `business_scope` | string 原样 |

## 用户可见的表单字段（UI 展示）

以下字段展示给用户在 UI 里核对/修改：

| 界面标签 | proto 字段 | 是否可修改 |
|---------|-----------|-----------|
| 证书文件预览 | `charitable_person_file_url` | ❌ 不可改（用户如需换图应回上传步骤）|
| 是否长期有效 | `certificate_validity_permanent` | ✅ 单选：是 / 否 |
| 有效期开始日期 | `certificate_validity_start_date` | ✅（`长期=否` 时必填）|
| 有效期结束日期 | `certificate_validity_end_date` | ✅（`长期=否` 时必填；`长期=是` 时锁空）|
| 业务主管单位 | `competent_unit` | ✅ |
| 业务主管单位所在地 | `competent_unit_location` | ✅ |
| 业务范围 | `business_scope` | ✅（多行文本框）|

## 提交前校验清单

Skill 兜底校验（UI 侧同规则）：

- ✅ `charitable_person_file_url` 非空
- ✅ `certificate_validity_permanent ∈ {1, 2}`
- ✅ `certificate_validity_permanent === 1` → **强制** `certificate_validity_end_date = ""`（`start_date` 可选）
- ✅ `certificate_validity_permanent === 2` → `start_date` + `end_date` 都非空，格式 `YYYY-MM-DD`，`end_date > start_date`，**`end_date > 今天`**（不能提交已过期证件）
- ✅ `competent_unit` / `competent_unit_location` / `business_scope` 都非空
- ✅ **覆盖语义**：`update_org_cert.cert_types` 中包含 `1` 时，本字段块 7 个字段全填（`permanent=1` 时 `end_date` 空是合法的"全填"）
