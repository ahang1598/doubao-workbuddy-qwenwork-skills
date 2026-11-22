import importlib.util
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location('template_reuse', Path(__file__).parents[1] / 'template' / 'template_reuse.py')

def module():
    assert Path(spec.origin).exists(), 'component extraction helper is missing'
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

XML = '''<slide xmlns="https://www.larkoffice.com/sml/2.0" id="page"><style><fill id="fill"><fillColor color="#fff"/></fill></style><data><shape id="decor" width="60" height="80" topLeftX="20" topLeftY="30"><fill><fillColor color="#f00"/></fill></shape><shape id="label" width="90" height="40"><content fontFamily="TemplateFont" fontSize="22" color="#123456"><p><span bold="true">Original</span><span fontSize="13">Body</span></p></content></shape><line id="edge" startShapeId="decor" endShapeId="label"/><img id="image" src="image-token" width="32" height="64"/><chart id="chart" type="bar"><chartField>1,2,3</chartField></chart></data><note>Old notes</note></slide>'''

def test_inventory_retains_text_style_and_data_objects(tmp_path):
    m=module(); f=tmp_path/'slide-01.xml'; f.write_text(XML)
    result=m.inventory(tmp_path)
    items={e['id']:e for e in result['slides'][0]['elements']}
    assert items['label']['text_runs'][0]['style']['fontFamily']=='TemplateFont'
    assert items['label']['text_runs'][0]['style']['fontSize']=='22'
    assert items['label']['text_runs'][1]['style']['fontSize']=='13'
    assert items['image']['attributes']['src']=='image-token'
    assert '1,2,3' in items['chart']['xml']
    assert items['decor']['attributes']['topLeftX']=='20'

def test_extract_preserves_complete_component_and_source(tmp_path):
    m=module();f=tmp_path/'s.xml';f.write_text(XML)
    out=m.extract(f,['decor','label','edge'])
    from lxml import etree
    root=etree.fromstring(out.encode())
    assert root.get('id') is None
    assert root.xpath('count(//*[local-name()="span"])')==2
    assert root.xpath('//*[local-name()="line"]')[0].get('endShapeId')=='label'
    assert root.xpath('count(//*[local-name()="style"])')==1
    assert not root.xpath('//*[local-name()="note"]')
    assert f.read_text()==XML

def test_extract_rejects_missing_member_and_orphan_connector(tmp_path):
    m=module(); f=tmp_path/'s.xml';f.write_text(XML)
    with pytest.raises(ValueError,match='missing'):m.extract(f,['absent'])
    with pytest.raises(ValueError,match='reference'):m.extract(f,['decor','edge'])

CIRCLE_XML='''<slide xmlns="https://www.larkoffice.com/sml/2.0"><data><shape id="circle" type="ellipse" topLeftX="-30" topLeftY="17" width="505" height="505"><border width="1" color="#595959"/></shape><shape id="red-a" type="ellipse" topLeftX="85" topLeftY="51" width="8" height="8"/><shape id="red-b" type="ellipse" topLeftX="471" topLeftY="265" width="8" height="8"/><shape id="label" type="text" topLeftX="100" topLeftY="200" width="100" height="40"><content fontFamily="TemplateFont" fontSize="22"><p>New label</p></content></shape></data></slide>'''

def test_component_transform_keeps_circle_and_red_nodes_in_one_affine_map(tmp_path):
    from lxml import etree
    m=module();assert hasattr(m,'transform_component'), 'atomic component transform missing'
    path=tmp_path/'source.xml';path.write_text(CIRCLE_XML)
    result=m.transform_component(path,['circle','red-a','red-b'],x=0,y=35,scale=.9)
    root=etree.fromstring(result['xml'].encode());items={n.get('id'):n for n in root.xpath('//*[local-name()="data"]/*')}
    assert float(items['circle'].get('topLeftX'))==0
    assert float(items['circle'].get('topLeftY'))==35
    assert float(items['circle'].get('width'))==pytest.approx(454.5)
    assert float(items['red-a'].get('topLeftX'))==pytest.approx(103.5)
    assert float(items['red-a'].get('topLeftY'))==pytest.approx(65.6)
    assert float(items['red-b'].get('topLeftX'))==pytest.approx(450.9)
    assert float(items['red-b'].get('topLeftY'))==pytest.approx(258.2)
    assert float(items['red-b'].get('width'))==pytest.approx(7.2)
    assert result['member_ids']==['circle','red-a','red-b']
    assert path.read_text()==CIRCLE_XML

def test_transform_preserves_typographic_ratios_tokens_and_values(tmp_path):
    from lxml import etree
    m=module();assert hasattr(m,'transform_component')
    path=tmp_path/'source.xml';path.write_text(XML.replace('<chart id="chart"','<chart width="100" height="80" topLeftX="30" topLeftY="10" id="chart"'))
    result=m.transform_component(path,['decor','label','edge','image','chart'],x=50,y=60,scale=2)
    root=etree.fromstring(result['xml'].encode())
    content=root.xpath('//*[local-name()="content"]')[0]
    assert content.get('fontFamily')=='TemplateFont' and float(content.get('fontSize'))==44
    assert root.xpath('//*[local-name()="img"]')[0].get('src')=='image-token'
    assert root.xpath('//*[local-name()="chartField"]')[0].text=='1,2,3'
    assert root.xpath('//*[local-name()="line"]')[0].get('endShapeId')=='label'

@pytest.mark.parametrize('scale',[0,-1,float('nan'),float('inf')])
def test_transform_rejects_invalid_scale_and_unknown_geometry(tmp_path,scale):
    m=module();assert hasattr(m,'transform_component')
    path=tmp_path/'source.xml';path.write_text(CIRCLE_XML)
    with pytest.raises(ValueError):m.transform_component(path,['circle','red-a','red-b'],scale=scale)

def test_transform_rejects_unsupported_host_instead_of_moving_only_some_members(tmp_path):
    m=module();assert hasattr(m,'transform_component')
    path=tmp_path/'source.xml';path.write_text('<slide><data><shape id="host" type="host" width="100" height="100"/></data></slide>')
    with pytest.raises(ValueError,match='unsupported'):m.transform_component(path,['host'],scale=2)

def test_transform_rejects_unimplemented_polyline_points_instead_of_half_transform(tmp_path):
    m=module();path=tmp_path/'source.xml'
    path.write_text('<slide><data><polyline id="path" width="100" height="100"><point x="30" y="40"/></polyline></data></slide>')
    with pytest.raises(ValueError,match='unsupported'):m.transform_component(path,['path'],x=50,scale=2)

def test_endpoint_line_scales_stroke_with_geometry(tmp_path):
    from lxml import etree
    m=module();p=tmp_path/'s.xml';p.write_text('<slide><data><line id="line" x1="10" y1="20" x2="100" y2="20" width="1" color="#000000"/></data></slide>')
    result=m.transform_component(p,['line'],scale=2)
    line=etree.fromstring(result['xml'].encode()).xpath('//*[local-name()="line"]')[0]
    assert float(line.get('x2'))==190 and float(line.get('width'))==2

@pytest.mark.parametrize('xml,ids',[('<slide><data><line id="line" startShapeId="ghost" endShapeId="ghost"/></data></slide>',['line']),('<slide><data><shape id="same"/><shape id="same"/></data></slide>',['same'])])
def test_extract_rejects_ghost_reference_and_duplicate_drawable_ids(tmp_path,xml,ids):
    m=module();p=tmp_path/'s.xml';p.write_text(xml)
    with pytest.raises(ValueError):m.extract(p,ids)

def test_native_endpoint_names_transform_and_scale_stroke(tmp_path):
    from lxml import etree
    m=module();p=tmp_path/'s.xml';p.write_text('<slide><data><line id="line" startX="10" startY="20" endX="100" endY="20" width="1"/></data></slide>')
    built=m.transform_component(p,['line'],x=30,y=40,scale=2)
    line=etree.fromstring(built['xml'].encode()).xpath('//*[local-name()="line"]')[0]
    assert [float(line.get(k)) for k in ['startX','startY','endX','endY','width']]==[30,40,210,40,2]

def tree_snapshot(node):
    # Independent stdlib comparison catches changed node order, geometry, style,
    # decorators, images, connectors and unaddressed text, including mixed tails.
    return (node.tag,dict(node.attrib),node.text,node.tail,
            [tree_snapshot(child) for child in node])

def test_r6_source8_replacement_keeps_two_independent_character_shapes(tmp_path):
    import hashlib
    from xml.etree import ElementTree as ET
    m=module();source=tmp_path/'slide-08.xml';source.write_text(R6_SOURCE8_XML,encoding='utf-8')
    original=source.read_bytes();ids=['bxd','bxf','bxn','bxb','bxA','bxq','bxw']
    result=m.replace_component_text(source,ids,{'bxb':'秋','bxA':'春'})
    expected=ET.fromstring(m.extract(source,ids));actual=ET.fromstring(result['xml'])
    ns={'s':'https://www.larkoffice.com/sml/2.0'}
    members={n.get('id'):n for n in expected.find('s:data',ns)}
    members['bxA'].find('s:content/s:p/s:span',ns).text='春'
    members['bxb'].find('s:content/s:p/s:span',ns).text='秋'
    assert tree_snapshot(actual)==tree_snapshot(expected)
    assert result['member_ids']==['bxw','bxq','bxA','bxb','bxn','bxf','bxd']
    actual_members={n.get('id'):n for n in actual.find('s:data',ns)}
    assert float(actual_members['bxA'].get('topLeftY'))<float(actual_members['bxb'].get('topLeftY'))
    assert source.read_bytes()==original
    assert result['source_sha256']==hashlib.sha256(original).hexdigest()

RICH_XML='''<slide><data><shape id="rich" vert="ea-vert" width="100" height="160"><content textType="body" fontFamily="SourceEA" fontSize="18" color="#234567"><p textAlign="right"><span id="cn" fontFamily="SourceEA" color="#ff0000">旧中文</span><span id="en" fontFamily="SourceLatin" italic="true">Old Latin</span>尾文</p><p indent="4"><span bold="true">第二段</span></p></content></shape><shape id="plain"><content fontSize="16"><p>Old</p></content></shape><shape id="empty"><content><p/></content></shape></data></slide>'''

def test_inventory_addresses_rich_runs_and_paragraphs_in_source_order(tmp_path):
    m=module();source=tmp_path/'slide-01.xml';source.write_text(RICH_XML)
    slots=m.inventory(tmp_path)['slides'][0]['elements'][0]['text_slots']
    assert [s['slot'] for s in slots]==['content[1]/p[1]/span[1]#text',
        'content[1]/p[1]/span[2]#text','content[1]/p[1]/span[2]#tail',
        'content[1]/p[2]/span[1]#text']
    assert [s['order'] for s in slots]==[1,2,3,4]
    assert all(s['shape_id']=='rich' and s['text_type']=='body' for s in slots)
    assert slots[0]['style']['fontFamily']=='SourceEA'
    assert slots[1]['style']['fontFamily']=='SourceLatin'
    assert slots[2]['style']['fontFamily']=='SourceEA'
    assert slots[3]['paragraph']['attributes']=={'indent':'4'}

def test_explicit_rich_slots_preserve_run_fonts_paragraphs_and_omitted_text(tmp_path):
    from xml.etree import ElementTree as ET
    m=module();source=tmp_path/'source.xml';source.write_text(RICH_XML)
    replacements={'rich':{'content[1]/p[1]/span[1]#text':'新中文',
                         'content[1]/p[1]/span[2]#text':'New Latin',
                         'content[1]/p[2]/span[1]#text':'下一段'}}
    result=m.replace_component_text(source,['rich','plain','empty'],replacements)
    expected=ET.fromstring(m.extract(source,['rich','plain','empty']))
    spans=expected.findall('./data/shape/content/p/span')
    spans[0].text='新中文';spans[1].text='New Latin';spans[2].text='下一段'
    assert tree_snapshot(ET.fromstring(result['xml']))==tree_snapshot(expected)
    assert source.read_text()==RICH_XML

def test_plain_and_empty_paragraphs_accept_string_without_rebuilding(tmp_path):
    from xml.etree import ElementTree as ET
    m=module();source=tmp_path/'s.xml';source.write_text(RICH_XML)
    result=m.replace_component_text(source,['plain','empty'],{'plain':'New & <value>','empty':'字'})
    actual=ET.fromstring(result['xml']);expected=ET.fromstring(m.extract(source,['plain','empty']))
    expected.findall('./data/shape/content/p')[0].text='New & <value>'
    expected.findall('./data/shape/content/p')[1].text='字'
    assert tree_snapshot(actual)==tree_snapshot(expected)

@pytest.mark.parametrize('text_map,match',[
    ({'rich':'Merged paragraphs'},'Ambiguous'),
    ({'rich':{'content[1]/p[3]#text':'Absent'}},'Unknown text slot'),
    ({'ghost':'Text'},'missing'),
    ({'plain':'Two\nlines'},'breaks'),
    ({'plain':{'content[1]/p[1]#text':12}},'string'),
    ({'plain':{}},'nonempty'),
])
def test_replacement_rejects_ambiguous_missing_or_structural_edits(tmp_path,text_map,match):
    m=module();source=tmp_path/'s.xml';source.write_text(RICH_XML)
    with pytest.raises(ValueError,match=match):m.replace_component_text(source,['rich','plain'],text_map)
    assert source.read_text()==RICH_XML

@pytest.mark.parametrize('content',['<p><field type="slidenum">1</field></p>',
    '<p><formula><latex>x</latex></formula></p>', '<ul><li><p>Item</p></li></ul>'])
def test_replace_refuses_unsupported_rich_objects_instead_of_flattening(tmp_path,content):
    m=module();source=tmp_path/'s.xml';xml='<slide><data><shape id="text"><content>'+content+'</content></shape></data></slide>'
    source.write_text(xml)
    with pytest.raises(ValueError,match='Unsupported rich text'):m.replace_component_text(source,['text'],{'text':'Plain'})
    assert source.read_text()==xml

def test_replace_cli_writes_text_and_provenance_without_touching_source(tmp_path):
    import hashlib,json,subprocess,sys
    from xml.etree import ElementTree as ET
    source=tmp_path/'s.xml';source.write_text(RICH_XML)
    mapping=tmp_path/'map.json';mapping.write_text(json.dumps({'plain':'New'}))
    output=tmp_path/'new.xml'
    command=[sys.executable,spec.origin,'replace','--source',str(source),'--ids','plain',
             '--text-map',str(mapping),'--output',str(output)]
    run=subprocess.run(command,capture_output=True,text=True)
    assert run.returncode==0,run.stderr
    assert ET.parse(output).find('./data/shape/content/p').text=='New'
    manifest=json.loads(output.with_suffix('.replace.json').read_text())
    assert manifest['member_ids']==['plain']
    assert manifest['xml_sha256']==hashlib.sha256(output.read_bytes()).hexdigest()
    assert manifest['text_replacements']==[{'shape_id':'plain','slot':'content[1]/p[1]#text','before':'Old','after':'New'}]
    assert source.read_text()==RICH_XML
    assert subprocess.run(command,capture_output=True,text=True).returncode!=0

# Read-only stdlib extraction of seven actual R6 L7 shufa/source-slides/slide-08.xml
# members, including both independent calligraphy characters and their ornaments.
# Source media references below are dummy fixture tokens, not live document resources.
R6_SOURCE8_XML = '''<slide xmlns="https://www.larkoffice.com/sml/2.0" id="peE"><style>
      <fill id="feE">
        <fillColor color="rgba(255, 255, 255, 1)" />
      </fill>
    </style>
    <data><img id="bxw" src="fixture-source-media-1" width="722.4000787401575" height="406.35" topLeftX="0" topLeftY="0">
        <crop leftOffset="0" rightOffset="0" topOffset="0" bottomOffset="0" />
      </img>
      <shape width="86.4" height="210.3" topLeftX="436.8" topLeftY="-1.5" type="rect" id="bxq">
        <fill>
          <fillColor color="rgba(192, 0, 0, 1)" />
        </fill>
        <content paddingTop="3.6" paddingBottom="3.6" paddingLeft="7.2" paddingRight="7.2" fontSize="16" fontFamily="思源黑体" color="rgba(31, 35, 41, 1)">
          <p textAlign="center" lineSpacing="multiple:1.2" defaultTabSize="72"><span color="rgba(255, 255, 255, 1)" fontSize="18" fontFamily="Calibri" bold="false" italic="false" strikethrough="false" underline="false"> </span></p>
        </content>
      </shape>
      <shape width="67.80574803149607" height="60.58590551181102" topLeftX="452.0971653543307" topLeftY="37.62370078740158" type="rect" id="bxA">
        <content verticalAlign="top" paddingTop="3.6" paddingBottom="3.6" paddingLeft="7.2" paddingRight="7.2" fontSize="16" fontFamily="思源黑体" color="rgba(31, 35, 41, 1)" autoFit="shape-auto-fit" wrap="false">
          <p textAlign="center" lineSpacing="multiple:1.2" defaultTabSize="72"><span color="rgba(255, 255, 255, 1)" fontSize="44" fontFamily="叶根友刀锋黑草" bold="false" italic="false" strikethrough="false" underline="false">惊 </span></p>
        </content>
      </shape>
      <shape width="67.55330708661417" height="60.58590551181102" topLeftX="452.2233858267717" topLeftY="114.40944881889766" type="rect" id="bxb">
        <content verticalAlign="top" paddingTop="3.6" paddingBottom="3.6" paddingLeft="7.2" paddingRight="7.2" fontSize="16" fontFamily="思源黑体" color="rgba(31, 35, 41, 1)" autoFit="shape-auto-fit" wrap="false">
          <p textAlign="center" lineSpacing="multiple:1.2" defaultTabSize="72"><span color="rgba(255, 255, 255, 1)" fontSize="44" fontFamily="叶根友刀锋黑草" bold="false" italic="false" strikethrough="false" underline="false">雪 </span></p>
        </content>
      </shape>
      <shape width="6.857165354330709" height="6.857165354330709" topLeftX="477.17141732283466" topLeftY="102.88094488188976" type="ellipse" id="bxn">
        <fill>
          <fillColor color="rgba(255, 255, 255, 1)" />
        </fill>
        <content paddingTop="3.6" paddingBottom="3.6" paddingLeft="7.2" paddingRight="7.2" fontSize="16" fontFamily="思源黑体" color="rgba(31, 35, 41, 1)">
          <p textAlign="center" lineSpacing="multiple:1.2" defaultTabSize="72"><span color="rgba(255, 255, 255, 1)" fontSize="18" fontFamily="Calibri" bold="false" italic="false" strikethrough="false" underline="false"> </span></p>
        </content>
      </shape>
      <shape width="68.25" height="167.15" topLeftX="445.87503937007875" topLeftY="25" type="rect" id="bxf">
        <border color="rgba(255, 255, 255, 1)" width="1" lineJoin="miter" miterLimit="10" />
        <content paddingTop="3.6" paddingBottom="3.6" paddingLeft="7.2" paddingRight="7.2" fontSize="16" fontFamily="思源黑体" color="rgba(31, 35, 41, 1)">
          <p textAlign="center" lineSpacing="multiple:1.2" defaultTabSize="72"><span color="rgba(255, 255, 255, 1)" fontSize="18" fontFamily="Calibri" bold="false" italic="false" strikethrough="false" underline="false"> </span></p>
        </content>
      </shape>
      <line id="bxd" startX="631.5" startY="264" endX="960" endY="265" type="line">
        <border color="rgba(128, 128, 128, 1)" width="1" lineJoin="miter" miterLimit="10" />
        <startArrow type="solid-circle" widthScale="sm" heightScale="sm" />
        <endArrow widthScale="med" heightScale="med" />
      </line>
      </data></slide>'''
