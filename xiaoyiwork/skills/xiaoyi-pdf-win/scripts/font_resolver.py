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
    else:  # Linux
        paths = [
            "/usr/share/fonts",
            os.path.expanduser("~/.local/share/fonts"),
            "/usr/local/share/fonts",
        ]

    return [p for p in paths if os.path.exists(p)]


# 鸿蒙黑体 = HarmonyOS Sans SC 的中文字族名（字体 name 表里同时有 HarmonyOS Sans SC / 鸿蒙黑体）。
# 候选只列我们真会装进系统的文件：小艺Work 随包内置的就是华为官方原始文件名，安装器把它们落到
# C:\Windows\Fonts 与 %LOCALAPPDATA%\Microsoft\Windows\Fonts（见 installer/nsis/install-fonts.nsh
# 与 scripts/pack-fonts.mjs 的 FONT_ASSETS）。不要往这里加我们并不分发的字体名：要么永远匹配不上，
# 要么把不该用的文件选中。
# 顺序即优先级：简中 SC → 繁中 TC，两者都含拉丁字符。纯拉丁的 HarmonyOS_Sans.ttf 不进候选：
# 它没有中文字形，一旦被选中，中文又会写成方块。
_HARMONY_FONTS = {
    "HarmonyHeiTi": ["HarmonyOS_Sans_SC.ttf", "HarmonyOS_Sans_TC.ttf"],
}


def _index_font_files() -> dict:
    """Map lower-cased file name → full path for every file in the system font dirs."""
    index = {}
    for font_dir in _get_system_font_dirs():
        for root, _dirs, files in os.walk(font_dir):
            for filename in files:
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

    固定使用 HarmonyHeiTi（= HarmonyOS Sans SC），不 fallback 到其他 CJK 字体。
    随包字体是可变字重（wght 100-900）的可变字体，系统里没有独立的粗体文件，ReportLab
    也不做字重实例化/合成，故 bold 与 regular 指向同一文件：标题少一层加粗，但中文不变方块。
    """
    candidates = _HARMONY_FONTS.get(target_name)
    if candidates:
        regular_path = _find_font_file(candidates)
        if regular_path:
            return {"regular": regular_path, "bold": regular_path, "resolved_name": target_name}

    return None


def get_css_font_stack(primary: str = "HarmonyHeiTi") -> str:
    """Return CSS font-family string. 强制使用鸿蒙黑体，忽略外部指定的 primary."""
    return "HarmonyHeiTi, sans-serif"
