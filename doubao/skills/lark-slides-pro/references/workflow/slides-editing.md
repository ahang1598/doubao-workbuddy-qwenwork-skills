# 编辑已有幻灯片

用户已经有一份内容、要在它基础上改时走这里。输入形态很多——飞书 Slides 链接/token、PPTX 文件、附带的文档或图片素材，或者只有一句话要求——但**执行顺序只有一条**。

想拿这份东西当**模板**、照着它的版式做一份新 deck，不走本文，走 [`template-editing.md`](template-editing.md)。

## 执行顺序

```text
第 1 步 理解现状        归一到一份在线 Slides → 读附件 → 回读这份 deck → 复核路由
第 2 步 定位要改哪里     产出 slide_id + block_id，以及每处要改成什么
第 3 步 备齐素材        照第 2 步的缺口去找、去加工（按需）
第 4 步 选操作并改       选命令 → 写 XML → 写入前 lint → 写入
第 5 步 回读校验并交付   必须用 NotifyHuman 交付最终幻灯片链接
```

**素材一定排在定位之后。** 缺哪张图、缺哪个口径的数据，是第 2 步的产出而不是它的前提——"把市场份额那页的数据换成 2025 的"，得先看过那页现在是什么图表、什么指标、几个系列，才知道要搜什么；没理解现状就去搜索生图，多半白做。

所有输入都从第 1 步进，区别只在第 1 步里多做什么：

| 用户给的 | 第 1 步里多做什么 |
|----------|-------------------|
| 飞书 Slides 链接 +「改某处」 | 无，直接回读 |
| PPTX +「改一下」 | 先导入成在线 Slides，之后只动这一份 |
| 链接 + 文档附件（「把这份材料的内容加进去」） | 完整解析附件，它往往直接决定要动哪几页 |
| 链接 + 图片（「把这张图放进去」） | 记下这张图和它的原图比例，加工上传留到第 3 步 |

## 第 1 步 · 理解现状

这一步要同时摸清两件事：**用户手上有什么材料**，以及**这份 deck 现在长什么样**。两者都清楚了才谈得上改哪里。

### 1.1 归一到一份在线 Slides

后续所有步骤都只认一个 `xml_presentation_id`，先把输入收敛成它。

**PPTX 文件**：导入成在线 Slides，导入结果就是之后编辑和交付的对象，不再回头动本地文件。

```bash
lark-cli drive +import --file "<deck.pptx>" --type slides --json
```

可加 `--name` / `--folder-token`。返回未就绪时执行响应里的 `next_command`，或跑 `drive +task_result --scenario import --ticket <TICKET>`。

**飞书 Slides 链接/token**：路径里的 token 直接就是 `xml_presentation_id`，不用转换。

**`/wiki/` 链接**：不能直接当 presentation ID 用，先解析真实 `obj_token`，见 SKILL.md「四、核心概念」。

拿到 ID 和链接后，**用 NotifyHuman 发开工通知**。

### 1.2 读附件（用户给了材料时）

做法与新建流程完全一致，细节见 SKILL.md `Step 3 · 收集素材`。

- 附件是本次任务**优先级最高**的事实来源，高于联网搜索和你的先验知识。
- 只跑 `paragraphs` / `pdftotext` 会丢掉图表：docx 必须再跑 `doc.tables` + `doc.inline_shapes` + `unzip word/media/`，pdf 必须再跑 `fitz.get_images` + `fitz.find_tables` + `page.get_pixmap`。
- 附件里提取的图片和表格**禁止裁剪**，只能缩放，`width:height` 必须对齐原图比例。
- 用户直接给了图片时，这里只需记下它和它的原图比例，去底色和上传留到第 3 步。

没读完附件就不要进第 2 步——附件内容往往直接决定了要动的范围。

### 1.3 回读这份 deck

**必须现在从服务端实时读**，不要用上一轮或历史会话存到本地的 XML——用户可能在此期间手动改过，旧文件里的 `slide_id` / `block_id`、以及上一轮记下的 `revision_id` 可能都已失效，据此改写会覆盖用户改动或报 3350001 / 3350002。

读法按范围选，别一上来就把整份 XML 塞进上下文。

**已经知道改哪一页**（用户提供了具体页面）：直接单页读，最省。返回里带这一页的 `block_id` 和 `revision_id`。

```bash
PID="xml_presentation_id"; SID="slide_id"

lark-cli slides xml_presentation.slide get \
  --params "{\"xml_presentation_id\":\"$PID\",\"slide_id\":\"$SID\"}"
```

**还不知道改哪一页，或改动会牵扯多页**：用 [`+xml-get`](../cli/lark-slides-xml-presentations-get.md) 回读全文，先看摘要再按需取页。

```bash
# 1. 回读全文到本地（--output 必填）
PID="xml_presentation_id"
mkdir -p .lark-slides
lark-cli slides +xml-get --presentation "$PID" --output .lark-slides/current.xml --json

# 2. 先看摘要：页数、页序、每页 slide_id、元素统计和正文预览
#    摘要模式可加 --output 落盘，不占上下文；summary.warnings 必看
python3 scripts/xml_inspect.py --input .lark-slides/current.xml

# 3. 再按需取目标页的完整 raw XML（可一次传多个 slide_id）
python3 scripts/xml_inspect.py --input .lark-slides/current.xml --slide-id "<sid-1>" "<sid-2>"

# 4. 要把某页落成文件（后面拼块跑 lint 时会用到）：raw 模式输出的是 JSON，
#    XML 在 .slides[].raw_xml 字段里，用 jq 取出来；raw 模式不接受 --output
SID="<上一步摘要里选定的 slide_id>"
python3 scripts/xml_inspect.py --input .lark-slides/current.xml --slide-id "$SID" \
  | jq -r '.slides[0].raw_xml' > ".lark-slides/page-$SID.xml"
```

回读出来的 XML 文件里**没有 `revision_id`**：它只在 CLI 响应中（`+xml-get --json` 的返回，或单页读的 `data.revision_id`），所以 `xml_inspect` 摘要里的 `presentation.revision_id` 对这类文件恒为 `null`。第 4 步「选操作并改」要加乐观锁的话，从 `+xml-get` 的 JSON 响应里取，或改走单页读。

摘要的 `summary.warnings` 要当回事，两类直接影响后面怎么改：

- **`<undefined>` 元素**（多见于 PPTX 导入的 deck，服务端用它占位视频/音频等不支持的类型）：**它不能写回**，带着它提交会返回 3350001。含 `<undefined>` 的页不要走整页重建，改用 `+replace-slide` 块级替换绕开那个块；确实必须重建整页时，先告知用户这页的视频/音频会丢。
- **重复 id**：`block_replace` 按 `block_id` 定位，撞车的若正好是目标块就无法唯一命中，这页改走整页重建。撞车的是 `slide_id` 时整页重建也不通——`+replace-pages` 同样按 `slide_id` 定位，`xml_inspect --slide-id` 会直接报无法唯一定位、连这页 XML 都取不出来，只能先告知用户。

不管走哪条，解析 XML 都必须用 XML 解析器，命名空间从根元素实际读取，不要硬编码，否则匹配不到元素。

版式和视觉效果光看 XML 判断不了时，用 [`+screenshot`](../cli/lark-slides-screenshot.md) 截目标页看真实渲染（怎么读截图见 [`validation-visual.md`](validation-visual.md)）。

### 1.4 复核路由：这真的是"在原稿上改"吗

进本文时的路由只能靠用户措辞判断，看过 deck 之后信息才够。出现下面任一情况，说明它其实是**模板任务**——就此打住，转 [`template-editing.md`](template-editing.md) 从头走，不要继续往第 2 步走：

- 现有页基本是占位内容（示例文案、样例数据、"标题占位"这类），和用户要放的内容没有对应关系。
- 用户要的是"照这个版式做我的一套内容"，而不是修订现在这套内容。
- 目标页数远多于现有页数，需要大量复制版式页来承载新内容。

判断标准是**产出物**：交回一份改过的原稿走本文，产出一份内容全新、只沿用版式的 deck 走 template-editing。反过来，如果你是从 template-editing 转过来、发现只是改几处文字或换张图，就从本文第 2 步接着做。

## 第 2 步 · 定位要改哪里

产出两样东西：一组明确的 **`slide_id` + `block_id`**，和**每处要改成什么**。两样都有了才算定位完成，缺一样都不要往下走。

- **用户直接指定了位置**（"第 3 页的标题"）：仍要在回读结果里核对一遍——页码只能当展示信息，实际下手必须按 `slide_id`；用户说的页码可能和当前页序对不上。
- **用户只给了目标**（"把市场份额那页的数据换成 2025 的"）：用摘要里的 `text_preview` 找到相关页，再取该页 raw XML 确认具体是哪个块，以及它现在的形态——是 `<chart>` 还是 `<table>`，几个系列、什么指标口径。这些决定了第 3 步要去找什么。
- `block_id` 是回读 XML 里每个块的 3 位 short id（如 `<shape id="bUn" ...>`）；配套的 `revision_id` 不在 XML 里，走单页读时从响应的 `data.revision_id` 取。
- 改动会波及邻居时（挪坐标、加元素、文字变长），把同页相关块一并列进来，别只盯着目标块。

顺带把**素材缺口**列出来：哪几处要新图、哪几处要新数据、哪些能直接从附件里取。这份清单就是第 3 步的输入。

## 第 3 步 · 备齐素材

只做第 2 步列出来的缺口，没有缺口就跳过。做法对齐 SKILL.md。

- **找**（SKILL.md `Step 3`）：缺数据先联网搜、不得编造；真实实体（人物、产品、logo、地标）用搜图工具；插画和示意图用生图工具。改数据时要沿用原页的指标口径和单位，不要换一套算法导致前后页对不上。
- **加工与上传**（SKILL.md `Step 6 · 图片处理`）：顺序是取到本地 → 去底色 → 上传，一步都不能省。**禁止 http(s) 外链**，渲染端不代理外链图，写进去通常不显示；带底色的图用 PIL 的 `floodfill` 抠掉纯色底，黑白灰底必抠、抠完效果差就回退用原图；最后 `+media-upload` 拿 `file_token`。
- `<img src>` 只能填 `file_token`。

下载幻灯片中的图片 `file_token` 使用 `lark-cli api GET "/open-apis/drive/v1/medias/<file_token>/download" --output "<file>"`。

## 第 4 步 · 选操作并改

### 选操作

| 需求 | 用什么 | 理由 |
|------|--------|------|
| 换某个块的整体内容（改标题、换图、挪坐标、改字号） | [`+replace-slide`](../cli/lark-slides-replace-slide.md) 的 `block_replace` | 精准替换单块，`slide_id` 和页序不变 |
| 只加 1~N 个元素、不动现有布局 | `+replace-slide` 的 `block_insert` | 新增不覆盖，可选 `insert_before_block_id` 定位 |
| 一次动多个块（如换标题 + 加图） | 单次 `--parts` 里拼多条，`block_replace` / `block_insert` 混用 | 整批原子事务，任一失败整批不生效 |
| **删除某个元素** | [`+replace-pages`](../cli/lark-slides-replace-pages.md) 整页重建 | 块级只有 `block_replace` / `block_insert`，**没有删除块的动作**，删元素只能重写整页 |
| **跨页统一改某个属性**（整份换字体、换配色等全局改写） | [`+replace-pages`](../cli/lark-slides-replace-pages.md) 整页重建 | 没有字段级 patch，逐块 `block_replace` 代价高；把受影响的页整页重建更省事 |
| 多页版式重建、整页坐标重排 | [`+replace-pages`](../cli/lark-slides-replace-pages.md) | 原 presentation 内批量重建，不生成新链接 |
| 追加新页 | [`xml_presentation.slide create`](../cli/lark-slides-xml-presentation-slide-create.md)，插到某页前用 `before_slide_id` | `before_slide_id` **只能放进 `--data`**，写进 `--params` 会被静默忽略、新页跑到末尾 |
| **删除整页** | [`xml_presentation.slide delete`](../cli/lark-slides-xml-presentation-slide-delete.md) | **不可逆**，删前先确认这页确实不要了；一份 deck 至少得留一页 |

以上都是在**原 presentation 上原地更新**，不要用 `+create` 新建一份覆盖——那会产生新链接，交付的就不是用户手上那份了。

> **没有字段级 patch，也没有删除块 / `str_replace` 动作**：即便只改一个 `topLeftX`，也要把整块的新 XML 写出来做 `block_replace`；要删元素或跨页统一改属性，只能走 `+replace-pages` 整页重建。`+replace-pages` 会刷新被替换页的 `slide_id`（原链接和页序不变）。

### 写 XML 的规矩

动手前**必读** [`xml-schema-quick-ref.md`](../xml/xml-schema-quick-ref.md)。其余和新建流程一致（SKILL.md `Step 7`）：元素不要自己编 `id`；`&` `<` `>` 必须转义；**全篇禁用 emoji**，语义图标一律用 IconPark `<icon>`；新增整页要补 `<note>` 讲稿。整页重建（`+replace-pages` 或 delete + create）还要把原页 `<note>` 一并带进新 XML，否则讲稿会丢，而且 lint 和回读都不会提醒。

**改前先 lint**：块片段不能直接喂 lint，它只认 `<presentation>` / `<slide>` 根，裸 `<shape>` 会被拒。把改好的块拼回第 1 步读到的那一页 `<slide>` 里，对拼出来的整页跑 `python3 scripts/xml_lint.py --input <整页文件>`，`error_count=0` 才能写入——这样才查得出它和周边既有元素的重叠。

**但设计决策和新建不同：不要另选设计系统。** 新增或改写的元素一律跟随这份 deck 已有的配色、字体、字号层级、留白和对齐轴，从第 1 步回读的 XML 里读出现有取值再复用。

### 改

```bash
SID="slide_id"

lark-cli slides +replace-slide \
  --presentation "$PID" --slide-id "$SID" \
  --parts '[{"action":"block_replace","block_id":"bUn","replacement":"<shape type=\"text\" topLeftX=\"80\" topLeftY=\"80\" width=\"800\" height=\"120\"><content textType=\"title\"><p>新标题</p></content></shape>"}]'
```

- `block_replace` 的 `replacement` 根 `id`、以及 `<shape>` 缺失的 `<content/>`，都由 CLI 自动补，手写 XML 不用自己加。参数和 parts 字段详见 [`+replace-slide`](../cli/lark-slides-replace-slide.md)。
- **写前加锁（可选）**：并发或多步编辑时，把第 1 步**从 CLI 响应里**取到的 `revision_id`（回读的 XML 文件里没有这个值）用 `--revision-id` 传给写操作做乐观锁；不确定就用默认 `-1`（基于最新版）。传超过当前版本的号会返回 3350002。
- 写失败或结果不明确时，不要假设那一步没有副作用，先回读确认真实状态再重试，错误码见 [`error-handling.md`](error-handling.md)。

**给已有页加图**：先读现有元素坐标挑空白区，空间不够就在同一批 `--parts` 里先移动或缩小现有块再插图。**图片可以裁剪或缩放大小来适配 PPT 的排版布局，不要溢出画布**；**附件中提取的图片/表格不允许做裁剪**，但可以缩放大小来适配你选择的 PPT 的排版布局；`<img>` 的 `width:height` 对齐原图比例就不会裁剪，只会缩放大小；对不上会自动裁剪，且默认从中心裁掉多余部分，可用 `<crop>` 的 `anchor` 指定保留哪一侧。**同一张图片不要在多页重复使用**，补充素材或重新排版，Logo、统一装饰除外。

```bash
# $TOKEN 来自第 3 步的 +media-upload
TOKEN=$(lark-cli slides +media-upload \
  --file ./pic.png --presentation "$PID" --jq '.data.file_token')

lark-cli slides +replace-slide \
  --presentation "$PID" --slide-id "$SID" \
  --parts "$(jq -n --arg t "$TOKEN" \
    '[{action:"block_insert",insertion:("<img src=\""+$t+"\" topLeftX=\"500\" topLeftY=\"100\" width=\"200\" height=\"150\"/>")}]')"
```

**整页重建**：`+replace-pages` 不吃 `--parts`，要的是 `pages.json`——每项一个 `slide_id` 加这一页完整的新 `<slide>`。这里的 content 本身就是整页，直接对它跑 lint，不用像块级替换那样先拼回原页。实跑前先 `--dry-run` 看替换计划，`--continue-on-error` 等参数见 [`+replace-pages`](../cli/lark-slides-replace-pages.md)。

**重建前先确认这页没有 `<undefined>`**（第 1 步摘要的 warnings 里会列出来）。它只能被导出、不能被写入，原样提交会 3350001，删掉它则意味着丢掉用户的视频/音频——两条路都得先跟用户说明，或者退回块级替换。

```bash
# page-01.xml 是这一页改好的完整 <slide>，已 lint 通过
jq -n --arg sid "$SID" --rawfile c page-01.xml '[{slide_id:$sid,content:$c}]' > pages.json

lark-cli slides +replace-pages --presentation "$PID" --pages @pages.json --dry-run
lark-cli slides +replace-pages --presentation "$PID" --pages @pages.json
```

**加页与删页**：`before_slide_id` 要和 `slide` 同级放进 `--data`（省掉它就是追加到末尾）。

```bash
# new-page.xml 是新页完整的 <slide>，含 <note> 讲稿
lark-cli slides xml_presentation.slide create \
  --params "{\"xml_presentation_id\":\"$PID\"}" \
  --data "$(jq -n --rawfile c new-page.xml --arg before "$SID" \
    '{slide:{content:$c},before_slide_id:$before}')"

lark-cli slides xml_presentation.slide delete \
  --params "{\"xml_presentation_id\":\"$PID\",\"slide_id\":\"$SID\"}"
```

## 第 5 步 · 回读校验并交付

改完必须回读，完整清单见 [`validation-xml.md`](validation-xml.md)。

1. `+xml-get` 重新回读全文（不能复用第 1 步的文件，它已经过期了）。
2. 对回读全文重跑 `xml_lint.py`，`error_count` 必须为 0 新增（之前就有的可以不处理）。改动波及的邻居元素、以及服务端对提交 XML 的规整，只有这一次查得出。
3. 逐页核对：目标元素确实变成了预期内容，页数和页序没被意外改动，周边结构没被破坏。
4. 改动较大的页用 `slides +screenshot --presentation <xml_presentation_id> --slide-id <slide_id> --output-dir <CWD 内相对路径>` 核对真实渲染（见 [`validation-visual.md`](validation-visual.md)）。
5. **用 NotifyHuman 交付最终幻灯片链接**，回复里附上简短验证记录。编辑任务同样必须交付链接。

## 相关文档

- [lark-slides-replace-slide.md](../cli/lark-slides-replace-slide.md) — `+replace-slide` 命令、parts 字段、合法根元素、报错（编辑主命令，细节都在这）
- [lark-slides-replace-pages.md](../cli/lark-slides-replace-pages.md) — 多页整页重建
- [lark-slides-xml-presentation-slide-get.md](../cli/lark-slides-xml-presentation-slide-get.md) — 单页读取
- [lark-slides-xml-presentation-slide-create.md](../cli/lark-slides-xml-presentation-slide-create.md) — 追加/插入新页（`before_slide_id` 定位）
- [lark-slides-xml-presentation-slide-delete.md](../cli/lark-slides-xml-presentation-slide-delete.md) — 删除整页（不可逆）
- [lark-slides-xml-presentations-get.md](../cli/lark-slides-xml-presentations-get.md) — `+xml-get` 回读全文到本地文件
- [lark-slides-media-upload.md](../cli/lark-slides-media-upload.md) — 上传图片拿 `file_token`
- [lark-slides-screenshot.md](../cli/lark-slides-screenshot.md) — `+screenshot` 页面截图
- [xml-schema-quick-ref.md](../xml/xml-schema-quick-ref.md) — XML 元素与属性速查
- [validation-xml.md](validation-xml.md) — 写入前/写入后两道校验关卡
- [template-editing.md](template-editing.md) — 拿模板做一份新 deck（不是在原稿上改）
