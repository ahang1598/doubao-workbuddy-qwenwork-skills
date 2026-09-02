---
name: criminal-simplified-fast-track-document-drafting
version: 1.0.0
name_en: criminal-simplified-fast-track-document-drafting
description: 生成简易程序、速裁程序和认罪认罚案件的程序选择评估、适用普通程序建议书及量刑建议协商意见书。触发：简易程序、速裁程序、认罪认罚程序选择、建议普通程序、量刑建议协商。不触发：认罪认罚具结签署确认调用 criminal-plea-negotiation；普通一审辩护词调用 criminal-defense-speech-trial。
---

# 简易速裁与认罪认罚程序文书

## 核心职责

区分普通、简易和速裁程序的适用前提、权利影响与案件争点；程序效率不得替代自愿性、事实证据和辩护权审查。

## 适用范围

- 案件阶段：`review_prosecution`、`first_instance`
- 支持文种：`procedure_selection_assessment`、`ordinary_procedure_recommendation`、`sentencing_recommendation_negotiation_opinion`
- 输出场景：机关文书使用 `agency_submission`；内部提纲使用 `lawyer_working`；只有模板明确为家属材料时使用 `family_communication`。

## 最小输入契约

- 必需：目标文种或可识别请求、可用事实摘要或材料。
- 条件必需：只有当阶段、主体或机关无法推导且会改变法律路径时才集中补问。
- 缺失处理：草稿允许 `[待补：字段]`；签名、日期、案号和附件通常在正式提交前补齐，不触发循环重试。

## 路由规则

律师内部比较生成 procedure_selection_assessment；认为简易/速裁不适合时向法院提交适用普通程序建议书；协商量刑建议时提交检察院意见书。

## 工作流程

1. 识别文种、案件阶段、输出场景和特殊标签。
2. 核对当前材料的来源与核验状态，不把转述写成已确认事实。
3. 内部程序比较选择程序评估；向法院建议改用普通程序选择建议书；向检察院协商量刑建议选择协商意见书。
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
- 输出回执包含 `skill_id`、版本、`doc_type`、`template_id`、绝对路径、渲染状态和待补项；程序效率不得代替自愿性和证据审查。
- 本 Skill 的 `PASS` 只表示起草制品已生成；正式交付由 verification 子 Agent 独立调用 `criminal-document-delivery-check`，本 Skill 不反向调用该 Skill。
