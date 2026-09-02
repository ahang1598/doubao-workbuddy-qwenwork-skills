---
name: criminal-pretrial-procedure-document-drafting
version: 1.0.0
name_en: criminal-pretrial-procedure-document-drafting
description: 生成刑事一审庭前会议、回避、管辖、不公开审理、被告人参加庭前会议及普通程序适用等申请文书。触发：刑事庭前程序申请、庭前会议、回避申请、管辖异议、不公开审理、普通程序建议。不触发：非法证据排除专门申请调用 criminal-illegal-evidence-exclusion-drafting；庭审发问调用 criminal-trial-questioning-evidence-outline。
---

# 刑事庭前程序文书起草

## 核心职责

按具体程序请求选择独立实体模板，说明请求、事实基础、提出时点和需法庭处理的事项；不同申请不得拼成一份万能文书。

## 适用范围

- 案件阶段：`first_instance`
- 支持文种：`pretrial_conference_application`、`recusal_application`、`jurisdiction_objection`、`closed_hearing_application`、`defendant_pretrial_participation_application`、`ordinary_procedure_recommendation`
- 输出场景：机关文书使用 `agency_submission`；内部提纲使用 `lawyer_working`；只有模板明确为家属材料时使用 `family_communication`。

## 最小输入契约

- 必需：目标文种或可识别请求、可用事实摘要或材料。
- 条件必需：只有当阶段、主体或机关无法推导且会改变法律路径时才集中补问。
- 缺失处理：草稿允许 `[待补：字段]`；签名、日期、案号和附件通常在正式提交前补齐，不触发循环重试。

## 路由规则

目标机关为承办一审案件的人民法院。一次请求包含多个独立程序事项时分别生成文书并提供总清单。

## 工作流程

1. 识别文种、案件阶段、输出场景和特殊标签。
2. 核对当前材料的来源与核验状态，不把转述写成已确认事实。
3. 按目标事项选择一个实体模板：庭前会议、回避、管辖、不公开审理、被告人参加庭前会议或普通程序建议；多个事项分别出稿并附总清单。
4. 填充可确认内容，保留最小占位和待核验提示。
5. 调用 `render_docx.py` 生成当前案件目录内的真实 DOCX，再调用 `validate_document.py` 做生成阶段检查；只返回制品和回执，不自行宣布正式交付通过。

## 输出契约

- `PASS`：可交付草稿；
- `PASS_WITH_WARNINGS`：可交付并列非根本缺口；
- `NEEDS_INPUT`：保留草稿并集中列必须由用户决定的事项；
- `BLOCKED`：仅空文件、标题空壳、机关确定性错配、重大确定值冲突或敏感泄露。

## 约束限制

1. 不编造主体、案号、金额、日期、证据、法条或案例。
2. 不承诺程序、定罪、量刑或机关采纳结果。
3. 不替代律师或当事人签署、提交、认罪、上诉或放弃权利。
4. 不用固定字数、固定章节数、模板哈希或全量字段表作为运行硬门禁。

## 参考规范

- [输入说明](./input-spec.md)
- [输出说明](./output-spec.md)
- [质量标准](./quality-standards.md)

## 确定性渲染与责任边界

- 执行前核对 manifest 版本、渲染入口、校验入口、`python-docx==1.2.0` 和所选实体模板；失败即 `BLOCKED`。
- 输出回执包含 `skill_id`、版本、`doc_type`、`template_id`、绝对路径、渲染状态和待补项。
- 本 Skill 的 `PASS` 只表示起草制品已生成；正式交付由 verification 子 Agent 独立调用 `criminal-document-delivery-check`，本 Skill 不反向调用该 Skill。
