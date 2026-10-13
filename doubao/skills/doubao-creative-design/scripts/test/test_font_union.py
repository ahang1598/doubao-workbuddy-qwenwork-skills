"""Behavior and preservation checks for the shared font recommendation source."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest
import re
import tempfile
import shutil

ROOT = Path(__file__).resolve().parents[2]

class FontUnionTests(unittest.TestCase):
    def setUp(self):
        self.pool = json.loads((ROOT/'assets/fonts/font-curated-pool.json').read_text())

    def query(self, **kwargs):
        path = ROOT/'scripts/runtime/select_fonts.py'
        self.assertTrue(path.exists(), 'shared font selector is missing')
        spec = importlib.util.spec_from_file_location('font_union_selector', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.recommend(ROOT, **kwargs)

    def test_all_existing_theme_names_are_accounted_for(self):
        sources = self.pool.get('legacy_recommendations', [])
        self.assertEqual(len({x['name'] for x in sources}), 57)
        keys = {x['key'] for x in self.pool['fonts']}
        self.assertTrue(all(x['font_key'] in keys for x in sources))

    def test_expanded_themes_and_bilingual_roles(self):
        self.assertGreaterEqual(len(self.pool['themes']), 24)
        for theme in self.pool['themes'].values():
            self.assertEqual(set(theme.get('language_roles', {})), {'zh', 'en', 'ko', 'ja'})

    def test_platform_registry_preserves_exact_faces(self):
        registry = {x['family']:x for x in self.pool.get('platform_fonts', [])}
        self.assertEqual(len(registry), 70)
        self.assertEqual(registry['Source Han Serif CN']['normal'], [600])
        self.assertEqual(registry['Smiley Sans']['italic'], [400])
        self.assertEqual(registry['S-Core Dream']['normal'], [300])
        self.assertNotIn('Inter', registry)

    def test_combination_ids_match_current_css_catalog(self):
        catalog = json.loads((ROOT/'assets/templates/css/catalog.json').read_text())
        self.assertNotIn('profiles', self.pool)
        self.assertEqual(set(self.pool['combinations']), {e['id'] for e in catalog['entries'] if e['id'].startswith('combination.')})
        for entry in catalog['entries']:
            if entry['id'].startswith('combination.'):
                self.assertIn(entry['id'], self.pool['combinations'])

    def test_english_bakery_does_not_return_chinese_candidates(self):
        result = self.query(theme='bakery_cafe', role='hero', language='en')
        self.assertTrue(result['candidates'])
        self.assertTrue(all('en' in x['recommendation_languages'] for x in result['candidates']))
        self.assertTrue(all(x['coverage_status']=='not_tested' for x in result['candidates']))

    def test_korean_serif_does_not_fall_back_to_chinese_sans(self):
        result = self.query(theme='bakery_cafe', role='body', language='ko', shape='serif')
        self.assertTrue(result['candidates'])
        self.assertTrue(all(x['shape']=='serif' and 'ko' in x['recommendation_languages'] for x in result['candidates']))
        self.assertGreater(result['shortfall'], 0)

    def test_exclusion_applies_to_all_stages(self):
        first = self.query(theme='bakery_cafe', role='hero', language='zh')['candidates'][0]
        result = self.query(theme='bakery_cafe', role='hero', language='zh', exclude=[first['display_name']])
        self.assertNotIn(first['key'], [x['key'] for x in result['candidates']])

    def test_platform_presence_is_not_runtime_readiness(self):
        result = self.query(theme='minimal_modern', role='hero', language='en', platform_only=True)
        self.assertTrue(result['candidates'])
        for item in result['candidates']:
            self.assertEqual(item['platform_status'], 'listed_not_runtime_verified')
            self.assertEqual(item['face_status'], 'not_tested')
            self.assertNotEqual(item['resource_status'], 'ready')

    def test_unresolved_legacy_font_is_preserved_without_fake_catalog(self):
        font = next((x for x in self.pool['fonts'] if x['display_name']=='Bodoni Moda'), None)
        self.assertIsNotNone(font)
        self.assertIsNone(font['catalog_id'])
        visual = self.query(theme='luxury_elegant', role='hero', language='en')
        self.assertIn(font['key'], [x['key'] for x in visual['candidates']])
        result = self.query(theme='luxury_elegant', role='hero', language='en', available_only=True)
        self.assertNotIn(font['key'], [x['key'] for x in result['candidates']])

    def test_selector_declares_query_scope_without_visual_approval(self):
        result = self.query(theme='minimal_modern', role='hero', language='zh')
        policy = result['selection_policy']
        self.assertEqual(
            policy.get('query_role'),
            'deterministic_query_and_diagnostics',
        )
        self.assertTrue(policy.get('visual_review_required'))
        self.assertEqual(policy.get('availability_scope'), 'runtime')
        self.assertIs(policy.get('recommendations_are_exhaustive'), False)

    def test_body_does_not_receive_display_only_candidates(self):
        for language in ('zh','en','ko','ja'):
            result = self.query(theme='bakery_cafe', role='body', language=language)
            self.assertTrue(result['candidates'])
            self.assertTrue(all('body' in x['roles'] for x in result['candidates']))

    def test_traits_are_intersection_and_unknown_combinations_fail(self):
        result = self.query(theme='bakery_cafe', role='hero', language='en', tags=['serif','handwritten'])
        self.assertFalse(result['candidates'])
        with self.assertRaises(ValueError):
            self.query(combination='combination.nonexistent', role='hero')

    def test_known_existing_combination_can_describe(self):
        path = ROOT/'scripts/runtime/select_fonts.py'
        self.assertTrue(path.exists())
        result = subprocess.run([sys.executable, str(ROOT/'scripts/runtime/query-css-library.py'),
            'describe','combination.four-zone-imagery'], capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('font_recommendations',json.loads(result.stdout))

    def test_new_resume_combinations_describe(self):
        for name in ('letter-rail', 'circle-editorial', 'pink-name-collage'):
            combo = 'combination.resume-' + name
            result = subprocess.run([sys.executable, str(ROOT/'scripts/runtime/query-css-library.py'),
                'describe', combo], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertTrue(data['font_recommendations'][combo]['body']['candidates'])

    def test_missing_binding_keeps_design_but_blocks_font_selection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)/'skill'
            shutil.copytree(ROOT, root)
            path = root/'assets/fonts/font-curated-pool.json'
            pool = json.loads(path.read_text())
            entry = {'id': 'combination.resume-10'}
            pool['combinations'].pop(entry['id'])
            path.write_text(json.dumps(pool))
            result = subprocess.run([sys.executable, str(root/'scripts/runtime/query-css-library.py'),
                'describe', entry['id']], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)
            self.assertEqual(data['candidates'][0]['id'], entry['id'])
            self.assertTrue(data.get('font_errors'), 'missing structured font error')
            self.assertEqual(data['font_errors'][0]['code'], 'FONT_BINDING_MISSING')
            self.assertEqual(data['font_status'], 'blocked')
            selection = subprocess.run([sys.executable, str(root/'scripts/runtime/select_fonts.py'),
                '--combination', entry['id'], '--role', 'body'], capture_output=True, text=True)
            self.assertEqual(selection.returncode, 2)
            self.assertIn('FONT_BINDING_MISSING', selection.stderr)

    def test_invalid_font_bindings_preserve_css_for_id_and_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)/'skill'; shutil.copytree(ROOT, root)
            catalog_path = root/'assets/templates/css/catalog.json'
            pool_path = root/'assets/fonts/font-curated-pool.json'
            catalog = json.loads(catalog_path.read_text()); pool = json.loads(pool_path.read_text())
            entry = next(e for e in catalog['entries'] if e['id']=='combination.resume-10')
            profile = entry['id']
            ref = catalog['documents'][entry['document']]['path']+'#'+entry['anchor']
            for mutation in ('list_binding', 'null_languages', 'null_roles', 'unknown_key', 'unknown_catalog'):
                c = json.loads(json.dumps(catalog)); p = json.loads(json.dumps(pool))
                e = next(e for e in c['entries'] if e['id']==entry['id'])
                if mutation=='list_binding': p['combinations'][profile]=[]
                elif mutation=='null_languages': p['combinations'][profile]['language_roles']=None
                elif mutation=='null_roles': p['combinations'][profile]['language_roles']['zh']=None
                elif mutation=='unknown_key': p['combinations'][profile]['language_roles']['zh']['hero']=['missing-font']
                else:
                    key=p['combinations'][profile]['language_roles']['zh']['hero'][0]
                    next(f for f in p['fonts'] if f['key']==key)['catalog_id']='missing-catalog'
                catalog_path.write_text(json.dumps(c));pool_path.write_text(json.dumps(p))
                for target in (entry['id'], ref):
                    with self.subTest(mutation=mutation,target=target):
                        r=subprocess.run([sys.executable,str(root/'scripts/runtime/query-css-library.py'),'describe',target],capture_output=True,text=True)
                        self.assertEqual(r.returncode,0,r.stderr)
                        d=json.loads(r.stdout);self.assertEqual(d.get('font_status'),'blocked');self.assertTrue(d['candidates'])

    def test_registry_mirror_matches_every_documented_face(self):
        text=(ROOT/'references/items/fonts.md').read_text().split('## 完整白名单')[1]
        expected={}
        for line in text.splitlines():
            cells=[c.strip() for c in line.split('|')]
            if len(cells)>5 and '`' in cells[2]:
                expected[cells[2].strip('`')]={
                    'normal':[int(x) for x in re.findall(r'\d+',cells[3])],
                    'italic':[int(x) for x in re.findall(r'\d+',cells[4])]}
        actual={e['family']:{'normal':e['normal'],'italic':e['italic']}
                for e in self.pool['platform_fonts']}
        self.assertEqual(actual,expected)

    def test_all_recommendation_references_resolve_and_fit_role_language(self):
        fonts={f['key']:f for f in self.pool['fonts']}
        self.assertEqual(len(fonts),len(self.pool['fonts']))
        self.assertIn('combinations', list(self.pool))
        for group in ('themes','combinations'):
            for item in self.pool[group].values():
                for language,role_map in item['language_roles'].items():
                    for role,keys in role_map.items():
                        self.assertEqual(len(keys),len(set(keys)))
                        for key in keys:
                            self.assertIn(key,fonts)
                            self.assertIn(role,fonts[key]['roles'])
                            self.assertIn(language,fonts[key]['recommendation_languages'])

    def test_unsupported_language_does_not_silently_return_chinese(self):
        with self.assertRaises(ValueError):
            self.query(theme='bakery_cafe', role='hero', language='ar')

    def test_unclassified_registry_fonts_are_not_theme_recommendations(self):
        unclassified={f['key'] for f in self.pool['fonts'] if f['recommendation_status']=='registered_unclassified'}
        self.assertTrue(unclassified)
        for theme in self.pool['themes'].values():
            for roles in theme['language_roles'].values():
                for keys in roles.values():
                    self.assertFalse(unclassified.intersection(keys))

if __name__=='__main__':
    unittest.main()
