---
name: Amazon流量结构分析
slug: proboost-amazon-traffic-analysis
version: 1.0.0
displayName: Amazon流量结构分析
name_en: proboost-amazon-traffic-analysis
description: >
  使用OpenBoost数据，分析Amazon ASIN的流量来源、关键词排名、流量词、扩展词和关联Listing，输出流量结构与优化线索。当用户询问ASIN流量来源或关键词表现时使用。
description_en: "Using OpenBoost data, analyze an Amazon ASIN's traffic sources, keyword ranks, traffic terms, extensions and related listings."
argument-hint: "Amazon站点、ASIN，以及可选的关键词和时间范围"
argument-hint-en: "Amazon marketplace, ASIN, and optional keywords and date range"
user-invocable: "true"
---

# Amazon流量结构分析

## 适用场景

弄清ASIN的流量从哪里来、由哪些词和关联页面贡献，并找出优化线索。

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
- ASIN（必填）
- 重点关键词或时间范围（可选）

连接检查通过或降级数据确认后再补问缺失的必填项；一次只问完成任务所必需的信息。

## 执行步骤

1. 读取ASIN流量来源和关键词排名。
2. 查询流量关键词统计与关键词明细。
3. 扩展相关流量词，并分析关联Listing页面和统计。
4. 按来源、词组和页面输出流量结构、风险和机会。

## Proboost MCP工具

连接通过后，先读取Proboost MCP的实时工具清单和真实schema，再调用工具；不得猜参数名，也不得切换数据源。使用当前环境对应的MCP工具发现、schema读取和调用能力。

| 工具 | 用途 |
|---|---|
| `amz_traffic_source` | 读取流量来源 |
| `amz_keyword_order` | 查看关键词排名 |
| `amz_traffic_keyword_stat` | 统计流量关键词 |
| `amz_traffic_extend` | 扩展相关流量词 |
| `amz_traffic_keyword` | 读取关键词明细 |
| `amz_traffic_listing_page` | 分析关联Listing页面 |
| `amz_traffic_listing_stat` | 统计关联Listing |

## 判断规则

- 只按工具返回的来源类型命名，不擅自把未知来源判断为自然或广告流量。
- 排名、流量份额和转化是不同概念，工具没返回转化时不做转化结论。
- 同时标记头部集中风险和长尾扩展机会。

## 输出格式

按下面顺序输出，优先用短表格和明确结论：

1. ASIN与站点
2. 流量来源
3. 核心流量词
4. 关键词排名
5. 关联Listing
6. 优化线索
7. 数据边界

## 常见错误与数据边界

- 未绑定、未连接或认证失败：按 Step 0 提示绑定；无法绑定时仅使用用户提供材料做离线降级。
- 工具超时或5xx：原参数最多重试1次；仍失败就写明失败工具、影响范围和可重试建议，不补造结果。
- 结果为空：最多放宽1个非关键筛选条件再查1次；仍为空就如实说明。
- 每个数字都保留单位、站点/国家、时间范围和工具返回口径；预测值、推断和事实分开写。
- 完成后用一句话概括结果，并注明“数据来源：Proboost MCP”。
