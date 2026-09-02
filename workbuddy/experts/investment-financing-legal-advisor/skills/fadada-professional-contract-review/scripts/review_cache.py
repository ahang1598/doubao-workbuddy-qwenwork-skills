#!/usr/bin/env python3
"""审查哈希冻结复用（共享内核 · SSOT）—— §7/§8 一致性最强保证。

key = hash(规范化合同文本 + 规则集)。命中**已核准**的历史审查 → 整份结论幂等复用（0 偏差）；
合同变更（key miss）→ 条款级 delta：只列出需重审的变化条款，未变条款的结论按内容哈希自动结转。

子命令：
  key     --contract <docx> [--ruleset <file>|--ruleset-id <id>]            # 打印 doc/ruleset/条目哈希
  freeze  --contract ... --operations ops.json [--report r.json] [--decision-state d.json]
          [--approve] [--cache-dir DIR]                                     # 冻结一次审查为缓存条目
  lookup  --contract ... [--cache-dir DIR]                                  # 命中→复用；未命中→条款 delta
退出码：0 命中可复用 / 2 部分复用(有变化条款需重审) / 3 无可用缓存(需全量审查)。
缓存目录默认 ./ .review-cache（或 --cache-dir / 环境变量 REVIEW_CACHE_DIR），属运行期数据，不纳入 SSOT 同步。
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, shutil, sys
from pathlib import Path

def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()

def clause_texts(docx: Path) -> list[str]:
    from docx import Document
    return [_norm(p.text) for p in Document(docx).paragraphs if _norm(p.text)]

def sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def ruleset_hash(args) -> tuple[str, str]:
    if args.ruleset:
        rid = Path(args.ruleset).stem
        return rid, sha(_norm(Path(args.ruleset).read_text(encoding="utf-8")))
    rid = args.ruleset_id or "general-practice"
    return rid, sha(rid)

def compute_keys(args):
    clauses = clause_texts(args.contract)
    clause_h = {f"p{i+1:04d}": sha(t) for i, t in enumerate(clauses)}
    doc_hash = sha("\n".join(clauses))
    rid, rs_hash = ruleset_hash(args)
    entry_id = f"{doc_hash[:12]}_{rs_hash[:8]}"
    return {"clauses": clauses, "clause_hash": clause_h, "doc_hash": doc_hash,
            "ruleset_id": rid, "ruleset_hash": rs_hash, "entry_id": entry_id}

def cache_dir(args) -> Path:
    d = Path(args.cache_dir or os.environ.get("REVIEW_CACHE_DIR", "./.review-cache"))
    d.mkdir(parents=True, exist_ok=True)
    return d

def load_entries(cdir: Path):
    for meta in cdir.glob("*/meta.json"):
        try:
            yield json.loads(meta.read_text(encoding="utf-8")), meta.parent
        except Exception:
            continue

def cmd_key(args):
    k = compute_keys(args)
    print(json.dumps({x: k[x] for x in ("doc_hash", "ruleset_id", "ruleset_hash", "entry_id")},
                     ensure_ascii=False, indent=2))
    return 0

def cmd_freeze(args):
    k = compute_keys(args); cdir = cache_dir(args)
    entry = cdir / k["entry_id"]; entry.mkdir(parents=True, exist_ok=True)
    for opt, name in [(args.operations, "operations.json"), (args.report, "report.json"),
                      (args.decision_state, "decision-state.json")]:
        if opt: shutil.copy2(opt, entry / name)
    meta = {"entry_id": k["entry_id"], "doc_hash": k["doc_hash"], "ruleset_id": k["ruleset_id"],
            "ruleset_hash": k["ruleset_hash"], "clause_hash": k["clause_hash"],
            "status": "approved" if args.approve else "pending",
            "contract": str(args.contract)}
    (entry / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已冻结条目 {k['entry_id']}  状态={meta['status']}  → {entry}")
    if not args.approve:
        print("  注：未核准条目不会被 lookup 复用；人工核对后用 --approve 重新冻结以启用复用。")
    return 0

def cmd_lookup(args):
    k = compute_keys(args); cdir = cache_dir(args)
    # 1) 精确命中（同合同+同规则）且已核准 → 幂等复用
    exact = cdir / k["entry_id"] / "meta.json"
    if exact.exists():
        m = json.loads(exact.read_text(encoding="utf-8"))
        if m.get("status") == "approved":
            print(f"[复用] 命中已核准缓存 {k['entry_id']}（合同与规则均未变）→ 直接复用既有结论，0 偏差。")
            print(f"  复用产物: {exact.parent}/operations.json|report.json|decision-state.json")
            return 0
        print(f"[未复用] 命中条目 {k['entry_id']} 但状态={m.get('status')}（未核准），需人工核准后方可复用。")
        return 2
    # 2) 未命中 → 找同规则下条款重叠最高的已核准条目，做条款级 delta
    cur = set(k["clause_hash"].values())
    best, best_overlap = None, -1
    for m, _p in load_entries(cdir):
        if m.get("status") != "approved" or m.get("ruleset_hash") != k["ruleset_hash"]:
            continue
        old = set(m.get("clause_hash", {}).values())
        ov = len(cur & old)
        if ov > best_overlap:
            best, best_overlap = m, ov
    if not best:
        print("[全量审查] 无同规则的已核准缓存，需对整份合同执行完整审查。")
        return 3
    old = set(best["clause_hash"].values())
    unchanged = cur & old; added = cur - old; removed = old - cur
    reuse_ratio = len(unchanged) / max(len(cur), 1)
    # 变化条款 → 新文档中的 para id
    h2id = {h: pid for pid, h in k["clause_hash"].items()}
    need_review = sorted(h2id[h] for h in added)
    print(f"[部分复用] 合同已变更，未精确命中；基于已核准条目 {best['entry_id']} 做条款级 delta：")
    print(f"  条款总数 {len(cur)} | 未变(结论结转) {len(unchanged)} | 新增/变更(需重审) {len(added)} | 删除 {len(removed)}")
    print(f"  结论结转率: {reuse_ratio:.2f}")
    print(f"  需重审条款(新文档 para id): {need_review or '无'}")
    print(f"  → 复用 {len(unchanged)} 条未变条款的既有结论，仅对上述 {len(added)} 条变化条款重新审查。")
    return 2 if added else 0

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("key", "freeze", "lookup"):
        sp = sub.add_parser(name)
        sp.add_argument("--contract", required=True, type=Path)
        sp.add_argument("--ruleset", type=Path)
        sp.add_argument("--ruleset-id")
        sp.add_argument("--cache-dir")
        if name == "freeze":
            sp.add_argument("--operations", type=Path, required=True)
            sp.add_argument("--report", type=Path)
            sp.add_argument("--decision-state", type=Path)
            sp.add_argument("--approve", action="store_true")
    args = ap.parse_args()
    return {"key": cmd_key, "freeze": cmd_freeze, "lookup": cmd_lookup}[args.cmd](args)

if __name__ == "__main__":
    sys.exit(main())
