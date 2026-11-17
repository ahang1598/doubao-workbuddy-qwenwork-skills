# 表单题目操作与配置协议

## 目录

- [创建或复用题目](#创建或复用题目form-questions-create)（含 [电话号码题](#电话号码题)、[超链接、公式、查找引用、签字题](#超链接公式查找引用签字题)）
- [更新题目](#更新题目form-questions-update)
- [删除题目](#删除题目form-questions-delete)
- [可见题目与排序](#可见题目与排序)
- [题目属性协议](#题目属性协议)

题目来源、标题保护、目标属性与数据保护范围见 [Form Scene](../scenes/form.md#共同约束与收集项核对)。
题目属性更新不改变题序；重排使用 [可见题目与排序](#可见题目与排序)。

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

每个对象二选一：形态 A 新建字段题目；形态 B 复用已有字段。基础 `type` 仅有 `text`、`number`、`select`、`datetime`、`user`、`attachment`、`location`、`formula`（公式）、`lookup`（查找引用）。

| 边界 | 规则 |
|---|---|
| 基础 `type` | 只填上述小写值；不得填 `Email`、`Currency`、`SingleLink` 等 UI 类型名。`phone`、`url` 是仅用于新建题目的兼容别名，分别展开为 `text` + 对应样式 |
| 专用样式题 | 用户明确要求电话样式时用 `text` + `style.type=phone`；超链接、签字按业务语义使用 `url`、`signature`，写法与约束见对应小节 |
| 已确认不支持的样式 | 文本的 `email`、`barcode`，数字的 `currency`、`progress`；按 [题目样式与数字精度](#题目样式与数字精度) 直接改用普通文本／普通数字收集并说明，不先试探 |
| 基础类型之外的字段 | 已有 `link` 按 [Form Scene](../scenes/form.md#输入与业务关联) 复用；`checkbox`、`group_chat`、系统时间／人员、自动编号、按钮等不能通过形态 B 加入表单 |
| 两种请求 | 形态 A 可带字段定义；形态 B 只带字段标识和题目配置，不带 `type/style/options/multiple/name` |

未验证样式视为未知；本地校验通过不代表服务端接受。主档关联见 [Form Scene](../scenes/form.md#输入与业务关联)：选择主档对象时复用真实 Link；不得用文本、URL 或独立单选代替记录关系。

#### 形态 A：新建字段题目

在数据表中新建字段，返回的 question `id` 即新字段 `field_id`；显式传 `title` 和 `type`。

| 字段 | 必填 | 规则 |
|---|---|---|
| `title` | 是 | 问题标题（字段名） |
| `type` | 是 | 上述基础类型之一；电话默认 `text`，明确要求电话样式时加 `style.type=phone`（兼容别名 `phone`）；超链接、签字按业务语义使用 `url`、`signature` |
| `description` | 否 | 纯文本或 Markdown 链接，如 `[文本](https://example.com)` |
| `required` | 否 | true/false |
| `option_display_mode` | 否 | 仅 `select`：`0`=下拉，`1`=纵向（默认），`2`=横向 |
| `multiple` | 否 | `select`/`user` 是否多选（bool） |
| `options` | 否 | 仅 `select`：`[{"name":"选项1","hue":"Blue"}]`；hue=`Red/Orange/Yellow/Green/Blue/Purple/Gray` |
| `style` | 否 | 见[样式协议](#题目样式与数字精度) |
| `expression` | `formula` 必填 | 公式表达式，语法与 `+field-create` 的 formula 相同 |
| `from` / `select` / `where` | `lookup` 必填 | 查找引用定义，写法与 `+field-create` 的 lookup 相同 |
| `aggregate` | 否 | `lookup` 的聚合方式，省略默认 `raw_value`，取值与 `+field-create` 的 lookup 相同 |
| `visible_rule` | 否 | 见[显隐条件](#显隐条件visible_rule) |
| `input_range_limit` | 否 | 字数、数值或日期范围，见[输入范围](#输入范围限制input_range_limit)；专用 Phone、超链接、签字、公式、查找引用题不支持 |

#### 形态 B：已有字段题目

把上述基础类型的已有字段加入表单；不建字段、不改记录。表里已有的电话号码、超链接、签字、公式、查找引用字段也可以加入，或把被隐藏的这类题目恢复显示，约束同新建，见「超链接、公式、查找引用、签字题」的共同约束；`Email`、`Barcode`、`Currency`、`Progress` 等不支持的样式不能通过该形态加入。用于恢复 `--keep-field` 移出的题目或补充已有字段。

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
- 形态 B 需要输入范围时：先加入表单，使用创建响应中的题目 ID，再用 `+form-questions-update` 传 `input_range_limit`，并按[全量覆盖](#全量覆盖与更新基线)带回其他属性；已是成员的题目直接更新。形态 A 的限制随创建一次提交。

### 题目样式与数字精度

| 类型 | `style` | 规则 |
|---|---|---|
| `text` | `{"type":"plain"}` / `phone` / `url` | `plain` 普通文本；`phone` 创建真实电话号码字段，返回统一为 `type:text` + `style.type:phone`；`url` 为超链接题，底层字段为超链接（Url） |
| `number` | `{"type":"plain","precision":0}` 或 `precision:2` | `precision` 是小数位数，按要求选择 |
| `number` 评分 | `{"type":"rating","icon":"star","min":1,"max":5}` | icon=`star/heart/thumbsup/fire/smile/lightning/flower/number` |
| `datetime` | `{"format":"yyyy/MM/dd"}` | format=`yyyy/MM/dd`、`yyyy/MM/dd HH:mm`、`MM-dd`、`MM/dd/yyyy`、`dd/MM/yyyy` |
| `attachment`（签字） | `{"type":"signature"}` | 签字题；不传 `style` 为普通附件题 |

数字完整协议见 [number 配置](field-config.md#number-字段)。

**已确认不支持的样式，新建题目按普通类型收集；已有字段按样式保护处理**：

- 邮箱（`email`）、条码（`barcode`）不能作为表单题目，已有的 `Email` / `Barcode` 字段也不能直接加入表单。用户要求收集这类信息时，直接建不带 `style` 的普通文本题收集，并在答复中说明表单不支持该样式、不做格式校验；不先发请求试探。已有 `Email` / `Barcode` 字段的处理见 [Scene 的样式恢复](../scenes/form.md#样式拒绝后的恢复)。
- 货币（`currency`）和进度（`progress`）不是表单支持的题型（新建会被拒，`800010529`）。用户要求货币／进度格式时，建 `plain` 数字题（按需设 `precision`），并说明表单里只能按普通数字收集、无法显示货币符号或进度条。已有 `Currency` / `Progress` 字段的处理见 [Scene 的样式恢复](../scenes/form.md#样式拒绝后的恢复)。

**禁止绕过题型限制**：不要先用 `+field-create` 建出表单不支持的字段（`email` / `barcode` 样式文本、`currency` / `progress` 数字），再加入表单或用 `+form-questions-update` 改标题来绕过；也不要建好题目后再用 `+field-update` 把题目的底层字段改成这些样式。有的表单会把表里新建的字段自动显示成题目，绕过后得到的仍是表单不支持的题型，等同违规交付。

### 电话号码题

电话信息默认用普通 `text`。用户明确要求专用电话样式时，规范形态是 `{"type":"text","style":{"type":"phone"}}`；`{"type":"phone"}` 仅作为兼容别名。若别名同时携带 `plain`、`email`、`url`、`barcode` 或未知 style，整批请求会在写入前失败。

用户明确要求的电话号码题**不适用**下方 [样式拒绝后的恢复](#样式拒绝后的恢复)：创建失败时不得静默去掉 style，也不得先把已有 Phone 字段改为 plain 再加入表单。服务端未就绪或返回不支持时，如实报告错误。

专用 Phone 题不支持 `input_range_limit`（字数／位数限制），号码字符由提交链路校验。用户明确要求专用 Phone 且同时要求位数限制时，保留 Phone 样式、不写 `input_range_limit`，并说明该限制无法配置；不得为了加限制改型。普通 `text` 电话题仍按普通文本范围协议处理。

### 超链接、公式、查找引用、签字题

**超链接**

- 写法：`{"type":"text","style":{"type":"url"},"title":"作品链接"}`，或别名 `{"type":"url","title":"作品链接"}`（不传 `style` 时自动展开为 `text` + `url`）。底层字段类型为超链接（Url）。
- 别名 `url` 不能再带非 `url` 的 `style`，例如 `{"type":"url","style":{"type":"plain"}}`：冲突时**整批拒绝**，同批其他合法题目也不会创建，修正后整批重发。
- 题目语义是链接／网址／主页时一律建超链接题。用户的附加要求超链接题做不到时（如字数限制、要提交一个不合法的链接），也**不能为了满足它而改建普通文本题**：照常建超链接题，并说明该要求无法设置／该链接会被拒；要提交不合法链接时，提交前指出并向用户确认，或照提交并如实报告被拒。

**公式（只读计算题）**

- 写法：`{"type":"formula","title":"总价","expression":"[单价]*[数量]"}`。`expression` 语法与 `+field-create` 的 formula 完全相同，写之前读 [公式表达式](field-formula-expression.md)。
- 表达式编译失败返回 `800010221`（validation_error），整批不创建任何字段。
- 表达式引用的字段必须**已存在于表中**。同一批新建的题目不能被本批公式引用：先调用一次创建被引用的题目，再单独调用一次创建公式题。
- 填写人答完被引用的题后，本题据此实时算出并在问卷上显示结果。表达式可引用排在前面的题，包括查找引用题查出的值；需要其他表的数据时，先用查找引用题取回，或在表达式中跨表筛选（如 `[购买记录].FILTER(CurrentValue.[手机号]=[手机号]).[金额].SUM()`）。

**查找引用（只读计算题）**

- **先确认来源存在**：`from` 指定的来源表或 `select` 字段在 Base 里不存在时，停下来告诉用户并确认来源；不要自行新建来源表，更不要编造示例数据去“凑”出查找结果。只有用户明确要求新建来源表并给出数据时才建。来源表不存在返回 `800030104`，来源表字段不存在返回 `800030201`。
- 写法：`{"type":"lookup","title":"部门负责人","from":"部门表","select":"负责人","where":{"logic":"and","conditions":[["部门名称","==",{"type":"field_ref","field":"所在部门"}]]}}`。`from` / `select` / `where` / `aggregate` 与 `+field-create` 的 lookup 写法完全一致，见 [查找引用配置](field-lookup-config.md)；`aggregate` 可省略，默认 `raw_value`。
- `where` 至少一个条件。条件第一个元素是**来源表**（`from`）的字段；`{"type":"field_ref","field":...}` 引用的是**当前表**的字段，通常是本表单里排在前面的另一道题，填写人答完那道题后，本题据此实时查出值。`empty` / `non_empty` 条件可省略比较值，写成二元组。
- 被 `field_ref` 引用的当前表字段必须**已存在**；同一批新建的题目不能被引用，需先建被引用题，再单独调用一次建查找引用题。

**签字**

- 写法：`{"type":"attachment","style":{"type":"signature"},"title":"本人签字","required":true}`。
- 填写时签名以 PNG 图片提交，且只能使用用户提供的签名图片，提交方式见 [签字题提交](form-fill.md#签字题)。

**共同约束**

- 公式、查找引用是只读计算题，填写人不作答：
  - 设 `required:true` 会被拒（`800010541`），`+form-questions-create` 与 `+form-questions-update` 都一样。
  - 不能被其他题目的 `visible_rule` 引用（`800010542`）。
- 签字题被其他题目的 `visible_rule` 引用时，只能用 `empty` / `non_empty`；用 `==` 带值会被拒（`800010506`）。
- 四种题型都不支持 `input_range_limit`，传了会报错。
- 这四种题型及用户明确要求的专用 Phone 题创建被拒时，**如实报告错误码和原因**，按报错修正后重试；不得静默改型，也不得用字段命令绕过表单接口。
- 表单题目接口的业务错误码在 CLI 输出里可能被归一成 `code: 1`，判断原因以 `message` / `hint` 为准；本节写的错误码用于对照服务端日志。

### 样式拒绝后的恢复

| 情形 | 动作 |
|---|---|
| 触发 | 基础类型题目带非默认 `style`，且 schema 或具体错误确认不接受。缺参数、未知属性、权限、超时、网络错误按原原因处理 |
| `number` + `plain` 失败 | 不删 `style`；保留所需 `precision` 并处理实际错误；精度无法满足则报告未完成。用户明确要求的电话、超链接、签字样式不静默回退；`email` / `barcode` / `currency` / `progress` 已确认不支持，默认按普通类型收集 |
| 只有 `invalid_request`、`N issues` 等泛错 | 不足以判定样式不支持；保留错误，核对形态和错误路径；无法定位则报告受阻，不删整批 `style` 试探 |
| 同时出现另一形态的 `use_existing_field` / `field_id` | 这是 union 报错，不据此切换形态；核对本次形态和错误路径 |
| 形态 A 拒绝 | 核请求是否符合原目标类型、样式；不为通过校验删除有业务语义的 `style`。明确能力拒绝则保留缺项并报告未完成；未知／部分成功先回查，不整批重放 |
| 形态 B 拒绝 | 保留原字段 ID、类型与样式，不为补题自动调用 `+field-update` 改成 plain，也不以新建同义字段替代；明确授权的样式修改另交 Field；核成员状态和请求，正确请求仍被明确拒绝则报告该项未完成 |
| 恢复预算 | 仅参数／请求错误按真实原因定向修正并复验，沿用主入口预算；明确能力拒绝不走样式降级或同请求反复重试 |

样式变更授权、能力降低、未完成项见 [Scene](../scenes/form.md#样式拒绝后的恢复)。

```bash
# 形态 A；同批显隐条件可引用更靠前的新题
lark-cli base +form-questions-create --base-token "<base_token>" --table-id "<table_id>" --form-id "<form_id>" \
  --questions '[{"type":"select","title":"状态","options":[{"name":"启用","hue":"Blue"}]},{"type":"number","title":"金额","required":true,"visible_rule":{"logic":"and","conditions":[["状态","==","启用"]]},"input_range_limit":{"type":"number_range","min_value":0}}]'
```

更多题型示例（均用 `+form-questions-create`，公共参数同上）：

```bash
# 用户明确要求专用 Phone 时的写法（兼容别名 {"type":"phone","title":"联系电话"}）
lark-cli base +form-questions-create --base-token "<base_token>" --table-id "<table_id>" --form-id "<form_id>"   --questions '[{"type":"text","style":{"type":"phone"},"title":"联系电话","required":true}]'

# 添加超链接题（text + url 样式；等价别名写法 {"type":"url","title":"作品链接"}）
lark-cli base +form-questions-create --base-token "<base_token>" --table-id "<table_id>" --form-id "<form_id>"   --questions '[{"type":"text","style":{"type":"url"},"title":"作品链接"}]'

# 添加签字题（attachment + signature 样式）
lark-cli base +form-questions-create --base-token "<base_token>" --table-id "<table_id>" --form-id "<form_id>"   --questions '[{"type":"attachment","style":{"type":"signature"},"title":"本人签字","required":true}]'

# 添加公式题（只读计算题；[单价]、[数量] 必须是表里已存在的字段）
lark-cli base +form-questions-create --base-token "<base_token>" --table-id "<table_id>" --form-id "<form_id>"   --questions '[{"type":"formula","title":"总价","expression":"[单价]*[数量]"}]'

# 添加查找引用题（只读计算题；按本表「所在部门」到「部门表」查出负责人，「所在部门」必须已存在）
lark-cli base +form-questions-create --base-token "<base_token>" --table-id "<table_id>" --form-id "<form_id>"   --questions '[{"type":"lookup","title":"部门负责人","from":"部门表","select":"负责人","where":{"logic":"and","conditions":[["部门名称","==",{"type":"field_ref","field":"所在部门"}]]}}]'
```

形态 B 的 `--questions` 最小对象：`[{"use_existing_field":true,"field_id":"fldOwner"}]`。

创建／更新响应：

```json
{"ok":true,"data":{"items":[{"id":"q_001","title":"状态","required":true}]}}
```

## 更新题目（+form-questions-update）

参数同创建：`--base-token`、`--table-id`、`--form-id`、`--questions <json>`（最多 10 个）、`--format`、`--as`、`--dry-run`。

### 全量覆盖与更新基线

- 本命令全量覆盖，不是 patch；未带属性回落默认值，空字符串／`null`／空数组写空。
- 更新前用 `+form-questions-list` 读完整配置，将要保留的属性原样带回。只传 `{"id":"q_002","title":"新标题"}` 会清 `description`、使 `required=false`、清 `visible_rule`。
- 仅在用户明确要求时传空值：`description:""` 清描述；`visible_rule:null` 或 `conditions:[]` 清条件；`input_range_limit:null` 清范围。
- 更新不改题序；响应 `questions` 只含本次题目且不代表题序；请求排列不改变实际顺序。题序见[下节](#可见题目与排序)。

### 更新请求与属性默认值

每个对象必须含 `id`，表示目标完整配置。公式、查找引用、签字题的必填与显隐条件限制见本页「超链接、公式、查找引用、签字题」的共同约束。

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

- 全量写入前用 `+view-get-visible-fields` 取当前列表，结果在 `data.visible_fields`。基线和写入里的字段可能是 ID 也可能是名称：先用可信的 `+field-list` 结果建立 ID ↔ 字段名映射，统一后再构造集合与顺序，不直接混用名称数组和 ID 数组，也不把自定义题目标题当字段名；同名或无法唯一映射时报告受阻。隐藏成员 ID 从题目 list 取，题目列表只对照成员和属性，不证明题序。
- 数组整体覆盖集合和顺序；只传移动题会隐藏其余题。被省略的题仍是成员，写回 `visible_fields` 即恢复，不用 `+form-questions-create` 重加；空列表隐藏全部；写入隐藏成员会重显。
- 已有 Link 可按 [关联流程](../scenes/form.md#输入与业务关联) 将原字段 ID 加入完整可见集合并回读；其他非成员先用 `+form-questions-create` 加入表单。
- 数组不能有重复项、不能带首尾空格，二者都被 CLI 本地拒绝（值原样发服务端，不 trim）。
- API 可能强制主字段置首；响应缺少最终顺序、后续操作依赖实际顺序或用户明确要求核验时，读取实际顺序。
- 实际顺序须满足[显隐条件](#显隐条件visible_rule)的前序可见依赖，主字段置首不豁免。
- `+view-set-visible-fields --json` 是输入（string，`{"visible_fields":[...]}`），不带值报 `flag needs an argument`。
- `+form-questions-create`／`+form-questions-update` 的 `--json` 是输出格式简写（bool，等价 `--format json`），传值报错。

```bash
lark-cli base +view-get-visible-fields --base-token "<base_token>" --table-id "<table_id>" --view-id "<form_id>"
lark-cli base +view-set-visible-fields --base-token "<base_token>" --table-id "<table_id>" --view-id "<form_id>" \
  --json '{"visible_fields":["fldC","fldA","fldB"]}'
# 响应缺少最终顺序或用户明确要求时再用 get 命令读取
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

提交前按参数类型使用正确换行编码；只有响应或后续读取出现字面 `\n` 时才修正。两种写法不得混用。

### 显隐条件（visible_rule）

以下维护 `visible_rule` 的请求形状。`visible_rule` 决定是否显示，`required` 决定显示后的题目是否必须作答，两项分别按 [Scene 的属性决策](../scenes/form.md#必填条件显示与输入范围) 确定。

只有业务允许条件不满足时隐藏题目，才能用 `required:true` 加 `visible_rule` 表达“出现时必填”；只要求条件显示不意味着必须作答。若要求题目始终可见、仅在某条件下必填，这个组合不等价：先核对当前入口能否表达该校验，无法表达时如实列出缺口，不能擅自改成隐藏、一直必填或一直选填，也不能用填写声明代替强制校验。

- 结构同视图 `filter`：`{logic?,conditions?}`；但 `field` 引用同表单题目名称或 ID（用 ID 避免重名），不是数据表字段。
- 只能引用排在当前题目前的可见题，不支持循环；引用题必须存在。创建按 `questions` 数组顺序，可引用同批更靠前的新题或已有题；更新按表单实际顺序。
- 更新传完整 `{logic,conditions}` 整体覆盖；保留须原样带回；`null`、省略或空 `conditions` 均使题目始终显示。
- `+form-questions-list` 原样返回每题 `visible_rule`；未设置返回 `null` 或空 `conditions`。

```json
{"logic":"and","conditions":[["q_001","==","启用"],["q_003",">=",1000]]}
```

顶层规则、operator、各类型 value 见 [shared-filter-tuple.md](shared-filter-tuple.md)。

### 输入范围限制（input_range_limit）

这是与 `required`、`visible_rule` 同级的题目配置，不是字段定义。只适用于普通文本（`text_length`）、普通数字（`number_range`）、日期（`date_range`）题；专用 Phone、超链接、签字、公式、查找引用题不支持。用户对这些题提范围要求时保持原题型并说明限制；普通 `text` 电话题按普通文本处理。形态 A 放同一对象；形态 B [先加入再更新](#形态-b已有字段题目)。清除传 `"input_range_limit":null`。

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
- `+form-questions-list` 回显限制，未配置返回 `null`；更新前需要保留现有限制、响应缺少最终设置或用户明确要求核验时再读取。
- 更新时，保留限制须原样带回，不能靠省略；仅明确取消时传 `null`；其他属性遵循[全量覆盖](#全量覆盖与更新基线)。

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

专用 Phone 题可以更新标题、描述、必填和显隐条件，也可以从隐藏状态恢复；其 `type:text` + `style.type:phone` 由服务端回显，不需要在更新对象里重传。专用 Phone 不支持 `input_range_limit`，普通 `text` 电话题按普通文本更新协议处理。

更新范围时先 list 取得完整题目，再 update（带回 `title/required` 等）。响应缺失、结果未知或用户明确要求核验时再读取。
