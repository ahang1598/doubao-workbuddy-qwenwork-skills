#!/usr/bin/env python3
"""CDP 降级提取脚本 - browser_use 失败时的备选方案。

使用 Selenium + 反检测参数启动 Chrome 浏览器，绕过反爬机制，
获取视频/笔记元数据和直链，输出 JSON 供 cli.py 后续处理。

支持平台: 抖音、B站、小红书
兼容系统: macOS (Intel/ARM)、Windows、Linux

用法:
    python3 scripts/cdp_extract.py --url "https://v.douyin.com/xxx"
    python3 scripts/cdp_extract.py --url "https://www.bilibili.com/video/BVxxx"
    python3 scripts/cdp_extract.py --url "https://www.xiaohongshu.com/explore/xxx"
    python3 scripts/cdp_extract.py --url "https://www.douyin.com" --check-only

依赖:
    pip install chromedriver-autoinstaller selenium
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

_CHROME_PROFILE_DIR = str(Path.home() / ".content-breakdown" / "chrome-profile-uc")


# ============================================================
# Browser Creation (cross-platform, auto ChromeDriver management)
# ============================================================

def _codesign_if_needed(binary_path: str):
    """macOS: 对未签名的二进制进行本地 ad-hoc 签名以绕过 Gatekeeper"""
    import platform as _platform
    import subprocess as _subprocess

    if _platform.system() != "Darwin":
        return

    try:
        # 先清除隔离属性
        _subprocess.run(["xattr", "-cr", binary_path], stderr=_subprocess.DEVNULL)
        # ad-hoc 签名(不需要 Apple 开发者账号, 不需要 sudo)
        _subprocess.run(
            ["codesign", "--force", "--sign", "-", binary_path],
            stderr=_subprocess.DEVNULL,
            check=True,
        )
    except (FileNotFoundError, _subprocess.CalledProcessError):
        pass  # Windows/Linux 或 codesign 不可用时跳过




def _connect_debug_chrome(port: int = 9222):
    """连接到已以 --remote-debugging-port 启动的 Chrome 实例。

    这是最稳定的方式：不需要新启动 Chrome，直接复用用户已有的浏览器（含登录态）。
    用户需要先以 debug 模式启动 Chrome：
        /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222

    Returns:
        WebDriver 实例，或 None（如果端口不可用）。
    """
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options

    try:
        # 先检测端口是否可用
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(("127.0.0.1", port))
        sock.close()
        if result != 0:
            return None  # 端口不可用

        options = Options()
        options.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(60)
        return driver
    except Exception:
        return None



def _launch_debug_chrome(port=9222, headless=False):
    """自动启动带 --remote-debugging-port 的 Chrome 进程，等待端口就绪。"""
    import socket, subprocess, platform as _platform

    def port_open():
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        r = s.connect_ex(("127.0.0.1", port))
        s.close()
        return r == 0

    if port_open():
        return

    system = _platform.system()
    if system == "Darwin":
        chrome_paths = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]
    elif system == "Windows":
        chrome_paths = [r"C:\Program Files\Google\Chrome\Application\chrome.exe"]
    else:
        chrome_paths = ["/usr/bin/google-chrome", "/usr/bin/chromium-browser"]

    chrome_bin = None
    for p in chrome_paths:
        if Path(p).exists():
            chrome_bin = p
            break
    if not chrome_bin:
        print("[cdp_extract] Chrome not found", file=sys.stderr)
        return

    if headless:
        # headless 用临时 profile，避免和日常 Chrome 冲突
        import tempfile
        user_data_dir = tempfile.mkdtemp(prefix="cdp-debug-headless-")
    else:
        # 有头模式用持久 profile（保留登录态）
        user_data_dir = _CHROME_PROFILE_DIR
        profile_dir = Path(user_data_dir)
        profile_dir.mkdir(parents=True, exist_ok=True)
        lock_file = profile_dir / "SingletonLock"
        if lock_file.exists() or lock_file.is_symlink():
            try:
                lock_file.unlink()
            except OSError:
                pass

    cmd = [chrome_bin, f"--remote-debugging-port={port}", f"--user-data-dir={user_data_dir}",
           "--no-first-run", "--no-default-browser-check", "--disable-extensions",
           "--disable-sync", "--disable-translate", "--disable-background-networking"]
    if headless:
        cmd.append("--headless=new")

    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"[cdp_extract] Chrome launched (port {port}), waiting...", file=sys.stderr)

    for _ in range(30):
        time.sleep(0.5)
        if port_open():
            print(f"[cdp_extract] Chrome port {port} ready", file=sys.stderr)
            return
    print(f"[cdp_extract] WARNING: Chrome launch timeout", file=sys.stderr)


def _create_browser(headless: bool = False):
    """创建 Chrome 浏览器实例（原生 Selenium + 反检测参数）。

    使用原生 Selenium + excludeSwitches + CDP 注入反检测脚本（不 patch Chrome 二进制）。

    ChromeDriver 版本管理:
    - chromedriver-autoinstaller 自动检测 Chrome 版本并下载匹配的 ChromeDriver
    - macOS 上自动 codesign 解决 Gatekeeper 拦截
    - 支持 Mac(Intel/ARM)、Windows、Linux
    """
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    import chromedriver_autoinstaller

    # 确保有正确版本的 ChromeDriver
    chromedriver_path = chromedriver_autoinstaller.install()

    # macOS: 签名以防 Gatekeeper 拦截(-9 SIGKILL)
    _codesign_if_needed(chromedriver_path)

    options = Options()

    if headless:
        # headless 模式使用临时 profile，避免与正在运行的 Chrome 冲突
        import tempfile
        tmp_profile = tempfile.mkdtemp(prefix="cdp-headless-")
        options.add_argument(f"--user-data-dir={tmp_profile}")
    else:
        # 有头模式使用持久化 profile（保留登录态）
        profile_dir = Path(_CHROME_PROFILE_DIR)
        profile_dir.mkdir(parents=True, exist_ok=True)
        lock_file = profile_dir / "SingletonLock"
        if lock_file.exists() or lock_file.is_symlink():
            try:
                lock_file.unlink()
            except OSError:
                pass
        options.add_argument(f"--user-data-dir={_CHROME_PROFILE_DIR}")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=zh-CN")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-default-apps")
    options.add_argument("--disable-sync")
    options.add_argument("--disable-translate")
    options.add_argument("--no-first-run")
    # 关键：移除自动化标记
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    if headless:
        options.add_argument("--headless=new")

    max_attempts = 2
    last_error = None

    for attempt in range(max_attempts):
        try:
            service = Service(executable_path=chromedriver_path)
            driver = webdriver.Chrome(service=service, options=options)
            driver.set_page_load_timeout(60)

            # CDP 注入反检测脚本（隐藏 webdriver 标记）
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    window.chrome = window.chrome || {};
                    window.chrome.runtime = window.chrome.runtime || {};
                    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                    Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
                """
            })

            return driver
        except Exception as browser_err:
            last_error = browser_err
            error_msg = str(browser_err)
            if ("unexpectedly exited" in error_msg or "Status code was: -9" in error_msg) and attempt == 0:
                import platform as _plat
                import subprocess as _sp
                if _plat.system() == "Darwin":
                    print(f"[cdp_extract] ChromeDriver blocked by macOS Gatekeeper, auto-fixing...", file=sys.stderr)
                    try:
                        _sp.run(["xattr", "-cr", chromedriver_path], stderr=_sp.DEVNULL)
                        _sp.run(["codesign", "--force", "--sign", "-", chromedriver_path],
                                capture_output=True, text=True)
                        import os
                        os.chmod(chromedriver_path, 0o755)
                        print(f"[cdp_extract] ChromeDriver signed, retrying...", file=sys.stderr)
                        continue
                    except Exception as fix_err:
                        print(f"[cdp_extract] Auto-fix failed: {fix_err}", file=sys.stderr)
            break

    # 所有尝试失败
    error_msg = str(last_error)
    if "unexpectedly exited" in error_msg or "Status code was: -9" in error_msg:
        import platform as _plat
        if _plat.system() == "Darwin":
            fix_cmd = f"codesign --force --sign - '{chromedriver_path}'"
            print(json.dumps({
                "success": False,
                "error": "chromedriver_blocked",
                "message": f"ChromeDriver was blocked by macOS security. Auto-fix failed. Please run manually:\n\n  {fix_cmd}\n\nThen retry.",
                "fix_command": fix_cmd
            }))
            sys.exit(1)
    raise last_error

# ============================================================
# Platform Detection
# ============================================================

def _detect_platform(url: str) -> str:
    """从 URL 识别平台"""
    if "douyin.com" in url:
        return "douyin"
    if "bilibili.com" in url or "b23.tv" in url:
        return "bilibili"
    if "xiaohongshu.com" in url or "xhslink.com" in url:
        return "xiaohongshu"
    if "baijiahao.baidu.com" in url or "mbd.baidu.com" in url:
        return "baijiahao"
    if "weibo.com" in url or "weibo.cn" in url:
        return "weibo"
    if "toutiao.com" in url:
        return "toutiao"
    return "unknown"


# ============================================================
# Login Status Check
# ============================================================

def _check_douyin_login(driver) -> bool:
    cookies = driver.get_cookies()
    cookie_names = [c["name"] for c in cookies]
    return "sessionid" in cookie_names or "sid_tt" in cookie_names


def _check_bilibili_login(driver) -> bool:
    cookies = driver.get_cookies()
    cookie_names = [c["name"] for c in cookies]
    return "SESSDATA" in cookie_names


def _check_xhs_login(driver) -> bool:
    cookies = driver.get_cookies()
    cookie_names = [c["name"] for c in cookies]
    return "web_session" in cookie_names


_LOGIN_CHECK_FNS = {
    "douyin": _check_douyin_login,
    "bilibili": _check_bilibili_login,
    "xiaohongshu": _check_xhs_login,
}

_PLATFORM_HOME_URLS = {
    "douyin": "https://www.douyin.com",
    "bilibili": "https://www.bilibili.com",
    "xiaohongshu": "https://www.xiaohongshu.com",
}


# ============================================================
# Douyin Extractor
# ============================================================

def _extract_douyin(driver, url: str) -> dict:
    """从抖音页面提取视频数据"""
    result = {
        "success": False,
        "platform": "douyin",
        "play_url": None,
        "audio_url": None,
        "metadata": {},
        "subtitle_infos": [],
        "login_status": "unknown",
        "data_completeness": "none",
        "error": None,
    }

    try:
        driver.get(url)
        time.sleep(6)

        # 模拟用户行为
        driver.execute_script("window.scrollBy(0, 300)")
        time.sleep(1)
        driver.execute_script("window.scrollBy(0, -100)")
        time.sleep(2)

        # 检查登录状态
        logged_in = _check_douyin_login(driver)
        result["login_status"] = "logged_in" if logged_in else "not_logged_in"

        # === 方式一: 从 RENDER_DATA 提取(最完整) ===
        render_data = driver.execute_script("""
        try {
            const rd = window.RENDER_DATA || window.__RENDER_DATA__;
            if (!rd) return null;
            const keys = Object.keys(rd);
            for (const k of keys) {
                let val = rd[k];
                if (typeof val === 'string') {
                    try { val = JSON.parse(decodeURIComponent(val)); } catch(e) { continue; }
                }
                if (val && (val.awemeDetail || val.aweme)) {
                    const d = val.awemeDetail || val.aweme;
                    return {
                        title: d.desc || '',
                        author: d.author ? d.author.nickname : '',
                        uid: d.author ? d.author.uid : '',
                        play_url: d.video && d.video.play_addr ? d.video.play_addr.url_list[0] : null,
                        download_url: d.video && d.video.download_addr ? d.video.download_addr.url_list[0] : null,
                        duration: d.video ? d.video.duration : 0,
                        subtitle_infos: d.video ? (d.video.subtitle_infos || []) : [],
                        statistics: d.statistics || {},
                        video_id: d.aweme_id || ''
                    };
                }
            }
            return null;
        } catch(e) {
            return {error: e.message};
        }
        """)

        if render_data and not render_data.get("error"):
            result["success"] = True
            result["play_url"] = render_data.get("play_url") or render_data.get("download_url")
            result["metadata"] = {
                "title": render_data.get("title", ""),
                "author": render_data.get("author", ""),
                "uid": render_data.get("uid", ""),
                "duration": render_data.get("duration", 0),
                "video_id": render_data.get("video_id", ""),
                "statistics": render_data.get("statistics", {}),
            }
            result["subtitle_infos"] = render_data.get("subtitle_infos") or []
            result["data_completeness"] = "full"
            return result

        # === 方式二: 从 Performance API 获取详情 API + CDN 直链 ===
        # 2a: 尝试找到详情 API URL 并用 XHR 重新请求（能拿到完整 play_url）
        detail_data = driver.execute_script("""
        try {
            const entries = performance.getEntriesByType('resource');
            const detailEntry = entries.find(e =>
                e.name.includes('aweme/v1/web/aweme/detail') ||
                e.name.includes('aweme/detail')
            );
            if (!detailEntry) return null;
            const xhr = new XMLHttpRequest();
            xhr.open('GET', detailEntry.name, false);
            xhr.withCredentials = true;
            xhr.send();
            if (xhr.status === 200) {
                const d = JSON.parse(xhr.responseText);
                const detail = d.aweme_detail || (d.aweme_details && d.aweme_details[0]) || d.aweme_list && d.aweme_list[0];
                if (detail) {
                    return {
                        title: detail.desc || '',
                        author: detail.author ? detail.author.nickname : '',
                        play_url: detail.video && detail.video.play_addr ? detail.video.play_addr.url_list[0] : null,
                        download_url: detail.video && detail.video.download_addr ? detail.video.download_addr.url_list[0] : null,
                        duration: detail.video ? detail.video.duration : 0,
                        subtitle_infos: detail.video ? (detail.video.subtitle_infos || []) : [],
                        statistics: detail.statistics || {},
                        video_id: detail.aweme_id || ''
                    };
                }
            }
            return null;
        } catch(e) {
            return null;
        }
        """)

        if detail_data and detail_data.get("play_url"):
            result["success"] = True
            result["play_url"] = detail_data.get("play_url") or detail_data.get("download_url")
            result["metadata"] = {
                "title": detail_data.get("title", ""),
                "author": detail_data.get("author", ""),
                "duration": detail_data.get("duration", 0),
                "video_id": detail_data.get("video_id", ""),
                "statistics": detail_data.get("statistics", {}),
            }
            result["subtitle_infos"] = detail_data.get("subtitle_infos") or []
            result["data_completeness"] = "full"
            return result

        # 2b: 详情 API 不可用，从 CDN 资源中分类提取
        perf_urls = driver.execute_script("""
        return performance.getEntriesByType('resource')
            .filter(e => e.name.includes('douyinvod.com'))
            .map(e => e.name);
        """)

        if not perf_urls:
            time.sleep(5)
            driver.execute_script("window.scrollBy(0, 500)")
            time.sleep(3)
            perf_urls = driver.execute_script("""
            return performance.getEntriesByType('resource')
                .filter(e => e.name.includes('douyinvod.com'))
                .map(e => e.name);
            """)

        if perf_urls:
            audio_urls = [u for u in perf_urls if "media-audio" in u]
            video_urls = [u for u in perf_urls if "media-video" in u]
            merged_urls = [u for u in perf_urls if "media-video" not in u and "media-audio" not in u]

            result["play_url"] = merged_urls[0] if merged_urls else None
            result["audio_url"] = audio_urls[0] if audio_urls else None
            if video_urls:
                result["video_url"] = video_urls[0]  # DASH 视频轨（可配合 audio_url 用 ffmpeg 合并）

            dom_meta = driver.execute_script("""
            return {
                title: document.querySelector('h1')?.textContent ||
                       document.querySelector('[data-e2e="video-desc"]')?.textContent ||
                       document.title || '',
                author: document.querySelector('[data-e2e="video-author-nickname"]')?.textContent ||
                        document.querySelector('.author-card-user-name')?.textContent || ''
            };
            """)

            result["success"] = True
            result["metadata"] = {
                "title": (dom_meta.get("title") or "").strip(),
                "author": (dom_meta.get("author") or "").strip(),
            }
            result["data_completeness"] = "partial"

            if not logged_in:
                result["login_hint"] = "Login recommended for full metadata (statistics, subtitles). Audio URL available for ASR."
            return result

        # 全部失败
        if not logged_in:
            result["error"] = "login_required"
            result["message"] = "Cannot extract video data. Please log in to Douyin in the Chrome window."
        else:
            result["error"] = "extraction_failed"
            result["message"] = "Page loaded but no video data found. The link may be invalid or expired."

    except Exception as extract_error:
        result["error"] = str(extract_error)

    return result


# ============================================================
# Bilibili Extractor
# ============================================================

def _extract_bilibili(driver, url: str) -> dict:
    """从B站页面提取 Cookie 和元数据"""
    result = {
        "success": False,
        "platform": "bilibili",
        "cookie_string": None,
        "bvid": None,
        "metadata": {},
        "login_status": "unknown",
        "data_completeness": "none",
        "error": None,
    }

    try:
        driver.get(url)
        time.sleep(5)

        logged_in = _check_bilibili_login(driver)
        result["login_status"] = "logged_in" if logged_in else "not_logged_in"

        # 获取 Cookie
        cookies = driver.get_cookies()
        cookie_parts = []
        for cookie in cookies:
            if cookie.get("domain", "").endswith("bilibili.com"):
                cookie_parts.append(f"{cookie['name']}={cookie['value']}")

        if cookie_parts:
            result["cookie_string"] = "; ".join(cookie_parts)

        # 提取 BV 号
        current_url = driver.current_url
        bv_match = re.search(r"(BV[\w]+)", current_url)
        if bv_match:
            result["bvid"] = bv_match.group(1)

        # 获取页面元数据
        dom_meta = driver.execute_script("""
        return {
            title: document.querySelector('h1.video-title')?.textContent ||
                   document.querySelector('.video-title')?.getAttribute('title') ||
                   document.title || '',
            author: document.querySelector('.up-name')?.textContent ||
                    document.querySelector('[class*="username"]')?.textContent || '',
            desc: document.querySelector('.basic-desc-info')?.textContent || ''
        };
        """)

        result["metadata"] = {
            "title": (dom_meta.get("title") or "").strip(),
            "author": (dom_meta.get("author") or "").strip(),
            "description": (dom_meta.get("desc") or "").strip(),
        }

        if logged_in and result["cookie_string"]:
            result["success"] = True
            result["data_completeness"] = "full"
        elif result["cookie_string"]:
            result["success"] = True
            result["data_completeness"] = "partial"
            result["login_hint"] = "Login required for subtitle download via API."
        else:
            result["error"] = "login_required"
            result["message"] = "No valid cookies. Please log in to Bilibili in the Chrome window."

    except Exception as extract_error:
        result["error"] = str(extract_error)

    return result


# ============================================================
# Xiaohongshu Extractor
# ============================================================

def _extract_xiaohongshu(driver, url: str) -> dict:
    """从小红书页面提取笔记数据"""
    result = {
        "success": False,
        "platform": "xiaohongshu",
        "metadata": {},
        "content": {},
        "login_status": "unknown",
        "data_completeness": "none",
        "error": None,
    }

    try:
        driver.get(url)
        time.sleep(5)

        logged_in = _check_xhs_login(driver)
        result["login_status"] = "logged_in" if logged_in else "not_logged_in"

        # 检查登录墙（多种判断方式）
        current_url = driver.current_url or ""
        page_title = driver.title or ""
        is_login_wall = (
            "/login" in current_url
            or "登录" in page_title
            or ("小红书" in page_title and "explore" not in current_url and "discovery" not in current_url)
        )
        if is_login_wall:
            result["error"] = "login_required"
            result["login_status"] = "not_logged_in"
            result["message"] = "Xiaohongshu login wall detected. Please log in."
            return result

        # 从 __INITIAL_STATE__ 提取
        note_data = driver.execute_script("""
        try {
            const state = window.__INITIAL_STATE__;
            if (state && state.note && state.note.noteDetailMap) {
                const noteMap = state.note.noteDetailMap;
                const noteId = Object.keys(noteMap)[0];
                if (noteId) {
                    const detail = noteMap[noteId].note;
                    return {
                        title: detail.title || '',
                        desc: detail.desc || '',
                        author: detail.user ? detail.user.nickname : '',
                        type: detail.type || '',
                        image_list: (detail.imageList || []).map(img => img.urlDefault || img.url || ''),
                        video_url: detail.video ? (detail.video.media ? detail.video.media.stream.h264[0].masterUrl : '') : '',
                        liked_count: detail.interactInfo ? detail.interactInfo.likedCount : '',
                        collected_count: detail.interactInfo ? detail.interactInfo.collectedCount : '',
                        comment_count: detail.interactInfo ? detail.interactInfo.commentCount : '',
                        share_count: detail.interactInfo ? detail.interactInfo.shareCount : '',
                        tags: (detail.tagList || []).map(t => t.name),
                        note_id: noteId
                    };
                }
            }
            return null;
        } catch(e) {
            return {error: e.message};
        }
        """)

        if note_data and not note_data.get("error"):
            result["success"] = True
            result["metadata"] = {
                "title": note_data.get("title", ""),
                "author": note_data.get("author", ""),
                "type": note_data.get("type", ""),
                "note_id": note_data.get("note_id", ""),
                "statistics": {
                    "liked_count": note_data.get("liked_count", ""),
                    "collected_count": note_data.get("collected_count", ""),
                    "comment_count": note_data.get("comment_count", ""),
                    "share_count": note_data.get("share_count", ""),
                },
                "tags": note_data.get("tags", []),
            }
            result["content"] = {
                "desc": note_data.get("desc", ""),
                "image_list": note_data.get("image_list", []),
                "video_url": note_data.get("video_url", ""),
            }
            result["data_completeness"] = "full"
            return result

        # Fallback: DOM 提取
        dom_data = driver.execute_script("""
        return {
            title: document.querySelector('#detail-title')?.textContent ||
                   document.querySelector('.title')?.textContent || '',
            desc: document.querySelector('#detail-desc')?.textContent ||
                  document.querySelector('.desc')?.textContent || '',
            author: document.querySelector('.username')?.textContent ||
                    document.querySelector('[class*="author"]')?.textContent || '',
            images: Array.from(document.querySelectorAll('.swiper-slide img, .note-image img'))
                        .map(img => img.src || img.getAttribute('data-src') || '')
                        .filter(Boolean)
        };
        """)

        if dom_data and (dom_data.get("title") or dom_data.get("desc")):
            result["success"] = True
            result["metadata"] = {
                "title": (dom_data.get("title") or "").strip(),
                "author": (dom_data.get("author") or "").strip(),
            }
            result["content"] = {
                "desc": (dom_data.get("desc") or "").strip(),
                "image_list": dom_data.get("images", []),
            }
            result["data_completeness"] = "partial"
            if not logged_in:
                result["login_hint"] = "Login may improve data completeness."
            return result

        # 全部失败
        if not logged_in:
            result["error"] = "login_required"
            result["message"] = "Cannot extract note. Please log in to Xiaohongshu."
        else:
            result["error"] = "extraction_failed"
            result["message"] = "Page loaded but no note data found."

    except Exception as extract_error:
        result["error"] = str(extract_error)

    return result


# ============================================================
# Article HTML Extractors (Baijiahao / Weibo / Toutiao)
# ============================================================

def _extract_article_html(driver, url: str, platform: str, wait_seconds: int = 5) -> dict:
    """通用的文章页面 HTML 提取（百家号/微博/头条共用）。

    打开页面 → 等待渲染 → 滚动触发懒加载 → 返回完整 page_source。
    """
    result = {"success": False, "platform": platform, "page_html": ""}

    try:
        driver.get(url)
        time.sleep(wait_seconds)

        # 滚动触发懒加载
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)

        page_html = driver.page_source or ""
        if len(page_html) < 500:
            result["error"] = "page_too_short"
            result["message"] = f"Page HTML too short ({len(page_html)} chars), likely blocked."
            return result

        result["success"] = True
        result["page_html"] = page_html
        result["metadata"] = {
            "title": driver.title or "",
            "url": driver.current_url or url,
            "html_length": len(page_html),
        }
    except Exception as extract_error:
        result["error"] = str(extract_error)

    return result


def _extract_baijiahao(driver, url: str) -> dict:
    """百家号文章提取（等 8 秒，百度安全验证可能需要更长时间）。"""
    return _extract_article_html(driver, url, "baijiahao", wait_seconds=8)


def _extract_weibo(driver, url: str) -> dict:
    """微博内容提取。"""
    return _extract_article_html(driver, url, "weibo", wait_seconds=5)


def _extract_toutiao(driver, url: str) -> dict:
    """头条文章提取 — 使用独立的 headless Chrome。

    头条是纯 CSR（客户端渲染），需要浏览器执行 JS 后才能拿到正文。
    使用独立 headless 实例以避免与有头浏览器冲突。
    传入的 driver 参数不使用（保持接口一致）。
    """
    result = {"success": False, "platform": "toutiao", "page_html": ""}
    headless_driver = None

    try:
        headless_driver = _create_browser(headless=True)
        headless_driver.get(url)

        # 轮询检测正文是否渲染完成（最多等 15 秒）
        for attempt in range(15):
            time.sleep(1)
            has_content = headless_driver.execute_script("""
                return !!(
                    document.querySelector('article') ||
                    document.querySelector('[class*="article"]') ||
                    document.querySelector('[class*="content"] p')
                );
            """)
            if has_content:
                break

        # 额外等待确保懒加载完成
        time.sleep(2)
        headless_driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        headless_driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)

        page_html = headless_driver.execute_script(
            "return document.documentElement.outerHTML;"
        ) or ""

        if len(page_html) < 500:
            result["error"] = "page_too_short"
            result["message"] = f"Page HTML too short ({len(page_html)} chars), likely blocked."
            return result

        result["success"] = True
        result["page_html"] = page_html
        result["metadata"] = {
            "title": headless_driver.title or "",
            "url": headless_driver.current_url or url,
            "html_length": len(page_html),
        }
    except Exception as extract_error:
        result["error"] = str(extract_error)
    finally:
        if headless_driver:
            try:
                headless_driver.quit()
            except Exception:
                pass

    return result


# ============================================================
# Main Entry
# ============================================================

_EXTRACT_FNS = {
    "douyin": _extract_douyin,
    "bilibili": _extract_bilibili,
    "xiaohongshu": _extract_xiaohongshu,
    "baijiahao": _extract_baijiahao,
    "weibo": _extract_weibo,
    "toutiao": _extract_toutiao,
}


def _validate_url(url: str) -> str:
    """校验 URL 仅允许 http/https 协议，防止通过 file:// 等协议读取本地文件。"""
    if not url or not isinstance(url, str):
        raise ValueError("URL 不能为空")
    stripped = url.strip()
    if stripped.startswith(("http://", "https://")):
        return stripped
    # 允许短链接（无协议前缀，如 v.douyin.com/xxx）
    if "://" not in stripped:
        return "https://" + stripped
    raise ValueError(
        f"不支持的 URL 协议，仅允许 http/https：{url}"
    )


def main():
    parser = argparse.ArgumentParser(
        description="CDP fallback extractor - use when browser_use fails"
    )
    parser.add_argument("--url", required=True, help="Content URL")
    parser.add_argument("--platform", help="Platform (auto-detected if omitted)")
    parser.add_argument("--check-only", action="store_true", help="Only check login status")
    parser.add_argument("--wait-login", action="store_true",
                        help="If not logged in, keep Chrome open for user to login, then retry")
    args = parser.parse_args()

    # 校验 URL 安全性（仅允许 http/https，防止 file:// 任意文件读取）
    args.url = _validate_url(args.url)

    platform = args.platform or _detect_platform(args.url)
    if platform == "unknown":
        print(json.dumps({"success": False, "error": "unsupported_platform",
                          "message": f"Cannot detect platform from URL: {args.url}"}))
        sys.exit(1)

    # --- 检测依赖 ---
    try:
        import selenium  # noqa: F401
        import chromedriver_autoinstaller  # noqa: F401
    except ImportError as imp_err:
        print(json.dumps({
            "success": False,
            "error": "missing_dependency",
            "message": f"Required package not installed: {imp_err.name}. Run: pip install chromedriver-autoinstaller selenium"
        }))
        sys.exit(1)
    # --- 百家号/微博/头条：自动启动 headless debug Chrome，不需要手动操作 ---
    if platform in ("toutiao", "baijiahao", "weibo") and not args.check_only:
        driver_to_close = None
        try:
            if platform == "toutiao":
                # 头条纯 CSR，用独立 headless
                result = _extract_toutiao(None, args.url)
            else:
                # 百家号/微博：自动启动 headless debug Chrome 并连接
                _launch_debug_chrome(port=9222, headless=True)
                driver = _connect_debug_chrome(9222)
                if driver:
                    print(f"[cdp_extract] 已连接到 debug Chrome (port 9222)", file=sys.stderr)
                else:
                    # 连接失败时 fallback 到 _create_browser headless
                    print(f"[cdp_extract] debug Chrome 连接失败，使用 headless fallback", file=sys.stderr)
                    driver = _create_browser(headless=True)
                driver_to_close = driver
                extract_fn = _EXTRACT_FNS[platform]
                result = extract_fn(driver, args.url)
        except Exception as err:
            result = {"success": False, "platform": platform, "error": str(err)}
        finally:
            if driver_to_close:
                try:
                    driver_to_close.quit()
                except Exception:
                    pass
        print(json.dumps(result, ensure_ascii=False))
        sys.exit(0 if result.get("success") else 1)

    # --- 抖音/B站/小红书：自动启动有头 debug Chrome（需要登录态） ---
    driver = None
    connected_to_debug = False
    try:
        _launch_debug_chrome(port=9222, headless=False)
        driver = _connect_debug_chrome(9222)
        if driver:
            connected_to_debug = True
            print(f"[cdp_extract] 已连接到 debug Chrome (port 9222)", file=sys.stderr)
        else:
            print(f"[cdp_extract] debug Chrome 连接失败，启动独立 Chrome", file=sys.stderr)
            driver = _create_browser()
        # --- check-only 模式 ---
        if args.check_only:
            home_url = _PLATFORM_HOME_URLS.get(platform, "https://www.douyin.com")
            driver.get(home_url)
            time.sleep(5)
            check_fn = _LOGIN_CHECK_FNS[platform]
            logged_in = check_fn(driver)

            if logged_in or not args.wait_login:
                # 已登录 或 不需要等待登录 → 直接返回结果
                print(json.dumps({
                    "success": True,
                    "platform": platform,
                    "logged_in": logged_in,
                }))
                return
            else:
                # 未登录 + --wait-login → 保持浏览器开着等待用户登录
                print(json.dumps({
                    "action": "waiting_for_login",
                    "platform": platform,
                    "logged_in": False,
                    "message": f"Not logged in. Chrome is open at {home_url}. Please log in. Waiting up to 300 seconds..."
                }), flush=True)

                start_time = time.time()
                while time.time() - start_time < 300:
                    time.sleep(5)
                    try:
                        if check_fn(driver):
                            print(json.dumps({
                                "success": True,
                                "platform": platform,
                                "logged_in": True,
                                "message": "Login detected! You can now proceed."
                            }))
                            return
                    except Exception:
                        pass

                # 超时
                print(json.dumps({
                    "success": False,
                    "platform": platform,
                    "logged_in": False,
                    "message": "Login wait timeout (300s). Please retry."
                }))
                return

        # --- 提取前先检测登录状态（抖音/小红书需要登录） ---
        extract_fn = _EXTRACT_FNS[platform]
        check_fn = _LOGIN_CHECK_FNS.get(platform)
        requires_login = platform in ("douyin", "xiaohongshu")

        if requires_login:
            # 先打开目标页面（会自动跳转，比如小红书跳到登录页）
            driver.get(args.url)
            time.sleep(5)
            logged_in = check_fn(driver)

            if not logged_in:
                # 未登录 → 导航到首页，保持浏览器开着等待登录
                home_url = _PLATFORM_HOME_URLS.get(platform, args.url)
                current_url = driver.current_url or ""
                # 如果已经在登录页就不用再跳转
                if "/login" not in current_url:
                    driver.get(home_url)
                    time.sleep(3)

                print(json.dumps({
                    "action": "waiting_for_login",
                    "platform": platform,
                    "logged_in": False,
                    "message": f"Not logged in to {platform}. Chrome is open. Please log in. Waiting up to 300 seconds..."
                }), flush=True)

                start_time = time.time()
                login_success = False
                while time.time() - start_time < 300:
                    time.sleep(5)
                    try:
                        if check_fn(driver):
                            login_success = True
                            break
                    except Exception:
                        pass

                if not login_success:
                    print(json.dumps({
                        "success": False,
                        "platform": platform,
                        "logged_in": False,
                        "error": "login_required",
                        "message": "Login wait timeout (300s). Please retry."
                    }))
                    return

                print(json.dumps({
                    "action": "login_detected",
                    "platform": platform,
                    "message": "Login detected! Extracting data..."
                }), file=sys.stderr)

        # --- 执行提取（已登录或不需要登录的平台） ---
        result = extract_fn(driver, args.url)

        print(json.dumps(result, ensure_ascii=False))

        sys.exit(0 if result.get("success") else 1)
    finally:
        # 只关闭我们自己启动的浏览器，不关闭用户的 debug Chrome
        if driver and not connected_to_debug:
            try:
                driver.quit()
            except Exception:
                pass

if __name__ == "__main__":
    main()
