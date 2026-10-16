"""Patient timelines with true-time treatment segments and event lanes."""

from __future__ import annotations

from xml.sax.saxutils import quoteattr

from ._academic_rigor import BBox, SeriesContext
from ._chart_layout import ChartLayout, finite, wrap_lines
from ._composition import attrs, footer, heading, numeric_axis, scale_from
from ._xy import _marker
from ._shared import tr


def _normalize(patients):
    out, times, treatments, kinds = [], [0.0], [], []
    for i, patient in enumerate(patients):
        p = dict(patient)
        p["id"] = str(p.get("id", i + 1))
        p["label"] = str(p.get("label", p["id"]))
        p["segments"], p["events"] = [], []
        for segment in patient.get("segments", []):
            s = dict(segment)
            s["start"], s["end"] = finite(s["start"], "segment start"), finite(s["end"], "segment end")
            if s["end"] <= s["start"]:
                raise ValueError("treatment end must exceed start")
            s["treatment"] = str(s.get("treatment", "Treatment"))
            if s["treatment"] not in treatments:
                treatments.append(s["treatment"])
            times.extend((s["start"], s["end"]))
            p["segments"].append(s)
        for event_index, event in enumerate(patient.get("events", [])):
            e = dict(event)
            e["id"] = str(e.get("id", event_index))
            e["time"] = finite(e["time"], "event time")
            e["kind"] = str(e.get("kind", "Event"))
            e["label"] = str(e.get("label", e["kind"]))
            if e["kind"] not in kinds:
                kinds.append(e["kind"])
            times.append(e["time"])
            p["events"].append(e)
        if len({e["id"] for e in p["events"]}) != len(p["events"]):
            raise ValueError("event ids must be unique within each patient")
        if patient.get("followup") is not None:
            f = dict(patient["followup"])
            f["start"], f["end"] = finite(f["start"], "followup start"), finite(f["end"], "followup end")
            if f["end"] < f["start"]:
                raise ValueError("followup end cannot precede start")
            p["followup"] = f
            times.extend((f["start"], f["end"]))
        if not p["segments"] and not p["events"] and p.get("followup") is None:
            raise ValueError("each patient needs a treatment, event, or followup")
        out.append(p)
    if not out or len({p["id"] for p in out}) != len(out):
        raise ValueError("patients must be non-empty with unique ids")
    return out, times, treatments, kinds


def _place_events(events, transform, layout, box):
    lanes, placed = [], []
    for event in sorted(events, key=lambda e: e["time"]):
        x = transform(event["time"])
        label_width = min(190, box.x1 - box.x0)
        lines = wrap_lines(event["label"], label_width, layout.font_sizes["label"], layout.font)
        width = max((layout.measure(line, layout.font_sizes["label"]) for line in lines), default=0)
        left = max(box.x0, min(x - width / 2, box.x1 - width))
        lane = next((i for i, right in enumerate(lanes) if right + 12 <= left), len(lanes))
        if lane == len(lanes):
            lanes.append(left + width)
        else:
            lanes[lane] = left + width
        placed.append((event, x, left, lane, lines))
    lane_heights = [
        max(
            (len(lines) * layout.font_sizes["label"] * 1.35 + 18 for _, _, _, level, lines in placed if level == lane),
            default=30,
        )
        for lane in range(len(lanes))
    ]
    return placed, lane_heights


def swimmer_state(patients, layout, time_domain=None):
    """Normalize once for either standalone or embedded clinical panels."""
    patients, times, treatments, kinds = _normalize(patients)
    return {
        "patients": patients,
        "scale": scale_from(times, domain=time_domain),
        "treatments": treatments,
        "kinds": kinds,
        "context": SeriesContext(treatments + [f"event:{kind}" for kind in kinds], pal=layout.pal),
    }


def _rail_width(state, layout, body):
    widths = [layout.measure(e["label"], layout.font_sizes["label"]) for p in state["patients"] for e in p["events"]]
    return min((body.x1 - body.x0) * 0.3, max(widths) + 18) if widths else 0


def _axis_heading_width(body, left, right, compact):
    if not compact:
        return right - left
    center = (left + right) / 2
    return 2 * min(center - body.x0, body.x1 - center)


def _axis_height(layout, text, width, compact):
    lines = len(wrap_lines(text, width, layout.font_sizes["xaxis"], layout.font))
    text_h = lines * layout.font_sizes["xaxis"] * 1.35 + layout.font_sizes["xtick"] * 1.7
    return text_h + 10 if compact else max(64, text_h + 24)


def _plan_rows(state, layout, body, scale=None, all_event_lanes=False, compact=False):
    patients = state["patients"]
    scale = scale or state["scale"]
    label_width = min(
        (body.x1 - body.x0) * 0.24,
        max(layout.measure(p["label"], layout.font_sizes["group"], True) for p in patients) * 1.05 + 1,
    )
    rail = _rail_width(state, layout, body) if compact else 0
    left, right = body.x0 + label_width + 24, body.x1 - 8 - (rail + 16 if rail else 0)
    if right - left < 160:
        raise ValueError("canvas is too narrow for patient labels")
    box = BBox(left, body.y0, right, body.y1)
    X = lambda v: scale.map(v, left, right)
    prepared = []
    for p in patients:
        segment_ends, segments = [], []
        for s in sorted(p["segments"], key=lambda s: s["start"]):
            lane = next((i for i, end in enumerate(segment_ends) if end <= s["start"]), len(segment_ends))
            if lane == len(segment_ends):
                segment_ends.append(s["end"])
            else:
                segment_ends[lane] = s["end"]
            segments.append((s, lane))
        label_lines = wrap_lines(p["label"], label_width / 1.05, layout.font_sizes["group"], layout.font)
        if compact:
            # Events sit on the bar line; their labels go to a right-hand rail, one line per event.
            events = [
                (
                    e,
                    X(e["time"]),
                    right + 16,
                    i,
                    wrap_lines(e["label"], rail - 18, layout.font_sizes["label"], layout.font),
                )
                for i, e in enumerate(sorted(p["events"], key=lambda e: e["time"]))
            ]
            heights = [len(lines) * layout.font_sizes["label"] * 1.35 for *_, lines in events]
            treatment_h = max(14, len(segment_ends) * 16)
            row_h = max(len(label_lines) * layout.font_sizes["group"] * 1.35, treatment_h, sum(heights)) + 3
            prepared.append((p, segments, events, heights, label_lines, treatment_h, 0, row_h))
            continue
        event_positions, event_heights = _place_events(
            p["events"], (lambda _v: left) if all_event_lanes else X, layout, box
        )
        treatment_h = max(22, len(segment_ends) * 20)
        followup_h = 16 if p.get("followup") is not None else 0
        row_h = max(
            len(label_lines) * layout.font_sizes["group"] * 1.35 + 18,
            treatment_h + followup_h + sum(event_heights) + 22,
        )
        prepared.append((p, segments, event_positions, event_heights, label_lines, treatment_h, followup_h, row_h))
    return prepared, left, right


def swimmer_height(
    state,
    layout,
    width,
    *,
    all_event_lanes=False,
    x_title="Time from treatment start",
    time_unit="months",
    compact=False,
):
    """Measured minimum body height, including the numerical time axis."""
    body = BBox(0, 0, width, 10000)
    rows, left, right = _plan_rows(state, layout, body, all_event_lanes=all_event_lanes, compact=compact)
    axis_h = _axis_height(
        layout, heading(x_title, state["scale"], time_unit), _axis_heading_width(body, left, right, compact), compact
    )
    return sum(row[-1] for row in rows) + axis_h + 4


def render_swimmer_plot(
    layout, body, state, *, time_unit="months", x_title="Time from treatment start", scale=None, compact=False
):
    """Append a plot inside body; return true patient/event anchors, never SVG."""
    scale = scale or state["scale"]
    patients, kinds, context = state["patients"], state["kinds"], state["context"]
    shapes = ("circle", "diamond", "triangle", "square")
    prepared, left, right = _plan_rows(state, layout, body, scale, compact=compact)
    heading_w = _axis_heading_width(body, left, right, compact)
    axis_h = _axis_height(layout, heading(x_title, scale, time_unit), heading_w, compact)
    top, bottom = body.y0, body.y1 - axis_h
    if sum(row[-1] for row in prepared) > bottom - top:
        raise ValueError("panel is too short for treatments and concurrent event labels")
    X = lambda v: scale.map(v, left, right)
    row_extra = min(6 if compact else 18, (bottom - top - sum(item[-1] for item in prepared)) / len(patients))
    end = top + sum(item[-1] + row_extra for item in prepared)
    plot = BBox(left, top, right, end)
    numeric_axis(layout, plot, scale, grid=True)
    cursor = top
    anchors = {}
    protected_start = len(layout.text_boxes)
    for p, segments, events, event_heights, label_lines, treatment_h, followup_h, row_h in prepared:
        row_top = cursor + (row_extra / 2 + 2 if compact else 9)
        layout.parts.append(f"<g {attrs(role='patient', row_id=p['id'], top=cursor, height=row_h + row_extra)}>")
        layout.text("\n".join(label_lines), left - 16, row_top, fs=layout.font_sizes["group"], bold=True, anchor="end")
        for s, lane in segments:
            y = row_top + lane * (16 if compact else 20)
            layout.parts.append(
                f'<rect x="{X(s["start"]):.3f}" y="{y:.3f}" width="{X(s["end"]) - X(s["start"]):.3f}" height="{11 if compact else 13}" rx="2" fill={quoteattr(context.color_of(s["treatment"]))} {attrs(role="treatment", row_id=p["id"], start=s["start"], end=s["end"], treatment=s["treatment"], lane=lane)}/>'
            )
        if p.get("followup") is not None:
            f, y = p["followup"], row_top + (5.5 if compact else treatment_h + 3)
            layout.parts.append(
                f'<path d="M{X(f["start"]):.3f},{y:.3f} H{X(f["end"]):.3f}" fill="none" stroke={quoteattr(layout.pal["ink6"])} stroke-dasharray="4 3" {attrs(role="followup", start=f["start"], end=f["end"])}/>'
            )
            if f.get("ongoing"):
                x = X(f["end"])
                layout.parts.append(
                    f'<path d="M{x - 5},{y - 4} L{x},{y} L{x - 5},{y + 4}" fill="none" stroke={quoteattr(layout.pal["ink6"])} data-role="ongoing"/>'
                )
        anchors[("patient", p["id"])] = (
            X(
                max(
                    [v for segment in p["segments"] for v in (segment["start"], segment["end"])]
                    + [event["time"] for event in p["events"]]
                    + ([p["followup"]["end"]] if p.get("followup") is not None else [])
                )
            ),
            row_top + 6.5,
            0,
        )
        anchors[("row", p["id"])] = (right, row_top + 6.5, 0)
        for event, x, label_left, lane, lines in events:
            if compact:
                marker_y = row_top + 5.5
                rail_y = row_top + sum(event_heights[:lane])
                color = context.color_of(f"event:{event['kind']}")
                anchors[("event", p["id"] + "/" + str(event["id"]))] = (x, marker_y, 4)
                shape = shapes[kinds.index(event["kind"]) % len(shapes)]
                event_attrs = attrs(row_id=p["id"], time=event["time"], kind=event["kind"], lane=lane)
                layout.parts.append(
                    _marker(
                        x,
                        marker_y,
                        4.5,
                        shape,
                        color,
                        opacity=1,
                        role="patient-event",
                        stroke_color=layout.ink,
                        attrs=event_attrs,
                    )
                )
                layout.parts.append(
                    _marker(
                        label_left - 9,
                        rail_y + layout.font_sizes["label"] * 0.55,
                        4,
                        shape,
                        color,
                        opacity=1,
                        role="event-rail",
                        stroke_color=layout.ink,
                    )
                )
                layout.text("\n".join(lines), label_left, rail_y, fs=layout.font_sizes["label"], color=layout.ink)
                continue
            marker_y = row_top + treatment_h + followup_h + sum(event_heights[:lane]) + 5
            anchors[("event", p["id"] + "/" + str(event["id"]))] = (x, marker_y, 4)
            color = context.color_of(f"event:{event['kind']}")
            layout.parts.append(
                f'<path d="M{x:.3f},{row_top + treatment_h:.3f} V{marker_y:.3f}" fill="none" stroke={quoteattr(color)} stroke-opacity=".35" stroke-width=".7"/>'
            )
            layout.parts.append(
                _marker(
                    x,
                    marker_y,
                    4,
                    shapes[kinds.index(event["kind"]) % len(shapes)],
                    color,
                    opacity=1,
                    role="patient-event",
                    stroke_color=layout.ink,
                    attrs=attrs(row_id=p["id"], time=event["time"], kind=event["kind"], lane=lane),
                )
            )
            layout.text("\n".join(lines), label_left, marker_y + 8, fs=layout.font_sizes["label"], color=layout.ink)
        layout.parts.append("</g>")
        cursor += row_h + row_extra
        layout.parts.append(
            f'<path d="M{body.x0},{cursor:.3f} H{body.x1}" stroke={quoteattr(layout.pal["grid"])} stroke-width=".6"/>'
        )
    layout.text(
        heading(x_title, scale, time_unit),
        (left + right) / 2,
        end + layout.font_sizes["xtick"] * 1.7 + 12,
        fs=layout.font_sizes["xaxis"],
        anchor="middle",
        width=heading_w,
    )
    return {
        "plot_bbox": plot,
        "anchors": anchors,
        "protected": [box[:4] for box in layout.text_boxes[protected_start:]],
    }


def make_swimmer(
    patients,
    *,
    time_unit="months",
    x_title="Time from treatment start",
    title=None,
    subtitle=None,
    figure_label=None,
    note=None,
    source=None,
    time_domain=None,
    width=1200,
    height=800,
    palette=None,
    font_family=None,
    variant=None,
):
    """Return one complete SVG; every position comes from supplied patient data."""
    if variant not in (None, "classic"):
        raise ValueError("swimmer variant must be classic or None")
    layout = ChartLayout(width, height, palette or "archive_ink", font_family, n_items=len(patients))
    state = swimmer_state(patients, layout, time_domain)
    patients, treatments, kinds, context = state["patients"], state["treatments"], state["kinds"], state["context"]
    shapes = ("circle", "diamond", "triangle", "square")
    top = layout.header(title, subtitle, figure_label)
    x = 28
    legend = [(name, context.color_of(name), None) for name in treatments] + [
        (kind, context.color_of(f"event:{kind}"), shapes[i % len(shapes)]) for i, kind in enumerate(kinds)
    ]
    for label, color, shape in legend:
        width_needed = layout.measure(label, layout.font_sizes["legend"]) + 34
        if width_needed > layout.width - 56:
            raise ValueError("legend entry exceeds canvas width")
        if x + width_needed > layout.width - 28:
            x = 28
            top += layout.font_sizes["legend"] * 1.35 + 10
        if shape:
            layout.parts.append(
                _marker(x + 7, top + 7, 4, shape, color, opacity=1, role="event-legend", stroke_color=layout.ink)
            )
        else:
            layout.parts.append(f'<rect x="{x}" y="{top + 1}" width="14" height="12" fill={quoteattr(color)}/>')
        layout.text(label, x + 22, top, fs=layout.font_sizes["legend"])
        x += width_needed
    top += layout.font_sizes["legend"] * 1.35 + 16
    if any(p.get("followup") for p in patients):
        top += (
            layout.text(
                tr("Dashed line: follow-up · Arrow: ongoing at last observation"),
                28,
                top,
                fs=layout.font_sizes["foot"],
                color=layout.pal["ink6"],
                width=layout.width - 56,
            )
            + 12
        )
    footer_h = sum(
        len(wrap_lines(v, layout.width - 56, layout.font_sizes["foot"], layout.font)) * layout.font_sizes["foot"] * 1.35
        for v in (note, source)
        if v
    )
    needed = (
        top + swimmer_height(state, layout, layout.width - 56, x_title=x_title, time_unit=time_unit) + footer_h + 48
    )
    compact = needed > layout.height and (
        top
        + swimmer_height(state, layout, layout.width - 56, x_title=x_title, time_unit=time_unit, compact=True)
        + footer_h
        + (40 if footer_h else 24)
        <= layout.height
    )
    if not compact:
        layout.height = max(layout.height, needed)
    bottom = footer(layout, note, source)
    render_swimmer_plot(
        layout, BBox(28, top, layout.width - 28, bottom), state, time_unit=time_unit, x_title=x_title, compact=compact
    )
    return layout.svg(title or "Patient treatment and follow-up timelines")
