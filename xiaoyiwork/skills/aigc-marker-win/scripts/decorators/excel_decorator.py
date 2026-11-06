"""Compatibility entry point for the shared OOXML document/template marker."""
from decorators.ooxml_decorator import OoxmlAigcDecorator


class ExcelAigcDecorator(OoxmlAigcDecorator):
    def __init__(self):
        super().__init__()
        self.name = "excel_aigc_decorator"
