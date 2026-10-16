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
    proc = subprocess.run(["lark-cli", *args], capture_output=True, text=True, cwd=cwd, timeout=180)
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
    embeds = [box(kids[i]) for i in generated_ids if kids[i].tag.endswith("embed") and box(kids[i])]

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
            # Text pressed on text is a real collision even inside generated output.
            texts = [el for _, el in hits if el.tag.endswith("shape") and el.get("type") == "text"]
            if code == "bbox_overlap" and len(texts) >= 2:
                report.append(err)
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
    if unwrapped:
        out["unwrapped_text"] = unwrapped
        out["fix"] = unwrapped["fix"]
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
        import color_contrast_check as cc

        records, slides = cc.parse_xml_root(ET.fromstring(page_xml))
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
    page_bg = (slides.get(1) or {}).get("page_bg") or "rgb(255,255,255)（默认白底）"
    out = {
        "text": worst["text"][:40],
        "text_color": worst.get("effective_fg_color") or worst["fg_color"],
        "background": worst.get("effective_bg_color"),
        "ratio": round(worst["contrast"], 2),
        "required": round(worst.get("required_contrast") or cc.DEFAULT_CONTRAST_GATE, 2),
        "under_text": under[:3] or [{"element": "页面背景", "color": page_bg}],
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
        from xml_lint import estimate_text_width

        bold = 'bold="true"' in ET.tostring(el, encoding="unicode")
        return max(estimate_text_width(line, size, 0, bold) for line in text.split("\n"))
    except Exception:  # noqa: BLE001 — a rough estimate is enough for the hint
        return max(sum(size if ord(c) > 0x2E80 else size * 0.55 for c in line) for line in text.split("\n"))


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
        need = max(need, lint_w)
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
                "两段图内文字互压：图被缩得太小，标签字号被抬到下限后挤在一起。把该图的框（chart_slide 的 width/height 或 "
                "to_slide 的 width）加大，或减少类别注释/中心文字/图例行数；不要逐个挪生成的文字。"
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
                f"文字框 {text['xml_box']} 超出底框 {box['xml_box']}（{sides}）：把底框改成 "
                f"[{nx:.0f}, {ny:.0f}, {nw:.0f}, {nh:.0f}]，或把文字框缩进底框内。"
            )
        return f"文字超出其底框（{sides}）：加大底框或缩短/缩小文字，让文字框完全落在底框内。"
    if code in ("text_may_overflow_shape",):
        return "文字放不下：先 fit_text_boxes(page_xml) 自动加高，仍超出则加宽或删减文字。"
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


def _prepare(page_xml):
    """Fix the mechanical rejections of hand-written page XML before the first write."""
    import sys

    scripts = str(Path(__file__).resolve().parents[2])
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    from text_fit import fit_text_boxes

    page_xml = _with_sml_namespace(
        _BARE_AMP.sub("&amp;", page_xml)
    )  # "Smith & Jones" in a source line is the classic parse error
    return fit_text_boxes(_native_fixes(page_xml))


def _page_registry(cwd, presentation):
    path = Path(cwd) / ".lark-slides" / f"pages-{presentation}.json"
    try:
        return path, json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return path, {}


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
    ``waive`` lists ``errors[i]["key"]`` values judged to be false positives: when every remaining finding is
    waived the page is written without lint and always screenshotted for a visual check.
    """
    notes = []
    page_xml, pasted = _lift_pasted_fragments(_with_sml_namespace(page_xml))
    if pasted:
        notes.append(f"page_xml 里拼进了 {len(pasted)} 个生成片段，已按片段处理；下次{_PASTED_HINT}")
        fragments = (*pasted, *fragments)
    page_xml, fit_warnings = _prepare(page_xml)
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
    if save_as:
        Path(save_as).write_text(xml, encoding="utf-8")
    if not presentation:
        result["summary"] = notes
        return result
    try:
        return _upload(
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
        )
    finally:
        result["summary"] = notes + list(result.get("summary") or [])
        for key, label in (("screenshot", "截图已保存"), ("preview", "预览图已保存")):
            if result.get(key):
                result["summary"].append(f"{label}：{result[key]}（以此路径为准，扩展名可能被改为 .jpg）")


def _upload(result, xml, generated, origins, presentation, slide_id, before_slide_id, page, screenshot, waive, cwd):
    cwd = cwd or os.getcwd()
    registry_path, registry = _page_registry(cwd, presentation)
    page_key = None if page is None else (f"p{int(page):02d}" if str(page).isdigit() else str(page))
    if page_key and not slide_id and page_key in registry:
        slide_id = registry[page_key]
    if page_key and not slide_id and not before_slide_id:
        later = sorted(k for k in registry if k > page_key)
        if later:
            before_slide_id = registry[later[0]]
    out_dir = ".lark-slides/screenshots/publish"
    os.makedirs(os.path.join(cwd, out_dir), exist_ok=True)
    fd, tmp = tempfile.mkstemp(suffix=".xml", dir=cwd)
    os.close(fd)
    Path(tmp).write_text(xml, encoding="utf-8")
    rel = os.path.relpath(tmp, cwd)
    try:

        def send(no_lint):
            if slide_id:
                args = [
                    "slides",
                    "+update-slide",
                    "--as",
                    "user",
                    "--presentation",
                    presentation,
                    "--slide-id",
                    slide_id,
                    "--content",
                    f"@{rel}",
                ]
            else:
                args = ["slides", "+add-slide", "--as", "user", "--presentation", presentation, "--slide", f"@{rel}"]
                if before_slide_id:
                    args += ["--before-slide-id", before_slide_id]
            return _run(args + (["--no-lint"] if no_lint else []), cwd)

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
                return result
            ignorable, report_errs = _classify(xml, generated, errors)
            result["ignored"] = len(ignorable)
            described = [_describe(xml, e, generated, origins) for e in report_errs]
            left = [d for d in described if d["key"] not in waive]
            if left:
                real = [d for d in left if "不是误报" in (d.get("fix") or "")]
                maybe = [d for d in left if d not in real]
                result.update(
                    ok=False,
                    errors=left,
                    summary=_summarize(left)
                    + ([_WAIVE_HINT.format(keys=", ".join(repr(d["key"]) for d in maybe))] if maybe else []),
                )
                if screenshot:
                    result["preview"] = _screenshot(
                        ["--content", f"@{rel}"], cwd, out_dir, f"preview-{int(time.time() * 1000)}"
                    )
                return result
            res = send(True)
            result["no_lint"] = True
            if described:
                screenshot = True
                result["waived"] = [d["key"] for d in described]
                waived_lines = [f"  - p{page or ''} {d['code']}：{d.get('message') or ''}"[:160] for d in described]
                result["summary"] = [
                    f"已按 waive 跳过 {len(described)} 条 lint 强行写入：必须 Read 返回的 screenshot 确认这些位置"
                    "没有真遮挡/截断/低对比；确有问题就修好后不带 waive 重提。",
                    "注意：服务端不会记住这次豁免。Step 8 回读（+xml-get）后用 lint_inspect.py 查看报告时，下面这些"
                    "条目还会原样出现在报告里（同一页、同一 code、同样的对象文字）——它们是这里已经截图确认过的误报，"
                    "不要回头再改这一页，也不要因此判定该页未通过；在验证记录里注明“已 waive 并截图确认”即可：",
                    *waived_lines,
                ]
            if not res.get("ok"):
                result.update(ok=False, errors=failure(res))
                return result
        sid = (res.get("data") or {}).get("slide_id") or slide_id or ""
        result["slide_id"] = sid
        if page_key and sid:
            registry[page_key] = sid
            registry_path.parent.mkdir(parents=True, exist_ok=True)
            registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=1), encoding="utf-8")
        if screenshot and sid:
            result["screenshot"] = _screenshot(
                ["--presentation", presentation, "--slide-id", sid], cwd, out_dir, f"{sid}-{int(time.time())}"
            )
        return result
    finally:
        os.unlink(tmp)
