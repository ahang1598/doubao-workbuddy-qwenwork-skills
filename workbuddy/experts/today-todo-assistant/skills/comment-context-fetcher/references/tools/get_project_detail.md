# get_project_detail

## 工具信息

| 项目 | 内容 |
|------|------|
| MCP Server | `gongyi-open-mcp` |
| 工具名 | `get_project_detail` |
| 接口名 | `GetProjectDetailForSkill` |
| 来源 | `project_manager_trpc.proto`（`GetProjectDetailForSkillReply`，见 `proto/project.proto`） |
| oapi 路径 | `/api/project_manager_trpc/GetProjectDetailForSkill` |

## 接口定义

查询项目详情，为 AI 生成建议回复提供项目公开信息。服务端复用 `GetProjectLaunch` 的数据加载逻辑，返回项目基础信息 / 详细富文本 / 爱心故事 / 募捐信息 / 备案号预算 / 执行地点。

## 请求参数

```json
{
  "project_no": "224328"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `project_no` | string | 是 | 项目编码 |

## 响应参数（生成侧消费的结构）

```json
{
  "info": {
    "project_name": "春蕾计划她们想上学",
    "project_intro": "项目简介...",
    "project_type": 1,
    "project_first_name": "教育助学",
    "project_second_name": "困境儿童助学",
    "fundras_object_first_name": "人",
    "fundras_object_second_name": "困境儿童",
    "fundrais_filing_code": "...",
    "closing_date": "2026-12-31",
    "close_fundraising_time": "2026-12-31 23:59:59",
    "fundras_state": 3,
    "online_time": "2026-01-01"
  },
  "detail": {
    "project_backdrop_title": "项目背景",
    "project_backdrop": "<p>项目背景正文（HTML）...</p>"
  },
  "loveStory": [
    {
      "story_name": "故事名",
      "story_intro": "<p>故事正文（HTML）...</p>",
      "story_summary": "AI 摘要（≤30 字）"
    }
  ],
  "donate": {
    "fundras_cycle_start_time": "2026-01-01",
    "fundras_cycle_end_time": "2026-12-31",
    "beneficiaries": "偏远学校",
    "assisted_materials_unit": "节",
    "assisted_materials": "艺术课"
  },
  "filing_budget": [
    {
      "fundrais_filing_code": "...",
      "fundras_target": "500.00",
      "is_valid": 1,
      "budget_list": [
        {
          "cost_item_one_name": "直接或委托其他组织资助给受益人的款物",
          "cost_item_two_name": "款项捐赠",
          "execution_content": "教育助学",
          "amount_desc": "助学金"
        }
      ]
    }
  ],
  "executorSite": [
    {
      "province_name": "北京市",
      "city_name": "北京市",
      "area_name": "东城区"
    }
  ]
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `info` | Info | 项目基础信息（名称、简介、分类/资助对象名称、备案号、状态、时间等） |
| `detail` | Detail | 项目详细信息（富文本）：生成侧仅消费项目背景，正文为 HTML |
| `loveStory` | array | 爱心故事列表（`story_name` / `story_intro` HTML / `story_summary` AI 摘要 ≤30 字） |
| `donate` | Donate | 募捐信息：筹款周期、受益对象、资助物资等量词 |
| `filing_budget` | array | 备案号预算列表；`is_valid=1` 为当前生效条目，含筹款目标 `fundras_target` 与预算表 `budget_list` |
| `executorSite` | array | 执行地点列表；`province_name`/`city_name`/`area_name` 由服务端统一回填（解析失败降级为空），生成侧只保留名称、不消费编码 |

> 接口原始响应还包含 `budget`（项目预算）、`funding_level`（资助档位）、`executor_info`（执行方信息）等节点，**生成侧不消费、脚本不写入精简上下文**，本文档不再展开。

## Info 关键字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `project_name` | string | 项目名称 |
| `project_intro` | string | 项目简介 |
| `project_type` | int32 | 项目类型 |
| `fundrais_filing_code` | string | 募捐备案号 |
| `closing_date` | string | 截止日期 |
| `close_fundraising_time` | string | 关闭筹款时间 |
| `project_first_name` | string | 项目一级分类名称 |
| `project_second_name` | string | 项目二级分类名称 |
| `fundras_object_first_name` | string | 资助对象一级分类名称 |
| `fundras_object_second_name` | string | 资助对象二级分类名称 |
| `fundras_state` | int32 | 项目状态 1:未上线、2:已上线、3:筹款中、4:暂停筹款、5:结束筹款、6:不可募款、7:已结项 |
| `online_time` | string | 上线时间 |

## Detail 关键字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `project_backdrop_title` / `project_backdrop` | string | 项目背景标题 / 正文（HTML） |

## Donate 关键字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `fundras_cycle_start_time` | string | 开始筹款时间 |
| `fundras_cycle_end_time` | string | 结束筹款时间 |
| `beneficiaries` | string | 受益对象 |
| `assisted_materials` | string | 资助物资（公益单位） |
| `assisted_materials_unit` | string | 资助量词 |

## FilingBudgetInfo / BudgetInfo 关键字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `filing_budget[].is_valid` | int32 | 是否当前生效 0-否 1-是（生成侧仅取 `is_valid=1` 的条目） |
| `filing_budget[].fundras_target` | string | 筹款目标（元） |
| `filing_budget[].budget_list[].cost_item_one_name` | string | 费用项一级名称 |
| `filing_budget[].budget_list[].cost_item_two_name` | string | 费用项二级名称 |
| `filing_budget[].budget_list[].execution_content` | string | 执行内容 |
| `filing_budget[].budget_list[].amount_desc` | string | 费用项说明 |

> 预算表（`budget_list`）生成侧**只保留以上 4 个语义字段**；`price`/`amount`/`unit`/`total`/`remark` 等数值与备注字段不纳入，避免 AI 直接引用未经核对的金额数字。

## 生成侧消费字段（fetch_payload.py 裁剪约定）

`fetch_payload.py` 的 `slim_project` 从全量响应中裁剪以下字段进入精简上下文（`contexts.json` 的 `projects[pid].project_detail`），富文本统一剥离 HTML 标签：

| 来源 | 字段 | 说明 |
|------|------|------|
| `info` | `project_name` / `project_intro` / `project_type` / `fundras_filing_code` / `closing_date` / `close_fundraising_time` | 基础信息 |
| `info` | `project_first_name` / `project_second_name` | 项目一级 / 二级分类名称 |
| `info` | `fundras_object_first_name` / `fundras_object_second_name` | 资助对象一级 / 二级分类名称 |
| `detail` | `project_backdrop_title` / `project_backdrop` | 项目背景（剥离 HTML） |
| `loveStory` | `love_story_list`（`story_name` / `story_intro` / `story_summary`） | 爱心故事（剥离 HTML） |
| `donate` | `fundras_cycle_start_time` / `fundras_cycle_end_time` | 开始 / 结束筹款时间 |
| `donate` | `beneficiaries` | 受益对象 |
| `donate` | `assisted_materials` / `assisted_materials_unit` | 资助物资（公益单位）/ 资助量词 |
| `filing_budget` | `filing_budget.fundras_target` / `filing_budget.budget_list` | **仅取 `is_valid=1` 的生效条目**：筹款目标（元）+ 预算表（仅费用项一/二级名称、执行内容、费用项说明 4 个字段） |
| `executorSite` | `executor_site` | 执行地列表，仅保留 `province_name`/`city_name`/`area_name` 三个名称字段，按省/市/区去重（编码不写入，避免 AI 二次解析） |

## 注意事项

1. `project_no` 为项目编码，与 `OrgCommentItem.project_id` 对应
2. 返回字段较多，AI 生成时只消费上表列出的裁剪字段，其余字段（图片/视频/联系人/执行方/项目预算/资助档位等）不进入精简上下文
3. 项目不存在时返回空 Info，需降级处理
4. `executorSite` 的省市区名称（`province_name`/`city_name`/`area_name`）由服务端 `GetProjectDetailForSkill` 统一回填；名称缺失的条目生成侧直接跳过，不输出编码
