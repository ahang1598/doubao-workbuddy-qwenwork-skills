# 确定性检查助手

`scripts/briefing_checks.py` 可在叙述前检查结构化行情收益、涨跌广度、截止资格，以及可选的交付契结构造。它是可选算术与结构助手，不选择 `direct`、`brief` 或 `full`，也不替代来源核验或经济判断。

## 调用

- 文件输入：`python3 scripts/briefing_checks.py INPUT.json`
- 标准输入：`python3 scripts/briefing_checks.py -`
- 程序只从指定输入读取，在标准输出写一个 JSON 文档；不访问网络、不写文件。文件复核通过把**已重开的正文**放进输入完成，由程序计算哈希，而不是信任自报摘要。

## 输入契约

根对象允许：

- `as_of`：必填、非空且无首尾空白的 ISO 8601 日期时间字符串，必须有显式 UTC 偏移；`Z` 可表示 UTC。无偏移日期时间、仅日期、命名时区及表示未知偏移的 `-00:00` 不接受。
- `observations`：必填数组，可以为空，按输入顺序处理。
- `delivery_contract`：可省略。若出现则必须是对象，只允许下文字段。省略时行为与旧观察契约相同。

每个观察对象只允许：

- `id`：必填、非空且无首尾空白的字符串；数组内不得重复。
- `observed_at`：必填，时间格式与 `as_of` 相同。
- `available_at`：必填，时间格式与 `as_of` 相同。
- `quote`：可省略或为 `null`；对象形式必须且只包含 `last`、`previous_close`。两者均须为有限正数，布尔值不是数值。
- `breadth`：可省略或为 `null`；对象形式必须且只包含 `up`、`down`、`unchanged`、`total`。字段均须为非负整数，布尔值不是整数；三类数量之和必须等于正整数 `total`。

`delivery_contract` 只允许：

- `query_requirements`：可省略数组。每项只含 `name`（非空字符串，数组内不重复）、`status`（`present` / `unknown` / `missing`）。`status` 为 `present` 时不得出现 `missing` 字段，包括 `null`。为 `unknown` 或 `missing` 时必须有非空 `missing`，说明缺口。
- `clues`：可省略数组。每项只含 `id`（非空且不重复）、`horizon`（`intraday` / `multi_day` / `multi_week` / `quarter` / `unknown`）、`horizon_source`（`material` / `user_window` / `none`）。`horizon` 不是 `unknown` 时，`horizon_source` 不得为 `none`；`horizon` 为 `unknown` 时，`horizon_source` 必须为 `none`。
- `session_gap`：可省略或 `null`。`applicable` 为 `false` 时只允许 `applicable` 与非空 `skip_reason`，不得出现 `items`、`last_close_at`、`gap_kind` 或 `no_new_information`。`applicable` 为 `true` 时必须有 `last_close_at`（早于顶层 `as_of`）、`gap_kind`（`cross_day` 或 `closed_session`）和 `items` 数组。`cross_day` 要求上次收盘与 `as_of` 在收盘时区下日期不同。`no_new_information` 为 `true` 时 `items` 必须为空；否则必须非空。每条 `items` 只含 `info`、`first_visible_at`（ISO 8601 或字面量 `unknown`）、`status`、`priced_in`（`yes` / `no` / `unknown`）。非 `unknown` 的 `first_visible_at` 必须晚于 `last_close_at` 且不晚于 `as_of`。`priced_in` 为 `yes` 时，`first_visible_at` 不得为 `unknown`，且必须有 `expectation_evidence=true`。
- `metrics`：可省略数组。若非空，必须至少一项 `role=mainline`，且必须同时提供非空 `mainline_text`。每项只含 `name`、`formula`、`unit`、`forbidden_aliases`（非空字符串数组）、`role`（`mainline` / `supplemental`）。
- `mainline_text`：在存在非空 `metrics` 时必填。必须点名每一个 `role=mainline` 的 `name`；去掉空白并忽略大小写后，不得包含任一 `forbidden_aliases` 作为子串。
- `mainline_terms`：可省略非空字符串数组；出现时必须已有 `metrics`，并按同样的子串规则检查禁用别称。
- `ranking`：可省略或 `null`。`possible` 为 `false` 时只允许 `possible` 与空数组 `items`。`possible` 为 `true` 时必须有 `order`（`asc` / `desc`）、非空 `source_rows` 和非空 `items`。每条 `source_rows` 只含 `key`、`sort_value`（有限数，布尔不是数）、`display`；`key` 必须出现在 `display` 中，且 `sort_value` 必须按 `order` 单调。每条 `items` 只含 `label`、`claim_type`（`leader` / `laggard` / `strongest` / `weakest` / `other`）、`source`（`table` / `calculation` / `file`）、`value`、`row_index`、`place`。`place` 必须等于 `row_index+1`，并在条目间唯一；可排序时必须包含 `place=1`。`leader` / `strongest` 只能是第 1 名，`laggard` / `weakest` 只能是最后一行。`value` 必须等于绑定行的 `key` 或出现在其 `display` 中。`source=file` 时还必须有合法 `artifact_index`，且绑定行的 `display` 出现在对应重开正文中。若同时存在 `artifacts` 与可排序结果，每条 `summary_claims` 必须能绑定到某一 `source_rows.display`。
- `artifacts`：可省略数组。每项只含 `name`、`text`（已重开文件的完整正文）、`sha256`（对 `text` 的 UTF-8 SHA-256，64 位小写十六进制）、非空 `accepted_rows`、`summary_claims`。每一行和每一条摘要都必须是 `text` 的子串；程序会重算哈希，自报哈希不一致即失败。

所有数值必须来自当前任务材料。程序不补默认价格、样本数、时间、市场身份或默认要素清单。未知子对象应省略；禁止用 `null` 占住声明中不得出现的字段。

## 输出契约

成功输出包含原样返回的 `as_of` 和 `observations` 数组。每项包含：

- `id`：原观察标识。
- `eligibility`：布尔值。仅当 `observed_at` 和 `available_at` 都不晚于 `as_of` 时为 `true`。
- `reasons`：资格为真时为空数组；否则按顺序包含 `observed_at_after_as_of`、`available_at_after_as_of` 中适用的代码。
- `metrics.quote`：合格且输入有 `quote` 时为含 `return_pct` 的对象，否则为 `null`。计算式为 `(last / previous_close - 1) * 100`，不隐式舍入。
- `metrics.breadth`：合格且输入有 `breadth` 时为含 `up_share`、`down_share` 的对象，否则为 `null`。两者分别为 `up / total` 和 `down / total`。

若输入含 `delivery_contract`，成功输出原样回传通过校验的该对象，并增加 `passed` 为 `true`。省略该字段时输出不含它。未通过校验的输入不会得到 `passed=true`。

未来观察仍保留在输出中，但资格为假且两个指标对象均为 `null`。缺失的输入子对象也保持对应指标为 `null`。

malformed JSON、重复 JSON 键、未知或缺失字段、重复 `id`、歧义时间、非有限数、布尔数值及其他契约错误都会输出带 `error.type` 和 `error.message` 的 JSON，并以非零状态退出。程序不会部分接受无效输入。

## 能力限制

该助手验证输入形状、时间截止、算术一致性，以及交付契约的窗口、子串和回读绑定。它不能核实来源真实性、官方交易日历真伪、证券或合约身份、行情字段的经济含义或样本代表性。使用结果时仍须标明市场、字段、单位、基准、观察时间和证据状态。
