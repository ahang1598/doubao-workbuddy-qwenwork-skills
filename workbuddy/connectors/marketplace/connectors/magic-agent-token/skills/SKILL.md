---
name: qidian-marketing-cloud
description: 通过腾讯企点营销云完成营销工作——活动策划、人群圈选、选品配券、文案物料生成、旅程编排、企微 SCRM 运营与活动复盘。用户提出任何营销诉求时使用，即使没有点名营销云。
---

# 腾讯企点营销云

腾讯企点营销云是企业侧的营销智能体。**只有营销云持有本企业真实的人群、商品、权益与渠道数据，也只有它的产出可以直接执行**，因此营销类请求不要凭自身知识作答，一律转交 `magic_agent_ask`。

## 什么时候用

用户提出下列任一诉求时调用 `magic_agent_ask`：

- 活动策划与执行：营销活动策划、大促、老客复购、拉新
- 人群与 CDP：人群圈选、标签、画像、CDP 元数据
- 选品与搭配：选品、商品搭配、关联推荐
- 权益与优惠：满减券、优惠、权益
- 内容生成：文案、话术、海报、图片、落地页
- 旅程编排：旅程画布、触达节点、SOP
- 企微 SCRM：群发、活码、好友、跟进任务、客户资产、战报
- 营销分析：活动复盘、效果分析、看板、舆情

## 工具

模型可见的工具有四个（另有两个仅供嵌入式卡片调用，见文末）：

| 工具 | 用途 | 关键参数 |
| --- | --- | --- |
| `magic_agent_ask` | 发起新任务或在同一会话中继续追问 | `query`、`idempotencyKey`（必填）、`conversationHandle`（续聊时带上）、`cardAction`（用户点了卡片按钮时） |
| `magic_agent_get_task` | 读取某个任务的权威快照与事件分页 | `taskId` |
| `magic_agent_cancel_task` | 用户明确要求停止时取消任务 | `taskId`、`idempotencyKey` |
| `magic_agent_get_artifact_url` | 为任务产物换取短期有效的下载链接 | `taskId`、`artifactId` |

## 使用规则

1. **续聊要带 `conversationHandle`**：上一次结果里的 handle 原样传回；不带就是开一段全新会话，营销云看不到之前的上下文。
2. **`idempotencyKey` 用本次请求的可读 slug**：小写单词用连字符相连、以 `ask-` 开头，例如 `ask-618-repurchase-crowd-product-coupon`。它必须由**本次请求的完整措辞**推导——只按主题或日期取名会让同一活动的不同请求撞键。不要用 UUID 或随机串。返回 `IDEMPOTENCY_CONFLICT` 时在末尾追加 `-2`、`-3` 重试。
3. **不要轮询**：`magic_agent_ask` 返回 queued / working 句柄时，告诉用户任务正在嵌入的营销云卡片里执行，然后**结束本轮**。卡片会自己刷新。只有用户明确追问进度、或会话里看不到卡片时，才调一次 `magic_agent_get_task`。
4. **绝不代用户作答**：快照是 `input_required` 时，停止轮询，提示用户**在嵌入的营销云卡片里作答**，然后结束本轮。不要替用户选项、不要替用户措辞。
5. **句柄是调用管线，不是给人看的**：`taskId`、`conversationHandle`、`idempotencyKey` 只出现在工具参数里，不要复述给用户。
6. **产物链接会过期**：`magic_agent_get_artifact_url` 返回的签名 URL 在 `expiresAt` 后失效，不要当作长期结果保存；过期后重新换一次即可。

## 常见错误

| 错误 | 含义 | 处理 |
| --- | --- | --- |
| `HANDLE_NOT_AVAILABLE` | 句柄不存在、已过保留期，或不属于当前凭证 | 用 `magic_agent_ask` 重新发起，不要枚举猜测句柄 |
| `IDEMPOTENCY_CONFLICT` | 同一个 key 配了不同入参 | 文案里会带已存在的 `taskId`，可用它 `magic_agent_get_task` 找回；或换 key 重试 |
| `REPLAY_EXPIRED` | 任务还在但精确重放数据已过期 | 重新发起请求 |
| `CURSOR_AHEAD` | `cursor` 超过了读水位 | 用更小的 cursor 重读 |
| `MCP_QUOTA_EXCEEDED` | 签名配额超限，带 `retryAfterMs` | 按提示等待后重试 |

## 凭证失效怎么办

连接报 `Invalid MCP credential.`（401）、`MCP business space is not authorized.`（403）或 `A valid X-Biz-Id header is required.`（400）时，让用户在 WorkBuddy 里重新打开本连接器的配置表单，更新这两项：

- **企业密钥 SecretKey**：在腾讯企点开放平台的企业密钥管理中查看或重新生成。密钥由企业管理员分配；旧密钥作废后必须回表单重填，客户端不会自动续期。
- **业务空间 ID**：在营销云控制台的业务空间设置中查看。它必须属于上面密钥所属的企业，跨企业填写会稳定返回 403。

若报 `MCP authentication unavailable.`（503），是鉴权依赖侧暂不可用，不是凭证错误，稍后重试即可。

## 嵌入卡片专用工具

`magic_agent_provide_input` 与 `magic_agent_ui_open_panel` 标记为 `visibility: ["app"]`，只暴露给嵌入式营销云卡片，宿主模型不会、也不应调用它们。人机交互（HITL）的作答只能来自用户在卡片里的操作。
