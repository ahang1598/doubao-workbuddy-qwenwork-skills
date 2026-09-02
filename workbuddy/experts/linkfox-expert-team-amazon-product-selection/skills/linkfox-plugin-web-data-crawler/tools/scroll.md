---
{
  "actionCode": "SCROLL",
  "fields": {
    "actionValue": { "type": "string|number", "required": true }
  }
}
---

# SCROLL

滚动页面触发懒加载。

## 参数

| 参数 | 类型 | 必须 | 说明 |
|---|---|---|---|
| `actionValue` | string 或 number | 是 | `"top"` / `"bottom"` / 像素数字如 `500` |

## 示例

```json
{ "actionCode": "SCROLL", "actionValue": 500, "tabKey": "tabKey666" }
```
