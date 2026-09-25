"""Supported relation-diagram skins.

The relation generator currently exposes 11 diagram presets only. This package
keeps generic/shared skins and the registered visual themes used by those
presets; obsolete diagram-specific skins are intentionally not exported.
"""
from __future__ import annotations

from ._base import Skin
from .napkin import NapkinSkin, NAPKIN
from .editorial import EditorialSkin, EDITORIAL
from .editorial_atelier import (
    EditorialAtelierSkin, EDITORIAL_ATELIER,
    BONE_RUST, HERO_CANVAS, EMBED_CANVAS, CanvasProfile,
)
from .strategic_briefing import (
    StrategicBriefingSkin, STRATEGIC_BRIEFING, STRATEGIC_NAVY,
)
from .ib_editorial import (
    IBEditorialSkin, IB_EDITORIAL, IIB_PASTEL,
)
from .saas_product import (
    SaaSProductSkin, SAAS_PRODUCT, SAAS_NIGHT,
)

__all__ = [
    # Protocol
    "Skin",
    # Singleton skins (推荐入口)
    "NAPKIN", "EDITORIAL", "EDITORIAL_ATELIER",
    "STRATEGIC_BRIEFING", "IB_EDITORIAL", "SAAS_PRODUCT",
    # Class 版
    "NapkinSkin", "EditorialSkin", "EditorialAtelierSkin",
    "StrategicBriefingSkin", "IBEditorialSkin", "SaaSProductSkin",
    # editorial_atelier · palette + canvas
    "BONE_RUST", "HERO_CANVAS", "EMBED_CANVAS", "CanvasProfile",
    # new palettes
    "STRATEGIC_NAVY", "IIB_PASTEL", "SAAS_NIGHT",
]
