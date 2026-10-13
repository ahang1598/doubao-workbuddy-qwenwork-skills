# 千问办公 Task 拉取参考（task-pull）

> 本文件只讲「从千问办公拿任务数据」。AI 表格字段写入值格式与高频错误见 `aitable-write.md`，人员/附件见 `people-attachment.md`。

千问办公的 task 数据**不走 bash/dws**，走内置 QwenWork Connector 工具（`mcp__qw-builtin__qw_query`）。不要尝试用 bash 或 qodercli 去拉，qodercli 本环境 Not logged in，且无干净 list-tasks 命令。

## 1. 拉任务列表（默认近一天，不拉全部）

用 `mcp__qw-builtin__qw_query` 查 `qwenwork.tasks`。分页/过滤参数以 `qwenwork_mcp_tool_get` 返回的 schema 为准，不要凭空记。日常同步固定：拉最近一页（`limit` 10~50），按 `updatedAt >= 昨天` 本地过滤，只对近一天任务做 diff/写入；**首次建台账做基线时才允许翻页拿全量**，不要每次同步都拉全量。过滤 IM 噪音、同步任务自身等规则见 SKILL.md「定时同步流程」。

返回结构（关键字段）：

```jsonc
{
  "data": {
    "scope": "all",
    "total": 10,
    "summary": {"total": 10, "running": 2, "completed": 3, "cancelled": 0, "failed": 0, "interrupted": 0},
    "tasks": [
      {
        "chatId": "msshkewyb1sidvp5",          // 写入台账「任务ID」，Agent类型=qwenwork
        "title": "任务标题",
        "createdAt": "2026-08-14T05:07:54.000Z",
        "updatedAt": "2026-08-14T08:41:22.000Z",
        "status": "running",                   // running/completed/cancelled/failed/interrupted
        "messageCount": 35,
        "chatType": "task",                    // task | im
        "sourceChatId": null,                  // 父任务 chatId，子任务/监听器才有
        "projectPath": "...",
        "worktreePath": "...",                 // 产出文件通常在此目录下 outputs/
        "archived": false
      }
    ]
  }
}
```

`summary` 已经是各状态计数，可直接用于校验同步后是否一致。

## 2. 拉单条任务详情（交接/提炼摘要用）

用 `mcp__qw-builtin__qw_query` 查 `qwenwork.tasks.<chatId>`，拿该任务的完整消息历史与 tool 调用细节，用于生成交接摘要、提炼一句话摘要、任务类型、优先级。

交接流程固定顺序：意图关键词 → 台账搜到 chatId → `qwenwork.tasks.<chatId>` 拉原始对话 → 生成六块交接摘要。

## 3. 状态映射（写入台账「状态」字段前必转）

| qwenwork status | 台账「状态」singleSelect 写入值 |
|---|---|
| running | 进行中 |
| pendingRequest（等待确认） | 等待确认 |
| completed | 已完成 |
| cancelled | 已取消 |
| failed | 失败 |
| interrupted | 中断 |

手动暂停写「暂停」。注意 `pendingRequest` 不在 summary 的五个计数里，需要从任务详情里看是否存在 pendingRequest 字段。

## 4. 幂等去重（硬规则）

千问办公取数逻辑保持不变：仍以 `chatId` 作为 qwenwork 任务唯一 ID。写入台账时 `chatId` →「任务ID」，「Agent类型」固定写 `qwenwork`。同步前先读台账里已有的「任务ID + Agent类型 + 创建人」集合，diff 后：新组合 → `record create`，已存在 → `record update`。跑多少次都不产生重复行。
