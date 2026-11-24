"""Turn a publish_slide refusal into lines the page author can act on (used by Frame.publish).

publish_slide reports server lint findings as described items ({"key", "code", "message", "objects", "fix"}) and
everything else as {"code": "upload_failed", "cli_code", "message", "fix"} (no "key"). Two traps this module closes:

* printing e.get("key") shows "None" for upload failures, and their generic fix says "不是排版问题" even when the
  message is in fact a lint report (error code 4000153, or a report wrapped in notices / truncated) — the author then
  cannot see that a line crosses a label and burns the page's refusal budget blind;
* a network / auth / parameter failure is not a layout problem and must not count toward that budget.
"""

from __future__ import annotations

import json
import re

LINT_CODE = "4000153"
_LINT_WORDS = re.compile(r"bbox_overlap|crosses (?:text|shape)|text_overflows_container|text_may_overflow_shape|"
                         r"text_color_contrast|out_of_(?:slide|canvas)|lint", re.I)


def _report_of(msg):
    """The lint report dict embedded in msg (a JSON string, possibly with leading/trailing noise), or None."""
    if isinstance(msg, dict):
        return msg
    s = str(msg or "")
    dec = json.JSONDecoder()
    for m in re.finditer(r"\{", s):
        try:
            obj, _ = dec.raw_decode(s, m.start())
        except ValueError:
            continue
        if isinstance(obj, dict) and any(k in obj for k in ("slides", "issues", "document", "errors")):
            if isinstance(obj.get("error"), dict):   # a whole CLI envelope
                inner = _report_of(obj["error"].get("message"))
                if inner:
                    return inner
            return obj
    return None


def report_issues(report):
    """Every blocking issue in a lint report (slides[].errors / issues, document.errors, top-level issues)."""
    out = []
    for sl in report.get("slides") or []:
        if isinstance(sl, dict):
            errs = sl.get("errors")
            if errs is None:
                errs = [i for i in sl.get("issues") or [] if isinstance(i, dict) and i.get("level", "error") == "error"]
            out += [e for e in errs or [] if isinstance(e, dict)]
    doc = report.get("document") or {}
    if isinstance(doc, dict):
        out += [e for e in doc.get("errors") or [] if isinstance(e, dict)]
    if not out:
        out += [e for e in report.get("errors") or report.get("issues") or []
                if isinstance(e, dict) and e.get("level", "error") == "error"]
    seen, uniq = set(), []
    for e in out:
        k = json.dumps(e, sort_keys=True, ensure_ascii=False, default=str)
        if k not in seen:
            seen.add(k)
            uniq.append(e)
    return uniq


def is_upload_failure(e):
    return isinstance(e, dict) and e.get("code") == "upload_failed"


def looks_like_lint(e):
    """An upload failure that is really a server lint refusal."""
    if not is_upload_failure(e):
        return False
    return (str(e.get("cli_code")) == LINT_CODE or _report_of(e.get("message")) is not None
            or bool(_LINT_WORDS.search(str(e.get("message") or ""))))


def normalise(errors, page_xml=""):
    """errors with every upload failure that hides a lint report replaced by described layout issues
    (key / code / message / objects / fix, same shape as publish_slide's own lint items)."""
    out = []
    for e in errors or []:
        if not looks_like_lint(e):
            out.append(e)
            continue
        rep = _report_of(e.get("message"))
        issues = report_issues(rep) if rep else []
        if not issues:   # lint words but no parseable report: keep the raw text, but as a layout issue
            out.append({"key": "server_lint", "code": "server_lint", "message": str(e.get("message") or "")[:400],
                        "fix": simpler(str(e.get("message") or "")), "layout": True})
            continue
        described = None
        if page_xml:
            try:
                from ..atomize_svg_to_slide._exhibit_publish import _describe, _children
                gen = set(range(len(_children(page_xml))))
                described = [_describe(page_xml, i, gen) for i in issues]
            except Exception:  # noqa: BLE001 — fall back to the raw issue fields
                described = None
        for k, i in enumerate(issues):
            d = dict(described[k]) if described else {"code": i.get("code"), "message": i.get("message"),
                                                      "objects": [{"path": p} for p in i.get("elements") or []]}
            d.setdefault("key", f"{i.get('code')}:{'+'.join(i.get('elements') or [])}")
            d["hint"] = d.get("hint") or i.get("hint")
            d["fix"] = d.get("fix") or simpler(f"{i.get('code')} {i.get('message')}")
            d["layout"] = True
            out.append(d)
    return out


def is_layout(e):
    """True for a refusal caused by what is on the page (server lint, or a lint report hidden in an upload failure)."""
    if not isinstance(e, dict):
        return False
    if e.get("layout"):
        return True
    if is_upload_failure(e):
        return looks_like_lint(e)
    return True


def _objects(e):
    parts = []
    for o in e.get("objects") or []:
        if not isinstance(o, dict):
            continue
        what = o.get("element") or o.get("path") or ""
        if o.get("text"):
            what += f"「{o['text'][:16]}」"
        box = o.get("xml_line") or o.get("xml_box")
        if box:
            what += f"@{box}"
        if what:
            parts.append(what)
    return " × ".join(parts[:2])


def line(e):
    """One printable line: key-or-code | message | elements | fix (or hint)."""
    if not isinstance(e, dict):
        return str(e)[:200]
    key = e.get("key") or e.get("code") or "error"
    if is_upload_failure(e) and not is_layout(e):
        key = f"upload_failed(cli {e.get('cli_code')})"
    bits = [str(key)[:60]]
    msg = str(e.get("message") or "")
    if msg and not _report_of(msg):
        bits.append(msg[:110])
    obj = _objects(e)
    if obj:
        bits.append(obj)
    fix = e.get("fix") or e.get("hint")
    if fix and not (is_upload_failure(e) and is_layout(e)):
        bits.append("→ " + str(fix)[:150])
    elif e.get("hint"):
        bits.append("→ " + str(e["hint"])[:150])
    return " | ".join(bits)


def simpler(text):
    """A concrete, simpler construction for the kind of finding named in text."""
    t = str(text or "")
    if "crosses text" in t:
        return ("线穿过文字：删掉被穿过的标签，或把它挪到线的一侧（callout prefer= / 数值 values=False）；"
                "参考线/网格线可去掉（show_grid=False / 不画 ref_y）")
    if "crosses shape" in t:
        return "线穿过色块：show_grid=False，参考线/分隔线放到柱外侧，或去掉这条线"
    if "overflow" in t:
        return "文字超出底框：缩短文字、放大底框，或去掉柱内数值（values=False）"
    if "contrast" in t:
        return "对比度不足：标签挪离深色线/色块，或深底上用白字"
    if "out_of" in t:
        return "出界：把元素放进 960×540 内（减小 x/y 或 Exhibit 宽高）"
    if "bbox_overlap" in t:
        return "两个元素相压：删掉其中一个标签（values=False 只留首尾值），或减少类别/系列"
    return "删掉报错的标签/说话框，或换成同一比较关系的 row_table（Label + Bar/Text 列）"


def stop_message(errors, blocks):
    """Hard-stop text: which issues remain on the page and the one simpler construction to use — never a bypass."""
    lay = [e for e in errors or [] if is_layout(e)]
    rem = "；".join(dict.fromkeys(line(e) for e in lay[:4])) or "（最后一次的报错见上）"
    ways = list(dict.fromkeys(simpler(f"{e.get('code')} {e.get('message')}") for e in lay[:4]))
    return (f"这页已被服务端 lint 拦 {blocks} 次，publish 不再接受同一构造。仍未解决：{rem}。"
            f"改法（选一个，一次改到位）：{' / '.join(ways) or simpler('')}；"
            "或整页换成 row_table（Label + Bar/Text 列）一次写入。"
            "不要直接调用 publish_slide / lark-cli 绕过——它们走同一个服务端 lint，只会被同样拦下，且跳过本地检查。")
