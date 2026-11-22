"""Default publishing records visual diagnostics; strict checks remain opt-in."""
import json
from pathlib import Path
import subprocess

import pytest

from test_template_publish import (module, Runner, READY, SUCCESS, XML, readback, cas_cache, ACTUAL,
                                   style_inputs, layout_inputs, chart_inputs)
from test_template_publish_migration import migration_inputs


def publish(tmp_path, runner, **options):
    # Exercise the API default directly, never the legacy strict fixture.
    xml = tmp_path / 'slide.xml'
    if not xml.exists():
        xml.write_text(XML)
    return module().publish(presentation='D', xml=xml, page=options.pop('page', 1),
                            mode='component_reuse', work_dir=tmp_path, runner=runner, **options)


def report(result):
    return json.loads(Path(result['report_path']).read_text())


BLOCKED = {'ok': False, 'status': 'blocked', 'block_reasons': ['text_capacity'],
           'checks': {'template_geometry': {'ok': False}}}


def test_default_visual_preflight_failure_is_diagnostic_and_server_lint_still_runs(tmp_path):
    runner = Runner(BLOCKED, SUCCESS)
    result = publish(tmp_path, runner)
    assert result['ok'] and result['status'] == 'published'
    assert result['needs_final_review'] and not result['requires_review']
    assert report(result)['preflight']['json'] == BLOCKED
    assert '--no-lint' not in runner.calls[1][0]
    assert not (tmp_path / 'published-pages.pending.json').exists()


def test_explicit_strict_preserves_visual_preflight_block(tmp_path):
    runner = Runner(BLOCKED)
    result = publish(tmp_path, runner, validation_policy='strict')
    assert result['status'] == 'preflight_blocked' and not result['ok']
    assert len(runner.calls) == 1


@pytest.mark.parametrize('link,key,status', [
    ('L3', 'layout_contract', 'layout_contract_blocked'),
    ('L6', 'chart_contract', 'chart_contract_blocked'),
    ('L8', 'migration_contract', 'migration_contract_blocked'),
])
def test_missing_automatic_contracts_are_advisory_but_strict_blocks(tmp_path, link, key, status):
    default = publish(tmp_path, Runner(READY, SUCCESS), link=link)
    assert default['ok'] and default['needs_final_review']
    assert report(default)[key]['ok'] is False
    strict_dir = tmp_path / 'strict'; strict_dir.mkdir()
    strict_runner = Runner()
    strict = publish(strict_dir, strict_runner, link=link, validation_policy='strict')
    assert strict['status'] == status and not strict_runner.calls


@pytest.mark.parametrize('option', ['source', 'style_card', 'layout_manifest', 'chart_contract', 'migration_bindings'])
def test_missing_validation_reference_is_advisory_with_complete_authored_payload(tmp_path, option):
    runner = Runner(READY, SUCCESS)
    result = publish(tmp_path, runner, **{option: tmp_path / 'missing.json'})
    assert result['ok'] and result['needs_final_review']
    assert any(isinstance(v, dict) and v.get('ok') is False for v in report(result).values())


def test_missing_actual_cas_cache_remains_a_hard_input_error(tmp_path):
    runner = Runner()
    result = publish(tmp_path, runner, no_lint=True, slide_id='S1', local_cache=tmp_path / 'missing.xml')
    assert result['status'] == 'invalid_input' and not runner.calls


@pytest.mark.parametrize('kind,link,key', [('style', 'L9', 'style_card'), ('layout', 'L3', 'layout_contract'),
                                         ('chart', 'L6', 'chart_contract'), ('migration', 'L8', 'migration_contract')])
def test_real_contract_mismatches_are_visible_diagnostics_in_default_policy(tmp_path, kind, link, key):
    if kind == 'style':
        xml, _ = style_inputs(tmp_path, 'rgb(62,74,46)')
    elif kind == 'layout':
        xml, _ = layout_inputs(tmp_path)
        xml.write_text(xml.read_text().replace('topLeftX="20"', 'topLeftX="60"'))
    elif kind == 'chart':
        xml, _ = chart_inputs(tmp_path)
        xml.write_text(xml.read_text().replace('rgb(36,81,255)', 'rgb(211,9,50)'))
    else:
        xml, _ = migration_inputs(tmp_path)
        xml.write_text(xml.read_text().replace('167 out of 173', '168 out of 173'))
    result = module().publish(presentation='D', xml=xml, page=1, mode='component_reuse',
                              work_dir=tmp_path, link=link, runner=Runner(READY, SUCCESS))
    assert result['ok'] and not result['requires_review'] and result['needs_final_review']
    assert report(result)[key]['ok'] is False and report(result)[key]['errors']


def test_direct_skip_bypasses_all_missing_validation_references_even_in_strict_mode(tmp_path):
    missing = tmp_path / 'unavailable.json'
    result = publish(tmp_path, Runner(SUCCESS, readback(XML.replace('<slide ', '<slide id="S1" ', 1))),
                     no_lint=True, validation_policy='strict', link='L8', source=missing,
                     style_card=missing, layout_manifest=missing, chart_contract=missing, migration_contract=missing,
                     exception_file=missing)
    assert result['ok'] and not list((tmp_path / 'publish-reports').glob('*.exception.json'))


@pytest.mark.parametrize('policy,pause', [('advisory', False), ('strict', True)])
def test_capacity_warning_is_final_review_in_default_and_pause_only_in_strict(tmp_path, policy, pause):
    ready = {**READY, 'checks': {'unexpected_wrapping': {'needs_capacity_review': True}}}
    result = publish(tmp_path, Runner(ready, SUCCESS), validation_policy=policy)
    assert result['ok'] and result['requires_review'] is pause
    if policy == 'advisory':
        assert result['needs_final_review']


@pytest.mark.parametrize('xml,options', [
    ('<slide>', {}),
    ('<presentation><slide/></presentation>', {}),
    ('<slide><slide/></slide>', {}),
    ('<slide id="wrong"/>', {'slide_id': 'S1'}),
    ('<slide presentation_id="another-deck"/>', {}),
])
def test_advisory_does_not_skip_xml_or_target_deck_validity(tmp_path, xml, options):
    (tmp_path / 'slide.xml').write_text(xml)
    runner = Runner()
    result = publish(tmp_path, runner, no_lint=True, **options)
    assert not result['ok'] and result['status'] == 'invalid_input' and not runner.calls


@pytest.mark.parametrize('reason', [None, 'Reviewed intentional source bleed'])
def test_direct_no_lint_needs_no_waiver_file_and_records_optional_reason(tmp_path, reason):
    runner = Runner(SUCCESS, readback(XML.replace('<slide ', '<slide id="S1" ', 1)))
    result = publish(tmp_path, runner, no_lint=True, reason=reason)
    assert result['ok'] and result['status'] == 'published'
    assert runner.calls[0][0][:3] == ['lark-cli', 'slides', '+add-slide']
    assert '--no-lint' in runner.calls[0][0] and len(runner.calls) == 2
    document = report(result)
    assert document['intent']['no_lint'] is True and document['intent']['reason'] == reason
    assert document['preflight']['skipped'] is True
    row = json.loads((tmp_path / 'published-pages.json').read_text())['pages'][0]
    assert row['no_lint'] is True and row['reason'] == reason


def test_strict_direct_no_lint_skips_visual_contracts_but_keeps_ack_readback_barrier(tmp_path):
    runner = Runner(SUCCESS, readback('<slide id="S1"><data/></slide>'))
    result = publish(tmp_path, runner, no_lint=True, validation_policy='strict', link='L3')
    assert result['status'] == 'published_content_unconfirmed' and result['write_acknowledged']
    assert result['first_difference'] and (tmp_path / 'published-pages.pending.json').exists()
    recovered = publish(tmp_path, Runner(readback(XML.replace('<slide ', '<slide id="S1" ', 1))),
                        validation_policy='strict', recover_readback=True)
    assert recovered['ok'] and not (tmp_path / 'published-pages.pending.json').exists()


@pytest.mark.parametrize('read_response', [readback('<slide id="S1"><data/></slide>'),
                                        {'ok': False, 'error': {'code': 'read-unavailable'}}])
def test_advisory_ack_with_readback_problem_remains_published_and_next_page_can_continue(tmp_path, read_response):
    result = publish(tmp_path, Runner(SUCCESS, read_response), no_lint=True)
    assert result['ok'] and result['status'] == 'published' and result['write_acknowledged']
    assert result['needs_final_review'] and not result['requires_review']
    assert not (tmp_path / 'published-pages.pending.json').exists()
    document = report(result)
    assert document.get('content_readback', {}).get('first_difference') or document['cas_post_readback'].get('validation_error')
    next_page = publish(tmp_path, Runner(READY, {'ok': True, 'data': {'slide_id': 'S2', 'xml_presentation_id': 'D'}}), page=2)
    assert next_page['ok']


def test_advisory_local_cache_post_ack_read_failure_never_leaves_global_barrier(tmp_path):
    cache = cas_cache(tmp_path)
    runner = Runner(READY, readback(ACTUAL), SUCCESS, {'ok': False, 'error': {'code': 'read-unavailable'}})
    result = publish(tmp_path, runner, local_cache=cache, slide_id='S1')
    assert result['ok'] and result['needs_final_review'] and result['cache_refreshed'] is False
    assert not (tmp_path / 'published-pages.pending.json').exists()


def test_no_lint_unknown_add_remains_pending_and_read_only_recovery_validates_override_command(tmp_path):
    first = publish(tmp_path, Runner(subprocess.TimeoutExpired('write', 120)), no_lint=True)
    assert first['status'] == 'write_unknown' and not first['ok']
    assert (tmp_path / 'published-pages.pending.json').exists()
    runner = Runner(readback(XML.replace('<slide ', '<slide id="S1" ', 1)))
    recovered = publish(tmp_path, runner, recover_write=True, slide_id='S1')
    assert recovered['ok'] and not recovered['requires_review'] and recovered['needs_final_review']
    assert len(runner.calls) == 1 and runner.calls[0][0][2] == '+xml-get'


def test_direct_skip_never_hides_a_genuine_transport_rejection(tmp_path):
    runner = Runner({'ok': False, 'error': {'code': 401, 'message': 'not authorized'}})
    result = publish(tmp_path, runner, no_lint=True)
    assert not result['ok'] and result['status'] == 'write_rejected' and len(runner.calls) == 1
    assert not (tmp_path / 'published-pages.json').exists()


@pytest.mark.parametrize('code', [4000153, 401])
def test_genuine_server_rejection_is_never_published_or_registered(tmp_path, code):
    failure = {'ok': False, 'error': {'code': code, 'message': 'server rejected'}}
    result = publish(tmp_path, Runner(READY, failure))
    assert result['status'] == 'write_rejected' and not result['ok']
    assert not (tmp_path / 'published-pages.json').exists()
    assert not (tmp_path / 'published-pages.pending.json').exists()
    if code == 4000153:
        assert '--no-lint' in result['next']


def test_cli_defaults_advisory_and_exposes_strict_direct_skip(monkeypatch, tmp_path):
    api = module(); calls = []
    monkeypatch.setattr(api, 'publish', lambda **kw: calls.append(kw) or {'ok': True})
    argv = ['--presentation', 'D', '--xml', 'slide.xml', '--page', '1', '--mode', 'component_reuse',
            '--work-dir', str(tmp_path), '--link', 'L4']
    assert api.main(argv) == 0 and calls[-1]['validation_policy'] == 'advisory'
    assert api.main(argv + ['--strict', '--no-lint', '--reason', 'Intentional visual variation']) == 0
    assert calls[-1]['validation_policy'] == 'strict' and calls[-1]['no_lint']
    assert calls[-1]['reason'] == 'Intentional visual variation'
