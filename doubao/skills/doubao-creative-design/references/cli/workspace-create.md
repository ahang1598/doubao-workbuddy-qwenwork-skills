# `design-cli design-workspace +workspace-create`

建一张新画布。调用 Alice IDL 的 `CreateCanvasWorkspaceForCLI`。

## 用途

产出一个 `canvas_workspace_id`，七个 Item／Frame 读写命令都要拿它当 `--canvas-workspace-id`。当前对话没有 Workspace ID 时，第一轮创作先调用本命令；已有唯一有效 ID 时直接复用，不重复创建。

它与 `+get-workspace` 都不带 `--canvas-workspace-id`。本命令创建 Workspace，`+create` 创建 Item／Frame，两者不要混用。

它是唯一不带 `--canvas-workspace-id` 的命令。名字不叫 `+create` 是因为那个已经是「建节点」（Item / Frame）——两者不要混。

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

读取响应中的 `canvas_workspace_id` 后，由主 Agent 立即调用一次独立的 `present_files(<canvas_workspace_id>)`：唯一输入必须是响应中的原始 Workspace ID，由该调用交付新建画布卡片。不得创建 `workspace-id.txt` 或其他中间文件，也不得加入字段名、标题、版本、XML、JSON、说明或任何包装。画布卡片交付成功前不得调用媒体生成／编辑工具，也不得执行 Item／Frame 写命令。

`version` 是画布的全局版本号，新建时为 `1`。

## 注意

- **没有幂等**：同样的 `--title` 调两次会建出两张画布。调用超时时不要盲目重试，先确认上一次是否已经建成。
- 会话由环境变量决定，命令行改不了。

退出码与错误处理见 [`README.md`](README.md)。
