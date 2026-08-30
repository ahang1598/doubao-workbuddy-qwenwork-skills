---
name_en: "cn-family-law-orchestrator"
name: "婚姻家事法律总编排"
displayName: "婚姻家事法律总编排"
description: "优先识别快速模板请求，并按关系、目标、法域、阶段、风险和交付物组织婚姻家事套件工作流。"
description_en: "Prioritize quick-template requests, then route Mainland China family-law work by relationship, goal, jurisdiction, stage, risk, and deliverable."
argument-hint: "请说明关系状态、希望解决的问题、所在地、是否有子女、材料情况和期望交付物。"
argument-hint-en: "Describe the relationship, goal, location, children, available materials, and desired deliverable."
user-invocable: true
---

# 婚姻家事法律总编排

先读 [统一作业标准](../../references/operating-standard.md)、[千问交互标准](../../references/qwen-interaction-standard.md) 和 [安全响应](../../references/emergency-safety.md)。

## 先判定交付模式

先读取用户提示词、对话和已授权材料建立 `known_fields`，不得重新获取其中已有信息。按千问交互标准直接判定 `quick_template / working_draft / reviewed_deliverable`；不得把“先问目标和安全”设为每次请求的固定首轮。

- 用户只要模板：不提问，直接路由到对应协议技能的 `assets/quick-template.docx`；已提供部分信息时按现有信息一次填充，缺项留占位符。
- 用户要求工作草案：只有无法用占位符处理且会改变核心条款时才提问；单次最多 4 个问题。
- 用户明确要求审查级、拟签署或正式成果：才进入完整事实、证据、法律和质量门禁链。

随后识别：

- 关系：拟结婚、已婚、登记离婚准备、同居、家庭共有、成年意定监护或其他。
- 目标：咨询、信息梳理、方案比较、协议起草、协议审查、正式文档或质量检查。
- 法域：常住地、婚姻登记地、财产所在地、公司注册地、子女生活地和实际办理地。
- 复杂度：普通家庭资产、公司股权/合伙份额、农村权益、境外或受限资产。
- 风险：胁迫/家暴、未成年人危险、资产转移、债权人受损、行为能力、必要主体缺失和第三人权利。

对复杂任务输出 `matter_id`、当前状态、已确认事实、缺口、拟调用技能、先后顺序、阻断项、人工复核点和下一步；快速模板请求直接交付，不先展示内部路由计划。

## 路由表

1. 信息不足但用户只要模板：不得调用访谈，直接按 `quick_template` 交付。
2. 个性化结果存在真正阻断缺口：才调用“家事事项访谈与材料清单”（`cn-family-matter-intake`）。
3. 材料较多或需要流水分析：调用“家事材料解析、银行流水分析与证据账本”（`cn-family-document-evidence`）。
4. 需要财产、债务、子女专题：分别调用 `cn-family-asset-ledger`、`cn-family-debt-ledger`、`cn-family-child-parenting-plan`。
5. 法律问题或起草约束：调用 `cn-family-legal-consultation`；法规按争点调用 `cn-family-statute-research`，只有裁判样本会影响判断时调用 `cn-family-case-research`。
6. `working_draft` 可用占位符起草；只有拟签署成果才要求关系、主体和关键事实达到完整起草条件。
7. 动态正式文档调用 `cn-family-deliverable-builder`；`reviewed_deliverable` 交付前必须调用 `cn-family-agreement-quality-gate`。未修改的预生成空白模板不重复生成或重复质检。

## 硬边界

- 关系类型未确认，不调用正式协议技能。
- 同居一方有配偶，不按普通双方均无配偶的同居协议生成终稿。
- 紧急人身或儿童风险优先安全响应；不推动双方共同签约。
- 疑似逃债、转移财产、虚假离婚或伪造债务时停止正式起草。
- 未成年人自有财产、行为能力争议、必要权利人缺席或重大第三人权益必须转人工复核。
- 意定监护起草前必须确认委托人当前具有完全民事行为能力、拟任监护人明确同意，并专项核验启动证据和监督机制。
