---
keyword: comment
---

**功能**：批注读取、创建、回复、更新和删除

# 本地 Word：批注读取与更新

先 Fetch `comments` 取得真实目标或批注 identity 和 fingerprint，按 action 补充最小参数；不得从正文 XML、可见文本、页码或 selection 猜 identity。参数遵循 `local-update` 和本页规则；未知参数或版本漂移时查看当前 `--help`，不将内部 `command_params` 字段臆造为 CLI flag。

## 批注：`comments` → `comment`

Fetch `comments` 可按 target ID 过滤并分页；默认 50、最大 100。结果返回批注树、锚点、`state_fingerprint`，按需返回目标的 `target_fingerprint`。作者、时间和持久 ID 只读。

`--target-ids` 可一次传入去重后的多个 target ID，返回各目标 fingerprint。每个 comment action 仍是单次命令；fingerprint 与 revision 的复用和推进由 workflow 编排。

创建多条批注时，写前将去重后的 target ID 一次传入 `--target-ids` 批量获取 fingerprint，再按每次回执推进 revision 串行提交；未被写入的 target 可复用本批 fingerprint，同一 target 再次写入前须重新 Fetch。

| action | 关键输入 | guard |
|---|---|---|
| `create_root` | `content`、非空 `anchors` | 每个 target 的 `expected_target_fingerprint` |
| `update_comment` | `comment_id`、`content` | `expected_state_fingerprint` |
| `add_reply` | `comment_id`、`content` | `expected_state_fingerprint` |
| `update_reply` | `comment_id`、`reply_id`、`content` | `expected_state_fingerprint` |
| `resolve` / `reopen` / `delete_comment` | `comment_id` | `expected_state_fingerprint` |
| `delete_reply` | `comment_id`、`reply_id` | `expected_state_fingerprint` |

`create_root` 最小 option：

```json
{"action":"create_root","content":"...","anchors":[{"kind":"text_range","start":0,"end":5,"block_id":"...","expected_target_fingerprint":"sha256:..."}]}
```

锚点闭集：同一 textual record 内非空的 UTF-16 `text_range`、已有对象的 `object`、图片上 `[0,1]` 归一化矩形 `image_area`。`text_range` 使用段落等文本记录及其 fingerprint；table/td 等结构容器不是文本目标，表格区域用其内部按文档顺序排列的一个或多个 `text_range`。根批注正文必须用 `update_comment`；`update_reply` 的 `reply_id` 必须属于指定根批注。不得伪造作者、时间或 ID。