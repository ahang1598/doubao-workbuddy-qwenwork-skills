# Base 资源解析命令

本页维护 Base 资源解析命令的输入、返回 ID 与参数错误约定；输入选路、候选消歧与后续任务见 [Base 定位流程](../scenes/base.md#定位已有-base)。

## 输入与命令

`--base-token` 接受真实 Base Token，不能填完整 URL、wiki token、workspace token 或孤立 raw token。`+url-resolve` 接受 URL，不接受孤立 raw token。

| 命令 | 输入与返回约定 |
| --- | --- |
| `lark-cli base +url-resolve --url "<url>" --as user` | 解析 URL 或分享链接，返回 `base_token` 及链接包含的相关对象 ID |
| `lark-cli base +title-resolve --title "<keyword>" --as user` | 按标题关键词定位；`--title` 不超过 30 个字符 |
| `lark-cli drive +search --doc-types bitable --as user` | 搜索用户可访问的 Base；支持最近访问、owner、创建人、时间或类型的筛选与排序 |

最近访问的调用示例；`--mine` 仅列我拥有的，`--created-by-me` 仅列我创建的：

```bash
lark-cli drive +search --doc-types bitable --sort open_time --opened-since 3m --page-size 20 --as user
```

## 文档嵌入标签

`<bitable>` / `<base_refer>` 中的属性直接映射为 Base 命令参数：

| 标签属性 | 命令参数 |
| --- | --- |
| `token` | `--base-token` |
| `table-id` | `--table-id` |
| `view-id` | `--view-id` |

## 返回 ID 与错误

- 后续命令逐字使用本次可信返回的 `base_token` 及任务所需 `table_id` / `view_id` / `record_id` / `form_id` / `dashboard_id` / `workflow_id` 等真实 ID，不手抄、缩写、从上下文记忆改写或混用旧轮次坐标。
- **`NOTEXIST` / `param baseToken is invalid` / `base_token invalid`**：先逐字比对本次参数与最近一次可信 `+url-resolve` 返回，检查是否误用了完整 URL、wiki token 或 workspace token，再判断权限、资源删除或平台异常。输入来自 Wiki 链接且报 not found 时，优先检查 wiki token 与 Base Token 是否混用，不立即改走裸 API。
