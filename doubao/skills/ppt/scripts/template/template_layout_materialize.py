#!/usr/bin/env python3
"""Expose zero-slide PPTX/POTX design layouts as full importable working pages.

materialize_layouts(source, output, *, layouts=None, placeholders='markers')

The new slides clone original placeholder shapes and their group transforms.
Original master/layout/theme/media bytes remain intact; backgrounds and static
decorations render once through normal inheritance. Content text changes to short slot
markers or empty strings; paragraphs, runs, formatting and geometry stay intact.
System date/footer/header/slide-number fields are retained. No data, graphics,
images, font substitution, cloud import or publishing is performed.
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
from xml.dom import Node
from xml.dom.minidom import parseString
from xml.parsers import expat
import zipfile

P='http://schemas.openxmlformats.org/presentationml/2006/main'
A='http://schemas.openxmlformats.org/drawingml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
REL='http://schemas.openxmlformats.org/package/2006/relationships'
CT='http://schemas.openxmlformats.org/package/2006/content-types'
APP='http://schemas.openxmlformats.org/officeDocument/2006/extended-properties'
VT='http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes'
PRESENTATION_MIME='application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml'
TEMPLATE_MIME='application/vnd.openxmlformats-officedocument.presentationml.template.main+xml'
SLIDE_MIME='application/vnd.openxmlformats-officedocument.presentationml.slide+xml'
LAYOUT_PATTERN=re.compile(r'ppt/slideLayouts/slideLayout(\d+)\.xml$')
SYSTEM_PLACEHOLDERS={'dt','ftr','hdr','sldNum'}
MARKERS={'title':'T','ctrTitle':'T','subTitle':'S',
         'body':'B','obj':'O','pic':'I','chart':'C',
         'tbl':'TB','media':'M','dgm':'D','clipArt':'I'}


def _sha(raw):return hashlib.sha256(raw).hexdigest()
def _children(node):return [n for n in node.childNodes if n.nodeType==Node.ELEMENT_NODE]
def _direct(node,ns,name):return [n for n in _children(node) if n.namespaceURI==ns and n.localName==name]
def _text(node):return ''.join(n.data for n in node.childNodes if n.nodeType in (Node.TEXT_NODE,Node.CDATA_SECTION_NODE))
def _xml(raw):
    checker=expat.ParserCreate()
    def reject(*args):raise ValueError('DTD and entity declarations are not supported')
    checker.StartDoctypeDeclHandler=reject;checker.EntityDeclHandler=reject;checker.ExternalEntityRefHandler=reject
    checker.SetParamEntityParsing(expat.XML_PARAM_ENTITY_PARSING_NEVER)
    try:checker.Parse(raw,True)
    except expat.ExpatError as exc:raise ValueError('Invalid package XML') from exc
    return parseString(raw)
def _bytes(tree):return tree.toxml(encoding='utf-8')
def _set_text(node,value):
    for child in list(node.childNodes):node.removeChild(child)
    if value:node.appendChild(node.ownerDocument.createTextNode(value))
def _tag(root,name):return (root.prefix+':' if root.prefix else '')+name
def _rels_name(owner):return posixpath.join(posixpath.dirname(owner),'_rels',posixpath.basename(owner)+'.rels')
def _resolve(owner,target):return target.lstrip('/') if target.startswith('/') else posixpath.normpath(posixpath.join(posixpath.dirname(owner),target))
def _rel_owner(name):
    if name=='_rels/.rels':return ''
    return posixpath.join(posixpath.dirname(posixpath.dirname(name)),posixpath.basename(name)[:-5])
def _relations(parts,owner):
    name='_rels/.rels' if not owner else _rels_name(owner)
    if name not in parts:return []
    nodes=_xml(parts[name]).getElementsByTagNameNS(REL,'Relationship');seen=set();out=[]
    for node in nodes:
        rid=node.getAttribute('Id')
        if not rid or rid in seen:raise ValueError('Missing/duplicate relationship ID: '+name)
        seen.add(rid)
        record={node.attributes.item(i).name:node.attributes.item(i).value for i in range(node.attributes.length)}
        if record.get('TargetMode')!='External':
            target=_resolve(owner,record.get('Target',''))
            if target not in parts:raise ValueError('Missing internal relationship target: '+target)
            record['_resolved']=target
        out.append(record)
    return out

def _validate_relationships(parts):
    for name in parts:
        if name.endswith('.rels') and (name=='_rels/.rels' or '/_rels/' in name):
            owner=_rel_owner(name)
            if not owner or owner in parts:_relations(parts,owner)

def _retain_placeholder_shapes(tree):
    """Keep source slots and necessary group transforms; inherit all static art."""
    for child in list(_children(tree)):
        if child.namespaceURI==P and child.localName in ('nvGrpSpPr','grpSpPr'):continue
        if child.namespaceURI==P and child.localName=='grpSp':_retain_placeholder_shapes(child)
        if not child.getElementsByTagNameNS(P,'ph'):tree.removeChild(child)

def _new_slide(layout_raw,mode,page_number):
    layout=_xml(layout_raw);old=layout.documentElement
    if old.namespaceURI!=P or old.localName!='sldLayout':raise ValueError('Expected a real slideLayout part')
    csld=_direct(old,P,'cSld')
    if len(csld)!=1:raise ValueError('Layout requires one complete cSld')
    document=old.ownerDocument.implementation.createDocument(P,_tag(old,'sld'),None)
    root=document.documentElement
    for i in range(old.attributes.length):
        attr=old.attributes.item(i)
        if attr.name=='xmlns' or attr.name.startswith('xmlns:') or attr.name=='mc:Ignorable':root.setAttribute(attr.name,attr.value)
    if old.prefix:root.setAttribute('xmlns:'+old.prefix,P)
    else:root.setAttribute('xmlns',P)
    for name in ('showMasterSp','showMasterPhAnim'):
        if old.hasAttribute(name):root.setAttribute(name,old.getAttribute(name))
    copied=document.importNode(csld[0],True);root.appendChild(copied)
    for background in _direct(copied,P,'bg'):copied.removeChild(background)
    trees=_direct(copied,P,'spTree')
    if len(trees)!=1:raise ValueError('Layout requires one original shape tree')
    _retain_placeholder_shapes(trees[0])
    for node in _direct(old,P,'clrMapOvr'):root.appendChild(document.importNode(node,True))
    slots=[]
    for shape in list(copied.getElementsByTagNameNS(P,'sp'))+list(copied.getElementsByTagNameNS(P,'pic'))+list(copied.getElementsByTagNameNS(P,'graphicFrame')):
        ph=shape.getElementsByTagNameNS(P,'ph')
        if not ph:continue
        if len(ph)!=1:raise ValueError('Ambiguous placeholder in original layout')
        ids=shape.getElementsByTagNameNS(P,'cNvPr');sid=ids[0].getAttribute('id') if ids else None
        kind=ph[0].getAttribute('type') or 'obj';idx=ph[0].getAttribute('idx') or '0'
        geometry=shape.getElementsByTagNameNS(A,'xfrm')
        before=_sha(shape.toxml(encoding='utf-8'))
        marker=None
        if kind not in SYSTEM_PLACEHOLDERS:
            leaves=shape.getElementsByTagNameNS(A,'t')
            if leaves:
                marker=f"[{MARKERS.get(kind,'X')}{page_number:02d}_{len(slots)+1}]" if mode=='markers' else ''
                for index,leaf in enumerate(leaves):_set_text(leaf,marker if index==0 else '')
        slots.append({'slot_id':f'{page_number}:{sid}:{idx}','shape_id':sid,'placeholder_type':kind,
            'placeholder_idx':idx,'placeholder_attributes':{ph[0].attributes.item(i).name:ph[0].attributes.item(i).value for i in range(ph[0].attributes.length)},'system_field_preserved':kind in SYSTEM_PLACEHOLDERS,
            'marker':marker,'original_shape_xml_sha256':before,
            'geometry_xml':geometry[0].toxml() if geometry else None,
            'geometry_source':'original layout xfrm' if geometry else 'original layout/master inheritance',
            'paragraph_run_style_and_geometry_preserved':True})
    return _bytes(document),slots,csld[0].getAttribute('name')


def _append_slide_ids(presentation,relationships,rows):
    root=presentation.documentElement
    lists=_direct(root,P,'sldIdLst')
    if lists:lst=lists[0]
    else:
        lst=presentation.createElementNS(P,_tag(root,'sldIdLst'))
        before={'sldSz','notesSz','smartTags','embeddedFontLst','custShowLst','photoAlbum','custDataLst','kinsoku','defaultTextStyle','modifyVerifier','extLst'}
        anchor=next((n for n in _children(root) if n.localName in before),None)
        root.insertBefore(lst,anchor)
    root.setAttribute('xmlns:r',R)
    rr=relationships.documentElement
    existing={n.getAttribute('Id') for n in relationships.getElementsByTagNameNS(REL,'Relationship')}
    next_id=256
    all_ids=presentation.getElementsByTagNameNS(P,'sldId')
    if all_ids:next_id=max([255]+[int(n.getAttribute('id')) for n in all_ids])+1
    for row in rows:
        rid='rIdMaterialized'+str(row['page'])
        while rid in existing:rid+='x'
        existing.add(rid)
        relation=relationships.createElementNS(REL,_tag(rr,'Relationship'))
        for k,v in {'Id':rid,'Type':R+'/slide','Target':posixpath.relpath(row['slide_part'],'ppt')}.items():relation.setAttribute(k,v)
        rr.appendChild(relation)
        sid=presentation.createElementNS(P,_tag(root,'sldId'));sid.setAttribute('id',str(next_id));sid.setAttributeNS(R,'r:id',rid)
        lst.appendChild(sid);row.update(presentation_slide_id=next_id,presentation_relationship_id=rid);next_id+=1

def _app_metadata(raw,rows):
    doc=_xml(raw)
    for n in doc.getElementsByTagNameNS(APP,'Slides'):_set_text(n,str(len(rows)))
    hp=doc.getElementsByTagNameNS(APP,'HeadingPairs');tp=doc.getElementsByTagNameNS(APP,'TitlesOfParts')
    if hp and tp:
        hv=hp[0].getElementsByTagNameNS(VT,'vector');tv=tp[0].getElementsByTagNameNS(VT,'vector')
        if hv and tv:
            variants=_children(hv[0]);titles=_children(tv[0]);offset=0
            for index in range(0,len(variants)-1,2):
                label=variants[index].getElementsByTagNameNS(VT,'lpstr');count=variants[index+1].getElementsByTagNameNS(VT,'i4')
                if not label or not count:continue
                size=int(_text(count[0]))
                if _text(label[0])=='Slide Titles':
                    tail=titles[offset+size:];anchor=tail[0] if tail else None
                    for node in titles[offset:offset+size]:tv[0].removeChild(node)
                    for row in rows:
                        name=doc.createElementNS(VT,_tag(tv[0],'lpstr'));name.appendChild(doc.createTextNode(row['layout_name'] or row['layout_part']))
                        tv[0].insertBefore(name,anchor)
                    _set_text(count[0],str(len(rows)));tv[0].setAttribute('size',str(len(titles)-size+len(rows)))
                offset+=size
    return _bytes(doc)


def materialize_layouts(source,output,*,layouts=None,placeholders='markers'):
    """Return a source-bound receipt and write a complete working presentation.

    layouts is an ordered list of exact original package part names; repeated
    layout selections are allowed. None means every original layout. Source
    must contain zero actual presentation slides. Marker labels identify source
    slots; they are not fake native cloud IDs. All original package members are
    retained. Existing different outputs and source aliases are rejected.
    """
    source,output=Path(source).resolve(),Path(output).resolve()
    if source.suffix.lower() not in ('.pptx','.potx'):raise ValueError('Source must be PPTX or POTX')
    if output.suffix.lower()!='.pptx':raise ValueError('Working output must be a standard PPTX')
    if source==output or output.exists() and os.path.samefile(source,output):raise ValueError('Output must be distinct from original source')
    if placeholders not in ('markers','empty'):raise ValueError('placeholders must be markers or empty')
    original=source.read_bytes()
    with zipfile.ZipFile(io.BytesIO(original)) as archive:
        infos=archive.infolist()
        if len({i.filename for i in infos})!=len(infos):raise ValueError('Duplicate original package member names')
        records=[(copy.copy(info),archive.read(info)) for info in infos];comment=archive.comment
    before={info.filename:raw for info,raw in records};after=dict(before)
    presentation=_xml(before['ppt/presentation.xml']);root=presentation.documentElement
    if root.namespaceURI!=P or root.localName!='presentation':raise ValueError('Expected a standard presentation main part')
    dimensions=_direct(root,P,'sldSz')
    if len(dimensions)!=1:raise ValueError('Original presentation requires canvas dimensions')
    canvas={key:int(dimensions[0].getAttribute(key)) for key in ('cx','cy')}
    if any(value<=0 for value in canvas.values()):raise ValueError('Invalid original canvas dimensions')
    lists=_direct(root,P,'sldIdLst')
    if len(lists)>1 or lists and _direct(lists[0],P,'sldId'):raise ValueError('Materialization accepts zero actual slides only')
    available=sorted((n for n in before if LAYOUT_PATTERN.fullmatch(n)),key=lambda n:int(LAYOUT_PATTERN.fullmatch(n).group(1)))
    selected=available if layouts is None else list(layouts) if not isinstance(layouts,str) else [layouts]
    if not selected or any(not isinstance(n,str) or n not in available for n in selected):raise ValueError('Select actual original slideLayout package parts')
    _validate_relationships(before)
    types=_xml(before['[Content_Types].xml']);main=[n for n in types.getElementsByTagNameNS(CT,'Override') if n.getAttribute('PartName')=='/ppt/presentation.xml']
    if len(main)!=1 or main[0].getAttribute('ContentType') not in (PRESENTATION_MIME,TEMPLATE_MIME):raise ValueError('Unsupported presentation main content type')
    normalized=main[0].getAttribute('ContentType')==TEMPLATE_MIME;main[0].setAttribute('ContentType',PRESENTATION_MIME)
    rels=_xml(before['ppt/_rels/presentation.xml.rels'])
    numbers=[int(re.fullmatch(r'ppt/slides/slide(\d+)\.xml',n).group(1)) for n in before if re.fullmatch(r'ppt/slides/slide(\d+)\.xml',n)]
    next_number=max(numbers or [0])+1;pages=[];new_parts={}
    for page,layout_part in enumerate(selected,1):
        related=_relations(before,layout_part);masters=[r for r in related if r.get('Type')==R+'/slideMaster']
        if len(masters)!=1:raise ValueError('Original layout requires exactly one original master relationship')
        slide_part=f'ppt/slides/slide{next_number}.xml';next_number+=1
        slide,slots,name=_new_slide(before[layout_part],placeholders,page)
        rd=parseString(f'<Relationships xmlns="{REL}"/>');rr=rd.documentElement;ids=set()
        for record in related:
            if record['Type']==R+'/slideMaster':continue
            relation=rd.createElementNS(REL,'Relationship')
            for k,v in record.items():
                if k.startswith('_'):continue
                if k=='Target' and record.get('TargetMode')!='External':v=posixpath.relpath(record['_resolved'],posixpath.dirname(slide_part))
                relation.setAttribute(k,v)
            rr.appendChild(relation);ids.add(record['Id'])
        rid='rIdMaterializedLayout'
        while rid in ids:rid+='x'
        relation=rd.createElementNS(REL,'Relationship')
        for k,v in {'Id':rid,'Type':R+'/slideLayout','Target':posixpath.relpath(layout_part,posixpath.dirname(slide_part))}.items():relation.setAttribute(k,v)
        rr.appendChild(relation)
        new_parts[slide_part]=slide;new_parts[_rels_name(slide_part)]=_bytes(rd)
        override=types.createElementNS(CT,_tag(types.documentElement,'Override'));override.setAttribute('PartName','/'+slide_part);override.setAttribute('ContentType',SLIDE_MIME);types.documentElement.appendChild(override)
        pages.append({'page':page,'slide_part':slide_part,'layout_part':layout_part,'layout_name':name,'master_part':masters[0]['_resolved'],'source_layout_sha256':_sha(before[layout_part]),'slots':slots,'framework':'original placeholders/group transforms plus unchanged layout/master/theme inheritance; static artwork inherited once'})
    _append_slide_ids(presentation,rels,pages)
    after['ppt/presentation.xml']=_bytes(presentation);after['ppt/_rels/presentation.xml.rels']=_bytes(rels);after['[Content_Types].xml']=_bytes(types)
    if 'docProps/app.xml' in after:after['docProps/app.xml']=_app_metadata(before['docProps/app.xml'],pages)
    after.update(new_parts);_validate_relationships(after)
    protected=[n for n in before if n.startswith(('ppt/slideMasters/','ppt/slideLayouts/','ppt/theme/','ppt/media/','ppt/notesMasters/'))]
    if not all(after[n]==before[n] for n in protected):raise ValueError('Original design/resource part changed')
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w') as archive:
        archive.comment=comment
        for info,_ in records:archive.writestr(info,after[info.filename])
        for name,raw in new_parts.items():
            info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;archive.writestr(info,raw)
    payload=buffer.getvalue()
    if source.read_bytes()!=original:raise ValueError('Original source changed during materialization')
    reused=False
    if output.exists():
        if output.read_bytes()!=payload:raise ValueError('Existing output differs;choose a new working-copy path')
        reused=True
    else:
        output.parent.mkdir(parents=True,exist_ok=True)
        with output.open('xb') as stream:stream.write(payload)
    return {'ok':True,'schema_version':1,'coordinate_unit':'EMU','canvas_emu':canvas,'source':str(source),'source_sha256':_sha(original),'source_bytes':len(original),'source_actual_slide_count':0,'output':str(output),'output_sha256':_sha(payload),'output_bytes':len(payload),'reused_identical_output':reused,'normalized_from_template_main':normalized,'layout_count':len(selected),'slide_count':len(pages),'placeholder_mode':placeholders,'pages':pages,'original_members_retained':True,'protected_parts_byte_identical':True,'protected_parts':[{'part':n,'sha256':_sha(before[n])} for n in protected],'changed_original_parts':[n for n in before if before[n]!=after[n]],'added_parts':list(new_parts),'dangling_internal_relationships':0,'font_substitution_performed':False,'new_media_created':False,'cloud_import_performed':False,'visual_review_required':True}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-pptx',required=True);parser.add_argument('--output-pptx',required=True)
    parser.add_argument('--layout',action='append');parser.add_argument('--placeholders',choices=['markers','empty'],default='markers')
    parser.add_argument('--report')
    args=parser.parse_args(argv)
    try:
        if args.report:
            report_path=Path(args.report).resolve()
            if report_path in (Path(args.source_pptx).resolve(),Path(args.output_pptx).resolve()) or report_path.exists():raise ValueError('Report must be a new,separate file')
        result=materialize_layouts(args.source_pptx,args.output_pptx,layouts=args.layout,placeholders=args.placeholders)
        if args.report:
            report_path.parent.mkdir(parents=True,exist_ok=True)
            with report_path.open('x',encoding='utf-8') as stream:json.dump(result,stream,ensure_ascii=False,indent=2)
    except (ValueError,OSError,KeyError,zipfile.BadZipFile,expat.ExpatError) as exc:
        print(json.dumps({'ok':False,'error':str(exc)},ensure_ascii=False));return 2
    print(json.dumps(result,ensure_ascii=False));return 0

if __name__=='__main__':sys.exit(main())
