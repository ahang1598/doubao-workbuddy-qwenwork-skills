"""Regression coverage for source template custom paths in local frame units."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from xml.etree import ElementTree as ET

import pytest

SCRIPT = Path(__file__).parents[1] / 'template' / 'template_reuse.py'


def module():
    spec = importlib.util.spec_from_file_location('template_reuse_custom_path', SCRIPT)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


# W55 source dimensions reconstructed from the original 1440x810 template:
# the failed 960x540 output scaled frames by 2/3 but retained these local paths.
W55 = '''<slide xmlns="https://www.larkoffice.com/sml/2.0" id="source1440"><data>
<shape id="btm" type="custom" topLeftX="0" topLeftY="15.4" width="1440" height="63.2954" path="M0,0 L1440,0 L1440,63.2954 L0,63.2954 Z"><fill><fillColor color="#eaeaea"/></fill></shape>
<shape id="btp" type="custom" topLeftX="109.7" topLeftY="234.55" width="1233.6" height="269.35" path="M0,0 L1233.6,0 L1233.6,269.35 L0,269.35 Z"><fill><fillColor color="#920011"/></fill></shape>
<shape id="bnt" type="text" topLeftX="109.7" topLeftY="535.215" width="240" height="36"><content fontFamily="SourceEA" fontSize="24" color="#1e1e1e"><p><span>研究缺口</span></p></content></shape>
<line id="reference" startShapeId="btp" endShapeId="bnt"/>
<img id="media" src="fixture-media" topLeftX="1200" topLeftY="0" width="24" height="24"><crop leftOffset="0"/></img>
<chart id="data" topLeftX="1250" topLeftY="0" width="100" height="100"><chartField>1440,63.2954</chartField></chart>
</data></slide>'''
IDS = ['btm', 'btp', 'bnt', 'reference', 'media', 'data']


def members(xml):
    return {n.get('id'): n for n in ET.fromstring(xml).find('{*}data')}


def test_w55_two_thirds_scale_keeps_local_red_ink_above_black_text(tmp_path):
    source = tmp_path / 'source1440.xml'
    source.write_text(W55, encoding='utf-8')
    original = source.read_bytes()
    result = module().transform_component(source, IDS, scale=2/3)
    nodes = members(result['xml'])
    red = nodes['btp']
    assert [float(red.get(k)) for k in ('topLeftX', 'topLeftY', 'width', 'height')] == pytest.approx([73.1333333333333, 156.366666666667, 822.4, 179.566666666667])
    assert red.get('path') == 'M 0 0 L 822.4 0 L 822.4 179.566666666667 L 0 179.566666666667 Z'
    assert nodes['btm'].get('path') == 'M 0 0 L 960 0 L 960 42.1969333333333 L 0 42.1969333333333 Z'
    assert float(red.get('topLeftY')) + 179.566666666667 < float(nodes['bnt'].get('topLeftY'))
    assert nodes['bnt'].find('{*}content/{*}p/{*}span').text == '研究缺口'
    assert nodes['bnt'].find('{*}content').get('fontFamily') == 'SourceEA'
    assert float(nodes['bnt'].find('{*}content').get('fontSize')) == 16
    assert nodes['btp'].find('{*}fill/{*}fillColor').get('color') == '#920011'
    assert nodes['reference'].get('startShapeId') == 'btp'
    assert nodes['reference'].get('endShapeId') == 'bnt'
    assert nodes['media'].get('src') == 'fixture-media'
    assert nodes['media'].find('{*}crop').get('leftOffset') == '0'
    assert nodes['data'].find('{*}chartField').text == '1440,63.2954'
    assert result['source_bbox'] == {'x': 0.0, 'y': 0.0, 'width': 1440.0, 'height': 571.215}
    assert result['target_bbox'] == {'x': 0.0, 'y': 0.0, 'width': 960.0, 'height': 380.81}
    assert result['member_ids'] == IDS
    assert result['source_sha256'] == hashlib.sha256(original).hexdigest()
    assert result['xml_sha256'] == hashlib.sha256(result['xml'].encode()).hexdigest()
    assert source.read_bytes() == original


def custom_source(tmp_path, path, attributes=''):
    source = tmp_path / 'custom.xml'
    source.write_text(f'<slide><data><shape id="custom" type="custom" topLeftX="10" topLeftY="20" width="100" height="60" path="{path}" {attributes}/></data></slide>')
    return source


def test_translate_only_preserves_exact_local_path_and_orientation(tmp_path):
    path = 'm1e1,2e1h30v-10a5,6 27 0 1 7,8z'
    source = custom_source(tmp_path, path, 'rotation="37" flipX="true" flipY="false"')
    transformed = members(module().transform_component(source, ['custom'], x=80, y=90)['xml'])['custom']
    assert transformed.get('path') == path
    assert [float(transformed.get(k)) for k in ('topLeftX', 'topLeftY', 'width', 'height')] == [80, 90, 100, 60]
    assert [transformed.get(k) for k in ('rotation', 'flipX', 'flipY')] == ['37', 'true', 'false']


@pytest.mark.parametrize(('path', 'expected'), [
    ('M1e1,-2E1 3e1,4e1 H50 V60 C1 2 3 4 5 6 S7 8 9 10 Q11 12 13 14 T15 16 A17 18 35 0 1 19 20 Z',
     'M 20 -40 60 80 H 100 V 120 C 2 4 6 8 10 12 S 14 16 18 20 Q 22 24 26 28 T 30 32 A 34 36 35 0 1 38 40 Z'),
    ('m10 20 30 40 h50 v-60 c1 2 3 4 5 6 s7 8 9 10 q11 12 13 14 t15 16 a17 18 -35 1 0 19 20 z',
     'm 20 40 60 80 h 100 v -120 c 2 4 6 8 10 12 s 14 16 18 20 q 22 24 26 28 t 30 32 a 34 36 -35 1 0 38 40 z'),
    ('M0 0 A10 20 45 01100 50 30 40 -15 1 0 -60 -70',
     'M 0 0 A 20 40 45 0 1 200 100 60 80 -15 1 0 -120 -140'),
])
def test_scale_respects_command_roles_relative_distances_and_compact_arc_flags(tmp_path, path, expected):
    source = custom_source(tmp_path, path, 'rotation="37" flipX="true"')
    transformed = members(module().transform_component(source, ['custom'], x=80, y=90, scale=2)['xml'])['custom']
    assert transformed.get('path') == expected
    assert [float(transformed.get(k)) for k in ('topLeftX', 'topLeftY', 'width', 'height')] == [80, 90, 200, 120]
    assert transformed.get('rotation') == '37'
    assert transformed.get('flipX') == 'true'


@pytest.mark.parametrize('path', ['', 'L0 0', 'M0 0 R1 2', 'M0 0 C1 2', 'M0 0 A1 2 0 2 0 3 4', 'M0 0 L1e999 0', 'M0 0? L1 2', 'M0 0 A-1 2 0 0 1 3 4'])
def test_malformed_or_unsupported_path_is_rejected_without_mutating_source(tmp_path, path):
    source = custom_source(tmp_path, path)
    before = source.read_bytes()
    with pytest.raises(ValueError, match='custom path'):
        module().transform_component(source, ['custom'], scale=2)
    assert source.read_bytes() == before


def test_custom_requires_local_path_attribute(tmp_path):
    source = tmp_path / 'missing.xml'
    source.write_text('<slide><data><shape id="custom" type="custom" width="100" height="60"><path d="M0 0 L100 60"/></shape></data></slide>')
    before = source.read_bytes()
    with pytest.raises(ValueError, match='custom path'):
        module().transform_component(source, ['custom'], scale=2)
    assert source.read_bytes() == before


@pytest.mark.parametrize('xml', [
    '<shape id="unsupported" type="host" width="100" height="60" path="M0 0 L100 60"/>',
    '<polyline id="unsupported" width="100" height="60"><point x="30" y="40"/></polyline>',
])
def test_unsupported_geometry_fails_whole_group_instead_of_returning_partial_xml(tmp_path, xml):
    source = tmp_path / 'unsupported.xml'
    source.write_text('<slide><data><shape id="valid" type="custom" width="100" height="60" path="M0 0 L100 60"/>' + xml + '</data></slide>')
    before = source.read_bytes()
    with pytest.raises(ValueError, match='unsupported'):
        module().transform_component(source, ['valid', 'unsupported'], scale=2)
    assert source.read_bytes() == before


def test_custom_transform_cli_writes_copied_xml_and_receipt(tmp_path):
    source = tmp_path / 'source1440.xml'
    source.write_text(W55, encoding='utf-8')
    before = source.read_bytes()
    output = tmp_path / 'scaled.xml'
    command = [sys.executable, str(SCRIPT), 'transform', '--source', str(source), '--ids', *IDS, '--scale', str(2/3), '--output', str(output)]
    result = subprocess.run(command, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert members(output.read_text())['btp'].get('path').startswith('M 0 0 L 822.4 0')
    receipt = json.loads(output.with_suffix('.transform.json').read_text())
    assert receipt['source_sha256'] == hashlib.sha256(before).hexdigest()
    assert receipt['xml_sha256'] == hashlib.sha256(output.read_bytes()).hexdigest()
    assert receipt['scale'] == 2/3
    assert source.read_bytes() == before
    assert subprocess.run(command, text=True, capture_output=True).returncode != 0


def migration_api():
    spec = importlib.util.spec_from_file_location('migration_custom_path', SCRIPT.with_name('template_migration.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def migrate_w55(tmp_path):
    source = tmp_path / 'source1440.xml'
    source.write_text(W55, encoding='utf-8')
    frame = tmp_path / 'frame960.xml'
    frame.write_text('<slide xmlns="https://www.larkoffice.com/sml/2.0"><data/></slide>')
    api = migration_api()
    result = api.compose_migration(source, frame, content_ids=IDS, frame_ids=[], target_region=[0, 0, 960, 540])
    return api, source, frame, result


def test_w55_migration_accepts_correctly_scaled_paths_without_changing_facts(tmp_path):
    api, source, frame, result = migrate_w55(tmp_path)
    nodes = members(result['xml'])
    assert nodes['btp'].get('path') == 'M 0 0 L 822.4 0 L 822.4 179.566666666667 L 0 179.566666666667 Z'
    assert nodes['btm'].get('path') == 'M 0 0 L 960 0 L 960 42.1969333333333 L 0 42.1969333333333 Z'
    assert api.validate_migration(result['xml'], result['contract'])['ok']
    assert source.read_text(encoding='utf-8') == W55
    assert result['contract']['source']['sha256'] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert result['contract']['frame']['sha256'] == hashlib.sha256(frame.read_bytes()).hexdigest()


@pytest.mark.parametrize(('change', 'member_id'), [
    ('text', 'bnt'), ('data', 'data'), ('chart_type', 'data'),
    ('reference', 'reference'), ('media', 'media'), ('note', 'note'),
])
def test_scaled_custom_path_migration_still_rejects_changed_facts_and_topology(tmp_path, change, member_id):
    api, source, _, result = migrate_w55(tmp_path)
    before = source.read_bytes()
    root = ET.fromstring(result['xml'])
    nodes = {n.get('id'): n for n in root.find('{*}data')}
    if change == 'text':
        nodes['bnt'].find('{*}content/{*}p/{*}span').text = 'Altered finding'
    elif change == 'data':
        nodes['data'].find('{*}chartField').text = '1441,63.2954'
    elif change == 'chart_type':
        nodes['data'].set('type', 'pie')
    elif change == 'reference':
        nodes['reference'].set('endShapeId', 'btm')
    elif change == 'media':
        nodes['media'].set('src', 'changed-media')
    else:
        note = ET.SubElement(root, '{https://www.larkoffice.com/sml/2.0}note')
        content = ET.SubElement(note, '{https://www.larkoffice.com/sml/2.0}content')
        ET.SubElement(content, '{https://www.larkoffice.com/sml/2.0}p').text = 'Changed speaker notes'
    verdict = api.validate_migration(ET.tostring(root, encoding='unicode'), result['contract'])
    assert not verdict['ok']
    assert any(error['member_id'] == member_id for error in verdict['errors'])
    assert source.read_bytes() == before
