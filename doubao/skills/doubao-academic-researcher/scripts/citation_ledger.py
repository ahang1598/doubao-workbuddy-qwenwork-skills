# -*- coding: utf-8 -*-
"""
citation_ledger.py — 引用编号单一事实源（引用台账）工具（v6.0 单写架构）

定位：编号漂移（正文 [12] 与文末 [12] 指向不同论文）的根因是编号被独立书写
两次（写正文一次、组参考文献一次），靠模型工作记忆对账。唯一可靠解是单一
事实源：编号在台账铸定一次，此后正文只抄、参考文献只打印（write-once,
print-many）。本脚本是台账的配套工具；对齐校验在 check_report.py
（--citation-ledger）。

台账 JSON schema（.workflow/citation_ledger.json）：
{
  "entries": [
    {"id": 1,
     "first_author": "Roth",
     "authors": "Roth K, et al.",
     "year": "2022",
     "title": "Towards Total Recall in Industrial Anomaly Detection",
     "venue": "CVPR",
     "verify_status": "VERIFIED",          # VERIFIED / MINOR / PAYWALL 可入账
     "aliases": ["PatchCore"],             # 系统名/常用简称，铸账时从工具返回抄录——
                                            # 论文真题名常不含系统名（PatchCore/ControlNet 皆如此），
                                            # 语义邻近检查依赖本字段声明名字，而非正则猜名字
     "role": "奠基工作",                    # 可选：角色标签
     "criteria": {"直接相关-鱼类任务": true}, # 可选：用户分级标准布尔字段
     "note": ""}
  ]
}

台账每次变更（含补搜追加）后必须重跑 validate；id 重复会让 print-refs 指错论文。

子命令：
  compile     **主路径（v6.1 引用键编译）**：把草稿里的 [@引用键] 编译为 [N] 数字
              引用（按首现顺序铸造）并同趟打印参考文献。草稿全程不出现数字编号
              ——数字由编译器铸造，模型从头到尾没碰过数字，正文↔文末错绑在构造
              上不可能（LaTeX \\cite + BibTeX 同型方案）。未知键、草稿手写数字
              引用均硬报错。键 = 台账 key 字段（默认取首个 alias，无 alias 用
              姓+年），alias 与 id 也可作键，大小写不敏感。多引 [@A; @B]。
  validate    台账 schema 校验：id 为正整数且唯一、引用键唯一、必填字段齐全、
              verify_status 合法（MAJOR/UNVERIFIABLE 不得入账——灰区不使用）。
  print-refs  从台账打印“参考文献”节（唯一合法的参考文献生成方式）。
              --report 给定时只打印正文实际引用的条目；未被引用的条目列到
              stderr（回正文补引用，或移入不编号的“扩展阅读”）。
  renumber    交付美化（可选）：按正文首现顺序把 [n]/[n, m] 原子重排为 1..K，
              正文与参考文献同一趟改写，并输出重排后的台账副本
              （*.delivery.json）。这是“重排只允许脚本原子完成”的唯一合法
              路径；无脚本环境不重排——绑定正确性优先于编号美观。
  csv         从台账序列化文献证据表 CSV（csv.writer 自动处理含逗号字段，
              消灭手打 CSV 的串行错位）。含用户分级布尔字段列。

用法：
  python3 scripts/citation_ledger.py validate   --ledger .workflow/citation_ledger.json
  python3 scripts/citation_ledger.py print-refs --ledger .workflow/citation_ledger.json --report 报告.md
  python3 scripts/citation_ledger.py renumber   --ledger .workflow/citation_ledger.json --report 报告.md --output 报告.delivery.md
  python3 scripts/citation_ledger.py csv        --ledger .workflow/citation_ledger.json --output 证据表.csv
  python3 scripts/citation_ledger.py --selftest

出口码：validate/renumber 发现 FAIL → 1，否则 0。
"""
import argparse
import csv as _csv
import io
import json
import re
import sys

CITE = re.compile(r"\[(\d{1,3}(?:\s*[,，、]\s*\d{1,3})*)\]")
CITEKEY = re.compile(r"\[@([^\[\]\n]+?)\]")
REFS_HEADING_LINE = re.compile(r"^(?:(#{1,6})\s*|\*\*)(参考文献|References)(?:\*\*)?\s*[:：]?\s*$")
HEADING_LINE = re.compile(r"^#{1,6}\s+\S")
# VERIFIED/MINOR = 已核验；PAYWALL/UNVERIFIED = 论文存在但题录字段未全核验（允许入账，
# 交付时打印（未核验）标注——对读者透明，不强制剔除）；MAJOR 必须先修正；
# UNVERIFIABLE = 存在性都无法确认 = 编造风险，一条不进（这条底线不放松）。
ALLOWED_STATUS = ("VERIFIED", "MINOR", "PAYWALL", "UNVERIFIED")
VERIFIED_STATUS = ("VERIFIED", "MINOR")
REJECTED_STATUS = ("MAJOR", "UNVERIFIABLE")


def _fence_mask(lines):
    """逐行标记是否处于 ``` 代码栅栏内（含栅栏定界行本身）。"""
    mask, in_code = [], False
    for line in lines:
        if line.strip().startswith("```"):
            in_code = not in_code
            mask.append(True)
            continue
        mask.append(in_code)
    return mask


# ---------------- core helpers ----------------

def load_ledger(path):
    data = json.loads(io.open(path, encoding="utf-8").read())
    entries = data.get("entries", [])
    if not isinstance(entries, list):
        raise SystemExit("台账格式错误：顶层需为 {\"entries\": [...]}")
    return entries


def entries_by_id(entries):
    out = {}
    for e in entries:
        if not isinstance(e, dict):
            continue
        try:
            eid = int(e.get("id"))
        except (TypeError, ValueError):
            continue
        if eid in out:
            raise SystemExit(f"台账 id {eid} 重复——同一编号指向多篇论文，print-refs/renumber 会指错文献；先跑 validate 修台账")
        out[eid] = e
    return out


def iter_cite_nums(text):
    """按出现顺序产出引用编号；单引 [n] 与多引 [n, m]（含中文逗号/顿号）均识别。**跳过代码栅栏**——`dists[9]` 这类代码下标不是引用。"""
    lines = text.split("\n")
    mask = _fence_mask(lines)
    for i, line in enumerate(lines):
        if mask[i]:
            continue
        for m in CITE.finditer(line):
            for x in re.split(r"[,，、]", m.group(1)):
                x = x.strip()
                if x:
                    yield int(x)


def split_refs(text):
    """返回 (正文, 标题级别, 参考文献列表区, 尾部内容)。逐行解析：

    - 代码栅栏内的"## 参考文献"不算标题（防样例模板截断解析范围）；
    - 标题识别 #{1,6} 与整行加粗 **参考文献** 变体；
    - 尾部 = 参考文献标题之后第一个真实 markdown 标题起的内容（如附录），
      renumber 必须原样保留并同步重排其中的 [n]。
    """
    lines = text.split("\n")
    mask = _fence_mask(lines)
    start, level = None, "##"
    for i, line in enumerate(lines):
        if mask[i]:
            continue
        m = REFS_HEADING_LINE.match(line.strip())
        if m:
            start, level = i, (m.group(1) or "##")
            break
    if start is None:
        return text, None, None, ""
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if not mask[j] and HEADING_LINE.match(lines[j]):
            end = j
            break
    body = "\n".join(lines[:start])
    refs = "\n".join(lines[start + 1:end])
    tail = "\n".join(lines[end:]) if end < len(lines) else ""
    return body, level, refs, tail


def _sub_outside_fences(text, repl_fn):
    """对栅栏外的行做 CITE 替换，栅栏内原样保留（renumber 不改代码）。"""
    lines = text.split("\n")
    mask = _fence_mask(lines)
    return "\n".join(line if mask[i] else CITE.sub(repl_fn, line)
                     for i, line in enumerate(lines))


def format_entry(e):
    """按 skill 引用格式打印一条：[N] 作者, “标题,” 会议/期刊, 年份.
    非 VERIFIED/MINOR 条目自动附（未核验）标注——用户要求：未核验的可以保留，
    但必须让读者一眼看出哪些验证过、哪些没验证过。"""
    authors = str(e.get("authors") or e.get("first_author") or "").strip().rstrip(",")
    title = str(e.get("title", "")).strip()
    tail = ", ".join(p for p in (str(e.get("venue", "")).strip(), str(e.get("year", "")).strip()) if p)
    mark = "" if str(e.get("verify_status", "")).strip().upper() in VERIFIED_STATUS else "（未核验）"
    if tail:
        return f"[{e['id']}] {authors}, “{title},” {tail}.{mark}"
    return f"[{e['id']}] {authors}, “{title}.”{mark}"


# ---------------- validate ----------------

def validate_entries(entries):
    fails, warns = [], []
    if not entries:
        fails.append("台账为空——literature-scout 清单定稿后必须先铸台账")
        return fails, warns
    seen = set()
    for i, e in enumerate(entries):
        tag = f"entries[{i}]"
        if not isinstance(e, dict):
            fails.append(f"{tag}: 必须是对象，得到 {type(e).__name__}")
            continue
        try:
            eid = int(e.get("id"))
            if eid <= 0:
                fails.append(f"{tag}: id 必须为正整数，得到 {e.get('id')!r}")
                continue
        except (TypeError, ValueError):
            fails.append(f"{tag}: id 缺失或非整数：{e.get('id')!r}")
            continue
        if eid in seen:
            fails.append(f"{tag}: id {eid} 重复——同一来源一个编号，编号永不复用")
        seen.add(eid)
        if not str(e.get("title", "")).strip():
            fails.append(f"[{eid}] 缺 title")
        if not str(e.get("authors") or e.get("first_author") or "").strip():
            fails.append(f"[{eid}] 缺 authors/first_author")
        status = str(e.get("verify_status", "")).strip().upper()
        if status in REJECTED_STATUS:
            fails.append(f"[{eid}] verify_status={status}——存在性未确认/引述未修正的引用不得入台账（防编造底线；字段级未核验请用 UNVERIFIED，交付带标注）")
        elif status not in ALLOWED_STATUS:
            fails.append(f"[{eid}] verify_status 非法：{e.get('verify_status')!r}（合法值：{'/'.join(ALLOWED_STATUS)}）")
        if not str(e.get("year", "")).strip():
            warns.append(f"[{eid}] 缺 year（综述纪律：不确定宁可省略，此为提示非失败）")
        if not str(e.get("venue", "")).strip():
            warns.append(f"[{eid}] 缺 venue")
        crit = e.get("criteria")
        if crit is not None and not isinstance(crit, dict):
            fails.append(f"[{eid}] criteria 必须为对象（用户分级标准布尔字段）")
        al = e.get("aliases")
        if al is not None and (not isinstance(al, list) or any(not isinstance(x, str) for x in al)):
            fails.append(f"[{eid}] aliases 必须为字符串数组（系统名/常用简称，铸账时从工具返回抄录）")
        elif not al:
            warns.append(f"[{eid}] 无 aliases——语义邻近检查（名字↔编号）对该条大概率空转，建议补系统名/简称")
    # 引用键唯一性（compile 解析的地基）：显式/派生主键跨条目冲突 → FAIL
    prim = {}
    for e in entries:
        if not isinstance(e, dict):
            continue
        k = str(e.get("key") or derive_key(e)).strip().casefold()
        if k:
            if k in prim:
                fails.append(f"引用键 '{k}' 冲突（[{prim[k]}] 与 [{e.get('id')}]）——为其一显式设置不同 key（如 Smith2023a/b）")
            else:
                prim[k] = e.get("id")
    return fails, warns


# ---------------- print-refs ----------------

def render_refs(entries, report_text=None):
    """返回 (参考文献行列表, 未被引用的台账 id 列表)。"""
    by_id = entries_by_id(entries)
    if report_text is not None:
        body, _, _, _ = split_refs(report_text)
        cited = []
        seen = set()
        for n in iter_cite_nums(body):
            if n not in seen:
                seen.add(n)
                cited.append(n)
        missing = [n for n in cited if n not in by_id]
        if missing:
            raise SystemExit(f"正文引用了台账外编号 {missing}——编号只能来自台账；先修台账或正文")
        ids = sorted(seen)
        uncited = sorted(set(by_id) - seen)
    else:
        ids = sorted(by_id)
        uncited = []
    return [format_entry(by_id[i]) for i in ids], uncited


# ---------------- renumber ----------------

def renumber_report(text, entries):
    """按首现顺序原子重排（正文与尾部同扫）：返回 (新报告文本, 重排后的台账 entries, 未引用 id)。"""
    by_id = entries_by_id(entries)
    body, heading_level, refs, tail = split_refs(text)
    scan = body + "\n" + tail
    order, seen = [], set()
    for n in iter_cite_nums(scan):
        if n not in seen:
            seen.add(n)
            order.append(n)
    if not order:
        raise SystemExit("正文无 [n] 引用，无可重排——先保证点名必引用")
    missing = [n for n in order if n not in by_id]
    if missing:
        raise SystemExit(f"正文引用了台账外编号 {missing}——重排前先对齐台账")
    mapping = {old: i + 1 for i, old in enumerate(order)}

    def repl(m):
        nums = [x.strip() for x in re.split(r"[,，、]", m.group(1)) if x.strip()]
        return "[" + ", ".join(str(mapping[int(x)]) for x in nums) + "]"

    new_body = _sub_outside_fences(body, repl)
    new_tail = _sub_outside_fences(tail, repl) if tail else ""
    delivery_entries = [dict(by_id[old], id=mapping[old]) for old in order]
    lvl = heading_level or "##"
    # 参考文献区内的非条目行（说明性散文/核验注记）原样保留在重印条目之后，不得吞掉
    prose_keep = [ln for ln in (refs or "").split("\n")
                  if ln.strip() and not re.match(r"^\s*\[\d{1,3}\]", ln)]
    out = new_body if new_body.endswith("\n") else new_body + "\n"
    out += "\n" + f"{lvl} 参考文献\n\n" + "\n".join(format_entry(e) for e in delivery_entries) + "\n"
    if prose_keep:
        out += "\n" + "\n".join(prose_keep) + "\n"
    if new_tail.strip():
        out += "\n" + new_tail.lstrip("\n")
    uncited = sorted(set(by_id) - set(order))
    return out, delivery_entries, uncited


# ---------------- compile：引用键 → 数字编号（主路径） ----------------

def derive_key(e):
    """条目的默认引用键：首个 alias > 姓+年 > id。"""
    for a in (e.get("aliases") or []):
        a = str(a).strip()
        if a:
            return a
    fa = str(e.get("first_author", "")).strip()
    yr = str(e.get("year", "")).strip()
    if fa:
        return f"{fa}{yr}" if yr else fa
    return str(e.get("id", "")).strip()


def build_key_map(entries):
    """返回 (key_casefold -> entry)。可用键 = 显式 key / 派生 key / 全部 aliases / str(id)；
    跨条目歧义的键从映射中剔除（解析它会报未知/歧义，validate 会提前抓显式键冲突）。"""
    m, coll = {}, set()

    def put(k, e):
        kl = str(k).strip().casefold()
        if not kl:
            return
        if kl in m and m[kl] is not e:
            coll.add(kl)
        else:
            m[kl] = e

    for e in entries:
        if not isinstance(e, dict):
            continue
        put(e.get("key") or derive_key(e), e)
        for a in (e.get("aliases") or []):
            put(a, e)
        put(str(e.get("id", "")), e)
    for k in coll:
        m.pop(k, None)
    return m


def _split_keys(group):
    for raw in re.split(r"[;；,，]", group):
        k = raw.strip().lstrip("@").strip()
        if k:
            yield k


def compile_report(text, entries):
    """把草稿的 [@key] 编译为 [N] 并打印参考文献。
    返回 (成品文本, delivery_entries, 未引用原始 id 列表)。

    契约：草稿只写 [@引用键]，禁止手写数字引用（发现即报错——数字只能由本函数
    铸造）；草稿在目标位置放一个空的 `## 参考文献` 节，其后可跟附录（保留并同
    步编译）；代码栅栏内不编译。"""
    by_id = entries_by_id(entries)
    key_map = build_key_map(entries)
    body, level, refs, tail = split_refs(text)
    lvl = level or "##"

    for seg, segname in ((body, "正文"), (tail, "尾部")):
        lines = seg.split("\n")
        mask = _fence_mask(lines)
        for i, line in enumerate(lines):
            if not mask[i]:
                m = CITE.search(line)
                if m:
                    raise SystemExit(f"草稿{segname}含手写数字引用 {m.group(0)}——草稿只写 [@引用键]，数字由 compile 铸造")

    order, seen, unknown = [], set(), []

    def scan(seg):
        lines = seg.split("\n")
        mask = _fence_mask(lines)
        for i, line in enumerate(lines):
            if mask[i]:
                continue
            for m in CITEKEY.finditer(line):
                for k in _split_keys(m.group(1)):
                    e = key_map.get(k.casefold())
                    if e is None:
                        unknown.append(k)
                        continue
                    eid = int(e["id"])
                    if eid not in seen:
                        seen.add(eid)
                        order.append(e)

    scan(body)
    scan(tail)
    if unknown:
        raise SystemExit("未知/歧义引用键：" + ", ".join(sorted(set(unknown))) +
                         "——键必须来自台账（key/alias/id，大小写不敏感）；台账外的论文先回 scout 入账")
    if not order:
        raise SystemExit("草稿无 [@key] 引用——点名必引用")
    num = {int(e["id"]): i + 1 for i, e in enumerate(order)}

    def repl(m):
        nums, out_seen = [], set()
        for k in _split_keys(m.group(1)):
            n = num[int(key_map[k.casefold()]["id"])]
            if n not in out_seen:
                out_seen.add(n)
                nums.append(str(n))
        return "[" + ", ".join(nums) + "]"

    def sub_seg(seg):
        lines = seg.split("\n")
        mask = _fence_mask(lines)
        return "\n".join(line if mask[i] else CITEKEY.sub(repl, line)
                         for i, line in enumerate(lines))

    new_body = sub_seg(body)
    new_tail = sub_seg(tail) if tail else ""
    delivery = [dict(e, id=num[int(e["id"])]) for e in order]
    prose_keep = [ln for ln in (refs or "").split("\n")
                  if ln.strip() and not re.match(r"^\s*\[\d{1,3}\]", ln)]
    out = new_body if new_body.endswith("\n") else new_body + "\n"
    out += "\n" + f"{lvl} 参考文献\n\n" + "\n".join(format_entry(e) for e in delivery) + "\n"
    if prose_keep:
        out += "\n" + "\n".join(prose_keep) + "\n"
    if new_tail.strip():
        out += "\n" + new_tail.lstrip("\n")
    uncited = sorted(set(by_id) - seen)
    return out, delivery, uncited


# ---------------- csv ----------------

BASE_FIELDS = ("id", "first_author", "authors", "year", "title", "venue", "verify_status", "role", "note")


def render_csv_rows(entries):
    crit_keys = sorted({k for e in entries for k in (e.get("criteria") or {})})
    header = list(BASE_FIELDS) + crit_keys
    rows = [header]
    for e in sorted(entries, key=lambda x: int(x.get("id", 0))):
        crit = e.get("criteria") or {}
        rows.append([str(e.get(k, "")) for k in BASE_FIELDS] + [str(crit.get(k, "")) for k in crit_keys])
    return rows


# ---------------- commands ----------------

def cmd_validate(args):
    fails, warns = validate_entries(load_ledger(args.ledger))
    for w in warns:
        print(f"[WARN] {w}")
    for x in fails:
        print(f"[FAIL] {x}")
    print(f"summary: FAIL {len(fails)} / WARN {len(warns)}")
    return 1 if fails else 0


def cmd_print_refs(args):
    report = io.open(args.report, encoding="utf-8").read() if args.report else None
    lines, uncited = render_refs(load_ledger(args.ledger), report)
    print("\n".join(lines))
    if uncited:
        sys.stderr.write(f"[WARN] 台账条目未被正文引用：{uncited}——回正文补引用，或移入不编号的“扩展阅读”\n")
    return 0


def cmd_compile(args):
    text = io.open(args.report, encoding="utf-8").read()
    entries = load_ledger(args.ledger)
    out_text, delivery, uncited = compile_report(text, entries)
    out = args.output or (args.report + ".final.md")
    io.open(out, "w", encoding="utf-8").write(out_text)
    ledger_out = args.ledger + ".delivery.json"
    io.open(ledger_out, "w", encoding="utf-8").write(
        json.dumps({"entries": delivery}, ensure_ascii=False, indent=2) + "\n")
    print(f"编译完成：{out}（配套台账 {ledger_out}）")
    for e in delivery:
        print(f"  [{e['id']}] ← [@{e.get('key') or derive_key(e)}]")
    if uncited:
        sys.stderr.write(f"[WARN] 台账条目未被草稿引用：{uncited}——回草稿补引用，或移入不编号的“扩展阅读”\n")
    print("下一步：python3 scripts/check_report.py 成品.md --citation-ledger " + ledger_out)
    return 0


def cmd_renumber(args):
    text = io.open(args.report, encoding="utf-8").read()
    entries = load_ledger(args.ledger)
    new_text, delivery, uncited = renumber_report(text, entries)
    out = args.output or (args.report + ".delivery.md")
    io.open(out, "w", encoding="utf-8").write(new_text)
    ledger_out = args.ledger + ".delivery.json"
    io.open(ledger_out, "w", encoding="utf-8").write(
        json.dumps({"entries": delivery}, ensure_ascii=False, indent=2) + "\n")
    print(f"重排完成：{out}（配套台账 {ledger_out}）")
    if uncited:
        sys.stderr.write(f"[WARN] 未被引用、未进入交付参考文献的台账条目：{uncited}\n")
    print("提示：交付前对重排后文件重跑 check_report.py --citation-ledger（用 .delivery.json）")
    return 0


def cmd_csv(args):
    rows = render_csv_rows(load_ledger(args.ledger))
    with io.open(args.output, "w", encoding="utf-8-sig", newline="") as fh:
        _csv.writer(fh).writerows(rows)
    print(f"已生成 {args.output}（{len(rows) - 1} 条）")
    return 0


# ---------------- selftest ----------------

GOOD_LEDGER = {"entries": [
    {"id": 1, "first_author": "Roth", "authors": "Roth K, et al.", "year": "2022",
     "title": "Towards Total Recall in Industrial Anomaly Detection", "venue": "CVPR",
     "verify_status": "VERIFIED", "aliases": ["PatchCore"], "criteria": {"直接相关": True}},
    {"id": 2, "first_author": "Lin", "authors": "Lin J, Wang Q", "year": "2025",
     "title": "D3Lite-MES: Lightweight Defect Detection, with Deployment", "venue": "IEEE TII",
     "verify_status": "MINOR", "aliases": ["D3Lite-MES", "D3Lite"]},
    {"id": 3, "first_author": "Batzner", "authors": "Batzner K, et al.", "year": "2024",
     "title": "EfficientAD: Accurate Visual Anomaly Detection", "venue": "WACV",
     "verify_status": "VERIFIED", "aliases": ["EfficientAD"]},
]}

BAD_LEDGER = {"entries": [
    {"id": 1, "authors": "A", "title": "T1", "venue": "V", "year": "2020", "verify_status": "VERIFIED"},
    {"id": 1, "authors": "B", "title": "T2", "venue": "V", "year": "2021", "verify_status": "UNVERIFIABLE"},
]}

RENUM_REPORT = """# 综述
乙方案 [3] 更快；两类证据 [1, 3] 一致，而 [1] 的口径不同。

## 参考文献

[1] Roth K, et al., “Towards Total Recall in Industrial Anomaly Detection,” CVPR, 2022.
[3] Batzner K, et al., “EfficientAD: Accurate Visual Anomaly Detection,” WACV, 2024.
"""

RENUM_TAIL_REPORT = """# 综述
乙方案 [3] 更快，甲方案 [1] 更稳。

## 参考文献

[1] Roth K, et al., “Towards Total Recall in Industrial Anomaly Detection,” CVPR, 2022.
[3] Batzner K, et al., “EfficientAD: Accurate Visual Anomaly Detection,” WACV, 2024.

## 附录 A：补充对比

附录再次引用 [1] 的实验设置。
"""


COMPILE_DRAFT = '''# 综述
记忆库范式由 [@PatchCore] 确立；轻量化证据 [@D3Lite-MES; @EfficientAD] 相互一致，并与 [@patchcore] 的结论呼应。

```python
x = ledger["[@NotAKey]"]  # 栅栏内不编译
```

## 参考文献

## 附录 A

附录补充 [@EfficientAD] 的实现细节。
'''


def selftest():
    ok = True

    def expect(cond, label):
        nonlocal ok
        print(("PASS  " if cond else "FAIL  ") + label)
        ok = ok and cond

    out, delivery, uncited = compile_report(COMPILE_DRAFT, GOOD_LEDGER["entries"])
    line1 = out.splitlines()[1]
    expect("[1] 确立" in line1.replace("由 [1]", "[1] 确立") or "由 [1] 确立" in line1, "compile：[@PatchCore] → [1]（首现铸号）")
    expect("[2, 3]" in line1, "compile：多引 [@A; @B] → [2, 3]")
    expect("与 [1] 的结论呼应" in line1, "compile：键大小写不敏感（[@patchcore] → [1]）")
    expect('x = ledger["[@NotAKey]"]' in out, "compile：代码栅栏内的键原样保留")
    expect("附录补充 [3] 的实现细节" in out, "compile：附录（参考文献节之后）同步编译且保留")
    expect(out.index("## 参考文献") < out.index("## 附录"), "compile：参考文献填在占位节位置，附录在其后")
    expect("[1] Roth" in out and "[2] Lin" in out and "[3] Batzner" in out, "compile：参考文献按首现新序由台账打印")
    expect(delivery[0]["id"] == 1 and delivery[0]["first_author"] == "Roth", "compile：交付台账（.delivery.json 内容）同步铸号")
    try:
        compile_report("草稿引用 [@Ghost2020]。\n", GOOD_LEDGER["entries"])
        expect(False, "compile：未知键必须硬报错")
    except SystemExit as exc:
        expect("Ghost2020" in str(exc), "compile：未知键硬报错并点名（不静默错绑）")
    try:
        compile_report("草稿手写 [2] 编号。[@PatchCore]\n", GOOD_LEDGER["entries"])
        expect(False, "compile：草稿手写数字引用必须硬报错")
    except SystemExit as exc:
        expect("手写数字引用" in str(exc), "compile：草稿禁止手写数字引用（数字只能由编译铸造）")

    fails, warns = validate_entries(GOOD_LEDGER["entries"])
    expect(not fails, "validate：合法台账零 FAIL")
    fails, _ = validate_entries(BAD_LEDGER["entries"])
    expect(any("重复" in x for x in fails), "validate：id 重复被抓")
    expect(any("UNVERIFIABLE" in x for x in fails), "validate：UNVERIFIABLE 不得入账被抓")

    lines, uncited = render_refs(GOOD_LEDGER["entries"], RENUM_REPORT)
    expect(len(lines) == 2 and lines[0].startswith("[1] Roth"), "print-refs：只打印正文引用的条目")
    expect(uncited == [2], "print-refs：未引用条目 [2] 被上报")

    unv = [dict(GOOD_LEDGER["entries"][0]), dict(GOOD_LEDGER["entries"][2], verify_status="UNVERIFIED")]
    fails, _ = validate_entries(unv)
    expect(not fails, "validate：UNVERIFIED（字段未核验）允许入账")
    lines2, _ = render_refs(unv)
    expect(lines2[0].endswith(".") and lines2[1].endswith("（未核验）"), "print-refs：未核验条目自动带（未核验）标注，已核验条目干净")

    new_text, delivery, uncited = renumber_report(RENUM_REPORT, GOOD_LEDGER["entries"])
    line2 = new_text.splitlines()[1]
    expect(line2.startswith("乙方案 [1]"), "renumber：首现 [3]→[1]")
    expect("[2, 1]" in line2, "renumber：多引 [1, 3]→[2, 1] 原子改写")
    expect("[1] Batzner" in new_text and "[2] Roth" in new_text, "renumber：参考文献由台账按新序打印")
    expect(delivery[0]["id"] == 1 and delivery[0]["first_author"] == "Batzner", "renumber：交付台账同步重排")
    expect(uncited == [2], "renumber：未引用条目不进交付参考文献并上报")

    new_text2, _, _ = renumber_report(RENUM_TAIL_REPORT, GOOD_LEDGER["entries"])
    expect("## 附录 A：补充对比" in new_text2, "renumber：参考文献节后的附录被保留，不吞尾部")
    expect("附录再次引用 [2] 的实验设置" in new_text2, "renumber：附录内引用同步重排（[1]→[2]）")
    expect(new_text2.index("## 参考文献") < new_text2.index("## 附录"), "renumber：参考文献节在附录之前")

    fence_report = (
        "# 综述\n正文引用 [3]。\n```python\nd = feats[3]  # 代码下标不是引用\n```\n"
        "#### 参考文献\n\n[3] Batzner K, et al., “EfficientAD: Accurate Visual Anomaly Detection,” WACV, 2024.\n\n"
        "（注：以上文献均经存在性核验。）\n"
    )
    new_text3, _, _ = renumber_report(fence_report, GOOD_LEDGER["entries"])
    expect("feats[3]" in new_text3, "renumber：代码栅栏内的 [n] 原样保留，不被改写")
    expect("正文引用 [1]" in new_text3, "renumber：栅栏外正文正常重排（[3]→[1]）")
    expect("（注：以上文献均经存在性核验。）" in new_text3, "renumber：参考文献区内的说明散文保留，不被重印覆盖")
    expect("#### 参考文献" in new_text3, "renumber：#### 四级参考文献标题被识别并保留级别")

    try:
        entries_by_id([{"id": 1, "title": "A"}, {"id": 1, "title": "B"}])
        expect(False, "entries_by_id：重复 id 必须拒绝")
    except SystemExit:
        expect(True, "entries_by_id：重复 id 拒绝执行（不再静默 last-wins 指错论文）")

    rows = render_csv_rows(GOOD_LEDGER["entries"])
    expect(rows[0][:2] == ["id", "first_author"] and "直接相关" in rows[0], "csv：表头含分级布尔字段")
    buf = io.StringIO()
    _csv.writer(buf).writerows(rows)
    expect('"D3Lite-MES: Lightweight Defect Detection, with Deployment"' in buf.getvalue(),
           "csv：含逗号题名自动加引号（消灭串行）")

    print("SELFTEST " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


# ---------------- driver ----------------

def main(argv=None):
    ap = argparse.ArgumentParser(description="引用编号单一事实源（台账）工具——编号铸一次，此后只抄只打印")
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    for name, fn in (("compile", cmd_compile), ("validate", cmd_validate), ("print-refs", cmd_print_refs),
                     ("renumber", cmd_renumber), ("csv", cmd_csv)):
        p = sub.add_parser(name)
        p.add_argument("--ledger", required=True, help="citation_ledger.json 路径")
        if name in ("compile", "print-refs", "renumber"):
            p.add_argument("--report", required=(name in ("compile", "renumber")), help="草稿/报告 markdown 路径")
        if name in ("compile", "renumber", "csv"):
            p.add_argument("--output", required=(name == "csv"), help="输出文件路径")
        p.set_defaults(fn=fn)
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    if not getattr(args, "cmd", None):
        ap.error("缺少子命令（validate / print-refs / renumber / csv）或 --selftest")
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
