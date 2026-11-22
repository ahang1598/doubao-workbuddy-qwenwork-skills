"""Visual references must not transfer source answers or confuse kickers with titles."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

SCRIPT = Path(__file__).parents[1] / 'template' / 'template_style_reference.py'
REFERENCE = SCRIPT.parents[5] / 'runs/template-reuse-20261105/round5-cli/runs/L9/inputs/tea_reference.pdf'


def api():
    assert SCRIPT.exists(), 'bounded visual-only reference helper is missing'
    spec = importlib.util.spec_from_file_location('template_style_reference', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def real_reference():
    pytest.importorskip('fitz')
    if not REFERENCE.exists():
        pytest.skip('local six-page audit reference is not part of the distributed skill')
    return REFERENCE


def card():
    return {'schema_version': 1, 'card_type': 'visual_style_card', 'roles': {
        'main_title': {'selected': {'fontFamily': 'Noto Serif SC', 'fontSize': 30,
                                    'color': '#C49A3C'},
                       'field_basis': {'fontFamily': 'explicit_user',
                                       'fontSize': 'explicit_user', 'color': 'explicit_user'}}}}


def text(element_id, kind='title', color='rgb(196,154,60)', size=30,
         font='Noto Serif SC', body='独立主题标题'):
    return (f'<shape id="{element_id}" type="text" topLeftX="65" topLeftY="52" width="700" height="44">'
            f'<content textType="{kind}" fontSize="{size}" fontFamily="{font}" color="{color}">'
            f'<p>{body}</p></content></shape>')


def slide(*elements):
    return '<slide><data>' + ''.join(elements) + '</data><note>London Three tests</note></slide>'


def codes(report):
    return {issue['code'] for issue in report['errors']}


def persisted_override_card():
    reference = {'schema_version': 1, 'reference_type': 'pdf_visual_only', 'pages': []}
    return api().build_style_card(reference, role_overrides={
        'main_title': {'basis': 'explicit_user', 'values': {
            'fontFamily': 'Noto Serif SC', 'fontSize': 30, 'color': '#6f42c1',
            'bold': False, 'italic': False}},
        'body': {'basis': 'explicit_user', 'values': {'fontSize': 16}},
        'background': {'basis': 'explicit_user', 'values': {'color': '#F8F2EC'}}})


def test_helper_card_with_saved_overrides_remains_valid_after_json_roundtrip():
    m = api(); selected = json.loads(json.dumps(persisted_override_card()))
    # Equivalent RGB notation is still the same explicit color, not a new choice.
    selected['roles']['main_title']['selected']['color'] = 'rgb(111,66,193)'
    selected['user_overrides']['main_title']['values']['color'] = '6f42c1'
    before = copy.deepcopy(selected)
    assert m.validate_sml_roles(slide(text('main', color='#6F42C1')), selected)['ok']
    assert selected == before


@pytest.mark.parametrize(('role', 'field', 'replacement'), [
    ('main_title', 'color', '#3E4A2E'),
    ('main_title', 'fontSize', 31),
    ('main_title', 'fontFamily', 'Source Han Serif SC'),
    ('main_title', 'bold', True),
    ('main_title', 'italic', True),
    ('body', 'fontSize', 18),
    ('background', 'color', '#FFFFFF'),
])
def test_saved_explicit_override_cannot_be_replaced_in_selected(role, field, replacement):
    m = api(); selected = persisted_override_card()
    selected['roles'][role]['selected'][field] = replacement
    with pytest.raises(ValueError, match='explicit_user'):
        m.validate_sml_roles(slide(text('main', color='#6F42C1')), selected)


@pytest.mark.parametrize('basis', ['reference_candidate', None])
def test_saved_explicit_override_cannot_be_downgraded_or_omitted_in_field_basis(basis):
    m = api(); selected = persisted_override_card()
    if basis is None:
        del selected['roles']['main_title']['field_basis']['color']
    else:
        selected['roles']['main_title']['field_basis']['color'] = basis
    with pytest.raises(ValueError, match='explicit_user'):
        m.validate_sml_roles(slide(text('main', color='#6F42C1')), selected)


def test_reference_colored_sml_cannot_pass_by_rewriting_saved_override_selection_and_basis():
    m = api(); selected = persisted_override_card()
    selected['roles']['main_title']['selected']['color'] = '#3E4A2E'
    selected['roles']['main_title']['field_basis']['color'] = 'reference_candidate'
    with pytest.raises(ValueError, match='explicit_user'):
        m.validate_sml_roles(slide(text('main', color='#3E4A2E')), selected)


@pytest.mark.parametrize('removed', ['role', 'field', 'field_basis'])
def test_saved_override_requires_its_corresponding_role_selection_and_basis(removed):
    m = api(); selected = persisted_override_card()
    if removed == 'role':
        del selected['roles']['background']
    elif removed == 'field':
        del selected['roles']['main_title']['selected']['color']
    else:
        del selected['roles']['main_title']['field_basis']
    with pytest.raises(ValueError, match='explicit_user'):
        m.validate_sml_roles(slide(text('main', color='#6F42C1')), selected)


@pytest.mark.parametrize('has_override_key', [False, True])
def test_historical_card_without_saved_overrides_remains_valid(has_override_key):
    m = api(); selected = card()
    if has_override_key:
        selected['user_overrides'] = {}
    assert m.validate_sml_roles(slide(text('main')), selected)['ok']


def test_external_overrides_match_normalized_card_values_without_mutating_either_input():
    m = api(); selected = persisted_override_card()
    explicit = {'main_title': {'basis': 'explicit_user', 'values': {'color': 'rgb(111,66,193)'}}}
    before = copy.deepcopy((selected, explicit))
    assert m.validate_sml_roles(slide(text('main', color='#6F42C1')), selected,
                                user_overrides=explicit)['ok']
    assert (selected, explicit) == before


@pytest.mark.parametrize('tamper', ['missing', 'empty', 'role', 'field', 'rewritten'])
def test_external_gold_requirement_cannot_be_bypassed_by_erasing_or_rewriting_card_overrides(tamper):
    m = api(); selected = card()
    selected['user_overrides'] = {'main_title': {'basis': 'explicit_user', 'values': {'color': '#C49A3C'}}}
    explicit = {'main_title': {'basis': 'explicit_user', 'values': {'color': '#C49A3C'}}}
    if tamper == 'missing':
        del selected['user_overrides']
    elif tamper == 'empty':
        selected['user_overrides'] = {}
    elif tamper == 'role':
        selected['user_overrides'] = {'body': {'basis': 'explicit_user', 'values': {'color': '#C49A3C'}}}
    elif tamper == 'field':
        selected['user_overrides']['main_title']['values'] = {'fontSize': 30}
    else:
        selected['user_overrides']['main_title']['values']['color'] = '#3E4A2E'
    selected['roles']['main_title']['selected']['color'] = '#3E4A2E'
    selected['roles']['main_title']['field_basis']['color'] = 'reference_candidate'
    with pytest.raises(ValueError, match='explicit_user'):
        m.validate_sml_roles(slide(text('main', color='#3E4A2E')), selected, user_overrides=explicit)


def test_external_requirement_needs_saved_marker_even_when_selected_sml_already_matches():
    m = api(); explicit = {'main_title': {'basis': 'explicit_user', 'values': {'color': '#C49A3C'}}}
    with pytest.raises(ValueError, match='explicit_user'):
        m.validate_sml_roles(slide(text('main')), card(), user_overrides=explicit)


def test_font_substitution_preserves_saved_override_card_and_does_not_waive_size_or_color():
    m = api(); selected = persisted_override_card()
    substitution = {'from': 'Noto Serif SC', 'to': 'Source Han Serif SC',
                    'basis': 'font_unavailable', 'reason': 'Requested font is unavailable in the authoring runtime.'}
    xml = slide(text('main', color='#6F42C1', font='Source Han Serif SC'))
    assert m.validate_sml_roles(xml, selected, font_substitutions=[substitution])['ok']
    bad = slide(text('main', color='#3E4A2E', size=32, font='Source Han Serif SC'))
    assert {'role_color_mismatch', 'role_size_mismatch'} <= codes(
        m.validate_sml_roles(bad, selected, font_substitutions=[substitution]))
    selected['roles']['main_title']['selected']['fontFamily'] = 'Source Han Serif SC'
    with pytest.raises(ValueError, match='explicit_user'):
        m.validate_sml_roles(xml, selected, font_substitutions=[substitution])


def test_real_pdf_metrics_have_main_title_role_even_when_lower_kpis_are_larger():
    m = api(); result = m.extract_reference(real_reference())
    assert result['page_count'] == 6
    page = result['pages'][1]
    title_id = page['role_candidates']['main_title'][0]
    title = next(span for span in page['spans'] if span['span_id'] == title_id)
    assert title['font'] == 'Georgia-Bold'
    assert title['size_pt'] == pytest.approx(29.991, abs=.001)
    assert title['color'] == '#3E4A2E'
    assert title['bbox'][:2] == pytest.approx([64.772, 45.690], abs=.001)
    assert any(s['size_pt'] > title['size_pt'] and s['span_id'] != title_id for s in page['spans'])
    assert page['background']['color'] == '#FAF7EF'
    assert page['images'] and set(page['images'][0]) == {'bbox'}
    assert any(v['kind'] == 'thin_rule' and v['fill'] == '#C49A3C' for v in page['vectors'])
    assert 0 < page['density']['text_bbox_coverage'] < .3
    chosen = m.build_style_card(result, source_page=2)['roles']['main_title']['selected']
    assert chosen['fontFamily'] == 'Georgia' and chosen['bold'] is True
    assert chosen['fontSize'] == pytest.approx(29.991, abs=.001)
    assert chosen['color'] == '#3E4A2E'


def test_export_never_contains_reference_words_labels_metadata_or_word_hashes_and_input_is_immutable():
    m = api(); pdf = real_reference(); before = pdf.read_bytes()
    reference = m.extract_reference(pdf)
    serialized = json.dumps({'reference': reference, 'card': m.build_style_card(reference)}).lower()
    for phrase in ('London', 'provenance', 'repeat rate', 'Three tests', 'Outlook',
                   'A quieter', 'City patterns', 'tea_reference.pdf'):
        assert phrase.lower() not in serialized
        assert hashlib.sha256(phrase.encode()).hexdigest() not in serialized
    forbidden = {'text', 'chars', 'c', 'words', 'label', 'name', 'metadata', 'image_bytes', 'word_hash'}
    def check(node):
        if isinstance(node, dict):
            assert not forbidden.intersection(node)
            for value in node.values(): check(value)
        elif isinstance(node, list):
            for value in node: check(value)
    check(reference)
    assert reference['source_sha256'] == '37408df351d4f4f63757af68920392158c0bcd9ed46016f83fe8723de5e605b5'
    assert pdf.read_bytes() == before


def test_explicit_user_gold_serif_main_title_overrides_green_source_without_rewriting_candidates():
    m = api(); reference = m.extract_reference(real_reference()); before = copy.deepcopy(reference)
    overrides = {'main_title': {'basis': 'explicit_user', 'values': {
        'color': '#C49A3C', 'fontFamily': 'Noto Serif SC', 'fontSize': 30}},
        'background': {'basis': 'explicit_user', 'values': {'color': '#FAF7EF'}},
        'body': {'basis': 'explicit_user', 'values': {'fontSize': 16}}}
    result = m.build_style_card(reference, role_overrides=overrides)
    title = result['roles']['main_title']
    assert title['selected']['color'] == '#C49A3C'
    assert title['selected']['fontFamily'] == 'Noto Serif SC'
    assert title['field_basis']['color'] == 'explicit_user'
    assert any(c['style']['color'] == '#3E4A2E' for c in title['reference_candidates'])
    assert result['user_overrides'] == overrides
    assert reference == before
    xml = slide(text('main').replace('textType="title"', 'textType="title" bold="true" italic="false"'))
    assert m.validate_sml_roles(xml, result)['ok']
    wrong = xml.replace('rgb(196,154,60)', 'rgb(62,74,46)')
    report = m.validate_sml_roles(wrong, result)
    assert not report['ok']
    assert any(e['expected'] == '#C49A3C' for e in report['errors'] if e['code'] == 'role_color_mismatch')


def test_gold_kicker_cannot_satisfy_wrong_green_main_title_even_if_bound_to_title():
    m = api()
    xml = slide(text('main', color='rgb(62,74,46)'), text('kicker', 'caption', size=12))
    report = m.validate_sml_roles(xml, card(), bindings={'main_title': ['kicker']})
    assert not report['ok']
    assert any(e['code'] == 'role_color_mismatch' and e['element_id'] == 'main' for e in report['errors'])
    assert any(e['code'] == 'role_size_mismatch' and e['element_id'] == 'kicker' for e in report['errors'])
    assert report['semantic_copy'] == 'not_assessed'
    assert 'London' not in json.dumps(report) and 'Three tests' not in json.dumps(report)


def test_no_main_title_is_a_failure_and_explicit_id_can_bind_a_real_main_title():
    m = api(); xml = slide(text('main', 'body'), text('kicker', 'caption', size=12))
    assert 'missing_main_title' in codes(m.validate_sml_roles(xml, card()))
    assert m.validate_sml_roles(xml, card(), bindings={'main_title': ['main']})['ok']


def test_explicit_main_title_binding_is_not_also_checked_as_body():
    m = api(); selected = card()
    selected['roles']['body'] = {'selected': {'fontFamily': 'Noto Serif SC', 'fontSize': 16, 'color': '#4A4A4A'}}
    xml = slide(text('main', 'body'), text('body', 'body', size=16, color='#4A4A4A'))
    report = m.validate_sml_roles(xml, selected, bindings={'main_title': ['main']})
    assert report['ok'], report
    assert {'element_id': 'main', 'page': 1, 'role': 'body'} not in report['checked_elements']


def test_validation_rejects_palette_only_title_card_without_size_and_family():
    m = api(); selected = card(); selected['roles']['main_title']['selected'] = {'color': '#C49A3C'}
    with pytest.raises(ValueError):
        m.validate_sml_roles(slide(text('kicker', size=12)), selected)


def test_report_discloses_selected_body_role_without_any_authored_body_check():
    m = api(); selected = card()
    selected['roles']['body'] = {'selected': {'fontSize': 16}}
    report = m.validate_sml_roles(slide(text('main')), selected)
    assert report['ok'] and 'body' in report['unchecked_roles']


def test_title_span_override_and_theme_inheritance_are_checked_on_visible_runs():
    m = api()
    theme = '<theme><textStyles><title fontFamily="Noto Serif SC" fontSize="30" fontColor="rgb(196,154,60)"/></textStyles></theme>'
    xml = '<presentation>' + theme + slide('<shape id="main" type="text"><content textType="title"><p>独立标题</p></content></shape>') + '</presentation>'
    assert m.validate_sml_roles(xml, card())['ok']
    bad = xml.replace('独立标题', '<span color="rgb(62,74,46)">独立标题</span>')
    assert 'role_color_mismatch' in codes(m.validate_sml_roles(bad, card()))


def test_omitted_regular_weight_and_italic_flags_do_not_create_false_mismatches():
    m = api(); selected = card()
    selected['roles']['main_title']['selected'].update({'bold': False, 'italic': False})
    assert m.validate_sml_roles(slide(text('main')), selected)['ok']
    bold = slide(text('main').replace('textType="title"', 'textType="title" bold="true"'))
    assert 'role_bold_mismatch' in codes(m.validate_sml_roles(bold, selected))


def test_unavailable_font_substitution_needs_specific_reason_and_cannot_waive_color():
    m = api(); xml = slide(text('main', font='Source Han Serif SC'))
    assert 'role_font_mismatch' in codes(m.validate_sml_roles(xml, card()))
    substitution = {'from': 'Noto Serif SC', 'to': 'Source Han Serif SC',
                    'basis': 'font_unavailable', 'reason': 'Authoring runtime lacks the requested font.'}
    report = m.validate_sml_roles(xml, card(), font_substitutions=[substitution])
    assert report['ok'] and report['font_substitutions'][0]['availability_verified'] is False
    bad = slide(text('main', font='Source Han Serif SC', color='rgb(62,74,46)'))
    assert 'role_color_mismatch' in codes(m.validate_sml_roles(bad, card(), font_substitutions=[substitution]))
    with pytest.raises(ValueError):
        m.validate_sml_roles(xml, card(), font_substitutions=[{**substitution, 'reason': ''}])


def test_validation_cli_works_from_stdin_without_optional_pdf_dependencies(tmp_path):
    api(); path = tmp_path / 'card.json'; path.write_text(json.dumps(card()))
    result = subprocess.run([sys.executable, '-S', str(SCRIPT), 'validate', '--sml', '-', '--card', str(path)],
                            input=slide(text('main')), text=True, capture_output=True)
    assert result.returncode == 0, result.stderr + result.stdout
    assert json.loads(result.stdout)['ok']
    bad = subprocess.run([sys.executable, '-S', str(SCRIPT), 'validate', '--sml', '-', '--card', str(path)],
                         input=slide(text('main', color='#3E4A2E')), text=True, capture_output=True)
    assert bad.returncode == 1 and 'role_color_mismatch' in codes(json.loads(bad.stdout))


def test_extract_cli_refuses_to_overwrite_source_pdf(tmp_path):
    api(); source = tmp_path / 'immutable.pdf'; source.write_bytes(real_reference().read_bytes())
    before = source.read_bytes()
    result = subprocess.run([sys.executable, str(SCRIPT), 'extract', '--pdf', str(source), '--out', str(source)],
                            text=True, capture_output=True)
    assert result.returncode == 2
    assert source.read_bytes() == before


def test_extract_cli_refuses_output_hardlink_to_immutable_source_pdf(tmp_path):
    api(); source = tmp_path / 'immutable.pdf'; source.write_bytes(real_reference().read_bytes())
    output = tmp_path / 'looks-like-json.json'; os.link(source, output)
    before = source.read_bytes()
    result = subprocess.run([sys.executable, str(SCRIPT), 'extract', '--pdf', str(source), '--out', str(output)],
                            text=True, capture_output=True)
    assert result.returncode == 2
    assert source.read_bytes() == before


def test_reference_page_limit_fails_without_silent_partial_export_or_mutation():
    m = api(); source = real_reference(); before = source.read_bytes()
    with pytest.raises(ValueError, match='page extraction limit'):
        m.extract_reference(source, max_pages=5)
    assert source.read_bytes() == before


def test_extract_cli_does_not_silently_ignore_requested_user_overrides(tmp_path):
    api(); overrides = tmp_path / 'overrides.json'
    overrides.write_text(json.dumps({'main_title': {'basis': 'explicit_user', 'values': {'color': '#C49A3C'}}}))
    result = subprocess.run([sys.executable, str(SCRIPT), 'extract', '--pdf', str(real_reference()),
                             '--overrides', str(overrides)], text=True, capture_output=True)
    assert result.returncode == 2 and 'style-card' in json.loads(result.stdout)['error']


def test_non_user_override_cannot_replace_source_and_unknown_content_field_is_rejected():
    m = api(); reference = m.extract_reference(real_reference())
    with pytest.raises(ValueError):
        m.build_style_card(reference, role_overrides={'main_title': {'basis': 'reference', 'values': {'color': '#C49A3C'}}})
    with pytest.raises(ValueError):
        m.build_style_card(reference, role_overrides={'main_title': {'basis': 'explicit_user', 'values': {'text': 'copied answer'}}})
