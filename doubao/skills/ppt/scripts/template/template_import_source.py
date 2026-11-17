#!/usr/bin/env python3
"""Prepare a distinct PPTX import copy using its original picture fallback.

Only a p:pic's asvg:svgBlip preference is removed when both original internal
SVG and PNG/JPEG relationships are verified. A known p14 InkML/contentPart
Choice with an existing original PNG/JPEG Fallback selects that complete p:pic.
Other AlternateContent is preserved. Pictures, original raster/SVG/Ink media,
all relationships, geometry, crop and placeholders are retained.
No SVG rendering, new media, SML creation, or original-baseline replacement occurs.
An optional Unicode bullet changes only a:buChar and its decorative buFont.
Template parsing also opts into removal of unused, unpainted textboxes from
the distinct import copy; real layout placeholders and referenced shapes stay.

prepare_import_source(source_pptx, output_pptx,
                      picture_fallbacks=True, bullet_char=None) -> report
"""
import argparse
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import posixpath
import re
import sys
import unicodedata
import zipfile
from xml.dom import Node

from xml.dom.minidom import parseString
from xml.parsers import expat
import struct
import zlib

P = 'http://schemas.openxmlformats.org/presentationml/2006/main'
A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
SVG = 'http://schemas.microsoft.com/office/drawing/2016/SVG/main'
PKG = 'http://schemas.openxmlformats.org/package/2006/relationships'
MC = 'http://schemas.openxmlformats.org/markup-compatibility/2006'
P14 = 'http://schemas.microsoft.com/office/powerpoint/2010/main'
INK = 'http://www.w3.org/2003/InkML'
DISPLAY_PART = re.compile(r'ppt/(?:slides/slide|slideLayouts/slideLayout|slideMasters/slideMaster)\d+\.xml$')


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _xml(raw):
    # Expat recognizes XML encodings/BOMs before callbacks, so UTF-16 cannot
    # bypass a byte-regex DTD/entity check. No declaration is expanded/fetched.
    checker = expat.ParserCreate()
    def forbidden(*args):
        raise ValueError('Source XML must not contain DTD or entity declarations')
    checker.StartDoctypeDeclHandler = forbidden
    checker.EntityDeclHandler = forbidden
    checker.ExternalEntityRefHandler = forbidden
    checker.SetParamEntityParsing(expat.XML_PARAM_ENTITY_PARSING_NEVER)
    try:
        checker.Parse(raw, True)
    except expat.ExpatError as exc:
        raise ValueError('Invalid original XML') from exc
    return parseString(raw)


def _direct(node, namespace, name):
    return [n for n in node.childNodes if n.nodeType == Node.ELEMENT_NODE
            and n.namespaceURI == namespace and n.localName == name]


def _first(node, namespace, name):
    nodes = _direct(node, namespace, name)
    return nodes[0] if nodes else None


def _attrs(node):
    return {node.attributes.item(i).name: node.attributes.item(i).value
            for i in range(node.attributes.length)} if node is not None else None


def _svg_preferences(pic):
    fill = _first(pic, P, 'blipFill')
    blip = _first(fill, A, 'blip') if fill is not None else None
    result = []
    if blip is not None:
        for extensions in _direct(blip, A, 'extLst'):
            for extension in _direct(extensions, A, 'ext'):
                result.extend(_direct(extension, SVG, 'svgBlip'))
    return blip, result


def _relationships(parts, owner):
    rel_part = posixpath.dirname(owner) + '/_rels/' + posixpath.basename(owner) + '.rels'
    if rel_part not in parts:
        return {}
    nodes = _xml(parts[rel_part]).getElementsByTagNameNS(PKG, 'Relationship')
    rels = {}
    for node in nodes:
        rid = node.getAttribute('Id')
        if rid in rels:
            raise ValueError('Duplicate relationship ID in ' + rel_part)
        rels[rid] = _attrs(node)
    return rels


def _raster_info(raw):
    """Read existing PNG/JPEG dimensions without an imaging dependency.

    This does not decode pixels or manufacture an equivalent asset. The receipt
    binds the original bytes; source-provided fallback appearance needs review.
    """
    if raw.startswith(b'\x89PNG\r\n\x1a\n'):
        offset, width, height, image_data = 8, None, None, False
        while offset + 12 <= len(raw):
            size = struct.unpack('>I', raw[offset:offset + 4])[0]
            end = offset + 12 + size
            if end > len(raw):
                raise ValueError('truncated original PNG fallback')
            kind = raw[offset + 4:offset + 8]
            payload = raw[offset + 8:offset + 8 + size]
            expected = struct.unpack('>I', raw[offset + 8 + size:end])[0]
            if zlib.crc32(kind + payload) & 0xffffffff != expected:
                raise ValueError('original PNG fallback checksum is invalid')
            if offset == 8:
                if kind != b'IHDR' or size != 13:
                    raise ValueError('original PNG fallback has no valid IHDR')
                width, height = struct.unpack('>II', payload[:8])
            if kind == b'IDAT':
                image_data = True
            if kind == b'IEND' and width and height and image_data:
                return {'format': 'PNG', 'width': width, 'height': height}
            offset = end
        raise ValueError('incomplete original PNG fallback')
    if raw.startswith(b'\xff\xd8'):
        offset = 2
        sof = {0xc0, 0xc1, 0xc2, 0xc3, 0xc5, 0xc6, 0xc7,
               0xc9, 0xca, 0xcb, 0xcd, 0xce, 0xcf}
        while offset < len(raw):
            if raw[offset] != 0xff:
                break
            while offset < len(raw) and raw[offset] == 0xff:
                offset += 1
            if offset >= len(raw):
                break
            marker = raw[offset]; offset += 1
            if marker in {0x01, 0xd8, 0xd9, *range(0xd0, 0xd8)}:
                continue
            if offset + 2 > len(raw):
                break
            size = struct.unpack('>H', raw[offset:offset + 2])[0]
            if size < 2 or offset + size > len(raw):
                break
            if marker in sof and size >= 8:
                height, width = struct.unpack('>HH', raw[offset + 3:offset + 7])
                if width and height:
                    return {'format': 'JPEG', 'width': width, 'height': height}
            if marker == 0xda:
                break
            offset += size
        raise ValueError('original JPEG fallback has no supported frame header')
    raise ValueError('fallback must already be PNG or JPEG')


def _image_binding(parts, rels, owner, rid, *, raster):
    if not rid or rid not in rels:
        raise ValueError('missing original ' + ('fallback' if raster else 'SVG') + ' relationship')
    rel = rels[rid]
    if rel.get('Type') != R + '/image' or rel.get('TargetMode', 'Internal') != 'Internal':
        raise ValueError('original image relationship is external or has the wrong type')
    target = rel.get('Target', '')
    part = target.lstrip('/') if target.startswith('/') else posixpath.normpath(posixpath.join(posixpath.dirname(owner), target))
    if not part.startswith('ppt/media/') or part not in parts:
        raise ValueError('original image media is missing or outside the media package')
    raw = parts[part]
    binding = {'relationship_id': rid, 'part': part, 'sha256': _sha(raw), 'bytes': len(raw)}
    if raster:
        binding.update(_raster_info(raw))
        binding['validation'] = 'original_format_header_and_dimensions; visual review required'
    else:
        document = _xml(raw)
        if document.documentElement.namespaceURI != 'http://www.w3.org/2000/svg' or document.documentElement.localName != 'svg':
            raise ValueError('original SVG relationship does not reference an SVG asset')
    return binding


def _picture_identity(pic, owner, index):
    names = pic.getElementsByTagNameNS(P, 'cNvPr')
    name = names[0] if names else None
    transforms = pic.getElementsByTagNameNS(A, 'xfrm')
    crop = pic.getElementsByTagNameNS(A, 'srcRect')
    placeholders = pic.getElementsByTagNameNS(P, 'ph')
    return {'owner_part': owner, 'picture_index': index,
            'owner_shape_id': name.getAttribute('id') if name is not None else None,
            'owner_shape_name': name.getAttribute('name') if name is not None else None,
            'source_picture_xml_sha256': _sha(pic.toxml(encoding='utf-8')),
            'original_xfrm_xml': transforms[0].toxml() if transforms else None,
            'original_crop_xml': crop[0].toxml() if crop else None,
            'original_placeholder_xml': placeholders[0].toxml() if placeholders else None}


def _prefix_namespace(node, prefix):
    while node is not None:
        if node.nodeType == Node.ELEMENT_NODE and node.hasAttribute('xmlns:' + prefix):
            return node.getAttribute('xmlns:' + prefix)
        node = node.parentNode
    return None


def _inside_alternate(node):
    """An unselected alternate owns its whole subtree, including preferences."""
    parent = node.parentNode
    while parent is not None:
        if parent.nodeType == Node.ELEMENT_NODE and parent.namespaceURI == MC and parent.localName == 'AlternateContent':
            return True
        parent = parent.parentNode
    return False


def _known_ink_alternate(alternate, parts, rels, owner):
    """Recognize the narrow p14 InkML choice; never flatten generic alternates."""
    choices = _direct(alternate, MC, 'Choice')
    fallbacks = _direct(alternate, MC, 'Fallback')
    children = [n for n in alternate.childNodes if n.nodeType == Node.ELEMENT_NODE]
    if len(choices) != 1 or len(fallbacks) != 1 or len(children) != 2:
        return None
    choice = choices[0]
    prefixes = choice.getAttribute('Requires').split()
    if len(prefixes) != 1 or _prefix_namespace(choice, prefixes[0]) != P14:
        return None
    content_parts = _direct(choice, P, 'contentPart')
    choice_children = [n for n in choice.childNodes if n.nodeType == Node.ELEMENT_NODE]
    if len(content_parts) != 1 or len(choice_children) != 1:
        return None
    content = content_parts[0]
    rid = content.getAttributeNS(R, 'id')
    rel = rels.get(rid)
    if not rel or rel.get('Type') != R + '/customXml' or rel.get('TargetMode', 'Internal') != 'Internal':
        return None
    target = rel.get('Target', '')
    part = target.lstrip('/') if target.startswith('/') else posixpath.normpath(posixpath.join(posixpath.dirname(owner), target))
    if not part.startswith('ppt/ink/') or part not in parts:
        return None
    ink = _xml(parts[part])
    if ink.documentElement.namespaceURI != INK or ink.documentElement.localName != 'ink' or not ink.getElementsByTagNameNS(INK, 'trace'):
        return None
    pictures = _direct(fallbacks[0], P, 'pic')
    fallback_children = [n for n in fallbacks[0].childNodes if n.nodeType == Node.ELEMENT_NODE]
    if len(pictures) != 1 or len(fallback_children) != 1:
        raise ValueError('Known InkML alternate needs one complete original picture fallback')
    pic = pictures[0]
    blip, _ = _svg_preferences(pic)
    if blip is None:
        raise ValueError('Known InkML alternate has no original picture fallback binding')
    fallback = _image_binding(parts, rels, owner, blip.getAttributeNS(R, 'embed'), raster=True)
    return {'picture': pic, 'fallback': fallback,
            'ink': {'relationship_id': rid, 'part': part, 'sha256': _sha(parts[part]), 'bytes': len(parts[part])},
            'original_content_part_xml': content.toxml(),
            'original_alternate_xml_sha256': _sha(alternate.toxml(encoding='utf-8'))}


def _project_ink_fallbacks(document, indices):
    alternates = list(document.getElementsByTagNameNS(MC, 'AlternateContent'))
    for index in indices:
        alternate = alternates[index - 1]
        fallback = _first(alternate, MC, 'Fallback')
        picture = _first(fallback, P, 'pic')
        alternate.parentNode.replaceChild(picture.cloneNode(deep=True), alternate)


def _protected_signature(document, picture_indices, normalize_bullets, ink_indices=(), empty_textboxes=False):
    """Full XML comparison after only the explicitly permitted leaf changes."""
    normalized = _xml(document.toxml(encoding='utf-8'))
    # The comparison uses precisely the already-verified source Fallback pic;
    # text, picture geometry, media references and all other XML remain bound.
    _project_ink_fallbacks(normalized, ink_indices)
    pictures = normalized.getElementsByTagNameNS(P, 'pic')
    for index in picture_indices:
        _, leaves = _svg_preferences(pictures[index - 1])
        for leaf in leaves:
            leaf.parentNode.removeChild(leaf)
    if normalize_bullets:
        for char in list(normalized.getElementsByTagNameNS(A, 'buChar')):
            if _inside_alternate(char):
                continue
            for font in _direct(char.parentNode, A, 'buFont'):
                char.parentNode.removeChild(font)
            char.parentNode.removeChild(char)
    if empty_textboxes:
        _prune_empty_textboxes(normalized)
    return _sha(normalized.toxml(encoding='utf-8'))


def _prune_empty_textboxes(document):
    """Drop only unpainted, unreferenced textbox debris on actual slides."""
    if document.documentElement.namespaceURI != P or document.documentElement.localName != 'sld':
        return []
    referenced = set()
    for node in document.getElementsByTagName('*'):
        if node.hasAttribute('spid'):
            referenced.add(node.getAttribute('spid'))
        if node.namespaceURI == A and node.localName in ('stCxn', 'endCxn'):
            referenced.add(node.getAttribute('id'))
    removed = []
    for shape in list(document.getElementsByTagNameNS(P, 'sp')):
        if _inside_alternate(shape) or shape.getElementsByTagNameNS(P, 'ph'):
            continue
        nv = _first(shape, P, 'nvSpPr')
        identity = _first(nv, P, 'cNvPr') if nv is not None else None
        textbox = _first(nv, P, 'cNvSpPr') if nv is not None else None
        body, geometry = _first(shape, P, 'txBody'), _first(shape, P, 'spPr')
        if (identity is None or textbox is None or body is None or geometry is None
                or textbox.getAttribute('txBox') not in ('1', 'true')
                or identity.getAttribute('id') in referenced
                or identity.getAttribute('descr').strip() or identity.getAttribute('title').strip()):
            continue
        # Hyperlinks, custom metadata and locks may make an invisible box an
        # intentional interaction/animation object rather than unused debris.
        if any(node.nodeType == Node.ELEMENT_NODE
               for parent in (identity, textbox, _first(nv, P, 'nvPr')) if parent is not None
               for node in parent.childNodes):
            continue
        if any(node.namespaceURI != P or node.localName not in ('nvSpPr', 'spPr', 'txBody')
               for node in shape.childNodes if node.nodeType == Node.ELEMENT_NODE):
            continue
        if any(node.namespaceURI != A or node.localName not in ('xfrm', 'prstGeom', 'noFill')
               for node in geometry.childNodes if node.nodeType == Node.ELEMENT_NODE):
            continue
        preset = _first(geometry, A, 'prstGeom')
        if preset is not None and preset.getAttribute('prst') != 'rect':
            continue
        if any(node.namespaceURI != A or node.localName in ('fld', 'buChar', 'buAutoNum', 'buBlip')
               for node in body.getElementsByTagName('*')):
            continue
        text = ''.join(node.data for tag in body.getElementsByTagNameNS(A, 't')
                       for node in tag.childNodes if node.nodeType in (Node.TEXT_NODE, Node.CDATA_SECTION_NODE))
        if text.strip():
            continue
        removed.append({'shape_id': identity.getAttribute('id'), 'shape_name': identity.getAttribute('name')})
        shape.parentNode.removeChild(shape)
    return removed


def _new_file(path, payload):
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError('Existing output has different content; choose a new output path')
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(payload)
    return False


def prepare_import_source(source_pptx, output_pptx, *, picture_fallbacks=True, bullet_char=None, empty_textboxes=False):
    """Write or reuse a distinct compatible copy and return original-source proof.

    Missing/invalid fallback pictures remain complete and are reported; ok=False
    signals that those pictures still need another verified handling path.
    Existing different outputs, source aliases and invalid markers are rejected.
    """
    source, output = Path(source_pptx).resolve(), Path(output_pptx).resolve()
    if source == output or output.exists() and os.path.samefile(source, output):
        raise ValueError('Output must be a distinct copy of the immutable original')
    if type(picture_fallbacks) is not bool:
        raise ValueError('picture_fallbacks must be a boolean')
    if type(empty_textboxes) is not bool:
        raise ValueError('empty_textboxes must be a boolean')
    if bullet_char is not None and (not isinstance(bullet_char, str) or len(bullet_char) != 1
            or not bullet_char.isprintable() or unicodedata.category(bullet_char)[0] not in ('P', 'S')):
        raise ValueError('bullet_char must be one printable Unicode punctuation/symbol marker')
    original = source.read_bytes()
    with zipfile.ZipFile(io.BytesIO(original)) as archive:
        infos = archive.infolist()
        if len({info.filename for info in infos}) != len(infos):
            raise ValueError('Duplicate package member names are ambiguous')
        records = [(copy.copy(info), archive.read(info)) for info in infos]
        comment = archive.comment
    before = {info.filename: raw for info, raw in records}
    after = dict(before)
    pictures, ink_changes, unsupported, bullets, changed_parts, empty_changes = [], [], [], [], [], []
    for part, raw in before.items():
        if not DISPLAY_PART.fullmatch(part):
            continue
        document = _xml(raw)
        original_document = _xml(raw)
        changed_indices = []
        ink_indices = []
        if picture_fallbacks:
            rels = _relationships(before, part)
            original_pictures = list(document.getElementsByTagNameNS(P, 'pic'))
            for alternate_index, alternate in enumerate(list(document.getElementsByTagNameNS(MC, 'AlternateContent')), 1):
                if _inside_alternate(alternate):
                    continue
                try:
                    selected = _known_ink_alternate(alternate, before, rels, part)
                except ValueError as exc:
                    unsupported.append({'owner_part': part, 'alternate_index': alternate_index,
                                        'reason': str(exc), 'kind': 'known_ink_fallback'})
                    continue
                if selected is None:
                    continue
                pic = selected.pop('picture')
                identity = _picture_identity(pic, part, original_pictures.index(pic) + 1)
                record = {**identity, **selected, 'alternate_index': alternate_index,
                          'operation': 'select_original_ink_picture_fallback',
                          'editable_boundary': 'original picture is editable/resizable; Ink stroke editing remains only in retained original InkML',
                          'visual_review_required': True}
                alternate.parentNode.replaceChild(pic.cloneNode(deep=True), alternate)
                ink_indices.append(alternate_index)
                ink_changes.append(record); pictures.append(record)
            for index, pic in enumerate(document.getElementsByTagNameNS(P, 'pic'), 1):
                if _inside_alternate(pic):
                    continue
                blip, leaves = _svg_preferences(pic)
                if not leaves:
                    continue
                identity = _picture_identity(pic, part, index)
                try:
                    fallback = _image_binding(before, rels, part, blip.getAttributeNS(R, 'embed'), raster=True)
                    svg_assets = [_image_binding(before, rels, part, leaf.getAttributeNS(R, 'embed'), raster=False) for leaf in leaves]
                except (ValueError, OSError) as exc:
                    unsupported.append({**identity, 'reason': str(exc)})
                    continue
                for leaf in leaves:
                    leaf.parentNode.removeChild(leaf)
                changed_indices.append(index)
                pictures.append({**identity, 'fallback': fallback, 'original_svg': svg_assets,
                                 'operation': 'select_existing_raster_fallback',
                                 'visual_review_required': True})
        part_bullets = []
        if bullet_char is not None:
            for index, char in enumerate(document.getElementsByTagNameNS(A, 'buChar'), 1):
                if _inside_alternate(char):
                    continue
                parent = char.parentNode
                fonts = _direct(parent, A, 'buFont')
                if len(fonts) > 1:
                    raise ValueError('Ambiguous marker font in ' + part)
                font = fonts[0] if fonts else None
                record = {'owner_part': part, 'marker_index': index, 'before_char': char.getAttribute('char'),
                          'before_font': _attrs(font)}
                if font is None:
                    prefix = char.prefix + ':' if char.prefix else ''
                    font = document.createElementNS(A, prefix + 'buFont')
                    parent.insertBefore(font, char)
                for name in ('panose', 'pitchFamily'):
                    if font.hasAttribute(name):
                        font.removeAttribute(name)
                font.setAttribute('typeface', 'Arial'); font.setAttribute('charset', '0')
                char.setAttribute('char', bullet_char)
                record.update(after_char=bullet_char, after_font=_attrs(font), operation='explicit_decorative_marker')
                part_bullets.append(record)
            bullets.extend(part_bullets)
        part_empty = _prune_empty_textboxes(document) if empty_textboxes else []
        empty_changes.extend({'owner_part': part, **item} for item in part_empty)
        if changed_indices or ink_indices or part_bullets or part_empty:
            if _protected_signature(original_document, changed_indices, bool(part_bullets), ink_indices, empty_textboxes) != _protected_signature(document, changed_indices, bool(part_bullets), empty_textboxes=empty_textboxes):
                raise ValueError('Protected source content changed outside permitted format/marker leaves')
            after[part] = document.toxml(encoding='utf-8')
            changed_parts.append({'part': part, 'before_sha256': _sha(raw), 'after_sha256': _sha(after[part])})
    media_unchanged = all(after[n] == raw for n, raw in before.items() if n.startswith('ppt/media/'))
    rels_unchanged = all(after[n] == raw for n, raw in before.items() if n.endswith('.rels'))
    if not media_unchanged or not rels_unchanged:
        raise ValueError('Original media or relationship bytes changed')
    if changed_parts:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            archive.comment = comment
            for info, _ in records:
                archive.writestr(info, after[info.filename])
        prepared = buffer.getvalue()
    else:
        prepared = original
    if source.read_bytes() != original:
        raise ValueError('Original source changed during import preparation')
    reused = _new_file(output, prepared)
    return {'ok': not unsupported, 'status': 'prepared' if not unsupported else 'unsupported_pictures',
            'source_pptx': str(source), 'source_sha256': _sha(original),
            'output_pptx': str(output), 'output_sha256': _sha(prepared),
            'reused_identical_output': reused, 'picture_fallbacks': picture_fallbacks,
            'bullet_char': bullet_char, 'picture_changes': pictures,
            'ink_changes': ink_changes,
            'unsupported_pictures': unsupported, 'bullet_changes': bullets,
            'empty_textboxes_removed': empty_changes, 'empty_textboxes_removed_count': len(empty_changes),
            'changed_xml_parts': changed_parts, 'media_unchanged': media_unchanged,
            'relationships_unchanged': rels_unchanged, 'protected_content_unchanged': True,
            'member_count': len(before), 'unchanged_member_count': sum(before[n] == after[n] for n in before),
            'baseline': 'original_pptx_plus_explicit_format_selection_receipt'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-pptx', required=True)
    parser.add_argument('--output-pptx', required=True)
    parser.add_argument('--no-picture-fallbacks', action='store_true')
    parser.add_argument('--bullet-char')
    parser.add_argument('--report', help='New JSON receipt path; existing different content is never overwritten')
    args = parser.parse_args()
    try:
        report = prepare_import_source(args.source_pptx, args.output_pptx,
            picture_fallbacks=not args.no_picture_fallbacks, bullet_char=args.bullet_char)
        if args.report:
            _new_file(Path(args.report).resolve(), (json.dumps(report, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    except (ValueError, OSError, zipfile.BadZipFile) as exc:
        report = {'ok': False, 'status': 'error', 'error': str(exc)}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['ok'] else 2


if __name__ == '__main__':
    sys.exit(main())
