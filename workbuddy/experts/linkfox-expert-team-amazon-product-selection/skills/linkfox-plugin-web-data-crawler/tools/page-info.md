---
{
  "actionCode": "GET_PAGE_INFO",
  "fields": {
    "extractField": { "type": "string", "required": false }
  }
}
---

# GET_PAGE_INFO

页面状态诊断，返回 URL、标题、验证码检测。Part 2 第一步。

## 参数

| 参数 | 类型 | 必须 | 说明 |
|---|---|---|---|
| `extractField` | string | 否 | 返回数据的 key |

## 示例

```json
{ "actionCode": "GET_PAGE_INFO", "extractField": "page", "tabKey": "tabKey666" }
```
