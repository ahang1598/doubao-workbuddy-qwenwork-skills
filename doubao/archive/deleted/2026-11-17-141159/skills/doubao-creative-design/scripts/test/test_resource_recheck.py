"""ModelHub findings: malformed fonts, safe fetch and both SVG modes."""
import hashlib
import io
import json
from pathlib import Path
import struct
import sys
from contextlib import redirect_stdout
from unittest.mock import patch
import test_font_resources as fonts
from test_font_resources import font_file, resolver, TTFont, TTCollection
import test_svg_styles as svgtests
from test_svg_styles import svg
from urllib.parse import unquote

# Reuse only fixtures; do not duplicate the inherited test methods.
import unittest
class FontRecheckTests(unittest.TestCase):
    setUp = fonts.FontResourceTests.setUp

    def test_invalid_glyph_count_ttf_and_ttc(self):
        a=font_file(self.root/'a.ttf',text='A')
        collection=TTCollection();collection.fonts=[TTFont(a),TTFont(a)]
        collection.save(self.root/'a.ttc');collection.close()
        for p in [a,self.root/'a.ttc']:
            data=bytearray(p.read_bytes());base=resolver.sfnt_offsets(bytes(data))[-1]
            offset=resolver.sfnt_tables(bytes(data),base)[b'maxp'][0]
            struct.pack_into('>H',data,offset+4,1);p.write_bytes(data)
            self.assertEqual(resolver.font_metadata([p],'A')['coverage_status'],'not_supported')

    def test_format12_glyph_range_is_checked(self):
        p=font_file(self.root/'astral.ttf',text='😀')
        data=bytearray(p.read_bytes());tables=resolver.sfnt_tables(bytes(data),0)
        for offset in resolver.cmap_subtables(bytes(data),tables):
            if resolver.unpack_u16(data,offset)==12:
                struct.pack_into('>I',data,offset+24,999)
        p.write_bytes(data)
        self.assertEqual(resolver.font_metadata([p],'😀')['coverage_status'],'not_supported')

    def test_expected_paths_do_not_hide_other_fonts(self):
        package=self.root/'input';font_file(package/'a.ttf',text='A');other=package/'b.ttf'
        record={'package_dir':'fonts/package','local_paths':['fonts/package/a.ttf']}
        for damaged in [False,True]:
            if damaged:other.write_bytes(b'not a font')
            else:font_file(other,text='B')
            cache=self.root/str(damaged);resolver.register(record,package,cache)
            paths=resolver.local_files(record,cache);self.assertEqual(len(paths),2)
            self.assertEqual(resolver.font_metadata(paths,'A')['coverage_status'],'not_supported' if damaged else 'missing_glyphs')

    def test_fetch_conflicts_idempotence_and_late_target(self):
        data=font_file(self.root/'incoming.ttf',family='Incoming').read_bytes()
        url='https://'+resolver.TRUSTED_CDN_HOST+'/font.ttf'
        entry={'local_path':'fonts/font.ttf','cdn_url':url,'size_bytes':len(data),'md5':hashlib.md5(data).hexdigest()}
        class Response(io.BytesIO):
            def geturl(self):return url
        cache=self.root/'cache';target=font_file(cache/'fonts/font.ttf',family='Existing');original=target.read_bytes()
        with patch.object(resolver.urllib.request,'urlopen',return_value=Response(data)):
            with self.assertRaises((ValueError,FileExistsError)):resolver.fetch_entries([entry],cache)
        self.assertEqual(target.read_bytes(),original)
        target.write_bytes(data)
        with patch.object(resolver.urllib.request,'urlopen',return_value=Response(data)):
            resolver.fetch_entries([entry],cache)
        self.assertEqual(target.read_bytes(),data)
        target.unlink()
        def arrive(*args,**kwargs):target.write_bytes(original);return Response(data)
        with patch.object(resolver.urllib.request,'urlopen',side_effect=arrive):
            with self.assertRaises((ValueError,FileExistsError)):resolver.fetch_entries([entry],cache)
        self.assertEqual(target.read_bytes(),original)
        self.assertEqual(list(target.parent.glob('*.part')),[])

    def test_local_state_does_not_claim_target_ready(self):
        record={'id':'demo','name':'Demo','package_dir':'fonts','local_paths':['fonts/a.ttf'],'open_source':True,'license':'OFL'}
        p=font_file(self.root/'fonts/a.ttf',text='A')
        for broken in [False,True]:
            if broken:p.write_bytes(b'not a font')
            output=io.StringIO()
            with patch.object(resolver,'load_records',return_value=[record]),patch.object(resolver,'load_curated_pool',return_value={'fonts':[]}),patch.object(resolver,'load_manifest',return_value={'files':[]}),patch.object(sys,'argv',['resolve_font.py','demo','--cache-root',str(self.root),'--text','A','--require-ready']),redirect_stdout(output):
                code=resolver.main()
            result=json.loads(output.getvalue())
            self.assertEqual(result['package_status'],'invalid' if broken else 'local_present')
            self.assertEqual(result['target_environment_status'],'not_checked')
            self.assertEqual(code,5 if broken else 0)
        font_file(p,text='A');record['open_source']=False
        output=io.StringIO()
        with patch.object(resolver,'load_records',return_value=[record]),patch.object(resolver,'load_curated_pool',return_value={'fonts':[]}),patch.object(resolver,'load_manifest',return_value={'files':[]}),patch.object(sys,'argv',['resolve_font.py','demo','--cache-root',str(self.root),'--text','A','--require-ready']),redirect_stdout(output):
            code=resolver.main()
        self.assertEqual(json.loads(output.getvalue())['package_status'],'blocked_by_license')
        self.assertEqual(code,6)

class SVGRecheckTests(unittest.TestCase):
    setUp=svgtests.SVGStyleTests.setUp
    write=svgtests.SVGStyleTests.write
    def test_data_uri_validates_decoded_css_but_keeps_source(self):
        source=self.write('<style>@media(min-width:1px){rect{fill:url("#p")}}</style><defs><linearGradient id="p"/></defs><rect fill="url(&quot;#p&quot;)"/>')
        out,_=svg.inline_assets('asset:svg/test.svg',self.root)
        self.assertEqual(unquote(out.split(',',1)[1]),source)
        for body in [r'<rect style="fill:u\72l(https://example.com/x.svg#p)"/>',r'<style>@\69mport "https://example.com/a.css";</style>']:
            self.write(body)
            with self.assertRaises(ValueError):svg.inline_assets('asset:svg/test.svg',self.root)
