"""Installed original-PPTX rendering must not be confused with cloud placeholders."""
import hashlib
import importlib.util
from pathlib import Path
import subprocess
import sys


def api():
    path = Path(__file__).parents[1] / 'template' / 'parse_template.py'
    spec = importlib.util.spec_from_file_location('source_preview_api', path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    original = list(sys.path)
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = original
    return module


def test_path_renderer_takes_precedence_over_app_probe(monkeypatch):
    m = api()
    monkeypatch.setattr(m.shutil, 'which', lambda name: '/bin/soffice' if name == 'soffice' else None)
    monkeypatch.setattr(m, '_soffice_candidates', lambda: ())
    assert m._find_soffice() == '/bin/soffice'


def test_mac_app_is_discovered_without_path_or_install(monkeypatch, tmp_path):
    m = api();binary=tmp_path/'LibreOffice.app/Contents/MacOS/soffice'
    binary.parent.mkdir(parents=True);binary.write_text('fixture');binary.chmod(0o755)
    monkeypatch.setattr(m.shutil,'which',lambda name:None)
    monkeypatch.setattr(m,'_soffice_candidates',lambda:(binary,))
    assert m._find_soffice()==str(binary)
    assert m._detect_capabilities()[0]['soffice'] is True


def test_non_executable_app_does_not_claim_renderer(monkeypatch, tmp_path):
    m=api();binary=tmp_path/'soffice';binary.write_text('fixture');binary.chmod(0o644)
    monkeypatch.setattr(m.shutil,'which',lambda name:None)
    monkeypatch.setattr(m,'_soffice_candidates',lambda:(binary,))
    assert m._find_soffice() is None


def test_conversion_has_its_own_profile_and_keeps_original(monkeypatch, tmp_path):
    m=api();source=tmp_path/'source.pptx';source.write_bytes(b'original source fixture')
    digest=hashlib.sha256(source.read_bytes()).hexdigest();out=tmp_path/'new-dir';profile_paths=[]
    monkeypatch.setattr(m,'_find_soffice',lambda:'/installed/soffice')
    def run(args, **kwargs):
        assert args[0]=='/installed/soffice' and kwargs['check'] is True
        assert out.is_dir() and str(source) in args
        profile=next(a for a in args if a.startswith('-env:UserInstallation='))
        from urllib.parse import unquote, urlparse
        p=Path(unquote(urlparse(profile.split('=',1)[1]).path));assert p.is_dir();profile_paths.append(p)
        (out/'source.pdf').write_bytes(b'%PDF fixture')
        return subprocess.CompletedProcess(args,0,b'',b'')
    monkeypatch.setattr(m.subprocess,'run',run)
    assert m._pptx_to_pdf(source,out)==out/'source.pdf'
    assert profile_paths and not profile_paths[0].exists()
    assert hashlib.sha256(source.read_bytes()).hexdigest()==digest


def test_failed_original_conversion_never_claims_success(monkeypatch, tmp_path):
    m=api();source=tmp_path/'source.pptx';source.write_bytes(b'original')
    monkeypatch.setattr(m,'_find_soffice',lambda:'/installed/soffice')
    def fail(args, **kwargs):raise subprocess.CalledProcessError(1,args)
    monkeypatch.setattr(m.subprocess,'run',fail)
    assert m._pptx_to_pdf(source,tmp_path/'out') is None


def test_next_hint_uses_actual_publisher_and_main_handles_difficult_pages(tmp_path):
    hint=api()._next_step_hint(tmp_path)
    assert 'template_publish.py' in hint and 'MainAgent' in hint
    assert '--template-assist' not in hint and 'Organizer' not in hint
    assert '不派 Organizer' not in hint
    assert 'native-chart-inventory' in hint
    assert '交付（Step 6）' in hint and 'Step 7' not in hint
    assert '全稿回读' not in hint and '视觉验收' not in hint and '全稿终检' not in hint
