---
name: criminal-illegal-evidence-exclusion-drafting
version: 1.0.0
name_en: criminal-illegal-evidence-exclusion-drafting
description: 生成刑事非法证据排除申请书及线索清单，说明涉嫌非法取证的人员、时间、地点、方式和材料。触发：非法证据排除、排除供述、刑讯逼供、违法取证申请。不触发：一般证据三性分析调用 criminal-evidence-analysis-report；普通质证提纲调用 criminal-court-cross-examination-outline-drafting。
---

# 刑事非法证据排除申请起草

## 核心职责

把非法证据线索、申请排除的具体证据、初步材料、调查核实请求和法律后果对应起来；线索不足时生成工作稿而非编造细节。

## 适用范围

- 案件阶段：`review_prosecution`、`first_instance`、`second_instance`
- 支持文种：`illegal_evidence_exclusion_application`、`illegal_evidence_clue_list`
- 输出场景：机关文书使用 `agency_submission`；内部提纲使用 `lawyer_working`；只有模板明确为家属材料时使用 `family_communication`。

## 最小输入契约

- 必需：目标文种或可识别请求、可用事实摘要或材料。
- 条件必需：只有当阶段、主体或机关无法推导且会改变法律路径时才集中补问。
- 缺失处理：草稿允许 `[待补：字段]`；签名、日期、案号和附件通常在正式提交前补齐，不触发循环重试。

## 路由规则

以正式申请为目标时输出 agency_submission；仅梳理排除线索时输出 lawyer_working。申请提交机关根据当前阶段确定，审判阶段致送法院。

## 工作流程

1. 识别文种、案件阶段、输出场景和特殊标签。
2. 核对当前材料的来源与核验状态，不把转述写成已确认事实。
3. 正式申请选择 [非法证据排除申请书](illegal-evidence-exclusion-application.md)；仅整理启动调查所需事实时选择 [非法证据线索清单](illegal-evidence-clue-list.md)，不得把内部核查清单直接作为申请书正文。
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
