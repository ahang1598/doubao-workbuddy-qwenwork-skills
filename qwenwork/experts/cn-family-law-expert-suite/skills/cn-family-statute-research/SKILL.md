---
name_en: "cn-family-statute-research"
name: "婚姻家事法规检索"
displayName: "婚姻家事法规检索"
description: "检索并核验婚姻家事相关法律、司法解释、行政法规、部门规范和地方办理规则的现行效力与适用。"
description_en: "Research and verify current Mainland China family-law statutes, judicial interpretations, regulations, departmental rules, and local procedures."
argument-hint: "请说明法律问题、关键事实、相关地区、时间节点和需要核验的规则或办理事项。"
argument-hint-en: "State the legal issue, key facts, relevant locations, dates, and rules or procedures to verify."
user-invocable: true
---

# 婚姻家事法规检索

先读 [法律权威核验](../../references/authority-baseline.md) 和 [统一作业标准](../../references/operating-standard.md)。

## 检索方法

1. 将用户问题拆成法律关系、争点、关键事实变量、时间与地区。
2. 先检索国家法律法规数据库、中国人大网、中国政府网、最高人民法院及主管部门官方来源。
3. 对房产、婚姻登记、户籍、公积金、税费、农村权益和地方程序按实际办理地补检。
4. 核对公布机关、文号、效力层级、施行日期、修改/废止、过渡规则和规范冲突。
5. 对每个规则执行“条文—要件—事实适配—例外—结论限度”。

## 输出

输出检索问题树、检索式、来源范围、`authority_record`、相关原文的必要短摘录、适用分析、规则冲突、未解决问题和检索时间。引用靠近结论，并提供官方可访问链接。

## 门禁

- 不把技能内置基线当作现行法证明。
- 不引用只有二手摘要且无法核对原文的规则作为核心依据。
- 网站登录、验证码或访问限制导致无法核验时，说明限制并请求人工补充，不绕过措施。
- “未检索到”不等于“不存在”；列出检索范围和局限。
- 不能核实现行有效版本时，不向下游标记为 `approved_for_drafting`。
