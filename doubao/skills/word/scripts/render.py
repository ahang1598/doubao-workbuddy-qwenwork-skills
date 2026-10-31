#!/usr/bin/env python3
"""DOCX rendering via lark-cli; PDF/PNG evidence, not visual approval.

render creates one isolated conversion run and all page PNGs.
No HTTP client, compression, automatic retries, TOC update or document repair
is implemented here.
Exit codes: 0 = operation succeeded; 1 = not succeeded (including pending tasks).
"""

from __future__ import annotations

import argparse
import errno
import hashlib
import importlib
import importlib.metadata
import importlib.util
import json
import math
import os
import platform
import re
import shutil
import site
import subprocess
import sys
import sysconfig
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile

SCHEMA_VERSION = 1
MANIFEST_NAME = "render-manifest.json"
MAX_PAGE_PIXELS = 50_000_000  # Resource limit, not a document-quality threshold.
PYMUPDF_VERSION = "1.27.2.2"
INSTALL_TIMEOUT = 180
LOCK_TIMEOUT = 240
CACHE_MANIFEST = "verified.json"
PYMUPDF_INFO = {}


class RenderError(Exception):
    def __init__(self, code: str, message: str, *, location_restricted: bool = False):
        super().__init__(message)
        self.code = code
        self.location_restricted = location_restricted


class RenderArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise RenderError("INVALID_ARGUMENT", message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def file_info(path: Path) -> dict:
    return {"sha256": sha256(path), "size": path.stat().st_size}


def redact(value):
    if isinstance(value, dict):
        return {
            key: (
                "<redacted>"
                if re.search(r"access.?token|refresh.?token|secret|authorization|cookie", key, re.I)
                else redact(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, str):
        value = re.sub(r"(https?://)[^\s/@]+(?::[^\s/@]*)?@", r"\1<redacted>@", value)
        value = re.sub(r"(https?://[^\s?#\"']+)[?#][^\s\"']+", r"\1?<redacted>", value)
        value = re.sub(r"(?i)\bBearer\s+\S+", "Bearer <redacted>", value)
        value = re.sub(
            r"(?i)\b(token|password|secret|authorization|cookie)(\s*[:=]\s*)\S+",
            r"\1\2<redacted>", value,
        )
        return value
    return value


def write_json(path: Path, value: dict) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(redact(value), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def find_cli(value: str) -> Path:
    found = shutil.which(value)
    if not found:
        raise RenderError("CLI_UNAVAILABLE", "找不到指定的 lark-cli；不要自动升级或换渲染器。")
    return Path(found).resolve()


def invoke(cli: Path, argv: list[str], cwd: Path, timeout: int) -> dict:
    try:
        result = subprocess.run(
            [str(cli), *argv], cwd=cwd, capture_output=True,
            text=True, encoding="utf-8", errors="replace", timeout=timeout, check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RenderError(
            "PROCESS_TIMEOUT",
            f"CLI 调用 {argv[:3]!r} 超过 {timeout} 秒；不自动重试或创建新任务。",
        ) from exc
    record = {"argv": [str(cli), *argv], "returncode": result.returncode}
    for name, text in [("stdout", result.stdout), ("stderr", result.stderr)]:
        try:
            record[name] = redact(json.loads(text))
        except ValueError:
            record[name] = redact(text)
    return record


def cli_identity(cli: Path) -> dict:
    version = invoke(cli, ["--version"], Path.cwd(), 30)
    if version["returncode"] != 0 or not isinstance(version["stdout"], str):
        raise RenderError("CLI_VERSION_FAILED", "不能读取 CLI 版本。")
    return {"path": str(cli), "version": version["stdout"].strip(), **file_info(cli)}


def check_capability(cli: Path) -> None:
    result = invoke(cli, ["docs", "+word-to-pdf", "--help"], Path.cwd(), 30)
    text = result["stdout"]
    if (
        result["returncode"] != 0 or not isinstance(text, str)
        or not re.search(r"lark-cli\s+docs\s+\+word-to-pdf\s+\[flags\]", text)
        or "--file" not in text or "--output" not in text
    ):
        raise RenderError(
            "COMMAND_UNAVAILABLE",
            "当前 CLI 未提供具体的 +word-to-pdf 帮助；docs 总帮助不算能力验证。",
        )


def pymupdf_cache() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Caches"
    else:
        configured = Path(os.environ.get("XDG_CACHE_HOME", ""))
        base = configured if configured.is_absolute() else Path.home() / ".cache"
    identity = json.dumps([
        sys.executable, str(Path(sys.executable).resolve()), sys.prefix, sys.version,
        sys.implementation.cache_tag, sysconfig.get_platform(), platform.machine(),
    ])
    key = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]
    return base / "lark-cli" / "word" / "pymupdf" / PYMUPDF_VERSION / key


@contextmanager
def cache_lock(path: Path):
    """OS locks are released even if the installing process exits unexpectedly."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as stream:
        stream.seek(0, os.SEEK_END)
        if stream.tell() == 0:
            stream.write(b"\0")
            stream.flush()
        deadline = time.monotonic() + LOCK_TIMEOUT
        while True:
            try:
                stream.seek(0)
                if sys.platform == "win32":
                    import msvcrt
                    msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as exc:
                if exc.errno not in {errno.EACCES, errno.EAGAIN, errno.EDEADLK}:
                    raise
                if time.monotonic() >= deadline:
                    raise RenderError("DEPENDENCY_LOCK_TIMEOUT", "等待 PyMuPDF 缓存安装锁超时。") from exc
                time.sleep(0.1)
        try:
            yield
        finally:
            stream.seek(0)
            if sys.platform == "win32":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def installation_location_restricted(output: str) -> bool:
    if re.search(r"(?m)^error: externally-managed-environment\s*$", output):
        return True
    # Require pip's installation OSError and a path in this interpreter's install
    # scheme. Permission words in proxy, TLS, wheel-download or temp errors do not qualify.
    roots = [sysconfig.get_path(key) for key in ("purelib", "platlib", "scripts")]
    user_site = site.getusersitepackages()
    roots.extend([user_site] if isinstance(user_site, str) else user_site)
    roots.append(str(Path(site.getuserbase()) / ("Scripts" if os.name == "nt" else "bin")))
    for line in output.splitlines():
        match = re.fullmatch(
            r"ERROR: Could not install packages due to an (?:OSError|EnvironmentError): "
            r"\[(?:Errno (?:1|13|30)|WinError 5)\] "
            r"(?:Permission denied|Operation not permitted|Read-only file system|Access is denied)"
            r":\s*['\"]([^'\"\r\n]+)['\"]\s*", line, re.I,
        )
        if match:
            target = Path(match[1]).resolve()
            if any(target.is_relative_to(Path(root).resolve()) for root in roots if root):
                return True
    return False


def dependency_process(argv: list[str], cwd: Path, code: str, timeout: int) -> str:
    try:
        result = subprocess.run(
            argv, cwd=cwd, capture_output=True, text=True, encoding="utf-8",
            errors="replace", shell=False, timeout=timeout, check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RenderError(code + "_TIMEOUT", f"PyMuPDF 依赖操作超过 {timeout} 秒。") from exc
    if result.returncode:
        output = (result.stderr + "\n" + result.stdout).strip()
        detail = redact(output)[-4000:]
        raise RenderError(
            code, f"PyMuPDF 依赖操作失败（退出码 {result.returncode}）：{detail}",
            location_restricted=(code == "DEPENDENCY_INSTALL_FAILED"
                                 and installation_location_restricted(output)),
        )
    return result.stdout


def pip_install_args(target: Path | None = None) -> list[str]:
    argv = [sys.executable, "-m", "pip", "install", f"PyMuPDF=={PYMUPDF_VERSION}",
            "--only-binary=:all:", "--no-deps", "--no-compile",
            "--no-input", "--disable-pip-version-check"]
    if target is not None:
        argv += ["--target", str(target)]
    return argv


def probe_pymupdf(cwd: Path, target: Path | None = None) -> dict:
    # Default installs need normal startup so pip's user-site fallback is visible.
    # Cache candidates are isolated from ambient packages before publication.
    output = dependency_process(
        [sys.executable, *(["-I"] if target is not None else []), "-B", "-c",
         "import sys, json; from pathlib import Path; "
         "sys.path[:0] = [sys.argv[1]] if sys.argv[1] else []; "
         "import pymupdf, importlib.metadata; "
         "dist = importlib.metadata.distribution('PyMuPDF'); "
         "assert dist.version == sys.argv[2]; "
         "path = Path(pymupdf.__file__).resolve(); "
         "assert path == Path(dist.locate_file('pymupdf/__init__.py')).resolve(); "
         "assert not sys.argv[1] or path.is_relative_to(Path(sys.argv[1]).resolve()); "
         "doc = pymupdf.open(); page = doc.new_page(); "
         "page.get_pixmap(dpi=72, colorspace=pymupdf.csRGB, alpha=False); doc.close(); "
         "print(json.dumps({'path': str(path), 'version': dist.version}))",
         str(target) if target is not None else "", PYMUPDF_VERSION],
        cwd, "DEPENDENCY_VERIFY_FAILED", 30,
    )
    try:
        return json.loads(output)
    except ValueError as exc:
        raise RenderError("DEPENDENCY_VERIFY_FAILED", "PyMuPDF 验证进程未返回有效 JSON。") from exc


def cache_files(site: Path) -> dict:
    files = {}
    for path in site.rglob("*"):
        if path.is_symlink():
            raise RenderError("DEPENDENCY_CACHE_INVALID", "PyMuPDF 缓存不能包含符号链接。")
        if path.is_file():
            files[path.relative_to(site).as_posix()] = file_info(path)
    if not files:
        raise RenderError("DEPENDENCY_CACHE_INVALID", "PyMuPDF 缓存为空。")
    return files


def validate_cache(cache: Path) -> None:
    try:
        if cache.is_symlink() or (cache / "site").is_symlink():
            raise ValueError("缓存不能是符号链接")
        manifest = json.loads((cache / CACHE_MANIFEST).read_text(encoding="utf-8"))
        if manifest["version"] != PYMUPDF_VERSION or manifest["files"] != cache_files(cache / "site"):
            raise ValueError("缓存版本、文件集合或 SHA-256 不匹配")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise RenderError("DEPENDENCY_CACHE_INVALID", f"PyMuPDF 缓存完整性检查失败：{exc}") from exc


def install_pymupdf(cache: Path) -> None:
    with tempfile.TemporaryDirectory(prefix=cache.name + "-install-", dir=cache.parent) as temporary:
        staging = Path(temporary) / "candidate"
        site = staging / "site"
        site.mkdir(parents=True)
        dependency_process(
            pip_install_args(site),
            staging, "DEPENDENCY_INSTALL_FAILED", INSTALL_TIMEOUT,
        )
        probe_pymupdf(staging, site)
        write_json(staging / CACHE_MANIFEST, {
            "version": PYMUPDF_VERSION, "files": cache_files(site),
        })
        validate_cache(staging)
        os.replace(staging, cache)


def import_pymupdf():
    try:
        return importlib.import_module("pymupdf")
    except Exception as exc:
        raise RenderError(
            "DEPENDENCY_IMPORT_FAILED", f"已有 PyMuPDF 无法加载：{redact(str(exc))}"
        ) from exc


def load_pymupdf(source: str, target: Path | None = None, expected: dict | None = None):
    if target is not None:
        sys.path.insert(0, str(target))
    importlib.invalidate_caches()
    previous = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        module = import_pymupdf()
        path = Path(module.__file__).resolve()
        if source != "existing":
            dist = importlib.metadata.distribution("PyMuPDF")
            if (dist.version != PYMUPDF_VERSION
                    or path != Path(dist.locate_file("pymupdf/__init__.py")).resolve()
                    or (target is not None and not path.is_relative_to(target.resolve()))
                    or (expected is not None and str(path) != expected["path"])):
                raise ValueError("当前进程的 PyMuPDF 路径或版本与验证来源不一致")
            with module.open() as document:
                document.new_page().get_pixmap(dpi=72, colorspace=module.csRGB, alpha=False)
        else:
            try:
                dist = importlib.metadata.distribution("PyMuPDF")
            except importlib.metadata.PackageNotFoundError:
                dist = None
        PYMUPDF_INFO.update(
            python=sys.executable, path=str(path),
            version=dist.version if dist is not None else module.VersionBind, source=source,
        )
        return module
    except Exception as exc:
        if target is not None:
            sys.path.remove(str(target))
        if isinstance(exc, RenderError) and source == "existing":
            raise
        raise RenderError(
            "DEPENDENCY_VERIFY_FAILED", f"PyMuPDF 当前进程加载或转图失败：{redact(str(exc))}"
        ) from exc
    finally:
        sys.dont_write_bytecode = previous


def pdf_module():
    module = sys.modules.get("pymupdf")
    if module is not None and PYMUPDF_INFO.get("path") == str(Path(module.__file__).resolve()):
        return module
    # A found package that fails to load is broken, not missing. Never replace it silently.
    if "pymupdf" in sys.modules or importlib.util.find_spec("pymupdf") is not None:
        return load_pymupdf("existing")
    cache = pymupdf_cache()
    with cache_lock(cache.with_suffix(".lock")):
        # Another process may have completed a default (including user-site) install.
        if site.ENABLE_USER_SITE:
            user_sites = site.getusersitepackages()
            for directory in ([user_sites] if isinstance(user_sites, str) else user_sites):
                if Path(directory).is_dir() and directory not in sys.path:
                    site.addsitedir(directory)
        importlib.invalidate_caches()
        if importlib.util.find_spec("pymupdf") is not None:
            return load_pymupdf("existing")
        if cache.exists() or cache.is_symlink():
            validate_cache(cache)
            return load_pymupdf("cache", cache / "site")
        dependency_process(
            [sys.executable, "-m", "pip", "--version"], Path.cwd(),
            "DEPENDENCY_PIP_UNAVAILABLE", 30,
        )
        try:
            dependency_process(pip_install_args(), Path.cwd(), "DEPENDENCY_INSTALL_FAILED", INSTALL_TIMEOUT)
        except RenderError as primary:
            if not primary.location_restricted:
                raise
            try:
                install_pymupdf(cache)
                return load_pymupdf("cache-install", cache / "site")
            except Exception as fallback:
                raise RenderError(
                    "DEPENDENCY_FALLBACK_FAILED",
                    f"默认安装失败 [{primary.code}]：{primary}；"
                    f"隔离缓存回退失败 [{getattr(fallback, 'code', 'DEPENDENCY_CACHE_FAILED')}]："
                    f"{redact(str(fallback))}。请修复对应原因后重试。",
                ) from fallback
        verified = probe_pymupdf(Path.cwd())
        return load_pymupdf("default-install", Path(verified["path"]).parent.parent, verified)


def local_file(run: Path, name: str) -> Path:
    if not isinstance(name, str) or Path(name).name != name or name in {"", ".", ".."}:
        raise RenderError("INVALID_MANIFEST", "清单中的输出文件名无效。")
    path = run / name
    if path.is_symlink():
        raise RenderError("INVALID_ARTIFACT", "渲染产物不能是符号链接。")
    return path


def require_match(path: Path, expected: dict) -> None:
    if not path.is_file() or file_info(path) != {
        "sha256": expected["sha256"], "size": expected["size"]
    }:
        raise RenderError("ARTIFACT_CHANGED", f"文件缺失或已改变，旧验收证据失效：{path}")


def check_input(manifest: dict, run: Path) -> None:
    require_match(Path(manifest["input"]["path"]), manifest["input"])
    require_match(local_file(run, "input.docx"), manifest["input"])


def rasterize(pdf: Path, run: Path, dpi: int) -> dict:
    fitz = pdf_module()
    fingerprint = file_info(pdf)
    pages = []
    with fitz.open(pdf) as document:
        if not document.is_pdf or document.needs_pass or document.page_count < 1:
            raise RenderError("INVALID_PDF", "PDF 无效、需密码或没有页面。")
        for index, page in enumerate(document, 1):
            rect = page.rect
            if not all(math.isfinite(v) for v in rect) or rect.width <= 0 or rect.height <= 0:
                raise RenderError("INVALID_PAGE", f"第 {index} 页尺寸无效。")
            width, height = math.ceil(rect.width * dpi / 72), math.ceil(rect.height * dpi / 72)
            if width * height > MAX_PAGE_PIXELS:
                raise RenderError("PAGE_RESOURCE_LIMIT", f"第 {index} 页超过转图像素预算，未跳页。")
            image = local_file(run, f"page-{index:04d}.png")
            if image.exists():
                raise RenderError("OUTPUT_EXISTS", f"拒绝覆盖已有页面：{image}")
            pixmap = page.get_pixmap(dpi=dpi, colorspace=fitz.csRGB, alpha=False)
            pixmap.save(image)
            pages.append({
                "page": index, "file": image.name, **file_info(image),
                "width_px": pixmap.width, "height_px": pixmap.height,
                "width_pt": rect.width, "height_pt": rect.height,
            })
            del pixmap
        metadata = document.metadata
    require_match(pdf, fingerprint)
    return {
        "pdf": {"file": pdf.name, **fingerprint, "metadata": metadata},
        "page_count": len(pages), "pages": pages, "rasterizer": f"PyMuPDF {fitz.VersionBind}",
        "dependency": dict(PYMUPDF_INFO),
    }


def convert(manifest: dict, run: Path, cli: Path, wait_seconds: int) -> int:
    try:
        check_input(manifest, run)
        pdf = local_file(run, "document.pdf")
        if pdf.exists():
            raise RenderError("OUTPUT_EXISTS", "本轮 PDF 已存在；不覆盖或当作新结果。")
        argv = ["docs", "+word-to-pdf", "--file", "./input.docx",
                "--wait-timeout-seconds", str(wait_seconds)]
        argv += ["--output", "./document.pdf", "--if-exists", "error", "--format", "json"]
        record = invoke(cli, argv, run, wait_seconds + 30)
        manifest["attempts"].append(record)
        check_input(manifest, run)
        envelope = record["stdout"]
        if record["returncode"] != 0:
            raise RenderError("CLI_FAILED", f"CLI 退出码 {record['returncode']}，详见本轮清单中的脱敏错误。")
        if not isinstance(envelope, dict) or envelope.get("ok") is not True or envelope.get("dry_run"):
            raise RenderError("INVALID_RESPONSE", "未取得真实转换的成功 JSON 信封。")
        data = envelope.get("data")
        if not isinstance(data, dict):
            raise RenderError("INVALID_RESPONSE", "转换结果缺少 data 对象。")
        task_id = data.get("task_id")
        if not isinstance(task_id, str) or not 1 <= len(task_id) <= 128:
            raise RenderError("INVALID_RESPONSE", "转换结果缺少有效 task_id。")
        manifest["task_id"] = task_id
        manifest["cli_status"] = data.get("status")
        for key in ["upload_preparation", "expires_at", "poll_after_ms", "stage"]:
            if key in data:
                manifest[key] = data[key]
        preparation = manifest.get("upload_preparation", {})
        if not isinstance(preparation, dict):
            raise RenderError("INVALID_RESPONSE", "upload_preparation 不是对象。")
        if preparation.get("layout_preserved") is False:
            raise RenderError("LAYOUT_NOT_PRESERVED", "CLI 明确报告上传副本未保持布局。")
        if data.get("status") == "processing":
            if pdf.exists():
                raise RenderError("UNEXPECTED_OUTPUT", "任务尚未完成却已有输出文件，拒绝复用。")
            manifest["status"] = "pending"
            return 1
        if data.get("status") != "succeeded" or data.get("timed_out") is True:
            raise RenderError("TASK_NOT_SUCCEEDED", f"任务未成功：{data.get('status')!r}")
        output_path = data.get("output_path")
        if not isinstance(output_path, str) or (run / output_path).resolve() != pdf.resolve():
            raise RenderError("OUTPUT_MISMATCH", "CLI 实际输出位置不属于本轮预期 PDF。")
        if not pdf.is_file() or pdf.stat().st_size <= 0:
            raise RenderError("MISSING_PDF", "CLI 报告完成，但 PDF 缺失或为空。")
        size = data.get("downloaded_size")
        if type(size) is not int or size != pdf.stat().st_size:
            raise RenderError("SIZE_MISMATCH", "实际 PDF 大小与 downloaded_size 不符。")
        manifest.update(rasterize(pdf, run, manifest["dpi"]))
        check_input(manifest, run)
        manifest["status"] = "rendered"
        return 0
    except Exception as exc:
        manifest["status"] = "failed"
        manifest["error"] = {"code": getattr(exc, "code", "RENDER_FAILED"), "message": str(exc)}
        raise
    finally:
        write_json(run / MANIFEST_NAME, manifest)


def main() -> int:
    parser = RenderArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    render = commands.add_parser("render", help="create one conversion run and all page PNGs")
    render.add_argument("docx", type=Path)
    render.add_argument("--output-dir", type=Path, required=True, help="parent of a unique run directory")
    render.add_argument("--cli", default="lark-cli", help="runtime CLI executable, not a shell command")
    render.add_argument("--dpi", type=int, default=150)
    render.add_argument("--wait-timeout-seconds", type=int, default=120)
    manifest_path = None
    try:
        args = parser.parse_args()
        if not 72 <= args.dpi <= 300 or not 0 <= args.wait_timeout_seconds <= 600:
            raise RenderError("INVALID_ARGUMENT", "dpi 范围 72–300；等待秒数范围 0–600。")
        source = args.docx.resolve(strict=True)
        if source.suffix.lower() != ".docx" or not source.is_file():
            raise RenderError("INVALID_DOCX", "输入必须为现有 .docx 文件。")
        with ZipFile(source) as archive:
            if not {"[Content_Types].xml", "_rels/.rels", "word/document.xml"} <= set(archive.namelist()):
                raise RenderError("INVALID_DOCX", "输入缺少 DOCX 基本部件；请先完成 audit。")
        pdf_module()  # Fail before upload if local rasterization is unavailable.
        cli = find_cli(args.cli)
        identity = cli_identity(cli)
        check_capability(cli)
        root = args.output_dir.resolve()
        root.mkdir(parents=True, exist_ok=True)
        run = Path(tempfile.mkdtemp(prefix="render-", dir=root))
        manifest_path = run / MANIFEST_NAME
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "status": "created", "visual_review": "pending",
            "channel": "lark-cli docs +word-to-pdf",
            "input": {"path": str(source), **file_info(source)},
            "cli": identity, "dpi": args.dpi, "attempts": [],
            "dependency": dict(PYMUPDF_INFO),
        }
        shutil.copyfile(source, run / "input.docx")
        exit_code = convert(manifest, run, cli, args.wait_timeout_seconds)
        result = {
            "status": manifest["status"],
            "manifest": str(manifest_path), "input_sha256": manifest["input"]["sha256"],
            "task_id": manifest.get("task_id"), "page_count": manifest.get("page_count", 0),
            "visual_review_required": True,
            "images": [str(run / item["file"]) for item in manifest.get("pages", [])],
            "upload_preparation": manifest.get("upload_preparation"),
        }
        print(json.dumps(redact(result), ensure_ascii=False))
        return exit_code
    except Exception as exc:
        print(json.dumps(redact({
            "status": "failed", "code": getattr(exc, "code", "INPUT_OR_RENDER_ERROR"),
            "message": str(exc), "manifest": str(manifest_path) if manifest_path else None,
        }), ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
