"""
统一的路径解析模块 —— RetailAnalysis Home 约定（PDF Runtime 视角）
=================================================================

所有 Skill 共享的「输入 / 输出 / 中间产物 / 日志」统一落到固定的
**Home 目录**；配置由业务 Skill 自带，默认 Home 为：

    ~/RetailAnalysis

可以通过环境变量 ``RETAIL_ANALYSIS_HOME`` 覆盖。
"""

from __future__ import annotations

import os
import pathlib

# ---------------------------------------------------------------------------
# 共享 PDF Runtime 位置解析（同时兼容源码目录与 vendor 注入目录）
# ---------------------------------------------------------------------------

SCRIPT_DIR: pathlib.Path = pathlib.Path(__file__).resolve().parent
RUNTIME_DIR: pathlib.Path = SCRIPT_DIR.parent

# 源码态：
#   .../financial-report-comparison/shared/pdf-report-builder-runtime/scripts/paths.py
# vendor 态：
#   .../<business-skill>/_vendor/pdf_report_builder_runtime/scripts/paths.py
if RUNTIME_DIR.parent.name == "shared":
    RUNTIME_MODE = "source"
    SHARED_ROOT: pathlib.Path = RUNTIME_DIR.parent
    REPO_ROOT: pathlib.Path = SHARED_ROOT.parent
    SKILLS_ROOT: pathlib.Path = REPO_ROOT / "skills"
elif RUNTIME_DIR.parent.name == "_vendor":
    RUNTIME_MODE = "vendored"
    CONSUMER_SKILL_DIR: pathlib.Path = RUNTIME_DIR.parent.parent
    SKILLS_ROOT = CONSUMER_SKILL_DIR.parent
    REPO_ROOT = SKILLS_ROOT.parent
else:
    RUNTIME_MODE = "standalone"
    SKILLS_ROOT = RUNTIME_DIR.parent
    REPO_ROOT = SKILLS_ROOT.parent

_SKILL_DIR_NAMES: dict[str, str] = {
    "skill1": "standard-data-extraction",
    "skill2": "text-data-extraction",
    "skill3": "benchmark-analysis",
    "skill4": "strategic-insight",
    "skill5": "strategy-governance-analysis",
}

# ---------------------------------------------------------------------------
# Home 根目录
# ---------------------------------------------------------------------------

ENV_VAR_NAME = "RETAIL_ANALYSIS_HOME"
DEFAULT_HOME = pathlib.Path.home() / "RetailAnalysis"


def get_home() -> pathlib.Path:
    override = os.environ.get(ENV_VAR_NAME)
    if override:
        return pathlib.Path(override).expanduser().resolve()
    return DEFAULT_HOME


RA_HOME: pathlib.Path = get_home()

# ---------------------------------------------------------------------------
# 二级目录
# ---------------------------------------------------------------------------

DATA_DIR: pathlib.Path = RA_HOME / "data"
OUTPUT_DIR: pathlib.Path = RA_HOME / "output"
LOGS_DIR: pathlib.Path = RA_HOME / "logs"
WORK_DIR: pathlib.Path = RA_HOME / "work"

# ---------------------------------------------------------------------------
# data/ 下的三级目录
# ---------------------------------------------------------------------------

REPORTS_DIR: pathlib.Path = DATA_DIR / "reports"
EXTRACTED_TEXT_DIR: pathlib.Path = DATA_DIR / "extracted_text"
PARTIAL_DIR: pathlib.Path = DATA_DIR / "partial"
STANDARD_DIR: pathlib.Path = DATA_DIR / "standard"
TEXT_DIR: pathlib.Path = DATA_DIR / "text"

# ---------------------------------------------------------------------------
# report_assets（VIS 资产）
# ---------------------------------------------------------------------------

REPORT_ASSETS_DIR: pathlib.Path = RA_HOME / "report_assets"
LOGO_DIR: pathlib.Path = REPORT_ASSETS_DIR / "logo"
VIS_DIR: pathlib.Path = REPORT_ASSETS_DIR / "vis"
ANNUAL_REPORT_DIR: pathlib.Path = REPORT_ASSETS_DIR / "annual_report"

# ---------------------------------------------------------------------------
# PDF Runtime 本地路径
# ---------------------------------------------------------------------------

RUNTIME_ASSETS_DIR: pathlib.Path = RUNTIME_DIR / "assets"
RUNTIME_SCRIPTS_DIR: pathlib.Path = RUNTIME_DIR / "scripts"
RUNTIME_CONFIG_DIR: pathlib.Path = RUNTIME_DIR / "config"

# ---------------------------------------------------------------------------
# 常用文件路径
# ---------------------------------------------------------------------------

STYLE_GUIDE_CSS: pathlib.Path = RUNTIME_ASSETS_DIR / "style_guide.css"
BASE_TEMPLATE_HTML: pathlib.Path = RUNTIME_ASSETS_DIR / "base_template.html"
HEADER_FOOTER_HTML: pathlib.Path = RUNTIME_ASSETS_DIR / "header_footer.html"
P0_CHECKLIST_YAML: pathlib.Path = RUNTIME_CONFIG_DIR / "p0_vis_checklist.yaml"

LOGO_PNG: pathlib.Path = LOGO_DIR / "logo.png"
LOGO_BASE64: pathlib.Path = LOGO_DIR / "logo_base64.txt"
LOGO_SOURCE: pathlib.Path = LOGO_DIR / "logo_source.txt"
PALETTE_JSON: pathlib.Path = VIS_DIR / "palette.json"

# ---------------------------------------------------------------------------
# 初始化辅助
# ---------------------------------------------------------------------------

_REQUIRED_DIRS = (
    DATA_DIR, REPORTS_DIR, EXTRACTED_TEXT_DIR,
    PARTIAL_DIR, STANDARD_DIR, TEXT_DIR, OUTPUT_DIR, LOGS_DIR, WORK_DIR,
    REPORT_ASSETS_DIR, LOGO_DIR, VIS_DIR, ANNUAL_REPORT_DIR,
)


def ensure_dirs() -> None:
    """按需创建所有约定子目录。"""
    for d in _REQUIRED_DIRS:
        d.mkdir(parents=True, exist_ok=True)


def get_skill_dir(skill_name: str) -> pathlib.Path | None:
    """
    返回指定 Skill 的目录。

    - source 模式：返回仓库 `skills/` 下的目录
    - vendored 模式：返回当前安装目录中与业务 Skill 并列的 sibling skill
    """
    dirname = _SKILL_DIR_NAMES.get(skill_name)
    if not dirname:
        return None
    return SKILLS_ROOT / dirname


def get_skill_assets_dir(skill_name: str) -> pathlib.Path | None:
    """返回指定 Skill 的 assets 目录。"""
    skill_dir = get_skill_dir(skill_name)
    return skill_dir / "assets" if skill_dir else None


def describe() -> str:
    """返回当前解析出的 Home 目录结构概要。"""
    lines = [
        f"PDF runtime mode: {RUNTIME_MODE}",
        f"PDF runtime dir : {RUNTIME_DIR}",
        f"RetailAnalysis Home: {RA_HOME}",
        f"  (env {ENV_VAR_NAME}={os.environ.get(ENV_VAR_NAME, '<unset, fallback to default>')})",
        f"  data    : {DATA_DIR}",
        f"  output  : {OUTPUT_DIR}",
        f"  logs    : {LOGS_DIR}",
        f"  work    : {WORK_DIR}",
        f"  report_assets: {REPORT_ASSETS_DIR}",
        f"  config override: {os.environ.get('RETAIL_ANALYSIS_CONFIG_DIR', '<unset>')}",
        "  config priority: override/<skill>/ > consumer skill-local",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Skill 运行日志（2026-04-30 新增）
# ---------------------------------------------------------------------------

def get_skill_log_dir(skill_name: str) -> pathlib.Path:
    """返回 Skill 的运行日志目录：``~/RetailAnalysis/logs/<skill>/``。"""
    log_dir = LOGS_DIR / skill_name
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def get_skill_log_path(skill_name: str, session_id: str, *, suffix: str = ".log") -> pathlib.Path:
    """为某次 Skill 执行生成日志文件路径：``logs/<skill>/<session_id>.log``。"""
    safe = (
        session_id.replace("/", "-").replace("\\", "-").replace(":", "-").replace(" ", "_").strip()
    ) or "unnamed"
    return get_skill_log_dir(skill_name) / f"{safe}{suffix}"


if __name__ == "__main__":
    print(describe())
