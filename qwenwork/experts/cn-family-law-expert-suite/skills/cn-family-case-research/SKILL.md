---
name_en: "cn-family-case-research"
name: "婚姻家事类案检索"
displayName: "婚姻家事类案检索"
description: "按争点、法域和关键事实变量检索分层权威案例与裁判样本，提炼可参考命题、差异和样本局限。"
description_en: "Research tiered authoritative cases and judgment samples by issue, forum, and key facts, identifying usable propositions, distinctions, and sample limits."
argument-hint: "请说明争点、目标法院或地区、关键事实变量、时间范围和希望验证的裁判倾向。"
argument-hint-en: "State the issue, target court or region, key fact variables, time range, and proposition to test."
user-invocable: true
---

# 婚姻家事类案检索

读 [统一作业标准](../../references/operating-standard.md) 和 [法律权威核验](../../references/authority-baseline.md)。先由 `cn-family-statute-research` 固定请求权基础、抗辩和现行法，案例不得替代制定法。

## 来源分层

1. 最高人民法院指导性案例。
2. 人民法院案例库经审核入库案例。
3. 最高人民法院典型案例和公报案例。
4. 最高人民法院及相关高级人民法院公开裁判。
5. 目标法院同辖区、同案由、同争点样本。
6. 其他公开裁判和商业数据库结果，仅作补充观察。

## 检索路径

`争点 → 请求权/抗辩 → 法条及司法解释 → 案由 → 关键事实变量 → 法院与年份 → 正反向案例`。

婚姻家事重点变量包括关系与持续时间、子女、登记状态、出资来源、父母赠与指向、共同生活和家庭贡献、债务用途、第三人善意、签约自愿、协议履行、家暴/过错及程序阶段。

## 案例记录

每个 `case_record` 包含：来源等级、入库编号/案号、法院、裁判日期、生效/程序状态、争点、关键事实、结果、理由、关联法条、相似点、差异点、可参考命题、不可外推部分、官方链接、检索式和检索时间。

## 输出

检索策略、案例比较表、正反命题、分歧原因、对本事项的适配、样本范围和研究缺口。明确提示普通裁判样本无普遍约束力、公开样本可能不完整、“未检索到”不等于不存在；不得凭二手案例摘要编造案号或裁判理由。
