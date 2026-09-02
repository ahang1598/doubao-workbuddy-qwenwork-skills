# get_process_detail

## 工具信息

| 项目 | 内容 |
|------|------|
| MCP Server | `gongyi-open-mcp` |
| 工具名 | `get_process_detail` |
| 接口名 | `GetProcessDetail` |
| 来源 | `proc_manage.proto` |
| oapi 路径 | `/api/proc_manage/GetProcessDetail` |
| x1 | ❌ 不带 `Gy-H-Test-Env-Key: x1` |

## 接口定义

查询项目进展详情，为 AI 生成建议回复提供进展公开信息。

## 请求参数

```json
{
  "id": 652964
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | uint32 | 是 | 进展 ID |

> **注意**：`OrgCommentItem.object_id` 为数字字符串（如 `"652964"`），需转为 `uint32` 后传入。

## 响应参数

```json
{
  "ProcessInfo": {
    "content_title": "项目进展报告",
    "desc": "进展摘要...",
    "content": "进展正文...",
    "concrete_info": "具体信息...",
    "image_url": ["..."],
    "begin_time": "2026-07-01",
    "end_time": "2026-07-31",
    "publish_time": "2026-08-01 10:00:00",
    "status": 1,
    "project_id": "224328",
    "project_name": "春蕾计划她们想上学"
  }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `ProcessInfo` | ProcessInfo | 进展详情 |

## ProcessInfo 关键字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `content_title` | string | 进展标题 |
| `desc` | string | 进展摘要 |
| `content` | string | 进展正文 |
| `concrete_info` | string | 具体信息 |
| `image_url` | string[] | 图片列表 |
| `begin_time` | string | 开始时间 |
| `end_time` | string | 结束时间 |
| `publish_time` | string | 发布时间 |
| `status` | uint32 | 状态（1-已发布） |
| `project_id` | string | 关联项目 ID |
| `project_name` | string | 关联项目名称 |

## 调用示例

```json
// 请求（object_id "652964" 转为 uint32）
{
  "id": 652964
}

// 响应
{
  "ProcessInfo": {
    "content_title": "项目进展报告",
    "desc": "...",
    ...
  }
}
```

## 注意事项

1. `id` 为 `uint32` 类型，`OrgCommentItem.object_id` 为数字字符串，需转换
2. `status = 1` 表示已发布，只有已发布的进展才用于 AI 生成
3. 进展不存在时返回空 ProcessInfo，需降级处理
4. 同一进展（`object_id`）被多条 process 评论引用时，单次 run 内只调用一次，以 `process:<object_id>` 为键去重（仅单次 run 内有效，去重后并发请求；不做跨 run 磁盘缓存，每次 run 实时拉取）
