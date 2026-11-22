"""Full professional PDF input stays complete; configured budgets fail, never crop."""
from pathlib import Path
import importlib.util
import hashlib
import json
import os
import subprocess
import sys

import fitz
import pytest

SCRIPT=Path(os.environ.get('STYLE_MODULE_PATH',Path(__file__).parents[1] / 'template' / 'template_style_reference.py'))
REAL=Path(os.environ.get('PPT_REFERENCE_TEST_SOURCE', '__external_reference_fixture__'))
REAL_SHA='954adefc6d866da5455ad6721d7a501f185d7a259e0c4e7daade8f1bf7deeaf3'


def api():
    spec=importlib.util.spec_from_file_location('full_reference_module',SCRIPT)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def small_pdf(tmp_path,pages=3):
    path=tmp_path/'small.pdf';document=fitz.open()
    for i in range(pages):
        page=document.new_page(width=240,height=180)
        page.insert_text((20,30),'Heading',fontsize=18)
        page.insert_text((20,70),'Body',fontsize=12)
        page.draw_rect(fitz.Rect(15,90,70,120),color=(0,0,0),fill=(1,0,0))
        page.draw_rect(fitz.Rect(90,90,145,120),color=(0,0,0),fill=(0,0,1))
    document.save(path);document.close()
    return path


def cli(source,out,*args):
    return subprocess.run([sys.executable,str(SCRIPT),'extract','--pdf',str(source),'--out',str(out),*args],capture_output=True,text=True)


@pytest.mark.skipif(not REAL.is_file(), reason='Set PPT_REFERENCE_TEST_SOURCE to the public 87-page reference')
def test_real_87_page_reference_extracts_completely_by_default_without_source_change():
    before=REAL.read_bytes();assert hashlib.sha256(before).hexdigest()==REAL_SHA
    result=api().extract_reference(REAL)
    assert result['page_count']==87 and len(result['pages'])==87
    assert [p['page'] for p in result['pages']]==list(range(1,88))
    assert result['source_sha256']==REAL_SHA and result['input_unchanged']
    assert REAL.read_bytes()==before


@pytest.mark.skipif(not REAL.is_file(), reason='Set PPT_REFERENCE_TEST_SOURCE to the public 87-page reference')
def test_real_87_page_cli_accepts_explicit_complete_reference_limits(tmp_path):
    out=tmp_path/'all-pages.json'
    proc=cli(REAL,out,'--max-pages','500','--max-spans','20000','--max-vectors','10000')
    assert proc.returncode==0,proc.stdout+proc.stderr
    result=json.loads(out.read_text());assert result['page_count']==87 and len(result['pages'])==87
    assert result['source_sha256']==REAL_SHA


def test_small_reference_low_page_limit_fails_without_partial_output(tmp_path):
    source=small_pdf(tmp_path);raw=source.read_bytes();out=tmp_path/'partial.json'
    with pytest.raises(ValueError,match='page extraction limit'):api().extract_reference(source,max_pages=2)
    proc=cli(source,out,'--max-pages','2')
    assert proc.returncode==2 and 'page extraction limit' in proc.stdout
    assert not out.exists() and source.read_bytes()==raw


@pytest.mark.parametrize('flag,error',[('--max-spans','span extraction limit'),('--max-vectors','vector extraction limit')])
def test_total_span_and_vector_budget_fails_across_pages_without_truncation(flag,error,tmp_path):
    source=small_pdf(tmp_path);out=tmp_path/'partial.json'
    proc=cli(source,out,'--max-pages','500',flag,'3')
    assert proc.returncode==2 and error in proc.stdout
    assert not out.exists()


@pytest.mark.parametrize('flag',['--max-pages','--max-spans','--max-vectors'])
@pytest.mark.parametrize('value',['0','-1','1.5'])
def test_cli_limits_remain_positive_integers(flag,value,tmp_path):
    source=small_pdf(tmp_path,1);out=tmp_path/'out.json';proc=cli(source,out,flag,value)
    assert proc.returncode==2 and not out.exists()
    assert 'positive integers' in proc.stdout or 'invalid int value' in proc.stderr


def test_default_page_budget_remains_bounded_at_500(tmp_path):
    source=tmp_path/'501-pages.pdf';d=fitz.open()
    for _ in range(501):d.new_page()
    d.save(source);d.close()
    before = source.read_bytes()
    with pytest.raises(ValueError,match='page extraction limit'):api().extract_reference(source)
    assert source.read_bytes() == before


def test_original_100_mib_file_budget_still_rejects_before_pdf_parsing(tmp_path, monkeypatch):
    source=tmp_path/'large.pdf'
    with source.open('wb') as stream:stream.truncate(100*1024*1024+1)
    opened = []
    monkeypatch.setattr(fitz, 'open', lambda *args, **kwargs: opened.append((args, kwargs)))
    with pytest.raises(ValueError,match='100 MiB extraction limit'):api().extract_reference(source)
    assert not opened
    assert source.stat().st_size == 100*1024*1024+1
