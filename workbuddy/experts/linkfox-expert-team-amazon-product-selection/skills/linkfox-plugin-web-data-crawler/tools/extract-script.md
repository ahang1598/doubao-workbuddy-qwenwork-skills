---
{
  "actionCode": "EXTRACT_SCRIPT",
  "fields": {
    "extractField": { "type": "string", "required": true },
    "pattern": { "type": "string", "required": true },
    "keyword": { "type": "string", "required": false },
    "group": { "type": "number", "required": false },
    "flags": { "type": "string", "required": false }
  }
}
---

# EXTRACT_SCRIPT

扫描 `<script>` 标签文本，用正则提取嵌入在 JS 源码中的数据（如 `colorImages`、JSON-LD）。DOM 属性无法表达的走此 action。

## 参数

| 参数 | 类型 | 必须 | 说明 |
|---|---|---|---|
| `extractField` | string | 是 | 返回数据的 key |
| `pattern` | string | 是 | 正则表达式，含捕获组 |
| `keyword` | string | 否 | 仅扫描包含此关键词的 `<script>` 标签 |
| `group` | number | 否 | 捕获组编号，默认 `1`（0 = 完整匹配） |
| `flags` | string | 否 | `"s"` — `.` 匹配换行；`"g"` — 全部匹配。可组合 `"sg"` |
| `tabKey` | string | 否 | 标签页标识符 |
| `allowFailure` | boolean | 否 | 为 `true` 时匹配不到输出 `null` 继续，否则终止 |

## 示例

```json
{ "actionCode": "EXTRACT_SCRIPT", "extractField": "images_raw", "pattern": "\"hiRes\"\\s*:\\s*\"(https?://[^\"]+)\"", "keyword": "colorImages", "group": 1, "flags": "g", "tabKey": "tabKey666", "allowFailure": true }
```
