# CHANGELOG

## v1.2.1 (2026-08-05)

### [AUDIT-FIX] 审查修复

修复v1.2.0修改后的遗漏与冲突：
- workflow-detail.md Phase 2 分类决策树从旧"八类"术语对齐为"三层清偿模型"（E3）
- workflow-detail.md Phase 6 分类统计从"八类"改为"各层"，输出格式xlsx→csv对齐output-spec（E4）
- legal-references.md 第113条条文摘要同步更新个人账户/统筹区分（E5）

## v1.2.0 (2026-08-05)

### [P0-FIX] 清偿顺位三层模型重构 + 法条文件补全

基于顶级破产法律实务专家团队评估，修复3项P0+1项P1问题：

**P0-1 清偿顺位模型重构**：
- methodology.md 社保债权区分从错误（"仅统筹账户优先"）修正为正确（个人账户→第113条(一)第一顺位，统筹账户→第113条(二)第二顺位），补充详细区分表
- methodology.md 核心方法论从"八类分类"重构为"三层清偿模型"（Layer 0 财产外扣除 → Layer 1 随时清偿 → Layer 2 第113条三顺位），新增完整计算公式
- legal-references.md 第113条描述补全个人账户/统筹区分，新增第113条第(二)项独立条目

**P1-1 抵销权审查增强**：
- workflow-detail.md Phase 4 新增步骤5"审查异议诉讼时效"——破产法解释二第41条3个月异议诉讼时限（管理人最易失权陷阱），输出新增"异议诉讼时限提醒"

**P0-5 九民纪要等司法文件补全**：
- legal-references.md 新增3个司法文件引用：九民纪要（第106-111条）+ 破产审判纪要（第14-30条）+ 民法典条文补充

### [FIX] 文件清单
修改：methodology.md / legal-references.md / workflow-detail.md / CHANGELOG.md（4文件）

## v1.1.1 (2026-07-27)

### [STRUCTURE] 六模块白名单重构

- SKILL.md 从 M1-M9 骨架重构为 §17.27 D1 六模块白名单结构（frontmatter/模块一/模块二/模块三/模块四/模块五）
- 核心原则（原M5 7条P1-P7）并入模块一
- 写作红线（原M6 8条R1-R8）迁移至 output-spec.md §1
- 核心方法论（原M4）外置至 methodology.md，SKILL.md 仅留指向
- 法条参考（原M8）删除，全部归 legal-references.md
- 文档索引（模块五）补充 CHANGELOG.md 条目
- O4 分类统计表从 xlsx 降级为 csv（§17.17：LLM无法直出二进制，csv可用Excel打开）
- manifest.json 精简非标准字段（governance/files/applicable_scope/target_users/output_types/format_seriousness）
- 删除根目录 references.zip 开发期打包产物

## v1.1.1 (2026-07-27)

### [AUDIT-FIX] 审计修复

- methodology 附停止条件债权表决权法条号修正：第59条第4款→第59条第2款
- methodology 建工优先权期限条文修正：民法典第807条→建工司法解释一第41条（807条仅规定优先受偿权，未规定期限；实务以应付工程款之日为准）
- 八类债权分类体系澄清：template/ workflow/ methodology/ output-spec 4处统一为"八类法定清偿顺位+别除权依第109条单列"表述，消除9项列在"八类"下的歧义

## v1.0.0 (2026-07-23)

### [INITIAL] 初始版本

- 创建破产债权审查技能
- 核心方法论：八类债权分类与决策树 + 抵销权逐项检查清单 + 金额核验5维度
- 6 Phase 工作流程
- SOFT_DEGRADED 降级机制（C+D+G最小骨架）
- 核心原则 7 条 + 写作红线 8 条
- 法条参考：企业破产法第40/41/42/46/48/56/58/109/113条 + 破产法解释二/三 + 民法典第807条
