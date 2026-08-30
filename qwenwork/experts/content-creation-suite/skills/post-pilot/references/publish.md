# publish 工具使用说明

## 版本信息
- **当前 mcp-autocli 版本**：1.0.6（从 assets/mcp_autocli-1.0.6-py3-none-any.whl 文件名提取）
- **版本来源**：直接从 assets 目录的 wheel 文件名解析
- **支持的工具版本**：publish 工具（含 click_draft_btn 等新特性）

## publish 参数

| 参数 | 必填 | 类型 | 说明 |
|---|---|---|---|
| `platform` | ✅ | string | 目标平台 |
| `content` | ✅ | string | 正文 |
| `media_type` | — | string | text/image（默认）/video |
| `title` | 小红书/抖音/微信公众号必填 | string | 标题 |
| `images` | media_type=image 时必填 | string[] | 图片绝对路径列表 |
| `video` | media_type=video 时必填 | string | 视频绝对路径 |
| `topics` | — | string[] | 话题标签（不含#），仅小红书/抖音 |
| `draft` | — | bool | **默认 true（安全）**：填表停住让用户手动发 |
| `click_draft_btn` | — | bool | 仅微信公众号：draft 模式下额外点击"保存为草稿"按钮，默认 false |

## 各平台限制

| 平台 | media_type | 图片上限 | 标题 | 正文限制 | 话题 |
|---|---|---|---|---|---|
| xiaohongshu | image / video | 1-9 张 | **必填 ≤20字** | - | ✅ |
| twitter | text / image / video | 1-4 张 | - | ≤280 字符 | - |
| instagram | image / video | 1-10 张（轮播） | - | ≤2200 字符 | - |
| douyin | image / video | 1-35 张 | **必填 ≤30字** | - | ✅ |
| weibo | text / image / video | 1-9 张 | - | ≤2000 字符 | ✅ `#话题#` |
| weixin | text / image | 1 张（封面） | **必填 ≤64字** | ≤20000 字符，支持 HTML | - |

微信公众号 `author` **必填**（先检查用户输入，html_file 模式可尝试从 HTML 提取，获取不到则 ask_human）。

微信公众号还支持 `html_file` 模式（传 HTML 文件路径，自动提取标题/封面/内联 CSS）。

## 返回

- `status: "已填好待确认 (draft 模式)"` — draft 成功
- `status: "发布成功"` / `"posted"` — 发布成功
- `status: "skipped"` + `skip_reason` — 验证失败或 autocli 错误

## draft 行为

- `draft=true`（默认）：自动填好表单后停住，用户在 Edge 窗口里手动点发布/关闭
- `draft=false`：自动填好并点击发布。**需用户明确同意**

## 典型工作流

```
收集需求（平台/内容/类型/素材/标题/话题）
  → 检查 MCP 是否连通
  → publish(platform, content, ..., draft=true)
  → 告知用户 Edge 中已打开发布页，请检查后手动发布
```
