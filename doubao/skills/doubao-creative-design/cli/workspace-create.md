# `design-cli design-workspace +workspace-create`

建一张新画布。调用 Alice IDL 的 `CreateCanvasWorkspaceForCLI`。

## 用途

仅用于 `image-coding`、`pure-coding` 的 PC Web 画布流程；`pure-image` 与 Mobile 不调用。路线、环境和最终交付统一按 [主入口](../SKILL.md#交付环境与画布)及 [Canvas 交付协议](../references/canvas-delivery.md)执行。

返回 `canvas_workspace_id`，供七个 Item／Frame 读写命令的 `--canvas-workspace-id` 使用。适用流程中没有当前任务的 Workspace ID 时，制作前调用；已有唯一有效 ID 时直接复用，不重复创建。

它与 `+get-workspace` 都不带 `--canvas-workspace-id`。本命令创建 Workspace，`+create` 创建 Item／Frame，两者不要混用。

## 命令

```bash
design-cli design-workspace +workspace-create --title <title>
```

## 参数与请求

| CLI 参数 | 必填 | JSON 字段 |
|---|---:|---|
| `--title` | 是 | `title`；空值或纯空白按缺失处理，退出码 `2`、不发请求 |

`conversation_id` 也进请求体，但**不是 CLI 参数** —— 它由 CLI 从环境变量读取（沙箱注入）：优先 `MCP_VM_CONVERSATION_ID`，未设或纯空白时回退 `SESSION_ID`，两者都没有才整格省略。不要试图用命令行指定会话。

```text
POST /creativity/canvas_workspace/cli/create_workspace
Content-Type: application/json
```

```json
{"title":"雨夜便利店短剧","conversation_id":"7788"}
```

## 输出

`xml_data` 内为 `<canvas_workspace>`：

```xml
<canvas_workspace>
  <canvas_workspace_id>cws_10001</canvas_workspace_id>
  <version>1</version>
</canvas_workspace>
```

只回 ID 与版本，不回画布内容——新画布本来就是空的。**记下 `canvas_workspace_id`**，后续所有命令都要用它。

## Workspace 画布卡片交付门禁

读取响应中的 `canvas_workspace_id` 后，由主 Agent 立即调用一次独立的 `present_files(<canvas_workspace_id>)`：唯一输入必须是响应中的原始 Workspace ID，由该调用交付新建画布卡片；这不代表成品已交付，最终 HTML 须逐项回读并展示 Item 卡片。不得创建 `workspace-id.txt` 或其他中间文件，也不得加入字段名、标题、版本、XML、JSON、说明或任何包装。画布卡片交付成功前不开始依赖该 Workspace 的制作或写入；已授权的独立 `pure-image` 产物不受此门禁阻塞。

`version` 是画布的全局版本号，新建时为 `1`。

## 注意

- **没有幂等**：同样的 `--title` 调两次会建出两张画布。调用超时且未取得 ID 时，仅通过已验证的当前会话查询能力（如 [+get-workspace](get-workspace.md)）找回；无法确认就停止重建并报告，不按通用重试次数再次创建。
- 会话由环境变量决定，命令行改不了。

退出码与错误处理见 [`README.md`](README.md)。
