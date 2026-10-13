"""Dependency-free guards for supplied JSON, decimal inputs and fund restrictions."""

from decimal import Decimal, InvalidOperation
import json
import os
from pathlib import Path
import stat

MAX_INPUT_BYTES = 8 * 1024 * 1024
MAX_ROWS = 512
MAX_INPUT_NODES = 20000
MAX_WORK_UNITS = 2000000
MAX_ACTIVE_FUNDS = 512
MAX_ACTIVE_PAYMENTS = 512
MAX_MATCH_PAIRS = 50000
PURPOSES = frozenset(("principal", "put", "interest"))


class LocalResourceLimit(ValueError):
    """An unsupported local size/work envelope, never a business result."""


def within(value, limit, location):
    if value > limit:
        raise LocalResourceLimit(f"unsupported_size_or_work: {location} exceeds local limit {limit}")


class Budget:
    def __init__(self, limit, location):
        self.limit, self.location, self.used = limit, location, 0

    def spend(self, amount):
        if type(amount) is not int or amount < 0:
            raise ValueError("work charges must be nonnegative integers")
        within(self.used + amount, self.limit, self.location)
        self.used += amount

    @property
    def remaining(self):
        return self.limit - self.used


def decimal_shape(value, name):
    if not value.is_finite():
        raise ValueError(f"{name}: finite decimal required")
    parts = value.as_tuple()
    within(len(parts.digits), 28, name + " decimal digits")
    within(abs(parts.exponent), 28, name + " decimal exponent")
    return value


def number(value, name, *, positive=False, signed=False):
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise ValueError(f"{name}: explicit finite decimal required")
    if isinstance(value, int):
        within(abs(value), 10**28 - 1, name + " integer magnitude")
    if isinstance(value, str):
        within(len(value), 128, name + " numeric representation")
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f"{name}: invalid decimal") from exc
    decimal_shape(result, name)
    if (not signed and result < 0) or (positive and result <= 0):
        raise ValueError(f"{name}: invalid range")
    return result


def input_shape(data, *, max_bytes=MAX_INPUT_BYTES, max_rows=MAX_ROWS, max_nodes=MAX_INPUT_NODES):
    nodes, strings = Budget(max_nodes, "input nodes"), Budget(max_bytes, "input text")

    def walk(value, depth):
        within(depth, 32, "input nesting")
        nodes.spend(1)
        if isinstance(value, dict):
            within(len(value), max_rows, "object fields")
            for key, item in value.items():
                if not isinstance(key, str):
                    raise ValueError("JSON object keys must be text")
                walk(key, depth + 1)
                walk(item, depth + 1)
        elif isinstance(value, list):
            within(len(value), max_rows, "input rows")
            for item in value:
                walk(item, depth + 1)
        elif isinstance(value, str):
            within(len(value), 65536, "input string")
            strings.spend(len(value.encode("utf-8")))
        elif isinstance(value, bool) or value is None:
            return
        elif isinstance(value, (int, float, Decimal)):
            number(value, "input", signed=True)
        else:
            raise ValueError("unsupported JSON input type")
    walk(data, 0)


def no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        within(len(key), 65536, "JSON key")
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read_json(path, *, max_bytes=MAX_INPUT_BYTES):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("input must be a regular non-symlink JSON file")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    with os.fdopen(fd, "rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("input must remain a regular JSON file")
        within(before.st_size, max_bytes, "input JSON bytes")
        raw = stream.read(max_bytes + 1)
        within(len(raw), max_bytes, "input JSON bytes during read")
        after = os.fstat(stream.fileno())
        if len(raw) != before.st_size or (before.st_size, before.st_mtime_ns) != (
                after.st_size, after.st_mtime_ns):
            raise ValueError("input JSON changed during read")
    depth, quoted, escaped = 0, False, False
    for char in raw:
        if quoted:
            if escaped:
                escaped = False
            elif char == 92:
                escaped = True
            elif char == 34:
                quoted = False
        elif char == 34:
            quoted = True
        elif char in (91, 123):
            depth += 1
            within(depth, 32, "JSON nesting")
        elif char in (93, 125):
            depth -= 1

    def decimal(value):
        within(len(value), 128, "JSON decimal representation")
        return decimal_shape(Decimal(value), "JSON")

    def integer(value):
        within(len(value.lstrip("-")), 28, "JSON integer digits")
        return int(value)

    def invalid(value):
        raise ValueError(f"invalid number: {value}")

    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=no_duplicates,
                          parse_float=decimal, parse_int=integer, parse_constant=invalid)
    except RecursionError as exc:
        raise LocalResourceLimit("unsupported_size_or_work: JSON parser nesting exceeded") from exc


def encode(value, *, max_bytes=MAX_INPUT_BYTES):
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("nonfinite JSON decimal")
        parts = value.as_tuple()
        within(len(parts.digits) + abs(parts.exponent) + 3, max_bytes, "expanded decimal bytes")
        return format(value, "f")
    raise TypeError(type(value).__name__)


def dumps(value, *, max_bytes=MAX_INPUT_BYTES):
    budget, chunks = Budget(max_bytes, "serialized JSON bytes"), []
    encoder = json.JSONEncoder(ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False,
                               default=lambda v: encode(v, max_bytes=max_bytes))
    for chunk in encoder.iterencode(value):
        budget.spend(len(chunk.encode("utf-8")))
        chunks.append(chunk)
    budget.spend(1)
    return "".join(chunks) + "\n"


def string_set(value, location):
    if not isinstance(value, list):
        raise ValueError(f"{location}: explicit string array required")
    within(len(value), MAX_ROWS, location)
    seen = set()
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{location}: nonempty text required")
        within(len(item), 65536, location + " text")
        if item in seen:
            raise ValueError(f"{location}: duplicate entry")
        seen.add(item)
    return seen


def restrictions(row, registered, location):
    kind = row["restriction"]
    if kind not in ("unrestricted", "dedicated", "unknown"):
        raise ValueError(f"{location}.restriction: unsupported restriction")
    debt_ids = string_set(row["debt_ids"], location + ".debt_ids")
    purposes = string_set(row["purposes"], location + ".purposes")
    if purposes - PURPOSES:
        raise ValueError(f"{location}.purposes: use only principal, put, interest")
    if kind == "unrestricted" and (debt_ids or purposes):
        raise ValueError(f"{location}: unrestricted conflicts with restriction lists")
    if kind == "dedicated" and (not debt_ids or not purposes):
        raise ValueError(f"{location}: dedicated funds require both debt and purpose restrictions")
    if debt_ids:
        if registered is None:
            raise ValueError(f"{location}.debt_ids: explicit registered_debt_ids required")
        if debt_ids - registered:
            raise ValueError(f"{location}.debt_ids: references unregistered debt")
