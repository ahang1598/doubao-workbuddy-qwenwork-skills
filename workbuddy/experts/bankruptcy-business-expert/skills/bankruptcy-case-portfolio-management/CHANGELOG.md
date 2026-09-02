# CHANGELOG

## v1.1.0 (2026-07-27)

### [STRUCTURE] 六模块白名单重构 + 法条修正

- SKILL.md 从模块一~十骨架重构为 §17.27 D1 六模块白名单结构
- 角色定位补充到模块一（修复 B6-4 角色定位警告）
- 核心原则（原模块五 10条P1-P10）并入模块一
- 写作红线（原模块六 8条R1-R8）迁移至 output-spec.md §1
- 核心方法论（原模块四）外置至 methodology.md，SKILL.md 仅留指向
- 法条参考（原模块八）删除，全部归 legal-references.md
- 文档索引（模块五）补充 CHANGELOG.md 条目
- 补建 .version 镜像文件（原缺失，现为1.1.0）
- legal-references.md 法条修正：
  - L1-L3: 删除错误的"解释三第1-3条=债权申报范围/期限/方式"，替换为正确的第6-15条（债权审查/会议/重整系列）
  - L4: 解释二第15条从"管理人撤销权行使"修正为"经诉讼仲裁执行个别清偿不得撤销（恶意串通除外）"——撤销权限制
  - 补全解释二第9-14条撤销权系列
- manifest.json 精简非标准字段（updated/format_seriousness/legal_domain/o1_format/o2_format/target_users/output_types/legal_basis/infrastructure_dependencies/copyright）

## v1.0.0 (2026-07-21)

### [INITIAL] 初始版本

- 创建破产案件组合管理技能
- 核心方法论：多案件工作空间标准化 + 索引台账 + 期限看板 + 履职节点锚定
- 6个功能模块（INIT/PORTFOLIO/DEADLINE/PROGRESS/DUTY-SUMMARY/UPDATE）
- 7 Phase 工作流程
- 核心原则 10 条 + 写作红线 8 条
- 3个示例（init-liquidation/portfolio-deadline/update-existing）
