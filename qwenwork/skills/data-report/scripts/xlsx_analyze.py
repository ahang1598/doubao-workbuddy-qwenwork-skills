#!/usr/bin/env python3
"""Automated data analysis engine for Excel / CSV files.

对数据自动执行 8 类分析，输出**纯事实型** findings JSON（无业务建议层）。
模型从 raw_stats 和 findings 中自己筛选、组织后写报告，而非脚本推荐。

Usage:
    python scripts/xlsx_analyze.py data.xlsx
    python scripts/xlsx_analyze.py data.xlsx --sheet "Sheet1"
    python scripts/xlsx_analyze.py data.xlsx --output findings.json
    python scripts/xlsx_analyze.py data.csv --encoding gbk
    python scripts/xlsx_analyze.py data.xlsx --profile-only  # 只数据画像不全分析

Output (JSON):
    {
      "ok": true,
      "file": "data.xlsx",
      "sheets_analyzed": N,
      "profile": [ ... ],          // 每 sheet 的列分类（dim/measure/date/unclassified）
                                    //   行列数、缺失率、数据质量 flag
      "raw_stats": [ ... ],        // 每列原始统计量 sum/mean/median/count/nunique/
                                    //   max/min/std/p25/p75/p90/p99 —— 纯数字事实
      "findings": [ ... ],         // 分析发现，每条含 type/sheet/column/data/text 字段
                                    //   按 priority 排序；**不含 chart_suggestion 或推荐层**
      "analysis_types": [ ... ],   // 出现的 finding 类型列表（参考）
      "data_traps": [ ... ],       // 由 xlsx_reader.py inspect 子调用并入
      "skipped": [ ... ],          // 跳过的 sheet/analyzer + 原因
      "human_summary": "..."
    }

Lean 哲学：本脚本是**事实摘录器**，不做以下事：
  ❌ KPI 推荐  ❌ 图表选型  ❌ 洞察叙事  ❌ 业务行动建议
  这些由模型基于 findings 自主判断。analyzer 函数内部历史上构造过 chart_suggestion 字段，
  但已在主流程 strip 掉（见 analyze() 函数 finding 后处理段，搜 'chart_suggestion'）。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except AttributeError:
    pass

_CSV_ENCODINGS = ['utf-8-sig', 'utf-8', 'gbk', 'gb18030']

# 大文件阈值：超过则默认 fail-fast，引导模型走 chunked pandas
# 200 MB 经验值：对应约 2-5M 行的中等宽度 CSV；常规笔记本读完 < 30s
# 显式 --head / --sample 可绕过；--profile-only 不受限（用 nrows 兜底）
DEFAULT_MAX_SIZE_MB = 200


def _read_data(filepath, sheet=None, encoding=None, head=None, sample=None):
    """Read file into DataFrame(s). Returns list of (sheet_name, df).

    Args:
      head: 若指定，只读前 N 行（pandas nrows）；适合超大文件快速分析
      sample: 若指定，等概率抽样 N 行；用于无偏统计估计（仅对 csv/tsv 有效）
    """
    import pandas as pd
    p = Path(filepath)
    ext = p.suffix.lower()

    if ext in ('.xlsx', '.xlsm'):
        read_kwargs = {}
        if head is not None:
            read_kwargs['nrows'] = head
        if sheet:
            df = pd.read_excel(filepath, sheet_name=sheet, **read_kwargs)
            return [(sheet, df)]
        else:
            all_sheets = pd.read_excel(filepath, sheet_name=None, **read_kwargs)
            return [(name, df) for name, df in all_sheets.items()
                    if not df.empty and df.shape[0] > 0]

    if ext in ('.csv', '.tsv'):
        sep = '\t' if ext == '.tsv' else ','
        encodings = [encoding] if encoding else _CSV_ENCODINGS
        for enc in encodings:
            try:
                if head is not None:
                    df = pd.read_csv(filepath, sep=sep, encoding=enc, nrows=head)
                elif sample is not None:
                    # Sample via skiprows: 先数总行，再随机 skip
                    # 适合中等大文件（< 1G）；超大文件应在 step 2 用 chunked
                    import random as _rnd
                    with open(filepath, 'rb') as f:
                        total = sum(1 for _ in f) - 1  # 减表头
                    if total <= sample:
                        df = pd.read_csv(filepath, sep=sep, encoding=enc)
                    else:
                        skip_idx = sorted(_rnd.Random(42).sample(
                            range(1, total + 1), total - sample))
                        df = pd.read_csv(filepath, sep=sep, encoding=enc,
                                         skiprows=skip_idx)
                else:
                    df = pd.read_csv(filepath, sep=sep, encoding=enc)
                return [(p.stem, df)]
            except (UnicodeDecodeError, UnicodeError):
                continue
        raise ValueError('CSV 编码检测失败')

    raise ValueError(f'不支持的格式: {ext}')


def _check_size_limit(filepath, max_size_mb):
    """Pre-flight size check. Returns (ok, size_mb).

    超过阈值则建议显式 --head N / --sample N / --profile-only，
    避免单次 read_excel 把 30M-50M 行直接拉内存。
    """
    try:
        size_mb = Path(filepath).stat().st_size / (1024 * 1024)
    except OSError:
        return True, 0.0
    return size_mb <= max_size_mb, size_mb


def _safe(v):
    """Convert to JSON-safe value."""
    import numpy as np
    if v is None or (isinstance(v, float) and (np.isnan(v) or np.isinf(v))):
        return None
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return round(float(v), 4)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if hasattr(v, 'isoformat'):
        return v.isoformat()
    return v


def _fmt_num(n):
    """Format number for display."""
    if n is None:
        return '-'
    abs_n = abs(n)
    if abs_n >= 1e8:
        return f'{n/1e8:.2f}亿'
    if abs_n >= 1e4:
        return f'{n/1e4:.1f}万'
    if isinstance(n, float):
        return f'{n:,.2f}'
    return f'{n:,}'


def _try_parse_numeric_text(series):
    """Try to extract numbers from text like '¥1,234.5' / '12%' / '1 234'.
    Returns True if column looks numeric-in-text."""
    import pandas as pd
    sample = series.dropna().head(30).astype(str)
    if len(sample) == 0:
        return False
    cleaned = sample.str.replace(r'[¥$€￥,，\s%％万亿元千百十]', '', regex=True)
    parsed = pd.to_numeric(cleaned, errors='coerce')
    if parsed.notna().sum() >= len(sample) * 0.5:
        return True
    return False


def _coerce_numeric_text(series):
    """Actually convert text-numeric column to float. Returns new Series or None.

    Uses pd.to_numeric(errors='coerce') instead of astype(float) so that
    mixed columns (e.g. numbers + "N/A" / "-" / text) are partially converted
    rather than entirely abandoned.
    """
    import pandas as pd
    try:
        cleaned = series.astype(str).str.replace(r'[¥$€￥,，\s千百十]', '', regex=True)
        # Handle 万/亿 multipliers
        has_wan = cleaned.str.contains('万', na=False)
        has_yi = cleaned.str.contains('亿', na=False)
        cleaned = cleaned.str.replace(r'[万亿元%％]', '', regex=True)
        result = pd.to_numeric(cleaned, errors='coerce')
        # Only keep if at least 50% of non-null values converted successfully
        if result.notna().sum() < max(1, len(series.dropna()) * 0.5):
            return None
        result[has_wan] *= 10000
        result[has_yi] *= 100000000
        return result
    except (ValueError, TypeError):
        return None


def _ensure_numeric_measures(df, measures):
    """Filter measures to only include truly numeric columns.

    For object-dtype columns that look numeric (e.g. '¥1,234'), attempt
    in-place coercion via _coerce_numeric_text.  Columns that cannot be
    converted are silently dropped from the returned list so that
    downstream analyzers never receive non-numeric measures.
    """
    import pandas as pd
    valid = []
    for col in measures:
        if col not in df.columns:
            continue
        if pd.api.types.is_numeric_dtype(df[col].dtype):
            valid.append(col)
        else:
            converted = _coerce_numeric_text(df[col])
            if converted is not None:
                df[col] = converted
                valid.append(col)
    return valid


def _classify_columns(df):
    """Classify columns into dimensions, measures, dates, and unclassified."""
    import pandas as pd
    dims = []
    measures = []
    dates = []
    unclassified = []

    for col in df.columns:
        try:
            dtype = df[col].dtype
            if pd.api.types.is_datetime64_any_dtype(dtype):
                dates.append(col)
            elif pd.api.types.is_numeric_dtype(dtype):
                nunique = df[col].nunique()
                is_int = pd.api.types.is_integer_dtype(dtype)
                # ID-like: 仅当列名看起来像 ID 且高基数整数时过滤。
                # 光凭 nunique >0.9*len 会把真实度量列（金额/数量）误判为 ID。
                name_lower = str(col).lower()
                id_keywords = ('id', '编号', '单号', 'code', 'number', '序号', 'uuid', 'guid')
                looks_like_id_name = any(k in name_lower for k in id_keywords)
                if is_int and nunique > 0.9 * len(df) and nunique > 50 and looks_like_id_name:
                    unclassified.append(col)
                    continue
                # Low cardinality integers might be categorical
                if is_int and nunique <= 10 and df[col].min() >= 0:
                    dims.append(col)
                else:
                    measures.append(col)
            elif pd.api.types.is_object_dtype(dtype) or (
                    hasattr(pd.api.types, 'is_categorical_dtype')
                    and pd.api.types.is_categorical_dtype(dtype)):
                sample = df[col].dropna().head(30)
                if len(sample) == 0:
                    unclassified.append(col)
                    continue
                # Try date
                try:
                    parsed = pd.to_datetime(sample, format='mixed', dayfirst=False)
                    if parsed.notna().sum() > len(sample) * 0.7:
                        dates.append(col)
                        continue
                except (ValueError, TypeError):
                    pass
                # Try numeric-in-text (e.g. "¥1,234", "12%")
                if _try_parse_numeric_text(df[col]):
                    measures.append(col)
                    continue
                # Categorical
                nunique = df[col].nunique()
                if nunique <= 200:
                    dims.append(col)
                else:
                    unclassified.append(col)
            else:
                unclassified.append(col)
        except Exception:
            unclassified.append(col)

    return dims, measures, dates, unclassified


# ── Analysis Functions ─────────────────────────────────────────────────

def _classify_sheet_role(df, sheet_name):
    """Infer sheet role based on row count and name heuristics.

    Returns one of:
      - 'config'  : very few rows, likely parameter/config table → skip analysis
      - 'summary' : aggregated totals → extract KPIs only, no trend/distribution
      - 'data'    : regular data table → full analysis
    """
    name_lower = sheet_name.lower()
    # Config / parameter sheets
    config_keywords = ('config', '配置', '参数', 'param', 'setting', '设置', '字典', 'dict', 'lookup')
    if any(k in name_lower for k in config_keywords):
        return 'config'
    if df.shape[0] <= 3:
        return 'config'
    # Summary / aggregate sheets
    summary_keywords = ('汇总', '总计', 'summary', 'total', 'overview', '概览', '合计')
    if any(k in name_lower for k in summary_keywords):
        return 'summary'
    if df.shape[0] <= 5 and df.shape[1] >= 3:
        return 'summary'
    return 'data'


def analyze_overview(df, sheet_name):
    """Basic data profile."""
    import pandas as pd
    import warnings as _w
    dims, measures, dates, unclassified = _classify_columns(df)
    missing = df.isnull().sum()
    missing_rate = {col: round(missing[col] / len(df) * 100, 1)
                    for col in df.columns if missing[col] > 0}
    role = _classify_sheet_role(df, sheet_name)

    # 数据质量标记 —— 供 _reader_guide must_honor 判定
    # ⚠️ 强信号识别：只信任已 classify 的日期列，且再做 80% 可解析兜底，
    # 避免把"日期"字样但实际是数字的列误当日期（pd.to_datetime 会把 20891103 解成 2089-11-03）
    data_quality_flags = []
    today = pd.Timestamp.now().normalize()
    for dc in dates:
        s = df[dc]
        if pd.api.types.is_datetime64_any_dtype(s):
            parsed = s
        elif s.dtype == object:
            try:
                with _w.catch_warnings():
                    _w.simplefilter('ignore')
                    parsed = pd.to_datetime(s, errors='coerce')
            except Exception:
                continue
            non_null = s.notna().sum()
            if non_null == 0 or parsed.notna().sum() / non_null < 0.8:
                continue
        else:
            continue  # int/float 列即使在 date_columns 里也不信任
        if (parsed > today).any():
            future_count = int((parsed > today).sum())
            data_quality_flags.append(f'future_date:{dc}({future_count})')

    return {
        'sheet': sheet_name,
        'role': role,
        'rows': len(df),
        'columns': len(df.columns),
        'column_names': list(df.columns),
        'dimensions': dims,
        'measures': measures,
        'date_columns': dates,
        'unclassified': unclassified,
        'missing': missing_rate,
        'duplicate_rows': int(df.duplicated().sum()),
        'data_quality_flags': data_quality_flags,
    }


def compute_raw_stats(df, measures, dates=None):
    """Return raw statistics per measure column — facts only, no recommendations.

    Each entry contains column name, null_count, and pure statistics
    (sum/mean/median/count/nunique/max/min/std). No aggregation hint,
    no `ready_kpi.value`, no `is_core` labeling, no percentile hints.
    The model decides which metrics matter and how to present them.
    """
    import pandas as pd
    import numpy as np

    measures = _ensure_numeric_measures(df, measures)
    stats = []
    for col in measures:
        s = df[col].dropna()
        if len(s) == 0:
            continue
        count = int(s.count())
        nunique = int(s.nunique())
        null_count = int(df[col].isna().sum())
        # Basic statistics
        total = _safe(s.sum())
        mean = _safe(s.mean())
        median = _safe(s.median())
        std = _safe(s.std()) if count >= 2 else None
        max_v = _safe(s.max())
        min_v = _safe(s.min())
        p25 = _safe(s.quantile(0.25)) if count >= 4 else None
        p75 = _safe(s.quantile(0.75)) if count >= 4 else None
        p90 = _safe(s.quantile(0.9)) if count >= 10 else None
        p99 = _safe(s.quantile(0.99)) if count >= 100 else None

        entry = {
            'column': col,
            'count': count,
            'nunique': nunique,
            'null_count': null_count,
            'sum': total,
            'mean': mean,
            'median': median,
            'std': std,
            'max': max_v,
            'min': min_v,
            'p25': p25,
            'p75': p75,
            'p90': p90,
            'p99': p99,
            # Pre-formatted for convenience — the model can ignore if
            # it wants its own formatting
            'formatted': {
                'sum': _fmt_num(total),
                'mean': _fmt_num(mean),
                'median': _fmt_num(median),
            },
        }
        stats.append(entry)
    return stats




def analyze_distribution(df, measures):
    """Distribution analysis for numeric columns."""
    measures = _ensure_numeric_measures(df, measures)
    findings = []
    for col in measures:
        s = df[col].dropna()
        if len(s) < 10:
            continue
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        iqr = q3 - q1
        outlier_low = q1 - 1.5 * iqr
        outlier_high = q3 + 1.5 * iqr
        outliers = s[(s < outlier_low) | (s > outlier_high)]
        skew = _safe(s.skew())

        if len(outliers) > 0:
            findings.append({
                'type': 'outlier',
                'priority': 1,
                'column': col,
                'tag': 'alert',
                'text': (f'"{col}" 列检测到 {len(outliers)} 个离群值'
                         f'（占 {len(outliers)/len(s)*100:.1f}%），'
                         f'正常范围 [{_fmt_num(_safe(outlier_low))}, {_fmt_num(_safe(outlier_high))}]，'
                         f'极端值如 {_fmt_num(_safe(outliers.iloc[0]))}。'),
                'data': {
                    'outlier_count': len(outliers),
                    'outlier_pct': round(len(outliers) / len(s) * 100, 1),
                    'range': [_safe(outlier_low), _safe(outlier_high)],
                },
            })

        if skew is not None and abs(skew) > 1.5:
            findings.append({
                'type': 'distribution',
                'priority': 4,
                'column': col,
                'tag': 'structure',
                'text': (f'"{col}" 偏度={skew:.2f}（>0 为右偏，<0 为左偏），'
                         f'中位数={_fmt_num(_safe(s.median()))}，'
                         f'均值={_fmt_num(_safe(s.mean()))}。'),
                'data': {
                    'skew': skew,
                    'median': _safe(s.median()),
                    'mean': _safe(s.mean()),
                    'sample_size': int(len(s)),
                },
            })

    return findings


def analyze_categorical(df, dims, measures):
    """Category breakdown: concentration, ranking."""
    measures = _ensure_numeric_measures(df, measures)
    findings = []
    for dim in dims:
        nunique = df[dim].nunique()
        if nunique < 2 or nunique > 50:
            continue
        vc = df[dim].value_counts()

        # Concentration (Pareto)
        if nunique >= 3 and len(measures) > 0:
            top_measure = measures[0]
            grouped = df.groupby(dim)[top_measure].sum().sort_values(ascending=False)
            total = grouped.sum()
            if total > 0:
                cumsum = grouped.cumsum()
                # Top items contributing to 80%
                top_80 = (cumsum <= total * 0.8).sum() + 1
                top_pct = grouped.iloc[0] / total * 100 if len(grouped) > 0 else 0

                if top_80 <= max(2, nunique * 0.3):
                    findings.append({
                        'type': 'concentration',
                        'priority': 2,
                        'column': dim,
                        'measure': top_measure,
                        'tag': 'rank',
                        'text': (f'按 "{dim}" 分组（按 {top_measure} 求和）：'
                                 f'Top {top_80} 项（共 {nunique} 项）累计占比 ≥80%；'
                                 f'Top1 "{grouped.index[0]}" 占比 {top_pct:.1f}%'
                                 f'（{_fmt_num(_safe(grouped.iloc[0]))}'
                                 f'/ {_fmt_num(_safe(total))}）。'),
                        'data': {
                            'dim': dim,
                            'measure': top_measure,
                            'aggregation': 'sum',
                            'top_items': [
                                {'name': str(idx), 'value': _safe(val),
                                 'pct': round(val / total * 100, 1)}
                                for idx, val in grouped.head(10).items()
                            ],
                            'total': _safe(total),
                            'top80_count': int(top_80),
                            'nunique': int(nunique),
                            'sample_size': int(len(df)),
                        },
                        'chart_suggestion': {
                            'type': 'horizontal_bar' if nunique > 6 else 'bar',
                            'title': f'各{dim}的{top_measure}排名',
                            'x_data': [str(x) for x in grouped.head(10).index],
                            'series': [{'name': top_measure,
                                        'data': [_safe(v) for v in grouped.head(10).values]}],
                        },
                    })

                # Pie chart for composition
                if nunique <= 8:
                    findings.append({
                        'type': 'composition',
                        'priority': 5,
                        'column': dim,
                        'measure': top_measure,
                        'tag': 'structure',
                        'text': (f'"{top_measure}"（按 {dim} 求和）构成：'
                                 + '、'.join(f'{idx}={val/total*100:.1f}%'
                                            for idx, val in grouped.head(5).items())
                                 + '。'),
                        'data': {
                            'dim': dim,
                            'measure': top_measure,
                            'aggregation': 'sum',
                            'composition': [
                                {'name': str(idx), 'value': _safe(val),
                                 'pct': round(val / total * 100, 1)}
                                for idx, val in grouped.items()
                            ],
                            'total': _safe(total),
                            'sample_size': int(len(df)),
                        },
                        'chart_suggestion': {
                            'type': 'pie',
                            'title': f'{top_measure}的{dim}占比',
                            'data': [{'name': str(idx), 'value': _safe(val)}
                                     for idx, val in grouped.items()],
                        },
                    })

        # Cross-dimension comparison for multiple measures
        if len(measures) >= 2 and nunique <= 10:
            for m in measures[:3]:
                grouped = df.groupby(dim)[m].mean()
                if grouped.std() > 0 and len(grouped) >= 2:
                    best = grouped.idxmax()
                    worst = grouped.idxmin()
                    ratio = grouped.max() / grouped.min() if grouped.min() > 0 else None
                    if ratio and ratio > 2:
                        # per-group sample size (smallest group size)
                        group_sizes = df.groupby(dim).size()
                        min_group = int(group_sizes.min())
                        findings.append({
                            'type': 'comparison',
                            'priority': 3,
                            'column': dim,
                            'measure': m,
                            'tag': 'compare',
                            'text': (f'按 "{dim}" 分组（按 {m} 求均值）：'
                                     f'最高 "{best}"={_fmt_num(_safe(grouped.max()))}，'
                                     f'最低 "{worst}"={_fmt_num(_safe(grouped.min()))}，'
                                     f'最高/最低={ratio:.1f}。'),
                            'data': {
                                'dim': dim,
                                'measure': m,
                                'aggregation': 'mean',
                                'max_label': str(best),
                                'max_value': _safe(grouped.max()),
                                'min_label': str(worst),
                                'min_value': _safe(grouped.min()),
                                'ratio': round(_safe(ratio), 2)
                                    if _safe(ratio) is not None else None,
                                'sample_size': int(len(df)),
                                'min_group_size': min_group,
                                'reliability': (
                                    'low' if min_group < 5
                                    else 'medium' if min_group < 30
                                    else 'high'),
                            },
                        })

    return findings


def analyze_time_series(df, dates, measures):
    """Time-based trend analysis."""
    import pandas as pd
    import numpy as np
    findings = []
    df = df.copy()  # avoid mutating the caller's DataFrame
    measures = _ensure_numeric_measures(df, measures)
    for date_col in dates:
        try:
            if not pd.api.types.is_datetime64_any_dtype(df[date_col]):
                df[date_col] = pd.to_datetime(df[date_col], format='mixed', dayfirst=False)
        except (ValueError, TypeError):
            continue

        for m in measures[:3]:
            ts = df.dropna(subset=[date_col, m]).set_index(date_col)[m].sort_index()
            if len(ts) < 3:
                continue

            # Detect native granularity from median_diff
            diffs = ts.index.to_series().diff().dropna()
            if len(diffs) == 0:
                continue
            median_diff = diffs.median()
            if median_diff <= pd.Timedelta(days=2):
                freq, label = 'D', '日'
            elif median_diff <= pd.Timedelta(days=8):
                freq, label = 'W', '周'
            elif median_diff <= pd.Timedelta(days=35):
                freq, label = 'ME', '月'
            else:
                freq, label = 'QE', '季'

            # Adaptive downsample：长跨度数据的 trend chart 应聚合到更粗粒度，
            # 避免 x 轴标签过密（>30 个点不可读）。按总跨度渐进降粒度：
            #   < 120 天   → 允许日粒度（最多 ~120 点，但趋势分析仍可读）
            #   120-400 天 → 至少周粒度（最多 ~57 点）
            #   400+ 天    → 至少月粒度（最多 ~13 月 / 3 年内）
            #   1100+ 天   → 季粒度
            span_days = (ts.index.max() - ts.index.min()).days
            gran_order = ['D', 'W', 'ME', 'QE']
            label_map = {'D': '日', 'W': '周', 'ME': '月', 'QE': '季'}
            target = freq
            if span_days > 120 and gran_order.index(target) < gran_order.index('W'):
                target = 'W'
            if span_days > 400 and gran_order.index(target) < gran_order.index('ME'):
                target = 'ME'
            if span_days > 1100 and gran_order.index(target) < gran_order.index('QE'):
                target = 'QE'
            freq, label = target, label_map[target]

            resampled = ts.resample(freq).sum()
            if len(resampled) < 2:
                continue

            # Missing-period metadata: resample().sum() fills gaps with 0,
            # which is indistinguishable from real zeros. Surface the gap
            # count so the model can judge whether the trend metric is reliable.
            period_counts = ts.resample(freq).size()
            missing_periods = int((period_counts == 0).sum())
            total_periods = len(period_counts)
            missing_ratio = round(missing_periods / total_periods, 3) \
                if total_periods > 0 else 0.0

            # Linear slope on the resampled series — pure descriptive statistic,
            # no extrapolation. Lets the model state "slope per period = X"
            # without consuming a forecast.
            try:
                y = resampled.values.astype(float)
                x = np.arange(len(y))
                slope = float(np.polyfit(x, y, 1)[0]) if len(y) >= 2 else None
                if slope is not None:
                    fitted = np.polyval(np.polyfit(x, y, 1), x)
                    ss_res = float(np.sum((y - fitted) ** 2))
                    ss_tot = float(np.sum((y - y.mean()) ** 2))
                    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else None
                else:
                    r2 = None
            except Exception:
                slope, r2 = None, None

            # Overall trend
            first_half = resampled.iloc[:len(resampled)//2].mean()
            second_half = resampled.iloc[len(resampled)//2:].mean()
            if first_half > 0:
                change_pct = (second_half - first_half) / first_half * 100
                findings.append({
                    'type': 'trend',
                    'priority': 3,
                    'column': m,
                    'date_column': date_col,
                    'tag': 'trend',
                    'text': (f'"{m}" 按{label}度：前半段（{len(resampled)//2} 期）'
                             f'均值={_fmt_num(_safe(first_half))}，'
                             f'后半段（{len(resampled) - len(resampled)//2} 期）'
                             f'均值={_fmt_num(_safe(second_half))}，'
                             f'变化={change_pct:+.1f}%。'),
                    'data': {
                        'freq': label,
                        'aggregation': 'sum',
                        'first_half_mean': _safe(first_half),
                        'second_half_mean': _safe(second_half),
                        'change_pct': round(_safe(change_pct), 2)
                            if _safe(change_pct) is not None else None,
                        'slope_per_period': _safe(slope),
                        'r_squared': _safe(r2),
                        'sample_size': int(len(resampled)),
                        'total_periods': total_periods,
                        'missing_periods': missing_periods,
                        'missing_ratio': missing_ratio,
                    },
                })

            # Period-over-period changes (find biggest drops/spikes)
            if len(resampled) >= 3:
                pct_change = resampled.pct_change().replace(
                    [np.inf, -np.inf], np.nan).dropna()
                if len(pct_change) > 0:
                    max_change = pct_change.abs().idxmax()
                    max_val = pct_change[max_change]
                    if abs(max_val) > 0.3:  # >30% change
                        prev_val = _safe(resampled.get(
                            resampled.index[resampled.index.get_loc(max_change)-1],
                            None))
                        cur_val = _safe(resampled[max_change])
                        findings.append({
                            'type': 'spike',
                            'priority': 1,
                            'column': m,
                            'tag': 'alert',
                            'text': (f'"{m}" 在 {max_change.strftime("%Y-%m-%d")} '
                                     f'环比变化 {max_val*100:+.1f}%，'
                                     f'前值={_fmt_num(prev_val)}，'
                                     f'当值={_fmt_num(cur_val)}。'),
                            'data': {
                                'date': max_change.strftime('%Y-%m-%d'),
                                'pct_change': round(_safe(max_val * 100), 2),
                                'prev_value': prev_val,
                                'current_value': cur_val,
                                'aggregation': 'sum',
                                'freq': label,
                            },
                        })

    return findings


def analyze_correlation(df, measures):
    """Pearson correlation between numeric columns.

    Emits all pairs with |r|>0.7 regardless of sample size — but every
    finding carries `sample_size` and `reliability` so the model can judge
    whether to cite it. We do NOT hard-cut at n<30 because that would hide
    legitimate signal in small but well-curated datasets.
    """
    measures = _ensure_numeric_measures(df, measures)
    findings = []
    if len(measures) < 2:
        return findings

    corr = df[measures].corr()
    seen = set()
    for i, c1 in enumerate(measures):
        for j, c2 in enumerate(measures):
            if i >= j:
                continue
            key = (c1, c2)
            if key in seen:
                continue
            seen.add(key)
            r = _safe(corr.loc[c1, c2])
            if r is not None and abs(r) > 0.7:
                # Pairwise complete observations (both columns non-null)
                pair_n = int(df[[c1, c2]].dropna().shape[0])
                reliability = (
                    'low' if pair_n < 30
                    else 'medium' if pair_n < 200
                    else 'high')
                findings.append({
                    'type': 'correlation',
                    'priority': 4,
                    'columns': [c1, c2],
                    'tag': 'structure',
                    'text': (f'"{c1}" 与 "{c2}"：Pearson r={r:.2f}（n={pair_n}，'
                             f'reliability={reliability}）。'),
                    'data': {
                        'columns': [c1, c2],
                        'pearson_r': r,
                        'sample_size': pair_n,
                        'reliability': reliability,
                    },
                    'chart_suggestion': {
                        'type': 'scatter',
                        'title': f'{c1} vs {c2} 相关性',
                        'x_label': c1,
                        'y_label': c2,
                        'series': [{
                            'name': f'{c1} vs {c2}',
                            'data': [[_safe(row[c1]), _safe(row[c2])]
                                     for _, row in df[[c1, c2]].dropna().head(200).iterrows()],
                        }],
                    },
                })

    return findings


def analyze_data_quality(df):
    """Data quality findings."""
    findings = []
    total = len(df)
    if total == 0:
        return findings

    # Missing values
    missing = df.isnull().sum()
    high_missing = [(col, int(cnt)) for col, cnt in missing.items()
                    if cnt > total * 0.1]
    if high_missing:
        cols_desc = '、'.join(f'"{c}"({n/total*100:.0f}%)' for c, n in high_missing[:5])
        findings.append({
            'type': 'data_quality',
            'priority': 5,
            'tag': 'alert',
            'text': f'以下列缺失率超过 10%：{cols_desc}。分析结论可能受缺失数据影响。',
        })

    # Duplicates
    dup_count = df.duplicated().sum()
    if dup_count > 0:
        findings.append({
            'type': 'data_quality',
            'priority': 5,
            'tag': 'alert',
            'text': f'数据中存在 {dup_count} 行完全重复（占 {dup_count/total*100:.1f}%）。',
        })

    return findings


def analyze_periodicity(df, dates, measures):
    """Detect weekly/monthly periodicity and compute MoM/YoY growth rates."""
    import pandas as pd
    import numpy as np
    measures = _ensure_numeric_measures(df, measures)
    findings = []
    for date_col in dates:
        try:
            if not pd.api.types.is_datetime64_any_dtype(df[date_col]):
                df = df.copy()
                df[date_col] = pd.to_datetime(df[date_col], format='mixed', dayfirst=False)
        except (ValueError, TypeError):
            continue

        for m in measures[:3]:
            ts = df.dropna(subset=[date_col, m]).copy()
            if len(ts) < 7:
                continue

            # ── Weekly pattern detection ──
            try:
                ts['_dow'] = ts[date_col].dt.dayofweek
                dow_agg = ts.groupby('_dow')[m].mean()
                if len(dow_agg) >= 5 and dow_agg.std() > 0:
                    cv = dow_agg.std() / dow_agg.mean() if dow_agg.mean() != 0 else 0
                    if cv > 0.15:  # coefficient of variation > 15% → meaningful pattern
                        best_day = dow_agg.idxmax()
                        worst_day = dow_agg.idxmin()
                        day_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
                        ratio = dow_agg.max() / dow_agg.min() if dow_agg.min() > 0 else 0
                        # weeks of coverage — controls reliability
                        date_span = (ts[date_col].max() - ts[date_col].min()).days
                        weeks_covered = max(1, date_span // 7)
                        reliability = (
                            'low' if weeks_covered < 4
                            else 'medium' if weeks_covered < 12
                            else 'high')
                        findings.append({
                            'type': 'periodicity',
                            'priority': 3,
                            'column': m,
                            'date_column': date_col,
                            'tag': 'structure',
                            'text': (f'"{m}" 周内 CV={cv:.1%}（按 dayofweek 求均值）：'
                                     f'{day_names[best_day]}={_fmt_num(_safe(dow_agg.max()))}，'
                                     f'{day_names[worst_day]}={_fmt_num(_safe(dow_agg.min()))}，'
                                     f'最高/最低={ratio:.1f}（weeks_covered={weeks_covered}，'
                                     f'reliability={reliability}）。'),
                            'data': {
                                'aggregation': 'mean',
                                'cv': round(_safe(cv), 4),
                                'best_day': day_names[best_day],
                                'best_value': _safe(dow_agg.max()),
                                'worst_day': day_names[worst_day],
                                'worst_value': _safe(dow_agg.min()),
                                'ratio': round(_safe(ratio), 2)
                                    if _safe(ratio) is not None else None,
                                'sample_size': int(len(ts)),
                                'weeks_covered': int(weeks_covered),
                                'reliability': reliability,
                            },
                            'chart_suggestion': {
                                'type': 'bar',
                                'title': f'{m}的周内分布',
                                'x_data': [day_names[i] for i in dow_agg.index],
                                'series': [{'name': f'平均{m}',
                                            'data': [_safe(v) for v in dow_agg.values]}],
                            },
                        })
            except Exception:
                pass

            # ── MoM / YoY growth rates ──
            try:
                monthly = ts.set_index(date_col)[m].resample('ME').sum()
                if len(monthly) < 2:
                    continue

                # Month-over-month
                mom = monthly.pct_change().replace(
                    [np.inf, -np.inf], np.nan).dropna()
                if len(mom) >= 1:
                    latest_mom = _safe(mom.iloc[-1] * 100)
                    latest_month = monthly.index[-1].strftime('%Y-%m')
                    if latest_mom is not None:
                        cur_val = _safe(monthly.iloc[-1])
                        prev_val = _safe(monthly.iloc[-2])
                        findings.append({
                            'type': 'growth_rate',
                            'priority': 2,
                            'column': m,
                            'date_column': date_col,
                            'tag': 'trend',
                            'text': (f'"{m}" 最近一期（{latest_month}）环比 '
                                     f'{latest_mom:+.1f}%，'
                                     f'当期={_fmt_num(cur_val)}，'
                                     f'上期={_fmt_num(prev_val)}。'),
                            'data': {
                                'period_type': 'MoM',
                                'aggregation': 'sum',
                                'freq': 'month',
                                'period': latest_month,
                                'pct': round(latest_mom, 2),
                                'current_value': cur_val,
                                'previous_value': prev_val,
                                'sample_size': int(len(monthly)),
                            },
                        })

                # Year-over-year (if enough data)
                if len(monthly) >= 13:
                    yoy = monthly.pct_change(periods=12).dropna()
                    if len(yoy) >= 1:
                        latest_yoy = _safe(yoy.iloc[-1] * 100)
                        if latest_yoy is not None:
                            cur_val = _safe(monthly.iloc[-1])
                            prev_val = _safe(monthly.iloc[-13])
                            findings.append({
                                'type': 'growth_rate',
                                'priority': 2,
                                'column': m,
                                'date_column': date_col,
                                'tag': 'trend',
                                'text': (f'"{m}" 最近一期（{latest_month}）同比 '
                                         f'{latest_yoy:+.1f}%。'),
                                'data': {
                                    'period_type': 'YoY',
                                    'aggregation': 'sum',
                                    'freq': 'month',
                                    'period': latest_month,
                                    'pct': round(latest_yoy, 2),
                                    'current_value': cur_val,
                                    'previous_value': prev_val,
                                    'sample_size': int(len(monthly)),
                                },
                            })
            except Exception:
                pass

    return findings


def analyze_percentile_profile(df, measures):
    """Generate percentile profiles (p25/p50/p75/p90/p95/p99) for numeric columns.
    Detects long-tail distributions and concentration patterns."""
    measures = _ensure_numeric_measures(df, measures)
    findings = []
    for col in measures:
        s = df[col].dropna()
        if len(s) < 20:
            continue

        try:
            pcts = s.quantile([0.25, 0.5, 0.75, 0.9, 0.95, 0.99])
            p50 = _safe(pcts[0.5])
            p90 = _safe(pcts[0.9])
            mean = _safe(s.mean())
            total = _safe(s.sum())

            if p50 is None or p90 is None or mean is None or total is None:
                continue
            if total == 0:
                continue

            # Long-tail detection: top 10% contributing disproportionately
            threshold_90 = pcts[0.9]
            top10_sum = s[s >= threshold_90].sum()
            top10_pct = top10_sum / total * 100 if total != 0 else 0

            # Mean/median divergence
            mean_median_ratio = mean / p50 if p50 != 0 else None

            n = int(len(s))
            # Reliability of p90/p95/p99 depends on sample size; p99 needs ~100
            reliability = (
                'low' if n < 50
                else 'medium' if n < 200
                else 'high')

            if top10_pct > 40:
                findings.append({
                    'type': 'percentile',
                    'priority': 3,
                    'column': col,
                    'tag': 'structure',
                    'text': (f'"{col}" Top 10%（≥p90）贡献 {top10_pct:.1f}% 总量；'
                             f'中位数={_fmt_num(p50)}，均值={_fmt_num(mean)}，'
                             f'均值/中位数={mean_median_ratio:.2f}（n={n}，'
                             f'reliability={reliability}）。')
                              if mean_median_ratio else
                              (f'"{col}" Top 10%（≥p90）贡献 {top10_pct:.1f}% 总量；'
                               f'中位数={_fmt_num(p50)}，均值={_fmt_num(mean)}'
                               f'（n={n}，reliability={reliability}）。'),
                    'data': {
                        'p25': _safe(pcts[0.25]),
                        'p50': p50,
                        'p75': _safe(pcts[0.75]),
                        'p90': p90,
                        'p95': _safe(pcts[0.95]),
                        'p99': _safe(pcts[0.99]),
                        'mean': mean,
                        'mean_median_ratio': _safe(mean_median_ratio),
                        'top10_contribution_pct': round(top10_pct, 1),
                        'sample_size': n,
                        'reliability': reliability,
                    },
                })
            elif mean_median_ratio and mean_median_ratio > 2:
                findings.append({
                    'type': 'percentile',
                    'priority': 4,
                    'column': col,
                    'tag': 'structure',
                    'text': (f'"{col}" 均值={_fmt_num(mean)}，中位数={_fmt_num(p50)}，'
                             f'均值/中位数={mean_median_ratio:.2f}（n={n}，'
                             f'reliability={reliability}）。'),
                    'data': {
                        'p25': _safe(pcts[0.25]),
                        'p50': p50,
                        'p75': _safe(pcts[0.75]),
                        'p90': p90,
                        'p95': _safe(pcts[0.95]),
                        'p99': _safe(pcts[0.99]),
                        'mean': mean,
                        'mean_median_ratio': _safe(mean_median_ratio),
                        'sample_size': n,
                        'reliability': reliability,
                    },
                })
        except Exception:
            continue

    return findings


def analyze_cross_dimension(df, dims, measures):
    """Cross-tabulation analysis: find interaction effects between two dimensions."""
    measures = _ensure_numeric_measures(df, measures)
    findings = []
    if len(dims) < 2 or not measures:
        return findings

    # Only analyze dimension pairs with manageable cardinality
    viable_dims = [d for d in dims if 2 <= df[d].nunique() <= 15]
    if len(viable_dims) < 2:
        return findings

    top_measure = measures[0]

    for i in range(min(len(viable_dims), 3)):
        for j in range(i + 1, min(len(viable_dims), 3)):
            dim1, dim2 = viable_dims[i], viable_dims[j]
            try:
                cross = df.groupby([dim1, dim2])[top_measure].sum().unstack(fill_value=0)
                if cross.shape[0] < 2 or cross.shape[1] < 2:
                    continue

                total = cross.values.sum()
                if total == 0:
                    continue

                # Find dominant cell
                max_idx = cross.stack().idxmax()
                max_val = cross.stack().max()
                max_pct = max_val / total * 100

                # Find biggest gap within a dimension
                row_means = cross.mean(axis=1)
                col_cv = cross.apply(lambda r: r.std() / r.mean() if r.mean() > 0 else 0, axis=1)
                most_varied_row = col_cv.idxmax() if col_cv.max() > 0.3 else None

                # Threshold: for a N×M grid, uniform distribution gives 100/(N*M)% per cell.
                # A cell exceeding 3× the uniform expectation is noteworthy.
                n_cells = cross.shape[0] * cross.shape[1]
                uniform_pct = 100.0 / n_cells if n_cells > 0 else 100
                threshold = max(uniform_pct * 3, 8)  # at least 8% to avoid noise
                if max_pct > threshold:
                    # per-cell sample sizes (smallest non-zero count)
                    cell_counts = df.groupby([dim1, dim2]).size()
                    min_cell = int(cell_counts.min()) if len(cell_counts) > 0 else 0
                    reliability = (
                        'low' if min_cell < 5
                        else 'medium' if min_cell < 30
                        else 'high')

                    text = (f'"{dim1}" × "{dim2}"（按 {top_measure} 求和）：'
                            f'Top cell={max_idx[0]} × {max_idx[1]}，'
                            f'占 {max_pct:.1f}%（{_fmt_num(_safe(max_val))}/'
                            f'{_fmt_num(_safe(total))}）。')
                    if most_varied_row is not None:
                        best_in_row = cross.loc[most_varied_row].idxmax()
                        row_cv = float(col_cv.max())
                        text += (f' "{most_varied_row}" 跨 "{dim2}" CV={row_cv:.2f}，'
                                 f'最大 cell="{best_in_row}"。')
                    text += (f'（min_cell_n={min_cell}，reliability={reliability}）')

                    # Build heatmap data
                    heatmap_data = []
                    for ri, row_label in enumerate(cross.index):
                        for ci, col_label in enumerate(cross.columns):
                            heatmap_data.append([ci, ri, _safe(cross.iloc[ri, ci])])

                    findings.append({
                        'type': 'cross_dimension',
                        'priority': 3,
                        'columns': [dim1, dim2],
                        'measure': top_measure,
                        'tag': 'compare',
                        'text': text,
                        'data': {
                            'aggregation': 'sum',
                            'top_cell': {
                                'labels': [str(max_idx[0]), str(max_idx[1])],
                                'value': _safe(max_val),
                                'pct': round(_safe(max_pct), 2)
                                    if _safe(max_pct) is not None else None,
                            },
                            'total': _safe(total),
                            'grid_shape': [int(cross.shape[0]), int(cross.shape[1])],
                            'min_cell_n': min_cell,
                            'sample_size': int(len(df)),
                            'reliability': reliability,
                        },
                        'chart_suggestion': {
                            'type': 'heatmap',
                            'title': f'{dim1} × {dim2} 的 {top_measure} 分布',
                            'x_data': [str(c) for c in cross.columns],
                            'y_data': [str(r) for r in cross.index],
                            'data': heatmap_data,
                        },
                    })
            except Exception:
                continue

    return findings


def _try_inspect_data_traps(filepath):
    """Call xlsx_reader.inspect_file to get data_traps. Returns [] if fails or not xlsx."""
    try:
        from pathlib import Path
        if Path(filepath).suffix.lower() not in ('.xlsx', '.xlsm'):
            return []
        # 动态导入同级目录的 xlsx_reader
        script_dir = Path(__file__).resolve().parent
        if str(script_dir) not in sys.path:
            sys.path.insert(0, str(script_dir))
        import xlsx_reader  # type: ignore
        result = xlsx_reader.inspect_file(str(filepath))
        if isinstance(result, dict):
            return result.get('data_traps', []) or []
    except Exception:
        pass
    return []


def analyze(filepath, sheet=None, encoding=None, profile_only=False,
            head=None, sample=None, max_size_mb=DEFAULT_MAX_SIZE_MB):
    """Return facts-only analysis: profile, raw stats, data traps, findings (数字).

    Skill philosophy (lean):
      - machines do statistics + technical trap detection
      - the model decides which metrics matter, how to visualize, and the narrative
      - no `ready_kpi.value`, no `ready_insight`, no `chart_suggestion` specs

    超大文件处理：
      - 默认 size > max_size_mb (200MB) 触发 fail-fast，返回 error_class='file_too_large'，
        提示模型用 chunked pandas 或显式 --head/--sample
      - --head N：只读前 N 行（适合验证流程或获取头部样本）
      - --sample N：等概率随机抽样 N 行（适合无偏统计估计，仅 csv/tsv）
      - --profile-only：跳过 finding 分析，仅出 profile 与 raw_stats（最快路径）

    Returns a minimal structure the model can read freely:
      {
        'ok': bool,
        'file': str,
        'profile': [{sheet, rows, cols, column_names, dtype…, dimensions,
                     measures, date_columns, missing, data_quality_flags}],
        'raw_stats': [{sheet, column, count, nunique, null_count,
                       sum, mean, median, std, max, min, p25, p75, p90, p99,
                       formatted: {sum, mean, median}}],
        'findings': [{sheet, type, column, data: {…numeric facts…}}],
        'data_traps': [{type, note, suggested_read_code, …}],
        'skipped': […],
        'human_summary': str,
        'sampling': {mode: 'head'|'sample'|None, n: int, file_size_mb: float},
      }
    """
    data_traps = _try_inspect_data_traps(filepath)
    sampling = {'mode': None, 'n': None, 'file_size_mb': 0.0}

    # Pre-flight size check — 显式 head/sample/profile_only 可绕过
    size_ok, size_mb = _check_size_limit(filepath, max_size_mb)
    sampling['file_size_mb'] = round(size_mb, 1)
    if not size_ok and head is None and sample is None and not profile_only:
        return {
            'ok': False,
            'error_class': 'file_too_large',
            'file': str(filepath),
            'file_size_mb': round(size_mb, 1),
            'size_limit_mb': max_size_mb,
            'human_summary': (
                f'文件 {size_mb:.0f} MB 超过 {max_size_mb} MB 阈值；'
                f'默认 fail-fast 避免单次 read_excel/read_csv 占满内存'
            ),
            'next_action': {
                'code': 'use_explicit_subset_or_chunked_read',
                'options': [
                    f'快速画像：xlsx_analyze.py "{filepath}" --profile-only',
                    f'读前 N 行：xlsx_analyze.py "{filepath}" --head 100000',
                    f'随机抽样：xlsx_analyze.py "{filepath}" --sample 200000  (仅 csv/tsv)',
                    '或在 Step 2 自己写 chunked pandas：'
                    'for chunk in pd.read_csv(file, chunksize=200_000): ...'
                    ' 然后逐块聚合后合并',
                ],
                'rationale': (
                    '脚本职责是事实摘录器；对超大文件用 chunked 聚合是模型的'
                    'Step 2 工作。本阈值可用 --max-size-mb 调整，但建议保留默认'
                    '以防内存爆炸。'
                ),
            },
            'data_traps': data_traps,
        }

    try:
        sheets_data = _read_data(filepath, sheet, encoding,
                                  head=head, sample=sample)
        if head is not None:
            sampling['mode'] = 'head'
            sampling['n'] = head
        elif sample is not None:
            sampling['mode'] = 'sample'
            sampling['n'] = sample
    except MemoryError as e:
        return {
            'ok': False,
            'error_class': 'memory_error',
            'human_summary': f'内存不足，建议显式 --head 或 chunked read: {e}',
            'file_size_mb': round(size_mb, 1),
            'data_traps': data_traps,
        }
    except Exception as e:
        return {
            'ok': False,
            'error_class': 'read_failed',
            'human_summary': f'读取失败: {e}',
            'data_traps': data_traps,
        }

    all_findings = []
    all_stats = []
    all_profiles = []
    skipped = []

    for sheet_name, df in sheets_data:
        if df.empty or df.shape[0] == 0:
            skipped.append({'sheet': sheet_name, 'reason': '空 sheet'})
            continue

        try:
            profile = analyze_overview(df, sheet_name)
            all_profiles.append(profile)
        except Exception as e:
            skipped.append({'sheet': sheet_name, 'reason': f'profile 失败: {e}'})
            continue

        role = profile['role']
        if role == 'config':
            skipped.append({'sheet': sheet_name, 'reason': '角色为 config，跳过分析'})
            continue

        dims = profile['dimensions']
        measures = profile['measures']
        dates = profile['date_columns']

        # Coerce text-numeric columns so downstream analyzers can use them
        import pandas as pd
        converted_cols = []
        for col in list(measures):
            if pd.api.types.is_object_dtype(df[col].dtype):
                new_series = _coerce_numeric_text(df[col])
                if new_series is not None:
                    df[col] = new_series
                    converted_cols.append(col)
                else:
                    measures.remove(col)
                    dims.append(col)
        if converted_cols:
            profile['converted_to_numeric'] = converted_cols

        if not measures:
            skipped.append({'sheet': sheet_name,
                            'reason': f'未识别出数值列，columns={list(df.columns)}'})

        # Raw stats — facts only。即使 profile_only=True 也输出，作为 spot check 锚点。
        # 计算成本远低于 analyzer 全跑（约 5% of total），收益高（防 case_t04 类编造）。
        try:
            stats = compute_raw_stats(df, measures, dates)
            for s in stats:
                s['sheet'] = sheet_name
            all_stats.extend(stats)
        except Exception as e:
            skipped.append({'sheet': sheet_name, 'analysis': 'raw_stats',
                            'reason': str(e)})

        if profile_only:
            # profile_only 只跳过 finding analyzers，raw_stats 已在上方收集
            continue

        if role == 'summary':
            skipped.append({'sheet': sheet_name,
                            'reason': '角色为 summary，仅提取 raw_stats，跳过详细分析'})
            continue

        # Finding analyzers — each returns numeric facts (text fields are kept
        # as concise fact descriptions, not narrative; no chart_suggestion spec)
        analyses = [
            ('distribution', lambda: analyze_distribution(df, measures)),
            ('categorical', lambda: analyze_categorical(df, dims, measures)),
            ('time_series', lambda: analyze_time_series(df, dates, measures)),
            ('correlation', lambda: analyze_correlation(df, measures)),
            ('data_quality', lambda: analyze_data_quality(df)),
            ('periodicity', lambda: analyze_periodicity(df, dates, measures)),
            ('percentile', lambda: analyze_percentile_profile(df, measures)),
            ('cross_dimension', lambda: analyze_cross_dimension(df, dims, measures)),
        ]
        for name, fn in analyses:
            try:
                results = fn()
                for f in results:
                    f['sheet'] = sheet_name
                    # ⚠️ Lean 哲学护栏 — 不要解除以下 strip：
                    # analyzer 函数内部历史上构造了 chart_suggestion / level / tag 字段
                    # （图表推荐 / 重要性标签 / 业务标签），属于"业务呈现层"。
                    # Lean skill 定位是"事实摘录器"，不做这些建议；由模型自己判断怎么用 findings。
                    # 即便未来加新 analyzer，也要遵守这一边界 —— 想加业务建议层应单独走另一个脚本，
                    # 不要 by-pass 这里。
                    f.pop('chart_suggestion', None)
                    f.pop('level', None)
                    f.pop('tag', None)
                all_findings.extend(results)
            except Exception as e:
                skipped.append({'sheet': sheet_name, 'analysis': name,
                                'reason': str(e)})

    if profile_only:
        return {
            'ok': True,
            'file': str(filepath),
            'mode': 'profile_only',
            'sheets_profiled': len(all_profiles),
            'profile': all_profiles,
            'raw_stats': all_stats,
            'data_traps': data_traps,
            'skipped': skipped,
            'sampling': sampling,
            'human_summary': (
                f'数据画像：{len(all_profiles)} sheet，'
                f'{len(all_stats)} 列 raw_stats，'
                f'{len(data_traps)} 个 data_traps'
            ),
        }

    # Sort findings by priority (no presentation enrichment)
    all_findings.sort(key=lambda x: x.get('priority', 99))

    types_found = sorted(set(f['type'] for f in all_findings))
    summary_parts = [
        f'{len(all_stats)} 列 raw_stats',
        f'{len(all_findings)} 条 findings',
    ]
    if data_traps:
        summary_parts.append(
            f'{len(data_traps)} data_traps'
            f'({", ".join(sorted(set(t.get("type","") for t in data_traps)))})'
        )

    if sampling['mode']:
        summary_parts.append(
            f'采样模式={sampling["mode"]}(n={sampling["n"]})')

    return {
        'ok': True,
        'file': str(filepath),
        'sheets_analyzed': len(sheets_data),
        'profile': all_profiles,
        'raw_stats': all_stats,
        'findings': all_findings,
        'analysis_types': types_found,
        'skipped': skipped,
        'data_traps': data_traps,
        'sampling': sampling,
        'human_summary': '分析完成：' + '、'.join(summary_parts),
    }


def main():
    import warnings
    warnings.filterwarnings('ignore')  # 压制 openpyxl/pandas 的 stderr warnings

    parser = argparse.ArgumentParser(description='Automated Excel/CSV analysis')
    parser.add_argument('file', help='Path to .xlsx/.csv/.tsv file')
    parser.add_argument('--sheet', help='Specific sheet name')
    parser.add_argument('--encoding', help='CSV encoding')
    parser.add_argument('--output', help='Write findings to JSON file')
    parser.add_argument('--profile-only', action='store_true',
                        help='Only output data profile, skip full analysis')
    parser.add_argument('--head', type=int,
                        help='Read only first N rows (for fast preview of large files)')
    parser.add_argument('--sample', type=int,
                        help='Random sample N rows (csv/tsv only; uses skiprows)')
    parser.add_argument('--max-size-mb', type=int, default=DEFAULT_MAX_SIZE_MB,
                        help=f'File size limit MB (default {DEFAULT_MAX_SIZE_MB}). '
                             'Beyond this returns error_class=file_too_large unless '
                             '--head/--sample/--profile-only is given.')
    args = parser.parse_args()

    if not Path(args.file).exists():
        result = {
            'ok': False,
            'error_class': 'file_not_found',
            'human_summary': f'文件不存在: {args.file}',
            'next_action': {'code': 'stop_and_report'},
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(2)

    result = analyze(args.file, args.sheet, args.encoding,
                     profile_only=args.profile_only,
                     head=args.head, sample=args.sample,
                     max_size_mb=args.max_size_mb)

    def _json_safe_default(obj):
        """Safely serialize numpy/pandas types; never fall through to str()."""
        import numpy as np
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            v = float(obj)
            if np.isnan(v) or np.isinf(v):
                return None
            return round(v, 6)
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        if isinstance(obj, (np.ndarray,)):
            return obj.tolist()
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        # Last resort: str, but log a warning
        return str(obj)

    output_json = json.dumps(result, ensure_ascii=False, indent=2, default=_json_safe_default)

    if args.output:
        Path(args.output).write_text(output_json, encoding='utf-8')

    print(output_json)
    sys.exit(0 if result['ok'] else 1)


if __name__ == '__main__':
    main()
