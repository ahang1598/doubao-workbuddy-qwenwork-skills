---
name_en: "cn-family-child-parenting-plan"
name: "子女抚养与共同养育方案"
displayName: "子女抚养与共同养育方案"
description: "以最有利于未成年人为核心，设计直接抚养、费用、探望、教育医疗、重大决定、信息共享和变化处理方案。"
description_en: "Design a child-centered parenting plan covering primary care, support, contact, education, medical care, major decisions, information sharing, and change management."
argument-hint: "请说明子女年龄、目前生活照护、健康就学、父母居住工作、费用和希望的探望安排。"
argument-hint-en: "Describe each child's age, current care, health and schooling, parents' living and work arrangements, expenses, and desired contact schedule."
user-invocable: true
---

# 子女抚养与共同养育方案

读 [统一作业标准](../../references/operating-standard.md)、[千问交互标准](../../references/qwen-interaction-standard.md)、[安全响应](../../references/emergency-safety.md) 和 [法律权威核验](../../references/authority-baseline.md)。

## 原则

以最有利于未成年人、稳定照护、发展需求和安全为中心。不得把抚养费、探望或子女权益作为对另一方的惩罚或财产交换；不得让父母处分子女自有财产或预先放弃子女法定权利。

## 模块

- 子女身份、年龄、健康、就学、长期居住、既有照护和特殊需求。
- 直接照护、日常作息、交接时间地点、接送责任和迟到/取消处理。
- 抚养费基数、金额、支付日、账户、调整机制、截止条件和逾期凭证。
- 教育、医疗、保险、兴趣活动及大额费用的范围、比例、事前沟通、紧急例外和凭证。
- 工作日、周末、节假日、寒暑假、生日和线上联系；婴幼儿或远距离情形采用适龄安排。
- 迁居、转学、重大医疗、出境、证件保管和重大决定。
- 学校/医疗信息共享、隐私、照片发布和不得贬损/利用子女传话。
- 紧急情况、临时替代照护、家暴或不安全探望、监督探望和恢复条件。
- 随年龄、健康、学校、父母工作/居住变化的定期复审和争议解决。

## 方法

先建立 `child_record` 和父母可执行的时间/费用事实。只有存在真实且重要的替代安排时才形成最多三套方案；已有明确共识时直接形成一套可执行方案。不要用抽象“随时探望”“费用各半”代替可执行的时间、范围、审批和凭证规则。

## 输出

子女情况摘要、必要的方案比较或单一方案、月度基础费用测算、特殊费用表、年度探望日历、交接规则、重大决定矩阵、信息共享、变化/紧急机制、风险和律师复核点。家暴、抢夺藏匿子女、出境风险、拒绝必要医疗或子女安全问题必须升级人工处理。
