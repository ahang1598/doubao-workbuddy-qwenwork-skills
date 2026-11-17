---
keyword: block_replace
---

**功能**：用 XML 替换已有块，可沿用原块 ID

### block_replace：替换整个 block

`block_replace` 可替换 `<p>`、标题和 `<li>` 等目标，支持范围见 [`local-update` 的能力表](local-update.md#可寻址标签与可用命令)。替换文本块时，在最新完整 XML 上修改，保留原 ID、未修改的 `<span>` 边界和属性；内部 `<span>` 不能单独作为替换目标。

**这是内容替换，不是只补指定格式的 patch。** 对被替换文本，字体、字号、颜色等协议拥有的行内格式由传入 XML 表达，缺席时不自动继承，且可能没有 warning；原 ID 只保留身份。段落属性中明确规定“缺席保持”的规则不能推广到行内格式。修改文字并加粗时，复制原格式节点后做局部修改，见局部文字与格式修改。

用 `--detail full` 取得要替换的块，再在原 XML 上修改目标内容。读取页面布局时，`with-ids` 也会返回完整布局属性。示例只展示一段，实际写入时保留原有且未修改的格式和对象。

```bash
lark-cli docs +local-update --doc "<token>" \
  --command block_replace \
  --block-id "<paragraph_block_id>" \
  --content '<p id="<paragraph_block_id>" align="justify" first-line-indent="24px" line-height="1.5"><span font-family="Arial" font-size="16px">更新后的正文。</span></p>'
```

单元格、列表项、图片和布局的 XML 写法见各自的说明。

宿主另有 `block_replace.block_ids`，仅用于同一 story、同一父容器、连续文本块的跨 carrier 书签边界更新，不是通用批量替换。只有当前 CLI 帮助暴露对应参数时才按 `xml:p` 的书签规则使用。

## 分页和页面布局

前置查询 `local-update`、`xml:common`；块内分页查询 `xml:layout-break`，页面属性查询 `xml:layout`，修改后续节的页面属性时两者都查询。

这些场景不新增 command，而是使用通用 block 指令写入 XML。先用 `lark-cli docs +local-fetch --scope layout --detail full` 获取当前节和布局，再读取插入点或布局目标 block。只读页面尺寸作为图片/表格尺寸参考时，不要求查询布局写入 schema。水印不是 layout XML，查询 `watermark`。

按页首或页尾定位时，从目标页和实际存在的相邻页读取块 ID，判断目标块是否跨页。跨页时，用页面 PDF 找到可见断点，再在块的完整 XML 中找到对应位置。例如一个段落从第 2 页延续到第 3 页，直接插在段后会落到第 3 页。无法定位断点时，先别用整块前后的位置代替。

## 块内分页符

carrier 内部的分页通过完整 `block_replace` 在准确行内位置加入或移除 `<page-break/>`，只拆分必要文本节点并保留格式；块间插入查询 `block_insert_after`。

```bash
# 块内示例：实际 XML 须保留最新 full 中的全部非目标属性
lark-cli docs +local-update --doc "<token>" \
  --command block_replace \
  --block-id "<carrier_id>" \
  --content '<p id="<carrier_id>"><span>前半内容</span><page-break/><span>后半内容</span></p>'
```

## 更新页面布局、行网格、分栏、页眉、页脚和页码域

先执行 `lark-cli docs +local-fetch --scope layout --detail full` 获取 layout block ID，再用 `block_replace` 更新完整 `<layout>`。可更新页面属性、页眉、页脚和页码域（`<page-number/>` 表示当前页码域，`<page-count/>` 表示总页数域）；没有可写 ID 时不能更新。协议没有 `<layouts>` 包裹层。

以 Fetch 返回的完整布局为底稿，只修改目标属性。所有非目标标量属性仍须保留；未修改的 header/footer placement 省略对应元素以保持原 story，不能把依赖片段外定义的自闭合共享引用单独写回，详见 共享页眉页脚规则。

- 行网格设置为 `grid-type="lines"` 并给正长度 `grid-line-pitch`；清除 direct grid 用 `remove-grid="true"`，两种形态互斥。字符网格不支持。
- 等宽分栏使用 `<columns count="2" equal-width="true" gap="24pt" separator="false"/>`；非等宽分栏使用 `equal-width="false"`，并按顺序为每个 `<column width="..." gap-after="..."/>` 显式给宽度。清除 direct columns 用 `<columns remove="true"/>`。
- 缺省末栏宽度与 `layout-break type="next-column"` 尚未实现，不能靠省略字段猜测。

`<layout>` 是文档级单例，表示第一节；后续各节由起始处的 `<layout-break>` 表示。要修改后续节的纸张方向、页边距或页眉页脚，用 `block_replace` 修改该节起始处的 `<layout-break>`。`--scope layout` 按正文节顺序返回 `<layout>` 和所有 `<layout-break>`。

```bash
lark-cli docs +local-update --doc "<token>" \
  --command block_replace \
  --block-id "<layout_block_id>" \
  --content @layout.xml
```

`layout.xml` 必须以本轮 Fetch 返回的完整 `<layout>` 或 `<layout-break>` 为底稿，只修改计划字段并保留其余标量属性和真实 `id`；未修改的 header/footer 元素按上文省略保留，其他子树仍按专项规则保真。header/footer ID 是 story identity，不是可独立更新的 block ID；已有正文和页码域优先通过该 story 内 block ID 精确更新，placement 的新增、删除或解除共享才替换所属 layout。共享页眉或页脚中的内容一经修改，所有引用它的节都会更新。只改指定节时，按 `xml:layout` 解除共享后再改。

`<layout>` 与 `<layout-break>` 的 `block_replace` 对 content 形状有硬约束：**必须恰好一个根元素、标签与目标类型一致、`id` 等于 `--block-id`**，任何一条不满足都是参数错误。

改纸张方向要留意：只有 `page-size` 与 `orientation` 同时在场才会真的交换宽高。基线里是显式 `page-width` / `page-height` 时，单改 `orientation` 不旋转版面；要换成预设纸张必须同时删掉 `page-width` / `page-height`，两者共存是整次失败。删除页眉页脚要写 `remove="true"`，细节查询 `xml:layout`。

## 图表尺寸

以 chart record id 执行 `block_replace`，保留 Fetch 返回的 `id` 和已有 `data-id`，只改 `width` / `height`。

- 图表删除：以 chart record id 执行 `block_delete`。
- 尺寸和布局约束查询 `xml:chart`。
- `CHART_CAPABILITY_UNAVAILABLE` 表示当前客户端未发布图表能力，不转用私有接口。