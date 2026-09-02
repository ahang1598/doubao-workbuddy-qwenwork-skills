# 上下游技能依赖 — tm-damage-calc

> **所属技能**：tm-damage-calc | **文件角色**：依赖声明 | **版本**：v1.3.0

---

## 一、基础设施依赖

> 依据 type_tag = T-calculation 的依赖决策矩阵

| 依赖名称 | 类型 | 必需 | 降级行为 | 来源 |
|----------|------|------|----------|------|
| `calc.date_calc` | 基础设施 | 可选 | 手动计算侵权持续时间 | `base/infrastructure/calc/date_calc.py` |
| `calc.limitation_calc` | 基础设施 | 可选 | 手动计算诉讼时效 | `base/infrastructure/calc/limitation_calc.py` |
| `governance.soft_degraded` | 基础设施 | 必需 | 无此依赖则降级机制无法正常运作 | `base/infrastructure/governance/soft_degraded.py` |

---

## 二、上游技能依赖

| 技能名称 | 关系 | 依赖强度 | 交互方式 |
|----------|------|---------|----------|
| tm-infringement-complaint | 上游：民事起诉状 | 弱引用 | 消费其侵权事实认定和赔偿诉求 |
| tm-case-evaluation | 上游：案件初评 | 弱引用 | 消费其侵权定性输出 |

> **弱引用说明**：本技能可独立运行——即使上游技能不可用，仍可通过用户直接输入计算要素完成赔偿测算。

---

## 三、下游技能依赖

| 技能名称 | 关系 | 依赖强度 | 交互方式 |
|----------|------|---------|----------|
| tm-infringement-complaint | 下游：民事起诉状 | 弱引用 | 下游消费本技能的测算结果作为赔偿请求依据 |

---

## 四、跨技能共享组件

| 共享组件 | 来源 | 本技能消费方式 |
|---------|------|--------------|
| 法条库 | `base/shared/legal-citation-format.md` | 三标注体系格式规范 |
| 写作红线 | `base/shared/writing-redlines.md` | WR-01~11全部遵守 |
| 风险规则 | `base/shared/risk-rules-common.md` | L1/L2/L3禁止事项 |
| 术语规范 | `base/shared/terminology-common.md` | 通用法律术语标准表述 |

---

## 五、独立运行声明

本技能声明**可独立运行**——不依赖任何上游技能的输出即可完成核心功能（赔偿金额测算）。上游技能的输出仅用于增强计算准确性，缺失时通过用户直接输入替代。
