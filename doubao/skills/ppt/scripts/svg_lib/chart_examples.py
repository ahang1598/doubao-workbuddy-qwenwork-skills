"""Runnable example kwargs for every chart in svg_lib.charts."""

import math
import random


def _rng(seed):
    return random.Random(seed)


def _r(value, digits=2):
    return round(value, digits) + 0.0  # + 0.0 turns -0.0 into 0.0


def _normal(seed, n, mean, sd, digits=2):
    rng = _rng(seed)
    return [_r(rng.gauss(mean, sd), digits) for _ in range(n)]


def _linspace(lo, hi, n, digits=6):
    return [_r(lo + (hi - lo) * i / (n - 1), digits) for i in range(n)]


def _gauss_peak(x, center, sigma):
    return math.exp(-((x - center) ** 2) / (2 * sigma * sigma))


def _groups(seed, specs, n, digits=2):
    """[(name, [n draws of N(mean, sd)])] for spec (name, mean, sd)."""
    return [[name, _normal(seed + i, n, mean, sd, digits)] for i, (name, mean, sd) in enumerate(specs)]


_DOSE_GROUPS = (("Control", 2.7, 1.0), ("Low", 3.5, 1.4), ("High", 5.1, 1.3), ("Washout", 3.6, 1.1))


def _candle(seed=11, n=60):
    rng = _rng(seed)
    ohlc, close = [], 100.0
    for _ in range(n):
        open_ = close
        close = open_ + rng.gauss(-0.05, 1.3)
        high = max(open_, close) + abs(rng.gauss(0, 0.9))
        low = min(open_, close) - abs(rng.gauss(0, 0.9))
        ohlc.append([_r(open_), _r(high), _r(low), _r(close)])
    return {"ohlc": ohlc, "volume": [rng.randint(500_000, 2_000_000) for _ in range(n)]}


def _composite_series():
    def points(offset):
        return [[x, _r(2.6 + offset + 0.6 * (x - 1) + 0.4 * math.sin(x - 1), 3)] for x in range(1, 13)]

    return [{"name": "Control", "points": points(0)}, {"name": "Treated", "points": points(0.7)}]


def _dose_response(seed=13):
    rng = _rng(seed)
    doses = [10 ** (-2 + 4 * i / 19) for i in range(20)]
    return [
        {"dose": _r(d, 4), "response": _r(100 / (1 + (ec50 / d) ** 1.4) + rng.gauss(0, 3)), "group": group}
        for group, ec50 in (("Drug A", 1.0), ("Drug B", 2.8), ("Drug C", 0.28))
        for d in doses
    ]


def _kinetics(seed=14):
    rng = _rng(seed)
    time = list(range(0, 60, 2))
    return [
        {"name": name, "time": list(time), "value": [_r(100 * (1 - math.exp(-k * t)) + rng.gauss(0, 2)) for t in time]}
        for name, k in (("Enz A", 0.08), ("Enz B", 0.14), ("Enz C", 0.22))
    ]


def _km_group(seed, name, mean_time, event_rate, n=60):
    rng = _rng(seed)
    times = [max(0.1, _r(rng.expovariate(1 / mean_time), 1)) for _ in range(n)]
    return {"name": name, "times": times, "events": [int(rng.random() < event_rate) for _ in range(n)]}


def _line_band(seed=15):
    rng = _rng(seed)
    series = []
    for name, start, slope in (("Model A", 1.06, 0.29), ("Model B", 1.56, 0.29)):
        mean = [_r(start + slope * x + rng.gauss(0, 0.08)) for x in range(16)]
        series.append(
            {
                "name": name,
                "x": list(range(16)),
                "y_mean": mean,
                "y_ci_up": [_r(m + 0.3) for m in mean],
                "y_ci_dn": [_r(m - 0.3) for m in mean],
            }
        )
    return series


def _pairs(seed=17):
    rng = _rng(seed)
    means = {"A": (0.0, 0.0, 0.0), "B": (1.0, 0.55, 0.1)}
    return [
        {**{v: _r(rng.gauss(m, 0.95)) for v, m in zip("abc", means[group])}, "group": group}
        for group in "AB"
        for _ in range(40)
    ]


def _pseudotime(seed=18, n=240):
    """Cells along a sine-shaped trajectory; both stemness markers fall with pseudotime."""
    rng = _rng(seed)
    points, expr = [], []
    for i in range(n):
        t = i / (n - 1)
        points.append(
            {
                "x": _r(t + rng.gauss(0, 0.03), 4),
                "y": _r(math.sin(2 * math.pi * t) + rng.gauss(0, 0.12), 4),
                "pseudotime": _r(t, 4),
            }
        )
        expr.append([_r(1 - t + rng.gauss(0, 0.04), 3), _r(1 - t + rng.gauss(0, 0.05), 3)])
    trajectory = [[_r(k / 24, 4), _r(math.sin(2 * math.pi * k / 24), 4)] for k in range(25)]
    return {"points": points, "trajectory": trajectory, "marker_genes": ["SOX2", "NANOG"], "expr_matrix": expr}


def _pr_curve(seed, start, drop):
    rng = _rng(seed)
    recall = [_r(0.05 * (i + 1)) for i in range(20)]
    return recall, [_r(min(0.99, start - drop * r + rng.gauss(0, 0.015)), 3) for r in recall]


def _roc_pr():
    fpr = [_r(i / 20) for i in range(21)]
    curves = [
        {"name": name, "fpr": list(fpr), "tpr": [_r(1 - (1 - f) ** power, 6) for f in fpr], "auc": auc}
        for name, power, auc in (("Model A", 3, 0.92), ("Model B", 2, 0.78))
    ]
    pr_curves = []
    for seed, name, start, drop, auc in ((21, "Model A", 0.99, 0.47, 0.88), (22, "Model B", 0.97, 0.6, 0.7)):
        recall, precision = _pr_curve(seed, start, drop)
        pr_curves.append({"name": name, "recall": recall, "precision": precision, "auc": auc})
    return {"curves": curves, "pr_curves": pr_curves}


def _scatter_series(seed, name, slope, intercept):
    rng = _rng(seed)
    points = []
    for _ in range(28):
        x = rng.uniform(0, 10)
        points.append({"x": _r(x), "y": _r(intercept + slope * x + rng.gauss(0, 0.6))})
    return {"name": name, "points": points, "fit": "linear"}


def _seismic(seed=23):
    """P arrival at once, S arrival slightly later; both decaying wave trains with background noise."""
    rng = _rng(seed)
    time = [_r(i * 0.02) for i in range(400)]

    def trace(freq, decay, onset):
        return [
            _r(
                (1 - math.exp(-t / onset)) * math.exp(-t / decay) * math.sin(2 * math.pi * freq * t)
                + rng.gauss(0, 0.04),
                3,
            )
            for t in time
        ]

    return [
        {"name": "P-wave", "time": list(time), "amplitude": trace(3.1, 1.6, 0.03)},
        {"name": "S-wave", "time": list(time), "amplitude": trace(4.4, 1.9, 0.02)},
    ]


_SPECTRUM_PEAKS = [(480, 44), (520, 100), (650, 70)]


def _spectrum(seed=25):
    rng = _rng(seed)
    x = _linspace(400, 800, 300, 3)
    y = [_r(max(0.0, sum(h * _gauss_peak(v, c, 12) for c, h in _SPECTRUM_PEAKS) + rng.gauss(0, 1.2))) for v in x]
    return {"x": x, "y": y, "peaks": [{"x": c, "y": h} for c, h in _SPECTRUM_PEAKS]}


def _swimmer():
    stages = ("Induction", "Consolidation", "Maintenance")
    plan = [
        (6, 11, 15, 18),
        (4, 7, 13, 16),
        (2, 4, 7, 11),
        (5, 9, 15, 18),
        (5, 8, 14, 15),
        (3, 6, 9, 14),
        (6, 9, 13, 18),
        (2, 4, 8, 12),
    ]
    patients = []
    for i, (*ends, last) in enumerate(plan):
        starts = [0, *ends[:-1]]
        patients.append(
            {
                "id": f"P{i + 1}",
                "segments": [{"treatment": s, "start": a, "end": b} for s, a, b in zip(stages, starts, ends)],
                "followup": {"start": ends[-1], "end": last, "ongoing": True},
                "events": [{"time": ends[-1], "kind": "Response"}],
            }
        )
    return patients


def _ternary(seed=26):
    rng = _rng(seed)
    points = []
    for group, alpha in (("Shale", (3, 2.4, 2.4)), ("Sandstone", (2.4, 3, 2.4)), ("Limestone", (2.4, 2.4, 3))):
        for _ in range(25):
            a, b, c = (rng.gammavariate(k, 1) for k in alpha)
            total = a + b + c
            a, b = _r(a / total, 3), _r(b / total, 3)
            points.append({"a": a, "b": b, "c": _r(1 - a - b, 3), "group": group})
    return points


def _time_latitude(seed=27):
    """Warming that spreads from the northern to the southern latitudes over time."""
    rng = _rng(seed)
    times = list(range(1980, 2024))
    latitudes = _linspace(-60, 60, 12, 4)
    matrix = [
        [_r(0.85 * (year - 1980) / 43 + 0.85 * lat / 120 - 0.45 + rng.gauss(0, 0.08), 3) for lat in latitudes]
        for year in times
    ]
    return {"times": times, "latitudes": latitudes, "matrix": matrix}


def _umap(seed=28):
    rng = _rng(seed)
    centers = (("C0", -3.0, 0.0), ("C1", 2.1, 3.0), ("C2", 3.1, -2.0))
    return [
        {"x": _r(rng.gauss(cx, 0.65), 3), "y": _r(rng.gauss(cy, 0.65), 3), "cluster": name}
        for name, cx, cy in centers
        for _ in range(60)
    ]


def _volcano(seed=29, n=120):
    """Significance grows with |log2FC| so the corners hold labelled hits."""
    rng = _rng(seed)
    points = []
    for i in range(n):
        fc = rng.gauss(0, 1.15)
        points.append(
            {"log2fc": _r(fc), "neg_log10_p": _r(min(6.0, rng.uniform(0, 5) + 0.6 * abs(fc))), "name": f"Gene {i + 1}"}
        )
    return points


def _set_members(seed, k):
    return sorted(_rng(seed).sample(range(1, 201), k))


def _calheat(seed=30):
    rng = _rng(seed)
    return [_r(max(0.01, rng.gammavariate(2.3, 1.04))) for _ in range(364)]


def _depth_profile(seed=31):
    rng = _rng(seed)
    depths = list(range(0, 200, 5))
    return {
        "name": "Temperature",
        "depths": depths,
        "values": [_r(5 + 16 * math.exp(-d / 45) + rng.gauss(0, 0.45), 3) for d in depths],
    }


def _band_dos():
    xs = _linspace(-4, 4, 80)
    return [[x, _r(math.exp(-((x + 2) ** 2)) + 0.6 * math.exp(-((x - 1.2) ** 2) / 1.15), 6)] for x in xs]


def _contour():
    return [
        [_r(math.cos(math.pi / 6 + j * math.pi / 9) * math.cos((i - 12) * 5 * math.pi / 48), 3) for j in range(25)]
        for i in range(25)
    ]


def _parallel_samples(seed=32):
    rng = _rng(seed)
    return [{"group": "AB"[i % 2], "values": [_r(rng.gauss(0.9, 1.1), 3) for _ in range(5)]} for i in range(60)]


def _fit_points(seed=33):
    rng = _rng(seed)
    points = []
    for _ in range(50):
        x = rng.uniform(0.7, 20)
        points.append([_r(x), _r(max(0.9, 0.7 * x + rng.gauss(0, 1.9)))])
    return points


_FIT_POINTS = _fit_points()
_VIOLIN_GROUPS = _groups(40, (("Control", 2.9, 0.9), ("Low", 3.5, 1.2), ("High", 5.4, 1.6), ("Washout", 3.5, 1.3)), 25)


EXAMPLES: dict[str, dict] = {
    "band_structure": {
        "bands": [
            {"k_points": [0, 0.25, 0.5, 0.75, 1], "energies": [-1, -1.4, -1.8, -1.4, -1], "is_valence": True},
            {"k_points": [0, 0.25, 0.5, 0.75, 1], "energies": [1, 1.4, 1.8, 1.4, 1]},
        ],
        "high_symmetry_points": [[0, "G"], [0.5, "X"], [1, "M"]],
        "dos_data": _band_dos(),
    },
    "bar_academic": {
        "groups": _groups(41, [(f"Cond {i}", 2.9 + 0.65 * i - 0.1 * i * i, 1.1) for i in range(4)], 28, 4),
        "y_unit": "a.u.",
    },
    "boxplot": {"groups": _groups(42, _DOSE_GROUPS, 25)},
    "bubble": {
        "points": [
            {"x": 65, "y": 44, "size": 93, "label": "US"},
            {"x": 68, "y": 78, "size": 78, "label": "CN"},
            {"x": 35, "y": 72, "size": 93, "label": "IN"},
            {"x": 55, "y": 66, "size": 9, "label": "DE"},
            {"x": 32, "y": 46, "size": 118, "label": "JP"},
            {"x": 71, "y": 54, "size": 94, "label": "BR"},
            {"x": 35, "y": 71, "size": 89, "label": "FR"},
            {"x": 68, "y": 74, "size": 112, "label": "GB"},
            {"x": 83, "y": 86, "size": 56, "label": "IT"},
            {"x": 58, "y": 50, "size": 61, "label": "RU"},
        ],
    },
    "calheat": {"values": _calheat()},
    "candle": _candle(),
    "clustered_heatmap": {
        "matrix": [
            [-0.95, -0.46, -0.6, -0.32, 0.72, -1.72, -0.34, -0.49],
            [-0.88, -0.12, 0, 2.47, 0.3, -0.01, 0.87, -1.05],
            [-0.6, 0.55, -0.5, -0.98, -0.58, -1.35, 1.15, 1.27],
            [2.62, -0.29, -0.23, -0.2, 0.54, 0.01, 0.79, -0.31],
            [-1.43, 1.59, -0.5, 1.16, -0.34, 0.14, -1.66, -0.98],
            [0.4, 0.59, -0.23, 0.14, -1.85, 0.04, -0.68, -1.03],
            [0.35, -0.45, -0.88, -0.4, -0.39, -0.29, 0.07, -0.44],
            [0.91, 1.57, 1.01, -0.34, -0.64, 0.39, -0.21, 1.37],
            [0.22, 0.45, -0.58, 0.16, -1.1, -1.49, 0.2, -1.13],
            [-0.61, 0.87, 1.58, 0.05, -0.43, 0.76, 0.96, 0.52],
            [-0.86, -0.49, 1.02, -1.09, 0.07, 1.22, 1.03, -0.65],
            [-0.29, -0.22, -1.11, 0.07, -0.85, 0.61, -1.07, -0.63],
        ],
        "row_labels": [
            "Gene_1",
            "Gene_2",
            "Gene_3",
            "Gene_4",
            "Gene_5",
            "Gene_6",
            "Gene_7",
            "Gene_8",
            "Gene_9",
            "Gene_10",
            "Gene_11",
            "Gene_12",
        ],
        "col_labels": ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8"],
    },
    "composite": {"data": [{"name": name, "series": _composite_series()} for name in ("Condition A", "Condition B")]},
    "contour": {"grid": _contour(), "slice_x": 0, "slice_y": 0},
    "depth_profile": {"series": [_depth_profile()]},
    "dose_response": {"points": _dose_response()},
    "dot_matrix": {
        "size_matrix": [
            [0.45, 0.56, 0.92, 0.47],
            [0.51, 0.59, 0.18, 0.51],
            [0.63, 0.79, 0.09, 0.3],
            [0.09, 0.81, 0.69, 0.04],
            [0.98, 0.96, 0.65, 0.62],
        ],
        "color_matrix": [
            [-1.37, -1.94, 0.11, -1.76],
            [-1.24, -1.03, -1.88, -0.14],
            [-0.24, 1.37, 0.08, 0.56],
            [0, 0.65, -0.17, -0.89],
            [1.99, 1.98, 1.36, 0.83],
        ],
        "row_labels": ["Enriched up", "Enriched down", "Shared", "Unique A", "Unique B"],
        "col_labels": ["Cluster 1", "Cluster 2", "Cluster 3", "Cluster 4"],
    },
    "dot_plot_scrna": {
        "genes": ["A", "B", "C"],
        "clusters": ["T", "B", "NK"],
        "pct_expr": [[80, 10, 5], [10, 85, 20], [5, 20, 75]],
        "mean_expr": [[2, 0.4, 0.1], [0.4, 2.5, 0.8], [0.1, 0.8, 2.2]],
    },
    "coef_plot": {
        "series": [
            {
                "name": "TWFE",
                "points": [
                    {"x": -4, "y": 0.01, "lo": -0.02, "hi": 0.04},
                    {"x": -3, "y": -0.005, "lo": -0.035, "hi": 0.025},
                    {"x": -2, "y": 0.008, "lo": -0.022, "hi": 0.038},
                    {"x": 0, "y": -0.02, "lo": -0.05, "hi": 0.01},
                    {"x": 1, "y": -0.035, "lo": -0.065, "hi": -0.005},
                    {"x": 2, "y": -0.05, "lo": -0.08, "hi": -0.02},
                    {"x": 3, "y": -0.045, "lo": -0.075, "hi": -0.015},
                ],
            }
        ],
        "x_title": "Years relative to policy",
        "y_title": "Log employment",
        "base_x": -1,
        "ci_level": 95,
    },
    "dumbbell": {
        "rows": [
            {"label": "Alpha", "before": 29.7, "after": 60.3},
            {"label": "Beta", "before": 39.5, "after": 57.5},
            {"label": "Gamma", "before": 36.1, "after": 67.8},
            {"label": "Delta", "before": 21.7, "after": 72.8},
            {"label": "Epsilon", "before": 21.1, "after": 70.2},
        ],
    },
    "forest": {
        "rows": [
            {"label": "ALPHA", "subgroup": "Age < 60", "estimate": 0.322, "ci_lo": 0.089, "ci_hi": 0.556},
            {"label": "BETA", "subgroup": "Age < 60", "estimate": 0.292, "ci_lo": 0.091, "ci_hi": 0.493},
            {"label": "GAMMA", "subgroup": "Age < 60", "estimate": 0.328, "ci_lo": 0.093, "ci_hi": 0.562},
            {"label": "DELTA", "subgroup": "Age < 60", "estimate": 0.465, "ci_lo": 0.291, "ci_hi": 0.639},
            {"label": "ALPHA", "subgroup": "Age ≥ 60", "estimate": 0.889, "ci_lo": 0.844, "ci_hi": 0.933},
            {"label": "BETA", "subgroup": "Age ≥ 60", "estimate": 0.509, "ci_lo": 0.22, "ci_hi": 0.797},
            {"label": "GAMMA", "subgroup": "Age ≥ 60", "estimate": 0.468, "ci_lo": 0.279, "ci_hi": 0.658},
            {"label": "DELTA", "subgroup": "Age ≥ 60", "estimate": 0.491, "ci_lo": 0.214, "ci_hi": 0.768},
        ],
    },
    "funnel_classic": {
        "stages": [10000, 6200, 3400, 1800, 920, 310],
        "stage_labels": ["曝光", "点击", "注册", "试用", "付费", "续费"],
        "stage_descriptions": ["首页展示", "点击落地页", "完成注册", "7 天内试用", "首单付费", "次月续费"],
    },
    "gantt": {
        "tasks": [
            ["设计评审", 0, 2, 0],
            ["原型开发", 2, 7, 1],
            ["内部测试", 7, 10, 1],
            ["用户研究", 4, 8, 0],
            ["正式开发", 10, 16, 1],
            ["压力测试", 16, 18, 1],
            ["发布准备", 18, 20, 0],
        ],
        "weeks": 20,
        "critical_index": 1,
        "milestones": [[10, "原型完成"], [20, "正式发布"]],
    },
    "grouped_bar": {
        "categories": ["T0", "T1", "T2"],
        "series": [["Control", [[1, 2, 3], [2, 3, 4], [3, 4, 5]]], ["Treated", [[2, 3, 4], [4, 5, 6], [5, 6, 7]]]],
    },
    "histogram": {"values": _normal(55, 120, 4.9, 1.45, 4), "bins": 20},
    "hr_diagram": {
        "stars": [
            {"temp": 5778, "luminosity": 1, "name": "Sun"},
            {"temp": 9000, "luminosity": 25, "name": "A"},
            {"temp": 3500, "luminosity": 0.03, "name": "B"},
            {"temp": 4500, "luminosity": 100, "name": "C"},
        ],
    },
    "kinetics": {"curves": _kinetics()},
    "km_survival": {"groups": [_km_group(50, "Control", 10.5, 0.8), _km_group(51, "Treated", 22, 0.82)]},
    "line_band": {"series": _line_band()},
    "marimekko": {
        "markets": [
            ["中国", 1200, [["Brand A", 31], ["Brand B", 26], ["Brand C", 33], ["其他", 10]]],
            ["美国", 950, [["Brand A", 15], ["Brand B", 22], ["Brand C", 15], ["其他", 48]]],
            ["欧洲", 820, [["Brand A", 27], ["Brand B", 26], ["Brand C", 17], ["其他", 30]]],
            ["东南亚", 460, [["Brand A", 28], ["Brand B", 24], ["Brand C", 25], ["其他", 23]]],
            ["日韩", 310, [["Brand A", 18], ["Brand B", 33], ["Brand C", 31], ["其他", 18]]],
        ],
    },
    "matrix_heat": {
        "matrix": [
            [-0.15, -0.51, -1.45, 1.47, -1.97, 0.01],
            [1.59, -1.68, 0.22, 0.47, -1.84, -0.48],
            [0.81, -0.19, 0.9, -1.37, -1.05, -1.56],
            [0.03, 1.7, 0.36, 1.1, -0.47, 0.98],
            [-1.59, -0.84, 0.7, 0.9, -0.31, -1.65],
            [-0.93, -1.16, -0.88, 1.24, -1.2, 1.55],
        ],
        "row_labels": ["Patient A", "Patient B", "Patient C", "Patient D", "Patient E", "Patient F"],
        "col_labels": ["IFN-α", "IFN-γ", "IL-2", "IL-6", "TNF-α", "IL-10"],
        "colorbar_label": "Z score",
    },
    "nested_donut": {"data": [["Domain A", 60, [["A1", 35], ["A2", 25]]], ["Domain B", 40, [["B1", 25], ["B2", 15]]]]},
    "network": {
        "nodes": [
            {"id": "A", "category": "core"},
            {"id": "B", "category": "core"},
            {"id": "C", "category": "core"},
            {"id": "D", "category": "leaf"},
            {"id": "E", "category": "leaf"},
            {"id": "F", "category": "leaf"},
            {"id": "G", "category": "leaf"},
            {"id": "H", "category": "leaf"},
        ],
        "edges": [
            {"source": "A", "target": "C", "weight": 0.36},
            {"source": "A", "target": "E", "weight": 0.82},
            {"source": "A", "target": "G", "weight": 0.75},
            {"source": "C", "target": "E", "weight": 0.95},
            {"source": "C", "target": "F", "weight": 0.3},
            {"source": "D", "target": "H", "weight": 0.97},
            {"source": "E", "target": "F", "weight": 0.63},
            {"source": "E", "target": "G", "weight": 0.24},
            {"source": "E", "target": "H", "weight": 0.68},
        ],
    },
    "nyquist_bode": {"nyquist_points": [[i, _r(0.3 * i * (10 - i)), _r(100 / (i + 1), 8)] for i in range(11)]},
    "pairs": {"data": _pairs(), "variables": ["a", "b", "c"]},
    "parallel_coords": {
        "axes": [["m1", ""], ["m2", ""], ["m3", "ms"], ["m4", "$"], ["m5", ""]],
        "samples": _parallel_samples(),
    },
    "percent_grid": {"options": [["非常满意", 32], ["基本满意", 44], ["一般", 15], ["不太满意", 7], ["非常不满意", 2]]},
    "phase_diagram": {
        "regions": [
            {"name": "Solid", "boundary": [[0.5, 1], [1, 50], [1.5, 110], [2, 180]]},
            {"name": "Liquid", "boundary": [[1, 50], [1.5, 110], [2, 180], [2.5, 260]]},
            {"name": "Gas", "boundary": [[0, 0], [0.5, 50], [1, 180], [2, 260]]},
        ],
    },
    "phylogeny": {"tree": "((Human:0.1,Chimp:0.1):0.2,(Mouse:0.4,Rat:0.4):0.3,(Chicken:0.6,Finch:0.5):0.4);"},
    "population_pyramid": {
        "categories": ["0-9", "10-19", "20-29", "30-39", "40-49", "50-59", "60-69", "70-79", "80+"],
        "left_values": [14.06, 11.86, 12.67, 14.05, 7.6, 11.36, 14.05, 13.72, 10.73],
        "right_values": [6.69, 9.12, 14.94, 6.03, 8.19, 14.5, 9.49, 7.09, 8.17],
    },
    "potential_energy_surface": {
        "curve": [[0, 0], [1, 3], [2, 8], [3, 3], [4, -2]],
        "states": [
            {"x": 0, "y": 0, "label": "Reactant"},
            {"x": 2, "y": 8, "label": "Transition", "kind": "ts"},
            {"x": 4, "y": -2, "label": "Product"},
        ],
    },
    "pseudotime": _pseudotime(),
    "quadrant_2x2": {
        "items": [
            {"name": "A", "x": 6.48, "y": 7.01, "highlight": False},
            {"name": "B", "x": 1.96, "y": 0.65, "highlight": False},
            {"name": "C", "x": 3.33, "y": 3.72, "highlight": False},
            {"name": "D", "x": 1.83, "y": 9.1, "highlight": False},
            {"name": "E", "x": 0.71, "y": 9.18, "highlight": False},
            {"name": "F", "x": 0.79, "y": 8.39, "highlight": False},
            {"name": "G", "x": 7.4, "y": 6.58, "highlight": False},
            {"name": "H", "x": 0.12, "y": 9.74, "highlight": False},
            {"name": "I", "x": 2.53, "y": 6.12, "highlight": False},
            {"name": "J", "x": 6.5, "y": 7.04, "highlight": False},
            {"name": "K", "x": 0.99, "y": 3.92, "highlight": False},
            {"name": "L", "x": 7.49, "y": 9.31, "highlight": False},
        ],
        "x_title": "Market share",
        "y_title": "Growth rate",
    },
    "radar": {
        "axes": [
            {"name": "Speed", "min": 0, "max": 10},
            {"name": "Accuracy", "min": 0, "max": 100},
            {"name": "Recall", "min": 0, "max": 1},
            {"name": "F1", "min": 0, "max": 1},
            {"name": "Latency", "min": 0, "max": 500},
            {"name": "Cost", "min": 0, "max": 1000},
        ],
        "series": [
            {"name": "Model A", "values": [9.25, 94.86, 0.89, 0.08, 296.01, 423.75]},
            {"name": "Model B", "values": [5.3, 13.03, 0.19, 0.44, 110.52, 455.03]},
            {"name": "Model C", "values": [0.25, 8.58, 0.71, 0.42, 256.32, 734.21]},
        ],
    },
    "raincloud": {"groups": _VIOLIN_GROUPS},
    "ridge": {
        "distributions": [_normal(53 + i, 60, 50 + i, 10) for i in range(10)],
        "group_labels": [str(2015 + i) for i in range(10)],
    },
    "roc_pr": _roc_pr(),
    "sankey": {
        "left_nodes": ["煤", "天然气", "核能", "水电", "风电", "光伏"],
        "right_nodes": ["工业", "商业", "居民", "交通", "出口"],
        "flows": [
            ["煤", "工业", 420],
            ["煤", "商业", 60],
            ["天然气", "工业", 180],
            ["天然气", "居民", 90],
            ["核能", "工业", 110],
            ["核能", "商业", 40],
            ["水电", "工业", 90],
            ["水电", "居民", 50],
            ["风电", "居民", 30],
            ["风电", "交通", 20],
            ["光伏", "居民", 40],
            ["光伏", "出口", 15],
        ],
    },
    "scatter": {"points": [_scatter_series(65, "Control", 0.62, 0.75), _scatter_series(66, "Treated", 0.75, 1.1)]},
    "scatter_fit": {"points": _FIT_POINTS},
    "seismic_waveform": {"traces": _seismic()},
    "spectrum": _spectrum(),
    "stress_strain": {
        "curve": [[0, 0], [0.002, 300], [0.02, 400], [0.06, 500], [0.1, 450]],
        "yield_point": [0.002, 300],
        "ultimate_point": [0.06, 500],
        "fracture_point": [0.1, 450],
    },
    "swimmer": {"patients": _swimmer()},
    "ternary": {"points": _ternary()},
    "time_latitude": _time_latitude(),
    "titration": {
        "volume": [0, 5, 10, 15, 20, 25, 30, 35, 40],
        "ph_or_response": [2, 2.5, 3, 3.7, 5, 9, 11, 11.5, 12],
        "equivalence_points": [23],
    },
    "umap_cluster": {
        "points": _umap(),
        "marker_data": {
            "genes": ["GENE1", "GENE2", "GENE3"],
            "clusters": ["C0", "C1", "C2"],
            "mean_expr": [[0.5, 0.9, 0.5], [0.9, 0.5, 0.9], [0.5, 0.9, 0.5]],
            "pct_expr": [[20, 45, 70], [45, 70, 20], [70, 20, 45]],
        },
    },
    "upset": {
        "sets": {
            name: _set_members(70 + i, k)
            for i, (name, k) in enumerate((("Dataset A", 54), ("Dataset B", 58), ("Dataset C", 31), ("Dataset D", 53)))
        }
    },
    "vector_field": {
        "x_coords": list(range(-8, 9)),
        "y_coords": list(range(-5, 6)),
        "grid": [[[_r(-0.1 * y, 1), _r(0.1 * x, 1)] for x in range(-8, 9)] for y in range(-5, 6)],
    },
    "violin": {"groups": _VIOLIN_GROUPS},
    "volcano": {"points": _volcano(), "top_k_labels": 8},
    "waterfall": {"steps": [["Start", 100, "total"], ["Gain", 20, "pos"], ["Loss", 5, "neg"], ["End", 115, "total"]]},
}
