"""A fixed source page cannot silently become a recomposed page."""
import importlib.util
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / 'template' / 'template_lint_all.py'

def api():
    spec = importlib.util.spec_from_file_location('fixed_lint',SCRIPT)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    assert hasattr(m,'check_fixed_template_geometry'), 'fixed-page source geometry check missing'
    return m

def files(tmp_path, source, authored):
    s=tmp_path/'source.xml';a=tmp_path/'authored.xml'
    s.write_text('<slide><data>'+source+'</data></slide>')
    a.write_text('<slide><data>'+authored+'</data></slide>')
    return s,a

TITLE='<shape id="title" type="rect" topLeftX="93.6" topLeftY="144" width="720" height="100.8"><content><p>Old title</p></content></shape>'

def test_fixed_cover_title_shift_and_width_drift_fail_with_source_values(tmp_path):
    s,a=files(tmp_path,TITLE,TITLE.replace('topLeftY="144"','topLeftY="168"').replace('width="720"','width="820"'))
    result=api().check_fixed_template_geometry(a,s,'fixed_template')
    assert result['fail_count']==1
    assert result['issues'][0]['element_id']=='title'
    assert result['issues'][0]['expected']['topLeftY']==144
    assert result['issues'][0]['actual']['width']==820

def test_fixed_ending_title_and_line_cannot_be_recentered_or_shortened(tmp_path):
    line='<shape id="line" type="line" topLeftX="64.8" topLeftY="288" width="756" height="3.6"/>'
    s,a=files(tmp_path,TITLE+line,TITLE+line.replace('width="756"','width="139.2"'))
    result=api().check_fixed_template_geometry(a,s,'fixed_template')
    assert result['fail_count']==1 and result['issues'][0]['element_id']=='line'

def test_replacing_text_and_chart_data_preserves_fixed_geometry(tmp_path):
    chart='<chart id="chart" topLeftX="64" topLeftY="200" width="756" height="220"><chartData><chartField>1,2</chartField></chartData></chart>'
    s,a=files(tmp_path,TITLE+chart,(TITLE+chart).replace('Old title','New title').replace('>1,2<','>3,4<'))
    assert api().check_fixed_template_geometry(a,s,'fixed_template')['fail_count']==0

def test_component_migration_can_move_the_whole_component(tmp_path):
    s,a=files(tmp_path,TITLE,TITLE.replace('width="720"','width="820"'))
    result=api().check_fixed_template_geometry(a,s,'component_reuse')
    assert not result['checked'] and result['fail_count']==0

def test_source_decorative_bleed_is_unchanged_fixed_geometry(tmp_path):
    ellipse='<shape id="ellipse" type="ellipse" topLeftX="-30.6" topLeftY="17.12" width="505.75" height="505.75"/>'
    s,a=files(tmp_path,ellipse,ellipse)
    assert api().check_fixed_template_geometry(a,s,'fixed_template')['fail_count']==0

def test_small_height_autofit_only_for_unchanged_text_keeps_whitelist(tmp_path):
    s,a=files(tmp_path,TITLE,TITLE.replace('height="100.8"','height="106.8"'))
    assert api().check_fixed_template_geometry(a,s,'fixed_template')['fail_count']==0
    a.write_text(a.read_text().replace('Old title','A new longer title'))
    assert api().check_fixed_template_geometry(a,s,'fixed_template')['fail_count']==1

def test_fixed_source_is_required_and_ids_cannot_all_be_discarded(tmp_path):
    s,a=files(tmp_path,TITLE,TITLE.replace('id="title"','id="new-title"'))
    assert api().check_fixed_template_geometry(a,None,'fixed_template')['fail_count']==1
    assert api().check_fixed_template_geometry(a,s,'fixed_template')['fail_count']==1

def test_declared_content_reflow_stays_inside_its_source_region_and_does_not_unlock_title(tmp_path):
    import hashlib,json
    nodes='<shape id="a" topLeftX="100" topLeftY="300" width="100" height="80"/><shape id="b" topLeftX="220" topLeftY="300" width="100" height="80"/>'
    s,a=files(tmp_path,TITLE+nodes,TITLE+nodes.replace('topLeftX="100"','topLeftX="110"'))
    decision=tmp_path/'reflow.json';decision.write_text(json.dumps({'source_sha256':hashlib.sha256(s.read_bytes()).hexdigest(),'groups':[{'member_ids':['a','b'],'reason':'Node capacity adjusted inside original content region'}]}))
    assert api().check_fixed_template_geometry(a,s,'fixed_template',decision)['fail_count']==0
    a.write_text(a.read_text().replace('topLeftY="144"','topLeftY="168"'))
    result=api().check_fixed_template_geometry(a,s,'fixed_template',decision)
    assert result['fail_count']==1 and result['issues'][0]['element_id']=='title'
    a.write_text(s.read_text().replace('topLeftX="100"','topLeftX="50"'))
    result=api().check_fixed_template_geometry(a,s,'fixed_template',decision)
    assert result['fail_count']==1 and result['issues'][0]['code']=='fixed_reflow_outside_source_region'

def test_malformed_reflow_is_a_reported_failure_not_an_exception(tmp_path):
    import hashlib,json
    s,a=files(tmp_path,TITLE,TITLE);p=tmp_path/'reflow.json'
    for definition in [None,{'source_sha256':hashlib.sha256(s.read_bytes()).hexdigest(),'groups':[None]}]:
        p.write_text(json.dumps(definition))
        assert api().check_fixed_template_geometry(a,s,'fixed_template',p)['fail_count']==1

def test_schema_autofit_small_height_for_new_text_keeps_frame(tmp_path):
    original=TITLE.replace('<content>','<content autoFit="shape-auto-fit">')
    s,a=files(tmp_path,original,original.replace('Old title','New title').replace('height="100.8"','height="106.8"'))
    assert api().check_fixed_template_geometry(a,s,'fixed_template')['fail_count']==0

def test_new_node_outside_declared_reflow_region_is_not_fixed(tmp_path):
    import hashlib,json
    nodes='<shape id="a" topLeftX="100" topLeftY="300" width="100" height="80"/><shape id="b" topLeftX="220" topLeftY="300" width="100" height="80"/>'
    new='<shape id="c" topLeftX="800" topLeftY="300" width="100" height="80"/>'
    s,a=files(tmp_path,TITLE+nodes,TITLE+nodes+new);p=tmp_path/'reflow.json'
    p.write_text(json.dumps({'source_sha256':hashlib.sha256(s.read_bytes()).hexdigest(),'groups':[{'member_ids':['a','b'],'reason':'Two nodes become three'}]}))
    result=api().check_fixed_template_geometry(a,s,'fixed_template',p)
    assert result['fail_count']==1 and result['issues'][0]['element_id']=='c'

def test_native_line_inside_reflow_region_is_allowed(tmp_path):
    import hashlib,json
    nodes='<shape id="a" topLeftX="100" topLeftY="300" width="100" height="80"/><shape id="b" topLeftX="220" topLeftY="300" width="100" height="80"/>'
    line='<line id="new-line" startX="150" startY="350" endX="270" endY="350" width="1"/>'
    s,a=files(tmp_path,TITLE+nodes,TITLE+nodes+line);p=tmp_path/'reflow.json'
    p.write_text(json.dumps({'source_sha256':hashlib.sha256(s.read_bytes()).hexdigest(),'groups':[{'member_ids':['a','b'],'reason':'Add a connection inside the source component'}]}))
    assert api().check_fixed_template_geometry(a,s,'fixed_template',p)['fail_count']==0


# Geometry and separate glyph IDs read from the R6 calligraphy source P8.
# The source plaque bxq is empty; its text lives in two horizontal single-glyph
# frames. Keep this fixture independent of the immutable evaluation directory.
CALLIGRAPHY = (
    '<shape id="bxq" type="rect" topLeftX="436.8" topLeftY="-1.5" width="86.4" height="210.3"><fill><fillColor color="rgba(192,0,0,1)"/></fill><content><p><span> </span></p></content></shape>'
    '<shape id="bxA" type="rect" topLeftX="452.0971653543307" topLeftY="37.62370078740158" width="67.80574803149607" height="60.58590551181102"><content autoFit="shape-auto-fit" wrap="false"><p><span fontSize="44">惊</span></p></content></shape>'
    '<shape id="bxb" type="rect" topLeftX="452.2233858267717" topLeftY="114.40944881889766" width="67.55330708661417" height="60.58590551181102"><content autoFit="shape-auto-fit" wrap="false"><p><span fontSize="44">雪</span></p></content></shape>'
)

def decision(tmp_path, source, *, groups=None, removed=None):
    definition={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest()}
    if groups is not None:definition['groups']=groups
    if removed is not None:
        source_nodes={n.get('id'):n for n in ET.parse(source).getroot().iter() if n.get('id')}
        definition['removed_slots']=[{
            'element_id':identifier,
            'source_member_sha256':hashlib.sha256(ET.tostring(source_nodes[identifier],encoding='utf-8')).hexdigest(),
            'reason':reason,
        } for identifier,reason in removed]
    p=tmp_path/'decision.json';p.write_text(json.dumps(definition));return p

def issue_codes(result):
    return {i['code'] for i in result['issues']}

def test_preserving_background_ids_does_not_hide_deleted_source_glyph_frames(tmp_path):
    root=ET.fromstring('<data>'+CALLIGRAPHY+'</data>')
    plaque=root[0];plaque.set('vert','ea-vert')
    content=plaque.find('content');content.clear()
    ET.SubElement(content,'p').text='隶';ET.SubElement(content,'p').text='书'
    s,a=files(tmp_path,CALLIGRAPHY,ET.tostring(plaque,encoding='unicode'))
    result=api().check_fixed_template_geometry(a,s,'fixed_template')
    missing={i['element_id'] for i in result['issues'] if i['code']=='fixed_source_member_missing'}
    assert missing=={'bxA','bxb'}
    assert 'fixed_source_text_structure_changed' in issue_codes(result)

def test_fixed_glyph_frames_replace_text_without_recomposing_the_plaque(tmp_path):
    s,a=files(tmp_path,CALLIGRAPHY,CALLIGRAPHY.replace('惊','隶').replace('雪','书'))
    assert api().check_fixed_template_geometry(a,s,'fixed_template')['fail_count']==0

def test_kept_id_cannot_hide_changed_text_direction_or_vertical_columns(tmp_path):
    original=TITLE.replace('<shape ','<shape vert="ea-vert" ')
    changed=original.replace('<p>Old title</p>','<p>新</p><p>题</p>')
    s,a=files(tmp_path,original,changed)
    assert 'fixed_source_text_structure_changed' in issue_codes(api().check_fixed_template_geometry(a,s,'fixed_template'))
    a.write_text(s.read_text().replace('vert="ea-vert"','vert="horz"'))
    assert 'fixed_source_text_structure_changed' in issue_codes(api().check_fixed_template_geometry(a,s,'fixed_template'))

def test_fixed_nowrap_slot_cannot_add_hard_breaks_but_flowing_body_can(tmp_path):
    original=TITLE.replace('<content>','<content wrap="false">')
    s,a=files(tmp_path,original,original.replace('<p>Old title</p>','<p>New<br/>title</p>'))
    assert 'fixed_source_text_structure_changed' in issue_codes(api().check_fixed_template_geometry(a,s,'fixed_template'))
    s,a=files(tmp_path,TITLE,TITLE.replace('<p>Old title</p>','<p>New paragraph</p><p>Another paragraph</p>'))
    assert api().check_fixed_template_geometry(a,s,'fixed_template')['fail_count']==0

def test_kept_element_id_cannot_change_native_element_type_or_clear_text(tmp_path):
    s,a=files(tmp_path,TITLE,TITLE.replace('shape','chart'))
    assert 'fixed_source_member_type_changed' in issue_codes(api().check_fixed_template_geometry(a,s,'fixed_template'))
    a.write_text(s.read_text().replace('Old title',''))
    assert 'fixed_source_text_structure_changed' in issue_codes(api().check_fixed_template_geometry(a,s,'fixed_template'))

def test_checked_unknown_example_slot_can_be_removed_or_cleared(tmp_path):
    contact=TITLE.replace('id="title"','id="contact"').replace('Old title','Template contact: Someone')
    s,a=files(tmp_path,TITLE+contact,TITLE)
    p=decision(tmp_path,s,removed=[('contact','No contact supplied; remove the source example contact slot')])
    result=api().check_fixed_template_geometry(a,s,'fixed_template',p)
    assert result['fail_count']==0
    assert result['removed_slots'][0]['element_id']=='contact'
    a.write_text(s.read_text().replace('Template contact: Someone',''))
    assert api().check_fixed_template_geometry(a,s,'fixed_template',p)['fail_count']==0
    definition=json.loads(p.read_text());definition['removed_slots'][0]['source_member_sha256']='wrong'
    p.write_text(json.dumps(definition))
    assert api().check_fixed_template_geometry(a,s,'fixed_template',p)['fail_count']==1

def test_removal_declaration_does_not_unlock_unknown_ids_or_still_used_slots(tmp_path):
    s,a=files(tmp_path,TITLE,TITLE)
    p=decision(tmp_path,s,removed=[('title','Remove unused source example')])
    assert api().check_fixed_template_geometry(a,s,'fixed_template',p)['fail_count']==1
    definition=json.loads(p.read_text());definition['removed_slots'][0]['element_id']='invented-id'
    p.write_text(json.dumps(definition))
    assert api().check_fixed_template_geometry(a,s,'fixed_template',p)['fail_count']==1

def test_reflow_does_not_silently_authorize_removing_source_members(tmp_path):
    nodes='<shape id="a" topLeftX="100" topLeftY="300" width="100" height="80"><content><p>One</p></content></shape><shape id="b" topLeftX="220" topLeftY="300" width="100" height="80"><content><p>Two</p></content></shape>'
    s,a=files(tmp_path,TITLE+nodes,TITLE+nodes[:nodes.index('<shape id="b"')])
    groups=[{'member_ids':['a','b'],'reason':'Two source items become one'}]
    p=decision(tmp_path,s,groups=groups)
    assert 'fixed_source_member_missing' in issue_codes(api().check_fixed_template_geometry(a,s,'fixed_template',p))
    p=decision(tmp_path,s,groups=groups,removed=[('b','Only one evidenced item; remove second complete source item')])
    assert api().check_fixed_template_geometry(a,s,'fixed_template',p)['fail_count']==0

def test_blank_decoration_cannot_be_declared_as_an_unknown_contact_slot(tmp_path):
    blank='<shape id="decoration" topLeftX="0" topLeftY="0" width="100" height="100"/>'
    s,a=files(tmp_path,TITLE+blank,TITLE)
    p=decision(tmp_path,s,removed=[('decoration','No contact supplied')])
    assert api().check_fixed_template_geometry(a,s,'fixed_template',p)['fail_count']==1

def test_new_members_need_a_declared_source_component_region_even_without_ids(tmp_path):
    for node in ['<shape id="new" topLeftX="10" topLeftY="10" width="20" height="20"/>','<shape topLeftX="10" topLeftY="10" width="20" height="20"/>']:
        s,a=files(tmp_path,TITLE,TITLE+node)
        assert 'fixed_source_member_added' in issue_codes(api().check_fixed_template_geometry(a,s,'fixed_template'))


def test_filling_empty_source_placeholder_is_normal_fixed_content_update(tmp_path):
    empty=TITLE.replace('Old title','')
    s,a=files(tmp_path,empty,empty.replace('<p></p>','<p><span>New content</span></p>'))
    assert api().check_fixed_template_geometry(a,s,'fixed_template')['fail_count']==0

def test_native_data_slot_can_be_explicitly_removed_without_fabricating_data(tmp_path):
    chart='<chart id="unused" topLeftX="10" topLeftY="20" width="100" height="100"><chartData><chartField>1,2</chartField></chartData></chart>'
    s,a=files(tmp_path,TITLE+chart,TITLE)
    p=decision(tmp_path,s,removed=[('unused','Source example has no corresponding supplied data')])
    assert api().check_fixed_template_geometry(a,s,'fixed_template',p)['fail_count']==0

def test_complete_item_removal_can_include_its_declared_blank_base(tmp_path):
    nodes='<shape id="a" topLeftX="100" topLeftY="300" width="100" height="80"><content><p>One item</p></content></shape><shape id="base" topLeftX="100" topLeftY="300" width="100" height="80"/>'
    s,a=files(tmp_path,TITLE+nodes,TITLE)
    p=decision(tmp_path,s,groups=[{'member_ids':['a','base'],'reason':'Remove complete unused source item'}],removed=[('a','Item has no corresponding fact'),('base','Remove its complete item base together')])
    assert api().check_fixed_template_geometry(a,s,'fixed_template',p)['fail_count']==0

def test_reflow_cannot_bypass_kept_source_text_direction(tmp_path):
    s,a=files(tmp_path,CALLIGRAPHY,CALLIGRAPHY.replace('id="bxA"','vert="ea-vert" id="bxA"'))
    p=decision(tmp_path,s,groups=[{'member_ids':['bxq','bxA','bxb'],'reason':'Capacity adapts inside the source component'}])
    assert 'fixed_source_text_structure_changed' in issue_codes(api().check_fixed_template_geometry(a,s,'fixed_template',p))

def test_source_member_without_id_is_unverifiable_instead_of_silently_ignored(tmp_path):
    s,a=files(tmp_path,TITLE+'<shape width="100" height="100" topLeftX="0" topLeftY="0"/>',TITLE)
    assert 'fixed_source_geometry_unverifiable' in issue_codes(api().check_fixed_template_geometry(a,s,'fixed_template'))

def test_fixed_checks_do_not_restrict_active_rebuild(tmp_path):
    s,a=files(tmp_path,TITLE,'<shape id="new"/>')
    result=api().check_fixed_template_geometry(a,s,'active_rebuild')
    assert not result['checked'] and result['fail_count']==0


def built_chart(values):
    # Exercise the production builder's real IDless output, using its established
    # inventory fixture rather than adding IDs to a simplified chart element.
    path=Path(__file__).with_name('test_template_chart_contract.py')
    spec=importlib.util.spec_from_file_location('native_chart_fixture',path)
    fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
    inventory=fixture.inventory();data={**fixture.DATA,'series':[{'name':'Current rate','values':values}]}
    return fixture.module().build_chart(inventory,'slide-01:element-10:r0',data,series_map=[0])['xml']

def test_production_idless_native_chart_updates_values_on_a_fixed_page(tmp_path):
    old,new=built_chart([10,20,30]),built_chart([30,20,10])
    assert ET.fromstring(old).get('id') is None
    assert ET.fromstring(new).get('id') is None
    s,a=files(tmp_path,old,new)
    result=api().check_fixed_template_geometry(a,s,'fixed_template')
    assert result['fail_count']==0

IDLESS_TABLE='<table topLeftX="80" topLeftY="140" width="520" height="52"><colgroup><col/></colgroup><tr><td><content><p>100</p></content></td></tr></table>'
IDLESS_LINE='<line startX="20" startY="210" endX="600" endY="210" type="line"/>'

def test_schema_native_idless_table_and_line_keep_identity_during_data_update(tmp_path):
    old=TITLE+IDLESS_TABLE+IDLESS_LINE
    s,a=files(tmp_path,old,old.replace('<p>100</p>','<p>125</p>'))
    assert api().check_fixed_template_geometry(a,s,'fixed_template')['fail_count']==0

def test_idless_native_member_deletion_and_geometry_drift_are_detected(tmp_path):
    for original in [built_chart([10,20,30]),IDLESS_TABLE,IDLESS_LINE]:
        s,a=files(tmp_path,TITLE+original,TITLE)
        result=api().check_fixed_template_geometry(a,s,'fixed_template')
        assert 'fixed_source_member_missing' in issue_codes(result)
        root=ET.fromstring(original)
        key='startX' if root.tag=='line' else 'topLeftX'
        root.set(key,str(float(root.get(key))+15))
        a.write_text('<slide><data>'+TITLE+ET.tostring(root,encoding='unicode')+'</data></slide>')
        assert api().check_fixed_template_geometry(a,s,'fixed_template')['fail_count']>0

def idless_removal(tmp_path,source,index,reason):
    charts=[n for d in ET.parse(source).getroot() if d.tag=='data' for n in d if n.tag=='chart']
    return tmp_path/'idless-removal.json',{
        'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'removed_slots':[{'element_id':f'chart_index:{index}',
            'source_member_sha256':hashlib.sha256(ET.tostring(charts[index],encoding='utf-8')).hexdigest(),
            'reason':reason}]}

def test_declared_idless_chart_deletion_does_not_rebind_the_following_chart(tmp_path):
    first=built_chart([10,20,30]);second=ET.fromstring(built_chart([1,2,3]));second.set('topLeftX','400')
    second=ET.tostring(second,encoding='unicode')
    s,a=files(tmp_path,TITLE+first+second,TITLE+second.replace('>1,2,3<','>3,2,1<'))
    p,definition=idless_removal(tmp_path,s,0,'No corresponding fact for the first example chart')
    p.write_text(json.dumps(definition))
    result=api().check_fixed_template_geometry(a,s,'fixed_template',p)
    assert result['fail_count']==0
    assert result['removed_slots'][0]['element_id']=='chart_index:0'
    # A declaration for the chart that is still at its source geometry must fail.
    p,definition=idless_removal(tmp_path,s,1,'Wrong source chart removed')
    p.write_text(json.dumps(definition))
    assert api().check_fixed_template_geometry(a,s,'fixed_template',p)['fail_count']>0

def test_ambiguous_idless_members_have_an_explicit_unverifiable_boundary(tmp_path):
    s,a=files(tmp_path,TITLE+IDLESS_TABLE+IDLESS_TABLE,TITLE+IDLESS_TABLE+IDLESS_TABLE)
    result=api().check_fixed_template_geometry(a,s,'fixed_template')
    assert 'fixed_source_geometry_unverifiable' in issue_codes(result)
    assert '无 ID' in result['issues'][0]['message']


def test_declared_idless_table_deletion_preserves_following_table_identity(tmp_path):
    second=IDLESS_TABLE.replace('topLeftY="140"','topLeftY="240"')
    s,a=files(tmp_path,TITLE+IDLESS_TABLE+second,TITLE+second.replace('>100<','>150<'))
    source_node=next(n for d in ET.parse(s).getroot() for n in d if n.tag=='table')
    p=tmp_path/'table-removal.json';p.write_text(json.dumps({
        'source_sha256':hashlib.sha256(s.read_bytes()).hexdigest(),
        'removed_slots':[{'element_id':'table_index:0',
            'source_member_sha256':hashlib.sha256(ET.tostring(source_node,encoding='utf-8')).hexdigest(),
            'reason':'First source example table has no corresponding supplied data'}]}))
    assert api().check_fixed_template_geometry(a,s,'fixed_template',p)['fail_count']==0

def test_idless_line_can_leave_only_with_its_declared_complete_item(tmp_path):
    s,a=files(tmp_path,TITLE+IDLESS_LINE,TITLE)
    source_line=next(n for d in ET.parse(s).getroot() for n in d if n.tag=='line')
    definition={'source_sha256':hashlib.sha256(s.read_bytes()).hexdigest(),
        'removed_slots':[{'element_id':'line_index:0',
            'source_member_sha256':hashlib.sha256(ET.tostring(source_line,encoding='utf-8')).hexdigest(),
            'reason':'Remove the unused source item connector'}]}
    p=tmp_path/'line-removal.json';p.write_text(json.dumps(definition))
    assert api().check_fixed_template_geometry(a,s,'fixed_template',p)['fail_count']==1
    definition['groups']=[{'member_ids':['title','line_index:0'],'reason':'Complete source item capacity changes in its original region'}]
    p.write_text(json.dumps(definition))
    assert api().check_fixed_template_geometry(a,s,'fixed_template',p)['fail_count']==0


def test_native_line_ordered_endpoints_cannot_change_despite_identical_bbox(tmp_path):
    for identifier in [' id="diagonal"','']:
        original=f'<line{identifier} startX="0" startY="0" endX="10" endY="10" type="line"/>'
        for changed in [original.replace('startY="0"','startY="10"').replace('endY="10"','endY="0"'),
                        original.replace('startX="0" startY="0" endX="10" endY="10"','startX="10" startY="10" endX="0" endY="0"')]:
            s,a=files(tmp_path,original,changed)
            result=api().check_fixed_template_geometry(a,s,'fixed_template')
            assert result['fail_count']==1
            issue=result['issues'][0]
            assert issue['code']=='fixed_source_line_endpoints_changed'
            assert issue['expected']['startY']==0
            assert issue['actual']['startY']==10

def test_declared_complete_reflow_group_can_rearrange_native_line_endpoints(tmp_path):
    line='<line id="diagonal" startX="100" startY="150" endX="200" endY="200" type="line"/>'
    s,a=files(tmp_path,TITLE+line,TITLE+line.replace('startY="150"','startY="200"').replace('endY="200"','endY="150"'))
    p=decision(tmp_path,s,groups=[{'member_ids':['title','diagonal'],'reason':'Complete source item reflow changes its connector inside the original region'}])
    assert api().check_fixed_template_geometry(a,s,'fixed_template',p)['fail_count']==0
