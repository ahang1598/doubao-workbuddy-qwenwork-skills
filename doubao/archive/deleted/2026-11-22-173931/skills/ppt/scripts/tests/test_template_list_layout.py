"""Fixed numbering oracles from actual L7 P20 and native SML preview.

P20 excerpt provenance: QBhIsZiD4l9n1QdWqZqctOZTnyd / pwv, round 2.
li@index alone exported 1/1/1; p@autoStartAt exported 1/2/3 on the
independent diagnostic deck VH5gsmXVKlX99ldR69jc6dHhnVv / poo.
Counter and nested expectations below were read from native preview images,
not calculated with the helper under test. In the observed service, an explicit
p reset is item-local and clears that level's implicit continuation counter.
"""
import importlib.util
from pathlib import Path
import sys

from lxml import etree as ET
import pytest

SCRIPT = Path(__file__).parents[1] / 'template' / 'template_list_layout.py'
NS = 'https://www.larkoffice.com/sml/2.0'


def api():
    assert SCRIPT.exists(), 'explicit native paragraph numbering helper is missing'
    spec = importlib.util.spec_from_file_location('template_list_layout_under_test', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def slide(content, note=''):
    return f'<slide xmlns="{NS}"><data><shape id="body" type="text" topLeftX="40" topLeftY="40" width="800" height="400">{content}</shape></data><note>{note}</note></slide>'


def numbers(xml):
    return [int(p.get('autoStartAt')) for p in ET.fromstring(xml.encode()).findall('.//{*}data//{*}p') if p.get('autoStartAt') is not None]


def test_actual_l7_abc_list_emits_1_2_3_on_paragraphs_without_retyping(tmp_path):
    source = Path(__file__).with_name('fixtures') / 'L7_P20_actual_list.xml'
    raw = source.read_bytes()
    copy = tmp_path / 'author-copy.xml'; copy.write_bytes(raw)
    result = api().explicit_numbering(copy)
    assert numbers(result['xml']) == [1, 2, 3]
    assert [row['number'] for row in result['numbered_paragraphs']] == [1, 2, 3]
    actual = ET.fromstring(result['xml'].encode())
    assert [''.join(p.itertext()) for p in actual.findall('.//{*}ol/{*}li/{*}p')] == [
        '一种专门用于图像的激活函数',
        '一层预处理：在全连接层前归一化图像',
        '用小窗口在图像上滑动，提取局部模式的层',
    ]
    for para in actual.findall('.//{*}data//{*}p'):
        para.attrib.pop('autoStartAt', None)
    assert ET.tostring(actual) == ET.tostring(ET.fromstring(raw))
    assert copy.read_bytes() == raw and source.read_bytes() == raw


# Literal source/render pairs from counter-oracle.png; explicit p resets are
# intentionally not inferred from ordinary HTML's different continuation rule.
COUNTER_ORACLES = [
    ('implicit_ol', '<ol><li><p>A</p></li><li><p>B</p></li><li><p>C</p></li></ol><p list="number">after</p>', [7, 8, 9, 10]),
    ('isolated_ol_start', '<ol autoStartAt="4"><li><p>A</p></li><li><p>B</p></li><li><p>C</p></li></ol><p list="number">after</p>', [4, 5, 6, 7]),
    ('li_index_advances', '<ol><li><p>A</p></li><li index="10"><p>B</p></li><li><p>C</p></li></ol><p list="number">after</p>', [7, 10, 11, 12]),
    ('direct_p_local_reset', '<p list="number">A</p><p list="number" autoStartAt="20">B</p><p list="number">C</p><p list="number">after</p>', [7, 20, 7, 8]),
    ('p_reset_in_started_ol', '<ol autoStartAt="4"><li><p>A</p></li><li><p autoStartAt="20">B</p></li><li><p>C</p></li></ol><p list="number">after</p>', [4, 20, 4, 7]),
    ('p_reset_in_implicit_ol', '<ol><li><p>A</p></li><li><p autoStartAt="20">B</p></li><li><p>C</p></li></ol><p list="number">after</p>', [7, 20, 7, 8]),
]


@pytest.mark.parametrize('name,body,want', COUNTER_ORACLES, ids=[row[0] for row in COUNTER_ORACLES])
def test_content_ol_index_and_p_start_follow_native_rendered_counter(name, body, want):
    result = api().explicit_numbering(slide(f'<content autoStartAt="7">{body}</content>'))
    assert numbers(result['xml']) == want
    assert [row['number'] for row in result['numbered_paragraphs']] == want


def test_existing_li_index_survives_paragraph_override_and_group_restart():
    xml = slide('<content autoStartAt="7"><ol autoStartAt="4"><li><p>A</p></li><li index="9"><p autoStartAt="20">B</p></li><li><p>C</p></li></ol><p list="number">after</p><ol><li><p>D</p></li><li><p>E</p></li></ol></content>')
    result = api().explicit_numbering(xml)
    assert numbers(result['xml']) == [4, 20, 4, 7, 8, 9]
    assert ET.fromstring(result['xml'].encode()).find('.//{*}li[@index="9"]') is not None


def test_nested_levels_use_source_start_and_reset_deeper_levels_without_flattening():
    xml = slide('<content list="number" listStyle="hierarchical-number" autoStartAt="5"><p level="1">outer A</p><p level="2">inner A</p><p level="2">inner B</p><p level="1">outer B</p><p level="2">inner C</p><p level="3">deep C</p><p level="2">inner D</p></content>')
    result = api().explicit_numbering(xml)
    # Native baseline and explicit paragraph preview both displayed:
    # 5; 5.5; 5.6; 6; 6.5; 6.5.5; 6.6.
    assert numbers(result['xml']) == [5, 5, 6, 6, 5, 5, 6]
    root = ET.fromstring(result['xml'].encode())
    assert [p.get('level') for p in root.findall('.//{*}data//{*}p')] == ['1', '2', '2', '1', '2', '3', '2']
    assert root.find('.//{*}content').get('listStyle') == 'hierarchical-number'


def test_numbering_state_is_independent_per_content_and_notes_remain_original():
    xml = slide('<content list="number"><p>A</p><p>B</p></content><content list="number"><p>C</p><p>D</p></content>', '<content list="number"><p>Original numbered note</p></content>')
    result = api().explicit_numbering(xml)
    assert numbers(result['xml']) == [1, 2, 1, 2]
    assert ET.fromstring(result['xml'].encode()).find('.//{*}note//{*}p').get('autoStartAt') is None


def test_bullets_and_plain_paragraphs_do_not_gain_numbering_or_lose_symbols():
    xml = slide('<content list="bullet" bulletChar="✓"><p level="2">Bullet</p><p list="none">Plain</p><ol listStyle="alpha-uc-period"><li><p>Numbered</p></li></ol></content>')
    result = api().explicit_numbering(xml)
    assert numbers(result['xml']) == [1]
    assert ET.fromstring(result['xml'].encode()).find('.//{*}content').get('bulletChar') == '✓'


def test_explicit_numbering_is_idempotent_and_effective_schema_legal():
    xml = slide('<content autoStartAt="7"><ol><li><p>A</p></li><li index="10"><p>B</p></li><li><p>C</p></li></ol></content>')
    first = api().explicit_numbering(xml)
    second = api().explicit_numbering(first['xml'])
    assert first['xml'] == second['xml']
    sys.path.insert(0, str(SCRIPT.parent))
    from scripts import xml_lint
    import xml.etree.ElementTree as StandardET
    assert not xml_lint.validate_sxsd_document(first['xml'], StandardET.fromstring(first['xml']))


@pytest.mark.parametrize('attrs', ['autoStartAt="0"', 'autoStartAt="32768"', 'autoStartAt="1.5"', 'level="0"', 'level="11"'])
def test_invalid_counter_or_level_is_rejected_without_changing_source(attrs, tmp_path):
    raw = slide(f'<content list="number"><p {attrs}>A</p></content>').encode()
    source = tmp_path/'author.xml'; source.write_bytes(raw)
    with pytest.raises(ValueError):
        api().explicit_numbering(source)
    assert source.read_bytes() == raw


def test_out_of_range_li_override_cannot_be_silently_coerced():
    with pytest.raises(ValueError):
        api().explicit_numbering(slide('<content><ol><li index="0"><p>A</p></li></ol></content>'))


def test_counter_overflow_and_nested_list_in_inline_paragraph_are_explicit_failures():
    with pytest.raises(ValueError):
        api().explicit_numbering(slide('<content list="number" autoStartAt="32767"><p>A</p><p>B</p></content>'))
    with pytest.raises(ValueError):
        api().explicit_numbering(slide('<content><ol><li><p>A<ol><li><p>B</p></li></ol></p></li></ol></content>'))
