---
name: Amazon关键词研究
slug: proboost-amazon-keyword-research
version: 1.0.0
displayName: Amazon关键词研究
name_en: proboost-amazon-keyword-research
description: >
  使用OpenBoost数据，挖掘Amazon关键词并分析搜索趋势、ABA排名、月度表现和Google趋势，形成分层关键词清单。当用户询问关键词拓展、趋势或搜索需求时使用。
description_en: "Using OpenBoost data, mine and analyze Amazon keywords using search trends, ABA rankings, monthly research and Google Trends."
argument-hint: "Amazon站点、种子关键词或ASIN，以及目标时间范围"
argument-hint-en: "Amazon marketplace, seed keyword or ASIN, and target date range"
user-invocable: "true"
---

# Amazon关键词研究

## 适用场景

从种子词扩展关键词，并判断需求强弱、趋势和搜索意图。

## 前置依赖

本技能优先使用 **Proboost Amazon MCP**，连接器 Key 为 `proboost-Amazon-mcp`。

### Step 0 — Proboost MCP就绪检查（每次必做）

1. 检查 `proboost-Amazon-mcp` 是否已连接，并读取实时工具清单与真实 schema。
2. 若已连接，使用该 MCP 完成任务，不猜测参数名，不用网页或模型知识补造数据。
3. 若未连接、401/403 或 token 失效，先提示：**“请先绑定并连接 proboost-Amazon-mcp；连接完成后我可以直接查询 OpenBoost 数据。”**
4. 如果暂时无法绑定，可接受用户提供的 CSV、XLSX、JSON、截图或平台导出文件继续分析；报告必须注明“用户提供数据 / 离线降级”，只分析材料中实际存在的字段。
5. 若既无可用 MCP 也无用户材料，只输出所需输入模板并停止，不编造结论。

## 最少输入

- Amazon站点（必填）
- 种子关键词或ASIN（至少一项）
- 时间范围与用途（可选）

连接检查通过或降级数据确认后再补问缺失的必填项；一次只问完成任务所必需的信息。

## 执行步骤

1. 用关键词挖掘工具扩展种子词。
2. 读取关键词研究结果和趋势。
3. 用ABA周/月数据与月度研究交叉验证需求变化。
4. 必要时查看Google趋势，按核心词、长尾词和场景词输出。

## Proboost MCP工具

连接通过后，先读取Proboost MCP的实时工具清单和真实schema，再调用工具；不得猜参数名，也不得切换数据源。使用当前环境对应的MCP工具发现、schema读取和调用能力。

| 工具 | 用途 |
|---|---|
| `amz_keyword_miner` | 扩展关键词 |
| `amz_keyword_research` | 读取关键词指标 |
| `amz_keyword_research_trends` | 分析Amazon搜索趋势 |
| `amz_aba_research_trends` | 分析ABA趋势 |
| `amz_aba_research_weekly` | 查看ABA周度数据 |
| `amz_research_monthly` | 查看月度研究数据 |
| `amz_google_trends` | 补充站外趋势 |

## 判断规则

- 趋势、搜索排名和相关性分开评价，热度高但不相关的词不纳入核心词。
- ABA和Google趋势口径不同，不直接混成一个数值。
- 关键词分层必须写明依据，不编造搜索量或转化率。

## 输出格式

按下面顺序输出，优先用短表格和明确结论：

1. 研究口径
2. 关键词分层表
3. 趋势变化
4. ABA证据
5. 搜索意图
6. 建议用法
7. 数据缺口

## 常见错误与数据边界

- 未绑定、未连接或认证失败：按 Step 0 提示绑定；无法绑定时仅使用用户提供材料做离线降级。
- 工具超时或5xx：原参数最多重试1次；仍失败就写明失败工具、影响范围和可重试建议，不补造结果。
- 结果为空：最多放宽1个非关键筛选条件再查1次；仍为空就如实说明。
- 每个数字都保留单位、站点/国家、时间范围和工具返回口径；预测值、推断和事实分开写。
- 完成后用一句话概括结果，并注明“数据来源：Proboost MCP”。
