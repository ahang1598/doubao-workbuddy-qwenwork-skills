#!/usr/bin/env python3
"""Audit a generated DOCX for editability, layout integrity and, when a
pdf_layout.json is provided, coverage against the source PDF.

Serves as the hard gate for:
- doubao-pdf/references/workflows/pdf-to-word.md

Supports pdf_layout.json schema_version 1.x. Higher major bumps error out;
higher minor is warned but not blocked.
"""

from __future__ import annotations

import argparse
import collections
import functools
import json
import re
import statistics
import subprocess
import sys
import unicodedata
import zipfile
from pathlib import Path
from typing import Any

from docx import Document
from docx.oxml.ns import qn
from lxml import etree

COVERAGE_THRESHOLD = 0.9  # DOCX meaningful chars vs pdf_layout.json total
SUPPORTED_MINOR = 6       # 与 analyze_pdf_layout.py 当前输出的 schema 1.6 保持一致

# ECMA-376 5th Transitional + OPC XSD 目录（脚本旁的 ooxml_schemas/）。用于校验
# 生成的 DOCX 能否被 Office Word 打开——XSD 通过是 Word 打开的必要条件。
# 目录内容：
#   - 26 个 Transitional XSD（源: github.com/QtExcel/ecma-376-5th，路径
#     ECMA-376/OfficeOpenXML-XMLSchema-Transitional/），选 Transitional 而非
#     Strict 是因为 Office 2013+ 默认输出 Transitional，Strict 会拒绝 w:cs / VML。
#   - 4 个 OPC XSD（同源，OpenPackagingConventions-XMLSchema/）。
#   - xml.xsd（源: www.w3.org/2001/xml.xsd），补齐 xml namespace。
#   - wml.xsd 和 shared-math.xsd 已 patched，把 <xsd:import
#     namespace="http://www.w3.org/XML/1998/namespace"/> 加上 schemaLocation="xml.xsd"，
#     否则 lxml build XMLSchema 时会因不识别 xml:space 报错。替换 XSD 时需保留此 patch。
_DEFAULT_SCHEMAS_DIR = Path(__file__).parent / "ooxml_schemas"

# OPC (Open Packaging Conventions) 命名空间
_CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
_MC_NS = "http://schemas.openxmlformats.org/markup-compatibility/2006"
_MAIN_DOC_REL_TYPES = frozenset({
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument",
    "http://purl.oclc.org/ooxml/officeDocument/relationships/officeDocument",
})
# Word 主文档在 Content_Types 里必须精确声明为下列之一；否则即使有 default xml
# 匹配 extension，Word 也拒绝打开（default 的 "application/xml" 不是 Word 主文档类型）。
_MAIN_DOC_CONTENT_TYPES = frozenset({
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.template.main+xml",
    "application/vnd.ms-word.document.macroEnabled.main+xml",
    "application/vnd.ms-word.template.macroEnabled.main+xml",
})


def _count_pdf_pages(pdf_path):
    """Count pages of a rendered PDF via pymupdf. Import lazily so tests without pymupdf still pass."""
    import pymupdf
    with pymupdf.open(str(pdf_path)) as doc:
        return doc.page_count


def _estimate_docx_pages(doc):
    """Structural page count estimation without rendering.

    Returns (min_pages, breakdown_dict). min_pages is a lower bound derived from:
    - explicit <w:br w:type="page"/> paragraph runs
    - hard section breaks (sectPr.type != "continuous")
    - the implicit first page

    This is a lower bound because Word/LibreOffice will also insert page breaks
    based on font metrics and content overflow which we can't compute without a
    renderer. But an over-count is definitive: if min_pages already exceeds the
    source PDF page count, the DOCX cannot match — that's a hard error.
    """
    explicit = 0
    for p in doc.paragraphs:
        for r in p.runs:
            for br in r._element.findall(qn("w:br")):
                if br.get(qn("w:type")) == "page":
                    explicit += 1

    hard_section_breaks = 0
    section_count = 0
    for section in doc.sections:
        section_count += 1
        sectPr = section._sectPr
        typ_el = sectPr.find(qn("w:type")) if sectPr is not None else None
        val = typ_el.get(qn("w:val")) if typ_el is not None else "nextPage"
        if val != "continuous":
            hard_section_breaks += 1
    # first section's sectPr terminates the doc, not the start; subtract 1
    hard_section_breaks = max(0, hard_section_breaks - 1)

    min_pages = 1 + explicit + hard_section_breaks
    return min_pages, {
        "explicit_page_breaks": explicit,
        "hard_section_breaks": hard_section_breaks,
        "section_count": section_count,
    }


def _collect_source_fonts(layout):
    """From pdf_layout.json's pages[].text_lines[].font, produce a sorted unique font list."""
    fonts = set()
    for p in layout.get("pages", []):
        for line in p.get("text_lines", []) or []:
            f = line.get("font")
            if f:
                fonts.add(f)
    return sorted(fonts)


def _installed_fonts_via_fc_list():
    """Return the set of installed font family names via `fc-list : family`.
    Returns None if fc-list is unavailable so the caller can skip the check."""
    try:
        out = subprocess.run(
            ["fc-list", ":", "family"],
            capture_output=True, text=True, timeout=10,
        )
        if out.returncode != 0:
            return None
    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        return None
    installed = set()
    for line in out.stdout.splitlines():
        for name in line.split(","):
            installed.add(name.strip())
    return installed


def _match_font_family(needed, installed):
    """Loose matching: exact match OR family prefix match (e.g. 'SimSun' matches 'SimSun-ExtB')."""
    if needed in installed:
        return True
    lc_needed = needed.lower().replace(" ", "").replace("-", "")
    for name in installed:
        lc_name = name.lower().replace(" ", "").replace("-", "")
        if lc_name.startswith(lc_needed) or lc_needed.startswith(lc_name):
            return True
    return False


def dxa_value(element, attr="w:w"):
    raw = element.get(qn(attr)) if element is not None else None
    try:
        return int(raw) if raw is not None else None
    except ValueError:
        return None


def _meaningful(text):
    return len("".join(text.split()))


def _textbox_text(doc):
    """Collect editable text stored in Word text boxes."""
    return "".join(node.text or "" for node in doc.element.xpath(".//w:txbxContent//w:t"))


# 评测报告发现 doubao 大量使用方正字体（收费 + 跨平台不可用），Codex 用 Arial Unicode MS，
# Workbuddy 用黑体/仿宋。检测输出用了收费字体的场景，加警告推动 agent 用跨平台字体。
COMMERCIAL_FONT_KEYWORDS = ("方正", "founder", "Founder", "FZ", "FZLan", "FZKai", "FZSong",
                            "FZHei", "FZFangSong", "FZXiaoBiaoSong")
CROSS_PLATFORM_FONT_HINT = ("Arial Unicode MS", "PingFang SC", "Noto Sans CJK SC",
                            "Songti SC", "Source Han Sans", "微软雅黑", "宋体", "黑体", "仿宋", "楷体")

# 评测报告发现 5/15 case 把页码/页眉/页脚误当正文段落写入。以下正则覆盖常见形态：
# 纯数字、中文「第 X 页」、英文「Page X」、短横夹数字「-3-」、分数式「3 / 10」。
PAGE_MARKER_PATTERNS = (
    re.compile(r"^\d{1,4}$"),
    re.compile(r"^第\s*\d+\s*页$"),
    re.compile(r"^Page\s+\d+(?:\s*/\s*\d+)?$", re.IGNORECASE),
    re.compile(r"^-\s*\d+\s*-$"),
    re.compile(r"^\d+\s*/\s*\d+$"),
)


def _detect_commercial_fonts(fonts_by_level):
    """扫描 _collect_run_fonts 的结果，找出 (ascii, eastAsia) 签名里含方正字体的情况。"""
    hits = []
    for level, sigs in fonts_by_level.items():
        for sig in sigs:
            for name in sig:
                if not name:
                    continue
                for kw in COMMERCIAL_FONT_KEYWORDS:
                    if kw in name:
                        hits.append({"level": level, "font": name})
                        break
    return hits


def _iter_all_cells(tables):
    """B.2: 递归遍历所有 cell（含嵌套表），修覆盖率被严重低估的问题。"""
    for t in tables:
        for r in t.rows:
            for c in r.cells:
                yield c
                yield from _iter_all_cells(c.tables)


def _iter_all_tables(tables):
    for t in tables:
        yield t
        for r in t.rows:
            for c in r.cells:
                yield from _iter_all_tables(c.tables)


def _collect_run_fonts(doc):
    buckets = collections.defaultdict(set)

    def _classify(style_name):
        low = (style_name or "Normal").lower()
        if "title" in low:
            return "title"
        if "heading" in low:
            return "heading"
        if "caption" in low or "footer" in low or "header" in low:
            return "peripheral"
        return "body"

    def _sig(run):
        rPr = run._element.find(qn("w:rPr"))
        if rPr is None:
            return (None, None)
        rFonts = rPr.find(qn("w:rFonts"))
        if rFonts is None:
            return (None, None)
        return (rFonts.get(qn("w:ascii")), rFonts.get(qn("w:eastAsia")))

    for para in doc.paragraphs:
        bucket = _classify(para.style.name if para.style else "")
        for run in para.runs:
            buckets[bucket].add(_sig(run))

    for cell in _iter_all_cells(doc.tables):
        for para in cell.paragraphs:
            for run in para.runs:
                buckets["table"].add(_sig(run))

    # B.1: 用 key= 兜住 None；否则 sorted 会抛 TypeError
    return {level: sorted(sigs, key=lambda s: tuple(x or "" for x in s))
            for level, sigs in buckets.items()}


def _collect_run_font_sizes(doc):
    """按 title/heading/body/table/peripheral 分层收集字号 (pt)。

    Word rPr.sz 使用半点单位（half-point），实际字号 = sz.val / 2。
    评测报告显示 15/15 case 报「字体/字号错误」——脚本必须主动抓字号偏差，
    不能仅靠模型自觉。返回 {level: {median, count, range}}，供与 pdf_layout 对比。
    """
    buckets = collections.defaultdict(list)

    def _classify(style_name):
        low = (style_name or "Normal").lower()
        if "title" in low:
            return "title"
        if "heading" in low:
            return "heading"
        if "caption" in low or "footer" in low or "header" in low:
            return "peripheral"
        return "body"

    def _size_pt(run):
        rPr = run._element.find(qn("w:rPr"))
        if rPr is None:
            return None
        sz = rPr.find(qn("w:sz"))
        if sz is None:
            return None
        try:
            return float(sz.get(qn("w:val"))) / 2.0
        except (TypeError, ValueError):
            return None

    for para in doc.paragraphs:
        bucket = _classify(para.style.name if para.style else "")
        for run in para.runs:
            sz = _size_pt(run)
            if sz is not None:
                buckets[bucket].append(sz)

    for cell in _iter_all_cells(doc.tables):
        for para in cell.paragraphs:
            for run in para.runs:
                sz = _size_pt(run)
                if sz is not None:
                    buckets["table"].append(sz)

    return {
        level: {
            "median": round(statistics.median(sizes), 2),
            "count": len(sizes),
            "range": [round(min(sizes), 2), round(max(sizes), 2)],
        }
        for level, sizes in buckets.items()
    }


def _pdf_body_size_median(layout):
    """从 pdf_layout.pages[].text_lines[].size 计算源 PDF 正文字号中位数 (pt)。

    权重：按每行字符数加权，长文本行的字号更能代表正文；
    去掉极端 5% 抛掉标题极大值和脚注极小值。
    返回 None 表示样本不足，不做对比。
    """
    weighted = []
    for page in layout.get("pages", []):
        for line in page.get("text_lines", []) or []:
            size = line.get("size", 0) or 0
            char_count = len((line.get("text", "") or "").strip())
            if size > 0 and char_count > 0:
                weighted.extend([size] * char_count)
    if not weighted:
        return None
    if len(weighted) < 20:
        return round(statistics.median(weighted), 2)
    weighted.sort()
    n = len(weighted)
    trimmed = weighted[int(n * 0.05):int(n * 0.95)]
    return round(statistics.median(trimmed), 2)


def _compare_tables_pairwise(pdf_tables_flat, docx_tables, tolerance_pct=0.20):
    """按顺序匹配 PDF 表格和 DOCX 表格，对比 rows / cols / col_widths。

    评测数据：8/15 case 报「表格结构错误」（Q1 因此触发红线）+ 5/15 case 报
    「表格宽度错误」——只对比表格数量抓不到列宽和结构错，必须逐个对比。

    参数：
        pdf_tables_flat: pdf_layout.pages[].tables[] 扁平化列表
        docx_tables: DOCX 中所有表格（含嵌套，已由 _iter_all_tables 展平）
        tolerance_pct: 行/列/列宽偏差的容忍百分比
    返回：问题描述字符串列表，由调用方决定报错级别。

    1.6 关键约束：**数量不一致时不做逐个对比**——按 index 匹配后中间少一个表
    就会连锁错位到底（15 份实测：Case 13 差 10 个表 → 256 条虚报错误）。此时只
    报总差，让模型先修数量再重新审计。

    col_widths 对比也做了收紧：pdfplumber 的 col_widths 从第一行 cells 提取，
    合并单元格会产生 <20pt 或 >700pt 的极端值（Case 02 有 25.2pt / 732.9pt 混
    杂）。因此只有当每一列宽度都落在合理范围（20~700pt）时才做 pt 级 diff。
    """
    issues = []
    if len(pdf_tables_flat) != len(docx_tables):
        issues.append(
            f"表格数量不一致：源 PDF {len(pdf_tables_flat)} 个 vs DOCX {len(docx_tables)} 个"
            f"（数量差异 > 0，跳过逐个对比以避免错位连锁误报；请先补齐/删除多余表格再重审）"
        )
        return issues

    for i in range(len(pdf_tables_flat)):
        pdf_t = pdf_tables_flat[i]
        docx_t = docx_tables[i]

        pdf_rows = pdf_t.get("rows", 0) or 0
        pdf_cols = pdf_t.get("cols", 0) or 0
        docx_rows = len(docx_t.rows)
        docx_cols = len(docx_t.rows[0].cells) if docx_t.rows else 0

        if pdf_rows and abs(docx_rows - pdf_rows) / pdf_rows > tolerance_pct:
            issues.append(
                f"第 {i+1} 个表格行数偏差：源 {pdf_rows} 行 vs DOCX {docx_rows} 行"
            )
        if pdf_cols and abs(docx_cols - pdf_cols) / pdf_cols > tolerance_pct:
            issues.append(
                f"第 {i+1} 个表格列数偏差：源 {pdf_cols} 列 vs DOCX {docx_cols} 列"
            )

        pdf_widths = pdf_t.get("col_widths", []) or []
        # DOCX 网格列宽单位为 DXA（1 pt = 20 DXA）
        docx_grid = [dxa_value(c) for c in docx_t._tbl.tblGrid]
        docx_widths_pt = [dxa / 20.0 if dxa else 0 for dxa in docx_grid]

        if pdf_widths and docx_widths_pt and len(pdf_widths) == len(docx_widths_pt):
            # 极端值过滤：pdfplumber 合并单元格伪造的宽度会造成假阳性
            widths_reasonable = all(20 <= w <= 700 for w in pdf_widths)
            if widths_reasonable:
                for j, (p, d) in enumerate(zip(pdf_widths, docx_widths_pt)):
                    if p > 0 and d > 0 and abs(d - p) / p > tolerance_pct:
                        issues.append(
                            f"第 {i+1} 个表格第 {j+1} 列宽度偏差：源 {p:.1f}pt vs DOCX {d:.1f}pt"
                        )
                        break  # 一个表格只报一次列宽问题

    return issues


def _count_docx_drawings(doc):
    """统计 DOCX 中 drawing 元素（图片/形状容器）。

    评测数据：14/15 case 报「其他」（含 logo/图标/横线/边框/装饰丢失）——
    很多装饰在 DOCX 中根本没生成 drawing。用 iter 扫全文（含嵌套）比
    xpath 更稳定，不依赖 namespace 前缀映射。
    """
    inline_count = len(doc.inline_shapes)
    all_drawings = list(doc.element.iter(qn("w:drawing")))
    return {
        "total_drawings": len(all_drawings),
        "inline_pictures": inline_count,
        "floating_pictures": max(0, len(all_drawings) - inline_count),
    }


def _detect_page_marker_leaks(doc):
    """检测正文段落中疑似页码/页眉/页脚的短行。

    评测数据：5/15 case 报「结构-页眉页脚混入正文」，正则命中即强证据。
    只扫短段落（≤ 30 字符），避免正文中偶然含数字的段落误报。
    """
    hits = []
    for index, para in enumerate(doc.paragraphs):
        text = para.text.strip()
        if not text or len(text) > 30:
            continue
        for pattern in PAGE_MARKER_PATTERNS:
            if pattern.match(text):
                hits.append({"paragraph_index": index, "text": text})
                break
    return hits


def _check_omml_cambria_math(doc):
    """检查 OMML 数学公式的 math run 是否使用 Cambria Math 字体。

    Word 硬编码用 Cambria Math 渲染 OMML 公式：math run 的 <w:rPr>/<w:rFonts>
    的 ascii/hAnsi 属性不是 "Cambria Math" 时，希腊字母、积分号、求和号等符号
    会退化为普通字体的对应字形（甚至方框），公式整体渲染错乱。eastAsia 允许
    保留其它值（公式常与中文混排），只校验 ascii 和 hAnsi。

    返回:
        {"omml_present": False}  当文档不含 OMML 公式
        {"omml_present": True, "omath_count": int, "math_run_count": int,
         "bad_run_count": int, "bad_runs_sample": [...]}  含 OMML 时返回明细
    """
    body = doc.element.body
    omath_para = body.findall(".//" + qn("m:oMathPara"))
    omath = body.findall(".//" + qn("m:oMath"))
    if not omath and not omath_para:
        return {"omml_present": False}

    m_runs = body.findall(".//" + qn("m:r"))
    bad_runs = []
    for m_r in m_runs:
        # OMML math run 内 <w:rPr> 才是字体属性载体；<m:rPr>/<m:sty> 只影响
        # italic/bold 等样式，不承载 rFonts。
        w_rPr = m_r.find(qn("w:rPr"))
        rFonts = w_rPr.find(qn("w:rFonts")) if w_rPr is not None else None
        ascii_font = rFonts.get(qn("w:ascii")) if rFonts is not None else None
        hansi_font = rFonts.get(qn("w:hAnsi")) if rFonts is not None else None
        if ascii_font == "Cambria Math" and hansi_font == "Cambria Math":
            continue
        m_t = m_r.find(qn("m:t"))
        sample_text = (m_t.text or "")[:20] if m_t is not None else ""
        bad_runs.append({
            "text": sample_text,
            "ascii": ascii_font,
            "hAnsi": hansi_font,
        })

    return {
        "omml_present": True,
        "omath_count": len(omath) + len(omath_para),
        "math_run_count": len(m_runs),
        "bad_run_count": len(bad_runs),
        "bad_runs_sample": bad_runs[:5],
    }


def _special_chars_from_text(text):
    """扫描非 ASCII、非 CJK 汉字/常见 CJK 标点的符号字符（Unicode S* 类）。

    与 analyze_pdf_layout._collect_special_chars 保持规则一致，独立实现避免脚本间耦合。
    """
    if not text:
        return set()
    special = set()
    for ch in text:
        cp = ord(ch)
        if cp < 128:
            continue
        if 0x4E00 <= cp <= 0x9FFF:
            continue
        if 0x3400 <= cp <= 0x4DBF:
            continue
        if 0xF900 <= cp <= 0xFAFF:
            continue
        if 0x3000 <= cp <= 0x303F:
            continue
        if 0xFF00 <= cp <= 0xFFEF:
            continue
        if unicodedata.category(ch).startswith("S"):
            special.add(ch)
    return special


def _collect_docx_special_chars(doc):
    """扫描 DOCX 所有可见文本（含表格、文本框、页眉页脚）里的特殊符号集合。"""
    parts = [p.text for p in doc.paragraphs]
    parts.extend(cell.text for cell in _iter_all_cells(doc.tables))
    parts.append(_textbox_text(doc))
    for section in doc.sections:
        parts.append("\n".join(p.text for p in section.header.paragraphs))
        parts.append("\n".join(p.text for p in section.footer.paragraphs))
    return _special_chars_from_text("\n".join(parts))


def _collect_numbering(doc):
    seqs = collections.defaultdict(list)
    for para in doc.paragraphs:
        numPr = para._p.find(f"{qn('w:pPr')}/{qn('w:numPr')}")
        if numPr is None:
            continue
        numId = numPr.find(qn("w:numId"))
        ilvl = numPr.find(qn("w:ilvl"))
        if numId is None:
            continue
        key = f"numId={numId.get(qn('w:val'))},ilvl={ilvl.get(qn('w:val')) if ilvl is not None else '0'}"
        seqs[key].append(len(seqs[key]) + 1)
    return {"lists_detected": list(seqs.keys())}


def _header_footer_present(doc):
    out = []
    for i, section in enumerate(doc.sections, start=1):
        header = section.header
        footer = section.footer
        header_text = "\n".join(p.text for p in header.paragraphs).strip()
        footer_text = "\n".join(p.text for p in footer.paragraphs).strip()
        out.append({
            "section": i,
            "has_header_text": bool(header_text),
            "has_footer_text": bool(footer_text),
            "header_sample": header_text[:64],
            "footer_sample": footer_text[:64],
        })
    return {"sections": out}


def _collect_docx_links(doc):
    """Inspect hyperlink elements and field codes not exposed by python-docx."""
    hyperlink_nodes = doc.element.xpath(".//w:hyperlink")
    external = 0
    internal = 0
    for node in hyperlink_nodes:
        relationship_id = node.get(qn("r:id"))
        anchor = node.get(qn("w:anchor"))
        if relationship_id:
            relationship = doc.part.rels.get(relationship_id)
            if relationship is not None and relationship.reltype.endswith("/hyperlink"):
                external += 1
        if anchor:
            internal += 1

    instructions = [
        " ".join((node.text or "").split())
        for node in doc.element.xpath(".//w:instrText")
        if (node.text or "").strip()
    ]
    toc_fields = sum(instruction.upper().startswith("TOC ") or instruction.upper() == "TOC"
                     for instruction in instructions)
    hyperlink_fields = sum(instruction.upper().startswith("HYPERLINK ")
                           for instruction in instructions)
    reference_fields = sum(
        instruction.upper().startswith(("REF ", "PAGEREF ", "NOTEREF "))
        for instruction in instructions
    )
    return {
        "hyperlink_elements": len(hyperlink_nodes),
        "external_hyperlinks": external + hyperlink_fields,
        "internal_references": internal + reference_fields,
        "toc_fields": toc_fields,
        "field_instructions": instructions,
    }


def _validate_layout_relationships(layout):
    """Validate schema 1.4 relationship ids and page targets before comparison."""
    pages = layout.get("pages", []) or []
    relationships = layout.get("relationships", []) or []
    relationship_by_id = {}
    errors = []

    for relationship in relationships:
        relationship_id = relationship.get("id")
        if not relationship_id:
            errors.append("pdf_layout.relationships 存在缺少 id 的条目")
            continue
        if relationship_id in relationship_by_id:
            errors.append(f"pdf_layout.relationships 存在重复 id：{relationship_id}")
            continue
        relationship_by_id[relationship_id] = relationship

    page_count = layout.get("source", {}).get("page_count")
    if not isinstance(page_count, int) or page_count < 1:
        page_count = max((p.get("page", 0) for p in pages), default=0)

    for page in pages:
        page_number = page.get("page")
        for relationship_id in page.get("link_relationship_ids", []) or []:
            relationship = relationship_by_id.get(relationship_id)
            if relationship is None:
                errors.append(f"pdf_layout 第 {page_number} 页引用不存在的 relationship：{relationship_id}")
            elif relationship.get("source", {}).get("page") != page_number:
                errors.append(f"pdf_layout relationship {relationship_id} 的源页与页面索引不一致")
        for reference in page.get("cross_references", []) or []:
            relationship_id = reference.get("relationship_id")
            relationship = relationship_by_id.get(relationship_id)
            if relationship is None:
                errors.append(f"pdf_layout 第 {page_number} 页交叉引用悬空：{relationship_id}")
            elif relationship.get("target", {}).get("kind") not in ("internal", "named"):
                errors.append(f"pdf_layout 交叉引用 {relationship_id} 不是内部或命名目标")

    for relationship_id, relationship in relationship_by_id.items():
        target = relationship.get("target", {})
        target_page = target.get("page")
        if target_page is not None and (
            not isinstance(target_page, int) or target_page < 1
            or (page_count and target_page > page_count)
        ):
            errors.append(f"pdf_layout relationship {relationship_id} 的目标页越界：{target_page}")

    return errors


def _blank_paragraph_runs(doc):
    return sum(1 for p in doc.paragraphs if not p.text.strip())


def _check_all_xml_wellformed(zip_path):
    """遍历 DOCX 压缩包内所有 .xml/.rels，用 lxml 尝试解析确认 well-formed。

    XML well-formed（标签闭合、属性合法、无非法字符）是 Word 打开的必要条件；
    只要有一个部件解析失败，Word 会报"文档已损坏"并拒绝打开或提示是否修复。

    返回错误列表；空 list 表示所有 XML 都是 well-formed。
    """
    errors = []
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.namelist():
            if not (member.endswith(".xml") or member.endswith(".rels")):
                continue
            try:
                etree.fromstring(archive.read(member))
            except etree.XMLSyntaxError as exc:
                errors.append({
                    "part": member,
                    "line": getattr(exc, "lineno", None),
                    "message": str(exc)[:200],
                })
    return errors


def _normalize_rel_target(base_dir, target):
    """把 relationship 的 Target 相对路径转成 zip 内的绝对路径（去掉 ./ 和 ../）。

    OPC relationships 的 Target 通常写作相对当前 .rels 所在目录的路径；
    Word 打开时按此 resolve，指向的 part 必须真实存在，否则内容会被静默丢弃或报错。
    """
    if target.startswith("/"):
        parts = target.lstrip("/").split("/")
    else:
        base_parts = base_dir.split("/") if base_dir else []
        parts = base_parts + target.split("/")
    result = []
    for part in parts:
        if part == "" or part == ".":
            continue
        if part == "..":
            if result:
                result.pop()
        else:
            result.append(part)
    return "/".join(result)


def _validate_opc_package(zip_path):
    """检查 OPC (Open Packaging Conventions) 包完整性。

    Word 打开 DOCX 需要满足：
      1. [Content_Types].xml 存在且格式合法
      2. _rels/.rels 声明了 officeDocument 主关系，且指向存在的 part
      3. 所有 .rels 中 Internal 型 Target 都在 zip 内存在（悬空引用 = 内容丢失/报错）
      4. 每个非关系 part 都能匹配 Content_Types 里的 Override 或 Default extension
    检查通过并不能保证一定能被 Word 打开，但检查失败几乎必然打不开。
    """
    errors = []
    with zipfile.ZipFile(zip_path) as archive:
        members = set(archive.namelist())

        if "[Content_Types].xml" not in members:
            errors.append("缺少 [Content_Types].xml —— OPC 包必需，Word 会拒绝打开")
            return errors

        try:
            ct_root = etree.fromstring(archive.read("[Content_Types].xml"))
        except etree.XMLSyntaxError as exc:
            errors.append(f"[Content_Types].xml 解析失败：{exc}")
            return errors

        defaults = {}
        overrides = {}
        for child in ct_root:
            if child.tag == f"{{{_CT_NS}}}Default":
                ext = (child.get("Extension") or "").lower()
                if ext:
                    defaults[ext] = child.get("ContentType")
            elif child.tag == f"{{{_CT_NS}}}Override":
                partname = child.get("PartName") or ""
                if partname:
                    overrides[partname] = child.get("ContentType")

        # 主 rels 与 officeDocument 关系
        has_main = False
        main_target_norm = None
        if "_rels/.rels" not in members:
            errors.append("缺少 _rels/.rels —— 无法定位主文档，Word 拒绝打开")
        else:
            try:
                rels_root = etree.fromstring(archive.read("_rels/.rels"))
            except etree.XMLSyntaxError as exc:
                errors.append(f"_rels/.rels 解析失败：{exc}")
                rels_root = None
            if rels_root is not None:
                for rel in rels_root:
                    if rel.tag != f"{{{_REL_NS}}}Relationship":
                        continue
                    if rel.get("Type") in _MAIN_DOC_REL_TYPES:
                        has_main = True
                        target = rel.get("Target") or ""
                        main_target_norm = _normalize_rel_target("", target)
                        if main_target_norm not in members:
                            errors.append(f"主 relationship 指向不存在的 part：{target}")
                if not has_main:
                    errors.append("_rels/.rels 未声明 officeDocument 主关系")

        # 主文档必须在 Content_Types 里精确声明为 wordprocessingml.document.main+xml
        # （或 template/macroEnabled 变体）；Default extension="xml" 是通用类型，
        # 不足以让 Word 识别为 Word 主文档。
        if main_target_norm and main_target_norm in members:
            main_partname = "/" + main_target_norm
            main_ct = overrides.get(main_partname)
            if main_ct not in _MAIN_DOC_CONTENT_TYPES:
                errors.append(
                    f"主文档 {main_partname} 在 [Content_Types].xml 中未声明为 Word 主文档 content type"
                    f"（当前 Override={main_ct!r}）；Word 会报"
                    f"'该文件的 Office Open XML 文件无法打开，因为内容有错误'"
                )

        # 遍历所有 .rels 检查 Internal Target 是否指向存在的 part
        for member in members:
            if not member.endswith(".rels"):
                continue
            try:
                rels_root = etree.fromstring(archive.read(member))
            except etree.XMLSyntaxError:
                continue
            # base_dir 是 .rels 所在目录去掉 "_rels" 一级
            # 例如 word/_rels/document.xml.rels 的 base_dir 为 "word"
            segments = member.split("/")
            base_dir = "/".join(seg for seg in segments[:-1] if seg != "_rels")
            for rel in rels_root:
                if not rel.tag.endswith("}Relationship"):
                    continue
                if (rel.get("TargetMode") or "Internal") == "External":
                    continue
                target = rel.get("Target") or ""
                if not target:
                    continue
                target_norm = _normalize_rel_target(base_dir, target)
                if target_norm and target_norm not in members:
                    errors.append(f"{member} 引用不存在的 part：{target} (归一化 {target_norm})")

        # Content_Types 覆盖检查：非 .rels 的 part 都必须有 Override 或匹配 Default
        missing_ct = []
        for member in members:
            if member == "[Content_Types].xml" or member.endswith("/"):
                continue
            partname = "/" + member
            if partname in overrides:
                continue
            ext = member.rsplit(".", 1)[-1].lower() if "." in member else ""
            if ext and ext in defaults:
                continue
            missing_ct.append(member)
        if missing_ct:
            preview = missing_ct[:5]
            more = f"（共 {len(missing_ct)} 个，仅列出前 5 个）" if len(missing_ct) > 5 else ""
            errors.append(f"以下 part 在 [Content_Types].xml 中未声明：{preview}{more}")

    return errors


@functools.lru_cache(maxsize=1)
def _load_wml_schema(schema_path_str):
    """加载并缓存 wml.xsd 编译后的 XMLSchema。缓存 key 是绝对路径字符串。

    首次 build 约 40ms（26 个 XSD + import 链），后续 audit 复用同一实例。
    参数用字符串是为了配合 lru_cache 的 hashable 要求。
    """
    return etree.XMLSchema(etree.parse(schema_path_str))


def _strip_mc_ignorable(root):
    """按 mc:Ignorable 声明的前缀，剥除对应命名空间下的所有元素/属性。

    OOXML 的 Markup Compatibility (MC) 允许 Word 后续版本引入扩展属性（w14 段落 ID、
    w15 协作标记等）并声明 `mc:Ignorable="w14 w15 wp14"`——不识别扩展的 consumer
    可安全忽略。我们校验用的 ECMA-376 5th Transitional XSD 早于这些扩展，直接跑会
    对 w14/w15 属性误报"not allowed"。此函数模拟"忽略扩展"的 consumer 行为，
    剥除后 XSD 校验才能反映真正的结构错误。就地修改并返回同一 root。
    """
    ignorable = (root.get(f"{{{_MC_NS}}}Ignorable") or "").split()
    if not ignorable:
        return root
    # 遍历所有元素，累积前缀→URI 映射（子元素可能引入新前缀）
    nsmap = {}
    for element in root.iter():
        for prefix, uri in element.nsmap.items():
            if prefix and prefix not in nsmap:
                nsmap[prefix] = uri
    ignorable_uris = {nsmap[p] for p in ignorable if p in nsmap}
    ignorable_uris.add(_MC_NS)  # mc:AlternateContent / mc:Ignorable 自身也剥掉
    if not ignorable_uris:
        return root

    for element in root.iter():
        # 剥离属性
        for attr in list(element.attrib):
            if attr.startswith("{") and attr[1:].split("}")[0] in ignorable_uris:
                del element.attrib[attr]
        # 剥离子元素
        for child in list(element):
            tag = child.tag
            if isinstance(tag, str) and tag.startswith("{"):
                if tag[1:].split("}")[0] in ignorable_uris:
                    element.remove(child)
    return root


# 已知的 ECMA-376 5th Transitional schema 误报关键词——Office 2013+ 实际接受
# 但 schema 未收录。命中这些关键词的错误不上报，避免把"能被 Word 打开的正常文件"标错。
#   * w:rFonts@w:hint='cs' —— Complex Script hint 值，Office 2013+ 支持
#   * w:uiPriority —— 常见样式属性，schema 位置约束偏严
_KNOWN_XSD_FALSE_POSITIVES = ("'cs'", "uiPriority")


def _validate_ooxml_schema(zip_path, schemas_dir):
    """用 ECMA-376 5th Transitional XSD 校验 word/document.xml。

    只校验主文档：styles.xml/numbering.xml 里的 uiPriority 等元素在 schema 里位置
    约束偏严，误报多且价值低——Word 对这些辅助 part 更宽容。

    过滤已知误报（`_KNOWN_XSD_FALSE_POSITIVES`）并预处理 mc:Ignorable 后仍报错的
    才当作真错误上报。XSD 通过是 Word 打开的**必要**条件，不是充分条件。
    """
    schema_path = schemas_dir / "wml.xsd"
    if not schema_path.is_file():
        return {"available": False, "reason": f"未找到 {schema_path}", "issues": []}

    try:
        schema = _load_wml_schema(str(schema_path.resolve()))
    except Exception as exc:  # 加载失败不阻塞 audit，退化为提示
        return {"available": False, "reason": f"加载 wml.xsd 失败：{exc}", "issues": []}

    issues = []
    with zipfile.ZipFile(zip_path) as archive:
        member = "word/document.xml"
        if member not in archive.namelist():
            return {"available": True, "issues": [{"part": member, "message": "缺失"}]}
        try:
            root = etree.fromstring(archive.read(member))
        except etree.XMLSyntaxError as exc:
            return {"available": True, "issues": [{
                "part": member, "line": getattr(exc, "lineno", None),
                "message": str(exc)[:200],
            }]}

        _strip_mc_ignorable(root)
        if not schema.validate(root):
            for err in schema.error_log:
                message = err.message or ""
                if any(kw in message for kw in _KNOWN_XSD_FALSE_POSITIVES):
                    continue
                issues.append({
                    "part": member,
                    "line": err.line,
                    "message": message[:200],
                })
    return {"available": True, "issues": issues}


def _load_layout(layout_path):
    if not layout_path.is_file():
        return None
    data = json.loads(layout_path.read_text(encoding="utf-8"))
    version = data.get("schema_version", "0.0")
    parts = version.split(".")
    major = parts[0] if parts else "0"
    minor = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    if major != "1":
        raise SystemExit(f"unsupported pdf_layout schema_version: {version} (expected 1.x)")
    if minor > SUPPORTED_MINOR:
        print(
            f"warning: pdf_layout schema_version {version} newer than supported 1.{SUPPORTED_MINOR}; "
            f"未识别字段将被忽略",
            file=sys.stderr,
        )
    return data


def audit(path, layout, strict_tables=False, fidelity="high", rendered_pdf=None,
          page_count_hint=None, check_fonts=False, xsd_validate=False,
          schemas_dir=None):
    package_ok = zipfile.is_zipfile(path)
    bad_member = None
    if package_ok:
        with zipfile.ZipFile(path) as archive:
            bad_member = archive.testzip()
            package_ok = bad_member is None and "word/document.xml" in archive.namelist()

    report = {
        "源文件": str(path.resolve()),
        "文件大小_字节": path.stat().st_size,
        "文件包完整": package_ok,
        "损坏的压缩成员": bad_member,
        "保真模式": fidelity,
        "错误": [],
        "警告": [],
        "提示": [],
    }
    if not package_ok:
        report["错误"].append("DOCX 压缩包无效或缺少 word/document.xml")
        return report

    # OOXML 结构校验层 —— 检查通过是 Word 能打开的必要条件；失败几乎必然打不开。
    # 顺序：先 well-formed（最基础），再 OPC（结构完整），最后 XSD schema（细节）。
    wellformed_errors = _check_all_xml_wellformed(path)
    if wellformed_errors:
        report["XML完整性错误"] = wellformed_errors[:20]
        preview = [f"{e['part']}:{e.get('line') or '?'}" for e in wellformed_errors[:3]]
        report["错误"].append(
            f"{len(wellformed_errors)} 个 XML/rels part 解析失败（示例：{preview}）；"
            f"Word 会拒绝打开或提示'内容有错误'，需修复未闭合标签/非法字符/BOM 位置等"
        )
        # XML 都打不开就没必要继续跑后续深检，直接返回。
        return report

    opc_errors = _validate_opc_package(path)
    if opc_errors:
        report["OPC包完整性错误"] = opc_errors
        # OPC 层错误覆盖 Word 拒绝打开的主要原因，全部升级为错误。
        for err in opc_errors:
            report["错误"].append(f"OPC 结构错误：{err}")
        # OPC 结构错的文件 python-docx 也打不开（KeyError on missing part），
        # 后续深检没意义，直接返回让用户先修 OPC 层。
        return report

    if xsd_validate:
        schemas_dir = schemas_dir or _DEFAULT_SCHEMAS_DIR
        xsd_result = _validate_ooxml_schema(path, schemas_dir)
        if not xsd_result.get("available"):
            report["提示"].append(
                f"跳过 XSD 校验：{xsd_result.get('reason')}；"
                f"提供 --schemas-dir 或恢复 {_DEFAULT_SCHEMAS_DIR} 目录后可启用"
            )
        else:
            issues = xsd_result.get("issues") or []
            if issues:
                # 按命名空间分类：
                #   OMML (m:) 结构错就是 Word 拒绝渲染公式的根因——公式语义强依赖嵌套
                #   （分数 = m:fPr + m:num + m:den；脱离容器无法恢复），任何 "not expected"
                #   或 "Missing" 都意味着 Word 无法把子元素塞回正确的语义位置。
                #   wml (w:) 里的 "not expected" 多是子元素顺序错（tblStyle/tcW/tblW 位置），
                #   Word 按 tag 名识别、能宽容处理——实测 928 处 wml 违规也能打开。
                # 所以以"是否有 OMML 结构错"作为硬信号（不看数量），wml 违规仅警告。
                # 对照样本佐证：009.docx（11 oMath + Word 能打开）OMML 违规 = 0；
                # digital-communication（1423 oMath + Word 打不开）OMML 违规 = 169。
                # 没有中间样本能证明"少量 OMML 违规仍能被 Word 打开"，因此不设阈值。
                omml_issues = [it for it in issues
                               if "officeDocument/2006/math" in (it.get("message") or "")]
                wml_issues = [it for it in issues if it not in omml_issues]
                report["XSD校验错误"] = issues[:50]
                report["XSD校验统计"] = {
                    "总违规数": len(issues),
                    "OMML命名空间违规": len(omml_issues),
                    "wml命名空间违规": len(wml_issues),
                }

                if omml_issues:
                    # 按违规元素类型归类，报"具体错什么"而不是"错多少个"
                    omml_by_element = collections.Counter()
                    for it in omml_issues:
                        match = re.search(r"Element '\{[^}]+\}([^']+)'", it.get("message") or "")
                        omml_by_element[match.group(1) if match else "?"] += 1
                    kinds = ", ".join(f"m:{el}×{cnt}" for el, cnt in omml_by_element.most_common(6))
                    report["错误"].append(
                        f"OMML 公式结构错乱：{kinds}——这些 m: 命名空间元素出现在错误的父容器下或缺必需子元素。"
                        f"OMML 语义强依赖嵌套（分数由 m:fPr+m:num+m:den 构成），Word 无法从错位的元素恢复公式语义，"
                        f"会拒绝渲染公式或整个文件——需修复 m:oMath 内部子元素的容器归属"
                    )

                if wml_issues:
                    preview = [f"line {i.get('line')}: {i.get('message','')[:80]}" for i in wml_issues[:3]]
                    report["警告"].append(
                        f"WordprocessingML 结构违规 {len(wml_issues)} 处（示例：{preview}）；"
                        f"多为子元素顺序错，Word 按 tag 名识别能宽容处理，但可能有样式偏差，建议核查"
                    )

    doc = Document(str(path))

    # 结构级页数估算（不依赖 libreoffice）
    docx_min_pages, page_breakdown = _estimate_docx_pages(doc)
    report["结构页数估算"] = {
        "min_pages": docx_min_pages,
        **page_breakdown,
    }

    # B.2: 递归读嵌套 cell 文本；python-docx 不会把文本框暴露为普通段落，需从 XML 单独读取。
    all_text = "\n".join(p.text for p in doc.paragraphs)
    all_text += "\n" + "\n".join(c.text for c in _iter_all_cells(doc.tables))
    textbox_text = _textbox_text(doc)
    textbox_meaningful = _meaningful(textbox_text)
    all_text += "\n" + textbox_text
    docx_meaningful = _meaningful(all_text)
    report["可编辑字符数"] = docx_meaningful
    report["文本框可编辑字符数"] = textbox_meaningful
    report["正文段落数"] = len(doc.paragraphs)
    report["空段落数"] = _blank_paragraph_runs(doc)

    all_tables = list(_iter_all_tables(doc.tables))
    report["表格数量"] = len(all_tables)

    report["分节"] = []
    for index, section in enumerate(doc.sections, start=1):
        report["分节"].append({
            "序号": index,
            "页面宽度_毫米": round(section.page_width.mm, 2),
            "页面高度_毫米": round(section.page_height.mm, 2),
            "页面方向": str(section.orientation),
            "页边距_毫米": {
                "上": round(section.top_margin.mm, 2),
                "右": round(section.right_margin.mm, 2),
                "下": round(section.bottom_margin.mm, 2),
                "左": round(section.left_margin.mm, 2),
            },
        })

    table_reports = []
    for index, table in enumerate(all_tables, start=1):
        tblPr = table._tbl.tblPr
        table_width = tblPr.first_child_found_in("w:tblW") if tblPr is not None else None
        layout_prop = tblPr.first_child_found_in("w:tblLayout") if tblPr is not None else None
        grid = [dxa_value(column) for column in table._tbl.tblGrid]
        width_dxa = dxa_value(table_width)
        item = {
            "序号": index,
            "行数": len(table.rows),
            "首行列数": len(table.rows[0].cells) if table.rows else 0,
            "表格宽度_DXA": width_dxa,
            "布局方式": layout_prop.get(qn("w:type")) if layout_prop is not None else None,
            "网格列宽_DXA": grid,
        }
        # B.3 + C.4: 表格宽度 / 网格缺失 从警告升级为错误（可选严格模式，方案 §4.1 硬约束）
        if strict_tables:
            if width_dxa in (None, 0):
                report["错误"].append(f"第 {index} 个表格未设 DXA 固定总宽度")
            if not grid or any(v in (None, 0) for v in grid):
                report["错误"].append(f"第 {index} 个表格网格列宽不完整")
        else:
            if width_dxa in (None, 0) or (grid and any(v in (None, 0) for v in grid)):
                report["警告"].append(f"第 {index} 个表格缺少完整的固定宽度信息")
        table_reports.append(item)
    report["表格明细"] = table_reports

    fonts = _collect_run_fonts(doc)
    report["字体明细"] = fonts

    # 评测数据：字体/字号错误 15/15 case 出现，是最高频错误——除了字体名，
    # 也必须主动检查字号中位数与源 PDF 的偏差。
    sizes = _collect_run_font_sizes(doc)
    report["字号明细"] = sizes

    # 评测报告发现的收费字体问题：方正系列在 macOS/多数 Linux 上会被替换成默认字体，
    # 导致页数漂移、版式塌陷（Codex 用 Arial Unicode MS 就没这问题）。检测并警告。
    commercial_hits = _detect_commercial_fonts(fonts)
    if commercial_hits:
        report["提示"].append(
            f"检测到收费/系统受限字体（跨平台可能被替换）：{commercial_hits}；"
            f"建议改用跨平台字体，如 {list(CROSS_PLATFORM_FONT_HINT)[:5]} 等"
        )
        report["收费字体使用"] = commercial_hits

    for level, sigs in fonts.items():
        # B.5: 先过滤 (None, None) 空签名，再判断是否 > 1 组
        real_sigs = [s for s in sigs if any(x is not None for x in s)]
        if len(real_sigs) > 1:
            # 高保真模式：源 PDF 本就多字体是正常状况 —— 降为「提示」，不推 agent 去"统一美化"
            msg = f"{level} 层级检测到 {len(real_sigs)} 组字体签名：{real_sigs}"
            if fidelity == "high":
                report["提示"].append(msg + "（高保真模式下视为正常，除非用户要求统一）")
            else:
                report["警告"].append(msg + "，可能不一致")
        if level in {"body", "table"} and any(sig[1] is None for sig in real_sigs):
            # eastAsia 缺失是结构问题，非美观问题，两种模式都要警告
            report["警告"].append(f"{level} 层级缺少 w:eastAsia 字体，跨软件可能显示方框")

    report["列表"] = _collect_numbering(doc)
    report["页眉页脚"] = _header_footer_present(doc)

    # 页码/页眉/页脚混入正文检测——不需要 layout，独立可用
    page_marker_hits = _detect_page_marker_leaks(doc)
    if page_marker_hits:
        report["疑似页码正文混入"] = page_marker_hits
        if len(page_marker_hits) >= 3:
            report["警告"].append(
                f"正文中检测到 {len(page_marker_hits)} 处疑似页码/页眉页脚短行"
                f"（示例：{[h['text'] for h in page_marker_hits[:3]]}）；"
                f"评测「页眉页脚混入正文」5/15 case 出现，请把页码写入 Word 页脚区而非正文段落"
            )

    # OMML 公式必须用 Cambria Math；Word 硬编码要求，与 fidelity 模式无关
    omml_check = _check_omml_cambria_math(doc)
    report["OMML公式字体"] = omml_check
    if omml_check.get("omml_present") and omml_check.get("bad_run_count", 0) > 0:
        report["错误"].append(
            f"OMML 公式字体错误：{omml_check['bad_run_count']}/{omml_check['math_run_count']} "
            f"个 math run 未使用 Cambria Math（示例：{omml_check['bad_runs_sample']}）；"
            f"Word 只认 Cambria Math 渲染数学公式，其他字体会导致希腊字母/运算符退化为方框或错误字形，"
            f"请把每个 <m:r>/<w:rPr>/<w:rFonts> 的 w:ascii 和 w:hAnsi 都设为 \"Cambria Math\""
        )

    docx_links = _collect_docx_links(doc)
    report["目录与链接"] = {"docx": docx_links}

    if layout is not None:
        report["错误"].extend(_validate_layout_relationships(layout))
        pdf_meaningful = sum(p.get("meaningful_chars", 0) for p in layout.get("pages", []))
        pdf_tables = sum(len(p.get("tables", [])) for p in layout.get("pages", []))
        pdf_table_candidates = sum(len(p.get("table_candidates", [])) for p in layout.get("pages", []))
        primary_kind = layout.get("summary", {}).get("primary_kind")
        needs_ocr_pages = layout.get("summary", {}).get("needs_ocr_pages", [])
        coverage = docx_meaningful / pdf_meaningful if pdf_meaningful else 1.0
        report["与源PDF对比"] = {
            "primary_kind": primary_kind,
            "pdf有效字符数": pdf_meaningful,
            "docx有效字符数": docx_meaningful,
            "覆盖率": round(coverage, 4),
            "pdf表格总数": pdf_tables,
            "pdf表格候选数": pdf_table_candidates,
            "docx表格总数": len(all_tables),
            "需要OCR的页": needs_ocr_pages,
        }
        source_toc = layout.get("toc", []) or []
        source_relationships = layout.get("relationships", []) or []
        source_external_links = sum(
            relationship.get("target", {}).get("kind") in ("uri", "remote", "launch")
            for relationship in source_relationships
        )
        source_internal_links = sum(
            relationship.get("target", {}).get("kind") in ("internal", "named")
            for relationship in source_relationships
        )
        report["目录与链接"]["pdf"] = {
            "toc_entries": len(source_toc),
            "relationships": len(source_relationships),
            "external_links": source_external_links,
            "internal_links": source_internal_links,
        }
        if source_external_links > docx_links["external_hyperlinks"]:
            report["错误"].append(
                f"外部超链接缺失：源 PDF {source_external_links} 个，DOCX "
                f"{docx_links['external_hyperlinks']} 个"
            )
        if source_internal_links > docx_links["internal_references"]:
            report["错误"].append(
                f"内部跳转/交叉引用缺失：源 PDF {source_internal_links} 个，DOCX "
                f"{docx_links['internal_references']} 个"
            )
        if source_toc and docx_links["toc_fields"] == 0:
            report["警告"].append(
                f"源 PDF 有 {len(source_toc)} 个目录/书签条目，但 DOCX 未检测到 TOC 域；"
                "若使用静态可编辑目录，请人工核对层级与页码"
            )
        if primary_kind != "scan" and coverage < COVERAGE_THRESHOLD:
            report["错误"].append(
                f"覆盖率不足：DOCX 有效字符 {docx_meaningful} / PDF {pdf_meaningful} = {coverage:.1%}, 期望 ≥ {COVERAGE_THRESHOLD:.0%}"
            )
        if (pdf_tables + pdf_table_candidates) > 0 and len(all_tables) == 0:
            report["错误"].append(
                f"源 PDF 检测到 {pdf_tables} 个表格 + {pdf_table_candidates} 个候选表格，DOCX 未生成任何表格"
            )
        # B.4: 反向检测 —— PDF 无表但 DOCX 用了表
        if (pdf_tables + pdf_table_candidates) == 0 and len(all_tables) > 0 and primary_kind != "table":
            report["警告"].append(
                f"源 PDF 检测到 0 个表格但 DOCX 用了 {len(all_tables)} 个表——注意是否用表格伪造版式"
            )

        # 字号中位数对比 —— 评测最高频错误（字体/字号 15/15 case）
        pdf_body_size = _pdf_body_size_median(layout)
        if pdf_body_size is not None and "body" in sizes:
            docx_body_size = sizes["body"]["median"]
            size_drift = abs(docx_body_size - pdf_body_size) / pdf_body_size
            report["与源PDF对比"]["源正文字号中位数_pt"] = pdf_body_size
            report["与源PDF对比"]["DOCX正文字号中位数_pt"] = docx_body_size
            report["与源PDF对比"]["正文字号偏差"] = round(size_drift, 3)
            if size_drift > 0.20:
                msg = (
                    f"正文字号中位数偏差 {size_drift:.1%}：源 PDF {pdf_body_size:.1f}pt "
                    f"vs DOCX {docx_body_size:.1f}pt；评测最高频错误(15/15 case)，务必修正"
                )
                if fidelity == "high":
                    report["错误"].append(msg)
                else:
                    report["警告"].append(msg)

        # 表格逐个对比 —— 只对比数量抓不到「结构错 / 列宽错」（评测 8/15 + 5/15 case）
        pdf_tables_flat = [
            t for page in layout.get("pages", [])
            for t in (page.get("tables", []) or [])
        ]
        if pdf_tables_flat and all_tables:
            table_issues = _compare_tables_pairwise(pdf_tables_flat, all_tables)
            for issue in table_issues:
                if strict_tables:
                    report["错误"].append(issue)
                else:
                    report["警告"].append(issue)

        # 矢量区/图片消费 —— 评测「其他-横线/图标/边框丢失」14/15 case，
        # analyze_pdf_layout 已经用 vector_regions 标出 logo/装饰区，审计必须验证 DOCX 有对应图形。
        pdf_image_count = sum(len(p.get("images", []) or []) for p in layout.get("pages", []))
        pdf_vector_count = sum(len(p.get("vector_regions", []) or []) for p in layout.get("pages", []))
        docx_drawings = _count_docx_drawings(doc)
        report["与源PDF对比"]["源PDF嵌入图片数"] = pdf_image_count
        report["与源PDF对比"]["源PDF矢量区数"] = pdf_vector_count
        report["与源PDF对比"]["DOCX drawing 数"] = docx_drawings["total_drawings"]
        # 期望下限：全部嵌入图 + 至少一半矢量区（矢量区颗粒度粗，宽松兜底）
        expected_min_drawings = pdf_image_count + (pdf_vector_count // 2)
        if expected_min_drawings > 0 and docx_drawings["total_drawings"] < expected_min_drawings * 0.7:
            report["警告"].append(
                f"图形/矢量区疑似丢失：源 PDF {pdf_image_count} 张嵌入图 + "
                f"{pdf_vector_count} 个矢量区（logo/图标/横线等），"
                f"DOCX 只有 {docx_drawings['total_drawings']} 个 drawing；"
                f"评测「其他-装饰丢失」14/15 case 出现"
            )

        # 特殊字符集合差 —— 评测「特殊字符错误」9/15 case（①②、m³、公式符号等）
        pdf_special = set()
        for page in layout.get("pages", []):
            pdf_special.update(page.get("special_chars", []) or [])
        docx_special = _collect_docx_special_chars(doc)
        missing_special = sorted(pdf_special - docx_special)
        report["与源PDF对比"]["源PDF特殊字符数"] = len(pdf_special)
        report["与源PDF对比"]["DOCX特殊字符数"] = len(docx_special)
        if missing_special:
            report["与源PDF对比"]["DOCX缺失的特殊字符"] = missing_special
            # 只在缺失比例较大时警告，避免"三线表符号 ─ 因排版差异丢失"这种噪音
            if pdf_special and len(missing_special) / len(pdf_special) > 0.3:
                report["警告"].append(
                    f"特殊字符缺失 {len(missing_special)}/{len(pdf_special)}：{missing_special[:10]}"
                    f"{'...' if len(missing_special) > 10 else ''}；"
                    f"评测「特殊字符错误」9/15 case 出现，请对着源 PDF 补齐"
                )
        if needs_ocr_pages and docx_meaningful < pdf_meaningful:
            report["警告"].append(f"源 PDF 存在需要 OCR 的页 {needs_ocr_pages}，请确认已挂 OCR 或已向用户告知")
        pages = layout.get("pages", [])
        pdf_page_count = layout.get("source", {}).get("page_count") or len(pages)
        if rendered_pdf is not None:
            try:
                docx_page_count = _count_pdf_pages(rendered_pdf)
            except Exception as exc:
                report["警告"].append(f"无法从渲染 PDF 读取页数（{exc}）；请手工核对页数与源 PDF 是否一致")
                docx_page_count = None
            if docx_page_count is not None:
                report["与源PDF对比"]["pdf页数"] = pdf_page_count
                report["与源PDF对比"]["docx渲染页数"] = docx_page_count
                if docx_page_count != pdf_page_count:
                    msg = f"页数不一致：源 PDF {pdf_page_count} 页 vs DOCX 渲染 {docx_page_count} 页"
                    # 高保真模式：页数偏差是保真失败硬约束
                    if fidelity == "high":
                        report["错误"].append(msg + "（高保真模式硬阻塞：检查页边距、字体大小、分节、图片缩放）")
                    else:
                        report["警告"].append(msg)

        # 结构级页数硬对比（不依赖 libreoffice）
        target_pages = page_count_hint if page_count_hint is not None else pdf_page_count
        if target_pages:
            report["与源PDF对比"]["源PDF页数"] = pdf_page_count
            report["与源PDF对比"]["DOCX结构最小页数"] = docx_min_pages
            report["与源PDF对比"]["页数上限依据"] = target_pages
            if docx_min_pages > target_pages:
                # 显式分页 + 硬分节已经超过源 PDF 页数 —— DOCX 一定放不下源 PDF 那么少页
                msg = (
                    f"结构页数超标：DOCX 结构最小页数 {docx_min_pages} 页（显式分页 {page_breakdown['explicit_page_breaks']} + "
                    f"硬分节 {page_breakdown['hard_section_breaks']} + 首页 1）> 期望 {target_pages} 页；"
                    f"必然与源 PDF 页数不一致，检查是否有多余的 <w:br type=\"page\"> 或多余的分节"
                )
                if fidelity == "high":
                    report["错误"].append(msg)
                else:
                    report["警告"].append(msg)
            elif rendered_pdf is None:
                # 有 hint 无 rendered，就把结构估算作为唯一依据；给出提示说明它是保守估计
                report["提示"].append(
                    f"结构页数估算 {docx_min_pages} ≤ 期望 {target_pages}（未提供 --rendered-pdf，"
                    f"实际渲染页数可能因字体度量差异高于估算；libreoffice 可用时建议再传 --rendered-pdf 精准核对）"
                )

        # 字体存在性预检
        if check_fonts:
            needed_fonts = _collect_source_fonts(layout)
            report["与源PDF对比"]["源PDF字体清单"] = needed_fonts
            installed = _installed_fonts_via_fc_list()
            if installed is None:
                report["提示"].append("fc-list 不可用，跳过字体存在性检查；请在 Word 中人工核对字体")
            elif needed_fonts:
                missing = [f for f in needed_fonts if not _match_font_family(f, installed)]
                if missing:
                    report["警告"].append(
                        f"以下源 PDF 字体在本机 fc-list 中未找到，libreoffice 渲染时会做字体替换、"
                        f"可能造成 line metrics 变化与页数漂移：{missing}"
                    )
                    report["与源PDF对比"]["缺失字体"] = missing
                else:
                    report["与源PDF对比"]["缺失字体"] = []

        if pages and doc.sections:
            first_pdf = pages[0]["size"]
            first_docx = doc.sections[0]
            expected_w_mm = first_pdf["width"] * 25.4 / 72
            expected_h_mm = first_pdf["height"] * 25.4 / 72
            if abs(first_docx.page_width.mm - expected_w_mm) > 5 or abs(first_docx.page_height.mm - expected_h_mm) > 5:
                report["警告"].append(
                    f"首节页面尺寸与源 PDF 首页差异 > 5mm: PDF {expected_w_mm:.1f}x{expected_h_mm:.1f} vs DOCX {first_docx.page_width.mm:.1f}x{first_docx.page_height.mm:.1f}"
                )

    # 可编辑文字是 Word 产物的硬要求，必须在统一审计入口中阻断，
    # 不能仅由 CLI 参数控制，否则直接调用 audit() 时可能绕过检查。
    if docx_meaningful == 0:
        report["错误"].append("文档中未发现可编辑文字")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_docx", type=Path)
    parser.add_argument("--json", type=Path, help="写入审计报告 JSON")
    parser.add_argument("--layout", type=Path, help="pdf_layout.json，触发覆盖率与页面尺寸对比")
    parser.add_argument("--strict-tables", action="store_true",
                        help="表格宽度/网格缺失从警告升级为错误（对齐方案 §4.1 硬约束）")
    parser.add_argument("--fidelity", choices=["high", "neutral"], default="high",
                        help="high（默认，PDF 转 Word 用）时把'字体多组签名'降为提示，避免推 agent 自作主张统一美化；"
                             "neutral 保留为警告")
    parser.add_argument("--rendered-pdf", type=Path,
                        help="TARGET_DOCX 用 docx2pdf.py 渲染后的 PDF 路径；给了后自动核对 DOCX 页数与源 PDF 页数是否一致（高保真模式下页数不一致→错误）")
    parser.add_argument("--page-count-hint", type=int,
                        help="期望页数（通常 = pdf_layout.source.page_count）。用于结构级页数估算：DOCX 显式 <w:br type=\"page\"> + 硬分节 + 首页 > hint 即报错。不依赖 docx2pdf.py 渲染结果")
    parser.add_argument("--check-fonts", action="store_true",
                        help="用 fc-list 检查 pdf_layout.pages[].text_lines[].font 声明的字体是否本机可用；缺字体会导致 libreoffice 沉默替换、进而使页数漂移")
    parser.add_argument("--xsd-validate", action="store_true",
                        help="启用 OOXML XSD schema 校验（默认关闭）；加载 scripts/ooxml_schemas/wml.xsd 校验 "
                             "word/document.xml，已知误报如 rFonts@hint='cs'、uiPriority 会被过滤。"
                             "默认关闭的原因：wml 结构违规 Word 通常宽容处理（可用 docx2pdf.py --reformat 洗一遍），"
                             "而真正影响 Word 打开的公式结构错已由 OMML Cambria Math 校验兜住")
    parser.add_argument("--schemas-dir", type=Path,
                        help=f"OOXML XSD 目录，默认 {_DEFAULT_SCHEMAS_DIR}（ECMA-376 5th Transitional + OPC，26+4 个 XSD）")
    args = parser.parse_args()

    if not args.input_docx.is_file():
        print(f"error: docx not found: {args.input_docx}", file=sys.stderr)
        return 1

    try:
        layout = _load_layout(args.layout) if args.layout else None
    except SystemExit:
        raise
    except Exception as exc:
        print(f"error: cannot load layout: {exc}", file=sys.stderr)
        return 1

    report = audit(args.input_docx, layout, strict_tables=args.strict_tables,
                   fidelity=args.fidelity, rendered_pdf=args.rendered_pdf,
                   page_count_hint=args.page_count_hint, check_fonts=args.check_fonts,
                   xsd_validate=args.xsd_validate,
                   schemas_dir=args.schemas_dir)

    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(rendered, encoding="utf-8")
        print(f"审计报告：{args.json}")
    else:
        print(rendered)

    return 1 if report["错误"] else 0


if __name__ == "__main__":
    raise SystemExit(main())