# docs +create（创建飞书文档/Lark Doc）

本文件负责新媒体写作任务的飞书文档/Lark Doc 创建与写入。进入本技能后，先创建 1 份在线文档并拿到文档入口，再按命中的创作类型 guide 与 samples 写入文本、图片和排版内容。

## 创建目标

1. 每次任务必须创建 1 份飞书文档/Lark Doc，内容与用户选择的小红书、公众号或短视频脚本类型一致。
2. 创建成功以命令返回 `document.url` 或 `document_id` 为准。
3. 创建成功后，所有创作内容写入同一份文档；每份文档同时包含文本内容和图片内容/图片落位。
4. 最终回复给出文档入口和必要说明。

## 命令入口

创建在线文档固定使用 `lark-cli docs +create`，参数包含 `--api-version v2`，默认 `--doc-format xml`；进入本技能后，直接用 `docs +create` 建文档。当前稳定命令体系：`docs +create` 创建文档，`docs +update` 追加或修改内容，`docs +fetch` 定位结构与校验结果，`docs +media-insert` 插入本地图片或剪贴板图片。

第一步固定执行（创建最小占位并拿入口；XML 创建时标题写入 `<title>`）：

```bash
lark-cli docs +create --api-version v2 --doc-format xml \
  --content '<title>平台｜主题｜内容类型</title><h1>待写入</h1><p>文档已创建。后续按命中的创作类型 guide 与排版 samples 写入文本内容、图片内容或图片落位、表格和核查信息。</p>'
```

从返回结果中取出 `document.url`（或 `document_id`）记为 `DOC`，后续全部写入与插图都对该 `DOC` 操作。

后续追加正文（每完成一个稳定模块即追加一次）：

```bash
lark-cli docs +update --api-version v2 --doc "$DOC" --command append \
  --doc-format xml --content '<h1>正文模块</h1><p>...</p>'
```

参数约束：`+create / +update / +fetch` 带 `--api-version v2`；XML 创建优先把文档标题作为 `<title>...</title>` 放入 `--content` 开头；`+media-insert` 直接执行对应命令。`--command` 使用 `str_replace | block_delete | block_insert_after | block_copy_insert_after | block_replace | block_move_after | overwrite | append`；追加内容用 `append`，定向填充章节或图片区优先用 `block_insert_after`。

命令参数需要确认时，读取当前 CLI 内置说明或帮助：

```bash
lark-cli skills read lark-doc references/lark-doc-create.md
lark-cli skills read lark-doc references/lark-doc-xml.md
lark-cli docs +create --api-version v2 --help
lark-cli docs +fetch --api-version v2 --help
lark-cli docs +update --api-version v2 --help
lark-cli docs +media-insert --help
```

## Fetch 定位规则

需要定位标题、章节、表格、图片落位或 block id 时，先用 `+fetch` 获取结构。`--scope` 使用固定枚举；按“封面方案”“视觉参考区”等标题定位时，用 `keyword` 或 `outline` 取得 block id 后再读 `section`。

1. **结构未知或要找标题 block**：先读目录或带 id 的全文结构。

```bash
lark-cli docs +fetch --api-version v2 --doc "$DOC" --scope outline --max-depth 3 --detail with-ids
lark-cli docs +fetch --api-version v2 --doc "$DOC" --detail with-ids
```

2. **只有标题/关键词文本**：用 `keyword` 定位候选块，再从返回结果中取 `id` 或 `top-block-id`。

```bash
lark-cli docs +fetch --api-version v2 --doc "$DOC" --scope keyword \
  --keyword "封面方案|笔记配图|视觉参考区|内容验真" --detail with-ids
```

3. **已拿到标题 block id 后读取整节**：`section` 必须搭配 `--start-block-id`。

```bash
lark-cli docs +fetch --api-version v2 --doc "$DOC" --scope section \
  --start-block-id "$HEADING_BLOCK_ID" --detail with-ids
```

4. **写操作后的 id 处理**：执行 `append`、`block_insert_after`、`block_replace`、`block_delete` 或 `overwrite` 后，后续若还要按 block 定位，重新 `+fetch --detail with-ids` 获取最新 block id。

5. **scope 参数恢复**：如果返回 `invalid value ... for --scope`，将 `--scope` 调整为 `full | outline | range | keyword | section` 之一；按标题定位时，用 `keyword` 或 `outline` 找到 block id，再执行 `section --start-block-id`。

## 更新命令规则

优先用 `append` 分段写入新模块；只有需要修改已写入内容时，才使用替换类命令。

1. **短文本替换**：使用 `str_replace --pattern --content`。

```bash
lark-cli docs +update --api-version v2 --doc "$DOC" --command str_replace \
  --pattern "待替换文本" --content "替换后的文本"
```

2. **整段、表格、图片区或跨 block 替换**：先获取 block id，再用 `block_replace` 或 `block_insert_after`。

```bash
lark-cli docs +fetch --api-version v2 --doc "$DOC" --detail with-ids
lark-cli docs +update --api-version v2 --doc "$DOC" --command block_replace \
  --block-id "$BLOCK_ID" --doc-format xml --content '<h1>模块标题</h1><p>更新后的内容</p>'
```

3. **插入到指定模块后**：先按“Fetch 定位规则”定位目标标题或模块的 `block_id`，再使用 `block_insert_after`。

```bash
lark-cli docs +update --api-version v2 --doc "$DOC" --command block_insert_after \
  --block-id "$BLOCK_ID" --doc-format xml --content '<h2>新增小节</h2><p>...</p>'
```

4. **占位内容处理**：最小占位只用于确认文档创建成功。开始写入正式内容后，可直接 `append` 正式模块；若需要删除或替换占位，先 `+fetch --detail with-ids` 定位占位 block，再 `block_delete` 或 `block_replace`。

## 创建顺序

1. 识别创作类型：确认本次是小红书、公众号还是短视频脚本。
2. 生成标题：用“平台 + 主题 + 内容类型”，如“小红书图文笔记｜通勤咖啡杯测评”“公众号文章｜AI 工具使用边界”“短视频分镜脚本｜新品发布 60 秒”；标题唯一，不与正文开头重复。
3. 先建最小占位：首次 `+create` 只保证真实文档已创建并可继续写入，平台分区和内容排版由命中的 guide 与 samples 接管。
4. 路由创作类型：按用户明确选择读取对应平台主干 guide，再由平台主干读取排版 samples，按其分区顺序和格式写入同一份文档。
5. 持续回写：平台主干每完成一个稳定模块就 `+update append` 或按需用更精确的更新命令写入文档。

## 骨架模板来源

本节标明各创作类型的文档内排版来源。创建文档时先用最小占位拿到入口；拿到 `DOC` 后，按命中类型的主干 guide 和排版 samples 写入。

### 小红书图文笔记

读取 `xhs.writing-guide.md`，并由其读取 `../xhs.samples/xhs-note-proposal.samples.output-format.md`。完整图文结构以该文件为准，核心顺序为：

1. 笔记标题。
2. 笔记配图。
3. 正文内容。
4. 直接复制版本。
5. 标题备选。
6. 话题标签备选。
7. 封面设计灵感。
8. 评论区互动引导。

配图数量、分栏、发布版正文纯净规则和局部需求压缩方式，均以小红书排版 sample 为准。

### 公众号文章

读取 `wechat.writing-guide.md`，并按需读取 `../wechat.samples/Layout-and-illustration-requirements.md`。完整文章结构以公众号主干和排版文件为准，核心顺序为：

1. 正文。
2. 封面图。
3. 备选标题。
4. 内容验真。

头图、正文、小标题、自然段、文中配图、重点句和结尾排版，按公众号排版文件自动匹配文章类型与风格。

### 短视频分镜脚本

读取 `short-video.writing-guide.md`，并由其读取 `../short-video.samples/output-format.md`。完整脚本结构以该文件为准，核心顺序为：

1. 项目概览。
2. 创意策略。
3. 完整标准 7 列分镜表。
4. 封面方案区。
5. 视觉参考区（关键分镜图）。
6. 拍摄执行包。
7. 剪辑提示。
8. 平台适配。
9. 合规与风险提醒。

分镜表字段、视觉参考区、封面方案、拍摄执行包和写入前检查，均以短视频排版 sample 为准。

## XML 内容规则

1. 默认 XML。
2. XML 用 `<title> <h1> <h2> <p>` 等标签承载结构；正文文字中的尖括号按 XML 规则转义（如 `&lt;`、`&gt;`），需展示代码或特殊符号时使用 Markdown 模式或代码块。
3. 资源标签（如 `<img>`）连同其 token/属性原样保留，以便图片和素材继续渲染。
4. 长文档先建最小占位，再分多次 `+update append` 写入，控制单次 `--content` 长度。

## 结构原则

- 文档只设 1 个主标题，正文开头不重复标题。
- 信息层级用标题、正文、表格、清单、引用/提示块承载；只有确需对比、流程、拆解或执行清单时才用结构化块。
- 平台内排版按对应平台 guide 与排版 samples 执行，各平台保留差异化排版。
- 需要图片、封面、视觉参考或素材占位时，先在文档建立明确位置，再由对应平台流程补充。
- 文档结构服务当前创作类型，同一模块只承载命中的平台内容。

## 搜图与生图写入流程

图片、封面、视觉参考图、分镜图进入文档对应位置，与文本内容一起构成完整文档。

1. 按命中类型 guide 写入时建立图片区、封面方案区或视觉参考区，写清用途和对应模块。
2. 搜图或生图成功后按平台排版原位写入：
   - 可访问的网络图片：先定位目标图片区、封面方案区或视觉参考区的 block id，再用 `block_insert_after` 写入 `<img href="https://..."/>`（仅支持 HTTP/HTTPS）。
   - 本地图片或剪贴板图片：先在目标位置写入唯一落位文本，再用 `+media-insert --selection-with-ellipsis` 插入到该落位附近。
3. 图片工具、搜图或生图暂不可用时，在原位写入“待生成 + 图片用途 + 生成/搜索提示词”，保持文档完整可交付。
4. 落位规则：小红书配图进“笔记配图”分栏区；公众号封面图或配图进正文、封面图或封面方案区；短视频封面图进封面方案区，关键分镜图进视觉参考区对应镜号。
5. 图片按对应模块原位回填；最终文档中的图片区、封面方案区或视觉参考区保持完整。

图片插入命令（`+media-insert` 直接执行对应命令；定向插入使用 `--selection-with-ellipsis`）：

```bash
lark-cli docs +update --api-version v2 --doc "$DOC" --command block_insert_after \
  --block-id "$TARGET_BLOCK_ID" --doc-format xml \
  --content '<p>图片落位：封面图｜请在此处插入</p>'

lark-cli docs +media-insert --doc "$DOC" --file "./image.png" \
  --selection-with-ellipsis "图片落位：封面图...请在此处插入" --align center --caption "封面图"

lark-cli docs +media-insert --doc "$DOC" --from-clipboard \
  --selection-with-ellipsis "图片落位：封面图...请在此处插入" --align center --caption "封面图"
```

网络图片写入目标位置：

```bash
lark-cli docs +update --api-version v2 --doc "$DOC" --command block_insert_after \
  --block-id "$TARGET_BLOCK_ID" --doc-format xml \
  --content '<img href="https://example.com/image.png"/>'
```

## 创建恢复流程

按顺序恢复，保持飞书文档/Lark Doc 交付通道：

1. `--content` 过长 → 缩短为“标题 + 最小占位”重试，正文后续分段 `append`。
2. 解析/格式提示（如 5000000）→ 检查正文尖括号并按 XML 转义，或改用 Markdown 模式后重试。
3. 标题参数提示 → 把 `<title>标题</title>` 放到 `--content` 最前面重试。
4. 标题重复 → 调整标题使其唯一后重试。
5. 权限或登录态异常 → 先用 `lark-cli docs +create --api-version v2 --help` 确认命令存在，再处理登录、身份或权限；需要 bot 身份时可改用 `--as bot`，但仍必须确认最终文档入口可访问。
6. 命令继续恢复 → 确认 `+create/+update/+fetch` 带 `--api-version v2`，`+media-insert` 使用自身参数；必要时执行 `lark-cli docs --api-version v2 --help` 查看当前可用子命令。
7. 文档入口仍需恢复 → 暂停后续创作路由，说明具体卡点和下一步恢复方式。

## 交付前验证

最终回复前确认：

1. 已拿到 `document.url` 或 `document_id` 且可继续写入。
2. 命中的创作类型主干已把内容写入同一份文档。
3. 对应平台核心排版区块已出现：小红书图文分区、公众号正文与验真区、短视频 7 列分镜表。
4. 文本与图片均已原位体现：成功图片、图片占位或生成/搜索提示词至少一种存在。
5. 需要核对写入结果时用 `lark-cli docs +fetch --api-version v2 --doc "$DOC"` 检查结构；发现缺块、错位或图片未落位先修复再交付。

## 最终回复

- 成功：`已完成：<文档标题>。文档：<链接>。包含：<一句话列出主要模块>。`
- 受限：说明具体卡点、已完成内容和可继续处理的下一步。
