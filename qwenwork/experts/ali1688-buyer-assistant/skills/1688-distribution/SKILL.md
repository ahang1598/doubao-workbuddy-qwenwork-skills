---
name: 分销经营
name_en: 1688-distribution
displayName: 分销经营
version: "2.0.0"
description: |
  1688 分销唯一主入口。选品铺货、订单管理、知识库查询、店铺绑定，涵盖分销全链路。
  当用户提到铺货、选品、分销、上架、查订单、催发、旺旺、发货流程、绑店时触发。
  不要在用户仅询问非1688业务（如闲聊、天气、翻译等无关话题）时触发。
description_zh: 1688分销全链路——选品铺货、订单管理、知识库查询、店铺绑定
user-invocable: true
argument-hint: 描述您的分销需求，如"帮我选几个热销商品铺到我的淘宝店"
---

# 1688 分销

## 处理边界

本 Skill 采用 **MCP 调用 + Python 后处理** 两段式流程：

1. **鉴权与 API 调用全部交给 MCP 连接器 `ali1688-buyer`**。Agent 不处理 AK、本地 Token、browser_use 授权、签名或 HTTP 请求。
2. **业务后处理必须交给 Python 脚本**。Agent 不直接解析 MCP 原始返回、不自行生成商品/订单/店铺/铺货结果表格。

## MCP 连接器

- 连接器名称：`ali1688-buyer`
- 本技能使用的 MCP 工具：
  - `distribution_select_offer`
  - `same_img_offer_search`
  - `distribution_offer_info`
  - `shop_and_tool_info`
  - `distribute_offer`
  - `fx_query_order`
  - `fx_send_ww`
  - `fx_ww_reply`
  - `distribution_knowledge_tool`
- `__userId__` 等用户身份参数由 MCP 网关自动注入，Agent 不手动传递。

## 命令入口

统一入口：

```bash
python3 {baseDir}/scripts/cli.py <业务域> <动作> [--参数] --mcp-result-file /tmp/mcp.json
```

也支持 stdin：

```bash
cat /tmp/mcp.json | python3 {baseDir}/scripts/cli.py <业务域> <动作> [--参数]
```

所有命令输出 JSON：

```json
{"success": true, "markdown": "...", "data": {...}}
```

Agent 展示给用户时必须完整输出 `markdown` 字段。除非用户明确要求分析，禁止追加“后续建议”“后续操作”“操作指引”等自创内容。

## 严格禁止

- 禁止配置、读取、提示用户粘贴或管理 AK。
- 禁止调用旧 `_http.py`、旧鉴权脚本、浏览器或网页搜索引擎请求 1688 分销数据。
- 禁止在 MCP 调用失败后自行通过外部网站补充商品、店铺、订单、供应商或链接信息。
- 禁止由 AI 直接改写 MCP 原始返回为最终结果；必须调用 Python 后处理脚本输出 `markdown`。
- 禁止编造数据/链接，所有数据必须来自 MCP 返回或 Python 后处理结果。
- 禁止未经确认执行铺货；铺货不可逆，必须用户明确确认商品和目标店铺。
- 禁止品牌未授权商品铺货：`isBrandOffer=true` 且 `isBrandAuth=false` 绝对不能铺货。
- 禁止擅自添加筛选条件、改写用户原话、猜测渠道和店铺。

## 意图判断

| 用户意图 | 业务域/动作 | MCP 工具 | 参考文档 |
|---------|-------------|----------|----------|
| 关键词选品 | `product_search_helper search` | `distribution_select_offer` | [scripts/biz/product_search_helper/reference.md](scripts/biz/product_search_helper/reference.md) |
| 图片选品 | `product_search_helper search` | `same_img_offer_search` | [scripts/biz/product_search_helper/reference.md](scripts/biz/product_search_helper/reference.md) |
| 商品分销参谋 | `offer_info query` | `distribution_offer_info` | [scripts/biz/offer_info/reference.md](scripts/biz/offer_info/reference.md) |
| 店铺/工具查询 | `shop_info query` | `shop_and_tool_info` | [scripts/biz/shop_info/reference.md](scripts/biz/shop_info/reference.md) |
| 铺货执行 | `distribute_helper execute` | `distribute_offer` | [scripts/biz/distribute_helper/reference.md](scripts/biz/distribute_helper/reference.md) |
| 查询订单 | `order_helper query` | `fx_query_order` | [scripts/biz/order_helper/reference.md](scripts/biz/order_helper/reference.md) |
| 旺旺催发 | `order_helper send` | `fx_send_ww` | [scripts/biz/order_helper/reference.md](scripts/biz/order_helper/reference.md) |
| 查询旺旺回复 | `order_helper query_reply` | `fx_ww_reply` | [scripts/biz/order_helper/reference.md](scripts/biz/order_helper/reference.md) |
| 分销知识库 | `knowledge_helper query` | `distribution_knowledge_tool` | [scripts/biz/knowledge_helper/reference.md](scripts/biz/knowledge_helper/reference.md) |

判断不清时优先询问用户意图，不要猜测。与 1688 分销无关的话题不触发本技能。

## 参考文档（按业务域按需加载）

各业务域的字段映射、接口规范、流程细节集中在 `scripts/biz/<业务域>/reference.md`。命中对应业务域时，Agent 必须先加载并阅读该 `reference.md`，再构造 MCP 参数与 Python 后处理调用。

| 业务域 | 参考文档 | 适用场景 |
|--------|---------|---------|
| 选品助手 | [scripts/biz/product_search_helper/reference.md](scripts/biz/product_search_helper/reference.md) | 关键词选品、图片选品的字段筛选与展示规范 |
| 商品分销参谋 | [scripts/biz/offer_info/reference.md](scripts/biz/offer_info/reference.md) | 单品分销决策因子（价格、运费、品牌授权、体验分等） |
| 店铺信息 | [scripts/biz/shop_info/reference.md](scripts/biz/shop_info/reference.md) | 三方分销工具与可用店铺过滤规则 |
| 铺货执行 | [scripts/biz/distribute_helper/reference.md](scripts/biz/distribute_helper/reference.md) | 铺货参数构造、错误码处理、品牌授权校验 |
| 订单助手 | [scripts/biz/order_helper/reference.md](scripts/biz/order_helper/reference.md) | 订单/退款查询、风险识别、旺旺催发与回复 |
| 知识库助手 | [scripts/biz/knowledge_helper/reference.md](scripts/biz/knowledge_helper/reference.md) | 渠道/工具枚举、知识库召回与总结流程 |

加载原则：

- 仅加载当前用户意图命中的业务域 `reference.md`，不要一次性加载全部。
- 同一会话中跨业务域时按需追加加载对应 `reference.md`。
- `reference.md` 与本 SKILL.md 内容冲突时，以本 SKILL.md 的处理边界与禁止项为准；业务字段、参数枚举、错误码映射以 `reference.md` 为准。

## MCP + Python 后处理映射

| 场景 | MCP 调用后执行 |
|------|---------------|
| 关键词选品 | `python3 scripts/cli.py product_search_helper search --filters='[...]' --page_size=20 --mcp-result-file /tmp/mcp.json` |
| 图片选品 | `python3 scripts/cli.py product_search_helper search --image_url="https://..." --page_size=20 --mcp-result-file /tmp/mcp.json` |
| 分销参谋 | `python3 scripts/cli.py offer_info query --offer_id=123 --decision=true --mcp-result-file /tmp/mcp.json` |
| 店铺查询 | `python3 scripts/cli.py shop_info query --mcp-result-file /tmp/mcp.json` |
| 铺货 | `python3 scripts/cli.py distribute_helper execute --app_key=... --shop_code=... --channel=... --offer_ids=... --mcp-result-file /tmp/mcp.json` |
| 订单查询 | `python3 scripts/cli.py order_helper query --mcp-result-file /tmp/mcp.json` |
| 旺旺发送 | `python3 scripts/cli.py order_helper send --question="..." --order_ids=... --mcp-result-file /tmp/mcp.json` |
| 回复查询 | `python3 scripts/cli.py order_helper query_reply --task_id=... --mcp-result-file /tmp/mcp.json` |
| 知识库 | `python3 scripts/cli.py knowledge_helper query --query="用户原话" --channel="default" --business="default" --mcp-result-file /tmp/mcp.json` |

## Python 后处理职责

本目录保留原有复杂后处理逻辑：

- 选品：解析关键词/图搜结果、截断展示数量、为品牌未授权商品注入 `brandAuthUrl`。
- 分销参谋：提取价格、运费、品牌授权、支持渠道、体验分、履约率、保障服务等决策因子。
- 店铺查询：过滤已过期工具和过期授权店铺，生成店铺列表。
- 铺货：解析 `errorCode`、成功/失败/未处理商品 ID，生成稳定铺货结果文案。
- 订单查询：翻译订单状态/退款状态，识别风险订单，生成订单统计和风险明细。
- 旺旺：校验消息和订单参数、解析任务 ID、解析商家回复列表。
- 知识库：校验渠道/工具名称，解析 JSON 字符串型文档列表。

Agent 不得复刻或替代以上逻辑。

## 选品铺货流程

1. 用户提出选品/铺货需求。
2. Agent 构造 MCP 参数并调用 `distribution_select_offer` 或 `same_img_offer_search`。
3. 将 MCP 原始返回交给 `product_search_helper search` 后处理。
4. 对候选商品调用 `distribution_offer_info`，再用 `offer_info query --decision=true` 后处理。
5. 若商品 `isBrandOffer=true` 且 `isBrandAuth=false`，标记不可铺货，禁止继续铺货。
6. 调用 `shop_and_tool_info` 并用 `shop_info query` 后处理可用店铺。
7. 用户确认商品和目标店铺后，调用 `distribute_offer`。
8. 将铺货 MCP 返回交给 `distribute_helper execute` 后处理并完整输出 `markdown`。

## 订单流程

- 查询订单：调用 `fx_query_order`，再用 `order_helper query` 生成订单统计、风险订单和退款明细。
- 催发催揽：从查询结果中的风险订单生成催发消息，用户确认后调用 `fx_send_ww`，再用 `order_helper send` 后处理任务 ID。
- 查询回复：调用 `fx_ww_reply`，再用 `order_helper query_reply` 后处理回复状态。

## 知识库流程

1. 识别用户 query、渠道、工具。
2. 用户未明确渠道/工具时传 `default`，不要猜测。
3. 调用 `distribution_knowledge_tool`。
4. 用 `knowledge_helper query` 解析和统计结果。

## 错误处理

### MCP 调用失败

1. 原样展示 MCP 返回的错误信息。
2. 鉴权、401、Forbidden、token 过期等错误：提示用户检查 `ali1688-buyer` 连接器 OAuth 授权，必要时在连接器设置中重新授权。
3. 限流、超时、服务异常：提示稍后重试。
4. 禁止提示用户配置 AK。
5. 禁止浏览器、网页搜索或旧 HTTP 脚本降级。

### Python 后处理失败

- 直接输出脚本返回的 `markdown`。
- 参数缺失时按脚本错误提示补齐。
- 不要手动重试，不要使用其他工具补充，不要编造数据。

## 安全声明

- 本技能不涉及任何 AK / Token 的本地存储和管理。
- 所有鉴权流程通过 MCP 连接器 `ali1688-buyer` 的 OAuth 机制完成。
- Agent 不应接触、存储或传输用户凭证。

## 免责声明

分销商品、店铺、订单和知识库数据来自 1688 平台。本技能仅作信息展示和操作辅助，不对商品质量、价格准确性、供应商资质、下游平台规则或交易结果做任何保证，用户应自行核实并承担交易风险。
