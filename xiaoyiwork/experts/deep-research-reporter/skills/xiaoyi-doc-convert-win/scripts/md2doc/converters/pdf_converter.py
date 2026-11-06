"""PDF converter for md2doc skill."""
import os
import subprocess
import tempfile
from time import perf_counter

from converters.converter import Converter
from logger import get_logger

LOG = get_logger("PdfConverter")


class PdfConverter(Converter):
    """HTML to PDF converter via LibreOffice (soffice)."""

    def __init__(self):
        super().__init__(name="pdf")

    def convert(self, content: str, target_path: str, **kwargs):
        request_id = kwargs.get("request_id", "")
        t0 = perf_counter()

        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".html", prefix="md2pdf_")
        try:
            with os.fdopen(tmp_fd, 'w', encoding='utf-8') as f:
                f.write(content)

            cmd = [
                "soffice",
                "--headless",
                "--convert-to", "pdf",
                "--outdir", os.path.dirname(tmp_path) or ".",
                tmp_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            expected_output = os.path.splitext(tmp_path)[0] + ".pdf"
            if os.path.exists(expected_output):
                os.replace(expected_output, target_path)

            LOG.info(f"request_id={request_id}, md2pdf done, cost {perf_counter() - t0:.2f}s.")
        except subprocess.CalledProcessError as e:
            message = f"soffice pdf conversion failed: {e.stderr}"
            LOG.error(f"request_id=[{request_id}], message={message}")
            raise ValueError(message) from e
        except Exception as e:
            message = f"pdf conversion failed: {str(e)}"
            LOG.error(f"request_id=[{request_id}], message={message}")
            raise ValueError(message) from e
        finally:
            for suffix in [".html", ".pdf"]:
                temp_file = os.path.splitext(tmp_path)[0] + suffix
                if os.path.exists(temp_file) and temp_file != target_path:
                    try:
                        os.remove(temp_file)
                    except OSError:
                        pass


pdf_converter = PdfConverter()
