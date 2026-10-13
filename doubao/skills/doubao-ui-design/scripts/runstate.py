#!/usr/bin/env python3
"""run.json —— 这一稿的唯一状态源。脚本写，你不写。

为什么需要它：没有它的时候，`shoot.py` 崩了一次、`observe.py`
跑了 0 次、`check.py` 跑了 0 次，**发布照样成功**。
质量机制写在文档里就等于没写——跳过它零成本，诚实执行反而多花十分钟。

所以这一版把机制变成**前置条件**：截图 / 看图 / 门 各自留下一张收据，
`publish.py` 从收据里读，读不到就不发。收据全部由包内脚本自己产出，
不依赖宿主能力、不依赖网络、不依赖你确认——拿不到的前置条件不设。

结构：
    contract   交付合同（plan.py 冻结）
    style      风格签名（style.py 生成）
    receipts   shot / observe / check / publish 四类收据
    delivery   最终交付参数（deliver.py 从 receipts 读，你不转写）

这个文件不是命令行工具，是其它脚本共用的一层。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import shutil
import sys
import tempfile
import time
from pathlib import Path

RUN_NAME = "run.json"
ENV_KEY = "UI_DESIGN_RUN"
ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
UI = f"python3 {SCRIPTS / 'ui.py'}"


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def blank(query: str = "") -> dict:
    return {
        "version": 1,
        "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "query": query,
        "contract": None,
        "style": None,
        "receipts": {"shot": [], "observe": [], "check": [], "publish": [],
                     "read": []},
        "delivery": None,
    }


# ── 任务身份与落点（P0-1）─────────────────────────────────
# 用 `slug + sha256(query)[:8]` 当目录名。它治好了「不同 query 抢同一份
# run.json」，但**治不了「两个相同需求同时跑」** —— 目录名是 query 的纯函数，
# 没有任何唯一位，两个并发会话仍然落回同一个目录。而并行正是 的原始诉求。
#
# 拆成两件事：**slug 只负责可读性**（让人在 runs 根目录里认得出哪个是哪个），
# **时间戳 + 随机位负责唯一性**。续跑必须显式 `--run <绝对路径>`，
# 不许靠 query 反推是哪一次任务 —— 反推正是上面那个 bug 的成因。
def run_slug(query: str) -> str:
    return re.sub(r"[^\w一-鿿]+", "", query)[:12] or "run"


def new_run_id(query: str) -> str:
    return (f"{run_slug(query)}-{time.strftime('%Y%m%d-%H%M%S')}"
            f"-{secrets.token_hex(2)}")


def candidate_roots() -> list[Path]:
    """固定顺序。**ROOT 内的候选一律剔除** —— 那正是 P0-1 要治的东西。

    宿主 Bash 默认带沙箱，`$HOME` 不保证可写，所以不硬编码任何绝对根：
    先试会话初始工作目录（宿主合同里明确的 writable root），再试 home，再试 tmp。
    """
    out: list[Path] = []
    env = os.environ.get("UI_DESIGN_HOME")           # 人工逃生口，不给模型用
    if env:
        out.append(Path(env))
    try:
        cwd = Path.cwd().resolve()
        if ROOT != cwd and ROOT not in cwd.parents:
            out.append(cwd / "ui-design-runs")
    except OSError:
        pass
    out.append(Path.home() / "ui-design-runs")
    out.append(Path(tempfile.gettempdir()) / "ui-design-runs")
    return out


def probe_writable(root: Path) -> str | None:
    """真的写一个文件再删掉。**不能用 os.access / 看 mode 位** ——
    沙箱是在 syscall 层拦的，mode 位是好的、写下去照样 EPERM。
    返回 None 表示可写，否则返回失败原因。"""
    try:
        root.mkdir(parents=True, exist_ok=True)
        p = root / f".probe-{secrets.token_hex(3)}"
        p.write_text("x", encoding="utf-8")
        p.unlink()
        return None
    except Exception as e:
        return f"{type(e).__name__}: {e}"


def list_runs() -> list[tuple[Path, dict]]:
    """扫所有候选根下的 run.json，按 mtime 倒序。给保底分岔列候选用。"""
    seen: dict[str, tuple[Path, dict]] = {}
    for r in candidate_roots():
        if not r.is_dir():
            continue
        for p in sorted(r.glob(f"*/{RUN_NAME}")):
            d = load(p)
            if d:
                seen[str(p.resolve())] = (p.resolve(), d)
    return sorted(seen.values(), key=lambda t: t[0].stat().st_mtime, reverse=True)


def describe_run(p: Path, d: dict) -> str:
    c = d.get("contract") or {}
    wd = Path(c.get("workdir") or p.parent)
    bits = []
    prod = ((c.get("deliverables") or {}).get("product") or {}).get("path")
    if prod and (wd / prod).is_file():
        bits.append(f"{prod} {(wd / prod).stat().st_size // 1024}KB")
    if (wd / "doc").is_dir():
        bits.append("doc/")
    if any(r.get("documentId") for r in (d.get("receipts") or {}).get("publish", [])):
        bits.append("已发布")
    ts = time.strftime("%m-%d %H:%M", time.localtime(p.stat().st_mtime))
    return f"{p.parent.name:38} {ts}  " + ("、".join(bits) or "只有骨架")


def resolve_workdir(query: str, explicit: str | None = None
                    ) -> tuple[Path | None, str, list[str]]:
    """返回 (工作目录, 选它的理由, 失败时试过哪些路径)。

    显式 --dir 优先（但仍然拒绝落进安装目录）。否则按候选顺序挑第一个
    **真的写得进去**的根，在它下面开一个唯一 id 的新目录。
    """
    if explicit:
        wd = Path(explicit).resolve()
        return wd, "你指定的 --dir", []
    tried: list[str] = []
    for r in candidate_roots():
        why = probe_writable(r)
        if why is None:
            return r / new_run_id(query), f"{r} 可写", tried
        tried.append(f"{r}　{why}")
    return None, "", tried


def guard_install_dir(wd: Path, query: str) -> bool:
    """产物不许住在 skill 安装目录里。返回 True 表示越界（调用方应当中止）。

    2026-07-27 实测：两个任务在安装目录里抢同一份 run.json，后开的那个继承了
    前一个的合同（官网任务拿到 App 骨架）；22 分钟的成品页 + 文档画布 + 合同
    在第 22 分钟被整体清空 —— 因为包自己的 .gitignore 把它们列成了可丢弃的构建产物。
    """
    w = wd.resolve()
    if w != ROOT and ROOT not in w.parents:
        return False
    print("✗ 工作目录落在 skill 安装目录里。安装目录是所有会话共享的，\n"
          "  而这个包的 .gitignore 曾把 run.json / shots/ / doc/img/ 列为可丢弃产物 ——\n"
          "  实测代价：22 分钟的成品页、文档画布和合同被另一个会话整体清空。\n"
          f"\n  照抄这条（不要 cd 进包目录）：\n    {UI} brief --query {json.dumps(query, ensure_ascii=False)}")
    return True


def die_no_writable_root(tried: list[str], query: str) -> None:
    print("✗ 没有可写的工作目录。试过：")
    for t in tried:
        print(f"    {t}")
    print("\n  这台机器上的 Bash 很可能处于沙箱模式，而以上路径都不在已授权目录里。\n"
          "  两条路，任选：\n"
          "  ① 让这条命令带提权跑（宿主会弹窗给你批准）\n"
          "  ② 指一个你确定可写的目录：\n"
          f"     {UI} brief --dir <你确定可写的目录> "
          f"--query {json.dumps(query, ensure_ascii=False)}")


def find(explicit: str | None = None, start: Path | None = None) -> Path | None:
    """显式路径 > 环境变量 > 从 start 向上找 run.json。找不到返回 None。"""
    if explicit:
        return Path(explicit).resolve()
    env = os.environ.get(ENV_KEY)
    if env:
        return Path(env).resolve()
    cur = (start or Path.cwd()).resolve()
    for d in [cur, *cur.parents]:
        cand = d / RUN_NAME
        if cand.is_file():
            return cand
        if len(str(d)) < 4:
            break
    return None


def load(path: Path | None) -> dict | None:
    if not path or not Path(path).is_file():
        return None
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None


def save(path: Path, data: dict) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2),
                          encoding="utf-8")


def add_receipt(path: Path | None, kind: str, obj: dict) -> bool:
    """往 run.json 追加一张收据。没有 run.json 就静默跳过——
    脚本单跑（比如你在调试 gold）不该被状态文件挡住。"""
    if not path:
        return False
    data = load(path) or blank
    data.setdefault("receipts", {}).setdefault(kind, []).append(
        {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), **obj})
    save(path, data)
    return True


def note_missing(kind: str) -> None:
    print(f"（没找到 {RUN_NAME}，{kind} 收据未记录。"
          f"先跑 `python3 {SCRIPTS}/plan.py --query \"…\"` 建合同，"
          f"否则 publish.py 会因为收据缺失拒绝发布。）")


def add_run_arg(ap) -> None:
    ap.add_argument("--run", help=f"{RUN_NAME} 路径（默认从当前目录向上找）")


# ── 合同横幅（P0-3）──────────────────────────────────────
# **唯一实现。** 除这里之外任何地方手写横幅即回归 FAIL（危险信号 10：两份抄本）。
#
# 为什么合同必须在每条命令上重印，一组实测就够了：宿主在 83 分钟里
# **压缩了 6 次上下文**，压缩存档由模型自己写，它保留语义、**丢弃几何与阈值**——
#
# 关键词        r2  r3  r4  r5  r6  r7
# 取景框         1   1   0   0   0   0   ← 第 3 次压缩后永久消失
# .stage/#app    0   0   0   0   0   0   ← 从来没进过任何一次存档
# 390 / 1440     0   0   0   0   0   0   ← 取景尺寸从来没进过存档
# 两件必交        0   0   0   0   0   0
#
# 第 22 分钟模型重建产物时，手上有取景框的**颜色**，没有取景框的**几何**。
# 所以横幅的硬要求是**必须含几何与数字**，不能只写语义。
#
# 第二条硬要求是**活得过管道过滤**：实测 28 次 ui.py 调用里 16 次（57%）带
# `| grep` 或 `| tail`，最短 `tail -20`。所以横幅 <=10 行、且结尾那次紧贴 NEXT——
# 10 行 + NEXT 6 行 = 16 < 20。配套的另一半是"让模型没有理由去 grep"（输出自适应）。
GOLD_OF = {"产品界面": "gold/app-home/index.html",
           "单向叙事": "gold/h5-qq2026/index.html",
           "互动生成器": "gold/h5-cycle/index.html",
           "web": "gold/web-pulse/index.html",
           # 四种新载体各有对口 gold，横幅那一行不再指到"结构最近的那份"
           "web-console": "gold/console-api/index.html",
           "big-screen": "gold/screen-hotan/index.html",
           "spec-board": "gold/board-flow/index.html",
           "long-image": "gold/longimg-summit/index.html"}
BAR_W = 74


def opponent_of(contract: dict) -> str:
    d = (contract.get("deliverables") or {}).get("product") or {}
    shape = d.get("shape")
    if shape in GOLD_OF:
        return GOLD_OF[shape]
    return GOLD_OF.get(contract.get("surface") or "", GOLD_OF["web"])


def banner(run: dict, stage: str = "", run_path: Path | None = None) -> str:
    c = run.get("contract") or {}
    if not c:
        return ""
    d = c.get("deliverables") or {}
    prod, doc = d.get("product") or {}, d.get("doc") or {}
    mobile = c.get("artifactClass") == "mobile"
    q = (run.get("query") or c.get("query") or "").strip().replace("\n", " ")
    if len(q) > 58:
        q = q[:34] + "…" + q[-22:]
    view = "390×844 与 1440×900（卡片被看到的宽度）" if mobile else "1440×900 与 390"
    geo = ("版心在 1440 下必须 <=520px（取景框）· 量 " if mobile
           else "按合同取景 · 量 ") + view
    cnt = c.get("count") or {}
    cnt_s = (f"　数量 {cnt['n']}{cnt.get('unit', '')}〔{cnt['mode']}〕"
             if cnt.get("n") else "")
    sig = ((run.get("style") or {}).get("signature")
           or (run.get("style") or {}))
    sig_s = " / ".join(str(sig[k]) for k in
                       ("ground", "typeVoice", "density", "colorStrategy",
                        "motionStance", "shapeLanguage") if sig.get(k))
    ledger = [x["value"] for x in (c.get("ledger") or []) if x.get("block")]
    L = ["═" * 6 + " 合同 · 每条命令都重印（上下文会被压缩，别靠记）" + "═" * 18,
         f"原话  {q}",
         f"合同  {c.get('surface') or c.get('artifactClass')}"
         f" · {c.get('operation') or 'create'}"
         f" · {prod.get('shape') or '宽屏'}"
         f" · 交 {'+'.join(c.get('handoff') or ['html', 'doc'])}{cnt_s}",
         f"风格  {sig_s or '（还没跑 style.py）'}"
         f"　← 配色/字体/构图按它长，不要凭手感",
         f"阶段  {stage or '未开始'}",
         f"交件① {prod.get('path'):<22}{geo}",
         f"交件② doc/*                 画布 {len(doc.get('canvases') or [])} 块 + 封面 + proposal"
         f"　关键界面节由 ship 自动写入",
         "顺序  先做完①再写② —— ②的关键界面节放的是①的真机截图，不是素材照片",
         # 「怎么看」「谁来交」不写进来，执行者就会自己发明：自建截图环当 review、
         # 拿 file:// 当交付，于是 doc 与两张卡一个都没有。横幅有行数预算，压成一行。
         "下一步  看图＝**执行** ui.py review（不是自己 open_url/截图/起 http.server）"
         "　交付＝ui.py ship 出参数：先 NotifyHuman 交 Doc、再 app_builder_agent 交卡"]
    if ledger:
        # 用户逐字点名的东西。**文案要 100% 匹配原文**，这一行是它的常驻提醒。
        s = " / ".join(ledger[:4])
        L.append(f"账本  必须出现：{s[:56]}" + ("…" if len(s) > 56 else ""))
    L += [f"对手  {ROOT / opponent_of(c)}"
          f"　← 学机制不抄版式（gold/README.md）",
          f"盘在  {c.get('workdir')}",
          "═" * BAR_W]
    return "\n".join(L)


ORCH_KEY = "UI_ORCHESTRATED"


def orchestrated() -> bool:
    """当前这次运行是被 ui.py 编排调起的吗。

    `ui.py` 把 18 条脚本命令收成 4 条，代价是**一次输出里会出现多条「下一步」**
    ——plan 一条、skeleton 一条、shoot 一条、编排器自己一条。
    守则 S24：一条命令的输出里只能有一个 NEXT，互斥指令并存时执行者走**先出现的那条**。
    所以子脚本在被编排调起时闭嘴，NEXT 由编排器统一在末行给出。

    注意这里关掉的只有"下一步"那一段。工艺内容（必读集、参考区间、形态口径）
    照印不误 —— 精简必读集时删流程，不删工艺。
    """
    return os.environ.get(ORCH_KEY) == "1"
