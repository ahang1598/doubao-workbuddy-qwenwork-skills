"""输出路径安全校验模块。

防止任意文件写入（path traversal）漏洞：校验 output_dir 不会逃逸到
用户 home 目录或 /tmp 之外的位置。
"""

from __future__ import annotations

from pathlib import Path

# 允许写入的基目录白名单
_ALLOWED_BASE_DIRS = [
    Path.home().resolve(),
    Path("/tmp").resolve(),
]


def safe_output_dir(output_dir: str | Path) -> Path:
    """校验并规范化输出目录路径，防止 path traversal。

    Args:
        output_dir: 用户指定的输出目录路径。

    Returns:
        规范化后的 Path 对象。

    Raises:
        ValueError: 路径包含 '..' 或不在允许的基目录白名单内。
    """
    raw = str(output_dir)

    if ".." in raw.split("/") or ".." in raw.split("\\"):
        raise ValueError(f"输出目录路径不安全，不允许包含 '..'：{raw}")

    resolved = Path(raw).resolve()

    is_allowed = any(
        resolved == base or str(resolved).startswith(str(base) + "/")
        for base in _ALLOWED_BASE_DIRS
    )
    if not is_allowed:
        allowed_list = ", ".join(str(b) for b in _ALLOWED_BASE_DIRS)
        raise ValueError(
            f"输出目录路径不在允许范围内：{resolved}\n"
            f"允许的基目录：{allowed_list}"
        )

    return resolved
