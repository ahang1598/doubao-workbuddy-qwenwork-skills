"""Optional Decimal arithmetic. Schema: references/calculations.md.
Python 3 stdlib, JSON path or '-' for stdin. No network or file writes.
"""
import argparse
import json
import sys
from decimal import Decimal, DecimalException, localcontext
from pathlib import Path

MAX_BYTES = 1024 * 1024


def number(value):
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise ValueError("finite decimal required")
    if len(str(value)) > 256:
        raise ValueError("numeric text too long")
    out = Decimal(str(value))
    if not out.is_finite() or len(out.as_tuple().digits) > 80 or abs(out.adjusted()) > 100:
        raise ValueError("number outside supported range")
    return out


def positive(value):
    out = number(value)
    if out <= 0:
        raise ValueError("positive value required")
    return out


def ratio(a, b):
    return a / b if b > 0 else None


def calculate(v):
    op = v["operation"]
    if op == "ratio":
        result = ratio(number(v["numerator"]), number(v["denominator"]))
        return {"ratio": result, "percent": result * 100 if result is not None else None}
    if op == "growth":
        before, after = number(v["before"]), number(v["after"])
        change = after - before
        result = ratio(change, before)
        return {"absolute_change": change, "growth_percent": result * 100 if result is not None else None}
    if op == "aggregate":
        values = v["values"]
        if not isinstance(values, list) or not values:
            raise ValueError("nonempty values list required")
        if v["metric_kind"] != "additive":
            raise ValueError("additive quantities required")
        values = [number(x) for x in values]
        total = sum(values, Decimal(0))
        return {"sum": total, "mean": total / len(values)}
    if op == "bridge":
        if v["metric_kind"] != "additive":
            raise ValueError("additive quantities required")
        return {"bridged_value": number(v["base"]) - number(v["remove"]) + number(v["add"])}
    if op == "scale":
        return {"converted_value": number(v["value"]) * positive(v["factor"])}
    raise ValueError("unknown operation")


def reject_constant(_):
    raise ValueError("non-standard JSON numeric constant")


def no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def encode(value):
    if isinstance(value, Decimal) and value.is_finite():
        return str(value)
    raise TypeError("unsupported result")


class InputParser(argparse.ArgumentParser):
    def error(self, message):
        print(json.dumps({"error": "invalid_input", "hint": "Supply one JSON path or -; see --help."}))
        raise SystemExit(2)


def cli(fn):
    parser = InputParser(description=__doc__)
    parser.add_argument("input", help="JSON file path or - for stdin")
    args = parser.parse_args()
    try:
        if args.input == "-":
            raw = sys.stdin.buffer.read(MAX_BYTES + 1)
        else:
            with Path(args.input).open("rb") as stream:
                raw = stream.read(MAX_BYTES + 1)
        if not raw or len(raw) > MAX_BYTES:
            raise ValueError("input empty or exceeds 1 MiB")
        v = json.loads(raw.decode("utf-8"), parse_float=Decimal,
                       parse_constant=reject_constant, object_pairs_hook=no_duplicates)
        if not isinstance(v, dict):
            raise ValueError("JSON object required")
        with localcontext() as ctx:
            ctx.prec = 400
            result = fn(v)
        print(json.dumps({**result, "arithmetic_only": True}, ensure_ascii=False,
                         default=encode, allow_nan=False, indent=2))
        return 0
    except (ValueError, KeyError, TypeError, OSError, DecimalException, RecursionError,
            AttributeError, IndexError, OverflowError):
        print(json.dumps({"error": "invalid_input", "hint": "Check fields, ranges, JSON and local file access."}))
        return 2


if __name__ == "__main__":
    sys.exit(cli(calculate))
