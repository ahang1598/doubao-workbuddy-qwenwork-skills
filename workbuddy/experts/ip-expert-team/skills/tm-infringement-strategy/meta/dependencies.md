# 上下游技能依赖 — tm-infringement-strategy

> **所属技能**：tm-infringement-strategy | **文件角色**：依赖声明 | **版本**：v1.1.0

---

## 一、基础设施依赖

> 依据 type_tag = T-consultation 的依赖决策矩阵

| 依赖名称 | 类型 | 必需 | 降级行为 | 来源 |
|----------|------|------|----------|------|
| `governance.soft_degraded` | 基础设施 | 必需 | 无此依赖则降级机制无法正常运作 | `base/infrastructure/governance/soft_degraded.py` |
| `governance.interaction_gates` | 基础设施 | 必需 | 无此依赖则交互补全无法门控 | `base/infrastructure/governance/interaction_gates.py` |

---

## 二、上游技能依赖

| 技能名称 | 关系 | 依赖强度 | 交互方式 | 缺失时降级 |
|----------|------|---------|---------|-----------|
| tm-infringement-comparison | 上游：侵权比对 | 强引用 | 消费侵权比对结论（必需） | 无法制定策略→建议先行比对 |
| tm-damage-calc | 上游：赔偿测算 | 弱引用 | 消费赔偿测算结论 | 简化版4路径估算 |
| tm-case-research | 上游：类案检索 | 弱引用 | 消费类案检索结论 | 无类案支撑→标注"未参考类案" |
| tm-case-evaluation | 上游：案件初评 | 弱引用 | 消费初评报告确定策略方向 | 通过用户直接输入替代 |
| tm-jurisdiction-analysis | 上游：管辖分析 | 弱引用 | 消费管辖分析 | 简化版管辖分析+⚠️标注 |

> **强引用说明**：tm-infringement-comparison 的输出是本技能的必需输入——没有侵权比对结论，无法制定诉讼策略。缺失时须建议用户先行完成侵权比对。

---

## 三、下游技能依赖

| 技能名称 | 关系 | 依赖强度 | 交互方式 |
|----------|------|---------|---------|
| tm-infringement-complaint | 下游：侵权起诉状 | 弱引用 | 消费策略方案确定起诉状内容 |

---

## 四、跨技能共享组件

| 共享组件 | 来源 | 本技能消费方式 |
|---------|------|--------------|
| 法条库 | `base/shared/legal-citation-format.md` | 三标注体系格式规范 |
| 写作红线 | `base/shared/writing-redlines.md` | WR-01~11+WR-T01~06全部遵守 |
| 风险规则 | `base/shared/risk-rules-common.md` | L1/L2/L3禁止事项 |
| 术语规范 | `base/shared/terminology-common.md` | 通用法律术语标准表述 |

---

## 五、独立运行声明

本技能声明**可条件独立运行**——必需 tm-infringement-comparison 的侵权比对结论方可制定完整策略。当该上游技能不可用时，输出建议用户先行完成侵权比对的降级提示。其他上游技能的输出仅用于增强策略质量，缺失时通过简化版替代。
