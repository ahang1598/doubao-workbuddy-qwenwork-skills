# CHANGELOG

## v1.2.1 (2026-08-05)

### [AUDIT-FIX] 审查修复

修复v1.2.0修改后的遗漏与错误：
- methodology.md Layer 1公式逻辑错误修正：`总变现财产−超额+超额转入`（自相矛盾）→ `非担保财产变现价+Layer 0超额转入`（E1）
- SKILL.md M3工作流概览表对齐三层模型新Phase编号（E2）
- legal-references.md 第113条条文摘要同步更新个人账户/统筹区分（E6）

## v1.2.0 (2026-08-05)

### [P0-FIX] 三层分配模型重构 + 法条文件补全

基于顶级破产法律实务专家团队评估，修复2项P0问题：

**P0-1 清偿顺位三层模型**：
- methodology.md 核心方法论从"6层递进"重构为"三层分配模型（Layer 0→1→2）"，新增完整分配计算公式（别除权受偿额/超额/不足/破产费用/共益债务/第113条三顺位逐层公式）
- output-spec.md O3 JSON schema 重构：by_priority → by_layer（layer0_property_offset / layer1_immediate_payment / layer2_statutory_priority），新增担保物变现费用/建工优先权/社保个人账户标注字段
- workflow-detail.md Phase 2-6 全面对齐三层模型（Layer 0 财产外扣除 → Layer 1 随时清偿 → Layer 2 三顺位），自检清单新增担保物变现费用+社保区分项
- legal-references.md 第113条描述补全"个人账户/统筹区分"

**P0-5 九民纪要等司法文件补全**：
- legal-references.md 新增九民纪要（第106/110/112条）+ 破产审判纪要（第28-31条）+ 法发〔2020〕14号（第15-19条）

### [FIX] 文件清单
修改：methodology.md / legal-references.md / output-spec.md / workflow-detail.md / CHANGELOG.md（5文件）

## v1.1.1 (2026-07-27)

### [STRUCTURE] 六模块白名单重构

- SKILL.md 从 M1-M9 骨架重构为 §17.27 D1 六模块白名单结构
- 核心原则（原M5 6条P1-P6）并入模块一
- 写作红线（原M6 7条R1-R7）迁移至 output-spec.md §1
- 核心方法论（原M4）外置至 methodology.md，SKILL.md 仅留指向
- 法条参考（原M8）删除，全部归 legal-references.md
- 文档索引（模块五）补充 CHANGELOG.md 条目
- O2 清偿率测算表从 xlsx 降级为 csv（§17.17：LLM无法直出二进制，csv可用Excel打开）
- P4原则"Word草案与Excel测算表一致"调整为"草案与测算表数据一致"（适配csv格式）
- manifest.json 精简非标准字段（governance/files/applicable_scope/target_users/output_types/format_seriousness）
- 删除根目录 references.zip 开发期打包产物

## v1.1.1 (2026-07-27)

### [AUDIT-FIX] 审计修复

- methodology 税收滞纳金引用文号修正：国家税务总局公告2020年第6号→2019年第48号
- quality-standards + methodology "草案与测算表"表述修正：Word草案与Excel测算表→草案(docx)与测算表(csv)

## v1.0.0 (2026-07-23)

### [INITIAL] 初始版本

- 创建破产分配计算技能
- 核心方法论：6层递进分配顺位计算公式 + 担保债权特殊处理 + 精度规则(4位小数+分+尾差)
- 6 Phase 工作流程
- SOFT_DEGRADED 降级机制（C+D+G最小骨架）
- 核心原则 6 条 + 写作红线 7 条
- 法条参考：企业破产法第41/42/43/109/113/115/116条 + 破产法解释三第10条
