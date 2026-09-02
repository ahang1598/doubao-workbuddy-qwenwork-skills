#!/usr/bin/env python3
"""Machine-readable PandaAI native operator catalog and expression helpers."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Operator:
    name: str
    category: str
    args: str
    stage: int
    aliases: tuple[str, ...] = ()
    risk: str = "normal"


OPERATORS = (
    Operator("ABS", "direct", "X", 1), Operator("LOG", "direct", "X", 1),
    Operator("LOGABS", "direct", "X", 1), Operator("AS_FLOAT", "direct", "X", 1),
    Operator("SIGN", "direct", "X", 1), Operator("POWER", "direct", "X,N", 1),
    Operator("SIGNEDPOWER", "direct", "X,N", 1),
    Operator("MAX", "direct", "A,B", 1), Operator("MIN", "direct", "A,B", 1),
    Operator("MEAN", "direct", "A,B", 1), Operator("IF", "conditional", "X,A,B", 1),
    Operator("REF", "time_series", "X,N", 2, ("DELAY",)),
    Operator("DELTA", "time_series", "X,N", 2, ("DIFF",)),
    Operator("TS_MEAN", "time_series", "X,N", 2, ("MA",)),
    Operator("SUM", "time_series", "X,N", 2),
    Operator("PRODUCT", "time_series", "X,N", 2),
    Operator("RETURNS", "time_series", "X,N", 1, ("ROC", "PCT_CHANGE")),
    Operator("STDDEV", "time_series", "X,N", 2, ("STD",)),
    Operator("VAR", "time_series", "X,N", 2),
    Operator("TS_MAX", "time_series", "X,N", 2, ("HHV",)),
    Operator("TS_MIN", "time_series", "X,N", 2, ("LLV",)),
    Operator("TS_MIDDLE", "time_series", "X,N", 2),
    Operator("TS_MAD", "time_series", "X,N", 2, ("AVEDEV",)),
    Operator("TS_RANK", "time_series", "X,N", 2),
    Operator("TS_ARGMAX", "time_series", "X,N", 2, ("HHVBARS",)),
    Operator("TS_ARGMIN", "time_series", "X,N", 2, ("LLVBARS",)),
    Operator("COUNT", "time_series", "X,N", 2),
    Operator("EVERY", "time_series", "X,N", 2),
    Operator("EXIST", "time_series", "X,N", 2),
    Operator("SLOPE", "time_series", "X,N", 2),
    Operator("ANGLE", "time_series", "X,N", 2),
    Operator("INTERCEPT", "time_series", "X,N", 2),
    Operator("FORCAST", "time_series", "X,N", 2),
    Operator("DECAYLINEAR", "time_series", "X,N", 2),
    Operator("TS_ZSCORE", "time_series", "X,N", 2),
    Operator("TS_SKEW", "time_series", "X,N", 2),
    Operator("TS_KURT", "time_series", "X,N", 2),
    Operator("TS_MEDIAN", "time_series", "X,N", 2),
    Operator("EMA", "time_series", "X,N", 2),
    Operator("WMA", "time_series", "X,N", 2),
    Operator("CORRELATION", "time_series_pair", "A,B,N", 2, ("CORR",)),
    Operator("COVARIANCE", "time_series_pair", "A,B,N", 2, ("COV",)),
    Operator("TS_REGRESSION", "time_series_pair", "A,B,N", 2),
    Operator("SUMIF", "time_series_pair", "A,B,N", 2),
    Operator("RANK", "cross_sectional", "X", 3),
    Operator("SCALE", "cross_sectional", "X", 3),
    Operator("ZSCORE", "cross_sectional", "X", 3),
    Operator("FUTURE_RETURNS", "forward_looking", "X,N", 99, risk="forbidden"),
)

FIELDS = ("CLOSE", "OPEN", "HIGH", "LOW", "VOLUME", "AMOUNT", "TURNOVER", "MARKET_CAP")
BY_NAME = {name: op for op in OPERATORS for name in (op.name, *op.aliases)}


def wrap(name: str, expression: str, window: int | None = None,
         other: str | None = None) -> str:
    key = name.upper()
    if key not in BY_NAME:
        raise ValueError(f"unknown PandaAI operator: {name}")
    op = BY_NAME[key]
    if op.risk == "forbidden":
        raise ValueError(f"forward-looking operator forbidden in mining: {key}")
    canonical = op.name
    if op.args == "X":
        return f"{canonical}({expression})"
    if op.args == "X,N":
        if window is None:
            raise ValueError(f"{canonical} requires window")
        return f"{canonical}({expression},{window})"
    if op.args == "A,B,N":
        if other is None or window is None:
            raise ValueError(f"{canonical} requires other and window")
        return f"{canonical}({expression},{other},{window})"
    raise ValueError(f"{canonical} requires task-specific arguments: {op.args}")


def validate(expression: str, max_depth: int = 8) -> dict:
    if expression.count("(") != expression.count(")"):
        return {"valid": False, "error": "unbalanced parentheses"}
    depth = peak = 0
    for char in expression:
        depth += char == "("
        peak = max(peak, depth)
        depth -= char == ")"
    if peak > max_depth:
        return {"valid": False, "error": f"nesting depth {peak}>{max_depth}"}
    names = set(re.findall(r"\b([A-Z][A-Z0-9_]*)\s*\(", expression.upper()))
    unknown = sorted(names - set(BY_NAME))
    forbidden = sorted(name for name in names if name in BY_NAME and BY_NAME[name].risk == "forbidden")
    if unknown:
        return {"valid": False, "error": "unknown operators", "operators": unknown}
    if forbidden:
        return {"valid": False, "error": "forward-looking operators", "operators": forbidden}
    return {"valid": True, "depth": peak, "operators": sorted(names)}


def main() -> None:
    parser = argparse.ArgumentParser(description="PandaAI native quant operator catalog")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--validate")
    parser.add_argument("--stage", type=int, choices=(1, 2, 3))
    args = parser.parse_args()
    if args.list:
        rows = [asdict(op) for op in OPERATORS if args.stage is None or op.stage <= args.stage]
        print(json.dumps({"fields": FIELDS, "operators": rows}, ensure_ascii=False, indent=2))
    elif args.validate:
        print(json.dumps(validate(args.validate), ensure_ascii=False, indent=2))
    else:
        parser.error("use --list or --validate")


if __name__ == "__main__":
    main()
