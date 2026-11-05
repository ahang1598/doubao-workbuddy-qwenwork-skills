"""Shared output protocol + helpers for the verifier CLI.

Every ``cmd_*`` function in lib/<family>.py SHOULD return a plain dict and
let the dispatcher in bin/verifier wrap it via ``ok()`` / ``err()`` and
``emit()`` it.  Functions MAY raise ``VerifierError`` to bubble a
recoverable error up; anything else propagates as an unhandled exception.

Output schema (one JSON object on stdout, no extra text):

    {"ok": true,  "tool": "<family>.<sub>", "result": {...}, "evidence": {...}}
    {"ok": false, "tool": "<family>.<sub>", "error": {"code": "...", "msg": "..."}}

``evidence`` is intentionally separate from ``result``: ``result`` is the
machine-readable answer; ``evidence`` is the human-quotable string the
judge can paste into ``questionnaire.md`` rationale.
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import pathlib
import shutil
import sys
from typing import Any


# ---------------------------------------------------------------------------
# Error codes — kept as a flat enum so SKILL.md / agent prompts can list them.
# ---------------------------------------------------------------------------

class ErrCode:
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    NOT_A_FILE = "NOT_A_FILE"
    BAD_EXT = "BAD_EXT"
    PARSE_ERROR = "PARSE_ERROR"
    LOCATOR_INVALID = "LOCATOR_INVALID"
    NOT_FOUND = "NOT_FOUND"
    DEP_MISSING = "DEP_MISSING"
    BAD_ARGS = "BAD_ARGS"
    INTERNAL = "INTERNAL"


class VerifierError(Exception):
    """Recoverable, JSON-serializable error from a verifier subcommand."""
    def __init__(self, code: str, msg: str) -> None:
        super().__init__(msg)
        self.code = code
        self.msg = msg


# ---------------------------------------------------------------------------
# Output wrappers
# ---------------------------------------------------------------------------

def ok(tool: str, result: Any, evidence: Any | None = None) -> dict:
    out: dict = {"ok": True, "tool": tool, "result": result}
    if evidence is not None:
        out["evidence"] = evidence
    return out


def err(tool: str, code: str, msg: str) -> dict:
    return {"ok": False, "tool": tool, "error": {"code": code, "msg": msg}}


def emit(payload: dict) -> int:
    """Write a single-line JSON to stdout; return shell exit code."""
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if payload.get("ok") else 1


# ---------------------------------------------------------------------------
# argparse integration
#
# argparse's default ``error()`` prints usage to stderr and exits 2, which
# would break the "every invocation prints one JSON object on stdout" contract.
# ``JsonArgumentParser`` turns those into VerifierError(BAD_ARGS) so the
# dispatcher can emit a normal error envelope.  ``--help`` still behaves
# normally because help goes through ``exit()``, not ``error()``.
# ---------------------------------------------------------------------------

class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Any:  # type: ignore[override]
        raise VerifierError(ErrCode.BAD_ARGS, f"{self.prog}: {message}")


# ---------------------------------------------------------------------------
# Dependency install hint
#
# The rollout sandbox refuses a plain ``pip install``: the user site lacks
# sys.path precedence and the venv's site-packages is not writable.  Installing
# into a private directory and putting it on PYTHONPATH is the form that works.
# ---------------------------------------------------------------------------

PYLIBS_DIR = "$HOME/.verifier-pylibs"


def install_hint(*dists: str) -> str:
    names = " ".join(dists)
    if os.name == "nt":
        # PowerShell has neither $HOME nor export, so the POSIX hint is not
        # something a Windows user can paste. A user-site install is the
        # simplest form that works there; the --target variant is kept for
        # parity with the sandbox, rewritten in PowerShell syntax.
        return (
            f'install hint (PowerShell): python -m pip install --user {names}  '
            f'or, sandbox-style: pip install --target "$env:USERPROFILE\\.verifier-pylibs" {names}; '
            f'$env:PYTHONPATH = "$env:USERPROFILE\\.verifier-pylibs;$env:PYTHONPATH"'
        )
    return (
        f'install hint: pip install --target "{PYLIBS_DIR}" {names} '
        f'&& export PYTHONPATH="{PYLIBS_DIR}:$PYTHONPATH"  '
        f"(a plain `pip install` fails in the sandbox: the venv site-packages "
        f"is not writable and the user site lacks sys.path precedence)"
    )


# ---------------------------------------------------------------------------
# file:// URIs
#
# ``"file://" + path`` is only correct when ``path`` starts with a slash. On
# Windows it yields ``file://C:\dir\f`` where the drive letter is parsed as the
# URL host, and it also leaves spaces and non-ASCII characters unescaped on
# POSIX. Always go through pathlib's as_uri().
# ---------------------------------------------------------------------------

def path_to_file_uri(path: str) -> str:
    """Absolute filesystem path -> a correctly escaped ``file://`` URI."""
    return pathlib.Path(os.path.abspath(path)).as_uri()


def dir_to_file_uri(path: str) -> str:
    """Same as :func:`path_to_file_uri`, for a directory that need not exist."""
    return pathlib.Path(os.path.abspath(path)).as_uri()


# ---------------------------------------------------------------------------
# Cross-platform external binary discovery
#
# shutil.which() only searches PATH. The LibreOffice installers on Windows and
# macOS do not put their binary on PATH, so PATH lookup alone reports the tool
# as missing on machines where it is installed.
#
# On Windows soffice.com is preferred over soffice.exe: the .exe is a launcher
# that returns immediately, so subprocess.run() would finish before the
# conversion is written to disk.
# ---------------------------------------------------------------------------

_IS_WINDOWS = os.name == "nt"

if _IS_WINDOWS:
    OFFICE_BINARY_NAMES: tuple[str, ...] = ("soffice.com", "soffice", "libreoffice")
else:
    OFFICE_BINARY_NAMES = ("soffice", "libreoffice")


def _office_fallback_paths() -> tuple[str, ...]:
    if _IS_WINDOWS:
        bases = [os.environ.get("ProgramFiles", r"C:\Program Files"),
                 os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")]
        return tuple(
            os.path.join(b, "LibreOffice", "program", exe)
            for b in bases if b for exe in ("soffice.com", "soffice.exe")
        )
    if sys.platform == "darwin":
        return (
            "/Applications/LibreOffice.app/Contents/MacOS/soffice",
            "/opt/homebrew/bin/soffice",
            "/usr/local/bin/soffice",
        )
    return ("/usr/bin/soffice", "/usr/bin/libreoffice",
            "/usr/lib/libreoffice/program/soffice",
            "/snap/bin/libreoffice")


def find_binary(names: tuple[str, ...], fallbacks: tuple[str, ...] = ()) -> str | None:
    """First existing executable among PATH lookups then explicit fallbacks."""
    for name in names:
        p = shutil.which(name)
        if p:
            return p
    for p in fallbacks:
        if p and os.path.isfile(p):
            return p
    return None


def find_office_binary() -> str | None:
    """Locate LibreOffice/soffice on any platform. None when unavailable."""
    return find_binary(OFFICE_BINARY_NAMES, _office_fallback_paths())


# The install command differs per platform, and a hint the reader cannot run is
# worse than no hint: on Windows `apt install libreoffice` just sends the model
# down a dead end. Give the command for the platform we are actually on.

def _office_install_cmd() -> str:
    if _IS_WINDOWS:
        return "`winget install --id TheDocumentFoundation.LibreOffice -e`"
    if sys.platform == "darwin":
        return "`brew install --cask libreoffice`"
    return "`apt install libreoffice`"


def office_missing_msg() -> str:
    """The DEP_MISSING message for a missing LibreOffice, platform-correct."""
    return ("LibreOffice not found. Looked for " + ", ".join(OFFICE_BINARY_NAMES)
            + " on PATH plus the standard install locations for this platform. "
              "Install it: " + _office_install_cmd()
            + ". If it is already installed but off PATH (the usual case on "
              "Windows and macOS), pass --soffice <path>.")


# ---------------------------------------------------------------------------
# Path / file helpers
# ---------------------------------------------------------------------------

def resolve_path(p: str) -> str:
    """Expand ``~`` and resolve to absolute path, but do NOT require existence."""
    return os.path.abspath(os.path.expanduser(p))


def require_file(path: str, expected_exts: tuple[str, ...] | None = None) -> str:
    """Validate that ``path`` is an existing file and (optionally) has an allowed extension.

    Raises VerifierError on any failure.  Returns the absolute path.
    """
    abs_path = resolve_path(path)
    if not os.path.exists(abs_path):
        raise VerifierError(ErrCode.FILE_NOT_FOUND, f"file does not exist: {abs_path}")
    if not os.path.isfile(abs_path):
        raise VerifierError(ErrCode.NOT_A_FILE, f"not a regular file: {abs_path}")
    if expected_exts:
        ext = os.path.splitext(abs_path)[1].lower()
        if ext not in expected_exts:
            raise VerifierError(
                ErrCode.BAD_EXT,
                f"unsupported extension {ext!r} for {abs_path}; expected one of {list(expected_exts)}",
            )
    return abs_path


def detect_kind(path: str) -> str:
    """Cheap file-kind detector based on extension + mimetype.

    Returns one of: ``xlsx``, ``docx``, ``pdf``, ``pptx``, ``text``, ``image``,
    ``binary``, ``unknown``.  Used by ``file_io.artifact_list``.
    """
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xlsm"):
        return "xlsx"
    if ext in (".docx", ".docm"):
        return "docx"
    if ext == ".pdf":
        return "pdf"
    if ext in (".pptx", ".pptm"):
        return "pptx"
    if ext in (".md", ".txt", ".csv", ".html", ".htm", ".json", ".yaml", ".yml", ".log"):
        return "text"
    if ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"):
        return "image"
    mime, _ = mimetypes.guess_type(path)
    if mime and mime.startswith("text/"):
        return "text"
    if mime and mime.startswith("image/"):
        return "image"
    if mime is None:
        return "unknown"
    return "binary"


def file_size(path: str) -> int:
    try:
        return os.path.getsize(path)
    except OSError:
        return -1


# ---------------------------------------------------------------------------
# Lazy-import helper — used by lib/<family>.py whose dependency is heavy /
# may not always be installed.
# ---------------------------------------------------------------------------

# module name -> pip distribution name, where they differ
_DIST_FOR_MODULE = {
    "docx": "python-docx",
    "pptx": "python-pptx",
    "fitz": "pymupdf",
    "yaml": "PyYAML",
    "PIL": "Pillow",
}


def lazy_import(module_name: str, hint: str | None = None) -> Any:
    """Import a module on demand; raise VerifierError(DEP_MISSING) if unavailable."""
    try:
        return __import__(module_name, fromlist=["*"])
    except ImportError as e:
        dist = _DIST_FOR_MODULE.get(module_name, module_name)
        msg = f"required dependency missing: {module_name} ({e}) — "
        msg += hint or install_hint(dist)
        raise VerifierError(ErrCode.DEP_MISSING, msg) from e


# ---------------------------------------------------------------------------
# Locator parsing — the same JSON-blob locator works across families:
#   xlsx: {"sheet": "P&L", "cell": "F12"}
#   docx: {"heading_regex": "区位优势", "min_chars": 80}
# Subcommands accept either ``--locator '<json>'`` or family-specific shorthand
# flags.  Helper kept thin to avoid a per-family JSON-blob bikeshed.
# ---------------------------------------------------------------------------

def parse_locator(raw: str | None) -> dict:
    """Parse a ``--locator`` JSON string; return ``{}`` on None.  Raises BAD_ARGS."""
    if raw is None or raw == "":
        return {}
    try:
        loc = json.loads(raw)
    except json.JSONDecodeError as e:
        raise VerifierError(ErrCode.LOCATOR_INVALID, f"--locator must be JSON: {e}") from e
    if not isinstance(loc, dict):
        raise VerifierError(ErrCode.LOCATOR_INVALID, "--locator JSON must be an object")
    return loc


# ---------------------------------------------------------------------------
# Numeric tolerance — shared between xlsx.assert_value, num.assert and rubric.numeric.
# ---------------------------------------------------------------------------

def in_tolerance(actual: Any, expected: float, tol_abs: float | None,
                 tol_rel: float | None) -> tuple[bool, str]:
    """Return (passed, explanation).  At least one of tol_abs/tol_rel must be given."""
    try:
        a = float(actual)
    except (TypeError, ValueError):
        return False, f"actual value {actual!r} is not numeric"
    e = float(expected)
    if tol_abs is None and tol_rel is None:
        # Default: exact equality
        return a == e, f"expected {e}, actual {a} (exact)"
    if tol_abs is not None and abs(a - e) <= tol_abs:
        return True, f"expected {e}, actual {a}, |Δ|={abs(a - e):.6g} ≤ tol_abs={tol_abs}"
    if tol_rel is not None and e != 0 and abs(a - e) / abs(e) <= tol_rel:
        return True, f"expected {e}, actual {a}, |Δ|/|exp|={abs(a - e) / abs(e):.6g} ≤ tol_rel={tol_rel}"
    parts = [f"expected {e}, actual {a}, |Δ|={abs(a - e):.6g}"]
    if tol_abs is not None:
        parts.append(f"tol_abs={tol_abs}")
    if tol_rel is not None:
        parts.append(f"tol_rel={tol_rel}")
    return False, "; ".join(parts)


# ---------------------------------------------------------------------------
# Evidence helper — keep produced evidence shapes consistent.
# ---------------------------------------------------------------------------

def evidence(file: str | None = None, locator: Any | None = None,
             quote: str | None = None, **extras: Any) -> dict:
    """Build a uniform evidence dict.  ``quote`` is a short human-readable string."""
    out: dict = {}
    if file:
        out["file"] = file
    if locator is not None:
        out["locator"] = locator
    if quote is not None:
        out["quote"] = quote
    for k, v in extras.items():
        out[k] = v
    return out
