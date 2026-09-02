# CHANGELOG

## v1.1.0 (2026-07-27)

### [STRUCTURE] 六模块白名单重构

- SKILL.md 从 M1-M9 骨架重构为 §17.27 D1 六模块白名单结构
- 核心原则（原M5 5条P1-P5）并入模块一
- 写作红线（原M6 6条R1-R6）迁移至 output-spec.md §1
- 核心方法论（原M4）外置至 methodology.md，SKILL.md 仅留指向
- 法条参考（原M8）删除，全部归 legal-references.md
- 文档索引（模块五）补充 CHANGELOG.md 条目
- manifest.json 精简非标准字段（governance/files/applicable_scope/target_users/output_types/format_seriousness）
- 删除根目录 templates.zip 开发期打包产物

## v1.1.2 (2026-07-27)

### [AUDIT-FIX] 审计修复

- report_type=distribution_plan 命名全技能统一：output-spec §2「分配执行报告（第115/116条）」→「分配方案报告（第115条）」，章节按第115条第2款调整为方案口径（方案依据/分配安排/提存与预留/剩余财产处理/后续工作与说明）
- workflow-detail 报告类型路由「分配执行报告5章节」→「分配方案报告5章节」
- output-spec §9 禁止事项「分配执行报告混淆」→「分配方案报告混淆」
- 与 SKILL.md 描述/模板（distribution-report-template.md）命名一致

## v1.1.1 (2026-07-27)

### [AUDIT-FIX] 审计修复

- report_type 枚举三处不一致统一：SKILL.md 4种/input-spec 5种(含claim_review)/output-spec §2仅3类 → 统一4种：takeover/asset_status/duty/distribution_plan
- output-spec §2 法定章节法条号修正：财产状况报告第26条→第25条，分配执行报告第120条→第115/116条
- 补接管报告章节（原output-spec §2缺失）
- workflow-detail 清理已删除的 claim_review/reorg_plan 路由行
- example report_type duty_report→duty
- input-spec 删除与claim-review技能重复的claim_review类型

## v1.0.0 (2026-07-23)

### [INITIAL] 初始版本

- 创建管理人报告编制技能
- 核心方法论：6种报告类型法定必含章节 + 数据一致性6项要求
- 5 Phase 工作流程
- SOFT_DEGRADED 降级机制（C+D+G最小骨架）
- 核心原则 5 条 + 写作红线 6 条
- 法条参考：企业破产法第25/69/80/115条 + 破产法解释三第10条
- 4个报告模板（接管/财产状况/履职/分配方案）
