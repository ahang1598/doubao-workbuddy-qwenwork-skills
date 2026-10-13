"""Offline font-binary and package integrity regressions."""
import importlib.util
from pathlib import Path
import shutil
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont, TTCollection

spec = importlib.util.spec_from_file_location('resource_resolver', Path(__file__).resolve().parents[1] / 'runtime/resolve_font.py')
resolver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(resolver)


def font_file(path, family='Test Family', text='A中'):
    builder = FontBuilder(1000, isTTF=True)
    glyphs = ['.notdef'] + ['u%04X' % ord(c) for c in text]
    builder.setupGlyphOrder(glyphs)
    builder.setupCharacterMap({ord(c): glyphs[i+1] for i,c in enumerate(text)})
    builder.setupGlyf({name: TTGlyphPen(None).glyph() for name in glyphs})
    builder.setupHorizontalMetrics({name: (600, 0) for name in glyphs})
    builder.setupHorizontalHeader(ascent=800, descent=-200)
    builder.setupNameTable({'familyName': family, 'styleName': 'Regular', 'uniqueFontIdentifier': family, 'fullName': family, 'psName': family.replace(' ', '')})
    builder.setupOS2(sTypoAscender=800, sTypoDescender=-200, usWinAscent=800, usWinDescent=200)
    builder.setupPost()
    builder.setupMaxp()
    path.parent.mkdir(parents=True, exist_ok=True)
    builder.save(path)
    return path


class FontResourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.record = {'package_dir': 'fonts/package', 'local_paths': []}

    def test_url_preserves_encoded_octets_and_query(self):
        base = 'https://' + resolver.TRUSTED_CDN_HOST
        original = base + '/字体/My%20Font%2FRegular.ttf?token=a%2Fb&x=1+2'
        expected = base + '/%E5%AD%97%E4%BD%93/My%20Font%2FRegular.ttf?token=a%2Fb&x=1+2'
        self.assertEqual(resolver.safe_url(original), expected)
        self.assertEqual(resolver.safe_url(expected), expected)
        self.assertEqual(resolver.safe_url(base+'/a%xx b.ttf'), base+'/a%25xx%20b.ttf')
        for url in ['http://'+resolver.TRUSTED_CDN_HOST+'/font.ttf', 'https://example.com/font.ttf']:
            with self.assertRaises(ValueError): resolver.safe_url(url)

    def test_real_ttf_woff_woff2_family_and_coverage(self):
        ttf = font_file(self.root/'base.ttf')
        for flavor in ['woff', 'woff2']:
            with TTFont(ttf) as font:
                font.flavor = flavor
                font.save(self.root/('base.'+flavor))
        for suffix in ['ttf', 'woff', 'woff2']:
            with self.subTest(suffix=suffix):
                result = resolver.font_metadata([self.root/('base.'+suffix)], 'A中')
                self.assertEqual(result['coverage_status'], 'complete', result)
                self.assertIn('Test Family', result['resolved_family_names'])
                missing = resolver.font_metadata([self.root/('base.'+suffix)], 'AB')
                self.assertEqual(missing['coverage_status'], 'missing_glyphs')
                self.assertEqual(missing['missing_characters'], ['B'])

    def test_webfont_mix_cannot_hide_missing_face(self):
        first = font_file(self.root/'a.ttf', text='A')
        second = font_file(self.root/'b.ttf', text='B')
        with TTFont(second) as font:
            font.flavor='woff'; font.save(self.root/'b.woff')
        result=resolver.font_metadata([first, self.root/'b.woff'], 'AB')
        self.assertEqual(result['coverage_status'], 'missing_glyphs', result)
        self.assertEqual(set(result['missing_characters']), {'A', 'B'})

    def test_collection_keeps_per_face_coverage(self):
        a=font_file(self.root/'a.ttf', text='A'); b=font_file(self.root/'b.ttf', text='B')
        collection=TTCollection(); collection.fonts=[TTFont(a), TTFont(b)]
        self.addCleanup(collection.close)
        collection.save(self.root/'mixed.ttc')
        result=resolver.font_metadata([self.root/'mixed.ttc'], 'AB')
        self.assertEqual(result['coverage_status'], 'missing_glyphs', result)

    def test_damaged_webfont_never_claims_ready(self):
        for magic in [b'wOFF', b'wOF2']:
            file=self.root/'broken.woff'; file.write_bytes(magic+b'invalid')
            result=resolver.font_metadata([file], 'A')
            self.assertEqual(result['coverage_status'], 'not_supported', result)
            self.assertIn(str(file), result['unsupported_font_files'])

    def test_missing_decoder_dependency_is_explicit(self):
        ttf=font_file(self.root/'base.ttf')
        with TTFont(ttf) as font:
            font.flavor='woff';font.save(self.root/'base.woff')
        script='import importlib.util,json;from pathlib import Path;s=importlib.util.spec_from_file_location("resolver",'+repr(str(Path(resolver.__file__).resolve()))+');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);print(json.dumps(m.font_metadata([Path('+repr(str(self.root/'base.woff'))+')],"A")))'
        run=subprocess.run([sys.executable,'-S','-c',script],capture_output=True,text=True)
        self.assertEqual(run.returncode,0,run.stderr)
        result=json.loads(run.stdout)
        self.assertEqual(result['coverage_status'],'not_supported')
        self.assertIn('fonttools',(run.stdout+run.stderr).lower())

    def test_webfont_head_content_types(self):
        class Response:
            status=200
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def geturl(self):return 'https://'+resolver.TRUSTED_CDN_HOST+'/font.woff'
        for content_type in ['font/woff','font/woff2','application/font-woff']:
            response=Response();response.headers={'Content-Length':'100','Content-Type':content_type}
            with patch.object(resolver.urllib.request,'urlopen',return_value=response):
                result=resolver.probe_entry({'cdn_url':response.geturl(),'size_bytes':100})
                self.assertTrue(result['verified'],result)

    def test_registration_keeps_nested_same_names(self):
        package=self.root/'input'
        first=font_file(package/'regular/font.ttf', 'Regular')
        second=font_file(package/'bold/font.ttf', 'Bold')
        cache=self.root/'cache'
        resolver.register(self.record, package, cache)
        target=cache/self.record['package_dir']
        self.assertEqual((target/'regular/font.ttf').read_bytes(), first.read_bytes())
        self.assertEqual((target/'bold/font.ttf').read_bytes(), second.read_bytes())
        self.assertEqual(len(resolver.local_files(self.record,cache)), 2)
        resolver.register(self.record,package,cache)
        self.assertEqual(len(resolver.local_files(self.record,cache)), 2)

    def test_conflict_fails_before_any_new_font_is_copied(self):
        package=self.root/'input'; font_file(package/'a.ttf'); font_file(package/'z.ttf','New')
        target=self.root/'cache/fonts/package'; original=font_file(target/'z.ttf','Existing').read_bytes()
        with self.assertRaises((ValueError, SystemExit, FileExistsError)):
            resolver.register(self.record,package,self.root/'cache')
        self.assertFalse((target/'a.ttf').exists())
        self.assertEqual((target/'z.ttf').read_bytes(),original)

    def test_escaping_package_symlink_is_rejected(self):
        package=self.root/'input';package.mkdir()
        outside=font_file(self.root/'outside.ttf')
        (package/'escape.ttf').symlink_to(outside)
        with self.assertRaises((ValueError, SystemExit)):
            resolver.register(self.record,package,self.root/'cache')

    def test_copy_failure_rolls_back_new_fonts(self):
        package=self.root/'input';font_file(package/'a.ttf');font_file(package/'b.ttf')
        copy=shutil.copyfileobj;calls=[]
        def fail_second(src,dst,*args,**kwargs):
            calls.append(str(src))
            if len(calls)==2:raise OSError('simulated disk failure')
            return copy(src,dst,*args,**kwargs)
        with patch.object(resolver.shutil,'copyfileobj',side_effect=fail_second),self.assertRaises((OSError,SystemExit)):
            resolver.register(self.record,package,self.root/'cache')
        self.assertEqual(list((self.root/'cache').rglob('*.ttf')),[])


if __name__=='__main__': unittest.main()
