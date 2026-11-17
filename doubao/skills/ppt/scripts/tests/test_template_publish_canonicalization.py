"""Service canonicalization is harmless only with intact content and references."""
import json
from pathlib import Path
import subprocess

import pytest

from test_template_publish import module, invoke, Runner, READY, SUCCESS, XML, readback
from test_template_publish_content_recovery import rejection_and_preflight


AUTHORED = ('<slide><data><shape id="rect" type="rect" width="960" height="540" '
            'topLeftX="0" topLeftY="0"><fill><solid color="#fff"/></fill></shape>'
            '<img id="image" src="media-original" width="20"/></data>'
            '<note><content><p>Exact speaker notes.</p></content></note></slide>')
SERVICE = (AUTHORED.replace('id="rect"', 'id="remote-rect" presetHandlers="0"')
           .replace('id="image"', 'id="remote-image"').replace('<note>', '<note id="remote-note">'))


@pytest.mark.parametrize('actual', [
    AUTHORED.replace('<note>', '<note id="remote-note">'),
    AUTHORED.replace('id="rect"', 'id="remote-rect" presetHandlers="0"'),
    SERVICE,
])
def test_generated_note_id_and_rect_zero_default_preserve_submitted_content(actual):
    assert module()._payload_matches(AUTHORED, actual)


def test_generated_note_id_does_not_shift_ids_of_later_referenced_members():
    expected = ('<slide><note><p>Notes</p></note><data><shape id="A"/>'
                '<shape id="B"/><line startShapeId="A" endShapeId="B"/></data></slide>')
    actual = expected.replace('<note>', '<note id="N">').replace('"A"', '"X"').replace('"B"', '"Y"')
    assert module()._payload_matches(expected, actual)
    assert not module()._payload_matches(expected, actual.replace('endShapeId="Y"', 'endShapeId="X"'))


@pytest.mark.parametrize('actual', [
    SERVICE.replace('Exact speaker notes.', 'Changed speaker notes.'),
    SERVICE.replace('media-original', 'media-replacement'),
    SERVICE.replace('width="960"', 'width="959.999999999"'),
    SERVICE.replace('presetHandlers="0"', 'presetHandlers="16"'),
    SERVICE.replace('color="#fff"', 'color="#000"'),
    SERVICE.replace('<note id="remote-note">', '<note id="remote-note" role="new-default">'),
    SERVICE.replace('<img ', '<img refId="remote-note" '),
    SERVICE.replace('id="remote-note"', 'id="remote-image"'),
])
def test_service_canonicalization_never_masks_content_or_reference_changes(actual):
    try:
        matches = module()._payload_matches(AUTHORED, actual)
    except ValueError:  # Duplicate member IDs must remain invalid.
        matches = False
    assert not matches


@pytest.mark.parametrize('tag', ['<shape type="round-rect"', '<shape type="ellipse"', '<crop type="rect"'])
def test_rect_zero_rule_does_not_apply_to_other_shapes_or_crop(tag):
    expected = '<slide><data>' + tag + '/></data></slide>'
    assert not module()._payload_matches(expected, expected.replace('/>', ' presetHandlers="0"/>', 1))


def test_explicit_note_identity_cannot_be_removed():
    assert not module()._payload_matches(SERVICE, SERVICE.replace(' id="remote-note"', ''))


def test_explicit_rect_handler_cannot_be_removed():
    assert not module()._payload_matches(SERVICE, SERVICE.replace(' presetHandlers="0"', ''))


@pytest.mark.parametrize('member', [
    '<img id="A" src="A"/>',
    '<chart id="A"><values><value label="A"/></values></chart>',
    '<shape id="A"><content color="A"><p>A</p></content></shape>',
])
def test_media_chart_and_style_literals_equal_to_member_ids_are_not_id_references(member):
    expected = '<slide><data>' + member + '</data></slide>'
    actual = expected.replace('"A"', '"B"')
    assert not module()._payload_matches(expected, actual)


def test_geometry_serialization_is_exact_even_beyond_decimal_context_precision():
    expected = '<slide><data><shape width="960.00000000000000000000000000001"/></data></slide>'
    assert not module()._payload_matches(expected, expected.replace('00001', '00002'))
    assert module()._payload_matches(AUTHORED, AUTHORED.replace('width="960"', 'width="960.0"'))


def test_chart_values_and_note_paragraph_structure_remain_exact():
    expected = ('<slide><data><chart id="C"><values><value>10</value></values></chart></data>'
                '<note><content><p>First</p><p>Second</p></content></note></slide>')
    canonical = expected.replace('id="C"', 'id="remote-C"').replace('<note>', '<note id="N">')
    assert module()._payload_matches(expected, canonical)
    assert not module()._payload_matches(expected, canonical.replace('<value>10</value>', '<value>11</value>'))
    assert not module()._payload_matches(expected, canonical.replace('<p>First</p><p>Second</p>', '<p>First Second</p>'))


def test_unknown_write_returns_first_difference_and_keeps_pending(tmp_path):
    actual = XML.replace('<slide ', '<slide id="S1" ', 1).replace('真实正文', '旧内容')
    result = invoke(tmp_path, Runner(READY, subprocess.TimeoutExpired('write', 120), readback(actual)), slide_id='S1')
    assert result['status'] == 'write_content_unconfirmed'
    difference = {'path': '/slide/data[1]/shape[1]/content[1]/p[1]/text()',
                  'expected': '真实正文', 'actual': '旧内容'}
    assert result['first_difference'] == difference
    report = json.loads(Path(result['report_path']).read_text())
    assert report['write_recovery']['first_difference'] == difference
    assert (tmp_path / 'published-pages.pending.json').exists()


def test_ack_and_read_only_recovery_expose_differences_without_resending(tmp_path):
    ready, failure = rejection_and_preflight(tmp_path)
    actual = XML.replace('<slide ', '<slide id="S1" ', 1).replace('真实正文', 'Changed')
    result = invoke(tmp_path, Runner(ready, failure, SUCCESS, readback(actual)), slide_id='S1')
    assert result['status'] == 'published_content_unconfirmed'
    difference = result['first_difference']
    assert difference['expected'] == '真实正文' and difference['actual'] == 'Changed'
    report = json.loads(Path(result['report_path']).read_text())
    assert report['content_readback']['first_difference'] == difference
    runner = Runner(readback(actual))
    recovered = invoke(tmp_path, runner, slide_id='S1', recover_readback=True)
    assert recovered['status'] == 'readback_recovery_failed'
    assert recovered['first_difference'] == difference
    report = json.loads(Path(recovered['report_path']).read_text())
    assert report['content_readback']['first_difference'] == difference
    assert len(runner.calls) == 1 and runner.calls[0][0][2] == '+xml-get'
    assert (tmp_path / 'published-pages.pending.json').exists()


def test_service_canonicalization_clears_ack_barrier_in_actual_publisher(tmp_path):
    xml = tmp_path / 'authoring' / 'slide-01.xml'
    xml.parent.mkdir(); xml.write_text(AUTHORED)
    ready, failure = rejection_and_preflight(tmp_path)
    result = invoke(tmp_path, Runner(ready, failure, SUCCESS, readback(SERVICE.replace('<slide>', '<slide id="S1">'))), slide_id='S1')
    assert result['ok'] and result['xml_readback_complete']
    assert not (tmp_path / 'published-pages.pending.json').exists()


def test_full_report_preserves_long_difference_while_result_stays_concise(tmp_path):
    actual = XML.replace('<slide ', '<slide id="S1" ', 1).replace('真实正文', 'X' * 1000)
    result = invoke(tmp_path, Runner(READY, subprocess.TimeoutExpired('write', 120), readback(actual)), slide_id='S1')
    report = json.loads(Path(result['report_path']).read_text())
    assert report['write_recovery']['first_difference']['actual'] == 'X' * 1000
    assert len(result['first_difference']['actual']) <= 200
    assert result['first_difference']['actual_truncated'] is True


def test_attribute_difference_reports_original_values_and_element_path(tmp_path):
    xml = tmp_path / 'authoring' / 'slide-01.xml'
    xml.parent.mkdir(); xml.write_text(AUTHORED)
    actual = SERVICE.replace('width="960"', 'width="900"').replace('<slide>', '<slide id="S1">')
    result = invoke(tmp_path, Runner(READY, subprocess.TimeoutExpired('write', 120), readback(actual)), slide_id='S1')
    assert result['first_difference'] == {'path': '/slide/data[1]/shape[1]/@width', 'expected': '960', 'actual': '900'}
