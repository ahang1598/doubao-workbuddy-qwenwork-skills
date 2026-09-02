# Workflow DSL — Tool Reference

本文档是 workflow DSL 中所有 `actionCode` 的文档索引。每个 actionCode 对应一个独立文档。

## Action Code 列表

| actionCode | 文档 | 用途 |
|---|---|---|
| `OPEN_TAB` | [open-tab.md](open-tab.md) | 打开浏览器标签页 |
| `CLOSE_TAB` | [close-tab.md](close-tab.md) | 关闭标签页 |
| `WAIT` | [wait.md](wait.md) | 等待元素/固定时长 |
| `CLICK` | [click.md](click.md) | 点击元素 |
| `INPUT` | [input.md](input.md) | 输入文本 |
| `FIND_SELECTOR` | [find-selector.md](find-selector.md) | 搜索 CSS 选择器 |
| `LOOP` | [loop.md](loop.md) | 批量迭代 |
| `IF` | [if.md](if.md) | 条件分支 |
| `EXTRACT` | [extract.md](extract.md) | DOM 提取 |
| `EXTRACT_SCRIPT` | [extract-script.md](extract-script.md) | script 标签正则提取 |
| `SCROLL` | [scroll.md](scroll.md) | 滚动页面 |
| `START_SUB_WORKFLOW` | [start-sub-workflow.md](start-sub-workflow.md) | AI 弹性子任务 |
| `GET_PAGE_INFO` | [page-info.md](page-info.md) | 页面状态诊断 |
| `GET_DOM` | [dom-dump.md](dom-dump.md) | DOM 快照 |
| `VERIFY_SELECTOR` | [verify-selector.md](verify-selector.md) | 验证选择器 |

## 通用机制

| 主题 | 文档 |
|---|---|
| Selector Fallback | [selector-fallback.md](selector-fallback.md) |
| `allowFailure` | 所有 step 可用。为 `true` 时失败不终止，输出原因后继续 |
| `onFailure` | EXTRACT/LOOP 可用。`{ "actionCode": "FIND_SELECTOR", "field": "...", "thenRetry": true }` |

## 通用字段（所有 step 适用）

| 字段 | 类型 | 必须 | 说明 |
|---|---|---|---|
| `actionCode` | string | 是 | 操作类型 |
| `actionDescription` | string | 否 | 步骤描述，仅用于日志 |
| `tabKey` | string | 条件 | 标签页标识符。LOOP/IF/EXTRACT_SCRIPT 不需要，其余必填 |
| `allowFailure` | boolean | 否 | 失败时是否继续 |
| `extractField` | string | 否 | 返回数据的 key |

## 顶层结构

```json
{
  "workflowName": "字符串，必填",
  "steps": [ <step>, ... ]
}
```

每个 `tools/<action>.md` 顶部 `---` 区块是 `validate_workflow.py` 的校验源，修改 action 字段时同步更新即可。

## 模板约定

各站点工作流模板在 `sites/<site>/base-full.json`。固定 `tabKey` 值 `"tabKey666"`，URL 由 `run_crawl.py` 自动替换。品类字段在 `sites/<site>/categories/fields/<category>.json`，自动注入到 CLOSE_TAB 之前。

## 校验

```bash
python scripts/validate_workflow.py <json路径>
```
