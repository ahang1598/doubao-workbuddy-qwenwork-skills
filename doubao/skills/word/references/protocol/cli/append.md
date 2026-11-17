---
keyword: append
---

**功能**：在尾随连续分节符之前追加合法正文 block

### append：尾随分节符前追加正文

```bash
lark-cli docs +local-update --doc "<token>" \
  --command append \
  --content @append.xml
```

按用户要求编写 `append.xml`；未指定格式时，沿用文末同类段落在 `--detail full` 结果中的格式。`append` 把正文插入到文末尾随的连续 `<layout-break>` 之前；需要插入到指定章节或指定分节之后时用 `block_insert_after`。

追加内容的格式选择规则见 `block_insert_after` 的新增段落说明。

**多节文档须确认落点。** `<layout-break>` 的页面设置属于其后新节；`append` 的正文位于尾随连续分节符之前，不属于这些分节符开启的新节。用户要求追加到指定节时，先读取 layout 和末尾正文，优先用目标节内真实末块执行 `block_insert_after`。

目标层级没有样式而用户只要求外观时，可以用带格式的普通段落。需要标题层级、目录收录或导航时，用能保留标题结构的方式；相关说明见 [Canvas 编辑](../../workflows/canvas-doc.md#在-canvas-里改)。