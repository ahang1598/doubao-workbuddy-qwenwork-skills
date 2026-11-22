# 模板工具说明

配合 [模板制作流程](workflow.md) 使用。这里提供参数、函数接口、脚本用法与恢复说明；具体任务与目标页面以用户要求和当前主流程为准。

## 阅读导航

以章节为阅读单位，首次使用某项工具时完整读取对应部分；后续沿用已读且仍适用的说明，不为每页重复阅读全文。

| 当前需要 | 阅读部分 |
|---|---|
| 组成整稿配方或机械填充、迁移 | [内容配方](#内容配方) |
| 首次发布页面、确认 ACK 与真实 ID | [发布与恢复](#发布与恢复) 和 [结果与恢复](#结果与恢复) |
| 用共享值计算、格式化和填入指标 | [共享指标显示值](#共享指标显示值) |
| 调用版式槽、原生图表、角色卡或原稿迁移工具 | 发布章节内对应的 L3/L6/L9/L8 部分 |
| 选择严格检查或处理未知写入 | 发布章节内的相应诊断/恢复部分 |

指标与严格诊断按实际需要查询，不是普通任务的必读部分。这里只解释模板工具，不提供角色判断、派单、交接或代理等待流程。

## 内容配方

这是模板内容配方的工具说明，支持 Python 函数和直接运行脚本。函数调用时，在 Python 中设置主流程的技能根目录、工作目录、`plan` 和目标 `DECK`：

```python
import sys
sys.path.insert(0, str(LARK_SLIDES_SKILL_DIR))
from scripts.template.template_authoring_plan import prepare_plan, run_plan

# 只准备稿件时使用 prepare_plan(plan, work_dir=WORK_DIR)。
# run_plan 自带准备与逐页发布，不必先重复 prepare_plan。
result = run_plan(plan, work_dir=WORK_DIR, presentation=DECK)
```

用于已完成内容与版式选择的机械填充、迁移和发布。MainAgent 负责语义、图片与图形关系，脚本消除重复操作；发布诊断、真实 ID 登记和未知回执恢复由 `template_publish.py` 负责。

先完成一个典型页并核对源图与目标截图，再编写整稿配方。多页 XML 已准备好时，用 `ready` 配方列出每个逻辑 `page` 对应的真实 `xml` 路径，交给 `run` 串行发布与补发；不另写 shell 循环拼文件名。执行器遇到真实写入失败/未知或构造失败时停并返回 `next_page`；默认视觉/来源建议不会逐页暂停。发布器用登记中的真实 ID 原位更新或按逻辑页号插到后页之前。所有相对路径以 `WORK_DIR` 为基准。每页明确 `page/link/mode/operation`：

- `migration`：原稿 `source`、目标视觉 `frame`、`frame_ids`、完整 `content_ids`、`placements` 或 `target_region`、可选 `role_styles/bindings/source_roles`。L8 用 `component_reuse` 和 `explicit_numbering: true`，讲稿直接保留原值。
- `fill`：完整组件 `source/ids/fill_plan` 与本题 `notes`（字符串或段落数组），新文字与讲稿同时填入。`fill_plan` 由 `template_reuse.py prepare-fill` 生成并逐槽完成。
- `ready`：已准备好的单页 `xml` 与该页已有 layout/chart/style 等合同、绑定。讲稿已经在 XML 中。 设置 `apply_values: true` 时，从共享值单次填入原生正文、标题、表格与notes中的 `{{key}}`；属性、图片路径、图表和SVG保留原样。默认ready不改原文。

每页可选 `no_lint: true` 直接跳过已判断的视觉误报，`reason` 只是说明，`strict: true` 才启用严格阻断；默认不要求豁免 JSON。

`fill/ready` 可选 `explicit_numbering: true` 把现有有序列表起点显式化；各 operation 可选 `text_fit_ids` 对指定文字容器准备内边距，失败则返回该页容量问题。二者保留已有字、顺序、角色和几何。

可选 `publish_source` 指发布时比较的真实模板源页；L8 不把原稿事实文件误当作目标模板。首个导入占位页提供真实 `slide_id`。核对源图后可在该页设置 `source_visual: "源页图片路径"` 或路径列表，执行器传给发布器自动复核原样装饰出血。

以下是 L8 两页配方结构，实际 ID、区域、文字与讲稿从本题材料和源页填写：

```json
{
  "pages": [
    {
      "page": 1, "link": "L8", "mode": "component_reuse", "operation": "migration",
      "source": "original-slides/slide-01.xml", "frame": "authoring/frame-01.xml",
      "frame_ids": ["background"], "target_region": [40, 100, 880, 380],
      "role_styles": {"title": {"fontFamily": "Arial", "fontSize": 32}},
      "explicit_numbering": true
    },
    {
      "page": 2, "link": "L8", "mode": "component_reuse", "operation": "migration",
      "source": "original-slides/slide-02.xml", "frame": "authoring/frame-02.xml",
      "frame_ids": ["background"], "target_region": [40, 100, 880, 380],
      "explicit_numbering": true
    }
  ]
}
```

`values_file` 或 `values` 存已经计算和格式化的字符串；可用 [共享指标显示值](tools.md#共享指标显示值) 从声明了名称、单位、口径和时段的端点生成。`{{key}}` 替换 fill 的 `new_text/notes`，也可由ready的 `apply_values: true` 填原生文字，不执行公式。例如 fill 的字段 `new_text: "年度目标 {{project_target}}"` 与讲稿 `notes: ["本页目标为 {{project_target}}。"]` 共用 `values: {"project_target":"27 项"}`。来源文字、路径及原稿备注保持原值。图片、关系图和图表片段在配方准备前按本题组织。

```bash
python3 "$LARK_SLIDES_SKILL_DIR/scripts/template/template_authoring_plan.py" run \
  --plan "manifest/authoring-plan.json" --work-dir "$WORK_DIR" \
  --presentation "<真实deck ID>"
```

`run` 自带准备与逐页发布，成功页继续，实际构造/写入失败或未知时返回 `next_page` 和报告。只有需要先取得离线稿时才另用 `prepare`（或 `prepare_plan`）；它保存 XML、来源及输入快照。`no_lint`/`strict` 按本页参数传给发布器；不手删 pending 来重复追加。修改失败页时给作者输出使用新版本文件名，避免覆盖已发候选证据，再从该页继续：

默认已写入页的文字容量风险留到整稿看图，不暂停后页。只有明确 `strict: true` 时可因 `requires_review` 在该页暂停；它不是写入失败，不重复 add。需要修订用真实 ID 原位更新。

```bash
python3 "$LARK_SLIDES_SKILL_DIR/scripts/template/template_authoring_plan.py" run \
  --plan "manifest/authoring-plan-v2.json" --work-dir "$WORK_DIR" \
  --presentation "<同一deck ID>" --start-page 14
```

回执未确认时，按发布响应的 `recovery_flag` 给原命令追加恢复参数，保留原目标、XML 和 `validation_policy`，只读核对原页。存在业务 ACK 时使用 `--recover-readback`；误用通用 `--recover-write` 也会进入相同的严格 ACK 回读，不重复写入。确认实际内容并查看恢复报告后，从 `next_page` 继续同一份计划。不要换成裸追加命令或修改登记跳过停点。`published_all` 证明逐页写入被确认，后续仍完成主流程的全稿内容、视觉核对与导出交付。

## 发布与恢复

这是模板发布工具的操作说明，支持 Python 函数和直接运行脚本。函数调用时，在 Python 中设置主流程的技能根目录及本页变量：

```python
import sys
sys.path.insert(0, str(LARK_SLIDES_SKILL_DIR))
from scripts.template.template_publish import publish

result = publish(presentation=DECK, work_dir=WORK_DIR, xml=PAGE_XML,
                 page=PAGE, mode="component_reuse", link=LINK)
```

`template_publish.py` 默认轻量发布：本地视觉估算、模板几何/风格与来源合同是诊断建议；真实业务 ACK 后登记并继续后页。已 ACK 的回读差异作为可选诊断，不锁住整稿。真正未知的写入才先只读确认，避免重复追加。

```bash
python3 "$LARK_SLIDES_SKILL_DIR/scripts/template/template_publish.py" \
  --presentation "$DECK" --work-dir "$WORK_DIR" --xml "$PAGE_XML" \
  --page "$PAGE" --mode component_reuse --link "$LINK"
```

首次更新保留页加真实 `--slide-id`；后续同页使用登记 ID。source/layout/chart/style 参数有需要才提供，不要求每页先准备校验 JSON。`published` 是已写入；全部页面完成后直接导出并交付，用户明确要求检查时再核对实际稿。

**误报直接跳过**：需要时原命令加 `--no-lint`，可选 `--reason "原模板出血/已看图"`，跳过本地视觉检查和服务端 lint，无需旧拒绝报告或声明文件。无效单页 XML、错目标、真实 API 拒绝不因此变成功。`--strict` 才恢复旧的合同与启发式阻断；旧 `--exception-file` 仅作可选严格调试兼容。

**实际画布**：从当前 deck 整稿 XML 根读取 `DECK_W/DECK_H`。单页本地检查可在命令前传 `LARK_SLIDE_CANVAS_W="$DECK_W" LARK_SLIDE_CANVAS_H="$DECK_H"`；它不改变远端画布。写入侧可能仍误用 960×540，这时不要缩坏正确稿，直接选择跳过误报并在整稿看实际图。需要尺寸转换用 `template_reuse.py transform` 同步变换外框、局部 path、字号、线宽等。

### 可选生成工具与严格诊断

下面参数帮助复用来源、构造原生内容和排障。默认发布不会因这些诊断失败而阻断；只有 `--strict` 使用其旧阻断行为。仅在实际用到对应工具时查该节。

### L3 版式槽

先用 `template_layouts.py --pptx ... --output "$WORK_DIR/manifest/layouts.json"` 读取真实目录，再逐页用 `template_layout_contract.py --manifest ... --layout "<名称>" --instance-id P2 --output "$WORK_DIR/manifest/layout-contracts/page-02.json" --skeleton "$WORK_DIR/authoring/slide-02.xml"` 生成空槽。填内容后发布：

```bash
python3 "$LARK_SLIDES_SKILL_DIR/scripts/template/template_publish.py" \
  --presentation "<deck ID>" --work-dir "$WORK_DIR" \
  --xml "$WORK_DIR/authoring/slide-02.xml" --page 2 --mode active_rebuild --link L3
```

默认查 `manifest/layouts.json`、`manifest/layout-contracts/page-NN.json`，支持 `--layout-manifest` / `--layout-contract` 指定路径。标题用生成 slot ID，保持原 bbox、字号、字体、字色和对齐；检查实际文字 run 的有效样式，不能改绑定中的源样式来放行。正文/图表完整落在所选槽内。一槽多元素或改 ID 时提供 `page-NN.bindings.json`（或 `--layout-bindings`）：

```json
{"elements":{"native-title":"<title slot_id>","chart-a":"<content slot_id>","caption-a":"<content slot_id>"},"decorative_ids":["background-image"]}
```

无 ID 可用 `data_index:0`（`<data>` 直接子元素的零基序号）。Title Only/Blank 的内容自由区用独立 JSON `[{"name":"content-area","bbox":{"x":36,"y":125,"width":648,"height":360}}]` 传 `--free-regions`；这些是按源构图选定的留白区，不是自动拉满画布。版式绑定记录在 XML 外，不添加 schema 未定义的属性。

中英文文字分别按真实源 Latin、EA/主题脚本字体继承；中文采用源宋体等合法源字体不算替代。源字体不可用时，bindings 增加 `"font_substitutions":{"<title slot_id>":{"fontFamily":"<实际支持的替代字体>","reason":"源字体不可用及保持原字形职责的依据"}}`；不借此改字号或文字色。

### L6 原生图表与源配置

先从 `manifest/native-chart-inventory.json` 选择实际源 chart/group ID，再准备**本题**新数据；源索引不含样例数值/类别。`new_data` 结构：
```json
{"category_name":"季度","categories":["2024Q4","2025Q4"],"series":[{"name":"本题指标","values":[18.8,20.1]}]}
```
每个新系列显式映射源系列索引，例如 `[0]`。源有逐点色而新类目数不同，使用 `{"series":0,"point_map":[0,1]}`；把某个源点色变成统一系列色用 `{"series":0,"color_point":1}`，两者不并用。数量、系列、色彩职责改变时说明适配原因；不把 logo 色当数据色。百分数值 18.8 配 `value_format: "0.0\"%\""`，分数 0.188 才配 `0%`；formatter 不自动缩放输入值。

本题需要可查数值时，在 `new_data` 中设置 `value_format` 或 `data_labels`。例如以下字段显示分段数值和系列名；也可保留底部图例。多系列堆叠须能用图例或柱/条分段系列标签识别身份，单系列可用分类名识别并设置 `legend: {"present":false}`。图表生成 API 的具体适配理由用 `adaptation_reason`，脚本接口用 `--reason`；生成工具有实际要求时提供，发布器的 `--reason` 本身是可选说明。

```json
{"value_format":"0.0\"%\"","data_labels":{"value":true,"series":true,"position":"inside","format":"0.0\"%\""},"legend":{"present":true,"position":"bottom"}}
```

显式格式会覆盖源中隐藏的数值刻度，数据标签同时写到全局和系列层。暗色页面可指定 `data_labels.color`、`legend.color` 或 `value_axis.label_color`，如 `"rgb(255,255,255)"`；不指定分段标签色时按源系列填充色选择对比文字色。

多系列标签叠在一起时，可在单个 `series[i].data_labels` 写标签配置或 `false`：例如参考期关闭、新一期显示值。出现系列级配置后不再输出全局标签，避免关闭的系列被全局设置重新打开；其余系列按自身设置或原有效设置生成。line/area 使用 `auto`，柱/条非堆叠可用 `outside/inside/center/top/bottom`，堆叠只用 `inside/center/top/bottom`，pie 使用 `inside/outside`。保留图例和明确可读的轴：顶层 `value_format` 仍恢复数值刻度。全部值标签关闭时必须有显式格式及真实数值轴，不能留下不可读的空图；只省略节点，不写非法 all-false `chartLabels`。

```json
{"value_format":"0.0\"%\"","series":[{"name":"参考期","values":[18.2,18.8],"data_labels":false},{"name":"本期","values":[17.7,18.1],"data_labels":{"value":true,"position":"auto","font_size":12}}],"legend":{"present":true,"position":"bottom"}}
```
此处是标签设置示例，其余 data 类别、源系列映射和适配理由按实际图补齐；不改变原值来拉开标签。生成后看真实截图核对标签未重叠，轴单位/刻度和系列身份可读。

```bash
mkdir -p "$WORK_DIR/manifest/chart-contracts"
python3 "$LARK_SLIDES_SKILL_DIR/scripts/template/template_chart_contract.py" \
  --inventory "$WORK_DIR/manifest/native-chart-inventory.json" \
  --chart-id "<真实源chart ID>" --data "$WORK_DIR/new-data-02.json" \
  --series-map "$WORK_DIR/series-map-02.json" --reason "<本题条件与适配理由>" \
  --output "$WORK_DIR/authoring/chart-fragment-02.xml" \
  --contract-output "$WORK_DIR/manifest/chart-contracts/page-02.json" \
  --bindings-output "$WORK_DIR/manifest/chart-contracts/page-02.bindings.json"
```
同页小多图使用 `--group-id` 替代 `--chart-id`，data 文件为 `[{"data":<new_data>,"series_map":[0]},...]`。源完整成员、行列与间距规律保留，减少节点保留原槽，增加节点按原行距延伸并说明；不把原分面压成单一大图。`--bbox` 可给 JSON `left/top/width/height` 整组目标区。

同指标分面用共同轴比较柱高时，给组生成命令增加 `--value-axis '{"shared":true,"include_zero":true,"format":"0.0\"%\""}'`，或用 Python API：

```python
built = build_group(
    inventory, group_id, panels,
    value_axis={"shared": True, "include_zero": True, "format": '0.0"%"'},
    adaptation_reason="本题同一利润率分面共用零基线与刻度",
)
```

`panels` 仍按上述结构提供本题数据和源系列映射。共同 `min/max` 只从这些新数据计算并向外取整数；正负堆叠按各自累计值覆盖，所有分面使用同一界限与格式。例如 21.6 与 11.8 使用 `0..22`，输入值保持原样。可在 `value_axis` 中给整数 `min/max` 固定范围；单图则把 `value_axis: {"min":0,"max":25,"format":"0.0\"%\""}` 放入 `new_data`。SML 轴界限只接受整数；该共同轴接口不猜测饼图、组合双轴或百分比堆叠的轴域，遇到这些配置按返回的适配器边界处理。

输出是**一页的图表片段**，合入完整页面 XML 后再发布：
```bash
python3 "$LARK_SLIDES_SKILL_DIR/scripts/template/template_publish.py" \
  --presentation "<deck ID>" --work-dir "$WORK_DIR" \
  --xml "$WORK_DIR/authoring/slide-02.xml" --page 2 --mode component_reuse --link L6 \
  --source "$WORK_DIR/source-slides/slide-04.xml"
```
发布默认读取上述单页 contract/bindings，验证实际 `<chart>`、新数据、源图种/配置、系列/逐点配色、组几何，再执行通常 lint。路径可用 `--chart-inventory` / `--chart-contract` / `--chart-bindings` 指定；加文字/装饰不改变 `bindings.chart_sources` 的 `chart_index:N`，重排图表后须更新。

真实源有时含不可见的重复辅助系列，而不是第二个业务指标或范围。inventory 只有在原 area 与 line 同公式/同值/同缺点 mask、line 为 noFill、无 marker/标签/error bars 时标记 `hidden_duplicate` 和源 `helper_of`。这类源可保留 area+invisible line 的原生组合；明确的新数据声明如下：
```json
{"kind":"combo","categories":["2024Q1","2024Q2"],"value_format":"0.0\"%\"","source_gap_policy":"continuous_new_data","series":[{"name":"季度利润率","values":[19.7,19.9]},{"name":"隐形重复辅助","values":[19.7,19.9],"hidden_duplicate":true,"helper_of":0,"data_labels":false}],"legend":{"present":false}}
```
源系列映射仍为 `[0,1]`；`helper_of` 是对应新可见系列位置，辅助值必须完全等于同一新数组，不可把独立指标藏起来。隐藏系列保持透明线、零 marker、无标签/图例，不造新可见颜色。适配理由须说明：本题连续新季度不需要原分类分段，保留源三行图区与面积风格。原五段 gap 原样保真仍未实现；未明确改分段职责或要求 preserve 会拒绝，不用 0 填缺点。scatter、隐藏 bar scaffold、error bars 等其它复杂源仍按实际边界处理；双系列/堆叠的合法完整数据不能误诊为只支持单系列。

Python API `build_chart(...)` / `build_group(...)` 返回 `xml/contract/bindings`；原生表格用 `build_table(inventory,{"headers":[...],"rows":[...]},bbox=...)`，真实表格与数据才可标 `table_page`。封面/结尾用 `make_page_contract(inventory,role="cover"或"ending")` 生成非数据页 contract；按真实用途选择角色，不把手画柱条改标成表格或封面。source 范围/ghost baseline/scatter 等当前适配器不支持的配置会给具体边界和替代方向：可按索引+schema自行原生处理完整配置，或选择数据语义自然匹配的同模板图；不以实现限制断言模板不适合，也不编范围数据。

### L9 视觉角色卡

PDF 参考的只读提取与角色确认见模板工作流 Step 1。发布 L9 时自动读取 `manifest/style-card.json`；不同页型可显式给 `--style-card <该页卡JSON>`。它在写入前核对实际 SML 中所有 `textType=title` 主标题及正文/已绑定文字角色，不能用金色眉标替代金色主标题。样式卡须包含主标题准确的 `fontFamily/fontSize/color`。

用户明确要求先独立保存在 `manifest/style-overrides.json`，再传给 card 命令的 `--overrides`。发布 L9 时自动读取这份文件，或用 `--style-overrides <JSON>` 指定；格式与 `build_style_card(..., role_overrides=...)` 一致。外部要求、卡的 `user_overrides/selected/field_basis` 和实际文字一起核对，不能删卡内标记、同步重选参考色来跳过已保存要求。所有页型卡沿用同一份用户要求；完整报告与登记保存其路径/哈希。机械检查不会从缺失文件推断用户的自然语言意图，所以先保存要求仍是必要步骤。

非默认文字角色用 `--style-bindings <JSON>` 绑定实际元素 ID，例如 `{"main_title":["title-id"],"kicker":["kicker-id"]}`；默认读取卡旁同名 `.bindings.json`，绑定不覆盖其他 `textType=title` 的检查。缺失字体的替代可给 `--style-font-substitutions <JSON>`，内容为 `[{"from":"<参考字体>","to":"<已支持替代>","basis":"font_unavailable","reason":"<已核对的缺失情况与字形角色>"}]`，只豁免该字体族差异，不豁免字色/字号。完整报告保留卡、绑定和替代文件的路径/哈希。

卡和独立要求文件都没有时不执行角色卡检查；缺卡或角色不匹配默认写入诊断，只有 `--strict` 且未选 `--no-lint` 时返回 `style_card_blocked` 并拒绝写入。工作流仍需先建立和视觉核对样式卡。卡内的几何候选准确性、底色、信息密度以及正文/备注是否搬用参考内容仍须逐页看图与语义比较，不能从此校验通过推断它们通过。

### MainAgent 已有困难页的基线检查与更新

MainAgent 自行优化已发布困难页时，可用 `--local-cache <实际单页回读缓存>` 核对外部编辑基线并更新同一实际 `slide_id`，不需要派单或所有权交接。缓存接受完整单页 XML 或包含该页 XML 的 JSON envelope；任何显式 deck/slide 身份必须一致。来源模板页、未发布 draft 和候选文件不是当前页缓存，缓存也不能与候选同路径。

```bash
python3 "$LARK_SLIDES_SKILL_DIR/scripts/template/template_publish.py" \
  --presentation "$DECK" --work-dir "$WORK_DIR" --page "$PAGE" --mode "$MODE" --link "$LINK" \
  --xml "$PAGE_DIR/candidate.xml" --slide-id "$SLIDE_ID" --local-cache "$PAGE_DIR/cache.xml" \
  --source "$SOURCE_XML"
```

没有可编辑源页时省略 source，layout/chart/style/reflow 等参数照常提供。默认服务端 lint 仍会请求，`--no-lint` 可跳过；本地视觉/来源检查默认是建议。缓存基线保护与这些视觉诊断分开：写入前回读相同目标页，比较全文、notes、样式/几何、图片 token 和图表/表格数据，忽略无关的 presentation revision 等包装元数据。冲突返回 `cas_conflict` 并刷新缓存，尚未写入；前读失败为 `cas_readback_failed`。该参数只接受真实已有目标，不会回退 add。

这是乐观基线检查，**不是服务端原子 CAS**。模板各页均由 MainAgent 逐页发布，同 work-dir 发布锁仍保护写入窗口。不能据读-比-写承诺任意外部编辑不会竞态，也不把旧 revision-id 当条件锁。

ACK 后回读用于刷新缓存。**默认 advisory** 下，回读失败或内容差异仍返回 `published`，并给 `needs_final_review`、`review_status` 等诊断；继续后页，最终核对实际内容，不重新写入已 ACK 页面。**严格模式** 才可能返回 `published_readback_failed` / `published_content_unconfirmed`，保留 ACK barrier；仅这类严格请求仍有 pending 时，按响应的 `recovery_flag` 保留原身份、XML 与 `--strict` 做只读恢复：
```bash
python3 "$LARK_SLIDES_SKILL_DIR/scripts/template/template_publish.py" \
  --presentation "$DECK" --work-dir "$WORK_DIR" --page "$PAGE" --mode "$MODE" --link "$LINK" \
  --xml "$PAGE_DIR/candidate.xml" --strict --recover-readback
```
它核对原报告/存档 payload 哈希/登记行及目标身份，只补回读缓存和恢复证据，不 add/update。成功返回 `readback_recovered_requires_review`；默认 `requires_review=false` 并留待最终核对，严格模式为 `requires_review=true`。操作成功不代表视觉已完成；MainAgent 读取最新实际页再处理余项。失败为 `readback_recovery_failed` 且保留 barrier；未知写入、身份不符或没有该 ACK barrier 返回 `readback_recovery_refused`，不能用此口盲清 pending。

### 可选严格诊断：固定页条目重排

需要精确核对固定页来源时使用本节；默认制作不要求这些哈希声明。严格检查核对源成员、元素类型、几何和文字框方向；竖排/nowrap 还核对显式段落与断行结构。空文字槽填内容、普通正文自动换行和原生数据更新仍允许。条目数量/容量变化时，只有该完整内容组件可在原联合框内重排，给 `--fixed-reflow`：
```json
{"source_sha256":"<源XML SHA256>","groups":[{"member_ids":["<完整组件成员>"],"reason":"条目数量或容量变化的具体依据"}]}
```
源组至少两个真实成员；原框由源几何计算，其它标题、框架、装饰不解锁。移动整个组件或改变构图应如实标 `component_reuse` 并记原因。源码自动适配或文字未变的微小高度差单独处理；横移、加宽、缩短装饰线不算自动适配。

**严格模式**下，需要核对示例槽的删除或清文字时，可在同一 JSON 的 `removed_slots` 逐槽登记；没有重排可省略 `groups`：
```json
{"source_sha256":"<完整源XML SHA256>","removed_slots":[{"element_id":"<真实源槽ID>","source_member_sha256":"<该源成员哈希>","reason":"材料未提供该示例槽事实的具体依据"}]}
```
成员哈希按标准库 `xml.etree.ElementTree` 解析原文件后计算 `hashlib.sha256(ET.tostring(member, encoding='utf-8')).hexdigest()`，完整源文件哈希另算；不是提取片段或目标成员的哈希。无文字底形/装饰不算未知事实，只有已声明完整条目重排时才可随该条目移除。删除声明不允许仍留着该源槽的新事实；逐字标题应在原字框填字，不能声明删除字框后合并到新竖排框。理由和组是否完整仍需源图核对，哈希本身不证明语义。此检查只适用于 `fixed_template`，组件迁移仍按完整组适配并人工核对。

原生 chart/table/line 没有 XML ID 时，用源页按类型零基序号的外部键 `chart_index:N` / `table_index:N` / `line_index:N` 声明，仍对原源成员算哈希，不向 XML 加 ID。目标按类型与唯一源静态几何匹配，删除前项不重算源键；无可核对几何或身份匹配模糊时需先处理具体边界。未声明重排的 native line 还比较有序起止端点，bbox 一样不代表连线未改变。

### 可选诊断：原样装饰出血

普通制作遇到装饰出血误报可直接 `--no-lint`，无需先造声明文件。本节只用于需要追溯源装饰的精确诊断，参数与记录不作为默认发布许可。适用对象为源页已有、视觉核对为装饰且结构原样保留的形状/图片。看过源页图片、确认出血是装饰后，发布时加 `--source-visual <源页图片>` 和 `--source <源页XML>`。脚本自动找出同画布、同几何、同素材、无可见文字的原样出血成员并保存完整复核记录，不需要复制图片或手写哈希/ID；保留源几何，不先移动装饰再回滚。图片内的字仍需作者看图判断。

已有精确成员声明也兼容 `--source-decorations <JSON>`（两种参数选一种），格式如下，源哈希为完整源 XML 的 SHA-256：

```json
{"source_sha256":"<源页XML SHA-256>","element_ids":["<源装饰ID>"],"reason":"源截图中该元素的用途与有意出血依据","visual_evidence":["source-page.png"]}
```

给发布命令加 `--source-decorations <该JSON>` 和 `--source <源页XML>`。证据路径相对该 JSON。预检重跑严格源 lint，核对源/目标完整元素、共享 style、图片 token 和同画布的原生出血，原 errors 保留在报告，已复核项另记原因与证据哈希。可见文字、图表、表格、改变几何/素材、其它错误不适用。服务端首次仍开启 lint。仅在已提供该源图复核参数、正常提交明确 `4000153` 拒绝，且报告的全部 error 都与已复核装饰的 code/ID/画布/bbox 一致时，脚本自动消耗一次绑定当前页/精确 XML 的例外提交；保留首次拒绝和例外记录，提交后回读核对内容。新增错误、文字越界、身份不明、报告不全均不能走此例外；第二次失败停止。

### L8 源内容迁移

先用 `template_migration.py compose` 从原稿单页内容树生成本页XML与源绑定合同：原p/span、表格、图表、信息图片和note直接复制，目标视觉壳决定背景、容器、字体和位置。标题、正文和图表可在 `placements` 中分组适配目标槽，讲稿保留原值（含原稿空note）。

L8发布默认读取 `manifest/migration-contracts/page-NN.json`，可用 `--migration-contract` 指定路径；ID或媒体token换绑时，提供同名`.bindings.json`或`--migration-bindings`，格式为 `{"ids":{"source-id":"actual-id"},"media":{"source-token":"current-upload-token"}}`。合同记录原SML路径/哈希与事实成员；发布报告和页登记保存合同来源，后续回读用同一基线。正文、表格单元格、数据/标签与notes比较来自源树，视觉样式可按角色调整。原PPTX导入时已损失的内容、图片旋转或图内文字须先对照原稿补回，不由合同自动恢复。

### 结果与恢复

| status | 含义与处理 |
|---|---|
| `published` | 业务已确认并登记；可以继续后页并正常交付，诊断按需查看 |
| `write_rejected` | 业务拒绝，未写入；视觉误报可直接加 `--no-lint`，实际 API 问题按错误处理 |
| `write_unknown` / `write_content_unconfirmed` | 未得到 ACK；先只读确认原目标，避免重复追加 |
| `*_blocked` | 先确认 `validation_policy`：来源/视觉合同只在 strict 时阻断；无效 XML、目标冲突或明确 API 拒绝仍须按实际错误处理 |

`--exception-file` 是可选的旧诊断接口，不要求普通任务使用；正常误报直接 `--no-lint` 即可。使用该接口时才需要绑定单次服务端拒绝：仅当前 XML 的正常提交明确 `4000153` 拒绝，报告完整、本地预检通过、视觉核验确认误报时可用。格式为 `{"rejection_report":"<本work-dir原拒绝报告>","reason":"具体复核依据","visual_evidence":["page.png"]}`；绑定 deck/page/目标ID/XML哈希，写入意图消耗后不能重用。参数格式以 `template_publish.py --help` 和已保存的本页拒绝回执为准。

文字容量、对比和源布局诊断用于最后看图：先做完整可审稿，再集中修孤字、截断或遮挡。默认 `needs_final_review` 不逐页暂停；严格模式可选择在风险页停下。

未收到可靠写入 ACK 的 update 会先自动回读一次；封面 ID 已存在但 data 为空、文字仍是旧值或元素结构不同，都不能判写入成功。响应 `recovery_flag` 指定下一步：已有 ACK 用 `--recover-readback`，未知写入用 `--recover-write`。通用 `--recover-write` 误用于 ACK barrier 时，也会进入同一严格 ACK 回读，并记录实际路由；仍不 add/update 或自动接受内容差异。恢复使用原 pending 保存的 XML 与哈希；add 身份未知时先回读取得真实 ID，再传 `--slide-id` 核对该页，不能按页号猜测。比较忽略 SML 命名空间写法、缩进、几何数值序列化与保持引用结构的服务端 ID 重映射；服务端未识别的结构改写保持未确认，不虚报成功。

## 共享指标显示值

这是模板指标工具说明。函数调用时，在 Python 中设置技能根目录，并把下方格式的本题数据读入 `metric_spec`：

```python
import sys
sys.path.insert(0, str(LARK_SLIDES_SKILL_DIR))
from scripts.template.template_metrics import build_metric_values

result = build_metric_values(metric_spec)
values = result["values"]
```

把已计算端点与来源口径一同保存，再生成正文、图旁结论和讲稿共用的显示字符串。图表仍用原数值数组；显示精度在最后处理。

```json
{"metrics":[{"id":"completion","label":"完成率","kind":"rate","unit":"%","scope":"完成次数/全部有效任务","period":{"before":"前期","after":"本期"},"scale":"fraction","before":{"numerator":72,"denominator":100},"after":{"numerator":81,"denominator":100}}],"literals":{"funding.status":"新增资金申请待批准"}}
```

`quantity`端点是数量；`rate`可用fraction（0.72）或percent（72），也可用分子/分母。label/unit/scope/period从本题资料落值，次数、货币和统计时段保持来源意义。literals保存需要重复的状态原句。

```bash
python3 "$LARK_SLIDES_SKILL_DIR/scripts/template/template_metrics.py" values \
  --input "$WORK_DIR/computed-metrics.json" --output "$WORK_DIR/values.json"
```

得到纯字符串映射与算术收据、源JSON快照：completion.before/after/absolute_change/relative_change/percentage_points/direction/summary。例如72%→81%生成9个百分点和12.5%相对变化。缺测显示“未测量”，基期0的相对变化显示“不可算”。显式图组的单位、口径和时段保存在收据；单位不同用分面，是否叠加还取决于组成关系。

作者XML可写{{completion.summary}}、{{completion.percentage_points}}、{{funding.status}}；ready配方设置apply_values:true，整稿设置values_file:"values.json"。它填原生标题、正文、表格与notes，保留属性、图片路径及图表/SVG内容。默认ready和migration保留原文。模板fill的new_text与notes使用相同变量；见[作者配方](tools.md#内容配方)。
