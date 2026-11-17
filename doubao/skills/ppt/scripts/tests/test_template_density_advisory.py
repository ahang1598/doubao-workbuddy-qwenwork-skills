"""Native charts and simple source components are not low-quality by node count."""
import importlib.util
from pathlib import Path

def api():
    p=Path(__file__).parents[1]/ 'template' / 'template_lint_all.py'
    spec=importlib.util.spec_from_file_location('density_lint',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m

def test_valid_simple_source_chart_is_advisory_not_a_density_block(tmp_path):
    p=tmp_path/'page.xml'
    p.write_text('<slide><data><shape id="title" type="text"><content fontSize="32"><p>真实季度经营结果</p></content></shape><chart id="chart" width="760" height="350"><chartData><dim1><chartField name="季度">Q1,Q2,Q3</chartField></dim1><dim2><chartField name="营收">12,15,18</chartField></dim2></chartData></chart></data></slide>')
    result=api().check_sparsity(p,p,'component_reuse')
    assert result['authored']['total']==2 and result['authored']['visual_other']==1
    assert result['fail_count']==0
    assert result['warning_count']>0 and result['status']=='review'

def test_counter_signal_does_not_require_automatic_refining_or_claim_visual_success():
    counts={'visual_shape':0,'visual_other':1,'text':1,'total':2,'total_text_chars':12}
    result=api()._compute_refine_triggers(counts,'active_rebuild')
    assert result['hit_count']>0
    assert result['should_refine'] is False and result['review_suggested'] is True
    assert '视觉' in result['summary']
