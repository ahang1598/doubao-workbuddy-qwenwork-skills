"""Optional, JSON-safe conversion observations; never changes the output XML."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from ._bounds import svg_bounds


def _native_font_policy(item, observed):
    """Combine decision observations with the actual serialized native sizes."""
    if not observed or item.tag.split("}")[-1] != "shape" or item.get("type") != "text":
        return None
    content = item.find("content")
    if content is None or content.get("fontSize") is None:
        return None
    result = dict(observed)
    result["actual_sml_font_size"] = float(content.get("fontSize"))
    if "runs" in observed:
        spans = list(content.iter("span"))
        if len(spans) == len(observed["runs"]):
            result["runs"] = [
                dict(run, actual_sml_font_size=float(span.get("fontSize")))
                for run, span in zip(observed["runs"], spans)
            ]
        else:
            # Do not guess a run-to-output match if a future converter changes it.
            result["run_mapping_complete"] = False
    return result


def record_atom(report, metadata, source, defs, fragment, viewport, *, font_policy=None):
    outputs = list(ET.fromstring("<data>" + fragment + "</data>"))
    native = sum(e.tag.split("}")[-1] != "embed" for e in outputs)
    svg_count = len(outputs) - native
    decision = "mixed" if native and svg_count else "svg" if svg_count else "native" if native else "omitted"
    reason = metadata["reason"]
    if reason == "native_candidate":
        reason = {
            "svg": "converter_fallback",
            "mixed": "partial_converter_fallback",
            "native": "native_geometry",
            "omitted": "no_visible_output_or_drop_policy",
        }[decision]
    element = ET.fromstring(source)
    features = sorted(
        {
            k
            for n in element.iter()
            for k in (
                "filter",
                "mask",
                "clip-path",
                "marker-start",
                "marker-mid",
                "marker-end",
                "stroke-dasharray",
                "transform",
                "fill-rule",
            )
            if n.get(k) not in (None, "none", "")
        }
    )
    features += sorted(
        {key + "_resource" for n in element.iter() for key in ("fill", "stroke") if "url(" in n.get(key, "")}
    )
    preservation = {}
    if reason == "group: Group compositing" and svg_count:
        triggers = []
        for node in element.iter():
            if node.tag.split("}")[-1] not in ("g", "svg"):
                continue
            attrs = {
                key: node.get(key)
                for key in ("opacity", "filter", "clip-path", "mask", "mix-blend-mode", "isolation")
                if node.get(key) not in (None, "", "none", "normal", "auto")
                and (key != "opacity" or float(node.get(key)) != 1)
            }
            if attrs:
                triggers.append({"source_id": node.get("id"), "attributes": attrs})
                if "opacity" in attrs:
                    features.append("group_opacity")
        preservation = {
            "reason_category": "fidelity_preservation",
            "compositing_triggers": triggers,
            "reason_note": "已转换为 SVG 单元，保留分组透明度或效果的共同合成；"
            "不应仅为消除 embed 删除效果。内部编辑粒度不同，边界与画面仍按实际结果判断。",
        }
    elif reason == "expansion: Nonuniform scaling or skew needs SVG compositing" and svg_count:
        preservation = {
            "reason_category": "fidelity_preservation",
            "reason_note": "已单独保留此元素的非等比或斜切变换及描边、文字外观；"
            "该 SVG 单元可独立选择，转换已完成。不要仅为变成原生形状重写整幅图。",
        }
    features = sorted(set(features))
    evidence = {}
    if svg_count:
        svg_bounds(element, defs, viewport, diagnostics=evidence)
    details = []
    output_start = report["output_count"]
    for i, item in enumerate(outputs):
        tag = item.tag.split("}")[-1]
        if tag == "line":
            x1, y1, x2, y2 = (float(item.get(k)) for k in ("startX", "startY", "endX", "endY"))
            box = [min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1)]
        else:
            box = [float(item.get(k, "0")) for k in ("topLeftX", "topLeftY", "width", "height")]
        output = {"index": output_start + i, "type": item.get("type", tag), "selection_bounds": box}
        observed_font = _native_font_policy(item, font_policy)
        if observed_font is not None:
            output["font_policy"] = observed_font
        details.append(output)
    report["objects"].append(
        {
            "atom_index": len(report["objects"]),
            "source_ids": metadata["source_ids"],
            "source_tag": element.tag.split("}")[-1],
            "decision": decision,
            "reason": reason,
            "features": features,
            "native_count": native,
            "svg_count": svg_count,
            "outputs": details,
            "bounds_evidence": evidence or None,
            "source_viewport_fallback": bool(svg_count and evidence.get("status") == "unknown"),
            **preservation,
        }
    )
    report["output_count"] += len(outputs)


def inspect_svg(svg_path, *, object_ids=None):
    """Return conversion choices/boxes and native font policies for selected IDs."""
    from ._atomizer import atomize_svg_to_slide

    if object_ids is not None:
        if isinstance(object_ids, str):
            object_ids = (object_ids,)
        selected = set(object_ids)
        if not all(isinstance(key, str) for key in selected):
            raise TypeError("object_ids must contain strings")
    report = {}
    atomize_svg_to_slide(Path(svg_path), diagnostics=report)
    if object_ids is not None:
        report["objects"] = [o for o in report["objects"] if selected.intersection(o["source_ids"])]
        found = {key for o in report["objects"] for key in o["source_ids"]}
        report["unmatched_ids"] = sorted(selected - found)
        report["requested_ids"] = sorted(selected)
    report["scope"] = "selected" if object_ids is not None else "all"
    return report
