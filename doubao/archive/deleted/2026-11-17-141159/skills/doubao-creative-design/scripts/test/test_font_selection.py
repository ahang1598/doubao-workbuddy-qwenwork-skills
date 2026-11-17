#!/usr/bin/env python3
"""Offline regression checks for curated selection, aliases and contract gates."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runtime"))
import resolve_font as resolver


class FontSelectionTests(unittest.TestCase):
    def setUp(self):
        self.pool = resolver.load_curated_pool()
        self.records = resolver.load_records()

    def test_pool_ids_and_aliases(self):
        fonts = self.pool['fonts']
        self.assertTrue({'sans','puhui','serif','mingxin','fangsong','wenkai','rounded','chillround','manhei','happy','smiley','douyin','shuheiti','muyao','wide','butter','saobao','pixel'}.issubset({f['key'] for f in fonts}))
        for f in fonts:
            if not f['catalog_id']:
                with self.assertRaises(SystemExit):
                    resolver.select(self.records, f['display_name'])
                continue
            for query in [f['catalog_id'], f['display_name'], *f['aliases']]:
                with self.subTest(query=query):
                    matches = {other['catalog_id'] for other in fonts
                               if resolver.normalize_query(query) in
                               {resolver.normalize_query(n) for n in [other['display_name'], *other['aliases']]}}
                    if query != f['catalog_id'] and len(matches) > 1:
                        with self.assertRaises(SystemExit):
                            resolver.select(self.records, query)
                    else:
                        self.assertEqual(resolver.select(self.records, query)['id'], f['catalog_id'])

    def test_every_scene_role_has_ordered_compatible_candidates(self):
        fonts = {f['key']: f for f in self.pool['fonts']}
        for theme, entry in self.pool['themes'].items():
            for role, keys in entry['roles'].items():
                with self.subTest(theme=theme, role=role):
                    self.assertGreater(len(keys), 0)
                    self.assertEqual(len(keys), len(set(keys)))
                    for key in keys:
                        self.assertIn(role, fonts[key]['roles'])
        self.assertNotIn('pixel', self.pool['themes']['pixel_game']['roles']['body'])

    def test_normalized_alias_and_explicit_variant(self):
        self.assertEqual(resolver.select(self.records, '  Ｓｍｉｌｅｙ   Ｓａｎｓ  ')['id'], 'chinese-0088-font-3a98f632ba91')
        self.assertEqual(resolver.select(self.records, 'Resource Han Rounded CN')['id'], 'chinese-0084-font-f715cbc87a44')
        self.assertEqual(resolver.select(self.records, 'chinese-0014-resource-han-rounded-cn')['id'], 'chinese-0014-resource-han-rounded-cn')

    def test_ambiguous_and_unknown_queries_fail(self):
        for query in ['Source Han Serif CN', '根本不存在的字体', '']:
            with self.subTest(query=query), self.assertRaises(SystemExit):
                resolver.select(self.records, query)

    def test_blocked_names_cannot_resolve_as_exact_fonts(self):
        for query in self.pool['blocked_names']:
            with self.subTest(query=query), self.assertRaises(SystemExit):
                resolver.select(self.records, query)

    def test_ambiguous_alias_fails(self):
        pool = {'fonts': [{'display_name': 'collision', 'catalog_id': 'a'}, {'display_name': 'collision', 'catalog_id': 'b'}]}
        with patch.object(resolver, 'load_curated_pool', return_value=pool), self.assertRaises(SystemExit):
            resolver.select(self.records, 'collision')

    def test_unresolved_alias_collision_reports_ambiguity(self):
        pool = {'fonts': [{'display_name': 'collision', 'catalog_id': None}, {'display_name': 'collision', 'catalog_id': 'a'}]}
        with patch.object(resolver, 'load_curated_pool', return_value=pool), self.assertRaisesRegex(SystemExit, 'ambiguous'):
            resolver.select(self.records, 'collision')

    def invoke(self, extra, paths=None, metadata=None):
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as cache, contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(sys, 'argv', ['resolve_font.py', '思源黑体', '--cache-root', cache, *extra]))
            stack.enter_context(contextlib.redirect_stdout(out))
            if paths is not None:
                stack.enter_context(patch.object(resolver, 'local_files', return_value=[Path(cache).resolve() / p for p in paths]))
            if metadata is not None:
                stack.enter_context(patch.object(resolver, 'font_metadata', return_value=metadata))
            code = resolver.main()
        return code, json.loads(out.getvalue())

    def test_no_resource_has_no_contract(self):
        code, result = self.invoke(['--text', '严肃报告 2026', '--require-ready'])
        self.assertEqual(code, 2)
        self.assertIsNone(result['font_contract_entry'])
        self.assertFalse(result['contract_ready'])
        self.assertEqual(result.get('unready_action'), 'request_user_confirmation')
        self.assertEqual(result['display_name'], '思源黑体')

    def test_unchecked_missing_or_unknown_family_has_no_contract(self):
        for status, names in [('not_checked', ['Real Family']), ('missing_glyphs', ['Real Family']), ('not_supported', []), ('complete', [])]:
            with self.subTest(status=status, names=names):
                _, result = self.invoke([], paths=['font.ttf'], metadata={'coverage_status': status, 'resolved_family_names': names})
                self.assertIsNone(result['font_contract_entry'])

    def test_contract_uses_real_family_not_display_name(self):
        code, result = self.invoke(['--text', '报告', '--require-ready'], paths=['font.ttf'], metadata={'coverage_status': 'complete', 'resolved_family_names': ['Real Internal Family']})
        self.assertEqual(code, 0)
        self.assertEqual(result['font_contract_entry']['family'], 'Real Internal Family')
        self.assertEqual(result['display_name'], '思源黑体')
        self.assertEqual(result['render_status'], 'not_checked')

    def test_local_nonstandard_license_does_not_bypass_gate(self):
        with patch.object(resolver, 'license_allows_automatic_fetch', return_value=False):
            code, result = self.invoke(['--text', '报告', '--require-ready'], paths=['font.ttf'], metadata={'coverage_status': 'complete', 'resolved_family_names': ['Real Family']})
        self.assertEqual(code, 6)
        self.assertIsNone(result['font_contract_entry'])
        self.assertEqual(result['license_status'], 'review_required')

    def test_multiple_faces_cannot_union_missing_glyphs(self):
        with tempfile.TemporaryDirectory() as cache:
            paths = [Path(cache) / 'a.ttf', Path(cache) / 'b.ttf']
            for p in paths:
                p.write_bytes(b'font')
            with patch.object(resolver, 'sfnt_offsets', return_value=[0]), patch.object(resolver, 'sfnt_tables', side_effect=[{'face': 'a'}, {'face': 'b'}]), patch.object(resolver, 'family_names', return_value={'Same Family'}), patch.object(resolver, 'font_supports', side_effect=lambda data, tables, cp: cp == ord(tables['face'])):
                result = resolver.font_metadata(paths, 'ab')
            self.assertEqual(result['coverage_status'], 'missing_glyphs')
            self.assertEqual(result['missing_characters'], ['a', 'b'])


class QijicThemePriorityTests(unittest.TestCase):
    def test_theme_title_priority_without_relaxing_filters(self):
        import select_fonts
        for theme in ('guochao_oriental', 'neo_chinese'):
            for role in ('hero', 'sub'):
                with self.subTest(theme=theme, role=role):
                    result = select_fonts.recommend(theme=theme, role=role, limit=2)
                    self.assertEqual(result['candidates'][1]['key'], 'qijic')
                    filtered = select_fonts.recommend(theme=theme, role=role, shape='brush', limit=50)
                    self.assertNotIn('qijic', [f['key'] for f in filtered['candidates']])
                    excluded = select_fonts.recommend(theme=theme, role=role, exclude=['qijic'], limit=50)
                    self.assertNotIn('qijic', [f['key'] for f in excluded['candidates']])
            for role in ('body', 'meta'):
                result = select_fonts.recommend(theme=theme, role=role, limit=50)
                self.assertNotIn('qijic', [f['key'] for f in result['candidates']])


class BrushMoodTests(unittest.TestCase):
    def query(self, **kwargs):
        import select_fonts
        return select_fonts.recommend(role='hero', limit=50, **kwargs)

    def keys(self, **kwargs):
        return [f['key'] for f in self.query(**kwargs)['candidates']]

    def test_brush_chinese_alias_preserves_order(self):
        self.assertEqual(self.keys(shape='毛笔'), self.keys(shape='brush'))
        self.assertEqual(self.keys(shape='软笔'), [])

    def test_cute_softbrush_and_wild_remain_distinct(self):
        self.assertEqual(self.keys(shape='brush', tags=['可爱']), ['muyao'])
        self.assertEqual(self.keys(shape='brush', tags=['狂放']), ['liujiang'])
        self.assertEqual(self.keys(shape='brush', tags=['狂放']), self.keys(shape='brush', tags=['wild']))
        self.assertEqual(self.keys(shape='brush', tags=['狂放','可爱']), [])

    def test_theme_and_combination_do_not_drop_mood(self):
        for context in [{'theme':'guochao_oriental'}, {'combination':'combination.resume-09'}]:
            keys=self.keys(shape='brush', tags=['狂放'], **context)
            self.assertNotIn('muyao', keys)
            self.assertEqual(keys, ['liujiang'])

    def test_missing_review_is_not_positive_match(self):
        result=self.query(shape='brush', tags=['清新'])
        self.assertEqual(result['candidates'], [])
        self.assertEqual(result['trait_diagnostics']['status'], 'no_matches')
        self.assertEqual(result['trait_diagnostics']['unreviewed_brush_traits'], [{'key':'moda_brush','traits':['fresh']}])
        unknown=self.query(shape='brush', tags=['invented-mood'])
        self.assertEqual(unknown['trait_diagnostics']['status'], 'unknown_traits')
        self.assertEqual(unknown['trait_diagnostics']['unknown_traits'], ['invented-mood'])

    def test_general_handwriting_not_promoted_to_brush(self):
        keys=self.keys(shape='毛笔')
        self.assertNotIn('chenluo', keys)
        self.assertNotIn('chill_zhengkai', keys)
        self.assertIn('mashanzheng', keys)

    def test_exclusion_and_limit_still_apply(self):
        import select_fonts
        limited = select_fonts.recommend(role='hero', shape='brush', limit=1)
        self.assertEqual(len(limited['candidates']), 1)
        self.assertEqual(limited['shortfall'], 0)
        self.assertEqual(self.keys(shape='brush', tags=['可爱'], exclude=['muyao']), [])
        result=self.query(shape='brush', tags=['狂放'], exclude=['moda_brush'])
        self.assertEqual(result['trait_diagnostics']['unreviewed_brush_traits'], [])



class ExpressiveCategoryTests(unittest.TestCase):
    def keys(self, shape, tag=None, language='zh'):
        import select_fonts
        result=select_fonts.recommend(shape=shape, tags=[tag] if tag else [], language=language, limit=200)
        return {f['key'] for f in result['candidates']}

    def test_calligraphy_alias_and_parent(self):
        self.assertEqual(self.keys('书法字'), self.keys('书法'))
        self.assertTrue(self.keys('毛笔') <= self.keys('书法字'))
        self.assertIn('wenkai', self.keys('书法字', '清新'))
        self.assertNotIn('muyao', self.keys('书法字', '狂放'))
        self.assertIn('mashanzheng', self.keys('书法字', '端正'))

    def test_handwriting_alias_and_moods(self):
        self.assertEqual(self.keys('手写字'), self.keys('手写体'))
        self.assertIn('mengshen_hand', self.keys('手写字', '可爱'))
        self.assertIn('jason7', self.keys('手写字', '松弛'))
        self.assertIn('carefree', self.keys('手写字', '清新'))

    def test_creative_does_not_mean_cute(self):
        self.assertIn('inorganic', self.keys('创意字', '科技'))
        self.assertNotIn('butter', self.keys('创意字', '科技'))
        self.assertIn('butter', self.keys('创意字', '可爱'))
        self.assertIn('pixel9', self.keys('创意字体', '复古'))
        self.assertIn('organic', self.keys('创意字', '实验'))

    def test_language_and_review_boundaries(self):
        self.assertIn('platform-allison', self.keys('书法字', '优雅', language='en'))
        self.assertNotIn('platform-allison', self.keys('书法字', language='zh'))
        self.assertNotIn('platform-alex-brush', self.keys('书法字', language='en'))
        self.assertNotIn('moda_brush', self.keys('毛笔', '狂放'))
        self.assertEqual(self.keys('毛笔', '清新'), set())

class DefaultFontPreferenceTests(unittest.TestCase):
    def query(self, **kwargs):
        import select_fonts
        return select_fonts.recommend(**kwargs)

    def test_muyao_requires_cute_brush_intent_across_routes(self):
        contexts=[{'theme':'tea_natural'}, {'theme':'bakery_cafe'},
                  {'theme':'guochao_oriental'}, {'combination':'combination.resume-09'},
                  {'combination':'combination.vertical-title-whitespace'}]
        for context in contexts:
            for limit in (1,10,200):
                for traits in ({}, {'shape':'毛笔'}, {'shape':'书法字'},
                               {'shape':'软笔'}, {'tags':['可爱']}):
                    with self.subTest(context=context,limit=limit,traits=traits):
                        rows=self.query(**context,**traits,limit=limit)['candidates']
                        self.assertNotIn('muyao',{f['key'] for f in rows})
        for shape in ('毛笔','软笔'):
            rows=self.query(shape=shape,tags=['可爱'],limit=200)['candidates']
            self.assertEqual(rows[-1]['key'],'muyao')
        keys={f['key'] for f in self.query(theme='guochao_oriental',shape='毛笔')['candidates']}
        self.assertTrue({'moda_brush','liujiang','mashanzheng'} <= keys)

    def test_gate_equivalent_tags_roles_and_exact_name(self):
        for role in ('hero','sub'):
            self.assertNotIn('muyao',{f['key'] for f in self.query(shape='毛笔',role=role,limit=200)['candidates']})
            for tags in (['cute','brush'], ['可爱','软笔']):
                result=self.query(tags=tags,role=role,limit=200)
                self.assertTrue(result['selection_policy']['muyao_cute_brush_intent'])
                self.assertIn('muyao',{f['key'] for f in result['candidates']})
                self.assertEqual(self.query(tags=tags,role=role,exclude=['沐瑶软笔'])['candidates'],[])
        pool=resolver.load_curated_pool()
        expected=next(f['catalog_id'] for f in pool['fonts'] if f['key']=='muyao')
        for name in ('沐瑶软笔手写体','沐瑶软笔'):
            self.assertEqual(resolver.select(resolver.load_records(),name)['id'],expected)


if __name__ == '__main__':
    unittest.main()
