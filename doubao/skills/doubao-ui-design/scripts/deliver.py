#!/usr/bin/env python3
"""交付参数由脚本产出，不由你转写。

这个脚本存在的全部理由是两条实测。

一、**转写会失真。**

    publish.py 打印    …/docx/Z8eXdXZydoq62BxhjMQcopOhnPh   （27 字符）
    模型抄进 NotifyHuman …/docx/Z8eXdXZydoq6BxhjMQcopOhnPh   （26 字符，少了一个 '2'）

文档本身完好，字节级对账全绿，**卡片指向一个不存在的文档**。
结论是通则性的：**再严的产物校验也拦不住"交付时抄错"。**

二、**转述会重画。**（新增）

    成功：给 app_builder_agent 的 prompt = 28,727 / 20,043 字，贴了完整 HTML
    失败：给 app_builder_agent 的 prompt = 359 字，一段功能描述

第三条里设计稿 `site/index.html` 一个字节都没进 prompt —— 它被 FileBatchUpload
上传了，然后被丢下。用户看到的那张网页卡是**另一个模型按 359 字重画的**，
和 doc 风格不一致是必然，交互简陋是必然。
只打印一句占位符 `<把 xxx 的完整 HTML 与素材 URL 写进 prompt>` 是不行的：
写不写进真 HTML 全凭运气。

所以凡是"机器产出、要被转写"的东西（doc URL、成品 HTML、图片 URL），
都由这个脚本自己产出成品，并做一次机器对账。

用法：
    python3 deliver.py --run run.json --upload-map "<FileBatchUpload 的返回原文>"
    python3 deliver.py --run run.json                 # 出交付参数 + 组装 app prompt
    python3 deliver.py --run run.json --confirm "<NotifyHuman 返回的原文>"
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import runstate  # noqa: E402

MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
        ".webp": "image/webp", ".gif": "image/gif", ".svg": "image/svg+xml"}
# prompt 的总上限。原图直接 base64 实测能撑到 8.9MB —— 那和交不出去是一回事。
# 上限由「执行者能不能把它当作一次工具调用的参数吐出来」决定，
# 不由「内存装不装得下」决定。成功样本 20 / 28 / 30KB；
# 408KB 那次的结果是整段放弃、改成传一行文件路径，图全丢。
# 取成功样本上沿的 2 倍。超过就一律走上传，不内联。
INLINE_CAP = 60_000
INLINE_W = 780          # 手机屏 390 CSS px 的 2 倍，内联图不需要比这更大


def shrink(f: Path) -> bytes:
    """把一张素材缩到手机屏 2× 再压。压不动就原样返回，绝不失败。"""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from pack_img import Backend, fit
        import tempfile
        be = Backend()
        if be.kind == "none":
            return f.read_bytes()
        w, _h = be.size(f)
        dst = Path(tempfile.mkdtemp()) / "s.jpg"
        fit(be, f, dst, min(w, INLINE_W), 90_000)
        return dst.read_bytes() if dst.is_file() else f.read_bytes()
    except Exception:
        return f.read_bytes()

DOCX = re.compile(r"(https?://[\w.-]+/docx/([\w-]+))")
# FileBatchUpload 的返回是一串 {"uri":…,"text":…,"path":…}，逐个抠出来。
UPLOAD = re.compile(r'\{[^{}]*"uri"\s*:\s*"([^"]+)"[^{}]*\}')
UPLOAD_PATH = re.compile(r'"path"\s*:\s*"([^"]+)"')
DATA_URI = re.compile(r"data:image/([a-z+]+);base64,([A-Za-z0-9+/=]+)")
ASSET_SRC = re.compile(r'([^"\'\s>=]+\.(?:jpg|jpeg|png|webp|gif|svg|mp4))', re.I)
# 宿主给的图片地址是**会话内临时凭据**，不是公网素材：换一个进程/沙箱就取不到。
# 交付端（app_builder）拿到它们只会渲染出 alt 文字。判据按域名与签名参数，两者都可证伪。
# 判据落在 URL **自己带的证据**上，不落在它来自哪个域名：
# 带签名/过期参数的是会话内临时凭据，换个进程就取不到；
# 而上传工具返回的短链没有这些参数，是可以交付的公网地址。
# 按裸域名拉黑会把唯一上传通路的产物一起判死。
FRAGILE_HOST = re.compile(
    r"(x-signature=|x-expires=|[\w-]+-sign\.[\w.-]+)", re.I)


def char_diff(want: str, got: str) -> str:
    """指出第几位开始对不上，并说清是漏了还是多了。"""
    import difflib
    out = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(a=want, b=got).get_opcodes():
        if tag == "equal":
            continue
        if tag == "delete":
            out.append(f"第 {i1 + 1} 位漏了 `{want[i1:i2]}`")
        elif tag == "insert":
            out.append(f"第 {j1 + 1} 位多了 `{got[j1:j2]}`")
        else:
            out.append(f"第 {i1 + 1} 位 `{want[i1:i2]}` 被写成了 `{got[j1:j2]}`")
    return "；".join(out) or "长度相同但不是同一个值"


def latest_publish(run: dict) -> dict | None:
    rs = [r for r in (run.get("receipts") or {}).get("publish", [])
          if r.get("url") and r.get("reconciled")]
    return rs[-1] if rs else None


def parse_upload_map(raw: str) -> dict[str, str]:
    """把 FileBatchUpload 的返回原文解析成 本地路径 → 公网 URL。"""
    out: dict[str, str] = {}
    for m in UPLOAD.finditer(raw):
        mp = UPLOAD_PATH.search(m.group(0))
        if mp:
            out[mp.group(1)] = m.group(1)
    return out


def build_app_prompt(run: dict, base: Path) -> tuple[str, list[str]]:
    """把成品 HTML 组装成可以整段粘贴的 app_builder_agent prompt。

    图片一律换成已上传的公网 URL —— host-contract.md §3：
    严禁在 prompt 里出现本地路径；0 个公网 URL 的 prompt 会产出一整页纯色块。
    """
    c = run["contract"]
    prod = c["deliverables"]["product"]
    html_path = base / prod["path"]
    warn: list[str] = []
    if not html_path.is_file():
        return "", [f"成品页还不存在：{prod['path']}"]
    html = html_path.read_text(encoding="utf-8", errors="ignore")

    umap: dict[str, str] = {}
    for r in (run.get("receipts") or {}).get("upload", []):
        umap.update(r.get("map") or {})
    # 本地路径在 HTML 里可能是绝对路径、相对路径或纯文件名三种形态，
    # 所以按**文件名**建索引，最宽松地替换。
    by_name = {Path(k).name: v for k, v in umap.items()}

    # 没有公网 URL 时**缩小后内联 data URI**，不再拒绝出 prompt。
    # --upload-map 不能做成硬前置：upload 收据经常是 0 条，
    # 那样这条路从头到尾走不通，最后只会编一段 255 字的描述交给 app_builder。
    # app_builder 吃的是 HTML，data URI 完全可用 —— 这就是那条保底分岔。
    # # 但内联必须有上限：原图直接 base64 实测把 prompt 撑到 8.9MB，一样交不出去。
    # 所以先缩到手机屏 2× 再压，总量超 INLINE_CAP 就不内联，
    # 改成把 FileBatchUpload 的 path_list **直接打印成可粘贴的参数**。
    refs = sorted({m.group(1) for m in ASSET_SRC.finditer(html)})
    todo: list[tuple[str, Path]] = []
    missing = []
    fragile = []
    for ref in refs:
        if ref.startswith(("data:",)):
            continue
        if ref.startswith(("http://", "https://", "//")):
            # 不能把所有外链都当成"已经是公网 URL，不用管"。
            # 实测代价：一份成品页里 11 张图全是宿主搜索结果的地址
            # （aka.doubaocdn.com/s/…、p3-doubao-search-sign.byteimg.com/…&x-signature=…），
            # app_builder 沙箱取不到，用户打开卡片看到的是一排 alt 文字。
            # 这类地址是**会话内临时凭据**，不是公网素材，交付出去必碎。
            if FRAGILE_HOST.search(ref):
                fragile.append(ref[:64])
            continue
        url = by_name.get(Path(ref).name)
        if url:
            html = html.replace(ref, url)
            continue
        f = (base / prod["path"]).parent / ref
        if not f.is_file():
            f = base / ref
        if f.is_file() and f.suffix.lower() in MIME:
            todo.append((ref, f))
        else:
            missing.append(ref)
    if fragile:
        warn.append(
            f"{len(fragile)} 张图引用的是**宿主的临时图片地址**，交付出去一定碎：\n"
            f"      {fragile[:2]}\n"
            f"      那是会话内的签名地址（byteimg / doubaocdn / 带 x-signature），"
            f"app_builder 沙箱取不到，\n"
            f"      打开卡片看到的会是一排 alt 文字。\n"
            f"      FIX: 把图下到成品页旁边的 assets/ 再按相对路径引用 ——\n"
            f"           curl -sL \"<地址>\" -o assets/<名字>.jpg\n"
            f"           下完确认体积 >4KB（失败的下载会留下一个 2 字节的空文件）。")
    if missing:
        warn.append(
            f"{len(missing)} 个素材既没有公网 URL、盘上也找不到文件：{missing[:4]}\n"
            f"      这些图在交付出去的页面里会是裂图。先确认路径对不对。")

    # 成品页里已经内联的 base64 要**拆出来**。
    # 实测：campus 那份 app/index.html 是 497KB，其中 454KB 是 11 张内联图，
    # 净 HTML 只有 43KB —— 而两次成功的交付 prompt 正好是 20KB 和 28KB。
    # 不拆，prompt 就是 500KB 起步，谁也粘不过去。
    out_dir = base / "deliver" / "assets"
    extracted: list[Path] = []
    for i, m in enumerate(list(DATA_URI.finditer(html)), 1):
        ext = {"jpeg": ".jpg", "jpg": ".jpg", "png": ".png",
               "webp": ".webp", "gif": ".gif"}.get(m.group(1).lower(), ".jpg")
        f = out_dir / f"inline-{i:02d}{ext}"
        url = by_name.get(f.name)
        if url:
            html = html.replace(m.group(0), url)
            continue
        out_dir.mkdir(parents=True, exist_ok=True)
        try:
            f.write_bytes(base64.b64decode(m.group(2)))
        except Exception:
            continue
        extracted.append(f)
        html = html.replace(m.group(0), f"__INLINE_{i:02d}__")
    if extracted:
        print(f"· 成品页里有 {len(extracted)} 张内联 base64，已拆到 "
              f"{out_dir.relative_to(base)}/ —— prompt 从 "
              f"{(len(html) + sum(f.stat().st_size for f in extracted) * 4 // 3) // 1024}KB "
              f"降到 {len(html) // 1024}KB")

    need_upload = [f for _ref, f in todo] + extracted
    if todo and not extracted:
        packed = [(ref, shrink(f)) for ref, f in todo]
        total = sum(len(b) for _, b in packed) * 4 // 3
        if len(html) + total <= INLINE_CAP:
            for ref, blob in packed:
                html = html.replace(
                    ref, "data:image/jpeg;base64," + base64.b64encode(blob).decode())
            print(f"· {len(packed)} 个素材没有公网 URL，已缩到手机屏 2× 后内联"
                  f"（约 {total // 1024}KB）。")
            need_upload = []
    if need_upload:
        est = (len(html) + sum(f.stat().st_size for f in need_upload) * 4 // 3) // 1024
        warn.append(
            f"{len(need_upload)} 张图还没有公网 URL —— app_builder 拿不到本地文件，\n"
            f"      而内联会把 prompt 撑到约 {est}KB（上限 {INLINE_CAP // 1024}KB）：\n"
            f"      那么大的 prompt 发不出去，结果是退化成传一行文件路径，图全丢。\n"
            f"      **先上传，再交卡** —— 三步，都在下面：\n"
            f"      ① 下面这行整段复制成 FileBatchUpload 的 path_list：\n"
            f"        {json.dumps([str(f.resolve()) for f in need_upload], ensure_ascii=False)}\n"
            f"      ② 把返回原文喂回来：\n"
            f"        python3 {runstate.SCRIPTS}/deliver.py --run run.json "
            f"--upload-map \"<返回原文>\"\n"
            f"      ③ 再重跑一次本命令，prompt 就齐了（图变成 URL 之后只有几十 KB）。")

    for i in range(1, 60):
        u = (by_name.get(f"inline-{i:02d}.jpg") or by_name.get(f"inline-{i:02d}.png")
             or by_name.get(f"inline-{i:02d}.webp"))
        if u:
            html = html.replace(f"__INLINE_{i:02d}__", u)

    shape = prod.get("shape") or ("宽屏可运行网页" if prod["profile"] == "web"
                                  else "移动端 H5")
    arch = "html" if prod["profile"] == "web" else "jspage"
    # 图片这一句要按**实际形态**说。内联时还写"已换成公网 URL"是假话，
    # 而假话会让接收方去找一个不存在的东西。
    imgline = ("图片已经内联成 data URI，直接用即可，不要去找本地文件。\n"
               if "data:image" in html else
               "图片链接已经全部替换成公网 URL，直接用即可。\n")
    head = (
        f"请根据以下**完整的 HTML 代码**创建一个网页应用："
        f"{c.get('title', '设计方案')}（{shape}）。\n"
        f"技术类型 arch_type={arch}。\n\n"
        f"**请直接使用提供的 HTML 代码，不要做任何修改、不要重写、不要精简、"
        f"不要按你自己的理解重新设计。**\n"
        f"这份 HTML 是已经定稿的设计，你的职责是把它原样上屏。\n"
        + imgline +
        f"禁止新增任何交互、动效、组件或页面；禁止替换或补充图片；"
        f"禁止调整配色、字号与间距。\n"
        f"如果你认为某处可以改进，**不要改**，在总结里说明即可。\n\n"
        f"完整 HTML 代码如下：\n\n")
    tail = "\n\n请严格按照上面的 HTML 代码创建应用，不要做任何修改。\n"
    return head + html + tail, warn


def _net(s: str) -> str:
    """把内联的 base64 归一成一个短占位，再比长度。

    不做这一步的话，拆图之后 prompt 45KB / 原文件 506KB，
    对账会把一份**正确的** prompt 判成描述式 —— 而 454KB 的差额
    全是被换成公网 URL 的图片。**判据要比的是骨肉，不是脂肪。**
    """
    return DATA_URI.sub("<IMG>", s)


def fidelity(prompt: str, base: Path, run: dict) -> str | None:
    """C6 · prompt 里必须含有产物 HTML 本身。描述式 prompt 直接拒绝。"""
    rel = run["contract"]["deliverables"]["product"]["path"]
    p = base / rel
    if not p.is_file():
        return None
    n_html = len(_net(p.read_text(encoding="utf-8", errors="ignore")))
    if len(_net(prompt)) >= n_html * 0.9:
        return None
    return (f"app_builder prompt 只有 {len(prompt)} 字，而成品页有 {n_html} 字 —— "
            f"这是一段**描述**，不是设计稿。\n"
            f"      实测：359 字的描述 prompt 让 app_builder 重画了一遍，\n"
            f"      用户看到的卡片和设计稿不是同一个东西，风格与 doc 完全对不上。\n"
            f"      HTML 一字不改地贴进去 —— 这一步由脚本做，不要手写。")


def main() -> int:
    ap = argparse.ArgumentParser(description="交付参数产出与对账")
    runstate.add_run_arg(ap)
    ap.add_argument("--confirm", help="把 NotifyHuman 的返回原文贴进来做对账")
    ap.add_argument("--upload-map", help="把 FileBatchUpload 的返回原文贴进来")
    ap.add_argument("--title", help="覆盖附件标题（默认取 contract.title）")
    a = ap.parse_args()

    path = runstate.find(a.run)
    run = runstate.load(path)
    if not run:
        print(f"找不到 run.json。先 `python3 {runstate.SCRIPTS}/plan.py --query \"…\"`。")
        return 2

    if a.upload_map:
        umap = parse_upload_map(a.upload_map)
        if not umap:
            print("从这段文本里没解析出任何 {\"uri\":…,\"path\":…} —— "
                  "请把 FileBatchUpload 的**返回原文**整段贴进来。")
            return 1
        runstate.add_receipt(path, "upload", {"map": umap, "n": len(umap)})
        print(f"记下 {len(umap)} 个素材的公网 URL：")
        for k, v in list(umap.items())[:12]:
            print(f"  {Path(k).name:28} → {v}")
        print(f"\n下一步：python3 {runstate.SCRIPTS}/deliver.py --run "
              f"{path}    ← 它会把这些 URL 写进成品 HTML 再组装 prompt")
        return 0

    pub = latest_publish(run)
    if not pub:
        print("run.json 里没有对账通过的发布收据 —— 先跑 publish.py。\n"
              "  没有发布收据就没有可交付的 URL，这一步不能靠回忆。")
        return 1
    url, doc_id = pub["url"], pub["documentId"]

    if a.confirm:
        m = DOCX.search(a.confirm)
        got = m.group(2) if m else (a.confirm.strip().rstrip("/").split("/")[-1])
        if got == doc_id:
            print(f"对账通过：交付出去的就是 {url}")
            run["delivery"] = {"url": url, "documentId": doc_id, "confirmed": True}
            runstate.save(path, run)
            return 0
        print("✗ 对账失败 —— 交付的 doc id 和发布出来的不是同一个。\n"
              f"    发布  {doc_id}   ({len(doc_id)} 字符)\n"
              f"    交付  {got}   ({len(got)} 字符)\n"
              f"    差异  {char_diff(doc_id, got)}\n\n"
              f"  正确的完整 URL（整行复制，不要重打）：\n    {url}\n\n"
              "  「文档打不开」多半就是这个：文档没坏，URL 抄错了一位。")
        return 1

    contract = run.get("contract") or {}
    title = a.title or contract.get("title") or "设计方案"
    base = Path(contract.get("workdir") or path.parent)

    # ── 封面：**披露，不阻断** ────────────────────────────────
    # 这里是一道 BLOCK：coverInserted 不为 true 就拒绝出交付参数。
    # 而当时 insert_cover 用了一个根本不存在的 flag，成功率 0% ——
    # 于是这道门变成死锁：FIX 提示让执行者去跑那条同样会失败的命令，
    # 跑两次之后它绕过整个交付脚本，自己手写了 255 字的 app_builder prompt，
    # 用户看到的「h5 图片全没了」就是从这里开始的。
    # # 教训是通则性的：**唯一还该阻断的判据形态是"可证伪的产物存在性"**
    # ——盘上有没有东西可发。封面在不在文档里属于完整性，
    # 让它决定"能不能交付"，就是在给绕过定价。所以改成强制披露。
    # publish.py 把「还差什么」写进了收据。这里原样印一遍 ——
    # 强制披露不能依赖执行者想起来加一个参数（守则 S13）。
    gaps = pub.get("gaps") or []
    if gaps:
        print(f"⚠  这一稿还差 {len(gaps)} 件事。**交付参数照出**，"
              f"但你应该在宣布做完之前先看一眼：\n")
        for g in gaps:
            print("   · " + g + "\n")

    cover_missing = pub.get("coverInserted") is not True
    if cover_missing:
        print("⚠  这篇文档里没有封面图 —— 交付参数照出，但你应该先补上。\n"
              "   封面是客户打开看到的第一屏，缺了它这份稿等于少了一页。\n"
              "   补（跑完再回来跑一次 deliver.py）：\n"
              f"     {runstate.UI} ship --run {path}\n"
              f"     它会重跑封面三级重试，插完回读确认。\n")

    steps = [{
        "step": 1,
        "tool": "NotifyHuman",
        "why": "Doc 卡必须最先交；顺序换了第二张卡会把它挤掉",
        "args": {"attachments": [{"attachment_name": title,
                                  "attachment_source": url}]},
    }]
    product = (contract.get("deliverables") or {}).get("product")
    prompt, warns = "", []
    if product:
        prompt, warns = build_app_prompt(run, base)
        bad = fidelity(prompt, base, run) if prompt else None
        if bad:
            warns.append(bad)
        if prompt:
            out = base / "deliver"
            out.mkdir(parents=True, exist_ok=True)
            (out / "app-prompt.txt").write_text(prompt, encoding="utf-8")
        steps.append({
            "step": 2,
            "tool": "app_builder_agent",
            "why": "网页/H5 类产物严禁走 NotifyHuman；它自己上屏，不再 NotifyHuman",
            # 宽屏族（官网 / 控制台 / 展板 / 大屏）走 html，移动端族走 jspage。
            # 写死 `== "web"` 会让宽屏族里的四种载体全部落到 jspage ——
            # 一份 1920 宽的大屏被当成手机页渲染。
            "args": {"arch_type": "html" if product["profile"] in (
                         "web", "web-console", "spec-board", "big-screen") else "jspage",
                     "user_prompt": f"↓↓ 见下面 {len(prompt)} 字的整段正文，原样复制 ↓↓"},
        })
    print(json.dumps(steps, ensure_ascii=False, indent=2))
    if warns:
        print("\n交付前还差这些：")
        for w in warns:
            print("  ✗ " + w)
        return 1

    # 正文**落盘，不走 stdout**。
    # 超过几 KB 的输出会被截断成「当前消息过长」，而被截掉的正是开头那个
    # 「从这里开始复制」的标记 —— 于是"整段复制"这条合同在执行时不成立，
    # 退路只剩下自己编一段描述或者传一行文件路径，两条都会让设计稿丢失。
    # 落盘 + 给路径，读进来多少就是多少，没有截断这一环。
    if prompt:
        f = base / "deliver" / "app-prompt.txt"
        print("\n" + "=" * 72)
        print(f"app_builder_agent 的 user_prompt 已备好：{f}")
        print(f"  体积 {len(prompt) // 1024}KB（{len(prompt)} 字，含完整成品 HTML"
              f"{'，图片是公网 URL' if 'data:image' not in prompt else '，图片已内联'}）")
        print("  **用 Read 读这个文件，把内容整段作为 user_prompt。**")
        print("  ✗ 不要传文件路径给 app_builder（它的沙箱读不到本机文件，"
              "只能照剩下的描述重画，图会全部丢失）")
        print("  ✗ 不要写功能摘要，✗ 不要按自己的理解重述")
        print("=" * 72)
    # **两张卡都要交，一张都不能少。**
    # 只交 Doc = 用户点不开你的界面；只交卡片 = 没有设计说明。
    # 这条要在最后再说一遍：只说顺序、不说"不能只交一张"是不够的 ——
    # 只交 Doc 就收工是常见失败。
    if len(steps) == 2:
        print("\n**上面两步都要做，一步都不能少。**\n"
              "  ① NotifyHuman 交 Doc URL —— 少了它，用户拿不到设计说明\n"
              "  ② app_builder_agent 交界面卡 —— 少了它，用户点不开你的界面\n"
              "  顺序不能换：网页卡自己上屏，它之后 Doc 卡会被挤掉。")
    else:
        print("\n⚠  只出得了一张卡（合同里没有成品页）—— "
              "如果用户要的是界面，这一步就是不完整的。")
    print("\n整行复制上面的 attachment_source，不要重打。\n"
          "调用完把返回原文贴回来对账：\n"
          f"  python3 {Path(__file__).resolve()} --run {path} --confirm \"<返回原文>\"")
    if prompt:
        # 「发出去了」一直有对账，「发出去的是不是这一稿」此前零判据 ——
        # 而那正是"卡片里的图全没了"落在的那一格。
        # app_builder 支持传 app_id 回读页面与源码，闭环是现成的。
        n_img = prompt.count("<img")
        print(f"\n**交完卡再回读一次**（这是唯一能证明卡片里是这一稿的动作）：\n"
              f"  拿返回的 app_id 再调一次 app_builder_agent，问：\n"
              f"    「这个应用首屏有几个 <img>？它们的 src 分别是什么？」\n"
              f"  · 期望：>= {n_img} 个，且 src 全是 https:// 或 data:\n"
              f"  · 实测 0 个或远少于 {n_img} → 它没用你给的 HTML，是照描述重画的。\n"
              f"    把 {base / 'deliver' / 'app-prompt.txt'} 整段重发一次"
              f"（带同一个 app_id，编辑模式）。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
