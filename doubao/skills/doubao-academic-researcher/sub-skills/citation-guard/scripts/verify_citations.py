#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_citations.py v4.4 — citation-guard 通道 1 的确定性脚本实现（零第三方依赖）。

用法:
  python3 verify_citations.py citations_input.json [-o verification_ledger.md]
  python3 verify_citations.py --probe        # 双类连通自检: 路径类(works/{doi}) + 查询类(query.bibliographic)
  python3 verify_citations.py --selftest     # 离线逻辑自检
  python3 verify_citations.py --emit-urls citations_input.json          # 混合模式第一步: 输出 URL 清单
  python3 verify_citations.py --from-dir responses/ citations_input.json [-o ledger.md]
                                             # 混合模式第二步: 消费网页工具保存的 JSON, 离线完成匹配与台账

混合模式（本环境已知问题的对策）: 若 --probe 显示路径类可达而查询类失败（bash 出网层剥离/破坏查询串），
用 --emit-urls 生成 URL 清单，由 agent 用网页阅读工具逐条访问，把每条返回的 JSON 原样保存为
responses/<id>.json，再用 --from-dir 完成确定性匹配、台账与报数——匹配逻辑与在线模式完全一致。

输入 JSON: [{"id","title","first_author","journal"?,"doi"?,"year"?,"volume"?,"issue"?,"pages"?}, ...]
规则: 双重误匹配防御(标题相似度>=0.90 或 副标题包含 + 第一作者姓氏)；DOI 直查张冠李戴检测；
给定字段逐项比对；页跨度<=3 或 type 非 journal-article 时告警"疑似简报/评论/更正"。
"""
import json, os, re, sys, time, unicodedata, difflib
import urllib.request, urllib.parse

API = "https://api.crossref.org/works"
UA = {"User-Agent": "doubao-academic-researcher-citation-guard/4.4 (mailto:skill-maintainer@example.com)"}
TODAY = time.strftime("%Y-%m-%d")
FIELD_ORDER = ["作者", "题目", "期刊", "文献类型", "卷", "期", "页码/文章号", "DOI", "正式刊出", "在线发表", "被引数(Crossref)"]
KNOWN = ("Impact of marginal and intergenerational effects on carbon emissions from household energy consumption in China", "Hu", "10.1016/j.jclepro.2020.123022")

ALIASES = {"first_author": ["first_author", "first_author_last", "first_author_surname", "surname", "last_name", "lastname", "author", "firstauthor"],
           "journal": ["journal", "venue", "journal_name", "container_title"],
           "title": ["title", "paper_title"],
           "doi": ["doi"], "pages": ["pages", "page"], "volume": ["volume", "vol"], "issue": ["issue"], "year": ["year"]}


def normalize_item(raw, idx):
    """宽容读取 + 响亮校验: 常见别名键自动映射(附提示), 必填缺失硬报错(不发网络请求)。"""
    low = {str(k).lower(): v for k, v in raw.items()}
    out, notes = {"id": str(raw.get("id", idx + 1))}, []
    for canon, alist in ALIASES.items():
        for a in alist:
            if a in low and str(low[a]).strip():
                out[canon] = low[a]
                if a != canon:
                    notes.append("字段名 '%s' 已自动映射为 '%s'" % (a, canon))
                break
    errs = []
    if not out.get("title"):
        errs.append("缺少 title")
    if not out.get("doi") and not out.get("first_author"):
        errs.append("缺少 first_author（无 doi 时必填；规范键名为 first_author）")
    return out, notes, errs



def fetch(url, retries=2):
    for i in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=25) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            if i == retries:
                return {"__error__": str(e)}
            time.sleep(2 * (i + 1))


def norm(t):
    t = unicodedata.normalize("NFKD", t or "").casefold()
    t = re.sub(r"[‐‑‒–—―-]", " ", t)
    t = re.sub(r"[^0-9a-z\u4e00-\u9fff ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def title_sim(a, b):
    na, nb = norm(a), norm(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    return difflib.SequenceMatcher(None, na, nb).ratio()


def author_match(surname, authors):
    if not surname:
        return False
    toks = norm(surname).split()
    cands = set()
    for a in authors or []:
        for k in ("family", "given", "name"):
            if a.get(k):
                cands.update(norm(a[k]).split())
    return any(t in cands for t in toks)


def get_fields(msg):
    def dp(key):
        try:
            return "-".join(str(x) for x in msg[key]["date-parts"][0])
        except Exception:
            return ""
    return {
        "题目": (msg.get("title") or [""])[0],
        "作者": "; ".join((("%s %s" % (a.get("given", ""), a.get("family", ""))).strip() or a.get("name", ""))
                          for a in msg.get("author", [])),
        "期刊": (msg.get("container-title") or [""])[0],
        "文献类型": msg.get("type", ""),
        "卷": msg.get("volume", ""),
        "期": msg.get("issue", ""),
        "页码/文章号": msg.get("page", "") or msg.get("article-number", ""),
        "DOI": msg.get("DOI", ""),
        "正式刊出": dp("published-print") or dp("published") or dp("issued"),
        "在线发表": dp("published-online"),
        "被引数(Crossref)": str(msg.get("is-referenced-by-count", "")),
    }


def build_query_url(item):
    q = item.get("title", "") + " " + item.get("first_author", "")
    if item.get("journal"):
        q += " " + item["journal"]
    return "%s?query.bibliographic=%s&rows=5" % (API, urllib.parse.quote_plus(q))


def resolve(item, preloaded=None):
    """(status, fields, src_url, note)  status: VERIFIED/NOT_FOUND/DOI_MISMATCH/ERROR/GARBAGE"""
    doi = (item.get("doi") or "").strip()
    title = item.get("title", "")
    if doi and preloaded is None:
        url = "%s/%s" % (API, urllib.parse.quote(doi))
        data = fetch(url)
        if "__error__" in data:
            return "ERROR", {}, url, data["__error__"]
        msg = data.get("message", {})
        r = title_sim(title, (msg.get("title") or [""])[0])
        if title and r < 0.90:
            return "DOI_MISMATCH", get_fields(msg), url, "给定DOI解析到另一篇文献(标题相似度%.2f)——张冠李戴" % r
        return "VERIFIED", get_fields(msg), url, "DOI直查, 标题相似度%.2f" % r
    url = build_query_url(item)
    data = preloaded if preloaded is not None else fetch(url)
    if "__error__" in data:
        return "ERROR", {}, url, data["__error__"]
    best = None
    for it in data.get("message", {}).get("items", []):
        ct = (it.get("title") or [""])[0]
        r = title_sim(title, ct)
        na, nc = norm(title), norm(ct)
        contained = (len(min(na, nc, key=len).split()) >= 6) and (na in nc or nc in na)
        a_ok = author_match(item.get("first_author", ""), it.get("author"))
        if best is None or r > best[0]:
            best = (r, a_ok, ct)
        if a_ok and (r >= 0.90 or contained):
            how = "相似度%.2f" % r + ("" if r >= 0.90 else "+包含关系(副标题差异)")
            return "VERIFIED", get_fields(it), url, "反查命中: 标题%s + 第一作者姓氏匹配" % how
    if best and best[0] < 0.25:
        return "GARBAGE", {}, url, ("返回候选与查询完全无关(最高相似度%.2f: '%s')——查询串疑似被网络层剥离/破坏。"
                                    "运行 --probe 复核；查询类测试失败则改用 --emit-urls + --from-dir 混合模式。") % (best[0], best[2][:50])
    diag = ""
    if best:
        if best[0] >= 0.90 and not best[1]:
            diag = "；最佳候选: '%s'(相似度%.2f)——标题近乎精确命中但第一作者姓氏未匹配: 最常见原因是输入 first_author 值与论文作者姓不符或拼写有误（当前输入值: '%s'），修正后重跑" % (best[2][:70], best[0], item.get("first_author", "<空>"))
        else:
            diag = "；最佳候选: '%s'(相似度%.2f, 作者匹配=%s)——相似度0.5~0.9多为副标题/翻译差异, 修正输入标题后重跑" % (best[2][:70], best[0], "是" if best[1] else "否")
    return "NOT_FOUND", {}, url, "前5条无满足双重防御的命中；中文文献属正常情况，走通道2网页核验" + diag


def diff_given(item, fields):
    m = {"year": "正式刊出", "volume": "卷", "issue": "期", "pages": "页码/文章号", "doi": "DOI", "journal": "期刊"}
    bad = []
    for k, f in m.items():
        gv = str(item.get(k, "") or "").strip()
        rv = str(fields.get(f, "") or "").strip()
        if gv and rv:
            a, b = norm(gv), norm(rv)
            ok = (a == b) or (k == "year" and rv.startswith(gv)) or (a and b and (a in b or b in a))
            if not ok:
                bad.append("%s: 给定'%s' vs 核验'%s'" % (f, gv, rv))
    return bad


def page_span(p):
    m = re.match(r"^\s*(\d+)\s*[-–]\s*(\d+)\s*$", p or "")
    if not m:
        return None
    return int(m.group(2)) - int(m.group(1)) + 1


def run(items, out_md, from_dir=None):
    rows, results, alerts = [], [], []
    n_ok = n_nf = n_mm = n_err = n_gb = f_ok = f_un = 0
    n_inerr = 0
    for i, raw_item in enumerate(items):
        item, in_notes, in_errs = normalize_item(raw_item, i)
        pid = item["id"]
        for nt in in_notes:
            alerts.append("[%s] 输入提示: %s" % (pid, nt))
        if in_errs:
            n_inerr += 1
            alerts.append("[%s] 输入校验失败: %s（未发起网络请求）" % (pid, "；".join(in_errs)))
            rows.append(("%s (%s)" % (pid, (item.get("title", "") or "")[:40]), "全部字段", "—", "未核验（输入校验失败）", "—"))
            f_un += 1
            results.append({"id": pid, "status": "INPUT_ERROR", "note": "；".join(in_errs), "source_url": "", "fields": {}})
            continue
        preloaded = None
        if from_dir is not None:
            fp = os.path.join(from_dir, "%s.json" % pid)
            if os.path.exists(fp):
                try:
                    preloaded = json.load(open(fp, encoding="utf-8"))
                except Exception as e:
                    preloaded = {"__error__": "响应文件解析失败: %s" % e}
            else:
                preloaded = {"__error__": "缺少响应文件 %s" % fp}
        status, fields, url, note = resolve(item, preloaded)
        results.append({"id": pid, "status": status, "note": note, "source_url": url, "fields": fields})
        label = "%s (%s)" % (pid, (item.get("title", "") or "")[:40])
        if status == "VERIFIED":
            n_ok += 1
            for f in FIELD_ORDER:
                v = fields.get(f, "")
                if v:
                    rows.append((label, f, v, "已核验（crossref）", url)); f_ok += 1
                else:
                    extra = "（Crossref未返回；期号缺失属正常，不构造）" if f == "期" else ""
                    rows.append((label, f, "—" + extra, "未核验", "—")); f_un += 1
            sp = page_span(fields.get("页码/文章号", ""))
            if (sp is not None and sp <= 3) or (fields.get("文献类型") and fields["文献类型"] != "journal-article"):
                alerts.append("[%s] 疑似简报/评论/更正等非研究论文（页跨度=%s, type=%s）——同族研究正文可能是另一个姊妹 DOI；核对任务的文献类型要求后再入选" % (pid, sp, fields.get("文献类型", "?")))
            bad = diff_given(item, fields)
            if bad:
                alerts.append("[%s] 给定题录与核验值不一致 → %s" % (pid, "；".join(bad)))
        elif status == "DOI_MISMATCH":
            n_mm += 1
            alerts.append("[%s] %s；该DOI实际指向: %s（%s）" % (pid, note, fields.get("题目", ""), fields.get("期刊", "")))
            rows.append((label, "全部字段", "—", "未核验（DOI张冠李戴，须重查）", url)); f_un += 1
        elif status == "GARBAGE":
            n_gb += 1
            alerts.append("[%s] %s" % (pid, note))
            rows.append((label, "全部字段", "—", "未核验（响应与查询无关）", url)); f_un += 1
        elif status == "NOT_FOUND":
            n_nf += 1
            rows.append((label, "全部字段", "—", "未核验（Crossref未命中，走通道2）", url)); f_un += 1
        else:
            n_err += 1
            rows.append((label, "全部字段", "—", "未核验（错误: %s）" % note, url)); f_un += 1
        if from_dir is None and i < len(items) - 1:
            time.sleep(1)

    md = ["## 【题录核验台账】（脚本生成部分：Crossref 通道）", "",
          "生成: verify_citations.py v4.4 · %s · 输入 %d 篇%s" % (TODAY, len(items), "（混合模式 --from-dir）" if from_dir else ""), "",
          "| 文献 | 字段 | 值 | 溯源 | 来源URL | 核验时间 |", "|---|---|---|---|---|---|"]
    for label, f, v, prov, url in rows:
        md.append("| %s | %s | %s | %s | %s | %s |" % (label, f, str(v).replace("|", "/"), prov, url, TODAY))
    if alerts:
        md += ["", "### 告警（必须逐条消解后才能出稿）", ""] + ["- " + a for a in alerts]
    md += ["", "**本台账仅覆盖 Crossref 通道。期刊等级、中文文献题录须按 citation-guard 通道 2 手工核验后追加台账行（标注 已核验（官方页面）/ 二手核验——等级行不得沿用本表的\u201c已核验（crossref）\u201d标签）。**"]
    open(out_md, "w", encoding="utf-8").write("\n".join(md) + "\n")
    open(out_md.rsplit(".", 1)[0] + ".json", "w", encoding="utf-8").write(json.dumps(results, ensure_ascii=False, indent=1))

    print("=== 分档报数（核验声明的数字直接抄这里，禁止另行估计）===")
    print("共 %d 篇：VERIFIED %d；NOT_FOUND %d（走通道2）；GARBAGE %d（响应无关）；DOI_MISMATCH %d；ERROR %d；INPUT_ERROR %d" % (len(items), n_ok, n_nf, n_gb, n_mm, n_err, n_inerr))
    if n_inerr:
        print("!! 输入校验失败 %d 篇：修正 citations_input.json 的键名/必填字段后重跑（规范键名: id/title/first_author, 可选 journal/doi/year/volume/issue/pages）。" % n_inerr)
    print("台账字段行：已核验（crossref）%d 行；未核验 %d 行" % (f_ok, f_un))
    if alerts:
        print("告警 %d 条——见台账末尾，逐条消解后才能出稿" % len(alerts))
    if len(items) >= 3 and (n_gb == len(items) or n_nf + n_gb == len(items)):
        print("!! 警告: 全部条目未命中。若 --probe 的查询类测试失败=网络层问题→用 --emit-urls + --from-dir 混合模式；"
              "若 probe 双类均通过→检查输入标题（翻译件/截断），按台账'最佳候选'诊断修正后重跑。不要退回纯手工。")
    print("台账文件: %s" % out_md)
    print("提醒: 期刊等级与中文文献不在脚本覆盖范围，须走通道2并追加台账行；清单篇数必须 = 输入篇数（篇级完备性闸门）。")
    return results


def emit_urls(items, out="crossref_urls.tsv"):
    lines = []
    for i, item in enumerate(items):
        pid = str(item.get("id", i + 1))
        doi = (item.get("doi") or "").strip()
        url = ("%s/%s" % (API, urllib.parse.quote(doi))) if doi else build_query_url(item)
        lines.append("%s\t%s" % (pid, url))
    open(out, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("已写出 %d 条 URL 到 %s" % (len(lines), out))
    print("下一步: 用网页阅读工具逐条访问，把每条返回的 JSON 原样保存为 responses/<id>.json，然后运行:")
    print("  python3 verify_citations.py --from-dir responses/ <input.json> -o verification_ledger.md")


CANNED = {"message": {"title": [KNOWN[0]], "type": "journal-article",
                      "author": [{"given": "Zhen", "family": "Hu"}, {"given": "Mei", "family": "Wang"},
                                 {"given": "Zhe", "family": "Cheng"}, {"given": "Zhenshan", "family": "Yang"}],
                      "container-title": ["Journal of Cleaner Production"], "volume": "273",
                      "page": "123022", "DOI": KNOWN[2],
                      "published-print": {"date-parts": [[2020, 11, 10]]},
                      "published-online": {"date-parts": [[2020, 7, 16]]},
                      "is-referenced-by-count": 120}}


def selftest():
    import tempfile
    f = get_fields(CANNED["message"])
    assert f["卷"] == "273" and f["文献类型"] == "journal-article"
    assert author_match("Hu", CANNED["message"]["author"]) and not author_match("Zhang", CANNED["message"]["author"])
    # 副标题包含
    na = norm(KNOWN[0]); nc = norm(KNOWN[0] + ": evidence from CFPS panel data")
    assert na in nc and len(na.split()) >= 6
    # GARBAGE 签名: 无关候选
    garbage = {"message": {"items": [{"title": ["Totally unrelated cement manufacturing study"], "author": [{"family": "Smith"}]}]}}
    st, _, _, note = resolve({"id": "x", "title": KNOWN[0], "first_author": "Hu"}, preloaded=garbage)
    assert st == "GARBAGE" and "剥离" in note, (st, note)
    # 简报守卫: 页跨度2
    brief = json.loads(json.dumps(CANNED)); brief["message"]["page"] = "1228-1229"; brief["message"]["type"] = "journal-article"
    d = tempfile.mkdtemp()
    json.dump({"message": {"items": [brief["message"]]}}, open(os.path.join(d, "b1.json"), "w"))
    res = run([{"id": "b1", "title": KNOWN[0], "first_author": "Hu"}], os.path.join(d, "l.md"), from_dir=d)
    led = open(os.path.join(d, "l.md")).read()
    assert res[0]["status"] == "VERIFIED" and "疑似简报" in led, led[-300:]
    # from_dir 缺文件
    res2 = run([{"id": "missing", "title": "t x y z a b c", "first_author": "Q"}], os.path.join(d, "l2.md"), from_dir=d)
    assert res2[0]["status"] == "ERROR"
    # 别名映射: first_author_last → first_author（Test R 实测事故的回归用例）
    it, notes, errs = normalize_item({"id": "a", "title": KNOWN[0], "first_author_last": "Hu"}, 0)
    assert it.get("first_author") == "Hu" and not errs and any("自动映射" in n for n in notes), (it, notes, errs)
    st, f2, _, _ = resolve(it, preloaded={"message": {"items": [CANNED["message"]]}})
    assert st == "VERIFIED"
    # 必填缺失 → 硬校验
    _, _, errs2 = normalize_item({"id": "b", "title": "x y z"}, 1)
    assert errs2, errs2
    # 高相似度+作者不匹配 → 新诊断指向 first_author
    st3, _, _, note3 = resolve({"id": "c", "title": KNOWN[0], "first_author": "Wrong"}, preloaded={"message": {"items": [CANNED["message"]]}})
    assert st3 == "NOT_FOUND" and "first_author" in note3, note3
    print("selftest OK: 字段提取/作者匹配/包含/GARBAGE签名/简报守卫/from_dir/别名映射/输入校验/作者诊断 全部通过")


def probe():
    u1 = "%s/%s" % (API, KNOWN[2])
    d1 = fetch(u1)
    ok1 = "__error__" not in d1 and title_sim(KNOWN[0], (d1.get("message", {}).get("title") or [""])[0]) > 0.9
    print("PROBE-路径类(works/{doi}): %s" % ("OK" if ok1 else "FAIL %s" % d1.get("__error__", "标题不符")))
    u2 = build_query_url({"title": KNOWN[0], "first_author": KNOWN[1]})
    d2 = fetch(u2)
    ok2 = False
    if "__error__" not in d2:
        for it in d2.get("message", {}).get("items", []):
            if title_sim(KNOWN[0], (it.get("title") or [""])[0]) >= 0.9:
                ok2 = True; break
    print("PROBE-查询类(query.bibliographic): %s" % ("OK" if ok2 else "FAIL"))
    if ok1 and not ok2:
        print(">> 诊断: 路径类可达但查询类失败——本环境网络层疑似剥离/破坏查询串。")
        print(">> 对策: 使用混合模式 --emit-urls 生成清单，用网页阅读工具取回 JSON 后 --from-dir 完成核验。")
    sys.exit(0 if (ok1 and ok2) else 1)


if __name__ == "__main__":
    argv = sys.argv[1:]
    if "--selftest" in argv:
        selftest()
    elif "--probe" in argv:
        probe()
    elif "--emit-urls" in argv:
        args = [a for a in argv if not a.startswith("-")]
        emit_urls(json.load(open(args[0], encoding="utf-8")))
    else:
        from_dir = None
        if "--from-dir" in argv:
            from_dir = argv[argv.index("--from-dir") + 1]
        args = [a for a in argv if not a.startswith("-") and a != from_dir]
        if not args:
            print(__doc__); sys.exit(1)
        out = "verification_ledger.md"
        if "-o" in argv:
            out = argv[argv.index("-o") + 1]
        run(json.load(open(args[0], encoding="utf-8")), out, from_dir=from_dir)
