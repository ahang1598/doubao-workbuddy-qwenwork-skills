---
name: comment-task-manager
description: "任务状态管理。组装结构化数据返回给前端：MCP 查询结果按最小白名单裁剪（仅保留 comment_id/subject_id/content/project_id/project_name/created_at/nick_name/object_type/object_id/risk_audit_status/risk_audit_reason/head_img 共 12 个协议字段，其余 21 个字段全部剔除）+ 逐条挂载 AI 建议回复（ai_suggestion）、进展名称（process_name，仅 process 类型，取自上下文进展标题）与参考进展条数（refer_process_num，int，project 类型取 process_list 长度，process 类型取 1/0），列表顺序保持 MCP 返回的原始数组顺序（后台已排好序，不做二次排序）。管理留言回复任务的状态（选中状态、编辑内容）。不含机构鉴权（MCP Token 自动完成）。"
---

# 任务状态管理

> **⚠️ 数据平面已脚本化**：本 Skill 的组装执行入口已切换为 `scripts/build_ui_payload.py`（白名单裁剪 + 挂载增强字段 + 产出 `open_comment_reply_ui` 完整入参 + **直连 MCP 调 `set_common_data_cache` 写后台缓存**），Agent 不再手工组装、也不再透传大载荷——只需把脚本返回的 `data_cache_id` 传给 `open_comment_reply_ui`。本文档的**11 字段白名单、`ai_suggestion`/`process_name`/`refer_process_num` 挂载规则、`submit.next_step` 契约文案、`open_comment_reply_ui` schema 约束仍为权威定义**，脚本按其实现。

## 概述

本 Skill 负责组装 Phase 1-4 的输出为前端需要的结构化数据，并管理留言回复任务的状态。

**核心功能**：
- 组装结构化数据（`total` / `risk_total` / `list`），由 Agent 调用 MCP 工具 `open_comment_reply_ui`（gongyi-open-mcp）传入该 JSON 展示到留言回复页面
- `list` 元素为 `OrgCommentItem` **按最小白名单裁剪**后的字段（仅保留 UI 展示 + 提交必需的 12 个协议字段：`comment_id` / `subject_id` / `content` / `project_id` / `project_name` / `created_at` / `nick_name` / `object_type` / `object_id` / `risk_audit_status` / `risk_audit_reason` / `head_img`，其余 21 个字段全部剔除）+ `ai_suggestion` 增强字段 + `process_name` 增强字段（仅 process 类型，取自进展标题，供前端展示信息来源）+ `refer_process_num` 增强字段（int，参考的进展条数，供前端展示信息来源规模）
- 列表顺序保持 MCP 返回的原始数组顺序（后台返回的 tool 数据本身已排好序），Agent 不做任何二次排序
- 管理任务状态（选中状态、编辑内容）

**关键约束**：
- 不含机构鉴权（MCP Token 自动完成）
- 只负责数据组装，不负责 UI 渲染
- `list` 元素必须按最小白名单裁剪 `OrgCommentItem`：只保留 12 个协议字段（`comment_id` / `subject_id` / `content` / `project_id` / `project_name` / `created_at` / `nick_name` / `object_type` / `object_id` / `risk_audit_status` / `risk_audit_reason` / `head_img`），其余字段（`status` / `gy_uid` / `like_num` / `comment_type` / `can_reply` / `is_recommended` / `reply_list` / `audit_type` / `risk_audit_at` / `opt_user` / `parent_comment_content` / `is_sticky` / `sticky_expire` / `can_sticky` / `can_cancel_sticky` / `can_delete` / `org_comment_id` / `org_reply_content` / `org_reply_time` / `parent_comment` / `audit_reject_reason` 共 21 个）一律剔除（UI 不使用）；不得新增业务字段（`ai_suggestion`、`process_name`、`refer_process_num` 三个 Agent 增强字段除外）
- 输出顶层**只允许** `total` / `risk_total` / `list` / `submit`（`open_comment_reply_ui` schema 不接受 `code`/`msg`，`additionalProperties: false`）；调用工具时另传 schema 唯一必填字段 `caller_expert_id`（详见参考文档）；Agent 运行状态（processed、ui_push_status、ui_push_error、note 等）禁止写入输出 JSON，由 Agent 文本报告承载
- reply-generator 的 `sources`（事实来源记录）属内部审计数据，**不得挂载到 list 元素**，不进入 UI 协议
- 字段类型对齐协议：`comment_id`（uint64）全程必须是 **JSON number**——`fetch_payload.py` 落盘 `comments_brief.json` 时已将上游字符串形态统一转为 int（Python int 无精度问题），本地文件与 `set_common_data_cache` 调用均不得出现字符串形态；`build_ui_payload.py` 保留防御性转换兜底；`org_comment_id` 等其他字段保持原始类型原样透传
- 输出结构必须与 `openspec/changes/comment-assistant/fe-view-protocol.md` 协议一定义完全一致

## 触发场景

Agent 在 Phase 3（组装数据并调用 open_comment_reply_ui 展示留言回复页面）时加载本 Skill。本 Skill 只负责组装输出 JSON；Agent 拿到输出后必须调用 `open_comment_reply_ui` 将其展示到留言回复页面，不得仅以文本形式输出列表。

## 输入格式

```json
{
  "comments": [
    {
      "comment_id": 123456789,
      "subject_id": "subj_001",
      "content": "钱都去哪了？...",
      "object_type": "project",
      "object_id": "224328",
      "project_id": "224328",
      "project_name": "春蕾计划她们想上学",
      "nick_name": "爱心网友A",
      "created_at": 1756000000,
      "status": 1,
      "risk_audit_status": 4,
      "risk_audit_reason": "质疑资金去向"
    }
  ],
  "ai_suggestions": {
    "123456789": "您好，感谢您的关注和监督！..."
  },
  "total": 36,
  "risk_total": 2
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `comments` | array | 是 | 留言列表（Phase 1 输出的完整 `OrgCommentItem`，本 Skill 负责按白名单裁剪后透出） |
| `ai_suggestions` | map | 是 | AI 建议回复映射（comment_id → ai_suggestion 字符串，Phase 4 的 reply-generator 输出） |
| `contexts` | map | 是 | 上下文映射（`object_type:object_id` → 上下文，Phase 3 的 comment-context-fetcher 输出）；process 类型条目的 `process_detail.content_title` 用于填充 `process_name`；project 类型条目的 `process_list` 长度、process 类型条目的 `process_detail` 有无用于填充 `refer_process_num` |
| `total` | uint32 | 是 | 待回复总数（MCP 返回的 total） |
| `risk_total` | uint32 | 是 | 高风险数（MCP 返回的 risk_total） |

## 工作流程

采用**零转录（no re-transcription）原地增强**方式组装，杜绝手工抄写字段导致的错值/丢字段/类型变化：

1. **保留原始对象**：Phase 1 MCP 返回的响应对象原样保留在内存中（或原样字节），不重新拼写、不逐字段抄录、不写中间转换脚本/中间 JSON 文件
2. **原地挂载（仅有的三个赋值操作）**：
   - `list[i].ai_suggestion = ai_suggestions[list[i].comment_id]`；未处理到的条目置空串
   - `list[i].process_name`：仅当 `list[i].object_type === 'process'` 时赋值，取 `contexts['process:' + list[i].object_id]?.process_detail?.content_title`；取不到（进展拉取失败/无标题）或 project 类型置空串
   - `list[i].refer_process_num`（int，参考的进展条数）：`object_type === 'project'` 时取 `contexts['project:' + list[i].object_id]?.process_list?.length ?? 0`（0~5，无进展/拉取失败为 0）；`object_type === 'process'` 时取 1（参考该条进展；`process_detail` 拉取失败则取 0）
   **除 `ai_suggestion`、`process_name` 与 `refer_process_num` 外不允许对任何字段重新赋值**
3. **最小白名单裁剪（仅有的删除操作）**：每个 `list[i]` 只保留 12 个协议字段（`comment_id` / `subject_id` / `content` / `project_id` / `project_name` / `created_at` / `nick_name` / `object_type` / `object_id` / `risk_audit_status` / `risk_audit_reason` / `head_img`），删除其余全部字段（`status` / `gy_uid` / `like_num` / `comment_type` / `can_reply` / `is_recommended` / `reply_list` / `audit_type` / `risk_audit_at` / `opt_user` / `parent_comment_content` / `is_sticky` / `sticky_expire` / `can_sticky` / `can_cancel_sticky` / `can_delete` / `org_comment_id` / `org_reply_content` / `org_reply_time` / `parent_comment` / `audit_reject_reason` 共 21 个，UI 不使用）；保留字段的值一律原样，不增不改
4. **保持原始顺序**：`list` 不做任何排序/重排——后台返回的 tool 数据本身已排好序，按数组原始顺序直接展示
5. **缓存写入 + key 展示**：脚本把组装好的 `{total, risk_total, list, submit}` 直连 MCP 调 `set_common_data_cache` 写入后台缓存，返回 `data_cache_id`；Agent 调 `open_comment_reply_ui` 只传 `caller_expert_id` + `data_cache_id`，大载荷不经过 LLM 输出。`submit` 固定为 `{"next_step": "执行comment-assistant专家的刷新留言列表步骤"}`，告知 APP 应发起的专家步骤调用（回复由 APP 直连后台提交并自动删除已提交留言，不经 Agent；**仅剩余待回复为 0 时 APP 才通知 Host 发起该步骤**）。缓存写入失败时也走相同方式（`caller_expert_id` + `data_cache_id`）

**⛔ 禁止**：
- 把留言字段逐个手写进新 JSON（历史事故：head_img 重复、project_id 乱码、误加 code/msg、list 多余嵌套，均源于手工转录/组装）
- 由 Agent 在上下文内手工执行本 Skill 的组装逻辑——**组装的唯一执行入口是 `scripts/build_ui_payload.py`**（在本地完成裁剪与挂载、写出 `ui_payload.json`，并直连 MCP 把数据写入后台缓存；Agent 只把返回的 `data_cache_id` 传给 `open_comment_reply_ui`，无需 Read 载荷文件）；手工组装在大载荷场景已实测发生结构错误与超长输出

## 输出格式

```json
{
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
    },
    {
      "comment_id": 123456790,
      "subject_id": "subj_002",
      "content": "加油！希望孩子们都能好好读书",
      "project_id": "224328",
      "project_name": "春蕾计划她们想上学",
      "created_at": 1756000100,
      "nick_name": "匿名捐赠人",
      "object_type": "project",
      "object_id": "224328",
      "risk_audit_status": 3,
      "ai_suggestion": "感谢支持，我们会持续努力！",
      "process_name": "",
      "refer_process_num": 5
    }
  ]
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `total` | uint32 | 待回复总数（与 MCP 返回的 total 口径一致） |
| `risk_total` | uint32 | 高风险数（与 MCP 返回的 risk_total 口径一致：risk_audit_status=4 且 status=1） |
| `list` | array | 留言列表，保持 MCP 返回的原始数组顺序（后台已排序，不二次排序）；元素为 `OrgCommentItem` **按最小白名单裁剪**（仅保留 12 个协议字段，剔除其余 21 个字段）+ `ai_suggestion` / `process_name` / `refer_process_num` 三个增强字段 |
| `submit` | object | 提交动作契约：APP 完成提交后据此通知专家刷新。固定为 `{"next_step": "执行comment-assistant专家的刷新留言列表步骤"}` |

> 顶层**只含** `total` / `risk_total` / `list` / `submit`：`open_comment_reply_ui` 的 schema 为 `additionalProperties: false`，传入 `code`/`msg` 会被参数校验直接拒绝。**无论主路径还是降级路径，Agent 都只传 `caller_expert_id` + `data_cache_id`**（data_cache_id = `set_common_data_cache` 返回的缓存 key，由脚本写入后台缓存后获得）。`submit.next_step` 固定为「执行comment-assistant专家的刷新留言列表步骤」，一字不差（格式为可路由句式"执行X专家的Y步骤"，Host 据此解析专家与步骤名并重新调度）。错误信息由 Agent 文本报告承载，不写入输出 JSON。

**关键规则**：

- `list[]` 元素必须按最小白名单裁剪：只保留 `comment_id` / `subject_id` / `content` / `project_id` / `project_name` / `created_at` / `nick_name` / `object_type` / `object_id` / `risk_audit_status` / `risk_audit_reason` / `head_img` 共 12 个协议字段 + 3 个增强字段，其余 21 个字段一律剔除（UI 不使用），不得额外裁剪或新增
- `process_name` 仅 process 类型挂载（取 `process_detail.content_title`），供前端展示「信息来源：项目名称（项目id）；进展名称（进展id）」；project 类型为空串
- `refer_process_num` 为 int：project 类型 = 该项目上下文 `process_list` 条数（0~5，无进展/拉取失败为 0）；process 类型 = 1（参考该条进展，`process_detail` 拉取失败为 0），供前端展示「参考进展 N 条」
- `ai_suggestion` 取自输入 `ai_suggestions` 映射，原样写入；未生成建议的条目置空串（前端做空态展示）
- 不拆分高风险/无风险列表，也不对 list 做二次排序；高风险优先由后台返回的原始数组顺序体现

## 异常处理

| 场景 | 处理方式 |
|------|---------|
| 某条无 AI 建议 | 该条 `ai_suggestion` 置空串 |
| 无待回复留言 | 返回 `total: 0, risk_total: 0, list: []` |
| 上游任一环节失败 | `list` 置空数组，错误原因由 Agent 文本报告承载，不写入输出 JSON |

## 依赖

- 无外部依赖（纯数据组装）

## 参考文档

- [references/tools/open_comment_reply_ui.md](references/tools/open_comment_reply_ui.md)：`open_comment_reply_ui` 工具调用参数定义（仅 `caller_expert_id` + `data_cache_id`）
- [references/tools/set_common_data_cache.md](references/tools/set_common_data_cache.md)：`set_common_data_cache` 写入数据的 JSON 结构定义（`total`/`risk_total`/`list`/`submit` 字段表、`CommentReplyItem` / `CommentReplyChildItem` 元素白名单、调用示例与注意事项）
