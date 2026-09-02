---
name: comment-fetcher
description: "查询机构 3.0 平台待回复留言。调用 MCP 工具 get_org_upreplied_comments，获取未回复的项目评论和进展评论列表，包含评论内容、用户信息、风险等级、object_type 等关键字段。支持分页和筛选。"
---

# 待回复留言查询

> **⚠️ 数据平面已脚本化**：本 Skill 的 MCP 调用执行入口已切换为 `skills/comment-context-fetcher/scripts/fetch_payload.py`（直连 oapi HTTP，大 JSON 落盘不经过 LLM），Agent 不再加载本 Skill 执行 MCP 调用。本文档的**接口协议、参数契约（size=30、start_time=当前 Unix 秒 - 2592000 等）仍为权威定义**，脚本按其实现。
>
> **🔑 执行前置（Token 全局缓存优先，对齐 invoice-expert 约定）**：`fetch_payload.py` 读写全局缓存 `~/.workbuddy/.gongyi_token`（跨专家共享，token 内含 `_prod_`/`_test_` 环境段天然隔离测试/正式环境）——**不传 `--token` 时脚本自动读缓存，有就直接用、不用每次调 `get_mcp_token`**；本地不判断过期时间，过期以接口鉴权失败为准。脚本打印 `{"need_refresh": true, ...}`（退出码 3 无缓存 / 4 鉴权失败已自动清缓存）时，调用 MCP 工具 `get_mcp_token`（携带 `caller_expert_id="comment-assistant"`，一次调用完成，禁止先无参调用再重试）获取新 token，以 `--token` 重跑（脚本同步写回缓存）。token 不打印。详见 `agents/comment-assistant.md` Step 0。

## 概述

本 Skill 负责查询机构 3.0 平台的待回复留言列表，是留言回复流程的第一步。

**核心功能**：
- 调用 MCP `get_org_upreplied_comments` 查询未回复留言
- 返回分页数据（总数、高风险数、留言列表）
- 支持时间范围、项目 ID 筛选

**关键约束**：
- MCP Token 自动注入 `org_no`，无需额外鉴权（指直连 MCP 通道；脚本化路径必须显式传 `--token`，见顶部执行前置）
- **固定传 `size=30`**（单次查询固定一页 30 条；MCP 工具已支持 size 透传）
- **固定传 `start_time = 当前 Unix 秒 - 2592000`**（产品要求只查询 30 天及之内的数据；服务端不传时默认 30 天前，但调用方必须显式传，避免依赖默认值）
- 查询失败时返回空列表，不阻断流程

## 触发场景

Agent 在 Phase 1（查询待回复留言）时加载本 Skill。

## 输入格式

```json
{
  "page": 0,
  "size": 30,
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
| `size` | uint32 | 是 | 每页大小，**固定传 30**（单次固定 30 条），最大 100 |
| `filter_start_time` | uint32 | 否 | 筛选开始时间戳（秒），0 表示不筛选 |
| `filter_end_time` | uint32 | 否 | 筛选结束时间戳（秒），0 表示不筛选 |
| `filter_project_id` | string | 否 | 项目 ID 筛选，空表示全部项目 |
| `mock_org_no` | string | 否 | 模拟机构 ID（仅七彩石 `enable_org_mock=true` 时生效，测试用） |
| `start_time` | int64 | 否 | 查询起始时间（Unix 秒），不传默认 30 天前。**产品要求只查询 30 天及之内的数据，每次调用必须显式传「当前 Unix 秒 - 2592000（30 天）」**，不依赖服务端默认值 |

## 工作流程

1. **参数校验**：校验 page/size 范围，size 固定 30，最大 100
2. **计算时间范围**：`start_time = 当前 Unix 秒 - 2592000`（30 天前），每次调用实时计算
3. **调用 MCP**：调用 `get_org_upreplied_comments`，入参原样透传（含 `start_time`）
3. **返回结果**：返回原始 `total` / `risk_total` / `OrgCommentItem[]`，**全字段透传不裁剪、不做加工**

## 输出格式

```json
{
  "total": 36,
  "risk_total": 2,
  "list": [
    {
      "comment_id": 123456789,
      "subject_id": "subj_001",
      "content": "钱都去哪了？一直没看到进展更新，是不是骗人的？",
      "object_type": "project",
      "object_id": "224328",
      "project_id": "224328",
      "project_name": "春蕾计划她们想上学",
      "status": 1,
      "nick_name": "爱心网友A",
      "head_img": "https://.../avatar.png",
      "like_num": 3,
      "created_at": 1756000000,
      "can_reply": true,
      "is_recommended": false,
      "reply_list": [],
      "audit_type": 2,
      "risk_audit_status": 4,
      "risk_audit_reason": "质疑资金去向",
      "risk_audit_at": 1756000050,
      "comment_type": 0
    }
  ]
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `total` | uint32 | 待回复留言总数（满足筛选条件的主评论数） |
| `risk_total` | uint32 | 高风险留言数（风控拦截评论总数：risk_audit_status=4 且 status=1） |
| `list` | OrgCommentItem[] | 留言列表（全字段透传，上方示例仅展示部分字段，实际返回不得裁剪） |

**OrgCommentItem 关键字段**（完整字段见参考文档）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `comment_id` | uint64 | 评论 ID |
| `subject_id` | string | 主题 ID（分片键，批量回复时必传） |
| `content` | string | 评论内容 |
| `object_type` | string | 对象类型：`project` / `process` / `yqj_feeds` |
| `object_id` | string | 对象 ID（project 类型时为项目 ID，process 类型时为进展 ID） |
| `project_id` | string | 项目 ID |
| `project_name` | string | 项目名称 |
| `status` | uint32 | 审核状态：0-待审核, 1-审核通过, 2-审核拒绝（本接口只返回审核通过的） |
| `nick_name` | string | 评论作者昵称 |
| `head_img` | string | 评论作者头像 URL |
| `like_num` | uint32 | 点赞数 |
| `created_at` | uint32 | 创建时间戳 |
| `can_reply` | bool | 是否可回复该评论 |
| `is_recommended` | bool | 是否 AI 推荐回复 |
| `reply_list` | OrgCommentReplyItem[] | 评论下的回复列表 |
| `audit_type` | uint32 | 审核类型：0-未审核, 1-UGC审核, 2-AI审核 |
| `risk_audit_status` | uint32 | 风控状态：0-审核中, 1-UGC拦截, 2-粗筛未命中, 3-AI放行, 4-AI拦截 |
| `risk_audit_reason` | string | 风控拦截原因（仅当 risk_audit_status=4 时有值） |
| `risk_audit_at` | uint32 | 风控状态最近更新时间（时间戳） |
| `comment_type` | uint32 | 0-用户留言, 2-机构回复, 3-管理员回复 |

## 异常处理

| 场景 | 处理方式 |
|------|---------|
| MCP 调用失败 | 返回空列表，不阻断流程 |
| 无待回复留言 | 返回 `total: 0, risk_total: 0, list: []` |
| 参数非法 | 使用默认值（page=0, size=30） |

## 依赖

- MCP Server: `gongyi-open-mcp`
- MCP Tool: `get_org_upreplied_comments`

## 参考文档

- [get_org_upreplied_comments.md](references/tools/get_org_upreplied_comments.md)
