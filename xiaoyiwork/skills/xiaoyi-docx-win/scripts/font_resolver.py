import os
import platform


def _get_system_font_dirs() -> list:
    """Return list of system font directories for current platform."""
    system = platform.system()
    paths = []

    if system == "Windows":
        paths = [
            os.path.expandvars(r"%WINDIR%\Fonts"),
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Windows\Fonts"),
        ]
    elif system == "Darwin":  # macOS
        paths = [
            os.path.expanduser("~/Library/Fonts"),
            "/System/Library/Fonts",
            "/Library/Fonts",
        ]
    else:  # Linux
        paths = [
            os.path.expanduser("~/.local/share/fonts"),
            "/usr/share/fonts",
            "/usr/local/share/fonts",
        ]

    return [p for p in paths if os.path.exists(p)]


# 鸿蒙黑体 = HarmonyOS Sans SC 的中文字族名。候选只列我们真会装进系统的文件（华为官方原始文件名，
# 随包内置 + 安装器落盘，见 installer/nsis/install-fonts.nsh 与 scripts/pack-fonts.mjs 的 FONT_ASSETS）。
# 不要往这里加我们并不分发的字体名：要么永远匹配不上，要么把不该用的文件选中。
# 顺序即优先级：简中 SC → 繁中 TC。纯拉丁的 HarmonyOS_Sans.ttf 不进候选：它没有中文字形，
# 一旦被选中，中文又会写成方块。
_HARMONY_FONTS = {
    "HarmonyHeiTi": ["HarmonyOS_Sans_SC.ttf", "HarmonyOS_Sans_TC.ttf"],
}


def _index_font_files() -> dict:
    """Map lower-cased file name → full path for every font file in the system font dirs."""
    index = {}
    for font_dir in _get_system_font_dirs():
        for root, _dirs, files in os.walk(font_dir):
            for filename in files:
                ext = os.path.splitext(filename)[1].lower()
                if ext in (".ttf", ".ttc", ".otf"):
                    index.setdefault(filename.lower(), os.path.join(root, filename))
    return index


def _find_font_file(candidates: list) -> str | None:
    """Return the highest-priority candidate that exists in the system font dirs."""
    idx = _index_font_files()
    for candidate in candidates:
        hit = idx.get(candidate.lower())
        if hit:
            return hit
    return None


def resolve_reportlab_fonts(target_name: str = "HarmonyHeiTi") -> dict | None:
    """Find the HarmonyOS Sans file for ReportLab registration.

    Returns {"regular": str, "bold": str, "resolved_name": str} or None.
    """
    candidates = _HARMONY_FONTS.get(target_name)
    if candidates:
        regular_path = _find_font_file(candidates)
        if regular_path:
            # 随包字体是可变字重，系统里没有独立粗体文件 → 粗体复用常规体
            return {"regular": regular_path, "bold": regular_path, "resolved_name": target_name}

    return None


def get_css_font_stack(primary: str = "HarmonyHeiTi") -> str:
    """Return CSS font-family string (Harmony first, then system sans-serif)."""
    fallbacks = [
        primary,
        '"Helvetica Neue"',
        "Helvetica",
        "Arial",
        "sans-serif",
    ]
    return ", ".join(fallbacks)
