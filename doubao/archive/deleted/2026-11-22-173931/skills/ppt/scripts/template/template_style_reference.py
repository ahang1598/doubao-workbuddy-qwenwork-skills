#!/usr/bin/env python3
"""Bounded, visual-only PDF reference extraction and optional SML role checks.

API: extract_reference(pdf), build_style_card(reference, role_overrides=None,
source_page=None), validate_sml_roles(sml, card, bindings=None,
font_substitutions=None, user_overrides=None). Only extraction imports optional PyMuPDF. No source
text, metadata, raster bytes, labels, or word hashes enter the visual schema.
PDF coordinates and sizes are points; role candidates require visual review.
This helper neither authors content nor assesses semantic copying.
"""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import sys
import xml.etree.ElementTree as ET

TEXT_FIELDS = frozenset({'fontFamily', 'fontSize', 'color', 'bold', 'italic'})
ROLES = ('main_title', 'body', 'kicker', 'footer', 'display', 'section_label', 'background')
DEFAULT_MAX_PAGES = 500
DEFAULT_MAX_SPANS = 20000
DEFAULT_MAX_VECTORS = 10000


def _number(value):
    return round(float(value), 3) if value is not None else None


def _bbox(value):
    return [_number(v) for v in value]


def _color(value):
    if isinstance(value, int):
        return '#%06X' % (value & 0xFFFFFF)
    if isinstance(value, (tuple, list)) and len(value) == 3:
        return '#' + ''.join('%02X' % round(max(0, min(1, v)) * 255) for v in value)
    if isinstance(value, str):
        if re.fullmatch(r'#?[0-9a-fA-F]{6}', value.strip()):
            return '#' + value.strip().lstrip('#').upper()
        match = re.fullmatch(r'rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)(?:\s*,\s*(1(?:\.0+)?))?\s*\)', value)
        if match and all(int(v) <= 255 for v in match.groups()[:3]):
            return '#' + ''.join('%02X' % int(v) for v in match.groups()[:3])
    raise ValueError('Only opaque RGB colors are supported')


def _font_family(font):
    font = re.sub(r'^[A-Z]{6}\+', '', font)
    return re.sub(r'[-,](?:BoldItalic|BoldOblique|Bold|Italic|Oblique|Regular|Roman)$', '', font, flags=re.I)


def _coverage(boxes, width, height):
    """Clipped rectangle union, not ink coverage or a content-length proxy."""
    clipped = [(max(0, b[0]), max(0, b[1]), min(width, b[2]), min(height, b[3])) for b in boxes]
    clipped = [b for b in clipped if b[2] > b[0] and b[3] > b[1]]
    xs = sorted({v for b in clipped for v in (b[0], b[2])})
    area = 0
    for x0, x1 in zip(xs, xs[1:]):
        ys = sorted((b[1], b[3]) for b in clipped if b[0] < x1 and b[2] > x0)
        length = 0; end = 0
        for y0, y1 in ys:
            length += max(0, y1 - max(end, y0)); end = max(end, y1)
        area += (x1 - x0) * length
    return round(area / (width * height), 5)


def _page_roles(spans, height):
    roles = {role: [] for role in ROLES if role != 'background'}
    if not spans:
        return roles
    # A lower display figure may be larger than the actual page heading.
    large = [s for s in spans if s['size_pt'] >= height * .033]
    headers = [s for s in large if s['bbox'][1] < height * .25]
    chosen = min(headers, key=lambda s: (s['bbox'][1], s['bbox'][0])) if headers else max(spans, key=lambda s: s['size_pt'])
    title_spans = [s for s in spans if s['block_index'] == chosen['block_index'] and
                   abs(s['size_pt'] - chosen['size_pt']) < .5]
    title_ids = {s['span_id'] for s in title_spans}
    title_top = min(s['bbox'][1] for s in title_spans)
    body_sizes = [s['size_pt'] for s in spans if s['span_id'] not in title_ids]
    body_size = statistics.median(body_sizes) if body_sizes else chosen['size_pt']
    for s in spans:
        if s['span_id'] in title_ids:
            role = 'main_title'
        elif s['bbox'][1] >= height * .84 and s['size_pt'] < chosen['size_pt'] * .7:
            role = 'footer'
        elif s['bbox'][3] <= title_top and s['size_pt'] < chosen['size_pt'] * .65:
            role = 'kicker'
        elif s['size_pt'] >= chosen['size_pt'] * .9:
            role = 'display'
        elif s['size_pt'] < body_size * .8:
            role = 'section_label'
        else:
            role = 'body'
        s['role_candidate'] = role
        roles[role].append(s['span_id'])
    return roles


def extract_reference(pdf, *, max_pages=DEFAULT_MAX_PAGES, max_spans=DEFAULT_MAX_SPANS, max_vectors=DEFAULT_MAX_VECTORS):
    """Read immutable PDF bytes and allowlist visual fields only.

    Limits fail rather than silently truncating. PyMuPDF must already exist in
    the caller's chosen Python environment; this helper installs nothing.
    """
    if any(isinstance(v, bool) or not isinstance(v, int) or v <= 0 for v in (max_pages, max_spans, max_vectors)):
        raise ValueError('Extraction limits must be positive integers')
    path = Path(pdf)
    if path.stat().st_size > 100 * 1024 * 1024:
        raise ValueError('PDF exceeds the 100 MiB extraction limit')
    source = path.read_bytes()
    digest = hashlib.sha256(source).hexdigest()
    try:
        import fitz
    except ImportError as exc:
        raise ValueError('PDF extraction needs PyMuPDF in the selected Python runtime; validation needs only stdlib') from exc
    result = {'schema_version': 1, 'reference_type': 'pdf_visual_only',
              'source_sha256': digest, 'coordinate_unit': 'pt', 'pages': [],
              'limitations': ['geometry_based_role_candidates_require_visual_review',
                              'bbox_density_is_not_ink_coverage', 'raster_content_not_inspected',
                              'font_identity_is_pdf_declared_not_runtime_availability',
                              'semantic_copy_not_assessed']}
    span_count = 0; vector_count = 0
    with fitz.open(stream=source, filetype='pdf') as document:
        if document.needs_pass:
            raise ValueError('Encrypted PDF is not supported')
        if len(document) > max_pages:
            raise ValueError('PDF exceeds the page extraction limit')
        result['page_count'] = len(document)
        for index, page in enumerate(document):
            width, height = page.rect.width, page.rect.height
            spans = []; line_count = 0
            # rawdict is transient: no character array is read or serialized.
            text_flags = fitz.TEXTFLAGS_RAWDICT & ~fitz.TEXT_PRESERVE_IMAGES
            for block_index, block in enumerate(page.get_text('rawdict', flags=text_flags)['blocks']):
                if block['type'] != 0:
                    continue
                for line in block['lines']:
                    line_count += 1
                    for raw in line['spans']:
                        span_count += 1
                        if span_count > max_spans:
                            raise ValueError('PDF exceeds the span extraction limit')
                        font = raw['font']; flags = int(raw.get('flags', 0))
                        spans.append({'span_id': f'p{index + 1}-s{len(spans) + 1}',
                                      'block_index': block_index, 'bbox': _bbox(raw['bbox']),
                                      'font': font, 'font_family': _font_family(font),
                                      'size_pt': _number(raw['size']), 'color': _color(raw['color']),
                                      'bold': bool(flags & 16), 'italic': bool(flags & 2),
                                      'serif_flag': bool(flags & 4),
                                      'ascender': _number(raw['ascender']), 'descender': _number(raw['descender'])})
            roles = _page_roles(spans, height)
            vectors = []; background = {'color': None, 'basis': 'unresolved'}
            for drawing in page.get_drawings():
                vector_count += 1
                if vector_count > max_vectors:
                    raise ValueError('PDF exceeds the vector extraction limit')
                box = _bbox(drawing['rect']); w, h = box[2] - box[0], box[3] - box[1]
                fill = _color(drawing['fill']) if drawing.get('fill') is not None else None
                stroke = _color(drawing['color']) if drawing.get('color') is not None else None
                is_background = (fill is not None and box[0] <= width * .01 and box[1] <= height * .01 and
                                 box[2] >= width * .99 and box[3] >= height * .99 and
                                 drawing.get('fill_opacity', 1) == 1)
                kind = 'full_page_fill' if is_background else 'thin_rule' if min(w, h) <= 3 and max(w, h) >= 20 else 'path_bbox'
                vectors.append({'bbox': box, 'kind': kind, 'fill': fill, 'stroke': stroke,
                                'stroke_width_pt': _number(drawing['width']) if drawing.get('width') is not None else None,
                                'fill_opacity': _number(drawing.get('fill_opacity', 1)),
                                'stroke_opacity': _number(drawing.get('stroke_opacity', 1))})
                if is_background:
                    background = {'color': fill, 'basis': 'last_opaque_full_page_vector_fill'}
            # Bboxes only: no image extraction, source labels, raster data or digests.
            images = [{'bbox': _bbox(info['bbox'])} for info in page.get_image_info()]
            result['pages'].append({'page': index + 1, 'bbox': _bbox(page.rect),
                                    'spans': spans, 'role_candidates': roles,
                                    'role_basis': 'top_large_span_or_largest_block_then_relative_geometry',
                                    'background': background, 'vectors': vectors, 'images': images,
                                    'density': {'span_count': len(spans), 'line_count': line_count,
                                                'text_bbox_coverage': _coverage([s['bbox'] for s in spans], width, height)}})
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError('Source PDF changed during extraction')
    result['input_unchanged'] = True
    return result


def _checked_values(role, values):
    allowed = {'color'} if role == 'background' else TEXT_FIELDS
    if not isinstance(values, dict) or not values or set(values) - allowed:
        raise ValueError('Role values must contain supported visual style fields only')
    normalized = copy.deepcopy(values)
    for key, value in values.items():
        if key == 'color':
            normalized[key] = _color(value)
        elif key == 'fontSize':
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError('Font size must be a positive finite number')
        elif key == 'fontFamily':
            if not isinstance(value, str) or not value.strip():
                raise ValueError('Font family must be a nonempty string')
        elif not isinstance(value, bool):
            raise ValueError('Bold and italic must be booleans')
    return normalized


def _checked_overrides(overrides):
    overrides = copy.deepcopy(overrides)
    if not isinstance(overrides, dict) or set(overrides) - set(ROLES):
        raise ValueError('Unknown override role')
    for role, override in overrides.items():
        if not isinstance(override, dict) or set(override) != {'basis', 'values'} or override['basis'] != 'explicit_user':
            raise ValueError('Role override must record explicit_user basis separately')
        override['values'] = _checked_values(role, override['values'])
    return overrides


def build_style_card(reference, *, role_overrides=None, source_page=None):
    """Select exact role styles; keep explicit user values separate from evidence.

    Overrides: {"main_title": {"basis": "explicit_user", "values":
    {"color": "#C49A3C", "fontFamily": "Noto Serif SC", "fontSize": 30}}}.
    Selection counts only candidates for that role, never a global palette/font.
    source_page selects a visual exemplar; it does not impose page-count quotas.
    """
    if reference.get('schema_version') != 1 or reference.get('reference_type') != 'pdf_visual_only':
        raise ValueError('Unsupported visual reference schema')
    pages = reference.get('pages', [])
    if source_page is not None:
        pages = [p for p in pages if p['page'] == source_page]
        if len(pages) != 1:
            raise ValueError('Source page must resolve exactly once')
    overrides = _checked_overrides(role_overrides or {})
    card = {'schema_version': 1, 'card_type': 'visual_style_card',
            'source_sha256': reference.get('source_sha256'), 'source_page': source_page,
            'roles': {}, 'user_overrides': overrides,
            'limitations': ['role_selection_requires_visual_review', 'semantic_copy_not_assessed',
                            'font_availability_not_verified', 'background_and_density_not_validated_in_sml']}
    for role in ROLES:
        candidates = []
        for page in pages:
            if role == 'background':
                if page['background']['color']:
                    candidates.append({'page': page['page'], 'bbox': page['bbox'],
                                       'style': {'color': page['background']['color']}})
                continue
            ids = set(page.get('role_candidates', {}).get(role, []))
            for span in page['spans']:
                if span['span_id'] in ids:
                    candidates.append({'page': page['page'], 'span_id': span['span_id'], 'bbox': span['bbox'],
                                       'style': {'fontFamily': span['font_family'], 'fontSize': span['size_pt'],
                                                 'color': span['color'], 'bold': span['bold'], 'italic': span['italic']}})
        if not candidates and role not in overrides:
            continue
        frequencies = {}
        for candidate in candidates:
            token = json.dumps(candidate['style'], sort_keys=True)
            # Multiple lines in a title do not outweigh other source pages.
            frequencies.setdefault(token, set()).add(candidate['page'])
        chosen_token = max(frequencies, key=lambda t: len(frequencies[t])) if frequencies else None
        selected = json.loads(chosen_token) if chosen_token else {}
        basis = {key: 'reference_candidate' for key in selected}
        if role in overrides:
            selected.update(overrides[role]['values'])
            basis.update({key: 'explicit_user' for key in overrides[role]['values']})
        card['roles'][role] = {'selected': selected, 'field_basis': basis,
                               'reference_candidates': copy.deepcopy(candidates)}
    return card


def _tag(node):
    return node.tag.rsplit('}', 1)[-1]


def _visible_styles(node, inherited):
    style = {**inherited, **{k: v for k, v in node.attrib.items() if k in TEXT_FIELDS}}
    if _tag(node) == 'strong': style['bold'] = 'true'
    if _tag(node) == 'em': style['italic'] = 'true'
    if (node.text and node.text.strip()) or _tag(node) == 'field':
        yield style
    for child in node:
        yield from _visible_styles(child, style)
        if child.tail and child.tail.strip():
            yield style


def validate_sml_roles(sml, card, *, bindings=None, font_substitutions=None, tolerance_pt=.5,
                       user_overrides=None):
    """Pure stdlib checks of visible title/body or explicitly bound text roles.

    bindings maps roles to authored element IDs, e.g. {"main_title": ["id2"]}.
    Inferred textType=title elements are always checked, even when another ID is
    bound. A reasoned font-unavailable substitution is disclosed, not verified;
    it waives only that family mismatch. Background, density, semantic copying
    and the accuracy of the author's role bindings need independent review.
    Saved user_overrides must agree with selected values and field_basis; cards
    without saved overrides remain supported and imply no further user intent.
    Optional user_overrides supplies independently saved requirements in the
    build_style_card role_overrides format; each field must also be saved in
    the card's user_overrides, so deleting that marker cannot bypass the check.
    """
    if card.get('schema_version') != 1 or card.get('card_type') != 'visual_style_card':
        raise ValueError('Unsupported visual style card')
    if not isinstance(tolerance_pt, (int, float)) or not math.isfinite(tolerance_pt) or tolerance_pt < 0:
        raise ValueError('Font-size tolerance must be finite and nonnegative')
    selections = {role: _checked_values(role, spec['selected']) for role, spec in card.get('roles', {}).items()}
    saved_overrides = _checked_overrides(card.get('user_overrides', {}))
    if user_overrides is not None:
        for role, override in _checked_overrides(user_overrides).items():
            saved_values = saved_overrides.get(role, {}).get('values', {})
            for key, value in override['values'].items():
                if saved_values.get(key) != value:
                    raise ValueError(f'Style card must preserve external explicit_user {role}.{key} in user_overrides')
    for role, override in saved_overrides.items():
        basis = card.get('roles', {}).get(role, {}).get('field_basis', {})
        for key, value in override['values'].items():
            if selections.get(role, {}).get(key) != value:
                raise ValueError(f'Style card must preserve explicit_user {role}.{key} in selected')
            if not isinstance(basis, dict) or basis.get(key) != 'explicit_user':
                raise ValueError(f'Style card must preserve explicit_user {role}.{key} in field_basis')
    if not {'fontFamily', 'fontSize', 'color'} <= set(selections.get('main_title', {})):
        raise ValueError('Style card needs exact main_title fontFamily, fontSize and color')
    bindings = bindings or {}
    if not isinstance(bindings, dict) or set(bindings) - set(selections):
        raise ValueError('Bindings must use selected style-card roles')
    for ids in bindings.values():
        if not isinstance(ids, list) or any(not isinstance(i, str) or not i for i in ids) or len(ids) != len(set(ids)):
            raise ValueError('Each role binding must be a list of unique nonempty IDs')
    substitutions = copy.deepcopy(font_substitutions or [])
    for item in substitutions:
        if (not isinstance(item, dict) or set(item) != {'from', 'to', 'basis', 'reason'} or
                item['basis'] != 'font_unavailable' or
                any(not isinstance(item[k], str) or not item[k].strip() for k in ('from', 'to', 'reason'))):
            raise ValueError('Font substitutions need explicit families, font_unavailable basis and a reason')
        item['availability_verified'] = False
    root = ET.fromstring(sml) if isinstance(sml, (str, bytes)) else sml
    slides = [root] if _tag(root) == 'slide' else [n for n in root.iter() if _tag(n) == 'slide']
    if not slides:
        raise ValueError('SML contains no slide')
    themes = {}
    for theme in root.iter():
        if _tag(theme) == 'textStyles':
            for node in theme:
                themes[_tag(node)] = {**node.attrib, 'color': node.get('fontColor', node.get('color'))}
    errors = []; checked = []; seen_bindings = set()
    def issue(code, page, element_id=None, **details):
        errors.append({'code': code, 'page': page, 'element_id': element_id, **details})
    for page_index, page in enumerate(slides, 1):
        title_count = 0; ids_on_page = set()
        for data in [n for n in page if _tag(n) == 'data']:
            for element in data.iter():
                if _tag(element) != 'shape': continue
                element_id = element.get('id')
                if element_id and element_id in ids_on_page:
                    issue('duplicate_element_id', page_index, element_id)
                ids_on_page.add(element_id)
                contents = [n for n in element if _tag(n) == 'content']
                for content in contents:
                    styles = list(_visible_styles(content, themes.get(content.get('textType'), {})))
                    if not styles: continue
                    roles = {role for role, ids in bindings.items() if element_id in ids}
                    if content.get('textType') == 'title': roles.add('main_title')
                    elif content.get('textType') == 'body' and 'body' in selections and not roles: roles.add('body')
                    for role in sorted(roles):
                        if role == 'main_title': title_count += 1
                        seen_bindings.add((role, element_id))
                        if role == 'background':
                            issue('unsupported_role_binding', page_index, element_id, role=role); continue
                        checked.append({'page': page_index, 'element_id': element_id, 'role': role})
                        for expected_key, expected in selections[role].items():
                            for style in styles:
                                actual = style.get(expected_key, False if expected_key in ('bold', 'italic') else None)
                                try:
                                    if expected_key == 'color': matches = _color(actual) == expected
                                    elif expected_key == 'fontSize': matches = abs(float(actual) - expected) <= tolerance_pt
                                    elif expected_key == 'fontFamily':
                                        matches = isinstance(actual, str) and actual.casefold() == expected.casefold()
                                        matches = matches or any(s['from'] == expected and s['to'] == actual for s in substitutions)
                                    else: matches = str(actual).lower() == str(expected).lower()
                                except (ValueError, TypeError):
                                    matches = False
                                if not matches:
                                    suffix = {'fontFamily': 'font', 'fontSize': 'size'}.get(expected_key, expected_key)
                                    issue(f'role_{suffix}_mismatch', page_index, element_id, role=role,
                                          field=expected_key, expected=expected, actual=actual)
                                    break
        if not title_count:
            issue('missing_main_title', page_index)
    for role, ids in bindings.items():
        for element_id in ids:
            if (role, element_id) not in seen_bindings:
                issue('missing_role_binding', None, element_id, role=role)
    return {'schema_version': 1, 'ok': not errors, 'errors': errors,
            'checked_elements': checked, 'font_substitutions': substitutions,
            'unchecked_roles': [r for r in selections if r not in {item['role'] for item in checked}],
            'semantic_copy': 'not_assessed', 'density': 'not_assessed',
            'role_binding_accuracy': 'requires_visual_review'}


def _read_json(path):
    return json.loads(sys.stdin.read() if path == '-' else Path(path).read_text(encoding='utf-8'))


def _write_json(value, path):
    serialized = json.dumps(value, ensure_ascii=False, indent=2) + '\n'
    if path:
        Path(path).write_text(serialized, encoding='utf-8')
    else:
        sys.stdout.write(serialized)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    extract = commands.add_parser('extract', help='visual fields only; requires already available PyMuPDF')
    extract.add_argument('--pdf', required=True); extract.add_argument('--out')
    extract.add_argument('--style-card'); extract.add_argument('--overrides')
    extract.add_argument('--source-page', type=int)
    extract.add_argument('--max-pages', type=int, default=DEFAULT_MAX_PAGES, help='Maximum input pages; fails rather than truncates (default: 500)')
    extract.add_argument('--max-spans', type=int, default=DEFAULT_MAX_SPANS, help='Total span budget across pages (default: 20000)')
    extract.add_argument('--max-vectors', type=int, default=DEFAULT_MAX_VECTORS, help='Total vector budget across pages (default: 10000)')
    build = commands.add_parser('card', help='select exact visual roles and explicit user overrides')
    build.add_argument('--reference', required=True); build.add_argument('--overrides')
    build.add_argument('--source-page', type=int); build.add_argument('--out')
    validate = commands.add_parser('validate', help='optional per-role SML checks; pure stdlib; --sml - reads stdin')
    validate.add_argument('--sml', required=True); validate.add_argument('--card', required=True)
    validate.add_argument('--bindings'); validate.add_argument('--font-substitutions')
    validate.add_argument('--out')
    args = parser.parse_args(argv)
    try:
        inputs = [getattr(args, key, None) for key in ('pdf', 'reference', 'sml', 'card', 'overrides', 'bindings', 'font_substitutions')]
        outputs = [getattr(args, key, None) for key in ('out', 'style_card')]
        protected = {Path(p).resolve() for p in inputs if p and p != '-'}
        destinations = [Path(p).resolve() for p in outputs if p]
        linked_input = any(a.exists() and b.exists() and a.samefile(b) for a in destinations for b in protected)
        linked_output = any(a.exists() and b.exists() and a.samefile(b)
                            for i, a in enumerate(destinations) for b in destinations[i + 1:])
        if protected.intersection(destinations) or len(destinations) != len(set(destinations)) or linked_input or linked_output:
            raise ValueError('Outputs must not overwrite any input or each other')
        if sum(p == '-' for p in inputs) > 1:
            raise ValueError('Only one input can read stdin')
        if args.command == 'extract':
            if (args.overrides or args.source_page is not None) and not args.style_card:
                raise ValueError('--overrides and --source-page require --style-card')
            result = extract_reference(args.pdf, max_pages=args.max_pages,
                                       max_spans=args.max_spans, max_vectors=args.max_vectors)
            if args.style_card:
                card = build_style_card(result, role_overrides=_read_json(args.overrides) if args.overrides else None,
                                        source_page=args.source_page)
                _write_json(card, args.style_card)
        elif args.command == 'card':
            result = build_style_card(_read_json(args.reference), role_overrides=_read_json(args.overrides) if args.overrides else None,
                                      source_page=args.source_page)
        else:
            sml = sys.stdin.read() if args.sml == '-' else Path(args.sml).read_text(encoding='utf-8')
            result = validate_sml_roles(sml, _read_json(args.card),
                                        bindings=_read_json(args.bindings) if args.bindings else None,
                                        font_substitutions=_read_json(args.font_substitutions) if args.font_substitutions else None)
        _write_json(result, args.out)
        return 1 if result.get('ok') is False else 0
    except (ValueError, OSError, KeyError, ET.ParseError) as exc:
        sys.stdout.write(json.dumps({'ok': False, 'error': str(exc)}, ensure_ascii=False) + '\n')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
