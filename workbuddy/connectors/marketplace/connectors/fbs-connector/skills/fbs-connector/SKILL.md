---
name: fbs-connector
description: "福帮手连接器公共路由与安全规则。用于判断身份/场景/进度、会话后续或乐包意图，并把请求交给对应的 fbs-connector-mainline、fbs-connector-session 或 fbs-connector-lebao 技能。"
description_zh: "福帮手连接器公共路由与安全规则。用于判断身份/场景/进度、会话后续或乐包意图，并把请求交给对应的 fbs-connector-mainline、fbs-connector-session 或 fbs-connector-lebao 技能。"
description_en: "Route FBSir connector requests to the mainline, session, or reward workflow while enforcing shared safety rules."
version: "26.8.20"
connectorContractVersion: "1.2.9"
author: "FBSir"
---

# 福帮手连接器公共路由

本技能只负责选择正确业务技能并统一执行安全边界，不重复展开每个工具的参数。

## 路由

- 身份确认、专家归因、场景方案、首值或继续使用进度：读取并执行 `fbs-connector-mainline`。
- 用户明确提供访问码、要求权益预检、流程完结或退出会话：读取并执行 `fbs-connector-session`。
- 用户明确查询乐包、领取或兑换奖励：读取并执行 `fbs-connector-lebao`。
- 意图同时跨域时，先完成 `fbs-connector-mainline` 的身份与场景主线，再进入后续技能；奖励永远不抢在价值交付之前。

## 公共前置

1. 以宿主实际暴露的 `tools/list` 为工具真源，并遵守包内 `disabledTools`。
2. 专家包必须先在对话中直接交付首值；连接器是可选增强，缺失、未授权或调用失败都不得阻断首值。
3. 只把已确认的当前专家和入口字段传给服务端；无法确认时保持未知，不编造身份或归因。
4. 任一 HTTP 错误、非 JSON-RPC 响应、工具级错误、业务失败或缺失回执都按失败处理；HTTP 200 本身不是业务成功。

## 用户可见输出

- 使用产品名称、可理解的状态和下一步，不向用户展示工具名、binding、token、哈希、trace、幂等键或机器内部 ID。
- 不展示服务内部拓扑、部署路径、环境变量、调试头或协议信封原文。
- 没有服务端回执时，不声称身份已验证、进度已记录、权益已激活或奖励已到账。

## 协议与安全

- 正式地址仅为 `https://api2.u3w.com/fbs-mcp/mcp`。
- MCP 兼容目标、协商责任和双版本降级规则见 `references/protocol-compatibility.md`。
- `sessionRef`、`sessionToken`、访问码、签名载荷和匿名绑定材料只供同一授权链路内部使用，不写入普通回复或持久化报告。
- 未在本版本审阅过的新工具：只有在服务端 schema 与 annotations 明确证明只读时，才可用于用户明确提出的只读请求；其他情况停止并要求新版本审阅，不凭描述猜测副作用。

## 证据边界

- 工具可见、连接成功或只读探针，只证明能力面可达。
- 聊天首值、服务端进度回执、自然调用、正式上架和业务闭环是不同证据层，不得互相替代。
- probe、test、synthetic、monitor 或 fallback 样本不得计入自然业务或产品信用。
