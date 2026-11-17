import hashlib
import importlib.util
import io
import os
from pathlib import Path
import posixpath
import re
import zipfile
from xml.dom.minidom import parseString
import pytest

HERE=Path(__file__).parent
ROOT=Path('__external_layout_fixtures__')
UND=Path(os.environ.get('PPT_LAYOUT_TEST_SOURCE',str(ROOT/'round3-materials/L3/inputs/L3_UND_complete_zero_slide_master.pptx')))
P='http://schemas.openxmlformats.org/presentationml/2006/main'
A='http://schemas.openxmlformats.org/drawingml/2006/main'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
REL='http://schemas.openxmlformats.org/package/2006/relationships'
CT='http://schemas.openxmlformats.org/package/2006/content-types'
SYSTEM={'dt','ftr','hdr','sldNum'}

def api():
    path=Path(os.environ.get('PPT_LAYOUT_MATERIALIZE_MODULE',str(HERE.parent/ 'template' / 'template_layout_materialize.py')))
    if not path.exists() and (HERE.parent/ 'template' / 'template_layout_materialize.py').exists():path=HERE.parent/ 'template' / 'template_layout_materialize.py'
    if not path.exists():
        raise AssertionError('Missing materialize_layouts operation: current zero-slide import input has no real source pages')
    spec=importlib.util.spec_from_file_location('candidate_layout_materialize',path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def parts(path):
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        return {n:z.read(n) for n in z.namelist()}

def slide_parts(pkg):
    return sorted(n for n in pkg if re.fullmatch(r'ppt/slides/slide\d+\.xml',n))

def layouts(pkg):
    return sorted((n for n in pkg if re.fullmatch(r'ppt/slideLayouts/slideLayout\d+\.xml',n)),key=lambda n:int(re.search(r'(\d+)\.xml$',n).group(1)))

def relationship_owner(name):
    if name=='_rels/.rels':return ''
    return posixpath.join(posixpath.dirname(posixpath.dirname(name)),posixpath.basename(name)[:-5])

def assert_relationships_resolve(pkg):
    for name,raw in pkg.items():
        if not name.endswith('.rels'):continue
        owner=relationship_owner(name);ids=set()
        for n in parseString(raw).getElementsByTagNameNS(REL,'Relationship'):
            assert n.getAttribute('Id') not in ids;ids.add(n.getAttribute('Id'))
            if n.getAttribute('TargetMode')=='External':continue
            target=n.getAttribute('Target')
            resolved=target.lstrip('/') if target.startswith('/') else posixpath.normpath(posixpath.join(posixpath.dirname(owner),target))
            assert resolved in pkg,(owner,resolved)

def masked_cSld(raw):
    tree=parseString(raw)
    for sp in tree.getElementsByTagNameNS(P,'sp'):
        ph=sp.getElementsByTagNameNS(P,'ph')
        if ph and ph[0].getAttribute('type') not in SYSTEM:
            for t in sp.getElementsByTagNameNS(A,'t'):
                for child in list(t.childNodes):t.removeChild(child)
    return tree.getElementsByTagNameNS(P,'cSld')[0].toxml()

@pytest.mark.skipif(not UND.is_file(), reason='Set PPT_LAYOUT_TEST_SOURCE and PPT_LAYOUT_ALPHA_TEST_SOURCE to public fixtures')
def test_real_und_zero_layouts_become_complete_registered_source_pages(tmp_path):
    before=parts(UND);assert not slide_parts(before)
    source_raw=UND.read_bytes();output=tmp_path/'materialized.pptx'
    result=api().materialize_layouts(UND,output)
    after=parts(output);assert len(slide_parts(after))==31
    assert result['layout_count']==31 and result['slide_count']==31
    assert set(before).issubset(after)
    allowed={'ppt/presentation.xml','ppt/_rels/presentation.xml.rels','[Content_Types].xml','docProps/app.xml'}
    assert {n for n in before if before[n]!=after[n]}<=allowed
    assert_relationships_resolve(after)
    assert UND.read_bytes()==source_raw
    assert result['source_sha256']==hashlib.sha256(source_raw).hexdigest()
    pres=parseString(after['ppt/presentation.xml'])
    assert len(pres.getElementsByTagNameNS(P,'sldId'))==31
    assert result['protected_parts_byte_identical']

@pytest.mark.skipif(not UND.is_file(), reason='Set PPT_LAYOUT_TEST_SOURCE and PPT_LAYOUT_ALPHA_TEST_SOURCE to public fixtures')
def test_selected_pages_keep_full_inherited_layout_and_real_slot_shapes(tmp_path):
    chosen=['ppt/slideLayouts/slideLayout3.xml','ppt/slideLayouts/slideLayout28.xml']
    output=tmp_path/'selected.pptx';result=api().materialize_layouts(UND,output,layouts=chosen)
    source=parts(UND);after=parts(output)
    assert len(result['pages'])==2
    for row,layout in zip(result['pages'],chosen):
        new=after[row['slide_part']]
        assert source[layout]==after[layout]
        orig=parseString(source[layout]);dst=parseString(new)
        assert len(orig.getElementsByTagNameNS(P,'ph'))==len(dst.getElementsByTagNameNS(P,'ph'))
        assert len(dst.getElementsByTagNameNS(P,'sp'))>0
        orig_slots={n.getElementsByTagNameNS(P,'cNvPr')[0].getAttribute('id'):n for n in orig.getElementsByTagNameNS(P,'sp') if n.getElementsByTagNameNS(P,'ph')}
        dst_slots={n.getElementsByTagNameNS(P,'cNvPr')[0].getAttribute('id'):n for n in dst.getElementsByTagNameNS(P,'sp')}
        assert set(orig_slots)==set(dst_slots)
        for sid,node in orig_slots.items():
            assert [n.toxml() for n in node.getElementsByTagNameNS(A,'xfrm')]==[n.toxml() for n in dst_slots[sid].getElementsByTagNameNS(A,'xfrm')]
        relname=posixpath.dirname(row['slide_part'])+'/_rels/'+posixpath.basename(row['slide_part'])+'.rels'
        rels=parseString(after[relname]).getElementsByTagNameNS(REL,'Relationship')
        links=[n for n in rels if n.getAttribute('Type').endswith('/slideLayout')]
        assert len(links)==1 and posixpath.normpath(posixpath.join('ppt/slides',links[0].getAttribute('Target')))==layout
    assert_relationships_resolve(after)

@pytest.mark.skipif(not UND.is_file(), reason='Set PPT_LAYOUT_TEST_SOURCE and PPT_LAYOUT_ALPHA_TEST_SOURCE to public fixtures')
def test_placeholders_have_short_markers_with_original_style_geometry_and_system_fields(tmp_path):
    output=tmp_path/'markers.pptx';result=api().materialize_layouts(UND,output,layouts=['ppt/slideLayouts/slideLayout9.xml'])
    before=parts(UND);after=parts(output);row=result['pages'][0]
    source=parseString(before[row['layout_part']]);dest=parseString(after[row['slide_part']])
    source_sp={n.getElementsByTagNameNS(P,'cNvPr')[0].getAttribute('id'):n for n in source.getElementsByTagNameNS(P,'sp') if n.getElementsByTagNameNS(P,'ph')}
    dest_sp={n.getElementsByTagNameNS(P,'cNvPr')[0].getAttribute('id'):n for n in dest.getElementsByTagNameNS(P,'sp')}
    assert set(source_sp)==set(dest_sp)
    for sid,node in source_sp.items():
        ph=node.getElementsByTagNameNS(P,'ph');new=dest_sp[sid]
        if not ph:assert node.toxml()==new.toxml();continue
        role=ph[0].getAttribute('type')
        if role in SYSTEM:assert node.toxml()==new.toxml()
        else:
            text=''.join(n.firstChild.data for n in new.getElementsByTagNameNS(A,'t') if n.firstChild)
            assert text.startswith('[') and len(text)<15
            assert [n.toxml() for n in node.getElementsByTagNameNS(A,'xfrm')]==[n.toxml() for n in new.getElementsByTagNameNS(A,'xfrm')]
            assert [n.toxml() for n in node.getElementsByTagNameNS(A,'rPr')]==[n.toxml() for n in new.getElementsByTagNameNS(A,'rPr')]
    assert result['pages'][0]['slots']

@pytest.mark.skipif(not UND.is_file(), reason='Set PPT_LAYOUT_TEST_SOURCE and PPT_LAYOUT_ALPHA_TEST_SOURCE to public fixtures')
def test_empty_mode_keeps_original_slot_objects(tmp_path):
    out=tmp_path/'empty.pptx';result=api().materialize_layouts(UND,out,layouts=['ppt/slideLayouts/slideLayout3.xml'],placeholders='empty')
    tree=parseString(parts(out)[result['pages'][0]['slide_part']])
    for sp in tree.getElementsByTagNameNS(P,'sp'):
        ph=sp.getElementsByTagNameNS(P,'ph')
        if ph and ph[0].getAttribute('type') not in SYSTEM:
            assert not any(t.firstChild and t.firstChild.data for t in sp.getElementsByTagNameNS(A,'t'))
    assert len(tree.getElementsByTagNameNS(P,'ph'))>0

@pytest.mark.skipif(not UND.is_file(), reason='Set PPT_LAYOUT_TEST_SOURCE and PPT_LAYOUT_ALPHA_TEST_SOURCE to public fixtures')
def test_potx_source_is_immutable_while_working_copy_is_standard_pptx(tmp_path):
    package=parts(UND);types=parseString(package['[Content_Types].xml'])
    for n in types.getElementsByTagNameNS(CT,'Override'):
        if n.getAttribute('PartName')=='/ppt/presentation.xml':n.setAttribute('ContentType','application/vnd.openxmlformats-officedocument.presentationml.template.main+xml')
    package['[Content_Types].xml']=types.toxml(encoding='utf-8');source=tmp_path/'source.potx'
    with zipfile.ZipFile(source,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for n,raw in package.items():z.writestr(n,raw)
    original=source.read_bytes();out=tmp_path/'from-potx.pptx';result=api().materialize_layouts(source,out,layouts=['ppt/slideLayouts/slideLayout1.xml'])
    after=parts(out);ct=parseString(after['[Content_Types].xml'])
    mime=[n.getAttribute('ContentType') for n in ct.getElementsByTagNameNS(CT,'Override') if n.getAttribute('PartName')=='/ppt/presentation.xml']
    assert mime==['application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml']
    assert source.read_bytes()==original and result['normalized_from_template_main']
    assert after['ppt/slideMasters/slideMaster1.xml']==package['ppt/slideMasters/slideMaster1.xml']

@pytest.mark.parametrize('selection',[[],['ppt/slideLayouts/missing.xml']])
@pytest.mark.skipif(not UND.is_file(), reason='Set PPT_LAYOUT_TEST_SOURCE and PPT_LAYOUT_ALPHA_TEST_SOURCE to public fixtures')
def test_invalid_layout_selection_does_not_emit_output(tmp_path,selection):
    out=tmp_path/'must-not-exist.pptx'
    with pytest.raises(ValueError):api().materialize_layouts(UND,out,layouts=selection)
    assert not out.exists()

@pytest.mark.skipif(not UND.is_file(), reason='Set PPT_LAYOUT_TEST_SOURCE and PPT_LAYOUT_ALPHA_TEST_SOURCE to public fixtures')
def test_source_alias_and_existing_different_output_are_not_overwritten(tmp_path):
    source=tmp_path/'source.pptx';source.write_bytes(UND.read_bytes());before=source.read_bytes()
    with pytest.raises(ValueError):api().materialize_layouts(source,source)
    alias=tmp_path/'hardlink.pptx';os.link(source,alias)
    with pytest.raises(ValueError):api().materialize_layouts(source,alias)
    assert source.read_bytes()==before
    output=tmp_path/'existing.pptx';output.write_bytes(b'existing-data')
    with pytest.raises(ValueError):api().materialize_layouts(source,output)
    assert output.read_bytes()==b'existing-data'

@pytest.mark.skipif(not UND.is_file(), reason='Set PPT_LAYOUT_TEST_SOURCE and PPT_LAYOUT_ALPHA_TEST_SOURCE to public fixtures')
def test_each_content_slot_has_a_unique_short_import_marker(tmp_path):
    result=api().materialize_layouts(UND,tmp_path/'unique-markers.pptx')
    slots=[s for p in result['pages'] for s in p['slots'] if s['marker']]
    assert len(slots)>1
    assert len({s['marker'] for s in slots})==len(slots)
    assert len({s['slot_id'] for s in slots})==len(slots)
    assert all(len(s['marker'])<15 for s in slots)
    assert all(s['shape_id'] is not None and s['placeholder_idx'] is not None for s in slots)

@pytest.mark.skipif(not UND.is_file(), reason='Set PPT_LAYOUT_TEST_SOURCE and PPT_LAYOUT_ALPHA_TEST_SOURCE to public fixtures')
def test_receipt_keeps_source_coordinate_unit_and_exact_placeholder_attributes(tmp_path):
    result=api().materialize_layouts(UND,tmp_path/'mapped.pptx',layouts=['ppt/slideLayouts/slideLayout1.xml'])
    assert result.get('coordinate_unit')=='EMU'
    assert result['canvas_emu']=={'cx':12192000,'cy':6858000}
    before=parseString(parts(UND)['ppt/slideLayouts/slideLayout1.xml'])
    phs={sp.getElementsByTagNameNS(P,'cNvPr')[0].getAttribute('id'):sp.getElementsByTagNameNS(P,'ph')[0] for sp in before.getElementsByTagNameNS(P,'sp') if sp.getElementsByTagNameNS(P,'ph')}
    for slot in result['pages'][0]['slots']:
        ph=phs[slot['shape_id']]
        attrs={ph.attributes.item(i).name:ph.attributes.item(i).value for i in range(ph.attributes.length)}
        assert slot['placeholder_attributes']==attrs
        assert slot['geometry_xml']


@pytest.mark.skipif(not UND.is_file(), reason='Set PPT_LAYOUT_TEST_SOURCE and PPT_LAYOUT_ALPHA_TEST_SOURCE to public fixtures')
def test_non_pptx_working_output_is_rejected_before_any_write(tmp_path):
    output=tmp_path/'wrong-kind.potx'
    with pytest.raises(ValueError):api().materialize_layouts(UND,output)
    assert not output.exists()


ALPHA_FIXTURE=Path(os.environ.get('PPT_LAYOUT_ALPHA_TEST_SOURCE',str(ROOT/'round4-candidate/independent-review-source/docs-review/layout-overdraw/zero-template.pptx')))

@pytest.mark.skipif(not ALPHA_FIXTURE.is_file(), reason='Set PPT_LAYOUT_TEST_SOURCE and PPT_LAYOUT_ALPHA_TEST_SOURCE to public fixtures')
def test_alpha_layout_decoration_is_inherited_once(tmp_path):
    """Regresses real Office evidence: 50% red became 75% red in v1."""
    source=parts(ALPHA_FIXTURE)
    result=api().materialize_layouts(ALPHA_FIXTURE,tmp_path/'alpha.pptx',layouts=['ppt/slideLayouts/slideLayout7.xml'])
    package=parts(tmp_path/'alpha.pptx');row=result['pages'][0]
    original=parseString(source[row['layout_part']])
    slide=parseString(package[row['slide_part']])
    assert any(n.getAttribute('name')=='Original alpha50 decoration' for n in original.getElementsByTagNameNS(P,'cNvPr'))
    assert not any(n.getAttribute('name')=='Original alpha50 decoration' for n in slide.getElementsByTagNameNS(P,'cNvPr')), 'Layout alpha decoration is drawn again on its inheriting slide'
    assert package[row['layout_part']]==source[row['layout_part']]
    assert package[row['master_part']]==source[row['master_part']]

@pytest.mark.skipif(not ALPHA_FIXTURE.is_file(), reason='Set PPT_LAYOUT_TEST_SOURCE and PPT_LAYOUT_ALPHA_TEST_SOURCE to public fixtures')
def test_grouped_placeholder_retains_transform_without_duplicate_sibling_art(tmp_path):
    source=parts(ALPHA_FIXTURE);layout='ppt/slideLayouts/slideLayout7.xml'
    doc=parseString(source[layout]);tree=doc.getElementsByTagNameNS(P,'spTree')[0]
    fixture=parseString(f'''<p:grpSp xmlns:p="{P}" xmlns:a="{A}">
      <p:nvGrpSpPr><p:cNvPr id="990" name="Grouped original slot"/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
      <p:grpSpPr><a:xfrm><a:off x="1828800" y="914400"/><a:ext cx="3657600" cy="1828800"/><a:chOff x="0" y="0"/><a:chExt cx="3657600" cy="1828800"/></a:xfrm></p:grpSpPr>
      <p:sp><p:nvSpPr><p:cNvPr id="991" name="Grouped alpha decoration"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="1828800" cy="1828800"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:solidFill><a:srgbClr val="FF0000"><a:alpha val="50000"/></a:srgbClr></a:solidFill><a:ln><a:noFill/></a:ln></p:spPr></p:sp>
      <p:sp><p:nvSpPr><p:cNvPr id="992" name="Grouped title slot"/><p:cNvSpPr/><p:nvPr><p:ph type="title" idx="12"/></p:nvPr></p:nvSpPr><p:spPr><a:xfrm><a:off x="1828800" y="0"/><a:ext cx="1828800" cy="1828800"/></a:xfrm></p:spPr><p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:r><a:rPr lang="en-US" sz="1200"/><a:t>Original group title</a:t></a:r></a:p></p:txBody></p:sp>
    </p:grpSp>''').documentElement
    tree.appendChild(doc.importNode(fixture,True));source[layout]=doc.toxml(encoding='utf-8')
    original=tmp_path/'group-zero.pptx'
    with zipfile.ZipFile(original,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for name,raw in source.items():z.writestr(name,raw)
    result=api().materialize_layouts(original,tmp_path/'group.pptx',layouts=[layout])
    package=parts(tmp_path/'group.pptx');slide=parseString(package[result['pages'][0]['slide_part']])
    names={n.getAttribute('name') for n in slide.getElementsByTagNameNS(P,'cNvPr')}
    assert 'Grouped alpha decoration' not in names, 'Grouped layout art is duplicated by the copied placeholder group'
    group=next(g for g in slide.getElementsByTagNameNS(P,'grpSp') if g.getElementsByTagNameNS(P,'cNvPr')[0].getAttribute('id')=='990')
    assert group.getElementsByTagNameNS(P,'grpSpPr')[0].toxml()==fixture.getElementsByTagNameNS(P,'grpSpPr')[0].toxml()
    ph=group.getElementsByTagNameNS(P,'ph');assert len(ph)==1 and ph[0].getAttribute('idx')=='12'
    text=''.join(t.firstChild.data for t in group.getElementsByTagNameNS(A,'t') if t.firstChild)
    assert re.fullmatch(r'\[T\d{2}_\d+\]',text)
    assert package[layout]==source[layout]

@pytest.mark.skipif(not ALPHA_FIXTURE.is_file(), reason='Set PPT_LAYOUT_TEST_SOURCE and PPT_LAYOUT_ALPHA_TEST_SOURCE to public fixtures')
def test_layout_background_stays_inherited_without_a_slide_override(tmp_path):
    package=parts(ALPHA_FIXTURE);layout='ppt/slideLayouts/slideLayout7.xml'
    doc=parseString(package[layout]);csld=doc.getElementsByTagNameNS(P,'cSld')[0]
    bg=parseString(f'<p:bg xmlns:p="{P}" xmlns:a="{A}"><p:bgPr><a:solidFill><a:srgbClr val="336699"><a:alpha val="50000"/></a:srgbClr></a:solidFill><a:effectLst/></p:bgPr></p:bg>').documentElement
    csld.insertBefore(doc.importNode(bg,True),csld.firstChild);package[layout]=doc.toxml(encoding='utf-8')
    source=tmp_path/'background-zero.pptx'
    with zipfile.ZipFile(source,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for name,raw in package.items():z.writestr(name,raw)
    result=api().materialize_layouts(source,tmp_path/'background.pptx',layouts=[layout])
    after=parts(tmp_path/'background.pptx');slide=parseString(after[result['pages'][0]['slide_part']])
    assert not slide.getElementsByTagNameNS(P,'bg'), 'Slide must inherit the original layout background instead of copying an override'
    assert after[layout]==package[layout]
