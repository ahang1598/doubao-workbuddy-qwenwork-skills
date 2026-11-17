---
keyword: xml:field
---

**功能**：域、DATE/TIME 与主 Story REF/NOTEREF 普通新建、题注和只读缓存

# 本地 Word XML：域、题注、脚注与尾注

用于 `SEQ` / `REF` / `PAGEREF` / `NOTEREF` / `DATE` / `TIME` 域、只读 HYPERLINK Field、独立题注、普通脚注与尾注。公共 XML、寻址和更新规则分别查询 `xml:common` 与 `local-update`。

Field 定义、题注、Note 使用既有 `block_replace`、`block_insert_after`、`append` 与 layout 更新命令；已有可安全求值 Field 的结果刷新使用 `field_update`。

- **修改前**：必须用 `+local-fetch --detail full` 取得实际可写标签和 ID。
- **新建前**：Field/题注读取 carrier 或正文锚点，按新建语法省略 ID 和 result；不要求已有同类对象。
- 仅返回只读投影时，该内容不能作为写入载荷。

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
| `type` | 全部 | `seq`、`ref`、`pageref`、`noteref`、`date`、`time` |
| `key` | `seq` | 必填的非空 sequence identifier |
| `target` | `ref` / `pageref` / `noteref` | 必填的非空 bookmark name |
| `format` | `seq` / `noteref` | 可选编号格式，见下方闭集 |
| `date-format` | `date` / `time` | 原生日期时间 picture，例如 `yyyy-MM-dd`、`HH:mm`；与编号 `format` 独立，见下文 |
| `restart` | `seq` | 非负整数；与 `repeat-current="true"` 互斥 |
| `repeat-current` | `seq` | boolean |
| `relative` | `pageref` | boolean |
| `locked` | 全部 | boolean |
| `editable` | 已有域 | Fetch 可能输出 `false` 的只读断言；不得改为 `true` 或通过删除来提升能力 |

`format` 只使用以下值：

`decimal`、`upper-roman`、`lower-roman`、`upper-letter`、`lower-letter`、`number-in-dash`、`decimal-full-width`、`chinese-counting`、`chinese-counting-thousand`、`chinese-legal-simplified`、`ideograph-traditional`、`ideograph-zodiac`。

- 子内容是 cached result 的只读 rich-text 投影。修改已有域定义时省略子内容表示保留；提交不同结果返回 `FIELD_RESULT_READONLY`。
- 未知 switch 或其他只读 Field 会由 Fetch 输出 `editable="false"`；该属性是 encode-only 断言，请求不得改为 `true`，也不能通过省略它把 Field 提升为可写。
- 新建域必须无 `id`、无子内容。CLI 无法根据当前文档计算初值时整次失败，不留下半成品。
- 定义变化时由宿主负责刷新结果，不在 XML 中写 `dirty`。
- 含未知 switch、非法嵌套、不完整 S/P/E 或 owner-specific 约束的域只读保真或拒绝更新。
- TOC-owned `PAGEREF` 必须继续使用 `table_of_contents`，不能用普通 `<field>` 绕过。
- 已有 Field 的结果刷新使用 `fields → field_update`；只处理 Fetch 明确标记 `updatable` 的 identity，不修改定义或缓存结果。
- HYPERLINK Field 保留独立 identity，以 `<field type="hyperlink" editable="false">` 只读投影；普通链接使用文本规范中的 `<a>`，两者不能互相转换。
- `<page-number/>`、`<page-count/>` 和 `<symbol/>` 仍分别使用既有标签，不改写成 `<field>`。

## 普通模式日期时间域

```xml
<p>日期：<field type="date" date-format="yyyy-MM-dd"/> 时间：<field type="time" date-format="HH:mm"/></p>
```

- 新建 DATE/TIME 仅普通模式，省略 `id` 与全部 cached result 子内容；它们是动态域，不能把当前日期或时间写成静态文本冒充域。
- `date-format` 对应宿主日期时间 picture，仅接受原生 formatter 支持的格式；不是数字格式 `format`。DATE/TIME 不带 `key`、`target` 或 positional args，不提交原始 instruction 或日期格式 switch。未支持的 picture 写前拒绝。
- 同次新建由宿主使用同一时间快照求初值并生成域结构；结果刷新仍查询 `field_update`，只刷新实际 `updatable` 的域，不手写缓存。
- 已有可写域基于最新完整 carrier 与实际 ID 保留/修改协议开放的定义属性，未知 switch、只读 projection、原始 instruction 或不完整域结构继续保真或拒绝。DATE/TIME 新建不开放修订，也不扩大任何 Field 结构修订支持；不把拒绝降为普通写入。

## 主 Story 普通交叉引用新建

```xml
<p>参见 <field type="ref" target="ExistingBookmark"/>；注释 <field type="noteref" target="ExistingNoteBookmark"/></p>
```

示例中的 target 只是占位名称，实际值必须来自当前文档查询，不按名称猜测。新建 REF/NOTEREF 仅主 Story、普通模式，省略 ID 和 cached result；不直接调用依赖真实选区的 UI 插入流程。

- 目标必须在请求前已经存在、名称合法、大小写精确匹配且唯一完整。REF 指向既有可求值书签；NOTEREF 指向可唯一解析到合法 Note reference/owner 的既有书签，不以 note ID 或显示编号替代 target。缺失、歧义、非法或无法求值的目标在写前拒绝。
- 写前读取 carrier、书签边界、目标内容/编号及 NOTEREF 的 owner graph；冻结既有目标，提交前由宿主复核目标与依赖漂移。目标在同一请求中新建、改写、删除或重编号时拒绝；不能在一个载荷里先造/改目标再引用。发生协同变化时重新 Fetch 和规划，不复用旧目标证据。
- 新域初值与域结构由宿主生成。子内容始终是只读缓存，不提交自编引用文字/编号；无法求值时整次失败，不留下半成品。
- 这项能力不开放 PAGEREF 新建或扩展 PAGEREF 的现有边界，不扩大域结构修订支持；TOC-owned PAGEREF 仍使用 `table_of_contents`。已有 REF/NOTEREF 定义变更仍以当前 Fetch 的 editable 能力和对应命令约束为准。

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

---

## 更新

- Field、题注和 `<note-ref>` 都属于宿主文本 block；Field/题注按最新完整 carrier XML 执行 `block_replace`，非目标 `<note-ref>` 原样保留。Note 创建、复制或 kind 转换还须在同一请求中携带匹配的 detached `<notes>` graph；删除引用时按上文清理规则省略被删除的 owner。
- 新建题注使用正文锚点的 `block_insert_after` 或 `append`；不要先插普通段落再补角色。
- Note body、TextBox、Header/Footer 都是分离 story。只使用当前 Fetch 返回的内部 block ID；目标关系或内容已变化时重新 Fetch，不用旧 ID 重试。

## 明确不支持

- 直接写入修订标记、任意原始 Field instruction 和未知 switch；日期时间域只按 `xml:field` 的普通模式能力执行，不支持修订新建；
- Field 超链接开关、TOC-owned `PAGEREF` 的通用 Field 写入；
- inline/隐藏 label 题注、对象上方题注、Caption 全局设置；
- 自定义 Note marker 与 separator/continuation separator story 写入。