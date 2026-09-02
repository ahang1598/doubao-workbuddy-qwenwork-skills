# 输入规格：criminal-prosecution-defense

> 刑事辩护意见书 | Step3产出 | 版本: v3.2.0

## 1. 输入模型

### 1.1 宽容摄取原则

接受6种输入形态：结构化(I1)/自然语言(I2)/混合式(I3)/渐进式(I4)/模板填充(I5)/最小化(I6)

### 1.2 交互补全（最多3轮）

| 轮次 | 触发条件 | 询问内容 |
|------|----------|----------|
| R1 | 缺少必填字段 | "请补充：①涉嫌罪名 ②辩护方向（innocent/lesser_crime/procedural/mitigated/comprehensive）③主要辩护要点" |
| R2 | 辩护依据不充分 | "请补充：①证据分析意见 ②法律适用论证 ③从轻/减轻情节" |
| R3 | 量刑意见缺失 | "请补充：①建议的量刑意见 ②是否有认罪认罚意向" |

3轮后仍不足 → SOFT_DEGRADED

---

## 2. 字段定义

### 2.1 必填字段（5个）

| # | 字段名 | 类型 | 说明 |
|---|--------|------|------|
| F1 | suspect_name | string | 犯罪嫌疑人姓名 |
| F2 | alleged_crime | string | 涉嫌罪名（即suspected_crime） |
| F3 | defense_direction | enum | 辩护方向：innocent / lesser_crime / procedural / mitigated / comprehensive |
| F4 | case_facts | text | 案件基本事实 |
| F5 | defense_points | array[text] | 辩护要点/理由 |

### 2.2 推荐字段（3个）

| # | 字段名 | 类型 | 说明 | 默认值 |
|---|--------|------|------|--------|
| R1 | evidence_analysis | text | 证据分析意见 | 从case_facts推断 |
| R2 | legal_arguments | text | 法律适用论证 | 从defense_type推断 |
| R3 | mitigating_factors | array[string] | 从轻/减轻处罚情节 | 从case_facts提取 |

### 2.3 可选字段（2个）

| # | 字段名 | 类型 | 说明 | 默认值 |
|---|--------|------|------|--------|
| O1 | sentencating_suggestion | text | 量刑建议意见 | 无 |
| O2 | case_stage | enum | 审查起诉内具体阶段 | pre_indictment |

---

## 3. 输入验证规则

### 3.1 硬拒绝条件

| # | 条件 | 处理 |
|---|------|------|
| HR-01 | 要求保证无罪判决结果 | 拒绝+说明理由 |
| HR-02 | 要求捏造或歪曲证据 | 拒绝+说明理由 |
| HR-03 | 要求对办案人员人身攻击 | 拒绝+说明理由 |

### 3.2 软降级条件

| # | 条件 | 降级方式 |
|---|------|----------|
| SD-01 | 仅姓名+罪名 | C档→G档 |
| SD-02 | 辩护类型不明确 | D档+提示选择 |
| SD-03 | 无法判断案件基本事实 | D档+框架填充 |
