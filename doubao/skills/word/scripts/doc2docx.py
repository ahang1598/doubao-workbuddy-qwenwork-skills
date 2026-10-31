import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from contextlib import suppress
from pathlib import Path


def libreoffice_candidate_ok(path):
    path = Path(path)
    return path.is_file() and (os.name == "nt" or os.access(path, os.X_OK))


def locate_soffice():
    if os.environ.get("DOC2DOCX_DISABLE_LIBREOFFICE"):
        return None

    choices = []
    for variable in (
        "DOC2DOCX_LIBREOFFICE",
        "LIBREOFFICE_PATH",
        "SOFFICE_PATH",
    ):
        value = os.environ.get(variable)
        if value:
            choices.append(value)

    commands = (
        ("soffice.com", "soffice", "libreoffice")
        if sys.platform == "win32"
        else ("soffice", "libreoffice")
    )
    choices.extend(filter(None, (shutil.which(command) for command in commands)))

    if sys.platform == "win32":
        for root in (
            os.environ.get("ProgramFiles"),
            os.environ.get("ProgramW6432"),
            os.environ.get("ProgramFiles(x86)"),
            os.environ.get("LOCALAPPDATA"),
        ):
            if root:
                program = Path(root) / "LibreOffice" / "program"
                choices.extend([program / "soffice.com", program / "soffice.exe"])

        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            program = Path(local_app_data) / "Programs" / "LibreOffice" / "program"
            choices.extend([program / "soffice.com", program / "soffice.exe"])

        choices.extend(
            [
                Path("C:/Program Files/LibreOffice/program/soffice.com"),
                Path("C:/Program Files/LibreOffice/program/soffice.exe"),
                Path("C:/Program Files (x86)/LibreOffice/program/soffice.com"),
                Path("C:/Program Files (x86)/LibreOffice/program/soffice.exe"),
            ]
        )

        import winreg

        for hive, key_name in (
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\LibreOffice\UNO\InstallPath"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\LibreOffice\UNO\InstallPath"),
            (
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\WOW6432Node\LibreOffice\UNO\InstallPath",
            ),
        ):
            with suppress(FileNotFoundError, OSError):
                with winreg.OpenKey(hive, key_name) as key:
                    install_path, _ = winreg.QueryValueEx(key, "")
                    choices.extend(
                        [
                            Path(install_path) / "soffice.com",
                            Path(install_path) / "soffice.exe",
                        ]
                    )
    elif sys.platform == "darwin":
        choices.extend(
            [
                Path("/Applications/LibreOffice.app/Contents/MacOS/soffice"),
                Path.home() / "Applications/LibreOffice.app/Contents/MacOS/soffice",
                Path("/opt/homebrew/bin/soffice"),
                Path("/usr/local/bin/soffice"),
                Path("/opt/local/bin/soffice"),
            ]
        )
    else:
        choices.extend(
            [
                Path("/usr/bin/soffice"),
                Path("/usr/local/bin/soffice"),
                Path("/snap/bin/libreoffice"),
                Path("/var/lib/flatpak/exports/bin/org.libreoffice.LibreOffice"),
            ]
        )

    seen = set()
    for candidate in choices:
        candidate = Path(candidate).expanduser()
        key = os.path.normcase(os.path.abspath(candidate))
        if key not in seen and libreoffice_candidate_ok(candidate):
            return str(candidate)
        seen.add(key)
    return None


def convert_with_libreoffice(source, out_dir, target="docx"):
    soffice = locate_soffice()
    if soffice is None:
        return None

    source = Path(source).expanduser().resolve()
    out_dir = Path(out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    profile = out_dir / "libreoffice-profile"
    profile.mkdir(exist_ok=True)
    result = subprocess.run(
        [
            soffice,
            f"-env:UserInstallation={profile.as_uri()}",
            "--headless",
            "--nologo",
            "--nodefault",
            "--nofirststartwizard",
            "--nolockcheck",
            "--convert-to",
            target,
            "--outdir",
            str(out_dir),
            str(source),
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,
    )
    output = out_dir / f"{source.stem}.{target.split(':', 1)[0]}"
    if result.returncode == 0 and output.exists():
        return output
    raise RuntimeError(
        result.stderr.decode("utf-8", errors="ignore")
        or result.stdout.decode("utf-8", errors="ignore")
        or "LibreOffice conversion failed"
    )


def convert_doc_to_docx(source, output):
    output = Path(output).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp_name:
        converted = convert_with_libreoffice(source, tmp_name)
        if converted is None:
            raise RuntimeError("LibreOffice is not available")
        shutil.copy2(converted, output)
    return output


def main():
    parser = argparse.ArgumentParser(description="Convert a .doc file to .docx")
    parser.add_argument("source")
    parser.add_argument("-o", "--output", required=True)
    args = parser.parse_args()

    source = Path(args.source).expanduser()
    if not source.is_file():
        parser.error(f"file does not exist: {source}")
    if source.suffix.lower() != ".doc":
        parser.error("source must be a .doc file")

    output = Path(args.output).expanduser()
    if output.suffix.lower() != ".docx":
        parser.error("output must be a .docx file")

    sys.stdout.write(f"{convert_doc_to_docx(source, output)}\n")


if __name__ == "__main__":
    main()
