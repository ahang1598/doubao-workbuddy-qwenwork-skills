"""
Inspection modules for Office document processing.
"""

from .core import PackageInspector
from .word import WordInspector
from .deck import DeckInspector
from .tracked import TrackedChangeAuditor

__all__ = [
    "PackageInspector",
    "WordInspector",
    "DeckInspector",
    "TrackedChangeAuditor",
]
