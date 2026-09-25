import argparse
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

LOGGER = logging.getLogger(__name__)


def locate_soffice():
    choices = [
        shutil.which("soffice"),
        shutil.which("libreoffice"),
    ]
    found = [item for item in choices if item and Path(item).exists()]
    return found[0] if found else None


def docx_to_pdf(source, output):
    source = Path(source).resolve()
    output = Path(output).resolve()
    if not source.is_file():
        raise FileNotFoundError(f"DOCX file does not exist: {source}")
    if source.suffix.lower() != ".docx":
        raise ValueError(f"Input file must have a .docx extension: {source}")
    if output.suffix.lower() != ".pdf":
        raise ValueError(f"Output file must have a .pdf extension: {output}")

    soffice = locate_soffice()
    if soffice is None:
        raise RuntimeError("LibreOffice is required for DOCX to PDF conversion")

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp_name:
        tmp = Path(tmp_name)
        profile = tmp / "libreoffice-profile"
        profile.mkdir()
        result = subprocess.run(
            [
                soffice,
                f"-env:UserInstallation={profile.as_uri()}",
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                str(tmp),
                str(source),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        converted = tmp / f"{source.stem}.pdf"
        if result.returncode != 0 or not converted.is_file():
            message = result.stderr.strip() or result.stdout.strip()
            raise RuntimeError(message or "LibreOffice conversion failed")
        shutil.copy2(converted, output)
    return output


def main():
    parser = argparse.ArgumentParser(description="Convert a DOCX file to PDF.")
    parser.add_argument("docx_name", help="source DOCX file")
    parser.add_argument("--output", required=True, help="target PDF file")
    args = parser.parse_args()

    try:
        output = docx_to_pdf(args.docx_name, args.output)
    except (OSError, ValueError, RuntimeError) as error:
        LOGGER.error("%s", error)
        return 1
    print(f"Wrote PDF to {output}")
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    raise SystemExit(main())
