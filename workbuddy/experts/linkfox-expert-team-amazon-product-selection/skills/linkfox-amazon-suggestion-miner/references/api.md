# Amazon 搜索建议词挖掘 API

- **端点**：`GET https://www.{domain}/suggestions`（Amazon 公开自动补全 API，非 LinkFox 网关）
- **无需登录/鉴权**：session-id 随机生成即可

## 参数表

### CLI 参数

| 参数 | 类型 | 必填 | 默认 | 枚举/范围 | 说明 |
|------|------|------|------|-----------|------|
| `--seed` | str | 是 | - | - | 种子词（如 "fan"） |
| `--mode` | str | 否 | expand | expand/az/reverse/deep | 挖掘模式 |
| `--rounds` | int | 否 | 2 | 1-5 | expand 模式扩展轮次 |
| `--depth` | int | 否 | 2 | 1-5 | deep 模式递归深度 |
| `--top-n` | int | 否 | 5(deep)/100(reverse) | - | 每轮取Top-N前缀/高频词 |
| `--market` | str | 否 | US | 23个站点简码 | 单站点 |
| `--markets` | str | 否 | - | 逗号分隔或ALL | 多站点批量 |
| `--auto-translate` | flag | 否 | false | - | 自动翻译种子词 |
| `--translations` | str | 否 | - | DE:词,JP:词 | 手动指定翻译 |
| `--delay` | float | 否 | 0.3 | 0.1-5.0 | 请求间隔秒数 |
| `--verbose` | flag | 否 | false | - | 详细输出 |
| `--xlsx` | str | 否 | - | 路径 | Excel输出路径 |
| `--csv` | str | 否 | - | 路径 | CSV输出路径 |
| `--output` | str | 否 | - | 路径 | JSON输出路径 |
| `--db` | str | 否 | - | 路径 | SQLite数据库路径 |

### 支持站点（23个）

US, CA, MX, DE, FR, IT, ES, IN, NL, AE, SA, PL, BE, EG, IE, ZA, SE, JP, UK, AU, BR, SG, TR

## 响应结构

### JSON 顶层

```json
{
  "seed": "fan",
  "mode": "expand",
  "market": "US",
  "total_keywords": 127,
  "total_widget_items": 15,
  "keywords": [...],
  "widget_items": [...],
  "stats": {...}
}
```

### keywords 数组元素

| 字段 | 类型 | 说明 |
|------|------|------|
| keyword | str | 搜索建议词 |
| source | str | autocomplete/az_scan/reverse/widget |
| prefix | str | 触发该词的前缀 |
| rank | int | 在建议列表中的排名 |
| sugg_type | str | KeywordSuggestion/WidgetSuggestion |
| candidate_source | str | local/lucene |
| depth | int | 递归深度（deep模式） |

### Excel (xlsx) Sheet 结构

| Sheet | 内容 |
|-------|------|
| 摘要 | 种子词、模式、站点、关键词数、Widget数、生成时间 |
| 关键词 | keyword/source/prefix/rank/sugg_type/candidate_source/depth |
| Widget分类词 | 分类标签/完整关键词/Widget标题/图片URL/搜索URL |
| 问句式关键词 | keyword/source/prefix/rank（如有） |

## 错误处理

- API 请求失败：返回空 keywords 列表，不崩栈
- 5个反爬站点（UK/AU/BR/SG/TR）：verbose 模式下提示需浏览器辅助
- 翻译失败：保留英文原词保底
- openpyxl 缺失：提示 `pip install openpyxl`

## 计费

直接调 Amazon 公开 API，不通过 LinkFox 网关，不计费。
