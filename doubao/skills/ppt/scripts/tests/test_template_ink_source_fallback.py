import pytest
from pathlib import Path
import importlib.util
import os
from zipfile import ZipFile, ZIP_DEFLATED
from lxml import etree as E
import hashlib

HERE=Path(__file__).parent
SOURCE=Path(os.environ.get('PPT_MIGRATION_TEST_SOURCE', '__external_migration_fixture__'))
BASE=HERE.parent/ 'template' / 'template_import_source.py'
pytestmark=pytest.mark.skipif(not SOURCE.is_file(), reason='Set PPT_MIGRATION_TEST_SOURCE to the public CV41 source')
P='http://schemas.openxmlformats.org/presentationml/2006/main'
MC='http://schemas.openxmlformats.org/markup-compatibility/2006'
R='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
PKG='http://schemas.openxmlformats.org/package/2006/relationships'


def api():
 p=Path(os.environ.get('IMPORT_SOURCE_MODULE',str(BASE)))
 s=importlib.util.spec_from_file_location('ink_import_under_test',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


def parts(path):
 with ZipFile(path) as z:return {n:z.read(n) for n in z.namelist()}


def test_real_cv41_selects_two_complete_original_ink_picture_fallbacks(tmp_path):
 before=parts(SOURCE);target=tmp_path/'source-v2.pptx'
 report=api().prepare_import_source(SOURCE,target)
 assert len(report.get('ink_changes',[]))==2, 'Known InkML branches are ignored; the two native arrows disappear'
 after=parts(target);src=E.fromstring(before['ppt/slides/slide35.xml']);dst=E.fromstring(after['ppt/slides/slide35.xml'])
 original=src.xpath('//*[local-name()="AlternateContent"]/*[local-name()="Fallback"]/*[local-name()="pic"]')
 assert len(original)==2
 assert not dst.xpath('//*[local-name()="AlternateContent"]')
 for pic in original:
  sid=pic.xpath('string(.//*[local-name()="cNvPr"]/@id)')
  matches=dst.xpath('//*[local-name()="spTree"]/*[local-name()="pic"][.//*[local-name()="cNvPr"]/@id=$sid]',sid=sid)
  assert len(matches)==1
  # Wrapper-only mc namespace declarations disappear when selecting its pic;
  # exclusive C14N compares the full actual picture XML, fields and geometry.
  assert E.tostring(matches[0],method='c14n',exclusive=True)==E.tostring(pic,method='c14n',exclusive=True)
  assert matches[0].xpath('string(.//*[local-name()="blip"]/@*[local-name()="embed"])') in ['rId7','rId9']


def test_cv41_protected_members_and_text_geometry_are_conserved(tmp_path):
 m=api();before=parts(SOURCE);target=tmp_path/'source-v2.pptx';raw=SOURCE.read_bytes()
 report=m.prepare_import_source(SOURCE,target);after=parts(target)
 assert set(before)==set(after)
 for n in before:
  if n.startswith(('ppt/media/','ppt/ink/','ppt/notesSlides/')) or n.endswith('.rels'):
   assert before[n]==after[n],n
 for n in before:
  if n.endswith('.xml') and n.startswith(('ppt/slides/slide','ppt/slideLayouts/slideLayout','ppt/slideMasters/slideMaster')):
   a=E.fromstring(before[n]);b=E.fromstring(after[n])
   assert a.xpath('//*[local-name()="t"]/text()')==b.xpath('//*[local-name()="t"]/text()')
 assert report['protected_content_unchanged'] and report['media_unchanged'] and report['relationships_unchanged']
 assert SOURCE.read_bytes()==raw


def test_unknown_alternate_content_is_preserved_when_known_ink_is_selected(tmp_path):
 original=parts(SOURCE);tree=E.fromstring(original['ppt/slides/slide35.xml']);sp=tree.xpath('//*[local-name()="spTree"]')[0]
 unknown=E.fromstring(f'<mc:AlternateContent xmlns:mc="{MC}" xmlns:p="{P}" xmlns:r="{R}" xmlns:p14="http://schemas.microsoft.com/office/powerpoint/2010/main"><mc:Choice Requires="p14"><p:contentPart r:id="rUnknown"/></mc:Choice><mc:Fallback><p:sp><p:txBody><p:t>Unknown original payload</p:t></p:txBody></p:sp></mc:Fallback></mc:AlternateContent>')
 sp.append(unknown);expected=E.tostring(unknown,method='c14n');original['ppt/slides/slide35.xml']=E.tostring(tree)
 rel=E.fromstring(original['ppt/slides/_rels/slide35.xml.rels']);E.SubElement(rel,'{'+PKG+'}Relationship',Id='rUnknown',Type=R+'/customXml',Target='../customXml/unknown.xml');original['ppt/slides/_rels/slide35.xml.rels']=E.tostring(rel);original['ppt/customXml/unknown.xml']=b'<original>Unknown data</original>'
 source=tmp_path/'unknown-source.pptx'
 with ZipFile(source,'w',ZIP_DEFLATED) as z:
  for n,b in original.items():z.writestr(n,b)
 target=tmp_path/'unknown-compatible.pptx';report=api().prepare_import_source(source,target)
 assert len(report.get('ink_changes',[]))==2
 rt=E.fromstring(parts(target)['ppt/slides/slide35.xml']);left=rt.xpath('//*[local-name()="AlternateContent"]')
 assert len(left)==1 and E.tostring(left[0],method='c14n')==expected


def test_known_ink_with_missing_existing_raster_is_reported_without_dropping_it(tmp_path):
 original=parts(SOURCE);original.pop('ppt/media/image48.png');source=tmp_path/'missing.pptx'
 with ZipFile(source,'w',ZIP_DEFLATED) as z:
  for n,b in original.items():z.writestr(n,b)
 target=tmp_path/'kept.pptx';report=api().prepare_import_source(source,target)
 assert report['ok'] is False
 assert any('fallback' in row['reason'] or 'media' in row['reason'] for row in report['unsupported_pictures'])
 rt=E.fromstring(parts(target)['ppt/slides/slide35.xml']);assert len(rt.xpath('//*[local-name()="AlternateContent"]'))==1


def test_picture_fallback_opt_out_preserves_the_real_original_bytes(tmp_path):
 out=tmp_path/'original-no-fallback.pptx';r=api().prepare_import_source(SOURCE,out,picture_fallbacks=False)
 assert out.read_bytes()==SOURCE.read_bytes()
 assert r.get('ink_changes',[])==[]
