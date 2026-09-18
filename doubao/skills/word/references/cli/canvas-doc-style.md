# 本地 Word：样式读取与受控写入

> 使用前须完整读取本页；未见末行「全文完」时，调整 offset 继续读取至该标记。

前置读取 [`canvas-doc-fetch.md`](canvas-doc-fetch.md)，需要写入时再读 [`canvas-doc-update.md`](canvas-doc-update.md)。样式 identity、关系和 fingerprint 只能来自当前 CLI 的结构化读取结果，不得从 DocxXML 标签名、显示名称或历史结果猜测。

本文仅描述 `lark-cli` 的公开接口：

- **返回格式**：样式读写均使用 `format=xml` 信封；查询结果位于结构化 `command_result`，不编码成 DocxXML。
- **调用边界**：`document_id`、`format`、`read_option`、`export_option`、`command_params` 是宿主内部字段，不属于 CLI 参数。禁止据此拼装请求或直调私有接口。
- **能力检查**：执行前运行 `docs +local-fetch --help` 或 `docs +local-update --help`；当前版本未显示的 scope、command 或 flag 视为未开放。

## 按目标读取

先确认当前构建的子命令帮助暴露所需参数，已核实的相同构建帮助可复用。只加载任务需要的查询，不固定先读全文正文：

| 目标 | 最小读取路径 |
|---|---|
| 从正文定位样式绑定 | 对目标范围使用可导出 block ID 的 detail，并加 `--export-style-context refs`，从 `data.command_result.style_context` 取得该 checkpoint 的 bindings、referenced styles 和 `styles_fingerprint`；layout 不支持此选项 |
| 已知 style ID，读取定义或计算后属性 | 直接查询 `style_catalog --style-ids`，按需选 `definition` 或 `computed`；无需先导出正文 |
| 修改样式定义 | 读取 `style_usage --include-descendants=true` 的完整分页结果；其中 `target_style` 已含目标定义和 computed 信息，同时返回所需的三类 fingerprints，无需重复查询同一目标的 catalog |
| 应用或清除段落样式 | 读取目标 `block_styles --style-detail computed`；set 还需目标 paragraph style 的 catalog computed 结果，clear 使用 block computed 返回的 fallback fingerprint |

所有写入 identity 与 `expected_*_fingerprint` 必须对应同一文档 checkpoint；跨查询或分页时核对读取版本一致。发生正文写入、协同变化或版本冲突后重新读取。顶层 `--revision-id` 必填，接受 `-1` 或非负安全整数，优先使用该 checkpoint 返回的具体 revision；语义见 [revision 规则](canvas-doc-update.md#revision-规则)。

### 查询参数

三个 scope 的结构化结果位于 `data.command_result`，使用以下样式专属参数，不混用普通 XML 的 `--detail` 或 export 参数：

| scope | 参数与取值 |
|---|---|
| `style_catalog` | `--style-detail summary\|definition\|computed`，默认 summary；`--style-types paragraph\|character\|table\|numbering` 和 `--style-ids` 支持逗号分隔或重复参数，不筛选时省略；`--cursor`、`--limit`，limit 默认 100、最大 500 |
| `style_usage` | 必填 `--style-id`；`--include-descendants=true` 包含 based_on 后代，默认 false；`--cursor`、`--limit`，limit 默认 200、最大 1000；不接受 `--style-detail` |
| `block_styles` | 必填 `--block-id`；`--style-scope self\|subtree`，默认 self；`--style-detail summary\|computed`，默认 summary；仅 subtree 可传 `--cursor`、`--limit`，limit 默认 200、最大 1000；self 禁止分页参数 |

```bash
lark-cli docs +local-fetch --doc "<token>" \
  --scope style_catalog --style-ids "<style_id>" --style-detail computed

lark-cli docs +local-fetch --doc "<token>" \
  --scope style_usage --style-id "<style_id>" --include-descendants=true

lark-cli docs +local-fetch --doc "<token>" \
  --scope block_styles --block-id "<block_id>" --style-detail computed
```

分页时把 `data.command_result.next_cursor` 原样传给下一次 `--cursor`，保持查询条件不变，读取至 `truncated=false`。`style_update.expected_usage_fingerprint` 必须来自同一 checkpoint、`include_descendants=true` 的完整影响集合；不能使用默认 exact-only 查询、单页 items 或客户端自行计算的 hash。各页 fingerprint 相同也不代表已读取完整影响面。

## `style_update`：修改样式定义

只允许样式 manifest 中的可读写 leaf；`changes` 非空，同一 property 不得重复。当前 CLI 要求显式提供 boolean `dry_run`；预检传 `dry_run=true`，提交传 `dry_run=false` 和对应 `plan_token`。先确认 `docs +local-update --help` 已显示 `style_update` 及样式 option 参数，再把以下对象作为该 option 的值传入：

### 当前可更新范围

`property` 使用 `<scope>.<canonical-attr>`。当前共开放 59 个 R/W leaf：

| scope | 可写属性 |
|---|---|
| `paragraph` | `align`、`spacing-before`、`spacing-after`、`spacing-before-auto`、`spacing-after-auto`、`line-indent`、`first-line-indent`、`hanging-indent`、`line-height`、`page-break-before`、`keep-next`、`keep-lines`、`widow-control` |
| `text` | `bold`、`italic`、`text-color`、`background-color`、`font-size`、`font-family-ascii`、`font-family-east-asia`、`font-family-h-ansi`、`font-family-cs`、`font-family-ascii-theme`、`font-family-east-asia-theme`、`font-family-h-ansi-theme`、`font-family-cs-theme`、`font-hint`、`shading-fill`、`shading-pattern`、`shading-foreground-color`、`character-scale`、`character-spacing` |
| `table` | `align`、`border-top`、`border-right`、`border-bottom`、`border-left`、`border-inside-h`、`border-inside-v`、`cell-padding-top`、`cell-padding-right`、`cell-padding-bottom`、`cell-padding-left` |
| `row` | `height`、`height-rule` |
| `cell` | `background-color`、`vertical-align`、`border-top`、`border-right`、`border-bottom`、`border-left`、`border-inside-h`、`border-inside-v`、`border-tl2br`、`border-tr2bl`、`cell-padding-top`、`cell-padding-right`、`cell-padding-bottom`、`cell-padding-left` |

style type 限制：

- paragraph style 只接受 `paragraph.*`、`text.*`；
- character style 只接受 `text.*`；
- table style 接受 `paragraph.*`、`text.*`、`table.*`、`row.*`、`cell.*`；
- numbering style、`origin=builtin_fallback|unresolved` 和不存在的 style 不可更新。

值域与成组规则：

- `action=set` 必须带 `value`；`action=clear` 不带 `value`，只删除该 style 的 direct 声明并恢复继承。一个请求内 property 必须唯一。
- paragraph/text boolean：`spacing-before-auto`、`spacing-after-auto`、`page-break-before`、`keep-next`、`keep-lines`、`widow-control`、`bold`、`italic`。
- `paragraph.align=left|center|right|justify|distribute`；`table.align=left|center|right`；`cell.vertical-align=top|middle|bottom`。
- paragraph spacing/indent、row height 使用非负 `<n>pt`；`text.character-spacing` 可使用负 `<n>pt`；`text.font-size` 必须是可量化为正 half-point 的 `<n>pt`。
- `paragraph.line-height` 使用非负倍率字符串，或 `exact <n>pt` / `at-least <n>pt`。`first-line-indent` 与 `hanging-indent` 不得在同一请求同时出现。
- `row.height` 与 `row.height-rule=auto|at-least|exact` 设置时必须成对出现；clear 任一项会同时清除两项，不能一项 set、另一项 clear。
- 四个 direct font family 必须为非空字符串；四个 theme font slot 只接受 `majorEastAsia|majorBidi|majorAscii|majorHAnsi|minorEastAsia|minorBidi|minorAscii|minorHAnsi`；`font-hint=default|eastAsia|cs`。
- `text-color`、shading color 和 `cell.background-color` 使用不透明 `rgb(R,G,B)`；`text.background-color` 仅接受 Word 可保存的 16 色：`rgb(0,0,0)`、`rgb(0,0,255)`、`rgb(0,255,255)`、`rgb(0,255,0)`、`rgb(255,0,255)`、`rgb(255,0,0)`、`rgb(255,255,0)`、`rgb(255,255,255)`、`rgb(0,0,128)`、`rgb(0,128,128)`、`rgb(0,128,0)`、`rgb(128,0,128)`、`rgb(128,0,0)`、`rgb(128,128,0)`、`rgb(128,128,128)`、`rgb(192,192,192)`。
- `text.shading-pattern` 只接受 `clear|solid|pct5|pct10|pct20|pct25|pct30|pct40|pct50|pct60|pct70|pct75|pct80|pct90|diagStripe|reverseDiagStripe|horzStripe|vertStripe|thinDiagStripe|thinReverseDiagStripe|thinHorzStripe|thinVertStripe`；`character-scale` 为 `1%..999%`。
- padding 使用 `auto` 或非负 `<n>pt`。border 使用 `none`，或 `style [<n>pt] [rgb(R,G,B)|auto]`，token 顺序不可交换；style 只接受 `single|thick|double|dotted|dashed|dotDash|dotDotDash|triple|thinThickSmallGap|thickThinSmallGap|thinThickThinSmallGap|thinThickMediumGap|thickThinMediumGap|thinThickThinMediumGap|thinThickLargeGap|thickThinLargeGap|thinThickThinLargeGap|wave|doubleWave|dashSmallGap|dashDotStroked|threeDEmboss|threeDEngrave|outset|inset`。

明确不可更新：

- `text.underline-color` 仅可读；underline/strike 开关、通用 `font-family`、run border、table width/background、paragraph border/shading、numbering、tabs、theme 定义均不在当前写入范围。
- `conditional_formats.*` 当前整体关闭；不能因 table style 支持五个普通 scope 就推断条件区域可写。
- 不支持创建/删除 style，修改 style ID/type、`based_on/next/link`、behavior、default style map、computed 或 provenance。

```json
{
  "style_id": "<style_id>",
  "expected_definition_fingerprint": "<from_fetch>",
  "expected_effective_fingerprint": "<from_fetch>",
  "expected_usage_fingerprint": "<from_fetch>",
  "changes": [
    {"property": "paragraph.align", "action": "set", "value": "center"},
    {"property": "text.bold", "action": "clear"}
  ],
  "dry_run": true
}
```

调用时使用 `lark-cli docs +local-update --doc "<token>" --revision-id "<revision_id_from_same_fetch>" --command style_update --style-option @style-option.json`。

帮助未显示 `--revision-id` 或样式 option 时停止，不把 JSON 当作完整请求提交。dry-run 的 diff、impact、fingerprints 和 plan token 位于 `data.command_result`。

## `style_apply`：设置或清除段落样式绑定

目标固定为单个 block；当前 CLI 要求显式提供 `target.kind="block"`、`style_type="paragraph"` 和 boolean `dry_run`；预检传 `true`，提交传 `false` 和预检返回的 `plan_token`。`set` 需要 `style_id` 和 `expected_target_effective_fingerprint`；`clear` 需要 `expected_fallback_effective_fingerprint`，且禁止携带 set 专属字段。两者都必须携带 `expected_block_style_fingerprint`。

- 目标仅限当前文档中可达的单个正文文本段落、Heading 或列表项；不支持批量 target、table/numbering style apply 或 character exact-range apply。
- `set` 只能绑定已有、`origin=document` 的 paragraph style；`clear` 只删除显式 paragraph binding，并回退到 default paragraph style 或无样式。
- 两种操作都保留文本、直接格式、paragraph mark 和 numbering。直接格式可能遮蔽样式变化，此时 dry-run 返回 `DIRECT_FORMATTING_OVERRIDES_STYLE` 和 `visible_change_expected=false`。
- 非 no-op 操作遇到 character-style text range 的 effective projection 不完整时返回 `STYLE_RESOLUTION_INCOMPLETE`，不会带着不完整计算提交。

```json
{
  "target": {"kind": "block", "block_id": "<block_id>"},
  "style_type": "paragraph",
  "action": "set",
  "style_id": "<style_id>",
  "expected_block_style_fingerprint": "<from_fetch>",
  "expected_target_effective_fingerprint": "<from_fetch>",
  "dry_run": true
}
```

调用时使用 `lark-cli docs +local-update --doc "<token>" --revision-id "<revision_id_from_same_fetch>" --command style_apply --style-option @style-option.json`。

帮助未显示 `--revision-id` 或样式 option 时停止。dry-run 的 binding、effective diff、fingerprints 和 plan token 位于 `data.command_result`。

样式命令不带 XML `--content`。option 文件只包含上面列出的样式业务字段，不写 `document_id`、`format`、`revision_id`、`command` 或其他内部路由字段；必需的 revision ID 只能通过顶层 `--revision-id` 传入。

## 提交与持久化边界（必须遵守）

- 两个命令都必须先 dry-run：option 中 `dry_run=true` 时校验当前 fingerprints，顶层 `--revision-id` 优先使用同一读取 checkpoint 的具体值（也接受显式 `-1`，不免除基线与 fingerprint 检查）；CLI 返回结构化 diff/impact，有实际变化时返回短时 plan token，无变化时 token 为 `null`，且不产生 revision。
- dry-run option 禁止传 plan token。提交时复用完全相同的规范化 intent、guards 与 dry-run 使用的顶层 `--revision-id`，仅改为 `dry_run=false` 并加入本次返回的 `plan_token`；除下条“成功回执丢失”的幂等重放外，文档变化、token 缺失、过期或 payload 不同时重新 Fetch/dry-run，不复用旧 plan token。
- 同一提交已经成功但调用方丢失响应时，在 plan token 的 5 分钟有效期内用**完全相同**的 document、command、intent 和 guards 重放，可幂等取得已记录的成功回执而不重复提交；任一请求字段变化都必须拒绝。请求仍在运行或终态未知时先按 recovery 回读确认，不并发重发。
- 提交成功时 `data.command_result.applied=true` 并返回 `new_revision_id`；`plan_token` 归零。响应不暴露内部持久化阶段，也不要求出现持久化 warning。
- 保存由宿主正常保存链路处理。用户要求持久化、保存重开或最终文件交付时，必须等待保存完成并重新打开/回读验证后再宣称已保存；不能仅凭 `applied=true` 推断文件已落盘。
- no-op dry-run 返回 `no_change=true`、`plan_token=null`，不得提交；提交成功后重新读取 catalog/block styles 验证运行时结果。

===== 全文完 =====
