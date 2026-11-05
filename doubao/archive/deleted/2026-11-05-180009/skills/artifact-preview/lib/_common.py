"""Shared error / dependency / path helpers for ``artifact-preview``.

The JSON protocol is the same one ``verifier-hub`` uses, so an agent that
already parses verifier output does not need a second code path:

    {"ok": true,  "tool": "render", "result": {...}}
    {"ok": false, "tool": "render", "error": {"code": "DEP_MISSING", "msg": "..."}}

Every subcommand emits one such object on stdout, including argument errors.

When a Python package is missing (PyMuPDF, python-pptx, python-docx, openpyxl,
Pillow) the affected renderer degrades to text and records a warning rather
than failing the whole call. System-level dependencies (LibreOffice for PPTX,
Chromium for HTML) behave the same way: an empty page list plus a warning, so
the rest of the manifest stays useful.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import sys
from typing import Any


# ── Error codes ────────────────────────────────────────────────────────


class ErrCode:
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    NOT_A_FILE = "NOT_A_FILE"
    BAD_EXT = "BAD_EXT"
    NOT_FOUND = "NOT_FOUND"
    PARSE_ERROR = "PARSE_ERROR"
    DEP_MISSING = "DEP_MISSING"
    BAD_ARGS = "BAD_ARGS"
    RENDER_FAILED = "RENDER_FAILED"
    INTERNAL = "INTERNAL"


class ArtifactPreviewError(Exception):
    """Recoverable, JSON-serializable error from a subcommand."""

    def __init__(self, code: str, msg: str) -> None:
        super().__init__(msg)
        self.code = code
        self.msg = msg


# ── argparse integration ───────────────────────────────────────────────
#
# argparse's default error() prints usage to stderr and exits 2, which would
# break the "one JSON object on stdout per invocation" contract. --help still
# works normally because it goes through exit(), not error().


class JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Any:  # type: ignore[override]
        raise ArtifactPreviewError(ErrCode.BAD_ARGS, f"{self.prog}: {message}")


# ── Dependency install hints ───────────────────────────────────────────
#
# The sandbox refuses a plain `pip install`: the venv site-packages is not
# writable and the user site lacks sys.path precedence. Installing into a
# private directory and putting it on PYTHONPATH is the form that works.

PYLIBS_DIR = "$HOME/.artifact-preview-pylibs"

_DIST_FOR_MODULE = {
    "fitz": "pymupdf",
    "pptx": "python-pptx",
    "docx": "python-docx",
    "PIL": "Pillow",
}


def install_hint(*dists: str) -> str:
    names = " ".join(dists)
    if os.name == "nt":
        # PowerShell has neither $HOME nor export, so the POSIX hint is not
        # something a Windows user can paste. A user-site install is the
        # simplest form that works there; the --target variant is kept for
        # parity with the sandbox, rewritten in PowerShell syntax.
        return (
            f'install hint (PowerShell): python -m pip install --user {names}  '
            f'or, sandbox-style: pip install --target "$env:USERPROFILE\\.artifact-preview-pylibs" {names}; '
            f'$env:PYTHONPATH = "$env:USERPROFILE\\.artifact-preview-pylibs;$env:PYTHONPATH"'
        )
    return (
        f'install hint: pip install --target "{PYLIBS_DIR}" {names} '
        f'&& export PYTHONPATH="{PYLIBS_DIR}:$PYTHONPATH"  '
        f"(a plain `pip install` fails in the sandbox: the venv site-packages "
        f"is not writable and the user site lacks sys.path precedence)"
    )


def lazy_import(module_name: str, hint: str | None = None) -> Any:
    """Import ``module_name`` on demand; raise ``DEP_MISSING`` if absent."""
    try:
        return __import__(module_name, fromlist=["*"])
    except ImportError as exc:
        dist = _DIST_FOR_MODULE.get(module_name, module_name)
        msg = f"required dependency missing: {module_name} ({exc}) — "
        msg += hint or install_hint(dist)
        raise ArtifactPreviewError(ErrCode.DEP_MISSING, msg) from exc


# ── file:// URIs ───────────────────────────────────────────────────────
#
# ``"file://" + path`` is only correct when path starts with a slash. On
# Windows it produces ``file://C:\dir\f`` where the drive letter is parsed as
# the URL host; on POSIX it leaves spaces and non-ASCII bytes unescaped.
# pathlib's as_uri() handles both.


def path_to_file_uri(path: str | os.PathLike) -> str:
    return pathlib.Path(os.path.abspath(os.fspath(path))).as_uri()


# ── Logical paths ──────────────────────────────────────────────────────
#
# os.getcwd() and Path.resolve() return the *physical* path: symlinks and bind
# mounts are collapsed. Inside the rollout VM that turns the agent-visible
# ``/home/user/.super_doubao/super-doubao-runtime/workspace/...`` into
# ``/sandboxdata/workspace/file/...``, so every path we hand back would use a
# prefix the agent never typed. Honour the shell's $PWD, which tracks the
# logical path, and fall back to getcwd() when it does not apply.


def logical_cwd() -> str:
    cwd = os.getcwd()
    pwd = os.environ.get("PWD")
    if not pwd or not os.path.isabs(pwd):
        return cwd
    try:
        if os.path.samefile(pwd, cwd):
            return os.path.normpath(pwd)
    except OSError:
        return cwd
    # $PWD can be stale — a process started with subprocess(cwd=<subdir>)
    # inherits the parent shell's PWD. When PWD still names an ancestor of the
    # real cwd, re-attach the tail so the caller's prefix survives instead of
    # falling back to the physical mount point.
    try:
        real_pwd = os.path.realpath(pwd).rstrip(os.sep)
        real_cwd = os.path.realpath(cwd)
    except OSError:
        return cwd
    if real_cwd.startswith(real_pwd + os.sep):
        candidate = os.path.join(pwd, real_cwd[len(real_pwd):].lstrip(os.sep))
        try:
            if os.path.samefile(candidate, cwd):
                return os.path.normpath(candidate)
        except OSError:
            pass
    return cwd


def logical_abspath(path: str | os.PathLike) -> str:
    """Absolute path that keeps the caller's prefix (no symlink collapsing)."""
    p = os.path.expanduser(os.fspath(path))
    if not os.path.isabs(p):
        p = os.path.join(logical_cwd(), p)
    return os.path.normpath(p)


# ── Cross-platform external binary discovery ───────────────────────────
#
# shutil.which() only searches PATH. LibreOffice and Chrome do not put
# themselves on PATH on Windows or macOS, so a PATH-only lookup reports them
# missing on machines where they are installed.
#
# On Windows soffice.com is preferred over soffice.exe: the .exe is a launcher
# that returns immediately, so subprocess.run() would finish before the
# conversion has been written to disk.

_IS_WINDOWS = os.name == "nt"
_IS_MACOS = sys.platform == "darwin"

if _IS_WINDOWS:
    OFFICE_BINARY_NAMES: tuple[str, ...] = ("soffice.com", "soffice", "libreoffice")
    BROWSER_BINARY_NAMES: tuple[str, ...] = (
        "chrome", "msedge", "chromium", "chromium-browser",
    )
else:
    OFFICE_BINARY_NAMES = ("soffice", "libreoffice")
    BROWSER_BINARY_NAMES = (
        "chromium-browser", "chromium", "google-chrome", "google-chrome-stable",
        "chrome", "microsoft-edge",
    )


def _office_fallbacks() -> tuple[str, ...]:
    if _IS_WINDOWS:
        bases = [os.environ.get("ProgramFiles", r"C:\Program Files"),
                 os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")]
        return tuple(os.path.join(b, "LibreOffice", "program", exe)
                     for b in bases if b for exe in ("soffice.com", "soffice.exe"))
    if _IS_MACOS:
        return ("/Applications/LibreOffice.app/Contents/MacOS/soffice",
                "/opt/homebrew/bin/soffice", "/usr/local/bin/soffice")
    return ("/usr/bin/soffice", "/usr/bin/libreoffice",
            "/usr/lib/libreoffice/program/soffice", "/snap/bin/libreoffice")


def _browser_fallbacks() -> tuple[str, ...]:
    if _IS_WINDOWS:
        bases = [os.environ.get("ProgramFiles", r"C:\Program Files"),
                 os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                 os.environ.get("LOCALAPPDATA", "")]
        out: list[str] = []
        for b in bases:
            if not b:
                continue
            out.append(os.path.join(b, "Google", "Chrome", "Application", "chrome.exe"))
            out.append(os.path.join(b, "Microsoft", "Edge", "Application", "msedge.exe"))
            out.append(os.path.join(b, "Chromium", "Application", "chrome.exe"))
        return tuple(out)
    if _IS_MACOS:
        return ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "/Applications/Chromium.app/Contents/MacOS/Chromium",
                "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge")
    return ("/usr/bin/chromium-browser", "/usr/bin/chromium",
            "/usr/bin/google-chrome", "/opt/google/chrome/chrome",
            "/snap/bin/chromium")


def find_binary(names: tuple[str, ...], fallbacks: tuple[str, ...] = ()) -> str | None:
    """First existing executable among PATH lookups, then explicit fallbacks."""
    for name in names:
        p = shutil.which(name)
        if p:
            return p
    for p in fallbacks:
        if p and os.path.isfile(p):
            return p
    return None


def find_office_binary(explicit: str | None = None) -> str | None:
    """Locate LibreOffice. ``explicit`` (from --soffice) wins when it exists."""
    if explicit:
        return explicit if os.path.isfile(explicit) else None
    env = os.environ.get("ARTIFACT_PREVIEW_SOFFICE")
    if env and os.path.isfile(env):
        return env
    return find_binary(OFFICE_BINARY_NAMES, _office_fallbacks())


def find_browser_binary(explicit: str | None = None) -> str | None:
    """Locate a Chromium-family browser. ``explicit`` (from --chromium) wins."""
    if explicit:
        return explicit if os.path.isfile(explicit) else None
    env = os.environ.get("ARTIFACT_PREVIEW_CHROMIUM")
    if env and os.path.isfile(env):
        return env
    return find_binary(BROWSER_BINARY_NAMES, _browser_fallbacks())


# The install command for a system binary differs per platform, and a hint the
# reader cannot run is worse than no hint: on Windows `apt install libreoffice`
# just sends the model down a dead end. Give the command for the platform we are
# actually on, and name the override for the case where it is installed but not
# on PATH (which is the normal state on Windows and macOS).

def _office_install_cmd() -> str:
    if _IS_WINDOWS:
        return "`winget install --id TheDocumentFoundation.LibreOffice -e`"
    if _IS_MACOS:
        return "`brew install --cask libreoffice`"
    return "`apt install libreoffice`"


def _browser_install_cmd() -> str:
    if _IS_WINDOWS:
        return ("nothing to install -- the preinstalled Microsoft Edge is "
                "usable; it lives at "
                r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe")
    if _IS_MACOS:
        return "`brew install --cask google-chrome`"
    return "`apt install chromium-browser`"


def office_missing_msg() -> str:
    return ("LibreOffice not found. Looked for " + ", ".join(OFFICE_BINARY_NAMES)
            + " on PATH plus the standard install locations for this platform. "
              "Install it: " + _office_install_cmd()
            + ". If it is already installed but off PATH (the usual case on "
              "Windows and macOS), point --soffice / $ARTIFACT_PREVIEW_SOFFICE "
              "at the binary.")


def browser_missing_msg() -> str:
    return ("chromium not installed. Looked for " + ", ".join(BROWSER_BINARY_NAMES)
            + " on PATH plus the standard install locations for this platform. "
              + _browser_install_cmd()
            + ". If a browser is already installed but off PATH, point "
              "--chromium / $ARTIFACT_PREVIEW_CHROMIUM at the binary.")


# ── JSON output protocol ──────────────────────────────────────────────


def ok(tool: str, result: dict, **extra: Any) -> dict:
    payload: dict[str, Any] = {"ok": True, "tool": tool, "result": result}
    payload.update(extra)
    return payload


def err(tool: str, code: str, msg: str, **extra: Any) -> dict:
    payload: dict[str, Any] = {"ok": False, "tool": tool,
                               "error": {"code": code, "msg": msg}}
    payload.update(extra)
    return payload


def emit(payload: dict, *, indent: int | None = 2) -> int:
    """Write ``payload`` as JSON to stdout; return the shell exit code."""
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=indent))
    sys.stdout.write("\n")
    sys.stdout.flush()
    return 0 if payload.get("ok") else 1
