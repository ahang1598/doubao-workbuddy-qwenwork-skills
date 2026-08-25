# 模板改写工作流

用于“用户提供 PPTX 或在线 Slides 作为模板，并要求据此制作新演示文稿”的任务。本工作流所称关键页包括封面、目录、导航、章节页、过渡页、总结/结论页和结束页。目标内容决定写什么，模板决定长什么样：关键页严格继承，内容页优先整页继承，结构不匹配时只重构主体内容区。

## 总览

严格按四步执行：

1. **取得目标文档**：导入 PPTX 或复制在线 Slides 或直接复用上一轮生成的需要修改模板的 Slides，后续始终编辑并交付这一份文档。
2. **理解模板并选择来源**：保存原始模板 XML 并查看全部页面，了解页面结构和视觉体系，识别关键页、内容布局、固定壳层和主体区域；只读取少量候选页 raw XML 来确认来源及相关 block。
3. **规划新文稿**：确定目标内容、每页类别、来源页、保留元素、主体区域、计划改动和写入方式；规划完成前不写入。
4. **分批制作和验收**：每批制作 2–4 页，对比修改前后 lint，写入并回读；全部验证后清理旧页并检查终稿。

始终遵守：

- 导入或复制得到的 Slides 是唯一目标文档；禁止另建空白演示文稿后从零制作。`+add-slide` 只能在该文档内创建页面。
- 新文稿的主题、章节数量、章节名称和顺序，以用户要求及用户提供的文字、文档、数据和图片等内容为准；模板中的示例文字和原有章节结构要相应替换，目录、章节页和导航必须保持一致。
- 模板原有背景、Logo、品牌标识、页眉页脚和装饰属于应继承的视觉资产，不属于“多余装饰”。
- 仅参考配色、字体或设计规律不算复用；复用必须保留来源页或组件的原始 XML。
- 制作优先级固定为：**同角色整页继承 > 模板壳层加主体区重构 > 已检查组件重组**。不得仅以复杂、效率或内容不同为由降级。
- 页面角色和视觉判断以截图为准，精确复用以 raw XML 为准；`template-index.json` 只能导航。
- 不得因来源 XML 触发 lint 就删除、替换或简化未计划修改的来源元素；增量 lint 规则见第四步。
- 制作阶段不删除来源页；全部目标页验证后再统一清理计划外页面。

## CWD 与脚本路径

始终停留在任务开始时的 CWD；所有产物写入 CWD 内的独立相对目录。第一条命令前初始化：

```bash
LARK_SLIDES_SKILL_DIR="<包含当前 SKILL.md 的绝对目录>"
WORK_DIR=".lark-slides/template/<deck-or-task-id>"
mkdir -p "$WORK_DIR/authoring" "$WORK_DIR/lint"
```

Skill 脚本始终通过 `$LARK_SLIDES_SKILL_DIR/scripts/...` 调用。

## 第一步：取得唯一目标文档

不得调用新建演示文稿命令绕开用户模板；后续读取、写入、截图、清理和交付都使用同一个 `xml_presentation_id`。

**PPTX 模板**：导入结果就是编辑和交付对象：

```bash
lark-cli drive +import --file "<template.pptx>" --type slides --json
```

可用 `--name "<title>"` 指定标题、`--folder-token <FOLDER_TOKEN>` 指定文件夹。返回未就绪时执行 `next_command`，或运行 `drive +task_result --scenario import --ticket <TICKET>`。

**在线 Slides 模板**：默认通过 `drive files copy` 复制后编辑；只有用户明确要求才直接修改原件。`/wiki/` 链接先解析真实 `obj_token`。

记录目标 URL、`xml_presentation_id`、`revision_id` 和模板来源，并按主 `SKILL.md` 发送开工通知。

## 第二步：理解模板并选择来源

### 1. 保存原始模板 XML 和页面索引

```bash
lark-cli slides +xml-get --presentation "<xml_presentation_id>" --output "$WORK_DIR/source.xml" --json
python3 "$LARK_SLIDES_SKILL_DIR/scripts/xml_inspect.py" --input "$WORK_DIR/source.xml" --output "$WORK_DIR/template-index.json"
```

`source.xml` 是不可覆盖的原始快照；后续在线回读另存为 `current.xml`。索引只用于定位页数、页序、`slide_id`、元素统计和文字预览；导入后不对整份模板运行 lint。

### 2. 截图并查看全部模板页

按 `slide_id` 分批截图全部页面，每批最多 10 页；多页时重复传入 `--slide-id`：

```bash
lark-cli slides +screenshot --presentation "<xml_presentation_id>" --slide-id "<slide_id_1>" --slide-id "<slide_id_2>" --output-dir "$WORK_DIR/source-screenshots"
```

实际查看全部页面；生成截图文件不算已查看。不要每轮只查看一张：优先在同一轮并行发起 4–6 个 Read 调用，每个调用传入一张截图的 `file_path`，逐张查看并记录判断。识别关键页、内容布局、固定壳层、主体区域、媒体槽位、网格和跨页节奏。

### 3. 按需读取 raw XML

根据截图选择候选页，每次读取 1–3 个 `slide_id`：

```bash
python3 "$LARK_SLIDES_SKILL_DIR/scripts/xml_inspect.py" --input "$WORK_DIR/source.xml" --slide-id "<slide_id_1>" "<slide_id_2>"
```

每类关键页和内容布局至少读取一个代表页；写入 page-plan 的来源必须已读。此处读取是为了选择来源、划分固定壳层与主体区域并确认 `block_id`；第四步再把同一来源直接提取到 authoring 文件，不必重新把 raw XML 展示给模型阅读。

结合截图与 XML 识别重要元素，不能只凭单一条件判断：

- **背景**：铺满或覆盖大部分画布、位于底层，并经常跨页重复的图片或形状。
- **Logo/品牌标识**：多页出现在相同角落，大小、外观和位置稳定的小型图片、SVG 或组合元素。
- **固定装饰**：多页在相同位置重复、通常位于主体区之外的图片、形状、线条或纹理。
- **标题区、导航和页脚**：同类页面中位置、样式和结构重复的文字与形状组合。截图确认视觉角色，raw XML 确认准确 block、坐标和层级顺序。

同时明确受众、目标页数、章节结构、叙事主线、每页核心结论、必须内容、禁用项和用户提供的内容。

## 第三步：规划新文稿

必须创建并重新读取 `$WORK_DIR/page-plan.md`：

**候选来源页表：**

| source_slide_id | 页面角色 | 固定壳层/可复用 block | 主体区与结构限制 |
|---|---|---|---|
| `<content_id>` | 内容页 | 背景、Logo、标题区、导航、页脚、装饰 / `<block_ids>` | 主体区 `<x,y,w,h>`；原版两栏 |

**目标页面表：**

| 目标页 | 页面类别/任务 | 来源 slide/block | 制作/写入方式 | 计划改动与必须保留 | authoring XML | 状态/最终 ID |
|---|---|---|---|---|---|---|
| 2 | 关键页：5 章目录 | `<agenda_id>` / 整页 | 整页派生 / `+update-slide` | 改标题；删第 6 组；五组重排；其余 block 保留 | `$WORK_DIR/authoring/slide-02.xml` | `planned` / `-` |
| 5 | 内容页：7 步流程 | `<content_id>` / 壳层 blocks | 壳层+主体重构 / `+add-slide` | 保留壳层；主体改为 7 步时间轴；旧正文和占位符残留=0 | `$WORK_DIR/authoring/slide-05.xml` | `planned` / `-` |

目录项、章节页和页内导航必须与 page-plan 的章节集合、名称和顺序一致。“计划改动”写清修改、删除、新增和必须保留的 block；没有写入计划的关键页来源 block 均为只读。用户明确要求保留的模板页也作为目标页记录；表外页面不进入终稿。

### 页面分类与制作路径

1. **关键页严格继承**：封面、目录、导航、章节/过渡、总结、结尾存在同角色来源时，只能从最新在线原页或完整 raw XML 开始。角色、模块数量、布局和容量完全匹配时做原页块级改写；需要增删或重排时做整页派生。来源中未列入计划修改或删除的元素全部保留，不得近似重画。
2. **内容页优先整页继承**：有适合承载目标内容的模板内容页时，从其完整 raw XML 派生并最小修改，不得为省事转入重构。
3. **内容页壳层加主体重构**：只有主体结构确实不匹配时使用；page-plan 必须写明具体原因，如“两栏无法承载 7 步时间轴”。仍从完整 raw XML 开始，原样保留计划列出的背景、Logo、标题区、导航、页眉页脚、固定装饰、字体、配色、裁切和对齐轴，只在明确主体区域内增删或重排。不得从空白 XML 开始。
4. **组件重组兜底**：模板没有可用同角色关键页或内容页壳层时，才从已检查来源复制完整组件 XML；没有可用组件时才继承设计参数。不得仅参考截图近似重画。

块级改写使用 `slides +replace-slide` 的 `block_replace` / `block_insert`；它不能替换整页或删除 block。整页覆盖已有页面用 `slides +update-slide`（`slide_id` 和页序不变），新增页面用 `slides +add-slide`（插入位置用 `--before-slide-id`）。

每个目标页只能有一个最终 ID：块级改写沿用原 `slide_id`；整页替换和创建必须将响应中的新 ID 写回 page-plan。实际写入命令必须与规划一致；确需改路径时，先更新并重新读取该行。

### 写入硬门槛

第一条写命令前必须满足：目标行数等于计划页数；每页已有类别、来源、具体选择理由、计划改动、保留元素、写入方式、authoring 路径和验收点；引用来源 raw XML 已读；所有状态为 `planned`。任一条件不满足，禁止写入。

## 第四步：分批制作、增量 lint 并验收

首次生成 XML 前完整读取 [`xml-schema-quick-ref.md`](../xml/xml-schema-quick-ref.md)、[`validation-xml.md`](validation-xml.md) 以及实际使用的写入命令文档。

每批选择 2–4 个相互独立的目标页：**准备本地页面 → 核对来源与模板残留 → 每个目标页的待写入完整 XML 完成 lint 对比 → 顺序写入并检查响应 → 批量回读 → 更新 page-plan。** 缺少任一目标页的 authoring、lint 或验收结论时不得写入；写入失败或结果不明确时立即停止该批并回读排障。

### 1. 准备本地页面

**原页块级改写**：写入前用 `+xml-get` 取得最新完整页面 XML，分别保存为来源页原始文件和待写入完整页面；先在待写入完整页面中应用计划修改并运行 lint，实际接口只提交 page-plan 中的 parts，未提交 block 原样继承。

**整页派生或内容页壳层重构**：直接从 `source.xml` 提取完整来源页，同时保存来源页原始文件和待写入完整页面：

```bash
python3 "$LARK_SLIDES_SKILL_DIR/scripts/xml_inspect.py" --input "$WORK_DIR/source.xml" --slide-id "<source_slide_id>" \
  | jq -r '.slides[0].raw_xml' | tee "$WORK_DIR/lint/slide-02-baseline.xml" > "$WORK_DIR/authoring/slide-02.xml"
```

提取必须先于编辑；之后直接 Edit authoring 文件，禁止从上下文重写完整 XML。多个目标页可复制同一份从 `source.xml` 提取后尚未编辑的来源页 XML 起步，但禁止复制另一目标页已经修改过的 authoring XML。提交完整新页前再按命令要求清除会重复的旧 ID。

**本地修改粒度**：首次派生 authoring XML 时，先汇总本页全部计划改动，再将相邻或同类的改动按每组 3–4 处集中处理；禁止为每个 block、文本框、段落或字段分别调用一次 Edit，也不要求一次修改完整页。lint 或回读发现少量独立问题时可逐项 Edit；多个同类问题仍按每组 3–4 处集中修复。

### 2. 来源完整性与模板残留

关键页逐项核对来源根级 block：每个 block 只能是“原样保留、计划修改、明确删除”。内容页壳层重构必须保留 page-plan 列出的全部壳层 block，只允许删除或重排计划中的主体 block。任何未计划消失、改型、改坐标/样式或被近似重画的来源元素都禁止写入。

新内容决定语义：核对来源中的可见文字、目录项、导航和占位符；无关旧文案、计划删除模块或“添加标题/标题”等占位内容仍存在时，记为模板残留并禁止写入。文字或图片替换后还要核对容器容量，避免溢出、异常换行、遮挡和裁切。

### 3. 增量 lint 门槛

同一来源页的原始 lint 结果可缓存共用，但每个目标页的待写入完整 XML 都必须在写入前单独 lint，不能用代表页代替。以下命令保存两份完整结果，同时把精简对比直接返回给模型，不需要再 Read 结果文件：

```bash
# xml_lint 发现问题时会退出 1，但仍会输出 JSON；test -s 用于确认结果文件已经生成且不为空
python3 "$LARK_SLIDES_SKILL_DIR/scripts/xml_lint.py" --input "$WORK_DIR/lint/slide-02-baseline.xml" > "$WORK_DIR/lint/slide-02-baseline.json" || test -s "$WORK_DIR/lint/slide-02-baseline.json"
python3 "$LARK_SLIDES_SKILL_DIR/scripts/xml_lint.py" --input "$WORK_DIR/authoring/slide-02.xml" > "$WORK_DIR/lint/slide-02-candidate.json" || test -s "$WORK_DIR/lint/slide-02-candidate.json"
jq -e -s '
  def brief: {file, summary,
    errors: [(.document.errors[]?, .slides[].errors[]?) | {code, path, element_ids, measurement}],
    warnings: [(.document.warnings[]?, .slides[].warnings[]?) | {code, path, element_ids, measurement}]};
  {baseline: (.[0] | brief), candidate: (.[1] | brief)}
' "$WORK_DIR/lint/slide-02-baseline.json" "$WORK_DIR/lint/slide-02-candidate.json"
```

- 新增、主动修改的 block 及其与来源元素交互产生的 error 必须为 0；API 写入成功不能豁免。
- 来源页原始结果中已存在、仅涉及完全未修改来源 block，且待写入页中 code、path/block 和 measurement 未变差的 issue，可标记 `inherited_source_issue`，不得为消除它修改来源元素。
- 常见来源问题包括 `<p defaultTabSize="72">` 的 `sxsd_unsupported_attr`、导入 SVG/embed 的 `duplicate_element_id`、截图正常的装饰叠放触发的 `bbox_overlap`；这些示例不是自动豁免白名单。
- 文字溢出、图片遮挡，以及壳层与新主体之间的新冲突都不是来源问题，必须修复。
- **非标准画布例外**：目标模板真实画布宽或高超过 960×540时，优先以真实宽高包装单页后 lint。若单页 lint 的 `slide_size` 仍回退为 960×540，且 `shape/img/table/chart_out_of_canvas` 指向的元素实际仍在目标模板真实画布内，可标记 `canvas_size_mismatch`；不得为清零而缩小模板壳层或整体比例。其他新增错误以及真正超出目标画布的问题不得豁免。

写入门槛是：新增或加重错误为 0、意外丢失来源元素为 0、模板残留为 0。含继承 issue 的页面还必须在写入后截图正常才能验证通过。

### 4. 写入、回读与状态

本地准备和 lint 可批量完成，在线写入仍按页顺序执行并保存响应。连续调用 `+add-slide` 时每次都必须检查 `.ok == true` 并取得新 ID，禁止无条件打印成功；任一失败立即停止并回读。`+update-slide` 逐页写入，同样不是跨页原子事务。

块级改写后立即单页回读；创建或整页替换可在本批响应全部成功后统一 `+xml-get`。核对内容、来源元素、壳层、位置、裁切、层级、页序和最新 ID，将状态更新为 `written`、`verified`；本批回读结果统一 lint。文字、图片、几何或层级变化后截图该页实际查看。

页序修正：回读发现页序错误时，应读取错位页的最新完整 XML，使用 `before_slide_id` 将其重新创建到下一张目标页之前；目标位置为末尾时省略该字段。新页写入并回读验证成功后才能删除旧页，同时将新 `slide_id` 更新到 page-plan。多张连续错位页应以同一张后继页为锚点，按最终顺序依次创建。


### 页面集合清理/删除模板页、无效页

全部目标页为 `verified` 后、终稿截图前，回读全文取得当前全部 ID；从 page-plan 取得终稿 ID 和页序，两者做差得到待删除页。`+delete-slide` 一次只能删除一页，可用 `for` 循环逐页删除，但任一失败必须立即停止并回读。删除后只有页数、ID 和页序与 page-plan 完全一致才进入终稿 review。

### 终稿全页视觉 review

按最新 ID 分批截图全部终稿页并实际查看；生成截图不等于完成 review。优先在同一轮并行发起 4–6 个 Read 调用，每个调用查看一张截图；复杂页和可疑页再单独查看。在 `$WORK_DIR/visual-review.md` 记录每页 `pass/fix`、发现和动作，检查溢出、异常换行、遮挡、裁切、对比度、对齐、层级顺序、模板识别度及目录—章节—导航一致性。

模型自己发现的任何“待删除、待修改、可优化、模板残留”都必须记为 `fix`，不能以时间或效率为由交付。修复后重新回读、lint、截图和记录。

交付前必须满足：最终 ID 及页序 = page-plan verified 集合及目标页序 = 截图集合 = visual-review 结论集合；所有新增/修改 error、计划外来源变化、模板残留和视觉 fix 均为 0。终稿 lint 必须读取 `.summary.error_count`、`.summary.warning_count` 和实际 issue；字段缺失或解析失败不得默认按 0。最终交付第一步取得并持续编辑的在线 Slides 链接，并说明实际页数和内容简介。
