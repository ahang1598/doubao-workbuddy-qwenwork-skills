# `design-cli design-workspace +get-workspace`

查当前会话上挂的画布。复用 Alice IDL 的 `GetCanvasWorkspace`（按会话查）。

## 用途

回答一个问题：**这个会话上有没有画布**。

- **有** → 返回 `canvas_workspace_id` 与 `version`，用于显式恢复或核对目标 Workspace
- **没有** → 返回 `exists=false`

本命令用于显式查询、恢复和排障。

## 命令

```bash
design-cli design-workspace +get-workspace
```

零参数。会话 ID 由 CLI 从环境变量读取（沙箱注入）：优先 `MCP_VM_CONVERSATION_ID`，未设或纯空白时回退 `SESSION_ID`。不能用命令行指定。

## 请求

```text
POST /creativity/canvas_workspace/cli/get_workspace
Content-Type: application/json
```

```json
{"conversation_id":"7788"}
```

## 输出

**会话上有画布：**

```json
{"code":0,"msg":"ok","xml_data":"<canvas_workspace><exists>true</exists><canvas_workspace_id>cws_10001</canvas_workspace_id><version>1</version></canvas_workspace>"}
```

**会话上还没有画布：**

```json
{"code":0,"msg":"ok","xml_data":"<canvas_workspace><exists>false</exists></canvas_workspace>"}
```

⚠️ **「没有画布」是正常答案，不是错误** —— `code` 仍是 `0`，退出码仍是 `0`。**按 `<exists>` 分支，不要按退出码判断有没有画布**。查不到时不返回 `canvas_workspace_id` 与 `version` 两格，不要把空串当成画布 ID 往下调。

真正的错误（参数错、内部错）照旧 `code != 0` + 退出码 `1`。

## 典型动线

```bash
design-cli design-workspace +get-workspace
# exists=false → 建一张
design-cli design-workspace +workspace-create --title "雨夜便利店短剧"
# 记下返回的 canvas_workspace_id，后续命令都用它
design-cli design-workspace +ls --canvas-workspace-id cws_10001
```

退出码与错误处理见 [`README.md`](README.md)。
