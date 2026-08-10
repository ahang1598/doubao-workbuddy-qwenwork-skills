#!/usr/bin/env python3
"""Read-only DOCX QA audit for journal-format runs.

The audit intentionally stays structural. Rendering is handled by render_docx.py.
This script records the package evidence needed to catch common regressions:
section/page layout drift, direct formatting that can override role styles,
numbering/style references, and media/OLE/relationship preservation.
"""

import argparse
import json
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter

W_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
R_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
PKG_REL_NS = 'http://schemas.openxmlformats.org/package/2006/relationships'
WP_NS = 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'
A_NS = 'http://schemas.openxmlformats.org/drawingml/2006/main'
M_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/math'

NS = {
    'w': W_NS,
    'r': R_NS,
    'pr': PKG_REL_NS,
    'wp': WP_NS,
    'a': A_NS,
    'm': M_NS,
}

EMU_PER_INCH = 914400

HEADING_STYLE_RE = re.compile(r'^(?:heading|head)\s*([1-9])$|^(?:[678]heading)([1-3])$', re.I)
NUMBERED_HEADING_RE = re.compile(r'^\s*(\d+(?:\.\d+)*)\s+\S+')
FIELD_UPDATE_TYPES = {'PAGE', 'NUMPAGES', 'TOC', 'REF', 'PAGEREF', 'SEQ'}

KEY_PARTS = [
    '[Content_Types].xml',
    'word/document.xml',
    'word/styles.xml',
    'word/numbering.xml',
    'word/settings.xml',
    'word/fontTable.xml',
    'word/theme/theme1.xml',
]


def qn(ns, local):
    return f'{{{ns}}}{local}'


def read_xml(zf, name):
    try:
        return ET.fromstring(zf.read(name))
    except KeyError:
        return None


def attr(el, local, default=None):
    if el is None:
        return default
    return el.get(qn(W_NS, local), default)


def para_text(p):
    return ''.join(t.text or '' for t in p.findall('.//w:t', NS))


def local_name(tag):
    return tag.split('}', 1)[-1] if '}' in tag else tag


def attrs_dict(el):
    if el is None:
        return {}
    return {local_name(k): v for k, v in el.attrib.items()}


def xml_child_profile(parent, child_name):
    child = parent.find(f'w:{child_name}', NS) if parent is not None else None
    return attrs_dict(child)


def paragraph_style_id(p):
    p_pr = p.find('w:pPr', NS)
    p_style = p_pr.find('w:pStyle', NS) if p_pr is not None else None
    return attr(p_style, 'val', '')


def load_style_spacing_map(styles_root):
    if styles_root is None:
        return {}
    result = {}
    for style in styles_root.findall('w:style', NS):
        if attr(style, 'type') != 'paragraph':
            continue
        style_id = attr(style, 'styleId')
        if not style_id:
            continue
        p_pr = style.find('w:pPr', NS)
        spacing = p_pr.find('w:spacing', NS) if p_pr is not None else None
        if spacing is not None:
            result[style_id] = attrs_dict(spacing)
    return result


def paragraph_high_inline_content_kinds(p):
    kinds = set()
    for node in p.iter():
        lname = local_name(node.tag)
        if lname in ('drawing', 'pict'):
            kinds.add(lname)
        elif lname in ('object', 'OLEObject', 'objectEmbed', 'control'):
            kinds.add('ole_object')
        elif lname in ('oMath', 'oMathPara') or node.tag.startswith(f'{{{M_NS}}}'):
            kinds.add('omml')
    return sorted(kinds)


def effective_spacing_attrs(p, style_spacing_map):
    p_pr = p.find('w:pPr', NS)
    direct = p_pr.find('w:spacing', NS) if p_pr is not None else None
    if direct is not None:
        return attrs_dict(direct), 'direct'
    style_id = paragraph_style_id(p)
    if style_id and style_spacing_map.get(style_id):
        return dict(style_spacing_map[style_id]), f'style:{style_id}'
    return {}, None


def inches_from_emu(value):
    if value in (None, ''):
        return None
    try:
        return round(int(value) / EMU_PER_INCH, 3)
    except Exception:
        return None


def heading_level_from_style(style_id):
    if not style_id:
        return None
    normalized = re.sub(r'[\s_\-]+', '', style_id).lower()
    match = re.search(r'heading([1-9])$', normalized) or re.search(r'head([1-9])$', normalized)
    if match:
        return int(match.group(1))
    match = re.match(r'[678]heading([1-3])$', normalized)
    if match:
        return int(match.group(1))
    return None


def numbered_heading_level(text):
    match = NUMBERED_HEADING_RE.match(text or '')
    if not match:
        return None
    return match.group(1).count('.') + 1


def iter_paragraphs(root):
    if root is None:
        return []
    return root.findall('.//w:p', NS)


def iter_content_parts(zf):
    for name in zf.namelist():
        if not name.startswith('word/') or not name.endswith('.xml'):
            continue
        base = name.rsplit('/', 1)[-1]
        if base == 'document.xml':
            yield name
        elif base.startswith('header') and base.endswith('.xml'):
            yield name
        elif base.startswith('footer') and base.endswith('.xml'):
            yield name
        elif base in ('footnotes.xml', 'endnotes.xml'):
            yield name


def rels_path_for_part(part_name):
    directory, base = part_name.rsplit('/', 1)
    return f'{directory}/_rels/{base}.rels'


def load_rels_map(zf, part_name):
    rels_name = rels_path_for_part(part_name)
    if rels_name not in zf.namelist():
        return {}
    try:
        root = ET.fromstring(zf.read(rels_name))
    except Exception:
        return {}
    rels = {}
    for rel in root.findall(f'{{{PKG_REL_NS}}}Relationship'):
        rid = rel.get('Id')
        target = rel.get('Target')
        rel_type = rel.get('Type')
        if rid:
            rels[rid] = {'target': target, 'type': rel_type}
    return rels


def section_audit(doc_root):
    sections = []
    if doc_root is None:
        return sections
    for idx, sect in enumerate(doc_root.findall('.//w:sectPr', NS), start=1):
        pg_sz = sect.find('w:pgSz', NS)
        pg_mar = sect.find('w:pgMar', NS)
        cols = sect.find('w:cols', NS)
        header_refs = sect.findall('w:headerReference', NS)
        footer_refs = sect.findall('w:footerReference', NS)
        sections.append({
            'index': idx,
            'page_size': {
                'w': attr(pg_sz, 'w'),
                'h': attr(pg_sz, 'h'),
                'orient': attr(pg_sz, 'orient'),
            },
            'margins': {
                key: attr(pg_mar, key)
                for key in ('top', 'right', 'bottom', 'left', 'header', 'footer', 'gutter')
            },
            'columns': {
                'num': attr(cols, 'num', '1'),
                'space': attr(cols, 'space'),
                'equalWidth': attr(cols, 'equalWidth'),
            },
            'headers': [
                {'type': attr(h, 'type'), 'rid': h.get(qn(R_NS, 'id'))}
                for h in header_refs
            ],
            'footers': [
                {'type': attr(f, 'type'), 'rid': f.get(qn(R_NS, 'id'))}
                for f in footer_refs
            ],
        })
    return sections


def formatting_audit(doc_root):
    paragraphs = list(iter_paragraphs(doc_root))
    direct_paragraphs = 0
    direct_runs = 0
    style_counts = Counter()
    font_counts = Counter()
    numbered_paragraphs = 0
    examples = {
        'direct_paragraph_formatting': [],
        'direct_run_formatting': [],
        'heading_like_not_heading_style': [],
    }

    for idx, p in enumerate(paragraphs, start=1):
        text = para_text(p).strip()
        p_pr = p.find('w:pPr', NS)
        p_style = p_pr.find('w:pStyle', NS) if p_pr is not None else None
        style_id = attr(p_style, 'val', '')
        if style_id:
            style_counts[style_id] += 1
        direct_p = False
        if p_pr is not None:
            for tag in ('w:ind', 'w:spacing', 'w:jc', 'w:tabs', 'w:pBdr', 'w:shd'):
                if p_pr.find(tag, NS) is not None:
                    direct_p = True
                    break
            if p_pr.find('w:numPr', NS) is not None:
                numbered_paragraphs += 1
                direct_p = True
        if direct_p:
            direct_paragraphs += 1
            if len(examples['direct_paragraph_formatting']) < 12:
                examples['direct_paragraph_formatting'].append({
                    'paragraph_index': idx,
                    'style_id': style_id,
                    'text': text[:120],
                })

        heading_like = (
            text
            and len(text) <= 90
            and not re.search(r'[。.;；]$', text)
            and re.match(r'^(?:\d+(?:\.\d+)*\s+|[一二三四五六七八九十]+、|[（(]?[一二三四五六七八九十]+[）)]).+', text)
        )
        if heading_like and not re.search(r'heading|head|title', style_id, re.I):
            if len(examples['heading_like_not_heading_style']) < 12:
                examples['heading_like_not_heading_style'].append({
                    'paragraph_index': idx,
                    'style_id': style_id,
                    'text': text[:120],
                })

        for r in p.findall('w:r', NS):
            r_pr = r.find('w:rPr', NS)
            if r_pr is None:
                continue
            r_text = ''.join(t.text or '' for t in r.findall('.//w:t', NS)).strip()
            direct_r = False
            for child in list(r_pr):
                local = child.tag.split('}')[-1]
                if local in ('rFonts', 'sz', 'szCs', 'b', 'i', 'color', 'u', 'vertAlign', 'position', 'spacing', 'highlight', 'shd'):
                    direct_r = True
                if local == 'rFonts':
                    for key in ('ascii', 'hAnsi', 'eastAsia', 'cs', 'asciiTheme', 'hAnsiTheme', 'eastAsiaTheme'):
                        value = attr(child, key)
                        if value:
                            font_counts[value] += max(len(r_text), 1)
            if direct_r:
                direct_runs += 1
                if len(examples['direct_run_formatting']) < 12:
                    examples['direct_run_formatting'].append({
                        'paragraph_index': idx,
                        'run_text': r_text[:80],
                    })

    return {
        'paragraph_count': len(paragraphs),
        'numbered_paragraphs': numbered_paragraphs,
        'direct_paragraph_formatting_paragraphs': direct_paragraphs,
        'direct_run_formatting_runs': direct_runs,
        'styles_by_paragraph_count': dict(style_counts.most_common(25)),
        'fonts_by_direct_run_char_count': dict(font_counts.most_common(25)),
        'examples': examples,
    }


def border_profile(container, path):
    borders = container.find(path, NS) if container is not None else None
    if borders is None:
        return {}
    return {
        side: attrs_dict(borders.find(f'w:{side}', NS))
        for side in ('top', 'bottom', 'left', 'right', 'insideH', 'insideV')
        if borders.find(f'w:{side}', NS) is not None
    }


def border_is_visible(attrs):
    val = (attrs or {}).get('val')
    return bool(val and val not in ('nil', 'none'))


def cell_border_profile(tc):
    tc_pr = tc.find('w:tcPr', NS) if tc is not None else None
    return border_profile(tc_pr, 'w:tcBorders')


def cell_grid_span(tc):
    tc_pr = tc.find('w:tcPr', NS) if tc is not None else None
    grid_span = tc_pr.find('w:gridSpan', NS) if tc_pr is not None else None
    try:
        return max(1, int(attr(grid_span, 'val', '1') or '1'))
    except Exception:
        return 1


def cell_has_vertical_merge(tc):
    tc_pr = tc.find('w:tcPr', NS) if tc is not None else None
    return tc_pr is not None and tc_pr.find('w:vMerge', NS) is not None


def row_effective_column_count(tr):
    return sum(cell_grid_span(tc) for tc in tr.findall('w:tc', NS))


def row_has_merge_topology(tr):
    return any(
        cell_grid_span(tc) > 1 or cell_has_vertical_merge(tc)
        for tc in tr.findall('w:tc', NS)
    )


def row_cell_texts(tr):
    return [para_text(tc).strip() for tc in tr.findall('w:tc', NS)]


def text_looks_numeric_data(text):
    compact = re.sub(r'\s+', '', text or '')
    if not compact:
        return False
    if re.fullmatch(r'[+-]?\d+(?:\.\d+)?%?', compact):
        return True
    if re.fullmatch(r'[+-]?\d+(?:\.\d+)?(?:±|~|-|—|–|至|到)[+-]?\d+(?:\.\d+)?%?', compact):
        return True
    if re.fullmatch(r'[×xX√/\\-]+', compact):
        return True
    return False


def row_feature_for_header_inference(row, max_cols):
    texts = row_cell_texts(row)
    nonempty = [text for text in texts if text]
    cell_count = max(1, len(texts))
    avg_cell_len = sum(len(text) for text in nonempty) / max(1, len(nonempty))
    numeric_cells = sum(1 for text in nonempty if text_looks_numeric_data(text))
    numeric_ratio = numeric_cells / float(max(1, len(nonempty)))
    text = ' '.join(nonempty)
    labelish_re = re.compile(
        r'^(Top\s*\d+|Acc(?:uracy)?|Precision|Recall|F1|AP|mAP|P@\d+|R@\d+|'
        r'准确率|精确率|召回率|分类方法|姿态维度|目标|指标|方法|维度|类别|模型|数据集|'
        r'均值|标准差|Mean|Std\.?|Dataset|Method|Metric|Category|Dimension)$',
        re.I,
    )
    labelish_cells = sum(1 for text in nonempty if labelish_re.match(text.strip()))
    has_sentence_punct = bool(re.search(r'[。；;.!?？]', text))
    return {
        'text': text,
        'nonempty_cells': len(nonempty),
        'cell_count': cell_count,
        'effective_cols': row_effective_column_count(row),
        'max_cols': max_cols,
        'avg_cell_len': avg_cell_len,
        'numeric_cells': numeric_cells,
        'numeric_ratio': numeric_ratio,
        'labelish_ratio': labelish_cells / float(max(1, len(nonempty))),
        'has_merge_topology': row_has_merge_topology(row),
        'has_spanning_group_cell': any(cell_grid_span(tc) > 1 for tc in row.findall('w:tc', NS)),
        'raw_cell_count_below_grid': cell_count < max_cols,
        'has_sentence_punct': has_sentence_punct,
        'is_short_label_row': bool(nonempty) and avg_cell_len <= 18 and not has_sentence_punct,
        'is_data_like': (
            numeric_cells >= 2
            or numeric_ratio >= 0.5
            or (numeric_cells >= 1 and avg_cell_len > 18)
        ),
    }


def infer_three_line_header_row_info(rows):
    if len(rows) <= 1:
        return {'count': 1 if rows else 0, 'features': [], 'reason': 'single_or_empty_table'}
    max_cols = max(row_effective_column_count(row) for row in rows) or 1
    features = [row_feature_for_header_inference(row, max_cols) for row in rows[: min(4, len(rows))]]
    header_count = 1
    reasons = ['first_row_header']
    for idx, feature in enumerate(features[1:], start=1):
        if idx >= len(rows) - 1:
            break
        if not feature['text']:
            continue
        prev = features[idx - 1] if idx - 1 < len(features) else {}
        next_feature = features[idx + 1] if idx + 1 < len(features) else {}
        merge_continuation = bool(prev.get('has_merge_topology') or feature['has_merge_topology'])
        grouped_header_continuation = (
            feature['is_short_label_row']
            and (
                merge_continuation
                or prev.get('has_spanning_group_cell')
                or prev.get('raw_cell_count_below_grid')
            )
            and (
                not next_feature
                or next_feature.get('is_data_like')
                or next_feature.get('avg_cell_len', 99) > feature.get('avg_cell_len', 0)
            )
        )
        likely_subheader = (
            feature['is_short_label_row']
            and (
                merge_continuation
                or feature['labelish_ratio'] >= 0.5
                or (next_feature and next_feature.get('is_data_like') and feature['numeric_cells'] == 0)
                or grouped_header_continuation
            )
        )
        if likely_subheader:
            header_count = idx + 1
            reasons.append(f'row_{idx}_subheader')
            continue
        if feature['is_data_like']:
            reasons.append(f'row_{idx}_data_like_stop')
        break
    return {
        'count': max(1, min(header_count, len(rows) - 1)),
        'features': features,
        'reason': ','.join(reasons),
    }


def visible_cell_side_count(row, side):
    count = 0
    cells = row.findall('w:tc', NS)
    for tc in cells:
        if border_is_visible(cell_border_profile(tc).get(side)):
            count += 1
    return count


def visible_cell_vertical_border_count(rows):
    count = 0
    for row in rows:
        for tc in row.findall('w:tc', NS):
            borders = cell_border_profile(tc)
            if any(border_is_visible(borders.get(side)) for side in ('left', 'right', 'insideV')):
                count += 1
    return count


def audit_three_line_border_integrity(rows, borders):
    if not rows:
        return []
    issues = []
    header_info = infer_three_line_header_row_info(rows)
    header_rows = header_info.get('count') or 1
    header_bottom_index = max(0, header_rows - 1)
    first_cells = rows[0].findall('w:tc', NS)
    header_bottom_cells = rows[header_bottom_index].findall('w:tc', NS)
    final_cells = rows[-1].findall('w:tc', NS)
    visible_vertical = any(border_is_visible(borders.get(side)) for side in ('left', 'right', 'insideV')) or visible_cell_vertical_border_count(rows)
    visible_horizontal = any(border_is_visible(borders.get(side)) for side in ('top', 'bottom', 'insideH')) or any(
        visible_cell_side_count(row, 'top') or visible_cell_side_count(row, 'bottom')
        for row in rows
    )
    likely_three_line = visible_horizontal and not visible_vertical
    if not likely_three_line:
        return []
    if first_cells and not border_is_visible(borders.get('top')) and visible_cell_side_count(rows[0], 'top') < len(first_cells):
        issues.append({
            'type': 'three_line_top_rule_incomplete',
            'message': 'possible three-line table is missing complete first-row top cell borders',
            'expected_cells': len(first_cells),
            'visible_cells': visible_cell_side_count(rows[0], 'top'),
        })
    if header_bottom_cells and visible_cell_side_count(rows[header_bottom_index], 'bottom') < len(header_bottom_cells):
        issues.append({
            'type': 'three_line_header_bottom_rule_incomplete',
            'message': 'possible three-line table is missing the bottom rule under the final inferred header row',
            'header_rows': header_rows,
            'header_inference_reason': header_info.get('reason'),
            'expected_cells': len(header_bottom_cells),
            'visible_cells': visible_cell_side_count(rows[header_bottom_index], 'bottom'),
        })
    if header_rows > 1:
        for sep_idx in range(0, header_bottom_index):
            cells = rows[sep_idx].findall('w:tc', NS)
            if cells and visible_cell_side_count(rows[sep_idx], 'bottom') < len(cells):
                issues.append({
                    'type': 'three_line_multi_header_separator_incomplete',
                    'message': 'multi-row header lacks a horizontal separator between header levels',
                    'separator_after_row': sep_idx + 1,
                    'header_rows': header_rows,
                    'expected_cells': len(cells),
                    'visible_cells': visible_cell_side_count(rows[sep_idx], 'bottom'),
                })
    if final_cells and not border_is_visible(borders.get('bottom')) and visible_cell_side_count(rows[-1], 'bottom') < len(final_cells):
        issues.append({
            'type': 'three_line_bottom_rule_incomplete',
            'message': 'possible three-line table is missing complete final-row bottom cell borders',
            'expected_cells': len(final_cells),
            'visible_cells': visible_cell_side_count(rows[-1], 'bottom'),
        })
    return issues


def table_geometry_audit(doc_root):
    if doc_root is None:
        return {'table_count': 0, 'issue_count': 0, 'issues': [], 'tables': []}
    tables = []
    issues = []
    for table_idx, tbl in enumerate(doc_root.findall('.//w:tbl', NS), start=1):
        tbl_pr = tbl.find('w:tblPr', NS)
        tbl_grid = tbl.find('w:tblGrid', NS)
        rows = tbl.findall('w:tr', NS)
        grid = [
            int(col.get(qn(W_NS, 'w'), '0') or '0')
            for col in (tbl_grid.findall('w:gridCol', NS) if tbl_grid is not None else [])
        ]
        tbl_w = xml_child_profile(tbl_pr, 'tblW')
        tbl_ind = xml_child_profile(tbl_pr, 'tblInd')
        tbl_layout = xml_child_profile(tbl_pr, 'tblLayout')
        tbl_cell_mar = attrs_dict(tbl_pr.find('w:tblCellMar', NS)) if tbl_pr is not None and tbl_pr.find('w:tblCellMar', NS) is not None else {}
        table_issues = []
        width_value = int(tbl_w.get('w', '0') or '0') if tbl_w else 0
        width_type = tbl_w.get('type')
        if width_type in ('dxa', 'pct') and width_value and grid and width_type == 'dxa':
            delta = abs(sum(grid) - width_value)
            if delta > 36:
                table_issues.append({
                    'type': 'grid_width_mismatch',
                    'message': 'tblGrid sum differs from explicit tblW',
                    'tblW': width_value,
                    'grid_sum': sum(grid),
                })
        if width_type in (None, 'auto') or width_value == 0:
            table_issues.append({
                'type': 'auto_or_missing_table_width',
                'message': 'table width is auto/missing; width may render differently across Word engines',
                'tblW': tbl_w,
            })
        row_profiles = []
        for row_idx, tr in enumerate(rows, start=1):
            cells = tr.findall('w:tc', NS)
            cell_widths = []
            merged_cells = 0
            tc_margin_profiles = []
            cell_border_count = 0
            for tc in cells:
                tc_pr = tc.find('w:tcPr', NS)
                tc_w = xml_child_profile(tc_pr, 'tcW')
                if tc_w:
                    try:
                        cell_widths.append(int(tc_w.get('w', '0') or '0'))
                    except Exception:
                        cell_widths.append(0)
                else:
                    cell_widths.append(0)
                if tc_pr is not None and any(tc_pr.find(f'w:{name}', NS) is not None for name in ('gridSpan', 'hMerge', 'vMerge')):
                    merged_cells += 1
                if tc_pr is not None and tc_pr.find('w:tcBorders', NS) is not None:
                    cell_border_count += 1
                tc_mar = tc_pr.find('w:tcMar', NS) if tc_pr is not None else None
                if tc_mar is not None:
                    tc_margin_profiles.append({
                        side: attrs_dict(tc_mar.find(f'w:{side}', NS))
                        for side in ('top', 'bottom', 'start', 'end', 'left', 'right')
                        if tc_mar.find(f'w:{side}', NS) is not None
                    })
            if grid and len(cell_widths) >= len(grid) and not merged_cells:
                comparable = cell_widths[:len(grid)]
                if any(abs((comparable[i] or 0) - grid[i]) > 36 for i in range(len(grid))):
                    table_issues.append({
                        'type': 'cell_width_grid_mismatch',
                        'message': 'row cell widths differ from tblGrid column widths',
                        'row': row_idx,
                        'grid': grid,
                        'cell_widths': comparable,
                    })
            row_profiles.append({
                'row': row_idx,
                'cells': len(cells),
                'merged_cells': merged_cells,
                'cell_widths': cell_widths[:12],
                'has_header_flag': tr.find('w:trPr/w:tblHeader', NS) is not None,
                'cell_border_count': cell_border_count,
                'cell_margin_profiles': tc_margin_profiles[:3],
            })
        borders = border_profile(tbl_pr, 'w:tblBorders')
        vertical_line_evidence = bool(
            borders.get('insideV') or borders.get('left') or borders.get('right') or
            any(r.get('cell_border_count') for r in row_profiles)
        )
        horizontal_line_evidence = bool(
            borders.get('top') or borders.get('bottom') or borders.get('insideH') or
            any(r.get('cell_border_count') for r in row_profiles)
        )
        if not borders and not any(r.get('cell_border_count') for r in row_profiles):
            table_issues.append({
                'type': 'no_explicit_table_borders',
                'message': 'table has no explicit tblBorders/tcBorders evidence',
            })
        table_issues.extend(audit_three_line_border_integrity(rows, borders))
        table_profile = {
            'index': table_idx,
            'rows': len(rows),
            'grid_columns': len(grid),
            'grid_widths': grid[:20],
            'grid_sum': sum(grid),
            'tblW': tbl_w,
            'tblInd': tbl_ind,
            'tblLayout': tbl_layout,
            'tblCellMar': tbl_cell_mar,
            'tblBorders': borders,
            'vertical_line_evidence': vertical_line_evidence,
            'horizontal_line_evidence': horizontal_line_evidence,
            'row_profiles': row_profiles[:8],
            'issues': table_issues[:12],
        }
        tables.append(table_profile)
        for issue in table_issues:
            issue_with_table = dict(issue)
            issue_with_table['table_index'] = table_idx
            issues.append(issue_with_table)
    return {
        'table_count': len(tables),
        'issue_count': len(issues),
        'issues': issues[:40],
        'tables': tables[:20],
    }


def image_anchor_audit(zf):
    rows = []
    kind_counts = Counter()
    missing_targets = []
    header_footer_background_images = []
    fixed_line_spacing_high_inline = []
    styles_root = read_xml(zf, 'word/styles.xml')
    style_spacing_map = load_style_spacing_map(styles_root)
    for part_name in iter_content_parts(zf):
        try:
            root = ET.fromstring(zf.read(part_name))
        except Exception:
            continue
        rels = load_rels_map(zf, part_name)
        for paragraph_index, p in enumerate(iter_paragraphs(root), start=1):
            kinds = paragraph_high_inline_content_kinds(p)
            if not kinds:
                continue
            spacing, source = effective_spacing_attrs(p, style_spacing_map)
            if (spacing.get('lineRule') or '').lower() == 'exact':
                fixed_line_spacing_high_inline.append({
                    'part': part_name,
                    'paragraph_index': paragraph_index,
                    'style_id': paragraph_style_id(p),
                    'spacing_source': source,
                    'spacing': spacing,
                    'content_kinds': kinds,
                    'text': para_text(p).strip()[:120],
                })
        for kind, tag in (('inline', 'inline'), ('anchor', 'anchor')):
            for drawing in root.findall(f'.//wp:{tag}', NS):
                kind_counts[kind] += 1
                extent = drawing.find('wp:extent', NS)
                blip = drawing.find('.//a:blip', NS)
                rid = blip.get(qn(R_NS, 'embed')) if blip is not None else None
                target = (rels.get(rid) or {}).get('target') if rid else None
                if rid and target:
                    if target.startswith('../'):
                        zip_target = 'word/' + target.replace('../', '')
                    elif target.startswith('/'):
                        zip_target = target.lstrip('/')
                    else:
                        base_dir = part_name.rsplit('/', 1)[0]
                        zip_target = f'{base_dir}/{target}'
                    if zip_target not in zf.namelist():
                        missing_targets.append({'part': part_name, 'rid': rid, 'target': target})
                rows.append({
                    'part': part_name,
                    'kind': kind,
                    'rid': rid,
                    'target': target,
                    'width_in': inches_from_emu(extent.get('cx') if extent is not None else None),
                    'height_in': inches_from_emu(extent.get('cy') if extent is not None else None),
                })
                if kind == 'anchor' and re.search(r'word/(?:header|footer)\d+\.xml$', part_name):
                    behind_doc = drawing.get('behindDoc') == '1'
                    width_in = inches_from_emu(extent.get('cx') if extent is not None else None)
                    height_in = inches_from_emu(extent.get('cy') if extent is not None else None)
                    if behind_doc or ((width_in or 0) >= 3.0 and (height_in or 0) >= 1.0):
                        header_footer_background_images.append({
                            'part': part_name,
                            'rid': rid,
                            'target': target,
                            'behindDoc': behind_doc,
                            'width_in': width_in,
                            'height_in': height_in,
                        })
    issues = []
    if kind_counts.get('anchor'):
        issues.append({
            'type': 'floating_images_present',
            'message': 'floating/anchored images use wp:anchor and need render/Word visual confirmation',
            'count': kind_counts.get('anchor'),
        })
    if missing_targets:
        issues.append({
            'type': 'image_relationship_target_missing',
            'message': 'some image relationship targets were not found in the package',
            'count': len(missing_targets),
            'examples': missing_targets[:8],
        })
    if header_footer_background_images:
        issues.append({
            'type': 'header_footer_background_images_present',
            'message': 'header/footer contains behind-text or large anchored images that may render as watermarks',
            'count': len(header_footer_background_images),
            'examples': header_footer_background_images[:8],
        })
    if fixed_line_spacing_high_inline:
        issues.append({
            'type': 'fixed_line_spacing_high_inline_content',
            'message': 'paragraphs containing drawings, OLE/MathType objects, or OMML formulas still use exact fixed line spacing and may clip visible content',
            'count': len(fixed_line_spacing_high_inline),
            'examples': fixed_line_spacing_high_inline[:8],
        })
    return {
        'drawing_count': len(rows),
        'kind_counts': dict(kind_counts),
        'header_footer_background_images': header_footer_background_images[:20],
        'fixed_line_spacing_high_inline_content': fixed_line_spacing_high_inline[:20],
        'issues': issues,
        'examples': rows[:30],
    }


def field_type(instr):
    normalized = re.sub(r'\s+', ' ', instr or '').strip()
    return (normalized.split(' ', 1)[0] if normalized else '(empty)').upper()


def extract_field_instructions(root):
    instructions = []
    for fld in root.findall('.//w:fldSimple', NS):
        instr = attr(fld, 'instr')
        if instr:
            instructions.append(instr)
    in_field = False
    buf = []
    for node in root.iter():
        if node.tag == qn(W_NS, 'fldChar'):
            fld_type = attr(node, 'fldCharType')
            if fld_type == 'begin':
                in_field = True
                buf = []
            elif fld_type == 'end' and in_field:
                instr = ''.join(buf).strip()
                if instr:
                    instructions.append(instr)
                in_field = False
                buf = []
        elif in_field and node.tag == qn(W_NS, 'instrText'):
            buf.append(node.text or '')
    if not instructions:
        for instr_text in root.findall('.//w:instrText', NS):
            if (instr_text.text or '').strip():
                instructions.append(instr_text.text or '')
    return [re.sub(r'\s+', ' ', instr).strip() for instr in instructions if re.sub(r'\s+', ' ', instr or '').strip()]


def field_audit(zf):
    by_part = {}
    type_counts = Counter()
    examples = {}
    for part_name in iter_content_parts(zf):
        try:
            root = ET.fromstring(zf.read(part_name))
        except Exception:
            continue
        instructions = extract_field_instructions(root)
        if not instructions:
            continue
        by_part[part_name] = instructions[:20]
        for instr in instructions:
            ft = field_type(instr)
            type_counts[ft] += 1
            examples.setdefault(ft, [])
            if len(examples[ft]) < 8:
                examples[ft].append(instr)
    update_sensitive = {
        ft: count for ft, count in type_counts.items()
        if ft in FIELD_UPDATE_TYPES or ft.startswith('TOC')
    }
    issues = []
    if update_sensitive:
        issues.append({
            'type': 'fields_need_word_refresh_check',
            'message': 'page, cross-reference, TOC, caption sequence, or similar fields may need updating in Word',
            'field_types': update_sensitive,
        })
    return {
        'field_count': sum(type_counts.values()),
        'field_type_counts': dict(type_counts.most_common(30)),
        'update_sensitive_field_counts': update_sensitive,
        'examples': examples,
        'by_part': by_part,
        'issues': issues,
    }


def heading_hierarchy_audit(doc_root):
    if doc_root is None:
        return {'heading_count': 0, 'issues': [], 'examples': []}
    headings = []
    issues = []
    counts = Counter()
    last_level = None
    for idx, p in enumerate(iter_paragraphs(doc_root), start=1):
        text = para_text(p).strip()
        if not text:
            continue
        p_pr = p.find('w:pPr', NS)
        p_style = p_pr.find('w:pStyle', NS) if p_pr is not None else None
        style_id = attr(p_style, 'val', '')
        style_level = heading_level_from_style(style_id)
        text_level = numbered_heading_level(text)
        level = style_level or text_level
        if level is None:
            if p_pr is not None and p_pr.find('w:numPr', NS) is not None and len(text) <= 120:
                issues.append({
                    'type': 'numbered_non_heading_paragraph',
                    'paragraph_index': idx,
                    'style_id': style_id,
                    'text': text[:120],
                })
            continue
        counts[level] += 1
        if last_level is not None and level > last_level + 1:
            issues.append({
                'type': 'heading_level_jump',
                'paragraph_index': idx,
                'from_level': last_level,
                'to_level': level,
                'style_id': style_id,
                'text': text[:120],
            })
        last_level = level
        headings.append({
            'paragraph_index': idx,
            'level': level,
            'style_id': style_id,
            'source': 'style' if style_level else 'text_number',
            'text': text[:120],
        })
    return {
        'heading_count': len(headings),
        'heading_counts_by_level': {str(k): v for k, v in sorted(counts.items())},
        'issues': issues[:40],
        'examples': headings[:40],
    }


def package_audit(zf):
    names = zf.namelist()
    counts = {
        'headers': len([n for n in names if re.match(r'word/header\d+\.xml$', n)]),
        'footers': len([n for n in names if re.match(r'word/footer\d+\.xml$', n)]),
        'media': len([n for n in names if n.startswith('word/media/')]),
        'embeddings': len([n for n in names if n.startswith('word/embeddings/')]),
        'charts': len([n for n in names if n.startswith('word/charts/')]),
        'diagrams': len([n for n in names if n.startswith('word/diagrams/')]),
        'rels': len([n for n in names if n.endswith('.rels')]),
        'customXml': len([n for n in names if n.startswith('customXml/')]),
    }
    present_key_parts = {part: (part in names) for part in KEY_PARTS}
    rel_types = Counter()
    for name in names:
        if not name.endswith('.rels'):
            continue
        try:
            root = ET.fromstring(zf.read(name))
        except Exception:
            continue
        for rel in root.findall(f'{{{PKG_REL_NS}}}Relationship'):
            rel_type = rel.get('Type') or ''
            if rel_type:
                rel_types[rel_type.rsplit('/', 1)[-1]] += 1
    return {
        'part_count': len(names),
        'key_parts': present_key_parts,
        'object_counts': counts,
        'relationship_types': dict(rel_types.most_common(40)),
    }


def audit_docx(path):
    if not zipfile.is_zipfile(path):
        raise RuntimeError(f'not a valid docx zip package: {path}')
    with zipfile.ZipFile(path) as zf:
        doc_root = read_xml(zf, 'word/document.xml')
        report = {
            'path': os.path.abspath(path),
            'sections': section_audit(doc_root),
            'formatting': formatting_audit(doc_root),
            'tables': table_geometry_audit(doc_root),
            'images': image_anchor_audit(zf),
            'fields': field_audit(zf),
            'headings': heading_hierarchy_audit(doc_root),
            'package': package_audit(zf),
        }
        report['summary'] = {
            'section_count': len(report['sections']),
            'paragraph_count': report['formatting']['paragraph_count'],
            'direct_run_formatting_runs': report['formatting']['direct_run_formatting_runs'],
            'direct_paragraph_formatting_paragraphs': report['formatting']['direct_paragraph_formatting_paragraphs'],
            'table_count': report['tables']['table_count'],
            'table_issue_count': report['tables']['issue_count'],
            'drawing_count': report['images']['drawing_count'],
            'floating_image_count': report['images']['kind_counts'].get('anchor', 0),
            'field_count': report['fields']['field_count'],
            'update_sensitive_field_count': sum(report['fields']['update_sensitive_field_counts'].values()),
            'heading_count': report['headings']['heading_count'],
            'heading_issue_count': len(report['headings']['issues']),
            'media_count': report['package']['object_counts']['media'],
            'embedding_count': report['package']['object_counts']['embeddings'],
        }
        return report


def main():
    parser = argparse.ArgumentParser(description='Read-only DOCX QA audit for journal formatting.')
    parser.add_argument('docx')
    parser.add_argument('--out-json')
    args = parser.parse_args()
    try:
        report = audit_docx(args.docx)
    except Exception as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 1
    if args.out_json:
        with open(args.out_json, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps(report['summary'], ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
