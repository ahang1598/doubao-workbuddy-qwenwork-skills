# 本地 Word：分页与布局更新

> 使用前须完整读取本页；未见末行「全文完」时，调整 offset 继续读取至该标记。

前置读取 [`canvas-doc-fetch.md`](canvas-doc-fetch.md)、[`canvas-doc-update.md`](canvas-doc-update.md) 和 [`canvas-doc-layout.md`](../xml/canvas-doc-layout.md)，其中的公共 XML 前置同样适用。

这些场景不新增 command，而是使用通用 block 指令写入 XML。先用 `docs +local-fetch --scope layout --detail full` 获取当前节和布局，再读取插入点或布局目标 block。只读页面尺寸作为图片/表格尺寸参考时，不要求加载本页。水印不是 layout XML，按 [`canvas-doc-update-domain.md`](canvas-doc-update-domain.md) 使用领域命令。

> **页首和页尾定位要求**：按“本页页首/页尾”插入时，必须先按 [`canvas-doc.md`](../workflows/canvas-doc.md#读取流程)读取目标页和实际存在的相邻页。存在相邻页时，只有边缘 block ID 未出现在相邻页，才能在该 block 前后插入；第一页页首与已确认末页的页尾沿用入口的文档起止证据，不请求不存在的邻页。同一 ID 出现在两页时必须查看 PDF、定位最新 `full` XML 中的块内边界并按下文拆分，消歧完成前禁止 update，不得降级为整个 block 前后插入。
>
> 反例：选区在第 2 页，而其 carrier 延续到第 3 页；即使它是两页共同的最后一个 block，段后插入仍位于第 3 页之后，必须按第 2 页页尾拆分。

## 插入分页符

块间插入使用下方写法；carrier 内部的分页通过完整 `block_replace` 在准确行内位置加入 `<page-break/>`，只拆分必要文本节点并保留格式。

```bash
lark-cli docs +local-update --doc "<token>" \
  --command block_insert_after \
  --block-id "<anchor_block_id>" \
  --content '<p><page-break/></p>'

# 块内示例：实际 XML 须保留最新 full 中的全部非目标属性
lark-cli docs +local-update --doc "<token>" \
  --command block_replace \
  --block-id "<carrier_id>" \
  --content '<p id="<carrier_id>"><span>前半内容</span><page-break/><span>后半内容</span></p>'
```

## 插入分节符

`<layout-break/>` 只能位于正文顶层，不能塞进段落、列表项或单元格。插入位置位于 carrier 内部时，必须在该处拆分 carrier 并在两部分之间插入，不得降级为整个 carrier 之前或之后。下面的两步拆分仅用于可按显式普通文本与格式无损重建的正文顶层段落/标题：后半段必须作为新 carrier 省略 record ID，不能借用仍在原段落中的图片、Drawing、Field、Note、书签或其他对象 identity；拆分涉及这些对象、跨 carrier 书签或未暴露的字符样式绑定时，写前输出 `local_unverifiable` 交回入口，不能先复制再尝试删掉旧引用。两步顺序固定为：先在原 carrier 后插入“分节符 + 后半 carrier”以保全后半内容，回读确认后，再用 `block_replace` 将原 carrier 缩短为前半内容；任一步结果不干净都立即进入恢复流程，不继续写。

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
# 屏障回读：确认分节符和后半 carrier 均已受理，再执行下一步
lark-cli docs +local-update --doc "<token>" \
  --command block_replace \
  --block-id "<carrier_id>" \
  --content '<p id="<carrier_id>"><span>前半内容</span></p>'
```

`layout-break.type` 的完整取值见 [`canvas-doc-layout.md`](../xml/canvas-doc-layout.md)。分节写入后重新 fetch `layout` 和受影响页。

在文档末尾插入分页符或分节符时，CLI 会在其后自动补充用于继续编辑的空段落；不要手动重复添加，也不要在写后回读时将其作为多余空白删除。

## 更新页面布局、行网格、分栏、页眉、页脚和页码域

先执行 `docs +local-fetch --scope layout --detail full` 获取 layout block ID，再用 `block_replace` 更新完整 `<layout>`。可更新页面属性、页眉、页脚和页码域（`<page-number/>` 表示当前页码域，`<page-count/>` 表示总页数域）；没有可写 ID 时不能更新。协议没有 `<layouts>` 包裹层。

以 Fetch 返回的完整布局为底稿，只修改目标属性。所有非目标标量属性仍须保留；未修改的 header/footer placement 省略对应元素以保持原 story，不能把依赖片段外定义的自闭合共享引用单独写回，详见 [共享页眉页脚规则](../xml/canvas-doc-layout.md#页面布局行网格分栏页眉和页脚)。

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

`layout.xml` 必须以本轮 Fetch 返回的完整 `<layout>` 或 `<layout-break>` 为底稿，只修改计划字段并保留其余标量属性和真实 `id`；未修改的 header/footer 元素按上文省略保留，其他子树仍按专项规则保真。header/footer ID 是 story identity，不是可独立更新的 block ID；已有正文和页码域优先通过该 story 内 block ID 精确更新，placement 的新增、删除或解除共享才替换所属 layout。共享 story 的修改会影响全部引用节，必须在写前核对用户范围；写后重新 fetch `layout` 验证。

`<layout>` 与 `<layout-break>` 的 `block_replace` 对 content 形状有硬约束：**必须恰好一个根元素、标签与目标类型一致、`id` 等于 `--block-id`**，任何一条不满足都是参数错误。

改纸张方向要留意：只有 `page-size` 与 `orientation` 同时在场才会真的交换宽高。基线里是显式 `page-width` / `page-height` 时，单改 `orientation` 不旋转版面；要换成预设纸张必须同时删掉 `page-width` / `page-height`，两者共存是整次失败。删除页眉页脚要写 `remove="true"`，细节见 [`canvas-doc-layout.md`](../xml/canvas-doc-layout.md)。

===== 全文完 =====
