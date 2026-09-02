# CHANGELOG

## v1.3.1 (2026-08-05)

### [AUDIT-FIX] 审查修复

修复v1.3.0修改后的遗漏与冲突：
- workflow-detail.md Phase 3 重整表决条号修正：第86条→第84条（第84条为表决组通过标准，第86条为整体通过认定）（C1）
- methodology.md 第87条六项条件措辞对齐reorg-plan-draft版本（统一条文原文要旨表述）
- methodology.md 通知期限15日计算补标注法条号"第64条第2款"（O3）

## v1.3.0 (2026-08-05)

### [P0-FIX] 会议通知条号修正 + 法条文件补全 + 救济路径补全

基于顶级破产法律实务专家团队评估，修复2项P0+1项P1问题：

**P0-3 会议通知条号硬伤修正**（全局第63条→第64条第2款）：
- output-spec.md O1 通知期限引用条号修正（第63条→第64条第2款【已核实】）
- output-spec.md 禁止事项表中"破产法第63条"修正
- workflow-detail.md Phase 4 通知条号修正
- legal-references.md 第62/63/64条要旨全面修正（原"第62条：会议召集与通知(15日)"→拆分为第62条首次会议召集+第64条第2款通知义务）
- templates/meeting-notice-template.md 引用条号修正
- methodology.md 通知期限15日计算保留（不涉及条号变更）

**P1 方案未通过救济预案+决议撤销风险**：
- workflow-detail.md Phase 5 新增：方案未通过救济预案（再表决→法院裁定→强批路径）+ 决议撤销风险自查（第64条第2款15日撤销权+撤销风险自查表）

**P0-5 九民纪要等司法文件补全**：
- legal-references.md 新增九民纪要（第107/108/112条）+ 破产审判纪要（第25-30条）+ 法发〔2020〕14号（第13-19条）

### [FIX] 文件清单
修改：legal-references.md / output-spec.md / workflow-detail.md / templates/meeting-notice-template.md / CHANGELOG.md（5文件）

## v1.2.0 (2026-08-05)

### [FEATURE] 表决可行性分析能力增强

基于华博润债权和解协议草案表决结果分析报告的真实律师产出水准，新增表决可行性测算能力：

- **新增 Phase 3.5 表决可行性测算**：门槛达标测算（双过半/2/3门槛逐项计算）+ 最小争取组合测算（贪心算法+多组合对比）+ 多情景假设（基准/保守/乐观/银行默许/分组未通过）+ 风险排序与策略建议
- **新增 O6 表决可行性分析报告**（docx）：含债权人结构总览/门槛达标测算/最小争取组合/多情景假设/风险排序与策略建议五部分
- **新增 P6 核心原则**：表决可行性量化——表决前须测算通过概率、最小争取组合与多情景假设，不凭经验判断
- **methodology.md 新增表决可行性测算方法论**：门槛测算口径（无担保债权总额计算/重整组内总额/连带债权去重）+ 最小争取组合算法逻辑（贪心+双门槛+争取难度评估）+ 多情景假设设置原则（银行默许实务依据+第87条强制批准六条件）+ 风险排序方法+策略建议输出规范
- **input-spec.md 新增 creditor_detail/voting_scenario 参数**
- **legal-references.md 新增第87条**（强制批准6项条件）
- **quality-standards.md 新增 BLK-06/07 阻断项 + WRN-02/03 警告项 + 表决测算准确维度**
- **description 触发词新增**：表决可行性/表决测算/最小争取组合

## v1.1.0 (2026-07-27)

### [STRUCTURE] 六模块白名单重构

- SKILL.md 从 M1-M9 骨架重构为 §17.27 D1 六模块白名单结构
- 核心原则（原M5 5条P1-P5）并入模块一
- 写作红线（原M6 6条R1-R6）迁移至 output-spec.md §1
- 核心方法论（原M4）外置至 methodology.md，SKILL.md 仅留指向
- 法条参考（原M8）删除，全部归 legal-references.md
- 文档索引（模块五）补充 CHANGELOG.md 条目
- legal-references.md 补充第84条（表决程序）和第85条（出资人组）法条引用
- manifest.json 精简非标准字段（governance/files/applicable_scope/target_users/output_types/format_seriousness）
- 删除根目录 references.zip 开发期打包产物

## v1.0.0 (2026-07-23)

### [INITIAL] 初始版本

- 创建债权人会议支持技能
- 核心方法论：债权人会议法定职权9项 + 三种表决规则对比 + 重整表决5分组
- 5 Phase 工作流程
- SOFT_DEGRADED 降级机制（C+D+G最小骨架）
- 核心原则 5 条 + 写作红线 6 条
- 法条参考：企业破产法第59-69/82/86/97条 + 破产法解释三第11-13条
