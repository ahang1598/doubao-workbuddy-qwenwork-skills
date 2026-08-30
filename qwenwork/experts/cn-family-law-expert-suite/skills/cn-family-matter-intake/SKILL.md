---
name_en: "cn-family-matter-intake"
name: "家事事项访谈与材料清单"
displayName: "家事事项访谈与材料清单"
description: "以最小必要、分轮追问的方式建立事项卡、人物关系、时间线、材料清单和事实缺口。"
description_en: "Conduct staged, minimum-necessary family-law intake and produce a matter card, relationship map, timeline, material list, and fact gaps."
argument-hint: "请说明希望解决的问题并上传已有材料；我会复用已提供信息，只追问真正阻断结果的缺口。"
argument-hint-en: "State your goal and provide available materials; the skill reuses supplied information and asks only about gaps that block the result."
user-invocable: true
---

# 家事事项访谈与材料清单

读 [千问交互标准](../../references/qwen-interaction-standard.md)、[统一作业标准](../../references/operating-standard.md)、[结构化底稿](../../references/data-contracts.md) 和 [安全响应](../../references/emergency-safety.md)。

## 先去重，再访谈

先从提示词、对话和授权材料建立 `known_fields`。已有且无实质冲突的信息不得再次询问或要求确认。

1. 用户只要空白或快速模板时不启动访谈，立即退回总编排按 `quick_template` 交付。
2. 其余请求先一次列出全部真正阻断的缺口；需要选择卡时，每题配置 2 至 4 个选项，单次最多 4 题，可按事项使用多选，平台自动追加 `其他`。
3. 只有上一批答案产生新的关键分支时才进入下一轮；不机械执行固定“第一轮、第二轮、第三轮”。
4. 后续仅处理矛盾信息、证据缺口、双方意见不一致和不能用占位符处理的履行细节。

每轮后直接更新事项卡并推进。只有用户需要审计轨迹时才输出 `已知 / 冲突 / 待核实 / 下一问必要性`，不得用流程复述延迟交付。

## 安全和资格先行

根据用户已提供的信息和材料筛查家暴、胁迫、儿童危险、自伤他伤、跟踪、设备监控、行为能力、当前配偶状态、代理权限和利益冲突。已有风险信号时按安全响应处理；没有风险迹象时不得以通用安全问卷阻断空白模板或普通工作稿。

## 输出

- `matter`：事项编号、法域、基准日、目标、交付物、截止日期、状态、负责人和批准人。
- `party`：当事人、配偶/前配偶、子女、父母、家庭成员、公司、债权人、拟任监护人和监督人。
- 人物关系图与关键时间线：结识、同居、结婚、分居、出资、购置、借款、冲突、签约和履行节点。
- 客户目标、底线、可交换项、不确定项，以及双方一致/不一致事项。
- 已收材料、缺失材料、材料用途、替代证据、待访谈人员和最迟取得时间。
- `facts_for_confirmation`：逐条让当事人确认；未经确认的保持 `party_statement` 或 `unknown`。

## 简化后的基础材料清单

按事项选择，不要求一次性全部提供：身份及关系材料；婚姻登记/离婚材料；子女出生、就学和医疗；房产、车辆、股权、存款、证券、保险、公积金；借款、担保和征信；银行/支付流水；聊天、邮件、录音录像；判决、调解书、既有协议；与履行、登记或税费有关的文件。

输出清单时解释“为什么需要、可用何种替代材料、是否必须原件、是否可先掩码”。
