from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from lxml import etree as E
import importlib.util
import hashlib
import json
import shutil
import pytest
import os

HERE=Path(__file__).parent
REVIEW=Path(os.environ.get('PPT_SOURCE_REVIEW_FIXTURES', '__external_source_review_fixtures__'))
pytestmark=pytest.mark.skipif(not REVIEW.is_dir(), reason='Set PPT_SOURCE_REVIEW_FIXTURES to the public review fixture directory')


def module(name):
    spec=importlib.util.spec_from_file_location('review_fix_'+name,HERE.parent/(name+'.py'))
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


def test_valid_future_alternate_keeps_its_original_svg_fallback_subtree(tmp_path):
    source=REVIEW/'alternate-fallbacks/valid-original.pptx';target=tmp_path/'copy.pptx'
    with ZipFile(source) as z:before=E.fromstring(z.read('ppt/slides/slide1.xml'))
    expected=before.xpath('//*[local-name()="AlternateContent"][*[local-name()="Choice"]/@Requires="future"]')[0]
    result=module('template_import_source').prepare_import_source(source,target)
    with ZipFile(target) as z:after=E.fromstring(z.read('ppt/slides/slide1.xml'))
    actual=after.xpath('//*[local-name()="AlternateContent"]')[0]
    assert E.tostring(actual,method='c14n',exclusive=True)==E.tostring(expected,method='c14n',exclusive=True)
    assert actual.xpath('.//*[local-name()="svgBlip"]')
    assert result['protected_content_unchanged']


def test_unknown_outer_alternate_protects_nested_known_ink_and_markers(tmp_path):
    source=REVIEW/'alternate-fallbacks/valid-original.pptx'
    with ZipFile(source) as z:parts={n:z.read(n) for n in z.namelist()}
    tree=E.fromstring(parts['ppt/slides/slide1.xml']);alts=tree.xpath('//*[local-name()="AlternateContent"]')
    known=next(a for a in alts if a.xpath('*[local-name()="Choice"]/@Requires')==['p14'])
    future=next(a for a in alts if a.xpath('*[local-name()="Choice"]/@Requires')==['future'])
    fallback=future.xpath('*[local-name()="Fallback"]')[0]
    fallback.append(E.fromstring(E.tostring(known)))
    marker=E.fromstring('<p:sp xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><p:txBody><a:p><a:pPr><a:buChar char="■"/></a:pPr><a:r><a:t>Unknown original text</a:t></a:r></a:p></p:txBody></p:sp>')
    fallback.append(marker);expected=E.tostring(future,method='c14n',exclusive=True)
    parts['ppt/slides/slide1.xml']=E.tostring(tree);custom=tmp_path/'nested.pptx'
    with ZipFile(custom,'w',ZIP_DEFLATED) as z:
        for n,b in parts.items():z.writestr(n,b)
    out=tmp_path/'nested-compatible.pptx';r=module('template_import_source').prepare_import_source(custom,out,bullet_char='•')
    assert len(r['ink_changes'])==1
    with ZipFile(out) as z:tree=E.fromstring(z.read('ppt/slides/slide1.xml'))
    actual=tree.xpath('//*[local-name()="AlternateContent"][*[local-name()="Choice"]/@Requires="future"]')[0]
    assert E.tostring(actual,method='c14n',exclusive=True)==expected


def prepared_fixture(tmp_path,monkeypatch):
    api=module('template_migration_source');source=REVIEW/'source-prepare/input.pptx'
    work=tmp_path/'source';(work/'raw-native').mkdir(parents=True)
    shutil.copy2(REVIEW/'source-prepare/work/raw-native/full.xml',work/'raw-native/full.xml')
    helper=api._helper
    class NoOtherNetwork:
        _run_with_retry=staticmethod(lambda *a,**kw: (_ for _ in ()).throw(AssertionError('No import/XML fetch allowed')))
    monkeypatch.setattr(api,'_helper',lambda name: NoOtherNetwork if name=='parse_template' else helper(name))
    with ZipFile(source) as z:payload=z.read('ppt/media/image1.png')
    calls=[];control={'payload':payload}
    def media_only(command, cwd, identity):
        assert '+media-download' in command
        calls.append(list(command));directory=cwd/command[command.index('--output-dir')+1];directory.mkdir(parents=True,exist_ok=True)
        path=directory/(command[command.index('--file-token')+1]+'.png');path.write_bytes(control['payload'])
        return {'ok':True,'data':{'path':str(path)}}
    monkeypatch.setattr(api,'_cli',media_only)
    first=api.prepare_source(source,work,'Existing source',source_deck='existing-source-deck')
    return api,source,work,first,calls,control


def test_resume_restores_only_missing_media_and_keeps_normal_recipe(tmp_path,monkeypatch):
    api,source,work,first,calls,_=prepared_fixture(tmp_path,monkeypatch)
    missing=Path(first['native_media'][0]['path']);other=Path(first['native_media'][1]['path'])
    original=missing.read_bytes();other_hash=hashlib.sha256(other.read_bytes()).hexdigest();missing.unlink()
    before_plan=Path(first['plan']).read_bytes()
    resumed=api.prepare_source(source,work,'Existing source',source_deck='existing-source-deck')
    assert missing.is_file() and missing.read_bytes()==original
    assert len(calls)==3 and calls[-1][calls[-1].index('--file-token')+1]==first['native_media'][0]['file_token']
    assert hashlib.sha256(other.read_bytes()).hexdigest()==other_hash
    assert resumed==first and Path(first['plan']).read_bytes()==before_plan


@pytest.mark.parametrize('same_size',[False,True])
def test_resume_rejects_changed_existing_media_without_overwrite(tmp_path,monkeypatch,same_size):
    api,source,work,first,calls,_=prepared_fixture(tmp_path,monkeypatch)
    media=Path(first['native_media'][0]['path']);raw=media.read_bytes()
    edited=(bytes([raw[0]^1])+raw[1:]) if same_size else b'User edited image'
    media.write_bytes(edited)
    with pytest.raises(ValueError,match='[Mm]edia.*(changed|differs|mismatch)'):
        api.prepare_source(source,work,'Existing source',source_deck='existing-source-deck')
    assert media.read_bytes()==edited and len(calls)==2


def test_missing_media_recovery_checks_expected_hash_before_restoring(tmp_path,monkeypatch):
    api,source,work,first,calls,control=prepared_fixture(tmp_path,monkeypatch)
    media=Path(first['native_media'][0]['path']);media.unlink();control['payload']=b'Different downloaded source response'
    with pytest.raises(ValueError,match='[Mm]edia.*(changed|differs|mismatch)'):
        api.prepare_source(source,work,'Existing source',source_deck='existing-source-deck')
    assert not media.exists() and len(calls)==3
    assert any(p.read_bytes()==control['payload'] for p in (work/'native-media').rglob('*.png'))


def test_authoring_root_binds_source_child_media_to_real_relative_paths_and_composes(tmp_path,monkeypatch):
    api,source,work,first,calls,_=prepared_fixture(tmp_path,monkeypatch)
    default_plan=Path(first['plan']).read_bytes()
    rooted=api.prepare_source(source,work,'Existing source',source_deck='existing-source-deck',authoring_work_dir=tmp_path)
    plan=json.loads(Path(rooted['plan']).read_bytes());assert plan['work_dir']==str(tmp_path)
    assert Path(first['plan']).read_bytes()==default_plan and len(calls)==2
    for page in plan['pages']:
        for path in page['bindings']['media'].values():
            assert path.startswith('@./source/native-media/') and (tmp_path/path[3:]).is_file()
        page['frame']='frame.xml';page['frame_ids']=[];page['target_region']=[40,100,800,300]
    (tmp_path/'frame.xml').write_text('<slide xmlns="https://www.larkoffice.com/sml/2.0"><style><fill><fillColor color="rgba(255,255,255,1)"/></fill></style><data/></slide>')
    spec=importlib.util.spec_from_file_location('review_rooted_plan',HERE.parent/ 'template' / 'template_authoring_plan.py');author=importlib.util.module_from_spec(spec);spec.loader.exec_module(author)
    result=author.prepare_plan(plan,tmp_path)
    assert result['ok'],result
    assert len(result['pages'])==2


def test_authoring_root_outside_source_ancestry_is_rejected_before_writes(tmp_path):
    api=module('template_migration_source');source=REVIEW/'source-prepare/input.pptx';work=tmp_path/'source'
    with pytest.raises(ValueError,match='authoring.*(inside|contain)|inside.*authoring'):
        api.prepare_source(source,work,'No mutation',source_deck='existing-source-deck',authoring_work_dir=tmp_path/'other')
    assert not work.exists()
