# SQL 结构上下文与只读查询契约

目录：Context 契约；SQL 契约（语法与函数、返回与错误、字段来源、示例、月趋势与环比）

本页只管参数、数据形状、技术限制，不另设口径或回退（归 [Query](../scenes/query.md)）；参数细节以 `--help` 为准。

## +schema-context-get：结构上下文

需要 `base:table:read`：

```bash
lark-cli base +schema-context-get --base-token "<base_token>" --language zh --table-id "<tbl_a>" --table-id "<tbl_b>"
```

| 参数 | 含义 |
| --- | --- |
| `--base-token` | 用 `+url-resolve` 从链接解析；一次一个 Base |
| `--table-id` | 可选、可重复，最多 10 个，只取这些表的 DDL；相关表未知时不传（取整个 Base 后选表），已知时传全相关表 |
| `--language` | zh/en/ja，DDL 注释与报错语言 |

### 返回解读、复用与截断

- 读 `data.content`：每表一段 DDL，列含义看 COMMENT；视图、仪表盘段的 SQL 片段可复用。表名、字段名只用 DDL 里的并加双引号（`"订单"."记录 ID"`），不凭简称或先验猜。
- 用 PRIMARY KEY、UNIQUE、重复值注释、业务粒度区分记录键、实体键、展示属性：记录 ID 唯一不代表不同实体（如多期快照）；实体键不同的同名不合并；名称或少量样例不证明实体身份；未声明 UNIQUE 不证明有重复，无重复提示不证明名称唯一。
- 同任务内 Base、身份、结构未变且相关字段已覆盖就复用 Context；新增数据源、建表、加字段后必须重取。
- 截断时先 +table-list / +field-list 定位候选表，再重复传明确的 --table-id 重取，覆盖所需数据源与关联表，不静默漏表。
- 样例只用来理解字段，不代表值域；状态取值、空值、关联覆盖用只读 SQL 补证据。

## +data-sql-query：只读 SQL 查询

需要 `base:record:read`。SQL 写进允许目录的文件用 `--sql @query.sql`；无单引号的短 SQL 才直接 `--sql '...'`（不在 shell 单引号里用 `\'` 转义）；`--sql -` 读 stdin。CLI 成功后再按 [响应解析协议](shared-cli-invocation.md#响应解析) 解析。

```bash
lark-cli base +data-sql-query --base-token "<base_token>" --language zh --sql @query.sql
```

| 参数 | 含义 |
| --- | --- |
| `--base-token`、`--language` | 同 Context（`--language` 只影响报错语言） |
| `--sql` | 一条只读 `SELECT` / `WITH ... SELECT`，传法见上 |
| `--timeout-ms` | 可选，只控 SQL 执行阶段超时（毫秒），非整个请求总超时；非正数同不传 |

### 支持的语法与函数

标准 PostgreSQL 语法、单条只读查询；只用下表函数，表外视为不支持（被拒处理见 [返回与错误](#返回与错误)）。字段类型只有 TEXT、DOUBLE PRECISION、BOOLEAN、TIMESTAMP、TEXT[]。

未实现 DECIMAL/NUMERIC；DOUBLE PRECISION 聚合与舍入可能有误差，ROUND 或类型转换不是精度修复。精度复算的许可与方法见 [Query](../scenes/query.md#精度与受控回退)、[共享规则](shared-statistics-rules.md#精确十进制复算方法)。

| 类别 | 写法 |
| --- | --- |
| 查询结构 | JOIN 只用 INNER/LEFT/RIGHT/CROSS JOIN ... ON；集合运算只用 UNION/UNION ALL；CTE 不递归 |
| 子查询 | 非相关子查询都可用（FROM 派生表、标量、IN/EXISTS）；相关子查询只支持单个等值键的 IN/EXISTS |
| 条件/转换 | CASE、COALESCE、NULLIF、GREATEST/LEAST、BETWEEN、IS [NOT] DISTINCT FROM、IN (...)、CAST/:: |
| 数值 | + - * /、ABS、ROUND、CEIL/FLOOR、MOD/% |
| 文本 | LIKE/ILIKE、\|\|、CONCAT、CONCAT_WS、LOWER/UPPER、TRIM、REPLACE、LENGTH |
| 日期 | '2025-01-01'::timestamp、NOW()/CURRENT_TIMESTAMP、DATE_TRUNC、EXTRACT/DATE_PART、TO_CHAR、± INTERVAL、EXTRACT(EPOCH FROM (a - b)) |
| 数组 | @>、<@、&&、CARDINALITY/ARRAY_LENGTH、下标 arr[1]、ARRAY_TO_STRING、ARRAY[...]、UNNEST（含 WITH ORDINALITY） |
| 聚合 | COUNT/COUNT(DISTINCT)、SUM/AVG/MIN/MAX、FILTER (WHERE ...)、ANY_VALUE、VAR_POP/VAR_SAMP、ARRAY_AGG |
| 窗口 | ROW_NUMBER/RANK/DENSE_RANK、LAG/LEAD、SUM/AVG/MIN/MAX/COUNT ... OVER (PARTITION BY ...)、命名 WINDOW |

### 返回与错误

- `data.columns` 按字母序（非 SELECT 顺序）；`data.rows` 每行「列名 → 值」，按列名取；同名列互相覆盖，表达式列要起别名。
- `data.row_count` 是本次结果行数（截断前），非源记录数或主体数（分组时数的是组，带 LIMIT 只描述该 SQL）；业务计数读显式 `COUNT(*)` / `COUNT(DISTINCT 业务键)` 列。
- `data.truncated` 超行上限（默认 2000）为 true，`rows` 只含前面的行；在 SQL 里聚合、加过滤，或 `ORDER BY "记录 ID" LIMIT 2000 OFFSET n` 翻页，不改原问题范围。

| 返回 | 处理 |
| --- | --- |
| ok=true 且 data.truncated=false | 核对 columns、rows、row_count；执行成功与结论成立分别验证；未截断不证明覆盖完整业务范围 |
| ok=false 且 data.truncated=true | 部分结果只作诊断，按上条补全 |
| stderr 普通失败 | 读实际 `error.message`；带 `建议：` 是编译器拒绝，据此改写，不原样重发；无具体原因先查是否超出 [支持的语法](#支持的语法与函数)，修正、重试、回退按有界恢复 |
| 字段缺失、结构异常、完整性无法确认 | 不下全局结论；失败、缺失、截断不当 0 |

LIMIT 可表达用户要的 TopN，不能把全量问题改成前 N 行；有效查询返回空集如实报“无符合条件的数据”，区别于执行失败。

### 字段来源与结果列

表达式决定源字段，别名只定列名：取对象姓名写 `t."对象姓名" AS "姓名"`；`t."联系人" AS "姓名"` 值看似合理也取自另一字段。按命名列读 `rows` 并保留列 → 表达式 → 源字段映射。

### 示例

DDL 节选：

```sql
CREATE TABLE "订单" ("记录 ID" TEXT, "订单号" TEXT, "客户" TEXT[], "状态" TEXT, "金额" DOUBLE PRECISION,
  "下单日期" TIMESTAMP, "负责人" TEXT, "负责人 ID" TEXT, "标签" TEXT[], PRIMARY KEY ("记录 ID"), UNIQUE ("订单号"));
COMMENT ON COLUMN "订单"."客户" IS '存放的是关联记录 ID，其关联到表 "客户" 的 "记录 ID" 字段';
COMMENT ON COLUMN "订单"."状态" IS '存储选项名称（待付款、已付款、已取消）';
CREATE TABLE "客户" ("记录 ID" TEXT, "行业" TEXT, PRIMARY KEY ("记录 ID"));
```

**关联字段 JOIN**（关联字段是记录 ID 数组，先 UNNEST 再 JOIN 目标表 `"记录 ID"`）：各行业已付款订单数和金额。前提：每笔已付款订单恰好关联一个可匹配客户、客户记录 ID 唯一，并有约束或查询证据。一单多客户时先定唯一归属、按权重分摊或允许重复归属，未定不套此例；`COUNT(DISTINCT 订单)` 只保护组内订单数，不保护金额、不保证跨组可加；允许重复归属时注明各组不可相加为总体。

```sql
WITH "订单客户" AS (
  SELECT o."记录 ID" AS "订单记录", o."金额", c."客户ID"
  FROM "订单" AS o, UNNEST(o."客户") AS c("客户ID") WHERE o."状态" = '已付款')
SELECT k."行业", COUNT(DISTINCT oc."订单记录") AS "订单数", SUM(oc."金额") AS "金额"
FROM "订单客户" AS oc JOIN "客户" AS k ON k."记录 ID" = oc."客户ID"
GROUP BY k."行业" ORDER BY "金额" DESC;
```

**人员字段**（展示列存姓名，`"<字段> ID"` 伴生列存 user_id）按 user_id 分组或筛选，同名不同 ID 分开，姓名仅展示；**多选字段**（TEXT[]）用数组运算符筛选，按值分组先 UNNEST：

```sql
SELECT "负责人 ID", ANY_VALUE("负责人") AS "负责人", COUNT(*) AS "订单数", SUM("金额") AS "金额"
FROM "订单" GROUP BY "负责人 ID" ORDER BY "金额" DESC;
SELECT "订单号", "标签" FROM "订单" WHERE "标签" @> ARRAY['VIP'];
SELECT u."标签", COUNT(*) AS "订单数" FROM "订单" AS o, UNNEST(o."标签") AS u("标签")
GROUP BY u."标签" ORDER BY "订单数" DESC;
```

### 月趋势与环比

按自然月分桶、用月初日期匹配真实上月，算 2025 年已付款金额环比；`LAG` 只取上一行，月份不连续时不能当“上月金额”。

```sql
WITH "月度" AS (
  SELECT DATE_TRUNC('month', "下单日期") AS "月初", SUM("金额") AS "金额" FROM "订单"
  WHERE "状态" = '已付款' AND "下单日期" >= '2025-01-01'::timestamp AND "下单日期" < '2026-01-01'::timestamp
  GROUP BY 1)
SELECT TO_CHAR(m."月初", 'YYYY-MM') AS "月份", m."金额", p."金额" AS "上月金额",
  ROUND((m."金额" - p."金额") * 100.0 / NULLIF(p."金额", 0), 2) AS "环比%"
FROM "月度" AS m LEFT JOIN "月度" AS p ON p."月初" = m."月初" - INTERVAL '1 month'
ORDER BY m."月初";
```

- 只返回有记录的月份，不补齐全年；缺上月时比较列为 null（只有 1 月、3 月数据时 3 月不能对 1 月算环比）；上月为 0 时保留 0、增长率为 null。本例未读 2024 年 12 月，1 月基期未知；要年初环比单独补基期，主结果仍限目标年度。
- 仅当已证明数据完整且业务定义把无记录月份视为零时才补零，缺失或覆盖未知不补；结果说明月份序列、基期取数、补值依据，“未返回”不等于“没有业务”。
