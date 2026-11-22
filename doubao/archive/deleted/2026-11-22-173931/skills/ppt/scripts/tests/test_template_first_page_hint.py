"""Parser receipts identify the retained first page before any authoring write."""
import importlib.util
import json
from pathlib import Path
import shlex
import sys

import pytest
from pptx import Presentation


def api():
    path = Path(__file__).parents[1] / 'template' / 'parse_template.py'
    spec = importlib.util.spec_from_file_location('first_page_hint_parser', path)
    module = importlib.util.module_from_spec(spec)
    original = list(sys.path)
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = original
    return module


@pytest.mark.parametrize('state', ['blank', 'template_remnant'])
def test_known_retained_first_page_returns_update_with_real_ids(state):
    hint = api()._first_page_write_hint({'template_imported': True, 'deck': {
        'xml_presentation_id': 'target-deck', 'first_page_slide_id': 'retained-first',
        'first_page_state': state}})
    command = shlex.split(hint['command'])
    assert command[:3] == ['lark-cli', 'slides', '+update-slide']
    assert command[command.index('--presentation') + 1] == 'target-deck'
    assert command[command.index('--slide-id') + 1] == 'retained-first'
    assert '--no-lint' in command and '--content' in command
    assert '+add-slide' not in command
    assert '第2页' in hint['message'] and '--slide-id' in hint['message']


def test_offline_hint_does_not_invent_an_update_target():
    hint = api()._first_page_write_hint({'template_imported': False, 'deck': None})
    assert hint['status'] == 'target_unavailable'
    assert 'command' not in hint and 'slide_id' not in hint


def test_next_steps_highlight_first_update_without_old_mandatory_lint(tmp_path):
    hint = api()._next_step_hint(tmp_path, {'template_imported': True, 'deck': {
        'xml_presentation_id': 'target-deck', 'first_page_slide_id': 'retained-first'}})
    assert hint.startswith('第一页') and '+update-slide' in hint
    assert 'retained-first' in hint and '--slide-id' in hint
    assert '--no-lint' in hint
    assert '完整预检' not in hint and '逐页 lint' not in hint


@pytest.mark.parametrize('offline', [False, True])
def test_main_returns_the_same_first_write_hint_in_stdout_and_index(tmp_path, monkeypatch, capsys, offline):
    module = api()
    source = tmp_path / 'source.pptx'
    prs = Presentation()
    for _ in range(2):
        prs.slides.add_slide(prs.slide_layouts[6])
    prs.slides[0].shapes.add_textbox(0, 0, 914400, 914400)
    prs.save(source)
    work = tmp_path / 'work'
    monkeypatch.setattr(module, '_detect_capabilities', lambda: ({
        'python_pptx': True, 'pypdfium2': True, 'pil': True, 'lxml': True,
        'soffice': True, 'lark_cli': True}, []))
    monkeypatch.setattr(module, '_render_overview', lambda *a, **kw: (True, 'fixture'))
    monkeypatch.setattr(module, '_import_pptx_to_lark', lambda *a, **kw: {
        'ok': True, 'xml_presentation_id': 'target-deck', 'url': 'https://example.test/slides/target-deck'})

    def split(*args, **kwargs):
        folder = work / 'source-slides'
        folder.mkdir(exist_ok=True)
        rows = []
        for i, sid in enumerate(['retained-first', 'source-second'], 1):
            path = folder / f'slide-{i:02d}.xml'
            path.write_text(f'<slide id="{sid}" xmlns="https://www.larkoffice.com/sml/2.0"><style/><data/></slide>')
            rows.append({'slide_num': i, 'slide_id': sid, 'local_xml_path': str(path)})
        return {'ok': True, 'slides': rows}

    monkeypatch.setattr(module, '_fetch_and_split_slides', split)
    monkeypatch.setattr(module, '_purge_deck_to_one_page', lambda *a, **kw: {
        'ok': True, 'first_page_slide_id': 'retained-first',
        'cleared_first_page': True, 'deleted_count': 1, 'failed_slide_ids': []})
    monkeypatch.setattr(sys, 'argv', ['parse_template.py', '--pptx', str(source), '--work-dir', str(work)] +
                        (['--offline-only'] if offline else []))
    assert module.main() == 0
    receipt = json.loads(capsys.readouterr().out)
    index = json.loads((work / 'manifest/template-index.json').read_text())
    assert receipt['first_page_write'] == index['first_page_write']
    assert receipt['empty_text_cleanup'] == index['empty_text_cleanup']
    assert receipt['empty_text_cleanup']['removed_count'] == 1
    assert 'empty_textboxes_removed' not in index['source_import_preparation']
    if offline:
        assert receipt['first_page_write']['status'] == 'target_unavailable'
    else:
        assert receipt['first_page_write']['slide_id'] == 'retained-first'
        assert '+update-slide' in receipt['next']
