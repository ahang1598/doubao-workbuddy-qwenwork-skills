# QwenWork Tasks Guide

This guide covers QwenWork tasks/chats, historical sessions, and background sub-tasks through the built-in QwenWork Connector.

Use this guide when the user asks to:

- view recent/current QwenWork tasks/chats or sub-tasks
- inspect historical sessions and what happened in them
- check why a task is running for a long time
- stop/cancel a task
- send a follow-up message to a task/chat, including a historical session
- approve/deny a pending task permission request
- answer a task's AskUser question

Prefer these Connector keys over legacy task tools unless the Connector keys are unavailable.

High-priority routing rule:

- For requests like "latest task", "recent tasks", "current task", "what did I/you do", "is it complete", "did everything finish", "why is it stuck", "continue that old task", or "answer the AskUser task", query `qwenwork.tasks` first.
- Then query `qwenwork.tasks.{chatId}` before summarizing status, reporting completion, stopping, sending a message, or responding to AskUser.
- Memory/awareness is not authoritative task state. Use it only after task queries for supplemental background, or when QwenWork Connector task keys are unavailable.

---

## Concepts

| Concept | Meaning |
|---------|---------|
| QwenWork task / chat | A top-level QwenWork conversation shown as a task in the sidebar. It has a stable `chatId`. |
| Source chat | The QwenWork chat that created another background task. Use it only as an optional filter. |
| Sub-task | A background task created from a source chat. It also has its own `chatId`. |
| Task detail | Recent message history, status, tool calls, and pending request summary for one task. |
| Pending AskUser | The task is waiting for user input from an `AskUserQuestion` tool call. |
| Pending permission | The task is waiting for approval/denial for a tool or operation. |

Important scope rule:

- `qwenwork.tasks` lists QwenWork tasks/chats across history by default.
- Pass `params.sourceChatId` only when the user specifically asks for sub-tasks created by a source chat.
- If the default all-task query returns an empty list, QwenWork has no non-deleted task records available.
- It is not the same as querying scheduled tasks; scheduled tasks use `qwenwork.cron`.
- Do not use memory/awareness as a fallback for task status. Use task queries for task state.

---

## Keys

| Key | Actions | Description |
|-----|---------|-------------|
| `qwenwork.tasks` | query | List QwenWork tasks/chats. Default scope is all non-deleted tasks. |
| `qwenwork.tasks.{chatId}` | query, execute | Inspect and operate one task/chat. |

---

## List Tasks

Start here when the user asks about QwenWork tasks, recent/latest/current tasks, historical tasks, sub-tasks, task status, what was done, whether work is complete, or why a task is stuck.

```
mcp__qw-builtin__qw_query({ key: "qwenwork.tasks" })
```

Optional explicit source chat:

```
mcp__qw-builtin__qw_query({
  key: "qwenwork.tasks",
  params: { sourceChatId: "source-chat-id" }
})
```

Response shape:

```json
{
  "success": true,
  "data": {
    "scope": "all",
    "total": 1,
    "limit": 50,
    "offset": 0,
    "summary": {
      "total": 1,
      "running": 1,
      "completed": 0,
      "cancelled": 0,
      "failed": 0,
      "interrupted": 0
    },
    "tasks": [
      {
        "key": "qwenwork.tasks.task-chat-id",
        "chatId": "task-chat-id",
        "title": "Task title",
        "status": "running",
        "messageCount": 3,
        "chatType": "task",
        "sourceChatId": null,
        "archived": false,
        "supportedActions": ["query", "execute"],
        "executeOperations": ["stop", "send_message", "respond"]
      }
    ]
  }
}
```

If the list is empty, explain that no QwenWork task records are available for the selected scope. Do not switch to memory search for task status.

---

## Query Task Detail

Always query detail before stopping, messaging, continuing, or responding to a task unless the user has already supplied the exact `chatId` and intended operation.

```
mcp__qw-builtin__qw_query({
  key: "qwenwork.tasks.<chatId>",
  params: { limit: 5 }
})
```

Response includes:

- task status
- total message count
- recent messages
- tool calls
- `pendingRequest` when the task is waiting for AskUser or permission handling
- available `executeOperations`

Use `pendingRequest.type` to choose the response:

| pendingRequest.type | Action |
|---------------------|--------|
| `ask_user_question` | Ask the user for an answer, then call `respond` with `response: "answer"`. |
| `permission` | Ask or infer whether to approve/deny, then call `respond` with `response: "approve"` or `"deny"`. |
| `null` | No pending request. Do not call `respond`. |

---

## Stop a Task

Use when the user asks to stop, cancel, abort, interrupt, or end a running task.

```
mcp__qw-builtin__qw_action({
  key: "qwenwork.tasks.<chatId>",
  action: "execute",
  params: { operation: "stop" }
})
```

If the task is already completed or not running, the result may return an error. Report that error directly.

---

## Send a Message to a Task

Use when the user wants to continue a task/chat, provide more context, or answer in free text outside of a pending AskUser prompt. This works for historical sessions as long as the task has a valid `chatId`.

```
mcp__qw-builtin__qw_action({
  key: "qwenwork.tasks.<chatId>",
  action: "execute",
  params: {
    operation: "send_message",
    message: "Continue with the latest requirement."
  }
})
```

Do not use `send_message` to answer a pending AskUser prompt when `pendingRequest.type` is `ask_user_question`; use `respond` with `response: "answer"` instead.

---

## Respond to AskUser

Use only after `query` shows a pending AskUser request.

The most compatible answer format is:

```
mcp__qw-builtin__qw_action({
  key: "qwenwork.tasks.<chatId>",
  action: "execute",
  params: {
    operation: "respond",
    response: "answer",
    answers: {
      "Question header": "Selected option label"
    }
  }
})
```

The task manager also accepts the structured option format:

```
mcp__qw-builtin__qw_action({
  key: "qwenwork.tasks.<chatId>",
  action: "execute",
  params: {
    operation: "respond",
    response: "answer",
    answers: {
      "questions": [
        { "selectedOptions": ["Option label"] }
      ]
    }
  }
})
```

For multi-select questions, join selected labels with `, ` when using the header map format.

---

## Approve or Deny a Permission Request

Use only after `query` shows a pending permission request.

Approve:

```
mcp__qw-builtin__qw_action({
  key: "qwenwork.tasks.<chatId>",
  action: "execute",
  params: {
    operation: "respond",
    response: "approve"
  }
})
```

Deny:

```
mcp__qw-builtin__qw_action({
  key: "qwenwork.tasks.<chatId>",
  action: "execute",
  params: {
    operation: "respond",
    response: "deny",
    message: "User denied this operation."
  }
})
```

---

## Troubleshooting

### User asks "why is the latest task stuck?"

1. Query `qwenwork.tasks`.
2. If tasks exist, inspect the newest/running task with `qwenwork.tasks.{chatId}`.
3. If `pendingRequest` is present, explain what the task is waiting for and ask the user whether to respond.
4. If no tasks are listed, explain that no QwenWork task records are available for the selected scope.

### User asks "what did I do in the latest task?" or "is everything done?"

1. Query `qwenwork.tasks` with a reasonable page size such as `{ limit: 10 }`.
2. Pick the newest task from the returned list unless the user names a specific task.
3. Query `qwenwork.tasks.{chatId}` with `{ limit: 10 }`.
4. Summarize the recent messages, status, tool calls, and pending request. If `status` is `running`, say it is not complete. If `pendingRequest` exists, say it is waiting for user action.
5. Do not use memory search as the primary source for task status.

### User asks to continue a historical task

1. Query `qwenwork.tasks` to find the target historical task.
2. Query `qwenwork.tasks.{chatId}` to confirm context and status.
3. Call `execute` with `operation: "send_message"` and the user's message.
4. Report whether the message was sent or queued.

### User asks "stop the latest task"

1. Query `qwenwork.tasks`.
2. Pick the newest running task.
3. Call `execute` with `operation: "stop"`.
4. Report the result.

### User asks "answer the task"

1. Query `qwenwork.tasks`.
2. Query the target task detail.
3. If the task has a pending AskUser request, call `respond` with `response: "answer"`.
4. If the task has no pending request, use `send_message` only if the user's intent is a follow-up message.
