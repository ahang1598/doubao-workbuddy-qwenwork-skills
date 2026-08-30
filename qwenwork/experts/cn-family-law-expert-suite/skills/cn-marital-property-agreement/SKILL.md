---
name_en: "cn-marital-property-agreement"
name: "婚内财产约定"
displayName: "婚内财产约定"
description: "快速提供婚内财产协议空白模板，或为已婚夫妻起草、审查可配置协议，处理既有与未来财产、债务、开销、贡献、第三人和登记履行。"
description_en: "Quickly provide a blank Mainland China marital property template, or draft and review a configurable agreement for existing and future assets, debts, expenses, contributions, third parties, and implementation."
argument-hint: "请说明结婚时间、现有财产债务、拟调整的财产归属、原因以及是否已有争议或债权人。"
argument-hint-en: "Provide the marriage date, existing assets and debts, intended changes, reasons, and any disputes or creditors."
user-invocable: true
---

# 婚内财产约定

读 [统一作业标准](../../references/operating-standard.md)、[千问交互标准](../../references/qwen-interaction-standard.md)、[法律权威核验](../../references/authority-baseline.md) 和 [婚内财产协议模板](references/template.md)。

以该内嵌模板的特定资产分类和签署结构为主要底稿；必须先区分维持性质、确认份额与实际分割/赠与/转让，不能用“自签字日起归某方”掩盖登记、贷款、债权人或赠与性质问题。

## 快速模板旁路

用户只要空白/快速模板，或明确要求信息不完整也先出稿时，不提问、不运行账本或法源检索；简短提示缺项将保留占位符后，立即输出模板正文并交付 [预生成 DOCX](assets/quick-template.docx)。用户已提供的内容必须复用；需要填充时只对预生成文件做一次定点替换。快速稿状态为 `draft`，不得表述为可直接签署终稿。

## 前置门禁

确认婚姻关系存续、双方真实自愿、行为能力、披露范围、目的、当前债权人/执行、未成年人和第三人权利。发现控制/胁迫、隐匿转移挥霍、伪造债务、明显无偿单边转移且影响债权人、重大权属冲突时停止终稿并升级。

必须使用 `cn-family-asset-ledger` 和 `cn-family-debt-ledger` 的逐项数据；不得用概括条款替代现有资产债务清单。

## 模式与模块

需要个性化且用户尚未提供调整范围时，选择卡配置 `仅调整未来所得` / `同时分割部分既有财产` / `全面重设财产与债务安排` 三项，并根据已知目标把推荐项排第一；平台自动追加 `其他`。住房、股权、父母出资、共同账户、开销照护、既有结算、继承赠与和保险可按主题用多选卡，单次总问题不得超过四个。

## 专项审查

- 既有共同财产是实际分割、确认份额，还是只约定未来归属。
- 房屋加名/去名、赠与、过户、抵押贷款、税费和未登记状态；不承诺签字即发生物权变动。
- 债权人知悉证据、对外效力、撤销风险、担保和执行。
- 婚内共同账户收支、家庭开销垫付、家务育儿照护、协助经营、欠付和结算基准日。
- 未来开销与扶养义务、子女利益及双方基本生活保障的衔接。
- 与遗嘱、赠与、公司章程/股东协议、保险受益、信托和既有协议的冲突。

## 输出

婚内财产协议草案、资产债务附件、既有结算表、变更登记/债权人同意/公司程序清单、条款选择说明、待确认项和律师复核点。未完成披露、权属或债权人分析时不得标记 `final`。
