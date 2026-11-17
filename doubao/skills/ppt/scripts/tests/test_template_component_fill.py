"""Complete-fill contracts catch missed source fields and partial deliverables.

These fixtures are hand-authored. Expectations do not use the production
inventory/replacement helpers, and the CLI tests run real local operations.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

from lxml import etree as ET
import pytest


SCRIPT = Path(__file__).parents[1] / 'template' / 'template_reuse.py'
NS = {'s': 'https://www.larkoffice.com/sml/2.0'}
SOURCE = '''<slide xmlns="https://www.larkoffice.com/sml/2.0" id="source-page" width="960" height="540"><style><fill id="page-fill"><fillColor color="#FFFFFF"/></fill></style><data><shape id="a" type="text" topLeftX="40" topLeftY="120" width="250" height="180"><content textType="title" fontFamily="Calibri" fontSize="24" color="#112233"><p textAlign="left"><span fontFamily="Calibri" italic="true" color="#005A9C">Legacy Heading</span><span fontFamily="思源宋体" bold="true" color="#7700AA">旧标题</span></p></content></shape><shape id="b" type="text" topLeftX="350" topLeftY="120" width="250" height="180"><content textType="body" fontFamily="Roboto" fontSize="18"><p>Lorem ipsum</p><p indent="4"><span bold="true">Step 01</span> | <span fontSize="12" color="#555555">2023年</span></p></content></shape><shape id="c" type="text" topLeftX="660" topLeftY="120" width="250" height="180"><content textType="caption" fontFamily="Calibri" fontSize="14"><p>Launch</p></content></shape><line id="ab" startShapeId="a" endShapeId="b" color="#222222" width="2"/><line id="bc" startShapeId="b" endShapeId="c" color="#222222" width="2"/><shape id="unselected"><content><p>Other source text</p></content></shape></data></slide>'''
IDS = ['c', 'bc', 'a', 'ab', 'b']
EXPECTED_FIELDS = [
    ('a', 'content[1]/p[1]/span[1]#text', 'Legacy Heading'),
    ('a', 'content[1]/p[1]/span[2]#text', '旧标题'),
    ('b', 'content[1]/p[1]#text', 'Lorem ipsum'),
    ('b', 'content[1]/p[2]/span[1]#text', 'Step 01'),
    ('b', 'content[1]/p[2]/span[1]#tail', ' | '),
    ('b', 'content[1]/p[2]/span[2]#text', '2023年'),
    ('c', 'content[1]/p[1]#text', 'Launch'),
]
DECISIONS = {
    ('a', EXPECTED_FIELDS[0][1]): ('replace', 'New <Brief> & Notes'),
    ('a', EXPECTED_FIELDS[1][1]): ('replace', '本题方案'),
    ('b', EXPECTED_FIELDS[2][1]): ('replace', '新内容'),
    ('b', EXPECTED_FIELDS[3][1]): ('replace', '阶段A'),
    ('b', EXPECTED_FIELDS[4][1]): ('keep_label', None),
    ('b', EXPECTED_FIELDS[5][1]): ('remove', None),
    ('c', EXPECTED_FIELDS[6][1]): ('keep_label', None),
}


def module():
    spec = importlib.util.spec_from_file_location('component_fill_under_test', SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def prepare(m, source):
    # A missing operation produces an intentional assertion failure in RED,
    # rather than an import/collection error before behavior can be exercised.
    assert callable(getattr(m, 'prepare_component_fill', None)), 'complete component fill operation is missing'
    return m.prepare_component_fill(source, IDS)


def decide(plan):
    for field in plan['fields']:
        action, new_text = DECISIONS[(field['shape_id'], field['slot'])]
        field.update(action=action, new_text=new_text)
    return plan


@pytest.fixture
def source(tmp_path):
    path = tmp_path / 'source.xml'
    path.write_text(SOURCE, encoding='utf-8')
    return path


def test_prepare_exposes_every_rich_field_old_year_and_label_in_source_order(source):
    # Break caught: omitting a tail/year field, or returning caller ID order.
    m = module()
    original = source.read_bytes()
    plan = prepare(m, source)
    assert [(f['shape_id'], f['slot'], f['source_text']) for f in plan['fields']] == EXPECTED_FIELDS
    assert plan['member_ids'] == ['a', 'b', 'c', 'ab', 'bc']
    assert plan['source_id'] == 'source-page'
    assert plan['source_sha256'] == hashlib.sha256(original).hexdigest()
    assert all(f['action'] is None for f in plan['fields'])
    assert source.read_bytes() == original


def test_complete_fill_keeps_mixed_run_styles_geometry_and_connections(source):
    # Break caught: flattening rich runs, losing selected links, or skipping a
    # requested replacement/removal while reporting completion.
    m = module()
    original = source.read_bytes()
    plan = decide(prepare(m, source))
    result = m.fill_component(source, IDS, plan)
    assert result['ok'] is True
    root = ET.fromstring(result['xml'].encode('utf-8'))
    data = root.find('s:data', NS)
    assert [e.get('id') for e in data] == ['a', 'b', 'c', 'ab', 'bc']
    a, b, c = data[:3]
    assert a.attrib == {'id':'a', 'type':'text', 'topLeftX':'40', 'topLeftY':'120', 'width':'250', 'height':'180'}
    spans = a.findall('s:content/s:p/s:span', NS)
    assert [e.text for e in spans] == ['New <Brief> & Notes', '本题方案']
    assert spans[0].attrib == {'fontFamily':'Calibri', 'italic':'true', 'color':'#005A9C'}
    assert spans[1].attrib == {'fontFamily':'思源宋体', 'bold':'true', 'color':'#7700AA'}
    assert b.find('s:content/s:p', NS).text == '新内容'
    second = b.findall('s:content/s:p', NS)[1]
    assert second.attrib == {'indent':'4'}
    assert second[0].text == '阶段A' and second[0].tail == ' | '
    assert second[1].text in (None, '')
    assert second[1].attrib == {'fontSize':'12', 'color':'#555555'}
    assert c.find('s:content/s:p', NS).text == 'Launch'
    assert data[3].attrib == {'id':'ab', 'startShapeId':'a', 'endShapeId':'b', 'color':'#222222', 'width':'2'}
    assert data[4].get('startShapeId') == 'b' and data[4].get('endShapeId') == 'c'
    assert 'Legacy Heading' not in result['xml'] and 'Lorem ipsum' not in result['xml'] and '2023年' not in result['xml']
    assert result['completed_field_count'] == 7
    assert result['source_sha256'] == hashlib.sha256(original).hexdigest()
    assert source.read_bytes() == original


def test_omitted_old_year_field_never_returns_partially_filled_xml(source):
    # Break caught: accepting a partially specified plan as a deliverable.
    m = module()
    plan = decide(prepare(m, source))
    plan['fields'] = [f for f in plan['fields'] if (f['shape_id'], f['slot']) != ('b', EXPECTED_FIELDS[5][1])]
    result = m.fill_component(source, IDS, plan)
    assert result['ok'] is False and result['status'] == 'incomplete_plan'
    assert 'xml' not in result
    assert ('b', EXPECTED_FIELDS[5][1]) in [(f['shape_id'], f['slot']) for f in result['missing_fields']]
    assert source.read_text(encoding='utf-8') == SOURCE


def test_present_but_undecided_label_is_incomplete_instead_of_implicit_keep(source):
    # Break caught: silently keeping a source label just because its row exists.
    m = module()
    plan = decide(prepare(m, source))
    plan['fields'][-1]['action'] = None
    result = m.fill_component(source, IDS, plan)
    assert result['ok'] is False and result['status'] == 'incomplete_plan'
    assert 'xml' not in result
    assert any(f['shape_id'] == 'c' for f in result['missing_fields'])


def test_fill_rejects_plan_bound_to_different_source_bytes(source):
    # Break caught: applying an old field plan to a changed source component.
    m = module()
    plan = decide(prepare(m, source))
    plan['source_sha256'] = '0' * 64
    with pytest.raises(ValueError, match='[Ss]ource.*hash|sha256'):
        m.fill_component(source, IDS, plan)
    assert source.read_text(encoding='utf-8') == SOURCE


@pytest.mark.parametrize('attribute', ['shape_id', 'slot'])
def test_malformed_field_identity_is_a_clear_plan_error(source, attribute):
    # Break caught: malformed authored JSON escaping as an unhashable-key
    # traceback instead of the operation's ValueError contract.
    m = module()
    plan = decide(prepare(m, source))
    plan['fields'][0][attribute] = ['not-a-field-identity']
    with pytest.raises(ValueError, match='shape_id.*slot.*strings'):
        m.fill_component(source, IDS, plan)
    assert source.read_text(encoding='utf-8') == SOURCE


def test_cli_prepare_and_fill_write_complete_xml_and_origin_summary(source, tmp_path):
    # Break caught: registering CLI names without their real complete-fill
    # behavior or writing XML without the source-bound completion summary.
    plan_path = tmp_path / 'plan.json'
    prep = subprocess.run([sys.executable, str(SCRIPT), 'prepare-fill', '--source', str(source), '--ids', *IDS, '--output', str(plan_path)], capture_output=True, text=True)
    assert prep.returncode == 0, prep.stderr
    plan = decide(json.loads(plan_path.read_text()))
    plan_path.write_text(json.dumps(plan, ensure_ascii=False), encoding='utf-8')
    output = tmp_path / 'filled.xml'
    run = subprocess.run([sys.executable, str(SCRIPT), 'fill', '--source', str(source), '--ids', *IDS, '--plan', str(plan_path), '--output', str(output)], capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    assert ET.parse(str(output)).find('.//s:p', NS)[0].text == 'New <Brief> & Notes'
    summary = json.loads(output.with_suffix('.fill.json').read_text())
    assert summary['completed_field_count'] == 7
    assert summary['source_sha256'] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert summary['xml_sha256'] == hashlib.sha256(output.read_bytes()).hexdigest()
    assert source.read_text(encoding='utf-8') == SOURCE


def test_cli_incomplete_plan_writes_no_xml_or_partial_summary(source, tmp_path):
    # Break caught: returning a nonzero status only after a partial file exists.
    m = module()
    plan = decide(prepare(m, source));plan['fields'].pop()
    plan_path = tmp_path / 'incomplete.json';plan_path.write_text(json.dumps(plan))
    output = tmp_path / 'partial.xml'
    run = subprocess.run([sys.executable, str(SCRIPT), 'fill', '--source', str(source), '--ids', *IDS, '--plan', str(plan_path), '--output', str(output)], capture_output=True, text=True)
    assert run.returncode != 0
    assert not output.exists() and not output.with_suffix('.fill.json').exists()
    assert 'incomplete_plan' in run.stdout + run.stderr


TABLE_SOURCE = '''<slide xmlns="https://www.larkoffice.com/sml/2.0" id="table-page"><data><group id="g"><shape id="title" width="200" height="50"><content fontFamily="TitleFont"><p>Old title</p></content></shape><table id="t" width="600" height="200" topLeftX="40" topLeftY="100" fontFamily="SourceLatin" fontSize="16" color="#123456"><colgroup><col width="200"/><col width="400"/></colgroup><tr height="80" fontSize="20" bold="true"><td id="cell-a"><fill><fillColor color="#EEEEEE"/></fill><content><p textAlign="right"><span fontFamily="SourceLatin" color="#AA0000">Lorem ipsum</span> Old year 2023</p></content></td><td id="cell-b" fontFamily="SourceEA" bold="false"><content><p>旧列名</p></content></td></tr><tr height="120"><td id="cell-c"><content><p>Step 01</p></content></td><td id="cell-d"><content><p><span italic="true">Old Latin</span><span fontFamily="SourceEA" bold="true">旧中文</span></p></content></td></tr></table></group></data></slide>'''
TABLE_FIELDS = [
    ('title', 'content[1]/p[1]#text', 'Old title'),
    ('t', 'tr[1]/td[1]/content[1]/p[1]/span[1]#text', 'Lorem ipsum'),
    ('t', 'tr[1]/td[1]/content[1]/p[1]/span[1]#tail', ' Old year 2023'),
    ('t', 'tr[1]/td[2]/content[1]/p[1]#text', '旧列名'),
    ('t', 'tr[2]/td[1]/content[1]/p[1]#text', 'Step 01'),
    ('t', 'tr[2]/td[2]/content[1]/p[1]/span[1]#text', 'Old Latin'),
    ('t', 'tr[2]/td[2]/content[1]/p[1]/span[2]#text', '旧中文'),
]


def test_group_table_cells_and_tails_are_complete_source_fields(tmp_path):
    # Break caught: reporting complete while native table p/span/tail values
    # inside a selected group were never offered to the author.
    m = module();source = tmp_path / 'table-source.xml';source.write_text(TABLE_SOURCE)
    original = source.read_bytes();plan = m.prepare_component_fill(source, ['g'])
    assert [(f['shape_id'], f['slot'], f['source_text']) for f in plan['fields']] == TABLE_FIELDS
    assert plan['member_ids'] == ['g']
    latin = plan['fields'][1]['style'];tail = plan['fields'][2]['style'];cjk = plan['fields'][3]['style']
    assert latin['fontFamily'] == 'SourceLatin' and latin['fontSize'] == '20' and latin['bold'] == 'true'
    assert latin['color'] == '#AA0000' and tail['color'] == '#123456'
    assert cjk['fontFamily'] == 'SourceEA' and cjk['bold'] == 'false'
    for field, text in zip(plan['fields'], ['New title', '本题内容', '（2027）', '新列名', 'Step 01', 'New Latin', '新中文']):
        field.update(action='replace', new_text=text)
    result = m.fill_component(source, ['g'], plan)
    assert result['ok'] and result['completed_field_count'] == 7
    out = ET.fromstring(result['xml'].encode());table = out.find('.//s:table', NS)
    assert table.attrib == {'id':'t', 'width':'600', 'height':'200', 'topLeftX':'40', 'topLeftY':'100', 'fontFamily':'SourceLatin', 'fontSize':'16', 'color':'#123456'}
    assert [c.get('width') for c in table.find('s:colgroup', NS)] == ['200', '400']
    rows = table.findall('s:tr', NS);assert [r.get('height') for r in rows] == ['80', '120']
    first = rows[0][0].find('s:content/s:p/s:span', NS)
    assert first.text == '本题内容' and first.tail == '（2027）'
    assert first.attrib == {'fontFamily':'SourceLatin', 'color':'#AA0000'}
    assert rows[1][1].find('s:content/s:p/s:span', NS).get('italic') == 'true'
    assert 'Lorem ipsum' not in result['xml'] and 'Old year 2023' not in result['xml']
    assert source.read_bytes() == original


def test_omitted_table_year_tail_cannot_produce_partial_deliverable(tmp_path):
    # Break caught: checking only ordinary shapes for plan completeness.
    m = module();source = tmp_path / 'table-source.xml';source.write_text(TABLE_SOURCE)
    plan = m.prepare_component_fill(source, ['g'])
    for field in plan['fields']:field.update(action='replace', new_text='本题')
    year_slot = 'tr[1]/td[1]/content[1]/p[1]/span[1]#tail'
    plan['fields'] = [f for f in plan['fields'] if f['slot'] != year_slot]
    result = m.fill_component(source, ['g'], plan)
    assert result['ok'] is False and result['status'] == 'incomplete_plan'
    assert 'xml' not in result
    assert any(f['shape_id'] == 't' and f['slot'] == year_slot for f in result['missing_fields'])
    assert source.read_text() == TABLE_SOURCE


@pytest.mark.parametrize('member', [
    '<shape id="x"><p><span>Unaddressed label</span></p></shape>',
    '<group id="x"><caption><p>Unaddressed label</p></caption></group>',
])
def test_unaddressable_text_owner_is_not_reported_as_complete(tmp_path, member):
    # Break caught: silently skipping meaningful source text outside supported
    # shape-content/table-cell containers, then calling an empty plan complete.
    m = module();source = tmp_path / 'unsupported.xml'
    source.write_text('<slide><data>'+member+'</data></slide>')
    original = source.read_bytes()
    with pytest.raises(ValueError, match='Unsupported text owner'):
        m.prepare_component_fill(source, ['x'])
    assert source.read_bytes() == original
