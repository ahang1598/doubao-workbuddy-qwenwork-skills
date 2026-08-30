---
name: Amazon产品机会筛选
slug: proboost-amazon-product-research
version: 1.0.0
displayName: Amazon产品机会筛选
name_en: proboost-amazon-product-research
description: >
  使用OpenBoost数据，结合Amazon选品、竞品、销量、评论和BSR预测数据筛选产品机会，输出候选、证据与风险。当用户询问Amazon选品、产品机会或竞品验证时使用。
description_en: "Using OpenBoost data, screen Amazon product opportunities using product selection, competitor, sales, review and BSR-prediction data."
argument-hint: "站点、种子关键词或类目，以及可选的价格和竞争要求"
argument-hint-en: "Marketplace, seed keyword or category, and optional price and competition requirements"
user-invocable: "true"
---

# Amazon产品机会筛选

## 适用场景

用需求、竞争、趋势和评论证据筛选Amazon产品机会。

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
- 种子关键词、类目或ASIN（至少一项）
- 价格带或竞争要求（可选）

连接检查通过或降级数据确认后再补问缺失的必填项；一次只问完成任务所必需的信息。

## 执行步骤

1. 先用选品工具形成候选池。
2. 查询候选竞品，并读取关键ASIN的商品和销量信息。
3. 读取评论，提炼需求、痛点和差异化方向。
4. 在适用时查看BSR销量预测，给出候选优先级和待验证项。

## Proboost MCP工具

连接通过后，先读取Proboost MCP的实时工具清单和真实schema，再调用工具；不得猜参数名，也不得切换数据源。使用当前环境对应的MCP工具发现、schema读取和调用能力。

| 工具 | 用途 |
|---|---|
| `amz_product_selection` | 形成候选产品池 |
| `amz_product_competitor` | 查找与比较竞品 |
| `amz_sku_query` | 读取ASIN商品信息 |
| `amz_sales_query` | 读取销售相关数据 |
| `amz_sales_prediction_bsr` | 用BSR辅助判断销量 |
| `amz_review_query` | 读取评论与用户痛点 |

## 判断规则

- 至少用需求、竞争和用户反馈中的两个维度验证候选。
- BSR预测是估算值，必须标记为预测，不当作官方销量。
- 没有采购、物流、广告和退货成本时，不给出确定利润结论。

## 输出格式

按下面顺序输出，优先用短表格和明确结论：

1. 筛选条件
2. 候选产品表
3. 需求证据
4. 竞争格局
5. 评论痛点
6. 机会排序
7. 成本与数据缺口

## 常见错误与数据边界

- 未绑定、未连接或认证失败：按 Step 0 提示绑定；无法绑定时仅使用用户提供材料做离线降级。
- 工具超时或5xx：原参数最多重试1次；仍失败就写明失败工具、影响范围和可重试建议，不补造结果。
- 结果为空：最多放宽1个非关键筛选条件再查1次；仍为空就如实说明。
- 每个数字都保留单位、站点/国家、时间范围和工具返回口径；预测值、推断和事实分开写。
- 完成后用一句话概括结果，并注明“数据来源：Proboost MCP”。
