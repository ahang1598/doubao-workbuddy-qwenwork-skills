"""Source-native chart styles must reach authored SML, not only a manifest."""
import copy
import importlib.util
import json
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parents[1]


def module():
    path = SCRIPTS / 'template' / 'template_chart_contract.py'
    assert path.exists(), 'source-native chart builder/contract is missing'
    spec = importlib.util.spec_from_file_location('template_chart_contract', path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def color(value, channel='fill'):
    return {'color': value, 'channel': channel, 'resolved': True, 'opacity': 1, 'source': 'explicit'}


def source_chart(i=0, kind='barChart'):
    return {'chart_id': f'slide-01:element-{10+i}:r{i}', 'source_slide_num': 1,
            'source_page_id': '101', 'source_slide_part': 'ppt/slides/slide7.xml',
            'element_id': str(10+i), 'chart_part': f'ppt/charts/chart{i+1}.xml',
            'chart_part_id': f'chart{i+1}', 'parsed': True, 'types': [kind],
            'bbox_inch': {'left': 1 + (i % 3)*2.2, 'top': 1 + (i//3)*2.2, 'width': 2, 'height': 2},
            'plot_types': [{'type': kind, 'grouping': 'clustered', 'bar_direction': 'col',
                            'axis_ids': ['x', 'y'], 'gap_width': '72', 'overlap': '0', 'smooth': False}],
            'series': [{'index': '0', 'order': '0', 'name': 'OLD_SAMPLE_SERIES',
                        'chart_type': kind, 'point_count': 3, 'appearance': {'fill': 'solidFill', 'line': 'none'},
                        'colors': [color('#213752')], 'marker': None,
                        'point_overrides': [{'index': str(n), 'appearance': {'fill': 'solidFill'}, 'colors': [color(c)]}
                                            for n, c in enumerate(['#00ACFF', '#2451FF', '#9D51D4'])]}],
            'axes': [{'type': 'catAx', 'axis_id': 'x', 'position': 'b', 'deleted': False, 'tick_label_position': 'none', 'orientation': 'minMax'},
                     {'type': 'valAx', 'axis_id': 'y', 'position': 'l', 'deleted': False, 'tick_label_position': 'nextTo', 'number_format': 'General', 'orientation': 'minMax', 'major_gridlines': False}],
            'legend': {'present': True, 'position': 'r', 'overlay': False, 'hidden_series_indices': []},
            'palette': ['#213752', '#00ACFF', '#2451FF', '#9D51D4']}


def inventory():
    charts = [source_chart(i) for i in range(6)]
    return {'ok': True, 'schema_version': 1, 'total_charts': 6, 'total_slides': 1,
            'source_pptx': '/reference/source.pptx', 'data_policy': {'sample_values_included': False},
            'slides': [{'slide_num': 1, 'charts': charts,
                        'small_multiple_groups': [{'group_id': 'slide-01-charts-1', 'candidate_only': True,
                                                  'rows': 2, 'columns': 3,
                                                  'bbox_inch': {'left': 1, 'top': 1, 'width': 6.4, 'height': 4.2},
                                                  'members': [{'chart_id': c['chart_id'], 'element_id': c['element_id'],
                                                               'row': i//3+1, 'column': i%3+1,
                                                               'bbox_inch': c['bbox_inch']} for i,c in enumerate(charts)]}]}]}


DATA = {'category_name': '城市', 'categories': ['上海,市区', '杭州&社区', '成都'],
        'series': [{'name': '当前续卡率', 'values': [64.2, 57.8, 62.7]}]}


def slide(fragment):
    return '<slide><data>' + fragment + '</data></slide>'


def test_builder_uses_explicit_new_data_and_native_source_point_palette():
    m=module(); inv=inventory(); before=copy.deepcopy(inv)
    built=m.build_chart(inv, 'slide-01:element-10:r0', DATA, series_map=[0])
    root=ET.fromstring(built['xml'])
    assert root.tag == 'chart'
    assert root.find('chartPlotArea/chartPlot').get('type') == 'column'
    bars=root.findall('chartPlotArea/chartPlot/chartSeriesList/chartSeries/chartBars/chartBar')
    assert [b.get('color') for b in bars] == ['rgb(0,172,255)','rgb(36,81,255)','rgb(157,81,212)']
    assert root.find('chartData/dim2/chartField').text == '64.2,57.8,62.7'
    assert root.find('chartData/dim1/chartField').get('valueType') == 'string'
    assert 'OLD_SAMPLE_SERIES' not in built['xml'] and 'D30932' not in built['xml']
    assert inv == before
    assert built['contract']['charts'][0]['source_chart_id'] == 'slide-01:element-10:r0'
    assert m.validate_chart_contract(slide(built['xml']),built['contract'],inventory=inv,bindings=built['bindings'])['ok']


def test_builder_preserves_axis_legend_and_bar_configuration():
    m=module(); inv=inventory(); built=m.build_chart(inv,inv['slides'][0]['charts'][0]['chart_id'],DATA,series_map=[0])
    root=ET.fromstring(built['xml']); plot=root.find('chartPlotArea/chartPlot')
    assert plot.find('chartSeriesList/chartSeries/chartBars').get('gapWidth') == '72'
    assert root.find('chartLegend').get('position') == 'right'
    x=root.find('chartPlotArea/chartAxes/chartAxis[@type="x"]')
    assert x.find('chartLabel').get('color') == 'rgba(0,0,0,0)'
    changed=built['xml'].replace('position="right"','position="top"')
    report=m.validate_chart_contract(slide(changed),built['contract'],inventory=inv,bindings=built['bindings'])
    assert not report['ok'] and 'source_chart_config_mismatch' in [e['code'] for e in report['errors']]


@pytest.mark.parametrize('kind,expected', [('barChart','bar'),('lineChart','line'),('areaChart','area'),('pieChart','pie'),('doughnutChart','pie')])
def test_common_native_types_have_real_sml_fragments(kind,expected):
    m=module(); inv=inventory(); c=inv['slides'][0]['charts'][0];c['types']=[kind];c['plot_types'][0].update(type=kind,bar_direction='bar',grouping='stacked' if kind=='areaChart' else 'standard',hole_size='60' if kind=='doughnutChart' else None)
    c['series'][0].update(chart_type=kind,point_overrides=[],colors=[color('#2451FF','line' if kind=='lineChart' else 'fill')],appearance={'fill':'solidFill','line':'solidFill' if kind=='lineChart' else 'none'})
    built=m.build_chart(inv,c['chart_id'],DATA,series_map=[0]);root=ET.fromstring(built['xml'])
    assert root.find('chartPlotArea/chartPlot').get('type') == expected
    if kind=='areaChart':assert root.find('chartPlotArea/chartPlot/chartExtra/chartStack') is not None
    if kind=='doughnutChart':assert root.find('.//chartSectors').get('innerRadius') == '0.6'
    assert m.validate_chart_contract(slide(built['xml']),built['contract'],inventory=inv,bindings=built['bindings'])['ok']


def test_preflight_rejects_logo_red_source_binding_type_and_data_tampering():
    m=module(); inv=inventory();built=m.build_chart(inv,inv['slides'][0]['charts'][0]['chart_id'],DATA,series_map=[0])
    for xml,code in [(built['xml'].replace('rgb(36,81,255)','rgb(211,9,50)'), 'source_palette_mismatch'),
                     (built['xml'].replace('type="column"','type="line"'),'source_chart_config_mismatch'),
                     (built['xml'].replace('57.8','60.8'),'new_data_mismatch')]:
        report=m.validate_chart_contract(slide(xml),built['contract'],inventory=inv,bindings=built['bindings'])
        assert not report['ok'] and code in [e['code'] for e in report['errors']]
    wrong=copy.deepcopy(built['bindings']);wrong['chart_sources']['chart_index:0']='slide-01:element-15:r5'
    assert 'source_chart_binding_mismatch' in [e['code'] for e in m.validate_chart_contract(slide(built['xml']),built['contract'],inventory=inv,bindings=wrong)['errors']]
    forged=copy.deepcopy(built['contract']);forged['charts'][0]['series_map']=[{'series':0,'color_point':55}]
    assert not m.validate_chart_contract(slide(built['xml']),forged,inventory=inv,bindings=built['bindings'])['ok']


def test_unknown_types_and_missing_combo_range_conditions_are_explicit_errors():
    m=module(); inv=inventory(); c=inv['slides'][0]['charts'][0]
    c['types']=['surfaceChart'];c['plot_types'][0]['type']='surfaceChart'
    with pytest.raises(m.ChartContractError) as error:m.build_chart(inv,c['chart_id'],DATA,series_map=[0])
    assert error.value.code == 'unsupported_source_type' and 'column' in error.value.alternatives
    c['types']=['barChart','scatterChart']
    with pytest.raises(m.ChartContractError,match='scatter'):m.build_chart(inv,c['chart_id'],DATA,series_map=[0])
    c['types']=['barChart'];c['plot_types'][0]['type']='barChart';c['series'][0]['appearance']['fill']='none';c['series'][0]['colors']=[]
    with pytest.raises(m.ChartContractError,match='range|baseline'):m.build_chart(inv,c['chart_id'],DATA,series_map=[0])
    with pytest.raises(m.ChartContractError,match='mapping|series_map'):m.build_chart(inventory(),'slide-01:element-10:r0',DATA)


def test_combo_requires_explicit_source_series_mapping_and_reuses_colors():
    m=module();inv=inventory();c=inv['slides'][0]['charts'][0]
    c['types']=['barChart','lineChart']; c['plot_types'].append({'type':'lineChart','grouping':'standard','axis_ids':['x','y']})
    c['series'][0]['point_overrides']=[];s=copy.deepcopy(c['series'][0]);s.update(index='1',order='1',chart_type='lineChart',colors=[color('#9D51D4','line')],appearance={'fill':'none','line':'solidFill'});c['series'].append(s)
    data={'categories':['Q1','Q2'],'series':[{'name':'当前门店','values':[20,30]},{'name':'当前率','values':[12,13]}],'kind':'combo'}
    built=m.build_chart(inv,c['chart_id'],data,series_map=[0,1]);p=ET.fromstring(built['xml']).find('chartPlotArea/chartPlot')
    assert p.get('type')=='combo'
    assert [s.get('comboType') for s in p.findall('chartSeriesList/chartSeries')] == ['column','line']
    assert p.find('chartSeriesList/chartSeries[@index="2"]/chartLine').get('color')=='rgb(157,81,212)'


def test_changed_series_or_point_roles_require_a_reason_and_explicit_source_palette_mapping():
    m=module();inv=inventory();data={'categories':['Q1','Q2'],'series':[{'name':n,'values':[10,20]} for n in ('社区','标准','旗舰')]}
    mapping=[{'series':0,'color_point':n} for n in range(3)]
    with pytest.raises(m.ChartContractError,match='reason'):m.build_chart(inv,'slide-01:element-10:r0',data,series_map=mapping)
    built=m.build_chart(inv,'slide-01:element-10:r0',data,series_map=mapping,adaptation_reason='当前三店型用源青蓝紫数据色映射，源单系列类别改为三系列季度比较')
    p=ET.fromstring(built['xml']).find('chartPlotArea/chartPlot')
    assert [s.find('chartBars').get('color') for s in p.findall('chartSeriesList/chartSeries')] == ['rgb(0,172,255)','rgb(36,81,255)','rgb(157,81,212)']
    assert m.validate_chart_contract(slide(built['xml']),built['contract'],inventory=inv,bindings=built['bindings'])['ok']


def test_group_keeps_full_source_geometry_contract_and_adapts_panel_count_only_with_reason():
    m=module();inv=inventory();panels=[{'data':DATA,'series_map':[0]} for _ in range(6)]
    built=m.build_group(inv,'slide-01-charts-1',panels,bbox={'left':20,'top':100,'width':640,'height':420})
    roots=list(ET.fromstring('<data>'+built['xml']+'</data>'));assert len(roots)==6
    assert [r.get('topLeftX') for r in roots[:3]] == ['20','240','460']
    assert [r.get('topLeftY') for r in roots[3:]] == ['320','320','320']
    assert built['contract']['groups'][0]['source_chart_ids']==['slide-01:element-10:r0','slide-01:element-11:r1','slide-01:element-12:r2','slide-01:element-13:r3','slide-01:element-14:r4','slide-01:element-15:r5']
    with pytest.raises(m.ChartContractError,match='reason'):m.build_group(inv,'slide-01-charts-1',panels[:4])
    adapted=m.build_group(inv,'slide-01-charts-1',panels[:4],adaptation_reason='用户只有四个城市，保留源2x3槽位规律并留空两格')
    assert adapted['contract']['groups'][0]['source_columns']==3
    assert len(adapted['contract']['groups'][0]['source_chart_ids'])==6
    assert m.validate_chart_contract(slide(adapted['xml']),adapted['contract'],inventory=inv,bindings=adapted['bindings'])['ok']
    incomplete=ET.fromstring('<data>'+built['xml']+'</data>');incomplete.remove(incomplete[-1])
    assert not m.validate_chart_contract(slide(''.join(ET.tostring(e,encoding='unicode') for e in incomplete)),built['contract'],inventory=inv,bindings=built['bindings'])['ok']


def test_data_page_cannot_replace_charts_with_shape_bars_or_fake_table_role():
    m=module();inv=inventory();built=m.build_chart(inv,'slide-01:element-10:r0',DATA,series_map=[0]);bars='<shape type="rect" width="100" height="30" topLeftX="50" topLeftY="50"/>'
    assert 'native_chart_required' in [e['code'] for e in m.validate_chart_contract(slide(bars),built['contract'],inventory=inv)['errors']]
    for role in ('cover','ending'):
        contract=m.make_page_contract(inv,role=role)
        assert m.validate_chart_contract(slide(bars),contract,inventory=inv)['ok']
    data={'headers':['城市','续卡率'],'rows':[['杭州',57.8],['上海',64.2]]}
    table=m.build_table(inv,data,bbox={'left':30,'top':100,'width':500,'height':200})
    assert m.validate_chart_contract(slide(table['xml']),table['contract'],inventory=inv)['ok']
    assert 'native_table_required' in [e['code'] for e in m.validate_chart_contract(slide(bars),table['contract'],inventory=inv)['errors']]
    assert 'table_data_mismatch' in [e['code'] for e in m.validate_chart_contract(slide(table['xml'].replace('57.8','60.8')),table['contract'],inventory=inv)['errors']]
    with pytest.raises(m.ChartContractError,match='data'):m.make_page_contract(inv,role='table_page')


def test_nonfinite_data_or_wrong_lengths_and_inventory_tampering_are_rejected():
    m=module(); inv=inventory()
    for values in ([1,2],[1,2,float('nan')],[1,2,float('inf')]):
        data=copy.deepcopy(DATA);data['series'][0]['values']=values
        with pytest.raises(m.ChartContractError):m.build_chart(inv,'slide-01:element-10:r0',data,series_map=[0])
    b=m.build_chart(inv,'slide-01:element-10:r0',DATA,series_map=[0]);changed=copy.deepcopy(inv);changed['slides'][0]['charts'][0]['series'][0]['colors'][0]['color']='#D30932'
    assert 'source_inventory_mismatch' in [e['code'] for e in m.validate_chart_contract(slide(b['xml']),b['contract'],inventory=changed,bindings=b['bindings'])['errors']]


def test_group_can_extend_rows_with_reason_without_losing_source_members():
    m=module();inv=inventory();panels=[{'data':DATA,'series_map':[0]} for _ in range(8)]
    b=m.build_group(inv,'slide-01-charts-1',panels,bbox={'left':20,'top':50,'width':640,'height':640},adaptation_reason='八个城市，需要按源三列规律增加第三行')
    charts=list(ET.fromstring('<data>'+b['xml']+'</data>'))
    assert len(charts)==8 and [c.get('topLeftX') for c in charts[-2:]] == ['20','240']
    assert [c.get('topLeftY') for c in charts[-2:]] == ['490','490']
    assert len(b['contract']['groups'][0]['source_chart_ids'])==6
    assert m.validate_chart_contract(slide(b['xml']),b['contract'],inventory=inv,bindings=b['bindings'])['ok']


def test_new_units_and_legend_adaptation_are_explicit_without_scaling_data():
    m=module(); inv=inventory();data=copy.deepcopy(DATA);data['value_format']='0.0"%"';data['legend']={'present':False}
    with pytest.raises(m.ChartContractError,match='reason'):m.build_chart(inv,'slide-01:element-10:r0',data,series_map=[0])
    b=m.build_chart(inv,'slide-01:element-10:r0',data,series_map=[0],adaptation_reason='新任务提供百分点字面量，单系列不需源右侧图例')
    root=ET.fromstring(b['xml']);assert root.find('chartLegend') is None
    assert root.find('chartData/dim2/chartField').text=='64.2,57.8,62.7'
    assert root.find('chartPlotArea/chartAxes/chartAxis[@type="y"]/chartLabel').get('format')=='0.0"%"'
    assert m.validate_chart_contract(slide(b['xml']),b['contract'],inventory=inv,bindings=b['bindings'])['ok']


def test_unsupported_types_take_precedence_over_point_adaptation_and_range_data_is_not_ordinary_bar():
    m=module();inv=inventory();c=inv['slides'][0]['charts'][0];c['types']=['scatterChart'];data=copy.deepcopy(DATA);data['categories']=data['categories'][:2];data['series'][0]['values']=[10,20]
    with pytest.raises(m.ChartContractError) as error:m.build_chart(inv,c['chart_id'],data,series_map=[0])
    assert error.value.code=='unsupported_source_type'
    data=copy.deepcopy(DATA);data['kind']='range'
    with pytest.raises(m.ChartContractError) as error:m.build_chart(inventory(),'slide-01:element-10:r0',data,series_map=[0])
    assert error.value.code=='unsupported_data_semantics'


def test_native_table_requires_sml_namespace():
    m=module();inv=inventory();data={'headers':['城市','率'],'rows':[['杭州',57.8]]};t=m.build_table(inv,data,bbox={'left':30,'top':100,'width':500,'height':200})
    fake=t['xml'].replace('<table ','<table xmlns="urn:fake" ',1)
    assert 'native_table_required' in [e['code'] for e in m.validate_chart_contract(slide(fake),t['contract'],inventory=inv)['errors']]


def test_contract_new_data_cannot_silently_change_with_authored_data():
    m=module();inv=inventory()
    b=m.build_chart(inv,'slide-01:element-10:r0',DATA,series_map=[0]);changed=copy.deepcopy(b['contract']);changed['charts'][0]['new_data']['series'][0]['values'][1]=60.8
    report=m.validate_chart_contract(slide(b['xml'].replace('57.8','60.8')),changed,inventory=inv,bindings=b['bindings'])
    assert 'new_data_contract_mismatch' in [e['code'] for e in report['errors']]


def test_source_line_marker_palette_is_not_replaced_by_the_line_or_logo_color():
    m=module();inv=inventory();c=inv['slides'][0]['charts'][0];c['types']=['lineChart'];c['plot_types'][0].update(type='lineChart',grouping='standard')
    c['series'][0].update(chart_type='lineChart',point_overrides=[],appearance={'line':'solidFill','fill':'none'},colors=[color('#2451FF','line'),color('#9D51D4','marker_fill')],marker={'symbol':'circle','size':'6'})
    b=m.build_chart(inv,c['chart_id'],DATA,series_map=[0]);root=ET.fromstring(b['xml'])
    point=root.find('chartPlotArea/chartPlot/chartSeriesList/chartSeries/chartPoints')
    assert point.get('shape')=='circle' and point.get('size')=='6' and point.get('color')=='rgb(157,81,212)'
    altered=b['xml'].replace('rgb(157,81,212)','rgb(211,9,50)')
    assert 'source_palette_mismatch' in [e['code'] for e in m.validate_chart_contract(slide(altered),b['contract'],inventory=inv,bindings=b['bindings'])['errors']]


def test_unresolved_doughnut_hole_size_is_not_guessed():
    m=module();inv=inventory();c=inv['slides'][0]['charts'][0];c['types']=['doughnutChart'];c['plot_types'][0].update(type='doughnutChart',hole_size=None);c['series'][0]['chart_type']='doughnutChart'
    with pytest.raises(m.ChartContractError,match='hole|size'):m.build_chart(inv,c['chart_id'],DATA,series_map=[0])


def test_numeric_style_spellings_are_equivalent():
    m=module()
    inv=inventory();b=m.build_chart(inv,'slide-01:element-10:r0',DATA,series_map=[0]);same=b['xml'].replace('gapWidth="72"','gapWidth="72.0"').replace('overlap="0"','overlap="0.0"')
    assert m.validate_chart_contract(slide(same),b['contract'],inventory=inv,bindings=b['bindings'])['ok']


def test_contract_retains_complete_source_catalogue_without_requiring_every_chart_on_the_page():
    m=module();inv=inventory();b=m.build_chart(inv,'slide-01:element-10:r0',DATA,series_map=[0])
    assert b['contract']['source_chart_ids']==['slide-01:element-10:r0','slide-01:element-11:r1','slide-01:element-12:r2','slide-01:element-13:r3','slide-01:element-14:r4','slide-01:element-15:r5']
    assert len(b['contract']['charts'])==1
    bad=copy.deepcopy(b['contract']);bad['source_chart_ids']=bad['source_chart_ids'][:1]
    assert 'source_catalog_mismatch' in [e['code'] for e in m.validate_chart_contract(slide(b['xml']),bad,inventory=inv,bindings=b['bindings'])['errors']]


def test_hidden_stacked_baseline_points_are_operator_range_limitations_not_missing_source_colors():
    m=module();inv=inventory();c=inv['slides'][0]['charts'][0];c['plot_types'][0]['grouping']='stacked'
    c['series'][0]['point_overrides'][0].update(colors=[],appearance={'fill':'none','line':'none'})
    with pytest.raises(m.ChartContractError) as error:m.build_chart(inv,c['chart_id'],DATA,series_map=[0])
    assert error.value.code=='unsupported_source_range' and 'column' in error.value.alternatives


def test_source_ooxml_rendering_semantics_are_kept_in_the_native_fragment():
    m=module();inv=inventory();b=m.build_chart(inv,'slide-01:element-10:r0',DATA,series_map=[0])
    assert ET.fromstring(b['xml']).get('ooxml')=='true'
    changed=b['xml'].replace(' ooxml="true"','')
    assert 'source_chart_config_mismatch' in [e['code'] for e in m.validate_chart_contract(slide(changed),b['contract'],inventory=inv,bindings=b['bindings'])['errors']]


def test_mixed_plot_stack_cannot_be_silently_applied_as_one_global_stack():
    m=module();inv=inventory();c=inv['slides'][0]['charts'][0];c['types']=['barChart','lineChart'];c['plot_types'][0]['grouping']='stacked'
    c['plot_types'].append({'type':'lineChart','grouping':'standard','axis_ids':['x','y']});c['series'][0]['point_overrides']=[]
    other=copy.deepcopy(c['series'][0]);other.update(chart_type='lineChart',index='1',colors=[color('#9D51D4','line')],appearance={'line':'solidFill'});c['series'].append(other)
    data={'categories':['Q1','Q2'],'series':[{'name':'规模','values':[10,20]},{'name':'增长','values':[1,2]}],'kind':'combo'}
    with pytest.raises(m.ChartContractError,match='stack|堆叠'):m.build_chart(inv,c['chart_id'],data,series_map=[0,1])


def test_inventory_exposes_structure_only_bar_pie_fields():
    sys.path.insert(0,str(SCRIPTS));from scripts.template.template_chart_inventory import parse_chart
    c='http://schemas.openxmlformats.org/drawingml/2006/chart'
    root=ET.fromstring(f'<c:chartSpace xmlns:c="{c}"><c:chart><c:plotArea><c:barChart><c:gapWidth val="72"/><c:overlap val="30"/><c:ser><c:idx val="0"/><c:val><c:numLit><c:ptCount val="3"/><c:pt idx="0"><c:v>987654321</c:v></c:pt></c:numLit></c:val></c:ser></c:barChart><c:doughnutChart><c:holeSize val="60"/><c:firstSliceAng val="45"/></c:doughnutChart></c:plotArea></c:chart></c:chartSpace>')
    got=parse_chart(root)
    assert got['plot_types'][0]['gap_width']=='72' and got['plot_types'][0]['overlap']=='30'
    assert got['plot_types'][1]['hole_size']=='60' and got['plot_types'][1]['first_slice_angle']=='45'
    assert got['series'][0]['point_count']==3 and '987654321' not in json.dumps(got)


@pytest.mark.skipif(not os.environ.get('PPT_TEST_MCKINSEY_TEMPLATE'),reason='real local source supplied for integration verification')
def test_real_source_all_34_ids_are_preserved_and_common_facets_use_source_blues():
    m=module();sys.path.insert(0,str(SCRIPTS));from scripts.template.template_chart_inventory import inventory as read_inventory
    inv=read_inventory(os.environ['PPT_TEST_MCKINSEY_TEMPLATE']);assert inv['total_charts']==34
    group=inv['slides'][3]['small_multiple_groups'][0]
    data={'categories':['2024','2025'],'series':[{'name':n,'values':[10+i,20+i]} for i,n in enumerate(['社区店','标准店','旗舰店'])]}
    panels=[{'data':data,'series_map':[{'series':0,'color_point':i} for i in (1,2,3)]} for _ in range(6)]
    b=m.build_group(inv,group['group_id'],panels,bbox={'left':300,'top':130,'width':600,'height':360},adaptation_reason='六个城市替代源十个分面，三店型用源青蓝紫点色映射为系列；保留2x5规律')
    assert len(b['contract']['source_chart_ids'])==34
    assert len(b['contract']['groups'][0]['source_chart_ids'])==10
    assert 'rgb(36,81,255)' in b['xml'] and 'rgb(157,81,212)' in b['xml'] and 'rgb(211,9,50)' not in b['xml']
    assert m.validate_chart_contract(slide(b['xml']),b['contract'],inventory=inv,bindings=b['bindings'])['ok']


def _readability_panels(values):
    return [{'data': {'categories': ['2025'], 'series': [{'name': 'EBITDA率', 'values': [value]}]},
             'series_map': [{'series': 0, 'color_point': 1}]} for value in values]


def test_shared_axis_uses_only_new_panel_values_and_same_format_without_rescaling():
    m=module(); inv=inventory(); before=copy.deepcopy(inv)
    for c in inv['slides'][0]['charts']:
        c['axes'][1].update(deleted=True, tick_label_position='none', number_format=';;;')
    panels=_readability_panels([21.4,21.6,21.1,11.8])
    built=m.build_group(inv,'slide-01-charts-1',panels,
                        value_axis={'shared':True,'include_zero':True,'format':'0.0"%"'},
                        adaptation_reason='同一单店利润率分面必须共用零基线及刻度')
    roots=list(ET.fromstring('<data>'+built['xml']+'</data>'))
    for root in roots:
        axis=root.find('chartPlotArea/chartAxes/chartAxis[@type="y"]')
        assert (axis.get('min'),axis.get('max'))==('0','22')
        assert axis.find('chartLabel').get('format')=='0.0"%"'
        assert axis.find('chartLabel').get('color')!='rgba(0,0,0,0)'
        assert root.find('.//chartLabels').get('value')=='true'
    assert [m._read_data(r)['series'][0]['values'][0] for r in roots]==[21.4,21.6,21.1,11.8]
    assert m.validate_chart_contract(slide(built['xml']),built['contract'],inventory=inv,bindings=built['bindings'])['ok']
    altered=built['xml'].replace('max="22"','max="12"',1)
    assert 'source_chart_config_mismatch' in [e['code'] for e in m.validate_chart_contract(slide(altered),built['contract'],inventory=inv,bindings=built['bindings'])['errors']]
    assert before['slides'][0]['charts'][0]['series']==inv['slides'][0]['charts'][0]['series']


@pytest.mark.parametrize('values,bounds', [([-1.4454,-3.2],('-4','0')), ([-1.4454,2.6],('-2','3')), ([0,0],('0','1'))])
def test_shared_axis_includes_negative_and_zero_baselines(values,bounds):
    m=module();inv=inventory();built=m.build_group(inv,'slide-01-charts-1',_readability_panels(values),
        value_axis={'shared':True},adaptation_reason='同比百分点按共同零基线比较')
    for root in ET.fromstring('<data>'+built['xml']+'</data>'):
        axis=root.find('.//chartAxis[@type="y"]');assert (axis.get('min'),axis.get('max'))==bounds


def test_shared_stacked_axis_uses_positive_and_negative_stack_totals():
    m=module();inv=inventory()
    for c in inv['slides'][0]['charts']:c['plot_types'][0]['grouping']='stacked'
    data={'categories':['Q1','Q2'],'series':[{'name':'有效会员','values':[10,-4]}, {'name':'其他会员','values':[20,-6]}],
          'legend':{'present':True,'position':'bottom'}}
    panels=[{'data':data,'series_map':[{'series':0,'color_point':0},{'series':0,'color_point':1}]} for _ in range(2)]
    built=m.build_group(inv,'slide-01-charts-1',panels,value_axis={'shared':True,'format':'0'},adaptation_reason='两系列会员堆叠按总规模共用轴')
    for root in ET.fromstring('<data>'+built['xml']+'</data>'):
        axis=root.find('.//chartAxis[@type="y"]');assert (axis.get('min'),axis.get('max'))==('-10','30')


@pytest.mark.parametrize('axis', [{'min':1,'max':20}, {'min':0,'max':21.6}, {'min':22,'max':0}, {'min':0,'max':22,'include_zero':'yes'}, {'min':float('nan'),'max':22}])
def test_axis_rejects_clipping_noninteger_sml_bounds_or_invalid_request(axis):
    m=module();inv=inventory();data=copy.deepcopy(DATA);data['value_axis']=axis
    with pytest.raises(m.ChartContractError):
        m.build_chart(inv,'slide-01:element-10:r0',data,series_map=[0],adaptation_reason='显式轴界限必须覆盖数据并符合SML')


def test_explicit_value_format_overrides_hidden_source_ticks_and_contract_checks_labels():
    m=module();inv=inventory();c=inv['slides'][0]['charts'][0]
    c['axes'][1].update(deleted=True,tick_label_position='none',number_format=';;;')
    data=copy.deepcopy(DATA);data.update(value_format='0.0"%"',legend={'present':False})
    built=m.build_chart(inv,c['chart_id'],data,series_map=[0],adaptation_reason='新任务需要可查数值和城市身份')
    root=ET.fromstring(built['xml']);axis=root.find('.//chartAxis[@type="y"]')
    assert axis.find('chartLabel').get('format')=='0.0"%"'
    assert axis.find('chartLabel').get('color')!='rgba(0,0,0,0)'
    assert root.find('.//chartAxis[@type="x"]/chartLabel').get('format')!=';;;'
    labels=root.findall('.//chartLabels');assert len(labels)==2 and all(l.get('value')=='true' for l in labels)
    labels[-1].set('value','false')
    report=m.validate_chart_contract(slide(ET.tostring(root,encoding='unicode')),built['contract'],inventory=inv,bindings=built['bindings'])
    assert 'chart_readability_mismatch' in [e['code'] for e in report['errors']]


def test_multi_series_stack_requires_legend_or_explicit_series_labels_but_single_series_does_not():
    m=module();inv=inventory();c=inv['slides'][0]['charts'][0];c['plot_types'][0]['grouping']='stacked';c['legend']={'present':False}
    data={'categories':['2025'],'series':[{'name':'有效会员','values':[20]},{'name':'其他会员','values':[10]}]}
    mapping=[{'series':0,'color_point':0},{'series':0,'color_point':1}]
    with pytest.raises(m.ChartContractError) as error:
        m.build_chart(inv,c['chart_id'],data,series_map=mapping,adaptation_reason='新任务是两种会员')
    assert error.value.code=='series_identity_required'
    data['data_labels']={'value':True,'series':True,'format':'0','position':'inside'}
    built=m.build_chart(inv,c['chart_id'],data,series_map=mapping,adaptation_reason='会员身份直接放在对应堆叠分段内')
    labels=ET.fromstring(built['xml']).findall('.//chartLabels');assert len(labels)==3 and all(l.get('series')=='true' for l in labels)
    assert m.validate_chart_contract(slide(built['xml']),built['contract'],inventory=inv,bindings=built['bindings'])['ok']
    plain=copy.deepcopy(DATA);plain['legend']={'present':False}
    single=m.build_chart(inv,c['chart_id'],plain,series_map=[0],adaptation_reason='单系列城市比较用分类名识别，无需图例')
    assert ET.fromstring(single['xml']).find('chartLegend') is None


def test_shared_axis_contract_rejects_independently_rebuilt_panel_bounds():
    m=module();inv=inventory();built=m.build_group(inv,'slide-01-charts-1',_readability_panels([21.6,11.8]),
        value_axis={'shared':True,'format':'0.0"%"'},adaptation_reason='同指标共同尺度')
    altered=copy.deepcopy(built['contract']);record=altered['charts'][1];record['new_data']['value_axis']['max']=12
    record['new_data_sha256']=m._digest(record['new_data'])
    xml=built['xml'];roots=list(ET.fromstring('<data>'+xml+'</data>'));roots[1].find('.//chartAxis[@type="y"]').set('max','12')
    report=m.validate_chart_contract(slide(''.join(ET.tostring(r,encoding='unicode') for r in roots)),altered,inventory=inv,bindings=built['bindings'])
    assert 'shared_value_axis_mismatch' in [e['code'] for e in report['errors']]


def test_group_explicit_bounds_and_format_reach_every_panel_and_native_sml_schema():
    m=module();inv=inventory();built=m.build_group(inv,'slide-01-charts-1',_readability_panels([21.6,11.8]),
        value_axis={'min':0,'max':25,'format':'0.0"%"'},adaptation_reason='固定0至25刻度比较利润率')
    sys.path.insert(0,str(SCRIPTS));import sxsd_validator
    xml='<slide xmlns="'+m.SML+'"><data>'+built['xml']+'</data></slide>'
    assert sxsd_validator.validate_sxsd(ET.fromstring(xml),SCRIPTS.parent/'references/xml/slides_xml_schema_definition.xml')==[]
    for root in ET.fromstring('<data>'+built['xml']+'</data>'):
        axis=root.find('.//chartAxis[@type="y"]');assert (axis.get('min'),axis.get('max'))==('0','25')
    etree=pytest.importorskip('lxml.etree');xsd=etree.XMLSchema(etree.parse(str(SCRIPTS.parent/'references/xml/slides_xml_schema_definition.xml')))
    full='<presentation xmlns="'+m.SML+'" width="720" height="540">'+xml.replace(' xmlns="'+m.SML+'"','')+'</presentation>'
    assert xsd.validate(etree.fromstring(full.encode())),str(xsd.error_log)


def test_explicit_axis_requires_real_source_value_axis_metadata():
    m=module();inv=inventory();inv['slides'][0]['charts'][0]['axes']=[]
    data=copy.deepcopy(DATA);data['value_axis']={'min':0,'max':100}
    with pytest.raises(m.ChartContractError) as error:
        m.build_chart(inv,'slide-01:element-10:r0',data,series_map=[0],adaptation_reason='轴界限不可静默丢弃')
    assert error.value.code=='unsupported_operator_axis'


def test_group_cli_accepts_shared_axis_request(tmp_path,capsys):
    m=module();inv_path=tmp_path/'inventory.json';data_path=tmp_path/'panels.json'
    inv_path.write_text(json.dumps(inventory()));data_path.write_text(json.dumps(_readability_panels([21.6,11.8])))
    result=m.main(['--inventory',str(inv_path),'--group-id','slide-01-charts-1','--data',str(data_path),
        '--value-axis','{"shared":true,"format":"0.0\\\"%\\\""}','--reason','同指标共同零基线',
        '--output',str(tmp_path/'fragment.xml'),'--contract-output',str(tmp_path/'contract.json'),'--bindings-output',str(tmp_path/'bindings.json')])
    assert result==0
    assert 'min="0"' in (tmp_path/'fragment.xml').read_text() and 'max="22"' in (tmp_path/'fragment.xml').read_text()


@pytest.mark.skipif(not os.environ.get('PPT_TEST_MCKINSEY_TEMPLATE'),reason='real local source supplied for operator-boundary verification')
def test_full_source_operator_boundary_is_21_supported_and_13_unsupported_with_readability_settings():
    m=module();sys.path.insert(0,str(SCRIPTS));from scripts.template.template_chart_inventory import inventory as read_inventory
    inv=read_inventory(os.environ['PPT_TEST_MCKINSEY_TEMPLATE']);supported=[];unsupported=[]
    for slide_record in inv['slides']:
        for source in slide_record['charts']:
            kinds=source['types'];data={'categories':['NEW_A','NEW_B','NEW_C','NEW_D'],
                'series':[{'name':'NEW_'+str(n),'values':[10+n,20+n,30+n,40+n]} for n in range(len(source['series']))],
                'legend':{'present':True,'position':'bottom'},'value_format':'0', 'kind':'combo' if len(kinds)>1 else 'categorical'}
            mapping=[{'series':n,'color_point':int(s['point_overrides'][0]['index'])} if s.get('point_overrides') else n for n,s in enumerate(source['series'])]
            try:
                built=m.build_chart(inv,source['chart_id'],data,series_map=mapping,adaptation_reason='用明确新任务数据与图例验证operator能力边界')
                assert len(built['contract']['source_chart_ids'])==34
                assert 'NEW_A' in built['xml'] and 'NEW_0' in built['xml']
                assert m.validate_chart_contract(slide(built['xml']),built['contract'],inventory=inv,bindings=built['bindings'])['ok']
                supported.append(source['chart_id'])
            except m.ChartContractError as error:unsupported.append((source['chart_id'],error.code))
    assert len(supported)==21 and len(unsupported)==13
    assert all(code in ('unsupported_source_range','unsupported_source_type') for _,code in unsupported)


def test_inside_stack_series_identity_chooses_visible_text_for_dark_and_light_source_fills():
    m=module();inv=inventory();c=inv['slides'][0]['charts'][0];c['plot_types'][0]['grouping']='stacked';c['legend']={'present':False}
    c['series'][0]['colors']=[color('#011C2D')];c['series'][0]['point_overrides']=[]
    other=copy.deepcopy(c['series'][0]);other['colors']=[color('#8DC6FF')];c['series'].append(other)
    data={'categories':['2025'],'series':[{'name':'有效会员','values':[20]},{'name':'其他会员','values':[10]}],
          'data_labels':{'value':True,'series':True,'position':'inside','format':'0'}}
    built=m.build_chart(inv,c['chart_id'],data,series_map=[0,1],adaptation_reason='对应源深浅蓝分段需要直接辨识会员身份')
    root=ET.fromstring(built['xml']);labels=root.findall('.//chartSeries/chartLabels')
    assert [label.get('color') for label in labels]==['rgb(255,255,255)','rgb(31,35,41)']
    assert m.validate_chart_contract(slide(built['xml']),built['contract'],inventory=inv,bindings=built['bindings'])['ok']
    data['data_labels']['color']='rgb(255,255,255)'
    explicit=m.build_chart(inv,c['chart_id'],data,series_map=[0,1],adaptation_reason='页面明确要求白色分段标签')
    assert all(label.get('color')=='rgb(255,255,255)' for label in ET.fromstring(explicit['xml']).findall('.//chartSeries/chartLabels'))


def test_new_task_can_explicitly_set_visible_axis_and_legend_text_on_dark_pages():
    m=module();inv=inventory();data=copy.deepcopy(DATA)
    data.update(value_axis={'min':0,'max':100,'format':'0.0"%"','label_color':'rgb(255,255,255)'},
                legend={'present':True,'position':'bottom','color':'rgb(255,255,255)'})
    built=m.build_chart(inv,'slide-01:element-10:r0',data,series_map=[0],adaptation_reason='暗色页面使用明确白色数值刻度与系列图例')
    root=ET.fromstring(built['xml']);assert root.find('.//chartAxis[@type="y"]/chartLabel').get('color')=='rgb(255,255,255)'
    assert root.find('chartLegend').get('color')=='rgb(255,255,255)'
    assert m.validate_chart_contract(slide(built['xml']),built['contract'],inventory=inv,bindings=built['bindings'])['ok']


def _combo_label_fixture(first_kind='areaChart'):
    inv=inventory();c=inv['slides'][0]['charts'][0];c['types']=[first_kind,'lineChart']
    c['plot_types']=[{'type':first_kind,'grouping':'standard','bar_direction':'col','axis_ids':['x','y'],'smooth':False},
                     {'type':'lineChart','grouping':'standard','axis_ids':['x','y'],'smooth':False}]
    c['series'][0].update(chart_type=first_kind,point_overrides=[],appearance={'fill':'solidFill'},colors=[color('#81D5F7')])
    line=copy.deepcopy(c['series'][0]);line.update(chart_type='lineChart',index='1',order='1',appearance={'line':'solidFill'},colors=[color('#011C2D','line')],marker={'symbol':'none'})
    c['series'].append(line);c['axes'][1].update(deleted=True,tick_label_position='none',number_format=';;;')
    data={'categories':['Q1','Q2','Q3','Q4'], 'kind':'combo',
          'series':[{'name':'参考期','values':[18.8,20.1,19.7,18.4]}, {'name':'当前期','values':[17.8,17.5,17.4,16.5]}]}
    return inv,c,data


def test_combo_series_labels_select_current_values_without_global_fallback_or_data_changes():
    m=module();inv,c,data=_combo_label_fixture();before=copy.deepcopy(data)
    data.update(value_format='0.0"%"',data_labels={'value':True,'position':'auto'},legend={'present':True,'position':'bottom'})
    data['series'][0]['data_labels']=False
    data['series'][1]['data_labels']={'value':True,'position':'auto','format':'0.0"%"'}
    built=m.build_chart(inv,c['chart_id'],data,series_map=[0,1],adaptation_reason='参考面积保留，当前折线显示值，避免重叠标签')
    root=ET.fromstring(built['xml']);plot=root.find('chartPlotArea/chartPlot');series=plot.findall('chartSeriesList/chartSeries')
    assert plot.find('chartLabels') is None
    assert series[0].find('chartLabels') is None
    assert series[1].find('chartLabels').get('format')=='0.0"%"'
    assert series[1].find('chartLabels').get('value')=='true'
    assert [s.get('comboType') for s in series]==['area','line']
    assert m._read_data(root)['series']==before['series']
    tick=root.find('.//chartAxis[@type="y"]/chartLabel');assert tick.get('format')=='0.0"%"' and tick.get('color')!='rgba(0,0,0,0)'
    assert m.validate_chart_contract(slide(built['xml']),built['contract'],inventory=inv,bindings=built['bindings'])['ok']
    ET.SubElement(series[0],'chartLabels',{'value':'true','format':'0.0"%"'})
    assert 'chart_readability_mismatch' in [e['code'] for e in m.validate_chart_contract(slide(ET.tostring(root,encoding='unicode')),built['contract'],inventory=inv,bindings=built['bindings'])['errors']]


def test_series_label_positions_follow_each_source_plot_role():
    m=module();inv,c,data=_combo_label_fixture('barChart');data['value_format']='0.0"%"'
    data['series'][0]['data_labels']={'position':'outside','value':True}
    data['series'][1]['data_labels']={'position':'auto','value':True}
    built=m.build_chart(inv,c['chart_id'],data,series_map=[0,1],adaptation_reason='柱值在柱外，线值用自动位置')
    assert [label.get('position') for label in ET.fromstring(built['xml']).findall('.//chartSeries/chartLabels')]==['outside','auto']
    assert m.validate_chart_contract(slide(built['xml']),built['contract'],inventory=inv,bindings=built['bindings'])['ok']
    data['series'][1]['data_labels']={'position':'inside','value':True}
    with pytest.raises(m.ChartContractError) as error:
        m.build_chart(inv,c['chart_id'],data,series_map=[0,1],adaptation_reason='原生线标签不能套柱内位置')
    assert error.value.code=='unsupported_operator_label_position'


def test_disabling_all_series_labels_requires_explicit_readable_value_ticks():
    m=module();inv,c,data=_combo_label_fixture()
    for s in data['series']:s['data_labels']=False
    with pytest.raises(m.ChartContractError) as error:
        m.build_chart(inv,c['chart_id'],data,series_map=[0,1],adaptation_reason='不能关掉所有查数入口')
    assert error.value.code=='chart_readability_required'
    data['value_format']='0.0"%"'
    built=m.build_chart(inv,c['chart_id'],data,series_map=[0,1],adaptation_reason='两期线面保留，以数值刻度查数，避免标签叠')
    assert not ET.fromstring(built['xml']).findall('.//chartLabels')
    assert ET.fromstring(built['xml']).find('.//chartAxis[@type="y"]/chartLabel').get('format')=='0.0"%"'
    assert m.validate_chart_contract(slide(built['xml']),built['contract'],inventory=inv,bindings=built['bindings'])['ok']
    c['axes']=[]
    with pytest.raises(m.ChartContractError) as error:
        m.build_chart(inv,c['chart_id'],data,series_map=[0,1],adaptation_reason='没有实际值轴时不能关掉数值标签')
    assert error.value.code=='chart_readability_required'


def test_series_only_label_configuration_requires_reason_and_restores_ticks():
    m=module();inv,c,data=_combo_label_fixture();data['series'][0]['data_labels']=False;data['series'][1]['data_labels']={'format':'0.0"%"'}
    with pytest.raises(m.ChartContractError) as error:m.build_chart(inv,c['chart_id'],data,series_map=[0,1])
    assert error.value.code=='adaptation_reason_required'
    built=m.build_chart(inv,c['chart_id'],data,series_map=[0,1],adaptation_reason='只显示当前期标签并恢复数值刻度')
    assert ET.fromstring(built['xml']).find('.//chartAxis[@type="y"]/chartLabel').get('format')=='General'
    assert m.validate_chart_contract(slide(built['xml']),built['contract'],inventory=inv,bindings=built['bindings'])['ok']


@pytest.mark.parametrize('setting',[True,None,'false',{'value':False},{'format':';;;'}])
def test_series_data_labels_accepts_only_false_or_valid_visible_settings(setting):
    m=module();inv,c,data=_combo_label_fixture();data['series'][0]['data_labels']=setting
    with pytest.raises(m.ChartContractError):m.build_chart(inv,c['chart_id'],data,series_map=[0,1],adaptation_reason='显式系列标签设置必须合法')


def test_selective_combo_labels_pass_native_sml_schema_and_label_semantics():
    m=module();inv,c,data=_combo_label_fixture();data['value_format']='0.0"%"'
    data['series'][0]['data_labels']=False;data['series'][1]['data_labels']={'value':True,'position':'auto'}
    built=m.build_chart(inv,c['chart_id'],data,series_map=[0,1],adaptation_reason='保留线面职责，仅当前系列标签，值轴可查数')
    sys.path.insert(0,str(SCRIPTS));import sxsd_validator,xml_lint
    xml='<slide xmlns="'+m.SML+'"><data>'+built['xml']+'</data></slide>';root=ET.fromstring(xml)
    assert sxsd_validator.validate_sxsd(root,SCRIPTS.parent/'references/xml/slides_xml_schema_definition.xml')==[]
    assert xml_lint.validate_chart_value_semantics(root)==[]
    etree=pytest.importorskip('lxml.etree');xsd=etree.XMLSchema(etree.parse(str(SCRIPTS.parent/'references/xml/slides_xml_schema_definition.xml')))
    full='<presentation xmlns="'+m.SML+'" width="720" height="540">'+xml.replace(' xmlns="'+m.SML+'"','')+'</presentation>'
    assert xsd.validate(etree.fromstring(full.encode())),str(xsd.error_log)
    assert root.find('.//{'+m.SML+'}chartArea').get('color')=='rgb(129,213,247)'
    assert root.find('.//{'+m.SML+'}chartLine').get('color')=='rgb(1,28,45)'


def test_selective_labels_leave_unconfigured_series_global_policy_and_check_settings_digest():
    m=module();inv,c,data=_combo_label_fixture();data.update(value_format='0.0"%"',data_labels={'font_size':11,'position':'auto'})
    data['series'][0]['data_labels']=False
    built=m.build_chart(inv,c['chart_id'],data,series_map=[0,1],adaptation_reason='参考系列关标签，当前继承明确全局标签配置')
    root=ET.fromstring(built['xml']);assert root.find('.//chartPlot/chartLabels') is None
    assert root.find('.//chartSeries[@index="1"]/chartLabels') is None
    assert root.find('.//chartSeries[@index="2"]/chartLabels').get('fontSize')=='11'
    changed=copy.deepcopy(built['contract']);changed['charts'][0]['new_data']['series'][0]['data_labels']={'value':True}
    report=m.validate_chart_contract(slide(built['xml']),changed,inventory=inv,bindings=built['bindings'])
    assert 'new_data_contract_mismatch' in [e['code'] for e in report['errors']]


@pytest.mark.skipif(not os.environ.get('PPT_TEST_MCKINSEY_TEMPLATE'),reason='real local source supplied for hidden-helper boundary verification')
def test_real_source_combo_hidden_line_helper_is_not_replaced_with_fake_values_or_colors():
    m=module();sys.path.insert(0,str(SCRIPTS));from scripts.template.template_chart_inventory import inventory as read_inventory
    inv=read_inventory(os.environ['PPT_TEST_MCKINSEY_TEMPLATE']);source=inv['slides'][1]['charts'][0]
    data={'categories':['NEW_Q1','NEW_Q2'], 'kind':'combo', 'value_format':'0.0"%"',
          'series':[{'name':'参考期','values':[18.8,20.1],'data_labels':False},
                    {'name':'当前期','values':[17.8,17.5],'data_labels':{'value':True,'position':'auto'}}]}
    before=copy.deepcopy(inv)
    with pytest.raises(m.ChartContractError) as error:m.build_chart(inv,source['chart_id'],data,series_map=[0,1],adaptation_reason='保留源线面职责，不能为隐藏helper系列造数据或颜色')
    assert error.value.code=='unsupported_source_range'
    assert inv==before


def test_selective_stacked_series_does_not_use_invalid_native_outside_position():
    m=module();inv=inventory();c=inv['slides'][0]['charts'][0];c['plot_types'][0]['grouping']='stacked'
    data={'categories':['2025'],'series':[{'name':'参考期','values':[20],'data_labels':False},
          {'name':'当前期','values':[10],'data_labels':{'value':True,'position':'outside'}}], 'value_format':'0'}
    with pytest.raises(m.ChartContractError) as error:
        m.build_chart(inv,c['chart_id'],data,series_map=[{'series':0,'color_point':0},{'series':0,'color_point':1}],adaptation_reason='堆叠系列标签只使用原生支持的柱内位置')
    assert error.value.code=='unsupported_operator_label_position'


def _verified_hidden_combo_fixture():
    inv,c,data=_combo_label_fixture();source_helper=c['series'][1]
    source_helper.update(appearance={'line':'none'},colors=[],marker={'symbol':'none'},hidden_duplicate=True,helper_of=0,
                         source_point_layout={'point_count':19,'nonempty_positions':[n for n in range(19) if n not in (3,7,11,15)],'missing_positions':[3,7,11,15],'blank_mode':'gap'})
    data.update(source_gap_policy='continuous_new_data',value_format='0.0"%"',legend={'present':False})
    data['series'][1].update(values=list(data['series'][0]['values']),hidden_duplicate=True,helper_of=0,data_labels=False)
    return inv,c,data


def test_verified_hidden_duplicate_keeps_no_stroke_and_only_supplied_new_area_values():
    m=module();inv,c,data=_verified_hidden_combo_fixture();before=copy.deepcopy(inv)
    built=m.build_chart(inv,c['chart_id'],data,series_map=[0,1],adaptation_reason='本题连续季度数据替代原分段类别，无需断组；隐形重复系列仅沿用新面积值')
    root=ET.fromstring(built['xml']);series=root.findall('.//chartSeries');helper=series[1]
    assert helper.find('chartLine').get('color')=='rgba(0,0,0,0)'
    assert helper.find('chartPoints').get('size')=='0' and helper.find('chartPoints').get('color')=='rgba(0,0,0,0)'
    assert helper.find('chartLabels') is None
    assert m._read_data(root)['series'][0]['values']==m._read_data(root)['series'][1]['values']==[18.8,20.1,19.7,18.4]
    assert [n.get('value') for n in root.findall('chartStyle/chartColorTheme/color')]==['rgb(129,213,247)']
    assert m.validate_chart_contract(slide(built['xml']),built['contract'],inventory=inv,bindings=built['bindings'])['ok']
    assert inv==before
    tampered=built['xml'].replace('rgba(0,0,0,0)','rgb(129,213,247)',1)
    assert 'source_palette_mismatch' in [e['code'] for e in m.validate_chart_contract(slide(tampered),built['contract'],inventory=inv,bindings=built['bindings'])['errors']]


@pytest.mark.parametrize('change', ['independent_values','wrong_helper_of','no_declaration','unverified_source','visible_labels'])
def test_hidden_helper_cannot_hide_independent_new_data_or_unverified_source(change):
    m=module();inv,c,data=_verified_hidden_combo_fixture()
    if change=='independent_values':data['series'][1]['values'][0]=17.8
    if change=='wrong_helper_of':data['series'][1]['helper_of']=1
    if change=='no_declaration':data['series'][1].pop('hidden_duplicate');data['series'][1].pop('helper_of')
    if change=='unverified_source':c['series'][1].pop('hidden_duplicate')
    if change=='visible_labels':data['series'][1]['data_labels']={'value':True}
    with pytest.raises(m.ChartContractError):m.build_chart(inv,c['chart_id'],data,series_map=[0,1],adaptation_reason='只允许源已验证的隐形重复职责')


def test_source_segment_gap_fidelity_remains_explicitly_unsupported_without_continuous_adaptation():
    m=module();inv,c,data=_verified_hidden_combo_fixture();data['source_gap_policy']='preserve'
    with pytest.raises(m.ChartContractError) as error:m.build_chart(inv,c['chart_id'],data,series_map=[0,1],adaptation_reason='要求完整保留原五段缺点结构')
    assert error.value.code=='unsupported_operator_gaps'
    data.pop('source_gap_policy')
    with pytest.raises(m.ChartContractError) as error:m.build_chart(inv,c['chart_id'],data,series_map=[0,1],adaptation_reason='不能默默改变原分段职责')
    assert error.value.code=='unsupported_operator_gaps'
    data['source_gap_policy']='continuous_new_data';data['series'][0]['values'][0]=None;data['series'][1]['values'][0]=None
    with pytest.raises(m.ChartContractError):m.build_chart(inv,c['chart_id'],data,series_map=[0,1],adaptation_reason='缺值不可填零')


@pytest.mark.skipif(not os.environ.get('PPT_TEST_MCKINSEY_TEMPLATE'),reason='real source supplied for focused hidden-duplicate integration')
def test_real_source_three_row_area_group_supports_explicit_continuous_new_data():
    m=module();sys.path.insert(0,str(SCRIPTS));from scripts.template.template_chart_inventory import inventory as read_inventory
    inv=read_inventory(os.environ['PPT_TEST_MCKINSEY_TEMPLATE']);group=inv['slides'][1]['small_multiple_groups'][0]
    panels=[]
    for name,values,fmt in [('季末门店',[240,247,241,266,266,271,283,295],'0'),
                            ('季末会员',[309692,313199,304826,355085,360126,391554,410825,444691],'#,##0'),
                            ('单店率',[19.8,19.9,19.6,18.8,18.5,18.1,17.0,17.2],'0.0"%"')]:
        panels.append({'data':{'categories':[f'NEW_Q{i+1}' for i in range(8)],'kind':'combo','value_format':fmt,
                              'source_gap_policy':'continuous_new_data','legend':{'present':False},
                              'series':[{'name':name,'values':values}, {'name':name+'隐形重复','values':list(values),'hidden_duplicate':True,'helper_of':0,'data_labels':False}]},
                       'series_map':[0,1]})
    built=m.build_group(inv,group['group_id'],panels,adaptation_reason='新连续8季度替代源5组分段类别，无需断组；隐形重复仅镜像本题面积值，保留源三行规律与青色色系')
    charts=list(ET.fromstring('<data>'+built['xml']+'</data>'));assert len(charts)==3
    assert group['rows']==3 and group['columns']==1
    assert max(float(chart.get('topLeftX')) for chart in charts)-min(float(chart.get('topLeftX')) for chart in charts)<2
    assert len({chart.get('topLeftY') for chart in charts})==3
    for chart,panel in zip(charts,panels):
        assert chart.find('.//chartPlot').get('type')=='combo'
        assert [s.get('comboType') for s in chart.findall('.//chartSeries')]==['area','line']
        assert chart.find('.//chartArea').get('color')=='rgb(88,215,254)'
        assert chart.find('.//chartLine').get('color')=='rgba(0,0,0,0)'
        assert m._read_data(chart)['series'][0]['values']==m._read_data(chart)['series'][1]['values']==panel['data']['series'][0]['values']
    assert m.validate_chart_contract(slide(built['xml']),built['contract'],inventory=inv,bindings=built['bindings'])['ok']
    import sxsd_validator,xml_lint
    root=ET.fromstring('<slide xmlns="'+m.SML+'"><data>'+built['xml']+'</data></slide>')
    assert sxsd_validator.validate_sxsd(root,SCRIPTS.parent/'references/xml/slides_xml_schema_definition.xml')==[]
    assert xml_lint.validate_chart_value_semantics(root)==[]


@pytest.mark.skipif(not os.environ.get('PPT_TEST_MCKINSEY_TEMPLATE'),reason='real source supplied for updated operator capability profile')
def test_real_source_explicit_hidden_duplicate_profile_is_24_supported_10_unsupported():
    m=module();sys.path.insert(0,str(SCRIPTS));from scripts.template.template_chart_inventory import inventory as read_inventory
    inv=read_inventory(os.environ['PPT_TEST_MCKINSEY_TEMPLATE']);supported=[];unsupported=[]
    for slide_record in inv['slides']:
        for source in slide_record['charts']:
            data={'categories':['NEW_Q1','NEW_Q2','NEW_Q3','NEW_Q4'], 'kind':'combo' if len(source['types'])>1 else 'categorical',
                  'value_format':'0','legend':{'present':True,'position':'bottom'},
                  'series':[{'name':'NEW_'+str(n),'values':[10+n,20+n,30+n,40+n]} for n in range(len(source['series']))]}
            mapping=[{'series':n,'color_point':int(s['point_overrides'][0]['index'])} if s.get('point_overrides') else n for n,s in enumerate(source['series'])]
            for n,s in enumerate(source['series']):
                if s.get('hidden_duplicate'):
                    data['series'][n].update(hidden_duplicate=True,helper_of=s['helper_of'],data_labels=False,values=list(data['series'][s['helper_of']]['values']))
                    data['source_gap_policy']='continuous_new_data'
                    data['legend']={'present':False}
            try:
                b=m.build_chart(inv,source['chart_id'],data,series_map=mapping,adaptation_reason='连续本题数据替代源分段类目；已验证隐形重复只镜像对应新面积值，不保留原五段gap')
                assert m.validate_chart_contract(slide(b['xml']),b['contract'],inventory=inv,bindings=b['bindings'])['ok']
                supported.append(source['chart_id'])
            except m.ChartContractError as error:unsupported.append((source['chart_id'],error.code))
    assert len(supported)==24 and len(unsupported)==10
    assert all(code in ('unsupported_source_range','unsupported_source_type') for _,code in unsupported)


def test_hidden_duplicate_cannot_surface_as_an_extra_legend_series():
    m=module();inv,c,data=_verified_hidden_combo_fixture();data['legend']={'present':True,'position':'bottom'}
    with pytest.raises(m.ChartContractError) as error:
        m.build_chart(inv,c['chart_id'],data,series_map=[0,1],adaptation_reason='helper不能作为额外经营指标显示到图例')
    assert error.value.code=='unsupported_operator_legend'
