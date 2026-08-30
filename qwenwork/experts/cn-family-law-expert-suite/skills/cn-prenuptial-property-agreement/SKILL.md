---
name_en: "cn-prenuptial-property-agreement"
name: "婚前财产约定"
displayName: "婚前财产约定"
description: "快速提供婚前财产协议空白模板，或为拟结婚双方起草、审查可配置协议，覆盖披露、财产制、债务、住房、股权、开销、照护和履行。"
description_en: "Quickly provide a blank Mainland China prenuptial template, or draft and review a configurable agreement covering disclosure, property regime, debts, housing, equity, expenses, care, and implementation."
argument-hint: "请说明双方拟结婚时间、主要财产债务、希望采用的婚后财产模式和特别关注事项。"
argument-hint-en: "Provide the expected marriage date, main assets and debts, desired post-marriage property regime, and special concerns."
user-invocable: true
---

# 婚前财产约定

先读 [统一作业标准](../../references/operating-standard.md)、[千问交互标准](../../references/qwen-interaction-standard.md)、[法律权威核验](../../references/authority-baseline.md) 和 [婚前财产协议模板](references/template.md)。

以该内嵌模板的特定资产分类和签署结构为主要底稿；结合个案删选模块，不得把附件范本中的“未经同意即为个人债务”“签字即完成权属转移”等表述带回终稿。

## 快速模板旁路

用户只要空白/快速模板，或明确要求信息不完整也先出稿时，不提问、不运行账本或法源检索；简短提示缺项将保留占位符后，立即输出模板正文并交付 [预生成 DOCX](assets/quick-template.docx)。用户已提供的内容必须复用；需要填充时只对预生成文件做一次定点替换。快速稿状态为 `draft`，不得表述为可直接签署终稿。

## 前置条件

确认双方拟结婚、当前婚姻状态、签约自愿性、行为能力、独立审阅机会、分析基准日、财产债务披露范围和主要办理地。存在胁迫、重大隐瞒、行为能力疑问、损害第三人或疑似逃债时不出可签署终稿。

财产与债务分别调用或复用 `cn-family-asset-ledger`、`cn-family-debt-ledger` 的批准数据；法律结论须经 `cn-family-legal-consultation` 和 `cn-family-statute-research` 核验。

## 方案选择

需要个性化且用户尚未提供婚后财产模式时，选择卡配置 `原则上各自所有` / `原则上共同所有` / `分类或比例混合` 三项，并根据已知目标把推荐项排第一；平台自动追加 `其他`，不得手工添加。住房、股权、父母出资、继承赠与、共同账户、开销与照护可用一张多选卡；单次总问题不得超过四个。

## 起草重点

- 婚前财产、债务及披露附件；原物、收益、孳息、替代物、增值和负担。
- 婚后工资、奖金、经营投资、继承赠与等采用各自、共同或混合模式。
- 住房首付、贷款、装修、加名、父母出资、未来购房和不能过户的替代机制。
- 公司股权/合伙份额、控制权、分红、增值、代持、融资和第三人文件。
- 债务、担保、共同意思与债权人知悉；区分内部承担与外部效力。
- 家庭开销、共同账户、重大支出、育儿家务照护及收入变化调整。
- 结婚未实现/长期推迟、重大财产变化、清单更新、变更、通知、争议和配套登记公证。

不得限制结婚或离婚自由、限制人身自由、预先剥夺法定救济、机械货币化情感或明显损害未成年人利益。

## 输出

主协议草案、完整披露附件、选用/删除条款说明、待确认项、所需第三人同意、登记/公证/公司程序清单和律师复核点。状态默认为 `draft` 或 `review_required`。
