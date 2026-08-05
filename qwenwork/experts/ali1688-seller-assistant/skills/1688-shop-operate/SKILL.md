---
name: 店铺经营健康诊断
name_en: 1688-shop-operate
displayName: 店铺经营健康诊断
version: "2.1.0"
description: |
  1688 店铺经营健康诊断能力。通过 MCP 查询核心指标、流量结构、行业交易排名、客户画像四维数据，再调用本地 Python 后处理脚本生成经营诊断报告。
description_zh: 基于 MCP 获取经营数据，并通过 Python 保留原脚本后处理口径生成诊断报告
user-invocable: true
argument-hint: 告诉我你想做店铺诊断，或指定近1天/近7天/近30天
---

# 1688 店铺经营健康诊断

## 职责边界

本技能采用「MCP 工具取数 + Python 脚本后处理」模式：

- 账号鉴权、Token 刷新、OAuth 授权全部由 MCP 连接器 `ali1688-seller` 管理。
- Agent 不处理 AK，不读取/保存 AK，不调用 `configure`、`get_ak`、`change_ak`、`authorize` 等授权命令。
- 经营数据必须通过 MCP 工具获取，禁止再通过 Python 脚本直接调用 HTTP API。
- MCP 返回后的结构校验、日期规则、行业模块跳过、字段格式化、章节重排、瓶颈诊断等后处理逻辑交给本技能 Python 脚本执行。

## MCP 连接器

- 连接器名称：`ali1688-seller`
- 协议：Streamable HTTP
- 本技能使用工具：`get_core_metrics`、`get_traffic_structure`、`get_transaction_ranking`、`get_customer_profile`

## 本地后处理脚本

- 脚本入口：`python3 {baseDir}/cli.py post_process_report --input-file <mcp_result.json>`
- 输入：包含 MCP 四路工具返回结果的 JSON 文件
- 输出：标准 JSON：`{"success": bool, "markdown": str, "data": {...}}`
- 用户可见内容：直接使用输出中的 `markdown`
- Agent 只能把 MCP 原始返回传给脚本，不得自行重写复杂报告逻辑

输入 JSON 结构：

```json
{
  "date_type": "RECENT_7",
  "get_core_metrics": {},
  "get_traffic_structure": {},
  "get_customer_profile": {},
  "get_transaction_ranking": {}
}
```

说明：

- 每个工具结果可以是 MCP 原始对象，也可以是 `{"success": true, "data": {"data": {...}}}` 这类包装结构。
- `RECENT_1` 不调用 `get_transaction_ranking`，输入中可省略 `get_transaction_ranking`。
- 脚本会按旧逻辑处理模块失败：单模块不可用时标注“数据暂不可用”，行业模块不可用时跳过行业章节并重排编号。

## 严格禁止 (NEVER DO)

- 不得编造任何经营数据，包括指标值、排名、百分位、趋势、行业标杆、客户数据。
- 不得在 MCP 或脚本失败时用估算值、历史记忆、模型推测补齐结果。
- 不得调用旧 Python 查询命令通过 HTTP 拉取经营数据，如 `get_core_metrics`、`get_traffic_structure`、`get_transaction_ranking`、`get_customer_profile`。
- 不得触发本技能内的 AK/OAuth 管理逻辑；鉴权异常只提示用户检查 `ali1688-seller` 连接器授权状态。
- 不得把 MCP 原始结构化数据直接全量倾倒给用户，必须通过 `post_process_report` 生成报告。
- 不得忽略日期类型限制：`get_transaction_ranking` 不支持 `RECENT_1`。

## 意图判断

### 触发本技能（满足任一）

- 用户提及：店铺诊断、经营诊断、健康诊断、经营分析、同行对比、店铺健康。
- 用户要求：分析最近经营表现、找经营瓶颈、输出提升建议。
- 用户希望按时间维度看经营情况：近1天、近7天、近30天。

### 不触发本技能

- 商品选品、找货、同款搜索、比价，应触发 `1688-product-find`。
- 商品发布、标题优化、主图优化、上下架，应触发 `1688-product-manage`。
- 下单、付款、履约、物流、售后、库存管理。

## 参数约束

公共规则：

- `device` 固定传 `ALL`
- 默认 `date_type = RECENT_7`

日期映射：

| 用户表达 | date_type |
|---|---|
| 近1天、昨天、最近一天 | `RECENT_1` |
| 近7天、最近一周、默认 | `RECENT_7` |
| 近30天、最近一个月 | `RECENT_30` |

各 MCP 工具的 `date_type` 白名单：

| 工具 | 支持值 |
|---|---|
| `get_core_metrics` | `RECENT_1`, `RECENT_7`, `RECENT_30` |
| `get_traffic_structure` | `RECENT_1`, `RECENT_7`, `RECENT_30` |
| `get_transaction_ranking` | `RECENT_7`, `RECENT_30` |
| `get_customer_profile` | `RECENT_1`, `RECENT_7`, `RECENT_30` |

参数不合法时直接提示用户使用近1天、近7天或近30天，不做隐式修正。

## 核心工作流

### Step 1：确定查询参数

1. 从用户请求中识别时间范围。
2. 未指定时使用 `RECENT_7`。
3. `device` 始终使用 `ALL`。
4. 若用户指定近1天（`RECENT_1`），后续跳过 `get_transaction_ranking`。

### Step 2：通过 MCP 并行获取数据

并行调用无数据依赖的 MCP 工具：

1. `get_core_metrics(date_type, device="ALL")`
2. `get_traffic_structure(date_type, device="ALL")`
3. `get_customer_profile(date_type, device="ALL")`
4. `get_transaction_ranking(date_type, device="ALL")`，仅当 `date_type != RECENT_1`

MCP 调用规则：

- 由 MCP 自动注入鉴权上下文。
- 工具返回错误时保留原始错误对象，不要自行兜底造数据。
- 除 `RECENT_1` 主动跳过行业排名外，其他工具都应尝试调用。

### Step 3：把 MCP 返回交给 Python 后处理

将 Step 2 的所有工具返回写入一个 JSON 文件，例如：

```json
{
  "date_type": "RECENT_7",
  "get_core_metrics": "<MCP get_core_metrics 原始返回>",
  "get_traffic_structure": "<MCP get_traffic_structure 原始返回>",
  "get_customer_profile": "<MCP get_customer_profile 原始返回>",
  "get_transaction_ranking": "<MCP get_transaction_ranking 原始返回>"
}
```

然后执行：

```bash
python3 {baseDir}/cli.py post_process_report --input-file <mcp_result.json>
```

必须使用脚本输出的 `markdown` 作为最终诊断报告。Agent 可以在报告后追加一句很短的交互引导，但不得修改报告里的指标、章节、判断、排名或改善方向。

### Step 4：脚本保留的后处理口径

`post_process_report` 必须保留以下旧逻辑：

1. **返回结构校验**
   - 每个工具结果必须能解析为对象。
   - 非对象按“格式异常，请稍后重试”处理。

2. **日期规则**
   - `get_transaction_ranking` 只支持 `RECENT_7`、`RECENT_30`。
   - `RECENT_1` 默认跳过行业定位章节。

3. **行业定位可用性判定**
   - 行业工具调用失败、返回为空、缺失 `industry_name` 时，跳过行业章节。
   - 跳过后，客户健康度与瓶颈诊断章节编号自动前移。

4. **趋势字段不完整兼容**
   - `get_core_metrics.trend` 可能缺失 `pay_cvr`、`pay_amount`。
   - 缺失项统一标注“数据暂不可用”，不得补造。

5. **统一输出格式**
   - 金额统一“元”，保留2位小数并带千分位，如 `¥125,000.00`。
   - 百分比保留1位小数。
   - 数据缺失统一标注“数据暂不可用”。
   - 报告章节顺序稳定，行业章节可跳过。

6. **瓶颈诊断**
   - 基于核心指标评级、流量结构、行业排名、客户复购等字段识别 1-3 个瓶颈。
   - 每个瓶颈必须包含数据依据和改善方向。
   - 数据不足时输出“数据完整性不足”类瓶颈，不得伪造业务结论。

## MCP 数据字段

### `get_core_metrics`

- `core_metrics`：7项核心指标。
- `trend`：同比、环比、较同行变化。

核心指标：

| metric_code | 指标名 |
|---|---|
| `impression` | 展现次数 |
| `visitor` | 访客数 |
| `page_view` | 浏览量 |
| `click_cvr` | 点击转化率 |
| `pay_cvr` | 支付转化率 |
| `buyer_count` | 支付买家数 |
| `pay_amount` | 支付金额 |

评级口径：

| 评级 | ratio_to_peer |
|---|---|
| 优秀 | `>= 1.1` |
| 持平 | `0.9 - 1.1` |
| 略低 | `0.5 - 0.9` |
| 极低 | `< 0.5` |

### `get_traffic_structure`

重点字段：来源排行、新老访客比、终端占比、跳失率、入店搜索词。

### `get_transaction_ranking`

重点字段：`industry_name`、`my_pay_amount`、`industry_rank`、`industry_total`、`rank_percentile`、`benchmark`。

### `get_customer_profile`

重点字段：买家数、L会员数、客户数、回头率、新老客 GMV、客单价。

## 报告输出要求

最终报告由脚本生成，结构如下：

```markdown
# 店铺经营健康诊断报告（{date_range 或 date_type}）

## 一、核心指标 vs 同行同层
...

## 二、流量结构分析
...

## 三、行业定位（当可用）
...

## 四、客户健康度（若行业定位不可用则编号前移）
...

## 五、瓶颈诊断与改善方向（若行业定位不可用则编号前移）
...
```

报告要求：

- 核心指标、流量结构、客户健康度为固定章节。
- 行业定位仅在 `get_transaction_ranking` 数据可用时出现。
- 单模块失败时该模块标注“数据暂不可用”，其他模块继续。
- 全部失败时脚本返回明确失败或“数据完整性不足”，不得生成伪报告。

## 错误处理

### MCP 工具调用/网关错误

| 场景 | 处理 |
|---|---|
| `401` / 鉴权失败 / 签名或令牌无效 | 提示用户检查 `ali1688-seller` 连接器是否已完成 OAuth 授权；不调用 AK 脚本 |
| `429` / 限流 | 建议等待 1-2 分钟后重试 |
| `400` / 参数错误 | 检查 `date_type` 是否符合白名单 |
| `500` / 服务异常 | 提示稍后重试 |

业务错误码命中以下之一时，也按连接器授权错误处理：

- `1688_token_expired`
- `1688_invalid_token`
- `1688_token_revoked`
- `1688_token_unauthorized`
- `1688_no_scope_specified`
- `1688_invalid_scope`

### Python 后处理错误

| 场景 | 处理 |
|---|---|
| 输入 JSON 缺失 | 重新构造 MCP 结果 JSON 后再调用脚本 |
| JSON 格式错误 | 修正 JSON 文件格式 |
| 脚本返回 `success: false` | 直接展示脚本 `markdown`，不要自行生成报告 |

## 参数补齐引导话术

> 默认按近7天做店铺健康诊断。你也可以指定时间范围：近1天、近7天、近30天。

## 免责声明

1. 技能运行结果可能因模型能力与上下文差异产生偏差，请对关键结论自行核验。  
2. 请妥善保管账号与授权信息，避免泄露导致损失。  
3. 不得篡改技能内容用于非授权用途。  
4. 平台不保证输出绝对准确、真实、时效，请谨慎使用。  
