"""Source migration copies factual objects; styling never re-authors their values."""
import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest
from lxml import etree as ET

SCRIPT = Path(__file__).parents[1] / 'template' / 'template_migration.py'
NS = 'https://www.larkoffice.com/sml/2.0'


def api():
    assert SCRIPT.exists(), 'the source-content migration authoring operation is missing'
    spec = importlib.util.spec_from_file_location('migration_under_test', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def inputs(tmp_path, note=''):
    actions = [
        ('Be head of household', 'Bahrain; Benin; Burundi (30)'),
        ('Choose where to live', 'Afghanistan; Bahrain; Benin (30)'),
        ('Apply for a passport', 'Afghanistan; Algeria; Bahrain (32)'),
        ('Confer citizenship on children', 'Bahamas; Bahrain (22)'),
        ('Get a job without permission', 'Bahrain; Bolivia (18)'),
        ('Obtain a national identity card', 'Afghanistan; Algeria (10)'),
        ('Travel outside the home', 'Afghanistan; Bahrain (17)'),
        ('Travel outside the country', 'Iran; Iraq (6)'),
        ('Open a bank account', 'Congo; Niger (2)'),
        ('Register a business', 'Bhutan; Congo; Pakistan; Suriname (4)'),
        ('Sign a contract', 'Congo; Equatorial Guinea (2)'),
    ]
    rows = ''.join('<tr height="20"><td><content><p>'+a+'</p></content></td>'
                   '<td><content><p>'+b+'</p></content></td></tr>' for a, b in actions)
    source = tmp_path / 'source.xml'
    source.write_text(f'''<slide xmlns="{NS}" id="source-slide"><data>
      <shape id="title" type="text" topLeftX="20" topLeftY="20" width="700" height="50">
        <content fontFamily="Arial" fontSize="36" color="#123456"><p><span bold="true">Parental leave</span></p></content>
      </shape>
      <shape id="body" type="text" topLeftX="20" topLeftY="85" width="700" height="55">
        <content fontSize="18"><p><span fontFamily="Arial">While 167 out of 173 economies mandate maternity leave, </span><span fontFamily="Source Han Sans">only 53 provide parental leave.</span></p></content>
      </shape>
      <table id="countries" topLeftX="20" topLeftY="160" width="700" height="240">{rows}</table>
      <chart id="plot" topLeftX="20" topLeftY="420" width="350" height="160">
        <chartPlotArea><chartPlot type="column"/><chartAxes><chartAxis type="y"><chartLabel format="0%"/></chartAxis></chartAxes></chartPlotArea>
        <chartData><dim1><chartField name="Category">Parental,Maternity</chartField></dim1><dim2><chartField name="Economies">53,167</chartField></dim2></chartData>
      </chart>
      <img id="photo" src="source-media" rotate="270" topLeftX="460" topLeftY="410" width="180" height="100"><crop leftOffset="0" rightOffset="0" topOffset="0" bottomOffset="0"/></img>
    </data><note><content><p>{note}</p></content></note></slide>''')
    frame = tmp_path / 'frame.xml'
    frame.write_text(f'''<slide xmlns="{NS}" id="target-slide"><style><fill><fillColor color="#fff"/></fill></style><data>
      <shape id="background" type="rect" topLeftX="0" topLeftY="0" width="960" height="540"><fill><fillColor color="#fff"/></fill></shape>
      <shape id="example-title" type="text" width="800" height="60"><content><p>IOWA example annual results 2020</p></content></shape>
    </data><note><content><p>Target template speaker notes</p></content></note></slide>''')
    return source, frame


def composed(tmp_path, **kwargs):
    source, frame = inputs(tmp_path)
    result = api().compose_migration(source, frame,
        content_ids=['title', 'body', 'countries', 'plot', 'photo'],
        frame_ids=['background'], target_region=[40, 100, 880, 390], **kwargs)
    return source, frame, result


def test_inventory_records_all_factual_members_and_original_empty_note(tmp_path):
    source, _ = inputs(tmp_path)
    result = api().source_content(source)
    assert result['member_ids'] == ['title', 'body', 'countries', 'plot', 'photo']
    assert result['note']['value'] == ''
    assert result['source_sha256'] == hashlib.sha256(source.read_bytes()).hexdigest()


def test_composition_reuses_complete_country_table_chart_rich_runs_and_empty_note(tmp_path):
    source, frame, result = composed(tmp_path)
    root = ET.fromstring(result['xml'].encode())
    assert root.get('id') is None
    assert len(root.findall('{*}data/{*}table/{*}tr')) == 11
    text = ' '.join(root.itertext())
    assert 'Bahrain; Benin; Burundi (30)' in text
    assert '167 out of 173' in text and 'only 53' in text
    assert '53,167' in text
    assert 'IOWA example' not in text and 'Target template speaker' not in text
    assert len(root.findall('{*}data/{*}shape[@id="body"]/{*}content/{*}p/{*}span')) == 2
    assert root.find('{*}data/{*}img').get('rotate') == '270'
    assert api().validate_migration(result['xml'], result['contract'])['ok']
    assert hashlib.sha256(source.read_bytes()).hexdigest() == result['contract']['source']['sha256']
    assert frame.read_text().find('IOWA example') >= 0


def test_replacing_eleven_original_rows_with_twelve_different_rows_is_detected(tmp_path):
    _, _, result = composed(tmp_path)
    root = ET.fromstring(result['xml'].encode())
    table = root.find('{*}data/{*}table')
    for row in list(table):
        table.remove(row)
    for i in range(12):
        row = ET.SubElement(table, f'{{{NS}}}tr')
        cell = ET.SubElement(row, f'{{{NS}}}td')
        ET.SubElement(cell, f'{{{NS}}}content').text = 'Different country '+str(i)
    verdict = api().validate_migration(ET.tostring(root), result['contract'])
    assert not verdict['ok']
    assert any(e.get('member_id') == 'countries' for e in verdict['errors'])


@pytest.mark.parametrize('change', ['number', 'chart', 'unit', 'note', 'media', 'rotation'])
def test_fact_data_note_and_informational_image_mutations_are_detected(tmp_path, change):
    _, _, result = composed(tmp_path)
    xml = result['xml']
    if change == 'number': xml = xml.replace('167 out of 173', '168 out of 173')
    elif change == 'chart': xml = xml.replace('53,167', '54,167')
    elif change == 'unit': xml = xml.replace('format="0%"', 'format="0"')
    elif change == 'note':
        root = ET.fromstring(xml.encode()); root.find('{*}note').append(ET.fromstring(f'<content xmlns="{NS}"><p>New speaker script</p></content>')); xml = ET.tostring(root)
    elif change == 'media': xml = xml.replace('source-media', 'different-media')
    else: xml = xml.replace('rotate="270"', 'rotate="0"')
    assert not api().validate_migration(xml, result['contract'])['ok']


def test_visual_restyling_and_explicit_id_media_rebinding_keep_facts_valid(tmp_path):
    _, _, result = composed(tmp_path,
        role_styles={'title': {'fontFamily': 'Noto Serif SC', 'fontSize': 32, 'color': '#AA5500'}},
        bindings={'ids': {'title': 'new-title'}, 'media': {'source-media': 'uploaded-same-image'}})
    root = ET.fromstring(result['xml'].encode())
    title = root.find('{*}data/{*}shape[@id="new-title"]')
    title.set('topLeftX', '70'); title.set('width', '820')
    for span in title.findall('.//{*}span'): span.set('color', '#333333')
    assert api().validate_migration(ET.tostring(root), result['contract'])['ok']
    assert root.find('{*}data/{*}img').get('src') == 'uploaded-same-image'


def test_selected_target_text_and_omitted_source_facts_are_not_composed(tmp_path):
    source, frame = inputs(tmp_path)
    with pytest.raises(ValueError, match='frame.*text|text.*frame'):
        api().compose_migration(source, frame, frame_ids=['example-title'], target_region=[40, 100, 880, 390])
    with pytest.raises(ValueError, match='factual|content'):
        api().compose_migration(source, frame, content_ids=['title'], frame_ids=['background'], target_region=[40, 100, 880, 390])


def test_additional_template_words_and_changed_source_file_fail_validation(tmp_path):
    source, _, result = composed(tmp_path)
    root = ET.fromstring(result['xml'].encode())
    extra = ET.fromstring(f'<shape xmlns="{NS}" id="extra" type="text"><content><p>New target institution</p></content></shape>')
    root.find('{*}data').append(extra)
    assert not api().validate_migration(ET.tostring(root), result['contract'])['ok']
    source.write_text(source.read_text().replace('167 out of 173', '999 out of 173'))
    assert not api().validate_migration(result['xml'], result['contract'])['ok']


def test_source_line_extending_past_boxes_still_fits_the_target_region(tmp_path):
    source, frame = inputs(tmp_path)
    root = ET.fromstring(source.read_bytes())
    root.find('{*}data').append(ET.fromstring(
        f'<line xmlns="{NS}" id="outside-line" x1="-50" y1="200" x2="20" y2="200"/>'))
    source.write_bytes(ET.tostring(root))
    result = api().compose_migration(source, frame, frame_ids=['background'],
                                     target_region=[40, 100, 880, 390])
    line = ET.fromstring(result['xml'].encode()).find('{*}data/{*}line')
    assert float(line.get('x1')) == pytest.approx(40)
    assert api().validate_migration(result['xml'], result['contract'])['ok']


def test_informational_image_fill_is_not_lost_from_the_fact_contract(tmp_path):
    source, frame = inputs(tmp_path)
    root = ET.fromstring(source.read_bytes())
    root.find('{*}data').append(ET.fromstring(
        f'<shape xmlns="{NS}" id="image-fill" type="rect" topLeftX="10" topLeftY="10" width="100" height="50"><fill><fillImg src="informational-image"/></fill></shape>'))
    source.write_bytes(ET.tostring(root))
    result = api().compose_migration(source, frame, frame_ids=['background'],
                                     target_region=[40, 100, 880, 390])
    changed = result['xml'].replace('informational-image', 'other-image')
    assert not api().validate_migration(changed, result['contract'])['ok']


def test_separate_placements_keep_rotated_image_aspect_and_visible_bounds(tmp_path):
    _, _, result = composed(tmp_path, placements=[
        {'ids':['title','body','countries','plot'], 'target_region':[40,100,800,330]},
        {'ids':['photo'], 'target_region':[850,420,60,100]},
    ])
    root = ET.fromstring(result['xml'].encode()); image = root.find('{*}data/{*}img')
    w,h,x,y = (float(image.get(k)) for k in ['width','height','topLeftX','topLeftY'])
    assert w/h == pytest.approx(1.8)
    assert image.get('rotate') == '270'
    assert x+w/2-h/2 >= 850-1e-6 and y+h/2-w/2 >= 420-1e-6
    assert x+w/2+h/2 <= 910+1e-6 and y+h/2+w/2 <= 520+1e-6
    image.set('width', str(w*2))
    assert not api().validate_migration(ET.tostring(root), result['contract'])['ok']


def test_cli_composes_and_validates_new_files_without_touching_inputs(tmp_path):
    source, frame = inputs(tmp_path); before = (source.read_bytes(), frame.read_bytes())
    xml, contract = tmp_path/'out.xml', tmp_path/'contract.json'
    result = subprocess.run([sys.executable,str(SCRIPT),'compose','--source',str(source),
        '--frame',str(frame),'--frame-ids','background','--target-region','40','100','880','390',
        '--output',str(xml),'--contract-out',str(contract)],capture_output=True,text=True)
    assert result.returncode == 0, result.stderr
    checked = subprocess.run([sys.executable,str(SCRIPT),'validate','--xml',str(xml),
                              '--contract',str(contract)],capture_output=True,text=True)
    assert checked.returncode == 0 and json.loads(checked.stdout)['ok']
    assert (source.read_bytes(),frame.read_bytes()) == before


@pytest.mark.parametrize('mode', ['xml-space', 'monospace', 'explicit-tab'])
def test_code_characters_and_indentation_survive_copy_and_cannot_be_collapsed(tmp_path, mode):
    source, frame = inputs(tmp_path)
    root = ET.fromstring(source.read_bytes()); content = root.find('{*}data/{*}shape[@id="body"]/{*}content')
    for old in list(content): content.remove(old)
    paragraph = ET.SubElement(content, f'{{{NS}}}p')
    if mode=='xml-space':
        paragraph.set('{http://www.w3.org/XML/1998/namespace}space','preserve')
        paragraph.text = "    print('a  b')"
    else:
        if mode=='monospace': content.set('fontFamily','Consolas')
        first = ET.SubElement(paragraph,f'{{{NS}}}span'); first.text = 'if ready:\n'
        if mode=='explicit-tab': ET.SubElement(paragraph,f'{{{NS}}}tab')
        second = ET.SubElement(paragraph,f'{{{NS}}}span'); second.text = "    print('a  b')"
    source.write_bytes(ET.tostring(root))
    result = api().compose_migration(source,frame,frame_ids=['background'],target_region=[40,100,880,390])
    copied = ET.fromstring(result['xml'].encode()).find('{*}data/{*}shape[@id="body"]/{*}content/{*}p')
    if mode=='xml-space': assert copied.text == "    print('a  b')"
    else:
        assert copied.text is None
        assert copied.findall('{*}span')[0].text == 'if ready:\n'
        assert copied.findall('{*}span')[1].text == "    print('a  b')"
    assert api().validate_migration(result['xml'],result['contract'])['ok']
    assert not api().validate_migration(result['xml'].replace('a  b','a b'),result['contract'])['ok']
    assert not api().validate_migration(result['xml'].replace("    print('a  b')","print('a  b')"),result['contract'])['ok']


def test_plain_prose_server_span_formatting_can_normalize_spaces(tmp_path):
    source,frame = inputs(tmp_path); root=ET.fromstring(source.read_bytes())
    paragraph=root.find('{*}data/{*}shape[@id="body"]/{*}content/{*}p')
    for old in list(paragraph): paragraph.remove(old)
    paragraph.text='Ordinary prose has  two spaces.'
    source.write_bytes(ET.tostring(root))
    result=api().compose_migration(source,frame,frame_ids=['background'],target_region=[40,100,880,390])
    assert api().validate_migration(result['xml'].replace('has  two','has two'),result['contract'])['ok']


def test_multiple_source_note_paragraphs_copy_and_cannot_be_merged(tmp_path):
    source,frame=inputs(tmp_path,note='First paragraph')
    root=ET.fromstring(source.read_bytes())
    ET.SubElement(root.find('{*}note/{*}content'),f'{{{NS}}}p').text='Second paragraph'
    source.write_bytes(ET.tostring(root))
    result=api().compose_migration(source,frame,frame_ids=['background'],target_region=[40,100,880,390])
    assert api().validate_migration(result['xml'],result['contract'])['ok']
    changed=ET.fromstring(result['xml'].encode()); note=changed.find('{*}note/{*}content')
    for p in list(note): note.remove(p)
    ET.SubElement(note,f'{{{NS}}}p').text='First paragraph Second paragraph'
    assert not api().validate_migration(ET.tostring(changed),result['contract'])['ok']


def test_legal_crop_anchor_and_ellipse_mask_validate_without_numeric_coercion(tmp_path):
    source,frame=inputs(tmp_path); root=ET.fromstring(source.read_bytes())
    crop=root.find('{*}data/{*}img/{*}crop'); crop.set('anchor','top'); crop.set('type','ellipse')
    source.write_bytes(ET.tostring(root))
    result=api().compose_migration(source,frame,frame_ids=['background'],target_region=[40,100,880,390])
    assert api().validate_migration(result['xml'],result['contract'])['ok']
    assert 'anchor="top"' in result['xml'] and 'type="ellipse"' in result['xml']


@pytest.mark.parametrize('change', ['carrier-rotation','carrier-aspect','fill-stretch','fill-crop'])
def test_informational_image_fill_display_transform_is_conserved(tmp_path, change):
    source,frame=inputs(tmp_path); root=ET.fromstring(source.read_bytes())
    root.find('{*}data').append(ET.fromstring(f'''<shape xmlns="{NS}" id="information-fill" type="rect" rotate="90" topLeftX="40" topLeftY="40" width="100" height="50"><fill><fillImg src="information-pixels" rotateWithShape="true" stretchLeft="0" stretchTop="-0.06"><crop anchor="top" type="rect" leftOffset="0"/></fillImg></fill></shape>'''))
    source.write_bytes(ET.tostring(root))
    result=api().compose_migration(source,frame,frame_ids=['background'],target_region=[40,100,880,390])
    assert api().validate_migration(result['xml'],result['contract'])['ok']
    actual=ET.fromstring(result['xml'].encode()); carrier=actual.find('{*}data/{*}shape[@id="information-fill"]')
    image=carrier.find('{*}fill/{*}fillImg')
    if change=='carrier-rotation': carrier.set('rotate','0')
    elif change=='carrier-aspect': carrier.set('width',str(float(carrier.get('width'))*2))
    elif change=='fill-stretch': image.set('stretchLeft','0.1')
    else: image.find('{*}crop').set('anchor','bottom')
    assert not api().validate_migration(ET.tostring(actual),result['contract'])['ok']


def test_ordinary_visual_solid_fill_can_change_without_retyping_facts(tmp_path):
    source,frame=inputs(tmp_path); root=ET.fromstring(source.read_bytes())
    body=root.find('{*}data/{*}shape[@id="body"]')
    body.append(ET.fromstring(f'<fill xmlns="{NS}"><fillColor color="#123456"/></fill>'))
    source.write_bytes(ET.tostring(root))
    result=api().compose_migration(source,frame,frame_ids=['background'],target_region=[40,100,880,390])
    changed=ET.fromstring(result['xml'].encode())
    changed.find('{*}data/{*}shape[@id="body"]/{*}fill/{*}fillColor').set('color','#FFFFFF')
    assert api().validate_migration(ET.tostring(changed),result['contract'])['ok']


def test_image_fill_xml_indentation_is_not_an_image_transform_change(tmp_path):
    source,frame=inputs(tmp_path); root=ET.fromstring(source.read_bytes())
    root.find('{*}data').append(ET.fromstring(f'<shape xmlns="{NS}" id="filled" type="rect" width="100" height="50"><fill><fillImg src="data-image" stretchLeft="0"><crop anchor="top" type="ellipse"/></fillImg></fill></shape>'))
    source.write_bytes(ET.tostring(root))
    result=api().compose_migration(source,frame,frame_ids=['background'],target_region=[40,100,880,390])
    actual=ET.fromstring(result['xml'].encode())
    actual.find('{*}data/{*}shape[@id="filled"]/{*}fill/{*}fillImg').text='\n  '
    assert api().validate_migration(ET.tostring(actual),result['contract'])['ok']


def test_role_styles_route_to_actual_schema_nodes_without_retyping_content(tmp_path):
    sys.path.insert(0,str(SCRIPT.parent))
    from scripts import xml_lint
    source=tmp_path/'source.xml';frame=tmp_path/'frame.xml'
    source.write_text(f'<slide xmlns="{NS}"><data><shape id="body" type="text" width="700" height="100"><content fontFamily="Arial" fontSize="18" color="rgb(0,0,0)"><p level="2" list="bullet"><span>Original body.</span></p></content></shape></data><note><content/></note></slide>')
    frame.write_text(f'<slide xmlns="{NS}"><style><fill><fillColor color="rgb(255,255,255)"/></fill></style><data/></slide>')
    result=api().compose_migration(source,frame,frame_ids=[],target_region=[40,100,800,300],role_styles={'body':{
        'fontFamily':'Arial','fontSize':20,'fontColor':'rgb(30,30,30)','bold':True,
        'textAlign':'left','lineSpacing':'multiple:1.2','verticalAlign':'top',
        'autoFit':'shape-auto-fit','textType':'body'}})
    import xml.etree.ElementTree as StdET
    issues=xml_lint.validate_sxsd_document(result['xml'],StdET.fromstring(result['xml']))
    assert not issues, issues
    root=ET.fromstring(result['xml'].encode());p=root.find('.//{*}p');span=p.find('{*}span');content=root.find('.//{*}content')
    assert p.get('level')=='2' and p.get('list')=='bullet'
    assert p.get('textAlign')=='left' and p.get('lineSpacing')=='multiple:1.2'
    assert p.get('fontFamily') is None and p.get('color') is None
    assert content.get('color')=='rgb(30,30,30)' and span.get('color')=='rgb(30,30,30)'
    assert content.get('bold')=='true' and span.get('bold')=='true'
    assert span.get('textAlign') is None and span.get('verticalAlign') is None
    assert api().validate_migration(result['xml'],result['contract'])['ok']


def test_wrap_indent_and_bullet_size_are_visual_but_list_level_is_factual(tmp_path):
    source,frame,result=composed(tmp_path)
    root=ET.fromstring(result['xml'].encode());content=root.find('{*}data/{*}shape[@id="body"]/{*}content');p=content.find('{*}p')
    content.set('wrap','true');p.set('indent','18');p.set('bulletSize','100%')
    assert api().validate_migration(ET.tostring(root),result['contract'])['ok']
    p.set('level','2')
    assert not api().validate_migration(ET.tostring(root),result['contract'])['ok']
