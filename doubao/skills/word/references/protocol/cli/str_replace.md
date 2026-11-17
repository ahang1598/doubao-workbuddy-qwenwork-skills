---
keyword: str_replace
---

**功能**：在指定范围内查找并替换所有匹配的纯文本

### str_replace：纯文本替换

`str_replace` 要求纯文本 `pattern` 至少命中一次，并在一次事务中替换搜索范围内全部非重叠命中；同一 record 内命中相互重叠则整次拒绝。`content` 中形似标签的文本按字面写入。可选 `--block-id` 将搜索范围限定为该 block；省略时搜索全文。只想修改一处时，须确认 pattern 在实际搜索范围内唯一，否则改用 `block_replace`。

省略 `--block-id` 时，搜索从 root page 正文沿实际引用遍历文本 record，包括表格及正文可达的 Note/TextBox，不沿 page/section 的 Header/Footer 槽位引用；也不按最近一次 Fetch 的选区缩小范围。传入 `--block-id` 时仅搜索该 block。需修改页眉页脚时按 layout/story 精确定位。

匹配可跨同一文本块内的多个 span/run，不能跨文本块。范围外样式保留；新文本仅继承命中范围内严格共有且可安全继承的字符样式，存在无法继承的样式时返回 `COMPAT_STYLE_LOST`。需要保留区间内不同样式时，使用 `block_replace`。只改指定 block 的纯文本时优先传 `--block-id`，避免整块重写影响书签等非目标结构。空字符串删除匹配文本，保留范围外内容。命中行内对象，或只覆盖 Field run 的一部分会报参数错误。

```bash
# 普通文本替换
lark-cli docs +local-update --doc "<token>" \
  --command str_replace \
  --pattern '旧版本预计周五发布' \
  --content '新版本预计下周一发布'

# 仅替换指定 block 内的匹配文本
lark-cli docs +local-update --doc "<token>" \
  --command str_replace --block-id "<最新目标 ID>" \
  --pattern '旧版本预计周五发布' \
  --content '新版本预计下周一发布'

# 删除全文中的匹配文本
lark-cli docs +local-update --doc "<token>" \
  --command str_replace \
  --pattern '废弃内容' --content ''
```