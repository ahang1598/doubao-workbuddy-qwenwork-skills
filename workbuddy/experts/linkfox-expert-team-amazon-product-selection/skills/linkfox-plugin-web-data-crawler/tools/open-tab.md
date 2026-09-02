---
{
  "actionCode": "OPEN_TAB",
  "fields": {
    "tabUrl": { "type": "string", "required": true },
    "tabKey": { "type": "string", "required": true }
  }
}
---

# OPEN_TAB

打开浏览器标签页并导航到指定 URL。

## 参数

| 参数 | 类型 | 必须 | 说明 |
|---|---|---|---|
| `tabUrl` | string | 是 | 目标 URL |
| `tabKey` | string | 是 | 标签页标识符，后续步骤用此值引用。单标签页统一用 `"tabKey666"` |

## 示例

```json
{ "actionCode": "OPEN_TAB", "tabUrl": "https://www.amazon.com/dp/B0CP9YB3Q4", "tabKey": "tabKey666" }
```
