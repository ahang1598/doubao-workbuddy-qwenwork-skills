#!/usr/bin/env python3
"""
gen_svg_charts.py · 多张 SVG 高级图表的生成器
按参数生成对应 SVG 字符串（不带 <embed> 外壳，方便模型直接嵌入）。

支持的 chart 类型：
  calheat            日历热力          参数：values（≤ 364 一维）或 matrix（52×7），可选 title/subtitle/kpis/note/source
  ridge              山脊图（多组分布）参数：distributions（N 组，每组是 pdf/hist 数值列表），可选 title/subtitle/highlight_index
  candle             K 线蜡烛图        参数：ohlc（[(open,high,low,close), ...] N 根）
  boxplot            箱线图            参数：groups（[(name, [values...])] N 组）
  sankey             桑基流            参数：left_nodes, right_nodes, flows（守恒自动校验）
  funnel_classic     经典梯形漏斗      参数：stages, stage_labels, stage_descriptions（每层一句描述）
  percent_grid       百人网格          参数：options（[(label, count_out_of_100), ...] 2..8 类），可选 title/subtitle/kpis 语义分组
  waterfall          瀑布图            参数：steps（[(name, value, kind), ...] kind='total'/'pos'/'neg'）
  gantt              甘特图            参数：tasks（[(name, start_week, end_week), ...]）, critical_index, milestones
  population_pyramid 人口金字塔        参数：categories, left_values, right_values，可选 title/kpis/median_index/peak_index/age_group_dividers
  event_timeline     事件时间轴        参数：years, events（[(index, side, title, sub, is_highlight), ...]）
  marimekko          马赛克图          参数：markets（[(name, width_share, [(sub, share), ...]), ...]）
  matrix_heat        矩阵热力          参数：matrix（N×N，传 -1 或 None 的格子会渲染为空白）, labels, highlight_pair
  quadrant_2x2       2×2 象限图        参数：items（[(name, x, y), ...]，x/y ∈ [0,1]）, x_axis, y_axis, x_title, y_title, highlight_index
  violin             小提琴分布        参数：groups（[(name, [values...])] N 组），可选 title/subtitle/y_axis_label/highlight_group/y_min/y_max

命令行用法：
  python3 gen_svg_charts.py --type calheat --matrix-file matrix.json
  python3 gen_svg_charts.py --type ridge --distributions-file dists.json
  python3 gen_svg_charts.py --type candle --ohlc-file ohlc.json --unit '$'
  python3 gen_svg_charts.py --type boxplot --groups-file groups.json --highlight Q3
  python3 gen_svg_charts.py --type sankey --sankey-file sankey.json
  python3 gen_svg_charts.py --type funnel_classic --stages '50,12,8,5,3,1' --labels '全市场,流动性,...' --descriptions '全球可交易品种;日均成交额...'
  python3 gen_svg_charts.py --type percent_grid --grid-file pg.json --footer 'ONE TICK = ONE RESPONDENT'
  python3 gen_svg_charts.py --type waterfall --waterfall-file wf.json
  python3 gen_svg_charts.py --type gantt --gantt-file gt.json
  python3 gen_svg_charts.py --type population_pyramid --pyramid-file pp.json
  python3 gen_svg_charts.py --type event_timeline --timeline-file et.json
  python3 gen_svg_charts.py --type marimekko --marimekko-file mk.json
  python3 gen_svg_charts.py --type matrix_heat --matheat-file mh.json
  python3 gen_svg_charts.py --type quadrant_2x2 --quadrant-file qd.json
  python3 gen_svg_charts.py --type violin --violin-file vl.json

Python 调用：
                              make_funnel_classic, make_percent_grid,
                              make_waterfall, make_gantt, make_population_pyramid,
                              make_event_timeline, make_marimekko,
                              make_matrix_heat, make_quadrant_2x2, make_violin)
  # 然后自己拼 <embed topLeftX=... topLeftY=... width=... height=...>{svg_str}</embed>

配色：所有 make_* 函数都接受统一 `palette` 参数（None / str / dict）。
      str 走 svg_palettes.PALETTES 查表（如 'archive_ink', 'nightlab', 'burgundy_analyst' ...），
      dict 直接传 {'ink', 'accent', 'secondary', 'bg', 'muted'} 五字段。
      None 时用中性默认色（rgba(28,28,26,x) 主色 + rgba(163,88,50,1) accent）。

embed 尺寸：SVG 内部 viewBox 由生成器决定（见 chart_help 里各图的具体尺寸）。
      slide 里 embed 的 topLeftX/Y/width/height 只要 aspect ratio 跟 viewBox 一致就不会裁；
      比例不同会自动从中心裁掉，若要保留某一侧用 <crop anchor="left|right|top|bottom">。
      想图占满整页 → embed 用大尺寸；想「左图右字」→ embed 用小尺寸（如 480×275、640×360）+ 旁边放 <shape type="text">。
"""

import math
import random
import json
import argparse
from typing import List, Sequence

# Ensure this file's directory (scripts/) is on sys.path so `svg_lib.*` resolves
# regardless of the caller's CWD or import path (e.g. `python3 -c "from scripts.gen_svg_charts import ..."`).
import os as _os, sys as _sys

_HERE = _os.path.dirname(_os.path.abspath(__file__))
if _HERE not in _sys.path:
    _sys.path.insert(0, _HERE)

# helpers moved to svg_lib/_common.py; re-export for legacy call sites
try:
    from svg_lib._common import *  # noqa: F401,F403
except ImportError:
    _sys.path.insert(0, _os.path.join(_HERE, "svg_lib"))
    from _common import *  # noqa: F401,F403


# Re-export make_* from svg_lib.charts (they live there now)
from svg_lib.charts.calheat import make_calheat  # noqa: F401
from svg_lib.charts.ridge import make_ridge  # noqa: F401
from svg_lib.charts.candle import make_candle  # noqa: F401
from svg_lib.charts.boxplot import make_boxplot  # noqa: F401
from svg_lib.charts.sankey import make_sankey  # noqa: F401
from svg_lib.charts.funnel import make_funnel_classic  # noqa: F401
from svg_lib.charts.percent_grid import make_percent_grid  # noqa: F401
from svg_lib.charts.waterfall import make_waterfall  # noqa: F401
from svg_lib.charts.gantt import make_gantt  # noqa: F401
from svg_lib.charts.pyramid import make_population_pyramid  # noqa: F401
from svg_lib.charts.event_timeline import make_event_timeline  # noqa: F401
from svg_lib.charts.marimekko import make_marimekko  # noqa: F401
from svg_lib.charts.matrix_heat import make_matrix_heat  # noqa: F401
from svg_lib.charts.quadrant import make_quadrant_2x2  # noqa: F401
from svg_lib.charts.violin import make_violin  # noqa: F401


# ============================================================
# 统一 palette 支持（所有 18 张图共用）
# ============================================================
# palette 参数接受：
#   - None: 用默认硬编码色（等价于 "archive_ink" 或未指定）
#   - str:  从 svg_palettes.PALETTES 查表（如 "burgundy_analyst"）
#   - dict: {"ink", "accent", "secondary", "bg", "muted"} 五字段自定义
# 派生字段（grid/connect/point_fill 等）由 chart 内部按需从 ink/accent 自动派生


# ============================================================
# svg_lib 分派（新骨架变体）
# ============================================================
# 每张 chart 有 5 个"骨架"变体（skeleton variants），来自 svg_lib.charts。
# 传统 make_<slug>(...) 保留为 baseline（variant=None 或 "classic"），
# 用户传其它变体名时走 svg_lib.draw_<chart>()。
#
# variant 映射：slug → (svg_lib module, [supported variants], default_variant)
# ==============================================================
# chart_help · 一次读取所有 chart 的调用范式
# ==============================================================

# (chart_slug, chart_name_cn, make_fn_name, scene_one_line, min_call_example, key_enum_or_pitfall)
_CHART_META = [
    (
        "calheat",
        "日历热力",
        "make_calheat",
        "52×7=364 天日度指标热度：一眼看某周/某月的密度、季节性；GitHub 风 + 学术印刷版式。",
        "make_calheat(values=[…364 个数值…], title='Daily activity, 2025', subtitle='commits per day · simulated', figure_label='FIGURE 4', kpis=[('TOTAL','1,986',''),('ACTIVE','320','of 365')], note='Each cell = one day; red circles = monthly peak.', source='Simulated.')",
        "values 长度 ≤ 364（不足自动补 0，多余截断）；matrix 必须严格 52×7 否则 raise；SVG viewBox 是**动态尺寸**（示例参数下典型 1261×316，加 kpis 后 1261×466，去掉 show_month_bars 后 1041×316），生成后先读 viewBox 再算 embed 的 width×height 保持一致；show_month_bars / show_colorbar / highlight_monthly_peak 都可关；红圈用固定 #C25D5D，与 palette 无关。",
    ),
    (
        "ridge",
        "山脊图",
        "make_ridge",
        '多组时间序列/分布纵向堆叠对比："某年整体分布右移"这种趋势。',
        "make_ridge(distributions=[[…], [...], ...], group_labels=['2019','2020','2021'], title='延迟分布逐年变化', subtitle='ms · 3 年对比')",
        "各组长度必须一致；原始样本先走 ridge_density_from_samples；SVG viewBox 宽固定 900，**高度随组数增长**（N=2 时 ≈188 → ratio 4.79；N=5 时 ≈290 → ratio 3.10；N=8 时 ≈392 → ratio 2.30），生成后先读 viewBox 再算 embed 的 width×height 保持一致。",
    ),
    (
        "candle",
        "K 线蜡烛图",
        "make_candle",
        "时序 OHLC：金融行情、月度波动区间；上涨白心描边、下跌主色实心。",
        "make_candle(ohlc=[(o,h,l,c), ...], date_labels=[...], y_unit='$', title='月度行情', subtitle='22 交易日')",
        "数据 round 到目标精度再传入（生成器不 round 数据标签）；SVG viewBox 1500×820（≈1.83:1），embed 保持这个 aspect ratio 即可（整页放大 vs 想留右侧文字栏用小尺寸如 600×328）。",
    ),
    (
        "boxplot",
        "箱线图",
        "make_boxplot",
        "多组分位数摘要（Q1/中位/Q3 + 须 + 离群点）：跨年、跨类别的离散度比较。",
        "make_boxplot(groups=[('Q1', [values...]), ('Q2', [values...])], y_unit='ms', highlight_group='Q3', title='响应延迟按季度', subtitle='4 季度 · 各 60 样本')",
        "每组样本量 ≥ 5；highlight_group 必须精确匹配某个 name；SVG viewBox 1200×720（≈1.67:1），embed 保持这个 aspect ratio 即可（整页放大 vs 想留右侧文字栏用 600×360 之类）。",
    ),
    (
        "sankey",
        "桑基流",
        "make_sankey",
        "量级流转——供应链上下游、预算分配、用户漏斗、能耗结构；两侧柱条厚度按流量。",
        "make_sankey(left_nodes=['A','B'], right_nodes=['X','Y'], flows=[('A','X',10), ('A','Y',5), ('B','X',3)], title='预算流转', subtitle='源 → 去向')",
        "自动守恒校验（左右 total 必须相等，否则 raise）；SVG viewBox 1200×760（≈1.58:1），embed 保持这个 aspect ratio 即可。",
    ),
    (
        "funnel_classic",
        "经典梯形漏斗",
        "make_funnel_classic",
        '分层筛选叙事——业务场景的"全体 → 精选组合"（投资标的、招聘、销售），数据量小（3-8 层）、每层需要一句解读时用本图。',
        "make_funnel_classic(stages=[50,12,8,5,3,1], stage_labels=['全市场','流动性',...], stage_descriptions=['全球可交易','日均成交额>1B',...], primary_rgb=(139,90,43), title='投资标的筛选', subtitle='6 层漏斗 · 50 → 1')",
        "**换品牌色必须传 primary_rgb=(r,g,b)**（字符串 recolor 摸不到）；SVG viewBox 1400×780（≈1.79:1），embed 保持这个 aspect ratio 即可（整页放大 vs 想留右侧文字栏用 640×356 之类）。",
    ),
    (
        "percent_grid",
        "百人网格",
        "make_percent_grid",
        '调研/问卷（"76% 支持"）、"多少人选了 X" 叙事；10×10 网格 + breakdown 累计条 + POS/NEU/NEG 大数字 + 侧栏图例。',
        "make_percent_grid(options=[('Enthusiastic',15),('Optimistic',28),('Neutral',22),('Concerned',25),('Fearful',10)], title='How the world feels about AI', subtitle='Each square = 1% · n=12,000', figure_label='FIGURE 11', positive_labels=['Enthusiastic','Optimistic'], neutral_label='Neutral', negative_labels=['Concerned','Fearful'], note='Grid filled left-to-right, top-to-bottom.')",
        "count ∈ [0,100] 且每项 int；sum(counts) ≤ 100 且当 <100 自动补空白类 '—'；options 类目数 2..8，越界 raise；positive/neutral/negative_labels 用 label 匹配；show_breakdown_band / show_kpi_row 可关；SVG viewBox 1400×800（≈1.75:1），embed 保持这个 aspect ratio 即可（整页放大 vs 想留右侧文字栏可以用 480×275 之类的小尺寸）；footer 是 note 的老名 alias。",
    ),
    (
        "waterfall",
        "瀑布图",
        "make_waterfall",
        '商业/财务的"毛→净"、MRR 变化归因、成本节余分解、预算差异分解；连接虚线让"跳台阶"感一眼可读。',
        "make_waterfall(steps=[('起点',100,'total'),('增A',20,'pos'),('减B',5,'neg'),('终点',115,'total')], title='MRR 变化归因', subtitle='Q1 → Q2 · 万美元')",
        "**kind 必须是 'total'/'pos'/'neg' 字符串，不接受布尔**；首尾 total 都要有；换主题色传 palette={'ink':..., 'accent':..., 'pos_bar':..., 'connect':..., 'grid':..., 'muted':...}（缺省项自动从 ink 派生半透明）；SVG viewBox 约 409×227（≈1.80:1），embed 保持这个 aspect ratio 即可。",
    ),
    (
        "gantt",
        "甘特图",
        "make_gantt",
        "项目管理/教育课程排期/产品迭代计划；关键路径主色高亮、里程碑菱形。",
        "make_gantt(tasks=[('设计',0,4),('开发',3,10),('测试',9,12)], weeks=16, critical_index=1, milestones=[(4,'评审')], title='项目排期', subtitle='16 周 · 关键路径高亮')",
        "milestones 只承载点事件（发布/评审），不放长任务；SVG viewBox 1620×980（≈1.65:1），embed 保持这个 aspect ratio 即可（整页放大 vs 想留右侧文字栏用 640×388 之类）。",
    ),
    (
        "population_pyramid",
        "人口金字塔",
        "make_population_pyramid",
        '"人口结构"、"两组人群对比"（男女、公私立、城乡、党团、前测后测）；顶部 KPI 卡片 + 中轴类目名 + 左右柱条 + median 卡片 + peak cohort 空心圆 + age-group 分组横线。',
        "make_population_pyramid(categories=['95+','90-94',...,'0-4'], left_values=[...], right_values=[...], left_label='MALE', right_label='FEMALE', title='Population pyramid, 2025', unit='k', x_axis_label='POPULATION (THOUSANDS)', kpis=[('TOTAL POPULATION','57.2M','million persons','left'),('MEDIAN AGE','36.7','years','left')], median_index=13, median_label='MEDIAN 36.7', peak_index=13, age_group_dividers=[(3,'65+',None),(14,'WORKING','0-14')])",
        "N ∈ [2, 30]；三序列长度必须相等且都 ≥ 0；median_index/peak_index 是**行索引**（0..N-1），median_label 会画一个 accent 描边小卡片放在 median 行上方 slot 里避让数值；kpi 每项 (header, big, sub, kind)，kind ∈ 'left'/'right'/'muted'；SVG viewBox 1280×720（≈1.78:1），embed 保持这个 aspect ratio 即可（整页放大 vs 想留右侧文字栏可以用 640×360 之类的小尺寸）。",
    ),
    (
        "marimekko",
        "马赛克图",
        "make_marimekko",
        "双向占比（业务组合矩阵）：列宽 = 市场规模，列内高度 = 各方份额。",
        "make_marimekko(markets=[('欧洲', 30, [('Us', 40), ('Rival', 60)]), ('亚洲', 45, [('Us', 25), ('Rival', 75)])], we_key='Us', title='市场份额矩阵', subtitle='列宽 = 市场规模 · 列内 = 竞品份额')",
        "**inside_share 单位是 0-100**（30 = 30%）；换品牌色传 accent_rgb=(r,g,b)；SVG viewBox 约 444×284（≈1.56:1），embed 保持这个 aspect ratio 即可。",
    ),
    (
        "matrix_heat",
        "矩阵热力",
        "make_matrix_heat",
        "N×N 节点两两关系强度：共用率、相关系数、协作频率、A-B 依赖；同色深浅编码。取代弧矩阵。",
        "make_matrix_heat(matrix=[[-1,3,5],[3,-1,7],[5,7,-1]], labels=['A','B','C'], highlight_pair=(1,2), title='团队协作强度', subtitle='3 部门联合任务频次', colorbar_label='Value')",
        "**传 -1 或 None 的格子会被视为『跳过』，渲染为灰色空白 + —**（用于对角线自比等无意义关系）；对角线也可以传实际值正常上色；shade 阈值和图例函数自动分位数分档；SVG viewBox 1300×820（≈1.59:1），embed 保持这个 aspect ratio 即可（整页放大 vs 想留右侧文字栏用 640×405 之类）。",
    ),
    (
        "quadrant_2x2",
        "2×2 象限图",
        "make_quadrant_2x2",
        "品牌定位、战略取舍、评估矩阵——两轴各是一个对立概念，落点即定位。非高亮点用轮廓风（淡填+深描边），高亮点用实心 accent。",
        "make_quadrant_2x2(items=[('我们',0.35,0.72),('竞品',0.75,0.65)], x_axis=('低','高'), y_axis=('大众','高端'), x_title='定价', y_title='目标客群', highlight_index=0, title='市场定位矩阵', subtitle='2 家竞品对比')",
        "简单模式 **x/y ∈ [0,1]**；数据模式传 x_range/y_range=(min,max)；highlight_index 全篇最多 1 个；换主题色传 palette={'ink':..., 'accent':..., 'rival':..., 'point_fill':..., 'grid':..., 'muted':...}；SVG viewBox 1050×820（≈1.28:1），embed 保持这个 aspect ratio 即可（整页放大 vs 想留右侧文字栏用 512×400 之类）。",
    ),
    (
        "violin",
        "小提琴分布",
        "make_violin",
        "多组连续变量的密度形状对比：按类别看分布尾巴、峰值、中位数偏移；学术印刷版 = KDE 轮廓 + 内嵌 mini boxplot + 均值空心圆 + outlier 空心圆 + Y 轴稀疏虚线网格。",
        "make_violin(groups=[('GPT-4o',[values...]),('Claude 4.7',[values...])], y_unit='s', highlight_group='Claude 4.7', title='End-to-end response latency', subtitle='Distribution of per-request latency', figure_label='FIGURE 2', y_axis_label='Response latency (seconds)', note='Violin outlines = Gaussian KDE truncated at ±1.5·IQR whiskers.', source='Simulated data.')",
        "y_unit='%' 时，若数据全部落在 [0,100]（问卷类）自动 clamp 到 [0,100]；若数据含负值或超 100（金融收益率、变化率等）则保持数据的自然范围不 clamp；组间量级差异大时传 y_min/y_max 聚焦；每组 (name, [values]) 且 values 至少 1 个；bandwidth=None 走 Silverman 自动；show_boxplot / show_mean / show_outliers / show_legend 都可关；per_group_n 显式指定 label 下方 'n = ...' 显示值；SVG viewBox 1200×720（≈1.67:1），embed 保持这个 aspect ratio 即可（整页放大 vs 想留右侧文字栏可以用 600×360 之类的小尺寸）。",
    )
]


def chart_help(name: str = None) -> str:
    """列出所有 SVG 图种的调用范式。

    chart_help()           → 16 张总览（每张 6 行：场景 / 调用 / 骨架变体 / 要点）
    chart_help("sankey")   → 该 chart 详情（含完整 docstring + 5 骨架变体细节）
    """
    # 骨架变体说明（每 variant 一行短描述，用于总览和单张详情）
    _VARIANT_HINTS = {
        "boxplot": {
            "default_flat": "经典箱线，Q1-Q3 主体 + 中位/须/离群",
            "beeswarm": "点阵沿 y 展开成蜂群，看每个样本分布（lint 会报 circle bbox 重叠，属设计意图，跳过）",
            "notched_outlined": "notch 缺口暗示中位数置信区间 + 描边风",
            "variable_width_gradient": "宽度反映组样本量 + 渐变填充",
            "strip_flat": "去除箱体只留点带，超简约",
        },
        "violin": {
            "boxplot_inner_flat": "琴身 + 内嵌 mini boxplot（推荐 default）",
            "quartile_outlined": "琴身描边 + 3 条四分位横线",
            "points_inner_flat": "Sina-plot 点阵嵌在琴身内",
            "half_gradient": "单侧琴身 + 渐变填充",
            "kde_only": "纯 KDE 轮廓无内标记，气质极简",
        },
        "ridge": {
            "default_flat": "群峰重叠渐变（推荐 default）",
            "outlined_separated": "各行独立描边，无重叠",
            "gradient_overlap": "水平渐变编码 x 值，跨行同色系",
            "joy_division": "Joy Division 唱片风：纯黑线条无填充",
            "histogram_binned": "直方图分箱，非 KDE 平滑",
        },
        "funnel_classic": {
            "default_flat": "经典梯形上宽下窄（推荐 default）",
            "rectangle_flat": "矩形层叠，宽度 sqrt 比例编码",
            "bar_lollipop": "水平线 + 端点圆盘（现代 dashboard 极简）",
            "nested_arrow": "逐层嵌套的向下箭头（Russian doll 叙事）",
            "pyramid_flat": "反向金字塔上窄下宽（少见）",
        },
        "marimekko": {
            "default_flat": "列宽×行高双维占比（推荐 default）",
            "mekko_gradient": "sub 段渐变填充",
            "mekko_outlined": "sub 段描边风",
            "shaded_residual": "we 段实心 · 其余段淡色对比",
            "treemap_flat": "去掉 market 分列，纯 treemap 布局",
        },
        "percent_grid": {
            "square_10x10": "10×10 方格（100 人代表 100%）",
            "dot_10x10": "同布局但用圆点",
            "person_10x10": "同布局但用人形 icon",
            "square_stacked_row": "单行堆叠横条 + 分段",
            "dot_faceted": "多面板并列，每 option 独立小 grid",
        },
        "population_pyramid": {
            "default_flat": "左右柱条对称（推荐 default）",
            "filled_gradient": "柱条渐变填充",
            "stacked_flat": "每 age 有 series 分段堆叠",
            "dot_flat": "点阵编码（1 dot = N 人）",
            "outlined_burgundy": "描边风 + accent 高亮",
        },
        "matrix_heat": {
            "square_flat_full": "N×N 方格填色（推荐 default）",
            "circle_full": "格中画圆，半径可缩",
            "ellipse_upper": "只画上三角，椭圆倾角编码相关性",
            "pie_full": "每格一个小饼图（大矩阵下 lint 会报 circle 密集 bbox 重叠，属格子密度限制，跳过）",
            "annotated_number": "格中直接写数字",
        },
        "quadrant_2x2": {
            "dot_cross": "点 + 十字准心（推荐 default）",
            "bubble_L": "气泡大小编码第三维（size）",
            "label_box_quadrant_bg": "带 pill label + 四角象限名",
            "emoji_icon_cross": "点换 emoji/icon",
            "ring_arrow": "空心环 + 箭头指向轨迹",
        },
        "gantt": {
            "default_flat": "经典任务条 + 里程碑（推荐 default）",
            "progress_split": "任务条内嵌进度分段",
            "critical_path": "关键路径 accent 高亮 + 图例",
            "gradient_bars": "任务条渐变填充",
            "dot_range": "任务用起终圆点 + 连线",
        },
        "candle": {
            "candle_american_filled": "美式实心 K 线（推荐 default）",
            "candle_japanese_hollow": "日式空心 K 线（涨空跌实）",
            "ohlc_american": "美式竹节棒图（无 body）",
            "heikin_ashi": "平均足平滑趋势",
            "line_close": "只画收盘价折线",
        },
        "event_timeline": {
            "horizontal_alt_dot": "横轴上下交替卡片（推荐 default）",
            "stepped_dot": "阶梯式 dot（少事件用）",
            "vertical_alt_dot": "竖轴左右交替卡片",
            "horizontal_pin": "横轴带 pin 图钉视觉",
            "circular_dot": "圆环上分布事件",
        },
        "sankey": {
            "default_ribbon_flat": "经典 bezier ribbon（推荐 default）",
            "alluvial_sinusoidal": "sinusoidal 缓动，更飘逸",
            "chord_circular": "圆形 chord 图，节点在圆周（lint 会报 path bbox 交叉，属流带 crossing 语义，跳过）",
            "multi_layer_flat": "多层 stepped/bezier（≥4 层自动降级）",
            "gradient_layered": "流带按源→目的渐变色",
        },
        "waterfall": {
            "default_flat": "经典瀑布（推荐 default）",
            "subtotal_bridge": "自动插入 Subtotal 桥接柱",
            "cross_axis": "水平线在 0 处，正负跨轴",
            "horizontal": "横向排列",
            "stacked_gradient": "每步内部按 sub_label 分段堆叠",
        },
        "calheat": {
            "default_row_52x7": "GitHub 风 52 周 × 7 天（推荐 default）",
            "monthly_grid_12x31": "12 月 × 31 天矩阵",
            "small_multiples": "每月一格小图并列",
            "radial_year": "径向布局年度视图",
            "dot_grid": "同 default 布局但用圆点",
        },
    }

    if name is None:
        lines = [
            "# 多张 SVG chart 总览（每张 6 行：场景 / 函数 / 调用示例 / 骨架变体 / 关键坑）",
            "",
            "## 通用规则（所有 chart 都适用）",
            "  - `<embed>` 的 topLeftX/Y/width/height 由 slide 版式决定；引擎按 SVG 内部 viewBox 缩放。",
            '  - 想图占满整页 → embed 用大尺寸；想「左图 + 右侧解读栏」→ embed 用小尺寸（例如 480×275、640×360）+ 旁边放 `<shape type="text">`。',
            "  - **只要 embed 的 width:height 跟下方要点里给的 SVG viewBox 比例一致，就不会裁;对不上会自动从中心裁掉多余边**（可用 `<crop anchor>` 指定保留哪一侧）。",
            "",
            "## Lint 告警的语义豁免（重要）",
            "  - xml_lint 会跑 embed_svg_validator 检查 SVG 内元素的 bbox 重叠。**下列 chart × variant 的重叠是设计意图，不是 bug，看到相关告警可以直接忽略/跳过**：",
            "    - **`boxplot / variant='beeswarm'`**：蜂群图本质就是把每个样本以点的形式沿 y 轴密集堆叠，circle 之间 bbox 相交是必然（数据点越多、报的 `embed_svg_bbox_overlap` 越多）。告警形如 `has N overlapping circle elements` 一律跳过。",
            "    - **`sankey / variant='chord_circular'` 或大数据场景**：桑基/chord 图的流带（ribbon path）会跨越节点相互交叉——这是它的核心语义（多源→同目的），path 之间 bbox 相交是正常的。告警形如 `has N overlapping path elements` 跳过。",
            "    - **`matrix_heat / variant='pie_full'` + 大矩阵（>8×8）**：小 pie glyph 在密集格子里 circle 会互压，报的 `has N overlapping circle elements` 跳过。",
            "  - **判断原则**：如果 lint 报的是 `embed_svg_bbox_overlap` 且 `primitive_kind=circle` 或 `primitive_kind=path`（不是 text），并且属于上述 chart × variant，就可以直接接受。**text 类的重叠必须修**（文字压在一起真的读不了）。",
            "",
            "## 默认参数下允许忽略的 lint 告警（每张图 · 2026-08 校验版）",
            "  以下告警来自图种自身的结构设计（注解框、贯穿参考线、band 内标签、装饰分割线等），",
            "  改动会破坏图表语义。看到 lint 报出下列**具体形态**时可以直接放行，不必收敛：",
            "",
            "  ### population_pyramid（默认参数）",
            "  - `embed_svg_text_shape_overlap`: `median_label` 的注解 rect 覆盖 median_index 上下相邻两格的 category 文字（比如 `'2021'` / `'2020'` 与 median rect）——注解框本就设计为**盖在两格中缝的白底描边卡片**，是 median 视觉锚点。**用户已确认此形态属设计意图，无需修改**（尤其 `variant='default_flat'` 下必现）。",
            "  - `embed_svg_text_shape_overlap`: 底部 legend 的 label 文字（如 `'可再生能源'`）与其右侧紧邻的 swatch rect bbox 相交 1-2px——这是紧邻布局的必然误差。",
            "  - `embed_svg_line_through_text`: median 贯穿虚线 (`stroke-dasharray='4 3'`) 经过左右 axis value（如 `'260'` / `'210'`）——参考线的核心就是**横穿整幅图**，包括两侧 axis 数字。",
            "",
            "  ### gantt（默认参数 + `milestones` 参数）",
            "  - `embed_svg_text_shape_overlap`: milestone 标签 `'◆ Mon DD'` 落在 milestone 专用行的 background rect 内——milestone label 就是该行的**行内标注**，本就应该在行内。",
            "",
            "  ### funnel_classic（默认参数）",
            "  - `embed_svg_text_shape_overlap`: `stage_label`（如 `'实验室研发'`）与 stage 顶部 2.2px 高的分割装饰 rect 相交——分割线画在每个 stage 的 top edge，与该 stage 名字标签共占 y 范围是**stage 内的装饰线**，不是无关几何。",
            "",
            "  ### percent_grid（default: `positive/neutral/negative` 语义分组）",
            "  - `embed_svg_text_shape_overlap`: breakdown band 内的 `'NN%'` 大数字落在 band 的 rect 群里——band 本就是包裹该分组的**语义容器**，percent 落在 band 内部是设计。",
            "  - `embed_svg_bbox_overlap`（**所有 variant** — `dot_10x10` / `person_10x10` / `square_10x10` / `dot_faceted` / `square_stacked_row`）: 只要开了语义分组（传入 `positive` / `neutral` / `negative` 三个参数任一），**KPI 大数字与其下方的小 caption 共占同一格 cell** 都会触发同类 bbox_overlap——KPI + caption 是同一 cell 内的『大字+小说明』组合，属豁免。",
            "",
            "  ### violin（default `boxplot_inner_flat` variant）",
            "  - `embed_svg_text_container_overflow`: 图内说明串（如 `'±1.5·IQR whiskers'`）宽于内嵌 mini boxplot 的 path bbox——**这个 label 是给 boxplot 边界方法做注释的自由文本**，不是 path 的内容 label；validator 把它当『容器溢出』是误判。",
            "  - `embed_svg_text_shape_overlap`（variant='points_inner_flat' / 'half_gradient'）: **label 与散点 circle 相交**——`points_inner_flat` 本质是 sina-plot（点阵嵌琴身），跟 `boxplot / beeswarm` 同套路；`half_gradient` 是单侧琴身+散点区，label 落入散点区同理。text vs circle 的 bbox 相交是密集点阵必然，属设计意图。",
            "",
            "  ### matrix_heat（默认参数 · variant='square_flat_full'）",
            "  - `embed_svg_bbox_overlap`: **colorbar 分位刻度数值（如 `'5.8'`）与图例说明文字（如 `'↓ Below midpoint'`）距离极近而报 bbox 相交**——colorbar 组件内部分位刻度与图例注释并列在下方，属组件常态布局。",
            "",
            "  **看到不属于以上明确列出的形态时，仍应视为真 bug**（比如 KPI 卡三行 bbox 相交、chart 内两 label bbox 相交、axis label 与 title bbox 相交等）——那些是布局参数算错，需要收敛。",
            "",
            "  **豁免只对默认参数** 有效。传入极端 `figure_label` / `note` / 超长 label / 传入超小 embed 尺寸导致相对比例失衡的情况，仍然要检查。",
            "",
            "## 骨架变体（skeleton variant · 新增）",
            "  - **每张图有 5 个 variant**：默认（不传 variant 或 variant='classic'）走原经典设计；传特定 variant 名（见下表）走 svg_lib 的骨架变体，同样的数据可切多种视觉气质。",
            "  - **变体是图形骨架层**，与配色（palette）、字体（font_family）正交组合。选骨架看**内容语义**（比如极简/传统/多密度对比），选 palette 看**页面底色气质**（比如深底、暖色、冷色），选字体看**deck 整体感**（比如衬线学术、无衬线科技）。",
            "  - **强烈建议先跟 style 文档匹配骨架/palette 推荐**：参见 `references/style/<场景>.md` 的『推荐骨架/palette』小节；不同场景（business-review / academic-research / brand-storytelling ...）推荐的默认组合不同。",
            "  - 用错变体名（拼错）会直接 `raise ValueError`（列出可用清单），不会静默 fallback。",
            "",
            "## palette / 配色",
            "  - **palette 参数所有 chart 通用**，接受 None / palette 名字符串（如 'archive_ink' / 'nightlab' / 'sapphire_dev_bright'）/ dict（含 ink/accent/secondary/bg/muted，可选 series）。**不要用字符串替换 SVG fill/stroke，走 palette 参数**。",
            "  - **选 palette 的关键约束**：要跟 slide 页面**背景底色接近或相同**，否则图表看着像贴上去的补丁。参考 style 文档里 palette 推荐。",
            "",
            "## title / subtitle / figure_label",
            "  - **所有 chart 通用**（string，缺省 None 不渲染）。**强烈建议每张图都传 `title`**——图内标题是专业感的关键；subtitle 补一句语境（比如 'Q1-Q4 · 万美元'）；figure_label 是编辑体的 FIGURE 01 小 caption，可选。**不传 title 图看起来会像半成品**，除非页面版式已经在图外独立给了大标题。",
            "",
            "## font_family",
            "  - **所有 chart 通用**（string，如 'PingFang SC, sans-serif' / 'Inter, sans-serif' / 'Menlo, monospace'）。缺省 None 保留原设计（body Inter + heading Georgia 混排）；传值则全局统一。**推荐做法**：一份 deck 里所有 chart + 所有 slide 用同一字体族，视觉一致性最高。",
            "",
        ]
        for slug, name_cn, fn, scene, example, pitfall in _CHART_META:
            lines.append(f"## {slug} · {name_cn}")
            lines.append(f"  场景：{scene}")
            lines.append(f"  调用：{example}")
            # 5 骨架变体
            vhints = _VARIANT_HINTS.get(slug, {})
            if vhints:
                lines.append(f"  骨架 variant（5 个）：")
                for vn, hint in vhints.items():
                    lines.append(f"    - `{vn}`: {hint}")
            lines.append(f"  要点：{pitfall}")
            lines.append("")
        lines.append("查看单张详情：chart_help('sankey') / chart_help('quadrant_2x2') / ...")
        lines.append("完整参数文档：help(make_sankey) 或 inspect.getdoc(make_sankey)")
        return "\n".join(lines)
    # 单张详情
    # 每张图默认参数下会触发但属于设计意图的 lint 告警（2026-08 校验）
    _LINT_HINTS = {
        "population_pyramid": (
            "- `embed_svg_text_shape_overlap` （variant='default_flat'）: **MEDIAN 注解框（median_label 的 rect）"
            "覆盖 median 所在行上下相邻两行的 category label 文字**（如 `'2021'` / `'2020'` 与 median rect "
            "bbox 交叠）——注解框本就设计为盖在两格中缝的白底描边卡片，是 median 视觉锚点。"
            "**用户已确认此形态属设计意图，无需修改**。\n"
            "- `embed_svg_text_shape_overlap`: 底部 legend 的 label 文字（如 `'可再生能源'`）与紧邻的"
            "swatch rect 相交 1-2px——紧邻布局的必然误差。\n"
            "- `embed_svg_line_through_text`: **median 贯穿虚线**（`stroke-dasharray='4 3'`）经过左右"
            "axis value（如 `'260'` / `'210'`）——参考线本就是横穿整幅图，包括两侧 axis 数字。"
        ),
        "gantt": (
            "- `embed_svg_text_shape_overlap`: **milestone 标签 `'◆ Mon DD'` 落在 milestone 行的"
            "background rect 内**——milestone label 就是该行的行内标注。"
        ),
        "funnel_classic": (
            "- `embed_svg_text_shape_overlap`: **stage_label（如 `'实验室研发'`）与 stage 顶部 2.2px"
            "高的分割装饰 rect 相交**——分割线画在每个 stage 的 top edge，与该 stage 名字标签共占"
            "y 范围是 stage 内的装饰线。"
        ),
        "percent_grid": (
            "- `embed_svg_text_shape_overlap` （**variant='square_10x10'** = classic default 语义分组）: "
            "**breakdown band 内的 `'NN%'` 大数字落在 band 的 rect 群里**——band 本就是包裹该分组的语义"
            "容器，percent 落在 band 内部是设计。\n"
            "- `embed_svg_text_shape_overlap` （**variant='square_10x10'**, 类别 ≥ 6 或有窄段 <14%）: "
            "**breakdown band 段内 label（`'A'` / `'B'` / `'12%'` 等）在段宽 <40px 时会溢出到相邻段的 "
            "rect**——breakdown 单行 100 格分段，窄段落到相邻段是分段容器的必然，属豁免。\n"
            "- `embed_svg_bbox_overlap` （**variant='square_10x10'**, 无语义分组）: **右侧 CATEGORIES "
            "legend 每一行的 label（`'A'`）与其行尾的 `NN%` 大数字 bbox 相交**——legend 是『色块 + label + "
            "百分比大字』的紧邻排版，label 与 pct 在同一行是设计意图。\n"
            "- `embed_svg_bbox_overlap` （**variant='square_10x10'**, 无语义分组）: **BREAKDOWN header "
            "灰字与紧跟其后的 breakdown band 内 `NN%` 大数字 bbox 相交**——header 与 band 首格紧贴是"
            "分组『标签 + 内容』的语义组合。\n"
            "- `embed_svg_bbox_overlap` （**所有 variant** — `dot_10x10` / `person_10x10` / `square_10x10` "
            "/ `dot_faceted` / `square_stacked_row`）: **只要开了语义分组**（传入 `positive_labels` / "
            "`neutral_label` / `negative_labels` 任一参数），KPI 大数字与其下方的小 caption（如 "
            "`'占总数'` / `'satisfied'` / `'Enthusiastic + Optimistic'`）**共占同一格 cell 的 bbox**，"
            "触发同类 bbox_overlap——KPI + caption 就是同一 cell 内的『大字+小说明』组合，是语义分组的"
            "展示方式，属豁免。另外相邻两个 KPI 槽位的 caption（如 `'Enthusiastic + Optimistic'` 与 "
            "`'no strong opinion'`）在 caption 特别长时也会 bbox 相交，同属设计意图。"
        ),
        "violin": (
            "- `embed_svg_text_container_overflow` （variant='boxplot_inner_flat'）: **`note`（如 "
            "`'±1.5·IQR whiskers'`）宽于内嵌 mini boxplot 的 path bbox**——这个 label 是给 boxplot "
            "边界方法做注释的自由文本，不是 path 的内容 label；validator 把它当『容器溢出』是误判。\n"
            "- `embed_svg_text_shape_overlap` （variant='points_inner_flat'）: **组名 label / 分位刻度"
            "文字与散点 circle 相交**——`points_inner_flat` 本质是 sina-plot（点阵嵌琴身），跟 "
            "`boxplot / beeswarm` 是一个套路：text vs circle 的 bbox 相交是密集点阵的必然，属设计意图。\n"
            "- `embed_svg_text_shape_overlap` （variant='half_gradient'）: **组名 / 分位 label 与单侧"
            "琴身或散点区的 circle 相交**——单侧琴身+散点区布局，label 落入点阵范围同 sina-plot 一样，"
            "属豁免。"
        ),
        "boxplot": (
            "- `embed_svg_bbox_overlap` （variant='beeswarm'）：`has N overlapping circle elements`"
            "——蜂群图本质就是密集点阵，circle bbox 相交是必然。"
        ),
        "sankey": (
            "- `embed_svg_bbox_overlap` （variant='chord_circular' 或大数据）：`has N overlapping"
            "path elements`——桑基/chord 流带跨越交叉是核心语义。"
        ),
        "matrix_heat": (
            "- `embed_svg_bbox_overlap` （variant='pie_full' + 矩阵 >8×8）：`has N overlapping"
            "circle elements`——密集格子里 pie glyph 互压是格子密度限制。\n"
            "- `embed_svg_bbox_overlap` （variant='square_flat_full'）: **colorbar 分位刻度数值"
            "（如 `'5.8'`）与图例说明文字（如 `'↓ Below midpoint'`）距离极近而报 bbox 相交**——"
            "属于 colorbar 组件内部布局的常态（分位刻度与图例注释本就并列在 colorbar 下方），"
            "属豁免。"
        ),
    }
    for slug, name_cn, fn, scene, example, pitfall in _CHART_META:
        if slug == name or slug == name.replace("-", "_"):
            fn_obj = globals().get(fn)
            docstring = fn_obj.__doc__ if fn_obj and fn_obj.__doc__ else "(no docstring)"
            variants_md = ""
            vhints = _VARIANT_HINTS.get(slug, {})
            if vhints:
                variants_md = (
                    "\n**骨架变体（5 个 · 传 variant= 参数切换）**：\n"
                    + "\n".join(f"  - `{vn}`: {hint}" for vn, hint in vhints.items())
                    + "\n\n**用法示例（骨架 + palette 组合）**：\n"
                    f"```python\n{fn}(..., variant='{list(vhints)[0]}', palette='archive_ink', font_family='PingFang SC, sans-serif')\n```\n\n"
                    "**选 variant 的原则**：\n"
                    "  1. 数据语义决定骨架（多组分布用 boxplot/violin；占比用 marimekko/donut；时序用 candle/gantt）\n"
                    "  2. 场景推荐见 references/style/<场景>.md 的『推荐骨架』小节\n"
                    "  3. 不传或传 `None`/`'classic'` 走原经典设计（跟本 skill v1 完全一致）\n"
                )
            lint_md = ""
            if slug in _LINT_HINTS:
                lint_md = (
                    "\n**默认参数下允许忽略的 lint 告警（设计意图，看到直接放行）**：\n" + _LINT_HINTS[slug] + "\n\n"
                    "> 只对**默认参数**有效。传入极端 label / 超小 embed / 自定义 variant 等情况仍需检查。\n"
                    "> 未在上述列表中出现的形态（比如 KPI 卡三行 bbox 相交、chart 内两 label bbox 相交）"
                    "属于真 bug，必须收敛。\n\n"
                )
            return (
                f"# {slug} · {name_cn}\n\n"
                f"**场景**：{scene}\n\n"
                f"**调用示例**：\n```python\n{example}\n```\n\n"
                f"{variants_md}"
                f"{lint_md}"
                f"**关键坑**：{pitfall}\n\n"
                f"**完整 docstring**：\n```\n{docstring}\n```\n"
            )
    return f"chart '{name}' not found. Available: " + ", ".join(m[0] for m in _CHART_META)


# ==============================================================
# CLI
# ==============================================================
def _cli():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--type",
        required=True,
        choices=[
            "calheat",
            "ridge",
            "candle",
            "boxplot",
            "sankey",
            "funnel_classic",
            "percent_grid",
            "waterfall",
            "gantt",
            "population_pyramid",
            "event_timeline",
            "marimekko",
            "matrix_heat",
            "quadrant_2x2",
            "violin",
        ],
    )
    ap.add_argument("--values", help="逗号分隔的数值 (calheat 备用)")
    ap.add_argument("--matrix-file", help="JSON 文件路径 · 52×7 二维数组 (calheat)")
    ap.add_argument("--distributions-file", help="JSON 文件路径 · N 组分布 (ridge)")
    ap.add_argument("--ohlc-file", help="JSON 文件路径 · [[open,high,low,close]...] (candle)")
    ap.add_argument("--groups-file", help="JSON 文件路径 · [[name, [values...]], ...] (boxplot)")
    ap.add_argument("--sankey-file", help="JSON 文件路径 · {left_nodes, right_nodes, flows}")
    ap.add_argument("--descriptions", help="分号分隔的每层描述 (funnel_classic)")
    ap.add_argument("--footer", help="底部整行说明 (funnel_classic / percent_grid)")
    ap.add_argument("--grid-file", help="JSON 文件路径 · [[label, v], ...] (percent_grid, v ∈ [0,100])")
    ap.add_argument("--waterfall-file", help="JSON 文件路径 · [[name, value, kind], ...] kind='total'/'pos'/'neg'")
    ap.add_argument(
        "--gantt-file",
        help="JSON 文件路径 · {tasks:[[name, s, e]...], weeks, critical_index, milestones:[[w,label]...]}",
    )
    ap.add_argument(
        "--pyramid-file", help="JSON 文件路径 · {categories, left_values, right_values, left_label, right_label}"
    )
    ap.add_argument("--timeline-file", help="JSON 文件路径 · {years:[...], events:[[idx, side, title, sub, is_hi]...]}")
    ap.add_argument(
        "--marimekko-file", help="JSON 文件路径 · {markets:[[name,share,[[sub,inside_share]...]]...], we_key}"
    )
    ap.add_argument("--matheat-file", help="JSON 文件路径 · {matrix:N×N（对角=-1）, labels, highlight_pair:[i,j]?}")
    ap.add_argument(
        "--quadrant-file",
        help="JSON 文件路径 · {items:[[name,x,y]...], x_axis, y_axis, x_title?, y_title?, highlight_index?}",
    )
    ap.add_argument(
        "--violin-file",
        help="JSON 文件路径 · {groups:[[name,[values...]]...], y_unit?, highlight_group?, bandwidth?, y_min?, y_max?}",
    )
    ap.add_argument("--labels", help="逗号分隔的标签（cluster / stage / date / time）")
    ap.add_argument("--highlight", help="boxplot 高亮组名")
    ap.add_argument("--unit", default="", help="X/Y 刻度单位后缀")
    args = ap.parse_args()

    labels = args.labels.split(",") if args.labels else None

    if args.type == "calheat":
        if args.matrix_file:
            matrix = json.load(open(args.matrix_file))
            print(make_calheat(matrix=matrix))
        elif args.values:
            values = [float(x) for x in args.values.split(",")]
            print(make_calheat(values=values))
        else:
            ap.error("--matrix-file 或 --values 二选一")
    elif args.type == "ridge":
        distributions = json.load(open(args.distributions_file))
        print(make_ridge(distributions, group_labels=labels))
    elif args.type == "candle":
        ohlc = json.load(open(args.ohlc_file))
        print(make_candle(ohlc, date_labels=labels, y_unit=args.unit))
    elif args.type == "boxplot":
        groups = json.load(open(args.groups_file))
        print(make_boxplot(groups, y_unit=args.unit, highlight_group=args.highlight))
    elif args.type == "sankey":
        cfg = json.load(open(args.sankey_file))
        print(make_sankey(cfg["left_nodes"], cfg["right_nodes"], cfg["flows"]))
    elif args.type == "funnel_classic":
        stages = [int(x) for x in args.stages.split(",")]
        descs = args.descriptions.split(";") if args.descriptions else None
        print(
            make_funnel_classic(
                stages,
                stage_labels=labels or [f"Stage {i + 1}" for i in range(len(stages))],
                stage_descriptions=descs,
                footer=args.footer,
            )
        )
    elif args.type == "percent_grid":
        opts = json.load(open(args.grid_file))
        footer = args.footer or "ONE TICK = ONE RESPONDENT · DOT MARKS EVERY TENTH"
        print(make_percent_grid(opts, footer=footer))
    elif args.type == "waterfall":
        steps = json.load(open(args.waterfall_file))
        print(make_waterfall(steps))
    elif args.type == "gantt":
        cfg = json.load(open(args.gantt_file))
        print(
            make_gantt(
                cfg["tasks"],
                weeks=cfg.get("weeks", 16),
                critical_index=cfg.get("critical_index"),
                milestones=cfg.get("milestones"),
            )
        )
    elif args.type == "population_pyramid":
        cfg = json.load(open(args.pyramid_file))
        print(
            make_population_pyramid(
                cfg["categories"],
                cfg["left_values"],
                cfg["right_values"],
                left_label=cfg.get("left_label", "MALE"),
                right_label=cfg.get("right_label", "FEMALE"),
            )
        )
    elif args.type == "event_timeline":
        cfg = json.load(open(args.timeline_file))
        print(make_event_timeline(cfg["years"], cfg["events"]))
    elif args.type == "marimekko":
        cfg = json.load(open(args.marimekko_file))
        print(make_marimekko(cfg["markets"], we_key=cfg.get("we_key", "Us")))
    elif args.type == "matrix_heat":
        cfg = json.load(open(args.matheat_file))
        hp = cfg.get("highlight_pair")
        if hp is not None:
            hp = tuple(hp)
        print(make_matrix_heat(cfg["matrix"], cfg["labels"], highlight_pair=hp, value_fmt=cfg.get("value_fmt", "auto")))
    elif args.type == "quadrant_2x2":
        cfg = json.load(open(args.quadrant_file))
        print(
            make_quadrant_2x2(
                cfg["items"],
                x_axis=tuple(cfg.get("x_axis", ("低", "高"))),
                y_axis=tuple(cfg.get("y_axis", ("低", "高"))),
                x_title=cfg.get("x_title", ""),
                y_title=cfg.get("y_title", ""),
                highlight_index=cfg.get("highlight_index"),
            )
        )
    elif args.type == "violin":
        cfg = json.load(open(args.violin_file))
        print(
            make_violin(
                cfg["groups"],
                y_unit=cfg.get("y_unit", ""),
                highlight_group=cfg.get("highlight_group"),
                bandwidth=cfg.get("bandwidth"),
                y_min=cfg.get("y_min"),
                y_max=cfg.get("y_max"),
            )
        )


if __name__ == "__main__":
    _cli()