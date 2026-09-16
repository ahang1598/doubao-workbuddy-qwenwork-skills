---
name: 51shebao-hr-tools
description: 51社保政策查询技能，用于查询中国城市社保与公积金的缴费基数、比例、办理截止日、最低工资、社平工资与产假天数，检索社保政策原文，并读取政策分析报告
version: "1.0.0"
author: 51社保
---

# 51社保政策查询 / 51Shebao Policy Search

本 Skill 只提供社保政策查询与政策原文检索能力，不办理增减员，不接收员工花名册，不提交工单，不执行任何写操作。

This Skill only provides social insurance and housing fund policy queries, policy-source search, and policy report reading. It does not process enrollment changes, accept employee rosters, submit service tickets, or perform any write operation.

## 认证说明 / Authentication

- 首次连接或授权失效时，WorkBuddy 会打开 51社保授权页面。用户通过手机号和短信验证码登录并确认授权。
- WorkBuddy 安全保存 OAuth 凭证，并在刷新令牌有效期内自动续期；无法续期时应引导用户重新连接，不要要求用户在对话中提供短信验证码。
- On first connection, or when authorization can no longer be refreshed, WorkBuddy opens the 51Shebao authorization page. The user signs in with a mobile number and SMS verification code and grants access.
- WorkBuddy stores and refreshes the OAuth credentials. If renewal fails, ask the user to reconnect. Never ask the user to disclose an SMS verification code in chat.

## 工具选用指引 / Which tool to use

1. 用户问的是「某城市某年的缴费基数上下限、缴费比例、办理截止日、最低工资、社平工资、产假」等**参数型问题** → `query_policy_config_list` 查 `policy_id`，再 `query_policy_config` 取参数与政策依据。
2. 用户问的是「某城市/省份某项社保政策的**原文规定**」（如“广东加班费怎么规定的”“上海生育津贴政策原文”）→ 直接用 `query_policy_notes` 按维度检索政策原文。
3. 用户要求「整体了解一下 51社保政策库覆盖了哪些城市/主题」→ `query_policy_catalog` 看可检索范围（domains/topics/regions），再据此构造 `query_policy_notes` 检索条件。
4. 用户问「最新的政策分析报告/宏观结论」→ `query_policy_report` 读正式政策分析报告（无参数）。
5. 城市、年度、参保身份或政策事项会影响答案且用户没说清楚时，先向用户确认，不要自行猜测。

For parameter-type questions (limits, rates, deadlines, wages, leave days), use `query_policy_config_list` then `query_policy_config`. For policy-source retrieval (original legal text by region/domain/topic), use `query_policy_notes`, and optionally `query_policy_catalog` first to learn supported dimensions. Use `query_policy_report` to read the formal analysis report. Ask for missing city, year, identity, or topic details when they materially affect the answer.

## 可用工具 / Available tools

### query_policy_config_list - 查找政策配置

列出某个城市、年度和参保身份下可用的政策配置，返回后续查询需要的 `policy_id`。Lists policy configurations and returns the `policy_id` required for the detailed query.

| 参数 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| regionName | string | ✅ | 城市名，如“北京”“成都”“上海” |
| year | integer | - | 政策年度；当前支持 2025、2026，不传默认 2026 |
| identity | string | - | 参保身份或医保档位，如“深户-医疗一档”；不传返回全部身份档 |

如果返回多个身份档位，应结合用户情况选择；无法判断时列出差异并询问用户。此工具不返回具体险种比例或截止日数值。

### query_policy_config - 获取政策参数和依据

根据 `policy_id` 获取缴费基数、单位/个人比例、截止日、最低工资、社平工资、产假等参数以及政策证据。Returns policy parameters and supporting evidence for a selected `policy_id`.

| 参数 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| policyId | string | ✅ | `query_policy_config_list` 返回的 `policy_id`，如 `110100_social_base_2026` |
| identity | string | - | 参保身份；同一城市存在多档时应传入，不传取该 policy_id 默认档 |

返回值含 `evidence` 数组，每项 `{dim, title, url, level, status}`，主证据在前；social 档附带社平/最低/产假/补偿依据。无证据命中时 evidence 为空数组且 `confidence=low`。

### query_policy_catalog - 查看政策库目录

读取政策库“可检索范围”：政策库规模 + domain/topic/region 取值字典 + 内容指纹。无参数。Reads the policy library catalog: scale, supported domains/topics/regions, and a content fingerprint. No parameters.

返回 JSON：`{version, generated_at, scale{notes, by_level, by_status}, domains[], topics[], regions{city[], province[], national}}`。在“查政策原文”前先调用本工具可感知可检索维度与覆盖范围，避免构造出库内不支持的检索条件。

### query_policy_notes - 检索政策原文

按维度检索政策原文（结构化检索），返回命中的政策条目。Searches original policy text by structured dimensions.

| 参数 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| region_level | string | - | 层级：all / city / province / national，默认 all |
| region | string | - | 城市名或省名（与 region_level 匹配；all 时匹配 city 或 province） |
| domain | string | - | 政策分类精确匹配：薪酬 / 社保 / 用工 / 福利 |
| topic | string[] | - | 事项数组（OR），如 `["调基", "公积金缴存"]`；取值见 query_policy_catalog.topics |
| status | string | - | 现行有效（默认）/ all（含已失效） |
| asof | string | - | 日期 `YYYY-MM-DD`，按 [effective, expiry) 时间窗口判定现行（优先于 status） |
| year | integer | - | 政策针对年度 |
| query | string | - | 标题+正文子串（轻量全文检索） |
| limit | integer | - | 返回条数上限，最大 50，默认 20 |
| include_content | boolean | - | true 时附正文全文，默认 false |

返回 JSON：`{count, not_found, hits[], upper_hits[]}`。单层无命中时 `upper_hits` 给出上层候选（city→省→national），`not_found=true` 表示“当前层级未收录但可向上层找依据”。回答“XX 政策原文怎么规定的”时优先用本工具。

### query_policy_report - 读取政策分析报告

读取正式政策分析报告全文（全局认知，八段结构）。无参数。Reads the formal policy analysis report. No parameters.

返回 report_latest.md 全文；若尚无正式报告则返回提示文案。适合回答“最新宏观政策趋势/分析结论”类问题。

## 数据时效与降级 / Freshness and fallback

- 参数配置返回的是**年度配置快照**（标注政策年度），政策原文检索返回的是**原文条目**（按生效窗口判定现行）。回答时区分两者，不得把快照描述为实时数据，也不要把快照参数与原文检索混为同一数据源。
- 优先展示工具实际返回的数据日期、政策年度、来源和证据链接。工具未返回更新时间时，明确写“数据更新时间未提供”，不要自行推断。
- 工具失败或返回“未收录/不存在”时，不得编造参数或原文，不得静默用其他年度/地区数据替代；说明缺口并请用户确认，或建议稍后重试。
- Annual snapshots and policy-source entries are different data sources. Clearly label year, region, level, and evidence for every result, and never fabricate or silently substitute data on failure.

## 结果解释 / Result interpretation

- `confidence: high`：已匹配到政策证据，回答时附证据标题和链接。
- `confidence: low`：参数来自配置快照但未匹配到充分证据；必须提示用户“建议结合当地最新官方口径复核”，不能表述为确定性法律结论。
- 空值表示当前数据未收录，不代表当地没有该政策或要求。
- `confidence: high` means supporting policy evidence was matched. `confidence: low` means the value comes from a configuration snapshot without sufficient evidence and must be presented with a local-authority verification notice.

## 回答模板 / Response template

- 地区 / Region（含城市与层级）
- 政策年度或生效日期 / Policy year or effective date
- 参保身份（如适用）/ Participant identity or tier (when applicable)
- 政策参数或原文要点 / Policy parameters or key points of the original text
- 数据来源与更新时间 / Data source and last-updated information
- 政策依据 / Supporting policy evidence
- 复核提示 / Verification notice

只展示与问题有关的字段，避免把完整配置或原文原样倾倒给用户。金额、比例和日期保留工具返回的原始单位与精度。

Only include fields relevant to the question. Preserve the units and precision returned by the tools.

## 隐私与安全 / Privacy and safety

- 不要向任何工具传入员工姓名、身份证号、手机号、工资明细或花名册。所有工具入参只允许城市、年度、政策事项等非个人信息。
- 本连接器只有查询能力，不代表已经完成社保申报或经办。
- 政策和参数会随地区、时间及人员身份变化；涉及实际申报或重大用工决策时，提醒用户复核最新官方文件。
- Never send names, identity numbers, mobile numbers, salary details, or employee rosters to these tools. Policy results are informational and do not mean that a filing or enrollment operation has been completed.

## 常见错误 / Common errors

- 地区未收录：请用户确认城市名称，或明确告知当前数据暂未覆盖。
- 年度不支持：说明当前支持的年度，不要用其他年度数据冒充。
- 身份档位不明确：先列出可用档位，再让用户选择。
- 检索条件超出库内维度：先调 `query_policy_catalog` 看可用 domain/topic/region 再重试。
- 服务暂时不可用：保留用户原始问题，建议稍后重试，不要编造查询结果。
- For unsupported regions, years, identity tiers, or catalog dimensions, explain the coverage gap and ask for a supported input. On temporary service failures, recommend retrying later and never fabricate a result.
