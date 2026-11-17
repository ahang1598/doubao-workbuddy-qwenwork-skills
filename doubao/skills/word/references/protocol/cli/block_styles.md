---
keyword: block_styles
---

**功能**：block 与精确字符范围的绑定、effective 属性和 guard 查询

# 读取块和字符范围的样式

需要写入时再查询 `local-update`。样式 identity、关系和 fingerprint 只能来自当前 CLI 的结构化读取结果，不得从 DocxXML 标签名、显示名称或历史结果猜测。

样式读写的结果在 `data.command_result`，返回对象字段而非正文 XML。

## 按目标读取

已知块 ID 时可以直接查询。

- 段落样式 set/clear 使用 `block_styles --style-detail computed`；set 另查 `style_catalog` 取得目标 paragraph style 的 computed，clear 使用 block computed 返回的 fallback fingerprint。
- 字符样式 set/clear 使用 self 精确 start/end 查询取得范围 guard；set 另查目标 character style 的 catalog computed，clear 使用该范围的 fallback fingerprint。具体 CLI 范围参数以当前帮助为准。

写入用的 ID 和 `expected_*_fingerprint` 来自同一文档版本。写入命令需传顶层 `--revision-id`，优先传读取结果中的版本，也可按 `local-update` 的规则传 `-1`。

### 查询参数

三个 scope 的结构化结果位于 `data.command_result`，使用以下样式专属参数，不混用普通 XML 的 `--detail` 或 export 参数：

| scope | 参数与取值 |
|---|---|
| `block_styles` | 必填 `--block-id`；`--style-scope self\|subtree`，默认 self；`--style-detail summary\|computed`，默认 summary；仅 subtree 可传 `--cursor`、`--limit`，limit 默认 200、最大 1000；self 禁止分页参数；self 可成对传 start/end 查询单块非空 UTF-16 半开范围，subtree 禁止范围参数；范围 CLI flag 名以当前帮助为准 |

```bash
lark-cli docs +local-fetch --doc "<token>" \
  --scope block_styles --block-id "<block_id>" --style-detail computed
```

### 精确字符范围与 guard 来源

- 范围相对块内的纯文本，单位 `utf16_code_unit`。start/end 成对传入，范围非空，不得越界或拆分 surrogate pair。字符范围参数以当前 `+local-fetch --help` 为准。CLI 没有提供这些参数时，不能用整块查询替代精确范围查询。
- `data.command_result.text_range` 返回 `range/text/runs`、`expected_text_range_fingerprint`、`fallback_effective_fingerprint` 与范围 resolution/projection；runs 含各子范围的 binding 和 effective_properties。未绑定样式的范围仍可显式查询；`bindings.text_ranges` 的既有 run 边界不能替代本次 exact range guard。
- character set/clear 原样使用精确范围的 `expected_text_range_fingerprint`；clear 原样使用该范围 `fallback_effective_fingerprint`，不能使用 block 层同名字段。set 的 effective guard 来自同一文档版本的 character catalog computed。
- 如果缺失样式链、run toggle 或 table conditional run 导致范围无法完整解析，就停止这次写入。普通正文 XML 不包含此查询返回的字符样式绑定。

分页时把 `data.command_result.next_cursor` 原样传给下一次 `--cursor`，保持查询条件不变，读取至 `truncated=false`。`style_update.expected_usage_fingerprint` 必须来自同一文档版本、`include_descendants=true` 的完整影响集合；不能使用默认 exact-only 查询、单页 items 或客户端自行计算的 hash。各页 fingerprint 相同也不代表已读取完整影响面。
