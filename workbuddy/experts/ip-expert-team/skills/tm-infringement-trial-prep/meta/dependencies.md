# 上下游技能依赖 — tm-infringement-trial-prep

> **所属技能**：tm-infringement-trial-prep | **文件角色**：依赖声明 | **版本**：v1.1.0

---

## 一、基础设施依赖

> 依据 type_tag = T-consultation 的依赖决策矩阵

| 依赖名称 | 类型 | 必需 | 降级行为 | 来源 |
|----------|------|------|----------|------|
| `governance.soft_degraded` | 基础设施 | 必需 | 无此依赖则降级机制无法正常运作 | `base/infrastructure/governance/soft_degraded.py` |
| `governance.interaction_gates` | 基础设施 | 必需 | 缺失时跳过交互补全，降级到占位标注 | `base/infrastructure/governance/interaction_gates.py` |

---

## 二、上游技能依赖

| 技能名称 | 关系 | 依赖强度 | 交互方式 | 占位格式 |
|----------|------|---------|---------|---------|
| tm-infringement-cross-exam | 上游：质证意见（D2） | 强引用 | 消费其质证结论→填入三、质证要点 | `[待消费D2(tm-infringement-cross-exam)输出]` |
| tm-infringement-comparison | 上游：商标比对（B1） | 强引用 | 消费其比对结论→填入四(一)、侵权构成论证 | `[待消费B1(tm-infringement-comparison)输出]` |
| tm-damage-calc | 上游：赔偿计算（A6） | 强引用 | 消费其计算结果→填入四(二)、赔偿计算论证 | `[待消费A6(tm-damage-calc)输出]` |
| tm-infringement-strategy | 上游：诉讼策略（C3） | 中引用 | 消费其策略预判→填入四(三)、对方抗辩回应 | `[待消费C3(tm-infringement-strategy)输出]` |

> **强引用说明**：D2/B1/A6的输出是庭审提纲的核心组成部分，缺失时必须占位标注。C3为中引用，缺失时不影响框架完整性。
>
> **框架先行**：本技能支持上游输出未就绪时框架先行完成——7环节结构先行生成，缺失部分用占位标注替代。

---

## 三、下游技能依赖

本技能暂无下游技能消费。

---

## 四、跨技能共享组件

| 共享组件 | 来源 | 本技能消费方式 |
|---------|------|--------------|
| 法条库 | `base/shared/legal-citation-format.md` | 三标注体系格式规范 |
| 写作红线 | `base/shared/writing-redlines.md` | WR-01~11全部遵守 |
| 风险规则 | `base/shared/risk-rules-common.md` | L1/L2/L3禁止事项 |
| 术语规范 | `base/shared/terminology-common.md` | 通用法律术语标准表述 |
| 商标审查标准 | 《商标审查及审理标准》 | 比对方法论证依据 |
| 证据编号 | tm-infringement-cross-exam | DE-XX编号体系对齐 |

---

## 五、独立运行声明

本技能声明**可框架独立运行**——不依赖任何上游技能的输出即可完成7环节框架生成。上游技能的输出用于填充框架中的具体内容，缺失时用占位标注替代，不影响框架的完整性。
