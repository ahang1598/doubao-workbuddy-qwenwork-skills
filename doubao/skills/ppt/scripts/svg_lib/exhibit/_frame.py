"""Shared page frame for strategy decks: title, subtitle, section tag, footnotes/source and page number as native XML.

Both agents use the same frame so every page has the same template, font and type sizes; the body (text columns,
KPI cards, chart box) is still hand-written XML placed between f.top and f.bottom.
"""

from __future__ import annotations

import math
import re
from html import escape

from ._palette import roles, set_default
from ._page import TABLES
from ._text import fmt, has_cjk, tw, wrap


def _c(c):
    """Slides XML accepts only rgb()/rgba() colours."""
    c = str(c)
    if c.startswith("#") and len(c) == 7:
        return "rgb(%d,%d,%d)" % tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))
    return c

W, H, X0 = 960, 540, 40
LAST_TITLE = ""
LAST_SUBTITLE = ""
LAST_LANG = "zh"   # language of the last frame() title; Exhibit(lang=None) follows it
LAST_NOTES = ""   # footnotes + source text of the last frame(): a "不可比" there forbids diff / growth marks (_semantics)


class Frame:
    def __init__(self, xml, top, bottom, palette, title=""):
        self.xml, self.top, self.bottom, self.C, self.title = xml, top, bottom, palette, title
        self.left, self.right = X0, W - X0

    note = None

    @property
    def body_w(self):
        """Chart width left of a key_takeaways rail (same as body_w(f))."""
        from ._layouts import body_w as _bw
        return _bw(self)
    foot_lines = 0
    appendix = False
    research = False
    speech = False
    subtitle = None

    def publish(self, *body, ex=None, frags=(), side=None, deck=None, page=None, cwd=None, screenshot=False,
                waive=(), who=None, layout=None, why=None, same_as_prev=None, insert=False):
        """One call per page: compose frame + body XML (+ side, e.g. points()[0]) + the exhibit (ex.to_slide at
        x=f.left, y=f.top unless already converted via frags), publish_slide it, and print ONE short line
        (ok / blocked + the fix list) instead of the whole result. who="main"/"organizer"/"builder" (multi-agent):
        refuses to overwrite a page that next handed to another agent. Returns the publish_slide result dict."""
        cwd = project_root(cwd)
        from pathlib import Path
        import json as _json
        from ..atomize_svg_to_slide._exhibit_publish import publish_slide, _deck_id
        me = who
        deck = _deck_id(deck) if deck else deck
        if page is None and deck and (getattr(self, "_kw", None) or {}).get("page") is not None:
            page = self._kw["page"]   # publish(page=) left out: the frame's page — never an unregistered extra slide
        if deck and getattr(self, "_kw", None) is not None and (getattr(self, "deck", None) != deck
                                                                 or (cwd and cwd != getattr(self, "_cwd", None))):
            # the frame was built for another (or no) deck: redraw its header so the logo / sample tag are this deck's
            from ._page import BLOCKS as _BLk
            from ._axes import PLOTS as _PLk
            from . import _layouts as _lyk
            from ._marks import SIGNAL_SINGLE_PCT as _SSPk
            kept = (list(_BLk), list(_PLk), list(_lyk.RAIL_NUMS), list(_lyk.RAIL_TEXT), list(_lyk.KPI_LINKS),
                    list(_lyk.CHART_SLOTS), list(_lyk.SHORT), list(_SSPk))
            fresh = frame(**self._kw, deck=deck, cwd=cwd)   # resets the per-page registries: keep what this page built
            (_BLk[:], _PLk[:], _lyk.RAIL_NUMS[:], _lyk.RAIL_TEXT[:], _lyk.KPI_LINKS[:], _lyk.CHART_SLOTS[:],
             _lyk.SHORT[:], _SSPk[:]) = kept
            if getattr(self, "full_bleed", False):   # contents() / chapter_nav own the whole canvas and their own header
                self.sample, self.deck, self._cwd = fresh.sample, deck, cwd
            else:
                self.xml, self.top, self.bottom, self.sample, self.deck, self._cwd = (fresh.xml, fresh.top, fresh.bottom,
                                                                                     fresh.sample, deck, cwd)
            self.research, self.speech = fresh.research, fresh.speech
        from ._page import FACTS as _F
        self._facts, _F[:] = list(_F), []   # this page's chart data; never carried over to the next page of the process
        for d_ in (_sync_dirs(cwd) if me else []):   # one task, one deck: whoever wrote SYNC/deck.txt first owns the deck ID
            dt = d_ / "deck.txt"
            if deck and page is not None and dt.exists():
                owner = (dt.read_text(encoding="utf-8").split() or [""])[0]
                if owner and owner != deck:
                    print(f"P{page} 未写入：这个任务的 deck 是 {owner}（SYNC/deck.txt），不是 {deck}——不要另建 deck；"
                          f"改用 deck={owner!r} 重新 publish（已建的多余 deck 不用管、不要删）")
                    return {"ok": False, "skipped": True, "wrong_deck": owner}
        from ..atomize_svg_to_slide._exhibit_publish import (_frozen_lock, FROZEN_MSG, _EXPORTED_MSG, SEAL_MSG, seal_broken,
                                                     delivered, edit_phase, refusal_hint)
        if page is not None and seal_broken(cwd or ".", deck):   # frozen.lock / exported deleted or edited by hand
            print(f"P{page} 未写入：{SEAL_MSG}")
            return {"ok": False, "skipped": True, "finished": True, "seal": True}
        for d_ in _sync_dirs(cwd, deck):   # the export marker survives hand edits of status.json ("unfreezing" for rework)
            if me and page is not None and (d_ / "exported").exists():
                print(f"P{page} 未写入：{refusal_hint(cwd, _EXPORTED_MSG + '（不做终审返工）。没有真问题就直接交付/return', deck)}")
                return {"ok": False, "skipped": True, "finished": True, "delivered": True}
        if page is not None and _frozen_lock(cwd or ".", page, deck) is not None:   # SYNC/frozen.lock, whatever status.json says
            print(f"P{page} 未写入：全部页已完成并冻结（SYNC/frozen.lock）——"
                  f"{refusal_hint(cwd, FROZEN_MSG + '；不做终审返工，直接 finish 交付', deck)}")
            return {"ok": False, "skipped": True, "finished": True, "frozen": True, "delivered": delivered(cwd or ".", deck)}
        editing = page is not None and edit_phase(cwd or ".", deck)   # follow-up turn after reopen: no ownership rules
        for stp in (d / "status.json" for d in _sync_dirs(cwd, deck) if (d / "status.json").exists() and not editing):
            st_ = stp.read_text(encoding="utf-8")
            try:
                frozen = _json.loads(st_).get("frozen") or []
            except ValueError:
                frozen = []
            if page is not None and int(page) in frozen:
                print(f"P{page} 未写入：全部页已完成并检查（organizer_done），{FROZEN_MSG}；不做终审返工，直接 finish 交付")
                return {"ok": False, "skipped": True, "finished": True}
            if me and page is not None and ('"finished_at"' in st_ or (me == "organizer" and '"organizer_done"' in st_)):
                fin_ = '"finished_at"' in st_
                hint_ = (refusal_hint(cwd, "", deck) if fin_ and me != "organizer" else
                         "真有错由 Main/Lead 用 finish --fix N --why …（每个任务一次）" if me != "organizer"
                         else "有问题写进 return 交给 Main")
                print(f"P{page} 未写入：{'finish 已导出 PPTX' if fin_ else '已 organizer_done'}，"
                      f"之后不再改页（不做终审返工；{hint_}）。直接交付/return")
                return {"ok": False, "skipped": True, "finished": True, **({"delivered": True} if fin_ else {})}
        for cl in (d / "claims.json" for d in _sync_dirs(cwd, deck)
                   if (d / "claims.json").exists() and not editing):  # page ownership (not in a reopened edit turn)
            c = _json.loads(cl.read_text(encoding="utf-8")).get(f"p{int(page):02d}") if page is not None else None
            who = c.get("who") if isinstance(c, dict) else c
            voided = _json.loads((cl.parent / "status.json").read_text(encoding="utf-8")).get("voided") \
                if (cl.parent / "status.json").exists() else None
            if c is None and me and page is not None and me in ((voided or {}).get(f"p{int(page):02d}") or []):
                print(f"P{page} 未写入：这页现在没人领（plan 改过页号后旧的领取已作废）。不要按旧脚本写，运行 next 领页")
                return {"ok": False, "skipped": True, "claim": None}
            if isinstance(c, dict) and c.get("state") == "reviewing" and c.get("reviewer") == me:
                import time as _tm
                if c.get("via") != "next":   # claims edited by hand to reopen a page: not a review that next handed out
                    print(f"P{page} 未写入：这页的检查不是 next --review 发的（claims 被手工改过）。不手改 claims，运行 next --review")
                    return {"ok": False, "skipped": True, "claim": "manual"}
                if _tm.time() - c.get("rev_since", _tm.time()) > 480 or _tm.time() - c.get("t", _tm.time()) > 180:
                    # quiet for 3 min (frame() / publish renew t) or 8 min in total: closed as is
                    print(f"P{page} 未写入：检查已超时（3 分钟无动作或累计 8 分钟），这页按原版结案。运行 next --review 领下一页（它会把这页记为 done）")
                    return {"ok": False, "skipped": True, "review_timeout": True}
                who = me   # the reviewer fixes this page
            if me and who == me and isinstance(c, dict):   # heartbeat: every publish attempt keeps the claim fresh
                try:
                    import fcntl as _f, time as _t
                    with open(cl.parent / "claims.lock", "w") as lk:
                        _f.flock(lk, _f.LOCK_EX)
                        allc = _json.loads(cl.read_text(encoding="utf-8"))
                        k = f"p{int(page):02d}"
                        if isinstance(allc.get(k), dict) and allc[k].get("state") in ("doing", "reviewing"):
                            allc[k]["t"] = _t.time()
                            cl.write_text(_json.dumps(allc, ensure_ascii=False, indent=1), encoding="utf-8")
                except Exception:  # noqa: BLE001
                    pass
            if me and who and who != me:
                if isinstance(c, dict) and c.get("revoked_from") == me:   # taken over after this agent went silent
                    from ..atomize_svg_to_slide._exhibit_publish import revoked_msg
                    print(revoked_msg(page, me, who))
                    return {"ok": False, "skipped": True, "claim": who, "revoked": True}
                print(f"P{page} 未写入：这页由 {who} 领取（claims.json）。不要再改这页的脚本，运行 next 领你自己的页"
                      "（只写 next 发给你的页：做页或 --review 检查的页）")
                return {"ok": False, "skipped": True, "claim": who}
        own_n = _main_page_max(cwd, deck)
        if me and me not in ("main", "lead") and page is not None and int(page) <= own_n and not editing and any(
                (d_ / "claims.json").exists() for d_ in _sync_dirs(cwd, deck)) and not (
                me == "organizer" and any((d_ / "main_gone").exists() for d_ in _sync_dirs(cwd, deck))):
            print(f"P{page} 未写入：封面/执行摘要/目录页（P1–P{own_n}）只由 Main / Lead 写——不要另做一份；回到 next")
            return {"ok": False, "skipped": True, "claim": "main"}
        from ._page import SIGNALS
        if not frags:
            SIGNALS.clear()   # signals left over from an earlier page that was never published
        from ._page import SLID as _SLIDp
        passed_ = [str(x_[0] if isinstance(x_, tuple) and x_ else x_) for x_ in list(frags) + list(body)]
        for x_ in dict.fromkeys(list(_SLIDp) + ([ex] if ex is not None else [])):
            fr_ = getattr(x_, "_frag", None)
            at_ = getattr(x_, "_at", None) if x_ is ex or (fr_ and any(fr_ in p_ for p_ in passed_)) else None
            if at_ and not getattr(self, "full_bleed", False) and (at_[0] < self.left - 8 or at_[1] < self.top - 40):
                raise ValueError(f"图区放在了 ({at_[0]:.0f}, {at_[1]:.0f})，跑出正文区（左边界 {self.left:.0f}、顶 {self.top:.0f}），"
                                 "页面会贴边/偏一侧：用 ex.to_slide(x=f.left, y=f.top)，或直接 f.publish(..., ex=ex) 不自己转换")
        unwrap = lambda b: b[0] if isinstance(b, tuple) and b and isinstance(b[0], str) else b   # (xml, y) / (xml, slots)
        if ex is not None and getattr(ex, "_slid", False):
            # ex.to_slide() already ran: never convert twice, never drop the chart. Its fragment may sit in frags,
            # in the body (positional), or nowhere (frags=[note_box] only) — then it is added here.
            own = getattr(ex, "_frag", None)
            sig = lambda s_: tuple(re.findall(r"<p\b[^>]*>(.*?)</p>", s_))   # noqa: E731  (same labels = same chart)
            passed = [str(unwrap(x)) for x in list(frags) + list(body)]
            if own is not None and any(own == p_ or own in p_ or (p_.lstrip().startswith("<slide") and sig(p_) == sig(own))
                                       for p_ in passed):
                ex = None   # passed already (frags or body, possibly converted twice): draw it once
            elif own is not None:
                frags = list(frags) + [own]   # frags=[note_box] only: the chart was silently dropped before
                if frags[:-1]:
                    print(f"P{page} 提醒：ex.to_slide() 的图没放进 frags，已自动补上（写法：frags=[frag, …] 或只传 ex=ex）")
                ex = None
            elif frags:
                ex = None
        frags = list(frags) + ([ex.to_slide(x=self.left, y=self.top)] if ex is not None else [])
        body = [unwrap(b) for b in body]
        plain = [b for b in body if isinstance(b, str) and b.strip() and not b.lstrip().startswith("<")]
        if plain:   # plain text passed as body XML would be dropped silently: refuse with the fix
            raise ValueError("f.publish 的正文收到纯文字（不是 XML），页面会是空的：文字写成块——"
                             "points(...)[0] / text_table / note_box / mixed_columns_page 的 text / dots 块；"
                             f"收到：{plain[0][:40]!r}")
        body = body + ([unwrap(side)] if side else [])
        frags = [unwrap(x) for x in frags]
        odd = [type(x).__name__ for x in frags if not isinstance(x, str)]
        if odd:   # columns() / bubbles() return value (a dict of positions) passed as a fragment
            raise ValueError(f"frags 里收到 {odd[0]}，不是页面片段：图表函数的返回值（位置 dict / list）不是 XML——"
                             "图画在 ex 上就传 f.publish(..., ex=ex)；已转换的图传 ex.to_slide(x=f.left, y=f.top) 的结果")
        frags += [b for b in body if str(b).lstrip().startswith("<slide")]   # an ex.to_slide() fragment passed as body
        body = [b for b in body if not str(b).lstrip().startswith("<slide")]
        empty_ = [x for x in frags if not re.search(r"<(?!/?(?:slide|data)\b)[a-zA-Z]", str(x))]   # an Exhibit with nothing drawn
        if empty_ and len(empty_) < len(frags):   # one panel of a multi-panel page came out blank
            SIGNALS.clear()
            msg = (f"有 {len(empty_)} 个图区是空的（Exhibit 里什么都没画）——那块会是白的。常见原因：kv_rows / text_table / "
                   "note_box 返回的是 XML，要先接住再放进 body（xml, _ = kv_rows(...); f.publish(heads, xml, frags=[...])），"
                   "不能画进 Exhibit；或这一栏的图根本没画")
            print(f"P{page} 未写入：{msg}")
            return {"ok": False, "held": [msg], "errors": [{"key": "empty_panel", "message": msg, "fix": msg}], "warnings": []}
        frags = [x for x in frags if x not in empty_]
        if not frags and not any(str(b).strip() for b in body):
            SIGNALS.clear()
            msg = "页面只有页眉、没有正文"
            fix = ("把正文传给 publish，四选一或组合：body XML 作位置参数 f.publish(xml, …)（kv_rows / text_table / 版式函数"
                   "返回的 XML 要先接住再传，例如 xml, _ = kv_rows(...)；空的 Exhibit 不算正文）、"
                   "图表 ex=、已转换的片段 frags=[…]、右栏 side=")
            print(f"P{page} 未写入：{msg}——{fix}")
            return {"ok": False, "held": [msg], "errors": [{"key": "empty_body", "message": msg, "fix": fix}],
                    "warnings": []}
        from ._autonative import swap
        frags, n_native = swap(frags)   # column / line data → editable native charts (annotations stay shapes)
        if "有标注图" in SIGNALS:   # one annotated chart carries the page; the plain panels beside it are fine
            SIGNALS[:] = [s_ for s_ in SIGNALS if s_ != "图上无标注"]
        SIGNALS[:] = [s_ for s_ in SIGNALS if s_ != "有标注图"]
        import re as _re
        page_text = _re.sub(r"<[^>]+>", " ", "".join(body) + "".join(str(f_) for f_ in frags))
        if getattr(self, "research", False) and deck and page is not None and not self.appendix:
            from ._glossary import footnote_terms, footnote_line, inhouse_jargon
            jar = inhouse_jargon(self.title + " " + page_text)
            if jar:   # coined shorthand the reader cannot decode: say what it means instead
                raise ValueError(f"页面里有圈内黑话 {jar[:4]}：读者看不懂——直接写它代表的意思（如'守正'→'稳健配置：份额与盈利已确定的龙头'，"
                                 "'卫星'→'高弹性配置：增速快但波动大'），不要用口号式标签")
            gl = footnote_line(footnote_terms(self.title + " " + page_text, cwd, deck, page, lang="zh" if has_cjk(self.title) else "en"), LAST_LANG)
            if gl and gl not in self.xml:
                self._add_glossary_line(gl)
        t_ = _re.sub(r"(?:现价|股价|收盘价|当前价|spot|current(?:\s+price)?|share\s+price|last\s+close)\s*[:：]?\s*"
                     r"(?:HK\$|US\$|\$|€|£|¥|￥)?\s*\d[\d,]*(?:\.\d+)?", "", self.title, flags=_re.I)   # the quote is context
        t_ = _re.sub(r"(\d+(?:\.\d+)?)\s*[–~\-—至到]\s*\d+(?:\.\d+)?", r"\1", t_.replace(",", ""))   # a range: its start
        t_ = _re.sub(r"\d+(?:\s*[/、]\s*\d+)*\s*(?:个月|年|天|日|周|季度|months?|years?|weeks?|days?|x|×|倍|家|个|款)(?!\w*[%亿万])", "", t_)
        nums = [n for n in _re.findall(r"\d+(?:\.\d+)?", t_) if not (len(n) == 4 and n.startswith(("19", "20")))
                and not (n.isdigit() and int(n) <= 12)]   # durations, counts, small integers: wording, not data points
        pt = page_text.replace(",", "")
        from ._page import SLID as _SLID0
        # every printed reading of the page's exhibits counts (row_table Heat / Text cells, value labels…), also when
        # the fragment text above lost them; the formatted cell strings are what the reader sees
        pt += " " + " ".join(str(e_["tag"]) for x_ in dict.fromkeys(list(_SLID0) + ([ex] if ex is not None else []))
                             for e_ in getattr(x_, "reg", []) if e_.get("kind") == "text").replace(",", "")
        def _on_page(n):
            if n in pt or (("." in n) and n.rstrip("0").rstrip(".") in pt):
                return True
            nd = len(n.split(".")[1]) if "." in n else 0   # a rounded title number (17.6) of a precise one on the chart (17.58)
            return any(round(float(m_), nd) == float(n) for m_ in _re.findall(r"\d+\.\d+", pt)
                       if len(m_.split(".")[1]) > nd)
        missing = [n for n in nums if not _on_page(n)]
        frag_text = _re.sub(r"<[^>]+>", " ", "".join(str(f_) for f_ in frags) + "".join(b for b in body if "<chart " in b))
        years = [m_.group(1) for m_ in _re.finditer(r"(?<!\d)(20[2-4]\d)(?:E|F)?(?!\d)", self.title)
                 if not _re.search(r"(?:post|pre|by|since|after|before|until|through|from|in)[-\s]*$|[前后以来起至到]$",
                                   self.title[max(0, m_.start() - 7):m_.start()], _re.I)
                 and not _re.match(r"\s*(?:年?(?:以来|起|后|前|之前|之后))", self.title[m_.end():m_.end() + 4])]
        has_time_axis = len(set(_re.findall(r"(?<!\d)20[0-4]\d(?!\d)", frag_text))) >= 2   # a chart over years
        if years and frags and has_time_axis and not any(y in frag_text or y[2:] in frag_text or y in pt for y in years):
            missing += [f"{years[-1]}年"]   # "2030 年 2,700 亿" over a chart that ends in 2025
        if missing:
            SIGNALS.append(f"标题数字 {missing} 不在图上")
            plotted = [v_ for x_ in dict.fromkeys(list(_SLID0) + ([ex] if ex is not None else []))
                       for fa in (getattr(x_, "facts", None) or []) for _, vs in (fa.get("series") or [])
                       for v_ in vs if isinstance(v_, (int, float))]
            off = [n for n in missing if re.fullmatch(r"\d+(?:\.\d+)?", n)
                   and any(abs(float(n) - v_) <= max(0.051, abs(v_) * 0.006) for v_ in plotted)]
            self._title_label_off = off
            print(f"P{page} 提醒：标题里的数字 {missing} 在图上/要点里找不到——"
                  + (f"{off} 是图上画了的数据但没印标签：恢复数值标签（values=True，或只给这一根 focus=）"
                     if off else "把它画到图上（badge、cagr=/diff=、callout）或核对口径是否一致"))
        exs_ = [ex] if ex is not None else []
        if re.search(r"CAGR|年均|复合增", self.title, re.I) and not any(getattr(e, "cagr_drawn", False) for e in exs_) \
                and not any(re.search(r"CAGR\s*[+−-]?\d", re.sub(r"<[^>]+>", " ", str(x))) for x in frags) \
                and not _table_cagr_text(page_text, "".join(body) + "".join(str(f_) for f_ in frags)) \
                and not any(fa.get("kind") in ("bridge", "variance") for e in exs_ for fa in (getattr(e, "facts", None) or [])):
            SIGNALS.append("CAGR 未画")   # a bridge / waterfall page explains the change: no CAGR arrow to draw
            print(f"P{page} 提醒：标题有 CAGR，但图上没用 columns(cagr=(i, j)) / cagr_arrow 画斜向箭头（不要手画水平线 + 文字）")
        from ._marks import title_rate_orphans
        orphan = [o for e in exs_ for o in title_rate_orphans(e)]
        self._rate_orphan = orphan if getattr(self, "research", False) else []
        if orphan:   # warning: the title's CAGR belongs to a series the chart does not show
            SIGNALS.append("标题 CAGR 无对应序列")
            print(f"P{page} 提醒：标题里的增速 {orphan} 在图上任何序列/区间都算不出来——这个 CAGR 属于图上没画的指标"
                  "（如利润 vs 图上只有收入）：把该序列画进图里，或从标题删掉，不在标题写图外指标的增速")
        if _points_unmarked(ex, body):   # print-only nudge: never holds, never flags the page for review
            print(f"P{page} 提醒：右侧要点没有与图形对应的标记：给对应要点加 mark（同色色块或编号），"
                  "如 points(..., [(lead, text, \"accent\"), …]) / mark=n 对应 num_dot")
        self._mark_bad = _mark_colours_missing(ex, body, frags)   # before POINTS_LOG is cleared; _precheck holds once
        self._tie_bad = research_ties(ex, frags, title=self.title, body=body)
        POINTS_LOG.clear()
        page_xml_ = "".join(str(b) for b in body)
        if any(x_ and x_ in page_xml_ for x_ in EMPTY_BODY_LOG):   # review signal only (no hold)
            SIGNALS.append("要点只有引语没有正文")
            print(f"P{page} 提醒：{EMPTY_BODY_MSG}")
        EMPTY_BODY_LOG.clear()
        other = _title_of_other_page(self.title, cwd, deck, page) if deck and page is not None else None
        if other:
            SIGNALS.clear()
            msg = (f"P{page} 未写入：标题是 plan 里第 {other} 页的标题——这像是把 P{other} 的脚本复制过来只改了页码，"
                   f"会让两页一模一样。按 next 给这一页（P{page}）的 title / body / recipe 重新写页面脚本")
            print(msg)
            return {"ok": False, "held": [msg], "errors": [], "warnings": []}
        if deck and page is not None and me and _writes(cwd, deck, page) >= MAX_WRITES:
            print(f"P{page} 未写入：这页已经写过 {MAX_WRITES} 次，保留当前版本。转下一页（next），不再改这一页")
            return {"ok": False, "skipped": True, "writes": MAX_WRITES}
        if deck and page is not None and _blocks(cwd, deck, page, add=False) >= MAX_BLOCKS:
            from ._page import USED as _U0
            if "row_table" not in _U0 or _blocks(cwd, deck, page, add=False, key="rt") >= 2:
                print(f"P{page} 未写入：{SERVER_STOP_MSG}")
                last_ = _last_refusal(cwd, deck, page)
                if last_:
                    print(f"  {last_}")
                return {"ok": False, "skipped": True, "server_blocked": True}
            _blocks(cwd, deck, page, key="rt")   # row_table fallback attempts (≤2)
        from ..atomize_svg_to_slide._exhibit_publish import unformatted_code, UNFORMATTED_MSG, UNFORMATTED_FIX
        import html as _html
        leak = unformatted_code(_html.unescape(_re.sub(r"<[^>]+>", " ", _re.sub(
            r"<note\b.*?</note>", "", self.page(*body) + "".join(str(x) for x in frags), flags=_re.S))))
        if leak:   # never budgeted / never passes: no reader may see raw Python
            SIGNALS.clear()
            from ..atomize_svg_to_slide._exhibit_publish import unformatted_hint
            fix_ = unformatted_hint(leak)
            print(f"P{page} 未写入：{UNFORMATTED_MSG}（{leak[:2]}）——{fix_}")
            return {"ok": False, "held": [f"{UNFORMATTED_MSG}：{leak[:2]}——{fix_}"], "errors": [{"key": "unformatted_code",
                    "message": UNFORMATTED_MSG, "fix": fix_}], "warnings": []}
        if deck and page is not None:
            self._who = me
            held = _precheck(self, body, frags, ex, cwd, deck, page)
            gap_ = _right_gap(body, frags, self.right)
            if not held and gap_ > 150 and _first_hold(cwd, f"held-ibcs-{deck or '_'}.json", 1900 + int(page)):
                held = [f"内容右侧空出 {gap_:.0f}px，页面没有右栏——没传 side 时宽度用 body_w(f, rail=False)"
                        "（Exhibit(w=...) / text_table 宽）" + ("" if self.speech else "，或补 side=key_takeaways(...)")]
            if held:
                SIGNALS.clear()
                _record_held(cwd, page, me, held, deck)
                print(f"P{page} 未写入（本地预检，页面保持原样）：")
                for h_ in held:
                    print("  -", h_)
                print("  改完用同一调用重提（同一页最多拦 2 次；不读 svg_lib 源码、不写测量脚本——改不掉就删掉出问题的标签/文字或换成更简单的图）")
                return {"ok": False, "held": held, "errors": [], "warnings": []}
        from pathlib import Path as _Path
        xml_path = None
        if page is not None:   # the composed page XML is kept so small edits can be made in the file and re-sent
            xml_path = _Path(cwd or ".").resolve() / ".lark-slides" / "xml" / str(deck or "_") / f"p{int(page):02d}.xml"
            xml_path.parent.mkdir(parents=True, exist_ok=True)
        from ..atomize_svg_to_slide import _exhibit_publish as _pubm
        from ._page import USED as _USED
        _pubm.LIB_CARDS[0] = bool(getattr(self, "full_bleed", False) or _USED & _LIB_CARD_FUNCS)
        try:
            r = publish_slide(self.page(*body), *frags, presentation=deck, page=page, cwd=cwd, screenshot=screenshot,
                              waive=waive, save_as=str(xml_path) if xml_path else None,
                              note_who=me if not editing else None, layout=layout, why=why, same_as_prev=same_as_prev,
                              insert=insert)
        except TimeoutError as e:   # deck lock held by a stuck writer: nothing was sent, the page can be retried
            SIGNALS.clear()
            print(f"P{page} 未写入：{e}")
            return {"ok": False, "errors": [{"key": "deck_busy", "message": str(e), "fix": str(e)}], "warnings": []}
        finally:
            _pubm.LIB_CARDS[0] = False
        r["xml_path"] = str(xml_path) if xml_path else ""
        flags = list(dict.fromkeys(SIGNALS + ([f"写入警告 {len(r['warnings'])} 条"] if r.get("warnings") else [])))
        SIGNALS.clear()
        if r.get("ok") and page is not None and deck:
            _kind_ledger(cwd, deck, page, _page_kind())
            if getattr(self, "_rail", None) is not None:
                _rail_ledger(cwd, deck, page, self._rail)
        from ._page import USED as _U, LAYOUTS_USED as _LU
        _U.clear()
        _LU.clear()
        if r.get("ok") and me and page is not None and deck and not editing:   # deck=None only composes
            _record_flags(cwd, page, me, flags, deck)
            _writes(cwd, deck, page, add=True)
        if r.get("ok") and page is not None and deck:
            _blocks(cwd, deck, page, reset=True)   # a page that got through starts a fresh server-block budget
        if r.get("ok"):
            print(f"P{page} ok" + (f"  截图 {r['screenshot']}" if r.get("screenshot") else "")
                  + (f"  warnings {len(r['warnings'])}" if r.get("warnings") else "")
                  + (f"  XML {xml_path}" if xml_path else ""))
            for w_ in r.get("warnings") or []:   # the model only sees what is printed: every warning in full
                print(f"  - warning {w_}")
        else:
            from . import _refusal as _rf
            # an upload failure may carry the server lint report (error 4000153): show its issues as layout issues
            r["errors"] = _rf.normalise(r.get("errors", []), r.get("page_xml") or "")
            errs_ = r["errors"]
            print(f"P{page} 被拦 {len(errs_)} 条：")
            for e in errs_[:8]:
                print("  -", _rf.line(e))
            local = {"multi_page_command", "frozen", "exported", "seal", "tiny_text", "unformatted_code", "fake_phone",
                     "same_skeleton", "sample_label_overuse", "layout_note_missing", "layout_note_too_long",
                     "same_layout_as_neighbor", "layout_note_mismatch", "deck_identity_mismatch", "deck_registry_invalid",
                     "deck_readback_invalid"}
            layout_ = [e for e in errs_ if _rf.is_layout(e)]
            if any(e.get("key") == "deck_identity_mismatch" for e in errs_):
                print("  这是整份 deck 的页登记问题（有一张不在登记里的 slide），不是本页排版：不改版式、不计入本页拦截；"
                      "运行 multiagent_sync.py next 让流程处理，不要手改 pages-*.json，也不要用 +add-slide / +xml-put 绕过")
            elif errs_ and not layout_:   # network / auth / parameter failure: not the page's layout, no budget spent
                print("  这不是排版问题（上传/接口失败），不计入这页的服务端拦截次数：按上面的 message 修正参数或稍后用同一调用重试；"
                      "不要改版式，也不要绕过 Frame.publish")
            if deck and page is not None and not r.get("skipped") and layout_ and not (
                    {e.get("key") for e in errs_} & local):
                # server blocks count too: at 3 the fastest fix, at 4 a hard stop (the page is handed on)
                n_ = _blocks(cwd, deck, page)
                _last_refusal(cwd, deck, page, _rf.stop_message(layout_, n_))
                if n_ >= MAX_BLOCKS:
                    print(f"  {SERVER_STOP_MSG}")
                    print(f"  {_rf.stop_message(layout_, n_)}")
                    _server_blocked(cwd, page, me, deck)
                    r["server_blocked"] = True
                elif n_ >= 3:
                    print(f"  这页已被服务端拦 {n_} 次（第 {MAX_BLOCKS} 次后不再接受提交）：不要再挪坐标——删掉报错的标签/说话框/要点"
                          "（或 values=False），或换成同一比较关系的 row_table + Bar；下一次提交前先减内容")
            if xml_path:
                print(f"  本次合成的 XML：{xml_path}（只改文字/数字时可直接改这个文件，再用 republish_xml 重发）")
        return r

    def _add_glossary_line(self, text):
        """Fill the footer line frame() kept for terms (research data pages): "术语：CAGR = 年均复合增长率；…"."""
        g = getattr(self, "_gloss", None)
        if not g:
            return
        y, fw, sub, font = g
        self.xml += _box(X0, y, fw, 16, f"<p>{escape(text)}</p>", 10, sub, font)
        self._gloss = None

    def page(self, *body):
        """Full <slide> XML: frame + body shapes (strings) + speaker note."""
        note = (f'<note><content textType="body"><p>{escape(self.note)}</p></content></note>' if self.note else "")
        return ('<slide xmlns="https://www.larkoffice.com/sml/2.0"><style><fill><fillColor color="rgb(255,255,255)"/></fill>'
                f'</style><data>{self.xml}{"".join(body)}</data>{note}</slide>')


DENSE = 260          # body-text load per content page (CJK char = 1, Latin word = 2, number = 1); appendix ×2
RESEARCH_DENSE_X = 1.8   # business-research reading decks (CATL-style IC pages): cap 468, hold above ×1.15 ≈ 538
RESEARCH_FOOT_LINES = 5  # research footer: up to 4 numbered footnotes + 1 source line (other decks: 3)
SPEECH_DATA_CAP = 100    # business-deck (speech) data page: text outside the charts (title / footer not counted)
SPEECH_TEXT_CAP = 200    # business-deck page without a chart (structure, team, process…)
SPEECH_SUMMARY_CAP = 220  # business-deck P2 summary (review_summary)
SPEECH_TABLE_MAX = 3     # business-deck: tables beyond 3 rows or 3 columns must become a chart


def _sync_dirs(cwd, deck=None):
    """SYNC dirs of the task this page belongs to (see _publish._task_sync_dirs): those whose deck.txt names `deck`,
    plus a live one that has no deck yet; without deck only live tasks. Another deck's or a finished task's SYNC in the
    same CWD is never read."""
    from ..atomize_svg_to_slide._exhibit_publish import _task_sync_dirs
    return _task_sync_dirs(cwd, deck)


MIN_PLOT_H = 100   # slide px: a plot area lower than this is flagged (soft) — the page carries too many blocks
TINY_PLOT_H = 60   # slide px: below this the plot is held once (a strip, nothing comparable), then flagged
RAIL_SHARE = 0.5   # same key_takeaways right rail on more than half of the pages so far: suggest other compositions
_LIB_CARD_FUNCS = {"swot_matrix", "contents", "kpi_cards", "glossary_page"}   # library layouts that draw panels on purpose


MAX_WRITES = 3   # successful writes of one page (all agents): later polishing is not worth the viewer's churn
MAX_BLOCKS = 4   # server lint blocks of one page: then publish stops taking it (one row_table rewrite allowed)
SERVER_STOP_MSG = ("已被服务端拦 4 次：换成 row_table（Label + Bar/Text 列）版本一次写入，或去掉报错的标签"
                   "（不要改用 publish_slide / lark-cli 直写：同一服务端 lint，只会再被拦）")


def _blocks(cwd, deck, page, add=True, reset=False, key=None):
    """Server-block counter of a page (<cwd>/.lark-slides/blocked-<deck>.json): add=True counts one more and returns
    the count; add=False only reads; reset=True clears it (the page got through). key="rt" tracks the one row_table
    fallback attempt after the hard stop."""
    import json as _j
    from pathlib import Path as _P
    from ..atomize_svg_to_slide._exhibit_publish import _SealLock, reseal_blocked
    f = _P(cwd or ".") / ".lark-slides" / f"blocked-{deck}.json"
    try:
        d = _j.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        d = {}
    k = f"p{int(page):02d}" + (f":{key}" if key else "")
    if reset:
        if not any(x in d for x in (k, k + ":rt")):
            return 0
        d.pop(k, None)
        d.pop(k + ":rt", None)
    elif add:
        d[k] = d.get(k, 0) + 1
    else:
        return d.get(k, 0)
    f.parent.mkdir(parents=True, exist_ok=True)
    with _SealLock(cwd):   # the counter is sealed: a hand reset breaks the seal and publish refuses
        f.write_text(_j.dumps(d), encoding="utf-8")
        reseal_blocked(cwd)
    return d.get(k, 0)


def _last_refusal(cwd, deck, page, text=None):
    """The latest server-refusal summary of a page (<cwd>/.lark-slides/lastblock-<deck>.json): text= stores it, else
    returns it ("" if none) — so the hard-stop refusal can still name the issues that remain."""
    import json as _j
    from pathlib import Path as _P
    f = _P(cwd or ".") / ".lark-slides" / f"lastblock-{deck}.json"
    try:
        d = _j.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        d = {}
    k = f"p{int(page):02d}"
    if text is None:
        return d.get(k, "") if isinstance(d, dict) else ""
    d[k] = text
    try:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(_j.dumps(d, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass
    return text


def _server_blocked(cwd, page, me, deck=None):
    """After the hard stop: close the page's claim (done, flag server_blocked) so next hands the agent a new page."""
    import fcntl
    import json
    import time as _t
    for cl in (d / "claims.json" for d in _sync_dirs(cwd, deck) if (d / "claims.json").exists()):
        try:
            with open(cl.parent / "claims.lock", "w") as lk:
                fcntl.flock(lk, fcntl.LOCK_EX)
                allc = json.loads(cl.read_text(encoding="utf-8"))
                c = allc.get(f"p{int(page):02d}")
                if isinstance(c, dict) and (not me or me in (c.get("who"), c.get("reviewer"))):
                    c.update(state="done", t=_t.time(), review="server_blocked",
                             flags=list(dict.fromkeys((c.get("flags") or []) + ["server_blocked"])))
                    c.setdefault("built_by", c.get("who"))
                    cl.write_text(json.dumps(allc, ensure_ascii=False, indent=1), encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass


def _writes(cwd, deck, page, add=False):
    import json as _j
    from pathlib import Path as _P
    f = _P(cwd or ".") / ".lark-slides" / f"writes-{deck}.json"
    try:
        d = _j.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        d = {}
    k = f"p{int(page):02d}"
    if add:
        d[k] = d.get(k, 0) + 1
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(_j.dumps(d), encoding="utf-8")
    return d.get(k, 0)


def _collisions(f, body, ex, frags=()):
    """Body XML text boxes measured at their real (lint-estimated) height: one running into the footnote band, onto
    the chart box, or onto another text box. Cards (a text box inside a filled shape) are fine."""
    import sys as _s
    from pathlib import Path as _P
    _s.path.insert(0, str(_P(__file__).resolve().parents[2]))
    try:
        from _exhibit_text_fit import _measure
    except Exception:  # noqa: BLE001
        return []
    finally:
        _s.path.pop(0)
    boxes, fills, text_bottoms = [], [], []
    for m in re.finditer(r"<shape\b([^>]*)>(.*?)</shape>", "".join(body), re.S):
        a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
        try:
            x, y, w, h = (float(a[k]) for k in ("topLeftX", "topLeftY", "width", "height"))
        except (KeyError, ValueError):
            continue
        txt = re.sub(r"<[^>]+>", "", m.group(2)).strip()
        if a.get("type") == "text" and txt:
            meas = _measure(m.group(0)) * 1.02
            need = max(h, meas)
            boxes.append((x, y, x + w, y + need, txt[:16]))
            text_bottoms.append(y + min(h, meas) if meas > 0 else y + h)   # a tall box with 2 lines is not "filled"
        elif "<fill>" in m.group(2) or a.get("type") in ("rect", "roundRect"):
            fills.append((x, y, x + w, y + h))
    out = []
    bottoms = text_bottoms + [fl[3] for fl in fills]
    if ex is not None:   # the exhibit's drawn content, not its box: a 3-row table in a full-height box is still half empty
        regb = [e["box"][3] if e["kind"] != "line" else max(e["box"][0][1], e["box"][1][1])
                for e in getattr(ex, "reg", []) if e.get("tag") not in ("grid",)]
        bottoms.append(f.top + (max(regb) * ex.slide_h / ex.h if regb else ex.slide_h))
    for fr in frags:   # charts placed by hand (ex.to_slide fragments) and native charts fill the body too
        bottoms += [float(y_) + float(h_) for y_, h_ in re.findall(r'topLeftY="([-\d.]+)" width="[\d.]+" height="([\d.]+)"', str(fr))]
    bottoms += [float(y_) + float(h_) for y_, h_ in re.findall(r'<chart topLeftX="[-\d.]+" topLeftY="([-\d.]+)" width="[\d.]+" height="([\d.]+)"', "".join(body))]
    used = (max(bottoms) - f.top) / max(f.bottom - f.top, 1) if bottoms else 1
    if bottoms and used < 0.78 and not getattr(f, "research", False):   # research pages: _coverage_gap (x and y)
        out.append(f"{'页面半空' if used < 0.62 else '下方留白'}：内容只到正文区 {used:.0%} 高度——图区/要点栏/表格用 h=f.bottom−f.top 竖向铺满，"
                   "或放大关键数字、加一个支撑结论的小图")

    def inter(a, b):
        return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))

    def area(a):
        return max(1.0, (a[2] - a[0]) * (a[3] - a[1]))

    def in_card(b):
        return any(c[0] - 2 <= b[0] and b[2] <= c[2] + 2 and c[1] - 2 <= b[1] and b[3] <= c[3] + 4 for c in fills)
    for b in boxes:
        if b[3] > f.bottom + 6:
            why = (f"来源/脚注占 {f.foot_lines} 行把正文底抬到 {f.bottom:.0f}——先把 source 精简到机构简称、口径说明移到 note="
                   if getattr(f, "foot_lines", 0) > 2 else f"正文底 {f.bottom:.0f}：删字或减少条数")
            out.append(f"文字框 '{b[4]}' 实际高度到 y={b[3]:.0f}，压进脚注区（{why}）")
    charts = []   # chart areas: ex, or ex.to_slide(x, y) fragments placed by hand (bounding box of their shapes)
    if ex is not None:
        charts.append((f.left, f.top, f.left + ex.slide_w, f.top + ex.slide_h))
    for m in re.finditer(r'<chart topLeftX="([-\d.]+)" topLeftY="([-\d.]+)" width="([\d.]+)" height="([\d.]+)"', "".join(body)):
        x, y, w, h = (float(v) for v in m.groups())
        charts.append((x, y, x + w, y + h))
    for fr in frags:
        xs = [(float(a), float(b), float(c), float(d)) for a, b, c, d in re.findall(
            r'topLeftX="([-\d.]+)" topLeftY="([-\d.]+)" width="([\d.]+)" height="([\d.]+)"', str(fr))]
        if xs:
            charts.append((min(x for x, _, _, _ in xs), min(y for _, y, _, _ in xs),
                           max(x + w for x, _, w, _ in xs), max(y + h for _, y, _, h in xs)))
    from ._layouts import SLOT_TITLES as _ST   # columns_page / mixed_columns_page chart titles sit on their own slot
    own_ttl = {str(t_)[:16] for t_ in _ST.values()} if {"columns_page", "mixed_columns_page"} & _lay_used() else set()
    for cb in charts:
        for b in boxes:
            if b[4] in own_ttl:
                continue
            if inter(b, cb) > 0.15 * area(b):
                from ._layouts import rail_x
                out.append(f"文字框 '{b[4]}' 压在图区上（图区 x {cb[0]:.0f}–{cb[2]:.0f}）：" + (
                    "右栏要点占了右侧，图要建成 Exhibit(w=body_w(f), h=f.bottom − f.top)" if cb[2] > rail_x(f) - 4 and b[0] >= rail_x(f) - 4
                    else "缩小 Exhibit(w=) 或右移文字栏"))
                break
    for i, a in enumerate(boxes):
        for b in boxes[i + 1:]:
            if inter(a, b) > 0.2 * min(area(a), area(b)) and not (in_card(a) and in_card(b)):
                out.append(f"文字框 '{a[4]}' 与 '{b[4]}' 重叠：拉开或删字")
    return list(dict.fromkeys(out))[:4]


COVER_MIN = 0.80     # research body: share of the body band's width / height covered by content (x and y separately)
COVER_GAP = 120      # an empty band (px) narrower than this inside the body is spacing, not a hole
COVER_EDGE = 32      # an empty band at the body's right / bottom edge counts from this size on


def _content_boxes(xml):
    """(x0, y0, x1, y1) of everything visible in slide XML: text boxes shrunk to their longest line (a full-width box
    with a short label does not "fill" the width), filled shapes, images, tables, charts, lines ≥ 60px."""
    out = []
    for m in re.finditer(r'<(shape|table|chart|img|line|polyline|embed)\b([^>]*?)(/>|>(.*?)</\1>)', xml, re.S):
        tag, attrs, inner = m.group(1), m.group(2), m.group(4) or ""
        a = dict(re.findall(r'(\w+)="([^"]*)"', attrs))
        try:
            if tag == "line":
                x1, y1, x2, y2 = (float(a[k]) for k in ("startX", "startY", "endX", "endY"))
                if max(abs(x2 - x1), abs(y2 - y1)) >= 60:
                    out.append((min(x1, x2), min(y1, y2) - 1, max(x1, x2), max(y1, y2) + 1))
                continue
            x, y, w, h = (float(a[k]) for k in ("topLeftX", "topLeftY", "width", "height"))
        except (KeyError, ValueError):
            continue
        if tag == "shape" and a.get("type") == "text":
            paras = [" ".join(re.sub(r"<[^>]+>", "", p).split()) for p in re.findall(r"<p\b[^>]*>(.*?)</p>", inner, re.S)]
            paras = [p for p in paras if p]
            if not paras:
                continue
            fs = float((re.search(r'fontSize="([\d.]+)"', inner) or [0, 14])[1])
            tw_ = min(w, max(sum(fs if ord(c) > 0x2E80 else fs * 0.56 for c in p) for p in paras))
            al = (re.search(r'textAlign="(\w+)"', inner) or [0, "left"])[1]
            x = x + (w - tw_) / 2 if al == "center" else x + w - tw_ if al == "right" else x
            w = tw_
        elif tag == "shape" and "<fill>" not in inner and "<border" not in inner:
            continue
        if w > 6 and h > 6:
            out.append((x, y, x + w, y + h))
    return out


def _axis_cover(spans, lo, hi):
    """Share of [lo, hi] not inside an empty band: inner gaps ≥ COVER_GAP and edge gaps ≥ COVER_EDGE count as empty."""
    iv = sorted((max(a, lo), min(b, hi)) for a, b in spans if min(b, hi) > max(a, lo))
    if not iv or hi <= lo:
        return 0.0
    empty, cur = 0.0, lo
    for a, b in iv:
        if a - cur > (COVER_EDGE if cur == lo else COVER_GAP):
            empty += a - cur
        cur = max(cur, b)
    if hi - cur > COVER_EDGE:
        empty += hi - cur
    return 1 - empty / (hi - lo)


def _coverage_gap(f, body, frags):
    """business-research: the body band projected on x and on y — an empty right third (a table that stops at 70% of
    the width) or an empty lower third (a strip of chart over white) is a half-empty page even when one thin box
    reaches the bottom. Returns "" or the hold text. Appendix / contents / summary pages are not checked."""
    if not getattr(f, "research", False) or f.appendix or getattr(f, "summary", False):
        return ""
    xml = "".join(str(b) for b in body) + "".join(str(x) for x in frags)
    top, bot, left, right = f.top, f.bottom, f.left, f.right
    boxes = [b for b in _content_boxes(xml) if b[3] > top + 2 and b[1] < bot - 2 and b[2] > left and b[0] < right]
    if not boxes:
        return ""
    cx = _axis_cover([(b[0], b[2]) for b in boxes], left, right)
    cy = _axis_cover([(b[1], b[3]) for b in boxes], top, bot)
    from ._layouts import rail_x as _rx, RAIL_TEXT as _RT
    rx = _rx(f)
    has_rail = bool(_RT) or any(b[0] >= rx - 4 and b[3] - b[1] >= 0.8 * (bot - top) for b in boxes)
    if has_rail and cy >= COVER_MIN:   # a full-height rail hides a short chart: check the main column on its own
        main = [b for b in boxes if b[2] <= rx - 4]
        cym = _axis_cover([(b[1], b[3]) for b in main], top, bot) if main else 1.0
        if cym < COVER_MIN:
            return (f"左侧主图区下方空白：主图只占正文高度的 {cym:.0%}（右栏铺满，左边没铺满）——"
                    "Exhibit(h=f.bottom−f.top) 让主图用满高度；单条 100% 横条 / 只有几行的表撑不满时，在下面再放一张"
                    "支撑图（ex.split / column_boxes 上下两块：构成 + 趋势、结构 + 对标），或换成更高的图（柱状、表格）")
    if has_rail and not (_lay_used() & _FIXED_ASPECT):   # a hole between the main column and the rail: the chart was
        # made narrower than body_w(f). A 10×10 icon grid is square by construction (its cells stay square, the key
        # sits beside it): it cannot widen to the rail, so the gap says nothing about a width bug
        main_r = max([b[2] for b in boxes if b[2] <= rx - 4] or [rx])
        if rx - main_r >= 120:
            return (f"主图和右栏之间空出 {rx - main_r:.0f}px：body_w(f) 已经给右栏留好了位置，"
                    "Exhibit(w=body_w(f)) 直接用、不要再减（body_w(f) − 220 这类写法会把右栏宽度扣两次）；"
                    "row_table 的列宽加起来等于图宽（或不写 width 让列自动分配）")
    if cx >= COVER_MIN and cy >= COVER_MIN:
        return ""
    where = []
    if cy < COVER_MIN:
        where.append(f"纵向只用了正文区 {cy:.0%}")
    if cx < COVER_MIN:
        where.append(f"横向只用了 {cx:.0%}（右侧/中间大片空白）")
    return ("页面半空：" + "，".join(where) + "——主图或表格的框用满正文区：Exhibit(w=body_w(f, rail=False) 或 body_w(f), "
            "h=f.bottom−f.top)，row_table 的列宽加起来等于图宽；内容确实少就补一张支撑图/右栏要点，或并入相邻页")


_VAGUE_QTY = re.compile(r"约\s*\d+(?:\.\d+)?\s*(?:%|倍|亿|万|元|x|×|个|家|pt)|数[十百千万亿]+(?:亿|万)?|数倍|几倍|近?[一二两三四五六七八九十]成|"
                        r"[两三四]位数|翻[一二两三四五]?番")
_VAGUE_STEM = re.compile(r"约|数[十百千万亿倍]|几倍|成|位数|翻")
_PLAN_NUM = re.compile(r"\{[^}]*\}|\d+(?:\.\d+)?\s*(?:%|倍|亿|万|元|x|×|pt|家)")


def _title_vague_numbers(f, cwd, deck, page):
    """business-research: the plan row's title carried an exact figure ({F[...]} / '39.5%') and the published title says
    '约 40%' / '数百亿' / '数倍' / '两位数' instead — the number was blurred to get past the title-number check. ""."""
    if not (getattr(f, "research", False) and deck and page is not None and int(page) > 3):
        return ""
    vague = _VAGUE_QTY.findall(f.title or "")
    if not vague:
        return ""
    for d in _sync_dirs(cwd, deck):
        row = _plan_row(d / "plan.py", int(page))
        if not row:
            continue
        plan_t = str(row.get("title") or "")
        exact = row.get("_title_has_num") or bool(_PLAN_NUM.search(plan_t))
        new = [v_ for v_ in vague if v_ not in plan_t and not any(s_ in plan_t for s_ in _VAGUE_STEM.findall(v_))]
        if exact and new:
            return (f"标题把精确数改成了虚化说法 {new[:3]}：plan 这页标题是精确数。标题写回精确数（从 plan/research 变量拼），"
                    "把这个数画到图上——focus= 高亮那根柱、callout / badge 标注，或 values=True 印出标签；不要改标题去过检查")
    return ""


# build / internal vocabulary that must never reach the reader (parameter names, plan markup, recipe words)
_BUILD_TERMS = [
    r"轴下(?:第[一二三四五六七八九十\d]+|数据)?行", r"(?:利润率|毛利率|增速|同比)行(?!业)", r"【(?:核心|重点|主图|辅图|结论|示意)】",
    r"(?<![A-Za-z_])(?:rows|focus|values|cagr|diff|frags|recipe|rail|kpis)\s*=", r"所以呢",
    # research-direction codenames of the multi-agent build ("R4 模型" / "R2 方向"); "R&D" / "R2 值" never match
    r"(?<![A-Za-z\d])R\d\s*(?:模型|方向|调研|测算)",
    r"(?<![A-Za-z\d])R\d\s+(?:model|direction|research)\b",
    # English build words: the under-axis data row, "So what:" lead-ins of the recipe
    r"(?i)\b(?:under|below)[-\s](?:axis|chart)\s+rows?\b", r"\bSo what\s*[:：]",
]
_BUILD_TERMS_ZH = [r"(?<![A-Za-z])focus(?![A-Za-z])", r"(?<![A-Za-z])Watch(?![A-Za-z])"]   # English words on a Chinese page


def _build_jargon(text, zh=True):
    """Build / internal words in the reader-visible text (first hit of each pattern)."""
    out = []
    for pat in _BUILD_TERMS + (_BUILD_TERMS_ZH if zh else []):
        m = re.search(pat, text)
        if m:
            out.append(m.group(0).strip())
    return list(dict.fromkeys(out))


def text_load(text):
    """Reading load of a text: CJK chars + 2 × Latin words + numbers (≈ CJK-char equivalents)."""
    return (len(re.findall(r"[\u4e00-\u9fff]", text)) + 2 * len(re.findall(r"[A-Za-z]{2,}", text))
            + len(re.findall(r"\d+(?:[.,]\d+)*", text)))


_CN_NUM = {"一": 1, "两": 2, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
_MAIN_CLAIM = re.compile(r"(?:主要|主因|大头|大部分|多半|最大(?:贡献|来源|拖累)?)(?:是|来自|因为|因|由于|由|源于|靠|在于|为)?\s*"
                         r"([^，,。；;：:（(]{2,30})")
_RESIDUAL = re.compile(r"其他|其它|other|others|残差|差额|未分类|其他因素|其它因素|other factors", re.I)


def _title_vs_data(title, facts):
    """Claims in the title that the page's own chart data contradicts: "N 项达标 / 全部达标" vs the Status column,
    "主要来自 X" vs the largest bridge / variance step. Only fires on a recognisable claim with matching data."""
    out = []
    t = title or ""
    st = next((x for x in facts if x["kind"] == "status"), None)
    if st and st["n"]:
        g, red, amb = st["counts"]["green"], st["counts"]["red"], st["counts"]["amber"]
        m = re.search(r"(\d+|[一两二三四五六七八九十])\s*[项家个款条](?:指标|门店|院区|供应商|品类)?(?:已|均)?(?<!未)达标", t)
        if m:
            n = int(m.group(1)) if m.group(1).isdigit() else _CN_NUM[m.group(1)]
            if n != g:
                out.append(f"标题说'{m.group(0)}'，但表里达标（Status=green）的是 {g} 项（接近 {amb}、未达标 {red}）：按数据改标题")
        elif re.search(r"全部达标|均已?达标|全面达标|全线达标", t) and g != st["n"]:
            out.append(f"标题说全部达标，但表里只有 {g}/{st['n']} 项达标：按数据改标题")
        m = re.search(r"(?:仅|只有|只)?\s*(\d+|[一两二三四五六七八九十])\s*[项家个款条](?:指标|门店|院区|供应商|品类)?"
                      r"(?:未达标|未达成|未达(?:到)?(?:[^，,。；;：:]{0,12}?目标)?|不达标|没达标)", t)
        if m:
            n = int(m.group(1)) if m.group(1).isdigit() else _CN_NUM[m.group(1)]
            if n not in (red, red + amb):
                out.append(f"标题说'{m.group(0).strip()}'，但表里未达标 {red} 项（另有接近 {amb} 项）：按数据改标题")
    steps = next((x for x in facts if x["kind"] == "bridge"), None) or next((x for x in facts if x["kind"] == "variance"), None)
    m = _MAIN_CLAIM.search(t)
    if steps and m and len(steps["items"]) >= 2:
        seg = m.group(1)
        resid = [(k, v) for k, v in steps["items"] if v and _RESIDUAL.fullmatch(str(k).strip())]
        items = [(k, v) for k, v in steps["items"] if v and not _RESIDUAL.fullmatch(str(k).strip())]
        pieces = [p_ for p_ in re.split(r"[与和及、/+]|以及", seg) if len(p_.strip()) >= 2]

        def said(lab):
            lab = lab.strip()
            return len(lab) >= 2 and (lab in seg or any(p_.strip() in lab or lab in p_ for p_ in pieces))
        named = [k for k, _ in items if said(k)]
        if named:
            ctx = t[max(0, m.start() - 12):m.end()]
            neg = re.search(r"下降|下滑|减少|拖累|降幅|亏损|流失|萎缩|回落|减量|decline|drop", ctx)
            pos = re.search(r"增量|增长|增加|提升|上升|改善|拉动|带动|贡献|growth|gain", ctx)
            pool = [(k, v) for k, v in items if (v < 0 if neg and not pos else v > 0 if pos and not neg else True)] or items
            top = max(pool, key=lambda kv: abs(kv[1]))
            if top[0] not in named:
                vv = f"{top[1]:+,.4g}".replace("-", "−")
                out.append(f"标题说'主要来自 {'、'.join(named)}'，但图上最大的一项是 {top[0]}（{vv}）：按数据改标题")
            else:   # the named step leads the real drivers — but a residual bucket bigger than it is the real "main" part
                sign = (lambda v: v < 0) if neg and not pos else (lambda v: v > 0) if pos and not neg else (lambda v: True)
                big = [(k, v) for k, v in resid if sign(v) and abs(v) > abs(top[1]) + 1e-9]
                if big:
                    k, v = max(big, key=lambda kv: abs(kv[1]))
                    vv = f"{v:+,.4g}".replace("-", "−")
                    out.append(f"最大一项是'{k}'（{vv}）：把它拆开或改标题，不要靠改名")
    out += _vs_ref_claim(t, facts)
    out += _driver_claim(t, facts)
    out += _trend_claim(t, facts)
    out += _to_value_claim(t, facts)
    out += _still_claim(t, facts)
    out += _funnel_claim(t, facts)
    return out


_VS_REF = re.compile(r"(\d+(?:\.\d+)?)\s*(?:x|倍|%|元|亿元|亿)?[^，,。；;\d]{0,8}?(低于|高于|不及|超过|领先|落后于?)"
                     r"[^，,。；;\d]{0,10}?(?:均值|平均|中位数|基准|行业|同业|龙头|目标|阈值|基线)")


def _vs_ref_claim(t, facts):
    """'19.2x 低于消费龙头均值' while the chart's reference line (the 均值) sits at 15x: the title's direction must
    match the number it names against the reference line drawn on the chart."""
    refs = [x["value"] for x in facts if x.get("kind") == "ref"]
    if len(refs) != 1:
        return []
    out = []
    for m in _VS_REF.finditer(t or ""):
        v, word = float(m.group(1)), m.group(2)
        below = word in ("低于", "不及", "落后", "落后于")
        if (below and v > refs[0] * 1.001) or (not below and v < refs[0] * 0.999):
            out.append(f"标题说 {v:g} {word}基准，但图上的基准线是 {refs[0]:g}（{v:g} {'高于' if below else '低于'}它）：按图上的数改方向，"
                       "或把基准线画成标题说的那个口径")
    return out


_FUNNEL_CLAIM = re.compile(r"(?:最大(?:的)?流失|流失最大|流失最多|最大(?:的)?漏损|最大断点)(?:的)?(?:环节)?\s*(?:在|是|为|发生在|出现在|位于)?\s*"
                           r"([^，,。；;：:（(]{2,30})")


def _funnel_claim(t, facts):
    """"最大流失在 X → Y" vs the step funnel() marked (lowest conversion, or furthest below target). Names of the drawn
    stages found in the claim decide: two names must be the marked pair, one name must belong to it. No stage name
    in the claim → no check."""
    fn = next((x for x in facts if x.get("kind") == "funnel"), None)
    m = _FUNNEL_CLAIM.search(t or "")
    if not fn or not m:
        return []
    seg = m.group(1)
    hits = sorted((seg.find(nm), nm) for nm in fn["stages"] if len(nm) >= 2 and nm in seg)
    names = [nm for _, nm in hits]
    a, b = fn["worst"]
    if not names or (len(names) >= 2 and (names[0], names[1]) == (a, b)) or (len(names) == 1 and names[0] in (a, b)):
        return []
    why = "低于目标最多" if fn.get("vs_target") else "转化率最低"
    return [f"标题说'{m.group(0).strip()}'，但漏斗上{why}的一步是 {a} → {b}：按图改标题，或给 funnel(targets=) 传各步目标转化"]


_STILL = re.compile(r"([^\s，,。；;：:、（(]{2,16}?)\s*(?:同比|较去年|比去年)?\s*仍(?:然|在)?\s*(高|增长?|上升|上涨|攀升|走高)")


def _still_claim(t, facts):
    """"X 仍高 / X 仍在增长 / X 同比仍上升" vs a recorded growth item named X (two periods, e.g. 2024 vs 2025): its
    change must be positive. Skipped unless exactly one drawn item matches X (e.g. "X 同比仍高" while X fell)."""
    growth = [x for x in facts if x.get("kind") == "growth"]
    if not growth:
        return []
    for m in _STILL.finditer(t):
        subj = re.sub(r"^(?:但|而|且|其中|主要|以及|与|和)", "", m.group(1))
        pieces = [p_ for p_ in re.split(r"[与和及、/+]|以及", subj) if len(p_.strip()) >= 2] or [subj]
        for g in growth:
            hits = [it for it in g.get("items") or [] if len(str(it[0]).strip()) >= 2
                    and any(str(it[0]).strip() in p_ or p_.strip() in str(it[0]) for p_ in pieces)]
            if not hits:
                continue
            bad = [it for it in hits if it[2] is not None and it[2] < 0]
            if bad:
                nm, rate, d = bad[0]
                show = f"{rate * 100:+.1f}%".replace("-", "−") if rate is not None else f"{d:+,.4g}".replace("-", "−")
                return [f"标题说'{m.group(0).strip()}'，但图上 {nm} 是下降的（{show}）：按数据改标题"
                        f"（如'{nm}同比降{show.lstrip('−+')}'，或只写水平不写'仍'）"]
            break
    return []


_DRIVER = re.compile(r"(?:由|靠)\s*([^\s，,。；;：:、（(]{2,12}?)\s*(?:拉动|带动|驱动)"
                     r"|([^\s，,。；;：:、（(由靠]{2,12}?)\s*(?:放量|驱动|带动|拉动|领涨|领跑)")


def _driver_claim(t, facts):
    """"储能放量 / 由动力拉动 / X 带动增长" vs a recorded multi-object growth comparison: X must have the largest growth
    rate (or, without rates, the largest increase). Skipped when X is not one of the drawn objects."""
    growth = [x for x in facts if x.get("kind") == "growth" and len(x.get("items") or []) >= 2]
    if not growth:
        return []
    out = []
    for m in _DRIVER.finditer(t):
        x = (m.group(1) or m.group(2) or "").strip()
        x = re.sub(r"^(?:主要|主要由|由|靠|是|在于|其中|而|且|但)", "", x)
        if len(x) < 2:
            continue
        for g in growth:
            items = g["items"]
            hit = [it for it in items if len(it[0].strip()) >= 2 and (it[0].strip() in x or x in it[0].strip())]
            if len(hit) != 1:
                continue
            rated = [it for it in items if it[1] is not None]
            if len(rated) == len(items):
                top = max(items, key=lambda it: it[1])
                key, show = (lambda it: it[1]), (lambda it: f"{it[1] * 100:+.1f}%".replace("-", "−"))
            else:
                top = max(items, key=lambda it: it[2])
                key, show = (lambda it: it[2]), (lambda it: f"{it[2]:+,.4g}".replace("-", "−"))
            if top[0] != hit[0][0] and key(top) > key(hit[0]) + 1e-9:
                out.append(f"标题说'{m.group(0).strip()}'，但图上增长最快的是 {top[0]}（{show(top)}），"
                           f"{hit[0][0]} 只有 {show(hit[0])}：按数据改标题（主语换成 {top[0]}，或写清 {hit[0][0]} 的真实角色）")
            break
        if out:
            break
    return out


_TREND = re.compile(r"(持续|连续\s*(\d+|[一两二三四五六七八九十])\s*(?:个)?(?:期|年|季度?|个?月|周))\s*"
                    r"(上行|增长|上升|走高|提升|攀升|改善|下滑|下降|下行|走低|回落|萎缩)")


def _trend_claim(t, facts):
    """"持续上行 / 连续 N 期增长 / 持续下滑" vs the one recorded time series: it must move that way every period
    (the last N for 连续 N). Only with exactly one series on the page."""
    m = _TREND.search(t)
    if not m:
        return []
    series = [x for x in facts if x.get("kind") == "series"]
    if len(series) != 1:
        return []
    vals = [v for v in series[0]["values"] if v is not None]
    pers = [p for p, v in zip(series[0].get("periods") or [None] * len(series[0]["values"]), series[0]["values"])
            if v is not None]
    if m.group(2):
        k = int(m.group(2)) if m.group(2).isdigit() else _CN_NUM.get(m.group(2), 0)
        if k < 1 or k + 1 > len(vals):
            return []
        vals, pers = vals[-(k + 1):], pers[-(k + 1):]
    if len(vals) < 3 and not m.group(2):
        return []
    down = m.group(3) in ("下滑", "下降", "下行", "走低", "回落", "萎缩")
    bad = [i for i in range(1, len(vals)) if (vals[i] > vals[i - 1] if down else vals[i] < vals[i - 1])]
    if not bad:
        return []
    i = bad[0]
    a = pers[i - 1] if pers and pers[i - 1] is not None else f"第{i}期"
    b = pers[i] if pers and pers[i] is not None else f"第{i + 1}期"
    return [f"标题说'{m.group(0)}'，但 {a}→{b} {'回升' if down else '回落'}（{fmt(vals[i - 1])}→{fmt(vals[i])}）：按数据改标题"
            f"（如'{('总体下行' if down else '总体上行')}、{b} {'反弹' if down else '回落'}'）"]


_TO_VALUE = re.compile(r"(升至|增至|提升至|攀升至|涨至|降至|跌至|回落至|下滑至|缩至)\s*(\d[\d,]*(?:\.\d+)?)")


def _to_value_claim(t, facts):
    """'ASP 升至 1129' over a series that fell into 1129 (the point before it was higher): the verb contradicts the data.
    Only when exactly one recorded series contains that value at a non-first position."""
    out = []
    series = [x for x in facts if x.get("kind") == "series"]
    for m in _TO_VALUE.finditer(t or ""):
        v = float(m.group(2).replace(",", ""))
        hits = [(s_, i) for s_ in series for i, x in enumerate(s_.get("values") or [])
                if i > 0 and x is not None and abs(x - v) <= max(0.051, abs(v) * 0.005)]
        if len(hits) != 1:
            continue
        s_, i = hits[0]
        prev = next((x for x in reversed(s_["values"][:i]) if x is not None), None)
        if prev is None:
            continue
        up = m.group(1) in ("升至", "增至", "提升至", "攀升至", "涨至")
        if (up and v < prev) or (not up and v > prev):
            out.append(f"标题说'{m.group(0)}'，但图上前一期是 {fmt(prev)}——实际是{'下降' if up else '上升'}到 {fmt(v)}：按数据改动词")
    return out


_GROWTH_T = re.compile(r"CAGR|年均|复合|年化|增速|增长|增至|增长到|翻(?:了)?(?:一番|倍)|上升|提升|攀升|走高|扩大|"
                       r"grow|growth|rise|increase|doubl", re.I)
_DOWN_T = re.compile(r"下降|下滑|回落|萎缩|走低|减少|缩小|decline|drop|fall", re.I)
_GAP_T = re.compile(r"差距|差值|领先|落后|高出|低于|高于|多出|是.{0,8}的\s*\d+(?:\.\d+)?\s*[倍x×]|\d+(?:\.\d+)?\s*[倍x×]|"
                    r"gap|lead|ahead|behind|vs\.?", re.I)
_TARGET_T = re.compile(r"目标|预算|缺口|达成|完成率|target|budget|plan", re.I)
_YOY_T = re.compile(r"同比|环比|较去年|比去年|YoY|MoM|拐点|转折|反弹|由降转升|由升转降", re.I)


def _title_value_idx(title, vals):
    """Index of the value the title names (exact or rounded match), else None."""
    nums = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", (title or "").replace(",", ""))
            if not (len(n) == 4 and n.startswith(("19", "20")))]
    for n in nums:
        for i, v in enumerate(vals):
            if v is not None and (abs(v - n) < 1e-9 or round(v, 1) == round(n, 1) or round(v) == n):
                return i
    return None


def _py(v):
    return repr(v) if not isinstance(v, str) else repr(v[:24])


def suggest_annotation(title, facts):
    """A ready-to-use annotation call for the page's chart, derived from its title and the data the chart drew
    (facts kind="chart" recorded by columns / lines / row_table). "" when no chart context is known. Never drawn
    automatically — the refusal prints it so the author adds it in one round."""
    charts = [x for x in (facts or []) if isinstance(x, dict) and x.get("kind") == "chart"]
    if not charts:
        return ""
    c = charts[0]
    cats, series = c.get("cats") or [], c.get("series") or []
    t = title or ""
    if not cats or not series:
        return ""
    vals = series[0][1] if series else []
    nz = [i for i, v in enumerate(vals) if v is not None]
    if not nz:
        return ""
    i0, i1 = nz[0], nz[-1]
    k_title = _title_value_idx(t, vals)
    from ._page import is_period
    periods = len(cats) >= 2 and all(is_period(x) for x in cats)
    fn = c.get("fn")
    if fn == "columns":
        args = "categories, series"
        if _TARGET_T.search(t):
            top = max(v for v in vals if v is not None)
            return (f"columns(ex, box, {args}, ..., target=({_py(round(top * 1.1, 2))}, '目标'))"
                    "（把目标值换成 plan 里的真实目标）")
        if len(series) >= 2 and not periods and _GAP_T.search(t):
            return (f"columns(ex, box, {args}, ..., delta=(0, 1))  # 每组「{series[1][0]}」−「{series[0][0]}」的差，程序算")
        if _YOY_T.search(t) and len(nz) >= 2:
            k = (k_title - 1) if k_title else nz[-2]
            k = max(nz[0], min(k, nz[-2]))
            return f"columns(ex, box, {args}, ..., yoy={k})  # {cats[k]}→{cats[k + 1]} 的变化箭头"
        named = [i for i in nz if len(str(cats[i])) >= 2 and str(cats[i]) in t]
        if _GAP_T.search(t) and len(named) >= 2:
            i, j = sorted(named[:2])
            return f"columns(ex, box, {args}, ..., diff=({i}, {j}))  # {cats[i]} vs {cats[j]} 的差距/倍数，程序算"
        if _GAP_T.search(t) and not periods and len(nz) >= 2:
            j = named[0] if named else (k_title if k_title is not None else max(nz, key=lambda i: vals[i]))
            i = min(nz, key=lambda i_: vals[i_]) if j != min(nz, key=lambda i_: vals[i_]) else max(nz, key=lambda i_: vals[i_])
            i, j = sorted((i, j))
            return f"columns(ex, box, {args}, ..., diff=({i}, {j}))  # {cats[i]} vs {cats[j]} 的差距/倍数，程序算"
        if periods and len(nz) >= 2 and all(vals[i] and vals[i] > 0 for i in (i0, i1)):
            j = k_title if k_title is not None and k_title > i0 else i1
            return (f"columns(ex, box, {args}, ..., cagr=({i0}, {j}))  # {cats[i0]}→{cats[j]} CAGR 斜向箭头"
                    f"（或 r = columns(...); cagr_arrow(ex, r, {i0}, {j})）")
        if len(nz) >= 2:
            j = k_title if k_title is not None else max(nz, key=lambda i: vals[i])
            i = i0 if j != i0 else i1
            i, j = sorted((i, j))
            return f"columns(ex, box, {args}, ..., diff=({i}, {j}))  # {cats[i]} vs {cats[j]}，程序算"
        return f"columns(ex, box, {args}, ..., note=({_py(cats[i0])}, '一句含义'))"
    if fn == "lines":
        xs = c.get("x") or cats
        if len(series) >= 2 and (_GAP_T.search(t) or not (_GROWTH_T.search(t) or _DOWN_T.search(t))):
            return (f"lines(ex, box, x, series, ..., delta=({_py(series[0][0])}, {_py(series[1][0])}, {_py(xs[i1])}))"
                    f"  # {xs[i1]} 时两线差，程序算")
        if _TARGET_T.search(t):
            return "ax = lines(...); ax.ref_y(目标值, '目标')  # 目标值取 plan 里的真实数"
        k = k_title if k_title is not None else (max(nz, key=lambda i: vals[i]) if not _DOWN_T.search(t)
                                                 else min(nz, key=lambda i: vals[i]))
        return (f"lines(ex, box, x, series, ..., note=({_py(xs[k])}, '一句判断'))  # 说话框指向 {series[0][0]} 在 {xs[k]} 的点"
                f"；或 ax = lines(...); callout(ex, (ax.sx({_py(xs[k])}), ax.sy({_py(vals[k])})), '一句判断')")
    if fn == "row_table":
        n = len(cats)
        if n >= 4 and re.search(r"前\s*\d+|top\s*\d+|头部|集中|合计|占比", t, re.I):
            m = re.search(r"前\s*(\d+)|top\s*(\d+)", t, re.I)
            k = int(next(g for g in m.groups() if g)) if m else 3
            col = (c.get("col") or [len(c.get("headers") or []) - 1])[0]
            tot = sum(v for v in vals if isinstance(v, (int, float)))
            top = sum(v for v in vals[:k] if isinstance(v, (int, float)))
            share = f"{top / tot:.0%}" if tot else "x%"
            return (f"row_table(..., brackets=[(0, {k - 1}, '前{k} 合计 {share}', {col})])  # 括号括住前 {k} 行，"
                    "占比用程序算")
        j = k_title if k_title is not None else max(nz, key=lambda i: vals[i] if isinstance(vals[i], (int, float)) else 0)
        return (f"row_table(..., focus=lambda r: r['label'] == {_py(cats[j])})，再加 Text 列写差值/排名，或 "
                f"callout(ex, (r['col'][{_py(series[0][0])}][1], r['y'][{_py(cats[j])}]), '一句判断')")
    return ""


def side_used(body):
    """True when the page body carries a right-hand takeaway rail (the key_takeaways block marker)."""
    return any("data-rail=" in str(b) or "key-takeaways" in str(b) for b in body)


_FIXED_ASPECT = {"icon_grid", "person_grid"}   # layouts whose figure keeps its aspect ratio (square icon cells)
_PLAN_TABLE_FNS = {"row_table", "text_table", "table_block", "native_table", "heat_matrix", "kpi_spark_table"}


def _plan_components_missing(cwd, page, deck, body, frags, ex):
    """The plan row names a table / chart / rail / schematic image the page does not carry (e.g. a left table lost while
    rebuilding): "" or one hold message. Counted with multiagent_sync._row_components (the plan_ready block count)."""
    from ._page import USED, BLOCKS
    import sys as _s
    from pathlib import Path as _P
    from ..atomize_svg_to_slide._exhibit_publish import NAV_BATCH
    if page is None or NAV_BATCH[0]:   # contents / chapter nav pages (their plan row may be stale after an insert)
        return ""
    row = None
    for d in _sync_dirs(cwd, deck):
        try:   # a page registered in gaps.md ("P6 不设右栏：…") already explained what it leaves out
            if re.search(rf"(?<![A-Za-z\d])[Pp]0*{int(page)}(?!\d)", (d / "gaps.md").read_text(encoding="utf-8")):
                return ""
        except OSError:
            pass
        row = _plan_row(d / "plan.py", int(page))
        if row:
            break
    if not row or row.get("chart") is False or not row.get("body") \
            or str(row.get("recipe", "")).split("/")[0].strip() in _TEXT_RECIPES or int(page) <= 3:
        return ""   # cover / contents / executive summary: text structure pages, never held for a missing chart
    _s.path.insert(0, str(_P(__file__).resolve().parents[2]))
    try:
        from multiagent_sync import _row_components
        _, names = _row_components(row)
    except Exception:  # noqa: BLE001
        return ""
    finally:
        _s.path.pop(0)
    xml = "".join(str(b) for b in body) + "".join(str(x) for x in frags)
    has = {"表": bool(USED & _PLAN_TABLE_FNS) or "<table" in xml or "table_block" in BLOCKS,
           "图": ex is not None or bool(frags) or "<chart " in xml or bool(_lay_used() & _FIXED_ASPECT),
           "右栏": "key_takeaways" in BLOCKS or "takeaways" in BLOCKS or "points" in USED or side_used(body),
           "示意图": "<img" in xml}
    miss = [n_ for n_ in names if has.get(n_.split("×")[0], True) is False
            and not (n_.startswith("表") and has["图"] and not any(x.startswith("图") for x in names))]
    # a chart in place of a planned table-only page is an upgrade, not a loss
    if not miss:
        return ""
    return (f"plan 组件缺失：plan 第 {page} 页写了 {'、'.join(names)}，页面里没有 {'、'.join(miss)}——把它画回来"
            "（用 next 给的 layout_code / recipe_code；重建页面时别丢块）；确实不需要就在 gaps.md 记一行原因再原样重提（只拦这一次）")


def _rail_ledger(cwd, deck, page=None, rail=None):
    """Deck-wide {page: carries the key_takeaways right rail} (page scripts are separate processes)."""
    import json as _j
    from pathlib import Path as _P
    f = _P(cwd or ".") / ".lark-slides" / f"rails-{deck}.json"
    try:
        d = _j.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        d = {}
    if page is not None and rail is not None:
        d[f"p{int(page):02d}"] = bool(rail)
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(_j.dumps(d), encoding="utf-8")
    return d


def _rail_mix_note(f, cwd, deck, page):
    """Soft (print only): this page uses the same KEY TAKEAWAYS right rail as more than half of the pages so far."""
    from ._page import BLOCKS
    if getattr(f, "speech", False) or f.appendix or getattr(f, "summary", False) or page is None or not deck:
        f._rail = None
        return
    rail = "key_takeaways" in BLOCKS
    f._rail = rail
    led = {k: v for k, v in _rail_ledger(cwd, deck).items() if k != f"p{int(page):02d}"}
    n, k = len(led) + 1, sum(1 for v in led.values() if v) + 1
    if rail and n >= 4 and k / n > RAIL_SHARE:
        print(f"P{page} 提醒（不阻塞）：右栏要点已用在 {k}/{n} 页（>{RAIL_SHARE:.0%}），版面节奏单一——这页可换一种构图："
              "左主图 + 下方拆解（上→下）、两图并排同口径、整页版式（mixed_columns_page / columns_page / kpi_charts_page），"
              "或通栏图 + 图内 callout")


_QTY_UNIT = re.compile(r"GWh|MWh|TWh|\bkWh|辆|万台|\bunits?\b|vehicles|deliveries|吨|\btons?\b|用户|users|门店|stores", re.I)


def _panel_units_differ(ex):
    """Panels headed with different kinds of unit (GWh vs US$, % vs 亿元): two metrics side by side, not one story."""
    from ._semantics import unit_kind
    kinds = set()
    for u in getattr(ex, "panel_units", None) or []:
        k = unit_kind(u) or ("q" if _QTY_UNIT.search(u) else None)
        if k:
            kinds.add(k)
    return len(kinds) >= 2


def _scale_slip(f, body, facts, cwd, deck):
    """A chart series whose values are the page's / research's own numbers × 10, 100 or 1000 (or ÷): a unit
    conversion slip (US$bn × 100 written as 亿美元 = ten times too big). Needs ≥ 2 values of the series to hit with the
    same factor and none of them stated as drawn. "" when fine."""
    if not getattr(f, "research", False):
        return ""
    years = lambda v: v.is_integer() and 1900 <= v <= 2100   # noqa: E731
    seen = re.sub(r"<[^>]+>", " ", re.sub(r"<note\b.*?</note>", "", f.title + " " + "".join(str(b) for b in body), flags=re.S))
    page_nums = {float(t_.replace(",", "")) for t_ in re.findall(r"\d[\d,]*(?:\.\d+)?", seen)}
    for d in _sync_dirs(cwd, deck):
        for md in sorted((d / "research").glob("R*.md")) if (d / "research").is_dir() else []:
            try:
                seen += " " + md.read_text(encoding="utf-8")
            except OSError:
                pass
    raw = re.findall(r"\d[\d,]*(?:\.\d+)?", seen)
    refs = {}
    for t_ in raw:
        try:
            v = float(t_.replace(",", ""))
        except ValueError:
            continue
        if v > 0 and not years(v):
            refs[v] = len(re.sub(r"^0+|\.|,", "", t_).rstrip("0") or "0")   # significant digits as written
    if not refs:
        return ""
    near = lambda a, b: abs(a - b) <= 0.006 * max(abs(a), abs(b))   # noqa: E731
    for fa in facts or []:
        if not (isinstance(fa, dict) and fa.get("kind") == "chart" and fa.get("fn") in ("columns", "lines")):
            continue
        for name, vals in fa.get("series") or []:
            vs = [float(v) for v in vals if isinstance(v, (int, float)) and v and v > 0]
            if len(vs) < 2 or any(near(v, r_) for v in vs for r_ in refs) or max(vs) <= 1:
                continue   # stated as drawn, or shares / rates stored as fractions (0.12 printed as 12%)
            for k in (10, 100, 1000, 0.1, 0.01, 0.001):
                hits = [(v, r_) for v in vs for r_ in refs if near(v, r_ * k)]
                hv = {v for v, _ in hits}
                if len(hv) >= max(2, -(-len(vs) * 3 // 5)) and any(refs[r_] >= 3 for _, r_ in hits) \
                        and any(r_ in page_nums for _, r_ in hits):   # the page itself prints the unscaled number
                    v0, r0 = hits[0]
                    kk = f"×{k:g}" if k > 1 else f"÷{1 / k:g}"
                    return (f"单位换算可能错了：图上「{name}」的值是正文/research 里同一组数的 {kk}（如图上 {fmt(v0)} ↔ 文字 {fmt(r0)}）"
                            "——检查换算系数（十亿美元→亿美元是 ×10，不是 ×100；百万→亿是 ÷100），图名单位与数值要一致")
    return ""


def _precheck(f, body, frags, ex, cwd, deck, page):
    """Problems a reader would see, caught before the page reaches the deck: chart check() issues, overflowing text
    boxes, a body that is a wall of text/numbers, more than 3 footnote lines. Holds the page back once (returns the
    fix list); a second submission of the same page goes through and the problems become review signals."""
    from ._page import SIGNALS
    out = []
    issues = getattr(ex, "_issues", None) if ex is not None else None
    if issues:
        bad = [i for i in issues if i.startswith(("出界", "超出所在面板", "文字重叠", "文字压图形", "线穿过文字", "服务端", "气泡 ", "轧差项",
                                                  "两期差异小于", "各期构成差异"))]
        rest = [i for i in issues if i not in bad]
        if bad:
            more = "" if len(bad) <= 8 else f" 等（另有 {len(bad) - 8} 处）"
            hint = ("；≥6 处说明对象太多放不下：减少类别/系列或删掉一半数值标签，比逐个挪更快" if len(bad) >= 6 else
                    "：挪开/删掉这些标签，或放大图区、减少对象")
            j = " ".join(bad)
            if "CAGR" in j or "(dim)" in j:   # never trade the argument annotation for a label
                hint += ("。CAGR 箭头保留（不要改 cagr=False 或改成手写大数字）：撞到的是柱顶数值时传 values=False 或只留首尾值，"
                         "撞到手放的 big_number / callout / 文字时删掉那个手放元素——增速已经写在箭头上")
            elif any(k_ in j for k_ in ("big_number", "%'")) and getattr(ex, "cagr_drawn", False):
                hint += "。图上已有 CAGR 箭头：删掉重复的手写大数字"
            out.append(f"图区 check：{len(bad)} 处文字读不清（{'; '.join(bad[:8])}{more}）{hint}")
        mixed = [i for i in rest if i.startswith("年度与半年")]
        if mixed and getattr(f, "research", False) and _first_hold(cwd, f"held-mixedperiod-{deck}.json", page):
            out.append(mixed[0] + "（只拦这一次）")
        rest = [i for i in rest if i not in mixed]
        if rest:
            out.append(f"图区提示：{'; '.join(rest[:2])}")
    import sys as _s
    from pathlib import Path as _P
    _s.path.insert(0, str(_P(__file__).resolve().parents[2]))
    try:
        from _exhibit_text_fit import fit_text_boxes
        _, warns = fit_text_boxes(f.page(*body))
    except Exception:  # noqa: BLE001
        warns = []
    finally:
        _s.path.pop(0)
    for w_ in warns[:6]:
        out.append(f"文字溢出：{w_}")
    out += _collisions(f, body, ex, frags)
    from ._layouts import SHORT as _SHORT
    if _SHORT and not any(o.startswith(("页面半空", "下方留白")) for o in out):
        out.append("下方留白：" + _SHORT[-1] + ("（只拦这一次）" if _first_hold(cwd, f"held-short-{deck}.json", page) else ""))
    _SHORT.clear()
    from ._layouts import SQUEEZE as _SQ
    for q_ in _SQ:   # small overflows the layout absorbed: a reminder, never a hold
        print(f"P{page} 提醒（已自动压缩）：{q_}")
    _SQ.clear()
    text = re.sub(r"<[^>]+>", " ", "".join(body) + "".join(str(x) for x in frags))
    mult = 2 if f.appendix else (getattr(f, "dense_x", None) or (1.25 if getattr(f, "summary", False) else 1))
    if getattr(f, "research", False) and not f.appendix:
        mult = max(mult, RESEARCH_DENSE_X)
    load, cap = text_load(text), int(DENSE * mult)
    speech = getattr(f, "speech", False) and not f.appendix
    if speech:   # speech deck: count only the words outside the charts
        chart = ex is not None or bool(frags) or "<chart " in "".join(body)
        load = text_load(re.sub(r"<[^>]+>", " ", "".join(b for b in body if "<chart " not in b)))
        cap = (SPEECH_SUMMARY_CAP if getattr(f, "summary", False) else SPEECH_DATA_CAP if chart else SPEECH_TEXT_CAP)
        if load > cap:
            SIGNALS.append("页面太满")
            out.append(f"页面太满（演讲型 deck）：图外正文约 {load} 字（上限 {cap}）。标题已是结论，"
                       + ("数据页只留每张图一行小标题/结论 + 图上 1–2 处标注：删掉要点栏/bullet/说明段，" if chart else
                          "每节点只留 1–3 条短 bullet，")
                       + "解释写进讲稿 note=；不缩字号")
    if speech:   # one reading direction per page: (a) two charts side by side, or (b) one line / big numbers + one chart
        from ._page import USED as _U2, LAYOUTS_USED as _LU2
        n_ch = max(len(getattr(ex, "panels", None) or []), 1) if ex is not None else 0
        n_ch = max(n_ch, len(re.findall(r"<chart\b", "".join(body))))
        layered = []
        if "kpi_charts_page" in _LU2 or ({"kpi_strip", "kpis"} & _U2 and (ex is not None or frags)):
            layered.append("大数字行叠在图表上方")
        if "key_takeaways" in _U2 or side_used(body):
            layered.append("右栏要点")
        if n_ch >= 3:
            layered.append(f"{n_ch} 张图")
        if layered:
            out.append("阅读方向混杂（演讲型 deck 每页只有一个阅读方向）：" + "、".join(layered)
                       + "——二选一：(a) 左→右只放 2 张同主题图（各一行小标题 / 结论）；(b) 上→下一行结论或 2–3 个大数字 + 1 张图；"
                         "标题已是结论，不加结论条 / 右栏")
    tables = [t for t in TABLES if t[0] > SPEECH_TABLE_MAX or t[1] > SPEECH_TABLE_MAX]
    cut = _rows_cut(f.title, [t[0] for t in TABLES], "".join(str(b) for b in body))
    TABLES.clear()
    cut_hold = bool(cut) and _first_hold(cwd, f"held-rowcut-{deck}.json", page)
    if cut_hold:   # the build dropped rows to fit the height: never silently — split, once
        out.append(cut)
    elif cut:
        SIGNALS.append("表格截行")
    from ._axes import PLOTS as _PL
    squeezed = [h_ for h_ in _PL if h_ < MIN_PLOT_H]
    tiny = [h_ for h_ in _PL if h_ < TINY_PLOT_H] if "small_multiples" not in _used() else []
    _PL.clear()
    tiny_hold = bool(tiny) and not f.appendix and _first_hold(cwd, f"held-tinyplot-{deck}.json", page)
    if tiny_hold:   # a plot strip under ~60px shows no comparison: once, then the soft note below
        out.append(f"主图压扁：绘图区只有约 {min(tiny):.0f}px 高（<{TINY_PLOT_H}px），柱/线/气泡读不出来——减块让主图占满正文高度"
                   "（删 KPI 行 / 底条 / 第二张小图，或把小面板改成右栏文字），多面板改一张图或拆 b 页（只拦这一次）")
        squeezed = []
    if squeezed and not f.appendix:   # soft: a plot under ~100px reads as a strip, its numbers cannot be compared
        out.append(f"主图过小：有 {len(squeezed)} 个图的绘图区只有约 {min(squeezed):.0f}px 高（<{MIN_PLOT_H}px），柱/线读不出差别——"
                   "减块：删掉 KPI 行 / 底条 / 第二张小图或改成右栏文字，让主图占满正文高度；多面板改成一张图或拆页")
    if speech and tables:
        out.append(f"表格偏大（演讲型 deck）：{tables[0][0]} 行 × {tables[0][1]} 列（只保留 ≤{SPEECH_TABLE_MAX}×{SPEECH_TABLE_MAX} 小表）——"
                   "对比改 ibcs_bars / dumbbell_table（只留哑铃列）/ 分组 columns，指标对目标改 bullet / target_columns 或 KPI 大数字，"
                   "清单改图标节点；保留表格就只留支撑标题的 Top 3 行、≤3 列")
    if not speech and load > cap:
        SIGNALS.append("页面太满")
        out.append(f"页面太满：正文约 {load} 字（上限 {cap}，英文 1 词≈2 字）。降密而不是缩字号：表格只留支撑标题的 3–4 列、"
                   "行数 >8 用 Top 5–6 + 其他；逐格文字改成 Harvey/Heat/✓ 图形编码；原始值改成统计量（中位数/区间/CAGR/"
                   "前 N 合计，dot_range、distribution_table）；只给主角和极值标数值；要点 ≤3 条、每条 ≤40 字且不重复图上数字；"
                   "明细移到附录或备注 note=")
    from ._page import SIGNALS as _S
    if (ex is not None or frags) and "图上无标注" in _S and _table_type_page(cwd, deck, page):
        _S[:] = [s_ for s_ in _S if s_ != "图上无标注"]   # a table / roadmap / pipeline list argues by its rows
    if (ex is not None or frags) and "图上无标注" in _S:
        from ._page import FACTS as _FA
        _fx = (getattr(ex, "facts", None) if ex is not None and getattr(ex, "facts", None) else
               (getattr(f, "_facts", None) if getattr(f, "_facts", None) is not None else _FA))
        sug = suggest_annotation(f.title, _fx)
        out.append("图上没有论证标注：按标题里的比较选——增速→标题写出 CAGR 自动画箭头；同一对象两期/同一系列两点之差→diff=(i, j)、delta="
                   "（不在两个不同对象或口径之间画差值箭头）；"
                   "目标/缺口→target=；时期→band；前 N 合计→vbracket；象限→quadrants；主角→focus=；拐点/某对象→callout。"
                   + (f"按本页标题和数据，直接这样改（数值由程序算，只加这一处即可）：{sug}" if sug else
                      "exhibit_help('<方案>') 的「标注参数」一节列出了本图能画的标注。每张图 1–2 处"))
    if ex is not None and "多图无关系" in _S:
        out.append(("多图只是并排（两图单位不同，可能是两个独立指标：真有因果/拆解再连，否则不用改）：" if _panel_units_differ(ex) else
                    "多图只是并排：") +
                   "几个面板要读成一张图——左图一行/一根柱/一段在右图展开（expand_panels + expand，或 "
                   "relate(ex, A, B, kind='drill', src=(columns结果, k))），同一时间轴（shared_time）、同一组对象（shared_rows），"
                   "或 relate(kind='arrow'/'op') 写出两图关系（导致/拆解为/×）；真的无关就拆成两页或删掉一张")
    if "CAGR 未画" in _S and (ex is not None or frags):
        out.append("CAGR 未画：标题说了年均增速/CAGR，图上要有斜向 CAGR 箭头——columns(..., cagr=(起始柱序号, 终止柱序号))（年度序列不传也会自动画，"
                   "检查是否传了 cagr=False，或数据不是按年份排列的柱图）；没有年度柱图就把标题里的增速删掉")
    miss = [s_ for s_ in _S if s_.startswith("标题数字")]
    if miss:
        off_ = getattr(f, "_title_label_off", None) or []
        out.append(f"{miss[0]}：" + (f"{off_} 已画在图上但标签被关掉（values=False / 小多图只印末值）——恢复这个数的标签或 focus= 它；"
                                     if off_ else "把它画到图上（数值标签 values=True、diff=、target=、callout）；")
                   + "不要靠删掉或改动标题里的数字过关——标题和图必须是同一个数（来自 plan/research 同一变量）；改标题数字会和别页对不上，"
                     "口径确实不同才改，并在副标题写明口径")
    side = [b for b in body if "lineSpacing=\"multiple:1.3\"" in b]   # points() columns
    if side and frags and not getattr(f, "research", False):
        nums = lambda t: set(n for n in re.findall(r"\d+(?:\.\d+)?", re.sub(r"<[^>]+>", " ", t).replace(",", ""))
                             if not (len(n) == 4 and n.startswith(("19", "20"))) and n not in ("0", "1", "2", "3"))
        sn, cn = nums("".join(side)), nums("".join(str(x) for x in frags))
        if len(sn) >= 4 and len(sn & cn) >= 0.6 * len(sn):
            out.append(f"要点栏的数字 {sorted(sn & cn)[:5]} 图上已经有了：要点改写成图上看不到的东西——原因、含义、对我方的影响，"
                       "或删掉要点栏让图占满宽度，把一句结论用 callout/takeaway 放到图上")
    if "<chart " in "".join(body) and (ex is None and not frags or "图上无标注" in _S):
        out.append("原生图表页缺带标注的 exhibit：原生图上画不了标注，同页必须再有一张带论证标注的 exhibit 图或表（纯文字表不算）——panel_heads 分两栏，"
                   "一栏 NativeChart(box=该栏)、另一栏 Exhibit 画拆解/对标/排名并加标注（见 exhibit_help('native_chart')）；"
                   "做不到就整页改用 exhibit")
    cj = re.findall(r"[\u4e00-\u9fff]+", text)[:4] if f.title and not has_cjk(f.title) else []
    if cj:   # full-width punctuation alone (：—“”) is not Chinese text
        out.append(f"英文页里有中文 {cj}：图内标签/图例/表头/来源全部改成英文（Exhibit 自动标签随 frame 标题语言）")
    if f.foot_lines > 3:
        out.append(f"脚注+来源 {f.foot_lines} 行（≤3）：口径说明移到备注 note=，来源只写机构简称")
    import re as _re2
    for m_ in _re2.finditer(r'<shape type="(?:rect|ellipse)" topLeftX="[-\d.]+" topLeftY="([-\d.]+)" width="([\d.]+)" '
                            r'height="([\d.]+)"[^>]*><fill><fillColor color="rgb\(255,255,255\)"/></fill><border color="[^"]+" '
                            r'width="2"/></shape>(.{0,900}?)</shape>', "".join(body), _re2.S):
        y_, w_, h_ = float(m_.group(1)), float(m_.group(2)), float(m_.group(3))
        txt_ = _re2.sub(r"<[^>]+>", "", m_.group(4)).strip()
        if y_ + h_ > f.top + 0.65 * (f.bottom - f.top) and w_ > 300 and txt_:   # a wide boxed sentence at the bottom
            out.append(f"结论放在页底：'{txt_[:24]}…'——结论先行，这句判断就是页标题，写进 frame 标题；底部结论框删掉，"
                       "需要的话把它改成图旁的拆解/含义栏（table_panel / points）或图上的 callout")
            break
    if frags and getattr(f, "subtitle", None) and "<chart " not in "".join(body) and not any(
            re.search(r'<shape type="(?!text")|<path|<img|<chart |<table', str(x)) for x in frags) \
            and not ({"row_table", "text_table"} & _used()):   # a table page is a table, not "text only"
        out.append("图区只有文字：这是数据页（有图表标题），图区却只有文字格——把数字画出来（row_table 加 Bar/Range/Dumbbell/Heat/Harvey 列，"
                   "或换成路由表同一比较关系的图表方案）；确实没有数字的页去掉副标题，按文字页做")
    if ex is None and not frags and "<chart " not in "".join(body) and getattr(f, "subtitle", None) \
            and "Georgia" in "".join(body) and "<table" not in "".join(body) and not ({"text_table", "row_table"} & _used()) \
            and {"kpis", "kpi_cards", "big_number"} & _used() \
            and not getattr(f, "summary", False) \
            and not f.appendix:
        out.append("只有几个数字：这是数据页（有图表标题），却只有 KPI 大数字卡、没有图——分析页要把数字画出来：时间序列用 columns/lines"
                   "（大促季节性用 layered_area(ridge=True)），占比用 donut/pie_of_pie，"
                   "对比用 row_table + Bar；KPI 卡最多作为图旁侧栏")
    kind = _page_kind()
    if kind and deck and page is not None and not _sync_dirs(cwd, deck):
        led = {k: v for k, v in _kind_ledger(cwd, deck).items() if k != f"p{int(page):02d}"}
        same = sorted(k for k, v in led.items() if v == kind)
        prev = led.get(f"p{int(page) - 1:02d}")
        if len(same) >= 3 or (prev == kind and len(same) >= 2):
            out.append(f"同类图过多：第 {', '.join(k[1:].lstrip('0') for k in same)} 页已经是{kind}，这页又是{kind}——"
                       "整稿看起来全是同一种图。按这页要比较的关系换一种：结构 → marimekko / share_bars / pie_of_pie；"
                       "两期 → dumbbell_table / slope；排名 → rank_table / bump；构成变化 → bridge / ibcs_bridge；"
                       "多对象走势 → small_multiples；集中度 → pareto；对象 × 期间 → heat_matrix")
    if ex is not None and getattr(ex, "two_bar", 0) >= 2:
        out.append(f"两根柱面板 ×{ex.two_bar}：每个面板只有 2 根柱 / 2 期（两期 / 计划 vs 实际），只是一个差值——几项'实际 vs 目标'合成一张 bullet，"
                   "'去年 → 今年'合成一张 dumbbell_table / slope（每项一行，差值自动标），或改用更长的序列（近 6–8 个季度的 ibcs_columns）")
    ph = re.findall(r"\b(?:TBD|TBC|XX+|lorem|placeholder)\b|(?<![A-Za-z\d.])X\s*(?:%|亿|万|倍)|待测算|待补充|待定|示意数据|待\s*(?:R\d|研究|调研|后续|核实|确认)\s*(?:后)?(?:补|填|更新)|\?\?",
                    text, re.I)
    if ph:
        out.append(f"占位文字：页面里还有 {sorted(set(ph))[:3]}——换成 plan/research 里的真实数字，没有就写'未披露'并删掉这项")
    if f.title and not has_cjk(f.title) and re.search(r"[A-Za-z]{3}", f.title):   # English page: no Chinese left on it
        seen_en = re.sub(r"<[^>]+>", " ", re.sub(r"<note\b.*?</note>", "", f.xml + "".join(str(b) for b in body)
                                                 + "".join(str(x) for x in frags), flags=re.S))
        note_en = " ".join(re.findall(r"<note\b.*?</note>", f.xml + "".join(str(b) for b in body), flags=re.S))
        cjk = re.findall(r"[\u4e00-\u9fff\uff08\uff09\uff1a\uff1b\uff0c\u3001\u3002]+", seen_en + " " + re.sub(r"<[^>]+>", " ", note_en))
        if cjk and _first_hold(cwd, f"held-encjk-{deck}.json", page):
            out.append(f"英文稿里有中文 / 全角标点：{sorted(set(cjk))[:4]}——来源名、标签、讲者备注都用英文与半角标点"
                       "（数据库名写英文名或删掉，'（P10）' 写成 '(P10)'）（只拦这一次）")
    prose0 = f.title + " " + " ".join(re.sub(r"<[^>]+>", " ", str(b)) for b in body)   # title, rail, notes — not the chart axis
    zeros = re.findall(r"(?:约|近|达|为|从|至|到|规模|CAGR|增速|份额|占比)\s*0(?:\.0+)?\s*(?:亿|万亿|万|%|倍|家)(?![\d.]|\s*[-–~～至]\s*\d|\s+\d+(?:\.\d+)?\s*%)", prose0)
    if len(zeros) >= 1 and _first_hold(cwd, f"held-zero-{deck}.json", page):
        out.append(f"数字是 0：{zeros[:3]}——多半是 plan 里 F 的占位没填（F['x'] = 0），页面照印成 0：从 research 变量取真实值，"
                   "没有数据就删掉这句（只拦这一次）")
    import html as _hs
    sec_ = _hs.unescape(str((getattr(f, "_kw", None) or {}).get("section") or "")).strip()
    if sec_ and getattr(f, "research", False) and not getattr(f, "full_bleed", False):
        names_ = _plan_section_names(cwd, deck)
        if names_ and sec_ not in names_ and not re.search(r"附录|appendix|术语|glossary|摘要|summary", sec_, re.I) \
                and _first_hold(cwd, f"held-section-{deck}.json", page):
            out.append(f"页眉章名「{sec_}」不在 plan 的 SECTIONS 里（{'、'.join(sorted(names_)[:6])}）——目录和导航页按 SECTIONS 编页码，"
                       "这页会对不上：frame(section=SECTIONS) 让它按页号自动取章名；真是新的一章就让 Organizer 先加进 SECTIONS（只拦这一次）")
    if getattr(f, "research", False):   # agent role names are the build team, never the reader's source / voice
        seen_r = re.sub(r"<[^>]+>", " ", re.sub(r"<note\b.*?</note>", "", f.xml + "".join(str(b) for b in body)
                                               + "".join(str(x) for x in frags), flags=re.S))
        roles_ = re.findall(r"(?<![A-Za-z])(?:Organizer|MainAgent|Builder\d?|SubAgent)(?![A-Za-z])|(?<![A-Za-z0-9])R[1-5](?=\s*(?:[–\-~/]\s*R\d|方向|view|的|调研|研究|标注))"
                            r"|(?:Organizer|Main|Lead)\s*(?:view|判断|观点)", seen_r)
        if roles_ and _first_hold(cwd, f"held-roleword-{deck}.json", page):
            out.append(f"页面上出现了做稿分工的角色名 {sorted(set(roles_))[:3]}（读者不认识）：来源写机构 / 报告名，"
                       "观点写'我们认为'或直接写判断（只拦这一次）")
    from ._marks import SIGNAL_SINGLE_PCT as _SSP
    if _SSP and getattr(f, "research", False):   # a review signal only (columns() already printed the icon_grid hint)
        SIGNALS.append("单根100%柱")
    _SSP.clear()
    unit_bad = _unit_suffix_mismatch()
    if unit_bad and _first_hold(cwd, f"held-unitsfx-{deck}.json", page):
        out.append(f"单位换算漏了：{unit_bad[0]}——按变量名的单位换算再接中文单位（千→万 ÷10、百万→亿 ÷100、十亿→亿 ×10），"
                   "或改用变量原单位写（如 “25 千台” / “$0.89B”）（只拦这一次）")
    lit = _literal_arrays()
    if lit:
        out.append(f"手打数据：页面脚本里有数字数组 {lit[:2]}——从 research/plan 变量取完整序列（如 [r['v'] for r in R1.xxx]），"
                   "手打的数会和别页对不上、也会漏掉年份")
    lost = _plan_components_missing(cwd, page, deck, body, frags, ex)
    lost_hold = bool(lost) and _first_hold(cwd, f"held-plancomp-{deck}.json", page)
    if lost_hold:
        out.append(lost)
    _rail_mix_note(f, cwd, deck, page)
    from ._page import FACTS
    facts = getattr(ex, "facts", None) if ex is not None and getattr(ex, "facts", None) else (
        getattr(f, "_facts", None) if getattr(f, "_facts", None) is not None else FACTS)
    mismatch = _title_vs_data(f.title, facts)
    slip = _scale_slip(f, body, facts, cwd, deck) if (ex is not None or frags) else ""
    if slip and _first_hold(cwd, f"held-scale-{deck}.json", page):
        out = [slip + "（只拦这一次）"] + out
    elif slip:
        SIGNALS.append("单位换算可疑")
    title_hold = False
    bubble_bad = _bubble_legend_mismatch(facts, body) if (ex is not None or frags) else ""
    bubble_hold = bool(bubble_bad) and _first_hold(cwd, f"held-bubble-{deck}.json", page)
    if bubble_hold:
        out = [bubble_bad] + out
    elif bubble_bad:
        SIGNALS.append("气泡编号与说明不符")
    from . import _layouts as _lyc
    empty = [sl for sl in _lyc.CHART_SLOTS if not _slot_filled(sl, frags)]
    _lyc.CHART_SLOTS.clear()
    if empty:
        out = [f"{len(empty)} 个图位是空的（版式留了 chart 位，却没有放图）：每个 slot 画一张 Exhibit(w=框宽, h=框高) → "
               "ex.to_slide(x=框左, y=框上)，放进 f.publish(..., frags=[...])；画不出图的栏改成 kv / text 块"] + out
    orphan = getattr(f, "_rate_orphan", None) or []
    if orphan and _first_hold(cwd, f"held-rate-{deck}.json", page):
        out = [f"标题里的增速 {orphan} 按图上的数算不出来（年数 = 年份间隔，2021→2025 是 4 年）：用程序算——标题写 "
               "f\"{(末/初)**(1/年数)-1:.0%}\"，或让 columns(cagr=(i, j)) 画箭头后照箭头上的数写（只拦这一次）"] + out
    xp = _cross_page_hold(f, body, frags, cwd, deck, page)
    if xp:   # a review signal only: Main / Organizer judge in review whether the two numbers share subject and scope
        SIGNALS.append("跨页数字不一致：" + xp.split("：", 1)[1].split("——", 1)[0][:160])
    dropped = _title_numbers_dropped(f, cwd, deck, page)
    if dropped and _first_hold(cwd, f"held-titlenum-{deck}.json", page):
        out = [dropped + "（只拦这一次）"] + out
    vague = _title_vague_numbers(f, cwd, deck, page)
    if vague and _first_hold(cwd, f"held-vague-{deck}.json", page):
        out = [vague + "（只拦这一次）"] + out
    elif vague:
        SIGNALS.append("标题数字被虚化")
    if getattr(f, "research", False):
        seen_t = f.title + " " + re.sub(r"<[^>]+>", " ", re.sub(r"<note\b.*?</note>", "", f.xml + "".join(str(b) for b in body)
                                                                + "".join(str(x) for x in frags), flags=re.S))
        jar = _build_jargon(seen_t, zh=has_cjk(f.title or ""))
        if jar and _first_hold(cwd, f"held-buildword-{deck}.json", page):
            out = [f"页面上有构建/内部用语 {jar[:4]}：读者看不懂——只改措辞、不删数据（'轴下行/利润率行'→该行的指标名如'经营利润率'，数据行照留；"
                   "'【核心】'删掉，'Watch'→'跟踪指标'，'所以呢 / So what:'→直接写含义，'R4 模型'→写成'本报告测算'或模型名），"
                   "参数名不要出现在文字里（只拦这一次）"] + out
        elif jar:
            SIGNALS.append("构建用语上页")
        gap = _coverage_gap(f, body, frags)
        if gap and gap.startswith("主图和右栏之间空出") and (_first_hold(cwd, f"held-railgap-{deck}.json", page)
                                                        or _first_hold(cwd, f"held-railgap2-{deck}.json", page)):
            out = [gap] + out   # a width bug, not a judgement call: held up to twice
        elif gap:
            SIGNALS.append("页面半空")
            print(f"P{page} 提醒：{gap}（不阻塞）")
    tie_bad = getattr(f, "_tie_bad", None) or []
    if tie_bad and _first_hold(cwd, f"held-ties-{deck}.json", page):
        out = [t + "（只拦这一次）" for t in tie_bad] + out
    elif tie_bad:
        SIGNALS.append("图文 / KPI 与图不对应")
    mark_bad = f._mark_bad if getattr(f, "_mark_bad", None) is not None else _mark_colours_missing(ex, body, frags)
    mark_msg = (f"要点标记色 {'、'.join(mark_bad)} 在图上没有同色元素：用图上对应元素的颜色（如 ex.C['good'] / 图例色 / "
                "ex.group_colors[…]），不要默认 accent（只拦这一次）") if mark_bad else ""
    mark_hold = bool(mark_bad) and _first_hold(cwd, f"held-markcolor-{deck}.json", page)
    if mark_hold:
        out = [mark_msg] + out
    elif mark_bad:
        SIGNALS.append("要点标记色不在图上")
    pct_bad = _pct_times_100(f"{f.title or ''} {re.sub(r'<[^>]+>', ' ', ''.join(map(str, body)))} "
                             f"{' '.join(re.sub(r'<[^>]+>', ' ', str(x)) for x in frags or ())}") \
        if getattr(f, "research", False) else ""
    if pct_bad and _first_hold(cwd, f"held-pct100-{deck}.json", page):
        out = [pct_bad] + out
    metric_bad = _metric_mismatch(f"{f.title or ''} {re.sub(r'<[^>]+>', ' ', ''.join(body))}", _plan_metrics(cwd, deck), page)
    metric_hold = bool(metric_bad) and _first_hold(cwd, f"held-metrics-{deck}.json", page)
    if metric_hold:   # once per page: the next submission goes through
        out = metric_bad + out
    elif metric_bad:
        SIGNALS.append("数字与 METRICS 不一致")
    if mismatch:   # held once per page (with the other items of this round); the next submission passes, flagged
        if _first_hold(cwd, f"held-title-{deck}.json", page):
            title_hold = True
            out = ["标题与图不符：" + m_ + "（只拦这一次）" for m_ in mismatch] + out
        else:
            SIGNALS.append("标题与图不符")
    if not out:
        return []
    # business-deck (speech): "同类图过多" / "只有几个数字" only warn — holding them pushed pages to KPI cards
    soft_speech = ("只有几个数字", "同类图过多") if getattr(f, "speech", False) else ()
    hard = [o for o in out if not o.startswith("多图只是并排（") and (re.match(r"\d+ 个图位是空的", o) or o.startswith(("占位文字", "只有几个数字", "文字溢出", "文字框", "图区 check", "英文页里有中文", "原生图表页",
                                            "主图和右栏之间空出", "多图只是并排", "结论放在页底", "CAGR 未画", "两根柱面板", "同类图过多")))
            and not (soft_speech and o.startswith(soft_speech))]
    if getattr(f, "full_bleed", False):   # contents / chapter navigation: no chart to annotate, no data to show
        out = [o for o in out if not o.startswith(("图上没有论证标注", "只有几个数字", "页面半空", "数据太少", "标题数字"))]
    if tiny_hold:
        hard += [o for o in out if o.startswith("主图压扁")]
    if cut_hold:
        hard += [cut]
    if lost_hold:
        hard += [lost]
    if title_hold:
        hard = [o for o in out if o.startswith("标题与图不符")] + hard
    if metric_hold:
        hard = [o for o in out if o in metric_bad] + hard
    if bubble_hold:
        hard = [bubble_bad] + hard
    if mark_hold:
        hard = [mark_msg] + hard
    hard += [o for o in out if o.endswith("（只拦这一次）") and o not in hard]   # ties / sparse / mixed periods: held once
    if any(o.startswith("标题数字") for o in out):
        SIGNALS.append("标题数字不在图上")
    m = re.search(r"正文约 (\d+) 字（上限 (\d+)", " ".join(out))
    if m and int(m.group(1)) > (1.5 if getattr(f, "speech", False) else 1.15) * int(m.group(2)):
        hard += [o for o in out if o.startswith("页面太满")]
    for o in out:   # soft items are review signals, not a reason to hold the page (each hold costs a rewrite)
        if o not in hard:
            SIGNALS.append(o.split("：")[0][:20])
            if o.startswith(("页面太满（演讲型", "表格偏大", "主图过小", "图上没有论证标注", "标题数字", "多图只是并排（") + soft_speech):
                print(f"P{page} 提醒：{o}")
    if not hard:
        return []
    import json as _j
    held = _P(cwd or ".") / ".lark-slides" / f"held-{deck}.json"   # page scripts run as fresh processes
    try:
        seen = _j.loads(held.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        seen = {}
    k = f"p{int(page):02d}"
    try:   # server blocks of the same page use up the same budget
        srv = _j.loads((_P(cwd or ".") / ".lark-slides" / f"blocked-{deck}.json").read_text(encoding="utf-8")).get(k, 0)
    except (OSError, ValueError):
        srv = 0
    if seen.get(k, 0) + srv >= 2:   # two rounds did not clear it: write it and send it to review instead of looping
        once = [h for h in hard if h.startswith("标题与图不符") or h in metric_bad or h == bubble_bad or h == mark_msg
                or h.endswith("（只拦这一次）")]
        if once:   # own one-shot budget: a single-word fix
            return once
        sticky = [h for h in hard if h.startswith("CAGR 未画")]
        if sticky and seen.get(k, 0) < 3:   # the argument is the point of the page: no pass-through
            seen[k] = seen.get(k, 0) + 1
            held.write_text(_j.dumps(seen), encoding="utf-8")
            return sticky + ["这一条不会自动放行：标题写了增速就保留年度柱让 CAGR 自动画（或删掉标题里的增速）"]
        SIGNALS.extend(h.split("：")[0][:20] for h in hard)
        return []
    seen[k] = seen.get(k, 0) + 1
    log = _P(cwd or ".") / ".lark-slides" / f"held-log-{deck}.txt"   # which checks cost rewrites (diagnosis)
    held.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "a", encoding="utf-8") as lf:
        lf.write(f"{k} {seen[k]} | " + " || ".join(h[:60] for h in hard) + "\n")
    held.write_text(_j.dumps(seen), encoding="utf-8")
    if seen[k] + srv == 2:   # last chance: the fastest fix, not another round of nudging coordinates
        hard = hard + ["这是最后一次拦截，下次提交会直接写入：不要逐个挪坐标——删掉出问题的标签/文字、减少类别或系列，"
                       "或把这页换成同一比较关系下更简单的方案（row_table + Bar/Range/Text）"]
    return hard + [f"（不阻塞，可不改）{o}" for o in out if o not in hard]


_GENERIC = {"frame", "Exhibit", "points", "panel_heads", "callout", "badge", "big_number", "kpis", "kpi_cards", "num_dot", "fmt", "tw",
            "wrap", "roles", "Label", "Text", "takeaway", "brace", "band", "vbracket", "span_bracket", "legend",
            "speech_note", "quadrants", "trend", "relate", "diamond", "missing_band", "top_n", "score_options",
            "linked_panel", "period_x", "ridge_point", "expand_panels", "expand"}


_KIND = {   # chart functions grouped by what the reader sees: same kind on many pages reads as "all bar charts"
    "columns": "柱图", "forecast_columns": "柱图", "ibcs_columns": "柱图", "stacked_columns": "柱图",
    "bars": "条形", "ibcs_bars": "条形", "share_bars": "条形",
    "lines": "折线", "trend_lines": "折线", "wbr_trend": "折线", "shared_time": "折线", "pace": "折线",
}


def _page_kind():
    from ._page import USED
    ks = [_KIND[n] for n in USED if n in _KIND]
    return max(set(ks), key=ks.count) if ks else None


def _kind_ledger(cwd, deck, page=None, kind=None):
    """Deck-wide record {page: chart kind} (page scripts run as separate processes). With page+kind: store it."""
    import json as _j
    from pathlib import Path as _P
    f = _P(cwd or ".") / ".lark-slides" / f"kinds-{deck}.json"
    try:
        d = _j.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        d = {}
    if page is not None:
        d[f"p{int(page):02d}"] = kind
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(_j.dumps(d, ensure_ascii=False), encoding="utf-8")
    return d


_PLAIN_CHARTS = {"columns", "lines", "plain_bars", "polyline", "stacked_bar", "bars", "line", "bar"}


def _right_gap(body, frags, right):
    """Empty width between the rightmost body/exhibit element and the frame's right edge."""
    xml = "".join(str(b) for b in body) + "".join(str(f_) for f_ in frags)
    boxes = [(float(x), float(w)) for x, w in re.findall(r'topLeftX="([\d.]+)"[^>]*?\bwidth="([\d.]+)"', xml)]
    lines = [(float(a), float(b_)) for a, b_ in re.findall(r'<line startX="([\d.]+)"[^>]*?endX="([\d.]+)"', xml)]
    if not (frags or any(b_ - a > 0.45 * right for a, b_ in lines)):   # only tables / exhibits, not a lone text box
        return 0.0
    ends = [x + w for x, w in boxes] + [max(a, b_) for a, b_ in lines]
    return right - max(ends) if ends else 0.0


# equivalent components: a page built with any member of the planned one's group follows the plan
_TABLE_FNS = {"row_table", "text_table", "table_block"}
_TABLE_PLAN = {"row_table", "text_table", "table_block", "table_panel", "rank_table", "variance_table", "heat_matrix",
               "dumbbell_table", "distribution_table", "kpi_spark_table"}
_TIMELINE_PLAN = {"timeline", "roadmap", "action_plan", "period_notes"}


_ANNOT_FREE = _TABLE_PLAN | _TIMELINE_PLAN | {"scorecard", "appendix", "text_table", "swot_matrix", "rank_table",
                                               "kpi_scorecard", "table_panel"}


def _table_type_page(cwd, deck, page):
    """Table-type page — the plan row's recipe is a table / roadmap / scorecard, or the page drew only table and timeline
    components (no plotted chart): the "图上没有论证标注" nudge does not apply (its argument is in the rows)."""
    from ._page import USED
    charts = USED - _GENERIC - {"kpis", "kpi_cards", "points", "exec_summary"}
    if charts and charts <= (_TABLE_FNS | {"timeline", "roadmap", "action_plan", "Range", "Harvey", "Heat", "Status",
                                           "Note", "Bar", "Spark", "Rank", "Level", "score_options", "top_n"}) \
            and not (charts & _PLAIN_CHARTS):
        return True
    if page is None:
        return False
    for d in _sync_dirs(cwd, deck):
        row = _plan_row(d / "plan.py", int(page)) or {}
        rec = str(row.get("recipe", "")).split("/")[0].strip()
        if rec:
            return rec in _ANNOT_FREE
    return False


def _table_cagr_text(text, xml=""):
    """A table page (row_table / text_table / table_block / native <table>) states the CAGR as text: no arrow is owed.
    Text = "CAGR 18.2%" / "年均 +12%" / "复合增速 9.6%", or a CAGR column (header "CAGR FY26–28" over cells "+79%":
    header and values sit in different cells, so they are not adjacent in the page text)."""
    from ._page import USED
    if not (USED & _TABLE_FNS) and "<table" not in xml and "<table" not in text:
        return False
    if re.search(r"(?:CAGR|年均(?:增速|增长|复合)?|复合增(?:速|长率?)?)[^\d]{0,8}[+−-]?\d+(?:\.\d+)?\s*%", text, re.I):
        return True
    if re.search(r"CAGR|年均|复合增", text, re.I) and re.search(r"(?<![\d.])[+−-]\d+(?:\.\d+)?\s*%", text):
        return True
    # a table-only page (no column / line chart) has nowhere to put an arrow: the year columns carry the growth and
    # the title-number note covers a CAGR printed nowhere — holding it only made pages delete the growth from the title
    return not (USED & set(_KIND))


_TEXT_RECIPES = {"appendix", "glossary", "术语", "text_table", "scorecard", "roadmap", "swot_matrix", "exec_summary", "contents", "目录", "chapter_nav",
                 "执行摘要", "封面", "cover", "agenda", "议程", "下一步", "next_steps", "review_summary", "关键数字"}


_CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"
_POINTS_NUM = re.compile(r'<shape type="text" topLeftX="[-\d.]+" topLeftY="[-\d.]+" width="22" height="22">'
                         r'<content[^>]*><p>(\d+)</p>')   # the digit box over a points() number circle


def _bubble_legend_mismatch(facts, body):
    """Bubbles numbered 1–n on the chart but the side list explains another set (e.g. bubbles 1–6, list ①②③).
    Only when the page text carries circled numbers ①… or points(numbered=True) circles; "" otherwise."""
    n = max([int(x.get("n") or 0) for x in (facts or []) if x.get("kind") == "bubble_numbers"] or [0])
    if not n:
        return ""
    xml = "".join(str(b) for b in body)
    text = re.sub(r"<[^>]+>", " ", xml)
    told = {_CIRCLED.index(ch) + 1 for ch in text if ch in _CIRCLED} | {int(m) for m in _POINTS_NUM.findall(xml)}
    told |= {int(m) for m in re.findall(r'<content[^>]*textAlign="center"[^>]*><p>(\d{1,2})</p>', xml)}   # key_takeaways circles
    told |= {int(m) for m in re.findall(r'width="18"[^>]*>\s*<content[^>]*><p>(?:<span[^>]*>)?(\d{1,2})(?:</span>)?</p>', xml)}
    if not told:
        return (f"气泡只标了编号 1–{n}，页面上没有编号说明：读者不知道 1、2、3 是谁——右栏写 key_takeaways([(名称, 说明, 1), …]) "
                "或 points(numbered=True) 逐一对应，或去掉 numbered= 直接标名称（只拦这一次）")
    if told == set(range(1, n + 1)):
        return ""
    shown = "".join(_CIRCLED[i - 1] if i <= len(_CIRCLED) else str(i) for i in sorted(told))
    return (f"气泡编号 1–{n}，说明只写了 {shown}：说明与气泡一一对应（每个气泡号在侧栏各有一条，"
            "多出的气泡删掉或补一条说明；只拦这一次）")


_COUNT_CLAIM = re.compile(r"(\d{1,3})\s*(?:个|款|项|家|条|只|种|个重点|个在研)?\s*(?:在研)?\s*(?:项目|产品|品种|管线|新药|药物|分子|"
                          r"公司|企业|标的|客户|门店|国家|市场|品牌|事件|里程碑|适应症|projects?|products?|assets?|companies|"
                          r"names|items)")


def _rows_cut(title, table_rows, body_xml=""):
    """The title counts N objects ("26 个项目") but the page's tables together list far fewer (≤ 60 % of N, ≥ 6 missing):
    rows were dropped to fit the height. Returns the split instruction (split_of + plan row), or ""."""
    if not table_rows:
        return ""
    shown = sum(table_rows) + len(re.findall(r"<tr\b", body_xml or ""))
    claims = [int(m.group(1)) for m in _COUNT_CLAIM.finditer(str(title or "")) if int(m.group(1)) >= 8]
    if not claims:
        return ""
    n = max(claims)
    if shown >= 0.6 * n or n - shown < 6:
        return ""
    from ._layouts import split_hint
    return (f"表格截行：标题说 {n} 个对象，表里只有 {shown} 行——构建时为放下高度截掉了 {n - shown} 行，读者会以为表是全量。"
            f"不静默截断：plan 加一行续页（新页 p=本页+1、split_of=本页、同表头、deps 相同），本页写前 {shown} 行、"
            f"续页写其余 {n - shown} 行；或标题改成「其中 {shown} 个重点」并在脚注写'其余 {n - shown} 个见附录/续页'。"
            + split_hint("row_table", n, shown) + "（只拦这一次）")


def _page_source():
    """Source of the running page script (its file, or the -c text kept by linecache); "" if unknown."""
    import sys as _s
    from pathlib import Path as _Pp
    try:
        main = _s.modules.get("__main__")
        fn = getattr(main, "__file__", None)
        if fn:
            return _Pp(fn).read_text(encoding="utf-8", errors="ignore")
        argv = getattr(_s, "orig_argv", None)
        if argv and "-c" in argv:
            return argv[argv.index("-c") + 1]
    except Exception:  # noqa: BLE001
        pass
    return ""


def _pct_times_100(text):
    """A '20.0%' on the page that is a research `*_pct` variable × 100, where that variable is a percent figure (0.2 =
    0.2 %) because its research module stores its other *_pct values as percents (> 1). Message, else "". The variables are the page script's globals (from research
    import *, research/Rk.py only); a module storing fractions (gm_pct = 0.12) is left alone."""
    import sys as _s
    g = {}
    for name, mod in list(_s.modules.items()):   # research/Rk.py modules the page imported; page-local values excluded
        if mod is not None and re.search(r"(?:^|\.)R\d+$", name) and "research" in str(getattr(mod, "__file__", "")):
            g.update(vars(mod))
    pcts = {n: v for n, v in g.items() if n.endswith("_pct") and isinstance(v, (int, float)) and not isinstance(v, bool)
            and v}
    if len(pcts) < 3 or sum(abs(v) > 1 for v in pcts.values()) < 0.6 * len(pcts):
        return ""
    shown = {float(m.group(1)) for m in re.finditer(r"(?<![\d.])(\d+(?:\.\d+)?)\s*%", str(text))}
    src = _page_source()
    for n, v in pcts.items():
        if not re.search(rf"\b{re.escape(n)}\b\s*\*\s*100\b", src):
            continue   # the script must scale this variable itself; an equal number from elsewhere is a coincidence
        if abs(v) <= 1 and any(abs(s - abs(v) * 100) <= max(0.051, abs(v) * 100 * 0.006) for s in shown) \
                and not any(abs(s - abs(v)) <= 0.051 for s in shown):
            return (f"量级可能错了：页上写 {abs(v) * 100:g}%，但 research 变量 {n} = {v:g} 已是百分数（该 research 文件其他 _pct 多数 > 1，"
                    f"{v:g} 即 {v:g}%）——直接写 f\"{{{n}}}%\"，不要再 ×100；确是小数比例就改名 _ratio（只拦这一次）")
    return ""


def _first_hold(cwd, fname, page):
    """True the first time `page` is held for this check (mark in <cwd>/.lark-slides/<fname>); later calls False."""
    import json as _j
    from pathlib import Path as _P
    f = _P(cwd or ".") / ".lark-slides" / fname
    try:
        seen = _j.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        seen = {}
    k = f"p{int(page):02d}"
    if seen.get(k):
        return False
    seen[k] = 1
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(_j.dumps(seen), encoding="utf-8")
    return True


_METRICS_CACHE = {}


def _plan_metrics(cwd, deck=None):
    """METRICS of the task's SYNC plan.py ({key: dict(name, unit, actual, …)}), {} when there is none. Literal dicts
    are read by AST; otherwise plan.py is run once per mtime (it may merge_metrics(M_R1, M_R2) from research files)."""
    import ast
    for d in _sync_dirs(cwd, deck):
        p = d / "plan.py"
        try:
            key = (str(p.resolve()), p.stat().st_mtime)
        except OSError:
            continue
        if key in _METRICS_CACHE:
            return _METRICS_CACHE[key]
        src = p.read_text(encoding="utf-8", errors="ignore")
        if not re.search(r"^\s*METRICS\s*=", src, re.M):
            _METRICS_CACHE[key] = {}
            return {}
        m = None
        try:
            for node in ast.parse(src).body:
                if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "METRICS" for t in node.targets):
                    m = ast.literal_eval(node.value) if isinstance(node.value, ast.Dict) else None
        except (SyntaxError, ValueError):
            m = None
        if m is None:
            import contextlib
            import io
            import runpy
            import sys as _s
            _s.path[:0] = [str(d)]
            try:
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    m = runpy.run_path(str(p), run_name="plan_metrics").get("METRICS")
            except BaseException:  # noqa: BLE001  (a broken plan must never block a page)
                m = None
            finally:
                if _s.path and _s.path[0] == str(d):
                    _s.path.pop(0)
        out = {}
        for k, v in (m or {}).items() if isinstance(m, dict) else ():
            if isinstance(v, dict) and isinstance(v.get("name"), str) and isinstance(v.get("actual"), (int, float)) \
                    and not isinstance(v.get("actual"), bool):
                out[k] = v
        _METRICS_CACHE[key] = out
        return out
    return {}


_SCALE = {"亿": 1e8, "万": 1e4, "千万": 1e7, "百万": 1e6}
_METRIC_GAP = re.compile(r"[\s:：]*(?:(?:19|20)\d{2}\s*(?:年|FY|E)?\s*)?(?:为|达|达到|实现|约|共|合计|总计|是)?\s*[:：]?\s*$")


def _scale_of(unit):
    u = str(unit or "")
    return next((s for k, s in sorted(_SCALE.items(), key=lambda kv: -len(kv[0])) if u.startswith(k)), 1.0)


def _metric_mismatch(text, metrics, page):
    """'GMV 38.6 亿' on the page vs METRICS[...].actual: exact `name` matches only, the number within 12 chars after the
    name with nothing but a year / 为 / 达 / 约 / colon between, 亿 / 万 normalised, >2% apart and not a rounding of the
    actual. Numbers that equal the target / ly / plan / a series value, or that are a growth rate (+x%, 同比…), pass."""
    out = []
    if not metrics or not text:
        return out
    t = text.replace(",", "")
    for m_ in metrics.values():
        name = m_["name"].strip()
        if len(name) < 2:
            continue
        pat = (r"(?<![A-Za-z0-9])" + re.escape(name) + r"(?![A-Za-z0-9])") if name.isascii() else re.escape(name)
        unit = str(m_.get("unit") or "")
        actual = float(m_["actual"])
        others = [float(v) for k_, v in m_.items() if k_ in ("target", "ly", "plan", "py", "budget", "prev")
                  and isinstance(v, (int, float)) and not isinstance(v, bool)]
        others += [float(v) for v in (m_.get("series") or []) if isinstance(v, (int, float)) and not isinstance(v, bool)]
        for hit in re.finditer(pat, t):
            pre = t[hit.start() - 1:hit.start()] if hit.start() else ""
            if pre and re.match(r"[一-鿿]", pre) and pre not in "的年季月期度总全及与和、为":
                continue   # '海外营收' is not '营收': only the exact metric name counts
            win = t[hit.end():hit.end() + 12]
            num = next((x for x in re.finditer(r"(?<![\d.])([+\-−]?)(\d+(?:\.\d+)?)\s*(千万|百万|亿|万)?\s*(%|pct|pp|pt|bp|倍|x)?", win)
                        if not (len(x.group(2)) == 4 and x.group(2).startswith(("19", "20")))), None)
            if not num or num.group(1) or not _METRIC_GAP.match(win[:num.start()]):
                continue
            v_txt, sc, tail = num.group(2), num.group(3), num.group(4)
            if tail and "%" not in unit and tail != unit:
                continue   # a rate / multiple of the metric — not its level
            v = float(v_txt)
            if v == 0:
                continue
            ms = _scale_of(unit)
            pv = v * (_SCALE[sc] if sc else ms)   # a bare number is read in the metric's own unit
            nd = len(v_txt.split(".")[1]) if "." in v_txt else 0

            def same(ref):
                rv = ref * ms
                return abs(pv - rv) <= 0.02 * abs(rv) or round(ref * ms / (_SCALE[sc] if sc else ms), nd) == v
            if same(actual) or any(same(o) for o in others):
                continue
            shown = f"{actual:,.4g}{unit}"
            out.append(f"第 {page} 页写的 {name} {v_txt}{sc or ''}{tail or ''} 与 plan.py 的 {shown} 不一致：数字从 METRICS 取"
                       f"（f-string 拼 METRICS 的 actual；口径确实不同就在名称里写明口径，如'{name}（单店）'）")
            break
    return out


def _literal_arrays():
    """Numeric list literals (≥3 numbers, not tick/band settings) in the page script that is calling publish."""
    import inspect
    out = []
    for fr in inspect.stack()[2:8]:
        fn = fr.filename
        if "svg_lib" in fn or not fn.endswith(".py"):
            continue
        try:
            src = inspect.getsource(fr.frame.f_code)
        except (OSError, TypeError):
            continue
        for m in re.finditer(r"(\w+\s*=\s*)?\[\s*(-?\d+(?:\.\d+)?\s*,\s*){2,}-?\d+(?:\.\d+)?\s*\]", src):
            pre = src[max(0, m.start() - 24):m.start()]
            if re.search(r"(ticks|bands|domain|ymax|ylim|xlim|xticks|yticks|range|cols|w|h)\s*=\s*$", pre + (m.group(1) or "")):
                continue
            nums = re.findall(r"-?\d+(?:\.\d+)?", m.group(0))
            if all(n.isdigit() and 1990 <= int(n) <= 2040 for n in nums):   # a year list
                continue
            out.append(m.group(0)[:40])
        break
    return out


_UNIT_SUFFIX = {"K": "千", "THOUSAND": "千", "M": "百万", "MN": "百万", "MILLION": "百万", "BN": "十亿", "B": "十亿",
                "BILLION": "十亿"}


def _unit_suffix_mismatch():
    """f"{X_K:.0f}万台" / f"{Y_BN}亿" in the calling page script: a variable whose name says thousands / millions /
    billions printed straight before 万 / 亿 with no conversion inside the braces — off by 10× / 100×."""
    import inspect
    out = []
    for fr in inspect.stack()[2:8]:
        fn = fr.filename
        if "svg_lib" in fn or not fn.endswith(".py"):
            continue
        try:
            src = inspect.getsource(fr.frame.f_code)
        except (OSError, TypeError):
            continue
        for m in re.finditer(r"\{([A-Z][A-Z0-9_]*?)_(K|M|MN|BN|B|THOUSAND|MILLION|BILLION)(?::[^{}]*)?\}\s*(万|亿)"
                             r"|\{([A-Za-z_][A-Za-z0-9_]*?)_(bn|mn|thousand|million|billion)(?::[^{}]*)?\}\s*(万|亿)", src):
            g = [x for x in m.groups() if x]
            m = type("M", (), {"group": lambda self, i, g=g, s=m.group(0): s if i == 0 else g[i - 1]})()
            out.append(f"{m.group(0)}（变量单位是{_UNIT_SUFFIX[m.group(2).upper()]}，直接接了“{m.group(3)}”）")
        break
    return out


def _lay_used():
    from ._page import LAYOUTS_USED
    return set(LAYOUTS_USED)


def _used():
    from ._page import USED
    return set(USED)


def _plan_row(path, n):
    """PAGES row n of plan.py by AST (literal fields only; f-strings / names become None)."""
    import ast
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, ValueError):
        return None
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "PAGES" for t in node.targets) \
                and isinstance(node.value, (ast.List, ast.Tuple)):
            for el in node.value.elts:
                row = _literal_row(el)
                if row and row.get("p") == n:
                    return row
    return None


def _literal_row(el):
    import ast
    pairs = []
    if isinstance(el, ast.Call) and getattr(el.func, "id", "") == "dict":
        pairs = [(k.arg, k.value) for k in el.keywords if k.arg]
    elif isinstance(el, ast.Dict):
        pairs = [(k.value, v) for k, v in zip(el.keys, el.values) if isinstance(k, ast.Constant)]
    out = {}
    for k, v in pairs:
        if k == "title" and isinstance(v, ast.JoinedStr):   # f"…{X}…": the title quotes a number from a variable
            out["_title_has_num"] = any(isinstance(p_, ast.FormattedValue) for p_ in v.values) or bool(
                re.search(r"\d", "".join(p_.value for p_ in v.values if isinstance(p_, ast.Constant) and isinstance(p_.value, str))))
        try:
            out[k] = ast.literal_eval(v)
        except ValueError:
            if isinstance(v, (ast.List, ast.Tuple)):   # deps=[R1] (bare names)
                out[k] = [getattr(e, "id", None) or getattr(e, "value", None) for e in v.elts]
            else:
                out[k] = None
    if isinstance(out.get("deps"), str):
        out["deps"] = [out["deps"]]
    return out or None


def _main_page_max(cwd, deck):
    """Last page only Main writes (3: cover, summary, contents; 2 in an older merged plan) — multiagent_sync._main_pages."""
    import sys as _s
    from pathlib import Path as _P
    dirs = [d for d in _sync_dirs(cwd, deck) if (d / "plan.py").exists()]
    if not dirs:
        return 3
    _s.path.insert(0, str(_P(__file__).resolve().parents[2]))
    try:
        from multiagent_sync import _main_pages
        return max(_main_pages(dirs[0]))
    except Exception:  # noqa: BLE001
        return 3
    finally:
        _s.path.pop(0)


_PLAN_RUN = {}


def _plan_pages_run(d):
    """PAGES of <d>/plan.py by running it (cached on mtime), or None when it does not run."""
    import contextlib, io, runpy, sys as _s
    f = d / "plan.py"
    try:
        key = (str(f), f.stat().st_mtime)
    except OSError:
        return None
    if key not in _PLAN_RUN:
        _s.path.insert(0, str(d))
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                g = runpy.run_path(str(f), run_name="plan_titles")
            _PLAN_RUN[key] = [r for r in (g.get("PAGES") or []) if isinstance(r, dict)]
        except BaseException:  # noqa: BLE001
            _PLAN_RUN[key] = None
        finally:
            if str(d) in _s.path:
                _s.path.remove(str(d))
    return _PLAN_RUN[key]


def _title_of_other_page(title, cwd, deck, page):
    """Page number whose plan title equals `title` when that is not this page's own plan title (a page script copied
    from another page with only page= changed), else None."""
    import ast
    norm = lambda s: re.sub(r"[\s\W_]+", "", str(s or "")).lower()   # noqa: E731
    t = norm(title)
    if len(t) < 6:
        return None
    for d in _sync_dirs(cwd, deck):
        rows = _plan_pages_run(d)   # evaluated: f-string titles become the text the pages print
        if rows is None:
            try:
                tree = ast.parse((d / "plan.py").read_text(encoding="utf-8"))
            except (OSError, SyntaxError, ValueError):
                continue
            rows = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign) and any(isinstance(x, ast.Name) and x.id == "PAGES" for x in node.targets) \
                        and isinstance(node.value, (ast.List, ast.Tuple)):
                    rows = [r for r in (_literal_row(e) for e in node.value.elts) if r]
        own = next((r for r in rows if r.get("p") == int(page)), None)
        if own is None or norm(own.get("title")) == t:
            continue
        hit = next((r["p"] for r in rows if r.get("p") != int(page) and norm(r.get("title")) == t), None)
        if hit is not None:
            return hit
    return None


def _title_numbers_dropped(f, cwd, deck, page):
    """business-research: the plan row's title quoted a number (f-string / digits) but the published title has none —
    a number deleted to get past a check (the claim becomes a slogan, or flips). "" when fine."""
    if not (getattr(f, "research", False) and deck and page is not None and int(page) > 3) or re.search(r"\d", f.title or "") \
            or getattr(f, "full_bleed", False):   # contents / chapter navigation: the title is the chapter name
        return ""
    for d in _sync_dirs(cwd, deck):
        row = _plan_row(d / "plan.py", int(page))
        if row and (row.get("_title_has_num") or re.search(r"\d", str(row.get("title") or ""))):
            return ("标题里的数字被删掉了：plan 这页的标题带数字，发布的标题没有——研究稿标题以关键数字开头，可在图上验证；"
                    "不要靠删数字过检查：把数画到图上（values / focus / diff= / cagr= / num_dot），口径不同就改成图上的那个数")
    return ""


def _record_held(cwd, page, me, held, deck=None):
    import fcntl
    import json
    for cl in (d / "claims.json" for d in _sync_dirs(cwd, deck) if (d / "claims.json").exists()):
        try:
            with open(cl.parent / "claims.lock", "w") as lk:
                fcntl.flock(lk, fcntl.LOCK_EX)
                allc = json.loads(cl.read_text(encoding="utf-8"))
                c = allc.get(f"p{int(page):02d}")
                if isinstance(c, dict) and me in (c.get("who"), c.get("reviewer")):
                    c["held"] = [h[:120] for h in held[:3]]
                    cl.write_text(json.dumps(allc, ensure_ascii=False, indent=1), encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass


def _record_flags(cwd, page, me, flags, deck=None):
    """Store this write's risk signals on the page's claim: next --review only checks pages that carry any."""
    from pathlib import Path
    import fcntl
    import json
    for cl in (d / "claims.json" for d in _sync_dirs(cwd, deck) if (d / "claims.json").exists()):
        try:
            with open(cl.parent / "claims.lock", "w") as lk:
                fcntl.flock(lk, fcntl.LOCK_EX)
                allc = json.loads(cl.read_text(encoding="utf-8"))
                c = allc.get(f"p{int(page):02d}")
                if isinstance(c, dict) and me in (c.get("who"), c.get("reviewer")):
                    c["flags"] = flags
                    c["written"] = c.get("written", 0) + 1   # next only closes a page that really reached the deck
                    cl.write_text(json.dumps(allc, ensure_ascii=False, indent=1), encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass


def _box(x, y, w, h, text_xml, size, color, font, bold=False, align="left", valign="top"):
    b = ' bold="true"' if bold else ""
    return (f'<shape type="text" topLeftX="{x:.0f}" topLeftY="{y:.0f}" width="{w:.0f}" height="{h:.0f}">'
            f'<content fontSize="{size}" fontFamily="{font}" color="{_c(color)}"{b} textAlign="{align}" verticalAlign="{valign}">{text_xml}</content></shape>')


_FILLER_SRC = re.compile(r"^\s*(?:(?:(?:本|我们)?(?:团队|项目组|笔者|本报告)|R\d\b).{0,14}|(?:our\s+|the\s+)?team\b.{0,20}|(?:internal|author|our)\s+(?:analysis|estimates?|model|calculations?).{0,12}|analysis|estimates?|分析|测算|估算|整理"
                         r"|内部测算)\s*$", re.I)


def _filler_source(it):
    """'团队分析' / '团队测算（情景假设）' / 'R4 单店模型': not a source a reader can check — never on the page."""
    if not isinstance(it, str):
        it = (list(it) if isinstance(it, (tuple, list)) else [it])[0] if not isinstance(it, dict) else ""
    t = re.sub(r"^(?:资料来源|来源|Source)\s*[:：]\s*", "", str(it or ""), flags=re.I)
    return bool(t) and not re.search(r"https?://", t) and bool(_FILLER_SRC.match(t))


_LINKS_CACHE = {}


def _src_entries(path):
    """(text, url) of every SRC entry of a research / data file that carries a link: strings with an http URL inside,
    tuples / dicts whose last field is a URL, and KEY / KEY_URL pairs."""
    import ast
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
    except (OSError, SyntaxError, ValueError):
        return []
    out = []
    for node in tree.body:
        if not (isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id.endswith("SRC") for t in node.targets)):
            continue
        try:
            val = ast.literal_eval(node.value) if isinstance(node.value, ast.Dict) else None
        except ValueError:
            val = None
        if not isinstance(val, dict):
            continue
        for k, v in val.items():
            if isinstance(v, dict):
                v = [x for x in v.values() if isinstance(x, (str, int))]
            if isinstance(v, (tuple, list)):
                url = next((x for x in reversed(v) if isinstance(x, str) and x.startswith(("http://", "https://"))), None)
                text = " ".join(str(x) for x in v if x not in (None, "") and x != url)
            else:
                v = str(v)
                m = re.search(r"https?://[^\s，,；;）)]+", v)
                url, text = (m.group(0), (v[:m.start()] + v[m.end():]).strip()) if m else (None, v)
                if not url and isinstance(val.get(f"{k}_URL"), str) and val[f"{k}_URL"].startswith("http"):
                    url = val[f"{k}_URL"]
            if url and text and not str(k).endswith("_URL"):
                out.append((text, url))
    return out


def _research_links(cwd, deck):
    """(text, url) of the linked SRC entries this task registered (SYNC/research/*.py, plan.py, data_common.py)."""
    from pathlib import Path as _P
    files = []
    try:
        for d in _sync_dirs(cwd, deck):
            files += sorted((d / "research").glob("*.py")) + [d / "plan.py"]
    except Exception:  # noqa: BLE001
        pass
    files += [_P(cwd or ".") / "data_common.py"]
    out = []
    for p in files:
        try:
            key = (str(p), p.stat().st_mtime)
        except OSError:
            continue
        if key not in _LINKS_CACHE:
            _LINKS_CACHE[key] = _src_entries(p)
        out += _LINKS_CACHE[key]
    return out


_REPORT_WORDS = ((r"年度业绩公告|年度业绩|全年业绩|年度报告|年报", "年报"), (r"半年度报告|半年报|中期报告|中期业绩|中报", "中报"),
                 (r"季度报告|季报", "季报"))


def _norm_src(t):
    t = re.sub(r"[\s·・,，、；;:：()（）《》<>“”\"'\-_/]+", "", str(t)).lower()
    for rx, w in _REPORT_WORDS:
        t = re.sub(rx, w, t)
    return re.sub(r"(\d)年(年报|中报)", r"\1\2", t)


def _linked(it, links):
    """A plain-text source ("中国平安2025年报") → (name, url) when a registered SRC entry with a link names it: the entry
    starts with the name (first such entry), else contains it (names ≥4 characters); years must match. One of several
    names joined by '/' links by its first part."""
    if not isinstance(it, str) or not links or re.search(r"https?://", it):
        return it
    raw = re.sub(r"^(?:资料来源|来源|Source)\s*[:：]\s*", "", it, flags=re.I)
    raw = re.split(r"\s*[/、]\s*", raw)[0]
    years = set(re.findall(r"(?:19|20)\d{2}", raw))
    core = re.sub(r"[（(][^）)]*[）)]", "", raw)
    n = _norm_src(core)
    n_wo = _norm_src(re.sub(r"(?:19|20)\d{2}(?:[-./]\d{1,2})*\s*(?:年|q[1-4]|h[12])?", "", core, flags=re.I))
    if len(n_wo) < 2:
        return it
    pre, inner = [], []
    for text, url in links:
        t = _norm_src(text)
        if not years <= set(re.findall(r"(?:19|20)\d{2}", text)):
            continue
        if t.startswith(n) or t.startswith(n_wo):
            pre.append(url)
        elif len(n_wo) >= (6 if n_wo.isascii() else 4) and (n in t or n_wo in t):   # short names: only as the lead
            inner.append(url)
    return (it, (pre or inner)[0]) if pre or inner else it


def _src_item(it, lang):
    """A source given as (name, url) or ("机构", "报告", 年份, "https://…") (plan.py SRC tuple) → short name with the URL
    laid over it as a hyperlink; a plain string stays as is."""
    if isinstance(it, str):
        m = re.search(r"https?://\S+", it)
        if not m:
            return escape(it)
        url, rest = m.group(0).rstrip("）)；;，,。"), (it[:m.start()] + it[m.end():]).strip(" ，,；;")
        org = re.split(r"[《“\"「]|\s(?:19|20)\d{2}", rest, 1)[0].strip(" ，,/") or rest[:16]
        yr = re.search(r"(19|20)\d{2}", rest[len(org):]) or re.search(r"(19|20)\d{2}", rest)
        name = (f"{org}（{yr.group(0)}）" if lang == "zh" else f"{org} ({yr.group(0)})") if yr else org
        return f'<a href="{escape(url)}">{escape(name)}</a>'
    if isinstance(it, dict):   # research SRC entries written as dicts
        g = lambda *ks: next((it[k] for k in ks if it.get(k) not in (None, "")), None)
        it = [g("org", "publisher", "source", "name", "机构"), g("title", "report", "报告"), g("year", "date", "年份"),
              g("url", "link", "链接")]
    it = list(it)
    url = it[-1] if it and isinstance(it[-1], str) and it[-1].startswith(("http://", "https://")) else None
    parts = [str(v) for v in (it[:-1] if url else it) if v not in (None, "")]
    if len(parts) >= 3:   # on the page only "机构（年份）"; the report title lives in the hyperlink / notes
        name = f"{parts[0]}（{parts[2]}）" if lang == "zh" else f"{parts[0]} ({parts[2]})"
    elif len(parts) == 2 and lang == "zh":
        name = f"{parts[0]}（{parts[1]}）"
    else:
        name = ", ".join(parts)
    return f'<a href="{escape(url)}">{escape(name)}</a>' if url else escape(name)


def image_size(path):
    """(width, height) of a PNG / JPEG / GIF / WebP file from its header bytes (standard library only), or None."""
    import struct
    try:
        with open(path, "rb") as fh:
            b = fh.read(64)
            if b[:8] == b"\x89PNG\r\n\x1a\n":
                return struct.unpack(">II", b[16:24])
            if b[:6] in (b"GIF87a", b"GIF89a"):
                return struct.unpack("<HH", b[6:10])
            if b[:4] == b"RIFF" and b[8:12] == b"WEBP":
                if b[12:16] == b"VP8X":
                    return (int.from_bytes(b[24:27], "little") + 1, int.from_bytes(b[27:30], "little") + 1)
                if b[12:16] == b"VP8L":
                    v = int.from_bytes(b[21:25], "little")
                    return ((v & 0x3FFF) + 1, ((v >> 14) & 0x3FFF) + 1)
                if b[12:16] == b"VP8 ":
                    return (struct.unpack("<H", b[26:28])[0] & 0x3FFF, struct.unpack("<H", b[28:30])[0] & 0x3FFF)
            if b[:2] == b"\xff\xd8":   # JPEG: walk the segments to the first SOFn marker
                fh.seek(2)
                while True:
                    m = fh.read(2)
                    if len(m) < 2 or m[0] != 0xFF:
                        return None
                    if m[1] in (0xD8, 0x01) or 0xD0 <= m[1] <= 0xD7:
                        continue
                    ln = struct.unpack(">H", fh.read(2))[0]
                    if 0xC0 <= m[1] <= 0xCF and m[1] not in (0xC4, 0xC8, 0xCC):
                        h, w = struct.unpack(">HH", fh.read(5)[1:5])
                        return (w, h)
                    fh.seek(ln - 2, 1)
    except (OSError, struct.error):
        return None
    return None


_LOGO = {}   # the deck's brand logo, set once (set_logo / first frame(logo=)) and drawn on every later page


def _logo_box(ratio=None, size=None):
    """(w, h) of the top-right logo: 32px high, width from the logo's own aspect ratio (never cropped); long
    wordmarks cap at 200px wide with the height shrunk to keep the ratio."""
    if size:
        return size
    r_ = ratio
    if isinstance(r_, str):
        sz_ = image_size(r_)
        r_ = sz_[0] / sz_[1] if sz_ and sz_[1] else None
    if not r_:
        raise ValueError("logo 需要原图宽高比，否则会被裁成一半：传 logo_ratio=\"<本地 logo 图片路径>\"（或 宽/高 数值）")
    r_ = float(r_)
    lh = 32.0
    lw = lh * r_
    if lw > 200:
        lw, lh = 200.0, 200.0 / r_
    if lw < 32 and r_ < 1:   # a tall logo: keep it inside the 32px band
        lw, lh = 32.0 * r_, 32.0
    return round(lw, 1), round(lh, 1)


def _task_root(cwd=None):
    """The task folder: cwd if given, else the working dir — or, for a page script run from inside the task's own
    .lark-slides/… tree (e.g. a SYNC dir), the folder that holds that .lark-slides. Never a parent folder beyond it."""
    import os as _os
    from pathlib import Path
    if cwd:
        return Path(cwd).resolve()
    here = Path(_os.getcwd()).resolve()
    if ".lark-slides" in here.parts:
        return Path(*here.parts[:here.parts.index(".lark-slides")])
    if here.name in ("SYNC", "sync") and (here / "claims.json").exists() | (here / "status.json").exists():
        return here.parent
    if not (here / ".lark-slides").exists():   # run from elsewhere (the skill folder) with the task's SYNC dir on sys.path
        import sys as _s
        for p_ in _s.path:
            d_ = Path(p_ or ".")
            for cand in (d_, d_.parent):
                if cand.name in ("sync", "SYNC") and ".lark-slides" in cand.parts and (cand / "status.json").exists():
                    return Path(*cand.parts[:cand.parts.index(".lark-slides")])
    return here


def _resolve_deck(deck=None, cwd=None):
    """The deck a frame / logo call belongs to: the one passed, else the deck of the multi-agent task running in cwd
    (SYNC/deck.txt of a live task), else None. Never "the last deck seen in this folder"."""
    if deck:
        from ..atomize_svg_to_slide._exhibit_publish import _deck_id
        return _deck_id(deck)
    from ..atomize_svg_to_slide._exhibit_publish import _task_deck
    return _task_deck(_task_root(cwd))


def _logo_file(cwd=None, deck=None):
    from ..atomize_svg_to_slide._exhibit_publish import deck_dir
    return deck_dir(_task_root(cwd), deck) / "logo.json"


def _load_logo(cwd=None, deck=None):
    """Fill _LOGO from this deck's .lark-slides/decks/<deck>/logo.json (written by set_logo): every page script is its
    own process, so the logo set once by one agent reaches all pages of that deck — and only that deck."""
    import json as _j
    deck = _resolve_deck(deck, cwd)
    if _LOGO and (not deck or _LOGO.get("deck") in (None, deck)):
        return _LOGO if deck or _LOGO.get("deck") is None else {}
    _LOGO.clear()   # cached for another deck
    if not deck:
        return _LOGO
    try:
        d = _j.loads(_logo_file(cwd, deck).read_text(encoding="utf-8"))
        if d.get("token") and float(d.get("w") or 0) > 0 and float(d.get("h") or 0) > 0:
            _LOGO.update(token=str(d["token"]), box=(float(d["w"]), float(d["h"])), deck=deck)
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return _LOGO


_DECK_PAL = {}   # the deck's palette (set_palette), cached per process: {"deck": id, "pal": name or dict}
LAST_DECK = [None]   # deck of the last frame() in this process: Exhibit() (no deck arg) reads that deck's palette


def _palette_file(cwd=None, deck=None):
    from ..atomize_svg_to_slide._exhibit_publish import deck_dir
    return deck_dir(_task_root(cwd), deck) / "palette.json"


def set_palette(pal, cwd=None, deck=None):
    """Record this deck's palette once (a PALETTES name, or a palette dict such as a copy with the brand colour as
    accent / brand_palette(...)) in <cwd>/.lark-slides/decks/<deck>/palette.json: every later frame() / Exhibit() of
    this deck that passes no palette= uses it, so page scripts and subagents need not pass it. Another deck in the same
    folder never inherits it. An explicit palette= still wins."""
    import json as _j
    deck = _resolve_deck(deck, cwd)
    if not deck:
        raise ValueError("set_palette 需要 deck=<xml_presentation_id>（配色按 deck 记录，不同 deck 互不继承）")
    if not pal or not isinstance(pal, (str, dict)):
        raise ValueError("set_palette 的 pal 是 PALETTES 里的名字或一份配色 dict")
    roles(pal)   # unknown names / malformed dicts fail here, not on a later page
    from ._palette import luminance as _lum, _hex as _hx
    from ..svg_palettes import PALETTES as _PALS
    p_ = _PALS.get(pal) if isinstance(pal, str) else pal
    bg_ = (p_ or {}).get("bg") if isinstance(p_, dict) else None
    if bg_ and is_research(cwd, deck):
        try:
            dark_ = _lum(_hx(str(bg_))) < 0.2
        except (ValueError, TypeError):
            dark_ = False
        if dark_:   # research pages are white: a dark palette's light ink and fills vanish on them
            light = [k for k, v in _PALS.items() if isinstance(v, dict) and v.get("bg") and "exhibit" in v][:8]
            raise ValueError(f"{pal if isinstance(pal, str) else '这份配色'} 是深底色系，研究稿页面是白底，浅色文字和填充会看不见："
                             f"换一个浅底色系（如 {', '.join(light)}）；品牌色用 brand_palette(…) 生成")
    f = _palette_file(cwd, deck)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(_j.dumps({"palette": pal}, ensure_ascii=False), encoding="utf-8")
    _DECK_PAL.clear()
    _DECK_PAL.update(deck=deck, pal=pal)
    return {"deck": deck, "palette": pal if isinstance(pal, str) else "dict", "file": str(f)}


def deck_palette(cwd=None, deck=None):
    """The palette recorded with set_palette for this deck (name or dict), or None."""
    import json as _j
    deck = _resolve_deck(deck, cwd) or LAST_DECK[0]
    if not deck:
        return None
    if _DECK_PAL.get("deck") == deck:
        return _DECK_PAL.get("pal")
    try:
        pal = _j.loads(_palette_file(cwd, deck).read_text(encoding="utf-8")).get("palette")
    except (OSError, ValueError, AttributeError):
        pal = None
    _DECK_PAL.clear()
    _DECK_PAL.update(deck=deck, pal=pal)
    return pal


PROFILE_FILE = "style"   # .lark-slides/decks/<deck>/style — "research" here, "keynote" from upload_images.py


def set_profile(name, cwd=None, deck=None):
    """Single-agent business-research decks: set_profile("research", cwd=CWD, deck=<deck>) once (multi-agent strategy
    tasks are detected from SYNC without it); set_profile("deck") turns on the speech limits (see is_speech). Research pages get the reading-deck limits: body-text load ×RESEARCH_DENSE_X,
    prose blocks down to RESEARCH_PT (tables / rail evidence / kv / notes), footnotes up to RESEARCH_FOOT_LINES lines."""
    deck = _resolve_deck(deck, cwd)
    if not deck:
        raise ValueError("set_profile 需要 deck=<xml_presentation_id>")
    if name not in ("research", "deck"):
        raise ValueError("set_profile 只接受 'research'（business-research 阅读型）或 'deck'（business-deck 演讲型）")
    from ..atomize_svg_to_slide._exhibit_publish import deck_dir
    f = deck_dir(_task_root(cwd), deck) / PROFILE_FILE
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(name, encoding="utf-8")
    return {"deck": deck, "profile": name, "file": str(f)}


def _sync_flow(d):
    """Flow of a multi-agent SYNC dir: flow.txt, else status.json task_flow, else its .lark-slides/<kind>/ folder."""
    import json as _j
    try:
        t = (d / "flow.txt").read_text(encoding="utf-8").strip()
        if t:
            return t
    except OSError:
        pass
    try:
        t = _j.loads((d / "status.json").read_text(encoding="utf-8")).get("task_flow")
        if t:
            return str(t)
    except (OSError, ValueError, AttributeError):
        pass
    kind = d.parents[1].name if len(d.parents) > 1 else ""
    return {"strategy": "strategy"}.get(kind, "")


def is_research(cwd=None, deck=None):
    """True for a business-research deck: set_profile("research") on this deck, or the deck's multi-agent task runs the
    strategy flow (the business-research flow). business-deck / keynote / other decks → False."""
    from ..atomize_svg_to_slide._exhibit_publish import deck_dir, sync_deck
    root = _task_root(cwd)
    if deck:
        try:
            if (deck_dir(root, deck) / PROFILE_FILE).read_text(encoding="utf-8").strip() == "research":
                return True
        except OSError:
            pass
    try:
        dirs = _sync_dirs(root, deck)
    except Exception:  # noqa: BLE001
        return False
    owned = [d for d in dirs if deck and sync_deck(d) == str(deck)] or dirs
    flows = {_sync_flow(d) for d in owned}
    return flows == {"strategy"}


def is_speech(cwd=None, deck=None):
    """True for a speech deck: set_profile("deck") on this deck. Speech pages: chart full width (body_w without rail), off-chart text ≤ SPEECH_DATA_CAP on data
    pages and ≤ SPEECH_TEXT_CAP elsewhere, big tables flagged."""
    from ..atomize_svg_to_slide._exhibit_publish import deck_dir
    root = _task_root(cwd)
    if deck:
        try:
            if (deck_dir(root, deck) / PROFILE_FILE).read_text(encoding="utf-8").strip() == "deck":
                return True
        except OSError:
            pass
    return False


def set_logo(file_token, ratio, cwd=None, deck=None, variant=None):
    """Brand decks: call once after uploading the ORIGINAL (uncropped) logo — every later frame() of this deck draws it
    top right, and logo_xml() gives the same box for hand-written pages. ratio: local logo path or w/h. Saved to
    <cwd>/.lark-slides/decks/<deck>/logo.json (deck: the xml_presentation_id; in a multi-agent task it defaults to the
    task's deck), so every later page script of that deck picks it up, and publish_slide(page=N) refuses its pages that
    miss it (logo_missing / logo_cropped). Another deck in the same folder never inherits it.
    variant="light" (any name): register an extra official variant of the same logo (e.g. the white version for dark
    covers) — stored under "variants" in logo.json, placed with logo_xml(..., variant="light"); a page carrying any
    registered variant counts as having the logo. The default logo frame() draws is unchanged."""
    import json as _j
    deck = _resolve_deck(deck, cwd)
    if not deck:
        raise ValueError("set_logo 需要 deck=<xml_presentation_id>（logo 按 deck 记录，不同 deck 互不继承）")
    f = _logo_file(cwd, deck)
    try:
        old = _j.loads(f.read_text(encoding="utf-8"))
        old = old if isinstance(old, dict) else {}
    except (OSError, ValueError):
        old = {}
    lw, lh = _logo_box(ratio)
    entry = {"token": str(file_token), "w": lw, "h": lh, "ratio": round(lw / lh, 4)}
    variants = dict(old.get("variants") or {})
    if variant and variant != "default":
        variants[str(variant)] = entry
        data = dict(old, variants=variants)
        if not old.get("token"):   # no main logo yet: the variant doubles as the default
            data.update(entry)
    else:
        data = dict(entry, **({"variants": variants} if variants else {}))
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(_j.dumps(data), encoding="utf-8")
    _LOGO.clear()
    _LOGO.update(token=str(data["token"]), box=(float(data["w"]), float(data["h"])), deck=deck)
    return dict(_LOGO, file=str(f), **({"variant": str(variant)} if variant else {}))


def _logo_variant(cwd, deck, variant):
    """(token, (w, h)) of a registered logo variant of this deck, or None."""
    import json as _j
    deck = _resolve_deck(deck, cwd)
    if not deck:
        return None
    try:
        v = (_j.loads(_logo_file(cwd, deck).read_text(encoding="utf-8")).get("variants") or {}).get(str(variant)) or {}
        if v.get("token") and float(v.get("w") or 0) > 0 and float(v.get("h") or 0) > 0:
            return str(v["token"]), (float(v["w"]), float(v["h"]))
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return None


def logo_xml(x=None, y=None, cwd=None, deck=None, variant=None):
    """This deck's logo (set_logo) as a native <img> at the frame's top-right slot — paste into hand-written page XML so
    every page carries it. Width:height equals the original, so the server never crops it. "" when the deck has no logo.
    variant="light": the variant registered with set_logo(..., variant="light") (e.g. white logo on a dark cover)."""
    if variant and variant != "default":
        got = _logo_variant(cwd, deck, variant)
        if not got:
            raise ValueError(f"logo 变体 {variant!r} 未登记：先 set_logo(<file_token>, <原图路径>, cwd=CWD, deck=<deck>, "
                             f"variant={variant!r})")
        tok, (lw, lh) = got
    else:
        if not _load_logo(cwd, deck):
            return ""
        tok, (lw, lh) = _LOGO["token"], _LOGO["box"]
    x = W - X0 - lw if x is None else x
    y = 18 + (32 - lh) / 2 if y is None else y
    return f'<img src="{escape(tok)}" topLeftX="{x:.1f}" topLeftY="{y:.1f}" width="{lw}" height="{lh}"/>'


def _slot_filled(slot, frags):
    """Some fragment draws inside this slide box (x, y, w, h)."""
    x, y, w, h = slot
    for fr in frags or ():
        for a, b in re.findall(r'topLeftX="([-\d.]+)" topLeftY="([-\d.]+)"', str(fr)):
            if x - 4 <= float(a) <= x + w + 4 and y - 4 <= float(b) <= y + h + 4:
                return True
    return False


def project_root(cwd):
    """A cwd inside .lark-slides (a plan.py that sets CWD = its task / SYNC dir, then `from plan import *` overrides the
    page script's own CWD) means the project root above it — the deck registry and task binding live there."""
    if cwd and ".lark-slides" in str(cwd).replace("\\", "/").split("/"):
        from pathlib import Path as _Pc
        parts = _Pc(cwd).resolve().parts
        return str(_Pc(*parts[:parts.index(".lark-slides")]))
    return cwd


def _plan_row_section(cwd, deck, page):
    """section= of this page's PAGES row in the task's plan.py ("" when none / no task)."""
    try:
        for d in _sync_dirs(cwd, _resolve_deck(deck, cwd)):
            row = _plan_row(d / "plan.py", int(page)) or {}
            if isinstance(row.get("section"), str):
                return row["section"].strip()
    except Exception:  # noqa: BLE001
        pass
    return ""


def _plan_section_names(cwd, deck):
    """Chapter names of the task's plan.py SECTIONS (set()), evaluated like the page titles."""
    import contextlib, io, runpy, sys as _s
    for d in _sync_dirs(cwd, deck):
        f = d / "plan.py"
        if not f.exists():
            continue
        try:
            key = ("sections", str(f), f.stat().st_mtime)
        except OSError:
            continue
        if key not in _PLAN_RUN:
            _s.path.insert(0, str(d))
            try:
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    g = runpy.run_path(str(f), run_name="plan_sections")
                sec = g.get("SECTIONS") or {}
                _PLAN_RUN[key] = {str(v).strip() for v in sec.values()} if isinstance(sec, dict) else set()
            except BaseException:  # noqa: BLE001
                _PLAN_RUN[key] = set()
            finally:
                if str(d) in _s.path:
                    _s.path.remove(str(d))
        return _PLAN_RUN[key]
    return set()


def align_sections(sections, pages):
    """SECTIONS {start page: chapter} re-anchored on PAGES rows: a chapter named in a row's section= starts at the first
    row that names it (the row is the page itself; a hand-typed SECTIONS start one page off shifted every page range
    and header). Chapters no row names keep their SECTIONS start."""
    if not isinstance(sections, dict) or not pages:
        return sections
    rows = [dict(v, p=k) if isinstance(v, dict) else v for k, v in pages.items()] if isinstance(pages, dict) else pages
    first, named = {}, {}
    for r in rows or []:
        if isinstance(r, dict) and isinstance(r.get("section"), str) and str(r.get("p", "")).isdigit():
            first.setdefault(r["section"].strip(), int(r["p"]))
            named[int(r["p"])] = r["section"].strip()
    out = {}
    for k, v in sections.items():
        nm, k_ = str(v).strip(), int(k) if str(k).isdigit() else k
        f_ = first.get(nm)
        # move only when a row says so: an earlier row already names this chapter, or the pages from the SECTIONS start
        # up to the first named row are named for another chapter (a nav page without section= is the chapter start)
        if isinstance(k_, int) and f_ is not None and (f_ < k_ or any(named.get(q) not in (None, nm) for q in range(k_, f_))):
            k_ = f_
        out[k_] = v
    if len(out) != len(sections):   # two chapters landed on one page: the plan is ambiguous, keep it as written
        return sections
    return type(sections)(sorted(out.items(), key=lambda t: int(t[0]) if str(t[0]).isdigit() else 0))


class Sections(dict):
    """SECTIONS = Sections({4: "一、市场", 9: "二、竞争"}): SECTIONS[7] gives the chapter page 7 falls in ("一、市场")."""

    def __missing__(self, page):
        starts = sorted((int(k), v) for k, v in self.items() if str(k).isdigit() and int(k) <= int(page))
        if not starts:
            raise KeyError(page)
        return starts[-1][1]


_TEAM_FILLER = re.compile(r"\s*(?:与|和|及)?\s*(?:本|我们)?团队(?:测算|分析|估算|判断|假设|整理)(?=[\s；;，,。）)]|$)")


def _drop_team_filler(text):
    """Remove "团队测算 / 团队判断"-style filler from a subtitle clause by clause: "2026E 为管理层目标与团队测算" keeps
    "2026E 为管理层目标"; a clause left dangling on a verb ("档位为团队判断" → "档位为") goes as a whole, with an
    empty bracket pair it leaves behind — never a cut-off "…，档位为）"."""
    out = []
    for part in re.split(r"([；;，,（()）])", text):
        if part and _TEAM_FILLER.search(part):
            rest = _TEAM_FILLER.sub("", part).rstrip()
            part = "" if not rest.strip() or re.search(r"(?:为|是|按|由|来自|系|基于|据)$", rest) else rest
        out.append(part)
    s = "".join(out)
    for _ in range(3):
        s = re.sub(r"[；;，,]\s*(?=[）)；;，,]|$)", "", s)   # a separator left before a closer / another separator
        s = re.sub(r"(?<=[（(])\s*[；;，,]\s*", "", s)
        s = re.sub(r"[（(]\s*[）)]", "", s)
    return s.strip(" ；;，,")


def frame(title, subtitle=None, source=None, notes=None, page=None, section=None, palette=None,
          font="思源黑体", note=None, lang=None, logo=None, logo_size=None, logo_ratio=None, sample=None, deck=None, cwd=None,
          chart_title=None, **_ignored):
    """Title = the page's point of view (a judgement, not a description), 22pt bold (20pt if that fits one line; 2
    lines max, longer raises), top-aligned so every page's title starts at the same height. Below it the grey rule.
    subtitle = the chart title ("**指标名，**单位"), drawn in dark bold-lead text UNDER the rule above the chart; pages
    without a chart pass no subtitle. Section tag (11pt accent, top LEFT above the title, read first), page number,
    footnotes + source (10pt, bottom). logo: file_token of the company logo (slides +media-upload) drawn top RIGHT,
    32px high and as wide as its own aspect ratio (never cropped): pass logo_ratio="<local image path>" (or w/h);
    logo_size=(w, h) forces a box. The first logo= is remembered (or call set_logo once): later frames draw it on
    every page without passing it again. Upload the original logo, uncropped.

    source: list of sources (or one string). Each item: short name string "机构（年份）", or (name, url), or a plan.py SRC
    tuple ("机构", "报告", 年份, "https://…") — the name is shown and the URL laid over it as a hyperlink (no raw URL
    text). Rendered as one line "来源：A；B" (zh) / "Source: A; B" (en); "团队分析" / "R4 模型"-style items are dropped (not a checkable source) and a plain name that matches a linked SRC entry of the task's research files gets that link. lang defaults to the
    title's language. note: speaker notes text (goes to <note>). Returns Frame: f.xml, f.top / f.bottom (free body
    band), f.left / f.right, f.page(*body_xml) -> slide XML.
    sample=True (illustrative / made-up numbers): the source line becomes "示例测算（参照：A、B）" on one line (long
    reference lists are cut first) and a "示例数据" tag sits in the footer next to the page number on every page.
    sample=None (default) turns it on when notes / a source item already say 示例数据 / 示例测算, or this deck has
    .lark-slides/decks/<deck>/sample.flag (or its task's SYNC/sample.flag).
    deck / cwd: the deck this page goes to (xml_presentation_id) and the task folder — the deck's logo and sample flag
    are read from it. In a multi-agent task deck defaults to the task's deck; f.publish(deck=…) rebuilds a frame made
    without one.
    """
    subtitle = subtitle or chart_title
    if subtitle:   # "…；2026E 为管理层目标与团队测算": the filler belongs in no visible line
        subtitle = _drop_team_filler(str(subtitle))
    cwd = project_root(cwd)
    if isinstance(section, dict) and page is not None:   # the plan row of this page names its chapter: that wins
        own = _plan_row_section(cwd, deck, page)
        if own and own in {str(v).strip() for v in section.values()}:
            section = own
    if isinstance(section, dict):   # section=SECTIONS: the chapter this page falls in (last chapter start ≤ page)
        starts = sorted((int(k), v) for k, v in section.items() if page is None or int(k) <= int(page))
        section = starts[-1][1] if starts else None
    _kw = dict(title=title, subtitle=subtitle, source=source, notes=notes, page=page, section=section, palette=palette,
               font=font, note=note, lang=lang, logo=logo, logo_size=logo_size, logo_ratio=logo_ratio, sample=sample)
    deck = _resolve_deck(deck, cwd)

    if re.search(r"[~≈]\s*[$€¥£]?\s*(?=[A-Za-z\u4e00-\u9fff]|$)|[$€¥£]\s*(?![\d.])|约\s*(?=亿|万|元|%)|\{[^}]*\}|\bNone\b|\bnan\b", title):
        raise ValueError(f"标题里有空缺的数字占位（{title[:40]}…）：f-string 的值没拼上，或写了 ~$ / {{}} / None——先在 plan.py 补上数字")
    m_note = re.search(r"示例|未设定|未测算|未披露|占位", title)
    if m_note:   # "（示例数据）" / "（预算未设定）" in titles: status notes crowd out the message
        raise ValueError(f"标题里不写'{m_note.group(0)}'：示例声明由 sample=True / sample.flag 统一放页脚；"
                         "'未设定 / 未披露 / 未测算'这类口径说明写进 notes= 或页脚来源，标题只写结论")
    LAST_DECK[0] = deck
    dpal = deck_palette(cwd, deck)
    if palette and dpal and palette != dpal and (is_speech(cwd, deck) or is_research(cwd, deck)):   # one palette per deck
        print(f"提醒：本 deck 已 set_palette，frame(palette={palette if isinstance(palette, str) else 'dict'!r}) 改用 deck 的配色"
              "（全稿一套色；不要另传 palette=）")
        palette = dpal
    palette = palette or dpal
    set_default(palette)
    C = roles(palette)
    ink, sub = C["ink"], C["sub"]
    lang = lang or ("zh" if has_cjk(title) else "en")
    global LAST_LANG, LAST_TITLE, LAST_SUBTITLE, LAST_NOTES
    LAST_LANG, LAST_TITLE, LAST_SUBTITLE = lang, title, subtitle or ""
    LAST_NOTES = " ".join(str(x) for x in ([notes] if isinstance(notes, str) else list(notes or []))
                          + ([source] if isinstance(source, str) else [str(x) for x in (source or [])]))
    if _LOGO and _LOGO.get("deck") and _LOGO.get("deck") != deck:   # set for another deck earlier in this process
        _LOGO.clear()
    if not logo and logo is not False:
        _load_logo(cwd, deck)
    if logo:
        lw, lh = _logo_box(logo_ratio, logo_size)
        if not _LOGO:
            _LOGO.update(token=str(logo), box=(lw, lh))
    elif _LOGO and logo is not False:
        logo, (lw, lh) = _LOGO["token"], _LOGO["box"]
    else:
        lw, lh = 0, 0
    tw_max = W - 2 * X0 - (lw + 16 if logo else 0)
    if sample is None:   # a page that already calls its numbers 示例 gets the full treatment (no real org as "source")
        said = " ".join(str(x) for x in ([notes] if isinstance(notes, str) else list(notes or []))
                        + ([source] if isinstance(source, str) else [str((list(it) if isinstance(it, (tuple, list)) else [it])[0])
                                                                     for it in (source or []) if not isinstance(source, str)]))
        sample = bool(re.search(r"(?:^|[\s；;，,（(])示例(?:数据|测算)", said)) or _sample_flag(cwd, deck)
    size = 22
    from ._page import lint_w

    def _wrap_srv(t_, s_, w_):   # wrap so every line also fits by the server's (≈10% wider) estimate — otherwise the
        for k_ in range(12):      # lint wraps a "2-line" title into 3, grows the box and the rule cuts through it
            ls_ = wrap(t_, s_, w_ * (1 - 0.03 * k_), bold=True)
            if all(lint_w(l_, s_, True) <= w_ + 20 for l_ in ls_):
                return ls_
        return ls_
    lines = _wrap_srv(title, size, tw_max - 24)
    if len(lines) == 2 and len(_wrap_srv(title, 20, tw_max - 24)) == 1:
        size, lines = 20, _wrap_srv(title, 20, tw_max - 24)
    if len(lines) > 2:
        raise ValueError(f"标题超过两行（{len(lines)} 行）：缩短到 ≤{int((tw_max - 24) * 2 / 22)} 个汉字左右，细节放副标题")
    th = 36 * len(lines)
    ty = 34 if section else 20
    parts = []
    if section:
        parts.append(_box(X0, 14, tw_max, 18, f"<p>{escape(section)}</p>", 11, C["accent"], font, bold=True))
    title_p = "".join(f"<p>{escape(t)}</p>" for t in lines)
    try:   # the server sizes the title with its own estimator (default line spacing 1.5): publish grows the box to that
        import sys as _s   # height, so a rule placed by our 36px/line guess ends up through the second line (40 blocks
        from pathlib import Path as _P   # "line crosses title" in one run). Measure it the server's way, at 1.2 spacing.
        _s.path.insert(0, str(_P(__file__).resolve().parents[2]))
        from _exhibit_text_fit import text_height
        th = max(th, text_height(f'<content fontSize="{size}" fontFamily="{font}" bold="true" lineSpacing="multiple:1.2">'
                                 f"{title_p}</content>", width=tw_max, font_size=size) - 2)
    except Exception:  # noqa: BLE001
        pass
    finally:
        _s.path.pop(0)
    parts.append(_box(X0, ty, tw_max, th + 2, title_p, size, ink, font, bold=True, valign="top")
                 .replace(' verticalAlign="top">', ' verticalAlign="top" lineSpacing="multiple:1.2">', 1))
    if logo:
        parts.append(f'<img src="{escape(str(logo))}" topLeftX="{W - X0 - lw}" topLeftY="{18 + (32 - lh) / 2:.1f}" '
                     f'width="{lw}" height="{lh}"/>')
    y = ty + th + 2 + (8 if len(lines) == 2 else 4)   # rule below the server-measured title box
    parts.append(f'<line startX="{X0}" startY="{y + 4}" endX="{W - X0}" endY="{y + 4}"><border color="{_c(C["grid"])}" width="1"/></line>')
    y += 14
    if subtitle:
        subtitle = subtitle.replace("**", "")
        comma = "，" if lang == "zh" else ", "
        head, sep, rest = subtitle.partition(comma)
        sx = (f'<p><span bold="true" color="{_c(ink)}">{escape(head + comma.strip() if lang == "zh" else head + ",")}</span>'
              f'{escape(rest if lang == "zh" else " " + rest)}</p>' if sep and len(head) <= 28
              else f'<p><span bold="true" color="{_c(ink)}">{escape(subtitle)}</span></p>')
        parts.append(_box(X0, y, W - 2 * X0, 22, sx, 14, C["text"], font))
        y += 28
    top = y
    foot = []
    for n in ([notes] if isinstance(notes, str) else notes or []):
        foot.append(escape(str(n)))
    fw = W - 2 * X0 - 60 - (_SAMPLE_W if sample else 0)   # footer text width (the sample tag sits at its right end)
    sample_src = None
    if source or sample:
        items = ([source] if isinstance(source, (str, tuple)) else list(source)) if source else []
        def _split_src(t):   # "A；B；团队测算" in one string: split at top level (never inside "示例测算（参照：A；B）")
            if not isinstance(t, str) or re.search(r"https?://", t):
                return [t]
            out_, depth, cur = [], 0, ""
            for ch in re.sub(r"^(?:资料来源|来源|Source)\s*[:：]\s*", "", t):
                depth += ch in "（("
                depth -= ch in "）)"
                if ch in "；;" and depth <= 0:
                    out_.append(cur.strip())
                    cur = ""
                else:
                    cur += ch
            return [x for x in out_ + [cur.strip()] if x]
        items = [x for it in items for x in _split_src(it)]
        items = [it for it in items if not _filler_source(it)]
        links = _research_links(cwd, deck)
        names = list(dict.fromkeys(_src_item(_linked(it, links), lang) for it in items))   # same org cited twice: once
        if deck and page is not None and not sample:   # every page's sources, for the appendix's source list
            try:
                from ._glossary import record_sources
                record_sources(cwd, deck, page, [re.sub(r"<[^>]+>", "", n_) for n_ in names])
            except Exception:  # noqa: BLE001
                pass
        if sample:   # illustrative numbers: real institutions are only the reference, never "the source"
            strip = r"^(?:资料来源|来源|Source)\s*[:：]\s*|^(?:示例测算|示例数据|Illustrative(?: estimate)?)\s*[（(:：]?\s*(?:参照|参考|ref\.?)?\s*[:：]?"
            def _clean(n_):
                a_ = re.match(r"^(<a\b[^>]*>)?(.*?)(</a>)?$", n_, re.S)   # a hyperlinked name: clean the text inside
                pre, n_, post = a_.group(1) or "", a_.group(2), a_.group(3) or ""
                wrap_ = re.compile(r"^(?:示例测算|示例数据|Illustrative(?: estimate)?)\s*[（(]\s*(?:参照|参考|ref\.?)\s*[:：]?\s*"
                                   r"(.*?)[）)]\s*((?:[（(][^（()）]*[）)])?)$", re.I | re.S)
                for _ in range(4):   # idempotent: "示例测算（参照：示例测算（参照：A））" / "来源：示例测算（参照：A）" → A
                    prev = n_
                    n_ = re.sub(r"^(?:资料来源|来源|Source)\s*[:：]\s*", "", n_, flags=re.I).strip(" ；;")
                    m_ = wrap_.match(n_)
                    if m_:
                        n_ = (m_.group(1).strip() + (m_.group(2) or "")).strip(" ；;")
                    else:
                        n_ = re.sub(strip, "", n_, flags=re.I).strip(" ；;")
                        while n_ and n_[-1] in "）)" and n_.count("（") + n_.count("(") < n_.count("）") + n_.count(")"):
                            n_ = n_[:-1].rstrip()   # the close paren of a stripped "示例测算（参照：…）"
                    if n_ == prev:
                        break
                return pre + n_ + post if n_ else ""
            names = [n_ for n_ in (_clean(n_) for n_ in names)
                     if re.sub(r"<[^>]+>", "", n_) and not re.fullmatch(r"(?:团队|本团队)?(?:分析|测算)|team analysis",
                                                                    re.sub(r"<[^>]+>", "", n_), re.I)]
            sample_src = names
            joined = ""
        else:
            joined = ("；" if lang == "zh" else "; ").join(names)
            if not re.sub(r"<[^>]+>", "", joined).startswith(("来源", "资料来源", "Source")):
                joined = ("来源：" if lang == "zh" else "Source: ") + joined
            foot.append(joined)

    def lines_of(t):
        n = len(wrap(re.sub(r"<[^>]+>", "", t), 10, fw))
        try:
            import sys as _s
            from pathlib import Path as _P
            _s.path.insert(0, str(_P(__file__).resolve().parents[2]))
            from _exhibit_text_fit import text_height
            n = max(n, round((text_height(f'<content fontSize="10" fontFamily="{font}"><p>{t}</p></content>',
                                          width=fw, font_size=10) - 2) / 14))
        except Exception:  # noqa: BLE001
            pass
        finally:
            _s.path.pop(0)
        return n
    if sample_src is not None:   # one line "示例测算（参照：A、B）": drop references from the end until it fits
        def _sl(ns, cut=False):
            if lang == "zh":
                return "示例测算" + (f"（参照：{'、'.join(ns)}{'等' if cut else ''}）" if ns else "")
            return "Illustrative estimate" + (f" (ref: {'; '.join(ns)}{' et al.' if cut else ''})" if ns else "")
        ns, cut = list(sample_src), False
        while ns and lines_of(_sl(ns, cut)) > 1:
            ns, cut = ns[:-1], True
        foot.append(_sl(ns, cut and bool(ns)))
    moved = []
    research = is_research(cwd, deck)
    max_foot = RESEARCH_FOOT_LINES if research else 3
    while len(foot) > 1 and sum(lines_of(t) for t in foot) > max_foot:   # long footnotes go to the speaker notes,
        moved.insert(0, re.sub(r"<[^>]+>", "", foot.pop(len(foot) - 2)))   # the source line stays on the page
    if moved:
        note = "\n".join(([note] if note else []) + [re.sub(r"&amp;", "&", m) for m in moved])
    foot_lines = sum(lines_of(t) for t in foot)
    fh = 14 * foot_lines
    if foot:   # size the box with the lint's own estimator so it never "overflows" past the slide bottom
        import sys as _s
        from pathlib import Path as _P
        _s.path.insert(0, str(_P(__file__).resolve().parents[2]))
        try:
            from _exhibit_text_fit import text_height
            need = text_height(f'<content fontSize="10" fontFamily="{font}">' + "".join(f"<p>{t}</p>" for t in foot)
                               + "</content>", width=fw, font_size=10) - 2
            fh = max(fh, need)
            foot_lines = max(foot_lines, round(fh / 14))
        except Exception:  # noqa: BLE001
            pass
        finally:
            _s.path.pop(0)
    fy = H - 14 - fh
    gloss_y = None
    if research and subtitle and not re.search(r"附录|appendix", f"{section or ''} {title}", re.I) and page is not None \
            and int(page) > 2:   # a data page: one line kept above the footnotes for terms the deck has not explained yet
        gloss_y = fy - 14 if foot else H - 30
        fy_body = gloss_y
    else:
        fy_body = fy
    if foot:
        parts.append(_box(X0, fy, fw, fh + 2, "".join(f"<p>{t}</p>" for t in foot), 10, sub, font))
    if sample:   # always on the page, whatever the source / notes length
        parts.append(_box(W - X0 - 60 - _SAMPLE_W + 4, H - 28, _SAMPLE_W - 4, 16,
                          f"<p>{'示例数据' if lang == 'zh' else 'Sample data'}</p>", 10, C["accent"], font, bold=True,
                          align="right"))
    if page is not None:
        parts.append(_box(W - X0 - 50, H - 28, 50, 16, f"<p>{page}</p>", 10, sub, font, align="right"))
    bottom = ((fy_body if gloss_y is not None else fy) if foot or gloss_y is not None else H - 30) - 8
    fr = Frame("".join(parts), top, bottom, C, title)
    fr._gloss = (gloss_y, fw, sub, font) if gloss_y is not None else None
    fr.subtitle = subtitle
    fr.note = note
    fr.page_no = page
    fr.foot_lines = foot_lines
    fr.appendix = bool(re.search(r"附录|appendix", f"{section or ''} {title}", re.I))
    from . import _page as _pg
    _pg.APPENDIX_PAGE = fr.appendix   # tables on this page: plain first column (no dark blocks in an appendix)
    fr.sample = bool(sample)
    fr.research = research
    fr.speech = (not research) and is_speech(cwd, deck)
    from ._page import BLOCKS as _BL
    from ._axes import PLOTS as _PL0
    _BL.clear()   # blocks are counted per page
    _ly_slots = __import__(__package__ + "._layouts", fromlist=["CHART_SLOTS"])
    _ly_slots.CHART_SLOTS.clear()
    _PL0.clear()
    from . import _layouts as _ly
    _ly.PROFILE["research"] = research   # prose blocks built for this page may go down to RESEARCH_PT
    _ly.SHORT.clear()   # layout warnings belong to the page being built, never to an earlier one
    from ._marks import SIGNAL_SINGLE_PCT as _SSP0
    _SSP0.clear()
    _ly.PROFILE["speech"] = fr.speech   # body_w() defaults to the full width (no takeaways rail) on speech decks
    fr.deck, fr._kw, fr._cwd = deck, _kw, cwd
    if page is not None and deck:
        _frame_heartbeat(cwd, deck, page)
    return fr


def _frame_heartbeat(cwd, deck, page):
    """Building page N (frame(page=N)) keeps its open claim fresh: scripts that stop at a local check or a traceback
    before publish still show next that the page is being worked on, so it is not revoked mid-iteration."""
    import fcntl
    import json
    import time as _t
    try:
        for cl in (d / "claims.json" for d in _sync_dirs(cwd, deck) if (d / "claims.json").exists()):
            with open(cl.parent / "claims.lock", "w") as lk:
                fcntl.flock(lk, fcntl.LOCK_EX)
                allc = json.loads(cl.read_text(encoding="utf-8"))
                c = allc.get(f"p{int(page):02d}")
                if isinstance(c, dict) and c.get("state") in ("doing", "reviewing"):
                    c["t"] = _t.time()
                    cl.write_text(json.dumps(allc, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:  # noqa: BLE001 — a heartbeat never breaks page building
        pass


_SAMPLE_W = 76   # footer width kept for the "示例数据" tag


def _sample_flag(cwd=None, deck=None):
    """True when this deck's numbers are illustrative: .lark-slides/decks/<deck>/sample.flag, or sample.flag in the SYNC
    dir of its multi-agent task. A flag of another deck / an earlier task in the same folder does not count."""
    from ..atomize_svg_to_slide._exhibit_publish import deck_dir
    root = _task_root(cwd)
    if deck and (deck_dir(root, deck) / "sample.flag").exists():
        return True
    return any((d / "sample.flag").exists() for d in _sync_dirs(root, deck))


def _lint_h(lead, text, size, lead_size, width, font):
    import sys as _s
    from pathlib import Path as _P
    _s.path.insert(0, str(_P(__file__).resolve().parents[2]))
    try:
        from _exhibit_text_fit import text_height
        body = (f'<span bold="true" fontSize="{lead_size}">{escape(lead)}</span>' if lead else "") + escape(text)
        return text_height(f'<content fontSize="{size}" fontFamily="{font}"><p lineSpacing="multiple:1.3">{body}</p>'
                           "</content>", width=width, font_size=size)
    except Exception:  # noqa: BLE001
        return 0.0
    finally:
        _s.path.pop(0)


_MARK_SHAPES = ("circle", "square")
POINTS_LOG: list = []   # side points() blocks built since the last publish: (xml, has_marks, mark colours) — publish
#                         nudges unmarked ones and holds once when a mark colour is drawn nowhere on the chart


def _split_item(it):
    """points() item → (lead, text, mark). Items: text | (lead, text) | (lead, text, mark)."""
    if not isinstance(it, (tuple, list)):
        return "", it, None
    return (it[0], it[1], it[2] if len(it) > 2 else None)


_ICON_INDEX = None   # {iconType} ∪ {bare name → iconType} from references/xml/iconpark-index.json (lazy; {} = unavailable)


def _icon_type(icon, where="icon"):
    """Validate an IconPark iconType ("iconpark/Money/wallet-one.svg"; a unique bare name "wallet-one" is resolved).
    Accepts anything when the index cannot be loaded."""
    global _ICON_INDEX
    if _ICON_INDEX is None:
        _ICON_INDEX = {}
        import sys as _s
        from pathlib import Path as _P
        _s.path.insert(0, str(_P(__file__).resolve().parents[2]))
        try:
            from iconpark_tool import load_index
            names = {}
            for e in load_index()["icons"]:
                _ICON_INDEX[e["iconType"]] = e["iconType"]
                names.setdefault(e["name"], []).append(e["iconType"])
            _ICON_INDEX.update({k: v[0] for k, v in names.items() if len(v) == 1 and k not in _ICON_INDEX})
        except BaseException:  # noqa: BLE001 — iconpark_tool.fail() exits; no index → accept as given
            _ICON_INDEX = {}
        finally:
            _s.path.pop(0)
    t = str(icon or "").strip()
    if not _ICON_INDEX:
        return t
    if t in _ICON_INDEX:
        return _ICON_INDEX[t]
    best = None
    try:   # an unknown name: nearest IconPark match by its words (the icon is decoration — never fail the page on it)
        import sys as _s
        from pathlib import Path as _P
        _s.path.insert(0, str(_P(__file__).resolve().parents[2]))
        from iconpark_tool import load_index, search_icons
        hits = search_icons(load_index(), {"query": re.sub(r"[-_/.]|svg|iconpark", " ", t), "limit": 1})
        best = hits[0]["iconType"] if hits else None
    except BaseException:  # noqa: BLE001
        best = None
    finally:
        if _s.path and _s.path[0].endswith("scripts"):
            _s.path.pop(0)
    best = best or "iconpark/Edit/dot.svg"
    print(f"提醒：{where}={icon!r} 不在 IconPark 索引里，已换成 {best}（想换就用 python3 scripts/iconpark_tool.py search --query <关键词>）")
    return best


def _mark_spec(mark, C, shape=None):
    """mark → ("num", n) | ("swatch", colour, shape) | ("icon", iconType, colour) | None. A colour mark is a role name
    of roles(palette) ("accent", "main", "neg", "good", "dim" …), a #hex / rgb() colour (e.g. ex.group_colors["华东"]),
    optionally as (colour, "circle"|"square"); an int n is the numbered circle that matches num_dot(ex, x, y, n);
    ("icon", iconType, colour) is an IconPark icon for points(style="card" | "badge")."""
    if mark is None or mark is False or mark == "":
        return None
    if isinstance(mark, int) and not isinstance(mark, bool):
        return ("num", mark)
    if isinstance(mark, (tuple, list)) and mark and mark[0] == "icon":
        if len(mark) < 2:
            raise ValueError('points icon mark 写成 ("icon", "iconpark/<分类>/<名>.svg", 颜色)')
        col = _mark_spec(mark[2] if len(mark) > 2 and mark[2] else "main", C, "circle")[1]
        return ("icon", _icon_type(mark[1], "points icon"), col)
    if isinstance(mark, (tuple, list)):
        col, shp = (list(mark) + [None])[:2]
        spec = _mark_spec(col, C, shp)
        return spec
    m = str(mark).strip()
    col = C.get(m) or (m if re.fullmatch(r"#[0-9A-Fa-f]{6}|rgba?\([^)]*\)", m) else None)
    if col is None:
        raise ValueError(f"points mark={mark!r} 不是颜色角色（{'/'.join(k for k in ('accent', 'main', 'neg', 'good', 'second', 'third', 'context', 'dim') if k in C)}）、"
                         "#hex / rgb() 颜色或整数编号")
    if shape is None:   # bubbles / dots are matched by a round swatch, bars and areas by a square one
        from ._page import USED
        shape = "circle" if USED & {"bubbles", "bubble_map", "dot_range", "ridge_point", "lines", "slope", "bump"} \
            else "square"
    if shape not in _MARK_SHAPES:
        raise ValueError(f"points mark 形状只能是 circle / square，不是 {shape!r}")
    return ("swatch", col, shape)


def _rgb(c):
    c = str(c)
    if c.startswith("#") and len(c) == 7:
        return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))
    m = re.findall(r"[\d.]+", c)
    return tuple(int(float(v)) for v in m[:3]) if len(m) >= 3 else (0, 0, 0)


def _readable(c):
    """Colour dark enough for bold lead text on white (contrast ≥ 3); light greys (dim / context) are not."""
    lum = []
    for v in _rgb(c):
        v /= 255
        lum.append(v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4)
    L = 0.2126 * lum[0] + 0.7152 * lum[1] + 0.0722 * lum[2]
    return 1.05 / (L + 0.05) >= 3


def _lead_sep(lead, text):
    """(lead, text) as points() renders them: a CJK lead gets "：", a Latin lead a space before the body."""
    if lead and text and has_cjk(lead[-1:]) and lead[-1] not in "：:，,。；;—–、）)】":
        lead += "："  # a CJK lead must be visibly separated from the body
    sep = " " if (lead and text and not has_cjk(lead[-1:]) and not lead.endswith(" ")
                  and not text.startswith(" ")) else ""
    return lead, sep + text


def _points_measure(x, w, items, sz, lsz, indent, font):
    tx = x + indent
    hs = []
    for it in items:
        lead, text, _ = _split_item(it)
        lead, text = _lead_sep(lead, text)   # measure what points() renders (the CJK "：" it appends wraps too)
        n_lines = len(wrap(lead + text, sz, w - (tx - x) - 4, bold=False))
        est = n_lines * sz * 1.5 + 6
        lint = _lint_h(lead, text, sz, lsz, w - (tx - x), font)   # the height the server lint will measure
        hs.append(max(est, lint + 4))
    return tx, hs


POINT_STYLES = ("plain", "swatch", "number", "card", "bar", "badge")
_CARD_BAND = "rgba(246,246,246,1)"


def _is_icon_mark(m):
    return isinstance(m, (tuple, list)) and bool(m) and m[0] == "icon"


def _style_geom(style, items, numbered=False):
    """(text indent, right padding) of one points block — the same for every item, so text left edges align."""
    marks = [_split_item(it)[2] for it in items]
    has = any(m not in (None, False, "") for m in marks)
    if style == "card":
        return (46 if any(_is_icon_mark(m) for m in marks) else 16), 8
    if style == "bar":
        return 16, 0
    if style == "badge":
        return (46 if has else 0), 0
    return (32 if (numbered or style == "number" or has) else 0), 0


def _style_h(style, hh):
    """Item height around a text height hh: card pads the band, badge keeps room for the 34px circle."""
    return hh + 12 if style == "card" else (max(hh, 36) if style == "badge" else hh)


def _points_fit(w, items, h, size=16, gap=14, numbered=False, lead_size=None, font="思源黑体", style="plain"):
    """The (size, lead_size, heights) points() would end up with in a column of height h (same shrink rule).
    heights are item heights (text + the style's padding)."""
    lead_size = lead_size or size + 2
    indent, rpad = _style_geom(style, items, numbered)
    _, hs = _points_measure(0, w - rpad, items, size, lead_size, indent, font)
    hs = [_style_h(style, v) for v in hs]
    floor = 12 if getattr(points, "_summary", False) else 14
    while h and sum(hs) + gap * (len(items) - 1) > h and size > floor:
        size, lead_size = size - 1, lead_size - 1
        _, hs = _points_measure(0, w - rpad, items, size, lead_size, indent, font)
        hs = [_style_h(style, v) for v in hs]
    return size, lead_size, hs


def points(x, y, w, items, palette=None, font="思源黑体", size=16, gap=14, numbered=False, h=None,
           lead_size=None, spread=True, style="plain"):
    """Numbered takeaways column (circle + bold lead + text) as native XML, sized from the wrapped text.

    items: [(lead, text)] or [text] or [(lead, text, mark)]. Body 16pt, lead 18pt by default. h: height of the column
    (e.g. f.bottom - y, or the chart box height) — items are spread over it so the column ends where the chart ends
    instead of stacking at the top (spread=False: fixed gap, top-aligned, no shrinking). If they do not fit at this
    size, shorten the text (or raise h); size only drops to 14 as a last resort. numbered=True draws ①②③ circles —
    only when the chart carries the same numbers (num_dot(ex, x, y, n) or bubbles(numbered=True)); otherwise a bold
    lead per item is enough.
    mark links one point to the chart: a colour role ("accent", "main", "neg", "good" … of ex.C) or a #hex / rgb()
    colour (ex.group_colors[group] for bubbles(groups=True)) draws a small swatch before the lead and colours the lead
    — use the colour of the highlighted bars / bubbles the point talks about; (colour, "square"|"circle") picks the
    swatch shape (default: circle on bubble / dot charts, square otherwise); an int n draws the numbered circle that
    matches num_dot(ex, x, y, n). Points about non-highlighted context get no mark; text stays aligned either way.
    style picks the decoration (same text left edge for every item of the block; text is emitted after all shapes):
      "plain" / "swatch"  small colour swatch per marked item (the mark rules above)
      "number"            numbered circles (= numbered=True) — pair with num_dot on the chart
      "card"              each item on a light band with a 4px left bar in the mark colour; mark ("icon", iconType,
                          colour) adds a 22px icon (sequential points: observation → evidence → action)
      "bar"               6px left colour bar per item in the mark colour (tiers mapped to a colour scale)
      "badge"             34px circle in the mark colour with a white icon; marks must be ("icon", iconType, colour)
                          (distinct natures: 机会 / 风险 / 提示, 人群)
    In card / bar / badge the lead takes the mark colour only for the accent item (others stay ink).
    Returns (xml, bottom_y).
    """
    if not isinstance(x, (int, float)):
        raise TypeError("points() 是页面 XML 助手（x, y 为幻灯片坐标），不画进 Exhibit：用返回的 XML 传给 f.publish(xml, ...)；"
                        "图内文字用 callout / big_number / badge")
    C = roles(palette)
    style = style or "plain"
    if style not in POINT_STYLES:
        raise ValueError(f"points style={style!r} 只能是 {' / '.join(POINT_STYLES)}")
    if style == "number":
        numbered = True
    lead_size = lead_size or size + 2
    specs = [_mark_spec(_split_item(it)[2], C) for it in items]
    if style == "badge":
        bad = [i + 1 for i, s in enumerate(specs) if s and s[0] != "icon"]
        if bad:
            raise ValueError(f"points(style='badge') 第 {bad} 条的 mark 不是图标：写成 (\"icon\", \"iconpark/<分类>/<名>.svg\", 颜色)"
                             "（iconpark_tool.py search 选图标）；只想要色块用 style='swatch'，不要硬凑图标")
    indent, rpad = _style_geom(style, items, numbered)
    tx, ths = _points_measure(x, w - rpad, items, size, lead_size, indent, font)
    hs = [_style_h(style, v) for v in ths]
    if h and spread:
        size, lead_size, hs = _points_fit(w, items, h, size, gap, numbered, lead_size, font, style)
        tx, ths = _points_measure(x, w - rpad, items, size, lead_size, indent, font)
        need = sum(hs) + 8 * (len(items) - 1)
        if need > h + 1:
            chars = sum(len(_split_item(it)[0] + _split_item(it)[1]) for it in items)
            raise ValueError(f"points 放不下：需要高 {need:.0f}px，只有 {h:.0f}px（{len(items)} 条、{chars} 字、已降到 {size}pt）。"
                             f"删到约 {int(chars * h / need * 0.9)} 字或减少条数，或加宽栏 w，不要反复挪坐标")
        free = h - sum(hs)
        gap = max(gap, min(free / max(len(items) - 1, 1), 48)) if len(items) > 1 else gap
        used = sum(hs) + gap * (len(items) - 1)
        y = y + max((h - used) / 2, 0)
    deco, icons, texts, cy = [], [], [], y   # z-order: bands / bars / badges, then icons, then all text on top
    acc = _c(C["accent"])
    rect = lambda x_, y_, w_, h_, col: (f'<shape type="rect" topLeftX="{x_:.0f}" topLeftY="{y_:.0f}" width="{w_:.0f}" '
                                        f'height="{h_:.0f}"><fill><fillColor color="{_c(col)}"/></fill></shape>')
    icon = lambda t, x_, y_, s_, col: (f'<icon iconType="{escape(t)}" topLeftX="{x_:.0f}" topLeftY="{y_:.0f}" width="{s_}" '
                                       f'height="{s_}"><fill><fillColor color="{_c(col)}"/></fill></icon>')
    for i, (it, hh, th, spec) in enumerate(zip(items, hs, ths, specs), 1):
        lead, text, _ = _split_item(it)
        lead_col = C["ink"]
        col = spec[2] if spec and spec[0] == "icon" else (spec[1] if spec and spec[0] == "swatch" else None)
        ty, t_h = cy, th
        if style in ("card", "bar", "badge"):
            if col and _c(col) == acc:   # heavy styles colour the lead only for the accent (red) item
                lead_col = col
            if style == "card":
                deco.append(rect(x, cy, w, hh, _CARD_BAND))
                deco.append(rect(x, cy, 4, hh, col or C["main"]))
                if spec and spec[0] == "icon":
                    icons.append(icon(spec[1], x + 14, cy + 8, 22, col))
                ty, t_h = cy + 6, hh - 12
            elif style == "bar":
                deco.append(rect(x, cy + 2, 6, max(th - 4, 20), col or C["main"]))
            elif spec:   # badge
                deco.append(f'<shape type="ellipse" topLeftX="{x:.0f}" topLeftY="{cy:.0f}" width="34" height="34">'
                            f'<fill><fillColor color="{_c(col)}"/></fill></shape>')
                icons.append(icon(spec[1], x + 7, cy + 7, 20, "#FFFFFF"))
        else:
            ccy = cy + lead_size * 0.65 - 11 + 8   # 22px marker box centred on the first line (lead line ≈ lead_size × 1.3)
            if numbered or (spec and spec[0] == "num"):
                n = spec[1] if spec and spec[0] == "num" else i
                fill = col or C["main"]
                deco.append(f'<shape type="ellipse" topLeftX="{x:.0f}" topLeftY="{ccy:.0f}" width="22" height="22">'
                            f'<fill><fillColor color="{_c(fill)}"/></fill></shape>')
                texts.append(_box(x, ccy, 22, 22, f"<p>{n}</p>", 12, "#FFFFFF", font, bold=True, align="center",
                                  valign="middle"))
            elif spec:
                shp = spec[2] if spec[0] == "swatch" else "square"
                deco.append(f'<shape type="{"ellipse" if shp == "circle" else "rect"}" topLeftX="{x + 5:.0f}" '
                            f'topLeftY="{ccy + 5:.0f}" width="12" height="12"><fill><fillColor color="{_c(col)}"/></fill>'
                            '</shape>')
                if _readable(col):
                    lead_col = col
            t_h = hh
        lead, text = _lead_sep(lead, text)
        body = (f'<span bold="true" fontSize="{lead_size}" color="{_c(lead_col)}">{escape(lead)}</span>' if lead else "") \
            + escape(text)
        texts.append(_box(tx, ty, w - indent - rpad, t_h, f'<p lineSpacing="multiple:1.3">{body}</p>', size, C["text"],
                          font))
        cy += hh + gap
    xml = "".join(deco + icons + texts)
    if _lead_only(items, specs, style):   # soft hint, never a hold: the detail text went missing
        print(f"提示：{EMPTY_BODY_MSG}")
        EMPTY_BODY_LOG.append(xml)
    if not getattr(points, "_summary", False) and not numbered and len(items) > 1:
        def _role(m):   # the role name behind a colour mark ("accent"), re-resolved with ex.C when palette=None
            m = m[2] if _is_icon_mark(m) and len(m) > 2 else (m[0] if isinstance(m, (tuple, list)) and m else m)
            return m if isinstance(m, str) and m in C else None
        cols_ = [(sp[1] if sp[0] == "swatch" else sp[2], None if palette else _role(_split_item(it)[2]))
                 for it, sp in zip(items, specs) if sp and sp[0] in ("swatch", "icon")]
        POINTS_LOG.append((xml, any(specs), cols_))
    return xml, cy - gap


EMPTY_BODY_MSG = "要点只有引语没有正文：把细节写进第二个字段，或改用 swot_matrix / row_table"
EMPTY_BODY_LOG: list = []   # points() blocks built since the last publish whose items are all lead-only


def _lead_only(items, specs, style):
    """All items are a lead with an empty body: ≥4 such items, or (plain / swatch style) every item also marked —
    the "S · 标题", "", "good" pattern that scatters lone swatches over the page with the detail text dropped."""
    parts = [_split_item(it) for it in items]
    if len(parts) < 2 or not all(str(ld or "").strip() and not str(tx or "").strip() for ld, tx, _ in parts):
        return False
    return len(parts) >= 4 or (style in ("plain", "swatch") and all(specs))


def _points_unmarked(ex, body):
    """Frame.publish nudge: the chart highlights something (accent / focus colour, num_dot) but a side points() block
    on the page carries no mark. Print-only — never a hold."""
    if ex is None:
        return False
    page = "".join(str(b) for b in body)
    side = [has for xml, has, *_ in POINTS_LOG if xml and xml in page]
    if not side or any(side):
        return False
    C = ex.C
    fills = {str(r.get("fill") or "").upper() for r in getattr(ex, "reg", []) if r.get("kind") == "mark"}
    hi = {str(C.get(k, "")).upper() for k in ("accent", "neg")} - {""}
    two_tone = str(C.get("main", "")).upper() in fills and bool(
        fills & {str(C.get(k, "")).upper() for k in ("context", "dim")})
    return bool(fills & hi) or two_tone or bool(getattr(ex, "num_dots", 0)) or bool(getattr(ex, "group_colors", None))


def _num_values(text):
    """Numbers written in a string ('1,484', '+19.4%', '2.19：1' → [1484.0, 19.4, 2.19, 1.0])."""
    return [float(x.replace(",", "")) for x in re.findall(r"\d[\d,]*(?:\.\d+)?", str(text))]


def _chart_numbers(xml):
    """Numbers printed inside chart fragments (value labels, CAGR badges, axis-free labels): from <p> text."""
    out = []
    for t in re.findall(r"<p[^>]*>(.*?)</p>", xml, re.S):
        out += _num_values(re.sub(r"<[^>]+>", "", t))
    return out


def _cross_page_hold(f, body, frags, cwd, deck, page):
    """business-research: a metric + period + unit on this page whose value differs (> 2 %) from the one an already
    written page of the deck states. Records this page's visible text for the next pages. "" when consistent."""
    if not (getattr(f, "research", False) and deck and page is not None and cwd):
        return ""
    import json as _j
    import sys as _s
    from pathlib import Path as _P
    led = _P(cwd) / ".lark-slides" / f"pagetext-{deck}.json"
    try:
        texts = _j.loads(led.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        texts = {}
    mine = " ".join(re.sub(r"<[^>]+>", " ", f.title + " " + "".join(str(b) for b in body)
                           + "".join(str(x) for x in frags)).replace("&amp;", "&").split())
    _s.path.insert(0, str(_P(__file__).resolve().parents[2]))
    try:
        from multiagent_sync import cross_page_conflicts
        others = {int(k): v for k, v in texts.items() if str(k).isdigit() and int(k) != int(page)}
        found = [c for c in cross_page_conflicts({**others, int(page): mine}) if f"P{int(page)} " in c]
    except Exception:  # noqa: BLE001
        found = []
    finally:
        _s.path.pop(0)
    texts[str(int(page))] = mine
    try:
        led.parent.mkdir(parents=True, exist_ok=True)
        led.write_text(_j.dumps(texts, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass
    if not found:
        return ""
    return ("跨页数字不一致：" + "；".join(found[:3]) + "——同一指标同一期间全稿只用一个数（从 plan/research 同一变量拼，"
            "不手写）；确实口径不同（全年 vs 半年、集团 vs 分部）就在这页写明口径")


_KPI_DATE = re.compile(r"(?i)\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*'?\d{2,4}\b|"
                       r"\b(?:Q[1-4]|H[12]|FY)\s*'?\d{2,4}\b|\b(?:19|20)\d{2}\s*(?:年\s*)?(?:\d{1,2}\s*月|Q[1-4]|H[12])?|"
                       r"\d{1,2}\s*月(?:\s*\d{1,2}\s*日)?")


def _kpi_is_quantity(value):
    """A KPI figure that is a measured quantity (12.4% / $245 / 3.2x / 1.1 亿) — the ones that must come from a chart.
    A date or status card ("April 2026", "Killed Apr 2025", "已获批", "2026Q2 上市") has no number left once dates are
    removed: nothing to read off a chart."""
    return bool(re.search(r"\d", _KPI_DATE.sub(" ", str(value))))


def research_ties(ex, frags=(), title="", body=()):
    """business-research: the parts of a page must point at each other.
    (1) kpi_charts_page figures name the chart they come from (4th item) and the figure is printed on that chart;
    (2) a key_takeaways rail is numbered and every number has a num_dot on the chart;
    (3) a page with ≥2 charts heads each chart with a judgement line (panel claim) — not only a metric name;
    (4) a number the title states is shown on a chart as a marked element (focus colour, dashed box, num_dot, badge,
        CAGR / diff label, KPI figure), not only somewhere in an axis label or the side text.
    Returns a list of messages ([] when fine or not a research page). Clears the per-page registries."""
    from . import _layouts as L
    kpi_links, rails, texts = list(L.KPI_LINKS), list(L.RAIL_NUMS), list(L.RAIL_TEXT)
    claims = list(L.CLAIMS)
    L.KPI_LINKS.clear()
    L.RAIL_NUMS.clear()
    L.RAIL_TEXT.clear()
    L.CLAIMS.clear()
    from ._page import SLID
    exs = list(dict.fromkeys(([ex] if ex is not None else []) + list(SLID)))
    SLID.clear()
    if not L.PROFILE.get("research"):
        return []
    msgs, tail = [], []
    claims += [c for e in exs for c in (getattr(e, "claims", None) or [])]
    own = [e for e in exs if e is ex or any(getattr(e, "_slid", False) and str(x) for x in frags or ())]
    n_charts = sum(max(1, len(getattr(e, "panels", None) or [])) for e in own) if own else 0
    n_charts = max(n_charts, len([x for x in frags or () if re.search(r"<(?:shape|line|polyline)\b", str(x))]))
    if n_charts >= 2 and len(claims) < n_charts and title \
            and not ({"small_multiples", "shared_time", "row_table", "focus_panels", "kpi_charts_page", "columns_page"}
                     & (_used() | _lay_used())):   # columns_page: each small chart sits under its column title
        tail.append(f"多图页每张图要一句判断句小标题：本页 {n_charts} 张图只有 {len(claims)} 句——图上方写这张图证明了什么"
                    "（ex.panel(box, claim='海外收入五年翻倍…', unit='海外收入，亿元') / mixed_columns_page 的 chart 块 claim= / "
                    "panel_heads），几句连起来复述页标题；写不出就说明两张图没关系，只留一张大图")
    for links in kpi_links:     # kpi_charts_page charts arrive as frags=[chart 0, chart 1] in slot order
        unbound = [v for v, ci in links if ci is None and _kpi_is_quantity(v)]
        if unbound:
            msgs.append(f"KPI {unbound} 没写出自下方哪张图：kpis 每项写成 (指标·期间, 数值, 口径, 图序号)，数值取自那张图"
                        "（末期值 / CAGR / 份额），图里没有的数不放 KPI 行")
            continue
    dots = sum(getattr(e, "num_dots", 0) for e in exs)
    if not exs and not any(re.search(r"<(?:path|line|shape|chart)\b", str(x)) for x in frags or ()):
        rails, texts = [], []   # a rail next to text only (no chart): nothing to number against
    if rails and dots:   # the rail has no numbers: numbered dots on the chart point at nothing
        msgs.append(f"图上有 {dots} 个编号圆点，右栏要点不用编号：删掉 num_dot，要点里直接点名它说的年份 / 对象并引用读数，"
                    "图上用 focus= 高亮那根柱、band / dashed_box 框出那一段")
    hit = lambda vs, on: any(abs(v - o) <= max(0.051, abs(o) * 0.006) for v in vs for o in on)   # noqa: E731
    on = [o for e in exs for o in _svg_numbers(e)] + [o for x in frags for o in _chart_numbers(str(x))]
    near = {}
    for e in exs:
        near.update(getattr(e, "dot_values", None) or {})
    for rail in texts:   # the first takeaways read the chart: their evidence quotes a value printed on it
        reads = [n for n, t in rail[:2] if _evidence_numbers(t)]
        if on and reads and not any(hit(_evidence_numbers(t), on) for n, t in rail[:2] if _evidence_numbers(t)):
            # a note, never a hold: held, it pushed rails into coordinate read-backs ("x=18、y=25.5%"), wrong chart
            # descriptions ("最右上角") and "图上…" meta wording, and action / qualitative rails got demoted to footnotes
            from ._page import SIGNALS as _SG
            _SG.append("要点未读图")
            print("提醒（不阻塞）：右栏前两条要点写的数字在图上都找不到——要点读图更有力：点名它说的年份 / 对象并引用图上那根柱 / "
                  "那个点的读数；要点本来就讲图外的事（行动、决策、定性判断）就不用改，也不要写“图上…”这类描述图的话")
    return msgs + tail


def _fmt_num(v):
    return f"{v:g}"


def _evidence_numbers(text):
    """Numbers a takeaway cites as evidence: not years, not bare single digits (counts, 'P5')."""
    t = re.sub(r"(?<![\d.,])(?:19|20)\d{2}(?:[EFAH]\d?|Q\d|年|\s*年|[-–/~至到]|(?=\s*[-–]))|(?<![\d.,])(?:19|20)\d{2}(?![\d.,]|\s*[万亿元%x倍个家台座GMWhKkg])"
               r"|[PQH]\d+|\d+\s*(?:家|条|个|项|轮|年|月|季)", " ", str(text))
    return [v for v in _num_values(t) if not (v.is_integer() and v < 10)]


def _svg_numbers(ex):
    """Numbers printed on an Exhibit (data labels, badges, axis ticks excluded only by being identical anyway)."""
    out = []
    for e in ex.reg:   # printed readings only: axis tick labels (every round number) would match anything
        if e["kind"] == "text" and e.get("fill") != ex.C["axis"]:
            out += _num_values(str(e["tag"]))
    return out


def _rgb_or_none(c):
    c = str(c or "").strip()
    if re.fullmatch(r"#[0-9A-Fa-f]{6}", c):
        return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))
    m = re.fullmatch(r"rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]+)\s*)?\)", c)
    if not m or (m.group(4) is not None and float(m.group(4)) < 0.3):
        return None
    return tuple(int(float(v)) for v in m.groups()[:3])


MARK_COLOUR_TOL = 40   # sum of |ΔR|+|ΔG|+|ΔB|: a mark "is" a chart colour within this distance


def _mark_colours_missing(ex, body, frags=()):
    """Side points() mark colours (swatch / card / bar / badge) that no element of the chart is painted in — e.g. an
    "accent" swatch next to a chart of teal / grey / green bars. Greys pass when the chart has any grey fill (context).
    Chart colours: ex.fills (+ <fillColor> of other exhibit fragments on the page). [] when nothing to compare."""
    page = "".join(str(b) for b in body)
    eC = getattr(ex, "C", None) or {}
    marks = [(eC.get(r_) or c) if r_ else c   # no palette= on points(): the role means the exhibit's colour
             for xml, _, *cs in POINTS_LOG if xml and xml in page for c, r_ in (cs[0] if cs else [])]
    if not marks:
        return []
    chart = set(getattr(ex, "fills", ()) or ()) if ex is not None else set()
    for fr in frags:
        chart |= set(re.findall(r'<fillColor color="([^"]+)"', str(fr)))
    rgbs = [v for v in (_rgb_or_none(c) for c in chart) if v and v not in ((255, 255, 255),)]
    if not rgbs:
        return []
    grey = lambda v: max(v) - min(v) <= 16   # noqa: E731
    has_grey = any(grey(v) for v in rgbs)
    out = []
    for c in dict.fromkeys(marks):
        v = _rgb_or_none(c)
        if v is None or (grey(v) and has_grey):
            continue
        if min(sum(abs(a - b) for a, b in zip(v, w)) for w in rgbs) > MARK_COLOUR_TOL:
            out.append(c)
    return out


def brace(x0, y0, x1, y1, tip="down", palette=None, color=None, width=1):
    """Native curly brace over the box (x0, y0, x1, y1), its tip pointing tip=down/up/right/left — e.g. under a chart
    (or two charts) pointing down at a takeaway box, or beside a table pointing right at the conclusion panel.
    Use a 14–18px thin box. Returns (xml, (tip_x, tip_y))."""
    C = roles(palette)
    col = _c(color or C["ink"])
    if tip in ("down", "up"):
        L, t = x1 - x0, y1 - y0
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        kind = "right-brace" if tip == "down" else "left-brace"
        attrs = f'topLeftX="{cx - t / 2:.0f}" topLeftY="{cy - L / 2:.0f}" width="{t:.0f}" height="{L:.0f}" rotation="90"'
        pt = (cx, y1 if tip == "down" else y0)
    else:
        kind = "right-brace" if tip == "right" else "left-brace"
        attrs = f'topLeftX="{x0:.0f}" topLeftY="{y0:.0f}" width="{x1 - x0:.0f}" height="{y1 - y0:.0f}"'
        pt = (x1 if tip == "right" else x0, (y0 + y1) / 2)
    return f'<shape type="{kind}" {attrs}><border color="{col}" width="{width}"/></shape>', pt


def takeaway(x, y, w, text, lead=None, palette=None, font="思源黑体", size=18, style="box", color=None,
             align="center", bottom=None):
    """Conclusion box the brace / connector points at: white box with an accent outline (style="box") or the
    McKinsey red oval (style="oval"); bold lead (optional) + text, 16–20pt. Height follows the wrapped text.
    bottom=f.bottom anchors the box to the bottom of the body area (the chart above then ends at top − 30).
    Returns (xml, top_y, bottom_y)."""
    if not isinstance(x, (int, float)):
        raise TypeError("takeaway() 是页面 XML 助手（x, y 为幻灯片坐标），不画进 Exhibit：用返回的 XML 传给 f.publish(xml, ...)；"
                        "图内文字用 callout / big_number / badge")
    C = roles(palette)
    col = _c(color or C["accent"])
    pad = w * 0.13 if style == "oval" else 14   # text must stay inside the ellipse's inscribed band
    n = len(wrap((lead or "") + text, size, w - 2 * pad, bold=True))
    h = n * size * 1.4 + (34 if style == "oval" else 18)
    if bottom is not None:
        y = bottom - h
    shape = "ellipse" if style == "oval" else "rect"
    ph = "" if style == "oval" else ' presetHandlers="6"'
    sep = " " if lead and not has_cjk(lead[-1:]) and not lead.endswith(" ") and not text.startswith(" ") else ""
    body = (f'<span bold="true" color="{col}">{escape(lead)}</span>' if lead else "") + escape(sep + text)
    xml = (f'<shape type="{shape}" topLeftX="{x:.0f}" topLeftY="{y:.0f}" width="{w:.0f}" height="{h:.0f}"{ph}>'
           f'<fill><fillColor color="rgb(255,255,255)"/></fill><border color="{col}" width="2"/></shape>'
           + _box(x + pad, y, w - 2 * pad, h, f'<p lineSpacing="multiple:1.2">{body}</p>', size, C["ink"], font,
                  bold=not lead, align=align, valign="middle"))
    return xml, y, y + h


def linked_panel(x, y, w, h, title, items, source=None, palette=None, font="思源黑体", size=16):
    """Dashed conclusion panel tied to the evidence: filled title tab on top, numbered points inside, and dashed
    connector lines from the source box's right corners (source=(x0, y0, x1, y1), e.g. the table / chart box) to
    the panel — reads as "this table → this conclusion". Returns xml."""
    C = roles(palette)
    main, line = _c(C["main"]), _c(C["second"])
    tab_h = 34
    out = []
    if source:
        sx0, sy0, sx1, sy1 = source
        for sy, py in ((sy0, y + tab_h / 2), (sy1, y + h)):
            out.append(f'<line startX="{sx1 + 4:.0f}" startY="{sy:.0f}" endX="{x:.0f}" endY="{py:.0f}">'
                       f'<border color="{line}" width="1" dashArray="dash"/></line>')
    out.append(f'<shape type="rect" topLeftX="{x:.0f}" topLeftY="{y + tab_h / 2:.0f}" width="{w:.0f}" '
               f'height="{h - tab_h / 2:.0f}"><fill><fillColor color="rgb(255,255,255)"/></fill>'
               f'<border color="{line}" width="1" dashArray="dash"/></shape>')
    tw_ = min(w - 40, max(120, len(title) * (size + 2) * (1 if has_cjk(title) else 0.6) + 36))
    out.append(f'<shape type="rect" topLeftX="{x + (w - tw_) / 2:.0f}" topLeftY="{y:.0f}" width="{tw_:.0f}" '
               f'height="{tab_h}"><fill><fillColor color="{main}"/></fill></shape>')
    out.append(_box(x + (w - tw_) / 2, y, tw_, tab_h, f"<p>{escape(title)}</p>", size + 2, "#FFFFFF", font, bold=True,
                    align="center", valign="middle"))
    px, _ = points(x + 16, y + tab_h + 12, w - 32, items, palette=palette, font=font, size=size,
                   h=h - tab_h - 24, numbered=True)
    out.append(px)
    return "".join(out)


def kpis(x, y, w, items, palette=None, font="思源黑体", cols=None, h=None, big=32, accent_first=True):
    """Row (or grid) of KPI cards: big number (Georgia) + unit + one-line label, thin top rule in the main colour.
    items: [(value, unit, label)] e.g. ("62.9", "GW", "在建装机，全球第一"). cols defaults to len(items) (≤4 per row).
    h: total height to fill (cards share it). The first card's number uses accent (accent_first). Returns (xml, bottom)."""
    from ._page import BLOCKS as _BL
    _BL.append("kpis")
    if not isinstance(x, (int, float)):
        raise TypeError("kpis() 是页面 XML 助手（x, y 为幻灯片坐标），不画进 Exhibit：用返回的 XML 传给 f.publish(xml, ...)；"
                        "图内文字用 callout / big_number / badge")
    C = roles(palette)
    n = len(items)
    cols = cols or min(n, 4)
    rows = -(-n // cols)
    gap = 16
    cw = (w - gap * (cols - 1)) / cols
    ch = (h - gap * (rows - 1)) / rows if h else big * 1.4 + 52
    out = []
    for i, (val, unit, label) in enumerate(items):
        r_, c_ = divmod(i, cols)
        cx, cy = x + c_ * (cw + gap), y + r_ * (ch + gap)
        col = C["accent"] if (accent_first and i == 0) else C["main"]
        out.append(f'<line startX="{cx:.0f}" startY="{cy:.0f}" endX="{cx + cw:.0f}" endY="{cy:.0f}">'
                   f'<border color="{_c(C["main"])}" width="2"/></line>')
        bs = big   # a long value ("€70–120m") shrinks to stay on one line instead of wrapping onto the label
        while bs > 18 and tw(str(val), bs, bold=True) * 1.12 + tw(" " + str(unit), 16, bold=True) > cw - 8:
            bs -= 2
        num = (f'<p><span fontFamily="Georgia" fontSize="{bs}" bold="true" color="{_c(col)}">{escape(str(val))}</span>'
               f'<span fontSize="16" bold="true" color="{_c(C["ink"])}"> {escape(unit)}</span></p>')
        out.append(_box(cx, cy + 8, cw, big * 1.4, num, bs, col, font, valign="top"))
        lines_ = len(wrap(label, 16, cw - 4))
        room = int((ch - big * 1.4 - 12) // 22)
        if h and lines_ > max(room, 1):
            raise ValueError(f"kpis：第 {i + 1} 张卡说明 '{label[:12]}…' 要 {lines_} 行，只放得下 {max(room, 1)} 行——"
                             f"说明压到约 {int(len(label) * max(room, 1) / lines_)} 字，或减少卡片数")
        out.append(_box(cx, cy + 10 + big * 1.4, cw, max(lines_ * 22 + 4, ch - big * 1.4 - 12),
                        f'<p lineSpacing="multiple:1.2">{escape(label)}</p>', 16, C["text"], font))
    return "".join(out), y + rows * ch + gap * (rows - 1)


_KPI_TRACK = "rgba(225,225,225,1)"
_KPI_GREY = "rgba(110,110,110,1)"


def _kpi_item(it):
    """kpi_cards item → dict(value, unit, label, icon, note, bar, focus); the old (value, unit, label) tuple is accepted."""
    if isinstance(it, dict):
        if "value" not in it or "label" not in it:
            raise ValueError(f"kpi_cards 卡片要有 value 与 label：{it!r}")
        d = dict(unit="", icon=None, note=None, bar=None, focus=False)
        d.update(it)
        return d
    if isinstance(it, (tuple, list)) and len(it) >= 3:
        return dict(value=it[0], unit=it[1], label=it[2], icon=None, note=None, bar=None, focus=False)
    raise ValueError(f"kpi_cards 卡片写成 dict(value=, unit=, label=, icon=, note=, bar=) 或 (值, 单位, 说明)：{it!r}")


def _kpi_bar(bar, C, focus_col):
    """bar spec → (kind, rows) where rows is a list of bars, each a list of (x_frac, w_frac, colour) segments
    (a grey track is drawn under "share" / "parts")."""
    if not bar:
        return None
    if not isinstance(bar, (tuple, list)) or len(bar) != 2:
        raise ValueError(f'kpi_cards bar 写成 ("share", 0.82) / ("parts", [(0.7, "main"), (0.3, "accent")]) / '
                         f'("compare", [("女", 100.3, "main"), ("男", 92.2, "accent")])，不是 {bar!r}')
    kind, val = bar
    colour = lambda c: _mark_spec(c, C, "square")[1] if c else focus_col
    if kind == "share":
        fr = float(val)
        if not 0 <= fr <= 1:
            raise ValueError(f'kpi_cards bar=("share", {val}) 要 0–1 的真实占比（如线下 0.817），不是百分数')
        return "share", [[(0.0, fr, focus_col)]]
    if kind == "parts":
        segs, x0 = [], 0.0
        for p in val:
            fr, c = (p, None) if isinstance(p, (int, float)) else (p[0], p[1] if len(p) > 1 else None)
            segs.append((x0, float(fr), colour(c)))
            x0 += float(fr)
        if x0 > 1.001 or any(s[1] < 0 for s in segs):
            raise ValueError(f"kpi_cards bar=('parts', …) 各段合计 {x0:.3f} > 1：写真实构成占比（合计 ≤1）")
        return "parts", [segs]
    if kind == "compare":
        rows = [tuple(r) if len(r) == 3 else (None,) + tuple(r) for r in val]
        if not 2 <= len(rows) <= 3:
            raise ValueError("kpi_cards bar=('compare', …) 放 2–3 个真实值（如 女 100.3 / 男 92.2）")
        mx = max(float(r[1]) for r in rows)
        if mx <= 0 or any(float(r[1]) < 0 for r in rows):
            raise ValueError("kpi_cards bar=('compare', …) 的值要 ≥0 且至少一个 >0")
        return "compare", [[(0.0, float(r[1]) / mx, colour(r[2]))] for r in rows]   # longest = max: no invented denominator
    raise ValueError(f"kpi_cards bar 类型只能是 share / parts / compare，不是 {kind!r}")


def kpi_cards(x, y, w, items, h=None, palette=None, font="思源黑体", gap=9, horizontal=False, reflow=False, rule="left"):
    """KPI cards (one column by default; horizontal=True puts them side by side): light band, 4px left accent bar,
    optional 34px circle badge with a white IconPark icon, big Georgia number + unit, grey label, right-aligned note
    on the label row and a 6px breakdown bar at the bottom.

    items: dict(value, unit, label, icon=None, note=None, bar=None, focus=False) — or the old (value, unit, label).
      icon: IconPark iconType ("iconpark/Money/wallet-one.svg"; pick with iconpark_tool.py search). No icon → no badge,
            text moves left (never invent one).
      note: short right-aligned fact on the label row ("线下占 81.7%").
      bar:  a REAL breakdown of this number, never an invented denominator —
            ("share", 0.817) one filled segment on a grey track (e.g. offline share of sales);
            ("parts", [(0.7, "main"), (0.3, "accent")]) stacked segments summing ≤1;
            ("compare", [("女", 100.3, "main"), ("男", 92.2, "accent")]) 2–3 thin bars, lengths ∝ value / max.
      focus: this card uses the accent colour (bar, badge, number); the others main / ink. Without any focus=True
            the first card is the focus.
    h: total height — the cards stretch to equal heights. reflow=True stacks complete labels and notes,
    fitting their native text height without discarding content. rule="top" uses a top rule instead of a left strip.
    business-deck (set_profile("deck")): a fragment-A KPI row instead (big number + caption, 1px separators, no card).
    Returns (xml, bottom)."""
    from ._page import BLOCKS as _BL
    _BL.append("kpi_cards")
    if not isinstance(x, (int, float)):
        raise TypeError("kpi_cards() 是页面 XML 助手（x, y 为幻灯片坐标），不画进 Exhibit：用返回的 XML 传给 f.publish(xml, ...)")
    if rule not in ("left", "top"):
        raise ValueError("kpi_cards rule 只能是 left / top")
    C = roles(palette)
    its = [_kpi_item(it) for it in items]
    if not its:
        return "", y
    from . import _layouts as _ly
    if _ly.PROFILE.get("speech"):   # business-deck: fragment-A KPI row, never cards
        return _speech_kpi_row(x, y, w, h, its, C, font, horizontal)
    if not any(d.get("focus") for d in its):
        its[0]["focus"] = True
    if reflow:
        return _reflow_kpi_cards(x, y, w, h, its, C, font, gap, horizontal, rule)
    n = len(its)
    has_bar = any(d.get("bar") for d in its)
    cmp_rows = max([len(d["bar"][1]) for d in its if d.get("bar") and d["bar"][0] == "compare"] + [1])
    bar_h = (cmp_rows * 4 + (cmp_rows - 1) * 2) if cmp_rows > 1 else 6
    big, us, ls = 28, 15, 14

    def need(pad):   # card content height at padding pad
        return pad + big * 1.35 + ls * 1.4 + (6 + bar_h if has_bar else 0) + pad
    if horizontal:
        cw = (w - gap * (n - 1)) / n
        ch = h if h else need(10)
    else:
        cw = w
        ch = (h - gap * (n - 1)) / n if h else need(10)
    pad = 10
    while need(pad) > ch and pad > 4:
        pad -= 2
    if need(pad) > ch + 0.5:
        fit_n = max(1, int((h + gap) // (need(4) + gap))) if (h and not horizontal) else None
        raise ValueError(f"kpi_cards 放不下：每张卡至少要高 {need(pad):.0f}px，只有 {ch:.0f}px——"
                         + (f"减少到 ≤{fit_n} 张卡、" if fit_n else "") + "去掉 bar，或加高 h")
    from ._page import lint_w
    lay = []   # per card: (text x, text width, number size, label width, note width) — widths by the lint's estimator
    for i, d in enumerate(its):
        tx_off = 62 if d.get("icon") else 16
        tw_ = cw - 8 - tx_off
        val, unit = str(d["value"]), str(d.get("unit") or "")
        bs = big   # a long value ("€70–120m") shrinks to stay on one line
        while bs > 18 and lint_w(val, bs, True) + (lint_w(" " + unit, us, True) if unit else 0) > tw_ - 6:
            bs -= 2
        if lint_w(val, bs, True) + (lint_w(" " + unit, us, True) if unit else 0) > tw_ - 6:
            raise ValueError(f"kpi_cards：第 {i + 1} 张卡完整数值与单位一行放不下——加宽 w")
        label, note = str(d["label"]), str(d.get("note") or "")
        lw0 = lint_w(label, ls)
        nw = lint_w(note, 12) + 8 if note else 0
        if lw0 + 6 + nw + (6 if note else 0) > tw_:
            raise ValueError(f"kpi_cards：第 {i + 1} 张卡说明 '{label[:12]}'" + (f" + note '{note[:12]}'" if note else "")
                             + f" 一行放不下（宽约 {tw_:.0f}px）——压短说明或 note，或加宽 w")
        lay.append((tx_off, tw_, bs, tw_ - nw - (4 if note else 0), nw))
    # A tall light band holding one number reads empty (server lint sparse_container_content: content < 15% of a
    # card ≥ 80px tall and ≥ 20000px²) — cap the stretched height by the content (or just under 80px, where the
    # rule does not apply), shrinking the padding if needed, and spread the spare height into the gaps instead.
    def _area(d, L):
        unit = str(d.get("unit") or "")
        a = (lint_w(str(d["value"]), L[2], True) + (lint_w(" " + unit, us, True) if unit else 0)) * L[2] * 1.2
        a += lint_w(str(d["label"]), ls) * ls * 1.2 + (lint_w(str(d["note"]), 12) * 14.4 if d.get("note") else 0)
        a += 1156 if d.get("icon") else 0
        if d.get("bar"):
            a += (cw - 16 - L[0]) * (6 if d["bar"][0] != "compare" else 4 * len(d["bar"][1]))
        return a
    area = min(_area(d, L) for d, L in zip(its, lay))
    cap = max(area / max(0.2 * cw, 1), 79)   # 0.2: margin over the 15% threshold (our width estimate runs wide)
    gap_ = gap
    if ch > cap:
        new_ch = cap
        while need(pad) > new_ch and pad > 2:   # the band may hug its content (2px) to stay under the 80px rule
            pad -= 1
        new_ch = max(new_ch, need(pad))
        if new_ch < ch:
            if not horizontal and n > 1:
                gap_ = (h - n * new_ch) / (n - 1) if h else gap
            ch = new_ch
    deco, icons, texts = [], [], []
    rect = lambda x_, y_, w_, h_, col: (f'<shape type="rect" topLeftX="{x_:.1f}" topLeftY="{y_:.1f}" width="{w_:.1f}" '
                                        f'height="{h_:.1f}"><fill><fillColor color="{_c(col)}"/></fill></shape>')
    for i, (d, (tx_off, tw_, bs, lw_, nw)) in enumerate(zip(its, lay)):
        cx = x + i * (cw + gap) if horizontal else x
        cy = y if horizontal else y + i * (ch + gap_)
        main = C["accent"] if d["focus"] else C["main"]
        num_col = C["accent"] if d["focus"] else C["ink"]
        deco.append(rect(cx, cy, cw, ch, _CARD_BAND))
        deco.append(rect(cx, cy, cw if rule == "top" else 4, 3 if rule == "top" else ch, main))
        body_h = big * 1.35 + ls * 1.4 + (6 + bar_h if has_bar else 0)
        top = cy + max(pad, (ch - body_h) / 2)   # content block centred vertically in the stretched card
        tx = cx + tx_off
        if d.get("icon"):
            t = _icon_type(d["icon"], "kpi_cards icon")
            by = top + (big * 1.35 + ls * 1.4) / 2 - 17
            deco.append(f'<shape type="ellipse" topLeftX="{cx + 16:.1f}" topLeftY="{by:.1f}" width="34" height="34">'
                        f'<fill><fillColor color="{_c(main)}"/></fill></shape>')
            icons.append(f'<icon iconType="{escape(t)}" topLeftX="{cx + 23:.1f}" topLeftY="{by + 7:.1f}" width="20" '
                         f'height="20"><fill><fillColor color="rgba(255,255,255,1)"/></fill></icon>')
        val, unit = str(d["value"]), str(d.get("unit") or "")
        num = (f'<p><span fontFamily="Georgia" fontSize="{bs}" bold="true" color="{_c(num_col)}">{escape(val)}</span>'
               + (f'<span fontSize="{us}" bold="true" color="{_c(C["ink"])}"> {escape(unit)}</span>' if unit else "")
               + "</p>")
        texts.append(_box(tx, top, tw_, big * 1.35, num, bs, num_col, font))
        ly = top + big * 1.35
        texts.append(_box(tx, ly, lw_, ls * 1.4, f"<p>{escape(str(d['label']))}</p>", ls, _KPI_GREY, font))
        if d.get("note"):
            texts.append(_box(tx + tw_ - nw, ly + 1, nw, ls * 1.4, f"<p>{escape(str(d['note']))}</p>", 12, _KPI_GREY,
                              font, align="right"))
        spec = _kpi_bar(d.get("bar"), C, main)
        if spec:
            kind, rows = spec
            bx, bw_, byy = tx, cx + cw - 16 - tx, ly + ls * 1.4 + 6
            th_ = 4 if kind == "compare" else 6
            if kind in ("share", "parts"):
                deco.append(rect(bx, byy, bw_, th_, _KPI_TRACK))
            for r_, segs in enumerate(rows):
                for x0, fr, col in segs:
                    if fr > 0:
                        deco.append(rect(bx + x0 * bw_, byy + r_ * (th_ + 2), fr * bw_, th_, col))
    xml = "".join(deco + icons + texts)   # z-order: bands / bars / badges, then icons, then text
    bottom = y + ch if horizontal else y + n * ch + gap_ * (n - 1)
    return xml, bottom


def _speech_kpi_row(x, y, w, h, its, C, font, horizontal):
    """business-deck kpi_cards (business-deck.md fragment A): per item a big main-colour number + small unit and a
    one-line muted caption (label · note), no band / strip / badge / bar; groups split by 1px light-grey rules —
    vertical between columns (horizontal=True), horizontal between stacked rows. focus=True (explicit only) → accent.
    Returns (xml, bottom)."""
    import math
    from ._page import lint_w
    n = len(its)
    sep = C.get("grid", "#E3E3E3")
    cap_size, us = 12, 18
    cw = w / n if horizontal else w
    tw_ = cw - 16
    deco, texts, sizes, caps = [], [], [], []
    for i, d in enumerate(its):
        val, unit = str(d["value"]), str(d.get("unit") or "")
        bs = 48 if horizontal else 40
        while bs > 24 and lint_w(val, bs, True) + (lint_w(unit, us, True) if unit else 0) > tw_ - 6:
            bs -= 2
        if lint_w(val, bs, True) + (lint_w(unit, us, True) if unit else 0) > tw_ - 6:
            raise ValueError(f"kpi_cards：第 {i + 1} 组完整数值与单位一行放不下——加宽 w 或减少组数")
        cap = str(d["label"]) + (f" · {d['note']}" if d.get("note") else "")
        lines = max(1, math.ceil(lint_w(cap, cap_size) / max(tw_ - 6, 1)))
        if lines > 2:
            raise ValueError(f"kpi_cards：第 {i + 1} 组口径 '{cap[:14]}' 超过两行——压短 label / note")
        sizes.append(bs)
        caps.append((cap, lines))
    row_h = max(bs * 1.3 for bs in sizes) + max(l for _, l in caps) * cap_size * 1.45 + 6
    if not horizontal and h:
        row_h = max(row_h, (h - 12 * (n - 1)) / n) if h >= n * row_h else row_h
    for i, d in enumerate(its):
        bs, (cap, lines) = sizes[i], caps[i]
        gx = x + i * cw if horizontal else x
        gy = y if horizontal else y + i * (row_h + 12)
        col = C["accent"] if d.get("focus") else C["main"]
        unit = str(d.get("unit") or "")
        num = (f'<p><span fontSize="{bs}" bold="true" color="{_c(col)}">{escape(str(d["value"]))}</span>'
               + (f'<span fontSize="{us}" color="{_c(col)}">{escape(unit)}</span>' if unit else "") + "</p>")
        align = "center" if horizontal else "left"
        texts.append(_box(gx + 8, gy, tw_, bs * 1.3, num, bs, col, font, align=align))
        texts.append(_box(gx + 8, gy + bs * 1.3 + 4, tw_, lines * cap_size * 1.45, f"<p>{escape(cap)}</p>", cap_size,
                          C.get("sub", _KPI_GREY), font, align=align))
        if i < n - 1:
            if horizontal:
                lx = x + (i + 1) * cw
                deco.append(f'<line startX="{lx:.0f}" startY="{y + 6:.0f}" endX="{lx:.0f}" endY="{y + row_h - 6:.0f}">'
                            f'<border color="{_c(sep)}" width="1"/></line>')
            else:
                ly = gy + row_h + 6
                deco.append(f'<line startX="{x:.0f}" startY="{ly:.0f}" endX="{x + w:.0f}" endY="{ly:.0f}">'
                            f'<border color="{_c(sep)}" width="1"/></line>')
    bottom = y + row_h if horizontal else y + n * row_h + 12 * (n - 1)
    return "".join(deco + texts), bottom


def _reflow_kpi_cards(origin_x, origin_y, width, total_height, items, colors, font, gap, horizontal, rule="left"):
    """Fit full KPI text in native boxes, retaining the card API's icons, units, focus and real bars."""
    import math
    import sys
    from pathlib import Path
    from ._page import lint_w

    scripts = str(Path(__file__).resolve().parents[2])
    if scripts not in sys.path:
        sys.path.append(scripts)
    if __package__ == "svg_lib.exhibit":
        from _exhibit_text_fit import _measure
        from _exhibit_xml_lint import tokenize_for_wrap
    else:
        from ..._exhibit_text_fit import _measure
        from ..._exhibit_xml_lint import tokenize_for_wrap

    count = len(items)
    cw = (width - gap * (count - 1)) / count if horizontal else width
    available = total_height if horizontal else ((total_height - gap * (count - 1)) / count if total_height is not None else None)
    text_width = math.floor(cw - 32)
    if text_width <= 6 or (available is not None and available <= 0):
        raise ValueError("kpi_cards：完整指标放不下——加宽 w 或加高 h；不会截短标签、丢弃 note 或减少卡片")
    specs = [_kpi_bar(item.get("bar"), colors, colors["accent"] if item["focus"] else colors["main"]) for item in items]

    def paragraph(text, size):
        lines, line = [], ""
        for kind, token in tokenize_for_wrap(str(text)):
            if kind != "space" and line and lint_w(line + token, size) > text_width - 6:
                lines.append(line)
                line = token
            else:
                line += token
        lines.append(line)
        return "".join(f'<p lineSpacing="multiple:1.2">{escape(part)}</p>' for part in lines)

    def text_box(left, top, width, height_, body, size, color):
        return _box(left, top, width, height_, body, size, color, font).replace('<content ', '<content wrap="false" ', 1)

    def height(body, width, size):
        return math.ceil(_measure(text_box(0, 0, width, 1, body, size, colors["ink"])) * 1.06) + 2

    layout = None
    for big, label_size, note_size in ((28, 14, 12), (26, 13, 12), (24, 12, 11), (22, 11, 11), (20, 11, 11), (18, 11, 11)):
        candidate = []
        for item, spec in zip(items, specs):
            offset = 62 if item.get("icon") else 16
            number_width = math.floor(cw - offset - 16)
            value, unit = str(item["value"]), str(item.get("unit") or "")
            if lint_w(value, big, True) + (lint_w(" " + unit, 15, True) if unit else 0) > number_width - 6:
                break
            label, note = str(item["label"]), str(item.get("note") or "")
            if any(lint_w(token, size) > text_width - 6 for text, size in ((label, label_size), (note, note_size))
                   for kind, token in tokenize_for_wrap(text) if kind == "word"):
                break
            number = (f'<p lineSpacing="multiple:1.2"><span fontFamily="Georgia" fontSize="{big}" bold="true">'
                      f'{escape(value)}</span>' + (f'<span fontSize="15" bold="true" color="{_c(colors["ink"])}"> '
                                                  f'{escape(unit)}</span>' if unit else "")
                      + "</p>")
            number_height = max(height(number, number_width, big), 34 if item.get("icon") else 0)
            label_height = height(paragraph(label, label_size), text_width, label_size)
            note_height = height(paragraph(note, note_size), text_width, note_size) if note else 0
            bar_height = (len(spec[1]) * 6 - 2 if spec[0] == "compare" else 6) if spec else 0
            body_height = number_height + 2 + label_height + (2 + note_height if note else 0) + (6 + bar_height if spec else 0)
            candidate.append((offset, number_width, number, number_height, label_height, note_height, body_height))
        if len(candidate) == count and (available is None or max(row[-1] for row in candidate) + 8 <= available):
            layout = candidate
            break
    if layout is None:
        bounds = f"{width:g}×{total_height:g}px" if total_height is not None else f"{width:g}px 宽"
        raise ValueError(f"kpi_cards：{count} 张完整指标在 {bounds} 放不下（标签/note 至少 11px）——"
                         "加宽 w 或加高 h；不会截短标签、丢弃 note 或减少卡片")
    card_height = max(row[-1] for row in layout) + 16
    if available is not None:
        card_height = min(card_height, available)
    card_gap = ((total_height - count * card_height) / (count - 1)
                if total_height is not None and not horizontal and count > 1 else gap)
    deco, icons, texts = [], [], []

    def rect(left, top, width, height_, color):
        return (f'<shape type="rect" topLeftX="{left:.1f}" topLeftY="{top:.1f}" width="{width:.1f}" '
                f'height="{height_:.1f}"><fill><fillColor color="{_c(color)}"/></fill></shape>')

    for index, (item, row, spec) in enumerate(zip(items, layout, specs)):
        offset, number_width, number, number_height, label_height, note_height, body_height = row
        left = origin_x + index * (cw + gap) if horizontal else origin_x
        top = origin_y if horizontal else origin_y + index * (card_height + card_gap)
        main = colors["accent"] if item["focus"] else colors["main"]
        num_color = colors["accent"] if item["focus"] else colors["ink"]
        deco.extend((rect(left, top, cw, card_height, _CARD_BAND),
                     rect(left, top, cw if rule == "top" else 4, 3 if rule == "top" else card_height, main)))
        text_top = top + (card_height - body_height) / 2
        if item.get("icon"):
            icon_type = _icon_type(item["icon"], "kpi_cards icon")
            badge_top = text_top + (number_height - 34) / 2
            deco.append(f'<shape type="ellipse" topLeftX="{left + 16:.1f}" topLeftY="{badge_top:.1f}" width="34" '
                        f'height="34"><fill><fillColor color="{_c(main)}"/></fill></shape>')
            icons.append(f'<icon iconType="{escape(icon_type)}" topLeftX="{left + 23:.1f}" topLeftY="{badge_top + 7:.1f}" '
                         'width="20" height="20"><fill><fillColor color="rgba(255,255,255,1)"/></fill></icon>')
        texts.append(text_box(left + offset, text_top, number_width, number_height, number, big, num_color))
        label_top = text_top + number_height + 2
        texts.append(text_box(left + 16, label_top, text_width, label_height, paragraph(item["label"], label_size),
                              label_size, _KPI_GREY))
        bar_top = label_top + label_height
        if item.get("note"):
            texts.append(text_box(left + 16, bar_top + 2, text_width, note_height, paragraph(item["note"], note_size),
                                  note_size, _KPI_GREY))
            bar_top += 2 + note_height
        if spec:
            kind, rows = spec
            thickness = 4 if kind == "compare" else 6
            bar_top += 6
            if kind in ("share", "parts"):
                deco.append(rect(left + 16, bar_top, text_width, thickness, _KPI_TRACK))
            for row_index, segments in enumerate(rows):
                for start, fraction, color in segments:
                    if fraction > 0:
                        deco.append(rect(left + 16 + start * text_width, bar_top + row_index * (thickness + 2),
                                         fraction * text_width, thickness, color))
    bottom = origin_y + card_height if horizontal else origin_y + count * card_height + card_gap * (count - 1)
    return "".join(deco + icons + texts), bottom


def _kpi_column(x, y, w, h, items, palette, font, cut=None, horizontal=False, rule="left"):
    """Summary KPI cards preserve every selected metric, full label and note; impossible fits raise explicitly."""
    items = [_kpi_item(item) for item in items]
    try:
        return kpi_cards(x, y, w, items, h=h, palette=palette, font=font, horizontal=horizontal, rule=rule)
    except ValueError:
        return kpi_cards(x, y, w, items, h=h, palette=palette, font=font, horizontal=horizontal, reflow=True, rule=rule)


def exec_summary(f, situation, complication, answers, kpi_items, risk=None, palette=None,
                 font="思源黑体", lang=None):
    """Executive summary: a dark left panel (complication as one bold white statement + 2–4 big KPI numbers) and, on
    white, a grey situation line over three numbered recommendations — each a cut-end ribbon carrying the claim (one
    plain sentence the reader understands, no label in front of it) and one evidence sentence.
    answers=[(claim, evidence, refs)]; refs stay in the notes, not on the page (the contents page carries page numbers).
    SCQA stays internal: no visible labels. Overflow raises. Returns XML for f.publish(...)."""
    return _exec_summary(f, situation, complication, answers, kpi_items, risk, palette, font, lang)


_NO_LINE_START = "，。；、：）)》”’,.;:%!?！？"
_NO_LINE_END = "（(《“‘"


def _exec_summary(f, situation, complication, answers, kpi_items, risk=None, palette=None, font="思源黑体", lang=None):
    import math
    from ._palette import _mix, contrast
    from ._page import lint_w
    if __package__ == "svg_lib.exhibit":
        from _exhibit_text_fit import _measure
        from _exhibit_xml_lint import tokenize_for_wrap
    else:
        from ..._exhibit_text_fit import _measure
        from ..._exhibit_xml_lint import tokenize_for_wrap

    page_palette = palette if palette is not None else {"exhibit": f.C}
    C = roles(page_palette)
    f.summary = True
    zh = (lang or ("zh" if has_cjk(str(situation) + str(complication)) else "en")) == "zh"
    top, bottom = f.top, f.bottom
    panel = C["deep"] if contrast(C["main"]) < 7 else C["main"]
    soft = _mix(panel, "#FFFFFF", 0.66)
    ribbon_fill = _mix(C["main"], "#FFFFFF", 0.9)

    def lines_of(text, size, width, bold=False):
        out, line = [], ""
        for kind, tok in tokenize_for_wrap(str(text)):
            if kind != "space" and lint_w(tok, size, bold) > width - 8:
                raise ValueError("exec_summary：完整词语放不下——缩短表达；不会截短论据")
            if kind != "space" and line and lint_w(line + tok, size, bold) > width - 8 and tok[:1] not in _NO_LINE_START:
                carry = ""
                while line and line[-1] in _NO_LINE_END:
                    carry, line = line[-1] + carry, line[:-1]
                out.append(line.rstrip() + ("" if zh else " "))
                line = carry + tok.lstrip()
            else:
                line += tok
        return out + [line]

    def box(x, y, w, text, size, color, bold=False, spacing=1.25, spans=None):
        ls = lines_of(text, size, w * 0.95, bold)   # rendered mixed CJK/Latin runs wider than lint_w: keep a margin
        body = "".join(f'<p lineSpacing="multiple:{spacing}">{escape(l)}</p>' for l in ls)
        probe = _box(0, 0, w, 1, body, size, color, font, bold).replace("<content ", '<content wrap="false" ', 1)
        h = math.ceil(_measure(probe) * 1.06) + 3
        if spans:   # (prefix, colour): colour the leading tag inside the first line
            pre, col = spans
            body = body.replace(f">{escape(pre)}", f'><span color="{_c(col)}">{escape(pre)}</span>', 1)
        return _box(x, y, w, h, body, size, color, font, bold).replace("<content ", '<content wrap="false" ', 1), h

    def rule(x0, y_, x1, col, w_):
        return (f'<line startX="{x0:.0f}" startY="{y_:.0f}" endX="{x1:.0f}" endY="{y_:.0f}">'
                f'<border color="{_c(col)}" width="{w_}"/></line>')

    parts = []
    # ---- left panel: the complication as one statement, then the KPI numbers
    pw, pad = 268, 22
    px, iw = f.left, 268 - 44
    panel_xml = []
    y = top + pad
    head = str(complication).strip().rstrip("。.")
    if head:
        hs = 15 if lint_w(head, 15, True) < iw * 4.6 else 14
        xml, h = box(px + pad, y, iw, head, hs, "#FFFFFF", bold=True, spacing=1.3)
        panel_xml.append(xml)
        y += h + 14
        panel_xml.append(rule(px + pad, y, px + pw - pad, _mix(panel, "#FFFFFF", 0.3), 1))
        y += 10
    kpis = [k if isinstance(k, dict) else (dict(value=k[0], unit="", label=k[1]) if len(k) == 2 else
                                           dict(value=k[0], unit=k[1], label=k[2])) for k in kpi_items][:4]
    if len(kpis) < 2:
        raise ValueError("exec_summary：kpi_items 至少 2 个（2–4 个关键数字放左栏）")
    size = 26
    blocks = []
    for k in kpis:
        val, unit = str(k.get("value", "")), str(k.get("unit", "") or "")
        lab = " · ".join(str(t) for t in (k.get("label"), k.get("note")) if t)
        lab_xml, lab_h = box(px + pad, 0, iw, lab, 11.5, soft, spacing=1.15) if lab else ("", 0)
        blocks.append((val, unit, lab_xml, size * 1.3 + lab_h))
    room = bottom - pad - y
    need = sum(b[3] for b in blocks)
    if need + 10 * (len(blocks) - 1) > room:
        raise ValueError("exec_summary：左栏放不下——complication 压成一句（≤50 字），或 KPI 减到 3 个")
    gap = min((room - need) / max(1, len(blocks) - 1), 48)
    for val, unit, lab_xml, bh in blocks:
        vw = lint_w(val, size, True) * 1.02 + 5
        panel_xml.append(_box(px + pad, y, vw + 2, size * 1.3, f"<p>{escape(val)}</p>", size, "#FFFFFF", "Georgia",
                              bold=True))
        if unit:
            panel_xml.append(_box(px + pad + vw, y + size * 0.55, max(20, iw - vw), 18, f"<p>{escape(unit)}</p>", 12,
                                  "#FFFFFF", font))
        if lab_xml:
            panel_xml.append(lab_xml.replace('topLeftY="0"', f'topLeftY="{y + size * 1.3:.0f}"', 1))
        y += bh + gap
    panel_h = y - gap + pad - top
    if panel_h > 0.8 * (bottom - top):   # nearly full height: run it to the bottom so both columns end together
        panel_h = bottom - top
    parts.append(f'<shape type="rect" topLeftX="{px}" topLeftY="{top}" width="{pw}" height="{panel_h:.0f}">'
                 f'<fill><fillColor color="{_c(panel)}"/></fill></shape>')
    parts += panel_xml
    # ---- right: situation line, then numbered ribbon claims with one evidence sentence each
    rx = px + pw + 30
    rw = f.right - rx
    y = top + 2
    ctx = str(situation).strip().rstrip("。.")
    if ctx:
        xml, h = box(rx, y, rw, ctx, 13, C["sub"], spacing=1.3)
        parts.append(xml)
        y += h + 12
        parts.append(rule(rx, y, f.right, C["main"], 2))
    items = []
    for lead, ev, *_ in answers:
        lead = str(lead).strip()
        sep = next((s for s in ("：", ": ") if s in lead and len(lead.split(s, 1)[0]) <= (6 if zh else 16)), None)
        # a short "稳健：" / "观察：" label in front of the claim is a category word the reader does not need: dropped
        claim = lead.split(sep, 1)[1].strip() if sep else lead
        items.append(("", claim, str(ev).strip()))
    num_w, rib_pad = 52, 12
    tx = rx + num_w
    tw_ = f.right - tx
    for size in (16, 15, 14):
        ribbon_width, ribbon_height = tw_, 10
        for iteration in range(8):
            rows = []
            claim_width = ribbon_width - rib_pad - ribbon_height / 2
            for tag, claim, evidence_text in items:
                text = (f"{tag}｜" if tag else "") + claim
                claim_height = box(0, 0, claim_width, text, size + 2, C["ink"], bold=True)[1]
                evidence_height = (box(0, 0, tw_ - rib_pad, evidence_text, size, C["text"], spacing=1.3)[1]
                                   if evidence_text else 0)
                rows.append((tag, claim, text, evidence_text, claim_height, evidence_height))
            measured_height = max(row[4] for row in rows) + 10
            longest = max(lint_w(row[2], size + 2, True) for row in rows)
            measured_width = min(tw_, math.ceil(longest / 0.95) + 2 * rib_pad + measured_height / 2 + 8)
            if (ribbon_width, ribbon_height) == (measured_width, measured_height):
                break
            ribbon_width, ribbon_height = measured_width, measured_height
        else:
            continue
        required_height = max(ribbon_height + 10 + row[5] for row in rows)
        if (required_height + 18) * len(rows) <= bottom - y - 8:
            break
    else:
        raise ValueError("exec_summary：14pt 仍放不下——每条主张一句（≤18 字）、证据一句；展开论据放证据页或讲稿")
    y += 8
    rh = (bottom - y) / max(1, len(rows))
    rib_h, rib_w = ribbon_height, ribbon_width
    for i, (tag, claim, text, ev, ch, eh) in enumerate(rows, 1):
        cy = y + (rh - (rib_h + 10 + eh)) / 2
        parts.append(f'<shape type="home-plate" topLeftX="{tx:.0f}" topLeftY="{cy:.0f}" width="{rib_w:.0f}" '
                     f'height="{rib_h:.0f}"><fill><fillColor color="{_c(ribbon_fill)}"/></fill></shape>')
        parts.append(_box(rx, cy + (rib_h - 40) / 2, num_w - 8, 40, f'<p lineSpacing="multiple:1.0">{i:02d}</p>', 28,
                          C["main"], "Georgia", bold=True))
        xml, _ = box(tx + rib_pad, cy + (rib_h - ch) / 2, rib_w - rib_pad - rib_h / 2, text, size + 2, C["ink"],
                     bold=True, spans=(f"{tag}｜", C["main"]) if tag else None)
        parts.append(xml)
        if ev:
            parts.append(box(tx + rib_pad, cy + rib_h + 10, tw_ - rib_pad, ev, size, C["text"], spacing=1.3)[0])
        y += rh
        if i < len(rows):
            parts.append(rule(tx, y, f.right, C["grid"], 1))
    if risk:
        note = ("关键风险：" if zh else "Risk watch: ") + str(risk)
        if note not in (f.note or "").splitlines():
            f.note = "\n".join(filter(None, (f.note, note)))
    return "".join(parts)


# a page-reference cell ("P9", "P9/P12", "P4、P12、P18", "P4–P6", "第 3 页"): such a column is right-aligned like numbers
PAGE_REF_RE = re.compile(r"^(?:第\s*\d+(?:\s*[-–~、,，/]\s*\d+)*\s*页|[Pp]\.?\s*\d+(?:\s*(?:[-–~、,，/]|及|和|and)\s*"
                         r"(?:[Pp]\.?\s*)?\d+)*)\s*(?:…|\.\.\.)?$")


def text_table(x, y, w, header, rows, widths=None, palette=None, font="思源黑体", size=12, h=None,
               bold_first=True, first_col="auto"):
    """Native XML text table for appendix / definition / assumption pages (wraps text, no chart needed).
    header: column names; rows: list of lists of strings; widths: column fractions (default equal). Row heights
    follow the wrapped text and stretch to fill h (pass h=f.bottom − y so the table reaches the page bottom); raises
    if it overflows h — split into two tables or two pages. Text columns are left-aligned; columns whose cells are all
    numbers (1,234 / 12.5% / +3.2pp / ¥45 / 2.1x, blanks like 未披露/— ignored) or page references (P9 / P9/P12 /
    P4、P12、P18 / 第 3 页) are right-aligned, header included. Each column's text spans exactly its head rule: left text
    starts at the rule's left end, right-aligned text ends at its right end.
    first_col="auto" (default): "plain" — bold ink text, no block (a column of solid blocks reads like a bar chart).
    first_col="fill" (McKinsey): each first-column cell is a solid dark block (palette main, deep when main is
    too light) with white bold text and a white gap between blocks; the head cell keeps the plain bold head + rule, and
    the row hairlines start at the second column. first_col="plain": the first column is ordinary bold ink text.
    Returns (xml, bottom_y)."""
    C = roles(palette)
    from ._table import _label_colors
    from ._page import first_col_mode
    mode1 = first_col_mode(first_col, [r[0] for r in rows if r])
    fill1 = mode1 in ("fill", "light") and len(header) >= 2
    blk = _label_colors(C)[0]
    blk_ink = "#FFFFFF"
    if mode1 == "light":
        from ._table import _light_block
        blk, blk_ink = _light_block(C), C["deep"]
    bpad = 8 if fill1 else 0   # text inset inside the first-column block
    from ._table import check_risk_levels
    for j, h_ in enumerate(header):   # a risk register's level column: 高/中/低 only
        if re.search(r"等级|级别|level|rating", str(h_), re.I):
            check_risk_levels([r[j] for r in rows if j < len(r)], f"text_table 列 {h_!r}")
    num_re = re.compile(r"^[~≈<>≥≤]?\s*[+\-−]?[¥$€£]?\s*\d[\d,]*(\.\d+)?\s*(%|pp|x|×|倍|亿|万|bp|bps|[A-Za-z]{0,3})?[¹²³⁴⁵*]*$")
    blank = {"", "—", "-", "–", "n/a", "N/A", "n.m.", "未披露", "null", "None"}
    def _pages(j):   # a page-reference column — not a priority / tier column (P0 / P1 / P2)
        cells = [str(r[j]).strip() for r in rows if str(r[j]).strip() not in blank]
        return (not re.search(r"优先|等级|级别|阶段|档|priority|tier|phase|level", str(header[j]), re.I)
                and not any(re.match(r"^[Pp]0\b", c) for c in cells))

    right = [any(str(r[j]).strip() not in blank for r in rows) and
             all(num_re.match(str(r[j]).strip()) or (PAGE_REF_RE.match(str(r[j]).strip()) and _pages(j))
                 for r in rows if str(r[j]).strip() not in blank)
             for j in range(len(header))]
    widths = widths or [1 / len(header)] * len(header)
    tot = sum(widths)
    cw = [w * f / tot for f in widths]
    xs = [x + sum(cw[:i]) for i in range(len(cw))]
    # gap after each column; the head rule ends there too, so right-aligned text ends exactly at its rule's right end
    pad = [min(10, max(8, cw[j] * 0.15)) if right[j] else 8 for j in range(len(header))]

    def _height(s):
        l_ = s * 1.35
        hh_ = max(len(wrap(str(t), s, cw[j] - pad[j], bold=True)) for j, t in enumerate(header)) * l_ + 8
        return hh_ + sum(max(len(wrap(str(t), s, (cw[j] - pad[j] - 2 - (2 * bpad if j == 0 else 0)) * 0.9,
                                     bold=fill1 and j == 0)) for j, t in enumerate(r)) * l_ + 8 + (4 if fill1 else 0)
                         for r in rows)
    if h and rows:   # spare height grows the type first (to 16pt), so cells don't dwarf small text
        while size < 16 and _height(size + 0.5) <= h * 0.92:
            size += 0.5
    row_pad = 8
    if h and rows and _height(size) > h + 1:   # overflow: ≤15 % is absorbed by tighter rows, more is split advice
        over = _height(size) - h
        tight = _height(size) - 4 * len(rows)   # cell padding 8 → 4px per row, same font
        from ._layouts import SQUEEZE_MAX, _squeezed, split_hint
        if over <= SQUEEZE_MAX * h and tight <= h + 1:
            row_pad = 4
            _squeezed(f"text_table 超出 {over:.0f}px（{over / h:.0%}）：已把行内留白 8→4px，字号不变")
        else:
            per = (_height(size) - (max(len(wrap(str(t), size, cw[j] - pad[j], bold=True)) for j, t in enumerate(header))
                                    * size * 1.35 + 8)) / len(rows)
            fit = int((h - 40) / max(per, 1))
            raise ValueError(f"text_table 超高 {over:.0f}px（{len(rows)} 行，超出 {over / h:.0%}，>{SQUEEZE_MAX:.0%} 不自动压缩）："
                             "删减行与文字，或缩短最长那列（附录也不缩到 12pt 以下）；" + split_hint("text_table", len(rows), fit))
    lh = size * 1.35
    out, cy = [], y
    hlines = [len(wrap(str(t), size, cw[j] - pad[j], bold=True)) for j, t in enumerate(header)]
    hh = max(hlines) * lh + 4
    for j, t in enumerate(header):   # McKinsey: bold ink heads, a main-colour rule under each column (gaps between)
        out.append(_box(xs[j], cy, cw[j] - pad[j], hh, f"<p>{escape(t)}</p>", size, C["ink"], font, bold=True,
                        align="right" if right[j] else "left"))
    cy += hh + 4
    for j in range(len(header)):
        x_a, x_b = xs[j], xs[j] + cw[j] - pad[j]   # = the column's text box: left text starts at x_a, right ends at x_b
        out.append(f'<line startX="{x_a:.0f}" startY="{cy - 3:.0f}" endX="{x_b:.0f}" endY="{cy - 3:.0f}">'
                   f'<border color="{_c(C["main"])}" width="2"/></line>')
    need = [max(len(wrap(str(t), size, (cw[j] - pad[j] - 2 - (2 * bpad if j == 0 else 0)) * 0.9, bold=fill1 and j == 0))
                for j, t in enumerate(r)) * lh + row_pad + (4 if fill1 else 0) for r in rows]
    extra = max(0.0, (h - (hh + 4) - sum(need)) / len(rows)) if (h and rows) else 0.0
    extra = min(extra, 2.5 * lh)   # rows stretch to fill h (no half-empty appendix) but never balloon
    blocks = []
    for r, base in zip(rows, need):
        rh = base + extra
        for j, t in enumerate(r):
            if j == 0 and fill1:   # solid block, 3px white gap above and below (the gaps separate the rows)
                bw = cw[0] - pad[0]
                blocks.append(f'<shape type="rect" topLeftX="{xs[0]:.0f}" topLeftY="{cy + 3:.0f}" width="{bw:.0f}" '
                              f'height="{rh - 6:.0f}"><fill><fillColor color="{_c(blk)}"/></fill></shape>')
                out.append(_box(xs[0] + bpad, cy + 3, bw - 2 * bpad, rh - 6,
                                f'<p lineSpacing="multiple:1.15">{escape(str(t))}</p>', size, blk_ink, font, bold=True,
                                valign="middle"))
                continue
            out.append(_box(xs[j], cy + 2, cw[j] - pad[j], rh - 2, f'<p lineSpacing="multiple:1.15">{escape(str(t))}</p>',
                            size, C["ink"] if (bold_first and j == 0) else C["text"], font, bold=bold_first and j == 0,
                            align="right" if right[j] else "left", valign="middle" if extra > lh else "top"))
        cy += rh
        last = r is rows[-1]
        dash_ = "" if last else ' dashArray="dash"'
        lx = xs[1] if (fill1 and not last) else x   # hairlines never run through the first-column blocks
        out.append(f'<line startX="{lx:.0f}" startY="{cy:.0f}" endX="{x + w:.0f}" endY="{cy:.0f}">'
                   f'<border color="rgb(191,191,191)" width="1"{dash_}/></line>')
    out = blocks + out   # blocks under the text
    if h is not None and cy - y > h + 1:
        raise ValueError(f"text_table 超高 {cy - y - h:.0f}px：拆成两张表 / 两页，或删减行与文字（附录也不缩到 12pt 以下）")
    return "".join(out), cy


def republish_xml(xml_path, deck, page, cwd=None, waive=()):
    """Re-send a page XML saved by f.publish (``.lark-slides/xml/<deck>/pNN.xml``) after editing it by hand — a title word,
    a number, a footnote, deleting a label. Overwrites page N in place (same slide), with server lint as usual.
    Chart structure changes go through the page function, not the XML."""
    from pathlib import Path as _Path
    from ..atomize_svg_to_slide._exhibit_publish import publish_slide
    p = _Path(xml_path)
    if not p.is_absolute():
        p = _Path(cwd or ".") / p
    from ..atomize_svg_to_slide._exhibit_publish import (_frozen_lock, FROZEN_MSG, _EXPORTED_MSG, SEAL_MSG, seal_broken,
                                                 refusal_hint)
    if seal_broken(cwd or ".", deck):
        print(f"P{page} 未写入：{SEAL_MSG}")
        return {"ok": False, "skipped": True, "finished": True, "seal": True}
    if _frozen_lock(cwd or ".", page, deck) is not None:
        print(f"P{page} 未写入：{refusal_hint(cwd, FROZEN_MSG, deck)}")
        return {"ok": False, "skipped": True, "finished": True, "frozen": True}
    for d_ in _sync_dirs(cwd, deck):   # same freeze as f.publish: no rework after export / organizer_done
        import json as _jj
        try:
            st_ = _jj.loads((d_ / "status.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            st_ = {}
        if (d_ / "exported").exists() or st_.get("finished_at") or int(page) in (st_.get("frozen") or []):
            print(f"P{page} 未写入：deck 已导出/冻结——{refusal_hint(cwd, _EXPORTED_MSG, deck)}")
            return {"ok": False, "skipped": True, "finished": True}
    r = publish_slide(p.read_text(encoding="utf-8"), presentation=deck, page=page, cwd=cwd, waive=waive)
    if r.get("ok"):
        print(f"P{page} ok（按 {p.name} 重发）")
    else:
        print(f"P{page} 被拦 {len(r.get('errors', []))} 条：")
        for e in r.get("errors", [])[:8]:
            from . import _refusal as _rf
            print("  -", _rf.line(e))
    return r


def _nav_numbers_unbacked(cwd, deck, answer, kpis, descs):
    """Amounts in the P2 answer / kpis / chapter descs that no research constant carries (multiagent_sync's
    plan check, applied to the text actually being printed). [] outside a multi-agent task."""
    import sys as _s
    from pathlib import Path as _P
    dirs = [d for d in _sync_dirs(project_root(cwd), _resolve_deck(deck, cwd)) if (d / "research").exists()]
    if not dirs:
        return []
    text = " ".join([str(answer or "")] + [" ".join(str(x) for x in k) if isinstance(k, (list, tuple)) else str(k)
                                          for k in (kpis or [])] + [str(v) for v in (descs or {}).values()])
    _s.path.insert(0, str(_P(__file__).resolve().parents[2]))
    try:
        from multiagent_sync import _prose_numbers_unbacked
        return _prose_numbers_unbacked({"STORY": {"x": text}, "F": {}, "PAGES": []}, dirs[0])
    except Exception:  # noqa: BLE001 — a hint only
        return []
    finally:
        _s.path.pop(0)


def publish_contents_and_navs(sections, pages, descs=None, question=None, answer=None, kpis=None, deck=None, cwd=None,
                              deck_name=None, palette=None, note=None, contents_page=3, who="main", only=None,
                              summary_page=2, points=None):
    """One call for the whole front + navigation set: the executive summary page (summary_page, when answer= is given:
    question → answer → kpis, and 3–5 supporting conclusions — points=[(conclusion, evidence)], default one per chapter
    from descs), the contents page (contents_page; None = none) and every chapter navigation page of PAGES (recipe
    chapter_nav), all from the same SECTIONS / PAGES / descs — same look, consistent page ranges. Cover → summary →
    contents → chapters: chapter 1 starts after the contents page. Publishes them one after another (each through
    Frame.publish, so claims / ledgers update) and returns {page: publish result}. only=[pages] rewrites just those."""
    if isinstance(pages, dict):
        rows = [dict(p=k, title=v) if isinstance(v, str) else dict(v, p=k) for k, v in pages.items()]
    else:
        rows = [r for r in (pages or []) if isinstance(r, dict)]
    summary_page = int(summary_page) if answer and summary_page else None
    if contents_page and summary_page and int(contents_page) == summary_page:   # old call (summary + contents in one)
        contents_page = summary_page + 1
    contents_page = int(contents_page) if contents_page else None
    front = [p for p in (summary_page, contents_page) if p]
    if not front:
        raise ValueError("publish_contents_and_navs：既没有 answer=（执行摘要页）也没有 contents_page（目录页）")
    clash = [int(r["p"]) for r in rows if str(r.get("p", "")).isdigit() and int(r["p"]) in front
             and str(r.get("recipe") or r.get("title") or "").strip()   # a bare dict(p=2) row says nothing
             and not re.match(r"\s*(contents|目录|exec_summary|执行摘要|摘要|summary)", str(r.get("recipe") or r.get("title")), re.I)]
    sec_front = {int(k): str(v) for k, v in (sections or {}).items() if str(k).isdigit() and int(k) in front
                 and not re.match(r"\s*(目录|执行摘要|摘要|contents|summary|executive)", str(v), re.I)}
    if clash or sec_front:
        p_ = sorted(set(clash) | set(sec_front))[0]
        msg = (f"P{p_} 在 plan 里是正文/导航页，但固定结构是 P1 封面 → P{summary_page or '-'} 执行摘要 → P{contents_page or '-'} 目录 → "
               f"第一章从 P{max(front) + 1} 起：把 plan.py 的 SECTIONS / PAGES 页号整体后移（第一章起始页改为 P{max(front) + 1}），"
               "再运行同一条 publish_contents_and_navs")
        print(f"publish_contents_and_navs 未写入：{msg}")
        return {p_: {"ok": False, "errors": [{"key": "front_pages", "message": msg, "fix": msg}], "warnings": []}}
    navs = sorted(int(r["p"]) for r in rows if str(r.get("p", "")).isdigit()
                  and str(r.get("recipe", "")).split("/")[0].strip() == "chapter_nav")
    if not navs:   # PAGES as {page: title}: a row titled exactly as the chapter starting there is its nav
        sec = {int(k): str(v).strip() for k, v in (sections or {}).items() if str(k).isdigit()}
        navs = sorted(int(r["p"]) for r in rows if str(r.get("p", "")).isdigit() and int(r["p"]) not in front
                      and sec.get(int(r["p"])) and str(r.get("title", "")).strip() == sec[int(r["p"])])
        rows = [dict(r, recipe="chapter_nav") if str(r.get("p", "")).isdigit() and int(r["p"]) in navs else r
                for r in rows]
    if not navs:
        print(f"publish_contents_and_navs：PAGES 里没有导航页（recipe='chapter_nav' 的行），这次只写 P{'、P'.join(map(str, front))}；"
              "deck 有章节导航页就传 plan.py 原样的 PAGES（行带 recipe），插页后把其后页号 +1、加上新页一行")
    sections = align_sections(sections, rows)
    if only is None:   # the numbers the summary / navs print must exist in the research (stale pre-research estimates do not)
        stale = _nav_numbers_unbacked(cwd, deck, answer, list(kpis or []) + [" ".join(map(str, x)) if isinstance(x, (list, tuple))
                                                                              else str(x) for x in (points or [])], descs)
        if stale and _first_hold(project_root(cwd), f"held-navnums-{_resolve_deck(deck, cwd)}.json", front[0]):
            msg = (f"执行摘要 / 目录 / 导航页里这些数字在 research 里找不到：{'、'.join(stale[:6])}——多半是研究前写进 plan 的估计"
                   "（CHAPTER_DESCS / STORY / answer / kpis），这些页会原样印出、与正文对不上：改成从 F / research 变量拼"
                   "（f-string），没有出处就删掉这个数，再运行同一条 publish_contents_and_navs（只拦这一次）")
            print(f"P{front[0]} 未写入：{msg}")
            return {front[0]: {"ok": False, "held": [msg], "errors": [], "warnings": []}}
    chap_starts = sorted(int(k) for k, v in sections.items() if int(k) > max(front)
                         and not re.match(r"\s*(目录|执行摘要|摘要|附录|appendix|contents|summary)", str(v), re.I))
    out = {}
    targets = front + navs
    from ..atomize_svg_to_slide import _exhibit_publish as _pubm
    _pubm.NAV_BATCH[0] = True
    try:
        _publish_navs(targets, only, summary_page, contents_page, answer, question, kpis, points, sections, rows, descs,
                      palette, deck, cwd, deck_name, note, chap_starts, who, out)
    finally:
        _pubm.NAV_BATCH[0] = False
    missed = [int(p) for p in (only or []) if not (out.get(int(p)) or {}).get("ok")]
    if missed:   # never let a partial `only=` write pass silently
        why = {p: ("不是执行摘要 / 目录页、PAGES 里也不是导航页（recipe='chapter_nav'）" if p not in targets else "写入没成功（见上面的拦截）")
               for p in missed}
        print("publish_contents_and_navs 未完成：only= 里这些页没写成——"
              + "；".join(f"P{p} {w}" for p, w in why.items())
              + "。传 plan.py 原样的 PAGES（导航页行带 recipe='chapter_nav'，插页后页号已 +1）再跑同一条")
        for p in missed:
            out.setdefault(p, {"ok": False, "errors": [{"key": "nav_not_written", "message": why[p], "fix": why[p]}],
                               "warnings": []})
    return out


def _publish_navs(targets, only, summary_page, contents_page, answer, question, kpis, points, sections, rows, descs,
                  palette, deck, cwd, deck_name, note, chap_starts, who, out):
    zh = has_cjk(" ".join(str(v) for v in sections.values()) + str(answer or "") + str(question or ""))
    for pg in targets:
        if only is not None and pg not in only:
            continue
        if pg == summary_page:
            f = frame("执行摘要" if zh else "Executive summary", page=pg, section=None, palette=palette, deck=deck, cwd=cwd,
                      note=note or (f"本页先给结论：{answer}" if zh else f"The answer first: {answer}"))
            body = contents(f, sections, rows, descs=descs, palette=palette, question=question, answer=answer, kpis=kpis,
                            deck_name=deck_name, points=points)
        elif pg == contents_page:
            f = frame("目录" if zh else "Contents", page=pg, section=None, palette=palette, deck=deck, cwd=cwd,
                      note=("本页是目录：" if zh else "Contents: ") + "；".join(
                          str(v) for k, v in sorted((int(k), v) for k, v in sections.items()) if k in chap_starts))
            body = contents(f, sections, rows, descs=descs, palette=palette, question=question, deck_name=deck_name)
        else:
            k = next((i for i, st in enumerate(chap_starts, 1) if st == pg or st == pg + 1), None)
            if k is None:   # the nav row's page is not a chapter start in SECTIONS: nearest chapter after it
                k = next((i for i, st in enumerate(chap_starts, 1) if st >= pg), len(chap_starts))
            name = str(sections.get(chap_starts[k - 1], sections.get(str(chap_starts[k - 1]), "")))
            f = frame(re.sub(r"^[一二三四五六七八九十]+[、.．]\s*|^\d+[、.．]\s*", "", name) or "章节", page=pg, section=None,
                      palette=palette, deck=deck, cwd=cwd, note=(f"进入第 {k} 章：{name}。" if zh else f"Chapter {k}: {name}. ") + str((descs or {}).get(name, "")))
            body = contents(f, sections, rows, descs=descs, palette=palette, current=k, deck_name=deck_name)
        out[pg] = f.publish(body, deck=deck, page=pg, cwd=cwd, who=who)
        if pg in (summary_page, contents_page) and not (out[pg] or {}).get("ok") and not (out[pg] or {}).get("skipped"):
            print(f"  P{pg} 没写成：其后的目录 / 导航页这次不写（它们用同一份章节描述）；改完后用同一条 publish_contents_and_navs 重跑，"
                  "执行摘要、目录和全部导航页一起写")
            break


def _ellipsize(text, lines, n):
    """text cut to its first n wrapped lines + "…": at a word boundary for Latin text (never "easin…"), one char
    short for CJK so the ellipsis stays on the line."""
    text = str(text)
    if has_cjk(text):
        keep = len("".join(lines[:n]))
        return text[:max(1, keep - 1)].rstrip(" ，,；;、") + "…"
    keep = len(" ".join(lines[:n]))
    head = text[:keep].rstrip()
    if " " in head:   # drop the last word: the ellipsis takes its place on the line
        head = head.rsplit(" ", 1)[0]
    return head.rstrip(" ,;:—–-") + "…"


def _contents_rows(sections, pages, descs, appendix):
    """Chapter rows of plan.py SECTIONS / PAGES for the contents, summary and navigation pages: ([(name, desc, "P4–P6")],
    [(start, end)], appendix). Front pages (cover / summary / contents) are not chapters; ranges skip nav pages."""
    groups = {}
    app_start = None
    if pages is not None:
        sections = align_sections(sections, pages)
    for p, name in sorted((int(k), v) for k, v in sections.items()):
        if re.match(r"\s*(附录|appendix)", str(name), re.I) and app_start is None:
            app_start = p
        if p <= 3 and re.fullmatch(r"\s*(目录|执行摘要|摘要|封面|contents|executive summary|summary|cover|"
                                   r"investment (?:thesis|summary)|key takeaways|投资(?:要点|逻辑|摘要)|核心观点)\s*", str(name), re.I):
            continue   # front pages (summary / thesis before chapter 1) are not chapters
        if appendix is None and re.match(r"\s*(附录|appendix)", str(name), re.I):
            appendix = (str(name).partition("：")[0], f"P{p}  " + (str(name).partition("：")[2] or
                                                               ("口径、假设与来源" if has_cjk(str(name)) else "Definitions, assumptions and sources")))
            continue
        groups.setdefault(name, []).append(p)
    if pages is None:   # multi-agent task: the plan's PAGES (nav pages and appendix rows set the page ranges)
        try:
            import runpy, contextlib, io, sys as _s
            for d_ in _sync_dirs(project_root(None), _resolve_deck(None, None)):
                if (d_ / "plan.py").exists():
                    _s.path.insert(0, str(d_))
                    try:
                        with contextlib.redirect_stdout(io.StringIO()):
                            pages = runpy.run_path(str(d_ / "plan.py"), run_name="contents_pages").get("PAGES")
                    finally:
                        _s.path.remove(str(d_)) if str(d_) in _s.path else None
                    break
        except Exception:  # noqa: BLE001
            pages = None
    if isinstance(pages, dict):   # PAGES passed as {page: title} or {page: row}
        pages = [dict(p=k, title=v) if isinstance(v, str) else dict(v, p=k) for k, v in pages.items()]
    plist = [r for r in (pages or []) if isinstance(r, dict) and str(r.get("p", "")).isdigit()]
    navs = {int(r["p"]) for r in plist if str(r.get("recipe", "")).split("/")[0].strip() in ("chapter_nav", "contents")}
    apx_rows = sorted(int(r["p"]) for r in plist if re.match(r"\s*(appendix|glossary|附录|术语)", str(r.get("recipe", "")), re.I)
                      or re.match(r"\s*(附录|appendix)", str(r.get("title", "")), re.I))
    if apx_rows and (app_start is None or apx_rows[0] < app_start) and apx_rows[0] > max(int(k) for k in sections):
        app_start = apx_rows[0]   # appendix pages that SECTIONS does not list: the last chapter ends before them
    titles = {int(r["p"]): str(r.get("title", "")) for r in plist if int(r["p"]) not in navs}
    last_page = max([int(r["p"]) for r in plist] or [0])
    starts = sorted(ps[0] for ps in groups.values())
    rows, spans = [], []
    for name, ps in groups.items():
        clean = re.sub(r"^[一二三四五六七八九十]+[、.．]\s*|^\d+[、.．]\s*", "", name)
        head, _, tail = clean.partition("：")
        first = min((q for q in titles if q >= ps[0] and not any(ps[0] < s_ <= q for s_ in starts)), default=ps[0])
        d = (descs or {}).get(name) or (descs or {}).get(clean) or tail or re.split(r"[：:]", titles.get(first, ""))[0]
        nxt = [s_ for s_ in starts if s_ > ps[0]]
        end = (nxt[0] - 1) if nxt else ((app_start - 1) if app_start and app_start > ps[0] else (last_page or ps[-1]))
        end = max(end, ps[0])
        while end - 1 >= ps[0] and end in navs:   # the next chapter's navigation page is not this chapter's
            end -= 1
        beg = ps[0]
        while beg + 1 <= end and beg in navs:   # the range starts at the chapter's first content page
            beg += 1
        rng = f"P{beg}" if end == beg else f"P{beg}–P{end}"
        rows.append((head if tail else clean, d, rng))
        spans.append((ps[0], end))
    if not rows:
        raise ValueError("contents：SECTIONS 里没有章节（封面/目录/摘要之外）——传 plan.py 的 SECTIONS")
    holes = [d for _, d, _ in rows if d and re.search(r"_{3,}|＿{2,}|\bXX+\b|[{]\w|待补|待\s*(?:R\d|研究|调研|后续)\s*(?:后)?(?:补|填)|TBD", str(d))]
    if holes:
        raise ValueError(f"contents：章节结论里还有占位（{holes[0][:30]}…）——plan.py 的 CHAPTER_DESCS 用调研回来的数字填好"
                         "（f-string 从 F / research 变量拼）再画目录 / 导航页")
    return rows, spans, appendix


def _summary_points(rows, points, x0, x1, H_, C, font, zh, srv_h):
    """Right side of the executive summary page: 3–5 numbered supporting conclusions (bold) each with one grey
    evidence line, spread over the page height. points=[(conclusion, evidence)] or chapter rows (desc over name)."""
    items = [(str(p[0]), str(p[1]) if len(p) > 1 and p[1] else "") if isinstance(p, (list, tuple)) else (str(p), "")
             for p in (points or [])] or [(d or n, n if d else "") for n, d, _ in rows]
    items = [it for it in items if it[0].strip()][:5]
    if not items:
        return []
    out = [_box(x0, 40, x1 - x0, 22, f"<p>{'核心结论' if zh else 'KEY FINDINGS'}</p>", 12, C["main"], font, bold=True),
           f'<line startX="{x0}" startY="70" endX="{x1}" endY="70"><border color="{_c(C["main"])}" width="2"/></line>']
    top, bot = 82, H_ - 40
    rh = (bot - top) / len(items)
    tw_ = x1 - x0 - 64
    for size in (17, 16, 15, 14):
        ev_size = size - 4
        hs = []
        for c_, e_ in items:
            cp = f'<p lineSpacing="multiple:1.2">{escape(c_)}</p>'
            ch = srv_h(cp, size, True, tw_) or int(size * 1.5) * len(wrap(c_, size, tw_, bold=True)) + 6
            ep = f'<p lineSpacing="multiple:1.2">{escape(e_)}</p>' if e_ else ""
            eh = (srv_h(ep, ev_size, False, tw_) or int(ev_size * 1.5) * len(wrap(e_, ev_size, tw_)) + 6) if e_ else 0
            hs.append((cp, ch, ep, eh))
        if all(ch + eh + 6 <= rh - 10 for _, ch, _, eh in hs):
            break
    else:
        raise ValueError("contents(answer=)：右栏结论放不下——每条结论一句（≤40 字）、证据一句，或减到 3–4 条")
    for i, (cp, ch, ep, eh) in enumerate(hs, 1):
        y = top + (i - 1) * rh
        if i > 1:
            out.append(f'<line startX="{x0}" startY="{y:.0f}" endX="{x1}" endY="{y:.0f}"><border color="{_c(C["grid"])}" '
                       'width="1"/></line>')
        g = ch + (eh + 6 if eh else 0)
        cy = y + (rh - g) / 2
        out.append(_box(x0, cy - 4, 56, 40, f"<p>{i:02d}</p>", 28, C["accent"], "Georgia", bold=True))
        out.append(_box(x0 + 64, cy, tw_, ch, cp, size, C["ink"], font, bold=True))
        if eh:
            out.append(_box(x0 + 64, cy + ch + 6, tw_, eh, ep, ev_size, C["sub"], font))
    return out


def contents(f, sections, pages=None, descs=None, palette=None, font="思源黑体", appendix=None, current=None,
             question=None, deck_name=None, answer=None, kpis=None, points=None):
    """Contents page (current=None) or chapter navigation page (current=N, placed right before chapter N's first page).
    Full-bleed: a palette colour panel on the left third — "CONTENTS" + 目录 + the one question the deck answers
    (question=, e.g. plan.py STORY's core question), or on a navigation page "PART 0N", a big chapter number, the chapter
    name and its one-line conclusion — and on the right every chapter as a row (number, bold name, grey conclusion,
    page range; thin rules). On a navigation page the current chapter row is highlighted (light band + accent bar +
    accent number) and the others are greyed. The frame's own title / rule / footer are replaced; the note and logo stay.
    sections: plan.py SECTIONS {page: "一、章名" or "章名"}; descs: {章名: 一句带数字的结论} (default: the first PAGES title
    of the chapter); appendix: (label, text) shown as a last grey line (default: an 附录 section). deck_name: footer text
    on the panel (default: the deck's cover title is not known here — pass the report name). Returns body XML; the
    frame passed in is rewritten (f.publish(contents(f, …), …)).
    Executive summary page (answer= given; its own page, before the contents page): the left panel carries the question
    (small), the answer (bold, ≤60 字: rating + target price, or the main recommendation) and kpis=[(value, label), …]
    (2–3 big numbers); the right side lists 3–5 supporting conclusions — points=[(conclusion, evidence), …], default
    each chapter's one-line conclusion (descs, with numbers) over its chapter name — filling the page height."""
    C = roles(palette)
    rows, spans, appendix = _contents_rows(sections, pages, descs, appendix)
    zh = has_cjk("".join(r[0] for r in rows))
    me = getattr(f, "page_no", None)
    if current is not None and me is not None and 1 <= int(current) <= len(rows):   # a navigation page highlights the chapter it opens (page ∈ that span)
        own = next((i for i, (a, b) in enumerate(spans, 1) if a <= int(me) <= b), None) or next(
            (i for i, (a, _) in enumerate(spans, 1) if a == int(me) + 1), None)
        if own and own != int(current):
            print(f"contents(current={current})：P{me} 是第 {own} 章的导航页（按 SECTIONS），已改为高亮第 {own} 章")
            current = own
    if current is not None and not 1 <= int(current) <= len(rows):
        raise ValueError(f"contents(current={current})：只有 {len(rows)} 章，current 取 1–{len(rows)}")
    W_, H_ = W, 540
    lw = 312
    out = []
    panel = C["main"]   # contents and chapter navigation pages share one panel colour
    out.append(f'<shape type="rect" topLeftX="0" topLeftY="0" width="{lw}" height="{H_}"><fill><fillColor color="{_c(panel)}"/>'
               '</fill></shape>')
    out.append(f'<shape type="rect" topLeftX="{lw - 6}" topLeftY="0" width="6" height="{H_}"><fill>'
               f'<fillColor color="{_c(C["accent"])}"/></fill></shape>')
    white = "#FFFFFF"
    out.append(f'<line startX="48" startY="{72 if (current is None and answer) else 96}" endX="96" '
               f'endY="{72 if (current is None and answer) else 96}"><border color="{_c(C["accent"])}" width="2"/></line>')
    def _srv_h(paras, size, bold=False, width=None):   # the server's own height estimate: boxes stacked by it never overlap
        try:
            import sys as _s
            from pathlib import Path as _P
            _s.path.insert(0, str(_P(__file__).resolve().parents[2]))
            from _exhibit_text_fit import text_height
            b_ = ' bold="true"' if bold else ""
            return text_height(f'<content fontSize="{size}" fontFamily="{font}"{b_}>{paras}</content>',
                               width=width or (lw - 96), font_size=size)
        except Exception:  # noqa: BLE001
            return 0
        finally:
            _s.path.pop(0)
    if current is None and answer:   # contents + executive summary: question → answer → key numbers
        lw_in = lw - 96
        out.append(_box(48, 40, lw - 90, 22, f"<p>{'执行摘要' if zh else 'EXECUTIVE SUMMARY'}</p>", 12, white, font,
                        bold=True))
        ks = [tuple(k)[:2] for k in (kpis or [])][:3]

        def _left(q_lines, a_size, k_n):   # lay the panel out with the server's heights; returns (parts, bottom)
            parts, y_ = [], 100
            if question and q_lines:
                full = wrap(str(question), 12, lw_in)
                qt = str(question)
                if len(full) > q_lines:   # cut at the end of the last kept line (keeps the question's own spacing)
                    qt = _ellipsize(qt, full, q_lines)
                qp = f"<p>{escape(qt)}</p>"
                qh = _srv_h(qp, 12) or 18 * len(ql) + 6
                parts.append(_box(48, y_, lw_in, qh, qp, 12, white, font))
                y_ += qh + 10
            ap = f"<p>{escape(str(answer))}</p>"   # one paragraph: the server wraps it and sizes the box to the text
            ah = _srv_h(f'<p lineSpacing="multiple:1.2">{escape(str(answer))}</p>', a_size, True) or \
                int(a_size * 1.45) * len(wrap(str(answer), a_size, lw_in, bold=True)) + 8
            parts.append(_box(48, y_, lw_in, ah, ap, a_size, white, font, bold=True)
                         .replace('verticalAlign="top">', 'verticalAlign="top" lineSpacing="multiple:1.2">', 1))
            y_ += ah + 14
            if k_n:
                parts.append(f'<line startX="48" startY="{y_:.0f}" endX="{48 + lw_in}" endY="{y_:.0f}">'
                             '<border color="rgb(255,255,255)" width="1"/></line>')
                y_ += 12
                for v_, l_ in ks[:k_n]:
                    vp = f"<p>{escape(str(v_))}</p>"
                    vh = max(30, _srv_h(vp, 22, True))
                    parts.append(_box(48, y_, lw_in, vh, vp, 22, white, font, bold=True))
                    lp = f"<p>{escape(str(l_))}</p>"
                    lh = max(18, _srv_h(lp, 11))
                    parts.append(_box(48, y_ + vh, lw_in, lh, lp, 11, white, font))
                    y_ += vh + lh + 10
            return parts, y_

        if len(str(answer)) > (90 if has_cjk(str(answer)) else 200):
            raise ValueError(f"contents(answer=)：答案 {len(str(answer))} 字太长——≤60 字一句话给结论（评级 + 目标价，或主建议），论据放各章结论")
        limit = H_ - 54 - (24 if deck_name else 0)
        # the question is never cut while the answer can shrink (18 → 14pt) or a KPI can go: a "…" question reads broken
        qf = min(6, len(wrap(str(question), 12, lw_in))) if question else 0
        k2 = min(2, len(ks))
        for q_lines, a_size, k_n in ((qf, 18, len(ks)), (qf, 16, len(ks)), (qf, 15, len(ks)), (qf, 16, k2), (qf, 15, k2),
                                     (qf, 14, k2), (qf, 14, min(1, len(ks))),
                                     (3, 18, len(ks)), (2, 16, len(ks)), (2, 16, k2), (1, 15, k2),
                                     (1, 14, min(1, len(ks))), (0, 14, 0)):
            parts, bottom = _left(q_lines, a_size, k_n)
            if bottom <= limit:
                break
        else:
            raise ValueError("contents(answer=)：答案太长，左栏放不下——≤40 字一句话给结论（评级 + 目标价，或主建议），论据放各章结论")
        if k_n < len(ks):
            print(f"contents：左栏放不下 {len(ks)} 个关键数字，只保留前 {k_n} 个（答案再短一些就能全放）")
        out.extend(parts)
    elif current is None:
        out.append(_box(48, 64, lw - 90, 24, f"<p>{'CONTENTS' if zh else 'CONTENTS'}</p>", 12, white, font, bold=True))
        out.append(_box(48, 112, lw - 90, 60, f"<p>{'目录' if zh else 'Contents'}</p>", 40, white, font, bold=True))
        if question:
            ql = wrap(str(question), 15, lw - 96)[:5]
            out.append(_box(48, 196, lw - 96, 26 * len(ql) + 8, "".join(f"<p>{escape(t)}</p>" for t in ql), 15, white,
                            font))
    else:
        n = int(current)
        name, d, _ = rows[n - 1]
        out.append(_box(48, 64, lw - 90, 24, f"<p>PART {n:02d}</p>", 12, white, font, bold=True))
        out.append(_box(40, 104, lw - 80, 150, f"<p>{n:02d}</p>", 110, white, font, bold=True))
        nl = wrap(name, 26 if len(name) <= 10 else 22, lw - 96, bold=True)[:2]
        nsz = 26 if len(name) <= 10 else 22
        np_ = "".join(f"<p>{escape(t)}</p>" for t in nl)
        nh = max(34 * len(nl) + 6, _srv_h(np_, nsz, True))
        out.append(_box(48, 262, lw - 96, nh, np_, nsz, white, font, bold=True))
        if d:
            dl = wrap(d, 13, lw - 96)[:4]
            dp_ = "".join(f"<p>{escape(t)}</p>" for t in dl)
            dy = 262 + nh + 10
            dh = max(21 * len(dl) + 6, _srv_h(dp_, 13))
            dl_ = len(dl)
            while dy + dh > H_ - 54 and dl_ > 1:   # keep clear of the footer line
                dl_ -= 1
                dp_ = "".join(f"<p>{escape(t)}</p>" for t in dl[:dl_ - 1] + [dl[dl_ - 1][:-1] + "…"])
                dh = max(21 * dl_ + 6, _srv_h(dp_, 13))
            out.append(_box(48, dy, lw - 96, dh, dp_, 13, white, font))
    if deck_name:
        out.append(_box(48, H_ - 44, lw - 96, 18, f"<p>{escape(str(deck_name))}</p>", 10, white, font))
    x0, x1 = lw + 56, W_ - 48
    if current is None and answer:   # executive summary: supporting conclusions, no chapter list / page ranges
        out.extend(_summary_points(rows, points, x0, x1, H_, C, font, zh, _srv_h))
        rows = []
    top, bot = 64, H_ - (88 if appendix else 56)
    rh = (bot - top) / max(1, len(rows))
    big = 28 if rh >= 56 else 22
    for i, (name, d, rng) in enumerate(rows, 1):
        y = top + (i - 1) * rh
        cur = current is not None and i == int(current)
        on = current is None or cur
        if cur:
            out.append(f'<shape type="rect" topLeftX="{x0 - 20:.0f}" topLeftY="{y + 4:.0f}" width="{x1 - x0 + 20:.0f}" '
                       f'height="{rh - 8:.0f}"><fill><fillColor color="{_c(C["band"])}"/></fill></shape>')
            out.append(f'<shape type="rect" topLeftX="{x0 - 20:.0f}" topLeftY="{y + 4:.0f}" width="4" height="{rh - 8:.0f}">'
                       f'<fill><fillColor color="{_c(C["accent"])}"/></fill></shape>')
        if i > 1:
            out.append(f'<line startX="{x0}" startY="{y:.0f}" endX="{x1}" endY="{y:.0f}"><border color="{_c(C["grid"])}" '
                       'width="1"/></line>')
        numc = C["accent"] if cur else (C["main"] if current is None else "#BBBBBB")
        namec = C["ink"] if on else "#A6A6A6"
        show_d = on and d and rh >= 48
        nw = x1 - x0 - 72 - 76
        out.append(_box(x0, y + (rh - 40) / 2 - 2, 64, 40, f"<p>{i:02d}</p>", big, numc, font, bold=True, valign="middle"))
        ny = y + (rh - 44) / 2 if show_d else y + (rh - 24) / 2
        nsz_ = 17
        while nsz_ > 12 and tw(name, nsz_, True) * 1.1 > nw:   # one line: a wrapped chapter name crosses the row rule
            nsz_ -= 1
        nm_ = name if tw(name, nsz_, True) * 1.1 <= nw else wrap(name, nsz_, nw / 1.1, bold=True)[0].rstrip("，, ") + "…"
        out.append(_box(x0 + 72, ny, nw, 24, f"<p>{escape(nm_)}</p>", nsz_, namec, font, bold=True, valign="middle"))
        if show_d:
            dl = wrap(d, 11.5, nw)
            d_n = 2 if len(dl) > 1 and rh >= 66 else 1   # a row tall enough for two lines shows the whole sentence
            if d_n == 2:   # name + two description lines, centred in the row as one group
                ny = y + (rh - 64) / 2
                dp2 = f"<p>{escape(d if len(dl) <= 2 else _ellipsize(d, dl, 2))}</p>"
                dh2 = max(36, _srv_h(dp2, 11.5, width=nw))
                out[-1] = _box(x0 + 72, ny, nw, 24, f"<p>{escape(nm_)}</p>", nsz_, namec, font, bold=True, valign="middle")
                out.append(_box(x0 + 72, ny + 28, nw, dh2, dp2, 11.5, C["sub"], font))
            else:
                t_ = dl[0] if len(dl) == 1 else _ellipsize(d, dl, 1)
                out.append(_box(x0 + 72, ny + 24, nw, 20, f"<p>{escape(t_)}</p>", 11.5, C["sub"], font, valign="middle"))
        out.append(_box(x1 - 76, y + (rh - 24) / 2, 76, 24, f"<p>{escape(rng)}</p>", 11, C["sub"] if on else "#BBBBBB", font,
                        align="right", valign="middle"))
    if appendix and rows:
        ya = H_ - 72
        out.append(f'<line startX="{x0}" startY="{ya:.0f}" endX="{x1}" endY="{ya:.0f}"><border color="{_c(C["grid"])}" width="1"/>'
                   '</line>')
        out.append(_box(x0, ya + 8, x1 - x0, 22, f'<p><span bold="true" color="{_c(C["main"] if current is None else "#A6A6A6")}">'
                        f'{escape(appendix[0])}</span>{"　" if has_cjk(appendix[0]) else "  "}{escape(appendix[1])}</p>', 11, C["sub"] if current is None else "#BBBBBB",
                        font, valign="middle"))
    # full-bleed: drop the frame's title / rule / footer, keep the logo (light variant on the panel is not needed: right side)
    logo = re.findall(r"<img [^>]*/>", f.xml)
    f.xml = "".join(logo)
    f.top, f.bottom, f.left, f.right = 0, H_, 0, W_   # the whole canvas is this page's body
    f.full_bleed = True
    f.dense_x = 2.0
    return "".join(out)


def dashboard(f, metrics, keys=None, cols=None, palette=None, font="思源黑体", h=None, spark=True):
    """Overview body for business reviews (page 2): one card per metric — name, big actual + unit, a line "同比 +43.0%
    ｜ 目标 480（达成 103%）" coloured by status (met = main, missed = neg), and a sparkline of m["series"] when given.
    metrics: data_common.py METRICS {key: dict(name, unit, actual, target?, ly?, series?, higher_better?)};
    keys picks/orders them (≤ 8; 3–4 per row). Fills f.top … f.top+h (default the whole body). Returns body XML."""
    from ._kpi import fmt_delta, fmt_value, status, vs_target
    C = roles(palette)
    keys = list(keys or metrics)[:8]
    n = len(keys)
    cols = cols or (n if n <= 4 else -(-n // 2))
    rows_ = -(-n // cols)
    gap = 20
    H = h or (f.bottom - f.top)
    cw = (f.right - f.left - gap * (cols - 1)) / cols
    ch = (H - gap * (rows_ - 1)) / rows_
    lang = (getattr(f, "_kw", None) or {}).get("lang") or ("zh" if has_cjk(f.title) else "en")
    zh = lang == "zh"
    out = []
    for i, k in enumerate(keys):
        m = metrics[k]
        r_, c_ = divmod(i, cols)
        x, y = f.left + c_ * (cw + gap), f.top + r_ * (ch + gap)
        st = status(m)
        col = C["neg"] if st == "red" else (C["accent"] if st == "amber" else C["main"])
        out.append(f'<line startX="{x:.0f}" startY="{y:.0f}" endX="{x + cw:.0f}" endY="{y:.0f}">'
                   f'<border color="{_c(C["main"])}" width="2"/></line>')
        out.append(_box(x, y + 8, cw, 20, f"<p>{escape(str(m.get('name', k)))}</p>", 13, C["sub"], font))
        val = m.get("display") or fmt_value(m)
        big = 30 if cols <= 4 else 26
        while big > 20 and tw(val, big, True) * 1.12 + tw(" " + str(m.get("unit", "")), 14, True) > cw - 6:
            big -= 2
        out.append(_box(x, y + 30, cw, big * 1.35,
                        f'<p><span fontFamily="Georgia" fontSize="{big}" bold="true" color="{_c(C["ink"])}">{escape(val)}</span>'
                        f'<span fontSize="14" bold="true" color="{_c(C["ink"])}"> {escape(str(m.get("unit", "")))}</span></p>',
                        big, C["ink"], font))
        parts = []
        d = fmt_delta(m, zh=zh)
        if d:
            parts.append(("同比 " if zh else "YoY ") + d)
        v = vs_target(m)
        if v:
            t = m["target"]
            ts = fmt_value(m, t)
            rate_unit = str(m.get("unit", "")).strip() in ("%", "pt", "pp")
            how = (fmt_delta(m, "target", zh=zh) if (rate_unit or not v["ok"]) else f"{v['rate']:.0f}%")
            word = ("超 " if v["ok"] and rate_unit else "达成 " if v["ok"] else "差 ") if zh else ""
            parts.append(f"目标 {ts}（{word}{how.lstrip('+') if word == '超 ' else how}）" if zh
                         else f"target {ts} ({'met, ' if v['ok'] else ''}{how})")
        ly_ = y + 30 + big * 1.35 + 2
        if parts:
            out.append(_box(x, ly_, cw, 20, f"<p>{escape('｜'.join(parts) if zh else ' | '.join(parts))}</p>", 12, col, font,
                            bold=st == "red"))
        ser = m.get("series") or {}
        sh = y + ch - (ly_ + 26)
        if spark and len(ser) >= 3 and sh >= 26:
            vals = [float(v_) for v_ in ser.values() if v_ is not None]
            lo, hi = min(vals), max(vals)
            sx0, sx1, sy0, sy1 = x + 2, x + cw - 40, ly_ + 34, ly_ + 30 + min(sh - 14, 64)
            pts = [(sx0 + j * (sx1 - sx0) / (len(vals) - 1), sy1 - (v_ - lo) / ((hi - lo) or 1) * (sy1 - sy0))
                   for j, v_ in enumerate(vals)]
            for p_, q_ in zip(pts, pts[1:]):
                out.append(f'<line startX="{p_[0]:.1f}" startY="{p_[1]:.1f}" endX="{q_[0]:.1f}" endY="{q_[1]:.1f}">'
                           f'<border color="{_c(C["second"])}" width="1.5"/></line>')
            ex_, ey_ = pts[-1]
            out.append(f'<shape type="ellipse" topLeftX="{ex_ - 3:.1f}" topLeftY="{ey_ - 3:.1f}" width="6" height="6">'
                       f'<fill><fillColor color="{_c(col)}"/></fill></shape>')
            last = list(ser)[-1]
            out.append(_box(sx1 + 6, ey_ - 9, 40, 18, f"<p>{escape(str(last))}</p>", 10, C["sub"], font))
    return "".join(out)


def _uniform_blocks(specs, font, size=16, lead_size=16):
    """Summary blocks laid out with points(): specs [(w, items, h)]. Every block is fitted first, then all are rendered
    with the SAME body / lead size (the smallest fitted one) and the same item gap, so one long block cannot leave the
    others in a different font size. Returns [(size, lead_size, gap)] per block (identical) — raises like points()
    when a block does not fit even at the floor."""
    fits = [_points_fit(w, its, h, size=size, lead_size=lead_size, font=font) for w, its, h in specs]
    for (w, its, h), (fs, fl, hs) in zip(specs, fits):
        if sum(hs) + 8 * (len(its) - 1) > h + 1:
            points(0, 0, w, its, font=font, h=h, size=fs, lead_size=fl)   # raises the usual "points 放不下" message
    sz = min(f_[0] for f_ in fits)
    lsz = min(f_[1] for f_ in fits)
    gaps = []
    for w, its, h in specs:
        _, hs = _points_measure(0, w, its, sz, lsz, 0, font)
        if len(its) > 1:
            gaps.append(max(8, min((h - sum(hs)) / (len(its) - 1), 48)))
    gap = min(gaps) if gaps else 14
    return sz, lsz, gap


_RS_LABELS = {
    "grai": (("结果", "原因", "下一步"), ("Results", "Why", "Next")),
    "wsn": (("发生了什么", "意味着什么", "接下来做什么"), ("What", "So what", "Now what")),
    "hla": (("亮点", "不足", "需要的支持"), ("Highlights", "Lowlights", "Asks")),
    "goals": (("完成情况", "主要不足", "明年重点"), ("Delivered", "Shortfalls", "Next year")),
}


def review_summary(f, results, causes, actions, kpi_items=None, ask=None, palette=None, font="思源黑体", lang=None,
                   style="grai", labels=None):
    """Business-review summary body (results first — not SCQA): three labelled blocks, each 1–3 items
    [(lead, text, "P4、P6")] with evidence pages; optional KPI cards kpi_items — kpi_cards dicts dict(value, unit, label,
    icon=, note=, bar=, focus=) or the old (value, unit, label) — and a bottom bar ask =
    "提请决议：…". style picks the labels and layout:
      "grai"  结果 / 原因 / 下一步 (rows; board & operating reviews)
      "wsn"   发生了什么 / 意味着什么 / 接下来做什么 (rows; monthly / growth reports, special reviews)
      "hla"   亮点 / 不足 / 需要的支持 (three side-by-side columns; QBR / MBR — lowlights as prominent as highlights)
      "goals" 完成情况 / 主要不足 / 明年重点 (rows; annual work summaries, HR / government reports)
    labels=(a, b, c) overrides the three block names. Returns body XML."""
    C = roles(palette)
    f.summary = True
    zh = (lang or ("zh" if has_cjk("".join(str(t) for it in results for t in it)) else "en")) == "zh"
    names = tuple(labels or _RS_LABELS.get(style, _RS_LABELS["grai"])[0 if zh else 1])
    L = dict(r=names[0], c=names[1], a=names[2], k="提请决议：" if zh else "Decision needed: ")
    if style == "hla":
        return _review_columns(f, C, L, results, causes, actions, kpi_items, ask, palette, font, zh)
    top, bottom = f.top, f.bottom
    out = []
    if ask:
        rh = len(wrap(L["k"] + ask, 16, f.right - f.left - 20)) * 22 + 22
        bottom -= rh + 10
        out.append(f'<shape type="rect" topLeftX="{f.left}" topLeftY="{bottom + 8:.0f}" width="{f.right - f.left}" '
                   f'height="{rh}"><fill><fillColor color="{_c(C["band"])}"/></fill></shape>')
        out.append(_box(f.left + 10, bottom + 8, f.right - f.left - 20, rh,
                        f'<p><span bold="true" color="{_c(C["main"])}">{L["k"]}</span>{escape(ask)}</p>', 16,
                        C["text"], font, valign="middle"))
    lw = 560 if kpi_items else f.right - f.left
    lab = max(64, int(max(tw(L[k], 16, bold=True) for k in ("r", "c", "a"))) + 12)
    blocks = [(L["r"], results, C["accent"]), (L["c"], causes, C["main"]), (L["a"], actions, C["main"])]
    blocks = [b for b in blocks if b[1]]
    weights = [max(1, len(b[1])) for b in blocks]
    gap = 12
    avail = bottom - top - gap * (len(blocks) - 1)
    y = top
    pw = lw - lab - 8
    hs_ = [avail * wgt / sum(weights) for wgt in weights]
    its_ = [[(ld, f"{tx}（{pg}）" if pg and zh else (f"{tx} ({pg})" if pg else tx)) for ld, tx, pg in items]
            for _, items, _ in blocks]
    points._summary = True
    try:   # one font size and one item gap for all three blocks (fitted first, smallest wins)
        sz, lsz, igap = _uniform_blocks([(pw, its, h - 10) for its, h in zip(its_, hs_)], font)
        for (name, items, col), its, h in zip(blocks, its_, hs_):
            out.append(f'<line startX="{f.left}" startY="{y:.0f}" endX="{f.left + lw:.0f}" endY="{y:.0f}">'
                       f'<border color="{_c(C["grid"])}" width="1"/></line>')
            out.append(_box(f.left, y + 6, lab, 24, f"<p>{escape(name)}</p>", 16, col, font, bold=True))
            px, _ = points(f.left + lab + 8, y + 6, pw, its, palette=palette, font=font, h=h - 10, size=sz,
                           lead_size=lsz, gap=igap, spread=False)
            out.append(px)
            y += h + gap
    finally:
        points._summary = False
    if kpi_items:
        kx = f.left + lw + 36
        out.append(_kpi_column(kx, top, f.right - kx, bottom - top, kpi_items, palette, font)[0])
    return "".join(out)


_SWOT_LABELS = (("优势", "劣势", "机会", "威胁"), ("Strengths", "Weaknesses", "Opportunities", "Threats"))
def _swot_item(it):
    """swot_matrix item → (title, detail, bold): (title, detail) | {"t"/"title", "d"/"detail"} | plain string."""
    if isinstance(it, dict):
        return str(it.get("t") or it.get("title") or ""), str(it.get("d") or it.get("detail") or ""), True
    if isinstance(it, (tuple, list)):
        return str(it[0] if it else ""), str(it[1] if len(it) > 1 and it[1] else ""), True
    return str(it), "", False


def _swot_shades(main, n=4, min_contrast=4.6):
    """n solid shades of ONE hue (the palette main), dark → light, each still carrying white text at ≥ min_contrast.
    Darkest = main mixed 25 % toward black; lightest = main lightened toward white as far as the contrast allows
    (≤ 45 %); the rest interpolate. No colour outside the palette's main hue is introduced."""
    from ._palette import _mix, contrast
    dark = _mix(main, "#000000", 0.25)
    t = 0.0
    while t < 0.45 and contrast(_mix(main, "#FFFFFF", t + 0.03)) >= min_contrast:
        t += 0.03
    light = _mix(main, "#FFFFFF", t)
    while contrast(light) < min_contrast:   # a light main: darken until white text reads
        light = _mix(light, "#000000", 0.06)
    if contrast(dark) < min_contrast:
        dark = _mix(light, "#000000", 0.3)
    out = []
    for k in range(n):
        c = _mix(dark, light, k / max(n - 1, 1))
        while contrast(c) < min_contrast:
            c = _mix(c, "#000000", 0.05)
        out.append(c)
    return out


def swot_matrix(f, S, W, O, T, palette=None, font="思源黑体", icons=False):
    """SWOT page body inside frame f: four tall solid cards side by side (S | W | O | T, 12px gutter) filling the
    body, one hue of the palette main from dark to light, white type. Card head = big bold name (优势/劣势/机会/威胁)
    with the English name small on the same line (English decks: English name only) over a thin translucent white
    rule; then the items — a short white bar + bold title, 1–3 lines of detail below; a giant faint S / W / O / T
    watermark sits at the card foot. S/W/O/T: lists of (title, detail) / {"t": title, "d": detail} / plain strings;
    ≤4 items per card, title ≤12 字, detail one sentence. Text starts at 14/12pt and drops to 13/11pt before raising.
    icons is accepted for compatibility and ignored. Returns body XML for f.publish(body, ...)."""
    from ._palette import _mix
    C = roles(palette)
    quads = [list(q or []) for q in (S, W, O, T)]
    allt = "".join(t + d for q in quads for t, d, _ in map(_swot_item, q))
    zh = has_cjk(allt) or not allt.strip()
    names_zh, names_en = _SWOT_LABELS
    cols = _swot_shades(C["main"])
    gut, pad = 12, 14
    x0, y0, x1, y1 = f.left, f.top, f.right, f.bottom
    cw, ch = (x1 - x0 - gut * 3) / 4, y1 - y0
    head = 60                      # name row + rule
    mk = 10                        # marker bar + gap before the item text
    tw_ = cw - pad * 2 - mk
    avail = ch - head - 10 - pad
    import sys as _s
    from pathlib import Path as _P
    _s.path.insert(0, str(_P(__file__).resolve().parents[2]))
    try:
        from _exhibit_text_fit import text_height as _th
    except Exception:  # noqa: BLE001
        _th = None
    finally:
        _s.path.pop(0)

    def paras(t, d, bold, ts, ds, dcol):
        p = (f'<p lineSpacing="multiple:1.2"><span bold="{"true" if bold else "false"}" color="rgb(255,255,255)">'
             f'{escape(t)}</span></p>')
        if d:
            p += (f'<p lineSpacing="multiple:1.25"><span fontSize="{ds}" color="{_c(dcol)}">'
                  f'{escape(d)}</span></p>')
        return p

    def measure(ts, ds):
        out = []
        for q in quads:
            hs = []
            for it in q:
                t, d, b = _swot_item(it)
                est = len(wrap(t, ts, tw_ - 4, bold=b)) * ts * 1.2 + \
                    ((len(wrap(d, ds, tw_ - 4)) * ds * 1.25) if d else 0) + 2
                lint = _th(f'<content fontSize="{ts}" fontFamily="{font}">{paras(t, d, b, ts, ds, "#FFFFFF")}</content>',
                           width=tw_, font_size=ts) if _th else 0
                hs.append(max(est, lint))
            out.append(hs)
        return out
    for ts, ds in ((14, 12), (13.5, 11.5), (13, 11)):
        H_ = measure(ts, ds)
        need = [sum(hs) + 10 * max(len(hs) - 1, 0) for hs in H_]
        if max(need, default=0) <= avail:
            break
    else:
        i = max(range(4), key=lambda k: need[k])
        raise ValueError(f"swot_matrix 放不下：{names_zh[i]}卡 {len(quads[i])} 条需要高 {need[i]:.0f}px，只有 {avail:.0f}px"
                         "（已降到 13pt）——每象限删到 ≤4 条，标题 ≤12 字、细节一句 ≤20 字；长论证移到 note=，不要改用四个 points 拼")
    nrow = max(len(q) for q in quads) if any(quads) else 0
    rows_h = [max(hs[j] for hs in H_ if j < len(hs)) for j in range(nrow)]
    aligned = sum(rows_h) + 10 * max(nrow - 1, 0) <= avail   # items sit on shared rows across the four cards
    if aligned:
        gap = min((avail - sum(rows_h)) / (nrow - 1), 14) if nrow > 1 else 0
    else:
        gaps = [(avail - sum(hs)) / (len(hs) - 1) for hs in H_ if len(hs) > 1]
        gap = max(8.0, min(gaps + [16.0]))   # one item gap on all four cards
    if aligned:
        body_h = sum(rows_h) + gap * max(nrow - 1, 0)
    else:
        body_h = max(sum(hs) + gap * max(len(hs) - 1, 0) for hs in H_)
    # watermark letter: as big as the free foot below the items allows (rendered cap top ≈ y1 − 1.0·size), capped by
    # the card width; never below 96pt (then it tucks faintly behind the last item — ghost text, alpha 0.14)
    foot = y1 - (y0 + head + 4 + body_h) - 10
    wm = int(max(96, min(170, foot, (cw - 8) / 0.95)))
    deco, ghost, texts = [], [], []
    for k, (q, hs) in enumerate(zip(quads, H_)):
        qx = x0 + k * (cw + gut)
        col = cols[k]
        dcol = _mix(col, "#FFFFFF", 0.86)   # detail: near-white, solid (no alpha) so contrast is measurable
        deco.append(f'<shape type="rect" topLeftX="{qx:.0f}" topLeftY="{y0:.0f}" width="{cw:.0f}" height="{ch:.0f}">'
                    f'<fill><fillColor color="{_c(col)}"/></fill></shape>')
        deco.append(f'<shape type="rect" topLeftX="{qx + pad:.0f}" topLeftY="{y0 + head - 8:.0f}" width="{cw - 2 * pad:.0f}" '
                    f'height="1"><fill><fillColor color="rgba(255,255,255,0.45)"/></fill></shape>')
        ghost.append(f'<shape type="text" topLeftX="{qx:.0f}" topLeftY="{y1 - wm * 1.12:.0f}" width="{cw:.0f}" '
                     f'height="{wm * 1.12:.0f}"><content fontSize="{wm}" fontFamily="Arial" color="rgba(255,255,255,0.14)" '
                     f'bold="true" textAlign="center" verticalAlign="bottom"><p>{"SWOT"[k]}</p></content></shape>')
        if zh:
            nw = tw(names_zh[k], 20, bold=True) + 6
            texts.append(_box(qx + pad, y0 + 12, nw, 32, f"<p>{names_zh[k]}</p>", 20, "#FFFFFF", font, bold=True,
                              valign="middle"))
            texts.append(_box(qx + pad + nw + 4, y0 + 19, cw - 2 * pad - nw - 4, 22, f"<p>{names_en[k]}</p>", 11,
                              "#FFFFFF", font, valign="middle"))
        else:
            texts.append(_box(qx + pad, y0 + 12, cw - 2 * pad, 32, f"<p>{names_en[k]}</p>", 18, "#FFFFFF", font,
                              bold=True, valign="middle"))
        iy = y0 + head + 4
        for j, (it, h_) in enumerate(zip(q, hs)):
            t, d, b = _swot_item(it)
            deco.append(f'<shape type="rect" topLeftX="{qx + pad:.0f}" topLeftY="{iy + ts * 0.18 + 1:.0f}" width="3" '
                        f'height="{ts * 0.95:.0f}"><fill><fillColor color="rgb(255,255,255)"/></fill></shape>')
            texts.append(_box(qx + pad + mk, iy, tw_, h_, paras(t, d, b, ts, ds, dcol), ts, "#FFFFFF", font))
            iy += (rows_h[j] if aligned else h_) + gap
    f.dense_x = 1.6   # four labelled lists are a dense page by design; the load check allows it
    return "".join(deco + ghost + texts)


def _review_columns(f, C, L, results, causes, actions, kpi_items, ask, palette, font, zh):
    """review_summary(style="hla"): optional KPI strip on top, then three equal columns (highlights / lowlights /
    asks), each headed by a coloured rule and label; lowlights use the warning colour so bad news is as visible."""
    top, bottom = f.top, f.bottom
    out = []
    if ask:
        rh = len(wrap(L["k"] + ask, 16, f.right - f.left - 20)) * 22 + 22
        bottom -= rh + 10
        out.append(f'<shape type="rect" topLeftX="{f.left}" topLeftY="{bottom + 8:.0f}" width="{f.right - f.left}" '
                   f'height="{rh}"><fill><fillColor color="{_c(C["band"])}"/></fill></shape>')
        out.append(_box(f.left + 10, bottom + 8, f.right - f.left - 20, rh,
                        f'<p><span bold="true" color="{_c(C["main"])}">{L["k"]}</span>{escape(ask)}</p>', 16,
                        C["text"], font, valign="middle"))
    if kpi_items:
        kh = 96
        if any(isinstance(it, dict) for it in kpi_items):   # new-style items: the same cards, side by side
            kx_xml, kb = _kpi_column(f.left, top, f.right - f.left, kh, kpi_items, palette, font, horizontal=True)
            kh = kb - top
        else:
            kx_xml, _ = kpis(f.left, top, f.right - f.left, list(kpi_items)[:4], palette=palette, font=font,
                             cols=min(4, len(kpi_items)), h=kh, big=28)
        out.append(kx_xml)
        top += kh + 18
    gap = 24
    blocks = [(L["r"], results, C["accent"]), (L["c"], causes, C["neg"]), (L["a"], actions, C["main"])]
    blocks = [b for b in blocks if b[1]]
    cw = (f.right - f.left - gap * (len(blocks) - 1)) / len(blocks)
    its_ = [[(ld, f"{tx}（{pg}）" if pg and zh else (f"{tx} ({pg})" if pg else tx)) for ld, tx, pg in items]
            for _, items, _ in blocks]
    ch = bottom - top - 44
    points._summary = True
    try:   # one font size and one item gap for all three columns (fitted first, smallest wins)
        sz, lsz, igap = _uniform_blocks([(cw, its, ch) for its in its_], font)
        for i, ((name, items, col), its) in enumerate(zip(blocks, its_)):
            x = f.left + i * (cw + gap)
            out.append(f'<line startX="{x:.0f}" startY="{top:.0f}" endX="{x + cw:.0f}" endY="{top:.0f}">'
                       f'<border color="{_c(col)}" width="3"/></line>')
            out.append(_box(x, top + 8, cw, 26, f"<p>{escape(name)}</p>", 18, col, font, bold=True))
            px, _ = points(x, top + 44, cw, its, palette=palette, font=font, h=ch, size=sz, lead_size=lsz, gap=igap,
                           spread=False)
            out.append(px)
    finally:
        points._summary = False
    return "".join(out)
