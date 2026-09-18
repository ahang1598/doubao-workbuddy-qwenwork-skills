# 本地 Word XML：表格

本页定义表格结构、列宽、行高、单元格属性、合并关系及自动归一化规则。

> 使用前须完整读取本页；未见末行「全文完」时，调整 offset 继续读取至该标记。

公共结构、颜色、单位和转义先读 [`canvas-doc-xml.md`](canvas-doc-xml.md)；表格命令和单元格内容替换读 [`canvas-doc-update-table.md`](../cli/canvas-doc-update-table.md)。

最小单元格内容为 `<td><p>文本</p></td>`；涉及内部富文本、段落格式、列表、书签或需要保真回放这些结构时，加读 [`canvas-doc-text.md`](canvas-doc-text.md)，涉及图片时加读 [`canvas-doc-media.md`](canvas-doc-media.md)。不展开无关能力文件。

## 结构示例

```xml
<table width="80%" align="center" border="single 0.75pt #808080" cell-padding="6pt">
  <colgroup>
    <col width="120"/>
    <col width="180"/>
  </colgroup>
  <thead>
    <tr height="24pt" height-rule="exact" repeat-header="true">
      <th background-color="#F2F2F2" vertical-align="middle">
        <p align="center"><b>姓名</b></p>
      </th>
      <th background-color="#DDEBF7" vertical-align="middle">
        <p align="center"><b>状态</b></p>
      </th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td rowspan="2" vertical-align="middle" cell-padding="6pt">
        <p align="center">研发部</p>
      </td>
      <td background-color="#E2F0D9"><p>在线</p></td>
    </tr>
    <tr><td><p>休假</p></td></tr>
  </tbody>
</table>
```

## 属性与结构规则

- `<table width>` 支持正数值加 `pt|cm|mm|in`、`0%..100%`、`auto`、`nil`、`clear`。缺席保持当前 direct preferred width，`clear` 删除它。
- `<table align>` 支持 `left|center|right|clear`。缺席保持当前 direct alignment，`clear` 删除它。
- `<colgroup>` 紧跟 `<table>` 开始标签，用 `<col width="...">` 定义列宽。**`<col width>` 只接受不带单位的正整数，或小数部分最多两位的正小数**（如 `width="120"`、`width="120.5"`、`width="120.25"`），数值按 `px` 解释。写 `120pt` 或超过两位小数不是「保持原值」——它返回 `ATTR_ENUM_INVALID_DROPPED` 并把该列**重置成默认列宽**，`span` 写错同理。数值沿用 fetch 返回值，不要自行换算。
- `<tr height>` 支持非负数值加 `pt|cm|mm|in`，并且必须同时写 `height-rule="auto|at-least|exact"`；`height="clear"` 显式删除 direct row height，且不得携带 `height-rule`。小于 Word 0.1cm 下限的值会钳到 57 twips，`auto` 会规范化为 `at-least`。
- 有表头时使用 `<thead>/<th>`；数据行使用 `<tbody>/<td>`。
- `<tr repeat-header="true|false">` 控制跨页重复表头，是 direct row property，与 `<thead>` 的产品表头语义独立。值为 true 的行必须从首行形成连续前缀；清除 direct 属性使用 `remove-repeat-header="true"`，与 `repeat-header` 互斥。
- `<table>`、`<td>`、`<th>` 有独立 Record；`<tr>`、`<col>` 没有。
- 单元格垂直对齐用 `vertical-align="top|middle|bottom"`；文字水平对齐用内部 `<p align="...">`。
- 合并单元格只输出起始格的 `rowspan` / `colspan`，被覆盖的格不要重复出现。
- `border` 使用“样式 宽度 颜色”，三段顺序可互换或缺省，宽度只接受 `pt`；`none` 表示无边框。四向边框使用 `border-top/right/bottom/left`，内部网格线使用 `border-inside-h/v`，单元格对角线使用 `border-tl2br/tr2bl`。`<td>` / `<th>` 支持同一套 `border-*` 属性。
- 无表级边框时，Fetch 会规范化输出六个 `border-*=none`；以返回结果为准保留即可。
- `cell-padding` 及四向 `cell-padding-top/right/bottom/left` 只接受单值 `pt` 或 `auto`，不支持 CSS 多值简写。`<td>` 和 `<th>` 都支持。
- 底色使用 `background-color`；除统一颜色文法外，表格底色还接受 `none` 清除。
- 改单元格内容用 `<td>` / `<th>` ID + `block_replace`；增删行列、合并拆分和已支持的单元格属性用对应的 [`table_*`](../cli/canvas-doc-update-table.md) 命令。修改整表 width/align、行高或列宽等仅由完整 `<table>` 表达的属性时，以最新完整表格 XML 为底稿执行 `block_replace`，只改目标属性并保留全部 table/row/cell/column ID、文本和合并关系；写后重新 fetch。
- 修改 `<table width>` 会同步 table、grid、column 和 source-cell 几何；不能只改 `<table width>` 后删掉或覆盖 Fetch 返回的 `<colgroup>`。
- 表格既可作为正文顶层块，也可放在页眉页脚 story 或递归放在 `<td>/<th>` 内；不得放进列表项。嵌套表格拥有独立 topology，最大深度 8，单次转换总表数最多 1000；系统还会校验 story owner-chain、parent/cycle 和 record 上限，失败时不得拆散结构或跨 story 复用 ID 绕过。
- 表格单元格内图片使用 `<td><p><img/></p></td>` 和既有图片资源流程，不存在表格专属图片语法。
- 表格文字环绕/浮动布局尚未开放 XML 写入。即使读取快照含相关内部字段，也不要为 `<table>` 写 floating、anchor、distance 或 wrap 属性；不能套用图片或 Drawing 的浮动布局语法。
- 以下三种结构问题同样是**整次失败**而不是丢弃：表格没有任何 `<tr>` 或没有任何列；`rowspan` 超出表格行数；唯一的 `<thead>` 行不在首行（底层快照只能把首行表达成表头）。
- `<tfoot>` 尚未实现，写入会返回 `BLOCK_NOT_IMPLEMENTED_TAG`。

## 自动归一化

以下三种写法不会失败，会被自动改写并返回诊断。看到对应诊断说明结构被调整过，回读时应确认结果符合预期：

| 写法 | 归一化结果 | 诊断 |
|---|---|---|
| `<td>裸文本</td>`、`<td><b>行内内容</b></td>`、`<td><img/></td>` | 行内内容和 `<img>` 自动用 `<p>` 包裹 | `REPAIR_CHILD_WRAPPED` |
| `<thead>` 里写了多行 | 第二行及之后自动降进 `<tbody>`，产品表头只表达一行；跨页多行重复用从首行连续的 `repeat-header`，不要求多行 `<thead>` | `REPAIR_NODE_DEMOTED` |
| `<col id="..." span="2"/>` | `span` 大于 1 表示这是一条新的列宽声明，`id` 被忽略 | `REPAIR_ATTR_IGNORED` |

===== 全文完 =====
