"""svg_lib.charts — productized chart modules.

Each module exposes a single `draw_<chart>(data, variant, palette, ...)` API.

Imports are best-effort so tests can run before all groups are done.
"""
__all__ = []

def _try(mod_name, attr):
    try:
        mod = __import__(f"charts.{mod_name}", fromlist=[attr])
        globals()[attr] = getattr(mod, attr)
        __all__.append(attr)
    except Exception:
        pass

for _m, _a in [
    ("boxplot", "draw_boxplot"),
    ("violin", "draw_violin"),
    ("funnel", "draw_funnel"),
    ("marimekko", "draw_marimekko"),
    ("nested_donut", "draw_nested_donut"),
    ("percent_grid", "draw_percent_grid"),
    ("pyramid", "draw_pyramid"),
    ("gantt", "draw_gantt"),
    ("matrix_heat", "draw_matrix_heat"),
    ("quadrant", "draw_quadrant"),
    ("calheat", "draw_calheat"),
]:
    _try(_m, _a)
