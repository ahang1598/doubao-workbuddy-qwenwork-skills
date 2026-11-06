#!/usr/bin/env python3
"""
AIGC Marker Skill - Add AIGC mark to existing documents

Usage:
    python main.py <file_path>

Arguments:
    file_path    Path to the target document, template, UOF, OFD, Markdown, XMind or media file
"""
import argparse
import hashlib
import importlib
import os
import json
import shutil
import tempfile
import sys
from pathlib import Path

# Add scripts directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

VERSION = (Path(__file__).resolve().parents[1] / "VERSION").read_text(encoding="utf-8").strip()

FORMAT_HANDLERS = {
    ".posm": ("decorators.pos_decorator", "PosAigcDecorator", "ProcessOn mind map"),
    ".posf": ("decorators.pos_decorator", "PosAigcDecorator", "ProcessOn flowchart"),
    ".dotx": ("decorators.ooxml_decorator", "OoxmlAigcDecorator", "Word template"),
    ".xltx": ("decorators.ooxml_decorator", "OoxmlAigcDecorator", "Excel template"),
    ".potx": ("decorators.ooxml_decorator", "OoxmlAigcDecorator", "PowerPoint template"),
    ".uot": ("decorators.uof_decorator", "UofAigcDecorator", "UOF document"),
    ".uott": ("decorators.uof_decorator", "UofAigcDecorator", "UOF document template"),
    ".uos": ("decorators.uof_decorator", "UofAigcDecorator", "UOF spreadsheet"),
    ".uost": ("decorators.uof_decorator", "UofAigcDecorator", "UOF spreadsheet template"),
    ".uop": ("decorators.uof_decorator", "UofAigcDecorator", "UOF presentation"),
    ".uopt": ("decorators.uof_decorator", "UofAigcDecorator", "UOF presentation template"),
    ".ofd": ("decorators.ofd_decorator", "OfdAigcDecorator", "OFD document"),
    ".xmind": ("decorators.xmind_decorator", "XmindAigcDecorator", "XMind workbook"),
    ".docx": ("decorators.ooxml_decorator", "OoxmlAigcDecorator", "Word document"),
    ".pdf": ("decorators.pdf_decorator", "PdfAigcDecorator", "PDF document"),
    ".xlsx": ("decorators.ooxml_decorator", "OoxmlAigcDecorator", "Excel file"),
    ".pptx": ("decorators.ooxml_decorator", "OoxmlAigcDecorator", "PowerPoint presentation"),
    ".md": ("decorators.md_decorator", "MdAigcDecorator", "Markdown file"),
    ".html": ("decorators.html_decorator", "HtmlAigcDecorator", "HTML file"),
    ".htm": ("decorators.html_decorator", "HtmlAigcDecorator", "HTML file"),
    ".jpg": ("decorators.image_decorator", "ImageAigcDecorator", "image"),
    ".jpeg": ("decorators.image_decorator", "ImageAigcDecorator", "image"),
    ".png": ("decorators.image_decorator", "ImageAigcDecorator", "image"),
    ".webp": ("decorators.image_decorator", "ImageAigcDecorator", "image"),
    ".heic": ("decorators.image_decorator", "ImageAigcDecorator", "image"),
    ".heif": ("decorators.image_decorator", "ImageAigcDecorator", "image"),
    ".wav": ("decorators.audio_decorator", "AudioAigcDecorator", "audio"),
    ".mp3": ("decorators.audio_decorator", "AudioAigcDecorator", "audio"),
    ".ogg": ("decorators.audio_decorator", "AudioAigcDecorator", "audio"),
    ".flac": ("decorators.audio_decorator", "AudioAigcDecorator", "audio"),
    ".m4a": ("decorators.audio_decorator", "AudioAigcDecorator", "audio"),
    ".mp4": ("decorators.video_decorator", "VideoAigcDecorator", "video"),
    ".flv": ("decorators.video_decorator", "VideoAigcDecorator", "video"),
    ".mkv": ("decorators.video_decorator", "VideoAigcDecorator", "video"),
    ".avi": ("decorators.video_decorator", "VideoAigcDecorator", "video"),
}


TEXT_FORMAT_EXTENSIONS = frozenset({".docx", ".dotx", ".xlsx", ".xltx", ".pptx", ".potx",
    ".uot", ".uott", ".uos", ".uost", ".uop", ".uopt", ".pdf", ".ofd", ".md", ".xmind", ".html", ".htm", ".posm", ".posf"})


def get_file_extension(file_path: str) -> str:
    """Get file extension in lowercase."""
    return Path(file_path).suffix.lower()


def validate_file(file_path: str) -> bool:
    """Validate if file exists and is supported."""
    if not os.path.isfile(file_path):
        print(f"Error: File not found: {file_path}")
        return False

    ext = get_file_extension(file_path)
    if ext not in FORMAT_HANDLERS:
        print(f"Error: Unsupported file format '{ext}'. Supported: {', '.join(FORMAT_HANDLERS)}")
        return False

    return True


def get_content_digest(file_path: str) -> str:
    """Return the SHA-256 digest of the file before marking."""
    digest = hashlib.sha256()
    with open(file_path, "rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def add_aigc_mark(file_path: str, add_visible_mark: bool = True):
    """Add AIGC mark to file based on its type."""
    ext = get_file_extension(file_path)
    handler = FORMAT_HANDLERS.get(ext)
    if handler is None:
        raise ValueError(f"Unsupported file format: {ext}")
    module_name, class_name, display_name = handler
    module = importlib.import_module(module_name)
    decorator_class = getattr(module, class_name)
    decorator = decorator_class()
    content = get_content_digest(file_path)
    if ext in TEXT_FORMAT_EXTENSIONS:
        from decorators.common import is_aigc_complete
        from decorators.text_metadata import GUIDE_EXTENSIONS, inspect_text_metadata
        fd, candidate = tempfile.mkstemp(prefix=".aigc-verify-", suffix=ext, dir=str(Path(file_path).parent))
        os.close(fd)
        try:
            shutil.copy2(file_path, candidate)
            decorator.decorate(candidate, content, add_visible_mark)
            if ext in GUIDE_EXTENSIONS:
                result = inspect_text_metadata(candidate)
                if not result['guide_storage_verified']:
                    print('AIGC_GUIDE_NOT_COVERED: legacy UOF1 XML; native marking only')
            elif not is_aigc_complete(decorator._get_aigc_data(candidate)):
                raise ValueError("written AIGC metadata could not be verified")
            if get_content_digest(candidate) != content:
                os.replace(candidate, file_path)
        finally:
            if os.path.exists(candidate):
                os.remove(candidate)
    else:
        decorator.decorate(file_path, content, add_visible_mark)
    print(f"[OK] AIGC mark added to {display_name}: {file_path}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Add AIGC marks to OOXML/UOF/PDF/OFD/Markdown/XMind/POSM/POSF/HTML/Image/Audio/Video files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python main.py document.docx
    python main.py report.pdf
    python main.py data.xlsx
    python main.py presentation.pptx
    python main.py photo.jpg
    python main.py image.png
    python main.py audio.mp3
    python main.py audio.m4a
    python main.py video.mp4
    python main.py video.avi
    python main.py document.docx --skip-visible  # Skip visible mark
        """
    )
    parser.add_argument('--version', action='version', version='aigc-marker-win ' + VERSION)
    parser.add_argument('--verify', action='store_true', help='Read-only text metadata verification against TC260-PG-20258A')
    parser.add_argument('file_path', help='Path to the target document, template, UOF, OFD, Markdown, XMind or media file')
    parser.add_argument('--skip-visible', action='store_true',
                        help='Skip adding visible AIGC mark, only add metadata')

    args = parser.parse_args()

    target_path = str(Path(args.file_path).expanduser().resolve())

    # Validate input file
    if not validate_file(target_path):
        sys.exit(1)

    print(f"Verifying AIGC metadata: {target_path}" if args.verify else f"Adding AIGC mark to: {target_path}")
    if args.skip_visible:
        print("Mode: Implicit metadata only (no visible mark)")

    try:
        if args.verify:
            from decorators.text_metadata import inspect_text_metadata
            result = inspect_text_metadata(target_path)
            print(json.dumps(result, ensure_ascii=False))
            if not result['guide_storage_verified']:
                sys.exit(3)
            print(f"AIGC_METADATA_VERIFIED: {target_path}")
            return
        # Add AIGC mark
        add_aigc_mark(target_path, add_visible_mark=not args.skip_visible)
        print(f"AIGC_MARKER_OK: {target_path}")

    except ModuleNotFoundError as e:
        print(f"AIGC_MARKER_FAILED: dependency_not_ready: {e.name}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        message = str(e)
        code = "ffmpeg_not_found" if "ffmpeg" in message.lower() and "not found" in message.lower() else "processing_error"
        print(f"AIGC_MARKER_FAILED: {code}: {message}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
