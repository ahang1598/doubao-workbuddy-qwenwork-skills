---
name: 备案号单步输入与 fundraising_program 业务体
description: run_record_ui.py 的唯一 record_input.json 及最终 fundraising_program 字段契约。
---

# 备案号单步输入与业务体

> `record_input.json` 同时包含用户所选项目上下文、视觉字段和质量信息，是正常视觉路径唯一落盘文件。
> Agent 在脚本前比较 `fields.no` 与 `context.selected_old_no` 并完成用户确认；`run_record_ui.py` 负责确定性校验、实时项目守卫、缓存和 UI 两字段输出。
> 脚本按 `id` 实时反查 `old_no`；若不同于 `selected_old_no`，返回 `STALE_PROJECT_CONTEXT`，不写缓存。
> 下表描述最终写入公共缓存的业务体字段。

## fundraising_program 业务体字段

| 字段 | 类型 | 来源 | 取值 / 说明 |
|------|------|------|-------------|
| `id` | int | 项目上下文 | `record.list[k].fund_raising_program_id`（**UI 不显示**）|
| `old_no` | string | 单步脚本实时反查 | `run_record_ui.py` 按 `id` 获取最新 `fund_raising_program_no`；必须等于输入的 `context.selected_old_no` |
| `org_no` | string | 查询脚本 org 字段 | 首次查询脚本输出 `org.org_no` 返回的真实机构编号（AI 取出后传入业务体，UI 不显示）；⛔ **必须带引号字符串**，禁止裸数字；⛔ 禁止传空串（会被接口判必填） |
| `no` | string | 已校验 OCR / 慈善中国 | 备案编号；传识别原值，严禁用 `old_no` 覆盖；仅该字段缺失时可传 `""` 进入 UI 补录 |
| `name` | string | OCR | 活动名称 |
| `start_date` | string（`YYYY-MM-DD`）| OCR | 起止时间-起 |
| `end_date` | string（`YYYY-MM-DD`）| OCR | 起止时间-止 |
| `purpose_of_donation` | string | OCR | 捐赠目的 |
| `purpose_use` | string | OCR | 募捐款物用途 |
| `support_project` | string | OCR | 支持项目（⚠️ 脚本会去除 `-` 前的前缀，只保留项目名；AI 可传 OCR 原值如 `531100006684027126P20001-三江源守护计划`，脚本归一为 `三江源守护计划`）|
| `offsite_fundraising` | int（0/1/2）| OCR | 异地募捐 |
| `recipient_scope` | string | OCR | 受益人范围 |
| `recipient_num` | string | OCR | 受益人预期数量 |
| `recipient_confirm_method` | string | OCR | 受益人确认方式 |
| `fundras_target` | string | OCR | 预期募集款物数额（⚠️ 脚本会剔除单位/空格/千分位等非数字字符，只保留纯浮点数字符串；AI 可传 OCR 原值如 `250000.00 元`，脚本归一为 `250000.00`）|
| `recipient_funding_desc` | string | OCR | 直接或委托资助款物 |
| `implement_desc` | string | OCR | 人员报酬 |
| `manage_cost_desc` | string | OCR | 管理费用 |
| `fundraising_cost` | string | OCR | 募捐成本 |
| `remain_assets_desc` | string | OCR | 剩余财产处理 |
| `has_partner` | int（0/1/2）| OCR | 是否有合作方 |
| `partner_type` | int（0/1/2）| OCR | 合作方类型（仅 `has_partner=1` 时校验）|
| `partner_name` | string | OCR | 合作方名称 |

字段来源必须严格区分：`context.id` / `org_no` / `org_name` / `selected_old_no` 来自 Step 2 已展示的数据；视觉字段来自同一文件的 `fields`；慈善中国链接只允许由统一脚本查询并补齐空字段。不得用 `selected_old_no` 或实时 `old_no` 覆盖识别 `no`。

## 类型与确认硬约束

- `context.org_no` 必须是带引号的字符串；`context.id` 必须是项目 ID。
- `context.selected_old_no` 必须是用户选择项目时展示的备案号，不得事后改为识别值。
- `quality_warning_confirmed` 默认 false；`confirmed_charity_org_name` 默认空字符串。`no` 不一致由 Agent 在脚本前提示，用户选择继续后不修改输入文件；机构确认仍绑定当次慈善中国机构名。
- 未识别字段在 `fields` 中保留 `null`；单步脚本构建业务体时转换为 string→`""`、int32→`0`。
- `no` 与 `name` 同时为空时拒绝；仅缺其中一个时必须先完成质量提示确认。
- 日期字段非空时必须是 `YYYY-MM-DD`；枚举必须属于 `{0,1,2}`，非法值由单步脚本归一为空并生成机器警告。
- 非空 `no !== selected_old_no` 时由 Agent 在脚本前询问；用户选择继续后不修改输入文件，脚本保留识别 `no` 并写入缓存，由 UI 标红并执行提交校验。
- 实时项目审批中或实时 `old_no !== selected_old_no` 时，脚本拒绝写缓存。

## 字段值归一化（单步脚本自动处理）

`run_record_ui.py` 在生成 UI 入参前自动处理：

- **`fundras_target`**：剔除单位 / 空格 / 千分位等非数字字符，仅保留纯浮点数字符串。例：`"250000.00 元"` → `"250000.00"`；`"250,000.00 元"` → `"250000.00"`。接口要求该字段为纯浮点数字符串，禁止携带 "元" 等任何其他字符。
- **`support_project`**：去除 `-` 及其之前的前缀，仅保留项目名。例：`"531100006684027126P20001-三江源守护计划"` → `"三江源守护计划"`；`"531100006684027126P20001-1-三江源守护计划"` → `"三江源守护计划"`。

## `record_input.json` 骨架

```json
{
  "schema_version": "2.0",
  "strategy_id": "llm_vision_record",
  "source": {"image_count": 1, "has_partner_image": false},
  "context": {
    "id": 12345,
    "org_no": "100027",
    "org_name": "示例慈善机构",
    "selected_old_no": "用户选择项目时展示的备案号",
    "quality_warning_confirmed": false,
    "confirmed_charity_org_name": ""
  },
  "fields": {},
  "quality": {"confidence": "high", "uncertain_fields": [], "warnings": []}
}
```

完整 `fields` 列表以 `llm-vision-record.md` 为准。文件写到当前工作目录（cwd），用相对路径 `record_input.json`；脚本终态自动清理，只有 `USER_DECISION_REQUIRED` 时保留同一文件等待更新确认标记。
