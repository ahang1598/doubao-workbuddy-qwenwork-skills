# 输入字段定义 — tm-infringement-trial-prep

> **所属技能**：tm-infringement-trial-prep | **文件角色**：输入规格 | **版本**：v1.1.0

---

## 必填字段（L3级——缺失则触发 SOFT_DEGRADED）

| 参数 | 类型 | 法律含义 | 约束 | 降级标记 |
|------|------|---------|------|---------|
| `plaintiff_mark` | object | 原告注册商标信息 | 含 name/category/reg_no 三子字段 | L3 |
| `plaintiff_mark.name` | string | 商标名称 | 非空 | L3 |
| `plaintiff_mark.category` | string | 核定商品类别 | 第1-45类之一 | L3 |
| `plaintiff_mark.reg_no` | string | 商标注册号 | 非空 | L3 |
| `infringement_summary` | string | 侵权行为概述 | 非空，描述被告侵权行为 | L3 |

> **L3 缺失处理**：缺少上述任一字段 → SOFT_DEGRADED，仅输出庭审提纲骨架+法定要素清单

---

## 条件必填字段（L2级——上游输出，缺失则占位）

| 参数 | 类型 | 来源技能 | 法律含义 | 缺失处理 |
|------|------|---------|---------|---------|
| `cross_exam_result` | string | D2(tm-infringement-cross-exam) | 质证结论 | 占位：`[待消费D2(tm-infringement-cross-exam)输出]` |
| `comparison_result` | string | B1(tm-infringement-comparison) | 商标近似比对结论 | 占位：`[待消费B1(tm-infringement-comparison)输出]` |
| `damage_calc_result` | string | A6(tm-damage-calc) | 赔偿计算结论 | 占位：`[待消费A6(tm-damage-calc)输出]` |
| `strategy_result` | string | C3(tm-infringement-strategy) | 诉讼策略 | 占位：`[待消费C3(tm-infringement-strategy)输出]` |
| `defendant_defense` | string | — | 被告抗辩类型 | 推断或标注"[待补充]" |
| `court_name` | string | — | 审理法院 | "[待补充]" |
| `defendant_name` | string | — | 被告名称 | "[待补充]" |

> **L2 缺失处理**：上游输出未就绪→占位标注，7环节框架先行完成

---

## 推荐字段（L1级——缺失则标注[待补充]后继续生成）

| 参数 | 类型 | 法律含义 | 降级标记 |
|------|------|---------|---------|
| `trial_date` | date | 开庭日期 | L1 |
| `trial_duration_minutes` | integer | 预计庭审时长（分钟），默认120 | L1 |
| `plaintiff_evidence_list` | array | 原告证据清单（含编号+名称+证明目的） | L1 |
| `judge_questions_focus` | string | 已知法官关注重点 | L1 |
| `prior_hearing_notes` | string | 庭前会议/证据交换笔录要点 | L1 |

> **L1 缺失处理**：完整庭审提纲正常输出，缺失处标注"[待补充]"

---

## 选填字段

| 参数 | 类型 | 法律含义 |
|------|------|---------|
| `well_known_claim` | boolean | 是否主张驰名商标 |
| `parallel_import` | boolean | 是否涉及平行进口 |
| `fair_use_defense` | boolean | 被告是否主张正当使用 |

---

## 上游消费占位标注规范

| 上游代号 | 技能名 | 占位格式 | 已消费格式 |
|---------|--------|---------|-----------|
| D2 | tm-infringement-cross-exam | `[待消费D2(tm-infringement-cross-exam)输出]` | `[已消费D2(tm-infringement-cross-exam)输出]` |
| B1 | tm-infringement-comparison | `[待消费B1(tm-infringement-comparison)输出]` | `[已消费B1(tm-infringement-comparison)输出]` |
| A6 | tm-damage-calc | `[待消费A6(tm-damage-calc)输出]` | `[已消费A6(tm-damage-calc)输出]` |
| C3 | tm-infringement-strategy | `[待消费C3(tm-infringement-strategy)输出]` | `[已消费C3(tm-infringement-strategy)输出]` |

---

## 降级分层汇总

| 降级等级 | 缺失字段 | 输出范围 |
|---------|---------|---------|
| **L0 完整** | 无缺失+上游输出齐全 | 完整庭审提纲 + 开庭陈述稿 + 法官提问预判表 |
| **L1 轻度** | 缺少推荐字段 | 完整庭审提纲 + 缺失处标注"[待补充]" |
| **L2 中度** | 上游输出全部缺失 | 7环节框架 + 全量占位标注 |
| **L3 重度→SOFT_DEGRADED** | 缺少必填字段 | 仅庭审提纲骨架 + 法定要素清单（C+D+G最小骨架） |

---

## 输入验证规则

| 规则 | 触发条件 | 处理 |
|------|---------|------|
| V-01 | `plaintiff_mark` 缺少任何子字段 | 交互补全 |
| V-02 | `infringement_summary` 为空 | 交互补全 |
| V-03 | 所有上游输出均缺失 | 不阻断，7环节框架先行+全量占位 |
| V-04 | 部分上游输出缺失 | 已就绪部分消费+缺失部分占位 |
| V-05 | `trial_duration_minutes` 超出合理范围 | 限制在60-480分钟 |
