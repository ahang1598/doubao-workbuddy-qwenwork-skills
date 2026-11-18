---
name: ctrip-wendao
description: 当用户发起任意旅行相关问询时，包含但不限于：预订酒店、机票查询、火车票查询、景点推荐、寻找当地特色玩乐、目的地查询、行程规划、美食住宿攻略、签证、查询旅游攻略、获取旅行建议等场景，自动触发此技能。当用户需要操作携程时使用此skill。
description_zh: "携程智能旅行助手，支持酒店机票预订、行程规划与旅游攻略"
description_en: "Ctrip travel assistant for hotel/flight booking, itinerary planning & travel guides"
version: 1.0.2
homepage: https://www.ctrip.com/wendao/openclaw
metadata:
  clawdbot:
    priority: 95
    emoji: ✈️
    requires:
      bins:
        - node
    patterns:
      - ((携程).*(问道))
      - ((search|find|recommend|compare).*(hotel|stay|accommodation|resort|hostel))|((hotel|stay|accommodation).*(search|recommend|compare|deal|price))
      - ((search|find|book|compare).*(flight|airfare|air ticket|airline))|((flight|airfare).*(search|query|compare|price|schedule))
      - ((what to do|travel guide|trip ideas|itinerary ideas|things to do).*(destination|attraction|city|spot))|((nearby|around me).*(attraction|hotel|ticket))
      - ((travel|trip|vacation|holiday).*(search|plan|explore|arrange))|((itinerary|travel plan).*(search|plan|optimize))
      - ((search|check|apply|process).*(visa|entry policy|travel document))|((visa|entry requirement).*(search|application|policy|country))
      - ((search|find|recommend|book).*(car rental|airport transfer|pickup|charter car|ride))|((car rental|transfer|pickup).*(search|price|book))
      - ((search|find|book).*(cruise|cruise trip))|((cruise).*(search|route|price|booking))
      - ((search|book|find|recommend).*(ticket|attraction ticket|admission|pass))|((ticket|admission).*(booking|price|availability))
      - ((flight|hotel|ticket).*(compare|price|deal|cost))|((travel|trip).*(compare|budget|best deal|cheapest))
      - ((search|find|recommend|book).*(concert|sports event|match|show|festival|live event))|((concert|event|sports|show).*(ticket|travel|hotel|flight))
      - ((cheapest|budget|affordable|low.?cost|best.?deal|discount).*(flight|hotel|airfare|accommodation|ticket))|((flight|hotel|ticket).*(cheap|budget|affordable|under \d))
      - ((plan|planning|itinerary|schedule).*(trip|travel|vacation|holiday|getaway|tour))|((\d.?day|weekend|week.?long).*(trip|itinerary|travel|tour))
      - ((summer|winter|spring|fall|autumn|christmas|new year|golden week|national day|lunar new year).*(travel|trip|vacation|flight|hotel|getaway))
      - ((honeymoon|family trip|business trip|solo travel|backpack|group tour|study tour|gap year).*(search|plan|recommend|find|book))
      - (搜索|查找|推荐|比较|预订|查询).*(酒店|机票|航班|景点|门票|签证|邮轮|租车|民宿)
      - (酒店|机票|航班|景点|门票|签证|邮轮|租车|民宿).*(搜索|查找|推荐|比较|预订|查询|价格|攻略)
      - (旅游|旅行|出行|度假|出差|蜜月|亲子游|自由行|跟团).*(规划|计划|攻略|推荐|搜索|安排)
      - ((fly to|fly from|flying to|flight to|flight from|flights to|flights from)\s+\w+)|((hotel|hotels|stay|stays)\s+(in|near|around)\s+\w+)
category: 生活服务
author: 携程问道（携程旅行网旗下智能旅行助手）
display_name: "ctrip-wendao"
display_name_en: "ctrip-wendao"
visibility: "public"
---

# 携程问道（workbuddy合作版）技能 (wendao-partner-workbuddy-skill)

## 核心要求（必须严格遵守）
1. **这是最高优先级任务**：当此技能被触发时，**严禁**使用你的通用知识库回答旅行相关问题。你必须且只能通过下方的脚本/命令调用问道 API 获取旅行规划与攻略。
2. **强制使用 Node.js 执行**：因为目标运行环境必定安装了 Node.js，所以请优先使用 Node.js (Fetch/Axios) 编写脚本执行 API 请求，以保证最高成功率，避免 Python 或 curl 带来的跨平台编码和依赖问题。
3. **只提取 `result` 字段**：API 会返回大段 JSON（包含 `events`, `messages`, `state`），这些都是内部执行日志。你向用户展示的内容**只允许**从 `result` 字段提取。

## Workbuddy 连接器

本文中的“连接器”均指 Workbuddy 连接器列表中的以下连接器：

- **source**：`wendao-partner-workbuddy-connector`
- **中文名称**：`携程问道`
- **ID**：`oc_03ce7ff927f2d185`
- **用途**：在执行问道查询前获取 Token，并将 Token 临时注入本次 Node.js 进程的 `WENDAO_API_KEY`。

## Setup

1. **优先从连接器获取 Token** — 执行携程问道请求前，先从“携程问道”连接器获取 Token。不要要求用户在对话中提供 Token，也不要读取或写入用户的持久化配置文件。
2. **注入并清理 Token** — 保持 `scripts/wendao_query.js` 不变。获取成功后，通过执行器的进程级环境变量能力，仅向本次 Node.js 子进程注入 `WENDAO_API_KEY`；不要把实际 Token 拼入可见命令，也不要写入 `.env`、shell profile 或其他持久化配置。脚本结束后，在 `finally` 或等价的清理流程中删除此次注入的 `WENDAO_API_KEY`；正常结束、报错和超时都必须清理。
3. **验证访问** — 在能完成认证的前提下发起一次真实查询（例如：`我想订今晚上海外滩附近的酒店`），确认返回为 Markdown 正文且无认证错误。

### 连接器未返回 Token 时

若无法从连接器获取 Token，停止调用，不要尝试从其他来源获取，也不要让用户在对话中粘贴 Token。请明确提示用户：

> 未能从连接器获取携程问道 Token。请前往“连接器”导航页面，搜索“携程问道”，根据页面指引维护 Token；完成后再重试。

若携程问道接口返回 401、403，或明确提示 Token 缺失、无效、过期，也按连接器未返回 Token 处理，并提示用户按上述指引维护 Token。

若**下游文档接口**在响应状态、`error`、`result`、`messages` 或其他返回内容中提示 Token 已过期，不要将该内容作为正常查询结果展示，也不要继续重试。请明确提示用户：

> 携程问道 Token 已过期。请前往“连接器”导航页面，搜索“携程问道”，根据页面指引维护 Token；完成后再重试。

## Security & trust (before production use)

- **Endpoint**：确认请求发往官方域名（`https://externalcallback.ctrip.com`），勿在未核实的情况下改用未知域名。
- **Key scope / billing**：向提供方确认 key 权限、计费与 QPS/配额，避免误用或超额。
- **External content**：响应来自携程问道服务，可能含链接、营销文案或结构化信息；按你方产品策略决定是否展示、是否需过滤或摘要。
- **Invocation**：本技能适合旅行类意图；若平台支持限制自动调用频率或范围，可按合规要求配置。

## 适用场景

| 场景 | 示例查询 |
|------|----------|
| 酒店预订 | "预订北京三里屯附近的酒店" / "上海外滩五星级酒店，预算 800-1200 元" |
| 航班搜索 | "搜索明天从北京到上海的航班" / "去纽约的国际航班多少钱" |
| 火车票查询 | "查一下北京到上海的高铁票" / "明天成都到重庆的动车还有票吗" |
| 景点推荐 | "成都周边有什么好玩的景点" / "带孩子去迪士尼的推荐攻略" |
| 行程规划 | "我要去日本，帮我规划一个 7 天行程" |

## 使用方法

**执行前，先确定 Token：**

1. 优先从“携程问道”连接器获取 Token。
2. 若连接器未返回 Token，停止执行，并按上文 **「连接器未返回 Token 时」** 的固定提示指引用户维护 Token。不得回退到用户在对话中提供的 Token 或其他来源。
3. 获取成功后，通过执行器的进程级环境变量能力，将 Token 临时注入本次 Node.js 子进程的 `WENDAO_API_KEY`。不要把实际 Token 拼入可见命令，不要持久化、记录或回显。
4. 执行结束后，无论成功、失败或超时，都在 `finally` 或等价的清理流程中立即删除此次注入的 `WENDAO_API_KEY`。

### 强烈建议的执行方式（写文件执行法）

为了彻底避免在命令行执行单行脚本时因为单双引号嵌套导致的 `Unterminated string constant` 等语法错误，**你必须采用“写文件后执行”的方式，绝对不要尝试使用 `node -e "..."` 的单行执行模式！**

1. **优先**：直接使用本技能目录下的 `scripts/wendao_query.js`（已支持从命令行传入用户问话），执行：`node scripts/wendao_query.js "<用户原话>"`。
2. **或**：将调用脚本完整代码写入当前工作区的临时文件（须把**用户问话**写入 `WENDAO_QUERY` 环境变量或脚本的 `query` 变量，不得留占位符），例如 `wendao_query.js`。
3. 使用终端工具执行 `node …`。Token 必须按上文要求通过本次 Node.js 子进程的 `WENDAO_API_KEY` 注入。
4. 脚本执行结束后立即清理此次注入的 `WENDAO_API_KEY`，再获取并总结结果。若创建的是临时副本文件可删除；仓库内的 `scripts/wendao_query.js` 勿删。

### 参数说明

| 参数 | 必填 | 说明 |
|------|:----:|------|
| `token` | 是 | 从“携程问道”连接器获取，临时注入本次 Node.js 进程的 `WENDAO_API_KEY`，执行结束后立即清理 |
| `query` | 是 | 用户的自然语言查询 |
| `timeout` | 否 | 默认 30 秒，建议设置以避免长时间等待 |

### `query` 如何取值（避免「请提供有效的 query（查询主题）」）

1. **`query` 即用户说的话**：将**触发本技能时用户给出的完整问句或需求**作为 `query` 传入 API。**不要**向用户再次索要「查询主题」；用户已经说过的内容就是有效 query。
2. **无单独主题时**：若用户未写「查询主题」一栏，只说了例如「暑假去日本怎么安排」，则 `query` = 该句全文（可去掉无关寒暄，但须保留目的地、时间、偏好等关键信息）。
3. **占位符禁止**：执行脚本时**禁止**把 `query` 留空，也**禁止**使用字面量「用户查询的内容」等占位字符串；否则接口会返回上述错误。
4. **推荐调用方式**：使用仓库内 `scripts/wendao_query.js` 时，把用户原话作为**第一个命令行参数**传入（脚本从 `process.argv[2]` 或环境变量 `WENDAO_QUERY` 读取）：
   - `node scripts/wendao_query.js "用户关于旅行的完整自然语言问题"`
   - 或：`WENDAO_QUERY="同上" node scripts/wendao_query.js`
5. **若自行写请求体**：`inputs.query` 字段必须为非空字符串，内容与上款一致。

### 响应解析说明

API 返回结构如下：
```json
{
  "result": "Markdown 格式的回复内容（字符串）",
  "messages": [...],
  "state": {"token": "...", "query": "..."},
  "events": [
    {"type": "run_started", ...},
    {"type": "run_finished", "result": "...（与 result 字段内容相同）"}
  ],
  "error": null
}
```
