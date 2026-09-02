---
{
  "actionCode": "CLOSE_TAB",
  "fields": {
    "tabKey": { "type": "string", "required": true }
  }
}
---

# CLOSE_TAB

关闭指定标签页。

## 参数

| 参数 | 类型 | 必须 | 说明 |
|---|---|---|---|
| `tabKey` | string | 是 | 要关闭的标签页标识符 |

## 示例

```json
{ "actionCode": "CLOSE_TAB", "tabKey": "tabKey666" }
```
