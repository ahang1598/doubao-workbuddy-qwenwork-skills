"""
Chrome/Chromium 查找与下载。

提供 Chrome/Chromium 可执行文件的查找、检查、下载功能。

查找策略（按优先级）：
1. 从 workspace/.bin 中查找已下载的 Chromium
2. 从 skill_context 中查找（chrome_path 路径）
3. 从用户系统中查找（环境变量 → which → 平台默认路径）
"""

import json
import os
import platform
import shutil
import sys
from pathlib import Path

from utils.download_utils import download_and_extract
from commands.skill_context import get_skill_context

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

_CHROME_FOR_TESTING_DOWNLOAD_HOST = "https://cdn.npmmirror.com/binaries/chrome-for-testing"

_SYSTEM_CHROME_PATHS: dict[str, list[str]] = {
    "Darwin": [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
    ],
    "Linux": [
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/snap/bin/chromium",
    ],
    "Windows": [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ],
}

# ---------------------------------------------------------------------------
# 查找：从 skill_context 中查找
# ---------------------------------------------------------------------------


def _find_chrome_from_skill_context(skill_context: dict) -> str | None:
    """从 skill_context 的 chrome_path 字段获取 Chrome 路径。"""
    chrome_path = skill_context.get("chrome_path") or skill_context.get("playwright_chrome")
    if chrome_path and os.path.isfile(chrome_path):
        return chrome_path
    return None


# ---------------------------------------------------------------------------
# 查找：从用户系统中查找
# ---------------------------------------------------------------------------


def _find_chrome_from_system() -> str | None:
    """从用户系统中查找 Chrome/Chromium 可执行文件。

    查找顺序：CHROME_BIN 环境变量 → which → 平台默认路径。
    """
    env_path = os.getenv("CHROME_BIN")
    if env_path and os.path.isfile(env_path):
        return env_path

    for binary_name in ("google-chrome", "chromium", "chrome", "chrome.exe"):
        found = shutil.which(binary_name)
        if found:
            return found

    system_name = platform.system()

    if system_name == "Windows":
        windows_search_bases = [
            r"C:\Program Files",
            r"C:\Program Files (x86)",
        ]
        for env_var in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
            base = os.environ.get(env_var, "")
            if base and base not in windows_search_bases:
                windows_search_bases.append(base)

        for base in windows_search_bases:
            candidate = os.path.join(base, "Google", "Chrome", "Application", "chrome.exe")
            if os.path.isfile(candidate):
                return candidate

    for path in _SYSTEM_CHROME_PATHS.get(system_name, []):
        if os.path.isfile(path):
            return path

    chrome_from_apps = _find_chrome_from_applications_dir()
    if chrome_from_apps:
        return chrome_from_apps

    return None


def _find_chrome_from_applications_dir() -> str | None:
    """从对应平台的应用程序目录中递归查找 Chrome/Chromium 可执行文件。"""
    system_name = platform.system()

    if system_name == "Darwin":
        search_dirs = [
            Path("/Applications"),
            Path.home() / "Applications",
        ]
        target_binaries = ["Google Chrome", "Chromium", "chrome", "chromium"]
    elif system_name == "Linux":
        search_dirs = [
            Path("/opt"),
            Path("/usr/local/bin"),
            Path("/usr/local/share"),
            Path.home() / ".local" / "bin",
            Path("/snap"),
        ]
        target_binaries = ["google-chrome", "google-chrome-stable", "chrome", "chromium", "chromium-browser"]
    elif system_name == "Windows":
        search_dirs = [
            Path(r"C:\Program Files"),
            Path(r"C:\Program Files (x86)"),
        ]
        for env_var in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
            base = os.environ.get(env_var, "")
            if base:
                candidate_dir = Path(base)
                if candidate_dir not in search_dirs:
                    search_dirs.append(candidate_dir)
        target_binaries = ["chrome.exe", "chromium.exe"]
    else:
        return None

    max_depth = 5

    for search_dir in search_dirs:
        if not search_dir.is_dir():
            continue
        result = _walk_find_binary(search_dir, target_binaries, max_depth)
        if result:
            return result

    return None


def _walk_find_binary(root: Path, target_names: list[str], max_depth: int) -> str | None:
    """在目录中按深度限制查找目标可执行文件。"""
    if max_depth < 0:
        return None

    try:
        entries = sorted(root.iterdir())
    except PermissionError:
        return None

    for entry in entries:
        if entry.is_file() and entry.name in target_names and os.access(str(entry), os.X_OK):
            return str(entry)

    for entry in entries:
        if entry.is_dir() and not entry.is_symlink():
            result = _walk_find_binary(entry, target_names, max_depth - 1)
            if result:
                return result

    return None


# ---------------------------------------------------------------------------
# 查找：从已下载的 .bin 目录中查找 Chromium
# ---------------------------------------------------------------------------


def _find_chrome_in_bin_dir(bin_dir: Path) -> str | None:
    """在指定 .bin 目录下递归查找已下载的 Chromium 可执行文件（限制深度）。"""
    if not bin_dir.is_dir():
        return None

    system_name = platform.system()

    if system_name == "Darwin":
        target_binaries = ["Chromium", "Google Chrome", "chromium"]
    elif system_name == "Linux":
        target_binaries = ["chrome", "chromium"]
    else:
        return None

    max_depth = 5
    return _walk_find_binary(bin_dir, target_binaries, max_depth)


# ---------------------------------------------------------------------------
# workspace/.bin 目录
# ---------------------------------------------------------------------------


def _get_workspace_bin_dir(skill_context: dict) -> Path:
    """获取 workspace/.bin 目录路径（内部使用，公开版本见 utils.envs）。"""
    workspace_dir = skill_context.get("workspace_dir")
    if workspace_dir:
        return Path(workspace_dir) / ".bin"

    agent_work_root = skill_context.get("agent_work_root")
    if agent_work_root:
        return Path(agent_work_root) / "workspace" / ".bin"

    raise EnvironmentError("无法确定 workspace 目录：AGENT_WORK_ROOT 未设置")

# ---------------------------------------------------------------------------
# 下载：通过 URL 下载 Chromium
# ---------------------------------------------------------------------------

def _get_chromium_download_url(skill_context: dict) -> str | None:
    """从 resource_manifest.json 获取 Chromium 下载地址，找不到则返回 None。"""
    agent_work_root = skill_context.get("agent_work_root")
    if not agent_work_root:
        print("⚠️  AGENT_WORK_ROOT 未设置，使用 fallback 下载地址", file=sys.stderr)
        return None

    manifest_path = Path(agent_work_root).resolve().parent.parent / ".bin" / "resource_manifest.json"

    if not manifest_path.is_file():
        print(f"⚠️  resource_manifest.json 不存在 ({manifest_path})，使用 fallback 下载地址", file=sys.stderr)
        return None

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        chromium_config = manifest.get("artifacts", {}).get("chromium", {})
        url = chromium_config.get("url")
        if url:
            return url
    except (json.JSONDecodeError, OSError) as error:
        print(f"⚠️  读取 resource_manifest.json 失败: {error}，使用 fallback 下载地址", file=sys.stderr)

    return None


def _download_chromium_from_url(skill_context: dict) -> str | None:
    """通过下载地址下载并解压 Chromium 到 workspace/.bin 目录。"""
    download_url = _get_chromium_download_url(skill_context)

    if not download_url:
        print("⚠️  未获取到 Chromium 下载地址，跳过直接下载", file=sys.stderr)
        return None

    bin_dir = _get_workspace_bin_dir(skill_context)
    chromium_dir = bin_dir / "chromium"
    chromium_dir.mkdir(parents=True, exist_ok=True)

    print("📥 从 URL 下载 Chromium...")
    print(f"   下载地址: {download_url}")
    print(f"   安装目录: {chromium_dir}")

    try:
        download_and_extract(download_url, chromium_dir)
        print(f"✅ 下载并解压完成: {chromium_dir}")
    except Exception as error:
        print(f"❌ 下载或解压 Chromium 失败: {error}", file=sys.stderr)
        return None

    chrome_path = _find_chrome_in_bin_dir(chromium_dir)
    if chrome_path:
        os.chmod(chrome_path, 0o755)
        print(f"✅ Chromium 已就绪: {chrome_path}")
        return chrome_path

    print("❌ 解压完成，但未找到 Chromium 可执行文件", file=sys.stderr)
    return None


# ---------------------------------------------------------------------------
# 公开 API
# ---------------------------------------------------------------------------


def check_chrome() -> str | None:
    """仅检查是否有可用的 Chrome（不触发下载），返回路径或 None。"""
    skill_context = get_skill_context()

    print("🔍 [1/3] 从 workspace/.bin 中查找已下载的 Chromium...")
    try:
        bin_dir = _get_workspace_bin_dir(skill_context)
        chrome_path = _find_chrome_in_bin_dir(bin_dir)
        if chrome_path:
            print(f"✅ 找到 Chromium (workspace/.bin): {chrome_path}")
            return chrome_path
    except EnvironmentError:
        pass

    print("🔍 [2/3] 从 skill_context 中查找 Chrome...")
    chrome_path = _find_chrome_from_skill_context(skill_context)
    if chrome_path:
        print(f"✅ 找到 Chrome (skill_context): {chrome_path}")
        return chrome_path

    print("🔍 [3/3] 从用户系统中查找 Chrome...")
    chrome_path = _find_chrome_from_system()
    if chrome_path:
        print(f"✅ 找到 Chrome (系统): {chrome_path}")
        return chrome_path

    print("❌ 未找到可用的 Chrome/Chromium")
    return None


def download_chrome() -> str | None:
    """下载 Chromium：从 URL 直接下载。"""
    skill_context = get_skill_context()

    print("📥 尝试从 URL 直接下载 Chromium...")
    try:
        chrome_path = _download_chromium_from_url(skill_context)
        if chrome_path:
            return chrome_path
    except EnvironmentError as error:
        print(f"⚠️  直接下载失败: {error}", file=sys.stderr)

    print("❌ 安装 Chromium 失败", file=sys.stderr)
    return None


def ensure_chrome() -> str | None:
    """确保有可用的 Chrome/Chromium：先检查，找不到则自动下载。"""
    chrome_path = check_chrome()
    if chrome_path:
        return chrome_path

    print("📥 本地未找到，开始下载 Chromium...")
    return download_chrome()
