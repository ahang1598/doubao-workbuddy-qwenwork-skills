---
keyword: xml:layout
---

**功能**：首页布局、纸张、页边距、分栏、行网格、页眉页脚和页码域

# 本地 Word XML：分页、分节与页面布局

本页定义分页符、分节、行网格、分栏、纸张、页边距、页眉页脚、页码域和脚注尾注的设置规则。

公共规则查询 `xml:common`，更新操作查询 `local-update` 及命中的 `block_replace` / `block_insert_after`。

页眉页脚可用最小 `<p>文本</p>` 形状；涉及内部复杂富文本、段落格式、列表或书签时，按结构查询 `xml:p`、`xml:span`、`xml:ol`，涉及图片时查询 `xml:img`。脚注尾注及 `<note-settings>` 查询 `xml:note`。TOC 不属于本页的页码域能力；查询 `table_of_contents`，能力不足时由上层 workflow 停止。

---

## 页面布局、行网格、分栏、页眉和页脚

```xml
<layout id="section-1"
        page-number-start="1"
        page-number-format="decimal"
        page-size="a4"
        orientation="portrait"
        margin-top="72pt"
        margin-right="72pt"
        margin-bottom="72pt"
        margin-left="72pt"
        first-page-different="true"
        grid-type="lines" grid-line-pitch="18pt">
  <columns count="2" equal-width="true" gap="24pt" separator="false"/>
  <header type="default"><p align="center">项目方案</p></header>
  <footer type="default">
    <p align="center">第 <page-number format="decimal"/> 页，共 <page-count scope="document"/> 页</p>
  </footer>
</layout>
```

| layout 属性 | 说明 |
|---|---|
| `id` | 文档级 layout 标识，必填 |
| `page-number-start` | 本节起始页码 |
| `page-number-format` | 页码格式，如 `decimal` |
| `page-size` | `a4`、`a5`、`letter`、`legal`；与 `page-width` / `page-height` 互斥 |
| `page-width` / `page-height` | 自定义纸张尺寸；与 `page-size` 互斥，必须带单位 |
| `orientation` | `portrait` 或 `landscape` |
| `margin-top/right/bottom/left/header/footer` | 页边距及页眉页脚距离；必须带单位 |
| `gutter` | 装订线宽度；必须带单位 |
| `first-page-different` / `odd-even-different` / `mirror-margins` | `true` / `false` |
| `grid-type` / `grid-line-pitch` | 当前只支持 `grid-type="lines"`；pitch 为正数且带 `pt\|cm\|mm\|in` |
| `remove-grid` | `true` 清除 direct grid；与 `grid-type/grid-line-pitch` 互斥 |

- 页面尺寸、页边距和装订线长度只接受 `pt`、`px`、`in`、`cm`、`mm`。**这一组属性写裸数字（`margin-top="72"`）是整次失败**（`ATTR_VALUE_INVALID`），不是丢弃该属性；与正文侧的尺寸属性不同。
- **`page-size` 与 `page-width` / `page-height` 同时出现是整次失败**（`ATTR_MUTUALLY_EXCLUSIVE`），不会择一生效。
- **改纸张方向不能只改 `orientation`。** 只有 `orientation` 与 `page-size` 一起在场时才真的交换宽高；基线里是显式 `page-width` / `page-height` 时（横向文档和自定义纸张 fetch 出来就是这个形状），单改 `orientation` 只翻一个标志位，版面不会旋转。仅当用户目标纸张与预设一致时，才可删掉 `page-width` / `page-height` 并改写为对应 `page-size`；两者不能共存。自定义纸张不得擅自改成 A4，必须同时按目标方向设置匹配的显式宽高。
- `page-number-format` 写协议枚举以外的值不会被丢弃，而是**原值透传**（渲染时兜底 decimal），但仍返回一条 `ATTR_ENUM_INVALID_DROPPED`。fetch 出来的非枚举值可以原样写回，看到这条诊断不必回滚。
- `lark-cli docs +local-fetch --scope layout --detail full` 返回可写的 layout block ID 时，支持使用 `block_replace` 写回完整 `<layout>`，并在其中新增或修改 `<header>`、`<footer>`、`<page-number/>` 和 `<page-count/>`。
- 协议没有 `<layouts>` 包裹层。`<header>` / `<footer>` 只能位于 `<layout>` 或 `<layout-break>` 内，`type` 支持 `default`、`first`、`even`，`remove` 支持 `true` / `false`；同一宿主下每个 type 只能出现一次，重复出现是整次失败（`ATTR_MUTUALLY_EXCLUSIVE`）。
- **页眉页脚子元素走「出现即替换、缺席即保留」，与同级标量属性的全量替换相反。** 改页边距时漏写页眉子树不会把页眉删掉；反过来，删除页眉必须显式写 `<header type="default" remove="true"/>`，空元素 `<header type="default"></header>` 表示「空白页眉」这个合法状态，不兼任删除。`remove="true"` 带子内容是整次失败。
- 同一个页眉页脚被多节共用时，Fetch **只在第一次出现的位置带内容**，后续位置是带 `id` 的自闭合引用。这种引用依赖同一片段中更早出现的完整定义；它不是独立的“按 ID 保留原正文”写法。`block_replace` 只提交一个 `<layout>` / `<layout-break>`，从 layout Fetch 中提取后续节时，不得把其自闭合 `<header id="..."/>` / `<footer id="..."/>` 原样写回，否则会把共享 story 正文替换为空。未修改的页眉页脚 placement 应省略整个对应元素，利用“缺席保留”；确需提交该 story 时，从本轮 layout Fetch 补齐其完整定义，在本次请求中首次出现时带内容，之后同 ID 的引用才自闭合。仅同一请求中重复定义同 ID 内容会整次失败。
- header/footer ID 是所属 layout 内的 story identity，不是 block ID。页眉页脚正文可用 story 内真实 block ID 精确更新；placement 本身的新增、删除、共享或解除共享仍通过完整 `<layout>` / `<layout-break>` 替换。替换需要可写的 layout block ID 和完整的所属 story 信息。
- 共享 Header/Footer story 的 block 更新会作用于所有 placements；如只需修改一个 placement，必须通过 layout replacement 解除共享并创建新 story identity，不能直接改共享 story 后声称只影响一节。
- `style_usage` / `block_styles` 返回 Header/Footer block 的 `story_id`；对这些 block 执行 `style_apply` 时必须在 target 中原样携带该 `story_id`，正文 target 则禁止携带。
- 页眉横线不是独立对象或命令，而是页眉文本段落的 `border-bottom`。用 layout Fetch 定位实际承载横线的首/末段并基于完整段落 `block_replace`；保留文字、样式和其他边框，删除横线写 `border-bottom="none"`。共享 story 修改会作用于全部 placements。
- `<layout>` 是**文档级单例，表示第一节的页面设置**；它的 ID 只能喂给 `block_replace`，写第二个 `<layout>` 会失败。
- **后续各节的页面设置挂在该节起始处的 `<layout-break>` 上。** 分节符的页面属性、页码和页眉页脚属于它后面的新节。`<layout-break>` 除文档级的 `mirror-margins` 和 `odd-even-different` 外支持与 `<layout>` 同名的页面属性；**在 `<layout-break>` 上写这两个属性中的任一个都会整次失败**（`ATTR_VALUE_INVALID`），不是忽略。奇偶页不同和镜像页边距只能在文档级 `<layout>` 上设置。缺省属性表示继承前一节，不表示清零。
- 自动分页由渲染器完成，不要人为为每页插入 `<page-break/>`。

### 分栏 `<columns>`

- 每个 `<layout>` / `<layout-break>` 至多一个 `<columns>`。设置时 `count` 为正整数，`equal-width` 必填。
- Fetch 会把底层 OOXML 省略 `num` / `equalWidth` 的合法分栏规范化为 `count="1"`、`equal-width="true"`；更新时保留 Fetch 返回的显式 canonical 值，不要再省略。
- 等宽模式 `equal-width="true"` 禁止 `<column>` 子节点，可选正长度 `gap` 与布尔 `separator`。
- 非等宽模式 `equal-width="false"` 要求 `<column>` 数量等于 `count`，每栏显式写正长度 `width`，可选正长度 `gap-after`；不推算缺省末栏宽度。
- `<columns remove="true"/>` 清除 direct columns，不能同时写其他属性或子栏。`<column>` 只用于这里，不是正文顶层标签，也没有独立 block ID。

## 页眉页脚页码域

| 标签 | 含义 | 属性 |
|---|---|---|
| `<page-number/>` | 当前页码域 | `format`：`decimal`、`upper-roman`、`lower-roman`、`upper-letter`、`lower-letter` |
| `<page-count/>` | 总页数域 | `scope`：`document`、`section`；`format` 同 `<page-number/>` |

## 脚注与尾注设置

`<layout>` / `<layout-break>` 可包含 footnote 和 endnote 各一个 `<note-settings>`。属性值域、逐项 `clear` 语义和 Note graph 约束查询 `xml:note`。设置缺席表示保留，不支持整体 `remove="true"`。