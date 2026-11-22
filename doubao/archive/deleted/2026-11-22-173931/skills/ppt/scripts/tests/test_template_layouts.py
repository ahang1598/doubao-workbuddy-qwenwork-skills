"""Behavior tests for zero-slide PPTX layout extraction (stdlib-only fixtures)."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

SCRIPT = Path(__file__).resolve().parents[1] / 'template' / 'template_layouts.py'
P = 'http://schemas.openxmlformats.org/presentationml/2006/main'
A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
PKG = 'http://schemas.openxmlformats.org/package/2006/relationships'


def module():
    assert SCRIPT.exists(), 'template_layouts.py helper is missing'
    spec = importlib.util.spec_from_file_location('template_layouts', SCRIPT)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def xfrm(x, y, w, h):
    return f'<a:xfrm><a:off x="{x * 12700}" y="{y * 12700}"/><a:ext cx="{w * 12700}" cy="{h * 12700}"/></a:xfrm>'


def shape(number, role, idx, transform='', text_style=''):
    return f'''<p:sp><p:nvSpPr><p:cNvPr id="{number}" name="slot-{number}"/><p:cNvSpPr/><p:nvPr><p:ph type="{role}" idx="{idx}"/></p:nvPr></p:nvSpPr><p:spPr>{transform}</p:spPr><p:txBody><a:bodyPr/><a:lstStyle/>{text_style or '<a:p/>'}</p:txBody></p:sp>'''


def fixture(path, width=1200, height=675, external_master=False):
    def root(tag, content, attrs=''):
        return f'<p:{tag} xmlns:p="{P}" xmlns:a="{A}" xmlns:r="{R}" {attrs}>{content}</p:{tag}>'
    def rels(items):
        return f'<Relationships xmlns="{PKG}">' + ''.join(f'<Relationship Id="{i}" Type="{R}/{kind}" Target="{target}" {extra}/>' for i,kind,target,extra in items) + '</Relationships>'
    master_shapes = shape(1,'title',0,xfrm(20,30,700,80)) + shape(2,'body',1,xfrm(20,120,700,400)) + shape(3,'ftr',9,xfrm(200,600,200,20))
    master_styles = '<p:txStyles><p:titleStyle><a:lvl1pPr><a:defRPr sz="4400" b="1"><a:latin typeface="+mj-lt"/><a:solidFill><a:schemeClr val="tx1"/></a:solidFill></a:defRPr></a:lvl1pPr></p:titleStyle><p:bodyStyle><a:lvl1pPr><a:defRPr sz="2400"><a:latin typeface="+mn-lt"/></a:defRPr></a:lvl1pPr></p:bodyStyle><p:otherStyle/></p:txStyles>'
    override = '<a:p><a:pPr><a:defRPr sz="2800"/></a:pPr><a:r><a:rPr b="0"><a:solidFill><a:srgbClr val="ABCDEF"/></a:solidFill></a:rPr><a:t>Example title</a:t></a:r></a:p>'
    files = {
        'ppt/presentation.xml': root('presentation', '<p:sldMasterIdLst><p:sldMasterId id="1" r:id="m1"/></p:sldMasterIdLst><p:sldIdLst/>' + f'<p:sldSz cx="{width*12700}" cy="{height*12700}"/>'),
        'ppt/_rels/presentation.xml.rels': rels([('m1','slideMaster','slideMasters/slideMaster1.xml','')]),
        'ppt/slideMasters/slideMaster1.xml': root('sldMaster','<p:cSld><p:spTree>'+master_shapes+'</p:spTree></p:cSld><p:clrMap bg1="lt1" tx1="dk1" accent1="accent1"/>'+master_styles),
        'ppt/slideMasters/_rels/slideMaster1.xml.rels': rels([('t1','theme','../theme/theme1.xml','')]),
        'ppt/slideLayouts/slideLayout1.xml': root('sldLayout','<p:cSld name="Inherited"><p:spTree>'+shape(1,'title',0)+shape(2,'obj',7)+shape(3,'ftr',12)+'</p:spTree></p:cSld>', 'type="obj"'),
        'ppt/slideLayouts/slideLayout2.xml': root('sldLayout','<p:cSld name="Override"><p:spTree>'+shape(1,'title',0,xfrm(40,50,500,70),override)+shape(2,'obj',1,xfrm(100,150,400,300))+'</p:spTree></p:cSld>', 'type="obj"'),
        'ppt/theme/theme1.xml': f'<a:theme xmlns:a="{A}" name="Test"><a:themeElements><a:clrScheme name="Colors"><a:dk1><a:srgbClr val="112233"/></a:dk1><a:lt1><a:sysClr val="window" lastClr="FFFFFF"/></a:lt1><a:accent1><a:srgbClr val="445566"/></a:accent1></a:clrScheme><a:fontScheme name="Fonts"><a:majorFont><a:latin typeface="Major Font"/><a:ea typeface=""/><a:font script="Hans" typeface="CJK Major"/></a:majorFont><a:minorFont><a:latin typeface="Minor Font"/></a:minorFont></a:fontScheme></a:themeElements></a:theme>',
    }
    for n in (1,2):
        target = 'https://example.invalid/master.xml' if external_master else '../slideMasters/slideMaster1.xml'
        files[f'ppt/slideLayouts/_rels/slideLayout{n}.xml.rels'] = rels([('m1','slideMaster',target,'TargetMode="External"' if external_master else '')])
    with zipfile.ZipFile(path, 'w') as archive:
        for name, data in files.items(): archive.writestr(name,data)


class LayoutTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.pptx = self.root/'template.pptx'
        fixture(self.pptx)

    def replace_part(self, name, transform):
        with zipfile.ZipFile(self.pptx) as z:
            files={n:z.read(n) for n in z.namelist()}
        files[name]=transform(files[name].decode()).encode()
        with zipfile.ZipFile(self.pptx,'w') as z:
            for n,data in files.items(): z.writestr(n,data)

    def inspect(self):
        return module().inspect_template(self.pptx)

    def test_zero_slides_and_real_canvas_without_rescaling_slots(self):
        for width,height in [(1200,675),(600,800)]:
            fixture(self.pptx,width,height)
            data=self.inspect()
            self.assertEqual(data['slide_count'],0)
            self.assertEqual(data['canvas_sml'],{'width':width,'height':height,'unit':'px','emu_per_px':12700})
            self.assertEqual(len(data['layouts']),2)
            self.assertEqual(data['layouts'][0]['placeholders'][0]['bbox'],{'x':20,'y':30,'width':700,'height':80})

    def test_inherits_by_role_when_layout_idx_differs_from_master(self):
        slots=self.inspect()['layouts'][0]['placeholders']
        self.assertEqual(slots[1]['role'],'obj')
        self.assertEqual(slots[1]['idx'],7)
        self.assertEqual(slots[1]['bbox'],{'x':20,'y':120,'width':700,'height':400})
        self.assertEqual(slots[1]['bbox_source']['level'],'master')
        self.assertEqual(slots[2]['bbox']['x'],200)
        self.assertEqual(slots[2]['master_placeholder']['idx'],9)

    def test_specialized_content_placeholders_inherit_body_bbox_and_font(self):
        # Legal content roles share the master body slot even with different idx.
        # Both geometry lookup and bodyStyle selection must use this mapping.
        for role in ['chart', 'tbl', 'pic', 'dgm', 'media', 'clipArt']:
            with self.subTest(role=role):
                fixture(self.pptx)
                name='ppt/slideLayouts/slideLayout1.xml'
                self.replace_part(name, lambda s:s.replace('type="obj" idx="7"', f'type="{role}" idx="7"'))
                slot=self.inspect()['layouts'][0]['placeholders'][1]
                self.assertEqual(slot['role'],role)
                self.assertEqual(slot['bbox'],{'x':20,'y':120,'width':700,'height':400})
                self.assertEqual(slot['master_placeholder']['role'],'body')
                style=slot['text_style']['default']
                self.assertEqual(style['font_latin']['value'],'+mn-lt')
                self.assertEqual(style['font_size_pt']['value'],24)
                self.assertIn('/txStyles/bodyStyle',style['font_latin']['source'])

    def test_layout_geometry_and_style_override_preserves_inherited_font(self):
        layout=self.inspect()['layouts'][1]
        self.assertEqual(layout['name'],'Override')
        self.assertEqual(layout['type'],'obj')
        self.assertEqual(layout['source_file'],'ppt/slideLayouts/slideLayout2.xml')
        slot=layout['placeholders'][0]
        self.assertEqual(slot['bbox'],{'x':40,'y':50,'width':500,'height':70})
        self.assertEqual(slot['bbox_source']['level'],'layout')
        style=slot['text_style']['default']
        self.assertEqual(style['font_size_pt']['value'],28)
        self.assertEqual(style['bold']['value'],False)
        self.assertEqual(style['font_latin']['value'],'+mj-lt')
        self.assertIn('slideMaster1.xml',style['font_latin']['source'])
        self.assertIn('slideLayout2.xml',style['font_size_pt']['source'])
        self.assertEqual(style['color']['value']['value'],'ABCDEF')

    def test_partial_transform_keeps_local_position_and_inherited_size(self):
        # Removing per-component inheritance would silently discard the local move.
        name='ppt/slideLayouts/slideLayout1.xml'
        self.replace_part(name, lambda s:s.replace('<p:spPr></p:spPr>', '<p:spPr><a:xfrm><a:off x="508000" y="635000"/></a:xfrm></p:spPr>',1))
        slot=self.inspect()['layouts'][0]['placeholders'][0]
        self.assertEqual(slot['bbox'],{'x':40,'y':50,'width':700,'height':80})
        self.assertEqual(slot['bbox_source']['level'],'mixed')
        self.assertEqual(slot['bbox_source']['components']['x']['level'],'layout')
        self.assertEqual(slot['bbox_source']['components']['width']['level'],'master')

    def test_idx_disambiguates_multiple_master_slots_of_the_same_role(self):
        name='ppt/slideMasters/slideMaster1.xml'
        self.replace_part(name,lambda s:s.replace('</p:spTree>',shape(4,'body',7,xfrm(300,150,250,330))+'</p:spTree>'))
        slot=self.inspect()['layouts'][0]['placeholders'][1]
        self.assertEqual(slot['bbox'],{'x':300,'y':150,'width':250,'height':330})
        self.assertEqual(slot['master_match_rule'],'role_and_idx')

    def test_theme_colors_fonts_and_references_are_discoverable(self):
        data=self.inspect()
        theme=data['themes'][0]
        self.assertEqual(theme['colors']['dk1']['value'],'112233')
        self.assertEqual(theme['fonts']['major']['latin'],'Major Font')
        self.assertEqual(theme['fonts']['major']['scripts']['Hans'],'CJK Major')
        self.assertEqual(data['masters'][0]['color_map']['tx1'],'dk1')
        self.assertIn('+mj-lt',data['masters'][0]['references']['font_tokens'])
        self.assertIn('tx1',data['masters'][0]['references']['scheme_colors'])

    def test_external_master_is_never_fetched_or_guessed(self):
        fixture(self.pptx,external_master=True)
        data=self.inspect()
        self.assertIsNone(data['layouts'][0]['placeholders'][0]['bbox'])
        self.assertTrue(data['warnings'])

    def test_cli_writes_json_and_refuses_existing_output(self):
        # Production bug caught: replacing exclusive creation with overwrite destroys evidence.
        output=self.root/'layouts.json'
        cmd=[sys.executable,str(SCRIPT),'--pptx',str(self.pptx),'--output',str(output)]
        first=subprocess.run(cmd,capture_output=True,text=True)
        self.assertEqual(first.returncode,0,first.stderr)
        self.assertEqual(json.loads(output.read_text())['slide_count'],0)
        before=output.read_bytes()
        second=subprocess.run(cmd,capture_output=True,text=True)
        self.assertNotEqual(second.returncode,0)
        self.assertIn('exists',second.stderr.lower())
        self.assertEqual(output.read_bytes(),before)
        original=self.pptx.read_bytes()
        cmd[-1]=str(self.pptx)
        self.assertNotEqual(subprocess.run(cmd,capture_output=True).returncode,0)
        self.assertEqual(self.pptx.read_bytes(),original)

    def test_rejects_missing_canvas_without_writing_output(self):
        with zipfile.ZipFile(self.pptx,'w') as z:z.writestr('ppt/presentation.xml',f'<p:presentation xmlns:p="{P}"/>')
        output=self.root/'invalid.json'
        result=subprocess.run([sys.executable,str(SCRIPT),'--pptx',str(self.pptx),'--output',str(output)],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('canvas',result.stderr)
        self.assertFalse(output.exists())


if __name__=='__main__': unittest.main()
