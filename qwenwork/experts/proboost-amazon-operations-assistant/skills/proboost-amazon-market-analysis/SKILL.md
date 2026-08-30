---
name: Amazon类目市场分析
slug: proboost-amazon-market-analysis
version: 1.0.0
displayName: Amazon类目市场分析
name_en: proboost-amazon-market-analysis
description: >
  使用OpenBoost数据，分析Amazon类目规模、价格、商品、卖家、品牌、上架时间和评分结构，输出市场格局与进入风险。当用户询问Amazon类目研究或市场容量时使用。
description_en: "Using OpenBoost data, analyze Amazon category size, price, products, sellers, brands, listing age and rating structure."
argument-hint: "Amazon站点、类目关键词或类目节点，以及分析范围"
argument-hint-en: "Amazon marketplace, category keyword or node, and analysis scope"
user-invocable: "true"
---

# Amazon类目市场分析

## 适用场景

全面描述Amazon类目规模、结构、竞争和进入门槛。

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
- 类目关键词或类目节点（必填）
- 时间或样本范围（可选）

连接检查通过或降级数据确认后再补问缺失的必填项；一次只问完成任务所必需的信息。

## 执行步骤

1. 查询类目并确认节点口径。
2. 读取市场研究和总体统计。
3. 依次分析价格、商品、卖家、卖家类型/地区、品牌、上架时间与评分。
4. 汇总规模、集中度、成熟度和进入风险。

## Proboost MCP工具

连接通过后，先读取Proboost MCP的实时工具清单和真实schema，再调用工具；不得猜参数名，也不得切换数据源。使用当前环境对应的MCP工具发现、schema读取和调用能力。

| 工具 | 用途 |
|---|---|
| `amz_category_query` | 查询类目 |
| `amz_category_query_v2` | 补充类目节点信息 |
| `amz_market_research` | 读取市场研究数据 |
| `amz_market_statistics` | 读取总体统计 |
| `amz_market_price` | 分析价格结构 |
| `amz_market_goods` | 分析商品结构 |
| `amz_market_seller` | 分析卖家集中度 |
| `amz_market_seller_type` | 分析卖家类型 |
| `amz_market_seller_location` | 分析卖家地区 |
| `amz_market_brand` | 分析品牌集中度 |
| `amz_market_shelf_time` | 分析上架时长 |
| `amz_market_shelf_trend` | 分析上架趋势 |
| `amz_market_ratings` | 分析评分分布 |
| `amz_market_rating` | 读取评分统计 |

## 判断规则

- 类目节点、站点和样本范围必须写在报告开头。
- 集中度、上架时长和评分结构共同用于判断成熟度，不用单一指标下结论。
- 样本数据不能直接等同整个市场，必须说明覆盖范围。

## 输出格式

按下面顺序输出，优先用短表格和明确结论：

1. 类目口径
2. 市场规模
3. 价格与商品结构
4. 卖家与品牌格局
5. 上架与评分结构
6. 机会与风险
7. 数据边界

## 常见错误与数据边界

- 未绑定、未连接或认证失败：按 Step 0 提示绑定；无法绑定时仅使用用户提供材料做离线降级。
- 工具超时或5xx：原参数最多重试1次；仍失败就写明失败工具、影响范围和可重试建议，不补造结果。
- 结果为空：最多放宽1个非关键筛选条件再查1次；仍为空就如实说明。
- 每个数字都保留单位、站点/国家、时间范围和工具返回口径；预测值、推断和事实分开写。
- 完成后用一句话概括结果，并注明“数据来源：Proboost MCP”。
