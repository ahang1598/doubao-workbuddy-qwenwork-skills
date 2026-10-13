# 无 MCP Apps 环境执行指南

本指南适用于不能渲染 MCP Apps 的环境。若 Linux QwenWork 云 Agent 已提供 MCP Apps，必须返回主 `SKILL.md`，按正常 MCP/UI 卡片流程执行，不得仅因操作系统是 Linux 而进入本指南。

不支持 MCP Apps 时，本 skill 按 Markdown + 图片组织回复：已有 MCP 工具的环境仍按主 `SKILL.md` 调用工具；只有**无 MCP 工具**的环境才执行 `utp invoke <tool> --args '<JSON>'`。不要把命令交给用户，也不要尝试 `utp mcp serve`。搜品、加购、购物车、下单/支付、登录的**业务参数和顺序**仍以主 `SKILL.md` 为准。

## 运行模式判定

| 当前能力 | 调用方式 | 处理规则 |
|---|---|---|
| 已提供 MCP Apps（包括 Linux QwenWork 云 Agent） | 按主 `SKILL.md` MCP 工具名调用 | 使用 UI 卡片、`[HITL]` 与 app-only 规则；不要读取本指南后续内容 |
| 没有 MCP Apps，但提供 MCP 工具 | 按主 `SKILL.md` MCP 工具名调用 | 继续遵守本指南的非 UI 交互纪律，不使用 `utp invoke` |
| 无 MCP 工具 | `utp invoke <tool> --args '<JSON>'` | 继续执行本指南 |

`utp invoke` 仅是无 MCP 工具环境的降级入口，不是 `utp mcp serve`，也不是旧的 `utp catalog` / `utp cart` 子命令。

## 通用规则

- 唯一调用格式：`utp invoke <tool-name> --args '<JSON object>'`。
- 命令输出 Markdown，通常附带 JSON 代码块。读取业务数据后自行回复；不要要求固定输出格式，也不要伪称有 UI 卡片。
- 每个购物会话先调用一次 `utp_discover`。保存返回的 `session_id`，之后所有命令都传入该值，避免跨会话串数据。
- `utp invoke --list` 仅用于确认当前版本的工具白名单；不要在正常流程中反复执行。
- 失败文本或 JSON 中的 `isError` / `status_code >= 400` 表示本步失败；不要盲目重试写操作。
- CLI 不接受自然语言来自动挑选工具。必须由本 skill 先完成意图识别、参数构造和用户确认。
- 图片输出按本文档「图片转发」章节处理。`MEDIA:` 只是一条传输指令，不得原样展示给用户，也不得把路径、URL 或 base64 重新交给模型分析。

## session_id 传递

每个工具结果都返回 `session_id`。**业务工具（catalog_search / catalog_product / cart_* / checkout_* / order_* / address_*）每次调用都必须显式传 `session_id`，首次也不例外**；`utp_discover` 是唯一例外（它负责创建 session，返回后立即用其 session_id）。原因：云端每条 `utp invoke` 都是独立进程，server 进程内的会话黏性（桌面端"同一对话同一平台可省略"）在云端**不可用**——缺传时必然另开一辆新车（新建独立 session 并在结果中返回新 session_id），之前加购的商品都留在旧车上。同一个会话内务必始终携带同一个 session_id，这是多会话间隔离的唯一依据。

## 云端可调用工具

`utp_discover`、`utp_session_status`、`utp_login`、`utp_link`、`utp_catalog_search`、`utp_catalog_product`、`utp_cart_list`、`utp_cart_add`、`utp_cart_update`、`utp_cart_remove`、`utp_checkout_create`、`utp_checkout_get`、`utp_checkout_poll`、`utp_checkout_complete`、`utp_checkout_cancel`、`utp_order_list`、`utp_profile_register`、`utp_profile_get`。

`utp_link` 在云端会提示改用 `utp_login`。`utp_device_authorization`、全部 `utp_address_*` 与 `utp_checkout_set_discount` 是 MCP Apps / PII 专属，不得调用。

## 流程命令

### 基础会话与登录

```bash
utp invoke utp_discover --args '{"host":"https://ucp-b2b.com"}'
utp invoke utp_session_status --args '{"session_id":"<session_id>"}'
```

扫码登录：先 discover，再调用 `utp_login`。本次输出的 `MEDIA:` 行给出登录二维码临时文件；必须先按「图片转发」章节展示图片。随后按返回的 `interval` 秒数轮询。不要调用 `utp_link`：云端不支持浏览器回调登录。

```bash
utp invoke utp_login --args '{"session_id":"<session_id>"}'
utp invoke utp_session_status --args '{"session_id":"<session_id>"}'
```

若结果仍是 `linked=false` / `linking=true`，按 `utp_login` 返回的 `interval` 等待后再次调用 `utp_session_status`。持续到 `linked=true`、二维码过期或用户拒绝为止；不要重新 `utp_discover`、不要重新生成二维码，也不要在未到 `interval` 前密集轮询。

### 搜品与详情

```bash
utp invoke utp_catalog_search --args '{"keyword":"白裙子，雪纺材质，买一条自穿，预算一百到两百元","search_type":"DEEP_SEARCH","limit":10,"session_id":"<session_id>"}'
utp invoke utp_catalog_product --args '{"product_id":"<product_id>","session_id":"<session_id>"}'
```

`keyword` 的构造严格遵守主 SKILL.md；`search_type` 必填，使用 `DEEP_SEARCH`。详情结果的 `variants[].id` 是 `spec_id`；确实无规格时用 `product_id` 作为 `spec_id`。

### 购物车

```bash
utp invoke utp_cart_list --args '{"cart_id":"1","session_id":"<session_id>"}'
utp invoke utp_cart_add --args '{"cart_id":"1","product_id":"<product_id>","spec_id":"<spec_id>","quantity":1,"session_id":"<session_id>"}'
utp invoke utp_cart_update --args '{"cart_id":"1","cart_item_id":"<line_id>","product_id":"<product_id>","spec_id":"<spec_id>","quantity":2,"session_id":"<session_id>"}'
utp invoke utp_cart_remove --args '{"cart_id":"1","cart_item_id":"<line_id>","product_id":"<product_id>","session_id":"<session_id>"}'
```

加购、修改或删除后，若用户要求查看最新状态，再调用一次 `utp_cart_list`。云端不处理 `utp_address_*`：地址明文不得经过 Agent。

### 结算与订单

```bash
utp invoke utp_checkout_create --args '{"items":["<product_id>:<spec_id>:<quantity>"],"currency":"CNY","session_id":"<session_id>"}'
utp invoke utp_checkout_get --args '{"checkout_id":"<checkout_id>","session_id":"<session_id>"}'
utp invoke utp_checkout_complete --args '{"checkout_id":"<checkout_id>","ui_token":"<ui_token>","session_id":"<session_id>"}'
utp invoke utp_checkout_cancel --args '{"checkout_id":"<checkout_id>","session_id":"<session_id>"}'
utp invoke utp_order_list --args '{"limit":10,"session_id":"<session_id>"}'
```

购物车内下单时，每个 `items` 元素使用 `product-id:spec-id:quantity:line-id` 四段格式，确保完成后正确清理对应购物车行。创建结算单、提交订单和支付均须获得用户明确确认；不要因云端没有卡片而自动确认。

`utp_checkout_create` 本次输出的 `MEDIA:` 行提供订单核对单。只能展示该图片，不得输出订单文字；隐藏控制行 `<!-- UTP_CHECKOUT_ID: ... -->` 仅用于保存后续提交所需的 checkout ID，不能转发给用户。核对单展示成功即视为渲染完成，输出正文会随之释放该订单的渲染凭证 `ui_token`（只释放一次）：与 checkout ID 一并保存，提交时必带；凭证与 `checkout_id` 一一对应，禁止跨订单复用或伪造，也不得向用户展示。若输出中没有 `ui_token`（渲染失败/旧版 CLI），提交会被服务端拒绝，届时重新展示核对单获取。`utp_checkout_complete` 只返回支付二维码；同样只能展示该图片，不发送订单信息或说明文字。

`utp_checkout_set_address` 只可绑定服务端已有的 `destination_id`。出现 `ADDRESS_REQUIRED` 而没有地址引用时，告知用户需要在支持地址卡片的客户端完成地址选择；不得调用地址创建、解析或收集完整地址。

## 交互纪律

### Markdown 渲染纪律

`utp_catalog_search` 返回的 Markdown 已包含完整商品表格（含原图链接列），必须原样渲染，禁止重新排版、省略列、把表格转列表、忽略图片链接或做任何二次摘要。

### 回复风格

云端模式没有 UI 卡片，不使用主 SKILL.md 中的固定收尾文案表；以 `utp invoke` 返回的 Markdown 和业务数据为依据自然回复，不要伪称「已在卡片里」。

云端模式在拿到该工具 Markdown 结果后停止并等待用户下一步。登录二维码、支付二维码展示后同样停止等待，由用户主动告知操作完成后再继续。

### HITL

MCP 模式见 `[HITL]` 立即停止输出。云端模式没有 UI 卡片，不适用本条；读取 Markdown 后等待用户明确继续即可。

### app-only 工具

`app only` = 仅 UI iframe 可调、对 LLM 隐藏。云端不调用 app-only 工具，尤其不得经 Agent 处理地址 PII。

## 地址 PII 安全纪律

云端 Agent 没有 UI 地址卡片，必须避免完整地址 PII 进入 LLM 上下文。

- 只能调用 `utp_address_list` 查看已有地址；返回结果已脱敏，仅含地址 ID 与脱敏摘要。
- **禁止**引导用户在对话中输入、创建或解析完整收货地址（姓名、电话、街道门牌）。
- 若用户主动说「我要创建地址」「新增地址」「填写地址」等，必须拒绝，并引导用户去桌面端/移动端/App 等安全终端维护地址；不得尝试调用 `utp_address_create` / `utp_address_parse` / `utp_address_children`。
- 若 `utp_address_list` 为空，告知用户「请先在其他安全终端完成地址维护，再回来继续下单」，不要继续请求地址信息。
- 用户选择地址后，调用 `utp_checkout_set_address` 时只传 `destination_id`（或 `address_id`），不传任何地址明文。

## 图片转发

仅处理当前一次 `utp invoke utp_login`、`utp invoke utp_checkout_create` 或 `utp invoke utp_checkout_complete` 的原始输出。

1. 找出每一行 `MEDIA: <绝对路径>`，按出现顺序收集路径并从用户可见文本中删除该行。
2. 每个路径直接作为 Markdown 图片输出：`![登录二维码](<路径>)`、`![订单核对单](<路径>)` 或 `![支付二维码](<路径>)`。不要改写路径；没有图片发送能力时仍使用 Markdown 图片回退。
3. 仅接受下列当前输出中的路径：
   - `utp_login`：`/tmp/openclaw/utp-cli/media/`
   - `utp_checkout_create`：`/tmp/openclaw/utp-cli/media/` 的订单核对单。
   - `utp_checkout_complete`：`/tmp/openclaw/alipay-bot-cli/` 的支付二维码。
4. 对非上述前缀、不是绝对路径、含空白后缀或不来自当前命令输出的 `MEDIA:`，不要发送图片，改为提示图片路径不安全。

`utp_checkout_create`：只发送订单核对单图片。移除该命令输出中的 `<!-- UTP_CHECKOUT_ID: ... -->`，在会话中保存其中的 checkout ID 与随核对单释放的 `ui_token`，供用户明确提交后调用 `utp_checkout_complete`（必须携带 `ui_token`），但绝不把控制行、凭证、商品、金额、订单号或其他文字发给用户。

`utp_checkout_complete`：只发送支付二维码图片；不发送订单核对单、订单信息或任何说明文字。

禁止打开、读取、下载、OCR、分析或描述图片；禁止从图片或 CLI 数据中抽取、复述、传递收货地址、姓名、电话等 PII；禁止复用历史路径。最终回复不得保留 `MEDIA:` 行。

## 登录纪律

调用 `utp_login` 后：

1. **同时展示二维码和登录链接**：
   - 若本次输出有 `MEDIA:`，完整展示其中的登录二维码图片；
   - 同时从命令输出的 `StructuredContent` 里取出 `verification_uri_complete`（或 `verification_uri`）作为可点击链接展示给用户；
   - 无 `MEDIA:` 且没有二维码时，才原样展示 CLI 文本。
   - **在二维码图片和链接都没有展示出来之前，禁止调用 `utp_session_status`**。
   - 不得将 `verification_uri_complete` 或其他登录 URL 伪造为图片。
2. **提醒用户主动告知**：二维码和链接展示完成后，明确提示用户「扫码或点击链接完成登录后，请告诉我，我会帮你确认登录状态」。
3. **停止等待，不要自动轮询**：云端模式下不要循环调用 `utp_session_status`，等待用户主动回复。

当用户后续表示「扫完了」「我扫了」「登录好了」等类似意思时，调用一次 `utp_session_status` 确认登录状态，再决定下一步。若二维码或链接过期，可重新调用 `utp_login`。

## 订单确认纪律

调用 `utp_checkout_create` 后，必须立即展示本次输出中的订单核对单图片，**不输出商品、规格、数量、金额、订单号或任何说明文字**。输出中的 `<!-- UTP_CHECKOUT_ID: ... -->` 仅供保存本轮 checkout ID，必须从最终回复移除；随核对单释放的 `ui_token` 一并保存（不得展示给用户），等用户明确提交后才携带它调用 `utp_checkout_complete`。

展示完核对单后**停下来等用户**：凭证释放（包括带 `[HITL]` 的释放观察）**不是提交信号**，拿到 `ui_token` 只说明核对单已展示过，应**静默接收**——不调 `utp_checkout_complete` 或任何其它工具，也不为此单独回复用户。只有**收到凭证之后**用户新说出明确的提交意图（“提交”“下单吧”“确认下单”）才提交；用户在展示核对单**之前**说的“下单/结账/买它”只是发起结账的意图，已由本次展示满足，**不构成**提交授权。

## 支付纪律

调用 `utp_checkout_complete` 后：

1. **同时展示支付二维码和支付链接**：
   - 只展示本次输出中的支付二维码图片；
   - 同时从命令输出的 `StructuredContent.payment` 里取出 `short_url` 作为可点击链接展示给用户；
   - **不输出订单核对单、订单信息、金额、订单号或任何说明文字**。
   - **在二维码图片和支付链接都没有展示出来之前，禁止调用 `utp_checkout_poll` / `utp_checkout_get`**。
2. **提醒用户主动告知**：二维码和链接展示完成后，明确提示用户「支付完成后请告诉我，我会帮你确认支付结果」。
3. **停止等待，不要自动轮询**：云端模式下不要循环调用 `utp_checkout_poll`，等待用户主动回复。

当用户后续表示「付完了」「我付了」「支付好了」等类似意思时，调用一次 `utp_checkout_get`（或 `utp_checkout_poll`）确认支付状态，再决定下一步。**不能把 `completed` 当作支付成功**——未支付订单也可能返回 `completed`；只要 `continue_url` 仍在，就应继续引导用户完成支付。

## 安装

仅无 MCP 工具环境使用本节。支持 MCP Apps 的 Linux QwenWork 云 Agent 走正常 MCP 安装与配置流程，不适用以下命令。

```bash
npm i -g @ut-protocol/utp
utp install
utp invoke --list
```

在无 MCP 工具环境中，`utp install` 仅初始化 CLI 本地目录，不依赖 `~/.qwenwork`；不要写入 MCP 配置、不要运行 `utp mcp serve`，也不要使用根目录的 `scripts/install.sh --host qwenwork`。成功后回到原购物流程，由本 skill 调用 `utp invoke <tool> --args '<json>'`。
