# 备案号流程脚本说明

## 唯一业务入口：`run_record_ui.py`

正常流程只执行此脚本一次。它读取当前工作目录（cwd）中的 `record_input.json`，在同一进程内完成：

1. schema 2.0 视觉字段校验与归一化；
2. Agent 质量/编号确认标记验证；
3. 可选慈善中国详情页查询与空字段补齐；
4. 实时项目、审批状态和 `old_no` 上下文过期守卫；
5. 业务体构建、公共缓存写入；
6. stdout 返回 `caller_expert_id`、`data_cache_id`。

```bash
python3 run_record_ui.py --source vision --json-file "<record_input.json>"
python3 run_record_ui.py --source vision --json-file "<record_input.json>" --charity-url "<详情页链接>"
python3 run_record_ui.py --source charity --json-file "<record_input.json>" --charity-url "<详情页链接>"
```

`PAYLOAD_BUILT` 前不会写 UI 参数文件。`USER_DECISION_REQUIRED` 不写缓存并保留输入文件；其他终态自动清理当前工作目录中的输入文件。

## 内部兼容模块

- `validate_record_ocr.py`：`run_record_ui.py` 导入的纯校验函数；保留旧 CLI 仅用于兼容和测试，Agent 不再单独执行。
- `build_record_ui_params.py`：提供字段归一化、实时查询和业务体构建函数；旧 CLI 保留兼容，Agent 不再单独执行。
- `fetch_charity_record.py`：由统一脚本按需导入；Agent 不再单独执行或生成慈善中国结果文件。

## 环境依赖

- Python 3.10+
- `pip install -r requirements.txt`（`requests`）

## 慈善中国查询触发条件

只有用户已经提供有效详情页链接并明确选择查询或补齐时，才向统一脚本传 `--charity-url`。OCR 低置信度、字段缺失或 `uncertain_fields` 非空不能自动触发查询。

## 输出字段映射（脚本字段 → `update_org_record_number` proto）

### ✅ 直接映射（15 个）

| 脚本字段 | proto 字段 | 说明 |
|---------|-----------|-----|
| `scheme_name` | `name` | 备案方案名称 |
| `scheme_no` | `no` | 备案号编号 |
| `start_date` | `start_date` | `YYYY-MM-DD` |
| `end_date` | `end_date` | `YYYY-MM-DD` |
| `purpose_of_donation` | `purpose_of_donation` | 捐赠目的 |
| `purpose_use` | `purpose_use` | 募捐款物用途 |
| `recipient_scope` | `recipient_scope` | 受益人范围 |
| `recipient_num` | `recipient_num` | 受益人预期数量 |
| `recipient_confirm_method` | `recipient_confirm_method` | 受益人确认方式 |
| `fundras_target` | `fundras_target` | 预期募集款物数额（保留原文本，含单位）|
| `recipient_funding_desc` | `recipient_funding_desc` | 直接或委托资助款物 |
| `implement_desc` | `implement_desc` | 人员报酬及相关费用 |
| `manage_cost_desc` | `manage_cost_desc` | 管理费用说明 |
| `fundraising_cost` | `fundraising_cost` | 募捐成本 |
| `remain_assets_desc` | `remain_assets_desc` |剩余财产处理 |

### ✅ 转换映射（4 个，脚本已做转换）

|脚本字段 | 值 | proto 字段 | 说明 |
|---------|----|-----------|-----|
| `offsite_fundraising` | `0` /`1` / `2` | `offsite_fundraising` | 是否线下异地募捐（0=未选择, 1=是，2=否）|
| `has_partner` | `0` / `1` / `2` | `has_partner` | 是否合作募捐（0=未选择, 1=是，2=否）|
| `partner_type` | `0` / `1` / `2` | `partner_type` | ⭐ **直接从 `<select name="aaex9167" value="X">` 读取**，字典 AAEX9167：`0`=未选择、`1`=不具有公开募捐资格的组织、`2`=个人，与 proto 语义一致。若 `has_partner=2` 或 select value 非法/缺失则不返回该字段，由 UI 让用户手选 |
| `partner_name` | 组织/个人姓名 | `partner_name` | 合作方名称/姓名 |

### ⚠️ 特殊映射 —— `support_project`

| 脚本字段 | proto 字段 | 说明 |
|---------|-----------|-----|
| `support_project` | `support_project` | ⚠️ 慈善中国页面上的"支持项目"字段可能与 `scheme_name` 相同也可能不同，UI 侧应允许用户核对/修改 |

### 脚本内部辅助字段（不进入 proto）

以下字段仅在统一脚本内部用于解析和一致性判断，不输出到 UI 参数：

| 脚本字段 | 用途 |
|---------|-----|
| `org_name` | ⭐ **机构一致性比对**：与首次查询脚本输出 `org.org_name` 比对（`get_org_detail` 已封装进脚本、AI 禁裸调），不一致时警告用户（但允许继续，因为可能是同一机构的不同表述）|
| `unified_social_credit_code` | 辅助机构一致性比对（当前机构的统一社会信用代码）|
| `partner_credit_code` | UI 展示辅助（用户视角"合作方是哪个机构"） |
| `filing_date` | 展示"备案日期"（辅助信息）|
| `legal_representative` | 展示"法定代表人"（辅助信息）|
| `success` / `_source` / `_schema_version` / `_page_id` | 慈善中国解析函数的内部追踪信息；统一脚本不把它们写入 UI 业务体 |

### 🚫 proto 有但脚本可能不返回

| proto 字段 | 说明 |
|-----------|-----|
| `partner_type` | 极小概率 `<select name="aaex9167">` 的 `value` 属性为空（如后台脏数据），此时脚本不写该字段——**UI 兜底**让用户手选 |

## 已知限制

1. **依赖慈善中国当前 DOM 结构**：网站改版会使脚本失效，因此只能用于用户显式提供链接并选择查询的路径，不作为图片主路径
2. **`support_project` 可能与 `scheme_name` 重复**：慈善中国页面上有些方案两者本来就一样，UI 侧应允许用户核对/修改
3. **`_extract_inputs` 支持 `<input>`/`<textarea>`/`<select>` 三种元素**：其中 `<select>` 的选中值直接从 select 标签的 `value` 属性读取（无需解析 `<option>` 列表），字典解释由后端映射，Skill 直接透传即可
4. **网络访问**：需要外网能访问 `cszg.mca.gov.cn`；15-30 秒超时
5. **不做浏览器自动化**：只走 HTTP + HTML 解析，不引入 selenium/playwright
