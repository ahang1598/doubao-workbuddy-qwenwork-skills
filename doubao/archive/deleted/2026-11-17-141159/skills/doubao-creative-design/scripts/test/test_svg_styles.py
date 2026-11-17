"""SVG cascade, editable text and fail-closed conversion regressions."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from urllib.parse import unquote
import tinycss2

SCRIPT=Path(__file__).resolve().parents[1]/'runtime/inline-svg-assets.py'
spec=importlib.util.spec_from_file_location('styled_svg_assets',SCRIPT)
svg=importlib.util.module_from_spec(spec);spec.loader.exec_module(svg)
NS='{http://www.w3.org/2000/svg}'

def declarations(node):
    return {d.lower_name:(tinycss2.serialize(d.value).strip(),d.important)
            for d in tinycss2.parse_declaration_list(node.get('style','')) if d.type=='declaration'}

class SVGStyleTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);(self.root/'svg').mkdir()

    def write(self,body):
        text='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 40">'+body+'</svg>'
        (self.root/'svg/test.svg').write_text(text)
        return text

    def test_static_cascade_is_applied_before_id_scoping(self):
        self.write('<style>text{fill:black}.title{fill:green}#title{fill:red}.title{fill:blue!important}g > text.title{stroke:orange}#title{font-size:18px}</style><g><text id="title" class="title" style="fill:purple;font-size:20px">准确标题</text></g>')
        out,_=svg.inline_assets('<!-- svg-inline:svg/test.svg -->',self.root)
        root=ET.fromstring(out);text=root.find('.//'+NS+'text')
        self.assertIsNone(root.find('.//'+NS+'style'))
        self.assertNotEqual(text.get('id'),'title')
        self.assertEqual(text.text,'准确标题')
        values=declarations(text)
        self.assertEqual(values['fill'],('blue',True))
        self.assertEqual(values['font-size'][0],'20px')
        self.assertEqual(values['stroke'][0],'orange')

    def test_important_inline_and_source_order(self):
        self.write('<style>.a,.b{fill:green}.a{fill:red}.b{stroke:black!important}</style><text class="a">A</text><text class="b" style="stroke:orange!important">B</text>')
        out,_=svg.inline_assets('<!-- svg-inline:svg/test.svg -->',self.root)
        texts=ET.fromstring(out).findall(NS+'text')
        self.assertEqual(declarations(texts[0])['fill'][0],'red')
        self.assertEqual(declarations(texts[1])['stroke'],('orange',True))

    def test_css_urls_href_and_accessibility_use_instance_ids(self):
        self.write('<style>#title{fill:url(#paint);filter:url("#blur")}</style><defs><linearGradient id="paint"/><filter id="blur"/><path id="arc" d="M0 20H100"/></defs><title id="label">说明</title><text id="title" aria-labelledby="label"><textPath href="#arc">中文 &amp; A</textPath></text>')
        out,_=svg.inline_assets('<!-- svg-inline:svg/test.svg --><!-- svg-inline:svg/test.svg -->',self.root)
        roots=list(ET.fromstring('<root>'+out+'</root>'))
        all_ids=[]
        for root in roots:
            ids={n.get('id') for n in root.iter() if n.get('id')};all_ids.extend(ids)
            text=root.find(NS+'text');values=declarations(text)
            for key in ['fill','filter']:
                target=values[key][0].split('#')[1].strip(')\"\' ')
                self.assertIn(target,ids)
            self.assertIn(text.get('aria-labelledby'),ids)
            self.assertIn(text.find(NS+'textPath').get('href')[1:],ids)
            self.assertEqual(text.find(NS+'textPath').text,'中文 & A')
        self.assertEqual(len(all_ids),len(set(all_ids)))

    def test_encoded_and_escaped_local_references(self):
        for fill in [r'url(#p\61 int)', 'url(#%70aint)', r'url(&quot;\23 paint&quot;)']:
            for styled in [False, True]:
                with self.subTest(fill=fill, styled=styled):
                    style = '<style>rect{stroke:red}</style>' if styled else ''
                    self.write(style+'<defs><linearGradient id="paint"/><path id="arc"/></defs><rect fill="'+fill+'"/><use href="#%61rc"/>')
                    out,_=svg.inline_assets('<!-- svg-inline:svg/test.svg -->',self.root)
                    root=ET.fromstring(out)
                    paint=root.find('.//'+NS+'linearGradient').get('id')
                    arc=root.find('.//'+NS+'path').get('id')
                    self.assertIn('#'+paint,root.find(NS+'rect').get('fill'))
                    self.assertEqual(root.find(NS+'use').get('href'),'#'+arc)

    def test_escaped_external_url_without_stylesheet_is_rejected(self):
        self.write(r'<rect style="fill:u\72l(https://example.com/a.svg#paint)"/>')
        with self.assertRaisesRegex(ValueError, 'external CSS URL'):
            svg.inline_assets('<!-- svg-inline:svg/test.svg -->',self.root)

    def test_data_uri_keeps_independent_svg_styles(self):
        source=self.write('<style>#title{fill:red}</style><text id="title">A</text>')
        uri,_=svg.inline_assets('asset:svg/test.svg',self.root)
        self.assertEqual(unquote(uri.split(',',1)[1]),source)

    def test_unsupported_rules_fail_and_existing_output_survives(self):
        for css in ['@media(min-width:10px){text{fill:red}}','text:hover{fill:red}','text::before{content:"x"}','text { fill: red; broken }']:
            with self.subTest(css=css):
                self.write('<style>'+css+'</style><text>A</text>')
                with self.assertRaises(ValueError):svg.inline_assets('<!-- svg-inline:svg/test.svg -->',self.root)
        input_file=self.root/'draft.html';input_file.write_text('<!-- svg-inline:svg/test.svg -->')
        output=self.root/'out.html';output.write_text('previous output')
        run=subprocess.run([sys.executable,str(SCRIPT),'--input',str(input_file),'--output',str(output),'--asset-root',str(self.root),'--force'],capture_output=True,text=True)
        self.assertNotEqual(run.returncode,0)
        self.assertEqual(output.read_text(),'previous output')

if __name__=='__main__':unittest.main()
