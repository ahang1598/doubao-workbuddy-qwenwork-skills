import platform
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import font_resolver
from font_resolver import _get_system_font_dirs


def test_get_system_font_dirs_returns_existing_paths():
    dirs = _get_system_font_dirs()
    assert isinstance(dirs, list)
    for d in dirs:
        assert os.path.exists(d), f"Font dir should exist: {d}"


def test_get_system_font_dirs_matches_platform():
    dirs = _get_system_font_dirs()
    system = platform.system()
    if system == "Windows":
        assert any("Windows" in d or "Fonts" in d for d in dirs)
    elif system == "Darwin":
        assert any("Library/Fonts" in d for d in dirs)
    else:
        assert any("usr/share/fonts" in d for d in dirs)


from font_resolver import resolve_reportlab_fonts


def test_windows_includes_machine_wide_font_dir():
    """机器级 C:\\Windows\\Fonts 也要搜：安装器把随包字体装在这里（另一处是用户级目录）。"""
    if platform.system() != "Windows":
        return
    assert os.path.expandvars(r"%WINDIR%\Fonts") in _get_system_font_dirs()


def _fake_font_dir(tmp_path, names):
    for name in names:
        (tmp_path / name).write_bytes(b"\x00\x01\x00\x00")
    return str(tmp_path)


def test_resolve_accepts_bundled_official_file_names(monkeypatch, tmp_path):
    """只认随包安装的官方文件名；简中 SC 优先。"""
    monkeypatch.setattr(
        font_resolver,
        "_get_system_font_dirs",
        lambda: [
            _fake_font_dir(
                tmp_path, ["HarmonyOS_Sans.ttf", "HarmonyOS_Sans_TC.ttf", "HarmonyOS_Sans_SC.ttf"]
            )
        ],
    )
    result = resolve_reportlab_fonts("HarmonyHeiTi")
    assert result is not None
    assert result["regular"].endswith("HarmonyOS_Sans_SC.ttf")
    # 随包字体是可变字重，没有独立粗体文件 → 粗体复用常规体
    assert result["bold"].endswith("HarmonyOS_Sans_SC.ttf")
    assert result["resolved_name"] == "HarmonyHeiTi"


def test_resolve_falls_back_to_tc(monkeypatch, tmp_path):
    """没有简中时用繁中，且不能选中纯拉丁的 HarmonyOS_Sans.ttf（否则中文又变方块）。"""
    monkeypatch.setattr(
        font_resolver,
        "_get_system_font_dirs",
        lambda: [_fake_font_dir(tmp_path, ["HarmonyOS_Sans.ttf", "HarmonyOS_Sans_TC.ttf"])],
    )
    result = resolve_reportlab_fonts("HarmonyHeiTi")
    assert result is not None
    assert result["regular"].endswith("HarmonyOS_Sans_TC.ttf")


def test_resolve_returns_none_without_harmony(monkeypatch, tmp_path):
    """目录里没有随包字体就返回 None，交给调用方的兜底逻辑。"""
    monkeypatch.setattr(
        font_resolver,
        "_get_system_font_dirs",
        lambda: [_fake_font_dir(tmp_path, ["arial.ttf"])],
    )
    assert resolve_reportlab_fonts("HarmonyHeiTi") is None


def test_resolve_reportlab_fonts_finds_fallback_on_windows():
    if platform.system() != "Windows":
        return
    result = resolve_reportlab_fonts("HarmonyHeiTi")
    assert result is not None
    assert "regular" in result
    assert "bold" in result
    assert "resolved_name" in result
    assert os.path.exists(result["regular"])
    assert os.path.exists(result["bold"])
    assert result["resolved_name"] == "HarmonyHeiTi"
