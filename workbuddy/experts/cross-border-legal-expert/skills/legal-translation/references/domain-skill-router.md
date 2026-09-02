# 领域术语技能路由表

本文件用于法律翻译总控技能在翻译、审校、起草和双语对照任务中选择领域术语判断模块。

## 默认规则

1. 只要任务涉及法律翻译、法律英文审校、术语统一或双语法律文书, 先启用 `foreign-legal-english-term-precision`。
2. 如果文本具有明确专业领域, 再启用 1-2 个领域技能。
3. 如果文本跨领域, 以“文书主任务”为主技能, 其他技能只用于相关术语局部判断。
4. 不因为出现单个关键词就机械触发; 必须确认该词在当前文本中承担法律功能。

## 路由矩阵

| 用户任务或文本线索 | 应启用技能 | 典型术语 | 不应误触发 |
|---|---|---|---|
| 普通合同、服务协议、买卖协议、保密协议 | `civil-law-private-rights-translator` | force majeure, consideration, breach, limitation, liability, privacy, personal data | 纯商务润色、营销翻译 |
| 起诉状、答辩状、判决、仲裁申请、程序通知 | `procedure-litigation-term-mapper` + `foreign-legal-english-term-precision` | plaintiff, defendant, respondent, service, jurisdiction, judgment, award, appeal | 实体合同条款解释 |
| 公司章程、股东会/董事会决议、投资协议、上市披露 | `commercial-corporate-finance-translator` | company law, registered capital, board of directors, board of supervisors, IPO, disclosure, fund | 普通商业介绍 |
| 提单、海运合同、保险合同、贸易融资单证 | `commercial-instruments-maritime-insurance-translator` | bill of lading, negotiable instrument, marine salvage, collision, insurance contract | 一般物流宣传文案 |
| 刑事判决、起诉书、引渡材料、刑事合规报告 | `criminal-law-elements-offenses-translator` | mens rea, actus reus, felony, misdemeanor, principal, accomplice, burglary, robbery | 民法中的 principal 或普通 crime 新闻翻译 |
| 涉美制裁、长臂管辖、域外适用、阻断法、301 条款 | `extraterritorial-rule-of-law-translator` | long-arm jurisdiction, minimum contacts, effects test, blocking statute, tariff, Section 301 | 普通国际贸易介绍 |
| 多领域复杂文本 | 主领域技能 + 必要辅助技能 | 公司涉诉、刑民交叉、涉外制裁合规 | 一次性启用全部技能 |

## 组合调用建议

- 涉外诉讼文书: `foreign-legal-english-term-precision` + `procedure-litigation-term-mapper`
- 跨境商事合同: `foreign-legal-english-term-precision` + `civil-law-private-rights-translator` + `commercial-corporate-finance-translator`
- 公司章程/决议: `foreign-legal-english-term-precision` + `commercial-corporate-finance-translator`
- 海运保险争议: `commercial-instruments-maritime-insurance-translator` + `civil-law-private-rights-translator` + `procedure-litigation-term-mapper`
- 刑事涉外材料: `criminal-law-elements-offenses-translator` + `procedure-litigation-term-mapper`
- 涉美制裁/长臂管辖备忘录: `extraterritorial-rule-of-law-translator` + `commercial-corporate-finance-translator`

## 负面触发

以下情形不启用本法律翻译体系:

- 普通英文润色、摘要、营销文案, 没有法律术语或法律文书属性。
- 单纯法律咨询、合同风险审查、法律研究, 用户没有要求翻译、审校、起草英文版或双语对照。
- 用户只是问“这个法律制度是什么”, 不要求英文术语选择或文本产出。
- 用户要求创建、安装、评估 skill, 应走 skill 创建/评估流程。

## 输出路由记录

交付报告中记录:

```text
触发的领域技能:
- foreign-legal-english-term-precision: 通用术语和角色称谓一致性
- procedure-litigation-term-mapper: 送达、管辖、裁判词审校
```

如果某个相邻技能没有启用, 但文本中存在边界词, 记录为:

```text
未启用但已排除:
- criminal-law-elements-offenses-translator: 文中 accused 仅作民事投诉中的普通描述, 非刑事程序身份
```
