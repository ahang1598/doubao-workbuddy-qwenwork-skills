#!/usr/bin/env python3
"""internet-data-analysis 配套计算工具（纯标准库，无 pandas/scipy 依赖）。

用途：提供漏斗和常见实验设计的确定性计算，减少分母、独立性和检验口径错误。
遇到这些计算时**优先跑本脚本**，不要现场手推公式（分母/单双尾/合并方差最易出错）。

用法（命令行）：
  python3 analysis_toolkit.py funnel 曝光=10000 点击=3200 加购=890 下单=210
  python3 analysis_toolkit.py ab_rate nA=1000 xA=120 nB=1000 xB=135 ratio=1:1
  python3 analysis_toolkit.py ab_paired_binary both_correct=100 treatment_only=20 control_only=15 both_wrong=10
  python3 analysis_toolkit.py srm nA=1000 nB=1000 ratio=1:1
  python3 analysis_toolkit.py mde n=1000 base=0.10
也可 import 后调用同名函数，返回 dict。
"""
import math
import random
import sys


def _norm_cdf(z):
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def _chi2_1df_p(x):
    """自由度 1 的卡方分布右尾 p 值。"""
    return math.erfc(math.sqrt(x / 2))


def _quantile(sorted_values, q):
    pos = (len(sorted_values) - 1) * q
    lo, hi = int(math.floor(pos)), int(math.ceil(pos))
    if lo == hi:
        return sorted_values[lo]
    weight = pos - lo
    return sorted_values[lo] * (1 - weight) + sorted_values[hi] * weight


def _exact_binomial_two_sided(k, n):
    """H0: p=0.5 的双侧精确二项检验。"""
    if n == 0:
        return 1.0
    observed = math.comb(n, k) * 0.5 ** n
    return min(1.0, sum(
        math.comb(n, i) * 0.5 ** n
        for i in range(n + 1)
        if math.comb(n, i) * 0.5 ** n <= observed + 1e-15
    ))


def funnel(**steps):
    """漏斗：按传入顺序算逐步/累计转化率、流失量、占总流失比。
    输入: 步骤名=人数（保持顺序）。"""
    names = list(steps.keys())
    counts = [float(steps[k]) for k in names]
    total_loss = counts[0] - counts[-1]
    rows = []
    for i, (n, c) in enumerate(zip(names, counts)):
        row = {"step": n, "count": int(c),
               "step_conv": None if i == 0 else round(c / counts[i-1], 4),
               "cum_conv": round(c / counts[0], 4),
               "loss": None if i == 0 else int(counts[i-1] - c),
               "loss_share": None if i == 0 or total_loss <= 0
               else round((counts[i-1] - c) / total_loss, 4)}
        rows.append(row)
    worst_rate = min((r for r in rows if r["step_conv"] is not None),
                     key=lambda r: r["step_conv"])
    worst_loss = max((r for r in rows if r["loss"] is not None),
                     key=lambda r: r["loss"])
    return {"rows": rows, "overall_conv": round(counts[-1] / counts[0], 4),
            "worst_step_by_rate": worst_rate["step"],
            "worst_step_by_loss": worst_loss["step"],
            "note": "转化率最低的步 和 绝对流失最大的步 可能不同，都要报"}


def srm(nA, nB, ratio="1:1"):
    """已知预期随机分流比例时的 Sample Ratio Mismatch 检查。"""
    nA, nB = float(nA), float(nB)
    a, b = (float(x) for x in str(ratio).split(":"))
    tot = nA + nB
    eA, eB = tot * a / (a + b), tot * b / (a + b)
    chi2 = (nA - eA) ** 2 / eA + (nB - eB) ** 2 / eB
    p = _chi2_1df_p(chi2)
    return {"chi2": round(chi2, 3), "p": round(p, 6),
            "srm_violation": p < 0.001,
            "verdict": "分流比例明显偏离预期，先查分流与数据链路" if p < 0.001 else "未发现明显分流比例异常"}


def ab_rate(nA, xA, nB, xB, ratio=None):
    """独立两组的两比例 z 检验（B 相对 A）；ratio 提供时才计算 SRM。"""
    nA, xA, nB, xB = float(nA), float(xA), float(nB), float(xB)
    s = srm(nA, nB, ratio) if ratio not in (None, "", "none", "None") else None
    pA, pB = xA / nA, xB / nB
    pool = (xA + xB) / (nA + nB)
    se = math.sqrt(pool * (1 - pool) * (1 / nA + 1 / nB))
    z = (pB - pA) / se if se else 0.0
    p_two = 2 * (1 - _norm_cdf(abs(z)))
    se_d = math.sqrt(pA * (1 - pA) / nA + pB * (1 - pB) / nB)
    lo, hi = (pB - pA) - 1.96 * se_d, (pB - pA) + 1.96 * se_d
    return {"rate_A": round(pA, 5), "rate_B": round(pB, 5),
            "abs_diff": round(pB - pA, 5),
            "rel_lift": round((pB - pA) / pA, 4) if pA else None,
            "ci95_abs": [round(lo, 5), round(hi, 5)],
            "z": round(z, 3), "p": round(p_two, 5),
            "significant": p_two < 0.05 and not (lo <= 0 <= hi),
            "srm": s,
            "note": "仅用于独立两组；显著性需结合效应大小、区间和决策成本解释"}


def ab_paired_binary(
    both_correct,
    treatment_only,
    control_only,
    both_wrong,
    bootstrap=10000,
    seed=42,
    alpha=0.05,
):
    """成对二元结果：精确 McNemar + 按配对单位 Bootstrap 差值区间。"""
    both_correct = int(float(both_correct))
    treatment_only = int(float(treatment_only))
    control_only = int(float(control_only))
    both_wrong = int(float(both_wrong))
    bootstrap = int(float(bootstrap))
    seed = int(float(seed))
    alpha = float(alpha)
    counts = [both_correct, treatment_only, control_only, both_wrong]
    if any(value < 0 for value in counts) or sum(counts) == 0:
        raise ValueError("四格表计数必须非负且总数大于 0")
    if bootstrap < 1000:
        raise ValueError("bootstrap 次数至少为 1000")

    total = sum(counts)
    discordant = treatment_only + control_only
    treatment_rate = (both_correct + treatment_only) / total
    control_rate = (both_correct + control_only) / total
    diff = treatment_rate - control_rate
    p_exact = _exact_binomial_two_sided(
        min(treatment_only, control_only), discordant
    )

    pair_differences = (
        [0] * both_correct
        + [1] * treatment_only
        + [-1] * control_only
        + [0] * both_wrong
    )
    rng = random.Random(seed)
    bootstrap_diffs = sorted(
        sum(rng.choice(pair_differences) for _ in range(total)) / total
        for _ in range(bootstrap)
    )
    lo_q, hi_q = alpha / 2, 1 - alpha / 2
    return {
        "pairs": total,
        "four_cell_counts": {
            "both_correct": both_correct,
            "treatment_only": treatment_only,
            "control_only": control_only,
            "both_wrong": both_wrong,
        },
        "treatment_rate": round(treatment_rate, 5),
        "control_rate": round(control_rate, 5),
        "abs_diff": round(diff, 5),
        "rel_lift": round(diff / control_rate, 4) if control_rate else None,
        "discordant_pairs": discordant,
        "mcnemar_exact_two_sided_p": round(p_exact, 6),
        "ci_abs_paired_bootstrap": [
            round(_quantile(bootstrap_diffs, lo_q), 5),
            round(_quantile(bootstrap_diffs, hi_q), 5),
        ],
        "alpha": alpha,
        "bootstrap_repetitions": bootstrap,
        "bootstrap_seed": seed,
        "test_method": "exact_two_sided_mcnemar",
        "interval_method": "paired_unit_bootstrap_percentile",
        "raw_significant": p_exact < alpha,
        "note": "成对设计专用；不使用独立两比例检验或 SRM；同一决策族有多个检验时须把原始 p 值传给 p_adjust",
    }


def p_adjust(pvalues, method="holm", alpha=0.05):
    """多重比较校正；pvalues 使用逗号分隔。"""
    raw = [float(item.strip()) for item in str(pvalues).split(",") if item.strip()]
    if not raw or any(value < 0 or value > 1 for value in raw):
        raise ValueError("pvalues 必须是 0 到 1 之间、以逗号分隔的数值")
    alpha = float(alpha)
    method = str(method).lower()
    size = len(raw)
    if method == "bonferroni":
        adjusted = [min(1.0, value * size) for value in raw]
    elif method == "holm":
        order = sorted(range(size), key=raw.__getitem__)
        sorted_adjusted = []
        running = 0.0
        for rank, index in enumerate(order):
            candidate = min(1.0, raw[index] * (size - rank))
            running = max(running, candidate)
            sorted_adjusted.append(running)
        adjusted = [0.0] * size
        for index, value in zip(order, sorted_adjusted):
            adjusted[index] = value
    else:
        raise ValueError("method 仅支持 holm 或 bonferroni")
    return {
        "raw_pvalues": raw,
        "adjusted_pvalues": [round(value, 8) for value in adjusted],
        "reject_adjusted": [value < alpha for value in adjusted],
        "family_size": size,
        "method": method,
        "alpha": alpha,
    }


def ab_mean(nA, meanA, stdA, nB, meanB, stdB):
    """两均值 Welch 检验（大样本正态近似）。重尾指标（收入）建议另做截尾均值对照。"""
    nA, meanA, stdA = float(nA), float(meanA), float(stdA)
    nB, meanB, stdB = float(nB), float(meanB), float(stdB)
    se = math.sqrt(stdA ** 2 / nA + stdB ** 2 / nB)
    z = (meanB - meanA) / se if se else 0.0
    p_two = 2 * (1 - _norm_cdf(abs(z)))
    lo, hi = (meanB - meanA) - 1.96 * se, (meanB - meanA) + 1.96 * se
    return {"diff": round(meanB - meanA, 5),
            "rel_lift": round((meanB - meanA) / meanA, 4) if meanA else None,
            "ci95": [round(lo, 5), round(hi, 5)],
            "z": round(z, 3), "p": round(p_two, 5),
            "significant": p_two < 0.05 and not (lo <= 0 <= hi)}


def mde(n, base, power=0.8, alpha=0.05):
    """当前每组样本量 n 下能检测到的最小相对效应（80% 功效，双尾 5%）。
    不显著时用它回答"能排除多大的效应"。"""
    n, base = float(n), float(base)
    z_a, z_b = 1.96, {0.8: 0.8416, 0.9: 1.2816}.get(power, 0.8416)
    se = math.sqrt(2 * base * (1 - base) / n)
    abs_mde = (z_a + z_b) * se
    return {"abs_mde": round(abs_mde, 5), "rel_mde": round(abs_mde / base, 4),
            "note": f"独立两组近似：当前样本量下，小于 {round(abs_mde/base*100,1)}% 的相对变化检测不出来"}


if __name__ == "__main__":
    import json
    if len(sys.argv) < 2 or sys.argv[1] not in (
        "funnel", "ab_rate", "ab_paired_binary", "ab_mean", "srm", "mde",
        "p_adjust"
    ):
        print(__doc__)
        sys.exit(1)
    fn = {
        "funnel": funnel,
        "ab_rate": ab_rate,
        "ab_paired_binary": ab_paired_binary,
        "ab_mean": ab_mean,
        "srm": srm,
        "mde": mde,
        "p_adjust": p_adjust,
    }[sys.argv[1]]
    kwargs = {}
    for arg in sys.argv[2:]:
        k, v = arg.split("=", 1)
        kwargs[k] = v
    print(json.dumps(fn(**kwargs), ensure_ascii=False, indent=1))
