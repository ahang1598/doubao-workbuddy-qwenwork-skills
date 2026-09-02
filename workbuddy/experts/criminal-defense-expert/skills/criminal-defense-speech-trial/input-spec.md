# 输入规格

> 本文件定义 criminal-defense-speech-trial 技能的完整输入参数规格
> 遵循 compiler/ssot.md §17（SSOT）：输入宽容度契约

## 1. 必需输入

| 字段 | 类型 | 枚举值 | 说明 | 验证规则 |
|------|------|--------|------|----------|
| `defendant_name` | string | - | 被告人姓名 | 非空 |
| `alleged_crime` | string | - | 涉嫌罪名 | 非空 |
| `defense_direction` | enum | 无罪/罪轻/程序 | 辩护方向 | 必须为枚举值 |
| `defense_points` | string | - | 辩护要点 | 非空 |

## 2. 可选输入

### 2.0 案件事实

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `case_facts` | string | [待补充] | 案件事实 |

### 2.1 被告人信息

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `defendant_gender` | string | [待补充] | 性别 |
| `defendant_age` | string | [待补充] | 年龄 |
| `defendant_custody` | boolean | true | 是否在押 |
| `prior_record` | boolean | false | 是否有前科 |

### 2.2 控方指控

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `prosecution_facts` | string | [待补充] | 指控事实 |
| `prosecution_evidence` | array[string] | [] | 控方主要证据 |
| `prosecution_law` | array[string] | [] | 控方适用法条 |
| `sentencing_request` | string | [待补充] | 检察院量刑建议 |

### 2.3 辩方材料

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `defense_evidence` | array[string] | [] | 辩方证据 |
| `mitigating_factors` | array[string] | [] | 从轻/减轻情节 |
| `cross_exam_results` | string | [待补充] | 质证结果概要 |
| `defendant_statement` | string | [待补充] | 被告人最后陈述要点 |

### 2.4 辩护律师

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `defense_lawyer` | string | [待补充] | 辩护律师姓名 |
| `lawyer_firm` | string | [待补充] | 律师事务所 |

## 3. 输入宽容度契约

| 最小输入 | 处理方式 |
|----------|----------|
| 仅被告+罪名+方向+辩护要点 | 生成辩护词框架 |
| 仅"辩护词"/"一审" | 询问案件信息 |
| 上游产物 | 消费criminal-case-reading-notes/criminal-evidence-analysis |

交互补全最多3轮。

## 4. 场景适配规则

### 4.1 辩护三层次

| defense_direction | 辩护核心 | 论证重点 |
|-------------|----------|----------|
| 无罪 | 事实之辩 | 证据不足/事实不清/不构成犯罪 |
| 罪轻 | 定罪之辩 | 此罪彼罪/定性不当 |
| 程序 | 程序之辩 | 程序违法/非法证据排除 |

### 4.2 庭审阶段适配

| 庭审环节 | 辩护词对应 | 重点 |
|----------|-----------|------|
| 法庭调查 | 质证意见 | 证据三性/证明力 |
| 法庭辩论 | 辩护词 | 事实认定/法律适用/量刑 |
| 最后陈述 | 被告人自行 | 辩护人可辅助准备 |

---

*本文件遵循 compiler/ssot.md §17（SSOT）：输入宽容度契约*
