"""Compatibility entry point for the shared OOXML document/template marker."""
from decorators.ooxml_decorator import OoxmlAigcDecorator


class PptAigcDecorator(OoxmlAigcDecorator):
    def __init__(self):
        super().__init__()
        self.name = "ppt_aigc_decorator"
