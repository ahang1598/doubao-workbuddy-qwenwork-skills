import importlib.util
from pathlib import Path
import unittest

SCRIPT=Path(__file__).resolve().parents[1]/ 'template' / 'template_metrics.py'

class MetricTests(unittest.TestCase):
    def api(self):
        if not SCRIPT.exists():self.fail('Metric formatting/comparison helper not implemented')
        spec=importlib.util.spec_from_file_location('metrics_test_api',SCRIPT)
        api=importlib.util.module_from_spec(spec);spec.loader.exec_module(api);return api

    def test_response_percentage_keeps_percentage_unit(self):
        api=self.api()
        self.assertEqual(api.format_metric(70,unit='percent',scale='percent',digits=0),'70%')
        self.assertEqual(api.format_metric(.70,unit='percent',scale='fraction',digits=0),'70%')
        self.assertEqual(api.format_metric(70,unit='score',digits=0),'70分')

    def test_twelve_to_twenty_is_not_doubling(self):
        result=self.api().compare_values(12,20)
        self.assertFalse(result['doubled'])
        self.assertAlmostEqual(result['relative_change_pct'],66.6666666667)
        self.assertEqual(result['delta'],8)

    def test_column_leader_has_real_exception(self):
        result=self.api().matrix_extrema(['家具','厨房','运动'],['信息','价格','售后','帮助','总体'],
            [[70,65,63,74,72],[78,73,68,80,77],[75,70,72,77,75]])
        self.assertEqual(result['all_column_leaders'],[])
        self.assertEqual(result['columns'][2]['max_rows'],['运动'])
        self.assertEqual(result['rows'][2]['min_columns'],['价格'])

    def test_zero_baseline_does_not_invent_growth_percentage(self):
        result=self.api().compare_values(0,8)
        self.assertIsNone(result['relative_change_pct'])
        self.assertIsNone(result['ratio'])

if __name__=='__main__':unittest.main()
