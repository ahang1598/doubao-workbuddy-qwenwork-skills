"""fadada-professional-contract-review 生成物路径策略（跨平台）。

历史问题（真机诊断 rpt_20260806T065933Z）：允许目录曾硬编码为云端沙箱的
`/mnt/user-data`、`/tmp`，导致 mac 上写用户工作区直接抛 ValueError、模型转而
`mkdir /mnt` 撞只读文件系统；Windows 上 `/tmp` 与 `/mnt` 均不成立，报告/红线/
清单全链路阻断。现改为运行时解析：

  交付目录 output_root()
      1. 环境变量 RICHEE_OUTPUT_DIR（宿主可注入真实工作区，优先级最高）
      2. /mnt/user-data/outputs —— 仅当该位置可写（云端沙箱）
      3. ~/richeeai/project —— 桌面端默认工作区（Windows 解析为
         %USERPROFILE%\\richeeai\\project）

  中间产物 work_root()
      系统临时目录（mac 为 $TMPDIR 或 /tmp；Windows 为 %TEMP%）

允许写入的位置 = 上述两处 + 本 skill 包内 outputs//evaluation/ +
仍然存在的历史目录（/mnt/user-data、/tmp、/private/tmp），保持向后兼容。
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent

ENV_OUTPUT_DIR = "RICHEE_OUTPUT_DIR"
CLOUD_OUTPUT_DIR = Path("/mnt/user-data/outputs")
DESKTOP_OUTPUT_DIR = Path.home() / "richeeai" / "project"

# 历史允许目录：存在才纳入，避免在 Windows 上引入 C:\tmp 这类伪路径
LEGACY_ROOTS = (Path("/mnt/user-data"), Path("/tmp"), Path("/private/tmp"))


def _writable(path: Path) -> bool:
    """目录可写；目录不存在时向上找到第一个存在的父目录判断可创建性。"""
    probe = path
    while True:
        if probe.is_dir():
            return os.access(probe, os.W_OK)
        parent = probe.parent
        if parent == probe:
            return False
        probe = parent


def _resolve(path: Path) -> Path:
    """尽力 resolve；路径不存在或含无效分量时退回 absolute，不抛错。"""
    candidate = Path(path).expanduser()
    try:
        return candidate.resolve()
    except OSError:
        return candidate.absolute()


def _norm(path: Path) -> str:
    """归一化为可做前缀比较的字符串（Windows 大小写不敏感，且带尾分隔符）。"""
    text = os.path.normcase(str(_resolve(path)))
    return text if text.endswith(os.sep) else text + os.sep


def output_root() -> Path:
    """正式交付目录。"""
    env = os.environ.get(ENV_OUTPUT_DIR, "").strip()
    if env:
        return Path(env).expanduser()
    if _writable(CLOUD_OUTPUT_DIR):
        return CLOUD_OUTPUT_DIR
    return DESKTOP_OUTPUT_DIR


def work_root() -> Path:
    """中间产物目录（extracted.json / operations.json / 构建暂存等）。"""
    return Path(tempfile.gettempdir())


def allowed_roots() -> list[Path]:
    """当前环境下允许写入的根目录，按可读性排序，已去重。"""
    roots = [
        output_root(),
        work_root(),
        SKILL_ROOT / "outputs",
        SKILL_ROOT / "evaluation",
    ]
    roots.extend(root for root in LEGACY_ROOTS if root.is_dir())

    unique: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        key = _norm(root)
        if key not in seen:
            seen.add(key)
            unique.append(root)
    return unique


def generated_path(path: Path, label: str = "output") -> Path:
    """校验并返回生成物的绝对路径；不在允许目录下时抛 ValueError。"""
    resolved = _resolve(Path(path))
    target = _norm(resolved)
    for root in allowed_roots():
        if target.startswith(_norm(root)):
            return resolved
    allowed = "、".join(str(_resolve(root)) for root in allowed_roots())
    raise ValueError(
        f"{label} 必须位于以下目录之一：{allowed}；实际: {resolved}。"
        f"如需交付到其他位置，请设置环境变量 {ENV_OUTPUT_DIR}。"
    )


def ensure_dir(path: Path, label: str = "output directory") -> Path:
    """创建目录并确认可写，失败时抛出带补救建议的异常。"""
    resolved = _resolve(Path(path))
    try:
        resolved.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ValueError(
            f"{label} 无法创建: {resolved}（{exc.strerror or exc}）。"
            f"请改用可写目录，或设置环境变量 {ENV_OUTPUT_DIR} 指向工作区。"
        ) from exc
    if not os.access(resolved, os.W_OK):
        raise ValueError(
            f"{label} 不可写: {resolved}。"
            f"请改用可写目录，或设置环境变量 {ENV_OUTPUT_DIR} 指向工作区。"
        )
    return resolved
