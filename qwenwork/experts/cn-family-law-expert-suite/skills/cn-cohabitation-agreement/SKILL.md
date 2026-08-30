---
name_en: "cn-cohabitation-agreement"
name: "同居协议"
displayName: "同居协议"
description: "快速提供同居协议空白模板，或为双方均无配偶的伴侣起草、审查可配置协议，处理共同生活、财产、债务、子女、退出和配套安排。"
description_en: "Quickly provide a blank Mainland China cohabitation template, or draft and review a configurable agreement for unmarried partners covering living arrangements, property, debts, children, exit, and ancillary documents."
argument-hint: "请确认双方当前婚姻状态，并说明共同生活、财产出资、子女、债务和退出安排。"
argument-hint-en: "Confirm both parties' current marital status and describe living, contributions, children, debts, and exit arrangements."
user-invocable: true
---

# 同居协议

读 [统一作业标准](../../references/operating-standard.md)、[千问交互标准](../../references/qwen-interaction-standard.md)、[安全响应](../../references/emergency-safety.md)、[法律权威核验](../../references/authority-baseline.md) 和 [同居协议模板](references/template.md)。

以该内嵌模板的关系性质、财产、开支、债务、账户、子女和效力结构为主要底稿；对数字账号、共同经营和照护补偿按真实权利及履行事实定性，不得仅靠“非赠与”“放弃撤销权”等标签规避现行法。

## 快速模板旁路

用户只要空白/快速模板，或明确要求信息不完整也先出稿时，不提问；简短提示该普通模板仅适合双方均无配偶、缺项将保留占位符后，立即输出模板正文并交付 [预生成 DOCX](assets/quick-template.docx)。用户已提供的内容必须复用；需要填充时只对预生成文件做一次定点替换。材料已明确显示一方有配偶、家暴或重大胁迫的除外。

## 首要前提

个性化或拟签署文本中，只有婚姻状态既未由用户提供、也无法从材料确定时才使用选择卡；配置 `双方均无配偶` / `一方或双方离婚手续未完成` / `暂不确定` 三项，按已知情况把推荐项排第一，平台自动追加 `其他`。只有第一项并经材料或陈述合理核验后进入普通同居协议拟签起草；其他情形先做专项法律分析。

协议不得把同居等同于婚姻，不得约定人身隶属、限制分手自由或以罚款控制交往。非婚生子女享有平等保护，不得通过协议降低其法定权益。

## 起草模块

- 同居事实、目的和双方独立身份；同居前个人财产。
- 同居期间各自所得、共同出资、共同购置/投资和证据保存。
- 房租、购房装修、共同账户、车辆、宠物、日常开销及家务照护。
- 共同经营、股权/合伙、对外债务、担保和内部结算。
- 子女抚养、费用和共同养育；调用 `cn-family-child-parenting-plan`。
- 终止通知、合理搬离期、财产盘点、折价结算、材料/钥匙/账号返还和隐私删除。
- 怀孕、生育、重大疾病、失业、死亡的衔接；继承、遗嘱、保险受益、医疗授权不能仅靠本协议完成时列配套文件。

## 输出

同居协议草案、个人/共同财产附件、出资和结算表、子女方案、退出路线、配套文件建议、待确认项和律师复核点。涉及一方有配偶、房屋/股权复杂权属、重大赠与、家暴或债权人风险时不得输出普通可签署终稿。
