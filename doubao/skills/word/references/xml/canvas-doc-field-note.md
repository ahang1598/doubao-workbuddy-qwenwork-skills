# 本地 Word XML：域、题注、脚注与尾注

用于 `SEQ` / `REF` / `PAGEREF` / `NOTEREF` 域、独立题注、普通脚注与尾注。公共 XML、寻址和更新规则先读 [`canvas-doc-xml.md`](canvas-doc-xml.md) 与 [`../cli/canvas-doc-update.md`](../cli/canvas-doc-update.md)。

> 使用前须完整读取本页；未见末行「全文完」时，调整 offset 继续读取至该标记。

使用既有 `block_replace`、`block_insert_after`、`append` 与 layout 更新命令，不另设专用请求。

- **修改前**：必须用 `+local-fetch --detail full` 取得实际可写标签和 ID。
- **新建前**：Field/题注读取 carrier 或正文锚点，按新建语法省略 ID 和 result；不要求已有同类对象。
- **能力不足**：Fetch 仅返回只读投影时向入口返回 `local_unverifiable`；Update 结构化返回不支持时，由 recovery 返回 `local_unsupported_runtime`。不得在本页直接切换路由、伪造 ID 或直调私有 API 绕过限制。

## 通用域 `<field>`

```xml
<p id="caption-1" role="caption">
  <span>Figure </span>
  <field id="seq-1" type="seq" key="Figure" format="decimal">1</field>
  <span> Architecture</span>
</p>

<p id="p-1">
  参见
  <field id="ref-1" type="ref" target="bookmark-1">第一章</field>
  第
  <field id="pageref-1" type="pageref" target="bookmark-1" relative="true">3</field>
  页。
</p>
```

| 属性 | 适用类型 | 取值与规则 |
|---|---|---|
| `id` | 全部 | 同一 story 内稳定的 Field identity；修改已有域必须沿用 Fetch 值，新建时省略 |
| `type` | 全部 | `seq`、`ref`、`pageref`、`noteref` |
| `key` | `seq` | 必填的非空 sequence identifier |
| `target` | `ref` / `pageref` / `noteref` | 必填的非空 bookmark name |
| `format` | `seq` / `noteref` | 可选编号格式，见下方闭集 |
| `restart` | `seq` | 非负整数；与 `repeat-current="true"` 互斥 |
| `repeat-current` | `seq` | boolean |
| `relative` | `pageref` | boolean |
| `locked` | 全部 | boolean |
| `editable` | 已有域 | Fetch 可能输出 `false` 的只读断言；不得改为 `true` 或通过删除来提升能力 |

`format` 只使用以下值：

`decimal`、`upper-roman`、`lower-roman`、`upper-letter`、`lower-letter`、`number-in-dash`、`decimal-full-width`、`chinese-counting`、`chinese-counting-thousand`、`chinese-legal-simplified`、`ideograph-traditional`、`ideograph-zodiac`。

- 子内容是 cached result 的只读 rich-text 投影。修改已有域时省略子内容表示保留；提交不同结果返回 `FIELD_RESULT_READONLY`。
- 未知 switch 或其他只读 Field 会由 Fetch 输出 `editable="false"`；该属性是 encode-only 断言，请求不得改为 `true`，也不能通过省略它把 Field 提升为可写。
- 新建域必须无 `id`、无子内容。CLI 无法根据当前文档计算初值时整次失败，不留下半成品。
- 定义变化时由宿主负责刷新结果，不在 XML 中写 `dirty`。
- 含未知 switch、非法嵌套、不完整 S/P/E 或 owner-specific 约束的域只读保真或拒绝更新。
- TOC-owned `PAGEREF` 必须继续使用 [`../cli/canvas-doc-update-domain.md`](../cli/canvas-doc-update-domain.md) 的 `table_of_contents_update`，不能用普通 `<field>` 绕过。
- `<page-number/>`、`<page-count/>` 和 `<symbol/>` 仍分别使用既有标签，不改写成 `<field>`。

## 独立题注

题注仍是普通 `<p>`，不新增 `<caption>` 标签：

```xml
<!-- 修改已有题注 -->
<p id="caption-1" role="caption">
  <span>Figure </span>
  <field id="seq-1" type="seq" key="Figure" format="decimal">1</field>
  <span> Architecture</span>
</p>

<!-- 新建独立题注 -->
<p role="caption">
  <span>Figure </span>
  <field type="seq" key="Figure" format="decimal"/>
  <span> Runtime architecture</span>
</p>
```

- 已有 `<p id role="caption">` 的 `role` 是只读语义断言；省略 `role` 表示继承当前角色，不可把普通段落改成已有题注。
- 新建 `<p role="caption">` 只能位于正文，且必须恰好包含一个无 `id`、无 result 的 `SEQ` 域。域前必须有非空 label 文本；去除 label 首尾空白并把其中每个空白字符替换为 `_` 后，必须与 `key` 完全一致。例如 `Figure ` 对应 `key="Figure"`，`图 ` 对应 `key="图"`，`Table A ` 对应 `key="Table_A"`；不能只改可见 label 而保留不匹配的 sequence key。
- 普通无 `id` `<p>` 即使包含 `SEQ` 也不会自动升级为题注。
- 创建时 Caption style、段落、SEQ、初始 result 和 managed mark 在同一事务中完成；任一条件不满足即零提交。
- 当前不支持 inline/隐藏 label 题注、对象上方题注、全局 Caption 设置，也不把题注持久绑定到图片、表格、图表或 Shape。

## 脚注与尾注

```xml
<fragment mode="range" requested-start="p-1" requested-end="p-3">
  <p id="p-1">正文<note-ref id="note-1" kind="footnote"/></p>
  <p id="p-3">后续正文</p>
  <notes>
    <note id="note-1" kind="footnote">
      <p id="note-p-1">脚注正文</p>
    </note>
  </notes>
</fragment>
```

- `<note-ref id>` 与 `<note id>` 使用同一个 note owner identity；`kind` 只取 `footnote|endnote`。
- `<notes>` 是可随正文片段读写的 detached collection，不进入正文 `rootIds`，也不是独立命令目标；一个片段最多出现一次，只能位于正文 roots 之后。
- `full`、`section`、`range`、`page` 只附带当前所选 roots 中 `<note-ref>` 可达的 Note，按正文首次引用顺序输出；范围外 Note 不进入本次 `<notes>`。
- `<note>` 只能位于 `<notes>` 内，正文复用普通 block 语法，但非空 body 必须以普通文本段落 `<p>` 开始，用于承载宿主生成的 canonical marker；不能直接以表格等非文本块开头。空 body 会自动补该段落。普通自动编号不输出 `mark`，当前不支持自定义 marker。
- Note body 内禁止再嵌套 `<note-ref>`，无论指向脚注还是尾注都会整次失败；不能借 detached `<notes>` graph 创建嵌套 Note。
- 创建或复制 Note 时，在同一次 `block_insert_after`、`block_replace` 或 `append` 中同时提交无 ID 的 `<note-ref>` 与尾部 `<notes><note>...</note></notes>`，由 runtime 原子创建新的 reference、owner、body 和 canonical marker；不得复用原 Note identity 或共享 body。
- **当前新增身份限制**：通过 `block_replace` 向已有 carrier 新增/复制 Note 时，仅当原有行内对象序列完全保留、所有新 Note 均位于该序列之后，或原 carrier 没有行内对象时使用 Local。向已有 Note 或其他行内对象之前/之间插入新 Note，前端可能按行内位置把新 Note 绑定到旧对象，导致别名或请求失败；该形状写前返回 `local_unverifiable` 交回入口评估 OOXML，不试写。不能为规避限制擅自移动注释位置、新增段落或删旧引用再插回。用户本就要求新增的 carrier 可按上述创建规则执行。
- 同一提交同时保留旧 Note 和创建新 Note 时，`<notes>` 中先完整列出保留的显式 ID owner，再按正文引用顺序列出无 ID 的新 owner；每种 kind 分别匹配。不能先放无 ID owner，否则它可能消费尚未定义的旧引用；所有既有 ID 和 body 保持原样，不能自行给新对象造 ID。
- 删除引用时从最新完整 carrier 中移除 `<note-ref>`；删除最后一个引用会清理 Note closure，仍有范围外引用时保留 closure。转换 kind 时则须在同一请求中让同 ID 的 reference 与 detached owner 使用相同的新 kind。
- 任何生命周期操作缺少所需 graph、出现重复 ID 或 kind 不一致时整次失败，不得只改 `<note-ref>` 制造不完整引用。
- separator / continuation separator 等 special story 只读保真。
- 修改 Note 正文必须使用该 story 内最新 Fetch 返回的 block ID；正文、其他 Note 或 Header/Footer 的同名 ID 不能跨 story 使用。

## Note 设置

`<layout>` 或 `<layout-break>` 内每种 `kind` 最多一个 `<note-settings>`：

```xml
<layout id="section-1">
  <note-settings kind="footnote" position="page-bottom"
    columns="2" number-format="decimal" start="1" restart="each-section"/>
  <note-settings kind="endnote" position="document-end"
    number-format="lower-roman" start="1" restart="continuous"/>
</layout>
```

| 属性 | 取值 |
|---|---|
| `kind` | `footnote`、`endnote`；不可清除 |
| `position` | footnote：`page-bottom\|beneath-text`；endnote：`document-end\|section-end`；`clear` 删除 direct 值 |
| `columns` | 正整数或 `clear`；仅 footnote |
| `number-format` | 上文编号格式闭集或 `clear` |
| `start` | 正整数或 `clear` |
| `restart` | footnote：`continuous\|each-section\|each-page`；endnote：`continuous\|each-section`；可写 `clear` |

属性缺席表示保留。`clear` 只清对应 direct path；没有整体 `remove="true"`，不得借此删除 separator 或其他未拥有的设置。

## 更新与验收

- Field、题注和 `<note-ref>` 都属于宿主文本 block；Field/题注按最新完整 carrier XML 执行 `block_replace`，非目标 `<note-ref>` 原样保留。Note 创建、复制或 kind 转换还须在同一请求中携带匹配的 detached `<notes>` graph；删除引用时按上文清理规则省略被删除的 owner。
- 新建题注使用正文锚点的 `block_insert_after` 或 `append`；不要先插普通段落再补角色。
- Note body、TextBox、Header/Footer 都是分离 story。只使用当前 Fetch 返回的内部 block ID；目标关系或内容已变化时重新 Fetch，不用旧 ID 重试。
- 写后回读同一 story，核对 Field identity、note reference-owner-body 一致性和非目标内容；定义未变时 cached result 保真，定义变化时验证宿主重算结果及依赖，不要求仍等于旧缓存；涉及分页的 `PAGEREF` 再核对目标页面。

## 明确不支持

- 修订、批注、日期时间域、任意原始 Field instruction 和未知 switch 写入；
- Field 超链接开关、TOC-owned `PAGEREF` 的通用 Field 写入；
- inline/隐藏 label 题注、对象上方题注、Caption 全局设置；
- 自定义 Note marker 与 separator/continuation separator story 写入。

===== 全文完 =====
