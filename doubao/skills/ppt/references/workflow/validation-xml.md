# 写入校验与回读核对

本文件是新建、编辑等流程共用的校验规则。**每个新增或修改页均须开启服务端 lint 提交，修复后继续开启 lint 重验**；默认不带 `--no-lint`，被阻断的写入不会生效。写入后还要确认实际存下来的内容，并补上页数、内容完整性、跨页 `id` 撞车和素材落地等检查。XML 可解析的文字与背景区分度会由 `text_color_contrast` 检查；图片背景、图片裁切、间距和跨页风格等仍需截图判断，见 [validation-visual.md](validation-visual.md)。

小型已有页编辑也要做对应范围的验证：至少读取被改页面或全文 XML，确认目标元素已更新、未破坏周边结构，并处理回读报告。编辑和模板任务在首次修改前保存原稿 lint 基线，规则见下文「原稿基线与前后对比」。

## 回读核对流程

1. 记录创建或编辑返回的 `xml_presentation_id`，以及已知的 `slide_id` / `revision_id`。`slide_id` 是页面唯一关联键；页码仅可作为展示信息。
2. 用 `slides +xml-get --output <CWD 内相对路径>` 回读全文 XML，并分别保存 stdout 完整响应和 stderr。XML 文件只含 XML；版本、读取范围和 `data.issues` 在响应 JSON 中。确认本次读取成功后，用 XML 解析器解析，并建立本次校验的 `slide_ids` 页清单；命名空间从根元素实际读取。增删页、整页替换或重排后必须刷新清单。
3. 完整读取本次回读的 lint 报告，编辑/模板任务与原稿基线比较；同时核对实际页数、关键元素与主视觉、空白/破损页、跨页 `id` 撞车（具体检查点见下方各节）。`xml_inspect.py` 只读取纯 XML，其 `summary.warnings` 是本地结构提示，不能代替服务端报告。
4. 按 [validation-visual.md](validation-visual.md) 核对真实渲染：新建和模板终稿检查全部页，已有稿编辑至少检查所有视觉变化页；写入成功但带问题发现或使用 `--no-lint` 的页须在该次写入后立即带 lint 回读、截图并实际查看，完成核验后才能继续下一页。报告中的 `screenshot_review_required: false` 不免除这些截图要求。
5. 发现问题的页用 `+replace-slide` 或对应写入操作修复后，开启写入 lint 重提，再带 lint 回读确认。创建过程部分失败时，先记录已创建的 `xml_presentation_id`，再回读确认哪些页已写入，不要假设失败的那一步没有副作用。
6. 在最终回复中给出简短验证记录，说明做了哪些检查；只有确实截图核对过时才写"已做视觉确认"。

文件保存在当前工作目录 `<CWD>` 下。`<CWD>` 仅用于说明位置；命令使用 `./readback.xml` 这样的相对路径，不把 `<CWD>` 字面量或绝对路径传给 CLI。

回读命令参数与返回字段见 [lark-slides-xml-presentations-get.md](../cli/lark-slides-xml-presentations-get.md)。

文件名按任务、页面和尝试次数区分；多次回读另存需要对比的快照，避免覆盖已有文件和原稿基线。先检查本次读取状态及响应的 `ok`，不要因路径上已有 XML 就认定本次读取成功。按下方用法读取 lint 检测状态、统计、诊断和相关问题详情；只看统计不能代替验收。未取得有效报告时按 [error-handling.md](error-handling.md) 处理。

## 服务端校验查什么、不查什么

服务端在落库前对提交的这一页检查：well-formed、schema 合法性（含 SML 命名空间前缀、iconType 合法性、必填属性与子元素、属性取值的枚举/范围/格式约束）、同页内元素 ID 重复、文本重叠、形状/图片/表格/图表遮挡文字、元素越界、文本溢出（纵向撑破高度与横向意外换行）、文字溢出背景容器、相邻卡片背景互叠、表格尺寸、icon 填充，以及布局密度（空白页、大容器/整页内容过稀疏）。

上述是写入校验的范围。回读只报告问题，不因发现 error 而阻断 XML 返回；不能假定回读与写入覆盖完全相同的规则，尤其不能用回读未报告 `sxsd_*` 证明已通过写入 schema 校验。写入每次只看提交的那一页；整份回读已可返回文档级跨页问题，应结合全文 XML 核对：

- **跨页 `id` 撞车**：写入的 `duplicate_element_id` 只覆盖单页；整份回读可在 `document.errors` 中返回跨页 ID 重复问题，必须读取并结合对应 XML 核实，不要只看 `slides`。新写的元素不要自己编 `id`，留空即可；改回读 XML 时把服务端 ID 只留在原元素上，复制出来的新元素要删掉 `id`。
- 页数、页序、内容完整性、素材落地：见下方三节。

## 校验报告怎么读

### 创建和写入的返回结构

返回 JSON 的外层包含 `ok` 和 `identity`：`ok` 表示调用是否成功，`identity` 表示调用身份。成功时业务字段位于 `data`，失败时错误信息位于 `error`。成功响应通常在 stdout，失败响应也可能在 stderr，按实际返回读取。

| 响应 | 当次处理 |
|---|---|
| `ok: true`，未附问题发现 | 从 `data` 记录 ID、版本等业务字段，继续流程。开启 lint 的单页提交可确认该次校验通过；空壳创建只确认文稿创建成功。最终内容与视觉验收仍按任务流程执行 |
| `ok: true`，有 `data.issues` | 已写入但有发现。对象/数组直接读；JSON 字符串解码后读；普通文本完整读。报告显示有问题时不能用空数组等默认值掩盖，未知格式不能按无问题处理 |
| `ok: true`，有 `data.slide_issues` | 多页创建按每项实际页标识及 `issues` 读取，保留与创建页的对应关系；其中的发现也按对象/数组、JSON 字符串或普通文本分别处理 |
| `ok: false`，`error.code: 4000153` | `error.message` 是一整段 JSON 字符串，先完整解码成报告，再读取全部问题；被拒页面未写入，修复后仍开启 lint 重提。多页创建中先前成功的页可能已保留 |
| `ok: false` 的其他错误，或响应不完整 | 读完整 `error` 或解析诊断，按实际原因处理；此时缺少 `data.issues` 绝不表示零问题 |

例如，单页被拒时返回的外层结构如下（仅用一条问题说明字符串包装方式）：

```json
{
  "ok": false,
  "identity": "user",
  "error": {
    "type": "api",
    "code": 4000153,
    "message": "{\"schema_version\":\"2.0\",\"tool\":\"xml_lint\",\"summary\":{\"error_count\":1,\"warning_count\":0,\"status\":\"blocked\"},\"slides\":[{\"slide_number\":1,\"errors\":[{\"code\":\"embed_svg_forbidden_attribute\",\"message\":\"embedded SVG uses forbidden attribute 'style' on <svg>\",\"element_ids\":[\"bxV\"]}]}]}"
  }
}
```

解析顺序是「外层响应 → `error.message` 字符串 → lint 报告对象」。成功的 `data.issues` 也可能包装同类报告；按实际类型决定是否解码。不要对已展开的对象再做 JSON 字符串解码，也不要把普通文字强行当 JSON。

报告对象的读取位置：

```text
lint 报告
├── summary                     检测状态和数量，用于导航与核对完整性
├── document                    errors / warnings / infos，文档级问题
├── slides[]                    每个报告页
│   ├── slide_number            当前报告内部页码
│   ├── errors / warnings / infos  页面分级问题列表
│   └── issues                  可能镜像该页分级列表，不重复计数
└── issues                      根部列表可能仅镜像文档级问题
```

`summary` 的 `error_count`、`warning_count`、`info_count` 是各级问题数，`status` 表示报告状态；`release_ready: true` 仍可能伴随 warning，具体问题以列表为准。逐条读完 `code`、`message`、实际存在的 `hint`、定位字段和测量依据，并核对文档级及当前页各级问题。只看 `summary`、`error.message[:200]`、`head` 或字符串长度，都不能证明问题已读完。字段不齐全不等于没有问题；详见下方「报告定位与去重」。成功附带发现时立即按回读与截图流程处理；真实问题须修复，不能只记录后继续下一页。

报告过大或工具输出截断时，先检查工具是否提供完整输出文件，或本次是否已保存完整响应。有完整响应文件时，可用 `lint_inspect.py` 分页读取；只有截断文本时，脚本无法恢复遗漏内容，报告应记为未读完整，不能认定全部问题已处理或据此豁免。重新回读得到的是当前已保存页面的报告，无法还原被拒候选 XML 的那次报告。写入状态不明时，按 [error-handling.md](error-handling.md) 处理。

### 回读：保存后立即读取 lint 检测报告

`+xml-get` 的 XML 与报告分开保存；用 `lint_inspect.py` 读取完整响应中的检测状态、各页数量和诊断，再按有问题的文档/页面范围读完详情。回读 `ok: true` 只表示读取成功，即使报告为 `blocked` 也会返回 XML；回读报告缺失、截断或解析失败均不能记为零问题。这与正常写入成功时可能不返回 `issues` 不同。

### 先读 lint 检测报告摘要，再按页读取详情

两种脚本的输入和输出不同：

| 脚本 | 输入 | 默认输出 |
|---|---|---|
| `xml_inspect.py` | `source.xml` 等纯 XML 文件 | **XML 内容与结构摘要**：页序、slide ID、元素统计和正文预览 |
| `lint_inspect.py` | `source-response.json` 或写入错误响应等 JSON 文件 | **lint 检测报告摘要**：检测状态、各页问题数量、错误码分布和报告解析诊断 |

`lint_inspect.py` 默认显示检测状态与问题统计；用 `--details` 读取具体问题、定位信息和修复提示；它不读取页面正文，也不生成 XML 内容摘要。

`LARK_SLIDES_SKILL_DIR` 指向当前 Skill 的绝对目录；输入和输出文件放在 `<CWD>` 下，命令使用相对路径。以下示例以成功回读响应为输入；读取长写入报告时，换成保留了该次完整响应的实际文件，脚本会解析字符串包装。

```bash
LARK_SLIDES_SKILL_DIR="<包含当前 SKILL.md 的绝对目录>"
# 默认返回 lint 检测报告摘要和前 10 页的问题统计；不展开问题正文
python3 "$LARK_SLIDES_SKILL_DIR/scripts/lint_inspect.py" --input ./readback-response.json

# 先查看文档级问题，再看相关页面；按返回的 next_offset 继续
python3 "$LARK_SLIDES_SKILL_DIR/scripts/lint_inspect.py" --input ./readback-response.json \
  --details --document --offset 0 --limit 3 --max-chars 6000
python3 "$LARK_SLIDES_SKILL_DIR/scripts/lint_inspect.py" --input ./readback-response.json \
  --details --slide-number 3 --offset 0 --limit 3 --max-chars 6000

# 已有完整写入错误响应文件时，可按此读取
python3 "$LARK_SLIDES_SKILL_DIR/scripts/lint_inspect.py" --input ./page-03-error.json
```

- lint 检测报告摘要包含接口是否成功、presentation/revision/scope、服务端统计与解析数量、每页问题数、错误码分布及诊断信息。报告中的页面问题统计通过 `page_pagination.next_offset` 继续读取。
- 脚本默认输出的 `pages` 只有页统计，详情正文在 `--details` 输出的 `issues[].issue`；不要在详情中找 `pages[].errors`，也不要把筛选错路径后的空结果当作零问题。
- 详情通过 `pagination.next_offset` 继续，保持原筛选参数，直到 `has_more: false`；`--slide-number` 可传多个页，另支持 `--slide-id`（仅响应明确提供的 ID）、`--level`、`--code`、`--issue-id`。筛选只是定位，不能因此漏读其他级别或文档级问题；默认不筛选时可遍历全部发现。
- 详情默认每批最多 10 条，并限制问题正文总字符预算为 12000；单条问题正文不会截断。若返回 `oversized_issue_id` 且本批无正文，用该 ID 单独导出，例如 `--details --issue-id i000001 --output ./issue-detail.json`，再分段读取文件；也可调大 `--max-chars`。输出文件只包含本次筛选/分页结果，继续检查其分页标记。
- `--output` 保存完整的本批结果，stdout 仅返回保存回执，**仍须主动读取输出文件**；不会创建目录或覆盖已有文件。未传 `--output` 时直接显示本批结果；工具若仍截断，减小批量或落盘后分段读取。
- `inspection_status: parsed` 表示完整报告已解析；`findings_only` 表示存在未附完整报告的发现列表，不能证明全部 lint 通过。`response_ok` 是接口结果，`lint_status` 才是可确认的报告状态；脚本退出码 0 表示可解析，不代表 lint 通过。缺失、冲突或未知格式退出码为 2，查看其诊断和保留的原文，不得据此绕过校验。
- `partial` 仍可分页定位已保留的问题，但缺失部分必须补齐；超出 lint 检测报告摘要显示上限的报告元信息或诊断可通过 `--output` 导出后查看。脚本不执行 lint、不自动修复，也不自动判断是否为原稿继承问题。

### 报告定位与去重

- `document.errors/warnings/infos` 和页面分级列表均需读取；报告根部 `issues` 在部分返回中只镜像文档级问题，不能当作全稿问题列表。
- 脚本仅合并相同范围内、完整内容相同的镜像记录；同一列表的重复条目和不同页面的同名错误保留。分类列表与合并列表不一致时保留额外发现并提示，实际数量与 summary 不一致时不认定报告完整。
- `element_ids` / `elements`、`target`、`related_objects`、`measurement` 等按实际返回保留；缺失字段不能按 0 处理，也不能因为没有 `hint` 或测量值而跳过问题。
- 单页报告的内部页码不一定是整稿页码；脚本保留响应页码与报告页码，不自行猜测 slide ID。整份报告仍需结合同次 XML 的页序与 ID 对应。来源位置和 `issue_id` 用于定位当前输入中的问题，不是跨版本匹配键。
- 报告缺失、JSON 截断或无法解析时，按上文检查是否有完整响应留存；没有留存时不能补齐原报告。回读失败可重新执行只读请求；结果不明的写入先回读确认状态，避免重复创建或更新。未知格式的原文可在详情中读取。正常写入成功、使用 `--no-lint` 后成功，均不能代替实际回读及必要截图核验。

**以每条发现的 `message` 和实际返回的 `hint` 为准动手改**；没有 `hint` 时结合对应 schema 或规则定位，不能忽略该问题。下面的表只用来快速认识 code 的含义和严重级，不重复 `hint` 的内容。

- `message` 说明发生了什么，通常带实测数值（如估算行宽 vs 可用宽度、各方向溢出多少 px）。
- `hint` 给出该条的具体修法。
- 定位元素先看报告实际返回的 `element_ids` / `elements`；这些列表可能为空，此时继续看 `target.xml_path` 或 schema 的 `path`，结合同页 XML 定位。常见定位方式包括：元素自己写了 `id` 就给这个 `id`；没写 `id` 就给 XML 路径 `slide[1]/data/shape[2]`（数 `<data>` 下第 2 个 `<shape>`，同类标签各自从 1 开始数，此时 `related_objects[].xml_path` 是同一个值）。`related_objects[]` 还带每个几何元素的 `kind`/`type`/`bbox`，可以拿 bbox 反查是哪个元素。
- `measurement` 与 `rule.comparison` 提供测量和判定依据；需结合 `message` 理解，不要只用一个数值自行推翻报告，例如线穿文字可能在 `intersection_area: 0` 时仍报 `bbox_overlap`。

**schema 错误会让该页跳过几何检查**：这一页存在 `sxsd_*` error 时，重叠/溢出/越界等几何检查全部不执行。先处理 schema，再开启 lint 重提并读完新报告；未执行的检查不等于通过，不能因第一轮没报几何问题就认定版式合格。

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
| `sxsd_unsupported_pattern` | 校验器读不懂 schema 里该属性的 XSD 正则，所以这个值**没有被校验过**（不代表值一定有错） | error·需人工确认 |
| `duplicate_element_id` | 同一个 ID 被多个元素使用；整份回读也可报告跨页重复 | error |
| `iconpark_unsupported_icon_type` | 用了 IconPark 不支持的 `iconType` | error |
| `icon_missing_fill_color` / `icon_transparent_fill_color` | `<icon>` 没有设置不透明的 `fillColor` | error |
| `shape_out_of_canvas` / `img_out_of_canvas` / `table_out_of_canvas` / `chart_out_of_canvas` | 文本框、矩形容器、图片、表格或图表超出校验使用的画布范围 | error |
| `line_out_of_canvas` | 线条超出画布，结合报告中的 canvas 与 overflow 核对 | error |
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
| `text_color_contrast` | XML 可解析背景下文字与背景区分度不足；按背景确定性和严重程度输出 error 或 warning | error / warning |

`sxsd_*` 是 schema 校验，`hint` 只说哪里不合规、不给正确写法：改之前对照 [`slides_xml_schema_definition.xml`](../xml/slides_xml_schema_definition.xml) 里该标签的定义，issue 的 `expected` 有值时会直接列出该处允许的子元素或取值，`path`（如 `slide/data/shape/content/text`）只有标签名、不带序号，和上面带下标的 `xml_path` 不是一回事。

`sxsd_unsupported_pattern` 是里面唯一的例外：它说的是校验器自己读不懂那条 XSD 正则，不是你的值有错，它的 `hint` 写给脚本维护者、照着改不动。对照 schema 里该类型的定义人工确认取值；确认无误后按下面的单页例外规则记录这一条能力缺口；仍须处理报告中的其他问题并完成例外核验，不能直接跳过整页所有问题。

### 影响排版的判定规则

这几条 `hint` 里没有，但决定了你该怎么摆元素：

- **图片压字**：`image_covers_text` 不看 z 序，也不看中间是否隔着蒙版或色块。两种豁免：铺满整页（≥95% 画布）且排在文字之前的整页背景图；以及排在文字之前、且几乎完整包住该段字形盒的局部背景图。只盖住半截文字的半出血大图一律会报。
- **图表压字**：`chart_covers_text` 不分上下层，压上就报，但环形图（`<chartPlot type="pie">` 带 `innerRadius`）的中心空洞是豁免的——把大数字标题放进甜甜圈中心是允许的，压在圆环本身上则会报。
- **文字溢出容器**：`text_overflows_container` 按文本框（authored box）而不是字形盒判定，且零容差——只要文本框跨过容器边界就报。贴着容器边缘（0px 间隙）摆放的说明文字也算这个容器的内容。
- **越界按实际报告核对**：除 shape/img/table/chart 外，报告也可能包含 `line_out_of_canvas`，不能假定线条不会报错；未确认覆盖的元素仍需自己核对坐标。底部留白也不在判定范围内，重要内容压过 `y=500` 要自己收。设计系统说的「出血 / full-bleed」是指贴齐画布边缘，不是用负坐标或超宽把图画到画布外——那样会报 `img_out_of_canvas`。
- **强制单行**：`wrap="false"` 不能解决框太窄的问题。文字放不下时它只会被裁切或溢出，服务端会按精确行宽报 `text_may_overflow_shape`（`overflow_axis: width`）。要单行就先把 `width` 加够，再配 `wrap="false"`。

## 原稿基线与前后对比

1. **修改前保存基线**：编辑/模板任务首次读取原稿，成对保存原始 XML 和完整响应（含 revision、读取范围与报告），后续另存最新回读，不覆盖基线。模板或多页任务优先整份读取；明确的单页编辑可只保存该页基线。未取得有效报告时只能记为基线校验未完成，不能把空报告当成“原稿无问题”。
2. **先对应页面与元素**：整份报告按同次 XML 的页序建立 `slide_number → slide_id` 对应；单页报告结合请求/响应中的 `slide_id` 定位，不假定内部页码就是整份 PPT 页码。增删、重排后按 ID 对应；模板派生页或元素重新分配 ID 时，使用已有来源映射和 XML 结构核对，不能仅因 ID 不同就判定新增，也不能无依据认定继承。XML 路径用于定位，不作为跨版本唯一标识。
3. **再比较同一问题**：结合页面、`code` / `rule.id`、相关元素及相互关系匹配，比较严重级、可用测量值和实际 XML 变化。溢出从 30px 增至 60px 是加重；A/B 重叠变成 A/C 重叠是不同问题。缺少测量值时结合属性、位置关系及截图判断，不得默认未加重。总数下降也不能掩盖某条新增或加重的问题。
4. **仅在相同检查范围内归因**：分别保留原稿回读、候选写入拒绝、实际写入后回读的报告，不混用版本或范围。回读未覆盖的规则、因 schema 错误未执行的几何检查，以及未读取的页面，都不能因“基线没报”就认定新引入；需结合原稿 XML 判断。反过来，基线有同名错误也不足以证明当前问题被继承。
5. **按范围处理**：新增或加重的真实问题必须修复；原稿既有问题按编辑/模板约定处理并说明，不能擅自修改范围外页面。基线报告只是归因依据，不能代替正常写入 lint，更不能直接授权 `--no-lint`；豁免仍须满足下方当前页、当前 XML 实际被拒的单页例外条件。

### 按目标页读取基线的例子

假设同次原稿 XML 表明整稿第 4 页的 `slide_id` 为 `SID_A`，而本次针对 `SID_A` 的单页写入报告内部页码为 1：先读取原稿报告的第 4 页详情，再与当次写入报告的第 1 页对照。两者对应同一个实际页面，不能直接按内部页码相等匹配。

```bash
python3 "$LARK_SLIDES_SKILL_DIR/scripts/lint_inspect.py" --input ./source-response.json \
  --details --slide-number 4 --offset 0 --limit 3 --max-chars 6000
```

页码 4 仅为示例，实际从同次 XML 索引确定。按返回的 `pagination.next_offset` 继续到 `has_more: false`，文档级问题另用 `--document` 读取。全稿报告未提供 slide ID 时不能用 `lint_inspect.py --slide-id` 盲筛；没有匹配项不证明目标页无问题。单页来源回读的内部页码也可能是 1，以该次请求/响应的 ID 对应。只读全稿统计、其他页详情或原稿 XML，均不算读过目标页的 lint 基线。

对比结论应能指出目标页、对应来源页、相关问题及依据；整稿总数有问题不代表目标页有问题，目标页无问题也不代表全稿通过。已有验证记录中写明本次检查范围即可。

## 修复与单页例外

**首次提交保护**：当前页首次写入时，直接携带 `--no-lint` 不能绕过服务端的首次校验，仍可能返回 lint 阻断。这属于服务端校验机制，不能据此判断 `--no-lint` 已失效或 CLI 不支持该参数。遇到这种情况，完整读取返回的检测报告，按问题修复，并恢复默认开启 lint 的提交方式。只有满足下方单页例外条件时，才可使用 `--no-lint`；首次被拦不代表下一次自动允许跳过。若 CLI 明确报告不识别参数，按 [error-handling.md](error-handling.md) 排查。

**修复须保留信息**：调整位置、尺寸、间距、线条走向等时，保留应有的正文、数值、单位、数据标签和图例；不得为了消除 lint 而批量删掉这些内容。修复前后核对内容差异，只有任务本身要求的内容增删才按计划执行。外层 `error.hint` 中通用的重试或跳过提示，不是某条问题已被证实为误报的依据。

1. **默认修复并重验**：报告里的问题绝大多数是真实缺陷。本次新增或加重的真实溢出、遮挡、越界及结构问题必须修复，不能以“继承模板”“有意设计”或“稍后截图”为由放行。每次修复都恢复 lint，读取新的完整报告并继续处理新暴露的问题，直到所有非豁免 error 清除；warning / info 也须逐条核对。
2. **先有本页证据，才判断例外**：只有当前页当前 XML 已在开启 lint 时被 `4000153` 拒绝，且完整报告中的每条阻断问题均已处理或逐条证实符合例外条件，才可单独对这一次提交使用 `--no-lint`。例外限于已核实的设计误判、上述校验器能力缺口，以及编辑/模板流程明确规定的情形；不能仅凭“原稿就有这个元素”认定问题被继承。记录本页、当前 XML、issue code、相关元素和依据，写入已有验证记录即可，不另建跟踪表。证据不足时不能豁免。
3. **豁免不能扩散**：不得写进多页循环、公共参数、包装函数的默认值或失败后自动降级重试；需要例外的页退出批处理，逐页单独处理。其他页仍须先开启 lint；同页再次修改后也须重新校验，不能沿用旧报告或上次豁免。页数多、同源模板、超时、限流或其他 API 错误都不是跳过理由。
4. **整页跳过不能冒充单条通过**：当服务端接受 `--no-lint` 的跳过请求时，跳过范围是整页写入校验；携带该参数本身不保证跳过生效。报告里其他问题仍须处理；schema 导致未执行的几何检查也不能记为通过。例外写入后立即回读、处理报告并实际查看本页截图，针对全部豁免项和可能漏查的布局核对，逐项记录结论后才继续下一页。回读通过不能追认写入 schema 已通过；截图只是补充核验，不能替代对已确认真实问题的修复。截图失败或问题未解决时，该页仍未完成验收，不得凭 `ok: true`、无 `issues` 或导出成功标记完成。

## 回读后核对：页数与完整性

下面这些服务端一条都不管，只能自己对着回读的 XML 看。空白页尤其别指望它：`blank_slide` 是故意宽松的，纯背景加一根装饰线的页它会放行。任何一条不满足，修复后再交付。

- 实际页数等于用户要求或大纲确定的页数，没有缺页、页序错误，也没有某页内容被 shell 截断。
- 每页都有 `<data>`，且 `<data>` 内至少有一个非背景主体元素——只有背景、装饰线或空 `<content/>` 的页算破损。封面、章节页、总结页可以文字很少，但不能只剩空背景。
- 关键文本确实出现在回读的 XML 里。
- `<img src>` 已经是 `file_token`，不是残留的 `@./path`，也不是 http(s) 外链（外链渲染端不代理，在幻灯片里通常不显示）。
- 没有一堆形状坐标完全相同、把主体内容压死。这种服务端也不报：它的形状重叠规则要求至少一方承载文字，并且会跳过完全包含的情况，几个坐标相同的空面板刚好两条都躲过。
- 渐变背景没有回退成空白或白底，导致文字不可读。

## 回读后核对：关键元素

按用户要求和大纲逐页核对：

- 标题或主结论存在，并能对应这一页要传达的核心信息。
- 这一页规划的主要结构（如对比、时间线、架构、流程、大数字等）已生成；技术解释、对比、流程、架构这几类页必须有匹配的结构元素，例如分组框、连线、时间轴、表格或图形化区域。
- 若该页包含树状图，回读 XML 中树状图主体必须是 `make_relation_atomized(..., strict_no_embed=True)` / CLI `--atomized` 生成的可编辑元素，不得是 `<embed>`。
- 主视觉是页面中最醒目或最大的信息区域之一。
- 文本量符合规划，高密度页用分栏、表格或分组承载，没有用单个长 bullet 框堆砌替代版式。
- 有真实素材的已放入正确区域；没有真实素材的，已用兜底方案（生图近似图、原生 `<chart>`、或 `<shape>`+`<line>` 结构图、标签、表格）填充——页面依赖的图片区域空着又没有 fallback，等同破损页。
- 跨页看一遍：内容页的版式有变化，不是所有页都套同一组"标题 + bullets"的坐标。

如果用户指定了关键页，例如“架构解释”“Self-Attention 机制解释”“对比或演进视角”“总结页”，最终验证记录必须逐项说明这些页已存在。

## 回读后核对：图片

这几条服务端也不管，只能对着回读的 XML 自己核：

- 主视觉和内容图没有跨页复用：同一个 `file_token` 出现在多页就要补素材或重新排版，Logo、统一装饰除外。
- 附件来源的图片/表格，`width:height` 与原图比例一致（比例对不上就是被裁了）；这类素材只允许缩放、不允许裁剪。

`<img>` 是否越出 960×540 画布由服务端的 `img_out_of_canvas` 覆盖，不必再手工对坐标。

## 验证记录

最终回复必须包含简短验证记录，建议格式：

```text
验证记录：
- 回读：已执行 slides +xml-get 并读取默认返回的 lint 报告，实际页数 N / 预期 N；写明报告是否完整、问题处理结论，编辑/模板任务说明与原稿基线相比的新增、加重及保留问题。未取得有效报告不能记为通过。
- 关键页：架构解释 / Self-Attention / 对比或演进 / 总结页均存在。
- 写入校验：列明开启 lint 通过的页面；返回 issues 的页与使用 --no-lint 的页，逐条写明页码、问题及处理依据、回读和截图结论。跳过页不得记为“lint 通过”，未核验页不得记为完成。
- 逐页核对：主要 shape/img/table/chart 元素齐全，主视觉与版式符合规划，无空白页或破损页，无跨页 id 撞车。
- 截图确认：写明已截图的页码与结论。
```

不要声称完成了人工视觉验收，除非确实打开或获取了可视化结果。
