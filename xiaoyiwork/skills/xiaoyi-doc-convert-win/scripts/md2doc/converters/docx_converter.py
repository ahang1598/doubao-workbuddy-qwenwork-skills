"""DOCX converter for md2doc skill."""
from converters.converter import Converter
from utils.pandoc_args_utils import get_pandoc_extra_args
from logger import get_logger
from utils.pandoc_tool import create_docx

LOG = get_logger("DocxConverter")


class DocxConverter(Converter):
    """Converter for generating docx files."""

    def __init__(self):
        super().__init__(name="docx")

    def convert(self, content: str, target_path: str, **kwargs):
        LOG.info(f"starting docx conversion")

        # Get configurable extra args
        extra_args = get_pandoc_extra_args()
        LOG.info(f"using pandoc extra args: {extra_args}")

        create_docx(content, target_path, extra_args)


docx_converter = DocxConverter()
