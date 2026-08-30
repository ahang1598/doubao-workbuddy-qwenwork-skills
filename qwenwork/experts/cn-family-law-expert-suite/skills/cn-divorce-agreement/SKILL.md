---
name_en: "cn-divorce-agreement"
name: "离婚协议"
displayName: "离婚协议"
description: "快速提供离婚协议空白模板，或为自愿登记离婚起草、审查可执行协议，覆盖子女、财产、债务、补偿、登记节点和履行路线。"
description_en: "Quickly provide a blank Mainland China divorce-agreement template, or draft and review an executable agreement covering children, assets, debts, compensation, registration, and implementation."
argument-hint: "请说明双方是否均同意登记离婚、子女、主要财产债务、分配共识和计划办理地。"
argument-hint-en: "State whether both parties agree to registered divorce, the children, main assets and debts, allocation consensus, and intended registration location."
user-invocable: true
---

# 离婚协议

读 [统一作业标准](../../references/operating-standard.md)、[千问交互标准](../../references/qwen-interaction-standard.md)、[安全响应](../../references/emergency-safety.md)、[法律权威核验](../../references/authority-baseline.md) 和 [离婚协议模板](references/template.md)。

模板采用用户范本的身份、子女、财产、债务、责任和签署主结构；起草时以该内嵌模板为主要条款底稿，但必须保留其登记、第三人、证据、失败替代和子女变化机制。不得恢复模板已经删除的概括免责、全事项违约金或含混抚养期限。

## 快速模板旁路

用户只要空白/快速模板，或明确要求信息不完整也先出稿时，不提问、不要求先建立资产、债务或子女方案；简短提示缺项将保留占位符后，立即输出模板正文并交付 [预生成 DOCX](assets/quick-template.docx)。用户已提供的内容必须复用；需要填充时只对预生成文件做一次定点替换。快速稿状态为 `draft`，不代表双方已满足登记离婚条件。

## 适用门

仅适用于双方真实、自愿地准备通过婚姻登记机关协议离婚。一方不同意、婚姻效力有争议、存在紧急保全/家暴/子女抢夺、需法院裁判或无法共同申请时，转诉讼/安全法律路径，不生成登记离婚终稿。

拟签署或审查级文本须先取得或建立资产、债务和子女方案；快速模板和工作稿可以保留清晰占位符，但不得用“双方无其他财产债务”替代完整核对。

## 起草顺序

1. 双方身份、婚姻登记、真实自愿、办理地和登记流程基准日。
2. 子女直接抚养、费用、探望、教育医疗、重大决定和变化机制；调用 `cn-family-child-parenting-plan`。
3. 每项财产的归属、折价、交付、过户、贷款、税费、期限、先后顺序和失败替代。
4. 每项债务的对外状态、内部承担、清偿、担保解除、债权人同意和追偿。
5. 家务劳动补偿、经济帮助、损害赔偿或其他补偿；不涉及也要核对而非臆断放弃。
6. 住房腾退、物品、账户、证照和材料移交；登记前、取得离婚证时和离婚后的生效/履行节点。
7. 遗漏或隐瞒财产债务、违约、通知、争议解决和协助履行。

## 专项门禁

- 内部债务分担不得写成当然免除对债权人的责任。
- 明显单边转移且存在债权人时提示撤销风险并转律师。
- 房屋、车辆、股权、贷款、保险必须有办理动作、材料、责任人、期限和替代方案。
- 父母不得处分子女自有财产或不当放弃子女权益。
- 2025 年修订婚姻登记规则及当地最新材料/流程必须在当前任务核验。

## 输出

离婚协议草案、子女方案、财产债务附件、付款/过户/交接表、登记办理清单、条款选项记录、待确认项和律师复核点。
