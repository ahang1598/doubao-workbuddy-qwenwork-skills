---
name: comment-todo-statistics
description: "获取待办统计（Leader 待办卡片）。查询机构 3.0 平台待回复留言总数与高风险数，按固定样式返回待办卡片 JSON：title=留言处理，subtitle=有XX条留言待处理, 其中YY条高风险留言, 我来协助你处理。待处理数为 0 时返回空卡片 {title:'', subtitle:''}。"
---

# 获取待办统计（Leader 待办卡片）

## 概述

本 Skill 为 Leader 提供"待办统计"能力：汇总机构当前待回复留言总量与高风险数量，产出一张**固定样式**的待办卡片 JSON，供 Leader 的待办视图直接消费。

**核心功能**：
- 查询机构 3.0 平台待回复留言的 `total` / `risk_total`
- 按固定模板拼接 `title` / `subtitle`
- 待处理数为 0 时返回空卡片

**关键约束**：
- 输出**严格固定**为 `{title, subtitle}` 两个字段，不得增减字段
- 待处理数（`total`）为 0 时，`title` 与 `subtitle` 均为空串
- `total` / `risk_total` 取自 `get_org_upreplied_comments` 返回值，口径与留言回复主流程一致（详见 `comment-fetcher`）

## 触发场景

Leader 调用本专家请求"待办统计 / 留言待办统计"时加载本 Skill（命名空间 `comment-assistant@my-experts:comment-todo-statistics`）。

## 输入格式

无强制输入。查询参数沿用留言查询惯例：`page=0, size=30`（size 固定 30；统计只读 `total` / `risk_total` 汇总值，与分页大小无关）。

## 工作流程

1. **查询统计**：调用 MCP 工具 `get_org_upreplied_comments`（gongyi-open-mcp），入参 `page=0, size=30`，读取返回的 `total` 与 `risk_total`。
2. **分支组装**：
   - 若 `total > 0`：
     ```json
     {
       "title": "留言处理",
       "subtitle": "有{t}条留言待处理, 其中{r}条高风险留言, 我来协助你处理"
     }
     ```
     其中 `{t}` = `total`，`{r}` = `risk_total`（均为数字，直接替换，不加引号、不加单位后缀）。
   - 若 `total == 0`：
     ```json
     {
       "title": "",
       "subtitle": ""
     }
     ```
3. **返回**：将上一步得到的 JSON 作为本能力的结构化返回，交给 Leader 待办视图消费。

## 输出格式

```json
{
  "title": "留言处理",
  "subtitle": "有36条留言待处理, 其中2条高风险留言, 我来协助你处理"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `title` | string | 固定为 `留言处理`；待处理数为 0 时为空串 |
| `subtitle` | string | 固定模板：`有{t}条留言待处理, 其中{r}条高风险留言, 我来协助你处理`；待处理数为 0 时为空串 |

**⛔ 禁止**：
- 输出 `title` / `subtitle` 之外的字段（如 `total` / `risk_total` / `code` / `msg`）
- 在 subtitle 中增删字词或改写模板（逗号、措辞必须一字不差）
- 将 `{t}` / `{r}` 替换为非数字内容（如"若干""少量"）
- 待处理数为 0 时仍输出非空 `title` / `subtitle`

## 异常处理

| 场景 | 处理方式 |
|------|---------|
| MCP 查询失败 | 视作无法获取统计，返回空卡片 `{title:'', subtitle:''}`（与"无待办"同态，避免 Leader 误判为有数据） |
| `total` 缺失/非法 | 按 0 处理，返回空卡片 |

## 依赖

- MCP Server: `gongyi-open-mcp`
- MCP Tool: `get_org_upreplied_comments`
