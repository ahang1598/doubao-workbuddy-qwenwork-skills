"""
统一的路径解析模块 —— RetailAnalysis Home 约定
================================================

所有 Skill 共享的「配置 / 输入 / 输出 / 中间产物 / 日志」统一落到
固定的 **Home 目录**，默认：

    ~/RetailAnalysis

可以通过环境变量 ``RETAIL_ANALYSIS_HOME`` 覆盖（例如在 CI / 测试环境中）。

目录结构约定（2026-04-30 调整：已取消全局 config/ 兜底）
--------------------------------------------------------

::

    $RETAIL_ANALYSIS_HOME/                  # 默认 ~/RetailAnalysis
    ├── data/                               # 运行时数据
    │   ├── reports/                        # 财报 PDF
    │   ├── extracted_text/                 # 文档解析产物（按银行分目录）
    │   ├── partial/                        # 单次 (bank × period) 抽取
    │   ├── standard/                       # Skill 1 主输出
    │   ├── text/                           # Skill 2 主输出
    │   ├── benchmark_database.json         # Skill 3 历史库
    │   └── insight_result.json             # Skill 4 输出
    ├── output/                             # 最终报告
    ├── logs/                               # Skill 运行日志
    │   └── <skill_name>/                   # 按 Skill 分目录（2026-04-30 新增）
    │       └── <session_id>.log           # 每次运行一个日志文件
    └── work/                               # 临时工作目录（coarse / bundles / extraction）

.. warning::

    配置按“CLI 显式路径 > ``RETAIL_ANALYSIS_CONFIG_DIR/<skill>/`` >
    Skill 本地 ``config/``”解析，不再从 ``~/RetailAnalysis/config/`` 兜底。
    Skill 本地配置由 ``scripts/release.py --sync-paths`` 从
    ``shared/config-sources/`` 生成。

为什么放 Home 目录
------------------

1. **数据与代码解耦**：仓库里只保留 Skill 脚本和 SKILL.md，不再混入 1GB+
   的 PDF 与中间 JSON，clone / push 速度显著提升。
2. **跨 checkout 复用**：多个 worktree / fork 可以共享同一份财报数据库，
   不必每份都下载 PDF 和重跑 LLM。
3. **跨 Skill 协作**：Skill 1~5 共享 Home 下的 ``data/``；配置由各 Skill
   自带副本保证独立运行，通过显式覆盖目录按需统一。

.. note::

    腾讯云 API 密钥 ``.env`` 仍放在
    ``standard-data-extraction/.env``（由 Skill 1 独占使用），
    不迁入 Home 目录。原因：该密钥只被 ``tencent_doc_parser.py`` 使用，
    就近放置便于维护。

使用方式
--------

在 Python 脚本中::

    from paths import RA_HOME, DATA_DIR, PARTIAL_DIR, get_skill_config_file

    metrics_yaml = get_skill_config_file("skill1", "metrics.yaml")   # 只查 skill 本地
    output = PARTIAL_DIR / f"standard_中信_2025年度.json"

在 Shell 中::

    export RETAIL_ANALYSIS_HOME=~/RetailAnalysis   # 可选，默认就是这个
    python scripts/merge_partials.py --kind standard
"""

from __future__ import annotations

import hashlib
import os
import pathlib
from typing import Any, Optional

# ---------------------------------------------------------------------------
# 仓库态 / 独立 Skill 态路径定位
# ---------------------------------------------------------------------------

_SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
_SKILL_DIR_NAMES: dict[str, str] = {
    "cninfo-bank-reports": "cninfo-bank-reports",
    "skill1": "standard-data-extraction",
    "skill2": "text-data-extraction",
    "skill3": "benchmark-analysis",
    "skill4": "strategic-insight",
    "skill5": "strategy-governance-analysis",
}
_SKILL_NAME_BY_DIR = {dirname: key for key, dirname in _SKILL_DIR_NAMES.items()}

# 根 scripts/paths.py：父目录是仓库根；Skill 副本：父目录是 Skill 根。
_candidate_skill_root = _SCRIPT_DIR.parent
if (_candidate_skill_root / "SKILL.md").is_file():
    LOCAL_SKILL_DIR: Optional[pathlib.Path] = _candidate_skill_root
    LOCAL_SKILL_NAME: Optional[str] = _SKILL_NAME_BY_DIR.get(_candidate_skill_root.name)
    _candidate_skills_root = _candidate_skill_root.parent
    REPO_ROOT: pathlib.Path = (
        _candidate_skills_root.parent
        if _candidate_skills_root.name == "skills"
        else _candidate_skills_root
    )
else:
    LOCAL_SKILL_DIR = None
    LOCAL_SKILL_NAME = None
    REPO_ROOT = _SCRIPT_DIR.parent

#: 仓库态可访问全部 Skill；独立发布态至少保证当前 Skill 可访问自身 config/。
SKILL_DIRS: dict[str, pathlib.Path] = {
    key: REPO_ROOT / "skills" / dirname
    for key, dirname in _SKILL_DIR_NAMES.items()
}
if LOCAL_SKILL_DIR is not None and LOCAL_SKILL_NAME is not None:
    SKILL_DIRS[LOCAL_SKILL_NAME] = LOCAL_SKILL_DIR

CONFIG_OVERRIDE_ENV = "RETAIL_ANALYSIS_CONFIG_DIR"

# ---------------------------------------------------------------------------
# Home 根目录
# ---------------------------------------------------------------------------

#: 环境变量名；优先于默认值。
ENV_VAR_NAME = "RETAIL_ANALYSIS_HOME"

#: 默认 Home 目录：用户主目录下的 ``RetailAnalysis/``。
DEFAULT_HOME = pathlib.Path.home() / "RetailAnalysis"


def get_home() -> pathlib.Path:
    """
    返回 RetailAnalysis Home 目录。

    优先使用环境变量 ``RETAIL_ANALYSIS_HOME``，未设置则回退到
    ``~/RetailAnalysis``。不强制要求目录存在（调用方按需 mkdir）。
    """
    override = os.environ.get(ENV_VAR_NAME)
    if override:
        return pathlib.Path(override).expanduser().resolve()
    return DEFAULT_HOME


#: 模块级常量，供其他脚本直接导入。
RA_HOME: pathlib.Path = get_home()

# ---------------------------------------------------------------------------
# 二级目录
# ---------------------------------------------------------------------------

# Home 只存运行数据；配置必须通过 resolve_config_file()/get_skill_config_file() 获取。
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
REPORT_ASSETS_DIR: pathlib.Path = RA_HOME / "report_assets"

# PDF Runtime 相关路径
RUNTIME_MODE: str = "runtime"  # 运行模式：runtime 或 development
RUNTIME_DIR: pathlib.Path = REPO_ROOT / "shared" / "pdf-report-builder-runtime"
SKILLS_ROOT: pathlib.Path = REPO_ROOT / "skills"

# ---------------------------------------------------------------------------
# 初始化辅助
# ---------------------------------------------------------------------------

#: 所有 Skill 期望预先存在的子目录。``ensure_dirs()`` 会按需创建。
#: 注意：CONFIG_DIR 不再在此列表（不再需要全局 config/）
_REQUIRED_DIRS = (
    DATA_DIR,
    REPORTS_DIR,
    EXTRACTED_TEXT_DIR,
    PARTIAL_DIR,
    STANDARD_DIR,
    TEXT_DIR,
    OUTPUT_DIR,
    LOGS_DIR,
    WORK_DIR,
)


def ensure_dirs() -> None:
    """按需创建所有约定子目录。配置目录不再自动创建（使用 skill 本地 config/）。"""
    for d in _REQUIRED_DIRS:
        d.mkdir(parents=True, exist_ok=True)


def _normalize_skill_name(skill_name: str) -> str:
    if skill_name in _SKILL_DIR_NAMES:
        return skill_name
    normalized = _SKILL_NAME_BY_DIR.get(skill_name)
    if normalized:
        return normalized
    raise KeyError(
        f"Unknown skill_name: {skill_name}; expected one of {list(_SKILL_DIR_NAMES)} "
        f"or {list(_SKILL_NAME_BY_DIR)}"
    )


def get_skill_config_dir(skill_name: str) -> pathlib.Path:
    """返回 Skill 自带的 ``config/``；不读取 RetailAnalysis Home。"""
    normalized = _normalize_skill_name(skill_name)
    skill_dir = SKILL_DIRS[normalized]
    local_cfg = skill_dir / "config"
    if not local_cfg.is_dir():
        raise FileNotFoundError(
            f"Skill '{normalized}' 本地 config/ 不存在：{local_cfg}\n"
            "仓库开发态请运行 `python3 scripts/release.py --sync-paths`；"
            "独立安装态请重新安装包含 config/ 的完整 Skill。"
        )
    return local_cfg.resolve()


def resolve_config_file(
    skill_name: str,
    filename: str,
    *,
    explicit_path: Optional[str | pathlib.Path] = None,
) -> tuple[pathlib.Path, str]:
    """按“显式参数 > 环境覆盖 > Skill 自带配置”解析并严格校验配置。"""
    normalized = _normalize_skill_name(skill_name)
    if explicit_path:
        path = pathlib.Path(explicit_path).expanduser().resolve()
        source = "cli-explicit"
    else:
        override_root = os.environ.get(CONFIG_OVERRIDE_ENV)
        if override_root:
            path = (
                pathlib.Path(override_root).expanduser().resolve()
                / normalized
                / filename
            )
            source = "env-override"
        else:
            path = get_skill_config_dir(normalized) / filename
            source = "skill-bundled"

    if not path.is_file():
        raise FileNotFoundError(
            f"配置文件不存在：{path}\n"
            f"配置来源：{source}\n"
            f"优先级：显式参数 > ${CONFIG_OVERRIDE_ENV}/<skill>/<file> > Skill 自带 config/。"
        )
    return path, source


def get_skill_config_file(
    skill_name: str, filename: str, *, fallback_global: bool = False,
) -> pathlib.Path:
    """兼容入口：严格返回环境覆盖或 Skill 本地配置，不再静默回退。"""
    if fallback_global:
        import warnings
        warnings.warn(
            "fallback_global=True 已弃用且不再生效；请使用显式参数或 "
            f"${CONFIG_OVERRIDE_ENV}/<skill>/。",
            DeprecationWarning,
            stacklevel=2,
        )
    return resolve_config_file(skill_name, filename)[0]


def config_file_metadata(path: pathlib.Path, source: str) -> dict[str, Any]:
    """生成可写入 manifest 的配置来源与内容指纹。"""
    resolved = pathlib.Path(path).expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"配置文件不存在：{resolved}")
    return {
        "source": source,
        "path": str(resolved),
        "sha256": hashlib.sha256(resolved.read_bytes()).hexdigest(),
    }


def describe() -> str:
    """返回当前解析出的 Home 目录结构概要，便于脚本自检打印。"""
    lines = [
        f"RetailAnalysis Home: {RA_HOME}",
        f"  (env {ENV_VAR_NAME}={os.environ.get(ENV_VAR_NAME, '<unset, fallback to default>')})",
        f"  data    : {DATA_DIR}",
        f"  output  : {OUTPUT_DIR}",
        f"  logs    : {LOGS_DIR}",
        f"  work    : {WORK_DIR}",
        f"  config override: {os.environ.get(CONFIG_OVERRIDE_ENV, '<unset>')}",
        "  config priority: explicit > override/<skill>/ > skill-local",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Skill 运行日志（2026-04-30 新增）
# ---------------------------------------------------------------------------

def get_skill_log_dir(skill_name: str) -> pathlib.Path:
    """
    返回某个 Skill 的运行日志目录：``~/RetailAnalysis/logs/<skill>/``。

    对未知 skill_name 不做严格限制（便于临时脚本记录），但建议使用 SKILL_DIRS 中的 key。
    """
    log_dir = LOGS_DIR / skill_name
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def get_skill_log_path(
    skill_name: str,
    session_id: str,
    *,
    suffix: str = ".log",
) -> pathlib.Path:
    """
    为某次 Skill 执行生成日志文件路径：``logs/<skill>/<session_id>.log``。

    - ``session_id`` 建议格式：``YYYYMMDD-HHMMSS-<short-title>``（ASCII + 中文均可，
      但会对路径分隔符 / \\ : 做替换）
    - 日志**应在执行过程中实时写入**，记录关键步骤、警告、错误与 traceback，便于后续优化 Skill。
    """
    safe = (
        session_id
        .replace("/", "-")
        .replace("\\", "-")
        .replace(":", "-")
        .replace(" ", "_")
        .strip()
    ) or "unnamed"
    return get_skill_log_dir(skill_name) / f"{safe}{suffix}"


if __name__ == "__main__":
    # 允许直接 `python scripts/paths.py` 检查路径解析
    print(describe())
