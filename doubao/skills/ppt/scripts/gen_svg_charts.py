#!/usr/bin/env python3
"""One-call SVG chart generation for slides and scientific figures."""

import argparse
import json

# Ensure this file's directory (scripts/) is on sys.path so `svg_lib.*` resolves
# regardless of the caller's CWD or import path (e.g. `python3 -c "from scripts.gen_svg_charts import ..."`).
import os as _os
import sys as _sys

_HERE = _os.path.dirname(_os.path.abspath(__file__))
if _HERE not in _sys.path:
    _sys.path.insert(0, _HERE)

# helpers moved to svg_lib/_common.py; re-export for legacy call sites
from svg_lib._common import *  # noqa: F403

# Re-export make_* from svg_lib.charts (they live there now)
from svg_lib.charts.band_structure import make_band_structure
from svg_lib.charts.bar_academic import make_bar_academic
from svg_lib.charts.boxplot import make_boxplot
from svg_lib.charts.bubble import make_bubble
from svg_lib.charts.calheat import make_calheat
from svg_lib.charts.candle import make_candle
from svg_lib.charts.clustered_heatmap import make_clustered_heatmap
from svg_lib.charts.composite import make_composite
from svg_lib.charts.contour import make_contour
from svg_lib.charts.depth_profile import make_depth_profile
from svg_lib.charts.dose_response import make_dose_response
from svg_lib.charts.dot_plot_scrna import make_dot_matrix, make_dot_plot_scrna
from svg_lib.charts.coef_plot import make_coef_plot
from svg_lib.charts.dumbbell import make_dumbbell
from svg_lib.charts.event_timeline import make_event_timeline
from svg_lib.charts.forest import make_forest
from svg_lib.charts.funnel import make_funnel_classic
from svg_lib.charts.gantt import make_gantt
from svg_lib.charts.grouped_bar import make_grouped_bar
from svg_lib.charts.histogram import make_histogram
from svg_lib.charts.hr_diagram import make_hr_diagram
from svg_lib.charts.kinetics import make_kinetics
from svg_lib.charts.km_survival import make_km_survival
from svg_lib.charts.line_band import make_line_band
from svg_lib.charts.marimekko import make_marimekko
from svg_lib.charts.matrix_heat import make_matrix_heat
from svg_lib.charts.nested_donut import make_nested_donut
from svg_lib.charts.network import make_network
from svg_lib.charts.nyquist_bode import make_nyquist_bode
from svg_lib.charts.pairs import make_pairs
from svg_lib.charts.parallel_coords import make_parallel_coords
from svg_lib.charts.percent_grid import make_percent_grid
from svg_lib.charts.phase_diagram import make_phase_diagram
from svg_lib.charts.phylogeny import make_phylogeny
from svg_lib.charts.potential_energy_surface import make_potential_energy_surface
from svg_lib.charts.pseudotime import make_pseudotime
from svg_lib.charts.pyramid import make_population_pyramid
from svg_lib.charts.quadrant import make_quadrant_2x2
from svg_lib.charts.radar import make_radar
from svg_lib.charts.raincloud import make_raincloud
from svg_lib.charts.ridge import make_ridge
from svg_lib.charts.roc_pr import make_roc_pr
from svg_lib.charts.sankey import make_sankey
from svg_lib.charts.scatter_fit import make_scatter, make_scatter_fit
from svg_lib.charts.seismic_waveform import make_seismic_waveform
from svg_lib.charts.spectrum import make_spectrum
from svg_lib.charts.stress_strain import make_stress_strain
from svg_lib.charts.swimmer import make_swimmer
from svg_lib.charts.ternary import make_ternary
from svg_lib.charts.time_latitude import make_time_latitude
from svg_lib.charts.titration import make_titration
from svg_lib.charts.umap_cluster import make_umap_cluster
from svg_lib.charts.upset import make_upset
from svg_lib.charts.vector_field import make_vector_field
from svg_lib.charts.violin import make_violin
from svg_lib.charts.volcano import make_volcano
from svg_lib.charts.waterfall import make_waterfall

from svg_lib._color_compat import office_safe_svg as _office_safe_svg


def _office_safe(make):
    import functools

    if getattr(make, "_chart_lib_marked", False):
        return make

    @functools.wraps(make)
    def wrapper(*args, **kwargs):
        svg = _office_safe_svg(make(*args, **kwargs))
        # Marks chart-library output so compose_slide can make a hand-wrapped <embed> semi-editable.
        return svg.replace("<svg ", '<svg data-chart-lib="1" ', 1) if "data-chart-lib=" not in svg[:400] else svg

    return wrapper


# Every public generator returns hex + opacity paints; PowerPoint drops rgba() alpha.
for _name in [n for n, v in list(globals().items()) if n.startswith("make_") and callable(v)]:
    globals()[_name] = _office_safe(globals()[_name])
del _name

__all__ = [
    "chart_catalog",
    "chart_fit",
    "chart_help",
    "chart_slide",
    "make_band_structure",
    "make_bar_academic",
    "make_boxplot",
    "make_bubble",
    "make_calheat",
    "make_candle",
    "make_clustered_heatmap",
    "make_composite",
    "make_contour",
    "make_depth_profile",
    "make_dose_response",
    "make_dot_matrix",
    "make_dot_plot_scrna",
    "make_coef_plot",
    "make_dumbbell",
    "make_event_timeline",
    "make_forest",
    "make_funnel_classic",
    "make_gantt",
    "make_grouped_bar",
    "make_histogram",
    "make_hr_diagram",
    "make_kinetics",
    "make_km_survival",
    "make_line_band",
    "make_marimekko",
    "make_matrix_heat",
    "make_nested_donut",
    "make_network",
    "make_nyquist_bode",
    "make_pairs",
    "make_parallel_coords",
    "make_percent_grid",
    "make_phase_diagram",
    "make_phylogeny",
    "make_population_pyramid",
    "make_potential_energy_surface",
    "make_pseudotime",
    "make_quadrant_2x2",
    "make_radar",
    "make_raincloud",
    "make_ridge",
    "make_roc_pr",
    "make_sankey",
    "make_scatter",
    "make_scatter_fit",
    "make_seismic_waveform",
    "make_spectrum",
    "make_stress_strain",
    "make_swimmer",
    "make_ternary",
    "make_time_latitude",
    "make_titration",
    "make_umap_cluster",
    "make_upset",
    "make_vector_field",
    "make_violin",
    "make_volcano",
    "make_waterfall",
]

_CHART_DESCRIPTIONS = {
    "band_structure": [
        "能带结构",
        "固体物理：高对称点 k 路径（Γ→X→M→...）上的能带 E(k) + Fermi 水平线 + 可选右侧 DOS 子图。",
    ],
    "boxplot": ["箱线图", "多组分位数摘要（Q1/中位/Q3 + 须 + 离群点）：跨年、跨类别的离散度比较。"],
    "bubble": [
        "气泡图",
        "三/四维散点：X、Y、气泡大小（第三维）+ 可选 color（第四维）；市场份额、GDP vs 预期寿命 vs 人口。",
    ],
    "calheat": ["日历热力", "52×7=364 天日度指标热度：一眼看某周/某月的密度、季节性；GitHub 风 + 学术印刷版式。"],
    "candle": ["K 线蜡烛图", "时序 OHLC：金融行情、月度波动区间；上涨白心描边、下跌主色实心。"],
    "clustered_heatmap": [
        "聚类热图",
        "N 行基因 × M 列样本/条件：带左侧行 dendrogram + 上侧列 dendrogram + 顶部 column annotation 色带的层次聚类热图。",
    ],
    "composite": [
        "组合图",
        "Shared facets, aligned tracks, line/bar, matrix overlays and heterogeneous panels in one call.",
    ],
    "contour": ["等值线", "标量场 z=f(x,y) 可视化：地形、损失面、浓度场、风速；填充色阶 + 等值线叠加。"],
    "depth_profile": [
        "深度剖面",
        "海洋/大气/钻孔：值 vs 深度的**竖版**剖面图，深度 Y 轴反向（0 在顶、深处在底），多站位 overlay + CI 带。",
    ],
    "dose_response": [
        "剂量响应",
        "药理 / 毒理：实际剂量与响应的 4PL 拟合、EC50 和 Hill；仅显示显式提供的有效 CI，不从残差拼造区间。",
    ],
    "dot_matrix": ["通用点矩阵", "矩阵的面积和颜色分别编码独立数值，支持真实图例、缺失值和注释轨道。"],
    "dot_plot_scrna": [
        "scRNA dot plot",
        "单细胞转录组：genes × clusters 矩阵，点大小 = 表达细胞比例、点颜色 = 平均表达。顶部可带 cluster annotation 色带。",
    ],
    "coef_plot": [
        "系数图 / 事件研究图",
        "线性轴上的点估计与置信区间（可正可负）：事件研究的领先滞后期系数，或多研究/多模型的效应对比。",
    ],
    "dumbbell": ["哑铃图", "每行两个明确命名的观测及连接，比较前后变化。"],
    "event_timeline": ["事件时间轴", "真实时间与事件的横向、纵向或环形布局。"],
    "forest": [
        "森林图",
        "亚组分析 / meta-analysis：点估计与已报告区间；置信水平须由来源提供，支持逐行混合水平；中线为参考值。",
    ],
    "funnel_classic": [
        "经典梯形漏斗",
        '分层筛选叙事——业务场景的"全体 → 精选组合"（投资标的、招聘、销售），数据量小（3-8 层）、每层需要一句解读时用本图。',
    ],
    "gantt": ["甘特图", "项目管理/教育课程排期/产品迭代计划；关键路径主色高亮、里程碑菱形。"],
    "grouped_bar": [
        "自适应分组比较",
        "同一类别×系列接口按数据自动生成直角坐标条形（少量汇总值；≤8 类或长标签横向）、数值热力、箱线/雨云、分组区间或 Marimekko。保留真实样本与统计信息。负值报错并提示使用原生图表。",
    ],
    "histogram": [
        "直方图",
        "单变量分布形状 + KDE 覆盖线 + mean/median 竖线 + 右侧统计盒；比 ridge 更关注单一样本本身。",
    ],
    "hr_diagram": [
        "赫罗图",
        "恒星演化：色指数（B-V 或温度，**X 轴反向**）vs 绝对星等（**Y 轴反向**）散点；主序带 + 可选演化轨迹 + 太阳参考点。",
    ],
    "kinetics": [
        "反应动力学",
        "时间与响应的多条件曲线；默认只连接给定点，一级/线性拟合须逐曲线显式选择 fit_type，value_label/value_unit 标明测量量。",
    ],
    "km_survival": [
        "KM 生存曲线",
        "临床生存分析：Kaplan-Meier 阶梯曲线 + 删失刻度 + Greenwood CI 阴影 + 底部 at-risk 表 + log-rank p/HR 注释。",
    ],
    "line_band": ["带置信带时序", "多序列折线 + 95% CI 阴影带：A/B 实验、队列趋势、模型 vs baseline 性能曲线。"],
    "marimekko": ["马赛克图", "双向占比（业务组合矩阵）：列宽 = 市场规模，列内高度 = 各方份额。"],
    "matrix_heat": [
        "矩阵热图",
        "Rectangular numeric or mixed-column matrices; -1 is data, None/NaN is missing; masks, annotations and independent upper/lower scales.",
    ],
    "nested_donut": ["嵌套占比环", "父子类别占比与多层环；数值必须来自真实组成，非通用径向数轴。"],
    "network": [
        "科研网络图",
        "Nodes and edges with force, radial, bipartite or supplied layouts; quantitative encodings and tracks.",
    ],
    "nyquist_bode": [
        "Nyquist/Bode",
        "电化学阻抗谱 (EIS) 两种常用视角：Nyquist = Z'-(-Z'') 复平面散点；Bode = 频率扫 |Z| 和相位（上下双面板）。",
    ],
    "pairs": ["散点矩阵", "Pairwise observations, correlations and diagonal distributions with shared group identity."],
    "parallel_coords": [
        "平行坐标",
        "高维（4-8 维）样本可视化：每条折线串起一行样本在各轴上的值；按 group 分色 + 四分位带做背景。",
    ],
    "percent_grid": [
        "百人网格",
        '调研/问卷（"76% 支持"）、"多少人选了 X" 叙事；10×10 网格 + breakdown 累计条 + POS/NEU/NEG 大数字 + 侧栏图例。',
    ],
    "phase_diagram": ["相图", "P-T / T-x 相图：若干填充相区（固/液/气/固溶体）+ 相界线 + 临界点/三相点/共晶点标注。"],
    "phylogeny": [
        "系统发育树",
        "Radial Newick or nested trees with true cumulative branch lengths and aligned leaf tracks.",
    ],
    "population_pyramid": [
        "人口金字塔",
        '"人口结构"、"两组人群对比"（男女、公私立、城乡、党团、前测后测）；顶部 KPI 卡片 + 中轴类目名 + 左右柱条 + median 卡片 + peak cohort 空心圆 + age-group 分组横线。',
    ],
    "potential_energy_surface": [
        "势能面",
        "反应坐标 vs 能量：反应物→过渡态（空心方块+‡）→产物的 PES；可标注活化能 Ea 箭头。",
    ],
    "pseudotime": [
        "伪时间轨迹",
        "细胞发育轨迹：UMAP 嵌入上按 pseudotime 0→1 连续着色 + 可选平滑轨迹曲线 + 箭头指示方向。",
    ],
    "quadrant_2x2": [
        "2×2 象限图",
        "品牌定位、战略取舍、评估矩阵——两轴各是一个对立概念，落点即定位。非高亮点用轮廓风（淡填+深描边），高亮点用实心 accent。",
    ],
    "radar": ["雷达图", "Multiple metrics with declared per-axis ranges and shared scales across facets."],
    "raincloud": ["云雨图", "半密度、真实观测、箱线在同一数轴上比较；支持方向、配对和条件分面。"],
    "ridge": ["山脊图", "每组真实观测或密度的纵向堆叠，用于比较分布；普通时间趋势使用 scatter 的曲线输入。"],
    "roc_pr": [
        "ROC/PR 曲线",
        "二分类评估：ROC（FPR vs TPR）或 PR（Recall vs Precision），每条曲线 AUC 自动算，带对角 baseline。",
    ],
    "sankey": ["桑基流", "量级流转——供应链上下游、预算分配、用户漏斗、能耗结构；两侧柱条厚度按流量。"],
    "scatter": [
        "分组散点图",
        "Observations, supplied or fitted curves, errors, categorical or continuous axes and shared group encodings.",
    ],
    "scatter_fit": [
        "散点+拟合",
        "两变量相关性 + 一次/多项式/幂律拟合 + 95% CI 带 + 右上角 R²/p/n 统计盒；期刊 figure 1 常见。",
    ],
    "seismic_waveform": [
        "地震波形",
        "多台站地震波：时间 vs 振幅堆叠（stacked）+ P/S 波到时事件竖线；地震学标准报告图。",
    ],
    "spectrum": [
        "谱图",
        "一维谱：实验谱（NMR / IR / Raman / mass spec）+ 峰注释（peak_style='stick'|'band'，x_reversed=True 右→左）；"
        "观测谱（凌星/发射/吸收谱）用 points 误差棒 + models 模型线与 1σ 带 + bands 分子吸收带。",
    ],
    "stress_strain": [
        "应力应变",
        "材料力学：σ-ε 曲线 + 弹性/塑性区背景带 + yield / ultimate / fracture 三个关键点 + Young's modulus 统计盒。",
    ],
    "swimmer": [
        "临床泳道图",
        "Per-patient treatment segments, follow-up and concurrent clinical events at their actual times.",
    ],
    "ternary": ["三元图", "三组分的重心坐标图：散点、气泡、类别/连续色、分面和三角域密度。"],
    "time_latitude": [
        "时间-纬度图",
        "气候/大气 Hovmöller 图：X 轴时间、Y 轴纬度、颜色编码标量值（如 SST / 风速 / 异常）；可开 diverging 色或 contour overlay。",
    ],
    "titration": ["滴定曲线", "酸碱 / 氧化还原滴定：加入体积 vs pH / 电位的 S 型曲线 + 等当点竖线 + pKa 水平线。"],
    "umap_cluster": ["UMAP/t-SNE 聚类", "单细胞/高维嵌入的 2D 聚类散点：每簇一色 + 簇心 label + 右侧 legend。"],
    "upset": ["集合交集图", "集合规模、独占或包含式交集计数，与相同排序的柱形和连点矩阵。"],
    "vector_field": [
        "向量场",
        "2D 流场 / 相图 / 磁场：网格箭头可视化，箭头大小/颜色编码幅值，可标注 source/sink/saddle 奇点。",
    ],
    "violin": [
        "小提琴分布",
        "多组连续变量的密度形状对比：按类别看分布尾巴、峰值、中位数偏移；学术印刷版 = KDE 轮廓 + 内嵌 mini boxplot + 均值空心圆 + outlier 空心圆 + Y 轴稀疏虚线网格。",
    ],
    "volcano": [
        "火山图",
        "差异表达 / 组学：x = log2 FC，y = -log10 p；左上/右上为显著基因，中间灰点为非显著。顶 K 个基因自动打标签。",
    ],
    "waterfall": [
        "瀑布图",
        '商业/财务的"毛→净"、MRR 变化归因、成本节余分解、预算差异分解；连接虚线让"跳台阶"感一眼可读。',
    ],
}

# Adapters with direct mode dispatch (legacy renderers expose their whitelist).
_CHART_MODES = {
    "grouped_bar": (
        "bars",
        "heatmap",
        "intervals",
        "boxplot",
        "raincloud",
        "marimekko",
        "with_facet_by_series",
    ),
    "scatter": ("with_marginal", "with_residual"),
    "scatter_fit": ("with_marginal", "with_residual"),
    "bubble": ("with_marginal",),
    "line_band": ("with_sample_size",),
}


# Charts that remain importable (for backwards-compat callers) but are hidden from the public catalog, help output and
# CLI choices.
_HIDDEN_FROM_CATALOG = {"event_timeline", "bar_academic", "academic_bar_chart"}

# Names agents commonly write for an existing chart; resolved by chart_help / chart_slide / chart_fit.
_CHART_ALIASES = {"grouped_bars": "grouped_bar", "academic_bar_chart": "grouped_bar"}

# The former radial academic_bar_chart now renders as Cartesian grouped_bar; its ring-only options are dropped.
_RING_ONLY_KWARGS = (
    "center",
    "grouping",
    "color_by",
    "inner_radius",
    "category_annotations",
    "group_gap",
    "value_format",
)


def _canonical_slug(slug):
    return _CHART_ALIASES.get(slug, slug) if isinstance(slug, str) else slug


def _drop_ring_kwargs(kwargs, stacklevel=3):
    """Strip options only the removed radial academic_bar_chart had, with one warning naming them."""
    import warnings

    ignored = [key for key in _RING_ONLY_KWARGS if key in kwargs]
    if ignored:
        warnings.warn(
            "academic_bar_chart: the radial ring was replaced by Cartesian grouped bars (grouped_bar); "
            f"ignored option(s) grouped_bar does not take: {', '.join(ignored)}",
            stacklevel=stacklevel,
        )
    return {key: value for key, value in kwargs.items() if key not in _RING_ONLY_KWARGS}


def make_academic_bar_chart(categories, series, **kwargs):
    """Deprecated alias: renders ``make_grouped_bar``; ring-only options are ignored with a warning."""
    return make_grouped_bar(categories, series, **_drop_ring_kwargs(kwargs))


def _chart_functions():
    """Return actual imported public generators, rather than a second hand-maintained list."""
    return {
        name.removeprefix("make_"): value
        for name, value in globals().items()
        if name.startswith("make_") and callable(value) and name.removeprefix("make_") not in _HIDDEN_FROM_CATALOG
    }


def chart_catalog():
    """Machine-readable capabilities; the same registry drives help and the CLI."""
    import inspect

    from svg_lib._common import _SVG_LIB_VARIANTS
    from svg_lib.chart_examples import EXAMPLES as examples

    result = {}
    for slug, function in sorted(_chart_functions().items()):
        metadata = _CHART_DESCRIPTIONS.get(slug)
        module = inspect.getmodule(function)
        modes = set(_CHART_MODES.get(slug, ()))
        if module is not None:
            for name, value in vars(module).items():
                if name.endswith("_MULTI_WHITELIST") and isinstance(value, dict):
                    modes.update(value)
        variants = _SVG_LIB_VARIANTS.get(slug, (None, [], None))[1]
        result[slug] = {
            "name": metadata[0] if metadata else slug.replace("_", " "),
            "function": function.__name__,
            "signature": str(inspect.signature(function)),
            "description": metadata[1] if metadata else (inspect.getdoc(function) or "").split("\n")[0],
            "example": f"{function.__name__}(**{examples[slug]!r})",
            "example_kwargs": examples[slug],
            "variants": list(variants),
            "modes": sorted(modes),
            "templates": ["facets", "tracks", "line_bar", "heatmap", "panels"] if slug == "composite" else [],
        }
    return result


# Charts whose multi_mode dispatch lives inside the function body instead of a ``_MULTI_WHITELIST`` dict.
_IN_FN_MODE_HINTS = {
    "grouped_bar": [
        (
            "bars",
            None,
            "auto default for few nonnegative summary values: Cartesian bars (horizontal for <=8 categories or long labels), values at bar ends",
        ),
        (
            "heatmap",
            None,
            "dense nonnegative summaries; matrix_heat circle_full with area legend and labels below dots; show_values=True shows all values",
        ),
        ("intervals", None, "sparse/mixed observations, supplied or computed intervals, or explicit comparisons"),
        ("boxplot", None, "at least 5 actual observations in every category/series cell"),
        ("raincloud", None, "at least 20 observations and 5 distinct values per cell; includes sample points"),
        (
            "marimekko",
            None,
            "stack='stacked'/'percent'; complete additive summary components with positive category totals",
        ),
        (
            "with_facet_by_series",
            None,
            "explicit legacy series facets; >=2 series and >=3 categories, actual observation arrays",
        ),
    ],
    "volcano": [("with_top_table", None, "need ranked points; falls back silently when top_k is 0")],
    "matrix_heat": [
        (
            "with_selected_comparison",
            None,
            "requires compare_cols=[name_a, name_b]; builds a dumbbell against the main heatmap",
        ),
    ],
    "scatter": [
        ("with_marginal", None, "adds marginal histograms on both axes"),
        ("with_residual", None, "requires fit='linear' or 'loess' on a series"),
    ],
    "scatter_fit": [
        ("with_marginal", None, "adds marginal histograms on both axes"),
        ("with_residual", None, "sub-panel plots residuals of the fit"),
    ],
    "bubble": [("with_marginal", None, "adds marginal distributions of x and y")],
    "line_band": [("with_sample_size", None, "requires sample_sizes list; sub-panel is n per x")],
    "funnel_classic": [],
    "population_pyramid": [],
}


def _mode_hints(slug):
    """Return a list of (mode_name, template, requirement_msg) tuples."""
    import inspect

    if slug == "grouped_bar":
        return list(_IN_FN_MODE_HINTS[slug])
    hints = []
    function = _chart_functions().get(slug)
    if function is None:
        return hints
    module = inspect.getmodule(function)
    if module is None:
        return hints
    for attr_name, attr_value in vars(module).items():
        if not attr_name.endswith("_MULTI_WHITELIST") or not isinstance(attr_value, dict):
            continue
        for mode_name, entry in attr_value.items():
            template = None
            msg = ""
            if isinstance(entry, tuple) and len(entry) >= 3:
                template, validator = entry[0], entry[2]
                try:
                    _ok, msg = validator({})
                except (ArithmeticError, AttributeError, LookupError, TypeError, ValueError) as exc:
                    msg = f"(probe raised {type(exc).__name__})"
            hints.append((mode_name, template, msg))
    if not hints and slug in _IN_FN_MODE_HINTS:
        hints = list(_IN_FN_MODE_HINTS[slug])
    return hints


def _pretty_example(kwargs, max_width=120, make=None):
    """Return runnable Python data, preserving example values and Python literals."""
    import pprint

    return pprint.pformat(_shorten_example(kwargs, make), width=max_width, sort_dicts=False, compact=True)


_EXAMPLE_KEEP = 12
_EXAMPLE_NUMBERS = 60


def _round_floats(value):
    if isinstance(value, float):
        return float(f"{value:.4g}")
    if isinstance(value, dict):
        return {k: _round_floats(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        items = [_round_floats(v) for v in value]
        return tuple(items) if isinstance(value, tuple) else items
    return value


def _truncate(value):
    if isinstance(value, dict):
        return {k: _truncate(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        items = [_truncate(v) for v in value]
        if len(items) > _EXAMPLE_KEEP and any(isinstance(v, dict) for v in items):
            items = items[:_EXAMPLE_KEEP]
        elif len(items) > _EXAMPLE_NUMBERS and all(isinstance(v, (int, float)) for v in items):
            items = items[:_EXAMPLE_NUMBERS]
        return tuple(items) if isinstance(value, tuple) else items
    return value


def _shorten_example(kwargs, make=None):
    """Help-text copy of the demo data: 4 significant digits, and long lists cut when the cut copy still renders."""
    rounded = _round_floats(kwargs)
    if make is None:
        return rounded
    cut = _truncate(rounded)
    if cut == rounded:
        return rounded
    try:
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            make(**cut)
        return cut
    except Exception:
        return rounded


# These conditions guide discovery; they do not change compatible make_* APIs.
_CHART_SELECTION = (
    (
        "类别概览（学术 / 策略）",
        "grouped_bar",
        "只有其他专业图都不贴切时才用 grouped_bar（直角坐标条形，数值标在条端）：两组配对值用 dumbbell，估计值与区间用 forest / coef_plot，随时间/剂量变化用曲线。中心均值及SD/SEM/CI仅在输入确为相应观测时显式启用。",
    ),
    (
        "两状态 / 前后对比（条形对比）",
        "dumbbell",
        "每行一个对象、两个同口径值（如前/后、对照/处理、两种材料）；横向排列，标签与差值清楚。",
    ),
    (
        "曲线 / 剖面 / 能量图",
        "scatter / potential_energy_surface / kinetics / titration",
        "有 x-y 数值的曲线（电压-容量、能垒-反应坐标、浓度-时间）用 scatter 的 curve 或对应专业入口，不要用 drawing 手画坐标曲线。",
    ),
    (
        "类别名其实是数值（ε=1、303 K、10 epochs）",
        "scatter",
        "每个系列一条 curve，x 取该数值；跨 >20 倍用 x_transform='log10'，比值/倍数类加 y=1 参考线。",
    ),
    (
        "自适应分组比较 / 普通趋势",
        "grouped_bar / scatter",
        "grouped_bar 也用于单系列少量数值（自动画直角坐标条形），前后两值用 dumbbell。grouped_bar 按非负汇总值、样本、区间或已声明组成选择视图；负值按报错转用原生图表。趋势 curve 使用实际 x/y，无拟合任务时 fit=None，无区间时 show_ci=False。",
    ),
    (
        "样本分布",
        "boxplot / violin / raincloud / ridge / histogram",
        "需要逐样本观测或接口支持的明确分位数/密度；仅均值、SEM、总量不足以还原分布。",
    ),
    (
        "不确定性 / 科学曲线",
        "forest / line_band / roc_pr / km_survival",
        "forest 用文献已报告的点估计+CI 即可；line_band 用已报告的均值与区间；roc_pr 需逐阈值点；km_survival 需逐例时间与删失。",
    ),
    ("变化贡献", "waterfall", "需要起终值与可加的增减项；时间趋势、独立消融结果不能直接当归因。"),
    (
        "组成 / 流转",
        "marimekko / nested_donut / sankey / funnel_classic",
        "已报告的组成比例或各阶段数量即可；流入流出须守恒，损耗显式给出。",
    ),
    (
        "多维关系 / 矩阵",
        "scatter / bubble / matrix_heat / dot_matrix / parallel_coords",
        "同一组对象在同一组指标上的已报告值即可（如多种材料的容量/倍率/循环）；不为加维度编评分，相关不等于因果。",
    ),
    (
        "专业测量 / 场",
        "spectrum / stress_strain / vector_field",
        "使用文献报告的测量点或特征值（峰位、屈服点、相界）及单位；其他专业入口见下方索引。",
    ),
    ("多面板", "composite", "每个面板都应增加证据；已有数据满足各面板条件，放到页面后标签仍可读。"),
)

_DATA_REQUIREMENTS = {
    slug: requirement for _meaning, slugs, requirement in _CHART_SELECTION for slug in slugs.split(" / ")
}
_P_HINT = " p 填数字 0.003；原文是阈值就传字符串 '<.05' / '<0.001' / 'n.s.'（不要把 P<.05 写成 0.05）。"
_DATA_REQUIREMENTS.update(
    {
        "grouped_bar": "类别与系列同口径、数值非负。auto 根据数据选择直角坐标条形/热力/区间/箱线/雨云；声明组成关系后用 Marimekko。汇总值不能还原分布；区间/样本/已请求的比较不能因换图丢失。负观测、负汇总值、负区间或负轴域报错，按提示改用原生图表。完整条件与显式模式见下方说明。",
        "dumbbell": "每行两个明确命名、同口径的观测；连接不自动意味着配对检验或因果。来源报告了区间就逐行填 before_lo/before_hi、after_lo/after_hi（画在端点上的 CI 须线），delta_ci=(lo, hi) 填变化量区间。"
        + _P_HINT,
        "coef_plot": "每个点为已报告的估计值，有 CI 时给 lo/hi（不自造区间）；series=[{name, points:[{x,y,lo,hi}]}] 画事件研究（x 为相对时期，base_x 标基期，event_label 标政策时点），rows=[{label, estimate, lo, hi, group}] 画多研究对比（≥2 个 group 自动分色+图例）；IRF/局部投影：x=期数、band=True，多变量 panels=True；调节效应：x=调节变量、每臂一条 series、band=True，interaction={'b','se'/'ci','p'} 标交互项；比值类 HR/OR 用 forest。",
        "spectrum": "实验谱用真实采样的 x/y 与报告峰位及单位。观测谱用真实分箱点与误差；没有数据时引用原图，不要用随机数合成。"
        "points=[{x, y, y_err}] 画误差棒，models=[{name, x, y, lo, hi}] 画模型线与 1σ 带，"
        "bands=[{start, end, label}] 画分子吸收带/谱窗。",
        "potential_energy_surface": "两种写法：① 单条曲线 curve + states（反应物/TS/产物，可标 activation_energies）；② 自由能图 pathways=[{name, energies, ts}] + steps=[各步名称]，多个催化剂/晶面/路径共用一条反应坐标并排对比（如 Cu(100) vs 晶界 Cu 的 C–C 偶联能垒），每条路径的最大正向能垒自动标注 ΔG‡，也可用 barriers 指定。能量用 DFT/文献报告值，energy_unit 写 eV 或 kJ/mol。能垒对比优先用 ②，不要拆成分组柱状图。",
        "forest": "每行已有点估计及其 CI，并明确单位/效应量/无效线；ci_level=95 表示95%，混合水平逐行给出，未提供时不假定95%；均值 ± SEM 不能变为 effect size + CI。log_x 默认自动（比值、无效线 1、跨 >10× 用对数轴），可显式 True/False；value_domain 可固定范围；single 模式可换行长标签，仍须按实际嵌入尺寸检查。favours=(左, 右)：HR/OR 左=治疗更优，d/SMD/MD（midline_value=0）右=干预更优；heterogeneity=dict(I2=, tau2=, Q=, p=) 标在合并行下。",
        "scatter": "曲线/散点用实际 x/y；末端自动标注可用 end_labels=False 关闭；x 是冲击后期数（IRF、局部投影）改用 coef_plot(series=, band=True)；参数量–精度权衡加 frontier=True。",
        "bubble": "x/y/size 均为已报告值；frontier=True 连帕累托前沿，尺寸图例自动放进空白角。",
        "line_band": "需要真实 x/y 与已提供或有依据计算的区间，标明 SD/SEM/CI；无不确定性的普通趋势使用 scatter 的曲线输入。",
        "roc_pr": "使用真实标签与预测分数或逐阈值 ROC/PR 点；只有 accuracy/AUC 汇总值不能还原曲线。",
        "km_survival": "需要事件时间与删失状态或已估计的生存阶梯；不能从各组总人数/事件率补造曲线。",
        "percent_grid": "每格代表明确相同比例，输入须匹配格数；多选题不能拼成互斥的整体占比。",
        "candle": "每期必须有实际 open/high/low/close；两个端点或均值不能还原 OHLC。",
        "gantt": "任务 tuple 第4项是 stream 工作流标签，不是关键路径标记（0/1也是标签）；关键路径单独用 critical_index。数值时间轴用 time_unit='h' 标单位。",
        "calheat": "需要日历对应的真实逐日数值；年度总量不能拆造逐日热度。",
        "upset": "需要真实集合成员或交集计数；单集合汇总量不足以推断交集。",
        "ternary": "每个样本是三个同口径、合计固定总量的非负组成。",
        "phylogeny": "需要实际树结构与分支长度；一般组织/协作结构使用可编辑关系库。",
    }
)


_DATA_REQUIREMENTS["stress_strain"] = (
    "单条 curve=[(ε, σ)…] 自动标屈服/UTS/断裂；多材料/温度对比用 curves={名称: [(ε, σ)…]} 叠在一张图，"
    "hardening=True 加 dσ/dε–ε 加工硬化率面板（稀疏的文献数字化点也可，内部单调插值）。"
)
_DATA_REQUIREMENTS["scatter"] = _DATA_REQUIREMENTS["scatter"].replace(
    "参数量–精度权衡加 frontier=True。",
    "参数量–精度权衡、材料强度–塑性权衡（x=强度, y=延伸率）加 frontier=True；预测/情景段 projected_from=2024 画虚线。",
)
for _slug in ("grouped_bar", "coef_plot", "forest", "scatter"):
    _DATA_REQUIREMENTS[_slug] += _P_HINT
_SUMMARY_SNIPPETS = {
    "grouped_bar": (
        "chart_slide('grouped_bar', 40, 110, 560, 330, categories=['NCM523', 'NCM622', 'NCM811'],\n"
        "            series=[{'name': '放电比容量', 'values': [165, 178, 203]}],   # 数字 = 汇总值；有区间写 {'value': v, 'lo': a, 'hi': b}\n"
        "            y_title='mAh/g', source='Bak et al. 2014')"
    ),
    "dumbbell": (
        "chart_slide('dumbbell', 40, 110, 560, 330, rows=[\n"
        "    {'label': 'NCM811', 'before': 228, 'before_lo': 222, 'before_hi': 234,\n"
        "     'after': 261, 'after_lo': 255, 'after_hi': 266, 'p': 0.003, 'n': 12},   # 端点 95% CI\n"
        "    {'label': 'NCM622', 'before': 241, 'after': 259, 'p': '<.05', 'n': 12},   # 原文只报阈值\n"
        "    {'label': 'NCM523', 'before': 252, 'after': 263}],   # 区间/p/n 仅在来源报告时填\n"
        "    series_labels=('改性前', '改性后'), x_title='放热峰温度 (°C)')"
    ),
    "forest": (
        "chart_slide('forest', 40, 110, 700, 330, rows=[\n"
        "    {'label': 'PD-L1 ≥50%', 'estimate': 0.62, 'ci_lo': 0.45, 'ci_hi': 0.85, 'n': 305, 'p': 0.002},\n"
        "    {'label': 'PD-L1 <50%', 'estimate': 0.88, 'ci_lo': 0.70, 'ci_hi': 1.10, 'n': 410},\n"
        "    {'label': '总体', 'estimate': 0.76, 'ci_lo': 0.64, 'ci_hi': 0.90, 'is_overall': True}],\n"
        "    x_title='HR (OS)', favours=('利于免疫治疗', '利于化疗'))"
    ),
    "spectrum": (
        "chart_slide('spectrum', box=(40, 110, 800, 380),   # x/y 是数据名，所以用 box=\n"
        "    points=[{'x': 3.0, 'y': 2.205, 'y_err': 0.011}, {'x': 3.6, 'y': 2.181, 'y_err': 0.010},\n"
        "            {'x': 4.0, 'y': 2.199, 'y_err': 0.014}, {'x': 4.3, 'y': 2.235, 'y_err': 0.010},\n"
        "            {'x': 4.6, 'y': 2.189, 'y_err': 0.014}, {'x': 5.0, 'y': 2.178, 'y_err': 0.012}],  # 分箱观测点 ± 1σ\n"
        "    models=[{'name': '最佳拟合模型', 'x': [3.0, 3.6, 4.0, 4.3, 4.6, 5.0],\n"
        "             'y': [2.204, 2.180, 2.192, 2.230, 2.190, 2.180],\n"
        "             'lo': [2.198, 2.174, 2.186, 2.224, 2.184, 2.174], 'hi': [2.210, 2.186, 2.198, 2.236, 2.196, 2.186]}],\n"
        "    bands=[{'start': 2.9, 'end': 3.2, 'label': 'H₂O'}, {'start': 4.2, 'end': 4.4, 'label': 'CO₂'}],\n"
        "    x_title='波长', x_unit='μm', y_title='凌星深度', y_unit='%', source='JWST NIRSpec, 文献图 2')"
    ),
    "coef_plot": (
        "chart_slide('coef_plot', 40, 110, 640, 330, rows=[\n"
        "    {'label': '本研究 (单臂)', 'estimate': 42.0, 'lo': 33.5, 'hi': 50.9, 'benchmark': 25.0, 'n': 120},\n"
        "    {'label': '亚组 ≥65 岁', 'estimate': 38.0, 'lo': 25.1, 'hi': 52.3, 'benchmark': 25.0},\n"
        "    {'label': '亚组 PD-L1+', 'estimate': 51.0, 'lo': 39.8, 'hi': 62.1, 'benchmark': 25.0}],\n"
        "    benchmark_label='历史对照 ORR', x_title='ORR (%)', reference=None)"
    ),
}


def chart_help(name=None, full=False):
    """Describe the actual generators; full=True adds the generator's complete notes."""
    import inspect

    catalog = chart_catalog()
    name = _canonical_slug(name)
    if name is not None:
        if name == "bar_academic":
            raise ValueError(
                "bar_academic is a legacy Python API, hidden from public discovery. "
                "Use chart_help('grouped_bar') for category comparisons."
            )
        if name not in catalog:
            raise ValueError(f"Unknown chart {name!r}. Available: {', '.join(catalog)}")
        entry = catalog[name]
        lines = [
            f"# {name} - {entry['name']}",
            entry["description"],
            "",
            f"On a slide: frag = chart_slide({name!r}, x, y, w, h, **kwargs) → publish_slide(page_xml, frag, ...). "
            "make_* returns one SVG string (not a tuple); do not call make_* to preview or search sizes — "
            "chart_slide fits any box (a 'fitted … at N% scale' warning is success; use chart_fit for the box).",
            "",
        ]

        if name in _DATA_REQUIREMENTS:
            lines += ["Data conditions: " + _DATA_REQUIREMENTS[name], ""]
        # Keep the exact public signature: commas also occur in annotations and defaults.
        lines.append(entry["function"] + entry["signature"])

        if entry["variants"]:
            lines += ["", "Variants: " + ", ".join(entry["variants"])]

        hints = _mode_hints(name)
        if hints:
            lines += ["", "Multi modes (pass via multi_mode=...):"]
            for mode_name, template, msg in hints:
                requirement = f" — {msg}" if msg else ""
                lines.append(f"  - {mode_name} [{template or 'in-fn'}]{requirement}")
        elif entry["modes"]:
            lines += ["", "Multi modes: " + ", ".join(entry["modes"])]

        if entry["templates"]:
            lines += ["", "Composite templates: " + ", ".join(entry["templates"])]

        if entry.get("example_kwargs"):
            lines += ["", "Example (ready to run):", "```python"]
            lines.append(f"from scripts.gen_svg_charts import {entry['function']}")
            lines.append("kwargs = " + _pretty_example(entry["example_kwargs"], make=_chart_functions()[name]))
            lines.append(f"svg = {entry['function']}(**kwargs)")
            lines.append("```")
        if name in _SUMMARY_SNIPPETS:
            lines += [
                "",
                "On a slide with reported summary values (most common in decks):",
                "```py",
                _SUMMARY_SNIPPETS[name],
                "```",
            ]

        docstring = inspect.getdoc(_chart_functions()[name])
        if docstring:
            if full:
                lines += ["", "Notes:", docstring]
            else:
                lead = docstring.split("\n\n")[0]
                more = " (more: chart_help(%r, full=True))" % name if lead != docstring else ""
                lines += ["", "Notes: " + " ".join(lead.split()) + more]
        return "\n".join(lines)

    lines = [
        f"# SVG charts ({len(catalog)} generators)",
        "",
        _SELECTION_GUIDE,
        "",
        "## 按研究问题选图（举例，不是白名单）",
        "",
        "下表只是常见搭配的示例：没有列出的学科、研究问题同样可以作图；同一张图也不限于表中所在的行，"
        "只要数据条件满足，可以用在任何学科和场景。鼓励在文末「全部入口」中选用表里没有提到的图种，"
        "只要它比表中的入口更能回答这一页的问题。",
        "",
        "| 学科 | 这页要回答 | 入口 | 只有文献报告值时 |",
        "|---|---|---|---|",
    ]
    lines.extend(f"| {field} | {question} | {slugs} | {feed} |" for field, question, slugs, feed in _BY_QUESTION)
    lines += [
        "",
        "## 数据条件",
        "",
        "| 要表达什么 | 入口 | 数据条件 |",
        "|---|---|---|",
    ]
    lines.extend(f"| {meaning} | {slugs} | {requirement} |" for meaning, slugs, requirement in _CHART_SELECTION)
    lines += [
        "",
        "按需详情：chart_help('<slug>') 返回真实签名、变体、组合条件及可运行示例。",
        "例如 chart_help('boxplot')；示例只演示接口，替换为任务数据后再生成。",
        "make_<slug>(**kwargs) 一次返回完整 SVG；CLI: --type <slug> --data-file <kwargs.json>。",
        "自动生成的轴名/图例/注释随传入文字的语言：任一参数含中文即输出中文（HR、CI、SD、P 等缩写保留），可用 lang='zh'/'en' 指定；你传入的文字原样保留。",
        "放进幻灯片用 chart_slide(slug, x=, y=, width=, height=, **kwargs)：按目标框尺寸出图，返回半可编辑片段"
        "（文字原生可改字号/内容，同色柱块/扇区为可整体换色的原生形状，其余留在局部 SVG）；用 compose_slide(page_xml, fragment) 合页。",
        "在幻灯片实际显示尺寸检查标签、单位、注释和图例；不足时减少面板或调整图内布局，不能删关键内容。",
        "关系库支持的结构用可编辑输出；自定义机制/流程/实验设计用 drawing 库画后 to_slide。",
        "",
        "## 全部入口（名称索引；详情仍在同一 chart_help 入口）",
    ]
    for slug, entry in catalog.items():
        lines.append(f"- {slug}: {entry['name']}")
    return "\n".join(lines)


_BY_QUESTION = (
    # (学科, 研究问题, 入口, 只有文献报告值时怎么画)
    (
        "医学 / 临床",
        "疗效、风险在各试验或亚组间怎样比较",
        "forest",
        "各试验/亚组已报告的 HR、OR、率差及其 CI 逐行填入；没有 CI 的行不要硬放。",
    ),
    (
        "医学 / 临床",
        "同一指标在两种条件下的差距（前后、对照/处理、血液瘤/实体瘤）",
        "dumbbell",
        "每行一个试验或适应症，两个已报告值；差距本身就是论点时比柱状更直观。",
    ),
    (
        "医学 / 临床",
        "每位患者的治疗、缓解与进展时间线",
        "swimmer",
        "病例报告或小样本早期试验公开的逐例时间；只有中位数时不适用。",
    ),
    (
        "医学 / 临床",
        "生存曲线比较",
        "km_survival",
        "需要逐例时间与删失；只有中位 OS/PFS 时改用 forest（HR+CI）或 dumbbell（两组中位数）。",
    ),
    ("药理 / 生化", "剂量与效应、EC50/IC50", "dose_response", "文献中各剂量下的响应率或抑制率。"),
    (
        "药理 / 生化",
        "随时间的变化（药代、扩增、释放、降解）",
        "kinetics / line_band",
        "已报告的若干时间点数值即可；有 SD/SEM/CI 时用 line_band。",
    ),
    (
        "组学 / 分子",
        "差异表达、通路富集、单细胞表达",
        "volcano / clustered_heatmap / dot_plot_scrna",
        "补充表中的 log2FC、p 值或表达矩阵。",
    ),
    (
        "材料 / 能源",
        "循环、倍率、电压-容量、J-V 等性能曲线",
        "scatter（curve）/ line_band",
        "从文献读出的关键点按实际 x/y 填入，多条件多系列对比，标注来源。",
    ),
    (
        "材料 / 能源",
        "阻抗、谱学、力学、相区与组成",
        "nyquist_bode / spectrum / stress_strain / phase_diagram / ternary",
        "报告的测量点或特征值（峰位、屈服点、相界、组成）。",
    ),
    (
        "化学 / 物理",
        "反应能垒与路径对比（多个催化剂/晶面/机理）",
        "potential_energy_surface(pathways=, steps=)",
        "各中间体/过渡态的 DFT 或文献能量；多路径并排画自由能图，自动标注决速步 ΔG‡。",
    ),
    (
        "化学 / 物理",
        "实验与理论对照、幂律关系、滴定",
        "scatter / titration",
        "带误差的测量点、理论曲线；幂律用 scatter(x_transform='log10', y_transform='log10')。",
    ),
    (
        "通用",
        "多指标综合画像（方法、材料、方案对比）",
        "radar / matrix_heat / parallel_coords",
        "每个对象在同一组指标上的已报告值，标明各轴范围。",
    ),
    (
        "通用",
        "构成与流转（占比、阶段转化、来源去向、增减归因）",
        "nested_donut / marimekko / sankey / waterfall",
        "已报告的组成比例、各阶段数量或增减项。",
    ),
    (
        "经济 / 社科",
        "政策效应随时间的动态（事件研究、DID 领先滞后期）",
        "coef_plot(series=)",
        "各期已报告的系数与 CI；基期 base_x 标为 0，政策时点画竖线。",
    ),
    (
        "经济 / 社科",
        "冲击后的动态响应（IRF、局部投影）",
        "coef_plot(series=, band=True)",
        "x=冲击后期数 0,1,2…，各期点估计+CI 带；多个响应变量 panels=True 分面，不要用 scatter 手读曲线。",
    ),
    (
        "经济 / 社科 / 医学",
        "多项研究或模型的效应估计（可正可负，如弹性、边际效应、均差）",
        "coef_plot(rows=)",
        "点估计 + CI 逐行填入；比值类（HR/OR）用 forest。",
    ),
    (
        "经济 / 社科 / 教育 / 医学",
        "调节效应 / 异质性：处理效应随调节变量变化",
        "coef_plot(series=, band=True, interaction=)",
        "x=调节变量（基线百分位、中心化得分；类别水平编码 0/1/2），每个处理臂一条预测线+CI 带（reference=None），"
        "或一条条件效应线（reference=0）；interaction={'b': .12, 'se': .04, 'p': '<.01'} 标交互项。",
    ),
    (
        "医学 / 临床",
        "单臂研究 vs 历史对照 / 目标值",
        "coef_plot(rows=)",
        "每行 estimate + lo/hi，对照或目标值写进该行 benchmark。",
    ),
    (
        "材料 / 能源 / 化工",
        "性能随时间衰减、寿命、中毒/老化",
        "scatter（curve）/ line_band",
        "x=时间（h/循环数），各条件一条曲线；报告区间用 line_band，T80/寿命阈值画 reference_lines。",
    ),
    (
        "天文 / 行星",
        "凌星/发射/吸收谱的分子特征",
        "spectrum(points=, models=, bands=)",
        "文献分箱点 ± 误差、模型曲线与 1σ 带、分子吸收带；没有数据时引用原图，不要合成。",
    ),
    (
        "机器学习 / CS",
        "隐私–效用、精度–算力、超参数敏感性",
        "scatter（curve）",
        "x 用数值（ε、FLOPs、学习率），跨数量级用对数 x；基线画 reference_lines。",
    ),
    (
        "机器学习 / CS",
        "多随机种子结果；消融或前后对比",
        "line_band / grouped_bar 误差棒；dumbbell",
        "报告了均值±SD 才画区间；消融每行一个模块的有/无。",
    ),
    (
        "材料 / 化工",
        "吸附等温线、穿透曲线、温度/压力依赖",
        "scatter（curve）",
        "实际 x/y 填入，工况点画 reference_lines；文献报告范围时用 lo/hi，不要取中值。",
    ),
    (
        "医学 / 通用",
        "阶段 / 检测窗口 / 时程区间（如标志物 2–6 h 升高）",
        "gantt",
        "每项 (名称, 起, 止, 分组) 画区间条，time_unit='h' 标单位；variant='dot_range' 标起止值。",
    ),
    (
        "机器学习 / CS",
        "参数量/算力–精度权衡",
        "scatter / bubble(frontier=True)",
        "各模型已报告的数值；frontier=True 连帕累托前沿，跨数量级用对数 x。",
    ),
    (
        "通用",
        "少量类别的单一数值概览",
        "grouped_bar",
        "只有“类别 + 一个数”且上面没有更贴切的问题时才用 grouped_bar（直角坐标条形）。",
    ),
)

_SELECTION_GUIDE = (
    "本总览需完整阅读（不要用 head/tail 截断），末尾「全部入口」列出了所有图种。"
    "先写下这页要回答的研究问题，再参考下表或全部入口选图。文献已报告的汇总值（HR+CI、ORR、时间点数值、峰位、能垒…）"
    "足以画大多数专业图，标注来源即可，不必有逐样本原始数据；只有确实没有更贴切的问题时才用类别柱状。"
    "数值不能编造：缺的量就不画，不为换图补造区间或分布。"
)


_SIZE_HINT = None


_AXIS_RE = None


def _plot_area(svg):
    """Longest marked axis spans ``(x0, y0, width, height)`` in viewBox px, or None when unmarked."""
    import re

    global _AXIS_RE
    if _AXIS_RE is None:
        _AXIS_RE = re.compile(r'<(?:line|path)\b[^>]*\bdata-role="([xy])-axis"[^>]*>')
    spans = {"x": [], "y": []}
    for match in _AXIS_RE.finditer(svg):
        tag = match.group(0)
        attrs = dict(re.findall(r'\b(x1|y1|x2|y2|d)="([^"]*)"', tag))
        try:
            if "d" in attrs:
                nums = [float(v) for v in re.findall(r"-?[0-9.]+(?:e-?[0-9]+)?", attrs["d"])]
                cmd = re.findall(r"[MmHhVvLl]", attrs["d"])
                if len(nums) < 3 or cmd[:1] != ["M"]:
                    continue
                x0, y0 = nums[0], nums[1]
                if cmd[1:2] == ["H"]:
                    x1, y1 = nums[2], y0
                elif cmd[1:2] == ["V"]:
                    x1, y1 = x0, nums[2]
                elif cmd[1:2] == ["L"] and len(nums) >= 4:
                    x1, y1 = nums[2], nums[3]
                else:
                    continue
            else:
                x0, y0, x1, y1 = (float(attrs[k]) for k in ("x1", "y1", "x2", "y2"))
        except (KeyError, ValueError):
            continue
        if match.group(1) == "x":
            spans["x"].append((min(x0, x1), abs(x1 - x0)))
        else:
            spans["y"].append((min(y0, y1), abs(y1 - y0)))
    if not spans["x"] or not spans["y"]:
        return None
    (x, w), (y, h) = max(spans["x"], key=lambda t: t[1]), max(spans["y"], key=lambda t: t[1])
    return x, y, w, h


_PLOT_GROW_MAX = 2.2


def _plot_shortfall(svg, box_w, box_h):
    """How much the canvas must grow so the plot reaches a usable size on the slide (1.0 = fine)."""
    import re

    area = _plot_area(svg)
    if area is None:
        return 1.0, None
    vw, vh = (float(v) for v in re.search(r'viewBox="([^"]+)"', svg).group(1).replace(",", " ").split()[2:])
    k = max(vw / box_w, vh / box_h)  # canvas px per slide px
    need_h = max(0.35 * box_h, min(120.0, 0.45 * box_h))
    need_w = max(0.35 * box_w, min(160.0, 0.45 * box_w))
    pw, ph = area[2] / k, area[3] / k  # plot size on the slide
    grow = 1.0
    for got, need, canvas, box in ((ph, need_h, vh, box_h), (pw, need_w, vw, box_w)):
        if got + 0.5 >= need:
            continue
        # Fixed chrome m = canvas - plot; growing by g gives (g*canvas - m) / (g*k) on the slide.
        chrome = canvas - got * k
        room = box - need
        grow = max(grow, chrome / (k * room) + 0.04 if room > 1 else _PLOT_GROW_MAX)
    return grow, (pw, ph)


def _render_fitting(make, params, kwargs, width, height):
    """Render at the box size."""
    import re

    global _SIZE_HINT
    _SIZE_HINT = None
    attempt, last = dict(kwargs), None
    sized = all(attempt.get(k) for k in ("width", "height") if k in params) and any(
        k in params for k in ("width", "height")
    )
    best = None
    for _ in range(8):
        try:
            chart_svg = make(**attempt)
            rendered = (chart_svg, _SIZE_HINT)  # (svg string, size notice) — make_* itself returns only the string
        except ValueError as error:
            last = error
            need = dict(
                re.findall(r"(width|height)[^0-9]{0,40}?(?:at least|need(?:s)? about|≥|>=)\s*([0-9.]+)", str(error))
            )
            if not any(k in params for k in ("width", "height")) or not re.search(
                r"too small|too short|too narrow|at least|>=|needs? (?:more|about|a larger|a taller|a wider)|taller canvas|wider canvas|larger canvas|increase (?:width|height)",
                str(error),
            ):
                raise
            grow = 1.25
            for key, value in need.items():
                if key in params and attempt.get(key):
                    grow = max(grow, float(value) / float(attempt[key]) + 0.02)
            for key in ("width", "height"):
                if key in params and attempt.get(key):
                    attempt[key] = float(attempt[key]) * grow
            continue
        if not sized or "width" not in params or "height" not in params:
            return rendered
        grow, plot = _plot_shortfall(chart_svg, float(width), float(height))
        if plot is not None and (best is None or min(plot[1] / height, plot[0] / width) > best[0] + 1e-3):
            best = (min(plot[1] / height, plot[0] / width), rendered)
        factor = float(attempt["height"]) / float(height)
        if grow <= 1.0 or factor >= _PLOT_GROW_MAX - 1e-6:
            return rendered if grow <= 1.0 or best is None else best[1]
        grow = min(max(grow, 1.12), _PLOT_GROW_MAX / factor)
        for key in ("width", "height"):
            attempt[key] = float(attempt[key]) * grow
    if best is not None:
        return best[1]
    raise ValueError(
        f"{last} — even a {attempt.get('width', width):.0f}x{attempt.get('height', height):.0f} canvas "
        "does not fit this data; split it across panels/pages"
    ) from last


def _warn_wide_bar_range(slug, svg, kwargs):
    """Linear bars spanning > 30x make the small values invisible; point the caller at a log axis."""
    import re
    import warnings

    if slug not in ("grouped_bar", "bar_academic") or 'data-role="categorical-chart"' not in svg:
        return
    domain = re.search(r'data-role="categorical-chart"[^>]*data-domain="\(([^,]+), ([^)]+)\)"', svg)
    values = [float(v) for v in re.findall(r'data-role="bar"[^>]*?data-value="([^"]+)"', svg)]
    if not values or min(values) <= 0 or max(values) / min(values) <= 30:
        return
    if domain and float(domain.group(1)) > 0:
        return  # already a log axis
    hint = (
        ""
        if kwargs.get("axis_break") is not None or kwargs.get("stack") not in (None, "none")
        else "pass value_scale='log' (axis title gets “对数轴”), or "
    )
    warnings.warn(
        f"chart_slide({slug!r}): bar values span {max(values) / min(values):.0f}x on a linear axis — the "
        f"smallest bars are nearly invisible; {hint}use coef_plot / a dot plot on a log axis",
        stacklevel=3,
    )


SLIDE_CHART_FONT = "思源黑体, Source Han Sans SC, Noto Sans CJK SC, PingFang SC, Microsoft YaHei, sans-serif"


_FIRST_SHAPE = None


def _drop_canvas_background(svg):
    """Remove the light full-canvas backing rect so the chart sits on the page colour (cream, paper, white alike)."""
    import re

    global _FIRST_SHAPE
    if _FIRST_SHAPE is None:
        _FIRST_SHAPE = re.compile(r"<(rect|path|line|polyline|polygon|circle|ellipse|text|image)\b[^>]*?/?>")
    shape = _FIRST_SHAPE.search(svg)
    box = re.search(r'viewBox="([^"]+)"', svg)
    if not shape or shape.group(1) != "rect" or not box:
        return svg
    tag = shape.group(0)
    attr = lambda name, default=None: (re.search(rf'\b{name}="([^"]*)"', tag) or [None, default])[1]
    vx, vy, vw, vh = (float(v) for v in box.group(1).replace(",", " ").split())
    try:
        x, y = float(attr("x", 0)), float(attr("y", 0))
        w, h = float(attr("width", 0)), float(attr("height", 0))
    except ValueError:
        return svg
    fill = (attr("fill", "") or "").strip()
    if attr("rx") or w * h < 0.9 * vw * vh or x > vx + 0.05 * vw or y > vy + 0.05 * vh or fill.lower() in ("", "none"):
        return svg
    from svg_lib._color_compat import parse_color

    parsed = parse_color(fill)
    if parsed is None:
        return svg
    r, g, b = (int(parsed[0][i : i + 2], 16) for i in (1, 3, 5))
    if 0.299 * r + 0.587 * g + 0.114 * b < 140:
        return svg
    return svg[: shape.start()] + svg[shape.end() :]


def _bar_values(svg):
    import re

    return [float(v) for v in re.findall(r'data-role="bar"[^>]*?data-value="([-0-9.eE+]+)"', svg)]


def _warn_narrow_bar_range(slug, svg, kwargs):
    """Bars must start at 0, so values within ~15% of each other look identical; suggest points instead."""
    import re
    import warnings

    if slug not in ("grouped_bar", "bar_academic") or kwargs.get("stack") not in (None, "none"):
        return
    values = _bar_values(svg)
    if len(values) < 3 or min(values) <= 0 or (max(values) - min(values)) / max(values) > 0.15:
        return
    if (
        re.search(r'data-role="categorical-chart"[^>]*data-domain="\(([^,]+),', svg)
        and float(re.search(r'data-domain="\(([^,]+),', svg).group(1)) > 0
    ):
        return  # explicit non-zero/log axis already chosen by the caller
    bounded = max(values) <= 1 or (max(values) <= 100 and min(values) > 50)
    what = "a bounded metric (0–1 / %)" if bounded else "values"
    warnings.warn(
        f"chart_slide({slug!r}): all bars lie within {(max(values) - min(values)) / max(values):.0%} of each other "
        f"({min(values):g}–{max(values):g}); bars must start at 0, so {what} this close look equal. Use "
        "dumbbell / coef_plot(rows=…) / a dot plot with a tight value axis (value_min=…), or state the "
        "differences in text — the bar baseline is not truncated silently",
        stacklevel=3,
    )


def _warn_forest_without_ci(slug, svg, kwargs=None):
    import warnings

    if slug == "forest" and 'data-forest-ci="none"' in svg:
        warnings.warn(
            "chart_slide('forest'): no row has a confidence interval, so this is not a forest plot (no whiskers to "
            "read against the reference line); use coef_plot(rows=[{label, estimate}...]) or a dot plot, or supply "
            "ci_lo/ci_hi from the source",
            stacklevel=3,
        )
        return
    rows = [
        r
        for r in (kwargs or {}).get("rows") or []
        if isinstance(r, dict) and not r.get("is_subgroup_header") and r.get("estimate") is not None
    ]
    missing = [r for r in rows if r.get("ci_lo") is None and r.get("lo") is None]
    if slug == "forest" and rows and len(missing) * 2 > len(rows):
        warnings.warn(
            f"chart_slide('forest'): {len(missing)}/{len(rows)} 行没有 CI——森林图要靠区间与无效线比较；"
            "来源报告了就填 ci_lo/ci_hi，否则改 coef_plot(rows=) 点图并在 note 注明“未报告 CI”",
            stacklevel=3,
        )


def _threshold_p_values(value, found=None):
    """Float P values equal to a conventional threshold (0.05/0.01/0.001), anywhere under p/pvalue/pairwise_p keys."""
    found = [] if found is None else found
    if isinstance(value, dict):
        for key, item in value.items():
            if key in ("p", "pvalue", "p_value") and isinstance(item, float) and item in (0.05, 0.01, 0.001):
                found.append(item)
            elif key == "pairwise_p" and isinstance(item, (list, tuple)):
                for c in item:
                    last = (
                        c.get("p") if isinstance(c, dict) else (c[-1] if isinstance(c, (list, tuple)) and c else None)
                    )
                    if isinstance(last, float) and last in (0.05, 0.01, 0.001):
                        found.append(last)
            else:
                _threshold_p_values(item, found)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _threshold_p_values(item, found)
    return found


def _hue_name(color):
    """Rough Chinese colour word for an rgb()/rgba()/#hex paint, so captions can name what is drawn."""
    import colorsys
    import re

    m = re.match(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", color or "")
    if m:
        r, g, b = (int(v) / 255 for v in m.groups())
    elif re.fullmatch(r"#[0-9a-fA-F]{6}", color or ""):
        r, g, b = (int(color[i : i + 2], 16) / 255 for i in (1, 3, 5))
    else:
        return color
    h, l, sat = colorsys.rgb_to_hls(r, g, b)
    if sat < 0.15 or l < 0.12:
        return "灰色" if l > 0.25 else "黑色"
    deg = h * 360
    for limit, word in (
        (15, "红色"),
        (40, "橙色"),
        (65, "黄色"),
        (160, "绿色"),
        (200, "青色"),
        (255, "蓝色"),
        (330, "紫色"),
        (361, "红色"),
    ):
        if deg < limit:
            return "棕色" if word in ("橙色", "红色") and l < 0.45 and deg > 10 else word
    return color


def _warn_marker_colors(slug, svg):
    """Gantt today/milestone marks use the palette accent: say which colour, so a caption does not guess."""
    import re
    import warnings

    if slug != "gantt":
        return
    m = re.search(r'data-role="today-marker" data-color="([^"]+)"', svg)
    if m:
        warnings.warn(
            f"chart_slide('gantt'): 今天线 = {_hue_name(m.group(1))}虚线 ({m.group(1)})，里程碑菱形同色；"
            "图注/讲稿按这个颜色写",
            stacklevel=3,
        )


def _warn_category_quantity(slug, kwargs):
    """scatter/line_band with category x like "293 K / 77 K / 4.2 K": a physical quantity belongs on a numeric axis."""
    import warnings

    if slug not in ("scatter", "line_band", "scatter_fit"):
        return
    series = kwargs.get("points") if slug != "line_band" else kwargs.get("series")
    xs = []
    for s in series or []:
        if isinstance(s, dict):
            for p in list(s.get("points") or []) + list(s.get("curve") or []):
                if isinstance(p, dict) and isinstance(p.get("x"), str):
                    xs.append(p["x"])
    cats = list(dict.fromkeys(xs))
    parsed = _numeric_categories(cats) if cats else None
    if parsed:
        values, _, suffix = parsed
        if suffix:
            warnings.warn(
                f"chart_slide({slug!r}): x 是带单位的数值类别 {cats[:3]}——物理量用数值 x（x={values[0]:g}…，"
                f"x_unit={suffix!r}，必要时 x_transform='log10'），间距才按真实比例",
                stacklevel=3,
            )


def _warn_threshold_p(slug, kwargs):
    import warnings

    found = _threshold_p_values(kwargs)
    if found:
        warnings.warn(
            f"chart_slide({slug!r}): p={found[0]:g} 恰好是常用阈值——原文若写的是 P<{found[0]:g}，"
            f"请传字符串 p='<{found[0]:g}'（否则图上印成 P={found[0]:g}）",
            stacklevel=3,
        )


_META_WORDS = ("合并", "汇总", "总体", "总计", "pooled", "overall", "meta", "summary", "random", "fixed")
_EFFECT_RE = None


def _effect_measures(texts):
    """Ratio effect measures named in the texts (aHR→HR, aOR→OR), by whole-word tokens."""
    import re

    global _EFFECT_RE
    if _EFFECT_RE is None:
        _EFFECT_RE = re.compile(r"(?<![A-Za-z])a?(HR|OR|IRR|RR)(?![A-Za-z])")
    return sorted({m.group(1) for t in texts if t for m in _EFFECT_RE.finditer(str(t))})


def _has_any(rows, keys):
    return any(isinstance(r, dict) and any(r.get(k) is not None for k in keys) for r in rows)


def _forest_axis_advice(kwargs):
    """Auto log axis for forest estimates spanning >10x on a default linear axis; returns (kwargs, warning or None)."""
    explicit = (
        "log_x",
        "logx",
        "xscale",
        "x_scale",
        "value_domain",
        "value_min",
        "value_max",
        "xlim",
        "x_min",
        "x_max",
    )
    rows = [r for r in kwargs.get("rows") or [] if isinstance(r, dict) and not r.get("is_subgroup_header")]
    if any(kwargs.get(k) is not None for k in explicit) or not rows:
        return kwargs, None
    mid = next(
        (kwargs[k] for k in ("midline_value", "reference", "ref_line", "null_value") if kwargs.get(k) is not None), 1
    )
    try:
        if float(mid) <= 0:
            return kwargs, None
        values = [float(r[k]) for r in rows for k in ("estimate", "ci_lo", "ci_hi") if r.get(k) is not None]
        estimates = [float(r["estimate"]) for r in rows if r.get("estimate") is not None]
    except (TypeError, ValueError):
        return kwargs, None
    # Same rule as make_forest(log_x=None): ratios whose estimates or CI limits span > 10x read on a log axis.
    if len(estimates) < 2 or min(values) <= 0 or max(values) / min(values) <= 10:
        return kwargs, None
    span = max(values) / min(values)
    return dict(kwargs, log_x=True), (
        f"chart_slide('forest'): 估计值/CI 跨 {span:.0f}×，已自动改用对数轴 log_x=True；"
        "要线性轴请显式传 log_x=False 或 value_domain"
    )


def _paper_mark_advice(slug, kwargs, svg):
    """One short line naming the paper marks (CI / P / n / reference) the chart still lacks, else None."""
    rows = [r for r in kwargs.get("rows") or [] if isinstance(r, dict)] if isinstance(kwargs.get("rows"), list) else []
    if slug == "forest" and rows and 'data-forest-ci="none"' not in svg:
        data = [r for r in rows if not r.get("is_subgroup_header")]
        if not _has_any(data, ("n", "events", "p")):
            labels = " ".join(str(r.get("label", "")) for r in data).lower()
            meta = any(w in labels for w in _META_WORDS) and not any(r.get("is_overall") for r in data)
            return "chart_slide('forest'): 各行无 n/events/p——来源报告了就逐行填入" + (
                "；合并/总体行设 is_overall=True 画菱形" if meta else ""
            )
    if (
        slug == "dumbbell"
        and rows
        and not _has_any(rows, ("before_lo", "before_hi", "after_lo", "after_hi", "delta_ci", "p", "n"))
    ):
        return "chart_slide('dumbbell'): 只有两端点值——来源报告了就加 before_lo/before_hi、after_lo/after_hi、p、n"
    if slug == "coef_plot" and rows and not _has_any(rows, ("lo", "hi", "ci_lo", "ci_hi")):
        return (
            "chart_slide('coef_plot'): 只有点估计，无区间不宜用系数图——来源有 CI 就传 lo/hi，"
            "否则改 dumbbell / 点图并在 note 注明未报告 CI"
        )
    if slug == "scatter":
        pts = kwargs.get("points") or []
        series = [s for s in pts if isinstance(s, dict) and "points" in s]
        if series:
            total = sum(len(s.get("points") or []) for s in series)
            curve = any(s.get("curve") for s in series)
        else:
            total, curve = len(pts), False
        if 0 < total < 5 and not curve:
            return (
                f"chart_slide('scatter'): 仅 {total} 个点且无曲线——来源有曲线/时间序列就用 curve 画全，"
                "否则把数字写成正文"
            )
    if slug == "grouped_bar" and not kwargs.get("reference_lines") and kwargs.get("stack") in (None, "none"):
        try:
            from svg_lib.charts._grouped_adaptive import coerce_series

            series = coerce_series(list(kwargs.get("series") or []))
        except Exception:
            return None
        if len(series) == 1:
            values = _summary_values(series[0]["values"] if isinstance(series[0], dict) else series[0][1])
            if values is not None:
                return (
                    "chart_slide('grouped_bar'): 单系列纯柱——有基线/目标值加 reference_lines=[{value,label}]，"
                    "或改点图 coef_plot(rows=)"
                )
    return None


def _render_png(svg, path, width):
    """PNG of the chart exactly as placed (preview=); same renderers as Drawing.preview."""
    import shutil, subprocess, tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "chart.svg"
        src.write_text(str(svg), encoding="utf-8")
        if shutil.which("rsvg-convert"):
            subprocess.run(["rsvg-convert", "-w", str(width), "-b", "white", str(src), "-o", str(path)], check=True)
            return path
        try:
            import cairosvg

            cairosvg.svg2png(url=str(src), write_to=str(path), output_width=width, background_color="white")
            return path
        except ImportError:
            pass
        if shutil.which("qlmanage"):
            subprocess.run(["qlmanage", "-t", "-s", str(width), "-o", tmp, str(src)], check=True, capture_output=True)
            shutil.move(str(Path(tmp) / "chart.svg.png"), str(path))
            return path
    raise RuntimeError("no SVG renderer found (rsvg-convert / cairosvg / qlmanage)")


_PAIR_WORDS = (
    ("前", "后"),
    ("改性前", "改性后"),
    ("未改性", "改性后"),
    ("未改性", "改性"),
    ("对照", "处理"),
    ("对照组", "实验组"),
    ("基线", "随访"),
    ("治疗前", "治疗后"),
    ("before", "after"),
    ("pre", "post"),
    ("baseline", "follow"),
    ("control", "treated"),
    ("control", "treatment"),
    ("wt", "mutant"),
    ("野生型", "突变"),
)


def _summary_values(cells):
    """Plain summary values of grouped_bar cells, or None if any cell carries replicates/intervals."""
    out = []
    for cell in cells:
        if isinstance(cell, bool) or cell is None:
            return None
        if isinstance(cell, (int, float)):
            out.append(float(cell))
        elif isinstance(cell, dict) and set(cell) <= {"value", "n"} and isinstance(cell.get("value"), (int, float)):
            out.append(float(cell["value"]))
        elif isinstance(cell, (list, tuple)) and len(cell) == 1 and isinstance(cell[0], dict):
            sub = _summary_values(cell)
            if sub is None:
                return None
            out.extend(sub)
        else:
            return None
    return out


_NUM_IN_LABEL = None


def _numeric_categories(cats):
    """(x values, prefix, suffix) when every label is one shared template around a single number, else None."""
    import re

    global _NUM_IN_LABEL
    if _NUM_IN_LABEL is None:
        _NUM_IN_LABEL = re.compile(r"(?<![A-Za-z0-9_.])([-+−]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)(?![0-9A-Za-z_])")
    if len(cats) < 3:
        return None
    xs, templates = [], set()
    for label in cats:
        found = _NUM_IN_LABEL.findall(label)
        if len(found) != 1:
            return None
        xs.append(float(found[0].replace("−", "-")))
        templates.add(" ".join(_NUM_IN_LABEL.sub("#", label, count=1).split()))
    if len(templates) != 1 or len(set(xs)) != len(xs):
        return None
    raw_prefix, raw_suffix = templates.pop().split("#", 1)
    strip = " =:：,，()（）[]"
    prefix, suffix = raw_prefix.strip(strip), raw_suffix.strip(strip)
    # A variable = value ("ε=1"), a bare number ("1", "10 epochs") or a short unit ("303 K") is a numeric x;
    # names that merely carry an index ("Group 1", "Phase 2", "Cu(100)") stay categorical.
    if not (
        raw_prefix.rstrip().endswith(("=", ":", "："))
        or not prefix
        or (suffix and len(suffix) <= 8 and len(prefix) <= 3 and not raw_prefix.rstrip().endswith(("(", "（")))
    ):
        return None
    return xs, prefix, suffix


_RATIO_RE = None


def _is_ratio(texts):
    """Axis/series text names a ratio or fold change (1 = no change), by whole-word tokens only."""
    import re

    global _RATIO_RE
    if _RATIO_RE is None:
        _RATIO_RE = (
            re.compile(r"(?<![A-Za-z])(?:BAF|TMF|BCF|OR|HR|RR|IRR|aOR|aHR)(?![A-Za-z])"),
            re.compile(r"(?<![A-Za-z])(?:fold|ratio|ratios)(?![A-Za-z])", re.I),
            re.compile(r"比值|比率|倍数|(?<!加)倍(?!率)"),
        )
    text = " ".join(str(t) for t in texts if t)
    return any(rx.search(text) for rx in _RATIO_RE)


_ENDPOINTS = (
    ("survival", r"(?<![A-Za-z])(?:OS|PFS|DFS|EFS|RFS|TTP)(?![A-Za-z])|生存|无进展|无病"),
    ("response", r"(?<![A-Za-z])(?:ORR|DCR|CR|PR|pCR|MRD)(?![A-Za-z])|缓解|应答|有效率|客观反应"),
    ("safety", r"(?<![A-Za-z])(?:AEs?|TRAEs?|SAEs?|CRS)(?![A-Za-z])|不良事件|不良反应|毒性"),
)


def _mixed_endpoints(cats):
    """Short description when categories put different endpoints or units on one axis, else None."""
    import re

    hits = {}
    for label in cats:
        for kind, pattern in _ENDPOINTS:
            if re.search(pattern, label, re.I if kind != "response" else 0):
                hits.setdefault(kind, label)
    if len(hits) >= 2:
        return " vs ".join(repr(v) for v in hits.values())
    units = {}
    for label in cats:
        m = re.search(r"[（(]([^()（）]{1,12})[)）]\s*$", label)
        if m:
            units.setdefault(m.group(1).strip(), label)
    return (
        " vs ".join(repr(v) for v in units.values())
        if len(units) >= 2
        and len(units) == len([c for c in cats if re.search(r"[（(][^()（）]{1,12}[)）]\s*$", c)])
        and len(units) * 2 > len(cats)
        else None
    )


def _accepts(slug, name):
    import inspect

    try:
        return name in inspect.signature(globals()["make_" + slug]).parameters
    except (KeyError, TypeError, ValueError):
        return False


_ENRICH = {
    "dumbbell": "add before_lo/before_hi/after_lo/after_hi, p and n per row when the source reports them "
    "(never invent them)",
    "coef_plot": "add lo/hi per row when the source reports a CI or range (not a midpoint), n/p if reported, and "
    "benchmark= per row for a target value or historical control",
    "scatter": "add lo/hi to curve points (or y_err) when the source reports them, and "
    "reference_lines=[{'value': …, 'label': …, 'axis': 'y'}] for a baseline or target",
    "grouped_bar": "add {'value': v, 'lo': a, 'hi': b} cells when the source reports intervals",
}


def _bar_upgrade(kwargs):
    """A better academic chart for grouped_bar data that is really a curve / paired / ranked comparison, else None."""
    if any(
        kwargs.get(k) not in (None, "none", "auto", False)
        for k in ("stack", "line_series", "axis_break", "pairwise_p", "auto_test")
    ) or kwargs.get("multi_mode") not in (None, "auto"):
        return None
    try:
        from svg_lib.charts._grouped_adaptive import coerce_series

        series = coerce_series(list(kwargs.get("series") or []))
    except Exception:
        return None
    cats = [str(c) for c in kwargs.get("categories") or []]
    named = [
        (str(s["name"] if isinstance(s, dict) else s[0]), _summary_values(s["values"] if isinstance(s, dict) else s[1]))
        for s in series
    ]
    if not cats or any(v is None or len(v) != len(cats) for _, v in named):
        return None
    common = {
        k: kwargs[k]
        for k in ("title", "subtitle", "note", "source", "palette", "font_family", "width", "height")
        if k in kwargs
    }
    axis = kwargs.get("y_title") or kwargs.get("y_unit") or ""
    explicit_axis = any(
        kwargs.get(k) is not None for k in ("value_domain", "y_min", "y_max", "ylim", "x_min", "x_max", "xlim")
    )
    scale = kwargs.get("value_scale")
    numeric = _numeric_categories(cats)
    if numeric is not None and not explicit_axis and (scale != "log" or all(v > 0 for _, vs in named for v in vs)):
        xs, prefix, suffix = numeric
        log_x = min(xs) > 0 and max(xs) / min(xs) > 20
        order = sorted(range(len(xs)), key=xs.__getitem__)
        curves = []
        for name, values in named:
            pts = [{"x": xs[i], "y": values[i]} for i in order]
            curves.append({"name": name, "points": pts, "curve": [dict(p) for p in pts]})
        unit_like = suffix and len(suffix) <= 5
        x_title = kwargs.get("x_title") or prefix or (None if unit_like else suffix) or None
        new = dict(
            common,
            points=curves,
            x_title=x_title,
            y_title=kwargs.get("y_title"),
            y_unit=kwargs.get("y_unit") or "",
            x_transform="log10" if log_x else "linear",
            y_transform="log10" if scale == "log" else "linear",
            fit=None,
            show_ci=False,
        )
        if unit_like and not kwargs.get("x_unit"):
            new["x_unit"] = suffix
        refs = [dict(r, axis=r.get("axis", "y")) for r in kwargs.get("reference_lines") or [] if isinstance(r, dict)]
        if _is_ratio([kwargs.get("y_title"), kwargs.get("y_unit")] + [n for n, _ in named]) and not any(
            r.get("value") == 1 for r in refs
        ):
            refs.append({"value": 1, "label": "1", "axis": "y"})
        if refs:
            new["reference_lines"] = refs
        shown = ", ".join(cats[:3]) + (", …" if len(cats) > 3 else "")
        return (
            "scatter",
            new,
            (
                f"categories are numeric ({shown} → x = {min(xs):g} … {max(xs):g}"
                + ("; log x axis" if log_x else "")
                + "), so each series is a curve over x"
            ),
        )
    ratio = _is_ratio([kwargs.get("y_title"), kwargs.get("y_unit")] + [n for n, _ in named])
    single = named[0][1] if len(named) == 1 else None
    log_flag = next(
        (
            (f, v)
            for f, v in (("value_scale", "log"), ("x_scale", "log"), ("log_x", True), ("x_transform", "log10"))
            if _accepts("coef_plot", f)
        ),
        None,
    )
    span = max(single) / min(single) if single and min(single) > 0 else None
    # A ratio dot plot needs a log axis once values span decades; without one, the log grouped_bar rule below wins.
    if ratio and span and len(cats) >= 2 and (span <= 10 or log_flag or scale == "linear" or explicit_axis):
        values = single
        rows = [{"label": c, "estimate": v} for c, v in zip(cats, values)]
        extra = {k: kwargs[k] for k in ("y_min", "y_max", "ylim") if kwargs.get(k) is not None}
        if kwargs.get("value_domain"):
            extra = {"value_min": kwargs["value_domain"][0], "value_max": kwargs["value_domain"][1]}
        if scale != "linear" and span > 3 and log_flag:
            extra[log_flag[0]] = log_flag[1]
        return (
            "coef_plot",
            dict(common, rows=rows, x_title=axis or named[0][0], reference=1, **extra),
            (
                f"the values are ratios / fold changes ({axis or named[0][0]!r}); 1 means no change, so a dot plot "
                "against the line at 1 reads correctly where bars from 0 do not"
            ),
        )
    if len(named) == 2 and len(cats) >= 2:
        (a, va), (b, vb) = named
        rows = [{"label": c, "before": x, "after": y} for c, x, y in zip(cats, va, vb)]
        pair = any(a.lower().startswith(p) and b.lower().startswith(q) for p, q in _PAIR_WORDS)
        reason = (
            f"two series ({a!r} → {b!r}) per category is a paired before/after comparison"
            if pair
            else f"two series ({a!r} vs {b!r}) per category is a two-condition comparison"
        )
        return "dumbbell", dict(common, rows=rows, series_labels=(a, b), x_title=axis or None), reason
    if len(named) == 1 and len(cats) >= 3:
        values = named[0][1]
        lo, hi = min(values), max(values)
        rows = [{"label": c, "estimate": v} for c, v in zip(cats, values)]
        if lo > 0 and hi / lo > 10 and kwargs.get("value_scale") in (None, "auto") and not explicit_axis:
            return (
                "grouped_bar",
                dict(kwargs, value_scale="log"),
                f"values span {hi / lo:.0f}× — on a linear axis the small bars vanish, so the value axis is logarithmic",
            )
        if lo > 0 and (hi - lo) / hi < 0.15:
            extra = {}
            domain = kwargs.get("value_domain")
            if domain:
                extra = {"value_min": domain[0], "value_max": domain[1]}
            return (
                "coef_plot",
                dict(common, rows=rows, x_title=axis or named[0][0], reference=None, **extra),
                f"values lie within {(hi - lo) / hi:.0%} of each other — bars start at 0 and look equal; a dot plot on a tight axis shows the differences",
            )
    return None


def chart_slide(
    slug, x=None, y=None, width=None, height=None, *, box=None, editable=True, preview=None, upgrade=True, **kwargs
):
    # Charts whose data is named x/y (e.g. spectrum) must pass box=(x, y, w, h).
    """Render chart ``slug`` for a slide box and return an SML fragment for compose_slide."""
    import inspect
    import re
    import warnings
    from svg_lib.chart_split import split_chart_svg

    if isinstance(x, (tuple, list)) and len(x) == 4 and box is None and y is None:
        box, x = x, None  # chart_slide(slug, (x, y, w, h), ...)
    if box is not None:
        for name, value in (("x", x), ("y", y)):
            if value is not None:
                kwargs[name] = value
        x, y, width, height = box
    functions = _chart_functions()
    if slug == "academic_bar_chart":
        kwargs = _drop_ring_kwargs(kwargs)
    slug = _canonical_slug(slug)
    if isinstance(slug, str) and slug.lstrip().startswith("<svg"):
        raise TypeError(
            "chart_slide's first argument is the chart name, not an SVG: "
            "chart_slide('grouped_bar', x, y, w, h, categories=..., series=...) builds and places the chart "
            "(no make_* call needed)"
        )
    if slug not in functions:
        import difflib

        close = difflib.get_close_matches(str(slug), list(functions), n=3, cutoff=0.5)
        raise ValueError(
            f"Unknown chart {slug!r}"
            + (f" (did you mean {', '.join(map(repr, close))}?)" if close else "")
            + f". Available: {', '.join(functions)}"
        )
    if None in (x, y, width, height):
        raise TypeError(
            f"chart_slide({slug!r}, x, y, width, height, **data) needs the slide box (or box=(x, y, w, h)); "
            "the chart's own options (title=, categories=…) go after it as keywords"
        )
    if slug == "grouped_bar":
        mixed = _mixed_endpoints([str(c) for c in kwargs.get("categories") or []])
        if mixed:
            warnings.warn(
                f"chart_slide('grouped_bar'): categories mix different endpoints ({mixed}); split into "
                "separate charts or use coef_plot rows with benchmark",
                stacklevel=2,
            )
    upgraded = False
    if slug == "forest":
        measures = _effect_measures(
            [kwargs.get("x_title"), kwargs.get("xlabel")]
            + [r.get("label") for r in kwargs.get("rows") or [] if isinstance(r, dict)]
        )
        if len(measures) >= 2:
            warnings.warn(
                f"chart_slide('forest'): 混用效应量 {'/'.join(measures)}——不同效应量不能共用一条轴，"
                "按效应量拆成多张 forest",
                stacklevel=2,
            )
        kwargs, log_note = _forest_axis_advice(kwargs)
        if log_note:
            warnings.warn(log_note, stacklevel=2)
        if kwargs.get("favours") and kwargs.get("midline_value", 1.0) == 0:
            warnings.warn(
                f"chart_slide('forest'): midline_value=0（差值类效应量 d/SMD/MD），favours="
                f"{tuple(kwargs['favours'])!r} 按 (左, 右) 显示——差值类效应量右侧通常=干预更优"
                "（与 HR/OR 左侧更优相反）；请确认 favours 顺序与效应方向一致",
                stacklevel=2,
            )
    if slug == "grouped_bar" and upgrade:  # upgrade=False: legacy, deliberately undocumented
        better = _bar_upgrade(kwargs)
        upgraded = better is not None
        if better is not None:
            new_slug, new_kwargs, reason = better
            if new_slug == "grouped_bar":
                warnings.warn(f"chart_slide('grouped_bar'): {reason}; {_ENRICH['grouped_bar']}", stacklevel=2)
            else:
                warnings.warn(
                    f"chart_slide('grouped_bar') → drew {new_slug!r} instead: {reason}. To enrich it, "
                    f"{_ENRICH[new_slug]}; to write it directly: chart_slide({new_slug!r}, x, y, w, h, "
                    + ", ".join(
                        f"{k}=…"
                        for k in new_kwargs
                        if k
                        in ("rows", "points", "series_labels", "x_title", "reference", "x_transform", "reference_lines")
                    )
                    + ")",
                    stacklevel=2,
                )
            slug, kwargs = new_slug, new_kwargs
    if (
        slug == "grouped_bar"
        and _accepts("grouped_bar", "reference_lines")
        and _is_ratio(
            [kwargs.get("y_title"), kwargs.get("y_unit"), kwargs.get("ylabel")]
            + [
                s.get("name") if isinstance(s, dict) else (s[0] if isinstance(s, (list, tuple)) and s else None)
                for s in kwargs.get("series") or []
            ]
        )
    ):
        refs = list(kwargs.get("reference_lines") or [])
        if not any(isinstance(r, dict) and r.get("value") == 1 for r in refs):
            kwargs = dict(kwargs, reference_lines=refs + [{"value": 1, "label": "1"}])
    make = globals()["make_" + slug]
    params = inspect.signature(make).parameters
    for key, value in (("width", width), ("height", height)):
        if key in params and key not in kwargs:
            kwargs[key] = value
    if "font_family" in params and not kwargs.get("font_family"):
        # Slides read in the deck's CJK sans; the library's journal serif body would show
        # as a serif English fallback in any layer that stays SVG.
        kwargs["font_family"] = SLIDE_CHART_FONT
    explicit_card = any(kwargs.get(k) is not None for k in ("background", "bg"))
    svg, notice = _render_fitting(make, params, kwargs, width, height)
    if not explicit_card:
        svg = _drop_canvas_background(svg)
    vw, vh = (float(v) for v in re.search(r'viewBox="([^"]+)"', svg).group(1).replace(",", " ").split()[2:])
    scale = min(width / vw, height / vh)
    w, h = vw * scale, vh * scale
    left, top = x + (width - w) / 2, y + (height - h) / 2
    if scale < 0.999:
        import warnings

        rows = ", ".join(f"{int(k * 100)}%: {vw * k:.0f}x{vh * k:.0f}" for k in (1, 0.8, 0.7, 0.6))
        warnings.warn(
            f"chart_slide({slug!r}): data needs a {vw:.0f}x{vh:.0f} canvas; already fitted into your "
            f"{width:g}x{height:g} box at {scale:.0%} scale (vector, still editable — nothing to fix). "
            f"Box size for a given scale: {rows}"
            + (
                "; below ~70% labels get crowded, so give the chart a larger box if the layout allows."
                if scale < 0.7
                else "."
            ),
            stacklevel=2,
        )
    if editable is False and _os.environ.get("CHART_SLIDE_ALLOW_EMBED") != "1":
        import warnings

        warnings.warn(
            f"chart_slide({slug!r}): editable=False is ignored — slide charts are always semi-editable "
            "(native text, recolorable blocks); publish_slide already waives conversion overlaps",
            stacklevel=2,
        )
        editable = True
    marks = len(re.findall(r'data-role="(?:before|after|bar|point|estimate|marker)"', svg))
    rows = kwargs.get("rows") if isinstance(kwargs.get("rows"), list) else None
    if (rows is not None and len(rows) < 3) or (rows is None and 0 < marks < 3):
        import warnings

        warnings.warn(
            f"chart_slide({slug!r}): only {len(rows) if rows is not None else marks} data row(s) — a chart "
            "this thin carries little evidence; show the numbers as large native figures in the text, or add "
            "comparable rows (other studies, conditions, years) from the literature",
            stacklevel=2,
        )
    _warn_wide_bar_range(slug, svg, kwargs)
    _warn_narrow_bar_range(slug, svg, kwargs)
    _warn_forest_without_ci(slug, svg, kwargs)
    _warn_threshold_p(slug, kwargs)
    _warn_category_quantity(slug, kwargs)
    _warn_marker_colors(slug, svg)
    advice = None if upgraded else _paper_mark_advice(slug, kwargs, svg)
    if advice:
        warnings.warn(advice, stacklevel=2)
    if preview:
        _render_png(svg, preview, int(w * 2))
    if editable:
        return split_chart_svg(svg, x=left, y=top, width=w)
    svg = svg.replace('data-chart-lib="1"', 'data-chart-lib="0"', 1)
    return f'<embed topLeftX="{left:.2f}" topLeftY="{top:.2f}" width="{w:.2f}" height="{h:.2f}">{svg}</embed>'


def chart_fit(slug, width, height, **kwargs):
    """How a chart would sit in a width×height slide box — without placing it."""
    import inspect
    import re
    import warnings

    functions = _chart_functions()
    if slug == "academic_bar_chart":
        kwargs = _drop_ring_kwargs(kwargs)
    slug = _canonical_slug(slug)
    if slug not in functions:
        raise ValueError(f"Unknown chart {slug!r}. Available: {', '.join(functions)}")
    make = globals()["make_" + slug]
    params = inspect.signature(make).parameters
    for key, value in (("width", width), ("height", height)):
        if key in params and key not in kwargs:
            kwargs[key] = value
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        svg, _ = _render_fitting(make, params, kwargs, width, height)
    vw, vh = (float(v) for v in re.search(r'viewBox="([^"]+)"', svg).group(1).replace(",", " ").split()[2:])
    scale = min(width / vw, height / vh)
    return {
        "scale": round(scale, 3),
        "canvas": (round(vw), round(vh)),
        "box_for": {f"{int(k * 100)}%": (round(vw * k), round(vh * k)) for k in (1, 0.8, 0.7)},
    }


_ELSEWHERE = {
    # name → where it actually lives (the import a caller should write)
    "chart_slide": "from scripts.gen_svg_charts import chart_slide",
    "chart_help": "from scripts.gen_svg_charts import chart_help",
    "chart_fit": "from scripts.gen_svg_charts import chart_fit",
    "publish_slide": "from scripts.svg_lib.atomize_svg_to_slide import publish_slide",
    "native_text": "from scripts.svg_lib.atomize_svg_to_slide import native_text",
    "native_table": "from scripts.svg_lib.atomize_svg_to_slide import native_table",
    "native_bullets": "from scripts.svg_lib.atomize_svg_to_slide import native_bullets",
    "page_frame": "from scripts.svg_lib.atomize_svg_to_slide import page_frame",
    "native_line": "from scripts.svg_lib.atomize_svg_to_slide import native_line",
    "compose_slide": "from scripts.svg_lib.atomize_svg_to_slide import compose_slide",
    "Drawing": "from scripts.svg_lib.svg_drawing import Drawing",
    "drawing_help": "from scripts.svg_lib.svg_drawing import drawing_help",
    "svg_at": "svg_at is a Drawing method: d = Drawing(w, h); d.svg_at(at, svg, size=...)",
    "box_at": "box_at is a Drawing method: d.box_at(at, text, font_size=...)",
    "text_at": "text_at is a Drawing method: d.text_at(at, text, font_size=...)",
    "arrow": "arrow is a Drawing method: d.arrow(node_a, node_b)",
    "relation_help": "from scripts.gen_svg_relations import relation_help",
    "make_relation_atomized": "from scripts.gen_svg_relations import make_relation_atomized",
}


def __getattr__(name):
    """A name imported from the neighbouring module resolves to the real one (the wrong import line still works)."""
    hint = _ELSEWHERE.get(name)
    if hint and hint.startswith("from "):
        import importlib

        module, attr = hint[5:].split(" import ")
        return getattr(importlib.import_module(module), attr)
    if hint:
        raise ImportError(f"{name!r} is not importable from {__name__}; {hint}")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _cli():
    functions = _chart_functions()
    parser = argparse.ArgumentParser(description="Generate a self-contained, data-driven SVG chart.")
    parser.add_argument("--type", required=True, choices=sorted(functions))
    parser.add_argument(
        "--data-file", help="JSON keyword arguments for any chart; optional args list for positional data"
    )
    # Retain legacy file flags while routing their payloads through the same functions.
    file_arguments = {
        "matrix": "calheat",
        "distributions": "ridge",
        "ohlc": "candle",
        "groups": "boxplot",
        "sankey": "sankey",
        "grid": "percent_grid",
        "waterfall": "waterfall",
        "gantt": "gantt",
        "pyramid": "population_pyramid",
        "timeline": "event_timeline",
        "marimekko": "marimekko",
        "matheat": "matrix_heat",
        "quadrant": "quadrant_2x2",
        "violin": "violin",
    }
    for flag in file_arguments:
        parser.add_argument(f"--{flag}-file")
    parser.add_argument("--values")
    parser.add_argument("--stages")
    parser.add_argument("--descriptions")
    parser.add_argument("--footer")
    parser.add_argument("--labels")
    parser.add_argument("--highlight")
    parser.add_argument("--unit", default="")
    args = parser.parse_args()
    function = functions[args.type]

    def load(path):
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)

    if args.data_file:
        payload = load(args.data_file)
        if not isinstance(payload, dict):
            parser.error("--data-file must contain a JSON object of function arguments")
        payload = dict(payload)
        positional = payload.pop("args", [])
        if not isinstance(positional, list):
            parser.error("args must be a JSON list")
        print(function(*positional, **payload))
        return

    selected = next(
        (flag for flag, slug in file_arguments.items() if slug == args.type and getattr(args, f"{flag}_file")), None
    )
    labels = args.labels.split(",") if args.labels else None
    if selected:
        payload = load(getattr(args, f"{selected}_file"))
        if isinstance(payload, dict):
            print(function(**payload))
            return
        options = {}
        if args.type == "calheat":
            options["matrix"] = payload
        elif args.type == "ridge":
            options.update(distributions=payload, group_labels=labels)
        elif args.type == "candle":
            options.update(ohlc=payload, date_labels=labels, y_unit=args.unit)
        elif args.type == "boxplot":
            options.update(groups=payload, y_unit=args.unit, highlight_group=args.highlight)
        elif args.type == "percent_grid":
            options.update(options=payload, footer=args.footer)
        elif args.type == "waterfall":
            options["steps"] = payload
        else:
            parser.error(f"--{selected}-file must contain a JSON object")
        print(function(**options))
        return
    if args.type == "calheat" and args.values:
        print(function(values=[float(value) for value in args.values.split(",")]))
        return
    if args.type == "funnel_classic" and args.stages:
        options = {"stages": [float(value) for value in args.stages.split(",")]}
        if labels:
            options["stage_labels"] = labels
        if args.descriptions:
            options["stage_descriptions"] = args.descriptions.split(";")
        if args.footer:
            options["footer"] = args.footer
        print(function(**options))
        return
    parser.error(f"--type {args.type} requires --data-file <kwargs.json> or its legacy input flag")


if __name__ == "__main__":
    _cli()
