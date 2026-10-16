"""svg_lib.charts — productized chart modules."""

from importlib import import_module

__all__ = []


def _export(mod_name, attr):
    mod = import_module(f".{mod_name}", __name__)
    globals()[attr] = getattr(mod, attr)
    __all__.append(attr)


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
    _export(_m, _a)


def _scaling_hint(message, name):
    """Append how to fit a chart that needs a larger canvas than the slide box."""
    import re

    m = re.search(r"needs? (?:about |at least )?([\d.]+)\s*[x×]\s*([\d.]+)", message)
    if "chart_slide" in message:
        return message
    if not m:
        if re.search(
            r"increase (?:the )?(?:width|height)|too (?:small|short|narrow)|needs? more (?:room|space)", message
        ):
            return (
                f"[use chart_slide('{name.removeprefix('make_')}', x, y, w, h, ...) — it grows the canvas and fits any box] "
                f"{message}\n→ On a slide, don't search width/height by hand: chart_slide grows the canvas automatically "
                "and fits the vector chart into your box (text stays native and editable)."
            )
        return message
    need_w, need_h = float(m.group(1)), float(m.group(2))
    rows = "; ".join(f"{int(k * 100)}% → {need_w * k:.0f}x{need_h * k:.0f}" for k in (1, 0.8, 0.7, 0.6, 0.5))
    slug = name.removeprefix("make_")
    return (
        f"[use chart_slide('{slug}', x, y, w, h, ...) — canvas size, not a bug] {message}\n"
        f"→ This is a canvas size, not an error to work around. The SVG is vector: draw it at "
        f"{need_w:.0f}x{need_h:.0f} (width={need_w:.0f}, height={need_h:.0f}) and place it scaled on the slide; "
        f"the slide box at each scale is {rows}. chart_slide('{slug}', x, y, w, h, ...) does this automatically "
        f"(it grows the canvas and fits it into your box, keeping text native and editable) — use it instead of "
        f"converting the chart to an image. Pick a box that keeps scale ≥ 70% so text stays ≥ 10pt."
    )


# matplotlib / seaborn vocabulary → this library's parameter names. Each alias maps to the first target that the
# chart actually takes, so one table serves every generator; an alias is never applied when its target was passed.
_KWARG_ALIASES = {
    "xlabel": ("x_title", "x_axis_label", "time_label", "value_title"),
    "x_label": ("x_title", "x_axis_label", "time_label"),
    "ylabel": ("y_title", "y_axis_label", "value_label", "value_title"),
    "y_label": ("y_title", "y_axis_label", "value_label"),
    "suptitle": ("title",),
    "caption": ("note",),
    "footnote": ("note",),
    "data_source": ("source",),
    "colors": ("palette",),
    "color": ("palette",),
    "cmap": ("colormap", "palette"),
    "legend": ("show_legend",),
    "annotate": ("show_values",),
    "show_labels": ("show_values",),
    "labels_on_bars": ("show_values",),
    "fmt": ("value_format", "value_fmt"),
    "x_unit_label": ("x_unit",),
    "y_unit_label": ("y_unit",),
    "reference": ("midline_value", "baseline_value"),
    "ref_line": ("midline_value", "baseline_value"),
    "null_value": ("midline_value",),
    "vmin": ("vmin", "value_min"),
    "vmax": ("vmax", "value_max"),
}
# Range aliases (ylim=(lo, hi), y_min=…, …): (lower, upper) targets per chart, or one domain-tuple target.
_RANGE_ALIASES = {
    "y": (("y_min", "y_max"), ("value_min", "value_max"), "value_domain", "y_range"),
    "x": (("x_min", "x_max"), ("value_min", "value_max"), "value_domain", "x_range"),
}


def _rename_kwargs(params, kwargs):
    """Rewrite matplotlib-style keyword names in place; return [(alias, target)] that were applied."""
    applied = []
    for alias, targets in _KWARG_ALIASES.items():
        if alias not in kwargs or alias in params:
            continue
        target = next((t for t in targets if t in params), None)
        if target is None or target in kwargs:
            continue
        value = kwargs.pop(alias)
        if alias in ("colors", "color") and target == "palette" and isinstance(value, (list, tuple)):
            value = {"series": list(value)}
        elif alias == "color" and target == "palette" and isinstance(value, str) and value.startswith("#"):
            value = {"series": [value]}
        kwargs[target] = value
        applied.append((alias, target))
    for axis, options in _RANGE_ALIASES.items():
        lim = kwargs.pop(f"{axis}lim", None) if f"{axis}lim" not in params else None
        lo = kwargs.pop(f"{axis}_min", None) if f"{axis}_min" not in params else None
        hi = kwargs.pop(f"{axis}_max", None) if f"{axis}_max" not in params else None
        if lim is not None:
            lo, hi = lim
        if lo is None and hi is None:
            continue
        for option in options:
            if isinstance(option, tuple) and all(o in params for o in option):
                if lo is not None:
                    kwargs.setdefault(option[0], lo)
                if hi is not None:
                    kwargs.setdefault(option[1], hi)
                applied.append((f"{axis}lim", "/".join(option)))
                break
            if isinstance(option, str) and option in params and lo is not None and hi is not None:
                kwargs.setdefault(option, (lo, hi))
                applied.append((f"{axis}lim", option))
                break
        else:  # nothing to map to: put the names back so the unknown-keyword message reports them
            if lim is not None:
                kwargs[f"{axis}lim"] = lim
            else:
                if lo is not None:
                    kwargs[f"{axis}_min"] = lo
                if hi is not None:
                    kwargs[f"{axis}_max"] = hi
    for axis in ("x", "y"):
        for key in (f"{axis}scale", f"{axis}_scale", f"log{axis}", f"log_{axis}"):
            if key not in kwargs or key in params:
                continue
            value = kwargs[key]
            is_log = value is True or (isinstance(value, str) and value.lower().startswith("log"))
            target = next((t for t in (f"log_{axis}", "value_scale") if t in params), None)
            if target is None:
                continue
            kwargs.pop(key)
            kwargs.setdefault(target, ("log" if is_log else "linear") if target == "value_scale" else bool(is_log))
            applied.append((key, target))
    return applied


# Generators whose group arguments are (name, samples) pairs; {"name", "values"} dicts are the shape callers write.
_PAIR_GROUPS = {
    "make_boxplot": "groups",
    "make_violin": "groups",
    "make_raincloud": "groups",
    "make_ridge": "distributions",
}


def _pair_groups(name, kwargs):
    key = _PAIR_GROUPS.get(name)
    items = kwargs.get(key) if key else None
    if not isinstance(items, (list, tuple)):
        return
    out = []
    for item in items:
        if isinstance(item, dict) and "name" in item:
            data = next((item[k] for k in ("values", "data", "observations", "samples") if k in item), None)
            if data is not None:
                item = (item["name"], data)
        out.append(item)
    kwargs[key] = out


def _unknown_kwargs_message(name, unknown, valid):
    import difflib

    hints = []
    for key in unknown:
        close = difflib.get_close_matches(key, valid, n=1, cutoff=0.6)
        if not close:  # a misspelt matplotlib name (ylabl → ylabel) points at our parameter
            alias = difflib.get_close_matches(key, list(_KWARG_ALIASES), n=1, cutoff=0.7)
            target = next((t for t in _KWARG_ALIASES[alias[0]] if t in valid), None) if alias else None
            close = [target] if target else []
        hints.append(f"{key!r}" + (f" (did you mean {close[0]!r}?)" if close else ""))
    return (
        f"{name}() got unexpected keyword argument(s): {', '.join(hints)}. "
        f"Valid parameters: {', '.join(valid)}. Font sizes scale with width/height; "
        f"the SVG is vector so there is no dpi."
    )


def _apply_background(name, params, kwargs):
    """Map background=/bg= (slide colour) onto the palette's bg; never a per-chart parameter."""
    import warnings

    keys = [k for k in ("background", "bg") if k in kwargs and k not in params]
    if not keys:
        return
    values = [kwargs.pop(k) for k in keys]
    color = values[-1]
    if color is None:
        return
    if "palette" not in params:
        warnings.warn(
            f"{name}: background={color!r} ignored (this chart has no palette); "
            "draw the background on the slide instead",
            stacklevel=3,
        )
        return
    from .._color_compat import parse_color

    parsed = parse_color(color) if str(color).strip().lower() != "none" else ("#000000", 0.0)
    if parsed is None:
        raise ValueError(f"{name}: background={color!r} is not a colour; use '#RRGGBB', 'rgb(...)' or a CSS name")
    hexed, alpha = parsed
    if alpha <= 0:
        warnings.warn(
            f"{name}: transparent background={color!r} ignored; charts are already drawn over the slide", stacklevel=3
        )
        return
    from ..svg_palettes import PALETTES

    palette = kwargs.get("palette")
    if palette is None:
        base = dict(PALETTES["archive_ink"])
    elif isinstance(palette, str):
        if palette not in PALETTES:
            raise ValueError(f"unknown palette {palette!r}. Available: {sorted(PALETTES)}")
        base = dict(PALETTES[palette])
    else:
        base = dict(palette)
    r, g, b = (int(hexed[i : i + 2], 16) for i in (1, 3, 5))
    base["bg"] = f"rgba({r},{g},{b},{alpha:g})"
    kwargs["palette"] = base


# Palette fields every renderer understands; any other key of a palette dict is a series / group name.
_PALETTE_FIELDS = {
    "ink",
    "accent",
    "secondary",
    "bg",
    "muted",
    "series",
    "grid",
    "connect",
    "panel",
    "ink_fg",
    "ink1",
    "ink2",
    "ink4",
    "ink6",
    "kicker",
    "color_stops",
    "series_colors",
}
# Arguments whose items carry the series / group names a {name: colour} palette refers to, in drawing order.
_NAMED_ARGS = (
    "series",
    "points",
    "models",
    "curves",
    "pathways",
    "groups",
    "distributions",
    "lines",
    "rows",
    "panels",
    "series_labels",
)


def _series_names(args, kwargs):
    names = []
    values = [kwargs.get(k) for k in _NAMED_ARGS] + [a for a in args if isinstance(a, (list, tuple))]
    for value in values:
        if isinstance(value, str) or not isinstance(value, (list, tuple)):
            continue
        for item in value:
            if isinstance(item, dict):
                if item.get("series") and isinstance(item["series"], list):  # panels=[{series: [...]}]
                    names += [str(s.get("name")) for s in item["series"] if isinstance(s, dict) and s.get("name")]
                name = item.get("name", item.get("group"))
            elif isinstance(item, (list, tuple)) and item and isinstance(item[0], str):
                name = item[0]
            elif isinstance(item, str):
                name = item
            else:
                name = None
            if name is not None:
                names.append(str(name))
    return list(dict.fromkeys(names))


def _normalize_palette(name, params, args, kwargs):
    """palette=[colours] or {series_name: colour} (optionally mixed with palette fields) → a palette dict."""
    palette = kwargs.get("palette")
    if "palette" not in params or palette is None or isinstance(palette, str):
        return
    from .._color_compat import parse_color
    from ..svg_palettes import PALETTES

    def colour(key, value):
        if not isinstance(value, str) or parse_color(value) is None:
            raise ValueError(f"{name}: palette[{key!r}]={value!r} is not a colour; use '#RRGGBB' or 'rgb(...)'")
        return value

    if isinstance(palette, (list, tuple)):
        if not palette:
            raise ValueError(f"{name}: palette=[] has no colours")
        kwargs["palette"] = dict(PALETTES["archive_ink"], series=[colour(i, c) for i, c in enumerate(palette)])
        return
    if not isinstance(palette, dict):
        raise TypeError(
            f"{name}: palette must be a palette name, a list of colours or {{series_name: colour}}, "
            f"got {type(palette).__name__}"
        )
    named = {
        k: v for k, v in palette.items() if k not in _PALETTE_FIELDS and not str(k).endswith(("_color", "_colors"))
    }
    if not named:
        return
    names = _series_names(args, kwargs)
    unknown = [k for k in named if str(k) not in names]
    if unknown:
        raise ValueError(
            f"{name}: palette keys {unknown} are neither palette fields ({', '.join(sorted(_PALETTE_FIELDS - {'series_colors'}))}) "
            f"nor series/group names in this chart ({names or 'none found'})"
        )
    mapping = {str(k): colour(k, v) for k, v in named.items()}
    fields = {k: v for k, v in palette.items() if k not in named}
    base = dict(PALETTES["archive_ink"], **fields) if not ({"ink", "accent"} & set(fields)) else fields
    spare = [
        c for c in base.get("series") or [base.get("accent"), base.get("secondary")] if c and c not in mapping.values()
    ]
    ordered, k = [], 0
    for series_name in names:
        if series_name in mapping:
            ordered.append(mapping[series_name])
        else:
            ordered.append(spare[k % len(spare)] if spare else base.get("ink", "#333333"))
            k += 1
    kwargs["palette"] = dict(base, series=ordered + spare, series_colors=mapping)


class ChartSVG(str):
    """SVG text that also unpacks as ``svg, notice`` (notice is always None)."""

    def __iter__(self):
        return iter((str(self), None))


def _mark_chart_output():
    """Every make_* (also when imported from a submodule) returns office-safe, chart-tagged SVG."""
    import functools
    import inspect
    import pkgutil
    import re
    from .._color_compat import office_safe_svg
    from ._shared import _AUTHORED, _CHART_LANG, authored_strings, has_cjk, tr

    def wrap(make):
        if getattr(make, "_chart_lib_marked", False):
            return make

        params = inspect.signature(make).parameters
        takes_lang = "lang" in params
        # English defaults of caption parameters (x_title="Hazard ratio", time_unit="months", ...) are chrome too.
        caption_defaults = {
            name: p.default
            for name, p in params.items()
            if isinstance(p.default, str) and re.search(r"(^|_)(title|label|header|unit)$", name)
        }

        accepts_any = any(p.kind is p.VAR_KEYWORD for p in params.values())
        valid = [n for n, p in params.items() if p.kind in (p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY)]
        valid += [] if "lang" in valid else ["lang"]

        @functools.wraps(make)
        def wrapper(*args, lang=None, **kwargs):
            _rename_kwargs(params, kwargs)
            _normalize_palette(make.__name__, params, args, kwargs)
            _apply_background(make.__name__, params, kwargs)
            _pair_groups(make.__name__, kwargs)
            if not accepts_any:
                unknown = [k for k in kwargs if k not in params]
                if unknown:
                    raise TypeError(_unknown_kwargs_message(make.__name__, unknown, valid))
            # Generated chrome is Chinese when the caller's own text is; lang='zh'/'en' overrides.
            if lang not in (None, "zh", "en"):
                raise ValueError(f"lang must be 'zh' or 'en', got {lang!r}")
            if _CHART_LANG.get() is None:  # nested make_* calls keep the outer chart's language
                # Lower-case identifiers ("mean", "auto", "log10") are option values, not displayed text.
                authored = frozenset(t for t in authored_strings((args, kwargs)) if not re.fullmatch(r"[a-z0-9_]+", t))
                lang = lang or ("zh" if has_cjk(authored) else "en")
                tokens = _CHART_LANG.set(lang), _AUTHORED.set(authored)
            else:
                lang, tokens = _CHART_LANG.get(), None
            if lang == "zh":
                kwargs.update({k: tr(v) for k, v in caption_defaults.items() if k not in kwargs})
            if takes_lang:
                kwargs["lang"] = lang
            try:
                raw = make(*args, **kwargs)
            except ValueError as error:
                raise ValueError(_scaling_hint(str(error), make.__name__)) from error
            finally:
                if tokens:
                    _CHART_LANG.reset(tokens[0])
                    _AUTHORED.reset(tokens[1])
            svg = office_safe_svg(raw)
            head = svg[:400]
            return ChartSVG(svg if "data-chart-lib=" in head else svg.replace("<svg ", '<svg data-chart-lib="1" ', 1))

        wrapper._chart_lib_marked = True
        return wrapper

    for info in pkgutil.iter_modules(__path__):
        if info.name.startswith("_") or info.name.endswith("_test"):
            continue
        module = import_module(f".{info.name}", __name__)
        for name, value in list(vars(module).items()):
            if name.startswith("make_") and callable(value) and getattr(value, "__module__", "") == module.__name__:
                setattr(module, name, wrap(value))


_mark_chart_output()
