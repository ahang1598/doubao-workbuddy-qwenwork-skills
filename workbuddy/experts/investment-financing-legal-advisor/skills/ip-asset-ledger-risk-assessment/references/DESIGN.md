# DESIGN.md — IP资产台账与风险评估

## 1. 设计目标

为投资方律师提供IP资产全生命周期管理工具，覆盖投前尽调→投中评估→投后R&W映射→年度盘点四场景，输出结构化xlsx台账+分析报告。

## 2. 核心设计决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 蓝图 | bp-due-diligence-opinion-support-v1 | 与07/03同蓝图，尽调+意见支持 |
| 风险等级 | L3 | 权属/许可/出资瑕疵直接关系交易价值 |
| 脚本必需性 | none | LLM能力足够完成台账生成与风险评级（§17.17） |
| 起草范式 | lawyer_draft | IP台账含大量分析论证（§17.28） |
| 输出格式 | xlsx+md | xlsx供法务/财务消费，md供律师阅读 |
| IP类型范围 | 4核心+4其他+1独立维度 | 覆盖投资尽调全部IP类型 |

## 3. 架构概要

### 双包模型（§17.9.1）

- `release/`：运行时交付包（SKILL.md ≤300行 + meta/ + references/ + templates/ + examples/）
- `development/`：开发包（CHANGELOG.md + design-spec.md + request/ + evaluation/）

### 7 Phase管线

P1场景路由 → P2资产结构化 → P3权属核验 → P4许可链+出资 → P5风险评级+R&W → P6双产物生成 → P7质量检查

### 文件归档结构

本技能采用归档结构，release/下仅SKILL.md、.version在根目录（其余文档置于子文件夹）：
- DESIGN.md/USAGE.md → `references/`
- methodology.md → `references/`
- input-spec/output-spec/workflow-detail/legal-references/format-spec → `references/`
- risk-framework → `references/`
- quality-profile → `references/`
- xlsx-structure/markdown-report → `templates/`
- example-001/002/003 → `examples/`
- manifest.json/dependencies/known-limitations → `meta/`

## 4. 关键方法论

1. **三级权属核验法**：证书层→登记层→官方状态层，逐层递进
2. **许可链追踪法**：原始权利人→N级被许可人，超3层标记RC-02
3. **出资瑕疵识别法**：评估合规+交付完整+公示合规+决议程序四要素
4. **R&W条款映射法**：风险→条款类型→条款建议，7类标准条款

## 5. 质量保证

- 25项自检（产物完整性/字段填充率/风险识别率/法条引用准确性/R&W条款完整性）
- xlsx与md数据一致性校验
- 法条引用三标注（[已核实]/[需核实]/[存疑]）
- 共享写作红线 `base/shared/writing-redlines.md` 11条无偏离
- 五维评测综合 ≥90分
