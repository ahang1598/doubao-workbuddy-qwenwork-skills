# 上下游技能依赖 — tm-infringement-evidence-checklist

> **所属技能**：tm-infringement-evidence-checklist | **文件角色**：依赖声明 | **版本**：v1.1.0

---

## 一、基础设施依赖

> 依据 type_tag = T-consultation 的依赖决策矩阵

| 依赖名称 | 类型 | 必需 | 降级行为 | 来源 |
|----------|------|------|----------|------|
| `governance.soft_degraded` | 基础设施 | 必需 | 无此依赖则降级机制无法正常运作 | `base/infrastructure/governance/soft_degraded.py` |
| `governance.interaction_gates` | 基础设施 | 可选 | 缺失时不做3轮交互限制，直接降级 | `base/infrastructure/governance/interaction_gates.py` |

---

## 二、上游技能依赖

| 技能名称 | 关系 | 依赖强度 | 交互方式 |
|----------|------|---------|---------|
| tm-infringement-comparison | 上游：侵权比对 | 弱引用 | 消费其比对分析结论，确定侵权证据方向 |
| tm-case-evaluation | 上游：案件初评 | 弱引用 | 消费其争议类型识别输出 |

> **弱引用说明**：上游技能的输出可提升本技能的证据组织精度，但本技能可独立运行。

---

## 三、下游技能依赖

| 技能名称 | 关系 | 依赖强度 | 交互方式 |
|----------|------|---------|---------|
| tm-infringement-complaint | 下游：侵权起诉状 | 弱引用 | 消费本技能的诉请-证据映射结果 |
| tm-damage-calc | 下游：赔偿计算 | 弱引用 | 消费本技能的损害证据分类结果 |

---

## 四、跨技能共享组件

| 共享组件 | 来源 | 本技能消费方式 |
|---------|------|--------------|
| 法条库 | `base/shared/legal-citation-format.md` | 三标注体系格式规范 |
| 写作红线 | `base/shared/writing-redlines.md` | WR-01~11全部遵守 |
| 风险规则 | `base/shared/risk-rules-common.md` | L1/L2/L3禁止事项 |

---

## 五、独立运行声明

本技能声明**可独立运行**——不依赖任何上游技能的输出即可完成核心功能（证据清单生成）。上游技能的输出仅用于增强证据组织精度，缺失时通过用户直接输入替代。
