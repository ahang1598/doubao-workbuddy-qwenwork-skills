#!/usr/bin/env python3
"""三条命令 —— 这个包的必经路径。

    python3 <SKILL>/scripts/ui.py brief  --query "<当前请求原文>"   ① 开工
    python3 <SKILL>/scripts/ui.py review --run <run.json>       ② 看自己（跑两次）
    python3 <SKILL>/scripts/ui.py ship   --run <run.json>       ③ 交付

为什么要有这个文件，一条实测就够了。

之前：**22 分 56 秒 / 103 次工具调用 / 产物 0 个。**
每一个 bug 都修对了（封面 API、交付 prompt、截图进 doc、发布一次报完），
但**一件事都没有删**。诚实路径需要 18 条脚本命令，
时间轴一眼能看见后果：**第一次尝试发布发生在第 18.4 分钟**，被拒；
之后只剩 4 分钟，第二次又被拒；会话结束，产物 0 个。

    步数是到达率的分母。判据的正确性乘以执行次数才是质量。
    前一个我一直在提高，后一个我一直在降低。

所以只做一件事：**不删判据，删步数。**
这里删的是**命令的种类**，
不是删闭环：`doc` 并进 `review`，由 `review` 按盘上的收据**自己认阶段**，
于是命令 4 → 3，而 Doc 在发布之前的那一次看图机会**一次没少**
（把可逆的检查与不可逆的发布合并，是 v3 差点犯下的回归）。

四条设计规矩，前三条是经验，第四条是量出来的：

1. **一次输出只能有一个 NEXT。** 子脚本被这里调起时（`UI_ORCHESTRATED=1`）
   闭掉自己的"下一步"，工艺照印。互斥指令并存时执行者走先出现的那条。
2. **每一步都能重跑，重跑不产生第二份东西。** `ship` 发过一次之后走 `--update`。
3. **失败要留下能继续的状态。** 拿不到的前置条件不设；
   拦得住的只有"盘上没有可发的东西"，其余一律发完再披露。
4. **合同必须在每条命令上重印，而且要活得过管道过滤。**
   实测：宿主在 83 分钟里压缩了 6 次上下文，压缩存档**丢弃几何与阈值**；
   同一段 trace 里 28 次 ui.py 调用有 16 次（57%）带 `| grep` 或 `| tail`，
   最短 `tail -20`。所以横幅 <=10 行、紧贴 NEXT，且配一条输出自适应
   ——**不让输出瘦身，横幅就会被 grep 掉**。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import runstate  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SC = ROOT / "scripts"
BAR = "─" * 70

# 各 profile 的取景尺寸。和 check.py 的 PROFILES 同源，改一处要对另一处。
VIEW = {"web": (1440, 900), "h5": (390, 844), "app-screen": (390, 844),
        "doc": (698, 900), "web-console": (1440, 900), "spec-board": (1600, 1000),
        "big-screen": (1920, 1080), "long-image": (750, 1200)}
SKELETON_OF = {"产品界面": "app", "单向叙事": "h5", "互动生成器": "h5"}
# 逐个界面状态截图只对"有状态"的载体成立。
# 大屏不滚、展板横向、长图单栏 —— 它们只截整页。
MULTI_STATE = ("h5", "app-screen", "web-console")

# 所有指向本包命令的字符串**只能从这里生成**。
# 实测：`need_run` 那条 NEXT 若印裸相对路径 `python3 scripts/ui.py start`，
# 而模型必须 cd 进包目录才跑得动它 —— 于是产物落在安装目录里，
# 被另一个会话连同合同一起清空。**印出来的命令必须自带落点。**
RUN_ARG = ""


def ui_cmd(subcmd: str, *extra: str) -> str:
    parts = [f"python3 {SC / 'ui.py'}", subcmd, *extra]
    if RUN_ARG:
        parts.append(RUN_ARG)
    return " ".join(x for x in parts if x)


# ── 基础设施 ────────────────────────────────────────────────
def sub(script: str, *args, cwd: Path | None = None,
        quiet: bool = False) -> tuple[int, str]:
    """调一个子脚本。UI_ORCHESTRATED 让它闭掉自己的 NEXT。"""
    env = dict(os.environ, **{runstate.ORCH_KEY: "1"})
    r = subprocess.run([sys.executable, str(SC / script), *[str(x) for x in args]],
                       cwd=str(cwd) if cwd else None, env=env,
                       capture_output=True, text=True, timeout=1800)
    out = (r.stdout or "") + (r.stderr or "")
    if not quiet:
        print(out.rstrip())
    return r.returncode, out


def step(mark: str, title: str) -> None:
    print(f"\n{BAR}\n{mark}  {title}\n{BAR}")


def nxt(what: str, cmd: str | None = None) -> None:
    """一条命令的输出里只能有一个 NEXT（守则 S24）。"""
    print(f"\n{BAR}\nNEXT ▸ {what}")
    if cmd:
        print(f"\n    {cmd}")
    print(BAR)


def finish(run: dict, stage: str, what: str, cmd: str | None = None) -> None:
    """一条命令的结尾。**顺序是硬的**：横幅在前、NEXT 紧跟在后。

    10 行横幅 + 6 行 NEXT = 16 行 < `tail -20`。
    实测 57% 的调用带管道过滤，最短就是 `tail -20` —— 横幅放在开头等于没印。
    """
    b = runstate.banner(run, stage)
    if b:
        print("\n" + b)
    nxt(what, cmd)


def need_run(a) -> tuple[Path, dict]:
    p = runstate.find(getattr(a, "run", None))
    data = runstate.load(p) if p else None
    if data and data.get("contract"):
        return p, data
    # 保底分岔（S13）：找不到合同时**不能**把模型推回"重跑 brief"——
    # 实测那正是"回包目录重开一个任务、前功尽弃"的入口。
    # 先扫盘上已有的 run，把可直接粘贴的续跑命令印出来。
    runs = runstate.list_runs()
    print("没拿到冻结的合同（--run 没给，或者给的那个文件不在）。")
    if runs:
        print(f"\n盘上已经有 {len(runs)} 个任务，八成是其中之一：")
        for p2, d2 in runs[:5]:
            print(f"  · {runstate.describe_run(p2, d2)}")
        print("\n续跑（把 --run 换成上面对应那一行的路径）：")
        print(f"    {ui_cmd('review', f'--run {runs[0][0]}')}")
        print("\n确实是一个新任务再开新的：")
    nxt("续跑上面某一个，或者开一个新任务",
        ui_cmd("brief", '--query "<当前请求原文>"'))
    sys.exit(1)


def workdir_of(run: dict) -> Path:
    return Path(run["contract"]["workdir"])


def rel_paths(c: dict) -> dict:
    d = c["deliverables"]
    return {"canvases": list(d["doc"]["canvases"]), "cover": d["doc"]["cover"],
            "coverImage": d["doc"]["coverImage"], "proposal": d["doc"]["proposal"],
            "product": d["product"]["path"], "profile": d["product"]["profile"]}


def view_of(c: dict, prof: str) -> tuple[int, int]:
    """这一稿在**哪个尺寸**上被量、被截。

    大屏 / 展板 / 长图的画布尺寸由 query 决定（合同的 `canvas` 字段），
    不是 profile 的默认值。这条是被一个真 bug 逼出来的：
    4001×2251 的大屏用 1920×1080 去截，`transform:scale` 不改变布局尺寸，
    于是 full_page 按 4001 的布局框截图、而内容缩在中间一小块 ——
    **截出来大半张是空的，而所有门都是绿的。**
    """
    cv = c.get("canvas") or {}
    if cv.get("w") and prof in ("big-screen", "spec-board", "long-image"):
        return int(cv["w"]), int(cv["h"])
    return VIEW.get(prof, (1440, 900))


def profile_for(c: dict, rel: str) -> str:
    p = rel_paths(c)
    if rel == p["product"]:
        return p["profile"]
    if rel in p["canvases"] or rel == p["cover"]:
        return "doc"
    return p["profile"]


# ── 还是不是骨架 ────────────────────────────────────────────
_TEXT = re.compile(r">([^<>]{8,})<")


def _visible_texts(html: str) -> set[str]:
    body = re.split(r"<body[^>]*>", html, 1)[-1]
    body = re.sub(r"<(script|style)\b.*?</\1>", " ", body, flags=re.S | re.I)
    body = re.sub(r"<!--.*?-->", " ", body, flags=re.S)
    return {t.strip() for t in _TEXT.findall(body) if t.strip()}


def still_stub(path: Path, skeleton: Path) -> bool:
    """这份文件还是刚拷出来的骨架吗。

    判据有两条，任一成立即算没写：占位标记还在；或者和骨架逐字相同的
    可见文案还剩 >=3 句。**不量"改了多少字节"** —— 改动量不代表写完了，
    而"骨架里的示范句还在页面上"是可证伪的。

    曾想在这里加第三条「取景框还在吗」，没有加，理由值得写下来：
    那件事**是几何的**，只有在浏览器里量得准（"版心在 1440 下 <=520px"），
    而这个函数是纯文本的、每条命令都要跑。所以它落在 `check.py` 的
    `frame-intact` 上（review 会在 1440 那一档专门量一次），
    不在这里做一个查类名的近似 —— 查 `.stage/.tabbar` 是对一份骨架的过拟合，
    登录页、详情页、全屏沉浸 H5 合法地没有它们。
    """
    if not path.is_file():
        return True
    t = path.read_text(encoding="utf-8", errors="ignore")
    if re.search(r"TODO|待填|Lorem ipsum|<填[：:]", t):
        return True
    if not skeleton.is_file():
        return False
    return len(_visible_texts(t) & _visible_texts(
        skeleton.read_text(encoding="utf-8", errors="ignore"))) >= 3


# ── 输出自适应（P0-4）───────────────────────────────────
# 模型 `grep -E "BLOCK"` 了 8 次、`tail` 了 8 次，成因是 check.py 单次输出
# **28 行里 25 行是 PASS**。噪声高到必须过滤时，过滤掉的一定包括
# 我们最想让它看到的东西（横幅）。所以"让输出变短"本身就是一条到达率机制。
def squeeze(out: str) -> str:
    """有 BLOCK 时只留 BLOCK 与总结行，PASS 折叠成一行。全绿时原样返回。"""
    lines = out.splitlines()
    if not any(ln.startswith("✗ BLOCK") for ln in lines):
        return out
    keep, npass = [], 0
    for ln in lines:
        if ln.startswith("  PASS"):
            npass += 1
            continue
        keep.append(ln)
    if npass:
        keep.insert(0, f"  （其余 {npass} 条通过，要看全部：同一条命令加 --verbose）")
    return "\n".join(keep)


def needs_gate(checks: list[dict], rel: str, wd: Path,
               peers: tuple[str, ...]) -> bool:
    """这份产物要不要（重新）跑门。

    两个条件任一成立就要跑：**没跑过**，或者**跑完之后又被改过**。
    第二条是必需的：产物会在两条命令之间被手工修改，
    按文件名去重会让最后一次修改永远不被任何门看见 —— 那次修改正是发出去的那一版。
    """
    import check as _check          # 延迟导入：与 publish 同一种写法，避免环形依赖
    import publish as _pub
    if not _pub._hit(checks, "target", rel, peers):
        return True
    f = wd / rel
    if not f.is_file():
        return False
    now = _check.file_sha(f)
    for r in reversed(checks):
        was = (r.get("sha") or {})
        for k, v in was.items():
            if k.replace("\\", "/").endswith(rel.replace("\\", "/")):
                return v != now          # 记过哈希：不一致才重跑
    return True                          # 跑过但没记哈希（旧收据）→ 保守重跑


def run_gate(rel: str, prof: str, wd: Path, run_path: Path,
             aesthetic: bool = True, verbose: bool = False,
             viewport: tuple[int, int] | None = None) -> tuple[int, list[str]]:
    args = ["--url", rel, "--profile", prof, "--run", str(run_path)]
    if viewport:
        args += ["--viewport", f"{viewport[0]}x{viewport[1]}"]
    if aesthetic:
        args.append("--aesthetic")
    code, out = sub("check.py", *args, cwd=wd, quiet=True)
    print((out if verbose else squeeze(out)).rstrip())
    blocked = [ln.split()[2] for ln in out.splitlines()
               if ln.startswith("✗ BLOCK") and len(ln.split()) > 2]
    return code, blocked


# ── ① brief ────────────────────────────────────────────────
def cmd_brief(a) -> int:
    """开工。带 `--run` 指向一个**已经发布过**的 run 时，这就是 `amend`：
    就地改这一稿已经交出去的产物，不建新骨架、不重跑生图、不发第二个链接。

    判据是两条可证伪条件，**不靠语气猜**：
      ① 能解析到一个已有 run　② 该 run 的 receipts.publish 里有 documentId
    缺任一条就按新建走，并印出原因 —— 猜错一次就白重做一遍。
    """
    global RUN_ARG
    query = a.query
    amend, prev = False, None
    if getattr(a, "run", None):
        prev = runstate.load(runstate.find(a.run))
        has_doc = any(r.get("documentId")
                      for r in ((prev or {}).get("receipts") or {}).get("publish", []))
        if prev and prev.get("contract") and has_doc:
            amend = True
        else:
            print("给了 --run，但那一次" + ("还没发布过（收据里没有 documentId）"
                  if prev else "不在盘上") + " —— 按新建处理。\n"
                  "  要就地改，`--run` 要指向那次已经发布过的 run.json。")
    if amend:
        wd = Path(prev["contract"]["workdir"])
        RUN_ARG = f"--run {runstate.find(a.run)}"
        print(f"就地改已交付的产物（operation=amend）→ {wd}\n"
              f"  不建新骨架、不重跑生图；ship 会 `--update` 重发同一篇，"
              f"不产生第二个链接。")
        run_path = runstate.find(a.run)
        wd.mkdir(parents=True, exist_ok=True)
    else:
        wd, why, tried = runstate.resolve_workdir(query, a.dir)
        if wd is None:
            runstate.die_no_writable_root(tried, query)
            return 1
        if runstate.guard_install_dir(wd, query):
            return 1
        wd.mkdir(parents=True, exist_ok=True)
        run_path = wd / runstate.RUN_NAME
        RUN_ARG = f"--run {run_path}"
        print(f"工作目录 → {wd}\n            （{why}；产物、收据、合同全在这里，"
              f"不在 skill 安装目录）")

    step("①", "交付合同（冻结之后就不改了）")
    args = ["--query", query, "--dir", str(wd), "--run", str(run_path)]
    for flag, v in (("--class", a.cls), ("--shape", a.shape),
                    ("--title", a.title), ("--surface", a.surface)):
        if v:
            args += [flag, v]
    for x in (a.attach or []):
        args += ["--attach", x]
    if amend:
        args.append("--amend")
    if a.force or amend:
        args.append("--force")
    sub("plan.py", *args, cwd=wd)
    run = runstate.load(run_path)
    if not run or not run.get("contract"):
        print("\n合同没冻结成功 —— 原因在上面。改完重跑同一条命令。")
        return 1
    c = run["contract"]
    p = rel_paths(c)

    step("②", "风格签名（决定这一稿往哪个方向长）")
    sub("style.py", "--query", query, "--out", str(wd / "style.json"),
        "--run", str(run_path), cwd=wd)

    step("③", "成品骨架（几何已经对了的起点，剩下的归你）")
    kind = c.get("skeleton") or SKELETON_OF.get(
        c["deliverables"]["product"].get("shape") or "", "web")
    dest = wd / p["product"]
    if dest.is_file():
        print(f"{p['product']} 已存在，不覆盖 —— 骨架只在开头拷一次，"
              f"后面直接改它。")
    else:
        sub("skeleton.py", kind, str(dest), "--title", c["title"], cwd=wd)

    step("④", "doc 的视觉人格（现在就定，做文档那一步要用）")
    try:
        import skeleton as _sk
        style = None
        sp = wd / "style.json"
        if sp.is_file():
            try:
                style = json.loads(sp.read_text(encoding="utf-8"))
            except Exception:
                style = None
        print(_sk.persona_help(style))
    except Exception as e:                                  # pragma: no cover
        print(f"（人格提示打印失败：{e}；做文档那一步会再要一次）")

    finish(run, f"产品（{p['product']}）",
           f"采素材 → 亲手写 {p['product']}（骨架已就位，直接改它，"
           f"所有 TODO 和占位值都要换掉）\n"
           f"       写完立刻回来看自己的产物 —— 这一步是整个包最重要的一环。\n"
           f"       **后面每一条命令都从输出里复制，不要凭记忆敲**（它们带 --run）：",
           ui_cmd("review"))
    return 0


# ── ② review ───────────────────────────────────────────────
def _obs_rounds(run: dict, rel: str) -> int:
    n = 0
    for o in (run.get("receipts") or {}).get("observe", []):
        u = str(o.get("url") or "")
        if u == rel or u.endswith("/" + rel) or Path(u).name == Path(rel).name:
            n += 1
    return n


def detect_stage(run: dict, wd: Path, c: dict, url: str | None) -> tuple[list[str], str]:
    """`review` 自己认现在该看什么。**认到的阶段印进横幅，不静默猜。**

    v3 曾想把 doc 的截图、门和发布全塞进 `ship` —— 那等于**把可逆的检查
    与不可逆的发布合并了**：Doc 写完到发布之间，没有任何一次看图机会。
    正确形态是减少命令的**种类**，不是删掉闭环。
    """
    p = rel_paths(c)
    if url:
        return [url], f"指定（{url}）"
    prod = p["product"]
    # 成品页要看**两轮**才算过：第一轮说要改哪儿，第二轮核对改没改。
    # 只看一轮也能交付，但那一轮说的话就没有人核对了。
    if not (wd / prod).is_file() or _obs_rounds(run, prod) < 2:
        return [prod], f"产品（{prod}）"
    # 画布**不在盘上**也算文档阶段 —— 那一轮要做的正是把它们建出来。
    # 判据不能写成"画布存在且没看过"：画布还没建的时候会退回产品阶段，
    # 而 NEXT 明明写着"接着写 doc" —— 指令和落点自相矛盾，链就断在这儿。
    todo = [x for x in p["canvases"]
            if not (wd / x).is_file() or _obs_rounds(run, x) < 1]
    if todo:
        return todo, f"文档（{'、'.join(todo)}）"
    return [prod], f"产品·复看（{prod}）"


def cmd_review(a) -> int:
    global RUN_ARG
    run_path, run = need_run(a)
    RUN_ARG = f"--run {run_path}"
    c = run["contract"]
    wd = workdir_of(run)
    p = rel_paths(c)

    targets, stage = detect_stage(run, wd, c, a.url)
    print(runstate.banner(run, stage))
    is_doc = stage.startswith("文档")

    if is_doc:
        return _review_doc(a, run_path, run, wd, c, p, targets, stage)

    rel = targets[0]
    target = (wd / rel) if not Path(rel).is_absolute() else Path(rel)
    if not target.is_file():
        print(f"\n{rel} 还不在盘上 —— 先把成品页写出来"
              f"（骨架在 brief 那一步已经拷好了）。")
        finish(run, stage, "写完成品页再回来", ui_cmd("review"))
        return 1
    # 骨架名从合同里读（新载体没有 shape，只有 skeleton）——
    # 拿错骨架，still_stub 就是在跟一份不相干的文件比文案。
    sk = ROOT / "skeletons" / ((c.get("skeleton") or SKELETON_OF.get(
        c["deliverables"]["product"].get("shape") or "", "web")) + ".html")
    if rel == p["product"] and not a.anyway and still_stub(target, sk):
        print(f"\n{rel} 还是骨架（TODO / 占位值还在，或者骨架的示范文案还留在页面上）。\n"
              f"  现在截图只会得到一张写着 TODO 的图。**先把它写成你的稿。**\n"
              f"  骨架只保证装得下、不溢出、可读；好不好看在 craft/ 那四份里。\n"
              f"  （如果这是误判 —— 你确实写完了但留着骨架的某句话 —— 加 --anyway 照跑。）")
        finish(run, stage,
               "把成品页写完（所有 TODO 和占位值都换掉），再回来看自己",
               ui_cmd("review"))
        return 1

    prof = a.profile or profile_for(c, rel)
    w, h = view_of(c, prof)
    stem = Path(rel).stem if Path(rel).stem != "index" else Path(rel).parent.name
    shots = wd / "shots"
    shots.mkdir(parents=True, exist_ok=True)

    step("①", f"截图（{prof}　{w}×{h}）")
    full = shots / f"{stem}-full.png"
    sub("shoot.py", "full", rel, str(full.relative_to(wd)), w, h,
        "--run", str(run_path), cwd=wd)
    screens_dir = shots / f"{stem}-screens"
    if prof in MULTI_STATE:
        sub("shoot.py", "states", rel, str(screens_dir.relative_to(wd)), a.screens,
            "--run", str(run_path), cwd=wd)
        sheet = shots / f"{stem}-sheet.png"
        sub("shoot.py", "sheet", str(screens_dir.relative_to(wd)),
            str(sheet.relative_to(wd)), cwd=wd, quiet=True)
        if sheet.is_file():
            print(f"联络表：{sheet}（多屏拼一张，一次看完）")
    print(f"\n**把这几张图读进上下文，真的看。**\n"
          f"  {full}"
          + (f"\n  {screens_dir}/p*.png" if screens_dir.is_dir() else "")
          + "\n  在参照产物上统计：7 处修改里有 4 处只有看图才能发现，"
            "任何数值门都测不出。")

    step("②", f"真值门（profile 按合同取，是 {prof}，不用你选）")
    _code, blocked = run_gate(rel, prof, wd, run_path, verbose=a.verbose,
                              viewport=(w, h))
    # 有 BLOCK 时**这里就是终点**，NEXT 指向改稿。
    # 门的价值 = 判据正确性 × **有没有人消费它的结论**；曾经后面这个乘数是 0。
    if blocked:
        print(f"\n这一稿有 {len(blocked)} 条 BLOCK：{'、'.join(blocked)}\n"
              f"  上面每一条都写了「要的是什么 → 实测是什么」，照着改。\n"
              f"  **先别做看图回执，也别去做 doc** —— 那些是在这份稿的基础上做的。\n"
              f"  改法：**Grep 定位 → Edit 改那一段**，不要为了找上下文整份重读 {rel}。")
        finish(run, stage,
               "把上面这几条 BLOCK 改掉，然后跑同一条命令（改完它会自己往下走）",
               ui_cmd("review", "" if rel == p["product"] else f"--url {rel}"))
        return 1

    step("③", "看图回执（脚本把量值填好，你补判断那两栏）")
    obs_rel = f"observed-{stem}.json"
    obs = wd / obs_rel
    if not obs.is_file():
        code, _ = sub("observe.py", "--url", rel, "--seed", "--observed", obs_rel,
                      "--width", w, "--height", h, "--run", str(run_path), cwd=wd)
        if code == 2:
            print("（没有 playwright，播不了种 —— 按上面的替代路径截图，手写这份 JSON。）")
        finish(run, stage,
               f"把上面那几张图读进上下文，逐段看，然后编辑 {wd / obs_rel}：\n"
               f"       · `where` 写在页面上哪儿　· `what` 写具体缺陷　· `fix` 写怎么改\n"
               f"       · selector 和 measure 已经量好了，别动它们\n"
               f"       **写完必须再跑一次同一条命令** —— 这一遍才算数，"
               f"文档阶段也才会开；\n"
               f"       只编辑文件不重跑，阶段会一直停在这里，doc 的画布与封面不会建出来：",
               ui_cmd("review"))
        return 0

    filled = 0
    try:
        items, _ = __import__("observe").normalize(
            json.loads(obs.read_text(encoding="utf-8")))
        filled = sum(1 for it in items
                     if str(it.get("what", "")).strip()
                     and str(it.get("fix", "")).strip())
    except Exception:
        items = []
    if filled < a.min:
        print(f"\n{obs_rel} 里只有 {filled} 条填了 what + fix，需要 {a.min} 条。")
        finish(run, stage,
               f"把图读进来，把 {wd / obs_rel} 的 `what` 和 `fix` 补满"
               f"（至少 {a.min} 条），再跑同一条命令", ui_cmd("review"))
        return 1

    code, _out = sub("observe.py", "--url", rel, "--observed", obs_rel,
                     "--min", a.min, "--width", w, "--height", h,
                     "--run", str(run_path), cwd=wd)
    if code == 1:
        finish(run, stage,
               f"上面每条 FAIL 都是「你说的和页面上量到的对不上」。"
               f"改 {obs_rel} 里那几条（或者去改稿），再跑同一条命令",
               ui_cmd("review"))
        return 1

    run = runstate.load(run_path) or run
    rounds = len((run.get("receipts") or {}).get("observe", []))
    if rounds < 2:
        finish(run, stage,
               "按回执把稿改掉，然后**再看一次**（第二轮的条目加 "
               "`\"resolved\": true`，量值按改完之后的新数值写）。\n"
               "       只看一轮也能交付，但那一轮说要改的地方改没改，就没有人核对了：",
               ui_cmd("review"))
        return 0
    finish(run, stage,
           "成品页这一半完成了。接着写 doc 的两块画布与封面 —— "
           "**同一条命令**，它会自己认出你在做文档那一半：",
           ui_cmd("review", f'--persona "{_persona_hint(wd)}"'))
    return 0


def _persona_hint(wd: Path) -> str:
    return "paper=…,ink=…,muted=…,hairline=…,soft=…,font=…,rule=…," \
           "numfont=…,radius=…,bodysize=…,lead=…"


# ── ②b review 的文档阶段（原 `ui.py doc`，闭环一条没少）────────
PROPOSAL_STUB = """<title>{title}</title>
<!-- 封面**不写在这里**：飞书的图片块只吃公网 URL，本地路径会被静默丢弃
     且不报错（发布报成功、封面没了）。封面由 publish.py 在发布之后媒体插入。 -->

<p>【待填：开场一段。用客户自己的话复述目标与人群，再把它翻译成一句话——
这一稿到底要做成什么。这是客户读到的第一句，别写工程语言。】</p>

<h1>【待填：上篇的标题。别叫"设计思路"，用这一稿自己的话】</h1>
<p>【待填：一句话说明下面这块画布讲什么】</p>
<html5-block path="@{canvas_a}"></html5-block>

<h1>【待填：下篇的标题】</h1>
<p>【待填：一句话说明下面这块画布讲什么】</p>
<html5-block path="@{canvas_b}"></html5-block>

<h1>一句话总结</h1>
<callout emoji="✨" background-color="light-blue" border-color="blue"><p><b>【待填：
能被客户复述给他老板听的那一句】</b>【待填：为什么是这句，它还能用在哪里】</p></callout>
"""


def _build_doc_skeletons(a, run_path: Path, run: dict, wd: Path, c: dict,
                         p: dict, stage: str) -> int | None:
    """缺什么建什么，已有的不覆盖。返回 int 表示到此为止。"""
    sk_canvas = ROOT / "skeletons" / "doc-canvas.html"
    missing = [x for x in p["canvases"] if not (wd / x).is_file()]
    if missing and not a.persona:
        print("\n这一步要先定 doc 的视觉人格 —— **它是唯一能阻止「所有人的文档"
              "长得一样」的地方**，所以没有默认值。\n")
        sub("skeleton.py", "doc", str(wd / p["canvases"][0]), "--title", c["title"],
            "--style", str(wd / "style.json"), cwd=wd)
        finish(run, stage,
               "把 11 个人格角色定下来（按上面 style.json 的签名推，别凭手感），"
               "然后重跑这一条",
               ui_cmd("review", f'--persona "{_persona_hint(wd)}"'))
        return 1
    for i, rel in enumerate(p["canvases"]):
        if (wd / rel).is_file():
            continue
        code, _ = sub("skeleton.py", "doc", str(wd / rel), "--title", c["title"],
                      "--project", c["title"], "--part", f"PART {i + 1:02d}",
                      "--persona", a.persona, "--style", str(wd / "style.json"),
                      *(["--accent", a.accent] if a.accent else []), cwd=wd)
        if code:
            finish(run, stage, "按上面补齐人格角色，再重跑这一条",
                   ui_cmd("review", '--persona "…"'))
            return 1
    if not (wd / p["cover"]).is_file():
        sub("skeleton.py", "cover", str(wd / p["cover"]), "--title", c["title"],
            "--project", c["title"], "--class", c["artifactClass"],
            *(["--hero-aspect", str(a.hero_aspect)] if a.hero_aspect else []),
            *(["--accent", a.accent] if a.accent else []), cwd=wd)
    prop = wd / p["proposal"]
    if not prop.is_file():
        prop.parent.mkdir(parents=True, exist_ok=True)
        rels = [os.path.relpath(wd / x, prop.parent).replace("\\", "/")
                for x in p["canvases"]]
        prop.write_text(PROPOSAL_STUB.format(
            title=c["title"], canvas_a=rels[0],
            canvas_b=rels[1] if len(rels) > 1 else rels[0]), encoding="utf-8")
        print(f"· 建了 {p['proposal']}（飞书原生块把两块画布包起来；"
              f"里面的【待填…】要换成你的话，留着会被发布拦下）")
    return None


def _review_doc(a, run_path: Path, run: dict, wd: Path, c: dict, p: dict,
                targets: list[str], stage: str) -> int:
    step("①", "建骨架（缺什么建什么，已有的不覆盖）")
    r = _build_doc_skeletons(a, run_path, run, wd, c, p, stage)
    if r is not None:
        return r

    sk_canvas = ROOT / "skeletons" / "doc-canvas.html"
    sk_cover = ROOT / "skeletons" / "doc-cover.html"
    pending = [x for x in p["canvases"] + [p["cover"]]
               if still_stub(wd / x, sk_cover if x == p["cover"] else sk_canvas)]
    if pending:
        step("②", "现在轮到你写")
        print("这几份还是骨架（占位符还在，或者骨架的示范文案还留在页面上）：")
        for x in pending:
            print(f"  · {wd / x}")
        print("\n  **改它们，不要重写它们。** 骨架的 CSS 就是它保证"
              "「装得下、不溢出、可读」的全部内容，\n"
              "  飞书块宽会浮动，那些 clamp()/min() 是踩出来的。\n"
              "  **只用 Edit 改 <body> 里的文案与图位，不要整份 Write 覆盖。**\n"
              "  实测：三份画布被整份重写花了约 16 分钟，而重写出来的类选择器\n"
              "  与骨架 100% / 79% 重合 —— 那十几分钟买的是一份你已经有的 CSS。\n"
              "\n  **关键界面那一节不用你贴图。** `ship` 会拿成品页现截的真机屏，\n"
              "  压好、转成 data URI，写进画布里 `<!-- KEY-SCREENS-START -->` 那一段。\n"
              "  你只要把 figcaption 换成你的话 —— 顺序也因此是硬的：先成品页，后 doc。\n"
              "  怎么排、哪些做法会出错：method/04-build-doc.md")
        finish(run, stage,
               f"把 {'、'.join(pending)} 和 {p['proposal']} 写完，再跑同一条命令"
               f"（它会出封面图、截画布、跑 doc 门）", ui_cmd("review"))
        return 0

    step("②", "封面出图 + 画布看自己 + 门")
    cov = wd / p["coverImage"]
    cov.parent.mkdir(parents=True, exist_ok=True)
    sub("shoot.py", "full", p["cover"], p["coverImage"], 1600, 900,
        "--run", str(run_path), cwd=wd)
    if cov.is_file():
        print(f"**把 {cov} 读进上下文看一眼** —— 封面是客户打开看到的第一屏。")
        print("\n封面进飞书还差一个公网 URL（本地路径会被静默丢弃）：")
        print("  1 调用宿主工具：")
        print(f"      FileBatchUpload(path_list=[\"{cov.resolve()}\"])")
        print("  2 把返回的 uri 回填给发布：")
        print(f"      python3 {SC / 'publish.py'} --run {run_path} "
              "--cover-url https://aka.doubaocdn.com/s/xxxx")
    blocked_all: list[str] = []
    for rel in p["canvases"]:
        sub("shoot.py", "full", rel, f"shots/{Path(rel).stem}-698.png", 698, 900,
            "--run", str(run_path), cwd=wd)
        _c, b = run_gate(rel, "doc", wd, run_path, aesthetic=False,
                         verbose=a.verbose)
        blocked_all += b
    print("\n**画布也走看图闭环**：把上面两张 698 宽的图读进来看一遍。"
          "文档那一半的缺陷同样只有看图才发现得了。")

    run = runstate.load(run_path) or run
    if blocked_all:
        finish(run, stage,
               f"画布有 {len(blocked_all)} 条 BLOCK：{'、'.join(sorted(set(blocked_all)))}"
               f" —— 改掉再跑同一条命令", ui_cmd("review"))
        return 1
    # 画布也要留下一次看图回执，否则 detect_stage 会一直停在文档阶段。
    for rel in targets:
        runstate.add_receipt(run_path, "observe", {
            "url": rel, "count": 0, "resolved": False, "via": "doc-canvas-shot"})
    run = runstate.load(run_path) or run
    finish(run, stage,
           "发布 + 出交付参数（发过一次就自动改成重发同一篇，不会产生第二个链接）",
           ui_cmd("ship"))
    return 0


# ── ③ ship ─────────────────────────────────────────────────
KEY_START = "<!-- KEY-SCREENS-START -->"
KEY_END = "<!-- KEY-SCREENS-END -->"
# 图位容器：片段替换的是**整个容器**，不是往容器里塞内容 ——
# 片段自带版式（场 + 机身 + 排布），塞进别人的 grid 里会得到 grid 套 grid。
_SLOT_OPEN = re.compile(
    r'<div[^>]*\bclass="[^"]*\b(?:screens|device|device-row|ui-stage|ui-plate)\b[^"]*"[^>]*>')


def _element_span(t: str, m: re.Match) -> tuple[int, int]:
    """从开标签起按 <div> 深度扫到配对的 </div>，返回整个元素的区间。

    非贪婪正则会停在**第一个** `</div>`，容器里只要有一层嵌套 div 就会截错，
    留下一个孤立的 `</div>` 把后面的版面全部吃掉。
    """
    depth, i = 1, m.end()
    for tag in re.finditer(r"<(/?)div\b", t[m.end():], re.I):
        depth += -1 if tag.group(1) else 1
        if depth == 0:
            i = m.end() + tag.end()
            return m.start(), t.find(">", i - 1) + 1 or i
    return m.start(), len(t)


def inject_key_screens(canvas: Path, fragment: str) -> str:
    """把关键屏原地写进画布。**四步变零步。**

    截图和「放进 doc」之间隔着出图、压缩、转 base64、写标签四步，
    隔四步的事情不会自己发生；打印片段让人粘贴也算隔一步 ——
    所以这里直接改文件。

    片段**自带 `<style>`**，所以两条落点都是「整块替换」，
    且落点周围一定补上 KEY-SCREENS 标记，重跑才是幂等的。
    """
    t = canvas.read_text(encoding="utf-8")
    # 只剥片段自己的说明性注释行，保留 <style> 与容器。
    inner = "\n".join(x for x in fragment.splitlines()
                      if not x.strip().startswith("<!--") and x.strip())
    block = KEY_START + "\n" + inner + "\n" + KEY_END
    if KEY_START in t and KEY_END in t:
        head, rest = t.split(KEY_START, 1)
        _old, tail = rest.split(KEY_END, 1)
        canvas.write_text(head + block + tail, encoding="utf-8")
        return "标记块"
    m = _SLOT_OPEN.search(t)
    if m:
        # 整个容器换掉，并补上标记 —— 否则下一次重跑既找不到标记
        # 也找不到容器（容器刚被我们换成了自带版式的片段）。
        a, b = _element_span(t, m)
        canvas.write_text(t[:a] + block + t[b:], encoding="utf-8")
        return "图位容器（已补标记块）"
    return ""


def _key_screens(run_path: Path, run: dict, wd: Path, c: dict, p: dict,
                 n: int, slot: str = "plate") -> tuple[bool, str]:
    """出图 → 压缩 → data URI → 写进画布。返回 (成功, 说明)。"""
    if not (wd / p["product"]).is_file():
        return False, f"{p['product']} 不在盘上，关键界面那一节只能空着"
    mobile = c["artifactClass"] == "mobile"
    if mobile:
        sd = wd / "shots" / "doc-screens"
        sub("shoot.py", "states", p["product"], str(sd.relative_to(wd)), n,
            "--run", str(run_path), cwd=wd)
        code, _ = sub("pack_img.py", "--for-doc-screens", str(sd.relative_to(wd)),
                      "--out", "doc/screens", "--run", str(run_path), cwd=wd)
        frag = wd / "doc" / "screens" / "screens-figures.html"
    else:
        # 宽屏稿的版面证据是**通栏长图**，不是手机机身位。
        # 不能无条件走 screens（写死 390×844）：那会把一份官网的关键界面节
        # 做成三台手机 —— 那是缺陷。
        full = wd / "shots" / "doc-full.png"
        product = wd / p["product"]
        shot_receipts = (run.get("receipts") or {}).get("shot", [])
        fresh = full.is_file() and any(
            r.get("path") in (str(full.relative_to(wd)), str(full))
            and r.get("source") == p["product"]
            and full.stat().st_mtime >= product.stat().st_mtime
            for r in shot_receipts)
        if fresh:
            print("· doc-full.png 是最新的，跳过重截（省约 10s）")
        else:
            sub("shoot.py", "full", p["product"], str(full.relative_to(wd)),
                1440, 900, "--run", str(run_path), cwd=wd)
        if not full.is_file():
            return False, "宽屏长图没截出来"
        code, _ = sub("pack_img.py", str(full.relative_to(wd)), "--slot", slot,
                      "--out", "doc/img", "--budget-kb", "366", "--bands", "3",
                      "--run", str(run_path), cwd=wd)
        frag = wd / "doc" / "img" / "plate-figure.html"
    # 判据是**片段在不在**，不是子脚本的退出码：pack_img 在"源图不够宽"时
    # 返回 1（那是一条如实报告，不是失败），片段照样是好的。
    if not frag.is_file():
        return False, f"出图/压缩没成功（没拿到 {frag}）"
    fragment = frag.read_text(encoding="utf-8")
    done = []
    for rel in p["canvases"]:
        cv = wd / rel
        if not cv.is_file():
            continue
        how = inject_key_screens(cv, fragment)
        if how:
            done.append(f"{rel}（{how}）")
            break                      # 只写第一块画布，避免同一批图出现两遍
    if not done:
        return False, ("画布里既没有 KEY-SCREENS 标记块也没有 .screens 容器 —— "
                       "把下面这段整段粘进关键界面那一节：\n      " + str(frag))
    packs = (runstate.load(run_path) or run).get("receipts", {}).get("pack", [])
    last = packs[-1] if packs else {}
    imgs = last.get("images") or []
    if imgs:
        widths = sorted({str(x.get("width")) for x in imgs if x.get("width")})
        qs = [x.get("quality") for x in imgs if x.get("quality")]
        b64 = last.get("base64Total")
        print(f"✓ 已写入 {done[0]}：KEY-SCREENS 标记块")
        print(f"  {len(imgs)} 张图　{','.join(widths)}px　q{min(qs)}–{max(qs)}"
              + (f"　合计 {b64 // 1024}KB base64（块上限 500KB）" if b64 else ""))
        print("  画布现在含内嵌 base64 —— 不要 cat / tail / sed / grep 这个文件；要看结构跑 ui.py review。")
    return True, "、".join(done)


def reconcile_ledger(wd: Path, c: dict) -> tuple[list[str], list[str]]:
    """把用户逐字点名的东西去产物里找一遍。返回 (缺的, 只报告的)。

    评测 rubric 里权重最大的一族就是这个：「轮播主标语『一起动起来』、
    闭馆公告文案、场地日期 yy-mm-dd 格式、『立即预约』按钮文案 **100% 匹配需求原文**」。
    它是可机械判定的，而包里此前**没有任何东西**把用户点名的东西抽成清单再对账。
    """
    ledger = c.get("ledger") or []
    if not ledger:
        return [], []
    text = ""
    for rel in [(c["deliverables"]["product"]["path"])] + \
            list(c["deliverables"]["doc"]["canvases"]):
        p = wd / rel
        if p.is_file():
            text += p.read_text(encoding="utf-8", errors="ignore")
    miss, soft = [], []
    for x in ledger:
        if x["value"] in text:
            continue
        (miss if x["block"] else soft).append(f"{x['kind']}「{x['value']}」")
    return miss, soft


def check_count(wd: Path, c: dict, n_shots: int) -> str | None:
    """数量合同。**只在 exact / minimum 两档上说话** ——
    脚本按载体建议的那个数（target）只提示，永不阻断。"""
    cnt = c.get("count") or {}
    if not cnt.get("n") or cnt.get("mode") == "target":
        return None
    want, unit, mode = cnt["n"], cnt.get("unit", ""), cnt["mode"]
    if unit in ("屏", "帧", "页", "张"):
        got = n_shots
    else:
        return None
    if mode == "exact" and got != want:
        return f"合同要 {want} {unit}（{cnt['source']}），实测 {got} {unit}"
    if mode == "minimum" and got < want:
        return f"合同要至少 {want} {unit}（{cnt['source']}），实测 {got} {unit}"
    return None


def cmd_ship(a) -> int:
    global RUN_ARG
    run_path, run = need_run(a)
    RUN_ARG = f"--run {run_path}"
    c = run["contract"]
    wd = workdir_of(run)
    p = rel_paths(c)
    stage = "交付"
    print(f"ship · {c.get('title', '未命名')} · {wd}")
    sys.path.insert(0, str(SC))
    import publish as _pub

    stop, gaps = _pub.closures(run, wd)
    if stop:
        step("✗", "盘上还没有可发的东西")
        for e in stop:
            print("  ✗ " + e + "\n")
        finish(run, stage, "补完上面这些再来（其余的都不阻断交付）", ui_cmd("ship"))
        return 1

    step("①", "关键屏进画布（脚本自己写，不用你粘）")
    ok_screens, how = _key_screens(run_path, run, wd, c, p, a.screens, a.slot)
    print(("· 已写进 " + how) if ok_screens else ("· 没写成：" + how))

    step("②", "需求账本对账（用户逐字点名的东西，一条都不许丢）")
    miss, soft = reconcile_ledger(wd, c)
    cnt_bad = check_count(wd, c, a.screens if ok_screens else 0)
    if not (c.get("ledger") or c.get("count", {}).get("n")):
        print("· 这条 query 没有逐字点名的东西，账本是空的。")
    for x in soft:
        print(f"  ○ {x} 没在产物里找到（只报告，不阻断 —— "
              f"否定式的判据挡不住换个说法）")
    for x in miss:
        print(f"  ✗ {x} **没有逐字出现在产物里**")
    if cnt_bad:
        print(f"  ✗ {cnt_bad}")
    if not miss and not cnt_bad:
        print("· 账本逐条对上了。")

    step("③", "汇报口吻 + 补齐还没跑过 / 跑过之后又改过的门")
    have = [x for x in p["canvases"] if (wd / x).is_file()]
    sub("check.py", "--canvas", *have, "--doc-voice", cwd=wd)
    checks = (run.get("receipts") or {}).get("check", [])
    peers = tuple(p["canvases"] + [p["product"]])
    todo = [(x, "doc") for x in have if needs_gate(checks, x, wd, peers)]
    if (wd / p["product"]).is_file() and needs_gate(
            checks, p["product"], wd, peers):
        todo.append((p["product"], p["profile"]))
    for rel, prof in todo:
        run_gate(rel, prof, wd, run_path, verbose=a.verbose,
                 viewport=None if prof == "doc" else view_of(c, prof))
    if not todo:
        print("· 门都跑过了，且跑完之后没人再改过产物。")

    step("④", "发布到飞书 + 字节级回读对账 + 封面重试")
    prev = [r for r in (run.get("receipts") or {}).get("publish", [])
            if r.get("documentId")]
    args = ["--run", str(run_path)]
    if prev:
        print(f"· 这一稿已经发过（{prev[-1]['documentId']}），改成重发同一篇。")
        args += ["--update", prev[-1]["documentId"],
                 "--proposal", str(wd / p["proposal"])]
        if (wd / p["coverImage"]).is_file():
            args += ["--cover", str(wd / p["coverImage"])]
    code, _out = sub("publish.py", *args, cwd=wd)
    run = runstate.load(run_path) or run
    if code == 2:
        finish(run, stage,
               "宿主上没有 lark-cli（`lark-cli auth login` 之后才有）。"
               "文档这一半发不出去 —— 先把这件事告诉用户，不要假装发过了。", None)
        return 2
    if code != 0:
        finish(run, stage, "按上面改完再跑同一条命令（已经发出去的不会重复发）",
               ui_cmd("ship"))
        return 1

    step("⑤", "交付参数（机器产出，你不转写）")
    code, _out = sub("deliver.py", "--run", str(run_path), cwd=wd)
    if code != 0:
        finish(run, stage, "按上面 ✗ 那几条补完，再跑同一条命令", ui_cmd("ship"))
        return 1

    # ── NEXT 三级优先（治 B3 的结构性成因）────────────────────
    # 封面回读失败时若只写进收据与 gaps，**唯一的 NEXT 就会指向交卡**。
    # **披露不是出口，NEXT 才是出口。** 门的价值 = 判据正确性 × 有没有人消费它。
    run = runstate.load(run_path) or run
    pubs = (run.get("receipts") or {}).get("publish", [])
    last = pubs[-1] if pubs else {}
    if last.get("documentId") and not last.get("coverInserted"):
        cover_path = (wd / p["coverImage"]).resolve()
        finish(run, stage,
               "**文档里还是没有封面**（回读判定，不是本地文件在不在）。\n"
               "       飞书 <img href> 只吃公网 URL。先把封面上传成 URL，再随正文重发：\n"
               f"       ① FileBatchUpload(path_list=[\"{cover_path}\"])\n"
               "       ② 把返回的 uri 填进下面这条：",
               f"python3 {SC / 'publish.py'} --run {run_path} "
               f"--update {last['documentId']} --proposal {wd / p['proposal']} "
               f"--cover {wd / p['coverImage']} --cover-url https://aka.doubaocdn.com/s/xxxx")
        return 1
    if not ok_screens:
        finish(run, stage,
               "**doc 的关键界面那一节还是空的**（脚本没写进去，原因在第①段）。\n"
               "       那一节放的是成品页的真机截图，是这份 doc 唯一的版面证据 —— "
               "补完再交卡：", ui_cmd("ship"))
        return 1
    if miss or cnt_bad:
        items = "、".join(miss[:4]) + ("；" + cnt_bad if cnt_bad else "")
        finish(run, stage,
               f"**用户点名的东西还有 {len(miss) + bool(cnt_bad)} 项没兑现**：{items}\n"
               f"       Grep 定位 → Edit 把原文补进去（**逐字**，不要换说法），"
               f"再跑同一条命令：", ui_cmd("ship"))
        return 1
    finish(run, stage,
           "交两张卡，**顺序是硬约束**：\n"
           "       ① 先 NotifyHuman 交 Doc URL（整行复制上面的 attachment_source）\n"
           "       ② 再 app_builder_agent，user_prompt = 上面 ↓↓ 到 END 之间那一整段\n"
           "       换顺序会丢卡；prompt 摘要或改写 = 另一个模型按你的描述重画一遍。\n"
           "       调用完把 NotifyHuman 的返回原文贴回来对账：",
           f"python3 {SC / 'deliver.py'} --run {run_path} --confirm \"<返回原文>\"")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="UI 设计包的三条命令：brief / review / ship")
    sp = ap.add_subparsers(dest="cmd", required=True)

    for name in ("brief", "start"):          # start 是旧名，留着不报错
        s = sp.add_parser(name, help="开工：合同 + 风格签名 + 成品骨架 + 这一稿的对手")
        s.add_argument("--query", required=True, help="当前请求原文，一个字都别改写")
        s.add_argument("--dir", help="工作目录（默认自动探测一个可写的根，"
                                     "**不会**落在 skill 安装目录里）")
        s.add_argument("--class", dest="cls", choices=["mobile", "web"])
        s.add_argument("--shape", choices=["产品界面", "单向叙事", "互动生成器"])
        s.add_argument("--surface", help="用户点名了产物类型就给它（mobile-app / "
                                         "mobile-h5 / web-site / web-console / "
                                         "spec-board / big-screen / long-image）")
        s.add_argument("--attach", action="append", default=[],
                       help="用户给的参考图 / 旧版稿，可给多次")
        runstate.add_run_arg(s)
        s.add_argument("--title")
        s.add_argument("--force", action="store_true", help="重新冻结合同")
        s.set_defaults(fn=cmd_brief)

    for name in ("review", "doc"):           # doc 并进 review，旧名留着不报错
        r = sp.add_parser(
            name, help="看自己：截图 + 门 + 看图回执（自己认产品/文档阶段）")
        runstate.add_run_arg(r)
        r.add_argument("--url", help="默认按盘上的收据自动认；也可以显式指定")
        r.add_argument("--profile", choices=list(VIEW), help="默认按合同取，不用给")
        r.add_argument("--min", type=int, default=2, help="看图回执至少几条")
        r.add_argument("--screens", type=int, default=6, help="移动端逐屏截几屏")
        r.add_argument("--anyway", action="store_true",
                       help="产物看起来还是骨架时也照跑（误判时用）")
        r.add_argument("--verbose", action="store_true",
                       help="有 BLOCK 时也把 PASS 行全印出来")
        r.add_argument("--persona", default="", help="doc 阶段：11 个人格角色 k=v,k=v")
        r.add_argument("--accent", help="doc 阶段：强调色")
        r.add_argument("--hero-aspect", type=float, help="doc 阶段：封面主素材宽/高")
        r.set_defaults(fn=cmd_review)

    h = sp.add_parser("ship", help="交付：关键屏进画布 + 门 + 发布 + 交付参数")
    runstate.add_run_arg(h)
    h.add_argument("--screens", type=int, default=6, help="关键屏截几屏进 doc")
    h.add_argument("--slot", default="plate",
                   choices=["plate", "duo", "screens2", "screens3", "screens4", "device", "device-row"],
                   help="宽屏稿关键界面进 doc 的图位；默认 plate")
    h.add_argument("--verbose", action="store_true")
    h.set_defaults(fn=cmd_ship)

    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
