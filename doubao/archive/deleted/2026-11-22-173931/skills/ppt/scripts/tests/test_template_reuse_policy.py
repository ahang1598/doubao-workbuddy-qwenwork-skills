import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("template_lint_all", Path(__file__).parents[1] / "template" / "template_lint_all.py")
lint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lint)

def test_rebuilt_page_retaining_real_components_is_reviewed_not_destroyed(tmp_path):
    source = tmp_path / "source.xml"
    authored = tmp_path / "authored.xml"
    source.write_text('<slide><data><shape id="a"><p><t>示例文本</t></p></shape><shape id="b"/><line id="c"/><img id="d" src="token"/></data></slide>')
    authored.write_text(source.read_text().replace('示例文本', '本期实际经营结论'))
    result = lint.check_template_copy_overfit(authored, source, 'active_rebuild')
    assert result['shared_ratio'] == 1
    assert result['fail_count'] == 0
    assert result['issues'][0]['severity'] == 'warning'

def test_component_reuse_keeps_placeholder_check(tmp_path):
    source = tmp_path / 's.xml'
    source.write_text('<slide><shape id="a"><t>示例文本</t></shape></slide>')
    result = lint.check_placeholders(source, source)
    assert '示例文本' in str(result)
    assert lint.check_template_copy_overfit(source, source, 'component_reuse')['fail_count'] == 0
