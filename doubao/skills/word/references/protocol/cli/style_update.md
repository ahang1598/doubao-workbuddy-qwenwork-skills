---
keyword: style_update
---

**功能**：修改样式定义；包含 dry-run、plan token 与提交契约

# 修改 Canvas 样式定义

通用写入参数见 `local-update`。样式 ID、关系和指纹取自当前 CLI 的结构化读取结果。修改样式定义需要 `style_usage` 返回的指纹。

样式读写的结果在 `data.command_result`，返回对象字段而非正文 XML。

---

## `style_update`：修改样式定义

`changes` 不能为空，且每个 `property` 只能出现一次。下方示例展示传给样式 option 的对象。

### 当前可更新范围

`property` 使用 `<scope>.<属性名>`；可写范围如下：

| scope | 可写属性 |
|---|---|
| `paragraph` | `align`、`bidi`、`contextual-spacing`、`spacing-before`、`spacing-after`、`spacing-before-lines`、`spacing-after-lines`、`spacing-before-auto`、`spacing-after-auto`、`line-indent`、`right-indent`、`start-indent`、`end-indent`、`first-line-indent`、`hanging-indent`、`line-height`、`page-break-before`、`keep-next`、`keep-lines`、`widow-control`、`tabs`、`shading-fill`、`shading-pattern`、`shading-foreground-color`、`border-top`、`border-right`、`border-bottom`、`border-left`、`border-between` |
| `text` | `bold`、`italic`、`underline`、`line-through`、`emphasis-mark`、`vertical-align`、`text-color`、`background-color`、`font-size`、`font-family-ascii`、`font-family-east-asia`、`font-family-h-ansi`、`font-family-cs`、`font-family-ascii-theme`、`font-family-east-asia-theme`、`font-family-h-ansi-theme`、`font-family-cs-theme`、`font-hint`、`shading-fill`、`shading-pattern`、`shading-foreground-color`、`character-scale`、`character-spacing` |
| `table` | `width`、`align`、`shading-fill`、`shading-pattern`、`shading-foreground-color`、`indent`、`layout`、`cell-spacing`、`border-top`、`border-right`、`border-bottom`、`border-left`、`border-inside-h`、`border-inside-v`、`cell-padding-top`、`cell-padding-right`、`cell-padding-bottom`、`cell-padding-left` |
| `row` | `height`、`height-rule`、`cant-split`、`repeat-header`、`align` |
| `cell` | `width`、`no-wrap`、`background-color`、`vertical-align`、`border-top`、`border-right`、`border-bottom`、`border-left`、`border-inside-h`、`border-inside-v`、`border-tl2br`、`border-tr2bl`、`cell-padding-top`、`cell-padding-right`、`cell-padding-bottom`、`cell-padding-left` |

style type 限制：

- paragraph style 只接受 `paragraph.*`、`text.*`；
- character style 只接受 `text.*`；
- table style 接受 `paragraph.*`、`text.*`、`table.*`、`row.*`、`cell.*`；
- numbering style、`origin=builtin_fallback|unresolved` 和不存在的 style 不可更新。

当前客户端支持的属性以结构化返回的 `property_schema` 为准。`text.emphasis-mark` 对应 `docxxml-attributes-v8`。

值域与成组规则：

- `action=set` 必须带 `value`；`action=clear` 不带 `value`，只删除该 style 的 direct 声明并恢复继承。一个请求内 property 必须唯一。
- `text.emphasis-mark=none|dot|comma|circle|underDot`；`set` 带五值之一。`set` 为 `none` 显式阻断继承，`clear` 不带 value，只删除本样式 direct 声明并恢复继承；二者均通过既有 dry-run/plan token。与 `text.italic` 独立。主 Story 的受支持样式修订仍沿用既有领域修订，不扩大修订边界。D013 记录的样式着重号保存重开丢失及修订自动保真取证缺口仍未修复，提交成功或模型回读不能证明 DOCX 已持久化。
- boolean：paragraph 的 `bidi/contextual-spacing/spacing-*-auto/page-break-before/keep-next/keep-lines/widow-control`、text 的 `bold/italic`、row 的 `cant-split/repeat-header`、cell 的 `no-wrap`。
- `paragraph.align=left|center|right|justify|distribute`；`table/row.align=left|center|right`；`cell.vertical-align=top|middle|bottom`。
- paragraph 物理 spacing/indent、table `indent/cell-spacing`、row height 使用非负 `<n>pt`；`start/end-indent` 仅接受 pt，`spacing-before/after-lines` 使用非负无单位行数；`text.character-spacing` 可为负 pt；`text.font-size` 必须可量化为正 half-point。
- `paragraph.line-height` 使用非负倍率字符串，或 `exact <n>pt` / `at-least <n>pt`。`first-line-indent` 与 `hanging-indent` 不得在同一请求同时出现。
- `paragraph.tabs` 使用按 position 升序的非空数组并整体替换本样式自有 stop：`{position:"<n>pt",align:"left|center|right|decimal|bar|clear",leader?:"none|dot|hyphen|underscore|middleDot"}`；position 非负、量化后唯一，`align=clear` 不带 leader。清除自有集合用 change 的 `action=clear`。
- `row.height` 与 `row.height-rule=auto|at-least|exact` 设置时必须成对出现；clear 任一项会同时清除两项，不能一项 set、另一项 clear。
- `text.line-through=none|single|double`、`text.vertical-align=baseline|superscript|subscript`；`text.underline` 为 `none|single|double|thick|dotted|dottedHeavy|dash|dashedHeavy|dashLong|dashLongHeavy|dotDash|dashDotHeavy|dotDotDash|dashDotDotHeavy|wave|wavyHeavy|wavyDouble`。
- `table/cell.width` 接受正 `<n>pt`、`0..100%`、`auto|nil`；`table.layout=fixed|autofit`。
- 四个 direct font family 必须为非空字符串；四个 theme font slot 只接受 `majorEastAsia|majorBidi|majorAscii|majorHAnsi|minorEastAsia|minorBidi|minorAscii|minorHAnsi`；`font-hint=default|eastAsia|cs`。
- `text-color`、shading color 和 `cell.background-color` 使用不透明 `rgb(R,G,B)`；`text.background-color` 仅接受 Word 可保存的 16 色：`rgb(0,0,0)`、`rgb(0,0,255)`、`rgb(0,255,255)`、`rgb(0,255,0)`、`rgb(255,0,255)`、`rgb(255,0,0)`、`rgb(255,255,0)`、`rgb(255,255,255)`、`rgb(0,0,128)`、`rgb(0,128,128)`、`rgb(0,128,0)`、`rgb(128,0,128)`、`rgb(128,0,0)`、`rgb(128,128,0)`、`rgb(128,128,128)`、`rgb(192,192,192)`。
- paragraph/text/table 的 `shading-pattern` 接受 `nil|clear|solid`、`pct<n>`（0..100）及 `diagCross|diagStripe|reverseDiagStripe|horzCross|horzStripe|vertCross|vertStripe|thinDiagCross|thinDiagStripe|thinReverseDiagStripe|thinHorzCross|thinHorzStripe|thinVertStripe`；`character-scale` 为 `1%..999%`。
- padding 使用 `auto` 或非负 `<n>pt`。border 使用 `none`，或 `style [<n>pt] [rgb(R,G,B)|auto]`，token 顺序不可交换；style 只接受 `single|thick|double|dotted|dashed|dotDash|dotDotDash|triple|thinThickSmallGap|thickThinSmallGap|thinThickThinSmallGap|thinThickMediumGap|thickThinMediumGap|thinThickThinMediumGap|thinThickLargeGap|thickThinLargeGap|thinThickThinLargeGap|wave|doubleWave|dashSmallGap|dashDotStroked|threeDEmboss|threeDEngrave|outset|inset`。

明确不可更新：

- `text.underline-color` 仅可读；通用 `font-family`、run border、`table.background-color`、numbering、theme 定义不在当前写入范围。
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

---

## 取得 plan_token 并提交

1. 传 `dry_run=true` 取得 `plan_token`，这一请求不带 `plan_token`。返回 `no_change=true` 时没有改动，也没有 `plan_token`，到此结束。
2. 提交时使用相同的文档、命令、参数、指纹和顶层 `--revision-id`，只把 `dry_run` 改成 `false` 并加上本次的 `plan_token`。文档或参数变化、`plan_token` 失效时，用当前数据重新取得 `plan_token`。
3. `data.command_result.applied=true` 和 `new_revision_id` 表示样式已在 Canvas 应用。文件保存由客户端处理。

提交已成功但回执丢失时，可在 `plan_token` 的 5 分钟有效期内用完全相同的请求取回原回执。请求仍在执行或结果不明时，先[处理原请求](../../workflows/canvas-doc-recovery.md)。
