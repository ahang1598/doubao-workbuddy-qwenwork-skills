#!/usr/bin/env python3
"""WPS-channel DOCX rendering via lark-cli; PDF/PNG evidence, not visual approval.

render creates one isolated conversion run and all page PNGs.
No HTTP client, compression, automatic retries, TOC update or document repair
is implemented here.
Exit codes: 0 = operation succeeded; 1 = not succeeded (including pending tasks).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile

SCHEMA_VERSION = 1
MANIFEST_NAME = "render-manifest.json"
MAX_PAGE_PIXELS = 50_000_000  # Resource limit, not a document-quality threshold.


class RenderError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


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
        value = re.sub(r"(https?://[^\s?\"']+)\?[^\s\"']+", r"\1?<redacted>", value)
        return re.sub(r"(?i)\bBearer\s+\S+", "Bearer <redacted>", value)
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


def pdf_module():
    try:
        import pymupdf
    except ImportError as exc:
        raise RenderError(
            "DEPENDENCY_MISSING", "请用当前 Python 安装 requirements.txt 中的 PyMuPDF。"
        ) from exc
    return pymupdf


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
