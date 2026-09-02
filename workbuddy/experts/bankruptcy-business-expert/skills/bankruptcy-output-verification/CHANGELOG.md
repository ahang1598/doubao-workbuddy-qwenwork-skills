# CHANGELOG

## v1.2.0 (2026-08-05)

### [P1-FIX] 门禁阻断机制补全

基于顶级破产法律实务专家团队评估，修复P1问题：

**P1 校验阻断机制补全**：
- SKILL.md 核心原则新增P7"阻断必停"——发现阻断级问题时须显著标注并退回对应技能修复
- SKILL.md 新增"门禁判定规则"章节：🔴不可交付/🟡需修改/🟢可交付三级门禁 + BLK-01至BLK-07共7项阻断级问题定义（金额矛盾/顺位错误/法条错误/章节缺失/越权表述/合计不闭合/程序缺陷）
- 阻断项未清除时禁止标记为"可交付"——从"建议型"升级为"阻断型"

### [FIX] 文件清单
修改：SKILL.md / CHANGELOG.md（2文件）

## v1.1.0 (2026-07-27)

### [STRUCTURE] 六模块白名单重构

- SKILL.md 从 M1-M9 骨架重构为 §17.27 D1 六模块白名单结构
- 核心原则（原M5 6条P1-P6）并入模块一
- 写作红线（原M6 7条R1-R7）迁移至 output-spec.md §1
- 核心方法论（原M4）外置至 methodology.md，SKILL.md 仅留指向
- 法条参考（原M8）删除，全部归 legal-references.md
- 文档索引（模块五）补充 CHANGELOG.md 条目
- manifest.json 精简非标准字段（governance/files/applicable_scope/target_users/output_types/format_seriousness）
- 删除根目录 references.zip 开发期打包产物

## v1.0.0 (2026-07-23)

### [INITIAL] 初始版本

- 创建破产成果校验技能
- 核心方法论：八维校验框架(V1-V8) + 法定必含章节检查6类 + 金额一致性核验5项 + 优先级独立复核
- 7 Phase 工作流程
- SOFT_DEGRADED 降级机制（C+D+G最小骨架）
- 核心原则 6 条 + 写作红线 7 条
- 法条参考：企业破产法第25/58/61/69/113/115条
