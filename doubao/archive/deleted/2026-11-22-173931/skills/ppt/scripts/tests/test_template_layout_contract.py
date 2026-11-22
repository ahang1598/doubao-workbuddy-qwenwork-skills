"""Executable layout contracts: native SML slots, inherited geometry, explicit binding."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / 'template' / 'template_layout_contract.py'


def load(path, name):
    assert path.exists(), f'{path.name} helper is missing'
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def native_text(element_id, x, y, w, h, text='Authored title', kind='title'):
    return f'<shape id="{element_id}" type="text" topLeftX="{x}" topLeftY="{y}" width="{w}" height="{h}"><content textType="{kind}" fontSize="28"><p>{text}</p></content></shape>'


def slide(*elements):
    return '<slide xmlns="https://www.larkoffice.com/sml/2.0"><data>' + ''.join(elements) + '</data></slide>'


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.pptx = self.root / 'template.pptx'
        self.fixture = load(HERE / 'test_template_layouts.py', 'layout_fixture')
        self.fixture.fixture(self.pptx)
        self.layout_api = load(HERE.parent / 'template' / 'template_layouts.py', 'layouts')

    def api(self):
        return load(SCRIPT, 'contract')

    def manifest(self):
        return self.layout_api.inspect_template(self.pptx)

    def contract(self, layout='Inherited', **kwargs):
        return self.api().build_layout_contract(self.manifest(), layout, **kwargs)

    def slot(self, contract, role):
        return next(s for s in contract['slots'] if s['role'] == role)

    def title(self, contract, element_id=None):
        s = self.slot(contract, 'title')
        b = s['bbox']
        node=ET.fromstring(native_text(element_id or s['slot_id'], b['x'], b['y'], b['width'], b['height']))
        node.find('content').attrib.update(s['sml_text_style'])
        return ET.tostring(node,encoding='unicode')

    def codes(self, result):
        return {e['code'] for e in result['errors']}

    def role_text(self, contract, role, text='Source role text'):
        slot = self.slot(contract,role)
        root = ET.fromstring(self.api().generate_skeleton(contract))
        node = next(n for n in root.findall('{*}data/{*}shape') if n.get('id') == slot['slot_id'])
        node.find('{*}content/{*}p').text = text
        return node

    def subtitle_manifest(self, color='<a:srgbClr val="345678"/>'):
        # Real source XML supplies geometry, minor Latin/EA font roles and 32pt.
        sample = ('<a:p><a:pPr algn="ctr"><a:defRPr sz="3200" b="0" i="0">'
                  '<a:latin typeface="+mn-lt"/><a:ea typeface="Source CJK"/>'
                  f'<a:solidFill>{color}</a:solidFill></a:defRPr></a:pPr><a:r><a:t>Subtitle</a:t></a:r></a:p>')
        subtitle = self.fixture.shape(4,'subTitle',8,self.fixture.xfrm(40,200,600,120),sample)
        subtitle = subtitle.replace('<a:bodyPr/>','<a:bodyPr anchor="ctr"/>')
        with zipfile.ZipFile(self.pptx) as archive:
            parts = {name:archive.read(name) for name in archive.namelist()}
        name = 'ppt/slideLayouts/slideLayout1.xml'
        parts[name] = parts[name].decode().replace('</p:spTree>',subtitle+'</p:spTree>').encode()
        with zipfile.ZipFile(self.pptx,'w') as archive:
            for name,data in parts.items(): archive.writestr(name,data)
        return self.manifest()

    def test_subtitle_visible_runs_cannot_hide_smaller_size_behind_content_default(self):
        manifest = self.subtitle_manifest()
        contract = self.api().build_layout_contract(manifest,'Inherited')
        node = self.role_text(contract,'subTitle')
        content = node.find('{*}content');content.set('fontSize','20')
        p = content.find('{*}p');p.text = None
        span = ET.SubElement(p,'span',{'fontSize':'18'});span.text = 'Visible subtitle'
        result = self.api().validate_layout_contract(slide(self.title(contract),ET.tostring(node,encoding='unicode')),contract,manifest=manifest)
        error = next(e for e in result['errors'] if e['code'] == 'slot_text_style_mismatch')
        self.assertEqual((error['role'],error['property'],error['expected'],error['actual']),('subTitle','fontSize','32',['18']))
        span.set('fontSize','32')
        self.assertTrue(self.api().validate_layout_contract(slide(self.title(contract),ET.tostring(node,encoding='unicode')),contract,manifest=manifest)['ok'])

    def test_subtitle_script_font_weight_alignment_and_direct_color_are_checked(self):
        manifest = self.subtitle_manifest()
        contract = self.api().build_layout_contract(manifest,'Inherited')
        node = self.role_text(contract,'subTitle','市场增长')
        content = node.find('{*}content');content.set('fontFamily','Source CJK')
        authored = lambda: slide(self.title(contract),ET.tostring(node,encoding='unicode'))
        self.assertTrue(self.api().validate_layout_contract(authored(),contract,manifest=manifest)['ok'])
        for key,value in [('fontFamily','Georgia'),('bold','true'),('italic','true'),('textAlign','left'),('verticalAlign','top'),('color','#000000')]:
            original = content.get(key)
            content.set(key,value)
            result = self.api().validate_layout_contract(authored(),contract,manifest=manifest)
            self.assertIn(key,{e.get('property') for e in result['errors'] if e['code']=='slot_text_style_mismatch'},result)
            content.set(key,original)

    def test_optional_subtitle_can_stay_empty_without_inventing_content(self):
        manifest = self.subtitle_manifest();contract = self.api().build_layout_contract(manifest,'Inherited')
        node = self.role_text(contract,'subTitle','')
        content = node.find('{*}content');content.set('fontSize','18')
        result = self.api().validate_layout_contract(slide(self.title(contract),ET.tostring(node,encoding='unicode')),contract,manifest=manifest)
        self.assertTrue(result['ok'],result)
        self.assertFalse(self.slot(contract,'subTitle')['required'])

    def test_transformed_subtitle_color_warns_without_using_resolver_rgb_as_proof(self):
        manifest = self.subtitle_manifest('<a:schemeClr val="tx1"><a:tint val="75000"/></a:schemeClr>')
        contract = self.api().build_layout_contract(manifest,'Inherited')
        node = self.role_text(contract,'subTitle');node.find('{*}content').set('color','#8B8B8B')
        result = self.api().validate_layout_contract(slide(self.title(contract),ET.tostring(node,encoding='unicode')),contract,manifest=manifest)
        self.assertTrue(result['ok'],result)
        self.assertTrue(any(w.get('code')=='uncertain_source_text_color' and w.get('reason')=='transformed_source_color' for w in result['warnings']))

    def test_subtitle_color_policy_cannot_be_edited_to_bypass_source_comparison(self):
        manifest = self.subtitle_manifest();contract = self.api().build_layout_contract(manifest,'Inherited')
        self.slot(contract,'subTitle')['color_validation'] = {'mode':'warning'}
        result = self.api().validate_layout_contract(slide(self.title(contract)),contract,manifest=manifest)
        self.assertIn('source_slot_mismatch',self.codes(result))
        for malformed in [None, [], {'mode':[]}, {'mode':'renderer_confirmed'}]:
            self.slot(contract,'subTitle')['color_validation'] = malformed
            self.assertIn('invalid_contract',self.codes(self.api().validate_layout_contract(slide(self.title(contract)),contract)))

    def test_subtitle_substitution_still_checks_size_and_legacy_tint_stays_uncertain(self):
        manifest = self.subtitle_manifest('<a:schemeClr val="tx1"><a:tint val="75000"/></a:schemeClr>')
        contract = self.api().build_layout_contract(manifest,'Inherited');slot = self.slot(contract,'subTitle')
        del slot['color_validation']  # A frozen contract predating this diagnostic.
        node = self.role_text(contract,'subTitle');content = node.find('{*}content')
        content.set('fontFamily','Replacement');content.set('color','#8B8B8B')
        binding = {'font_substitutions':{slot['slot_id']:{'fontFamily':'Replacement','reason':'Source font unavailable'}}}
        authored = lambda: slide(self.title(contract),ET.tostring(node,encoding='unicode'))
        result = self.api().validate_layout_contract(authored(),contract,manifest=manifest,bindings=binding)
        self.assertTrue(result['ok'],result)
        self.assertTrue(any(w.get('code')=='declared_text_font_substitution' for w in result['warnings']))
        content.set('fontSize','18')
        self.assertIn('slot_text_style_mismatch',self.codes(self.api().validate_layout_contract(authored(),contract,bindings=binding)))

    def test_body_obj_captions_and_chart_table_labels_are_not_forced_to_subtitle_style(self):
        contract = self.contract();slot_id = self.slot(contract,'obj')['slot_id']
        for element in [native_text(slot_id,30,130,400,100,'Chart caption','body'),
                        f'<chart id="{slot_id}" topLeftX="30" topLeftY="130" width="400" height="300"><content fontSize="11"><p>Label</p></content></chart>',
                        f'<table id="{slot_id}" topLeftX="30" topLeftY="130" width="400" height="300"><tr><td><content fontSize="11"><p>Label</p></content></td></tr></table>']:
            self.assertTrue(self.api().validate_layout_contract(slide(self.title(contract),element),contract)['ok'])

    def test_real_r5_source32_and_unchanged_original18_subtitle_regression(self):
        # Optional local integration proof. Never patch or save either PPTX.
        relative_source = 'outputs/template-clone-policy-v2-20261104/cases/L3/inputs/blank_layout_template.pptx'
        relative_original = 'runs/template-reuse-20261105/round5-cli/runs/L3/smart-home-market-vendor-investor-briefing.pptx'
        base = next((p for p in SCRIPT.parents if (p/relative_source).is_file() and (p/relative_original).is_file()),None)
        if base is None: self.skipTest('Original R5 L3/source evidence is not present in this checkout')
        source = base/relative_source;original = base/relative_original
        before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in [source,original]]
        self.assertEqual(before,['128959ff9fcbb216184f55a263cc09985c6a6ec1aab8fa6169b4652250334726',
                                 '4d511781cf418bd98b578d6cfc5acb6a55f58ffb6b95a42fa92ab74b5432c833'])
        manifest = self.layout_api.inspect_template(source)
        contract = self.api().build_layout_contract(manifest,'Title Slide')
        slot = self.slot(contract,'subTitle');self.assertEqual(slot['sml_text_style']['fontSize'],'32')
        ns = {'p':self.fixture.P,'a':self.fixture.A}
        with zipfile.ZipFile(original) as archive:
            root = ET.fromstring(archive.read('ppt/slides/slide1.xml'))
        native = next(n for n in root.findall('.//p:sp',ns) if n.find('p:nvSpPr/p:cNvPr',ns).get('id')=='5')
        native_runs = [r for r in native.findall('.//a:r',ns) if r.find('a:t',ns).text]
        self.assertEqual([r.find('a:rPr',ns).get('sz') for r in native_runs],['1800','1800'])
        node = self.role_text(contract,'subTitle','');content = node.find('{*}content');p = content.find('{*}p')
        for run in native_runs:
            props = run.find('a:rPr',ns)
            span = ET.SubElement(p,'span',{'fontSize':str(float(props.get('sz'))/100),
                                         'fontFamily':props.find('a:latin',ns).get('typeface')})
            span.text = run.find('a:t',ns).text
        # This in-memory SML representation isolates native visible-run evidence.
        title_node = self.role_text(contract,'ctrTitle')
        result = self.api().validate_layout_contract(slide(ET.tostring(title_node,encoding='unicode'),ET.tostring(node,encoding='unicode')),contract,manifest=manifest)
        error = next(e for e in result['errors'] if e.get('role')=='subTitle' and e.get('property')=='fontSize')
        self.assertEqual((error['expected'],error['actual']),('32',['18.0']))
        self.assertTrue(any(w.get('reason')=='transformed_source_color' for w in result['warnings']))
        self.assertEqual(before,[hashlib.sha256(p.read_bytes()).hexdigest() for p in [source,original]])

    def test_source_hash_identifies_actual_input_without_mutating_it(self):
        before = self.pptx.read_bytes()
        self.assertEqual(self.manifest().get('source_sha256'), hashlib.sha256(before).hexdigest())
        self.assertEqual(self.pptx.read_bytes(), before)

    def test_skeleton_preserves_inherited_slots_and_uses_native_attributes_only(self):
        api = self.api()
        contract = self.contract()
        before = self.pptx.read_bytes()
        root = ET.fromstring(api.generate_skeleton(contract))
        nodes = root.findall('{*}data/{*}shape')
        title = next(n for n in nodes if n.get('id') == self.slot(contract, 'title')['slot_id'])
        self.assertEqual([title.get(k) for k in ('topLeftX','topLeftY','width','height')], ['20','30','700','80'])
        content = title.find('{*}content')
        self.assertEqual(content.get('fontFamily'), 'Major Font')
        self.assertEqual(content.get('fontSize'), '44')
        self.assertEqual(content.get('color'), 'rgb(17,34,51)')
        self.assertEqual(content.get('textType'), 'title')
        self.assertFalse(''.join(content.itertext()).strip())
        self.assertTrue(set(title.attrib) <= {'id','type','topLeftX','topLeftY','width','height'})
        self.assertEqual(api.generate_skeleton(contract), api.generate_skeleton(self.contract()))
        self.assertEqual(self.pptx.read_bytes(), before)

    def test_known_zero_page_geometry_and_different_canvas_are_not_fitted(self):
        for canvas, bbox, transform in [
            ((960,540), {'x':36,'y':21.62503937007874,'width':648,'height':90}, '<a:xfrm><a:off x="457200" y="274638"/><a:ext cx="8229600" cy="1143000"/></a:xfrm>'),
            ((600,800), {'x':15,'y':27,'width':570,'height':65}, self.fixture.xfrm(15,27,570,65))]:
            with self.subTest(canvas=canvas):
                self.fixture.fixture(self.pptx,*canvas)
                with zipfile.ZipFile(self.pptx) as archive:
                    parts = {name:archive.read(name) for name in archive.namelist()}
                part = 'ppt/slideMasters/slideMaster1.xml'
                parts[part] = parts[part].decode().replace(self.fixture.xfrm(20,30,700,80),transform).encode()
                with zipfile.ZipFile(self.pptx,'w') as archive:
                    for name,value in parts.items(): archive.writestr(name,value)
                manifest = self.manifest()
                contract = self.api().build_layout_contract(manifest, 'Inherited')
                title = ET.fromstring(self.api().generate_skeleton(contract)).find('{*}data/{*}shape')
                self.assertEqual(contract['canvas_sml']['width'], canvas[0])
                self.assertEqual([float(title.get(k)) for k in ('topLeftX','topLeftY','width','height')], list(bbox.values()))

    def test_layout_override_preserves_role_font_and_explicit_color(self):
        contract = self.contract('Override')
        title = ET.fromstring(self.api().generate_skeleton(contract)).find('{*}data/{*}shape')
        content = title.find('{*}content')
        self.assertEqual(self.slot(contract, 'title')['bbox'], {'x':40,'y':50,'width':500,'height':70})
        self.assertEqual(content.get('fontFamily'), 'Major Font')
        self.assertEqual(content.get('fontSize'), '28')
        self.assertEqual(content.get('bold'), 'false')
        self.assertEqual(content.get('color'), 'rgb(171,205,239)')
        self.assertEqual(self.slot(contract, 'obj')['sml_text_style']['fontFamily'], 'Minor Font')

    def test_missing_title_binding_fails_even_when_title_is_inside_slot(self):
        contract = self.contract()
        result = self.api().validate_layout_contract(slide(self.title(contract,'server-title')), contract)
        self.assertFalse(result['ok'])
        self.assertIn('missing_title_binding', self.codes(result))
        self.assertIn('unbound_content', self.codes(result))

    def test_explicit_binding_accepts_server_ids_and_native_chart_inside_content_slot(self):
        contract = self.contract()
        obj = self.slot(contract, 'obj')
        chart = '<chart id="server-chart" topLeftX="40" topLeftY="140" width="650" height="350"><chartPlotArea><chartPlot type="column"/></chartPlotArea><chartData><dim1><chartField name="Year">2024,2025</chartField></dim1><dim2><chartField name="Units">12,19</chartField></dim2></chartData></chart>'
        bindings = {'elements': {'server-title': self.slot(contract,'title')['slot_id'], 'server-chart': obj['slot_id']}}
        result = self.api().validate_layout_contract(slide(self.title(contract,'server-title'),chart), contract, bindings=bindings)
        self.assertTrue(result['ok'], result)
        self.assertEqual(result['checked_elements'], 2)

    def test_geometry_drift_and_outside_content_bbox_fail(self):
        contract = self.contract()
        title_id = self.slot(contract, 'title')['slot_id']
        bad_title = native_text(title_id,60,70,840,80)
        img = f'<img id="{self.slot(contract,"obj")["slot_id"]}" src="media_token" topLeftX="700" topLeftY="150" width="100" height="100"/>'
        result = self.api().validate_layout_contract(slide(bad_title,img), contract)
        self.assertIn('title_bbox_mismatch', self.codes(result))
        self.assertIn('outside_slot_bbox', self.codes(result))

    def test_title_cannot_keep_geometry_but_adopt_new_deck_typography(self):
        contract=self.contract();title=self.title(contract)
        node=ET.fromstring(title);content=node.find('content')
        content.set('fontSize','24');content.set('fontFamily','Georgia');content.set('color','rgba(11,58,94,1)')
        result=self.api().validate_layout_contract(slide(ET.tostring(node,encoding='unicode')),contract)
        self.assertIn('title_style_mismatch',self.codes(result))
        self.assertEqual({e['property'] for e in result['errors'] if e['code']=='title_style_mismatch'}, {'fontSize','fontFamily','color'})

    def test_visible_run_style_is_checked_instead_of_unused_content_default(self):
        contract=self.contract();node=ET.fromstring(self.title(contract));content=node.find('content')
        original=dict(content.attrib);content.set('fontSize','16')
        p=content.find('p');p.text=None;span=ET.SubElement(p,'span',{'fontSize':original['fontSize']});span.text='Actual title'
        result=self.api().validate_layout_contract(slide(ET.tostring(node,encoding='unicode')),contract)
        self.assertTrue(result['ok'],result)
        span.set('fontSize','24')
        self.assertIn('title_style_mismatch',self.codes(self.api().validate_layout_contract(slide(ET.tostring(node,encoding='unicode')),contract)))

    def test_equivalent_colors_and_explicit_unavailable_font_substitution(self):
        contract=self.contract();node=ET.fromstring(self.title(contract));content=node.find('content')
        content.set('color','rgba(17, 34, 51, 1)');content.set('fontFamily','Compatible Font')
        slot=self.slot(contract,'title')['slot_id']
        bindings={'font_substitutions':{slot:{'fontFamily':'Compatible Font','reason':'Original font unavailable; same serif role retained'}}}
        result=self.api().validate_layout_contract(slide(ET.tostring(node,encoding='unicode')),contract,bindings=bindings)
        self.assertTrue(result['ok'],result)
        bindings['font_substitutions'][slot]['reason']=''
        self.assertFalse(self.api().validate_layout_contract(slide(ET.tostring(node,encoding='unicode')),contract,bindings=bindings)['ok'])

    def test_source_style_cannot_be_edited_to_approve_small_title(self):
        manifest=self.manifest();contract=self.contract();contract['slots'][0]['sml_text_style']['fontSize']='24'
        result=self.api().validate_layout_contract(slide(self.title(contract)),contract,manifest=manifest)
        self.assertIn('source_slot_mismatch',self.codes(result))

    def east_asian_manifest(self, family='Source CJK'):
        # Real OOXML font fields must be parsed by the existing extractor.
        with zipfile.ZipFile(self.pptx) as archive:
            parts={name:archive.read(name) for name in archive.namelist()}
        name='ppt/slideMasters/slideMaster1.xml'
        parts[name]=parts[name].decode().replace('<a:latin typeface="+mj-lt"/>',f'<a:latin typeface="+mj-lt"/><a:ea typeface="{family}"/>',1).encode()
        with zipfile.ZipFile(self.pptx,'w') as archive:
            for name,value in parts.items(): archive.writestr(name,value)
        return self.manifest()

    def test_chinese_title_inherits_source_east_asian_font_without_substitution(self):
        manifest=self.east_asian_manifest()
        contract=self.api().build_layout_contract(manifest,'Inherited')
        node=ET.fromstring(self.title(contract));content=node.find('content')
        content.set('fontFamily','Source CJK');content.find('p').text='市场增长来自存量升级'
        result=self.api().validate_layout_contract(slide(ET.tostring(node,encoding='unicode')),contract,manifest=manifest)
        self.assertTrue(result['ok'],result)
        self.assertFalse(any(w.get('code')=='declared_title_font_substitution' for w in result['warnings'] if isinstance(w,dict)))
        self.assertEqual(self.slot(contract,'title')['sml_font_families']['east_asian'],'Source CJK')

    def test_source_cjk_does_not_allow_wrong_english_font_or_smaller_title(self):
        manifest=self.east_asian_manifest();contract=self.api().build_layout_contract(manifest,'Inherited')
        node=ET.fromstring(self.title(contract));content=node.find('content')
        content.set('fontFamily','Georgia');content.find('p').text='Market growth'
        result=self.api().validate_layout_contract(slide(ET.tostring(node,encoding='unicode')),contract,manifest=manifest)
        self.assertEqual({e['property'] for e in result['errors'] if e['code']=='title_style_mismatch'},{'fontFamily'})
        content.set('fontFamily','Source CJK');content.set('fontSize','24');content.find('p').text='市场增长'
        result=self.api().validate_layout_contract(slide(ET.tostring(node,encoding='unicode')),contract,manifest=manifest)
        self.assertEqual({e['property'] for e in result['errors'] if e['code']=='title_style_mismatch'},{'fontSize'})

    def test_mixed_title_spans_inherit_each_source_font_role(self):
        manifest=self.east_asian_manifest();contract=self.api().build_layout_contract(manifest,'Inherited')
        node=ET.fromstring(self.title(contract));p=node.find('content/p');p.text=None
        english=ET.SubElement(p,'span',{'fontFamily':'Major Font'});english.text='AI '
        chinese=ET.SubElement(p,'span',{'fontFamily':'Source CJK'});chinese.text='推动升级'
        result=self.api().validate_layout_contract(slide(ET.tostring(node,encoding='unicode')),contract,manifest=manifest)
        self.assertTrue(result['ok'],result)
        english.set('fontFamily','Georgia')
        self.assertIn('title_style_mismatch',self.codes(self.api().validate_layout_contract(slide(ET.tostring(node,encoding='unicode')),contract,manifest=manifest)))

    def test_common_numeric_run_can_keep_source_latin_inside_chinese_title(self):
        manifest=self.east_asian_manifest();contract=self.api().build_layout_contract(manifest,'Inherited')
        node=ET.fromstring(self.title(contract));p=node.find('content/p');p.text=None
        chinese=ET.SubElement(p,'span',{'fontFamily':'Source CJK'});chinese.text='增长 '
        digits=ET.SubElement(p,'span',{'fontFamily':'Major Font'});digits.text='2026'
        result=self.api().validate_layout_contract(slide(ET.tostring(node,encoding='unicode')),contract,manifest=manifest)
        self.assertTrue(result['ok'],result)
        digits.set('fontFamily','Source CJK')
        self.assertTrue(self.api().validate_layout_contract(slide(ET.tostring(node,encoding='unicode')),contract,manifest=manifest)['ok'])
        digits.set('fontFamily','Georgia')
        self.assertFalse(self.api().validate_layout_contract(slide(ET.tostring(node,encoding='unicode')),contract,manifest=manifest)['ok'])

    def test_theme_script_font_is_inherited_when_east_asian_theme_family_is_empty(self):
        manifest=self.east_asian_manifest('+mj-ea');contract=self.api().build_layout_contract(manifest,'Inherited')
        node=ET.fromstring(self.title(contract));content=node.find('content')
        content.set('fontFamily','CJK Major');content.find('p').text='市场增长'
        result=self.api().validate_layout_contract(slide(ET.tostring(node,encoding='unicode')),contract,manifest=manifest)
        self.assertTrue(result['ok'],result)
        self.assertEqual(self.slot(contract,'title')['sml_font_families']['scripts']['Hans'],'CJK Major')
        content.set('fontFamily','Major Font')
        self.assertIn('title_style_mismatch',self.codes(self.api().validate_layout_contract(slide(ET.tostring(node,encoding='unicode')),contract,manifest=manifest)))

    def test_japanese_korean_and_source_locale_select_real_theme_script_fonts(self):
        manifest=self.east_asian_manifest('+mj-ea')
        fonts=manifest['themes'][0]['fonts']['major']['scripts']
        fonts.update({'Hant':'Traditional Source','Jpan':'Japanese Source','Hang':'Korean Source'})
        for text,family,locale in [('かな市場','Japanese Source','en-US'),('한국 시장','Korean Source','en-US'),('市場成長','Traditional Source','zh-TW')]:
            with self.subTest(text=text):
                title=manifest['layouts'][0]['placeholders'][0]
                title['text_style']['default']['language']={'value':locale,'source':'fixture/paragraph'}
                contract=self.api().build_layout_contract(manifest,'Inherited')
                node=ET.fromstring(self.title(contract));content=node.find('content');content.set('fontFamily',family);content.find('p').text=text
                result=self.api().validate_layout_contract(slide(ET.tostring(node,encoding='unicode')),contract,manifest=manifest)
                self.assertTrue(result['ok'],result)

    def test_source_script_font_metadata_cannot_be_edited_to_approve_georgia(self):
        manifest=self.east_asian_manifest();contract=self.api().build_layout_contract(manifest,'Inherited')
        self.slot(contract,'title').setdefault('sml_font_families',{})['east_asian']='Georgia'
        node=ET.fromstring(self.title(contract));content=node.find('content');content.set('fontFamily','Georgia');content.find('p').text='市场增长'
        self.assertIn('source_slot_mismatch',self.codes(self.api().validate_layout_contract(slide(ET.tostring(node,encoding='unicode')),contract,manifest=manifest)))

    def test_smaller_title_cannot_evade_exact_title_geometry(self):
        contract = self.contract()
        small = native_text(self.slot(contract,'title')['slot_id'],25,35,100,20)
        result = self.api().validate_layout_contract(slide(small), contract)
        self.assertIn('title_bbox_mismatch', self.codes(result))

    def test_invalid_layout_and_stale_manifest_are_reported(self):
        api = self.api()
        manifest = self.manifest()
        with self.assertRaises(ValueError): api.build_layout_contract(manifest, 'Invented Layout')
        contract = self.contract()
        broken = copy.deepcopy(contract)
        broken['layout']['name'] = 'Invented Layout'
        result = api.validate_layout_contract(slide(self.title(contract)), broken, manifest=manifest)
        self.assertIn('invalid_layout', self.codes(result))
        manifest['canvas_sml']['width'] = 960
        result = api.validate_layout_contract(slide(self.title(contract)), contract, manifest=manifest)
        self.assertIn('manifest_mismatch', self.codes(result))

    def test_contract_cannot_replace_source_geometry_or_role_to_bypass_validation(self):
        manifest = self.manifest()
        contract = self.contract()
        title_slot = self.slot(contract,'title')
        title_slot['bbox'] = {'x':60,'y':70,'width':840,'height':80}
        title_slot['geometry'] = 'contain'
        result = self.api().validate_layout_contract(slide(self.title(contract)),contract,manifest=manifest)
        self.assertIn('source_slot_mismatch',self.codes(result))

    def test_real_decoration_is_excluded_but_text_cannot_be_hidden_as_decoration(self):
        contract = self.contract()
        deco = '<shape id="background" type="rect" topLeftX="0" topLeftY="0" width="1200" height="675"><fill><fillColor color="rgb(255,255,255)"/></fill><content><p/></content></shape>'
        logo = '<img id="logo" src="media_logo" topLeftX="1100" topLeftY="0" width="70" height="70"/>'
        bindings = {'decorative_ids':['logo']}
        result = self.api().validate_layout_contract(slide(deco,logo,self.title(contract)), contract, bindings=bindings)
        self.assertTrue(result['ok'], result)
        result = self.api().validate_layout_contract(slide(self.title(contract,'fake-deco')), contract, bindings={'decorative_ids':['fake-deco']})
        self.assertIn('invalid_decorative_binding', self.codes(result))

    def test_title_only_never_guesses_free_area_and_explicit_region_allows_table(self):
        manifest = self.manifest()
        layout = manifest['layouts'][0]
        layout['name'] = 'Title Only'
        layout['type'] = 'titleOnly'
        layout['placeholders'] = [p for p in layout['placeholders'] if p['role'] != 'obj']
        api = self.api()
        contract = api.build_layout_contract(manifest,'Title Only')
        table = '<table id="table" topLeftX="30" topLeftY="140" width="500" height="250"><colgroup><col width="500"/></colgroup><tr height="250"><td><content fontSize="20"><p>Findings</p></content></td></tr></table>'
        result = api.validate_layout_contract(slide(self.title(contract),table),contract)
        self.assertIn('unbound_content',self.codes(result))
        contract = api.build_layout_contract(manifest,'Title Only',free_regions=[{'name':'analysis','bbox':{'x':20,'y':120,'width':700,'height':400},'allowed_kinds':['text','table']}])
        region = next(s for s in contract['slots'] if s['role']=='free')
        result = api.validate_layout_contract(slide(self.title(contract),table),contract,bindings={'elements':{'table':region['slot_id']}})
        self.assertTrue(result['ok'], result)

    def test_specialized_chart_slot_rejects_body_text_and_accepts_native_chart(self):
        manifest = self.manifest()
        manifest['layouts'][0]['placeholders'][1]['role']='chart'
        contract = self.api().build_layout_contract(manifest,'Inherited')
        slot_id = self.slot(contract,'chart')['slot_id']
        result = self.api().validate_layout_contract(slide(self.title(contract),native_text(slot_id,30,130,400,100,'Copy','body')),contract)
        self.assertIn('slot_kind_mismatch',self.codes(result))
        chart = f'<chart id="{slot_id}" topLeftX="30" topLeftY="130" width="400" height="300"><chartPlotArea><chartPlot type="line"/></chartPlotArea><chartData><dim1><chartField name="Quarter">Q1,Q2</chartField></dim1><dim2><chartField name="Revenue">2,3</chartField></dim2></chartData></chart>'
        self.assertTrue(self.api().validate_layout_contract(slide(self.title(contract),chart),contract)['ok'])

    def test_contract_cli_creates_two_new_artifacts_and_refuses_overwrite(self):
        manifest = self.root/'layouts.json'
        manifest.write_text(json.dumps(self.manifest()))
        output = self.root/'contract.json'
        skeleton = self.root/'slide.xml'
        cmd=[sys.executable,str(SCRIPT),'--manifest',str(manifest),'--layout','Override','--output',str(output),'--skeleton',str(skeleton)]
        first=subprocess.run(cmd,capture_output=True,text=True)
        self.assertEqual(first.returncode,0,first.stderr)
        before=(output.read_bytes(),skeleton.read_bytes(),manifest.read_bytes(),self.pptx.read_bytes())
        second=subprocess.run(cmd,capture_output=True,text=True)
        self.assertNotEqual(second.returncode,0)
        self.assertEqual(before,(output.read_bytes(),skeleton.read_bytes(),manifest.read_bytes(),self.pptx.read_bytes()))

    def test_malformed_geometry_and_bindings_return_errors_instead_of_crashing(self):
        contract = self.contract()
        api = self.api()
        malformed = self.title(contract).replace('height="80.0"','height="nan"')
        self.assertIn('missing_element_bbox',self.codes(api.validate_layout_contract(slide(malformed),contract)))
        malformed = self.title(contract).replace('type="text"','rotation="broken" type="text"')
        self.assertIn('invalid_element_rotation',self.codes(api.validate_layout_contract(slide(malformed),contract)))
        self.assertIn('invalid_bindings',self.codes(api.validate_layout_contract(slide(self.title(contract)),contract,bindings=[])))
        self.assertIn('invalid_bindings',self.codes(api.validate_layout_contract(slide(self.title(contract)),contract,bindings={'decorative_ids':'all'})))

    def test_malformed_contract_structure_returns_invalid_contract(self):
        api = self.api()
        contract = self.contract()
        authored = slide(self.title(contract))
        cases = [None, [], 'contract',
                 {**contract,'slots':[None]}, {**contract,'slots':None},
                 {**contract,'layout':None}, {**contract,'slots':{'title':'slot'}},
                 {**contract,'slots':[{'slot_id':[]}]}]
        for malformed in cases:
            with self.subTest(contract=malformed):
                result = api.validate_layout_contract(authored,malformed,manifest=self.manifest())
                self.assertFalse(result['ok'])
                self.assertIn('invalid_contract',self.codes(result))

    def test_validation_cli_reports_malformed_slot_in_json(self):
        contract = self.contract()
        malformed = self.root/'malformed.json'
        malformed.write_text(json.dumps({**contract,'slots':[None]}))
        authored = self.root/'authored.xml'
        authored.write_text(slide(self.title(contract)))
        result = subprocess.run([sys.executable,str(SCRIPT),'--contract',str(malformed),'--sml',str(authored)],capture_output=True,text=True)
        self.assertEqual(result.returncode,1)
        self.assertIn('invalid_contract',self.codes(json.loads(result.stdout)))

    def test_explicit_index_bindings_accept_authoring_without_custom_ids(self):
        contract = self.contract()
        title = self.title(contract).replace(f' id="{self.slot(contract,"title")["slot_id"]}"','')
        result = self.api().validate_layout_contract(slide(title),contract,bindings={'elements':{'data_index:0':self.slot(contract,'title')['slot_id']}})
        self.assertTrue(result['ok'],result)

    def test_cli_output_pair_failure_leaves_no_partial_contract(self):
        manifest = self.root/'layouts.json'
        manifest.write_text(json.dumps(self.manifest()))
        output = self.root/'contract.json'
        skeleton = self.root/'missing-dir'/'slide.xml'
        cmd=[sys.executable,str(SCRIPT),'--manifest',str(manifest),'--layout','Inherited','--output',str(output),'--skeleton',str(skeleton)]
        self.assertNotEqual(subprocess.run(cmd,capture_output=True).returncode,0)
        self.assertFalse(output.exists())


if __name__=='__main__': unittest.main()
