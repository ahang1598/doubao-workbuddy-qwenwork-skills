# Word 引用与注释

涉及脚注、尾注、`[1]` 参考文献或编号交叉引用时读取本页。使用统一工具 `docx_citations.py`，由模型选择来源和正文锚点，工具维护 Word 原生结构。禁止以普通上标数字、页尾段落或格式不一致的手工括号模拟。

读取已有结构时先运行 `inspect`，核对原生引用、定义、书签和域，不要只提取正文文本。新建时先按下节选择结构，再按主工作流选定的创建方式生成正文和稳定锚点，使用统一工具写入；终稿按本页验收要求校验。

## 选择结构

先区分用户对呈现效果、使用行为和底层组件的要求，再选择结构；术语名称本身不等于指定 Word 组件。

- 新建文档在满足注释位置、编号样式、引用关联和更新行为的前提下选择实现。题材指南仅补充用户未指定的默认值。
- 用户或适用规范明确指定的组件，以及原稿已有的原生结构，优先保留；转换已有结构须有用户授权。
- 有实现能够满足要求时直接执行。只有实际约束无法同时满足时才澄清取舍，不因默认实现的局限而自行降低用户要求。

| 需求 | 原生结构 | 操作 |
|---|---|---|
| 当页随文注释，或需原生脚注/尾注行为、保留既有 note | note part + 正文引用 | `add / update / delete / configure` |
| 文末 `[1]`、`[2]` 参考文献 | 自动列表 `[%1]` + 书签 + REF 域 | `number / cite` |
| 同一文献多次引用 | 多个 REF 指向同一书签 | 重复 `cite` |
| 文献增删、重排后的显示编号 | 保留 REF，仅重算受支持的缓存 | `refresh` |

原生 note 的 `number_format` 不接受 `[%1]`，自定义标记不参与自动编号递增；工具尚未支持原生 note 的方括号样式。若原生组件是约束，应据此核对能否满足格式要求；不能将静态自定义标记当作可自动更新的编号。

## 统一调用与事务

下列命令以 skill 根目录为工作目录；其他目录执行时使用脚本、DOCX 和 spec 的绝对路径。  
$PYTHON_BIN 为所在系统上可执行的 `python` 指令，如mac linux使用 `python3`, windows使用`python`

```bash
$PYTHON_BIN scripts/docx_citations.py inspect INPUT.docx
$PYTHON_BIN scripts/docx_citations.py validate INPUT.docx
$PYTHON_BIN scripts/docx_citations.py apply TARGET.docx --spec operations.json --dry-run
$PYTHON_BIN scripts/docx_citations.py apply TARGET.docx --spec operations.json --in-place
```

`inspect` 返回 note 定义、正文引用、编号配置、复杂内容，以及 `cross_references` 的书签、域指令、缓存和应显示编号。`validate` 发现断开的引用、冲突或过期缓存时返回非零。只检查某类结构时可在这两个只读命令后加 `--scope notes` 或 `--scope references`；默认 `all`。专项检查不等于完整 OOXML 或版面验收。

所有写操作放在同一份 `{"version":1,"operations":[...]}` 中，可以混合 note 与文献引用操作。`apply` 按操作范围校验，全部操作成功后才原子发布；失败不写入目标。仅处理文献引用时不改写或强制套用旧 note 部件的兼容限制。

- 原稿先保留只读 baseline；始终操作当前工作流锁定的 `TARGET_DOCX`。
- 已生成正文或已复制出目标时使用 `--in-place`，保留本轮修改；不要再从旧 baseline 生成同名输出。
- 尚未创建目标时可用 `--out NEW.docx`。已有输出默认拒绝覆盖，只有明确需要覆盖时才使用 `--force`。
- `--dry-run` 执行完整操作与校验，不生成输出文件。

## 脚注与尾注

操作示例（ID 来自同一输入文件的最新 inspect；按任务选取操作，不直接套用示例 ID）：

```json
{
  "version": 1,
  "operations": [
    {"op": "add", "kind": "footnote", "anchor": {"text": "需要注释的原文", "position": "after"}, "paragraphs": ["第一段注释。", "第二段注释。"]},
    {"op": "update", "kind": "endnote", "id": 2, "paragraphs": ["更新后的尾注。"]},
    {"op": "delete", "kind": "footnote", "id": 3},
    {"op": "configure", "kind": "footnote", "scope": {"type": "document"}, "number_format": "decimal", "start": 1, "restart": "continuous", "position": "pageBottom"}
  ]
}
```

- `kind` 为 `footnote` / `endnote`；`paragraphs` 为非空文本数组。
- `add` 创建匹配的引用和定义，并补齐必要的部件、separator、样式、关系及 Content Type。首次创建且没有显式配置时，使用阿拉伯数字、起始 1、连续编号；脚注默认页底，尾注默认文末。已有配置不静默覆盖。
- `update` 保留内部 ID，只支持纯文本多段；图片、表格、公式、超链接等复杂内容会拒绝覆盖。`inspect` 只读报告复杂内容，显式 `delete` 可删除整条 note。
- `delete` 删除定义和全部同 ID 的直接 note 引用，不重排其他内部 ID。内部 ID 不等于页面上显示的序号。
- `configure.scope` 为 `{"type":"document"}` 或 `{"type":"section","index":1}`。文档级设置补到当前分节尚未配置的属性，保留已有分节 override。
- 常用 `number_format`：`decimal / upperRoman / lowerRoman / upperLetter / lowerLetter`；`start >= 1`；`restart`：`continuous / eachSect / eachPage`。
- 脚注 `position`：`pageBottom / beneathText / sectEnd / docEnd`；尾注：`sectEnd / docEnd`。

## 方括号参考文献与交叉引用

先写好正文和每条文献的独立段落，文献文本不带手工 `[1]` 前缀。为现有段落设置原生编号和书签，再插入引用：

```json
{
  "version": 1,
  "operations": [
    {"op": "number", "entries": [
      {"text": "第一条文献的唯一原文", "bookmark": "Ref_SourceA"},
      {"text": "第二条文献的唯一原文", "bookmark": "Ref_SourceB"}
    ]},
    {"op": "cite", "bookmark": "Ref_SourceA", "anchor": {"text": "正文中需要引用的原文"}, "superscript": true},
    {"op": "cite", "bookmark": "Ref_SourceA", "anchor": {"text": "另一处引用同一文献的原文"}, "superscript": true}
  ]
}
```

- 文末自动编号跟随每条文献首个正文文字的有效字号（含样式继承），不写死字号、不修改正文引用上标。先确定文献文字样式，再执行 `number`。
- `number` 新建独立自动列表；编号按文献段落的文档顺序计算，entries 数组顺序不改变正文。书签名唯一，字母或下划线起始，仅含 ASCII 字母、数字和下划线，最多 40 字符。
- 已有编号、书签或字段的文献段落不能再次 `number`。符合支持范围的既有文献，直接使用其真实书签名 `cite`，保留既有依赖。
- `cite` 生成完整的 `[1]` REF 域结果，不在域两侧拼括号；默认整体上标，`superscript:false` 使用普通基线。同一文献重复引用时复用书签，不复制文献条目。
- 文献文字字号在编号生成后发生变化时，可用 `{"op":"refresh","sync_number_size":true}` 同步已被引用条目的编号字号；默认 refresh 只更新域缓存。若列表层已有冲突的显式字号，工具拒绝覆盖，先处理该格式要求。
- `refresh`：`{"version":1,"operations":[{"op":"refresh"}]}`，根据当前列表顺序更新全部受支持 REF 的显示缓存，保留原生域与书签。
- 编辑文献时保留书签和列表绑定；删除被引用条目前先处理全部正文依赖。工具拒绝断开的引用，不静默删除或转为纯文本。
- 当前支持正文直接段落、显式单级 `decimal + [%1]` 列表、单段书签，以及 `REF bookmark \n \h` / `REF bookmark \r \h`。
- 不支持通过样式继承的列表、多级编号、嵌套/跨段 REF、富内容域结果、跨文档引用或 `[1–3]` / `[1,2]` 合并引用。其他 REF 指令只报告 warning，保持原样，不算验收通过。

## 锚点与验收

`add` 和 `cite` 共用精确正文锚点：`anchor.text` 必须是真实原文，`position` 为 `before / after`（默认 after），`occurrence` 为可选的 1-based 匹配序号。多处普通匹配必须消歧；字段显示结果（含跨段和嵌套字段）、超链接、修订、内容控件或复杂 run 内部拒绝写入。不得临时添加 marker 或退化为段末插入。

终稿包含引用与注释时重新运行 `inspect` 与 `validate`，核对引用、定义、书签、域缓存、编号配置及复杂内容警告。写入后核对计划内引用位置、内容及编号，确认计划外 note、正文、样式和关系保持。文献增删/重排后核对同一书签仍指向同一文献、重复引用编号一致；过期缓存先 refresh。

按当前创建/编辑工作流的渲染条件与预算检查整个 `[1]` 的格式、上下标、缩进、换行和分页。无本地渲染条件时披露视觉未验证。脚注/尾注结构检查不能代替显示编号及页面布局验证。

工具的 refresh 不是 Microsoft Word 实机更新域的证明。用户后续在 Word 中编辑文献后仍需“全选 → 更新域”或逐个更新相关域。LibreOffice 渲染验证与 Word/WPS 编号刷新、点击跳转、跨页行为分别报告；不能仅设置 dirty/updateFields 就声称已刷新。

原理参考：[Microsoft REF](https://learn.microsoft.com/en-us/openspecs/office_standards/ms-oi29500/7088a8ce-e784-49d4-94b8-cba6ef8fce78)、[自定义 note 标记](https://learn.microsoft.com/en-us/dotnet/api/documentformat.openxml.wordprocessing.footnoteendnotereferencetype.custommarkfollows)、[更新域](https://support.microsoft.com/en-us/word/update-fields)。
