#!/usr/bin/env python3
"""将旧版二进制 PPT 规范化为受支持的只读或可编辑格式。"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from _cloud_runtime import (
    CloudRuntimeError,
    cloud_runtime_ready,
    document_convert_target_supported,
    run_document_tool,
)
from _execution_route import (
    BackendFailure,
    BackendUnavailable,
    ExecutionMode,
    ExecutionReport,
    execute_with_fallback,
    execution_mode,
)
from oxml.lo_bridge import launch_soffice


def _valid_pdf(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size < 8:
        return False
    with path.open("rb") as source:
        return source.read(5) == b"%PDF-"


def _valid_pptx(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size < 64 or not zipfile.is_zipfile(path):
        return False
    try:
        with zipfile.ZipFile(path) as archive:
            names = frozenset(archive.namelist())
    except (OSError, zipfile.BadZipFile):
        return False
    return "[Content_Types].xml" in names and "ppt/presentation.xml" in names


def _publish(source: Path, output: Path) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    staged = output.with_name(f".{output.name}.staged")
    shutil.copyfile(source, staged)
    staged.replace(output)
    return output


def _convert_locally(input_path: Path, output_path: Path, target: str) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(
            prefix="legacy-ppt-local-", dir=str(output_path.parent)
        ) as temporary:
            target_dir = Path(temporary)
            result = launch_soffice(
                [
                    "--headless",
                    "--convert-to",
                    target,
                    "--outdir",
                    str(target_dir),
                    str(input_path.resolve()),
                ],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
            )
            if result.returncode != 0:
                raise BackendFailure("LOCAL_CONVERSION_FAILED", fallback_allowed=True)
            expected = target_dir / f"{input_path.stem}.{target}"
            candidates = sorted(target_dir.glob(f"*.{target}"))
            generated = (
                expected
                if expected.is_file()
                else (candidates[0] if len(candidates) == 1 else None)
            )
            validator = _valid_pdf if target == "pdf" else _valid_pptx
            if generated is None or not validator(generated):
                raise BackendFailure("LOCAL_CONVERSION_OUTPUT_INVALID", fallback_allowed=True)
            return _publish(generated, output_path)
    except BackendFailure:
        raise
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise BackendFailure("LOCAL_CONVERSION_FAILED", fallback_allowed=True) from exc


def _convert_in_cloud(input_path: Path, output_path: Path, target: str) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    validator = _valid_pdf if target == "pdf" else _valid_pptx
    try:
        with tempfile.TemporaryDirectory(
            prefix="legacy-ppt-cloud-", dir=str(output_path.parent)
        ) as temporary:
            generated = Path(temporary) / output_path.name
            run_document_tool(
                ("document", "convert"),
                input_path,
                save_path=generated,
                flags=(("to", target),),
            )
            if not validator(generated):
                raise BackendFailure("CLOUD_CONVERSION_OUTPUT_INVALID", fallback_allowed=True)
            return _publish(generated, output_path)
    except CloudRuntimeError as exc:
        if target == "pptx" and exc.code in {
            "CLOUD_REQUEST_INVALID",
            "INVALID_ARGUMENT",
            "OPERATION_UNAVAILABLE",
            "PARAMETER_INVALID",
        }:
            raise BackendFailure("CLOUD_TARGET_UNAVAILABLE", fallback_allowed=True) from exc
        raise BackendFailure(exc.code, fallback_allowed=exc.fallback_allowed) from exc


def _convert_pdf_in_cloud(input_path: Path, output_path: Path) -> Path:
    return _convert_in_cloud(input_path, output_path, "pdf")


def _convert_pptx_in_cloud(input_path: Path, output_path: Path) -> Path:
    return _convert_in_cloud(input_path, output_path, "pptx")


def _registered_host_converter() -> Path | None:
    configured = os.environ.get("QWENWORK_PPTX_CONVERTER_PATH", "").strip()
    if not configured:
        return None
    candidate = Path(configured).expanduser()
    if (
        not candidate.is_absolute()
        or not candidate.is_file()
        or not os.access(candidate, os.X_OK)
    ):
        return None
    return candidate.resolve()


def _convert_with_host_bridge(input_path: Path, output_path: Path) -> Path:
    converter = _registered_host_converter()
    if converter is None:
        raise BackendUnavailable("HOST_CONVERSION_BRIDGE_UNAVAILABLE")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(
            prefix="legacy-ppt-bridge-", dir=str(output_path.parent)
        ) as temporary:
            generated = Path(temporary) / output_path.name
            result = subprocess.run(
                [
                    str(converter),
                    "--input",
                    str(input_path.resolve()),
                    "--output",
                    str(generated.resolve()),
                    "--target",
                    "pptx",
                ],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=300,
                check=False,
            )
            if result.returncode != 0:
                raise BackendFailure("HOST_CONVERSION_BRIDGE_FAILED", fallback_allowed=True)
            if not _valid_pptx(generated):
                raise BackendFailure(
                    "HOST_CONVERSION_BRIDGE_OUTPUT_INVALID", fallback_allowed=True
                )
            return _publish(generated, output_path)
    except BackendFailure:
        raise
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise BackendFailure("HOST_CONVERSION_BRIDGE_FAILED", fallback_allowed=True) from exc


def prepare_pdf(input_path: Path, output_path: Path) -> ExecutionReport:
    _, report = execute_with_fallback(
        mode=execution_mode(),
        local_ready=lambda: shutil.which("soffice") is not None,
        cloud_ready=cloud_runtime_ready,
        run_local=lambda: _convert_locally(input_path, output_path, "pdf"),
        run_cloud=lambda: _convert_pdf_in_cloud(input_path, output_path),
        validate=_valid_pdf,
    )
    report.emit()
    return report


def prepare_pptx(input_path: Path, output_path: Path) -> ExecutionReport:
    mode = execution_mode()
    cloud_supported = (
        False
        if mode == ExecutionMode.LOCAL_REQUIRED
        else document_convert_target_supported("pptx")
    )
    if mode == ExecutionMode.CLOUD_REQUIRED and not cloud_supported:
        raise BackendUnavailable("LEGACY_PPT_CLOUD_TARGET_UNAVAILABLE")

    candidates = []
    if mode != ExecutionMode.LOCAL_REQUIRED and cloud_supported:
        candidates.append(
            (
                "cloud",
                "CLOUD_CAPABILITY_ADVERTISED",
                lambda: _convert_pptx_in_cloud(input_path, output_path),
            )
        )
    if mode != ExecutionMode.CLOUD_REQUIRED:
        if _registered_host_converter() is not None:
            candidates.append(
                (
                    "local",
                    "HOST_BRIDGE_REGISTERED",
                    lambda: _convert_with_host_bridge(input_path, output_path),
                )
            )
        if shutil.which("soffice") is not None:
            candidates.append(
                (
                    "local",
                    "LIBREOFFICE_AVAILABLE",
                    lambda: _convert_locally(input_path, output_path, "pptx"),
                )
            )
    if not candidates:
        raise BackendUnavailable("LEGACY_PPT_FAST_PATHS_EXHAUSTED")

    initial_backend = candidates[0][0]
    failures = []
    for backend, selection_reason, run in candidates:
        try:
            result = run()
            if not _valid_pptx(result):
                raise BackendFailure("OUTPUT_VALIDATION_FAILED", fallback_allowed=True)
        except BackendFailure as exc:
            if not exc.fallback_allowed:
                raise
            failures.append(exc.code)
            continue
        report = ExecutionReport(
            backend=backend,
            initial_backend=initial_backend,
            fallback_used=bool(failures),
            fallback_reason=",".join(failures),
            selection_reason=selection_reason,
        )
        report.emit()
        return report
    raise BackendFailure(
        "LEGACY_PPT_FAST_PATHS_EXHAUSTED",
        fallback_allowed=True,
        message=",".join(failures),
    )


def _default_output(input_path: Path, target: str) -> Path:
    return input_path.with_suffix(f".{target}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Normalize a legacy binary .ppt into PDF or editable PPTX."
    )
    parser.add_argument("input", type=Path, help="Input legacy .ppt file")
    parser.add_argument("--to", choices=("pdf", "pptx"), required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    input_path = args.input.expanduser().resolve()
    output_path = (args.output or _default_output(input_path, args.to)).expanduser().resolve()
    if input_path.suffix.lower() != ".ppt" or not input_path.is_file():
        parser.error("input must be an existing legacy .ppt file")
    if input_path == output_path:
        parser.error("output must differ from input")

    try:
        if args.to == "pdf":
            prepare_pdf(input_path, output_path)
        else:
            prepare_pptx(input_path, output_path)
    except BackendFailure as exc:
        exploration_allowed = exc.code == "LEGACY_PPT_FAST_PATHS_EXHAUSTED"
        print(
            json.dumps(
                {
                    "status": "error",
                    "code": exc.code,
                    "target": args.to,
                    "bounded_capability_discovery_allowed": exploration_allowed,
                },
                separators=(",", ":"),
            ),
            file=sys.stderr,
        )
        return 3

    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
