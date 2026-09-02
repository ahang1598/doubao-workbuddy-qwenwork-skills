#!/usr/bin/env python3
"""Execute an approved genetic batch and append compact results to JSONL."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandaai_cli_wrapper as cli


ALIASES = {
    "ic_mean": ("ic_mean", "IC_mean"),
    "rank_ic": ("rank_ic", "Rank_IC"),
    "ic_std": ("ic_std", "IC_std"),
    "ic_ir": ("ic_ir", "IC_IR"),
    "ir": ("ir", "IR"),
    "p_neg": ("p_neg", "P(IC<-0.02)"),
    "p_pos": ("p_pos", "P(IC>0.02)"),
    "t_stat": ("t_stat", "t统计量"),
    "monotonicity": ("monotonicity", "单调性"),
    "sharpe": ("sharpe", "sharpe_ratio", "夏普比率"),
    "annual_return": ("annualized_ratio", "annualized_return", "年化收益"),
    "max_drawdown": ("max_drawdown", "最大回撤"),
    "return_ratio": ("return_ratio", "累计收益"),
    "p_value": ("p_value", "p-value"),
}


def walk(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def _to_number(value: Any) -> float | None:
    """Coerce numeric or percentage-string values to float; None if not numeric."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        s = value.strip().rstrip("%").strip()
        try:
            return float(s)
        except ValueError:
            return None
    return None


def extract_metrics(result: dict[str, Any]) -> dict[str, float]:
    metrics: dict[str, float] = {}

    def grab(value: Any, key: str) -> None:
        for target, aliases in ALIASES.items():
            if target in metrics:
                continue
            for alias in aliases:
                if key == alias or key.lower() == alias.lower():
                    number = _to_number(value)
                    if number is not None:
                        metrics[target] = number
                        return

    def walk_nodes(value: Any) -> None:
        # Platform factor_result nests everything under factor_analysis:
        #   query_factor_analysis_data: [{indicator, factor1}, ...]
        #   query_one_group_data: {return_ratio, annualized_ratio, sharpe_ratio, maximum_drawdown}
        #   query_group_return_analysis: [{group, annualizedReturn, ...}]
        if isinstance(value, dict):
            fa = value.get("factor_analysis")
            if isinstance(fa, dict):
                for row in fa.get("query_factor_analysis_data", []) or []:
                    if isinstance(row, dict):
                        indicator = str(row.get("indicator") or "")
                        grab(row.get("factor1"), indicator)
                one = fa.get("query_one_group_data") or {}
                for key, val in one.items():
                    grab(val, key)
            for child in value.values():
                walk_nodes(child)
        elif isinstance(value, list):
            for child in value:
                walk_nodes(child)

    walk_nodes(result)

    # Fallback: legacy indicator/value pairs and direct key lookup.
    for node in walk(result):
        if isinstance(node, dict) and isinstance(node.get("indicator"), str) \
                and "factor_value" in node:
            number = _to_number(node.get("factor_value"))
            if number is not None:
                metrics.setdefault(node["indicator"], number)
            continue
        for target, aliases in ALIASES.items():
            if target in metrics:
                continue
            for alias in aliases:
                value = _to_number(node.get(alias))
                if value is not None:
                    metrics[target] = value
                    break
    return metrics


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run an approved PandaAI genetic batch")
    parser.add_argument("--batch", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--adjustment-cycle", type=int, required=True)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--execute", action="store_true",
                        help="Required safety switch; platform compute is used")
    args = parser.parse_args()
    if not args.execute:
        parser.error("refusing platform execution without --execute")
    if not 1 <= args.adjustment_cycle <= 10:
        parser.error("--adjustment-cycle must be between 1 and 10")
    batch = json.loads(args.batch.read_text(encoding="utf-8"))
    for candidate in batch["population"]:
        record = dict(candidate)
        created = cli.action_create(
            formula=candidate.get("formula"),
            code=candidate.get("code") if not candidate.get("formula") else None,
            name=f"blind-s{candidate['stage']}-g{candidate['generation']}-{candidate['candidate_id']}",
            start_date=args.start_date,
            end_date=args.end_date,
            adjustment_cycle=args.adjustment_cycle,
            factor_direction=candidate["factor_direction"],
        )
        record["create_result"] = created
        factor_id = created.get("factor_id")
        if not created.get("success") or not factor_id:
            record.update(status="create_failed", error=created.get("error"))
            append_jsonl(args.ledger, record)
            continue
        record["factor_id"] = factor_id
        result = cli.action_run(factor_id, timeout=args.timeout)
        record["run_id"] = result.get("factor_run_id")
        record["metrics"] = extract_metrics(result)
        record["billing"] = result.get("billing")
        record["status"] = "completed" if result.get("success") else "run_failed"
        record["error"] = result.get("error")
        append_jsonl(args.ledger, record)


if __name__ == "__main__":
    main()
