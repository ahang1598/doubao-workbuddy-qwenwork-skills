"""通用工具，所有 draw_<chart>() 函数复用：
- palette 解析
"""

import contextvars
import re
import sys
from pathlib import Path

from .._common import _xesc
from .._typography import chart_font_sizes

# svg_palettes.py 就在 svg_lib/ 下（scripts/svg_lib/svg_palettes.py）
SVG_LIB_ROOT = Path(__file__).resolve().parents[1]  # scripts/svg_lib/
if str(SVG_LIB_ROOT) not in sys.path:
    sys.path.insert(0, str(SVG_LIB_ROOT))
from svg_palettes import PALETTES

_INK = "rgba(28,28,26,1.0)"
_INK6 = "rgba(28,28,26,0.6)"
_INK4 = "rgba(28,28,26,0.4)"
_INK2 = "rgba(28,28,26,0.2)"
_INK1 = "rgba(28,28,26,0.12)"
_ACC = "rgba(163,88,50,1.0)"


# Generated chrome language: follows the caller's own text

_CHART_LANG = contextvars.ContextVar("chart_lang", default=None)
_AUTHORED = contextvars.ContextVar("chart_authored_text", default=frozenset())


def authored_strings(value, found=None):
    """Every string inside value, recursing through dicts/lists/tuples/sets."""
    found = set() if found is None else found
    if isinstance(value, str):
        found.add(value)
    elif isinstance(value, dict):
        for key, item in value.items():
            authored_strings(key, found)
            authored_strings(item, found)
    elif isinstance(value, (list, tuple, set, frozenset)):
        for item in value:
            authored_strings(item, found)
    return found


def has_cjk(texts):
    return any(
        "\u2e80" <= ch <= "\u9fff" or "\uac00" <= ch <= "\ud7af" or "\uf900" <= ch <= "\ufaff"
        for text in texts
        for ch in text
    )


def chart_lang():
    """Language of generated chrome for the chart being rendered: 'zh' or 'en'."""
    return _CHART_LANG.get() or "en"


def tr(template, **values):
    """Generated chart text in the current chart language."""
    if chart_lang() == "zh" and template not in _AUTHORED.get():
        template = ZH_CHROME.get(template, template)
    return template.format(**values) if values else template


ZH_CHROME = {
    # Shared axis / legend / stats chrome
    "Value": "数值",
    "Value ({unit})": "数值（{unit}）",
    "Unit: {unit}": "单位：{unit}",
    "Estimate": "估计值",
    "Series": "系列",
    "Count": "频数",
    "Density": "密度",
    "Size": "大小",
    "size": "大小",
    "Color": "颜色",
    "Category": "类别",
    "Column": "列",
    "Missing": "缺失",
    "Min": "最小值",
    "Max": "最大值",
    "Midpoint": "中点",
    "mean": "均值",
    "median": "中位数",
    "bins": "分箱数",
    "Mean": "均值",
    "Mean ± {kind}": "均值 ± {kind}",
    "Total: {value}": "合计：{value}",
    "Source: ": "来源：",
    "No data": "无数据",
    "Observations": "观测值",
    "Measurements": "测量值",
    "Residual": "残差",
    "Residual · log₁₀(y)": "残差 · log₁₀(y)",
    "Residual SE = {value}": "残差 SE = {value}",
    "offset {value}": "偏移 {value}",
    "Area ∝ {label}": "面积 ∝ {label}",
    "Pareto front": "帕累托前沿",
    "Intervals: ": "区间：",
    "Interval": "区间",
    "{level}% CI": "{level}% 置信区间",
    "Whiskers: reported lower–upper bounds": "误差线：报告的区间上下限",
    "log scale": "对数轴",
    "Sample z": "样本 z 值",
    "Theoretical z": "理论 z 值",
    "months": "月",
    "days": "天",
    "weeks": "周",
    "years": "年",
    "activity": "活动量",
    "Paired difference": "配对差值",
    "Difference = {b} − {a}.": "差值 = {b} − {a}。",
    "Center: arithmetic means of the supplied observations. ": "中心：各观测值的算术均值。",
    "Center: supplied means. ": "中心：报告的均值。",
    "Error bars: sample SD (n−1).": "误差线：样本 SD（n−1）。",
    "Error bars: SEM (SD/√n).": "误差线：SEM（SD/√n）。",
    "Error bars: {level}% CI (Student-t).": "误差线：{level}% CI（Student t）。",
    "Error bars: {level}% CI (supplied).": "误差线：{level}% 置信区间（原文报告）。",
    " Observation unit: {unit}.": "观测单位：{unit}。",
    "Radial length ({unit}): 0–{max}": "径向刻度（{unit}）：0–{max}",
    "Radial length: 0–{max}": "径向刻度：0–{max}",
    "Value / interval / n": "数值 / 区间 / n",
    "Circle area and color encode value.": "圆面积与颜色表示数值。",
    "Column width = category total; tile area = component amount.": "列宽 = 类别合计；色块面积 = 组分数量。",
    "Individual observations; uncertainty unavailable (n = 1 per series)": "单次观测；无法给出不确定性（每系列 n = 1）",
    "Error bars: {kind} where n ≥ 2; unavailable for n = 1": "误差线：n ≥ 2 时为 {kind}；n = 1 时不可用",
    "Error bars: {kind} · n per series": "误差线：{kind} · 各系列 n",
    "Survival probability": "生存概率",
    "Time ({unit})": "时间（{unit}）",
    "No. at risk": "风险人数",
    "log-rank P": "log-rank 检验 P",
    "Hazard ratio": "风险比",
    "Subgroup": "亚组",
    "Estimate (CI)": "估计值（CI）",
    "Estimate (CI level by row)": "估计值（各行 CI 水平）",
    "Dose": "剂量",
    "default": "全部数据",
    "Dose ({unit})": "剂量（{unit}）",
    "Response": "响应",
    "Response ({unit})": "响应（{unit}）",
    "{name}: 4PL fit failed · n = {n}": "{name}：4PL 拟合失败 · n = {n}",
    " · fit failed": " · 拟合失败",
    "Intervals: supplied CI; method and level follow the source.": "区间：报告的置信区间；方法与水平以原文为准。",
    "4PL point estimates; interval display disabled.": "4PL 点估计；未显示区间。",
    "4PL point estimates; confidence intervals not supplied.": "4PL 点估计；原文未报告置信区间。",
    "4PL fit unavailable; observations retained.": "无法进行 4PL 拟合；保留观测值。",
    "EC50 estimates · point area ∝ |Hill|": "EC50 估计 · 点面积 ∝ |Hill|",
    "EC50 estimates · supplied CI · point area ∝ |Hill|": "EC50 估计 · 报告的置信区间 · 点面积 ∝ |Hill|",
    "% expressing": "表达比例 (%)",
    "Mean expression": "平均表达量",
    "Mean expression ({unit})": "平均表达量（{unit}）",
    "Row mean": "行均值",
    "Col mean": "列均值",
    "Upper triangle": "上三角",
    "Upper size": "上三角大小",
    "Row annotation": "行注释",
    "Column annotation": "列注释",
    "Displayed values": "显示数值",
    "SCORE": "评分",
    "KDE density": "核密度",
    "Q1–Q3 · median · Tukey whiskers": "Q1–Q3 · 中位数 · Tukey 须",
    "quartiles": "四分位数",
    "outliers": "离群值",
    "observations": "观测值",
    "matching subject IDs": "同一受试者连线",
    "Notes. ": "注：",
    "Source. ": "来源：",
    "Notes.": "注：",
    "Source.": "来源：",
    "Offset {value}": "偏移 {value}",
    "Ranked by Δ ({b} − {a})": "按 Δ（{b} − {a}）排序",
    "Before": "前",
    "After": "后",
    "Paired standardized change (d_z)": "配对标准化变化（d_z）",
    "Cohen's d · independent samples": "Cohen's d · 独立样本",
    " · approximate 95% confidence interval": " · 近似 95% 置信区间",
    "Standardized effect sizes": "标准化效应量",
    "Comparison": "比较",
    "Estimate [95% CI]": "估计值 [95% CI]",
    "Box: Q1–Q3, median and Tukey whiskers; open dot: mean.": "箱体：Q1–Q3、中位数与 Tukey 须；空心点：均值。",
    "Box: Q1–Q3, median and Tukey whiskers.": "箱体：Q1–Q3、中位数与 Tukey 须。",
    ". Statistics use all raw observations.": "。统计量基于全部原始观测值。",
    "KDE from observed samples; violin width is relative density within each group.": "KDE 基于观测样本；小提琴宽度为组内相对密度。",
    "{n} observations": "{n} 个观测值",
    "range [{low}, {high}], median {median}, {count}": "范围 [{low}, {high}]，中位数 {median}，{count}",
    "{label}: {detail}.": "{label}：{detail}。",
    "Dense dots preserve exact repeats or display-bin medians; full counts and measured ranges:": "密集点保留精确重复值或显示分箱中位数；完整计数与实测范围：",
    "Distribution comparison": "分布比较",
    "Quantile probability": "分位概率",
    "Quantile shift · {b} − {a}": "分位数位移 · {b} − {a}",
    "Energy": "能量",
    "Energy ({unit})": "能量（{unit}）",
    "Wave vector k": "波矢 k",
    "Density of States": "态密度",
    "band {i}": "能带 {i}",
    "Signal": "信号",
    "Signal ({unit})": "信号（{unit}）",
    "Peak Table": "峰表",
    "Ht": "峰高",
    "Area": "面积",
    "Area %": "面积 %",
    "Total": "合计",
    "n peaks": "峰数",
    "total area": "总面积",
    "tallest RT": "最高峰 RT",
    "Insufficient data": "数据不足",
    "No spectrum data": "无光谱数据",
    "No time points": "无时间点",
    "Grid too small": "网格过小",
    "Probability density": "概率密度",
    "Annotations": "标注",
    "grid {rows}×{cols}": "网格 {rows}×{cols}",
    "z min {value}": "z 最小值 {value}",
    "z max {value}": "z 最大值 {value}",
    "Z at x={value}": "x={value} 处的 Z",
    "Z at y={value}": "y={value} 处的 Z",
    "Depth": "深度",
    "Mixed layer": "混合层",
    "Thermocline ({top}–{bottom} {unit})": "温跃层（{top}–{bottom} {unit}）",
    "Deep water": "深层水",
    "Gradient d/dz": "梯度 d/dz",
    "Series {i}": "系列 {i}",
    "curve {i}": "曲线 {i}",
    "Rate constants k": "速率常数 k",
    "Time": "时间",
    "{label} ({unit})": "{label}（{unit}）",
    "Luminosity": "光度",
    "Effective Temperature": "有效温度",
    "Absolute magnitude": "绝对星等",
    "B−V color index": "B−V 色指数",
    "Sun reference": "太阳参考点",
    "Mass hist": "质量直方图",
    "Reaction coordinate": "反应坐标",
    "Path {i}": "路径 {i}",
    "dashed bar = transition state ‡": "虚线横杠 = 过渡态 ‡",
    "Transition": "过渡态",
    "False positive rate": "假阳性率",
    "True positive rate": "真阳性率",
    "Precision": "精确率",
    "Recall": "召回率",
    "Fitted value": "拟合值",
    "Residuals are in log10(y) units.": "残差以 log10(y) 为单位。",
    "log2 fold change": "log2 倍数变化",
    "log₂ fold change": "log₂ 倍数变化",
    "Mean expression (log10)": "平均表达量（log10）",
    "P-value hist": "P 值分布",
    "p-value": "P 值",
    "n = {n}; sig = {sig}": "n = {n}；显著 = {sig}",
    "Not significant": "不显著",
    "Upregulated": "上调",
    "Downregulated": "下调",
    "Top features": "主要特征",
    "Threshold": "阈值",
    "Threshold {i}": "阈值 {i}",
    "Rug gene sets — {legend}": "基因集刻度 — {legend}",
    "Both up": "均上调",
    "Both down": "均下调",
    "Opposite": "方向相反",
    "Unchanged": "无变化",
    "X only": "仅 X",
    "Y only": "仅 Y",
    "Comparison X · log₂ FC": "比较 X · log₂ FC",
    "Comparison Y · log₂ FC": "比较 Y · log₂ FC",
    "Marker expression": "标志基因表达",
    "mean expr": "平均表达",
    "% expr": "表达 %",
    "n = {n} cells, k = {k} clusters": "n = {n} 个细胞，k = {k} 个簇",
    "n = {n} cells": "n = {n} 个细胞",
    "Pseudotime": "拟时序",
    "Expression": "表达量",
    "Marker gene dynamics along pseudotime": "标志基因沿拟时序的变化",
    "Phase (°)": "相位 (°)",
    "Frequency": "频率",
    "Frequency ({unit})": "频率（{unit}）",
    "n points": "点数",
    "n points = {n}": "点数 = {n}",
    "Stress": "应力",
    "Stress ({unit})": "应力（{unit}）",
    "Strain": "应变",
    "Strain ({unit})": "应变（{unit}）",
    "E (Young's)": "杨氏模量 E",
    "Elastic": "弹性区",
    "Plastic": "塑性区",
    "Work-hardening rate": "加工硬化率",
    "Specimen": "试样",
    "Amplitude": "振幅",
    "Amplitude ({unit})": "振幅（{unit}）",
    "Trace {i}": "道 {i}",
    "Freq bin": "频率分箱",
    "n traces = {traces}, n events = {events}": "道数 = {traces}，事件数 = {events}",
    "Latitude": "纬度",
    "Latitude ({unit})": "纬度（{unit}）",
    "Time mean": "时间平均",
    "Zonal mean": "纬向平均",
    "Volume ({unit})": "体积（{unit}）",
    "x min": "x 最小值",
    "x max": "x 最大值",
    "Kind": "类型",
    "Magnitude": "星等",
    "magnitude": "星等",
    "Magnitude distribution": "星等分布",
    "Star": "恒星",
    "Pulsar": "脉冲星",
    "Galaxy": "星系",
    "Aitoff projection": "Aitoff 投影",
    "Mollweide projection": "Mollweide 投影",
    "Ecliptic": "黄道",
    "Galactic plane": "银道面",
    "N": "北",
    "NE": "东北",
    "E": "东",
    "SE": "东南",
    "S": "南",
    "SW": "西南",
    "W": "西",
    "NW": "西北",
    "V range": "V 范围",
    "Buffer · pKa = {value}": "缓冲区 · pKa = {value}",
    "count": "计数",
    "Marginals: observed counts in equal-width bins.": "边缘分布：等宽分箱的观测频数。",
    "Marginals: counts and Gaussian KDE scaled to expected counts per bin (density × n × bin width).": "边缘分布：频数与按每箱期望频数缩放的高斯 KDE（密度 × n × 箱宽）。",
    "Marginals: Gaussian KDE; relative density heights share a scale across groups on each axis.": "边缘分布：高斯 KDE；同一轴上各组相对密度高度共用刻度。",
    "Marginals: median, quartiles and observed Tukey whiskers; outliers remain visible.": "边缘分布：中位数、四分位数与 Tukey 须；保留离群值。",
    "Statistics use X: {x}, Y: {y} coordinates.": "统计量使用 X：{x}，Y：{y} 坐标。",
    "linear": "线性",
    "log10": "log10",
    "Dashed ellipses: {level} chi-square(2) normal-reference covariance coverage of observations.": "虚线椭圆：观测值的 {level} 卡方(2) 正态参考协方差覆盖范围。",
    "Filled 2D Gaussian KDE: opacity shows each group’s fraction of peak density.": "填充二维高斯 KDE：不透明度表示各组相对峰值密度的比例。",
    "2D Gaussian KDE contours: {levels} of each group's peak density.": "二维高斯 KDE 等值线：各组峰值密度的 {levels}。",
    "Residual = observed − predicted, in {unit} units.": "残差 = 观测值 − 预测值，单位 {unit}。",
    "Histogram · count / bin": "直方图 · 频数 / 箱",
    "Gaussian KDE · density": "高斯 KDE · 密度",
    "Tukey box": "Tukey 箱线",
    "Histogram + KDE · count / bin": "直方图 + KDE · 频数 / 箱",
    "X marginal · ": "X 边缘 · ",
    "Y marginal · ": "Y 边缘 · ",
    "Coincident observations: circle/pie area ∝ n (largest n={max}); numerals give exact n, slices give group counts. Unnumbered marks are n=1. Statistics use all raw samples.": "重合观测：圆/饼面积 ∝ n（最大 n={max}）；数字为精确 n，扇区为各组计数，未标数字的点 n=1。统计量基于全部原始样本。",
    "Upper: {method} per group; n counts complete observed pairs. Undefined means fewer than two values or zero variance.": "上三角：各组 {method}；n 为完整观测对数。未定义表示少于两个值或方差为零。",
    "Spearman ρ (average ranks for ties)": "Spearman ρ（并列取平均秩）",
    "Diagonal: {diagonal}. Lower: {lower}.": "对角线：{diagonal}。下三角：{lower}。",
    "observed histogram counts": "观测直方图频数",
    "Gaussian KDE with shared relative height per variable": "各变量共用相对高度的高斯 KDE",
    "observed scatter": "观测散点",
    "2D Gaussian KDE; contours at {levels} of each group’s peak": "二维高斯 KDE；等值线位于各组峰值的 {levels}",
    "Axis/statistical coordinates: ": "坐标轴/统计坐标：",
    "Count / bin": "频数 / 箱",
    "Count / bin · max {max}": "频数 / 箱 · 最大 {max}",
    "Gaussian KDE": "高斯 KDE",
    "Positive": "正相关",
    "Negative": "负相关",
    "Zero / unspecified": "零 / 未指定",
    "Edge width: absolute weight / correlation (0–{max}). ": "边宽：权重/相关系数绝对值（0–{max}）。",
    "Dashed edge: P ≥ 0.05. ": "虚线边：P ≥ 0.05。",
    "Node area: size; open node: zero; dashed open node: missing. ": "节点面积：大小；空心节点：零；虚线空心节点：缺失。",
    " Node area: size; open node: zero; dashed open node: missing.": "节点面积：大小；空心节点：零；虚线空心节点：缺失。",
    "Node size": "节点大小",
    "Dashed extensions align tips with rings; they do not contribute branch length.": "虚线延长线仅使末端对齐环带，不计入枝长。",
    "Radius preserves cumulative branch length; dashed tip extensions add no length.": "半径保持累计枝长；末端虚线延长不计长度。",
    "branch length": "枝长",
    "edges (cladogram)": "条边（分支图）",
    "Composition": "组成",
    "Radial scale: linear · {directions}": "径向刻度：线性 · {directions}",
    "Radial scale: area · {directions}": "径向刻度：面积 · {directions}",
    "out": "向外",
    "in": "向内",
    "Grid rings show 25%, 50%, 75% and 100% of each stated axis range; ranges are shared across panels.": "网格环表示各轴量程的 25%、50%、75% 与 100%；各面板共用量程。",
    "{lo} to {hi}": "{lo}–{hi}",
    "{n} bins · bin width = {w}°": "{n} 个分箱 · 箱宽 = {w}°",
    "mean direction = {deg}°": "平均方向 = {deg}°",
    "weighted by {unit}": "按 {unit} 加权",
    "KDE density per unit area · Gaussian kernel on an equilateral triangle": "单位面积核密度 · 等边三角形上的高斯核",
    "Precomputed scalar field · triangular lattice": "预计算标量场 · 三角网格",
    "Components sum to {total}": "各组分之和为 {total}",
    " · normalized from supplied weights": " · 按给定权重归一化",
    "Axis ticks × {scale} · ": "坐标刻度 × {scale} · ",
    "Groups": "分组",
    "{label} (area)": "{label}（面积）",
    "Exclusive intersections: filled dots = present; other named sets = absent.": "互斥交集：实心点 = 包含；其余集合 = 不包含。",
    "Set size": "集合大小",
    "Set (size)": "集合（大小）",
    "Intersection size": "交集大小",
    "Dashed line: follow-up · Arrow: ongoing at last observation": "虚线：随访 · 箭头：末次观测时仍在持续",
    "Dashed line: follow-up; arrow: ongoing at last observation.": "虚线：随访；箭头：末次观测时仍在持续。",
    "Time from treatment start": "自治疗开始的时间",
    "Jan": "1月",
    "Feb": "2月",
    "Mar": "3月",
    "Apr": "4月",
    "May": "5月",
    "Jun": "6月",
    "Jul": "7月",
    "Aug": "8月",
    "Sep": "9月",
    "Oct": "10月",
    "Nov": "11月",
    "Dec": "12月",
    "JAN": "1月",
    "FEB": "2月",
    "MAR": "3月",
    "APR": "4月",
    "MAY": "5月",
    "JUN": "6月",
    "JUL": "7月",
    "AUG": "8月",
    "SEP": "9月",
    "OCT": "10月",
    "NOV": "11月",
    "DEC": "12月",
    "Mon": "周一",
    "Tue": "周二",
    "Wed": "周三",
    "Thu": "周四",
    "Fri": "周五",
    "Sat": "周六",
    "Sun": "周日",
    "Less": "少",
    "More": "多",
    "MONTHLY TOTAL": "月度合计",
    "MEAN BY WEEKDAY": "星期均值",
    "Monthly peak": "月峰值",
    "TOTAL": "合计",
    "ACTIVE DAYS": "活跃天数",
    "PEAK": "峰值",
    "of {n}": "共 {n} 天",
    "single day": "单日",
    "LAST PRICE": "最新价",
    "PERIOD CHANGE": "区间涨跌",
    "RANGE": "区间范围",
    "AVG VOLUME": "平均成交量",
    "VOLUME": "成交量",
    "LEGEND": "图例",
    "KEY EVENTS": "关键事件",
    "period end": "期末",
    "per bar": "每根 K 线",
    "{value} absolute": "绝对值 {value}",
    "span {value}": "跨度 {value}",
    "Up day (close ≥ open)": "上涨日（收盘 ≥ 开盘）",
    "Down day (close < open)": "下跌日（收盘 < 开盘）",
    "MA {w} (short-term)": "MA {w}（短期）",
    "MA {w} (long-term)": "MA {w}（长期）",
    "Bollinger ({w}, {k}σ)": "布林带（{w}, {k}σ）",
    "bar {i}": "第 {i} 根",
    "Candlestick · {n} bars · OHLC + volume": "K 线图 · {n} 根 · OHLC + 成交量",
    "Conversion": "转化率",
    "DROP-OFF": "流失",
    "STAGE": "阶段",
    "CUMULATIVE CONVERSION": "累计转化率",
    "CUMULATIVE": "累计",
    "CONVERSION": "转化率",
    "OVERALL CONVERSION": "整体转化率",
    "BIGGEST DROP-OFF": "最大流失",
    "STRONGEST STEP": "最佳环节",
    "{n} dropped": "流失 {n}",
    "ONE SQUARE = 1%": "每格 = 1%",
    "BREAKDOWN": "构成",
    "CATEGORIES": "类别",
    "CATEGORY": "类别",
    "POSITIVE": "正面",
    "NEUTRAL": "中立",
    "NEGATIVE": "负面",
    "no strong opinion": "无明确倾向",
    "MALE": "男性",
    "FEMALE": "女性",
    "M / F ratio": "男 / 女比例",
    "Median": "中位数",
    "Peak cohort": "峰值队列",
    "PREMIUM": "溢价型",
    "LEADERS": "领先者",
    "LAGGARDS": "落后者",
    "VALUE": "性价比型",
    "Top score, lower value": "得分高，价值较低",
    "High performance · high value": "高表现 · 高价值",
    "Underperform on both axes": "两项均落后",
    "Efficient, mid-tier score": "高效，得分中等",
    "KEY OBSERVATIONS": "关键观察",
    "TOTAL FLOWS": "总流量",
    "EVENTS": "事件",
    "Critical path": "关键路径",
    "Non-critical": "非关键",
    "CP": "关键",
    "TODAY": "今天",
    "PLAN": "计划",
    "OWNER": "负责人",
    "Planned duration": "计划工期",
    "Actual progress": "实际进度",
    "Milestone": "里程碑",
    "Today marker": "今日标记",
    "REPORTED PROGRESS": "已报告进度",
    "COMPLETED": "已完成",
    "ON TRACK": "正常推进",
    "AT RISK": "有风险",
    "{k}/{n} tasks reported": "{k}/{n} 项任务已报告",
    "{k}/{n} statuses reported": "{k}/{n} 项状态已报告",
    "Gantt · {n} tasks · {start} → {end}": "甘特图 · {n} 项任务 · {start} → {end}",
    "Positive residual": "正残差",
    "Negative residual": "负残差",
}


def resolve_palette(palette):
    """把 palette 参数（None/str/dict）解析为核心配色 dict。"""
    if palette is None:
        pl = {}
    elif isinstance(palette, dict):
        pl = dict(palette)
    elif isinstance(palette, str):
        if palette not in PALETTES:
            raise ValueError(f"unknown palette {palette!r}. Available: {sorted(PALETTES)}")
        pl = dict(PALETTES[palette])
    else:
        raise TypeError(f"palette must be None/str/dict, got {type(palette).__name__}")

    ink = pl.get("ink", _INK)
    accent = pl.get("accent", _ACC)
    secondary = pl.get("secondary", _rgba_with_alpha(ink, 0.6))
    bg = pl.get("bg", "rgba(250,248,242,1)")
    muted = pl.get("muted", _rgba_with_alpha(ink, 0.6))

    out = {
        "ink": ink,
        "accent": accent,
        "secondary": secondary,
        "bg": bg,
        "muted": muted,
        "ink6": _rgba_with_alpha(ink, 0.6),
        "ink4": _rgba_with_alpha(ink, 0.4),
        "ink2": _rgba_with_alpha(ink, 0.2),
        "ink1": _rgba_with_alpha(ink, 0.12),
    }
    for k, v in pl.items():
        if k not in out:
            out[k] = v
    return out


def _rgba_with_alpha(rgba_str, alpha):
    m = re.match(r"\s*rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)", rgba_str or "")
    if not m:
        return f"rgba(28,28,26,{alpha})"
    r, g, b = int(float(m.group(1))), int(float(m.group(2))), int(float(m.group(3)))
    return f"rgba({r},{g},{b},{alpha})"


def rgb_tuple(rgba_str):
    m = re.match(r"\s*rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)", rgba_str or "")
    if not m:
        return (28, 28, 26)
    return (int(float(m.group(1))), int(float(m.group(2))), int(float(m.group(3))))


def is_dark_palette(pal):
    """判断 palette 的 bg 是否深色（用于决定文字颜色对比）。"""
    r, g, b = rgb_tuple(pal.get("bg", "rgba(250,248,242,1)"))
    luma = 0.299 * r + 0.587 * g + 0.114 * b
    return luma < 128


xesc = _xesc  # XML/SVG 文本转义；与 _common._xesc 同一实现


def auto_font_size(n_items, base=12, min_size=8, max_size=16):
    """根据元素数量自适应字号：数量越多字号越小。"""
    if n_items <= 5:
        return base + 2
    elif n_items <= 10:
        return base
    elif n_items <= 20:
        return max(min_size, base - 1)
    else:
        return max(min_size, base - 2)


def data_scale_factor(n):
    """按数据规模 n 返回字号缩放因子。"""
    if n <= 4:
        return 1.4
    if n <= 8:
        return 1.0
    if n <= 15:
        return 0.8
    return 0.6


def viewbox_fs(vb_w, vb_h, n, role_mult=1.0, floor=10.0):
    """Return a measured-label size for the canvas and visible item count."""
    body = chart_font_sizes(vb_w, vb_h, n)["body"]
    return round(max(float(floor), body * float(role_mult)), 1)


def svg_open(vb_x=0, vb_y=0, vb_w=900, vb_h=540, bg=None):
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb_x} {vb_y} {vb_w} {vb_h}">']
    if bg:
        parts.append(f'<rect x="{vb_x}" y="{vb_y}" width="{vb_w}" height="{vb_h}" fill="{bg}"/>')
    return "".join(parts)


def svg_close():
    return "</svg>"


def gradient_def(gid, base_col, direction="vertical", x1=0, y1=0, x2=0, y2=100):
    """gradient 皮肤：linearGradient defs 字符串。返回 <defs> 内层片段。"""
    top = _rgba_with_alpha(base_col, 1.0)
    bot = _rgba_with_alpha(base_col, 0.55)
    if direction == "horizontal":
        x2, y2 = 100, 0
    return (
        f'<linearGradient id="{gid}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
        f'gradientUnits="userSpaceOnUse">'
        f'<stop offset="0%" stop-color="{top}"/>'
        f'<stop offset="100%" stop-color="{bot}"/>'
        f"</linearGradient>"
    )


def _header(ctx, ml=None, mr=None) -> str:
    """Title, subtitle and header rule shared by the candle / event-timeline / funnel / waterfall skeletons."""
    ink = ctx.pal["ink"]
    mut = ctx.pal["muted"]
    parts = []
    ML = ctx.ML if ml is None else ml
    MR = ctx.MR if mr is None else mr
    if ctx.title:
        parts.append(
            f'<text x="{ML}" y="30" font-family="Georgia, serif" font-size="20" '
            f'font-weight="600" fill="{ink}" letter-spacing=".03em">{xesc(ctx.title)}</text>'
        )
    if ctx.subtitle:
        y = 48 if ctx.title else 30
        parts.append(
            f'<text x="{ML}" y="{y}" font-family="Inter, sans-serif" font-size="11" '
            f'fill="{mut}" letter-spacing=".14em">{xesc(ctx.subtitle)}</text>'
        )
    if ctx.title:
        parts.append(
            f'<line x1="{ML}" y1="{ctx.header_h}" x2="{ctx.W - MR}" y2="{ctx.header_h}" '
            f'stroke="{ink}" stroke-width="0.6" opacity="0.4"/>'
        )
    return "".join(parts)


def notes_source_footer(
    note, source, *, x, x_right, y, rule, font, fs, color, fmt="", stack_source=False, figure_label=None, figure_fs=None
) -> str:
    """Classic ruled footer: ``Notes.`` / ``Source.`` lines and an optional right-aligned figure label."""
    if not (note or source):
        return ""
    parts = [
        f'<line x1="{x:{fmt}}" y1="{y - 14:{fmt}}" x2="{x_right:{fmt}}" '
        f'y2="{y - 14:{fmt}}" stroke="{rule}" stroke-width="0.5"/>'
    ]
    if note:
        parts.append(
            f'<text x="{x:{fmt}}" y="{y:{fmt}}" font-family="{font}" '
            f'font-size="{fs}" fill="{color}">'
            f'<tspan font-weight="600">{xesc(tr("Notes."))}</tspan> {xesc(note)}</text>'
        )
    if source:
        src_y = y + 14 if note or not stack_source else y
        parts.append(
            f'<text x="{x:{fmt}}" y="{src_y:{fmt}}" font-family="{font}" '
            f'font-size="{fs}" fill="{color}">'
            f'<tspan font-weight="600">{xesc(tr("Source."))}</tspan> {xesc(source)}</text>'
        )
    if figure_label:
        parts.append(
            f'<text x="{x_right:{fmt}}" y="{y + 14:{fmt}}" text-anchor="end" '
            f'font-family="{font}" font-size="{figure_fs}" fill="{color}" '
            f'letter-spacing=".05em">{xesc(figure_label)}</text>'
        )
    return "".join(parts)
