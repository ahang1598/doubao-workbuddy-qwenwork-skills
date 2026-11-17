#!/usr/bin/env python3
"""Copy a slide's factual content into a selected target visual frame.

inventory --source original.xml --output source-content.json
compose --source original.xml --frame frame.xml --frame-ids background \
  --target-region 40 110 880 370 --output page.xml --contract-out page.migration.json
validate --xml page.xml --contract page.migration.json

Content, rich runs, cells, chart fields, informational media and original notes
are copied, not entered again. Regions and role styles change their presentation.
The contract is bound to the original SML bytes. It cannot recover information
already lost by PPTX import: compare that baseline with the original PPTX/render,
especially image rotation/crop and labels, before composing a migration.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import math
import re
import tempfile
from pathlib import Path

from lxml import etree as ET

STYLE_KEYS = {'fontFamily', 'fontSize', 'fontColor', 'color', 'bold', 'italic',
              'underline', 'strikethrough', 'lineSpacing', 'textAlign',
              'verticalAlign', 'letterSpacing', 'autoFit', 'textType', 'wrap',
              'indent', 'marginLeft', 'marginRight', 'beforeLineSpacing',
              'afterLineSpacing', 'bulletSize', 'bulletColor'}
FONT_STYLE_KEYS = {'fontFamily','fontSize','color','bold','italic','underline',
                   'strikethrough','letterSpacing'}
PARAGRAPH_STYLE_KEYS = {'textAlign','lineSpacing','letterSpacing','indent',
    'marginLeft','marginRight','beforeLineSpacing','afterLineSpacing','bulletSize','bulletColor'}
CONTENT_STYLE_KEYS = FONT_STYLE_KEYS | {'textAlign','lineSpacing','verticalAlign',
    'autoFit','textType','wrap','beforeLineSpacing','afterLineSpacing','bulletSize','bulletColor'}
NODE_STYLE_KEYS = {'content':CONTENT_STYLE_KEYS,'p':PARAGRAPH_STYLE_KEYS,'span':FONT_STYLE_KEYS}
# Factual comparison excludes presentation geometry. Custom shape local paths
# scale with their frames; their outline and scale are reviewed visually, while
# this signature continues comparing text, data, media and reference topology.
VISUAL_KEYS = STYLE_KEYS | {'id', 'width', 'height', 'topLeftX', 'topLeftY', 'path',
    'startX', 'startY', 'endX', 'endY', 'x1', 'y1', 'x2', 'y2', 'position',
    'paddingLeft', 'paddingRight', 'paddingTop', 'paddingBottom', 'marginLeft',
    'marginRight', 'marginTop', 'marginBottom', 'indent', 'defaultTabSize',
    'presetHandlers', 'alpha', 'lineWidth', 'strokeWidth'}
VISUAL_TAGS = {'style', 'fill', 'border', 'shadow', 'animation', 'chartStyle',
    'chartBackground', 'chartBorder', 'chartColorTheme', 'chartGridLine',
    'colgroup', 'chartParsedValues'}
REF_KEYS = {'startShapeId', 'endShapeId', 'sourceId', 'targetId', 'beginShapeId',
            'shapeId', 'ref', 'refId', 'idref'}
CROP_OFFSETS = {'leftOffset','rightOffset','topOffset','bottomOffset'}


def _local(node):
    return ET.QName(node).localname if isinstance(node.tag, str) else ''


def _read(value):
    path = None
    if isinstance(value, ET._Element):
        raw = ET.tostring(value, encoding='utf-8')
    elif isinstance(value, bytes):
        raw = value
    elif isinstance(value, Path) or isinstance(value, str) and not value.lstrip().startswith('<'):
        path = Path(value).resolve(); raw = path.read_bytes()
    elif isinstance(value, str):
        raw = value.encode('utf-8')
    else:
        raise ValueError('Expected a source path or a single-slide XML value')
    root = ET.fromstring(raw, ET.XMLParser(resolve_entities=False, no_network=True))
    if _local(root) != 'slide' or any(n is not root and _local(n) == 'slide' for n in root.iter()):
        raise ValueError('Expected a single slide XML')
    if root.getroottree().docinfo.doctype:
        raise ValueError('Slide XML cannot include a document type')
    return root, raw, path


def _data(root):
    found = [n for n in root if _local(n) == 'data']
    if len(found) != 1:
        raise ValueError('Slide must have one data element')
    return found[0]


def _text(node):
    return re.sub(r'\s+', ' ', ''.join(node.itertext())).strip()


def _preformatted(node):
    """Classify from the original source, not from a replacement visual font."""
    monospace = ('monospace','consolas','courier','monaco','menlo','sf mono',
                 'cascadia','fira code','source code','dejavu sans mono')
    for part in [node]+list(node.iterancestors()):
        if (part.get('{http://www.w3.org/XML/1998/namespace}space')=='preserve'
                or _local(part) in {'pre','code'} or part.get('textType')=='code'):
            return True
        if any(name in part.get('fontFamily','').lower() for name in monospace):
            return True
    return any(_local(part) in {'tab','pre','code'}
               or part.get('{http://www.w3.org/XML/1998/namespace}space')=='preserve'
               or any(name in part.get('fontFamily','').lower() for name in monospace)
               for part in node.iter())


def _paragraph_text(node, preserve):
    def walk(part):
        if _local(part)=='tab': return '\t'
        if _local(part)=='br': return '\n'
        pieces=[part.text or '']
        for child in part:
            pieces.extend([walk(child),child.tail or ''])
        return ''.join(pieces)
    value=walk(node)
    return value if preserve else re.sub(r'\s+',' ',value).strip()


def _paragraph_policies(node):
    return [_preformatted(part) for part in node.iter() if _local(part)=='p']


def _has_text(node):
    return any(_local(n) in {'p', 'span', 't', 'chartField', 'chartTitle', 'text'}
               and _text(n) for n in node.iter())


def _factual(node):
    return _has_text(node) or _local(node) in {'table', 'chart', 'img', 'embed', 'icon', 'line'} \
        or any(n.get('src') for n in node.iter())


def _members(root, roles=None):
    roles = roles or {}
    if not isinstance(roles, dict):
        raise ValueError('source_roles must map actual member IDs to content/decoration/brand')
    elements = [n for n in _data(root) if isinstance(n.tag, str)]
    ids = [n.get('id') for n in elements]
    if any(not v for v in ids) or len(ids) != len(set(ids)):
        raise ValueError('Source data members require unique IDs')
    if set(roles) - set(ids):
        raise ValueError('source_roles contains an unknown source member')
    out = []
    for node in elements:
        role = roles.get(node.get('id'), 'content')
        if role not in {'content', 'decoration', 'brand'}:
            raise ValueError('Unknown source role: '+str(role))
        if role != 'content':
            if _has_text(node) or _local(node) in {'table', 'chart', 'embed'}:
                raise ValueError('A factual text/table/chart member cannot be excluded as decoration')
            continue
        if _factual(node):
            out.append(node)
    return out


def _note(root, paragraph_policy=None):
    notes = [n for n in root if _local(n) == 'note']
    if len(notes) > 1:
        raise ValueError('Slide has more than one note')
    node = notes[0] if notes else None
    paragraphs=[]
    if node is not None:
        for index,part in enumerate(n for n in node.iter() if _local(n)=='p'):
            preserve=(paragraph_policy[index] if paragraph_policy is not None and index<len(paragraph_policy)
                      else _preformatted(part))
            value=_paragraph_text(part,preserve)
            if value or preserve: paragraphs.append(value)
        # A service may wrap note text differently. Capture any actual text
        # outside p too; an empty source note must never become a new script.
        for part in node.iter():
            if _local(part)=='p' or any(_local(a)=='p' for a in part.iterancestors()): continue
            if part.text and part.text.strip(): paragraphs.append(part.text.strip())
            for child in part:
                if child.tail and child.tail.strip(): paragraphs.append(child.tail.strip())
    return {'value': '\n'.join(paragraphs), 'paragraphs':paragraphs,
            'xml': ET.tostring(node, encoding='unicode', with_tail=False) if node is not None else None}


def source_content(source_xml, source_roles=None):
    """Inventory actual factual members, without substituting a text summary."""
    root, raw, path = _read(source_xml)
    members = _members(root, source_roles)
    return {'schema_version': 1, 'source': str(path) if path else None,
            'source_sha256': hashlib.sha256(raw).hexdigest(),
            'member_ids': [n.get('id') for n in members],
            'members': [{'id': n.get('id'), 'kind': _local(n),
                         'xml': ET.tostring(n, encoding='unicode', with_tail=False)} for n in members],
            'note': _note(root), 'baseline': 'original_single_slide_sml',
            'original_pptx_check_required': True}


def _reuse():
    spec = importlib.util.spec_from_file_location('migration_reuse', Path(__file__).with_name('template_reuse.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def _boxes(nodes, rotated=True):
    boxes = []
    for n in nodes:
        endpoint_keys = ('startX','startY','endX','endY')
        if _local(n)=='line' and all(n.get(k) is not None for k in endpoint_keys):
            x1,y1,x2,y2 = (float(n.get(k)) for k in endpoint_keys)
            boxes.append((min(x1,x2),min(y1,y2),max(x1,x2),max(y1,y2)))
        elif all(n.get(k) is not None for k in ('width', 'height')):
            x, y = float(n.get('topLeftX', 0)), float(n.get('topLeftY', 0))
            w, h = float(n.get('width')), float(n.get('height'))
            angle = float(n.get('rotate', n.get('rotation', 0))) if rotated else 0
            if not all(math.isfinite(v) for v in (x, y, w, h, angle)) or w < 0 or h < 0:
                raise ValueError('Invalid source geometry')
            radians = math.radians(angle)
            vw = abs(w*math.cos(radians))+abs(h*math.sin(radians))
            vh = abs(w*math.sin(radians))+abs(h*math.cos(radians))
            boxes.append((x+w/2-vw/2, y+h/2-vh/2, x+w/2+vw/2, y+h/2+vh/2))
        else:
            keys = ('startX', 'startY', 'endX', 'endY') if n.get('startX') is not None else ('x1', 'y1', 'x2', 'y2')
            if all(n.get(k) is not None for k in keys):
                x1, y1, x2, y2 = (float(n.get(k)) for k in keys)
                boxes.append((min(x1,x2), min(y1,y2), max(x1,x2), max(y1,y2)))
    if not boxes:
        raise ValueError('Content group has no measurable geometry')
    return min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes)


def _binding(value):
    value = value or {}
    if not isinstance(value, dict): raise ValueError('bindings must be an object')
    result = {}
    for key in ('ids', 'media'):
        part = value.get(key, {})
        if not isinstance(part, dict) or any(not isinstance(k, str) or not isinstance(v, str) or not v for k,v in part.items()):
            raise ValueError('bindings '+key+' must map nonempty strings')
        if len(set(part.values())) != len(part):
            raise ValueError('bindings '+key+' has ambiguous destinations')
        result[key] = dict(part)
    return result


def _rebind(node, bindings):
    for n in node.iter():
        for key, value in list(n.attrib.items()):
            name = ET.QName(key).localname
            if name == 'id' or name in REF_KEYS:
                n.set(key, bindings['ids'].get(value, value))
            elif name == 'src':
                n.set(key, bindings['media'].get(value, value))


def _apply_role_style(node, style):
    """Replace a role's primary style while keeping its local emphasis."""
    normalized={('color' if k=='fontColor' else k):v for k,v in style.items()}
    parts=list(node.iter())
    def effective(part,key):
        for ancestor in [part]+list(part.iterancestors()):
            if key=='bold' and _local(ancestor)=='strong': return 'true'
            if key=='italic' and _local(ancestor)=='em': return 'true'
            if ancestor.get(key) is not None: return ancestor.get(key)
            if ancestor is node: break
        return 'false' if key in {'bold','italic','underline','strikethrough'} else None
    text_tags={'content','p','span','strong','em','u','del','a','field','formula'}
    pieces=[]
    for part in parts:
        if _local(part) in text_tags and part.text and part.text.strip(): pieces.append((part,part.text))
        parent=part.getparent()
        if parent is not None and _local(parent) in text_tags and part.tail and part.tail.strip(): pieces.append((parent,part.tail))
    primary={}
    for key in ('color','bold','italic','underline','strikethrough','fontSize'):
        counts={}
        for part,text in pieces:
            value=effective(part,key)
            if value is not None or key=='color': counts[value]=counts.get(value,0)+len(text.strip())
        candidate=max(counts,key=counts.get) if counts else None
        content=next((p for p in parts if _local(p)=='content'),None)
        declared=content.get(key) if content is not None else None
        if _local(node)=='shape' and declared in counts:
            candidate=declared
        primary[key]=candidate
    originals={(id(p),key):effective(p,key) for p in parts for key in FONT_STYLE_KEYS}
    def special_font(value):
        name=(value or '').lower()
        return any(token in name for token in ('symbol','wingdings','webdings','cambria math','fontawesome','material icons','material symbols','mdl2','fluent icons','icomoon','iconfont'))
    def private_glyph(part,family):
        return any(effective(owner,'fontFamily')==family
                   and (owner is part or part in owner.iterancestors())
                   and any(0xE000<=ord(c)<=0xF8FF or 0xF0000<=ord(c)<=0xFFFFD or 0x100000<=ord(c)<=0x10FFFD for c in text)
                   for owner,text in pieces)
    def monospace(value):
        name=(value or '').lower()
        return any(token in name for token in ('consolas','courier','monaco','menlo','mono','cascadia','fira code','source code'))
    for part in parts:
        allowed=NODE_STYLE_KEYS.get(_local(part),set())
        for key,value in normalized.items():
            if key not in allowed: continue
            old=originals.get((id(part),key))
            if key=='fontFamily' and old is not None and (special_font(old) or private_glyph(part,old) or monospace(old) and not monospace(str(value))):
                value=old
            elif _local(part)=='span' and key in {'color','bold','italic','underline','strikethrough'} and old is not None and old!=primary[key]:
                value=old
            elif _local(part)=='span' and key=='fontSize' and old is not None and primary[key] is not None:
                try: value=format(float(old)*float(value)/float(primary[key]),'.15g')
                except (ValueError,TypeError,ZeroDivisionError): pass
            if isinstance(value,bool): value='true' if value else 'false'
            elif key in {'bold','italic','underline','strikethrough','wrap'} and isinstance(value,str): value=value.lower()
            else: value=str(value)
            part.set(key,value)


def _explicit_lists(root):
    path=Path(__file__).with_name('template_list_layout.py')
    spec=importlib.util.spec_from_file_location('migration_list_layout',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return ET.fromstring(module.explicit_numbering(root)['xml'].encode())


def compose_migration(source, frame, content_ids=None, frame_ids=None,
                      target_region=None, *, placements=None, role_styles=None,
                      bindings=None, source_roles=None, explicit_numbering=False):
    """Build a complete editable draft by copying source objects into a frame.

    placements optionally partitions content IDs into independently fitted groups:
    [{"ids": [...], "target_region": [x,y,width,height]}]. role_styles maps member
    IDs to font/color properties; neither option changes the source text/data.
    """
    src, raw, source_path = _read(source); fr, frame_raw, frame_path = _read(frame)
    if ET.QName(src).namespace != ET.QName(fr).namespace:
        raise ValueError('Source and frame slide namespaces differ')
    factual = _members(src, source_roles)
    required = [n.get('id') for n in factual]
    ids = list(content_ids) if content_ids is not None else required
    if len(ids) != len(set(ids)) or set(required) - set(ids):
        raise ValueError('content_ids must include every factual source member')
    frame_data = _data(fr)
    frame_lookup = {n.get('id'): n for n in frame_data if isinstance(n.tag, str)}
    selected_frame = list(frame_ids) if frame_ids is not None else [n.get('id') for n in frame_data if not _factual(n)]
    if len(selected_frame) != len(set(selected_frame)) or any(i not in frame_lookup for i in selected_frame):
        raise ValueError('frame_ids must select actual unique frame members')
    if any(_has_text(frame_lookup[i]) or _local(frame_lookup[i]) in {'table','chart','embed'} for i in selected_frame):
        raise ValueError('Selected frame contains example text or factual content; select the empty visual frame')
    binding = _binding(bindings)
    styles = role_styles or {}
    if not isinstance(styles, dict) or set(styles) - set(ids):
        raise ValueError('role_styles must address selected content IDs')
    for style in styles.values():
        if not isinstance(style, dict) or set(style) - STYLE_KEYS:
            raise ValueError('role_styles may change only visual text properties')
    groups = placements or [{'ids': ids, 'target_region': target_region}]
    assigned = [i for g in groups for i in g.get('ids', [])]
    if len(assigned) != len(set(assigned)) or set(assigned) != set(ids):
        raise ValueError('placements must partition all content_ids exactly once')
    transformed = {}
    reuse = _reuse()
    with tempfile.TemporaryDirectory(prefix='sml-migration-') as folder:
        source_copy = Path(folder)/'source.xml'; source_copy.write_bytes(raw)
        for group in groups:
            selected = group['ids']; region = group.get('target_region')
            if not isinstance(region, (list, tuple)) or len(region) != 4:
                raise ValueError('target_region must be [x,y,width,height]')
            x, y, w, h = map(float, region)
            if not all(math.isfinite(v) for v in (x,y,w,h)) or w <= 0 or h <= 0:
                raise ValueError('target_region must be finite and have positive size')
            fragment = ET.fromstring(reuse.extract(source_copy, selected).encode())
            nodes = list(_data(fragment)); l,t,r,b = _boxes(nodes)
            scale = min(w/(r-l) if r>l else 1, h/(b-t) if b>t else 1)
            # The existing affine helper anchors unrotated boxes. Correct its
            # origin so rotated informational media also fits the visible region.
            raw_l,raw_t,_,_ = _boxes(nodes,rotated=False)
            moved = reuse.transform_component(source_copy, selected,
                x=x+(raw_l-l)*scale, y=y+(raw_t-t)*scale, scale=scale)
            for node in _data(ET.fromstring(moved['xml'].encode())):
                transformed[node.get('id')] = copy.deepcopy(node)
    out = ET.Element(fr.tag, attrib={k:v for k,v in fr.attrib.items() if k!='id'}, nsmap=fr.nsmap)
    for n in fr:
        if _local(n) in {'style','animation'}: out.append(copy.deepcopy(n))
    data = ET.SubElement(out, frame_data.tag, attrib=dict(frame_data.attrib))
    source_ids = {binding['ids'].get(n.get('id'),n.get('id')) for n in src.iter() if n.get('id')}
    actual_frame_ids = []
    for i in selected_frame:
        node = copy.deepcopy(frame_lookup[i]); frame_map = {}
        for child in node.iter():
            old = child.get('id')
            if old and old in source_ids: frame_map[old] = 'frame-'+old
        _rebind(node, {'ids':frame_map, 'media':{}})
        actual_frame_ids.append(node.get('id')); data.append(node)
    for node in _data(src):
        old = node.get('id')
        if old not in transformed: continue
        cloned = transformed[old]
        # Affine helpers serialize fragments for inspection. Restore every
        # original text/tail field so that XML indentation never alters code.
        for original,part in zip(node.iter(),cloned.iter()):
            part.text=original.text; part.tail=original.tail
        if old in styles:
            _apply_role_style(cloned,styles[old])
        _rebind(cloned, binding); data.append(cloned)
    note = next((n for n in src if _local(n)=='note'), None)
    if note is not None:
        copied = copy.deepcopy(note); _rebind(copied,binding); out.append(copied)
    if type(explicit_numbering) is not bool:
        raise ValueError('explicit_numbering must be a boolean')
    if explicit_numbering: out=_explicit_lists(out)
    xml = ET.tostring(out, encoding='unicode', pretty_print=False)
    contract = {'schema_version':1, 'contract_type':'source_content_migration',
        'source':{'path':str(source_path) if source_path else None,
                  'sha256':hashlib.sha256(raw).hexdigest(), 'xml':raw.decode('utf-8')},
        'source_roles':source_roles or {}, 'content_ids':ids,
        'frame':{'path':str(frame_path) if frame_path else None,
                 'sha256':hashlib.sha256(frame_raw).hexdigest()},
        'frame_ids':actual_frame_ids, 'bindings':binding,
        'explicit_numbering':explicit_numbering,
        'baseline':'original_single_slide_sml', 'original_pptx_check_required':True}
    return {'xml':xml, 'contract':contract, 'bindings':binding,
            'source_sha256':contract['source']['sha256'], 'member_ids':ids}


def _empty_crop(node):
    attrs={ET.QName(k).localname:v for k,v in node.attrib.items() if ET.QName(k).localname!='id'}
    if len(node) or set(attrs)-CROP_OFFSETS: return False
    try: return all(float(v)==0 for v in attrs.values())
    except (ValueError,TypeError): return False


def _image_fill_display(node, binding):
    """A picture fill is information, unlike a freely restyled solid fill."""
    fills=[n for n in node.iter() if _local(n)=='fillImg' and n.get('src')]
    if not fills: return None
    inverse={v:k for k,v in binding['media'].items()}
    numeric=CROP_OFFSETS|{'rotate','rotation','alpha','stretchLeft','stretchRight',
                         'stretchTop','stretchBottom','tileX','tileY','tileOffsetX','tileOffsetY'}
    def payload(part):
        attrs={}
        for key,value in part.attrib.items():
            key=ET.QName(key).localname
            if key=='id': continue
            if key=='src': value=inverse.get(value,value)
            elif key in numeric:
                try: value=float(value)
                except (ValueError,TypeError): pass
            elif key=='rotateWithShape':
                value={'true':True,'1':True,'false':False,'0':False}.get(value.lower(),value)
            attrs[key]=value
        return {'tag':_local(part),'attrs':attrs,
                'text':part.text.strip() if part.text and part.text.strip() else '',
                'children':[payload(c) for c in part if isinstance(c.tag,str)]}
    width,height=float(node.get('width',0)),float(node.get('height',0))
    return {'carrier_type':node.get('type'),
            'carrier_aspect_ratio':round(width/height,8) if height else None,
            'carrier_rotation':float(node.get('rotate',node.get('rotation',0)))%360,
            'fills':[payload(n) for n in fills]}


def _meaning(node, binding, paragraph_policy=None, _state=None):
    if paragraph_policy is None: paragraph_policy=_paragraph_policies(node)
    if _state is None: _state={'paragraph':0}
    kind = _local(node)
    if kind in VISUAL_TAGS: return None
    if kind == 'crop' and _empty_crop(node): return None
    ids_inverse = {v:k for k,v in binding['ids'].items()}
    media_inverse = {v:k for k,v in binding['media'].items()}
    media = [media_inverse.get(n.get('src'),n.get('src')) for n in node.iter() if n.get('src')]
    attrs = {}
    for key,value in node.attrib.items():
        key = ET.QName(key).localname
        if (key in VISUAL_KEYS or key=='space'
                or kind=='shape' and key in {'type','rotate','rotation'}): continue
        if key in REF_KEYS: value = ids_inverse.get(value,value)
        if key=='src': value = media_inverse.get(value,value)
        if kind=='crop' and key in CROP_OFFSETS:
            try: value=float(value)
            except (ValueError,TypeError): pass
        attrs[key] = value
    if kind=='p':
        # Run styles/wrappers can be normalized by the server. Paragraph text,
        # explicit fields/formulas/links and paragraph boundaries remain factual.
        index=_state['paragraph']; _state['paragraph']+=1
        preserve=paragraph_policy[index] if index<len(paragraph_policy) else _preformatted(node)
        special = [_meaning(n,binding,paragraph_policy,_state) for n in node.iter() if n is not node
                   and _local(n) not in {'span','strong','em','u','del'}
                   and (_local(n) in {'br','tab','field','formula','a'} or not isinstance(n.tag,str))]
        return {'tag':kind,'attrs':attrs,'text':_paragraph_text(node,preserve),
                'special':[v for v in special if v is not None]}
    if kind=='img':
        w,h = float(node.get('width',0)),float(node.get('height',0))
        attrs['aspect_ratio'] = round(w/h,8) if h else None
        attrs['rotate'] = float(node.get('rotate',node.get('rotation',0))) % 360
        attrs.pop('rotation',None)
    children = [_meaning(n,binding,paragraph_policy,_state) for n in node if isinstance(n.tag,str)]
    return {'tag':kind,'attrs':attrs,'text':node.text.strip() if node.text and node.text.strip() else '',
            'media':media,
            'image_fill_display':_image_fill_display(node,binding),
            'children':[n for n in children if n is not None]}


def validate_migration(authored_xml, contract, bindings=None):
    """Compare actual content against the bound source, permitting visual edits."""
    errors = []
    try:
        if not isinstance(contract,dict) or contract.get('contract_type')!='source_content_migration':
            raise ValueError('Expected a source-content migration contract')
        origin = contract['source']
        source_value = Path(origin['path']) if origin.get('path') else origin['xml']
        src,raw,_ = _read(source_value)
        if hashlib.sha256(raw).hexdigest() != origin.get('sha256'):
            raise ValueError('Bound source bytes changed')
        actual,_,_ = _read(authored_xml)
        if contract.get('explicit_numbering') is True:
            # Canonicalize both original and actual resolved labels. Adding
            # explicit start values is allowed; changing A/B/C to A/A/A is not.
            src=_explicit_lists(src);actual=_explicit_lists(actual)
        chosen = contract['content_ids']; facts = _members(src,contract.get('source_roles'))
        if set(n.get('id') for n in facts)-set(chosen):
            raise ValueError('Contract omitted factual source content')
        binding = _binding(contract.get('bindings'))
        if bindings is not None:
            extra = _binding(bindings)
            binding = _binding({k:{**binding[k],**extra[k]} for k in binding})
        expected = {n.get('id'):n for n in _data(src) if n.get('id') in chosen}
        actual_nodes = list(_data(actual)); byid = {}
        for n in actual_nodes: byid.setdefault(n.get('id'),[]).append(n)
        actual_content_ids = set()
        for old,node in expected.items():
            new = binding['ids'].get(old,old); actual_content_ids.add(new); candidates=byid.get(new,[])
            if len(candidates)!=1:
                errors.append({'code':'missing_or_duplicate_member','member_id':old}); continue
            if _meaning(node,{'ids':{},'media':{}}) != _meaning(candidates[0],binding,_paragraph_policies(node)):
                errors.append({'code':'factual_content_changed','member_id':old})
        source_note=next((n for n in src if _local(n)=='note'),None)
        note_policy=_paragraph_policies(source_note) if source_note is not None else []
        if _note(src)['paragraphs'] != _note(actual,note_policy)['paragraphs']:
            errors.append({'code':'source_note_changed','member_id':'note'})
        frame_ids=set(contract.get('frame_ids',[]))
        for node in actual_nodes:
            if node.get('id') in actual_content_ids: continue
            if node.get('id') in frame_ids:
                if _has_text(node) or _local(node) in {'table','chart','embed'}:
                    errors.append({'code':'frame_example_content_added','member_id':node.get('id')})
            elif _factual(node):
                errors.append({'code':'unexpected_factual_member','member_id':node.get('id')})
    except (OSError,ValueError,TypeError,KeyError,ET.XMLSyntaxError) as exc:
        errors.append({'code':'invalid_migration_contract_or_source','message':str(exc)})
    return {'ok':not errors, 'errors':errors, 'baseline':'source_bound_sml',
            'original_pptx_check_required':True}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__); sub=parser.add_subparsers(dest='command',required=True)
    a=sub.add_parser('prepare-source'); a.add_argument('--source-pptx',required=True); a.add_argument('--work-dir',required=True)
    a.add_argument('--authoring-work-dir')
    a.add_argument('--deck-title',required=True); a.add_argument('--notes-json'); a.add_argument('--source-deck'); a.add_argument('--as',dest='identity',choices=['user','bot'],default='user')
    a=sub.add_parser('inventory'); a.add_argument('--source',required=True); a.add_argument('--source-roles'); a.add_argument('--output',required=True)
    a=sub.add_parser('compose'); a.add_argument('--source',required=True); a.add_argument('--frame',required=True)
    a.add_argument('--content-ids',nargs='+'); a.add_argument('--frame-ids',nargs='+')
    a.add_argument('--target-region',type=float,nargs=4); a.add_argument('--placements'); a.add_argument('--role-styles')
    a.add_argument('--source-roles'); a.add_argument('--bindings'); a.add_argument('--output',required=True); a.add_argument('--contract-out',required=True)
    a.add_argument('--explicit-numbering',action='store_true')
    a=sub.add_parser('validate'); a.add_argument('--xml',required=True); a.add_argument('--contract',required=True); a.add_argument('--bindings')
    args=parser.parse_args(argv)
    load=lambda p: json.loads(Path(p).read_text(encoding='utf-8')) if p else None
    try:
        if args.command=='prepare-source':
            spec=importlib.util.spec_from_file_location('migration_source',Path(__file__).with_name('template_migration_source.py'))
            helper=importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
            result=helper.prepare_source(args.source_pptx,args.work_dir,args.deck_title,notes_json=args.notes_json,source_deck=args.source_deck,identity=args.identity,authoring_work_dir=args.authoring_work_dir)
            print(json.dumps(result,ensure_ascii=False,indent=2)); return 0 if result['ok'] else 1
        if args.command=='validate':
            result=validate_migration(Path(args.xml),load(args.contract),load(args.bindings))
            print(json.dumps(result,ensure_ascii=False,indent=2)); return 0 if result['ok'] else 1
        output=Path(args.output).resolve()
        if output.exists(): raise ValueError('Output exists; use a new versioned path')
        if args.command=='inventory':
            result=source_content(Path(args.source),load(args.source_roles)); output.parent.mkdir(parents=True,exist_ok=True)
            output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        else:
            contract_path=Path(args.contract_out).resolve()
            if contract_path==output or contract_path.exists(): raise ValueError('Contract output must be a new separate file')
            result=compose_migration(Path(args.source),Path(args.frame),args.content_ids,args.frame_ids,args.target_region,
                placements=load(args.placements),role_styles=load(args.role_styles),bindings=load(args.bindings),source_roles=load(args.source_roles),explicit_numbering=args.explicit_numbering)
            output.parent.mkdir(parents=True,exist_ok=True); contract_path.parent.mkdir(parents=True,exist_ok=True)
            output.write_text(result['xml'],encoding='utf-8'); contract_path.write_text(json.dumps(result['contract'],ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'ok':True,'output':str(output)},ensure_ascii=False)); return 0
    except (OSError,ValueError,TypeError,KeyError,ET.XMLSyntaxError) as exc: parser.error(str(exc))


if __name__=='__main__':
    raise SystemExit(main())
