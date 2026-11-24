#!/usr/bin/env python3
"""Prepare an imported, complete source tree for a visual-only migration.

prepare_source(source_pptx, work_dir, deck_title, notes_json=None,
               source_deck=None, identity='user', authoring_work_dir=None)

Uses template_import_source for the distinct compatible PPTX copy and the
existing parse_template import primitive. Complete SML is split locally using
its lxml copy operation; target-deck purge is not part of this path.
Target-template preparation remains a separate parse_template command.
authoring_work_dir optionally names a containing authoring root for relative
media bindings; omitting it retains the source work directory as that root.

The returned recipe is an authoring_plan migration skeleton: source paths and
all content IDs are ready; MainAgent selects frame/frame_ids/region/role_styles.
"""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import os
import posixpath
import subprocess
import sys
import time
import uuid
from zipfile import ZipFile

from lxml import etree as E

P = 'http://schemas.openxmlformats.org/presentationml/2006/main'
A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
NS = {'p': P, 'a': A, 'r': R}
_HELPERS = {}


def _helper(name):
    if name not in _HELPERS:
        directory = Path(__file__).parent
        if not (directory / (name + '.py')).is_file():
            directory = Path(os.environ['LARK_SLIDES_SKILL_DIR']) / 'scripts' / 'template'
        sys.path.insert(0, str(directory))
        spec = importlib.util.spec_from_file_location('migration_source_' + name, directory / (name + '.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _HELPERS[name] = module
    return _HELPERS[name]


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _write(path, raw):
    path = Path(path)
    if path.exists():
        if path.read_bytes() != raw:
            raise ValueError('Existing preparation output differs: ' + str(path))
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as f:
        f.write(raw)


def _json(path, value):
    _write(path, (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode())


def _root(raw):
    root = E.fromstring(raw, E.XMLParser(resolve_entities=False, no_network=True))
    if root.getroottree().docinfo.doctype:
        raise ValueError('DTD is unsupported in source XML')
    return root


def _local(node):
    return E.QName(node).localname if isinstance(node.tag, str) else ''


def _target(owner, value):
    return value.lstrip('/') if value.startswith('/') else posixpath.normpath(posixpath.join(posixpath.dirname(owner), value))


def _rels(parts, owner):
    name = posixpath.dirname(owner) + '/_rels/' + posixpath.basename(owner) + '.rels'
    if name not in parts:
        return {}
    return {n.get('Id'): dict(n.attrib) for n in _root(parts[name])}


def _paragraph(p):
    values = []
    for n in p.iter():
        if n.tag == '{' + A + '}t':
            values.append(n.text or '')
        elif n.tag == '{' + A + '}br':
            values.append('\n')
        elif n.tag == '{' + A + '}tab':
            values.append('\t')
    return ''.join(values)


def snapshot_original(source_pptx, work_dir, *, notes_json=None):
    source, work = Path(source_pptx).resolve(), Path(work_dir).resolve()
    original = source.read_bytes()
    if source == work / 'original.pptx':
        raise ValueError('work_dir must hold a distinct source copy')
    with ZipFile(source) as z:
        parts = {n: z.read(n) for n in z.namelist() if not n.endswith('/')}
    root = _root(parts['ppt/presentation.xml'])
    rels = _rels(parts, 'ppt/presentation.xml')
    pages = []
    for number, sid in enumerate(root.findall('p:sldIdLst/p:sldId', NS), 1):
        rid = sid.get('{' + R + '}id')
        part = _target('ppt/presentation.xml', rels[rid]['Target'])
        slide = _root(parts[part]); slide_rels = _rels(parts, part)
        note_part = next((_target(part, r['Target']) for r in slide_rels.values()
                          if r.get('Type') == R + '/notesSlide'), None)
        note_paragraphs = []
        if note_part:
            note = _root(parts[note_part])
            for shape in note.findall('.//p:sp', NS):
                ph = shape.find('.//p:ph', NS)
                if ph is not None and ph.get('type') == 'body':
                    note_paragraphs.extend(_paragraph(p) for p in shape.findall('.//a:p', NS))
        pictures = []
        for pic in slide.findall('.//p:pic', NS):
            binding = pic.find('.//a:blip', NS)
            rid = binding.get('{' + R + '}embed') if binding is not None else None
            pictures.append({'xml': E.tostring(pic, encoding='unicode', with_tail=False),
                             'relationship': slide_rels.get(rid),
                             'media_part': _target(part, slide_rels[rid]['Target']) if rid in slide_rels else None})
        pages.append({'page': number, 'source_slide_id': sid.get('id'), 'slide_part': part,
                      'slide_xml_sha256': _sha(parts[part]), 'relationships': slide_rels,
                      'paragraphs': [_paragraph(p) for p in slide.findall('.//a:p', NS)],
                      'pictures': pictures,
                      'notes': {'page': number, 'source_part': note_part,
                                'paragraphs': note_paragraphs, 'text': '\n'.join(note_paragraphs),
                                'is_empty': not any(p.strip() for p in note_paragraphs)}})
    if notes_json:
        supplied = json.loads(Path(notes_json).read_bytes())
        if supplied.get('source_sha256') != _sha(original) or supplied.get('slide_count') != len(pages):
            raise ValueError('notes sidecar is not bound to this source PPTX')
        source_notes = supplied.get('pages', [])
        if [p.get('page') for p in source_notes] != list(range(1, len(pages) + 1)):
            raise ValueError('notes sidecar does not cover the source page order')
        for page, notes in zip(pages, source_notes):
            if not isinstance(notes.get('paragraphs'), list) or any(not isinstance(p, str) for p in notes['paragraphs']):
                raise ValueError('notes paragraphs must be exact strings')
            if notes['paragraphs'] != page['notes']['paragraphs']:
                raise ValueError('notes sidecar differs from this source notes text')
            page['notes'] = {**copy.deepcopy(notes), 'page': page['page']}
    _write(work / 'original.pptx', original)
    media = []
    picture_metadata = []
    for part, raw in parts.items():
        destination = work / 'original-parts' / part
        if not destination.resolve().is_relative_to(work / 'original-parts'):
            raise ValueError('Source contains an unsafe package member')
        _write(destination, raw)
        if part.startswith('ppt/media/'):
            media.append({'part': part, 'path': str(destination.relative_to(work)),
                          'bytes': len(raw), 'sha256': _sha(raw)})
        if part.startswith(('ppt/slides/slide', 'ppt/slideLayouts/slideLayout', 'ppt/slideMasters/slideMaster')) and part.endswith('.xml'):
            relationships = _rels(parts, part)
            for picture in _root(raw).findall('.//p:pic', NS):
                picture_metadata.append({'owner_part': part,
                    'xml': E.tostring(picture, encoding='unicode', with_tail=False),
                    'relationships': relationships})
    receipt = work / 'manifest/import-preparation.json'
    if receipt.exists():
        preparation = json.loads(receipt.read_bytes())
        if preparation['source_sha256'] != _sha(original) or preparation['output_sha256'] != _sha((work / 'import-source.pptx').read_bytes()):
            raise ValueError('Existing import preparation does not match this source/copy')
    else:
        preparation = _helper('template_import_source').prepare_import_source(source, work / 'import-source.pptx')
    if not preparation['ok']:
        _json(work / 'manifest/import-preparation.json', preparation)
        raise ValueError('Original picture fallback preparation needs handling: ' + json.dumps(preparation['unsupported_pictures']))
    _json(work / 'manifest/import-preparation.json', preparation)
    snapshot = {'schema_version': 1, 'source': str(source), 'source_sha256': _sha(original),
                'page_count': len(pages), 'pages': pages, 'media': media,
                'picture_metadata': picture_metadata,
                'import_preparation': preparation}
    if source.read_bytes() != original:
        raise ValueError('Original source changed during preparation')
    _json(work / 'manifest/original-content.json', snapshot)
    _json(work / 'manifest/source-notes.json', {'source_sha256': _sha(original), 'slide_count': len(pages),
                                             'pages': [p['notes'] for p in pages]})
    return snapshot


def split_native_source(native_xml, source_dir, notes):
    """Copy every member; materialize the source theme and restore author notes.

    Each complete one-slide presentation also retains its exact global theme.
    The compose-ready single slide makes inherited source text attributes and
    background explicit, without changing any source text, geometry or media.
    """
    raw = Path(native_xml).read_bytes()
    root = _root(raw)
    slides = [n for n in root if _local(n) == 'slide'] if _local(root) != 'slide' else [root]
    if len(slides) != len(notes):
        raise ValueError(f'Native source incomplete: {len(slides)} slides for {len(notes)} original pages')
    themes = [n for n in root if _local(n) == 'theme'] if root not in slides else []
    if len(themes) > 1:
        raise ValueError('Multiple source themes are ambiguous')
    theme = themes[0] if themes else None
    inherited_text = {}
    background = None
    if theme is not None:
        for child in theme:
            if _local(child) == 'textStyles':
                inherited_text = {_local(n): dict(n.attrib) for n in child}
            elif _local(child) == 'background':
                background = child
    rows = []
    directory = Path(source_dir).resolve()
    for number, (slide, original_note) in enumerate(zip(slides, notes), 1):
        copied = copy.deepcopy(slide)
        namespace = E.QName(copied).namespace
        tag = lambda name: '{' + namespace + '}' + name if namespace else name
        materialized = []
        data = next(n for n in copied if _local(n) == 'data')
        for content in data.iter():
            if _local(content) != 'content':
                continue
            for name, value in inherited_text.get(content.get('textType', 'body'), {}).items():
                target = 'color' if name == 'fontColor' else name
                if target not in {'fontFamily', 'fontSize', 'color'}:
                    raise ValueError('Unsupported inherited source text style attribute: ' + name)
                if content.get(target) is None:
                    content.set(target, value)
                    materialized.append((content, target, value))
        style = next((n for n in copied if _local(n) == 'style'), None)
        if background is not None and (style is None or not any(_local(n) == 'fill' for n in style)):
            if style is None:
                style = E.Element(tag('style')); copied.insert(0, style)
            fill = E.SubElement(style, tag('fill'), attrib=dict(background.attrib))
            for child in background:
                fill.append(copy.deepcopy(child))
        for child in list(copied):
            if _local(child) == 'note':
                copied.remove(child)
        note = E.Element(tag('note'))
        animation = next((n for n in copied if _local(n) == 'animation'), None)
        copied.insert(list(copied).index(animation) if animation is not None else len(copied), note)
        content = E.SubElement(note, tag('content'))
        for value in original_note['paragraphs']:
            p = E.SubElement(content, tag('p'))
            p.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
            p.text = value
        path = directory / f'slide-{number:02d}.xml'
        payload = E.tostring(copied, encoding='utf-8', pretty_print=False)
        _write(path, payload)
        if _local(root) == 'slide':
            complete = copy.deepcopy(copied)
        else:
            complete = E.Element(root.tag, attrib=dict(root.attrib), nsmap=root.nsmap)
            for common in root:
                if _local(common) != 'slide':
                    complete.append(copy.deepcopy(common))
            complete.append(copy.deepcopy(copied))
        presentation_path = directory.parent / 'source-presentations' / f'slide-{number:02d}.xml'
        _write(presentation_path, E.tostring(complete, encoding='utf-8', pretty_print=False))
        inventory = _helper('template_migration').source_content(path)
        inv_path = directory.parent / 'manifest/source-content' / f'slide-{number:02d}.json'
        _json(inv_path, inventory)
        native_data = next(n for n in slide if _local(n) == 'data')
        checked = copy.deepcopy(data)
        original_contents = [n for n in data.iter() if _local(n) == 'content']
        checked_contents = [n for n in checked.iter() if _local(n) == 'content']
        for content, name, value in materialized:
            checked_contents[original_contents.index(content)].attrib.pop(name)
        if E.tostring(checked) != E.tostring(native_data):
            raise ValueError('Native data subtree changed during preparation')
        rows.append({'page': number, 'slide_id': copied.get('id'), 'path': str(path),
                     'inventory': str(inv_path), 'member_ids': inventory['member_ids'],
                     'complete_presentation': str(presentation_path),
                     'inherited_style_materializations': [{'attribute': k, 'value': v} for _, k, v in materialized],
                     'all_member_ids': [n.get('id') for n in data],
                     'source_sha256': _sha(payload), 'notes_empty': not any(p.strip() for p in original_note['paragraphs']),
                     'media_tokens': list(dict.fromkeys(n.get('src') for n in data.iter() if n.get('src')))})
    _json(directory.parent / 'manifest/native-elements.json', _helper('template_reuse').inventory(directory))
    return rows


def migration_recipes(rows, work_dir, media_bindings=None):
    pages = []
    for row in rows:
        pages.append({'page': row['page'], 'link': 'L8', 'mode': 'component_reuse',
                      'operation': 'migration', 'source': row['path'],
                      'content_ids': list(row.get('all_member_ids', row['member_ids'])),
                      'frame': None, 'frame_ids': None, 'target_region': None,
                      'role_styles': {}, 'publish_source': None, 'explicit_numbering': True})
        if media_bindings:
            pages[-1]['bindings'] = {'ids': {}, 'media': {t: media_bindings[t]
                for t in row.get('media_tokens', [])}}
    return {'schema_version': 1, 'preparation_state': 'source_complete_choose_target_frame_and_region',
            'work_dir': str(Path(work_dir).resolve()), 'pages': pages}


def _cli(command, work, identity):
    command = list(command)
    if '--as' not in command:
        command += ['--as', identity]
    for attempt in range(3):
        p = subprocess.run(command, cwd=work, capture_output=True, text=True, timeout=300)
        value = json.loads(p.stdout[p.stdout.find('{'):]) if p.returncode == 0 else None
        if not p.returncode and value and value.get('ok') is True:
            return value
        if 'rate_limit' not in p.stderr + p.stdout or attempt == 2:
            raise ValueError('CLI failed: ' + (p.stderr or p.stdout)[:1000])
        time.sleep(2 * (attempt + 1))


def _cached_media(row, token, work, identity):
    """Verify actual cached bytes; restore only a missing read-only resource."""
    if row.get('file_token') != token or type(row.get('bytes')) is not int or not isinstance(row.get('sha256'), str):
        raise ValueError('Media receipt does not match its source token')
    path = Path(row['path'])
    path = (path if path.is_absolute() else work / path).resolve()
    if not path.is_relative_to(work):
        raise ValueError('Media receipt path must remain inside source work_dir')
    if path.exists():
        if not path.is_file() or path.stat().st_size != row['bytes'] or _sha(path.read_bytes()) != row['sha256']:
            raise ValueError('Media file differs from its receipt; existing file preserved: ' + str(path))
        return row
    version = uuid.uuid4().hex
    response = _cli(['lark-cli','slides','+media-download','--file-token',token,
                     '--output-dir','native-media/recovery-' + version,'--json'], work, identity)
    downloaded = Path(response.get('data', {}).get('path', ''))
    downloaded = (downloaded if downloaded.is_absolute() else work / downloaded).resolve()
    if not downloaded.is_relative_to(work) or not downloaded.is_file():
        raise ValueError('Recovered media has no actual file inside source work_dir')
    raw = downloaded.read_bytes()
    event = {'file_token': token, 'original_receipt': row, 'response': response,
             'downloaded_path': str(downloaded), 'downloaded_bytes': len(raw),
             'downloaded_sha256': _sha(raw)}
    if len(raw) != row['bytes'] or _sha(raw) != row['sha256']:
        event['status'] = 'download_mismatch_preserved'
        _json(work / 'manifest/native-media-recoveries' / (version + '.json'), event)
        raise ValueError('Media download differs from its receipt; new version preserved: ' + str(downloaded))
    _write(path, raw)
    event.update(status='restored', restored_path=str(path))
    _json(work / 'manifest/native-media-recoveries' / (version + '.json'), event)
    # Keep the original receipt/normal recipe stable after restoring its bytes.
    return row


def prepare_source(source_pptx, work_dir, deck_title, *, notes_json=None,
                   source_deck=None, identity='user', authoring_work_dir=None):
    work = Path(work_dir).resolve()
    authoring_root = Path(authoring_work_dir).resolve() if authoring_work_dir is not None else work
    if not work.is_relative_to(authoring_root):
        raise ValueError('source work_dir must be inside authoring_work_dir; use its containing authoring root or omit the option')
    snapshot = snapshot_original(source_pptx, work, notes_json=notes_json)
    parser = _helper('parse_template')
    saved_runner = parser._run_with_retry
    def runner(command, **kwargs):
        command = list(command)
        if '--as' not in command:
            command += ['--as', identity]
        # The import operation is issued once; its receipt/ticket is captured by
        # the existing import primitive. Reads retain its existing retry policy.
        if '+import' in command:
            kwargs['max_attempts'] = 1
        result = saved_runner(command, **kwargs)
        path = work / 'manifest/cli-events'
        path.mkdir(parents=True, exist_ok=True)
        _json(path / (uuid.uuid4().hex + '.json'), {'argv': command, 'returncode': result[0],
                                         'stdout': result[1], 'stderr': result[2], 'timed_out': result[3]})
        return result
    record_path = work / 'manifest/source-deck.json'
    if record_path.exists():
        imported = json.loads(record_path.read_bytes())
        if source_deck and source_deck != imported['xml_presentation_id']:
            raise ValueError('Work directory belongs to another imported source deck')
    elif source_deck:
        imported = {'ok': True, 'xml_presentation_id': source_deck, 'url': '', 'reused_source_deck': True}
        _json(record_path, imported)
    else:
        attempt = work / 'manifest/import-attempt.json'
        if attempt.exists():
            raise ValueError('Import attempt exists without a confirmed source deck; recover its saved ticket/receipt first')
        _json(attempt, {'source_sha256': snapshot['source_sha256'], 'import_copy': 'import-source.pptx',
                        'deck_title': deck_title, 'identity': identity})
        parser._run_with_retry = runner
        try:
            imported = parser._import_pptx_to_lark(work / 'import-source.pptx', work,
                                                 deck_title, timeout=300, max_attempts=1)
        finally:
            parser._run_with_retry = saved_runner
        if not imported['ok']:
            _json(work / 'manifest/import-unconfirmed.json', imported)
            return {'ok': False, 'phase': 'import', 'receipt': str(work / 'manifest/import-unconfirmed.json'), **imported}
        _json(record_path, imported)
    deck = imported['xml_presentation_id']
    # Preserve the complete presentation-level public styles as well as using
    # the existing per-page split when that is needed by a large deck.
    raw_dir = work / 'raw-native'
    raw_dir.mkdir(parents=True, exist_ok=True)
    full = raw_dir / 'full.xml'
    if not full.exists():
        response = _cli(['lark-cli','slides','+xml-get','--presentation',deck,
                         '--output','raw-native/full.xml','--json'], work, identity)
        _json(raw_dir / 'full-response.json', response)
    native = _root(full.read_bytes())
    native_slides = [n for n in native if _local(n) == 'slide']
    if len(native_slides) != snapshot['page_count']:
        raise ValueError('Complete native XML does not cover every original page')
    # The old split primitive is coupled to another network fetch and accepts
    # partial large-deck results. Once the full XML is present, use its existing
    # lxml copy/split operation locally and retain every real source subtree.
    for number, slide in enumerate(native_slides, 1):
        _write(raw_dir / f'slide-{number:02d}.xml', E.tostring(slide, encoding='utf-8', with_tail=False))
    # Restore original notes into a separate complete single-page tree; retain
    # the true imported notes/objects as raw evidence above.
    rows = split_native_source(full, work / 'original-slides', [p['notes'] for p in snapshot['pages']])
    media = []
    tokens = list(dict.fromkeys(t for row in rows for t in row['media_tokens']))
    for number, token in enumerate(tokens, 1):
        record = work / 'manifest/native-media' / f'{number:03d}.json'
        if record.exists():
            media.append(_cached_media(json.loads(record.read_bytes()), token, work, identity))
            continue
        result = _cli(['lark-cli','slides','+media-download','--file-token',token,
                       '--output-dir','native-media','--json'], work, identity)
        data = result.get('data', {})
        path = Path(data.get('path', ''))
        if not path.is_absolute():
            path = work / path
        row = {'file_token': token, 'response': result,
               'path': str(path), 'sha256': _sha(path.read_bytes()), 'bytes': path.stat().st_size}
        _json(record, row)
        media.append(row)
    media_bindings = {r['file_token']: '@./' + str(Path(r['path']).relative_to(authoring_root)) for r in media}
    plan = migration_recipes(rows, authoring_root, media_bindings)
    suffix = '-root-' + _sha(str(authoring_root).encode())[:12] if authoring_root != work else ''
    plan_path = work / 'manifest' / ('authoring-plan-migration' + suffix + '.json')
    _json(plan_path, plan)
    result = {'ok': True, 'source_deck': imported, 'page_count': len(rows),
              'source_sha256': snapshot['source_sha256'], 'pages': rows, 'native_media': media,
              'original_media_count': len(snapshot['media']), 'source_deck_retained': True,
              'plan': str(plan_path)}
    if authoring_root != work:
        result['authoring_work_dir'] = str(authoring_root)
    _json(work / 'manifest' / ('migration-source' + suffix + '.json'), result)
    return result
