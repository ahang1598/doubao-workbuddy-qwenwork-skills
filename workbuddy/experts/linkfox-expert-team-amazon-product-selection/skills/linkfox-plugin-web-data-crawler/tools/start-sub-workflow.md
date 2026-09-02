---
{
  "actionCode": "START_SUB_WORKFLOW",
  "fields": {
    "actionDescription": { "type": "string", "required": true }
  }
}
---

# START_SUB_WORKFLOW

向浏览器端 AI 发自然语言指令，处理非确定性交互（cookie 弹窗、区域选择等）。

## 参数

| 参数 | 类型 | 必须 | 说明 |
|---|---|---|---|
| `actionDescription` | string | 是 | 自然语言指令 |

## 示例

```json
{ "actionCode": "START_SUB_WORKFLOW", "actionDescription": "关闭 cookie 同意弹窗（如果存在）", "tabKey": "tabKey666" }
```
