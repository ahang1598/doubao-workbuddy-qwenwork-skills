---
{
  "actionCode": "FIND_SELECTOR",
  "fields": {
    "field": { "type": "string", "required": true },
    "hint": { "type": "string", "required": false },
    "extractField": { "type": "string", "required": false }
  }
}
---

# FIND_SELECTOR

在已打开页面上根据字段语义搜索 CSS 选择器。用于 onFailure 自愈或 Part 2 诊断。

## 参数

| 参数 | 类型 | 必须 | 说明 |
|---|---|---|---|
| `field` | string | 是 | 字段语义：`title`/`price`/`rating`/`brand`/`images`/`bullets`/`review_count`/`availability`/`product_details` |
| `hint` | string | 否 | 辅助线索，如 `"pages"`、`"ISBN-10"`、`"aplus module images"` |
| `extractField` | string | 否 | 返回数据的 key |

## 示例

```json
{ "actionCode": "FIND_SELECTOR", "field": "brand", "tabKey": "tabKey666" }
```
