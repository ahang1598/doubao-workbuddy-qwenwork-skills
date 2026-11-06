#!/usr/bin/env python3
"""Expert Register — jiuwenswarm 专家可发现性确认。

jiuwenswarm 没有 marketplace.json 注册表：LocalDirExpertPackageSource 直接扫描
专家根目录（优先级 JIUWEN_EXPERTS_DIR > JIUWENSWARM_DATA_DIR/agent/workspace/experts
> ~/.jiuwenswarm/agent/workspace/experts，本地源默认启用，仅 JIUWEN_EXPERT_LOCAL_DIRS=0 关闭）。
因此 "注册" 等价于：终检（无 [TODO] 占位符）+ 确认包位于专家根目录 + 提示可发现性。

Usage:
    register_expert.py <expert-dir>

Examples:
    python3 register_expert.py ~/.jiuwenswarm/agent/workspace/experts/my-expert
    python3 register_expert.py ./my-expert
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Windows 默认 GBK 控制台无法编码 emoji，强制 UTF-8 输出
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        pass

script_dir = Path(__file__).parent.resolve()
sys.path.insert(0, str(script_dir))
from validate_expert import validate_expert  # noqa: E402


def get_experts_dir() -> Path:
    """优先级：JIUWEN_EXPERTS_DIR > JIUWENSWARM_DATA_DIR > ~/.jiuwenswarm（与 init_expert 一致）。"""
    override = os.environ.get("JIUWEN_EXPERTS_DIR", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    data_dir = os.environ.get("JIUWENSWARM_DATA_DIR", "").strip()
    if data_dir:
        return (Path(data_dir).expanduser() / "agent" / "workspace" / "experts").resolve()
    return Path.home() / ".jiuwenswarm" / "agent" / "workspace" / "experts"


def check_completeness(expert_dir: Path) -> list[str]:
    """检查是否还有未填充的 [TODO] 占位符。返回违规文件列表。"""
    issues: list[str] = []
    for path in sorted(expert_dir.rglob("*")):
        if not path.is_file():
            continue
        # 跳过二进制（头像）
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        todo_count = text.count("[TODO")
        if todo_count > 0:
            rel = path.relative_to(expert_dir)
            issues.append(f"{rel}: 仍有 {todo_count} 处 [TODO]")
    return issues


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    expert_dir = Path(sys.argv[1]).expanduser().resolve()

    if not expert_dir.is_dir():
        sys.exit(f" 专家目录不存在: {expert_dir}")

    print(f" 终检专家包: {expert_dir.name}")
    result = validate_expert(expert_dir)
    print(result.summary())
    if not result.is_valid:
        sys.exit("\n 校验未通过，无法确认可发现性。请先修复上述错误。")

    # 同 id / 同展示名查重（云端目录缓存 + 本地 experts/；同 id 阻断）
    from check_conflict import run_check
    code, messages = run_check(expert_dir=expert_dir)
    for line in messages:
        print(line)
    if code != 0:
        sys.exit("\n 查重未通过：与已有专家同 id。请更换 id（目录名与 agentCard.id 同步修改）后重试。")

    # [TODO] 占位符检查
    issues = check_completeness(expert_dir)
    if issues:
        print("\n 仍有未填充的 [TODO] 占位符：")
        for issue in issues:
            print(f"   - {issue}")
        sys.exit("   请补全内容后再注册。")

    # 确认位于专家根目录
    experts_dir = get_experts_dir().resolve()
    try:
        expert_dir.relative_to(experts_dir)
        in_place = True
    except ValueError:
        in_place = False

    print(f"\n 专家 '{expert_dir.name}' 内容完整、校验通过")
    if in_place:
        print(f"   位置: {expert_dir}（位于专家根目录，可被 expert.load 发现）")
        local_enabled = os.environ.get("JIUWEN_EXPERT_LOCAL_DIRS", "1") == "1"
        if local_enabled:
            print("   本地专家源已启用（默认）→ 立即可见于 experts.list")
        else:
            print("    本地专家源已被显式关闭（JIUWEN_EXPERT_LOCAL_DIRS=0）→ experts.list 暂不可见")
    else:
        print(f"    当前位置 {expert_dir} 不在专家根目录 {experts_dir} 下")
        print(f"      请移动到 {experts_dir / expert_dir.name} 后再 expert.load")


if __name__ == "__main__":
    main()
