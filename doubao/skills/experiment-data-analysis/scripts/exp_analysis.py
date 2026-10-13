#!/usr/bin/env python3
"""
Experiment Data Analysis Toolkit
=================================
被试间实验数据分析：信度 → 操纵检验 → ANOVA决策树 → 交互图 → 被调节的中介(PROCESS)

用法:
  python exp_analysis.py config.json
  python exp_analysis.py --help

退出码:
  0 = 成功
  1 = 配置错误（缺字段/文件不存在/变量缺失）
  2 = 数据格式不支持
  3 = 统计执行错误

配置文件格式见 config_example.json 或 references/config_guide.md。
"""
import sys, json, os, argparse, warnings
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.formula.api import ols
import pingouin as pg

warnings.filterwarnings('ignore')

# ──────────────────────── 退出码 ────────────────────────
EXIT_OK = 0
EXIT_CONFIG_ERROR = 1
EXIT_DATA_FORMAT = 2
EXIT_STATS_ERROR = 3


class ConfigError(Exception):
    """配置文件校验错误"""
    pass

# ──────────────────────── 配置校验 ────────────────────────

def validate_config(config):
    """校验配置文件，返回(ok, errors)。errors为字符串列表。"""
    errors = []

    # 必需顶层字段
    for field in ['data_file', 'output_dir', 'factors', 'dvs']:
        if field not in config:
            errors.append(f"缺少必需字段: '{field}'")

    if errors:
        return errors

    # 数据文件存在性
    if not os.path.isfile(config['data_file']):
        errors.append(f"数据文件不存在: {config['data_file']}")

    # factors
    if not isinstance(config['factors'], dict) or len(config['factors']) == 0:
        errors.append("'factors' 必须为非空对象")
    else:
        for fname, finfo in config['factors'].items():
            if not isinstance(finfo, dict):
                errors.append(f"factors.{fname} 必须为对象")
                continue
            if 'levels' not in finfo:
                errors.append(f"factors.{fname} 缺少 'levels' 字段（原始值→0/1映射）")

    # scales（可选）
    scales = config.get('scales', {})
    if scales and not isinstance(scales, dict):
        errors.append("'scales' 必须为对象 {量表名: [题项列名]}")

    # manipulation_checks（可选）
    for i, chk in enumerate(config.get('manipulation_checks', [])):
        if not isinstance(chk, dict):
            errors.append(f"manipulation_checks[{i}] 必须为对象")
            continue
        for field in ['iv', 'check_var']:
            if field not in chk:
                errors.append(f"manipulation_checks[{i}] 缺少 '{field}'")
        if chk.get('type') == 'categorical' and 'correct_values' not in chk:
            errors.append(f"manipulation_checks[{i}] 为categorical类型但缺少 'correct_values'")

    # dvs
    if not isinstance(config['dvs'], dict) or len(config['dvs']) == 0:
        errors.append("'dvs' 必须为非空对象 {列名: 显示名}")

    # mediation（可选）
    med = config.get('mediation')
    if med:
        if not isinstance(med, dict):
            errors.append("'mediation' 必须为对象")
        else:
            for field in ['X', 'M', 'Y_cols']:
                if field not in med:
                    errors.append(f"mediation 缺少 '{field}'")
            if 'Y_cols' in med and not isinstance(med.get('Y_cols'), list):
                errors.append("mediation.Y_cols 必须为数组")

    return errors


def validate_columns(df, config):
    """校验数据中是否存在配置引用的所有列，返回错误列表"""
    errors = []

    # factors source_col
    for fname, finfo in config['factors'].items():
        src = finfo.get('source_col', fname)
        if src not in df.columns:
            errors.append(f"自变量 {fname}: 数据中找不到列 '{src}'")

    # scales items
    for sname, items in config.get('scales', {}).items():
        missing = [it for it in items if it not in df.columns]
        if missing:
            errors.append(f"量表 {sname}: 以下题项在数据中不存在: {missing}")

    # manipulation checks
    for i, chk in enumerate(config.get('manipulation_checks', [])):
        var = chk.get('check_var', '')
        if var and var not in df.columns:
            errors.append(f"操纵检验[{i}] {chk.get('label','')}: 数据中找不到列 '{var}'")

    # dvs
    for dv_col in config.get('dvs', {}):
        if dv_col not in df.columns:
            errors.append(f"因变量 '{dv_col}' 在数据中不存在（注意：scales中定义的量表名会自动创建）")

    # mediation
    med = config.get('mediation', {})
    if med:
        for field in ['X', 'W', 'Z', 'M']:
            val = med.get(field)
            if val and val not in df.columns:
                errors.append(f"mediation.{field} = '{val}' 在数据中不存在")
        for y in med.get('Y_cols', []):
            if y not in df.columns:
                errors.append(f"mediation.Y_cols 中的 '{y}' 在数据中不存在")

    return errors


# ──────────────────────── 工具函数 ────────────────────────

def sig(p):
    if p < 0.001: return '***'
    if p < 0.01:  return '**'
    if p < 0.05:  return '*'
    if p < 0.10:  return '†'
    return ''

def load_data(path):
    """加载 .sav 或 .csv 文件"""
    ext = os.path.splitext(path)[1].lower()
    if ext == '.sav':
        try:
            import pyreadstat
        except ImportError:
            raise ConfigError("读取.sav文件需要pyreadstat，请运行: pip install pyreadstat")
        df, meta = pyreadstat.read_sav(path)
        return df, meta
    elif ext == '.csv':
        try:
            return pd.read_csv(path), None
        except Exception as e:
            raise ConfigError(f"CSV文件读取失败: {e}")
    else:
        raise ConfigError(f"不支持的文件格式: {ext}，请使用 .sav 或 .csv")

def build_scales(df, scales):
    """构建量表均值，返回 (df, reliability_dict)
    scales: {scale_name: [item1, item2, ...]}
    """
    rel = {}
    for name, items in scales.items():
        available = [c for c in items if c in df.columns]
        if not available:
            print(f"  ⚠️ 量表 {name}: 所有题项均未找到，跳过")
            continue
        df[name] = df[available].mean(axis=1)
        if len(available) >= 2:
            alpha = pg.cronbach_alpha(df[available])[0]
            rel[name] = {'items': available, 'alpha': alpha, 'n_items': len(available)}
        else:
            rel[name] = {'items': available, 'alpha': None, 'n_items': 1}
    return df, rel

def encode_factors(df, factors):
    """将自变量编码为0/1（或保留原值），重命名为简称，并添加标签
    factors: {col_or_name: {'label': str, 'source_col': str(数据列名, 可选),
                            'levels': {old: new}, 'level_labels': [str, str]}}
    - 若提供 source_col，则从该列读取数据并重命名为 key
    - 若 levels 中键为字符串数字，自动转为 float
    """
    rename_map = {}
    for col, info in factors.items():
        src = info.get('source_col', col)
        if src != col:
            df[col] = df[src]
            rename_map[src] = col
        if 'levels' in info:
            mapping = {}
            for k, v in info['levels'].items():
                try:
                    mapping[float(k)] = v
                except (ValueError, TypeError):
                    mapping[k] = v
            df[col] = df[col].map(mapping)
        if 'level_labels' not in info:
            info['level_labels'] = [f'水平{i}' for i in sorted(df[col].dropna().unique())]
    return df

# ──────────────────────── 信度报告 ────────────────────────

def report_reliability(rel):
    lines = []
    lines.append("## 一、信度分析\n")
    lines.append("| 量表 | 题项数 | Cronbach's α | 评价 |")
    lines.append("|---|---|---|---|")
    for name, r in rel.items():
        a = r['alpha']
        if a is None:
            eval_ = '单题项'
        elif a >= 0.9: eval_ = '优秀'
        elif a >= 0.8: eval_ = '良好'
        elif a >= 0.7: eval_ = '可接受'
        elif a >= 0.6: eval_ = '偏低，需说明'
        else: eval_ = '不可接受'
        lines.append(f"| {name} | {r['n_items']} | {a:.3f} | {eval_} |")
    return '\n'.join(lines)

# ──────────────────────── 操纵检验 ────────────────────────

def manipulation_check(df, factors, checks):
    """
    操纵检验，支持三种情境：
    1. 单因素2水平：独立样本t检验 + 方向检验
    2. 单因素3+水平：one-way ANOVA + Tukey事后检验
    3. 多因素设计：对每个连续型check跑全因素ANOVA（主效应精准命中+无交叉污染+无交互）
    4. 分类变量：卡方检验 + 正确率

    checks配置项:
      iv: 对应自变量列名
      check_var: 检验变量列名
      label: 检验题描述
      type: "continuous"(默认) 或 "categorical"
      expected_direction: "high"(iv=1组应更高) 或 "low"(iv=0组应更高)，仅2水平连续型
      correct_values: {iv_level: correct_value}，分类变量各组正确答案
      correct_threshold: 正确率阈值，默认0.80
    """
    lines = []
    lines.append("\n## 二、操纵检验\n")
    fcols = list(factors.keys())
    n_factors = len(fcols)

    # 分离连续型和分类型check
    cont_checks = [c for c in checks if c.get('type', 'continuous') == 'continuous']
    cat_checks  = [c for c in checks if c.get('type', 'continuous') == 'categorical']

    # ── 连续型操纵检验 ──
    if cont_checks:
        if n_factors == 1:
            # 单因素设计
            iv = fcols[0]
            n_levels = df[iv].nunique()
            if n_levels == 2:
                lines.append("### 连续型检验（独立样本 t 检验）\n")
                lines.append("| 检验题 | 组1 M(SD) | 组2 M(SD) | t | p | d | 方向 | 结论 |")
                lines.append("|---|---|---|---|---|---|---|---|")
                for chk in cont_checks:
                    lines.append(_mc_t_test(df, factors, chk))
            else:
                lines.append("### 连续型检验（单因素 ANOVA + Tukey HSD）\n")
                for chk in cont_checks:
                    lines.append(_mc_oneway_anova(df, factors, chk))
        else:
            # 多因素设计：对每个check跑全因素ANOVA
            lines.append("### 连续型检验（多因素 ANOVA：主效应精准命中 + 无交叉污染 + 无交互）\n")
            for chk in cont_checks:
                lines.append(_mc_factorial(df, factors, chk))

    # ── 分类型操纵检验 ──
    if cat_checks:
        lines.append("\n### 分类型检验（卡方检验 + 正确率）\n")
        lines.append("| 检验题 | 组别 | 正确 n | 总 n | 正确率 | χ² | p | 结论 |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for chk in cat_checks:
            lines.append(_mc_chi_square(df, factors, chk))

    return '\n'.join(lines)


def _mc_t_test(df, factors, chk):
    """单因素2水平：t检验 + 方向检验"""
    iv = chk['iv']; var = chk['check_var']; label = chk.get('label', var)
    direction = chk.get('expected_direction', None)
    if iv not in df.columns or var not in df.columns:
        return f"| {label} | — | — | — | — | — | — | ⚠️变量缺失 |"
    levels = sorted(df[iv].dropna().unique())
    g0 = df[df[iv]==levels[0]][var].dropna()
    g1 = df[df[iv]==levels[1]][var].dropna()
    res = pg.ttest(g0, g1)
    t = res.iloc[0]['T']; p = res.iloc[0]['p_val']; d = res.iloc[0]['cohen_d']
    ll = factors[iv].get('level_labels', [str(levels[0]), str(levels[1])])
    # 方向检验
    dir_ok = True; dir_str = '—'
    if direction == 'high':
        dir_ok = g1.mean() > g0.mean()
        dir_str = f'{ll[1]}>{ll[0]}' if dir_ok else f'方向反了({ll[1]}<{ll[0]})'
    elif direction == 'low':
        dir_ok = g0.mean() > g1.mean()
        dir_str = f'{ll[0]}>{ll[1]}' if dir_ok else f'方向反了({ll[0]}<{ll[1]})'
    passed = p < 0.05 and dir_ok
    concl = '✅ 通过' if passed else ('❌ 未通过' if p >= 0.05 else '⚠️ 方向不符')
    return (f"| {label} | {ll[0]}: {g0.mean():.2f}({g0.std():.2f}) | "
            f"{ll[1]}: {g1.mean():.2f}({g1.std():.2f}) | {t:.3f} | {p:.4f}{sig(p)} | "
            f"{d:.3f} | {dir_str} | {concl} |")


def _mc_oneway_anova(df, factors, chk):
    """单因素3+水平：ANOVA + Tukey"""
    iv = chk['iv']; var = chk['check_var']; label = chk.get('label', var)
    lines = [f"\n**{label}**\n"]
    sub = df[[iv, var]].dropna()
    aov = pg.anova(dv=var, between=iv, data=sub, detailed=True)
    row = aov.iloc[0]
    pcol = 'p_unc' if 'p_unc' in aov.columns else 'p-unc'
    F = row['F']; p = row[pcol]
    lines.append(f"- ANOVA: F({int(row['DF'])}, {int(aov.iloc[1]['DF'])}) = {F:.3f}, p = {p:.4f}{sig(p)}")
    if p < 0.05:
        ph = pg.pairwise_tukey(data=sub, dv=var, between=iv)
        lines.append("- Tukey HSD 事后检验：")
        for _, r in ph.iterrows():
            lines.append(f"  - {r['A']} vs {r['B']}: 均值差={r['diff']:.3f}, p={r['p-tukey']:.4f}{sig(r['p-tukey'])}")
    else:
        lines.append("- ❌ 操纵检验未通过（整体差异不显著）")
    # 各组均值
    ms = sub.groupby(iv)[var].mean()
    lines.append("- 各组均值：" + ", ".join([f"{k}={v:.2f}" for k,v in ms.items()]))
    return '\n'.join(lines)


def _mc_factorial(df, factors, chk):
    """多因素设计：对check变量跑全因素ANOVA，检查精准命中+无交叉污染+无交互"""
    var = chk['check_var']; label = chk.get('label', var)
    target_iv = chk['iv']
    fcols = list(factors.keys())
    lines = [f"\n**{label}**（目标操纵：{target_iv}）\n"]

    formula = var + ' ~ ' + ' * '.join([f'C({c})' for c in fcols])
    try:
        model = ols(formula, data=df).fit()
        aov = sm.stats.anova_lm(model, typ=3).drop('Intercept', errors='ignore')
    except Exception as e:
        lines.append(f"⚠️ ANOVA失败: {e}")
        return '\n'.join(lines)

    lines.append("| 效应 | F | p | η²p | 判断 |")
    lines.append("|---|---|---|---|---|")
    ss_resid = aov.loc['Residual','sum_sq']
    issues = []
    for idx in aov.index:
        if idx == 'Residual': continue
        row = aov.loc[idx]
        F = row['F']; p = row['PR(>F)']; ss = row['sum_sq']
        eta_p = ss / (ss + ss_resid)
        name = idx.replace('C(','').replace(')','').replace(':','×')
        is_target = (name == target_iv)
        is_interaction = ('×' in name)
        # 判断逻辑
        if is_target:
            judge = '✅ 精准命中' if p < 0.05 else '❌ 目标操纵未显著'
            if p >= 0.05: issues.append(f'目标自变量{target_iv}主效应不显著(p={p:.4f})')
        elif is_interaction:
            judge = '✅ 无交互污染' if p >= 0.05 else '⚠️ 存在交互污染'
            if p < 0.05: issues.append(f'{name}交互显著(p={p:.4f})，操纵可能"串味"')
        else:
            judge = '✅ 无交叉污染' if p >= 0.05 else '⚠️ 交叉污染'
            if p < 0.05: issues.append(f'{name}显著影响该检验(p={p:.4f})，存在交叉污染')
        lines.append(f"| {name} | {F:.3f} | {p:.4f}{sig(p)} | {eta_p:.3f} | {judge} |")

    # 各组均值
    lines.append("\n各组均值：")
    cell = df.groupby(fcols)[var].mean().round(3)
    for idx, val in cell.items():
        if not isinstance(idx, tuple): idx = (idx,)
        lines.append(f"- {'×'.join(str(x) for x in idx)}: {val:.3f}")

    if issues:
        lines.append("\n**问题：** " + "；".join(issues))
    else:
        lines.append("\n✅ 操纵检验通过：主效应精准命中，无交叉污染，无交互作用。")
    return '\n'.join(lines)


def _mc_chi_square(df, factors, chk):
    """分类变量：卡方检验 + 正确率"""
    iv = chk['iv']; var = chk['check_var']; label = chk.get('label', var)
    correct_map = chk.get('correct_values', {})
    threshold = chk.get('correct_threshold', 0.80)
    if iv not in df.columns or var not in df.columns:
        return f"| {label} | — | — | — | — | — | — | ⚠️变量缺失 |"

    # 计算各组正确率
    rows = []
    levels = sorted(df[iv].dropna().unique())
    for lv in levels:
        sub = df[df[iv]==lv][var].dropna()
        correct_val = correct_map.get(str(lv), correct_map.get(lv, None))
        if correct_val is not None:
            n_correct = (sub == correct_val).sum()
        else:
            n_correct = 0
        rate = n_correct / len(sub) if len(sub) > 0 else 0
        rows.append((lv, n_correct, len(sub), rate))

    # 卡方检验（组间正确率差异）
    correct_counts = [r[1] for r in rows]
    wrong_counts = [r[2]-r[1] for r in rows]
    table = np.array([correct_counts, wrong_counts]).T
    from scipy.stats import chi2_contingency
    if table.sum() > 0:
        chi2, p, dof, _ = chi2_contingency(table)
    else:
        chi2, p, dof = 0, 1.0, 0

    ll = factors[iv].get('level_labels', [str(lv) for lv in levels])
    lines = []
    all_pass = True
    for i, (lv, nc, nt, rate) in enumerate(rows):
        lname = ll[i] if i < len(ll) else str(lv)
        passed = rate >= threshold
        if not passed: all_pass = False
        lines.append(f"| {label} | {lname} | {nc} | {nt} | {rate:.1%} | {chi2:.3f} | {p:.4f}{sig(p)} | {'✅' if passed else '❌'} |")
    return '\n'.join(lines)

# ──────────────────────── ANOVA 决策树 ────────────────────────

def factorial_anova(df, factors, dv_col, dv_name, section_num=3):
    """
    多因素被试间ANOVA，按决策树执行：
    1. 最高阶交互 → 显著则简单(简单)效应
    2. 不显著则降级看低阶交互
    3. 都不显著看主效应（2水平直接比均值，3+水平做事后检验）
    """
    fcols = list(factors.keys())
    n_factors = len(fcols)
    lines = []

    # Type III ANOVA
    formula = dv_col + ' ~ ' + ' * '.join([f'C({c})' for c in fcols])
    model = ols(formula, data=df).fit()
    aov = sm.stats.anova_lm(model, typ=3).drop('Intercept', errors='ignore')
    ss_resid = aov.loc['Residual','sum_sq']; df_resid = aov.loc['Residual','df']

    cn = ['一','二','三','四','五','六','七','八']
    sec = cn[section_num-1] if section_num <= len(cn) else str(section_num)
    lines.append(f"\n## {sec}、多因素方差分析：{dv_name}\n")

    # Levene's方差齐性检验
    from scipy.stats import levene
    cells = []
    cell_labels = []
    for combo, sub in df.groupby(fcols):
        vals = sub[dv_col].dropna()
        if len(vals) >= 2:
            cells.append(vals.values)
            cell_labels.append(combo if isinstance(combo, tuple) else (combo,))
    if len(cells) >= 2:
        lev_stat, lev_p = levene(*cells, center='median')
        lev_pass = lev_p >= 0.05
        lines.append(f"**Levene方差齐性检验**：W = {lev_stat:.3f}, p = {lev_p:.4f}"
                     + (" ✅ 方差齐性假设成立" if lev_pass else " ⚠️ 方差不齐，结果需谨慎解读，考虑Welch校正或稳健ANOVA"))
        lines.append("")

    lines.append(f"**Type III SS ANOVA**，R² = {model.rsquared:.4f}\n")
    lines.append("| 效应 | SS | df | MS | F | p | η²p |")
    lines.append("|---|---|---|---|---|---|---|")
    effect_map = {}
    for idx in aov.index:
        if idx == 'Residual': continue
        row = aov.loc[idx]
        F = row['F']; p = row['PR(>F)']; ss = row['sum_sq']; dfd = row['df']
        eta_p = ss / (ss + ss_resid)
        name = idx.replace('C(','').replace(')','').replace(':','×')
        lines.append(f"| {name} | {ss:.3f} | {dfd:.0f} | {ss/dfd:.3f} | {F:.3f} | {p:.4f}{sig(p)} | {eta_p:.3f} |")
        effect_map[idx] = {'F':F, 'p':p, 'eta_p':eta_p, 'ss':ss, 'df':dfd}
    lines.append(f"| 残差 | {ss_resid:.3f} | {df_resid:.0f} | {ss_resid/df_resid:.3f} | | | |")

    # ── 决策树 ──
    lines.append(f"\n### 决策树执行\n")

    # 构建交互项层级
    from itertools import combinations
    all_terms = []
    for k in range(n_factors, 0, -1):
        for combo in combinations(fcols, k):
            key = ':'.join([f'C({c})' for c in combo])
            all_terms.append((combo, key))

    # 从最高阶开始找显著交互
    significant_interactions = []
    explored = set()
    for combo, key in all_terms:
        if len(combo) < 2: continue
        if key in effect_map:
            p = effect_map[key]['p']
            if p < 0.05:
                significant_interactions.append((combo, key, p))
                # 标记此交互包含的低阶项为"已被高阶交互涵盖"
                for k2 in range(len(combo)-1, 1, -1):
                    for sub in combinations(combo, k2):
                        explored.add(':'.join([f'C({c})' for c in sub]))

    if significant_interactions:
        for combo, key, p in significant_interactions:
            lines.append(f"**{'×'.join(combo)} 交互显著** (F={effect_map[key]['F']:.3f}, p={p:.4f}{sig(p)})，停止解释主效应，执行简单效应分析。\n")
            lines.append(_simple_effects(df, list(combo), dv_col, factors))
        skip_main_effects = True
    else:
        # 检查边缘显著 (p<.10) 的交互
        marginal = []
        for combo, key in all_terms:
            if len(combo) < 2: continue
            if key in effect_map and effect_map[key]['p'] < 0.10:
                marginal.append((combo, key, effect_map[key]['p']))
        if marginal:
            for combo, key, p in marginal:
                lines.append(f"**{'×'.join(combo)} 交互边缘显著** (p={p:.4f}{sig(p)})，按探索性做简单效应分析，不解释主效应。\n")
                lines.append(_simple_effects(df, list(combo), dv_col, factors))
            skip_main_effects = True
        else:
            skip_main_effects = False

        # 主效应（仅在所有交互均不显著时报告）
        if not skip_main_effects:
            lines.append(f"\n### 主效应检验\n")
            for c in fcols:
                key = f'C({c})'
                if key not in effect_map: continue
                p = effect_map[key]['p']; F = effect_map[key]['F']; eta = effect_map[key]['eta_p']
                n_levels = df[c].nunique()
                label = factors[c].get('label', c)
                ll = factors[c].get('level_labels', [])
                if p < 0.05:
                    if n_levels == 2:
                        ms = df.groupby(c)[dv_col].mean()
                        levels = sorted(ms.index)
                        direction = '高于' if ms[levels[1]] > ms[levels[0]] else '低于'
                        l0 = ll[0] if len(ll)>0 else str(levels[0])
                        l1 = ll[1] if len(ll)>1 else str(levels[1])
                        lines.append(f"- **{label} 主效应显著**：F={F:.3f}, p={p:.4f}{sig(p)}, η²p={eta:.3f}；"
                                     f"{l1}(M={ms[levels[1]]:.3f}){direction}{l0}(M={ms[levels[0]]:.3f})")
                    else:
                        lines.append(f"- **{label} 主效应显著**：F={F:.3f}, p={p:.4f}{sig(p)}, η²p={eta:.3f}，{n_levels}个水平需做事后检验。")
                        lines.append(_posthoc(df, c, dv_col, factors))
                elif p < 0.10:
                    ms = df.groupby(c)[dv_col].mean()
                    levels = sorted(ms.index)
                    l0 = ll[0] if len(ll)>0 else str(levels[0])
                    l1 = ll[1] if len(ll)>1 else str(levels[1])
                    lines.append(f"- {label} 主效应边缘显著：F={F:.3f}, p={p:.4f}{sig(p)}, η²p={eta:.3f}；"
                                 f"{l0} M={ms[levels[0]]:.3f}, {l1} M={ms[levels[1]]:.3f}")
                else:
                    lines.append(f"- {label} 主效应不显著：F={F:.3f}, p={p:.4f}")

    # 描述统计
    lines.append(f"\n### 各单元均值与标准差\n")
    lines.append("| " + " | ".join(fcols) + " | M | SD | n |")
    lines.append("|" + "---|"*(len(fcols)+3))
    cell = df.groupby(fcols)[dv_col].agg(['mean','std','count']).round(3)
    for idx, row in cell.iterrows():
        if not isinstance(idx, tuple): idx = (idx,)
        lines.append("| " + " | ".join(str(x) for x in idx) + f" | {row['mean']:.3f} | {row['std']:.3f} | {int(row['count'])} |")

    return '\n'.join(lines)

def _simple_effects(df, interaction_factors, dv_col, factors):
    """对交互项做简单效应分析"""
    lines = []
    # 对交互中每个focal X，在其他factor的各水平组合下做检验
    for i, focal in enumerate(interaction_factors):
        others = [f for f in interaction_factors if f != focal]
        lines.append(f"\n**简单效应：{focal} 在 {'×'.join(others)} 各水平下**\n")
        lines.append("| 条件 | M组1 | M组2 | t | p | Cohen's d |")
        lines.append("|---|---|---|---|---|---|")
        # 其他变量的水平组合
        other_levels = []
        for o in others:
            other_levels.append(sorted(df[o].dropna().unique()))
        from itertools import product
        for combo in product(*other_levels):
            mask = pd.Series([True]*len(df))
            cond_labels = []
            for o, lv in zip(others, combo):
                mask &= (df[o] == lv)
                ll = factors[o].get('level_labels', [])
                lidx = sorted(df[o].dropna().unique()).index(lv)
                cond_labels.append(ll[lidx] if lidx < len(ll) else str(lv))
            sub = df[mask]
            levels = sorted(sub[focal].dropna().unique())
            if len(levels) != 2: continue
            g0 = sub[sub[focal]==levels[0]][dv_col].dropna()
            g1 = sub[sub[focal]==levels[1]][dv_col].dropna()
            if len(g0)<2 or len(g1)<2: continue
            res = pg.ttest(g0, g1)
            t = res.iloc[0]['T']; p = res.iloc[0]['p_val']; d = res.iloc[0]['cohen_d']
            lines.append(f"| {'+'.join(cond_labels)} | {g0.mean():.3f}(n={len(g0)}) | "
                         f"{g1.mean():.3f}(n={len(g1)}) | {t:.3f} | {p:.4f}{sig(p)} | {d:.3f} |")
    return '\n'.join(lines)

def _posthoc(df, factor, dv_col, factors):
    """事后检验（Tukey HSD）"""
    from statsmodels.stats.multicomp import pairwise_tukeyhsd
    lines = []
    tk = pairwise_tukeyhsd(df[dv_col], df[factor], alpha=0.05)
    lines.append("\n| 组1 | 组2 | 均值差 | p | 95%CI |")
    lines.append("|---|---|---|---|---|")
    for r in tk._results_table.data[1:]:
        lines.append(f"| {r[0]} | {r[1]} | {r[2]:.3f} | {r[3]:.4f} | [{r[5]:.3f}, {r[6]:.3f}] |")
    return '\n'.join(lines)

# ──────────────────────── 交互图 ────────────────────────

def plot_interactions(df, factors, dv_cols, out_path):
    """绘制交互作用图（最多3个factor：facet, x轴, 线条）"""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    for f in ['PingFang SC','Heiti SC','STHeiti','Arial Unicode MS','SimHei']:
        if any(f in fn.name for fn in font_manager.fontManager.ttflist):
            plt.rcParams['font.sans-serif'] = [f]; break
    plt.rcParams['axes.unicode_minus'] = False

    fcols = list(factors.keys())
    if len(fcols) == 2:
        fig, axes = plt.subplots(1, len(dv_cols), figsize=(6*len(dv_cols), 5))
        if len(dv_cols)==1: axes=[axes]
        for ax, (dv_col, dv_name) in zip(axes, dv_cols):
            _plot_2way(ax, df, fcols[0], fcols[1], dv_col, dv_name, factors)
    elif len(fcols) >= 3:
        fig, axes = plt.subplots(len(dv_cols), 2, figsize=(12, 5*len(dv_cols)))
        if len(dv_cols)==1: axes = axes.reshape(1,-1)
        for row, (dv_col, dv_name) in enumerate(dv_cols):
            for col, f3v in enumerate(sorted(df[fcols[2]].unique())):
                ax = axes[row, col]
                sub = df[df[fcols[2]]==f3v]
                ll = factors[fcols[2]].get('level_labels',[])
                lidx = sorted(df[fcols[2]].unique()).index(f3v)
                title = f'{dv_name} — {ll[lidx] if lidx<len(ll) else f3v}'
                _plot_2way(ax, sub, fcols[0], fcols[1], dv_col, title, factors)
    else:
        return
    plt.tight_layout()
    plt.savefig(out_path, dpi=200, bbox_inches='tight')
    plt.close()
    return out_path

def _plot_2way(ax, df, x_col, group_col, dv_col, title, factors):
    colors = ['#4472C4','#ED7D31','#A5A5A5','#FFC000','#5B9BD5']
    x_levels = sorted(df[x_col].dropna().unique())
    g_levels = sorted(df[group_col].dropna().unique())
    x_labels = factors[x_col].get('level_labels', [str(x) for x in x_levels])
    g_labels = factors[group_col].get('level_labels', [str(g) for g in g_levels])
    for i, gv in enumerate(g_levels):
        sub = df[df[group_col]==gv]
        means = [sub[sub[x_col]==xv][dv_col].mean() for xv in x_levels]
        sems = [sub[sub[x_col]==xv][dv_col].sem() for xv in x_levels]
        gl = g_labels[i] if i < len(g_labels) else str(gv)
        ax.errorbar(range(len(x_levels)), means, yerr=[1.96*s for s in sems],
                   fmt='o-', color=colors[i%len(colors)], capsize=5, linewidth=2, markersize=8, label=gl)
    ax.set_xticks(range(len(x_levels)))
    ax.set_xticklabels([x_labels[i] if i<len(x_labels) else str(xv) for i,xv in enumerate(x_levels)], fontsize=11)
    ax.set_title(title, fontsize=13, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(axis='y', alpha=0.3)

# ──────────────────────── 中介分析 (PROCESS) ────────────────────────

def mediated_moderation(df, X, W, Z, M_col, Y_cols, Y_names, n_boot=5000, seed=42, section_num=6):
    """
    PROCESS Model 12 (有W和Z时) / Model 8 (只有W时) / Model 4 (无W,Z时)
    X→M→Y, W/Z调节a路径和c'路径
    三层递进: ①交互项 ②Index of Moderated Mediation ③条件间接效应
    """
    np.random.seed(seed)
    lines = []
    d = df.copy()

    # 构建交互项
    terms = [X]
    if W:
        d[f'{X}_x_{W}'] = d[X]*d[W]; terms.append(f'{X}_x_{W}')
    if Z:
        d[f'{X}_x_{Z}'] = d[X]*d[Z]; terms.append(f'{X}_x_{Z}')
    if W and Z:
        d[f'{W}_x_{Z}'] = d[W]*d[Z]; terms.append(f'{W}_x_{Z}')
        d[f'{X}_x_{W}_x_{Z}'] = d[X]*d[W]*d[Z]; terms.append(f'{X}_x_{W}_x_{Z}')

    cn = ['一','二','三','四','五','六','七','八','九','十']
    sec = cn[section_num-1] if section_num <= len(cn) else str(section_num)
    model_name = 'Model 4 (简单中介)' if not W else ('Model 8' if not Z else 'Model 12')
    lines.append(f"\n## {sec}、被调节的中介分析（PROCESS {model_name}）\n")
    lines.append(f"X={X}, W={W or '—'}, Z={Z or '—'}, M={M_col}, Bootstrap={n_boot}\n")

    # a路径模型（标准PROCESS顺序: X, W, Z, X×W, X×Z, W×Z, X×W×Z）
    a_preds = [X]
    if W: a_preds += [W]
    if Z: a_preds += [Z]
    if W: a_preds += [f'{X}_x_{W}']
    if Z: a_preds += [f'{X}_x_{Z}']
    if W and Z: a_preds += [f'{W}_x_{Z}', f'{X}_x_{W}_x_{Z}']

    Xa = sm.add_constant(d[a_preds])
    model_a = sm.OLS(d[M_col], Xa).fit()

    lines.append(f"### Outcome: {M_col}（a路径）")
    lines.append(f"R²={model_a.rsquared:.4f}, F({int(model_a.df_model)},{int(model_a.df_resid)})={model_a.fvalue:.3f}, p={model_a.f_pvalue:.4f}\n")
    lines.append("| 系数 | 项 | B | SE | t | p |")
    lines.append("|---|---|---|---|---|---|")
    a_labels = {'const':'常数'}
    for i, t in enumerate(a_preds):
        a_labels[t] = f'a{i+1}: {t.replace("_x_","×")}'
    for t in ['const']+a_preds:
        B=model_a.params[t]; se=model_a.bse[t]; p=model_a.pvalues[t]
        lines.append(f"| {a_labels[t]} | {t} | {B:.4f} | {se:.4f} | {B/se:.3f} | {p:.4f}{sig(p)} |")

    # 对每个Y
    for y_col, y_name in zip(Y_cols, Y_names):
        lines.append(f"\n### Outcome: {y_name}\n")
        c_preds = a_preds + [M_col]
        Xc = sm.add_constant(d[c_preds])
        model_c = sm.OLS(d[y_col], Xc).fit()
        # c'路径标签
        c_labels = {'const':'常数'}
        ci = 1
        for t in a_preds:
            if '_x_' not in t:
                c_labels[t] = f"c'{ci}: {t}"; ci += 1
            else:
                c_labels[t] = f"c'int: {t.replace('_x_','×')}"
        lines.append(f"R²={model_c.rsquared:.4f}, F({int(model_c.df_model)},{int(model_c.df_resid)})={model_c.fvalue:.3f}, p={model_c.f_pvalue:.6f}\n")
        lines.append("| 系数 | 项 | B | SE | t | p |")
        lines.append("|---|---|---|---|---|---|")
        for t in ['const']+c_preds:
            B=model_c.params[t]; se=model_c.bse[t]; p=model_c.pvalues[t]
            label = f'b: {M_col}→Y' if t==M_col else c_labels.get(t, t)
            lines.append(f"| {label} | {t} | {B:.4f} | {se:.4f} | {B/se:.3f} | {p:.4f}{sig(p)} |")

        # Bootstrap
        n = len(d)
        boot_a = np.zeros((n_boot, len(a_preds)+1))
        boot_c = np.zeros((n_boot, len(c_preds)+1))
        for i in range(n_boot):
            idx = np.random.choice(n, n, replace=True)
            dd = d.iloc[idx]
            try:
                boot_a[i] = sm.OLS(dd[M_col], sm.add_constant(dd[a_preds])).fit().params.values
                boot_c[i] = sm.OLS(dd[y_col], sm.add_constant(dd[c_preds])).fit().params.values
            except:
                boot_a[i]=np.nan; boot_c[i]=np.nan
        a_idx = {t:i for i,t in enumerate(['const']+a_preds)}
        c_idx = {t:i for i,t in enumerate(['const']+c_preds)}
        b_boot = boot_c[:, c_idx[M_col]]
        b_point = model_c.params[M_col]

        # Step 1: 交互项
        if W or Z:
            lines.append(f"\n#### Step 1: a路径交互项检验\n")
            int_terms = [t for t in a_preds if '_x_' in t]
            for t in int_terms:
                p = model_a.pvalues[t]; B = model_a.params[t]
                flag = '✅ 显著' if p<.05 else ('⚠️ 边缘显著' if p<.10 else '❌ 不显著')
                lines.append(f"- {t.replace('_x_','×')}: B={B:.4f}, p={p:.4f}{sig(p)} {flag}")

            # Step 2: Index of Moderated Mediation
            lines.append(f"\n#### Step 2: Index of Moderated Mediation\n")
            lines.append("| 指数 | Index | Boot SE | 95% CI | 结论 |")
            lines.append("|---|---|---|---|---|")
            for t in int_terms:
                idx_point = model_a.params[t] * b_point
                idx_boot = boot_a[:, a_idx[t]] * b_boot
                lo, hi = np.nanpercentile(idx_boot, [2.5, 97.5])
                se_v = np.nanstd(idx_boot)
                is_sig = (lo>0) or (hi<0)
                lines.append(f"| Index_{t.replace('_x_','×')} | {idx_point:.4f} | {se_v:.4f} | [{lo:.4f}, {hi:.4f}] | {'✅ 成立' if is_sig else '❌ 不成立'} |")

        # Step 3: 条件间接效应
        lines.append(f"\n#### Step 3: 条件间接效应（{X}→{M_col}→{y_name}）\n")
        if not W and not Z:
            # Model 4: 简单间接效应
            ab = model_a.params[X] * b_point
            ab_boot = boot_a[:, a_idx[X]] * b_boot
            lo, hi = np.nanpercentile(ab_boot, [2.5, 97.5])
            lines.append(f"间接效应 a×b = {ab:.4f}, Boot SE = {np.nanstd(ab_boot):.4f}, 95% CI = [{lo:.4f}, {hi:.4f}] {'✅ 显著' if (lo>0 or hi<0) else '❌ 不显著'}")
        else:
            # 构建条件
            a1 = model_a.params[X]
            a1_b = boot_a[:, a_idx[X]]
            w_vals = [0,1] if W else [None]
            z_vals = [0,1] if Z else [None]
            # 条件a = a1 + a_xw*W + a_xz*Z + a_xwz*W*Z
            cond_header = []
            if W: cond_header.append(f'W={W}')
            if Z: cond_header.append(f'Z={Z}')
            lines.append("| " + " | ".join(cond_header) + " | 条件a | 间接效应a×b | Boot SE | 95% CI | 显著 |")
            lines.append("|" + "---|"*(len(cond_header)+5))
            for wv in w_vals:
                for zv in z_vals:
                    cond_a = a1
                    cond_a_b = a1_b
                    cond_label = []
                    if W:
                        cond_label.append(str(wv))
                        aw = model_a.params[f'{X}_x_{W}']; aw_b = boot_a[:, a_idx[f'{X}_x_{W}']]
                        cond_a += aw*wv; cond_a_b += aw_b*wv
                    if Z:
                        cond_label.append(str(zv))
                        az = model_a.params[f'{X}_x_{Z}']; az_b = boot_a[:, a_idx[f'{X}_x_{Z}']]
                        cond_a += az*zv; cond_a_b += az_b*zv
                    if W and Z:
                        awz = model_a.params[f'{X}_x_{W}_x_{Z}']; awz_b = boot_a[:, a_idx[f'{X}_x_{W}_x_{Z}']]
                        cond_a += awz*wv*zv; cond_a_b += awz_b*wv*zv
                    ab = cond_a * b_point
                    ab_boot = cond_a_b * b_boot
                    lo, hi = np.nanpercentile(ab_boot, [2.5, 97.5])
                    se_v = np.nanstd(ab_boot)
                    is_sig = (lo>0) or (hi<0)
                    lines.append("| " + " | ".join(cond_label) + f" | {cond_a:.4f} | {ab:.4f} | {se_v:.4f} | [{lo:.4f}, {hi:.4f}] | {'✅' if is_sig else ''} |")

    return '\n'.join(lines)

# ──────────────────────── ICC（嵌套设计） ────────────────────────

def compute_icc(data_file, group_col, dv_col, source_col_map=None):
    """
    计算空模型ICC（组内相关系数），用于嵌套设计（类型2）。
    ICC = σ²_between / (σ²_between + σ²_within)
    ICC > .05 → 必须使用多层模型；ICC ≤ .05 → 可考虑普通ANOVA但仍建议报告ICC。

    参数:
      data_file: .sav或.csv路径
      group_col: 分组/嵌套变量列名（如班级ID）
      dv_col: 因变量列名
      source_col_map: 可选，列名映射（用于中文列名重命名）
    """
    df, _ = load_data(data_file)
    if source_col_map:
        for new, src in source_col_map.items():
            if src in df.columns and new != src:
                df[new] = df[src]

    if group_col not in df.columns:
        raise ConfigError(f"分组变量 '{group_col}' 不在数据中。可用列: {list(df.columns)[:20]}...")
    if dv_col not in df.columns:
        raise ConfigError(f"因变量 '{dv_col}' 不在数据中。可用列: {list(df.columns)[:20]}...")

    sub = df[[group_col, dv_col]].dropna()
    n_groups = sub[group_col].nunique()
    n_total = len(sub)

    # 空模型
    from statsmodels.regression.mixed_linear_model import MixedLM
    model = MixedLM.from_formula(f'{dv_col} ~ 1', groups=group_col, data=sub)
    result = model.fit(method='lbfgs')

    var_between = float(result.cov_re.iloc[0, 0])
    var_within = float(result.scale)
    icc = var_between / (var_between + var_within)

    # 各组样本量
    group_sizes = sub.groupby(group_col).size()

    print(f"\n{'='*60}")
    print(f"ICC 计算结果（空模型 / Null Model）")
    print(f"{'='*60}")
    print(f"因变量: {dv_col}")
    print(f"分组变量: {group_col}")
    print(f"总样本量: N = {n_total}")
    print(f"组数: {n_groups}")
    print(f"平均组大小: {group_sizes.mean():.1f} (最小{group_sizes.min()}, 最大{group_sizes.max()})")
    print(f"组间方差 (τ₀₀): {var_between:.4f}")
    print(f"组内方差 (σ²):  {var_within:.4f}")
    print(f"ICC = {var_between:.4f} / ({var_between:.4f} + {var_within:.4f}) = {icc:.4f}")
    print(f"{'='*60}")
    if icc > 0.05:
        print(f"⚠️ ICC = {icc:.3f} > .05，数据存在嵌套依赖性！")
        print(f"   禁止使用普通OLS/ANOVA，必须使用多层模型(HLM/LMM)。")
        print(f"   建议: MixedLM.from_formula('{dv_col} ~ IV', groups='{group_col}', data=df)")
    elif icc > 0.01:
        print(f"⚠️ ICC = {icc:.3f}，较小但非零，建议仍使用多层模型并报告ICC。")
    else:
        print(f"✅ ICC = {icc:.3f} ≤ .05，嵌套依赖性可忽略，普通ANOVA可接受（仍建议报告ICC）。")
    print(f"{'='*60}\n")
    return icc


# ──────────────── 重复测量 / 混合ANOVA（类型4/5）────────────────

def repeated_measures_anova(data_file, subject_col, within_col, dv_col, within_labels=None):
    """
    类型4：基础被试内设计 — 重复测量ANOVA。
    数据必须为长格式：每被试每条件一行。
    命门：Mauchly球形检验；违背时报告Greenhouse-Geisser校正。
    """
    df, _ = load_data(data_file)
    for col, name in [(subject_col,'被试ID'), (within_col,'被试内变量'), (dv_col,'因变量')]:
        if col not in df.columns:
            raise ConfigError(f"{name}列 '{col}' 不在数据中。可用列: {list(df.columns)[:20]}...")

    sub = df[[subject_col, within_col, dv_col]].dropna()
    n_subjects = sub[subject_col].nunique()
    levels = sorted(sub[within_col].unique())

    print(f"\n{'='*60}")
    print(f"重复测量ANOVA（被试内设计）")
    print(f"{'='*60}")
    print(f"因变量: {dv_col}")
    print(f"被试内变量: {within_col}（{len(levels)}个水平: {levels}）")
    print(f"被试数: N = {n_subjects}")

    # 重复测量ANOVA
    aov = pg.rm_anova(data=sub, dv=dv_col, within=within_col, subject=subject_col, detailed=True)
    print(f"\n--- ANOVA结果 ---")
    print(aov.to_string(index=False))

    # 球形检验和GG校正
    row = aov.iloc[0]
    pcol = 'p-unc' if 'p-unc' in aov.columns else 'p_unc'
    spher = row.get('sphericity', None)
    W_spher = row.get('W', None)
    p_spher = row.get('p-spher', row.get('p_spher', None))
    eps_gg = row.get('eps', None)
    p_gg = row.get('p-GG-corr', row.get('p_GG_corr', row.get(pcol)))
    F = row['F']; p_unc = row[pcol]; ng2 = row.get('ng2', row.get('np2', None))

    print(f"\n--- 命门审查 ---")
    df1 = row['DF']
    df2 = aov[aov['Source']=='Error'].iloc[0]['DF'] if 'Error' in aov['Source'].values else ''
    if p_spher is not None and str(spher).lower() != 'true':
        print(f"⚠️ Mauchly球形检验: W={W_spher:.3f}, p={p_spher:.4f}，球形假设违背！")
        print(f"   Greenhouse-Geisser ε = {eps_gg:.3f}")
        print(f"   校正后: F({df1:.0f}, {df2:.0f}) = {F:.3f}, p = {p_gg:.4f}{sig(p_gg)}")
        if p_gg < 0.05:
            print(f"   ✅ GG校正后仍显著")
        else:
            print(f"   ❌ GG校正后不显著")
    else:
        print(f"✅ 球形假设成立（p={p_spher:.4f}）" if p_spher is not None and str(spher).lower() != 'true' else "✅ 球形假设成立（2水平无需检验）")
        print(f"   F({df1:.0f}, {df2:.0f}) = {F:.3f}, p = {p_unc:.4f}{sig(p_unc)}")

    # 事后检验
    if len(levels) > 2 and p_unc < 0.05:
        print(f"\n--- 事后检验（配对t检验 + Bonferroni校正）---")
        pt = pg.pairwise_tests(data=sub, dv=dv_col, within=within_col, subject=subject_col, padjust='bonf')
        pcol = 'p_corr' if 'p_corr' in pt.columns else ('p-corr' if 'p-corr' in pt.columns else 'p_unc')
        for _, r in pt.iterrows():
            print(f"  {r['A']} vs {r['B']}: t={r['T']:.3f}, p={r[pcol]:.4f}{sig(r[pcol])}, d={r['hedges']:.3f}")

    # 描述统计
    print(f"\n--- 各条件均值 ---")
    ms = sub.groupby(within_col)[dv_col].agg(['mean','std','count'])
    for lv, r in ms.iterrows():
        print(f"  {lv}: M={r['mean']:.3f}, SD={r['std']:.3f}, n={int(r['count'])}")
    print(f"{'='*60}\n")


def mixed_anova(data_file, subject_col, within_col, between_col, dv_col):
    """
    类型5：基础混合设计 — 混合ANOVA（组间×被试内）。
    数据必须为长格式。
    命门：组间×时间交互效应是证明干预有效的唯一核心指标。
    """
    df, _ = load_data(data_file)
    for col, name in [(subject_col,'被试ID'), (within_col,'被试内变量'),
                       (between_col,'组间变量'), (dv_col,'因变量')]:
        if col not in df.columns:
            raise ConfigError(f"{name}列 '{col}' 不在数据中。可用列: {list(df.columns)[:20]}...")

    sub = df[[subject_col, within_col, between_col, dv_col]].dropna()
    n_subjects = sub[subject_col].nunique()
    b_levels = sorted(sub[between_col].unique())
    w_levels = sorted(sub[within_col].unique())

    print(f"\n{'='*60}")
    print(f"混合ANOVA（组间×被试内设计）")
    print(f"{'='*60}")
    print(f"因变量: {dv_col}")
    print(f"组间变量: {between_col}（{b_levels}）")
    print(f"被试内变量: {within_col}（{w_levels}）")
    print(f"被试数: N = {n_subjects}")

    aov = pg.mixed_anova(data=sub, dv=dv_col, within=within_col, between=between_col,
                         subject=subject_col)
    # pingouin列名兼容：p-unc 或 p_unc
    p_col = 'p-unc' if 'p-unc' in aov.columns else 'p_unc'
    np2_col = 'np2' if 'np2' in aov.columns else 'ng2'
    print(f"\n--- ANOVA结果 ---")
    print(aov.to_string(index=False))

    # 找交互效应行
    interaction_row = aov[aov['Source'].str.contains('Interaction|×|\\*', case=False, regex=True)]
    if len(interaction_row) == 0:
        interaction_row = aov.iloc[2]
    else:
        interaction_row = interaction_row.iloc[0]

    F_int = interaction_row['F']; p_int = interaction_row[p_col]
    np2_int = interaction_row.get(np2_col, None)

    print(f"\n--- 命门审查：组间×被试内交互效应 ---")
    print(f"交互效应: F = {F_int:.3f}, p = {p_int:.4f}{sig(p_int)}"
          + (f", η²p = {np2_int:.3f}" if np2_int is not None else ""))

    if p_int < 0.05:
        print(f"✅ 交互效应显著！这是证明干预有效的核心证据。")
        print(f"   必须做简单效应分析：")
        # 简单效应：在各组内检验被试内效应
        for bl in b_levels:
            sub_b = sub[sub[between_col]==bl]
            pt = pg.pairwise_tests(data=sub_b, dv=dv_col, within=within_col,
                                    subject=subject_col, padjust='bonf')
            pcol = 'p_corr' if 'p_corr' in pt.columns else ('p-corr' if 'p-corr' in pt.columns else 'p_unc')
            for _, r in pt.iterrows():
                print(f"   在{between_col}={bl}时, {within_col} {r['A']}vs{r['B']}: "
                      f"t={r['T']:.3f}, p={r[pcol]:.4f}{sig(r[pcol])}, d={r['hedges']:.3f}")
        # 在各时间点检验组间差异
        for wl in w_levels:
            sub_w = sub[sub[within_col]==wl]
            groups = [sub_w[sub_w[between_col]==bl][dv_col].dropna() for bl in b_levels]
            if len(groups) == 2:
                res = pg.ttest(groups[0], groups[1])
                print(f"   在{within_col}={wl}时, {between_col}组间: "
                      f"t={res.iloc[0]['T']:.3f}, p={res.iloc[0]['p_val']:.4f}{sig(res.iloc[0]['p_val'])}, "
                      f"d={res.iloc[0]['cohen_d']:.3f}")
    else:
        print(f"❌ 交互效应不显著！不能做出干预有效的因果结论。")
        print(f"   即使被试内主效应显著，也可能是成熟/练习/重测效应。")
        # 检查主效应
        for _, r in aov.iterrows():
            if r['Source'] != interaction_row['Source']:
                print(f"   {r['Source']}主效应: F={r['F']:.3f}, p={r[p_col]:.4f}{sig(r[p_col])}")

    # 描述统计
    print(f"\n--- 各单元格均值 ---")
    cell = sub.groupby([between_col, within_col])[dv_col].agg(['mean','std','count'])
    for (bl, wl), r in cell.iterrows():
        print(f"  {between_col}={bl}, {within_col}={wl}: M={r['mean']:.3f}, SD={r['std']:.3f}, n={int(r['count'])}")
    print(f"{'='*60}\n")


# ──────────────────────── 主流程 ────────────────────────

def run_analysis(config):
    """执行完整分析流程"""
    out_dir = config.get('output_dir', '.')
    os.makedirs(out_dir, exist_ok=True)
    report_lines = []

    # 1. 加载数据
    df, meta = load_data(config['data_file'])
    print(f"  数据加载成功: N={len(df)}, 变量数={len(df.columns)}")
    report_lines.append(f"# 实验数据分析报告\n")
    report_lines.append(f"数据文件：{config['data_file']}，N = {len(df)}\n")

    # 2. 编码自变量
    factors = config['factors']
    df = encode_factors(df, factors)

    # 3. 构建量表
    scales = config.get('scales', {})
    if scales:
        df, rel = build_scales(df, scales)
        report_lines.append(report_reliability(rel))

    # 4. 操纵检验
    checks = config.get('manipulation_checks', [])
    if checks:
        report_lines.append(manipulation_check(df, factors, checks))

    # 5. ANOVA
    dvs = config.get('dvs', {})
    sec = 3
    for dv_col, dv_name in dvs.items():
        if dv_col in df.columns:
            report_lines.append(factorial_anova(df, factors, dv_col, dv_name, section_num=sec))
            sec += 1

    # 6. 交互图
    dv_list = [(c, n) for c,n in dvs.items() if c in df.columns]
    if len(factors) >= 2 and dv_list:
        plot_path = os.path.join(out_dir, 'interaction_plot.png')
        try:
            plot_interactions(df, factors, dv_list, plot_path)
            report_lines.append(f"\n## 交互作用图\n\n![交互作用图](interaction_plot.png)\n")
            print(f"  交互图已保存: {plot_path}")
        except Exception as e:
            report_lines.append(f"\n（交互图生成失败：{e}）\n")
            print(f"  ⚠️ 交互图生成失败: {e}")

    # 7. 中介分析
    med = config.get('mediation', {})
    if med and med.get('M') and med.get('X'):
        Y_cols = med.get('Y_cols', [])
        Y_names = med.get('Y_names', Y_cols)
        Y_cols = [y for y in Y_cols if y in df.columns]
        if Y_cols:
            med_section = 3 + len(dv_list)
            print(f"  开始Bootstrap中介分析 (n_boot={med.get('n_boot', 5000)})，可能需要数分钟...")
            report_lines.append(mediated_moderation(
                df, med['X'], med.get('W'), med.get('Z'),
                med['M'], Y_cols, Y_names,
                n_boot=med.get('n_boot', 5000),
                seed=med.get('seed', 42),
                section_num=med_section
            ))

    # 输出报告
    report_path = os.path.join(out_dir, 'analysis_report.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
    print(f"✅ 报告已保存: {report_path}")
    return report_path


def main():
    parser = argparse.ArgumentParser(
        description='实验数据分析工具：设计类型诊断→组间ANOVA/嵌套ICC/操纵检验/被调节的中介(PROCESS)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python exp_analysis.py config.json                        # 完整分析（类型1组间设计）
  python exp_analysis.py config.json --check-only           # 仅校验配置
  python exp_analysis.py --icc data.sav --group class --dv Y  # ICC（类型2嵌套）
  python exp_analysis.py --rm-anova data.csv --subject id --within time --dv Y  # 重复测量（类型4）
  python exp_analysis.py --mixed-anova data.csv --subject id --within time --between group --dv Y  # 混合（类型5）

配置文件格式见 config_example.json。
退出码: 0=成功, 1=配置错误, 2=数据格式错误, 3=统计执行错误
        """)
    parser.add_argument('config', nargs='?', help='JSON配置文件路径')
    parser.add_argument('--check-only', action='store_true',
                        help='仅校验配置文件和数据，不执行分析')
    parser.add_argument('--icc', metavar='DATA_FILE',
                        help='计算ICC（嵌套设计类型2）：指定数据文件.sav/.csv')
    parser.add_argument('--group', metavar='COL',
                        help='ICC模式：分组/嵌套变量列名（如班级ID）')
    parser.add_argument('--dv', metavar='COL',
                        help='ICC/重复测量模式：因变量列名')
    parser.add_argument('--rm-anova', metavar='DATA_FILE',
                        help='重复测量ANOVA（类型4被试内设计）：指定长格式数据文件')
    parser.add_argument('--mixed-anova', metavar='DATA_FILE',
                        help='混合ANOVA（类型5混合设计）：指定长格式数据文件')
    parser.add_argument('--subject', metavar='COL',
                        help='重复测量/混合ANOVA：被试ID列名')
    parser.add_argument('--within', metavar='COL',
                        help='重复测量/混合ANOVA：被试内变量列名')
    parser.add_argument('--between', metavar='COL',
                        help='混合ANOVA：组间变量列名')
    args = parser.parse_args()

    # ICC模式
    if args.icc:
        if not args.group or not args.dv:
            print("❌ ICC模式需要 --group 和 --dv 参数")
            print("   示例: python exp_analysis.py --icc data.sav --group class_id --dv Y")
            sys.exit(EXIT_CONFIG_ERROR)
        try:
            compute_icc(args.icc, args.group, args.dv)
        except ConfigError as e:
            print(f"❌ {e}")
            sys.exit(EXIT_CONFIG_ERROR)
        except Exception as e:
            print(f"❌ ICC计算错误: {e}")
            sys.exit(EXIT_STATS_ERROR)
        sys.exit(EXIT_OK)

    # 重复测量ANOVA模式（类型4）
    if args.rm_anova:
        if not args.subject or not args.within or not args.dv:
            print("❌ 重复测量ANOVA需要 --subject, --within, --dv 参数")
            print("   示例: python exp_analysis.py --rm-anova data.csv --subject id --within time --dv Y")
            sys.exit(EXIT_CONFIG_ERROR)
        try:
            repeated_measures_anova(args.rm_anova, args.subject, args.within, args.dv)
        except ConfigError as e:
            print(f"❌ {e}")
            sys.exit(EXIT_CONFIG_ERROR)
        except Exception as e:
            print(f"❌ 重复测量ANOVA错误: {e}")
            import traceback; traceback.print_exc()
            sys.exit(EXIT_STATS_ERROR)
        sys.exit(EXIT_OK)

    # 混合ANOVA模式（类型5）
    if args.mixed_anova:
        if not args.subject or not args.within or not args.between or not args.dv:
            print("❌ 混合ANOVA需要 --subject, --within, --between, --dv 参数")
            print("   示例: python exp_analysis.py --mixed-anova data.csv --subject id --within time --between group --dv Y")
            sys.exit(EXIT_CONFIG_ERROR)
        try:
            mixed_anova(args.mixed_anova, args.subject, args.within, args.between, args.dv)
        except ConfigError as e:
            print(f"❌ {e}")
            sys.exit(EXIT_CONFIG_ERROR)
        except Exception as e:
            print(f"❌ 混合ANOVA错误: {e}")
            import traceback; traceback.print_exc()
            sys.exit(EXIT_STATS_ERROR)
        sys.exit(EXIT_OK)

    # 完整分析模式
    if not args.config:
        parser.print_help()
        sys.exit(EXIT_CONFIG_ERROR)

    # 读取配置
    if not os.path.isfile(args.config):
        print(f"❌ 配置文件不存在: {args.config}")
        sys.exit(EXIT_CONFIG_ERROR)

    try:
        with open(args.config, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ 配置文件JSON格式错误: {e}")
        sys.exit(EXIT_CONFIG_ERROR)

    # 校验配置
    errors = validate_config(config)
    if errors:
        print("❌ 配置校验失败:")
        for e in errors:
            print(f"   - {e}")
        sys.exit(EXIT_CONFIG_ERROR)

    # 加载数据并校验列
    try:
        df, _ = load_data(config['data_file'])
    except ConfigError as e:
        print(f"❌ {e}")
        sys.exit(EXIT_DATA_FORMAT)
    except Exception as e:
        print(f"❌ 数据加载失败: {e}")
        sys.exit(EXIT_DATA_FORMAT)

    # 编码factors并构建scales后再校验列（量表名在build_scales后才存在）
    df_check = df.copy()
    for fname, finfo in config['factors'].items():
        src = finfo.get('source_col', fname)
        if src in df_check.columns and src != fname:
            df_check[fname] = df_check[src]
        elif 'levels' in finfo:
            # apply mapping for validation
            mapping = {}
            for k, v in finfo['levels'].items():
                try: mapping[float(k)] = v
                except: mapping[k] = v
            df_check[fname] = df_check[fname].map(mapping) if fname in df_check.columns else None

    # build scales for column validation
    scales = config.get('scales', {})
    for sname, items in scales.items():
        available = [c for c in items if c in df_check.columns]
        if available:
            df_check[sname] = df_check[available].mean(axis=1)

    col_errors = validate_columns(df_check, config)
    if col_errors:
        print("❌ 变量校验失败:")
        for e in col_errors:
            print(f"   - {e}")
        print(f"\n   数据中的列名: {list(df.columns)}")
        sys.exit(EXIT_CONFIG_ERROR)

    print(f"✅ 配置校验通过（{len(config['factors'])}个自变量, {len(df)}条记录）")

    if args.check_only:
        print("仅校验模式，不执行分析。")
        sys.exit(EXIT_OK)

    # 执行分析
    try:
        run_analysis(config)
    except ConfigError as e:
        print(f"❌ {e}")
        sys.exit(EXIT_CONFIG_ERROR)
    except Exception as e:
        print(f"❌ 分析执行错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(EXIT_STATS_ERROR)

    sys.exit(EXIT_OK)


if __name__ == '__main__':
    main()
