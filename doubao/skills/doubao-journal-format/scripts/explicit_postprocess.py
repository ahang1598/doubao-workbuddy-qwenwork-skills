#!/usr/bin/env python3
"""Explicit, opt-in post-format DOCX edits.

This script is intentionally conservative. It only runs when an ops JSON says
enabled=true, and it skips paragraphs containing fields, drawings, math, OLE, or
other complex content.
"""

import argparse
import collections
import copy
import json
import os
import re
import shutil
import tempfile
import zipfile
import xml.etree.ElementTree as ET


W_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
PKG_REL_NS = 'http://schemas.openxmlformats.org/package/2006/relationships'
DOC_REL_NS = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'

ET.register_namespace('w', W_NS)
ET.register_namespace('r', DOC_REL_NS)
ET.register_namespace('', PKG_REL_NS)


def w(tag):
    return f'{{{W_NS}}}{tag}'


def local_name(tag):
    return tag.split('}', 1)[-1] if '}' in tag else tag


def load_json(path):
    if not path:
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def read_zip_xml(zip_path, name):
    with zipfile.ZipFile(zip_path, 'r') as zf:
        data = zf.read(name)
    return ET.ElementTree(ET.fromstring(data))


def write_zip_with_document(input_docx, output_docx, document_bytes):
    with zipfile.ZipFile(input_docx, 'r') as zin, zipfile.ZipFile(output_docx, 'w', zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == 'word/document.xml':
                data = document_bytes
            zout.writestr(item, data)


def tree_to_bytes(tree):
    return ET.tostring(tree.getroot(), encoding='utf-8', xml_declaration=True)


def para_text(p):
    return ''.join(t.text or '' for t in p.iter(w('t')))


def is_paragraph(elem):
    return elem.tag == w('p')


def is_table(elem):
    return elem.tag == w('tbl')


def has_sect_pr(elem):
    return elem.find('.//' + w('sectPr')) is not None


COMPLEX_TAGS = {
    'drawing',
    'pict',
    'object',
    'fldChar',
    'instrText',
    'smartTag',
    'sdt',
    'bookmarkStart',
    'bookmarkEnd',
    'commentRangeStart',
    'commentRangeEnd',
    'footnoteReference',
    'endnoteReference',
}


def paragraph_is_simple(p):
    for elem in p.iter():
        if local_name(elem.tag) in COMPLEX_TAGS:
            return False
    return True


def run_text_nodes(r):
    return [child for child in list(r) if child.tag == w('t')]


def run_is_simple_text(r):
    for child in list(r):
        lname = local_name(child.tag)
        if lname not in ('rPr', 't'):
            return False
    return len(run_text_nodes(r)) == 1


def clone_rpr(r):
    rPr = r.find(w('rPr'))
    return copy.deepcopy(rPr) if rPr is not None else None


def ensure_child(parent, tag):
    child = parent.find(tag)
    if child is None:
        child = ET.SubElement(parent, tag)
    return child


def remove_children_by_local_name(parent, names):
    if parent is None:
        return
    for child in list(parent):
        if local_name(child.tag) in names:
            parent.remove(child)


def apply_run_props(rPr, bold=None, italic=None, superscript=False):
    if rPr is None:
        rPr = ET.Element(w('rPr'))
    if bold is not None:
        remove_children_by_local_name(rPr, {'b', 'bCs'})
        if bold:
            ET.SubElement(rPr, w('b'))
            ET.SubElement(rPr, w('bCs'))
    if italic is not None:
        remove_children_by_local_name(rPr, {'i', 'iCs'})
        if italic:
            ET.SubElement(rPr, w('i'))
            ET.SubElement(rPr, w('iCs'))
    if superscript:
        remove_children_by_local_name(rPr, {'vertAlign'})
        vert = ET.SubElement(rPr, w('vertAlign'))
        vert.set(w('val'), 'superscript')
    return rPr


def make_run(text, base_rPr=None, bold=None, italic=None, superscript=False):
    r = ET.Element(w('r'))
    rPr = copy.deepcopy(base_rPr) if base_rPr is not None else None
    if bold is not None or italic is not None or superscript:
        rPr = apply_run_props(rPr, bold=bold, italic=italic, superscript=superscript)
    if rPr is not None:
        r.append(rPr)
    t = ET.SubElement(r, w('t'))
    if text[:1].isspace() or text[-1:].isspace():
        t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
    t.text = text
    return r


def replace_run_with_runs(p, index, new_runs):
    old = list(p)[index]
    p.remove(old)
    for offset, new_run in enumerate(new_runs):
        p.insert(index + offset, new_run)


def split_run_by_matches(r, pattern, marker_transform, marker_props):
    text_nodes = run_text_nodes(r)
    if len(text_nodes) != 1:
        return None
    text = text_nodes[0].text or ''
    matches = list(pattern.finditer(text))
    if not matches:
        return None
    base = clone_rpr(r)
    parts = []
    pos = 0
    for match in matches:
        if match.start() > pos:
            parts.append(make_run(text[pos:match.start()], base))
        marker = marker_transform(match)
        parts.append(make_run(
            marker,
            base,
            bold=marker_props.get('bold'),
            italic=marker_props.get('italic'),
            superscript=bool(marker_props.get('superscript')),
        ))
        pos = match.end()
    if pos < len(text):
        parts.append(make_run(text[pos:], base))
    return parts


REFERENCE_HEADING_RE = re.compile(r'^\s*(参考文献|references)\s*[:：]?\s*$', re.I)
REFERENCE_ITEM_RE = re.compile(r'^\s*(\[\d+\]|［\d+］|\d+[\.\)、．])')
REFERENCE_PREFIX_RE = re.compile(r'^(\s*)(\[(\d+)\]|［(\d+)］|\((\d+)\)|（(\d+)）|(\d+)[\.\)、．]?)(\s*)')
FIG_CAPTION_RE = re.compile(r'^\s*(图|fig\.?|figure)\s*([0-9]+[a-zA-Z]?)\s*[\.:：、-]?\s*(.*)$', re.I)
TABLE_CAPTION_RE = re.compile(r'^\s*(表|tab\.?|table)\s*([0-9]+[a-zA-Z]?)\s*[\.:：、-]?\s*(.*)$', re.I)


def is_caption_para(p, kind=None):
    text = para_text(p).strip()
    if kind == 'figure':
        return bool(FIG_CAPTION_RE.match(text))
    if kind == 'table':
        return bool(TABLE_CAPTION_RE.match(text))
    return bool(FIG_CAPTION_RE.match(text) or TABLE_CAPTION_RE.match(text))


FORMULA_OR_COMPLEX_OBJECT_TAGS = {
    'object',
    'OLEObject',
    'objectEmbed',
    'control',
    'oMath',
    'oMathPara',
    'fldChar',
    'instrText',
    'sdt',
    'bookmarkStart',
    'bookmarkEnd',
    'commentRangeStart',
    'commentRangeEnd',
    'footnoteReference',
    'endnoteReference',
}


def paragraph_has_figure_payload(p):
    for elem in p.iter():
        if local_name(elem.tag) in {'drawing', 'pict'}:
            return True
    return False


def paragraph_has_formula_or_complex_object(p):
    for elem in p.iter():
        if local_name(elem.tag) in FORMULA_OR_COMPLEX_OBJECT_TAGS:
            return True
    return False


def paragraph_text_looks_like_body_prose(p):
    text = re.sub(r'\s+', ' ', para_text(p) or '').strip()
    if not text or is_caption_para(p):
        return False
    latin_words = re.findall(r'[A-Za-z]{2,}', text)
    cjk_chars = re.findall(r'[\u4e00-\u9fff]', text)
    has_sentence_punct = bool(re.search(r'[。！？.!?;；:：]', text))
    if len(latin_words) >= 12 and has_sentence_punct:
        return True
    if len(cjk_chars) >= 30 and has_sentence_punct:
        return True
    return False


def paragraph_is_movable_figure_payload(p):
    if not paragraph_has_figure_payload(p):
        return False, 'no_figure_payload'
    if paragraph_has_formula_or_complex_object(p):
        return False, 'formula_or_complex_object'
    if paragraph_text_looks_like_body_prose(p):
        return False, 'body_prose_mixed_with_drawing'
    if has_sect_pr(p):
        return False, 'section_properties'
    return True, ''


def append_limited_warning(stats, message, limit=20):
    if len(stats.get('warnings') or []) < limit:
        stats.setdefault('warnings', []).append(message)


def find_body(root):
    body = root.find(w('body'))
    if body is None:
        raise ValueError('word/document.xml has no w:body')
    return body


def body_preservation_signature(body):
    counts = collections.Counter()
    paragraph_texts = []
    for child in list(body):
        if is_paragraph(child):
            counts['paragraphs'] += 1
            paragraph_texts.append(re.sub(r'\s+', ' ', para_text(child) or '').strip())
        elif is_table(child):
            counts['tables'] += 1
        for elem in child.iter():
            lname = local_name(elem.tag)
            if lname in {'drawing', 'pict', 'object', 'OLEObject', 'oMath', 'oMathPara'}:
                counts[lname] += 1
    return {
        'counts': dict(counts),
        'paragraph_text_multiset': collections.Counter(paragraph_texts),
    }


def compare_preservation_signatures(before, after, operations):
    issues = []
    before_counts = before.get('counts') or {}
    after_counts = after.get('counts') or {}
    for key in sorted(set(before_counts) | set(after_counts)):
        if after_counts.get(key, 0) < before_counts.get(key, 0):
            issues.append({
                'type': 'content_count_dropped',
                'metric': key,
                'before': before_counts.get(key, 0),
                'after': after_counts.get(key, 0),
            })
    text_sensitive_ops = {
        'move_tables_after_references',
        'move_figures_after_references',
    }
    if any((op.get('type') or op.get('operation')) in text_sensitive_ops for op in operations if isinstance(op, dict)):
        before_texts = before.get('paragraph_text_multiset') or collections.Counter()
        after_texts = after.get('paragraph_text_multiset') or collections.Counter()
        missing = list((before_texts - after_texts).elements())
        added = list((after_texts - before_texts).elements())
        if missing or added:
            issues.append({
                'type': 'paragraph_text_multiset_changed',
                'missing_examples': [text[:160] for text in missing if text][:8],
                'added_examples': [text[:160] for text in added if text][:8],
                'missing_count': len(missing),
                'added_count': len(added),
            })
    return issues


def move_tables_after_references(body, op):
    stats = {'operation': 'move_tables_after_references', 'target_scope': 'table_blocks_before_references', 'moved_groups': 0, 'skipped': 0, 'warnings': []}
    children = list(body)
    ref_idx = None
    for idx, child in enumerate(children):
        if is_paragraph(child) and REFERENCE_HEADING_RE.match(para_text(child)):
            ref_idx = idx
            break
    if ref_idx is None:
        stats['warnings'].append('reference heading not found; no tables moved')
        return stats

    include_caption = op.get('include_caption', True)
    groups = []
    used = set()
    for idx, child in enumerate(children):
        if idx >= ref_idx or not is_table(child):
            continue
        group = [idx]
        if include_caption and idx > 0 and (idx - 1) not in used:
            prev = children[idx - 1]
            if is_paragraph(prev) and is_caption_para(prev, kind='table') and not has_sect_pr(prev):
                group.insert(0, idx - 1)
        if any(has_sect_pr(children[i]) for i in group):
            stats['skipped'] += 1
            stats['warnings'].append(f'skipped table at body index {idx} because nearby section properties would move')
            continue
        groups.append(group)
        used.update(group)

    if not groups:
        return stats

    moved = []
    for group in reversed(groups):
        elems = []
        for idx in reversed(group):
            elem = children[idx]
            try:
                body.remove(elem)
                elems.insert(0, elem)
            except ValueError:
                stats['skipped'] += 1
        if elems:
            moved.insert(0, elems)

    insert_at = len(list(body))
    current_children = list(body)
    if current_children and current_children[-1].tag == w('sectPr'):
        insert_at -= 1
    for group in moved:
        for elem in group:
            body.insert(insert_at, elem)
            insert_at += 1
        stats['moved_groups'] += 1
    return stats


def move_figures_after_references(body, op):
    stats = {
        'operation': 'move_figures_after_references',
        'target_scope': 'figure_blocks_before_references',
        'moved_groups': 0,
        'skipped': 0,
        'skipped_uncaptioned': 0,
        'skipped_complex_or_formula': 0,
        'skipped_mixed_body': 0,
        'warnings': [],
    }
    children = list(body)
    ref_idx = None
    for idx, child in enumerate(children):
        if is_paragraph(child) and REFERENCE_HEADING_RE.match(para_text(child)):
            ref_idx = idx
            break
    if ref_idx is None:
        stats['warnings'].append('reference heading not found; no figures moved')
        return stats

    include_caption = op.get('include_caption', True)
    require_caption = op.get('require_caption', True)
    groups = []
    used = set()
    for idx, child in enumerate(children):
        if idx >= ref_idx or idx in used or not is_paragraph(child):
            continue
        movable, reason = paragraph_is_movable_figure_payload(child)
        if not movable:
            if paragraph_has_figure_payload(child):
                stats['skipped'] += 1
                if reason == 'formula_or_complex_object':
                    stats['skipped_complex_or_formula'] += 1
                elif reason == 'body_prose_mixed_with_drawing':
                    stats['skipped_mixed_body'] += 1
                append_limited_warning(
                    stats,
                    f'skipped drawing/pict paragraph at body index {idx} because it is not a standalone figure payload: {reason}'
                )
            continue
        group = [idx]
        has_caption = False
        if include_caption and idx > 0 and (idx - 1) not in used:
            prev = children[idx - 1]
            if is_paragraph(prev) and is_caption_para(prev, kind='figure') and not has_sect_pr(prev):
                group.insert(0, idx - 1)
                has_caption = True
        if include_caption and idx + 1 < ref_idx and (idx + 1) not in used:
            nxt = children[idx + 1]
            if is_paragraph(nxt) and is_caption_para(nxt, kind='figure') and not has_sect_pr(nxt):
                group.append(idx + 1)
                has_caption = True
        if require_caption and not has_caption:
            stats['skipped'] += 1
            stats['skipped_uncaptioned'] += 1
            append_limited_warning(
                stats,
                f'skipped figure-like paragraph at body index {idx} because no adjacent figure caption was found'
            )
            continue
        if any(has_sect_pr(children[i]) for i in group):
            stats['skipped'] += 1
            append_limited_warning(stats, f'skipped figure at body index {idx} because nearby section properties would move')
            continue
        groups.append(group)
        used.update(group)

    if not groups:
        return stats

    moved = []
    for group in reversed(groups):
        elems = []
        for idx in reversed(group):
            elem = children[idx]
            try:
                body.remove(elem)
                elems.insert(0, elem)
            except ValueError:
                stats['skipped'] += 1
        if elems:
            moved.insert(0, elems)

    insert_at = len(list(body))
    current_children = list(body)
    if current_children and current_children[-1].tag == w('sectPr'):
        insert_at -= 1
    for group in moved:
        for elem in group:
            body.insert(insert_at, elem)
            insert_at += 1
        stats['moved_groups'] += 1
    return stats


def in_reference_zone_flags(body):
    flags = {}
    in_refs = False
    for idx, child in enumerate(list(body)):
        if is_paragraph(child):
            text = para_text(child)
            if REFERENCE_HEADING_RE.match(text):
                in_refs = True
            flags[id(child)] = in_refs
    return flags


def normalize_body_citations(body, op):
    stats = {
        'operation': 'normalize_body_citations',
        'display_name': 'normalize_intext_citation_markers',
        'target_scope': 'body_citation_markers_outside_references',
        'changed_paragraphs': 0,
        'changed_markers': 0,
        'skipped_complex': 0,
    }
    ref_flags = in_reference_zone_flags(body)
    bracket_pattern = re.compile(r'\[(\d+(?:\s*[-,，]\s*\d+)*)\]')
    to = op.get('to', 'parentheses')
    italic = bool(op.get('italic', False))
    bold = op.get('bold')
    superscript = bool(op.get('superscript', False))

    def transform(match):
        inner = re.sub(r'\s+', '', match.group(1)).replace('，', ',')
        if to in ('parentheses', 'round'):
            return f'({inner})'
        if to in ('square_brackets', 'brackets'):
            return f'[{inner}]'
        return match.group(0)

    for p in body.iter(w('p')):
        if ref_flags.get(id(p)):
            continue
        text = para_text(p)
        if not bracket_pattern.search(text):
            continue
        if is_caption_para(p) or REFERENCE_ITEM_RE.match(text):
            continue
        if not paragraph_is_simple(p):
            stats['skipped_complex'] += 1
            continue
        changed_here = 0
        children = list(p)
        for idx in reversed(range(len(children))):
            r = children[idx]
            if r.tag != w('r') or not run_is_simple_text(r):
                continue
            new_runs = split_run_by_matches(
                r,
                bracket_pattern,
                transform,
                {'italic': italic, 'bold': bold, 'superscript': superscript},
            )
            if new_runs:
                changed_here += len(new_runs) - 1
                stats['changed_markers'] += len(bracket_pattern.findall(''.join(t.text or '' for t in run_text_nodes(r))))
                replace_run_with_runs(p, idx, new_runs)
        if changed_here:
            stats['changed_paragraphs'] += 1
    return stats


def format_reference_number(number, style):
    if style in ('round', 'parentheses'):
        return f'({number})'
    if style in ('square', 'brackets', 'square_brackets'):
        return f'[{number}]'
    if style in ('plain', 'bare'):
        return str(number)
    if style in ('plain_dot', 'dot'):
        return f'{number}.'
    if style in ('plain_chinese_dot', 'chinese_dot'):
        return f'{number}．'
    if style in ('plain_parenthesis', 'right_parenthesis'):
        return f'{number})'
    return None


def reference_prefix_number(match):
    for group in match.groups()[2:7]:
        if group:
            return int(group)
    return None


def normalize_reference_prefixes(body, op):
    stats = {
        'operation': 'normalize_reference_prefixes',
        'display_name': 'normalize_reference_list_numbers',
        'target_scope': 'reference_list_prefixes_inside_references',
        'changed': 0,
        'added': 0,
        'skipped': 0,
        'warnings': [],
    }
    style = op.get('style', 'round')
    renumber = bool(op.get('renumber', False))
    add_missing = bool(op.get('add_missing', False))
    separator = op.get('separator', ' ')
    expected = int(op.get('start', 1) or 1)
    in_refs = False

    for p in body.iter(w('p')):
        text = para_text(p)
        if REFERENCE_HEADING_RE.match(text):
            in_refs = True
            continue
        if not in_refs:
            continue
        stripped = text.strip()
        if not stripped:
            continue
        if not paragraph_is_simple(p):
            stats['skipped'] += 1
            continue
        match = REFERENCE_PREFIX_RE.match(text)
        if match:
            number = expected if renumber else reference_prefix_number(match)
            if number is None:
                stats['skipped'] += 1
                continue
            prefix = format_reference_number(number, style)
            if prefix is None:
                stats['warnings'].append(f'unsupported reference prefix style: {style}')
                return stats
            new_text = text[:match.start()] + match.group(1) + prefix + separator + text[match.end():].lstrip()
            if new_text != text:
                replace_paragraph_text_with_runs(p, [make_run(new_text)])
                stats['changed'] += 1
            expected = number + 1 if not renumber else expected + 1
            continue
        if add_missing and re.search(r'[A-Za-z\u4e00-\u9fff].{10,}', stripped):
            prefix = format_reference_number(expected, style)
            if prefix is None:
                stats['warnings'].append(f'unsupported reference prefix style: {style}')
                return stats
            replace_paragraph_text_with_runs(p, [make_run(f'{prefix}{separator}{stripped}')])
            stats['added'] += 1
            expected += 1
        else:
            stats['skipped'] += 1
    return stats


def first_sentence_boundary(text):
    if not text:
        return 0
    match = re.search(r'([。！？.!?])(\s|$)', text)
    if match:
        return match.end(1)
    return len(text)


def replace_paragraph_text_with_runs(p, runs):
    pPr = None
    if list(p) and list(p)[0].tag == w('pPr'):
        pPr = copy.deepcopy(list(p)[0])
    for child in list(p):
        p.remove(child)
    if pPr is not None:
        p.append(pPr)
    for run in runs:
        p.append(run)


def normalize_captions(body, op, kind):
    op_name = f'normalize_{kind}_captions'
    stats = {'operation': op_name, 'target_scope': f'{kind}_caption_prefixes', 'changed': 0, 'skipped_complex': 0}
    prefix = op.get('prefix') or ('Fig.' if kind == 'figure' else 'Table')
    separator = op.get('separator', ':')
    first_sentence_bold = bool(op.get('first_sentence_bold', False))
    regex = FIG_CAPTION_RE if kind == 'figure' else TABLE_CAPTION_RE

    for p in body.iter(w('p')):
        text = para_text(p).strip()
        match = regex.match(text)
        if not match:
            continue
        if not paragraph_is_simple(p):
            stats['skipped_complex'] += 1
            continue
        number = match.group(2)
        rest = match.group(3).strip()
        new_text = f'{prefix} {number}{separator}'
        if rest:
            new_text += f' {rest}'
        boundary = first_sentence_boundary(new_text) if first_sentence_bold else 0
        if first_sentence_bold and boundary > 0:
            runs = [make_run(new_text[:boundary], bold=True)]
            if boundary < len(new_text):
                runs.append(make_run(new_text[boundary:]))
        else:
            runs = [make_run(new_text)]
        replace_paragraph_text_with_runs(p, runs)
        stats['changed'] += 1
    return stats


def apply_operations(tree, ops_config):
    root = tree.getroot()
    body = find_body(root)
    report = {
        'enabled': bool(ops_config.get('enabled') or ops_config.get('_meta', {}).get('enabled')),
        'operations': [],
        'warnings': [],
        'preservation_issues': [],
    }
    if not report['enabled']:
        report['warnings'] = ['explicit postprocess disabled; set enabled=true to run operations']
        return report

    operations = ops_config.get('operations') or []
    if not isinstance(operations, list):
        report['warnings'].append('postprocess operations must be an array; no operations executed')
        return report
    before_signature = body_preservation_signature(body)
    for op in operations:
        if not isinstance(op, dict) or not op.get('enabled', True):
            continue
        if op.get('_config_warning'):
            report['warnings'].append(op.get('_config_warning'))
        if op.get('_config_error'):
            report['operations'].append({
                'operation': op.get('type') or 'invalid_postprocess_operation',
                'skipped': True,
                'warning': op.get('_config_error'),
            })
            report['warnings'].append(op.get('_config_error'))
            continue
        op_type = op.get('type')
        if op_type == 'move_tables_after_references':
            report['operations'].append(move_tables_after_references(body, op))
        elif op_type == 'move_figures_after_references':
            report['operations'].append(move_figures_after_references(body, op))
        elif op_type == 'normalize_body_citations':
            report['operations'].append(normalize_body_citations(body, op))
        elif op_type == 'normalize_reference_prefixes':
            report['operations'].append(normalize_reference_prefixes(body, op))
        elif op_type == 'normalize_figure_captions':
            report['operations'].append(normalize_captions(body, op, 'figure'))
        elif op_type == 'normalize_table_captions':
            report['operations'].append(normalize_captions(body, op, 'table'))
        else:
            warning = f'unsupported explicit postprocess operation: {op_type or "unknown"}'
            report['operations'].append({'operation': op_type or 'unknown', 'skipped': True, 'warning': warning})
            report['warnings'].append(warning)
    after_signature = body_preservation_signature(body)
    report['preservation_issues'] = compare_preservation_signatures(before_signature, after_signature, operations)
    if report['preservation_issues']:
        report['warnings'].append('explicit postprocess preservation audit found possible content loss')
    return report


def main():
    parser = argparse.ArgumentParser(description='Apply explicit opt-in post-format DOCX edits.')
    parser.add_argument('input_docx')
    parser.add_argument('output_docx')
    parser.add_argument('--ops-json', required=True, help='JSON file with enabled=true and explicit operations')
    parser.add_argument('--report-out', help='Write operation report JSON')
    args = parser.parse_args()

    ops = load_json(args.ops_json)
    tree = read_zip_xml(args.input_docx, 'word/document.xml')
    report = apply_operations(tree, ops)
    if os.path.abspath(args.input_docx) == os.path.abspath(args.output_docx):
        fd, temp_path = tempfile.mkstemp(suffix='.docx')
        os.close(fd)
        os.unlink(temp_path)
        write_zip_with_document(args.input_docx, temp_path, tree_to_bytes(tree))
        shutil.move(temp_path, args.output_docx)
    else:
        write_zip_with_document(args.input_docx, args.output_docx, tree_to_bytes(tree))
    if args.report_out:
        with open(args.report_out, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
