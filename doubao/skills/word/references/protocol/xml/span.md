---
keyword: xml:span
---

**功能**：行内文字与字符格式、超链接、公式、换行和符号

# 本地 Word XML：文本、段落与列表

用于段落、标题、富文本、公式、列表、制表位、书签和受限 SYMBOL 域。

## 按需读取

文字、格式和行内对象分别看下面的例子与属性表。

| 涉及内容 | 补读章节 |
|---|---|
| 普通超链接 | 普通超链接 |
| 下划线、字符边框、底纹 | 对应的下划线类型、字符边框线型、字符底纹图案 |
| 公式、段内换行、分栏符、SYMBOL | 对应的公式、段内换行、分栏符、高级符号 |

段落和书签见 `xml:p`，标题见 `xml:h1`，列表见 `xml:ol`。

公共结构、寻址、颜色、单位和转义查询 `xml:common`，不查询无关能力。

---

## 行内样式嵌套

Fetch 返回的行内标签按固定顺序嵌套，由外向内是：

```text
<b> → <em> → <del> → <u> → <sup>/<sub> → <span> → 文本
```

- Fetch 按此顺序输出，使相同样式对应相同标签树。写入不校验嵌套顺序，任意顺序均可解析。
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
| 着重号 | `<span emphasis-mark="...">` | `none`、`dot`、`comma`、`circle`、`underDot`；与斜体 `<em>` 独立，见下文 |
| 删除线 | `<del text-decoration-style="...">` | `single` 或 `double`；缺省为 `single` |
| 下划线 | `<u text-decoration-style="...">` | 17 个合法值，见下表 |
| 统一字体 | `<span font-family="宋体">` | 为文本设置统一字体名 |
| 中文或中西文混排字体 | `font-family-east-asia`、`font-family-ascii`、`font-family-h-ansi`、`font-family-cs` | 编辑时保留原字体槽；新建且没有现有格式基准、或用户要求统一字体时，才将四槽设为同一字体；要求中西文不同字体时分别设置 |
| 主题字体与提示 | `font-family-ascii-theme`、`font-family-east-asia-theme`、`font-family-h-ansi-theme`、`font-family-cs-theme`、`font-hint` | 引用已有主题字体，见下文；`font-hint` 取 `default`、`eastAsia` 或 `cs` |
| 字号 | `font-size` | 非负十进制数且数值至少 0.5，必须带 `pt` 或 `px`，例如 `12pt`、`16px`；写入量化为 half-point，读取结果返回规范化值 |
| 字体与下划线颜色 | `text-color`、`underline-color` | 使用统一颜色文法 |
| 高亮/纯色底色 | `background-color` | 使用统一颜色文法 |
| 字符底纹 | `shading-fill`（背景色） / `shading-pattern`（图案类型） / `shading-foreground-color`（图案颜色） | 仅用于 `<span>`；`shading-pattern` 取值见下方枚举 |
| 字符边框 | `border-style` + `border-color` + `border-width` | `border-style` 取 23 个线型之一，见下方枚举；宽度只接受 `pt` |
| 字符缩放 | `character-scale` | 必须是带百分号的整数，范围 `1%`～`999%` |
| 字符间距 | `character-spacing` | 必须带 `pt` 或 `px`，可为负数 |
| 显式关闭继承样式 | `bold`、`italic`、`underline`、`line-through` | 前两者取布尔值；后两者只取 `none` |
| 上标、下标 | `<sup>`、`<sub>` | — |
| 段内换行 | `<br/>` | 空元素，等价于 Word 里的 Shift+Enter；见下方说明 |
| 公式 | `<equation input_mode="latex" alignment="center" layout="inline">x^2</equation>` | 正文为公式源文本；三个属性均可省略 |

主题字体属性引用文档现有主题，不创建或修改 theme 定义。常用规范值为 `majorEastAsia`、`majorBidi`、`majorAscii`、`majorHAnsi`、`minorEastAsia`、`minorBidi`、`minorAscii`、`minorHAnsi`；XML 接受非空引用字符串，已有值以 Fetch 为准。只改其他属性时保留原有 direct/theme 字体槽，不为统一字体无意删除主题绑定。

### 着重号

`emphasis-mark` 大小写敏感，仅接受 `none|dot|comma|circle|underDot`。`<em>` 仍表示斜体，不表示着重号；两者可以同时使用：

```xml
<p><span emphasis-mark="dot">着重号</span><em><span emphasis-mark="underDot">斜体并加下点</span></em><span emphasis-mark="none">显式关闭继承</span></p>
```

- `none` 是显式关闭并阻断继承；在完整 XML 替换中省略该属性会清除该范围的直接着重号声明，随后仍可能继承样式着重号。不要把省略、`none` 和样式 `clear` 混为一谈，也不写 `emphasis-mark="clear"`。纯文本 `str_replace` 沿用命中范围的共有格式，不适合清除着重号。
- 非目标 span 的着重号及其他属性必须完整回放；只改局部文字时按原格式边界拆分。样式定义的 `text.emphasis-mark` set/clear 查询 `style_update`；字符样式绑定查询 `style_apply`，绑定操作保留直接格式。
- 当前属性能力以实际返回的 schema 为准；W0 对应 `docxxml-attributes-v8`。旧 schema 或未暴露该属性时先确认能力，不借本页推断当前宿主已支持。
- 主 Story 同文原位格式写入可使用既有修订链路：接受保留新值，拒绝恢复旧值或旧属性缺席；不扩大非主 Story tracked run 或字符范围 style_apply 的修订支持。普通 Header/Footer 写入仍须按 exact occurrence/placement 定位。
- 样式里的着重号可能在保存并重新打开后丢失，见 `style_update`。

### 普通超链接

普通 Word 超链接使用行内 `<a>`，通过所属 carrier 的 `block_replace` 创建、更新或删除：

```xml
<p id="p1"><a href="https://example.com" tooltip="说明">网页</a></p>
<p id="p2"><a href="../files/report.docx" target-kind="file">文件</a></p>
<p id="p3"><a anchor="BookmarkName">文内位置</a></p>
```

- `href` 与 `anchor` 必须且只能提供一个；文件链接使用 `target-kind="file"`。
- `tooltip`、`history` 可保留或更新；当前 converter 仅保证 anchor/history 保存重开，tooltip 只保证当前页面会话。
- 删除普通链接时移除 `<a>` 外层并保留其文字与内部行内样式。链接不能嵌套，也不能覆盖 Field、批注或 inline object 的部分结构。
- 文内 `anchor` 必须对应当前文档唯一、完整且大小写精确匹配的 bookmark；否则停止写入。
- HYPERLINK Field 是独立、只读的 `<field type="hyperlink" editable="false">`，不得改写成 `<a>` 或编辑其定义。

字符样式（Word character style）没有 DocxXML 属性，普通 DocxXML 不输出字符样式引用，也不会把它继承的格式展开为上述直接格式属性。因此，XML 中缺少某个格式属性不代表文本的最终显示没有该格式。更新仍保留原有文本结构与所有已返回属性；未暴露的字符样式引用由宿主合并保留，跨越不同样式的替换区间只继承共有的可保留属性。不要自行写 `style-id` 或把继承样式重建成直接格式。需要设置或清除字符样式绑定时，查询 `style_apply`；通过 `block_styles` 精确范围读取取得 guard，不能用 XML 缺席属性推断绑定已清除。

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

`<img border-style>` 用的是另一套枚举，不要互相套用；图片线型查询 `xml:img`。

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

### 分栏符

已有分栏布局中的 inline 分栏符使用空元素 `<column-break/>`：

```xml
<p id="p1">第一栏<column-break id="break-1"/>第二栏</p>
```

- 必须位于 `<p>`、标题或 `<li>` 的文本流中；根级标签非法。
- 新建时省略 `id`；移动或删除时基于最新完整 carrier XML 保留或移除整个元素，不拆分该对象。
- 分栏符只表达在当前多栏布局中换到下一栏，不等同于 `<layout-break type="next-column">`；后者仍未开放。
- 更新使用所属 carrier 的 `block_replace`，不把分栏符 ID 当成独立 `--block-id`。

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

`SEQ`、`REF`、`PAGEREF`、`NOTEREF` 与普通模式 `DATE`/`TIME` 查询 `xml:field`；自动目录查询 `table_of_contents`。任意原始 instruction、未知 switch 或专项未开放的通用域不支持写入。`<page-number/>`、`<page-count/>` 和 `<symbol/>` 继续使用既有标签。

---

## 更新约束

段落对齐、间距、制表位、单 carrier 书签、单双删除线和受限 `<symbol/>` 均通过完整 `block_replace` 更新；仅专项明确支持的属性按“缺席保持”处理；其他属性仍须完整回放，不能把局部 patch 语义推广到整个 block。清除必须使用 `clear`、`<tabs/>` 或 `<span line-through="none">` 等显式写法。以最新完整 Fetch XML 为底稿，只修改目标内容或属性。