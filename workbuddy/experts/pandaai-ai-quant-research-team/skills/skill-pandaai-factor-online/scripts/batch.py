#!/usr/bin/env python3
"""Create, run, and tabulate a batch of PandaAI factor candidates.

Input is a text file with one candidate per line: `name ~ definition ~ direction`.
Use formula mode for formulas; Python mode treats definition as a `.py` file passed to the CLI.
Blank lines and lines starting with `#` are ignored.

Progress is checkpointed to <input>.state.json after every step, so an interrupted
batch resumes without re-creating or re-running anything -- which matters because every
run costs compute credits. Each entry carries a fingerprint of the formula, direction,
window and cycle it was produced with, so an edited candidate is never resumed as if
nothing had changed.
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import io
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

# The platform sorts the full universe by factor value. With its ten groups, each group is one
# decile and the held portfolio is the direction-selected extreme (top 10% for direction 1,
# bottom 10% for direction 0), equal-weighted and rebalanced synchronously with the factor pool.
# Group labels are ascending, so 分组1 is the bottom decile and 分组10 the top decile.
LOW, HIGH = "分组1", "分组10"

# Two formula traps worth catching before they cost a run. FUTURE_RETURNS reads the answer;
# MEAN(X, 20) averages X with the constant 20 instead of taking a 20-day window, and the
# result looks entirely plausible. See references/pitfalls.md.
LOOKAHEAD = re.compile(r"\bFUTURE_\w+\s*\(", re.I)
CONSTANT_WINDOW = re.compile(r"\bMEAN\s*\(\s*[^,()]+,\s*\d+\s*\)", re.I)


def lint(formula: str) -> str | None:
    if LOOKAHEAD.search(formula):
        return "uses a future function, so its backtest cannot mean anything"
    if CONSTANT_WINDOW.search(formula):
        return "MEAN(X, N) averages X with the constant N; use MA or TS_MEAN for a rolling window"
    return None


def cli(*args: str, timeout: int = 1800) -> dict:
    """Run pandaai-cli in JSON mode and return the parsed payload."""
    proc = subprocess.run(
        ["pandaai-cli", "--json", *args], capture_output=True, text=True, timeout=timeout
    )
    try:
        return json.loads(proc.stdout)
    except ValueError:
        return {"success": False, "error": {"message": (proc.stdout + proc.stderr).strip()[:300]}}


def lint_python(path: Path) -> str | None:
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except (OSError, UnicodeError, SyntaxError) as exc:
        return f"cannot load Python factor: {exc}"
    factors = [node for node in tree.body if isinstance(node, ast.ClassDef)
               and any(isinstance(base, ast.Name) and base.id == "Factor" for base in node.bases)]
    if len(factors) != 1:
        return "Python factor must define exactly one class that directly inherits Factor"
    methods = [node for node in factors[0].body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
               and node.name == "calculate"]
    if len(methods) != 1 or isinstance(methods[0], ast.AsyncFunctionDef):
        return "Factor subclass must define one synchronous calculate(self, factors) method"
    if len(methods[0].args.args) < 2:
        return "calculate must accept self and factors"
    return None


def parse_candidates(path: Path, mode: str = "formula") -> list[dict]:
    out, seen = [], {}
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("~")]
        if len(parts) != 3:
            sys.exit(f"{path}:{lineno}: expected `name ~ formula ~ direction`, got {len(parts)} fields")
        name, definition, direction = parts
        if direction not in ("0", "1"):
            sys.exit(f"{path}:{lineno}: direction must be 0 or 1, got {direction!r}")
        # Names key the state file, so duplicates would have two formulas share one result.
        if name in seen:
            sys.exit(f"{path}:{lineno}: candidate name {name!r} already used on line {seen[name]}")
        if mode == "formula":
            if (problem := lint(definition)) is not None:
                sys.exit(f"{path}:{lineno}: {name}: {problem}")
            candidate = {"name": name, "formula": definition, "direction": direction,
                         "mode": mode, "content": definition}
        else:
            source_path = (path.parent / definition).resolve()
            if source_path.suffix.lower() != ".py":
                sys.exit(f"{path}:{lineno}: {name}: Python candidates must reference a .py file")
            if (problem := lint_python(source_path)) is not None:
                sys.exit(f"{path}:{lineno}: {name}: {problem}")
            candidate = {"name": name, "file": str(source_path), "direction": direction,
                         "mode": mode, "content": source_path.read_text(encoding="utf-8")}
        seen[name] = lineno
        out.append(candidate)
    return out


def fingerprint(cand: dict, args) -> str:
    """Everything that changes what a run means. Trading cost is absent on purpose: it is
    applied locally at report time, so changing it never needs another run."""
    mode = cand.get("mode", "formula")
    content = cand.get("content", cand.get("formula", ""))
    spec = json.dumps([mode, content, cand["direction"], args.start, args.end,
                       args.cycle, args.group_number],
                      ensure_ascii=False)
    return hashlib.sha256(spec.encode("utf-8")).hexdigest()[:16]


def save(path: Path, state: dict) -> None:
    """Write through a temporary file, so an interrupt cannot truncate the whole batch."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)


def save_text(path: Path, text: str) -> None:
    """Atomically write a user-facing UTF-8 report."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="")
    os.replace(tmp, path)


def pct(text) -> float:
    """'12.34%' -> 12.34, tolerating missing values."""
    try:
        return float(str(text).rstrip("%"))
    except (TypeError, ValueError):
        return float("nan")


def extract(payload: dict, direction: str, group_number: int | None = None) -> dict:
    """Pull the metrics worth comparing out of a factor_run payload.

    Raises ValueError rather than returning NaN: a candidate missing its long side has not
    produced a weak result, it has produced no result, and ranking it would be a fiction.
    """
    # `factor_run` nests analysis under results; `factor_result` returns it at the top level.
    analysis = payload.get("factor_analysis") or (payload.get("results") or {}).get("factor_analysis") or {}
    # CLI 0.1.3 calls the value `factor_value`; older payloads and some workflow nodes use
    # `factor1`. Accept both so a successful run cannot silently lose its IC metrics.
    indicators = {r["indicator"]: r.get("factor1", r.get("factor_value"))
                  for r in analysis.get("query_factor_analysis_data", [])}
    groups = {r["group"]: r for r in analysis.get("query_group_return_analysis", [])}

    labels = [r["group"] for r in analysis.get("query_group_return_analysis", [])
              if re.fullmatch(r"分组\d+", str(r.get("group", "")))]
    if len(labels) < 2:
        raise ValueError("fewer than two group rows returned")
    if group_number is None:
        # Direct callers may provide a compact fixture or a partial payload; batch.py passes
        # the requested count explicitly and therefore validates the complete set.
        group_number = len(labels)
    expected = {f"分组{i}" for i in range(1, group_number + 1)}
    available = expected.intersection(groups)
    if len(available) != group_number and group_number != len(labels):
        raise ValueError(f"expected {group_number} group rows, found {len(available)}")
    numeric_labels = sorted((int(label[2:]), label) for label in labels)
    low_name = numeric_labels[0][1] if numeric_labels else "分组1"
    high_name = numeric_labels[-1][1] if numeric_labels else f"分组{group_number}"
    long_name = high_name if direction == "1" else low_name
    short_name = low_name if direction == "1" else high_name
    if long_name not in groups:
        raise ValueError(f"no {long_name} row in the group returns")
    turnover = pct(groups[long_name].get("turnoverRate"))
    excess = pct(groups[long_name].get("excessAnnualized"))
    if not (math.isfinite(turnover) and math.isfinite(excess)):
        raise ValueError(f"{long_name} returned no usable excess return or turnover")
    return {
        "ic_mean": indicators.get("IC_mean"),
        "rank_ic": indicators.get("Rank_IC"),
        "ic_ir": indicators.get("IC_IR"),
        # The platform's p-value belongs to the IC_mean t-statistic, not to Rank_IC.
        "ic_p_value": indicators.get("p-value"),
        "monotonicity": indicators.get("单调性"),
        "long_excess": excess,
        "short_excess": pct(groups.get(short_name, {}).get("excessAnnualized")),
        "turnover": turnover,
        # Held-side diagnostics are useful for one-factor review, but do not reproduce
        # the competition's standardized, equal-weighted pool-level C score.
        "long_sharpe": pct(groups[long_name].get("sharpeRatio")),
        "long_max_drawdown": pct(groups[long_name].get("maxDrawdown")),
        "long_monthly_win_rate": pct(groups[long_name].get("monthlyWinRate")),
    }


def cost_of(metrics: dict, cycle: int, one_way: float) -> float:
    """Annualise one-way cost on both sells and buys for the replaced portfolio slice."""
    return metrics["turnover"] * (2.0 * one_way) * (252.0 / cycle)


def report(state: dict, candidates: list[dict], cycle: int, round_trip: float,
           hypotheses: int, group_number: int = 10) -> None:
    header = (f"{'name':<28} {'IC_mean':>8} {'Rank_IC':>8} {'IC_p':>7} {'mono':>6} "
              f"{'long%':>8} {'turn%':>7} {'cost%':>7} {'net%':>8}")
    print("\n" + header)
    print("-" * len(header))
    rows = []
    for cand in candidates:
        metrics = state.get(cand["name"], {}).get("metrics")
        if metrics:
            cost = cost_of(metrics, cycle, round_trip)
            rows.append((cand["name"], metrics, cost, metrics["long_excess"] - cost))
    for name, m, cost, net in sorted(rows, key=lambda r: -r[3]):
        print(f"{name[:28]:<28} {str(m.get('ic_mean')):>8} {str(m['rank_ic']):>8} "
              f"{str(m.get('ic_p_value')):>7} {str(m['monotonicity']):>6} {m['long_excess']:>8.2f} "
              f"{m['turnover']:>7.2f} {cost:>7.2f} {net:>8.2f}")
    print(f"\nlong% is the excess return of the direction-selected, equal-weighted extreme 1/{group_number}; "
          f"net% subtracts annual turnover cost at {round_trip:.2%} one-way (buy and sell are counted separately).")
    print("IC_p is the p-value of the IC_mean t-statistic. Rank_IC has no p-value of its own.")

    failed = [c["name"] for c in candidates if state.get(c["name"], {}).get("error")]
    if failed:
        print(f"\nfailed ({len(failed)}, not retried unless you pass --retry-failed):")
        for name in failed:
            print(f"  {name}: {state[name]['error'][:120]}")
    threshold = 0.05 / max(hypotheses, 1)
    scope = "in this file" if hypotheses == len(candidates) else "in this study"
    print(f"\ntested {hypotheses} candidate{'s' if hypotheses != 1 else ''} {scope}"
          f" -> multiple-testing threshold p < {threshold:.4f}")
    if hypotheses == len(candidates):
        print("Pass --hypotheses with the running total once a study spans several files,"
              " or this threshold resets every batch.")


REPORT_COLUMNS = (
    "name", "direction", "status", "factor_id", "run_id", "rank_ic", "ic_mean", "ic_ir",
    "ic_p_value", "monotonicity", "long_excess_pct", "turnover_pct", "annual_cost_pct",
    "net_excess_pct", "long_sharpe", "long_max_drawdown_pct", "long_monthly_win_rate_pct",
    "raw_result", "error",
)


def report_rows(state: dict, candidates: list[dict], cycle: int, one_way: float) -> list[dict]:
    """Turn durable batch state into flat report rows without calling the CLI."""
    rows = []
    for cand in candidates:
        entry = state.get(cand["name"], {})
        metrics = entry.get("metrics")
        row = {
            "name": cand["name"], "direction": cand["direction"],
            "status": "completed" if metrics else ("failed" if entry.get("error") else "pending"),
            "factor_id": entry.get("factor_id", ""), "run_id": entry.get("run_id", ""),
            "raw_result": entry.get("raw_result", ""), "error": entry.get("error", ""),
        }
        if metrics:
            cost = cost_of(metrics, cycle, one_way)
            row.update({
                "rank_ic": metrics.get("rank_ic"), "ic_mean": metrics.get("ic_mean"),
                "ic_ir": metrics.get("ic_ir"), "ic_p_value": metrics.get("ic_p_value"),
                "monotonicity": metrics.get("monotonicity"),
                "long_excess_pct": metrics.get("long_excess"), "turnover_pct": metrics.get("turnover"),
                "annual_cost_pct": cost, "net_excess_pct": metrics["long_excess"] - cost,
                "long_sharpe": metrics.get("long_sharpe"),
                "long_max_drawdown_pct": metrics.get("long_max_drawdown"),
                "long_monthly_win_rate_pct": metrics.get("long_monthly_win_rate"),
            })
        rows.append({column: row.get(column, "") for column in REPORT_COLUMNS})
    return rows


def markdown_value(column: str, value: object) -> str:
    if value in (None, ""):
        return "-"
    if column.endswith("_pct"):
        return f"{float(value):.2f}%"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value).replace("|", "\\|").replace("\n", " ")


def write_reports(input_file: Path, state: dict, candidates: list[dict], cycle: int,
                  one_way: float, hypotheses: int, group_number: int) -> tuple[Path, Path]:
    """Write reusable Markdown and CSV research views beside a candidate manifest."""
    rows = report_rows(state, candidates, cycle, one_way)
    csv_path = input_file.with_name(f"{input_file.stem}.report.csv")
    csv_buffer = io.StringIO(newline="")
    writer = csv.DictWriter(csv_buffer, fieldnames=REPORT_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    save_text(csv_path, csv_buffer.getvalue())

    md_path = input_file.with_name(f"{input_file.stem}.report.md")
    completed = sum(row["status"] == "completed" for row in rows)
    failed = sum(row["status"] == "failed" for row in rows)
    selected = [row for row in rows if row["status"] == "completed"]
    selected.sort(key=lambda row: float(row["net_excess_pct"]), reverse=True)
    columns = ("name", "direction", "rank_ic", "ic_ir", "long_excess_pct", "turnover_pct",
               "annual_cost_pct", "net_excess_pct", "long_sharpe", "long_max_drawdown_pct",
               "long_monthly_win_rate_pct")
    lines = [
        "# PandaAI Factor Research Report", "",
        f"- Candidates: {len(rows)}; completed: {completed}; failed: {failed}",
        f"- Settings: {cycle}-day rebalance, {group_number} groups, {one_way:.2%} one-way cost",
        f"- Multiple-testing reference: p < {0.05 / max(hypotheses, 1):.4f}",
        "- `long_sharpe`, drawdown, and monthly win rate are direction-selected single-factor diagnostics, not official pool-level C metrics.",
        "- Full CLI payloads are retained at the `raw_result` paths in the CSV.", "",
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    lines.extend("| " + " | ".join(markdown_value(column, row[column]) for column in columns) + " |"
                 for row in selected)
    if not selected:
        lines.append("| - | - | - | - | - | - | - | - | - | - | - |")
    if failed:
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- `{row['name']}`: {row['error']}" for row in rows if row["status"] == "failed")
    save_text(md_path, "\n".join(lines) + "\n")
    return md_path, csv_path


def cache_result(input_file: Path, candidate_name: str, run_id: object, payload: dict) -> str:
    """Preserve the full paid-run response so later metrics need no second run."""
    raw_dir = input_file.with_name(f"{input_file.stem}.results")
    raw_dir.mkdir(parents=True, exist_ok=True)
    key = str(run_id or candidate_name)
    filename = re.sub(r"[^A-Za-z0-9._-]+", "_", key).strip("._") or "result"
    path = raw_dir / f"{filename}.json"
    save(path, payload)
    return str(path.relative_to(input_file.parent))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("file", type=Path)
    ap.add_argument("--mode", choices=("formula", "python"), default="formula",
                    help="definition type: formula by default, python for .py files")
    ap.add_argument("--start", required=True, help="YYYYMMDD")
    ap.add_argument("--end", required=True, help="YYYYMMDD")
    ap.add_argument("--cycle", type=int, default=5, help="rebalance cycle in days, 1-10")
    ap.add_argument("--group-number", type=int, choices=range(2, 11), default=10,
                    help="return groups, 2-10; default 10 for decile-compatible reporting")
    ap.add_argument("--round-trip", type=float, default=0.003,
                    help="one-way trading cost as a fraction, default 0.3%% for A-shares")
    ap.add_argument("--prefix", default="", help="prepended to every factor name, eases bulk cleanup")
    ap.add_argument("--create-only", action="store_true", help="create factors without spending runs")
    ap.add_argument("--report-only", action="store_true", help="re-print the table from saved state")
    ap.add_argument("--retry-failed", action="store_true",
                    help="run the candidates that failed last time; each retry costs credits again")
    ap.add_argument("--max-runs", type=int, default=0,
                    help="stop after this many runs, whatever remains in the file (0 = no cap)")
    ap.add_argument("--hypotheses", type=int, default=0,
                    help="candidates tested in the whole study so far, for the multiple-testing "
                         "threshold (0 = just this file)")
    args = ap.parse_args()

    candidates = parse_candidates(args.file, args.mode)
    hypotheses = max(args.hypotheses, len(candidates))
    state_path = args.file.with_suffix(args.file.suffix + ".state.json")
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}

    if args.report_only:
        report(state, candidates, args.cycle, args.round_trip, hypotheses, args.group_number)
        md_path, csv_path = write_reports(args.file, state, candidates, args.cycle, args.round_trip,
                                          hypotheses, args.group_number)
        print(f"saved report: {md_path}\nsaved table: {csv_path}")
        return 0

    # Check every fingerprint before spending anything: a stale entry reused as if it were
    # fresh is how an in-sample result ends up reported as out-of-sample.
    stale, unverified = [], []
    for cand in candidates:
        entry = state.get(cand["name"], {})
        if not entry:
            continue
        if saved := entry.get("spec"):
            if saved != fingerprint(cand, args):
                stale.append(cand["name"])
        elif entry.get("metrics"):
            unverified.append(cand["name"])
    if unverified:
        print(f"note: {len(unverified)} saved result(s) predate fingerprinting and cannot be "
              f"checked against\nthe current settings. Delete their entries to re-run them."
              , file=sys.stderr)
    if stale:
        print("These candidates were last run with a different mode, definition, direction, window "
              "or cycle:", file=sys.stderr)
        for name in stale:
            print(f"  {name}", file=sys.stderr)
        print(f"\nReusing their saved results would misreport them. Either restore the old "
              f"settings, or\nstart a separate state file by copying the candidates into a new "
              f"filename.\n(state file: {state_path})", file=sys.stderr)
        return 1

    runs = 0
    for i, cand in enumerate(candidates, 1):
        name = cand["name"]
        entry = state.setdefault(name, {})
        if entry.get("metrics"):
            print(f"[{i}/{len(candidates)}] {name}: done", file=sys.stderr)
            continue
        # A failure already cost a run. Repeating it on the next invocation costs another one,
        # which is not what someone re-running an interrupted batch is asking for.
        if entry.get("error") and not args.retry_failed:
            print(f"[{i}/{len(candidates)}] {name}: failed before, skipping", file=sys.stderr)
            continue
        if args.max_runs and runs >= args.max_runs and not args.create_only:
            print(f"\nstopping at the {args.max_runs}-run cap;"
                  f" re-run to continue from here", file=sys.stderr)
            break
        entry["spec"] = fingerprint(cand, args)

        if not entry.get("factor_id"):
            definition_args = (["--formula", cand["formula"]] if cand["mode"] == "formula"
                               else ["--file", cand["file"]])
            created = cli("factor_create", *definition_args,
                          "--name", args.prefix + name,
                          "--start-date", args.start, "--end-date", args.end,
                          "--adjustment-cycle", str(args.cycle),
                          "--group-number", str(args.group_number),
                          "--factor-direction", cand["direction"])
            if not created.get("success"):
                entry["error"] = f"create: {created.get('error', {}).get('message', created)}"
                save(state_path, state)
                print(f"[{i}/{len(candidates)}] {name}: create failed", file=sys.stderr)
                continue
            entry["factor_id"] = created["factor_id"]
            save(state_path, state)

        if args.create_only:
            print(f"[{i}/{len(candidates)}] {name}: created {entry['factor_id']}", file=sys.stderr)
            continue

        result = cli("factor_run", entry["factor_id"])
        runs += 1
        if result.get("success"):
            entry["run_id"] = result.get("factor_run_id")
            entry["raw_result"] = cache_result(args.file, name, entry["run_id"], result)
            try:
                entry["metrics"] = extract(result, cand["direction"], args.group_number)
                entry.pop("error", None)
                net = entry["metrics"]["long_excess"] - cost_of(entry["metrics"], args.cycle,
                                                                args.round_trip)
                print(f"[{i}/{len(candidates)}] {name}: net {net:+.2f}%", file=sys.stderr)
            except ValueError as exc:
                entry["error"] = f"result: {exc}"
                print(f"[{i}/{len(candidates)}] {name}: unusable result -- {exc}", file=sys.stderr)
        else:
            entry["error"] = f"run: {result.get('error', {}).get('message', result)}"
            print(f"[{i}/{len(candidates)}] {name}: run failed", file=sys.stderr)
        save(state_path, state)

    if not args.create_only:
        report(state, candidates, args.cycle, args.round_trip, hypotheses, args.group_number)
        md_path, csv_path = write_reports(args.file, state, candidates, args.cycle, args.round_trip,
                                          hypotheses, args.group_number)
        print(f"saved report: {md_path}\nsaved table: {csv_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
