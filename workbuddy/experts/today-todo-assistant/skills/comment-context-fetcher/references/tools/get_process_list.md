# get_process_list — 项目进展列表

> **所属层级**: 第2层（依赖 project_id）
> **使用场景**: project 类型留言的信息来源补充（项目信息 + 最近 5 条进展）
> **关联工具**: 前置 [`get_project_detail`](./get_project_detail.md)（项目详情，并行拉取）
> **最后更新**: 2026-08-14
> **接口**: 工具名 `get_process_list` · 接口名 `GetProcessList` · 来源 `proc_manage.proto`
> **oapi 路径**: `/api/proc_manage/GetProcessList`
> **x1**: ❌ 不带 `Gy-H-Test-Env-Key: x1`

## 概述

获取指定项目下的进展列表。每一条进展记录了项目的阶段性执行情况，包含标题、摘要、正文、执行数据等。**仅用于 project 类型留言**：产品要求项目评论的 AI 回复信息来源 = 项目信息 + 最近 5 条进展（最多 5 条；没有进展则只用项目信息）。同一 `project_id` 单次 run 内只拉取一次（多个 project 评论属同一项目时去重后共享结果，并发请求；不做跨 run 磁盘缓存）。

## 触发条件

当留言 `object_type = "project"` 时，在拉取 `get_project_detail` 的同时调用本工具拉取该项目最近 5 条进展。

## 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `project_id` | uint32 | **是** | 项目ID（取 `OrgCommentItem.object_id`，数字字符串需转为 uint32） |
| `index` | uint32 | 是 | 页码（从1开始）。**固定 1** |
| `size` | uint32 | 是 | 每页条数。**固定 5**（最多 5 条） |
| `platform_version` | uint32 | 是 | 平台版本：**3**=新版进展。**固定 3** |
| `status` | ProcessStatus | 是 | 进展审核状态筛选。**固定 1**（审核通过） |
| `publish_status` | ProcessPublishStatus | 是 | 发布状态筛选。**固定 -1**（全部发布状态） |

> 留言回复场景的典型调用（**除 `project_id` 外全部固定**，不传其他可选参数）：`project_id` + `index=1` + `size=5` + `platform_version=3` + `status=1` + `publish_status=-1`

## 返回字段

### 分页信息

| 字段 | 类型 | 说明 |
|------|------|------|
| `total` | uint32 | 符合条件的进展总数 |
| `list` | ProcessInfo[] | 当前页进展列表（≤5 条，无进展时为空数组） |

### ProcessInfo — 进展条目

#### 标识

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | uint32 | 进展ID。引用该条进展事实时记录为 `sources` 的 `source_id` |
| `project_id` | uint32 | 所属项目ID |
| `scenes_type` | uint32 | 场景类型：1=母项目、2=子计划、3=合作活动 |
| `draft_id` | uint32 | 草稿ID。0表示非草稿 |

#### 内容

| 字段 | 类型 | 说明 |
|------|------|------|
| `content_title` | string | 进展标题。快速了解进展内容主题 |
| `desc` | string | 进展摘要。进展内容的简短概述 |
| `content` | string | 进展正文（**HTML格式**）。包含完整的进展详情文本。注意需要处理HTML标签 |
| `concrete_info` | string | **结构化执行数据（JSON字符串）**。可解析提取执行指标（受益人数、执行金额、物资数量等）。字段内容因进展类型和模板而异 |

#### 媒体

| 字段 | 类型 | 说明 |
|------|------|------|
| `image_url` | string | 图片列表（逗号分隔的CDN地址） |
| `video_url` | string | 视频地址（转码后CDN地址） |
| `video_snapshot` | string | 视频截图CDN地址 |

#### 时间

| 字段 | 类型 | 说明 |
|------|------|------|
| `begin_time` | uint32 | 进展执行开始时间（Unix时间戳） |
| `end_time` | uint32 | 进展执行结束时间（Unix时间戳） |
| `publish_time` | uint32 | 发布时间（Unix时间戳）。**关键字段**，引用进展事实时记录为 `sources` 的 `updated_at` |
| `created_at` | uint32 | 提交时间（Unix时间戳） |
| `updated_at` | uint32 | 更新时间（Unix时间戳） |

#### 状态与类型

| 字段 | 类型 | 说明 |
|------|------|------|
| `status` | ProcessStatus | 进展审核状态（枚举值） |
| `type` | uint32 | 进展类型：0=普通进展、7=具象化进展 |

## 调用示例

```
输入:
  project_id=224328
  index=1
  size=5
  platform_version=3
  status=1
  publish_status=-1

返回:
  total: 42
  list:
    - id: 1001
      content_title: "2026年7月进展报告"
      desc: "本月服务乡村儿童500人次..."
      publish_time: 1786000000
      concrete_info: "{\"beneficiaries\":500}"
    - id: 1002
      content_title: "2026年6月进展报告"
      desc: "完成3所乡村小学素质教育课程..."
      publish_time: 1783400000
```

## 分页策略

- 留言回复场景只关注**最近 5 条**进展，**固定 `index=1, size=5`，不翻页**
- `status=1` + `publish_status=-1` 确保取审核通过的进展，不过滤发布状态

## 注意事项

1. `project_id` 是**必填参数**，取 `OrgCommentItem.object_id`（数字字符串需转为 uint32）
2. `list` 为空数组时（项目无进展），project 类型上下文仅含 `project_detail`，按「仅项目信息」单来源生成回复
3. `content` 为 **HTML 格式**，展示/提取文本时需处理 HTML 标签
4. `concrete_info` 为 **JSON 字符串**，可尝试解析提取结构化执行数据。解析失败不阻断流程
5. 时间字段（`publish_time`、`created_at` 等）为 Unix 时间戳（秒），需转换为可读日期格式
6. 同一 `project_id` 单次 run 内只调用一次，以 `process_list:<project_id>` 为键去重（仅单次 run 内有效，去重后并发请求；不做跨 run 磁盘缓存，每次 run 实时拉取）

## 后续下钻

- 单条进展的全文不在此下钻（process 类型留言走 [`get_process_detail`](./get_process_detail.md)，与 project 类型链路独立）
