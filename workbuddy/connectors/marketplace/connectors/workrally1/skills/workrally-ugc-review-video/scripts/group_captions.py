#!/usr/bin/env python3
"""
group_captions.py — 把词级时间轴切成 1-2 词的动态字幕段，停顿时**留空**。
输出喂给 scripts/make_captions.py。

输入 words.json    : [[start, end, "word"], ...]（faster-whisper word_timestamps）
输出 segments.json : {"video": ..., "style": {"margin_v": ...}, "segments":[{start,end,text}]}

正确性：一定要传 --script（撰写好的口播原文）。字幕**文字**取自脚本（品牌 / 产品拼写正确），
时间轴由 whisper 提供 —— whisper 只当秒表。这样无需按品牌硬编码就能消掉转写错字。

中文支持：分词与显示宽度都做了 CJK 处理 —— 中文脚本按字切 token，中文之间拼接不加空格，
一个汉字按 2 个显示宽度计。

用法：
    python3 group_captions.py words.json -o segments.json --video final.mp4 --script script.txt
"""
import json, argparse, re, difflib, sys

# --- 默认值（在这里调） ---
MAX_PAIR_WIDTH = 11    # 两个词合并的条件：合起来显示宽度 <= 此值（汉字算 2）
MAX_JOIN_GAP   = 0.35  # ...且两者间隔小于此值（秒）
TAIL           = 0.15  # 字幕在最后一个词之后多留这么久（这就是停顿留空的机制）
MIN_HOLD       = 0.20  # 最短驻留时间
MARGIN_V       = 1380  # 写进 style.margin_v；流水线后面还会再处理 .ass

SENT_END_PUNCT = (".", "!", "?", ":", ";", "。", "！", "？", "：", "；", "、", "，")  # 句界不合并
# 可选的人工转写覆盖，按词小写匹配。默认**为空** —— 正确性靠 --script 对齐，不靠按品牌硬编码。
# 只有对齐确实解决不了的罕见情况才加一条，换站点时清空。
FIX = {}

CJK = r"\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\u3040-\u30ff\uac00-\ud7af"
_CJK_RE = re.compile(f"[{CJK}]")
# 拉丁 token 把内部的 . ' ’ - 粘住（域名 adidas.com、two-day、wasn't 都是一个 token）
_TOKEN_RE = re.compile(f"[{CJK}]|[0-9A-Za-z]+(?:[.'\u2019-][0-9A-Za-z]+)*|[^\\s]")
_PUNCT_RE = re.compile(r"^[^0-9A-Za-z\s]$")


def _norm(t):
    """把一个 token 归一化用于匹配：小写，去掉非字母数字，但**保留** CJK 字形。"""
    return re.sub(f"[^0-9a-z{CJK}]", "", t.lower())


def _tokenize(text):
    """把脚本切成可对齐的 token：汉字逐字，拉丁文按词，标点单独成 token。

    中文脚本没有空格，直接 split() 会得到一整块，对齐必然失败。"""
    return [t for t in _TOKEN_RE.findall(text) if t.strip()]


def _join(tokens):
    """拼接 token：相邻两侧只要有一侧是 CJK、或后一个是单个标点，就不加空格，否则用空格。"""
    out = ""
    for t in tokens:
        if not out:
            out = t
            continue
        if _CJK_RE.search(out[-1]) or _CJK_RE.search(t[0]) or _PUNCT_RE.match(t):
            out += t
        else:
            out += " " + t
    return out


def _width(text):
    """显示宽度：CJK 字形算 2，其余算 1。"""
    return sum(2 if _CJK_RE.match(ch) else 1 for ch in text)


def load_words(path):
    raw = json.load(open(path, encoding="utf-8"))
    words = [(float(s), float(e), FIX.get(w.strip().lower(), w.strip())) for s, e, w in raw]
    # 粘回被切开的 token，如 "adidas" + ".com"、"two" + "-day"
    merged = []
    for s, e, w in words:
        if merged and w.startswith((".", "-", "'")):
            ps, pe, pw = merged[-1]; merged[-1] = (ps, e, pw + w); continue
        merged.append((s, e, w))
    return merged


SPAN_SIMILARITY = 0.6   # 归一化文本相似度超过此值即视为「同一批词被听错了」


def _span_ratio(a_tokens, b_tokens):
    """把两段 token 拉平成字符串后比相似度。"""
    return difflib.SequenceMatcher(a="".join(a_tokens), b="".join(b_tokens), autojunk=False).ratio()


def align_to_script(words, script_text):
    """把 whisper 的词**文字**换成脚本里撰写的原词（保留 whisper 的时间），做法是对齐两个
    token 序列。whisper 只提供秒表，所以品牌 / 产品名永远按撰写拼写。

    听错常见是 N<->M 而不是 1:1 —— 转写把一个多词名收成一个 token、把一个词拆成两个、
    或者漏词。等长区间直接映射；不等长区间在该区间的 whisper 词上摊开（保证每个撰写词
    都按顺序落在真实时间上），前提是两段读起来确实是同一批词。真的不是同一批词时保留
    whisper 文字并由 QA 检查报出来 —— 对齐从不凭空造词，也从不在作者真的写过的词上
    偏向 ASR 拼写。"""
    script_tokens = _tokenize(script_text)
    a = [_norm(w) for _, _, w in words]
    b = [_norm(t) for t in script_tokens]
    out = [[s, e, w] for s, e, w in words]
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        n, m = i2 - i1, j2 - j1
        if tag == "equal" or (tag == "replace" and n == m):
            for k in range(n):
                if _norm(script_tokens[j1 + k]):        # 不要用纯标点 token 覆盖
                    out[i1 + k][2] = script_tokens[j1 + k]
        elif tag == "replace" and n > 0 and m > 0:
            # 不等长区间：只有明显是同一批词被听错时才替换，转写听成别的东西就不动。
            if _span_ratio(a[i1:i2], b[j1:j2]) < SPAN_SIMILARITY:
                continue
            # 把 m 个撰写 token 按顺序摊到 n 个 whisper 词上；最后一个 whisper 词吸收余数，
            # 保证撰写内容一个都不丢。
            base, extra = divmod(m, n)
            cursor = j1
            for k in range(n):
                width = base + (1 if k < extra else 0)
                take = script_tokens[cursor:j2] if k == n - 1 else script_tokens[cursor:cursor + width]
                cursor += len(take)
                text = _join([t for t in take if _norm(t)])
                if text:
                    out[i1 + k][2] = text
        # delete / insert：保留 whisper 原词
    return [(s, e, w) for s, e, w in out]


def group(words):
    segs, i = [], 0
    while i < len(words):
        s, e, w = words[i]
        pair = (i + 1 < len(words)
                and _width(w) + _width(words[i + 1][2]) <= MAX_PAIR_WIDTH
                and (words[i + 1][0] - e) < MAX_JOIN_GAP
                and not w.rstrip().endswith(SENT_END_PUNCT))  # 通用句界判断
        if pair:
            ns, ne, nw = words[i + 1]
            segs.append({"start": round(s, 2), "end": round(ne, 2), "text": _join([w, nw])}); i += 2
        else:
            segs.append({"start": round(s, 2), "end": round(e, 2), "text": w}); i += 1
    # 停顿留空：end = 词尾 + 小尾巴，绝不桥接到下一条字幕
    for j, seg in enumerate(segs):
        nxt = segs[j + 1]["start"] if j + 1 < len(segs) else seg["end"] + TAIL
        seg["end"] = round(min(seg["end"] + TAIL, nxt - 0.02), 2)
        if seg["end"] < seg["start"] + MIN_HOLD:
            seg["end"] = round(seg["start"] + MIN_HOLD, 2)
    # 两条字幕绝不在时间上重叠 —— ASS 会把重叠事件堆叠，文字会上下跳。
    GAP = 0.02
    for i in range(len(segs) - 1):
        if segs[i]["end"] > segs[i + 1]["start"] - GAP:
            segs[i]["end"] = round(
                max(segs[i]["start"] + 0.05, segs[i + 1]["start"] - GAP), 2
            )
    return segs


def qa_check(segs, script_text):
    """报出不在撰写脚本里的字幕词（对齐没能修掉的听错）。返回违规词，调用方据此**阻止**烧字。"""
    vocab = {_norm(t) for t in _tokenize(script_text) if _norm(t)}
    unknown = sorted({w for seg in segs for w in _tokenize(seg["text"])
                      if _norm(w) and _norm(w) not in vocab})
    if unknown:
        print(f"[QA] {len(unknown)} caption word(s) not in the script: {unknown}")
    else:
        print("[QA] ok — every caption word is in the script")
    return unknown


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("words_json")
    ap.add_argument("-o", "--out", default="segments.json")
    ap.add_argument("--video", default="final.mp4")
    ap.add_argument("--script", default=None, help="撰写好的口播原文 —— 字幕拼写取自它")
    ap.add_argument("--margin-v", type=int, default=MARGIN_V)
    ap.add_argument("--allow-qa-misses", action="store_true",
                    help="即使有字幕词不在脚本里也照样写出 segments"
                         "（默认退出码 3，避免串联烧字时把听错的文字烧上去）")
    a = ap.parse_args()

    words = load_words(a.words_json)
    script_text = None
    if a.script:
        script_text = open(a.script, encoding="utf-8").read()
        words = align_to_script(words, script_text)

    segs = group(words)
    unknown = []
    if script_text is not None:
        unknown = qa_check(segs, script_text)
    else:
        print("[QA] no --script given — captions use raw transcription (brand/product typos possible)")

    json.dump({"video": a.video, "style": {"margin_v": a.margin_v}, "segments": segs},
              open(a.out, "w"), ensure_ascii=False)
    print(f"wrote {a.out} — {len(segs)} segments")

    # QA 列表非空说明烧字会把 ASR 拼写放上屏幕。宁可显式失败：
    # 去脚本里把品牌和数字写成上屏该有的样子再跑；确认那些词本来就对，再用 --allow-qa-misses。
    if unknown and not a.allow_qa_misses:
        print("[QA] BLOCKED — not safe to burn. Author every brand and number in the script "
              "exactly as it must read on screen, then re-run; pass --allow-qa-misses to override.")
        sys.exit(3)


if __name__ == "__main__":
    main()
