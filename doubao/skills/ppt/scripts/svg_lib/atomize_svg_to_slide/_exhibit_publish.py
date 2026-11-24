"""Compose a page, upload it to a Feishu deck and report only what the author must fix."""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from ._compose import compose_slide

_SML = "https://www.larkoffice.com/sml/2.0"
_GENERATED_ONLY = {"bbox_overlap", "embed_svg_bbox_overlap", "text_overflows_container"}


def _run(args, cwd):
    try:
        proc = subprocess.run(["lark-cli", *args], capture_output=True, text=True, cwd=cwd, timeout=120)
    except subprocess.TimeoutExpired:   # a hung CLI call becomes an ordinary failure, not a stuck publish
        return {"ok": False, "error": {"code": "cli_timeout", "message": f"lark-cli {args[:2]} 120 秒没返回：服务端超时，稍后重试同一调用"}}
    decoder = json.JSONDecoder()
    for text in (proc.stdout or "", proc.stderr or ""):
        # The CLI response is the last top-level JSON object; notices or warnings may precede it.
        starts = [m.start() for m in re.finditer(r"(?m)^\{", text)] + [m.start() for m in re.finditer(r"\{", text)][:1]
        for start in sorted(set(starts), reverse=True):
            try:
                obj, _ = decoder.raw_decode(text, start)
            except ValueError:
                continue
            if isinstance(obj, dict) and "ok" in obj:
                return obj
    return {"ok": False, "error": {"message": ((proc.stdout or "") + (proc.stderr or ""))[-2000:]}}


def _children(page_xml):
    root = ET.fromstring(page_xml)
    data = root.find(f"{{{_SML}}}data")
    return [] if data is None else [c for c in data if isinstance(c.tag, str)]


def _element_index(path):
    """slide[1]/data/shape[23] -> ('shape', 23)."""
    m = re.search(r"data/(\w+)\[(\d+)\]", path or "")
    return (m.group(1), int(m.group(2))) if m else (None, None)


def _is_text(el):
    return el.tag.endswith("shape") and el.get("type") == "text" and "".join(el.itertext()).strip() != ""


def _light_rule(el):
    """A thin light line (gridline / table row rule): text drawn over it stays readable."""
    if not el.tag.endswith(("line", "polyline")):
        return False
    border = next((c for c in el if isinstance(c.tag, str) and c.tag.endswith("border")), None)
    if border is None:
        return False
    m = re.findall(r"[\d.]+", border.get("color") or "")
    try:
        r, g, b = (float(v) for v in m[:3])
        width = float(border.get("width") or 1)
    except ValueError:
        return False
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255 >= 0.78 and width <= 1.5


def _spills(text_el, box_el):
    """The text belongs to the box (mostly inside it) but part of it runs out — a real overflow; a label that only
    grazes a background shape it was never placed in is not."""
    try:
        tx, ty, tw_, th = (float(text_el.get(k)) for k in ("topLeftX", "topLeftY", "width", "height"))
        bx, by_, bw, bh = (float(box_el.get(k)) for k in ("topLeftX", "topLeftY", "width", "height"))
    except (TypeError, ValueError):
        return True
    inter = max(0.0, min(tx + tw_, bx + bw) - max(tx, bx)) * max(0.0, min(ty + th, by_ + bh) - max(ty, by_))
    return inter >= 0.5 * max(tw_ * th, 1.0)


def _classify(page_xml, generated_ids, errors):
    """Split lint errors into (ignorable, to_report)."""
    kids = _children(page_xml)
    by_tag = {}
    for i, el in enumerate(kids):
        by_tag.setdefault(el.tag.split("}")[-1], []).append(i)

    def node(path):
        tag, n = _element_index(path)
        if tag is None or tag not in by_tag or n > len(by_tag[tag]):
            return None, None
        i = by_tag[tag][n - 1]
        return i, kids[i]

    def box(el):
        try:
            return tuple(float(el.get(k)) for k in ("topLeftX", "topLeftY", "width", "height"))
        except (TypeError, ValueError):
            return None

    # Lint resolves text contrast against native fills only; generated text drawn over a generated local SVG
    # (a protein lobe, a dark wedge) is compared with the page background instead and misreported.
    embeds = [box(kids[i]) for i in generated_ids if i < len(kids) and kids[i].tag.endswith("embed") and box(kids[i])]

    def over_embed(el):
        b = box(el)
        return b is not None and any(
            e[0] - 0.5 <= b[0]
            and e[1] - 0.5 <= b[1]
            and b[0] + b[2] <= e[0] + e[2] + 0.5
            and b[1] + b[3] <= e[1] + e[3] + 0.5
            for e in embeds
        )

    ignorable, report = [], []
    for err in errors:
        code = err.get("code") or (err.get("rule") or {}).get("id")
        paths = list(err.get("elements") or []) + [o.get("xml_path") for o in err.get("related_objects") or []]
        paths = [p for p in dict.fromkeys(paths) if p]
        hits = [node(p) for p in paths]
        if (
            code == "text_color_contrast"
            and hits
            and all(i is not None and i in generated_ids and over_embed(el) for i, el in hits)
        ):
            ignorable.append(err)
        elif code in _GENERATED_ONLY and hits and all(i is not None and i in generated_ids for i, _ in hits):
            # Inside generated output only collisions that do not touch readable text are conversion noise
            # (gridlines through bars, adjacent marks). Text under a dark line / filled shape / other text, and text
            # spilling out of the box it sits in, are what a reader sees — those are reported.
            texts = [el for _, el in hits if _is_text(el)]
            others = [el for _, el in hits if not _is_text(el)]
            if code == "bbox_overlap":
                if not texts or (len(texts) == 1 and others and all(_light_rule(el) for el in others)):
                    ignorable.append(err)
                else:
                    report.append(err)
            elif code == "text_overflows_container":
                if texts and others and _spills(texts[0], others[0]):
                    report.append(err)
                else:
                    ignorable.append(err)
            else:
                ignorable.append(err)
        elif code == "embed_svg_bbox_overlap" and all(i in generated_ids for i, _ in hits if i is not None):
            ignorable.append(err)
        else:
            report.append(err)
    return ignorable, report


def _describe(page_xml, err, generated=(), origins=None):
    """One lint finding with everything needed to locate and fix it."""
    kids = _children(page_xml)
    by_tag = {}
    for i, el in enumerate(kids):
        by_tag.setdefault(el.tag.split("}")[-1], []).append(i)
    objs = []
    paths = [o.get("xml_path") for o in err.get("related_objects") or []] or list(err.get("elements") or [])
    boxes = {o.get("xml_path"): o.get("bbox") or {} for o in err.get("related_objects") or []}
    for path in dict.fromkeys(p for p in paths if p):
        tag, n = _element_index(path)
        entry = {"path": path}
        if tag in by_tag and n and n <= len(by_tag[tag]):
            idx = by_tag[tag][n - 1]
            el = kids[idx]
            entry["element"] = tag + (f'[type="{el.get("type")}"]' if el.get("type") else "")
            text = " ".join("".join(el.itertext()).split())
            if text:
                entry["text"] = text[:40]
            authored = [el.get(k) for k in ("topLeftX", "topLeftY", "width", "height")]
            if all(v is not None for v in authored):
                entry["xml_box"] = [round(float(v), 1) for v in authored]
            elif tag == "line":
                entry["xml_line"] = [round(float(el.get(k, 0)), 1) for k in ("startX", "startY", "endX", "endY")]
            fs = re.search(r'fontSize="([\d.]+)"', ET.tostring(el, encoding="unicode"))
            if fs:
                entry["font_size"] = float(fs.group(1))
            if el.get("id"):
                entry["id"] = el.get("id")
            entry["source"] = (origins or {}).get(idx) or ("generated" if idx in generated else "page_xml")
        b = boxes.get(path)
        if b:
            entry["lint_box"] = [round(b.get(k, 0), 1) for k in ("x", "y", "width", "height")]
        objs.append(entry)
    out = {
        "key": _key(err.get("code"), objs),
        "code": err.get("code"),
        "rule": (err.get("rule") or {}).get("name"),
        "message": err.get("message"),
        "objects": objs,
    }
    if err.get("measurement"):
        out["measurement"] = err["measurement"]
    if err.get("overflow"):
        out["overflow"] = err["overflow"]
    frags = sorted({o["source"] for o in objs if str(o.get("source", "")).startswith("fragment")})
    if frags:
        out["fragments"] = {f: _fragment_box(kids, origins or {}, f) for f in frags}
    out["fix"] = _suggest(out)
    unwrapped = _unwrapped_text(kids, by_tag, objs, err)
    if out["code"] == "image_covers_text" or (out["code"] == "text_may_overflow_shape"
                                              and _SERVER_LINE.search(str(err.get("message") or ""))):   # width axis only
        fit = _run_fit(kids, by_tag, objs)
        if fit:
            out["run_fit"] = fit
    if unwrapped:
        out["unwrapped_text"] = unwrapped
        out["fix"] = unwrapped["fix"]
    else:
        fit = _wrapped_fit(kids, by_tag, objs, err)
        if fit:
            out["wrapped_fit"] = fit
    if out["code"] == "text_overflows_container":
        deco = _decorative_container(kids, by_tag, objs)
        if deco:
            out["decorative_container"] = deco
    if out["code"] == "bbox_overlap" and not (err.get("measurement") or {}).get("intersection_area"):
        hidden = _line_not_over(kids, by_tag, objs)
        if hidden:
            out["line_not_over"] = hidden
    if out["code"] == "text_color_contrast":
        evidence = _contrast_evidence(page_xml, kids, objs, origins)
        if evidence:
            out["contrast"] = evidence
            out["fix"] = evidence["fix"]
        crossers = _over_text(kids, objs, origins)
        if crossers:
            out["covered_by"] = crossers
            out["fix"] = (
                "文字颜色本身没问题：服务端按压在文字框上的元素颜色算对比度，压住它的是 "
                + "、".join(
                    f"{c['element']} {c.get('xml_line') or c.get('xml_box')}（{c['source']}）" for c in crossers[:3]
                )
                + "。不要改颜色：把这条连线/色块绕开文字（示意图里连线两端传节点对象 d.arrow(a, b)，"
                "斜线外接框也不能盖住标签），或把标签挪离它。"
            )
    if err.get("hint"):
        out["hint"] = err["hint"]
    return out


def _contrast_evidence(page_xml, kids, objs, origins=None):
    """Which text, which colour, against which background (top-most layer first) and the ratio — the local"""
    target = next((o for o in objs if o.get("element", "").endswith('"text"]')), None)
    if not target:
        return None
    tag, n = _element_index(target["path"])
    try:
        import sys

        scripts = str(Path(__file__).resolve().parents[2])
        if scripts not in sys.path:
            sys.path.insert(0, scripts)
        import _exhibit_color_contrast_check as cc

        # lines judged by their stroke, not their bounding box: a value label beside a diagonal CAGR arrow sits on the
        # page / bar colour (the box made it read "text rgb(34,34,34) on rgb(34,34,34)" and authors switched labels off)
        records, slides = cc.parse_xml_root(ET.fromstring(page_xml), exact_lines=True)
        results, _ = cc.check(
            [r for r in records if r.get("object_path") == f"data/{tag}[{n}]"], slides, "", cc.DEFAULT_CONTRAST_GATE
        )
    except Exception:  # noqa: BLE001 — evidence is a convenience; the finding itself still stands
        return None
    rated = [r for r in results if r.get("contrast") is not None]
    if not rated:
        return None
    worst = min(rated, key=lambda r: r["contrast"])
    tx, ty, tw, th = worst["bbox"]
    idx = next(
        (
            i
            for i, el in enumerate(kids)
            if el.tag.split("}")[-1] == tag and sum(1 for k in kids[: i + 1] if k.tag == el.tag) == n
        ),
        None,
    )
    under = []
    for i in range(len(kids) - 1, -1, -1):  # top-most first
        el = kids[i]
        if idx is None or i >= idx or el.tag.split("}")[-1] not in ("shape", "embed", "img", "table", "line"):
            continue
        try:
            bx = cc.element_bbox(el)
        except Exception:  # noqa: BLE001
            continue
        if not (bx[0] < tx + tw and tx < bx[0] + bx[2] and bx[1] < ty + th and ty < bx[1] + bx[3]):
            continue
        local = el.tag.split("}")[-1]
        color = cc.border_color(el) if local == "line" else cc.fill_color(el)
        if local == "shape" and not color:
            continue
        under.append(
            {
                "element": local + (f'[type="{el.get("type")}"]' if el.get("type") else ""),
                "box": [round(v, 1) for v in bx],
                "color": color or ("局部 SVG，lint 看不到其颜色" if local == "embed" else None),
                "source": (origins or {}).get(i, "page_xml"),
            }
        )
    diag = []   # diagonal lines (any paint order) whose bounding box — not stroke — covers the text: server false positive
    for el in kids:
        if el.tag.split("}")[-1] != "line":
            continue
        try:
            x1, y1, x2, y2 = (float(el.get(k, 0)) for k in ("startX", "startY", "endX", "endY"))
        except ValueError:
            continue
        if abs(x2 - x1) > 2 and abs(y2 - y1) > 2 and min(x1, x2) < tx + tw and tx < max(x1, x2) \
                and min(y1, y2) < ty + th and ty < max(y1, y2):
            diag.append([round(v, 1) for v in (x1, y1, x2, y2)])
    page_bg = (slides.get(1) or {}).get("page_bg") or "rgb(255,255,255)（默认白底）"
    out = {
        "text": worst["text"][:40],
        "text_color": worst.get("effective_fg_color") or worst["fg_color"],
        "gradient_text": idx is not None and bool(re.search(r'color="[^"]*gradient', ET.tostring(kids[idx], encoding="unicode"))),
        "background": worst.get("effective_bg_color"),
        "ratio": round(worst["contrast"], 2),
        "required": round(worst.get("required_contrast") or cc.DEFAULT_CONTRAST_GATE, 2),
        "under_text": under[:3] or [{"element": "页面背景", "color": page_bg}],
        "diagonal_box": diag[:3],
    }
    bg_desc = "、".join(
        f"{u['element']} {u.get('color')}" + (f" @{u['box']}" if u.get("box") else "") for u in out["under_text"]
    )
    if worst["contrast"] >= out["required"]:
        verdict = f"本地按 XML 复算 {out['ratio']}:1 已达标（≥{out['required']}），多半是误报"
    else:
        verdict = f"本地按 XML 复算 {out['ratio']}:1 < {out['required']}"
    embed_note = (
        "；文字下是局部 SVG，lint 只按其下方原生底色算，常是误报" if any(u["element"] == "embed" for u in under) else ""
    )
    out["fix"] = (
        f"「{out['text']}」文字色 {out['text_color']} 对背景 {out['background']}（下方依次为 {bg_desc}）："
        f"{verdict}{embed_note}。一步改：改深色字/浅底（或浅字配深底），或确认误报后 waive=[key]。"
    )
    return out


def _boxes_intersect(a, b, pad=0.0):
    return a[0] < b[0] + b[2] - pad and b[0] < a[0] + a[2] - pad and a[1] < b[1] + b[3] - pad and b[1] < a[1] + a[3] - pad


def _local_false_positive(d, business=True):
    """Server findings that local recomputation from the page XML shows to be false positives → reason string, else "".
    text_color_contrast on gradient text (the server reads it as the default dark colour): the local check, which judges
    a gradient by its worst stop colour, passes, nothing drawn across
    the text and no local SVG under it (lint cannot see SVG colours). image_covers_text: the authored image box and the
    text box do not intersect and the text does not run past its box unwrapped (wrap=false big numbers).
    text_may_overflow_shape on wrap=true text whose locally wrapped height (lines × font size × line spacing) fits.
    ``business``: a decorative / scrim "container" is only trusted on business decks (light borderless cards elsewhere
    are real containers)."""
    code = d.get("code")
    if code == "text_may_overflow_shape" and d.get("run_fit"):
        f = d["run_fit"]
        reason = (f"wrap=false 按每段 span 的字号 / 字体（窄体 ×{CONDENSED_RATIO:g}）复算单行 {f['run_width']:g}px，"
                  f"×{RUN_FIT_SLACK:g} 仍 ≤ 框宽 {f['box_w']:g}")
        d["auto_waived"] = reason
        return reason
    if code == "bbox_overlap" and d.get("line_not_over"):
        reason = f"0px 重叠：{d['line_not_over']}，看不到线压住什么"
        d["auto_waived"] = reason
        d["fix"] = reason
        return reason
    if code == "text_overflows_container" and business and d.get("decorative_container"):
        reason = f"底框是装饰性的低透明度 / 渐隐蒙版形状（{d['decorative_container']}），不是文字容器"
        d["auto_waived"] = reason
        d["fix"] = reason   # _suggest's "不是误报" would keep it refused
        return reason
    if code == "text_overflows_container":
        graze = _container_graze(d)
        if graze:
            d["auto_waived"] = graze
            d["fix"] = graze
            return graze
    if code == "text_may_overflow_shape" and d.get("wrapped_fit") and not d.get("unwrapped_text"):
        b = d["wrapped_fit"]["boxes"][0]
        reason = f"wrap=true 按框宽换行 {b['lines']} 行、高约 {b['height']:g}px ≤ 框高 {b['box_h']:g}"
        d["auto_waived"] = reason
        return reason
    if code == "text_color_contrast":
        ev = d.get("contrast") or {}
        if (ev.get("ratio") is not None and ev["ratio"] >= ev.get("required", 99) and not d.get("covered_by")
                and not ev.get("gradient_text") and ev.get("diagonal_box")
                and not any(u.get("element") in ("embed", "img") for u in ev.get("under_text") or [])):
            # the server took a diagonal line's bounding box for the label's background; the stroke itself is clear
            reason = f"斜线外接框误判：按线条本身复算 {ev['ratio']}:1 ≥ {ev['required']}（文字下是页面/柱的颜色）"
            d["auto_waived"] = reason
            return reason
        if (ev.get("gradient_text") and ev.get("ratio") is not None
                and ev["ratio"] >= ev.get("required", 99) and not d.get("covered_by")
                and not any(u.get("element") == "embed" for u in ev.get("under_text") or [])):
            reason = f"渐变字按最差停靠色复算 {ev['ratio']}:1 ≥ {ev['required']}"
            d["auto_waived"] = reason
            return reason
    if code == "image_covers_text" and (not d.get("unwrapped_text") or d.get("run_fit")):
        objs = d.get("objects") or []
        imgs = [o["xml_box"] for o in objs if str(o.get("element", "")).startswith("img") and o.get("xml_box")]
        texts = [o["xml_box"] for o in objs if str(o.get("element", "")).endswith('"text"]') and o.get("xml_box")]
        if d.get("run_fit"):   # the line is narrower than the server thinks: judge where its glyphs really end
            texts = [d["run_fit"]["glyph_box"]]
        if imgs and texts and not any(_boxes_intersect(i, t) for i in imgs for t in texts):
            reason = f"图框 {imgs[0]} 与文字框 {texts[0]} 按 XML 不相交"
            d["auto_waived"] = reason
            return reason
    return ""


DECOR_MAX_ALPHA = 0.30   # a shape whose fill never gets more opaque than this, carries no text: a glow, not a text box


def _container_graze(d):
    """Server text_overflows_container where the authored text frame only grazes the "container" (xml_lint's
    container_contact_is_graze: < 2px side-by-side overlap, or ≤ 2px poking out). Description, else ""."""
    objs = d.get("objects") or []
    text = next((o for o in objs if str(o.get("element", "")).endswith('"text"]') and o.get("xml_box")), None)
    box = next((o for o in objs if o is not text and o.get("xml_box")), None)
    if not text or not box:
        return ""
    t = dict(zip(("x", "y", "width", "height"), text["xml_box"]))
    b = dict(zip(("x", "y", "width", "height"), box["xml_box"]))
    ov = {"left": max(b["x"] - t["x"], 0), "top": max(b["y"] - t["y"], 0),
          "right": max(t["x"] + t["width"] - b["x"] - b["width"], 0),
          "bottom": max(t["y"] + t["height"] - b["y"] - b["height"], 0)}
    try:
        import sys

        scripts = str(Path(__file__).resolve().parents[2])
        if scripts not in sys.path:
            sys.path.insert(0, scripts)
        from _exhibit_xml_lint import container_contact_is_graze
    except Exception:  # noqa: BLE001
        return ""
    if not any(v > 0 for v in ov.values()) or not container_contact_is_graze(t, b, ov):
        return ""
    return f"文字框 {text['xml_box']} 只与底框 {box['xml_box']} 相切（交叠 / 越出 ≤2px），不在框里"


def _fill_max_alpha(el):
    """Highest alpha of a shape's fill colour stops (rgba / gradient stops; rgb / hex = 1); None without a fill colour."""
    fill = next((c for c in el.iter() if c.tag.split("}")[-1] == "fillColor"), None)
    color = (fill.get("color") or "").strip() if fill is not None else ""
    if not color:
        return None
    alphas = [float(a) for a in re.findall(r"rgba\(\s*[\d.]+\s*,\s*[\d.]+\s*,\s*[\d.]+\s*,\s*([\d.]+)\s*\)", color)]
    opaque = len(re.findall(r"rgb\(|#[0-9A-Fa-f]{3,8}\b", color))
    try:
        op = float(fill.get("opacity") or el.get("alpha") or 1)
    except ValueError:
        op = 1.0
    return max(alphas + [1.0] * opaque or [1.0]) * op


def _decorative_container(kids, by_tag, objs):
    """text_overflows_container whose "container" is a decorative shape — no text of its own, no visible border, fill
    alpha ≤ DECOR_MAX_ALPHA at every stop (a radial glow behind a slogan), or a scrim — description, else ""."""
    for o in objs:
        if o.get("element", "").endswith('"text"]'):
            continue
        tag, n = _element_index(o.get("path"))
        if tag not in by_tag or not n or n > len(by_tag[tag]):
            return ""
        el = kids[by_tag[tag][n - 1]]
        if "".join(el.itertext()).strip():
            return ""
        border = next((c for c in el if isinstance(c.tag, str) and c.tag.split("}")[-1] == "border"), None)
        if border is not None and border.get("color") and (border.get("width") or "1") not in ("0", "0.0"):
            m = re.findall(r"rgba\([^)]*,\s*([\d.]+)\s*\)", border.get("color"))
            if not m or max(float(v) for v in m) > 0.05:
                return ""
        a = _fill_max_alpha(el)
        if a is None:
            return ""
        if a <= DECOR_MAX_ALPHA:
            return f'{tag}[type="{el.get("type")}"] 填充最高不透明度 {a:.2f}'
        scrim = _scrim_fade(el)
        return f'{tag}[type="{el.get("type")}"] {scrim}' if scrim else ""
    return ""


SCRIM_MIN_AREA = 0.30   # share of the 960×540 canvas: a gradient fading to transparent this large is an image scrim


def _line_not_over(kids, by_tag, objs):
    """bbox_overlap of a <line> that covers nothing visible — description, else "":
    - the other object is a solid filled node drawn AFTER the line (a timeline / flow baseline running under its white
      circle nodes): the node paints over the line, the line shows only between nodes;
    - the other object is a text box and the straight line lies outside the text's lines, only through the box's empty
      margin (a footer rule under a two-line note in a taller middle-aligned box)."""
    els = []
    for o in objs:
        tag, n = _element_index(o.get("path"))
        if tag not in by_tag or not n or n > len(by_tag[tag]):
            return ""
        els.append((by_tag[tag][n - 1], kids[by_tag[tag][n - 1]]))
    lines = [(i, e) for i, e in els if e.tag.split("}")[-1] == "line"]
    if len(els) != 2 or len(lines) != 1:
        return ""
    li, line = lines[0]
    oi, other = next((i, e) for i, e in els if i != li)
    try:
        x1, y1, x2, y2 = (float(line.get(k) or 0) for k in ("startX", "startY", "endX", "endY"))
    except ValueError:
        return ""
    if other.tag.split("}")[-1] == "shape" and other.get("type") != "text":
        fill = next((c for c in other.iter() if c.tag.split("}")[-1] == "fillColor"), None)
        color = (fill.get("color") or "") if fill is not None else ""
        alphas = [float(a) for a in re.findall(r"rgba\(\s*[\d.]+\s*,\s*[\d.]+\s*,\s*[\d.]+\s*,\s*([\d.]+)\s*\)", color)]
        solid = color and "gradient" not in color and (min(alphas) if alphas else 1.0) >= 0.95
        try:
            solid = solid and float(other.get("alpha") or 1) >= 0.95
        except ValueError:
            solid = False
        if oi > li and solid:
            return f"线画在实心 {other.get('type')} 节点下层，被节点盖住"
        return ""
    if not _is_text(other) or (abs(y2 - y1) > 0.5 and abs(x2 - x1) > 0.5):
        return ""
    try:
        import sys

        scripts = str(Path(__file__).resolve().parents[2])
        if scripts not in sys.path:
            sys.path.insert(0, scripts)
        import _exhibit_xml_lint as _lint

        src = re.sub(r"\sxmlns(?::\w+)?=\"[^\"]*\"", "", re.sub(r"<(/?)\w+:", r"<\1", ET.tostring(other, encoding="unicode")))
        el = next(e for e in _lint.extract_elements(f'<slide xmlns="{_SML}"><data>{src}</data></slide>')
                  if _lint.is_text_element(e))
        if abs(y2 - y1) <= 0.5:   # horizontal: compare with the span the text lines take, anchored like the renderer
            block = _lint.estimate_text_block_height(el)
            inner = el["height"] - el.get("paddingTop", 0) - el.get("paddingBottom", 0)
            if not block or block["estimated_height"] > inner:
                return ""
            top = el["y"] + el.get("paddingTop", 0)
            va = el.get("verticalAlign") or "middle"
            top += (inner - block["estimated_height"]) / 2 if va == "middle" else inner - block["estimated_height"] \
                if va == "bottom" else 0
            bottom = top + block["estimated_height"]
            if top < y1 < bottom:
                return ""
            return f"横线 y={y1:g} 在文字行（y {top:.0f}–{bottom:.0f}）之外，只经过文字框的空白边距"
        glyph = _lint.estimate_text_visual_bbox(el)
        if not glyph or glyph["x"] < x1 < glyph["x"] + glyph["width"]:
            return ""
        return f"竖线 x={x1:g} 在文字（x {glyph['x']:.0f}–{glyph['x'] + glyph['width']:.0f}）之外，只经过文字框的空白边距"
    except Exception:  # noqa: BLE001
        return ""


def _scrim_fade(el):
    """A cover / hero scrim: gradient fill with a stop at alpha ≤ 0.05 (fades out over the picture) covering ≥
    SCRIM_MIN_AREA of the canvas (white 0.95 → 0 over a full-bleed photo). A card base
    has no transparent stop and is far smaller, so it stays a container. Description, else ""."""
    fill = next((c for c in el.iter() if c.tag.split("}")[-1] == "fillColor"), None)
    color = (fill.get("color") or "") if fill is not None else ""
    if "gradient" not in color:
        return ""
    alphas = [float(a) for a in re.findall(r"rgba\(\s*[\d.]+\s*,\s*[\d.]+\s*,\s*[\d.]+\s*,\s*([\d.]+)\s*\)", color)]
    try:
        area = float(el.get("width") or 0) * float(el.get("height") or 0)
    except ValueError:
        return ""
    if not alphas or min(alphas) > 0.05 or area < SCRIM_MIN_AREA * 960 * 540:
        return ""
    return f"渐变渐隐到透明的大面积蒙版（{area / (960 * 540):.0%} 画布）"


def _key(code, objs):
    return f"{code}:" + "+".join(sorted(o.get("id") or o["path"] for o in objs))


_TEXT_CODES = {
    "bbox_overlap",
    "embed_svg_bbox_overlap",
    "text_overflows_container",
    "text_may_overflow_shape",
    "text_out_of_slide",
    "element_out_of_slide",
}


def _kind_of(o):
    """What kind of object a described lint entry is, in the words the author uses."""
    el, src = o.get("element", ""), str(o.get("source", ""))
    what = (
        "文字框"
        if el.endswith('"text"]')
        else "嵌入 SVG"
        if el.startswith("embed")
        else "线"
        if el == "line"
        else "图形"
    )
    m = re.fullmatch(r"fragment\[(\d+)\]", src)
    if m:
        return f"第 {int(m.group(1)) + 1} 个片段（chart_slide/to_slide）的{what}"
    return f"页面手写{what}"


def _single_line_width(el, text):
    fs = re.search(r'fontSize="([\d.]+)"', ET.tostring(el, encoding="unicode"))
    size = float(fs.group(1)) if fs else 16.0
    try:
        import sys

        scripts = str(Path(__file__).resolve().parents[2])
        if scripts not in sys.path:
            sys.path.insert(0, scripts)
        from _exhibit_xml_lint import estimate_text_width

        bold = 'bold="true"' in ET.tostring(el, encoding="unicode")
        return max(estimate_text_width(line, size, 0, bold) for line in text.split("\n"))
    except Exception:  # noqa: BLE001 — a rough estimate is enough for the hint
        return max(sum(size if ord(c) > 0x2E80 else size * 0.55 for c in line) for line in text.split("\n"))


_SERVER_LINE = re.compile(r"estimated line\s*([\d.]+)\s*px", re.I)

# Condensed display faces (keynote big numbers): Latin glyphs render at 0.60–0.80 of the sans estimate; 0.82 ≥ the worst.
_CONDENSED_FONTS = ("anton", "bebas", "oswald", "impact", "condensed", "narrow", "compressed", "league gothic", "fjalla")
CONDENSED_RATIO = 0.82


def _run_line_width(el):
    """Widest paragraph of a text shape measured run by run — each <span>'s own fontSize / fontFamily / bold, Latin glyphs
    of a condensed face × CONDENSED_RATIO. The server measures the whole box at the base size with sans widths, so
    "8000<span fontSize=44> 次</span>" in Anton comes back ~2× too wide. None when the estimator is unavailable."""
    try:
        import sys

        scripts = str(Path(__file__).resolve().parents[2])
        if scripts not in sys.path:
            sys.path.insert(0, scripts)
        from _exhibit_xml_lint import estimate_text_width, is_cjk_char
    except Exception:  # noqa: BLE001
        return None
    content = next((c for c in el.iter() if c.tag.split("}")[-1] == "content"), None)
    if content is None:
        return None

    def attrs(node, base):
        size = node.get("fontSize")
        return (float(size) if size else base[0], node.get("fontFamily") or base[1],
                (node.get("bold") == "true") if node.get("bold") else base[2])

    def width(text, a):
        size, family, bold = a
        latin = "".join(ch for ch in text if not is_cjk_char(ch))
        cjk = "".join(ch for ch in text if is_cjk_char(ch))
        w_latin = estimate_text_width(latin, size, 0, bold, family, bool(cjk)) if latin else 0.0
        if any(m in (family or "").lower() for m in _CONDENSED_FONTS):
            w_latin *= CONDENSED_RATIO
        return w_latin + (estimate_text_width(cjk, size, 0, bold, family, True) if cjk else 0.0)

    base = attrs(content, (16.0, "", False))
    widths = []
    for p in [c for c in content if c.tag.split("}")[-1] == "p"] or [content]:
        pa = attrs(p, base)
        runs = [(p.text or "", pa)]
        for s in p.iter():
            if s is p:
                continue
            sa = attrs(s, pa)
            runs += [(s.text or "", sa), (s.tail or "", pa)]
        text = "".join(t for t, _ in runs)
        if not text.strip():
            continue
        lead = len(text) - len(text.lstrip())
        trail = len(text) - len(text.rstrip())
        total, pos = 0.0, 0
        for t, a in runs:   # leading / trailing blanks are trimmed by the renderer
            s0, s1 = max(lead - pos, 0), max(len(t) - max(pos + len(t) - (len(text) - trail), 0), 0)
            total += width(t[s0:s1], a) if s1 > s0 else 0.0
            pos += len(t)
        widths.append(total)
    return max(widths) if widths else None


RUN_FIT_SLACK = 1.06   # the per-run width × this must still fit the box for the server finding to be waived


def _run_fit(kids, by_tag, objs):
    """The hand-written wrap=false text box of a finding whose per-run width (_run_line_width) × RUN_FIT_SLACK fits its
    box: {path, run_width, box_w, glyph_box (where its glyphs really end, by alignment)}; None otherwise."""
    for o in objs:
        if o.get("source") != "page_xml" or not o.get("element", "").endswith('"text"]') or not o.get("xml_box"):
            continue
        tag, n = _element_index(o["path"])
        if tag not in by_tag or not n or n > len(by_tag[tag]):
            continue
        el = kids[by_tag[tag][n - 1]]
        if not any(c.get("wrap") in ("false", "0") for c in el.iter() if c.tag.split("}")[-1] in ("content", "p")):
            continue
        run_w = _run_line_width(el)
        bx, by_, box_w, bh = o["xml_box"]
        if not run_w or run_w * RUN_FIT_SLACK > box_w:
            return None
        gw = run_w * RUN_FIT_SLACK
        align = next((c.get("textAlign") for c in el.iter() if c.get("textAlign")), "left")
        gx = bx + (box_w - gw) / 2 if align == "center" else bx + box_w - gw if align == "right" else bx
        return {"path": o["path"], "run_width": round(run_w, 1), "box_w": box_w,
                "glyph_box": [round(gx, 1), by_, round(gw, 1), bh]}
    return None


def _server_line_width(err):
    """The one-line width the server measured ("... (estimated line 528px, available 504px)"), else 0."""
    m = _SERVER_LINE.search(str(err.get("message") or ""))
    try:
        return float(m.group(1)) if m else 0.0
    except ValueError:
        return 0.0


def _server_available(err):
    m = re.search(r"available\s*([\d.]+)\s*px", str(err.get("message") or ""), re.I)
    return float(m.group(1)) if m else 0.0


def _line_height(spacing, size):
    m = re.fullmatch(r"(multiple|fixed):([\d.]+)", str(spacing or "multiple:1.5"))
    if not m:
        return size * 1.5
    return size * float(m.group(2)) if m.group(1) == "multiple" else float(m.group(2))


def _wrapped_fit(kids, by_tag, objs, err):
    """text_may_overflow_shape on wrap=true text: recompute the wrapped height locally (per paragraph: wrapped line count
    at the box width × font size × line spacing; a one-paragraph text takes at least as many lines as the server's
    estimated line width needs). Returns evidence when every flagged text box holds its text, else None."""
    if err.get("code") != "text_may_overflow_shape":
        return None
    server_w = _server_line_width(err)
    try:
        import sys

        scripts = str(Path(__file__).resolve().parents[2])
        if scripts not in sys.path:
            sys.path.insert(0, scripts)
        from _exhibit_xml_lint import count_wrapped_lines
    except Exception:  # noqa: BLE001 — without the estimator nothing is downgraded
        return None
    fits = []
    for o in objs:
        if not o.get("element", "").endswith('"text"]'):
            continue
        tag, n = _element_index(o["path"])
        if tag not in by_tag or not n or n > len(by_tag[tag]) or not o.get("xml_box"):
            return None
        el = kids[by_tag[tag][n - 1]]
        content = next((c for c in el.iter() if c.tag.split("}")[-1] == "content"), None)
        if content is None or any(c.get("wrap") in ("false", "0") for c in el.iter()):
            return None
        _, _, w, h = o["xml_box"]
        w = min(w, _server_available(err) or w)   # the server's inner width (box minus padding) when it says so
        base = float(content.get("fontSize") or 16)
        paras = [p for p in content.iter() if p.tag.split("}")[-1] == "p"] or [content]
        lines, height = 0, 0.0
        for p in paras:
            text = "".join(p.itertext()).strip()
            sizes = [float(s.get("fontSize")) for s in p.iter() if s.get("fontSize")] or [base]
            size = max(sizes)
            bold = any(s.get("bold") == "true" for s in [content, *p.iter()])
            k = count_wrapped_lines(text, size, 0, bold, None, max(w, 1)) if text else 1
            if len(paras) == 1 and server_w:
                k = max(k, -(-int(server_w) // max(int(w), 1)))
            lines += k
            height += k * _line_height(p.get("lineSpacing") or content.get("lineSpacing"), size)
        if height > h + 1:
            return None
        fits.append({"path": o["path"], "lines": lines, "height": round(height, 1), "box_h": h})
    return {"boxes": fits} if fits else None


def _unwrapped_text(kids, by_tag, objs, err):
    """A hand-written native text box with wrap="false" whose one-line width runs past its box: the real cause."""
    if (err.get("code") or "") not in _TEXT_CODES and "overflow" not in str(err.get("code") or ""):
        return None
    for o in objs:
        if o.get("source") != "page_xml" or not o.get("element", "").endswith('"text"]') or not o.get("xml_box"):
            continue
        tag, n = _element_index(o["path"])
        el = kids[by_tag[tag][n - 1]]
        flags = [c.get("wrap") for c in el.iter() if c.tag.split("}")[-1] in ("content", "p")]
        if not any(f in ("false", "0") for f in flags):
            continue
        x, y, w, h = o["xml_box"]
        text = "\n".join(
            " ".join("".join(p.itertext()).split()) for p in el.iter() if p.tag.split("}")[-1] == "p"
        ) or o.get("text", "")
        need = _single_line_width(el, text)
        lint_w = (o.get("lint_box") or [0, 0, 0])[2]
        need = max(need, lint_w, _server_line_width(err))
        if need <= w + 2:
            continue
        name = f"#{o['id']}" if o.get("id") else o["path"]
        others = [_kind_of(q) for q in objs if q is not o]
        tail = (
            "；不是图表/示意图的问题"
            if any(str(q.get("source", "")).startswith("fragment") for q in objs if q is not o)
            else ""
        )
        with_ = f"，压到{'、'.join(dict.fromkeys(others))}" if others else ""
        fix = (
            f"文字框 {name}「{text[:16]}」未开启换行，按单行测宽 {need:.0f}px 溢出到 x={x + need:.0f}"
            f'（框宽 {w:.0f}）{with_}：给 <shape type="text"> 的 <content> 设 wrap="true" 并留够高度，'
            f"或加宽/缩短文字{tail}"
        )
        return {
            "path": o["path"],
            "id": o.get("id"),
            "single_line_width": round(need, 1),
            "box": o["xml_box"],
            "fix": fix,
        }
    return None


WIDEN_MAX = 1.15   # wrap=false text whose one-line width exceeds its box by at most 15% is widened in place, not refused
_WIDEN_CODES = {"text_may_overflow_shape"}


WIDEN_SLACK, WIDEN_PAD = 1.06, 12   # widened box = max(server, local one-line width) × 1.06 + 12 (+8 came back short)
WIDEN_EDGE_MARGIN = 24   # auto-widen never pushes a box closer than this to the canvas edge (unless it already was)


def _box_of(el):
    try:
        return tuple(float(el.get(k)) for k in ("topLeftX", "topLeftY", "width", "height"))
    except (TypeError, ValueError):
        return None


def _glyph_box(el):
    """xml_lint's visual (glyph) box (x, y, w, h) of a native text shape element, or None."""
    try:
        import sys

        scripts = str(Path(__file__).resolve().parents[2])
        if scripts not in sys.path:
            sys.path.insert(0, scripts)
        import _exhibit_xml_lint as _lint

        src = re.sub(r"\sxmlns(?::\w+)?=\"[^\"]*\"", "", re.sub(r"<(/?)\w+:", r"<\1", ET.tostring(el, encoding="unicode")))
        for e in _lint.extract_elements(f'<slide xmlns="{_SML}"><data>{src}</data></slide>'):
            if _lint.is_text_element(e) and _lint.has_text_content(e):
                b = _lint.estimate_text_visual_bbox(e)
                return (b["x"], b["y"], b["width"], b["height"]) if b else None
    except Exception:  # noqa: BLE001
        return None
    return None


def _is_text_el(el):
    return el.tag.split("}")[-1] == "shape" and el.get("type") == "text"


def _widen_box(xml, idx, nw, canvas_w=960.0):
    """Widen the idx-th data child (a text shape) of xml to nw keeping its alignment anchor, inside the canvas.
    Returns (new_xml, (x, w) new) or (None, why) when the wider box would reach an element it did not touch before.
    Centre-aligned text widens symmetrically; against a neighbouring text box it is the glyphs that must not meet, not
    the boxes — a row of centred KPI numbers in edge-to-edge boxes widens into the neighbour's empty margin."""
    kids = _children(xml)
    el = kids[idx]
    old = _box_of(el)
    x, y, w, h = old
    align = next((c.get("textAlign") for c in el.iter() if c.get("textAlign")), "left")
    # the anchor never moves: left text grows rightwards only, right text leftwards only, centred text both ways equally
    # (no sliding the box back inside the canvas — that would shift the text off the column it aligns with)
    nx = x - (nw - w) / 2 if align == "center" else x - (nw - w) if align == "right" else x
    if (nx < min(x, WIDEN_EDGE_MARGIN) - 0.5 or nx + nw > max(x + w, canvas_w - WIDEN_EDGE_MARGIN) + 0.5):
        return None, f"加宽到 w={nw:g} 会让文字框离画布边不足 {WIDEN_EDGE_MARGIN:g}px（x={nx:g}），标题会离开版心"
    new = (nx, y, nw, h)
    mine = None
    for j, other in enumerate(kids):
        ob = _box_of(other)
        if j == idx or not ob or other.tag.split("}")[-1] == "line":
            continue
        if _boxes_intersect(new, ob, 1) and not _boxes_intersect(old, ob, 1):
            if align == "center" and _is_text_el(other):
                if mine is None:
                    probe = ET.fromstring(ET.tostring(el))
                    probe.set("topLeftX", f"{nx:g}")
                    probe.set("width", f"{nw:g}")
                    mine = _glyph_box(probe) or False
                theirs = _glyph_box(other)
                if mine and (theirs is None or not _boxes_intersect(mine, theirs, 1)):
                    continue   # only the empty margins of the two boxes overlap
            kind = other.tag.split("}")[-1]
            return None, f"加宽到 w={nw:g} 会压到{'图片' if kind == 'img' else '相邻元素'} {kind}（x={ob[0]:g} w={ob[2]:g}）"
    attrs = {k: el.get(k) for k in ("topLeftX", "topLeftY", "width", "height")}
    pat = re.compile(r"<shape\b(?=[^>]*\btype=\"text\")" + "".join(
        rf'(?=[^>]*\b{k}="{re.escape(v)}")' for k, v in attrs.items()) + r"[^>]*>")
    m = pat.search(xml)
    if not m:
        return None, "没找到这个文字框的原始标签"
    tag_src = re.sub(r'\bwidth="[^"]*"', f'width="{nw:g}"', m.group(0), count=1)
    tag_src = re.sub(r'\btopLeftX="[^"]*"', f'topLeftX="{nx:g}"', tag_src, count=1)
    return xml[:m.start()] + tag_src + xml[m.end():], (nx, nw)


def _grow_for_headroom(xml, over, canvas=(960.0, 540.0)):
    """held-overflow (wrap=true text that fits by the local wrap estimate but the server flags): instead of asking the
    author to cut text, give each flagged box one spare line beyond its wrapped height (what the hold asked for), kept
    where the text sits now — verticalAlign middle grows both ways, top grows down, bottom grows up — only when the
    taller box stays on the canvas and touches no element it did not touch before. A box that already has that spare
    line is left as is. Returns (new_xml, notes), or (None, why) when one box cannot grow safely (hold as before)."""
    notes = []
    cw, ch = (canvas or (960.0, 540.0))[:2]
    for d in over:
        for b in (d.get("wrapped_fit") or {}).get("boxes") or []:
            kids = _children(xml)
            by_tag = {}
            for i, el in enumerate(kids):
                by_tag.setdefault(el.tag.split("}")[-1], []).append(i)
            tag, n = _element_index(b["path"])
            if tag not in by_tag or not n or n > len(by_tag[tag]) or not b.get("lines"):
                return None, "找不到文字框"
            idx = by_tag[tag][n - 1]
            el = kids[idx]
            old = _box_of(el)
            if not old:
                return None, "文字框没有坐标"
            x, y, w, h = old
            need = b["height"] + b["height"] / b["lines"] + 4   # wrapped height + one line + padding
            if h >= need:
                continue
            grow = need - h
            va = next((c.get("verticalAlign") for c in el.iter() if c.get("verticalAlign")), "middle")
            ny = y if va == "top" else y - grow if va == "bottom" else y - grow / 2
            new = (x, round(ny, 1), w, round(need, 1))
            if new[1] < 0 or new[1] + new[3] > ch or x < 0 or x + w > cw:
                return None, f"加高到 h={need:.0f} 会出画布"
            for j, other in enumerate(kids):
                ob = _box_of(other)
                if j == idx or not ob:
                    continue
                if _boxes_intersect(new, ob, 1) and not _boxes_intersect(old, ob, 1):
                    return None, f"加高到 h={need:.0f} 会压到 {other.tag.split('}')[-1]}（y={ob[1]:g} h={ob[3]:g}）"
            attrs = {k: el.get(k) for k in ("topLeftX", "topLeftY", "width", "height")}
            pat = re.compile(r"<shape\b(?=[^>]*\btype=\"text\")" + "".join(
                rf'(?=[^>]*\b{k}="{re.escape(v)}")' for k, v in attrs.items()) + r"[^>]*>")
            m = pat.search(xml)
            if not m:
                return None, "没找到这个文字框的原始标签"
            tag_src = re.sub(r'\bheight="[^"]*"', f'height="{new[3]:g}"', m.group(0), count=1)
            tag_src = re.sub(r'\btopLeftY="[^"]*"', f'topLeftY="{new[1]:g}"', tag_src, count=1)
            xml = xml[:m.start()] + tag_src + xml[m.end():]
            text = (next((o.get("text") for o in d.get("objects") or [] if o.get("path") == b["path"]), "") or "")[:12]
            notes.append(f"「{text}」按服务端估算可能多折一行：已把文字框加高一行到 y={new[1]:g} h={new[3]:g}"
                         "（文字位置不变，未碰其他元素）；本地 XML 同步改这两个数，不用删字")
    return xml, notes


def _auto_widen(page_xml, described, canvas_w=960.0):
    """Server overflow findings on hand-written wrap=false text that is at most WIDEN_MAX wider than its box: widen the
    box to max(server, local) × WIDEN_SLACK + WIDEN_PAD (keeping its alignment anchor, inside the canvas, without
    reaching an element it did not already touch). Returns (new_xml, notes); (None, [why]) when a box could be widened
    but the wider box would hit another element (an image …) — the page is refused as before, with the reason;
    (None, []) unless every finding is such a text box."""
    kids = _children(page_xml)
    by_tag = {}
    for i, el in enumerate(kids):
        by_tag.setdefault(el.tag.split("}")[-1], []).append(i)
    xml, notes, done = page_xml, [], set()
    for d in described:
        u = d.get("unwrapped_text")
        if not u or d.get("code") not in _WIDEN_CODES:
            return None, []
        if u["path"] in done:
            continue
        tag, n = _element_index(u["path"])
        idx = by_tag[tag][n - 1]
        old = _box_of(kids[idx])
        need = float(u["single_line_width"])
        nw = round(need * WIDEN_SLACK + WIDEN_PAD)
        if not old or old[2] <= 0 or need > old[2] * WIDEN_MAX or nw > canvas_w:
            return None, []
        w = old[2]
        xml, got = _widen_box(xml, idx, nw, canvas_w)
        if xml is None:
            return None, [f"auto_widen 没有加宽：{got}，保持原样拒收——缩短文字 / 字号降一档 / 挪开该元素后重提"]
        nx, nw = got
        kids = _children(xml)
        done.add(u["path"])
        notes.append(f"{d['code']}：wrap=false 文字「{(d['objects'][0].get('text') or '')[:12] if d.get('objects') else ''}」"
                     f"单行 {need:.0f}px 比框宽 {w:.0f} 超出 ≤{WIDEN_MAX - 1:.0%}，已自动把框改为 x={nx:g} w={nw:g} 后带 lint 重提；"
                     "本地 XML 同步改这两个数即可，不用再改页")
    return (xml, notes) if done else (None, [])


def _wrap_lines(text, size, bold, width):
    """Greedy wrapped lines of one paragraph (the xml_lint estimator), as strings; [] when unavailable."""
    try:
        import sys

        scripts = str(Path(__file__).resolve().parents[2])
        if scripts not in sys.path:
            sys.path.insert(0, scripts)
        from _exhibit_xml_lint import estimate_text_width, tokenize_for_wrap
    except Exception:  # noqa: BLE001
        return []
    cjk = any(ord(c) > 0x2E80 for c in text)
    lines, cur, cur_w = [], "", 0.0
    for kind, tok in tokenize_for_wrap(text):
        tw_ = estimate_text_width(tok, size, 0, bold, None, cjk)
        if kind == "space":
            if cur:
                cur, cur_w = cur + tok, cur_w + tw_
            continue
        if cur and cur_w + tw_ > width:
            lines.append(cur)
            cur, cur_w = "", 0.0
        cur, cur_w = cur + tok, cur_w + tw_
    if cur:
        lines.append(cur)
    return lines


ORPHAN_MAX = 2   # a wrapped title whose last line holds ≤ 2 characters reads as a stray glyph


def _orphan_widen(xml, described, canvas_w=960.0):
    """wrap=true text findings downgraded as fitting (wrapped_fit): when a one-paragraph box would end on a last line of
    1–ORPHAN_MAX characters, widen it just enough to pull them up (≤ WIDEN_MAX, no new collision).
    Returns (new_xml, notes) or (xml, [])."""
    notes = []
    for d in described:
        if not d.get("auto_waived") or not d.get("wrapped_fit"):
            continue
        for b in d["wrapped_fit"]["boxes"]:
            kids = _children(xml)
            by_tag = {}
            for i, el in enumerate(kids):
                by_tag.setdefault(el.tag.split("}")[-1], []).append(i)
            tag, n = _element_index(b["path"])
            if tag not in by_tag or not n or n > len(by_tag[tag]):
                continue
            idx = by_tag[tag][n - 1]
            el = kids[idx]
            content = next((c for c in el.iter() if c.tag.split("}")[-1] == "content"), None)
            paras = [p for p in el.iter() if p.tag.split("}")[-1] == "p"]
            box = _box_of(el)
            if content is None or len(paras) != 1 or not box:
                continue
            text = "".join(paras[0].itertext()).strip()
            size = max([float(s.get("fontSize")) for s in paras[0].iter() if s.get("fontSize")]
                       or [float(content.get("fontSize") or 16)])
            bold = any(s.get("bold") == "true" for s in [content, *paras[0].iter()])
            lines = _wrap_lines(text, size, bold, box[2])
            last = re.sub(r"\s", "", lines[-1]) if lines else ""
            if len(lines) < 2 or not 1 <= len(last) <= ORPHAN_MAX:
                continue
            want = next((w for w in range(int(box[2]) + 4, int(box[2] * WIDEN_MAX) + 1, 4)
                         if len(_wrap_lines(text, size, bold, w)) < len(lines)), None)
            if not want or want > canvas_w:
                continue
            new, got = _widen_box(xml, idx, float(want), canvas_w)
            if new is None:
                notes.append(f"「{text[:12]}」末行只剩「{last}」：{got}，没有自动加宽——删一两个字或调宽后重提")
                continue
            xml = new
            notes.append(f"「{text[:12]}」换行后末行只剩「{last}」（孤字），已把框加宽到 x={got[0]:g} w={got[1]:g}；"
                         "本地 XML 同步改这两个数")
    return xml, notes


def _seg_hits_box(seg, width, box):
    """True when a line's stroke (not its bounding box) touches the text box (x, y, w, h)."""
    x1, y1, x2, y2 = seg
    tx, ty, tw, th = box
    pad = width / 2
    steps = max(2, int(max(abs(x2 - x1), abs(y2 - y1)) / 2))
    return any(tx - pad <= x1 + (x2 - x1) * i / steps <= tx + tw + pad and ty - pad <= y1 + (y2 - y1) * i / steps <= ty + th + pad
               for i in range(steps + 1))


def _over_text(kids, objs, origins=None):
    """Lines/filled shapes whose bounding box covers a reported text box (server contrast uses what lies under the text)."""
    texts = [o["xml_box"] for o in objs if o.get("xml_box") and o.get("element", "").endswith('"text"]')]
    if not texts:
        return []
    found = []
    for idx, el in enumerate(kids):
        tag = el.tag.split("}")[-1]
        try:
            if tag == "line":
                x1, y1, x2, y2 = (float(el.get(k, 0)) for k in ("startX", "startY", "endX", "endY"))
                bx = (min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
                desc = {"element": "line", "xml_line": [round(v, 1) for v in (x1, y1, x2, y2)]}
                sw = max(1.0, float(next((c.get("width") for c in el if c.tag.split("}")[-1] == "border"), 1) or 1))
                if _light_rule(el) or not any(_seg_hits_box((x1, y1, x2, y2), sw, t) for t in texts):
                    continue   # a light gridline under a label stays readable; a diagonal's box is not its stroke
            elif tag == "shape" and el.get("type") not in ("text", None):
                bx = tuple(float(el.get(k)) for k in ("topLeftX", "topLeftY", "width", "height"))
                desc = {"element": f'shape[type="{el.get("type")}"]', "xml_box": [round(v, 1) for v in bx]}
            else:
                continue
        except (TypeError, ValueError):
            continue
        for tx, ty, tw, th in texts:
            if bx[0] < tx + tw and tx < bx[0] + max(bx[2], 1) and bx[1] < ty + th and ty < bx[1] + max(bx[3], 1):
                if (
                    tag == "shape"
                    and bx[0] <= tx
                    and bx[1] <= ty
                    and bx[0] + bx[2] >= tx + tw
                    and bx[1] + bx[3] >= ty + th
                ):
                    continue  # a background the text sits fully inside is the intended backdrop, not a crossing
                desc["source"] = (origins or {}).get(idx, "page_xml")
                found.append(desc)
                break
    return found


def _summarize(items):
    """One line per (code, source) group so the author sees what to change first."""
    groups = {}
    for it in items:
        srcs = sorted({o.get("source", "?") for o in it.get("objects", [])})
        key = (it.get("code"), "+".join(srcs))
        groups.setdefault(key, []).append(it)
    lines = []
    for (code, src), its in groups.items():
        sample = "、".join(
            dict.fromkeys(
                (o.get("text") or o.get("path", "")) + (f" @{o['xml_box']}" if o.get("xml_box") else "")
                for it in its[:3]
                for o in it["objects"]
            )
        )
        lines.append(f"{code} ×{len(its)}（来源 {src}；如 {sample}）→ {its[0].get('fix') or its[0].get('hint') or ''}")
    return lines


def _fragment_box(kids, origins, name):
    xs, ys, x2, y2 = [], [], [], []
    for i, src in origins.items():
        if src != name:
            continue
        el = kids[i]
        try:
            x, y, w, h = (float(el.get(k)) for k in ("topLeftX", "topLeftY", "width", "height"))
        except (TypeError, ValueError):
            continue
        xs.append(x)
        ys.append(y)
        x2.append(x + w)
        y2.append(y + h)
    if not xs:
        return None
    return {
        "box": [round(min(xs), 1), round(min(ys), 1), round(max(x2) - min(xs), 1), round(max(y2) - min(ys), 1)],
        "elements": sum(1 for v in origins.values() if v == name),
    }


def _suggest(item):
    """Concrete next step in page coordinates, so the author can edit one number."""
    code, objs, m = item.get("code"), item.get("objects", []), item.get("measurement") or {}
    srcs = {o.get("source") for o in objs}
    gen = any(str(x).startswith("fragment") or x == "generated" for x in srcs)
    if code == "bbox_overlap" and len(objs) == 2:
        a, b = objs
        h, w = m.get("intersection_height"), m.get("intersection_width")
        texts = [o for o in objs if o.get("element", "").endswith('"text"]')]
        frag_text = next((o for o in texts if str(o.get("source", "")).startswith("fragment")), None)
        page_text = next((o for o in texts if o.get("source") == "page_xml"), None)
        if frag_text and page_text:
            fb = next(iter((item.get("fragments") or {}).values()), None) or {}
            box = f"（图表框现为 {fb['box']}）" if fb.get("box") else ""
            return (
                f"图表片段里的文字「{frag_text.get('text', '')}」压到页面标题/正文「{page_text.get('text', '')}」："
                f"不是误报，不要 waive——缩小/下移图表框{box}，或去掉该文字（如单独一行的单位改写进轴标题）。"
            )
        if gen and all(o.get("element", "").endswith('"text"]') for o in objs):
            return (
                "两段图内文字互压（不是误报，不要 waive）：图被缩得太小，标签字号被抬到下限后挤在一起。把该图的框（chart_slide 的 "
                "width/height 或 to_slide 的 width）加大，或减少类别注释/中心文字/图例行数；不要逐个挪生成的文字。"
            )
        if gen and texts:
            hand = "移动页面上手写的那个元素，或" if "page_xml" in srcs else ""
            return (
                f"{_kind_of(a)} 与 {_kind_of(b)} 相压，文字被线/形状盖住（不是误报，不要 waive）：{hand}"
                "让标签离开深色线和填充形状（换位置、删掉这条标注或数值标签），或把图的框整体挪开/放大。"
            )
        if gen:
            hand = "移动页面上手写的那个元素，或" if "page_xml" in srcs else ""
            return (
                f"{_kind_of(a)} 与 {_kind_of(b)} 相压：{hand}把图的框整体挪开/缩小；"
                "片段内部坐标没有被缩放，不要去改图表/示意图的标签。"
            )
        if h is not None and w is not None:
            mv = "下移" if (b.get("lint_box", [0, 0])[1] >= a.get("lint_box", [0, 0])[1]) else "上移"
            return (
                f"两者重叠 {w}×{h}px：把“{b.get('text', b['path'])}”{mv}至少 {h + 2:.0f}px，"
                f"或把较小的框缩窄 {w + 2:.0f}px。"
            )
    if code == "text_overflows_container":
        ov = item.get("overflow") or {}
        sides = ", ".join(f"{k} {v}px" for k, v in ov.items() if v)
        text = next((o for o in objs if o.get("element", "").endswith('"text"]')), None)
        box = next((o for o in objs if o is not text and o.get("xml_box")), None)
        if text and box and text.get("xml_box"):
            tx, ty, tw, th = text["xml_box"]
            bx, by, bw, bh = box["xml_box"]
            # the smallest container that holds the text box, padded 6px
            nx, ny = min(bx, tx - 6), min(by, ty - 6)
            nw, nh = max(bx + bw, tx + tw + 6) - nx, max(by + bh, ty + th + 6) - ny
            return (
                f"文字框 {text['xml_box']} 超出底框 {box['xml_box']}（{sides}，不是误报，不要 waive）：把底框改成 "
                f"[{nx:.0f}, {ny:.0f}, {nw:.0f}, {nh:.0f}]，或把文字框缩进底框内、删短文字。"
            )
        return f"文字超出其底框（{sides}，不是误报，不要 waive）：加大底框或缩短文字，让文字框完全落在底框内。"
    if code in ("text_may_overflow_shape",):
        return ("文字放不下：publish 已自动加高过，仍报说明加高会压到下方元素（warning 里 'text box … not grown' 写了压到谁、"
                "要下移几 px）——标题折行就缩成一行或加宽，数字 / 正文就加宽框或删字，或把下方元素按报文下移；不要只靠 waive。")
    if code and "out_of" in code:
        return "超出页面 960×540：把该元素移回页面内或缩小。"
    if code == "text_color_contrast":
        return "文字与背景对比不足：加深文字色或改浅/改深底色。"
    if code and "sparse" in code:
        return "页面可见内容过少：检查片段是否真的放进了页面（x/y/width 是否正确），或把图/文字放大到占满规划区域。"
    return ""


def _saved_path(data, cwd, out_dir, name):
    """The file the CLI really wrote: it may fix the extension (.png → .jpg) or rename to avoid a clash."""
    shots = data.get("screenshots") or []
    candidates = [data.get("output")] + [s.get("path") for s in shots if isinstance(s, dict)]
    for c in candidates:
        if c and os.path.exists(c if os.path.isabs(c) else os.path.join(cwd, c)):
            return c if os.path.isabs(c) else os.path.abspath(os.path.join(cwd, c))
    found = sorted(Path(cwd, out_dir).glob(f"{name}*"), key=lambda q: q.stat().st_mtime)
    if found:
        return str(found[-1].resolve())
    return next((c for c in candidates if c), "")


def _screenshot(args, cwd, out_dir, name, tries=4):
    for attempt in range(tries):
        res = _run(
            ["slides", "+screenshot", "--as", "user", *args, "--output-dir", out_dir, "--output-name", name]
            if "--content" in args
            else ["slides", "+screenshot", "--as", "user", *args, "--output", f"{out_dir}/{name}"],
            cwd,
        )
        if res.get("ok"):
            return _saved_path(res.get("data") or {}, cwd, out_dir, name)
        msg = json.dumps(res.get("error") or {}, ensure_ascii=False)
        if "rate_limit" in msg or "frequency" in msg or "99991400" in msg:
            time.sleep(2 + attempt * 3)
            continue
        time.sleep(1)
    return ""


def _native_fixes(xml):
    """Mechanical schema fixes on native SML (outside embedded <svg>): integer border widths, rgb() colours."""

    def hex_rgb(m):
        h = m.group(2)
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        return f'{m.group(1)}"rgb({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)})"'

    def fix(chunk):
        chunk = re.sub(
            r'(<border\b[^>]*?\bwidth=")(\d+\.\d+)(")',
            lambda m: f"{m.group(1)}{max(1, round(float(m.group(2))))}{m.group(3)}",
            chunk,
        )
        chunk = re.sub(r'(\b(?:color|backgroundColor)=)"#([0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})"', hex_rgb, chunk)

        def lift(m):
            content, body = m.group(1), m.group(2)
            moved = {}
            for attr in ("wrap", "autoFit"):
                for v in re.findall(rf'<p\b[^>]*\b{attr}="([^"]*)"', body):
                    moved.setdefault(attr, v)
                body = re.sub(rf'(<p\b[^>]*?)\s{attr}="[^"]*"', r"\1", body)
            for attr, v in moved.items():
                if f' {attr}="' not in content:
                    content = content[:-1] + f' {attr}="{v}">'
            return content + body

        return re.sub(r"(<content\b[^>]*>)(.*?)(?=</content>)", lift, chunk, flags=re.S)

    parts = re.split(r"(<svg\b.*?</svg>)", xml, flags=re.S)
    return "".join(p if p.startswith("<svg") else fix(p) for p in parts)


_ZERO_SHAPE = re.compile(r'<shape\b(?=[^>]*\b(?:width|height)="0(?:\.0+)?")[^>]*?(?:/>|>.*?</shape>)', re.S)


def _drop_degenerate(xml):
    """Generated zero-width/height shapes (a collapsed marker or empty label) are invisible but rejected by the"""
    count = len(_ZERO_SHAPE.findall(xml))
    return (_ZERO_SHAPE.sub("", xml), count) if count else (xml, 0)


def _with_sml_namespace(page_xml):
    """A hand-written page ``<slide>`` without xmlns is accepted on its own by publish_slide; accept it with fragments too."""
    if isinstance(page_xml, str):
        head = re.match(r"\s*(?:<\?xml[^>]*\?>\s*)?<slide\b([^>]*)>", page_xml)
        if head and "xmlns=" not in head.group(1):
            at = head.end(1)
            page_xml = page_xml[:at] + f' xmlns="{_SML}"' + page_xml[at:]
    return page_xml


_BARE_AMP = re.compile(r"&(?!(?:[A-Za-z][A-Za-z0-9]*|#[0-9]+|#x[0-9A-Fa-f]+);)")
_NAMED_ENTITY = re.compile(r"&([A-Za-z][A-Za-z0-9]*);")
_XML_ENTITIES = {"amp", "lt", "gt", "quot", "apos"}


def _html_entities(xml):
    """HTML named entities (&nbsp; &mdash; &rarr; …) are not XML: the parser stops with "undefined entity". Write them as
    numeric character references; an unknown name becomes a literal "&amp;name;"."""
    from html.entities import name2codepoint

    def sub(m):
        name = m.group(1)
        if name in _XML_ENTITIES:
            return m.group(0)
        cp = name2codepoint.get(name)
        return f"&#{cp};" if cp else f"&amp;{name};"

    return _NAMED_ENTITY.sub(sub, xml) if isinstance(xml, str) and "&" in xml else xml


def _prepare(page_xml, pin_top=False):
    """Fix the mechanical rejections of hand-written page XML before the first write."""
    import sys

    scripts = str(Path(__file__).resolve().parents[2])
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    from _exhibit_text_fit import fit_text_boxes

    page_xml = _with_sml_namespace(
        _BARE_AMP.sub("&amp;", _html_entities(page_xml))
    )  # "Smith & Jones" in a source line is the classic parse error; &nbsp; from HTML habits the next one
    page_xml, typos = _sxsd_typos(page_xml)
    out, warns = fit_text_boxes(_native_fixes(page_xml), pin_top=pin_top)
    return out, list(typos) + list(warns)


_TEXT_TAGS = r"(?:content|p|span)"
_LS_ATTRS = r"(?:lineSpacing|beforeLineSpacing|afterLineSpacing)"


def _sxsd_typos(xml):
    """Common hand-written SXSD slips fixed before submit (each reported once as a warning): align= on <content> / <p>
    / <span> → textAlign=, bare numeric lineSpacing (LineSpacingType is "multiple:N" or "fixed:Npx") → multiple:N for
    a factor ≤ 4, fixed:N for a pixel value. Embedded <svg> is left alone."""
    fixed = {}

    def fix(chunk):
        def align(m):
            if re.search(r"\btextAlign=", m.group(0)):
                return re.sub(r'\salign="[^"]*"', "", m.group(0), count=1)
            fixed["align"] = fixed.get("align", 0) + 1
            return re.sub(r'\balign="', 'textAlign="', m.group(0), count=1)

        chunk = re.sub(rf'<{_TEXT_TAGS}\b[^>]*\salign="[^"]*"[^>]*>', align, chunk)

        def spacing(m):
            v = float(m.group(2))
            new = f"multiple:{m.group(2)}" if v <= 4 else f"fixed:{m.group(2)}"
            fixed.setdefault("lineSpacing", []).append(f'{m.group(2)}→{new}')
            return f'{m.group(1)}="{new}"'

        return re.sub(rf'\b({_LS_ATTRS})="(\d+(?:\.\d+)?)"', spacing, chunk)

    parts = re.split(r"(<svg\b.*?</svg>)", xml, flags=re.S)
    xml = "".join(p if p.startswith("<svg") else fix(p) for p in parts)
    notes = []
    if fixed.get("align"):
        notes.append(f'sxsd_typo：{fixed["align"]} 处文字用了 align=，已改为 textAlign=（align 只属于图片/填充）；本地 XML 同步改')
    if fixed.get("lineSpacing"):
        notes.append(f'sxsd_typo：lineSpacing 写了裸数字（{"、".join(dict.fromkeys(fixed["lineSpacing"]))}），'
                     '已改成 multiple:N（倍数）/ fixed:N（像素）；本地 XML 同步改')
    return xml, notes


_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_CTRL_ENTITY = re.compile(r"&#(?:x([0-9A-Fa-f]+)|([0-9]+));")
_LATEX_HINT = {"\t": "\\t（\\text / \\times / \\tau / \\theta）", "\x08": "\\b（\\beta / \\bar）", "\x07": "\\a（\\alpha）",
               "\x0c": "\\f（\\frac）", "\x0b": "\\v（\\vec / \\varepsilon）", "\r": "\\r（\\rho / \\right）"}
CONTROL_CHAR_FIX = ('文本里混进了控制字符：普通 Python 字符串里的 "\\text"、"\\times"、"\\frac"、"\\beta" 会被转义成 TAB/退格/换页'
                    '（显示成 "extm/s²"、"4imes8"）。含反斜杠的文字用原始字符串 r"..." 或写成双反斜杠 "\\\\times"，'
                    '公式符号最好直接写 Unicode（×、÷、√、α、β、→）；改完用同一调用重提')


def _ctrl_ok(code):
    return code in (9, 10, 13) or code >= 32


def control_chars(*xmls):
    r"""Control characters in the page XML that no author means: \x00-\x08, \x0b, \x0c, \x0e-\x1f anywhere (raw or as
    &#N; entities), and TAB / CR-before-a-letter inside text content (indentation between tags is fine). These come from
    LaTeX written into a normal Python string ("\text" -> TAB + "ext"). Returns [(char, snippet)]."""
    out = []
    for x in xmls:
        if not isinstance(x, str):
            continue
        for m in _CTRL.finditer(x):
            out.append((m.group(0), x[max(0, m.start() - 12):m.end() + 12]))
        for m in _CTRL_ENTITY.finditer(x):
            code = int(m.group(1), 16) if m.group(1) else int(m.group(2))
            if not _ctrl_ok(code) or (code in (9, 13) and _in_text(x, m.start())):
                out.append((chr(code) if code < 0x110000 else "?", x[max(0, m.start() - 12):m.end() + 12]))
        for seg in re.finditer(r">([^<]+)<", x):
            t = seg.group(1)
            if not t.strip():
                continue   # whitespace / indentation between tags
            for m in re.finditer(r"\t|\r(?=[A-Za-z])", t):
                out.append((m.group(0), t[max(0, m.start() - 12):m.end() + 12]))
    return out


def _in_text(x, pos):
    """True when position ``pos`` of ``x`` lies in text content (after a '>' and before the next '<'), not in a tag."""
    return x.rfind(">", 0, pos) > x.rfind("<", 0, pos)


def _control_char_error(found):
    kinds = list(dict.fromkeys(c for c, _ in found))
    named = "、".join(_LATEX_HINT.get(c, repr(c)) for c in kinds)
    snips = "；".join(repr(sn) for _, sn in found[:3])
    return {"key": "control_chars", "code": "control_chars",
            "message": f"页面文字含 {len(found)} 个控制字符 {named}：{snips}", "fix": CONTROL_CHAR_FIX}


def _page_registry(cwd, presentation):
    path = Path(cwd) / ".lark-slides" / f"pages-{presentation}.json"
    try:
        return path, json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return path, {}


_EMPTY_FIELD = re.compile(r"<field\b([^>]*?)(?:/>|>\s*</field>)", re.S)
EMPTY_FIELD_FIX = ('<field type="slidenum"> 没有降级文字（空元素服务端报 4001000）：写成 <field type="slidenum">N</field>'
                   "（N = 本页页码），或传 page=N 让 publish 自动填")


def _fill_empty_fields(xml, page=None, slide_id=None, cwd=None, deck=None):
    """(xml, None) with every empty <field> given its fallback text — slidenum: this page's number (page=, else the
    registry entry of slide_id), datetime*: today's date — or (xml, error) when a page number is needed but unknown.
    An empty <field/> is rejected by the server with 4001000."""
    if "<field" not in xml:
        return xml, None
    n = _page_no(page)
    if n is None and slide_id and deck:
        _, reg = _page_registry(cwd or ".", deck)
        n = next((_page_no(k) for k, v in reg.items() if v == slide_id and _page_no(k) is not None), None)
    missing = []

    def fill(m):
        kind = (re.search(r"""\btype\s*=\s*["']([^"']*)""", m.group(1)) or [None, ""])[1]
        if kind.startswith("datetime"):
            text = time.strftime("%Y-%m-%d")
        elif n is not None:
            text = str(n)
        else:
            missing.append(kind or "?")
            return m.group(0)
        return f"<field{m.group(1).rstrip()}>{text}</field>"

    out = _EMPTY_FIELD.sub(fill, xml)
    if missing:
        return out, {"key": "empty_field", "code": "empty_field",
                     "message": f"{len(missing)} 个 <field type=\"{missing[0]}\"> 是空元素，页码未知无法自动填",
                     "fix": EMPTY_FIELD_FIX}
    return out, None


_NESTED_FRAGMENT = re.compile(r"(?:<slide\b[^>]*>\s*)?<data\b[^>]*>(.*?)</data>(?:\s*</slide>)?", re.S)
_PASTED_HINT = "把 to_slide()/chart_slide() 的返回值作为 publish_slide 的第 2 个参数传入，不要拼进 page_xml"


def _lift_pasted_fragments(page_xml):
    """A to_slide()/chart_slide() result pasted into page_xml's <data> is a whole ``<slide><data>…</data></slide>``"""
    if not isinstance(page_xml, str):
        return page_xml, []
    head = re.search(r"<data\b[^>]*>", page_xml)
    if not head:
        return page_xml, []
    out, found, pos = page_xml[: head.end()], [], head.end()
    for m in _NESTED_FRAGMENT.finditer(page_xml, head.end()):
        out += page_xml[pos : m.start()]
        found.append(f'<slide xmlns="{_SML}"><data>{m.group(1)}</data></slide>')
        pos = m.end()
    if not found:
        return page_xml, []
    out += page_xml[pos:]
    try:
        _children(_with_sml_namespace(out))
        for frag in found:
            _children(frag)
    except ET.ParseError:
        return page_xml, []  # not a clean paste between page elements: leave it to the normal error path
    return out, found


_DIAGRAM_SHAPES = {"rect", "round-rect", "ellipse", "custom", "diamond", "triangle", "slides-full-round-rect"}


_WAIVE_HINT = (
    "这些问题若看过 preview/截图确认是误报（或同一条已改过一次仍报），不要再反复挪坐标：同一调用加 "
    "waive=[{keys}]（只填确认误报的那几条）强行写入，函数会自动截图，Read 截图核对即可。"
)


def _hand_diagram(kids):
    """Native page_xml that pieces a diagram together: many plain shapes plus several arrow-ended lines."""
    shapes = sum(1 for el in kids if el.tag.split("}")[-1] == "shape" and el.get("type") in _DIAGRAM_SHAPES)
    arrows = 0
    for el in kids:
        if el.tag.split("}")[-1] not in ("line", "polyline", "connector"):
            continue
        heads = [c for c in el if isinstance(c.tag, str) and c.tag.split("}")[-1] in ("startArrow", "endArrow")]
        arrows += any((c.get("type") or "none") != "none" for c in heads)
    return shapes >= 8 and arrows >= 4


_HAND_DIAGRAM_NOTE = (
    "本页用原生形状手拼了示意图：机制/结构图请用 drawing 库（部件 + d.arrow）画后 to_slide，连线与对象才能对齐、可审查"
)


def _sync_candidates(cwd):
    """Every multi-agent SYNC dir under cwd: <cwd>/.lark-slides/<strategy|review>/<task>/sync (and older layouts), plus a
    SYNC/ or sync/ folder directly under cwd. Archived turns (SYNC/turns/<n>/) are not SYNC dirs."""
    root = Path(cwd or ".")
    out = []
    for kind in ("strategy", "review"):
        out += list(root.glob(f".lark-slides/{kind}/*/sync")) + list(root.glob(f".lark-slides/{kind}/sync"))
        out += [p.parent for p in root.glob(f".lark-slides/{kind}/**/status.json")
                if "turns" not in p.relative_to(root).parts]
    out += [root / n for n in ("SYNC", "sync") if (root / n / "claims.json").exists() or (root / n / "status.json").exists()]
    return list(dict.fromkeys(out))


def sync_deck(d):
    """The deck a SYNC dir belongs to (first token of SYNC/deck.txt), or None before Main created it."""
    try:
        return (Path(d, "deck.txt").read_text(encoding="utf-8").split() or [None])[0]
    except OSError:
        return None


LIVE_WINDOW = 5400   # s: a SYNC dir untouched this long (and not delivered) is a dead task, not the one being written


def sync_finished(d):
    """A SYNC dir of a task that is over: delivered (exported / finished_at) and not reopened for an edit turn, or
    abandoned (a newer task was dispatched in the same CWD)."""
    st = _status(d)
    if st.get("abandoned"):
        return True
    return ((Path(d) / "exported").exists() or bool(st.get("finished_at"))) and st.get("phase") != "edit"


def sync_active_at(d):
    """Last time any agent touched the SYNC dir (newest mtime of the dir and its top-level files)."""
    d = Path(d)
    ts = []
    for f in [d, *d.iterdir()] if d.is_dir() else []:
        try:
            ts.append(f.stat().st_mtime)
        except OSError:
            pass
    return max(ts) if ts else 0.0


def sync_live(d):
    """The SYNC dir of a task still in progress: not finished and touched within LIVE_WINDOW (a reopened edit turn is in
    progress whatever its age)."""
    if sync_finished(d):
        return False
    return _status(d).get("phase") == "edit" or time.time() - sync_active_at(d) < LIVE_WINDOW


def _owner_deck(d, cwd):
    """The deck a SYNC dir belongs to: deck.txt, else the single page registry (pages-<deck>.json) in the task CWD
    written since the SYNC dir was set up, else None (not decided yet)."""
    tok = sync_deck(d)
    if tok:
        return tok
    try:
        born = min(f.stat().st_mtime for f in [Path(d), *Path(d).iterdir()]) - 5
    except (OSError, ValueError):
        return None
    regs = [f for f in (Path(cwd or ".") / ".lark-slides").glob("pages-*.json") if f.stat().st_mtime >= born]
    return regs[0].name[6:-5] if len(regs) == 1 else None


def _task_sync_dirs(cwd, deck=None, deckless=True):
    """SYNC dirs of the task being written. With deck: dirs whose deck.txt names that deck (delivered ones too — their
    freeze protects that deck; finish / export / organizer_done stamp deck.txt), plus (deckless=True) live dirs that have
    no deck yet. Without deck: live dirs only. A SYNC dir of another deck, or of a finished / abandoned / long-idle task
    in the same CWD, never counts — its freeze, claims, plan and sample flag belong to that task."""
    out = []
    for d in _sync_candidates(cwd):
        owner = _owner_deck(d, cwd)
        if deck:
            if owner == str(deck) or (deckless and owner is None and sync_live(d)):
                out.append(d)
        elif sync_live(d):
            out.append(d)
    return out


def _task_deck(cwd):
    """The one deck of the running multi-agent task in cwd (first token of SYNC/deck.txt), or None."""
    if not cwd:
        return None
    for d in _task_sync_dirs(cwd):
        tok = sync_deck(d)
        if tok:
            return tok
    return None


def _binding_task(cwd, deck):
    candidates = [(directory, _status(directory)) for directory in _sync_candidates(cwd)]
    candidates = [(directory, status) for directory, status in candidates
                  if status.get("task_id") and status.get("task_flow") in ("strategy",)
                  and not status.get("abandoned") and not sync_finished(directory)]
    try:
        dispatch = json.loads((Path(cwd) / ".lark-slides" / "dispatch.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        dispatch = {}
    if not isinstance(dispatch, dict):
        dispatch = {}
    current = [candidate for candidate in candidates if str(candidate[0].resolve()) == dispatch.get("sync")]
    matching = [candidate for candidate in candidates if sync_deck(candidate[0]) == deck]
    selected = current or matching or candidates
    return selected[0] if len(selected) == 1 else (None, {"ambiguous_binding": bool(selected)})


def _presentation_snapshot(response, deck):
    data = response.get("data") if isinstance(response, dict) and response.get("ok") is True else None
    if not isinstance(data, dict) or data.get("scope") not in (None, "presentation"):
        return None
    document = data.get("xml_presentation")
    content = document.get("content") if isinstance(document, dict) else None
    if not isinstance(content, str):
        content = next((data[key] for key in ("xml", "content", "xml_content")
                        if isinstance(data.get(key), str)), None)
    try:
        root = ET.fromstring(content)
    except (ET.ParseError, TypeError):
        return None
    identity = data.get("xml_presentation_id")
    if root.tag not in ("presentation", f"{{{_SML}}}presentation") or (root.get("id") or identity) != deck:
        return None
    if identity is not None and identity != deck:
        return None
    slide_nodes = [element for element in root.iter() if element.tag.split("}")[-1] == "slide"]
    if any(element not in list(root) or element.tag not in ("slide", f"{{{_SML}}}slide")
           for element in slide_nodes):
        return None
    slides = [child.get("id") for child in slide_nodes]
    if any(not slide for slide in slides) or len(slides) != len(set(slides)):
        return None
    return {"ordered_slide_ids": slides, "revision_id": data.get("revision_id"), "xml": content}


def _check_task_deck(cwd, deck, response, registry, initialize=False, repair=False, directory=None,
                     owned_slide_ids=()):
    if directory is None:
        directory, status = _binding_task(cwd, deck)
    else:
        directory, status = Path(directory), _status(directory)
        if not status.get("task_id") or status.get("task_flow") not in ("strategy",):
            return {"ok": True, "managed": False}
    if directory is None and not status.get("ambiguous_binding"):
        return {"ok": True, "managed": False}
    result = {"ok": False, "managed": True, "code": "deck_binding_unverified",
              "next": "目标稿未获当前任务授权：用已有 +create 返回的空白 deck，或显式 edit / 同任务 resume；不清空、不另建逃避"}
    if directory is None or sync_deck(directory) not in (None, deck):
        return result
    snapshot = _presentation_snapshot(response, deck)
    if snapshot is None:
        return {**result, "code": "deck_readback_invalid", "next": "完整回读失败或目标身份不符：不得写入或导出，恢复本次 +xml-get 后再重试"}
    result.update(ordered_slide_ids=snapshot["ordered_slide_ids"], revision_id=snapshot["revision_id"])
    binding = status.get("deck_binding")
    if binding is not None and (not isinstance(binding, dict) or binding.get("task_id") != status["task_id"]
            or binding.get("deck") != deck or binding.get("mode") not in ("fresh", "edit")
            or (binding.get("mode") == "fresh" and (binding.get("authority") != "empty_presentation_readback"
                or binding.get("baseline_slide_ids") != []))
            or (binding.get("mode") == "edit" and binding.get("authority") not in ("dispatch:edit", "reopen"))):
        return result
    if not isinstance(registry, dict) or any(not isinstance(value, str) or not value for key, value in registry.items()
                                            if re.fullmatch(r"p\d+", key)):
        return {**result, "code": "deck_registry_invalid"}
    pages = {key: value for key, value in registry.items() if re.fullmatch(r"p\d+", key)}
    if binding is None:
        if snapshot["ordered_slide_ids"] or pages:
            return {**result, "unexpected_slide_ids": snapshot["ordered_slide_ids"]}
        binding = {"task_id": status["task_id"], "deck": deck, "mode": "fresh",
                   "authority": "empty_presentation_readback", "creation_receipt_verified": False,
                   "baseline_slide_ids": [], "revision_id": snapshot["revision_id"]}
    baseline = binding.get("baseline_slide_ids")
    if baseline is None and binding["mode"] == "edit":
        binding = {**binding, "baseline_slide_ids": snapshot["ordered_slide_ids"],
                   "revision_id": snapshot["revision_id"]}
        baseline = binding["baseline_slide_ids"]
    if (not isinstance(baseline, list) or any(not isinstance(slide, str) or not slide for slide in baseline)
            or len(baseline) != len(set(baseline))):
        return result
    positions = {slide: position for position, slide in enumerate(snapshot["ordered_slide_ids"], 1)}
    ordered_pages = sorted(pages, key=lambda key: int(key[1:]))
    missing = [int(key[1:]) for key in ordered_pages if pages[key] not in positions]
    duplicates = {slide: [int(key[1:]) for key in ordered_pages if pages[key] == slide]
                  for slide in set(pages.values()) if list(pages.values()).count(slide) > 1}
    expected = [pages[key] for key in ordered_pages if pages[key] in positions]
    actual = [slide for slide in snapshot["ordered_slide_ids"] if slide in pages.values()]
    permitted = set(pages.values()) | set(baseline) | (set(owned_slide_ids) if repair else set())
    unexpected = [slide for slide in snapshot["ordered_slide_ids"] if slide not in permitted]
    result.update(missing=missing, duplicates=duplicates, unexpected_slide_ids=unexpected,
                  logical_to_actual={key: positions[slide] for key, slide in pages.items() if slide in positions})
    if unexpected or (not repair and (missing or duplicates or expected != actual)):
        order_only = not unexpected and not duplicates and not missing
        return {**result, "code": "deck_identity_mismatch", "next": (
            "页都已登记，只是在线顺序与页码不一致：在 ppt 技能目录运行一次 python3 -m scripts.svg_lib.atomize_svg_to_slide._publish "
            f"verify {deck} --repair --cwd {cwd} 按页码重排，再原样重跑刚才的 publish" if order_only else
            "在线页身份 / 顺序与本任务登记不一致：只报告并沿现有 order / reopen 修复，不删除陌生页；"
            "不要手改 pages-*.json（本页上次写入残留的 slide 由 publish 自动登记，原样重跑同一条 publish 即可）")}
    if initialize and status.get("deck_binding") != binding:
        latest = _status(directory)
        latest["deck_binding"] = binding
        _save_registry(directory / "status.json", latest)
    return {key: value for key, value in {**result, "ok": True}.items() if key not in ("code", "next")}


_FIX_HINT = ("要改页：本轮交付前的修复只能由 Main/Lead 运行 multiagent_sync.py finish --fix N --why …（每个任务一次）；"
             "交付后用户追问的新一轮修改先运行 multiagent_sync.py reopen --cwd <CWD> --deck <deck> --why …")
_EXPORTED_MSG = f"PPTX 已导出交付：{_FIX_HINT}；不要手改 status.json / claims.json / exported"
DELIVERED_MSG = ("这是已交付的 deck：若是用户追问的新一轮修改，先运行 multiagent_sync.py reopen --cwd {cwd} --deck {deck} --why "
                 "\"<用户追问摘要>\"；若是本轮交付前的修复，用 finish --fix N --why …（每个任务一次）。"
                 "不要手改 status.json / claims.json / exported / frozen.lock")


def _exported(cwd, deck=None, deckless=True):
    """The SYNC dir of this deck whose `exported` marker (written by multiagent_sync finish / export) says the deck was
    delivered, or None."""
    return next((d for d in _task_sync_dirs(cwd, deck, deckless) if (d / "exported").exists()), None)


def _status(d):
    try:
        st = json.loads((Path(d) / "status.json").read_text(encoding="utf-8"))
        return st if isinstance(st, dict) else {}
    except (OSError, ValueError):
        return {}


def delivered(cwd, deck=None):
    """True when a SYNC dir of this deck shows it was already delivered (exported marker or finished_at)."""
    return any((d / "exported").exists() or _status(d).get("finished_at") for d in _task_sync_dirs(cwd, deck))


def edit_phase(cwd, deck=None):
    """True in a follow-up edit turn opened by multiagent_sync.py reopen (status phase "edit", not yet re-exported):
    publish then skips the multi-agent ownership rules (claims, P1–P3 Main-only) but keeps every quality check."""
    dirs = _task_sync_dirs(cwd, deck)
    return bool(dirs) and any(_status(d).get("phase") == "edit" for d in dirs) and not delivered(cwd, deck)


def refusal_hint(cwd, base, deck=None):
    """The fix text for an exported / frozen refusal: DELIVERED_MSG (reopen for a follow-up turn, finish --fix for a
    pre-delivery repair) when the deck was already delivered, else `base`."""
    if delivered(cwd, deck):
        return DELIVERED_MSG.format(cwd=Path(cwd or ".").resolve(), deck=deck or "<deck>")
    return base


FROZEN_MSG = f"页面已冻结：{_FIX_HINT}；不要改 status.json / frozen.lock"
SEAL_MSG = ("冻结/导出标记或服务端拦截计数（blocked-*.json）被手工删改：要改页只能用 finish --fix N --why …（每个任务一次），"
            "交付后的新一轮追问用 multiagent_sync.py reopen --cwd <CWD> --deck <deck> --why …；"
            "被拦 4 次的页按提示换 row_table 版本，不要清零计数")
SEAL_BLOCKED = "__blocked__"   # .seal key: {blocked-<deck>.json: sha256} of the server-block counters


def _sha(path):
    import hashlib
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return None


class _SealLock:
    """flock on <cwd>/.lark-slides/.seal.lock: counter writes + seal update are one step for readers (no torn state)."""

    def __init__(self, cwd, shared=False):
        self.path, self.shared, self.f = Path(cwd or ".") / ".lark-slides" / ".seal.lock", shared, None

    def __enter__(self):
        import fcntl
        try:
            if self.shared and not self.path.exists():
                return self
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.f = open(self.path, "a")
            fcntl.flock(self.f, fcntl.LOCK_SH if self.shared else fcntl.LOCK_EX)
        except OSError:
            self.f = None
        return self

    def __exit__(self, *exc):
        if self.f:
            self.f.close()
        return False


def reseal_blocked(cwd):
    """Record the sha256 of every <cwd>/.lark-slides/blocked-*.json in .seal (call under _SealLock after writing a
    counter). Only for multi-agent tasks (a SYNC dir exists) or when a .seal already exists."""
    lsd = Path(cwd or ".") / ".lark-slides"
    seal = lsd / ".seal"
    if not seal.exists() and not _sync_candidates(cwd):
        return
    try:
        d = json.loads(seal.read_text(encoding="utf-8"))
        d = d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        d = {}
    d[SEAL_BLOCKED] = {f.name: _sha(f) for f in sorted(lsd.glob("blocked-*.json"))}
    tmp = seal.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, seal)


def seal_broken(cwd, deck=None):
    """True when <cwd>/.lark-slides/.seal (sha256 of SYNC/frozen.lock and SYNC/exported, written by multiagent_sync
    whenever it writes them, and of the server-block counters blocked-*.json, written by Frame.publish) no longer
    matches the files: they were deleted or edited by hand to reopen pages / reset the block budget."""
    lsd = Path(cwd or ".") / ".lark-slides"
    with _SealLock(cwd, shared=True):
        try:
            d = json.loads((lsd / ".seal").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return False
        if not isinstance(d, dict):
            return False
        blocked = d.get(SEAL_BLOCKED)
        if isinstance(blocked, dict):
            names = set(blocked) | {f.name for f in lsd.glob("blocked-*.json")}
            if deck:   # another deck's counters are that task's business
                names = {n for n in names if n == f"blocked-{deck}.json"}
            if any(blocked.get(n) != _sha(lsd / n) for n in names):
                return True
        for sync, rec in d.items():
            if sync == SEAL_BLOCKED or not isinstance(rec, dict) or not Path(sync).is_dir():   # SYNC dir gone: other task
                continue
            if deck and sync_deck(sync) not in (None, str(deck)):
                continue
            for name, key in (("frozen.lock", "frozen"), ("exported", "exported")):
                if rec.get(key) != _sha(Path(sync) / name):
                    return True
    return False


def _frozen_lock(cwd, page, deck=None, deckless=True):
    """The SYNC dir whose frozen.lock (written by multiagent_sync when organizer_done freezes the pages, updated by
    finish when it unfreezes one) lists this page, or None. Independent of status.json, so deleting "frozen" there by
    hand does not reopen a page."""
    n = _page_no(page)
    if n is None:
        return None
    for d in _task_sync_dirs(cwd, deck, deckless):
        try:
            pages = json.loads((d / "frozen.lock").read_text(encoding="utf-8")).get("pages") or []
            if n in {int(x) for x in pages}:
                return d
        except (OSError, ValueError, TypeError, AttributeError):
            continue
    return None


MULTI_PAGE_FIX = "一条命令只提交一页：拆成多次调用，每次读完 lint 再提交下一页"
_WRITE_TOKENS = re.compile(r"\+(?:add|update|replace)-slide\b|\bpublish_slide\(|\brepublish_xml\(")
_PY_SCRIPT = re.compile(r"\bpython[\d.]*\s+(?:-[uBO]\s+)*([^\s;&|<>()]+\.py)((?:[ \t]+[^\s;&|<>()]+)*)")
_PY_LOOP = re.compile(r"^([ \t]*)for\b[^\n]*:[ \t]*\n(?:\1[ \t]+[^\n]*\n)*?\1[ \t]+[^\n]*"
                      r"(?:\bpublish_slide\(|\brepublish_xml\()", re.M)
_LOOP = re.compile(r"\b(?:for|while|until)\b[^\n;]*(?:;|\n)\s*do\b(.*?)\bdone\b", re.S)


_PARENT_CMD = {}


def _parent_cmdline():
    """Command line of the shell that started this python process ("" when unavailable; read once per process)."""
    ppid = os.getppid()
    if ppid not in _PARENT_CMD:
        out = ""
        try:   # Linux: raw argv (newlines intact)
            out = Path(f"/proc/{ppid}/cmdline").read_bytes().replace(b"\0", b" ").decode("utf-8", "replace")
        except OSError:
            try:   # macOS ps prints a newline inside an argument as the escape \012
                out = subprocess.run(["ps", "-ww", "-o", "command=", "-p", str(ppid)], capture_output=True, text=True,
                                     timeout=3, check=False).stdout.replace("\\012", "\n")
            except Exception:  # noqa: BLE001
                out = ""
        _PARENT_CMD[ppid] = out.strip()
    return _PARENT_CMD[ppid]


_HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1[^\n]*\n(.*?)\n\s*\2\s*(?:\n|$)", re.S)


def _strip_file_heredocs(cmd):
    """Drop heredoc bodies that are written to a file (cat > p05.py <<'EOF' … EOF && python3 p05.py writes one page):
    only a heredoc fed to python is code that runs now."""
    out, pos = [], 0
    for m in _HEREDOC.finditer(cmd):
        line = cmd[cmd.rfind("\n", 0, m.start()) + 1:m.start()]
        seg = re.split(r"&&|\|\||;|\|", line)[-1]
        if re.search(r"\bpython", seg):
            continue
        out.append(cmd[pos:m.start()] + "<<" + m.group(2) + "\n")
        pos = m.end()
    return "".join(out) + cmd[pos:]


def _is_page_script(path):
    """build_p05.py / lead_p02.py / p3.py / pages.py / lead_pages.py / page5.py / slide_03.py — not helper scripts
    such as slides_chart_tool.py, multiagent_sync.py or build_data.py."""
    stem = Path(path).stem.lower()
    return bool(re.search(r"(?:^|[_\-.])p\d{1,3}(?:$|[_\-.])", stem) or re.search(r"(?:^|_)pages?(?:$|_)", stem)
                or re.search(r"(?:^|_)(?:page|slide)_?\d+(?:$|_)", stem))


def multi_page_command(cmd=None):
    """Why the parent shell command writes more than one page ("" when it writes at most one): ≥2 page-write calls
    (+add/+update/+replace-slide, publish_slide(, republish_xml() and page-script runs (build_p05.py,
    lead_p02.py, pages.py 5 …) together, or a shell for/while loop around any of them. One python run with several
    page args (python3 pages.py 5 7 9) counts once here; inside the process publish_slide caps it at
    MAX_PAGES_PER_PROCESS (3) pages — the 4th page of the same process is refused (_process_page_error)."""
    cmd = _parent_cmdline() if cmd is None else cmd
    if not cmd:
        return ""
    cmd = _strip_file_heredocs(cmd)
    writes = _WRITE_TOKENS.findall(cmd)
    scripts = list(dict.fromkeys(m.group(0).strip() for m in _PY_SCRIPT.finditer(cmd) if _is_page_script(m.group(1))))
    for m in _LOOP.finditer(cmd):
        loop, body = m.group(0), m.group(1)
        if _WRITE_TOKENS.search(body) or any(_is_page_script(x.group(1)) for x in _PY_SCRIPT.finditer(body)) or (
                re.search(r"\bpython", body) and any(_is_page_script(re.sub(r"[*?]|\$\w+|\[[^\]]*\]", "1", t))   # build/p*.py
                                               for t in re.findall(r"[^\s;&|<>()]+\.py", loop))):
            return "shell 循环里提交页面"
    if _PY_LOOP.search(cmd):
        return "python 循环里提交页面（for … : publish_slide / republish_xml）"
    if len(writes) + len(scripts) >= 2 and len(_written_pages(cmd)) >= 2:
        return f"一条命令里有 {len(writes) + len(scripts)} 处写页（{', '.join((writes + scripts)[:4])}）"
    return ""


_PAGE_ARG = re.compile(r"\bpage\s*=\s*(\d{1,3})\b")
_REPUB_POS = re.compile(r"^\s*[^,()]+,\s*[^,()]+,\s*(\d{1,3})\b")
_PAGE_NAME = re.compile(r"(?<![A-Za-z0-9])(?:p|page|slide)[_\-]?0*(\d{1,3})(?![0-9])", re.I)


def _written_pages(cmd):
    """Distinct pages the write sites of a shell command target (main_p05.py && republish_xml('p05.xml', D, 5) is
    one page). A site whose page cannot be told (+add-slide, publish_slide without page=, pages.py without args)
    counts as a page of its own, so only provably-same-page chains collapse."""
    keys, n = set(), 0
    for m in _WRITE_TOKENS.finditer(cmd):
        tail = cmd[m.end():m.end() + 300].split("\n", 1)[0]
        k = None
        if m.group(0).startswith("+"):
            if not m.group(0).startswith("+add"):
                sid = re.search(r"--slide-id[ =]+['\"]?([\w-]+)", tail)
                k = f"sid:{sid.group(1)}" if sid else None
        else:
            hit = _PAGE_ARG.search(tail) or (m.group(0).startswith("republish") and _REPUB_POS.search(tail)) \
                or _PAGE_NAME.search(tail)
            k = int(hit.group(1)) if hit else None
        keys.add(k if k is not None else f"?{n}")
        n += 1
    for m in _PY_SCRIPT.finditer(cmd):
        if not _is_page_script(m.group(1)):
            continue
        hit = _PAGE_NAME.search(Path(m.group(1)).stem)
        args = [int(a) for a in (m.group(2) or "").split() if a.isdigit()]
        if hit and not args:
            keys.add(int(hit.group(1)))
        elif args:
            keys.update(args)
        else:
            keys.add(f"?{n}")
        n += 1
    return keys


def _multi_page_error():
    why = multi_page_command()
    if not why:
        return None
    return {"key": "multi_page_command", "code": "multi_page_command", "message": why, "fix": MULTI_PAGE_FIX}


NAV_BATCH = [False]   # set by exhibit.publish_contents_and_navs while it writes the navigation set
MAX_PAGES_PER_PROCESS = 3   # python3 pages.py 5 7 9 is fine; submit_page.py 18 31 (14 pages in one run) is not
_PROCESS_PAGES = []         # page keys this python process already sent to a deck (publish_slide / republish_xml / f.publish)
PROCESS_PAGES_FIX = (f"一个进程最多提交 {MAX_PAGES_PER_PROCESS} 页：每次运行只做 1–3 页，读完每页的 lint/截图再跑下一批；"
                     "不要用一个脚本循环生成、提交整份 deck")


def _process_key(presentation, page, slide_id):
    n = _page_no(page)
    return f"{presentation}:p{n}" if n is not None else (f"{presentation}:{slide_id}" if slide_id else None)


def _process_page_error(presentation, page, slide_id):
    """multi_page_command when this python process already published MAX_PAGES_PER_PROCESS other pages (a page sent
    again — same page number / slide — does not count twice). Pages count once written (_note_process_page)."""
    key = _process_key(presentation, page, slide_id)
    if key is not None and key in _PROCESS_PAGES:
        return None
    if NAV_BATCH[0]:   # publish_contents_and_navs: the contents + chapter navigation set is one library call
        return None
    if len(_PROCESS_PAGES) >= MAX_PAGES_PER_PROCESS:
        return {"key": "multi_page_command", "code": "multi_page_command",
                "message": f"同一个 python 进程已提交 {len(_PROCESS_PAGES)} 页，这是第 {len(_PROCESS_PAGES) + 1} 页",
                "fix": PROCESS_PAGES_FIX}
    return None


def _note_process_page(presentation, page, slide_id):
    key = _process_key(presentation, page, slide_id) or f"{presentation}:new{len(_PROCESS_PAGES)}"
    if key not in _PROCESS_PAGES:
        _PROCESS_PAGES.append(key)


# Chained processes (python3 fix.py 5 6 7 && python3 fix.py 8 9 10) each stay under the per-process cap, so the cap is
# also kept per writer and deck over a short window in .lark-slides/rate-<deck>.json. Only writes made from the same
# parent shell count together: every agent tool call (Bash) starts a new shell, so a Lead writing one page per command —
# however quickly — never adds up; one shell command chaining several page processes does.
WINDOW_PAGES = 3
WINDOW_S = 60
_now = time.time   # tests inject the clock
_ppid = os.getppid   # tests inject the parent shell


def _writer(who):
    """Who the window counts for: the ``who`` passed in (main / lead / builder2 …), else the parent shell process (one
    agent's commands come from one shell session)."""
    return str(who).strip().lower() if who else f"ppid{_ppid()}"


def _rate_path(cwd, deck):
    return Path(cwd or ".") / ".lark-slides" / f"rate-{deck}.json"


def _rate_read(cwd, deck):
    try:
        d = json.loads(_rate_path(cwd, deck).read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _rate_entry(v):
    """(t, parent pid) of one rate ledger entry (older ledgers stored just t: counted as this shell)."""
    if isinstance(v, dict):
        return float(v.get("t") or 0), v.get("ppid")
    return float(v), None


def _window_key(cwd, deck, page, slide_id):
    """Rate-window key of a write: a slide_id rewrite of a registered page counts as that page (page=N and
    slide_id=<its id> are the same page, so fixing one page several ways never adds up)."""
    if slide_id and _page_no(page) is None:
        _, registry = _page_registry(cwd or ".", deck)
        k = next((k for k, v in registry.items() if v == slide_id and re.fullmatch(r"p\d+", k)), None)
        if k:
            return f"{deck}:p{int(k[1:])}"
    return _process_key(deck, page, slide_id)


def _window_page_error(cwd, deck, who, page, slide_id):
    """multi_page_command when this writer already wrote WINDOW_PAGES other pages of this deck in the last WINDOW_S
    seconds from the same parent shell (one shell command chaining processes; slide_id rewrites count like page=
    writes). Writes from other shells (separate tool calls) and re-sending a page already in the window are free."""
    if NAV_BATCH[0]:
        return None
    key = _window_key(cwd, deck, page, slide_id)
    now, me = _now(), _ppid()
    recent = {}
    for k, v in (_rate_read(cwd, deck).get(_writer(who)) or {}).items():
        try:
            t, pp = _rate_entry(v)
        except (TypeError, ValueError):
            continue
        if now - t < WINDOW_S and pp in (None, me):
            recent[k] = t
    if key is not None and key in recent:
        return None
    if len(recent) >= WINDOW_PAGES:
        wait = int(WINDOW_S - (now - min(recent.values()))) + 1
        return {"key": "multi_page_command", "code": "multi_page_command",
                "message": f"同一条 shell 命令里 {WINDOW_S} 秒内已连续提交 {len(recent)} 页"
                           f"（{', '.join(sorted(k.split(':', 1)[1] for k in recent))}），"
                           f"这是第 {len(recent) + 1} 页——像是用 && 或脚本把多次写页串在一起",
                "fix": f"SKILL.md 规则 11：一条命令只写一页，读完这页的 lint/截图再写下一页（不要用 && 串多个进程）；"
                       f"单独用一次新的命令重提这一页（或约 {wait} 秒后；不要 sleep）"}
    return None


def _note_window_page(cwd, deck, who, page, slide_id):
    key = _window_key(cwd, deck, page, slide_id) or f"{deck}:new{int(_now() * 1000)}"
    f = _rate_path(cwd, deck)
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        import fcntl
        with open(f.with_suffix(".lock"), "w") as lk:
            fcntl.flock(lk, fcntl.LOCK_EX)
            d, now = _rate_read(cwd, deck), _now()
            keep = {}
            for w, pages in d.items():
                if not isinstance(pages, dict):
                    continue
                for k, v in pages.items():
                    try:
                        if now - _rate_entry(v)[0] < WINDOW_S:
                            keep.setdefault(w, {})[k] = v
                    except (TypeError, ValueError):
                        pass
            keep.setdefault(_writer(who), {})[key] = {"t": now, "ppid": _ppid()}
            tmp = f.with_suffix(".tmp")
            tmp.write_text(json.dumps(keep), encoding="utf-8")
            os.replace(tmp, f)
    except OSError:
        pass


# ------------------------------------------------------------------ one-shot layout holds (page= only)

def _skeleton(xml):
    """Layout signature of a page: sorted (element type, x/40, y/40, w/40, h/40) of its shapes / images / charts /
    tables, text content ignored. Two pages with the same signature have the same layout."""
    try:
        kids = _children(xml)
    except ET.ParseError:
        return None
    sig = []
    for el in kids:
        tag = el.tag.split("}")[-1]
        if tag not in ("shape", "img", "chart", "table", "embed"):
            continue
        try:
            box = tuple(round(float(el.get(k) or 0) / 40) for k in ("topLeftX", "topLeftY", "width", "height"))
        except ValueError:
            continue
        sig.append((tag + (f":{el.get('type')}" if el.get("type") else ""), *box))
    return sorted(sig) if len(sig) >= 5 else None   # a near-empty page (divider) has no layout worth comparing


def _skeleton_ledger(cwd, deck, page=None, sig=None):
    """<cwd>/.lark-slides/skeletons-<deck>.json {pNN: signature hash}; with page+sig: store it."""
    import hashlib
    f = Path(cwd or ".") / ".lark-slides" / f"skeletons-{deck}.json"
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        d = {}
    if page is not None and sig is not None:
        d[f"p{_page_no(page):02d}"] = hashlib.sha1(json.dumps(sig).encode()).hexdigest()[:16]
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(d), encoding="utf-8")
    return d


SAME_SKELETON_FIX = "连续 3 页版式完全相同：换一种版式（大图 + 要点 / 分栏 / 时间线 / 表格…）；只拦这一次，确实要保留就原样再提交一次"


def _same_skeleton(xml, cwd, deck, page):
    """Message when page N has the same layout signature as pages N−1 and N−2 (3 in a row), else None."""
    import hashlib
    n = _page_no(page)
    sig = _skeleton(xml)
    if n is None or n < 3 or sig is None:
        return None
    led = _skeleton_ledger(cwd, deck)
    h = hashlib.sha1(json.dumps(sig).encode()).hexdigest()[:16]
    if led.get(f"p{n - 1:02d}") == h and led.get(f"p{n - 2:02d}") == h:
        return f"P{n - 2}、P{n - 1}、P{n} 版式骨架完全相同（同样的元素、同样的位置，只换了文字/图片）"
    return None


LAYOUT_MAX, WHY_MAX = 20, 50


def _deck_id(presentation):
    """xml_presentation_id from an ID or a /slides/<id> URL (query / trailing slash dropped)."""
    p = str(presentation or "").split("?")[0].rstrip("/")
    return p.rsplit("/", 1)[-1] if "/" in p else p
_LEADS = {"main", "lead", "organizer", "org"}
LAYOUT_NOTE_FIX = (f'子代理每页 publish 都带 layout="这页版式（≤{LAYOUT_MAX} 字，如：左大图 + 右三条要点）"、'
                   f'why="为什么这样排能满足本页要求（≤{WHY_MAX} 字）"，一两句即可')
SAME_LAYOUT_FIX = ('换一种版式，并改写 layout / why；确实需要和相邻页同版式（如逐个城市同构对比）就加 '
                   'same_as_prev="理由（≤50 字）"')


def _is_subagent(who):
    """Page-writing subagents (R1…, builder1…, any other worker name); Main / Organizer / Lead and single-agent runs
    (who=None) are exempt from the per-page layout note."""
    return bool(who) and str(who).strip().lower() not in _LEADS


def _layout_ledger(cwd, deck, page=None, rec=None):
    """<cwd>/.lark-slides/layouts-<deck>.json {pNN: {layout, why, who, same_as_prev?}}; with page+rec: store it."""
    f = Path(cwd or ".") / ".lark-slides" / f"layouts-{deck}.json"
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        d = {}
    if page is not None and rec is not None:
        d[f"p{_page_no(page):02d}"] = rec
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    return d


def _norm_layout(s):
    return re.sub(r"[\s，,、；;：:（）()【】\[\]+＋/|·.。\-—]", "", str(s or "")).lower()


def _same_layout(a, b):
    import difflib
    a, b = _norm_layout(a), _norm_layout(b)
    return bool(a and b) and (a == b or difflib.SequenceMatcher(None, a, b).ratio() >= 0.8)


LAYOUT_FAMILIES = ("图表主导", "大图+注解", "对比两栏", "时间线", "矩阵四象限", "卡片网格", "引用大字", "流程图", "大数字+支撑")
DOMINANCE_MIN_PAGES, VISUAL_GAP = 12, 8
REPEAT_OK = "章节页 / 练习页这类刻意重复的页，写 same_as_prev=\"理由\" 说明即可"


def _layout_alternatives(led, layout):
    """2–3 generic layout families not resembling this layout nor any already in the ledger (fallback: any unlike it)."""
    used = [r.get("layout") for r in led.values() if isinstance(r, dict)]
    pool = [f for f in LAYOUT_FAMILIES if not _same_layout(f, layout) and _norm_layout(f) not in _norm_layout(layout)]
    fresh = [f for f in pool if not any(_norm_layout(f) in _norm_layout(u) or _same_layout(f, u) for u in used)]
    return "、".join((fresh + [f for f in pool if f not in fresh])[:3])


def _has_visual(xml, generated=()):
    """The page carries a picture (<img> / image fill), a native <chart> / <table> / <embed>, a generated chart / diagram
    fragment, or a native shape diagram (≥ 4 boxes tied together by ≥ 2 lines / connectors). Half-visual counts."""
    if generated or _images(xml):
        return True
    try:
        kids = _children(xml)
    except ET.ParseError:
        return False
    tags = [el.tag.split("}")[-1] for el in kids]
    if any(t in ("chart", "table", "embed") for t in tags):
        return True
    boxes = sum(1 for el, t in zip(kids, tags) if t == "shape" and el.get("type") in _DIAGRAM_SHAPES)
    lines = sum(1 for t in tags if t in ("line", "polyline", "connector"))
    return _hand_diagram(kids) or (boxes >= 4 and lines >= 2)


def _structure(xml, generated=()):
    """Coarse structural signature of a page, wording ignored — what the layout really is, however the builder describes
    it: each visual block (picture / chart / table / generated graphic, logos and icons < 3% of the canvas dropped) as
    kind@column(L/C/R)-size(big/mid/small), plus the body text boxes as count bucket and number of columns. Two pages
    "photo left + bullets right" share it even when one layout note says "左图右文" and the other "案例照片配要点"."""
    try:
        kids = _children(xml)
    except ET.ParseError:
        return None
    canvas, vis, gen_box, texts = 960.0 * 540.0, [], None, []
    for i, el in enumerate(kids):
        tag = el.tag.split("}")[-1]
        try:
            x, y, w, h = (float(el.get(k) or 0) for k in ("topLeftX", "topLeftY", "width", "height"))
        except ValueError:
            continue
        if i in generated:
            gen_box = (x, y, x + w, y + h) if gen_box is None else (min(gen_box[0], x), min(gen_box[1], y),
                                                                    max(gen_box[2], x + w), max(gen_box[3], y + h))
            continue
        img = tag == "img" or any(isinstance(c.tag, str) and c.tag.split("}")[-1] == "fillImg" for c in el.iter())
        kind = "pic" if img else tag if tag in ("chart", "table", "embed") else None
        if kind:
            vis.append((kind, x, w, w * h))
        elif tag == "shape" and "".join(el.itertext()).strip() and 100 <= y < 490:
            texts.append(x + w / 2)
    if gen_box is not None:
        gx0, gy0, gx1, gy1 = gen_box
        vis.append(("gfx", gx0, gx1 - gx0, (gx1 - gx0) * (gy1 - gy0)))
    parts = []
    for kind, x, w, area in vis:
        if area < 0.03 * canvas:
            continue
        cx = x + w / 2
        col = "L" if cx < 320 else "C" if cx < 640 else "R"
        size = "big" if area >= 0.3 * canvas else "mid" if area >= 0.1 * canvas else "small"
        parts.append(f"{kind}@{col}-{size}")
    if not parts and not texts:
        return None
    n = len(texts)
    cols = len({0 if c < 320 else 1 if c < 640 else 2 for c in texts})
    parts.append(f"text:{'0' if not n else '1-3' if n <= 3 else '4-6' if n <= 6 else '7+'}/c{cols}")
    return "|".join(sorted(parts))


def _struct_countable(sig):
    """Coarse structures compared across pages: picture / table / text-led ones. Chart- or generated-graphic-led pages
    vary by chart type, which the coarse signature cannot see — they only match on the exact skeleton."""
    return bool(sig) and not any(p.startswith(("chart@", "gfx@", "embed@")) for p in str(sig).split("|"))


def _struct_label(sig):
    """Readable name of a structural signature for messages ("pic@L-big|text:1-3/c1" → 大图+文字)."""
    names = {"pic": "图片", "chart": "图表", "table": "表格", "embed": "图示", "gfx": "图表/示意图"}
    vis = [names.get(p.split("@")[0], p) for p in str(sig).split("|") if "@" in p]
    return "+".join(dict.fromkeys(vis)) + "+文字" if vis else "纯文字"


STRUCT_VARIANTS_FIX = ("同构的条目页（逐个案例 / 城市 / 产品各一页）轮换 3–4 种结构变体（如 左图右文 / 上图下表 / 大数字+要点 / "
                       "对比两栏 / 满版图压字），换的是元素结构不是 layout 描述的措辞；确实刻意同构就写 same_as_prev=\"理由\"")
STRUCT_OVERUSE_SHARE = 0.35   # a structure may cover ~1/3 of the deck: rotating 3–4 variants always stays under it


def _visual_gap_warning(led, page):
    """Non-blocking note when page N closes a run of ≥ VISUAL_GAP ledger pages (page order) with no picture / chart.
    Pages recorded without the visual flag break the run (unknown)."""
    n = _page_no(page)
    nums = sorted(int(k[1:]) for k, r in led.items() if re.fullmatch(r"p\d+", k) and isinstance(r, dict))
    if n not in nums:
        return None
    i = j = nums.index(n)
    flat = lambda m: led[f"p{m:02d}"].get("visual") is False   # noqa: E731
    if not flat(n):
        return None
    while i > 0 and flat(nums[i - 1]):
        i -= 1
    while j < len(nums) - 1 and flat(nums[j + 1]):
        j += 1
    if j - i + 1 < VISUAL_GAP:
        return None
    return (f"P{nums[i]}–P{nums[j]} 连续 {j - i + 1} 页没有图片或图表：后续页内容允许时加一个视觉主体"
            f"（图片 / 图表 / 示意图），不要一路纯文字（仅提醒，不拦）")


def _layout_errors(xml, root, deck, page, layout, why, same_as_prev, generated=()):
    """Per-page layout note of a subagent: present and short, and different from the neighbouring pages that carry
    one (unless same_as_prev gives the reason). Describing the same element layout in other words is held once.
    Whole-deck checks (also waived by same_as_prev, the one "this repetition is deliberate" channel): A-B-A-B
    alternation over 4 consecutive pages, and — once the ledger has ≥ 12 pages — a layout already on more than
    max(3, 20% of ledger pages) pages. Both also fire on the page structure (_structure / the exact skeleton hash), not
    only the wording: alternating structures, or one structure on more than max(4, 35%) of the ledger pages."""
    import hashlib
    n = _page_no(page)
    layout, why = str(layout or "").strip(), str(why or "").strip()
    if not layout or not why:
        return [{"key": "layout_note_missing", "code": "layout_note_missing",
                 "message": "子代理写页没有带 layout / why", "fix": LAYOUT_NOTE_FIX}]
    layout, why = layout[:LAYOUT_MAX], why[:WHY_MAX]   # an over-long note is cut, never a hold (a page rewrite for 3 chars)
    if same_as_prev:
        return []
    led = _layout_ledger(root, deck)
    for m in (n - 1, n + 1):
        rec = led.get(f"p{m:02d}")
        if isinstance(rec, dict) and _same_layout(layout, rec.get("layout")):
            return [{"key": "same_layout_as_neighbor", "code": "same_layout_as_neighbor",
                     "message": f"P{n} 的版式「{layout}」与相邻 P{m} 的「{rec.get('layout')}」相同",
                     "fix": SAME_LAYOUT_FIX}]
    lay_of = lambda m: layout if m == n else (led.get(f"p{m:02d}") or {}).get("layout")   # noqa: E731
    skel = _skeleton_ledger(root, deck)
    sig_now = _skeleton(xml)
    h_now = hashlib.sha1(json.dumps(sig_now).encode()).hexdigest()[:16] if sig_now else None
    st_now = _structure(xml, generated)

    def struct_of(m):   # (coarse structure, exact skeleton hash) of a ledger page, or of this page
        if m == n:
            return st_now, h_now
        rec = led.get(f"p{m:02d}")
        return ((rec.get("skel") if isinstance(rec, dict) else None),
                (skel.get(f"p{m:02d}") if isinstance(rec, dict) else None))

    empty = hashlib.sha1(b"[]").hexdigest()[:16]   # near-empty pages are stored with the hash of []

    def same_struct(a, b):
        sa, sb = struct_of(a), struct_of(b)
        return bool((_struct_countable(sa[0]) and sa[0] == sb[0]) or (sa[1] and sa[1] != empty and sa[1] == sb[1]))

    for s in range(n - 3, n + 1):   # A-B-A-B: each 4-page window holding page n
        if all(isinstance(lay_of(m), str) for m in range(s, s + 4)) \
                and _same_layout(lay_of(s), lay_of(s + 2)) and _same_layout(lay_of(s + 1), lay_of(s + 3)):
            return [{"key": "alternating_layout", "code": "alternating_layout",
                     "message": f"P{s}–P{s + 3} 两种版式交替（「{lay_of(s)}」/「{lay_of(s + 1)}」）",
                     "fix": f"这页换一种版式（如 {_layout_alternatives(led, layout)}）并改写 layout / why；{REPEAT_OK}"}]
        if all(isinstance(lay_of(m), str) for m in range(s, s + 4)) and same_struct(s, s + 2) \
                and same_struct(s + 1, s + 3) and not same_struct(s, s + 1):
            return [{"key": "alternating_layout", "code": "alternating_layout",
                     "message": f"P{s}–P{s + 3} 版式结构两种交替（layout 描述不同，但元素结构是"
                                f"「{_struct_label(struct_of(s)[0])}」/「{_struct_label(struct_of(s + 1)[0])}」轮流）",
                     "fix": STRUCT_VARIANTS_FIX}]
    others = {k: r for k, r in led.items() if isinstance(r, dict) and k != f"p{n:02d}"}
    if len(others) >= DOMINANCE_MIN_PAGES:
        cap = max(3, int(0.2 * len(others)))
        hits = sorted(int(k[1:]) for k, r in others.items() if k[1:].isdigit() and _same_layout(layout, r.get("layout")))
        if len(hits) > cap:
            pages = "、".join(f"P{m}" for m in hits[:8]) + ("…" if len(hits) > 8 else "")
            return [{"key": "layout_overused", "code": "layout_overused",
                     "message": f"版式「{layout}」已用在 {len(hits)} 页（{pages}），超过全稿上限 {cap} 页",
                     "fix": f"换一种版式（如 {_layout_alternatives(led, layout)}）并改写 layout / why；{REPEAT_OK}"}]
        cap = max(4, int(STRUCT_OVERUSE_SHARE * len(others)))
        hits = sorted(int(k[1:]) for k in others if k[1:].isdigit() and not others[k].get("same_as_prev")
                      and same_struct(n, int(k[1:])))
        if len(hits) > cap:
            pages = "、".join(f"P{m}" for m in hits[:8]) + ("…" if len(hits) > 8 else "")
            return [{"key": "layout_overused", "code": "layout_overused",
                     "message": f"版式结构「{_struct_label(st_now)}」已用在 {len(hits)} 页（{pages}，layout 描述各不相同），"
                                f"超过全稿上限 {cap} 页",
                     "fix": STRUCT_VARIANTS_FIX}]
    if sig_now:
        h = h_now
        for m in (n - 1, n + 1):
            if isinstance(led.get(f"p{m:02d}"), dict) and skel.get(f"p{m:02d}") == h \
                    and _first_hold_mark(root, f"held-layout-{deck}.json", page):
                return [{"key": "layout_note_mismatch", "code": "layout_note_mismatch",
                         "message": f"layout 写的与 P{m} 不同，但两页元素位置完全相同",
                         "fix": "真的换一种版式；确实要同版式就写 same_as_prev=\"理由\"（只拦这一次）"}]
    return []


SAMPLE_LABEL_FIX = "页脚统一声明一次'示例数据'，正文里不逐项写'示例'；只拦这一次，确实要保留就原样再提交一次"


def _page_no(page):
    m = re.fullmatch(r"p?0*(\d+)", str(page)) if page is not None else None
    return int(m.group(1)) if m else None


def deck_dir(cwd, deck):
    """<cwd>/.lark-slides/decks/<deck>/: per-deck task settings (logo.json, sample.flag, palette.json). Keyed by the deck
    ID every write passes, so a second deck made in the same CWD starts with none of the first one's settings."""
    return Path(cwd or ".").resolve() / ".lark-slides" / "decks" / str(deck)


def _stored_logo(cwd, deck=None):
    """{"token", "w", "h"} of this deck's brand logo (.lark-slides/decks/<deck>/logo.json, written by exhibit
    set_logo(..., deck=)), or None. Without a deck there is no logo to require."""
    if not deck:
        return None
    try:
        d = json.loads((deck_dir(cwd, deck) / "logo.json").read_text(encoding="utf-8"))
        return d if d.get("token") and float(d.get("w") or 0) > 0 and float(d.get("h") or 0) > 0 else None
    except (OSError, ValueError, TypeError, AttributeError):
        return None


def _logo_variants(logo):
    """{token: {"name", "w", "h", "want"}} for the deck's logo and every registered variant (set_logo(..., variant=)):
    any of them counts as the logo, each checked against its own aspect ratio."""
    out = {}
    if not logo:
        return out
    extra = logo.get("variants") if isinstance(logo.get("variants"), dict) else {}
    for name, v in [(None, logo)] + sorted(extra.items()):
        try:
            w, h = float(v.get("w") or 0), float(v.get("h") or 0)
        except (TypeError, ValueError, AttributeError):
            continue
        if v.get("token") and w > 0 and h > 0 and str(v["token"]) not in out:
            out[str(v["token"])] = {"name": name, "w": v["w"], "h": v["h"], "want": w / h}
    return out


COVER_IMAGE_SHARE = 0.5
COVER_COMPOSITION_SHARE = 0.25


def _cover_image_area(xml, skip=()):
    """Union of exposed picture bounds, weighted by alpha and later rectangular fills; logos do not count."""
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return 0.0
    layers = []

    def opacity(element):
        try:
            value = float(element.get("alpha", "1"))
            colour = element.get("color", "")
            if "gradient(" in colour:   # a gradient mask hides the photo by the mean alpha of its stops, not fully
                stops = re.findall(r"rgba?\(([^)]*)\)|\btransparent\b", colour)
                alphas = [0.0 if not s else float(s.split(",")[3]) if s.count(",") == 3 else 1.0 for s in stops]
                value *= sum(alphas) / len(alphas) if alphas else 1.0
            elif colour.startswith("rgba("):
                value *= float(colour.rsplit(",", 1)[1].rstrip(")"))
            return min(1.0, max(0.0, value))
        except (ValueError, IndexError):
            return 1.0

    style = root.find(f"{{{_SML}}}style")
    if style is not None:
        background = next((child for child in style.iter() if child.tag == f"{{{_SML}}}fillImg"
                           and child.get("src") and child.get("src") not in skip), None)
        if background is not None:
            layers.append((0.0, 0.0, 960.0, 540.0, True, opacity(background)))
    for el in _children(xml):
        tag = el.tag.split("}")[-1]
        fill = next((child for child in el.iter() if child.tag in
                     (f"{{{_SML}}}fillImg", f"{{{_SML}}}fillColor")), None)
        src = el.get("src") if tag == "img" else next(
            (c.get("src") for c in el.iter() if isinstance(c.tag, str) and c.tag.split("}")[-1] == "fillImg"), None)
        if src in skip or (not src and (el.get("type") not in ("rect", "text") or fill is None)):
            continue
        try:
            x, y = float(el.get("topLeftX") or 0), float(el.get("topLeftY") or 0)
            w, h = float(el.get("width") or 0), float(el.get("height") or 0)
        except ValueError:
            continue
        left, top, right, bottom = max(0.0, x), max(0.0, y), min(x + w, 960.0), min(y + h, 540.0)
        if not (0 <= left < right <= 960 and 0 <= top < bottom <= 540):
            continue
        alpha = opacity(el) * (opacity(fill) if fill is not None else 1.0)
        if alpha:
            layers.append((left, top, right, bottom, bool(src), alpha))
    edges = sorted({edge for layer in layers for edge in (layer[0], layer[2])})
    area = 0.0
    for left, right in zip(edges, edges[1:]):
        active = [layer for layer in layers if layer[0] <= left and layer[2] >= right]
        heights = sorted({edge for layer in active for edge in (layer[1], layer[3])})
        for top, bottom in zip(heights, heights[1:]):
            visible = 0.0
            for layer in active:
                if layer[1] <= top and layer[3] >= bottom:
                    visual, alpha = layer[4:]
                    visible = alpha * visual + (1 - alpha) * visible
            area += (right - left) * (bottom - top) * visible
    return area


def _cover_text_hierarchy(xml):
    """An editorial split needs an actual large title and smaller supporting text, not empty font attributes."""
    runs = []

    def walk(node, size):
        try:
            size = float(node.get("fontSize", size))
            alpha = float(node.get("alpha", "1"))
        except (TypeError, ValueError):
            return
        if alpha <= 0:
            return
        if node.text and len(re.sub(r"\s", "", node.text)) >= 3:
            runs.append(size)
        for child in node:
            walk(child, size)
            if child.tail and len(re.sub(r"\s", "", child.tail)) >= 3:
                runs.append(size)

    for element in _children(xml):
        if not _is_text(element):
            continue
        try:
            left, top, width, height = (float(element.get(key, "0")) for key in
                                        ("topLeftX", "topLeftY", "width", "height"))
        except ValueError:
            continue
        if 0 <= left < 960 and 0 <= top < 440 and width > 0 and height > 0:
            walk(element, 18)
    title_size = max(runs, default=0)
    return title_size >= 28 and any(12 <= size <= title_size * 0.75 for size in runs)


def _images(xml):
    """(src, width, height) of every picture on the page: <img> elements and image-filled shapes (<fillImg>)."""
    out = []
    try:
        kids = _children(xml)
    except ET.ParseError:
        return out
    for el in kids:
        tag = el.tag.split("}")[-1]
        src = el.get("src") if tag == "img" else next(
            (c.get("src") for c in el.iter() if isinstance(c.tag, str) and c.tag.split("}")[-1] == "fillImg"), None)
        if src is None:
            continue
        try:
            w, h = float(el.get("width") or 0), float(el.get("height") or 0)
        except ValueError:
            w = h = 0.0
        out.append((src, w, h))
    return out


_PLACEHOLDER = re.compile(   # bare 占位 is a normal word ("先发者占位牢固"): only placeholder phrasings match
    r"(?<![A-Za-z])[Xx]{2,}(?![A-Za-z])|(?<![A-Za-z\d.])[<≈~约]?\s*X\s*(?:%|亿|万|倍|个百分点|pt|周|个月|家)|占位符|(?:示例|模板|仅)占位|(?<!成)为占位|[（(]\s*占位\s*[）)]|【[^】]{0,12}占位[^】]{0,12}】"
    r"|待补(?![强位齐足短货仓课贴偿救])|待\s*(?:R\d|研究|调研|后续|核实|确认)\s*(?:后)?(?:补|填|更新)|(?<![A-Za-z])TODO(?![A-Za-z])|example\.com|000-0000"
    r"|(?<![\w.])[Xx]{2,}@[\w.\-]*|[\w.+\-]+@example\b"
    r"|【\s*】|【[^】]{0,12}(?:姓名|名字|名称|日期|时间|电话|手机|邮箱|地址|填写|输入|汇报人|部门|公司|职位|标题|内容|插入|图片)[^】]{0,8}】"
    # a "?" standing in for a number ("1-? 月"): a real question has a word before its "?" and never matches
    r"|\d\s*[-–~至]\s*[?？]|(?<![一-鿿A-Za-z])[?？]{1,2}\s*(?:月|年|日|季度|%|亿|万)|(?<![^\s\d.,:：/（(\-–~])[?？]{2,}")
PLACEHOLDER_FIX = "用户没给的信息（汇报人、电话、邮箱等）整行删掉或写合理示例并标'示例'，不留 XX/占位"

# Invented phone numbers (400-000-0000, 000-0000-0000, 138 0000 0000): never a sample worth showing — not waivable.
_FAKE_PHONE = re.compile(r"(?<!\d)400[-\s]?0{3}[-\s]?0{4}(?!\d)|(?<!\d)0{3}-0{4}-0{4}(?!\d)"
                         r"|(?<!\d)1[3-9]\d[-\s]?\d{4}[-\s]?\d{4}(?!\d)")
FAKE_PHONE_FIX = "用户没提供的联系方式不要编：整行删掉（咨询电话/手机/热线），不要写 400-000-0000 之类的假号码再标'示例'"

# A Python expression that reached the slide unevaluated: an f-string without its f prefix, or a template variable
# never substituted. Not waivable — no reader should ever see it.
_CODE_LEAK = re.compile(
    r"\{\(?\s*[A-Za-z_][\w.]*\s*[\[\(][^{}\n]{0,80}\}"      # {M_R1['capex'][…]…} / {(a / b - 1):+.1%} / {f(x)}
    r"|\{\(\s*[A-Za-z_]\w*\s*\["                            # {(M_R1[…
    r"|:[+\-]?,?\.\d+[%f]\}"                                # :+.1%}  :.1f}  :,.0f}
    r"|(?<![\w])M_R\d|\bMETRICS\[|(?<![\w])F\[['\"\w]|\bSRC(?:_R\d)?\[")
# business decks only: role names / long floats / None / ['a'] are ordinary text in academic or teaching pages
_CODE_LEAK_BIZ = re.compile(
    r"[（(]\s*(?:accent|neg|main|second|third|light2?|deep|context|ink|sub)\s*[）)]"   # palette role names typed as text
    r"|(?<![\d.])\d+\.\d{6,}(?![\d])"   # 14.305350434780628%: a float printed without formatting
    r"|<[\w.]+ object at 0x[0-9a-fA-F]+>|\bobject at 0x[0-9a-fA-F]{6,}"   # a Python object (Bar(...), Col) printed as text
    r"|<(?:function|bound method|class|module) [\w.]+"
    r"|\[\s*'[^'\n]{1,60}'\s*(?:,\s*'[^'\n]{0,60}'\s*)*\]"   # ['a', 'b']: a list printed with str()
    r"|(?:^|[|｜\s])None(?=$|[|｜\s])")   # a missing value printed as the word None
UNFORMATTED_MSG = "正文里有没求值的 Python 表达式：字符串漏了 f 前缀或变量没替换"
UNFORMATTED_FIX = ("给拼出这段文字的字符串加 f 前缀（或 .format() 代入变量），长小数用格式化写法（f\"{v:.1f}%\" / fmt(v)），"
                   "在页面脚本里 print 一下确认已是数字，再重提；"
                   "不要 waive，也不要手改 XML 里的表达式")
_NO_WAIVE = {"logo_cropped", "unformatted_code", "fake_phone", "control_chars"}


def unformatted_hint(leaks):
    """The fix that fits what leaked (a printed object / list / None is not a missing f prefix)."""
    j = " ".join(leaks)
    if "object at 0x" in j or re.search(r"<(?:function|bound method|class|module) ", j):
        return ("页面上印出了 Python 对象（如 Bar(...) 放进了只收文字的表格 / 文本块）：图形列只在 row_table 的 columns 里用，"
                "表格单元格、text、kv 写成字符串")
    if any(re.fullmatch(r"\[\s*'.*'\s*\]", x.strip()) for x in leaks):
        return "页面上印出了 Python 列表 ['…', '…']：text 块传字符串或列表（每项一行），不要 str(列表)"
    if re.search(r"(?:^|\s)None(?:\s|$)", j):
        return "页面上印出了 None：缺失值写'—'或'未披露'，或删掉这一格"
    return UNFORMATTED_FIX


def unformatted_code(text, business=False):
    """Snippets of unevaluated Python (format expressions / research variable names) in visible text, [] if none;
    ``business`` adds the printed-value patterns (_CODE_LEAK_BIZ)."""
    pats = (_CODE_LEAK, _CODE_LEAK_BIZ) if business else (_CODE_LEAK,)
    return list(dict.fromkeys(m.group(0)[:60] for p in pats for m in p.finditer(text or "")))


def _fake_phones(xml):
    try:
        kids = _children(xml)
    except ET.ParseError:
        return []
    found = []
    for el in kids:
        for m in _FAKE_PHONE.finditer(_texts(el)):
            digits = re.sub(r"\D", "", m.group(0))
            if digits.startswith("1") and len(digits) == 11 and digits.count("0") < 7:
                continue   # a real-looking mobile number: only all-zero fillers are fake
            found.append(m.group(0))
    return list(dict.fromkeys(found))


def _code_leaks(xml, business=False):
    """unformatted_code() over the page's visible text (<data> only; speaker notes are not shown)."""
    try:
        kids = _children(xml)
    except ET.ParseError:
        return []
    return unformatted_code("\n".join(_texts(el) for el in kids), business)


def _texts(el):
    """Visible text of a page element (all nested text, attributes excluded)."""
    return "".join(t for t in el.itertext())


def _placeholders(xml):
    """Placeholder runs left in the page text (<data> only; speaker notes are not shown): XX / XXX, 占位, 待补, TODO,
    example.com, 000-0000, 【】 / 【汇报人姓名】-style template brackets. Real words with X (XXL, XL) do not match."""
    try:
        kids = _children(xml)
    except ET.ParseError:
        return []
    found = []
    for el in kids:
        found += [m.group(0) for m in _PLACEHOLDER.finditer(_texts(el))]
    return list(dict.fromkeys(found))


def _canvas_scale(cwd=None, presentation=None):
    """(width / 960, height / 540) of the page canvas: LARK_SLIDE_CANVAS_W/H, else the deck's known canvas (canvas.json
    cache / source-slides/full.xml — no server call), else 960×540."""
    try:
        if os.environ.get("LARK_SLIDE_CANVAS_W"):
            return (float(os.environ["LARK_SLIDE_CANVAS_W"]) / 960,
                    float(os.environ.get("LARK_SLIDE_CANVAS_H") or 540) / 540)
    except ValueError:
        pass
    canvas = _deck_canvas(cwd, presentation, fetch=False) if presentation else None
    return (canvas[0] / 960, canvas[1] / 540) if canvas else (1.0, 1.0)


def _tiny_text_warning(xml, share=0.30, small=10, min_chars=40, scale=None):
    """Warning (not a block) when > share of the page's body text is set below `small` pt (× canvas width / 960) —
    footer / source boxes at the bottom of the page (top ≥ 440 and reaching y ≥ 500, scaled) and speaker notes are not
    counted."""
    try:
        kids = _children(xml)
    except ET.ParseError:
        return None
    sx, sy = scale or _canvas_scale()
    small = small * sx
    tot = tiny = 0

    def walk(node, size):
        nonlocal tot, tiny
        fs = node.get("fontSize")
        try:
            size = float(fs) if fs else size
        except ValueError:
            pass
        for chunk, sz in ((node.text, size),):
            n = len(re.sub(r"\s", "", chunk or ""))
            tot += n
            tiny += n if sz is not None and sz < small else 0
        for ch in node:
            if isinstance(ch.tag, str):
                walk(ch, size)
            n = len(re.sub(r"\s", "", ch.tail or ""))
            tot += n
            tiny += n if size is not None and size < small else 0

    for el in kids:
        try:
            y, h = float(el.get("topLeftY") or 0), float(el.get("height") or 0)
        except ValueError:
            y, h = 0.0, 0.0
        if y >= 440 * sy and y + h >= 500 * sy:
            continue
        walk(el, None)
    if tot >= min_chars and tiny > share * tot:
        return (f"正文字号过小：{tiny}/{tot} 字小于 {small:g}pt（{tiny / tot:.0%}）——放大到 ≥{14 * sx:g}（来源/脚注除外），"
                "放不下就删字或拆成图表")
    return None


def _sample_label_warning(xml, limit=2, footer_y=500):
    """Warning (not a block) when "示例" appears more than `limit` times in the page body — speaker notes and the footer
    band (elements starting at y ≥ footer_y) are not counted: one sample-data disclaimer in the footer is enough."""
    try:
        kids = _children(xml)
    except ET.ParseError:
        return None
    n = 0
    for el in kids:
        try:
            y = float(el.get("topLeftY") or 0)
        except ValueError:
            y = 0.0
        if y >= footer_y:
            continue
        n += _texts(el).count("示例")
    if n > limit:
        return f"本页'示例'出现 {n} 次：统一在页脚声明一次；用户没给的主办方/单位等信息整行删掉"
    return None


def _local_blocks(xml, page, cwd, waive, deck=None, profile="auto"):
    """Page checks made before anything is sent: brand logo present and uncropped, cover has a key visual."""
    errs = []
    logo = _stored_logo(cwd, deck)
    imgs = _images(xml)
    variants = _logo_variants(logo)
    if logo and page is not None:
        tok = str(logo["token"])
        mine = [(w, h, variants[s]) for s, w, h in imgs if s in variants]
        if not any(t in xml for t in variants):
            errs.append({"key": "logo_missing", "code": "logo_missing",
                         "message": f"本 deck 有品牌 logo（.lark-slides/decks/{deck}/logo.json，token {tok}），这页没有放",
                         "fix": f"在 <data> 里加入 logo_xml(cwd=CWD, deck={deck!r}) 返回的 <img>（按原图比例，不改宽高）",
                         "hint": "frame(..., deck=<deck>) 的页会自动放 logo（cwd 传任务 CWD）；"
                                 "确实不该放 logo 的页才 waive=['logo_missing']"})
        bad = [(w, h, v) for w, h, v in mine
               if w > 0 and h > 0 and abs(w / h - v["want"]) / v["want"] > 0.03]
        if bad:
            w, h, v = bad[0]
            vx = f", variant={v['name']!r}" if v["name"] else ""
            errs.append({"key": "logo_cropped", "code": "logo_cropped",
                         "message": f"logo 的宽高比 {w / h:.2f} 与原图 {v['want']:.2f} 不一致：服务端会从中间裁掉一部分",
                         "fix": f"用 logo_xml(cwd=CWD, deck={deck!r}{vx}) 返回的 <img> 原样放（宽 {v['w']}、高 {v['h']}，"
                                "或按同一比例缩放），不要自己改宽高、不要塞进固定方框"})
    if _page_no(page) == 1:
        area = _cover_image_area(xml, variants)
        share = area / (960 * 540)
        if share < COVER_IMAGE_SHARE and not (share >= COVER_COMPOSITION_SHARE and _cover_text_hierarchy(xml)):
            pct = round(100 * area / (960 * 540))
            errs.append({"key": "cover_no_image", "code": "cover_no_image",
                         "message": (f"封面可见主视觉占 {pct}%（多图去重、扣除透明/矩形遮挡，不含 logo）："
                                     "需 ≥50%，或 ≥25% 且有大标题与较小说明的清晰层级"
                                     if area else "封面没有可见主视觉（只有文字、logo 或被遮住的图）"),
                         "fix": "按题材用相关真素材做摄影、多图或图文结构；图文需 ≥28pt 标题与 12pt 以上较小说明，"
                                "图太小则扩大有效主视觉，不加隐藏背景图凑面积；不做无视觉标题卡"})
    ph = _placeholders(xml)
    if ph:
        errs.append({"key": "placeholder_text", "code": "placeholder_text",
                     "message": f"页面里还有占位文字 {ph[:4]}", "fix": PLACEHOLDER_FIX})
    phones = _fake_phones(xml)
    if phones:
        errs.append({"key": "fake_phone", "code": "fake_phone", "message": f"页面里有编造的电话号码 {phones[:3]}",
                     "fix": FAKE_PHONE_FIX})
    code = _code_leaks(xml, _business(cwd, deck, profile))
    if code:
        errs.append({"key": "unformatted_code", "code": "unformatted_code",
                     "message": f"{UNFORMATTED_MSG}（{code[:2]}）", "fix": UNFORMATTED_FIX})
    return [e for e in errs if e["key"] not in waive or e["key"] in _NO_WAIVE]


OFF_PALETTE_FIX = ("全稿一套色：手写 XML 与图表只用本 deck set_palette 的色值（deck_palette(cwd=CWD, deck=<deck>) / frame 的 f.C；"
                   "内容页底色统一白色，与 frame 页一致）；不要给 frame / Exhibit 另传 palette=。只拦这一次，确有理由就原样再提交一次")
_CSS_COL = re.compile(r'(?:color|fill|stroke)="(rgba?\([^)]*\)|#[0-9A-Fa-f]{6})"')


def _rgba(c):
    """(r, g, b, alpha) of rgb()/rgba()/#hex, else None."""
    c = str(c).strip()
    try:
        if c.startswith("#") and len(c) == 7:
            return int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16), 1.0
        if c.startswith("rgb"):
            v = [float(x) for x in c[c.index("(") + 1:c.index(")")].split(",")]
            return int(v[0]), int(v[1]), int(v[2]), (v[3] if len(v) > 3 else 1.0)
    except (ValueError, IndexError):
        return None
    return None


def _hls(rgb):
    import colorsys
    return colorsys.rgb_to_hls(*(v / 255 for v in rgb[:3]))


def _palette_colours(cwd, deck):
    """(brand hues in degrees, exact palette colours) of this deck's set_palette, or None when none was recorded."""
    try:
        pal = json.loads((deck_dir(cwd, deck) / "palette.json").read_text(encoding="utf-8")).get("palette")
    except (OSError, ValueError, AttributeError):
        return None
    if not pal:
        return None
    try:
        from ..exhibit._palette import roles
        C = roles(pal)
    except Exception:  # noqa: BLE001 — unknown palette name: nothing to compare against
        return None
    exact = [v for v in C.values() if isinstance(v, str) and v.startswith("#")]
    if isinstance(pal, dict):
        exact += [str(v) for k, v in pal.items() if k in ("bg", "ink", "accent", "secondary")]
        exact += [str(v) for v in pal.get("series") or []]
    hues = set()
    for k in ("main", "accent", "second", "light", "light2", "third", "deep"):
        rgb = _rgba(C.get(k, ""))
        if rgb:
            h, l, s = _hls(rgb)
            if s > 0.15 and 0.08 < l < 0.95:
                hues.add(round(h * 360))
    return hues, [x for x in (_rgba(c) for c in exact) if x]


def _snap_off_palette(xml, cwd, deck):
    """business-research decks: a saturated colour whose hue is not the deck palette's family (a hand-typed red / blue
    on a green deck) becomes the palette colour of nearest lightness — written as is, no rework round."""
    if not (deck and _style_is("research", cwd, deck)):
        return xml
    pc = _palette_colours(cwd, deck)
    if not pc or not pc[0]:
        return xml
    hues, exact = pc
    try:
        from ..exhibit._palette import roles as _roles_
        pal_ = json.loads((deck_dir(cwd, deck) / "palette.json").read_text(encoding="utf-8")).get("palette")
        C_ = _roles_(pal_)
        gb = [x for x in (_rgba(C_.get("good", "")), _rgba(C_.get("bad", ""))) if x]
    except Exception:  # noqa: BLE001
        gb = []
    keep = [e for e in exact if not any(e[:3] == g[:3] for g in gb)]
    choices = [e for e in exact if _hls(e)[2] > 0.15 and any(
        min(abs(_hls(e)[0] * 360 - x), 360 - abs(_hls(e)[0] * 360 - x)) <= 25 for x in hues)]
    if not choices:
        return xml

    def swap(m):
        c = m.group(1)
        rgb = _rgba(c)
        if not rgb or rgb[3] < 0.3:
            return m.group(0)
        h, l, s_ = _hls(rgb)
        if s_ <= 0.25 or l <= 0.12 or l >= 0.9:
            return m.group(0)
        deg = h * 360
        if any(min(abs(deg - x), 360 - abs(deg - x)) <= 25 for x in hues):
            return m.group(0)
        if any(sum((a - b) ** 2 for a, b in zip(rgb[:3], e[:3])) ** 0.5 <= 24 for e in keep):
            return m.group(0)   # a colour the palette itself defines (its neg, tints) — only good / bad green / blue move
        best = min(choices, key=lambda e: abs(_hls(e)[1] - l))
        new = "rgba(%d,%d,%d,%g)" % (*best[:3], rgb[3]) if c.startswith("rgba") else "rgb(%d,%d,%d)" % best[:3]
        return m.group(0).replace(c, new)
    return _CSS_COL.sub(swap, xml)


def _palette_bg(cwd, deck):
    """Background colour of this deck's palette (white, warm white, cream… — whatever set_palette chose), or None."""
    try:
        pal = json.loads((deck_dir(cwd, deck) / "palette.json").read_text(encoding="utf-8")).get("palette")
        from ..exhibit._palette import roles
        C = roles(pal)
    except Exception:  # noqa: BLE001
        return None
    for v in ([pal.get("bg")] if isinstance(pal, dict) else []) + [C.get("bg"), C.get("paper"), C.get("background")]:
        rgb = _rgba(v or "")
        if rgb:
            return rgb
    return None


def _speech_layout(xml, cwd, deck, page):
    """business-deck (speech) pages read in one direction: big tables (> 3×3 native <table>) and multi-layer pages
    (a row of ≥3 big numbers stacked with charts, a dark full-width conclusion bar under charts, ≥3 charts) are flagged.
    Returns a message or ""."""
    if not _style_is("speech", cwd, deck) or (_page_no(page) or 0) <= 1:
        return ""
    msgs = []
    for tb in re.findall(r"<table\b.*?</table>", xml, re.S):
        rows = re.findall(r"<tr\b.*?</tr>", tb, re.S)
        cols = max([len(re.findall(r"<td\b", r)) for r in rows] or [0])
        if len(rows) > 3 or cols > 3:
            msgs.append(f"表格 {len(rows)} 行 × {cols} 列（演讲型 deck 最多 3×3）：对比改横向条形 / 哑铃 / 分组柱，"
                        "每个指标一张小图或只挑 1–2 个关键指标，其余进讲稿")
    charts = len(re.findall(r"<chart\b", xml))
    groups = len(re.findall(r"<(?:shape|img)\b[^>]*\bdata-exhibit=", xml))
    n_charts = max(charts, 1 if groups else 0)
    sizes = [float(s) for s in re.findall(r'fontSize="([\d.]+)"', xml)]
    big_nums = len([s for s in sizes if s >= 26]) - 1          # minus the title
    has_bar = bool(re.search(r'<shape\b[^>]*\bwidth="(?:8[5-9]\d|9[0-6]\d)(?:\.\d+)?"[^>]*\bheight="(?:[2-5]\d)(?:\.\d+)?"'
                             r'[^>]*\btopLeftY="(?:4[2-9]\d|50\d)', xml))
    if n_charts >= 3:
        msgs.append(f"一页 {n_charts} 张图（演讲型 deck 最多 2 张并排）")
    if n_charts and big_nums >= 3:
        msgs.append("大数字行 + 图表叠在同一页（阅读方向混杂）：二选一——2 张图并排（左→右），或一行 2–3 个大数字 / 一句结论 + 1 张图（上→下）")
    if n_charts and has_bar:
        msgs.append("图下方有通栏结论条：标题已经是结论，删掉底部结论条")
    return "；".join(msgs)


def _off_palette(xml, cwd, deck, page):
    """business-deck (speech) decks: colours a page paints that are not this deck's palette — a light background other
    than white on a content page, or a saturated fill / text / line colour whose hue is not the brand family and that is
    not one of the palette's exact colours (good / bad / series…). "" when fine or no palette was set."""
    if not _style_is("speech", cwd, deck):
        return ""
    pc = _palette_colours(cwd, deck)
    if not pc:
        return ""
    hues, exact = pc
    msgs = []
    m = re.search(r"<style>\s*<fill[^>]*>\s*<fillColor color=\"([^\"]+)\"", xml)
    bg = _rgba(m.group(1)) if m else None
    want = _palette_bg(cwd, deck) or (255, 255, 255)
    if bg and bg[3] > 0.3 and (_page_no(page) or 0) > 1:
        h, l, s = _hls(bg)
        if l > 0.85 and sum((a - b) ** 2 for a, b in zip(bg[:3], want[:3])) ** 0.5 > 12:
            msgs.append(f"内容页底色 {m.group(1)} 和本 deck palette 的底色 rgb{tuple(want[:3])} 不一致（同一稿内容页只用一种底色）")
    bad = {}
    for c in _CSS_COL.findall(xml):
        rgb = _rgba(c)
        if not rgb or rgb[3] < 0.3:
            continue
        h, l, s = _hls(rgb)
        if s <= 0.2 or l <= 0.1 or l >= 0.93:
            continue   # greys, near-black, near-white tints: neutral
        deg = h * 360
        if any(min(abs(deg - x), 360 - abs(deg - x)) <= 18 for x in hues):
            continue   # the brand family (shades / tints of the palette's own hues)
        if any(sum((a - b) ** 2 for a, b in zip(rgb[:3], e[:3])) ** 0.5 <= 24 for e in exact):
            continue   # an exact palette colour (good / bad / series)
        key = "rgb(%d,%d,%d)" % rgb[:3]
        bad[key] = bad.get(key, 0) + 1
    if bad:
        top = sorted(bad, key=bad.get, reverse=True)[:3]
        msgs.append(f"页面用了 palette 外的颜色 {top}")
    return "；".join(msgs)


CARD_LIMIT = 4
_SHAPE_BLOCK = re.compile(r"<shape\b([^>]*)>(.*?)</shape>", re.S)


TEXT_BLOCK_LIMIT = 3     # filled blocks carrying text (own text or a text box laid on top) that read as cards / panels
LIGHT_PANEL_LIMIT, LIGHT_PANEL_L = 2, 0.85   # ≥ 2 pale tint panels carrying text on one page
DARK_FILL_SHARE = 0.25   # a dark fill covering more than this share of a non-cover page
DARK_PANEL_SHARE = 0.05  # a dark text-carrying panel (side rail / KPI box) at least this share of the page
DECK_SKELETON_TIP = ("改用 business-deck.md「非图表页骨架」：KPI 行 = 大数字 + 1px 竖线分组（片段 A），流程 = 节点骑线"
                     "（片段 B），图 + 结论 = 右栏 1px 左竖线 + 小标题 + bullet，归因 / 诊断 = 编号列表 + 1px 横线；不加底色")
DARK_FILL_TIP = ("页面底色保持白色：章节页用大号 main_text 编号 + 左侧 brand 竖条，结论写进标题或用 1px 左竖线 + 文字，"
                 "结尾页同样白底")


def _style_is(kind, cwd, deck):
    """_frame.is_research / is_speech ("research" / "speech") of the deck; False when the check itself fails."""
    try:
        from ..exhibit import _frame
        return bool(getattr(_frame, f"is_{kind}")(cwd, deck))
    except Exception:  # noqa: BLE001
        return False


def _deck_on(cwd, deck, profile=None):
    """business-deck checks run for publish_slide(profile='deck') or a set_profile("deck") (speech) deck."""
    return profile == "deck" or _style_is("speech", cwd, deck)


def _business(cwd, deck, profile=None):
    """business-research / business-deck / business-keynote deck: the checks added for these styles only."""
    return bool(deck) and (profile == "keynote" or _deck_on(cwd, deck, profile) or _deck_style(cwd, deck) == "keynote"
                           or _style_is("research", cwd, deck))


def _num(attrs, name):
    m = re.search(rf'\b{name}="(-?[\d.]+)"', attrs)
    try:
        return float(m.group(1)) if m else None
    except ValueError:
        return None


def _dark_table_header(xml):
    """Fill colour of the first <tr> of a <table> when one of its cells is a dark solid fill, else ""."""
    for table in re.findall(r"<table\b.*?</table>", xml, re.S):
        tr = re.search(r"<tr\b.*?</tr>", table, re.S)
        for td in re.findall(r"<td\b.*?</td>", tr.group(0) if tr else "", re.S):
            m = re.search(r'<fill>\s*<fillColor color="([^"]+)"', td)
            rgb = _rgba(m.group(1)) if m else None
            if rgb and rgb[3] > 0.6 and _hls(rgb)[1] < 0.45:
                return m.group(1)
    return ""


def _missing_note(xml, cwd, deck, profile=None):
    """business-deck: every page carries 3–5 spoken sentences in <note> (SKILL Step 7); "" when present."""
    if not _deck_on(cwd, deck, profile):
        return ""
    m = re.search(r"<note\b.*?</note>", xml, re.S)
    if m and re.sub(r"<[^>]+>", "", m.group(0)).strip():
        return ""
    return "本页没有 <note> 讲稿：在 </data> 后补 <note><content><p>3–5 句可照读的讲稿</p></content></note>，同一页重提"


RESEARCH_CARD_FIX = ("研究稿正文不用手画底色卡片（米色/浅色/描边卡 + 大数字 + 小字）——同样的内容改成：(a) text_table / row_table（首列论点、"
                     "中列关键数字、右列证据与含义，一行一条），或 (b) 一张图 + key_takeaways 要点栏，或 (c) 分栏只用顶部细线 + 编号粗体标题 + "
                     "灰色正文、不加底色；只拦这一次，确实要保留就原样再提交")


LIB_CARDS = [False]   # Frame.publish sets this when the page body comes from a library card layout (SWOT, contents…)


def _research_cards(xml, cwd, deck, generated_text=""):
    """business-research decks: ≥ 3 hand-drawn panels side by side — filled (non-white) or outlined rectangles each
    carrying text — the PPT-template card row (beige cards + a big number + small caption). Library output
    (exhibit fragments, key_takeaways, contents / SWOT) is excluded by the caller. "" when fine."""
    if not _style_is("research", cwd, deck):
        return ""
    shapes, texts = [], []
    for attrs, body in _SHAPE_BLOCK.findall(xml):
        x, y, w, h = (_num(attrs, k) for k in ("topLeftX", "topLeftY", "width", "height"))
        if None in (x, y, w, h):
            continue
        t = (re.search(r'\btype="([^"]+)"', attrs) or [None, ""])[1]
        txt = re.sub(r"<[^>]+>", "", body).strip()
        if t == "text":
            if txt:
                texts.append((x, y, w, h))
            continue
        fill = re.search(r'<fillColor color="([^"]+)"', body)
        rgb = _rgba(fill.group(1)) if fill else None
        border = re.search(r'<border\b[^>]*\bcolor="([^"]+)"', body)
        filled = bool(rgb and rgb[3] > 0.3 and min(rgb[:3]) < 250)
        if (filled or border) and 120 <= w <= 480 and h >= 150:
            shapes.append((x, y, w, h))
    cards = [b for b in shapes if sum(1 for tx, ty, tw, th in texts
                                      if b[0] - 4 <= tx and tx + tw <= b[0] + b[2] + 4 and b[1] - 4 <= ty
                                      and ty + th <= b[1] + b[3] + 8) >= 2]
    rows = {}
    for b in cards:
        rows.setdefault(round(b[1] / 20), []).append(b)
    best = max((len(v) for v in rows.values()), default=0)
    return f"本页 {best} 张并排的手画底色/描边卡片" if best >= 3 else ""


def _card_grid(xml, cwd, deck, page=None, profile=None):
    """business-deck decks, warning only (never blocks). Flags the three things the deck doc bans but models keep
    drawing: ≥ CARD_LIMIT filled rounded rectangles (card grid), ≥ TEXT_BLOCK_LIMIT filled shapes carrying text (KPI
    cards, black takeaway panels, 2×2 boxes — text inside the shape or a text box laid on it), and on non-cover pages a
    dark fill (page background or one shape) covering > DARK_FILL_SHARE of the page. "" when fine."""
    if not _deck_on(cwd, deck, profile):
        return ""
    W, H = 960.0, 540.0
    shapes = []
    for attrs, body in _SHAPE_BLOCK.findall(xml):
        t = re.search(r'\btype="([^"]+)"', attrs)
        t = t.group(1) if t else ""
        x, y, w, h = (_num(attrs, k) for k in ("topLeftX", "topLeftY", "width", "height"))
        if None in (x, y, w, h):
            continue
        has_text = bool(re.sub(r"<[^>]+>", "", body).strip())
        if t == "text":
            shapes.append({"text_box": (x, y, w, h)} if has_text else {})
            continue
        r = _num(attrs, "presetHandlers")
        fill = re.search(r'<fillColor color="([^"]+)"', body)
        rgb = _rgba(fill.group(1)) if fill else None
        border = re.search(r'<border\b([^>]*)>', body)
        brgb = _rgba((re.search(r'\bcolor="([^"]+)"', border.group(1)) or [None, ""])[1]) if border else None
        stroked = bool(brgb and brgb[3] > 0.3 and (_num(border.group(1), "width") or 1) > 0
                       and t in ("rect", "round-rect", "slides-full-round-rect"))
        shapes.append({"type": t, "box": (x, y, w, h), "rgb": rgb, "text": has_text, "stroked": stroked,
                       "rounded": (t in ("round-rect", "slides-full-round-rect") and r != 0) or (t == "rect" and (r or 0) > 0)})
    texts = [s["text_box"] for s in shapes if "text_box" in s]

    def sized(s):
        return s["box"][2] >= 60 and s["box"][3] >= 30 and s["box"][2] * s["box"][3] < 0.6 * W * H

    filled = [s for s in shapes if s.get("rgb") and s["rgb"][3] > 0.3 and min(s["rgb"][:3]) < 250
              and s["box"][2] >= 60 and s["box"][3] >= 30]
    msgs = []
    cards = [s for s in filled if s["rounded"] and s["box"][3] >= 40]
    if len(cards) >= CARD_LIMIT:
        msgs.append(f"本页 {len(cards)} 个实心圆角矩形（卡片网格）")

    def inside(s, tb, pad=4):
        bx, by, bw, bh = s["box"]
        tx, ty, tw, th = tb
        return bx - pad <= tx and by - pad <= ty and tx + tw <= bx + bw + pad and ty + th <= by + bh + pad

    def carries_text(s):
        if s["text"]:
            return True
        bx, by, bw, bh = s["box"]
        return any(bx <= tx + tw / 2 <= bx + bw and by <= ty + th / 2 <= by + bh or inside(s, (tx, ty, tw, th))
                   for tx, ty, tw, th in texts)

    blocks = [s for s in filled if sized(s) and carries_text(s)]
    # white / unfilled rects with a visible border and a text box laid inside: outlined cards drawn as rect + text
    framed = [s for s in shapes if s.get("stroked") and s not in filled and sized(s)
              and (s["text"] or any(inside(s, tb) for tb in texts))]
    pale = [s for s in blocks if _hls(s["rgb"])[1] >= LIGHT_PANEL_L]   # light / light2 tint panels under text
    if len(blocks) >= TEXT_BLOCK_LIMIT and len(cards) < CARD_LIMIT:
        msgs.append(f"本页 {len(blocks)} 个带文字的实心底块（KPI 卡 / 要点栏 / 卡片列表）")
    elif len(blocks) + len(framed) >= TEXT_BLOCK_LIMIT and len(cards) < CARD_LIMIT:
        msgs.append(f"本页 {len(blocks) + len(framed)} 个文字叠在填充 / 描边矩形上的卡片（描边卡 / 底块卡）")
    elif len(pale) >= LIGHT_PANEL_LIMIT and len(cards) < CARD_LIMIT:
        msgs.append(f"本页 {len(pale)} 块浅色底（light / light2 面板、结论条）上叠文字：分组靠留白和细线，不靠底色——"
                    "结论条改成 1px 左竖线 + 粗体一句，面板去底色留小标题 + 细线")
    if msgs:
        msgs[-1] += f"：{DECK_SKELETON_TIP}"
    head = _dark_table_header(xml)
    if head:
        msgs.append(f"表头 {head} 是深色实心填充：表头用 light2 底 + 粗体 ink，行间 grey_light 细线")
    dark_page = False
    if (_page_no(page) or 0) != 1:
        dark = []
        m = re.search(r"<style>\s*<fill[^>]*>\s*<fillColor color=\"([^\"]+)\"", xml)
        bg = _rgba(m.group(1)) if m else None
        if bg and bg[3] > 0.6 and _hls(bg)[1] < 0.3:
            dark.append(("页面底色", m.group(1), 1.0))
        for s in shapes:
            rgb = s.get("rgb")
            if not rgb or rgb[3] <= 0.6 or _hls(rgb)[1] >= 0.3:
                continue
            x, y, w, h = s["box"]
            area = max(0.0, min(x + w, W) - max(x, 0.0)) * max(0.0, min(y + h, H) - max(y, 0.0))
            if area > DARK_FILL_SHARE * W * H:
                dark.append(("深色块", "rgb(%d,%d,%d)" % rgb[:3], area / (W * H)))
        if dark:
            what, col, share = max(dark, key=lambda d: d[2])
            msgs.append(f"非封面页{what} {col} 占页面 {share:.0%}（深色章节页 / 黑色结论栏 / 深色结尾）：{DARK_FILL_TIP}")
            dark_page = share >= 0.6
        else:   # a smaller dark side panel / KPI box (deep colour as fill): below the page-share rule, still banned
            panels = [s for s in shapes if s.get("rgb") and s["rgb"][3] > 0.6 and _hls(s["rgb"])[1] < 0.3
                      and s["box"][2] * s["box"][3] >= DARK_PANEL_SHARE * W * H and s["box"][3] >= 100
                      and carries_text(s)]
            if panels:
                col = "rgb(%d,%d,%d)" % panels[0]["rgb"][:3]
                msgs.append(f"深色面板 {col}（{len(panels)} 处，深色 / deep 做了侧栏或 KPI 底）：deep 只给图形数据，不做填充；"
                            "侧栏改成 1px 左竖线 + 小标题 + bullet，KPI 改成片段 A")
    if not msgs:
        return ""
    if dark_page:   # a one-attribute fix: "本页可保留" would keep the dark page
        return "；".join(msgs) + "（只提醒不拦截；这页把底色 / 深色大块改成白色即可，改动很小，建议改完重提这一页）"
    return "；".join(msgs) + "（只提醒不拦截，下一页起照骨架写；本页可保留）"


_LINE_TAG = re.compile(r"<line\b([^>]*)>")
_CHART_BLOCK = re.compile(r"<chart\b([^>]*)>(.*?)</chart>", re.S)


def _floats(text):
    out = []
    for v in (text or "").split(","):
        try:
            out.append(float(v.strip().replace("%", "")))
        except ValueError:
            out.append(None)
    return out


_REAL_PCT = re.compile(r"""(format=)(["'])([#0,]*0(?:\.0+)?)(?:%|'%')\2""")   # formats the server renders ×100


def _chart_pct_ratios(xml):
    r"""Native <chart> series of percentage points (1.74 for 1.74%) under a format the server renders ×100 ("0%",
    "0.00%", "0'%'", "0.00'%'" — a quoted '%' is not literal there) show as 174%. When the page text states the
    series' values as "v%" (≥ 2 of them, or the only one) and never ×100, those formats become the literal "0\%" /
    "0.00\%" (decimals kept); values are not touched. Ratios (0.68 or 1.08 with "0%") are right as they are. Values > 1
    under such a format without that evidence only get a note. Returns (xml, notes)."""
    words = re.sub(r"<[^>]+>", " ", _CHART_BLOCK.sub(" ", xml))
    shown = {round(float(v), 6) for v in re.findall(r"(-?\d+(?:\.\d+)?)\s*%", words)}
    notes = []
    lit = lambda mm: f"{mm.group(1)}{mm.group(2)}{mm.group(3)}\\%{mm.group(2)}"  # noqa: E731

    def fix(m):
        attrs, body = m.group(1), m.group(2)
        dim2 = re.search(r"<dim2>(.*?)</dim2>", body, re.S)
        if not dim2 or not _REAL_PCT.search(body):
            return m.group(0)
        fields = list(re.finditer(r"(<chartField\b[^>]*>)([^<]*)", dim2.group(1)))
        right = [int(i) for i, side in re.findall(
            r'<chartSeries\b[^>]*?\bindex="(\d+)"[^>]*?\byAxisPosition="(\w+)"', body) if side == "right"]
        r_axis = re.search(r'<chartAxis\b[^>]*position="right"[^>]*>(.*?)</chartAxis>', body, re.S)
        edits, names = [], []
        for k, f in enumerate(fields, start=1):
            vals = {round(v, 6) for v in _floats(f.group(2)) if v}
            nm = (re.search(r'name="([^"]*)"', f.group(1)) or [None, f"系列{k}"])[1]
            if not vals:
                continue
            ser = re.search(rf'<chartSeries\b[^>]*?\bindex="{k}"[^>]*?(?:/>|>(.*?)</chartSeries>)', body, re.S)
            spans = [(ser.start(1), ser.end(1))] if ser and ser.group(1) else []
            if r_axis and right == [k]:
                spans.append((r_axis.start(1), r_axis.end(1)))
            if len(fields) == 1:   # every format of a one-series chart is that series' format
                spans = [(0, dim2.start())]
            spans = [sp for sp in spans if _REAL_PCT.search(body[sp[0]:sp[1]])]
            if not spans:
                continue
            hits = vals & shown
            if len(hits) >= min(2, len(vals)) and not any(round(v * 100, 6) in shown for v in vals):
                names.append(nm)
                edits += [(a, b, _REAL_PCT.sub(lit, body[a:b])) for a, b in spans]
            elif max(abs(v) for v in vals) > 1 and not any(round(v * 100, 6) in shown for v in vals):
                notes.append(f"chart_pct：原生图系列「{nm}」值 >1 配了会 ×100 的百分比格式（0% / 0'%'）：本来就是百分点（1.8 = 1.8%）"
                             "就把格式改成字面 0.0\\%；是比率（1.08 = 108%）不用改（只提醒不拦截）")
        if not edits:
            return m.group(0)
        out, pos = [], 0
        for s0, e0, new in sorted(set(edits)):
            if s0 < pos:
                continue
            out.append(body[pos:s0] + new)
            pos = e0
        out.append(body[pos:])
        notes.append(f"chart_pct：原生图「{'、'.join(names)}」存的是百分点（页上写着 v%），格式 0% / 0'%' 会再 ×100："
                     "已改成字面 0\\% / 0.00\\%，数值不变；本地 XML 同步这样改即可")
        return f"<chart{attrs}>{''.join(out)}</chart>"

    return _CHART_BLOCK.sub(fix, xml), notes


def _chart_info(attrs, body):
    """Native <chart> facts for the deck checks: plot type, box, categories, series [(name, values)], explicit y-axis
    ranges {position: (min, max)}, series index → y-axis side, whether a legend is written."""
    plot = re.search(r'<chartPlot\b[^>]*\btype="([^"]+)"', body)
    dim1 = re.search(r"<dim1>\s*<chartField\b[^>]*>(.*?)</chartField>", body, re.S)
    dim2 = re.search(r"<dim2>(.*?)</dim2>", body, re.S)
    series = [((re.search(r'name="([^"]*)"', a) or [None, ""])[1], _floats(v))
              for a, v in re.findall(r"<chartField\b([^>]*)>(.*?)</chartField>", dim2.group(1) if dim2 else "", re.S)]
    axes = {}
    for a in re.findall(r'<chartAxis\b([^>]*\btype="y"[^>]*)>', body):
        axes[(re.search(r'\bposition="([^"]+)"', a) or [None, "left"])[1]] = (_num(a, "min"), _num(a, "max"))
    sides = {int(i): s for i, s in re.findall(r'<chartSeries\b[^>]*?\bindex="(\d+)"[^>]*?\byAxisPosition="(\w+)"', body)}
    return {"type": plot.group(1) if plot else "", "box": tuple(_num(attrs, k) for k in
                                                                ("topLeftX", "topLeftY", "width", "height")),
            "series": series, "axes": axes, "sides": sides, "legend": "<chartLegend" in body,
            "cats": [c.strip() for c in (dim1.group(1) if dim1 else "").split(",") if c.strip()]}


def _combo_same_axes(xml, cwd, deck, profile=None):
    """business-deck, warning only: a combo chart with a right y axis whose two axes carry the same explicit min / max
    (a second axis that says nothing). "" otherwise."""
    if not _deck_on(cwd, deck, profile):
        return ""
    for attrs, body in _CHART_BLOCK.findall(xml):
        info = _chart_info(attrs, body)
        left, right = info["axes"].get("left"), info["axes"].get("right")
        if info["type"] == "combo" and left and right and None not in left and left == right:
            return (f"组合图左右两轴刻度相同（{left[0]:g}–{left[1]:g}）：去掉右轴（删 yAxisPosition=\"right\" 和右侧 <chartAxis>），"
                    "系列共用左轴；基期不同的指数不放同一轴，改成同一基期或拆两张小图（只提醒不拦截）")
    return ""


def _chart_axis_ranges(xml, cwd, deck, profile=None):
    """business-deck, warning only: a bar / column chart whose value axis starts above 0 (truncated bars exaggerate the
    change), or a line chart whose data span covers < LINE_SPAN_MIN of its explicit axis range (the line is flattened).
    "" otherwise."""
    if not _deck_on(cwd, deck, profile):
        return ""
    out = []
    for attrs, body in _CHART_BLOCK.findall(xml):
        info = _chart_info(attrs, body)
        kinds = set(re.findall(r'<chartPlot\b[^>]*\btype="([^"]+)"', body))
        vals = [v for _, vs in info["series"] for v in vs if v is not None]
        lo, hi = info["axes"].get("left") or (None, None)
        if kinds & {"bar", "column"} and lo is not None and lo > 0:
            out.append(f"柱 / 条图数值轴从 {lo:g} 起（截断轴，柱长比例被放大）：删掉 min 或写 min=\"0\"；要看小幅变化改用折线或在标签里写变化值")
        if "line" in kinds and vals and len(vals) >= 2:
            a = lo if lo is not None else min(0.0, min(vals))
            b = hi if hi is not None else None
            if b is not None and b > a and (max(vals) - min(vals)) < LINE_SPAN_MIN * (b - a):
                out.append(f"折线数据 {min(vals):g}–{max(vals):g} 只占轴 {a:g}–{b:g} 的 "
                           f"{(max(vals) - min(vals)) / (b - a):.0%}（线被压平）：把 y 轴 min / max 收窄到数据上下各留约一格的整数")
            elif b is None and lo is None and min(vals) > 0 and (max(vals) - min(vals)) < LINE_SPAN_MIN * max(vals):
                out.append(f"折线数据 {min(vals):g}–{max(vals):g} 没写轴范围，默认从 0 起会被压平：<chartAxis type=\"y\"> 写整数 "
                           "min / max 收窄到数据范围")
    return "；".join(dict.fromkeys(out)) + "（只提醒不拦截）" if out else ""


LINE_SPAN_MIN = 0.10


DECK_MONOTONY_RUN = 4


def _text_skeleton(xml):
    """Coarse signature of a chart-free, image-free page built from text + thin rules: (thin vertical bars / rules,
    text columns). None for pages carrying a chart / image / table / embed or with no thin rule — those vary anyway."""
    if re.search(r"<(?:chart|img|table|embed)\b", xml):
        return None
    vbars, cols = 0, set()
    for attrs, body in _SHAPE_BLOCK.findall(xml):
        x, y, w, h = (_num(attrs, k) for k in ("topLeftX", "topLeftY", "width", "height"))
        if None in (x, y, w, h):
            continue
        if w <= 6 and h >= 24:
            vbars += 1
        elif 'type="text"' in attrs and re.sub(r"<[^>]+>", "", body).strip() and y >= 90 and w >= 80:
            cols.add(round(x / 40))
    for attrs in _LINE_TAG.findall(xml):
        p = [_num(attrs, k) for k in ("startX", "startY", "endX", "endY")]
        if None not in p and abs(p[0] - p[2]) <= 2 and abs(p[1] - p[3]) >= 24:
            vbars += 1
    if not vbars:
        return None
    return f"{min(vbars, 6)}v/{min(len(cols), 4)}c"


def _deck_monotony(xml, cwd, deck, page, profile=None):
    """business-deck, warning only: this page and the DECK_MONOTONY_RUN − 1 pages before it are all the same non-chart
    text skeleton (e.g. 4px bar + text, three columns + thin rules; .lark-slides/textskel-<deck>.json)."""
    n = _page_no(page)
    if n is None or not _deck_on(cwd, deck, profile):
        return ""
    sig = _text_skeleton(xml)
    f = Path(cwd or ".") / ".lark-slides" / f"textskel-{deck}.json"
    try:
        led = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        led = {}
    led[f"p{n:02d}"] = sig
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(led), encoding="utf-8")
    except OSError:
        pass
    run = [led.get(f"p{k:02d}") for k in range(n - DECK_MONOTONY_RUN + 1, n + 1)]
    if sig is None or n < DECK_MONOTONY_RUN or any(s != sig for s in run):
        return ""
    return (f"P{n - DECK_MONOTONY_RUN + 1}–P{n} 连续 {DECK_MONOTONY_RUN} 页都是同一种「竖条 / 细线 + 文字栏」骨架：下一页换结构图"
            "（前后流程对照 + 驱动落点、括线归组 / 量级标签、节点流程、数据图），见 business-deck.md 非图表页骨架（只提醒不拦截）")


STYLE_FILE = "style"   # .lark-slides/decks/<deck>/style: "keynote" (written by upload_images.py)
KEYNOTE_FIX = "按 message 删字 / 放大图片 / 换构图（business-keynote.md 设计系统模板），不缩字号，改完重提同一页"
KEYNOTE_REUSED_FIX = ("同一张图不在多页当主图：换这个主体的另一张图，或用 image_edit 以它为参考生成不同角度 / 使用场景，"
                      "或用 <crop> 取局部特写")


def _deck_style(cwd, deck):
    """The deck's style marker. A "keynote" marker is ignored in a business-research multi-agent task (a strategy SYNC
    dir of this deck): upload_images.py may have written it while a builder uploaded a picture."""
    try:
        style = (deck_dir(cwd, deck) / STYLE_FILE).read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    if style == "keynote":
        try:
            if any(d.parents[1].name == "strategy" or _status(d).get("task_flow") == "strategy"
                   for d in _task_sync_dirs(cwd, deck)):
                return ""
        except Exception:  # noqa: BLE001
            pass
    return style


def _hero_key(cwd, deck, page, slide_id):
    """Ledger key of a page: pNN when page= is given, else the page its slide_id is registered under, else the id."""
    if page is not None and _page_no(page) is not None:
        return _page_key(page)
    if slide_id:
        _, reg = _page_registry(cwd, deck)
        return next((k for k, v in reg.items() if v == slide_id), slide_id)
    return None


def _hero_ledger(cwd, deck, key=None, token=None):
    """.lark-slides/decks/<deck>/hero-images.json {page key: main image token}; with key: store (token None clears)."""
    f = deck_dir(cwd, deck) / "hero-images.json"
    try:
        led = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        led = {}
    if key:
        if token:
            led[key] = token
        else:
            led.pop(key, None)
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(led, ensure_ascii=False), encoding="utf-8")
    return led


def _unused_uploads_note(cwd, deck, page=None):
    """Hint tail for keynote_number_without_image: tokens upload_images.py registered (logos excluded) that no other
    written page uses (keynote-shape.json "srcs"), and "keep the number, add a picture"."""
    up = _uploaded_tokens(cwd, deck) or set()
    up -= _uploaded_tokens(cwd, deck, logos=True) or set()
    try:
        led = json.loads((deck_dir(cwd, deck) / "keynote-shape.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        led = {}
    me = f"p{_page_no(page):02d}" if page is not None and _page_no(page) is not None else None
    used = {s for k, v in led.items() if k != me and isinstance(v, dict) for s in v.get("srcs") or []}
    free = sorted(up - used)
    head = "。保留数字、补图，不要改成金句页（数字是证据）"
    return head + (f"；已上传还没用过的图：{', '.join(free[:6])}" if free else "；没有未用的已上传图时先 upload_images.py 补一张")


def _uploaded_tokens(cwd, deck, logos=False):
    """file_tokens upload_images.py registered for this deck (.lark-slides/decks/<deck>/uploads.json), or None when it
    never ran here (no ledger: the image source check is skipped). ``logos``: only those uploaded with --logo."""
    try:
        led = json.loads((deck_dir(cwd, deck) / "uploads.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(led, dict):
        return None
    return {t for t, v in led.items() if isinstance(v, dict) and v.get("logo")} if logos else set(led)


def _keynote_total(cwd, deck):
    """Planned page count: plan.py PAGES of this task's SYNC dir, else page-plan.md rows, else None."""
    for f in list(Path(cwd).glob(".lark-slides/*/*/sync/plan.py"))[:3] + [Path(cwd) / "page-plan.md"]:
        try:
            text = f.read_text(encoding="utf-8")
        except OSError:
            continue
        n = len(re.findall(r"dict\(\s*p\s*=", text)) if f.suffix == ".py" else len(
            re.findall(r"^\s*\|\s*\**P\d+", text, re.M))
        if n:
            return n
    return None


def _keynote_checks(xml, cwd, deck, page, slide_id, page_type=None, total=None):
    """(errors, warnings, main image token) of xml_lint --profile keynote plus the deck-level reused-main-image check."""
    import sys

    scripts = str(Path(__file__).resolve().parents[2])
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    import _exhibit_xml_lint as xml_lint

    n = _page_no(page) if page is not None else None
    res = xml_lint.lint_xml(xml, profile="keynote", keynote_cover=n == 1 if n is not None else None,
                            keynote_page=n, keynote_total=total or _keynote_total(cwd, deck),
                            keynote_page_type=page_type, keynote_uploaded=_uploaded_tokens(cwd, deck),
                            keynote_logos=_uploaded_tokens(cwd, deck, logos=True))
    errs, warns = [], []
    for sl in res.get("slides") or []:
        for i in sl.get("issues") or []:
            if not str(i.get("code", "")).startswith("keynote_"):
                continue
            if i.get("level") == "error":
                fix = i.get("hint") or KEYNOTE_FIX
                if i["code"] == "keynote_number_without_image":
                    fix += _unused_uploads_note(cwd, deck, page)
                errs.append({"key": i["code"], "code": i["code"], "message": i.get("message", ""), "fix": fix})
            elif i.get("level") == "warning":
                warns.append(f"{i['code']}：{i.get('message', '')}")
    hero = None
    try:
        w, h = 960, 540
        imgs = [(e, src) for e in xml_lint.lint_slide(xml, 1, w, h)["elements"] if e["kind"] == "img"
                and (src := re.search(r'\bsrc="([^"]+)"', xml[e.get("_source_offset", 0):].split(">", 1)[0]))
                and not xml_lint.keynote_is_logo(e, w * h, h)]
        if imgs:
            big, src = max(imgs, key=lambda t: xml_lint.element_area(t[0]))
            if xml_lint.element_area(big) / (w * h) >= 0.15:   # a real main picture, not a small inset
                hero = src.group(1)
    except Exception:  # noqa: BLE001 — the reuse check is best effort
        hero = None
    if hero:
        me = _hero_key(cwd, deck, page, slide_id)
        others = sorted(k for k, v in _hero_ledger(cwd, deck).items() if v == hero and k != me)
        if others:
            errs.append({"key": "keynote_image_reused", "code": "keynote_image_reused",
                         "message": f"主图 {hero} 已是 {', '.join(others)} 的主图", "fix": KEYNOTE_REUSED_FIX})
    return errs, warns, hero


KEYNOTE_SPLIT_RUN, KEYNOTE_BARE_RUN, KEYNOTE_TEXT_SHARE = 3, 2, 0.25
KEYNOTE_RHYTHM_FIX = "下一页换一种骨架：满版出血图压一句大字 / 巨字大数字（配对比基准）/ 特性标签页 / 前后对比页（仅提醒，不拦）"


def _keynote_shape(xml):
    """{"split": "L"/"R"/None, "img": bool} of a keynote page: split = the main picture fills one half (≤ 65% of the
    width) and every body text box sits on the other half (the left-text / right-picture skeleton, either way round);
    img = any picture ≥ 3% of the canvas (logos and icons do not count)."""
    try:
        kids = _children(xml)
    except ET.ParseError:
        return None
    pics, texts = [], []
    for el in kids:
        tag = el.tag.split("}")[-1]
        try:
            x, y, w, h = (float(el.get(k) or 0) for k in ("topLeftX", "topLeftY", "width", "height"))
        except ValueError:
            continue
        pic = tag == "img" or any(isinstance(c.tag, str) and c.tag.split("}")[-1] == "fillImg" for c in el.iter())
        if pic and w * h >= 0.03 * 960 * 540:
            pics.append((x, w, w * h))
        elif tag == "shape" and "".join(el.itertext()).strip():
            texts.append(x + w / 2)
    split = None
    if pics and texts:
        x, w, _ = max(pics, key=lambda t: t[2])
        side = "L" if x + w / 2 < 480 else "R"
        if w <= 0.65 * 960 and all((c >= 480) == (side == "L") for c in texts):
            split = side
    return {"split": split, "img": bool(pics)}


def _keynote_rhythm(cwd, deck, page, xml):
    """Record this page in .lark-slides/decks/<deck>/keynote-shape.json and return soft warnings (page order): ≥3
    consecutive left/right split pages, ≥2 consecutive pages without a picture, or text-only pages > 25% so far."""
    n = _page_no(page)
    shape = _keynote_shape(xml)
    if n is None or shape is None:
        return []
    f = deck_dir(cwd, deck) / "keynote-shape.json"
    try:
        led = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        led = {}
    titles = _title_texts(xml)
    if titles:
        shape = dict(shape, titles=titles)
    words = _visible_text(xml)[:300]   # captions too: a big-number page's title is only "$8M"
    if words:
        shape = dict(shape, text=words)
    led[f"p{n:02d}"] = shape
    srcs = sorted(set(re.findall(r'<img\b[^>]*?\bsrc="([^"]+)"', xml)))
    if srcs:
        led[f"p{n:02d}"]["srcs"] = srcs
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(led, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass
    nums = sorted(int(k[1:]) for k in led if re.fullmatch(r"p\d+", k))

    def run(pred):   # length of the consecutive run (no page-number gaps) through page n satisfying pred
        if not pred(led[f"p{n:02d}"]):
            return 0
        lo = hi = n
        while lo - 1 in nums and pred(led[f"p{lo - 1:02d}"]):
            lo -= 1
        while hi + 1 in nums and pred(led[f"p{hi + 1:02d}"]):
            hi += 1
        return hi - lo + 1, lo, hi

    out = []
    r = run(lambda v: bool(v.get("split")))
    if r and r[0] >= KEYNOTE_SPLIT_RUN:
        out.append(f"keynote_rhythm：P{r[1]}–P{r[2]} 连续 {r[0]} 页都是一半文字一半图的左右分栏，构图单一——{KEYNOTE_RHYTHM_FIX}")
    r = run(lambda v: not v.get("img"))
    bare = sum(1 for k in nums if not led[f"p{k:02d}"].get("img"))
    if r and r[0] >= KEYNOTE_BARE_RUN:
        out.append(f"keynote_rhythm：P{r[1]}–P{r[2]} 连续 {r[0]} 页没有图片，后半程变成纯文字尾巴——{KEYNOTE_RHYTHM_FIX}")
    elif not shape["img"] and len(nums) >= 4 and bare / len(nums) > KEYNOTE_TEXT_SHARE:
        out.append(f"keynote_rhythm：已写 {len(nums)} 页里 {bare} 页没有图片（>{KEYNOTE_TEXT_SHARE:.0%}）——{KEYNOTE_RHYTHM_FIX}")
    return out


def _title_texts(xml, min_pt=28):
    """Visible text of the page's title-size boxes (largest font ≥ min_pt, else the largest box), ≤ 60 chars each."""
    found = []
    for attrs, body in _SHAPE_BLOCK.findall(xml):
        if 'type="text"' not in attrs and "<p" not in body:
            continue
        text = " ".join(re.sub(r"<[^>]+>", " ", body).split())
        sizes = [float(v) for v in re.findall(r'\bfontSize="([\d.]+)"', body)]
        if text and sizes:
            found.append((max(sizes), text[:60]))
    big = [t for sz, t in found if sz >= min_pt] or [t for sz, t in sorted(found)[-1:]]
    return big[:3]


BP_ITEMS = (   # business-keynote.md §3 融资 BP must-haves → title keywords (Chinese + English pitch decks)
    ("痛点 / 方案", r"痛点|问题|难题|方案|解决|problem|pain|solution|solve|guess|waste"),
    ("产品", r"产品|平台|技术|功能|方案|product|platform|technology|features?|how it works|demo"),
    ("市场空间", r"市场|TAM|SAM|规模|空间|赛道|market|opportunity"),
    ("商业模式与收入", r"商业模式|收入|营收|盈利|变现|定价|收费|模式|business model|revenue|pricing|subscription|SaaS|monetiz"),
    ("牵引力", r"订单|客户|用户|增长|牵引|里程碑|交付|签约|合作|traction|customers?|users|pilot|growth|milestones?|"
              r"restaurants|partners"),
    ("竞争格局", r"竞争|竞品|对手|壁垒|格局|对比|优势|competition|competitors?|landscape|\bvs\.?\b|moat|lose to"),
    ("团队", r"团队|创始人|CEO|核心成员|合伙人|Founder|Team"),
    ("财务与预测", r"财务|预测|利润|现金流|毛利|营收预测|收入预测|盈亏|financials?|projections?|forecast|ARR|"
                 r"margin|break-?even|P&L"),
    ("融资额与用途", r"本轮|资金用途|募资|融资额|融资金额|融资计划|用途|估值|the ask|raising|use of funds|"
                  r"seed round|series [a-d]\b|valuation"),
)
_BP_MARK = re.compile(r"融资\s*BP|\bBP\b|商业计划书?|融资计划书?|融资路演|pitch\s*deck|investor\s*(?:deck|presentation)|"
                      r"fundrais\w*|seed\s*(?:round|stage)|pre-?seed|series\s*[a-d]\b|raising\s+(?:usd|us\$|\$)", re.I)
FRANCHISE_ITEMS = (   # business-keynote.md §3 企业宣传 / 招商 must-haves → title keywords
    ("品牌", r"品牌|使命|愿景|门店|规模|故事|我们是"),
    ("市场", r"市场|赛道|行业|需求|趋势|消费者|消费市场"),
    ("店型 / 产品", r"店型|门店模型|单店|多店|面积|选址|产品|菜单|爆品|空间"),
    ("投资与回本", r"投资|投入|费用|加盟费|回本|回收|回报|收益|万起|ROI"),
    ("合作条件", r"条件|资质|门槛|要求|资金|区域|合伙人画像|找.{0,4}人"),
    ("支持体系", r"支持|赋能|培训|陪跑|督导|供应链|运营|总部"),
    ("案例", r"案例|故事|加盟商|合伙人说|成功|样板"),
    ("流程与联系方式", r"流程|步骤|加入|联系|热线|电话|二维码|官网|咨询"),
)
_FRANCHISE_MARK = re.compile(r"招商|加盟|合伙人招募|事业合伙人|franchise", re.I)
_MUST_LISTS = (("融资 BP 必含 9 项", _BP_MARK, BP_ITEMS), ("招商必含 8 项", _FRANCHISE_MARK, FRANCHISE_ITEMS))


def _must_missing(cwd, deck):
    """(label, missing item names) for a keynote deck that is a fundraising BP or a franchise / 招商 deck (decks/<deck>/
    subtype, a plan / brief file in cwd, or the cover title says so): the must-have items not found in any written
    page title; ("", []) for other decks."""
    d = deck_dir(cwd, deck)
    led = {}
    try:
        led = json.loads((d / "keynote-shape.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    titles = [t for v in led.values() if isinstance(v, dict) for t in v.get("titles") or []]
    if not titles:
        return "", []
    marks = []
    for f in [d / "subtype", *sorted(Path(cwd).glob("*plan*.md")), *sorted(Path(cwd).glob("*brief*.md"))][:6]:
        try:
            marks.append(f.read_text(encoding="utf-8")[:4000])
        except OSError:
            pass
    p1 = led.get("p01") if isinstance(led.get("p01"), dict) else {}
    cover = " ".join(p1.get("titles") or []) + " " + (p1.get("text") or "")   # "Seed Round | 2026" under the name
    body = " ".join(" ".join(v.get("titles") or []) + " " + (v.get("text") or "")
                    for k, v in led.items() if k != "p01" and isinstance(v, dict))
    for label, mark, items in _MUST_LISTS:
        if any(mark.search(m) or m.strip() == ("bp" if items is BP_ITEMS else "franchise") for m in marks) \
                or mark.search(cover):
            return label, [name for name, pat in items if not re.search(pat, body, re.I)]
    return "", []


KEYNOTE_MIN_PAGES = 15   # business-keynote.md: 15–30 pages when the user gave no count


def _deck_summary_note(cwd, deck, total):
    """Last-page hint (keynote): page count vs the style's recommended minimum and the share of pages without a
    picture, from keynote-shape.json. "" when both are fine."""
    try:
        led = json.loads((deck_dir(cwd, deck) / "keynote-shape.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    pages = sorted(k for k, v in led.items() if re.fullmatch(r"p\d+", k) and isinstance(v, dict))
    if not pages:
        return ""
    bare = [f"P{int(k[1:])}" for k in pages if not led[k].get("img")]
    parts = []
    if int(total) < KEYNOTE_MIN_PAGES:
        parts.append(f"共 {total} 页，低于本风格推荐的 {KEYNOTE_MIN_PAGES}–30 页（用户指定页数时忽略）")
    if len(bare) / len(pages) > KEYNOTE_TEXT_SHARE:
        parts.append(f"无图页 {len(bare)}/{len(pages)}（{'、'.join(bare[:8])}），推荐 ≤{KEYNOTE_TEXT_SHARE:.0%}")
    if not parts:
        return ""
    return ("deck_summary：" + "；".join(parts) + "——缺内容就按骨架补页、无图页换已上传的图，补完再导出（只提示不拦）")


NO_TOTAL_MSG = "no_total：第 1 页没传 total=N——传 total=N 以便末页做缺项检查（只提示一次）"


KEYNOTE_HARD = {"keynote_image_unverified", "keynote_page_number"}   # always refused: broken display / page numbers
KEYNOTE_HOLD_NOTE = "第一次提示；如是用户明确要求或确需保留，原样重提同一页即可写入（降为 warning）"


def _keynote_hold(errs, cwd, presentation, page):
    """(errors still refusing the page, warnings): with page= given, a keynote error code is refused the first time it
    shows on this page (mark in <cwd>/.lark-slides/held-keynote-<code>-<presentation>.json) and only warned about on
    later submissions; KEYNOTE_HARD codes and calls without page= always refuse."""
    if page is None or _page_no(page) is None:
        return errs, []
    keep, warn = [], []
    for e in errs:
        if e["code"] in KEYNOTE_HARD:
            keep.append(e)
        elif _first_hold_mark(cwd, f"held-keynote-{e['code']}-{presentation}.json", page):
            keep.append(dict(e, held=True, fix=f"{e['fix']}（{KEYNOTE_HOLD_NOTE}）"))
        else:
            warn.append(f"{e['code']}（已提示过一次，按原样写入）：{e['message']}")
    return keep, warn


DOWNGRADE_AT = 2   # server lint blocks of one page before publish hands back the downgrade recipe
DOWNGRADE_HEAD = "这页已被服务端拦 {n} 次：不要再挪坐标，也不要查看 blocked-*.json / _publish.py——"
DOWNGRADE_FIX = DOWNGRADE_HEAD + "去掉报错的标签/说话框，或把这页改成 row_table + Text 列，一次写入"
DOWNGRADE_BY_CODE = {   # per error code: the one move that ends the loop (no table recipe where it does not apply)
    "text_color_contrast": "看一眼 preview：确实看得清就同一调用加 waive=[{key}] 写入；看不清就把文字改成白 / 近黑实色（不用渐变）",
    "image_covers_text": "看一眼 preview：文字确实没被图盖住就同一调用加 waive=[{key}] 写入；盖住了就把图和文字分到两侧，不缩字号",
    "text_may_overflow_shape": "删掉一半文字或把文字框加高 / 加宽一档，一次写入",
}
DOWNGRADE_DECK = {"text_overflows_container": "删掉文字的底框（用 1px 细线分组代替），一次写入"}   # deck style: no cards
DOWNGRADE_KEYNOTE = "删掉报错的那个文字元素（内容进 <note>），或换设计系统模板里的另一种构图，一次写入"


def _server_block_note(result, cwd, presentation, page, profile="auto"):
    """Count server lint blocks per page (<cwd>/.lark-slides/srvblk-<deck>.json; reset when the page gets through);
    from the 2nd block on, the first error's fix leads with DOWNGRADE_FIX (Frame.publish prints fix[:160])."""
    errs = result.get("errors") or []
    if not result.get("ok") and not (errs and all(e.get("code") != "upload_failed" for e in errs)):
        return 0
    f = Path(cwd or ".") / ".lark-slides" / f"srvblk-{presentation}.json"
    try:
        seen = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        seen = {}
    k = f"p{_page_no(page):02d}"
    if result.get("ok"):
        if seen.pop(k, None) is None:
            return 0
        n = 0
    else:
        n = seen[k] = seen.get(k, 0) + 1
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(seen), encoding="utf-8")
    if n >= DOWNGRADE_AT:
        first = errs[0] if errs else {}
        code = str(first.get("code") or "")
        by_code = {**DOWNGRADE_BY_CODE, **(DOWNGRADE_DECK if _deck_on(cwd, _deck_id(presentation), profile) else {})}
        if code in by_code:
            tip = DOWNGRADE_HEAD.format(n=n) + by_code[code].format(key=repr(first.get("key") or code))
        elif _deck_style(cwd, _deck_id(presentation)) == "keynote":
            tip = DOWNGRADE_HEAD.format(n=n) + DOWNGRADE_KEYNOTE
        else:
            tip = DOWNGRADE_FIX.format(n=n)
        errs[0]["fix"] = tip + "。" + str(errs[0].get("fix") or "")
        result["downgrade"] = tip
        result["summary"] = [tip] + list(result.get("summary") or [])
    return n


def _first_hold_mark(cwd, fname, page):
    """True the first time `page` is held for this check (mark in <cwd>/.lark-slides/<fname>); later calls False."""
    f = Path(cwd or ".") / ".lark-slides" / fname
    try:
        seen = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        seen = {}
    k = f"p{_page_no(page):02d}"
    if seen.get(k):
        return False
    seen[k] = 1
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(seen), encoding="utf-8")
    return True


def _touch_claim(cwd, page, who, written=False, deck=None):
    """publish_slide(who=…): keep the page's claim fresh (heartbeat) and, after a successful write, count it as
    written — the same bookkeeping Frame.publish does, for hand-written XML pages."""
    n = _page_no(page)
    if not who or n is None:
        return
    import fcntl

    for d in _task_sync_dirs(cwd, deck):
        cl = d / "claims.json"
        if not cl.exists():
            continue
        try:
            with open(d / "claims.lock", "w") as lk:
                fcntl.flock(lk, fcntl.LOCK_EX)
                allc = json.loads(cl.read_text(encoding="utf-8"))
                c = allc.get(f"p{n:02d}")
                if not isinstance(c, dict) or who not in (c.get("who"), c.get("reviewer")):
                    continue
                if c.get("state") in ("doing", "reviewing"):
                    c["t"] = time.time()
                if written:
                    c["written"] = c.get("written", 0) + 1
                cl.write_text(json.dumps(allc, ensure_ascii=False, indent=1), encoding="utf-8")
        except (OSError, ValueError):
            pass


REVOKED_FIX = ("立即停止这页的一切工作（不再改脚本、不再跑本地 lint、不再 publish 它；已写的脚本不用删），"
               "运行 next 领下一页")


def revoked_owner(cwd, page, who, deck=None):
    """The agent page N was handed over to after `who` went silent (claims.json: revoked_from=who), else None."""
    n = _page_no(page)
    if not who or n is None:
        return None
    for d in _task_sync_dirs(cwd, deck):
        try:
            c = json.loads((d / "claims.json").read_text(encoding="utf-8")).get(f"p{n:02d}")
        except (OSError, ValueError):
            continue
        if (isinstance(c, dict) and c.get("revoked_from") == who and c.get("who") not in (None, who)
                and c.get("reviewer") != who):
            return c.get("who")
    return None


def revoked_msg(page, who, owner):
    return (f"P{_page_no(page)} 未写入：这页已转交给 {owner}（你太久没有提交，claims.json 记为 revoked_from={who}）——"
            + REVOKED_FIX)


def _nolint_elements(page_xml, key):
    """A waive key ("code:id+slide[1]/data/shape[3]") → [[tokens of one element]]: each element as its data path
    ("shape[3]") and, when it carries one, its id ("#t1") — the stable handles finish matches read-back issues on."""
    parts = [p for p in str(key).split(":", 1)[-1].split("+") if p]
    try:
        kids = _children(page_xml) if page_xml else []
    except ET.ParseError:
        kids = []
    paths, seen = {}, {}
    for el in kids:
        tag = el.tag.split("}")[-1]
        seen[tag] = seen.get(tag, 0) + 1
        if el.get("id"):
            paths[el.get("id")] = f"{tag}[{seen[tag]}]"
    out = []
    for p in parts:
        tag, i = _element_index(p)
        if tag is not None:
            out.append([f"{tag}[{i}]"])
        else:
            out.append(sorted({f"#{p}"} | ({paths[p]} if p in paths else set())))
    return out


def _warned_ledger(cwd, deck, page, result):
    """.lark-slides/decks/<deck>/warned.json {pNN: [first words of each warning]}: pages whose last write carried
    warnings (or went out without lint) — export --who solo lists them for the final look. A clean rewrite clears it."""
    n = _page_no(page)
    if n is None or not deck:
        return
    f = deck_dir(cwd, deck) / "warned.json"
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        d = {}
    marks = [re.split(r"[：:（(]", str(w), 1)[0][:40] for w in result.get("warnings") or []]
    if result.get("no_lint"):
        marks.append("no_lint")
    k = f"p{n:02d}"
    if marks:
        d[k] = list(dict.fromkeys(marks))[:4]
    elif k in d:
        d.pop(k)
    else:
        return
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def _nolint_ledger(cwd, deck, page, result):
    """<cwd>/.lark-slides/nolint-<deck>.json {pNN: {"v": 2, "waived": [{code, els}], "noise": bool}}: pages whose last
    write went out without server lint after publish judged the findings. finish's read-back lint waives on that page
    only (a) the very issues the author waived (same code, same elements — `els` lists each element's data path / id)
    and (b) when noise is true, issues that the same conversion-noise rule (_classify) still drops on the read-back XML,
    or whose code is one publish already judged as noise on this page (`noise_codes`).
    Any other issue blocks. A later linted write clears the entry.
    Old ledgers ({pNN: [codes]}) are still read as whole-code waivers."""
    n = _page_no(page)
    if n is None or not deck:
        return
    f = Path(cwd or ".") / ".lark-slides" / f"nolint-{deck}.json"
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        d = {}
    k = f"p{n:02d}"
    rec = None
    if result.get("no_lint"):
        waived = [{"code": str(w).split(":", 1)[0], "els": _nolint_elements(result.get("page_xml"), w)}
                  for w in result.get("waived") or []]
        noise = bool(result.get("ignored"))
        if waived or noise:
            rec = {"v": 2, "waived": waived, "noise": noise}
            if noise and result.get("ignored_codes"):
                rec["noise_codes"] = list(result["ignored_codes"])
    if d.get(k) == rec:
        return
    if rec:
        d[k] = rec
    else:
        d.pop(k, None)
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(d), encoding="utf-8")
    except OSError:
        pass


_EMPTY_TEXT_SHAPE = re.compile(r'\s*<shape\b(?=[^>]*\btype="text")[^>]*>(?:(?!</shape>).)*?</shape>', re.S)


def _drop_empty_text_shapes(xml):
    """Text boxes with no text and no fill / border: the editor shows them as a "点击可添加正文" placeholder
    (invisible in screenshots), so they are removed."""
    def keep(m):
        s = m.group(0)
        if re.search(r"<fillColor|<border|<img|<field", s):
            return s
        txt = re.sub(r"<[^>]+>", "", s)
        return s if txt.replace("&nbsp;", "").strip() else ""
    return _EMPTY_TEXT_SHAPE.sub(keep, xml)


def publish_slide(
    page_xml,
    *fragments,
    presentation=None,
    slide_id=None,
    before_slide_id=None,
    page=None,
    screenshot=False,
    save_as=None,
    waive=(),
    cwd=None,
    who=None,
    layout=None,
    why=None,
    same_as_prev=None,
    note_who=None,
    profile="auto",
    page_type=None,
    total=None,
    insert=False,
):
    """Compose ``page_xml`` with generated ``fragments`` and (optionally) write it to a deck.

    Returns a dict:
      ``ok``          – page written (or composed, when no presentation is given)
      ``slide_id``    – written page id (``slide_id`` when updating)
      ``page_xml``    – the composed page XML
      ``screenshot``  – path of a screenshot of the written page ("" when skipped or blocked)
      ``preview``     – when blocked, a render of the XML for inspection ("" if unavailable)
      ``errors``      – lint findings the author must fix (empty when written)
      ``ignored``     – number of conversion-overlap findings that were waived
      ``no_lint``     – True when the page was re-sent without lint after waiving findings
      ``waived``      – keys of findings force-written because the author passed them in ``waive``
    ``slide_id`` replaces that page in place (+update-slide); otherwise a page is added
    (before ``before_slide_id`` when given). ``page=`` (e.g. 3 or "p03") makes re-running a page script
    idempotent: the first write records page→slide_id in .lark-slides/pages-<deck>.json, later calls with
    the same ``page`` update that slide in place, and a new page is inserted before the next higher
    recorded page so the deck order follows page numbers. ``save_as`` also writes the XML to that path.
    ``insert=True`` (with ``page=N``) inserts a NEW page N in front of the page now recorded as N: on success every
    recorded page ≥ N moves up one in the registry and in the per-page ledgers / saved XML (.lark-slides/*-<deck>.json,
    decks/<deck>/*.json, xml/<deck>/pNN.xml); ``renumbered`` lists the shifted pages whose printed page numbers /
    navigation need +1. In an edit turn (deck exported before — marker or a later .pptx in cwd — or a reopened multi-agent task) ``page=N`` without
    ``insert`` / ``slide_id`` whose title differs from the page recorded as N is held once (``page_overwrite``).
    ``waive`` lists ``errors[i]["key"]`` values judged to be false positives: when every remaining finding is
    waived the page is written without lint and always screenshotted for a visual check.
    Local blocks before any write (``errors[i]["key"]``): ``logo_missing`` (cwd has .lark-slides/logo.json and the page
    lacks that token or any registered variant; waivable), ``logo_cropped`` (logo <img> ratio off its original by >3%),
    ``cover_no_image`` (page 1 needs 50% exposed imagery, or 25% with title/supporting-text hierarchy; image unions
    exclude logos and account for alpha and rectangular masks; waivable). After finish exported the deck nothing is written;
    a page listed in SYNC/frozen.lock is refused (``frozen``) whatever status.json says; ``multi_page_command`` when the
    parent shell command writes several pages (two page scripts / write calls, or a for/while loop around them), or
    when this python process already wrote 3 other pages (at most 3 pages per process: ``pages.py 5 7 9`` works, a
    script that submits a whole deck does not).
    The same writer (``who``, else the parent shell) may write at most WINDOW_PAGES (3) distinct pages of a deck within
    WINDOW_S (60) seconds across processes of one parent shell (.lark-slides/rate-<deck>.json; slide_id rewrites
    count): chained ``python3 fix.py 5 6 7 && python3 fix.py 8 9 10`` is refused with ``multi_page_command``; quick
    one-page-per-tool-call writes (each its own shell) are not.
    An empty ``<field type="slidenum"/>`` (server 4001000) gets the page number (page=, or slide_id's registry entry)
    as its fallback text, datetime fields today's date; unknown page number → ``empty_field``.
    ``control_chars`` (not waivable): control characters in the text (\\x00-\\x1f raw or as &#N;, TAB inside text) —
    LaTeX such as "\\text" / "\\times" in a normal Python string; use r"..." or double backslashes.
    Every server write of a deck holds .lark-slides/pages-<deck>.lock; check the deck order with verify_order().
    ``placeholder_text`` (XX / 占位 / 待补 / TODO / example.com / 000-0000 / template 【…】 left in the text; waivable).
    ``fake_phone`` (400-000-0000 / 000-0000-0000 / all-zero mobile numbers; not waivable) and ``unformatted_code``
    (an unevaluated Python expression such as ``{(M_R1['x'] / …):+.1%}`` in the visible text; not waivable).
    A page whose body text is mostly < 10pt gets a "正文字号过小" entry in ``warnings``; with ``page=`` given it is
    held once instead (``tiny_text``, one-shot per page — the next submission goes through). Same one-shot hold with
    ``page=``: ``sample_label_overuse`` (body — notes and the footer band y ≥ 500 excluded — says "示例" more than
    twice; without page= only a warning) and ``same_skeleton`` (pages N−2, N−1 and N have the identical layout
    signature, .lark-slides/skeletons-<deck>.json).
    ``who`` (multi-agent: "main"/"lead"/…) keeps the page's claim fresh and marks it written, like Frame.publish.
    ``layout`` / ``why`` / ``same_as_prev``: only for page-writing subagents (``who`` not main / organizer / lead): a new
    page (page=N, no slide_id, not a reopened edit turn) needs a short layout description (≤20 chars) and why it meets
    the page's brief (≤50); a layout equal to a neighbouring page's is refused unless ``same_as_prev`` gives the reason
    (``layout_note_missing`` / ``layout_note_too_long`` / ``same_layout_as_neighbor``; .lark-slides/layouts-<deck>.json).
    ``note_who`` names the writer for this check only (Frame.publish keeps its own claim bookkeeping); default ``who``.
    ``profile="keynote"`` (default when upload_images.py marked the deck: .lark-slides/decks/<deck>/style; ``profile=None``
    turns it off) runs ``xml_lint --profile keynote`` before writing: with ``page=`` each keynote error code is refused
    the first time it shows on that page and only warned about when the page is resubmitted (``keynote_image_unverified``
    and ``keynote_page_number`` always refuse; without ``page=`` every keynote error refuses), plus ``keynote_image_reused``: the page's main picture is already the main picture of another page of the
    deck (.lark-slides/decks/<deck>/hero-images.json). ``page_type`` ("cover" / "reveal" / "number" / "ending") adds the
    page-type checks: a reveal page needs a product picture, a big-number page a picture proving it.
    ``profile="deck"`` (business-deck) adds warning-only design checks (card grid, ≥3 filled / outlined text blocks,
    a dark solid table header, a large dark fill on a non-cover page, a missing <note>) — the page is still written.
    """
    if who in ("main", "lead") and cwd:   # Main is still working: the Organizer must not take over P1–P3
        import time as _tmain
        for _d in _task_sync_dirs(cwd, None):
            try:
                (_d / "main_seen").write_text(str(_tmain.time()), encoding="utf-8")
            except OSError:
                pass
    notes = []
    bad = control_chars(page_xml, *fragments)
    if bad:   # before any parsing: a raw \x08 is not even well-formed XML
        err = _control_char_error(bad)
        return {"ok": False, "slide_id": slide_id or "", "page_xml": page_xml if isinstance(page_xml, str) else "",
                "screenshot": "", "preview": "", "errors": [err], "ignored": 0, "no_lint": False, "waived": [],
                "warnings": [], "summary": [f"未写入（本地检查）control_chars：{err['message']}——{err['fix']}"]}
    page_xml, pasted = _lift_pasted_fragments(_with_sml_namespace(page_xml))
    if pasted:
        notes.append(f"page_xml 里拼进了 {len(pasted)} 个生成片段，已按片段处理；下次{_PASTED_HINT}")
        fragments = (*pasted, *fragments)
    biz = bool(presentation) and _business(cwd or os.getcwd(), _deck_id(presentation), profile)
    page_xml, fit_warnings = _prepare(page_xml, pin_top=biz)
    if biz and _deck_on(cwd or os.getcwd(), _deck_id(presentation), profile):
        from _exhibit_text_fit import pin_tall_body_top   # on sys.path after _prepare
        page_xml, pin_notes = pin_tall_body_top(page_xml)
        fit_warnings = list(fit_warnings) + pin_notes
    tiny = _tiny_text_warning(page_xml, scale=_canvas_scale(cwd or os.getcwd(), presentation))
    if tiny:
        fit_warnings = list(fit_warnings) + [tiny]
    if not fragments and _hand_diagram(_children(page_xml)):
        notes.append(_HAND_DIAGRAM_NOTE)
    cleaned, dropped = [], 0
    for frag in fragments:
        frag, n = _drop_degenerate(frag)
        cleaned.append(frag)
        dropped += n
    if dropped:
        fit_warnings = list(fit_warnings) + [f"dropped {dropped} zero-size generated shape(s)"]
    origins, xml = {}, page_xml
    for k, frag in enumerate(cleaned):
        before = len(_children(xml))
        xml = compose_slide(xml, frag)
        for i in range(before, len(_children(xml))):
            origins[i] = f"fragment[{k}]"
    generated = set(origins)
    xml = _drop_empty_text_shapes(xml)
    if presentation:
        xml = _snap_off_palette(xml, cwd or os.getcwd(), _deck_id(presentation))
        if _deck_on(cwd or os.getcwd(), _deck_id(presentation), profile):   # ratios > 1 under "0%" come back ÷ 100
            xml, pct_notes = _chart_pct_ratios(xml)
            fit_warnings = list(fit_warnings) + pct_notes
    xml, empty_field = _fill_empty_fields(xml, page, slide_id, cwd or os.getcwd(), _deck_id(presentation)
                                          if presentation else None)
    sample = _sample_label_warning(xml)
    if sample:
        fit_warnings = list(fit_warnings) + [sample]
    result = {
        "ok": True,
        "slide_id": slide_id or "",
        "page_xml": xml,
        "screenshot": "",
        "preview": "",
        "errors": [],
        "summary": [],
        "ignored": 0,
        "no_lint": False,
        "waived": [],
        "warnings": fit_warnings,
    }
    ins_deck = _deck_id(presentation) if presentation else None
    ins_root = cwd or os.getcwd()
    if ins_deck and before_slide_id and page is None and not slide_id and _edit_turn(ins_root, ins_deck):
        # an unregistered slide would fail every later publish with deck_identity_mismatch: same as insert=True there
        anchor = next((k for k, v in _page_registry(ins_root, ins_deck)[1].items()
                       if v == before_slide_id and re.fullmatch(r"p\d+", k)), None)
        if anchor:
            page, insert, before_slide_id = _page_no(anchor), True, None
            prev = f"p{page - 1:02d}"
            try:   # the same script run again: the page in front of the anchor is the one it inserted — rewrite it
                again = prev in json.loads((deck_dir(ins_root, ins_deck) / INSERTED_FILE).read_text(encoding="utf-8"))
            except (OSError, ValueError, TypeError):
                again = False
            if again and _same_page(ins_root, ins_deck, prev, xml):
                page -= 1
            notes.append(f"before_slide_id 指向已登记的页：按 page={page}, insert=True 插入并登记")
    ins_key = _page_key(page) if page is not None and _page_no(page) is not None else None
    insert = bool(insert and ins_deck and ins_key and not slide_id and not before_slide_id)
    if (ins_deck and ins_key and not insert and not slide_id and not before_slide_id
            and _process_key(presentation, page, None) not in _PROCESS_PAGES and not seal_broken(ins_root, ins_deck)
            and _edit_turn(ins_root, ins_deck, ins_key)):
        # before save_as: Frame.publish saves the composed page as xml/<deck>/pNN.xml, where the old title is read
        over = _overwrite_title(ins_root, ins_deck, ins_key, xml)
        if over and _first_hold_mark(ins_root, f"held-overwrite-{ins_deck}.json", page):
            msg = f"page={_page_no(page)} 会覆盖 P{_page_no(page)}《{over[0]}》（新页标题《{over[1]}》）"
            fix = (f"插页加 insert=True（原第 {_page_no(page)} 页及之后自动顺延）；确实要替换这一页就原样重提；"
                   "不要改用 +update-slide / +add-slide 绕过")
            result.update(ok=False, held=True, errors=[{"key": "page_overwrite", "code": "page_overwrite",
                                                         "message": msg, "fix": fix}],
                          summary=notes + [f"未写入（本地检查，只拦一次）page_overwrite：{msg}——{fix}"])
            return result
    if save_as and not insert:   # insert: written after the shift moved the saved XML of the page now at N
        Path(save_as).write_text(xml, encoding="utf-8")
    if empty_field and presentation:
        result.update(ok=False, errors=[empty_field], summary=notes + [f"未写入（本地检查）empty_field：{EMPTY_FIELD_FIX}"])
        return result
    if not presentation:
        result["summary"] = notes
        return result
    deck = _deck_id(presentation)
    owner = _task_deck(cwd)   # a live multi-agent task in this CWD owns one deck (finished / idle tasks own none)
    if owner and deck != owner:
        result.update(ok=False, skipped=True, wrong_deck=owner, summary=notes + [
            f"未写入：这个任务的 deck 是 {owner}（SYNC/deck.txt），不是 {presentation}——一个任务只用一份飞书幻灯片，"
            f"改用 presentation={owner!r} 重新写入；不要另建 deck，已建的多余 deck 不用管、不要删"])
        return result
    root = cwd or os.getcwd()
    # heartbeat first: every attempt by the claim owner — also ones refused below (local checks, holds, server lint) —
    # shows next that the page is being worked on, so it is not handed to another agent mid-iteration
    _touch_claim(root, page, who, deck=deck)
    gone_to = revoked_owner(root, page, note_who or who, deck) if not edit_phase(root, deck) else None
    if gone_to:
        msg = revoked_msg(page, note_who or who, gone_to)
        result.update(ok=False, skipped=True, revoked=True, claim=gone_to,
                      errors=[{"key": "revoked", "code": "revoked", "message": msg, "fix": REVOKED_FIX}],
                      summary=notes + [msg])
        return result
    if seal_broken(root, deck):
        result.update(ok=False, skipped=True, finished=True, errors=[{"key": "seal", "code": "seal", "message": SEAL_MSG,
                                                                     "fix": SEAL_MSG}],
                      summary=notes + [f"未写入：{SEAL_MSG}"])
        return result
    done = _exported(root, deck)
    if done is not None:
        fix = refusal_hint(root, _EXPORTED_MSG, deck)
        result.update(ok=False, skipped=True, finished=True, delivered=True,
                      errors=[{"key": "exported", "code": "exported", "message": f"{done / 'exported'} 存在", "fix": fix}],
                      summary=notes + [f"未写入：{fix}"])
        return result
    if _frozen_lock(root, page, deck) is not None:
        fix = refusal_hint(root, FROZEN_MSG, deck)
        result.update(ok=False, skipped=True, finished=True, errors=[{
            "key": "frozen", "code": "frozen", "message": f"P{_page_no(page)} 在 SYNC/frozen.lock 里（全部页已完成并冻结）",
            "fix": fix}], summary=notes + [f"未写入：P{_page_no(page)} 已冻结——{fix}"])
        return result
    multi = (_multi_page_error() or _process_page_error(presentation, page, slide_id)
             or _window_page_error(root, deck, note_who or who, page, slide_id))
    if multi:
        result.update(ok=False, errors=[multi], summary=notes + [f"未写入：{multi['message']}——{multi['fix']}"])
        return result
    if insert:   # after the hard refusals, before the page checks (their one-shot marks are then this page's own)
        with _deck_lock(root, deck):
            shifted = _insert_shift(root, deck, ins_key, xml)
        if shifted:
            result["renumbered"] = shifted
            _pending_renumber(root, deck, add=shifted, at=_page_no(page))   # footers move once this page is written
            notes.append(f"insert=True：登记表已把原第 {_page_no(page)}–{shifted[-1] - 1} 页顺延为第 {shifted[0]}–{shifted[-1]} 页；"
                         "本页没写成功就原样重提，不会再顺延")
        elif _page_key(page) in _page_registry(root, deck)[1]:
            notes.append(f"insert=True：第 {_page_no(page)} 页就是上次插入的这一页（标题相同），按原地覆盖处理，不再顺延")
        if save_as:
            Path(save_as).write_text(xml, encoding="utf-8")
    blocks = _local_blocks(xml, page, root, set(waive or ()), deck, profile)
    if blocks:
        result.update(ok=False, errors=blocks, summary=notes + [f"未写入（本地检查）{e['key']}：{e['fix']}" for e in blocks]
                      + ([_WAIVE_HINT.format(keys=", ".join(repr(e["key"]) for e in blocks if e["key"] not in _NO_WAIVE))]
                         if any(e["key"] not in _NO_WAIVE for e in blocks) else []))
        return result
    keynote = (profile == "keynote" or (profile == "auto" and _deck_style(root, deck) == "keynote"))
    if keynote:
        kn_errs, kn_warn, hero = _keynote_checks(xml, root, deck, page, slide_id, page_type)
        result["warnings"] = list(result.get("warnings") or []) + kn_warn
        kn_errs, soft = _keynote_hold(kn_errs, root, presentation, page)
        result["warnings"] = list(result.get("warnings") or []) + soft
        if kn_errs:
            result.update(ok=False, errors=kn_errs, summary=notes + [f"未写入（keynote 检查）{e['key']}：{e['message']}——{e['fix']}"
                                                                     for e in kn_errs]
                          + ([KEYNOTE_HOLD_NOTE] if any(e.get("held") for e in kn_errs) else []))
            return result
    if tiny and page is not None and _first_hold_mark(root, f"held-tiny-{presentation}.json", page):
        # multi-agent / page-numbered publish: hold once (the next identical call goes through with the warning)
        err = {"key": "tiny_text", "code": "tiny_text", "message": tiny,
               "fix": "正文字号放大到 ≥10.5pt（正文 ≥14），放不下就删字或拆卡；只拦这一次，确实要保留就原样再提交一次"}
        result.update(ok=False, held=True, errors=[err], summary=notes + [f"未写入（本地检查，只拦一次）tiny_text：{err['fix']}"])
        return result
    note_layout = (_is_subagent(note_who or who) and page is not None and _page_no(page) is not None and not slide_id
                   and not edit_phase(root, deck))
    if note_layout:
        lay = _layout_errors(xml, root, presentation, page, layout, why, same_as_prev, generated)
        if lay:
            result.update(ok=False, errors=lay, summary=notes + [f"未写入（本地检查）{e['key']}：{e['message']}——{e['fix']}"
                                                                 for e in lay])
            return result
    if page is not None and _page_no(page) is not None:   # one-shot layout holds: the next identical call goes through
        held = []
        if sample and _first_hold_mark(root, f"held-sample-{presentation}.json", page):
            held.append({"key": "sample_label_overuse", "code": "sample_label_overuse", "message": sample,
                         "fix": SAMPLE_LABEL_FIX})
        same = _same_skeleton(xml, root, presentation, page)
        if same and _first_hold_mark(root, f"held-skeleton-{presentation}.json", page):
            held.append({"key": "same_skeleton", "code": "same_skeleton", "message": same, "fix": SAME_SKELETON_FIX})
        lay = _speech_layout(xml, root, deck, page)
        if lay and _first_hold_mark(root, f"held-speechlayout-{presentation}.json", page):
            held.append({"key": "speech_layout", "code": "speech_layout", "message": lay,
                         "fix": "按 business-deck.md 第一节\"阅读方向\"改成 (a) 两图并排或 (b) 一行结论 / 大数字 + 1 张图，表格转图表，改完重提同一页"})
        elif lay:
            result["warnings"] = list(result.get("warnings") or []) + [f"speech_layout：{lay}"]
        off = _off_palette(xml, root, deck, page)
        if off and _first_hold_mark(root, f"held-palette-{presentation}.json", page):
            held.append({"key": "off_palette", "code": "off_palette", "message": off, "fix": OFF_PALETTE_FIX})
        elif off:
            result["warnings"] = list(result.get("warnings") or []) + [f"off_palette：{off}"]
        filler = _style_is("research", root, deck) and re.search(
            r"(?:来源|Source)[:：][^<]{0,200}?((?:本|我们)?团队(?:分析|测算|估算|整理|规划|假设)|team\s+(?:analysis|estimates?|E\b))",
            xml, re.I)
        if filler and _first_hold_mark(root, f"held-filler-{presentation}.json", page):
            held.append({"key": "filler_source", "code": "filler_source", "message": f"来源行里有'{filler.group(1)}'",
                         "fix": "来源只写读者能核对的机构/报告（带链接更好）；派生计算在脚注写清算法，删掉'团队测算/团队分析'；只拦这一次"})
        rc = "" if LIB_CARDS[0] else _research_cards(xml, root, deck)
        if rc and _first_hold_mark(root, f"held-cards-{presentation}.json", page):
            held.append({"key": "research_cards", "code": "research_cards", "message": rc, "fix": RESEARCH_CARD_FIX})
        elif rc:
            result["warnings"] = list(result.get("warnings") or []) + [f"research_cards：{rc}"]
        cards = _card_grid(xml, root, deck, page, profile)
        if cards:
            result["warnings"] = list(result.get("warnings") or []) + [f"card_grid：{cards}"]
        axes = _combo_same_axes(xml, root, deck, profile)
        if axes:
            result["warnings"] = list(result.get("warnings") or []) + [f"combo_same_axes：{axes}"]
        ranges = _chart_axis_ranges(xml, root, deck, profile)
        if ranges:
            result["warnings"] = list(result.get("warnings") or []) + [f"chart_axis_range：{ranges}"]
        mono = _deck_monotony(xml, root, deck, page, profile)
        if mono:
            result["warnings"] = list(result.get("warnings") or []) + [f"same_text_skeleton：{mono}"]
        no_note = _missing_note(xml, root, deck, profile)
        if no_note:
            result["warnings"] = list(result.get("warnings") or []) + [f"missing_note：{no_note}"]
        if held:
            result.update(ok=False, held=True, errors=held,
                          summary=notes + [f"未写入（本地检查，只拦一次）{e['key']}：{e['fix']}" for e in held])
            return result
    if screenshot and (keynote or _deck_on(root, deck, profile)) and not waive:
        screenshot = DECK_SHOT   # taken only when the write comes back with warnings (see _send_page)
    if total is not None:
        _planned_total(root, deck, total)
    total = _planned_total(root, deck)
    try:
        r = _upload(
            result,
            xml,
            generated,
            origins,
            presentation,
            slide_id,
            before_slide_id,
            page,
            screenshot,
            set(waive or ()),
            cwd,
            business=_business(root, deck, profile),
        )
        if page is not None and _page_no(page) is not None:
            _server_block_note(r, root, presentation, page, profile)
        if r.get("ok") and r.get("slide_id") and keynote and page is not None:
            _hero_ledger(root, deck, _hero_key(root, deck, page, r.get("slide_id")), hero)
            rhythm = _keynote_rhythm(root, deck, page, xml)
            if rhythm:
                r["warnings"] = list(r.get("warnings") or []) + rhythm
            keynote = "done"   # ledgers updated: not again below
            if (not total and _page_no(page) == 1 and not _keynote_total(root, deck)
                    and _first_hold_mark(root, f"no-total-{presentation}.json", 1)):
                r["warnings"] = list(r.get("warnings") or []) + [NO_TOTAL_MSG]
        if r.get("ok") and r.get("slide_id") and total:
            done_note = _all_written_note(root, presentation, total)
            if done_note:
                r["all_written"] = True
                r["summary"] = list(r.get("summary") or []) + [done_note]
                label, gaps = _must_missing(root, deck) if keynote else ("", [])
                if gaps:
                    if label.startswith("融资"):
                        r["bp_missing"] = gaps
                    r["must_missing"] = gaps
                    r["warnings"] = list(r.get("warnings") or []) + [
                        f"{'bp_missing' if label.startswith('融资') else 'must_missing'}：{label}里这些在页标题里没找到："
                        f"{'、'.join(gaps)}——查得到就补页（每项 1–2 页），查不到写进讲稿说明，不整项删（只提示不拦）"]
                summ = _deck_summary_note(root, deck, total) if keynote else ""
                if summ:
                    r["warnings"] = list(r.get("warnings") or []) + [summ]
        if r.get("ok") and r.get("slide_id"):
            if keynote and keynote != "done":
                _hero_ledger(root, deck, _hero_key(root, deck, page, r.get("slide_id")), hero)
            _touch_claim(root, page, who, written=True, deck=deck)
            if page is not None and _page_no(page) is not None:
                _record_title(root, deck, _page_key(page), xml)
                if insert:
                    _record_inserted(root, deck, _page_key(page), r.get("slide_id"))
                    if result.get("renumbered") or _pending_renumber(root, deck):
                        told = _insert_notice(root, deck, page, result.get("renumbered") or [],
                                              _business(root, deck, profile))
                        notes.extend(told)
                        if not keynote:   # keynote prints the whole summary below; others print this here
                            print("\n".join(f"[publish_slide P{_page_no(page)}] {t}" for t in told), flush=True)
            _nolint_ledger(root, presentation, page, r)
            _warned_ledger(root, deck, page, r)
            _note_process_page(presentation, page, r.get("slide_id"))
            _note_window_page(root, deck, note_who or who, page, slide_id)
            if page is not None and _page_no(page) is not None:
                _skeleton_ledger(root, presentation, page, _skeleton(xml) or [])
                if note_layout:
                    rec = {"layout": str(layout).strip(), "why": str(why).strip(), "who": str(note_who or who)}
                    if same_as_prev:
                        rec["same_as_prev"] = str(same_as_prev).strip()
                    rec["visual"] = _has_visual(xml, generated)
                    st = _structure(xml, generated)
                    if st:
                        rec["skel"] = st
                    gap = _visual_gap_warning(_layout_ledger(root, presentation, page, rec), page)
                    if gap:
                        r["warnings"] = list(r.get("warnings") or []) + [gap]
                        rec["warn"] = gap   # the Lead reads the ledger, not the builder's output
                        _layout_ledger(root, presentation, page, rec)
        return r
    finally:
        result["summary"] = notes + list(result.get("summary") or [])
        seen = set(result["summary"])   # every warning reaches a script that only prints summary
        result["summary"] += [f"warning {w}" for w in (result.get("warnings") or [])
                              if w not in seen and f"warning {w}" not in seen]
        for key, label in (("screenshot", "截图已保存"), ("preview", "预览图已保存")):
            if result.get(key):
                result["summary"].append(f"{label}：{result[key]}（以此路径为准，扩展名可能被改为 .jpg）")
        if result["summary"]:
            result["summary"][-1] += f"（{RATE_NOTE}）"
        else:
            result["summary"].append(RATE_NOTE)
        if keynote:   # keynote: print warnings + summary here, a caller printing only errors still sees them
            print(f"[publish_slide P{page if page is not None else '?'}] ok={result.get('ok')}"
                  + "".join(f"\n  {s_}" for s_ in result["summary"]), flush=True)


PLANNED_FILE = "planned"   # .lark-slides/decks/<deck>/planned: page count passed as publish_slide(total=N)


def _planned_total(cwd, deck, total=None):
    """Single-agent planned page count of this deck: with total, record it; returns the recorded count or None.
    Multi-agent tasks (a SYNC dir bound to this deck) never get it — their finish exports."""
    f = deck_dir(cwd, deck) / PLANNED_FILE
    if total is not None:
        try:
            if int(total) > 0:
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text(str(int(total)), encoding="utf-8")
        except (OSError, ValueError, TypeError):
            pass
    try:
        n = int(f.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None
    try:
        if _task_sync_dirs(cwd, deck, deckless=False):
            return None
    except Exception:  # noqa: BLE001
        pass
    return n if n > 0 else None


def export_command(deck, url=None):
    """The one single-agent delivery command (SKILL.md Step 8)."""
    return ('python3 "<ppt skill 目录>/scripts/multiagent_sync.py" export --who solo --deck ' + str(deck)
            + ' --cwd "$CWD" --name "<标题>" --url "' + (url or "<+create 返回的 url>") + '"')


def _all_written_note(cwd, presentation, total):
    """Once every planned page 1..total is in this deck's page registry: the delivery reminder, else ""."""
    _, registry = _page_registry(cwd, presentation)
    if any(f"p{k:02d}" not in registry for k in range(1, int(total) + 1)):
        return ""
    deck = _deck_id(presentation)
    try:
        url = (deck_dir(cwd, deck) / "url.txt").read_text(encoding="utf-8").strip() or None
    except OSError:
        url = None
    return (f"全部页已写入（{total}/{total}）：下一步执行导出命令 {export_command(deck, url)}，然后一次 present_files "
            "交付链接 + PPTX（export 自己回读一次并列出要看的页，只看那几页、不另截全稿；不写验证记录文件，导出前别停）")


def _page_key(page):
    return None if page is None else (f"p{int(page):02d}" if str(page).isdigit() else str(page))


def _anchor_key(registry, page_key):
    """Registry key of the page a new ``page_key`` goes in front of: the next higher recorded page, compared as numbers
    (p100 comes after p99, not before p11 as a string comparison has it)."""
    n = _page_no(page_key)
    if n is not None and re.fullmatch(r"p\d+", page_key):
        later = sorted((int(k[1:]), k) for k in registry if re.fullmatch(r"p\d+", k) and int(k[1:]) > n)
        return later[0][1] if later else None
    later = sorted(k for k in registry if k > page_key and not re.fullmatch(r"p\d+", k))
    return later[0] if later else None


DECK_LOCK_WAIT = 150   # s a writer waits for the deck lock before giving up with a message


PAGE_TEXT_FILE = "written-text.json"   # .lark-slides/decks/<deck>/written-text.json {pNN: {"t": title, "x": text}}
INSERTED_FILE = "inserted.json"   # .lark-slides/decks/<deck>/inserted.json {pNN: slide id} pages added by insert=True
SAME_PAGE_MIN = 0.25   # shared word share of two versions of one page (edited ≥ 0.28, a different page ≤ 0.17)


def _edit_turn(cwd, deck, key=None):
    """A follow-up edit turn of this deck: it was exported before (decks/<deck>/exported, solo decks), its multi-agent
    task was reopened (status phase "edit"), or (with ``key``) a .pptx in cwd was saved after page ``key`` was last
    written — a bare ``drive +export`` leaves no marker."""
    if (deck_dir(cwd, deck) / "exported").exists() or edit_phase(cwd, deck):
        return True
    if key is None:
        return False
    f = deck_dir(cwd, deck) / PAGE_TEXT_FILE
    try:
        rec = json.loads(f.read_text(encoding="utf-8")).get(key)
        written = rec.get("w") or f.stat().st_mtime
    except (OSError, ValueError, AttributeError):
        return False
    return any(p.stat().st_mtime > written for p in Path(cwd).glob("*.pptx"))


def _visible_text(xml):
    return " ".join(re.sub(r"<[^>]+>", " ", re.sub(r"<note\b.*?</note>", "", xml or "", flags=re.S)).split())


def _title_tokens(text):
    t = (text or "").lower()
    return set(re.findall(r"[a-z]{3,}|\d+(?:\.\d+)?", t)) | {t[i:i + 2] for i in range(len(t) - 1)
                                                            if re.fullmatch(r"[一-鿿]{2}", t[i:i + 2])}


def _recorded_page(cwd, deck, key):
    """(title, visible text or "") last written as `key`: written-text.json, else the saved xml/<deck>/pNN.xml, else the
    keynote ledger's titles."""
    try:
        v = json.loads((deck_dir(cwd, deck) / PAGE_TEXT_FILE).read_text(encoding="utf-8")).get(key)
        if isinstance(v, dict) and (v.get("x") or "").strip():
            return v.get("t") or "", v["x"]
    except (OSError, ValueError, AttributeError):
        pass
    try:
        x = (Path(cwd) / ".lark-slides" / "xml" / str(deck) / f"{key}.xml").read_text(encoding="utf-8")
        return " ".join(_title_texts(x)), _visible_text(x)
    except OSError:
        pass
    try:
        v = json.loads((deck_dir(cwd, deck) / "keynote-shape.json").read_text(encoding="utf-8")).get(key)
        return " ".join((v or {}).get("titles") or []) if isinstance(v, dict) else "", ""
    except (OSError, ValueError, AttributeError):
        return "", ""


def _same_page(cwd, deck, key, xml):
    """True / False: is `xml` a version of the page recorded as `key` (shared word share of the visible text ≥
    SAME_PAGE_MIN; with only the old title known, any shared title word); None when nothing is known about it."""
    title, text = _recorded_page(cwd, deck, key)
    if text.strip():
        a, b = _title_tokens(text), _title_tokens(_visible_text(xml))
        return len(a & b) / max(1, min(len(a), len(b))) >= SAME_PAGE_MIN if a and b else None
    if title.strip():
        new = " ".join(_title_texts(xml))
        return bool(_title_tokens(title) & _title_tokens(new)) if new.strip() else None
    return None


def _overwrite_title(cwd, deck, key, xml):
    """(old title, new title) when `key` is a recorded page and `xml` is clearly another page — page=N about to replace
    a different page (a new page meant to be inserted), else None."""
    if key not in _page_registry(cwd, deck)[1] or _same_page(cwd, deck, key, xml) is not False:
        return None
    title, text = _recorded_page(cwd, deck, key)
    new = " ".join(_title_texts(xml))
    if title.strip() and new.strip() and _title_tokens(title) & _title_tokens(new):
        return None   # the same page redone (title kept or lightly edited), not another page
    return " ".join((title or text).split())[:30], " ".join(" ".join(_title_texts(xml)).split())[:30]


def _record_title(cwd, deck, key, xml):
    f = deck_dir(cwd, deck) / PAGE_TEXT_FILE
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        d = {}
    if key and isinstance(d, dict):
        d[key] = {"t": " ".join(_title_texts(xml)), "x": _visible_text(xml)[:1500], "w": time.time()}
        try:
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass


def _record_inserted(cwd, deck, key, sid):
    f = deck_dir(cwd, deck) / INSERTED_FILE
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        d = {}
    if isinstance(d, dict):
        d[key] = sid
        try:
            f.write_text(json.dumps(d), encoding="utf-8")
        except OSError:
            pass


def _shift_keys(d, n):
    """Dict with every page key (pNN or a bare number) ≥ n moved up by one, other keys kept; None when nothing moved."""
    out, moved = {}, False
    for k, v in d.items():
        m = re.fullmatch(r"(p?)(\d+)", str(k))
        if m and int(m.group(2)) >= n:
            k, moved = (f"p{int(m.group(2)) + 1:02d}" if m.group(1) else str(int(m.group(2)) + 1)), True
        out[k] = v
    return out if moved else None


def _insert_shift(cwd, deck, key, xml):
    """insert=True at page `key` (pN), under the deck lock: when pN is recorded and is not this same page already (an
    earlier insert=True write of it, _same_page), move every page ≥ N up by one — the registry, every per-page ledger of
    this deck (.lark-slides/*-<deck>.json and decks/<deck>/*.json keyed pNN or by number) and the saved
    xml/<deck>/pNN.xml — and grow decks/<deck>/planned by one. Returns the new numbers of the moved pages ([] when
    nothing moved)."""
    n = _page_no(key)
    reg_path, reg = _page_registry(cwd, deck)
    if key not in reg:
        return []
    try:
        mine = key in json.loads((deck_dir(cwd, deck) / INSERTED_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        mine = False
    if mine and _same_page(cwd, deck, key, xml):
        return []   # the page at N is this page (inserted by an earlier call and written): rewrite in place
    top = max(int(k[1:]) for k in reg if re.fullmatch(r"p\d+", k))
    root = Path(cwd) / ".lark-slides"
    files = [f for f in root.glob(f"*{deck}*.json")] + list(deck_dir(cwd, deck).glob("*.json"))
    for f in files:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(d, dict):
            moved = _shift_keys(d, n)
            if moved is not None:
                _save_registry(f, moved)
    xd = root / "xml" / str(deck)
    for f in sorted(xd.glob("p[0-9]*.xml"), key=lambda p: -int(p.stem[1:])):
        if int(f.stem[1:]) >= n:
            os.replace(f, xd / f"p{int(f.stem[1:]) + 1:02d}.xml")
    planned = deck_dir(cwd, deck) / PLANNED_FILE
    try:
        if int(planned.read_text(encoding="utf-8").strip()) <= top:
            planned.write_text(str(top + 1), encoding="utf-8")
    except (OSError, ValueError):
        pass
    return list(range(n + 1, top + 2))
_LOCKS = {}   # (lock path, thread) -> [open file, depth]: _deck_lock is re-entrant inside one process (verify_order repair)


class _deck_lock:
    """Exclusive flock on <cwd>/.lark-slides/pages-<deck>.lock around every server write of that deck from this CWD and
    the registry read-modify-write around it. Parallel writers (builders + Lead) therefore never send two writes of one
    deck at the same time: concurrent +add-slide / +update-slide calls each resolve "latest revision" on their own and
    the server can drop a page or hand one slide_id to two pages."""

    def __init__(self, cwd, presentation):
        import threading
        self.file = Path(cwd) / ".lark-slides" / f"pages-{presentation}.lock"
        self.path = (str(self.file.resolve()), threading.get_ident())   # re-entrant per thread, exclusive across

    def __enter__(self):
        held = _LOCKS.get(self.path)
        if held:
            held[1] += 1
            return self
        import fcntl
        self.file.parent.mkdir(parents=True, exist_ok=True)
        f = open(self.file, "w")
        import time as _tl
        end = _tl.time() + DECK_LOCK_WAIT
        while True:   # bounded: a writer stuck on a hung CLI call must not freeze every other agent's publish
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if _tl.time() > end:
                    f.close()
                    raise TimeoutError(f"另一个写入占着这份 deck 超过 {DECK_LOCK_WAIT}s（可能卡在服务端调用）：这页没写，"
                                       "先做别的页或运行 next，稍后用同一调用重试；不要绕过 publish 直接 +add-slide")
                _tl.sleep(0.5)
        _LOCKS[self.path] = [f, 1]
        return self

    def __exit__(self, *exc):
        held = _LOCKS[self.path]
        held[1] -= 1
        if held[1] == 0:
            held[0].close()
            del _LOCKS[self.path]
        return False


_STUB_XML = ('<slide xmlns="https://www.larkoffice.com/sml/2.0"><style><fill><fillColor color="rgba(255,255,255,1)"/></fill>'
             '</style><data><shape type="text" topLeftX="40" topLeftY="40" width="400" height="60">'
             '<content fontSize="24" color="rgba(31,35,41,1)"><p>写入中</p></content></shape></data></slide>')
CANVAS_FILE = "canvas.json"   # .lark-slides/decks/<deck>/canvas.json {"width", "height"}: the deck's real canvas


def _deck_canvas(cwd, presentation, fetch=True):
    """(width, height) of the deck: cached canvas.json, else a template WORK_DIR's source-slides/full.xml, else one
    +xml-get of the deck (<presentation width height>), cached. None when unknown."""
    deck = _deck_id(presentation)
    f = deck_dir(cwd, deck) / CANVAS_FILE
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
        return float(d["width"]), float(d["height"])
    except (OSError, ValueError, KeyError, TypeError):
        pass
    text = ""
    full = Path(cwd or ".") / "source-slides" / "full.xml"
    if full.is_file():
        with open(full, encoding="utf-8", errors="ignore") as fh:
            text = fh.read(4096)
    m = re.search(r'<presentation\b[^>]*?\bwidth=\\?"([\d.]+)\\?"[^>]*?\bheight=\\?"([\d.]+)', text)
    if not m and not fetch:
        return None
    if not m:
        res = _run(["slides", "+xml-get", "--as", "user", "--presentation", presentation], cwd)
        text = json.dumps(res.get("data") or {}, ensure_ascii=False)[:20000] if res.get("ok") else ""
        m = re.search(r'<presentation\b[^>]*?\bwidth=\\?"([\d.]+)\\?"[^>]*?\bheight=\\?"([\d.]+)', text)
    if not m:
        return None
    w, h = float(m.group(1)), float(m.group(2))
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps({"width": w, "height": h}), encoding="utf-8")
    except OSError:
        pass
    return w, h


def _canvas_only(errors, cwd, presentation):
    """Deck canvas (w, h) when every server finding is a *_out_of_canvas whose box lies inside the deck's real canvas
    (the server lints a single page at 960×540 whatever the deck size); else None."""
    if not errors or not all(str(e.get("code") or "").endswith("_out_of_canvas") for e in errors):
        return None
    boxes = []
    for e in errors:
        b = e.get("bbox") or (e.get("measurement") or {}).get("bbox") or next(
            (o.get("bbox") for o in e.get("related_objects") or [] if o.get("bbox")), None)
        try:
            boxes.append((float(b["x"]), float(b["y"]), float(b["x"]) + float(b["width"]), float(b["y"]) + float(b["height"])))
        except (TypeError, KeyError, ValueError):
            return None
    canvas = _deck_canvas(cwd, presentation)
    if not canvas or (canvas[0] <= 960 and canvas[1] <= 540):
        return None
    w, h = canvas
    return canvas if all(x0 >= -2 and y0 >= -2 and x1 <= w + 2 and y1 <= h + 2 for x0, y0, x1, y1 in boxes) else None


def _upload(result, xml, generated, origins, presentation, slide_id, before_slide_id, page, screenshot, waive, cwd,
            trusted=False, owned_slide_ids=(), business=True):
    """Send one page under the deck lock. ``trusted`` (verify_order repair: XML that was accepted before) re-sends without
    lint when lint blocks."""
    cwd = cwd or os.getcwd()
    out_dir = ".lark-slides/screenshots/publish"
    os.makedirs(os.path.join(cwd, out_dir), exist_ok=True)
    fd, tmp = tempfile.mkstemp(suffix=".xml", dir=cwd)
    os.close(fd)
    Path(tmp).write_text(xml, encoding="utf-8")
    rel = os.path.relpath(tmp, cwd)
    try:
        with _deck_lock(cwd, presentation):
            shot = _send_page(result, xml, generated, origins, presentation, slide_id, before_slide_id, page,
                              waive, cwd, rel, screenshot, trusted, owned_slide_ids, business)
        if shot:   # screenshots are taken after the lock is released: other writers need not wait for them
            kind, args, name = shot
            result[kind] = _screenshot(args, cwd, out_dir, name)
        return result
    finally:
        os.unlink(tmp)


def _add_attempts(registry_path, page_key, add=False):
    """Failed +add-slide attempts of `page_key` (<cwd>/.lark-slides/addfail-<deck>.json): only such a page may adopt the
    one unregistered slide sitting in its place (a server error after the slide was created)."""
    if not page_key:
        return 0
    f = Path(registry_path).with_name(Path(registry_path).name.replace("pages-", "addfail-", 1))
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        d = {}
    if add:
        d[page_key] = int(d.get(page_key, 0)) + 1
        _save_registry(f, d)
    return int(d.get(page_key, 0) or 0)


def _adopt_orphan(checked, registry, page_key):
    """deck_identity_mismatch caused only by ONE unregistered slide sitting exactly where `page_key` belongs in the
    page order (every registered page before it is lower, every one after it higher) while `page_key` itself is not
    registered (or its slide is gone): the slide a failed write of this page left behind. Returns its id, else None."""
    if checked.get("ok") or checked.get("code") != "deck_identity_mismatch" or not page_key:
        return None
    n = _page_no(page_key)
    extra = checked.get("unexpected_slide_ids") or []
    if n is None or len(extra) != 1 or checked.get("duplicates"):
        return None
    pages = {k: v for k, v in registry.items() if re.fullmatch(r"p\d+", k)}
    order = checked.get("ordered_slide_ids") or []
    if pages.get(page_key) in order:
        return None   # this page already has a live slide: the stranger belongs to someone else
    missing = set(checked.get("missing") or []) - {n}
    if missing:
        return None
    by_id = {v: int(k[1:]) for k, v in pages.items()}
    pos = order.index(extra[0]) if extra[0] in order else -1
    if pos < 0:
        return None
    before = [by_id[s] for s in order[:pos] if s in by_id]
    after = [by_id[s] for s in order[pos + 1:] if s in by_id]
    if all(p < n for p in before) and all(p > n for p in after) and before == sorted(before) and after == sorted(after):
        return extra[0]
    return None


def _footer_no(body):
    """Page number printed in a slide's footer (a short text box at the bottom right: "12" or "12 / 15"), else None."""
    m = _footer_match(body)
    return int(m.group(2)) if m else None


def _footer_match(body):
    """The footer page-number box: group 2 = the page number, group 4 = the total of an "N / M" footer (else None)."""
    for m in re.finditer(r'<shape\b([^>]*)>(?:(?!</shape>).)*?<p\b[^>]*>\s*(\d{1,3})(\s*/\s*(\d{1,3}))?\s*</p>', body or "",
                         re.S):
        y = re.search(r'topLeftY="([\d.]+)"', m.group(1))
        x = re.search(r'topLeftX="([\d.]+)"', m.group(1))
        if y and x and float(y.group(1)) >= 480 and float(x.group(1)) >= 700:
            return m
    return None


RENUMBER_FILE = "renumber.json"   # decks/<deck>/renumber.json {"pages": [new page numbers]}: footers still to move +1


def _pending_renumber(cwd, deck, add=None, at=None, clear=False):
    """Pages shifted by insert=True whose footer page number has not been moved yet; add (with at=N: earlier pending
    pages ≥ N shift too) / clear; returns the sorted list."""
    f = deck_dir(cwd, deck) / RENUMBER_FILE
    try:
        pages = [int(p) for p in json.loads(f.read_text(encoding="utf-8")).get("pages") or []]
    except (OSError, ValueError, AttributeError, TypeError):
        pages = []
    if add:
        pages = sorted({p + 1 if at is not None and p >= at else p for p in pages} | set(add))
    if clear:
        pages = []
    if add or clear:
        try:
            if pages:
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text(json.dumps({"pages": pages}), encoding="utf-8")
            else:
                f.unlink(missing_ok=True)
        except OSError:
            pass
    return sorted(pages)


def _paras(xml):
    import html as _html
    xml = re.sub(r"<note\b.*?</note>", "", xml or "", flags=re.S)
    return sorted(" ".join(_html.unescape(re.sub(r"<[^>]+>", "", p)).split())
                  for p in re.findall(r"<p\b[^>]*>(.*?)</p>", xml, re.S))


FRAME_FOOTER = re.compile(r'topLeftX="870" topLeftY="512" width="50" height="16"><content fontSize="10"[^>]*textAlign="right"')


def _bump_footer(xml, m, page_step, totals):
    """`xml` with the footer `m` moved: page number + page_step, an "N / M" total + 1 when M is in `totals`."""
    if m.group(4) and int(m.group(4)) in totals:
        xml = xml[:m.start(4)] + str(int(m.group(4)) + 1) + xml[m.end(4):]
    if page_step:
        n = m.group(2)
        xml = xml[:m.start(2)] + str(int(n) + page_step).zfill(len(n)) + xml[m.end(2):]
    return xml


def renumber_footers(cwd, deck, pages, business=True):
    """After insert=True: each shifted page with a footer page number gets that number +1 (only the digits of that one
    text box; an "N / M" footer's total M + 1 too, and so on every other registered page showing that total) and is
    written back with +update-slide under the deck lock. The page is read from its saved .lark-slides/xml/<deck>/pNN.xml
    when the live slide still shows the same text (else left for a hand fix), or from the live slide when nothing was
    saved. Outside business decks only frame()'s own footer box (FRAME_FOOTER) is touched: a hand-placed bottom-right
    number may be anything. Returns (updated pages, pages to fix by hand, whether any page carries a footer number)."""
    xd = Path(cwd) / ".lark-slides" / "xml" / str(deck)
    done, manual = [], []
    with _deck_lock(cwd, deck):
        _, registry = _page_registry(cwd, deck)
        res = _run(["slides", "+xml-get", "--as", "user", "--presentation", deck], cwd)
        live = dict(_deck_slides(res)) if isinstance(res, dict) and res.get("ok") else {}
        todo = {}   # page -> (saved file or None, source xml, footer match, live body)
        for n in sorted(int(k[1:]) for k in registry if re.fullmatch(r"p\d+", k)):
            f = xd / f"p{n:02d}.xml"
            body = live.get(registry.get(f"p{n:02d}"))
            src = f.read_text(encoding="utf-8") if f.exists() else (f'<slide xmlns="{_SML}">{body}</slide>' if body else "")
            m = _footer_match(src)
            if m:
                todo[n] = (f if f.exists() else None, src, m, body)
        shifted = [n for n in pages if n in todo]
        totals = {int(todo[n][2].group(4)) for n in shifted if todo[n][2].group(4)}
        if not shifted:
            return [], [], False
        others = [n for n in todo if n not in pages and todo[n][2].group(4) and int(todo[n][2].group(4)) in totals]
        for n in shifted + others:
            f, src, m, body = todo[n]
            if (not body or _footer_no(body) != int(m.group(2)) or _paras(body) != _paras(src)
                    or not (business or FRAME_FOOTER.search(m.group(0)))):
                manual.append(n)
                continue
            new = _bump_footer(src, m, 1 if n in pages else 0, totals)
            if new == src:
                continue
            fd, tmp = tempfile.mkstemp(suffix=".xml", dir=cwd)
            os.close(fd)
            Path(tmp).write_text(new, encoding="utf-8")
            args = ["slides", "+update-slide", "--as", "user", "--presentation", deck, "--slide-id",
                    registry[f"p{n:02d}"], "--content", f"@{os.path.relpath(tmp, cwd)}"]
            try:
                r = _run(args, cwd)
                if not (isinstance(r, dict) and r.get("ok")) and "4000153" in json.dumps(r, ensure_ascii=False):
                    r = _run(args + ["--no-lint"], cwd)   # the page passed before; only one digit changed
            finally:
                os.unlink(tmp)
            if isinstance(r, dict) and r.get("ok"):
                if f is not None:
                    f.write_text(new, encoding="utf-8")
                _record_title(cwd, deck, f"p{n:02d}", new)
                done.append(n)
            else:
                manual.append(n)
    return sorted(done), sorted(manual), True


def _insert_notice(cwd, deck, page, shifted, business=True):
    """The lines printed after a successful insert=True write: where the page went, footers moved, navs to redo."""
    n = _page_no(page)
    pend = _pending_renumber(cwd, deck)
    why = ""
    try:
        done, manual, has = renumber_footers(cwd, deck, pend, business) if pend else ([], [], False)
    except Exception as e:  # noqa: BLE001 — never blocks the page that was just written
        done, manual, has, why = [], list(pend), True, f"（{str(e)[:80]}）"
    if pend:
        _pending_renumber(cwd, deck, clear=True)
    rng = f"（现为第 {shifted[0]}–{shifted[-1]} 页）" if shifted else ""
    if not has:
        foot = "页上没有页脚页码，不用改"
    else:
        parts = ([f"已自动更新：{'、'.join(f'P{p}' for p in done)}"] if done else []) + (
            [f"需更新（用 page=N 重提）：{'、'.join(f'P{p}' for p in manual)}{why}"] if manual else [])
        foot = "页脚页码" + "；".join(parts)
    lines = [f"已插入为第 {n} 页；原第 {n} 页及之后顺延{rng}，{foot}"]
    if _style_is("research", cwd, deck):
        lines.append("目录/导航页需要重发：plan.py 的 SECTIONS / PAGES 里插入页之后的页号 +1 并加上新页一行，再运行 "
                     "publish_contents_and_navs(SECTIONS, PAGES, descs=CHAPTER_DESCS, deck=…, cwd=…)"
                     "（PAGES 用 plan.py 原样的行，导航页靠 recipe='chapter_nav'）")
    else:
        lines.append("目录页 / 正文里写到的页码（如\"见 P12\"）也要 +1")
    return lines


def _title_of(body):
    """Second text paragraph of a page (after the section tag): the page title as frame() writes it."""
    ps = [re.sub(r"<[^>]+>", "", x).strip() for x in re.findall(r"<p\b[^>]*>.*?</p>", body or "", re.S)]
    ps = [x for x in ps if x]
    return ps[1] if len(ps) > 1 else (ps[0] if ps else "")


def _adopt_by_footer(checked, response, registry, cwd, deck):
    """deck_identity_mismatch caused only by unregistered slides that are pages of this task written by an add whose
    reply was lost: a stranger whose footer page number N is not registered and whose title equals the saved
    .lark-slides/xml/<deck>/pNN.xml title is registered as pN. Returns {page key: slide id} adopted (nothing on doubt)."""
    if checked.get("ok") or checked.get("code") != "deck_identity_mismatch" or checked.get("duplicates"):
        return {}
    extra = checked.get("unexpected_slide_ids") or []
    if not extra or len(extra) > 3:
        return {}
    bodies = dict(_deck_slides(response))
    xml_dir = Path(cwd) / ".lark-slides" / "xml" / str(deck)
    got = {}
    for sid in extra:
        n = _footer_no(bodies.get(sid))
        k = f"p{n:02d}" if n else None
        f = xml_dir / f"{k}.xml" if k else None
        if not k or k in registry or k in got or not f.exists():
            return {}
        t_live, t_saved = _title_of(bodies.get(sid)), _title_of(f.read_text(encoding="utf-8"))
        if not t_live or t_live != t_saved:
            return {}
        got[k] = sid
    return got


def drop_duplicate_strangers(checked, response, registry, cwd, deck):
    """Unregistered slides that repeat a registered page (same footer page number and same title as that page's live
    slide) are leftovers of an earlier write of that page: delete them. Returns the deleted slide ids."""
    if checked.get("ok") or checked.get("code") != "deck_identity_mismatch" or checked.get("duplicates"):
        return []
    bodies = dict(_deck_slides(response))
    gone = []
    for sid in checked.get("unexpected_slide_ids") or []:
        n = _footer_no(bodies.get(sid))
        live = registry.get(f"p{n:02d}") if n else None
        if not live or live not in bodies:
            continue
        t = _title_of(bodies.get(sid))
        if not t or t != _title_of(bodies[live]):
            continue
        r = _run(["slides", "+delete-slide", "--as", "user", "--presentation", deck, "--slide-id", sid], cwd)
        if isinstance(r, dict) and r.get("ok"):
            gone.append(sid)
    return gone


def _send_page(result, xml, generated, origins, presentation, slide_id, before_slide_id, page, waive, cwd, rel,
               screenshot, trusted, owned_slide_ids=(), business=True):
    """Runs under _deck_lock. Returns (result key, screenshot args, name) when a screenshot is wanted, else None."""
    registry_path, registry = _page_registry(cwd, presentation)
    directory, status = _binding_task(cwd, presentation)
    if directory is not None or status.get("ambiguous_binding"):
        response = _run(["slides", "+xml-get", "--as", "user", "--presentation", presentation], cwd)
        checked = _check_task_deck(cwd, presentation, response, registry, initialize=True, repair=trusted,
                                   owned_slide_ids=owned_slide_ids)
        adopted = _adopt_orphan(checked, registry, _page_key(page)) if _add_attempts(registry_path, _page_key(page)) else None
        if adopted:   # the last attempt's slide (server 500 after creating it): register it instead of asking the model
            registry[_page_key(page)] = adopted
            _save_registry(registry_path, registry)
            warnings_pre = [f"{_page_key(page)} 上次写入返回错误但服务端已建出 slide {adopted}：已自动登记到 pages 映射并就地更新"]
            result.setdefault("warnings", []).extend(warnings_pre)
            checked = _check_task_deck(cwd, presentation, response, registry, initialize=True, repair=trusted,
                                       owned_slide_ids=owned_slide_ids)
        found = _adopt_by_footer(checked, response, registry, cwd, presentation) if not checked["ok"] else {}
        if found:   # pages whose add reply was lost (slide created, never registered): register them by footer + title
            registry.update(found)
            _save_registry(registry_path, registry)
            result.setdefault("warnings", []).append(
                f"deck 里有 {len(found)} 张未登记的 slide 是本任务已写的页（页脚页码与标题对得上）：已登记为 {sorted(found)}")
            checked = _check_task_deck(cwd, presentation, response, registry, initialize=True, repair=trusted,
                                       owned_slide_ids=owned_slide_ids)
        if (not checked["ok"] and checked.get("code") == "deck_identity_mismatch" and not checked.get("duplicates")
                and _page_key(page)):
            # a stranger / misordered slide elsewhere in the deck is not this page's problem: write this page (it
            # updates its own slide or inserts by page order) and leave the stranger to finish
            result.setdefault("warnings", []).append(
                "deck 里有未登记或顺序不对的 slide（不是本页的问题，本页照常写入）：finish 会自动清掉与已登记页重复的残留页、按页码重排")
            checked = {"ok": True}
        if not checked["ok"]:
            result.update(ok=False, errors=[{"key": checked["code"], "code": checked["code"],
                                            "message": checked["next"], "fix": checked["next"]}],
                          summary=[checked["next"]], deck_binding=checked)
            return None
    page_key = _page_key(page)
    pinned = {"slide": bool(slide_id), "before": bool(before_slide_id)}
    warnings = []

    def place():
        nonlocal slide_id, before_slide_id
        if page_key and not pinned["slide"]:
            slide_id = registry.get(page_key)
            shared = [k for k, v in registry.items() if slide_id and v == slide_id and k != page_key]
            if shared:   # one slide recorded for two pages: never overwrite the other page's slide, add this page anew
                warnings.append(f"登记表里 {page_key} 和 {', '.join(shared)} 指向同一个 slide {slide_id}：本页改为新增一页，"
                                "写完后运行 verify_order(deck, repair=True) 核对页序")
                registry.pop(page_key, None)
                _save_registry(registry_path, registry)
                slide_id = None
        if page_key and not slide_id and not pinned["before"]:
            k = _anchor_key(registry, page_key)
            before_slide_id = registry[k] if k else None

    place()

    def send(no_lint):
        for _ in range(3):   # a page the user deleted in the deck: forget it and insert again in page order
            res = send_once(no_lint)
            if res.get("ok") or not page_key or not _gone(res):
                return res
            stale = [k for k, v in registry.items() if v in (slide_id, before_slide_id)
                     and not (pinned["slide"] and v == slide_id) and not (pinned["before"] and v == before_slide_id)]
            if not stale:
                return res
            for k in stale:
                registry.pop(k, None)
            _save_registry(registry_path, registry)
            place()
        return res

    def send_once(no_lint):
        if slide_id:
            args = ["slides", "+update-slide", "--as", "user", "--presentation", presentation, "--slide-id", slide_id,
                    "--content", f"@{rel}"]
        else:
            args = ["slides", "+add-slide", "--as", "user", "--presentation", presentation, "--slide", f"@{rel}"]
            if before_slide_id:
                args += ["--before-slide-id", before_slide_id]
        res = _run(args + (["--no-lint"] if no_lint else []), cwd)
        if not slide_id and page_key and not (isinstance(res, dict) and res.get("ok")):
            _add_attempts(registry_path, page_key, add=True)   # a failed add may still have created the slide
        return res

    def failure(res):
        err = res.get("error") or {}
        msg = str(err.get("message", err))[:1500]
        if str(err.get("code")) == "3350002" or re.search(r"not[ _]?found|不存在", msg, re.I):
            target = f"slide_id {slide_id!r}" if slide_id else f"presentation {presentation!r}"
            fix = (
                f"{target} 不存在：这不是排版、缓存或网络问题。把 presentation 改成 +create 返回的 "
                "xml_presentation_id 原文（复制，不要手敲）；更新页时核对 slide_id 或删掉 .lark-slides/pages-*.json 里的旧记录。"
            )
        else:
            fix = "不是排版问题：按 message 修正 XML 结构/参数后用同一调用重试，不要加 --no-lint，也不要绕过 publish_slide 直接 +add-slide。"
        item = {"code": "upload_failed", "cli_code": err.get("code"), "message": msg, "fix": fix}
        result["summary"] = [f"upload_failed（cli {err.get('code')}）：{msg[:200]} → {fix}"]
        return [item]

    res, described = send(False), []
    if not res.get("ok"):
        try:
            report = json.loads(res["error"]["message"])
            errors = [e for s in report.get("slides", []) for e in s.get("errors", [])]
            errors += list((report.get("document") or {}).get("errors", []))
        except (KeyError, TypeError, ValueError):
            result.update(ok=False, errors=failure(res))
            return None
        ignorable, report_errs = _classify(xml, generated, errors)
        canvas = _canvas_only(report_errs, cwd, presentation) if report_errs and not trusted else None
        if canvas:   # every finding: *_out_of_canvas inside the deck's real (non-960) canvas — the server lints at 960×540
            added_stub = not slide_id
            if added_stub:   # minimal placeholder page for a slide_id, then the full page without lint
                stub = os.path.join(os.path.dirname(os.path.join(cwd, rel)), f".stub-{os.getpid()}.xml")
                Path(stub).write_text(_STUB_XML, encoding="utf-8")
                args = ["slides", "+add-slide", "--as", "user", "--presentation", presentation,
                        "--slide", f"@{os.path.relpath(stub, cwd)}"] + (["--before-slide-id", before_slide_id]
                                                                         if before_slide_id else [])
                try:
                    res = _run(args, cwd)
                finally:
                    os.unlink(stub)
                slide_id = (res.get("data") or {}).get("slide_id") if res.get("ok") else None
            if slide_id:
                res = send_once(True)
                if res.get("ok") and added_stub:
                    res = dict(res, data=dict(res.get("data") or {}, slide_id=slide_id))
            if not res.get("ok"):
                result.update(ok=False, errors=failure(res))
                return None
            result["no_lint"] = True
            result["canvas_false_positives"] = sorted({str(e.get("code")) for e in report_errs})
            result["summary"] = [f"服务端按 960×540 判出界，元素都在 deck 画布 {canvas[0]:g}×{canvas[1]:g} 内：已自动占位页 + "
                                 "完整版 --no-lint 覆盖写入，不用改页、不用裸 +add-slide"]
            report_errs, errors = [], []
        result["ignored"] = len(ignorable)
        result["ignored_codes"] = sorted({str(e.get("code")) for e in ignorable if e.get("code")})
        described = [_describe(xml, e, generated, origins) for e in report_errs]
        auto = [d for d in described if _local_false_positive(d, business)]
        if auto and page is not None and _page_no(page) is not None and not trusted:
            # finish's read-back lint uses the server's estimate and blocks it again: grow one line now, else hold once
            over = [d for d in auto if d.get("code") == "text_may_overflow_shape" and d.get("wrapped_fit")]
            grown, grow_notes = (_grow_for_headroom(xml, over, _deck_canvas(cwd, presentation, fetch=False) or (960, 540))
                                 if over else (None, []))
            if over and grown is not None:
                if grown != xml:
                    xml = grown
                    Path(os.path.join(cwd, rel)).write_text(xml, encoding="utf-8")
                    result["page_xml"] = xml
                warnings.extend(grow_notes)
            elif over and _first_hold_mark(cwd, f"held-overflow-{presentation}.json", page):
                auto = [d for d in auto if d not in over]
                for d in over:
                    d.pop("auto_waived", None)
                    d["fix"] = ("服务端估算这段文字超出文字框，finish 回读时还会拦（不是误报，不要 waive）：把框加高一行"
                                f"（{grow_notes}），放不下再删修饰词，保留数字 / 指标；只拦这一次，重提即写入")
        if auto:
            waive = set(waive or ()) | {d["key"] for d in auto}
            warnings.extend(f"{d['code']} 已自动降为 warning（{d['auto_waived']}）：Read 返回的截图确认一眼即可，不用改页"
                            for d in auto)
        left = [d for d in described if d["key"] not in waive or "不是误报" in (d.get("fix") or "")]
        widened, widen_notes = (_auto_widen(xml, left, (_deck_canvas(cwd, presentation, fetch=False) or (960,))[0])
                                if left and not canvas and not trusted else (None, []))
        if widen_notes and not widened:   # widening would hit an image / neighbour: refused as before, say why
            result["widen_failed"] = widen_notes[0]
            result["warnings"] = list(result.get("warnings") or []) + widen_notes
        if widened:   # small wrap=false overflow: widen the box and resubmit once (with lint) instead of refusing
            Path(os.path.join(cwd, rel)).write_text(widened, encoding="utf-8")
            rest = len(left) < len(described)   # other findings already waived / auto-downgraded
            res2 = send(False)
            if not res2.get("ok") and rest and _only_waived(res2, widened, generated, origins, waive, business):
                res2 = send(True)   # lint now reports only the findings judged before: keep them waived
            if res2.get("ok"):
                xml, res, left = widened, res2, []
                described = [d for d in described if d["key"] in waive]
                result.update(page_xml=widened, auto_widened=True, no_lint=rest or result.get("no_lint", False))
                warnings.extend(widen_notes)
            else:
                Path(os.path.join(cwd, rel)).write_text(xml, encoding="utf-8")
                widened = None
                why = (res2.get("error") or {}).get("message") or res2.get("error") or "未知"
                try:
                    rep = json.loads(why)
                    why = "；".join(str(e.get("message") or e.get("code")) for sl in rep.get("slides", [])
                                   for e in sl.get("errors", []))[:300] or why
                except (TypeError, ValueError, AttributeError):
                    pass
                note = (f"auto_widen 已试过加宽重提但仍被拒（{str(why)[:300]}），已回滚到原 XML：按下面 errors 手动加宽"
                        "到报文 estimated line 宽度 ×1.06 +12px 以上，或给文字开 wrap=\"true\" 并留够高度")
                result["warnings"] = list(result.get("warnings") or []) + [note]
                result["widen_failed"] = note
        if canvas or widened:
            pass
        elif left and not trusted:
            real = [d for d in left if "不是误报" in (d.get("fix") or "")]
            maybe = [d for d in left if d not in real]
            result.update(
                ok=False,
                errors=left,
                summary=_summarize(left)
                + ([result["widen_failed"]] if result.get("widen_failed") else [])
                + ([_WAIVE_HINT.format(keys=", ".join(repr(d["key"]) for d in maybe))] if maybe else []),
            )
            return ("preview", ["--content", f"@{rel}"], f"preview-{int(time.time() * 1000)}") if screenshot else None
        else:
            orphan_xml, orphan_notes = _orphan_widen(xml, described, (_deck_canvas(cwd, presentation, fetch=False)
                                                                      or (960,))[0]) if auto and not trusted else (xml, [])
            if orphan_xml != xml:   # wrap=true title ending on a 1–2 character line: widen slightly before writing
                xml = orphan_xml
                Path(os.path.join(cwd, rel)).write_text(xml, encoding="utf-8")
                result["page_xml"] = xml
            warnings.extend(orphan_notes)
            res = send(True)
            result["no_lint"] = True
        if described and not trusted:
            screenshot = True
            result["waived"] = [d["key"] for d in described]
            waived_lines = [f"  - p{page or ''} {d['code']}：{d.get('message') or ''}"[:160] for d in described]
            result["summary"] = [
                f"已按 waive 跳过 {len(described)} 条 lint 强行写入：Read 一次返回的 screenshot 确认这些位置"
                "没有真遮挡/截断/低对比；确有问题就修好后不带 waive 重提（只看这一张，不截其他页）。",
                "注意：服务端不会记住这次豁免，回读报告里还会出现下面这些条目；lint_inspect.py 已按 "
                ".lark-slides/nolint-<deck>.json 把它们标为 confirmed_waived 并默认滤掉——不要回头再改这一页：",
                *waived_lines,
            ]
        if not res.get("ok"):
            result.update(ok=False, errors=failure(res))
            return None
    added = not slide_id
    sid = (res.get("data") or {}).get("slide_id") or slide_id or ""
    result["slide_id"] = sid
    if sid:
        # the server re-issues the id of a deleted slide: a page still recorded under a freshly added id is gone
        reused = [k for k, v in registry.items() if v == sid and k != page_key] if added else []
        for k in reused:
            registry.pop(k, None)
        if reused:
            warnings.append(f"服务端把 {', '.join(reused)} 登记的 slide_id {sid} 给了这一页——说明 {', '.join(reused)} "
                            "已被删出 deck（不是本页的问题）。已从登记表移除；运行 verify_order(deck, repair=True) "
                            "按保存的 XML 补回，不要用裸 +add-slide / +delete-slide")
        if page_key:
            registry[page_key] = sid
        if page_key or reused:
            _save_registry(registry_path, registry)
    if warnings:
        result["warnings"] = list(result.get("warnings") or []) + warnings
        result["summary"] = list(result.get("summary") or []) + warnings
    if screenshot == DECK_SHOT and not result.get("warnings"):   # deck page with nothing to check: no screenshot
        result["summary"] = list(result.get("summary") or []) + [DECK_SHOT_NOTE]
        return None
    if screenshot and sid:
        return ("screenshot", ["--presentation", presentation, "--slide-id", sid], f"{sid}-{int(time.time())}")
    return None


DECK_SHOT = "deck-if-warned"   # profile='deck' screenshot=True: shoot only when the write carries warnings / waivers
DECK_SHOT_NOTE = ("本页无 warning，已忽略 screenshot=True（不逐页截图；写完全部页后 export 会列出需要看的页，只看那几页）")
RATE_NOTE = "已自带限速，不要 sleep"   # last words of every publish output: models padded each write with sleep 3–5 s

def _only_waived(res, xml, generated, origins, waive, business=True):
    """True when a lint refusal lists only findings already waived / judged false positives (keys in waive or
    auto-downgraded again on xml)."""
    try:
        report = json.loads(res["error"]["message"])
        errors = [e for s_ in report.get("slides", []) for e in s_.get("errors", [])]
    except (KeyError, TypeError, ValueError):
        return False
    _, real = _classify(xml, generated, errors)
    return all(d["key"] in waive or _local_false_positive(d, business) for d in (_describe(xml, e, generated, origins) for e in real))


def _gone(res):
    err = res.get("error") or {}
    try:   # a lint report (JSON with "slides") that merely mentions "不存在" is not a missing slide
        if isinstance(json.loads(str(err.get("message", ""))), dict):
            return False
    except ValueError:
        pass
    return str(err.get("code")) == "3350002" or bool(re.search(r"not[ _]?found|不存在", str(err.get("message", err)), re.I))


def _save_registry(path, registry):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(registry, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)


# ------------------------------------------------------------------ deck order check / repair (one +xml-get)

def _deck_slides(res):
    """[(slide_id, slide body)] in deck order from a +xml-get result."""
    data = (res or {}).get("data") or {}
    content = ((data.get("xml_presentation") or {}).get("content") if isinstance(data.get("xml_presentation"), dict)
               else None)
    if not isinstance(content, str):
        content = json.dumps(data, ensure_ascii=False).replace('\\"', '"')
    return [(m.group(1), m.group(2) or "") for m in
            re.finditer(r'<slide\b[^>]*?\bid="([^"]+)"[^>]*?(?:/>|>(.*?)</slide>)', content, re.S)]


def _text_of(xml):
    return set(re.findall(r"\w{2,}", re.sub(r"<[^>]+>", " ", xml or "")))


def _rising(seq):
    """Indices of one longest strictly increasing subsequence of ``seq``."""
    import bisect
    tails, tails_i, prev = [], [], [-1] * len(seq)
    for i, v in enumerate(seq):
        j = bisect.bisect_left(tails, v)
        if j == len(tails):
            tails.append(v)
            tails_i.append(i)
        else:
            tails[j], tails_i[j] = v, i
        prev[i] = tails_i[j - 1] if j else -1
    out, i = [], tails_i[-1] if tails_i else -1
    while i >= 0:
        out.append(i)
        i = prev[i]
    return set(out)


def verify_order(presentation, cwd=None, repair=False):
    """Compare the deck's page order with .lark-slides/pages-<deck>.json using ONE ``slides +xml-get``.

    Returns ``{"ok", "slides", "missing", "misplaced", "duplicates", "unregistered", "no_xml", "repaired", "failed"}``:
      missing      – registered pages (numbers) whose slide is not in the deck (deleted / lost in a concurrent write)
      misplaced    – pages present but out of page-number order (outside the longest in-order run)
      duplicates   – {slide_id: [pages]}: one slide recorded for several pages (the server re-issued a deleted id)
      unregistered – slide ids in the deck that no page records (e.g. a cover written with raw +add-slide; left alone)
      no_xml       – missing / misplaced pages without a saved .lark-slides/xml/<deck>/pNN.xml (cannot be re-added)
    ``repair=True`` fixes missing / misplaced / duplicate pages under the deck lock with the same write path as
    publish_slide: each page is re-added at its page-number position from the saved XML (a misplaced page from its
    current deck content when available), then the misplaced old copy is deleted — only a slide the registry still
    maps to no other page. Never use raw +add-slide / +delete-slide for this. Run it once more afterwards to confirm.

    CLI (from skills/ppt):  python3 -m scripts.svg_lib.atomize_svg_to_slide._publish verify <deck> [--repair]
    Python:  from scripts.svg_lib.atomize_svg_to_slide._publish import verify_order; verify_order(deck, cwd, repair=True)
    """
    cwd = cwd or os.getcwd()
    deck = _deck_id(presentation)
    out = {"ok": False, "slides": 0, "missing": [], "misplaced": [], "duplicates": {}, "unregistered": [],
           "no_xml": [], "repaired": [], "failed": []}
    xml_dir = Path(cwd) / ".lark-slides" / "xml" / deck

    def saved(n):
        f = xml_dir / f"p{n:02d}.xml"
        return f.read_text(encoding="utf-8") if f.exists() else None

    with _deck_lock(cwd, deck):
        registry_path, registry = _page_registry(cwd, deck)
        res = _run(["slides", "+xml-get", "--as", "user", "--presentation", deck], cwd)
        checked = _check_task_deck(cwd, deck, res, registry, repair=repair)
        if checked.get("managed"):
            out.update(checked)
            out["slides"] = len(checked.get("ordered_slide_ids", []))
        if not checked["ok"]:
            return out
        if not isinstance(res, dict) or res.get("ok") is not True:
            out["error"] = str(res)[:500]
            return out
        slides = _deck_slides(res)
        order = [sid for sid, _ in slides]
        bodies = dict(slides)
        out["slides"] = len(order)
        pages = {int(k[1:]): v for k, v in registry.items() if re.fullmatch(r"p\d+", k)}
        by_sid = {}
        for n, sid in sorted(pages.items()):
            by_sid.setdefault(sid, []).append(n)
        dup = {sid: ns for sid, ns in by_sid.items() if len(ns) > 1}
        out["duplicates"] = dup
        owner = {}
        for sid, ns in by_sid.items():   # a shared slide belongs to the page whose saved text it matches best
            if len(ns) == 1 or sid not in bodies:
                owner[sid] = ns[0]
                continue
            have = _text_of(bodies[sid])
            owner[sid] = max(ns, key=lambda n: (len(have & _text_of(saved(n))), -n))
        pos = {sid: i for i, sid in enumerate(order)}
        missing = sorted(n for n, sid in pages.items() if sid not in pos or owner.get(sid) != n)
        present = sorted((pos[sid], n) for n, sid in pages.items() if n not in missing)
        keep = _rising([n for _, n in present])
        misplaced = sorted(n for i, (_, n) in enumerate(present) if i not in keep)
        out.update(missing=missing, misplaced=misplaced,
                   unregistered=[sid for sid in order if sid not in by_sid],
                   no_xml=[n for n in sorted(set(missing) | set(misplaced))
                           if saved(n) is None and not (n in misplaced and bodies.get(pages[n]))])
        out["ok"] = not (missing or misplaced or dup)
        if not repair or out["ok"]:
            return out
        if _exported(cwd, deck) is not None:
            out["error"] = "deck 已导出（SYNC/exported）：不再改页序"
            return out
        for n in missing:   # forget lost / shared records first so anchors only point at slides really in the deck
            if registry.get(f"p{n:02d}") is not None and owner.get(registry[f"p{n:02d}"]) != n:
                registry.pop(f"p{n:02d}")
            elif registry.get(f"p{n:02d}") not in pos:
                registry.pop(f"p{n:02d}", None)
        old_ids = {n: registry.pop(f"p{n:02d}") for n in misplaced}
        _save_registry(registry_path, registry)
        for n in sorted(set(missing) | set(misplaced), reverse=True):   # top down: each page's successor is in place
            old = old_ids.get(n)
            sources = ([re.sub(r'\s(?:id|slide_id)="[^"]*"', "", f'<slide xmlns="{_SML}">{bodies[old]}</slide>')]
                       if old and bodies.get(old) else []) + ([saved(n)] if saved(n) else [])
            r = {}
            for xml in sources:
                r = {"ok": True, "warnings": [], "summary": []}
                try:
                    _upload(r, xml, set(), {}, deck, None, None, n, False, set(), cwd, trusted=True,
                            owned_slide_ids=by_sid)
                except Exception as e:  # noqa: BLE001
                    r = {"ok": False, "errors": [str(e)]}
                if r.get("ok") and r.get("slide_id"):
                    break
            if not (r.get("ok") and r.get("slide_id")):
                if old:   # put the old record back: the page is still in the deck, only out of order
                    _, registry = _page_registry(cwd, deck)
                    registry[f"p{n:02d}"] = old
                    _save_registry(registry_path, registry)
                out["failed"].append({"page": n, "why": "无保存的 XML" if not sources else
                                      str((r.get("errors") or [r])[0])[:200]})
                continue
            _, registry = _page_registry(cwd, deck)
            if old and old != r["slide_id"] and old not in registry.values():
                d = _run(["slides", "+delete-slide", "--as", "user", "--presentation", deck, "--slide-id", old], cwd)
                if not d.get("ok") and not _gone(d):
                    out["failed"].append({"page": n, "why": f"新副本已插入，旧位置 {old} 未删掉：{str(d.get('error'))[:150]}"})
            out["repaired"].append(n)
    out["ok"] = not out["failed"]
    return out


def _main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(prog="python3 -m scripts.svg_lib.atomize_svg_to_slide._publish")
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("verify", help="compare deck order with pages-<deck>.json (one +xml-get); --repair fixes it")
    v.add_argument("deck")
    v.add_argument("--repair", action="store_true")
    v.add_argument("--cwd", default=None)
    a = ap.parse_args(argv)
    r = verify_order(a.deck, a.cwd, repair=a.repair)
    print(json.dumps(r, ensure_ascii=False))
    return 0 if r.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(_main())
