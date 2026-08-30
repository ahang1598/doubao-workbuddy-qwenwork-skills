---
name_en: "cn-family-agreement-quality-gate"
name: "家事协议法律与文档质检"
displayName: "家事协议法律与文档质检"
description: "对婚姻家事协议执行主体、事实、证据、法律、数字、第三人、执行、引用、隐私和版式的发布门禁。"
description_en: "Apply a release gate to family-law agreements across parties, facts, evidence, law, numbers, third parties, implementation, citations, privacy, and rendering."
argument-hint: "请提供协议正文、全部附件、事实证据账本、法律研究和当前批准状态。"
argument-hint-en: "Provide the agreement, all attachments, fact and evidence ledgers, legal research, and current approval status."
user-invocable: true
---

# 家事协议法律与文档质检

读 [统一作业标准](../../references/operating-standard.md)、[法律权威核验](../../references/authority-baseline.md)、[结构化底稿](../../references/data-contracts.md) 和 [交付物标准](../../references/deliverable-standard.md)。质检独立于起草过程；不因文本流畅而降低证据和履行门槛。

空白快速模板只做模板结构、占位符可见性和预生成 DOCX 版式检查，并保持 `draft`；下列完整阻断检查用于个性化审查级或拟签署成果。不得因空白模板天然缺少当事人事实而拒绝交付模板。

## 阻断检查

1. 主体、身份、婚姻状态、行为能力、子女、代理权限和必要签约人完整。
2. 每一实质事实有来源，或明确标记为当事人陈述/待核实；争议事实未伪装成确定事实。
3. 资产、债务、子女、监护权限账本完整映射到正文和附件。
4. 金额、比例、日期、币种、账号掩码、面积、份额、总计、定义和附件编号一致。
5. 对内约定与对外效力、合同约束与物权登记、签约与实际履行正确区分。
6. 不侵害债权人、未成年人、共有人、继承人、被监护人或其他第三人权益。
7. 不错误承诺签字即完成房屋、车辆、股权、贷款、保险、监护或其他机构手续。
8. 子女条款符合最有利于未成年人原则并保留必要调整空间。
9. 生效、登记、交付、付款、过户、担保解除、通知和失败替代形成可执行时序。
10. 现行法规、条款、案例编号和来源已在当前基准日核验；地方口径已按办理地补检。
11. 无未解释空白、互相冲突条款、定义缺失、附件遗漏、模板残留或越权新增内容。
12. 无限制婚姻/人身自由、剥夺法定救济、胁迫性罚则或其他明显无效/高风险表述。
13. DOCX 的 OOXML 结构和正文抽取通过；动态拟签文件另需在具备能力的受控环境完成逐页视觉质检。千问办公不得为此调用 LibreOffice；未完成视觉质检时状态最多为 `review_required`。内容未变化且哈希命中既有 QA 清单的预生成模板除外。
14. 敏感信息最小化、项目隔离、普通版本掩码、对外披露有授权。
15. 当事人已确认关键事实与选择，负责中国大陆执业律师已实质复核批准。

## 协议专项

意定监护追加检查签署时完全行为能力、拟任监护人同意、书面形式、启动证据、监督、权限限制和退出替代；离婚协议追加检查现行登记流程、子女、债务外部效力和不动产/贷款时序；同居协议追加检查双方无配偶；分家析产追加检查全部必要权利人。

## 输出

输出 `passed / blocked`、逐项结果、阻断项、严重程度、修订建议、责任人、所需证据、复核方法和允许状态。任一阻断项未关闭时只能为 `draft` 或 `review_required`，不得标记 `final`。
