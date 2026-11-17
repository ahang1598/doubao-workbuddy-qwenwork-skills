#!/usr/bin/env python3
"""Inspect complete template elements and extract a selected component as SML.

inventory --source-dir source-slides --output candidates.json
extract --source slide-07.xml --ids a b c --output component.xml
transform --source slide-07.xml --ids a b c --x 40 --y 120 --scale .9 --output component-v2.xml
replace --source slide-07.xml --ids a b c --text-map replacements.json --output component-v3.xml
prepare-fill --source slide-07.xml --ids a b c --output field-plan.json
fill --source slide-07.xml --ids a b c --plan field-plan.json --output component-v4.xml

Inventory lists candidates, not inferred semantic components. Select members by
reading the source page. Extraction preserves source order and styles, refuses
unknown IDs and dangling known element references, and never changes the source.
"""
import argparse
import copy
import hashlib
import json
import math
import sys
from pathlib import Path
from lxml import etree as ET

STYLE_KEYS = {'fontFamily','fontSize','color','bold','italic','underline','strikethrough','lineSpacing','textAlign','verticalAlign','letterSpacing'}
REF_KEYS = {'startShapeId','endShapeId','sourceId','targetId','beginShapeId','shapeId'}
TEXT_TAGS = {'content','p','span','t','strong','em','u','del','a'}
TEXT_CHILD_TAGS = TEXT_TAGS | {'br','tab'}
TABLE_TEXT_CONTAINERS = {'table','thead','tbody','tfoot','tr','td','th'}

def local(element):
    return ET.QName(element).localname if isinstance(element.tag,str) else ''

def read(path):
    root=ET.parse(str(path),ET.XMLParser(resolve_entities=False,no_network=True)).getroot()
    if local(root)!='slide':raise ValueError('Expected a single slide XML')
    return root

def runs(element,inherited=None):
    style=dict(inherited or {})
    style.update({k:v for k,v in element.attrib.items() if k in STYLE_KEYS})
    out=[]
    if element.text and element.text.strip() and local(element) in {'p','span','t'}:
        out.append({'text':element.text,'style':style})
    for c in element:
        if isinstance(c.tag,str):out.extend(runs(c,style))
        if c.tail and c.tail.strip():out.append({'text':c.tail,'style':style})
    return out

def _text_slots(element,table=False):
    """Return ordered source text fields; paths are relative to the real shape.

    A field addresses .text or .tail, never a reconstructed paragraph. Unsupported
    fields/formulas/lists are not flattened into ordinary text.
    """
    slots=[]
    traversable=TEXT_CHILD_TAGS | (TABLE_TEXT_CONTAINERS if table else set())
    text_tags=TEXT_TAGS | ({'td','th'} if table else set())
    def walk(node,path,style,paragraph=None):
        implicit={'strong':{'bold':'true'},'em':{'italic':'true'},
                  'u':{'underline':'true'},'del':{'strikethrough':'true'}}
        style={**style,**implicit.get(local(node),{})}
        style={**style,**{k:v for k,v in node.attrib.items() if k in STYLE_KEYS}}
        if local(node)=='p':paragraph={'path':path,'attributes':dict(node.attrib)}
        if local(node) in text_tags and (node.text and node.text.strip() or not len(node)):
            slots.append(({'slot':path+'#text','text':node.text or '',
                           'style':style,'paragraph':paragraph,
                           'attributes':dict(node.attrib)},node,'text'))
        counts={}
        for child in node:
            if not isinstance(child.tag,str):continue
            kind=local(child);counts[kind]=counts.get(kind,0)+1
            child_path=(path+'/' if path else '')+f'{kind}[{counts[kind]}]'
            if kind in traversable:walk(child,child_path,style,paragraph)
            if child.tail and child.tail.strip():
                slots.append(({'slot':child_path+'#tail','text':child.tail,
                               'style':style,'paragraph':paragraph,
                               'attributes':dict(node.attrib)},child,'tail'))
    if table:
        walk(element,'',{})
    else:
        for index,content in enumerate((n for n in element if local(n)=='content'),1):
            walk(content,f'content[{index}]',{k:v for k,v in element.attrib.items() if k in STYLE_KEYS})
    return slots

def text_slots(element):
    """Inventory addressable p/span fields with inherited style and source order."""
    if local(element)!='shape':return []
    return [{'shape_id':element.get('id'),'order':index,
             'text_type':next((c.get('textType') for c in element if local(c)=='content'),None),
             **slot} for index,(slot,_,_) in enumerate(_text_slots(element),1)]

def inventory(source_dir):
    pages=[]
    for path in sorted(Path(source_dir).glob('slide-*.xml')):
        root=read(path);elements=[]
        for data in root:
            if local(data)!='data':continue
            for e in data:
                if not isinstance(e.tag,str):continue
                elements.append({'id':e.get('id'),'type':local(e),'attributes':dict(e.attrib),'member_ids':[x.get('id') for x in e.iter() if x.get('id')], 'text_runs':runs(e),'text_slots':text_slots(e),'xml':ET.tostring(e,encoding='unicode',with_tail=False)})
        pages.append({'source':str(path),'slide_id':root.get('id'),'elements':elements})
    return {'schema_version':1,'slides':pages}

def extract(source,ids):
    root=read(source);wanted=set(ids)
    if not wanted:raise ValueError('No members selected')
    data=next((e for e in root if local(e)=='data'),None)
    if data is None:raise ValueError('Slide has no data')
    top_ids=[e.get('id') for e in data if isinstance(e.tag,str) and e.get('id')]
    if len(top_ids)!=len(set(top_ids)):raise ValueError('Duplicate top-level member IDs in source')
    lookup={e.get('id'):e for e in data if isinstance(e.tag,str) and e.get('id')}
    missing=wanted-set(lookup)
    if missing:raise ValueError('missing top-level member IDs: '+', '.join(sorted(missing)))
    chosen=[e for e in data if e.get('id') in wanted]
    available={e.get('id') for e in root.iter() if e.get('id')}
    included={e.get('id') for top in chosen for e in top.iter() if e.get('id')}
    for top in chosen:
        for e in top.iter():
            for key,value in e.attrib.items():
                if key in REF_KEYS and value not in available:
                    raise ValueError(f'Unresolved source reference: {top.get("id")} -> {value}')
                if key in REF_KEYS and value not in included:
                    raise ValueError(f'Unselected reference: {top.get("id")} -> {value}')
    out=ET.Element(root.tag,attrib={k:v for k,v in root.attrib.items() if k!='id'},nsmap=root.nsmap)
    for e in root:
        if local(e)=='style':out.append(copy.deepcopy(e))
    target=ET.SubElement(out,data.tag,attrib=dict(data.attrib))
    for e in chosen:target.append(copy.deepcopy(e))
    return ET.tostring(out,encoding='unicode',pretty_print=True)

def replace_component_text(source,ids,text_map):
    """Copy a complete component and change only explicitly addressed text fields.

    text_map is {real_shape_id: new_text} for a single paragraph/run, or
    {real_shape_id: {"content[1]/p[1]/span[1]#text": new_text, ...}} for rich text.
    Omitted slots/members remain unchanged. Multi-paragraph/run content requires
    explicit slots from inventory; no merging, script-aware redistribution or
    font substitution occurs. Assign Latin/EA runs separately using their source
    styles. Font availability, glyph coverage and fit require rendered review.
    New paragraph/line/tab breaks and unsupported field/formula/list content fail.
    """
    if not isinstance(text_map,dict) or not text_map:raise ValueError('text_map must be a nonempty object keyed by source shape ID')
    source_raw=Path(source).read_bytes()
    xml=extract(source,ids)
    root=ET.fromstring(xml.encode(),ET.XMLParser(resolve_entities=False,no_network=True))
    data=next(e for e in root if local(e)=='data')
    lookup={e.get('id'):e for e in data}
    replacements=[]
    for shape_id,values in text_map.items():
        if shape_id not in lookup:raise ValueError('Unselected or missing text shape ID: '+str(shape_id))
        shape=lookup[shape_id]
        if local(shape)!='shape':raise ValueError('Text replacement requires a source shape: '+str(shape_id))
        contents=[c for c in shape if local(c)=='content']
        if len(contents)!=1:raise ValueError('Expected one source content element: '+str(shape_id))
        unsupported=[local(c) for c in contents[0].iter() if local(c) not in TEXT_CHILD_TAGS]
        if unsupported:raise ValueError('Unsupported rich text in '+str(shape_id)+': '+', '.join(sorted(set(unsupported))))
        slots=_text_slots(shape);by_slot={slot['slot']:(slot,node,field) for slot,node,field in slots}
        if isinstance(values,str):
            if len(slots)!=1 or any(local(c) in {'br','tab'} for c in contents[0].iter()):
                raise ValueError('Ambiguous text slots in '+str(shape_id)+'; use explicit p/span slot paths from inventory')
            values={slots[0][0]['slot']:values}
        if not isinstance(values,dict) or not values:raise ValueError('Text replacement must be a string or nonempty slot object: '+str(shape_id))
        for address,value in values.items():
            if address not in by_slot:raise ValueError('Unknown text slot in '+str(shape_id)+': '+str(address))
            if not isinstance(value,str):raise ValueError('Replacement text must be a string: '+str(address))
            if any(c in value for c in '\r\n\t\u2028\u2029'):raise ValueError('Replacement text cannot add line/paragraph/tab breaks: '+str(address))
            slot,node,field=by_slot[address]
            setattr(node,field,value)
            replacements.append({'shape_id':shape_id,'slot':address,'before':slot['text'],'after':value})
    result=ET.tostring(root,encoding='unicode',pretty_print=True)
    if Path(source).read_bytes()!=source_raw:raise ValueError('Source changed during text replacement')
    return {'xml':result,'source':str(Path(source).resolve()),
            'source_sha256':hashlib.sha256(source_raw).hexdigest(),
            'member_ids':[n.get('id') for n in data],
            'text_replacements':replacements,'xml_sha256':hashlib.sha256(result.encode()).hexdigest()}


def _component_fill_state(source,ids):
    """Copy selected source members and index their real rich-text fields."""
    raw=Path(source).read_bytes()
    original=read(source)
    xml=extract(source,ids)
    root=ET.fromstring(xml.encode(),ET.XMLParser(resolve_entities=False,no_network=True))
    data=next(e for e in root if local(e)=='data')
    fields=[];owner_ids=set()
    for owner in data.iter():
        kind=local(owner)
        if kind not in {'shape','table'}:continue
        # A table owns its nested cell paths; do not inventory them again as
        # independent owners. Structural chart data remains a chart operation.
        if any(local(p) in {'table','chart'} for p in owner.iterancestors() if p is not data):continue
        is_table=kind=='table'
        contents=[c for c in owner.iter() if local(c)=='content'] if is_table else [c for c in owner if local(c)=='content']
        if not is_table and not contents:continue
        owner_id=owner.get('id')
        if not owner_id or owner_id in owner_ids:
            raise ValueError('Missing or duplicate text owner ID: '+str(owner_id))
        owner_ids.add(owner_id)
        if not is_table and len(contents)!=1:raise ValueError('Expected one source content element: '+owner_id)
        for content in contents:
            unsupported={local(c) for c in content.iter() if local(c) not in TEXT_CHILD_TAGS}
            if unsupported:raise ValueError('Unsupported rich text in '+owner_id+': '+', '.join(sorted(unsupported)))
        for slot,node,attribute in _text_slots(owner,table=is_table):
            field={'shape_id':owner_id,'slot':slot['slot'],'source_text':slot['text'],
                   'owner_type':kind,
                   'order':len(fields)+1,'style':slot['style'],
                   'paragraph':slot['paragraph'],'attributes':slot['attributes']}
            fields.append((field,node,attribute))
    addressed={(node,attribute) for _,node,attribute in fields}
    for node in data.iter():
        if local(node)=='chart' or any(local(p)=='chart' for p in node.iterancestors()):continue
        if (local(node) in TEXT_TAGS and (node.text and node.text.strip() or not len(node))
                and (node,'text') not in addressed):
            raise ValueError('Unsupported text owner for source '+local(node)+' field')
        if node.tail and node.tail.strip() and (node,'tail') not in addressed:
            raise ValueError('Unsupported text owner for source '+local(node)+' tail')
    if Path(source).read_bytes()!=raw:raise ValueError('Source changed during component fill preparation')
    origin={'source':str(Path(source).resolve()),'source_id':original.get('id'),
            'source_sha256':hashlib.sha256(raw).hexdigest(),
            'member_ids':[n.get('id') for n in data],
            'all_member_ids':[n.get('id') for n in data.iter() if n.get('id')]}
    return raw,root,origin,fields


def prepare_component_fill(source,ids):
    """Plan every selected p/span text or tail field in source order.

    Each field requires an explicit replace, keep_label or remove decision.
    shape_id is the source owner ID (shape or table). Native table fields use
    their stable tr/td/content/p/span paths, including inherited styles/tails.
    The plan inventories text; it does not infer semantic labels or flatten
    source formulas/lists. Geometric and non-text source members remain intact.
    """
    _,_,origin,fields=_component_fill_state(source,ids)
    return {'schema_version':1,**origin,
            'fields':[{**field,'action':None,'new_text':None} for field,_,_ in fields]}


def fill_component(source,ids,plan):
    """Fill a complete source-bound plan, never return a partial deliverable.

    replace changes only the real text/tail value; keep_label retains it;
    remove clears that value without deleting its run, paragraph or shape.
    Missing/undecided fields return incomplete_plan without XML. Invalid,
    stale or ambiguous plans raise ValueError before any field is changed.
    """
    raw,root,origin,fields=_component_fill_state(source,ids)
    if not isinstance(plan,dict) or not isinstance(plan.get('fields'),list):
        raise ValueError('Fill plan must contain a fields array')
    if plan.get('source_sha256')!=origin['source_sha256']:
        raise ValueError('Source hash/sha256 does not match fill plan')
    if plan.get('source_id')!=origin['source_id'] or plan.get('member_ids')!=origin['member_ids']:
        raise ValueError('Source ID or selected member IDs do not match fill plan')
    expected={(f['shape_id'],f['slot']):f for f,_,_ in fields}
    decisions={}
    for field in plan['fields']:
        if not isinstance(field,dict):raise ValueError('Every fill field must be an object')
        if not all(isinstance(field.get(k),str) for k in ('shape_id','slot')):
            raise ValueError('Fill field shape_id and slot must be strings')
        key=(field.get('shape_id'),field.get('slot'))
        if key not in expected:raise ValueError('Unknown fill field: '+str(key))
        if key in decisions:raise ValueError('Duplicate fill field: '+str(key))
        if field.get('source_text')!=expected[key]['source_text']:
            raise ValueError('Source text does not match fill field: '+str(key))
        decisions[key]=field
    missing=[];operations=[]
    for field,node,attribute in fields:
        key=(field['shape_id'],field['slot']);decision=decisions.get(key)
        if decision is None or decision.get('action') in (None,''):
            missing.append({**field,'reason':'missing_field' if decision is None else 'undecided_action'})
            continue
        action=decision['action'];value=decision.get('new_text')
        if action=='replace':
            if not isinstance(value,str):raise ValueError('Replacement text must be a string: '+str(key))
            if any(c in value for c in '\r\n\t\u2028\u2029'):
                raise ValueError('Replacement text cannot add line/paragraph/tab breaks: '+str(key))
        elif action=='keep_label':
            if value is not None and value!=field['source_text']:
                raise ValueError('keep_label cannot supply different text: '+str(key))
            value=field['source_text']
        elif action=='remove':
            if value not in (None,''):raise ValueError('remove cannot supply replacement text: '+str(key))
            value=''
        else:raise ValueError('Unknown fill action: '+str(action))
        operations.append((field,node,attribute,action,value))
    if missing:
        return {'ok':False,'status':'incomplete_plan',**origin,
                'required_field_count':len(fields),'completed_field_count':0,'missing_fields':missing}
    summary=[]
    for field,node,attribute,action,value in operations:
        setattr(node,attribute,value)
        summary.append({**field,'action':action,'new_text':value})
    xml=ET.tostring(root,encoding='unicode',pretty_print=True)
    if Path(source).read_bytes()!=raw:raise ValueError('Source changed during component fill')
    return {'ok':True,'status':'complete','xml':xml,**origin,
            'completed_field_count':len(summary),'field_summary':summary,
            'xml_sha256':hashlib.sha256(xml.encode()).hexdigest()}


PIXEL_TEXT_KEYS={'fontSize','paddingLeft','paddingRight','paddingTop','paddingBottom',
                 'marginLeft','marginRight','marginTop','marginBottom','letterSpacing','indent','defaultTabSize'}


def transform_component(source,ids,*,x=None,y=None,scale=1):
    """Apply one affine map to a complete selected group without rewriting facts.

    Target x/y is the group's bounding-box origin. A uniform scale preserves
    aspect ratios, font hierarchies and endpoint relations. Source colors,
    tokens, chart values, IDs and reference strings remain unchanged. Custom
    shape paths scale in local frame units; rotation/flips remain on the shape.
    Host members and unsupported path syntax fail before returning any XML.
    """
    if not isinstance(scale,(int,float)) or not math.isfinite(scale) or scale<=0:
        raise ValueError('scale must be a positive finite number')
    for value in (x,y):
        if value is not None and (not isinstance(value,(int,float)) or not math.isfinite(value)):
            raise ValueError('target origin must be finite')
    source_raw=Path(source).read_bytes()
    result=extract(source,ids)
    root=ET.fromstring(result.encode(),ET.XMLParser(resolve_entities=False,no_network=True))
    data=next(e for e in root if local(e)=='data')
    boxes=[];geometry=[];custom_paths=[]
    def number(value):
        value=float(value)
        if not math.isfinite(value):raise ValueError('nonfinite source geometry/style')
        return value
    def encoded(value):return format(value,'.15g')
    for node in data:
        kind=local(node)
        if kind=='shape' and node.get('type')=='host':
            raise ValueError('unsupported host component transform: '+str(node.get('id')))
        if kind=='shape' and node.get('type')=='custom':
            # Reuse SVG's command-aware parser, including relative commands and
            # compact arc flags. Support direct CLI and file-loaded migration
            # callers without requiring them to configure a Python module path.
            directory=str(Path(__file__).resolve().parent.parent)
            if directory not in sys.path:sys.path.insert(0,directory)
            from svg_lib.atomize_svg_to_slide._geometry import scale_local_path
            try:custom_paths.append((node,scale_local_path(node.get('path'),scale)))
            except ValueError as error:
                raise ValueError('unsupported custom path for '+str(node.get('id'))+': '+str(error)) from error
        if kind not in {'shape','img','chart','table','line','icon'}:
            raise ValueError('unsupported component member: '+kind)
        if kind=='line' and all(node.get(k) is not None for k in ('startX','startY','endX','endY')):
            points=tuple(number(node.get(k)) for k in ('startX','startY','endX','endY'))
            boxes.append((min(points[0],points[2]),min(points[1],points[3]),max(points[0],points[2]),max(points[1],points[3])))
            geometry.append((node,'native_endpoints',points))
        elif all(node.get(k) is not None for k in ('width','height')):
            px,py=number(node.get('topLeftX','0')),number(node.get('topLeftY','0'))
            w,h=number(node.get('width')),number(node.get('height'))
            if w<0 or h<0:raise ValueError('negative source bbox dimensions')
            boxes.append((px,py,px+w,py+h));geometry.append((node,'bbox',(px,py,w,h)))
        elif kind=='line' and all(node.get(k) is not None for k in ('x1','y1','x2','y2')):
            points=tuple(number(node.get(k)) for k in ('x1','y1','x2','y2'))
            boxes.append((min(points[0],points[2]),min(points[1],points[3]),max(points[0],points[2]),max(points[1],points[3])))
            geometry.append((node,'endpoints',points))
        elif kind=='line' and any(node.get(k) for k in REF_KEYS):
            # extract already verifies endpoint nodes are inside this group;
            # native references follow the transformed nodes at render time.
            geometry.append((node,'linked',()))
        else:
            raise ValueError('unsupported or missing member geometry: '+str(node.get('id')))
    if not boxes:raise ValueError('component has no measurable source bbox')
    left,top=min(b[0] for b in boxes),min(b[1] for b in boxes)
    right,bottom=max(b[2] for b in boxes),max(b[3] for b in boxes)
    tx=left if x is None else float(x);ty=top if y is None else float(y)
    mx=lambda value:tx+(value-left)*scale
    my=lambda value:ty+(value-top)*scale
    for node,path in custom_paths:node.set('path',path)
    for node,kind,values in geometry:
        if kind=='bbox':
            px,py,w,h=values
            for key,value in [('topLeftX',mx(px)),('topLeftY',my(py)),('width',w*scale),('height',h*scale)]:
                node.set(key,encoded(value))
        elif kind in {'endpoints','native_endpoints'}:
            keys=('startX','startY','endX','endY') if kind=='native_endpoints' else ('x1','y1','x2','y2')
            for key,value in zip(keys,(mx(values[0]),my(values[1]),mx(values[2]),my(values[3]))):
                node.set(key,encoded(value))
        if kind in {'endpoints','native_endpoints','linked'} and node.get('width') is not None:
            node.set('width',encoded(number(node.get('width'))*scale))
        for part in node.iter():
            for key in PIXEL_TEXT_KEYS:
                if part.get(key) is not None:part.set(key,encoded(number(part.get(key))*scale))
            if local(part) in {'border','line'} and part.get('width') is not None and part is not node:
                part.set('width',encoded(number(part.get('width'))*scale))
            if local(part)=='shadow':
                for key in ('offset','blur'):
                    if part.get(key) is not None:part.set(key,encoded(number(part.get(key))*scale))
    xml=ET.tostring(root,encoding='unicode',pretty_print=True)
    if Path(source).read_bytes()!=source_raw:raise ValueError('Source changed during component transform')
    return {'xml':xml,'source':str(Path(source).resolve()),
            'source_sha256':hashlib.sha256(source_raw).hexdigest(),
            'member_ids':[n.get('id') for n in data],
            'source_bbox':{'x':left,'y':top,'width':right-left,'height':bottom-top},
            'target_bbox':{'x':tx,'y':ty,'width':(right-left)*scale,'height':(bottom-top)*scale},
            'scale':scale,'xml_sha256':hashlib.sha256(xml.encode()).hexdigest()}

def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    a=sub.add_parser('inventory');a.add_argument('--source-dir',required=True);a.add_argument('--output',required=True)
    b=sub.add_parser('extract');b.add_argument('--source',required=True);b.add_argument('--ids',nargs='+',required=True);b.add_argument('--output',required=True)
    c=sub.add_parser('transform');c.add_argument('--source',required=True);c.add_argument('--ids',nargs='+',required=True);c.add_argument('--output',required=True)
    c.add_argument('--x',type=float);c.add_argument('--y',type=float);c.add_argument('--scale',type=float,default=1)
    d=sub.add_parser('replace');d.add_argument('--source',required=True);d.add_argument('--ids',nargs='+',required=True)
    d.add_argument('--text-map',required=True,help='JSON object of real shape IDs to text or explicit p/span slot objects')
    d.add_argument('--output',required=True)
    e=sub.add_parser('prepare-fill');e.add_argument('--source',required=True);e.add_argument('--ids',nargs='+',required=True)
    e.add_argument('--output',required=True)
    f=sub.add_parser('fill');f.add_argument('--source',required=True);f.add_argument('--ids',nargs='+',required=True)
    f.add_argument('--plan',required=True,help='Complete source-bound field plan from prepare-fill')
    f.add_argument('--output',required=True)
    args=parser.parse_args();out=Path(args.output)
    if out.exists():parser.error('Output exists; use a new versioned path')
    manifest=None;manifest_path=None
    try:
        if args.command=='inventory':result=json.dumps(inventory(args.source_dir),ensure_ascii=False,indent=2)
        elif args.command=='extract':result=extract(args.source,args.ids)
        elif args.command=='transform':
            transformed=transform_component(args.source,args.ids,x=args.x,y=args.y,scale=args.scale)
            result=transformed.pop('xml');manifest=transformed
            manifest_path=out.with_suffix('.transform.json')
        elif args.command=='replace':
            replaced=replace_component_text(args.source,args.ids,json.loads(Path(args.text_map).read_text(encoding='utf-8')))
            result=replaced.pop('xml');manifest=replaced
            manifest_path=out.with_suffix('.replace.json')
        elif args.command=='prepare-fill':
            result=json.dumps(prepare_component_fill(args.source,args.ids),ensure_ascii=False,indent=2)
        else:
            filled=fill_component(args.source,args.ids,json.loads(Path(args.plan).read_text(encoding='utf-8')))
            if not filled['ok']:
                print(json.dumps(filled,ensure_ascii=False))
                parser.exit(2)
            result=filled.pop('xml');manifest=filled
            manifest_path=out.with_suffix('.fill.json')
        if manifest_path==out:raise ValueError('XML output and manifest must use different paths')
        if manifest_path is not None and manifest_path.exists():raise ValueError('Manifest output exists')
    except (ValueError,OSError,ET.XMLSyntaxError) as e:parser.error(str(e))
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('x',encoding='utf-8') as f:f.write(result+'\n')
    if manifest is not None:
        # Hash the actual serialized output, including its trailing newline.
        manifest['xml_sha256']=hashlib.sha256(out.read_bytes()).hexdigest()
        with manifest_path.open('x',encoding='utf-8') as f:json.dump(manifest,f,ensure_ascii=False,indent=2)
    print(json.dumps({'ok':True,'output':str(out)},ensure_ascii=False))

if __name__=='__main__':main()
