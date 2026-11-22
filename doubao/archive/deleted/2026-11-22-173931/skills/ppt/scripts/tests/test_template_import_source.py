"""The preparation changes format preference and optional decorative markers only."""
from pathlib import Path
import importlib.util
import io
import json
import os
import subprocess
import sys
import zipfile

from lxml import etree as ET
from PIL import Image
import pytest

SCRIPT = Path(__file__).parents[1] / 'template' / 'template_import_source.py'
P = 'http://schemas.openxmlformats.org/presentationml/2006/main'
A = 'http://schemas.openxmlformats.org/drawingml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
SVG = 'http://schemas.microsoft.com/office/drawing/2016/SVG/main'
PKG = 'http://schemas.openxmlformats.org/package/2006/relationships'
NS = {'p': P, 'a': A, 'r': R, 'asvg': SVG}


def api():
    assert SCRIPT.exists(), 'compatible original-PPTX preparation operation is missing'
    spec = importlib.util.spec_from_file_location('template_import_source_under_test', SCRIPT)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def picture(fallback='rPng'):
    embed = f'r:embed="{fallback}"' if fallback else ''
    return f'''<p:pic><p:nvPicPr><p:cNvPr id="7" name="Speaker1Image" descr="Original image"/><p:cNvPicPr/><p:nvPr><p:ph type="pic" idx="4"/></p:nvPr></p:nvPicPr><p:blipFill><a:blip {embed}><a:extLst><a:ext uri="svg-priority"><asvg:svgBlip r:embed="rSvg"/></a:ext><a:ext uri="keep-other"><a:alphaModFix amt="50000"/></a:ext></a:extLst></a:blip><a:srcRect l="1000" r="2000" t="3000" b="4000"/><a:stretch><a:fillRect/></a:stretch></p:blipFill><p:spPr><a:xfrm rot="5400000" flipH="1"><a:off x="100" y="200"/><a:ext cx="300" cy="400"/></a:xfrm><a:prstGeom prst="rect"/></p:spPr></p:pic>'''


def fixture(path, *, fallback='rPng', image_format='PNG', fallback_target='../media/fallback.png', target_mode='', include_fallback=True):
    raster = io.BytesIO(); Image.new('RGB', (12, 8), (20, 30, 40)).save(raster, format=image_format)
    svg_asset = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 12 8"><path d="M0 0H12V8H0Z"/></svg>'
    marker = '<a:buFont typeface="Wingdings" charset="2" panose="05000000000000000000" pitchFamily="2"/><a:buChar char="&#158;"/>'
    source = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?><p:sld xmlns:p="{P}" xmlns:a="{A}" xmlns:r="{R}" xmlns:asvg="{SVG}"><p:cSld><p:spTree>{picture(fallback)}<p:sp><p:nvSpPr><p:cNvPr id="8" name="Original code"/></p:nvSpPr><p:txBody><a:bodyPr/><a:lstStyle/><a:p><a:pPr lvl="2">{marker}</a:pPr><a:r><a:rPr><a:latin typeface="Wingdings"/></a:rPr><a:t xml:space="preserve">  code • ≥ × &#158;\n  next&#9;line</a:t></a:r><a:fld id="field-original" type="datetime"><a:t>2016-11-07</a:t></a:fld></a:p><a:p><a:pPr lvl="1"><a:buAutoNum type="alphaUcPeriod" startAt="5"/></a:pPr><a:r><a:t>Numbered item</a:t></a:r></a:p></p:txBody></p:sp><p:graphicFrame><asvg:svgBlip r:embed="rSvg"/><a:tbl><a:tr><a:tc><a:txBody><a:p><a:r><a:t>167 of 173</a:t></a:r></a:p></a:txBody></a:tc></a:tr></a:tbl></p:graphicFrame></p:spTree></p:cSld></p:sld>'''
    layout = f'<p:sldLayout xmlns:p="{P}" xmlns:a="{A}" xmlns:r="{R}" xmlns:asvg="{SVG}"><p:cSld><p:spTree>{picture(fallback)}</p:spTree></p:cSld></p:sldLayout>'
    master = f'<p:sldMaster xmlns:p="{P}" xmlns:a="{A}"><p:txStyles><p:bodyStyle><a:lvl3pPr>{marker}</a:lvl3pPr></p:bodyStyle></p:txStyles></p:sldMaster>'
    raster_rel = f'<Relationship Id="rPng" Type="{R}/image" Target="{fallback_target}" {target_mode}/>' if include_fallback else ''
    rels = f'<Relationships xmlns="{PKG}">{raster_rel}<Relationship Id="rSvg" Type="{R}/image" Target="../media/asset.svg"/></Relationships>'
    parts = {
        '[Content_Types].xml': b'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="xml" ContentType="application/xml"/><Default Extension="png" ContentType="image/png"/><Default Extension="svg" ContentType="image/svg+xml"/></Types>',
        'ppt/slides/slide1.xml': source.encode(),
        'ppt/slides/_rels/slide1.xml.rels': rels.encode(),
        'ppt/slideLayouts/slideLayout1.xml': layout.encode(),
        'ppt/slideLayouts/_rels/slideLayout1.xml.rels': rels.encode(),
        'ppt/slideMasters/slideMaster1.xml': master.encode(),
        'ppt/media/fallback.png': raster.getvalue(),
        'ppt/media/asset.svg': svg_asset,
        'ppt/charts/chart1.xml': b'<chart><values>72,8,12,108</values></chart>',
        'ppt/notesSlides/notesSlide1.xml': f'<p:notes xmlns:p="{P}" xmlns:a="{A}"><p:sp><p:txBody><a:p><a:r><a:t xml:space="preserve">Original notes\nSecond paragraph</a:t></a:r></a:p></p:txBody></p:sp></p:notes>'.encode(),
    }
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        z.comment = b'original-package-comment'
        for name, raw in parts.items(): z.writestr(name, raw)
    return parts


def package(path):
    with zipfile.ZipFile(path) as z:
        return {n: z.read(n) for n in z.namelist()}


def test_svg_priority_is_disabled_only_for_actual_pictures_with_original_raster_fallback(tmp_path):
    src = tmp_path/'original.pptx'; expected = fixture(src); raw = src.read_bytes()
    out = tmp_path/'compatible.pptx'; report = api().prepare_import_source(src, out)
    assert report['ok'] and len(report['picture_changes']) == 2
    assert src.read_bytes() == raw
    actual = package(out)
    assert actual.keys() == expected.keys()
    for name in expected:
        if name not in ['ppt/slides/slide1.xml', 'ppt/slideLayouts/slideLayout1.xml']:
            assert actual[name] == expected[name], name
    for part in ['ppt/slides/slide1.xml', 'ppt/slideLayouts/slideLayout1.xml']:
        old = ET.fromstring(expected[part]); new = ET.fromstring(actual[part])
        pic = new.find('.//p:pic', NS)
        assert pic.find('.//asvg:svgBlip', NS) is None
        assert pic.find('./p:blipFill/a:blip', NS).get('{'+R+'}embed') == 'rPng'
        for xpath in ['./p:nvPicPr', './p:spPr', './p:blipFill/a:srcRect']:
            assert ET.tostring(pic.find(xpath, NS)) == ET.tostring(old.find('.//p:pic', NS).find(xpath, NS))
        assert pic.find('.//a:ext[@uri="keep-other"]/a:alphaModFix', NS).get('amt') == '50000'
    assert ET.fromstring(actual['ppt/slides/slide1.xml']).find('.//p:graphicFrame/asvg:svgBlip', NS) is not None
    assert report['media_unchanged'] and report['relationships_unchanged'] and report['protected_content_unchanged']
    assert report['picture_changes'][0]['owner_shape_id'] == '7'
    assert report['picture_changes'][0]['fallback']['format'] == 'PNG'
    assert report['picture_changes'][0]['fallback']['width'] == 12
    with zipfile.ZipFile(out) as z: assert z.comment == b'original-package-comment'


def test_default_does_not_change_markers_inline_symbols_or_field_and_table_content(tmp_path):
    src=tmp_path/'original.pptx'; old=fixture(src); out=tmp_path/'out.pptx'
    report=api().prepare_import_source(src,out); new=package(out)
    assert report['bullet_changes'] == []
    for name in ['ppt/slides/slide1.xml', 'ppt/slideLayouts/slideLayout1.xml', 'ppt/slideMasters/slideMaster1.xml']:
        before=ET.fromstring(old[name]); after=ET.fromstring(new[name])
        if name == 'ppt/slides/slide1.xml':
            assert [e.text for e in before.findall('.//a:t',NS)] == [e.text for e in after.findall('.//a:t',NS)]
        assert [e.attrib for e in before.findall('.//a:buChar',NS)] == [e.attrib for e in after.findall('.//a:buChar',NS)]
        assert [e.attrib for e in before.findall('.//a:buFont',NS)] == [e.attrib for e in after.findall('.//a:buFont',NS)]


def test_explicit_unicode_marker_changes_only_buchar_and_marker_font(tmp_path):
    src=tmp_path/'original.pptx'; old=fixture(src); out=tmp_path/'out.pptx'
    report=api().prepare_import_source(src,out,bullet_char='•'); new=package(out)
    assert len(report['bullet_changes']) == 2
    before=ET.fromstring(old['ppt/slides/slide1.xml']); after=ET.fromstring(new['ppt/slides/slide1.xml'])
    assert after.find('.//a:buChar',NS).get('char') == '•'
    assert after.find('.//a:buFont',NS).get('typeface') == 'Arial'
    assert [e.text for e in before.findall('.//a:t',NS)] == [e.text for e in after.findall('.//a:t',NS)]
    assert after.find('.//a:rPr/a:latin',NS).get('typeface') == 'Wingdings'
    assert [e.attrib for e in before.findall('.//a:buAutoNum',NS)] == [e.attrib for e in after.findall('.//a:buAutoNum',NS)]
    assert [e.get('lvl') for e in before.findall('.//a:pPr',NS)] == [e.get('lvl') for e in after.findall('.//a:pPr',NS)]
    assert ET.tostring(before.find('.//a:fld',NS)) == ET.tostring(after.find('.//a:fld',NS))
    assert report['bullet_changes'][0]['before_char'] == '\x9e'
    assert report['bullet_changes'][0]['before_font']['typeface'] == 'Wingdings'
    assert report['bullet_changes'][0]['after_char'] == '•'


@pytest.mark.parametrize('options', [{'fallback':None}, {'include_fallback':False}, {'fallback_target':'../media/missing.png'}, {'fallback_target':'https://example.test/a.png','target_mode':'TargetMode="External"'}, {'image_format':'GIF'}])
def test_missing_external_or_unsupported_fallback_is_reported_without_deleting_picture(options,tmp_path):
    src=tmp_path/'original.pptx'; old=fixture(src,**options); out=tmp_path/'out.pptx'
    report=api().prepare_import_source(src,out)
    assert not report['ok'] and len(report['unsupported_pictures']) == 2
    assert report['picture_changes'] == []
    assert package(out) == old
    assert src.read_bytes() == out.read_bytes()


def test_jpeg_fallback_is_selected_without_recoding_original_media(tmp_path):
    src=tmp_path/'original.pptx';old=fixture(src,image_format='JPEG');out=tmp_path/'out.pptx'
    report=api().prepare_import_source(src,out)
    assert report['ok'] and report['picture_changes'][0]['fallback']['format'] == 'JPEG'
    assert package(out)['ppt/media/fallback.png'] == old['ppt/media/fallback.png']


def test_disabled_fallback_selection_returns_an_identical_copy(tmp_path):
    src=tmp_path/'original.pptx';fixture(src);out=tmp_path/'out.pptx'
    report=api().prepare_import_source(src,out,picture_fallbacks=False)
    assert report['ok'] and report['picture_changes'] == []
    assert out.read_bytes() == src.read_bytes()


def test_original_alias_existing_different_output_and_invalid_bullet_are_not_overwritten(tmp_path):
    src=tmp_path/'original.pptx';fixture(src);raw=src.read_bytes();out=tmp_path/'existing.pptx';out.write_bytes(b'existing content')
    with pytest.raises(ValueError):api().prepare_import_source(src,src)
    with pytest.raises(ValueError):api().prepare_import_source(src,out)
    assert out.read_bytes() == b'existing content' and src.read_bytes() == raw
    alias=tmp_path/'alias.pptx';os.link(src,alias)
    with pytest.raises(ValueError):api().prepare_import_source(src,alias)
    with pytest.raises(ValueError):api().prepare_import_source(src,tmp_path/'bad.pptx',bullet_char='word')
    assert not (tmp_path/'bad.pptx').exists()


def test_identical_prepared_output_is_reused_without_rewriting(tmp_path):
    src=tmp_path/'original.pptx';fixture(src);out=tmp_path/'out.pptx'
    api().prepare_import_source(src,out);stamp=out.stat().st_mtime_ns
    report=api().prepare_import_source(src,out)
    assert report['reused_identical_output'] and out.stat().st_mtime_ns == stamp


def test_cli_creates_distinct_source_copy_and_json_operation_receipt(tmp_path):
    src=tmp_path/'original.pptx';fixture(src);out=tmp_path/'prepared.pptx'
    assert SCRIPT.exists(), 'compatible preparation CLI is missing'
    proc=subprocess.run([sys.executable,str(SCRIPT),'--source-pptx',str(src),'--output-pptx',str(out),'--bullet-char','•'],capture_output=True,text=True)
    assert proc.returncode == 0, proc.stderr
    report=json.loads(proc.stdout)
    assert report['ok'] and len(report['picture_changes']) == 2 and len(report['bullet_changes']) == 2


def test_frozen_module_import_and_operation_need_only_standard_library(tmp_path):
    src=tmp_path/'original.pptx';fixture(src);out=tmp_path/'prepared.pptx';bundle=tmp_path/'frozen-helper.zip'
    with zipfile.ZipFile(bundle,'w') as z:z.writestr('template_import_source.py',SCRIPT.read_bytes())
    code='''import builtins,sys,json
original_import=builtins.__import__
def stdlib_only(name,*args,**kwargs):
    if name.split('.')[0] in {'defusedxml','lxml','PIL'}:
        raise ImportError('third-party package intentionally unavailable: '+name)
    return original_import(name,*args,**kwargs)
builtins.__import__=stdlib_only
sys.path.insert(0,sys.argv[1])
import template_import_source as module
assert module.__file__.startswith(sys.argv[1])
result=module.prepare_import_source(sys.argv[2],sys.argv[3],bullet_char='•')
print(json.dumps({'ok':result['ok'],'pictures':len(result['picture_changes']),'markers':len(result['bullet_changes'])}))
'''
    proc=subprocess.run([sys.executable,'-I','-c',code,str(bundle),str(src),str(out)],capture_output=True,text=True)
    assert proc.returncode==0,proc.stderr
    assert json.loads(proc.stdout)=={'ok':True,'pictures':2,'markers':2}


@pytest.mark.parametrize('encoding',['utf-8','utf-16'])
def test_doctype_and_entities_are_rejected_in_any_xml_encoding_without_output(encoding,tmp_path):
    src=tmp_path/'original.pptx';parts=fixture(src)
    text=f'<?xml version="1.0" encoding="{encoding}"?><!DOCTYPE p:sld [<!ENTITY expansion "unsafe">]><p:sld xmlns:p="{P}"/>'
    parts['ppt/slides/slide1.xml']=text.encode(encoding)
    with zipfile.ZipFile(src,'w') as z:
        for name,raw in parts.items():z.writestr(name,raw)
    raw=src.read_bytes();out=tmp_path/'out.pptx'
    with pytest.raises(ValueError):api().prepare_import_source(src,out)
    assert not out.exists() and src.read_bytes()==raw
