#!/usr/bin/env python3
"""verify_probe.py — 验证 agent_task_probe.py 对全部 agent 的兼容情况。"""
import json
from pathlib import Path
import subprocess
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
PROBE = SCRIPT_DIR / "agent_task_probe.py"
AGENTS = ["qoder", "codex", "claudecode", "qoderwork"]
REQUIRED = ["chatId", "title", "status", "createdAt", "updatedAt", "chatType", "sourceChatId", "agent", "summary"]


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    return p.returncode, p.stdout, p.stderr


failures = []

# 1. 逐 agent --list：契约字段 + outputFiles
detail_samples = {}
for agent in AGENTS:
    code, out, err = run([sys.executable, str(PROBE), "--list", "--agent", agent, "--limit", "100"])
    if code != 0:
        failures.append(f"{agent} --list exit={code}: {err[:200]}")
        continue
    try:
        d = json.loads(out)
    except json.JSONDecodeError as e:
        failures.append(f"{agent} --list stdout 非法 JSON: {e}")
        continue
    bad = [t["chatId"] for t in d["tasks"] if any(not t.get(f) for f in REQUIRED)]
    with_files = [t for t in d["tasks"] if t["outputFiles"]]
    no_out_key = [t["chatId"] for t in d["tasks"] if "outputFiles" not in t]
    print(f"[list] {agent:<11} total={d['total']:<5} 缺字段={len(bad)} 无outputFiles键={len(no_out_key)} 前100条带产出文件={len(with_files)}")
    if bad:
        failures.append(f"{agent} 缺字段: {bad[:3]}")
    if no_out_key:
        failures.append(f"{agent} 缺 outputFiles 键: {no_out_key[:3]}")
    if with_files:
        detail_samples[agent] = with_files[0]["chatId"]
        print(f"       示例 {with_files[0]['chatId'][:45]} -> {with_files[0]['outputFiles'][0][:70]}")
    else:
        print(f"       ⚠ 前100条无产出文件样本")

# 2. 逐 agent --detail：outputFiles 带 exists
for agent, chat_id in detail_samples.items():
    code, out, err = run([sys.executable, str(PROBE), "--detail", chat_id])
    if code != 0:
        failures.append(f"{agent} --detail exit={code}")
        continue
    d = json.loads(out)
    t = d["task"]
    files = t.get("outputFiles", [])
    ok_shape = all(isinstance(f, dict) and "path" in f and "exists" in f for f in files)
    exists_n = sum(1 for f in files if f["exists"])
    print(f"[detail] {agent:<11} files={len(files)} exists={exists_n} 结构正确={ok_shape}")
    if not ok_shape:
        failures.append(f"{agent} detail outputFiles 结构异常")
    if files:
        print(f"         {files[0]}")

# 3. 全量 all：去重 + 契约
code, out, err = run([sys.executable, str(PROBE), "--list", "--agent", "all"])
if code == 0:
    d = json.loads(out)
    ids = [t["chatId"] for t in d["tasks"]]
    dup = len(ids) - len(set(ids))
    bad = sum(1 for t in d["tasks"] if any(not t.get(f) for f in REQUIRED))
    dist = {}
    for t in d["tasks"]:
        dist[t["agent"]] = dist.get(t["agent"], 0) + 1
    print(f"[all] total={d['total']} 重复chatId={dup} 缺字段={bad} 分布={dist}")
    if dup:
        failures.append(f"全量重复 chatId={dup}")
    if bad:
        failures.append(f"全量缺字段={bad}")
else:
    failures.append(f"all --list exit={code}")

print()
if failures:
    print("❌ 失败项：")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("✅ 全部通过")
