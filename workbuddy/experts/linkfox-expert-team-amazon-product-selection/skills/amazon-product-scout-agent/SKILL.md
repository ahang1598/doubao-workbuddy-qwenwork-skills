---
name: amazon-product-scout-agent
description: >-
  亚马逊多轮选品侦察兵：使用卖家精灵数据按多维度条件筛选亚马逊商品，支持翻页续接、跨条件去重、智能条件推荐三大机制。
  当用户提到多轮选品、批量筛品、翻页找货、去重找新品、换条件再找、选品侦察、product scout、
  multi-round product selection、pagination dedup、condition switching、
  找更多商品、继续翻页、换个条件找、已找过的不要重复 时触发此技能。
  即使用户未明确提及"scout"，只要其需求涉及在同一对话中多轮获取不同商品且不重复，也应触发此技能。
---

# Amazon Product Scout Agent

多轮选品侦察兵：在同一对话中多轮获取亚马逊商品，**翻页续接**不重复拉取，**跨条件去重**过滤已见 ASIN，**智能推荐**不重叠的换条件方案。

## 核心概念

**三大机制**：

| 机制 | 触发场景 | 行为 |
|------|---------|------|
| 翻页续接 | 同条件继续要货 | 从上次最后一页+1开始，SQLite 记录 last_page |
| 跨条件去重 | 换了筛选条件 | 从第1页开始，SQLite 过滤已见 ASIN，只输出新商品 |
| 智能条件推荐 | 翻完或用户想换方向 | 基于API枚举推荐不重叠方案，等用户确认后执行 |

**数据源**：`linkfox-sellersprite-product-search`（卖家精灵选产品）

**定时任务**：配合 `linkfox-task-scheduler` 可实现每小时/每天自动选品

**输出格式**：CSV only，禁止 HTML 报告

**支持站点**：US, UK, DE, FR, JP, CA, IT, ES, MX, IN

## 参数指南

### 核心参数

| 参数 | 类型 | 说明 | 默认值 |
|------|------|------|--------|
| marketplace | string | 站点代码 | US |
| listedWithinLastMonths | int | 上架时间（月），枚举: 1/3/6/12/24 | 3 |
| minPrice / maxPrice | number | 价格区间 | - |
| maxWeights / minWeights | number | 重量区间 | - |
| weightUnit | string | 重量单位: g/kg/oz/lb | g |
| minUnits | int | 最低月销量 | - |
| fulfillment | string | 配送: AMZ/FBA/FBM | - |
| sellerNation | string | 卖家国籍: CN/HK/US等 | - |
| order.field | string | 排序字段（16种） | total_units |
| order.desc | string | "true"降序/"false"升序 | "true" |

### 排序字段枚举（16种）

total_units, total_amount, bsr_rank, price, rating, reviews, profit, reviews_rate, available_date, questions, total_units_growth, total_amount_growth, reviews_increasement, bsr_rank_cv, bsr_rank_cr, amz_unit

### 扩展参数

支持 `linkfox-sellersprite-product-search` 的全部参数，详见 `references/api-params-catalog.md`。

## 工作流

### 调用方式

```bash
# 默认运行（使用上次条件或初始默认）
python3 scripts/product_scout_agent.py

# 带参数运行
python3 scripts/product_scout_agent.py --marketplace UK --min-price 10 --max-price 30 --max-weight 500 --weight-unit g --min-units 151 --fulfillment FBA --seller-nation CN --listed-within-months 3

# 从参数文件运行
python3 scripts/product_scout_agent.py --params params.json

# 查看状态
python3 scripts/product_scout_agent.py --status

# 查看条件推荐（12大类91个选项）
python3 scripts/product_scout_agent.py --suggest

# 生成模板参数文件
python3 scripts/product_scout_agent.py --init-params

# 导出全部唯一 ASIN 为 CSV
python3 scripts/product_scout_agent.py --export-all

# 重置所有状态
python3 scripts/product_scout_agent.py --reset
```

### 每轮执行流程

1. **识别条件**：计算 query_hash，判断是"同条件续接"还是"新条件查询"
2. **翻页拉取**：同条件从 last_page+1 开始；新条件从第1页开始。每轮3页×100条=300条
3. **去重过滤**：每条结果与 SQLite 中已见 ASIN 比对，只保留新商品
4. **输出结果**：CSV 导出 + Top10 预览 + NEXT_STEPS_JSON
5. **智能推荐**：基于API参数枚举，推荐3个不重叠的换条件方案

### NEXT_STEPS_JSON 结构

每轮结束后输出结构化 JSON，供 agent 解析并告知用户：

```json
{
  "round": 1,
  "this_round_new": 300,
  "total_unique_so_far": 300,
  "current_condition": "£10-30 | ≤500g | 月销>151 | 近3月新品 | FBA | 卖家CN",
  "pagination": {
    "status": "available",
    "message": "当前条件还有更多商品可翻页获取",
    "can_continue": true,
    "next_page": 4
  },
  "alternatives": [
    {"label": "价格跳跃 £30-50", "desc": "完全不重叠的更高价格区间", "overlap": "无"},
    {"label": "扩重量 500-2000g", "desc": "打开更重品类空间", "overlap": "无"},
    {"label": "提销量门槛>450", "desc": "只看更高销量的头部爆款", "overlap": "低"}
  ],
  "already_explored": ["£10-30, ≤500g (翻到第3页)"],
  "call_to_action": "回复「继续」在当前条件下翻页获取更多 | 或选择一个新方案编号"
}
```

### Agent 使用指引

1. **用户说"找商品"**：用默认条件或用户指定条件运行脚本第一轮，输出 CSV
2. **用户说"继续"/"更多"**：同条件继续运行脚本（自动翻页续接）
3. **用户说"换个条件"**：运行 `--suggest` 获取推荐方案，用 `AskUserQuestion` 让用户选择
4. **脚本输出"EXHAUSTED"**：告知用户当前条件已翻完，运行 `--suggest` 推荐新方案
5. **用户说"定时选品"/"每天自动跑"**：用 `linkfox-task-scheduler` 创建定时任务
6. **每轮结束后**：解析 NEXT_STEPS_JSON，告知用户还有多少商品可翻页、有哪些备选方案
7. **禁止生成 HTML 报告**，所有结果只输出 CSV 数据

### 定时任务集成

配合 `linkfox-task-scheduler` 可实现自动化定时选品：

1. 先用 `--init-params` 生成参数文件
2. 用 `linkfox-task-scheduler` 创建定时任务，prompt 中包含脚本调用命令
3. 每次定时执行自动续接上次翻页位置（SQLite 持久化）
4. 结果 CSV 自动保存到会话目录

## 成本

每次 API 调用消耗 15 积分（由 `linkfox-sellersprite-product-search` 计费）。每轮3页=45积分。

**定时任务成本**：
- 每小时1轮 = 45积分/小时 = 1080积分/天
- 每2小时1轮 = 540积分/天
- 每天1轮 = 45积分/天

创建定时任务前必须告知用户成本并确认。

## 重要限制

- API 单页最多返回 100 条
- 同一参数组合有 24h 本地缓存
- SQLite 数据库持久化在会话目录，同一 SESSION_ID 下跨轮次有效
- 不同会话（SESSION_ID 变化）需重新建库
- **禁止生成 HTML 报告**，所有结果只输出 CSV

## 输出文件

| 文件 | 路径 | 说明 |
|------|------|------|
| SQLite DB | `<session>/data/scout_agent.db` | 去重库+查询状态+轮次记录 |
| 每轮 CSV | `<session>/data/scout_round{N}_new_products.csv` | 当轮新商品 |
| 全量 CSV | `<session>/data/scout_all_unique_products.csv` | 所有唯一 ASIN（`--export-all`） |
| 轮次摘要 JSON | `<session>/data/amazon-product-scout-agent-round{N}-*.json` | 轮次结果+Top20新品（`Saved full response` 协议） |
| 参数模板 | `<session>/data/scout_params_template.json` | `--init-params` 生成的模板 |
| SellerSprite JSON | `<session>/data/linkfox-sellersprite-product-search-*.json` | API 原始响应 |
