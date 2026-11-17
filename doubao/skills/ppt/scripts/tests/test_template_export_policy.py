"""Template metadata warnings permit review export without claiming completion."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
import multiagent_sync as ms
from test_template_registered_export import setup


def remote(monkeypatch, *, deck='D', ids=('a', 'b'), export_ok=True):
    calls = []
    def cli(args, cwd):
        calls.append(args)
        if args[:2] == ['slides', '+xml-get']:
            return {'ok': True, 'data': {'xml_presentation_id': deck,
                    'xml_presentation': {'content': '<presentation>' + ''.join(
                        '<slide id="' + sid + '"/>' for sid in ids) + '</presentation>'}}}
        assert args[:2] == ['drive', '+export']
        assert args[args.index('--token') + 1] == 'D'
        return {'ok': True, 'data': {'saved_path': './Review.pptx'}} if export_ok else {
                'ok': False, 'error': {'code': 'export_unavailable'}}
    monkeypatch.setattr(ms, '_cli', cli)
    return calls


@pytest.mark.parametrize('warning,code', [
    ('pending', 'template_publish_pending'),
    ('plan', 'template_plan_incomplete'),
    ('missing', 'unregistered_pages'),
    ('mismatch', 'template_registry_mismatch'),
])
def test_default_exports_review_despite_template_metadata_warning(tmp_path, monkeypatch, warning, code):
    work, _ = setup(tmp_path, monkeypatch)
    if warning == 'pending':
        (work / 'published-pages.pending.json').write_text(json.dumps({'presentation': 'D'}))
    elif warning == 'plan':
        (work / 'page-plan.md').write_text('| P1 | content |\n| P2 | content |\n| P3 | content |\n')
    elif warning == 'missing':
        (work / 'published-pages.json').unlink()
    before = {p: p.read_bytes() for p in work.glob('published-pages*.json')}
    calls = remote(monkeypatch, ids=('a', 'b', 'unregistered') if warning == 'mismatch' else ('a', 'b'))
    result = ms.export('D', tmp_path, who='lead')
    assert result['ok'] and result['draft'] and result['needs_final_review']
    assert result['registry_advisory']['code'] == code
    assert result['pptx'] == str(tmp_path / 'Review.pptx')
    assert any(c[:2] == ['drive', '+export'] for c in calls)
    assert all(c[1] not in ('+add-slide', '+update-slide') for c in calls)
    assert all(p.read_bytes() == content for p, content in before.items())
    assert 'final_reply' not in result
    assert not (tmp_path / '.lark-slides/decks/D/FINAL_REPLY.md').exists()


def test_strict_retains_legacy_template_registry_refusal(tmp_path, monkeypatch):
    work, _ = setup(tmp_path, monkeypatch)
    (work / 'published-pages.pending.json').write_text(json.dumps({'presentation': 'D'}))
    calls = remote(monkeypatch)
    result = ms.export('D', tmp_path, strict=True)
    assert not result['ok'] and result['code'] == 'template_publish_pending' and not calls


@pytest.mark.parametrize('pending', [False, True])
def test_actual_wrong_deck_remains_hard_even_with_pending_metadata(tmp_path, monkeypatch, pending):
    work, _ = setup(tmp_path, monkeypatch)
    if pending:
        (work / 'published-pages.pending.json').write_text(json.dumps({'presentation': 'D'}))
    calls = remote(monkeypatch, deck='OTHER')
    result = ms.export('D', tmp_path)
    assert not result['ok'] and result['code'] == 'template_readback_wrong_deck'
    assert all(c[:2] != ['drive', '+export'] for c in calls)


def test_metadata_advisory_never_turns_export_transport_failure_into_success(tmp_path, monkeypatch):
    work, _ = setup(tmp_path, monkeypatch)
    (work / 'published-pages.json').unlink()
    remote(monkeypatch, export_ok=False)
    result = ms.export('D', tmp_path)
    assert not result['ok'] and not result['pptx']
    assert not (tmp_path / '.lark-slides/decks/D/exported').exists()


@pytest.mark.parametrize('pending', [False, True])
def test_unavailable_aggregate_xml_read_still_allows_official_review_export(tmp_path, monkeypatch, pending):
    work, _ = setup(tmp_path, monkeypatch)
    if pending:
        (work / 'published-pages.pending.json').write_text(json.dumps({'presentation': 'D'}))
    calls = []
    def cli(args, cwd):
        calls.append(args)
        return {'ok': False, 'error': {'code': 4001000, 'message': 'aggregate XML unavailable'}} if args[1] == '+xml-get' else {
                'ok': True, 'data': {'saved_path': './Review.pptx'}}
    monkeypatch.setattr(ms, '_cli', cli)
    result = ms.export('D', tmp_path, who='lead')
    assert result['ok'] and result['draft'] and result['needs_final_review']
    assert result['registry_advisory']['code'] == ('template_publish_pending' if pending else 'template_readback_failed')
    assert [c[1] for c in calls] == ['+xml-get', '+export']


def test_ordinary_registered_export_is_unchanged(tmp_path, monkeypatch):
    setup(tmp_path, monkeypatch)
    calls = remote(monkeypatch)
    result = ms.export('D', tmp_path, who='lead', title='Completed deck', pages=2)
    assert result['ok'] and result['final_reply_file']
    assert 'draft' not in result and 'registry_advisory' not in result
    assert [c[:2] for c in calls] == [['slides', '+xml-get'], ['drive', '+export']]


def test_solo_review_export_preserves_existing_content_gap_diagnostics(tmp_path, monkeypatch):
    work, _ = setup(tmp_path, monkeypatch)
    (work / 'published-pages.json').unlink()
    remote(monkeypatch)
    gaps = {'look': [{'page': 2, 'slide_id': 'b', 'why': ['needs-content-review']}],
            'cross_page': 'Possible cross-page content gap'}
    monkeypatch.setattr(ms, '_final_look', lambda *args: gaps)
    result = ms.export('D', tmp_path, who='solo')
    assert result['ok'] and result['draft'] and result['look'] == gaps['look']
    assert result['cross_page'] == gaps['cross_page'] and result['needs_final_review']


@pytest.mark.parametrize('gate', ['handoff', 'content'])
def test_registry_advisory_does_not_bypass_other_export_gates(tmp_path, monkeypatch, gate):
    work, _ = setup(tmp_path, monkeypatch)
    (work / 'published-pages.json').unlink()
    calls = remote(monkeypatch)
    monkeypatch.setattr(ms, '_template_export_gate', lambda *args: {
        'mode': 'assist_wait', 'expected': ['current-summary'], 'template_assist': True} if gate == 'handoff' else None)
    monkeypatch.setattr(ms, '_must_missing_hold', lambda *args: ('Required content missing', ['required section']))
    result = ms.export('D', tmp_path, who='lead')
    assert not result['ok'] and all(c[:2] != ['drive', '+export'] for c in calls)
    if gate == 'handoff':
        assert result['code'] == 'template_assist_pending'
    else:
        assert result['must_missing'] == ['required section']


def test_export_cli_defaults_advisory_and_passes_optional_strict(tmp_path, monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(ms, 'export', lambda *a, **kw: calls.append(kw) or {'ok': True})
    assert ms.main(['export', '--deck', 'D', '--cwd', str(tmp_path)]) == 0
    assert calls[-1]['strict'] is False
    assert ms.main(['export', '--deck', 'D', '--cwd', str(tmp_path), '--strict']) == 0
    assert calls[-1]['strict'] is True
