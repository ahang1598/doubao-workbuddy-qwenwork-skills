"""Consulting exhibit charts (strategy-and-analysis): the chart area of a slide, native Slides output.

The page itself (title, subtitle, text, KPI cards, footnotes, source, <note>) is hand-written slide XML; the exhibit
draws only the chart into the box the XML leaves free:

    from scripts.svg_lib.exhibit import *
    ex = Exhibit(w=880, h=340, palette="mckinsey_blue")   # box size on the slide (px == pt)
    main, side = ex.split(0.32)
    with ex.panel(main): ...                                # labels / callouts placed automatically at output
    frag = ex.to_slide(x=40, y=120)                         # check() + atomize; publish_slide(page_xml, frag, ...)

Start with exhibit_help() for the recipe list, exhibit_help("<recipe>") for a recipe.
"""

from ._axes import Axes, NAxes, nice_ticks
from ._marks import (area_stack, axis_arrow_title, badge, big_number, bubbles, columns, diamond, dim_arrow, dot_waffle,
                     gap_fill, hstack100, leader_label, legend, missing_band, num_dot, polyline, size_legend, span_bracket,
                     stacked_bar, vbracket, venn3, vstack100, waterfall, band, dashed_box, quadrants, trend,
                     cagr_arrow, total_diff, level_diff, relate)
from ._extra import bullet, bump, dot_range, fan, funnel, pareto, profit_pool, slope, small_multiples, treemap
from ._combo import panel_heads, period_notes, period_x, shared_time
from ._expand import expand, expand_panels, plain_bars, small_rows
from ._kpi import check_mix, check_stock, ratio, fmt_delta, fmt_value, gap_vs_baseline, merge_metrics, remaining_risk, metric_rows, on_page, status, vs_target, yoy
from ._frame import Sections, image_size, set_logo, set_palette, set_profile, is_research, is_speech, deck_palette, logo_xml, brace, contents, publish_contents_and_navs, dashboard, exec_summary, review_summary, swot_matrix, frame, kpis, kpi_cards, linked_panel, points, republish_xml, takeaway, text_table
from ._page import Exhibit
from ._glossary import glossary_page
from ._native import NativeChart
from ._palette import brand_palette, roles
from ._ibcs import chart_head, ibcs_bars, ibcs_bridge, ibcs_columns, pace, scale_marker, scen_bar, scen_legend, wbr_trend
from ._more import donut, lines, marimekko, sankey, timeline, tornado
from ._place import callout, place_label
from ._composite import layered_area, pie_of_pie, ridge_point, speech_note
from ._table import Bar, Box, Diverge, Dumbbell, Harvey, Heat, Label, Level, Note, Range, Rank, Scen, Spark, Status, Text, Variance, row_table, score_options, top_n
from ._text import fmt, tw, wrap
from ._layouts import (image_inset, icon_grid, person_grid, body_w, column_boxes, table_block, kpi_strip, kpi_charts_page, columns_page, diagram_page, mixed_columns_page, dot_bullets, key_takeaways, kv_rows, note_box, numbered_steps,
                       rail_x, section_head, stat_stack, LINE_ART_PROMPT, LINE_ART_PROMPT_ZH,
                       DIAGRAM_PROMPTS, DIAGRAM_PROMPTS_ZH, diagram_prompt)

__all__ = ["image_size", "image_inset",
    "panel_heads", "period_notes", "period_x", "shared_time", "expand", "expand_panels", "plain_bars", "small_rows",
    "Exhibit", "NativeChart", "Axes", "NAxes", "nice_ticks", "row_table", "Label", "Text", "Bar", "Dumbbell", "Range", "Heat", "Harvey", "Level", "Status", "Diverge", "Box", "Note", "Rank",
    "bubbles", "columns", "stacked_bar", "waterfall", "polyline", "area_stack", "gap_fill", "hstack100", "vstack100",
    "dot_waffle", "venn3", "missing_band", "badge", "num_dot", "dim_arrow", "span_bracket", "vbracket", "big_number", "leader_label",
    "diamond", "legend", "size_legend", "axis_arrow_title", "callout", "place_label", "fmt", "tw", "wrap",
    "lines", "donut", "marimekko", "timeline", "sankey", "tornado",
    "frame", "Sections", "set_logo", "set_palette", "set_profile", "is_research", "is_speech", "deck_palette", "logo_xml", "republish_xml", "points", "kpis", "kpi_cards", "exec_summary", "review_summary", "swot_matrix", "contents", "publish_contents_and_navs", "dashboard", "text_table", "brace", "takeaway", "linked_panel", "score_options", "top_n", "roles", "slope", "bullet", "pareto", "small_multiples", "fan", "treemap",
    "profit_pool", "bump", "dot_range", "funnel",
    "band", "dashed_box", "quadrants", "trend", "cagr_arrow", "total_diff", "level_diff", "relate",
    "pie_of_pie", "layered_area", "speech_note", "ridge_point",
    "vs_target", "yoy", "status", "fmt_delta", "fmt_value", "metric_rows", "merge_metrics", "on_page", "check_mix", "check_stock", "ratio",
    "gap_vs_baseline", "remaining_risk",
    "Scen", "Spark", "Variance", "brand_palette", "scen_bar", "scen_legend", "ibcs_columns", "ibcs_bars", "ibcs_bridge", "wbr_trend", "pace",
    "scale_marker", "chart_head",
    "exhibit_help",
    "glossary_page", "key_takeaways", "icon_grid", "person_grid", "stat_stack", "section_head", "kv_rows", "note_box", "dot_bullets", "numbered_steps",
    "columns_page", "mixed_columns_page", "diagram_page", "table_block", "kpi_strip", "kpi_charts_page", "column_boxes", "rail_x", "body_w", "LINE_ART_PROMPT", "LINE_ART_PROMPT_ZH",
    "DIAGRAM_PROMPTS", "DIAGRAM_PROMPTS_ZH", "diagram_prompt",
]


def _track():
    """Record which chart functions a page script calls (publish compares them with the plan row's recipe)."""
    import functools
    from . import _page
    g = globals()
    skip = {"frame", "set_profile", "is_research", "is_speech", "Exhibit", "fmt", "tw", "wrap", "roles", "exhibit_help", "republish_xml", "Axes", "NAxes",
            "vs_target", "yoy", "status", "fmt_delta", "fmt_value", "metric_rows", "merge_metrics", "on_page",
            "check_mix", "check_stock", "ratio", "gap_vs_baseline", "remaining_risk", "nice_ticks", "NativeChart", "brand_palette", "image_size", "image_inset",
            "rail_x", "body_w", "column_boxes", "LINE_ART_PROMPT", "LINE_ART_PROMPT_ZH", "DIAGRAM_PROMPTS",
            "DIAGRAM_PROMPTS_ZH", "diagram_prompt",
            "glossary_page", "publish_contents_and_navs", "key_takeaways", "stat_stack", "section_head", "kv_rows", "note_box", "dot_bullets", "numbered_steps",
            "columns_page", "mixed_columns_page", "diagram_page", "table_block", "kpi_strip", "kpi_charts_page", "icon_grid", "person_grid"}
    for n in __all__:
        f = g.get(n)
        if n in skip or not callable(f) or isinstance(f, type):
            continue

        def mk(f=f, n=n):
            @functools.wraps(f)
            def w(*a, **k):
                _page.USED.add(n)
                return f(*a, **k)
            return w
        g[n] = mk()
    for n in ("columns_page", "mixed_columns_page", "diagram_page", "kpi_charts_page", "icon_grid", "person_grid"):
        def mk_l(f=g[n], n=n):
            @functools.wraps(f)
            def w(*a, **k):
                _page.LAYOUTS_USED.add(n)
                return f(*a, **k)
            return w
        g[n] = mk_l()


_track()


def exhibit_help(name=None):
    from ._help import exhibit_help as _h
    return _h(name)
