# 数据规范：字段 ID 与行数据 ID

> 这是开发数据源插件时**最容易出错**的部分，必须严格遵守。

## 1. 字段 ID 规范

字段 ID 是 AI 表格识别列的唯一标识，必须满足：

- **唯一性**：每个字段的 ID 不能重复
- **稳定性**：同一个数据源下每次 `/api/sheet_meta` 返回的字段 ID 必须完全一致

**推荐生成方式**：
- 直接使用字段名作为 ID（如 `"id"`、`"username"`）
- 或使用 `字段名_字段类型` 组合（如 `"created_at_date"`）

**禁止使用**：随机数、UUID、时间戳、自增序号

## 2. 行数据 ID 规范

行 ID 是 AI 表格识别每一行数据的唯一标识，必须满足：

- **唯一性**：每行数据的 ID 不能重复
- **稳定性**：同一行数据无论何时获取、在第几页，ID 必须相同

**生成策略**：

| 场景 | 推荐方案 |
|------|---------|
| 数据源有主键 | 直接使用主键值（String 类型） |
| 数据源无主键 | 选取多个稳定字段拼接后取 MD5 哈希 |

**禁止使用**：随机数、时间戳、分页序号（`rowIndex`）

## 3. 数据类型规范

行数据中每个字段的值类型必须与 `/api/sheet_meta` 中声明的字段类型严格对应：

| 字段类型 | 必须返回的值类型 | 示例 |
|---------|----------------|------|
| `number` | 数字（int/long/double） | `25`、`3.14` |
| `date` | 毫秒时间戳（long） | `1703980800000` |
| `text` | 字符串 | `"张三"` |
| `singleSelect` / `multipleSelect` | 选项名称字符串 | `"选项A"` |

### Boolean 字段特别说明

数据库的 `BOOLEAN` / `BIT` / `TINYINT(1)` 类型在 `/api/sheet_meta` 中如果映射为 `singleSelect`，则 `/api/records` 返回时**必须将布尔值转换为字符串**：

| 数据库原始值 | 必须返回的值 |
|------------|------------|
| `true` / `1` | `"true"` |
| `false` / `0` | `"false"` |
| `null` | `null` |

**各数据库 JDBC 返回类型说明**：

| 数据库 | 字段类型 | JDBC 返回 Java 类型 | 处理方式 |
|--------|---------|-------------------|---------|
| MySQL | `BOOLEAN` / `TINYINT(1)` | `Boolean` | `String.valueOf(value)` |
| PostgreSQL | `BOOLEAN` | `Boolean` | `String.valueOf(value)` |
| SQL Server | `BIT` | `Boolean` | `String.valueOf(value)` |
| Oracle | 无原生 BOOLEAN，通常用 `NUMBER(1)` 模拟 | `Integer` | 需手动判断列类型转换 |

## 4. 代码示例

### ✅ 正确示例

```java
// 字段定义：使用字段名作为 ID
Field idField = new Field();
idField.setId("id");               // 字段 ID = 字段名，稳定不变
idField.setName("id");
idField.setType("number");
idField.setProperty("{\"formatter\":\"INT\"}");
idField.setIsPrimary(true);        // 标记主键，前端可自动跳过字段映射步骤

// 行数据：使用主键值作为行 ID
Record record = new Record();
record.setId("123");               // 主键值，String 类型
Map<String, Object> fields = new HashMap<>();
fields.put("id", 123);            // number → 数字
fields.put("name", "张三");        // text → 字符串
fields.put("created_at", 1703980800000L);  // date → 毫秒时间戳
record.setFields(fields);

// 无主键时：多字段拼接取哈希
String combined = name + "_" + email;
String recordId = DigestUtils.md5Hex(combined);
record.setId(recordId);
```

### ❌ 错误示例

```java
// ❌ 字段 ID 使用随机数（每次调用不同）
field.setId("field_" + UUID.randomUUID());

// ❌ 行 ID 使用时间戳（每次调用不同）
record.setId(String.valueOf(System.currentTimeMillis()));

// ❌ 行 ID 使用分页序号（换页后 ID 错乱）
record.setId(String.valueOf(rowIndex));

// ❌ number 类型返回字符串
fields.put("age", "25");           // 应为 25（数字）

// ❌ date 类型返回日期字符串
fields.put("created_at", "2024-01-01");  // 应为毫秒时间戳
```
