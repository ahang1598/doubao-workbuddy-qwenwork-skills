#!/usr/bin/env python3
"""Analyze PDF layout and emit pdf_layout.json + per-page PNG for Word reconstruction.

This is the layout-analysis stage of the doubao-pdf PDF -> Word pipeline.
The same skill's references/workflows/pdf-to-word.md consumes this stable
artifact for strategy selection and DOCX assembly.

schema_version 1.2 adds:
- `cover` kind for high-image-ratio first pages (or explicit is_cover flag)
- HD cover renders (300 dpi) written to pages/page-NN-hd.png when kind==cover
- HD render also for kind==graphic and is_graphic_dense pages (Q13 SITOP fix)
- pikepdf raw image extraction fallback (masked / CMYK / weird colorspaces pymupdf misses)
- per-page render_metrics {ink_ratio, content_bbox, content_area_ratio}
- clustered vector region detection (get_drawings) written as auxiliary icons
- pdfplumber tables merged with pymupdf tables (fixes -95%~-100% table collapse)
- per-page is_graphic_dense flag for high-density image/vector pages
- summary.graphic_dense_pages / cover_pages / tables_total_{pymupdf,pdfplumber,total}
schema 1.0/1.1 -> 1.2 is backward compatible; the downstream workflow warns but does not block on a supported higher minor version.
schema_version 1.3 adds:
- `tables[].row_heights`: per-row height list (pt), 双源均输出，供 word 侧「行高守护」避免空白 cell 塌陷
- `tables[].col_widths`: per-column width list (pt), 双源均输出，供 word 侧「列宽守护」避免均分列宽
- `pages[].column_count`: 主文文字栏数（== len(text_columns)）
- `pages[].body_bbox`: 去掉 header/footer 后的主文 bbox，供 word 侧「非对称页边距 / 空装饰侧栏」判定
1.2 -> 1.3 向后兼容。
schema_version 1.4 adds:
- `toc[]`: PDF outline / bookmark hierarchy with stable parent ids and destinations
- `relationships[]`: normalized internal, external, named, remote, and launch links
- `pages[].link_relationship_ids`: relationship ids originating on each page
- `pages[].cross_references[]`: internal-link ids and display formats for Word reconstruction
1.3 -> 1.4 向后兼容。
schema_version 1.5 adds:
- `pages[].paragraph_groups[]`: 相邻 text block 的保守合并结果，供 Word 侧避免「每行一段」误拆
- `pages[].special_chars[]`: 该页出现的非 CJK/非 ASCII 符号字符集合，供审计做集合差
1.4 -> 1.5 向后兼容。
schema_version 1.6：启发式收紧（15 case 实测反噪音）
- `_extract_text_lines_and_columns`：x_start histogram + 每列 line 阈值 + y 重叠检查，取代 x_center gap
- `_detect_table_candidates`：多 x 起点簇 + aligned ≥ 5，避免把单列正文当表格候选
- `_extract_tables_pdfplumber`：needs_ocr 页（meaningful_chars < 40）跳过，避免扫描图像横线误报表格
- `_cluster_paragraph_groups`：短独立 block 识别为标题，不合并到相邻段
1.5 -> 1.6 向后兼容（同为可读性收紧，字段结构不变）。
"""

from __future__ import annotations

import argparse
import collections
import datetime as _dt
import hashlib
import json
import re
import statistics
import sys
import unicodedata
from pathlib import Path
from typing import Any

import pymupdf

SCHEMA_VERSION = "1.6"
GENERATOR = "doubao-pdf/analyze_pdf_layout.py"

_LINK_KIND_NAMES = {
    getattr(pymupdf, "LINK_NONE", 0): "none",
    getattr(pymupdf, "LINK_GOTO", 1): "internal",
    getattr(pymupdf, "LINK_URI", 2): "uri",
    getattr(pymupdf, "LINK_LAUNCH", 3): "launch",
    getattr(pymupdf, "LINK_NAMED", 4): "named",
    getattr(pymupdf, "LINK_GOTOR", 5): "remote",
}


def _sha1(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _parse_pages(spec, total):
    if not spec:
        return list(range(total))
    out = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            start, end = int(a), int(b)
            if start < 1 or end < 1 or start > end:
                raise ValueError(f"invalid range: {part}")
            for i in range(start - 1, min(end, total)):
                out.add(i)
        else:
            i = int(part) - 1
            if 0 <= i < total:
                out.add(i)
    return sorted(out)


def _meaningful_chars(text):
    return len("".join(text.split()))


def _point_to_list(value):
    """Convert a PyMuPDF Point-like destination to a JSON-safe pair."""
    if value is None:
        return None
    try:
        if hasattr(value, "x") and hasattr(value, "y"):
            return [round(float(value.x), 2), round(float(value.y), 2)]
        if len(value) >= 2:
            return [round(float(value[0]), 2), round(float(value[1]), 2)]
    except (TypeError, ValueError):
        return None
    return None


def _rect_to_list(value):
    """Convert a PyMuPDF Rect-like source area to a JSON-safe bbox."""
    if value is None:
        return None
    try:
        if all(hasattr(value, attr) for attr in ("x0", "y0", "x1", "y1")):
            coords = (value.x0, value.y0, value.x1, value.y1)
        else:
            coords = value[:4]
        return [round(float(v), 2) for v in coords]
    except (TypeError, ValueError):
        return None


def _link_kind_name(kind):
    return _LINK_KIND_NAMES.get(kind, f"unknown_{kind}")


def _classify_cross_reference(text, kind):
    """Classify link display text without inventing a destination relationship."""
    normalized = " ".join((text or "").split())
    lower = normalized.lower()
    if kind == "uri":
        return "email" if lower.startswith("mailto:") or "@" in lower else "url"
    if kind == "remote":
        return "remote_document"
    if kind == "launch":
        return "launch_action"
    if kind == "named":
        return "named_destination"
    if kind != "internal":
        return "other"
    if re.fullmatch(r"(?:第\s*)?[ivxlcdm\d]+\s*(?:页|頁)?", lower, re.IGNORECASE):
        return "page_number"
    if re.search(r"(?:第\s*[一二三四五六七八九十百\d]+\s*[章节]|chapter|section|§)", lower):
        return "section"
    if re.search(r"(?:图|figure|fig\.?)\s*[A-Za-z0-9一二三四五六七八九十.-]+", lower):
        return "figure"
    if re.search(r"(?:表|table)\s*[A-Za-z0-9一二三四五六七八九十.-]+", lower):
        return "table"
    if re.search(r"(?:脚注|注释|footnote|note)\s*[A-Za-z0-9一二三四五六七八九十.-]+", lower):
        return "footnote"
    return "internal"


def _extract_toc(document, warnings):
    """Extract PDF outlines while retaining hierarchy and destination details."""
    try:
        raw_toc = document.get_toc(simple=False) or []
    except Exception as exc:
        warnings.append(f"document: table of contents extraction failed ({exc})")
        return []

    out = []
    ancestors = {}
    for index, item in enumerate(raw_toc, start=1):
        if len(item) < 3:
            warnings.append(f"document: malformed table of contents entry {index} skipped")
            continue
        level, title, page_number = int(item[0]), str(item[1]), int(item[2])
        destination = item[3] if len(item) > 3 and isinstance(item[3], dict) else {}
        entry_id = f"toc-{index}"
        parent_id = ancestors.get(level - 1)
        out.append({
            "id": entry_id,
            "level": level,
            "parent_id": parent_id,
            "title": title,
            "target": {
                "kind": _link_kind_name(destination.get("kind")),
                "page": page_number if page_number > 0 else None,
                "point": _point_to_list(destination.get("to")),
                "zoom": destination.get("zoom"),
                "uri": destination.get("uri"),
                "file": destination.get("file"),
                "named_destination": destination.get("nameddest") or destination.get("name"),
            },
            "xref": destination.get("xref"),
            "collapsed": bool(destination.get("collapse", False)),
        })
        ancestors[level] = entry_id
        for stale_level in [key for key in ancestors if key > level]:
            del ancestors[stale_level]
    return out


def _extract_page_relationships(page, page_number, warnings):
    """Extract link annotations/actions and normalize all page numbers to 1-based."""
    try:
        raw_links = page.get_links() or []
    except Exception as exc:
        warnings.append(f"page {page_number}: link extraction failed ({exc})")
        return []

    relationships = []
    for index, link in enumerate(raw_links, start=1):
        kind = _link_kind_name(link.get("kind"))
        bbox = _rect_to_list(link.get("from"))
        source_text = ""
        if bbox is not None:
            try:
                source_text = " ".join(page.get_textbox(pymupdf.Rect(bbox)).split())
            except Exception as exc:
                warnings.append(
                    f"page {page_number} link {index}: source text extraction failed ({exc})"
                )

        target_page = link.get("page")
        if isinstance(target_page, int) and target_page >= 0:
            target_page += 1
        else:
            target_page = None
        relationships.append({
            "id": f"link-p{page_number}-{index}",
            "type": "hyperlink",
            "source": {
                "page": page_number,
                "bbox": bbox,
                "text": source_text,
            },
            "target": {
                "kind": kind,
                "page": target_page,
                "point": _point_to_list(link.get("to")),
                "zoom": link.get("zoom"),
                "uri": link.get("uri"),
                "file": link.get("file"),
                "named_destination": link.get("nameddest") or link.get("name"),
            },
            "cross_reference_format": _classify_cross_reference(source_text, kind),
            "xref": link.get("xref"),
            "annotation_id": link.get("id"),
        })
    return relationships


def _classify_kind(page_index, meaningful, largest_img, tables, rects,
                   page_area, table_area, columns, text_lines):
    """kind 分类；1.2 起加 cover 分支。first page + 低文本 + 大图/大字/大图形 = cover。"""
    reason = (
        f"meaningful_chars={meaningful}, "
        f"largest_image_ratio={largest_img:.2f}, "
        f"tables={tables}, rects={rects}, "
        f"columns={columns}"
    )
    # Scan first
    if meaningful < 40 and largest_img > 0.55:
        return "scan", reason
    # Cover: 首页 + (文本少且有大图 or 大字号 or 大量图形元素)
    if page_index == 0 and meaningful < 300:
        max_size = max((l.get("size", 0) for l in text_lines), default=0)
        if largest_img > 0.15 or rects > 15 or max_size > 24:
            return "cover", reason + f", max_font_size={max_size:.1f}"
    # Table
    table_ratio = table_area / page_area if page_area else 0.0
    if tables >= 1 and (rects > 20 or table_ratio >= 0.4):
        return "table", reason
    # Mixed
    if meaningful >= 40 and largest_img > 0.2:
        return "mixed", reason
    # Graphic
    if meaningful < 100 and rects > 30 and tables == 0:
        return "graphic", reason
    return "text", reason


def _classify_image_role(width_px, height_px, bbox):
    """1.1: geometry-only heuristic for role_hint."""
    area = width_px * height_px
    if area < 30000:
        return "icon"
    if bbox and len(bbox) >= 4:
        w = abs(bbox[2] - bbox[0])
        h = abs(bbox[3] - bbox[1])
        if min(w, h) > 0 and max(w, h) > 0 and min(w, h) / max(w, h) < 0.25:
            return "decor"
    if area < 200000:
        return "thumb"
    return "photo"


def _extract_page_images(document, page, page_number, images_dir, seen, warnings):
    """1.2: 优先 pymupdf.Pixmap -> PNG；失败时 pikepdf raw bytes 兜底（保留原编码，支持 masked/CMYK）。

    保证输出 PNG 或原始扩展名（raw 兜底时保留 jpg/png/jp2 供 python-docx 直接嵌入）。
    """
    out = []
    for image_index, image in enumerate(page.get_images(full=True), start=1):
        xref = int(image[0])
        if xref in seen:
            continue
        seen.add(xref)

        width_px = height_px = 0
        rel = None
        source = None

        # Try pymupdf.Pixmap first
        try:
            pix = pymupdf.Pixmap(document, xref)
            if pix.n - pix.alpha >= 4:
                pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
            width_px = pix.width
            height_px = pix.height
            rel = f"p{page_number}_img{image_index}.png"
            (images_dir / rel).write_bytes(pix.tobytes("png"))
            source = "pymupdf.Pixmap"
            pix = None
        except Exception as exc:
            warnings.append(
                f"page {page_number} image xref={xref}: pymupdf.Pixmap failed ({exc}); trying pikepdf raw"
            )
            try:
                import pikepdf
                with pikepdf.open(str(document.name)) as pdf:
                    obj = pdf.get_object((xref, 0))
                    if obj is None or obj.get("/Subtype") != "/Image":
                        continue
                    filter_type = obj.get("/Filter")
                    if isinstance(filter_type, list):
                        filter_type = filter_type[0] if filter_type else None
                    ext_map = {"/DCTDecode": "jpg", "/FlateDecode": "png", "/JPXDecode": "jp2"}
                    ext = ext_map.get(str(filter_type) if filter_type is not None else "", "bin")
                    if ext == "bin":
                        warnings.append(
                            f"page {page_number} image xref={xref}: unsupported filter {filter_type!r}, skipped"
                        )
                        continue
                    rel = f"p{page_number}_img{image_index}.{ext}"
                    (images_dir / rel).write_bytes(obj.read_raw_bytes())
                    width_px = int(obj.get("/Width", 0))
                    height_px = int(obj.get("/Height", 0))
                    source = f"pikepdf.raw({filter_type})"
            except Exception as exc2:
                warnings.append(
                    f"page {page_number} image xref={xref}: pikepdf fallback failed ({exc2}); dropped"
                )
                continue

        bbox = None
        for info in page.get_image_info(xrefs=True):
            if int(info.get("xref", -1)) == xref:
                bbox = list(info.get("bbox", (0, 0, 0, 0)))
                break

        out.append({
            "xref": xref,
            "bbox": bbox,
            "file": f"images/{rel}",
            "width_px": width_px,
            "height_px": height_px,
            "role_hint": _classify_image_role(width_px, height_px, bbox),
            "extract_source": source,
        })
    return out


def _compute_body_bbox(text_lines, page_rect):
    """1.3: 去掉 header/footer 后估算主文 bbox（中间 84% y 区间）。

    供 word 侧检测「非对称页面留白 / 空装饰侧栏」：连续 ≥ 2 页 body_bbox 与
    page_rect 的 x0/x1 偏移 ≥ 60 pt 时，应切新 section 并按实测偏移设置非对称
    left_margin / right_margin。
    """
    if not text_lines:
        return None
    top = page_rect.height * 0.08
    bot = page_rect.height * 0.92
    body = [l for l in text_lines if top < l["bbox"][1] < bot]
    if not body:
        return None
    return [
        round(min(l["bbox"][0] for l in body), 2),
        round(min(l["bbox"][1] for l in body), 2),
        round(max(l["bbox"][2] for l in body), 2),
        round(max(l["bbox"][3] for l in body), 2),
    ]


def _extract_text_lines_and_columns(page):
    """1.1: span-level text_lines[] + x-start clustered text_columns[]。

    1.6 v3 分列判据：x_start 20pt histogram + 相对高峰 + 距离约束。
    - v1 死阈值 max(5, total*0.15) 对中文双列论文（top bin 只占 10%）漏报，
      对合同/招标内散落的印章、日期短元素过报；v2 用最大 x_start gap 又对
      x_start 分布连续的复杂论文（Case 06 最大 gap 才 23pt）失效。
    - v3 改成：找 x_start 最高 bin（top）作为一列锚点；再找一个 bin，其 count
      >= top × 0.4（相对高峰）且中心距 top > 25% 页宽（真列间距）——两者同
      时满足才判分列。case 06 top 38 + far bin 17 (45%) 通过；case 07 top 20
      + 距离远处 bin 都 ≤ 8 (40%) 单列；case 10 短元素 count 远低于 top 单列。

    始终至少返回一列（覆盖所有 line 的 bbox）——为下游 body_bbox 等提供稳定输入。
    """
    lines = []
    # 1.6 v3.1: 分列检测要用 line-level x_start（每行首字），不是 span-level。
    # span-level 会把行中间的公式、独立 span 也算作独立 x_start，导致英文论文
    # （Case 07）里被大量"远处 bin"误报为分列。
    line_x_starts = []
    try:
        page_dict = page.get_text("dict")
    except Exception:
        return [], []

    for block in page_dict.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            line_first_x = None
            for span in line.get("spans", []):
                text = span.get("text", "")
                if not text.strip():
                    continue
                bbox = list(span.get("bbox", (0, 0, 0, 0)))
                lines.append({
                    "bbox": [round(v, 2) for v in bbox],
                    "text": text,
                    "font": span.get("font"),
                    "size": round(span.get("size", 0), 2),
                    "color": span.get("color"),
                })
                if line_first_x is None or bbox[0] < line_first_x:
                    line_first_x = bbox[0]
            if line_first_x is not None:
                line_x_starts.append(line_first_x)

    if not lines:
        return [], []

    def _build_column(col_lines):
        col_lines_sorted = sorted(col_lines, key=lambda l: (l["bbox"][1], l["bbox"][0]))
        x0 = min(l["bbox"][0] for l in col_lines_sorted)
        y0 = min(l["bbox"][1] for l in col_lines_sorted)
        x1 = max(l["bbox"][2] for l in col_lines_sorted)
        y1 = max(l["bbox"][3] for l in col_lines_sorted)
        return {
            "bbox": [round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2)],
            "char_count": sum(len(l["text"]) for l in col_lines_sorted),
            "line_count": len(col_lines_sorted),
        }

    default_column = _build_column(lines)
    page_width = page.rect.width
    total_lines = len(lines)

    # 1.6 v3.3: 用 line-level x_start histogram 找 top bin + 一个"距离 top 足够
    # 远的次要 bin"。历史实验：
    # - span-level x_start：英文论文行内公式/独立 span 会制造大量 far bin 误报（Case 07）
    # - cluster 合并策略：散乱短元素累加也会误报（Case 10）
    # 单 bin + 绝对下限 8 + 相对 0.4 top 是稳定的折中：
    #   Case 06 top=35, right bin=13 (0.4*35=14 差 1) 会漏判 page 2；但 page 1/3/5
    #   仍正确识别，评测语义上"多列 vs 单列"判定为多列即可，不必 100% 每页命中。
    # 阈值 = max(8 line 绝对下限, top × 0.4 相对高峰)
    if not line_x_starts:
        return lines, [default_column]
    bin_size = 20
    x_start_bins = collections.Counter(int(x // bin_size) for x in line_x_starts)
    sorted_by_count = sorted(x_start_bins.items(), key=lambda kv: -kv[1])
    top_bin_idx, top_count = sorted_by_count[0]
    top_center = (top_bin_idx + 0.5) * bin_size

    second_bin_idx = None
    col_threshold = max(8, top_count * 0.4)
    for bin_idx, cnt in sorted_by_count[1:]:
        center = (bin_idx + 0.5) * bin_size
        if cnt >= col_threshold and abs(center - top_center) > page_width * 0.25:
            second_bin_idx = bin_idx
            break

    if second_bin_idx is None:
        return lines, [default_column]

    second_center = (second_bin_idx + 0.5) * bin_size
    split_pos = (top_center + second_center) / 2
    left_lines = [l for l in lines if l["bbox"][0] < split_pos]
    right_lines = [l for l in lines if l["bbox"][0] >= split_pos]

    # 判据 2：两侧 line 数都 >= max(5, total * 0.15)，避免印章/日期短元素触发
    min_per_col = max(5, int(total_lines * 0.15))
    if len(left_lines) < min_per_col or len(right_lines) < min_per_col:
        return lines, [default_column]

    # 判据 3：两列 y 分布重叠 >= 30%（否则本质是上下堆叠单列）
    def _y_range(ls):
        y0s = [l["bbox"][1] for l in ls]
        y1s = [l["bbox"][3] for l in ls]
        return min(y0s), max(y1s)
    ly0, ly1 = _y_range(left_lines)
    ry0, ry1 = _y_range(right_lines)
    overlap = min(ly1, ry1) - max(ly0, ry0)
    max_height = max(ly1 - ly0, ry1 - ry0)
    if max_height <= 0 or overlap / max_height < 0.3:
        return lines, [default_column]

    return lines, [_build_column(left_lines), _build_column(right_lines)]


def _detect_table_candidates(text_lines, ruled_tables, text_columns):
    """1.1: 无边框表的候选兜底。

    1.6 v2: 判据「多 x 起点簇 + aligned≥5」（v1）在英文论文（Case 04/07）里不生效——
    正文里的公式、段落缩进、图题都能形成 3+ line 的小 cluster，误把整块正文当表。
    改为**依赖新分列结果**：单列文档不可能是无边框表（无边框表天然需要多列结构），
    只有当 text_columns 已判定为多列时，才允许产生 clustered_text 候选。
    这样把"是否多列"和"是否是表格候选"解耦——分列判据的准确性传递到候选判据。
    """
    # v2: 单列文档跳过候选生成——无边框表必然是多列结构
    if not text_columns or len(text_columns) < 2:
        return []

    def _overlaps(a, b, tol=5):
        return not (a[2] < b[0] - tol or a[0] > b[2] + tol or a[3] < b[1] - tol or a[1] > b[3] + tol)

    ruled = [t["bbox"] for t in ruled_tables]
    candidates = []
    if len(text_lines) < 4:
        return candidates

    y_bins = {}
    for line in text_lines:
        key = round(line["bbox"][1] / 5) * 5
        y_bins.setdefault(key, []).append(line)
    rows = sorted([(y, ls) for y, ls in y_bins.items() if len(ls) >= 2], key=lambda kv: kv[0])
    if len(rows) < 3:
        return candidates

    x_starts = [round(l["bbox"][0]) for _y, ls in rows for l in ls]
    if not x_starts:
        return candidates
    try:
        mode = statistics.mode(x_starts)
    except statistics.StatisticsError:
        return candidates

    aligned = sum(1 for _y, ls in rows if any(round(l["bbox"][0]) == mode for l in ls))
    if aligned < 5:
        return candidates

    x0 = min(l["bbox"][0] for _y, ls in rows for l in ls)
    y0 = min(l["bbox"][1] for _y, ls in rows for l in ls)
    x1 = max(l["bbox"][2] for _y, ls in rows for l in ls)
    y1 = max(l["bbox"][3] for _y, ls in rows for l in ls)
    cols_estimate = max(2, len({round(l["bbox"][0] / 10) for _y, ls in rows for l in ls}))
    candidate = {
        "bbox": [round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2)],
        "rows": len(rows),
        "cols": cols_estimate,
        "source": "clustered_text",
    }
    if not any(_overlaps(candidate["bbox"], b) for b in ruled):
        candidates.append(candidate)
    return candidates


def _extract_tables_pdfplumber(pdf_path, page_number, ruled_bboxes, meaningful_chars):
    """1.2 表格识别补强：pdfplumber 作为 pymupdf 的并列源。

    pymupdf 对无边框表识别弱（Q4/Q5/Q7/Q8 塌陷率 -95%~-100%）。pdfplumber 的
    表格算法更稳。这里返回与 pymupdf 输出结构一致、去重后的表格列表。
    Lazy import：pdfplumber 缺失时返回空列表，不阻塞流程。

    1.6：needs_ocr 页（meaningful_chars < 40）直接跳过——pdfplumber 会把扫描图像
    里的矢量描边（有些扫描 PDF 会附带描边）识别为表格边框，产生纯空表。
    Case 01 红头文件 196 页全无文字 → pdfplumber 报 57 张空表，模型会被误导。
    """
    if meaningful_chars < 40:
        return []
    try:
        import pdfplumber
    except ImportError:
        return []

    def _overlaps(a, b, tol=8):
        return not (a[2] < b[0] - tol or a[0] > b[2] + tol
                    or a[3] < b[1] - tol or a[1] > b[3] + tol)

    out = []
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            if page_number - 1 >= len(pdf.pages):
                return []
            page = pdf.pages[page_number - 1]
            for t in page.find_tables():
                bbox = [round(v, 2) for v in t.bbox]  # x0, top, x1, bottom
                if any(_overlaps(bbox, rb) for rb in ruled_bboxes):
                    continue  # pymupdf 已识别到，跳过重复
                try:
                    data = t.extract() or []
                except Exception:
                    data = []
                header = data[0] if data else []
                body = data[1:] if len(data) > 1 else []
                out.append({
                    "bbox": bbox,
                    "rows": len(data),
                    "cols": len(header) if header else 0,
                    "header": [c or "" for c in (header or [])],
                    "data": [[c or "" for c in row] for row in body],
                    "row_heights": [round(r.bbox[3] - r.bbox[1], 2) for r in t.rows] if hasattr(t, 'rows') else [],
                    "col_widths": [round(c[2] - c[0], 2) if c and len(c) >= 4 else 0 for c in (getattr(t.rows[0], 'cells', []) if hasattr(t, 'rows') and t.rows else [])],
                    "source": "pdfplumber",
                })
    except Exception:
        return out
    return out


def _cluster_vector_regions(drawings, page_rect):
    """1.2: 把 get_drawings 的向量元素按 bbox 聚类，产出可能的 logo/icon 区域。

    并不精细——只是给 kind=cover / graphic / mixed 一个"这里可能有 vector 图形"的提示，
    重建时 agent 可以按 bbox 从 pages/*.png 或 pages/*-hd.png 裁剪出来嵌入。
    """
    if not drawings:
        return []
    boxes = []
    for d in drawings:
        for item in d.get("items", []):
            if len(item) >= 2 and hasattr(item[1], "rect"):
                r = item[1].rect
                boxes.append([r.x0, r.y0, r.x1, r.y1])
            elif isinstance(item, tuple) and len(item) >= 2:
                # fall back: pymupdf sometimes returns Rect-like directly
                try:
                    r = d.get("rect")
                    if r:
                        boxes.append([r.x0, r.y0, r.x1, r.y1])
                except Exception:
                    pass
        # fallback per-drawing rect
        r = d.get("rect")
        if r:
            try:
                boxes.append([r.x0, r.y0, r.x1, r.y1])
            except Exception:
                pass

    if not boxes:
        return []

    # Simple bounding-box cluster: union boxes that overlap within tol
    def _union(a, b):
        return [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]

    def _overlap(a, b, tol=10):
        return not (a[2] + tol < b[0] or a[0] > b[2] + tol
                    or a[3] + tol < b[1] or a[1] > b[3] + tol)

    clusters = []
    for box in boxes:
        merged = False
        for i, c in enumerate(clusters):
            if _overlap(c["bbox"], box):
                c["bbox"] = _union(c["bbox"], box)
                c["count"] += 1
                merged = True
                break
        if not merged:
            clusters.append({"bbox": box, "count": 1})

    # Only keep clusters with ≥3 drawings and reasonable size (likely logos/icons, not stray lines)
    page_area = page_rect.width * page_rect.height
    out = []
    for c in clusters:
        b = c["bbox"]
        area = max(0.0, (b[2] - b[0]) * (b[3] - b[1]))
        if c["count"] >= 3 and area > 100 and area < 0.5 * page_area:
            out.append({
                "bbox": [round(v, 2) for v in b],
                "drawing_count": c["count"],
                "area_ratio": round(area / page_area, 4) if page_area else 0.0,
                "hint": "vector_region",
            })
    return out


def _page_ink_metrics(png_path, white_threshold=245):
    """1.2: 像 kimi cmd_inspect 那样计算 ink ratio / content bbox。"""
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        img = Image.open(png_path).convert("L")
    except Exception:
        return None
    ink = img.point(lambda v: 255 if v < white_threshold else 0)
    total = max(1, img.width * img.height)
    ink_pixels = ink.histogram()[255]
    bbox = ink.getbbox()
    if bbox is None:
        return {"ink_ratio": 0.0, "content_bbox": None,
                "content_width_ratio": 0.0, "content_height_ratio": 0.0, "content_area_ratio": 0.0}
    l, t, r, b = bbox
    return {
        "ink_ratio": round(ink_pixels / total, 6),
        "content_bbox": [l, t, r, b],
        "content_width_ratio": round((r - l) / img.width, 4),
        "content_height_ratio": round((b - t) / img.height, 4),
        "content_area_ratio": round(((r - l) * (b - t)) / total, 4),
    }


def _needs_ocr(meaningful, largest_img, columns):
    if meaningful < 40 and largest_img > 0.55:
        return True
    if meaningful < 40 and not columns:
        return True
    return False


# 常见句末标点（合并段落时用作"上一行未结束"的判定基础）
_SENTENCE_ENDINGS = tuple("。！？!?.…；;")


def _looks_like_heading(text, bbox, line_height_hint):
    """判断一个 block 是否像"独立标题"（单行、短、结尾无句末标点）。

    评测 Case 07 抽样：blocks[3]="3.2\\nAttention"（小节标题）曾被合并进后续正文
    blocks[4]，标题层级信息全部丢失。1.6 用 3 条硬性特征识别标题：
    - 文本长度 < 40 字符（英文小节标题、中文小节标题都符合）
    - block 高度 ≤ 1.5 × 行高（说明只是单行）
    - 结尾无句末标点（正文段落末尾一般有句号）

    参数 line_height_hint 应传入"单行高度参考"，不是"合并阈值 1.5 × 字号"。
    """
    stripped = (text or "").strip()
    if not stripped or len(stripped) >= 40:
        return False
    block_height = bbox[3] - bbox[1]
    if block_height > line_height_hint * 1.5:
        return False
    if stripped.endswith(_SENTENCE_ENDINGS):
        return False
    return True


def _cluster_paragraph_groups(blocks, text_lines):
    """把 PyMuPDF 的 text blocks 合并成段落组，帮 Word 侧避免「每行一段」。

    评测数据：4/15 case 报「结构-段落误拆/误合」；PyMuPDF 天然 block 有时
    把跨行段落拆成多个 block，模型光看 blocks 容易照抄成多个 Word 段落。

    合并规则（保守，宁少不错）：
    - 同栏（起点 x0 差 < 5 pt）
    - 竖向紧接（y 间隔 < 1.5 × 该页字号中位数）
    - 上一 block 结尾没有句末标点（未结束的段落大概率跨行）

    返回：每个 group 含 block_indices、bbox、text、joined 段落文字。
    """
    if not blocks:
        return []
    sizes = [line.get("size", 0) or 0 for line in text_lines or [] if line.get("size", 0) > 0]
    if sizes:
        line_height_hint = statistics.median(sizes) * 1.5
    else:
        line_height_hint = 18.0  # 兜底：12pt 字号的 1.5 倍行距

    groups = []
    current = None
    for index, block in enumerate(blocks):
        if block.get("block_type", 0) != 0:
            continue
        text = (block.get("text") or "").strip()
        if not text:
            continue
        bbox = block["bbox"]
        if current is None:
            current = {
                "block_indices": [index],
                "bbox": list(bbox),
                "text": text,
            }
            continue

        prev_x0 = current["bbox"][0]
        prev_y1 = current["bbox"][3]
        prev_text = current["text"]
        same_column = abs(bbox[0] - prev_x0) < 5.0
        close_y = 0 < bbox[1] - prev_y1 < line_height_hint
        prev_unterminated = not prev_text.rstrip().endswith(_SENTENCE_ENDINGS)

        # 1.6: 标题保护——短独立 block 不参与合并（防止把 "3.2 Attention" 吸收进正文）
        # line_height_hint 已经是 1.5 × 字号中位数，除回来得到单行高度基准
        single_line_height = line_height_hint / 1.5
        current_is_heading = _looks_like_heading(text, bbox, single_line_height)
        prev_is_heading = (
            len(current["block_indices"]) == 1
            and _looks_like_heading(current["text"], current["bbox"], single_line_height)
        )

        if (
            not current_is_heading
            and not prev_is_heading
            and same_column
            and close_y
            and prev_unterminated
        ):
            current["block_indices"].append(index)
            current["bbox"] = [
                min(prev_x0, bbox[0]),
                current["bbox"][1],
                max(current["bbox"][2], bbox[2]),
                bbox[3],
            ]
            current["text"] = prev_text + text
        else:
            groups.append(current)
            current = {
                "block_indices": [index],
                "bbox": list(bbox),
                "text": text,
            }
    if current is not None:
        groups.append(current)
    # 把 bbox 精度对齐存量代码
    for g in groups:
        g["bbox"] = [round(v, 2) for v in g["bbox"]]
    return groups


def _collect_special_chars(text):
    """扫描非 ASCII、非 CJK 汉字/常见 CJK 标点的符号字符。

    评测数据：9/15 case 报「内容-特殊字符错误」，主要是 ①② 圆圈数字、
    m³ 上下标、数学公式符号等。用 Unicode 分类 S* (符号类) 精准捕获，
    跳过 CJK 汉字和常见 CJK 标点/全角形式，避免误报。
    """
    if not text:
        return []
    special = set()
    for ch in text:
        cp = ord(ch)
        if cp < 128:
            continue
        # CJK 汉字（基本 + 扩展 A + 兼容）
        if 0x4E00 <= cp <= 0x9FFF:
            continue
        if 0x3400 <= cp <= 0x4DBF:
            continue
        if 0xF900 <= cp <= 0xFAFF:
            continue
        # CJK 符号和标点（。，、《》【】等）
        if 0x3000 <= cp <= 0x303F:
            continue
        # 半宽全宽形式（全角数字/英文字母）
        if 0xFF00 <= cp <= 0xFFEF:
            continue
        if unicodedata.category(ch).startswith("S"):
            special.add(ch)
    return sorted(special)


def analyze(input_pdf, output_dir, dpi, render, extract_images, extract_columns,
            pages_spec, render_hd_cover):
    pages_dir = output_dir / "pages"
    images_dir = output_dir / "images"
    text_dir = output_dir / "text"
    text_dir.mkdir(parents=True, exist_ok=True)
    if render:
        pages_dir.mkdir(parents=True, exist_ok=True)
    if extract_images:
        images_dir.mkdir(parents=True, exist_ok=True)

    with pymupdf.open(str(input_pdf)) as document:
        indices = _parse_pages(pages_spec, document.page_count)
        seen_xref = set()
        pages_out = []
        kind_dist = {}
        warnings = []
        toc_out = _extract_toc(document, warnings)
        relationships_out = []

        if document.is_encrypted:
            warnings.append("source pdf is encrypted; extraction may be partial")

        scale = dpi / 72.0
        matrix = pymupdf.Matrix(scale, scale)
        hd_matrix = pymupdf.Matrix(300 / 72.0, 300 / 72.0)  # 1.2: cover HD

        for idx in indices:
            page = document[idx]
            page_number = idx + 1
            rect = page.rect
            page_area = float(rect.width * rect.height)

            text = page.get_text("text", sort=True) or ""
            # 提前计算 meaningful_chars —— pdfplumber 表格识别在扫描页需要跳过
            meaningful = _meaningful_chars(text)
            blocks_raw = page.get_text("blocks", sort=True) or []
            blocks = [
                {
                    "bbox": [round(b[0], 2), round(b[1], 2), round(b[2], 2), round(b[3], 2)],
                    "text": b[4] if len(b) > 4 else "",
                    "block_no": int(b[5]) if len(b) > 5 else 0,
                    "block_type": int(b[6]) if len(b) > 6 else 0,
                }
                for b in blocks_raw
            ]
            drawings = page.get_drawings()
            lines_count = sum(1 for d in drawings if d.get("type") in ("s", "sf"))
            rects_count = sum(len(d.get("items", [])) for d in drawings if d.get("type") == "f")

            largest_ratio = 0.0
            for info in page.get_image_info():
                bbox = info.get("bbox", (0, 0, 0, 0))
                area = max(0.0, (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]))
                if page_area:
                    largest_ratio = max(largest_ratio, area / page_area)

            tables_out = []
            table_area = 0.0
            try:
                finder = page.find_tables()
                for table in finder.tables:
                    bbox = list(table.bbox)
                    table_area += max(0.0, (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]))
                    data = table.extract() or []
                    header = data[0] if data else []
                    body = data[1:] if len(data) > 1 else []
                    tables_out.append({
                        "bbox": [round(v, 2) for v in bbox],
                        "rows": len(data),
                        "cols": len(header),
                        "header": header,
                        "data": body,
                        "row_heights": [round(r.bbox[3] - r.bbox[1], 2) for r in table.rows],
                        "col_widths": [round(c[2] - c[0], 2) if c is not None and len(c) >= 4 else 0 for c in (getattr(table.rows[0], 'cells', []) if table.rows else [])],
                        "source": "pymupdf",
                    })
            except Exception as exc:
                warnings.append(f"page {page_number}: pymupdf table detection failed ({exc})")

            # 1.2: pdfplumber 并列表格识别 —— 补 pymupdf 对无边框表 -95%~-100% 塌陷的短板
            # 1.6: 传 meaningful_chars，扫描/无文字页直接跳过 pdfplumber
            ruled_bboxes = [t["bbox"] for t in tables_out]
            plumber_tables = _extract_tables_pdfplumber(input_pdf, page_number, ruled_bboxes, meaningful)
            for t in plumber_tables:
                b = t["bbox"]
                table_area += max(0.0, (b[2] - b[0]) * (b[3] - b[1]))
                tables_out.append(t)

            text_lines_out = []
            text_columns_out = []
            if extract_columns:
                text_lines_out, text_columns_out = _extract_text_lines_and_columns(page)

            table_candidates_out = _detect_table_candidates(text_lines_out, tables_out, text_columns_out)
            vector_regions = _cluster_vector_regions(drawings, rect)

            # 1.2: graphic_density —— 触发 HD 渲染兜底（Q13 SITOP 型密集图表页）
            drawing_count = sum(len(d.get("items", [])) for d in drawings)
            is_graphic_dense = (
                rects_count > 30
                or drawing_count > 100
                or len(vector_regions) > 3
                or (largest_ratio > 0.3 and meaningful < 500)
            )
            kind, reason = _classify_kind(
                idx, meaningful, largest_ratio, len(tables_out), rects_count,
                page_area, table_area, len(text_columns_out), text_lines_out,
            )
            kind_dist[kind] = kind_dist.get(kind, 0) + 1

            images_out = _extract_page_images(document, page, page_number, images_dir, seen_xref, warnings) if extract_images else []
            page_relationships = _extract_page_relationships(page, page_number, warnings)
            relationships_out.extend(page_relationships)
            cross_references = [
                {
                    "relationship_id": relationship["id"],
                    "text": relationship["source"]["text"],
                    "format": relationship["cross_reference_format"],
                    "target_page": relationship["target"]["page"],
                }
                for relationship in page_relationships
                if relationship["target"]["kind"] in ("internal", "named")
            ]

            text_rel = f"text/page-{page_number:02d}.txt"
            (output_dir / text_rel).write_text(text, encoding="utf-8")

            preview_rel = None
            preview_hd_rel = None
            render_metrics = None
            if render:
                pixmap = page.get_pixmap(matrix=matrix, alpha=False)
                preview_rel = f"pages/page-{page_number:02d}.png"
                preview_path = output_dir / preview_rel
                pixmap.save(str(preview_path))
                render_metrics = _page_ink_metrics(preview_path)

                # 1.2: HD render for cover + graphic-dense pages —— 图片密集页丢图时的整页兜底
                need_hd = render_hd_cover and (kind in ("cover", "graphic") or is_graphic_dense)
                if need_hd:
                    hd_pix = page.get_pixmap(matrix=hd_matrix, alpha=False)
                    preview_hd_rel = f"pages/page-{page_number:02d}-hd.png"
                    hd_pix.save(str(output_dir / preview_hd_rel))

            pages_out.append({
                "page": page_number,
                "kind": kind,
                "kind_reason": reason,
                "size": {"width": round(rect.width, 2), "height": round(rect.height, 2), "unit": "pt", "rotation": int(page.rotation)},
                "meaningful_chars": meaningful,
                "blocks": blocks,
                "paragraph_groups": _cluster_paragraph_groups(blocks, text_lines_out),
                "special_chars": _collect_special_chars(text),
                "text_lines": text_lines_out,
                "text_columns": text_columns_out,
                "column_count": len(text_columns_out),
                "body_bbox": _compute_body_bbox(text_lines_out, rect),
                "table_candidates": table_candidates_out,
                "vector_regions": vector_regions,
                "lines": lines_count,
                "rects": rects_count,
                "drawing_count": drawing_count,
                "is_graphic_dense": bool(is_graphic_dense),
                "largest_image_ratio": round(largest_ratio, 4),
                "tables": tables_out,
                "tables_pymupdf_count": sum(1 for t in tables_out if t.get("source") == "pymupdf"),
                "tables_pdfplumber_count": sum(1 for t in tables_out if t.get("source") == "pdfplumber"),
                "images": images_out,
                "link_relationship_ids": [relationship["id"] for relationship in page_relationships],
                "cross_references": cross_references,
                "text_file": text_rel,
                "preview_png": preview_rel,
                "preview_hd_png": preview_hd_rel,
                "render_metrics": render_metrics,
                "needs_ocr": _needs_ocr(meaningful, largest_ratio, text_columns_out),
            })

        primary_kind = max(kind_dist.items(), key=lambda kv: kv[1])[0] if kind_dist else "text"

        return {
            "schema_version": SCHEMA_VERSION,
            "generated_at": _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
            "generator": GENERATOR,
            "source": {
                "path": str(input_pdf),
                "size_bytes": input_pdf.stat().st_size,
                "sha1": _sha1(input_pdf),
                "encrypted": bool(document.is_encrypted),
                "page_count": document.page_count,
            },
            "artifacts": {
                "layout_json": "pdf_layout.json",
                "pages_dir": "pages/" if render else None,
                "images_dir": "images/" if extract_images else None,
                "text_dir": "text/",
            },
            "summary": {
                "kind_distribution": kind_dist,
                "primary_kind": primary_kind,
                "warnings": warnings,
                "needs_ocr_pages": [p["page"] for p in pages_out if p.get("needs_ocr")],
                "cover_pages": [p["page"] for p in pages_out if p["kind"] == "cover"],
                "graphic_dense_pages": [p["page"] for p in pages_out if p.get("is_graphic_dense")],
                "tables_total_pymupdf": sum(p.get("tables_pymupdf_count", 0) for p in pages_out),
                "tables_total_pdfplumber": sum(p.get("tables_pdfplumber_count", 0) for p in pages_out),
                "tables_total": sum(len(p.get("tables", [])) for p in pages_out),
                "toc_entries": len(toc_out),
                "links_total": len(relationships_out),
                "internal_links": sum(
                    relationship["target"]["kind"] in ("internal", "named")
                    for relationship in relationships_out
                ),
                "external_links": sum(
                    relationship["target"]["kind"] in ("uri", "remote", "launch")
                    for relationship in relationships_out
                ),
            },
            "toc": toc_out,
            "relationships": relationships_out,
            "pages": pages_out,
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_pdf", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--dpi", type=int, default=200)
    parser.add_argument("--render", dest="render", action="store_true", default=True,
                        help="Render each page to pages/page-NN.png (default on)")
    parser.add_argument("--no-render", dest="render", action="store_false")
    parser.add_argument("--images", dest="images", action="store_true", default=True,
                        help="Extract embedded images (pymupdf + pikepdf raw fallback) (default on)")
    parser.add_argument("--no-images", dest="images", action="store_false")
    parser.add_argument("--extract-columns", dest="extract_columns", action="store_true", default=True,
                        help="Emit text_lines[] + text_columns[] (default on)")
    parser.add_argument("--no-extract-columns", dest="extract_columns", action="store_false")
    parser.add_argument("--render-hd-cover", dest="render_hd_cover", action="store_true", default=True,
                        help="Render cover pages (kind==cover) at 300 dpi as pages/page-NN-hd.png (default on)")
    parser.add_argument("--no-render-hd-cover", dest="render_hd_cover", action="store_false")
    parser.add_argument("--pages", type=str, default=None, help="Page spec like 1-3,5,7-9")
    args = parser.parse_args()

    if not args.input_pdf.is_file():
        print(f"error: pdf not found: {args.input_pdf}", file=sys.stderr)
        return 1
    args.output_dir.mkdir(parents=True, exist_ok=True)

    try:
        report = analyze(args.input_pdf, args.output_dir, args.dpi,
                         args.render, args.images, args.extract_columns,
                         args.pages, args.render_hd_cover)
    except pymupdf.FileDataError as exc:
        print(f"error: cannot open pdf: {exc}", file=sys.stderr)
        return 2

    layout_path = args.output_dir / "pdf_layout.json"
    layout_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"layout: {layout_path}")

    total_meaningful = sum(p["meaningful_chars"] for p in report["pages"])
    if total_meaningful == 0:
        print("warning: no meaningful text extracted; treat as scan", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())