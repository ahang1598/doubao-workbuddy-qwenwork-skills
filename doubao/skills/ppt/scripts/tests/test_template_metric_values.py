import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from lxml import etree as ET

SCRIPTS = Path(os.environ.get('METRIC_VALUES_SCRIPTS', Path(__file__).parents[1]))


def load(name):
    spec = importlib.util.spec_from_file_location('candidate_' + name, SCRIPTS / 'template' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class MetricValuesTests(unittest.TestCase):
    def metric(self, **changes):
        result = {'id': 'points', 'label': '服务点数量', 'kind': 'quantity', 'unit': '个',
                  'scope': '服务网络', 'period': {'before': '年初', 'after': '年末'},
                  'before': 18, 'after': 27, 'digits': 0}
        result.update(changes)
        return result

    def build(self, metrics, **kwargs):
        module = load('template_metrics')
        self.assertTrue(callable(getattr(module, 'build_metric_values', None)),
                        'Shared comparison-values operation is missing')
        return module.build_metric_values({'metrics': metrics, **kwargs})

    def test_quantity_summary_preserves_its_metric_unit_scope_and_period(self):
        result = self.build([self.metric()])
        v = result['values']
        self.assertEqual(v['points.before'], '18个')
        self.assertEqual(v['points.after'], '27个')
        self.assertEqual(v['points.absolute_change'], '+9个')
        self.assertEqual(v['points.relative_change'], '+50.0%')
        self.assertEqual(v['points.direction'], '增加')
        self.assertIn('服务点数量（服务网络，年初→年末）', v['points.summary'])
        self.assertNotIn('覆盖率', v['points.summary'])
        self.assertEqual(result['metrics'][0]['unit'], '个')

    def test_rate_from_numerators_uses_points_and_keeps_appointment_scope(self):
        metric = self.metric(id='attendance', label='到场率', kind='rate', unit='%',
            scope='有效预约次数', period={'before': '第一次观测', 'after': '第二次观测'},
            before={'numerator': 846, 'denominator': 1000},
            after={'numerator': 891, 'denominator': 1000}, digits=1)
        result = self.build([metric])
        v = result['values']
        self.assertEqual(v['attendance.before'], '84.6%')
        self.assertEqual(v['attendance.after'], '89.1%')
        self.assertEqual(v['attendance.percentage_points'], '+4.5个百分点')
        self.assertEqual(v['attendance.relative_change'], '+5.3%')
        self.assertIn('有效预约次数', v['attendance.summary'])
        self.assertNotIn('人', v['attendance.summary'])

    def test_fraction_and_percent_rates_produce_identical_shared_values(self):
        fraction = self.metric(id='rate', label='返工率', kind='rate', unit='%',
            before=.0324, after=.025782155272305908, scale='fraction', digits=2,
            relative_digits=2)
        percent = {**fraction, 'before': 3.24, 'after': 2.5782155272305908, 'scale': 'percent'}
        a, b = self.build([fraction]), self.build([percent])
        self.assertEqual(a['values'], b['values'])
        self.assertEqual(a['values']['rate.percentage_points'], '-0.66个百分点')
        self.assertEqual(a['values']['rate.relative_change'], '-20.43%')
        self.assertEqual(a['values']['rate.direction'], '减少')

    def test_zero_and_missing_endpoints_do_not_become_a_zero_relative_rate(self):
        result = self.build([self.metric(id='zero', before=0, after=8),
                             self.metric(id='missing', before=None, after=8)])
        self.assertEqual(result['values']['zero.relative_change'], '不可算')
        self.assertEqual(result['values']['missing.before'], '未测量')
        self.assertEqual(result['values']['missing.absolute_change'], '不可算')
        self.assertIsNone(result['metrics'][0]['relative_change_pct'])
        self.assertIsNone(result['metrics'][1]['absolute_change'])

    def test_missing_or_zero_rate_denominator_stays_unmeasured(self):
        rate = self.metric(id='rate', kind='rate', unit='%', digits=1,
            before={'numerator': 0, 'denominator': 0},
            after={'numerator': 0, 'denominator': 100})
        result = self.build([rate])
        self.assertEqual(result['values']['rate.before'], '未测量')
        self.assertEqual(result['values']['rate.after'], '0.0%')
        self.assertEqual(result['values']['rate.percentage_points'], '不可算')

    def test_literal_states_copy_exactly_and_group_metadata_separates_units(self):
        a = self.metric(id='nodes', label='计算节点数', unit='个', scope='共享平台')
        b = self.metric(id='projects', label='年支持项目数', unit='项/年', scope='共享平台')
        result = self.build([a, b], literals={'power.status': '备用电源预算尚待批准。'},
            groups=[{'id': 'capacity', 'metrics': ['nodes', 'projects']}])
        self.assertEqual(result['values']['power.status'], '备用电源预算尚待批准。')
        self.assertFalse(result['groups'][0]['same_unit'])
        self.assertFalse(result['groups'][0]['stack_recommended'])
        self.assertEqual(result['groups'][0]['suggested_layout'], 'separate_panels')

    def test_comparable_group_metadata_uses_declared_scope_and_period(self):
        result = self.build([self.metric(id='north'), self.metric(id='south')],
            groups=[{'id': 'regions', 'metrics': ['north', 'south']}])
        self.assertTrue(result['groups'][0]['comparable'])
        self.assertEqual(result['groups'][0]['suggested_layout'], 'shared_axis')

    def test_writer_preserves_exact_source_and_compatible_string_values(self):
        module = load('template_metrics')
        self.assertTrue(callable(getattr(module, 'write_metric_values', None)),
                        'Shared values writer is missing')
        with tempfile.TemporaryDirectory() as name:
            work = Path(name)
            source = work / 'input.json'
            raw = json.dumps({'metrics': [self.metric()],
                'literals': {'state': '待批 & {{原句}}'}}, ensure_ascii=False, indent=3).encode()
            source.write_bytes(raw)
            receipt = module.write_metric_values(source, work / 'values.json')
            self.assertEqual(Path(receipt['source']['snapshot']).read_bytes(), raw)
            self.assertEqual(source.read_bytes(), raw)
            values = json.loads(Path(receipt['values']['path']).read_text())
            self.assertEqual(values['state'], '待批 & {{原句}}')
            self.assertEqual(values['points.after'], '27个')
            self.assertTrue(all(isinstance(v, str) for v in values.values()))
            self.assertEqual(module.write_metric_values(source, work / 'values.json'), receipt)

    def test_declared_metric_unit_is_required_and_rate_scale_is_not_guessed(self):
        module = load('template_metrics')
        self.assertTrue(callable(getattr(module, 'build_metric_values', None)))
        missing = self.metric()
        missing.pop('unit')
        with self.assertRaises(ValueError):
            module.build_metric_values({'metrics': [missing]})
        with self.assertRaises(ValueError):
            module.build_metric_values({'metrics': [self.metric(kind='rate', unit='%', before=.7, after=.8)]})


NS = 'https://www.larkoffice.com/sml/2.0'
XML = ('<slide xmlns="' + NS + '" id="ready"><data>'
       '<shape id="title" type="text" width="300" height="80" path="{{name}}"><content fontFamily="{{name}}">'
       '<p>{{name}}<span bold="true">{{rate}}</span> &amp; {{state}}</p></content></shape>'
       '<table id="facts" topLeftY="100" width="300" height="60"><tr><td><content><p>{{state}}</p></content></td></tr></table>'
       '<img id="picture" src="{{name}}"/>'
       '<chart id="chart"><chartData><field name="{{name}}" value="{{rate}}"/></chartData>'
       '<chartLabels>{{name}}</chartLabels></chart>'
       '</data><note><content><p>{{name}} {{literal}} {plain} {{}}</p></content></note></slide>')


class ReadyValuesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)
        self.source = self.work / 'source.xml'
        self.source.write_text(XML)
        self.original = self.source.read_bytes()
        self.api = load('template_authoring_plan')
        self.values = {'name': '研学 & 中文<计划>', 'rate': '89.1%',
                       'state': '尚待批准', 'literal': '{{unknown_literal}}'}

    def plan(self, **page_changes):
        page = {'page': 1, 'operation': 'ready', 'xml': 'source.xml',
                'link': 'L5', 'mode': 'active_rebuild', **page_changes}
        return {'pages': [page], 'values': self.values}

    def test_ready_opt_in_replaces_text_inline_tail_table_and_notes_once(self):
        result = self.api.prepare_plan(self.plan(apply_values=True), self.work)
        self.assertTrue(result['ok'], result)
        raw = Path(result['pages'][0]['xml_path']).read_bytes()
        root = ET.fromstring(raw)
        paragraph = root.find('.//{*}shape/{*}content/{*}p')
        self.assertEqual(paragraph.text, '研学 & 中文<计划>')
        self.assertEqual(paragraph[0].text, '89.1%')
        self.assertEqual(paragraph[0].tail, ' & 尚待批准')
        self.assertEqual(root.find('.//{*}td/{*}content/{*}p').text, '尚待批准')
        self.assertEqual(root.find('{*}note/{*}content/{*}p').text,
            '研学 & 中文<计划> {{unknown_literal}} {plain} {{}}')
        self.assertIn(b'&amp;', raw)
        self.assertEqual(self.source.read_bytes(), self.original)
        self.assertEqual(json.loads(Path(result['values_snapshot']).read_text()), self.values)
        self.assertEqual(Path(result['pages'][0]['source_snapshots'][0]['snapshot']).read_bytes(), self.original)

    def test_ready_opt_in_leaves_attributes_paths_and_entire_chart_unchanged(self):
        result = self.api.prepare_plan(self.plan(apply_values=True), self.work)
        self.assertTrue(result['ok'])
        root = ET.parse(result['pages'][0]['xml_path']).getroot()
        self.assertEqual(root.find('.//{*}shape').get('path'), '{{name}}')
        self.assertEqual(root.find('.//{*}content').get('fontFamily'), '{{name}}')
        self.assertEqual(root.find('.//{*}img').get('src'), '{{name}}')
        self.assertEqual(root.find('.//{*}field').get('value'), '{{rate}}')
        self.assertEqual(root.find('.//{*}chartLabels').text, '{{name}}')

    def test_ready_native_values_leave_embedded_svg_and_definition_text_unchanged(self):
        svg = 'http://www.w3.org/2000/svg'
        self.source.write_text('<slide xmlns="' + NS + '"><data>'
            '<shape id="native" type="text"><content><p>{{name}}</p></content></shape>'
            '<embed id="vector"><svg xmlns="' + svg + '"><defs><text>{{name}}</text></defs>'
            '<text>{{name}}</text><path d="{{name}}"/></svg></embed>'
            '<defs><shape type="text"><content><p>{{name}}</p></content></shape></defs>'
            '</data><note><content><p>{{name}}</p></content></note></slide>')
        original_root = ET.parse(self.source).getroot()
        result = self.api.prepare_plan(self.plan(apply_values=True), self.work)
        self.assertTrue(result['ok'], result)
        root = ET.parse(result['pages'][0]['xml_path']).getroot()
        self.assertEqual(root.find('.//{*}shape[@id="native"]/{*}content/{*}p').text,
                         '研学 & 中文<计划>')
        self.assertEqual(root.find('{*}note/{*}content/{*}p').text, '研学 & 中文<计划>')
        for tag in ['embed', 'defs']:
            self.assertEqual(ET.tostring(root.find('{*}data/{*}' + tag), with_tail=False),
                ET.tostring(original_root.find('{*}data/{*}' + tag), with_tail=False))

    def test_foreign_text_placeholder_does_not_block_native_values(self):
        self.source.write_text('<slide xmlns="' + NS + '"><data><shape type="text">'
            '<content><p>{{name}}<svg xmlns="http://www.w3.org/2000/svg">'
            '<text>{{foreign_unknown}}</text></svg> tail {{state}}</p></content>'
            '</shape></data></slide>')
        result = self.api.prepare_plan(self.plan(apply_values=True), self.work)
        self.assertTrue(result['ok'], result)
        root = ET.parse(result['pages'][0]['xml_path']).getroot()
        paragraph = root.find('.//{*}shape/{*}content/{*}p')
        self.assertEqual(paragraph.text, '研学 & 中文<计划>')
        self.assertEqual(paragraph[0][0].text, '{{foreign_unknown}}')
        self.assertEqual(paragraph[0].tail, ' tail 尚待批准')

    def test_native_inline_and_comment_tails_substitute_once_in_parent_context(self):
        self.source.write_text('<slide xmlns="' + NS + '"><data><shape type="text">'
            '<content><p>{{name}}<span bold="true">{{rate}}</span> {{state}}'
            '<!-- {{comment_unknown}} --> {{literal}}</p></content></shape></data></slide>')
        result = self.api.prepare_plan(self.plan(apply_values=True), self.work)
        self.assertTrue(result['ok'], result)
        root = ET.parse(result['pages'][0]['xml_path']).getroot()
        paragraph = root.find('.//{*}shape/{*}content/{*}p')
        self.assertEqual(paragraph.text, '研学 & 中文<计划>')
        self.assertEqual(paragraph[0].text, '89.1%')
        self.assertEqual(paragraph[0].tail, ' 尚待批准')
        self.assertEqual(paragraph[1].text, ' {{comment_unknown}} ')
        self.assertEqual(paragraph[1].tail, ' {{unknown_literal}}')

    def test_default_ready_preserves_exact_input_bytes_including_placeholders(self):
        result = self.api.prepare_plan(self.plan(), self.work)
        self.assertTrue(result['ok'])
        self.assertEqual(Path(result['pages'][0]['xml_path']).read_bytes(), self.original)
        self.assertEqual(self.source.read_bytes(), self.original)

    def test_unknown_text_key_stops_before_any_publish_or_output(self):
        self.values.pop('rate')
        calls = []
        def runner(argv, **kwargs):
            calls.append(argv)
            return subprocess.CompletedProcess(argv, 1,
                json.dumps({'ok': False, 'status': 'unexpected_publish'}), '')
        result = self.api.run_plan(self.plan(apply_values=True), self.work, 'deck',
                                  runner=runner)
        self.assertFalse(result['ok'])
        self.assertEqual(result['status'], 'prepare_blocked')
        self.assertIn('Unknown shared value key: rate', result['error'])
        self.assertEqual(calls, [])
        self.assertFalse((self.work / 'authoring/slide-01.xml').exists())

    def test_migration_preserves_source_text_even_with_ready_opt_in_field(self):
        source_root = ET.fromstring(self.original)
        data = source_root.find('{*}data')
        for child in list(data):
            if ET.QName(child).localname in {'img', 'chart'}:
                data.remove(child)
        self.source.write_bytes(ET.tostring(source_root))
        frame = self.work / 'frame.xml'
        frame.write_text('<slide xmlns="' + NS + '"><data><shape id="bg" type="rect" '
            'width="960" height="540"><fill><fillColor color="#fff"/></fill></shape></data></slide>')
        page = {'page': 1, 'operation': 'migration', 'source': 'source.xml', 'frame': 'frame.xml',
                'content_ids': ['title', 'facts'], 'frame_ids': ['bg'], 'target_region': [40, 40, 800, 400],
                'link': 'L8', 'mode': 'component_reuse', 'apply_values': True}
        result = self.api.prepare_plan({'pages': [page], 'values': self.values}, self.work)
        self.assertTrue(result['ok'], result)
        root = ET.parse(result['pages'][0]['xml_path']).getroot()
        self.assertEqual(root.find('.//{*}shape[@id="title"]/{*}content/{*}p').text, '{{name}}')
        self.assertEqual(root.find('{*}note/{*}content/{*}p').text,
                         '{{name}} {{literal}} {plain} {{}}')


if __name__ == '__main__':
    unittest.main(verbosity=2)
