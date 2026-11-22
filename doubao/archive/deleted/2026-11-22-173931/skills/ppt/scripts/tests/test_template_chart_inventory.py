"""Native chart style discovery must survive combos, point overrides and grouped frames."""
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parents[1]
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
C = "http://schemas.openxmlformats.org/drawingml/2006/chart"
P = "http://schemas.openxmlformats.org/presentationml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def module():
    path = SCRIPTS / "template" / "template_chart_inventory.py"
    assert path.exists(), "native PPTX chart inventory helper is missing"
    spec = importlib.util.spec_from_file_location("template_chart_inventory", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def rels(*items):
    return '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' + ''.join(
        f'<Relationship Id="{rid}" Type="{R}/{kind}" Target="{target}"/>'
        for rid, kind, target in items
    ) + '</Relationships>'


def frame(element_id, rid, x, y, w=914400, h=914400):
    return f'''<p:graphicFrame><p:nvGraphicFramePr><p:cNvPr id="{element_id}" name="Chart {element_id}"/></p:nvGraphicFramePr>
      <p:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{w}" cy="{h}"/></p:xfrm>
      <a:graphic><a:graphicData><c:chart r:id="{rid}"/></a:graphicData></a:graphic></p:graphicFrame>'''


def pptx_fixture(tmp_path, *, empty=False, broken=False, reordered=False):
    """Values are deliberately distinctive so any leaking caches/formulas is detectable."""
    path = tmp_path / "template.pptx"
    presentation = f'''<p:presentation xmlns:p="{P}" xmlns:r="{R}"><p:sldIdLst>
      <p:sldId id="901" r:id="s2"/><p:sldId id="900" r:id="s1"/>
      </p:sldIdLst><p:sldSz cx="12192000" cy="6858000"/></p:presentation>'''
    if not reordered:
        presentation = f'''<p:presentation xmlns:p="{P}" xmlns:r="{R}"><p:sldIdLst><p:sldId id="900" r:id="s1"/><p:sldId id="901" r:id="s2"/></p:sldIdLst><p:sldSz cx="12192000" cy="6858000"/></p:presentation>'''
    frames = '' if empty else ''.join(frame(i, f'c{i}', x, y) for i, x, y in (
        (10, 0, 0), (11, 1097280, 0), (12, 0, 1097280), (13, 1097280, 1097280)))
    group = f'''<p:grpSp><p:nvGrpSpPr><p:cNvPr id="9" name="Panels"/></p:nvGrpSpPr>
      <p:grpSpPr><a:xfrm><a:off x="914400" y="1828800"/><a:ext cx="4389120" cy="4389120"/>
      <a:chOff x="0" y="0"/><a:chExt cx="2194560" cy="2194560"/></a:xfrm></p:grpSpPr>{frames}</p:grpSp>'''
    slide = f'<p:sld xmlns:p="{P}" xmlns:a="{A}" xmlns:c="{C}" xmlns:r="{R}"><p:cSld><p:spTree>{group}</p:spTree></p:cSld></p:sld>'
    series = '''<c:ser><c:idx val="0"/><c:order val="0"/><c:tx><c:strRef><c:f>SECRET_NAME_FORMULA</c:f><c:strCache><c:pt idx="0"><c:v>Source series</c:v></c:pt></c:strCache></c:strRef></c:tx>
      <c:spPr><a:solidFill><a:schemeClr val="accent2"><a:lumMod val="60000"/><a:lumOff val="40000"/></a:schemeClr></a:solidFill><a:ln><a:noFill/></a:ln>
      <a:extLst><a:ext><a:hiddenFill><a:solidFill><a:srgbClr val="DEAD00"/></a:solidFill></a:hiddenFill></a:ext></a:extLst></c:spPr>
      <c:dPt><c:idx val="1"/><c:spPr><a:solidFill><a:srgbClr val="7030A0"/></a:solidFill></c:spPr></c:dPt>
      <c:cat><c:strLit><c:pt idx="0"><c:v>SECRET_CATEGORY</c:v></c:pt></c:strLit></c:cat>
      <c:val><c:numRef><c:f>SECRET_VALUE_FORMULA</c:f><c:numCache><c:pt idx="0"><c:v>987654321</c:v></c:pt></c:numCache></c:numRef></c:val></c:ser>'''
    chart = f'''<c:chartSpace xmlns:c="{C}" xmlns:a="{A}" xmlns:r="{R}"><c:chart><c:plotArea>
      <c:barChart><c:barDir val="col"/><c:grouping val="stacked"/>{series}<c:axId val="100"/><c:axId val="200"/></c:barChart>
      <c:lineChart><c:ser><c:idx val="1"/><c:order val="1"/><c:tx><c:v>Reference</c:v></c:tx><c:spPr><a:ln><a:solidFill><a:srgbClr val="112233"/></a:solidFill></a:ln></c:spPr></c:ser><c:axId val="100"/><c:axId val="200"/></c:lineChart>
      <c:catAx><c:axId val="100"/><c:delete val="0"/><c:axPos val="b"/><c:tickLblPos val="none"/><c:crossAx val="200"/></c:catAx>
      <c:valAx><c:axId val="200"/><c:scaling><c:min val="0"/><c:max val="987654321"/><c:orientation val="minMax"/></c:scaling><c:delete val="1"/><c:axPos val="l"/><c:numFmt formatCode="0%" sourceLinked="0"/><c:majorGridlines/></c:valAx>
      </c:plotArea><c:legend><c:legendPos val="b"/><c:overlay val="0"/><c:legendEntry><c:idx val="1"/><c:delete val="1"/></c:legendEntry></c:legend></c:chart></c:chartSpace>'''
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('ppt/presentation.xml', presentation)
        z.writestr('ppt/_rels/presentation.xml.rels', rels(('s1', 'slide', 'slides/slide1.xml'), ('s2', 'slide', 'slides/slide2.xml')))
        z.writestr('ppt/slides/slide1.xml', slide)
        z.writestr('ppt/slides/slide2.xml', f'<p:sld xmlns:p="{P}"><p:cSld><p:spTree/></p:cSld></p:sld>')
        z.writestr('ppt/slides/_rels/slide1.xml.rels', rels(('lay', 'slideLayout', '../slideLayouts/slideLayout1.xml'), *[(f'c{i}', 'chart', f'../charts/chart{i}.xml') for i in range(10, 14)]))
        z.writestr('ppt/slideLayouts/slideLayout1.xml', f'<p:sldLayout xmlns:p="{P}"/>')
        z.writestr('ppt/slideLayouts/_rels/slideLayout1.xml.rels', rels(('master', 'slideMaster', '../slideMasters/slideMaster1.xml')))
        z.writestr('ppt/slideMasters/slideMaster1.xml', f'<p:sldMaster xmlns:p="{P}"><p:clrMap bg1="lt1" tx1="dk1" accent2="accent2"/></p:sldMaster>')
        z.writestr('ppt/slideMasters/_rels/slideMaster1.xml.rels', rels(('theme', 'theme', '../theme/theme1.xml')))
        z.writestr('ppt/theme/theme1.xml', f'<a:theme xmlns:a="{A}"><a:themeElements><a:clrScheme><a:dk1><a:sysClr val="windowText" lastClr="000000"/></a:dk1><a:lt1><a:srgbClr val="FFFFFF"/></a:lt1><a:accent2><a:srgbClr val="01AFE5"/></a:accent2></a:clrScheme></a:themeElements></a:theme>')
        for i in range(10, 14):
            if broken and i == 11:
                continue
            z.writestr(f'ppt/charts/chart{i}.xml', chart)
    return path


def test_inventory_keeps_relationship_ids_and_presentation_page_order(tmp_path):
    m = module(); result = m.inventory(pptx_fixture(tmp_path, reordered=True))
    assert [s['source_slide_part'] for s in result['slides']] == ['ppt/slides/slide2.xml', 'ppt/slides/slide1.xml']
    chart = result['slides'][1]['charts'][0]
    assert chart['source_page_id'] == '900'
    assert chart['element_id'] == '10' and chart['relationship_id'] == 'c10'
    assert chart['chart_part'] == 'ppt/charts/chart10.xml'
    assert result['total_charts'] == 4


def test_inventory_exposes_combo_series_and_effective_theme_point_colors(tmp_path):
    m = module(); chart = m.inventory(pptx_fixture(tmp_path))['slides'][0]['charts'][0]
    assert chart['types'] == ['barChart', 'lineChart']
    assert chart['plot_types'][0]['grouping'] == 'stacked'
    assert chart['plot_types'][0]['bar_direction'] == 'col'
    series = chart['series'][0]
    assert series['name'] == 'Source series'
    # DrawingML lumMod/lumOff operate on HSL luminance, not RGB channels.
    assert series['colors'][0]['color'] == '#58D7FE'
    assert series['colors'][0]['scheme'] == 'accent2'
    assert series['colors'][0]['theme_part'] == 'ppt/theme/theme1.xml'
    assert series['point_overrides'][0]['colors'][0]['color'] == '#7030A0'
    assert '#DEAD00' not in chart['palette']
    assert chart['series'][1]['colors'][0]['channel'] == 'line'
    assert chart['series'][1]['colors'][0]['color'] == '#112233'
    assert chart['series'][1]['name'] == 'Reference'


def test_inventory_does_not_promote_template_sample_data(tmp_path):
    m = module(); result = m.inventory(pptx_fixture(tmp_path))
    serialized = json.dumps(result)
    for value in ('987654321', 'SECRET_VALUE_FORMULA', 'SECRET_NAME_FORMULA', 'SECRET_CATEGORY'):
        assert value not in serialized
    assert result['data_policy']['sample_values_included'] is False
    assert result['data_policy']['series_names_role'] == 'source_style_labels'


def test_inventory_records_axes_and_legend_visibility_without_scale_bounds(tmp_path):
    m = module(); chart = m.inventory(pptx_fixture(tmp_path))['slides'][0]['charts'][0]
    assert chart['axes'][0]['axis_id'] == '100'
    assert chart['axes'][0]['tick_label_position'] == 'none'
    assert chart['axes'][1]['deleted'] is True
    assert chart['axes'][1]['number_format'] == '0%'
    assert chart['axes'][1]['major_gridlines'] is True
    assert chart['legend']['position'] == 'b' and chart['legend']['overlay'] is False
    assert chart['legend']['hidden_series_indices'] == ['1']


def test_inventory_transforms_grouped_chart_frames_and_finds_panel_geometry(tmp_path):
    m = module(); slide = m.inventory(pptx_fixture(tmp_path))['slides'][0]
    assert slide['charts'][0]['bbox_inch'] == {'left': 1.0, 'top': 2.0, 'width': 2.0, 'height': 2.0}
    assert slide['charts'][0]['parent_group_ids'] == ['9']
    group = slide['small_multiple_groups'][0]
    assert group['rows'] == 2 and group['columns'] == 2
    assert len(group['members']) == 4
    assert group['candidate_only'] is True
    assert group['bbox_inch'] == {'left': 1.0, 'top': 2.0, 'width': 4.4, 'height': 4.4}


def test_inventory_retains_broken_refs_as_warnings_and_handles_zero_charts(tmp_path):
    m = module(); result = m.inventory(pptx_fixture(tmp_path, broken=True))
    assert result['total_charts'] == 4
    assert result['parsed_chart_count'] == 3
    assert result['warnings'] and 'chart11.xml' in str(result['warnings'])
    result = m.inventory(pptx_fixture(tmp_path, empty=True))
    assert result['total_charts'] == 0
    assert result['slides'][0]['small_multiple_groups'] == []


def test_inventory_tolerates_malformed_chart_parts_without_hiding_other_charts(tmp_path):
    m = module(); source = pptx_fixture(tmp_path)
    with zipfile.ZipFile(source) as z:
        parts = {n: z.read(n) for n in z.namelist()}
    parts['ppt/charts/chart11.xml'] = b'<c:chartSpace malformed'
    with zipfile.ZipFile(source, 'w') as z:
        for name, data in parts.items(): z.writestr(name, data)
    result = m.inventory(source)
    assert result['total_charts'] == 4 and result['parsed_chart_count'] == 3
    assert len(result['warnings']) == 1


def test_theme_override_colors_keep_per_slot_provenance(tmp_path):
    m = module(); source = pptx_fixture(tmp_path)
    with zipfile.ZipFile(source) as z:
        parts = {n: z.read(n) for n in z.namelist()}
    chart = parts['ppt/charts/chart10.xml'].decode().replace('<a:srgbClr val="7030A0"/>', '<a:schemeClr val="tx1"/>')
    parts['ppt/charts/chart10.xml'] = chart.encode()
    parts['ppt/charts/_rels/chart10.xml.rels'] = rels(('themeOverride', 'themeOverride', '../theme/override.xml')).encode()
    parts['ppt/theme/override.xml'] = f'<a:themeOverride xmlns:a="{A}"><a:clrScheme><a:accent2><a:srgbClr val="000000"/></a:accent2></a:clrScheme></a:themeOverride>'.encode()
    with zipfile.ZipFile(source, 'w') as z:
        for name, data in parts.items(): z.writestr(name, data)
    chart = m.inventory(source)['slides'][0]['charts'][0]
    assert chart['series'][0]['colors'][0]['color'] == '#666666'
    assert chart['series'][0]['colors'][0]['theme_part'] == 'ppt/theme/override.xml'
    point = chart['series'][0]['point_overrides'][0]['colors'][0]
    assert point['color'] == '#000000' and point['theme_part'] == 'ppt/theme/theme1.xml'


def test_unspecified_or_unsupported_color_does_not_invent_a_palette():
    m = module()
    root = ET.fromstring(
        f'<c:chartSpace xmlns:c="{C}" xmlns:a="{A}"><c:chart><c:plotArea><c:barChart><c:ser><c:idx val="0"/></c:ser></c:barChart></c:plotArea></c:chart></c:chartSpace>')
    chart = m.parse_chart(root)
    assert chart['palette'] == []
    assert chart['series'][0]['color_resolution'] == 'none_or_unresolved_inherited'
    color = m.resolve_color(ET.fromstring(f'<a:schemeClr xmlns:a="{A}" val="accent9"/>'))
    assert color['resolved'] is False and color['color'] is None


def test_inventory_cli_refuses_to_overwrite_source(tmp_path):
    module(); source = pptx_fixture(tmp_path)
    before = source.read_bytes()
    run = subprocess.run([sys.executable, str(SCRIPTS / 'template' / 'template_chart_inventory.py'), '--pptx', str(source), '--output', str(source)], capture_output=True, text=True)
    assert run.returncode == 2 and json.loads(run.stdout)['ok'] is False
    assert source.read_bytes() == before


@pytest.mark.skipif(not os.environ.get('PPT_TEST_MCKINSEY_TEMPLATE'), reason='local source PPTX supplied only for integration validation')
def test_actual_mckinsey_template_chart_types_colors_and_facets():
    m = module(); source = Path(os.environ['PPT_TEST_MCKINSEY_TEMPLATE'])
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    result = m.inventory(source)
    assert result['total_charts'] == 34 and result['parsed_chart_count'] == 34
    assert [s['chart_count'] for s in result['slides']] == [1, 3, 1, 10, 1, 8, 9, 1]
    assert result['warnings'] == []
    assert m.summarize(result)['types'] == {'barChart': 31, 'areaChart': 3, 'lineChart': 3, 'scatterChart': 9}
    assert '#2451FF' in result['slides'][3]['charts'][0]['palette']
    assert '#9D51D4' in result['slides'][3]['charts'][0]['palette']
    members = result['slides'][3]['small_multiple_groups'][0]['members']
    # Source y coordinates differ by a few EMU; visual order must use row/column bands.
    assert [(m['row'], m['column']) for m in members] == [(1, 1), (1, 2), (1, 3), (1, 4), (1, 5), (2, 1), (2, 2), (2, 3), (2, 4), (2, 5)]
    assert [(g['rows'], g['columns'], len(g['members'])) for s in result['slides'][3:7] for g in s['small_multiple_groups']] == [(2, 5, 10), (2, 4, 8), (2, 5, 9)]
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before


def test_inventory_cli_writes_full_index_and_prints_compact_summary(tmp_path):
    m = module(); source = pptx_fixture(tmp_path)
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    output = tmp_path / 'nested' / 'inventory.json'
    run = subprocess.run([sys.executable, str(SCRIPTS / 'template' / 'template_chart_inventory.py'), '--pptx', str(source), '--output', str(output)], capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    report = json.loads(run.stdout)
    assert report['total_charts'] == 4 and report['chart_counts_by_slide'] == [4, 0]
    assert 'series' not in report
    assert json.loads(output.read_text())['slides'][0]['charts'][0]['types'] == ['barChart', 'lineChart']
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before


def test_parse_template_exposes_native_inventory_to_lightweight_index(tmp_path, monkeypatch, capsys):
    source = pptx_fixture(tmp_path)
    monkeypatch.syspath_prepend(str(SCRIPTS))
    from scripts.template import parse_template as pt
    capabilities = {'python_pptx': False, 'pypdfium2': False, 'pil': False, 'lxml': False, 'soffice': False, 'lark_cli': False}
    monkeypatch.setattr(pt, '_detect_capabilities', lambda: (capabilities.copy(), []))
    monkeypatch.setattr(pt, '_ensure_pip_deps', lambda *a, **kw: [])
    monkeypatch.setattr(pt, '_render_overview', lambda *a, **kw: (False, 'test_no_renderer'))
    work = tmp_path / 'work'
    monkeypatch.setattr(sys, 'argv', ['parse_template.py', '--pptx', str(source), '--work-dir', str(work), '--offline-only'])
    assert pt.main() == 0
    report = json.loads(capsys.readouterr().out)
    assert report['native_chart_inventory_path'] == 'manifest/native-chart-inventory.json'
    index = json.loads((work / report['template_index_path']).read_text())
    assert index['native_charts']['total_charts'] == 4
    assert index['slides'][0]['native_charts']['types'] == ['barChart', 'lineChart']
    assert '#7030A0' in index['slides'][0]['native_charts']['palette']
    assert index['slides'][0]['native_charts']['small_multiple_groups'][0]['rows'] == 2
    detail = json.loads((work / 'manifest/slides/slide-01.json').read_text())
    assert detail['native_charts'][0]['element_id'] == '10'


def hidden_duplicate_chart_xml():
    values='<c:numRef><c:f>SECRET_RANGE</c:f><c:numCache><c:ptCount val="4"/><c:pt idx="0"><c:v>987654321</c:v></c:pt><c:pt idx="2"><c:v>987654322</c:v></c:pt><c:pt idx="3"><c:v>987654323</c:v></c:pt></c:numCache></c:numRef>'
    off='<c:dLbls><c:showVal val="0"/><c:showCatName val="0"/><c:showSerName val="0"/><c:showPercent val="0"/><c:showLegendKey val="0"/></c:dLbls>'
    return f'<c:chartSpace xmlns:c="{C}" xmlns:a="{A}"><c:chart><c:plotArea><c:areaChart><c:grouping val="standard"/><c:ser><c:idx val="1"/><c:spPr><a:solidFill><a:srgbClr val="58D7FE"/></a:solidFill></c:spPr><c:val>{values}</c:val></c:ser>{off}<c:axId val="x"/><c:axId val="y"/></c:areaChart><c:lineChart><c:grouping val="standard"/><c:ser><c:idx val="0"/><c:spPr><a:ln><a:noFill/></a:ln></c:spPr><c:marker><c:symbol val="none"/></c:marker><c:val>{values}</c:val></c:ser>{off}<c:axId val="x"/><c:axId val="y"/></c:lineChart></c:plotArea><c:dispBlanksAs val="gap"/></c:chart></c:chartSpace>'


def test_inventory_verifies_invisible_duplicate_without_leaking_sample_values_or_formula():
    result=module().parse_chart(ET.fromstring(hidden_duplicate_chart_xml()));helper=result['series'][1]
    assert helper['hidden_duplicate'] is True and helper['helper_of']==0
    assert helper['source_point_layout']=={'point_count':4,'nonempty_positions':[0,2,3],'missing_positions':[1],'blank_mode':'gap'}
    assert result['series'][0].get('hidden_duplicate') is not True
    assert all(secret not in json.dumps(result) for secret in ('987654321','987654322','987654323','SECRET_RANGE'))


@pytest.mark.parametrize('change', ['different_formula','different_value','different_mask','marker','stroke','errorbar','labels','different_axes'])
def test_hidden_duplicate_requires_verified_same_data_and_fully_invisible_source(change):
    root=ET.fromstring(hidden_duplicate_chart_xml());helper=root.find('.//{'+C+'}lineChart/{'+C+'}ser');line=root.find('.//{'+C+'}lineChart')
    if change=='different_formula':helper.find('.//{'+C+'}f').text='OTHER_RANGE'
    if change=='different_value':helper.find('.//{'+C+'}v').text='987654320'
    if change=='different_mask':helper.find('.//{'+C+'}pt').set('idx','1')
    if change=='marker':helper.find('.//{'+C+'}symbol').set('val','circle')
    if change=='stroke':helper.find('.//{'+A+'}noFill').tag='{'+A+'}solidFill'
    if change=='errorbar':ET.SubElement(helper,'{'+C+'}errBars')
    if change=='labels':line.find('{'+C+'}dLbls/{'+C+'}showVal').set('val','1')
    if change=='different_axes':line.find('{'+C+'}axId').set('val','other')
    assert module().parse_chart(root)['series'][1].get('hidden_duplicate') is not True


def test_real_source_hidden_duplicates_keep_only_structural_gap_metadata():
    source=os.environ.get('PPT_TEST_MCKINSEY_TEMPLATE')
    if not source:pytest.skip('real source template supplied for integration')
    result=module().inventory(source)
    helpers=[c['series'][1] for c in result['slides'][1]['charts']]
    assert all(h['hidden_duplicate'] is True and h['helper_of']==0 for h in helpers)
    assert all(h['source_point_layout']['missing_positions']==[3,7,11,15] for h in helpers)
    assert all(h['source_point_layout']['point_count']==19 for h in helpers)
    assert 'Sheet1!' not in json.dumps(result)
