#!/usr/bin/env python3
"""飞书文档发布 + 字节级回读对账 + 一条阻断线 + 一份披露清单。

为什么必须对账：曾经的做法是 `register-site` 会打印
「PASS 官网卡片已登记：https://…」—— 而它什么都没登记，只是把一个地址写进了 JSON。
执行者读到 PASS 就以为第二张卡完成了。
**脚本自己打印的 PASS 不是证据。** 唯一不能自我欺骗的证据是把发出去的东西读回来比字节。

为什么曾经需要硬闭包：一条真实 trace 里 shoot 崩了一次、observe 0 次、
check 0 次，**发布照样成功**——跳过零成本，诚实执行多花十分钟，绕过是理性选择。
的答案是把它们变成前置条件：收据不在，就不发。

**把这个答案改了一半**，因为它的下一个后果同样有实测：
一次 22 分 56 秒的会话，第 18.4 分钟第一次发布被拒，第二次又被拒，**产物 0 个**。

    用户拿到 0 个产物，和拿到一个"少了封面的 doc"，差距是天壤之别。

所以现在是**一条阻断线 + 一份披露清单**：阻断只剩"盘上有没有可发的东西"
与 preflight（发出去也是坏的）；截图/看图/门/素材/封面全部发完再披露，
写进收据由 deliver.py 再印一遍。**披露由收据状态自动决定，不要求你加参数。**
到达率改由 `ui.py` 承担：那些机械动作被收进三条命令里，默认就发生。

封面这条链修了三轮（补插入、修 flag、修路径形态），
每一轮的症状都是同一个：cover.html 建了 3/3，文档里有封面 **0/3**。
最早的根因值得单独记一笔：闭包查的是「doc/cover.html 这个**文件**在不在」——
**门量了文件，用户看的是文档。判据的对象错了，比没有判据更危险。**

用法：
    python3 <SKILL>/scripts/ui.py ship --run <run.json>         # ← 正常走这条
    python3 publish.py --run run.json --cover shots/cover.jpg   # 单跑：合同 + 阻断线 + 插封面
    python3 publish.py --proposal doc/proposal.xml --debug-package   # 只发（调试包本身用）
    python3 publish.py --verify <doc_id_or_url> --canvas doc/a.html
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import runstate  # noqa: E402

MAX_BYTES = 512_000
DOC_URL = re.compile(r"https://[\w.-]+/docx/[\w-]+")
HTML5 = re.compile(r"<html5-block\b[^>]*path=[\"']@?([^\"']+)[\"']", re.I)


def run(cmd: list[str], cwd: Path | None = None) -> tuple[int, str]:
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=900)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def preflight(proposal: Path) -> list[str]:
    """发布前的四条硬约束，全部是真事故换来的。"""
    errs: list[str] = []
    xml = proposal.read_text(encoding="utf-8")
    base = proposal.parent
    refs = HTML5.findall(xml)
    if not refs:
        errs.append("proposal 里一个 <html5-block> 都没有 —— 文档会退化成纯文字。")
    for rel in refs:
        p = base / rel
        if not p.is_file():
            errs.append(f"html5-block 指向的文件不存在：{rel}")
            continue
        t = p.read_text(encoding="utf-8", errors="ignore")
        low = t.lstrip().lower()
        if not (low.startswith("<!doctype html") and "</html>" in low):
            errs.append(f"{rel} 不是完整 HTML 文档 —— 飞书会按片段渲染。")
        comments = re.findall(r"/\*.*?\*/", t, re.S) + re.findall(r"<!--.*?-->", t, re.S)
        hits = re.findall(r"</?(?:html|head|body|style|script)\b", "".join(comments), re.I)
        if hits:
            errs.append(f"{rel} 的注释里有结构标签字面量 {hits[:2]} —— "
                        f"消费方会从那里截断，把 CSS 当正文印出来（已知失败条件）。")
        n = len(t.encode())
        if n > MAX_BYTES:
            errs.append(f"{rel} 体积 {n // 1024}KB 超过飞书硬上限 {MAX_BYTES // 1024}KB。")
        # 正向口径：每个 <img src> 都必须是 data: URI。
        # 不要写成 `'src="assets/' in t` —— 否定式窄枚举，
        # 实测被 `../h5/assets/` 和 `../shots/` 两种写法绕过，用户看到三个裂图。
        bad = [x[:44] for x in re.findall(r'<img[^>]+src=["\']([^"\']{0,80})', t, re.I)
               if x.strip() and not x.startswith("data:")]
        if bad:
            errs.append(f"{rel} 里有 {len(bad)} 个 <img> 不是 data: URI：{bad[:2]}\n"
                        f"    飞书会把相对路径和外链**静默丢弃**，文档里就是裂图占位符。\n"
                        f"    FIX: 图一律 base64 内嵌；用 pack_img.py，让宽度和质量按下限协商，\n"
                        f"         不要手搓 sips/PIL 把图压到 q10 或压到 185px。")
    # 官网整页不能塞进文档
    for rel in refs:
        if re.search(r"site.*\.html$", rel, re.I):
            errs.append(f"{rel} 看起来是官网整页。官网在文档里只以截图出现，不塞 html5-block。")

    # 图片必须是公网 URL —— 本地路径飞书**静默丢弃且不报错**。
    # 已知失败条件：<img href="cycle-cover.jpg"> 发布报"成功 + 字节对账通过"，
    # 回读却是「封面图：无」。和"URL 抄错一位"是同一类病：
    # **发布成功 ≠ 内容完整**，而字节对账只对得上 html5-block，对不上被丢掉的图片块。
    for m in re.finditer(r"<img[^>]+href=[\"']([^\"']+)", xml):
        src = m.group(1)
        if not src.startswith(("http://", "https://")):
            errs.append(
                f'<img href="{src}"> 是本地路径。飞书只接受公网 URL，'
                f'本地路径会被**静默丢弃且不报错**——封面会消失，而发布仍然报成功。\n'
                        f"    FIX: `<img href>` 只吃公网 URL。先用 FileBatchUpload 上传封面图，\n"
                        f"         再重跑 publish.py --cover-url https://aka.doubaocdn.com/s/xxxx；\n"
                        f"         publish.py 会把公网封面写进临时 proposal，再随 +create 一起发。")
    return errs


# ── 封面 ────────────────────────────────────────────────────
COVER_OK_SUFFIX = {".jpg", ".jpeg", ".png", ".webp"}


def cover_arg_errors(cover: str | None) -> list[str]:
    """封面参数的三条硬约束。全部是 实测踩到的。"""
    if not cover:
        return []
    p = Path(cover)
    if not p.is_file():
        return [f"封面文件不存在：{cover}\n"
                f"      python3 {runstate.SCRIPTS}/shoot.py full doc/cover.html {cover} 1600 900"]
    if p.suffix.lower() not in COVER_OK_SUFFIX:
        return [f"封面必须是图片（{'/'.join(sorted(COVER_OK_SUFFIX))}），"
                f"你给的是 {p.suffix or '无后缀'}：{cover}\n"
                f"      cover.html 是**出图的源**，不是封面本身。先截图：\n"
                f"      python3 {runstate.SCRIPTS}/shoot.py full doc/cover.html "
                f"shots/cover.jpg 1600 900"]
    if p.stat().st_size < 20_000:
        return [f"封面只有 {p.stat().st_size // 1024}KB —— 多半是截图截空了或截糊了。\n"
                f"      1600×900 的封面正常在 120–600KB。重截并把图读进上下文看一眼。"]
    return []


def cover_anchor(proposal: Path) -> str | None:
    """从 proposal 里取第一段正文当锚点 —— 封面要插在它**前面**。

    这个函数存在的唯一原因，是 `media-insert` 只能相对一段文本定位。
    锚点必须由脚本机械提取，不能让执行者自己想（S23-3）。
    """
    xml = proposal.read_text(encoding="utf-8")
    xml = re.sub(r"<!--.*?-->", " ", xml, flags=re.S)
    for m in re.finditer(r"<(p|h1|callout)\b[^>]*>(.*?)</\1>", xml, re.S | re.I):
        t = re.sub(r"<[^>]+>", "", m.group(2))
        t = re.sub(r"\s+", " ", t).strip()
        if len(t) >= 8:
            # 太长的锚点容易被 CLI 的模糊匹配打偏，取前 24 个字够定位了
            return t[:24]
    return None


def media_insert_cmd(doc_id: str, cover: Path, as_who: str,
                     anchor: str | None) -> tuple[list[str], Path]:
    """媒体插入的命令与工作目录。**拆出来是为了能被回归真的断言到**——
    这条命令只在真实发布路径上跑得到，两轮里两个不同的参数 bug
    （不存在的 --index、绝对路径的 --file）都是只有在真实链路上才会暴露。
    现在它是一个纯函数：给什么、在哪儿跑，回归可以直接量。
    """
    cmd = ["lark-cli", "docs", "+media-insert", "--doc", doc_id,
           "--as", as_who, "--file", f"./{cover.name}", "--type", "image"]
    if anchor:
        cmd += ["--selection-with-ellipsis", anchor, "--before"]
    return cmd, cover.parent


def image_size(p: Path) -> tuple[int, int]:
    try:
        from PIL import Image
        with Image.open(p) as im:
            return im.size
    except Exception:
        out = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(p)],
                             capture_output=True, text=True).stdout
        w = h = 0
        for line in out.splitlines():
            if "pixelWidth" in line:
                try:
                    w = int(line.split(":")[-1])
                except ValueError:
                    w = 0
            if "pixelHeight" in line:
                try:
                    h = int(line.split(":")[-1])
                except ValueError:
                    h = 0
        return w or 1600, h or 900


def inline_cover(proposal: Path, cover_url: str | None,
                 cover: str | None = None) -> tuple[Path, str | None]:
    """把公网封面作为 +create content 的第一个内容块写进临时 proposal。

    `+media-insert` 是回退路径：它要求本地相对路径、靠正文模糊定位，匹配不上
    还会静默追加到文末。主路径应该是把公网 URL 的 `<img>` 随正文一起创建。
    """
    if not cover_url:
        return proposal, None
    if not cover_url.startswith(("http://", "https://")):
        print("封面 URL 不是公网地址，跳过 inline 封面：" + cover_url)
        return proposal, None
    xml = proposal.read_text(encoding="utf-8")
    if re.search(r"<title>.*?</title>\s*<p>\s*<img\b", xml, re.S | re.I):
        print("proposal 自带封面，不重复插。")
        return proposal, "inline"
    w, h, name = 1600, 900, "cover.jpg"
    if cover and Path(cover).is_file():
        cp = Path(cover)
        w, h = image_size(cp)
        name = cp.name
    img = f'<p><img width="{w}" height="{h}" caption="" name="{name}" href="{cover_url}"/></p>'
    if re.search(r"</title>", xml, re.I):
        xml = re.sub(r"(</title>)", r"\1\n" + img, xml, count=1, flags=re.I)
    else:
        xml = img + "\n" + xml
    tmp = Path(tempfile.mkdtemp(prefix="lark-inline-cover-")) / proposal.name
    tmp.write_text(xml, encoding="utf-8")
    print(f"封面随 +create 写入：{name} {w}×{h} → {cover_url}")
    return tmp, "inline"


def insert_cover(doc_id: str, cover: str, as_who: str,
                 proposal: Path | None = None) -> bool:
    """把封面插到正文第一段**之前**。

    这里写的是 `--index 1` —— **`lark-cli docs +media-insert` 根本没有这个 flag**。
    我从旧 XML 注释里照抄进来，一次都没验证过。实测报错原文：
        unknown flag "--index" for "lark-cli docs +media-insert"
    于是封面插入的成功率是 **0%**，而它上面还挂着一道 BLOCK 闭包：
    收据永远 coverInserted:false → deliver.py 永远拒绝出交付参数 →
    FIX 提示让执行者去跑同一条必然失败的命令 → 死锁 →
    模型绕过整个交付脚本，自己手写了 255 字的 app_builder prompt →
    **用户看到的「h5 图片全没了」，是从这一个 flag 开始的。**

    真实签名（`--help` 实证）：默认追加到文末；要定位插入只有
        --selection-with-ellipsis <锚点文本> [--before]
    这一条路。已用 `--dry-run` 验证组合成立。

    又抓到同一类的第二个 bug，症状和 一模一样（封面成功率 0%），
    这次是 `--file` 的**路径形态**。实测报错原文：

        unsafe file path: --file must be a relative path within the current
        directory, got "/…/shots/cover.jpg"

    不要传 `str(p)`（绝对路径），lark-cli 一律拒绝。
    所以在图片自己的目录里跑，传 `./文件名`。
    **教训是同一条：写下"必须用 X"之前，先在真实宿主上跑一次 X。**
    一条 dry-run 验过的 flag 组合，不代表参数的取值形态也验过。
    """
    p = Path(cover).resolve()
    anchor = cover_anchor(proposal) if proposal else None
    where = f"插在「{anchor}」之前" if anchor else "追加到文末（没找到锚点段落）"
    print(f"插封面 → {p.name}（{p.stat().st_size // 1024}KB，{where}）")
    cmd, cwd = media_insert_cmd(doc_id, p, as_who, anchor)
    code, out = run(cmd, cwd=cwd)
    if code != 0:
        print("封面插入失败（正文已经写成功，只需要补这一步）：\n" + out[-900:])
        return False
    return True


def doc_first_text(doc_id: str, as_who: str) -> str | None:
    """把文档读回来，取第一段够长的正文当锚点 —— 第二级定位用。

    为什么需要第二级：`--selection-with-ellipsis` 是**模糊匹配线上正文**，
    而锚点是从本地 proposal 里取的。两边只要有一点不一致（服务端把标点
    规范化了、把连续空白折叠了），匹配就落空，`lark-cli` 于是
    **默认追加到文末并返回成功** —— 命令报成功，封面在最后一屏。
    直接拿线上那一份的原文当锚点，这一类不一致就不存在了。
    """
    tmp = Path(tempfile.mkdtemp(prefix="lark-anchor-"))
    try:
        code, out = run(["lark-cli", "docs", "+fetch", "--doc", doc_id,
                         "--as", as_who, "--detail", "full"], cwd=tmp)
        if code != 0:
            return None
        text = out
        for f in sorted(tmp.rglob("*")):
            if f.is_file() and f.suffix.lower() in (".xml", ".md", ".txt") \
                    and f.stat().st_size < 4_000_000:
                text += "\n" + f.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r">([^<>]{12,})<", text):
            t = re.sub(r"\s+", " ", m.group(1)).strip()
            if len(t) >= 12 and not t.startswith("<"):
                return t[:24]
        return None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def insert_cover_verified(doc_id: str, cover: str, as_who: str,
                          proposal: Path | None = None) -> bool:
    """插封面 → **回读确认 → 换一种定位再来**，最多三级。

    B3：这条判据本身是对的（`+fetch` 回读，这条链上唯一不能自我欺骗的证据），
    但**修法没有出口**：`cover_ok=False` 只写进收据与 `gaps`，
    `publish.py` 没有任何重试，`ui.py` 直接走 deliver，唯一的 NEXT 印的是「交两张卡」。

        披露 + 唯一 NEXT 指向别处 = 这件事永远不会被做。
        门的价值 = 判据正确性 × **有没有人消费它的结论**。

    更要命的是物理成因有两种，而它们返回同一个 False：
      ① 插入命令根本没成功
      ② 锚点匹配不上 → `lark-cli` **默认追加到文末并返回成功** → 封面在最后一屏
    所以重试不能只是"再跑一遍同一条命令"，必须**换定位策略**。
    """
    levels = [
        ("锚点＝proposal 第一段", lambda: cover_anchor(proposal) if proposal else None),
        ("锚点＝线上文档第一段", lambda: doc_first_text(doc_id, as_who)),
        ("不给锚点（lark-cli 会追加到文末）", lambda: None),
    ]
    p = Path(cover).resolve()
    for i, (why, get_anchor) in enumerate(levels, 1):
        anchor = None
        try:
            anchor = get_anchor()
        except Exception as e:
            print(f"  第 {i}/3 级（{why}）：取锚点失败，跳过：{e}")
            continue
        if i == 2 and not anchor:
            print(f"  第 {i}/3 级（{why}）：线上读不出可用的锚点，跳过。")
            continue
        print(f"  第 {i}/3 级（{why}）"
              + (f"　锚点「{anchor}」" if anchor else "")
              + f"　{p.name} {p.stat().st_size // 1024}KB")
        try:
            cmd, cwd = media_insert_cmd(doc_id, p, as_who, anchor)
            code, out = run(cmd, cwd=cwd)
            if code != 0:
                print("    命令失败：" + out.strip()[-240:])
                continue
        except Exception as e:
            print(f"    命令异常：{e}")
            continue
        got = cover_in_doc(doc_id, as_who)
        if got:
            print(f"    ✓ 回读确认：文档第 1 块是图片（第 {i} 级成功）。")
            return True
        print("    ✗ 命令报成功，但回读的文档第 1 块**不是图片** —— 换一级定位。")
    print("  三级都没把封面放到第 1 块。正文已经在线上，只差这一件；"
          "上面每一级的原文都在，照着看是哪一步断的。")
    return False


def cover_in_doc(doc_id: str, as_who: str) -> bool | None:
    """把文档读回来，看第 1 块到底是不是图片。

    这是这条链上唯一不能自我欺骗的证据。不能只查本地文件在不在 ——
    文件在，门绿，文档没封面。返回 None 表示"读不出来"，
    按包内通则（目标集合为空必须 FAIL）当作没插成功处理。
    """
    tmp = Path(tempfile.mkdtemp(prefix="lark-cover-"))
    try:
        code, out = run(["lark-cli", "docs", "+fetch", "--doc", doc_id,
                         "--as", as_who, "--detail", "full"], cwd=tmp)
        if code != 0:
            return None
        text = out
        for f in sorted(tmp.rglob("*")):
            if f.is_file() and f.suffix.lower() in (".xml", ".md", ".txt", ".json") \
                    and f.stat().st_size < 4_000_000:
                text += "\n" + f.read_text(encoding="utf-8", errors="ignore")
        if not text.strip():
            return None
        i_img = text.find("<img")
        if i_img < 0:
            return False
        # 封面要在正文之前。拿第一个 html5-block 当"正文开始"的锚点。
        m = re.search(r"<html5-block|html5_\d", text)
        return m is None or i_img < m.start()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ── 闭包：一条阻断线 + 一份披露清单 ────────────────────────────
def _hit(receipts: list[dict], key: str, rel: str,
         peers: tuple[str, ...] = ()) -> bool:
    """收据里的 source/target 指到了这份产物没有。

    修的是一个**误报了两次发布**的 bug：兜底不能写成
    `Path(v).name == Path(rel).name` —— 按 basename 匹配，
    而 `app/index.html` 和 `doc/index.html` 同名。
    实测收据里 app 那份的 profile 明明是 `app-screen`、`passed: true`，
    `mine[-1]` 取到的却是 doc 那份的 `web` 收据。
    **一条永远修不掉的报错，会让执行者认定这条链有毛病** —— 那一轮它确实这么判了。

    现在：相对路径**精确尾匹配**优先；只有当这个 basename 在本次的产物清单里
    唯一时，才允许回落到 basename（执行者在子目录里跑命令时收据只有文件名）。
    """
    rel = rel.replace("\\", "/").lstrip("./")
    base = rel.rsplit("/", 1)[-1]
    base_unique = sum(1 for p in peers
                      if p.replace("\\", "/").rsplit("/", 1)[-1] == base) <= 1
    for r in receipts:
        v = str(r.get(key, "")).replace("\\", "/").lstrip("./")
        if not v:
            continue
        if v == rel or v.endswith("/" + rel):
            return True
        if base_unique and (v == base or v.endswith("/" + base)):
            return True
    return False


STUB_MARK = "【待填"


def closures(run_data: dict, base: Path) -> tuple[list[str], list[str]]:
    """返回 (阻断, 披露)。

    把这里从「一条闭包不过就一张卡都没有」改成两层。
    直接对策是实测：22分56秒、103 次工具调用、**产物 0 个** ——
    第一次尝试发布发生在第 18.4 分钟，被拒；之后只剩 4 分钟，第二次又被拒。
    用户拿到 0 个产物，和拿到一个"少了封面的 doc"，差距是天壤之别。

    守则 S13：**唯一还该阻断的判据形态是"可证伪的产物存在性"**——盘上有没有东西可发。
    "产物够不够好"由强制披露承担：披露写进发布收据，deliver.py 再印一遍，
    不需要执行者想起来加参数。

    阻断（发不出去 / 发出去是坏的）：没有合同、proposal 不在、一块画布都没有、
                                    proposal 还是占位稿。
    披露（发得出去，但还差点）：封面、截图、看图轮次、门的收据、素材数、被手改的合同。
    """
    # 印给模型抄的每一条命令都必须自带落点（P0-2）。
    # 实测：裸相对路径 `python3 scripts/ui.py …` 逼着模型 cd 进包目录，
    # 产物于是落在安装目录里，被另一个会话连同合同一起清空。
    RUN_HINT = Path(base) / runstate.RUN_NAME
    c = run_data.get("contract")
    if not c:
        return (["run.json 里没有冻结的合同。先跑："
                 f"\n      {runstate.UI} brief --query \"<用户原话>\""], [])
    stop: list[str] = []
    gaps: list[str] = []
    rec = run_data.get("receipts") or {}
    shots, obs, checks = rec.get("shot", []), rec.get("observe", []), rec.get("check", [])
    d = c["deliverables"]
    canvases = list(d["doc"]["canvases"])
    cover = d["doc"].get("cover")
    cover_img = d["doc"].get("coverImage")
    proposal = d["doc"]["proposal"]
    product = d["product"]["path"]
    profile = d["product"]["profile"]
    peers = tuple(canvases + [product])

    # ── 阻断 ①　发不出去：proposal 与至少一块画布必须在盘上 ──────────
    if not (base / proposal).is_file():
        stop.append(f"没有 {proposal} —— 没有它 lark-cli 无从发起。\n"
                    f"      {runstate.UI} review --run {RUN_HINT}    ← 它会建好 proposal 与两块画布")
    have_canvas = [x for x in canvases if (base / x).is_file()]
    if not have_canvas:
        stop.append(f"一块画布都没有（要 {', '.join(canvases)}）。\n"
                    f"      发一份没有画布的 proposal 出去，客户看到的是一页纯文字。\n"
                    f"      {runstate.UI} review --run {RUN_HINT}")

    # ── 阻断 ②　发出去是坏的：proposal 还是脚本生成的占位稿 ────────
    # 这一条是 自己欠的债：ui.py doc 现在会**替你生成** proposal 骨架，
    # 生成器的产物必须端到端跑一遍下游校验器，否则新产能就是新缺陷源。
    # 判据是精确的占位标记，填过的 proposal 不会被判成缺陷。
    if (base / proposal).is_file():
        txt = (base / proposal).read_text(encoding="utf-8", errors="ignore")
        n = txt.count(STUB_MARK)
        if n:
            stop.append(f"{proposal} 里还有 {n} 处 {STUB_MARK}…】占位没填。\n"
                        f"      那是脚本给你的骨架，不是文案。发出去客户会逐字读到它。")

    # ── 以下全部是披露：发照发，差什么说清楚 ─────────────────────
    # 合同被手改（治 ）。把它从阻断降为披露：
    # 门不再拦发布之后，手改 run.json 已经没有收益，动机消失了。
    try:
        import plan as _plan
        want = c.get("hash")
        if want and _plan.contract_hash(c) != want:
            gaps.append(
                "run.json 里的合同和它自己的指纹对不上 —— 它被手改过，"
                "所有'以合同为准'的核对都不再可信。\n"
                f"      要改就重冻：python3 {runstate.SCRIPTS}/plan.py --force "
                "--query \"<用户原话>\" [--class mobile|web] [--shape …]")
    except Exception:
        pass

    for rel in [x for x in canvases if x not in have_canvas] + [product]:
        if not (base / rel).is_file():
            gaps.append(f"必交产物还缺：{rel}（合同冻结于 {c['frozen']}，两条都是必交）")

    # 门的结论排在披露清单第一条 —— 它是唯一一条"客户打开就会看见"的。
    # 一份真实产物连跑 8 次门全红（图取不到 + 文字压在一起），
    # 一次没改就交付了。把它埋在封面和截图后面，等于没说。
    for rel, prof in [(product, profile)] + [(x, "doc") for x in have_canvas]:
        if not (base / rel).is_file():
            continue
        mine = [r for r in checks if _hit([r], "target", rel, peers)]
        if not mine:
            gaps.append(f"{rel} 没有门的收据。\n"
                        f"      {runstate.UI} review --run {RUN_HINT} --url {rel}")
        elif not mine[-1].get("passed"):
            codes = mine[-1].get("block") or []
            hard = [c for c in codes if c in ("img-broken", "img-remote-src",
                                              "element-overlap", "content-under-dock",
                                              "overflow-x", "placeholder")]
            gaps.append(
                f"{rel} 最后一次跑门还有未处理的 BLOCK：{','.join(codes)}"
                + (f"\n      **{'、'.join(hard)} 不是审美问题，是坏掉** —— "
                   f"图取不到就是一排 alt 文字，重叠就是字压着字，客户一眼看得见。"
                   if hard else "")
                + f"\n      {runstate.UI} review --run {RUN_HINT} --url {rel}")

    if cover_img and not (base / cover_img).is_file():
        gaps.append(
            f"封面图还没出：{cover_img} —— 封面是客户打开看到的第一屏。\n"
            f"      python3 {runstate.SCRIPTS}/shoot.py full {cover} {cover_img} 1600 900\n"
            f"      然后 python3 {runstate.SCRIPTS}/publish.py --update <doc_id> "
            f"--proposal {Path(proposal).name} --cover {cover_img}")

    for rel in have_canvas + [product]:
        if (base / rel).is_file() and not _hit(shots, "source", rel, peers):
            gaps.append(f"{rel} 没有截图收据 —— 这份东西你没看过。\n"
                        f"      {runstate.UI} review --run {RUN_HINT} --url {rel}")

    if not obs:
        gaps.append("一轮看图回执都没有。**这是这个包最贵的一条**：\n"
                    "      在参照产物上统计： 7 处修改有 4 处只有看图才能发现，"
                    "任何数值门都测不出。\n"
                    f"      {runstate.UI} review --run {RUN_HINT}")
    elif len(obs) < 2 or not obs[-1].get("resolved"):
        gaps.append(f"看图只有 {len(obs)} 轮"
                    + ("（且最后一轮没有一条标 resolved:true）" if obs else "")
                    + " —— 第二轮的意义是复核第一轮说要改的地方改了没有。\n"
                      f"      改完再跑一次：{runstate.UI} review --run {RUN_HINT}")

    need = c.get("minVisualAssets", 8)
    pc = [r for r in checks if _hit([r], "target", product, peers)
          and r.get("assetCount") is not None]
    if not pc:
        gaps.append(f"成品页没有素材计数——跑门时加 --aesthetic 才会量：\n"
                    f"      python3 {runstate.SCRIPTS}/check.py --url {product} "
                    f"--profile {profile} --aesthetic")
    elif pc[-1]["assetCount"] < need:
        gaps.append(
            f"成品页只有 {pc[-1]['assetCount']} 个真实视觉资产，合同要求 >={need}。\n"
            f"      实测：gold/web-pulse 17 个、gold/h5-qq2026 14 个、"
            f"低分参照样本 只有 2 个（且全是 emoji 冒充）。\n"
            f"      按合同的 assetPlan 采齐：python3 {runstate.SCRIPTS}/plan.py --validate")

    # C5「形态自查」已删除。它按 basename 匹配收据，
    # `app/index.html` 与 `doc/index.html` 同名 → 两次发布里都误报。
    # 而它的正确形态不是一道门：**`ui.py review` 直接按合同选 profile，
    # 根本不给选错的机会。**
    return stop, gaps


def update(doc_id: str, proposal: Path, cover: str | None, cover_url: str | None,
           as_who: str,
           run_path: Path | None = None, url: str | None = None) -> int:
    """改完稿重发到同一篇。

    为什么要封装：改稿重发是常态（本轮三份文档各做了一遍），
    而手动做是「覆盖正文 → 重新插封面 → 再对账」三步，
    少做中间那步的结果就是**封面没了而你不知道**——
    因为字节对账只对 html5-block，对不上被丢掉的图片块。

    这个分支**从来不写收据**，所以 `--update --cover` 就算成功了，
    deliver.py 读到的还是 create 那一次的旧 coverInserted。
    实测代价：模型跑了两次 --update --cover，收据纹丝不动，交付被永久拒绝。
    """
    proposal_to_send, cover_via = inline_cover(proposal, cover_url, cover)
    print(f"覆盖正文 → {doc_id}")
    code, out = run(["lark-cli", "docs", "+update", "--doc", doc_id, "--as", as_who,
                     "--command", "overwrite", "--content", f"@{proposal_to_send.name}"],
                    cwd=proposal_to_send.parent)
    if code != 0:
        print("覆盖失败：\n" + out[-1200:])
        return 1

    # 插入失败不再 return 1 —— 正文已经在线上了，直接退出会让收据永远停在旧值。
    cover_ok_early = None
    if cover and not cover_via:
        print("\n插封面（插完回读确认，不成换定位再来，最多三级）：")
        cover_ok_early = insert_cover_verified(doc_id, cover, as_who, proposal)

    canvases = [proposal.parent / r for r in HTML5.findall(
        proposal.read_text(encoding="utf-8"))]
    print("\n回读对账：")
    rc = reconcile(doc_id, canvases, as_who)
    cover_ok = (cover_ok_early if cover_ok_early is not None
                else report_cover(doc_id, as_who, bool(cover)))
    if run_path:
        # 披露要按**重发之后**的盘上状态重算：补完封面再 --update 的那次，
        # 收据里的 gaps 必须跟着少一条，否则 deliver 会一直印着已经修好的问题。
        rd = runstate.load(run_path) or {}
        gaps = closures(rd, Path(rd["contract"]["workdir"]))[1] \
            if rd.get("contract") else []
        runstate.add_receipt(run_path, "publish", {
            "url": url or f"https://bytedance.larkoffice.com/docx/{doc_id}",
            "documentId": doc_id, "blocks": len(canvases),
            "reconciled": rc == 0, "coverInserted": cover_ok,
            "cover": cover or None, "coverUrl": cover_url or None,
            "coverVia": cover_via or ("media-insert" if cover else None),
            "via": "update", "gaps": gaps})
    return rc


def report_cover(doc_id: str, as_who: str, attempted: bool) -> bool:
    """回读确认封面。返回值会写进收据，deliver.py 从那里读。"""
    got = cover_in_doc(doc_id, as_who)
    if got:
        print("封面对账通过：文档第 1 块是图片。")
    elif got is False:
        print("✗ 回读的文档里**没有封面图**。"
              + ("插入命令报成功但内容不在 —— 重跑一次 --cover。"
                 if attempted else
                 "发布时没带 --cover。补：\n"
                 f"    python3 {runstate.SCRIPTS}/publish.py --update <doc_id> "
                 "--proposal doc/proposal.xml --cover shots/cover.jpg"))
    else:
        print("· 封面回读不出来（fetch 失败或返回为空）—— 按没插成功处理。")
    return bool(got)


def reconcile(doc_id: str, canvases: list[Path], as_who: str) -> int:
    """把发出去的画布读回来比字节。这是唯一不能伪造的证据。"""
    tmp = Path(tempfile.mkdtemp(prefix="lark-verify-"))
    code, out = run(["lark-cli", "docs", "+fetch", "--doc", doc_id,
                     "--as", as_who, "--detail", "full"], cwd=tmp)
    if code != 0:
        print("回读失败：\n" + out[-1200:])
        return 1
    got = sorted((tmp / "doc-fetch-resources" / doc_id).glob("html5_*.html"))
    if len(got) != len(canvases):
        print(f"对账失败：本地 {len(canvases)} 块，线上回读 {len(got)} 块。")
        shutil.rmtree(tmp, ignore_errors=True)
        return 1
    bad = 0
    for local, remote in zip(canvases, got):
        a, b = local.read_bytes(), remote.read_bytes()
        same = a == b
        bad += not same
        print(f"  {'一致' if same else '不一致'}  {local.name:24} "
              f"本地 {len(a)}B  回读 {len(b)}B")
    shutil.rmtree(tmp, ignore_errors=True)
    if bad:
        print("\n有块对不上 —— 说明画布在服务端被改写或截断，不要宣布发布成功。")
        return 1
    print("\n字节级对账通过：发出去的就是本地那份。")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="飞书发布 + 回读对账 + 阻断线与披露清单")
    runstate.add_run_arg(ap)
    ap.add_argument("--proposal")
    ap.add_argument("--title")
    ap.add_argument("--as", dest="as_who", default="user")
    ap.add_argument("--verify", help="只对账：传 doc id 或 URL")
    ap.add_argument("--update", metavar="DOC_ID",
                    help="改完稿重发到同一篇：覆盖正文 → 重插封面 → 字节对账")
    ap.add_argument("--cover",
                    help="封面图（.jpg/.png；用于取尺寸；无 --cover-url 时才走媒体插入回退路径）")
    ap.add_argument("--cover-url",
                    help="封面公网 URL；会写进临时 proposal，随 +create/+update 一起发布")
    ap.add_argument("--canvas", nargs="*", default=[])
    # 这个开关不叫 --no-closure，并且写在 --help 里。
    # 模型读到它之后原话是「看看有没有办法跳过闭包（--no-closure 参数）」，
    # 然后三次发布全部带着它 —— 全部质量机制被合法绕过。
    # 它唯一正当的用途是调试包本身，而那时**不会有合同**。所以：有合同就拒绝。
    ap.add_argument("--debug-package", "--no-closure", dest="debug_package",
                    action="store_true",
                    help="只在调试包本身时用（没有合同时才允许；有合同会被拒绝）")
    a = ap.parse_args()

    run_path = runstate.find(a.run)
    run_data = runstate.load(run_path)

    if a.debug_package and run_data and run_data.get("contract"):
        print("--debug-package 被拒绝：这份 run.json 里有冻结的合同，"
              "说明这是一个真实交付。\n"
              "  这个开关只用于调试包本身。曾出现过一条真实运行 用它\n"
              "  跳过了全部闭包，三次发布 —— 截图、看图、门一次都没跑。\n"
              "  现在能拦住你的只剩「盘上没有可发的东西」，每一条都附了\n"
              "  能立刻执行的命令，照着跑就行 —— 已经没有值得绕的门了。")
        return 1

    if a.verify:
        if not shutil.which("lark-cli"):
            print("lark-cli 不可用。先 `lark-cli auth login`。")
            return 2
        doc_id = a.verify.rstrip("/").split("/")[-1]
        return reconcile(doc_id, [Path(c) for c in a.canvas], a.as_who)

    if a.update:
        if not shutil.which("lark-cli"):
            print("lark-cli 不可用。先 `lark-cli auth login`。")
            return 2
        rel = a.proposal or ((run_data or {}).get("contract") or {}).get(
            "deliverables", {}).get("doc", {}).get("proposal")
        if not rel:
            ap.error("--update 需要 --proposal 或一份带合同的 run.json")
        proposal = Path(rel)
        if not proposal.is_absolute() and run_data:
            proposal = Path(run_data["contract"]["workdir"]) / rel
        errs = preflight(proposal.resolve())
        if errs:
            print("PREFLIGHT 未通过：")
            for e in errs:
                print("  ✗ " + e)
            return 1
        return update(a.update.rstrip("/").split("/")[-1], proposal.resolve(),
                      a.cover, a.cover_url, a.as_who, run_path)

    # ── 闭包先跑：**拦住的只有"发不出去"，其余照发并披露** ──
    proposal_rel = a.proposal
    gaps: list[str] = []
    if run_data and run_data.get("contract"):
        base = Path(run_data["contract"]["workdir"])
        # 合同里有封面图就默认用它，不用每次手写 --cover。
        # 「要多打一个参数才能拿到封面」本身就是它三次都没被打上的原因。
        ci = (run_data["contract"]["deliverables"]["doc"].get("coverImage"))
        if not a.cover and ci and (base / ci).is_file():
            a.cover = str(base / ci)
        pubs = ((run_data.get("receipts") or {}).get("publish") or [])
        if not a.cover_url:
            for r in reversed(pubs):
                if r.get("coverUrl"):
                    a.cover_url = r["coverUrl"]
                    break
        proposal_rel = proposal_rel or str(base / run_data["contract"]
                                           ["deliverables"]["doc"]["proposal"])
        # **闭包和 preflight 一次报完。**
        # closures 不能先跑、不过就 return，于是 preflight 那两条
        # （图不是 data URI、画布超 500KB）要等下一轮才看得见。
        # 实测代价：发布环节曾卡了 11.5 分钟、被拒四次，
        # 每次只暴露一件事，每次都要重写画布再来一遍。
        stop, gaps = closures(run_data, base)
        # 封面参数不对**不再阻断发布**：正文照发，封面事后补。
        # 同一条教训 —— 一个不成立的前置条件把整篇文档一起挡在门外。
        cov_err = cover_arg_errors(a.cover)
        if cov_err:
            gaps += cov_err
            a.cover = None
        pf = preflight(Path(proposal_rel).resolve()) \
            if Path(proposal_rel).is_file() else []
        if stop or pf:
            print("发布被拒 —— **下面是全部问题**，一次改完再来：\n")
            auto = [e for e in pf + stop if "pack_img.py" in e or "超过飞书硬上限" in e
                    or "不是 data: URI" in e]
            manual = [e for e in pf + stop if e not in auto]
            if auto:
                print("① 一条命令能修完的：\n")
                for e in auto:
                    print("  ✗ " + e + "\n")
            if manual:
                print("② 需要你判断的：\n")
                for e in manual:
                    print("  ✗ " + e + "\n")
            # 阻断项只剩"发不出去"和"发出去是坏的"。其余全部改成披露，
            # 所以这里顺带把它们印出来 —— 一次看完，不要挤牙膏。
            if gaps:
                print("③ 不阻断发布，但这一稿还差这些：\n")
                for g in gaps:
                    print("  · " + g + "\n")
            print("这些收据全部由包内脚本自己产出，不依赖宿主、不依赖网络。\n"
                  "  不要手写收据进 run.json —— 那是出过三次的失败，"
                  "而且 check/shot 的收据里有 sha256，编不出来。")
            return 1
        a.title = a.title or run_data["contract"].get("title")
    elif not a.debug_package:
        print("找不到 run.json —— 交付合同没冻结，闭包无从谈起。\n"
              f"  {runstate.UI} brief --query \"<用户原话>\"\n"
              "  只在调试包本身时才用 --debug-package。")
        return 1
    else:
        errs = cover_arg_errors(a.cover)
        if errs:
            print("封面参数不对：")
            for e in errs:
                print("  ✗ " + e)
            return 1

    if not shutil.which("lark-cli"):
        print("lark-cli 不可用。先 `lark-cli auth login`。")
        return 2
    if not proposal_rel:
        ap.error("要么给 --proposal，要么给 --run（合同里有），要么给 --verify")

    proposal = Path(proposal_rel).resolve()
    errs = preflight(proposal)
    if errs:
        print("PREFLIGHT 未通过：")
        for e in errs:
            print("  ✗ " + e)
        return 1
    print("preflight 通过。盘上有可发的东西（proposal + 画布），开始发布。"
          + (f"\n  另有 {len(gaps)} 条「还差什么」，发完一次报给你 —— 它们不阻断交付。"
             if gaps else ""))

    proposal_to_send, cover_via = inline_cover(proposal, a.cover_url, a.cover)
    if not a.cover_url and a.cover:
        print("\n封面还差一个公网 URL（飞书 <img href> 只吃公网地址，本地路径会被静默丢弃）。\n"
              "  第一步　调用宿主工具：\n"
              f"      FileBatchUpload(path_list=[\"{Path(a.cover).resolve()}\"])\n"
              "  第二步　把返回的 uri 回填：\n"
              f"      python3 {runstate.SCRIPTS}/publish.py --run {run_path or 'run.json'} "
              "--cover-url https://aka.doubaocdn.com/s/xxxx\n"
              "  本次先走 media-insert 回退路径。")

    cmd = ["lark-cli", "docs", "+create", "--as", a.as_who,
           "--content", f"@{proposal_to_send.name}"]
    if a.title:
        cmd += ["--title", a.title]
    code, out = run(cmd, cwd=proposal_to_send.parent)
    m = DOC_URL.search(out)
    if code != 0 or not m:
        print("创建失败：\n" + out[-1500:])
        return 1
    url = m.group(0)
    doc_id = url.rstrip("/").split("/")[-1]
    blocks = re.findall(r'"block_type":\s*"html5-block"', out)
    print(f"\n已创建：{url}\n  html5-block {len(blocks)} 块")

    # 封面就在这里插 —— 不是"发布之后你记得再手跑一条命令"。
    # 那句话若只写在参照案例的 XML 注释里，实测没有一次回来做第二步。
    # 插完**立刻回读确认**，不成就换一种定位再来，最多三级。
    cover_ok_early = True if cover_via == "inline" else None
    if a.cover and not cover_via:
        print("\n插封面（插完回读确认，不成换定位再来，最多三级）：")
        cover_ok_early = insert_cover_verified(doc_id, a.cover, a.as_who, proposal)

    canvases = [proposal.parent / r for r in HTML5.findall(
        proposal.read_text(encoding="utf-8"))]
    print("\n回读对账：")
    rc = reconcile(doc_id, canvases, a.as_who)
    cover_ok = (cover_ok_early if cover_ok_early is not None
                else report_cover(doc_id, a.as_who, bool(a.cover)))
    # 披露随收据一起落盘 —— deliver.py 从这里读，不要求执行者想起来加参数。
    # 守则 S13：披露模式由收据状态自动决定。
    runstate.add_receipt(run_path, "publish", {
        "url": url, "documentId": doc_id, "blocks": len(blocks),
        "reconciled": rc == 0, "coverInserted": cover_ok,
        "cover": a.cover or None, "coverUrl": a.cover_url or None,
        "coverVia": cover_via or ("media-insert" if a.cover else None),
        "gaps": gaps})
    print(json.dumps({"url": url, "documentId": doc_id,
                      "blocks": len(blocks), "reconciled": rc == 0,
                      "coverInserted": cover_ok,
                      "coverVia": cover_via or ("media-insert" if a.cover else None),
                      "gaps": len(gaps)},
                     ensure_ascii=False))
    if gaps:
        print(f"\n文档已经在线上了。**这一稿还差这 {len(gaps)} 件事**"
              "（不阻断交付，但交付前你应该知道）：\n")
        for g in gaps:
            print("  · " + g + "\n")
        print("  补完之后重发到同一篇（不会产生第二个链接）：\n"
              f"    python3 {runstate.SCRIPTS}/publish.py --update {doc_id} "
              f"--proposal {proposal.name} --cover shots/cover.jpg")
    if rc != 0:
        print("\n回读对账没过 —— 线上那份和本地不是同一个东西，先别宣布发布成功。")
    if not runstate.orchestrated():
        print("\n**不要手抄上面这个 URL。** 少一个字符文档就打不开，"
              "卡片就是这么丢的（文档完好，卡片 404）。\n"
              f"  python3 {runstate.SCRIPTS}/deliver.py --run "
              f"{run_path or 'run.json'}    ← 它出可直接粘贴的参数")
    return rc


if __name__ == "__main__":
    sys.exit(main())
