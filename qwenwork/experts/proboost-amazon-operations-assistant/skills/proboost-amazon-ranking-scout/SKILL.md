---
name: Amazon榜单机会发现
slug: proboost-amazon-ranking-scout
version: 1.0.0
displayName: Amazon榜单机会发现
name_en: proboost-amazon-ranking-scout
description: >
  使用OpenBoost数据，浏览Amazon热销榜类目树和榜单，结合ASIN、销量、竞品与关键词数据发现榜单机会。当用户询问热销榜、新品榜或榜单选品时使用。
description_en: "Using OpenBoost data, scout Amazon ranking lists and validate opportunities with ASIN, sales, competitor and keyword data."
argument-hint: "Amazon站点、榜单类型和类目，以及可选的筛选条件"
argument-hint-en: "Amazon marketplace, ranking type, category and optional filters"
user-invocable: "true"
---

# Amazon榜单机会发现

## 适用场景

从Amazon榜单找到候选，再用商品、销量、竞品和关键词证据做二次验证。

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
- 榜单类型与类目（必填）
- 价格、评分或上架时间要求（可选）

连接检查通过或降级数据确认后再补问缺失的必填项；一次只问完成任务所必需的信息。

## 执行步骤

1. 读取热销榜类目树，确认类目节点。
2. 查询指定榜单并形成候选ASIN列表。
3. 读取候选ASIN商品和销量信息，并查询竞品。
4. 补充关键词需求，输出榜单机会与风险。

## Proboost MCP工具

连接通过后，先读取Proboost MCP的实时工具清单和真实schema，再调用工具；不得猜参数名，也不得切换数据源。使用当前环境对应的MCP工具发现、schema读取和调用能力。

| 工具 | 用途 |
|---|---|
| `amz_hot_amz_hot_cat_tree` | 读取榜单类目树 |
| `amz_hot_amz_hot_list_v2` | 读取榜单商品 |
| `amz_sku_query` | 读取候选ASIN详情 |
| `amz_sales_query` | 验证销量相关信息 |
| `amz_product_competitor` | 验证竞争情况 |
| `amz_keyword_research` | 验证搜索需求 |

## 判断规则

- 上榜只代表当前榜单表现，不自动等于长期机会。
- 至少用销量、竞品或关键词中的两个维度二次验证。
- 榜单时间点、站点和类目必须写清楚。

## 输出格式

按下面顺序输出，优先用短表格和明确结论：

1. 榜单口径
2. 候选ASIN
3. 销量验证
4. 竞争验证
5. 关键词验证
6. 机会排序
7. 榜单时效风险

## 常见错误与数据边界

- 未绑定、未连接或认证失败：按 Step 0 提示绑定；无法绑定时仅使用用户提供材料做离线降级。
- 工具超时或5xx：原参数最多重试1次；仍失败就写明失败工具、影响范围和可重试建议，不补造结果。
- 结果为空：最多放宽1个非关键筛选条件再查1次；仍为空就如实说明。
- 每个数字都保留单位、站点/国家、时间范围和工具返回口径；预测值、推断和事实分开写。
- 完成后用一句话概括结果，并注明“数据来源：Proboost MCP”。
