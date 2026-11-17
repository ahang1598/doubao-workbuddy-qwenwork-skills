---
keyword: xml:p
---

**功能**：段落结构、段落属性、分页、制表位、书签和合法 children

# 本地 Word XML：文本、段落与列表

用于段落、标题、富文本、公式、列表、制表位、书签和受限 SYMBOL 域。

## 按需读取

**公共必读**：段落正文、完整属性表及更新约束；涉及制表位或书签时，完整读取对应子节。段落正文读至首个子标题，子节读至下一同级或更高级标题。

标题结构查询 `xml:h1`；行内文字、字符格式、超链接、公式或符号查询 `xml:span`；列表查询 `xml:ol`。必须保留的特殊结构也须读取对应规则，Field/Note/Drawing 按实际结构加载专项；不加载无关字符枚举，不通过删格式或对象减少读取。

公共结构、寻址、颜色、单位和转义查询 `xml:common`，不查询无关能力。

---

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
| `spacing-before-lines` / `spacing-after-lines` | 非负无单位十进制行数；量化为 1/100 行，`0` 可显式取消继承值，`clear` 只清该行单位槽 |
| `spacing-before-auto` / `spacing-after-auto` | `true`、`false` 或 `clear`；缺席保持，`clear` 删除 direct 值 |
| `contextual-spacing` | `true`、`false` 或 `clear`；控制同样式相邻段落是否忽略段前/段后间距 |
| `line-indent` | 非负数值加 `ch`、`px` 或 `pt`，例如 `2ch`、`18pt`；负值会被丢弃 |
| `right-indent` | 物理右缩进；值域同 `line-indent` |
| `start-indent` / `end-indent` | Word 逻辑起点/终点缩进；非负 `ch`、`px` 或 `pt`，`clear` 删除对应逻辑槽 |
| `first-line-indent` | 同上；与 `hanging-indent` 互斥，同写时按 `hanging-indent` 生效并返回 `ATTR_MUTUALLY_EXCLUSIVE` 警告，不是失败 |
| `hanging-indent` | 同上；与 `first-line-indent` 互斥，同写时它胜出 |
| `line-height` | 倍率裸数字，如 `1.15`；或 `exact 12pt`、`at-least 12pt`，后两种只接受 `pt` |
| `shading-fill`（背景色） / `shading-pattern`（图案类型） / `shading-foreground-color`（图案颜色）| 段落底纹；颜色使用统一文法，`none` 清对应槽，pattern 使用字符底纹同一闭集 |
| `border-top/right/bottom/left/between` | 段落单边边框 token：`none`，或 `style [width] [color]`；缺席保留，单边更新不覆盖其他边 |
| `page-break-before` | `true` / `false`，段前分页 |
| `keep-next` | `true` / `false`，与下段同页 |
| `keep-lines` | `true` / `false`，段中不分页 |
| `widow-control` | `true` / `false`，孤行控制 |

除 `type` 外，这些属性也可按 fetch 返回结构用于标题或表格单元格中的 `<p>`。不要用空格模拟缩进或居中。

`line-indent/right-indent` 表达物理左右缩进，`start-indent/end-indent` 表达 Word 逻辑方向；不要按当前 LTR/RTL 把逻辑值物化成物理值。逻辑与物理槽可以并存，修改时使用 Fetch 已返回的 canonical 属性并保留未触及槽位。设置 absolute 段距会清同侧 lines 并关闭 auto；设置 lines 会保留同侧 absolute fallback 并关闭 auto。

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

---

## 更新约束

段落对齐、间距、制表位、单 carrier 书签、单双删除线和受限 `<symbol/>` 均通过完整 `block_replace` 更新；仅专项明确支持的属性按“缺席保持”处理；其他属性仍须完整回放，不能把局部 patch 语义推广到整个 block。清除必须使用 `clear`、`<tabs/>` 或 `<span line-through="none">` 等显式写法。以最新完整 Fetch XML 为底稿，只修改目标内容或属性。