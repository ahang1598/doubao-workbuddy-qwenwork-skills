---
{
  "actionCode": "INPUT",
  "fields": {
    "selector": { "type": "string|string[]", "required": true },
    "text": { "type": "string", "required": true }
  }
}
---

# INPUT

在输入框中输入文本。

## 参数

| 参数 | 类型 | 必须 | 说明 |
|---|---|---|---|
| `selector` | `string` 或 `string[]` | 是 | 数组时依次尝试回退 |
| `text` | string | 是 | 要输入的文本内容 |

## 示例

```json
{ "actionCode": "INPUT", "selector": "#contextualIngressPtLabel_deliveryShortLine input", "text": "10001", "tabKey": "tabKey666" }
```
