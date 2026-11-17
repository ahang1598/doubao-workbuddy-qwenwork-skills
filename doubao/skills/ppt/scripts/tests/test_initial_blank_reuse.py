"""A retained first blank is reused only after one identity-verified read."""
import json
import sys
from pathlib import Path
import subprocess

import pytest

sys.path.insert(0, str(Path(__file__).parents[2]))
from scripts.svg_lib.atomize_svg_to_slide import _publish as generic
from test_template_publish import module, READY


COVER = ('<slide xmlns="https://www.larkoffice.com/sml/2.0"><data>'
         '<img src="cover-media" topLeftX="0" topLeftY="0" width="960" height="540"/>'
         '<shape type="text" topLeftX="60" topLeftY="100" width="600" height="80">'
         '<content fontSize="40"><p>History of calligraphy</p></content></shape>'
         '</data><note><content><p>Opening remarks.</p></content></note></slide>')
BLANK = '<slide id="RETAINED"><style/><data/><note><content/></note></slide>'


def response(slides=BLANK, deck='D'):
    return {'ok': True, 'data': {'xml_presentation_id': deck, 'scope': 'presentation',
            'xml_presentation': {'content': '<presentation id="' + deck + '">' + slides + '</presentation>'}}}


class Server:
    def __init__(self, read):
        self.read = read
        self.calls = []

    def generic(self, args, cwd, body=None):
        self.calls.append(args)
        assert args[args.index('--presentation') + 1] == 'D'
        if args[1] == '+xml-get':
            return self.read
        assert args[1] in ('+update-slide', '+add-slide')
        if body is None:
            body = Path(cwd, args[args.index('--content' if args[1] == '+update-slide' else '--slide') + 1][1:]).read_text()
        assert 'History of calligraphy' in body and 'Opening remarks.' in body
        sid = args[args.index('--slide-id') + 1] if args[1] == '+update-slide' else 'ADDED'
        return {'ok': True, 'data': {'slide_id': sid, 'xml_presentation_id': 'D'}}

    def template(self, args, **kw):
        result = READY if args[0] != 'lark-cli' else self.generic(args[1:], kw['cwd'], kw.get('input'))
        return subprocess.CompletedProcess(args, 0, json.dumps(result), '')


def publish(kind, tmp_path, monkeypatch, server, **options):
    if kind == 'template':
        xml = tmp_path / 'cover.xml'; xml.write_text(COVER)
        return module().publish(presentation='D', xml=xml, page=options.pop('page', 1),
                                mode='component_reuse', work_dir=tmp_path, runner=server.template, **options)
    monkeypatch.setattr(generic, '_run', server.generic)
    return generic.publish_slide(COVER, presentation='D', page=options.pop('page', 1), cwd=str(tmp_path),
                                 screenshot=False, **options)


@pytest.mark.parametrize('kind', ['template', 'generic'])
def test_first_page_updates_single_retained_blank_and_registers_real_id(tmp_path, monkeypatch, kind):
    server = Server(response())
    result = publish(kind, tmp_path, monkeypatch, server)
    assert result['ok'] and result['slide_id'] == 'RETAINED'
    assert [c[1] for c in server.calls] == ['+xml-get', '+update-slide']
    assert result['initial_blank']['status'] == 'reused'
    path = tmp_path / ('published-pages.json' if kind == 'template' else '.lark-slides/pages-D.json')
    state = json.loads(path.read_text())
    assert (state['pages'][0]['slide_id'] if kind == 'template' else state['p01']) == 'RETAINED'


@pytest.mark.parametrize('kind', ['template', 'generic'])
@pytest.mark.parametrize('read', [
    response(''),
    response(BLANK.replace('<data/>', '<data><shape type="rect"/></data>')),
    response(BLANK.replace('<content/>', '<content><p>Existing notes</p></content>')),
    response(BLANK.replace('<content/>', '<img src="speaker-media"/>')),
    response(BLANK.replace('<data/>', '<data/>Existing text')),
    response(BLANK + '<slide id="OTHER"><data/></slide>'),
    {'ok': False, 'error': {'code': 4001000, 'message': 'read unavailable'}},
    {'ok': True, 'data': {'xml_presentation': {'content': '<presentation>' + BLANK + '</presentation>'}}},
    {'ok': True, 'data': {'xml_presentation_id': '',
                         'xml_presentation': {'content': '<presentation>' + BLANK + '</presentation>'}}},
    response(BLANK.replace('id="RETAINED"', 'id=" "')),
])
def test_no_overwrite_or_new_block_when_blank_reuse_is_unproven(tmp_path, monkeypatch, kind, read):
    server = Server(read)
    result = publish(kind, tmp_path, monkeypatch, server)
    assert result['ok'] and result['slide_id'] == 'ADDED'
    assert [c[1] for c in server.calls] == ['+xml-get', '+add-slide']
    assert result['initial_blank']['status'] != 'reused'


@pytest.mark.parametrize('kind', ['template', 'generic'])
def test_explicit_slide_id_is_honored_without_initial_lookup(tmp_path, monkeypatch, kind):
    server = Server(response())
    result = publish(kind, tmp_path, monkeypatch, server, slide_id='EXPLICIT')
    assert result['ok'] and result['slide_id'] == 'EXPLICIT'
    assert [c[1] for c in server.calls] == ['+update-slide']


@pytest.mark.parametrize('kind', ['template', 'generic'])
def test_proven_wrong_deck_read_is_never_used_or_written(tmp_path, monkeypatch, kind):
    server = Server(response(deck='OTHER'))
    result = publish(kind, tmp_path, monkeypatch, server)
    assert not result['ok'] and [c[1] for c in server.calls] == ['+xml-get']


def test_generic_explicit_insertion_anchor_never_reuses_retained_blank(tmp_path, monkeypatch):
    server = Server(response())
    result = publish('generic', tmp_path, monkeypatch, server, before_slide_id='RETAINED')
    assert result['ok'] and result['slide_id'] == 'ADDED'
    assert [c[1] for c in server.calls] == ['+add-slide']


@pytest.mark.parametrize('kind', ['template', 'generic'])
def test_later_logical_page_does_not_probe_or_reuse_initial_blank(tmp_path, monkeypatch, kind):
    server = Server(response())
    result = publish(kind, tmp_path, monkeypatch, server, page=2)
    assert result['ok'] and [c[1] for c in server.calls] == ['+add-slide']


@pytest.mark.parametrize('kind', ['template', 'generic'])
def test_existing_page_registration_is_honored_without_probe(tmp_path, monkeypatch, kind):
    if kind == 'template':
        (tmp_path / 'published-pages.json').write_text(json.dumps({'version': 1, 'presentation': 'D', 'pages': [{
            'page': 1, 'mode': 'component_reuse', 'source': None, 'presentation': 'D',
            'slide_id': 'REGISTERED', 'xml_sha256': 'a' * 64}]}))
    else:
        folder = tmp_path / '.lark-slides'; folder.mkdir()
        (folder / 'pages-D.json').write_text(json.dumps({'p01': 'REGISTERED'}))
    server = Server(response())
    result = publish(kind, tmp_path, monkeypatch, server)
    assert result['ok'] and result['slide_id'] == 'REGISTERED'
    assert [c[1] for c in server.calls] == ['+update-slide']


def test_generic_legacy_task_files_do_not_prevent_reusing_proven_retained_blank(tmp_path, monkeypatch):
    sync = tmp_path / '.lark-slides/strategy/fresh/sync'; sync.mkdir(parents=True)
    (sync / 'status.json').write_text(json.dumps({'task_id': 'fresh-task', 'task_flow': 'strategy'}))
    (sync / 'deck.txt').write_text('D')
    server = Server(response())
    result = publish('generic', tmp_path, monkeypatch, server)
    assert result['ok'] and result['slide_id'] == 'RETAINED'
    assert [c[1] for c in server.calls] == ['+xml-get', '+update-slide']
    assert json.loads((sync / 'status.json').read_text()) == {'task_id': 'fresh-task', 'task_flow': 'strategy'}
