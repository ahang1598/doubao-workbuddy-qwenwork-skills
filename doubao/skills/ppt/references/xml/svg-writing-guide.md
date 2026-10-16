# SVG 写作指南 · 面向飞书幻灯片

数据图、示意图都先读本文。配色、密度与修饰由所选 `style/` 文档决定；本文给出可直接照写的调用方式，常用接口都列在下面，不需要先查 help。

**SVG 页不慢的三条规矩**（线上 1 小时的 deck 里，SVG 页平均比纯原生页慢 3–5 倍，多出来的时间几乎都花在这三处）：
1. **不读库源码、不自己试 API**：数据图只用 `chart_slide`（想看图加 `preview=`，不调 `make_*`）；示意图接口查第四节的表或 `drawing_help("名字")`。报错信息里的 `fix`/提示就是改法，按它改一次即可，不要 grep 源码、写 debug 脚本二分排查。
2. **按 `publish_slide` 返回的 `summary`/`fix` 改**（第六节）：not found 是 ID 写错，`text_color_contrast` 是线压字；不要因为写入失败改走手动 `+add-slide`。
3. **改动用 Edit**：不要为改几行整份 Write 重写 build 脚本。

## 一、先分流

| 内容 | 工具 | 产物 |
|---|---|---|
| 有数据的专业图（分布、误差、生存、森林、热图、桑基…） | 图表库 `chart_slide(slug, …)` | 半可编辑：文字原生、同色柱块可整体换色 |
| 标准关系树（鱼骨/金字塔/脑图/分类/KPI/五问/OSI/C4/故障树） | `make_relation_atomized(..., strict_no_embed=True)` | 全部原生 |
| 机制图、示意图、结构图、自定义流程、实验设计 | drawing 库 `Drawing` → `to_slide(...)` | 全部原生 |
| 简单文字、方框流程、表格 | 原生元素 | — |

不为使用复杂图种编造数据。**凡是有数值的图（频率、比例、生存率、HR、计数…）一律走图表库**：不要用 drawing 的 `rect_at` / `box_at` 或 shape 拼条形图、进度条、点图，也不要把图表渲染成 PNG/`<img>` 来规避 lint 或字体问题；`chart_slide` 已把文字映射为思源黑体，导出 pptx 字体一致。drawing 只画没有数值坐标的机制、结构与流程。**自检**：页面上只要出现“标签 + 按数值长短的条/点”，就应换成 `chart_slide('grouped_bar' / 'dumbbell' / 'forest', ...)`。

## 二、图表库：一行放进幻灯片

```python
import sys

sys.path.insert(
    0, "<skill 根目录>"
)  # SKILL.md 所在目录；脚本放在任务工作目录时必须先加，否则 No module named 'scripts'
from scripts.gen_svg_charts import chart_help, chart_slide
from scripts.svg_lib.atomize_svg_to_slide import publish_slide

print(chart_help())  # 完整阅读、不截断；选图表只是举例，全部入口都可选；再 chart_help('forest') 看参数与示例
fragment = chart_slide("forest", x=40, y=96, width=880, height=380, rows=rows, ci_level=95, palette="science_cell_eng")
# 两条件对比 + 来源报告的 CI / P / n 直接写进行字段（论文图的统计标识画在图里）
fragment = chart_slide(
    "dumbbell",
    40,
    110,
    560,
    330,
    series_labels=("对照", "处理"),
    x_title="缓解率 (%)",
    rows=[{"label": "试验 A", "before": 32, "after": 48, "after_lo": 44, "after_hi": 53, "p": "<0.001", "n": 412}, ...],
)
r = publish_slide(page_xml, fragment, presentation=deck_id)  # 合页 + 写入 + 截图，见第六节
```

- **数据图只走 `chart_slide`，不要自己调 `make_*`**（`make_*` 返回一个 SVG 字符串，不是元组）：图表是矢量的，`chart_slide(x, y, w, h)` 会按需放大画布再等比缩进你给的框，文字仍是原生；warning 里的 `already fitted … at N% scale (… nothing to fix)` 就是成功，并列出 100%/80%/70%/60% 各需多大的框——缩放 ≥70% 直接用，低于 70% 加大框或减少注释。想看一眼图加 `preview="p05.png"`，排版前想知道框够不够用 `chart_fit(slug, w, h, **同样的参数)`。不要循环调 `make_*` 试尺寸、不要删数据、不要把图表转成 PNG；`make_*` 报 "needs about WxH" / "canvas is too small" 是画布尺寸，改用 `chart_slide` 即可。
- 曲线（电压–容量、能垒、浓度–时间）也走图表库：`chart_slide('scatter', ..., points=[{"name": "P2 首圈充电", "points": pts, "curve": pts, "marker": "none"}], x_title=..., y_title=..., fit=None, show_ci=False)`；`pts` 为 `[{"x":..,"y":..}]`。前后/两组对比用 `dumbbell`（`rows=[{"label":..,"before":..,"after":..}]`）。
- `chart_slide` 按目标框尺寸出图（字号在框内 ≥10pt），保持 viewBox 比例居中放置；返回的片段里文字是原生文本框，同色柱/扇区/色块合并成一个原生形状（选中即可整体换色），线、点、渐变等留在局部 SVG。图表总是半可编辑，不提供整图 `<embed>` 选项。
- **一页里图表 + 文字栏 + 示意图**：页标题、正文、要点栏写在 `page_xml`（原生文本），图表和示意图各自是片段、各占一个框，一起交给 `publish_slide(page_xml, chart_frag, d.to_slide(...))`。不要把 `make_*` 的 SVG 塞进 `Drawing`（`svg_at` 会直接报错），也不要用 `d.text_at` 写整栏正文。
- 换色只改 `palette=`；改数据改 kwargs 重跑。用户改了原生数值文字不会移动图形，改数值请重跑。
- **matplotlib 的参数名直接可用**：`xlabel` / `ylabel`、`xlim` / `ylim` / `y_min` / `y_max`、`xscale='log'`、`colors=[...]`、`annotate=True`、`reference=` 会自动映射到各图表自己的参数；数据格式也接受最自然的写法（裸数字、`{'name', 'values'}`）。拼错时报错会给出正确的参数名。

| 要回答的问题 | 选择与数据条件 |
|---|---|
| 疗效、风险在试验/亚组间比较 | `forest`：已报告的点估计 + CI 即可（比值类 HR/OR）；有 n、事件数、P 就加 `n`/`events`/`p` 列，汇总行 `is_overall=True`，`favours=` 标方向 |
| 效应估计、回归系数、事件研究（可正可负） | `coef_plot`：各期/各研究的估计值 + CI，线性轴、零线与政策时点 |
| 两种条件的差距 | `dumbbell`：每行两个已报告值，有区间/P/n 就加 `before_lo/hi`、`after_lo/hi`、`p`、`n`；单臂结果 vs 历史对照用 `coef_plot` 行的 `benchmark` |
| 少量类别的单值概览 | `grouped_bar`（直角坐标条形，上面各行都不贴切时才用）：没有更贴切的问题时再用；数值相差一个数量级以上或有负值时改用 `coef_plot`、`dumbbell` 或线性条形 |
| 指标随时间、剂量、ε、温度、压力变化 | `kinetics` / `dose_response` / `scatter` 曲线，按真实间隔（类别名是数值时就是曲线，不是柱）；基线、目标、工况用 `reference_lines`；已有有效区间才用 `line_band` |
| 样本差异与分布 | 箱线/小提琴/云雨/山脊需要逐样本观测；配对比较保留个体 ID |
| 变化由哪些可加项组成 | `waterfall`：起点、终点与可加和的有符号增减项 |
| 数量如何流转 | `sankey`：来源—去向与守恒流量；只有一个来源分成 2–3 路时用 `grouped_bar(stack='percent')` 更直观；只有流程关系时画示意图 |
| 多维差异或关联 | 矩阵图需明确行列与量纲；散点/气泡需同一对象的成对数值 |
| 不确定性或专业曲线 | 误差带写明 SD/SEM/CI；`forest` 需估计值、区间与置信水平；ROC/PR、生存曲线需原始标签或已报告曲线 |

## 三、作图先建立关系

1. **连接落在真实位置**：`d.arrow(a, b)` 的 a/b **传节点对象**（`box_at`/`place`/`svg_at` 的返回值）或 `node.port(...)`，端点自动落在轮廓上、不穿过节点自己的文字；不要手写 `(x, y)` 坐标对去估端点——那正是“箭头穿字/压框”反复返工的来源。连线起止于对象轮廓或端口，不用外接框中心目测；膜蛋白放在膜轮廓上，跨膜过程画出经过的界面。
2. **同一套坐标**：连续数值的点、刻度、阈值共用一次映射（`CoordinateMap`），不按列表序号均分。
3. **线有含义**：激活用箭头、抑制用横杠、结合用圆点或无端点实线、间接/反馈用虚线；汇合、分支、反馈要有明确接收方。
4. **标签不压线**：标签靠近对应结构，必要时用引线；不让文字、箭头遮住关键细节。
5. **画到能看懂**：对象按第四节「精细度原则」画出辨识特征，优先 `parts` 部件，库里没有用 `svg_at`。方框（`box_at`）只用于信号节点和结论标签。同类对象同色同形，强调色只给关键步骤。
6. **标注贴着对象写**：名称、功能直接写在对象旁边（`callout` / `place_label` 带引线），不要用 ①②③ 编号再到底部图例里解释——读者得来回对照才能看懂。
7. **箭头直接用 `d.arrow`（或手写 SVG 里的 `<marker>`）**：转换时会把箭头头、抑制横杠展开成等价形状，虚线、弯曲、半透明都支持；不要为了“规避 marker”改用 `d.line` + 手绘三角形，那样端点不会贴在轮廓上、也不随对象移动。
8. **接触是允许的**：受体立在膜上、细胞贴着血管、色块与色块叠放，`publish_slide` 会自动豁免这些图形重叠（第六节）。不要为了躲 lint 把细节删掉、把对象拉远或改成抽象符号。

## 四、drawing 库（像 svgwrite 一样直接画）

```python
import sys

sys.path.insert(0, "<skill 根目录>")  # 同上，放在所有 from scripts... 之前
from scripts.svg_lib.svg_drawing import Drawing
from scripts.svg_lib.atomize_svg_to_slide import publish_slide

from scripts.svg_lib.svg_drawing import cell, receptor, cytokine

d = Drawing(900, 420)  # 画布坐标，左上为原点；at 均为中心
t = d.place(cell(95, kind="t_cell", fill="#EEF3FA", membrane="#3A5A8C"), at=(200, 220), key="t")  # 现成部件
pd1 = d.mount(receptor(kind="bar", color="#5B1061", height=34), on=t.contour_at(0.0, normal="outward"), inset=3)
# 库里没有的对象：直接写 SVG 节点（坐标随意，自动居中缩放到 size），连线照样落在它的外轮廓上
pdl1 = d.svg_at(
    (470, 220),
    '<path d="M-60 -48 C-20 -70 40 -64 62 -30 C80 0 64 46 20 60 C-24 72 -70 44 -72 4 C-74 -22 -70 -40 -60 -48 Z" '
    'fill="#F7ECE6" stroke="#A34450" stroke-width="2.2"/>'
    '<ellipse cx="6" cy="2" rx="26" ry="22" fill="#E6B9C4" stroke="#A34450"/><circle cx="12" cy="-4" r="7" fill="#A34450"/>',
    size=(170, 150),
    key="tumor",
)
d.place(cytokine(5, r=5, color="#E0A458"), at=(335, 120), key="ifn")
shp2 = d.box_at((200, 380), "SHP-2 去磷酸化", font_size=15, fill="#9B2D6F", text_fill="#FFFFFF", shape="pill")
out = d.box_at((740, 110), "T 细胞失能", font_size=16, stroke="#2A1A4A")
d.arrow(pd1, pdl1, head="dot", stroke="#5B1061")  # 结合：端点自动落在两侧轮廓上
d.arrow(pd1, shp2, stroke="#5B1061", curve=-30, label="招募")  # 激活；label= 边标签自动放在线外空白处、随线移动
d.arrow(shp2, t, head="inhibit", stroke="#C0392B", curve=-40)  # 抑制：横杠端点 = 抑制 TCR 信号
d.arrow(pdl1, out, dashed=True, stroke="#7A7A7A", route="orthogonal")
d.arrow(
    out, t, route="loop", side="top", dashed=True, label="负反馈"
)  # 反馈回路：绕到两端之间所有对象上方的 U 形三段线，不要手算坐标
d.text_at((450, 24), "PD-1 / PD-L1 抑制 T 细胞信号", font_size=22, font_weight="bold", fill="#2A1A4A")
r = publish_slide(page_xml, d.to_slide(x=30, y=90, width=900), presentation=deck_id)
```

| 接口 | 说明 |
|---|---|
| `rect_at(at, w, h, rx=, **style)` / `ellipse_at(at, rx, ry, **style)` | 以 `at` 为中心放形状；返回 Node |
| svgwrite 写法：`d.rect(insert=, size=)` / `d.circle(center=, r=)` / `d.ellipse(center=, r=(rx, ry))` / `d.text(s, insert=)` / `d.polyline(pts)` / `d.polygon(pts)` / `d.path(d=)` / `d.tostring()` / `d.saveas()` | 和 svgwrite 同名同义，返回 Node，可直接传给 `arrow` / `callout` |
| `box_at(at, text, font_size=, fill=, stroke=, text_fill=, shape='rect'/'pill'/'ellipse', max_width=)` | 按文字自适应的节点框，带 top/bottom/left/right 端口 |
| `text_at(at, text, font_size=, anchor='center', line_height=1.35, **style)` | 文字；多行用 `\n`，`line_height` 小于 3 时按字号倍数 |
| `place(part, at=, anchor='center', svg=, size=)` | 放部件（cell/atom/block/lattice…）或 Geometry，**把它的外接框中心移到 `at`**；传 `svg=` 则保留部件位置和尺寸、外形换成手写 SVG |
| `d.add(key, geometry)` | 按画布坐标原样放入（`membrane(path)`、`circular_arc(center, r, start, sweep)`、`ribbon`、`repeat_along_path` 这类用画布坐标建的几何用它，不要用 `place`） |
| `svg_at(at, svg, size=, ports=)` | 直接把一段手写 SVG 当作节点（库里没有的对象就这样画）；第一个形状是外轮廓，连线/标签/mount 都落在上面 |
| `path_at(d, **style)` | 任意 SVG 路径（画布坐标），可写 A 弧、C 曲线 |
| `arrow(a, b, head='arrow'/'inhibit'/'dot'/'diamond'/None, tail=, curve=, route='straight'/'orthogonal'/'elbow'/'loop', side=, dashed=, label=, label_side=, stroke=, stroke_width=)` | 连线；a/b 可传 Node（自动落轮廓）、`node.port('right')`、`node.contour_at(t)` 或坐标；`label=` 边标签，`route='loop', side='bottom'` 反馈回路 |
| `line(a, b, **同上)` | 无端点连线（结合、引导线） |
| `node.contour_at(t, normal='outward')` / `node.contour_toward(target)` | 轮廓上的点：膜上第 t 处、朝向某对象的交点 |
| `node.anchor('top_left'…)` / `node.port('right')` | 外接框位置 / 真实接口；`rect_at`/`ellipse_at` 没有声明端口时 `port('left')` 等同外接框边中点 |
| `place_label(key, label(text, font_size=…), target)` / `label_connector(key, link_key, label(...))` | 自动选不遮挡的位置；全部画完后调用 `d.relayout_labels()` |
| `row` / `column` / `grid` / `ring` / `bipartite_order` / `spread_ports` / `tree_layout` | 排布：行列网格、环形循环、两列配对减交叉、一边多线错开、树 |
| `d.to_slide(x=, y=, width=)` | 写 SVG + 映射 + 拆成原生元素，返回片段（字符串）交给 `publish_slide`；片段不要自己字符串拼进 page_xml |
| `d.check()` / `d.review()` / `d.summary()` / `d.preview(path)` | `check()` 返回问题 **list**（空列表即通过，不是元组）；`review()` 返回细节审查 list（空 = 主体已有细节）；`summary()` 返回文字摘要；`preview()` 渲染一张 PNG（review 有提示时才用，见下文） |

**约定**：`chart_slide` / `to_slide` 返回片段字符串，`chart_fit` / `publish_slide` 返回 dict。位置由参数名决定、全库一致：`at=` / `center=` 是**中心点**，`insert=` 按 svgwrite 含义（矩形左上角、文字基线起点），任何方法都可以用这两种写法（左对齐文字也可写 `anchor="start"`）；`path_at`、`membrane`、`ribbon`、`repeat_along_path` 直接用画布坐标。样式参数就是 SVG 属性的下划线写法：`fill`、`stroke`、`stroke_width`、`opacity`、`font_weight`。

**手写 SVG 节点与精修**：创建时就能用自己写的 SVG——`svg_at(at, svg, size=)` 或 `place(部件, at=, svg=)`；已建好的节点也可 `node.replace_svg(svg, ports={...})` 换外形，或 `node.svg_source()` 读出现有外形改完再 `replace_svg(src, fit="own")`。连线、标签、挂载的受体都跟着新外形走；精修写在脚本里，重跑不会丢。

**看不见画面时读排版摘要**：连线实际端点与长度、自适应框尺寸、自动标签位置和画布→页面缩放都是计算出来的；`d.summary(width=页面宽)` 按页面实际尺寸列出每个对象的位置尺寸、每条连线的实际长度与线宽、页面字号，`to_slide` 发现线过细、字过小、连线过短、对象过挤或留白过大时会自动打印提示，按提示改画布或参数即可，无需截图。

**审查有提示才预览精修**：画完先调 `d.check()`（`to_slide` 也会自动检查并给出警告），它报告文字互压、连线穿过非端点文字、斜线外接框压字、超出画布，以及文字半压在色块外接框上（服务端 lint 按外接框判定），按 hint 改掉；图形之间的叠放不用管。再看 `d.review()`（`to_slide` 自动打印「细节审查」）：它只看结构，点名连线最多、面积最大的主体里只画成方框/单个图形/纯文字的节点、手画的膜和字符箭头。**review 为空就直接写入，不用预览**；有提示时先判断节点是不是实体（是就换部件或 `svg_at` 外形，只是步骤标签就保留），再 `d.preview("pNN.png")` 看一次、精修一轮后写入，不做第二次预览。不要自己用 qlmanage/rsvg 渲染，不要跑本地 `xml_lint.py` 校准，数据图不做预览。整页截图统一放到 Step 8。

**通用部件**（可选零件，不是边界——贴合就用，不贴合就用 `path_at` / `svg_at` 自己画，不要为了套部件改变内容）：

| 学科 | 部件 | 典型用途 |
|---|---|---|
| 生命科学 | `cell`（kind=generic/t_cell/tumor/bacterium/macrophage/dendritic/neutrophil/epithelial/plasma/plant/stellate/myofibroblast；state="lysing" 裂解）、`membrane`、`receptor`（antibody/car/gpcr/channel/bar）、`transporter`（channel/pump/antiporter/symporter/abc/aquaporin，`d.place(..., anchor="tail")` 立在膜线上）、`nucleus`、`mitochondrion`、`vessel`、`virus`（enveloped/phage/icosahedral）、`neuron`、`dna` / `duplex` / `nucleic_strand`、`protein_complex`、`cytokine`；器官 `heart`、`nephron`、`bbb_unit`（血脑屏障）、`root_section`（根横切）；受体–配体接触用 `cell_interface`，细菌包膜 `cell_envelope`，生物膜（含 O₂ 梯度）`biofilm_section`；肝窦（窗孔内皮、Disse 间隙、星状/Kupffer 细胞、纤维化）`liver_sinusoid`；`brain(nodes=, edges=)` 叠加脑网络连接；膜能量学：`membrane_complex`（呼吸链/光系统复合物 + 辅因子 + H⁺ 泵）、`atp_synthase`（F₀F₁ 侧视）、`transport_chain`（整条电子传递链/类囊体链，自动画电子路径与 H⁺）、`ion_marker`（按文字定半径的 H⁺ 小圆，别手画圆+字） | 细胞与膜蛋白、免疫与感染、上皮转运、器官生理、氧化磷酸化/光合作用 |
| 通路与范式 | `signaling_cascade`（配体→膜受体→磷酸化级联→核内靶基因；负反馈 T 形抑制、旁路分支、药物靶点自动布局，**通路图不要用方框+箭头手拼**）、`trial_sequence`（实验范式：斜叠屏幕 + 时长 + 时间轴）、`badge`（编号圆圈，一个对象） | 信号转导机制、药物作用点、认知/心理物理任务流程、图中编号 |
| 化学与材料 | `atom`、`molecule`（也接受 "CO2"/"H2O"/"CH4"/"NH3"/"carbamate"/"benzene" 等预设）、`lattice`、`particle`、`porous_framework`（MOF/COF/沸石：节点 + 配体 + 孔道客体）、`porous_electrode`（两相烧结颗粒网络 + 孔隙 + 三相界面，可叠加积碳纤维/硫吸附/团聚/裂纹）、`microplastic`、`layer_stack`、`interface_section` | 分子与吸附、晶体与缺陷、多孔材料、颗粒/核壳、器件叠层、界面失效 |
| 晶体缺陷 | `close_packed`（ABC/ABAB 堆垛侧视，自动高亮层错/HCP 薄层）、`twin_lattice`（孪晶界两侧镜像）、`edge_dislocation`（多余半原子面 + ⊥ + 滑移面 + b）、`polycrystal`（Voronoi 晶粒 + 退火孪晶 + 晶内 ⊥）、`dislocation_symbol` | 层错、孪生、位错与滑移、晶界与多晶组织 |
| 工程、物理、CS | `block`、`nn_layer` + `dense_links`、`tensor_block`、`encoder_decoder`（U-Net/编解码，可换 Transformer 瓶颈）、`transformer_block`、`patch_embed`（ViT 分块→token）、`device`（phone/laptop/server/database/cloud/hospital/edge/camera/gpu）、`image_grid`（重建/去噪缩略图条）、`vector_packet`（参数/梯度向量，可加密）、`wave`、`lens` / `laser_beam`、`circuit_symbol`、`spring` / `magnet` | 系统与协议架构、网络结构、信号、光路、电路 |
| 电磁学与电路 | `coil`（solenoid 立体螺线管，可 core="iron"、current 电流箭头 + 右手定则 N/S 端口、field_lines 管内磁感线；loop 单匝；toroid）、`field_marks`（⊗/⊙ 匀强磁场区域，keepout 留空）、`rails_rod`（导轨 + 导体棒 + v + 负载 + 感应电流 I，可铺磁场）、`circuit_loop`（元件按边放在矩形上自动布线，RL/RC 回路不手算坐标）、`circuit_symbol`（另有 galvanometer/ammeter/voltmeter/rheostat/inductor_core）、`magnet`（感应图务必 field_lines=True） | 电磁感应、楞次定律、RL/RC 暂态、电表接线 |
| 地学 / 天文 / 生态 / 通用 | `globe`、`star` / `planet` / `transit_geometry`（凌星透射几何）、`water_column_section`（湖/海/河剖面：水层、跃层、沉积物）、`soil_aggregate`（土壤团聚体/沉积物孔隙：颗粒、水膜、气/水孔、缺氧核心、菌落）、`organism`（fish/daphnia/copepod/algae/bivalve/worm/plant/mouse/human）；`legend_row` | 地球球面、恒星与行星、水环境迁移与食物网、实验动物；图例 |

参数一次查一个：`drawing_help("cell")`（可一次传多个名字）；`drawing_help("parts")` 只给一页目录。受体、探针立在轮廓上用 `d.mount(part, on=node.contour_at(t, normal="outward"))`。部件默认 `style="rich"`（渐变与纹理留在局部 SVG，轮廓、核、受体和文字仍是原生、可改色），**学术示意图一律保持 rich**；`style="flat"` 只在用户明确要求"全部可编辑/纯色"时用。自己画的对象用 `drawing_help("finish")` 补细节：`bilayer(path)` 沿任意路径画磷脂双层，`sphere_shading` / `soft_shading` 加明暗，`circle_union` 合并重叠圆，`shade(color, t)` 推导同色系深浅。

**页面照常手写 XML，Python 只生成图形片段**：标题、正文、要点、来源、页码等页面元素按 SKILL.md 的方式直接手写成 `<slide>` XML（不画图的页照常 `+add-slide`，不要为它写 Python）；只有数据图和示意图用 Python 生成片段，再和这页手写的 XML 一起交给 `publish_slide` 合页写入。配色用 Step 4 设计系统里定下的色值，手写 XML 与 `palette=` / 部件颜色参数用同一组；多页复用同一个部件时，可以在工作目录放一个只含色值和部件函数的小文件 import，不要把页面骨架、写入函数也封装进去。

```python
# build_p05.py：一张示意图页
import sys

sys.path.insert(0, "<skill 根目录>")  # 必须在任何 from scripts… 之前
from scripts.svg_lib.svg_drawing import Drawing, cell, receptor
from scripts.svg_lib.atomize_svg_to_slide import publish_slide

page_xml = """<slide xmlns="https://www.larkoffice.com/sml/2.0"><style><fill><fillColor color="rgb(250,250,252)"/></fill></style><data>
  <shape type="text" topLeftX="40" topLeftY="28" width="880" height="44"><content fontSize="26" color="rgb(42,26,74)" bold="true"><p>结论式标题</p></content></shape>
  <shape type="text" topLeftX="40" topLeftY="506" width="880" height="18"><content fontSize="10" color="rgb(107,107,107)"><p>来源：…</p></content></shape>
</data></slide>"""  # 手写的页面部分：标题、正文、来源

d = Drawing(900, 400)
# …画示意图…
if __name__ == "__main__":  # 被 import 时不写页
    r = publish_slide(page_xml, d.to_slide(x=30, y=90, width=900), presentation="<xml_presentation_id>", page=5)
    print(r["ok"], r["slide_id"], "\n".join(r["summary"]))
```

`native_bullets` / `native_table(best=…)` / `page_frame` 等原生元素助手可选用（签名 `print(slide_help())`），但不是必须；页面仍以手写 XML 为主。

**精细度原则**：
1. 要么不画，要画就做到教科书插图的辨识度——细胞要有双层膜、核膜核仁和细胞器，抗体要分重链/轻链，器件要分层标注等等；一条线、一个圆就代表一个机制属于不合格。画不出辨识特征的对象改用文字框或图片，不要用椭圆、方块当占位。
2. 先用部件或 `svg_at` 搭出整体，再对研究主体精修：`replace_svg` 换更贴切的外形、`drawing_help("finish")` 补膜层/明暗/纹理、`callout` 标出关键结构；预制部件只是起点，主体对象的细节要比配角多一层。
3. 关系要画成真实的空间关系：结合/接触就让两者贴合，吸附/负载就把客体放进孔道或表面，分子按真实键角等等；盾牌、叉号、问号这类简单符号不能代替机制本身。主体之间都要有箭头、接触或包含关系，`d.review()` 会点名孤立的主体。

**结构细节配方**（让示意图有形态，不只是方框）：

```python
from scripts.svg_lib.svg_drawing import ellipse, repeat_along_path, ribbon

mem = "M 60 260 C 260 200 640 200 840 260"  # 膜中线
d.add("bilayer", ribbon(mem, 14, fill="#9A88C9", fill_opacity=0.25))  # 双层膜底带
for side in (-7, 7):  # 磷脂头部两排
    d.add(f"heads{side + 7}", repeat_along_path(ellipse(5, fill="#9A88C9"), mem, spacing=14, normal_offset=side))
d.path_at(
    "M 420 140 C 400 200 400 300 420 360", stroke="#5B1061", stroke_width=10, fill="none", stroke_linecap="round"
)  # 跨膜螺旋/通道
```

用方框加文字代替细胞、膜、分子、晶格、器件这些对象，就是不合格的示意图；题目里的具体结构（细菌包膜、电池、突触…）用上表的通用部件组合出来，组合写法见 `scripts/svg_lib/drawing_examples/` 的模板。

其余可组合的几何（截面放大 `zoom`、剖切 `cutaway`、厚度 `extrude`、函数曲线 `sample_function`、蛋白结合位点等）用 `drawing_help("任务名")` 查，例如 `drawing_help("沿曲线排列")`。

## 五、手写 SVG 的转换边界

drawing 库之外手写的 SVG，用 `atomize_svg_to_slide` 转换（见第六节）。

| 输入 | 转换结果 |
|---|---|
| rect / circle / ellipse / line / 直线 path | 原生形状或线；旋转、镜像可保留 |
| 曲线或复合 path | custom shape；Q/T/A 转为等价 C，可直接写 A 弧 |
| text / tspan | 原生文字或富文本，含显式多行、字距、旋转 |
| g / use / symbol / transform | 展开为独立对象 |
| 直线虚线 | 按真实长度展开为 custom 路径；曲线、圆形、圆角矩形的虚线保留为局部 SVG |
| 滤镜、蒙版、复杂裁切、径向渐变 | 局部 SVG embed，可整体选中拖动，内部不可细改 |

- 颜色写 `#RRGGBB`、半透明用 `*-opacity`，viewBox 零原点且与目标区域等比、字号按缩放比例放大——规则见 `xml-schema-quick-ref.md` 的 embed 一节。`text.y` 是基线；转换器把过小文字抬到 10pt，下限不能修复拥挤。
- 残缺路径、缺失引用、非法颜色或数值会直接报错：**修正源数据，不要删除元素绕过**。
- 图片走 Slides 图片层，不用 `<image>`。

## 六、合页与写入：publish_slide

```python
from scripts.svg_lib.atomize_svg_to_slide import publish_slide

r = publish_slide(page_xml, *fragments, presentation=deck_id, page=3)  # 第 3 页：首次新增，重跑原地更新，页序按页码
r = publish_slide(page_xml, *fragments, presentation=deck_id, slide_id=sid)  # 修改后整页覆盖原页，不会重复加页
```

- `page_xml` 是本页手写部分（标题、正文、来源等原生元素）；`fragments` 是 `chart_slide` / `d.to_slide` / `atomize_svg_to_slide` 的返回值。函数先合页，再开启服务端 lint 写入；写入前会按 lint 同款估算加高放不下的文字框、把 `<border width>` 取整（`r["warnings"]` 列出会越界的框）。
- **只有含图的页才用 `publish_slide`**：每张图页一个 `build_pNN.py`，传 `page=N` 让重跑同一脚本原地更新、补写的页自动插到正确位置；不画图的页照常手写 XML 用 `+add-slide`，不要为它写 Python。
- 若 lint 只报**图表/示意图转换内部的形状重叠**（受体贴膜、扇区外接框、细胞贴血管等几何误报），它会自动改用 `--no-lint` 重新写入，`r["no_lint"]=True`、`r["ignored"]` 为豁免条数；**不要自己手动加 `--no-lint`**。
- 文字压文字、手写元素的问题、其他规则（对比度、越界、溢出等）会写入失败：先读 `r["summary"]`（按问题类型和来源分组的一行一条），再按需看 `r["errors"]` 的明细——每条含 `objects`（文字内容、`xml_box` 页面坐标 [x,y,w,h]、字号、`source`：`page_xml` 表示手写元素，`fragment[k]` 表示第 k 个传入的片段）、`measurement`（重叠宽高）、`fragments`（该片段在页面上的外框）和 `fix`（具体改法）。手写元素按坐标改；`fragment[k]` 的问题改对应 `chart_slide` / `to_slide` 的参数或框，不要去挪生成的单个元素。改完用同一调用（带 `slide_id=` 时为覆盖）重试。
- **确认是误报就豁免，不要反复改**：每条 `errors` 都带 `key`。看 `r["preview"]` 确认某条是误报（视觉上没有真遮挡/截断/低对比），或同一条已按 `fix` 改过一次仍报时，同一调用加 `waive=["<key>", ...]`（只填确认误报的那几条），函数会跳过 lint 强行写入并自动截图（`r["waived"]` 列出被跳过的条目），Read `r["screenshot"]` 核对即可。仍有未豁免的条目时照常被拦。服务端不记豁免，这些条目在 Step 8 回读后用 `lint_inspect.py` 查看时还会原样出现，不要回头再改。
- 返回 `r["ok"]`、`r["slide_id"]`、`r["page_xml"]`、`r["screenshot"]`（写入后的页面截图，限流自动重试）、`r["preview"]`（失败时按 XML 渲染的预览图，便于看清哪里压了）。截图只在需要时 Read，不必每页都看。
- **常见报错直接按 `fix` 改，不要另做排查**：
  - `upload_failed` + not found：presentation / slide_id 写错了（常见是 DECK 常量手敲错一个字母），不是缓存、TTY 或网络问题。
  - `text_color_contrast` 出现在 `fragment[k]` 上：几乎都是连线或色块（含斜线的外接框）压在标签上，`covered_by` 会列出是哪条；把线改成 `route="orthogonal"` 或挪开标签，不要改文字颜色。`d.check()` 的 `line_box_over_text` 就是提前报这个。其余情况看 `contrast`（文字、字色、实际底色与下方图层、复算比值）：改一次深字/浅底，仍报或复算已达标就 waive，不要追查 lint 怎么算的。
- **修改用 Edit 改局部**：被拦后按 `fix` 改一两行再跑同一脚本，不要整份 Write 重写 build 脚本——一次重写 4–8k token，要 60–130 秒。复杂示意图先写主体跑通，再分几次 Edit 补细节。
- **写入一律直接传 `presentation=`**，不要合页后再自己调 `+add-slide`，也不要因为一次写入失败就改走手动 `compose_slide` + `+add-slide`——那样自动豁免、报错定位都不会生效，会多出几十条图内重叠报错。只有整份一次性 `+create --slides` 时才用不传 `presentation` 的纯合页（可加 `save_as=`）。
- 手写 SVG：先 `set_mapping(svg_w=, svg_h=, slide_x0=, slide_y0=, slide_w=, slide_h=)`，再把 `atomize_svg_to_slide(svg_path)` 作为 fragment 传入。标题、结论与来源用原生元素，图内不重复页面已有文字。

## 七、lint

以服务端 lint 为准，本地 `xml_lint.py` 可能落后，它对部件之间报的 `bbox_overlap` 不作为阻塞依据。收到 `4000153` 先完整读报告，修复真实的重叠、越界、溢出。`--no-lint` 只按 [`validation-xml.md`](../workflow/validation-xml.md#修复与单页例外) 的单页例外使用。可编辑 SVG 常见误报：透明外框被当成实心、有意的接触与叠放（受体嵌在膜上、文字压在柱上）、沿边线的浮点误差、字宽估算偏差。确认是误报时保留原几何，不为清零告警把部件拉开或删字。
