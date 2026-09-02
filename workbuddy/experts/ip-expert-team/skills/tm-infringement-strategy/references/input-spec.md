# 输入字段定义 — tm-infringement-strategy

> **所属技能**：tm-infringement-strategy | **文件角色**：输入规格 | **版本**：v1.1.0

---

## 必填字段（L3级——缺失则触发 SOFT_DEGRADED 或无法制定策略）

| 参数 | 类型 | 法律含义 | 约束 | 降级标记 |
|------|------|---------|------|---------|
| `infringement_analysis.similarity_conclusion` | enum | 侵权比对结论 | 近似/不近似/存疑 | L3(强引用) |
| `infringement_analysis.confusion_possibility` | enum | 混淆可能性 | 高/中/低 | L3(强引用) |
| `infringement_analysis.goods_similarity` | enum | 商品类似性 | 相同/类似/不类似 | L3(强引用) |
| `trademark_info.trademark_text` | string | 商标标识 | 非空 | L3 |
| `trademark_info.nice_class` | integer | 尼斯分类 | 1-45 | L3 |
| `trademark_info.designated_goods` | string | 核定商品 | 非空 | L3 |
| `opponent_info.name` | string | 被告名称 | 非空 | L3 |
| `opponent_info.domicile` | string | 被告住所地 | 非空（影响管辖） | L3 |
| `client_priority` | enum | 客户优先目标 | 停止侵权/赔偿最大化/快速解决/全面维权 | L3 |

> **L3 缺失处理**：缺少侵权比对结论 → 无法制定策略，建议先行侵权比对

---

## 条件必填字段（L2级——缺失则降级到策略框架+占位）

| 参数 | 类型 | 条件 | 法律含义 | 降级标记 |
|------|------|------|---------|---------|
| `trademark_info.registration_date` | date | 涉及三年不使用抗辩时 | 注册日期（影响第64条适用） | L2 |
| `opponent_info.business_location` | string | 涉及管辖选择时 | 经营地/侵权行为地 | L2 |
| `opponent_info.asset_clue` | string | 涉及财产保全时 | 财产线索 | L2 |

> **L2 缺失处理**：缺少注册日期 → 三年不使用抗辩预判用"需确认注册日期"占位

---

## 推荐字段（L1级——缺失则标注后继续生成）

| 参数 | 类型 | 来源 | 法律含义 | 降级标记 |
|------|------|------|---------|---------|
| `damage_estimate` | object | tm-damage-calc | 赔偿测算结论 | L1 |
| `evidence_status` | string | 用户输入 | 充分/一般/不足 | L1 |
| `case_research` | object | tm-case-research | 类案检索结论 | L1 |
| `opponent_info.online_platform` | string | 用户输入 | 网络销售平台（影响管辖） | L1 |

> **L1 缺失处理**：完整策略正常输出，赔偿使用简化版估算

---

## 降级分层汇总

| 降级等级 | 缺失字段 | 输出范围 |
|---------|---------|---------|
| **L0 完整** | 无缺失 | 完整策略方案 + 五类抗辩预判表 + 三维风险矩阵 + 管辖对比分析 |
| **L1 轻度** | 缺少 damage_estimate | 完整策略 + 简化版赔偿估算 |
| **L2 中度** | 缺少被告住所地 | 策略框架 + 管辖占位标注 |
| **L3 重度→SOFT_DEGRADED** | 缺少侵权比对结论 | 仅策略骨架 + 建议先行比对（C+D+G最小骨架） |

---

## 交互补全规则

当必需参数不完整时，按以下优先级交互（≤3轮）：

| 优先级 | 缺失信息 | 默认提示 |
|--------|---------|---------|
| P0 | 侵权比对结论 | "请提供侵权比对分析结论（来自tm-infringement-comparison）" |
| P1 | 被告住所/经营地 | "请提供被告住所地或侵权行为地" |
| P2 | 客户优先目标 | "请明确客户优先目标（停止侵权/赔偿最大化/快速解决/全面维权）" |
