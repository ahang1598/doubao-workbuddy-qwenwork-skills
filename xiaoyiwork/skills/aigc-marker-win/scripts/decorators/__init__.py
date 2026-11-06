"""Lazy compatibility exports for the AIGC decorator package.

Importing this package must not load optional dependencies for every supported
format.  The singleton exports remain available for callers of the original
cloud-sandbox API, but each one is created only when it is first requested.
"""
import importlib


_DECORATORS = {
    "audio_aigc_decorator": ("decorators.audio_decorator", "AudioAigcDecorator"),
    "docx_aigc_decorator": ("decorators.docx_decorator", "DocxAigcDecorator"),
    "excel_aigc_decorator": ("decorators.excel_decorator", "ExcelAigcDecorator"),
    "html_aigc_decorator": ("decorators.html_decorator", "HtmlAigcDecorator"),
    "image_aigc_decorator": ("decorators.image_decorator", "ImageAigcDecorator"),
    "md_aigc_decorator": ("decorators.md_decorator", "MdAigcDecorator"),
    "pdf_aigc_decorator": ("decorators.pdf_decorator", "PdfAigcDecorator"),
    "ppt_aigc_decorator": ("decorators.ppt_decorator", "PptAigcDecorator"),
    "video_aigc_decorator": ("decorators.video_decorator", "VideoAigcDecorator"),
}

__all__ = list(_DECORATORS)


def __getattr__(name: str):
    """Create legacy singleton exports without importing unrelated formats."""
    target = _DECORATORS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, class_name = target
    decorator_class = getattr(importlib.import_module(module_name), class_name)
    instance = decorator_class()
    globals()[name] = instance
    return instance
