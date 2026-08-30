---
name: Amazon ASIN综合诊断
slug: proboost-amazon-asin-analysis
version: 1.0.0
displayName: Amazon ASIN综合诊断
name_en: proboost-amazon-asin-analysis
description: >
  使用OpenBoost数据，综合诊断Amazon ASIN的商品、销量、评论、竞品、关键词和流量结构，输出问题清单与改进顺序。当用户要求分析单个ASIN或竞品ASIN时使用。
description_en: "Using OpenBoost data, diagnose an Amazon ASIN across product, sales, reviews, competitors, keywords and traffic structure."
argument-hint: "Amazon站点、ASIN，以及可选的竞品ASIN和关注问题"
argument-hint-en: "Amazon marketplace, ASIN, optional competitor ASINs and key concerns"
user-invocable: "true"
---

# Amazon ASIN综合诊断

## 适用场景

把一个ASIN的商品、销售、口碑、竞品和流量证据合成可执行诊断。

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
- 目标ASIN（必填）
- 竞品ASIN或关注问题（可选）

连接检查通过或降级数据确认后再补问缺失的必填项；一次只问完成任务所必需的信息。

## 执行步骤

1. 读取目标ASIN的商品与销量信息。
2. 查询评论和竞品，找出卖点、痛点和差异。
3. 查询流量词、关键词排名和关联Listing。
4. 把问题按证据强弱和行动优先级整理，明确缺失数据。

## Proboost MCP工具

连接通过后，先读取Proboost MCP的实时工具清单和真实schema，再调用工具；不得猜参数名，也不得切换数据源。使用当前环境对应的MCP工具发现、schema读取和调用能力。

| 工具 | 用途 |
|---|---|
| `amz_sku_query` | 读取商品信息 |
| `amz_sales_query` | 读取销量相关数据 |
| `amz_review_query` | 分析评论反馈 |
| `amz_product_competitor` | 查找竞品 |
| `amz_traffic_keyword_stat` | 统计流量词 |
| `amz_traffic_keyword` | 读取流量词明细 |
| `amz_keyword_order` | 查看关键词排名 |
| `amz_traffic_listing_page` | 查看关联Listing页面 |
| `amz_traffic_listing_stat` | 统计关联Listing |

## 判断规则

- 每条诊断必须对应商品、销量、评论、竞品或流量证据。
- 没有Listing正文、广告报表或成本数据时，只给线索，不宣称完成Listing、广告或利润诊断。
- 事实、推断和建议分开写。

## 输出格式

按下面顺序输出，优先用短表格和明确结论：

1. ASIN概况
2. 销量表现
3. 评论与用户痛点
4. 竞品差异
5. 关键词与流量
6. 问题优先级
7. 行动清单
8. 数据边界

## 常见错误与数据边界

- 未绑定、未连接或认证失败：按 Step 0 提示绑定；无法绑定时仅使用用户提供材料做离线降级。
- 工具超时或5xx：原参数最多重试1次；仍失败就写明失败工具、影响范围和可重试建议，不补造结果。
- 结果为空：最多放宽1个非关键筛选条件再查1次；仍为空就如实说明。
- 每个数字都保留单位、站点/国家、时间范围和工具返回口径；预测值、推断和事实分开写。
- 完成后用一句话概括结果，并注明“数据来源：Proboost MCP”。
