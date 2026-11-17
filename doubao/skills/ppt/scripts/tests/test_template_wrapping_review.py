"""Capacity warnings pause expansion; direct paragraph text is not invisible."""
import importlib.util
from pathlib import Path

from test_template_publish import invoke, Runner, READY, SUCCESS
from test_template_authoring_plan import api as plan_api, ready_pages, PublishingCLI


def lint_api():
    path = Path(__file__).parents[1] / 'template' / 'template_lint_all.py'
    spec = importlib.util.spec_from_file_location('wrapping_review_lint', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def test_direct_paragraph_title_reports_capacity_review(tmp_path):
    page = tmp_path / 'page.xml'
    page.write_text('<slide><data><shape id="title" type="text" width="404" height="56">'
                    '<content fontSize="46"><p>多项运动参与的价值</p></content></shape></data></slide>')
    result = lint_api().check_unexpected_wrapping(page)
    assert result['warning_count'] == 1
    assert result['needs_capacity_review']
    assert result['issues'][0]['estimated_lines'] == 2


def test_source_vertical_title_is_not_a_horizontal_wrapping_warning(tmp_path):
    page = tmp_path / 'page.xml'
    page.write_text('<slide><data><shape id="title" type="text" width="46" height="500">'
                    '<content fontSize="46" vert="ea-vert"><p><span>中国书法</span></p></content></shape></data></slide>')
    assert lint_api().check_unexpected_wrapping(page)['warning_count'] == 0


def test_intentional_multiline_body_that_fits_does_not_require_capacity_review(tmp_path):
    page = tmp_path / 'page.xml'
    page.write_text('<slide><data><shape id="body" type="text" width="120" height="120">'
                    '<content fontSize="20"><p>正文说明可以正常换行且不超出文本框</p></content></shape></data></slide>')
    assert lint_api().check_unexpected_wrapping(page)['needs_capacity_review'] is False


def test_explicit_breaks_cannot_hide_a_two_line_title_in_a_one_line_frame(tmp_path):
    page = tmp_path / 'page.xml'
    page.write_text('<slide><data><shape id="title" type="text" width="300" height="25">'
                    '<content fontSize="20"><p>标题<br/>第二行</p></content></shape></data></slide>')
    result = lint_api().check_unexpected_wrapping(page)
    assert result['needs_capacity_review'] and result['issues'][0]['estimated_lines'] == 2


def test_publisher_exposes_review_after_acknowledged_capacity_warning(tmp_path):
    ready = {**READY, 'checks': {'unexpected_wrapping': {'warning_count': 1, 'needs_capacity_review': True}}}
    result = invoke(tmp_path, Runner(ready, SUCCESS))
    assert result['status'] == 'published' and result['ok']
    assert result['requires_review'] is True
    assert 'unexpected_wrapping' in result['review_reasons']


def test_plan_stops_after_written_page_requiring_capacity_review(tmp_path):
    plan = ready_pages(tmp_path, 3)
    publisher = PublishingCLI()
    def boundary(argv, **kwargs):
        response = publisher(argv, **kwargs)
        import json
        payload = json.loads(response.stdout)
        payload['requires_review'] = True
        response.stdout = json.dumps(payload)
        return response
    result = plan_api().run_plan(plan, tmp_path, 'D', runner=boundary)
    assert not result['ok'] and result['status'] == 'published_requires_review'
    assert result['published_pages'] == [1]
    assert result['review_page'] == 1 and result['next_page'] == 2
    assert len(publisher.commands) == 1
