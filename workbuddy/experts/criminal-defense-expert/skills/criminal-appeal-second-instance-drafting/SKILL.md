---
name: criminal-appeal-second-instance-drafting
version: 1.0.0
name_en: criminal-appeal-second-instance-drafting
description: 生成刑事上诉状、二审辩护意见、公开开庭审理申请书及二审补充意见。触发：刑事上诉、二审辩护、申请二审开庭、一审判决评析后起草。不触发：一审辩护词调用 criminal-defense-speech-trial；再审申请调用 criminal-special-procedure-document-drafting。
---

# 刑事上诉与二审文书起草

## 核心职责

从一审裁判、庭审记录和上诉期限出发提炼事实认定、证据采信、法律适用、量刑和程序理由；上诉状与二审辩护意见采用不同功能结构。

## 适用范围

- 案件阶段：`second_instance`
- 支持文种：`criminal_appeal`、`second_instance_defense_opinion`、`second_instance_open_hearing_application`、`second_instance_supplemental_opinion`
- 输出场景：机关文书使用 `agency_submission`；内部提纲使用 `lawyer_working`；只有模板明确为家属材料时使用 `family_communication`。

## 最小输入契约

- 必需：目标文种或可识别请求、可用事实摘要或材料。
- 条件必需：只有当阶段、主体或机关无法推导且会改变法律路径时才集中补问。
- 缺失处理：草稿允许 `[待补：字段]`；签名、日期、案号和附件通常在正式提交前补齐，不触发循环重试。

## 路由规则

对一审未生效裁判提出救济时路由上诉状；案件已进入二审时路由二审辩护意见；是否开庭存在必要性时单独生成公开开庭审理申请书。

## 工作流程

1. 识别文种、案件阶段、输出场景和特殊标签。
2. 核对当前材料的来源与核验状态，不把转述写成已确认事实。
3. 按目标文种选择上诉状、二审辩护意见、公开开庭申请书或二审补充意见；不得用一审辩护词改标题代替二审文书。
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
