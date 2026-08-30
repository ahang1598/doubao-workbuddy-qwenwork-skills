---
name: fbs-connector-session
description: "福帮手访问码激活、权益预检、流程完结与退出会话。仅处理用户明确提出或主线明确要求的高级后续，不作为首轮业务入口。"
version: "26.8.20"
author: "FBSir"
---

# 福帮手会话后续

执行本技能时同时遵守 `fbs-connector` 的公共安全与输出规则。

## 路由

- `skill_activate`：用户明确提供访问码，或主线返回明确要求激活；必填 `accessCode`、`skillCode`。
- `skill_precheck`：身份或会话已经明确，用户要求校验指定权益或积分；必填 `skillCode`。
- `skill_finish`：业务流程已经真实完成且有使用记录；必填 `usageId`、`status`。
- `skill_logout`：用户明确要求退出或重置会话。

## 边界

- 不向用户索要未被当前步骤需要的凭证；访问码、会话令牌只在授权链路内部原样传递。
- 激活、预检与完结都不替代聊天首值，也不自动触发奖励。
- `skill_finish` 不用于首轮入口或首值记录；主线进度由 `skill_consume` 负责。
- 不因网络错误、重试或内部诊断擅自登出。
- 成功必须由对应工具回执证明；没有回执就只报告未确认状态。
