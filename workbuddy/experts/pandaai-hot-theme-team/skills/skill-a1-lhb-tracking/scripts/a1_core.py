"""Core logic for A1 Longhubang capital tracking alpha.

The module is deliberately data-source agnostic. Production scripts fetch data
from PandaAI data, then pass pandas DataFrames into these functions.
"""

from __future__ import annotations

import bisect
import math
from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd


FACTOR_ID = "A1"
FACTOR_NAME = "Longhubang capital tracking"
DEFAULT_LOOKBACK_DAYS = 30
DEFAULT_MIN_HISTORY = 3

REQUIRED_FACTOR_COLUMNS = [
    "trade_date",
    "asset_type",
    "ts_code",
    "factor_id",
    "factor_name",
    "factor_value",
    "score",
    "rank",
    "signal",
    "confidence",
    "data_version",
    "update_time",
]


@dataclass(frozen=True)
class SeatStats:
    agency: str
    sample_count: int
    win_rate: float
    avg_win: float
    avg_loss_abs: float
    payoff_ratio: float
    mean_next_open_premium: float
    seat_score: float


def normalize_date(value: object) -> str | None:
    """Normalize date-like values to YYYYMMDD strings."""
    if value is None or pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y%m%d")
    text = str(value).strip()
    if not text:
        return None
    if text.endswith(".0"):
        text = text[:-2]
    text = text.replace("-", "").replace("/", "")
    return text[:8]


def _copy_frame(df: pd.DataFrame | None, columns: Iterable[str]) -> pd.DataFrame:
    if df is None or len(df) == 0:
        return pd.DataFrame(columns=list(columns))
    return df.copy()


def _as_numeric(frame: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    for column in columns:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


def _first_non_null(series: pd.Series) -> object:
    non_null = series.dropna()
    if len(non_null) == 0:
        return np.nan
    return non_null.iloc[0]


def _sum_numeric(series: pd.Series) -> float:
    values = pd.to_numeric(series, errors="coerce")
    return float(values.sum(min_count=1)) if values.notna().any() else np.nan


def aggregate_buy_detail_by_agency(buy_detail: pd.DataFrame, group_cols: list[str] | None = None) -> pd.DataFrame:
    """Collapse duplicate buy-side agency rows before scoring seats."""
    if len(buy_detail) == 0:
        return buy_detail.copy()

    frame = buy_detail.copy()
    group_cols = group_cols or ["date", "symbol", "agency"]
    group_cols = [column for column in group_cols if column in frame.columns]
    if not group_cols:
        return frame

    aggregations = {}
    for column in frame.columns:
        if column in group_cols:
            continue
        if column in {"b_value", "s_value", "buy_value", "net_buy_value"}:
            aggregations[column] = _sum_numeric
        elif column == "rank":
            aggregations[column] = "min"
        else:
            aggregations[column] = _first_non_null

    return (
        frame.groupby(group_cols, as_index=False, dropna=False)
        .agg(aggregations)
        .sort_values(group_cols)
        .reset_index(drop=True)
    )


def normalize_lhb_list(lhb_list: pd.DataFrame | None) -> pd.DataFrame:
    frame = _copy_frame(
        lhb_list,
        ["symbol", "date", "type", "reason", "amount", "volume", "turnover"],
    )
    if "ts_code" in frame.columns and "symbol" not in frame.columns:
        frame = frame.rename(columns={"ts_code": "symbol"})
    for column in ["symbol", "date", "type", "reason"]:
        if column not in frame.columns:
            frame[column] = ""
    frame["symbol"] = frame["symbol"].astype(str).str.strip()
    frame["date"] = frame["date"].map(normalize_date)
    frame["type"] = frame["type"].fillna("").astype(str)
    frame["reason"] = frame["reason"].fillna("").astype(str)
    frame = _as_numeric(frame, ["amount", "volume", "turnover"])
    return frame.dropna(subset=["symbol", "date"])


def normalize_lhb_detail(lhb_detail: pd.DataFrame | None) -> pd.DataFrame:
    frame = _copy_frame(
        lhb_detail,
        ["symbol", "date", "type", "side", "rank", "agency", "b_value", "s_value", "reason"],
    )
    if "ts_code" in frame.columns and "symbol" not in frame.columns:
        frame = frame.rename(columns={"ts_code": "symbol"})
    for column in ["symbol", "date", "type", "side", "agency", "reason"]:
        if column not in frame.columns:
            frame[column] = ""
    frame["symbol"] = frame["symbol"].astype(str).str.strip()
    frame["date"] = frame["date"].map(normalize_date)
    frame["type"] = frame["type"].fillna("").astype(str)
    frame["side"] = frame["side"].fillna("").astype(str).str.lower()
    frame["agency"] = frame["agency"].fillna("").astype(str).str.strip()
    frame["reason"] = frame["reason"].fillna("").astype(str)
    frame = _as_numeric(frame, ["rank", "b_value", "s_value", "next_open_premium"])
    return frame.dropna(subset=["symbol", "date"])


def normalize_stock_daily(stock_daily: pd.DataFrame | None) -> pd.DataFrame:
    frame = _copy_frame(
        stock_daily,
        ["symbol", "date", "open", "close", "high", "low", "volume", "amount", "trade_status"],
    )
    if "ts_code" in frame.columns and "symbol" not in frame.columns:
        frame = frame.rename(columns={"ts_code": "symbol"})
    for column in ["symbol", "date"]:
        if column not in frame.columns:
            frame[column] = ""
    frame["symbol"] = frame["symbol"].astype(str).str.strip()
    frame["date"] = frame["date"].map(normalize_date)
    frame = _as_numeric(
        frame,
        ["open", "close", "high", "low", "volume", "amount", "pre_close", "trade_status"],
    )
    frame = frame.dropna(subset=["symbol", "date"]).sort_values(["symbol", "date"])
    return frame


def normalize_trade_calendar(trade_cal: pd.DataFrame | None) -> list[str]:
    if trade_cal is None or len(trade_cal) == 0:
        return []
    frame = trade_cal.copy()
    date_col = "nature_date" if "nature_date" in frame.columns else "date"
    if "is_trade" in frame.columns:
        frame = frame[pd.to_numeric(frame["is_trade"], errors="coerce").fillna(0).astype(int) == 1]
    elif "is_trading_day" in frame.columns:
        frame = frame[pd.to_numeric(frame["is_trading_day"], errors="coerce").fillna(0).astype(int) == 1]
    dates = [normalize_date(value) for value in frame[date_col].tolist()]
    return sorted({date for date in dates if date})


def build_event_outcomes(lhb_detail: pd.DataFrame, stock_daily: pd.DataFrame) -> pd.DataFrame:
    """Attach next-open premium labels to historical buy-side LHB detail rows."""
    detail = normalize_lhb_detail(lhb_detail)
    if len(detail) == 0:
        return pd.DataFrame()

    buy_detail = detail[detail["side"].eq("buy")].copy()
    buy_detail = buy_detail[buy_detail["agency"].ne("")]
    buy_detail = _as_numeric(buy_detail, ["b_value", "s_value"])
    buy_detail = aggregate_buy_detail_by_agency(buy_detail)

    if "next_open_premium" in buy_detail.columns:
        buy_detail = _as_numeric(buy_detail, ["next_open_premium"])
        buy_detail["buy_value"] = buy_detail["b_value"].clip(lower=0).fillna(0.0)
        buy_detail["net_buy_value"] = (buy_detail["b_value"].fillna(0.0) - buy_detail["s_value"].fillna(0.0)).clip(lower=0)
        for column in ["close", "next_date", "next_open"]:
            if column not in buy_detail.columns:
                buy_detail[column] = np.nan
        return buy_detail

    prices = normalize_stock_daily(stock_daily)
    if len(prices) == 0:
        return pd.DataFrame()

    prices = prices.sort_values(["symbol", "date"]).copy()
    prices["next_date"] = prices.groupby("symbol")["date"].shift(-1)
    prices["next_open"] = prices.groupby("symbol")["open"].shift(-1)

    merged = buy_detail.merge(
        prices[["symbol", "date", "close", "next_date", "next_open"]],
        on=["symbol", "date"],
        how="left",
    )
    valid = (merged["close"] > 0) & (merged["next_open"] > 0)
    merged["next_open_premium"] = np.where(
        valid,
        merged["next_open"] / merged["close"] - 1.0,
        np.nan,
    )
    merged["buy_value"] = merged["b_value"].clip(lower=0).fillna(0.0)
    merged["net_buy_value"] = (merged["b_value"].fillna(0.0) - merged["s_value"].fillna(0.0)).clip(lower=0)
    return merged


def _trade_dates_from_inputs(
    trade_cal: pd.DataFrame | None,
    stock_daily: pd.DataFrame,
    lhb_list: pd.DataFrame,
    lhb_detail: pd.DataFrame,
) -> list[str]:
    dates = normalize_trade_calendar(trade_cal)
    if dates:
        return dates

    collected: set[str] = set()
    for frame in [stock_daily, lhb_list, lhb_detail]:
        if frame is None or len(frame) == 0:
            continue
        if "date" in frame.columns:
            collected.update(date for date in frame["date"].map(normalize_date).tolist() if date)
        if "nature_date" in frame.columns:
            collected.update(date for date in frame["nature_date"].map(normalize_date).tolist() if date)
    return sorted(collected)


def _lookback_date_set(current_date: str, trade_dates: list[str], lookback_days: int) -> set[str]:
    if not trade_dates:
        return set()
    idx = bisect.bisect_left(trade_dates, current_date)
    start_idx = max(0, idx - lookback_days)
    return set(trade_dates[start_idx:idx])


def _score_seat(history: pd.DataFrame, agency: str) -> SeatStats:
    premiums = pd.to_numeric(history["next_open_premium"], errors="coerce").dropna()
    sample_count = int(len(premiums))
    if sample_count == 0:
        return SeatStats(agency, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

    wins = premiums[premiums > 0]
    losses = premiums[premiums < 0]
    win_rate = float(len(wins) / sample_count)
    avg_win = float(wins.mean()) if len(wins) else 0.0
    avg_loss_abs = float(abs(losses.mean())) if len(losses) else 0.0
    if avg_loss_abs > 0:
        payoff_ratio = avg_win / avg_loss_abs
    else:
        payoff_ratio = 3.0 if avg_win > 0 else 0.0
    mean_premium = float(premiums.mean())

    payoff_component = min(max(payoff_ratio, 0.0), 3.0) / 3.0
    premium_component = min(max((mean_premium + 0.03) / 0.08, 0.0), 1.0)
    sample_component = min(sample_count / 10.0, 1.0)
    seat_score = 100.0 * (
        0.40 * win_rate
        + 0.25 * payoff_component
        + 0.25 * premium_component
        + 0.10 * sample_component
    )
    return SeatStats(
        agency=agency,
        sample_count=sample_count,
        win_rate=win_rate,
        avg_win=avg_win,
        avg_loss_abs=avg_loss_abs,
        payoff_ratio=float(payoff_ratio),
        mean_next_open_premium=mean_premium,
        seat_score=float(seat_score),
    )


def _events_from_inputs(lhb_list: pd.DataFrame, lhb_detail: pd.DataFrame) -> pd.DataFrame:
    events = normalize_lhb_list(lhb_list)
    if len(events) == 0:
        detail = normalize_lhb_detail(lhb_detail)
        if len(detail) == 0:
            return pd.DataFrame(columns=["date", "symbol", "type", "reason", "amount"])
        events = detail[["date", "symbol", "type", "reason"]].drop_duplicates().copy()
        events["amount"] = np.nan
    keep = ["date", "symbol", "type", "reason", "amount", "volume", "turnover"]
    for column in keep:
        if column not in events.columns:
            events[column] = np.nan if column in {"amount", "volume", "turnover"} else ""
    return events[keep].drop_duplicates(["date", "symbol", "type"]).sort_values(["date", "symbol", "type"])


def compute_a1_factor(
    lhb_list: pd.DataFrame,
    lhb_detail: pd.DataFrame,
    stock_daily: pd.DataFrame,
    trade_cal: pd.DataFrame | None = None,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    min_history: int = DEFAULT_MIN_HISTORY,
    data_version: str = "dev",
    update_time: str | None = None,
) -> pd.DataFrame:
    """Compute A1 factors for every LHB event in the supplied period.

    Seat statistics are always built from events strictly earlier than the
    current LHB date, preventing use of the current event's next-day outcome.
    """
    events = _events_from_inputs(lhb_list, lhb_detail)
    detail = normalize_lhb_detail(lhb_detail)
    prices = normalize_stock_daily(stock_daily)
    outcomes = build_event_outcomes(detail, prices)
    trade_dates = _trade_dates_from_inputs(trade_cal, prices, events, detail)

    if len(events) == 0 or len(detail) == 0:
        return pd.DataFrame(columns=REQUIRED_FACTOR_COLUMNS)

    current_buy = detail[detail["side"].eq("buy")].copy()
    current_buy = current_buy[current_buy["agency"].ne("")]
    current_buy = _as_numeric(current_buy, ["b_value", "s_value", "rank"])
    current_buy["buy_value"] = current_buy["b_value"].clip(lower=0).fillna(0.0)

    rows: list[dict[str, object]] = []
    for event in events.itertuples(index=False):
        event_type = getattr(event, "type", "")
        mask = current_buy["date"].eq(event.date) & current_buy["symbol"].eq(event.symbol)
        if event_type:
            typed_mask = mask & current_buy["type"].eq(event_type)
            if typed_mask.any():
                mask = typed_mask
        event_buys = current_buy[mask].copy()
        if len(event_buys) == 0:
            continue
        event_buys = aggregate_buy_detail_by_agency(event_buys)

        window_dates = _lookback_date_set(event.date, trade_dates, lookback_days)
        seat_details: list[dict[str, object]] = []
        agencies_with_history = 0
        weighted_score = 0.0
        total_weight = 0.0
        total_history = 0

        for buy in event_buys.itertuples(index=False):
            agency = str(buy.agency)
            history = outcomes[
                outcomes["agency"].eq(agency)
                & outcomes["date"].isin(window_dates)
                & outcomes["date"].lt(event.date)
                & outcomes["next_open_premium"].notna()
            ]
            stats = _score_seat(history, agency)
            has_history = stats.sample_count >= min_history
            if has_history:
                agencies_with_history += 1
            total_history += stats.sample_count

            weight = float(getattr(buy, "buy_value", 0.0) or 0.0)
            if weight <= 0:
                weight = 1.0
            score_for_weighting = stats.seat_score if has_history else 0.0
            weighted_score += weight * score_for_weighting
            total_weight += weight
            seat_details.append(
                {
                    "agency": agency,
                    "buy_value": float(getattr(buy, "buy_value", 0.0) or 0.0),
                    "history_count": stats.sample_count,
                    "win_rate": stats.win_rate,
                    "payoff_ratio": stats.payoff_ratio,
                    "mean_next_open_premium": stats.mean_next_open_premium,
                    "seat_score": score_for_weighting,
                }
            )

        agency_count = max(len(seat_details), 1)
        coverage = agencies_with_history / agency_count
        history_ratio = min(total_history / max(min_history * agency_count, 1), 1.0)
        confidence = min(max(0.60 * coverage + 0.40 * history_ratio, 0.0), 1.0)
        raw_seat_score = weighted_score / total_weight if total_weight > 0 else 0.0
        current_buy_value = float(event_buys["buy_value"].sum())

        top_agencies = sorted(seat_details, key=lambda x: float(x["seat_score"]), reverse=True)[:3]
        rows.append(
            {
                "trade_date": event.date,
                "asset_type": "stock",
                "ts_code": event.symbol,
                "factor_id": FACTOR_ID,
                "factor_name": FACTOR_NAME,
                "raw_seat_score": raw_seat_score,
                "current_buy_value": current_buy_value,
                "agency_count": agency_count,
                "agencies_with_history": agencies_with_history,
                "history_count": total_history,
                "confidence": confidence,
                "lhb_type": event_type,
                "lhb_reason": getattr(event, "reason", ""),
                "top_agencies": "; ".join(
                    f"{item['agency']}({item['seat_score']:.1f}/{item['history_count']})"
                    for item in top_agencies
                ),
                "data_version": data_version,
                "update_time": update_time or pd.Timestamp.now(tz="Asia/Shanghai").strftime("%Y-%m-%d %H:%M:%S%z"),
            }
        )

    factors = pd.DataFrame(rows)
    if len(factors) == 0:
        return pd.DataFrame(columns=REQUIRED_FACTOR_COLUMNS)

    amount_rank = factors.groupby("trade_date")["current_buy_value"].rank(pct=True).fillna(0.0)
    factors["amount_rank"] = amount_rank
    factors["factor_value"] = factors["raw_seat_score"] * (0.75 + 0.25 * factors["amount_rank"])
    factors["score"] = factors.groupby("trade_date")["factor_value"].rank(pct=True).mul(100).round(4)
    factors["rank"] = (
        factors.groupby("trade_date")["factor_value"]
        .rank(method="first", ascending=False)
        .astype(int)
    )
    factors["signal"] = np.where((factors["score"] >= 80.0) & (factors["confidence"] >= 0.35), "buy", "hold")
    factors["confidence"] = factors["confidence"].round(4)
    factors["factor_value"] = factors["factor_value"].round(6)

    ordered = REQUIRED_FACTOR_COLUMNS + [
        "raw_seat_score",
        "current_buy_value",
        "amount_rank",
        "agency_count",
        "agencies_with_history",
        "history_count",
        "lhb_type",
        "lhb_reason",
        "top_agencies",
    ]
    return factors[ordered].sort_values(["trade_date", "rank", "ts_code"]).reset_index(drop=True)


def attach_next_open_premium(factors: pd.DataFrame, stock_daily: pd.DataFrame) -> pd.DataFrame:
    labels = _build_next_open_labels(stock_daily)
    if len(factors) == 0 or len(labels) == 0:
        out = factors.copy()
        out["next_open_premium"] = np.nan
        return out

    out = factors.merge(
        labels,
        left_on=["ts_code", "trade_date"],
        right_on=["symbol", "date"],
        how="left",
    )
    return out.drop(columns=[column for column in ["symbol", "date"] if column in out.columns])


def _build_next_open_labels(stock_daily: pd.DataFrame) -> pd.DataFrame:
    prices = normalize_stock_daily(stock_daily).copy()
    if len(prices) == 0:
        return pd.DataFrame(columns=["symbol", "date", "close", "next_date", "next_open", "next_open_premium"])

    prices["next_date"] = prices.groupby("symbol")["date"].shift(-1)
    prices["next_open"] = prices.groupby("symbol")["open"].shift(-1)
    optional_next_columns = {
        "pre_close": "next_pre_close",
        "high": "next_high",
        "low": "next_low",
        "volume": "next_volume",
        "amount": "next_amount",
        "trade_status": "next_trade_status",
    }
    for source, target in optional_next_columns.items():
        if source in prices.columns:
            prices[target] = prices.groupby("symbol")[source].shift(-1)
    keep_columns = ["symbol", "date", "close", "next_date", "next_open"] + [
        target for target in optional_next_columns.values() if target in prices.columns
    ]
    labels = prices[keep_columns].copy()
    labels["next_open_premium"] = np.where(
        (labels["close"] > 0) & (labels["next_open"] > 0),
        labels["next_open"] / labels["close"] - 1.0,
        np.nan,
    )
    return labels


def attach_full_universe_next_open_premium(
    factors: pd.DataFrame,
    stock_daily: pd.DataFrame,
    missing_factor_value: float = 0.0,
) -> pd.DataFrame:
    """Attach labels for every stock_daily row, filling non-LHB stocks with neutral scores."""
    labels = _build_next_open_labels(stock_daily)
    if len(labels) == 0:
        out = factors.copy()
        out["next_open_premium"] = np.nan
        return out

    factor_dates = {normalize_date(value) for value in factors["trade_date"].dropna().tolist()}
    factor_dates.discard(None)
    if factor_dates:
        labels = labels[labels["date"].isin(factor_dates)].copy()

    base = labels.rename(columns={"symbol": "ts_code", "date": "trade_date"})
    factor_cols = [
        column
        for column in factors.columns
        if column not in {"close", "next_date", "next_open", "next_open_premium"}
    ]
    factor_frame = factors[factor_cols].copy()
    factor_frame["trade_date"] = factor_frame["trade_date"].map(normalize_date)
    factor_frame["ts_code"] = factor_frame["ts_code"].astype(str).str.strip()
    if "factor_id" not in factor_frame.columns:
        factor_frame["factor_id"] = FACTOR_ID
    factor_frame = factor_frame.drop_duplicates(["trade_date", "ts_code", "factor_id"], keep="first")

    out = base.merge(
        factor_frame,
        on=["ts_code", "trade_date"],
        how="left",
    )
    out["asset_type"] = out["asset_type"].fillna("stock") if "asset_type" in out else "stock"
    out["factor_id"] = out["factor_id"].fillna(FACTOR_ID) if "factor_id" in out else FACTOR_ID
    out["factor_name"] = out["factor_name"].fillna(FACTOR_NAME) if "factor_name" in out else FACTOR_NAME
    for column in ["factor_value", "score"]:
        if column not in out.columns:
            out[column] = missing_factor_value
        out[column] = pd.to_numeric(out[column], errors="coerce").fillna(missing_factor_value)
    if "signal" not in out.columns:
        out["signal"] = "hold"
    else:
        out["signal"] = out["signal"].fillna("hold")
    if "confidence" not in out.columns:
        out["confidence"] = 0.0
    else:
        out["confidence"] = pd.to_numeric(out["confidence"], errors="coerce").fillna(0.0)
    return out


def add_group_neutral_columns(
    factors_with_labels: pd.DataFrame,
    neutral_columns: list[str],
    score_col: str = "score",
    label_col: str = "next_open_premium",
) -> pd.DataFrame:
    out = factors_with_labels.copy()
    group_cols = ["trade_date"] + [column for column in neutral_columns if column in out.columns]
    if len(group_cols) <= 1:
        out[f"{score_col}_neutral"] = pd.to_numeric(out[score_col], errors="coerce")
        out[f"{label_col}_neutral"] = pd.to_numeric(out[label_col], errors="coerce")
        return out

    out[score_col] = pd.to_numeric(out[score_col], errors="coerce")
    out[label_col] = pd.to_numeric(out[label_col], errors="coerce")
    out[f"{score_col}_neutral"] = out[score_col] - out.groupby(group_cols, dropna=False)[score_col].transform("mean")
    out[f"{label_col}_neutral"] = out[label_col] - out.groupby(group_cols, dropna=False)[label_col].transform("mean")
    return out


def _select_metric_columns(frame: pd.DataFrame, score_col: str, label_col: str) -> pd.DataFrame:
    out = frame.copy()
    out["_metric_score"] = pd.to_numeric(out[score_col], errors="coerce")
    out["_metric_label"] = pd.to_numeric(out[label_col], errors="coerce")
    return out


def _rank_correlation(score: pd.Series, label: pd.Series) -> float | None:
    ranked_score = score.rank(method="average")
    ranked_label = label.rank(method="average")
    corr = ranked_score.corr(ranked_label, method="pearson")
    return None if pd.isna(corr) else float(corr)


def validate_factor_frame(factors: pd.DataFrame, require_no_forward_label: bool = True) -> list[str]:
    errors: list[str] = []
    missing = [column for column in REQUIRED_FACTOR_COLUMNS if column not in factors.columns]
    if missing:
        errors.append(f"missing required columns: {missing}")
        return errors

    if factors.empty:
        errors.append("factor frame is empty")
        return errors

    key_cols = ["trade_date", "ts_code", "factor_id"]
    duplicates = factors.duplicated(key_cols).sum()
    if duplicates:
        errors.append(f"duplicated primary keys: {duplicates}")

    score = pd.to_numeric(factors["score"], errors="coerce")
    if score.isna().any() or not score.between(0, 100).all():
        errors.append("score must be numeric and between 0 and 100")

    confidence = pd.to_numeric(factors["confidence"], errors="coerce")
    if confidence.isna().any() or not confidence.between(0, 1).all():
        errors.append("confidence must be numeric and between 0 and 1")

    allowed_signals = {"buy", "sell", "hold", 1, 0, -1, "1", "0", "-1"}
    bad_signals = sorted(set(factors["signal"].dropna().tolist()) - allowed_signals)
    if bad_signals:
        errors.append(f"signal contains unsupported values: {bad_signals}")

    required_non_null = ["trade_date", "asset_type", "ts_code", "factor_id", "factor_name", "factor_value", "data_version", "update_time"]
    null_columns = [column for column in required_non_null if factors[column].isna().any()]
    if null_columns:
        errors.append(f"required columns contain nulls: {null_columns}")

    if require_no_forward_label:
        forward_cols = {"next_open", "next_date", "next_open_premium", "future_return"}
        leaked = sorted(forward_cols.intersection(factors.columns))
        if leaked:
            errors.append(f"production factor output contains forward-looking columns: {leaked}")

    return errors


def compute_backtest_metrics(
    factors_with_labels: pd.DataFrame,
    group_count: int = 5,
    score_col: str = "score",
    label_col: str = "next_open_premium",
    one_way_cost_bps: float = 0.0,
    one_way_slippage_bps: float = 0.0,
) -> tuple[dict[str, float | int | str | None], pd.DataFrame, pd.DataFrame]:
    frame = _select_metric_columns(factors_with_labels, score_col, label_col)
    frame = frame.dropna(subset=["trade_date", "ts_code", "_metric_score", "_metric_label"])
    if len(frame) == 0:
        empty = pd.DataFrame()
        return {"sample_count": 0}, empty, empty

    ic_rows = []
    group_rows = []
    top_sets: list[set[str]] = []
    for date, day in frame.groupby("trade_date"):
        day = day.sort_values("_metric_score", ascending=False)
        if (
            len(day) >= 3
            and day["_metric_score"].nunique(dropna=True) > 1
            and day["_metric_label"].nunique(dropna=True) > 1
        ):
            ic = day["_metric_score"].corr(day["_metric_label"], method="pearson")
            rank_ic = _rank_correlation(day["_metric_score"], day["_metric_label"])
            ic_rows.append({"trade_date": date, "ic": ic, "rank_ic": rank_ic, "n": len(day)})

        ranks = day["_metric_score"].rank(method="first", ascending=False)
        buckets = np.ceil(ranks / max(len(day), 1) * group_count).astype(int).clip(1, group_count)
        day = day.assign(group=buckets)
        top_sets.append(set(day.loc[day["group"].eq(1), "ts_code"].tolist()))
        for group, group_frame in day.groupby("group"):
            group_rows.append(
                {
                    "trade_date": date,
                    "group": int(group),
                    "mean_next_open_premium": float(group_frame["_metric_label"].mean()),
                    "count": int(len(group_frame)),
                }
            )

    ic_frame = pd.DataFrame(ic_rows)
    group_frame = pd.DataFrame(group_rows)

    if len(group_frame) > 0:
        pivot = group_frame.pivot(index="trade_date", columns="group", values="mean_next_open_premium")
        top = pivot.get(1, pd.Series(dtype=float))
        bottom = pivot.get(group_count, pd.Series(dtype=float))
        long_short = (top - bottom).dropna()
    else:
        top = pd.Series(dtype=float)
        bottom = pd.Series(dtype=float)
        long_short = pd.Series(dtype=float)

    def _mean(series: pd.Series) -> float | None:
        return float(series.mean()) if len(series) else None

    def _std(series: pd.Series) -> float | None:
        return float(series.std(ddof=1)) if len(series) > 1 else None

    def _win_rate(series: pd.Series) -> float | None:
        series = series.dropna()
        return float((series > 0).mean()) if len(series) else None

    def _cumulative_return(series: pd.Series) -> float | None:
        series = series.dropna()
        return float((1.0 + series).prod() - 1.0) if len(series) else None

    def _max_drawdown(series: pd.Series) -> float | None:
        series = series.dropna()
        if len(series) == 0:
            return None
        curve = (1.0 + series).cumprod()
        drawdown = curve / curve.cummax() - 1.0
        return float(drawdown.min())

    def _annualized_return(series: pd.Series) -> float | None:
        series = series.dropna()
        if len(series) == 0:
            return None
        return float((1.0 + series.mean()) ** 252 - 1.0)

    def _annualized_volatility(series: pd.Series) -> float | None:
        std = _std(series.dropna())
        return float(std * math.sqrt(252)) if std is not None else None

    def _sharpe(series: pd.Series) -> float | None:
        series = series.dropna()
        std = _std(series)
        if std is None or std <= 0:
            return None
        return float(series.mean() / std * math.sqrt(252))

    ic_mean = _mean(ic_frame["ic"]) if "ic" in ic_frame else None
    rank_ic_mean = _mean(ic_frame["rank_ic"]) if "rank_ic" in ic_frame else None
    ic_std = _std(ic_frame["ic"]) if "ic" in ic_frame else None
    rank_ic_std = _std(ic_frame["rank_ic"]) if "rank_ic" in ic_frame else None
    icir = (ic_mean / ic_std * math.sqrt(252)) if ic_mean is not None and ic_std and ic_std > 0 else None
    rank_icir = (
        rank_ic_mean / rank_ic_std * math.sqrt(252)
        if rank_ic_mean is not None and rank_ic_std and rank_ic_std > 0
        else None
    )

    one_way_cost = max(float(one_way_cost_bps or 0.0), 0.0) / 10000.0
    one_way_slippage = max(float(one_way_slippage_bps or 0.0), 0.0) / 10000.0
    round_trip_cost = 2.0 * (one_way_cost + one_way_slippage)
    long_short_round_trip_cost = 2.0 * round_trip_cost
    top_net = top - round_trip_cost
    bottom_net = bottom - round_trip_cost
    long_short_net = long_short - long_short_round_trip_cost
    max_drawdown = _max_drawdown(long_short)
    long_short_mean = float(long_short.mean()) if len(long_short) else None

    turnovers = []
    for prev, cur in zip(top_sets, top_sets[1:]):
        if not prev:
            continue
        turnovers.append(1.0 - len(prev.intersection(cur)) / len(prev))
    turnover = float(np.mean(turnovers)) if turnovers else None

    summary: dict[str, float | int | str | None] = {
        "score_column": score_col,
        "label_column": label_col,
        "one_way_cost_bps": float(one_way_cost_bps or 0.0),
        "one_way_slippage_bps": float(one_way_slippage_bps or 0.0),
        "round_trip_cost": float(round_trip_cost),
        "long_short_round_trip_cost": float(long_short_round_trip_cost),
        "sample_count": int(len(frame)),
        "date_count": int(frame["trade_date"].nunique()),
        "ic_mean": ic_mean,
        "rank_ic_mean": rank_ic_mean,
        "icir": icir,
        "rank_icir": rank_icir,
        "top_group_mean_next_open_premium": _mean(group_frame[group_frame["group"].eq(1)]["mean_next_open_premium"]) if len(group_frame) else None,
        "bottom_group_mean_next_open_premium": _mean(group_frame[group_frame["group"].eq(group_count)]["mean_next_open_premium"]) if len(group_frame) else None,
        "long_short_mean_next_open_premium": long_short_mean,
        "top_group_mean_next_open_premium_net": _mean(top_net),
        "bottom_group_mean_next_open_premium_net": _mean(bottom_net),
        "long_short_mean_next_open_premium_net": _mean(long_short_net),
        "top_group_cumulative_return": _cumulative_return(top),
        "bottom_group_cumulative_return": _cumulative_return(bottom),
        "long_short_cumulative_return": _cumulative_return(long_short),
        "top_group_cumulative_return_net": _cumulative_return(top_net),
        "bottom_group_cumulative_return_net": _cumulative_return(bottom_net),
        "long_short_cumulative_return_net": _cumulative_return(long_short_net),
        "top_group_annualized_return": _annualized_return(top),
        "bottom_group_annualized_return": _annualized_return(bottom),
        "long_short_annualized_return": _annualized_return(long_short),
        "top_group_annualized_return_net": _annualized_return(top_net),
        "bottom_group_annualized_return_net": _annualized_return(bottom_net),
        "long_short_annualized_return_net": _annualized_return(long_short_net),
        "top_group_annualized_volatility": _annualized_volatility(top),
        "long_short_annualized_volatility": _annualized_volatility(long_short),
        "top_group_sharpe": _sharpe(top),
        "long_short_sharpe": _sharpe(long_short),
        "top_group_sharpe_net": _sharpe(top_net),
        "long_short_sharpe_net": _sharpe(long_short_net),
        "top_group_win_rate": _win_rate(top),
        "long_short_win_rate": _win_rate(long_short),
        "top_group_win_rate_net": _win_rate(top_net),
        "long_short_win_rate_net": _win_rate(long_short_net),
        "max_drawdown": max_drawdown,
        "max_drawdown_net": _max_drawdown(long_short_net),
        "turnover": turnover,
    }
    return summary, ic_frame, group_frame


def make_sample_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Small deterministic sample used for smoke tests only."""
    dates = [
        "20250102",
        "20250103",
        "20250106",
        "20250107",
        "20250108",
        "20250109",
        "20250110",
        "20250113",
        "20250114",
        "20250115",
    ]
    symbols = ["000001.SZ", "000002.SZ", "000003.SZ"]
    close_map = {
        "000001.SZ": [10.0, 10.5, 10.7, 11.0, 11.2, 11.8, 12.0, 12.5, 12.7, 13.0],
        "000002.SZ": [20.0, 19.4, 19.1, 18.8, 18.5, 18.2, 18.0, 17.8, 17.5, 17.3],
        "000003.SZ": [30.0, 30.1, 29.9, 30.2, 30.0, 30.4, 30.2, 30.5, 30.3, 30.7],
    }
    price_rows = []
    for symbol in symbols:
        for idx, date in enumerate(dates):
            close = close_map[symbol][idx]
            open_price = close * (0.995 if idx % 2 else 1.005)
            price_rows.append(
                {
                    "symbol": symbol,
                    "date": date,
                    "open": open_price,
                    "close": close,
                    "pre_close": close_map[symbol][idx - 1] if idx > 0 else close,
                    "high": close * 1.03,
                    "low": close * 0.97,
                    "volume": 1_000_000 + idx * 1000,
                    "amount": close * (1_000_000 + idx * 1000),
                    "trade_status": 0,
                }
            )
    stock_daily = pd.DataFrame(price_rows)

    event_rows = []
    detail_rows = []
    schedule = []
    for idx, date in enumerate(dates[:-1]):
        schedule.extend(
            [
                (date, "000001.SZ", "Alpha Hot Seat", 80_000_000 + idx * 5_000_000),
                (date, "000002.SZ", "Beta Weak Seat", 70_000_000 + idx * 3_000_000),
                (date, "000003.SZ", "Gamma Mixed Seat", 65_000_000 + idx * 2_000_000),
            ]
        )
    for date, symbol, agency, buy_value in schedule:
        event_rows.append(
            {
                "symbol": symbol,
                "date": date,
                "type": "G0007",
                "reason": "sample LHB reason",
                "amount": buy_value * 3,
                "volume": 1_000_000,
                "turnover": 0.25,
            }
        )
        detail_rows.append(
            {
                "symbol": symbol,
                "date": date,
                "type": "G0007",
                "side": "buy",
                "rank": 1,
                "agency": agency,
                "b_value": buy_value,
                "s_value": buy_value * 0.05,
                "reason": "sample LHB reason",
            }
        )
    trade_cal = pd.DataFrame({"nature_date": dates, "is_trade": 1, "exchange": "SH"})
    return pd.DataFrame(event_rows), pd.DataFrame(detail_rows), stock_daily, trade_cal
