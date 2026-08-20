# XML 校验

本文件覆盖**写入前后对 XML 的校验**这一必做环节：写入前校验你手里的单页 XML，写入后校验服务端回读的全文。目标是发现 XML 损坏、schema 不合法、空白页、内容截断、明显溢出和未验证输出。只能靠截图主观判断的视觉问题（对比度、图片裁切、间距、跨页风格等）见 [validation-visual.md](validation-visual.md)。

小型已有页编辑也要做对应范围的验证：至少读取被改页面或全文 XML，确认目标元素已更新且未破坏周边结构。

## 两道关卡

`xml_lint` 在流程里跑两次，输入不同、目的也不同，**两次都必做，谁也替代不了谁**：

| | 写入前（SKILL Step 7） | 写入后（SKILL Step 8） |
|---|---|---|
| 输入 | 你刚写好的**单页** `<slide>` 本地文件 | `+xml-get` 回读的**全文** `<presentation>` |
| 目的 | 拦住不合法或明显崩版的页，别让它写进去 | 确认服务端真正存下来的东西和你想的一样 |
| 过不了的后果 | 不许提交这一页 | 不许交付 |

### 写入前：单页静态校验

逐页闭环的一环——一页校验通过就写一页，不要攒完整份再统一校验。

1. 把这一页 XML 存成本地文件：单个 `<slide>` 元素，不用包 `<presentation>`，不用写 `<?xml ...?>` 声明。
2. 跑 `python3 scripts/xml_lint.py --input <这一页的文件>`，`error_count` 必须为 0。
3. 照 `hint` 改，改完重跑，干净了再提交这一页。这一步没有截图这个选项——页还没写进去，截不到；疑似误报的留到写入后再核。

改已有页时提交的是块片段（`<shape>` 之类），**lint 不收裸片段**，只认 `<presentation>` 或 `<slide>` 根，直接喂会报 `input must contain a <presentation> or <slide> root`。把新块拼回这一页回读到的 `<slide>` 里，对拼出来的整页跑——只有这样才查得出它和周边既有元素的重叠。

### 写入后：全文回读校验

1. 记录创建或编辑返回的 `xml_presentation_id`，以及已知的 `slide_id` / `revision_id`。`slide_id` 是页面唯一关联键；页码仅可作为展示信息。
2. 用 `slides +xml-get --output <CWD 内相对路径>` 回读全文 XML 到本地文件（必须使用 `--output`；必须先用 XML 解析器解析，命名空间从根元素实际读取，不要硬编码否则匹配不到元素），并以当前结果建立本次校验的 `slide_ids` 页清单。首次新建且页集合未变时，可复用创建响应；增删页、整页替换或重排后必须刷新清单。
3. 对回读文件再跑一次 `xml_lint`，`error_count` 必须为 0。**逐页都干净不等于全文干净**：服务端会规整你提交的 XML（丢弃它不认识的属性、补上默认值），落地结果和你写的可能不是一回事；而且跨页才查得出的问题（如 `id` 跨页撞车）只有这一次能发现。
4. 对照回读的 XML 逐页核对：实际页数、关键元素与主视觉、空白/破损页（具体检查点见下方各节，这些 `xml_lint` 都不管）。
5. 发现问题的页用 `+replace-slide` 或对应写入操作修复后，重新回读确认。创建过程部分失败时，先记录已创建的 `xml_presentation_id`，再回读确认哪些页已写入，不要假设失败的那一步没有副作用。
6. 个别你确信是有意设计（如刻意层叠、紧凑排布）而疑似 `xml_lint` 误报的，用截图核对真实渲染（可选，见 [validation-visual.md](validation-visual.md)）；截图不可用时，以静态检查结论为准。
7. 在最终回复中给出简短验证记录，说明做了哪些检查；只有确实截图核对过时才写"已做视觉确认"。

回读命令：

```bash
lark-cli slides +xml-get \
  --presentation "YOUR_ID" \
  --output .lark-slides/<deck-or-task-id>/readback.xml \
  --json
```

## XML 静态检查（xml-lint）

上面两次跑的是同一个脚本，行为也完全一致，只是喂的文件不同：单个 `<slide>` 和完整 `<presentation>` 都能直接吃。它会检查 well-formed、schema 合法性（含 SML 命名空间前缀、iconType 合法性、必填属性与子元素、属性取值的枚举/范围/格式约束）、元素 ID 重复、文本重叠、形状/图片/表格/图表遮挡文字、元素越界、文本溢出（纵向撑破高度与横向意外换行）、文字溢出背景容器、相邻卡片背景互叠、表格尺寸、icon 填充，以及布局密度（空白页、大容器/整页内容过稀疏）。`--input` 是必填参数，指向要检查的本地 XML 文件；不带 `--input` 直接运行会报错。路径相对技能根目录，若从别处运行请补全到 `scripts/xml_lint.py` 的实际位置。

```bash
python3 scripts/xml_lint.py --input <presentation.xml>
```

通过标准：

- `summary.error_count == 0`。任何 error 都必须先修复再交付。
- **schema 错误会让该页跳过几何检查**：某页存在 `sxsd_*` error 时，该页的 `element_count` 为 0，重叠/溢出/越界等几何检查全部不执行。所以看到 `sxsd_*` 必须先修 schema，再重跑一次 lint，否则几何问题会被藏住。
- 只有 `error` 计入 `error_count` 并阻断交付；`warning` 与 `info` 不阻断，但代表真实风险，应逐条核对后决定是否修复或收紧版式。
- lint 可能误报有意设计：绝大多数报告都是真实缺陷、应直接修复；只有当你确信某条是刻意设计（如为层次感让文字与形状/其它元素重叠、紧凑排布）时，才用截图核对真实渲染（见 [validation-visual.md](validation-visual.md)），确认无碍后保留并在验证记录说明——不要拿"设计如此"当默认借口跳过修复。
- 该工具不能替代页数核对、关键内容核对或真实视觉验收。

### 怎么读一条 issue

每条 issue 自带修法，**以 `hint` 和 `message` 为准动手改**；下面的表只用来快速认识 code 的含义和严重级，不重复 `hint` 的内容。

- `message` 说明发生了什么，通常带实测数值（如估算行宽 vs 可用宽度、各方向溢出多少 px）。
- `hint` 给出该条的具体修法。
- 定位元素看 `elements`，它给的是下面两种之一：元素自己写了 `id` 就给这个 `id`；没写 `id` 就给 XML 路径 `slide[1]/data/shape[2]`（数 `<data>` 下第 2 个 `<shape>`，同类标签各自从 1 开始数，此时 `related_objects[].xml_path` 是同一个值）。`related_objects[]` 还带每个几何元素的 `kind`/`type`/`bbox`，可以拿 bbox 反查是哪个元素。
- `measurement` 与 `rule.comparison` 给出判定阈值，用来判断距离通过还差多少。

### code 速查

| code | 含义 | 级别 |
|------|------|------|
| `xml_not_well_formed` | XML 语法错误，或文本/属性里的 `&` `<` `>` 未转义 | error |
| `sml_prefixed_tag` | SML 标签用了命名空间前缀（如 `sml:`） | error |
| `sxsd_unsupported_tag` / `sxsd_unsupported_attr` | 标签或属性不在 schema 中 | error |
| `sxsd_missing_required_attr` / `sxsd_missing_required_child` | 缺少必填属性或必填子元素（如 `<shape>` 少 `height`、`<img>` 少 `src`） | error |
| `sxsd_unexpected_child` / `sxsd_too_many_children` / `sxsd_invalid_child_order` | 子元素不被该父标签接受、超出允许数量，或顺序与 schema 的 sequence 不符 | error |
| `sxsd_invalid_enum` / `sxsd_invalid_scalar` / `sxsd_value_out_of_range` / `sxsd_pattern_mismatch` | 属性值不在枚举内、类型不对、超出取值范围，或不匹配格式（如颜色串） | error |
| `sxsd_invalid_namespace` / `sxsd_unexpected_root` / `sxsd_unsupported_declaration` | 命名空间不对、根元素不是 `<presentation>`/`<slide>`，或写了 `<?xml ...?>` 声明 | error |
| `sxsd_unsupported_pattern` | lint 读不懂 schema 里该属性的 XSD 正则，所以这个值**没有被校验过**（不代表值一定有错） | error·需人工确认 |
| `duplicate_element_id` | 同一个 `id` 被多个元素使用（同页内或跨页） | error |
| `iconpark_unsupported_icon_type` | 用了 IconPark 不支持的 `iconType` | error |
| `icon_missing_fill_color` / `icon_transparent_fill_color` | `<icon>` 没有设置不透明的 `fillColor` | error |
| `shape_out_of_canvas` / `img_out_of_canvas` / `table_out_of_canvas` / `chart_out_of_canvas` | 文本框、矩形容器、图片、表格或图表超出 960×540 画布（只对这五类判定越界） | error |
| `bbox_overlap` | 元素绘制区域重叠。覆盖五种情况：两段文字互压、填充形状盖住不属于它的文字、相邻卡片背景互叠、`<line>` 穿过字形、`autoFit="shape-auto-fit"` 文字长出原框压到下方元素 | error·误报高发 |
| `image_covers_text` | `<img>` 压住文本框的估算字形区域 | error·误报高发 |
| `table_covers_text` / `chart_covers_text` | 游离的文本框压在 `<table>` 网格或 `<chart>` 绘图区上，会与单元格文字、坐标轴标签、图例打架 | error·误报高发 |
| `text_may_overflow_shape` | 文本超出自身文本框，`overflow_axis` 区分 `height`（行数撑破高度）和 `width`（单行太宽，会意外换行或被 `wrap="false"` 裁切） | error（背景装饰巨字降 info） |
| `text_overflows_container` | 文本框越过了它所在的背景容器（卡片、色块、胶囊）边界，`overflow` 给出四个方向各溢出多少 px | error |
| `blank_slide` | 该页没有任何可见元素 | error |
| `sparse_container_content` / `sparse_slide_content` | 大容器（`rect`）内部或整页的可见内容覆盖率过低 | warning |
| `whiteboard_external_overlap` | `<whiteboard>` 越过自身边界压到相邻兄弟元素。自己写不出画板（schema 里没有这个元素），只有回读用户原稿时才可能遇到；回读不含画板内部的 SVG/Mermaid，最终以截图渲染为准 | warning |
| `table_resolved_size_mismatch` | `<table>` 声明的 width/height 与 `<col>`/`<tr>` 解析出的实际总尺寸不一致 | info |
| `image_may_cover_vertical_text` | 竖排文字疑似被 `<img>` 覆盖（竖排布局无法静态建模，需截图核对） | info |

`sxsd_*` 是 schema 校验，`hint` 只说哪里不合规、不给正确写法：改之前对照 [`slides_xml_schema_definition.xml`](../xml/slides_xml_schema_definition.xml) 里该标签的定义，issue 的 `expected` 有值时会直接列出该处允许的子元素或取值，`path`（如 `slide/data/shape/content/text`）只有标签名、不带序号，和上面带下标的 `xml_path` 不是一回事。

`sxsd_unsupported_pattern` 是里面唯一的例外：它说的是 lint 自己读不懂那条 XSD 正则，不是你的值有错，它的 `hint` 写给脚本维护者、照着改不动。对照 schema 里该类型的定义人工确认取值；确认无误就在验证记录里写明这一条是 lint 能力缺口后放行，不必为了把 `error_count` 压到 0 去改一个本来正确的值。

几条判定规则 `hint` 里没有、但会影响你怎么排版，值得先知道：

- **图片压字**：`image_covers_text` 不看 z 序，也不看中间是否隔着蒙版或色块。两种豁免：铺满整页（≥95% 画布）且排在文字之前的整页背景图；以及排在文字之前、且几乎完整包住该段字形盒的局部背景图。只盖住半截文字的半出血大图一律会报。
- **图表压字**：`chart_covers_text` 不分上下层，压上就报，但环形图（`<chartPlot type="pie">` 带 `innerRadius`）的中心空洞是豁免的——把大数字标题放进甜甜圈中心是允许的，压在圆环本身上则会报。
- **文字溢出容器**：`text_overflows_container` 按文本框（authored box）而不是字形盒判定，且零容差——只要文本框跨过容器边界就报。贴着容器边缘（0px 间隙）摆放的说明文字也算这个容器的内容。
- **越界只判五类**：`*_out_of_canvas` 只覆盖 `<img>`、`<table>`、`<chart>` 和 `type` 为 `rect`/`text` 的 `<shape>`。`<icon>`、`<line>` 超出画布 lint 不会报，得自己对坐标核一遍。底部留白也不在判定范围内，重要内容压过 `y=500` 要自己收。设计系统说的「出血 / full-bleed」是指贴齐画布边缘，不是用负坐标或超宽把图画到画布外——那样会报 `img_out_of_canvas`。
- **强制单行**：`wrap="false"` 不能解决框太窄的问题。文字放不下时它只会被裁切或溢出，lint 会按精确行宽报 `text_may_overflow_shape`（`overflow_axis: width`）。要单行就先把 `width` 加够，再配 `wrap="false"`。
- **元素 ID**：新写的元素不要自己编 `id`，留空即可；改回读 XML 时把服务端 ID 只留在原元素上，复制出来的新元素要删掉 `id`。

## 回读后核对：页数与完整性

下面这些 `xml_lint` 一条都不管，只能自己对着回读的 XML 看。空白页尤其别指望它：`blank_slide` 是故意宽松的，纯背景加一根装饰线的页它会放行。任何一条不满足，修复后再交付。

- 实际页数等于用户要求或大纲确定的页数，没有缺页、页序错误，也没有某页内容被 shell 截断。
- 每页都有 `<data>`，且 `<data>` 内至少有一个非背景主体元素——只有背景、装饰线或空 `<content/>` 的页算破损。封面、章节页、总结页可以文字很少，但不能只剩空背景。
- 关键文本确实出现在回读的 XML 里。
- `<img src>` 已经是 `file_token`，不是残留的 `@./path`，也不是 http(s) 外链（外链渲染端不代理，在幻灯片里通常不显示）。
- 没有一堆形状坐标完全相同、把主体内容压死。这种 lint 也不报：它的形状重叠规则要求至少一方承载文字，并且会跳过完全包含的情况，几个坐标相同的空面板刚好两条都躲过。
- 渐变背景没有回退成空白或白底，导致文字不可读。

## 回读后核对：关键元素

按用户要求和大纲逐页核对：

- 标题或主结论存在，并能对应这一页要传达的核心信息。
- 这一页规划的主要结构（如对比、时间线、架构、流程、大数字等）已生成；技术解释、对比、流程、架构这几类页必须有匹配的结构元素，例如分组框、连线、时间轴、表格或图形化区域。
- 主视觉是页面中最醒目或最大的信息区域之一。
- 文本量符合规划，高密度页用分栏、表格或分组承载，没有用单个长 bullet 框堆砌替代版式。
- 有真实素材的已放入正确区域；没有真实素材的，已用兜底方案（生图近似图、原生 `<chart>`、或 `<shape>`+`<line>` 结构图、标签、表格）填充——页面依赖的图片区域空着又没有 fallback，等同破损页。
- 跨页看一遍：内容页的版式有变化，不是所有页都套同一组"标题 + bullets"的坐标。

如果用户指定了关键页，例如“架构解释”“Self-Attention 机制解释”“对比或演进视角”“总结页”，最终验证记录必须逐项说明这些页已存在。

## 回读后核对：图片

这几条 `xml_lint` 也不管，只能对着回读的 XML 自己核：

- 主视觉和内容图没有跨页复用：同一个 `file_token` 出现在多页就要补素材或重新排版，Logo、统一装饰除外。
- 附件来源的图片/表格，`width:height` 与原图比例一致（比例对不上就是被裁了）；这类素材只允许缩放、不允许裁剪。

`<img>` 是否越出 960×540 画布由 `img_out_of_canvas` 静态检查覆盖，不必再手工对坐标。

## 验证记录

最终回复必须包含简短验证记录，建议格式：

```text
验证记录：
- 回读：已执行 slides +xml-get，实际页数 N / 预期 N。
- 关键页：架构解释 / Self-Attention / 对比或演进 / 总结页均存在。
- 静态检查：每页写入前 xml_lint 均 error_count=0；回读全文重跑 xml_lint error_count=0。
- 逐页核对：主要 shape/img/table/chart 元素齐全，主视觉与版式符合规划，无空白页或破损页。
- 截图确认（按需）：如对疑似误报做了截图核对，写明页码与结论；未做则以静态检查为准（截图流程见 validation-visual.md）。
```

不要声称完成了人工视觉验收，除非确实打开或获取了可视化结果。仅从 XML 静态检查得出的结论，应表述为“静态检查未发现明显问题”。
