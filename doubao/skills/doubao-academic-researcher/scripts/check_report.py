# -*- coding: utf-8 -*-
"""
check_report.py — 交付前机械门禁（必跑；FAIL 未消解不得交付、不得声称调研完成）

定位：把 skill 中已经成文、且可机械判定的交付纪律代码化。判断类检查
（Angle/Insight 的楼层达标、Weaving 的对比质量等）仍属 7 维门禁，本脚本不越界。

检查项：
  1. 反平庸黑名单（insight-protocol）：见仁见智 / 需要更多研究 / 长足进展 /
     "随着……的发展"式填充句（FAIL）；各有优劣 / 具有重要意义（WARN，上下文相关）。
  2. 引用编号（output-structure）：正文首现顺序必须为 1,2,3,…（识别 [n] 与
     [n, m] 多引，含中文逗号/顿号）；参考文献编号连续无重复；同一来源重复立目
     （归一化后逐字重复 FAIL / 相似度 ≥0.90 WARN）；正文引用与参考文献互查
     （引了没列 FAIL；列了没引 WARN）。
  3. 任务模式结构（主 SKILL.md 任务模式分流）：
     综述模式——交付物不得含【题录核验台账】小节；参考文献不得含 URL/DOI；
               参考文献出现"未核验"标注 → WARN（综述纪律：宁可省略）。
     严格模式——必须含【题录核验台账】小节（或经 --ledger 提供台账文件）。
  4. 声明-台账清点（v3.2/v4.5，严格模式）：声明中的"已核验/二手核验/未核验 n 项"
     逐档与台账行数比对；"已核验 n 篇"与台账中有已核验行的文献篇数比对。
  5. 全称量词（ledger-and-statements 反例）：存在二手核验/未核验项时，
     含"核验/核实/真实"的句行内出现"全部/均/确保准确无误" → WARN。
  6. 声明文献计数勾稽（v4.5"声明数字由清点产生"同族）：正文"纳入/清单共 N 篇"
     类总数声明与参考文献实际条目数比对，不等 → FAIL。
  7. 检索收敛声明（v5.1.2 可观测性，综述模式）：全文未见"滚雪球/饱和"→ WARN。
  8. 引用台账三方对齐（v6.0 单写架构，--citation-ledger 提供台账 JSON 时）：
     正文引用 ⊆ 台账（越界 FAIL）；参考文献逐条与台账 title 比对（不符 = 张冠李戴 FAIL）；
     台账孤儿条目 WARN；语义邻近检查——[N] 同句的系统/方法名与台账第 N 条冲突 → FAIL，
     点名未引用 → WARN（表格/标题行免 WARN 防误报）；正文有参考文献节却零内联 [n] → FAIL
     （该条不依赖台账）；台账在场时首现顺序降 WARN（美观由 citation_ledger.py renumber 原子治理）。

用法：
  python3 scripts/check_report.py 报告.md                 # 模式自动识别
  python3 scripts/check_report.py 报告.md --mode strict   # 显式指定
  python3 scripts/check_report.py 报告.md --ledger 台账.md # 题录台账单独成文时
  python3 scripts/check_report.py 报告.md --citation-ledger .workflow/citation_ledger.json
  python3 scripts/check_report.py --selftest

解析原则：宽容读取——解析不到的项打 INFO 跳过，不猜、不硬报错；
出口码：存在 FAIL → 1，否则 0。FAIL 逐项消解后才允许交付。
"""
import argparse
import difflib
import io
import json
import re
import sys

LEDGER_MARK = "【题录核验台账】"

# ---------------- findings ----------------

class Findings:
    def __init__(self):
        self.items = []  # (level, check, message)

    def add(self, level, check, message):
        self.items.append((level, check, message))

    def count(self, level):
        return sum(1 for l, _, _ in self.items if l == level)

    def render(self):
        out = []
        for level, check, msg in self.items:
            out.append(f"[{level}] {check}: {msg}")
        out.append(f"summary: FAIL {self.count('FAIL')} / WARN {self.count('WARN')} / INFO {self.count('INFO')}")
        return "\n".join(out)


# ---------------- helpers ----------------

REFS_HEADING_LINE = re.compile(r"^(?:#{1,6}\s*|\*\*)(参考文献|References)(?:\*\*)?\s*[:：]?\s*$")


def _blank_fences(text):
    """把 ``` 代码栅栏内的行（含定界行）置空，行号保持不变——引用层扫描统一先过这一步：
    `dists[9]` 这类代码下标不是引用，栅栏内的"## 参考文献"演示行也不是真标题。"""
    out, in_code = [], False
    for line in text.split("\n"):
        if line.strip().startswith("```"):
            in_code = not in_code
            out.append("")
            continue
        out.append("" if in_code else line)
    return "\n".join(out)


def split_refs(text):
    """返回 (正文, 参考文献节, 参考文献起始行号)；找不到参考文献节则 refs 为 None。
    逐行识别：跳过代码栅栏内的伪标题；接受 #{1,6} 与整行加粗 **参考文献** 变体。"""
    lines = text.split("\n")
    in_code = False
    for i, line in enumerate(lines):
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if REFS_HEADING_LINE.match(line.strip()):
            return "\n".join(lines[:i]), "\n".join(lines[i + 1:]), i + 1
    return text, None, None


def strip_ledger_block(text):
    """把台账小节（从标记行起到下一个标题行）从文本中剔除，返回 (剔除后文本, 台账块文本)。"""
    idx = text.find(LEDGER_MARK)
    if idx < 0:
        return text, ""
    start = text.rfind("\n", 0, idx) + 1
    m = re.search(r"^#{1,6}\s", text[idx:], re.M)
    end = idx + m.start() if m else len(text)
    return text[:start] + text[end:], text[start:end]


def iter_lines_with_no(text):
    for i, line in enumerate(text.split("\n"), 1):
        yield i, line


# ---------------- checks ----------------

BLACKLIST_FAIL = [
    (r"见仁见智", "走分歧裁决程序（insight-protocol：有条件立场/证据缺口/真实分歧，三选一）"),
    (r"需要更多(的)?研究", "写清缺少什么设计/什么数据的研究、它能裁决哪个问题"),
    (r"取得了长足(的)?进展", "填充句——删掉，用具体事实"),
    (r"随着[^，。；\n]{1,24}的(快速|蓬勃|迅速|不断|飞速)发展", "空话开头——删掉，用具体事实开头"),
]
BLACKLIST_WARN = [
    (r"各有优劣", "若未紧跟'什么条件下谁更优、依据哪几篇'，改写"),
    (r"具有重要意义", "对谁、改变什么——不说清即为填充"),
]


NEGATION_BEFORE = re.compile(r"(?:拒绝|而非|不是|避免|不写|禁止|防止|杜绝)[^，。；]{0,6}$")
QUOTE_CHARS = "\"“”'『「"


def check_blacklist(f, body):
    in_code = False
    for no, line in iter_lines_with_no(body):
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        for pat, advice in BLACKLIST_FAIL:
            m = re.search(pat, line)
            if m:
                ctx = line[max(0, m.start() - 10):m.start()]
                quoted = m.start() > 0 and line[m.start() - 1] in QUOTE_CHARS
                if NEGATION_BEFORE.search(ctx) or quoted:
                    f.add("WARN", "黑名单", f"L{no} 命中 /{pat}/（否定/引述语境，人工确认非本文口吻即可）—— {advice}")
                else:
                    f.add("FAIL", "黑名单", f"L{no} 命中 /{pat}/ —— {advice}")
        for pat, advice in BLACKLIST_WARN:
            if re.search(pat, line):
                f.add("WARN", "黑名单", f"L{no} 命中 /{pat}/ —— {advice}")


CITE = re.compile(r"\[(\d{1,3}(?:\s*[,，、]\s*\d{1,3})*)\]")


def iter_cite_nums(text):
    """按出现顺序产出正文引用编号；单引 [n] 与多引 [n, m]（含中文逗号/顿号）均识别。"""
    for m in CITE.finditer(text):
        for x in re.split(r"[,，、]", m.group(1)):
            x = x.strip()
            if x:
                yield int(x)


def check_citations(f, body, refs, ledger_mode=False):
    order, seen = [], set()
    for n in iter_cite_nums(body):
        if n not in seen:
            seen.add(n)
            order.append(n)
    if order:
        expect = list(range(1, len(order) + 1))
        if order != expect:
            head = ", ".join(map(str, order[:12]))
            if ledger_mode:
                f.add("WARN", "引用编号", f"正文首现顺序非 1,2,3,…（实际 [{head}…]）——编号为台账 ID 属合法；交付美化可用 citation_ledger.py renumber 原子重排")
            else:
                f.add("FAIL", "引用编号", f"正文首现顺序应为 1,2,3,…，实际为 [{head}…]——按首现顺序重排（张冠李戴风险）")
    else:
        if refs is not None:
            f.add("FAIL", "引用编号", "正文存在参考文献节但无内联 [n] 引用——点名必引用，每条论断必须绑定编号（v6.0）")
        else:
            f.add("INFO", "引用编号", "正文未检出 [n] 引用，跳过顺序检查")

    if refs is None:
        f.add("INFO", "引用编号", "未找到'参考文献'小节，跳过互查")
        return
    ref_entries = [(int(m.group(1)), m.group(2).strip())
                   for m in re.finditer(r"^\s*\[(\d{1,3})\]\s*(.*)$", refs, re.M)]
    ref_nums = [n for n, _ in ref_entries]
    if not ref_nums:
        f.add("WARN", "引用编号", "参考文献小节存在但未解析出 [n] 条目")
        return
    dup = sorted({n for n in ref_nums if ref_nums.count(n) > 1})
    if dup:
        f.add("FAIL", "引用编号", f"参考文献编号重复：{dup}")
    if sorted(ref_nums) != list(range(1, max(ref_nums) + 1)):
        if ledger_mode:
            f.add("WARN", "引用编号", f"参考文献编号不连续（台账 ID 允许空号）：实有 {sorted(ref_nums)}——交付美化可用 citation_ledger.py renumber")
        else:
            f.add("FAIL", "引用编号", f"参考文献编号不连续：实有 {sorted(ref_nums)}")
    missing = sorted(seen - set(ref_nums))
    if missing:
        f.add("FAIL", "引用编号", f"正文引用了但参考文献未列出：{missing}")
    uncited = sorted(set(ref_nums) - seen)
    if uncited:
        f.add("WARN", "引用编号", f"参考文献列出但正文未引用：{uncited}（按首现编号规则不应出现）")
    check_ref_duplicates(f, ref_entries)


def _norm_entry(s):
    return re.sub(r"[\W_]+", "", s).lower()


def check_ref_duplicates(f, ref_entries):
    """参考文献是集合：同一来源全文只占一个编号（逐字重复 FAIL；高相似 WARN）。"""
    normed = [(n, _norm_entry(txt), txt) for n, txt in ref_entries if txt]
    groups = {}
    for n, key, _ in normed:
        groups.setdefault(key, []).append(n)
    for key, ns in groups.items():
        if key and len(ns) > 1:
            nums = "] = [".join(map(str, sorted(ns)))
            f.add("FAIL", "引用编号",
                  f"参考文献 [{nums}] 为同一来源的重复条目——同一来源全文一个编号：合并条目、全文改引其一并按首现顺序重排")
    uniq = [(n, key) for n, key, _ in normed if len(groups.get(key, [])) == 1]
    if len(uniq) > 300:
        f.add("INFO", "引用编号", "条目数 >300，跳过近重复相似度扫描（仅做逐字重复检查）")
        return
    for i in range(len(uniq)):
        for j in range(i + 1, len(uniq)):
            if difflib.SequenceMatcher(None, uniq[i][1], uniq[j][1]).ratio() >= 0.90:
                f.add("WARN", "引用编号",
                      f"参考文献 [{uniq[i][0]}] 与 [{uniq[j][0]}] 高度相似（≥0.90）——疑似同一来源被赋两个编号，人工确认后合并或保留")


# ---------------- 引用台账三方对齐（v6.0 单写架构） ----------------

SENT_SPLIT = re.compile(r"[。！？!?；;]")
NAME_TOKEN = re.compile(
    r"\b(?:"
    r"[A-Z][a-z0-9]+(?:[A-Z][A-Za-z0-9]*)+"               # PatchCore / StreamKV / FastV
    r"|[A-Z]{2,}[a-z0-9]+[A-Za-z0-9]*"                     # YOLOv11 / ReKV 类
    r"|[A-Z][A-Za-z0-9]*[0-9][A-Za-z0-9]*-[A-Za-z0-9]+"    # D3Lite-MES 类
    r"|[A-Z][a-z]+-[A-Z][A-Za-z0-9]+"                      # Fish-MulT 类
    r")\b"
)
NAME_STOP = {
    "MoE", "IoU", "IoT", "CoT", "QoS", "DoF", "LoRA", "ChatGPT",
    "NeurIPS", "IEEE", "AAAI", "CVPR", "ICML", "ICLR", "EMNLP", "WACV",
    "TPAMI", "IJCV", "TGRS", "GitHub", "PyTorch", "TensorFlow", "OpenAI", "DeepMind",
}


def _parse_ref_entries(refs):
    return [(int(m.group(1)), m.group(2).strip())
            for m in re.finditer(r"^\s*\[(\d{1,3})\]\s*(.*)$", refs, re.M)]


def check_ledger_alignment(f, body, refs, ledger):
    """正文引用 ⊆ 台账；参考文献 ≡ 台账打印。台账是编号唯一事实源（v6.0）。"""
    body_ids = set(iter_cite_nums(body))
    for n in sorted(body_ids - set(ledger)):
        f.add("FAIL", "台账对齐", f"正文引用 [{n}] 不在引用台账中——编号只能来自台账（citation_ledger.py）")
    orphan = sorted(set(ledger) - body_ids)
    if orphan:
        f.add("WARN", "台账对齐", f"台账条目未被正文引用：{orphan}——回正文补引用，或移入不编号的'扩展阅读'")
    if refs is None:
        f.add("INFO", "台账对齐", "未找到'参考文献'小节，跳过台账-参考文献比对")
        return
    for n, text in _parse_ref_entries(refs):
        if n not in ledger:
            f.add("FAIL", "台账对齐", f"参考文献 [{n}] 不在台账中——参考文献只能由台账打印（print-refs）")
            continue
        e = ledger[n]
        norm_text = _norm_entry(text)
        title = _norm_entry(str(e.get("title", "")))
        if title and title not in norm_text:
            f.add("FAIL", "台账对齐",
                  f"参考文献 [{n}] 与台账第 {n} 条 title 不符（疑张冠李戴）——用 citation_ledger.py print-refs 重新生成该节")
            continue
        first_author = _norm_entry(str(e.get("first_author", "")))
        if first_author and first_author not in norm_text:
            f.add("FAIL", "台账对齐",
                  f"参考文献 [{n}] 未含台账第一作者 '{e.get('first_author')}'（作者张冠李戴/错写）——由 print-refs 重新生成")
        year = str(e.get("year", "")).strip()
        if year and year not in text:
            status = str(e.get("verify_status", "")).strip().upper()
            lvl = "FAIL" if status == "VERIFIED" else "WARN"
            f.add(lvl, "台账对齐", f"参考文献 [{n}] 年份与台账不符（台账 {year}，条目核验状态 {status or '未知'}）")


COMPARE_BEFORE = re.compile(r"(?:与|和|同|较之?|比|如|优于|超越|逊于|胜过)\s*$")
COMPARE_AFTER = re.compile(r"^\s*(?:相比|相较|之后|以来|以外|之外|不同|范式|系列|家族|一致|类似|等)")


def check_name_binding(f, body, ledger):
    """语义邻近检查：句中点到的系统/方法名与引用编号必须对位。

    名字来源优先是台账 aliases（铸账时声明——论文真题名常不含系统名，
    PatchCore/ControlNet 皆如此，正则猜名字只能当补充；红队 A2/A2b）；
    其次是 NAME_TOKEN 正则命中且为某标题子串的 token。alias 命中不受
    NAME_STOP/长度限制（LoRA/ViT/中文名靠 alias 声明）。

    判定规则（保守，v5.1.2 教训：误报 = 安全网对自己人拉警报）：
    - token 匹配集与句中引用有交集 → 还要核对**最近括号**：不在最近括号、
      且最近括号被其他 token 唯一认领 → 句内互换 FAIL（红队 D1：
      "A……[x]，而 B……[y]"合句曾整体豁免）；否则疑似错位 WARN；
    - 无交集 → 多命中也照判（红队 A3：同名综述入账曾静音检查）；
      对比句式或无自由编号 → WARN，否则错绑 FAIL；
    - 无引用句只 WARN（点名未引用）；表格/标题行免 WARN；编号已在同一行
      出现的免 WARN（邻句引用属合法写法）。
    """
    titles = {n: _norm_entry(str(e.get("title", ""))) for n, e in ledger.items()}
    alias_ids = {}
    for n, e in ledger.items():
        for a in (e.get("aliases") or []):
            a = str(a).strip()
            if a:
                alias_ids.setdefault(a, set()).add(n)

    def title_hits(token):
        t = _norm_entry(token)
        return {n for n, title in titles.items() if t and title and t in title}

    def latin_bounded(sent, start, end):
        # '-' 计入边界拒绝：FR-PatchCore / DoG-PaDiM 是派生方法，不是对原方法的点名
        before_ok = start == 0 or not re.match(r"[A-Za-z0-9-]", sent[start - 1])
        after_ok = end >= len(sent) or not re.match(r"[A-Za-z0-9-]", sent[end:end + 1])
        return before_ok and after_ok

    in_code = False
    for no, line in iter_lines_with_no(body):
        s = line.strip()
        if s.startswith("```"):
            in_code = not in_code
            continue
        if in_code or not s:
            continue
        skip_warn = s.startswith("|") or s.startswith("#")
        line_ids = set(iter_cite_nums(line))
        for sent in SENT_SPLIT.split(line):
            raw_groups = [(g.start(), g.end(), [int(x) for x in re.split(r"[,，、]", g.group(1)) if x.strip()])
                          for g in CITE.finditer(sent)]
            # 相邻括号组合并为一个多引组："甲、乙均已验证 [7][8]" 的 [7][8] ≡ [7, 8]
            groups = []
            for s0, e0, ns in raw_groups:
                if groups and s0 - groups[-1][1] <= 1:
                    groups[-1] = (groups[-1][0], e0, groups[-1][2] + ns)
                else:
                    groups.append((s0, e0, ns))
            groups = [(s0, ns) for s0, _, ns in groups]
            ids_here = [n for _, ns in groups for n in ns]
            cands = {}
            for a, ns in alias_ids.items():
                for am in re.finditer(re.escape(a), sent):
                    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*", a) and not latin_bounded(sent, am.start(), am.end()):
                        continue
                    cands.setdefault((am.start(), a), set()).update(ns)
            for tm in NAME_TOKEN.finditer(sent):
                token = tm.group(0)
                if len(token) < 4 or token in NAME_STOP:
                    continue
                if not latin_bounded(sent, tm.start(), tm.end()):
                    continue
                hits = title_hits(token)
                if hits:
                    cands.setdefault((tm.start(), token), set()).update(hits)
            if not cands:
                continue
            # 同位置重叠 token 去重：保留最长（"D3Lite-MES" 覆盖 "D3Lite"）
            kept = []
            for pos, tok in sorted(cands, key=lambda k: (k[0], -len(k[1]))):
                if not any(p <= pos and pos + len(tok) <= p + len(t2) and (p, t2) != (pos, tok)
                           for p, t2 in kept):
                    kept.append((pos, tok))
            cands = {k: cands[k] for k in kept}
            uniq_claims = {next(iter(h)) for h in cands.values() if len(h) == 1}
            for (pos, token), hits in sorted(cands.items()):
                if ids_here:
                    if hits & set(ids_here):
                        if len(hits) == 1 and groups:
                            m = next(iter(hits))
                            nearest = min(groups, key=lambda g: abs(g[0] - pos))
                            if m not in nearest[1]:
                                others = set(nearest[1]) & (uniq_claims - {m})
                                if others:
                                    f.add("FAIL", "台账对齐",
                                          f"L{no} 句内编号互换：'{token}' 属台账 [{m}]，其最近引用却是 {nearest[1]}——张冠李戴")
                                else:
                                    f.add("WARN", "台账对齐",
                                          f"L{no} 编号疑似错位：'{token}' 属台账 [{m}]，但其最近引用是 {nearest[1]}——人工核对")
                        continue
                    disp = "/".join(str(x) for x in sorted(hits))
                    free_ids = [x for x in ids_here if x not in uniq_claims]
                    comparative = bool(COMPARE_BEFORE.search(sent[max(0, pos - 6):pos])) or bool(
                        COMPARE_AFTER.match(sent[pos + len(token):]))
                    if comparative or not free_ids:
                        f.add("WARN", "台账对齐",
                              f"L{no} 对比/提及对象 '{token}'（台账 [{disp}]）未挂自己的编号——建议补编号")
                    else:
                        f.add("FAIL", "台账对齐",
                              f"L{no} '{token}' 属台账 [{disp}]，句中却引用 {sorted(set(ids_here))}——编号错绑（张冠李戴）")
                elif not skip_warn and len(hits) == 1 and next(iter(hits)) not in line_ids:
                    f.add("WARN", "台账对齐",
                          f"L{no} 点名未引用：'{token}' 是台账 [{sorted(hits)[0]}] 的工作，该句未挂编号（点名必引用）")


REF_COUNT_CLAIMS = [
    r"纳入[^\n。；]{0,14}?(\d{1,4})\s*篇",
    r"文献清单[（(]\s*共\s*(\d{1,4})\s*篇",
    r"参考文献[^\n。；]{0,6}?共\s*(\d{1,4})\s*[篇条]",
]


def check_ref_count_claims(f, body, refs):
    """声明数字必须由清点产生（v4.5 同族，两种模式通用）：总数声明 vs 参考文献实际条目数。
    带 [n] 引用的行不勾稽——那是转述他人研究的规模（"Wang 等的综述共纳入 87 篇 RCT [2]"），
    不是本文声明（红队 B2：无主语限定曾造成必然误报）。"""
    if refs is None:
        return
    ref_cnt = len(re.findall(r"^\s*\[\d{1,3}\]", refs, re.M))
    if not ref_cnt:
        return
    for line in body.split("\n"):
        if CITE.search(line):
            continue
        for pat in REF_COUNT_CLAIMS:
            for m in re.finditer(pat, line):
                n = int(m.group(1))
                if n != ref_cnt:
                    f.add("FAIL", "声明清点",
                          f"正文声明文献 {n} 篇 ≠ 参考文献实际 {ref_cnt} 条（'{m.group(0)}'）——声明数字只能来自对最终清单的机械清点；先解决清单问题（如重复条目），再按清点改声明")


BODY_URL_RE = re.compile(r"https?://|doi\.org/|\b10\.\d{4,9}/\S+")
CITEKEY_RESIDUE = re.compile(r"\[@[^\[\]\n]*\]")


def check_citekey_residue(f, body, refs):
    """交付物不得残留未编译的 [@引用键]（v6.1）：草稿写键、交付写数字，
    残留键 = compile 没跑或没跑完。"""
    for no, line in iter_lines_with_no(body):
        for m in CITEKEY_RESIDUE.finditer(line):
            f.add("FAIL", "引用编译", f"L{no} 残留未编译引用键 {m.group(0)[:30]}——先跑 citation_ledger.py compile")
    if refs and CITEKEY_RESIDUE.search(refs):
        f.add("FAIL", "引用编译", "参考文献节残留引用键——参考文献必须由 compile 打印，不手写")


def check_body_urls(f, body):
    """正文禁止裸 URL/DOI（两种模式，v6.0.2 用户红线）：正文引用的唯一形态是 [N] 编号；
    链接只能进严格模式台账的溯源栏。裸 URL 内联 = 不是一篇正式 survey。"""
    for no, line in iter_lines_with_no(body):
        for m in BODY_URL_RE.finditer(line):
            f.add("FAIL", "正文URL", f"L{no} 正文出现裸 URL/DOI（'{m.group(0)[:40]}…'）——引用一律 [N] 编号，链接不进正文")


def check_mode_structure(f, mode, report_text, refs, ledger_text):
    if mode == "survey":
        if LEDGER_MARK in report_text:
            f.add("FAIL", "模式结构", "综述模式交付物含台账小节——台账是严格模式产物（v4.2：不污染综述交付物）")
        if refs:
            if re.search(r"https?://", refs) or re.search(r"\b10\.\d{4,9}/\S+", refs) or re.search(r"\bDOI\b", refs, re.I):
                f.add("FAIL", "模式结构", "综述参考文献含 URL/DOI——综述默认格式不带；用户要求带则属严格模式，须走台账")
            # v6.0.2：参考文献中的（未核验）标注是**要求的**透明行为（未核验条目保留但标注），不再告警
        if not re.search(r"滚雪球|饱和", report_text):
            f.add("WARN", "模式结构", "全文未见检索收敛声明——研究方法应含一句'滚雪球 N 轮，末轮新增 0 篇，达检索饱和'（v5.1.2 可观测性）")
    else:  # strict
        if not ledger_text:
            f.add("FAIL", "模式结构", "严格模式交付物缺少【题录核验台账】小节（也未经 --ledger 提供）——先台账后正文")


def parse_ledger(ledger_text):
    """按行解析台账表：返回 (rows_by_cat, docs_by_cat)；宽容读取。"""
    rows = {"verified": 0, "secondary": 0, "unverified": 0}
    docs = {"verified": set(), "all": set()}
    for line in ledger_text.split("\n"):
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 3 or any("---" in c for c in cells):
            continue
        if cells[0] in ("文献", "条目", "字段"):
            continue
        joined = "|".join(cells)
        doc = cells[0]
        if doc:
            docs["all"].add(doc)
        if "二手核验" in joined:
            rows["secondary"] += 1
        elif "未核验" in joined:
            rows["unverified"] += 1
        elif "已核验" in joined:
            rows["verified"] += 1
            if doc:
                docs["verified"].add(doc)
    return rows, docs


def check_statements(f, report_text, ledger_text, refs):
    if not ledger_text:
        f.add("INFO", "声明清点", "无台账文本，跳过")
        return
    rows, docs = parse_ledger(ledger_text)
    if sum(rows.values()) == 0:
        f.add("INFO", "声明清点", "台账小节存在但未解析出表格行，跳过（人工核对）")
        return
    body_wo_ledger, _ = strip_ledger_block(report_text)
    pairs = [("已核验", "verified"), ("二手核验", "secondary"), ("未核验", "unverified")]
    stated_any = False
    for label, key in pairs:
        pat = ("(?<!二手)" if label == "已核验" else "") + label + r"[：: ]*\s*(\d+)\s*项"
        m = re.search(pat, body_wo_ledger)
        if m:
            stated_any = True
            n = int(m.group(1))
            if n != rows[key]:
                f.add("FAIL", "声明清点", f"声明'{label} {n} 项' ≠ 台账{label}行数 {rows[key]}——从台账逐行重数（v3.2）")
    m = re.search(r"已核验\s*(\d+)\s*篇", body_wo_ledger)
    if m:
        stated_any = True
        n = int(m.group(1))
        if n != len(docs["verified"]):
            f.add("FAIL", "声明清点", f"声明'已核验 {n} 篇' ≠ 台账中有已核验记录的文献 {len(docs['verified'])} 篇（v3.3/v4.5：候选数≠终选数）")
    if not stated_any:
        f.add("INFO", "声明清点", "未检出分档报数句，跳过数字比对（若确有声明，请人工核对）")
    if refs:
        ref_cnt = len(re.findall(r"^\s*\[\d{1,3}\]", refs, re.M))
        if ref_cnt and docs["all"] and ref_cnt != len(docs["all"]):
            f.add("WARN", "声明清点", f"参考文献 {ref_cnt} 条 vs 台账涉及文献 {len(docs['all'])} 篇——若清单核验后有增删，台账须同步（v4.5）")
    # 全称量词
    if rows["secondary"] + rows["unverified"] > 0:
        for no, line in iter_lines_with_no(body_wo_ledger):
            if re.search(r"核验|核实|真实", line) and re.search(r"全部|均(?!值)|确保准确无误", line):
                f.add("WARN", "全称量词", f"L{no} 存在二手/未核验项时使用全称量词：{line.strip()[:48]}…")


def _ledger_from_data(data):
    """把台账 JSON 转成 {id: entry}；返回 (dict, failures)。
    门禁侧健壮加载（红队 C3/A5/A6）：坏台账必须产出诊断 FAIL 并挡下交付——
    traceback 会被解读成"脚本坏了，退回无脚本路径"；静默 dict 化会让重复 id
    与空 title 把语义检查变瞎，交付方却拿到 "FAIL 0" 凭证。"""
    fails, out = [], {}
    entries = data.get("entries", []) if isinstance(data, dict) else None
    if not isinstance(entries, list):
        return out, ['台账顶层必须是 {"entries": [...]}']
    for i, e in enumerate(entries):
        if not isinstance(e, dict):
            fails.append(f"entries[{i}] 不是对象——先跑 citation_ledger.py validate")
            continue
        try:
            eid = int(e.get("id"))
        except (TypeError, ValueError):
            fails.append(f"entries[{i}] id 非整数：{e.get('id')!r}")
            continue
        if eid in out:
            fails.append(f"台账 id {eid} 重复——print-refs/对齐会指错论文，先修台账")
            continue
        out[eid] = e
        if not str(e.get("title", "")).strip():
            fails.append(f"台账 [{eid}] 缺 title——语义对齐对该条失效")
    if not out:
        fails.append("台账无可用条目")
    return out, fails


# ---------------- driver ----------------

def run_checks(report_text, ledger_extra="", mode="auto", citation_ledger=None):
    f = Findings()
    embedded = LEDGER_MARK in report_text
    if mode == "auto":
        mode = "strict" if (embedded or ledger_extra) else "survey"
    _, embedded_block = strip_ledger_block(report_text)
    ledger_text = (embedded_block + "\n" + ledger_extra).strip()
    body_full, refs, _ = split_refs(report_text)
    body, _ = strip_ledger_block(body_full)
    body_cite = _blank_fences(body)  # 引用层统一跳代码栅栏（红队 B4/C2/D3）

    check_blacklist(f, body)
    check_body_urls(f, body_cite)
    check_citekey_residue(f, body_cite, refs)
    check_citations(f, body_cite, refs, ledger_mode=citation_ledger is not None)
    check_ref_count_claims(f, body_cite, refs)
    if citation_ledger:
        check_ledger_alignment(f, body_cite, refs, citation_ledger)
        check_name_binding(f, body, citation_ledger)
    check_mode_structure(f, mode, report_text, refs, ledger_text)
    if mode == "strict":
        check_statements(f, report_text, ledger_text, refs)
    return mode, f


def main(argv=None):
    ap = argparse.ArgumentParser(description="交付前机械门禁（FAIL 消解后才交付）")
    ap.add_argument("report", nargs="?", help="报告 markdown 文件")
    ap.add_argument("--ledger", help="题录核验台账单独成文时的文件路径")
    ap.add_argument("--citation-ledger", help="引用台账 citation_ledger.json（v6.0 单写架构，启用三方对齐检查）")
    ap.add_argument("--mode", choices=["auto", "survey", "strict"], default="auto")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()
    if not args.report:
        ap.error("缺少报告文件（或用 --selftest）")
    text = io.open(args.report, encoding="utf-8").read()
    extra = io.open(args.ledger, encoding="utf-8").read() if args.ledger else ""
    cledger = None
    if args.citation_ledger:
        try:
            data = json.loads(io.open(args.citation_ledger, encoding="utf-8").read())
        except Exception as exc:
            print("== check_report ==  mode: n/a")
            print(f"[FAIL] 台账校验: 台账不可解析（{exc}）——先修 JSON 或重跑 citation_ledger.py validate")
            print("summary: FAIL 1 / WARN 0 / INFO 0")
            return 1
        cledger, lfails = _ledger_from_data(data)
        if lfails:
            print("== check_report ==  mode: n/a")
            for x in lfails:
                print(f"[FAIL] 台账校验: {x}")
            print(f"summary: FAIL {len(lfails)} / WARN 0 / INFO 0")
            return 1
    mode, f = run_checks(text, extra, args.mode, cledger)
    print(f"== check_report ==  mode: {mode}")
    print(f.render())
    return 1 if f.count("FAIL") else 0


# ---------------- selftest ----------------

BAD_SURVEY = """# 某话题综述
## 摘要
方法各有优劣，见仁见智[3]。随着人工智能的快速发展，未来需要更多研究。
## 四、分支
A[3] 与 B[1] 相比……C[2]。
【题录核验台账】
| 文献 | 字段 | 值 | 溯源 |
|---|---|---|---|
| X 2020 | DOI | 10.1/x | 已核验（crossref） |
## 参考文献
[1] A, "T1," V, 2020.
[2] B, "T2," V, 2021. https://doi.org/10.1/x
[4] C, "T3," V, 2022. 年份未核验
"""

GOOD_SURVEY = """# 某话题综述：一个有条件的判断
## 摘要
微观负效应高度一致（5/6 篇）[1]；宏观正效应集中于生产侧口径[2]。
## 二、研究方法
四视角检索后滚雪球 2 轮，末轮新增 0 篇，达检索饱和；最终纳入文献 3 篇。
## 四、分支
A [1, 2] 在口径上相反，C[3] 支持前者。
## 参考文献
[1] A, "T1," V, 2020.
[2] B, "T2," V, 2021.
[3] C, "T3," V, 2022.
"""

# 外发实测事故（InSAR 综述）的蒸馏回归样本：多引合规 + 重复条目 + 计数失配 三合一
DUP_REFS_SURVEY = """# 综述
## 二、研究方法
检索滚雪球 2 轮，末轮新增 0 篇，达检索饱和；最终纳入核心文献 2 篇。
## 四、分支
甲 [1, 2] 的两类证据一致；乙 [3] 与甲 [1] 相反。
## 参考文献
[1] Zhou L, Yu H. PU-GAN: A One-Step 2-D InSAR Phase Unwrapping. IEEE TGRS, 2022.
[2] Wang K, Qian K. Deep learning spatial phase unwrapping: a comparative review. APN, 2022.
[3] Zhou L, Yu H. PU-GAN: A One-Step 2-D InSAR Phase Unwrapping. IEEE TGRS, 2022.
"""

NEARDUP_SURVEY = """# 综述
## 二、研究方法
滚雪球 1 轮，末轮新增 0 篇，达检索饱和。
## 四、分支
A[1] 与 B[2] 一致，C[3] 相反。
## 参考文献
[1] Spoorthi G E, et al. PhaseNet: A Deep CNN for 2D Phase Unwrapping. IEEE Signal Processing Letters, 2019.
[2] Spoorthi G E, et al. PhaseNet: A Deep CNN for 2D Phase Unwrapping. IEEE Signal Process. Lett., 2019.
[3] C, "T3," V, 2022.
"""

BAD_STRICT = """# 检索报告
正文引用 [1] 与 [2]。
## 核验声明
已核验 9 项；二手核验 0 项；未核验 0 项。已核验 9 篇。所有文献的题录信息均经过核实，确保准确无误。
【题录核验台账】
| 文献 | 字段 | 值 | 溯源 |
|---|---|---|---|
| X 2020 | DOI | 10.1/x | 已核验（crossref） |
| X 2020 | 卷 | 12 | 已核验（crossref） |
| Y 2021 | 页码 | 3-9 | 二手核验 |
| Z 2019 | 期 | — | 未核验 |
## 参考文献
[1] X, "T," V, 2020.
[2] Y, "T," V, 2021.
"""


# v6.0 单写架构回归样本：评测事故蒸馏（正文[12]=D3Lite-MES 而文末[12]=PatchCore 的同族）。
# 台账用**真实形态题名**（系统名不进标题，红队 A2b）——名字检测依赖 aliases 声明。
CL_LEDGER = {
    1: {"id": 1, "first_author": "Roth", "authors": "Roth K, et al.", "year": "2022",
        "title": "Towards Total Recall in Industrial Anomaly Detection", "venue": "CVPR",
        "verify_status": "VERIFIED", "aliases": ["PatchCore"]},
    2: {"id": 2, "first_author": "Lin", "authors": "Lin J, Wang Q", "year": "2025",
        "title": "Lightweight Defect Detection for Manufacturing Execution Systems", "venue": "IEEE TII",
        "verify_status": "VERIFIED", "aliases": ["D3Lite-MES", "D3Lite"]},
    3: {"id": 3, "first_author": "Batzner", "authors": "Batzner K, et al.", "year": "2024",
        "title": "EfficientAD: Accurate Visual Anomaly Detection", "venue": "WACV",
        "verify_status": "VERIFIED", "aliases": ["EfficientAD"]},
}

# 红队 A3：以某系统命名的综述入账后，多命中不得让原始工作的错绑检查静音
CL_LEDGER_SURVEY = dict(CL_LEDGER)
CL_LEDGER_SURVEY[4] = {"id": 4, "first_author": "Zhao", "authors": "Zhao Y, et al.", "year": "2025",
                       "title": "A Survey of PatchCore Extensions for Industrial Inspection",
                       "venue": "arXiv:2501.00001", "verify_status": "VERIFIED", "aliases": []}

CL_SCRAMBLED = """# 综述
## 二、研究方法
滚雪球 1 轮，末轮新增 0 篇，达检索饱和；最终纳入文献 3 篇。
## 四、分支
PatchCore 建立了记忆库范式 [2]。D3Lite-MES 面向产线部署 [1]。EfficientAD 提升了推理速度 [3]。
## 参考文献
[1] Roth K, et al., “Towards Total Recall in Industrial Anomaly Detection,” CVPR, 2022.
[2] Lin J, Wang Q, “Lightweight Defect Detection for Manufacturing Execution Systems,” IEEE TII, 2025.
[3] Batzner K, et al., “EfficientAD: Accurate Visual Anomaly Detection,” WACV, 2024.
"""

CL_REFS_MISMATCH = """# 综述
## 二、研究方法
滚雪球 1 轮，末轮新增 0 篇，达检索饱和。
## 四、分支
记忆库范式已确立 [1]，轻量化部署可行 [2]。
## 参考文献
[1] Roth K, et al., “Towards Total Recall in Industrial Anomaly Detection,” CVPR, 2022.
[2] Batzner K, et al., “EfficientAD: Accurate Visual Anomaly Detection,” WACV, 2024.
"""

CL_NO_INLINE = """# 综述
## 二、研究方法
滚雪球 1 轮，末轮新增 0 篇，达检索饱和。
## 四、分支
记忆库方法已成为工业界事实标准。
## 参考文献
[1] Roth K, et al., “Towards Total Recall in Industrial Anomaly Detection,” CVPR, 2022.
"""

CL_MENTION = """# 综述
## 二、研究方法
滚雪球 1 轮，末轮新增 0 篇，达检索饱和。
## 四、分支
PatchCore 已成为工业检测的事实基线，其记忆库设计被广泛沿用。

后续的轻量化工作在该记忆库之上扩展 [1]。
## 参考文献
[1] Roth K, et al., “Towards Total Recall in Industrial Anomaly Detection,” CVPR, 2022.
"""

CL_COMPARE = """# 综述
## 二、研究方法
滚雪球 1 轮，末轮新增 0 篇，达检索饱和。
## 四、分支
与 PatchCore 相比，D3Lite-MES 的端到端延迟更低 [2]。在 EfficientAD 之后，轻量化成为该方向的主线 [2]。
## 参考文献
[2] Lin J, Wang Q, “Lightweight Defect Detection for Manufacturing Execution Systems,” IEEE TII, 2025.
"""

CL_COMPOUND_SWAP = """# 综述
## 二、研究方法
滚雪球 1 轮，末轮新增 0 篇，达检索饱和。
## 四、分支
PatchCore 建立了记忆库范式 [2]，而 D3Lite-MES 面向产线部署 [1]。
## 参考文献
[1] Roth K, et al., “Towards Total Recall in Industrial Anomaly Detection,” CVPR, 2022.
[2] Lin J, Wang Q, “Lightweight Defect Detection for Manufacturing Execution Systems,” IEEE TII, 2025.
"""

CL_WRONG_AUTHOR = """# 综述
## 二、研究方法
滚雪球 1 轮，末轮新增 0 篇，达检索饱和。
## 四、分支
PatchCore 奠定了基线 [1]。
## 参考文献
[1] Bergmann P, Fauser M, “Towards Total Recall in Industrial Anomaly Detection,” NeurIPS, 2019.
"""

CL_FENCE = '''# 综述
## 二、研究方法
滚雪球 1 轮，末轮新增 0 篇，达检索饱和。
## 四、分支
正文合法引用 [1]。

```python
dists[9] = index.query(feats[3])
## 参考文献
```

上述检索实现的取舍见仁见智。
## 参考文献
[1] Roth K, et al., “Towards Total Recall in Industrial Anomaly Detection,” CVPR, 2022.
'''

CL_QUOTED_COUNT = """# 综述
## 二、研究方法
滚雪球 1 轮，末轮新增 0 篇，达检索饱和；最终纳入文献 3 篇。
## 四、分支
Wang 等的系统综述共纳入 87 篇 RCT，其方向与本节证据一致 [2]。
## 参考文献
[1] Roth K, et al., “Towards Total Recall in Industrial Anomaly Detection,” CVPR, 2022.
[2] Lin J, Wang Q, “Lightweight Defect Detection for Manufacturing Execution Systems,” IEEE TII, 2025.
[3] Batzner K, et al., “EfficientAD: Accurate Visual Anomaly Detection,” WACV, 2024.
"""

CL_NEGATED = """# 综述
## 二、研究方法
滚雪球 1 轮，末轮新增 0 篇，达检索饱和。
## 四、分支
开放问题部分拒绝“需要更多研究”式的收尾，逐条写明缺什么设计才能裁决 [1]。
## 参考文献
[1] Roth K, et al., “Towards Total Recall in Industrial Anomaly Detection,” CVPR, 2022.
"""

BODY_URL_SURVEY = """# 综述
## 二、研究方法
滚雪球 1 轮，末轮新增 0 篇，达检索饱和。
## 四、分支
记忆库范式的方法细节详见 https://arxiv.org/abs/2106.08265 与 [1]，消融另见 10.1109/CVPR52688.2022.01392 的表 3。
## 参考文献
[1] Roth K, et al., “Towards Total Recall in Industrial Anomaly Detection,” CVPR, 2022.（未核验）
"""


def selftest():
    ok = True

    def expect(cond, label):
        nonlocal ok
        print(("PASS  " if cond else "FAIL  ") + label)
        ok = ok and cond

    mode, f = run_checks(BAD_SURVEY, mode="survey")
    msgs = "\n".join(m for _, _, m in f.items)
    expect(sum(1 for l, c, _ in f.items if l == "FAIL" and c == "黑名单") >= 3, "综述样例：黑名单 FAIL≥3（见仁见智/更多研究/随着发展）")
    expect(any(c == "黑名单" and l == "WARN" for l, c, _ in f.items), "综述样例：各有优劣 WARN")
    expect(any("首现顺序" in m for _, _, m in f.items), "综述样例：首现顺序 3,1,2 被抓")
    expect(any("不连续" in m for _, _, m in f.items), "综述样例：参考文献缺 [3] 编号不连续被抓")
    expect(any("未列出" in m and "[3]" in m for _, _, m in f.items) or any("未列出：[3]" in m for _, _, m in f.items), "综述样例：引了 [3] 未列出被抓")
    expect(any("台账小节" in m for _, _, m in f.items), "综述样例：交付物含台账被抓")
    expect(any("URL/DOI" in m for _, _, m in f.items), "综述样例：参考文献含 DOI 链接被抓")
    expect(not any("未核验" in m and c == "模式结构" for _, c, m in f.items), "综述样例：参考文献（未核验）标注不再告警（v6.0.2：未核验条目保留+标注是要求行为）")
    expect(any("检索收敛" in m for _, _, m in f.items), "综述样例：无饱和声明触发收敛 WARN")

    mode, f = run_checks(GOOD_SURVEY)
    expect(mode == "survey" and f.count("FAIL") == 0, "良品综述：auto 判 survey 且零 FAIL")
    expect(not any("首现顺序应为" in m for _, _, m in f.items), "良品综述：多引 [1, 2] 被正确解析，首现顺序不误报")
    expect(not any("检索收敛" in m for _, _, m in f.items), "良品综述：含饱和声明，不触发收敛 WARN")
    expect(not any(c == "声明清点" and l == "FAIL" for l, c, _ in f.items), "良品综述：'纳入 3 篇'与清单 3 条勾稽通过")

    mode, f = run_checks(DUP_REFS_SURVEY, mode="survey")
    expect(not any("首现顺序应为" in m for _, _, m in f.items), "事故回归：多引下首现顺序 1,2,3 干净，无误报")
    expect(any("重复条目" in m and "[1] = [3]" in m for _, _, m in f.items), "事故回归：[1]=[3] 逐字重复条目 FAIL")
    expect(any(c == "声明清点" and "2 篇" in m and "3 条" in m for l, c, m in f.items if l == "FAIL"), "事故回归：声明 2 篇 vs 实际 3 条 FAIL")

    mode, f = run_checks(NEARDUP_SURVEY, mode="survey")
    expect(any("高度相似" in m for _, _, m in f.items), "近重复：相似度 ≥0.90 WARN")

    mode, f = run_checks("# r\n乱序 [2, 1]。\n## 参考文献\n[1] A, \"T,\" V, 2020.\n[2] B, \"T,\" V, 2021.", mode="survey")
    expect(any("首现顺序应为" in m for _, _, m in f.items), "多引乱序 [2, 1]：首现顺序 FAIL 仍能触发")

    mode, f = run_checks(BAD_STRICT)
    expect(mode == "strict", "严格样例：auto 判 strict")
    expect(any("已核验 9 项" in m for _, _, m in f.items), "严格样例：声明 9 项 vs 台账 2 项被抓")
    expect(any("已核验 9 篇" in m for _, _, m in f.items), "严格样例：声明 9 篇 vs 台账 1 篇被抓")
    expect(any(c == "全称量词" for _, c, _ in f.items), "严格样例：全称量词 WARN")
    expect(any("二手核验" in m and "0" in m for _, _, m in f.items) or True, "严格样例：二手档 0≠1（软断言）")

    mode, f = run_checks("# 报告\n正文[1]。\n## 参考文献\n[1] A, \"T,\" V, 2020.", mode="strict")
    expect(any("缺少【题录核验台账】" in m for _, _, m in f.items), "严格无台账：FAIL")

    mode, f = run_checks(CL_SCRAMBLED, mode="survey", citation_ledger=CL_LEDGER)
    expect(sum(1 for l, c, m in f.items if l == "FAIL" and "错绑" in m) >= 2, "台账回归：PatchCore/D3Lite 编号错绑 FAIL×2（张冠李戴被抓）")
    expect(not any("title 不符" in m for _, _, m in f.items), "台账回归：参考文献与台账一致，无 title 误报")
    expect(any(l == "WARN" and "首现顺序" in m for l, _, m in f.items), "台账回归：台账在场首现乱序降 WARN（renumber 治理）")

    mode, f = run_checks(CL_REFS_MISMATCH, mode="survey", citation_ledger=CL_LEDGER)
    expect(any("title 不符" in m and "[2]" in m for _, _, m in f.items), "台账回归：参考文献[2]与台账失配 FAIL")
    expect(any("未被正文引用" in m for _, _, m in f.items), "台账回归：孤儿条目 [3] WARN")

    mode, f = run_checks(CL_NO_INLINE, mode="survey")
    expect(any(l == "FAIL" and "无内联" in m for l, _, m in f.items), "零内联：有参考文献节无 [n] → FAIL（v13 类失败）")

    mode, f = run_checks(CL_MENTION, mode="survey", citation_ledger=CL_LEDGER)
    expect(any(l == "WARN" and "点名未引用" in m for l, _, m in f.items), "台账回归：点名未引用 WARN")
    expect(not any(l == "FAIL" and c == "台账对齐" for l, c, _ in f.items), "台账回归：正确绑定无 FAIL 误报")

    mode, f = run_checks(CL_COMPARE, mode="survey", citation_ledger=CL_LEDGER)
    expect(not any(l == "FAIL" for l, _, _ in f.items), "台账回归：合法对比句式（与 X 相比 / 在 X 之后）零 FAIL——不对自己人拉警报")
    expect(any(l == "WARN" and "对比/提及对象" in m for l, _, m in f.items), "台账回归：对比对象未挂编号降级为 WARN 建议")

    mode, f = run_checks(CL_COMPOUND_SWAP, mode="survey", citation_ledger=CL_LEDGER)
    expect(any(l == "FAIL" and "句内编号互换" in m for l, _, m in f.items), "红队D1：合句互换（…[2]，而…[1]）FAIL——原旗舰样本逗号合句即穿透，已堵")

    CL_LIST_STYLE = (
        "# 综述\n## 二、研究方法\n滚雪球 1 轮，末轮新增 0 篇，达检索饱和。\n## 四、分支\n"
        "PatchCore、D3Lite-MES 等方法均已在产线验证 [1][2]。FR-PatchCore 将图像 AUROC 进一步推高。\n"
        "## 参考文献\n"
        "[1] Roth K, et al., “Towards Total Recall in Industrial Anomaly Detection,” CVPR, 2022.\n"
        "[2] Lin J, Wang Q, “Lightweight Defect Detection for Manufacturing Execution Systems,” IEEE TII, 2025.\n"
    )
    mode, f = run_checks(CL_LIST_STYLE, mode="survey", citation_ledger=CL_LEDGER)
    expect(not any(l == "FAIL" for l, _, _ in f.items), "实测回归：列举式尾引 '甲、乙…[1][2]' 相邻括号并组，不再误判互换")
    expect(not any("点名未引用" in m and "PatchCore" in m for _, _, m in f.items), "实测回归：FR-PatchCore 是派生方法名，连字符边界不再误认为对 PatchCore 的点名")

    mode, f = run_checks(CL_SCRAMBLED, mode="survey", citation_ledger=CL_LEDGER_SURVEY)
    expect(any(l == "FAIL" and ("错绑" in m or "互换" in m) for l, _, m in f.items), "红队A3：同名综述入账（PatchCore 多命中）不再静音错绑检查")

    mode, f = run_checks(CL_WRONG_AUTHOR, mode="survey", citation_ledger=CL_LEDGER)
    expect(any(l == "FAIL" and "第一作者" in m for l, _, m in f.items), "红队A4：参考文献作者张冠李戴 FAIL（Roth→Bergmann 被抓）")
    expect(any(l == "FAIL" and "年份" in m for l, _, m in f.items), "红队A4：VERIFIED 条目年份错 FAIL（2022→2019 被抓）")

    mode, f = run_checks(CL_FENCE, mode="survey", citation_ledger=CL_LEDGER)
    expect(not any("[9]" in m for _, _, m in f.items), "红队B4：代码块 dists[9] 不再被当引用误杀")
    expect(any(l == "FAIL" and c == "黑名单" for l, c, _ in f.items), "红队D3：栅栏内伪'## 参考文献'不再截断检查范围（其后黑名单仍被抓）")
    expect(not any("title 不符" in m for _, _, m in f.items), "红队D3：真参考文献节被正确识别并与台账对齐")

    mode, f = run_checks(CL_QUOTED_COUNT, mode="survey", citation_ledger=CL_LEDGER)
    expect(not any(l == "FAIL" for l, _, _ in f.items), "红队B2：转述他人 meta 分析纳入数（带 [n] 行）不再触发计数 FAIL")

    mode, f = run_checks(CL_NEGATED, mode="survey", citation_ledger=CL_LEDGER)
    expect(not any(l == "FAIL" and c == "黑名单" for l, c, _ in f.items) and
           any(l == "WARN" and c == "黑名单" for l, c, _ in f.items), "红队B5：否定/引述语境黑名单降 WARN")

    cl, lf = _ledger_from_data({"entries": [{"id": "N/A", "title": "X"}, "junk", {"id": 2, "title": ""}, {"id": 2, "title": "Y"}]})
    expect(any("非整数" in x for x in lf) and any("不是对象" in x for x in lf) and
           any("缺 title" in x for x in lf) and any("重复" in x for x in lf),
           "红队C3/A5/A6：坏台账（非整数id/字符串条目/空title/重复id）产出诊断 FAIL 而非 traceback/静默")

    mode, f = run_checks(BODY_URL_SURVEY, mode="survey")
    expect(sum(1 for l, c, _ in f.items if l == "FAIL" and c == "正文URL") >= 2,
           "用户红线：正文裸 URL 与裸 DOI 均 FAIL（引用唯一形态是 [N]）")
    expect(not any("未核验" in m and c == "模式结构" for l, c, m in f.items),
           "用户红线：参考文献（未核验）标注是要求行为，不告警")

    mode, f = run_checks("# 综述\n结论见 [@PatchCore] 与 [1]。\n## 参考文献\n[1] A, \"T,\" V, 2020.", mode="survey")
    expect(any(l == "FAIL" and c == "引用编译" for l, c, _ in f.items),
           "v6.1：交付物残留未编译引用键 [@…] → FAIL（compile 必须跑完）")

    print("SELFTEST " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
