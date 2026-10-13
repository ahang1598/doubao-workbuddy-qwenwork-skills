import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('query_affinity', ROOT / 'scripts/runtime/query-css-library.py')
query = importlib.util.module_from_spec(spec)
spec.loader.exec_module(query)


class StyleAffinityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        base = self.root / 'assets/templates/css'
        base.mkdir(parents=True)
        (base / 'layouts.md').write_text('<a id="one"></a>\n## Layout\n阅读顺序：身份、经历。\n')
        self.data = {'documents': {'layouts': {'path': 'assets/templates/css/layouts.md'}}, 'entries': []}
        for name, level, terms in [('a', 'adaptable', ['手账', '贴纸']), ('b', 'strong', ['手账', '贴纸'])]:
            self.data['entries'].append({
                'id': 'layout.' + name, 'name': '布局 ' + name,
                'document': 'layouts', 'anchor': 'one', 'tags': ['简历'],
                'style_tags': ['通用'], 'artifact_types': ['简历'], 'layout_scope': '整张单屏',
                'style_affinities': [{'style': '手账拼贴风 / 照片剪贴', 'terms': terms,
                                     'level': level, 'reason': '保留事实区；不适合霓虹'}],
                'related_combinations': ['combination.example'],
            })
        self.path = base / 'catalog.json'

    def library(self):
        self.path.write_text(json.dumps(self.data, ensure_ascii=False))
        return query.Library(self.root)

    def test_direct_query_prioritizes_structural_affinity(self):
        result = self.library().search('灰蓝贴纸风简历', kind='layout', artifact='简历', layout_scope='整张单屏')
        first = result['candidates'][0]
        self.assertEqual(first['id'], 'layout.b')
        self.assertEqual(first['style_matches'][0]['level'], 'strong')
        self.assertIn('贴纸', first['style_matches'][0]['matched_terms'])
        self.assertEqual(first['related_combinations'], ['combination.example'])

    def test_style_flag_uses_same_affinity(self):
        result = self.library().search(style='手账拼贴风', kind='layout')
        self.assertEqual(result['candidates'][0]['id'], 'layout.b')
        self.assertTrue(result['candidates'][0]['style_match'])

    def test_color_and_reason_do_not_imply_style(self):
        lib = self.library()
        for text in ['灰蓝 简历', '霓虹 简历']:
            for row in lib.search(text, kind='layout')['candidates']:
                self.assertEqual(row.get('style_matches', []), [])
                self.assertEqual(row['recall_stage'], 'weak')

    def test_hard_filters_survive_affinity(self):
        self.data['entries'][1]['artifact_types'] = ['海报']
        rows = self.library().search('手账', kind='layout', artifact='简历')['candidates']
        self.assertEqual([r['id'] for r in rows], ['layout.a'])

    def test_expansion_is_not_reported_as_direct_match(self):
        for e in self.data['entries']:
            e['style_affinities'][0]['terms'] = ['手账']
        rows = self.library().search('贴纸', kind='layout')['candidates']
        self.assertTrue(rows)
        self.assertTrue(all(r['recall_stage'] == 'expanded' for r in rows))

    def test_alias_repetition_does_not_multiply_style_evidence(self):
        self.data['entries'][1]['style_affinities'][0]['terms'] += ['手账', '贴纸']
        rows = self.library().search('手账 贴纸 手账', kind='layout')['candidates']
        self.assertEqual(len(rows[0]['style_matches']), 1)
        self.assertEqual(set(rows[0]['style_matches'][0]['matched_terms']), {'手账', '贴纸'})

    def test_describe_exposes_affinity_without_implementation(self):
        row = self.library().describe(['layout.b'])['candidates'][0]
        self.assertEqual(row['style_affinities'][0]['level'], 'strong')
        self.assertEqual(row['related_combinations'], ['combination.example'])

    def test_explicit_child_does_not_match_sibling_or_unknown_style(self):
        self.data['entries'][0]['style_affinities'][0]['style'] = '手账拼贴风 / 票据档案'
        lib = self.library()
        rows = lib.search(style='手账拼贴风 / 照片剪贴', kind='layout')['candidates']
        self.assertEqual([r['id'] for r in rows], ['layout.b'])
        self.assertEqual(lib.search(style='不存在的风格', kind='layout')['candidates'], [])

    def test_family_evidence_is_not_multiplied_by_substyles(self):
        e = self.data['entries'][1]
        e['style_affinities'].append(dict(e['style_affinities'][0], style='手账拼贴风 / 票据档案'))
        rows = self.library().search('手账', kind='layout')['candidates']
        self.assertEqual(len(rows[0]['style_matches']), 1)

    def test_direct_fit_precedes_related_style_even_if_related_is_strong(self):
        self.data['entries'][0]['style_affinities'][0]['terms'] = ['贴纸']
        self.data['entries'][1]['style_affinities'][0]['terms'] = ['手账']
        rows = self.library().search('贴纸', kind='layout')['candidates']
        self.assertEqual([r['id'] for r in rows], ['layout.a', 'layout.b'])
        self.assertEqual([r['recall_stage'] for r in rows], ['exact', 'expanded'])

    def test_real_resume_queries_and_metadata(self):
        lib = query.Library(ROOT)
        for text, expected in [
            ('灰蓝贴纸风简历', {'layout.resume-paper-collage', 'layout.resume-profile-header'}),
            ('极简简历', {'layout.resume-narrow-sidebar', 'layout.resume-section-sidebar', 'layout.resume-profile-left'}),
            ('瑞士网格简历', {'layout.resume-editorial-grid'}),
        ]:
            rows = lib.search(text, kind='layout', artifact='简历', layout_scope='整张单屏', limit=3)['candidates']
            self.assertIn(rows[0]['id'], expected, text)
            self.assertTrue(rows[0]['style_matches'])
        layouts = [e for e in lib.entries.values() if e['id'].startswith('layout.resume-')]
        self.assertEqual(len(layouts), 13)
        for e in layouts:
            self.assertEqual(e['style_tags'], ['通用'])
            self.assertTrue(e['style_affinities'])
            for affinity in e['style_affinities']:
                self.assertIn(affinity['level'], ['strong', 'adaptable'])
                self.assertTrue(affinity['reason'])
            for ref in e['related_combinations']:
                self.assertIn(ref, lib.entries)


if __name__ == '__main__':
    unittest.main()
