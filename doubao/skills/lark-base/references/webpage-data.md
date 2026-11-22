# 页面查询数据与人员搜索

页面需要查询 Base 数据或搜索人员时加载本文件。查询代码前读取工程内的 `common/hooks/use-base-data.ts`、`common/types/base-query-dsl.ts`；使用人员搜索时再读 `common/api`。单条新增与附件上传按需读取 [新增记录规则](webpage-record-create.md)。说明使用中文，代码标识符、类型名、字段名保持英文原名（翻译后照抄会导致编译或运行错误）。

表、字段及选项使用已核实的元数据，`fieldId` 属于对应的 `tableId`；记录 ID 来自真实记录。资料不足时用 Base 的 `+table-get` / `+field-list` / `+field-get` 补齐，选项可用 `+field-search-options` 查询。

## 能力边界（先读）

本文件负责真实记录、统计与排行的查询展示，以及查询 / 录入共用的人员搜索。查询、筛选、排序、聚合、图表与详情不触发写入；新增记录的能力边界见 [新增记录规则](webpage-record-create.md)，完整拒识清单见 [页面开发入口](../scenes/webpage.md) 的「不支持的能力（拒识）」。

## useBaseData：查询取数

通过 `useBaseData()` 读取真实 Base 数据；查询为空时显示空状态，不用 mock 或虚构记录兜底。指标数字与结论由查询结果计算，尚无数据时使用「数据概览」等中性标签。

```tsx
import { useBaseData } from "../common/hooks/use-base-data";
import { Aggregation } from "../common/types/base-query-dsl";
```

### DSL 结构（所有字段引用都用 `fieldId`）

```tsx
const [pageIndex, setPageIndex] = useState(0);
const pageSize = 50;
const { data, loading, error, total, hasMore, refetch } = useBaseData({
  dsl: {
    datasource: { table: { tableId: "tblXXXX" } },

    // 三种查询模式选其一（至少一个）：
    // 模式 1：columns —— 原始字段值，不分组（原始记录列表）
    columns: [{ fieldId: "fldXXXX" }, { fieldId: "fldYYYY" }],

    // 模式 2：dimensions + measures —— 分组聚合（图表 / KPI）
    // dimensions: [{ fieldId: "fldXXXX" }],
    // measures: [{ fieldId: "fldYYYY", aggregation: Aggregation.Sum }],

    // 模式 3：仅 measures —— 全表聚合（单个 KPI）
    // measures: [{ fieldId: "fldYYYY", aggregation: Aggregation.Sum }],

    filters: {                       // 可选 —— 单层过滤结构
      conjunction: "and",            // "and" | "or" —— 同一查询共用一个
      conditions: [{                 // 叶子数组：{ fieldId, operator, value }
        fieldId: "fldZZZZ",
        operator: "isGreater",       // 原始过滤操作符（见下表）
        value: ["0"],
      }],
    },
    sort: [{ fieldId: "fldXXXX", order: "asc" }],  // 可选，asc | desc
  },
  pageSize,          // 可选 —— 服务端分页，最大 100
  pageIndex,         // 可选 —— 0 起的页码状态，用于原始记录列表
});
const totalPages = Math.ceil((total ?? 0) / pageSize);
const goPrevPage = () => setPageIndex(prev => Math.max(prev - 1, 0));
const goNextPage = () => hasMore && setPageIndex(prev => prev + 1);
```

### DSL 查询约束

- **`columns` / `dimensions` / `measures` 至少有一个**，空查询会被拒绝。
- **每个 measure 必须声明 `aggregation`**，漏了会 `ErrInvalidParam`。
- **排序用原始 `fieldId`**；`count(fldXX)`、`sum(fldXX)` 是输出 key。按聚合结果做服务端 Top N 排名是仪表盘转换的专有扩展，用 measure `alias` + `sort.ref` + `pagination.limit`，见 [仪表盘指引](webpage-dashboard.md)。
- **`filters.conditions` 是叶子 `{ fieldId, operator, value }` 的扁平数组**，同一查询共用一个 `conjunction`（`"and"` 或 `"or"`），不支持嵌套或混合 AND / OR。多字段 OR 搜索与其他 AND 筛选无法组合在同一查询中，可改用单个主字段 `contains` 搜索，其他筛选共用 `"and"`。
- **Link/DuplexLink 字段按 recId 过滤**，`fieldId` 使用关联字段 ID，`value` 使用该字段的 `originValue` 或 `row["rec_id"]?.value` 中的记录 ID。DSL 不支持把 `rec_id` 当过滤字段；显示标题不能用于关联匹配。
- **每字段上限**：`columns` ≤ 30、`dimensions` ≤ 30、`measures` ≤ 30、`filters.conditions` ≤ 30、`sort` ≤ 30。
- **搜索、筛选、排序、排名和统计由 DSL 完成**，前端仅持有一页数据（≤ pageSize 行），本地处理不能代表全表结果。关键词变化时更新 DSL 的 `contains` 条件重新查询。
- **`columns` 查询展示完整列表时提供分页 UI**，用有状态的 `pageIndex` + `total` / `hasMore` 访问所有页，筛选变化时 `pageIndex` 归 0。明确只取有限子集（如卡片 top-N、单条查询）可省略分页。
- **Hook 在组件顶层调用。**
- **DSL 中的值跨 render 保持稳定。** `useBaseData` 把序列化后的 DSL 作为 effect 依赖；直接写入 `dayjs()` 等每次变化的值可能持续触发请求，动态时间用 `useMemo` 算定：
  ```tsx
  const sixMonthsAgo = useMemo(() => dayjs().subtract(6, "month").valueOf(), []);
  // 再在 filters.conditions[].value 里使用 sixMonthsAgo
  ```
- **展示用 `.value`，数值逻辑用 `.originValue`。** `.value` 是格式化显示串（如 `"85%"`、`"¥312,312.00"`），不能直接作为原始数字；`.originValue` 保留 `0.85`、`312312` 等原始值。
- **日期统一用 `dayjs`**——日期 `.value` 格式随用户设置变化。用 `dayjs(row["fldXXX"]?.value)` 解析，`.month()` / `.year()` / `.format()` 提取。

### Aggregation 枚举（import 自 `../common/types/base-query-dsl`）

- `Aggregation.Sum` — Number、Progress、Currency、Rating、Duration
- `Aggregation.Avg` — Number、Progress、Currency、Rating、Duration
- `Aggregation.Min` — Number、Progress、Currency、Rating、Duration、Date
- `Aggregation.Max` — Number、Progress、Currency、Rating、Duration、Date
- `Aggregation.Count` — 除 Attachment 外所有类型 —— 只统计非空值
- `Aggregation.CountAll` — 除 Attachment 外所有类型 —— 统计所有行（含空）
- `Aggregation.DistinctCount` — 除 Attachment 外所有类型 —— 统计去重值个数

统计每组记录 / 行数用 `Aggregation.CountAll`；统计某字段非空单元格用 `Count`。

### 过滤操作符

支持的操作符：`"is"`、`"isNot"`、`"contains"`、`"doesNotContain"`、`"isEmpty"`、`"isNotEmpty"`、`"isGreater"`、`"isGreaterEqual"`、`"isLess"`、`"isLessEqual"`。并非所有操作符都适用所有字段类型，按下方规则选。

```tsx
{
  fieldId: "fldXXXX",   // 必填 —— 字段 ID
  operator: "is",       // 必填 —— 过滤操作符
  value: ["text"]       // 除 isEmpty/isNotEmpty 外必填；格式取决于字段类型
}
```

#### 各字段类型取值规则

- Text/Phone/URL/Location/AutoNumber：字符串数组，如 `["abc"]`。文本型不支持范围操作符；AutoNumber 支持。
- Number/Progress/Currency/Rating/Duration：数值字符串数组，如 `["100"]`；Progress 用小数串，如 60% 写 `["0.6"]`。
- SingleSelect/Stage/MultiSelect：已核实的 **option ID** 字符串数组，如 `["optXXXX"]`。`is` / `isNot` 恰好 1 项，`contains` / `doesNotContain` 可多项。
- User/CreatedUser/ModifiedUser：userId 字符串数组，如 `["ou_aaa", "ou_bbb"]`。IMGroup：groupId 字符串数组，如 `["oc_aaa", "oc_bbb"]`。
- SingleLink/DuplexLink：`value` 是 **recId 扁平字符串数组**，如 `["recAAA", "recBBB"]`；`originValue` 已是数组时直接传入，不再包一层数组。Attachment：仅 `"isEmpty"` / `"isNotEmpty"`。
- Formula/Lookup：按上面对应的真实结果类型。

#### 日期过滤

- 支持的操作符**仅**：`"is"`、`"isGreater"`、`"isLess"`、`"isEmpty"`、`"isNotEmpty"`。**不支持** `"isGreaterEqual"` / `"isLessEqual"`——用 `"isGreater"` / `"isLess"` 配合 ±1 天。
- **`isGreater` / `isLess` 按天粒度排除所指日期。** 匹配某一天用 `operator: "is"`；要包含边界日则偏移 1 天（"≥ X 日" → `isGreater` 的 X-1 日）。
- 预定义取值：
  - 精确 / 区间：`["ExactDate", "<ms_timestamp>"]`（`is`/`isGreater`/`isLess`，绝不用 ISO），`["RangeDate", "<start_ms>", "<end_ms>"]`（仅 `is`）。
  - 日：`["Today"]`、`["Tomorrow"]`、`["Yesterday"]`（也支持范围操作符）；`["TheDayBeforeYesterday"]`、`["OneWeekBefore"]`、`["OneMonthBefore"]`、`["OneYearBefore"]`、`["OneWeekBeforeYesterday"]`、`["OneMonthBeforeYesterday"]`、`["OneYearBeforeYesterday"]`。
  - 周 / 月：`["CurrentWeek"]`、`["CurrentWeekEndDay"]`、`["LastWeek"]`、`["LastWeekEndDay"]`、`["OneWeekBeforeLastWeek"]`、`["LastYearCurrentWeekEndDay"]`、`["OneYearBeforeLastWeek"]`、`["CurrentMonth"]`、`["CurrentMonthEndDay"]`、`["LastMonth"]`、`["LastMonthEndDay"]`、`["OneMonthBeforeLastMonth"]`、`["LastYearCurrentMonthEndDay"]`、`["OneYearBeforeLastMonth"]`。
  - 季 / 年：`["CurrentQuarterEndDay"]`、`["LastQuarter"]`、`["LastQuarterEndDay"]`、`["OneQuarterBeforeLastQuarter"]`、`["LastYearCurrentQuarterEndDay"]`、`["OneYearBeforeLastQuarter"]`、`["CurrentYearEndDay"]`、`["LastYear"]`、`["LastYearEndDay"]`、`["OneYearBeforeLastYear"]`。
  - 滚动：`["TheLastWeek"]`、`["TheNextWeek"]`、`["TheLastMonth"]`、`["TheNextMonth"]`、`["LatestOneWeek"]`、`["LastOneWeek"]`、`["LatestTwoWeek"]`、`["LastTwoWeek"]`、`["LatestOneMonth"]`、`["LastOneMonth"]`、`["LatestThreeMonthEndDay"]`、`["LastThreeMonthEndDay"]`、`["LatestHalfYearEndDay"]`、`["LastHalfYearEndDay"]`、`["LatestOneYear"]`、`["LastOneYear"]`。
- 快速日期默认 `is`。`...EndDay` 指"截至今天 / 对应日"的区间，不是某个字面句末日期。snapshot token 原样保留，绝不改写成 `ExactDate`。
- 未列出的区间用计算后的 `ExactDate`；绝不发明 `TheLastSixMonths`、`CurrentYear` 这类 token（`CurrentYearEndDay` 合法）。

#### Checkbox 过滤

- 仅支持 `"is"`，值 `["true"]` 或 `["false"]`。

### 返回值 —— 输出 Key 规则

`data` 为 `Array<Record<string, { value: any; originValue: any; attachments?: Array<{ url: string; type: "image" | "video" | "audio" | "unknown" }> }>>`。`attachments` 只在 Attachment 字段提供，其他字段不要读取或处理。

**输出 key：dimension / column 用 `fieldId`，measure 用 `agg(fieldId)`。** 聚合名用 snake_case（`count_all`、`distinct_count`，不是 `countAll` ❌）。

`columns` 模式每行含内置 `rec_id`：`row["rec_id"]?.value` 返回 recordId（如 `"recXXXX"`），可用作 Link 字段过滤值。

| 查询字段类型 | 输出 key 格式 | 访问示例 |
|---|---|---|
| dimension / column | `fieldId` | `row["fldXXXX"]?.value` |
| measure | `aggregation(fieldId)` | `row["count_all(fldYYYY)"]?.value` |
| 内置 | `rec_id` | `row["rec_id"]?.value` |

```tsx
// 分组聚合
const { data } = useBaseData({
  dsl: {
    datasource: { table: { tableId: "tblXXXX" } },
    dimensions: [{ fieldId: "fldAAA" }],
    measures: [{ fieldId: "fldBBB", aggregation: Aggregation.Sum }],
    sort: [{ fieldId: "fldBBB", order: "desc" }],  // 排序用原始 fldXXX，不是 "sum(fldBBB)"
  }
});
// 访问：row["fldAAA"]?.value（维度）、row["sum(fldBBB)"]?.value（度量）

// Link 字段过滤：value 使用关联记录的 recId 数组
const { data: tasks } = useBaseData({
  dsl: {
    datasource: { table: { tableId: "tblTasks" } },
    columns: [{ fieldId: "fldTaskName" }, { fieldId: "fldStatus" }],
    filters: {
      conjunction: "and",
      conditions: [{
        fieldId: "fldTaskId",
        operator: "contains",
        value: ["recAAA", "recBBB"],  // 关联字段 originValue 中的 recId
      }],
    },
  }
});

// columns 查询 + 分页
const { data: rawData, total, hasMore } = useBaseData({
  dsl: { datasource: { table: { tableId: "tblXXXX" } }, columns: [{ fieldId: "fldAAA" }, { fieldId: "fldBBB" }, { fieldId: "fldCCC" }] },
  pageSize: 50,
  pageIndex,
});

rawData?.map(row => ({
  name: row["fldAAA"]?.value,
  amount: row["fldBBB"]?.value,         // 直接展示；数值逻辑用 .originValue
  image: row["fldCCC"]?.value?.[0],     // attachment：value 是 string[]，元素即 URL
}));
```

```tsx
// ❌ 错 —— .value 已格式化（如 "85%"、"¥312,312.00"）→ Number() = NaN
Number(row["fldXX"]?.value)        // "85%" → NaN

// ❌ 错 —— .value 已含符号，不要再加 "%" 或 "¥"
<span>{row["fldXX"]?.value}%</span>          // "85%" + "%" → "85%%"

// ✅ 对 —— 直接渲染 .value
<span>{row["fldBBB"]?.value}</span>           // "¥312,312.00"
<span>{row["sum(fldBBB)"]?.value}</span>      // "1,234,567.00"

// ✅ 对 —— 数值逻辑用 .originValue
const raw = row["fldBBB"]?.originValue;  // 312312（原始数字）
```

**各字段类型的 value / originValue：**
- Text、Email、Barcode、AutoNumber：`value` 始终是字符串。
- Number：`value` 是格式化显示串（如 `"121231.00"`、`"85%"`、`"1,234"`）；`originValue` 是原始数字（如 `121231`、`0.85`、`1234`）。数值逻辑用 `originValue`。
- Progress/Currency/Rating/Duration：`value` 已格式化（如 `"60%"`、`"¥312,312.00"`）；`originValue` 是原始数字。
- DateTime/CreatedTime/ModifiedTime：`value` 是格式化串如 `"2026/03/04 10:58"`。
- Checkbox：`value` 是 `"true"` / `"false"`；字段为空时返回 `"false"`。
- SingleSelect/Stage：`value` 是选项名字符串，`originValue` 是选项 ID（`"optXXX"`）。
- MultiSelect：`value` 是名字数组 `["选项A", "选项B"]`，`originValue` 是 ID 数组 `["optA", "optB"]`（下标对应）。
- User/CreatedUser/ModifiedUser：`value` 是名字数组 `["张三", "李四"]`，`originValue` 是 userId 数组 `["uid1", "uid2"]`。
- IMGroup：`value` 是群名数组 `["群组A", "群组B"]`，`originValue` 是 `["oc_aaa", "oc_bbb"]`。
- SingleLink/DuplexLink：`value` 是标题数组 `["标题A", "标题B"]`，`originValue` 是 recId 数组 `["recAAA", "recBBB"]`。判断归属用 `.includes()`，绝不 `=== "recXXX"`；过滤必须用 `originValue`。
- Attachment：`attachments` 是可选的 `{ url, type }` 数组。存在时**必须**用它而非 `value`，并显式判断每种 type 再渲染：`image` → `<img>`、`video` → `VideoPlayer`、`audio` → `AudioPlayer`、`unknown` → `<img>`。缺 `attachments` 才回退到兼容 URL 数组 `value`；不要给 `value` 的元素追加 `.url`。
- Phone：电话号字符串。URL（超链接）：链接文本字符串。Location：完整地址字符串。
- Formula/Lookup：按结果类型，但**数字型特殊**——`originValue` 是字符串（如 `"312312"`），多值逗号拼接 `"1.3,1.4"`，运算前先 `Number(originValue)` 或 `.split(",").map(Number)`；`value` 像 Number 一样已格式化。
- measure 列：`count`/`count_all`/`distinct_count` 返回整数；`sum`/`avg`/`min`/`max` 按源字段类型格式化。measure 为空时 `value` 与 `originValue` 均 `null`。
- 空值：维度 `value` 为空时为 `null`（Checkbox 除外 → `"false"`）；空查询结果为 `[]`。

不同查询可以调用多个 `useBaseData`。

## 人员搜索 `searchUsers`

查询筛选或新增 User 字段需要人员选择时，通过 `common/api` 导出的 API 搜索人员，不直接 import 或调用底层 channel client。

```tsx
import {
  searchUsers,
  type SearchUser,
} from "../common/api";
```

用文本关键词调用 `searchUsers(searchText)`，返回 `Promise<SearchUser[]>`。

```tsx
interface SearchUser {
  userId: string;
  name: string;
  enName: string;
  avatarUrl: string;
  isExternal: boolean;
}

const users = await searchUsers(searchText.trim());
```

- 用 `userId` 作稳定标识、React list key 与 User 字段过滤值；新增记录的人员编码见 [新增记录规则](webpage-record-create.md)。
- 输入后自动触发搜索（建议 300ms 防抖），不要求点提交按钮。
- 空关键词合法：`searchUsers("")` 返回推荐人员列表。
- 用请求序号或取消守卫保护异步搜索，避免旧响应覆盖新结果。
- 显式处理 loading、空、错误状态。
- 人员搜索依赖宿主 sandbox/iframe 通道，必须在该环境验证；本地浏览器直连可能没有宿主桥接。

## 构建前核对

实现前按本节核对查询方案，构建前对照实际代码再查一次；修改只检查涉及的查询及必要关联。

**数据真实性**

- Base 展示数据与指标都来自 `useBaseData`：没有示例数组、兜底假数据或模仿真实数据的默认值。
- 无数据时显示空状态；文案不写死未经查询支持的数字与结论，也不把空值显示成查询得到的 0。

**表与字段引用**

- 表、字段、选项 ID 与元数据逐字一致，字段属于所查的数据表；`tableId` 放在 `datasource.table.tableId`。
- DSL 字段引用用以 `fld` 开头的真实 `fieldId`，不拿 `rec_id`、字段名称或系统属性替代。
- 指标、筛选、排行、详情绑定的字段含义与名称一致，不用 ID、编码或相近字段代替。
- 多个指标共用一个筛选时，统计口径一致，各自时间范围符合需求；合并多个来源的结果时覆盖全部要求的来源。

**查询结构**

- 每个查询含 columns、dimensions + measures、measures 三者之一；每个 measure 都有 `aggregation`；排序按上方「DSL 查询约束」核对。
- 筛选、搜索、排序、聚合按本文 DSL 契约执行：`filters` 为扁平的单一 conjunction，选项 / 关联 / 日期值编码合法。
- DSL 用 `useMemo` 保持引用稳定，不在其中直接写 `dayjs()`。

**取值与展示**

- `.value` 用于展示，`.originValue` 用于数值逻辑；输出 key 按本文件或所加载专项的返回契约读取。
- Formula / Lookup 的数字先按真实结果类型转换；聚合只用契约支持的字段类型与操作。
- 数值动画、图表、指标组件按其实际 API 传入所需 props 或 children；输入是有限的原始数字，不传格式化字符串或组件不支持的属性，不存在必然产生 `NaN` 的路径。

**分页与人员**

- 完整列表有真实分页（`pageIndex` + `total` / `hasMore`），筛选变化时 `pageIndex` 归 0。
- 人员选择使用真实搜索结果中的 `userId`，加载、空与错误状态完整。
