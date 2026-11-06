"""PDF AIGC decorator."""
import io
import json
import os
import tempfile
from struct import iter_unpack
from typing import Union, cast

from pypdf import PdfReader, PdfWriter
from pypdf._utils import StreamType
from pypdf.generic import DictionaryObject, NameObject, TextStringObject

from decorators.common import get_aigc_signature, is_aigc_complete, parse_aigc_json, canonical_signature, AIGC_FIELDS


class RawTextStringObject(TextStringObject):
    """Custom TextStringObject that writes raw text without escaping."""

    def write_to_stream(
            self, stream: StreamType, encryption_key: Union[None, str, bytes] = None
    ) -> None:
        bytearr = self.get_encoded_bytes()
        stream.write(b"(")
        for c_ in iter_unpack("c", bytearr):
            c = cast(bytes, c_[0])
            stream.write(c)
        stream.write(b")")


class PdfAigcDecorator:
    """PDF AIGC decorator - adds hidden AIGC mark to PDF documents."""

    def __init__(self):
        self.name = "pdf_aigc_decorator"

    def decorate(self, file_path: str, content: str, add_visible_mark: bool = True):
        """Add AIGC mark to PDF file."""
        existing = self._get_aigc_data(file_path)
        raw = (PdfReader(file_path).metadata or {}).get('/AIGC')
        flat = False
        try:
            flat = isinstance(raw, str) and json.loads(raw) == existing
        except ValueError:
            pass
        if flat and existing and is_aigc_complete(existing) and all(k in existing for k in AIGC_FIELDS) and (not add_visible_mark or self._has_visible_mark(file_path)):
            print(f"  [PDF] AIGC mark complete, skipping")
            return
        try:
            aigc_signature = canonical_signature(existing, content)

            self._add_aigc_mark(file_path, {"AIGC": aigc_signature}, add_visible_mark)
            print(f"  [PDF] AIGC mark added successfully")
        except Exception as e:
            raise RuntimeError(f"PDF AIGC marking failed: {e}") from e

    def _has_visible_mark(self, file_path):
        reader = PdfReader(file_path)
        return bool(reader.pages) and all('内容由AI生成' in (page.extract_text() or '') for page in reader.pages)

    def _get_aigc_data(self, file_path: str) -> dict | None:
        """Read and parse AIGC metadata from PDF info dictionary."""
        try:
            with open(file_path, "rb") as f:
                reader = PdfReader(f)
                if reader.metadata:
                    for key, value in reader.metadata.items():
                        if key == "/AIGC":
                            return parse_aigc_json(str(value))
        except Exception:
            return None
        return None

    def _add_aigc_mark(self, input_path: str, data: dict, add_visible_mark: bool = True) -> None:
        """Add or update metadata and optional watermark in a PDF file."""
        # Read input PDF
        reader = PdfReader(input_path)
        writer = PdfWriter()

        # Copy all pages
        writer.clone_reader_document_root(reader)

        # Add visible watermark if requested
        if add_visible_mark:
            self._add_visible_watermark(writer, reader)

        # Ensure writer._info is a DictionaryObject
        if writer._info is None:
            writer._info = DictionaryObject()

        # Preserve existing metadata
        if reader.metadata:
            for key, value in reader.metadata.items():
                pdf_key = NameObject(key)
                if pdf_key not in writer._info:
                    writer._info[pdf_key] = TextStringObject(str(value))

        # Add/update new metadata
        for key, value in data.items():
            pdf_key = NameObject(f"/{key.lstrip('/')}")
            writer._info[pdf_key] = TextStringObject(str(value))

        # Write beside the source and atomically replace it. This is safe on
        # Windows and avoids leaving a truncated PDF after an interrupted write.
        target_dir = os.path.dirname(os.path.abspath(input_path))
        fd, tmp_path = tempfile.mkstemp(prefix=".aigc-", suffix=".pdf", dir=target_dir)
        os.close(fd)
        try:
            with open(tmp_path, "wb") as f:
                writer.write(f)
            os.replace(tmp_path, input_path)
        except Exception as e:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise Exception(f"PDF add metadata failed: {str(e)}") from e

    def _add_visible_watermark(self, writer: PdfWriter, reader: PdfReader):
        """Add visible '内容由AI生成' watermark to PDF pages using reportlab-generated watermark."""
        from pdf_extend.pdf_watermark import create_watermark_pdf

        watermark_by_size = {}
        temp_paths = []
        try:
            for page in writer.pages:
                if page.rotation:
                    page.transfer_rotation_to_content()
                width = float(page.cropbox.width)
                height = float(page.cropbox.height)
                size_key = (round(width, 3), round(height, 3))
                watermark_page = watermark_by_size.get(size_key)
                if watermark_page is None:
                    fd, watermark_path = tempfile.mkstemp(prefix="aigc-watermark-", suffix=".pdf")
                    os.close(fd)
                    temp_paths.append(watermark_path)
                    create_watermark_pdf(
                        output_path=watermark_path,
                        text="内容由AI生成",
                        font_size=10.5,
                        opacity=1.0,
                        angle=0,
                        color=(0, 0, 0),
                        position="bottom-center",
                        page_size=(width, height),
                    )
                    with open(watermark_path, "rb") as watermark_file:
                        watermark_page = PdfReader(io.BytesIO(watermark_file.read())).pages[0]
                    watermark_by_size[size_key] = watermark_page
                page.merge_translated_page(watermark_page, float(page.cropbox.left), float(page.cropbox.bottom), over=True)
        finally:
            for path in temp_paths:
                try:
                    os.remove(path)
                except OSError:
                    pass
