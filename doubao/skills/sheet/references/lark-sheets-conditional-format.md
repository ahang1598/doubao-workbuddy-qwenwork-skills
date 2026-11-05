# Lark Sheet Conditional Format

## 条件联动使用真实规则，固定标注使用静态样式

按值或规则决定颜色且需要随数据更新时，用 `+cond-format-create` / `+cond-format-update` 创建或维护规则。明确的固定标注、装饰性着色用静态样式；单独出现颜色词不强制改为条件格式。下列指令带条件或联动语义时适用：

- **颜色动作**："标红 / 标黄 / 标绿 / 上色 / 染色 / 涂色 / 表红色 / 表黄色"
- **视觉强调**："高亮 / 突出 / 标记 / 标注 / 区分"——**限带条件语义的**（按值 / 规则决定哪些格上色）；纯装饰性无条件上色（斑马纹、整行固定底色）不在强制范围，按视觉规范直接设背景色
- **条件触发**："重复的标出来 / 异常的圈出来 / 过期的染红 / 大于 X 的标黄 / 不达标的标红"
- **联动语义**："颜色随数据变 / 联动 / 自动更新 / 改了数据颜色也跟着变"
- **数值可视化**："数据条 / 色阶 / 渐变色 / 进度条样式"

需要联动的标色不能只刷静态颜色，例如过期提醒应随日期变化。用户要求一次性的固定标记时，不据此增加联动规则。

**大数据量首选**：当数据量 > 1000 行时，条件格式是首选——它由飞书自身渲染，比"本地脚本逐行计算 + `+cells-set` 写静态背景色"更高效、更稳（颜色还能随源数据自动联动）。

## 使用场景

读写条件格式对象，并读取条件格式**计算后的单元格样式结果**。本 reference 覆盖这些 shortcut：

| 操作需求 | 使用工具 | 说明 |
|---------|---------|------|
| 查看已有条件格式规则 | `+cond-format-list` | 获取规则类型、范围、样式配置与 rule_id，供后续更新或删除使用 |
| 创建/更新/删除条件格式规则 | `+cond-format-create` / `+cond-format-update` / `+cond-format-delete` | 对条件格式规则执行写入操作 |
| 用户要求查看 / 核验条件格式计算结果 | `+cond-format-result-get` | 读取条件格式计算后的 `cell_styles` |
| 常规读数时临时带上条件格式 | `+cells-get --include conditional_format` | 与 `+cond-format-result-get` 等价地合并条件格式样式，但仍归属普通单元格读取入口 |

典型工作流：先读取现有条件格式了解配置 → 执行创建/更新/删除。

**常见配置错误（必须注意）**：
- **范围与触发粒度一致**：逐格条件用相对引用，整行条件锁定判定列；确认比较的是用户指定指标。逐格规则只引用当前格，避免将逐格条件写成整行着色
- **`style.back_color` vs `style.fore_color` 的中文语义**：用户中文语境下的"**标红/染色/标记**"指**单元格背景色**，用 `back_color`；"**文字红/字体红/把字变红**"才用 `fore_color`。默认无说明时选 `back_color`。用户说"**标红**"用标准红 `back_color: "#FF0000"`；说"**高亮/突出**"才用浅色底（如 `#FFE6E6`）配合可选的 `fore_color` 加深字体——把"标红"做成浅粉会被认为没按要求标色
- **日期比较先区分有效日期、空值与异常文本**：确认日期为数值型后，可用 `=AND(ISNUMBER(E1),E1<TODAY())` 判断早于今天，包含当天时按用户要求改为 `<=`。文本日期先按明确格式解析；无效日期另列为异常，不把它当成未过期或自动纠正成别的日期，也不把空白当作 0 标红。
- **公式条件注意引用方式**：自定义公式条件中的单元格引用需要根据实际场景选择相对/绝对引用（如 `=E1<=TODAY()` 而非 `=$E$1<=TODAY()`，后者只比较一个格）
- **判重先确定字段与保留规则**：`duplicateValues` 只按单列判重；多字段用 `COUNTIFS` 等表达联合条件，或构造不会因分隔符而碰撞的辅助键。标记重复组全部成员使用全区间计数 `>1`，仅标记第二次及以后出现使用从首行到当前行的累计计数 `>1`；两者不可互换。编号按文本处理，条件值含 `*`、`?`、`~` 时按函数语义转义或改用精确比较，避免通配符扩大匹配。

⚠️ **用户明确要求"辅助列+条件格式"两步走时，禁止用 `expression` 绕过**：当用户说以下任意一种表达时，必须按两步走（先建辅助列 → 再基于辅助列做条件格式），**禁止**直接用一个 `rule_type: "expression"` 公式一步完成：

- "**增加辅助列**，再/然后标记……"
- "**先计算/判断** XX **是否** YY，**再**标记……"
- "**新建一列**放结果，再用结果染色"
- 明确要求用 "辅助列"、"辅助字段"、"判断列"、"标记列"

**正确做法（两步走）**：

Step 1 的 `+cells-set` 及 `--copy-to-range` 等 flag 以 `references/lark-sheets-write-cells.md` 为准。

```
Step 1: 先写新增列表头，再用 `+cells-set` 在每条适用记录写判断公式（形成"是/否"或布尔辅助列；条件判定不能部分写公式、部分写固定标签）
  range="H2", cells=[[{formula: "=IF(A2>B2, \"是\", \"否\")"}]], --copy-to-range="H2:H100"

Step 2: 基于辅助列值做条件格式（用 cellIs 或引用辅助列的 expression）
  `+cond-format-{create|update|delete}` create
    rule_type: "expression"
    ranges: ["A2:H100"]  // 整行高亮
    attrs: [{formula: ["=$H2=\"是\""]}]  // 引用辅助列
    style: {back_color: "#FFECEC"}
```

**错误做法（一步走绕过辅助列）**：

```
`+cond-format-{create|update|delete}` create
  rule_type: "expression"
  ranges: ["2:145"]
  attrs: [{formula: ["=$O2>$H2"]}]   ← 虽然逻辑等价，但产物里缺辅助列 → 不满足用户明确要求的"辅助列"诉求
```

为什么禁止一步走：用户明确要求辅助列是有**业务意图**的——让人肉眼能在表里看到"是/否"列；条件格式只是视觉辅助。一步 expression 虽然效果对了，但用户打开表格看不到辅助列，被视为"操作不完整/未采用公式"。

`expression` 单独使用的场景是：用户**没有**明确要求辅助列、只要"标红符合条件的行"时。

**按字段语义设置条件引用**：用已读取的表头、字段值与类型信息确定列对应。表头含义不明或类型信息不足时，再读取相关数据；不凭列名猜日期、数值或文本含义。

## 辅助判断列与动态高亮示例

需要展示规则判断并动态标记结果时，可采用「判断公式 → 辅助列 → 条件格式」。这也是导入不支持元素时的一个候选方案；是否替代按 `references/lark-sheets-workbook.md` 的通用原则选择，不要求采用本例。此实现用于提示，不会阻止录入。

采用本例时，先从源文件或用户要求读取判断规则、作用范围和空值策略，不从已丢失配置的在线表猜规则。按 `references/lark-sheets-write-cells.md` 确认真实表头行、首条数据行及空白辅助列；辅助列只放在允许新增的范围内。公式保留实际业务条件与数据范围，涉及唯一性时覆盖实际输入全区间。

示例仅演示「允许空白；录入值为非负数字且不超过同一行上限」：已确认 B 列是上限、C 列是录入值，字段表头在第 2 行、数据在第 3–12 行，F 是原末列、G 全空且允许新增。按真实结构和源规则改写，不能照抄字母与行号；要求必填时空值须返回「非法」，不能沿用示例的空字符串分支。

```bash
# 先继承表头与数据样式；不覆盖上方合并标题
lark-cli sheets +range-copy --url "<表格URL>" --sheet-name "<真实表名>" \
  --source-range "F2:F12" --target-range "G2" --paste-type formats
lark-cli sheets +cells-set --url "<表格URL>" --sheet-name "<真实表名>" \
  --range "G2" --cells '[[{"value":"输入校验"}]]'

# 写入辅助列公式并按相对引用扩展；IFERROR 按本例规则将输入错误归为非法
lark-cli sheets +cells-set --url "<表格URL>" --sheet-name "<真实表名>" \
  --range "G3" --cells '[[{"formula":"=IFERROR(IF(C3=\"\",\"\",IF(AND(ISNUMBER(C3),C3>=0,C3<=B3),\"合法\",\"非法\")),\"非法\")"}]]' \
  --copy-to-range "G3:G12"

# 锁辅助列、让行号随数据行变化，范围不含表头
lark-cli sheets +cond-format-create --url "<表格URL>" --sheet-name "<真实表名>" \
  --rule-type expression --ranges '["A3:G12"]' \
  --properties '{"attrs":[{"formula":["=$G3=\"非法\""]}],"style":{"back_color":"#FF0000"}}'
```

写入后按回执处理 `formula_errors` 和失败项，修复仅作用于已确认受影响的范围；成功后继续用户要求的后续操作或交付。

采用该方案时，在交付说明中写明实际判断规则和使用限制，例如「提示非法值，不会阻止录入」，并列出与原实现的差异。

### 仅按用户明确要求核验该方案

按用户要求选择诊断范围与项目，以下命令用于公式及条件格式结果核验：

```bash
lark-cli sheets +formula-verify --url "<表格URL>" --sheet-name "<真实表名>" \
  --range "G3:G12" --exit-on-error
lark-cli sheets +cond-format-list --url "<表格URL>" --sheet-name "<真实表名>"
lark-cli sheets +cond-format-result-get --url "<表格URL>" --sheet-name "<真实表名>" \
  --range "A3:G12"
```

按实际规则比对合法值、非法值、上下界和允许的空值；涉及唯一性时包含重复记录。用户要求测试动态联动时，在独立测试副本中修改输入并观察提示与颜色，不为测试改写用户原始记录。公式诊断返回 `partial` 时说明未覆盖范围，按所需诊断范围拆分继续。

## Shortcuts

| Shortcut | Risk | 分组 |
| --- | --- | --- |
| `+cond-format-list` | read | 对象 |
| `+cond-format-result-get` | read | 对象 |
| `+cond-format-create` | write | 对象 |
| `+cond-format-update` | write | 对象 |
| `+cond-format-delete` | high-risk-write | 对象 |

## Flags

### `+cond-format-list`

_公共四件套 · 系统：`--dry-run`_

| Flag | Type | 必填 | 说明 |
| --- | --- | --- | --- |
| `--rule-id` | string | optional | 按规则 id 过滤 |

### `+cond-format-result-get`

_公共四件套 · 系统：`--dry-run`_

| Flag | Type | 必填 | 说明 |
| --- | --- | --- | --- |
| `--range` | string | required | A1 范围，如 `A1:F10`（不带 sheet 前缀；用 `--sheet-id` / `--sheet-name` 指定 sheet） |
| `--max-chars` | int | optional | 单次返回字符上限，默认 500000（兜底防爆） |

### `+cond-format-create`

_公共四件套 · 系统：`--dry-run`_

| Flag | Type | 必填 | 说明 |
| --- | --- | --- | --- |
| `--properties` | string + File + Stdin（复合 JSON） | required | 规则配置 JSON，含 `style`（命中样式，必填）和 `attrs?`（规则参数列表，因 `rule_type` 不同结构而异）/ `has_ref?`。`rule_type` 和 `ranges` 已拎为独立 flag |
| `--rule-type` | string | required | 条件格式规则类型；优先级高于 `--properties` 中同名字段（可选值：`duplicateValues` / `uniqueValues` / `cellIs` / `containsText` / `timePeriod` / `containsBlanks` / `notContainsBlanks` / `dataBar` / `colorScale` / `rank` / `aboveAverage` / `expression` / `iconSet`） |
| `--ranges` | string + File + Stdin（简单 JSON） | required | 应用条件格式的 A1 范围 JSON 数组（如 `["A1:A100","C2:C50"]`）；优先级高于 `--properties` 中同名字段 |

### `+cond-format-update`

_公共四件套 · 系统：`--dry-run`_

| Flag | Type | 必填 | 说明 |
| --- | --- | --- | --- |
| `--rule-id` | string | required | 目标规则 id |
| `--properties` | string + File + Stdin（复合 JSON） | required | 规则配置 JSON，结构同 `+cond-format-create` 的 `--properties`；update 是整组覆盖式 |
| `--rule-type` | string | required | 条件格式规则类型；优先级高于 `--properties` 中同名字段（可选值：`duplicateValues` / `uniqueValues` / `cellIs` / `containsText` / `timePeriod` / `containsBlanks` / `notContainsBlanks` / `dataBar` / `colorScale` / `rank` / `aboveAverage` / `expression` / `iconSet`） |
| `--ranges` | string + File + Stdin（简单 JSON） | required | 应用条件格式的 A1 范围 JSON 数组（如 `["A1:A100","C2:C50"]`）；优先级高于 `--properties` 中同名字段 |

### `+cond-format-delete`

_公共四件套 · 系统：`--yes`、`--dry-run`_

| Flag | Type | 必填 | 说明 |
| --- | --- | --- | --- |
| `--rule-id` | string | required | 目标规则 id |

## Schemas

> 复合 JSON flag 字段速查（只列顶层 + 一层嵌套）。深层结构看下方 `## Examples`，或用 `--print-schema` 读完整 JSON Schema（用法见 SKILL.md「公共 flag 速查」与「Agent 使用提示」）。

### `+cond-format-create` `--properties` / `+cond-format-update` `--properties`

_创建/更新的条件格式属性_

**顶层字段**：
- `rule_type` (enum) — 条件格式规则类型 [duplicateValues / uniqueValues / cellIs / containsText / timePeriod / containsBlanks / notContainsBlanks / dataBar / colorScale / rank / aboveAverage / expression / iconSet] — ⚠️ 已拎为独立 flag `--rule-type`，请勿在此 JSON 内重复填写（同名以独立 flag 为准）
- `ranges` (array<string>) — 应用条件格式的 A1 范围列表 — ⚠️ 已拎为独立 flag `--ranges`，请勿在此 JSON 内重复填写（同名以独立 flag 为准）
- `style` (object) — 命中规则时应用的单元格样式 { back_color?: string, fore_color?: string, text_decoration?: enum, font?: enum }
- `attrs` (array<oneOf>?) — 规则参数列表
- `has_ref` (boolean?) — 可选

## Examples

公共四件套：所有 shortcut 顶部排列 `--url` / `--spreadsheet-token` / `--sheet-id` / `--sheet-name`（XOR）。

### `+cond-format-list`

```bash
# 列出当前 sheet 全部条件格式规则（拿 rule_id 供 update/delete）
lark-cli sheets +cond-format-list --url "..." --sheet-id "$SID"
```

### `+cond-format-create`

`--rule-type` / `--ranges` 是独立 flag（不要再放 `--properties`）；`style` / `attrs` 等结构走 `--properties`：

```bash
# 重复值高亮
lark-cli sheets +cond-format-create --url "..." --sheet-id "$SID" \
  --rule-type duplicateValues --ranges '["A1:A100"]' \
  --properties '{"style":{"back_color":"#FFD7D7"}}'

# 数据条
lark-cli sheets +cond-format-create --url "..." --sheet-id "$SID" \
  --rule-type dataBar --ranges '["B2:B100"]' \
  --properties @rule.json
```

### `+cond-format-result-get`

用于读取条件格式**计算后的样式结果**，不是读取规则对象。用户需要查看计算样式时使用。

CLI 会对白名单字段做输出裁剪：顶层只保留警告、分页和返回单元格计数；每个 range 只保留请求/实际范围、真实行列坐标、截断标记和二维 `cells`；每个 cell 只保留 `cell_styles`，不返回 `value` / `formula` / `note` / `data_validation` / `border_styles` 等其它单元格数据。`cell_styles` 是底层开启条件格式计算后得到的最终合并样式，不包含 `rule_id` 或独立的命中标记。

```bash
# 读取 B2:B10 的条件格式命中样式，返回 cell_styles.background_color / font_color 等
lark-cli sheets +cond-format-result-get --url "..." --sheet-id "$SID" \
  --range "B2:B10"

# 如果只想在普通读取里临时合并条件格式，也可用 +cells-get --include conditional_format
lark-cli sheets +cells-get --url "..." --sheet-id "$SID" \
  --range "B2:B10" --include conditional_format
```

### `+cond-format-update`

整组覆盖式：先 `+cond-format-list --rule-id <id>` 拿当前完整配置，改后整组传回。

### `+cond-format-delete`

```bash
lark-cli sheets +cond-format-delete --url "..." --sheet-id "$SID" --rule-id "$RULE_ID" --yes
```

> 一次只删一个 `--rule-id`。要删**多个**条件格式时，先 `+cond-format-list` 拿到各 `rule-id`，再用 `+batch-update` 把多个 `+cond-format-delete` 合并为单次批量提交（fail-fast，失败处置见 `references/lark-sheets-batch-update.md`），不要逐个调用。

### Validate / DryRun / Execute 约束

- `Validate`：XOR 公共四件套；`--rule-type` / `--ranges` 必填；`--properties` 必须能解析为合法 JSON；按 `--rule-type` 检查必填子字段（`cellIs` 需 `attrs.operator` + `attrs.value`、`expression` 需 `attrs.formula`、`colorScale` 需 `min/mid/max` 配色等）；`+cond-format-delete` 强制 `--yes` 或 `--dry-run`。
- `DryRun`：写操作输出"将要 POST/PATCH/DELETE 的 conditional_format 请求模板"。

===== 全文完（共 252 行）=====
