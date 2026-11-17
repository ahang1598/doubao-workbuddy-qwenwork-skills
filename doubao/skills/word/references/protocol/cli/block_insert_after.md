---
keyword: block_insert_after
---

**功能**：在指定锚点后插入内容块

### block_insert_after：插入 block

```bash
lark-cli docs +local-update --doc "<token>" \
  --command block_insert_after \
  --block-id "<section_heading_block_id>" \
  --content @insert.xml
```

`insert.xml` 按用户要求生成完整 XML；需要延续现有格式时，以写前 `full` 中的同类元素为基准，移除新对象不应复用的 ID。一次可写入连续的多个 XML block。回执不返回新块 ID。后续操作需要该 ID 时，可从插入锚点附近读取。特殊目标的 content 形状查询对应能力协议。

新增段落默认延续相邻同类元素的字体、字号、缩进和行距；用户指定新格式时按要求设置。没有同类元素时按目标样式生成，不以缺少模板为由禁止新增。

## 分页和分节

前置查询 `local-update`、`xml:common` 和 `xml:layout-break`。

这些场景不新增 command，而是使用通用 block 指令写入 XML。先用 `lark-cli docs +local-fetch --scope layout --detail full` 获取当前节和布局，再读取插入点或布局目标 block。只读页面尺寸作为图片/表格尺寸参考时，不要求查询布局写入 schema。水印不是 layout XML，查询 `watermark`。

按页首或页尾定位时，从目标页和实际存在的相邻页读取块 ID，判断目标块是否跨页。跨页时，用页面 PDF 找到可见断点，再在块的完整 XML 中找到对应位置。例如一个段落从第 2 页延续到第 3 页，直接插在段后会落到第 3 页。无法定位断点时，先别用整块前后的位置代替。

## 插入块间分页符

```bash
lark-cli docs +local-update --doc "<token>" \
  --command block_insert_after \
  --block-id "<anchor_block_id>" \
  --content '<p><page-break/></p>'
```

块内分页查询 `block_replace`；分节插入涉及拆分 carrier 时，也须查询 `block_replace`。

## 插入分节符

`<layout-break/>` 只能位于正文顶层。插入点在段落或标题中间时，在该处拆成两块，再在中间插入分节符。以下两步只适用于能按原文字和格式重建的正文顶层段落或标题。后半段是新块，省略 ID。拆分涉及图片、绘图、域、注释、跨块书签或未暴露的字符样式绑定时，用能保留这些结构的方式处理，见 [Canvas 编辑](../../workflows/canvas-doc.md#在-canvas-里改)。

先在原块后插入分节符和后半段。回执为 `result=success` 且没有影响这两部分的警告时，再用 `block_replace` 把原块缩短为前半段。部分成功、出现相关警告或结果不明时，保留原块，先按[异常处理](../../workflows/canvas-doc-recovery.md)处理这次插入。

```bash
lark-cli docs +local-update --doc "<token>" \
  --command block_insert_after \
  --block-id "<anchor_block_id>" \
  --content '<layout-break type="next-page"/>'

# 块内示例：先保全后半内容，再缩短原 carrier；实际 XML 须保留最新 full 中的全部非目标属性
lark-cli docs +local-update --doc "<token>" \
  --command block_insert_after \
  --block-id "<carrier_id>" \
  --content '<layout-break type="even-page"/><p><span>后半内容</span></p>'
# 分节符和后半段完整应用后，缩短原段落
lark-cli docs +local-update --doc "<token>" \
  --command block_replace \
  --block-id "<carrier_id>" \
  --content '<p id="<carrier_id>"><span>前半内容</span></p>'
```

`layout-break.type` 的完整取值查询 `xml:layout-break`。

在文档末尾插入分页符或分节符时，CLI 会在其后自动补充用于继续编辑的空段落；不要手动重复添加。