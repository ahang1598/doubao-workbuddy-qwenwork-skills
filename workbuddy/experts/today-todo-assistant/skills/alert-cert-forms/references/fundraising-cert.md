# 慈善组织公开募捐资格证书 — 字段与提交

> 本文件是 `alert-cert-forms` skill 的 reference，描述**慈善组织公开募捐资格证书**（`cert_type=2`，仅公募机构会有）的 K-V 字段清单、OCR ↔ proto 映射与提交前校验。
> 完整字段契约见同目录 [`tools/org_cert_update_review_input.md`](./tools/org_cert_update_review_input.md)。

## OCR 云返回字段（K-V）

`alert-ocr` 走 `cloud_cert_pipeline` 引擎（`ocr_type=0`，公有桶），云 OCR 返回的 K-V 字段（示意）：

| K-V 键（云 OCR）| 说明 |
|-----------------|------|
| 证书文件URL | alert-ocr Step 1 上传后拼接的 CDN 访问链接（**非 OCR 返回，由 Skill 层记录**）|
| 有效期起 | `YYYY-MM-DD` |
| 有效期止 | `YYYY-MM-DD`，若识别为"长期"则应为空 |
| 是否长期 | 从原文判定 |

## K-V → proto 字段映射

对应 proto `CharitablePublicCert`（在 `update_org_cert.charitable_public` 字段块）：

| K-V 键 | proto 字段 | 类型转换 |
|-------|-----------|---------|
| 证书文件URL | `charitable_public_file_url` | string 原样 |
| 有效期起 | `charitable_public_start_date` | string `YYYY-MM-DD`；长期时空 |
| 有效期止 | `charitable_public_end_date` | string `YYYY-MM-DD`；**长期时必须为空** |
| 是否长期 | `charitable_public_permanent` | int32：是 → `1`、否 → `2` |

## 用户可见的表单字段（UI 展示）

| 界面标签 | proto 字段 | 是否可修改 |
|---------|-----------|-----------|
| 证书文件预览 | `charitable_public_file_url` | ❌ 不可改（用户如需换图应回上传步骤）|
| 是否长期有效 | `charitable_public_permanent` | ✅ 单选：是 / 否 |
| 有效期开始日期 | `charitable_public_start_date` | ✅（`长期=否` 时必填）|
| 有效期结束日期 | `charitable_public_end_date` | ✅（`长期=否` 时必填；`长期=是` 时锁空）|

## 提交前校验清单

- ✅ `charitable_public_file_url` 非空
- ✅ `charitable_public_permanent ∈ {1, 2}`
- ✅ `charitable_public_permanent === 1` → **强制** `charitable_public_end_date = ""`
- ✅ `charitable_public_permanent === 2` → `start_date` + `end_date` 都非空，格式 `YYYY-MM-DD`，`end_date > start_date`，**`end_date > 今天`**（不能提交已过期证件）
- ✅ **覆盖语义**：`update_org_cert.cert_types` 中包含 `2` 时，本字段块 4 个字段全填（`permanent=1` 时 `end_date` 空是合法的"全填"）

## 触发范围提示

仅**公募机构**（`institution_type == 1`）会产生本类型证件预警。非公募机构（`institution_type == 2`）的 `cert_warning` 里不会出现 `cert_type == 2`，Skill 不应主动提示用户上传本类证件。
