#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""没有可用的 Pillow 也要量得到像素。

**为什么本包需要它。** 很多机器的默认解释器不带 Pillow，也有机器上的 Pillow
是装坏的：`import PIL` 成功，`from PIL import Image` 抛 `cannot import name
'_imaging'`，或者干脆挂住。而像素类判据普遍写着 `except Exception: return None`
—— 于是它们**全部静默**，打印出来的样子与"全都合格"一模一样：安静区、
忙碌度、主体区、大罩、叠图，一条都没有跑过，链条却全绿。
**一条量不到东西的判据比没有判据更贵**，因为它还占着"已经查过了"的位置。

这份模块用**标准库**实现判据真正用到的那一小片 PIL 接口，并在真 Pillow
不可用时挂进 `sys.modules["PIL"]`，让 `deck.py` 一个字都不用改。

**JPEG 只解 DC 系数**：每个 8×8 块出一个像素，得到 1/8 缩略图。判据要的正是
这一档——安静区网格 20px、忙碌度网格 20px，都比 1/8 还粗。

**做不到的事要说清**：不做 IDCT（拿不到块内细节）、不支持 Adam7 交错 PNG、
渐进 JPEG 只解第一遍 DC 扫描、不支持 WebP/GIF/BMP。遇到解不动的图返回 None，
让判据保持沉默——**沉默要比猜一个结论好**，但沉默必须被上层记成"没量过"，
不是"没问题"。

用法（`deck.py` 在导入 PIL 之前调一次）：

    import pixels
    source = pixels.install()      # "pillow" 或 "stdlib"
    gaps = pixels.selfcheck()      # 空列表＝本次运行的像素接口都能用
"""
from __future__ import annotations

import io
import struct
import sys
import types
import zlib
from pathlib import Path
from typing import Any

__all__ = ["install", "real_pil_works", "diagnose", "selfcheck", "Image", "SOURCE"]

#: 本次运行的像素来源，供 hostcheck / 判据打印时如实说明。
SOURCE = "stdlib"

_CHANNELS = {"L": 1, "RGB": 3, "RGBA": 4}

#: 解过的图按 (路径, mtime, 大小) 缓存。判据会为同一页反复拼底图。
_CACHE: dict[tuple, "Img"] = {}
_CACHE_MAX = 48
# ────────────────────────────────────────────────────────── 探测真 Pillow

#: 探测超时（秒）。超时即判定"真 Pillow 不可用"，走标准库实现。
PROBE_TIMEOUT = 5.0
#: 探测结果的缓存有效期（秒）。同一台机器只付一次钱。
PROBE_TTL = 7 * 24 * 3600
#: 上一次探测是怎么结束的，供 hostcheck 如实打印。
PROBE_VERDICT = "未探测"


def _probe_cache_path() -> Path:
    """探测结果落在用户缓存目录，不写进 Skill 包（包目录可能只读）。"""
    import os  # noqa: PLC0415
    base = os.environ.get("XDG_CACHE_HOME") or ""
    if not base:
        try:
            base = str(Path.home() / ".cache")
        except Exception:  # noqa: BLE001 - 没有 HOME 的环境
            base = ""
    if not base:
        import tempfile  # noqa: PLC0415
        base = tempfile.gettempdir()
    return Path(base) / "doubao-visual-creative" / "pixel-probe.json"


def _probe_key() -> str:
    """缓存键 = 解释器 + PIL 包文件的 mtime/大小。

    `find_spec` **不执行**目标模块，所以拿这个键的代价是一次文件系统查询，
    不会碰 C 扩展。装了新 Pillow 或换了解释器，键就变，缓存自然失效。
    """
    import importlib.util  # noqa: PLC0415
    parts = [sys.executable, sys.version.split()[0]]
    try:
        spec = importlib.util.find_spec("PIL")
        origin = getattr(spec, "origin", None) if spec else None
        if origin:
            st = Path(origin).stat()
            parts += [origin, str(int(st.st_mtime)), str(st.st_size)]
        else:
            parts.append("no-PIL")
    except Exception:  # noqa: BLE001 - 找不到就当没有
        parts.append("no-PIL")
    return "|".join(parts)


def _probe_in_subprocess(timeout: float) -> bool:
    """在子进程里碰一次 C 扩展。**父进程永远不 import PIL。**

    为什么必须隔一层进程：坏掉/未签名/被安全软件扫描的 `_imaging` 扩展
    会让 `from PIL import Image` 阻塞几十秒到几分钟，而且**不响应信号**——
    在父进程里做这件事，`hostcheck / check / ground / shots` 每一条命令
    都要先交这笔钱，超时也打断不了。子进程可以被 `timeout` 直接杀掉。
    """
    import subprocess  # noqa: PLC0415
    code = ("from PIL import Image;"
            "Image.new('RGB',(2,2)).resize((1,1)).convert('L');"
            "print('ok')")
    try:
        done = subprocess.run([sys.executable, "-c", code],
                              capture_output=True, timeout=timeout, check=False)
    except Exception:  # noqa: BLE001 - 超时、找不到解释器、权限，都算不可用
        return False
    return done.returncode == 0 and b"ok" in (done.stdout or b"")


def real_pil_works(timeout: float | None = None) -> bool:
    """真 Pillow 能不能用。**在子进程里碰一次 C 扩展，结果按机器缓存。**

    只 `import PIL` 会通过——坏掉的 Pillow 里 `PIL/__init__.py` 是好的，
    死在 `PIL.Image` 那一层。所以探测必须真的碰一下扩展；
    而"真的碰一下"在部分机器上会挂死，所以它必须发生在**子进程**里、**带超时**、
    并且**只做一次**。
    """
    global PROBE_VERDICT  # noqa: PLW0603 - 供 hostcheck 打印
    import json  # noqa: PLC0415
    import time  # noqa: PLC0415
    limit = PROBE_TIMEOUT if timeout is None else timeout
    key = _probe_key()
    cache = _probe_cache_path()
    try:
        blob = json.loads(cache.read_text(encoding="utf-8"))
        if blob.get("key") == key and time.time() - float(blob.get("at", 0)) < PROBE_TTL:
            PROBE_VERDICT = "缓存命中（%s）" % ("可用" if blob.get("ok") else "不可用")
            return bool(blob.get("ok"))
    except Exception:  # noqa: BLE001 - 没缓存/读不动都当没探测过
        pass
    start = time.time()
    ok = _probe_in_subprocess(limit)
    spent = time.time() - start
    PROBE_VERDICT = ("可用（%.2fs）" % spent) if ok else (
        "超时 %.0fs → 按标准库走" % limit if spent >= limit - 0.05
        else "不可用（%.2fs）" % spent)
    try:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps({"key": key, "ok": ok, "at": time.time(),
                                     "verdict": PROBE_VERDICT}), encoding="utf-8")
    except Exception:  # noqa: BLE001 - 缓存写不进去不影响正确性
        pass
    return ok


def diagnose() -> tuple[str, list[str]]:
    """真 Pillow 不可用时，说清**是哪一种不可用**，并给出对得上的修法。

    两种形态完全不同：
      · **抛异常**——缺依赖／架构不对／文件残缺。
      · **挂起**——`dlopen()` 卡在系统的安全校验上，且不响应信号。

    挂起那一档的关键事实：坏状态**绑在那几个 `.so` 文件本身**上，不是绑在目录或
    解释器上——把同一批文件复制一份放到**同一个 site-packages 里**，新副本立刻能加载，
    原来那几个仍然挂住。常见来源是这些文件带过下载来源标记（部分系统会为下载文件
    打隔离属性），标记被清掉之后坏状态也不会自己恢复。

    所以修法是**换掉这些文件**，而且必须带 `--force-reinstall`：
    不带的话 pip 看到"已安装"就什么都不做——这正是"重装了一次，没有任何变化"的来处。
    **印一条修不好的修法，比不印更糟**：执行者照做一遍没变化，从此不再信这一行。
    """
    hints: list[str] = []
    timed_out = "超时" in (PROBE_VERDICT or "")
    shape = "加载 C 扩展时**挂起**" if timed_out else "`PIL.Image` 加载失败"
    if timed_out:
        hints.append("这一档的坏状态绑在那几个 `.so` 文件上（同目录下放一份新副本就正常），"
                     "所以要**换掉文件**，而且必须带 `--force-reinstall`——"
                     "不带的话 pip 看到已安装就什么都不做：")
        hints.append(f'    "{sys.executable}" -m pip install --user '
                     "--force-reinstall --no-cache-dir pillow")
        hints.append("    （命令里写死的是**正在跑本脚本的解释器**——PATH 上的 python3 "
                     "常常是另一个，装错解释器等于没装；"
                     "若报 externally-managed-environment 就再加 --break-system-packages）")
        marked = _quarantined_pil()
        if marked:
            hints.append("    这批文件现在还带着下载来源标记，多半就是它引来的反复校验；"
                         "重装会写入不带标记的新文件。")
    else:
        hints.append(f'    "{sys.executable}" -m pip install --user '
                     "--force-reinstall --no-cache-dir pillow")
        hints.append("    （命令里写死的是**正在跑本脚本的解释器**，装到 PATH 上另一个 "
                     "python3 等于没装；若报 externally-managed-environment 就再加 "
                     "--break-system-packages）")
    hints.append("    装完重跑 `hostcheck`，【像素测量能力】那一行要变成「走 Pillow」。")
    hints.append("    装不上也不阻塞：像素判据会走包内标准库解码器（1/8 精度，"
                 "够用于安静区与忙碌度）；但抠图（floodfill）这类**改图**的动作仍然需要真 Pillow。")
    return shape, hints


def _quarantined_pil() -> str:
    """PIL 的 C 扩展带不带隔离属性；带就返回那个包目录，否则空串。

    **不能 import PIL 来定位它**（那正是会挂住的动作），只按路径找。
    也不能用 `find_spec`：`install()` 之后 `PIL` 已经被本模块顶掉了。
    """
    import subprocess  # noqa: PLC0415
    if sys.platform != "darwin":
        return ""
    for base in sys.path:
        if not base:
            continue
        folder = Path(base) / "PIL"
        try:
            if not folder.is_dir():
                continue
            cores = sorted(folder.glob("_imaging*.so"))
        except OSError:
            continue
        if not cores:
            continue
        try:
            done = subprocess.run(
                ["xattr", "-p", "com.apple.quarantine", str(cores[0])],
                capture_output=True, timeout=5, check=False)
        except Exception:  # noqa: BLE001 - 没有 xattr／超时都当"查不出来"
            return ""
        if done.returncode == 0 and (done.stdout or b"").strip():
            return str(folder)
    return ""


def install() -> str:
    """真 Pillow 不可用时把本模块挂成 `PIL`。返回本次运行的像素来源。

    挂进 `sys.modules` 而不是改每一处 `from PIL import Image`：
    改散在各处的导入点，漏掉一个就又是一族静默判据。
    """
    global SOURCE  # noqa: PLW0603 - hostcheck 与判据都要如实打印本次运行的来源
    import os  # noqa: PLC0415
    # 逃生阀：机器上的 Pillow 行为可疑时可以强制走标准库解码器；
    # 回归测试也靠它把**两条分支**都跑一遍（只测一条等于只有一半实现被验证过）。
    forced = (os.environ.get("DECK_PIXELS") or "").strip().lower()
    if forced not in ("stdlib", "pillow", ""):
        forced = ""
    if forced != "stdlib" and (forced == "pillow" or real_pil_works()):
        SOURCE = "pillow"
        return "pillow"
    SOURCE = "stdlib"
    pil = types.ModuleType("PIL")
    pil.Image = Image           # type: ignore[attr-defined]
    pil.__version__ = "stdlib-fallback"
    sys.modules["PIL"] = pil
    sys.modules["PIL.Image"] = Image  # type: ignore[assignment]
    return "stdlib"


#: 本包在像素上真正会调到的接口。**改 deck.py 时同步改这里**——
#: 回退实现少一个方法，上层的 `except` 接不住 `AttributeError`，
#: 打印出来会是"像素测量不可用"，而执行者会把它读成"这一页没问题"。
USED_API = ("new", "open", "convert", "resize", "load", "size",
            "getpixel", "crop", "paste", "save", "split", "getdata")


def selfcheck() -> list[str]:
    """跑一遍判据真正会调的那几个接口，缺一个就点名。

    量不到 ≠ 合格；而"量不到"如果连自己都不知道，就连披露都做不到。
    所以这一条必须在 `hostcheck` 里跑，并把结果如实打印出来。
    """
    from PIL import Image as _I  # noqa: PLC0415 - 此时 sys.modules 里已是本轮的实现
    bad: list[str] = []
    try:
        im = _I.new("RGB", (8, 6), (10, 20, 30))
        checks = (
            ("new", lambda: im.size == (8, 6)),
            ("size", lambda: im.size == (8, 6)),
            ("convert", lambda: im.convert("L").size == (8, 6)),
            ("resize", lambda: im.resize((4, 3)).size == (4, 3)),
            ("load", lambda: im.load()[0, 0] == (10, 20, 30)),
            ("getpixel", lambda: im.getpixel((1, 1)) == (10, 20, 30)),
            ("crop", lambda: im.crop((0, 0, 4, 3)).size == (4, 3)),
            ("split", lambda: len(im.split()) == 3),
            ("getdata", lambda: len(list(im.getdata())) == 48),
            ("paste", lambda: im.copy().paste(_I.new("RGB", (2, 2), (1, 1, 1)),
                                              (0, 0)) is None),
            ("open/PNG", _roundtrip_png),
            ("open/JPEG", _roundtrip_jpeg),
        )
        for name, run in checks:
            try:
                if not run():
                    bad.append(name + "（返回值不对）")
            except Exception as exc:  # noqa: BLE001
                bad.append(f"{name}（{type(exc).__name__}: {exc}）")
    except Exception as exc:  # noqa: BLE001
        bad.append(f"Image.new（{type(exc).__name__}: {exc}）")
    return bad


def _roundtrip_png() -> bool:
    """写一张 PNG 再读回来——`save` 与 `open` 必须能对上。"""
    from PIL import Image as _I  # noqa: PLC0415
    import tempfile  # noqa: PLC0415
    canvas = _I.new("RGB", (12, 8), (200, 40, 30))
    with tempfile.TemporaryDirectory() as box:
        path = Path(box) / "probe.png"
        canvas.save(path)
        back = _I.open(path).convert("RGB")
        if back.size != (12, 8):
            return False
        r, g, b = back.load()[3, 3]
        return abs(r - 200) <= 4 and abs(g - 40) <= 4 and abs(b - 30) <= 4


#: 一张 16×16 中灰的基线 JPEG（最小可解样本，用来自证 DC 解码通路活着）。
_PROBE_JPEG = (
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAYEBQYFBAYGBQYHBwYIChAKCgkJChQODwwQFxQY"
    "GBcUFhYaHSUfGhsjHBYWICwgIyYnKSopGR8tMC0oMCUoKSj/2wBDAQcHBwoIChMKChMoGhYa"
    "KCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCj/wAAR"
    "CAAQABADASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAA"
    "AgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkK"
    "FhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWG"
    "h4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl"
    "5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREA"
    "AgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYk"
    "NOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOE"
    "hYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk"
    "5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwAooooA/9k="
)


def _roundtrip_jpeg() -> bool:
    """解一张已知 JPEG——只要求尺寸对、像素在合理区间（DC 重建有量化误差）。"""
    import base64  # noqa: PLC0415
    import io as _io  # noqa: PLC0415
    from PIL import Image as _I  # noqa: PLC0415
    # 用 BytesIO 而不是裸 bytes：真 Pillow 的 `open` 只吃路径或文件对象，
    # 而自检必须在**两种实现上都通过**，否则它会把真 Pillow 误判成缺口。
    im = _I.open(_io.BytesIO(base64.b64decode(_PROBE_JPEG))).convert("RGB")
    if im.size != (16, 16):
        return False
    r, g, b = im.load()[8, 8]
    return 90 <= r <= 170 and 90 <= g <= 170 and 90 <= b <= 170
# ────────────────────────────────────────────────────────── 像素访问

class _Access:
    """`img.load()` 返回的东西：`px[x, y]` 取值、赋值。

    坐标是**逻辑坐标**（`img.size`），内部按数据分辨率折算——
    JPEG 的数据只有 1/8，但上层不需要知道。
    """

    __slots__ = ("_img",)

    def __init__(self, img: "Img") -> None:
        self._img = img

    def _index(self, xy: tuple[int, int]) -> int:
        img = self._img
        x, y = xy
        dx = x * img._dw // max(1, img.size[0])
        dy = y * img._dh // max(1, img.size[1])
        dx = min(max(dx, 0), img._dw - 1)
        dy = min(max(dy, 0), img._dh - 1)
        return (dy * img._dw + dx) * img._n

    def __getitem__(self, xy: tuple[int, int]) -> Any:
        img = self._img
        i = self._index(xy)
        if img._n == 1:
            return img._data[i]
        return tuple(img._data[i:i + img._n])

    def __setitem__(self, xy: tuple[int, int], value: Any) -> None:
        img = self._img
        i = self._index(xy)
        if img._n == 1:
            img._data[i] = int(value) & 0xFF
        else:
            seq = tuple(value)
            for k in range(img._n):
                img._data[i + k] = int(seq[k] if k < len(seq) else 255) & 0xFF


class Img:
    """一张位图。`size` 是逻辑尺寸，`_dw/_dh` 是真实存着的分辨率。

    两者分开是为了 JPEG：数据只有 1/8，而上层拿到的 `size` 必须是真尺寸，
    否则 `resize((960,540))` 会按错误的基准算。
    """

    __slots__ = ("mode", "size", "_dw", "_dh", "_n", "_data", "_tex")

    def __init__(self, mode: str, size: tuple[int, int], data: bytearray | None = None,
                 dims: tuple[int, int] | None = None, tex: bytearray | None = None) -> None:
        self.mode = mode
        self.size = (int(size[0]), int(size[1]))
        self._n = _CHANNELS[mode]
        self._dw, self._dh = dims or self.size
        self._dw = max(1, int(self._dw))
        self._dh = max(1, int(self._dh))
        self._data = data if data is not None else bytearray(self._dw * self._dh * self._n)
        self._tex = tex

    # ---- 基本

    @property
    def width(self) -> int:
        return self.size[0]

    @property
    def height(self) -> int:
        return self.size[1]

    def load(self) -> _Access:
        return _Access(self)

    def copy(self) -> "Img":
        return Img(self.mode, self.size, bytearray(self._data), (self._dw, self._dh),
                   bytearray(self._tex) if self._tex else None)

    def getpixel(self, xy: tuple[int, int]) -> Any:
        return _Access(self)[xy]

    def putpixel(self, xy: tuple[int, int], value: Any) -> None:
        _Access(self)[xy] = value

    # ---- 逐点读取
    #
    # **这一组是判据真正在用的接口，缺一个就等于整族判据静默。**
    # `list(im.getdata())` 出现在对比度、底纹体检、资产指标、拼贴分析里；
    # 缺它时抛的是 AttributeError，而上层的 `except ImportError` 接不住，
    # 打印出来是"像素测量不可用"——执行者会把它读成"这一页没问题"。

    def getdata(self, band: int | None = None) -> list:
        """按**逻辑坐标**逐行返回像素，长度 = width × height。

        内部数据分辨率可能只有 1/8（JPEG 只解 DC），这里按逻辑尺寸重采样，
        让上层拿到的长度与真 Pillow 一致——上层普遍写 `px[y * w + x]`。
        """
        access = _Access(self)
        w, h = self.size
        out = []
        for y in range(h):
            for x in range(w):
                value = access[x, y]
                if band is not None and isinstance(value, tuple):
                    value = value[band]
                out.append(value)
        return out

    def getchannel(self, channel: Any) -> "Img":
        """取单通道，返回 L 模式图。接受序号或 'R'/'G'/'B'/'A'。"""
        if isinstance(channel, str):
            channel = {"R": 0, "G": 1, "B": 2, "A": 3, "L": 0}.get(channel.upper(), 0)
        planes = self.split()
        if not planes:
            return self.convert("L")
        return planes[min(int(channel), len(planes) - 1)]

    def getextrema(self) -> Any:
        """单通道返回 (min, max)；多通道返回每通道一组，与真 Pillow 一致。"""
        n, data = self._n, self._data
        pairs = []
        for k in range(n):
            plane = data[k::n]
            pairs.append((min(plane) if plane else 0, max(plane) if plane else 0))
        return pairs[0] if n == 1 else tuple(pairs)

    def getcolors(self, maxcolors: int = 256) -> Any:
        """返回 [(count, color), …]；颜色数超过 maxcolors 时返回 None（同真 Pillow）。"""
        tally: dict[Any, int] = {}
        for value in self.getdata():
            tally[value] = tally.get(value, 0) + 1
            if len(tally) > maxcolors:
                return None
        return sorted(((c, v) for v, c in tally.items()), reverse=True)

    def quantize(self, colors: int = 256, **_kw: Any) -> "Img":
        """把颜色数压到 ≤ colors。

        真 Pillow 走中位切分，这里走**均匀分桶**：判据只用它数"有几种颜色、
        最大一块占多少"，桶的选法不影响这两个数的量级，而实现代价低一个数量级。
        """
        rgb = self.convert("RGB")
        levels = max(2, min(8, int(round(max(2, colors) ** (1.0 / 3.0)))))
        step = 256.0 / levels
        data = bytearray(rgb._data)
        for i, value in enumerate(data):
            bucket = min(levels - 1, int(value / step))
            data[i] = int(min(255, round(bucket * step + step / 2)))
        return Img("RGB", rgb.size, data, (rgb._dw, rgb._dh),
                   bytearray(rgb._tex) if rgb._tex else None)

    # ---- 模式

    def convert(self, mode: str) -> "Img":
        if mode == self.mode:
            return self
        if mode not in _CHANNELS:
            raise ValueError(f"不支持的模式 {mode}")
        n_out = _CHANNELS[mode]
        src, n_in = self._data, self._n
        out = bytearray(self._dw * self._dh * n_out)
        for i in range(self._dw * self._dh):
            si, di = i * n_in, i * n_out
            if n_in == 1:
                r = g = b = src[si]
                a = 255
            else:
                r, g, b = src[si], src[si + 1], src[si + 2]
                a = src[si + 3] if n_in == 4 else 255
            if n_out == 1:
                out[di] = int(0.299 * r + 0.587 * g + 0.114 * b) & 0xFF
            else:
                out[di], out[di + 1], out[di + 2] = r, g, b
                if n_out == 4:
                    out[di + 3] = a
        return Img(mode, self.size, out, (self._dw, self._dh), self._tex)

    def split(self) -> tuple["Img", ...]:
        planes = []
        for k in range(self._n):
            buf = bytearray(self._data[k::self._n])
            planes.append(Img("L", self.size, buf, (self._dw, self._dh)))
        return tuple(planes)

    # ---- 几何

    def resize(self, size: tuple[int, int], resample: Any = None) -> "Img":
        """缩放。**缩小时做面积平均**（等价 PIL 的 BOX），放大时只改逻辑尺寸。

        放大不重采样是有意的：数据本来就没有那么多信息，
        真去插值只是把同一份数据摊大，还多烧十几倍时间。
        """
        _ = resample
        w, h = max(1, int(size[0])), max(1, int(size[1]))
        if w >= self._dw and h >= self._dh:
            out = Img(self.mode, (w, h), self._data, (self._dw, self._dh), self._tex)
            return out
        dw, dh = min(w, self._dw), min(h, self._dh)
        n = self._n
        src, out = self._data, bytearray(dw * dh * n)
        tex_in, tex_out = self._tex, (bytearray(dw * dh) if self._tex else None)
        # **热路径要先把索引算完，再在内层只做加法。**
        # 逐点重算 `x0/x1` 与逐通道 `acc[k] += …` 是这条实现最贵的两处；
        # 一次完整校验会调它上百次（安静区、忙碌度、承文形、接缝各一遍），
        # 于是十几秒全花在同一段三重循环里。这里预先算好每一列的源区间，
        # 单通道再走一条不拆通道的快路。
        xs = [(ox * self._dw // dw, max(ox * self._dw // dw + 1, (ox + 1) * self._dw // dw))
              for ox in range(dw)]
        for oy in range(dh):
            y0 = oy * self._dh // dh
            y1 = max(y0 + 1, (oy + 1) * self._dh // dh)
            rows = range(y0, y1)
            obase = oy * dw
            for ox in range(dw):
                x0, x1 = xs[ox]
                count = (y1 - y0) * (x1 - x0) or 1
                o = (obase + ox) * n
                if n == 1:
                    acc0 = 0
                    for yy in rows:
                        base = yy * self._dw
                        acc0 += sum(src[base + x0:base + x1])
                    out[o] = acc0 // count
                else:
                    acc = [0] * n
                    for yy in rows:
                        base = (yy * self._dw + x0) * n
                        for _ in range(x1 - x0):
                            for k in range(n):
                                acc[k] += src[base + k]
                            base += n
                    for k in range(n):
                        out[o + k] = acc[k] // count
                if tex_out is not None and tex_in is not None:
                    tacc = 0
                    for yy in rows:
                        base = yy * self._dw
                        tacc += sum(tex_in[base + x0:base + x1])
                    tex_out[obase + ox] = min(255, tacc // count)
        return Img(self.mode, (w, h), out, (dw, dh), tex_out)

    def thumbnail(self, size: tuple[int, int], resample: Any = None) -> None:
        w, h = self.size
        scale = min(size[0] / max(w, 1), size[1] / max(h, 1), 1.0)
        new = self.resize((max(1, int(w * scale)), max(1, int(h * scale))), resample)
        self.mode, self.size = new.mode, new.size
        self._n, self._dw, self._dh = new._n, new._dw, new._dh
        self._data, self._tex = new._data, new._tex

    def crop(self, box: tuple[int, int, int, int]) -> "Img":
        left, top, right, bottom = (int(v) for v in box)
        w, h = max(0, right - left), max(0, bottom - top)
        if w <= 0 or h <= 0:
            return Img(self.mode, (max(w, 1), max(h, 1)))
        sx = self._dw / max(1, self.size[0])
        sy = self._dh / max(1, self.size[1])
        dl, dt = int(left * sx), int(top * sy)
        dr, db = max(dl + 1, int(right * sx)), max(dt + 1, int(bottom * sy))
        dl, dt = max(0, min(dl, self._dw - 1)), max(0, min(dt, self._dh - 1))
        dr, db = max(dl + 1, min(dr, self._dw)), max(dt + 1, min(db, self._dh))
        dw, dh, n = dr - dl, db - dt, self._n
        out = bytearray(dw * dh * n)
        tex = bytearray(dw * dh) if self._tex else None
        for y in range(dh):
            si = ((dt + y) * self._dw + dl) * n
            out[y * dw * n:(y + 1) * dw * n] = self._data[si:si + dw * n]
            if tex is not None:
                s2 = (dt + y) * self._dw + dl
                tex[y * dw:(y + 1) * dw] = self._tex[s2:s2 + dw]
        return Img(self.mode, (w, h), out, (dw, dh), tex)

    def paste(self, other: Any, box: tuple[int, int] | None = None,
              mask: Any = None) -> None:
        """把 `other` 贴到 `(x, y)`。`mask` 只认 RGBA 的 alpha（判据只用这一种）。"""
        x0, y0 = (box or (0, 0))[:2]
        if not isinstance(other, Img):                     # 纯色填充
            colour = other
            src = Img(self.mode, (1, 1))
            _Access(src)[0, 0] = colour
            other = src
        sx = other._dw / max(1, other.size[0])
        sy = other._dh / max(1, other.size[1])
        dx0 = int(x0 * self._dw / max(1, self.size[0]))
        dy0 = int(y0 * self._dh / max(1, self.size[1]))
        dwid = max(1, int(other.size[0] * self._dw / max(1, self.size[0])))
        dhei = max(1, int(other.size[1] * self._dh / max(1, self.size[1])))
        n = self._n
        # **不透明整块贴入走行切片。** 判据里最常见的 paste 是"把一张底图铺进画布"，
        # 没有 mask、通道数一致、缩放比 1:1——那一档逐点搬运是纯粹的浪费，
        # 一次完整校验里它占掉的时间比任何一条判据都多。
        if (mask is None and other._n == n and dwid == other._dw and dhei == other._dh):
            for y in range(dhei):
                ty = dy0 + y
                if not 0 <= ty < self._dh:
                    continue
                lo = max(0, -dx0)
                hi = min(dwid, self._dw - dx0)
                if hi <= lo:
                    continue
                si = (y * other._dw + lo) * n
                ti = (ty * self._dw + dx0 + lo) * n
                self._data[ti:ti + (hi - lo) * n] = other._data[si:si + (hi - lo) * n]
            if self._tex is not None and other._tex is not None:
                for y in range(dhei):
                    ty = dy0 + y
                    if not 0 <= ty < self._dh:
                        continue
                    lo = max(0, -dx0)
                    hi = min(dwid, self._dw - dx0)
                    if hi <= lo:
                        continue
                    self._tex[ty * self._dw + dx0 + lo: ty * self._dw + dx0 + hi] = \
                        other._tex[y * other._dw + lo: y * other._dw + hi]
            return
        for y in range(dhei):
            ty = dy0 + y
            if not 0 <= ty < self._dh:
                continue
            oy = min(other._dh - 1, int(y * other._dh / dhei))
            for x in range(dwid):
                tx = dx0 + x
                if not 0 <= tx < self._dw:
                    continue
                ox = min(other._dw - 1, int(x * other._dw / dwid))
                si = (oy * other._dw + ox) * other._n
                if mask is not None:
                    m = mask
                    mi = (min(m._dh - 1, int(y * m._dh / dhei)) * m._dw
                          + min(m._dw - 1, int(x * m._dw / dwid))) * m._n
                    alpha = m._data[mi + m._n - 1] if m._n in (2, 4) else m._data[mi]
                    if alpha == 0:
                        continue
                else:
                    alpha = 255
                ti = (ty * self._dw + tx) * n
                if other._n == 1:
                    rgb = (other._data[si],) * 3
                else:
                    rgb = (other._data[si], other._data[si + 1], other._data[si + 2])
                for k in range(min(n, 3)):
                    if alpha >= 255:
                        self._data[ti + k] = rgb[k]
                    else:
                        self._data[ti + k] = (self._data[ti + k] * (255 - alpha)
                                              + rgb[k] * alpha) // 255
                if n == 4:
                    self._data[ti + 3] = 255
        _ = sx, sy

    # ---- 落盘
    def save(self, path: Any, *_args: Any, **_kw: Any) -> None:
        """只写 PNG 字节（格式永远是 PNG，无论文件名后缀写的是什么）。

        **落盘必须按逻辑尺寸，不能按内部数据尺寸。** JPEG 只解 DC 系数时
        内部数据是 1/8（见模块顶部），而 `size` 报的是真尺寸。从前这里直接写
        `_dw × _dh`，于是"裁一块 400×540 存成资产"落到磁盘上是 50×68 的文件，
        宿主再把它放大 8 倍铺满图窗——成稿上就是一张糊图，而本地一切正常。
        （标定：曾出现 12 页稿中两页主视觉糊掉而 XML、门、收据全绿的情况。）

        逐点重采样救不回已经丢掉的信息，所以尺寸对上之后还要**说出来**：
        这张图是 DC 重建，能用来量，不该当成稿资产。
        """
        rgb = self.convert("RGB") if self.mode != "RGB" else self
        if (rgb._dw, rgb._dh) != tuple(rgb.size):
            coarse = (rgb._dw, rgb._dh)
            # `resize` 放大时**只改逻辑尺寸不动数据**（那是给判据省时间的有意设计），
            # 所以这里不能指望它铺开——按逻辑坐标逐点取一遍，自己铺。
            lw, lh = int(rgb.size[0]), int(rgb.size[1])
            access = _Access(rgb)
            grown = bytearray(lw * lh * 3)
            for y in range(lh):
                row = y * lw * 3
                for x in range(lw):
                    px = access[x, y]
                    i = row + x * 3
                    grown[i] = px[0]
                    grown[i + 1] = px[1]
                    grown[i + 2] = px[2]
            rgb = Img("RGB", (lw, lh), grown, (lw, lh), None)
            sys.stderr.write(
                "PIXELS 警告：这张图是标准库回退的 DC 重建（内部只有 "
                f"{coarse[0]}×{coarse[1]}，逻辑尺寸 {rgb.size[0]}×{rgb.size[1]}）。"
                f"已按逻辑尺寸落盘 {Path(str(path)).name}，但**清晰度救不回来**——"
                "它只能用来量（对比度/空白带/底纹），"
                "✗ 不要把它当成稿资产发给宿主，成稿上会是一张糊图。"
                "要真的裁图：装 Pillow（`deck.py hostcheck` 会打印本机该跑哪条 pip），"
                "或者用 image_gen 按目标尺寸重生成一张。\n")
        raw = bytearray()
        for y in range(rgb._dh):
            raw.append(0)
            i = y * rgb._dw * 3
            raw += rgb._data[i:i + rgb._dw * 3]

        def chunk(tag: bytes, payload: bytes) -> bytes:
            body = tag + payload
            return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body))

        blob = (b"\x89PNG\r\n\x1a\n"
                + chunk(b"IHDR", struct.pack(">IIBBBBB", rgb._dw, rgb._dh, 8, 2, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(bytes(raw), 6))
                + chunk(b"IEND", b""))
        Path(str(path)).write_bytes(blob)
# ────────────────────────────────────────────────────────── PNG

def _decode_png(blob: bytes) -> Img | None:
    if blob[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    pos, width, height, depth, ctype, interlace = 8, 0, 0, 8, 6, 0
    idat = bytearray()
    palette = b""
    trns = b""
    while pos + 8 <= len(blob):
        length = struct.unpack(">I", blob[pos:pos + 4])[0]
        tag = blob[pos + 4:pos + 8]
        body = blob[pos + 8:pos + 8 + length]
        pos += 12 + length
        if tag == b"IHDR":
            width, height, depth, ctype, _c, _f, interlace = struct.unpack(">IIBBBBB", body)
        elif tag == b"PLTE":
            palette = body
        elif tag == b"tRNS":
            trns = body
        elif tag == b"IDAT":
            idat += body
        elif tag == b"IEND":
            break
    if not width or not height or interlace:
        return None                      # Adam7 交错不解，交给上层沉默
    try:
        raw = zlib.decompress(bytes(idat))
    except zlib.error:
        return None
    samples = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}.get(ctype)
    if samples is None or depth not in (8, 16):
        return None
    bpp = samples * (depth // 8)
    stride = width * bpp
    if len(raw) < (stride + 1) * height:
        return None
    prev = bytearray(stride)
    rows: list[bytearray] = []
    off = 0
    for _y in range(height):
        ftype = raw[off]
        line = bytearray(raw[off + 1:off + 1 + stride])
        off += 1 + stride
        if ftype == 1:
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 0xFF
        elif ftype == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif ftype == 3:
            for i in range(stride):
                left = line[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + ((left + prev[i]) >> 1)) & 0xFF
        elif ftype == 4:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                b = prev[i]
                c = prev[i - bpp] if i >= bpp else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pred = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pred) & 0xFF
        rows.append(line)
        prev = line
    step = depth // 8
    out = bytearray(width * height * 4)
    for y in range(height):
        line = rows[y]
        for x in range(width):
            i = x * bpp
            if ctype == 3:
                idx = line[i]
                base = idx * 3
                r = palette[base] if base + 2 < len(palette) else 0
                g = palette[base + 1] if base + 2 < len(palette) else 0
                b = palette[base + 2] if base + 2 < len(palette) else 0
                a = trns[idx] if idx < len(trns) else 255
            elif ctype in (0, 4):
                r = g = b = line[i]
                a = line[i + step] if ctype == 4 else 255
            else:
                r, g, b = line[i], line[i + step], line[i + 2 * step]
                a = line[i + 3 * step] if ctype == 6 else 255
            o = (y * width + x) * 4
            out[o], out[o + 1], out[o + 2], out[o + 3] = r, g, b, a
    return Img("RGBA", (width, height), out, (width, height))


# ────────────────────────────────────────────────────────── JPEG（只解 DC）

_ZIGZAG_FIRST = 0


#: 快查表位宽。12 位覆盖真实图里绝大多数霍夫曼码，一次查表出结果；
#: 更长的码在同一个循环里逐位延长（**不要因此整张退回慢解码器**——
#: 长码在照片的 AC 表里很常见，一退就等于快路白写）。
#: 不做这一层时一张 2048×1152 要 1.8 秒，12 页稿光解图就是半分钟。
_FAST_BITS = 12


class _BitReader:
    """JPEG 熵编码位流。0xFF00 填充与 RSTn 标记都在这里处理。"""

    __slots__ = ("data", "pos", "bits", "nbits", "end")

    def __init__(self, data: bytes, pos: int) -> None:
        self.data, self.pos, self.bits, self.nbits = data, pos, 0, 0
        self.end = len(data)

    def _feed(self, want: int) -> None:
        data, pos, end = self.data, self.pos, self.end
        bits, nbits = self.bits, self.nbits
        while nbits < want:
            if pos >= end:
                bits = (bits << 8)
                nbits += 8
                continue
            byte = data[pos]
            pos += 1
            if byte == 0xFF:
                nxt = data[pos] if pos < end else 0
                if nxt == 0x00:
                    pos += 1
                else:
                    # 碰到真标记（RSTn/EOI）：退回去，往流里补 0，
                    # 由 align_restart 决定怎么继续。吞掉标记会解出一张噪声图。
                    pos -= 1
                    byte = 0
            bits = (bits << 8) | byte
            nbits += 8
        self.pos, self.bits, self.nbits = pos, bits, nbits

    def peek(self, count: int) -> int:
        if self.nbits < count:
            self._feed(count)
        return (self.bits >> (self.nbits - count)) & ((1 << count) - 1)

    def skip(self, count: int) -> None:
        if self.nbits < count:
            self._feed(count)
        self.nbits -= count
        self.bits &= (1 << self.nbits) - 1

    def get(self, count: int) -> int:
        if count <= 0:
            return 0
        if self.nbits < count:
            self._feed(count)
        self.nbits -= count
        value = (self.bits >> self.nbits) & ((1 << count) - 1)
        self.bits &= (1 << self.nbits) - 1
        return value

    def align_restart(self) -> bool:
        """跳到下一个 RSTn 标记。找不到就说找不到——**不要静默继续**。"""
        self.bits, self.nbits = 0, 0
        data, i = self.data, self.pos
        while i + 1 < self.end:
            if data[i] == 0xFF and 0xD0 <= data[i + 1] <= 0xD7:
                self.pos = i + 2
                return True
            i += 1
        return False


class _Huff:
    """一张霍夫曼表。

    `flat[i]` 把 (值, 码长) 压成一个 int（`值 << 5 | 码长`）——热循环里
    元组拆包与 None 判断都要钱，一张 2048×1152 有三万多个块、每块解 1+63 次。
    长码（>_FAST_BITS 位）走 `slow`，它们在真实图里占比不到 1%。
    """

    __slots__ = ("fast", "slow", "flat")

    def __init__(self, bits: bytes, vals: bytes) -> None:
        self.fast = [None] * (1 << _FAST_BITS)
        self.flat = [0] * (1 << _FAST_BITS)
        self.slow: dict[tuple[int, int], int] = {}
        code = 0
        k = 0
        for length in range(1, 17):
            for _ in range(bits[length - 1]):
                if k >= len(vals):
                    break
                value = vals[k]
                if length <= _FAST_BITS:
                    shift = _FAST_BITS - length
                    base = code << shift
                    entry = (value, length)
                    packed = (value << 5) | length
                    for offset in range(1 << shift):
                        self.fast[base + offset] = entry
                        self.flat[base + offset] = packed
                else:
                    self.slow[(length, code)] = value
                code += 1
                k += 1
            code <<= 1

    def decode(self, reader: _BitReader) -> int:
        entry = self.fast[reader.peek(_FAST_BITS)]
        if entry is not None:
            reader.skip(entry[1])
            return entry[0]
        code = reader.peek(_FAST_BITS)
        length = _FAST_BITS
        while length < 16:
            length += 1
            code = (code << 1) | ((reader.peek(length) & 1))
            hit = self.slow.get((length, code))
            if hit is not None:
                reader.skip(length)
                return hit
        reader.skip(1)
        return 0


def _build_huff(bits: bytes, vals: bytes) -> _Huff:
    return _Huff(bits, vals)


def _destuff(blob: bytes, start: int) -> list[bytes]:
    """去掉 `0xFF 0x00` 填充，并在 RSTn 处切段。

    **只洗一遍**：不洗的话，每取一个字节都要判一次 0xFF，
    而这一判在最内层循环里跑几百万次。切段同时把重启区间分好，
    DC 预测值按段清零，不用在循环里数 MCU。
    """
    out = bytearray()
    segs: list[bytes] = []
    i, n = start, len(blob)
    while i < n:
        byte = blob[i]
        if byte != 0xFF:
            out.append(byte)
            i += 1
            continue
        nxt = blob[i + 1] if i + 1 < n else 0xD9
        if nxt == 0x00:
            out.append(0xFF)
            i += 2
            continue
        if 0xD0 <= nxt <= 0xD7:
            segs.append(bytes(out))
            out = bytearray()
            i += 2
            continue
        break                      # EOI 或下一个真标记：熵段到此为止
    segs.append(bytes(out))
    return segs


def _extend(value: int, length: int) -> int:
    if length == 0:
        return 0
    return value - (1 << length) + 1 if value < (1 << (length - 1)) else value


def _decode_jpeg(blob: bytes) -> Img | None:
    pos = 2
    qt: dict[int, list[int]] = {}
    huff_dc: dict[int, dict] = {}
    huff_ac: dict[int, dict] = {}
    comps: list[dict] = []
    width = height = 0
    restart = 0
    progressive = False
    while pos + 3 < len(blob):
        if blob[pos] != 0xFF:
            pos += 1
            continue
        marker = blob[pos + 1]
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            pos += 2
            continue
        if marker == 0xD9:
            break
        length = struct.unpack(">H", blob[pos + 2:pos + 4])[0]
        seg = blob[pos + 4:pos + 2 + length]
        if marker == 0xDB:
            i = 0
            while i < len(seg):
                pq, tq = seg[i] >> 4, seg[i] & 15
                i += 1
                size = 64 * (2 if pq else 1)
                raw = seg[i:i + size]
                qt[tq] = ([struct.unpack(">H", raw[j:j + 2])[0] for j in range(0, size, 2)]
                          if pq else list(raw))
                i += size
        elif marker in (0xC0, 0xC1, 0xC2):
            progressive = marker == 0xC2
            height, width = struct.unpack(">HH", seg[1:5])
            count = seg[5]
            comps = []
            for c in range(count):
                cid, hv, tq = seg[6 + c * 3], seg[7 + c * 3], seg[8 + c * 3]
                comps.append({"id": cid, "h": hv >> 4, "v": hv & 15, "tq": tq,
                              "pred": 0, "blocks": {}, "energy": {}})
        elif marker in (0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            return None                    # 算术编码/无损：不解
        elif marker == 0xC4:
            i = 0
            while i < len(seg):
                tc, th = seg[i] >> 4, seg[i] & 15
                bits = seg[i + 1:i + 17]
                total = sum(bits)
                vals = seg[i + 17:i + 17 + total]
                (huff_ac if tc else huff_dc)[th] = _build_huff(bits, vals)
                i += 17 + total
        elif marker == 0xDD:
            restart = struct.unpack(">H", seg[:2])[0]
        elif marker == 0xDA:
            if not comps or not width:
                return None
            ns = seg[0]
            scan = []
            for s in range(ns):
                cs, tt = seg[1 + s * 2], seg[2 + s * 2]
                comp = next((c for c in comps if c["id"] == cs), None)
                if comp is None:
                    return None
                scan.append((comp, tt >> 4, tt & 15))
            ss, se, ahal = seg[1 + ns * 2], seg[2 + ns * 2], seg[3 + ns * 2]
            al = ahal & 15
            ah = ahal >> 4
            body_start = pos + 2 + length
            if progressive and (ss != 0 or ah != 0):
                pos = body_start
                continue               # 渐进：只吃各分量第一遍 DC，细化与 AC 扫描跳过
            ok = _scan_dc(blob, body_start, scan, comps, width, height,
                          huff_dc, huff_ac, restart, progressive, al, se)
            if not ok:
                return None
            if progressive:
                pos = body_start
                continue
            break
        pos += 2 + length
    if not comps or not width or not height:
        return None
    return _assemble(comps, qt, width, height)


def _scan_dc(blob: bytes, start: int, scan: list, comps: list[dict],
             width: int, height: int, huff_dc: dict, huff_ac: dict,
             restart: int, progressive: bool, al: int, se: int) -> bool:
    """解这一遍扫描的 DC 系数（顺带把 AC 跳过去），并留下每块的 AC 能量。

    位读取器整个**内联**在最内层循环里：属性查找与方法调用在这里各跑几百万次，
    分出去写成类方法要慢三到五倍，而这条路径决定了链条在真机上跑不跑得动。
    """
    h_max = max(c["h"] for c in comps) or 1
    v_max = max(c["v"] for c in comps) or 1
    mcus_x = -(-width // (8 * h_max))
    mcus_y = -(-height // (8 * v_max))
    segments = _destuff(blob, start)
    per_seg = restart if restart else mcus_x * mcus_y
    fast_bits = _FAST_BITS
    fast_mask = (1 << fast_bits) - 1
    plan = []
    for comp, dc_id, ac_id in scan:
        dc_tab = huff_dc.get(dc_id)
        ac_tab = huff_ac.get(ac_id)
        if dc_tab is None or (not progressive and ac_tab is None):
            return False
        plan.append((comp, comp["blocks"], comp["energy"], comp["h"], comp["v"],
                     dc_tab.flat, dc_tab.slow,
                     ac_tab.flat if ac_tab else None,
                     ac_tab.slow if ac_tab else {}))
    if len(plan) == 1 and (progressive or len(comps) > 1):
        # **单分量扫描不是 MCU 交错的**：渐进 JPEG 的第一遍 DC 常常一个分量一遍，
        # 块按该分量自己的光栅序排。按 MCU 序解会把亮度算到色度格子上——
        # 解出来是一张灰的、明暗全错的图，而判据会拿它当真画面。
        return _scan_dc_single(segments, plan[0], comps, width, height,
                               h_max, v_max, restart, progressive, al, se,
                               fast_bits, fast_mask)
    mcu = 0
    total = mcus_x * mcus_y
    for seg in segments:
        if mcu >= total:
            break
        for entry in plan:
            entry[0]["pred"] = 0
        buf = 0
        nbits = 0
        pos = 0
        ln = len(seg)
        stop = min(total, mcu + per_seg)
        while mcu < stop:
            my, mx = divmod(mcu, mcus_x)
            mcu += 1
            for (comp, blocks, energy, ch, cv,
                 dc_flat, dc_slow, ac_flat, ac_slow) in plan:
                for by in range(cv):
                    for bx in range(ch):
                        # ---- DC 码
                        while nbits < 32 and pos < ln:
                            buf = (buf << 8) | seg[pos]
                            pos += 1
                            nbits += 8
                        if nbits < 16:
                            buf <<= 16
                            nbits += 16
                        packed = dc_flat[(buf >> (nbits - fast_bits)) & fast_mask]
                        if packed:
                            size = packed >> 5
                            nbits -= packed & 31
                        else:
                            size = 0
                            length = fast_bits
                            while length < 16:
                                length += 1
                                if nbits < length:
                                    buf <<= (length - nbits)
                                    nbits = length
                                hit = dc_slow.get(
                                    (length, (buf >> (nbits - length)) & ((1 << length) - 1)))
                                if hit is not None:
                                    size = hit
                                    nbits -= length
                                    break
                            else:
                                return False
                        buf &= (1 << nbits) - 1
                        if size:
                            while nbits < size and pos < ln:
                                buf = (buf << 8) | seg[pos]
                                pos += 1
                                nbits += 8
                            if nbits < size:
                                buf <<= (size - nbits)
                                nbits = size
                            nbits -= size
                            raw = (buf >> nbits) & ((1 << size) - 1)
                            buf &= (1 << nbits) - 1
                            diff = raw - (1 << size) + 1 if raw < (1 << (size - 1)) else raw
                        else:
                            diff = 0
                        comp["pred"] += diff
                        cx = mx * ch + bx
                        cy = my * cv + by
                        blocks[(cx, cy)] = comp["pred"] << al
                        if progressive:
                            continue
                        # ---- AC：不要值，只把位流推过去；顺带累计高频能量
                        k = 1
                        ac_energy = 0
                        while k <= se:
                            while nbits < 32 and pos < ln:
                                buf = (buf << 8) | seg[pos]
                                pos += 1
                                nbits += 8
                            if nbits < 16:
                                buf <<= 16
                                nbits += 16
                            packed = ac_flat[(buf >> (nbits - fast_bits)) & fast_mask]
                            if packed:
                                rs = packed >> 5
                                nbits -= packed & 31
                            else:
                                rs = -1
                                length = fast_bits
                                while length < 16:
                                    length += 1
                                    if nbits < length:
                                        buf <<= (length - nbits)
                                        nbits = length
                                    hit = ac_slow.get(
                                        (length, (buf >> (nbits - length)) & ((1 << length) - 1)))
                                    if hit is not None:
                                        rs = hit
                                        nbits -= length
                                        break
                                if rs < 0:
                                    return False
                            buf &= (1 << nbits) - 1
                            run, size = rs >> 4, rs & 15
                            if size == 0:
                                if run != 15:
                                    break
                                k += 16
                                continue
                            k += run + 1
                            while nbits < size and pos < ln:
                                buf = (buf << 8) | seg[pos]
                                pos += 1
                                nbits += 8
                            if nbits < size:
                                buf <<= (size - nbits)
                                nbits = size
                            nbits -= size
                            buf &= (1 << nbits) - 1
                            ac_energy += size
                        energy[(cx, cy)] = ac_energy
    return bool(comps[0]["blocks"])


def _scan_dc_single(segments, entry, comps, width, height, h_max, v_max,
                    restart, progressive, al, se, fast_bits, fast_mask) -> bool:
    """一个分量单独一遍扫描：块按这个分量自己的光栅序走。"""
    (comp, blocks, energy, ch, cv, dc_flat, dc_slow, ac_flat, ac_slow) = entry
    bw = -(-(width * ch) // (8 * h_max))
    bh = -(-(height * cv) // (8 * v_max))
    total = bw * bh
    done = 0
    per_seg = restart if restart else total
    for seg in segments:
        if done >= total:
            break
        comp["pred"] = 0
        buf = nbits = pos = 0
        ln = len(seg)
        stop = min(total, done + per_seg)
        while done < stop:
            cy, cx = divmod(done, bw)
            done += 1
            while nbits < 32 and pos < ln:
                buf = (buf << 8) | seg[pos]
                pos += 1
                nbits += 8
            if nbits < 16:
                buf <<= 16
                nbits += 16
            packed = dc_flat[(buf >> (nbits - fast_bits)) & fast_mask]
            if packed:
                size = packed >> 5
                nbits -= packed & 31
            else:
                size = 0
                length = fast_bits
                while length < 16:
                    length += 1
                    if nbits < length:
                        buf <<= (length - nbits)
                        nbits = length
                    hit = dc_slow.get(
                        (length, (buf >> (nbits - length)) & ((1 << length) - 1)))
                    if hit is not None:
                        size = hit
                        nbits -= length
                        break
                else:
                    return bool(blocks)
            buf &= (1 << nbits) - 1
            if size:
                while nbits < size and pos < ln:
                    buf = (buf << 8) | seg[pos]
                    pos += 1
                    nbits += 8
                if nbits < size:
                    buf <<= (size - nbits)
                    nbits = size
                nbits -= size
                raw = (buf >> nbits) & ((1 << size) - 1)
                buf &= (1 << nbits) - 1
                diff = raw - (1 << size) + 1 if raw < (1 << (size - 1)) else raw
            else:
                diff = 0
            comp["pred"] += diff
            blocks[(cx, cy)] = comp["pred"] << al
            energy[(cx, cy)] = 0
    return bool(blocks)


class _Window:
    """给慢路一个只读快照（长码极少，走到这里就整张改用慢解码器重来）。"""

    __slots__ = ("seg", "pos", "buf", "nbits")

    def __init__(self, seg: bytes, pos: int, buf: int, nbits: int) -> None:
        self.seg, self.pos, self.buf, self.nbits = seg, pos, buf, nbits


#: 兜底路径，尚未接线。接线前须先造一个能触发它的样本（长码 >12 位的 JPEG）跑通对账。
def _slow_scan(blob: bytes, start: int, scan: list, comps: list[dict],
               width: int, height: int, huff_dc: dict, huff_ac: dict,
               restart: int, progressive: bool, al: int, se: int) -> bool:
    """码长超过快查表时的兜底：逐位解，慢但一定对。

    **不要在快路里"猜一个"继续**——霍夫曼流一旦错位，后面每一个块都是噪声，
    而解出来的那张噪声图会被判据当成真画面。
    """
    h_max = max(c["h"] for c in comps) or 1
    v_max = max(c["v"] for c in comps) or 1
    mcus_x = -(-width // (8 * h_max))
    mcus_y = -(-height // (8 * v_max))
    reader = _BitReader(blob, start)
    for comp in comps:
        comp["pred"] = 0
        comp["blocks"].clear()
        comp["energy"].clear()
    seen = 0
    for my in range(mcus_y):
        for mx in range(mcus_x):
            if restart and seen and seen % restart == 0:
                if not reader.align_restart():
                    return bool(comps[0]["blocks"])
                for comp in comps:
                    comp["pred"] = 0
            seen += 1
            for comp, dc_id, ac_id in scan:
                dc_tab = huff_dc.get(dc_id)
                ac_tab = huff_ac.get(ac_id)
                if dc_tab is None or (not progressive and ac_tab is None):
                    return False
                for by in range(comp["v"]):
                    for bx in range(comp["h"]):
                        size = dc_tab.decode(reader)
                        diff = _extend(reader.get(size), size) if size else 0
                        comp["pred"] += diff
                        cx, cy = mx * comp["h"] + bx, my * comp["v"] + by
                        comp["blocks"][(cx, cy)] = comp["pred"] << al
                        if progressive:
                            continue
                        k, ac_energy = 1, 0
                        while k <= se:
                            rs = ac_tab.decode(reader)
                            run, size = rs >> 4, rs & 15
                            if size == 0:
                                if run != 15:
                                    break
                                k += 16
                                continue
                            k += run + 1
                            reader.get(size)
                            ac_energy += size
                        comp["energy"][(cx, cy)] = ac_energy
            if reader.pos > len(blob):
                return bool(comps[0]["blocks"])
    return True


def _assemble(comps: list[dict], qt: dict[int, list[int]],
              width: int, height: int) -> Img | None:
    if not comps[0]["blocks"]:
        return None
    h_max = max(c["h"] for c in comps) or 1
    v_max = max(c["v"] for c in comps) or 1
    bw, bh = -(-width // 8), -(-height // 8)
    out = bytearray(bw * bh * 3)
    luma = comps[0]
    chroma = comps[1:3] if len(comps) >= 3 else []
    q_luma = qt.get(luma["tq"], [16] * 64)

    def sample(comp: dict, bx: int, by: int) -> float:
        cx = bx * comp["h"] // h_max
        cy = by * comp["v"] // v_max
        raw = comp["blocks"].get((cx, cy))
        if raw is None:
            return 0.0
        table = qt.get(comp["tq"], [16] * 64)
        return raw * table[_ZIGZAG_FIRST] / 8.0

    _ = q_luma
    for by in range(bh):
        for bx in range(bw):
            y = sample(luma, bx, by) + 128.0
            if chroma:
                cb = sample(chroma[0], bx, by)
                cr = sample(chroma[1], bx, by)
                r = y + 1.402 * cr
                g = y - 0.344136 * cb - 0.714136 * cr
                b = y + 1.772 * cb
            else:
                r = g = b = y
            i = (by * bw + bx) * 3
            out[i] = 0 if r < 0 else (255 if r > 255 else int(r))
            out[i + 1] = 0 if g < 0 else (255 if g > 255 else int(g))
            out[i + 2] = 0 if b < 0 else (255 if b > 255 else int(b))
    return Img("RGB", (width, height), out, (bw, bh))
# ────────────────────────────────────────────────────────── PIL 兼容外壳

class _ImageModule:
    Image = Img
    BOX = "box"
    LANCZOS = "lanczos"
    BILINEAR = "bilinear"
    NEAREST = "nearest"
    Resampling = types.SimpleNamespace(BOX="box", LANCZOS="lanczos",
                                       BILINEAR="bilinear", NEAREST="nearest")

    @staticmethod
    def new(mode: str, size: tuple[int, int], color: Any = 0) -> Img:
        img = Img(mode, size)
        if color:
            if isinstance(color, str):
                color = (255, 255, 255)
            if isinstance(color, int):
                color = (color,) * img._n
            cell = bytes(int(c) & 0xFF for c in tuple(color)[:img._n])
            if len(cell) < img._n:
                cell = cell + bytes(img._n - len(cell))
            # **整块填充，不逐点赋值。** 一张 960×540 的底图是 518,400 次
            # `__setitem__`；判据在一次完整校验里会建十几张这样的画布，
            # 于是一条纯粹的内存操作要花掉十秒量级——超过宿主 15s 前台窗口之后，
            # 每一次完整校验都要多花一次 TaskOutput 往返。
            img._data[:] = cell * (img._dw * img._dh)
        return img

    @staticmethod
    def open(source: Any) -> Img:
        cache_key = None
        if not isinstance(source, (bytes, bytearray, io.IOBase)):
            path = Path(str(source))
            try:
                stat = path.stat()
                cache_key = (str(path), stat.st_mtime_ns, stat.st_size)
            except OSError:
                cache_key = None
            if cache_key is not None and cache_key in _CACHE:
                return _CACHE[cache_key].copy()
        if isinstance(source, (bytes, bytearray)):
            blob = bytes(source)
        elif isinstance(source, io.IOBase):
            blob = source.read()
        else:
            blob = Path(str(source)).read_bytes()
        img = _decode_png(blob) if blob[:8] == b"\x89PNG\r\n\x1a\n" else None
        if img is None and blob[:2] == b"\xff\xd8":
            img = _decode_jpeg(blob)
        if img is None:
            raise OSError("这张图解不动（交错 PNG / 算术编码 JPEG），本轮按「没量过」处理")
        if cache_key is not None:
            # **一定要缓存**：判据会为同一页的机械校验、视觉复核和交付复核反复拼底图，
            # 纯 Python 解一张 2048×1152 要半秒，不缓存时一份 12 页稿要多烧一分钟。
            if len(_CACHE) > _CACHE_MAX:
                _CACHE.clear()
            _CACHE[cache_key] = img
            return img.copy()
        return img


Image = _ImageModule


if __name__ == "__main__":                             # 手工自检入口
    print("像素来源：", install())
    gaps = selfcheck()
    print("接口自检：", "全部可用" if not gaps else "缺口 " + "；".join(gaps))
    sys.exit(1 if gaps else 0)
