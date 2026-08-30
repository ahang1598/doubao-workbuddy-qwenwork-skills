# 结账与下单指南

> 用户要下单/结账/直接购买时读本文件，读完按此执行。

## 创建 checkout：Normal vs ByCart

一律通过 `items` 逐项指定商品，按**商品来源**选方式：

| 情形 | 方式 | spec_id 来源 | line_id（items 第4段） |
|------|------|-------------|---------------------|
| 商品**在购物车里**（全部或部分，含卡片内加购的） | **ByCart** | 直接取该 `LineItem` 的 `Spec` 字段，不必重查详情 | **必带** |
| 商品**不在购物车**（直接点名新商品、DIRECT_BUY） | **Normal** | 从 catalog / ACTION_PRODUCT 取 | 不带 |

```json
// Normal：每项 "product-id:quantity" 或 "product-id:spec-id:quantity"
toolName: "utp_checkout_create"
arguments: { "items": ["948603919228:f218a50d:2"], "currency": "CNY" }
```
```json
// ByCart：每项 "product-id:spec-id:quantity:line-id"（line_id 取自 cart_list 对应行的 LineItem）
toolName: "utp_checkout_create"
arguments: { "items": ["948603919228:f218a50d:2:7019739720001"], "currency": "CNY" }
```

- 🔴 **ByCart 必须带第4段 `line_id`**：服务端只删除带 line_id 的购物车行，漏带会导致下单成功但购物车不清空
- "下单全部购物车" = 所有购物车行（带 line_id）都列进 `items`
- `cart_scope` 须与加购/查看时一致
- 返回带 `[HITL]`，停止输出

## 结账流程

1. **确认范围**：用户指定了商品按指定；说"结账"但购物车有历史商品 → 优先结算本次会话加购的并向用户确认；"全部结账" → 全部
2. **创建**（见上）。状态判断：`ready_for_complete` → 等用户在卡内确认；`incomplete` → 提取错误信息告知原因并停止；`requires_escalation` → 告知需在商家页面完成
3. **完成**：`utp_checkout_complete({ "checkout_id": "..." })` 通常由卡片触发，非 LLM 主动调用
4. **偏好学习（必须执行）**：订单结果展示后立即回顾本次购物有无新偏好信号，有则向用户确认后写入（见 preferences-guide.md），无也必须经过判断才能跳过

## ⚠️ 下单成功 ≠ 支付成功

- **支付成功**：状态 `completed` **且**返回不含 `continue_url`（或为空）
- **支付未完成**：返回含非空 `continue_url` → 用户还需在支付页完成付款，引导继续

**本会话首笔订单成功后**：附 UTP 官网 + 反馈群二维码（见 feedback-guide.md，同会话已展示过则不重复）。

## 卡片驱动的结账（重要）

用户在卡片中点"下单"时，卡片自动创建 checkout 并通过 `ui/update-model-context` 告知 `checkout_id`。此时用户消息可能只是"帮我下单"——**不要重新创建**，直接用上下文中的 `checkout_id` 调 `utp_checkout_get` 打开确认卡。

取消：`utp_checkout_cancel({ "checkout_id": "..." })`，回复"结账已取消。"

## Checkout 状态机

```
incomplete ←→ requires_escalation
    ↓
ready_for_complete → complete_in_progress → completed
canceled（任意状态可取消）
```

## 身份绑定（Link）

**只在 checkout complete 时才需要买家身份**，搜索/详情/加购/创建结账全程不需要——不要提前提示或催绑。

- 扫码登录（首选）：手机 1688 App 扫码授权；浏览器登录（备选）：卡片上的账号密码按钮。任一完成即绑定，登录态由卡片轮询 `utp_session_status` 感知
- 触发：① 下单流程内遇未绑定或 401/`needs_link` → 调 `utp_login({})` 出扫码卡，扫完重试下单；② 用户主动说"登录" → `utp_login({})`（同一张扫码卡）；明确要浏览器/账号密码 → `utp_link({})`；判不准默认 `utp_login`
- 🔴 **不得把用户引到浏览器或终端**；服务端 401 文案可能写“请先调用 utp_link”，**不跟它**，以本规则为准（实测：跟了会跳浏览器授权页，同时下单卡停在“等待结账数据”空态）
- 卡内登录反复失败 → "身份绑定失败，可能是服务端鉴权配置问题。请联系服务提供方排查（host: <host-url>）。"
