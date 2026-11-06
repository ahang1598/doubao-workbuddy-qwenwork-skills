"""Pandoc tool for md2doc skill."""
from time import perf_counter
import pypandoc

from config import CONFIG
from config import CONFIG_PATH
from logger import get_logger

LOG = get_logger("PandocTool")

config = CONFIG.md2doc_config


def create_docx(markdown_content: str, target_path: str, extra_args: list = None):
    """Convert markdown to docx using pypandoc."""
    if extra_args is None:
        extra_args = []

    pandoc_filters = config.get('md2doc_pandoc_filters', [])
    filters_args = []
    for f in pandoc_filters:
        filters_args.append(f"--lua-filter={CONFIG_PATH}/{f}")

    try:
        t0 = perf_counter()
        pypandoc.convert_text(
            markdown_content,
            "docx",
            encoding='utf-8',
            format="markdown",
            outputfile=target_path,
            extra_args=extra_args + filters_args,
            sandbox=True
        )
        LOG.debug(f"md2docx cost {perf_counter() - t0: .2f}s.")
    except Exception as e:
        message = f"md2doc failed: {str(e)}"
        LOG.error(f"message={message}")
        raise ValueError(message) from e
    return markdown_content
