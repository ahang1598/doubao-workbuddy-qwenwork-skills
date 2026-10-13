#!/usr/bin/env python3
"""包自检：证明这个 skill 能产出 gold/ 里那个质量的东西，且门没跑偏。

跑的是**双向回归**，缺任何一向都会重演上一代"越改越差"：

  正向  gold/ 里的产物必须过各自的断言（它们是真的做出来过的东西）
  反向  gold/ 里的产物必须过全部 BLOCK 门 —— 任何 BLOCK 门 FAIL 它们，
        就是门错了，改门不改稿。这条是门的标定基准。
  机制  质量机制本身要能被绕过吗？不能。闭包、对账、空集必 FAIL 都在这里验。
  结构  脚本齐全、方法论文档齐全、gold 源码齐全

每一条都对应 方案里的一个编号用例，注释里标了。

用法：  python3 scripts/selftest.py [--quick]
"""
from __future__ import annotations

import argparse
import http.server
import json
import re as _re
import socket
import socketserver
import subprocess
import sys
import tempfile
import threading
from contextlib import closing
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SC = ROOT / "scripts"
results: list[tuple[str, bool, str]] = []


def ck(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))


# ── M5 · 审美资产只增不减 ────────────────────────────────────────
# 这是 的第一行代码，装在所有改动之前 —— 它是保险丝，不是检查。
#
# 隔壁包 的原样事故：为了"缩短路径"把 SKILL.md 从 35KB 削到 11.8KB，
# 把工艺搬出必经路径，**到达率归零**，产出退化成「上图下文 × 15 页」。
# 而本轮实测（§3.6）已经证明这个担心在本包同样成立：
# 写成品页那一刻 `gold/app-home` 到达 0 次、`fingerprints` 0 次、图标库 0 次。
#
# 所以：门可以删（本轮删了两条），命令可以合（4 → 3），
# **但 craft/ reference/ gold/ assets/ 只许增，不许减、不许缩。**
# 想故意改：`python3 scripts/selftest.py --relock`，那是一次显式动作。
AESTHETIC_DIRS = ("craft", "reference", "gold", "assets")
LOCK = ROOT / "tests" / "aesthetic-assets.lock.json"


def aesthetic_manifest() -> dict[str, list]:
    import hashlib
    out: dict[str, list] = {}
    for d in AESTHETIC_DIRS:
        base = ROOT / d
        if not base.is_dir():
            continue
        for p in sorted(base.rglob("*")):
            if not p.is_file() or p.name == ".DS_Store":
                continue
            h = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
            out[str(p.relative_to(ROOT))] = [p.stat().st_size, h]
    return out


def aesthetic_lock() -> None:
    if not LOCK.is_file():
        ck("M5 审美资产只增不减", False,
           f"锁文件不在（{LOCK.relative_to(ROOT)}）—— 先跑 "
           "`python3 scripts/selftest.py --relock` 建锁")
        return
    want = json.loads(LOCK.read_text(encoding="utf-8"))
    now = aesthetic_manifest()
    gone = [k for k in want if k not in now]
    shrunk = [f"{k} {want[k][0]}→{now[k][0]}B"
              for k in want if k in now and now[k][0] < want[k][0]]
    added = [k for k in now if k not in want]          # 增是允许的，不报错
    changed = [k for k in want
               if k in now and now[k][1] != want[k][1] and now[k][0] >= want[k][0]]
    detail = ""
    if gone:
        detail += "消失 " + "、".join(gone[:3])
    if shrunk:
        detail += ("　" if detail else "") + "变小 " + "；".join(shrunk[:3])
    if gone or shrunk:
        detail += ("　—— 审美资产只增不减。的原样事故是把工艺搬出必经路径，"
                   "到达率归零，产出退化成「上图下文 × 15 页」。"
                   "确实要改：selftest.py --relock")
    else:
        detail = f"{len(want)} 份守住" + (f"，新增 {len(added)} 份" if added else "") \
                 + (f"，改写 {len(changed)} 份（只增不减，改写允许）" if changed else "")
    ck("M5 审美资产只增不减（craft/reference/gold/assets）",
       not gone and not shrunk, detail)


def free_port() -> int:
    with closing(socket.socket()) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Server:
    def __init__(self, directory: Path):
        self.port = free_port()
        handler = type("H", (http.server.SimpleHTTPRequestHandler,),
                       {"__init__": lambda s, *a, **k:
                        http.server.SimpleHTTPRequestHandler.__init__(
                            s, *a, directory=str(directory), **k),
                        "log_message": lambda *a: None})
        self.httpd = socketserver.TCPServer(("127.0.0.1", self.port), handler)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}/index.html"

    def close(self) -> None:
        self.httpd.shutdown()


def sh(cmd: list[str], cwd: Path | None = None) -> tuple[int, str]:
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=900, cwd=cwd)
    return r.returncode, r.stdout + r.stderr


def py(script: str, *args: str, cwd: Path | None = None) -> tuple[int, str]:
    return sh([sys.executable, str(SC / script), *args], cwd=cwd)


def structure() -> None:
    for rel in ["SKILL.md", "scripts/ui.py", "scripts/shoot.py", "scripts/check.py",
                "scripts/observe.py", "scripts/fetch_photos.py",
                "scripts/publish.py", "scripts/skeleton.py", "scripts/plan.py",
                "scripts/style.py", "scripts/deliver.py", "scripts/runstate.py",
                "method/01-look.md", "method/05-review.md",
                "craft/page-grammar.md", "craft/anti-patterns.md",
                "craft/award-mechanisms.md",
                "craft/scale-atlas.md", "reference/scale-atlas.json",
                "craft/composition-motion.md",
                "reference/image-direction.md", "delivery/host-contract.md",
                "skeletons/web.html", "skeletons/h5.html",
                "skeletons/doc-canvas.html", "skeletons/doc-cover.html",
                "gold/web-pulse/index.html", "gold/h5-qq2026/index.html",
                "gold/doc-canvas/build_docs.py", "gold/README.md"]:
        ck(f"存在 {rel}", (ROOT / rel).is_file())

    n_py = len(list(SC.glob("*.py")))
    # 12 → 13：新增 ui.py。它是**编排器**，不是新能力 ——
    # 它存在的意义正好相反：把必经路径上的 18 条命令收成 4 条。
    # 13 → 14：新增 icons.py。它也不是新能力，是把**包里已经有的**
    # 4.3MB 图标库接到手上 —— 上一版那一行只写了"图标必须用 SVG"，
    # 于是库调用 0 次、图标只能手搓或用 emoji 顶（而 anti-patterns 的
    # 第一条正是"不许用 emoji 冒充主视觉"）。**规则没有变成产能。**
    ck("脚本数量克制（<=14）", n_py <= 14, f"{n_py} 个")
    def _lines(p: Path) -> int:
        return len(p.read_text(encoding="utf-8", errors="ignore").splitlines())

    # 起分两笔算：**上线跑的代码**和**回归自己**是两回事，
    # 把它们加在一起，会出现"多写几条回归就必须去删产能"的荒唐激励。
    test_lines = _lines(SC / "selftest.py")
    py_lines = sum(_lines(p) for p in SC.glob("*.py")) - test_lines
    # 上限被抬过三次，每次都要写清理由，否则它就变成一个可以无声上调的数字：
    # 3600 → 4800：新增 pack_img.py（产能，给文档出图）
    # 4800 → 5200：净增 465 行 —— pack_img 的 --for-doc-screens、
    # deliver 的 base64 拆分与 prompt 直印、publish 的封面 API 修正与清单合并，
    # 全部是产能与 bug 修复；门这一侧净增 0（新增一条同时删掉一条）。
    # 5200 → 5500（且不再计入 selftest.py）：新增 ui.py 编排器 + observe
    # 形状自动修。门这一侧是**净减**：删掉闭包 C5、把 C1–C4 与封面参数
    # 从阻断降为披露。行数涨了而阻断点少了 —— 这正是这一轮要的方向。
    # 真正防"脚本变成生成器"的是下面那条**比值**，不是这个绝对值。
    # 5500 → 6600：本轮的净增全部在**产能与状态**这一侧 ——
    # runstate 的合同横幅与 runId、shoot 的 states 声明式协议、
    # publish 的封面三级重试、ui 的关键屏自动入稿与阶段识别、
    # 新增 icons.py（把 4.3MB 的图标库接进素材计划）。
    # 门这一侧是**净 0**：新增 frame-intact / contract-frame 两条，
    # 同时删掉 content-under-dock(app) 与恒真的 screen-fit（收支表见 §5.4）。
    # -B/C 6600 → 7400：四个正交合同字段 + 需求账本 + 四种新载体的骨架映射。
    # 门这一侧仍是净减（BLOCK 13 → 12），新载体靠**关掉不适用的门**分化，
    # `SKIP_BY_PROFILE` 是减法表，不是新门。
    # 7400 → 7600：本轮新增的产能与修复，逐项可追 ——
    #   人格值解析（括号内逗号不切断，治整份样式表被截断）
    #   门的复跑判据改内容哈希（治"改完之后没有门再看过"）
    #   手机图位按台数分岔 + 片段自带样式
    #   对比度报错给出前景/背景 hex 与同色相替代值
    #   角色清洗的静态判据与它的对偶断言
    # 门这一侧是**净 0**：device-scale 由 REPORT 升 BLOCK，没有新增门码。
    ck("上线脚本 <=7600 行", py_lines <= 7600, f"{py_lines} 行")
    # 900 → 1100：新增 M5 审美资产锁（本轮的保险丝）与七条阳性对照。
    # 这个数字放宽的代价必须写清楚：**它只对"回归自己"放宽**，
    # 上线脚本那条比值门（门 <= 产能 45%）一个字没动。
    # 1400 → 1550：角色清洗的两条断言 + 人格解析的两条 + 片段自带样式的三条。
    # 放宽只对"回归自己"成立；上线脚本那条比值门（门 <= 产能 45%）一个字没动。
    ck("回归自己 <=1620 行", test_lines <= 1620, f"{test_lines} 行")

    # 单个脚本不许无限膨胀 —— 一个文件吞掉一切是"生成器化"的早期形态。
    # check.py（校验器）和 selftest.py（回归）天然长，两个都不上线，单独放宽。
    # 700 → 860：ui.py（编排器）与 publish.py（发布链）两个都过线了，
    # 而它们涨出来的行**没有一行是新判据**：ui.py 是阶段识别 + 关键屏自动入稿
    # + 横幅，publish.py 是封面三级重试。两个文件都不产出设计内容 ——
    # 真正防"脚本变成生成器"的是下面那条**比值**门和"没有成片字面 CSS"，
    # 那两条一个字没动。
    fat = [(p.name, _lines(p)) for p in SC.glob("*.py")
           if p.name not in ("check.py", "selftest.py", "ui.py") and _lines(p) > 980]
    # ui.py 与 check.py 一起移出这条：它是**编排器**，长度是"把 18 条命令
    # 收成 3 条"的价目，它一行设计内容都不产出。真正防"脚本变成生成器"的是
    # 下面那条比值门和"没有成片字面 CSS"，两条一个字没动。
    # 860 → 980：plan.py 涨的是**参考**不是规则 ——
    # 八份 gold 的对手卡（每份 4 段源码锚点 + 机制说明）都住在它的 GOLD_ANCHORS 里。
    # 判断一个脚本是不是在"生成器化"，看的是下面那条比值门和"没有成片字面 CSS"，
    # 不是行数本身。
    ck("没有单个上线脚本超过 980 行（编排器与校验器除外）", not fat, str(fat))

    # 这一条才是上一代真正的病征：**校验器比生成器还大**（6318 行门 vs 1714 行产能）。
    # 总行数只是它的代理指标，而且很容易被"多写点产能"合法地顶破。
    gate_lines = len((SC / "check.py").read_text(encoding="utf-8").splitlines())
    rest = py_lines - gate_lines
    ck("门不得比产能大（check.py <= 其余脚本的 45%）",
       gate_lines <= rest * 0.45, f"门 {gate_lines} 行 / 其余 {rest} 行 "
       f"= {gate_lines / max(1, rest):.0%}")

    # 上一代 116KB 字面 CSS 常量的复发检测。
    # 注意别把 JS 探针的大括号当成 CSS —— 只认真正的 CSS 声明。
    CSS_PROP = _re.compile(
        r"\b(?:color|background(?:-color|-image)?|font-(?:size|family|weight)|"
        r"padding|margin|border(?:-radius)?|display|position|width|height|"
        r"grid-template-columns|flex|box-shadow|letter-spacing|line-height)\s*:",
        _re.I)
    decls = 0
    for p in SC.glob("*.py"):
        src = p.read_text(encoding="utf-8", errors="ignore")
        for lit in _re.findall(r'"""(.*?)"""', src, _re.S):
            decls += len(CSS_PROP.findall(lit))
    ck("脚本里没有成片字面 CSS（<40 条声明）", decls < 40, f"{decls} 条 CSS 声明")

    sk = list((ROOT / "skeletons").glob("*.html"))
    ck("骨架是独立可编辑的 HTML 文件（>=4 份）", len(sk) >= 4, f"{len(sk)} 份")

    # 文档里提到的脚本必须真的存在。
    # 一条指向不存在文件的命令，执行者会先 find 几次再放弃整条链 ——
    # 隔壁 skill 因为一个解析不出来的入口，让八轮加的门全部执行 0 次。
    # 这一轮清掉了 7 条上一代残留的悬空引用
    # （ui_pipeline / check_ui_quality / phosphor_icon / build_widget /
    # check_assets / check_image_prompt / select_dna / validate_research_evidence）。
    dangling = set()
    for p in ROOT.rglob("*.md"):
        for m in _re.finditer(r"scripts/([a-z_]+\.py)",
                              p.read_text(encoding="utf-8", errors="ignore")):
            if not (SC / m.group(1)).is_file():
                dangling.add(f"{p.relative_to(ROOT)} → {m.group(1)}")
    ck("文档里没有指向不存在脚本的命令", not dangling,
       "; ".join(sorted(dangling)[:3]))

    # 参照物必须能在离线的包里打开。
    # 这个 skill 给无数人用，绝大多数人点不开某个内网文档。
    ext = []
    for p in ROOT.rglob("*.md"):
        for m in _re.finditer(r"(参考|参照|排版参考)[^。\n]{0,20}(https?://\S+|docx/\w+)",
                              p.read_text(encoding="utf-8", errors="ignore")):
            ext.append(f"{p.name}:{m.group(0)[:40]}")
    ck("参照物不指向外部链接", not ext, "; ".join(ext[:3]))

    # 发现路径下只有一个 UI 设计类 skill（两个并存时路由不可预测）
    peers = [d.name for d in ROOT.parent.iterdir()
             if d.is_dir() and _re.search(r"ui-design", d.name)]
    # 并存**允许且仅允许**一种情况：稳定版 + 一个 -v2 试验版。
    # 这是刻意的（在副本上改，不动已经及格的那版），但它仍然是路由风险：
    # 两个都能被 skill 发现机制命中。所以这条不放过，只是把话说清楚。
    stable = [x for x in peers if not x.endswith("-v2")]
    ok = len(peers) <= 1 or (len(stable) == 1 and len(peers) == 2)
    ck("发现路径下的 UI 设计类 skill", ok,
       ",".join(peers) + ("　← 稳定版 + 试验版并存：试跑时要确认 trace 加载的是哪一个，"
                          "定版后必须归档另一个" if ok and len(peers) == 2 else ""))


# ── 本轮的阳性对照（不需要浏览器的那一半）──────────────────
# §9.2 的规矩：**先加进来看着它们红，再动手。**
# 抓不到的自门只是一条更慢的 PASS —— 所以每一条都要能指出
# 「把修复禁用掉，它必须转红」。逐处对应关系写在每条的 detail 里。
def r31() -> None:
    sys.path.insert(0, str(SC))
    import runstate as _rs                                    # noqa: E402
    import ui as _ui                                          # noqa: E402
    import pack_img as _pack                                  # noqa: E402
    import plan as _plan                                      # noqa: E402
    import check as _check                                    # noqa: E402

    # 并发同 query：两个完全相同的需求同时跑，必须落在两个目录里。
    # `slug + sha256(query)[:8]` 是 query 的**纯函数**，没有唯一位 ——
    # 这一条在它身上必然红，而并行正是 的原始诉求。
    q = "为大学生群体设计一个校园论坛形式的社交app首页"
    ids = {_rs.new_run_id(q) for _ in range(8)}
    ck("同一条 query 连开 8 次 → 8 个不同的 runId", len(ids) == 8,
       f"{len(ids)} 个不同　例：{sorted(ids)[0]}")
    ck("runId 里有可读的 slug（人要在 runs 目录里认得出哪个是哪个）",
       all(x.startswith(_rs.run_slug(q)) for x in ids), _rs.run_slug(q))

    # 工作目录不许落在安装目录里（的核心诉求）
    roots = _rs.candidate_roots()
    inside = [r for r in roots if r == ROOT or ROOT in r.parents]
    ck("候选工作根一个都不在 skill 安装目录里", not inside,
       "、".join(str(x) for x in inside[:2]) or f"{len(roots)} 个候选全在包外")
    ck("guard_install_dir 拦得住把产物写进安装目录",
       _rs.guard_install_dir(ROOT / "app", q) is True
       and _rs.guard_install_dir(Path(tempfile.gettempdir()) / "x", q) is False)

    # 横幅唯一实现。除 runstate.banner 之外任何地方手写即 FAIL
    #（危险信号 10：两份抄本一定会分叉）。
    hand = []
    for p in SC.glob("*.py"):
        if p.name in ("runstate.py", "selftest.py"):
            continue
        for i, ln in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if "合同 · 每条命令都重印" in ln or _re.search(r'"原话\s', ln):
                hand.append(f"{p.name}:{i}")
    ck("合同横幅只有 runstate.banner 一处实现", not hand,
       "；".join(hand[:3]) or "0 处手写")

    # 横幅必须活得过 `| tail -20`：实测 57% 的 ui.py 调用带管道过滤，
    # 最短就是 tail -20。**印在开头的东西有一半概率不会被读到。**
    run = {"query": q, "contract": {
        "artifactClass": "mobile", "workdir": "/tmp/x", "title": "t",
        "deliverables": {"product": {"path": "app/index.html", "shape": "产品界面"},
                         "doc": {"canvases": ["a", "b"]}}}}
    run["contract"]["ledger"] = [{"kind": "文案", "value": "立即发布", "block": True}]
    run["contract"]["count"] = {"unit": "屏", "n": 5, "mode": "exact", "source": "原话"}
    run["contract"]["surface"] = "mobile-app"
    run["contract"]["operation"] = "create"
    run["contract"]["handoff"] = ["html", "doc"]
    run["style"] = {"signature": {"ground": "dark", "typeVoice": "sans-cool"}}
    b = _rs.banner(run, "产品（app/index.html）")
    lines = b.splitlines()
    # 下限 8 是必需的：把 banner 改成 `return ""` 时它有 0 行，
    # 而"<=13"对 0 行成立 —— **一条对空输入成立的断言是空真空通过**，
    # 这个坑包里已经踩过三次（图片门 0 张图报绿、分屏门选择器不匹配报绿）。
    ck("横幅 8–13 行（13 + NEXT 6 = 19 < tail -20，且不许是空的）",
       8 <= len(lines) <= 13, f"{len(lines)} 行")
    need = ["390", "1440", "520", "产品界面", "app/index.html", q[:10],
            "立即发布", "5屏", "dark"]
    miss = [x for x in need if x not in b]
    ck("横幅带几何与数字（压缩存档丢的正是这一类）", not miss,
       "缺 " + "、".join(miss) if miss else "390/1440/520/形态/交件/原话 都在")

    # 输出自适应：有 BLOCK 时 PASS 行折叠。
    # 成因是实测 check.py 单次输出 **28 行里 25 行是 PASS** —— 那就是模型
    # 去 `grep -E BLOCK` 的原因，而过滤掉的一定包括我们最想让它看到的横幅。
    fake = "\n".join(["  PASS  x" + str(i) + "  想要什么" for i in range(25)]
                     + ["✗ BLOCK  frame-intact  想要什么   → 实测 1440px",
                        "", "25/26 通过｜BLOCK 1｜REPORT 0"])
    sq = _ui.squeeze(fake)
    ck("有 BLOCK 时输出 <=25 行且 PASS 折叠成一行",
       len(sq.splitlines()) <= 25 and "其余 25 条通过" in sq
       and "frame-intact" in sq, f"{len(sq.splitlines())} 行")
    green = "\n".join(["  PASS  x" + str(i) + "  y" for i in range(25)])
    ck("全绿时原样返回（这时它不长，也没人需要 grep）",
       _ui.squeeze(green) == green)

    # -AA/AB · M1 对手卡：按形态指到对口的 gold，锚点**现算**不写死行号。
    for shape, want, cls in [("产品界面", "gold/app-home", "mobile"),
                             ("单向叙事", "gold/h5-qq2026", "mobile"),
                             ("互动生成器", "gold/h5-cycle", "mobile"),
                             (None, "gold/web-pulse", "web")]:
        card = _plan.opponent_card(ROOT, shape, cls)
        n_anchor = card.count("▸ L")
        ck(f"对手卡指对 gold：{shape or 'web'} → {want}",
           want in card and n_anchor >= 3,
           f"{n_anchor} 段锚点" + ("" if want in card else f"　指到了别处"))
    # 往 gold 里插 20 行空白，锚点必须还指得对（按类名现算，不是硬编码行号）
    src = ROOT / "gold" / "app-home" / "index.html"
    before = _plan._excerpt(src, r"^#flow\{")
    shifted = Path(tempfile.mkdtemp()) / "gold" / "app-home"
    shifted.mkdir(parents=True)
    (shifted / "index.html").write_text(
        "\n" * 20 + src.read_text(encoding="utf-8"), encoding="utf-8")
    after = _plan._excerpt(shifted / "index.html", r"^#flow\{")
    ck("对手卡的行号是现算的（往 gold 里插 20 行，锚点仍对）",
       bool(before and after) and after[0] == before[0] + 20
       and after[1] == before[1], f"{before[0] if before else '-'} → "
                                  f"{after[0] if after else '-'}")

    # M4 图标库真的取得出来。上一版这一行只说"不能用什么"，
    # 结果 4.3MB 的库调用 0 次、图标只能手搓或用 emoji 顶。
    code, out = py("icons.py", "find", "搜索", "消息", "发布", "我的")
    ck("icons.py find 打印可内联的 <svg>",
       code == 0 and out.count("<svg class=\"ic ") >= 4 and "currentColor" in out,
       f"{out.count('<svg class=')} 个 svg")
    plan_out = py("plan.py", "--query", q, "--dir", tempfile.mkdtemp())[1]
    ck("素材计划里有 icons.py 那条可复制命令",
       "icons.py find" in plan_out,
       "有" if "icons.py find" in plan_out else "没有 —— 规则又没有变成产能")
    ck("对手卡真的印在 brief 的必经输出里（不是只存在于函数里）",
       "这一稿的对手" in plan_out and "学机制，不抄版式" in plan_out)

    # 四问必须写全：出什么 / 什么格式 / 谁来交 / 怎么看。
    # 只写前两问时，执行者会自己发明后两问 —— 自起服务器+浏览器截图当 review、
    # 拿 file:// 链接当交付，于是 doc 与两张卡一个都没有。
    _bn = _rs.banner({"contract": {"artifactClass": "mobile", "surface": "mobile-app",
                                   "deliverables": {"product": {"path": "app/index.html"},
                                                    "doc": {"canvases": ["a", "b"]}}},
                      "query": "示例输入"}, "产品")
    ck("横幅答了「怎么看」，且点明它是一条命令",
       "review" in _bn and "**执行**" in _bn)
    ck("横幅答了「谁来交」，两张卡都点名",
       "NotifyHuman" in _bn and "app_builder_agent" in _bn)
    ck("横幅明确禁掉自建截图环", "http.server" in _bn and "open_url" in _bn)

    # 骨架是执行者唯一必然打开的文件 —— 下一步命令必须写在它里面，
    # 而且要带真实 run 路径（占位符没被替换就等于没写）。
    for _k in ("app", "h5", "web", "doc"):
        _sk = (ROOT / "skeletons" / {"app": "app.html", "h5": "h5.html",
                                     "web": "web.html", "doc": "doc-canvas.html"}[_k])
        _s = _sk.read_text(encoding="utf-8")
        ck(f"骨架 {_sk.name} 头部写着下一条命令",
           "__NEXT_CMD__" in _s and "ui.py" not in _s.split("<html")[0].replace("__NEXT_CMD__", ""))
    # 内部子脚本名不许出现在给执行者的「下一步」里 —— 印它们等于教它自己拼流水线
    import skeleton as _sk2
    _bad = [k for k, v in _sk2.NEXT.items()
            if "shoot.py" in v or "observe.py" in v or "check.py --profile" in v]
    ck("下一步里不印内部子脚本名（只印 ui.py review）", not _bad, str(_bad))

    # 四问要写全：出什么 / 什么格式 / 谁来交 / 怎么看。
    # 只写前两问，执行者会自己发明后两问（自建截图环、file:// 交付）。
    _bn = _rs.banner({"contract": {"artifactClass": "mobile", "surface": "mobile-app",
                                   "deliverables": {"product": {"path": "app/index.html"},
                                                    "doc": {"canvases": ["a", "b"]}}},
                      "query": "示例输入"}, "产品")
    ck("横幅答了「怎么看」且点明是命令",
       "review" in _bn and "**执行**" in _bn and "http.server" in _bn)
    ck("横幅答了「谁来交」，两张卡都点名",
       "NotifyHuman" in _bn and "app_builder_agent" in _bn)
    _sm = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    ck("SKILL.md 有主链路工具表（含 TaskOutput 与 FileBatchUpload）",
       "TaskOutput" in _sm and "FileBatchUpload" in _sm and "user_prompt" in _sm)
    # 骨架是执行者唯一必然打开的文件，下一条命令要写在里面
    for _n in ("app.html", "h5.html", "web.html", "doc-canvas.html"):
        ck(f"骨架 {_n} 头部带下一条命令占位",
           "__NEXT_CMD__" in (ROOT / "skeletons" / _n).read_text(encoding="utf-8"))
    # 给执行者看的下一步里不许出现需要它自己解析的占位符，也不许印内部子脚本名
    import skeleton as _sk2
    _bad = [k for k, v in _sk2.NEXT.items()
            if "<SKILL>" in v or "shoot.py" in v or "observe.py" in v]
    ck("下一步里无 <SKILL> 占位符、无内部子脚本名", not _bad, str(_bad))

    # 人格值自己带逗号（`rgba(58,53,48,.10)`、字体栈），按裸逗号切会把它截断，
    # 写进画布就是 `--line:rgba(58;` —— **整份样式表从那里断掉**。
    # 实测代价：67 条 CSS 规则只剩 2 条，所有网格塌成通栏竖排，
    # 而每一道门都还是绿的（门量的是渲染结果，而渲染结果"确实"就是那样）。
    import skeleton as _sk                                    # noqa: E402
    _p = _sk.parse_persona(
        "paper=#FAF8F4,hairline=rgba(58,53,48,.10),"
        "font=Inter,PingFang SC,system-ui,radius=18px")
    ck("人格值里括号内的逗号不被切断（rgba 保持完整）",
       _p.get("hairline") == "rgba(58,53,48,.10)", _p.get("hairline", ""))
    ck("字体栈不被切成多个键，后面的键也不丢",
       _p.get("font") == "Inter,PingFang SC,system-ui" and _p.get("radius") == "18px",
       f"font={_p.get('font')}　radius={_p.get('radius')}")

    # 关键屏**自动写进画布**。上一版最后一步是"打印 <figure> 让模型粘"，
    # 实测粘了，但把 p01 粘了两次（而 p01/p02/p03 本来就是同一张图）。
    # **打印让粘贴也算隔一步，隔一步的事情不会自己发生。**
    tmp = Path(tempfile.mkdtemp())
    cv = tmp / "canvas.html"
    # 片段就用真的那一份形态：自带 <style>、自带带机身的容器。
    frag = _pack.stage_fragment(
        ['<figure><img src="data:image/jpeg;base64,AAA" alt="关键屏 1">'
         '<figcaption>一</figcaption></figure>'])
    cv.write_text("<html><body>\n<!-- KEY-SCREENS-START -->\n<p>旧的</p>\n"
                  "<!-- KEY-SCREENS-END -->\n</body></html>", encoding="utf-8")
    how = _ui.inject_key_screens(cv, frag)
    t = cv.read_text(encoding="utf-8")
    ck("关键屏写进 KEY-SCREENS 标记块（模型零参与）",
       bool(how) and "data:image/jpeg" in t and "旧的" not in t
       and "ui-stage" in t and "<!-- ↓↓" not in t, how)
    # 片段必须**自带样式**：粘进一份没有任何图位规则的手写画布也要成立。
    ck("片段自带样式（手写画布里也有机身和场，不退化成通栏竖图）",
       "<style>" in t and ".ui-stage img" in t and "box-shadow" in t)
    # 落点是旧图位容器时：整个容器被换掉，不套两层，且**补上标记**。
    cv.write_text('<html><body><div class="screens" style="--cols:3">'
                  '<div class="inner"><!-- 空 --></div></div></body></html>',
                  encoding="utf-8")
    how2 = _ui.inject_key_screens(cv, frag)
    t2 = cv.read_text(encoding="utf-8")
    ck("没有标记块时退到图位容器，整块替换且不套两层",
       bool(how2) and "data:image/jpeg" in t2
       and t2.count("ui-stage ui-stage-row") + t2.count('class="ui-stage"') == 1
       and 'class="screens"' not in t2 and "inner" not in t2,
       f"{how2}　stage={t2.count('ui-stage')}")
    ck("退到图位容器时补上标记块（重跑才是幂等的）",
       _ui.KEY_START in t2 and _ui.KEY_END in t2)
    _ui.inject_key_screens(cv, frag)
    t3 = cv.read_text(encoding="utf-8")
    ck("重跑不叠加（图与样式各只有一份）",
       t3.count("data:image/jpeg") == 1 and t3.count("<style>") == 1,
       f"img={t3.count('data:image/jpeg')} style={t3.count('<style>')}")
    cv.write_text("<html><body><p>什么都没有</p></body></html>", encoding="utf-8")
    ck("两条通路都没有时如实返回空（不假装写成功了）",
       _ui.inject_key_screens(cv, frag) == "")

    # 骨架必须预填截图声明 —— 没有它，`states` 只能滚动兜底，
    # 而这两份骨架的 body 都是锁死的（内容在内层容器里滚）→ N 张同图。
    for name in ("app", "h5"):
        t = (ROOT / "skeletons" / f"{name}.html").read_text(encoding="utf-8")
        ck(f"skeletons/{name}.html 预填了 __UI_CAPTURE__",
           "__UI_CAPTURE__" in t and "states:" in t)
    # 画布骨架要有关键屏的落点，否则 P0-9 只能退到 .screens 容器
    dc = (ROOT / "skeletons" / "doc-canvas.html").read_text(encoding="utf-8")
    ck("画布骨架有 KEY-SCREENS 标记块",
       "<!-- KEY-SCREENS-START -->" in dc and "<!-- KEY-SCREENS-END -->" in dc)

    # -AE/AF · M5 保险丝的阳性对照：少一份要红，多一份不许红。
    lock = json.loads(LOCK.read_text(encoding="utf-8")) if LOCK.is_file() else {}
    ck("M5 锁真的覆盖四个目录",
       bool(lock) and all(any(k.startswith(d + "/") for k in lock)
                          for d in AESTHETIC_DIRS),
       f"{len(lock)} 份")

    # 封面重试必须**换定位策略**，不是把同一条命令再跑一遍。
    # 物理成因有两种而它们返回同一个 False：命令没成功 / 锚点匹配不上被
    # lark-cli 追加到文末并**返回成功**。
    import publish as _pub                                    # noqa: E402
    src = (SC / "publish.py").read_text(encoding="utf-8")
    body = src.split("def insert_cover_verified", 1)[-1].split("\ndef ", 1)[0]
    ck("封面重试三级，且每一级换一种定位",
       body.count("lambda:") >= 3 and "doc_first_text" in body
       and "cover_in_doc" in body,
       f"{body.count('lambda:')} 级")
    ck("每一级都回读确认，不信命令的返回码",
       body.count("cover_in_doc(doc_id, as_who)") >= 1)
    # ship 的 NEXT 三级优先：封面缺失 > 关键屏没进画布 > 交卡。
    # **披露不是出口，NEXT 才是出口** —— 上一版封面回读失败只写进 gaps，
    # 而唯一的 NEXT 印的是"交两张卡"，于是这件事永远不会被做。
    ship = (SC / "ui.py").read_text(encoding="utf-8").split("def cmd_ship", 1)[-1]
    i_cover = ship.find("coverInserted")
    i_screens = ship.find("not ok_screens")
    i_card = ship.find("交两张卡")
    ck("ship 的 NEXT 三级优先：封面 > 关键屏 > 交卡",
       0 < i_cover < i_screens < i_card,
       f"{i_cover} / {i_screens} / {i_card}")

    # 命令种类：4 → 3（doc 并进 review）。**闭环一条没少**，少的是种类。
    subs = set(_re.findall(r'sp\.add_parser\(\s*[\'"]?(\w+)',
                           (SC / "ui.py").read_text(encoding="utf-8")))
    subs |= set(_re.findall(r'for name in \("(\w+)", "(\w+)"\)',
                            (SC / "ui.py").read_text(encoding="utf-8"))[0]
                if _re.findall(r'for name in \("(\w+)", "(\w+)"\)',
                               (SC / "ui.py").read_text(encoding="utf-8")) else [])
    code, out = py("ui.py", "--help")
    ck("命令种类 3 条（brief / review / ship），旧名仍可用",
       all(x in out for x in ("brief", "review", "ship", "start", "doc")),
       out.split("positional")[-1][:80].replace("\n", " "))

    # 印给模型抄的命令必须自带落点。实测：裸相对路径 `python3 scripts/ui.py`
    # 逼着模型 cd 进包目录，产物于是落在安装目录里被另一个会话清空。
    bare = []
    for p in SC.glob("*.py"):
        if p.name == "selftest.py":
            continue
        for i, ln in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if _re.search(r'["\s]python3 scripts/ui\.py', ln):
                bare.append(f"{p.name}:{i}")
    ck("-P0-2 脚本里 0 处裸 `python3 scripts/ui.py`（命令必须自带落点）",
       not bare, "；".join(bare[:3]) or "0 处")


def code_of(p: Path) -> str:
    """剥掉注释与文档字符串之后的源码。

    危险信号 17：**断言查措辞不查行为**，而且"把教训写进注释"这个动作本身
    会让断言失败 —— 一次踩中三条：我在 docstring 里写下
    「这里写的是 --index，那个 flag 不存在」，
    于是"源码里不许再出现 --index"的断言当场变红。
    结论是通则性的：**要查源码就先剥注释**，能查行为就不要查源码。

    用 ast 走一遍再 unparse —— 注释和文档字符串都不会出现在 AST 里，
    比手写 tokenize 过滤可靠得多（手写那版把 docstring 之后的字符串也误删了）。
    """
    import ast
    src = p.read_text(encoding="utf-8")
    try:
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Module, ast.ClassDef,
                                     ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            body = getattr(node, "body", [])
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                node.body = body[1:] or [ast.Pass()]
        return ast.unparse(tree)
    except Exception:
        return src


def _pub_anchor(pr: Path) -> str | None:
    sys.path.insert(0, str(SC))
    import publish as _p
    return _p.cover_anchor(pr)


def _deliver_fidelity(base: Path, run: dict, prompt: str) -> str | None:
    sys.path.insert(0, str(SC))
    import deliver as _d
    return _d.fidelity(prompt, base, run)


def mechanisms() -> None:
    """质量机制本身能不能被绕过 —— 这是这一轮的主题。"""
    tmp = Path(tempfile.mkdtemp(prefix="ui-selftest-"))

    # R5 · 素材计划：query 必须产出 >=4 个角色，且 image_gen 只能是满版
    code, out = py("plan.py", "--query",
                   "做一个骑行 App，帮用户挑路线、看天气、准备装备",
                   "--dir", str(tmp), cwd=tmp)
    run = json.loads((tmp / "run.json").read_text(encoding="utf-8"))
    plan = (run.get("contract") or {}).get("assetPlan") or []
    bad_slot = [a for a in plan if a["how"] == "image_gen" and a["slot"] != "full-bleed"]
    ck("R5 assetPlan >=4 个角色", len(plan) >= 4, f"{len(plan)} 个")
    ck("生图素材只能是满版（矩形图没有透明底）", not bad_slot, str(bad_slot[:1]))
    ck("R8 合同把 doc 冻结成必交产物",
       bool(((run.get("contract") or {}).get("deliverables") or {}).get("doc")))

    # R7 · 盘上没有可发的东西时必须拒绝
    # 作废了这条用例的旧语义（"没有收据不许发布"）：收据缺失现在是**披露**，
    # 不是阻断。阻断只剩"可证伪的产物存在性"，这里测的就是它。
    code, out = py("publish.py", "--run", str(tmp / "run.json"), cwd=tmp)
    ck("R7 盘上没有 proposal / 画布时拒绝发布",
       code != 0 and len([x for x in out.splitlines() if x.startswith("  ✗")]) >= 2,
       out.splitlines()[0] if out else "")
    ck("R8 缺 doc 时点名缺的是什么", "canvas-a" in out and "proposal" in out)
    # 命令必须**自带落点**（绝对路径），不能是裸 `python3 scripts/…` ——
    # 那种形态逼着模型 cd 进包目录，产物于是落进安装目录被别的会话清空。
    # 这条断言跟着换判据：数的是"带绝对路径的可执行命令"。
    abs_cmds = [ln for ln in out.splitlines()
                if "python3 /" in ln or str(SC) in ln]
    ck("闭包的每条失败都给了可执行的命令（且自带落点）",
       len(abs_cmds) >= 2 and "python3 scripts/" not in out,
       f"{len(abs_cmds)} 条带绝对路径"
       + ("；仍有裸相对路径" if "python3 scripts/" in out else ""))

    # R9 · 素材闭包：真实视觉资产 <8 必须拒绝
    # 拿 低分参照样本 的首页当被测件 —— 它实测只有 2 个，且全是 emoji 冒充
    # 产物路径从**合同**里读，不写死 —— 形态不同路径就不同（app/ vs h5/）
    prod = run["contract"]["deliverables"]["product"]
    ppath = tmp / prod["path"]
    ppath.parent.mkdir(parents=True, exist_ok=True)
    ppath.write_bytes((ROOT / "tests" / "case79" / "index.html").read_bytes())
    (ppath.parent / "shared.css").write_bytes(
        (ROOT / "tests" / "case79" / "shared.css").read_bytes())
    py("check.py", "--run", str(tmp / "run.json"), "--url", str(ppath),
       "--profile", prod["profile"], "--aesthetic", cwd=tmp)
    code, out = py("publish.py", "--run", str(tmp / "run.json"), cwd=tmp)
    ck("R9 真实视觉资产不足时被点名",
       "个真实视觉资产，合同要求" in out, "")

    # R2 · 交付对账：抄错一位必须当场被戳穿（上一轮"文档打不开"的全部原因）
    run = json.loads((tmp / "run.json").read_text(encoding="utf-8"))
    good = "Z8eXdXZydoq62BxhjMQcopOhnPh"
    run["receipts"]["publish"] = [{
        "url": f"https://example.larkoffice.com/docx/{good}",
        "documentId": good, "reconciled": True}]
    (tmp / "run.json").write_text(json.dumps(run, ensure_ascii=False), encoding="utf-8")
    code, out = py("deliver.py", "--run", str(tmp / "run.json"),
                   "--confirm", f"https://example.larkoffice.com/docx/{good[:12]}{good[13:]}")
    ck("R2 doc id 抄错一位被戳穿", code != 0 and "漏了" in out, out.splitlines()[0] if out else "")
    code, out = py("deliver.py", "--run", str(tmp / "run.json"),
                   "--confirm", f"https://example.larkoffice.com/docx/{good}")
    ck("R2 抄对了要放行", code == 0 and "对账通过" in out)

    # R6 · 风格不收敛
    hist = tmp / ".style-history.json"
    py("style.py", "--query", "做一个骑行 App，挑路线看天气",
       "--history", str(hist), "--out", str(tmp / "s1.json"))
    py("style.py", "--query", "一个高端茶叶品牌的官网，讲产地和工艺",
       "--history", str(hist), "--out", str(tmp / "s2.json"))
    s1 = json.loads((tmp / "s1.json").read_text())["signature"]
    s2 = json.loads((tmp / "s2.json").read_text())["signature"]
    d = sum(1 for k in s1 if s1[k] != s2[k])
    ck("R6 两个不同 query 的签名 >=3 维不同", d >= 3, f"{d} 维")
    code, out = py("style.py", "--diverge", str(ROOT / "gold/web-pulse/index.html"),
                   str(ROOT / "gold/h5-qq2026/index.html"))
    ck("R6 两稿视觉层 CSS Jaccard <=0.55", code == 0,
       out.splitlines()[0] if out else "")

    # / 封面必交且版式随内容变
    got = {}
    for name, args in [("mobile", ["--class", "mobile"]),
                       ("竖图", ["--class", "web", "--hero-aspect", "0.66"]),
                       ("横图", ["--class", "web", "--hero-aspect", "1.78"])]:
        code, out = py("skeleton.py", "cover", str(tmp / f"cov-{name}.html"),
                       "--title", "T", *args)
        m = _re.search(r"封面版式：(\S+)", out)
        got[name] = m.group(1) if m else "?"
    ck("封面版式随内容变", len(set(got.values())) == 3, str(got))
    ck("封面在合同的必交清单里",
       bool(((run.get("contract") or {})["deliverables"]["doc"]).get("cover")))

    # ══ 这一轮的五条根因，每条一个断言 ══════════════════

    # 载体分类：`app\b` 的 \b 在中文里永不成立，三条 query 全被判成 web
    sys.path.insert(0, str(SC))
    import plan as _plan
    for q, want in [("为大学生设计一个校园论坛社交app首页", "mobile"),
                    ("设计一个记账app的首页", "mobile"),
                    ("做一个健身app界面", "mobile"),
                    ("为空气传感器设计响应式产品官网", "web")]:
        ck(f"载体判对：{q[:14]}…", _plan.classify(q, None) == want,
           f"判成了 {_plan.classify(q, None)}，要的是 {want}")
    # 三种形态
    for q, want in [("咖啡点单小程序首页改版，加入邻居晒单动态流", "产品界面"),
                    ("QQ 2026 年度盘点报告，十屏复古风", "单向叙事"),
                    ("做一个 H5，测测你是哪种咖啡人格", "互动生成器")]:
        ck(f"形态判对：{q[:12]}…", _plan.product_shape(q) == want,
           f"判成了 {_plan.product_shape(q)}，要的是 {want}")
    ck("产品界面的 profile 是 app-screen",
       _plan.SHAPE_RULES["产品界面"][1] == "app-screen")

    # 风格签名：query 没给信号就**留空**，不再兜底成字典第一个键。
    # 实测三条真实 trace 的 ground 全是 dark —— 那不是审美失误，是默认值。
    import style as _style
    sig, _ = _style.choose(_style.score("为大学生群体设计校园论坛社交app首页"), [], {})
    ck("校园 query 不落 dark", sig.get("ground") != "dark", str(sig.get("ground")))
    sig2, conf2 = _style.choose(_style.score("做一个东西"), [], {})
    ck("无信号的维度留空而不是兜底",
       all(v is None for v in sig2.values()), str(sig2))
    ck("留空时把线索表交回给你", "由你按内容定" in " ".join(conf2.values()))

    # 封面：合同里冻的是**要插进文档的那张图**，不只是 cover.html
    ck("合同冻结封面图",
       bool(((run.get("contract") or {})["deliverables"]["doc"]).get("coverImage")))
    import publish as _pub
    ck("封面传 .html 会被拒（cover.html 是源，不是封面）",
       bool(_pub.cover_arg_errors(str(ROOT / "gold/doc-canvas/pulse-cover.html"))))
    ck("封面传合格的 jpg 放行",
       not _pub.cover_arg_errors(str(ROOT / "gold/doc-canvas/pulse-cover.jpg")))

    # 闭包逃逸：有合同时 --debug-package 必须被拒
    code, out = py("publish.py", "--run", str(tmp / "run.json"),
                   "--debug-package", cwd=tmp)
    ck("有合同时闭包逃逸开关被拒",
       code != 0 and "被拒绝" in out, out.splitlines()[0] if out else "")

    # 合同指纹：手改 run.json 会被戳穿
    r2 = json.loads((tmp / "run.json").read_text(encoding="utf-8"))
    r2["contract"]["artifactClass"] = "web"
    (tmp / "run2.json").write_text(json.dumps(r2, ensure_ascii=False), encoding="utf-8")
    code, out = py("publish.py", "--run", str(tmp / "run2.json"), cwd=tmp)
    ck("手改合同被指纹戳穿", "它被手改过" in out,
       next((ln.strip()[:70] for ln in out.splitlines() if "手改" in ln), ""))

    # ══ 这一轮的六条，每条一个断言 ══════════════════════

    # 封面：`--index` 这个 flag 在 lark-cli 里不存在，成功率 0%
    src = code_of(SC / "publish.py")
    ck("封面不再用不存在的 --index",
       '"--index"' not in src and "--selection-with-ellipsis" in src)
    # 锚点必须由脚本从 proposal 机械提取，不能让执行者自己想
    for pr in sorted((ROOT / "gold").glob("doc-*/*proposal*.xml")):
        ck(f"{pr.name} 能提取封面锚点", bool(_pub_anchor(pr)), str(_pub_anchor(pr)))

    # 封面**不再阻断交付** —— 上一版这道 BLOCK 配上那个不存在的 flag
    # 造出了死锁：FIX 提示让执行者去跑同一条必然失败的命令。
    dsrc = code_of(SC / "deliver.py")
    ck("封面缺失只披露不阻断",
       "⚠  这篇文档里没有封面图" in dsrc and "不出交付参数" not in dsrc)

    # 交付 prompt **落盘 + 给路径**，不再整段印在 stdout 上。
    # 「直接打印」这条上一轮成立的做法，被一个更硬的约束推翻了：
    # 超过几 KB 的输出会被截断成「当前消息过长」，被截掉的正是开头
    # 那个「从这里开始复制」的标记 —— 于是"整段复制"在执行时不成立。
    # 落盘之后读进来多少就是多少，没有截断这一环。
    ck("prompt 落盘并给出路径（不整段走 stdout）",
       "app-prompt.txt" in dsrc and "用 Read 读这个文件" in dsrc
       and "END —— 到这里为止都是 user_prompt" not in dsrc)
    ck("明写不许传文件路径给 app_builder（沙箱读不到本机文件）",
       "不要传文件路径给 app_builder" in dsrc)
    # 上限按「能不能被吐出来」标定：成功样本 20/28/30KB，失败样本 408KB。
    sys.path.insert(0, str(SC))
    import deliver as _d                                      # noqa: E402
    ck("内联上限标定在成功样本上沿，不是理论上限",
       _d.INLINE_CAP <= 80_000, f"INLINE_CAP={_d.INLINE_CAP}")
    # 判据落在 URL 自带的证据上，不落在域名 —— 唯一上传通路返回的就是那个域名。
    ck("临时凭据按签名/过期参数判，不按裸域名判",
       bool(_d.FRAGILE_HOST.search("https://x.com/a?x-signature=b"))
       and bool(_d.FRAGILE_HOST.search("https://p6-flow-imagex-sign.byteimg.com/a"))
       and not _d.FRAGILE_HOST.search("https://aka.doubaocdn.com/s/aFo31wr1SZ"))
    # 交完卡要回读核对：「发出去了」有对账，「发出去的是不是这一稿」此前零判据。
    ck("交卡后回读 app_id 核对图数", "app_id" in dsrc and "回读" in dsrc)
    # 成品页里已内联的 base64 要拆出来，否则 prompt 500KB 起步
    ck("拆成品页里的内联 base64", "DATA_URI" in dsrc and "b64decode" in dsrc)

    # 关键屏进 doc 是一条命令
    psrc = code_of(SC / "pack_img.py")
    ck("pack_img 有 --for-doc-screens", "--for-doc-screens" in psrc
       and "screens-figures.html" in psrc)
    ck("shoot.py screens 打印下一条命令",
       "--for-doc-screens" in code_of(SC / "shoot.py"))
    ck("合同打印「先成品页后 doc」的顺序",
       "两件必交有先后" in code_of(SC / "plan.py"))

    # 门的净变化为 0：新增一条必须删掉一条
    csrc = code_of(SC / "check.py")
    # 查行为不查源码：拿包内阳性对照跑一遍，必须真的 FAIL。
    es = ROOT / "tests" / "regressions" / "empty-screens" / "canvas.html"
    if es.is_file():
        _c, eo = py("check.py", "--url", str(es), "--profile", "doc")
        ck("空槽位阳性对照被 doc-screens-empty 抓到",
           any(ln.startswith(("✗ BLOCK", "· REPORT")) and "doc-screens-empty" in ln
               for ln in eo.splitlines()),
           next((ln.strip()[:80] for ln in eo.splitlines()
                 if "doc-screens-empty" in ln), "没报"))
    else:
        ck("空槽位阳性对照存在", False, str(es))
    ck("同时删掉 aes-no-real-imagery（与 asset-count 重叠）",
       "add('aes-no-real-imagery'" not in csrc)

    # 弹窗相对取景框，不是相对视口 —— 这是真实产物里出现过的缺陷
    asrc = (ROOT / "skeletons" / "app.html").read_text(encoding="utf-8")
    ck("骨架有弹窗原语且是 absolute",
       ".modal{position:absolute" in asrc and ".scrim{position:absolute" in asrc)

    # 交付保真：描述式 prompt（远短于成品 HTML）必须被拒
    ck("描述式 prompt 被拒",
       bool(_deliver_fidelity(tmp, run, "请做一个校园论坛 App 首页，暗色系，圆角卡片。")))
    ck("贴了完整 HTML 就放行",
       not _deliver_fidelity(tmp, run,
                             (tmp / run["contract"]["deliverables"]["product"]["path"])
                             .read_text(encoding="utf-8") + "x" * 400))

    # ══ 把链砍到跑得完。五条根因，每条一个断言 ══════════════
    import publish as _pub2
    import observe as _obs

    # `_hit` 按 basename 匹配 —— app/index.html 与 doc/index.html 撞车。
    # 实测后果：C5 在两次发布里都误报「门是按 web 跑的」，而收据里
    # app 那份明明是 app-screen。一条永远修不掉的报错会让执行者
    # 认定这条链有毛病 —— 那一轮它确实这么判了。
    peers = ("app/index.html", "doc/index.html")
    r_doc = [{"target": "doc/index.html", "profile": "web"}]
    r_app = [{"target": "app/index.html", "profile": "app-screen"}]
    ck("doc/index.html 的收据不再命中 app/index.html",
       not _pub2._hit(r_doc, "target", "app/index.html", peers))
    ck("精确路径仍然命中", _pub2._hit(r_app, "target", "app/index.html", peers))
    ck("绝对路径的收据也命中（执行者常传绝对路径）",
       _pub2._hit([{"target": "/tmp/w/app/index.html"}], "target",
                  "app/index.html", peers))
    ck("同名不唯一时不回落 basename",
       not _pub2._hit([{"target": "index.html"}], "target",
                      "app/index.html", peers))

    # observe 的入口形状：写错就整条拒绝 → 实测跑 7 次、收据 0 条。
    # 现在机械项脚本直接修完（守则 S23-2）。
    items, notes = _obs.normalize({"observations": [
        {"location": "首屏", "css": ".hero", "problem": "两块橙打架",
         "measure": {"n": 3}, "suggestion": "换黑白人像"}]})
    ok = (len(items) == 1 and items[0]["selector"] == ".hero"
          and items[0]["where"] == "首屏" and items[0]["what"] == "两块橙打架"
          and items[0]["fix"] == "换黑白人像" and items[0]["measure"] == {"count": 3})
    ck("形状/别名错误被自动修好", ok, str(items[:1]))
    ck("修了什么会说清楚", len(notes) >= 4, f"{len(notes)} 条")
    one, _ = _obs.normalize({"where": "x", "selector": "body", "what": "y",
                             "measure": {}, "fix": "z"})
    ck("单个对象被包成数组", len(one) == 1)
    # 查行为不查措辞（危险信号 17）：两条回执在不给 --min 时必须被受理，
    # 而不是被"至少 3 条"挡回来。
    two = tmp / "observed-two.json"
    two.write_text(json.dumps([
        {"where": "整页", "selector": "body", "what": "底色停在纯白",
         "measure": {"count": 1}, "fix": "换成微黄纸"},
        {"where": "整页", "selector": "html", "what": "没有一处影像",
         "measure": {"count": 1}, "fix": "首屏加满版底图"}], ensure_ascii=False),
        encoding="utf-8")
    _c, o_min = py("observe.py", "--url", str(ROOT / "gold/app-home/index.html"),
                   "--observed", str(two))
    ck("两条回执在默认 --min 下被受理", "只写了 2 条" not in o_min,
       o_min.splitlines()[0] if o_min else "")

    # **这一轮唯一算数的判据**：封面缺失 / 关键屏空 / 看图只有一轮时，
    # ship 仍然要把 doc 发出去。上一轮的实测是 0 张卡 ——
    # 用户拿到 0 个产物和拿到一个"少了封面的 doc"，差距是天壤之别。
    part = Path(tempfile.mkdtemp(prefix="ui-partial-"))
    py("plan.py", "--query", "做一个骑行 App，帮用户挑路线", "--dir", str(part), cwd=part)
    prun = json.loads((part / "run.json").read_text(encoding="utf-8"))
    pc = prun["contract"]["deliverables"]
    (part / "doc").mkdir(parents=True, exist_ok=True)
    (part / pc["doc"]["canvases"][0]).write_text("<!DOCTYPE html><html></html>",
                                                 encoding="utf-8")
    (part / pc["doc"]["proposal"]).write_text(
        "<title>t</title><p>正文</p>"
        f'<html5-block path="@{Path(pc["doc"]["canvases"][0]).name}"></html5-block>',
        encoding="utf-8")
    stop, gaps = _pub2.closures(prun, part)
    ck("只有 proposal + 一块画布时**不阻断**发布", not stop, str(stop[:1])[:120])
    ck("缺的东西全部进披露清单（封面/截图/看图/门/素材）",
       len(gaps) >= 5, f"{len(gaps)} 条：" + " | ".join(g.splitlines()[0][:22]
                                                       for g in gaps[:6]))
    ck("披露里点名了封面与看图",
       any("封面" in g for g in gaps) and any("看图" in g for g in gaps))
    # 阳性对照：把画布拿掉，必须重新变成阻断
    (part / pc["doc"]["canvases"][0]).unlink()
    stop2, _ = _pub2.closures(prun, part)
    ck("一块画布都没有时仍然阻断", bool(stop2), str(stop2[:1])[:80])

    # proposal 还是脚本生成的占位稿 —— 发出去客户会逐字读到【待填…】
    (part / pc["doc"]["canvases"][0]).write_text("<!DOCTYPE html><html></html>",
                                                 encoding="utf-8")
    (part / pc["doc"]["proposal"]).write_text(
        "<title>t</title><p>【待填：开场一段】</p>"
        f'<html5-block path="@{Path(pc["doc"]["canvases"][0]).name}"></html5-block>',
        encoding="utf-8")
    stop3, _ = _pub2.closures(prun, part)
    ck("占位稿 proposal 被拦下", any("待填" in s for s in stop3),
       str(stop3[:1])[:80])

    # 封面媒体插入的参数形态。两轮两个 bug 都出在这条命令上，
    # 而它以前只在真实发布路径上跑得到 —— 现在是纯函数，能被断言。
    cmd, cwd = _pub2.media_insert_cmd("D1", Path("/tmp/w/shots/cover.jpg"),
                                      "user", "锚点文本")
    fi = cmd[cmd.index("--file") + 1]
    ck("--file 传相对路径（lark-cli 拒绝绝对路径）",
       not fi.startswith("/") and fi.endswith("cover.jpg"), fi)
    ck("媒体插入在图片自己的目录里跑", str(cwd) == "/tmp/w/shots", str(cwd))
    ck("锚点仍然是 --selection-with-ellipsis --before",
       "--selection-with-ellipsis" in cmd and "--before" in cmd)

    # 编排：子脚本被 ui.py 调起时闭掉自己的"下一步"。
    # 守则 S24：一条命令的输出里只能有一个 NEXT，
    # 互斥指令并存时执行者走**先出现的那条**。
    solo = Path(tempfile.mkdtemp(prefix="ui-next-"))
    _c, o_solo = py("plan.py", "--query", "做一个骑行 App", "--dir", str(solo), cwd=solo)
    orch = Path(tempfile.mkdtemp(prefix="ui-next2-"))
    env = dict(__import__("os").environ, UI_ORCHESTRATED="1")
    r = subprocess.run([sys.executable, str(SC / "plan.py"), "--query", "做一个骑行 App",
                        "--dir", str(orch)], capture_output=True, text=True,
                       cwd=orch, env=env, timeout=300)
    ck("单跑 plan.py 仍然给下一步", "下一步" in o_solo)
    ck("被编排时子脚本不再给下一步", "下一步" not in (r.stdout + r.stderr))
    ck("工艺照印（必读五件套没被一起关掉）",
       "award-mechanisms" in r.stdout and "参考区间" in r.stdout)

    # 四条命令各自只出一个 NEXT
    step1 = Path(tempfile.mkdtemp(prefix="ui-start-"))
    code, o1 = py("ui.py", "start", "--query", "咖啡点单小程序首页改版", "--dir", str(step1))
    ck("ui.py start 跑通且只有一个 NEXT",
       code == 0 and o1.count("NEXT ▸") == 1, f"exit={code} NEXT={o1.count('NEXT ▸')}")
    ck("start 一条命令做完合同 + 签名 + 骨架",
       (step1 / "run.json").is_file() and (step1 / "style.json").is_file()
       and any((step1).rglob("index.html")))
    code, o2 = py("ui.py", "ship", "--run", str(step1 / "run.json"), cwd=step1)
    ck("ship 在盘上没东西时给的是一个 NEXT，不是死路",
       o2.count("NEXT ▸") == 1 and "ui.py" in o2, f"NEXT={o2.count('NEXT ▸')}")

    # ══ 两条真实用户反馈，四组断言 ══════════════════════
    # 案例 A：一份「响应式产品官网」的关键界面节被做成三台手机
    # 案例 B：门连报 8 次（图取不到 + 文字重叠），一次没改就交付了

    # 载体分叉。**这条用例在 换了样本**：那三步现在由 `ui.py ship`
    # 自动做完（截图 → 压缩 → data URI → 原地写进画布的标记块），
    # 所以合同里不该再印任何让人手跑的证据命令 ——
    # 打印让粘贴也算隔一步，而隔一步的事情不会自己发生。
    # 旧断言查的是"印出来的命令对不对"，那个语义已经作废，整条换掉。
    for q, cls, want in [
            ("为一款低能耗空气传感器设计响应式产品官网", "web", "通栏长图"),
            ("为大学生设计一个校园论坛社交app首页", "mobile", "界面状态")]:
        d = Path(tempfile.mkdtemp(prefix="ui-carrier-"))
        _c, o = py("plan.py", "--query", q, "--dir", str(d), cwd=d)
        seg = o.split("两件必交有先后")[-1].split("那一节不放素材照片")[0]
        cmds = [x.strip() for x in seg.splitlines() if "python3 " in x]
        ck(f"{cls} 合同不再印手跑的证据命令（ship 自己做完）",
           not cmds, " / ".join(c[:52] for c in cmds) or "0 条")
        ck(f"{cls} 合同说清了这个载体的版面证据是什么形态",
           want in seg and "KEY-SCREENS" in seg,
           seg.strip().splitlines()[1][:70] if seg.strip() else "")

    # 宽屏截图不许进手机机身位。判据是**源图形状**，不靠调用方申报。
    import pack_img as _pk
    be = _pk.Backend
    if be.kind != "none":
        wide = Path(tempfile.mkdtemp(prefix="ui-wide-"))
        try:
            from PIL import Image
            Image.new("RGB", (1440, 900), "white").save(wide / "p01.png")
            Image.new("RGB", (780, 1688), "white").save(wide / "p02.png")
        except Exception:
            pass
        if (wide / "p01.png").is_file():
            code, o = py("pack_img.py", "--for-doc-screens", str(wide),
                         "--out", str(wide / "out"))
            ck("宽屏截图进 --for-doc-screens 被拒绝",
               code != 0 and "--slot plate" in o,
               o.splitlines()[0][:80] if o else "")
            only_tall = Path(tempfile.mkdtemp(prefix="ui-tall-"))
            Image.new("RGB", (780, 1688), "white").save(only_tall / "p01.png")
            code, o = py("pack_img.py", "--for-doc-screens", str(only_tall),
                         "--out", str(only_tall / "out"))
            ck("竖屏关键屏仍然照常出图", code == 0, o.splitlines()[0][:60])

    # 成品页的外链图（宿主搜索地址在交付端一定碎）
    remote = Path(tempfile.mkdtemp(prefix="ui-remote-")) / "index.html"
    remote.write_text(
        '<!DOCTYPE html><html><body><main style="height:900px">'
        '<img src="https://p3-doubao-search-sign.byteimg.com/x.jpeg?x-signature=a" '
        'alt="a" width="300" height="200">'
        '<p style="font-size:16px;color:#111">正文</p></main></body></html>',
        encoding="utf-8")
    _c, o = py("check.py", "--url", str(remote), "--profile", "web")
    ck("成品页引用外链图被报出",
       any(ln.startswith("· REPORT") and "img-remote-src" in ln
           for ln in o.splitlines()),
       next((ln.strip()[:70] for ln in o.splitlines() if "img-remote-src" in ln), "没报"))

    # doc 画布里手画的 SVG 示意图
    fake = Path(tempfile.mkdtemp(prefix="ui-fake-")) / "canvas.html"
    fake.write_text(
        '<!DOCTYPE html><html><head><style>.cv{max-width:900px}</style></head><body>'
        '<div class="cv"><p>正文</p>'
        "<img src=\"data:image/svg+xml,%3Csvg%3E%3Crect/%3E%3C/svg%3E\" alt=\"竞品\">"
        '</div></body></html>', encoding="utf-8")
    _c, o = py("check.py", "--canvas", str(fake))
    ck("画布里手画的 SVG 示意图被报出",
       any(ln.startswith(("· REPORT", "✗ BLOCK")) and "doc-fake-figure" in ln
           for ln in o.splitlines()),
       next((ln.strip()[:70] for ln in o.splitlines() if "doc-fake-figure" in ln), "没报"))
    # 阴性对照：inline <svg> 图标不受影响（gold 全部走这条路）
    icon = fake.with_name("icon.html")
    icon.write_text(
        '<!DOCTYPE html><html><head><style>.cv{max-width:900px}</style></head><body>'
        '<div class="cv"><p>正文</p><svg viewBox="0 0 24 24"><path d="M0 0h24v24H0z"/></svg>'
        '</div></body></html>', encoding="utf-8")
    _c, o = py("check.py", "--canvas", str(icon))
    ck("inline <svg> 图标不被误伤", "doc-fake-figure" not in o or "REPORT 0" in o,
       next((ln.strip()[:60] for ln in o.splitlines() if "通过｜" in ln), ""))

    # 有 BLOCK 时 review 必须**停在改稿上**，不能继续推进到看图/做 doc。
    # 这一条是案例 B 的直接对策：那一轮门连报 8 次，链照走，稿照交。
    blk = Path(tempfile.mkdtemp(prefix="ui-block-"))
    py("plan.py", "--query", "为大学生设计一个校园论坛社交app首页",
       "--dir", str(blk), cwd=blk)
    brun = json.loads((blk / "run.json").read_text(encoding="utf-8"))
    bp = blk / brun["contract"]["deliverables"]["product"]["path"]
    bp.parent.mkdir(parents=True, exist_ok=True)
    bp.write_text(
        '<!DOCTYPE html><html><body><main style="height:844px">'
        '<img src="https://p3-doubao-search-sign.byteimg.com/nope.jpeg" alt="x" '
        'width="300" height="200"><p style="font-size:16px">内容</p>'
        "</main></body></html>", encoding="utf-8")
    code, o = py("ui.py", "review", "--run", str(blk / "run.json"), cwd=blk)
    tail = o.split("NEXT ▸")[-1]
    ck("有 BLOCK 时 review 停在改稿上",
       code != 0 and "BLOCK" in tail and "ui.py doc" not in tail,
       tail.strip().splitlines()[0][:70] if tail.strip() else "没有 NEXT")
    ck("停下来时仍然只有一个 NEXT", o.count("NEXT ▸") == 1,
       f"{o.count('NEXT ▸')} 个")

    # 下载失败留下的空文件必须被删掉（已知失败条件：三个 2 字节的 .jpg）
    import fetch_photos as _fp
    fp_dir = Path(tempfile.mkdtemp(prefix="ui-fp-"))
    (fp_dir / "picks.json").write_text('{"hero": ["0", 1200]}', encoding="utf-8")
    old_cdn = _fp.CDN
    try:
        _fp.CDN = "file:///nonexistent-{id}-{w}.jpg"      # 必然失败，且会落空文件
        _fp.cmd_pick(argparse.Namespace(map=str(fp_dir / "picks.json"),
                                        out=str(fp_dir / "assets")))
    except SystemExit:
        pass
    finally:
        _fp.CDN = old_cdn
    left = list((fp_dir / "assets").glob("*")) if (fp_dir / "assets").is_dir() else []
    ck("下载失败不留空文件", not left, str([f.name for f in left]))

    # doc 画布要文件路径，不是目录（传目录会产出没人要的 doc/index.html）
    sk_dir = Path(tempfile.mkdtemp(prefix="ui-sk-"))
    code, o = py("skeleton.py", "doc", str(sk_dir / "doc"), "--title", "T",
                 "--persona", "paper=#fff,ink=#111,muted=#777,hairline=1px,soft=#eee,"
                 "font=Inter,rule=none,numfont=700 20px Inter,radius=2px,"
                 "bodysize=15px,lead=1.6")
    ck("doc 传目录被拒绝，不产出孤儿 index.html",
       code != 0 and not (sk_dir / "doc" / "index.html").is_file(),
       o.splitlines()[0][:70] if o else "")


def r31_browser() -> None:
    """里要真开浏览器才验得了的那几条。"""
    real = ROOT / "tests" / "regressions"

    # content-under-dock(app-screen) 已删。阳性对照是方案附录 A 的
    # 最小复现页：它是**正确**的布局（#flow 留了 90px，底栏 64px），
    # 而 .publish-modal 用 translateY(100%) 完全移出了屏幕。
    # 上一版在它身上 BLOCK，且 detail 给的是两个内容块的类名 ——
    # 一条真实 trace 在这上面死磕 15 分 14 秒。
    f = real / "fixed-dock-app" / "index.html"
    code, out = py("check.py", "--url", str(f), "--profile", "app-screen")
    cud = [ln for ln in out.splitlines() if "content-under-dock" in ln]
    dock = [ln for ln in out.splitlines() if "dock-reserved" in ln]
    ck("content-under-dock 不再出现在 app-screen 的输出里", not cud,
       cud[0].strip()[:80] if cud else "0 处")
    ck("而 dock-reserved 仍然 PASS（真的「滚到底还压着」由它管）",
       bool(dock) and dock[0].startswith("  PASS"),
       dock[0].strip()[:70] if dock else "这道门不见了")
    ck("screen-fit 已删（frame 兜底到 body，判据恒真）",
       "screen-fit" not in out)

    # -O/P · frame-intact 的双向标定。
    # 阳性：把 gold/app-home 的取景框去掉 → 必须 FAIL
    # 特异性：一份**没有 TabBar、没有状态栏**、但版心 <=520px 的登录页 → 必须 PASS
    # （v3 想查 .stage/#app/.statusbar/.tabbar 四个类名，
    # 那是对一份骨架的过拟合，这一条在它身上必然红）
    src = (ROOT / "gold" / "app-home" / "index.html").read_text(encoding="utf-8")
    broke = Path(tempfile.mkdtemp()) / "index.html"
    broke.write_text(
        src.replace("#app{", "#app{width:100%!important;max-width:none!important;")
           .replace(".stage{", ".stage{display:block!important;"), encoding="utf-8")
    code, out = py("check.py", "--url", str(broke), "--profile", "app-screen")
    line = next((ln for ln in out.splitlines() if "frame-intact" in ln), "")
    ck("取景框被拆掉 → frame-intact FAIL", line.startswith("✗ BLOCK"),
       line.strip()[:96] or "这道门没跑")
    ck("FAIL 时给出可粘贴的恢复片段（S13 保底分岔）",
       ".stage{position:fixed" in out and "#app{" in out)
    code, out = py("check.py", "--url",
                   str(real / "frameless-login" / "index.html"), "--profile", "h5")
    line = next((ln for ln in out.splitlines() if "frame-intact" in ln), "")
    ck("没有 TabBar/状态栏但版心 <=520px 的登录页 → frame-intact PASS",
       line.startswith("  PASS"), line.strip()[:96] or "这道门没跑")

    # 四种新载体：**没有 gold 就不许上线**这条准入我做不到
    # （包里还没有这四种被认可过的真实产物），所以退一步用可证伪的替代：
    # 每种新载体的骨架必须在自己的 profile 下**只剩 placeholder 一条 BLOCK**
    # （骨架有 TODO 是对的，那正是它要你去填的东西）。
    # 这不等于标定 —— 它只保证"门关停表没有关错、也没有漏关"。
    # **补 gold 之前，不要给这四种载体加任何新门。**
    # **这四种载体现在有 gold 了**（补的四份，还原自真实项目的设计终稿）。
    # 所以准入判据从"骨架自检"升级成两条：
    # ① 对口 gold 必须存在且过全部 BLOCK 门（在上面的门标定循环里）
    # ② 骨架自己只剩 placeholder 一条 BLOCK（TODO 是它该有的）
    GOLD_OF_SURFACE = {"web-console": "console-api", "spec-board": "board-flow",
                       "big-screen": "screen-hotan", "long-image": "longimg-summit"}
    for f, prof in [("console.html", "web-console"), ("board.html", "spec-board"),
                    ("screen.html", "big-screen"), ("longimg.html", "long-image")]:
        g = ROOT / "gold" / GOLD_OF_SURFACE[prof] / "index.html"
        ck(f"{prof} 有对口 gold（没有 gold 不许给它加门）", g.is_file(),
           str(g.relative_to(ROOT)))
        code, out = py("check.py", "--url", str(ROOT / "skeletons" / f),
                       "--profile", prof)
        blocks = {ln.split()[2] for ln in out.splitlines()
                  if ln.startswith("✗ BLOCK") and len(ln.split()) > 2}
        ck(f"{prof} 骨架只剩 placeholder 一条 BLOCK",
           blocks == {"placeholder"}, "、".join(sorted(blocks)) or "一条都没有（可疑）")
        ck(f"{prof} 印出了关掉了哪几条门（减法要可见）",
           "对这种载体不适用，已关掉" in out,
           next((ln for ln in out.splitlines() if "不适用" in ln), "")[:70])

    # text-invisible 补的 div 分支：一份 fixture 同时验两个方向。
    # 阳性：白底容器里的 div 继承了深底那套浅墨 —— 必须抓到（1.09:1）
    # 特异性：**包装型** div（自己没有文本节点，文字都在子元素里）—— 不许误伤
    # 这两半缺一不可：只做阳性会造出一整片假阳性，只做特异性等于没加这条。
    f = ROOT / "tests" / "regressions" / "div-text" / "index.html"
    code, out = py("check.py", "--url", str(f), "--profile", "web")
    hit = [ln for ln in out.splitlines()
           if "text-invisible" in ln and ln.startswith("✗ BLOCK")]
    ck("白字压白底的 div 被抓到（选择器里原本没有 div）",
       bool(hit) and "1.0" in (hit[0] if hit else ""),
       hit[0].strip()[-42:] if hit else "漏掉了 —— div 分支没生效")
    ck("包装型 div 不被误伤（只量自己有文本节点的元素）",
       len(hit) <= 1 and "包装型" not in (hit[0] if hit else ""),
       hit[0].strip()[-42:] if hit else "")

    # -L/M · 关键屏不许是 N 张同图。
    # 本机在包自己的骨架上复现过：`screens` 出 5 个文件、**1 个 sha256**。
    # 收据数的是文件个数，不是不同的图 ——「目标集合为空必须 FAIL」
    # 缺的那条对偶是「目标集合全都一样也必须 FAIL」。
    # 直接的改前改后：同一份 skeletons/app.html，旧 `screens` 出 **1 个 sha256**
    #（本机复现过：5 个文件、770fe3cc… 一个哈希）。
    d = Path(tempfile.mkdtemp())
    code, out = py("shoot.py", "states", str(ROOT / "skeletons" / "app.html"),
                   str(d), "5")
    shots = sorted(d.glob("*.png"))
    shas = {_hash(p) for p in shots}
    ck("skeletons/app.html：旧 screens 出 1 个 sha256，现在 >=4 个",
       len(shots) == 5 and len(shas) >= 4,
       f"{len(shots)} 张 / {len(shas)} 个不同 sha256")
    ck("走的是声明式通路，且通路印出来了（不静默）",
       "关键屏通路" in out and "manifest" in out, out.splitlines()[0][:70])
    # 骨架的"卡片展开"里还没有内容，所以它和首页确实长一样 ——
    # 这时门要报，而且报的话要**指出是哪两张**、给出两种成因。
    ck("有重复时点名是哪两张并给两种成因（不是笼统一句「选择器不对」）",
       len(shas) == 5 or ("完全相同的是" in out and "选择器不对" in out
                          and "状态本身是空的" in out),
       "无重复" if len(shas) == 5 else "报了并给了成因")
    # 真产物上（gold 有 10 屏）必须张张不同
    d3 = Path(tempfile.mkdtemp())
    py("shoot.py", "states", str(ROOT / "gold" / "h5-qq2026" / "index.html"),
       str(d3), "5")
    s3 = {_hash(p) for p in sorted(d3.glob("*.png"))}
    ck("gold/h5-qq2026 出 5 张张张不同",
       len(list(d3.glob("*.png"))) == 5 and len(s3) == 5,
       f"{len(list(d3.glob('*.png')))} 张 / {len(s3)} 个不同")
    # 降级链：把声明删掉，退回滚动兜底；这个页面不滚 → 必须报重复并给可粘贴修法
    nodecl = d / "nodecl.html"
    t = (ROOT / "skeletons" / "app.html").read_text(encoding="utf-8")
    nodecl.write_text(t.split("window.__UI_CAPTURE__")[0] + "</script></body></html>",
                      encoding="utf-8")
    d2 = Path(tempfile.mkdtemp())
    code, out = py("shoot.py", "states", str(nodecl), str(d2), "5")
    shas2 = {_hash(p) for p in sorted(d2.glob("*.png"))}
    ck("删掉声明 → 退回滚动兜底并印出用了哪一级",
       "window-scroll" in out or "screen-scroll" in out, out.splitlines()[0][:70])
    ck("兜底出重复图时报错，且给的是**可粘贴的修法**（S13）",
       len(shas2) == len(list(d2.glob("*.png"))) or
       ("__UI_CAPTURE__" in out and "完全相同的是" in out),
       f"{len(shas2)} 个不同 sha256")


def _hash(p: Path) -> str:
    import hashlib
    return hashlib.sha256(p.read_bytes()).hexdigest()


def gates() -> None:
    """门的标定：跑 gold 零报警，跑已知坏稿要报出来。"""
    # 反向：gold 必须过全部 BLOCK 门，且审美判据零报警（的一半）
    # h5-cycle 是第三份 gold：满版照片 + 暗场 + 文字压上面。
    # 它和 h5-qq2026（零照片、全 CSS 手绘）证明的是两条不同的路，两条都要不报警。
    # app-home 是 补的第四份：**产品界面原型**。
    # 这一形态在此之前没有任何样本，而 prototype-not-deck 是 BLOCK ——
    # 一条没有正样本的 BLOCK 门是不能上线的，它的阈值无从标定。
    # 把后四份补进来之后，**门第一次在这四种载体的真产物上被执行过**。
    # 允许的已知 REPORT 写在这里，逐条带理由 —— 不许无声扩大：
    # longimg-summit / asset-count
    # 这份还原稿的礼品与人像是手绘 SVG，而原稿是 12 张实拍。
    # **那条 REPORT 是对的**，留着不修；把阈值调低去迁就一份还原稿，
    # 等于把尺子拧弯来量自己。
    KNOWN_REPORT = {("longimg-summit", "asset-count")}
    for name, prof, vp in [("web-pulse", "web", None), ("h5-qq2026", "h5", None),
                           ("h5-cycle", "h5", None), ("app-home", "app-screen", None),
                           ("console-api", "web-console", None),
                           ("screen-hotan", "big-screen", "4001x2251"),
                           ("board-flow", "spec-board", "3400x760"),
                           ("longimg-summit", "long-image", "750x4200")]:
        srv = Server(ROOT / "gold" / name)
        try:
            args = [sys.executable, str(SC / "check.py"), "--url", srv.url,
                    "--profile", prof, "--aesthetic"]
            if vp:
                args += ["--viewport", vp]
            code, out = sh(args)
            tail = [ln for ln in out.splitlines() if "通过｜" in ln]
            ck(f"gold/{name} 无 BLOCK（门标定）", code == 0, tail[-1] if tail else out[-200:])
            fired = {ln.split()[2] for ln in out.splitlines()
                     if ln.startswith("· REPORT") and len(ln.split()) > 2}
            extra = {c for c in fired if (name, c) not in KNOWN_REPORT}
            ck(f"gold/{name} 审美判据无新报警", not extra,
               "、".join(sorted(extra)) or
               (f"只剩 {len(fired)} 条已知项" if fired else "零报警"))
        finally:
            srv.close()

    # 只挑画布，不要把封面页也当画布跑 —— 封面是一张 16:9 的图，不是窄栏排版
    canvases = sorted((ROOT / "gold").glob("doc-*/*canvas*.html"))
    ck("gold 的 doc 画布 >=6 份（三份方案 × 上下篇）", len(canvases) >= 6,
       f"{len(canvases)} 份")
    for c in canvases:
        # R19/R20/R21 都在这一条里：版面工艺六条门跑 gold 必须零报警
        code, out = py("check.py", "--url", str(c), "--profile", "doc")
        tail = [ln for ln in out.splitlines() if "通过｜" in ln]
        ck(f"gold/{c.name} 版面与排版判据零报警",
           "BLOCK 0｜REPORT 0" in (tail[-1] if tail else ""), tail[-1] if tail else "")
    # 汇报口吻：gold 是正例。
    # **按"整份 doc"量，不按单块画布量** —— 上篇/下篇各占一半，
    # 「下一步」天然只在下篇里。第一版按单块量，六份 gold 全部报警，
    # 那是判据的对象错了，不是稿错了。
    # # 允许两条已知 REPORT，理由写在这里，不许无声扩大：
    # doc-has-素材与数据说明   骑不骑那份没有这一节。**这是稿的真实缺口**——
    # "虚构数据未标注来源"在评测里是一票否决，
    # 而这几份 gold 做在这条要求之前。
    # doc-data-honest          QQ 年度盘点里 10 组数字是为演示编的，没标"示例数据"。
    # 两条都是 REPORT（不阻断），留着是因为它们**指出的是真问题**；
    # 不改 gold 是因为改它会连带动到人格指纹的标定基准。
    KNOWN = {"doc-has-素材与数据说明", "doc-data-honest"}
    for pair in [sorted((ROOT / "gold" / d).glob("*canvas*.html"))
                 for d in ("doc-canvas", "doc-cycle") if (ROOT / "gold" / d).is_dir()]:
        for i in range(0, len(pair), 2):
            grp = [str(x) for x in pair[i:i + 2]]
            if not grp:
                continue
            code, out = py("check.py", "--canvas", *grp, "--doc-voice")
            fired = {ln.split()[2] for ln in out.splitlines()
                     if ln.startswith(("✗ BLOCK", "· REPORT")) and len(ln.split()) > 2}
            ck(f"gold {Path(grp[0]).name} 那一份汇报口吻无新报警",
               not (fired - KNOWN), "、".join(sorted(fired - KNOWN)) or
               f"只剩 {len(fired & KNOWN)} 条已知项")

    # ── –版面工艺门必须真的能抓到问题 ──────────────────
    # 一条门没有阳性对照就是摆设。tests/messy-canvas 复刻的是
    # "所有旧门都绿、用户一眼说乱"的那一版。
    messy = ROOT / "tests" / "messy-canvas" / "index.html"
    if messy.is_file():
        code, out = py("check.py", "--url", str(messy), "--profile", "doc")
        fired = [ln for ln in out.splitlines()
                 if ln.startswith(("✗ BLOCK", "· REPORT"))]
        for g in ("orphan-row", "reading-gutter", "gutter-balance",
                  "sample-wrap", "grid-declared-vs-actual"):
            ck(f"版面工艺门抓得到 {g}",
               any(ln.split()[2].startswith(g) for ln in fired),
               " / ".join(ln.split()[2][:26] for ln in fired))
        code, out = py("check.py", "--canvas", str(messy))
        ck("转义残留（%% 让整条声明被静默丢弃）被抓到",
           "css-escape-leftover" in out and "REPORT" in out)
    else:
        ck("版面工艺的阳性对照存在", False)

    # ── 试跑反馈的四条，全部拿真实产物当阳性对照 ────────────
    real = ROOT / "tests" / "regressions"
    # 判据必须查**那道门真的 FAIL 了**，不能只查门名出现在输出里 ——
    # 门名在 PASS 行上也会打印。实测：blurry 这份阳性对照里的 base64
    # 根本解码不了（naturalWidth=0），img-upscaled 从来没在它身上 FAIL 过，
    # 而这条断言**一直是绿的**。一条永远绿的断言比没有断言更危险。
    for name, args, want in [
        ("图被放大（文档里图片看不清）",
         ["--url", str(real / "blurry" / "canvas.html"), "--profile", "doc"], "img-upscaled"),
        ("长图高宽比超标",
         ["--url", str(real / "blurry" / "canvas.html"), "--profile", "doc"],
         "doc-image-aspect"),
        ("竖图占满通栏（该用 .device）",
         ["--url", str(real / "blurry" / "canvas.html"), "--profile", "doc"],
         "device-scale"),
        ("画布图不是 data URI（裂图）",
         ["--canvas", str(real / "broken-img" / "canvas.html")], "canvas-img-embedded"),
        ("常驻底栏没贴底",
         ["--url", str(real / "floating-dock" / "index.html"), "--profile", "h5"],
         "dock-at-bottom"),
        ("正文贴着版心边（官网也会犯）",
         ["--url", str(real / "flush-text" / "index.html"), "--profile", "web"],
         "reading-gutter"),
    ]:
        f = Path(args[1])
        if not f.is_file():
            ck(name + " 的阳性对照存在", False, str(f))
            continue
        code, out = py("check.py", *args)
        fired = [ln for ln in out.splitlines()
                 if ln.startswith(("✗ BLOCK", "· REPORT")) and want in ln]
        ck(name, bool(fired), (fired[0].strip()[:90] if fired
                               else "这道门在阳性对照上没有 FAIL —— 断言是空的"))

    # 本地路径的 <img href> 必须被 preflight 拦下
    bad = ROOT / "tests" / "bad-proposal" / "proposal.xml"
    if bad.is_file():
        code, out = py("publish.py", "--proposal", str(bad), "--debug-package")
        ck("preflight 拦下 <img href=本地路径>",
           code != 0 and "静默丢弃" in out, out.splitlines()[0] if out else "")
        cmds = [ln.strip() for ln in out.splitlines() if ln.strip().startswith(("python3", "lark-cli"))]
        ck("FIX 给的是 publish.py --cover，不再让你手跑 media-insert",
           any("--cover" in c for c in cmds)
           and not any("media-insert" in c for c in cmds),
           " / ".join(c[:52] for c in cmds[:3]))
    else:
        ck("的阳性对照存在", False)

    # gold 自己的 proposal 不能带着这个 bug
    sys.path.insert(0, str(SC))
    from publish import preflight  # noqa: E402
    for pr in sorted((ROOT / "gold").glob("doc-*/*proposal*.xml")):
        ck(f"gold/{pr.name} 过 preflight", not preflight(pr), str(preflight(pr))[:110])

    # ── 版式通用性：参考库里的三种正当移动端形态不许被门判死 ──────
    # 要求：移动端骨架要足够通用，覆盖这些形态 ——
    # 移动端的案例，看看是否都能适配」。看完 269 份参考稿，挑了三种
    # 结构上最不像 gold/app-home 的做成样本 —— 门判死正当形态就是门错。
    # 首轮实测这三份共报了 6 处误伤，全部是门的问题，已逐条改掉：
    # reading-gutter   排行榜每行 14 字 → 目标集合为空 → 强制 FAIL（门槛 30 字太高）
    # 多通路           叫车页只有点击，键盘翻页对它没有意义（只在多单元时才该查）
    # 副作用反馈       纯浏览页没有分享/收藏这类动作，不该要求 toast
    # asset-count      排行榜的 12 个小头像被 3% 面积门槛全筛掉
    # dock-reserved    地图页的上浮面板被当成常驻底栏
    # minVisualAssets  产品界面靠列表和数据，要 8 个满版素材只会逼出装饰图
    for name, why in [("a-hero-detail", "顶部大图 + 上浮面板 + 通栏 CTA（无 tab）"),
                      ("b-map-sheet", "全屏地图 + bottom sheet（主操作不在拇指区外）"),
                      ("c-dense-list", "密集排行榜（一屏十几行、几乎无图）")]:
        f = ROOT / "tests" / "archetypes" / f"{name}.html"
        if not f.is_file():
            ck(f"形态样本存在 {name}", False, str(f))
            continue
        code, out = py("check.py", "--url", str(f), "--profile", "app-screen")
        tail = [ln for ln in out.splitlines() if "通过｜" in ln]
        ck(f"正当形态不被判死：{why}",
           "BLOCK 0｜REPORT 0" in (tail[-1] if tail else ""), tail[-1] if tail else out[-160:])

    case = ROOT / "tests" / "case79"
    if not case.is_file() and not (case / "index.html").is_file():
        ck("低分参照样本 回归样本存在", False)
        return

    # R1 · 按钮重叠：用户亲眼看到的缺陷必须被报出来
    code, out = py("check.py", "--url", str(case / "index.html"), "--profile", "app-screen",
                   "--aesthetic")
    ck("R1 低分参照样本 的元素重叠被报出", "element-overlap" in out and "BLOCK" in out,
       next((ln.strip() for ln in out.splitlines() if "element-overlap" in ln), ""))
    # 另一半：坏稿要报够
    n_rep = len([ln for ln in out.splitlines()
                 if ln.startswith("· REPORT") and ln.split()[2].startswith(("aes-", "asset"))])
    ck("低分参照样本 至少报 3 条审美判据", n_rep >= 3, f"{n_rep} 条")

    # R3 · 空集必 FAIL：拿没有 .screen 的页面跑 h5 profile
    code, out = py("check.py", "--url", str(case / "index.html"), "--profile", "h5")
    line = next((ln for ln in out.splitlines() if "screen-height" in ln), "")
    ck("R3 目标集合为空时 FAIL 而不是 PASS",
       "BLOCK" in line and "目标集合为空" in line, line.strip())

    # R4 · shoot 不崩：外链字体 + 无限动画 + setInterval + 大 base64 也要出图
    hostile = ROOT / "tests" / "hostile" / "index.html"
    if hostile.is_file():
        out_png = Path(tempfile.mkdtemp()) / "h.png"
        code, out = py("shoot.py", "full", str(hostile), str(out_png), "1440", "900")
        ck("R4 敌意页面也能截出图", out_png.is_file() and out_png.stat().st_size > 5000,
           f"exit={code}")
    else:
        ck("R4 敌意样本存在", False)


def assertions() -> None:
    """正向：每一份参照案例都要过它自己的任务级断言。

    每份断言只写**这个载体独有**的那几条 —— 通用的几何与可读性由门去管。
    断言里的判据都对着同目录 `rubric.md` 右边那一列（扣分判断）写：
    知道会怎么扣分，比知道满分长什么样更有用。
    """
    for name in ("web-pulse", "h5-qq2026", "app-home",
                 "console-api", "screen-hotan", "board-flow", "longimg-summit"):
        f = ROOT / "gold" / name / "assertions.py"
        if not f.is_file():
            ck(f"gold/{name} 断言存在", False)
            continue
        srv = Server(ROOT / "gold" / name)
        try:
            src = f.read_text(encoding="utf-8")
            patched = _re.sub(r'URL\s*=\s*"[^"]+"', f'URL = "{srv.url}"', src, count=1)
            tmp = f.with_name("_selftest_tmp.py")
            tmp.write_text(patched, encoding="utf-8")
            code, out = sh([sys.executable, str(tmp)])
            tmp.unlink(missing_ok=True)
            tail = [ln for ln in out.splitlines() if "通过" in ln]
            ck(f"gold/{name} 任务级断言全通过", code == 0,
               tail[-1] if tail else out[-200:])
        finally:
            srv.close()


# ── 包里只允许存在三种人：执行者、用户、产物受众 ────────────────
# 维护者、调试者、历史反馈者必须完全隐身。
# 判据是可机械判定的七类痕迹；命中就是没达标。
#
# 为什么要有这道门：靠自觉写不出「不带轮次号」的注释。
# 而这些痕迹不只是风格问题 —— 其中「邀请执行者改这个包」那一类，
# 会在门失败时被打印给执行者看，等于授权它去改判据。
# 「用户」指本轮下达指令的人时是合法的（`用户点名了就照他说的`）；
# 只有把它当成历史反馈者或产品使用者时才是泄漏。所以只收不含歧义的那几种写法。
ROLE_LEAK = _re.compile(
    r"(?<![A-Za-z0-9+/])R(?:1[0-9]|2[0-9]|3[0-9])(?![A-Za-z0-9+/=])"   # 轮次号
    r"|case-\d+|trace[ -]\d+"                                          # 调试样本/trace 编号
    r"|用户原话[：:「]|用户的原话"                                      # 写死的历史引语
    r"|用户(?:说|反馈|判为|直接指出|亲眼|认可|判死|点开)"               # 历史反馈者/使用者
    r"|上一版|上一轮|上一代|这一轮|历来"                                # 版本对比
    r"|真实事故|真实任务|真实产出|翻车|踩过|事故史"                     # 事故叙事
    r"|改门不改稿|selftest|改这个包|改完门|标定过|误伤")                # 邀请改包
# 三类按**路径**豁免，不按词豁免：
#   gold/**       产物正文本身，是给汇报受众看的方案，里面的"我们"是乙方
#   tests/**      测试夹具
#   本文件        维护侧工具，执行任务时永不调用；它提到自己的名字不是泄漏。
#                 代价是必须有另一条断言：**执行者会读到的文件里不许出现它**。
ROLE_EXEMPT = ("gold/", "tests/", "scripts/selftest.py")


def role_hits(p: Path) -> int:
    t = p.read_text(encoding="utf-8", errors="ignore")
    if len(t) > 1_500_000:
        return 0
    t = _re.sub(r'data:image/[^"\')]{200,}', "", t)      # 剥 base64，否则全是假阳性
    return len(ROLE_LEAK.findall(t))


def role_clean() -> None:
    bad = []
    for p in sorted(ROOT.rglob("*")):
        if not (p.is_file() and p.suffix in (".md", ".py", ".html", ".txt")):
            continue
        rel = str(p.relative_to(ROOT))
        if rel.startswith(ROLE_EXEMPT):
            continue
        n = role_hits(p)
        if n:
            bad.append(f"{rel}({n})")
    ck("包里读不到维护者、调试者与历史反馈者",
       not bad, "　".join(bad[:6]) + (f" …共 {len(bad)} 份" if len(bad) > 6 else ""))
    # 自检工具被豁免，那就必须保证**没有任何一条执行路径把执行者引向它** ——
    # 否则等于在运行时授权它去改这个包的判据。
    pointing = []
    for p2 in sorted(ROOT.rglob("*")):
        if not (p2.is_file() and p2.suffix in (".md", ".py", ".html")):
            continue
        rel2 = str(p2.relative_to(ROOT))
        if rel2.startswith(("tests/", "gold/")) or rel2 == "scripts/selftest.py":
            continue
        if "selftest" in p2.read_text(encoding="utf-8", errors="ignore"):
            pointing.append(rel2)
    ck("没有任何文件把执行者引向自检工具", not pointing, "　".join(pointing[:4]))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="跳过浏览器项")
    ap.add_argument("--relock", action="store_true",
                    help="重新给 craft/reference/gold/assets 上锁（显式动作）")
    ap.add_argument("--roles", action="store_true",
                    help="只列出还带着维护痕迹的文件")
    a = ap.parse_args()

    if a.roles:
        for p in sorted(ROOT.rglob("*")):
            if not (p.is_file() and p.suffix in (".md", ".py", ".html", ".txt")):
                continue
            rel = str(p.relative_to(ROOT))
            if rel.startswith(ROLE_EXEMPT):
                continue
            n = role_hits(p)
            if n:
                print(f"{n:>5}  {rel}")
        return 0

    if a.relock:
        m = aesthetic_manifest()
        LOCK.parent.mkdir(parents=True, exist_ok=True)
        LOCK.write_text(json.dumps(m, ensure_ascii=False, indent=1),
                        encoding="utf-8")
        print(f"审美资产已重新上锁：{len(m)} 份 → {LOCK.relative_to(ROOT)}")
        return 0

    aesthetic_lock()
    role_clean()
    structure()
    r31()
    if a.quick:
        return report()
    mechanisms()
    r31_browser()
    gates()
    assertions()
    return report()


def report() -> int:
    bad = [r for r in results if not r[1]]
    for n, ok, d in results:
        print(("  PASS  " if ok else "  FAIL  ") + n
              + (f"   → {d}" if d and not ok else (f"   ({d})" if d else "")))
    print(f"\n{len(results) - len(bad)}/{len(results)} 通过")
    if bad:
        print("\n有 FAIL。如果 FAIL 的是「gold 无 BLOCK」或「gold 零报警」，先怀疑门：\n"
              "  gold/ 里的产物是真的做出来并被验收通过的，门判死它们 = 门错了。\n"
              "  改门，不要改 gold —— 除非门指出的是一个真缺陷（这也发生过：\n"
              "  doc 画布的强调色小字实测 2.3:1，那次是稿错了）。")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
