"""SVG → independent Slides shapes, paths, text and local SVG composites."""

from __future__ import annotations

from ._atomizer import atomize_svg_to_slide
from ._diagnostics import inspect_svg
from ._config import (  # noqa: F401  (_CFG re-exported config dict)
    _CFG,
    set_drop_background,
    set_drop_micro_gray,
    set_drop_text_below,
    set_mapping,
    set_font_metrics,
    set_min_slide_font_size,
    set_subtitle_relax,
)
from ._convert import (
    convert_circle,
    convert_ellipse,
    convert_line,
    convert_path,
    convert_polygon,
    convert_polyline,
    convert_rect,
    convert_text,
)
from ._scale import s2l_x, s2l_y
from ._serialize import serialize_slide
from ._compose import compose_slide
from ._publish import publish_slide
from ._merge import merge_atomized_slide
from ._native import native_bullets, native_line, native_table, native_text, page_frame


def slide_help() -> str:
    """Signatures + docstrings of the page helpers (generated from the code, never drifts)."""
    import inspect

    lines = [
        "from scripts.svg_lib.atomize_svg_to_slide import publish_slide, page_frame, native_bullets, "
        "native_text, native_line, native_table",
        "Flow: page = page_frame(title, native_bullets(...), ...); "
        "publish_slide(page, chart_slide(...) / d.to_slide(...), presentation=..., page=N)",
    ]
    for fn in (publish_slide, page_frame, native_bullets, native_text, native_line, native_table):
        doc = (inspect.getdoc(fn) or "").replace("\n", "\n    ")
        lines.append(f"\n{fn.__name__}{inspect.signature(fn)}\n    {doc}")
    return "\n".join(lines)


__all__ = [
    "slide_help",
    "inspect_svg",
    "atomize_svg_to_slide",
    "serialize_slide",
    "compose_slide",
    "publish_slide",
    "merge_atomized_slide",
    "native_table",
    "native_bullets",
    "page_frame",
    "native_text",
    "native_line",
    "set_mapping",
    "set_font_metrics",
    "set_drop_background",
    "set_drop_micro_gray",
    "set_drop_text_below",
    "set_min_slide_font_size",
    "set_subtitle_relax",
    "s2l_x",
    "s2l_y",
    "convert_rect",
    "convert_line",
    "convert_text",
    "convert_path",
    "convert_circle",
    "convert_ellipse",
    "convert_polygon",
    "convert_polyline",
]


_ELSEWHERE = {
    # name → where it actually lives (the import a caller should write)
    "chart_slide": "from scripts.gen_svg_charts import chart_slide",
    "chart_help": "from scripts.gen_svg_charts import chart_help",
    "chart_fit": "from scripts.gen_svg_charts import chart_fit",
    "publish_slide": "from scripts.svg_lib.atomize_svg_to_slide import publish_slide",
    "native_text": "from scripts.svg_lib.atomize_svg_to_slide import native_text",
    "native_table": "from scripts.svg_lib.atomize_svg_to_slide import native_table",
    "native_bullets": "from scripts.svg_lib.atomize_svg_to_slide import native_bullets",
    "page_frame": "from scripts.svg_lib.atomize_svg_to_slide import page_frame",
    "native_line": "from scripts.svg_lib.atomize_svg_to_slide import native_line",
    "compose_slide": "from scripts.svg_lib.atomize_svg_to_slide import compose_slide",
    "Drawing": "from scripts.svg_lib.svg_drawing import Drawing",
    "drawing_help": "from scripts.svg_lib.svg_drawing import drawing_help",
    "svg_at": "svg_at is a Drawing method: d = Drawing(w, h); d.svg_at(at, svg, size=...)",
    "box_at": "box_at is a Drawing method: d.box_at(at, text, font_size=...)",
    "text_at": "text_at is a Drawing method: d.text_at(at, text, font_size=...)",
    "arrow": "arrow is a Drawing method: d.arrow(node_a, node_b)",
    "relation_help": "from scripts.gen_svg_relations import relation_help",
    "make_relation_atomized": "from scripts.gen_svg_relations import make_relation_atomized",
}


def __getattr__(name):
    """A name imported from the neighbouring module resolves to the real one (the wrong import line still works)."""
    hint = _ELSEWHERE.get(name)
    if hint and hint.startswith("from "):
        import importlib

        module, attr = hint[5:].split(" import ")
        return getattr(importlib.import_module(module), attr)
    if hint:
        raise ImportError(f"{name!r} is not importable from {__name__}; {hint}")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
