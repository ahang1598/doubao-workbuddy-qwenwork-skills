# 上下游技能依赖 — tm-infringement-cross-exam

> **所属技能**：tm-infringement-cross-exam | **文件角色**：依赖声明 | **版本**：v1.1.0

---

## 一、基础设施依赖

> 依据 type_tag = T-consultation 的依赖决策矩阵

| 依赖名称 | 类型 | 必需 | 降级行为 | 来源 |
|----------|------|------|----------|------|
| `governance.soft_degraded` | 基础设施 | 必需 | 无此依赖则降级机制无法正常运作 | `base/infrastructure/governance/soft_degraded.py` |
| `governance.interaction_gates` | 基础设施 | 必需 | 缺失时跳过交互补全，降级到占位标注 | `base/infrastructure/governance/interaction_gates.py` |

---

## 二、上游技能依赖

| 技能名称 | 关系 | 依赖强度 | 交互方式 |
|----------|------|---------|---------|
| tm-infringement-comparison | 上游：商标比对 | 中引用 | 消费其比对结论用于不近似抗辩质证 |
| tm-damage-calc | 上游：赔偿计算 | 中引用 | 消费其计算结果用于赔偿相关证据质证 |

> **中引用说明**：上游技能的输出可显著提升质证的精准度，但本技能可独立运行——缺失时在对应位置标注"[待引用B1/A6输出]"。

---

## 三、下游技能依赖

| 技能名称 | 关系 | 依赖强度 | 交互方式 |
|----------|------|---------|---------|
| tm-infringement-trial-prep | 下游：庭审提纲 | 强引用 | 下游消费本技能的质证意见（D2输出→D3消费） |

---

## 四、跨技能共享组件

| 共享组件 | 来源 | 本技能消费方式 |
|---------|------|--------------|
| 法条库 | `base/shared/legal-citation-format.md` | 三标注体系格式规范 |
| 写作红线 | `base/shared/writing-redlines.md` | WR-01~11全部遵守 |
| 风险规则 | `base/shared/risk-rules-common.md` | L1/L2/L3禁止事项 |
| 术语规范 | `base/shared/terminology-common.md` | 通用法律术语标准表述 |
| 商标审查标准 | 《商标审查及审理标准》 | 不近似抗辩比对方法依据 |

---

## 五、独立运行声明

本技能声明**可独立运行**——不依赖任何上游技能的输出即可完成核心功能（质证意见生成）。上游技能的输出仅用于增强质证精准度，缺失时通过用户直接输入替代或标注占位。
