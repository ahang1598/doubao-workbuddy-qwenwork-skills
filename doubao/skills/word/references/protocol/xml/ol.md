---
keyword: xml:ol
---

**功能**：有序/无序列表、连续新树跨层编号模板与嵌套规则

# 本地 Word XML：文本、段落与列表

用于段落、标题、富文本、公式、列表、制表位、书签和受限 SYMBOL 域。

## 按需读取

普通列表看下方属性表。列表预设、标记和多级编号各有示例。

列表项的段落属性、制表位和书签查询 `xml:p`；行内内容查询 `xml:span`；列表内标题同时查询 `xml:h1`。必须保留的特殊结构也须读取对应规则，不加载无关枚举，不通过删格式或对象减少读取。

公共结构、寻址、颜色、单位和转义查询 `xml:common`，不查询无关能力。

---

## 列表

```xml
<ol list-preset="ordered-upper-roman-multilevel-dot" marker-template="%1." marker-align="right" marker-suffix="space">
  <li seq="1">第一项</li>
  <li seq="2" marker-font-size="14pt" marker-text-color="#FF0000">
    第二项
    <ul list-style-type="diamond"><li>子项</li></ul>
  </li>
</ol>
```

- 新增列表项必须放在 `<ul>` 或 `<ol>` 内；空的 `<ol>` / `<ul>` 不合法。
- **列表项不只有 `<li>`：`<h1>`～`<h9>` 同样可以直接作为 `<ol>` / `<ul>` 的子节点**，表示「这一项同时是标题」。fetch 会原样返回这种形状，例如 `<ol list-style-type="decimal"><h2 id="..." seq="2" align="center">章节标题</h2><li id="...">普通项</li></ol>`。这不是畸形结构，不要把它改写成 `<li>`；`seq` 在这种标题项上同样有效，段落属性（`align`、`keep-next` 等）也照常可用。
- 嵌套子列表放在父 `<li>` 内，最多 9 层。
- 一个 `<li>` 的行内内容必须全部写在嵌套子列表**之前**；子列表之后不能再跟文本。
- 未计划调整的真实 `seq` 和嵌套层级应保留；用户要求重新组织列表时，按列表重组与保留项确定新的起始／接续关系。不要猜测 Word 内部 `numId` / `ilvl`。
- `<li seq>` 接受 `auto`、`copy` 或正整数；没有 `seq-auto` 属性。`seq` 只对有序列表项有效，`<ul>` 里的 `<li seq>` 会被忽略并返回诊断。
- `<li>` 里多包的一层 `<p>` 会被自动解包（`REPAIR_CHILD_UNWRAPPED`）。
- **列表项的替换必须连列表容器一起写。** 目标传 `<li>` 的 block ID，但 content 写裸 `<li>…</li>` 会失败（`BLOCK_INVALID_PARENT`）；容器形状示例是 `<ol list-style-type="decimal"><li id="<原 li id>">新内容</li></ol>`。实际载荷仍须保留原项和容器的非目标属性；写回原 `id` 只保留该项身份，不保证其他同级项的容器归属与编号不变。单项载荷范围见 `local-update`。

`list-style-type` 是封闭枚举，写入不在表内的值会被丢弃。它只作用于当前列表容器，不向嵌套列表传播。

有序列表（`<ol>`）：

`decimal`、`decimal-zero`、`upper-roman`、`lower-roman`、`upper-letter`、`lower-letter`、`ordinal`、`cardinal-text`、`ordinal-text`、`chinese-counting`、`chinese-legal-simplified`、`chinese-counting-thousand`、`decimal-enclosed-circle`、`decimal-enclosed-paren`、`numberIn-dash`。

无序列表（`<ul>`）：

`disc`、`circle`、`square`、`white-square`、`diamond`、`white-diamond`、`dash`、`arrow`、`check`、`none`。

### 新建连续跨层编号

```xml
<ol marker-template="%1.">
  <li>第一章
    <ol marker-template="%1.%2">
      <li>第一节</li>
      <li>第二节</li>
    </ol>
  </li>
  <li>第二章
    <ol marker-template="%1.%2"><li>第一节</li></ol>
  </li>
</ol>
```

预期显示顺序为 `1. / 1.1 / 1.2 / 2. / 2.1`。新树整体通过合法插入命令提交，不逐层拆成独立列表。

### 列表预设

`list-preset` 使用当前 Word 工具栏 preset。新建列表时会生成完整多级模板；替换已有列表时只更新当前绝对层级，保留实例起始值、其他层级和协议未拥有的编号属性。`list-preset` 与 `list-style-type` 同时出现时以 `list-preset` 为准，并返回 `ATTR_MUTUALLY_EXCLUSIVE` 诊断。

有序列表 preset：

`ordered-decimal-dot`、`ordered-decimal-parenthesis`、`ordered-chinese-counting-comma`、`ordered-chinese-counting-parenthesis`、`ordered-legal-decimal-dot`、`ordered-upper-letter-multilevel-dot`、`ordered-upper-roman-multilevel-dot`、`ordered-decimal-zero-dot`、`ordered-decimal-enclosed-circle`、`ordered-lower-letter-parenthesis`、`ordered-lower-letter-multilevel-dot`、`ordered-chinese-counting-dot`、`ordered-lower-alpha-dot`、`ordered-upper-alpha-dot`、`ordered-lower-roman-dot`、`ordered-upper-roman-dot`。

无序列表 preset：

`bullet-multilevel-disc-circle-square`、`bullet-multilevel-diamond-arrow-square`、`bullet-multilevel-hollow-square`、`bullet-disc`、`bullet-arrow`、`bullet-hollow-square`、`bullet-circle`、`bullet-square`、`bullet-diamond`、`bullet-fancy-diamond`、`bullet-check`、`bullet-star`。

### 列表标记

- `marker-template` 仅 `<ol>` 支持，非空、无控制字符、长度不超过 64 字符且至少包含一个合法占位符。第 N 层可引用 `%1`…`%N`，例如一级 `%1.`、二级 `%1.%2`；禁止 `%0`、未来层引用（一级 `%2`、二级 `%3`）或超出 9 层的占位符。
- 跨层模板首期仅支持从第一层开始新建一个连续有序列表树，不混合有序与无序列表，同一列表项最多一个连续子列表；同一树各层共享新编号实例，父层计数参与子层展开。同一绝对层级重复出现的模板和层定义必须一致；二级 `%1.%2` 与 `%2)` 等同层冲突须在规划时拒绝。相邻 `<ol>` 仍是独立树，不能按相同外观合并。既有列表的内容编辑继续保留树边界、起始/接续关系和非目标层定义，不借新建能力改写目标外共享编号定义。
- `marker-symbol` 仅 `<ul>` 支持，必须是单个非空、非控制字符、非私有区 Unicode code point。
- `marker-align` 取 `left` / `center` / `right`；`marker-suffix` 取 `tab` / `space` / `nothing`。
- `marker-*` 字符格式写在 `<li>` 或列表内的 `<h1>`～`<h9>` 上，仅影响该项的 marker，不影响正文 `<span>`。支持 `marker-font-size`、`marker-font-family`、`marker-font-family-ascii`、`marker-font-family-east-asia`、`marker-font-family-h-ansi`、`marker-font-family-cs`、`marker-font-hint`、`marker-text-color`、`marker-background-color`、`marker-bold`、`marker-italic`、`marker-line-through`、`marker-character-scale`、`marker-border-style`、`marker-border-width`、`marker-border-color`。

上述 16 个字符格式属性均支持 `clear`：缺席保留原 direct 声明，`clear` 删除对应 direct 声明并恢复继承；`false` 或 `none` 是显式关闭，不能与 `clear` 混同。

| 属性 | 非 clear 值与写入规则 |
|---|---|
| `marker-font-size` | 带 `pt` 或 `px` 的非负十进制数，数值至少 0.5；量化为 half-point，同时设置普通与复杂脚本字号，读取结果返回规范化值 |
| `marker-font-family`、四个 `marker-font-family-*` direct 槽 | 去除首尾空白后非空、无控制字符的字体名；统一字体与分槽规则见下文 |
| `marker-font-hint` | `default`、`eastAsia`、`cs` |
| `marker-text-color`、`marker-background-color`、`marker-border-color` | 不透明统一颜色文法；不接受 alpha 小于 1 |
| `marker-bold`、`marker-italic` | `true`、`false`；无序列表限制见下文 |
| `marker-line-through` | `single`、`double`、`none` |
| `marker-character-scale` | `1%`～`999%` 的整数百分比 |
| `marker-border-style` | 字符边框线型的 23 个值 |
| `marker-border-width` | 非负 `<n>pt`，量化到 1/8 pt；不接受裸数或 px |

`marker-font-family` 会先清除四个 direct 字体槽、四个 theme 字体槽及 hint，再把四个 direct 槽设为指定字体；值为 `clear` 时只清除。分槽属性和 `marker-font-hint` 随后生效，各自只修改对应槽。只改一个字体槽时用分槽属性，避免通过统一字体清除原有主题引用；其他未点名的 marker 属性保持不变。

无序列表不支持修改或清除 `marker-bold`、`marker-italic`，写入时返回 `ATTR_CAPABILITY_LIMITED`。使用 `marker-text-color="clear"` 清除直接设置的编号颜色，继承的颜色可能继续生效，原有粗体等其他格式保持。工具无法完整表达某些编号格式时会返回 `COMPAT_STYLE_LOST`。

协议不暴露 Word 内部的编号原语（`numId`、`ilvl`、原始编号格式串、原始层级文本模板或 `lvlRestart`）。已有文档里的复杂编号在只改列表内容或未点名的列表属性时会原样保留；可设置的编号方案见上文的属性表。

## 更新约束

段落对齐、间距、制表位、单 carrier 书签、单双删除线和受限 `<symbol/>` 均通过完整 `block_replace` 更新；仅专项明确支持的属性按“缺席保持”处理；其他属性仍须完整回放，不能把局部 patch 语义推广到整个 block。清除必须使用 `clear`、`<tabs/>` 或 `<span line-through="none">` 等显式写法。以最新完整 Fetch XML 为底稿，只修改目标内容或属性。