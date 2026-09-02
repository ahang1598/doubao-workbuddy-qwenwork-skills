# get_org_upreplied_comments

## 工具信息

| 项目 | 内容 |
|------|------|
| MCP Server | `gongyi-open-mcp` |
| 工具名 | `get_org_upreplied_comments` |
| 接口名 | `ListOrgUnrepliedCommentsForOrgPlatform` |
| 来源 | `comment_svc.proto`（`org_platform3/comment_svc/stub/comment_svc.proto`） |
| oapi 路径 | `/api/comment_svc/ListOrgUnrepliedCommentsForOrgPlatform` |
| x1 | ✅ 需带 `Gy-H-Test-Env-Key: x1`（comment_svc 接口） |

## 接口定义

查询机构未回复且已审核通过的评论（高风险优先）。

## 请求参数（ListOrgUnrepliedCommentsForOrgPlatformReq）

```json
{
  "page": 0,
  "size": 20,
  "filter_start_time": 0,
  "filter_end_time": 0,
  "filter_project_id": "",
  "mock_org_no": "",
  "start_time": 0
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `page` | uint32 | 是 | 页码，0 开始 |
| `size` | uint32 | 是 | 每页大小，默认 20，最大 100 |
| `filter_start_time` | uint32 | 否 | 筛选开始时间（Unix 时间戳），0 表示不筛选 |
| `filter_end_time` | uint32 | 否 | 筛选结束时间（Unix 时间戳），0 表示不筛选 |
| `filter_project_id` | string | 否 | 项目 ID 筛选，空表示全部项目 |
| `mock_org_no` | string | 否 | 模拟机构 ID（仅七彩石 `enable_org_mock=true` 时生效） |
| `start_time` | int64 | 否 | 查询起始时间（Unix 秒），**不传默认 30 天前**。产品要求只查询 30 天及之内的数据，调用方应显式传「当前时间 - 30 天」 |

## 响应参数（ListOrgUnrepliedCommentsForOrgPlatformRsp）

```json
{
  "total": 36,
  "risk_total": 2,
  "list": [
    {
      "comment_id": 123456789,
      "subject_id": "subj_001",
      "content": "钱都去哪了？...",
      "project_id": "224328",
      "project_name": "春蕾计划她们想上学",
      "status": 1,
      "created_at": 1756000000,
      "nick_name": "爱心网友A",
      "head_img": "https://.../avatar.png",
      "gy_uid": "u_xxx",
      "like_num": 3,
      "comment_type": 0,
      "object_type": "project",
      "object_id": "224328",
      "can_reply": true,
      "is_recommended": false,
      "reply_list": [],
      "audit_type": 2,
      "risk_audit_status": 4,
      "risk_audit_reason": "质疑资金去向",
      "risk_audit_at": 1756000050
    }
  ],
  "code": 0,
  "msg": ""
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `total` | uint32 | 总数量（满足筛选条件的主评论数） |
| `risk_total` | uint32 | 风控拦截评论总数（risk_audit_status=4 且 status=1），即高风险留言数 |
| `list` | OrgCommentItem[] | 评论列表（复用 `OrgCommentItem` 结构） |
| `code` | uint32 | 返回码，0 表示成功 |
| `msg` | string | 错误信息 |

## OrgCommentItem 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `comment_id` | uint64 | 评论 ID |
| `subject_id` | string | 主题 ID（分片键，批量回复时必传） |
| `content` | string | 评论内容 |
| `project_id` | string | 项目 ID |
| `project_name` | string | 项目名称 |
| `status` | uint32 | 审核状态：0-待审核，1-审核通过，2-审核拒绝（本接口只返回审核通过的） |
| `created_at` | uint32 | 创建时间（时间戳） |
| `opt_user` | string | 机构用户名称（审核人员） |
| `comment_type` | uint32 | 评论类型：0-用户留言，2-机构回复，3-管理员回复（本接口只返回 0） |
| `parent_comment_content` | string | 被回复的用户评论内容（兼容字段，完整信息见 `parent_comment`） |
| `is_sticky` | bool | 是否置顶 |
| `sticky_expire` | uint32 | 置顶过期时间（时间戳） |
| `can_reply` | bool | 是否可回复该评论 |
| `can_sticky` | bool | 是否可置顶该评论 |
| `can_cancel_sticky` | bool | 是否可取消置顶 |
| `can_delete` | bool | 是否可删除（仅机构回复有效） |
| `is_recommended` | bool | 是否 AI 推荐回复 |
| `gy_uid` | string | 评论作者用户 ID |
| `nick_name` | string | 评论作者昵称 |
| `head_img` | string | 评论作者头像 URL |
| `like_num` | uint32 | 点赞数 |
| `org_comment_id` | uint64 | 机构评论中间表 ID |
| `org_reply_content` | string | 机构回复内容（如果有，仅第一条，兼容字段） |
| `org_reply_time` | uint32 | 机构回复时间（如果有，仅第一条，兼容字段） |
| `reply_list` | OrgCommentReplyItem[] | 评论下的回复列表（完整列表） |
| `parent_comment` | OrgCommentReplyItem | 被回复的父评论信息（机构回复时返回） |
| `audit_reject_reason` | string | 审核拒绝原因（当 status=2 时有值） |
| `audit_type` | uint32 | 审核类型：0-未审核，1-UGC审核，2-AI审核 |
| `risk_audit_status` | uint32 | 风控审核状态：0-审核中，1-UGC拦截，2-粗筛未命中，3-AI放行，4-AI拦截 |
| `risk_audit_reason` | string | 风控拦截原因（当 risk_audit_status=4 时有值） |
| `risk_audit_at` | uint32 | 风控状态最近更新时间（时间戳） |
| `object_type` | string | 评论对象类型（来自 Subject 表）：`project` / `process` / `yqj_feeds` |
| `object_id` | string | 评论对象 ID（project 类型时为项目 ID，process 类型时为进展 ID） |

## OrgCommentReplyItem 字段说明（reply_list / parent_comment 元素）

| 字段 | 类型 | 说明 |
|------|------|------|
| `comment_id` | uint64 | 回复评论 ID |
| `content` | string | 回复内容 |
| `created_at` | uint32 | 回复时间（时间戳） |
| `reply_type` | uint32 | 回复类型：0-用户回复，2-机构回复，3-管理员回复 |
| `replier_uid` | string | 回复者 ID（用户 gy_uid 或机构 ID） |
| `replier_name` | string | 回复者名称 |
| `replier_avatar` | string | 回复者头像 |
| `status` | uint32 | 回复状态：0-待审核，1-审核通过，2-审核拒绝 |
| `parent_comment_id` | uint64 | 被回复的评论 ID |
| `audit_reject_reason` | string | 审核拒绝原因（当 status=2 时有值） |
| `audit_type` | uint32 | 审核类型：0-未审核，1-UGC审核，2-AI审核 |
| `can_delete` | bool | 是否可删除（仅机构回复有效） |

## 调用示例

```json
// 请求
{
  "page": 0,
  "size": 20
}

// 响应
{
  "total": 36,
  "risk_total": 2,
  "list": [...],
  "code": 0,
  "msg": ""
}
```

## 注意事项

1. `subject_id` 是分片键，批量回复时必须传递
2. `object_type` 用于区分项目评论（`project`）和进展评论（`process`）
3. `risk_audit_status = 4` 表示 AI 拦截，即高风险留言；`risk_total` 统计口径为 risk_audit_status=4 且 status=1
4. `comment_type = 0` 表示用户留言（机构未回复）
5. `object_id` 为数字字符串，process 类型时可转为 uint32 作为进展 ID
6. 测试环境调用需在 HTTP header 携带 `Gy-H-Test-Env-Key: x1`（已在 MCP Server 配置中注入）
