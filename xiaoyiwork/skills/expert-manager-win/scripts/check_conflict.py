#!/usr/bin/env python3
"""Expert Conflict Check — 创建/导入专家前的同 id、同展示名查重。

数据源（均只读）：
  - 云端目录缓存：expert-catalog-cache.json（桌面主进程 SWR 落盘，
    位于 JIUWENSWARM_DATA_DIR 的父目录；文件缺失时跳过云端查重并提示）
  - 本地专家：experts/ 根目录扫描（id = 目录名；展示名读各自 manifest.json）

用法：
  python check_conflict.py --id <expert_id> --name <展示名>   # 定名阶段（包目录未建）
  python check_conflict.py <expert_dir>                      # 包已就绪（读 manifest.json）

判定与退出码：
  - 同 id（云端或本地已存在）→ exit 1：必须更换 id（目录名与 agentCard.id 需同步一致），
    否则本地包会静默遮蔽云端同 id 专家、云端更新断供
  - 仅 displayName 冲突 → exit 0：打印警告，建议更换展示名或向用户说明后确认
  - 用法/清单错误 → exit 2
"""

import json
import os
import sys
from pathlib import Path

CLOUD_CATALOG_FILE = "expert-catalog-cache.json"


def get_experts_dir() -> Path:
    """专家包根目录解析，优先级与 init_expert.get_experts_dir 保持一致：
    JIUWEN_EXPERTS_DIR > JIUWENSWARM_DATA_DIR/agent/workspace/experts > ~/.jiuwenswarm/..."""
    override = os.environ.get("JIUWEN_EXPERTS_DIR", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    data_dir = os.environ.get("JIUWENSWARM_DATA_DIR", "").strip()
    if data_dir:
        return (Path(data_dir).expanduser() / "agent" / "workspace" / "experts").resolve()
    return Path.home() / ".jiuwenswarm" / "agent" / "workspace" / "experts"


def get_cloud_catalog_path() -> Path:
    """云端目录缓存路径：JIUWENSWARM_DATA_DIR 的父目录下（桌面用户根）。
    桌面两种布局（.../users/<uid>/jiuwenswarm 或 .../users/<uid>/xiaoyiwork）均可命中。"""
    data_dir = os.environ.get("JIUWENSWARM_DATA_DIR", "").strip()
    base = Path(data_dir).expanduser().resolve() if data_dir else Path.home() / ".jiuwenswarm"
    return base.parent / CLOUD_CATALOG_FILE


def load_cloud_catalog() -> tuple[list[dict] | None, Path]:
    """读取云端目录缓存；返回 (条目列表|None, 缓存路径)。None = 缓存不可用。"""
    cache = get_cloud_catalog_path()
    if not cache.is_file():
        return None, cache
    try:
        entries = json.loads(cache.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return None, cache
    if not isinstance(entries, list):
        return None, cache
    return [e for e in entries if isinstance(e, dict)], cache


def load_local_experts(experts_dir: Path, exclude: Path | None) -> list[tuple[str, str, str]]:
    """扫描本地 experts/ 根：返回 [(id, 展示名, 目录名)]。available 与否都参与查重。"""
    out: list[tuple[str, str, str]] = []
    if not experts_dir.is_dir():
        return out
    for child in sorted(experts_dir.iterdir()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        if exclude is not None and child.resolve() == exclude.resolve():
            continue
        eid, ename = child.name, child.name
        manifest = child / "manifest.json"
        if manifest.is_file():
            try:
                card = (json.loads(manifest.read_text(encoding="utf-8")).get("agentCard") or {})
                eid = str(card.get("id") or eid)
                ename = str(card.get("name") or ename)
            except (json.JSONDecodeError, OSError, UnicodeDecodeError):
                pass
        out.append((eid, ename, child.name))
    return out


def run_check(expert_dir: Path | None = None, expert_id: str = "", expert_name: str = "") -> tuple[int, list[str]]:
    """执行查重。返回 (退出码, 输出行)。id 冲突 → 1；仅展示名冲突 → 0；干净 → 0。"""
    lines: list[str] = []
    if expert_dir is not None:
        manifest_path = expert_dir / "manifest.json"
        if not manifest_path.is_file():
            return 2, [f" manifest.json 不存在: {manifest_path}"]
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError, UnicodeDecodeError) as exc:
            return 2, [f" manifest.json 解析失败: {exc}"]
        card = manifest.get("agentCard") or {}
        expert_id = str(card.get("id") or expert_dir.name)
        expert_name = str(card.get("name") or expert_dir.name)

    expert_id = expert_id.strip()
    expert_name = expert_name.strip()
    if not expert_id:
        return 2, [" 未提供 expert id"]

    id_conflicts: list[str] = []
    name_conflicts: list[str] = []

    entries, cache_path = load_cloud_catalog()
    if entries is None:
        lines.append(f"  [跳过] 未找到云端目录缓存（{cache_path}），仅查本地")
    else:
        for item in entries:
            cid = str(item.get("id", "")).strip()
            cname = str(item.get("displayName", "")).strip()
            if cid and cid == expert_id:
                id_conflicts.append(f"云端专家 id='{cid}'（{cname or '无展示名'}）")
            elif cname and cname == expert_name:
                name_conflicts.append(f"云端专家 displayName='{cname}'（id={cid}）")

    experts_dir = get_experts_dir()
    for eid, ename, dirname in load_local_experts(experts_dir, exclude=expert_dir):
        if eid == expert_id:
            id_conflicts.append(f"本地专家 id='{eid}'（目录 {dirname}）")
        elif ename and ename == expert_name:
            name_conflicts.append(f"本地专家 displayName='{ename}'（目录 {dirname}）")

    lines.append(f" 查重目标: id='{expert_id}'  displayName='{expert_name}'")

    if id_conflicts:
        lines.append(f" [阻断] 同 id 冲突 x{len(id_conflicts)}：")
        for c in id_conflicts:
            lines.append(f"   - {c}")
        lines.append("   同 id 会让本地包静默遮蔽对方（云端更新断供），必须更换 id 重查。")
        return 1, lines

    if name_conflicts:
        lines.append(f" [警告] displayName 冲突 x{len(name_conflicts)}：")
        for c in name_conflicts:
            lines.append(f"   - {c}")
        lines.append("   列表会出现同名牌；建议更换展示名，或向用户说明后确认继续。")

    if not name_conflicts:
        lines.append(" [通过] 无同 id / 同展示名冲突")
    return 0, lines


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(2)
    if args[0] == "--id":
        if len(args) < 2:
            sys.exit(" 用法: check_conflict.py --id <expert_id> [--name <展示名>]")
        expert_id = args[1]
        expert_name = args[3] if len(args) >= 4 and args[2] == "--name" else ""
        code, lines = run_check(expert_id=expert_id, expert_name=expert_name)
    else:
        code, lines = run_check(expert_dir=Path(args[0]).expanduser().resolve())
    for line in lines:
        print(line)
    sys.exit(code)


if __name__ == "__main__":
    main()
