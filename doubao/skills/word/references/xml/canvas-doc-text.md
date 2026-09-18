# 本地 Word XML：文本、段落与列表

用于段落、标题、富文本、公式、列表、制表位、书签和受限 SYMBOL 域。

## 按需读取

**公共必读**：[文档与标题](#文档与标题)、[行内样式嵌套](#行内样式嵌套)、[更新约束](#更新约束)。再按本次修改及必须保留的结构读取：

| 涉及内容 | 补读章节 |
|---|---|
| 段落/标题属性，包括段前分页 | [段落](#段落)正文与属性表 |
| 文字或字符格式 | [富文本](#富文本)正文与属性表、[局部文字与格式修改](#局部文字与格式修改) |
| 下划线、字符边框、底纹 | 对应的[下划线类型](#下划线类型)、[字符边框线型](#字符边框线型)、[字符底纹图案](#字符底纹图案) |
| 公式、段内换行、SYMBOL | 对应的[公式](#公式)、[段内换行](#段内换行)、[高级符号](#高级符号) |
| 制表位、书签 | 对应的[制表位](#制表位)、[书签](#书签) |
| 列表或列表内的标题 | [列表](#列表)（含预设与标记子节） |

章节完整读至下一同级或更高级标题；标明“正文”时读至第一个子标题，子节按表补齐。只改段落属性且完整保留原普通行内结构时，无需加载无关字符枚举；原有书签、公式、列表等特殊结构即使不修改也须读对应规则，Field/Note/Drawing 等继续加载各自专项。组合结构取所涉规则并集，不通过删格式或对象减少读取。同轮已完整读取且仍可见的章节直接复用。

公共结构、寻址、颜色、单位和转义先读 [`canvas-doc-xml.md`](canvas-doc-xml.md)，不展开无关能力文件。

## 文档与标题

```xml
<h1>一、项目背景</h1>
<h2>（一）现状</h2>
<p>正文段落。</p>
```

- 标题层级不要跳级。
- 精确更新已有块时，通过命令的 `--block-id` 定位；写入内容不要自行伪造 fetch 返回的 block `id`。
- **新增标题依赖文档已有的标题样式。** 写 `<h2>变更记录</h2>` 时，会去文档的样式表里反查对应层级的 Word 标题样式；文档里没有定义该层级的标题样式时整条指令失败，不会退化成假标题。带显式格式的 `<p>` 仍是普通段落，不具备标题层级、目录收录或导航语义。

## 行内样式嵌套

Fetch 返回的行内标签按固定顺序嵌套，由外向内是：

```text
<b> → <em> → <del> → <u> → <sup>/<sub> → <span> → 文本
```

- Fetch 按此顺序输出，使相同样式对应相同标签树。写入不校验嵌套顺序，任意顺序均可解析；沿用 fetch 顺序便于写后比较。
- `<strong>`、`<i>`、`<s>` / `<strike>`、`<text>` 会分别归一为 `<b>`、`<em>`、`<del>`、`<span>`。
- `<sup>` 和 `<sub>` 是具体语义节点，不要为了满足顺序强行包进无意义的 `<span>`。

## 富文本

```xml
<p>
  <b>加粗</b>
  <em>斜体</em>
  <u text-decoration-style="double">双下划线</u>
  <del>单删除线</del>
  <del text-decoration-style="double">双删除线</del>
  <span line-through="none">关闭继承的删除线</span>
  <span font-family-east-asia="黑体" font-family-ascii="黑体" font-family-h-ansi="黑体" font-hint="eastAsia" font-size="14pt">中文黑体 14pt</span>
  <span text-color="#FF0000" background-color="#FFFF00">彩色高亮</span>
  <span border-style="single" border-color="#000000" border-width="1pt">字符边框</span>
  <span character-scale="80%" character-spacing="2px">缩放与字距</span>
  x<sup>2</sup> H<sub>2</sub>O
</p>
```

| 能力 | 标签 / 属性 | 取值说明 |
|---|---|---|
| 加粗、斜体 | `<b>`、`<em>` | 标签语义不变 |
| 删除线 | `<del text-decoration-style="...">` | `single` 或 `double`；缺省为 `single` |
| 下划线 | `<u text-decoration-style="...">` | 17 个合法值，见下表 |
| 统一字体 | `<span font-family="宋体">` | 为文本设置统一字体名 |
| 中文或中西文混排字体 | `font-family-east-asia`、`font-family-ascii`、`font-family-h-ansi`、`font-family-cs` | 编辑时保留原字体槽；新建且没有现有格式基准、或用户要求统一字体时，才将四槽设为同一字体；要求中西文不同字体时分别设置 |
| 主题字体与提示 | `font-family-ascii-theme`、`font-family-east-asia-theme`、`font-family-h-ansi-theme`、`font-family-cs-theme`、`font-hint` | 引用已有主题字体，见下文；`font-hint` 取 `default`、`eastAsia` 或 `cs` |
| 字号 | `font-size` | 非负十进制数且数值至少 0.5，必须带 `pt` 或 `px`，例如 `12pt`、`16px`；写入量化为 half-point，回读以规范化值为准 |
| 字体与下划线颜色 | `text-color`、`underline-color` | 使用统一颜色文法 |
| 高亮/纯色底色 | `background-color` | 使用统一颜色文法 |
| 字符底纹 | `shading-fill`、`shading-foreground-color`、`shading-pattern` | 仅用于 `<span>`；`shading-pattern` 取值见下方枚举 |
| 字符边框 | `border-style` + `border-color` + `border-width` | `border-style` 取 23 个线型之一，见下方枚举；宽度只接受 `pt` |
| 字符缩放 | `character-scale` | 必须是带百分号的整数，范围 `1%`～`999%` |
| 字符间距 | `character-spacing` | 必须带 `pt` 或 `px`，可为负数 |
| 显式关闭继承样式 | `bold`、`italic`、`underline`、`line-through` | 前两者取布尔值；后两者只取 `none` |
| 上标、下标 | `<sup>`、`<sub>` | — |
| 段内换行 | `<br/>` | 空元素，等价于 Word 里的 Shift+Enter；见下方说明 |
| 公式 | `<equation input_mode="latex" alignment="center" layout="inline">x^2</equation>` | 正文为公式源文本；三个属性均可省略 |

主题字体属性引用文档现有主题，不创建或修改 theme 定义。常用规范值为 `majorEastAsia`、`majorBidi`、`majorAscii`、`majorHAnsi`、`minorEastAsia`、`minorBidi`、`minorAscii`、`minorHAnsi`；XML 接受非空引用字符串，已有值以 Fetch 为准。只改其他属性时保留原有 direct/theme 字体槽，不为统一字体无意删除主题绑定。

字符样式（Word character style）没有协议属性，Fetch 不输出字符样式引用，也不会把它继承的格式展开为上述直接格式属性。因此，XML 中缺少某个格式属性不代表文本的最终显示没有该格式，不能只凭 XML 验收继承样式的视觉效果。更新仍保留原有文本结构与所有已返回属性；未暴露的字符样式引用由宿主合并保留，跨越不同样式的替换区间只继承共有的可保留属性，须检查兼容性诊断。不要自行写 `style-id` 或把继承样式重建成直接格式。

### 局部文字与格式修改

基于最新 `full` XML 的原节点修改文字，保留段落属性、每段文字的样式标签和全部非目标属性；不要从纯文本重建无格式的 `<p>/<span>`。局部加粗允许在目标边界拆分原 span，但拆出的每一段都复制原属性，只有目标文字增加 `<b>`；若目标原有 `bold="false"`，须一并移除或改为 `true`。其他非目标样式和节点边界保持不变。

例如，假设 Fetch 返回以下完整段落（示例字体不是默认值）：

```xml
<p id="p1" align="center"><span font-family-east-asia="宋体" font-size="12pt">计划周五发布。</span></p>
```

将“周五”改成“周六”并仅将修改处加粗，提交：

```xml
<p id="p1" align="center"><span font-family-east-asia="宋体" font-size="12pt">计划</span><b><span font-family-east-asia="宋体" font-size="12pt">周六</span></b><span font-family-east-asia="宋体" font-size="12pt">发布。</span></p>
```

实际段落有更多属性或混合格式时全部沿用；修改跨多个原 span 时分别保留各自格式，不把整段统一成一个 span。无法明确新文字到原格式的映射时缩小改动，不凭空挑一种格式覆盖。

### 公式

```xml
<p id="p1">勾股关系：<equation>x^2+y^2=z^2</equation></p>
<p id="p2"><equation input_mode="unicode-math" alignment="right" layout="block">α/β</equation></p>
```

- `<equation>` 是行内特殊对象，不是 block；必须位于段落、标题、列表项或支持的行内格式容器中。`layout="block"` 仍是 carrier 内的公式，不能放到 XML 顶层。正文只允许文本或 CDATA，不允许嵌套 `<b>`、`<span>` 等子元素。
- 正文是公式源文本，按 `input_mode` 解释；UnicodeMath 输入会在内部转换为 canonical LaTeX。允许 `<equation></equation>` 表示空公式。正文保留换行，XML 特殊字符使用实体转义或 CDATA。
- `input_mode` 取 `latex|unicode-math`，默认 `latex`；`alignment` 取 `left|center|right`，默认 `center`；`layout` 取 `inline|block`，默认 `inline`。输出省略默认属性。
- `<equation>` 没有 `id` 属性并严格校验属性；`id`、`source`、其他未知属性及非法枚举都会使请求失败。
- 新建通过 `append`、`block_insert_after` 或 `block_replace` 提交含公式的完整 carrier；修改或删除已有公式时，用 `block_replace` 定位宿主 carrier，并在完整 XML 中更新或省略对应 `<equation>`。`str_replace` 不能创建、修改或删除公式。

### 下划线类型

`text-decoration-style` 使用 Roadster DSL 的 `UnderlineStyleType` 原值，大小写敏感：

| 值 | 效果 |
|---|---|
| `single` | 单下划线 |
| `words` | 仅文字下划线，不为词间空格加线 |
| `double` | 双下划线 |
| `thick` | 粗下划线 |
| `dotted` | 点状下划线 |
| `dottedHeavy` | 粗点状下划线 |
| `dash` | 短划线下划线 |
| `dashedHeavy` | 粗短划线下划线 |
| `dashLong` | 长划线下划线 |
| `dashLongHeavy` | 粗长划线下划线 |
| `dotDash` | 点划线下划线 |
| `dashDotHeavy` | 粗点划线下划线 |
| `dotDotDash` | 双点划线下划线 |
| `dashDotDotHeavy` | 粗双点划线下划线 |
| `wave` | 波浪下划线 |
| `wavyHeavy` | 粗波浪下划线 |
| `wavyDouble` | 双波浪下划线 |

不要自行改写枚举名称，例如单下划线使用 `single`，短划线使用 `dash`。

`<u>` 没有 `none`：不写 `<u>` 表示不启用下划线；压制样式链继承使用 `<span underline="none">`。

`<del>` 没有 `none`：不写 `<del>` 表示不新增删除线；压制样式链继承的单/双删除线使用 `<span line-through="none">`。已有脏数据同时包含单删除线和双删除线时，Fetch 以双删除线输出。

### 字符边框线型

`<span border-style>` 使用 OOXML `w:val` 线型枚举，大小写敏感，只接受以下 23 个值：

`single`、`double`、`dashed`、`dotted`、`threeDEmboss`、`threeDEngrave`、`thickThinSmallGap`、`thick`、`thin`、`medium`、`hair`、`dashDotDot`、`dashDotStroked`、`dashSmallGap`、`dotDash`、`dotDotDash`、`wave`、`doubleWave`、`inset`、`outset`、`triple`、`none`、`nil`。

`<img border-style>` 用的是另一套枚举，不要互相套用；图片线型见 [`canvas-doc-media.md`](canvas-doc-media.md#图片边框线型)。

### 字符底纹图案

`shading-pattern` 只接受以下取值：

- 无图案：`nil`、`clear`、`solid`；
- 条纹与交叉线：`diagCross`、`diagStripe`、`reverseDiagStripe`、`horzCross`、`horzStripe`、`vertCross`、`vertStripe`、`thinDiagCross`、`thinDiagStripe`、`thinHorzCross`、`thinHorzStripe`、`thinReverseDiagStripe`、`thinVertStripe`；
- 百分比网点：`pct0` 到 `pct100`，可带小数，如 `pct12.5`。

### 段内换行

段内换行（Word 里的 Shift+Enter）用空元素 `<br/>` 表达，它是唯一有效写法：

```xml
<p>第一行<br/>第二行</p>
```

- `<p>`、`<h1>`～`<h9>`、`<li>` 和单元格内的 `<p>` 都可以使用。
- **XML 源码里的裸换行字符是不显著空白，会被丢弃并返回诊断（`REPAIR_TEXT_NORMALIZED`）。** 这意味着为了可读性给 XML 加缩进和折行是安全的，不会在正文里凭空多出换行或空格；反过来，靠打一个真实换行来断行不会生效。
- 清理时**连换行两侧的空格和制表符一起删掉**。标签之间折行缩进因此是安全的，但不要在一段英文句子中间折行——`hello` 折行 `world` 会粘成 `helloworld`。
- 段内换行不等于新段落。需要新段落时写两个 `<p>`。

### 高级符号

普通 Unicode 字符直接写在文本中。只有需要保留 Word `SYMBOL` 域身份时才使用空元素 `<symbol/>`：

```xml
<p>
  Unicode 文本：∞
  <symbol code="0x221E" unicode="true" font-family="Cambria Math" font-size="12pt"/>
  <symbol code="0xA9" unicode="false" font-family="Symbol"/>
</p>
```

| 属性 | 取值 |
|---|---|
| `code` | 必填；十进制或 `0x` 十六进制 Unicode scalar，拒绝 surrogate、负数和大于 `0x10FFFF` 的值 |
| `unicode` | 必填；`true` 或 `false` |
| `font-family` | Unicode 分支可选；legacy 分支必须为 `Symbol` |
| `font-size` | 可选；十进制数值至少 0.5 的 `pt` 长度，例如 `12pt` |

- `unicode=true` 允许合法 Unicode scalar。
- `unicode=false` 只允许已核对的 `0xA9 -> ♥` 和 `0xD3 -> ©`；其他 legacy code 或非 `Symbol` 字体整次失败。
- `<symbol>` 不能包含文本或子元素，也不能传 field id、原始 instruction、cached result 或 switch。
- `<symbol>` 是不可拆分的行内对象；修改或删除时必须覆盖整个域。
- 系统生成完整 S/P/E markers。Fetch 只把完整、单层且可稳定求值的 SYMBOL field 输出为 `<symbol/>`；其他情况不输出可再次写入的 `<symbol/>`。

`SEQ`、`REF`、`PAGEREF`、`NOTEREF` 使用 [`canvas-doc-field-note.md`](canvas-doc-field-note.md) 的 `<field>`；自动目录仍先读 [`canvas-doc-update-domain.md`](../cli/canvas-doc-update-domain.md) 使用领域命令。日期时间域、任意原始 instruction 或其他通用域向 [`canvas-doc.md` 的 CLI 能力门禁](../workflows/canvas-doc.md#第三层最少必要读取cli-能力与调用预算) 输出 `local_unsupported`；目录只按 [`canvas-doc-toc.md`](canvas-doc-toc.md) 使用 CLI，不支持时停止。`<page-number/>`、`<page-count/>` 和 `<symbol/>` 继续使用既有标签。

## 段落

```xml
<p align="justify" line-indent="2ch" first-line-indent="2ch" line-height="1.5" keep-lines="true">
  两端对齐、左缩进和首行缩进 2 字符、1.5 倍行距，并保持段中不分页。
</p>
```

| 属性 | 取值与说明 |
|---|---|
| `type` | 仅 `<p>`：`text`（默认）、`bullet`、`ordered` |
| `align` | `left`、`center`、`right`、`justify`、`distribute`、`clear`；缺席保持原 direct 值，`clear` 删除 direct 值 |
| `spacing-before` / `spacing-after` | 非负数值加 `pt`、`cm`、`mm` 或 `in`；`0pt` 是显式零，`clear` 删除 direct 值 |
| `spacing-before-auto` / `spacing-after-auto` | `true`、`false` 或 `clear`；缺席保持，`clear` 删除 direct 值 |
| `line-indent` | 非负数值加 `ch`、`px` 或 `pt`，例如 `2ch`、`18pt`；负值会被丢弃 |
| `first-line-indent` | 同上；与 `hanging-indent` 互斥，同写时按 `hanging-indent` 生效并返回 `ATTR_MUTUALLY_EXCLUSIVE` 警告，不是失败 |
| `hanging-indent` | 同上；与 `first-line-indent` 互斥，同写时它胜出 |
| `line-height` | 倍率裸数字，如 `1.15`；或 `exact 12pt`、`at-least 12pt`，后两种只接受 `pt` |
| `page-break-before` | `true` / `false`，段前分页 |
| `keep-next` | `true` / `false`，与下段同页 |
| `keep-lines` | `true` / `false`，段中不分页 |
| `widow-control` | `true` / `false`，孤行控制 |

除 `type` 外，这些属性也可按 fetch 返回结构用于标题或表格单元格中的 `<p>`。不要用空格模拟缩进或居中。

`line-indent` 只表达物理左缩进。若最新 Fetch 显示目标仍依赖 Word 的逻辑方向 `start/end` 缩进，不要用 `line-indent` 覆盖；当前更新会 fail closed，向入口输出 `local_unsupported`。

### 制表位

普通制表位不通过 CLI 新增、编辑；目录的更新除外。

```xml
<p id="p1"><tabs><tab position="432pt" align="right" leader="dot"/></tabs>标题	12</p>
```

- `<tabs>` 只定义制表位；正文需在跳转处包含真实 Tab 字符（U+0009，常记作 `\t`；上例位于“标题”和“12”之间），否则不会产生跳转或引导符。不要提交字面量反斜杠和字母 `t`。
- `<tabs>` 缺席表示保持，`<tabs/>` 删除全部 direct tabs，非空容器完整替换；必须位于可见内容之前。
- `position` 为非负 `pt|cm|mm|in|ch`；`align` 为 `left|center|right|decimal|bar|clear`；`leader` 为 `none|dot|hyphen|underscore|heavy|middleDot`。`ch` 是写入输入单位，会按冻结目标段落所属 section 的字符网格与 Normal 有效字号换算，Fetch 统一回显 `pt`；共享页眉/页脚在所引用 section 间字符宽度不一致时会拒绝写入。

### 书签

```xml
<p id="p1">A<bookmark-start id="request-1" name="Target"/>B<bookmark-end id="request-1"/>C</p>
```

- 新建或删除书签时，start/end 必须在同一 `<p>`、`<h1>`～`<h9>` 或 `<li>` 内完整配对。
- Fetch 可以返回同一 Word story 内跨 textual carrier 的 start/end，但公开更新链路将其视为只读；不得创建、删除、修改任一边界、删除其 carrier，或拆成多个 `block_replace` 写回。
- 新建时 `id` 仅用于请求内配对；名称以 Unicode 字母开头，后续最多 39 个字母、组合标记、数字或下划线，并按 Word Unicode case-fold 判重。
- 删除时只移除对应边界，保留中间内容和其他书签。

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
- 未计划调整的真实 `seq` 和嵌套层级应保留；用户要求重新组织列表时，按[列表重组与保留项](../workflows/canvas-doc-editing.md#列表重组与保留项)确定新的起始／接续关系。不要猜测 Word 内部 `numId` / `ilvl`。
- `<li seq>` 接受 `auto`、`copy` 或正整数；没有 `seq-auto` 属性。`seq` 只对有序列表项有效，`<ul>` 里的 `<li seq>` 会被忽略并返回诊断。
- `<li>` 里多包的一层 `<p>` 会被自动解包（`REPAIR_CHILD_UNWRAPPED`）。
- **列表项的替换必须连列表容器一起写。** 目标传 `<li>` 的 block ID，但 content 写裸 `<li>…</li>` 会失败（`BLOCK_INVALID_PARENT`）；容器形状示例是 `<ol list-style-type="decimal"><li id="<原 li id>">新内容</li></ol>`。实际载荷仍须保留原项和容器的非目标属性；写回原 `id` 只保留该项身份，不保证其他同级项的容器归属与编号不变。单项载荷范围及写后验收见 [Update 列表约束](../cli/canvas-doc-update.md#可寻址标签与可用命令)。

`list-style-type` 是封闭枚举，写入不在表内的值会被丢弃。它只作用于当前列表容器，不向嵌套列表传播。

有序列表（`<ol>`）：

`decimal`、`decimal-zero`、`upper-roman`、`lower-roman`、`upper-letter`、`lower-letter`、`ordinal`、`cardinal-text`、`ordinal-text`、`chinese-counting`、`chinese-legal-simplified`、`chinese-counting-thousand`、`decimal-enclosed-circle`、`decimal-enclosed-paren`、`numberIn-dash`。

无序列表（`<ul>`）：

`disc`、`circle`、`square`、`white-square`、`diamond`、`white-diamond`、`dash`、`arrow`、`check`、`none`。

### 列表预设

`list-preset` 使用当前 Word 工具栏 preset。新建列表时会生成完整多级模板；替换已有列表时只更新当前绝对层级，保留实例起始值、其他层级和协议未拥有的编号属性。`list-preset` 与 `list-style-type` 同时出现时以 `list-preset` 为准，并返回 `ATTR_MUTUALLY_EXCLUSIVE` 诊断。

有序列表 preset：

`ordered-decimal-dot`、`ordered-decimal-parenthesis`、`ordered-chinese-counting-comma`、`ordered-chinese-counting-parenthesis`、`ordered-legal-decimal-dot`、`ordered-upper-letter-multilevel-dot`、`ordered-upper-roman-multilevel-dot`、`ordered-decimal-zero-dot`、`ordered-decimal-enclosed-circle`、`ordered-lower-letter-parenthesis`、`ordered-lower-letter-multilevel-dot`、`ordered-chinese-counting-dot`、`ordered-lower-alpha-dot`、`ordered-upper-alpha-dot`、`ordered-lower-roman-dot`、`ordered-upper-roman-dot`。

无序列表 preset：

`bullet-multilevel-disc-circle-square`、`bullet-multilevel-diamond-arrow-square`、`bullet-multilevel-hollow-square`、`bullet-disc`、`bullet-arrow`、`bullet-hollow-square`、`bullet-circle`、`bullet-square`、`bullet-diamond`、`bullet-fancy-diamond`、`bullet-check`、`bullet-star`。

### 列表标记

- `marker-template` 仅 `<ol>` 支持，长度不超过 64 字符，只允许引用当前层级占位符。例如一级列表只能写 `%1`，二级只能写 `%2`。
- `marker-symbol` 仅 `<ul>` 支持，必须是单个非空、非控制字符、非私有区 Unicode code point。
- `marker-align` 取 `left` / `center` / `right`；`marker-suffix` 取 `tab` / `space` / `nothing`。
- `marker-*` 字符格式写在 `<li>` 或列表内的 `<h1>`～`<h9>` 上，仅影响该项的 marker，不影响正文 `<span>`。支持 `marker-font-size`、`marker-font-family`、`marker-font-family-ascii`、`marker-font-family-east-asia`、`marker-font-family-h-ansi`、`marker-font-family-cs`、`marker-font-hint`、`marker-text-color`、`marker-background-color`、`marker-bold`、`marker-italic`、`marker-line-through`、`marker-character-scale`、`marker-border-style`、`marker-border-width`、`marker-border-color`。

上述 16 个字符格式属性均支持 `clear`：缺席保留原 direct 声明，`clear` 删除对应 direct 声明并恢复继承；`false` 或 `none` 是显式关闭，不能与 `clear` 混同。

| 属性 | 非 clear 值与写入规则 |
|---|---|
| `marker-font-size` | 带 `pt` 或 `px` 的非负十进制数，数值至少 0.5；量化为 half-point，同时设置普通与复杂脚本字号，回读以规范化值为准 |
| `marker-font-family`、四个 `marker-font-family-*` direct 槽 | 去除首尾空白后非空、无控制字符的字体名；统一字体与分槽规则见下文 |
| `marker-font-hint` | `default`、`eastAsia`、`cs` |
| `marker-text-color`、`marker-background-color`、`marker-border-color` | 不透明统一颜色文法；不接受 alpha 小于 1 |
| `marker-bold`、`marker-italic` | `true`、`false`；无序列表限制见下文 |
| `marker-line-through` | `single`、`double`、`none` |
| `marker-character-scale` | `1%`～`999%` 的整数百分比 |
| `marker-border-style` | [字符边框线型](#字符边框线型)的 23 个值 |
| `marker-border-width` | 非负 `<n>pt`，量化到 1/8 pt；不接受裸数或 px |

`marker-font-family` 会先清除四个 direct 字体槽、四个 theme 字体槽及 hint，再把四个 direct 槽设为指定字体；值为 `clear` 时只清除。分槽属性和 `marker-font-hint` 随后生效，各自只修改对应槽。只改一个字体槽时用分槽属性，避免通过统一字体清除原有主题引用；其他未点名的 marker 属性保持不变。

无序列表的 `marker-bold` / `marker-italic`（包括 `clear`）写入会返回 `ATTR_CAPABILITY_LIMITED` 并忽略；其他 marker 字符格式按可表达性回读，不能无损表达时会返回 `COMPAT_STYLE_LOST`。例如清除编号颜色使用 `marker-text-color="clear"`，回读核对 direct 颜色已移除，同时保留原有粗体等非目标格式。

协议不暴露 Word 内部的编号原语（`numId`、`ilvl`、原始编号格式串、原始层级文本模板或 `lvlRestart`）。已有文档里的复杂编号在只改列表内容或未点名的列表属性时会原样保留；确实超出 `list-preset`、`list-style-type`、`marker-*` 表达面的编号方案时向入口输出 `local_unsupported`。

## 更新约束

段落对齐、间距、制表位、单 carrier 书签、单双删除线和受限 `<symbol/>` 均通过完整 `block_replace` 更新；仅专项明确支持的属性按“缺席保持”处理；其他属性仍须完整回放，不能把局部 patch 语义推广到整个 block。清除必须使用 `clear`、`<tabs/>` 或 `<span line-through="none">` 等显式写法。以最新完整 Fetch XML 为底稿，只修改目标内容或属性。

===== 全文完 =====
