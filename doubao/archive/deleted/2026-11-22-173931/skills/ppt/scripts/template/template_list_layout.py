#!/usr/bin/env python3
"""Materialize native paragraph numbering in a copied single authoring slide.

    result = explicit_numbering(Path('authoring/page-20.xml'))
    Path('authoring/page-20.numbered.xml').write_text(result['xml'])

Only numbered body paragraphs receive autoStartAt. Text, list containers,
li@index, levels, styles, media and original notes remain intact. The source
file/tree is never edited and this helper does not publish anything.

Counter behavior follows native SML rendering verified in November 2026:
content supplies the initial value at every level; a shallower item resets
its descendants; an explicit ol start has its own counter scope; li@index
advances the group counter. An explicit p start is item-local and resets
that level's implicit continuation to its containing scope's initial value.
This last rule differs from ordinary HTML and from some prose schema examples.
The result preserves the observed numbers rather than silently correcting them.

The actual cloud exporter ignores li@index unless its p also has autoStartAt.
All values are planned before mutation, so newly explicit attributes cannot
change the resolution of later implicit items during this operation.
"""
import hashlib
from pathlib import Path
import re

from lxml import etree as ET


def _local(node):
    return ET.QName(node).localname if isinstance(node.tag, str) else ''


def _integer(value, name, maximum=32767):
    if not isinstance(value, str) or not re.fullmatch(r'\+?\d+', value.strip()):
        raise ValueError(name + ' must be an integer')
    number = int(value)
    if not 1 <= number <= maximum:
        raise ValueError(name + ' is outside the native supported range')
    return number


def _read(source):
    path = None
    if isinstance(source, ET._Element):
        raw = ET.tostring(source)
    elif isinstance(source, bytes):
        raw = source
    elif isinstance(source, Path) or isinstance(source, str) and not source.lstrip().startswith('<'):
        path = Path(source).resolve()
        raw = path.read_bytes()
    elif isinstance(source, str):
        raw = source.encode('utf-8')
    else:
        raise ValueError('Expected a single-slide XML path, value or tree')
    root = ET.fromstring(raw, ET.XMLParser(resolve_entities=False, no_network=True))
    if root.getroottree().docinfo.doctype:
        raise ValueError('Authoring XML must not include a document type')
    if _local(root) != 'slide' or any(_local(n) == 'slide' for n in root.iter() if n is not root):
        raise ValueError('Expected exactly one authoring slide')
    namespace = ET.QName(root).namespace
    data = [n for n in root if _local(n) == 'data' and ET.QName(n).namespace == namespace]
    if len(data) != 1:
        raise ValueError('Authoring slide must have one data element')
    return root, data[0], namespace, raw, path


def _plan_content(content):
    initial = _integer(content.get('autoStartAt', '1'), 'content autoStartAt')
    counters = {}
    rows = []

    def paragraph(p, inherited_list, inherited_style, state, start, li_index=None):
        if any(_local(n) in ('ol', 'ul', 'li') for n in p.iter() if n is not p):
            raise ValueError('Nested lists inside inline p are unsupported; use paragraph levels')
        kind = p.get('list', inherited_list)
        if kind not in ('none', 'bullet', 'number'):
            raise ValueError('Unsupported native list type')
        if kind != 'number':
            return
        level = _integer(p.get('level', '1'), 'paragraph level', 10)
        explicit = p.get('autoStartAt')
        index = _integer(li_index, 'li index') if li_index is not None else None
        for depth in list(state):
            if depth > level:
                del state[depth]
        if explicit is not None:
            number = _integer(explicit, 'paragraph autoStartAt')
            state.pop(level, None)
        else:
            number = index if index is not None else state.get(level, start)
            if not 1 <= number <= 32767:
                raise ValueError('Native list counter exceeds 32767')
            state[level] = number + 1
        rows.append((p, {'number': number, 'level': level,
                         'list_style': p.get('listStyle', inherited_style),
                         'li_index': li_index, 'before_autoStartAt': explicit}))

    def group(node, kind, inherited_style, state, start):
        if kind == 'number' and node.get('autoStartAt') is not None:
            start = _integer(node.get('autoStartAt'), 'ol autoStartAt')
            state = {}
        style = node.get('listStyle', inherited_style)
        for li in node:
            if not isinstance(li.tag, str):
                continue
            if _local(li) != 'li':
                raise ValueError('List must contain native li members')
            children = [n for n in li if isinstance(n.tag, str)]
            if len(children) != 1 or _local(children[0]) != 'p':
                raise ValueError('Each native li must contain exactly one p')
            paragraph(children[0], kind, style, state, start, li.get('index'))

    inherited_list = content.get('list', 'none')
    style = content.get('listStyle')
    for child in content:
        kind = _local(child)
        if kind == 'p':
            paragraph(child, inherited_list, style, counters, initial)
        elif kind in ('ol', 'ul'):
            group(child, 'number' if kind == 'ol' else 'bullet', style, counters, initial)
        elif any(_local(n) == 'p' and n.get('list') == 'number' or _local(n) == 'ol' for n in child.iter()):
            raise ValueError('Numbered paragraphs have an unsupported container')
    return rows


def explicit_numbering(source_xml):
    """Return a copied slide whose existing numbered body items export correctly.

    Accept a Path, XML bytes/string, or lxml element. Caller writes the returned
    xml to a distinct authoring copy. Metadata addresses each existing paragraph
    and records its resolved number; it does not authorize source-content edits.
    L8 migration still needs semantic-equivalence validation against its original
    immutable baseline before these newly explicit attributes can be accepted.
    """
    root, data, namespace, raw, path = _read(source_xml)
    content_tag = '{' + namespace + '}content' if namespace else 'content'
    plans = []
    for content_index, content in enumerate(data.iter(content_tag), 1):
        for paragraph_index, (p, row) in enumerate(_plan_content(content), 1):
            row.update(content_index=content_index, paragraph_index=paragraph_index,
                       xml_path=root.getroottree().getpath(p))
            plans.append((p, row))
    changed = 0
    for p, row in plans:
        value = str(row['number'])
        changed += p.get('autoStartAt') != value
        p.set('autoStartAt', value)
    xml = ET.tostring(root, encoding='unicode', pretty_print=False)
    if path is not None and path.read_bytes() != raw:
        raise ValueError('Source authoring XML changed during numbering preparation')
    return {'xml': xml, 'numbered_paragraphs': [row for _, row in plans],
            'changed_paragraphs': changed, 'source': str(path) if path else None,
            'source_sha256': hashlib.sha256(raw).hexdigest(),
            'xml_sha256': hashlib.sha256(xml.encode('utf-8')).hexdigest()}
