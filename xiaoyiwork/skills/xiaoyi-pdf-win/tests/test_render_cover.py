import os
import sys
from pathlib import Path

_root = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(_root, "..", "scripts"))

import render_cover


def test_resolve_chrome_path_uses_first_existing_candidate(monkeypatch, tmp_path):
    missing = tmp_path / "missing-browser"
    browser = tmp_path / "browser.exe"
    browser.write_bytes(b"browser")
    monkeypatch.setattr(
        render_cover,
        "_browser_candidates",
        lambda: [missing, browser],
    )

    assert render_cover.resolve_chrome_path() == str(browser)


def test_resolve_chrome_path_allows_playwright_fallback(monkeypatch, tmp_path):
    monkeypatch.setattr(
        render_cover,
        "_browser_candidates",
        lambda: [tmp_path / "missing-browser"],
    )

    assert render_cover.resolve_chrome_path() is None


def test_browser_candidates_put_chrome_path_first(monkeypatch, tmp_path):
    configured = tmp_path / "custom-browser.exe"
    monkeypatch.setenv("CHROME_PATH", str(configured))

    assert render_cover._browser_candidates()[0] == Path(configured)


class _FakeChromium:
    def __init__(self):
        self.launch_kwargs = None

    def launch(self, **kwargs):
        self.launch_kwargs = kwargs
        return object()


def test_launch_browser_uses_playwright_default_when_system_browser_missing(monkeypatch):
    chromium = _FakeChromium()
    monkeypatch.setattr(render_cover, "resolve_chrome_path", lambda: None)

    render_cover._launch_browser(chromium)

    assert chromium.launch_kwargs == {}


def test_launch_browser_passes_discovered_executable(monkeypatch):
    chromium = _FakeChromium()
    monkeypatch.setattr(
        render_cover,
        "resolve_chrome_path",
        lambda: r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    )

    render_cover._launch_browser(chromium)

    assert chromium.launch_kwargs == {
        "executable_path": r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    }
