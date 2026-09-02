---
{
  "actionCode": "LOOP",
  "fields": {
    "condition": { "type": "string|array", "required": false },
    "loopTarget": { "type": "string|array", "required": false },
    "steps": { "type": "array", "required": true },
    "loopItemKey": { "type": "string", "required": false },
    "start": { "type": "number", "required": false },
    "end": { "type": "number", "required": false },
    "extractField": { "type": "string", "required": false },
    "breakCondition": { "type": "string", "required": false },
    "onFailure": {
      "type": "object",
      "required": false,
      "schema": {
        "actionCode": { "type": "string", "required": true, "const": "FIND_SELECTOR" },
        "field": { "type": "string", "required": false },
        "hint": { "type": "string", "required": false },
        "thenRetry": { "type": "boolean", "required": false }
      }
    }
  },
  "requires_one_of": [["condition", "loopTarget"]],
  "mutually_exclusive": [["condition", "loopTarget"]]
}
---

# LOOP

迭代执行子步骤。`condition`/`loopTarget` 解析为数组则遍历元素，解析为数字 N 则执行 N 次。

## 参数

| 参数 | 类型 | 必须 | 说明 |
|---|---|---|---|
| `condition` | template 表达式 | 条件 | 迭代目标。与 `loopTarget` 二选一 |
| `loopTarget` | template 表达式 | 条件 | 纯数组形式，如 `"{{result.variantAsins}}"`。与 `condition` 二选一 |
| `steps` | `ScrapeStep[]` | 是 | 子步骤数组 |
| `loopItemKey` | string | 否 | 当前迭代元素的模板变量名，默认 `"loopElement"` |
| `start` | number | 否 | 起始索引（0-based），默认 0 |
| `end` | number | 否 | 结束索引（0-based，不包含），默认 `arr.length` |
| `extractField` | string | 否 | LOOP 整体结果 key，不设置时结果丢弃 |
| `breakCondition` | string | 否 | 提前退出表达式（语法同 IF），如 `"exists('.no-more')"` |
| `onFailure` | object | 否 | 自愈配置：`{ "actionCode": "FIND_SELECTOR", "field": "...", "thenRetry": true }` |

## 模板变量

子步骤内可用：`{{loopIndex}}`（0-based）、`{{loopElement}}`（当前元素）、`{{loopData}}`（前序迭代累积数组）。

## 结果聚合

- 子步骤有 `extractField` → 以该 key 存入迭代结果对象
- 子步骤无 `extractField` → 浅合并到结果对象
- LOOP 自身有 `extractField` → 整体结果 `flat(Infinity)` 后存入该 key

## 示例

```json
{
  "actionCode": "LOOP",
  "extractField": "product_details",
  "loopTarget": ["#productDetails_expanderSectionTables tr", "#detailBullets_feature_div ul li"],
  "steps": [
    { "actionCode": "EXTRACT", "selector": "{{loopElement}}", "extractType": "list", "tabKey": "tabKey666", "allowFailure": true }
  ]
}
```
