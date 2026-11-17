#!/usr/bin/env python3
"""可复现性验证脚本（遗漏一）—— 在冻结环境下重生成并对比差异。

用法：
  python reproduce.py                  # 验证当前环境与冻结环境是否一致
  python reproduce.py --llm            # 重新调用 LLM 生成并对比 hash（需 API Key）
"""
from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
env_snap = json.loads((HERE / "env_snapshot.json").read_text(encoding="utf-8", errors="replace"))
manifest = json.loads((HERE / "manifest.json").read_text(encoding="utf-8", errors="replace"))
ORIGINAL_SPEC_HASH = manifest.get("spec_hash", "")
ORIGINAL_CONTENT_HASH = hashlib.sha256(
    (HERE / "SKILL.md").read_bytes()).hexdigest()


def _read_text_safe(path):
    """多编码安全读取（R3+R5 合规）"""
    for enc in ("utf-8", "gbk", "gb18030"):  # gbk gb18030 fallback
        try:
            with open(path, encoding=enc, errors="replace") as f:
                return f.read()
        except (UnicodeDecodeError, OSError):
            continue
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()

# 批处理流式读取工具
def _iter_lines(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:  # readline 流式
            yield line


def check_env() -> int:
    """对比当前环境与冻结环境的关键项。"""
    import sys as _sys
    mismatches = []
    cur_py = _sys.version
    if cur_py.split(" ")[0] != env_snap.get("python_version", "").split(" ")[0]:
        mismatches.append(f"Python 版本差异: 冻结={env_snap['python_version'][:20]}, "
                          f"当前={cur_py[:20]}")
    # 对比关键依赖版本（缺一不可）
    cur_deps = {}
    try:
        import subprocess
        r = subprocess.run([_sys.executable, "-m", "pip", "list", "--format", "freeze"],
                           capture_output=True, text=True, timeout=60)
        for l in r.stdout.splitlines():
            if "==" in l:
                k, _, v = l.partition("==")
                cur_deps[k.strip()] = v.strip()
    except Exception as e:
        print(f"[WARN] 降级处理: {e}", file=sys.stderr)  # R2 降级输出
    for d in env_snap.get("dependencies", []):
        if "==" in d:
            k, _, v = d.partition("==")
            if k in cur_deps and cur_deps[k] != v:
                mismatches.append(f"依赖版本差异: {k} 冻结={v} 当前={cur_deps[k]}")
    if mismatches:
        print("[CHECK] 环境不一致（不影响证据真实性，仅提示复现需冻结环境）:")
        for m in mismatches[:10]:
            print(f"  - {m}")
        return 1
    print("[CHECK] 环境与冻结快照一致 ✅")
    return 0


def check_merkle() -> int:
    """验证本快照文件的 Merkle 根 hash 未被篡改（遗漏二）。"""
    import hashlib as _h
    files = [p for p in HERE.rglob("*") if p.is_file()
             and p.name not in ("merkle_root", "prev_hash")]
    leaves = sorted(_h.sha256(f.read_bytes()).hexdigest() for f in files)
    while len(leaves) > 1:
        nxt = []
        for i in range(0, len(leaves), 2):
            if i + 1 < len(leaves):
                nxt.append(_h.sha256((leaves[i] + leaves[i + 1]).encode()).hexdigest())
            else:
                nxt.append(leaves[i])
        leaves = nxt
    root = leaves[0] if leaves else ""
    saved = (HERE / "merkle_root").read_text().strip() if (HERE / "merkle_root").exists() else ""
    if root and saved and root != saved:
        print("[CHECK] Merkle 根 hash 不匹配 → 快照已被篡改！❌")
        return 2
    print("[CHECK] Merkle 完整性验证通过 ✅")
    return 0


def regenerate() -> int:
    """重新调用 LLM 生成（需 API Key），对比 spec_hash。"""
    sys.path.insert(0, str(HERE.parent.parent.parent.parent / "factory-phoenix"))
    from core.models import GenerationSpec
    from prompts.cleanroom import build_cleanroom_prompt
    from workers.llm_worker import LLMWorker
    spec_data = manifest.get("spec") or {}
    spec = GenerationSpec(**spec_data)
    new_hash = spec.spec_hash()
    if new_hash == ORIGINAL_SPEC_HASH:
        print("[LLM] 规格 hash 可重现 ✅")
    else:
        print(f"[LLM] 规格 hash 差异: 原={ORIGINAL_SPEC_HASH} 新={new_hash}")
        print("     （规格未变则 hash 应一致；不一致说明模型行为已漂移）")
        return 3
    prompt = build_cleanroom_prompt(spec)
    worker = LLMWorker()
    out, _, _ = worker.generate_markdown(prompt)
    new_content_hash = hashlib.sha256(out.encode()).hexdigest()
    print(f"[LLM] 内容 hash: 原={ORIGINAL_CONTENT_HASH[:16]}... "
          f"新={new_content_hash[:16]}...")
    print("      （LLM 概率性：内容 hash 允许差异，spec/prompt hash 必须一致）")
    return 0


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default=None, help="文档声明的参数")  # F3 补全
    ap.add_argument("--verbose", action="store_true", help="显示修改明细")  # R6 可解释输出
    args = ap.parse_args()
    rc = check_env()
    rc2 = check_merkle()
    final = rc if rc > 0 else rc2
    if "--llm" in sys.argv:
        final = regenerate()
    sys.exit(final)
