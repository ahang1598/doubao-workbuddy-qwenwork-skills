"""Convert an Office document to PDF through qwenwork's remote capability tool.

Usage: python3 office_to_pdf.py <input office document> <output pdf>
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


SCRIPT_DIRECTORY = Path(__file__).resolve().parent
if str(SCRIPT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIRECTORY))
from _cloud_runtime import remote_runtime_required, resolve_qwenwork_cli
from _execution_route import (
    BackendFailure,
    execute_with_fallback,
    execution_mode,
)


OFFICE_SUFFIXES = {
    ".doc",
    ".docx",
    ".odp",
    ".ods",
    ".odt",
    ".ppt",
    ".pptx",
    ".xls",
    ".xlsx",
}
def _remote_runtime_required():
    return remote_runtime_required()


def _resolve_qwenwork_cli(
    script_path: Path | None = None,
    platform_name: str | None = None,
):
    return resolve_qwenwork_cli(
        script_path=script_path,
        platform_name=platform_name,
        required=False,
    )


def _local_runtime_ready():
    return shutil.which("soffice") is not None


def _cloud_runtime_ready():
    try:
        return _resolve_qwenwork_cli() is not None
    except RuntimeError:
        return False


def _try_remote_runtime(input_path, output_path):
    """Delegate routing, authentication, and file transfer to qwenwork CLI."""
    cli = _resolve_qwenwork_cli()
    if cli is None:
        return None
    try:
        result = subprocess.run(
            [
                cli,
                "tools",
                "document",
                "convert",
                input_path.resolve().as_posix(),
                "--to",
                "pdf",
                "--save",
                output_path.resolve().as_posix(),
                "--deadline",
                "10m",
                "-o",
                "json",
            ],
            capture_output=True,
            text=True,
            timeout=620,
            check=False,
        )
        if result.returncode == 2:
            return None
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "remote conversion failed").strip()
            raise RuntimeError(detail[:500])
        if not output_path.is_file() or output_path.stat().st_size < 5:
            raise RuntimeError("document runtime completed without a PDF")
        with output_path.open("rb") as output_file:
            if output_file.read(5) != b"%PDF-":
                raise RuntimeError("document runtime output is not a PDF")
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print("Warning: remote document runtime failed: " + str(exc)[:500], file=sys.stderr)
        return False
    print(f"Converted Office document through qwenwork document runtime: {output_path}")
    return True


def _convert_locally(input_path, output_path):
    soffice = shutil.which("soffice")
    if not soffice:
        raise RuntimeError("LibreOffice soffice is unavailable")
    with tempfile.TemporaryDirectory(prefix="office-to-pdf-") as directory:
        work_directory = Path(directory)
        profile_directory = work_directory / "libreoffice-profile"
        profile_directory.mkdir()
        result = subprocess.run(
            [
                soffice,
                f"-env:UserInstallation={profile_directory.as_uri()}",
                "--headless",
                "--nodefault",
                "--norestore",
                "--nolockcheck",
                "--nofirststartwizard",
                "--convert-to",
                "pdf",
                "--outdir",
                directory,
                str(input_path),
            ],
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
        generated = work_directory / f"{input_path.stem}.pdf"
        if result.returncode != 0 or not generated.is_file():
            detail = (result.stderr or result.stdout or "conversion failed").strip()
            raise RuntimeError(detail[:500])
        temporary = output_path.with_name(f".{output_path.name}.tmp")
        shutil.copy2(generated, temporary)
        temporary.replace(output_path)
    print(f"Converted Office document locally: {output_path}")


def _valid_pdf(path):
    if not path.is_file() or path.stat().st_size < 5:
        return False
    with path.open("rb") as output_file:
        return output_file.read(5) == b"%PDF-"


def main(argv):
    if len(argv) != 3:
        print("Usage: python3 office_to_pdf.py <input office document> <output pdf>")
        return 2
    input_path = Path(argv[1]).expanduser().resolve()
    output_path = Path(argv[2]).expanduser().resolve()
    if not input_path.is_file() or input_path.suffix.lower() not in OFFICE_SUFFIXES:
        print(f"Error: unsupported Office input: {input_path}", file=sys.stderr)
        return 2
    if output_path.suffix.lower() != ".pdf":
        print(f"Error: output must be a PDF path: {output_path}", file=sys.stderr)
        return 2
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        def run_local():
            try:
                _convert_locally(input_path, output_path)
            except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
                raise BackendFailure("LOCAL_OFFICE_CONVERT_FAILED", retryable=True) from exc
            return output_path

        def run_cloud():
            remote = _try_remote_runtime(input_path, output_path)
            if not remote:
                raise BackendFailure("CLOUD_OFFICE_CONVERT_FAILED", retryable=True)
            return output_path

        _, report = execute_with_fallback(
            mode=execution_mode(),
            local_ready=_local_runtime_ready,
            cloud_ready=_cloud_runtime_ready,
            run_local=run_local,
            run_cloud=run_cloud,
            validate=_valid_pdf,
        )
        report.emit()
    except (BackendFailure, OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
