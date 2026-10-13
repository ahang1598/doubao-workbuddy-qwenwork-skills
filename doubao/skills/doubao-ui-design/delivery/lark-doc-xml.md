> **包内闭合子集。** 本文件包含本 Skill 默认发布链实际使用的 XML / html5-block 语法，
> 不依赖另一个 Skill。若用户另行要求白板、OKR 或复杂增量编辑等默认流程之外的飞书能力，
> 再使用宿主提供的飞书工具说明；不得让这些可选能力阻断 UI 方案发布。
>
> **执行边界**：本文件只解释底层标签与 CLI 语法。UI 设计任务不得复制下列裸
> `docs +create/+update` 命令；创建和更新都必须走 `python3 scripts/ui.py ship`
> —— 它会做 preflight、插封面、并把发出去的东西读回来比字节。
> 手跑裸命令的那三次，结果都是"发布报成功、封面没了"。

基于 HTML 子集的 XML 格式描述飞书文档内容。

# 一、标准 HTML 标签
p, h1-h9, ul, ol, li, table, thead, tbody, tr, th, td, blockquote, pre, code, hr, img, b, em, u, del, a, br, span 语义不变

# 二、扩展标签速查表
## 块级标签
|标签|说明|关键属性|
|-|-|-|
| `<title>` | 文档标题（每篇唯一）| `align` |
| `<checkbox>` | 待办项| `done="true"\|"false"` |

## 容器标签
|标签|说明|关键属性|
|-|-|-|
| `<callout>` | 高亮框，子块仅支持文本、标题、列表、待办、引用 | `emoji`(默认 bulb), `background-color`, `border-color`, `text-color` |
| `<grid>` + `<column>` | 分栏布局，各列 width-ratio 之和为 1 | `width-ratio` |
| `<whiteboard>` | 嵌入画板 | `type`: `blank` \| `mermaid` \| `plantuml` \| `svg` |
| `<pre>` | （代码块，内含 `code`）| `lang`, `caption` |
| `<figure>` | 视图容器 | `view-type` |
| `<bookmark>` | 书签链接 | `<bookmark name="标题" href="https://..."></bookmark>`，必传 name 和 href |

## 行内组件
| 标签 | 说明 | 关键属性 |
|-|-|-|
| `<cite type="user">` | @人 | `<cite type="user" user-id="userID"></cite>` |
| `<cite type="doc">` | @文档 | `<cite type="doc" doc-id="docx_token"></cite>` |
| `<latex>` | 行内公式 | `<latex>E = mc^2</latex>` |
| `<img>` | 图片（可独立成块或内联） | `<img width="800" height="600" caption="说明" name="图.png" href="http 或 https"/>` |
| `<source>` | 文件附件（可独立成块或内联） | `<source name="报告.pdf"/>` |
| `<a type="url-preview">` | 预览卡片 | `<a type="url-preview" href="...">标题</a>` |
| `<button>` | 操作按钮 | `background-color`、`src`，必须包含 `action=OpenLink\|DuplicatePage\|FollowPage` |
| `<time>` | 提醒 | 必包含 `expire-time`、`notify-time`（毫秒时间戳）、`should-notify=true\|false` |

## 文本块通用属性
- `align` — `"left"`|`"center"`|`"right"`（适用于 p / h1-h9 / li / checkbox）
- 有序列表项用 `seq="auto"` 自动编号

# 三、资源块

文档中可嵌入外部资源块（属于容器标签的特殊形式），需要额外语法创建：

- `<img>` — `<img href="https://..."/>` 上传网络图片
- `<whiteboard>` — 简单图可直接插入 `<whiteboard type="svg">完整自包含 SVG</whiteboard>`，或用本地文件简写 `<whiteboard type="svg" path="@diagram.svg"></whiteboard>`；复杂白板不属于默认 UI 方案发布链。
- `<sheet>` — `<sheet type="blank"></sheet>` 空白；`<sheet sheet-id="SID" token="TOKEN"></sheet>` 复制已有
- `<task>` — `<task task-id="GUID"></task>`，必传 task-id（任务 guid）
- `<chat_card>` — `<chat_card chat-id="CHAT_ID"></chat_card>`，必传 chat-id
- `<sub-page-list>` — `<sub-page-list></sub-page-list>` 子页面列表块；仅 wiki 文档可插入
- `<html5-block>` — 在飞书文档「HTML 块」iframe 里加载的单文件 HTML；发现内容可用 HTML 渲染时，直接生成单文件 HTML 并使用该块。
  **单块上限 500KB**（服务端报错 `isv data size too large, max=500`）；超限要拆块或降低内联图片尺寸。
  iframe 有 CSP：外链 CDN 脚本会被拦掉且不报错，JS 库必须内联。
- bitable、base_ref、synced_reference、synced_source — 不可创建，仅支持移动
- `<okr>` — 创建时仅支持 root-only `<okr cycle-id="..."/>` 挂载已有 OKR；不属于默认 UI 方案发布链

## html

1. 写入 HTML 内容块时，把 HTML 存为本地 `.html` 文件，XML 写 `<html5-block path="@widget.html"></html5-block>`；已有 `data-ref` 时配合 `--reference-map @reference-map.json`。读取时 `<html5-block data-ref="html5_1"></html5-block>` 只是占位，必须从 `document.reference_map["html5-block"]["html5_1"].data` 读取 HTML；若 entry 是 `path`，读取对应 `@doc-fetch-resources/...html` 文件。
2. 格式如下：
```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="use-iframe" content="true">
  <meta name="html-box-height-mode" content="auto">
  <meta name="description" content="内容摘要，会导出为 html5-block 的 alt 属性，帮助模型理解该 HTML 块的用途">
  <title></title>
</head>
<body>
  ...
</body>
</html>
```

# 四、块级复制与移动

## 移动（block_move_after）
支持**所有**块类型（块级标签、容器标签、行内组件、资源块），使用 `docs +update --command block_move_after --block-id "<锚点>" --src-block-ids "id1,id2"`。

## 复制（block_copy_insert_after）
- **基础标签**（块级标签、容器标签、行内组件）：均支持复制
- **资源块**：仅 img、source、whiteboard、sheet、chat_card、sub-page-list 支持复制；task、bitable、base_ref、synced_reference、synced_source、okr 不支持复制

使用 `docs +update --command block_copy_insert_after --block-id "<锚点>" --src-block-ids "id1,id2"`。

> 默认 UI 方案不直接执行块级复制或移动；所有创建与回读仍走包内受控发布入口。

# 五、补充规则

## 富文本样式嵌套顺序
- 行内样式标签必须按以下固定顺序嵌套（外 → 内），关闭顺序严格反转：`<a> → <b> → <em> → <del> → <u> → <code> → <span> → 文本内容`

## 列表分组
- 连续同类型列表项自动合并为一个 `<ul>` 或 `<ol>`
- 嵌套子列表放在 `<li>` 内部
- 新增列表项必须包在 `<ul>` 或 `<ol>` 内：
   ```xml
   <ul>
     <li>第一项</li>
     <li>第二项</li>
   </ul>
   ```

## 代码块
- 代码块必须写成 `<pre lang="xxx" caption="可选说明"><code>代码内容</code></pre>`。
- 不要将代码文本直接放在 `<pre>` 下；应放在内层 `<code>` 中。


## 用户名写入规则

- 当从 IM 消息、日历、审批、任务等来源获取到用户的 `open_id` 时，写入文档**必须**使用 `<cite type="user" user-id="open_id">` 标签，而非纯文本名字。这样文档中会渲染为可点击的 @人。
- 典型场景：IM 消息的 `sender`、`mentions`、reactions 的 `operator`、卡片消息中引用的用户、系统消息中的用户名、合并转发中的用户名。
- 当只有纯文本名字而没有 `open_id` 时（如系统消息、合并转发内容），先通过 `lark-cli contact +search-user --query "名字" --as user` 反查 `open_id`，再写入 cite 标签。

## 表格扩展
标准 HTML table 结构不变，扩展点：
- `<colgroup>` / `<col>` 定义列宽，紧跟 `<table>` 之后：`<col span="2" width="100"/>`
- `<th>` / `<td>` 增加 `background-color` 和 `vertical-align`（top | middle | bottom）
- 有表头时第一行在 `<thead>` 用 `<th>`，其余在 `<tbody>` 用 `<td>`
- 合并单元格仅起始格输出 `colspan` / `rowspan`，被合并的格不出现

# 六、美化系统
- 颜色优先使用命名色，也可写 `rgb(r,g,b)` / `rgba(r,g,b,a)`。**基础色（7 色）**：red, orange, yellow, green, blue, purple, gray
  | 属性 | 支持的命名色 |                                                                                                                                                                                                        
  |-|-|
  | 文字颜色 `<span text-color>` | 基础色 |
  | 高亮框字色 `<callout text-color>` | 基础色 |
  | 高亮框边框 `<callout border-color>` | 基础色 |                                                                                                                                                                                 
  | 文字背景 `<span background-color>` | 基础色 + `light-{色}` + `medium-gray` |                                                                                                                                                   
  | 高亮框填充 `<callout background-color>` | `gray` + `light-{色}` + `medium-{色}` |                                                                                                                                              
  | 单元格背景 `<th/td background-color>` | 同文字背景 |                                                                                                                                                                           
  | 按钮背景 `<button background-color>` | 同文字背景 |
- 常用 emoji： 💡(默认)✅❌📝❓❗👍❤️📌🏁⭐

# 七、**重要规则**
## 转义规则：标签本身 **禁止转义**，只有标签内部的文本内容才需要转义

**错误** ❌：`&lt;p&gt;内容&lt;/p&gt;`（把标签也转义了）
**正确** ✅：`<p>A &amp; B 的对比：1 &lt; 2</p>`（标签保持原样，文本中的 `&` 和 `<` 才转义）

转义字符表：
- `<` → `&lt;`
- `>` → `&gt;`
- `&` → `&amp;`
- `\n`（换行符） → `<br/>`


# 八、完整示例

```xml
<title>文档标题</title>

<h1>一级标题</h1>

<p><b>加粗文本</b>，<span text-color="green">绿色文本</span></p>

<callout emoji="💡" background-color="light-yellow" border-color="yellow">
  <p>高亮框内容，子块仅支持文本/标题/列表/待办/引用</p>
</callout>

<checkbox done="true">已完成事项</checkbox>
<checkbox done="false">未完成事项</checkbox>

<grid>
  <column width-ratio="0.5">
    <p>左栏</p>
  </column>
  <column width-ratio="0.5">
    <p>右栏</p>
  </column>
</grid>

<table>
  <colgroup><col span="2" width="120"/></colgroup>
  <thead><tr><th background-color="light-gray">表头</th><th background-color="light-gray">表头</th></tr></thead>
  <tbody><tr><td>单元格</td><td>单元格</td></tr></tbody>
</table>

<p><cite type="doc" doc-id="DOC_TOKEN"></cite> <cite type="user" user-id="USER_ID"></cite></p>

<ol><li seq="auto">第一项</li><li seq="auto">第二项</li></ol>

<p><a type="url-preview" href="https://example.com">链接标题</a></p>

<p><latex>E = mc^2</latex></p>

<pre lang="go" caption="示例"><code>fmt.Println("hello")</code></pre>

<hr/>

<source name="文件名.pdf"/>
<img src="IMG_TOKEN" width="800" height="400" caption="说明" name="图.png"/>
<img href="https://example.com/photo.png"/>

<button action="OpenLink" src="https://example.com">按钮文字</button>

<time expire-time="1775916000000" notify-time="1775912400000" should-notify="false">时间戳毫秒</time>

<cite type="citation"><a href="https://example.com">引文标题</a></cite>
<bookmark name="书签标题" href="https://example.com"></bookmark>

<task task-id="TASK_GUID"></task>
<chat_card chat-id="CHAT_ID"></chat_card>
<sub-page-list></sub-page-list>
```
