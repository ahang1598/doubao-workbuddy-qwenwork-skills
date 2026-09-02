---
name: org_cert_update_review 业务体结构（build_cert_ui_params.py 输入）
description: build_cert_ui_params.py 的 --json-file / stdin 输入格式，即 org_cert_update_review 业务体（cert_types + 三块 K-V）的字段契约。
---

# org_cert_update_review 业务体结构（脚本输入格式）

> 本文件是 `skills/alert-cert-forms/references/scripts/build_cert_ui_params.py` 的 `--json-file`（或 stdin）**输入**格式的唯一字段契约。
> 输入即一份 `org_cert_update_review` 业务体 JSON，**只含本文件描述的结构，不含 `caller_expert_id` / `submit`**（那两层由脚本负责组装并写入公共缓存）。
> 字段名 / 层级 / 类型必须与下表完全一致；所有字段值从 OCR 结果 / 会话上下文逐字填入，禁止理解后改写。

## org_cert_update_review 结构

| 字段 | 类型 | 层级 | 出现条件 |
|------|------|------|----------|
| `cert_types` | array\<int\> | 顶层 | 必填；裸 int 数组，如 `[1, 3]`；**禁止**包成 `{"item":...}` 或字符串 |
| `charitable_person` | object | 顶层 | `cert_types` 含 `1` 时 |
| `charitable_public` | object | 顶层 | `cert_types` 含 `2` 时 |
| `idcard` | object | 顶层 | `cert_types` 含 `3` 时 |

块出现规则：以实际出现的块为准，逐字照搬；`cert_types` 与块一一对应（有类必有块、有块必有类）。

### charitable_person 字段

| 字段 | 类型 |
|------|------|
| `charitable_person_file_url` | string |
| `certificate_validity_start_date` | string（`YYYY-MM-DD`）|
| `certificate_validity_end_date` | string（`YYYY-MM-DD`；长期时为**空字符串 `""`**，字段保留）|
| `certificate_validity_permanent` | int（`1`=是 / `2`=否）|
| `competent_unit` | string |
| `competent_unit_location` | string |
| `business_scope` | string |

### charitable_public 字段

| 字段 | 类型 |
|------|------|
| `charitable_public_file_url` | string |
| `charitable_public_start_date` | string（`YYYY-MM-DD`）|
| `charitable_public_end_date` | string（`YYYY-MM-DD`；长期时为**空字符串 `""`**，字段保留）|
| `charitable_public_permanent` | int（`1`=是 / `2`=否）|

### idcard 字段

| 字段 | 类型 |
|------|------|
| `idcard_front` | string |
| `idcard_back` | string |
| `name` | string |
| `id_card` | string |
| `id_card_validity` | string（`YYYY-MM-DD~YYYY-MM-DD` 或 `YYYY-MM-DD~长期`）|

## 类型硬约束

- int 字段（`*_permanent`、`cert_types` 元素）必须传 JSON **数字**，禁止字符串（如 `2` 非 `"2"`）。
- 日期字段必须 `YYYY-MM-DD` 字符串；长期时对应 `end_date` 传**空字符串 `""`**（字段保留，禁止省略、禁止 `null`）。
- 4 个图片 URL 字段必须原样保留（值来自 OCR / 会话），禁止删除或改写域名。
- 所有字段值逐字填，禁止理解后改写 / 重推。

## 输入文件示例

```json
{
  "cert_types": [1, 3],
  "charitable_person": {
    "charitable_person_file_url": "https://cdn.example.com/xxx.jpg",
    "certificate_validity_start_date": "2020-01-01",
    "certificate_validity_end_date": "2030-01-01",
    "certificate_validity_permanent": 2,
    "competent_unit": "XX 市民政局",
    "competent_unit_location": "XX市 XX 区",
    "business_scope": "开展公益慈善服务..."
  },
  "idcard": {
    "idcard_front": "https://xxx.cos.ap-guangzhou.myqcloud.com/front.jpg",
    "idcard_back": "https://xxx.cos.ap-guangzhou.myqcloud.com/back.jpg",
    "name": "张三",
    "id_card": "440101198001010011",
    "id_card_validity": "2020-01-01~2030-12-31"
  }
}
```

（`charitable_public` 未完成 → 不进 `cert_types`，也不传块。注意本示例**只含 `org_cert_update_review` 业务体本身**，没有 `caller_expert_id` / `submit` —— 那两层由脚本组装。）
