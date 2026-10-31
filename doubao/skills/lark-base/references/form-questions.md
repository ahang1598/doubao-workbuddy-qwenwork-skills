# 表单题目操作与配置协议

## 目录

- [创建或复用题目](#创建或复用题目form-questions-create)
- [更新题目](#更新题目form-questions-update)
- [删除题目](#删除题目form-questions-delete)
- [可见题目与排序](#可见题目与排序)
- [题目属性协议](#题目属性协议)

题目来源、标题保护、目标属性与数据保护范围见 [Form Scene](../scenes/form.md#共同约束与收集项核对)。

## 创建或复用题目（+form-questions-create）

### 创建参数

| 参数 | 必填 | 说明 |
|---|---|---|
| `--base-token <token>` | 是 | Base Token（base_token） |
| `--table-id <id>` | 是 | 数据表 ID |
| `--form-id <id>` | 是 | 表单 ID |
| `--questions <json>` | 是 | 1~10 个问题对象的 JSON 数组 |
| `--format` | 否 | json（默认）\| pretty \| table \| ndjson \| csv |
| `--as` | 否 | 本环境仅支持 user |
| `--dry-run` | 否 | 预览 API 调用，不执行 |

### 创建请求与支持类型

每个对象二选一：形态 A 新建字段题目；形态 B 复用已有字段。基础 `type` 仅有 `text`、`number`、`select`、`datetime`、`user`、`attachment`、`location`。

| 边界 | 规则 |
|---|---|
| 基础 `type` | 只填上述小写值；不得填 `Email`、`Currency`、`SingleLink` 等 UI 类型名 |
| 7 类之外的字段 | `checkbox`、`group_chat`、`link`、`formula`、`lookup`、系统时间／人员、自动编号、按钮等不能通过形态 B 加入表单 |
| 样式 | Phone、Email、Url、Barcode 是文本样式，Currency、Progress 是数字样式；基础类型受支持不代表样式可用，按[样式协议](#题目样式与数字精度)和服务端结果判断 |
| 两种请求 | 形态 A 可带字段定义；形态 B 只带字段标识和题目配置，不带 `type/style/options/multiple/name` |

未验证样式视为未知；本地校验通过不代表服务端接受。主档关联见 [Form Scene](../scenes/form.md#输入与业务关联)：不得用 Link、文本或 URL 代替记录关系；选择主档对象时补单选题，提交后建关联。

#### 形态 A：新建字段题目

在数据表中新建字段，返回的 question `id` 即新字段 `field_id`；显式传 `title` 和 `type`。

| 字段 | 必填 | 规则 |
|---|---|---|
| `title` | 是 | 问题标题（字段名） |
| `type` | 是 | 上述 7 类之一 |
| `description` | 否 | 纯文本或 Markdown 链接，如 `[文本](https://example.com)` |
| `required` | 否 | true/false |
| `option_display_mode` | 否 | 仅 `select`：`0`=下拉，`1`=纵向（默认），`2`=横向 |
| `multiple` | 否 | `select`/`user` 是否多选（bool） |
| `options` | 否 | 仅 `select`：`[{"name":"选项1","hue":"Blue"}]`；hue=`Red/Orange/Yellow/Green/Blue/Purple/Gray` |
| `style` | 否 | 见[样式协议](#题目样式与数字精度) |
| `visible_rule` | 否 | 见[显隐条件](#显隐条件visible_rule) |
| `input_range_limit` | 否 | 字数、数值或日期范围，见[输入范围](#输入范围限制input_range_limit) |

#### 形态 B：已有字段题目

把上述 7 类已有字段加入表单；不建字段、不改记录。用于恢复 `--keep-field` 移出的题目或补充已有字段。

| 字段 | 必填 | 规则 |
|---|---|---|
| `use_existing_field` | 是 | 固定 `true` |
| `field_id` | 是 | 字段 ID 或字段名，长度 1~100；用 ID 避免同名，长名称用 ID |
| `title` | 否 | 省略时用字段名 |
| `description` | 否 | 同形态 A |
| `required` | 否 | 默认 false |
| `option_display_mode` | 否 | 仅 `select`：`0`/`1`（默认）/`2` |
| `visible_rule` | 否 | 见[显隐条件](#显隐条件visible_rule) |

- strict schema：带 `type`、`style`、`options`、`multiple`、`name` 会被拒绝。
- `options` 是形态 A 的字段选项定义，不是过滤器；形态 B 和更新无选项子集参数。`option_display_mode` 只改展示，`visible_rule` 只改整题显隐，均不限制答案。
- 范围与共享字段保护见 [Form 决策](../scenes/form.md#必填条件显示与输入范围)。
- 形态 B 需要输入范围时：先加入表单，回读题目 ID，再用 `+form-questions-update` 传 `input_range_limit`，并按[全量覆盖](#全量覆盖与回读)带回其他属性；已是成员的题目直接更新。形态 A 的限制随创建一次提交。

### 题目样式与数字精度

| 类型 | `style` | 规则 |
|---|---|---|
| `text` | `{"type":"plain"}` / `phone` / `email` / `url` / `barcode` | 服务端裁决是否可用；拒绝后按下节恢复 |
| `number` | `{"type":"plain","precision":0}` 或 `precision:2` | `precision` 是小数位数，按要求选择 |
| `number` 评分 | `{"type":"rating","icon":"star","min":1,"max":5}` | icon=`star/heart/thumbsup/fire/smile/lightning/flower/number` |
| `datetime` | `{"format":"yyyy/MM/dd"}` | format=`yyyy/MM/dd`、`yyyy/MM/dd HH:mm`、`MM-dd`、`MM/dd/yyyy`、`dd/MM/yyyy` |

数字完整协议见 [number 配置](field-config.md#number-字段)。

### 样式拒绝后的恢复

| 情形 | 动作 |
|---|---|
| 触发 | 7 类题目带非默认 `style`，且 schema 或具体错误确认不接受。缺参数、未知属性、权限、超时、网络错误按原原因处理 |
| `number` + `plain` 失败 | 不删 `style`；保留所需 `precision` 并处理实际错误；精度无法满足则报告未完成 |
| 只有 `invalid_request`、`N issues` 等泛错 | 不足以判定样式不支持；保留错误，核对形态和错误路径；无法定位则报告受阻，不删整批 `style` 试探 |
| 同时出现另一形态的 `use_existing_field` / `field_id` | 这是 union 报错，不据此切换形态；核对本次形态和错误路径 |
| 形态 A 回退 | 确认允许普通样式后去掉 `style` 重发一次；文本落为 `plain`。参数校验拒绝不会建字段；超时或部分成功先列现有字段和题目，不整批重放 |
| 形态 B 回退 | 先用 `+field-update` 把字段 `style.type` 改为 `plain`，再加入表单 |
| 再次拒绝 | 回退只做一次；保留错误并停止该项重试 |

样式变更授权、能力降低、未完成项见 [Scene](../scenes/form.md#样式拒绝后的恢复)。

```bash
# 形态 A；同批显隐条件可引用更靠前的新题
lark-cli base +form-questions-create --base-token "<base_token>" --table-id "<table_id>" --form-id "<form_id>" \
  --questions '[{"type":"select","title":"状态","options":[{"name":"启用","hue":"Blue"}]},{"type":"number","title":"金额","required":true,"visible_rule":{"logic":"and","conditions":[["状态","==","启用"]]},"input_range_limit":{"type":"number_range","min_value":0}}]'
```

形态 B 的 `--questions` 最小对象：`[{"use_existing_field":true,"field_id":"fldOwner"}]`。

创建／更新响应：

```json
{"ok":true,"data":{"items":[{"id":"q_001","title":"状态","required":true}]}}
```

## 更新题目（+form-questions-update）

参数同创建：`--base-token`、`--table-id`、`--form-id`、`--questions <json>`（最多 10 个）、`--format`、`--as`、`--dry-run`。

### 全量覆盖与回读

- 本命令全量覆盖，不是 patch；未带属性回落默认值，空字符串／`null`／空数组写空。
- 更新前用 `+form-questions-list` 读完整配置，将要保留的属性原样带回。只传 `{"id":"q_002","title":"新标题"}` 会清 `description`、使 `required=false`、清 `visible_rule`。
- 仅在用户明确要求时传空值：`description:""` 清描述；`visible_rule:null` 或 `conditions:[]` 清条件；`input_range_limit:null` 清范围。
- 更新不改题序；响应 `questions` 只含本次题目且不代表题序；请求排列不改变实际顺序。题序见[下节](#可见题目与排序)。

### 更新请求与属性默认值

每个对象必须含 `id`，表示目标完整配置。

| 字段 | 必填 | 省略／空值语义 |
|---|---|---|
| `id` | 是 | 问题 ID（field_id），不可修改 |
| `title` | 否 | 省略回落字段名；空串写空标题（若允许）；也是 `+form-submit` 的字段键，保留须带回 |
| `description` | 否 | 纯文本或 Markdown 链接；省略或空串均清空 |
| `required` | 否 | 省略回落 `false` |
| `option_display_mode` | 否 | 仅 `select`：`0`/`1`（默认）/`2`；省略回落默认 |
| `visible_rule` | 否 | 完整 `{logic,conditions}` 覆盖；`null` 或省略均清空 |
| `input_range_limit` | 否 | 完整对象覆盖；`null` 清除；省略不保留 |

```bash
# 读－改－写；带回全部待保留属性
lark-cli base +form-questions-list --base-token "<base_token>" --table-id "<table_id>" --form-id "<form_id>"
lark-cli base +form-questions-update --base-token "<base_token>" --table-id "<table_id>" --form-id "<form_id>" \
  --questions '[{"id":"q_001","title":"真实姓名","description":"请填写真实姓名","required":true,"visible_rule":null}]'
```

## 删除题目（+form-questions-delete）

默认删除底层字段及记录值；按 [Scene](../scenes/form.md#移除题目与底层字段保护) 选择：

| 参数 | 结果 |
|---|---|
| 传 `--keep-field` | 只移出表单，保留字段和记录值；可按[形态 B](#形态-b已有字段题目)重新加入 |
| 省略 `--keep-field` | 删除字段及记录值；仍受[主字段删除限制](field-commands.md#删除字段与主字段限制) |

仅隐藏并保留成员关系时改[可见题目](#可见题目与排序)。

```bash
lark-cli base +form-questions-delete --base-token "<base_token>" --table-id "<table_id>" --form-id "<form_id>" \
  --question-ids '["<field_id>"]' --keep-field --yes
```

返回 `data.deleted` 是布尔值。

## 可见题目与排序

目标顺序与依赖冲突见 [Scene](../scenes/form.md#题序目标与依赖)。Form 在 `visible_fields` 接口中作为 View，`--view-id` 传表单 ID；`+view-get-visible-fields` 读、`+view-set-visible-fields` 写同一份 `visible_fields`，数组顺序即题序。没有表单专用排序命令，`+form-questions-update` 也不控制题序，但不能因此说不支持排序。

- 用 `+view-get-visible-fields` 取列表并回读；隐藏成员 ID 从题目 list 取，题目列表只对照成员和属性，不证明题序。
- 数组整体覆盖集合和顺序；只传移动题会隐藏其余题。被省略的题仍是成员，写回 `visible_fields` 即恢复，不用 `+form-questions-create` 重加；空列表隐藏全部；写入隐藏成员会重显。
- 只能写 Form 成员；非成员用 `+form-questions-create`。
- 数组不能有重复项、不能带首尾空格，二者都被 CLI 本地拒绝（值原样发服务端，不 trim）。
- 回读须与提交一致。API 可能强制主字段置首；仅此差异以实际结果为准并报告，不重提；其他偏差不适用。
- 实际顺序须满足[显隐条件](#显隐条件visible_rule)的前序可见依赖，主字段置首不豁免。
- `+view-set-visible-fields --json` 是输入（string，`{"visible_fields":[...]}`），不带值报 `flag needs an argument`。
- `+form-questions-create`／`+form-questions-update` 的 `--json` 是输出格式简写（bool，等价 `--format json`），传值报错。

```bash
lark-cli base +view-get-visible-fields --base-token "<base_token>" --table-id "<table_id>" --view-id "<form_id>"
lark-cli base +view-set-visible-fields --base-token "<base_token>" --table-id "<table_id>" --view-id "<form_id>" \
  --json '{"visible_fields":["fldC","fldA","fldB"]}'
# 写后用 get 命令回读
```

## 题目属性协议

### 描述与换行

题目 `description` 在 JSON 中用 `\n`，不放真实换行。表单描述的 `+form-create`／`+form-update --description` 是裸字符串 flag：引号内 `\n` 是字面量，须传真实换行。

```bash
lark-cli base +form-questions-create --base-token "<base_token>" --table-id "<table_id>" --form-id "<form_id>" \
  --questions '[{"type":"text","title":"备注","description":"第一行\n第二行"}]'
# 正确：真实换行
lark-cli base +form-update --base-token "<base_token>" --table-id "<table_id>" --form-id "<form_id>" --description $'第一行\n第二行'
# 错误：落库成字面量「第一行\n第二行」
lark-cli base +form-update ... --description "第一行\n第二行"
```

写后回读；出现字面 `\n` 即失败并重写。两种写法不得混用。

### 显隐条件（visible_rule）

条件满足则显示；不传或 `conditions:[]` 则始终显示。条件必填=`required:true` + `visible_rule`；目标见 [Scene](../scenes/form.md#必填条件显示与输入范围)。

- 结构同视图 `filter`：`{logic?,conditions?}`；但 `field` 引用同表单题目名称或 ID（用 ID 避免重名），不是数据表字段。
- 只能引用排在当前题目前的可见题，不支持循环；引用题必须存在。创建按 `questions` 数组顺序，可引用同批更靠前的新题或已有题；更新按表单实际顺序。
- 更新传完整 `{logic,conditions}` 整体覆盖；保留须原样带回；`null`、省略或空 `conditions` 均使题目始终显示。
- `+form-questions-list` 原样返回每题 `visible_rule`；未设置返回 `null` 或空 `conditions`。

```json
{"logic":"and","conditions":[["q_001","==","启用"],["q_003",">=",1000]]}
```

顶层规则、operator、各类型 value 见 [shared-filter-tuple.md](shared-filter-tuple.md)。

### 输入范围限制（input_range_limit）

这是与 `required`、`visible_rule` 同级的题目配置，不是字段定义。形态 A 放同一对象；形态 B [先加入再更新](#形态-b已有字段题目)。清除传 `"input_range_limit":null`。

| type | 参数 | 规则 |
|---|---|---|
| `text_length` | `min_length`?、`max_length`? | 正整数，不接受 0；两侧都有时 `min_length <= max_length` |
| `number_range` | `min_value`?、`max_value`? | 至少一个有限数字；允许 0、负数；两侧有时 `min_value <= max_value` |
| `date_range` | `earliest`?、`latest`? | 至少一个；每侧是 `{"fixed_ms":整数毫秒}` 或 `{"dynamic":{"anchor":...,"offset_days":...}}`，二者互斥 |

未传的一侧边界表示不限制。以下是互相独立的最小 JSON：

```jsonc
{"type":"text_length","min_length":1,"max_length":100}
{"type":"number_range","min_value":0,"max_value":100}
{"type":"date_range","earliest":{"dynamic":{"anchor":"today","offset_days":0}},"latest":{"dynamic":{"anchor":"today","offset_days":7}}}
{"type":"date_range","earliest":{"fixed_ms":1790784000000},"latest":{"fixed_ms":1791302400000}}
```

固定例按北京时间为 `2026-10-01 00:00:00`~`2026-10-07 00:00:00`，允许 10 月 1~7 日；`latest` 是 10-07 零点，非 10-08。

硬规则：

- 不限的一侧省略键。边界传 `null` 被 CLI 拒绝：`--questions item N.input_range_limit.min_length must be a JSON number, not null`，请求不发出。`null` 只清整个限制。
- 字段名只用 snake_case，不接受别名；`min_length/max_length/min_value/max_value/fixed_ms` 必须是 JSON 数字，不得是字符串。
- `anchor` 仅取 `today/monday/friday/saturday/sunday/month_start/month_end`；`offset_days` 为可正可负的整数天。
- 两边界均为闭区间，`fixed_ms` 填当天 00:00:00，不 +1 天；最晚 9 月 30 日填 9-30 零点。填 10-01 零点或 9-30 23:59:59 都会多放一天；`earliest` 同理。
- 仅用户点名绝对日期时用 `fixed_ms`；“今天起、未来 N 天、本周内”等用随运行日期滚动的 `dynamic`。
- 两端均为 `fixed_ms` 时 CLI 比较先后，`earliest` 晚于 `latest` 会拒绝；一端为 `dynamic` 时不比较。
- `+form-questions-list` 回显限制，未配置返回 `null`；这是唯一验收证据。
- 更新时，保留限制须原样带回，不能靠省略；仅明确取消时传 `null`；其他属性遵循[全量覆盖](#全量覆盖与回读)。

相对日期只用 `anchor` + `offset_days`，不得发明“7 天前”等 anchor：

| 用户说法 | 写法 |
|---|---|
| 今天／昨天／明天 | `{"anchor":"today","offset_days":0}` / `-1` / `1` |
| 7 天前／后 | `{"anchor":"today","offset_days":-7}` / `7` |
| 30 天前／后 | `{"anchor":"today","offset_days":-30}` / `30` |
| 本周一／五／六／日 | `monday/friday/saturday/sunday` + `offset_days:0`；自然周周一始、周日止 |
| 月初／月末 | `month_start/month_end` + `offset_days:0` |

| 产品限制 | 边界 |
|---|---|
| 文本字数 | 最小下限 1，最大上限 100000 |
| 数字范围 | 可负、可小数；缺省一侧即不限 |
| 日期范围 | 只到日，不支持时分秒 |

更新范围时执行 list → update（带回 `title/required` 等）→ list；末次回读中范围符合要求且标题未变才验收。
