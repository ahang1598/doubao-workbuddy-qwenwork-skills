---
keyword: xml:layout-break
---

**功能**：后续分节、分页边界及分节布局

# 本地 Word XML：分页、分节与页面布局

本页定义分页符、分节、行网格、分栏、纸张、页边距、页眉页脚、页码域和脚注尾注的设置规则。

公共规则查询 `xml:common`，更新操作查询 `local-update` 及命中的 `block_replace` / `block_insert_after`。

页眉页脚可用最小 `<p>文本</p>` 形状；涉及内部复杂富文本、段落格式、列表或书签时，按结构查询 `xml:p`、`xml:span`、`xml:ol`，涉及图片时查询 `xml:img`。脚注尾注及 `<note-settings>` 查询 `xml:note`。TOC 不属于本页的页码域能力；查询 `table_of_contents`，能力不足时由上层 workflow 停止。

## 分页符与分节符

```xml
<p>第一页内容<page-break/></p>
<p>下一页内容</p>

<layout-break type="continuous"/>
<layout-break type="next-page"/>
<layout-break type="odd-page"/>
<layout-break type="even-page"/>
```

`layout-break.type` 支持：

- `continuous`：当前位置开始新节，不换页；
- `next-page`：下一页开始新节；
- `odd-page`：下一个奇数页开始；
- `even-page`：下一个偶数页开始。

`odd-page` / `even-page` 为满足下一节的起始页奇偶性，渲染或导出 PDF 时可能自动补空白页；起始页奇偶性与分节类型一致时属于预期分页。

本页定义分节类型与分页边界；修改 `<layout-break>` 所开启的后续节的纸张、页边距、分栏或页眉页脚时，同时查询 `xml:layout` 的页面属性与共享 story 规则。

`next-column` 只是预留值，当前未实现，写入会返回 `BLOCK_NOT_IMPLEMENTED_TAG`。`<page-break/>` 是行内元素，只能放在 `<p>`、`<h1>`～`<h9>` 或 `<li>` 内。

增删分页符时，通常替换包含它的段落、标题或列表项。`+local-update` 无法直接定位到 `<page-break/>`。

通常用 `block_insert_after` 插入分节符。已有的 `<layout-break/>` 有自己的块 ID，可用 `block_delete` 删除，也可用 `block_replace` 改类型。替换时，`content` 只传一个带原 ID 的 `<layout-break>`。后续操作需要新的页码或分节位置时，再读 `layout` 和相关页面。

在文档末尾插入分页符或分节符时，文档会自动补一个空段落，让光标可以停在那里继续编辑。保留这个段落即可。
