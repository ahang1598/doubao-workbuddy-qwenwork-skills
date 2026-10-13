#!/usr/bin/env python3
"""Generate self-contained HTML-block charts for Lark equity-research documents."""

import argparse
import html
import json
import math
import sys
from datetime import date
from pathlib import Path


COLORS = ["#2563EB", "#14936B", "#D97706", "#8B5CF6", "#D64A52"]
INK = "#172033"
MUTED = "#667085"
GRID = "#E5EAF0"


def emit(message):
    sys.stderr.write(f"{message}\n")


def load_object(path):
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("输入 JSON 顶层必须是对象")
    return value


def text_value(value, label, *, default="", max_length=160):
    if value is None:
        return default
    if not isinstance(value, str):
        raise ValueError(f"{label} 必须是字符串")
    value = value.strip()
    if not value and default:
        return default
    if len(value) > max_length:
        raise ValueError(f"{label} 最长 {max_length} 个字符")
    return value


def finite_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} 必须是数值")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{label} 必须是有限数")
    return number


def iso_date(value, label):
    if not isinstance(value, str):
        raise ValueError(f"{label} 必须是 YYYY-MM-DD")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{label} 必须是 YYYY-MM-DD") from exc
    return value


def common_meta(data):
    title = text_value(data.get("title"), "title", max_length=80)
    if not title:
        raise ValueError("title 不能为空")
    return {
        "title": title,
        "subtitle": text_value(data.get("subtitle"), "subtitle", max_length=140),
        "unit": text_value(data.get("unit"), "unit", max_length=30),
        "as_of": text_value(data.get("as_of"), "as_of", max_length=20),
        "source_note": text_value(
            data.get("source_note"), "source_note", max_length=180
        ),
    }


def write_output(path, content, input_path):
    output = Path(path).resolve()
    if output == Path(input_path).resolve():
        raise ValueError("输出路径不能覆盖输入文件")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    return output


def number_text(value, decimals=1):
    text = f"{value:,.{decimals}f}"
    return text.rstrip("0").rstrip(".") if "." in text else text


def script_json(value):
    return json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).replace("</", "<\\/")


def note_text(meta):
    return " ｜ ".join(
        filter(
            None,
            [
                meta["unit"] and f"单位：{meta['unit']}",
                meta["as_of"] and f"截至 {meta['as_of']}",
                meta["source_note"],
            ],
        )
    )


def canvas_html(meta, kind, model, *, aria_label):
    model_json = script_json(model)
    if kind == "timeline":
        min_width = max(680, len(model["events"]) * 135)
    elif kind == "waterfall":
        min_width = max(680, len(model["items"]) * 86)
    else:
        min_width = 680
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="use-iframe" content="true"><meta name="html-box-height-mode" content="auto"><title>{html.escape(meta["title"])}</title>
<style>
*{{box-sizing:border-box}}body{{margin:0;background:#fff;color:{INK};font-family:Inter,"Noto Sans SC","PingFang SC",Arial,sans-serif}}
.root{{padding:18px}}.card{{border:1px solid {GRID};border-radius:18px;padding:20px;box-shadow:0 10px 28px rgba(23,32,51,.07);overflow:auto}}
h1{{font-size:22px;margin:0}}.sub{{font-size:13px;color:{MUTED};margin:6px 0 12px}}.canvas-wrap{{position:relative;width:100%;min-width:{min_width}px;height:460px}}
canvas{{width:100%;height:100%;display:block}}footer{{font-size:11px;color:#98A2B3;margin-top:10px}}
</style></head><body><main class="root"><section class="card" aria-label="{html.escape(aria_label)}">
<h1>{html.escape(meta["title"])}</h1><div class="sub">{html.escape(meta["subtitle"])}</div>
<div class="canvas-wrap"><canvas id="chart"></canvas></div><footer>{html.escape(note_text(meta))}</footer>
</section></main><script>
const TYPE={json.dumps(kind)},MODEL={model_json},COLORS={script_json(COLORS)},INK={json.dumps(INK)},MUTED={json.dumps(MUTED)},GRID={json.dumps(GRID)};
const canvas=document.getElementById("chart"),ctx=canvas.getContext("2d");
function fmt(v){{return new Intl.NumberFormat("zh-CN",{{maximumFractionDigits:2}}).format(v)}}
function setup(){{const r=canvas.getBoundingClientRect(),d=Math.min(window.devicePixelRatio||1,2);canvas.width=Math.round(r.width*d);canvas.height=Math.round(r.height*d);ctx.setTransform(d,0,0,d,0,0);return{{w:r.width,h:r.height}}}}
function line(x1,y1,x2,y2,color=GRID,width=1,dash=[]){{ctx.beginPath();ctx.setLineDash(dash);ctx.moveTo(x1,y1);ctx.lineTo(x2,y2);ctx.strokeStyle=color;ctx.lineWidth=width;ctx.stroke();ctx.setLineDash([])}}
function text(value,x,y,align="center",color=MUTED,size=12,weight=500){{ctx.fillStyle=color;ctx.font=`${{weight}} ${{size}}px Inter,"Noto Sans SC","PingFang SC",Arial,sans-serif`;ctx.textAlign=align;ctx.textBaseline="middle";ctx.fillText(value,x,y)}}
function drawAxes(w,h,min,max,categories,barMode=false){{const p={{l:64,r:24,t:46,b:52}},cw=w-p.l-p.r,ch=h-p.t-p.b;for(let i=0;i<6;i++){{const y=p.t+ch*i/5,v=max-(max-min)*i/5;line(p.l,y,w-p.r,y);text(fmt(v),p.l-10,y,"right")}}const step=Math.max(1,Math.ceil(categories.length/9));categories.forEach((c,i)=>{{if(i%step===0||i===categories.length-1){{const x=barMode?p.l+(i+.5)*cw/categories.length:p.l+(categories.length===1?cw/2:i*cw/(categories.length-1));text(c,x,h-24)}}}});return{{...p,cw,ch,sx:i=>p.l+(categories.length===1?cw/2:i*cw/(categories.length-1)),sy:v=>p.t+(max-v)/(max-min)*ch}}}}
function drawTrend(w,h){{const a=drawAxes(w,h,MODEL.y_min,MODEL.y_max,MODEL.categories);MODEL.series.forEach((s,si)=>{{const color=COLORS[si%COLORS.length];ctx.beginPath();s.values.forEach((v,i)=>{{const x=a.sx(i),y=a.sy(v);i?ctx.lineTo(x,y):ctx.moveTo(x,y)}});ctx.strokeStyle=color;ctx.lineWidth=3;ctx.lineJoin="round";ctx.lineCap="round";ctx.stroke();s.values.forEach((v,i)=>{{ctx.beginPath();ctx.arc(a.sx(i),a.sy(v),4,0,Math.PI*2);ctx.fillStyle="#fff";ctx.fill();ctx.strokeStyle=color;ctx.lineWidth=2;ctx.stroke()}});const lx=72+si*150;line(lx,18,lx+24,18,color,4);text(s.name,lx+32,18,"left",INK,12,600)}})}}
function drawWaterfall(w,h){{const a=drawAxes(w,h,MODEL.y_min,MODEL.y_max,MODEL.items.map(i=>i.label),true),n=MODEL.items.length,step=a.cw/n,bw=Math.min(68,step*.58);MODEL.items.forEach((b,i)=>{{const x=a.l+step*(i+.5),y1=a.sy(b.start),y2=a.sy(b.end),y=Math.min(y1,y2),bh=Math.max(2,Math.abs(y2-y1)),color=b.kind==="change"?(b.value>=0?"#14936B":"#D64A52"):"#2563EB";ctx.fillStyle=color;ctx.globalAlpha=.9;ctx.beginPath();ctx.roundRect(x-bw/2,y,bw,bh,7);ctx.fill();ctx.globalAlpha=1;text((b.kind==="change"&&b.value>=0?"+":"")+fmt(b.value),x,Math.max(12,y-12),"center",INK,12,700);if(i<n-1)line(x+bw/2,a.sy(b.end),a.l+step*(i+1.5)-bw/2,a.sy(b.end),"#98A2B3",1.5,[5,4])}})}}
function drawTimeline(w,h){{const events=MODEL.events,p={{l:55,r:55}},axis=h/2,step=(w-p.l-p.r)/Math.max(1,events.length-1);line(p.l,axis,w-p.r,axis,"#98A2B3",4);events.forEach((e,i)=>{{const x=p.l+step*i,upper=i%2===0,boxY=upper?38:axis+54,color=COLORS[MODEL.categories.indexOf(e.category)%COLORS.length];line(x,axis,x,upper?150:boxY,color,2);ctx.beginPath();ctx.arc(x,axis,7,0,Math.PI*2);ctx.fillStyle="#fff";ctx.fill();ctx.strokeStyle=color;ctx.lineWidth=4;ctx.stroke();const bw=Math.min(150,Math.max(104,step-18)),bh=104,bx=x-bw/2;ctx.fillStyle="#fff";ctx.strokeStyle=color;ctx.lineWidth=2;ctx.beginPath();ctx.roundRect(bx,boxY,bw,bh,12);ctx.fill();ctx.stroke();text(e.category,x,boxY+20,"center",color,11,700);text(e.label,x,boxY+44,"center",INK,12,700);text(e.note||"",x,boxY+66,"center",MUTED,10,500);text(e.date,x,boxY+88,"center","#98A2B3",10,500)}})}}
function draw(){{const{{w,h}}=setup();ctx.clearRect(0,0,w,h);if(TYPE==="trend")drawTrend(w,h);else if(TYPE==="waterfall")drawWaterfall(w,h);else drawTimeline(w,h)}}
new ResizeObserver(draw).observe(canvas.parentElement);draw();
</script></body></html>'''


def render_trend(data):
    meta = common_meta(data)
    categories = data.get("categories")
    if not isinstance(categories, list) or not 2 <= len(categories) <= 36:
        raise ValueError("categories 必须包含 2–36 项")
    categories = [
        text_value(value, f"categories[{index}]", max_length=12)
        for index, value in enumerate(categories)
    ]
    if any(not value for value in categories) or len(set(categories)) != len(categories):
        raise ValueError("categories 不得为空或重复")

    raw_series = data.get("series")
    if not isinstance(raw_series, list) or not 1 <= len(raw_series) <= 5:
        raise ValueError("series 必须包含 1–5 组")
    series = []
    names = set()
    values = []
    for index, raw in enumerate(raw_series):
        if not isinstance(raw, dict):
            raise ValueError(f"series[{index}] 必须是对象")
        name = text_value(raw.get("name"), f"series[{index}].name", max_length=12)
        if not name or name in names:
            raise ValueError("series.name 不得为空或重复")
        names.add(name)
        raw_values = raw.get("values")
        if not isinstance(raw_values, list) or len(raw_values) != len(categories):
            raise ValueError(f"series[{index}].values 数量必须等于 categories")
        parsed = [
            finite_number(value, f"series[{index}].values[{value_index}]")
            for value_index, value in enumerate(raw_values)
        ]
        values.extend(parsed)
        series.append({"name": name, "values": parsed})

    y_min = (
        finite_number(data.get("y_min"), "y_min")
        if data.get("y_min") is not None
        else min(values)
    )
    y_max = (
        finite_number(data.get("y_max"), "y_max")
        if data.get("y_max") is not None
        else max(values)
    )
    if y_max <= y_min:
        pad = abs(y_min) * 0.05 or 1.0
        y_min -= pad
        y_max += pad
    else:
        pad = (y_max - y_min) * 0.08
        if data.get("y_min") is None:
            y_min -= pad
        if data.get("y_max") is None:
            y_max += pad
    model = {
        "categories": categories,
        "series": series,
        "y_min": y_min,
        "y_max": y_max,
    }
    return canvas_html(meta, "trend", model, aria_label="多序列趋势图")


def render_waterfall(data):
    meta = common_meta(data)
    raw_items = data.get("items")
    if not isinstance(raw_items, list) or not 3 <= len(raw_items) <= 14:
        raise ValueError("items 必须包含 3–14 项")
    items = []
    for index, raw in enumerate(raw_items):
        if not isinstance(raw, dict):
            raise ValueError(f"items[{index}] 必须是对象")
        label = text_value(raw.get("label"), f"items[{index}].label", max_length=12)
        kind = raw.get("kind")
        if kind not in {"start", "change", "end"}:
            raise ValueError(f"items[{index}].kind 必须是 start、change 或 end")
        items.append(
            {
                "label": label,
                "kind": kind,
                "value": finite_number(raw.get("value"), f"items[{index}].value"),
            }
        )
    if items[0]["kind"] != "start" or items[-1]["kind"] != "end":
        raise ValueError("第一项必须是 start，最后一项必须是 end")
    if any(item["kind"] != "change" for item in items[1:-1]):
        raise ValueError("中间项必须全部是 change")

    current = items[0]["value"]
    bars = [{"start": 0.0, "end": current, **items[0]}]
    for item in items[1:-1]:
        before = current
        current += item["value"]
        bars.append({"start": before, "end": current, **item})
    tolerance = max(1e-9, abs(current) * 1e-6)
    if abs(items[-1]["value"] - current) > tolerance:
        raise ValueError("end.value 必须等于 start 加全部 change")
    bars.append({"start": 0.0, "end": current, **items[-1]})
    endpoints = [0.0] + [
        value for bar in bars for value in (bar["start"], bar["end"])
    ]
    y_min, y_max = min(endpoints), max(endpoints)
    pad = (y_max - y_min) * 0.12 or 1.0
    model = {"items": bars, "y_min": y_min - pad, "y_max": y_max + pad}
    return canvas_html(meta, "waterfall", model, aria_label="数值桥接瀑布图")


def render_timeline(data):
    meta = common_meta(data)
    raw_events = data.get("events")
    if not isinstance(raw_events, list) or not 2 <= len(raw_events) <= 10:
        raise ValueError("events 必须包含 2–10 项")
    events = []
    for index, raw in enumerate(raw_events):
        if not isinstance(raw, dict):
            raise ValueError(f"events[{index}] 必须是对象")
        events.append(
            {
                "date": iso_date(raw.get("date"), f"events[{index}].date"),
                "label": text_value(
                    raw.get("label"), f"events[{index}].label", max_length=12
                ),
                "category": text_value(
                    raw.get("category"),
                    f"events[{index}].category",
                    default="事件",
                    max_length=16,
                ),
                "note": text_value(
                    raw.get("note"), f"events[{index}].note", max_length=24
                ),
            }
        )
    if any(not event["label"] for event in events):
        raise ValueError("events.label 不能为空")
    if [event["date"] for event in events] != sorted(
        event["date"] for event in events
    ):
        raise ValueError("events 必须按日期升序")
    categories = []
    for event in events:
        if event["category"] not in categories:
            categories.append(event["category"])
    return canvas_html(
        meta,
        "timeline",
        {"events": events, "categories": categories},
        aria_label="事件与催化剂时间线",
    )


def mix_color(start, end, ratio):
    ratio = max(0.0, min(1.0, ratio))
    a = tuple(int(start[index : index + 2], 16) for index in (1, 3, 5))
    b = tuple(int(end[index : index + 2], 16) for index in (1, 3, 5))
    rgb = tuple(
        round(a[index] + (b[index] - a[index]) * ratio) for index in range(3)
    )
    return "#" + "".join(f"{value:02X}" for value in rgb)


def contrast_text(background):
    red, green, blue = (
        int(background[index : index + 2], 16) for index in (1, 3, 5)
    )
    luminance = 0.2126 * red + 0.7152 * green + 0.0722 * blue
    return "#FFFFFF" if luminance < 135 else INK


def render_heatmap(data):
    meta = common_meta(data)
    x_labels = data.get("x_labels")
    y_labels = data.get("y_labels")
    if not isinstance(x_labels, list) or not 2 <= len(x_labels) <= 16:
        raise ValueError("x_labels 必须包含 2–16 项")
    if not isinstance(y_labels, list) or not 2 <= len(y_labels) <= 16:
        raise ValueError("y_labels 必须包含 2–16 项")
    x_labels = [
        text_value(value, f"x_labels[{index}]", max_length=20)
        for index, value in enumerate(x_labels)
    ]
    y_labels = [
        text_value(value, f"y_labels[{index}]", max_length=20)
        for index, value in enumerate(y_labels)
    ]
    if any(not value for value in x_labels + y_labels):
        raise ValueError("x_labels 与 y_labels 不得为空")
    raw_values = data.get("values")
    if not isinstance(raw_values, list) or len(raw_values) != len(y_labels):
        raise ValueError("values 行数必须等于 y_labels")
    values = []
    flat = []
    for row_index, row in enumerate(raw_values):
        if not isinstance(row, list) or len(row) != len(x_labels):
            raise ValueError(f"values[{row_index}] 列数必须等于 x_labels")
        parsed = [
            finite_number(value, f"values[{row_index}][{column_index}]")
            for column_index, value in enumerate(row)
        ]
        values.append(parsed)
        flat.extend(parsed)
    scale = data.get("scale", "diverging")
    if scale not in {"diverging", "sequential"}:
        raise ValueError("scale 必须是 diverging 或 sequential")
    center = (
        finite_number(data.get("center"), "center")
        if data.get("center") is not None
        else (min(flat) + max(flat)) / 2
    )
    decimals = data.get("decimals", 1)
    if isinstance(decimals, bool) or not isinstance(decimals, int) or not 0 <= decimals <= 4:
        raise ValueError("decimals 必须是 0–4 的整数")
    baseline = data.get("baseline", {})
    if not isinstance(baseline, dict):
        raise ValueError("baseline 必须是对象")
    baseline_x = baseline.get("x")
    baseline_y = baseline.get("y")
    if baseline_x is not None and baseline_x not in x_labels:
        raise ValueError("baseline.x 不在 x_labels")
    if baseline_y is not None and baseline_y not in y_labels:
        raise ValueError("baseline.y 不在 y_labels")

    minimum, maximum = min(flat), max(flat)

    def color(value):
        if maximum == minimum:
            return "#EAF1FF"
        if scale == "sequential":
            return mix_color(
                "#EFF6FF", "#1D4ED8", (value - minimum) / (maximum - minimum)
            )
        if value <= center:
            ratio = 1.0 if center == minimum else (value - minimum) / (center - minimum)
            return mix_color("#DDE7F6", "#FFFFFF", ratio)
        ratio = 1.0 if maximum == center else (value - center) / (maximum - center)
        return mix_color("#FFFFFF", "#F3B7A6", ratio)

    rows = []
    header_cells = "".join(f"<th>{html.escape(label)}</th>" for label in x_labels)
    rows.append(f"<tr><th></th>{header_cells}</tr>")
    for row_index, label in enumerate(y_labels):
        cells = []
        for column_index, value in enumerate(values[row_index]):
            is_baseline = label == baseline_y and x_labels[column_index] == baseline_x
            classes = "baseline" if is_baseline else ""
            background = color(value)
            title = (
                f"{label} × {x_labels[column_index]}: "
                f"{number_text(value, decimals)}"
            )
            cells.append(
                f'<td class="{classes}" style="background:{background};'
                f'color:{contrast_text(background)}" title="{html.escape(title)}">'
                f"{number_text(value, decimals)}</td>"
            )
        rows.append(f"<tr><th>{html.escape(label)}</th>{''.join(cells)}</tr>")
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="use-iframe" content="true"><meta name="html-box-height-mode" content="auto"><title>{html.escape(meta["title"])}</title>
<style>
*{{box-sizing:border-box}}body{{margin:0;background:#fff;color:{INK};font-family:Inter,"Noto Sans SC","PingFang SC",Arial,sans-serif}}
.root{{padding:18px}}.card{{border:1px solid {GRID};border-radius:18px;padding:20px;box-shadow:0 10px 28px rgba(23,32,51,.07);overflow:auto}}
h1{{font-size:22px;margin:0}}.sub{{font-size:13px;color:{MUTED};margin:6px 0 16px}}table{{border-collapse:separate;border-spacing:4px;width:100%;min-width:560px}}
th{{font-size:12px;color:{MUTED};font-weight:600;padding:8px}}td{{height:48px;text-align:center;border-radius:8px;font-size:13px;font-weight:700;font-variant-numeric:tabular-nums;border:2px solid transparent;transition:transform .12s,border-color .12s}}
td:hover{{transform:scale(1.04);border-color:#344054}}td.baseline{{border-color:#7C3AED;box-shadow:inset 0 0 0 1px #fff}}footer{{font-size:11px;color:#98A2B3;margin-top:12px}}
</style></head><body><main class="root"><section class="card" aria-label="敏感性热力图"><h1>{html.escape(meta["title"])}</h1>
<div class="sub">{html.escape(meta["subtitle"])}</div><table>{"".join(rows)}</table><footer>{html.escape(note_text(meta))}</footer></section></main></body></html>'''


def render_flow(data):
    meta = common_meta(data)
    raw_nodes = data.get("nodes")
    if not isinstance(raw_nodes, list) or not 2 <= len(raw_nodes) <= 10:
        raise ValueError("nodes 必须包含 2–10 项")
    nodes = []
    ids = set()
    for index, raw in enumerate(raw_nodes):
        if not isinstance(raw, dict):
            raise ValueError(f"nodes[{index}] 必须是对象")
        node_id = text_value(raw.get("id"), f"nodes[{index}].id", max_length=24)
        title = text_value(raw.get("title"), f"nodes[{index}].title", max_length=24)
        if not node_id or node_id in ids:
            raise ValueError("nodes.id 不得为空或重复")
        if not title:
            raise ValueError("nodes.title 不能为空")
        ids.add(node_id)
        nodes.append(
            {
                "id": node_id,
                "title": title,
                "note": text_value(
                    raw.get("note"), f"nodes[{index}].note", max_length=60
                ),
                "tone": raw.get("tone", "neutral"),
            }
        )
        if nodes[-1]["tone"] not in {"neutral", "positive", "negative", "warning"}:
            raise ValueError("nodes.tone 必须是 neutral、positive、negative 或 warning")
    raw_edges = data.get("edges")
    if not isinstance(raw_edges, list) or not 1 <= len(raw_edges) <= 14:
        raise ValueError("edges 必须包含 1–14 项")
    edges = []
    for index, raw in enumerate(raw_edges):
        if not isinstance(raw, dict):
            raise ValueError(f"edges[{index}] 必须是对象")
        source = text_value(raw.get("from"), f"edges[{index}].from", max_length=24)
        target = text_value(raw.get("to"), f"edges[{index}].to", max_length=24)
        if source not in ids or target not in ids or source == target:
            raise ValueError("edges 的 from/to 必须引用不同的有效 nodes.id")
        edges.append(
            {
                "from": source,
                "to": target,
                "label": text_value(
                    raw.get("label"), f"edges[{index}].label", max_length=30
                ),
            }
        )
    incoming = {node_id: [] for node_id in ids}
    outgoing = {node_id: [] for node_id in ids}
    for edge in edges:
        incoming[edge["to"]].append(edge)
        outgoing[edge["from"]].append(edge)
    ordered_ids = [node["id"] for node in nodes]
    position = {node_id: index for index, node_id in enumerate(ordered_ids)}
    if any(position[edge["from"]] >= position[edge["to"]] for edge in edges):
        raise ValueError("nodes 必须按阅读顺序排列，edges 只能指向后续节点")

    cards = []
    for index, node in enumerate(nodes):
        incoming_labels = [
            edge["label"] for edge in incoming[node["id"]] if edge["label"]
        ]
        connector = ""
        if index:
            connector = (
                '<div class="connector"><span>→</span>'
                f'<small>{html.escape("；".join(incoming_labels[:2]))}</small></div>'
            )
        cards.append(
            connector
            + f'<article class="node {node["tone"]}"><div class="step">{index + 1:02d}</div>'
            + f'<h2>{html.escape(node["title"])}</h2><p>{html.escape(node["note"])}</p></article>'
        )
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="use-iframe" content="true"><meta name="html-box-height-mode" content="auto"><title>{html.escape(meta["title"])}</title>
<style>
*{{box-sizing:border-box}}body{{margin:0;background:#fff;color:{INK};font-family:Inter,"Noto Sans SC","PingFang SC",Arial,sans-serif}}.root{{padding:18px}}
.card{{border:1px solid {GRID};border-radius:18px;padding:20px;box-shadow:0 10px 28px rgba(23,32,51,.07);overflow:auto}}h1{{font-size:22px;margin:0}}
.sub{{font-size:13px;color:{MUTED};margin:6px 0 18px}}.flow{{display:flex;align-items:stretch;min-width:680px}}.node{{position:relative;flex:1;min-width:130px;padding:16px;border:1px solid #D8DEE8;border-radius:14px;background:#F7F9FC}}
.node.positive{{background:#EEFAF4;border-color:#A7DCC5}}.node.negative{{background:#FFF1F2;border-color:#F2B8BE}}.node.warning{{background:#FFF8E8;border-color:#F1D393}}
.step{{font-size:11px;font-weight:800;color:#2563EB}}h2{{font-size:15px;margin:8px 0 6px}}p{{font-size:12px;color:{MUTED};line-height:1.5;margin:0}}.connector{{width:58px;flex:0 0 58px;display:flex;flex-direction:column;align-items:center;justify-content:center;color:#98A2B3}}
.connector span{{font-size:24px}}.connector small{{font-size:10px;text-align:center;color:{MUTED};line-height:1.3}}footer{{font-size:11px;color:#98A2B3;margin-top:12px}}
</style></head><body><main class="root"><section class="card" aria-label="研究传导链"><h1>{html.escape(meta["title"])}</h1>
<div class="sub">{html.escape(meta["subtitle"])}</div><div class="flow">{"".join(cards)}</div><footer>{html.escape(note_text(meta))}</footer></section></main></body></html>'''


def self_test():
    trend = {
        "title": "收入与利润趋势",
        "categories": ["FY24", "FY25E", "FY26E"],
        "series": [
            {"name": "收入", "values": [100, 118, 136]},
            {"name": "利润", "values": [12, 16, 21]},
        ],
        "unit": "亿元",
    }
    trend_html = render_trend(trend)
    if "<canvas" not in trend_html or "FY26E" not in trend_html:
        raise AssertionError("趋势 HTML 自测失败")

    waterfall = {
        "title": "利润桥",
        "items": [
            {"label": "上期利润", "kind": "start", "value": 100},
            {"label": "销量", "kind": "change", "value": 20},
            {"label": "成本", "kind": "change", "value": -8},
            {"label": "本期利润", "kind": "end", "value": 112},
        ],
    }
    waterfall_html = render_waterfall(waterfall)
    if "<canvas" not in waterfall_html or "本期利润" not in waterfall_html:
        raise AssertionError("瀑布 HTML 自测失败")

    timeline = {
        "title": "催化剂时间线",
        "events": [
            {"date": "2026-08-01", "label": "产品发布", "category": "经营"},
            {"date": "2026-09-15", "label": "财报", "category": "财务"},
        ],
    }
    timeline_html = render_timeline(timeline)
    if "<canvas" not in timeline_html or "2026-09-15" not in timeline_html:
        raise AssertionError("时间线 HTML 自测失败")

    heatmap = {
        "title": "估值敏感性",
        "x_labels": ["7%", "8%", "9%"],
        "y_labels": ["2%", "3%", "4%"],
        "values": [[90, 82, 75], [101, 91, 82], [115, 102, 91]],
        "baseline": {"x": "8%", "y": "3%"},
    }
    heatmap_html = render_heatmap(heatmap)
    if "html-box-height-mode" not in heatmap_html or "baseline" not in heatmap_html:
        raise AssertionError("热力图 HTML 自测失败")

    flow = {
        "title": "行业变量传导",
        "nodes": [
            {"id": "supply", "title": "供给收缩", "note": "有效产能下降"},
            {"id": "price", "title": "产品涨价", "note": "单位售价上行", "tone": "positive"},
            {"id": "profit", "title": "盈利改善", "note": "毛利率扩张", "tone": "positive"},
        ],
        "edges": [
            {"from": "supply", "to": "price", "label": "供需缺口"},
            {"from": "price", "to": "profit", "label": "价格传导"},
        ],
    }
    flow_html = render_flow(flow)
    if 'class="flow"' not in flow_html or "供需缺口" not in flow_html:
        raise AssertionError("传导链 HTML 自测失败")

    broken = json.loads(json.dumps(waterfall))
    broken["items"][-1]["value"] = 999
    try:
        render_waterfall(broken)
    except ValueError:
        pass
    else:
        raise AssertionError("不平衡瀑布图应被拒绝")
    emit("SELF_TEST_PASS")


RENDERERS = {
    "trend": render_trend,
    "waterfall": render_waterfall,
    "timeline": render_timeline,
    "heatmap": render_heatmap,
    "flow": render_flow,
}


def build_parser():
    parser = argparse.ArgumentParser(description="生成飞书股票研究 HTML block 图表")
    parser.add_argument("--self-test", action="store_true")
    subparsers = parser.add_subparsers(dest="command")
    help_texts = {
        "trend": "生成多序列趋势 HTML block",
        "waterfall": "生成桥接瀑布 HTML block",
        "timeline": "生成事件时间线 HTML block",
        "heatmap": "生成敏感性热力图 HTML block",
        "flow": "生成传导链 HTML block",
    }
    for name, help_text in help_texts.items():
        sub = subparsers.add_parser(name, help=help_text)
        sub.add_argument("input_json")
        sub.add_argument("--output", required=True)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.self_test:
        self_test()
        return 0
    if args.command is None:
        parser.error(
            "请选择 trend、waterfall、timeline、heatmap 或 flow，或使用 --self-test"
        )
    try:
        data = load_object(args.input_json)
        output = write_output(
            args.output, RENDERERS[args.command](data), args.input_json
        )
    except Exception as exc:
        emit(f"[错误] {exc}")
        return 1
    emit(f"已生成: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
