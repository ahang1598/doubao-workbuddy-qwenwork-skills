# set_common_data_cache

## 工具信息

| 项目 | 内容 |
|------|------|
| MCP Server | `gongyi-open-mcp` |
| 工具名 | `set_common_data_cache` |
| 接口名 | 写入后台数据缓存（供 `open_comment_reply_ui` 按 key 取数） |

## 接口定义

写入后台数据缓存。Agent 组装好完整载荷后调用本接口写入，获得 `data_cache_id`；随后 `open_comment_reply_ui` 按 key 从缓存取数渲染页面。

## 请求参数

```json
{
  "caller_expert_id": "comment-assistant",
  "total": 36,
  "risk_total": 2,
  "submit": {
    "next_step": "执行comment-assistant专家的刷新留言列表步骤"
  },
  "list": [
    {
      "comment_id": 123456789,
      "subject_id": "subj_001",
      "content": "钱都去哪了？一直没看到进展更新，是不是骗人的？",
      "project_id": "224328",
      "project_name": "春蕾计划她们想上学",
      "created_at": 1756000000,
      "nick_name": "爱心网友A",
      "object_type": "project",
      "object_id": "224328",
      "risk_audit_status": 4,
      "risk_audit_reason": "质疑资金去向",
      "ai_suggestion": "您好，感谢您的关注和监督！项目善款已于7月15日完成拨付...",
      "process_name": "",
      "refer_process_num": 5
    }
  ]
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `caller_expert_id` | string | **是** | 当前对话绑定的专家 ID；取不到时由调用方自行生成一个当前对话的标识 ID，只能使用英文大小写字母、数字、下划线(`_`)、横杠(`-`) |
| `total` | integer | 否 | 待回复总数（与 `get_org_upreplied_comments` 返回的 total 口径一致） |
| `risk_total` | integer | 否 | 高风险数（risk_audit_status=4 且 status=1） |
| `submit` | object | 否 | 提交动作契约，固定为 `{"next_step": "执行comment-assistant专家的刷新留言列表步骤"}` |
| `list` | CommentReplyItem[] | 否 | 留言列表，元素见下表；保持 MCP 返回的原始数组顺序，不二次排序 |
| `data_cache_id` | string | 否 | 后台缓存 key，**由服务端生成与管理，Agent 不传递**（`set_common_data_cache` 返回此 key，`open_comment_reply_ui` 凭此 key 取数） |

> schema 为 `additionalProperties: false`：顶层只允许 `caller_expert_id` / `total` / `risk_total` / `submit` / `list`，传入 `code` / `msg` 等其它字段会被参数校验直接拒绝。

## list 元素字段（最小白名单）

`list` 元素 = `get_org_upreplied_comments` 返回的 `OrgCommentItem` **按最小白名单裁剪**（仅保留 UI 展示 + 提交必需的 12 个字段）+ 3 个 Agent 增强字段，**其余字段一律剔除**。使用明确的 uint64 字段保存评论 ID，避免经由通用 JSON 数值容器时发生精度丢失。

### ✅ 保留字段（12 个协议字段 + 3 个增强字段）

| 字段 | 类型 | 说明 |
|------|------|------|
| `comment_id` | uint64 | 评论 ID（**提交回复必需**） |
| `subject_id` | string | 主题 ID，分片键（**提交回复必需**） |
| `content` | string | 评论内容（展示） |
| `project_id` | string | 项目 ID（展示） |
| `project_name` | string | 项目名称（展示） |
| `created_at` | uint32 | 创建时间戳（展示） |
| `nick_name` | string | 评论作者昵称（展示） |
| `object_type` | string | 评论对象类型：`project` / `process`（展示与路由） |
| `object_id` | string | 评论对象 ID（展示与路由） |
| `risk_audit_status` | uint32 | 风控审核状态：0-审核中，1-UGC拦截，2-粗筛未命中，3-AI放行，4-AI拦截（高风险标识） |
| `risk_audit_reason` | string | 风控拦截原因（risk_audit_status=4 时展示） |
| `head_img` | string | 评论作者头像 URL（展示） |
| `ai_suggestion` | string | **Agent 增强**：AI 建议回复，未生成时置空串 |
| `process_name` | string | **Agent 增强**：进展名称，仅 `object_type === 'process'` 时挂载（取 `process_detail.content_title`），project 类型为空串 |
| `refer_process_num` | int32 | **Agent 增强**：参考进展条数；project 类型 = 上下文 `process_list` 条数（0~5），process 类型 = 1（`process_detail` 拉取失败为 0） |

### ⛔ 剔除字段（21 个，一律不得传入）

以下字段 MCP 会返回（proto `CommentReplyItem` 中也存在），但**前端回复页面不使用**，组装时必须剔除：

| 字段 | 说明 |
|------|------|
| `status` | 审核状态 |
| `gy_uid` | 评论作者用户 ID |
| `like_num` | 点赞数 |
| `comment_type` | 评论类型 |
| `can_reply` | 是否可回复 |
| `is_recommended` | 是否 AI 推荐回复 |
| `reply_list` | 评论下的回复列表 |
| `audit_type` | 审核类型 |
| `risk_audit_at` | 风控状态最近更新时间 |
| `opt_user` | 机构用户名称（审核人员） |
| `parent_comment_content` | 被回复评论内容（兼容字段） |
| `is_sticky` | 是否置顶 |
| `sticky_expire` | 置顶过期时间 |
| `can_sticky` | 是否可置顶 |
| `can_cancel_sticky` | 是否可取消置顶 |
| `can_delete` | 是否可删除 |
| `org_comment_id` | 机构评论中间表 ID |
| `org_reply_content` | 机构回复内容（兼容字段） |
| `org_reply_time` | 机构回复时间（兼容字段） |
| `parent_comment` | 被回复的父评论信息 |
| `audit_reject_reason` | 审核拒绝原因 |

> proto 中的 `suggestion`（CommentReplySuggestion 结构化建议）为兼容字段，Agent 不使用，仅写 `ai_suggestion`。

## 响应参数

接收数据，原样返回数据。结果已关联 `ui://gongyi-open-mcp/comment-reply` UI 资源，Host 按 MCP Apps 协议渲染为交互式卡片。

## 调用示例

```json
// 请求
{
  "caller_expert_id": "comment-assistant",
  "total": 1,
  "risk_total": 1,
  "submit": {
    "next_step": "执行comment-assistant专家的刷新留言列表步骤"
  },
  "list": [
    {
      "comment_id": 123456789,
      "subject_id": "subj_001",
      "content": "钱都去哪了？...",
      "object_type": "project",
      "object_id": "224328",
      "project_id": "224328",
      "project_name": "春蕾计划她们想上学",
      "created_at": 1756000000,
      "nick_name": "爱心网友A",
      "risk_audit_status": 4,
      "risk_audit_reason": "质疑资金去向",
      "ai_suggestion": "您好，感谢您的关注和监督！...",
      "process_name": "",
      "refer_process_num": 5
    }
  ]
}

// 响应：原样返回数据，由 Host 渲染为留言回复卡片
```

## 注意事项

1. **`caller_expert_id` 必填**：schema 唯一 required 字段；取当前对话绑定的专家 ID，取不到时自行生成一个对话标识 ID（仅限英文大小写字母、数字、`_`、`-`）
2. **`additionalProperties: false`**：顶层只允许 `caller_expert_id` / `total` / `risk_total` / `submit` / `list`；`code` / `msg` 等字段会被参数校验拒绝，错误信息由 Agent 文本报告承载
   - **`list` 的值直接是留言对象数组**：`"list": [{...}, {...}]`。⛔ 禁止任何形式的多余嵌套/包装——`{"list": {"list": [...]}}`、`{"list": [[...]]}`、`{"list": {"items": [...]}}`、元素再包一层对象/数组，均属结构错误，会被参数校验拒绝并白白浪费一轮重试（大载荷下重试成本极高）。调用前自检：顶层平铺 5 个键、`list` 是数组、`list[0]` 是含 `comment_id` 的扁平对象
3. **`data_cache_id` 由服务端生成与管理**：`set_common_data_cache` 写入成功后返回此 key，Agent 将其传给 `open_comment_reply_ui` 取数渲染
4. **`submit.next_step` 固定值**：「执行comment-assistant专家的刷新留言列表步骤」，一字不差（可路由句式"执行X专家的Y步骤"，Host 据此重新调度本专家）
5. **最小白名单**：`list` 元素只保留上方「✅ 保留字段」表中的 15 个字段（12 协议 + 3 增强），「⛔ 剔除字段」表中的 21 个字段一律不得传入，也不得新增其它业务字段
6. **uint64 类型**：`comment_id` 协议为 uint64，全程必须是 **JSON number**——`fetch_payload.py` 落盘 `comments_brief.json` 时已统一转为 int（Python int 无精度问题），本工具调用载荷中不得出现字符串形态；`build_ui_payload.py` 保留防御性转换兜底；其余字段保持原始类型透传
7. **不二次排序**：`list` 保持后台返回的原始数组顺序（高风险优先已由后台排好）
8. **禁止文本复述**：工具结果不含文本摘要，Agent 不得在对话中复述或以表格罗列这些数据
9. 测试环境调用需在 HTTP header 携带 `Gy-H-Test-Env-Key: x1`（已在 MCP Server 配置中注入）
