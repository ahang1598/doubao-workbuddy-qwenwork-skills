# 备案号截图 LLM 视觉 Prompt 模板

> 本文件描述用 LLM 视觉能力提取**备案表截图**字段的 prompt 模板。
> **v4 更新（2026-08-23）**：改为单文件精简输入，移除 raw OCR/证据原文和独立校验中间文件。

## 执行前提（必须先满足）

- `llm_vision_record` 是识别策略标签，不是工具、脚本、函数或 MCP 名称。
- 禁止搜索 `llm_vision_record`、`LLM OCR` 或 `multimodal` 工具。
- 对用户消息中的每个唯一 `image_local_path` 调用一次图片读取能力；判断成功与否的依据是「你自己是否实际看到了图片内容（能否描述图片里有什么）」，而非返回文本里的措辞。返回文本里的 "unknown""stored at""blob" 等图片来源/存储说明不是失败信号。
- 图片载入成功后，当前模型直接执行下方 Prompt；不得继续寻找其他 OCR 能力或切换引擎。
- 图片载入成功不等于字段提取完成；只有生成下方完整 `record_input.json` 才能进入单步脚本。
- 仅在图片读取**明确返回拒绝/错误字样**（"文件不存在""格式不支持""无法呈现图片""图片内容被过滤""当前模型不支持图片"等）**且你确实看不到图片内容**时，才报告图片不可读；⛔ 严禁在已经能看到图片内容的情况下，仅凭返回文本措辞就宣称"不支持图片"；不得根据工具列表推断视觉能力不可用。

## 目标字段（两组）

### 组 1：备案表主体（必传）

用户上传的第一张图是"慈善组织公开募捐方案备案表"主体，包含以下 17 个字段：

| 字段编码 | 界面标签 | 说明 |
|---------|---------|------|
| `no` | 备案编号 | 通常以数字+字母组成，如 `52620600MJY949356HA26006`|
| `name` | 备案方案名称 / 活动名称 | 如"为山区儿童筹集学费" |
| `start_date` | 起始时间 | 规范化为 `YYYY-MM-DD` |
| `end_date` | 结束时间 | 规范化为 `YYYY-MM-DD` |
| `purpose_of_donation` | 捐赠目的 | 自由文本 |
| `purpose_use` | 募捐款物用途 | 自由文本 |
| `support_project` | 支持的慈善项目 | ≤ 100 字|
| `offsite_fundraising` | 是否开展线下异地募捐 | 界面"是"→1；"否" → 2, 未选择 → 0 |
| `recipient_scope` | 受益人范围 | ≤ 200 字 |
| `recipient_num` | 受益人预期数量 | ≤ 50 字 |
| `recipient_confirm_method` | 受益人确认方式 | ≤ 200 字 |
| `fundras_target` | 预期募集款物数额（元/年）| 保留原文本（含单位）|
| `recipient_funding_desc` | 直接或委托其他组织资助给受益人的款物 | ≤ 500 字 |
| `implement_desc` | 为提供慈善服务和实施善举项目发生的人员报酬及相关费用 | ≤ 500 字 |
| `manage_cost_desc` | 管理费用说明 | ≤ 500 字 |
| `fundraising_cost` | 募捐成本 | ≤ 800 字 |
| `remain_assets_desc` | 剩余财产处理 | ≤ 800 字 |

### 组 2：合作方信息（选传，用户可能上传第二张图）

用户可能额外上传"合作方信息"截图，包含以下 3 个字段：

| 字段编码 | 界面标签 | 说明 |
|---------|---------|------|
| `has_partner` | 是否开展合作公开募捐 | 界面"是" → 1；"否" → 2, 未选择 → 0|
| `partner_type` | 合作方类型 | "不具有公开募捐资格的组织" → 1；"个人" → 2, 未选择 → 0 |
| `partner_name` | 合作方名称/姓名 | ≤ 20 字 |

**⚠️ 界面上的其他字段不识别**：
- "填报日期"（无对应后端字段）
- "统一社会信用代码/身份证号码"（无对应后端字段）
- "其他需要说明的事项"（无对应后端字段）

## Prompt 模板

```
你是一个专业的公益活动备案信息提取助手。用户会上传 1-2 张"慈善组织公开募捐方案备案表"截图：
- 第 1 张（必有）：备案表主体
- 第 2 张（可能有）：合作方信息

请根据实际上传的图片, 准确识别以下字段, 并以严格的 JSON 格式返回。若某字段无法识别或图片中不存在, 置为 null。不要编造。

【字段值转义规则】字段值若包含 ASCII 双引号（"），在输出的 JSON 中必须转义为 `\"`（例如原文 `举办"生态管护员训练营"对生态管护员...` 须写成 `举办\"生态管护员训练营\"对生态管护员...`）；禁止在 JSON 字符串内直接写入未转义的双引号，否则 JSON 无法解析。如不便转义，也可将原文 ASCII 引号替换为中文引号「」后再输出（需保持语义一致）。

【备案表主体字段】(第 1 张图)
- no: 备案编号（数字+字母组合，如"52620600MJY949356HA26006"）
- name: 备案方案名称 / 活动名称
- start_date: 起始时间（规范化为 YYYY-MM-DD）
- end_date:   结束时间（规范化为 YYYY-MM-DD）
- purpose_of_donation: 捐赠目的
- purpose_use: 募捐款物用途
- support_project: 支持的慈善项目
- offsite_fundraising: 是否开展线下异地募捐（"是"输出 1，"否"输出 2, 未选择 输出 0）
- recipient_scope: 受益人范围
- recipient_num: 受益人预期数量
- recipient_confirm_method: 受益人确认方式
- fundras_target: 预期募集款物数额（保留原文本，含单位）
- recipient_funding_desc: 直接或委托其他组织资助给受益人的款物
- implement_desc: 为提供慈善服务和实施善举项目发生的人员报酬及相关费用
- manage_cost_desc: 管理费用说明
- fundraising_cost: 募捐成本
- remain_assets_desc: 剩余财产处理

【合作方字段】(第 2 张图，若存在)
- has_partner: 是否开展合作公开募捐（"是"→ 1，"否" → 2, 未选择 → 0）
- partner_type: 合作方类型（"不具有公开募捐资格的组织"→ 1，"个人" → 2, 未选择 → 0）
- partner_name: 合作方名称/姓名

【质量信息】
- confidence: high | medium | low（整体识别置信度，仅作提示，不替代脚本校验）
- uncertain_fields: 能看到内容但字迹模糊、存在多种可能的字段名列表
- warnings: 其他识别风险；只允许小写英文机器代码（如 `layout_uncertain`），不得放入图片原文、姓名、证件号或解释性句子
- 不生成 `raw_ocr_text`、`evidence` 或负责人姓名、身份证号、手机号等非业务信息；缺失字段由脚本根据 `fields` 计算

输出严格 JSON；`context` 使用用户选项目时已保存的真实上下文，不得从图片推断：
{
  "schema_version": "2.0",
  "strategy_id": "llm_vision_record",
  "source": {
    "image_count": 1,
    "has_partner_image": false
  },
  "context": {
    "id": 12345,
    "org_no": "100027",
    "org_name": "当前机构名称",
    "selected_old_no": "用户所选项目当前备案号",
    "quality_warning_confirmed": false,
    "confirmed_charity_org_name": ""
  },
  "fields": {
    "no": "...",
    "name": "...",
    "start_date": "YYYY-MM-DD",
    "end_date": "YYYY-MM-DD",
    "purpose_of_donation": "...",
    "purpose_use": "...",
    "support_project": "...",
    "offsite_fundraising": 0,
    "recipient_scope": "...",
    "recipient_num": "...",
    "recipient_confirm_method": "...",
    "fundras_target": "...",
    "recipient_funding_desc": "...",
    "implement_desc": "...",
    "manage_cost_desc": "...",
    "fundraising_cost": "...",
    "remain_assets_desc": "...",
    "has_partner": null,
    "partner_type": null,
    "partner_name": null
  },
  "quality": {
    "confidence": "high",
    "uncertain_fields": [],
    "warnings": []
  }
}

若某字段无法识别或图片中不存在，在 `fields` 中置为 null；不要编造。`quality_warning_confirmed` 默认 false，`confirmed_charity_org_name` 默认空字符串。编号不一致确认不写入 JSON；慈善中国机构不一致时才写入用户确认过的机构名。不要输出 JSON 之外的任何自然语言解释。
```

## 输出解析与单步处理

1. 当前模型直接生成上述 JSON（不带自然语言解释），然后用**文件写入能力**直接落盘到当前工作目录的相对路径 `record_input.json`（禁 shell 内联写文件，规则见编排层「全局落盘与脚本调用约定」）；不得写入 Skill 源码目录。
2. Agent 先在会话中比较 `fields.no` 与 `context.selected_old_no`：不一致时必须先弹窗；用户选择继续后不修改 `record_input.json`，直接进入单步脚本，识别 `no` 原样交给 UI 核对。
3. 低置信度、仅缺 `no`/`name` 或存在 `uncertain_fields` 时，先执行备案号 Skill 的质量处理；用户选择带警告继续后才将 `context.quality_warning_confirmed` 改为 true。
4. 确认完成后只运行一次 `python3 run_record_ui.py --source vision --json-file "<record_input.json>"`。脚本内联确定性校验、实时项目守卫、业务体构建和公共缓存写入。
5. 脚本返回 `PAYLOAD_BUILT` 时，stdout 已直接包含 `caller_expert_id` 与 `data_cache_id`；不得再生成、读取或删除 UI 参数文件。
6. 脚本返回 `STALE_PROJECT_CONTEXT` 表示实时 `old_no` 已不同于用户选择时的 `selected_old_no`，不得使用旧确认，必须刷新项目后重新处理。

- ⚠️ **JSON 解析失败**：允许基于已载入图片重新结构化一次，但不得重复读取图片；再次失败则提示用户重传。
- ⚠️ **`null` → 零值转换**：`null` 在输入中保留“未识别”语义，由单步脚本在构建 UI 业务体时转换为 string→`""`、int32→`0`、float→`0`。
- 若 `source.has_partner_image === false`，脚本忽略合作方字段；若为 true 但 `fields.has_partner !== 1`，脚本清空合作方类型和名称。
- 单步脚本在成功、拒绝或上下文过期时自动删除当前工作目录中的输入文件；需要用户确认时保留同一文件供更新确认标记后重试。

## 边界处理

- 图片模糊 → `confidence: low`，Skill 提示用户核对
- 图片非备案表截图 → 关键字段全空（`no` / `name` 都是 null），Skill 提示"未识别到备案信息"
- 起止时间格式多样（"2025.01.01" / "2025-01-01" / "2025年 1 月 1 日"）→ prompt 明确要求规范化为 `YYYY-MM-DD`
- 界面上有但后端不收的字段（填报日期、统一社会信用代码、其他需要说明的事项）→ **不识别，不出现在 JSON 里**
