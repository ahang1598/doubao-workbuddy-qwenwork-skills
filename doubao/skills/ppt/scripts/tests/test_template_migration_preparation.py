import pytest
import importlib.util
import os
from pathlib import Path
import subprocess
import json
import hashlib
from zipfile import ZipFile
from lxml import etree as E

HERE = Path(__file__).parent
BASE = HERE.parent
SOURCE = Path(os.environ.get('PPT_MIGRATION_TEST_SOURCE', '__external_migration_fixture__'))
NOTES = Path(os.environ.get('PPT_MIGRATION_TEST_NOTES', '__external_migration_notes__'))
NATIVE = Path(os.environ.get('PPT_MIGRATION_TEST_NATIVE', '__external_migration_native__'))
NS = 'https://www.larkoffice.com/sml/2.0'


def api():
    p = Path(os.environ.get('MIGRATION_SOURCE_MODULE', str(BASE / 'template' / 'template_migration_source.py')))
    assert p.is_file(), 'CV41 has no one-command complete native source-tree preparation API'
    spec = importlib.util.spec_from_file_location('test_migration_source_api', p)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cli_discovers_native_source_preparation():
    cli = Path(os.environ.get('MIGRATION_CLI', str(BASE / 'template' / 'template_migration.py')))
    p = subprocess.run(['python3', str(cli), 'prepare-source', '--help'], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    assert '--source-pptx' in p.stdout and '--work-dir' in p.stdout


@pytest.mark.skipif(not (SOURCE.is_file() and NOTES.is_file() and NATIVE.is_file()), reason='Set PPT_MIGRATION_TEST_SOURCE, NOTES and NATIVE to public fixtures')
def test_real_cv41_source_inventory_and_notes(tmp_path):
    m = api()
    snapshot = m.snapshot_original(SOURCE, tmp_path, notes_json=NOTES)
    assert snapshot['page_count'] == 41
    assert (tmp_path / 'original.pptx').read_bytes() == SOURCE.read_bytes()
    assert snapshot['source_sha256'] == '5f71821c59e199dd35428b101c32fe4ec879a71b786e162856a3578703ee5142'
    assert [p['page'] for p in snapshot['pages']] == list(range(1,42))
    assert sum(p['notes']['is_empty'] for p in snapshot['pages']) == 24
    assert any('196x16x16' in ''.join(p['paragraphs']) for p in snapshot['pages'] if p['page'] == 27)
    assert any('Using Mobile-Net and local inference' in ''.join(p['paragraphs']) for p in snapshot['pages'] if p['page'] == 40)
    with ZipFile(SOURCE) as z:
        media = [n for n in z.namelist() if n.startswith('ppt/media/') and not n.endswith('/')]
        assert len(snapshot['media']) == len(media)
        for row in snapshot['media']:
            assert (tmp_path / row['path']).read_bytes() == z.read(row['part'])
            assert row['sha256'] == hashlib.sha256(z.read(row['part'])).hexdigest()
        pictures = sum(len(E.fromstring(z.read(n)).xpath('//*[local-name()="pic"]'))
                       for n in z.namelist() if n.startswith(('ppt/slides/slide','ppt/slideLayouts/slideLayout','ppt/slideMasters/slideMaster')) and n.endswith('.xml'))
        assert len(snapshot['picture_metadata']) == pictures
    original = SOURCE.read_bytes()
    assert snapshot['import_preparation']['media_unchanged']
    assert snapshot['import_preparation']['protected_content_unchanged']
    assert SOURCE.read_bytes() == original


@pytest.mark.skipif(not (SOURCE.is_file() and NOTES.is_file() and NATIVE.is_file()), reason='Set PPT_MIGRATION_TEST_SOURCE, NOTES and NATIVE to public fixtures')
def test_raw_notes_and_repeat_snapshot_keep_exact_empty_paragraphs(tmp_path):
    m = api()
    source = m.snapshot_original(SOURCE, tmp_path)
    supplied = json.loads(NOTES.read_text())
    assert [p['notes']['paragraphs'] for p in source['pages']] == [p['paragraphs'] for p in supplied['pages']]
    assert source['pages'][16]['notes']['paragraphs'][1] == ''
    assert m.snapshot_original(SOURCE, tmp_path) == source


def test_shared_styles_and_real_members_survive_split(tmp_path):
    m = api()
    native = tmp_path / 'native.xml'
    native.write_text(f'''<presentation xmlns="{NS}" width="960" height="540"><theme><background><fillColor color="rgba(40,40,40,1)"/></background><textStyles><body fontFamily="Calibri" fontSize="20" fontColor="rgba(90,90,90,1)"/></textStyles></theme><slide id="s1"><data><shape id="a"><content textType="body"><p>Let’s &amp; a→b</p></content></shape><shape id="b"><content textType="body" fontSize="13"><p>Explicit</p></content></shape><img id="photo" src="native-token" width="100" height="100"/><line id="edge" startShapeId="a" endShapeId="photo"/></data><note><content><p>Click to add text</p></content></note></slide></presentation>''')
    notes = [{'page': 1, 'paragraphs': [], 'text': '', 'is_empty': True}]
    rows = m.split_native_source(native, tmp_path / 'complete', notes)
    assert len(rows) == 1
    root = E.parse(rows[0]['path']).getroot()
    contents=root.xpath('//*[local-name()="data"]//*[local-name()="content"]')
    assert contents[0].get('fontFamily') == 'Calibri'
    assert contents[0].get('fontSize') == '20'
    assert contents[0].get('color') == 'rgba(90,90,90,1)'
    assert contents[1].get('fontSize') == '13'
    assert root.xpath('//*[local-name()="style"]//*[local-name()="fillColor"]')[0].get('color') == 'rgba(40,40,40,1)'
    assert ''.join(root.xpath('//*[local-name()="data"]')[0].itertext()).strip() == 'Let’s & a→bExplicit'
    assert root.xpath('//*[local-name()="img"]')[0].get('src') == 'native-token'
    assert root.xpath('//*[local-name()="line"]')[0].get('endShapeId') == 'photo'
    assert not root.xpath('//*[local-name()="note"]//*[local-name()="p"]')
    assert 'Click to add text' in native.read_text()
    inventory = json.loads(Path(rows[0]['inventory']).read_text())
    assert set(inventory['member_ids']) == {'a','b','photo','edge'}


def test_recipe_contains_complete_source_members(tmp_path):
    m = api()
    slide = tmp_path / 'source.xml'
    slide.write_text(f'<slide xmlns="{NS}" id="s"><style/><data><shape id="title"><content><p>Original</p></content></shape><img id="image" src="real" width="20" height="20"/></data><note><content/></note></slide>')
    rows = [{'page':1,'path':str(slide),'member_ids':['title','image']}]
    plan = m.migration_recipes(rows, tmp_path)
    row = plan['pages'][0]
    assert row['operation'] == 'migration' and row['link'] == 'L8'
    assert row['source'] == str(slide) and row['content_ids'] == ['title','image']
    assert row['frame'] is None and row['target_region'] is None and row['role_styles'] == {}
    assert 'notes' not in row


def test_recipe_mechanically_binds_downloaded_source_media_for_target_upload(tmp_path):
    m=api()
    rows=[{'page':1,'path':'original-slides/slide-01.xml','member_ids':['pic'], 'media_tokens':['original-token']}]
    recipe=m.migration_recipes(rows,tmp_path,{'original-token':'@./native-media/original.png'})
    assert recipe['pages'][0]['bindings']['media']=={'original-token':'@./native-media/original.png'}


def test_recipe_preserves_all_source_top_level_members_including_unlabelled_geometry(tmp_path):
    m=api()
    rows=[{'page':1,'path':'source.xml','member_ids':['text'], 'all_member_ids':['axis','text','node']}]
    assert m.migration_recipes(rows,tmp_path)['pages'][0]['content_ids']==['axis','text','node']


@pytest.mark.skipif(not (SOURCE.is_file() and NOTES.is_file() and NATIVE.is_file()), reason='Set PPT_MIGRATION_TEST_SOURCE, NOTES and NATIVE to public fixtures')
def test_unverified_sidecar_rejected_before_copy(tmp_path):
    m = api()
    bad = json.loads(NOTES.read_text());bad['source_sha256']='wrong'
    sidecar=tmp_path/'bad.json';sidecar.write_text(json.dumps(bad))
    import pytest
    with pytest.raises(ValueError, match='notes.*source|source.*notes'):
        m.snapshot_original(SOURCE,tmp_path/'work',notes_json=sidecar)
    assert not (tmp_path/'work'/'original.pptx').exists()


@pytest.mark.skipif(not (SOURCE.is_file() and NOTES.is_file() and NATIVE.is_file()), reason='Set PPT_MIGRATION_TEST_SOURCE, NOTES and NATIVE to public fixtures')
def test_real_import_fixture_all_41_pages_when_available(tmp_path):
    m=api()
    native=NATIVE
    assert native.is_file(), 'Live CV41 source import fixture required for GREEN'
    snapshot=m.snapshot_original(SOURCE,tmp_path,notes_json=NOTES)
    rows=m.split_native_source(native,tmp_path/'source-slides',[p['notes'] for p in snapshot['pages']])
    assert len(rows)==41
    assert sum(r['notes_empty'] for r in rows)==24
    for row in rows:
        inv=json.loads(Path(row['inventory']).read_text())
        assert inv['source_sha256']==hashlib.sha256(Path(row['path']).read_bytes()).hexdigest()
        root=E.parse(row['path']).getroot()
        assert len(root.xpath('//*[local-name()="data"]/*'))==len(row['all_member_ids'])
        assert all(n.get('id') in row['all_member_ids'] for n in root.xpath('//*[local-name()="data"]/*'))
    assert any('196x16x16' in ''.join(E.parse(rows[26]['path']).getroot().itertext()) for _ in [0])


@pytest.mark.skipif(not (SOURCE.is_file() and NOTES.is_file() and NATIVE.is_file()), reason='Set PPT_MIGRATION_TEST_SOURCE, NOTES and NATIVE to public fixtures')
def test_complete_saved_native_xml_avoids_redundant_per_page_network_reads(tmp_path, monkeypatch):
    m=api()
    import shutil
    raw=tmp_path/'raw-native';raw.mkdir();shutil.copy2(NATIVE,raw/'full.xml')
    helper=m._helper
    class ParserBoundary:
        _run_with_retry = staticmethod(lambda *a,**kw: (_ for _ in ()).throw(AssertionError('No import or XML fetch needed')))
        _fetch_and_split_slides = staticmethod(lambda *a,**kw: (_ for _ in ()).throw(AssertionError('Complete full XML must not trigger redundant 41-page refetch')))
    monkeypatch.setattr(m,'_helper',lambda name: ParserBoundary if name=='parse_template' else helper(name))
    original_runner = ParserBoundary._run_with_retry
    def download_only(command, work, identity):
        assert '+media-download' in command
        media=work/'native-media';media.mkdir(exist_ok=True)
        path=media/(command[command.index('--file-token')+1]+'.png');path.write_bytes(b'test-only-media-boundary')
        return {'ok':True,'data':{'path':str(path)}}
    monkeypatch.setattr(m,'_cli',download_only)
    r=m.prepare_source(SOURCE,tmp_path,'CV41',notes_json=NOTES,source_deck='confirmed-test-boundary')
    assert r['ok'] and r['page_count']==41
    assert len(list((tmp_path/'raw-native').glob('slide-*.xml')))==41
    assert ParserBoundary._run_with_retry is original_runner
