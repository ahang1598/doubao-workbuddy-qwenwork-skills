# 字段类型参考

AI 表格支持的同步的数据源字段类型枚举及对应的 `property` 配置。

本文档配合 `references/backend-developer-guide.md` 使用。后端 `/api/sheet_meta` 接口返回的每个字段，其 `type` 和 `property` 必须符合本文档中定义的类型枚举和配置格式。

## 支持的字段类型

| 字段类型 | `type` 值 | `property` 配置 |
|---------|-----------|----------------|
| 文本 | `text` | 无（`null`） |
| 数字 | `number` | 见下方 formatter 枚举 |
| 单选 | `singleSelect` | 见下方 choices 配置 |
| 多选 | `multipleSelect` | 同单选 |
| 日期 | `date` | 见下方 formatter 枚举 |
| 链接 | `url` | 无（`null`） |

## 数字类型 formatter 枚举

```json
{
  "formatter": "INT"
}
```

| formatter 值 | 显示效果 |
|-------------|---------|
| `INT` | 整数（1234） |
| `FLOAT_1` | 保留1位小数（1234.5） |
| `FLOAT_2` | 保留2位小数（1234.56） |
| `FLOAT_3` | 保留3位小数 |
| `FLOAT_4` | 保留4位小数 |
| `THOUSAND` | 千分位（1,234） |
| `THOUSAND_FLOAT` | 千分位含小数（1,234.56） |
| `PRESENT` | 百分比（12%） |
| `PRESENT_FLOAT` | 百分比含小数（12.34%） |
| `CNY` | 人民币（¥1,234） |
| `CNY_FLOAT` | 人民币含小数 |
| `HKD` | 港元 |
| `HKD_FLOAT` | 港元含小数 |
| `USD` | 美元（$1,234） |
| `USD_FLOAT` | 美元含小数 |
| `EUR` | 欧元 |
| `EUR_FLOAT` | 欧元含小数 |
| `JPY` | 日元 |
| `JPY_FLOAT` | 日元含小数 |

## 日期类型 formatter 枚举

```json
{
  "formatter": "YYYY-MM-DD"
}
```

| formatter 值 | 显示效果 |
|-------------|---------|
| `YYYY-MM-DD` | 2023-12-31 |
| `YYYY-MM-DD HH:mm` | 2023-12-31 09:00 |
| `YYYY/MM/DD` | 2023/12/31 |
| `YYYY/MM/DD HH:mm` | 2023/12/31 09:00 |

> ⚠️ 日期字段的值必须传毫秒时间戳（long），不是日期字符串。

## 单选/多选 choices 配置

```json
{
  "choices": [
    { "name": "选项A" },
    { "name": "选项B" },
    { "name": "选项C" }
  ]
}
```

## 数据库类型映射建议

| 数据库类型 | 推荐 AI 表格类型 | 推荐 property |
|-----------|----------------|--------------|
| `INT` / `INTEGER` / `BIGINT` | `number` | `{"formatter":"INT"}` |
| `DECIMAL` / `DOUBLE` / `FLOAT` | `number` | `{"formatter":"FLOAT_2"}` |
| `VARCHAR` / `TEXT` / `CHAR` | `text` | 无 |
| `DATE` | `date` | `{"formatter":"YYYY-MM-DD"}` |
| `DATETIME` / `TIMESTAMP` | `date` | `{"formatter":"YYYY-MM-DD HH:mm"}` |
| `ENUM` | `singleSelect` | `{"choices":[...]}` |
| `BOOLEAN` / `TINYINT(1)` | `singleSelect` | `{"choices":[{"name":"true"},{"name":"false"}]}` |
| `URL` / 链接字段 | `url` | 无 |


