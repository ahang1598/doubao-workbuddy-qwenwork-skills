"""Strict, offline, source-bound input handling shared by the workflow."""

from decimal import Decimal, localcontext
import hashlib
import os
from pathlib import Path
import stat

import fixed_income_checks as legacy
import input_guards as guards
from input_guards import Budget, LocalResourceLimit, within

VERSION = "fixed-income-workflow-v1"
ZERO = Decimal(0)
MAX_INPUT_BYTES = guards.MAX_INPUT_BYTES
MAX_ROWS = guards.MAX_ROWS
MAX_INPUT_NODES = guards.MAX_INPUT_NODES
MAX_SOURCE_FILES = 64
MAX_SOURCE_BYTES = 32 * 1024 * 1024
MAX_TOTAL_SOURCE_BYTES = 128 * 1024 * 1024
MAX_WORK_UNITS = guards.MAX_WORK_UNITS


def input_shape(data):
    guards.input_shape(data, max_bytes=MAX_INPUT_BYTES, max_rows=MAX_ROWS, max_nodes=MAX_INPUT_NODES)


def bounded_stream(stream, limit, budget, destination=None):
    hasher, size = hashlib.sha256(), 0
    while True:
        chunk = stream.read(min(1024 * 1024, limit - size + 1, budget.remaining + 1))
        if not chunk:
            return {"sha256": hasher.hexdigest(), "bytes": size}
        within(size + len(chunk), limit, "file bytes")
        budget.spend(len(chunk))
        size += len(chunk)
        hasher.update(chunk)
        if destination is not None:
            destination.write(chunk)


def file_receipt(path, limit, budget, destination=None):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("file must be regular and non-symlink")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    with os.fdopen(fd, "rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("file is no longer regular")
        within(before.st_size, min(limit, budget.remaining), "file bytes before read")
        receipt = bounded_stream(stream, limit, budget, destination)
        after = os.fstat(stream.fileno())
        if (receipt["bytes"] != before.st_size or
                (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns)):
            raise ValueError("file changed during read; partial output is not verified")
    return receipt


def fields(value, required, optional=()):
    legacy.fields(value, set(required) | set(optional), set(required))


def text(value, name="text"):
    return legacy.text(value, name)


def number(value, name="number", positive=False, signed=False):
    return guards.number(value, name, positive=positive, signed=signed)


def integer(value, name, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name}: integer >= {minimum} required")
    return value


def simple_interest(principal, rate, days, basis):
    # Limit repeating quotients here; later allocation/conservation uses a
    # wider context so those finite amounts are added and subtracted exactly.
    with localcontext() as context:
        context.prec = 50
        return principal * rate * Decimal(days) / basis


def boolean(value, name):
    if type(value) is not bool:
        raise ValueError(f"{name}: explicit boolean required")
    return value


def day(value):
    return legacy.day(value)


def rows(value):
    if isinstance(value, list):
        within(len(value), MAX_ROWS, "record count")
    return legacy.unique(value)


def encode(value):
    return guards.encode(value, max_bytes=MAX_INPUT_BYTES)


def dumps(value):
    return guards.dumps(value, max_bytes=MAX_INPUT_BYTES)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def no_duplicates(pairs):
    return guards.no_duplicates(pairs)


def read_json(path):
    return guards.read_json(path, max_bytes=MAX_INPUT_BYTES)


def private_file(path):
    """Create, never replace, an owner-only output file."""
    if os.name != "posix":
        raise ValueError("private output requires POSIX permissions; use authorized host handling")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        os.fchmod(fd, 0o600)
        return os.fdopen(fd, "wb")
    except BaseException:
        os.close(fd)
        raise


def directory_path(path):
    """Check lexical ancestors before resolving an output directory."""
    path = Path(path).absolute()
    if ".." in path.parts:
        raise ValueError("directory path must not contain parent traversal")
    for parent in reversed((path, *path.parents)):
        if parent.is_symlink():
            raise ValueError("directory path must have no symlink components")
        if parent.exists() and not parent.is_dir():
            raise ValueError("directory path contains a non-directory component")
    return path


def private_directory(path, exist_ok=False):
    path = directory_path(path)
    if os.name != "posix" or path.is_symlink():
        raise ValueError("private directory requires POSIX permissions and no symlink")
    if path.exists():
        if not exist_ok or not path.is_dir():
            raise ValueError("output directory already exists; never overwrite a prior run")
        return
    private_directory(path.parent, exist_ok=True)
    path.mkdir(mode=0o700)


def check_private(path):
    path = Path(path)
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode):
        raise ValueError("symlink in private output")
    expected = 0o700 if stat.S_ISDIR(info.st_mode) else 0o600
    if (not (stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode))
            or stat.S_IMODE(info.st_mode) != expected):
        raise ValueError("output permissions must remain private (directories 0700, files 0600)")


class Context:
    def __init__(self, data, source_root):
        input_shape(data)
        self.work = Budget(MAX_WORK_UNITS, "calculation work")
        fields(data, {"version", "as_of", "cutoff", "meta", "sources", "evidence",
                      "debt_analysis", "cash_analysis"}, {"report_metadata"})
        if data["version"] != VERSION or data["cutoff"] != "end_of_day":
            raise ValueError("v1 requires an explicit end_of_day date cutoff; no intraday inference")
        self.as_of = data["as_of"]
        day(self.as_of)
        self.meta = legacy.metadata(data["meta"])
        self.sources, self.evidence, self.used = {}, rows(data["evidence"]), set()
        lexical_root = Path(source_root).absolute()
        if ".." in lexical_root.parts:
            raise ValueError("source root must not contain parent traversal")
        if any(p.is_symlink() for p in (lexical_root, *lexical_root.parents)):
            raise ValueError("source root must have no symlink components")
        if not lexical_root.is_dir():
            raise ValueError("source root must be a directory")
        root = lexical_root.resolve(strict=True)
        sources, source_paths = rows(data["sources"]), set()
        within(len(sources), MAX_SOURCE_FILES, "source count")
        if not sources or not self.evidence:
            raise ValueError("at least one source and evidence record required; bind the supplied task if self-contained")
        pending, total = [], 0
        for key, row in sources.items():
            fields(row, {"id", "path", "sha256"})
            relative = Path(text(row["path"], "source path"))
            within(len(relative.parts), 16, "source path depth")
            within(len(str(relative).encode("utf-8")), 1024, "source path bytes")
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("sources must use relative paths inside --source-root")
            if relative in source_paths:
                raise ValueError("duplicate source path; reuse its source id with distinct evidence locators")
            source_paths.add(relative)
            path = root / relative
            if any(p.is_symlink() for p in (path, *path.parents)) or not path.is_file():
                raise ValueError("source must be a regular file without symlink components")
            if not path.resolve().is_relative_to(root):
                raise ValueError("source escaped the permitted root")
            size = path.stat().st_size
            within(size, MAX_SOURCE_BYTES, "source bytes")
            total += size
            within(total, MAX_TOTAL_SOURCE_BYTES, "total source bytes")
            pending.append((key, row, path, size))
        budget = Budget(MAX_TOTAL_SOURCE_BYTES, "total source bytes")
        for key, row, path, size in pending:
            receipt = file_receipt(path, MAX_SOURCE_BYTES, budget)
            if receipt["sha256"] != row["sha256"] or receipt["bytes"] != size:
                raise ValueError(f"source hash mismatch: {key}")
            self.sources[key] = {**row, "resolved_path": str(path), "bytes": receipt["bytes"]}
        for key, row in self.evidence.items():
            fields(row, {"id", "source_id", "locator", "known_at", "effective_at",
                         "status", "kind", "note"})
            if row["source_id"] not in self.sources:
                raise ValueError(f"unknown source for evidence: {key}")
            text(row["locator"], "source locator")
            if row["kind"] not in ("fact", "assumption"):
                raise ValueError("evidence kind must be fact or assumption")
            if row["kind"] == "assumption":
                text(row["note"], "assumption explanation")
            for field in ("known_at", "effective_at"):
                if row[field] is not None:
                    legacy.instant(row[field])
            self.proof(key)
        self.used.clear()
        supplied = data.get("report_metadata", {})
        fields(supplied, set(), {"business_timezone", "material_classification"})
        self.report_metadata = {}
        for field in ("business_timezone", "material_classification"):
            entry = supplied.get(field, {"value": None, "evidence_id": None})
            fields(entry, {"value", "evidence_id"})
            value, key = entry["value"], entry["evidence_id"]
            if value is not None:
                text(value, "report_metadata/" + field)
            reason = "missing_evidence_id" if key is None else self.proof(key)[1]
            self.report_metadata[field] = {
                "value": value if reason == "eligible" else None, "supplied_value": value,
                "evidence_id": key, "evidence_status": reason,
                "status": "confirmed" if value is not None and reason == "eligible" else "unknown",
            }

    def meta_check(self, value):
        if legacy.metadata(value) != self.meta:
            raise ValueError("scope/currency/unit mismatch; normalize with explicit source evidence first")

    def proof_details(self, key, allow_assumption=False):
        text(key, "evidence id")
        if key not in self.evidence:
            raise ValueError(f"unregistered evidence id: {key}")
        self.used.add(key)
        row = self.evidence[key]
        old = {"source": f"{row['source_id']}:{row['locator']}", "known_at": row["known_at"],
               "effective_at": row["effective_at"], "status": row["status"]}
        reasons = legacy.evidence_reasons(old, self.as_of)
        if row["kind"] == "assumption" and not allow_assumption:
            reasons.append("assumption_not_confirmed_fact")
        return old, legacy.admission(reasons)

    def proof(self, key, allow_assumption=False):
        old, state = self.proof_details(key, allow_assumption)
        return old, state["evidence_status"]

    def eligible(self, key, allow_assumption=False):
        return self.proof(key, allow_assumption)[1] == "eligible"

    def aggregate_proof(self, key):
        if key is None:
            return None
        proof, _ = self.proof(key)
        return {**proof, "kind": self.evidence[key]["kind"]}

    def fact_reason(self, key, location, unknowns):
        reasons = (["missing_evidence_id"] if key is None
                   else self.proof_details(key)[1]["evidence_reasons"])
        unknowns.extend({"location": location, "reason": reason} for reason in reasons)
        return next(iter(reasons), "eligible")

    def future(self, value):
        if day(value) <= day(self.as_of):
            raise ValueError("remaining cash events must be after the end-of-day cutoff; reconcile arrears separately")
        return value

    def source_manifest(self):
        return [{"id": k, "path": v["path"], "sha256": v["sha256"], "bytes": v["bytes"]}
                for k, v in self.sources.items()]


def nullable_amount(value, reason, unknowns, location, **kwargs):
    parsed = None if value is None else number(value, location, **kwargs)
    if value is None or reason != "eligible":
        unknowns.append({"location": location, "reason": reason if reason != "eligible" else "unknown_amount"})
        return None
    return parsed
