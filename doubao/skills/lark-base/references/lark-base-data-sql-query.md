# +data-sql-query：只读 SQL 查询

本参考只描述 SQL 命令的调用、返回和语法契约。业务口径与验收由分析流程控制；本参考不另设重试预算或授权回退。

## 1. 调用与参数

```bash
# SQL 写进文件用 @file 传（免 shell 转义）；很短且不含单引号的可以直接 --sql '...'；--sql - 从 stdin 读
lark-cli base +data-sql-query --base-token <base_token> --language zh --sql @query.sql
lark-cli base +data-sql-query --base-token <base_token> --language zh --sql 'SELECT "订单号", "金额" FROM "订单" LIMIT 10'
```

| 参数 | 含义 |
| --- | --- |
| `--base-token` | 可信 Base token；一次只查一个 Base |
| `--language` | `zh` / `en` / `ja`，报错文案的语言 |
| `--sql` | 一条只读 `SELECT` / `WITH ... SELECT`；`@文件路径` 从文件读，`-` 从 stdin 读 |
| `--timeout-ms` | 可选，只控制 SQL 执行阶段的超时（毫秒），不是整个 OpenAPI 请求的总超时；非正数等同于不指定 |

**权限**：SQL 查询需要 `base:record:read`。参数细节以当前命令 `--help` 为准。

## 2. 返回与错误

返回字段：

- `data.columns`：结果列名，按字母序排列，不是 SELECT 顺序。
- `data.rows`：每行是「列名 → 值」的映射，按列名取值；同名列会互相覆盖，表达式列要起别名。
- `data.row_count`：本次 SQL 的结果总行数，截断前计数，不等于源记录数或业务主体数；分组查询数的是结果组，带 `LIMIT` 的查询也只描述该 SQL 范围。业务计数读取显式 `COUNT(*)` / `COUNT(DISTINCT 业务键)` 的结果列，不能直接用 `row_count` 替代。
- `data.truncated`：结果超过行上限（默认 2000）时为 `true`，`rows` 只含前面的行。按所需结果在 SQL 里聚合 / 加过滤，或 `ORDER BY "记录 ID" LIMIT 2000 OFFSET n` 翻页；处理截断不能改变原问题范围。

| 返回 | 核验与处理 |
| --- | --- |
| `ok=true` 且 `data.truncated=false` | 核对 `columns` / `rows` / `row_count`，再检查数据源、范围、粒度、连接与指标是否符合问题；接口成功本身不证明业务口径正确 |
| `ok=false` 且 `data.truncated=true` | 部分结果只作诊断；按上面 `data.truncated` 的处理改成云端聚合、加过滤或翻页，在不改变问题范围的前提下补全结果 |
| stderr 返回普通失败 | 读取实际 `error.message`；带 `建议：` 的是编译器拒绝，据此定位问题，不原样重发；没有具体原因时先检查是否只用了本参考第 3 节的写法。修正、重试或回退遵循分析流程的有界恢复策略 |
| 字段缺失、结构异常或完整性无法确认 | 不能据此给出全局结论，不能把失败、缺失或截断当作 0 |

`truncated=false` 只说明本次查询返回未被截断，不证明 SQL 覆盖了完整业务范围。`LIMIT` 可以表达用户要求的 TopN，但不能把全量问题改为前 N 行；有效查询返回空集可以如实报告“无符合条件的数据”，不同于执行失败。

## 3. 支持的语法与函数

标准 PostgreSQL 语法，单条只读查询。函数只用下表列出的，表里没有的视为不支持；被拒时按 `error.message` 里的 `建议：` 改写。当前下游尚未实现 `DECIMAL` / `NUMERIC` 精确十进制类型；不能因采用 PostgreSQL 语法就假定具备 PostgreSQL 的 numeric 语义。`DOUBLE PRECISION` 聚合和舍入可能有精度误差，`ROUND` 或类型转换不构成精度修复。普通数值分析仍使用 SQL；仅满足 [数值精度与本地复算](lark-base-analysis-sql.md#数值精度与本地复算) 的触发条件时才读取原始记录复算，展示小数位要求本身不触发该例外。

字段类型只有 5 种：`TEXT`、`DOUBLE PRECISION`、`BOOLEAN`、`TIMESTAMP`、`TEXT[]`。

| 类别 | 写法 |
| --- | --- |
| 查询结构 | JOIN 只用 `INNER` / `LEFT` / `RIGHT` / `CROSS JOIN ... ON`；集合运算只用 `UNION` / `UNION ALL`；CTE 不递归 |
| 子查询 | 非相关子查询随便用（FROM 派生表、标量、`IN` / `EXISTS`）；相关子查询只支持单个等值键的 `IN` / `EXISTS` |
| 条件 / 转换 | `CASE`、`COALESCE`、`NULLIF`、`GREATEST` / `LEAST`、`BETWEEN`、`IS [NOT] DISTINCT FROM`、`IN (...)`、`CAST` / `::` |
| 数值 | `+ - * /`、`ABS`、`ROUND`、`CEIL` / `FLOOR`、`MOD` / `%` |
| 文本 | `LIKE` / `ILIKE`、`\|\|` / `CONCAT` / `CONCAT_WS`、`LOWER` / `UPPER`、`TRIM`、`REPLACE`、`LENGTH` |
| 日期 | `'2025-01-01'::timestamp`、`NOW()` / `CURRENT_TIMESTAMP`、`DATE_TRUNC`、`EXTRACT` / `DATE_PART`、`TO_CHAR`、`± INTERVAL`、`EXTRACT(EPOCH FROM (a - b))` |
| 数组 | `@>` / `<@` / `&&`、`CARDINALITY` / `ARRAY_LENGTH`、下标 `arr[1]`、`ARRAY_TO_STRING`、`ARRAY[...]`、`UNNEST`（含 `WITH ORDINALITY`） |
| 聚合 | `COUNT` / `COUNT(DISTINCT)`、`SUM` / `AVG` / `MIN` / `MAX`、`FILTER (WHERE ...)`、`ANY_VALUE`、`VAR_POP` / `VAR_SAMP`、`ARRAY_AGG` |
| 窗口 | `ROW_NUMBER` / `RANK` / `DENSE_RANK`、`LAG` / `LEAD`、`SUM` / `AVG` / `MIN` / `MAX` / `COUNT ... OVER (PARTITION BY ...)`、命名 `WINDOW` |

## 4. 示例

示例基于这段 DDL 节选（字段和 COMMENT 形态与真实返回一致），全部只用第 3 节的写法：

```sql
CREATE TABLE "订单" (
  "记录 ID" TEXT,
  "订单号" TEXT,
  "客户" TEXT[],
  "状态" TEXT,
  "金额" DOUBLE PRECISION,
  "下单日期" TIMESTAMP,
  "负责人" TEXT,
  "负责人 ID" TEXT,
  "标签" TEXT[],
  PRIMARY KEY ("记录 ID"),
  UNIQUE ("订单号")
);
COMMENT ON COLUMN "订单"."客户" IS '存放的是关联记录 ID，其关联到表 "客户" 的 "记录 ID" 字段';
COMMENT ON COLUMN "订单"."状态" IS '存储选项名称（待付款、已付款、已取消）';
COMMENT ON COLUMN "订单"."负责人 ID" IS '存放的是用户 user_id';

CREATE TABLE "客户" (
  "记录 ID" TEXT,
  "客户名" TEXT,
  "行业" TEXT,
  PRIMARY KEY ("记录 ID")
);
```

**关联字段 JOIN**（关联字段是记录 ID 数组，先 `UNNEST` 再对目标表的 `"记录 ID"`）— 各行业客户的已付款订单数和金额：

此例假定每笔已付款订单恰好关联一个可匹配客户，且客户记录 ID 唯一；执行前应有约束或查询证据支持，否则先处理关联覆盖与归属口径。

```sql
WITH "订单客户" AS (
  SELECT o."记录 ID" AS "订单记录", o."金额", c."客户ID"
  FROM "订单" AS o, UNNEST(o."客户") AS c("客户ID")
  WHERE o."状态" = '已付款'
)
SELECT k."行业", COUNT(DISTINCT oc."订单记录") AS "订单数", SUM(oc."金额") AS "金额"
FROM "订单客户" AS oc
JOIN "客户" AS k ON k."记录 ID" = oc."客户ID"
GROUP BY k."行业"
ORDER BY "金额" DESC;
```

一个订单关联多个客户时，先明确按唯一归属、按权重分摊，还是允许多组重复归属；口径未定不能直接套用此例。`COUNT(DISTINCT 订单)` 只保护组内订单数，不保护金额，也不保证跨组订单数可相加；仅按订单去重不能解决订单跨行业的金额归属。允许重复归属时须明示各组不可直接相加为总体。

**人员字段**（展示列存姓名，`"<字段> ID"` 伴生列存 user_id）：按人统计以 user_id 分组，同名不同 ID 分开；姓名仅作展示，不决定分组。

```sql
SELECT "负责人 ID", ANY_VALUE("负责人") AS "负责人",
       COUNT(*) AS "订单数", SUM("金额") AS "金额"
FROM "订单" GROUP BY "负责人 ID" ORDER BY "金额" DESC;

SELECT "订单号", "金额" FROM "订单" WHERE "负责人 ID" = '<user_id>';
```

**多选字段**（`TEXT[]`）— 打了 VIP 标签的订单；各标签的订单数：

```sql
SELECT "订单号", "标签" FROM "订单" WHERE "标签" @> ARRAY['VIP'];

SELECT u."标签", COUNT(*) AS "订单数"
FROM "订单" AS o, UNNEST(o."标签") AS u("标签")
GROUP BY u."标签" ORDER BY "订单数" DESC;
```

**月趋势 + 环比**（`TO_CHAR` 分桶、时间常量显式转型、常量偏移的 `LAG`）— 2025 年每月已付款金额及环比：

```sql
WITH "月度" AS (
  SELECT TO_CHAR("下单日期", 'YYYY-MM') AS "月份", SUM("金额") AS "金额"
  FROM "订单"
  WHERE "状态" = '已付款'
    AND "下单日期" >= '2025-01-01'::timestamp AND "下单日期" < '2026-01-01'::timestamp
  GROUP BY 1
)
SELECT "月份", "金额",
       LAG("金额", 1, 0) OVER (ORDER BY "月份") AS "上月金额",
       ROUND(("金额" - LAG("金额", 1, 0) OVER (ORDER BY "月份")) * 100.0
             / NULLIF(LAG("金额", 1, 0) OVER (ORDER BY "月份"), 0), 2) AS "环比%"
FROM "月度"
ORDER BY "月份";
```
