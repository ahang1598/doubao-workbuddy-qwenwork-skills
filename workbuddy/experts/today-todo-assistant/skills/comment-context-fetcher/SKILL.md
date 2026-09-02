---
name: comment-context-fetcher
description: "拉取评论关联的项目或进展上下文。按 object_type 分类：project → get_project_detail（项目详情）+ get_process_list（该项目最近5条进展，无进展则仅项目详情）；process → get_process_detail（该条进展），并按评论自带的 project_id 追加拉取所属项目详情。单次 run 内按 id 去重（同一 id 仅拉一次），去重后全部并行请求；不做跨 run 磁盘缓存。"
---

# 评论上下文拉取

> **⚠️ 数据平面已脚本化**：本 Skill 的 MCP 调用执行入口已切换为 `skills/comment-context-fetcher/scripts/fetch_payload.py`（拉取+分类+去重+并行，单次 run 内按 id 去重、不做跨 run 磁盘缓存，并在拉取完成后一并组装精简 contexts.json / comments_brief.json），大 JSON 落盘不经过 LLM。本文档的**分类/去重规则、`get_process_list` 固定参数（index=1/size=5/platform_version=3/status=1/publish_status=-1）、上下文组合契约（project=项目详情+最近5条进展，process=进展详情+所属项目详情）仍为权威定义**，脚本按其实现。
>
> **🔑 执行前置（Token 全局缓存优先，对齐 invoice-expert 约定）**：`fetch_payload.py` 读写全局缓存 `~/.workbuddy/.gongyi_token`（跨专家共享，token 内含 `_prod_`/`_test_` 环境段天然隔离测试/正式环境）——**不传 `--token` 时脚本自动读缓存，有就直接用、不用每次调 `get_mcp_token`**；本地不判断过期时间，过期以接口鉴权失败为准。脚本打印 `{"need_refresh": true, ...}`（退出码 3 无缓存 / 4 鉴权失败已自动清缓存）时，调用 MCP 工具 `get_mcp_token`（携带 `caller_expert_id="comment-assistant"`，一次调用完成，禁止先无参调用再重试）获取新 token，以 `--token` 重跑（脚本同步写回缓存）。token 不打印。详见 `agents/comment-assistant.md` Step 0。

## 概述

本 Skill 负责拉取评论关联的项目或进展的公开信息，为 AI 生成建议回复提供事实依据。

**核心功能**：
- 根据 `object_type` 调用对应 MCP 工具
- `project` → `get_project_detail`（项目详情）**+ 追加 `get_process_list`（该项目最近 5 条进展）**：产品要求项目评论的回复信息来源 = 项目信息 + 最近 5 条进展（最多 5 条；没有进展则只用项目信息）。固定参数 `index=1, size=5, platform_version=3, status=1, publish_status=-1`，与项目详情并行拉取
- `process` → `get_process_detail`（进展详情）**+ 追加 `get_project_detail`（进展所属项目详情）**：进展评论逻辑保持不变，回复需结合「进展内容 + 所属项目信息」，项目 ID 直接取评论自带的 `project_id`（无需等进展拉完再取），与进展拉取并行
- 支持批量并行拉取；**单次 run 内按 id 去重**（同一 id 仅拉一次），**不做跨 run 磁盘缓存**（每次 run 实时拉取）

**关键约束**：
- 只读取已发布的、可追溯的信息
- 拉取失败时降级为 `"context": null`，不阻断流程
- 去重粒度为「`object_type` + `object_id`」：**同一类型的同一个 `object_id` 单次 run 内仅拉取一次**；不同类型允许相同 `object_id` 各自拉取（project 与 process 是不同命名空间）
- **process 的所属项目按 id 去重**：进展评论自带的 `project_id` 收集后按 id 去重，同一 `project_id` 单次 run 内仅拉一次 `get_project_detail`（与 project 组合并去重，避免同一项目被 project 评论与 process 评论重复拉取）
- **project 的进展列表按 id 去重**：同一 `project_id` 单次 run 内仅拉一次 `get_process_list`（10 条 project 评论属同一项目时只拉 1 次）
- **不做跨 run 磁盘缓存**：以上去重仅单次 run 内有效，每次 run 都实时拉取，保证不读到陈旧数据
- **并行拉取**：project 组（项目详情 + 进展列表）、process 组、process 所属项目组之间、同组内多个 id 之间均并行发起调用，互不串行等待

## 触发场景

Agent 在 Phase 3（拉取上下文）时加载本 Skill。

## 输入格式

```json
{
  "items": [
    {
      "object_type": "project",
      "object_id": "224328"
    },
    {
      "object_type": "process",
      "object_id": "652964",
      "project_id": "224328"
    }
  ]
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `items` | array | 是 | 待拉取上下文的列表 |
| `items[].object_type` | string | 是 | 对象类型：`project` / `process` |
| `items[].object_id` | string | 是 | 对象 ID |
| `items[].project_id` | string | process 必填 | 所属项目 ID（直接取评论 `OrgCommentItem.project_id`；object_type=process 时用于追加拉取所属项目详情，project 类型忽略） |

## 工作流程

1. **分类**：按 `object_type` 分为 project / process 两组
2. **组内去重**：每组内按 `object_id` 去重，同一类型的同一个 `object_id` 单次 run 内只保留一条；不同类型不去重（命名空间不同）
3. **收集 process 所属项目**：对 process 组每条评论取自带 `project_id`，汇总后**按 `project_id` 去重**（与 project 组的 project_id 合并去重——同一项目若既有 project 评论又有 process 评论，单次 run 内仅拉一次）
4. **并行批量调用**（各类并行发起，同组内多个 id 也并行）：
   - `project` 组 → 并行调用 `get_project_detail`（按 object_id 去重）
   - `project` 组 → 并行调用 `get_process_list`（按 project_id 去重，固定参数 `index=1, size=5, platform_version=3, status=1, publish_status=-1`，取该项目最近 5 条进展）
   - `process` 组 → 并行调用 `get_process_detail`（按 object_id 去重）
   - process 所属项目组 → 并行调用 `get_project_detail`（按 project_id 去重，与 project 组合并去重）
4. **组装结果**：两段式结构——`projects` 按 project_id 单独存放项目数据（`project_detail` 含基础字段 + 项目背景/爱心故事 + 募捐信息/执行地(名称)/生效备案号预算；`process_list` 仅 project 类型留言所属项目有），`contexts` 按 `object_type:object_id` 复合键存放各留言对象上下文并以 `project_id` 引用 `projects`（避免跨类型 ID 碰撞互相覆盖，也避免同一项目数据在多条进展上下文中重复内嵌）：
   - **project 类型**上下文 = `{"type": "project", "project_id": "<pid>"}`，项目数据取 `projects[pid]`（`project_detail` + `process_list` 最近 5 条，无进展/拉取失败为空数组）
   - **process 类型**上下文 = `{"type": "process", "process_detail": {...}, "project_id": "<pid>"}`，所属项目详情取 `projects[pid].project_detail`

## 输出格式

```json
{
  "projects": {
    "224328": {
      "project_detail": {
        "project_name": "春蕾计划她们想上学",
        "project_intro": "...",
        "project_type": 1,
        "fundras_filing_code": "...",
        "closing_date": "2026-12-31",
        "close_fundraising_time": "2026-12-31 23:59:59",
        "project_backdrop_title": "项目背景",
        "project_backdrop": "项目背景正文（已剥离 HTML）...",
        "love_story_list": [
          {"story_name": "...", "story_intro": "故事正文（已剥离 HTML）...", "story_summary": "..."}
        ],
        "fundras_cycle_start_time": "2026-01-01",
        "fundras_cycle_end_time": "2026-12-31",
        "beneficiaries": "偏远学校",
        "assisted_materials": "艺术课",
        "assisted_materials_unit": "节",
        "executor_site": [
          {"province_name": "北京市", "city_name": "北京市", "area_name": "东城区"}
        ],
        "filing_budget": {
          "fundras_target": "500.00",
          "budget_list": [
            {"cost_item_one_name": "...", "cost_item_two_name": "...", "execution_content": "...", "amount_desc": "..."}
          ]
        }
      },
      "process_list": [
        {
          "id": 1001,
          "content_title": "2026年7月进展报告",
          "desc": "本月完成...",
          "publish_time": 1786000000
        }
      ]
    }
  },
  "contexts": {
    "project:224328": {
      "type": "project",
      "project_id": "224328"
    },
    "process:652964": {
      "type": "process",
      "process_detail": {
        "content_title": "项目进展报告",
        "desc": "...",
        "content": "...",
        "concrete_info": "...",
        "publish_time": "2026-08-01 10:00:00"
      },
      "project_id": "224328"
    }
  }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `projects` | map | 按 project_id 单独存放的项目数据（同一项目仅一份，被多条上下文引用） |
| `projects[pid].project_detail` | object | 项目详情：基础字段（含项目分类/资助对象名称）+ `project_backdrop(_title)`（项目背景）+ `love_story_list`（爱心故事）+ 募捐信息（`fundras_cycle_start_time`/`fundras_cycle_end_time`/`beneficiaries`/`assisted_materials(_unit)`）+ `executor_site`（执行地，仅 province_name/city_name/area_name 三个名称字段）+ `filing_budget`（is_valid=1 生效备案号的筹款目标 + 预算表 4 字段），富文本已剥离 HTML；字段明细以 [get_project_detail.md](references/tools/get_project_detail.md) 为权威定义 |
| `projects[pid].process_list` | array | **仅 project 类型留言所属项目有**：该项目最近 5 条进展（最多 5 条；无进展/拉取失败时为空数组） |
| `contexts` | map | 按 `object_type:object_id` 复合键映射的上下文（避免跨类型 ID 碰撞互相覆盖） |
| `contexts[key].type` | string | 上下文类型：`project` / `process` |
| `contexts[key].project_id` | string | 引用 `projects` 的键：type=project 时为该项目自身；**type=process 时为该进展所属项目**（取评论自带 project_id） |
| `contexts[key].process_detail` | object | 进展详情（type=process 时） |

## 异常处理

| 场景 | 处理方式 |
|------|---------|
| MCP 调用失败 | 该 `object_id` 的上下文设为 `null` |
| 项目/进展不存在 | 该 `object_id` 的上下文设为 `null` |
| 部分失败 | 成功的正常返回，失败的设为 `null` |

## 依赖

- MCP Server: `gongyi-open-mcp`
- MCP Tools: `get_project_detail`, `get_process_detail`, `get_process_list`

## 参考文档

- [get_project_detail.md](references/tools/get_project_detail.md)
- [get_process_detail.md](references/tools/get_process_detail.md)
- [get_process_list.md](references/tools/get_process_list.md)
- [mcp-tool-mapping.md](references/mcp-tool-mapping.md)
