---
keyword: style_apply
---

**功能**：设置或清除段落、标题、列表项及单块字符范围的样式绑定

# 在 Canvas 应用样式

通用写入参数见 `local-update`。样式 ID、关系和指纹取自当前 CLI 的结构化读取结果。

样式读写的结果在 `data.command_result`，返回对象字段而非正文 XML。

---

## `style_apply`：设置或清除段落样式绑定

目标固定为单个 block；调用时显式传 `target.kind="block"`、`style_type="paragraph"` 和 `dry_run`，提交时设 `dry_run=false` 并带预检返回的 `plan_token`。`set` 需要 `style_id` 和 `expected_target_effective_fingerprint`；`clear` 需要 `expected_fallback_effective_fingerprint`，且禁止携带 set 专属字段。两者都必须携带 `expected_block_style_fingerprint`。

- 目标限当前文档中可达的单个正文或 Header/Footer 文本段落、Heading、列表项；不支持批量 target 或 table/numbering style apply；字符精确范围见下节。修订模式只支持主 Story。
- `style_usage` / `block_styles` 对 Header/Footer 返回 `story_id`。Header/Footer 普通写入的 target 必须携带该 `story_id`，正文 target 禁止携带；共享 story 的样式绑定会自然作用到所有 placements。
- `set` 默认只能绑定已有、`origin=document` 的 paragraph style，有限 builtin 例外见下节；`clear` 只删除显式 paragraph binding，并回退到 default paragraph style 或无样式。
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

Header/Footer 示例只改变 target：`{"kind":"block","block_id":"<block_id>","story_id":"<story_id_from_fetch>"}`。不得用当前激活页眉、任意 placement 或首个 block ID 代替。

调用时使用 `lark-cli docs +local-update --doc "<token>" --revision-id "<revision_id_from_same_fetch>" --command style_apply --style-option @style-option.json`。

帮助未显示 `--revision-id` 或样式 option 时停止。dry-run 的 binding、effective diff、fingerprints 和 plan token 位于 `data.command_result`。

样式命令不带 XML `--content`。option 文件只放样式业务字段；revision ID 仅通过顶层 `--revision-id` 传入。

## 字符精确范围 set/clear

仅单个可达 textual block 内非空 UTF-16 code unit 半开区间 `[start,end)`；offset 相对该 block 纯文本，从 0 开始。必须是安全整数且 `0 <= start < end <= 文本 UTF-16 长度`，不能跨 block、拆分 surrogate pair、受保护行内结构或待审修订。字符范围首期只支持普通模式，不因失败切换模式或降为普通写入。既有 Story 门禁继续生效，不从段落普通写入能力推断新增字符范围支持所有 Story。

例如纯文本 `A😀中文B` 长度为 6，`[3,5)` 精确选择“中文”；`[1,2)` 拆分 emoji，必须拒绝。不得按 Unicode code point 或 XML 字符数计算 offset。

```json
{
  "target": {"kind": "text_range", "block_id": "<block_id>", "start": 3, "end": 5},
  "style_type": "character",
  "action": "set",
  "style_id": "<character_style_id_from_catalog>",
  "expected_text_range_fingerprint": "<from_exact_range_fetch>",
  "expected_target_effective_fingerprint": "<from_character_catalog_computed>",
  "dry_run": true
}
```

```json
{
  "target": {"kind": "text_range", "block_id": "<block_id>", "start": 3, "end": 5},
  "style_type": "character",
  "action": "clear",
  "expected_text_range_fingerprint": "<from_exact_range_fetch>",
  "expected_fallback_effective_fingerprint": "<from_exact_range_fetch>",
  "dry_run": true
}
```

- 写前以 `block_styles` 的 self 精确 `start/end` 范围查询取得 `text_range.expected_text_range_fingerprint`；set 的 target effective guard 来自目标 character style 的 catalog computed；clear 的 fallback guard 来自同一 `text_range.fallback_effective_fingerprint`。无现有绑定也应显式查该范围。所有 identity、范围与 guard 对应同一文档版本；不使用整块 fingerprint、相邻范围或客户端自算 hash 替代。
- character 分支禁止 `expected_block_style_fingerprint`；paragraph 分支禁止范围参数与 `expected_text_range_fingerprint`。clear 禁止 `style_id`、`expected_target_effective_fingerprint` 和 `materialize_builtin`；set 禁止 fallback effective 字段。
- set/clear 仅写入/删除范围的字符样式绑定，保留全部直接格式与相邻范围；clear 回退到剩余 cascade，不等于清除文字强调，也不创建默认 character binding。不要用清冲突格式的 UI command 替代。
- dry-run 检查 `before_text_range/after_text_range`、范围 fingerprint、binding、`effective_diff`、`visible_change_expected` 与 plan token；直接格式可遮蔽样式。缺失样式链或相关 effective/resolution 不完整时停止，不提交不完整结果。
- 调用仍使用上文公开 `--style-option`，不带 XML content，不把示例包装成私有请求；精确范围查询的 CLI 参数名须先按当前 `+local-fetch --help` 核对，未暴露则停止。

## linked 选择与有限 builtin 补建

linked 不是新 `style_type`。paragraph 分支用查询返回的段落侧 ID，character 分支用查询返回的字符侧 ID；关系和类型由 catalog 核对，不按样式名称猜测或拼接另一侧 ID。

set 可显式带 `materialize_builtin=true`，仅允许当前 runtime 返回的 `origin=builtin_fallback`，且属于有限集合 `__wordPresetStyleNormal`、`__wordPresetStyleHeading1`…`9` 及对应 `Heading1Char`…`9Char`。这些名称用于说明范围，实际完整 ID 必须来自查询；不猜测 ID，不覆盖任何同 ID 既有定义。宿主在同事务补齐缺失依赖再绑定，dry-run 检查补建影响及 after binding 的 `origin=document`。已有 document 定义使用普通 set，不带补建开关；unresolved 或其他 builtin 不开放。有限补建只支持普通模式，不扩大 `style_update` 的创建/修改能力。

## 取得 plan_token 并提交

1. 传 `dry_run=true` 取得 `plan_token`，这一请求不带 `plan_token`。返回 `no_change=true` 时没有改动，也没有 `plan_token`，到此结束。
2. 提交时使用相同的文档、命令、参数、指纹和顶层 `--revision-id`，只把 `dry_run` 改成 `false` 并加上本次的 `plan_token`。文档或参数变化、`plan_token` 失效时，用当前数据重新取得 `plan_token`。
3. `data.command_result.applied=true` 和 `new_revision_id` 表示样式已在 Canvas 应用。文件保存由客户端处理。

提交已成功但回执丢失时，可在 `plan_token` 的 5 分钟有效期内用完全相同的请求取回原回执。请求仍在执行或结果不明时，先[处理原请求](../../workflows/canvas-doc-recovery.md)。
