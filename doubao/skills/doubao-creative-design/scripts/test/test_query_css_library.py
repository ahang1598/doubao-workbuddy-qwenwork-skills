import importlib.util,json,tempfile,unittest,subprocess,sys
from pathlib import Path
spec=importlib.util.spec_from_file_location('query',Path(__file__).resolve().parents[1]/'runtime/query-css-library.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.css=self.root/'assets/templates/css';self.css.mkdir(parents=True)
  (self.css/'a.md').write_text('INTRO\n<a id="one"></a>\n## ONE\ncontent [shared](b.md#shared) [spec](../../../spec.md)\n```html\n<a id="fake"></a>\n```\n<a id="two"></a>\n## TWO\nSECRET OTHER BODY\n')
  (self.css/'b.md').write_text('<a id="shared"></a>\n## SHARED\n[back](a.md#one)\n')
  self.data={'documents':{'a':{'path':'assets/templates/css/a.md'},'b':{'path':'assets/templates/css/b.md'}},'entries':[{'id':'combination.one','name':'室内组合','document':'a','anchor':'one','tags':['图窗'],'style_tags':['一级：精品'],'candidate_contexts':{'use_when':'家具与团队'}},{'id':'layout.two','name':'通用网格','document':'a','anchor':'two','tags':['图窗'],'style_tags':['通用']}]}
  self.data['reading_contracts']={'assets/templates/css/a.md#one':{'b.md#shared':'required','../../../spec.md':'reference'},'assets/templates/css/b.md#shared':{'a.md#one':'required'}}
  templates=self.root/'assets/templates';templates.mkdir(exist_ok=True)
  (templates/'ref-bindings.json').write_text(json.dumps({'category_refs':{'a':{},'b':{}},'css':{'default_ref_keys':['a','b'],'entry_overrides':{'combination.one':['a']}}}))
  self.save();self.lib=m.Library(self.root)
 def save(self):(self.css/'catalog.json').write_text(json.dumps(self.data,ensure_ascii=False))
 def test_compound_expansion_respects_hard_filter(self):
  self.data['entries']=[{'id':'shape.a','tags':['贴纸卡片'],'artifact_types':['通知']},{'id':'shape.b','tags':['贴纸'],'artifact_types':['邀请函']},{'id':'shape.c','tags':['手账'],'artifact_types':['邀请函']}];self.save()
  r=m.Library(self.root).search('贴纸卡片',artifact='邀请函',kind='shape',limit=3)
  self.assertEqual({x['id'] for x in r['candidates']},{'shape.b','shape.c'})
 def test_indented_fences_are_read(self):
  blocks=m.Library.blocks('  ```json\n  {"dependencies":["shape.b"]}\n  ````\n')
  self.assertEqual(len(blocks),1);self.assertEqual(json.loads(blocks[0].group(3))['dependencies'],['shape.b'])
 def test_search_metadata_only(self):
  (self.css/'a.md').unlink();r=self.lib.search('图窗','精品',None,8);self.assertEqual(r['total'],2);self.assertNotIn('SECRET',json.dumps(r));self.assertEqual(r['candidates'][0]['id'],'combination.one')
 def test_context(self):self.assertEqual(self.lib.search('家具','',None,8)['candidates'][0]['id'],'combination.one')
 def test_no_match(self):self.assertEqual(self.lib.search('不存在','',None,8)['total'],0)
 def test_kind(self):self.assertEqual(self.lib.search('图窗','','layout',8)['total'],1)
 def test_ref_key(self):
  r=self.lib.search('图窗',ref_key='b');self.assertEqual([x['id'] for x in r['candidates']],['layout.two'])
  with self.assertRaises(ValueError):self.lib.search('图窗',ref_key='missing')
 def test_empty_search(self):
  with self.assertRaises(ValueError):self.lib.search('','',None,8)
 def test_generic_container_search_prefers_structural_profiles(self):
  self.data['entries']=[
   {'id':'shape.rounded','name':'圆角容器','document':'a','anchor':'one','tags':['卡片','容器'],'style_tags':['通用'],'container_profile':'neutral'},
   {'id':'shape.folder','name':'文件夹','document':'a','anchor':'two','tags':['容器','异形'],'style_tags':['通用'],'container_profile':'structural'},
  ];self.save();lib=m.Library(self.root)
  generic=lib.search('容器','',None,8)
  self.assertEqual(generic['candidates'][0]['id'],'shape.folder')
  self.assertEqual(generic['candidates'][0]['ranking_reason'],'泛化容器查询优先结构型轮廓')
  explicit=lib.search('容器 圆角','',None,8)
  self.assertEqual(explicit['candidates'][0]['id'],'shape.rounded')
 def test_generic_visual_intents_expand_bounded_candidates(self):
  self.data['entries']=[
   {'id':'layout.collage','name':'叠层拼贴','document':'a','anchor':'one','tags':['拼贴'],'style_tags':['通用']},
   {'id':'surface.light-paper','name':'轻纸纹','document':'a','anchor':'two','tags':['纸纹'],'style_tags':['通用']},
   {'id':'text.outline','name':'文字描边','document':'a','anchor':'one','tags':['描边'],'style_tags':['通用']},
   {'id':'palette.cream-pink','name':'奶油粉','document':'a','anchor':'two','tags':['奶油粉'],'style_tags':['通用']},
  ];self.save();lib=m.Library(self.root)
  collage=lib.search('有趣 排版','',None,8)['candidates'][0]
  self.assertEqual(collage['id'],'layout.collage');self.assertIn('有趣排版',collage['implied_intents'])
  background=lib.search('背景 氛围','',None,8)['candidates'][0]
  self.assertEqual(background['id'],'surface.light-paper');self.assertIn('背景氛围',background['implied_intents'])
  text=lib.search('特效','',None,8)['candidates'][0]
  self.assertEqual(text['id'],'text.outline');self.assertIn('文字特效',text['implied_intents'])
  color=lib.search('配色','',None,8)['candidates'][0]
  self.assertEqual(color['id'],'palette.cream-pink');self.assertIn('配色',color['implied_intents'])
 def test_broad_intents_offer_scene_and_type_without_implied_frames(self):
  self.data['entries']=[
   {'id':'layout.image-stage','name':'主图舞台','tags':['主图']},
   {'id':'layout.staggered-title','name':'错位标题','tags':['标题']},
   {'id':'layout.collage','name':'拼贴','tags':['拼贴']},
   {'id':'shape.arch-window','name':'拱窗','tags':['拱窗']},
   {'id':'layout.card-rail','name':'横向卡片列','tags':['卡片']},
   {'id':'surface.light-paper','name':'纸纹','tags':['纸纹']},
  ];self.save();lib=m.Library(self.root)
  creative={e['id'] for e in lib.search('创意 排版',limit=20)['candidates']}
  self.assertTrue({'layout.image-stage','layout.staggered-title','layout.collage'} <= creative)
  self.assertNotIn('shape.arch-window',creative)
  self.assertNotIn('layout.card-rail',creative)
  background={e['id'] for e in lib.search('背景 氛围',limit=20)['candidates']}
  self.assertTrue({'layout.image-stage','surface.light-paper'} <= background)
  self.assertEqual(lib.search('拱窗',limit=8)['candidates'][0]['id'],'shape.arch-window')
  self.assertEqual(lib.search('卡片',limit=8)['candidates'][0]['id'],'layout.card-rail')
  self.assertTrue(all(e['id'].startswith('surface.') for e in lib.search('背景',kind='surface',limit=20)['candidates']))
 def test_section_boundary_and_fence(self):
  r=self.lib.get(['combination.one'],templates=True);s=r['sections'][0]['content'];self.assertIn('fake',s);self.assertNotIn('SECRET',s);self.assertNotIn('INTRO',s)
 def test_cycle_and_dedup(self):
  r=self.lib.get(['combination.one','combination.one'],dependencies=True);self.assertEqual(len(r['sections']),2);self.assertTrue(r['follow_ups'])
 def test_budget_no_silent_cut(self):
  with self.assertRaises(m.BudgetExceeded):self.lib.get(['combination.one'],max_chars=10)
 def test_unknown(self):
  with self.assertRaises(ValueError):self.lib.get(['unknown'])
 def test_missing_anchor(self):
  with self.assertRaises(ValueError):self.lib.get(['assets/templates/css/a.md#missing'])
 def test_escape(self):
  with self.assertRaises(ValueError):self.lib.get(['../../outside.md#x'])
 def test_duplicate_ids(self):
  self.data['entries'].append(self.data['entries'][0]);self.save()
  with self.assertRaises(ValueError):m.Library(self.root)
 def test_templates_opt_in(self):
  (self.css/'t.html').write_text('<main>template</main>');p=self.css/'a.md';p.write_text(p.read_text().replace('content','[template](t.html) content'))
  self.assertEqual(len(self.lib.get(['combination.one'])['sections']),1)
  self.assertEqual(len(self.lib.get(['combination.one'],templates=True)['sections']),1)
  self.assertEqual(self.lib.template('assets/templates/css/t.html',selector='main')['content'],'<main>template</main>')
 def test_json_common_and_template(self):
  p=self.css/'a.md';p.write_text(p.read_text().replace('content', '```json\n{"common":"recipe.common","template":"demo.html","selector":"article"}\n```\ncontent')+'\n<a id="recipe.common"></a>\nPARAMETERS\n')
  r=self.lib.get(['combination.one'],dependencies=True)
  self.assertTrue(any(x['anchor']=='recipe.common' for x in r['sections']))
  self.assertTrue(any('article' in x.get('selectors', []) for x in r['follow_ups']))
 def test_longer_closing_fence_preserves_dependency(self):
  p=self.css/'a.md';p.write_text('<a id="one"></a>\n## One\n```json\n{"dependencies":["layout.two"]}\n````\n<a id="two"></a>\n## Two\nDEPENDENCY\n')
  result=self.lib.get(['combination.one'],dependencies=True)
  self.assertEqual([x['anchor'] for x in result['sections']],['one','two'])
 def test_same_template_all_selectors_preserved(self):
  p=self.css/'a.md';p.write_text('<a id="one"></a>\n## One\n```json\n{"template":"t.html","selector":"section[id=a]"}\n```\n```json\n{"template":"t.html","selector":"section[id=b]"}\n```\n')
  (self.css/'t.html').write_text('<section id="a"></section><section id="b"></section>')
  result=self.lib.get(['combination.one'])
  row=next(x for x in result['follow_ups'] if x['reference'].endswith('t.html'))
  self.assertEqual(row.get('selectors'),['section[id=a]','section[id=b]'])
 def test_compound_chinese_recall_and_unknown_visual_id(self):
  root=Path(__file__).resolve().parents[2];lib=m.Library(root)
  result=lib.search('简历 灰蓝贴纸风 RV5.3',kind='combination',artifact='简历',layout_scope='整张单屏',limit=5)
  self.assertIn('combination.resume-10',[x['id'] for x in result['candidates']])
  self.assertIn('rv5.3',result.get('query_analysis',{}).get('unresolved_terms',[]))
  self.assertEqual(result['candidates'][0]['relevance'],'effect_match')
 def test_color_does_not_expand_to_collage_and_category_only_is_weak(self):
  root=Path(__file__).resolve().parents[2];lib=m.Library(root)
  result=lib.search('灰蓝',kind='combination')
  self.assertFalse(result.get('query_analysis',{}).get('expansions'))
  result=lib.search('简历 不存在效果词',kind='combination',artifact='简历')
  self.assertTrue(result['candidates'])
  self.assertTrue(all(x.get('relevance')=='category_only' for x in result['candidates']))
 def test_expansion_is_explained_and_hard_filters_preserved(self):
  self.data['entries']=[{'id':'combination.one','document':'a','anchor':'one','name':'纸片','tags':['手账'],'artifact_types':['简历'],'layout_scope':'整张单屏'}];self.save();lib=m.Library(self.root)
  r=lib.search('贴纸',kind='combination',artifact='简历',layout_scope='整张单屏')
  self.assertTrue(r['candidates'])
  self.assertEqual(r['candidates'][0]['recall_stage'],'expanded')
  self.assertEqual(r['candidates'][0]['expanded_matches'],[{'from':'贴纸','term':'手账'}])
  self.assertFalse(lib.search('贴纸',kind='combination',artifact='菜单')['candidates'])
 def test_all_catalog_namespaces_are_cli_queryable(self):
  script=Path(__file__).resolve().parents[1]/'runtime/query-css-library.py'
  for kind,word in [('surface','纸纹'),('text','文字'),('palette','配色')]:
   r=subprocess.run([sys.executable,str(script),'search',word,'--kind',kind],capture_output=True,text=True)
   self.assertEqual(r.returncode,0,r.stderr)

 def test_symlink_escape(self):
  (self.css/'escape.md').symlink_to('/etc/passwd')
  with self.assertRaises(ValueError):self.lib.get(['assets/templates/css/escape.md#x'])
 def test_heading(self):
  (self.css/'head.md').write_text('# Title\n## Text Shape\nkeep\n### Child\nchild\n## Next\nexclude')
  r=self.lib.get(['assets/templates/css/head.md#text-shape']);self.assertIn('child',r['sections'][0]['content']);self.assertNotIn('exclude',r['sections'][0]['content'])
class ProgressiveTests(unittest.TestCase):
 maxDiff=600
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.base=self.root/'assets/templates/css';self.base.mkdir(parents=True)
  self.data={'documents':{'x':{'path':'assets/templates/css/x.md'}},'entries':[{'id':'combination.one','name':'候选','document':'x','anchor':'one','style_tags':['纸感'],'tags':['图窗'],'candidate_contexts':{'use_when':'场景与文字并置'}},{'id':'recipe.unused','document':'x','anchor':'unused','name':'无关模板'}]}
  (self.base/'catalog.json').write_text(json.dumps(self.data,ensure_ascii=False))
  (self.base/'x.md').write_text('<a id="one"></a>\n## One\n### 背景与图文关系\n文字在安静区域，照片跨栏。\n### 字体\n标题宋体，正文黑体。\n```json\n{"applies_to":["recipe.unused"],"common":"local.common"}\n```\n```css\nREAL_CSS\n```\n```html\n'+('BIG_HTML'*6000)+'\n```\n<a id="local.common"></a>\n## Common\nNEEDED\n<a id="unused"></a>\n## Unused\nUNRELATED\n')
  self.lib=m.Library(self.root)
 def test_applies_to_not_dependency(self):
  r=self.lib.get(['combination.one'],dependencies=True,max_chars=100000);s=''.join(x['content'] for x in r['sections']);self.assertNotIn('UNRELATED',s);self.assertIn('NEEDED',s)
 def test_template_body_opt_in(self):
  r=self.lib.get(['combination.one']);s=''.join(x['content'] for x in r['sections']);self.assertIn('REAL_CSS',s);self.assertNotIn('BIG_HTML',s);self.assertTrue(r['template_blocks'])
 def test_selection_evidence_without_code(self):
  r=self.lib.describe(['combination.one']);s=json.dumps(r,ensure_ascii=False);self.assertIn('文字在安静区域',s);self.assertIn('标题宋体',s);self.assertNotIn('BIG_HTML',s);self.assertNotIn('REAL_CSS',s);self.assertNotIn('UNRELATED',s)
 def test_read_state_reuse_and_invalidation(self):
  state={};a=self.lib.get(['combination.one'],read_state=state);b=self.lib.get(['combination.one'],read_state=state);self.assertTrue(a['sections']);self.assertFalse(b['sections']);self.assertTrue(b['reused_sections'])
  p=self.base/'x.md';p.write_text(p.read_text().replace('REAL_CSS','CHANGED_CSS'));c=m.Library(self.root).get(['combination.one'],read_state=state);self.assertIn('CHANGED_CSS',c['sections'][0]['content'])
 def test_failed_read_does_not_mark_state(self):
  state={}
  with self.assertRaises(m.BudgetExceeded):self.lib.get(['combination.one'],max_chars=2,read_state=state)
  self.assertEqual(state,{})

class RoutingTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.base=self.root/'assets/templates/css';self.base.mkdir(parents=True)
  self.doc=self.base/'a.md';self.doc.write_text('<a id="one"></a>\n## One\n```json\n{"layout":{"relationship":"背景承托文字"},"fonts":{"weight":650},"future_fact":"不能删除未知设计字段"}\n```\n例如 [必要布局](a.md#two)\n[可选光晕](a.md#three)\n```css\n.one {display:grid}\n```\n```html\n<main><p>structure</p></main>\n```\n<a id="two"></a>\n## Two\nrequired grid\n<a id="three"></a>\n## Three\noptional glow\n')
  self.catalog={'documents':{'a':{'path':'assets/templates/css/a.md'}},'entries':[{'id':'one','document':'a','anchor':'one'}],'reading_contracts':{'assets/templates/css/a.md#one':{'a.md#two':'required','a.md#three':'optional'}}}
  (self.base/'catalog.json').write_text(json.dumps(self.catalog));self.lib=m.Library(self.root)
 def test_json_design_evidence(self):
  s=self.lib.get(['one'],prose=True)['sections'][0]['content'];self.assertIn('背景承托文字',s);self.assertIn('future_fact',s);self.assertNotIn('display:grid',s);self.assertNotIn('<main>',s)
 def test_explicit_dependency_ignores_word_position(self):
  r=self.lib.get(['one'],dependencies=True);self.assertEqual([s['anchor'] for s in r['sections']],['one','two']);self.assertTrue(any(x.get('role')=='optional' for x in r['follow_ups']))
 def test_selected_inline_structure(self):
  r=self.lib.template('one',block=3);self.assertIn('<main>',r['content']);self.assertNotIn('optional glow',r['content'])
 def test_selected_external_node(self):
  (self.base/'t.html').write_text('<html><head><style data-preview-only>excluded</style><style data-recipe-css>needed</style></head><body><article data-recipe="a"><img src="x"><p>A</p></article><article data-recipe="b">B</article></body></html>')
  r=self.lib.template('assets/templates/css/t.html',selector='article[data-recipe="a"]');self.assertIn('<p>A</p>',r['content']);self.assertNotIn('excluded',r['content']);self.assertNotIn('>B<',r['content'])
  self.assertEqual(self.lib.template('assets/templates/css/t.html',selector='style[data-recipe-css]')['content'],'<style data-recipe-css>needed</style>')
  with self.assertRaises(ValueError):self.lib.template('assets/templates/css/t.html',selector='article')
  with self.assertRaises(m.BudgetExceeded):self.lib.template('assets/templates/css/t.html',selector='article[data-recipe="a"]',max_chars=5)
 def test_unknown_links_remain_visible(self):
  self.doc.write_text(self.doc.read_text().replace('例如','[新增](a.md#two)\n例如'));self.catalog['reading_contracts']={};(self.base/'catalog.json').write_text(json.dumps(self.catalog));r=m.Library(self.root).get(['one'],dependencies=True);self.assertTrue(any(x.get('role')=='unclassified' for x in r['follow_ups']))

if __name__=='__main__':unittest.main()
