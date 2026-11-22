"""Template preflight permits MainAgent to finish every page without delegation."""
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import multiagent_sync as ms
from scripts.template import parse_template as pt
from scripts.template import template_lint_all as tla
SKILL = Path(__file__).resolve().parents[2]
SLIDE = ('<slide xmlns="https://www.larkoffice.com/sml/2.0"><data>'
         '<shape type="text" topLeftX="40" topLeftY="40" width="400" height="60"><content><p>标题</p></content></shape>'
         '</data></slide>')


def _work(tmp_path, plan_pages=None, n_slides=3):
    work = tmp_path / ".lark-slides" / "template" / "t1"
    (work / "authoring").mkdir(parents=True)
    (work / "manifest").mkdir()
    (work / "manifest" / "template-index.json").write_text("{}")
    if plan_pages:
        rows = "\n".join(f"| P{i} | content | active_rebuild | slide-0{i} | - | - | - | x |" for i in range(1, plan_pages + 1))
        (work / "page-plan.md").write_text("Style: fallback\n\n| 目标页 | 页形 |\n|---|---|\n" + rows + "\n")
    for i in range(1, n_slides + 1):
        (work / "authoring" / f"slide-{i:02d}.xml").write_text(SLIDE)
    return work


def _check(work, n):
    return tla.check_template_dispatch(work / "authoring" / f"slide-{n:02d}.xml", SKILL)


def test_page_3_needs_no_dispatch(tmp_path):
    work = _work(tmp_path, plan_pages=9)
    res = _check(work, 3)
    assert not res.get("fail")
    assert not (tmp_path / ".lark-slides" / "dispatch.json").exists()


def test_missing_page_plan_does_not_require_delegation(tmp_path):
    work = _work(tmp_path, n_slides=3)
    assert not _check(work, 3).get("fail")
    work2 = _work(tmp_path / "b", n_slides=2)
    assert not _check(work2, 2).get("fail")


def test_cli_default_needs_no_solo_flag_or_dispatch(tmp_path):
    work = _work(tmp_path, plan_pages=9)
    p = subprocess.run([sys.executable, str(SKILL / "scripts" / "template" / "template_lint_all.py"), "--authored",
                        str(work / "authoring" / "slide-03.xml"), "--skill-root", str(SKILL)],
                       capture_output=True, text=True)
    out = json.loads(p.stdout)
    assert not any("organizer_not_dispatched" in r for r in out.get("block_reasons", []))


def test_solo_skips_dispatch_gate(tmp_path):
    work = _work(tmp_path, plan_pages=9)
    res = tla.check_template_dispatch(work / "authoring" / "slide-03.xml", SKILL, solo=True)
    assert not res.get("fail") and res["dispatched"].startswith("solo")


def test_cli_solo_not_blocked(tmp_path):
    work = _work(tmp_path, plan_pages=9)
    p = subprocess.run([sys.executable, str(SKILL / "scripts" / "template" / "template_lint_all.py"), "--authored",
                        str(work / "authoring" / "slide-03.xml"), "--skill-root", str(SKILL), "--solo",
                        "--page-role", "active_rebuild"],
                       capture_output=True, text=True)
    out = json.loads(p.stdout)
    assert not any("organizer_not_dispatched" in r for r in out.get("block_reasons", []))


def test_passes_with_open_dispatch(tmp_path, monkeypatch):
    work = _work(tmp_path, plan_pages=9)
    monkeypatch.setattr(ms, "_retire_open_tasks", lambda *a, **k: [])
    assert ms.dispatch(str(tmp_path), "template")["ok"]
    res = _check(work, 3)
    assert not res.get("fail")


def test_closed_old_dispatch_does_not_block_main(tmp_path):
    work = _work(tmp_path, plan_pages=9)
    (tmp_path / ".lark-slides" / "dispatch.json").write_text(
        json.dumps({"flow": "template", "t": time.time() - 99999, "closed": time.time() - 99000}))
    assert not _check(work, 3).get("fail")


def test_passes_when_page_plan_has_two_pages(tmp_path):
    work = _work(tmp_path, plan_pages=2, n_slides=2)
    res = _check(work, 2)
    assert not res.get("fail")


def test_passes_in_lead_mode(tmp_path, monkeypatch):
    work = _work(tmp_path, plan_pages=9)
    monkeypatch.setattr(ms, "_retire_open_tasks", lambda *a, **k: [])
    assert ms.role(str(tmp_path))["role"] == "lead"   # legacy label; no new Lead state
    res = _check(work, 3)
    assert not res.get("fail")


def test_not_checked_outside_authoring_or_cwd(tmp_path):
    f = tmp_path / "lint" / "final-p3.xml"
    f.parent.mkdir()
    f.write_text(SLIDE)
    assert not tla.check_template_dispatch(f, SKILL)["checked"]
    g = tmp_path / "x" / "authoring" / "slide-05.xml"
    g.parent.mkdir(parents=True)
    g.write_text(SLIDE)
    assert not tla.check_template_dispatch(g, SKILL)["checked"]


def test_parse_template_next_keeps_hard_pages_and_final_delivery_with_main(tmp_path):
    work = tmp_path / ".lark-slides" / "template" / "t1"
    hint = pt._next_step_hint(work)
    assert "page-plan.md" in hint and "template_publish.py" in hint and "--who solo" in hint
    assert "困难页" in hint and "MainAgent" in hint
    assert "dispatch" not in hint and "Organizer" not in hint


def test_placeholder_boilerplate_text_is_an_error(tmp_path):
    def page(text):
        f = tmp_path / "p.xml"
        f.write_text(SLIDE.replace("<p>标题</p>", f"<p>{text}</p>"))
        return tla.check_placeholder_text(f)
    for t in ("Click to add text", "单击此处添加标题", "点击添加文本", "Lorem ipsum dolor sit amet", "请输入标题",
              "Your text here", "添加标题"):
        assert page(t)["fail_count"] == 1, t
    for t in ("2024 年营收增长 32%", "点击率提升 12%", "添加标题后可排序的列表", "Address title risks"):
        assert page(t)["fail_count"] == 0, t


def test_parse_template_skips_zip_directory_entries(tmp_path):
    import zipfile
    p = tmp_path / "t.pptx"
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("ppt/media/", "")
        z.writestr("ppt/media/image1.png", b"png")
        z.writestr("ppt/theme/", "")
    out = pt._extract_images(p, tmp_path / "assets")
    assert [m["filename"] for m in out] == ["image1.png"]
