# 刑事电子证据分析 — 输入规格

> 本节遵循 compiler/ssot.md §17（SSOT）：可维护度约束

## 1. 必需输入

| # | 字段 | 类型 | 必填 | 说明 | 法律含义 |
|---|------|------|------|------|---------|
| 1 | `case_name` | string | 是 | 案件名称 | 标识分析对象 |
| 2 | `alleged_crime` | string | 是 | 涉嫌罪名 | 决定罪名路由（T1-T5/通用） |
| 3 | `evidence_list` | array | 是 | 电子证据清单 | 分析的核心对象 |

### evidence_list 条目结构

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 是 | 证据名称（如"微信聊天记录"） |
| `form` | string | 是 | 证据形式（扣押手机/截图/鉴定意见/数据报告/银行流水等） |
| `source` | string | 否 | 证据来源（侦查机关/鉴定机构/被害人提供等） |
| `hash_value` | string | 否 | 完整性校验值（MD5/SHA-1/SHA-256） |
| `content_summary` | string | 否 | 关键内容摘要 |
| `timestamp` | string | 否 | 时间戳/时间范围 |
| `media_info` | string | 否 | 存储介质信息 |
| `collection_method` | string | 否 | 收集提取方式（扣押/现场提取/在线提取/远程勘验/调取等） |

## 2. 可选输入

| # | 字段 | 类型 | 说明 | 法律含义 |
|---|------|------|------|---------|
| 1 | `crime_type` | enum | 罪名类型：T1(电诈)/T2(网赌)/T3(洗钱)/T4(非集)/T5(职务侵占)/通用 | 决定专攻审查点 |
| 2 | `hash_values` | object | 全案哈希值集合 {证据编号: 哈希值} | 完整性核验依据 |
| 3 | `forensic_report` | string | 鉴定意见关键结论 | 鉴定意见四要素审查 |
| 4 | `media_inventory` | string | 介质扣押清单内容 | 载体识别+扣押程序审查 |
| 5 | `case_file_list` | string | 案卷材料列表 | 多源印证参考 |
| 6 | `defense_perspective` | string | 辩护视角（无罪/罪轻/量刑） | 分析侧重方向 |
| 7 | `identity_mapping` | object | 已知身份映射（微信号→姓名等） | 主体同一性分析参考 |
| 8 | `timeline_events` | array | 已知时间线事件 | 时间线重建参考 |

## 3. 输入形态

本技能接受文本输入，支持以下3种形态：

### 形态1：结构化文本（基础）

用户手工整理的 evidence_list，直接作为输入。

### 形态2：截图内容文本（中等）

用户将微信/QQ/支付宝聊天截图经OCR提取后的文本内容，作为 evidence_list 条目的 content_summary 输入。

> **说明**：OCR提取为平台能力，非本技能职责。本技能接受OCR后的文本结果。

### 形态3：鉴定意见文本（高级）

用户将电子数据鉴定意见书、介质扣押清单经平台解析后的文本内容，作为 forensic_report 和 media_inventory 输入。

> **说明**：PDF解析为平台能力，非本技能职责。本技能接受解析后的文本结果。

## 4. 输入校验规则

| # | 校验项 | 规则 | 失败处理 |
|---|--------|------|---------|
| 1 | case_name 非空 | string, len > 0 | 提示补充 |
| 2 | alleged_crime 非空 | string, len > 0 | 提示补充 |
| 3 | evidence_list 非空 | array, len ≥ 1 | 阻断，至少1项电子证据 |
| 4 | 证据形式可识别 | form ∈ 已知枚举 | 标注为"未识别形式"，继续分析 |
| 5 | crime_type 合法 | enum ∈ {T1,T2,T3,T4,T5,通用} | 自动推断为"通用" |

## 5. 缺失降级路径

**策略**：classified_handling（分类处理）

| 缺失项 | 影响 | 降级动作 |
|--------|------|---------|
| hash_values 缺失 | A2完整性核验维度受限 | 标注"未提供哈希值，原始性可质疑"，风险等级提升 |
| forensic_report 缺失 | 鉴定意见四要素审查无法进行 | 跳过鉴定意见专项审查，标注"未提供鉴定意见" |
| media_inventory 缺失 | A1载体识别维度受限 | 基于evidence_list推断载体，标注"未提供扣押清单" |
| crime_type 缺失 | 无罪名专攻审查点 | 自动走通用路由，不影响12维度框架 |
| defense_perspective 缺失 | 分析侧重方向不明 | 按综合视角分析，所有C组维度均输出 |
