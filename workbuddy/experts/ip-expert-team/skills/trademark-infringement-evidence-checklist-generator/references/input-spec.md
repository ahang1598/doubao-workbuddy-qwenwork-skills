# 输入字段定义 — tm-infringement-evidence-checklist

> **所属技能**：tm-infringement-evidence-checklist | **文件角色**：输入规格 | **版本**：v1.1.0

---

## 必填字段（L3级——缺失则触发 SOFT_DEGRADED）

| 参数 | 类型 | 法律含义 | 约束 | 降级标记 |
|------|------|---------|------|---------|
| `case_type` | enum | 案件类型 | infringement_litigation / administrative_complaint | L3 |
| `party_role` | enum | 当事人身份 | plaintiff / defendant | L3 |

> **L3 缺失处理**：缺少上述任一字段 → SOFT_DEGRADED，仅输出通用证据框架+编号体系

---

## 条件必填字段（L2级——缺失则降级到无诉请映射）

| 参数 | 类型 | 条件 | 法律含义 | 降级标记 |
|------|------|------|---------|---------|
| `claims` | string[] | 始终需要 | 诉讼请求列表，诉请映射的基础 | L2 |

> **L2 缺失处理**：缺少诉请 → 证据清单+四分类，无诉请映射

---

## 推荐字段（L1级——缺失则标注[待补充]后继续生成）

| 参数 | 类型 | 法律含义 | 降级标记 |
|------|------|---------|---------|
| `existing_evidence` | string[] | 已有证据清单（三态标记☑） | L1 |
| `defendant_mark_desc` | string | 被控侵权标识描述 | L1 |
| `infringement_type` | enum[] | 侵权行为类型 | L1 |
| `damage_basis` | enum | 赔偿依据 | L1 |

> **L1 缺失处理**：完整清单正常输出，缺失处标注"[待补充]"

---

## 选填字段

| 参数 | 类型 | 法律含义 |
|------|------|---------|
| `trademark_name` | string | 商标名称 |
| `trademark_class` | integer | 商标类别 |
| `defendant_name` | string | 被告名称 |
| `infringement_duration` | string | 侵权持续时间 |

---

## 降级分层汇总

| 降级等级 | 缺失字段 | 输出范围 |
|---------|---------|---------|
| **L0 完整** | 无缺失 | 完整证据清单 + 诉请映射 + 证据收集指引 |
| **L1 轻度** | 缺少推荐字段 | 完整证据清单 + 诉请映射，缺失处标注"[待补充]" |
| **L2 中度** | 缺少条件必填字段 | 证据清单+四分类+编号，无诉请映射 |
| **L3 重度→SOFT_DEGRADED** | 缺少必填字段 | 仅通用证据框架+编号体系（C+D+G最小骨架） |
