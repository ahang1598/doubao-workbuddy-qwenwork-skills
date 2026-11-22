#!/usr/bin/env python3
"""Read PPTX layout geometry/styles without slides, Office, network or extraction.

CLI: python template_layouts.py --pptx template.pptx --output layouts.json
Python: inspect_template(path) -> JSON-compatible dict (schema_version=1).

canvas_sml and placeholder bbox use SML pixels = EMU / 12700, never a fitted
960/720 canvas. Missing geometry stays null with a warning. text_style.default
and levels retain a source for every value; layers retain direct/parent style
information. Theme font tokens and scheme colors are preserved, not replaced
with local fonts. Existing output files are never overwritten.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import posixpath
import re
import sys
import xml.etree.ElementTree as ET
import zipfile

NS = {
    'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
}
EMU_PER_PX = 12700
# OOXML layout content placeholders inherit the master body placeholder and
# bodyStyle, including specialized content types (python-pptx semantics).
BODY_PLACEHOLDER_ROLES = frozenset({
    'body', 'subTitle', 'obj', 'chart', 'tbl', 'pic', 'dgm', 'media', 'clipArt',
})


def master_role(role):
    if role == 'ctrTitle':
        return 'title'
    return 'body' if role in BODY_PLACEHOLDER_ROLES else role


def local(tag):
    return tag.rsplit('}', 1)[-1]


def px(value):
    return int(value) / EMU_PER_PX


def xml_part(archive, part):
    data = archive.read(part)
    if re.search(br'<!\s*(DOCTYPE|ENTITY)\b', data, re.I):
        raise ValueError(f'DTD/entity declarations are unsupported: {part}')
    return ET.fromstring(data)


def relationships(archive, part, warnings):
    relfile = posixpath.join(posixpath.dirname(part), '_rels', posixpath.basename(part) + '.rels')
    if relfile not in archive.namelist():
        return []
    result = []
    for rel in xml_part(archive, relfile):
        target = rel.get('Target', '')
        if rel.get('TargetMode', '').lower() == 'external':
            warnings.append(f'External relationship ignored: {part} -> {target}')
            continue
        resolved = posixpath.normpath(posixpath.join(posixpath.dirname(part), target)) if not target.startswith('/') else target.lstrip('/')
        if resolved.startswith('../') or ':' in resolved or resolved not in archive.namelist():
            warnings.append(f'Unresolved relationship: {part} -> {target}')
            continue
        result.append({'id': rel.get('Id'), 'type': rel.get('Type', '').rsplit('/', 1)[-1], 'target': resolved})
    return result


def linked(rels, kind):
    return next((r['target'] for r in rels if r['type'] == kind), None)


def color(node):
    if node is None:
        return None
    for child in node:
        if local(child.tag) in {'srgbClr', 'schemeClr', 'sysClr', 'prstClr', 'scrgbClr', 'hslClr'}:
            return {'type': local(child.tag), 'value': child.get('val'),
                    'attributes': dict(child.attrib),
                    'transforms': [{'type': local(t.tag), **t.attrib} for t in child]}
    return None


def run_style(node):
    if node is None:
        return {}
    result = {}
    for attr, key in [('sz', 'font_size_pt'), ('b', 'bold'), ('i', 'italic'), ('u', 'underline'), ('lang', 'language'), ('spc', 'character_spacing')]:
        value = node.get(attr)
        if value is not None:
            result[key] = float(value) / 100 if attr == 'sz' else value in {'1', 'true', 'on'} if attr in {'b', 'i'} else value
    for script in ('latin', 'ea', 'cs', 'sym'):
        font = node.find('a:' + script, NS)
        if font is not None:
            result['font_' + script] = font.get('typeface', '')
    fill = color(node.find('a:solidFill', NS))
    if fill is not None:
        result['color'] = fill
    return result


def paragraph_style(node):
    if node is None:
        return {}
    result = {'paragraph_' + k: v for k, v in node.attrib.items() if k != 'lvl'}
    for child in node:
        if local(child.tag) != 'defRPr':
            result['paragraph_' + local(child.tag)] = {'attributes': dict(child.attrib), 'children': [{'type': local(c.tag), **c.attrib} for c in child]}
    result.update(run_style(node.find('a:defRPr', NS)))
    return result


def list_layer(node, source):
    result = {'source': source, 'defaults': {}, 'levels': {}}
    if node is None:
        return result
    result['defaults'] = paragraph_style(node.find('a:defPPr', NS))
    for i in range(1, 10):
        paragraph = node.find(f'a:lvl{i}pPr', NS)
        if paragraph is not None:
            result['levels'][str(i - 1)] = paragraph_style(paragraph)
    return result


def shape_layers(shape, source):
    if shape is None:
        return []
    body = shape.find('p:txBody', NS)
    if body is None:
        return []
    layers = [list_layer(body.find('a:lstStyle', NS), source + '/lstStyle')]
    # Keep each paragraph/run as evidence; only the first paragraph at each
    # level supplies its sample default, so lower sample bullets cannot replace
    # the title's text style.
    samples = {'source': source + '/paragraphs', 'defaults': {}, 'levels': {}, 'paragraphs': []}
    for p in body.findall('a:p', NS):
        ppr = p.find('a:pPr', NS)
        level = ppr.get('lvl', '0') if ppr is not None else '0'
        props = paragraph_style(ppr)
        runs = [run_style(r.find('a:rPr', NS)) for r in p if local(r.tag) in {'r', 'fld'}]
        if runs:
            props.update(runs[0])
        else:
            props.update(run_style(p.find('a:endParaRPr', NS)))
        samples['levels'].setdefault(level, props)
        samples['paragraphs'].append({'level': int(level), 'style': props, 'runs': runs})
    layers.append(samples)
    return layers


def text_style(presentation, master, master_shape, layout_shape, role, master_file, layout_file):
    layers = [list_layer(presentation.find('p:defaultTextStyle', NS), 'presentation/defaultTextStyle')]
    inherited_role = master_role(role)
    style_role = 'titleStyle' if inherited_role == 'title' else 'bodyStyle' if inherited_role == 'body' else 'otherStyle'
    if master is not None:
        layers.append(list_layer(master.find('p:txStyles/p:' + style_role, NS), f'{master_file}/txStyles/{style_role}'))
    layers += shape_layers(master_shape, f'{master_file}/placeholder')
    layers += shape_layers(layout_shape, f'{layout_file}/placeholder')
    effective = {}
    for i in range(9):
        props = {}
        for layer in layers:
            for key, value in {**layer['defaults'], **layer['levels'].get(str(i), {})}.items():
                props[key] = {'value': value, 'source': layer['source']}
        effective[str(i)] = props
    body_properties = {}
    for sp, file in [(master_shape, master_file), (layout_shape, layout_file)]:
        body = sp.find('p:txBody/a:bodyPr', NS) if sp is not None else None
        if body is not None:
            body_properties.update({k: {'value': v, 'source': f'{file}/bodyPr'} for k, v in body.attrib.items()})
    return {'default': effective['0'], 'levels': effective, 'body_properties': body_properties, 'layers': layers}


def placeholders(root):
    if root is None:
        return []
    result = []
    for sp in root.findall('.//p:sp', NS):
        ph = sp.find('p:nvSpPr/p:nvPr/p:ph', NS)
        if ph is not None:
            info = sp.find('p:nvSpPr/p:cNvPr', NS)
            result.append((sp, {'role': ph.get('type', 'obj'), 'idx': int(ph.get('idx', '0')),
                                'id': info.get('id') if info is not None else None,
                                'name': info.get('name') if info is not None else None,
                                'attributes': dict(ph.attrib)}))
    return result


def match_master(slot, candidates):
    # Layout->master correspondence is role-based; idx disambiguates multiple
    # same-role slots. Content placeholders of any idx inherit master body.
    role = master_role(slot['role'])
    matching = [(sp, data) for sp, data in candidates if data['role'] == slot['role']]
    if not matching:
        matching = [(sp, data) for sp, data in candidates if data['role'] == role]
    exact = [(sp, data) for sp, data in matching if data['idx'] == slot['idx']]
    if exact:
        return exact[0], 'role_and_idx'
    if len(matching) == 1:
        return matching[0], 'role'
    return (None, None), 'unresolved'


def transform(shape):
    node = shape.find('p:spPr/a:xfrm', NS) if shape is not None else None
    if node is None:
        return None
    values = {}
    for child, fields in [('off', [('x', 'x'), ('y', 'y')]), ('ext', [('cx', 'width'), ('cy', 'height')])]:
        element = node.find('a:' + child, NS)
        if element is not None:
            values.update({key: int(element.get(attr)) for attr, key in fields if element.get(attr) is not None})
    return {'values': values, 'attributes': dict(node.attrib)}


def resolved_geometry(shape, parent, info, parent_info, layout_file, master_file):
    values, sources, attributes = {}, {}, {}
    for level, sp, slot, file in [('master', parent, parent_info, master_file), ('layout', shape, info, layout_file)]:
        transform_data = transform(sp)
        if transform_data is None:
            continue
        attributes.update(transform_data['attributes'])
        for key, value in transform_data['values'].items():
            values[key] = value
            sources[key] = {'level': level, 'source_file': file, 'placeholder_id': slot['id']}
    if set(values) != {'x', 'y', 'width', 'height'}:
        return {'bbox': None, 'bbox_emu': None, 'bbox_source': None, 'transform_attributes': attributes}
    levels = {s['level'] for s in sources.values()}
    source = dict(sources['x']) if len(levels) == 1 else {'level': 'mixed', 'source_file': layout_file, 'placeholder_id': info['id']}
    source['components'] = sources
    return {'bbox': {k: v / EMU_PER_PX for k, v in values.items()}, 'bbox_emu': values,
            'bbox_source': source, 'transform_attributes': attributes}


def references(root):
    if root is None:
        return {'font_tokens': [], 'font_names': [], 'scheme_colors': [], 'style_refs': []}
    fonts = {e.get('typeface') for e in root.iter() if e.get('typeface')}
    return {'font_tokens': sorted(f for f in fonts if f.startswith('+')),
            'font_names': sorted(f for f in fonts if not f.startswith('+')),
            'scheme_colors': sorted({e.get('val') for e in root.findall('.//a:schemeClr', NS) if e.get('val')}),
            'style_refs': [{'type': local(e.tag), **e.attrib} for e in root.iter() if local(e.tag) in {'fontRef', 'fillRef', 'lnRef', 'effectRef'}]}


def theme_info(root, file):
    result = {'source_file': file, 'name': root.get('name'), 'colors': {}, 'fonts': {}}
    scheme = root.find('a:themeElements/a:clrScheme', NS)
    if scheme is not None:
        result['colors'] = {local(c.tag): color(c) for c in scheme}
    font_scheme = root.find('a:themeElements/a:fontScheme', NS)
    for role in ('major', 'minor'):
        node = font_scheme.find('a:' + role + 'Font', NS) if font_scheme is not None else None
        if node is not None:
            result['fonts'][role] = {local(e.tag): e.get('typeface', '') for e in node if local(e.tag) != 'font'}
            result['fonts'][role]['scripts'] = {e.get('script'): e.get('typeface', '') for e in node.findall('a:font', NS)}
    return result


def part_order(name):
    return [int(s) if s.isdigit() else s for s in re.split(r'(\d+)', name)]


def inspect_template(pptx):
    warnings = []
    # Identify the actual immutable source, not its path or a fitted canvas.
    digest = hashlib.sha256()
    with open(pptx, 'rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    with zipfile.ZipFile(pptx) as archive:
        files = archive.namelist()
        presentation_file = 'ppt/presentation.xml'
        presentation = xml_part(archive, presentation_file)
        size = presentation.find('p:sldSz', NS)
        if size is None or int(size.get('cx', '0')) <= 0 or int(size.get('cy', '0')) <= 0:
            raise ValueError('PPTX is missing a positive presentation canvas (p:sldSz)')
        result = {'schema_version': 1, 'source_pptx': str(Path(pptx).resolve()), 'source_sha256': digest.hexdigest(),
                  'canvas_sml': {'width': px(size.get('cx')), 'height': px(size.get('cy')), 'unit': 'px', 'emu_per_px': EMU_PER_PX},
                  'canvas_emu': {'width': int(size.get('cx')), 'height': int(size.get('cy'))},
                  'slide_count': len(presentation.findall('p:sldIdLst/p:sldId', NS)),
                  'layouts': [], 'masters': [], 'themes': [], 'warnings': warnings}
        masters = {}
        for file in sorted((f for f in files if re.fullmatch(r'ppt/slideMasters/[^/]+\.xml', f)), key=part_order):
            root = xml_part(archive, file)
            rels = relationships(archive, file, warnings)
            masters[file] = root
            cmap = root.find('p:clrMap', NS)
            result['masters'].append({'source_file': file, 'theme_file': linked(rels, 'theme'),
                                      'color_map': dict(cmap.attrib) if cmap is not None else {},
                                      'references': references(root)})
        for file in sorted((f for f in files if re.fullmatch(r'ppt/theme/[^/]+\.xml', f)), key=part_order):
            result['themes'].append(theme_info(xml_part(archive, file), file))
        for file in sorted((f for f in files if re.fullmatch(r'ppt/slideLayouts/[^/]+\.xml', f)), key=part_order):
            root = xml_part(archive, file)
            rels = relationships(archive, file, warnings)
            master_file = linked(rels, 'slideMaster')
            master = masters.get(master_file)
            cslide = root.find('p:cSld', NS)
            cmap = root.find('p:clrMapOvr/a:overrideClrMapping', NS)
            record = {'name': cslide.get('name', '') if cslide is not None else '', 'type': root.get('type'),
                      'source_file': file, 'master_file': master_file, 'placeholders': [],
                      'color_map_override': dict(cmap.attrib) if cmap is not None else None,
                      'references': references(root)}
            if master is None:
                warnings.append(f'No resolved master for {file}; inherited geometry/styles unavailable')
            master_slots = placeholders(master)
            for shape, info in placeholders(root):
                (parent, parent_info), match_rule = match_master(info, master_slots)
                geom = resolved_geometry(shape, parent, info, parent_info, file, master_file)
                record['placeholders'].append({**info, 'master_placeholder': parent_info, 'master_match_rule': match_rule,
                    **geom, 'text_style': text_style(presentation, master, parent, shape, info['role'], master_file, file)})
                if geom['bbox'] is None:
                    warnings.append(f'Unresolved placeholder bbox: {file} id={info["id"]} role={info["role"]} idx={info["idx"]}')
            result['layouts'].append(record)
        return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pptx', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.output.exists() or args.output.is_symlink():
            raise FileExistsError(f'Output already exists: {args.output}')
        data = inspect_template(args.pptx)
        encoded = json.dumps(data, ensure_ascii=False, indent=2) + '\n'
        # Exclusive open also protects against races and source/output aliases.
        with args.output.open('x', encoding='utf-8') as stream:
            stream.write(encoded)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, ET.ParseError) as error:
        print(f'template_layouts: {error}', file=sys.stderr)
        return 1
    print(json.dumps({'ok': True, 'output': str(args.output.resolve()), 'layouts': len(data['layouts']), 'slide_count': data['slide_count'], 'warnings': len(data['warnings'])}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
