"""Backward-compatible, lazy exports for the original marker module."""
import decorators as _decorators
from decorators.common import DEFAULT_CUSTOM_PROPERTY_FMTID, generate_sha256, get_aigc_signature


_LAZY_EXPORTS = set(_decorators.__all__)
_CLASS_EXPORTS = {
    "AudioAigcDecorator": ("decorators.audio_decorator", "AudioAigcDecorator"),
    "DocxAigcDecorator": ("decorators.docx_decorator", "DocxAigcDecorator"),
    "ExcelAigcDecorator": ("decorators.excel_decorator", "ExcelAigcDecorator"),
    "HtmlAigcDecorator": ("decorators.html_decorator", "HtmlAigcDecorator"),
    "ImageAigcDecorator": ("decorators.image_decorator", "ImageAigcDecorator"),
    "MdAigcDecorator": ("decorators.md_decorator", "MdAigcDecorator"),
    "PdfAigcDecorator": ("decorators.pdf_decorator", "PdfAigcDecorator"),
    "PptAigcDecorator": ("decorators.ppt_decorator", "PptAigcDecorator"),
    "VideoAigcDecorator": ("decorators.video_decorator", "VideoAigcDecorator"),
}
__all__ = [
    "DEFAULT_CUSTOM_PROPERTY_FMTID",
    "RawTextStringObject",
    "generate_sha256",
    "get_aigc_signature",
    *_CLASS_EXPORTS,
    *_decorators.__all__,
]


def __getattr__(name: str):
    if name == "RawTextStringObject":
        from decorators.pdf_decorator import RawTextStringObject

        return RawTextStringObject
    target = _CLASS_EXPORTS.get(name)
    if target is not None:
        import importlib

        module_name, class_name = target
        value = getattr(importlib.import_module(module_name), class_name)
        globals()[name] = value
        return value
    if name in _LAZY_EXPORTS:
        value = getattr(_decorators, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
