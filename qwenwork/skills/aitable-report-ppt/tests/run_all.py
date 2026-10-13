#!/usr/bin/env python3
"""统一测试入口：合约 → 反例夹具 → 故障注入。

三者回答三个不同的问题，缺一不可：

- 合约测试：各脚本之间的接口还对得上吗
- 反例夹具：已知的两份坏产物，现在还会被拒吗
- 故障注入：尺子本身还量得准吗

反例夹具此前只躺在目录里，没有任何流程执行它们，README 里"必须失败"的描述
无人核对——这正是缺陷产物能被冻结成金标准的原因之一。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _playwright import node_modules  # noqa: E402

NODE_MODULES = node_modules() or ""

# 每份反例必须失败，且失败项要包含这些关键词——只断言退出码为 1 是不够的：
# 一份低对比度样本若被无关的指纹检查拦下，退出码同样是 1，而可读性门禁其实没起作用。
NEGATIVES = [
    ("negative-underfilled", [
        "text meets displayed font floors",
        "chart axis text meets font floor",
        "average coverage across analysis slides",
        "primary charts meet minimum height",
    ]),
    ("v3-known-bad", [
        "text meets contrast floors",
        "page runtime meets the validator contract",
    ]),
]


# 唯一的正样本：v5 交付件，2026-08-21 人工逐页确认过。
# 它的正确状态是 manual_required 而非 passed——无头环境没有登录态，内嵌的钉钉
# 记录必然 401，这是设计内的第三态。断言必须指名道姓：状态是 manual_required、
# 硬失败恰好 0、唯一的非通过项就是那条登录态检查。
# 写成「退出码为 0」会让这份好样本天天假失败；写成「退出码非 0」则与反例无异。
POSITIVE = ("v5-known-good", "embedded record sources need a signed-in check")

def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    # 合约测试自己不解析 Playwright 路径，靠这里注进环境；漏了它整组会以
    # "Playwright not found" 假失败，看着像门禁坏了，其实只是路径没传下去。
    env = {**os.environ, "CODEX_NODE_MODULES": NODE_MODULES}
    return subprocess.run(cmd, env=env, text=True, **kw)


def section(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def check_negatives() -> bool:
    section("反例夹具：两份已知坏产物必须被拒")
    fixtures = ROOT / "tests/fixtures/regression"
    ok = True
    for name, expected in NEGATIVES:
        html, spec = fixtures / f"{name}.html", fixtures / f"{name}-spec.json"
        if not html.exists():
            print(f"❌ {name}: 夹具缺失"); ok = False; continue
        out = fixtures / f".{name}-result.json"
        # 先删旧结果：上一次中断留下的文件会在本次崩溃时被当成本次结论读取，
        # 那正是"把陈旧数据当新鲜判定"——与门禁里修过的错误同一类。
        out.unlink(missing_ok=True)
        proc = run(["node", str(ROOT / "scripts/validate_visual_report.js"),
                    str(html), str(spec), "--output", str(out)], capture_output=True)
        if not out.exists():
            print(f"💥 {name}: 验证器崩溃，没有产出判定\n   {proc.stderr[-300:]}")
            ok = False
            continue
        payload = json.loads(out.read_text(encoding="utf-8"))
        out.unlink()
        failed = [c["name"] for r in payload.get("runs", []) for c in r.get("checks", [])
                  if not c.get("passed")]
        if not failed:
            print(f"❌ {name}: 竟然通过了——门禁退化了，不是样本变好了")
            ok = False
            continue
        missing = [e for e in expected if not any(e in f for f in failed)]
        if missing:
            print(f"⚠️  {name}: 失败了，但缺少预期失败项 {missing}")
            ok = False
        else:
            print(f"✅ {name}: 被拒，且命中全部 {len(expected)} 项预期失败")
    return ok


def check_positive() -> bool:
    section("正样本夹具：一份已知好产物必须通过")
    fixtures = ROOT / "tests/fixtures/regression"
    name, allowed = POSITIVE
    html, spec = fixtures / f"{name}.html", fixtures / f"{name}-spec.json"
    oracle = fixtures / f"{name}-oracle.json"
    if not html.exists():
        print(f"❌ {name}: 夹具缺失")
        return False
    out = fixtures / f".{name}-result.json"
    out.unlink(missing_ok=True)
    proc = run(["node", str(ROOT / "scripts/validate_visual_report.js"),
                str(html), str(spec), "--oracle", str(oracle), "--output", str(out)],
               capture_output=True)
    if not out.exists():
        print(f"💥 {name}: 验证器崩溃，没有产出判定\n   {proc.stderr[-300:]}")
        return False
    payload = json.loads(out.read_text(encoding="utf-8"))
    out.unlink()
    failed = [c["name"] for r in payload.get("runs", []) for c in r.get("checks", [])
              if not c.get("passed")]
    stray = [f for f in failed if allowed not in f]
    if stray:
        print(f"❌ {name}: 好样本被拦下了——门禁收得过紧，误伤合格产物：{stray[:4]}")
        return False
    if payload.get("status") != "manual_required":
        print(f"❌ {name}: 状态应为 manual_required，实际 {payload.get('status')}")
        return False
    print(f"✅ {name}: 通过（{payload.get('passed')} 项），唯一非通过项是设计内的登录态复核")
    return True


def main() -> None:
    results = {}

    section("合约测试")
    results["contracts"] = run([sys.executable, str(ROOT / "scripts/test_contracts.py")],
                               capture_output=True).returncode == 0
    print("✅ 通过" if results["contracts"] else "❌ 失败（单独运行 scripts/test_contracts.py 看详情）")

    results["negatives"] = check_negatives()
    results["positive"] = check_positive()

    section("故障注入：检验门禁的测量能力")
    results["mutations"] = run([sys.executable, str(ROOT / "tests/mutations/run_mutations.py")]).returncode == 0

    section("汇总")
    for name, ok in results.items():
        print(f"  {'✅' if ok else '❌'} {name}")
    sys.exit(0 if all(results.values()) else 1)


if __name__ == "__main__":
    main()
