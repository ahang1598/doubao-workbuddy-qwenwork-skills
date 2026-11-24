"""File-based hand-off between MainAgent and Organizer (the Organizer cannot send_message).

  status        Organizer: python3 multiagent_sync.py status --dir D --phase plan_ready [--done 4,7] [--note ...]
  wait          MainAgent: python3 multiagent_sync.py wait --dir D --phase plan_ready [--max 180]
  next          builders: python3 multiagent_sync.py next --dir D --who builder1 [--agent-id <create_agent id>]
                Main:     next --dir D --who main --prefer 1-3                       (cover / contents / summary)
                review:   next --dir D --who main|organizer --review → check one builder page →
                verdict   python3 multiagent_sync.py verdict --dir D --page N --who main --ok | --fixed
                          | --redo --note "<defect>" (before export: reopen a done page to yourself, not the --fix)
                organizer_done / auto-freeze waits until no page is built / reviewing / redo-pending.
  finish        MainAgent: python3 multiagent_sync.py finish --dir D --deck <id> --cwd CWD [--name 标题] — read back,
                check every plan page is in the deck, export PPTX (the whole closing step). Refused for --who organizer
                while Main's dispatch is open. After export, the one legal rework (Main / Lead, once per task):
                finish ... --fix 5[,7] --why "<defect>" → unfreezes those pages; republish them; plain finish re-exports.
  reopen        Main / Lead, follow-up turn after delivery: reopen --cwd CWD [--deck D] --why "<用户追问摘要>" [--readback ./edit-vNN/source-response.json]
                (refused until this turn's +xml-get readback of the deck exists) → archives exported /
                frozen.lock to SYNC/turns/<n>/, phase "edit" (no ownership rules, fresh block budgets), reseals; edit the
                pages (chart pages: f.publish(..., page=N)), then export re-exports and closes the turn again.
  ready         any agent: python3 multiagent_sync.py ready --deck <xml_presentation_id> --page 7 [--cwd CWD]
                ok=true when every earlier page p01..p06 is already in the publish_slide page registry.
  dispatch      MainAgent, right before create_agent: dispatch --cwd CWD --flow strategy|template (records a live,
                skill-guided Main in <CWD>/.lark-slides/dispatch.json); after delivery: dispatch --cwd CWD --close.
                Optional --flow template --template-assist: assigned difficult pages only, no strategy SYNC/DAG;
                separate template-assist-dispatch.json, selected by role --marker template. Final export waits for
                current return-summary; close with --flow template --template-assist --close (global dispatch untouched).
  role          any dispatched agent, first thing: role --cwd CWD [--marker strategy|template] → organizer (case 1,
                Main is alive and follows the skill) or lead (case 2: do Main's and Organizer's work, who=lead).
                dispatch creates and returns the task's own SYNC dir (<CWD>/.lark-slides/<strategy|review>/<task-id>/sync); role
                returns it (organizer) or sync_by_flow (lead).
  lead-return   Lead, after the one final present_files: lead-return --title T --pages N --url URL --pptx PATH
                [--notes …] [--gaps …] → plain-text return message (forwarded verbatim by the dispatching agent).
                Text with $ (e.g. $250K): write it to a file and pass --notes-file F / --gaps-file F (finish takes
                the same flags) — inside double quotes the shell expands $250K to 50K.

Phases advance outline_ready → plan_ready → pages_in_progress → organizer_done; ``failed`` ends the run.
No placeholder pages: the deck only ever shows finished pages. ``publish_slide(..., page=N)`` run from the same CWD
inserts page N before the nearest later page already written (page→slide_id in <CWD>/.lark-slides/pages-<deck>.json),
so pages land in order whichever agent finishes first; the page list comes from plan.py PAGES.
"""

from __future__ import annotations

import argparse
import json
import re
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PHASES = ("outline_ready", "research_ready", "plan_ready", "pages_in_progress", "organizer_done")
_SML = "https://www.larkoffice.com/sml/2.0"
FLOWS = ("strategy", "template")
DISPATCH_FRESH = 900   # s: a dispatch older than this (or already taken / closed) is a leftover of an earlier turn
_SKILL_ROOT = Path(__file__).resolve().parent.parent
FINAL_REPLY_FILE = "FINAL_REPLY.md"   # <cwd>/.lark-slides/decks/<deck>/FINAL_REPLY.md: the Lead's last message, verbatim
FINAL_REPLY_RULE = "最后一条消息 = FINAL_REPLY.md 全文（cat 出来原样发），不自己写摘要、不改写、前后不加字"
_ROLE_DOCS = {"strategy": "SKILL.md",
              "template": "SKILL.md"}


def _read_text(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError:
        return ""


def _read(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _write(path, data, binding_update=False):
    path = Path(path)
    if path.name == "status.json" and isinstance(data, dict):
        current = _read(path)
        deck = (_pub().sync_deck(path.parent) or (current.get("deck_binding") or {}).get("deck")) if current.get("task_id") else None
        if deck:
            with _pub()._deck_lock(_task_cwd(path.parent), deck):
                current = _read(path)
                merged = dict(data)
                for key in ("task_id", "task_flow", "deck_binding"):
                    if key in current and (key != "deck_binding" or not binding_update):
                        merged[key] = current[key]
                return _atomic_write(path, merged)
        if current.get("task_id"):
            data = {**data, **{key: current[key] for key in ("task_id", "task_flow", "deck_binding")
                              if key in current and (key != "deck_binding" or not binding_update)}}
    return _atomic_write(path, data)


def _atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def _pages(spec):
    out = []
    for part in str(spec).split(","):
        part = part.strip()
        if not part:
            continue
        lo, _, hi = part.partition("-")
        out += list(range(int(lo), int(hi or lo) + 1))
    return sorted(set(out))


def _dispatch_path(cwd):
    return Path(cwd).resolve() / ".lark-slides" / "dispatch.json"


def _template_assist_dispatch_path(cwd):
    return Path(cwd).resolve() / ".lark-slides" / "template-assist-dispatch.json"


_FRONT_SUMMARY = r"\s*((执行)?摘要|executive summary|summary)\s*"
_FRONT_CONTENTS = r"\s*(目录|contents)\s*"


def _plan_sections(directory):
    """plan.py SECTIONS {page: name}, read from the source (no plan run); {} when absent."""
    try:
        src = (Path(directory) / "plan.py").read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return {}
    m = re.search(r"^SECTIONS\s*=\s*(?:Sections\()?\{([^}]*)\}", src, re.M)
    return {int(k): v for k, v in re.findall(r"\b(\d+)\s*:\s*f?['\"]([^'\"]*)['\"]", m.group(1))} if m else {}


def _first_chapter(sec):
    """First chapter page of SECTIONS: front pages (cover / summary / contents) and the appendix are not chapters."""
    return min([k for k, v in sec.items() if k >= 2 and not re.fullmatch(_FRONT_SUMMARY, v, re.I)
                and not re.fullmatch(_FRONT_CONTENTS, v, re.I) and not re.search(r"封面|cover|附录|appendix", v, re.I)]
               or [0])


def _main_pages(directory):
    """Pages only Main / Lead write: cover, executive summary, contents (P1 → P2 → P3; chapter 1 starts at P4)."""
    st = _read(Path(directory) / "status.json").get("main_pages")
    if st:
        return set(_pages(st))
    if _first_chapter(_plan_sections(directory)) == 3:   # older plan: P2 = summary + contents in one, body from P3
        return {1, 2}
    return set(_pages("1-3"))


def _nav_pages(directory):
    """Chapter navigation pages of plan.py (rows with recipe chapter_nav), read from the source (no plan run)."""
    try:
        src = (Path(directory) / "plan.py").read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return set()
    out = set()
    for row in re.findall(r"dict\(([^()]*(?:\([^()]*\)[^()]*)*)\)", src):
        if re.search(r"recipe\s*=\s*['\"]chapter_nav", row):
            m = re.search(r"\bp\s*=\s*(\d+)", row)
            if m:
                out.add(int(m.group(1)))
    return out


def _summary_page(directory):
    """The executive summary page (needs every number): P2, before the contents page (P3 only in a plan that still
    lists 目录 at P2 and 执行摘要 at P3)."""
    mp = sorted(_main_pages(directory))
    if len(mp) < 2:
        return None
    sec = _plan_sections(directory)
    if len(mp) >= 3 and re.fullmatch(_FRONT_CONTENTS, sec.get(2, ""), re.I) and re.fullmatch(_FRONT_SUMMARY, sec.get(3, ""), re.I):
        return 3
    return mp[1]


def _contents_page(directory):
    """The contents page: the Main page after the cover that is not the summary (the summary itself in an older merged
    plan); None when Main owns the cover only."""
    summ = _summary_page(directory)
    rest = [p for p in sorted(_main_pages(directory)) if p not in (1, summ)]
    return rest[0] if rest else summ


_SYNC_KIND = {"strategy": "strategy"}


def sync_dir(cwd, flow, task="main"):
    """The SYNC dir of a multi-agent deck: <cwd>/.lark-slides/<strategy|review>/<task>/sync (None for template)."""
    kind = _SYNC_KIND.get(flow)
    return Path(cwd).resolve() / ".lark-slides" / kind / task / "sync" if kind else None


def new_task_id(prefix="t"):
    """A task id unique within the CWD: every dispatch / Lead task gets its own SYNC dir, so a second deck made in the
    same conversation never reads the first one's plan, claims, freeze or deck.txt."""
    import secrets
    return f"{prefix}{time.strftime('%m%d%H%M%S')}{secrets.token_hex(2)}"


def _retire_open_tasks(cwd, keep=None):
    """A new task starts in this CWD: SYNC dirs of earlier tasks that never finished are marked abandoned (publish /
    next stop treating them as the running task). Delivered ones are left as they are (reopen still finds them by deck)."""
    from_pub = _pub()
    out = []
    for d in from_pub._sync_candidates(cwd):
        if keep and Path(d).resolve() == Path(keep).resolve():
            continue
        if from_pub.sync_finished(d):
            continue
        st = _read(Path(d) / "status.json")
        st["abandoned"] = time.time()
        _write(Path(d) / "status.json", st)
        out.append(str(d))
    return out


def _pub():
    sys.path.insert(0, str(_SKILL_ROOT))
    try:
        from scripts.svg_lib.atomize_svg_to_slide import _publish
    finally:
        sys.path.pop(0)
    return _publish


CWD_MSG = ("CWD 用你第一次 pwd 得到的对话目录下的子目录（如 $(pwd)/<deck名>），不要自拟路径、不要改对话编号：{why}。"
           "重新 pwd，用那个目录（或其子目录）重跑同一条 dispatch")


def _foreign_cwd(cwd_):
    """dispatch: the task CWD must belong to this conversation. The shell an agent starts in is its conversation folder;
    a CWD outside it (and not one of its parents) is refused when it sits in a sibling folder of the same kind
    (new-chat-25 → new-chat-26: another live conversation) or below a folder that already holds another task's
    .lark-slides artifacts. None when fine."""
    try:
        here = Path(os.getcwd()).resolve()
    except OSError:
        return None
    if cwd_ == here or here in cwd_.parents or cwd_ in here.parents:
        return None
    a, b = here.parts, cwd_.parts
    i = 0
    while i < min(len(a), len(b)) and a[i] == b[i]:
        i += 1
    if i < len(a) and i < len(b) and re.search(r"\d", a[i]) and re.sub(r"\d+", "#", a[i]) == re.sub(r"\d+", "#", b[i]):
        return CWD_MSG.format(why=f"当前对话目录是 {Path(*a[:i + 1])}，你给的 CWD 在另一个对话目录 {Path(*b[:i + 1])} 下")
    if len(a) - i > 2:   # the shell is not in a conversation folder next to the CWD (e.g. run from the skill dir): no verdict
        return None
    for up in list(cwd_.parents)[:max(len(b) - i - 1, 0)]:   # ancestors below the common root
        ls = up / ".lark-slides"
        if ls.is_dir() and ((ls / "decks").is_dir() or any(ls.glob("pages-*.json")) or (ls / "dispatch.json").exists()):
            return CWD_MSG.format(why=f"{up} 里已经有别的任务的 .lark-slides 产物（不属于本任务）")
    return None


def dispatch(cwd, flow, close=False, deck=None, binding=None, template_assist=False):
    """Main, right before create_agent: record that a MainAgent following this skill is alive and is handing `flow`
    to exactly one Organizer, and create the task's SYNC dir (same path on every re-run). With close=True (delivery
    done) the record is retired so a later turn's agent is a Lead; it looks for .lark-slides/dispatch.json in --cwd
    and up to 4 parent dirs (run from a WORK_DIR below the task CWD it still closes the right record).
    template_assist=True selects a separate template-assist-dispatch.json for both open and close."""
    if template_assist and flow != "template":
        raise SystemExit("--template-assist is only valid with dispatch --flow template")
    path = _template_assist_dispatch_path(cwd) if template_assist else _dispatch_path(cwd)
    if close:
        for up in [Path(cwd).resolve(), *list(Path(cwd).resolve().parents)[:4]]:
            candidate = _template_assist_dispatch_path(up) if template_assist else _dispatch_path(up)
            if candidate.exists():
                path = candidate
                break
        d = _read(path)
        if not d:   # an error, not a harmless no-op: a Lead that runs it should see a failed call (exit code 1)
            return {"ok": False, "closed": False, "note": "没有 dispatch 记录：Lead 不需要也不应运行 dispatch（含 --close）"}
        if d.get("template_assist") and not d.get("closed"):
            gate = _template_export_gate(path.parent.parent)
            if not gate or gate["mode"] != "returned":
                return {"ok": False, "closed": False, "code": "template_assist_pending",
                        "next": "指定页尚未交回：先停止全部 writer，用实际 wait_agent/return 确认，再核对本轮最新 return-summary；不能提前关闭派单绕过导出门禁。"}
        d["closed"] = time.time()
        _write(path, d)
        return {"ok": True, "closed": True, "path": str(path)}
    if flow not in FLOWS:
        raise SystemExit(f"unknown flow {flow!r}; use one of {', '.join(FLOWS)}")
    cwd_ = Path(cwd).resolve()
    foreign = _foreign_cwd(cwd_)
    if foreign:   # refuse before anything is created: a made-up CWD lands the deck in another conversation's folder
        return {"ok": False, "flow": flow, "cwd_rejected": str(cwd_), "next": foreign}
    prev = _read(path)
    if binding not in (None, "edit", "resume") or bool(deck) != bool(binding):
        return {"ok": False, "note": "显式绑定需要 --deck 与 --binding edit|resume；普通新建不需要这些参数"}
    previous_status = _read(Path(prev["sync"]) / "status.json") if prev.get("sync") else {}
    previous_binding = previous_status.get("deck_binding") or {}
    if binding == "resume" and not (prev.get("flow") == flow and not prev.get("closed")
            and previous_status.get("task_id") and previous_binding.get("task_id") == previous_status["task_id"]
            and previous_binding.get("deck") == _pub()._deck_id(deck)
            and not _pub().sync_finished(prev["sync"])):
        return {"ok": False, "note": "resume 只能继续同一 task_id 已核实的 deck；不能给陌生稿授权"}
    if binding == "resume" or (prev.get("sync") and not prev.get("closed") and prev.get("flow") == flow
            and time.time() - prev.get("t", 0) < DISPATCH_FRESH and Path(prev["sync"]).is_dir()
            and not _pub().sync_finished(prev["sync"])):
        sync = Path(prev["sync"])   # a re-run of the same dispatch (context compaction): same SYNC, same answer
    else:
        sync = sync_dir(cwd_, flow, new_task_id()) if _SYNC_KIND.get(flow) else None
        if sync:
            _write(sync / "status.json", {"task_id": sync.parent.name, "task_flow": flow})
    if binding == "edit" and sync:
        target = _pub()._deck_id(deck)
        owner = _pub().sync_deck(sync)
        if owner and owner != target:
            return {"ok": False, "note": "本任务已有另一份 deck 绑定；不能用 edit 参数替换它"}
        status = _read(sync / "status.json")
        status.update(task_id=status.get("task_id") or sync.parent.name, task_flow=flow)
        status["deck_binding"] = {"task_id": status["task_id"], "deck": target, "mode": "edit",
                                 "authority": "dispatch:edit", "baseline_slide_ids": None}
        _write(sync / "status.json", status, binding_update=True)
        (sync / "deck.txt").write_text(target, encoding="utf-8")
    # Template assistance owns only its explicitly assigned pages; it must not
    # abandon a different strategy deck merely because it has no strategy SYNC.
    retired = [] if template_assist else _retire_open_tasks(cwd_, keep=sync)
    rec = {"flow": flow, "t": time.time(), "main_alive": True}
    if template_assist:
        rec["template_assist"] = True
    if sync:
        (sync / "research").mkdir(parents=True, exist_ok=True)
        (sync / "flow.txt").write_text(flow, encoding="utf-8")
        rec["sync"] = str(sync)
    _write(path, rec)
    marker = f"[ppt-dispatch:{flow}]"
    line = f"{marker} CWD={cwd_}" + (f" SYNC={sync}" if sync else "")
    out = {"ok": True, "flow": flow, "marker": marker, "marker_line": line, "cwd": str(cwd_),
           "next": (f"派单消息第一行原样写：{line}（Organizer 据此和 dispatch.json 判定自己是协作 Organizer）；"
                    + ("SYNC 已建好，所有 agent 都用这个路径（不自己拼 task-id、不另建目录）；" if sync else "")
                    + "其余按本流程的 Organizer 派单模板写，然后立即 create_agent")}
    if sync:
        out["sync"] = str(sync)
    if template_assist:
        out.update(template_assist=True, scope="assigned_pages")
    if retired:
        out["retired"] = retired
    return out


def lead_syncs(cwd):
    """Read existing legacy paths; never initialise Lead state or retire another task."""
    record = _read(Path(cwd).resolve() / '.lark-slides/lead.json')
    existing = record.get('sync')
    return existing if isinstance(existing, dict) else {}


def role(cwd, marker=None):
    """Read legacy role/scope records and point to an existing current entry.

    The historical labels remain compatible; an unbound request starts no Lead workflow.
    """
    path = _dispatch_path(cwd)
    if marker == "template":
        assist_path = _template_assist_dispatch_path(cwd)
        assist, ordinary = _read(assist_path), _read(path)
        if assist and (ordinary.get("flow") != "template" or assist.get("t", 0) >= ordinary.get("t", 0)):
            path = assist_path
    d, now = _read(path), time.time()
    if d.get("template_assist") and d.get("closed"):
        return {"ok": False, "role": "organizer", "template_assist": True, "scope": "assigned_pages",
                "code": "template_assist_closed", "doc": str(_SKILL_ROOT / _ROLE_DOCS["template"]),
                "next": "本轮模板辅助派单已关闭：停止写入并交回 Main，不接管全稿，不创建 Lead SYNC 或改变其它 strategy 任务。"}
    flow = d.get("flow")
    why = None
    if not d:
        why = "没有 dispatch.json（派你的 agent 没按本 skill 派单）"
    elif d.get("closed"):
        why = "dispatch.json 已关闭（上一轮已交付）"
    elif now - d.get("t", 0) > DISPATCH_FRESH and not d.get("template_assist"):
        why = f"dispatch.json 写于 {int((now - d.get('t', 0)) // 60)} 分钟前（上一轮的遗留）"
    if why and marker in FLOWS and not d:   # the marker came through but the file did not (different CWD)
        why, flow = None, marker
    if why is None and flow in FLOWS:
        if d and not d.get("taken"):   # diagnostics only: a re-run after context compaction must give the same answer
            d["taken"] = now
            _write(path, d)
        sync = d.get("sync") or (str(sync_dir(cwd, flow)) if sync_dir(cwd, flow) else None)
        out = {"ok": True, "role": "organizer", "flow": flow, "doc": str(_SKILL_ROOT / _ROLE_DOCS[flow]),
               "next": f"你是协作 Organizer（MainAgent 在线、已按 skill 派单）：按 {_ROLE_DOCS[flow]} 干活；建 deck、开工通知、"
                       "最终交付仍由 MainAgent 做。" + (f"SYNC 一律用 {sync}（不自己拼、不另建、不删）。" if sync else "")
                       + "role 只跑这一次，结果记住"}
        if sync:
            out["sync"] = sync
        if d.get("template_assist"):
            out.update(template_assist=True, scope="assigned_pages")
            out["next"] = ("你是模板专项 Organizer：只处理 Main 明确交接的困难页。稳定 deck 与实际 slide_id、"
                           "完整 source/roles/facts 和当前基线均来自派单；未创建页只回 draft。"
                           "Main 继续正常页，你不得接管全稿、add/delete 或最终交付。按 "
                           + _ROLE_DOCS["template"] + " 的当前入口确认流程，保持原交接范围。")
        return out
    current_doc = _ROLE_DOCS['template'] if flow == 'template' or marker == 'template' else 'SKILL.md'
    return {"ok": True, "role": "lead", "legacy_role": True, "why": why or "dispatch.json 内容不完整",
            "doc": str(_SKILL_ROOT / current_doc),
            "sync_by_flow": lead_syncs(cwd),
            "sync_note": "只返回已有历史路径；不新建任务目录或改变其他任务状态。",
            "must": "按当前入口确认用户任务、目标和发布权；历史角色字段不授权新的代理分工或接管整稿。",
            "on_followup": "之后收到 send_message 追问或返工：第一个调用重新 Read SKILL.md，再 Read workflow/slides-editing.md，回读目标页后再改",
            "subagents": {"strategy 新建 ≥6 页": "按当前 SKILL.md 的任务规则执行，不依据旧角色标签自动派代理。",
                          "模板题": "按 references/template/workflow.md 亲手完成整稿及困难页优化；不创建代理、不转交全稿",
                          "其余所有任务（含 strategy <6 页、business-deck、编辑）": "不派任何子代理，亲手按 SKILL.md 做完"},
            "next": f"lead 仅为历史兼容标签；从 {current_doc} 确认当前流程，沿用本任务已明确的目标与范围，不启动旧 Lead 流程。"}


def set_status(directory, phase, done=None, note=None):
    if phase == "plan_final":   # agents reach for it as a phase: it is the SYNC/plan_final marker
        (Path(directory) / "plan_final").touch()
        return dict(_read(Path(directory) / "status.json"), plan_final=True)
    if phase not in PHASES + ("failed",):
        raise SystemExit(f"unknown phase {phase!r}; use one of {', '.join(PHASES + ('failed',))}")
    path = Path(directory) / "status.json"
    status = _read(path)
    if status.get("phase") == "edit":   # a reopened follow-up turn: no phases, no freeze — export closes it
        return dict(status, ignored=True, next=_EDIT_NEXT)
    if (status.get("phase") == "organizer_done" or status.get("finished_at")) and phase != "organizer_done":
        return dict(status, ignored=True, next="全部页已完成并冻结（organizer_done），状态不再回退：直接 finish 交付")
    if phase in ("plan_ready", "plan_final") and (Path(directory) / "plan.py").exists():
        try:   # a plan.py that does not even parse stops every page script (they all import it)
            compile((Path(directory) / "plan.py").read_text(encoding="utf-8"), "plan.py", "exec")
        except SyntaxError as e:
            return dict(status, ok=False, next=(f"{phase} 未发出：plan.py 第 {e.lineno} 行语法错误（{e.msg}）——"
                                                "字符串里的引号换成「」或转义，改完重跑同一条命令；只有 Organizer 改 plan.py"))
    if phase == "plan_ready" and status.get("phase") not in PHASES[2:] and status.get("plan_block_rejects", 0) < 2:
        g_ = _load_plan(directory, "plan_blocks") or {}
        bad = block_issues(g_.get("PAGES") or [])
        if bad:   # a 4+ block row costs a page of trial-and-error later: fix it while nobody has started
            status["plan_block_rejects"] = status.get("plan_block_rejects", 0) + 1
            _write(path, status)
            return dict(status, ignored=True, rejected=bad,
                        next=(f"plan_ready 未发出：{'、'.join(bad)} 超过 {MAX_BLOCKS_PER_ROW} 块（每页一种构图、≤3 块）。"
                              "Edit 这些 PAGES 行：只留主证据 + 1–2 块相连的（右栏 2–4 条 / 下方拆解 / 同口径第二张图），"
                              "KPI 行只在 kpi_charts_page 上用、删复述标题的结论条；放不下的内容拆成 a/b 两页（新行 split_of=N）。"
                              "改完重跑同一条 status --phase plan_ready"))
    if phase == "plan_ready" and status.get("phase") not in PHASES[2:] and not status.get("plan_rail_rejected"):
        g_ = _load_plan(directory, "plan_rails") or {}
        rail = rail_share_issue(g_.get("PAGES") or [])
        if rail:   # counted from PAGES once: the write-time rail ledger misses pages written by other agents
            status["plan_rail_rejected"] = True
            _write(path, status)
            return dict(status, ignored=True, rejected=[rail],
                        next=f"plan_ready 未发出（只拦这一次）：{rail}。Edit 这些 PAGES 行后重跑同一条 status --phase plan_ready")
    if phase == "plan_ready" and status.get("phase") not in PHASES[2:] and not status.get("plan_rel_rejected"):
        g_ = _load_plan(directory, "plan_rels") or {}
        rel = relation_issues(g_.get("PAGES") or [])
        if rel:   # a multi-chart row with no stated relation becomes "two charts side by side": fix it before anyone builds
            status["plan_rel_rejected"] = True
            _write(path, status)
            return dict(status, ignored=True, rejected=[rel],
                        next=f"plan_ready 未发出（只拦这一次）：{rel}。Edit 这些 PAGES 行后重跑同一条 status --phase plan_ready")
    status["phase"] = phase
    status["updated_at"] = time.strftime("%H:%M:%S")
    if phase == "plan_ready" and "plan_ready_at" not in status:
        status["plan_ready_at"] = time.time()
    if phase == "organizer_done":   # every page is built and checked: freeze them (publish refuses rewrites)
        claims = _read(Path(directory) / "claims.json")
        plan = _plan_pages(directory)
        want = set(plan) | set(range(1, min(plan))) if plan else set()
        open_ = sorted(n for n in want if (lambda c: c["state"] in ("todo", "doing") and not c.get("redo"))(
            _claim_state(claims.get(f"p{n:02d}", {"who": "", "state": "todo"}))))
        reg = _registered(directory)
        stuck = _unwritten_any(claims, reg, want)   # done + written=0 + unregistered: refuse every time
        once = set(_done_unwritten(claims, reg))   # next reopens these itself (first time, within 20 min)
        open_ = sorted(set(open_) | once | set(stuck))   # done but written=0
        if open_:   # freezing now would lock unwritten pages out of the deck (Main could never write its P3)
            owners = {n: (_claim_state(claims[f"p{n:02d}"]).get("who") or "main") if n in once
                      else _reopen_unwritten(directory, n) for n in stuck}
            who_txt = "；".join(f"P{n} 归 {o}" for n, o in owners.items())
            return dict(status, ignored=True, unwritten=open_, **({"owners": owners} if owners else {}),
                        next=f"第 {open_} 页还没写进 deck，不能标 organizer_done"
                             + (f"（{who_txt}：已退回给它，用 publish 写入一次；它已 return 就 release --who 它 后你自己领；连续被服务端拦就按返回的降级写法写）" if owners else "")
                             + "：继续运行 next --review（它会在全部写完后自动标记）")
        pending = _verdict_pending(claims)
        if pending:   # a page still waiting for (or under) review: freezing now forces a --fix round later
            return dict(status, ignored=True, unreviewed=pending,
                        next=f"第 {pending} 页还在待检查/检查中，不能标 organizer_done：先 next --review 领这些页并给 verdict"
                             "（发现问题用 verdict --redo --page N --note …），全部有 verdict 后 next 会自动标记")
        status["frozen"] = sorted(set(int(k[1:]) for k in claims if re.fullmatch(r"p\d+", k)) | set(_plan_pages(directory)))
        _write_frozen_lock(directory, status["frozen"])
        _stamp_deck(directory)
    if done is not None:
        status["done"] = sorted(set(status.get("done", [])) | set(_pages(done)))
    if note:
        status.setdefault("notes", []).append(f"{status['updated_at']} {note}")
    _write(path, status)
    if phase == "plan_ready":
        status["next"] = ("不另派 Builder（调研 SubAgent 调研完接着做页）：运行 next --review，按方向返回的 tune 逐个定稿；"
                          "有 plan_mix 先 Edit 对应 PAGES 行")
        issues = plan_check(directory)
        if not status.get("skeleton_hinted"):
            g_ = _load_plan(directory, "plan_skeleton") or {}
            sk = skeleton_issue(g_.get("PAGES") or [], _query_text(directory))
            qc = query_coverage_issue(g_.get("PAGES") or [], _query_text(directory))
            if sk or qc:
                issues = [x for x in (qc, sk) if x] + list(issues or [])
                status["skeleton_hinted"] = True
                _write(path, {k: v for k, v in status.items() if k != "next"})
        if issues:
            status = dict(status, plan_mix=issues,
                          next=status["next"] + "；整稿组合未达标：派完 Builder 后用 Edit 改 PAGES 的 recipe/body（Builder 领页时读最新 plan）")
    return status




def _query_text(directory):
    """The user's request as saved by Main (status.json "query" / query.txt in SYNC or its parents), else ""."""
    d = Path(directory)
    for p in (d / "query.txt", d.parent / "query.txt"):
        if p.exists():
            return p.read_text(encoding="utf-8", errors="ignore")
    try:
        return str(json.loads((d / "status.json").read_text(encoding="utf-8")).get("query", ""))
    except (OSError, ValueError):
        return ""


def _requested_language(query):
    if not query.strip() or re.search(r"\bbilingual\b|English\s+(?:and|/)\s+Chinese|Chinese\s+(?:and|/)\s+English|中英文双语",
                                      query, re.I):
        return None
    modifiers = r"(?:(?:strategy|business|management|investment|investor|financial|annual|review)\s+){0,3}"
    explicit_english = bool(re.search(
        rf"\bEnglish(?:-language)?\s+{modifiers}(?:presentation|deck|PPT)\b|"
        r"\b(?:presentation|deck|PPT)\b.{0,30}\bin English\b|(?:用|以)英文|英文(?:版)?\s*(?:PPT|演示|幻灯片)", query, re.I))
    explicit_chinese = bool(re.search(
        rf"\bChinese(?:-language)?\s+{modifiers}(?:presentation|deck|PPT)\b|"
        r"\b(?:presentation|deck|PPT)\b.{0,30}\bin Chinese\b|(?:用|以)中文|中文(?:版)?\s*(?:PPT|演示|幻灯片)", query, re.I))
    if explicit_english or explicit_chinese:
        return None if explicit_english and explicit_chinese else ("en" if explicit_english else "zh")
    paragraphs = re.split(r"\n\s*\n", query, maxsplit=1)
    if len(paragraphs) == 2 and re.search(r"SKILL\.md", paragraphs[0], re.I) and re.search(r"\.zip\b", paragraphs[0], re.I):
        query = paragraphs[1]
    cjk_count = len(re.findall(r"[\u4e00-\u9fff]", query))
    return "en" if cjk_count < 5 else ("zh" if cjk_count > 20 else None)


SIDE_STYLES = ("takeaways", "plain", "swatch", "number", "card", "bar", "badge")
SIDE_DEFAULTS = ("takeaways", "plain")   # default rails: not rotated (the 40 % left-chart cap still bounds them)
SIDE_MSG = ("右侧要点样式：默认 takeaways（key_takeaways 右栏）；points 样式 swatch/number/card/bar/badge "
            "只在要点对应图上元素时用，相邻页不重复、同一样式 ≤1/3")


def _side_variety(pages):
    """PAGES rows may carry side="takeaways|swatch|number|card|bar|badge|plain" (takeaways = key_takeaways rail, the
    rest = points(style=)). With ≥4 rows declaring it: two adjacent data pages with the same points style, or one
    points style on more than 1/3 of the side-column pages → one issue."""
    rows = [r for r in pages if isinstance(r, dict) and r.get("chart") is not False]
    sty = [str(r.get("side") or "").strip().lower() or None for r in rows]
    declared = [x for x in sty if x]
    if len(declared) < 4:
        return []
    adjacent = any(a and a == b and a not in SIDE_DEFAULTS for a, b in zip(sty, sty[1:]))
    import collections as _c
    heavy = any(k not in SIDE_DEFAULTS and v > len(declared) / 3 for k, v in _c.Counter(declared).items())
    return [SIDE_MSG] if adjacent or heavy else []


CAP_TABLE_WITH_CHART = 8   # plan capacity (conservative): a table of > 8 rows leaves no room for a chart on the same page
CAP_TABLE_ALONE = 20       # > 20 table rows do not fit one page at 12pt even alone
CAP_CHARTS_WITH_TABLE = 2  # > 2 charts plus a table = 4+ blocks
CAPACITY_MSG = "容量超了"
_TABLE_RECIPES = ("row_table", "text_table", "table_block", "heat_matrix", "variance_table", "rank_table", "dumbbell_table",
                  "distribution_table", "scorecard", "kpi_spark_table", "kpi_scorecard", "table_panel", "appendix")
_TABLE_WORD = r"表|table|清单|名单|登记|register"
_CHART_WORD = (r"折线|柱|条形|横向条|堆叠|面积|散点|气泡|饼|环形|瀑布|桥|矩阵图|热力|漏斗|雷达|"
               r"columns|lines|bars|bubble|scatter|waterfall|bridge|donut|pie|area|risk_matrix|marimekko|treemap|slope|"
               r"dumbbell|fan|pareto|ridgeline|funnel|chart")
_ROW_COUNT = re.compile(r"(?:全|共|约)?\s*(\d{1,3})\s*(?:行|条|家|项|个(?:公司|企业|对象|国家|品牌|产品|事件)|只股票|款)")


def _row_load(row):
    """(table rows, tables, charts) a PAGES row asks for, read from recipe / layout_recipe / body. Body segments split
    on ①②③… (or 上/中/下/左/右 + 半部/排/块); each segment is a table, a chart, or neither. Conservative: counts only
    what the body names explicitly; a number counts as table rows only inside a table segment."""
    rec = str(row.get("recipe", "")).split("/")[0].strip()
    body = str(row.get("body", ""))
    segs = [x for x in re.split(r"[①②③④⑤⑥⑦⑧⑨]", body) if x.strip()]
    if len(segs) <= 1:
        segs = [body]
    rows_, tables, charts = 0, 0, 0
    for seg in segs:
        head = seg[:80]
        is_table = bool(re.search(_TABLE_WORD, head, re.I)) or (len(segs) == 1 and rec in _TABLE_RECIPES)
        is_chart = bool(re.search(_CHART_WORD, head, re.I)) and not is_table
        if is_table:
            tables += 1
            ns = [int(m.group(1)) for m in _ROW_COUNT.finditer(seg) if 2 <= int(m.group(1)) <= 200]
            rows_ = max([rows_] + ns)
        elif is_chart:
            charts += 1
    if len(segs) == 1 and not tables and not charts:
        if rec in _TABLE_RECIPES:
            tables = 1
        elif rec and rec not in _WHOLE_PAGE:
            charts = 1
    return rows_, tables, charts


def _over_capacity(row):
    """Why a PAGES row will not fit one page ("" when it fits): only clear overloads — a table of > 8 rows plus a chart,
    > 2 charts plus a table, or > 20 table rows."""
    rows_, tables, charts = _row_load(row)
    if rows_ > CAP_TABLE_WITH_CHART and charts >= 1:
        return f"{rows_} 行表 + {charts} 张图"
    if charts > CAP_CHARTS_WITH_TABLE and tables >= 1:
        return f"{charts} 张图 + {tables} 张表"
    if rows_ > CAP_TABLE_ALONE:
        return f"{rows_} 行表（一页约 {CAP_TABLE_ALONE // 2}–{CAP_TABLE_ALONE} 行）"
    return ""


MAX_BLOCKS_PER_ROW = 3   # a plan row naming > 3 components (KPI row, charts, tables, rail, conclusion bar) is rejected
_NEG = (r"(?:(?:不设|不放|无需|无须|不|无|没有|去掉|删掉|禁|免)(?:加|用|放|要|做|写|设)?\s*"
        r"|\b(?:no|without)\s+(?:right[- ]?(?=rail)|separate\s+)?)")   # "No right rail" (English plans)
_KPI_WORD = r"KPI|指标行|大数字|kpi_strip|kpi_cards|\bkpis\b"
_BAR_WORD = r"结论条|底条|结论框|read_across"
_RAIL_WORD = r"右栏|要点栏|关键要点|rail|key_takeaways|右侧要点"
_IMG_WORD = r"示意图|线稿|cutaway|工程剖面|image 模块|生图"


def _row_components(row):
    """[component names] a PAGES row asks for: charts and tables (_row_load), KPI row, right rail, conclusion bar,
    image module. Negated mentions ("不加结论条") do not count."""
    body = " ".join(str(row.get(k) or "") for k in ("body", "layout_recipe"))
    clean = re.sub(_NEG + f"(?:{_KPI_WORD}|{_BAR_WORD}|{_RAIL_WORD}|{_IMG_WORD})", " ", body, flags=re.I)
    if _whole_page_row(row):   # "右栏 table / 右栏 图" of a mixed / columns page is one of its columns, not a rail
        clean = re.sub(r"右栏", " ", clean)
    _, tables, charts = _row_load(row)
    out = [f"图×{charts}"] * (1 if charts else 0) + [f"表×{tables}"] * (1 if tables else 0)
    n = charts + tables
    for name, pat in (("KPI 行", _KPI_WORD), ("结论条", _BAR_WORD), ("右栏", _RAIL_WORD), ("示意图", _IMG_WORD)):
        if re.search(pat, clean, re.I) or (name == "右栏" and _wants_takeaways(dict(row, body=clean)) and not _whole_page_row(row)):
            out.append(name)
            n += 1
    return n, out


_COLUMN_PAGES = ("mixed_columns_page", "columns_page", "four_columns")


def _whole_page_row(row):
    """The row is a whole-page column layout (its right column is content, not a takeaway rail)."""
    return bool({str(row.get("recipe", "")).split("/")[0].strip(), str(row.get("layout_recipe", "")).strip()}
                & set(_COLUMN_PAGES))


def rail_share_issue(pages):
    """plan_ready: right-rail (key_takeaways) rows of the data pages, counted from PAGES (the write-time ledger misses
    pages built by other agents). "" or one message when > RESEARCH_SIDE_SHARE of ≥ 4 data pages carry it.
    One share for the plan gate and plan_check: a stricter gate here makes Organizers strip rails plancomp demands back."""
    rows = [r for r in pages or [] if isinstance(r, dict) and str(r.get("p", "")).isdigit() and r.get("chart") is not False
            and str(r.get("recipe", "")).split("/")[0].strip() not in ("appendix", "附录", "")]
    if len(rows) < 4:
        return ""
    rail = [f"P{r['p']}" for r in rows if "右栏" in _row_components(r)[1]]
    if len(rail) / len(rows) <= RESEARCH_SIDE_SHARE:
        return ""
    return (f"右栏要点写在了 {len(rail)}/{len(rows)} 个数据页（{'、'.join(rail[:10])}，>{RESEARCH_SIDE_SHARE:.0%}）：其中几页改成"
            "左主图 + 下方拆解、两图并排同口径、整页版式（mixed_columns_page / columns_page / kpi_charts_page）或通栏图 + 图内 callout")


RESEARCH_SKELETON = {   # business-research.md 骨架覆盖 → PAGES title/body keywords
    "company": (("分业务拆分", r"分业务|分部|业务拆分|各业务|业务线|分产品|量价"),
                ("可比估值", r"可比|同业估值|对标估值|comps"),
                ("PE/PB 带", r"PE\s*/?\s*PB|PE带|PB带|PE 带|PB 带|估值带|历史分位|band"),
                ("催化剂", r"催化"),
                ("共识与分歧", r"共识|分歧|预期差")),
    "industry": (("供需对照图", r"供需|供给.{0,8}需求|需求.{0,8}供给|利用率|平衡"),
                 ("价格序列", r"价格|单价|租金|报价|ASP"),
                 ("资本开支", r"资本开支|capex|投资规模|投资额"),
                 ("标的推荐表", r"标的|推荐|受益|组合|个股")),
}
_IC_MARK = r"IC|投资判断|目标价|评级|公司深度|值不值得投|估值"
_INDUSTRY_MARK = r"行业|市场|赛道|产业|供需|格局"


def skeleton_issue(pages, query=""):
    """plan_ready (business-research): IC / industry skeleton chapters not named by any PAGES title/body ("" when all
    are covered or the deck is neither)."""
    rows = [r for r in pages or [] if isinstance(r, dict)]
    if len(rows) < 6:
        return ""
    text = " ".join(f"{r.get('title', '')} {r.get('body', '')}" for r in rows)
    titles = " ".join(str(r.get("title", "")) for r in rows) + " " + str(query)
    kind = "company" if re.search(_IC_MARK, titles) else "industry" if re.search(_INDUSTRY_MARK, titles) else None
    if not kind:
        return ""
    miss = [name for name, pat in RESEARCH_SKELETON[kind] if not re.search(pat, text, re.I)]
    if not miss:
        return ""
    return (f"{'公司深度 / IC' if kind == 'company' else '行业研究'}骨架里这些章节 PAGES 没覆盖：{'、'.join(miss)}——"
            "每项补一页（查不到写缺口与替代证据），页数不设上限，不用删别的页换（只提示一次）")


_QI_DIMS = {   # breakdown dimension the user names → words a page about that breakdown carries
    "region": r"region|geograph|地区|区域", "country": r"countr|国家|各国", "product": r"product|产品", "segment": r"segment|分部|业务线",
    "channel": r"channel|渠道", "customer": r"customer|客户", "category": r"categor|品类", "city": r"\bcit(?:y|ies)|城市|[六五四七八]城",
    "vehicle": r"per[- ]vehicle|per car|per[- ]unit|单车|每辆", "store": r"per[- ]store|单店", "user": r"per[- ]user|ARPU|单用户|人均"}
_QI_SYN = {"subsc": r"subsc|member", "prici": r"pric|asp\b", "price": r"pric|asp\b", "growt": r"growt|grew|adds|\+\d", "增长": r"增长|增速|同比"}
_QI_ZH = {"地区": "region", "区域": "region", "国家": "country", "产品": "product", "业务": "segment", "分部": "segment",
          "渠道": "channel", "客户": "customer", "品类": "category", "城市": "city", "单车": "vehicle", "单店": "store"}


def _query_items(query):
    """Breakdowns the user names: [(item, dimension, [metric words], [listed members])] — "market share by region",
    "gross margin per vehicle", "各渠道的增长/客单价", "data center revenue by product (Hopper, Blackwell, networking)"."""
    q = re.sub(r"^.*?(?:use this version for the task below\.|并用这个版本完成下面的任务。)", "", str(query or ""), flags=re.S)
    out = []
    for m in re.finditer(r"([A-Za-z][A-Za-z /-]{2,40}?)\s+(by|per|across)\s+([a-z]+)(?:\s*\(([^)]*)\))?", q):
        dim = next((k for k in _QI_DIMS if m.group(3).startswith(k[:5])), None)
        if not dim:
            continue
        lead = re.split(r",|:|\band\b", m.group(1))[-1].strip()
        words = [w.lower()[:5] for w in re.findall(r"[A-Za-z]{3,}", lead) if w.lower() not in ("the", "and", "deliveries")][-2:]
        mem = [x.strip() for x in re.split(r"[,，、]", m.group(4) or "") if x.strip()]
        out.append((f"{lead} {m.group(2)} {m.group(3)}", dim, words, mem))
    for m in re.finditer(r"(?:各|按|分)(地区|区域|国家|产品|业务|分部|渠道|客户|品类|城市)(?:的|各\S{1,3}的)?([^，,；;。：:（(]{2,30})", q):
        if re.search(r"数据|附件|明细|\.csv|\.xlsx|字段|行[）)]?$", m.group(2)) or re.search(r"附件|数据[：:（(]|csv|xlsx", q[max(0, m.start() - 12):m.start()], re.I):
            continue   # "附件：各城市分品类经营数据" describes the input, not an analysis the user asks for
        mets = [t for t in re.split(r"[/、与和及]", re.sub(r"诊断|表现|对比|情况|分析|结构", "", m.group(2))) if len(t) >= 2]
        mets = [t for t in mets if re.search(r"增长|增速|收入|营收|销量|售价|价格|客单|毛利|利润|ROI|退货|复购|份额|占比|订单|单价|转化|留存|成本|费用", t, re.I)]
        for t in mets[:5]:
            out.append((f"各{m.group(1)}{t}", _QI_ZH[m.group(1)], [t], []))
    return out


def query_coverage_issue(pages, query):
    """plan_ready: a breakdown the query names (by region / per vehicle / 各渠道客单价) that no PAGES row draws — no row names
    both the metric and the dimension (or ≥ 2 of the listed members). A hint, never a hold."""
    rows = [f"{r.get('title', '')}。{r.get('body', '')}" for r in pages or [] if isinstance(r, dict)
            and not re.match(r"\s*(?:附录|appendix)", f"{r.get('title', '')} {r.get('recipe', '')}", re.I)]
    if len(rows) < 6:
        return ""
    def near(r, dim, words, mem):   # metric and dimension in one sentence of one row, or ≥ 2 listed members
        low = r.lower()
        if sum(x.lower() in low for x in mem) >= 2:
            return True
        # "承接 P11 城市分化" / "next: regional mix" points at another page; it covers nothing here
        r = re.sub(r"(?:承接|衔接|引出|下一页|下页|见\s*P\d|next\b|see\s+p\d)[^，,。；;\n]*", " ", r, flags=re.I)
        found = lambda win: all(re.search(_QI_SYN.get(w.lower(), re.escape(w.lower())), win) for w in words)   # noqa: E731
        if re.search(r"每格|面板|小多图|small[ _]multiples|each panel", r, re.I) and re.search(_QI_DIMS[dim], r, re.I):
            return not words or found(r.lower())   # one panel per member: the whole row is that breakdown
        for sent in re.split(r"[。；;！？!?\n]", r):
            for m in re.finditer(_QI_DIMS[dim], sent, re.I):
                # a breakdown (各城市 / 分城市 / 5 城市× / by city) carries over the whole sentence; a bare mention
                # ("城市分化三大风险") only covers the metric in its own list item
                cut = bool(re.search(r"(?:各|分|按|每|×|\d|[二三四五六七八九十]|by|per|across|each)\s*$", sent[max(0, m.start() - 7):m.start()], re.I)
                           or re.match(r"\s*(?:×|x\b|维度|拆分|分布|排名|对比)", sent[m.end():], re.I))
                if cut:
                    win = sent.lower()
                else:
                    a = max([sent.rfind(c, 0, m.start()) for c in "、，,"] + [-1]) + 1
                    b = min([i for i in (sent.find(c, m.end()) for c in "、，,") if i >= 0] + [len(sent)])
                    win = sent[a:b].lower()
                if not words or found(win):
                    return True
        return False
    miss = []
    for item, dim, words, mem in _query_items(query):
        ok = any(near(r, dim, words, mem) for r in rows)
        if not ok:
            miss.append(item)
    if not miss:
        return ""
    return (f"用户点名的拆解在 PAGES 里没有对应页：{'、'.join(dict.fromkeys(miss))}——每项要有一页按这个维度画图（title / body 写出"
            "维度和指标）；已覆盖但换了说法的忽略（只提示一次）")


def block_issues(pages):
    """plan_ready rejection: PAGES rows with more than MAX_BLOCKS_PER_ROW components."""
    bad = []
    for r in pages or []:
        if not isinstance(r, dict) or not str(r.get("p", "")).isdigit() or r.get("chart") is False:
            continue
        n, names = _row_components(r)
        if n > MAX_BLOCKS_PER_ROW:
            bad.append(f"P{r['p']}（{n} 块：{'、'.join(names)}）")
    return bad


def capacity_issues(pages):
    """plan_check item: PAGES rows over one page's capacity, each with how to split it into a/b pages."""
    bad = []
    for r in pages or []:
        if not isinstance(r, dict) or not str(r.get("p", "")).isdigit():
            continue
        why = _over_capacity(r)
        if why:
            bad.append(f"P{r['p']}（{why}）")
    if not bad:
        return []
    return [f"{CAPACITY_MSG}，这些行要拆成 a/b 两页：{'、'.join(bad)}。每行拆成相邻两页（a=表、b=图；或 a=表前一半行、b=其余行，"
            "同表头），在 PAGES 里插入新行（新页 p=N+1、写 split_of=N、deps 与原行相同，后面还没领走的页号顺延），"
            "两页交不同 builder 并行做——页数不设上限，一页塞满会反复放不下拖成关键路径"]


# How the charts of one page connect (consulting decks: every multi-chart page is one of these; anything else = two
# unrelated charts → one big chart). Key → (name, how it is drawn).
CHART_RELATIONS = {
    "expand": ("总量→展开", "左图一根柱 / 一段在右图或右表拆开：expand_panels + expand，被展开的段 accent、其余灰"),
    "slices": ("同一指标两个切面", "同一总量按两种维度切（按地区 / 按产品），柱位、年份、总计一致，同对象同色"),
    "stock_flow": ("结构→变化", "左 100% 堆叠讲份额，右桥图讲增量来自谁，两图分类与颜色一致"),
    "multiples": ("同尺度小多图", "small_multiples 共用尺度 / 基准线 ref=，每格一个大数字 kpi="),
    "drivers": ("总量 + 驱动分解", "左大图总量，右侧 2–6 个驱动因子小图（同年份、最新期同色），或驱动树每个节点一张小图"),
    "chain": ("三栏论证链", "2–3 张图共用类别轴与配色，每张图的判断句小标题连起来 = 页标题"),
    "evidence": ("定量 + 定性互证", "左图右引述 / 访谈原话，原话引线连到图上那一段"),
}
_REL_ALIASES = {"展开": "expand", "drill": "expand", "切面": "slices", "两个切面": "slices", "结构变化": "stock_flow",
                "结构→变化": "stock_flow", "小多图": "multiples", "small_multiples": "multiples", "驱动": "drivers",
                "驱动分解": "drivers", "论证链": "chain", "三栏": "chain", "互证": "evidence", "引述": "evidence"}


def _rel_key(v):
    v = str(v or "").strip()
    return v if v in CHART_RELATIONS else _REL_ALIASES.get(v, "")


def relation_issues(pages):
    """plan_ready (business-research): rows that draw ≥2 charts must say how they connect — rel= one of
    CHART_RELATIONS — else the page is two unrelated charts and should be one big chart (or two pages)."""
    bad = []
    for r in pages or []:
        if not isinstance(r, dict) or not str(r.get("p", "")).isdigit() or r.get("chart") is False:
            continue
        rec = str(r.get("recipe", "")).split("/")[0].strip()
        if rec in ("small_multiples", "baseline_panels", "shared_time", "shared_rows", "expand_row", "expand_bar",
                   "expand_segment", "pie_of_pie", "panel_trends", "panel_pair") and not r.get("rel"):
            continue   # the recipe itself is the relation
        _, tables, charts = _row_load(r)
        if charts >= 2 and not _rel_key(r.get("rel")):
            bad.append(f"P{r['p']}")
    if not bad:
        return ""
    opts = "；".join(f"{k}={v[0]}（{v[1]}）" for k, v in CHART_RELATIONS.items())
    return (f"多图页没写图之间的关系：{'、'.join(bad)}——每个 ≥2 张图的 PAGES 行加 rel=，七选一：{opts}。"
            "写不出就是两张互不相关的图：只留一张大图（另一个指标放轴下数据行 rows= 或右栏），或拆成两页")


RESEARCH_SIDE_SHARE = 0.65   # business-research (strategy flow): KEY TAKEAWAYS rail on ≤65 % of data pages (CATL IC ≈61 %);
_WHOLE_PAGE = ("kpi_charts_page", "columns_page", "four_columns", "mixed_columns_page", "diagram_page")


def _num_pool(obj, out, depth=0):
    if depth > 6:
        return
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        out.add(float(obj))
    elif isinstance(obj, str):
        for m in re.findall(r"\d[\d,]*(?:\.\d+)?", obj):
            try:
                out.add(float(m.replace(",", "")))
            except ValueError:
                pass
    elif isinstance(obj, dict):
        for v in obj.values():
            _num_pool(v, out, depth + 1)
    elif isinstance(obj, (list, tuple, set)):
        for v in obj:
            _num_pool(v, out, depth + 1)


def _prose_numbers_unbacked(g, directory):
    """Numbers with a unit in STORY / CHAPTER_DESCS (and amounts in PAGES titles) that no F value or research constant
    carries (within rounding): estimates written before the research, which P2 / nav pages / titles print verbatim."""
    prose = " ".join(str(v) for v in (g.get("STORY") or {}).values()) if isinstance(g.get("STORY"), dict) else ""
    prose += " " + " ".join(str(v) for v in (g.get("CHAPTER_DESCS") or {}).values()) \
        if isinstance(g.get("CHAPTER_DESCS"), dict) else ""
    if not prose.strip():
        return []
    titles = " ".join(str(r.get("title") or "") for r in g.get("PAGES", []) or [] if isinstance(r, dict))
    pool = set()   # research constants + F values plan.py computes (a literal typed into F may be the estimate itself)
    try:
        import ast
        typed = {float(n.value) for n in ast.walk(ast.parse((Path(directory) / "plan.py").read_text(encoding="utf-8")))
                 if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool)}
    except (OSError, SyntaxError, ValueError):
        typed = set()
    fvals = set()
    _num_pool(g.get("F"), fvals)
    pool |= {v for v in fvals if not any(abs(v - t) <= 1e-9 for t in typed)}
    rdir = Path(directory) / "research"
    for f_ in sorted(rdir.glob("R*.py")) if rdir.exists() else []:   # numeric values only (source quotes may hold
        try:                                                          # every alternative estimate)
            import ast
            for node in ast.walk(ast.parse(f_.read_text(encoding="utf-8", errors="ignore"))):
                if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
                    pool.add(float(node.value))
        except (OSError, SyntaxError, ValueError):
            pass
    if len(pool) < 10:   # research not in yet: nothing to compare against
        return []
    unit = (r"(?:%|pct|pp|pt|倍|x|×|亿|万|千|百万|GWh|MWh|TWh|GW|MW|kW|EFLOPS|PFLOPS|元|美元|港元|欧元|日元|M€|€|\$|B\b|M\b|bn|"
            r"万辆|万台|家|座|店|万吨|吨|万人|nm)")
    bad = []
    money = r"(?:亿|万|元|美元|港元|欧元|日元|M€|€|\$|B\b|bn|GWh|万辆|万吨)"
    # amounts only: a % / x in prose is usually a ratio of research values computed on the page
    items = [(m, True) for m in re.finditer(r"(?<![\w.])([$€¥£]?)(\d[\d,]*(?:\.\d+)?)\s*(" + money + ")", prose)]
    # page titles: only amounts (targets, market sizes) — a title's % / x is usually derived on the page itself
    items += [(m, False) for m in re.finditer(r"(?<![\w.])([$€¥£]?)(\d[\d,]*(?:\.\d+)?)\s*(" + money + ")", titles)]
    for m, _ in items:
        src = prose if _ else titles
        if re.search(r"\d\s*[-–~～至到]\s*$", src[max(0, m.start() - 3):m.start()]) or \
                re.match(r"\s*[-–~～至到]\s*\d", src[m.end():m.end() + 3]):
            continue   # a range end ("7-20 万元车型"): a band, not a measured value
        v = float(m.group(2).replace(",", ""))
        if re.search(r"(?:每|per|each|±|\+/-)\s*[+±−-]?\s*[$€¥£]?\s*$", src[max(0, m.start() - 8):m.start()], re.I):
            continue   # a sensitivity step ("铜价每 +1000 美元"): an assumption, not a measured value
        if (1990 <= v <= 2100 and "." not in m.group(2)) or v in (0, 1, 2, 3):
            continue
        ks = (1, 100) if m.group(3) in ("%", "pct", "pp", "pt") else (1, 1e4, 1e-4) if m.group(3) in ("亿", "万") else (1,)
        near = lambda a: any(abs(a * k - v) <= max(0.051, abs(v) * 0.012) for k in ks)   # noqa: E731
        if not any(near(a) for a in pool):
            bad.append(m.group(0).strip())
    return list(dict.fromkeys(bad))


_PROSE_PH = re.compile(r"[（(]?[^，。；（()）]{0,8}待\s*(?:R\d|调研|研究|数据)?\s*(?:补|填|回填|核实|确认|更新)[^，。；（()）]{0,4}[）)]?"
                       r"|\bTBD\b|\bTODO\b|\bXX+\b|[xX]{2,}\s*(?:%|亿|万)")


def _prose_placeholders(g):
    """Placeholder phrases left in STORY / CHAPTER_DESCS / PAGES titles ("数字待 R1 补", TBD, XX%): P2 and the chapter
    navigation pages print these strings verbatim."""
    vals = []
    for k in ("STORY", "CHAPTER_DESCS"):
        if isinstance(g.get(k), dict):
            vals += [str(v) for v in g[k].values()]
    vals += [str(r.get("title") or "") for r in g.get("PAGES", []) or [] if isinstance(r, dict)]
    return list(dict.fromkeys(m.group(0).strip() for v in vals for m in _PROSE_PH.finditer(v)))


def plan_check(directory):
    """Deck-level mix of plan.py PAGES: chart types, multi-chart / text-from-chart layouts, common chart share.
    Returned with plan_ready so the Organizer fixes the mix by editing PAGES before builders start."""
    import contextlib
    import io
    import runpy
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            sys.path[:0] = [str(directory)]
            g = runpy.run_path(str(Path(directory) / "plan.py"), run_name="plan_check")
    except Exception as e:  # noqa: BLE001
        return [f"plan.py 运行出错：{type(e).__name__}: {str(e)[:160]}"]
    finally:
        if sys.path and sys.path[0] == str(directory):
            sys.path.pop(0)
    rows = [r for r in g.get("PAGES", []) or [] if r.get("chart") is not False]
    recs = [str(r.get("recipe", "")).split("/")[0].strip() for r in rows]
    data = [x for x in recs if x and x not in ("appendix", "附录")]
    side = _side_variety(g.get("PAGES", []) or [])
    side = capacity_issues(g.get("PAGES", []) or []) + side   # first: plan_mix is cut to 4 items downstream
    sec0 = {int(k): str(v) for k, v in (g.get("SECTIONS") or {}).items() if str(k).isdigit()}
    first_ch = _first_chapter(sec0)
    body1 = min([int(r["p"]) for r in g.get("PAGES", []) or [] if isinstance(r, dict) and str(r.get("p", "")).isdigit()
                 and int(r["p"]) >= 2 and not re.match(r"\s*(contents|目录|exec_summary|执行摘要|摘要|summary|cover|封面)",
                                                       str(r.get("recipe") or r.get("title") or ""), re.I)] or [0])
    front_extra = [k for k, v in sec0.items() if 4 <= k < first_ch and not re.search(r"封面|cover", v, re.I)] if first_ch else []
    if (first_ch and first_ch < 4) or (body1 and body1 < 4):   # front pages: P1 cover → P2 summary → P3 contents
        n_ = 4 - min(x for x in (first_ch, body1) if x)
        side = [f"固定结构是 P1 封面 → P2 执行摘要 → P3 目录 → 第一章从 P4 起（现在正文从 P{min(x for x in (first_ch, body1) if x)} 起）："
                f"PAGES / SECTIONS 的正文页号整体 +{n_}，SECTIONS 改为 {{2: \"执行摘要\", 3: \"目录\", 4: 第一章, …}}；"
                "P2、P3 不写 PAGES 行（Main 用 publish_contents_and_navs 一起画）"] + side
    elif front_extra:
        side = [f"P4–P{first_ch - 1} 在第一章之前（{sec0.get(front_extra[0], '')}…）：P2 执行摘要已给答案 + 关键数字 + 支撑结论，"
                f"不要再放单独的投资要点 / 摘要页——第一章从 P4 开始，原来那页的要点并进 P2 的 answer / kpis / points 或第一章"] + side
    first_at = {}
    for r in g.get("PAGES", []) or []:
        if isinstance(r, dict) and isinstance(r.get("section"), str) and str(r.get("p", "")).isdigit():
            first_at.setdefault(r["section"].strip(), int(r["p"]))
    by_name = {v.strip(): k for k, v in sec0.items()}
    missing_ch = [nm for nm in first_at if nm not in by_name and not re.search(r"附录|appendix|术语|glossary", nm, re.I)]
    if missing_ch and sec0:
        side = [f"PAGES 里有章名不在 SECTIONS：{'、'.join(missing_ch[:3])}——目录和导航页只列 SECTIONS 的章，这些页会算进上一章、"
                f"页码区间错。把它们加进 SECTIONS（起始页 {', '.join(str(first_at[n]) for n in missing_ch[:3])}）"] + side
    off = [(nm, by_name[nm], p_) for nm, p_ in first_at.items() if nm in by_name and by_name[nm] != p_]
    if off:
        fixed = dict(sorted({**{k: v for k, v in sec0.items() if v.strip() not in first_at},
                             **{p_: nm for nm, p_ in first_at.items() if nm in by_name}}.items()))
        side = [f"SECTIONS 与 PAGES 的 section 错位：" + "；".join(f"「{nm}」SECTIONS 写从 P{a_} 开始，PAGES 里第一页是 P{b_}"
                                                       for nm, a_, b_ in off[:3])
                + f"——目录页码区间和页眉都按 SECTIONS 算，会整体错页。SECTIONS 改为 {fixed}"] + side
    ph = _prose_placeholders(g)
    if ph:   # placeholders in CHAPTER_DESCS are printed verbatim on P2 and nav pages
        side = [f"STORY / CHAPTER_DESCS / 页标题里还有占位：{'、'.join(ph[:4])}——P2 和导航页会原样印出：改成从 F 拼的结论句"
                "（f-string），没有数就写不带数的判断，删掉占位"] + side
    stale = _prose_numbers_unbacked(g, directory)
    if stale:
        side = [f"STORY / CHAPTER_DESCS / 页标题里的金额在 research 变量里找不到：{'、'.join(stale[:6])}——这些是研究前写的估计，"
                "P2 和导航页会原样印出、与正文对不上：改成从 F 拼（f-string），或删掉这个数"] + side
    swot = [r.get("p") for r in g.get("PAGES", []) or [] if isinstance(r, dict)
            and re.search(r"swot", f"{r.get('recipe', '')} {r.get('title', '')}", re.I)]
    if swot:
        side = [f"P{'、P'.join(map(str, swot))} 是 SWOT 页：研究稿不做 SWOT 四格（读起来像模板）——改成与对手的对标表 / "
                "评分矩阵（row_table：维度 × 我方 vs 对手，每格写数字证据），或并入相关章节的要点"] + side
    lays = [r for r in rows if {str(r.get("recipe", "")), str(r.get("layout_recipe", ""))} & set(_WHOLE_PAGE)]
    if len(data) >= 6 and len(lays) < 2:
        side = side + [f"整页版式只有 {len(lays)} 页：至少 2 页写 recipe 或 layout_recipe = kpi_charts_page（上方 2–4 指标 + 下方 1–2 图，"
                       "适合结果/现状页）/ columns_page（三表 + icon + kv 行，适合方案或对象对比）/ four_columns / mixed_columns_page / "
                       "diagram_page；替换只有 2–3 根柱或 2 行表的页"]
    if len(data) < 5:
        return side
    out = list(side)
    # chart type follows the data relation (basic charts first): no quotas on multi-chart pages, rare chart types,
    # bar/line share, tables or number of schemes — they pushed plans towards decorative composites and extra blocks
    side = [r for r in rows if re.search(_SIDE_TEXT, str(r.get("body", "")), re.I)
            or str(r.get("side") or "").strip().lower() == "takeaways" or r.get("layout_recipe") == "key_takeaways"]
    if len(side) > RESEARCH_SIDE_SHARE * len(data):
        out.append(f"{len(side)}/{len(data)} 页写了左图/左表 + 右侧要点（上限 {RESEARCH_SIDE_SHARE:.0%}）：其中几页改成全宽图 + 图内标注、"
                   "chart_takeaway（右侧拆解栏）、table_panel、多图，或整页版式 layout_recipe=columns_page / "
                   "mixed_columns_page / four_columns / diagram_page")
    import collections as _c
    many = [k for k, v in _c.Counter(data).items() if v > 2]
    if many:
        out.append(f"同一方案超过 2 页 {many}：其中几页换成同一比较关系的其他方案（路由表同一行的另一个候选）")
    per = _c.Counter(d for r in g.get("PAGES", []) or [] for d in (r.get("deps") or [])
                     if _is_researcher(d) and len(r.get("deps") or []) == 1)
    heavy = {k: v for k, v in per.items() if v > 4}
    if heavy:   # one direction with 5+ pages is built serially by one agent and becomes the tail
        out.append(f"方向页数不均 {dict(per)}：{list(heavy)} 超过 4 页会成为拖尾——把其中 1–2 页的 deps 改给页少的方向，或合并成多图页")
    q = _query_text(directory)
    body_q = re.sub(r"^.*?(?:use this version for the task below\.|并用这个版本完成下面的任务。)", "", q, flags=re.S)
    titles = " ".join(str(r.get("title", "")) for r in g.get("PAGES", []) or [])
    requested_language = _requested_language(body_q)
    if requested_language == "en" and len(re.findall(r"[\u4e00-\u9fff]", titles)) > 20:
        out.insert(0, "语言错了：用户原文是英文，整份 deck（标题、图内标签、要点、来源）都要用英文——把 PAGES 的 title/body 改成英文")
    elif requested_language == "zh" and titles and len(re.findall(r"[\u4e00-\u9fff]", titles)) < 5:
        out.insert(0, "语言错了：用户原文是中文，整份 deck 用中文——把 PAGES 的 title 改成中文")
    hints = []
    if re.search(r"内部|其中|平台.{0,6}(份额|占比)|within|of which|split of .{0,20}(online|channel)", q, re.I) \
            and "pie_of_pie" not in data:
        hints.append("用户要\"某一块内部的构成\"（如外卖/线上内部各平台占比）→ pie_of_pie")
    if re.search(r"季节|旺季|淡季|月度|大促|seasonal|by month|monthly|peak", q, re.I) and "ridgeline" not in data:
        hints.append("用户要季节性/月度峰值 → ridgeline（各年一行，峰值月份一眼可比）——前提是 research 里有真实的分月/分季数据；"
                     "没有就用季度柱 + band 标出旺季，不要编'示意指数'")
    if re.search(r"against .{0,30}price|价格.{0,6}(走势|指数)|电价|油价|vs\.? price", q, re.I) and "layered_area" not in data:
        hints.append("总量与分项 + 价格同图 → layered_area(line=价格)")
    if hints:
        out.append("这些问题有更贴切的复合图：" + "；".join(hints) + "（exhibit_help('<方案>') 看代码）")
    same = [recs[i] for i in range(1, len(recs)) if recs[i] and recs[i] == recs[i - 1]]
    if same:
        out.append(f"相邻页同方案 {sorted(set(same))}：合并或换方案")
    tbl = [f"P{r.get('p')}" for r, x in zip(rows, recs) if x in ("row_table", "text_table", "table", "表格", "对照表")
           or (x == "roadmap" and not re.search(r"Range|甘特|起止", str(r.get("body", ""))))]
    if len(data) >= 8 and len(tbl) > max(2, 0.2 * len(data)):
        out.append(f"表格页偏多 {tbl}（{len(tbl)}/{len(data)} 个数据页）：表格只给精确值，论点要靠图——"
                   "多对象 × 一个指标改条形 / 点图（rank_table 带 Bar）、两期改 dumbbell_table、两指标改 bubble_map、"
                   "事件清单改 timeline；只留 1–2 页真正需要逐格读数的财务 / 估值表")
    import collections as _cc
    data_names = {k for k, v in g.items() if re.fullmatch(r"[A-Z][A-Z0-9_]{2,}", k)
                  and isinstance(v, (list, dict, tuple)) and k not in ("PAGES", "SECTIONS", "SRC", "STORY", "F", "ME")}
    uses = _cc.defaultdict(list)
    for r in rows:
        for nm in set(re.findall(r"\b[A-Z][A-Z0-9_]{2,}\b", str(r.get("body", "")))) & data_names:
            uses[nm].append(r.get("p"))
    heavy_use = {k: v for k, v in uses.items() if len(v) >= 3}
    if heavy_use:
        k0, v0 = max(heavy_use.items(), key=lambda kv: len(kv[1]))
        out.append(f"同一组数据画了 {len(v0)} 页：{k0} 出现在 P{'、P'.join(map(str, v0))}——同一组对象 × 同一指标只画一次，"
                   "其余页换成别的证据（另一个指标、另一组对象、时间序列或财务数据），或把几页合成一页多图")
    xp_plan = cross_page_conflicts({int(r["p"]): f"{r.get('title', '')} {r.get('body', '')}" for r in g.get("PAGES", []) or []
                                    if isinstance(r, dict) and str(r.get("p", "")).isdigit()})
    if xp_plan:
        out.insert(0, "PAGES 里同一指标同一期间写了不同的数：" + "；".join(xp_plan[:3]) +
                   "——在 F 里定一个值，标题 / body 都用 f-string 引用同一个键")
    allp = [r for r in g.get("PAGES", []) or [] if isinstance(r, dict)]
    gl = [r.get("p") for r in allp if re.search(r"glossary|术语表|术语与来源", f"{r.get('recipe', '')} {r.get('title', '')}", re.I)]
    if gl:   # terms are explained in each page's footer line; a glossary page repeats them and often sits half empty
        out.append(f"P{'、P'.join(map(str, gl))} 是术语表页：研究稿不做术语表（每页页脚已自动解释首次出现的术语，术语少时整页空着）"
                   "——删掉这一行；数据来源已在各页脚注，可点击")
    if len(allp) >= 10 and not any(re.search(r"^appendix|方法|口径|假设", f"{r.get('recipe', '')} {r.get('title', '')}", re.I)
                                   for r in allp if not re.search(r"glossary|术语", str(r.get("recipe", "")))):
        out.append("缺方法论附录：加一页 recipe=\"appendix\"（口径、测算假设、估值方法）")
    sec = g.get("SECTIONS") or {}
    chapters = [k for k, v in sec.items() if str(k).isdigit() and int(k) > 2
                and not re.search(r"目录|摘要|附录|appendix|contents|summary", str(v), re.I)]
    navs = {int(r["p"]) for r in allp if str(r.get("p", "")).isdigit() and str(r.get("recipe", "")).startswith("chapter_nav")}
    starts_ = sorted(int(k) for k in chapters)
    ends_ = starts_[1:] + [max([int(r["p"]) for r in allp if str(r.get("p", "")).isdigit()] or [0]) + 1]
    short = [a for a, b in zip(starts_, ends_) if a in navs and b - a <= 2]   # nav + ≤1 content page: the nav is padding
    if short:
        out.append(f"P{'、P'.join(map(str, short))} 的章只有 1 页正文，不配章节导航页：删掉这些导航行（把章并入相邻章或只保留正文）")
    if any(str(v).strip() in ("执行摘要", "摘要", "Executive summary", "Summary") for k, v in sec.items() if str(k) == "3") \
            and any(str(v).strip() in ("目录", "Contents") for k, v in sec.items() if str(k) == "2"):
        out.append("P2 目录、P3 执行摘要顺序反了：固定结构是 P1 封面 → P2 执行摘要 → P3 目录 → 第一章 P4，SECTIONS 改为 "
                   "{2: \"执行摘要\", 3: \"目录\", 4: 第一章, …}；两页由 Main 用 publish_contents_and_navs 一起画")
    missing_nav = [int(k) for k in chapters if int(k) not in navs and int(k) not in short]
    if len(chapters) >= 4 and missing_nav and len(chapters) <= 6:
        out.append(f"{len(chapters)} 章：每章第一页前加一页章节导航（缺 P{'、P'.join(map(str, missing_nav[:6]))}）——"
                   f"每章一行 dict(p=章起始页, recipe=\"chapter_nav\", title=章名, chart=False, deps=[])"
                   "（Main 用 contents(..., current=第几章) 一行做，SECTIONS 的章起始页指向它），并在 plan.py 写 CHAPTER_DESCS")
    timey = [int(r["p"]) for r in allp if str(r.get("p", "")).isdigit()
             and re.search(r"row_table|rank_table|dumbbell_table", str(r.get("recipe", "")))
             and re.search(r"(?:逐年|历年|按年|年度|20\d{2}\s*[-–—~至到]\s*20\d{2}|季度|近\s*\d+\s*年).{0,30}(?:Bar|条|柱|趋势|增长)|"
                           r"(?:Bar|横条).{0,20}(?:年份|年度|季度)", f"{r.get('title', '')} {r.get('body', '')}")]
    if timey:
        out.append(f"P{'、P'.join(map(str, timey[:4]))} 用表格画时间序列：时间放横轴（columns / lines，第二指标放 rows= 轴下数据行），"
                   "不把年份竖排成表格行再画横条（有意为之可忽略）")
    dup = duplicate_titles(g.get("PAGES", []) or [])
    if dup:
        out.insert(0, f"重复页 {dup}：两页标题讲同一件事（同一组对象 × 同一指标）——合并成一页（多图 / 表 + 图），"
                      "腾出的页号改成骨架里还没覆盖的论点（盈利预测、估值敏感性、供需、标的表等）")
    allrows = [r for r in g.get("PAGES", []) or [] if isinstance(r, dict)]
    story_txt = " ".join(f"{r.get('title', '')} {r.get('body', '')}" for r in allrows) + " " + q
    if len(allrows) >= 10 and re.search(_SCHEMATIC_TOPIC, story_txt, re.I) and not any(
            re.search(_SCHEMATIC_PLAN, f"{r.get('recipe', '')} {r.get('layout_recipe', '')} {r.get('body', '')}", re.I)
            and not re.search(_SCHEMATIC_REFUSED, str(r.get("body", "")), re.I) for r in allrows):
        out.append("全稿没有示意图页：讲产品/技术/工艺/商业模式的论点至少 1–2 页用示意线稿（cutaway / 原理 / 产品结构 / 工艺流程，"
                   "生图后 mixed_columns_page image + callouts）或架构/流程/价值链图（drawing 库或手写 XML）——按公开资料里通用、已知的"
                   "构造层级画，图注写“示意图，非精确比例/非官方图纸”，不需要官方逐部件原文；只有具体参数数值要来源")
    return out


def _title_terms(t):
    t = re.sub(r"\{[^}]*\}|[\d.,%+−\-~约亿万元倍x×：:；;，,、（）()“”\"'·\s]+", " ", str(t))
    grams = set()
    for part in t.split():
        if re.search(r"[\u4e00-\u9fff]", part):
            grams |= {part[i:i + 2] for i in range(len(part) - 1)}
        elif len(part) > 2:
            grams.add(part.lower())
    return grams - {"行业", "公司", "市场", "我们", "其中", "对比", "分析"}


def duplicate_titles(pages, share=0.6):
    """[(p, q)] of page pairs whose titles share ≥ share of their 2-char terms (the same point told twice)."""
    rows = [(r.get("p"), _title_terms(r.get("title", ""))) for r in pages if isinstance(r, dict) and r.get("p")
            and str(r.get("p")).isdigit() and int(r["p"]) > 3]
    out = []
    for i, (p, a) in enumerate(rows):
        for q, b in rows[i + 1:]:
            if len(a) >= 4 and len(b) >= 4 and len(a & b) >= share * min(len(a), len(b)):
                out.append((p, q))
    return out[:4]


_SCHEMATIC_TOPIC = r"产品|技术|工艺|电芯|芯片|架构|商业模式|产业链|价值链|平台|机理|制程|product|technolog|process|architecture|business model|value chain"
_SCHEMATIC_PLAN = (r"cutaway|剖面|示意|线稿|架构图|流程图|价值链|产业链全景|飞轮|生态图|diagram|schematic|flow ?chart|"
                   r"mixed_columns_page|diagram_page|drawing")
_SCHEMATIC_REFUSED = r"不画|不用(?:工程|示意)|无需(?:工程|示意)|no (?:cutaway|diagram)"


def _load_plan(directory, run_name="plan_required"):
    import contextlib
    import io
    import runpy
    if not (Path(directory) / "plan.py").exists():
        return None
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            sys.path[:0] = [str(directory)]
            return runpy.run_path(str(Path(directory) / "plan.py"), run_name=run_name)
    except BaseException:  # noqa: BLE001 — a broken plan.py is reported by plan_check, not here
        return None
    finally:
        if sys.path and sys.path[0] == str(directory):
            sys.path.pop(0)


def wait(directory, phase, max_seconds=180, interval=10):
    target = PHASES.index(phase)
    deadline = time.time() + max_seconds
    started = time.time()
    while True:
        _touch_main(directory)
        status = _read(Path(directory) / "status.json")
        current = status.get("phase")
        if (phase == "plan_ready" and current not in PHASES[2:] and current != "failed"
                and time.time() - started > 240 and len(_plan_pages(directory)) >= 4):
            # plan.py already lists the pages: builders can start on it now (the organizer keeps wiring numbers)
            status = set_status(directory, "plan_ready", note="plan.py 已有 PAGES：wait 自动放行 plan_ready，数字随调研接入")
            current = "plan_ready"
        if current == "failed" or (current in PHASES and PHASES.index(current) >= target):
            return {"reached": current != "failed", "phase": current, "status": status}
        if time.time() >= deadline:
            return {
                "reached": False,
                "phase": current,
                "status": status,
                "next": "未到目标阶段：peek_agent 看 Organizer 是否还在运行；已退出或超过兜底时限就按文档兜底，否则再 wait 一次",
            }
        time.sleep(interval)


def _cli(args, cwd):
    proc = subprocess.run(["lark-cli", *args], check=False, capture_output=True, text=True, cwd=cwd, timeout=120)
    text = proc.stdout.strip() or proc.stderr.strip()
    try:
        return json.loads(text[text.index("{") :])
    except ValueError:
        return {"ok": False, "error": {"message": text[-500:]}}


FROZEN_LOCK = "frozen.lock"


def _write_frozen_lock(directory, pages):
    """SYNC/frozen.lock: the frozen page list, kept beside status.json so a hand edit of status.json ("frozen": [])
    does not unfreeze anything — Frame.publish / publish_slide read the lock too. Only set_status(organizer_done) and
    finish (its own consistency / missing-page unfreeze) write it."""
    _write(Path(directory) / FROZEN_LOCK, {"pages": sorted({int(p) for p in pages}), "t": time.time()})
    _seal(directory)


SEAL = ".seal"


def _task_cwd(directory):
    """The task CWD of a documented SYNC dir (<cwd>/.lark-slides/<strategy|review>/<task>/sync, or <cwd>/SYNC), else None."""
    d = Path(directory).resolve()
    if len(d.parents) > 3 and d.parents[1].name in ("strategy", "review") and d.parents[2].name == ".lark-slides":
        return d.parents[3]
    if d.name in ("SYNC", "sync"):
        return d.parent
    return None


def _sha(path):
    import hashlib
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return None


def _seal(directory, cwd=None):
    """<cwd>/.lark-slides/.seal: sha256 of SYNC/frozen.lock and SYNC/exported as multiagent_sync last wrote them, plus
    the server-block counters <cwd>/.lark-slides/blocked-*.json ("__blocked__"; Frame.publish reseals it on each count).
    publish refuses writes when any was deleted / changed by hand (the only legal reopening is finish --fix)."""
    cwd = Path(cwd).resolve() if cwd else _task_cwd(directory)
    if cwd is None:
        return
    path = cwd / ".lark-slides" / SEAL
    d = _read(path)
    sync = Path(directory).resolve()
    d[str(sync)] = {"frozen": _sha(sync / FROZEN_LOCK), "exported": _sha(sync / "exported")}
    d["__blocked__"] = {f.name: _sha(f) for f in sorted((cwd / ".lark-slides").glob("blocked-*.json"))}
    _write(path, d)


def _frozen_lock(directory):
    d = _read(Path(directory) / FROZEN_LOCK)
    try:
        return {int(p) for p in (d.get("pages") or [])}
    except (TypeError, ValueError):
        return set()


def _plan_pages(directory):
    """Page numbers of plan.py PAGES (the page list once the plan exists)."""
    import contextlib
    import io
    import runpy
    if not (Path(directory) / "plan.py").exists():
        return []
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            sys.path[:0] = [str(directory)]
            g = runpy.run_path(str(Path(directory) / "plan.py"), run_name="plan_pages")
        return sorted({int(r["p"]) for r in g.get("PAGES", []) or [] if str(r.get("p", "")).isdigit()})
    except Exception:  # noqa: BLE001
        return []
    finally:
        if sys.path and sys.path[0] == str(directory):
            sys.path.pop(0)


def _slide_ids(directory):
    """{"p05": slide_id} from <cwd>/.lark-slides/pages-<deck>.json of this task's deck(s)."""
    d = Path(directory).resolve()
    cwd = d.parents[3] if len(d.parents) > 3 and d.parents[1].name in ("strategy", "review") else d.parent
    out = {}
    for deck in _task_decks(d, cwd):
        out.update({k: v for k, v in _read(cwd / ".lark-slides" / f"pages-{deck}.json").items()
                    if re.fullmatch(r"p\d+", k) and isinstance(v, str)})
    return out


def _registered(directory):
    """Page keys ("p05") that publish_slide(page=N) already put in the deck (<cwd>/.lark-slides/pages-*.json): a page
    written with plain publish_slide (hand-written non-chart pages) counts as written even though no claim heartbeat ran."""
    d = Path(directory).resolve()
    cwd = d.parents[3] if len(d.parents) > 3 and d.parents[1].name in ("strategy", "review") else d.parent
    out = set()
    for deck in _task_decks(d, cwd):
        out |= {k for k in _read(cwd / ".lark-slides" / f"pages-{deck}.json") if re.fullmatch(r"p\d+", k)}
    return out


def _sync_born(directory):
    """When the SYNC dir was set up (oldest of the dir and its top-level files)."""
    d = Path(directory)
    ts = []
    for f in [d, *d.iterdir()] if d.is_dir() else []:
        try:
            st = f.stat()
            ts.append(getattr(st, "st_birthtime", st.st_mtime))
        except OSError:
            pass
    return min(ts) if ts else 0.0


def _stamp_deck(directory, deck=None):
    """Write SYNC/deck.txt when it is missing (Main forgot the echo): from the deck finish / export was given, else the
    one page registry this task wrote. A delivered SYNC dir must name its deck — publish ties its freeze to that deck."""
    d = Path(directory)
    if (d / "deck.txt").exists() or not d.is_dir():
        return
    cwd = _task_cwd(d)
    decks = [str(deck)] if deck else _task_decks(d, cwd)
    if len(decks) == 1:
        (d / "deck.txt").write_text(decks[0], encoding="utf-8")


def _task_decks(directory, cwd):
    """The deck(s) of this SYNC's task: SYNC/deck.txt when Main wrote it; before that, only page registries
    (pages-<deck>.json) written since this SYNC dir was set up — an earlier deck's registry in the same CWD is not this
    task's."""
    d = Path(directory)
    deck = (_read_text(d / "deck.txt").split() or [None])[0]
    if deck:
        return [deck]
    if cwd is None:
        return []
    born = _sync_born(d) - 5
    out = []
    for f in sorted((Path(cwd) / ".lark-slides").glob("pages-*.json")):
        try:
            if f.stat().st_mtime >= born:
                out.append(f.name[6:-5])
        except OSError:
            pass
    return out


def _claim_state(v):
    return v if isinstance(v, dict) else {"who": v, "state": "doing"}


def _done_unwritten(claims, reg):
    """Pages a claim calls done that never reached the deck (e.g. a page done with written=0 left the deck one page short):
    state done, an explicit written=0 and no pages-<deck>.json entry. Only when the registry is in use (reg non-empty:
    bare +add-slide runs register nothing) and only once per page (reopened_unwritten), so it can never loop."""
    if not reg:
        return []
    out = []
    for k, v in claims.items():
        v = _claim_state(v)
        if (re.fullmatch(r"p\d+", k) and v.get("state") == "done" and "written" in v and not v["written"]
                and k not in reg and v.get("via") != "registry" and not v.get("reopened_unwritten")
                and time.time() - float(v.get("since") or v.get("t") or 0) < 1200):   # past next's 20-min hold: leave it
            out.append(int(k[1:]))
    return sorted(out)


def _unwritten_any(claims, reg, want=()):
    """organizer_done guard (a page blocked by the server twice was otherwise frozen after the one-time reopen): every plan page whose
    claim is done with written=0 and that pages-<deck>.json does not list — no reopen-count or age limit."""
    if not reg:
        return []
    keys = [f"p{n:02d}" for n in want] if want else [k for k in claims if re.fullmatch(r"p\d+", k)]
    out = []
    for k in keys:
        v = _claim_state(claims.get(k) or {"who": "", "state": "todo"})
        if (v.get("state") == "done" and "written" in v and not v["written"] and k not in reg
                and v.get("via") != "registry"):
            out.append(int(k[1:]))
    return sorted(out)


def _reset_page_ledger(directory, pages, kinds=("blocked", "srvblk", "held")):
    """A page handed to a writer again (reopen of an unwritten / server-stopped page, takeover, redo) gets a fresh
    server-block budget: its keys leave blocked-/srvblk-/held-<deck>.json and the seal is rewritten. Without this a page
    hard-stopped at MAX_BLOCKS was reopened into a publish gate that refused it at once — nobody could write it."""
    cwd = _task_cwd(directory)
    if cwd is None or not pages:
        return
    pub = _pub()
    lsd = Path(cwd) / ".lark-slides"
    keys = {f"p{int(n):02d}" for n in pages}
    with pub._SealLock(cwd):
        for deck in _task_decks(directory, cwd):
            for kind in kinds:
                f = lsd / f"{kind}-{deck}.json"
                d = _read(f) if f.exists() else {}
                gone = [k for k in d if str(k).split(":")[0] in keys]
                for k in gone:
                    d.pop(k)
                if gone:
                    _write(f, d)
        pub.reseal_blocked(cwd)


def _reopen_owner(directory, c, n):
    """Who rewrites a reopened unwritten page: its owner while still working; an owner that already returned hands it to
    the Organizer (then Main) — never to an agent that is gone, so the page always has exactly one live writer."""
    gone = _read(Path(directory) / RETURNED_FILE)
    owner = c.get("who") or c.get("built_by") or "main"
    if n in _main_pages(directory):
        return owner if owner in ("main", "lead") else "main"
    if owner in gone:
        owner = "organizer" if "organizer" not in gone and owner != "organizer" else "main"
    return owner


def _reopen_unwritten(directory, n):
    """Hand an unwritten 'done' page back to a live owner (state doing, fresh since, fresh block budget) so its next
    resumes it; returns owner."""
    import fcntl
    directory = Path(directory)
    _reset_page_ledger(directory, [n])
    with open(directory / "claims.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        claims = {k: _claim_state(v) for k, v in _read(directory / "claims.json").items()}
        c = claims.get(f"p{n:02d}") or {}
        owner = _reopen_owner(directory, c, n)
        c.update(who=owner, state="doing", t=time.time(), since=time.time(), written=0,
                 held=["claims 标了 done 但这页没写进 deck（written=0，pages-*.json 未登记）"])
        claims[f"p{n:02d}"] = c
        _write(directory / "claims.json", claims)
    return owner


def _verdict_pending(claims):
    """Pages without a final verdict: waiting for review ("built"), under review ("reviewing"), or reopened with
    verdict --redo and not yet rewritten. organizer_done / auto-freeze waits until this is empty."""
    out = []
    for k, v in claims.items():
        if not re.fullmatch(r"p\d+", k):
            continue
        v = _claim_state(v)
        if v.get("state") in ("built", "reviewing") or (v.get("redo") and v.get("state") == "doing"):
            out.append(int(k[1:]))
    return sorted(out)


REVIEW_RESCUE = 180   # s a written page may wait on review alone (queued or under review) once nothing else is open


def _rescue_reviews(claims, now=None):
    """Pages already in the deck that only wait on review pass as written (review="rescued") once review is the tail:
    each queued ("built") or under review ("reviewing") for more than REVIEW_RESCUE, and every other page done — a
    reviewer whose tool timed out / is stuck in a screenshot must not hold finish. Redo rewrites are never rescued.
    Returns the rescued page numbers."""
    now = now or time.time()
    pages = {k: v for k, v in claims.items() if re.fullmatch(r"p\d+", k) and isinstance(v, dict)}

    def stuck(v):
        if v.get("redo") or v.get("state") not in ("built", "reviewing"):
            return False
        since = v.get("rev_since", v.get("t", now)) if v.get("state") == "reviewing" else v.get("t", now)
        return now - since > REVIEW_RESCUE
    cand = {k for k, v in pages.items() if stuck(v)}
    if not cand or not all(v.get("state") == "done" or k in cand for k, v in pages.items()):
        return []   # pages are still being built: the review queue is not the tail yet
    for k in cand:
        pages[k].update(state="done", review="rescued", t=now)
    return sorted(int(k[1:]) for k in cand)


def _first_mtime(directory):
    """When plan_ready was first announced (status.json plan_ready_at, set once by set_status)."""
    t = _read(Path(directory) / "status.json").get("plan_ready_at")
    if t:
        return float(t)
    plan = Path(directory) / "plan.py"
    return plan.stat().st_mtime if plan.exists() else time.time()


_SIDE_TEXT = r"右侧要点|要点栏|关键要点|左图右|左表右|side points|right[- ]side|points on the right|key[_ ]takeaways"


def _wants_takeaways(row):
    """side="takeaways", or a body asking for a right-hand text column without naming a points() style."""
    side = str(row.get("side") or "").strip().lower()
    if side == "takeaways":
        return True
    return not side and bool(re.search(_SIDE_TEXT, str(row.get("body", "")), re.I))


def _page_brief(directory, n):
    """The PAGES row of page n from <D>/plan.py plus the exhibit recipe code for its recipe (best effort)."""
    import contextlib
    import io
    import runpy
    out = {}
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            sys.path[:0] = [str(directory)]
            g = runpy.run_path(str(directory / "plan.py"), run_name="plan_brief")
        row = next((r for r in g.get("PAGES", []) if int(r.get("p", -1)) == n), None)
    except Exception as e:  # noqa: BLE001
        return {"plan_row_error": f"{type(e).__name__}: {e}"[:200]}
    finally:
        if sys.path and sys.path[0] == str(directory):
            sys.path.pop(0)
    if not row:
        return out
    out["plan_row"] = {k: v for k, v in row.items() if isinstance(v, (str, int, float, list))}
    rk = _rel_key(row.get("rel"))
    if rk:   # how the page's charts connect, spelled out for the builder
        out["relation"] = (f"多图关系 = {CHART_RELATIONS[rk][0]}：{CHART_RELATIONS[rk][1]}。每张图上方一句判断句小标题"
                           "（ex.panel(box, claim=…, unit=…) / chart 块 claim= / panel_heads），几句连起来复述页标题")
    elif _row_load(row)[2] >= 2:
        out["relation"] = "plan 没写多图关系：只画一张大图（第二个指标放轴下数据行 rows= 或右栏），不并排两张无关的图"
    over = _over_capacity(row)
    if over:   # the plan was not split: build to one page's capacity at once instead of trial-and-error fitting
        out["capacity_note"] = (f"这页 plan 要 {over}，超出一页容量：直接按容量做——表取 Top 8 + 其他（或只留支撑标题的行），"
                                "图最多 2 张；放不下的部分写一行到 SYNC/gaps.md（页号 + 拆出去的内容），由 Organizer 拆 b 页，"
                                "不要逐像素调高度反复重跑")
    dep = [d for d in (row.get("deps") or []) if _is_researcher(d)]
    if dep:   # numbers come from the direction's small data file; its long report is for its own researcher only
        out["data"] = (f"数字从 research/{dep[0]}.py 取（from research.{dep[0]} import *，或 plan.py 已转接的变量）；"
                       f"不读 research/*.md 调研报告。画 body 点名的完整序列（全部年份 / 全部对象 / 分项），"
                       f"不要只挑 2–3 个点；同一页可用的相关变量见 data_vars，数据多就用多图或分项堆叠把它们画出来")
        inv = {}
        for d_ in dep:
            inv.update(_data_vars(directory / "research" / f"{d_}.py"))
        if inv:
            out["data_vars"] = inv
    if dep and (directory / "research_build").exists() and not (directory / "research" / f"{dep[0]}.go").exists() \
            and not (directory / "plan_final").exists():
        out["plan_row_note"] = ("这一方向的 plan 行还没被 Organizer 定稿，由你按数据定：用 data_vars 里的完整序列画 recipe 的图，"
                                "标题保留数字（f-string 从变量拼），判断按数据改；不删数字过关")
    visual_plan = "; ".join(str(row.get(key) or "") for key in ("recipe", "layout_recipe", "body"))
    cutaway_rejected = re.search(
        r"(?:不(?:使?用|选(?:用)?|适合)|无需)\s*(?:\bcutaway\b|工程剖面)"
        r"|\b(?:without|do(?:\s+not|n't)\s+use)\s+(?:a\s+)?cutaway\b"
        r"|\bno\s+cutaway\b(?=\s*(?:is\s+(?:appropriate|suitable)\b|[,.;]|$))"
        r"|\bcutaway\b\s+(?:is\s+)?not\s+(?:appropriate|suitable)\b", visual_plan, re.I,
    )
    if re.search(r"\bcutaway\b|工程剖面", visual_plan, re.I) and not cutaway_rejected:
        image_note = (
            "工程图按 body 的画法与配色执行，生图 prompt 写本页深色描边/强调色的具体色值；"
            "缺省用 cutaway 工程剖面线稿（三分之四视角、白底、外粗内细、浅灰排线、焦点少量强调色、图内无文字/logo）。"
            "先用生图工具生成 → 按成图尺寸记录原图 ratio（宽/高） → +media-upload 取得 file_token → 按计划用 image 模块组页，"
            "图外部件细引线与 caption“工程剖面示意图”（或“示意图，非精确比例/非官方图纸”）随图；按公开资料通用、已知的构造层级画，"
            "不要求官方逐部件原文，只有具体参数数值要来源。没有现成图片/token 是待完成的素材任务，不改用 steps/takeaways。"
            "实际生图/上传失败才把页号、工具与错误写 SYNC/gaps.md 并回报 Organizer，由它决定重试或改计划；不提交替代文字页。"
        )
        out["plan_row_note"] = " ".join(filter(None, (out.get("plan_row_note"), image_note)))
    recipe = str(row.get("recipe", "")).split("/")[0].strip()
    recipe = {"评分矩阵": "scorecard", "选项对比": "scorecard", "风险象限": "risk_register", "风险清单": "risk_register", "风险登记": "risk_register", "路线图": "roadmap",
              "附录": "appendix"}.get(recipe, recipe)
    if re.fullmatch(r"(?i)swot(?:[ _]?(?:matrix|四象限|矩阵|分析))?|SWOT\s*四象限|四象限\s*SWOT", recipe):
        recipe = "swot_matrix"   # SWOT / 2×2 text frameworks: never four bare points() blocks
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from scripts.svg_lib.exhibit._help import RECIPES, exhibit_help
        from scripts.svg_lib.exhibit._layout_help import PAGE_LAYOUTS
        if recipe in RECIPES:
            out["recipe_code"] = exhibit_help(recipe)
            out["signatures"] = _signatures(RECIPES[recipe][1])
            from scripts.svg_lib.exhibit._help import annotation_hints
            out["annotations"] = annotation_hints(out["signatures"])   # title says X → pass Y, per function
        elif recipe in PAGE_LAYOUTS:
            out["recipe_code"] = exhibit_help(recipe)
            out["signatures"] = _signatures(PAGE_LAYOUTS[recipe][1])
        layout_recipe = row.get("layout_recipe")
        wants = _wants_takeaways(row)
        if layout_recipe not in PAGE_LAYOUTS and recipe not in PAGE_LAYOUTS and wants:
            layout_recipe = "key_takeaways"   # left chart + right text defaults to the takeaways rail
        if layout_recipe in PAGE_LAYOUTS:
            out["layout_code"] = exhibit_help(layout_recipe)
            out["layout_signatures"] = _signatures(PAGE_LAYOUTS[layout_recipe][1])
    except Exception:  # noqa: BLE001
        pass
    return out


_DV_CACHE = {}


def _research_import_error(directory, who):
    """'' when research/<who>.py runs; else the error line. Checked once per file version (mtime)."""
    import subprocess
    directory = Path(directory).resolve()   # a relative --dir resolved again under cwd=directory found no file
    f = directory / "research" / f"{who}.py"
    if not f.exists():
        return ""
    key = (str(f), f.stat().st_mtime)
    if key not in _RI_CACHE:
        try:
            r = subprocess.run([sys.executable, str(f)], cwd=str(directory), capture_output=True, text=True, timeout=30,
                               env={**os.environ, "PYTHONPATH": os.pathsep.join([str(directory), str(Path(directory) / "research"), str(Path(__file__).resolve().parents[1]),
                                                                                 os.environ.get("PYTHONPATH", "")])})
            err = (r.stderr or "").strip().splitlines()
            last = err[-1] if err else ""
            # only an error raised by the file's own code counts; anything about running it (path, interpreter) does not
            real = r.returncode and re.match(r"\w*(?:Error|Exception)\b", last) and "can't open file" not in (r.stderr or "")
            _RI_CACHE[key] = last[:200] if real else ""
        except Exception:  # noqa: BLE001 — a timeout / missing interpreter is not the file's fault
            _RI_CACHE[key] = ""
    return _RI_CACHE[key]


_RI_CACHE = {}


def _data_vars(path, limit=1500):
    try:
        key = (str(path), Path(path).stat().st_mtime)
    except OSError:
        return {}
    if key not in _DV_CACHE:
        _DV_CACHE[key] = _data_vars_(path, limit)
    return _DV_CACHE[key]


def _data_vars_(path, limit=1500):
    """{name: 'list[8] 2018..2025' / 'dict{6}: a, b, …'} of the data a research file defines — so a page uses the full
    series, not the 3 numbers its plan row happened to mention."""
    import contextlib
    import io
    import runpy
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            g = runpy.run_path(str(path), run_name="data_vars")
    except BaseException:  # noqa: BLE001  (a research file calling sys.exit must not take next down)
        return {}
    out, size = {}, 0
    for k, v in g.items():
        if k.startswith("_") or k.isupper() and k in ("SRC",) or not isinstance(v, (list, tuple, dict)) or len(v) < 2:
            continue
        if isinstance(v, dict):
            keys = list(v)[:6]
            d = f"dict{{{len(v)}}}: " + ", ".join(str(x) for x in keys) + ("…" if len(v) > 6 else "")
        else:
            d = f"list[{len(v)}]: " + ", ".join(str(x)[:18] for x in list(v)[:3]) + ("…" if len(v) > 3 else "")
        d = d[:110]
        if size + len(d) > limit:
            break
        out[k] = d
        size += len(d) + len(k)
    return out


def _signatures(code):
    """Signatures of the exhibit functions a recipe calls, so a builder never greps svg_lib for parameter names."""
    import inspect
    import re as _re
    from scripts.svg_lib import exhibit as _ex
    out = {}
    for name in dict.fromkeys(_re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\(", code)):
        fn = getattr(_ex, name, None)
        if callable(fn) and name not in ("Exhibit",):
            try:
                sig = _re.sub(r"<function <lambda> at 0x[0-9a-f]+>", "fmt", str(inspect.signature(fn)))
                out[name] = f"{name}{sig}"[:420]
            except (TypeError, ValueError):
                pass
    return out


_TEXT_RECIPES = ("chapter_nav", "文字", "建议", "下一步", "行动", "结论", "关键数字", "要点", "过渡", "目录", "封面",
                 "摘要", "exec_summary", "review_summary", "text", "next steps", "recommend", "案例", "经验", "决议",
                 "提请", "highlights", "lessons", "asks", "case", "swot")   # roadmap/timeline/scorecard are charts


TEXT_SHARE, HARD_SHARE, OWN_SHARE = 0.10, 0.10, 0.15
REVIEW_MAX = 180   # s without a heartbeat before a review is closed as is (frame() / publish attempts renew it)
REVIEW_CAP = 480   # s a review may run in total, heartbeats or not
ORG_QUEUE_GRACE = 60   # s a flagged page waits for the Organizer's review before Main may take it
STUCK_HELP = 360   # s a builder page may stay claimed-but-unwritten before idle Main / Organizer take that builder's next page
TAIL_STALE = 180   # s: the last open builder page with no heartbeat goes to the idle reviewer (nothing else to do)
ORG_STALE = 300   # s without any Organizer heartbeat (it runs a script every 1–2 min while working): Main takes its pages
BUILDER_STALE = 540   # s without a heartbeat (t: refreshed by next, frame() and every publish attempt, refused ones too)
#                       before a builder's page is handed to someone else
SUMMARY_SETTLE = 180   # s after the last research .done (all directions in) before the exec summary goes out anyway
SUMMARY_SHARE = 0.7    # ... or once this share of the content pages after it is written
_HEAVY_RECIPES = ("heat_matrix", "bubble", "scatter", "sankey", "mekko", "bridge", "waterfall", "small_multiples",
                  "panel_pair", "mixed_columns_page", "kpi_charts_page", "four_columns", "columns_page", "diagram_page",
                  "layered_area", "pie_of_pie", "ridgeline", "football", "sensitivity", "scorecard", "score_options",
                  "treemap", "bump")
#                       recipes Main never builds itself (it closes the deck: P1–P3, reviews, finish)


def _classify(directory, main_pages=()):
    """(text_pages, hard_pages) that Main / Organizer build themselves instead of the builders.

    text = PAGES row chart=False or a text-type recipe (free-form layouts a small model tends to rework); hard = row
    hard=True (multi-chart linkage, cross-chapter sizing, option trade-off). Capped as shares of the content pages —
    text ≤ 20 %, hard ≤ 15 %, both together ≤ 25 % (at least 1 each) — so the big models never become the tail; pages
    beyond the caps (latest page numbers first) stay with the builders."""
    import contextlib
    import io
    import math
    import runpy
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            sys.path[:0] = [str(directory)]
            g = runpy.run_path(str(Path(directory) / "plan.py"), run_name="plan_text")
    except Exception:  # noqa: BLE001
        return set(), set()
    finally:
        if sys.path and sys.path[0] == str(directory):
            sys.path.pop(0)
    text, hard, content, navs = [], [], 0, []
    for r in g.get("PAGES", []) or []:
        try:
            p = int(r["p"])
        except Exception:  # noqa: BLE001
            continue
        if p in main_pages:
            continue
        rec = str(r.get("recipe", "")).lower()
        if rec.split("/")[0].strip() == "chapter_nav":   # chapter navigation pages: always Main / Organizer, outside the caps
            navs.append(p)
            continue
        content += 1
        if r.get("chart") is False or any(k in rec for k in _TEXT_RECIPES):
            text.append(p)
        elif r.get("hard"):
            hard.append(p)
    cap = lambda share: max(1, math.ceil(share * content)) if content else 0
    text = sorted(text)[:cap(TEXT_SHARE)]
    hard = sorted(hard)[:max(0, min(cap(HARD_SHARE), cap(OWN_SHARE) - len(text)))]
    return set(text) | set(navs), set(hard)


def _text_pages(directory):
    return _classify(directory)[0]


_WEAK = ("图上无标注", "图上没有论证标注", "下方留白", "写入警告", "要点栏的数字", "脚注+来源", "标题数字不在图上",
         "要点标记色不在图上")   # already held once at write time: a second look rarely changes the page


def _flags(claim):
    """Risk signals worth a reviewer's look: weak style nudges (no annotation, some white space, footnote lines) alone
    do not send a page to review — they fire on most pages and the precheck already printed them to the author."""
    return [f for f in (claim.get("flags") or []) if f and not str(f).startswith(_WEAK)]


def _is_builder(who):   # builder1–5, or a research+build agent R1–R5 (researches its direction, then builds its pages)
    return str(who).startswith("builder") or _is_researcher(who)


def _is_researcher(who):
    return bool(re.fullmatch(r"R\d", str(who), re.I))


def _n_research(directory):
    """How many researchers this deck has: the R-directions named in deps.json / plan.py deps (2–5; 3 if unknown)."""
    names = set()
    for v in _read(directory / "deps.json").values():
        names |= {x for x in (v if isinstance(v, list) else [v]) if _is_researcher(x)}
    plan = _read_text(directory / "plan.py")
    for m in re.finditer(r"deps\s*=\s*\[([^\]]*)\]", plan):
        names |= set(re.findall(r"R\d", m.group(1), re.I))
    rdir = directory / "research"
    if rdir.exists():
        names |= {p.stem for p in rdir.glob("*.done") if _is_researcher(p.stem)}
    return len(names) if names else 3


def _plan_deps(directory):
    """{page: deps} straight from the PAGES rows of plan.py (AST, no import): deps.json may be written late."""
    return {p: [str(d) for d in r["deps"] if d] for p, r in _plan_literal_rows(directory).items()
            if isinstance(r.get("deps"), list)}


def _plan_literal_rows(directory):
    """{page: literal row fields} of plan.py PAGES by AST (no import; f-string fields are None)."""
    import ast
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    try:
        from scripts.svg_lib.exhibit._frame import _literal_row
        tree = ast.parse(_read_text(Path(directory) / "plan.py"))
    except Exception:  # noqa: BLE001
        return {}
    finally:
        sys.path.pop(0)
    out = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "PAGES" for t in node.targets) \
                and isinstance(node.value, (ast.List, ast.Tuple)):
            for el in node.value.elts:
                row = _literal_row(el) or {}
                if isinstance(row.get("p"), int):
                    out[row["p"]] = row
    return out


def _heavy_pages(directory):
    """Pages whose plan recipe / layout is a complex chart (_HEAVY_RECIPES): never built by Main."""
    out = set()
    for p, r in _plan_literal_rows(directory).items():
        rec = f"{r.get('recipe') or ''} {r.get('layout_recipe') or ''}".lower()
        if any(k in rec for k in _HEAVY_RECIPES):
            out.add(p)
    return out


def _release_gate(directory):
    """True once pages gated on research may go out anyway (plan_final, or 10 min after plan v1, or 5 min after the
    last research .done)."""
    if (directory / "research" / "plan_final").exists() and not (directory / "plan_final").exists():
        (directory / "plan_final").touch()   # written one level too deep
    final = (directory / "plan_final").exists()
    plan = directory / "plan.py"
    overdue = (not final and plan.exists() and time.time() - _first_mtime(directory) > 600)
    research = sorted((directory / "research").glob("*.done")) if (directory / "research").exists() else []
    if not final and len(research) >= _n_research(directory) and time.time() - max(f.stat().st_mtime for f in research) > 300:
        overdue = True
    return final or overdue, overdue


_REVIEW = ("先看送审原因对应的问题，再扫一遍清单（1–2 分钟）：① 标题是观点（所以呢）而不是事实罗列，数字与 plan.py 一致；② 标题里的比较/数字"
           "在图上有标注（cagr=/diff=/badge/band…）；③ 多图读成一张图（expand_* 展开 / 共用时间轴 / 共用对象行 / 面板结论），不是并排摆放；④ 表格文字左、数字右；"
           "⑤ 无溢出/遮挡/半页空白，正文 ≥16；⑥ 副标题是图表标题、无图页没有副标题。")


def _next_once(directory, who, prefer=None, from_end=False, review=False, agent_id=None):
    """Finish this agent's current page and take exactly one next one, under a lock on <D>/claims.json.

    Builders (who=builder1/2/3) build content pages. A finished page goes to review ("built") only when its publish
    left risk flags (check issues, unrelated panels, title number missing on the chart, CAGR not drawn, publish
    warnings — what remained after publish's precheck held the page once); otherwise it is "done" (review auto). Once no page is unclaimed and
    nobody else is building, still-unreviewed pages pass as they are (review skipped) — no review tail.
    Text-only and hard=True pages (capped shares, see _classify) are built by Main / Organizer via --review.
    Main / organizer: with review=True they take the oldest "built" page to check ("reviewing"); then
    `verdict --page N --ok` / `--fixed` closes it ("done"). Without review they build pages in prefer (Main: 1–3).
    Pages already taken are never handed to a second builder; a builder claim whose heartbeat (t) is older than BUILDER_STALE is handed over (claim age alone never).
    <D>/deps.json {"5": ["R1"], "12": ["ALL"]} gates pages on research (<D>/research/<R>.done; ALL = <D>/plan_final).
    """
    import fcntl

    directory = Path(directory)
    if who in ("main", "lead"):
        _touch_main(directory)
    if _is_researcher(who) and (directory / "research" / f"{who}.done").exists():
        bad = _research_import_error(directory, who)
        if bad:   # a .done file that does not run stops plan.py (it imports it) for every agent: fix it first
            try:
                (directory / "research" / f"{who}.done").unlink()
            except OSError:
                pass
            return {"ok": True, "page": None, "mode": "fix_research", "finished": [], "next": (
                f"research/{who}.py 运行出错：{bad}。plan.py 会 import 它，它跑不通全组都拿不到页——"
                f"现在修好这个文件（python3 research/{who}.py 能跑通），再 touch research/{who}.done，然后运行同一条 next")}
    try:   # plan titles (F numbers) as page 0 of the publish-time cross-page check; rewritten only when plan.py changed
        _sync_plan_facts(directory)
    except Exception:  # noqa: BLE001 — a hint only
        pass
    with open(directory / "claims.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        claims = {k: _claim_state(v) for k, v in _read(directory / "claims.json").items()}
        for v in claims.values():   # a review is a quick look + one small fix: REVIEW_MAX without a heartbeat (t: every
            # frame() / publish attempt of the reviewer renews it) closes it as is; REVIEW_CAP bounds a busy one
            now_ = time.time()
            if v["state"] == "reviewing" and (now_ - v.get("t", now_) > REVIEW_MAX
                                              or now_ - v.get("rev_since", v.get("t", now_)) > REVIEW_CAP):
                v.update(state="done", review="timeout", t=time.time())
        _rescue_reviews(claims)   # written pages held only by a review: pass with the written version
        _rows_now = _plan_literal_rows(directory)
        for k_, v_ in list(claims.items()):   # the plan was renumbered after this page was taken: its slot now holds a
            n_ = int(k_[1:]) if re.fullmatch(r"p\d+", k_) else None   # different page — the unwritten claim is void
            if n_ and v_.get("state") == "doing" and not v_.get("written") and v_.get("recipe") \
                    and str((_rows_now.get(n_) or {}).get("recipe") or "") not in ("", v_["recipe"]):
                del claims[k_]
                st_v = _read(directory / "status.json")
                st_v.setdefault("voided", {}).setdefault(k_, [])
                if v_.get("who") not in st_v["voided"][k_]:
                    st_v["voided"][k_].append(v_.get("who"))
                _write(directory / "status.json", st_v)
        reg = _registered(directory)
        if (directory / "plan_final").exists():   # claims.json lost / rebuilt: a page already in the deck is done,
            for k_ in reg:                         # never handed out again as "builder went quiet"
                if k_ not in claims:
                    claims[k_] = {"who": "main", "state": "done", "t": time.time(), "via": "registry", "written": 1}
        reopened = set(_read(directory / "status.json").get("reopened") or [])
        for n_ in sorted(_main_pages(directory) - reopened):   # a cover / summary written with plain publish_slide(page=N) is in the deck: done
            k_ = f"p{n_:02d}"
            if k_ in reg and claims.get(k_, {}).get("state") != "done" and not claims.get(k_, {}).get("redo"):
                c_ = claims.get(k_) or {"who": who if who in ("main", "lead") else "main", "t": time.time()}
                c_.update(state="done", built_by=c_.get("who"), t=time.time(), via="registry")
                claims[k_] = c_
        for n_ in _done_unwritten(claims, reg):   # "done" but never in the deck: reopen once to a live owner (Main: P1–P3)
            c_ = claims[f"p{n_:02d}"]
            owner = _reopen_owner(directory, c_, n_)
            # fresh server budget (else publish refuses at once); local holds keep counting
            _reset_page_ledger(directory, [n_], kinds=("blocked", "srvblk"))
            c_.update(who=owner or "main", state="doing", t=time.time(), since=time.time(), written=0,
                      reopened_unwritten=1, held=["claims 标了 done 但这页没写进 deck（written=0，pages-*.json 未登记）"])
            st_ = _read(directory / "status.json")
            if n_ in (st_.get("frozen") or []) or n_ in _frozen_lock(directory):   # frozen too early: let it be written
                st_["frozen"] = [p for p in (st_.get("frozen") or []) if p != n_]
                _write(directory / "status.json", st_)
                if (directory / FROZEN_LOCK).exists():
                    _write_frozen_lock(directory, _frozen_lock(directory) - {n_})
        doing = [int(k[1:]) for k, v in claims.items() if v["who"] == who and v["state"] == "doing"]
        unwritten = [n for n in doing if "written" in claims[f"p{n:02d}"] and not claims[f"p{n:02d}"]["written"]
                     and (f"p{n:02d}" not in reg or claims[f"p{n:02d}"].get("redo"))   # a redo page is in the deck already
                     and time.time() - claims[f"p{n:02d}"].get("since", claims[f"p{n:02d}"]["t"]) < 1200]
        finished = [n for n in doing if n not in unwritten]
        if unwritten:   # held by the precheck / blocked by lint: the page is not in the deck yet — not done
            n = unwritten[0]
            c = claims[f"p{n:02d}"]
            c["t"] = time.time()
            _write(directory / "claims.json", claims)
            if c.get("redo"):   # reopened by verdict --redo: rewrite it before anything else
                return {"ok": True, "page": n, "mode": "build", "finished": [], "unwritten": True, "redo": True,
                        "next": (f"第 {n} 页被 verdict --redo 退回：{c.get('redo_note') or '见检查意见'}。只改这一处，"
                                 f"用同一页脚本 publish(page={n}, who=\"{who}\") 重写一次，成功后再运行 next"),
                        **_page_brief(directory, n)}
            return {"ok": True, "page": n, "mode": "build", "finished": [], "unwritten": True,
                    "next": (f"第 {n} 页还没有写进 deck：" + "；".join(c.get("held") or ["上次 publish 未成功"])
                             + "。按这些问题改完，用同一调用重新 publish 这一页，成功后再运行 next"),
                    **_page_brief(directory, n)}
        for n in finished:   # builder pages are reviewed only with risk flags
            c = claims[f"p{n:02d}"]
            if c.pop("redo", None):   # a redo rewrite closes the page: the redo note was the review
                c.update(state="done", built_by=c.get("built_by") or who, t=time.time(), review="redo")
                continue
            if _is_builder(who) and _flags(c):   # publish's precheck already caught the rest before the write
                c.update(state="built", built_by=who, t=time.time(), why=_flags(c))
            else:
                c.update(state="done", built_by=who, t=time.time(), **({"review": "auto"} if _is_builder(who) else {}))
        plan_pages = _plan_pages(directory)
        if plan_pages:   # the cover (and whatever Main wrote before the plan) counts as a plan page too
            plan_pages = sorted(set(plan_pages) | set(range(1, min(plan_pages))))
        pages = plan_pages or _pages(prefer or "")
        frozen_ = set(_read(directory / "status.json").get("frozen") or []) | _frozen_lock(directory)
        pages = [n for n in pages if n not in frozen_]   # after organizer_done nothing is handed out again
        deps = {int(k): v for k, v in _read(directory / "deps.json").items()}
        for n_, d_ in _plan_deps(directory).items():
            deps.setdefault(n_, d_)
        summ = _summary_page(directory)
        if summ and len(_plan_pages(directory)) >= 8:
            deps.setdefault(summ, ["ALL"])   # the summary page needs every number: never before plan_final / release
        for n_ in (set(range(1, summ or 3)) | {_contents_page(directory)}) - {summ}:   # cover and contents never wait on data
            deps.pop(n_, None)
        final, overdue = _release_gate(directory)

        plan_src = _read_text(directory / "plan.py")

        def written(r):   # .done is sometimes touched before Rk.py is complete: wait until the data file is stable
            f_ = directory / "research" / f"{r}.py"
            d_ = directory / "research" / f"{r}.done"
            if not f_.exists() or not d_.exists():
                return True
            return f_.stat().st_mtime <= d_.stat().st_mtime + 1 or time.time() - f_.stat().st_mtime > 20

        def wired(r):   # research is done AND plan.py already pulls its numbers in (else builders render placeholders)
            return (directory / "research" / f"{r}.done").exists() and written(r) and (r in plan_src or overdue)

        def go(r):   # organizer finalised direction r's plan rows (research/<r>.go), or 2.5 min passed since its .done
            if (directory / "research" / f"{r}.go").exists():   # (then Rk tunes its own rows: next says so + data_vars)
                return True
            d_ = directory / "research" / f"{r}.done"
            return d_.exists() and written(r) and time.time() - d_.stat().st_mtime > 90

        if _is_researcher(who) and not (directory / "research_build").exists():
            (directory / "research_build").write_text(who)   # this deck runs research+build agents (go protocol)
        go_protocol = (directory / "research_build").exists() or any((directory / "research").glob("*.go"))

        rs_ = sorted((directory / "research").glob("*.done")) if (directory / "research").exists() else []
        all_go = (len(rs_) >= _n_research(directory) and
                  all((directory / "research" / f"{x.stem}.go").exists() for x in rs_))
        last_go = max([x.stat().st_mtime for x in rs_] + [0])   # research all in (or tuned): numbers settle soon after
        _rd = directory / "research"
        settled_dirs = {x.stem for x in _rd.glob("*.done")} | {x.stem for x in _rd.glob("*.go")} if _rd.exists() else set()
        last_any = max([x.stat().st_mtime for x in (list(_rd.glob("*.done")) + list(_rd.glob("*.go")))] + [0]) \
            if _rd.exists() else 0
        # a direction counts once it has .done or .go (a .go without .done: the Organizer released it by hand)
        hard_final = ((directory / "plan_final").exists() or time.time() - _first_mtime(directory) > 1200
                      or (len(settled_dirs) >= _n_research(directory) and time.time() - last_any > 240))
        # cross-chapter pages (exec summary, bridge, options, roadmap) only on plan_final: their numbers must agree

        _mp = sorted(_main_pages(directory))
        contents_pg = _contents_page(directory)
        settle_pages = (({summ} if summ else set()) | _nav_pages(directory)
                        | ({contents_pg} if contents_pg else set())) - {1}   # summary, contents and chapter navs

        def ready_(n):   # research+build agents: direction pages wait for the organizer's go (plan rows tuned to data)
            # summary, contents and chapter navigation quote the chapters' numbers: after every direction is tuned
            if n in settle_pages and go_protocol and summ:   # (or plan_final / 20 min)
                rest = [q for q in pages if q > summ and q not in settle_pages]
                wrote = [q for q in rest if claims.get(f"p{q:02d}", {}).get("state") in ("done", "built", "reviewing")
                         or (claims.get(f"p{q:02d}", {}).get("state") == "doing" and claims[f"p{q:02d}"].get("written"))]
                rest_done = bool(rest) and len(wrote) == len(rest)   # every content page written (none listed yet ≠ done)
                # research all in and quiet for SUMMARY_SETTLE s, or most content pages already in the deck: the
                # numbers the summary quotes are settled — waiting for every tune / the last page only delayed P3
                settled = len(rs_) >= _n_research(directory) and time.time() - last_go > SUMMARY_SETTLE
                most = bool(rest) and len(wrote) >= SUMMARY_SHARE * len(rest)
                # numbers the summary quotes come from the content pages: wait until most of them are in the deck
                # (or plan_final); "research quiet for 3 min" alone sent P3 out with numbers the pages later changed
                return (rest_done or most or (directory / "plan_final").exists() or all_go
                        or (settled and time.time() - last_go > 2 * SUMMARY_SETTLE)
                        or time.time() - _first_mtime(directory) > 1200)
            return all(((hard_final if go_protocol else final) if r == "ALL" else (go(r) if go_protocol else wired(r)) or final)
                       for r in deps.get(n, []))   # cross-chapter pages need the wired numbers: plan_final, not a timer
        reserved = set(_pages(prefer or "")) if not _is_builder(who) else set()
        main_pages = _main_pages(directory)
        text_pages, hard_pages = _classify(directory, main_pages)   # Main / Organizer build these, not builders
        own = text_pages | hard_pages
        heavy = (_heavy_pages(directory) - main_pages) if who in ("main",) or _is_builder(who) else set()
        main_open = any(claims.get(f"p{n:02d}", {}).get("state") != "done" and f"p{n:02d}" not in reg
                        for n in main_pages if n in pages)   # P1–P3 not all in the deck yet
        waiting = [n for n in pages if f"p{n:02d}" not in claims and not ready_(n)]
        free = [n for n in pages if f"p{n:02d}" not in claims and ready_(n)]
        _navs = _nav_pages(directory)
        batch_set = (_navs | {contents_pg}) - {summ, None}   # contents + chapter navs come with the summary page
        if summ and batch_set and max(main_pages) not in _navs:   # (one publish_contents_and_navs call); once the
            p2_live = f"p{summ:02d}" in claims                      # summary claim exists, a leftover one may go alone
            free = [n for n in free if n not in batch_set or p2_live]
        # cross-chapter pages (deps=ALL) are the critical path once plan_final is in: hand them out first
        all_pri = [n for n in free if deps.get(n) == ["ALL"] and n not in main_pages] \
            if (directory / "plan_final").exists() else []
        free = all_pri + [n for n in free if n not in all_pri]
        pick, mode, stale, tail_pick, help_pick = None, "build", None, False, None
        active = any(f"p{n:02d}" not in claims and n not in main_pages | own for n in pages) or any(
            v["state"] == "doing" and _is_builder(v["who"]) for v in claims.values())   # builders still at work
        org_reviews = who == "organizer" or (who == "main" and any(
            "organizer" in (v.get("who"), v.get("reviewer"), v.get("built_by")) for v in claims.values()))
        org_queue = set()   # flagged pages the Organizer has not judged yet: Main neither skips nor freezes past them
        org_busy = any(v["state"] == "doing" and v["who"] == "organizer" for v in claims.values())
        if review and not active:   # builders are done: no review tail, open flags pass as is
            # (Main never skips pages still in the Organizer's review queue: freezing before its verdicts forced a
            # --fix round and a second export; after 2 × REVIEW_MAX they pass — organizer gone)
            for k, v in claims.items():   # ...except pages whose chart proves nothing — one quick fix is worth it
                if v["state"] == "built" and not any(str(w).startswith(("图上无标注", "图上没有论证标注", "没按方案", "页面半空", "文字框", "文字溢出"))
                                                     for w in (v.get("why") or [])):
                    if org_reviews and time.time() - v.get("t", 0) < 2 * REVIEW_MAX:
                        if time.time() - v.get("t", 0) < ORG_QUEUE_GRACE and not org_busy:
                            org_queue.add(k)
                        continue   # queued > ORG_QUEUE_GRACE (or the Organizer is building): Main may review it
                    v.update(state="done", review="skipped")
        tune = []
        if who in ("organizer", "lead") and go_protocol and not (directory / "plan_final").exists():
            rdir = directory / "research"
            tune = [p_.stem for p_ in sorted(rdir.glob("*.done"), key=lambda q: q.stat().st_mtime)   # first done, first tuned
                    if _is_researcher(p_.stem) and not (rdir / f"{p_.stem}.go").exists()] if rdir.exists() else []
            for r_ in list(tune):   # its pages were already taken (go() released them 90 s after .done): tuning rows
                # nobody reads any more is serial dead time — treat the direction as go; tune only unclaimed pages
                rows_ = [n for n, ds in deps.items() if ds == [r_]]
                if rows_ and all(f"p{n:02d}" in claims for n in rows_):
                    tune.remove(r_)
                    try:
                        (rdir / f"{r_}.go").write_text("auto: pages already taken", encoding="utf-8")
                    except OSError:
                        pass
        if tune:
            pick = None
        elif review:
            todo = sorted(((v.get("t", 0), int(k[1:])) for k, v in claims.items()
                           if v["state"] == "built" and v.get("built_by") != who
                           and not (who == "main" and k in org_queue)))   # the Organizer's queue stays its own
            gone_main = who == "organizer" and main_gone(directory)
            mine_ready = [n for n in free if n in main_pages] if (who in ("main", "lead") or gone_main) else []
            gone_ = _read(directory / RETURNED_FILE)
            org_t = [v.get("t", 0) for v in claims.values() if v.get("who") == "organizer" or v.get("reviewer") == "organizer"]
            if who == "main" and "organizer" not in gone_ and org_t and time.time() - max(org_t) > ORG_STALE:
                gone_ = {**gone_, "organizer": max(org_t)}   # every Organizer claim silent > ORG_STALE: it has left
            # Main closes the deck: no content page while P1–P3 are open; no hard / complex page until the Organizer returned
            main_block = who == "main" and main_open
            main_skip = (hard_pages | heavy) if who == "main" and "organizer" not in gone_ else set()
            # hard pages have exactly one builder: the Organizer (Lead). Main takes them only once the Organizer has
            # returned — never because it is busy (that handed one page to two agents and both versions were built)
            mine_own = (text_pages | (hard_pages if "organizer" in gone_ else set())) if who == "main" else own
            if main_block:
                mine_own = set()
            own_ready = [n for n in free if n in mine_own]   # earliest page first: the deck fills in from the front
            if who in ("organizer", "lead") and go_protocol and all_go and not (directory / "plan_final").exists():
                own_ready = []   # every direction tuned: plan_final first (deps=ALL pages wait on it), own pages after
            if mine_ready:   # Main's own pages (cover / contents / exec summary) come first once their data is in
                pick = mine_ready[0]
            elif own_ready:  # then text / hard pages: a review can be skipped at the end, an unbuilt page cannot
                pick = own_ready[0]
            elif todo:
                pick, mode = todo[0][1], "review"
            else:   # reviewers cannot talk to builders: take over stalled / abandoned work from claims.json alone
                now = time.time()
                old_rev = sorted(int(k[1:]) for k, v in claims.items() if v["state"] == "reviewing"
                                 and v.get("reviewer") != who and now - v.get("t", now) > 480)
                # a page is taken only when its heartbeat (t: every next / frame() / publish attempt) went quiet —
                # never by claim age alone, and never back to the agent it was taken from (no ping-pong)
                # the deck's last open page(s): nobody else has work, so a silent holder is handed over sooner
                open_ = [k for k, v in claims.items() if v["state"] == "doing"]
                tail_only = len(open_) <= 2 and not any(f"p{n:02d}" not in claims for n in pages)
                old_build = sorted(int(k[1:]) for k, v in claims.items() if v["state"] == "doing" and v["who"] != who
                                   and not v.get("written")   # already in the deck: let its owner finish
                                   and int(k[1:]) not in main_pages   # P1–P3 stay with Main (publish only accepts Main)
                                   and who not in (v.get("revoked_all") or [v.get("revoked_from")])
                                   and (int(k[1:]) not in hard_pages or who != "main" or "organizer" in gone_)
                                   and int(k[1:]) not in main_skip
                                   and (_is_builder(v["who"]) or not any(f"p{n:02d}" not in claims for n in pages))
                                   and now - v.get("t", now) > (ORG_STALE if v["who"] == "organizer" and "organizer" in gone_
                                                                else TAIL_STALE if tail_only and _is_builder(v["who"])
                                                                else BUILDER_STALE)) if not main_block else []
                last_b = max([v.get("t", 0) for v in claims.values() if _is_builder(v.get("built_by") or v["who"])]
                             or [_first_mtime(directory)])
                idle = [n for n in free if n not in main_pages and n not in main_skip] \
                    if now - last_b > 600 and not main_block else []
                busy = {v["who"] for v in claims.values() if v["state"] == "doing"} | set(gone_)
                # waiting reviewers build a queued page from the tail (its direction's agent is busy or gone; never a
                # hard / complex page for Main, nothing at all for Main before P1–P3) instead of idling in next
                tail = [n for n in free if n not in main_pages and n not in hard_pages and n not in main_skip
                        and [d for d in deps.get(n, []) if _is_researcher(d)]
                        and all(d in busy for d in deps.get(n, []) if _is_researcher(d))] if not main_block else []
                txt = [n for n in free if n in mine_own]
                # a builder stuck on one page (claimed > STUCK_HELP, nothing written): its b-split page, then its next
                # unstarted page go to the idle reviewer — the stuck page itself stays with its holder (no double work)
                splits = {}
                for r_ in ((_load_plan(directory, "plan_split") or {}).get("PAGES") or []):
                    if isinstance(r_, dict) and str(r_.get("p", "")).isdigit() and str(r_.get("split_of", "")).isdigit():
                        splits[int(r_["p"])] = int(r_["split_of"])
                helps = []
                for k_, v_ in sorted(claims.items()):
                    if not (v_["state"] == "doing" and v_["who"] != who and _is_builder(v_["who"]) and not v_.get("written")
                            and now - v_.get("since", v_.get("t", now)) > STUCK_HELP):
                        continue
                    sp_ = int(k_[1:])
                    for n_ in ([n for n in free if splits.get(n) == sp_]
                               + [n for n in free if deps.get(n) == [v_["who"]]]):
                        if n_ not in main_pages and n_ not in hard_pages and n_ not in main_skip and n_ not in helps \
                                and not main_block:
                            helps.append((n_, sp_, v_["who"]))
                if txt:            # text-only and hard content pages are built by the reviewers themselves
                    pick, stale = txt[0], None
                elif old_rev:      # the other reviewer stalled on a review
                    pick, mode, stale = old_rev[0], "review", claims[f"p{old_rev[0]:02d}"].get("reviewer")
                elif old_build:    # a builder went quiet > BUILDER_STALE
                    pick, stale = old_build[0], claims[f"p{old_build[0]:02d}"]["who"]
                elif helps:        # help the stuck builder: its next page, earliest first
                    pick, help_pick = helps[0][0], helps[0][1:]
                elif tail:
                    pick, tail_pick = tail[-1], True
                elif idle:         # no builder claimed or finished anything for 10 min: treat them as gone
                    pick, stale = idle[0], "Builder"
        else:
            if _is_builder(who):
                free = [n for n in free if n not in main_pages | own]
                waiting = [n for n in waiting if n not in main_pages | own]
            if _is_researcher(who):   # own direction first (its data is already in context), then help elsewhere
                mine_dir = [n for n in free if deps.get(n) == [who]]
                if mine_dir or all_pri:   # a released deps=ALL page first, then its own direction
                    free = [n for n in all_pri if n in free] + mine_dir
                elif any(f"p{n:02d}" not in claims and deps.get(n) == [who] for n in pages):
                    free = []   # own pages still gated (own .done not written yet): keep researching, do not wander
            if who == "main":   # Main closes the deck: hard pages go to the organizer / builders, not to Main
                free = [n for n in free if n not in hard_pages
                        and (n in main_pages or not main_open)   # P1–P3 first, no content page before them
                        and (n not in heavy or "organizer" in _read(directory / RETURNED_FILE))]
                if go_protocol:   # research+build decks: a direction's pages belong to its SubAgent, never to Main
                    free = [n for n in free if not any(_is_researcher(d) for d in deps.get(n, []))]
            mine = [n for n in sorted(reserved) if n in free]
            if mine or _is_builder(who) or not reserved:   # no prefer = take over any free content page
                pick = mine[0] if mine else ((free[-1] if from_end else free[0]) if free else None)
            if pick is None and _is_builder(who):   # nothing left: an unstarted text page, never a hard / complex one (small builders)
                spare = [n for n in pages if f"p{n:02d}" not in claims and ready_(n) and n in text_pages and n not in heavy]
                if spare:
                    pick = spare[0]
            if pick is None and _is_builder(who):
                now = time.time()
                # a stalled builder page goes to an idle builder; a hard / complex page never does (stays for Main / Organizer)
                old = [(int(k[1:]), v) for k, v in claims.items() if v["state"] == "doing" and v["who"] != who
                       and now - v.get("t", now) > BUILDER_STALE and who not in (v.get("revoked_all") or [v.get("revoked_from")])
                       and _is_builder(v["who"]) and int(k[1:]) not in hard_pages | heavy]
                if old:
                    pick, stale = min(old, key=lambda t: t[0])[0], min(old, key=lambda t: t[0])[1]["who"]
        if pick is not None:
            if mode == "review":
                claims[f"p{pick:02d}"].update(state="reviewing", reviewer=who, t=time.time(), rev_since=time.time(),
                                              via="next")   # publish only accepts reviews handed out here
            else:
                prev = claims.get(f"p{pick:02d}") or {}
                claims[f"p{pick:02d}"] = {"who": who, "state": "doing", "t": time.time(), "since": time.time(),
                                          "written": prev.get("written", 0) if prev.get("state") == "doing" else 0}
                _rec = (_plan_literal_rows(directory).get(pick) or {}).get("recipe")
                if _rec:
                    claims[f"p{pick:02d}"]["recipe"] = str(_rec)   # page numbers moved later → recipe differs → reissued
                if prev.get("state") == "doing" and prev.get("who") and prev["who"] != who:   # taken over: tell them
                    claims[f"p{pick:02d}"]["revoked_from"] = prev["who"]
                    claims[f"p{pick:02d}"]["revoked_all"] = sorted(set(prev.get("revoked_all") or []) | {prev["who"]})
                    _reset_page_ledger(directory, [pick])   # the new writer starts with a fresh block budget
            batch_navs = []
            if mode != "review" and who in ("main", "lead", "organizer") and summ and pick == summ:
                # summary, contents and every chapter navigation page come from one call (same SECTIONS / PAGES):
                # claim them together so Main publishes the whole set at once
                for n_ in sorted((_nav_pages(directory) | {contents_pg}) - {summ, None}):
                    if f"p{n_:02d}" not in claims or claims[f"p{n_:02d}"].get("state") not in ("done", "doing"):
                        claims[f"p{n_:02d}"] = {"who": who, "state": "doing", "t": time.time(), "since": time.time(),
                                                "written": 0, "batch": pick}
                        batch_navs.append(n_)
            if agent_id and mode != "review":   # finish names it in still_running so Main can shut the right agent down
                claims[f"p{pick:02d}"]["agent_id"] = str(agent_id)
        for n in finished:
            if agent_id and f"p{n:02d}" in claims:
                claims[f"p{n:02d}"].setdefault("agent_id", str(agent_id))
        _write(directory / "claims.json", claims)
    st = {k: v["state"] for k, v in claims.items()}
    left = [n for n in pages if f"p{n:02d}" not in claims]
    building = {k: v["who"] for k, v in claims.items() if v["state"] == "doing" and v["who"] != who}
    to_review = sorted(k for k, s_ in st.items() if s_ == "built")
    reviewing = {k: v.get("reviewer") for k, v in claims.items() if v["state"] == "reviewing"}
    batch_navs = locals().get("batch_navs") or []
    out = {"ok": pick is not None, "page": pick, "mode": mode, "finished": sorted(finished), "unclaimed_left": left,
           "building": building, "to_review": to_review, "reviewing": reviewing, "waiting_on_research": waiting}
    if who in ("organizer", "lead") and not tune and go_protocol and not (directory / "plan_final").exists() and \
            len(list((directory / "research").glob("*.done"))) >= _n_research(directory):
        out["plan_final_due"] = ("全部方向已定稿：现在就把 options()/目标桥的数字接好、python3 plan.py 跑通、touch plan_final——"
                                 "执行摘要和跨章页都在等它（7 分钟后会按当前 plan.py 自动放行）")
        try:
            mix = [m for m in plan_check(directory) if m.startswith((CAPACITY_MSG, "SECTIONS 与 PAGES", "PAGES 里有章名", "STORY / CHAPTER_DESCS", "同一方案超过", "相邻页同方案", "语言"))]
        except Exception:  # noqa: BLE001
            mix = []
        if mix:
            out["plan_final_due"] += "。touch 前先改这几条（还没领走的页才改）：" + "；".join(mix[:3])
    if tune:
        r = tune[0]
        rows = sorted(n for n, ds in deps.items() if ds == [r] and f"p{n:02d}" not in claims)   # taken pages: as built
        out.update(ok=True, mode="tune", direction=r, pages=rows, next=(
            f"{r} 的数据到了（research/{r}.py；不读 {r}.md，需要结论时 grep -n -A12 '## 结论' research/{r}.md）。"
            f"只定稿这一个方向（其余方向等下一次 next 再做，不攒批）——它的页 {rows} 的 plan 行（Edit，≤2 分钟）：① 数字用 F/{r} 变量，按源表归属/期间/分母定判断；预测与代理指标在可见标题或图中标明；"
            "② 按表达目的定下用图或不用：产品机理/工艺壁垒/技术/商业模式论点用示意线稿（cutaway 剖面、原理示意、产品结构、工艺流程）或架构/流程图解释关键构造/作用路径，再配图表验证商业影响；总量/对标/财务页不用图。示意线稿按公开资料里通用、已知的构造层级画，不要求官方结构逐部件原文，图注写“示意图，非精确比例/非官方图纸”；只有具体技术参数（数值）需要来源，未知局部省略；据此保留或去掉草稿候选（缺官方部件原文不是去掉的理由），定稿不留可选/optional/有图再用。image 模块与图表/表格/解释左右或上下组合，通常全稿 1–2 处、非配额、参数可省；其余按数据关系选 recipe、基础图优先（同方案 ≤2 页且不相邻）；一页 ≤3 块；"
            "③ body 写到参数级：主标注（cagr=(i,j) / diff= / target= / band / callout 锚点）、图文结合方式（callout、big_number、focus 高亮、虚线框、Note 含义列、table_panel）、"
            "工程生图在同一 body 写用途、型号/主要部件、cutaway 画法（三分之四视角、白底、外粗内细、浅灰排线）、"
            "并写明\"图内不出现任何文字/字母/数字/标签\"（步骤名、部件名用页面原生文字放在图外）、"
            "本页深色描边/强调色的具体色值（不只写 palette 名）、位置与组合、随图的部件细引线与“工程剖面示意图”图注、配套证据，未知结构省略；"
            "④ 不可比证据用结构化参数/口径对照表，不强画同轴；短表配解释或并页。"
            f"在 plan.py 里接入 `from research.{r} import *`，`python3 plan.py` 跑通后 touch {directory}/research/{r}.go"
            f"（它方向的页随即发给 {r}），然后运行同一条 next --review"))
        try:
            mix = plan_check(directory)
        except Exception:  # noqa: BLE001
            mix = []
        if mix:
            out["plan_mix"] = mix[:4]
        out["data_vars"] = _data_vars(directory / "research" / f"{r}.py")
        out["next"] += ("。定稿时每页 body 写清用 data_vars 里哪几个变量的完整序列（全部年份/对象/分项）——数据丰富的方向可把两页合成多图，"
                        "不只取 2–3 个点")
    if who in ("organizer", "lead") and not stale:   # research finished: its slots go to extra builders while pages queue up
        rdir = directory / "research"
        n_done = len(list(rdir.glob("*.done"))) if rdir.exists() else 0
        known = {v.get("built_by") or v["who"] for v in claims.values() if _is_builder(v.get("built_by") or v["who"])}
        queued = [n for n in left if n not in main_pages | own]
        n_r = _n_research(directory)
        agents_r = any(_is_researcher(v.get("built_by") or v["who"]) for v in claims.values())
        if agents_r:   # research+build agents: up to 5 − n_r helpers, only once pages queue up after all research is in
            slots = max(0, 5 - n_r)
        else:          # separate researchers: builder1–3 run alongside, freed research slots go to builder4/5
            slots = max(0, n_done - max(0, n_r - 2))
        extra = [b_ for b_ in ("builder4", "builder5") if b_ not in known][:slots]
        if n_done >= n_r and len(queued) >= 4 and extra and not _read(directory / "status.json").get("extra_builders"):
            st_ = _read(directory / "status.json")
            st_["extra_builders"] = extra
            _write(directory / "status.json", st_)
            out["spawn_builders"] = extra
    if who in ("organizer", "lead") and stale:   # organizer owns the builders: restart the stalled / vanished ones
        if stale == "Builder":   # no builder activity for 10 min: all of them are gone
            names = sorted({v.get("built_by") or v["who"] for v in claims.values()
                            if _is_builder(v.get("built_by") or v["who"])}) or ["builder1", "builder2", "builder3"]
            out["restart_builders"] = names
        else:
            out["restart_builders"] = [stale]
    if tune:
        return out
    if pick and mode == "review":
        c = claims[f"p{pick:02d}"]
        p3_open = who in ("main", "lead") and any(f"p{n:02d}" not in claims for n in main_pages)
        sid_ = _slide_ids(directory).get(f"p{pick:02d}")
        look_ = (f"slides +screenshot --presentation <deck> --slide-id {sid_}" if sid_ else
                 f"slides +screenshot --presentation <deck> --slide-number {pick}")
        out["slide_id"] = sid_
        out["next"] = (f"检查第 {pick} 页（{c.get('built_by')} 做的，送审原因：{'、'.join(c.get('why') or ['—'])}）：{look_}"
                       f" 看一眼，必要时读 {c.get('built_by')} 的页面脚本。改文字/数字只改本地 .lark-slides/xml/<deck>/p{pick:02d}.xml"
                       f" 再 republish_xml(路径, <deck>, page={pick}, cwd=CWD)；需要回读服务端 XML 时用 +xml-get --slide-id {sid_ or '<本页 id>'}，"
                       "不要用 --slide-number（并行写入时 deck 里的物理顺序可能和页码对不上，会拿到别的页）。" + _REVIEW +
                       f" 全部满足 → verdict --page {pick} --ok；有问题 → 在你自己的脚本里改这一页（可复制对方函数），"
                       f"只改送审原因对应的那一处（标题、一个标注、挪一个标签、删字），不重建图表、不换数据源，f.publish(..., page={pick}, who=\"{who}\") 写入一次（3 分钟没有动作或累计 8 分钟，这页自动按原版结案、之后的写入会被拒绝；修不好就保留原版），"
                       f"然后 verdict --page {pick} --fixed。每页只检查一次，不复查第二遍。"
                       + ("你的执行摘要还没做：这页只看一眼送审原因，能 1 分钟修好就修，否则直接 --ok，别让它挡住 P3。" if p3_open else "")
                       + ("【跨页数字】先判断：同一口径同一期间 → 以 plan.py F（没有就以先写的页）为准，改这页的数；口径或期别不同 → "
                          "在这页数字旁补期别 / 口径（如“2025 年末”“半年报”“集团 / 分部”）；误报 → 直接 --ok。只改文字：改 publish 打印的 "
                          "XML 文件里那几个数再 republish_xml，不重画图。"
                          if any(str(w).startswith("跨页数字不一致") for w in (c.get("why") or [])) else "")
                       + ("（check 问题 ≥10 个：说明版式整体放不下，不逐个挪标签——删掉一半对象/标签或换成 row_table，一次写入）"
                          if any(re.match(r"check (\d+)", w) and int(re.match(r"check (\d+)", w).group(1)) >= 10
                                 for w in (c.get("why") or [])) else ""))
        out.update(_page_brief(directory, pick))
    elif pick and review:
        if stale:
            out["next"] = ("做第 %d 页（%s 超过 9 分钟没有任何提交，这页转交给你；对方脚本 CWD/build/*_pages.py 里若已有这页就直接复用、"
                           "只修报错）：按下面 plan 行与 recipe 实现，写入即完成、不需要再检查；写入后运行同一条 next --review"
                           % (pick, stale))
        elif help_pick:
            out["next"] = ("做第 %d 页（%s 卡在第 %d 页已超过 %d 分钟未写入，它的下一页先由你做；第 %d 页仍归 %s，不要碰）：按下面 plan 行与 "
                           "recipe_code 实现，f.publish(..., page=%d, who=\"%s\") 写入即完成、不需要再检查；写入后运行同一条 next --review"
                           % (pick, help_pick[1], help_pick[0], STUCK_HELP // 60, help_pick[0], help_pick[1], pick, who))
            out["helping"] = {"stuck_page": help_pick[0], "holder": help_pick[1]}
        elif tail_pick:
            out["next"] = ("做第 %d 页（队尾的图表页：它所属方向的 SubAgent 还在做别的页，你空着就先做它，不要空等）：按下面 plan 行与 "
                           "recipe_code 实现，f.publish(..., page=%d, who=\"%s\") 写入即完成、不需要再检查；写入后运行同一条 next --review"
                           % (pick, pick, who))
        elif pick == 1 and (who in ("main", "lead") or gone_main):
            out["next"] = _cover_next(directory, who)
        elif pick in main_pages and gone_main:
            out["next"] = (("Main 已 %d 分钟没有动作（提前结束了本轮）：第 %d 页由你做——执行摘要 / 目录用 "
                            "publish_contents_and_navs(...)（写法同 business-research-main 第 2 节，who=\"organizer\"，目录与导航页一起写）；"
                            "写入后运行同一条 next --review") % (MAIN_SILENT // 60, pick))
        elif pick in main_pages:
            out["next"] = (("做第 %d 页（你自己的页，数据已齐）：按 business-research-main 第 2 节写（执行摘要 / 目录用 publish_contents_and_navs），"
                            "写入后运行同一条 next --review") % pick)
        elif pick in hard_pages:
            out["next"] = ("做第 %d 页（图表页，由你亲自做，写入即完成、不需要再检查）：按下面 plan_row 与 recipe_code 写 "
                           "CWD/build/p%02d.py，f.publish(..., page=%d, who=\"%s\") 写入；被拦按提示改，同页拦 2 次就删标签或换更简单方案；"
                           "写入后运行同一条 next --review" % (pick, pick, pick, who))
        else:
            out["next"] = ("做第 %d 页（无图表的文字页，由检查人亲自做，写入即完成、不需要再检查）：按下面 plan 行实现——"
                           "结构化成评分矩阵/选项对比/路线图等有视觉锚点的版式（row_table/roadmap/points；KPI 卡只作侧栏，不做整页数字），"
                           "不写满屏段落；写入后运行同一条 next --review" % pick)
        out.update(_page_brief(directory, pick))
        if out.get("layout_code") and pick not in main_pages:   # Main / Organizer on a builder's page: the planned layout
            lay_ = (out.get("plan_row") or {}).get("layout_recipe") or "key_takeaways"
            out["layout_required"] = lay_
            out["next"] += (f"。版式照下面 layout_code（{lay_}）排、图表画进它的 slots——不自己从头拼块，≤3 块；"
                            "放不下就删块或在 gaps.md 记一行拆 b 页")
        out["publish"] = (f'publish_slide(xml, presentation=<deck>, page=1, cwd=<CWD>, who="{who}")'
                          if pick == 1 and (who in ("main", "lead") or gone_main) and not stale else
                          f'f.publish(..., deck=<deck>, page={pick}, cwd=<CWD>, who="{who}")')
    elif pick == 1 and who in ("main", "lead"):
        out["next"] = _cover_next(directory, who, review=False)
        out["publish"] = f'publish_slide(xml, presentation=<deck>, page=1, cwd=<CWD>, who="{who}")'
    elif pick:
        out["next"] = "做第 %d 页：按下面 plan 行与 recipe 代码改数据实现，用 publish 字段的写法写入（带 who），写入后再运行同一条 next 命令" % pick
        if overdue and int(pick) in deps:
            out["next"] += "（调研超时已放行：用 plan.py / research 里已有的数字，缺的写\"未披露\"，不要等）"
        if stale and _is_builder(who):
            out["next"] += "（%s 超过 9 分钟没有任何提交，已转交给你；对方脚本若已有这页可直接复用）" % stale
        elif stale:
            out["next"] += ("（%s 超过 9 分钟没有任何提交，这页转交给你自己做：对方脚本若已有这页可直接复用；你自己做的页"
                            "写入即完成，不需要再检查；做完运行同一条 next --review）" % stale)
        out.update(_page_brief(directory, pick))
        out["publish"] = f'f.publish(..., deck=<deck>, page={pick}, cwd=<CWD>, who="{who}"' + (
            ', layout="<这页版式，≤20 字>", why="<为什么这样排满足本页要求，≤50 字>")' if _is_builder(who) else ")")
        if batch_navs:
            out["batch_pages"] = [pick] + batch_navs
            cp_ = _contents_page(directory)
            cp_ = cp_ if cp_ in batch_navs else None
            nv_ = [n for n in batch_navs if n != cp_]
            out["next"] = (f"做第 {pick} 页（执行摘要）" + (f"、第 {cp_} 页（目录）" if cp_ else "")
                           + (f"和全部章节导航页 P{'、P'.join(map(str, nv_))}" if nv_ else "") + "——一条命令一起写："
                           "from plan import *; from scripts.svg_lib.exhibit import publish_contents_and_navs; "
                           f"r = publish_contents_and_navs(SECTIONS, PAGES, descs=CHAPTER_DESCS, question=<核心问题>, "
                           "answer=<答案一句：评级 + 目标价 / 主建议，≤60 字>, kpis=[(值, 说明)]×2–3, "
                           "points=[(支撑结论, 一句证据)]×3–5（数字从 F 拼）, deck=<deck>, cwd=<CWD>, "
                           f"deck_name=<报告名>, summary_page={pick}, contents_page={cp_}, who=\"{who}\"); "
                           "print({k: v.get('ok') for k, v in r.items()})"
                           "——同一套 SECTIONS / PAGES / CHAPTER_DESCS，版式与页码区间一致；有页没写成就按返回改了只重写那几页"
                           f"（同一调用加 only=[页号]）；全部写成后再运行同一条 next")
            out["publish"] = "publish_contents_and_navs(...)（见 next）"
    elif _is_builder(who):
        if waiting or not (pages or frozen_):
            out["next"] = "剩余页还在等计划或数据：原样再运行同一条 next（它会自己等待）；不要搜索、不要自己编数、不要 return"
            out["ok"] = None
        else:
            out["next"] = "没有可领的页了：立即 return（已写页号），不做全稿回读、截图、导出、复查"
            _mark_returned(directory, who)
    elif not review:
        pend = sorted(n for n in reserved if f"p{n:02d}" not in claims)
        out["next"] = ((f"P{pend} 还在等全部数据（plan_final）：先用 next --review 检查 Builder 的页，几分钟后再用同一条 "
                        f"--prefer 领") if pend else "你的页已做完。之后用 next --review 领 Builder 写完的页逐页检查（每页一次）")
        out["ok"] = None if pend else False
    elif building or left or waiting or reviewing or not (pages or frozen_):
        out["next"] = ("暂时没有待检查的页（Builder 还在做 %s）：%s；期间不截图、不重做"
                       % (", ".join(sorted(building)) or "剩余页", NEXT_RETRY))
        out["ok"] = None
    elif _verdict_pending(claims):   # pages still waiting for the Organizer's verdict (or a redo rewrite): no freeze yet
        out["next"] = (f"第 {_verdict_pending(claims)} 页还在等检查结论（Organizer 的检查队列 / redo 重写）：{NEXT_RETRY}；"
                       "全部有 verdict 后自动标 organizer_done")
        out["ok"] = None
    else:
        if _read(directory / "status.json").get("phase") != "organizer_done":   # freeze the pages
            st_ = set_status(directory, "organizer_done", note=f"{who}: 全部页已完成，自动标记 organizer_done")
            if st_.get("ignored") and st_.get("unwritten"):   # a page never reached the deck: not done yet
                out.update(ok=None, unwritten=st_["unwritten"], next=st_["next"])
                if st_.get("owners"):
                    out["owners"] = st_["owners"]
                return out
        cwd = (directory.parents[3] if len(directory.parents) > 3 and directory.parents[1].name in ("strategy", "review")
               else directory.parent if (directory.parent / ".lark-slides").exists() else None)   # also <cwd>/SYNC
        lead = who == "lead" or (who == "main" and cwd is not None and _no_main(cwd))
        out["next"] = ("全部页已做完：**现在**运行 finish（回读核对 + 导出）→ "
                       + (_LEAD_DELIVER if lead else "present_files 交付 → " + ORG_SHUTDOWN_NOTE) + "。"
                       "标了 skipped 的页是按规则直接通过的，不要再去截图或修改；之前截好的 review 截图也不要再看——"
                       "这一步多花的每分钟都会推迟交付")
        out["finish"] = (f'python3 {Path(__file__).resolve()} finish --dir {directory} --deck <deck> --cwd <CWD> --name "<标题>"'
                         + (" --who lead" if lead else " --who main"))
        org_closes = who == "organizer" and main_gone(directory)
        if org_closes:
            out["finish"] = out["finish"].replace(" --who main", " --who organizer")
        elif who not in ("main", "lead"):   # only Main / Lead finish: an Organizer that exports races Main
            out.pop("finish")
        decks = _task_decks(directory, cwd) if cwd else []   # this task's deck only
        deck = next((d for d in decks if d and len(set(_read(Path(cwd) / ".lark-slides" / f"pages-{d}.json"))
                                                     & {f"p{n:02d}" for n in pages}) >= max(1, len(pages) - 1)), None)
        if deck and who in ("main", "lead") and not _read(directory / "status.json").get("finished_at"):   # one exporter
            try:   # export right away: no window for full-deck screenshot sweeps or "final review" rewrites
                fin = finish(directory, deck, cwd=str(cwd), who="lead" if lead else who)
            except Exception as e:  # noqa: BLE001
                fin = {"ok": False, "next": f"自动导出出错 {type(e).__name__}：运行 finish 字段的命令"}
            out["export"] = fin
            if fin.get("front_stale") or fin.get("logo_missing") or (fin.get("lint_errors") and not fin.get("ok")):
                out["next"] = fin["next"]
            if fin.get("ok") and not lead:
                out["next"] = (f"全部页已做完，已自动导出 PPTX：{fin.get('pptx')}。现在用一次 present_files 同时交付 PPTX 与链接 → "
                               f"运行 dispatch --cwd {cwd} --close → "
                               + (ORG_RETURNED_NOTE if fin.get("organizer_returned") else ORG_SHUTDOWN_NOTE) + "；不截图、不复查、不改任何页、不给 Organizer/Builder 发返工消息（页面已冻结，"
                               "返工会重启调研与建页，交付晚 5–10 分钟；用户之后要改再按页改）")
        if lead and out.get("export", {}).get("ok"):
            out["next"] = (f"全部页已做完，已自动导出 PPTX：{out['export'].get('pptx')}。现在{_LEAD_DELIVER}"
                           "（旧任务返回格式的命令见 lead_return 字段，输出按原派单要求返回）→ send_message shutdown 仍在跑的 "
                           "Builder/调研 SubAgent；不截图、不复查、不改任何页")
            out["lead_return"] = _lead_return_cmd(out["export"].get("pptx"))
            if out["export"].get("final_reply"):
                out["final_reply"] = out["export"]["final_reply"]
                out["final_reply_file"] = out["export"].get("final_reply_file")
                out["next"] += "。" + FINAL_REPLY_NEXT
        if out.get("export", {}).get("still_running"):
            out["still_running"] = out["export"]["still_running"]
            agents = out["export"].get("still_running_agents") or [{"who": w} for w in out["still_running"]]
            out["still_running_agents"] = agents
            out["still_running_cmd"] = out["export"].get("still_running_cmd") or _shutdown_cmd(agents, lead=lead)
            if STILL_RUNNING_MSG not in out["next"]:
                out["next"] = f"{STILL_RUNNING_MSG}：{_running_text(agents)}（照做：{out['still_running_cmd']}）；" + out["next"]
        if org_closes:
            out["next"] = ("全部页已做完，Main 已提前结束本轮：由你收尾——运行 finish 字段的命令导出 PPTX → 用一次 present_files "
                           "同时交付飞书链接与 PPTX → send_message shutdown 仍在跑的子代理 → return（链接、PPTX 路径、一句结论）。"
                           "不截图、不复查、不改页")
        elif who == "organizer":
            _mark_returned(directory, who)
            out["next"] = ("全部页已做完：已写 organizer_done（页面已冻结）。Main 负责 finish 导出与 present_files 交付——你不跑 finish、"
                           "不 present_files；立即 return（数据缺口、修过的页号）；"
                           "不截图、不复查、不手改 claims/status、不绕过 publish 重写任何页")

    return out


def _cover_next(directory, who, review=True):
    """The cover instruction (P1 is always the cover — never the summary text)."""
    doc = "business-research-main"
    return (f"做第 1 页封面（不依赖 plan.py 与调研）：按 {doc} 第 1 节第 3 步与 style「封面」一节做——必须有主视觉图（生图或搜图，"
            "图占画面 ≥1/2），不只放文字或 logo；有品牌时右上角放 logo_xml(cwd=<CWD>, deck=<deck>) 的 <img>（不改宽高）；封面不放业绩数字。"
            f'用 publish_slide(xml, presentation=<deck>, page=1, cwd=<CWD>, who="{who}") 写入，写入后运行同一条 next'
            + (" --review" if review else ""))


EXPORTED_STOP = "已导出交付：立即 return，不再做任何事"
STILL_RUNNING_WINDOW = 600   # s: a builder / researcher whose claim moved this recently may still be running
STILL_RUNNING_MSG = "先 send_message shutdown 这些子代理（名字/agent_id 如下）再交付"
SHUTDOWN_WAIT = ("；send_message shutdown 后 wait_agent(wait_timeout=120) 等它结束，不要 kill_agent"
                 "（Organizer 要先停掉它自己派的子代理；被 kill 的来不及停，子代理会一直跑）")
AGENTS_FILE = "agents.json"   # SYNC/agents.json {who: agent_id} recorded by next --agent-id
RETURNED_FILE = "returned.json"   # SYNC/returned.json {who: t}: next told this agent "立即 return" at t


def _mark_returned(directory, who):
    """next answered `who` with a final "立即 return": remember it, so finish does not ask to shut it down again."""
    path = Path(directory) / RETURNED_FILE
    d = _read(path)
    d[str(who)] = time.time()
    try:
        _write(path, d)
    except OSError:
        pass
    if who not in ("main", "lead"):   # a returning agent never writes again: its unwritten pages go back to next at once
        try:
            import fcntl
            with open(Path(directory) / "claims.lock", "w") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                claims = _read(Path(directory) / "claims.json")
                gone = [k for k, v in claims.items() if isinstance(v, dict) and v.get("who") == who
                        and v.get("state") == "doing" and not v.get("written")]
                for k in gone:
                    del claims[k]
                if gone:
                    _write(Path(directory) / "claims.json", claims)
        except OSError:
            pass


def _organizer_gone(directory, cwd=None):
    """The Organizer is known to have returned: next told it to return (SYNC/returned.json), or (template flow) a
    return-summary.md exists under <cwd>/.lark-slides/**/organizer/ newer than the dispatch."""
    if directory and "organizer" in _read(Path(directory) / RETURNED_FILE):
        return True
    if cwd:
        d = _read(_dispatch_path(cwd))
        return _organizer_returned(Path(cwd).resolve(), float(d.get("t") or 0)) if d else False
    return False


def closing_notice(to, flow="template", minutes=3):
    """notice --to R1: the fixed closing text Main / Lead sends verbatim to a review subagent (hand-written
    forwards lost details such as the "3 分钟" window)."""
    return (f"{to}：收尾：复核一轮，{int(minutes)} 分钟内 return；已发现的问题当场修或写进 return-summary；"
            "return 后不再写任何页")


CLOSING_FILE = "closing.json"   # <cwd>/.lark-slides/closing.json {to: [...], minutes, t}: reviewers read it each poll


def write_closing(cwd, to, minutes=3):
    """notice also drops the closing signal into a file (forwarded notices tend to get rewritten by hand):
    review subagents check it every poll and start their closing window themselves."""
    f = Path(cwd or ".") / ".lark-slides" / CLOSING_FILE
    d = _read(f)
    names = list(dict.fromkeys((d.get("to") or []) + [str(to)]))
    _write(f, {"to": names, "minutes": int(minutes), "t": d.get("t") or time.time()})
    return f


def _shutdown_cmd(agents, lead=False):
    """still_running as one directly executable instruction: Main asks the Organizer (it owns the subagents), a Lead
    shuts them down itself (a bare name list made Main search its trace for ids)."""
    names = "、".join(a["who"] + (f"（{a['agent_id']}）" if a.get("agent_id") else "") for a in agents)
    unknown = [a["who"] for a in agents if not a.get("agent_id")]
    if lead:   # the Lead created them itself: their ids are in its own create_agent results
        return (f"send_message 分别给 {names}：shutdown"
                + (f"（{'、'.join(unknown)} 没登记 agent_id：用你 create_agent 时返回的 id；找不到就跳过——deck 已导出冻结，"
                   "它们再写页会被 publish 拒绝，不影响交付）" if unknown else "") + SHUTDOWN_WAIT)
    return (f"send_message Organizer：请 shutdown {names} 后 return"
            + ("（Organizer 派的子代理 id 只有它知道：只发这一条，不要自己找 id；Organizer 已结束就跳过——deck 已导出冻结，"
               "它们再写页会被 publish 拒绝，不影响交付）" if unknown else
               "（Organizer 已 return 的跳过——deck 已导出冻结，它们再写页会被 publish 拒绝）")) + SHUTDOWN_WAIT


def _cwd_sync_dirs(cwd, deck=None):
    """SYNC dirs in cwd of one deck (deck.txt names it) — the same filter publish uses; without deck every SYNC dir
    that has a deck.txt (reopen / export must then name the deck when there are several)."""
    pub = _pub()
    if hasattr(pub, '_sync_candidates'):
        dirs = pub._sync_candidates(cwd)
    else:
        # main's lightweight publisher has no collaboration state. The export
        # compatibility entry can still read old task directories itself.
        root = Path(cwd)
        dirs = []
        for kind in ('strategy', 'review'):
            dirs.extend(p.parent for p in root.glob(f'.lark-slides/{kind}/**/status.json')
                        if 'turns' not in p.relative_to(root).parts)
        dirs.extend(root / name for name in ('SYNC', 'sync') if (root / name / 'status.json').is_file())
        dirs = list(dict.fromkeys(dirs))
    def bound_deck(directory):
        if hasattr(pub, 'sync_deck'):
            return pub.sync_deck(directory)
        tokens = _read_text(Path(directory) / 'deck.txt').split()
        return tokens[0] if tokens else None
    if deck:
        deck = pub._deck_id(deck)
        return [d for d in dirs if bound_deck(d) == deck]
    return [d for d in dirs if bound_deck(d)]


_LEDGER_GLOBS = ("blocked-*.json", "srvblk-*.json", "held-*.json", "writes-*.json")
_EDIT_NEXT = ("这是 reopen 打开的追问修改轮（phase=edit）：不跑 next / status / verdict，按 slides-editing.md 直接改目标页"
              "（图表页 f.publish(..., page=N, cwd=CWD)），改完运行 multiagent_sync.py export --deck … --cwd … 重新导出并交付")
REOPEN_NEXT = ("现在按 slides-editing.md 回读并修改目标页：图表页用 f.publish(..., page=N, cwd=CWD)，纯 XML 页用 "
               "publish_slide(xml, presentation=…, page=N)；不用 +update-slide / +replace-slide / +add-slide。要新增一页：插在用户说的位置（f.publish(..., page=N, "
               "insert=True)，其后页号与页脚页码自动顺延，不追加到末尾），和正文页一样用 frame + exhibit 库做（情景 / 对比 / 测算用 "
               "row_table 或 text_table 一行一个情景、或柱图 + key_takeaways，不手画并排底色卡片），数字从 SYNC/plan.py 与 research "
               "变量取、与其它页一致；页码变了就把目录页和**每一张**章节导航页都重画（plan.py 的 PAGES/SECTIONS 先把插入页之后的页号 +1、加上新页一行，再运行 publish_contents_and_navs(SECTIONS, PAGES, descs=CHAPTER_DESCS, deck=…, cwd=…)；不要手改其中几张的页码文字，否则各页页码互相对不上）。新增表格页骨架（照抄改字段）： from scripts.svg_lib.exhibit import *; f = frame('观点标题', '指标，单位', source=[SRC[k]], page=N, section='所在章名（插页后页号变了，直接写章名字符串）')； ex = Exhibit(w=body_w(f), h=f.bottom - f.top)；row_table(ex, ex.body, rows=[dict(name=…, v=…), …], columns=[Label('name', header='…'), Text('v', header='…'), Bar('x', header='…')])；side = key_takeaways(f, [(结论, 证据), …], label='…')； f.publish(ex=ex, side=side, deck=DECK, page=N, cwd=CWD, insert=True)。改完运行 multiagent_sync.py export --deck … --cwd … "
               "重新导出并交付")


READBACK_SCAN_DEPTH, READBACK_SCAN_FILES, READBACK_MAX_BYTES = 3, 400, 4 * 1024 * 1024


def _readback_cmd(deck):
    return (f"lark-cli slides +xml-get --presentation {deck} --output ./edit-vNN/source.xml --json "
            f"> ./edit-vNN/source-response.json")


def _last_export_t(dirs):
    """When this deck was last exported / frozen (mtime of SYNC/exported / frozen.lock, status finished_at): a readback
    taken before it shows the previous turn's deck, not the one the user is asking about now."""
    t = 0.0
    for d in dirs:
        for name in ("exported", FROZEN_LOCK):
            try:
                t = max(t, (d / name).stat().st_mtime)
            except OSError:
                pass
        try:
            t = max(t, float(_read(d / "status.json").get("finished_at") or 0))
        except (TypeError, ValueError):
            pass
    return t


def _mentions_deck(path, deck, need_key=False):
    """The file names this deck: "xml_presentation_id": "<deck>" (an +xml-get response), or — need_key False — the
    deck id anywhere (an XML readback that carries it). Reads at most READBACK_MAX_BYTES."""
    try:
        with open(path, "rb") as fh:
            text = fh.read(READBACK_MAX_BYTES).decode("utf-8", "replace")
    except OSError:
        return False
    if re.search(r'"xml_presentation_id"\s*:\s*"' + re.escape(str(deck)) + '"', text):
        return '"content_saved"' in text or '"scope"' in text   # an +xml-get response, not +create / screenshot
    return (not need_key and "<presentation" in text
            and bool(re.search(r"[\"'/=]" + re.escape(str(deck)) + r"[\"'/?&<\s]", text)))


def _fresh_readback(root, deck, since, given=None):
    """(path, None) of a readback of `deck` written after `since`, or (None, why). given: --readback <file> (the
    +xml-get XML or its --json response); an XML output that carries no id is accepted when a response JSON next to it
    is fresh and names the deck. Without given: a cheap scan of the CWD tree (depth ≤ READBACK_SCAN_DEPTH, skipping
    .lark-slides / hidden dirs, newest files first) for a fresh *.json / *.xml naming the deck."""
    if given:
        p = Path(given)
        if not p.is_absolute():
            p = root / p
        if not p.is_file():
            return None, f"--readback {given} 不存在"
        if p.stat().st_mtime < since:
            return None, f"--readback {given} 早于这份 deck 上次导出（是上一轮的回读），要本轮重新 +xml-get"
        if _mentions_deck(p, deck):
            return p, None
        sib = [q for q in p.parent.glob("*.json") if q.stat().st_mtime >= since and _mentions_deck(q, deck, need_key=True)]
        if sib:
            return p, None
        return None, f"--readback {given} 里没有这份 deck 的 presentation id（{deck}）：回读的是另一份 deck？"
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        rel = Path(dirpath).relative_to(root)
        dirnames[:] = [n for n in dirnames if not n.startswith(".") and n not in ("node_modules", "__pycache__", "turns")]
        if len(rel.parts) >= READBACK_SCAN_DEPTH:
            dirnames[:] = []
        for n in filenames:
            if n.endswith((".json", ".xml")):
                found.append(Path(dirpath) / n)
        if len(found) > READBACK_SCAN_FILES * 4:
            break
    fresh = []
    for p in found:
        try:
            st = p.stat()
        except OSError:
            continue
        if st.st_mtime >= since and st.st_size <= READBACK_MAX_BYTES * 4:
            fresh.append((st.st_mtime, p))
    for _, p in sorted(fresh, reverse=True)[:READBACK_SCAN_FILES]:
        if _mentions_deck(p, deck, need_key=p.suffix == ".json"):
            return p, None
    return None, "本轮还没有回读这份 deck"


def _delivered_decks(root):
    """{deck: {"title", "url"}} of every deck delivered from this CWD (.lark-slides/decks/<deck>/FINAL_REPLY.md or
    url.txt, and multi-agent SYNC dirs with an exported marker)."""
    out = {}
    base = Path(root) / ".lark-slides" / "decks"
    for d in sorted(base.glob("*")) if base.is_dir() else []:
        fr = _read_text(d / FINAL_REPLY_FILE)
        if not fr and not (d / URL_FILE).exists():
            continue
        m = re.search(r"已完成：(.+?)，共", fr)
        out[d.name] = {"title": m.group(1).strip() if m else "", "url": _read_text(d / URL_FILE).strip()}
    for d in _cwd_sync_dirs(root):
        k = _pub().sync_deck(d)
        if k and k not in out and ((d / "exported").exists() or _read(d / "status.json").get("finished_at")
                                   or (d / "turns").is_dir()):
            out[k] = {"title": "", "url": ""}
    return out


def reopen(cwd, why, deck=None, readback=None):
    """reopen --cwd CWD --why "<用户追问摘要>" [--readback <+xml-get output>]: open a follow-up edit turn on a delivered
    multi-agent deck. Refused until this deck was read back in this turn (a fresh +xml-get output / response naming it,
    passed as --readback or found in the CWD tree): the agent must first check the target page against the request
    (already satisfied → just answer the user, no reopen). For every
    SYNC dir: exported / frozen.lock (and a status / claims snapshot) move to SYNC/turns/<n>/, status.json gets
    phase "edit", turn n+1 (frozen, finished_at, fix_round cleared), every claim is closed as done (next hands nothing
    out). The deck's server-block counters, write counts and one-shot hold ledgers move to the archive too, an open
    dispatch.json is closed, and .seal is rewritten so publish accepts writes again. Idempotent within a turn."""
    if not why or not str(why).strip():
        return {"ok": False, "next": "reopen 需要 --why \"<用户追问摘要>\"（例如'把第 4 页的图表换成柱状图'）"}
    root = Path(cwd).resolve()
    dirs = _cwd_sync_dirs(root, deck)
    if not dirs:
        return {"ok": False, "next": (f"{root}/.lark-slides/ 下没有 deck {deck} 的 SYNC 目录" if deck else
                                      f"{root}/.lark-slides/ 下没有 strategy/ 或 review/ 的 SYNC 目录")
                + "：这不是多 agent deck，不需要 reopen，直接按 slides-editing.md 改页"}
    decks = sorted({_pub().sync_deck(d) for d in dirs})
    if len(decks) > 1:
        return {"ok": False, "decks": decks,
                "next": f"这个目录里有 {len(decks)} 份多 agent deck（{', '.join(decks)}）：带 --deck <要改的那份 ID> 重跑 reopen"}
    deck = decks[0]
    lsd = root / ".lark-slides"
    url = _deck_url(dirs[0], root, deck)   # persist the link (decks/<deck>/url.txt) for this turn's export
    turns = [int(_read(d / "status.json").get("turn") or 1) for d in dirs]
    closed = [d for d in dirs if (d / "exported").exists() or (d / FROZEN_LOCK).exists()
              or _read(d / "status.json").get("finished_at") or _read(d / "status.json").get("frozen")]
    if not closed:   # already reopened in this turn (nothing exported / frozen since): no-op
        return {"ok": True, "turn": max(turns), "already_open": True, "next": REOPEN_NEXT}
    rb, miss = _fresh_readback(root, deck, _last_export_t(dirs), readback)
    if rb is None:
        return {"ok": False, "deck": deck, "readback_missing": True,
                "next": (f"未 reopen：{miss}。先回读：{_readback_cmd(deck)}（edit-vNN 换成本轮编号），"
                         "用 xml_inspect.py --mode summary 核对标题就是用户说的那份、再看目标页现状与用户要求逐条对比——"
                         "已经满足（如要求换成柱状图而那页已是柱状图）就直接回复用户现状并问要改什么，不 reopen、不改页；"
                         f"确需修改再带 --readback ./edit-vNN/source-response.json 重跑 reopen")}
    old = max(turns)
    new = old + 1
    import fcntl
    import shutil
    for d in dirs:
        arc = d / "turns" / str(old)
        arc.mkdir(parents=True, exist_ok=True)
        for name in ("exported", FROZEN_LOCK):
            if (d / name).exists():
                os.replace(d / name, arc / name)
        for name in ("status.json", "claims.json"):   # snapshot under another name: publish never sees it as a SYNC dir
            if (d / name).exists():
                shutil.copy2(d / name, arc / name.replace(".json", ".prev.json"))
        st = _read(d / "status.json")
        for k in ("frozen", "finished_at", "fix_round", "fix_pages", "reopened", "extra_builders"):
            st.pop(k, None)
        st.update(phase="edit", turn=new, updated_at=time.strftime("%H:%M:%S"), reopened_at=time.time())
        if st.get("task_id"):
            st["deck_binding"] = {"task_id": st["task_id"], "deck": deck, "mode": "edit",
                                  "authority": "reopen", "baseline_slide_ids": None}
        st.setdefault("turns", []).append({"turn": new, "why": str(why)[:200], "t": time.time()})
        st.setdefault("notes", []).append(f"{st['updated_at']} reopen turn {new}: {str(why)[:120]}")
        _write(d / "status.json", st, binding_update=True)
        with open(d / "claims.lock", "w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            claims = {k: _claim_state(v) for k, v in _read(d / "claims.json").items()}
            for v in claims.values():
                for k in ("redo", "held", "reopened_unwritten"):
                    v.pop(k, None)
                v.update(state="done", turn_closed=old)
            if (d / "claims.json").exists():
                _write(d / "claims.json", claims)
    led = dirs[0] / "turns" / str(old) / "ledgers"
    moved = []
    for pat in _LEDGER_GLOBS:   # the edit turn gets fresh server-block / write / one-shot hold budgets (this deck's)
        for f in sorted(lsd.glob(pat.replace("*", f"*{deck}*") if "*" in pat else pat)):
            led.mkdir(parents=True, exist_ok=True)
            os.replace(f, led / f.name)
            moved.append(f.name)
    dp = _dispatch_path(root)
    d_ = _read(dp)
    if d_ and not d_.get("closed"):
        d_["closed"] = time.time()
        _write(dp, d_)
    for d in dirs:
        _seal(d, cwd=root)
    out = {"ok": True, "turn": new, "archived": str(dirs[0] / "turns" / str(old)), "sync": [str(d) for d in dirs],
           "reset": moved, "readback": str(rb), "next": REOPEN_NEXT, **({"url": url} if url else {})}
    others = {k: v for k, v in _delivered_decks(root).items() if k != deck}
    if others:   # several decks delivered from this CWD: make sure "刚才那份" really meant this one
        out["other_decks"] = [dict(deck=k, **v) for k, v in sorted(others.items())]
        out["confirm"] = (f"这个目录还交付过 {len(others)} 份别的 deck（" + "；".join(
            f"{v['title'] or k}{'：' + v['url'] if v['url'] else ''}" for k, v in sorted(others.items()))
            + f"）：确认用户说的就是 {deck} 这份（标题 / 页面内容对得上）再改；对不上就停手问用户")
        out["next"] = out["confirm"] + "。" + out["next"]
    return out


def _edit_dirs(cwd, deck=None):
    """SYNC dirs of this deck in a reopened edit turn (status phase "edit")."""
    return [d for d in _cwd_sync_dirs(cwd, deck) if _read(d / "status.json").get("phase") == "edit"]


def _close_edit_turn(cwd, pptx, deck=None):
    """End of an edit turn (export / finish succeeded): write `exported` again, stamp finished_at and reseal — the next
    follow-up needs reopen again."""
    for d in _edit_dirs(cwd, deck):
        st = _read(d / "status.json")
        st["finished_at"] = time.time()
        _write(d / "status.json", st)
        (d / "exported").write_text(str(pptx or ""), encoding="utf-8")
        _seal(d, cwd=cwd)


def _exported_now(directory):
    """True once finish exported the deck (SYNC/exported marker or status finished_at); finish --fix clears both."""
    d = Path(directory)
    return (d / "exported").exists() or bool(_read(d / "status.json").get("finished_at"))


def _record_agent(directory, who, agent_id):
    """next --agent-id: remember which create_agent id runs `who` (SYNC/agents.json), so finish can name it."""
    if not agent_id or not who:
        return
    path = Path(directory) / AGENTS_FILE
    d = _read(path)
    if d.get(who) != agent_id:
        d[who] = str(agent_id)
        _write(path, d)


def _still_running(directory, window=STILL_RUNNING_WINDOW, with_ids=False):
    """Builders / researchers whose own claims or reviews show activity in the last `window` seconds: they may still run
    and keep the whole run open after delivery unless they are shut down. with_ids=True returns
    [{"who": name, "agent_id": id?}] (agent_id from the claim or SYNC/agents.json when an agent passed --agent-id).
    Return instructions in SYNC/returned.json fence ownership (since) / review (rev_since) epochs, not another agent's
    later bookkeeping t. A newer epoch can reactivate a worker; the registry does not prove process exit."""
    now, out, ids, last = time.time(), set(), {}, {}
    for v in _read(Path(directory) / "claims.json").values():
        v = _claim_state(v)
        try:
            t = float(v.get("t") or 0)
        except (TypeError, ValueError):
            t = 0.0
        current = v.get("reviewer") or v.get("who")
        for worker, since in ((v.get("who"), v.get("since")), (v.get("reviewer"), v.get("rev_since"))):
            if not worker or not _is_builder(worker):
                continue
            try:
                epoch = float(since or (t if worker == current else 0))
            except (TypeError, ValueError):
                epoch = 0.0
            activity = max(epoch, t) if worker == current else epoch
            if not (now - activity <= window):
                continue
            out.add(worker)
            last[worker] = max(last.get(worker, 0.0), epoch)
            if v.get("agent_id") and worker == v.get("who"):
                ids.setdefault(worker, str(v["agent_id"]))
    gone = _read(Path(directory) / RETURNED_FILE)
    out = {w for w in out if not (isinstance(gone.get(w), (int, float)) and gone[w] >= last.get(w, 0.0))}
    if not with_ids:
        return sorted(out)
    known = _read(Path(directory) / AGENTS_FILE)
    return [dict(who=w, **({"agent_id": ids.get(w) or known.get(w)} if (ids.get(w) or known.get(w)) else {}))
            for w in sorted(out)]


def _running_text(agents):
    """'R1（agent_id=a1）, builder4' for the still_running message."""
    return ", ".join(a["who"] + (f"（agent_id={a['agent_id']}）" if a.get("agent_id") else "") for a in agents)


def _take_revoked(directory, who):
    """{page: new owner} for pages handed over from `who` (revoked_from) that `who` has not been told about yet;
    marks them told so each takeover is reported once."""
    import fcntl
    directory = Path(directory)
    if not (directory / "claims.json").exists():
        return {}
    with open(directory / "claims.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        claims = _read(directory / "claims.json")
        out = {}
        for k, v in claims.items():
            if (isinstance(v, dict) and re.fullmatch(r"p\d+", k) and v.get("revoked_from") == who
                    and v.get("who") != who and not v.get("revoked_told")):
                out[int(k[1:])] = v.get("who")
                v["revoked_told"] = time.time()
        if out:
            _write(directory / "claims.json", claims)
    return out


def _revoked_note(revoked):
    pages = "、".join(f"P{n}（现归 {w}）" for n, w in sorted(revoked.items()))
    return (f"注意：{pages} 因你超过 {BUILDER_STALE // 60} 分钟没有提交已转交他人——立即停止这些页的一切工作"
            "（不再改它们的脚本、不跑本地 lint、不 publish），只做下面这页")


NEXT_BLOCK = 120   # default in-command wait (builders / --review): short enough for any tool-call timeout
NEXT_POLL = 20
NEXT_RETRY = ("先 wait_agent(wait_timeout=120)（有子代理时）或做别的待办，稍后再运行同一条 next"
              "（加 --no-wait 立即返回当前状态）；不用 sleep / timeout 包装，不调用内部函数")


def next_page(directory, who, prefer=None, from_end=False, review=False, block=None, agent_id=None, no_wait=False):
    """_next_once, but when nothing can be handed out yet (ok is None: pages waiting on the plan / research,
    builders still working) it waits inside the command — polling every 20 s up to `block` seconds (default
    NEXT_BLOCK for builders and reviewers) — so a small model never mistakes "nothing yet" for "finished" and returns
    early. no_wait=True: one look, no waiting; an ok:null answer carries retry_after (seconds) instead.
    agent_id (subagents: the id create_agent gave them): stored on their claims and in SYNC/agents.json, so finish's
    still_running names the agent to shut down."""
    if agent_id:
        _record_agent(directory, who, agent_id)
    if _read(Path(directory) / "status.json").get("phase") == "edit":   # follow-up turn: next hands out nothing
        return {"ok": False, "page": None, "edit": True, "next": _EDIT_NEXT}
    if _is_builder(who) and _exported_now(directory):   # a builder still running after export keeps the run open
        _mark_returned(directory, who)
        return {"ok": False, "page": None, "exported": True, "next": EXPORTED_STOP}
    if no_wait:
        block = 0
    elif block is None:
        block = NEXT_BLOCK if (_is_builder(who) or review) else 0
    deadline = time.time() + block
    kw = {"agent_id": agent_id} if agent_id else {}
    out = _next_once(directory, who, prefer, from_end, review, **kw)
    while out.get("ok") is None and time.time() < deadline:
        time.sleep(min(NEXT_POLL, max(1, deadline - time.time())))
        if _is_builder(who) and _exported_now(directory):
            _mark_returned(directory, who)
            return {"ok": False, "page": None, "exported": True, "next": EXPORTED_STOP}
        out = _next_once(directory, who, prefer, from_end, review, **kw)
    if out.get("ok") is None:
        out["retry_after"] = 0 if block else 60   # after an in-command wait: rerun at once
        if no_wait:
            out["next"] = (f"现在还没有可做的页（--no-wait 未等待）：约 {out['retry_after']} 秒后再运行同一条 next"
                           "（或去掉 --no-wait 让它在命令内等待），期间可先 wait_agent(wait_timeout=120)；"
                           "不要 return、不要搜索、不要截图或复查已完成的页。原提示：" + str(out.get("next") or ""))
        elif block:
            out["next"] = ("等了 %d 秒仍没有可做的页（还在等数据/其他人）：原样再运行同一条命令，它会继续等"
                           "（或先 wait_agent(wait_timeout=120)）；不要 return、不要搜索、不要截图或复查已完成的页" % block)
    revoked = _take_revoked(directory, who)
    if revoked:
        out["revoked"] = {str(n): w for n, w in sorted(revoked.items())}
        out["next"] = _revoked_note(revoked) + "。" + str(out.get("next") or "")
    return out


def verdict(directory, page, who, fixed=False, note=None, redo=False):
    """Close a review: the page becomes "done" (ok, or fixed by the reviewer).

    redo=True (Organizer / Main / Lead, before export): reopen a page already done or under review — state "doing",
    who = the caller — to rewrite it once; this is not the one-time finish --fix. Auto-freeze (organizer_done) waits
    until the redo page is rewritten (next closes it as done)."""
    import fcntl
    directory = Path(directory)
    if redo:
        return _redo(directory, page, who, note)
    with open(directory / "claims.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        claims = {k: _claim_state(v) for k, v in _read(directory / "claims.json").items()}
        k = f"p{int(page):02d}"
        if k not in claims:
            return {"ok": False, "next": f"P{page} 不在 claims 里"}
        if claims[k].get("redo") and claims[k].get("who") != who:   # a redo page belongs to the one who reopened it
            return {"ok": False, "next": _redo_locked(int(page), claims[k])}
        claims[k].update(state="done", reviewer=who, review="fixed" if fixed else "ok", t=time.time())
        if note:
            claims[k]["review_note"] = note[:200]
        _write(directory / "claims.json", claims)
    return {"ok": True, "page": int(page), "review": claims[k]["review"],
            "next": "运行 next --review 领下一页（没有就按它的提示等待或收尾）"}


def _redo_locked(n, c):
    owner = c.get("redo_by") or c.get("who")
    return (f"P{n} 已被 {owner} 用 verdict --redo 退回、正在重写：这页只归 {owner} 一人（不另起脚本重做、不再 redo / verdict）。"
            "有补充问题写进 gaps.md，运行 next --review 领别的页")


def _redo(directory, page, who, note):
    """verdict --redo: the reviewer found a real defect on a written page before export — reopen it to the caller."""
    import fcntl
    if who not in ("organizer", "main", "lead"):
        return {"ok": False, "next": "verdict --redo 只由 Organizer / Main / Lead 运行（检查人退回页面）"}
    if not note or not str(note).strip():
        return {"ok": False, "next": "verdict --redo 需要 --note \"<要改的真实问题>\"（例如'P5 口径与 P2 不一致'）"}
    if _exported_now(directory):
        return {"ok": False, "next": "已经导出：verdict --redo 只能在导出前用；导出后真有错由 Main/Lead 用 finish --fix N --why …（每个任务一次）"}
    n = int(page)
    if n in _frozen_lock(directory) or n in set(_read(directory / "status.json").get("frozen") or []):
        return {"ok": False, "next": f"P{n} 已冻结（organizer_done）：redo 只在冻结前用；Main/Lead 导出后用 finish --fix {n} --why …"}
    with open(directory / "claims.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        claims = {k: _claim_state(v) for k, v in _read(directory / "claims.json").items()}
        k = f"p{n:02d}"
        c = claims.get(k)
        if c and (c.get("redo") or c.get("redo_by")) and (c.get("redo_by") or c.get("who")) != who \
                and (c.get("redo") or c.get("state") == "doing"):
            return {"ok": False, "next": _redo_locked(n, c)}
        if c and c.get("state") == "reviewing" and c.get("reviewer") not in (None, who):
            return {"ok": False, "next": (f"P{n} 正由 {c.get('reviewer')} 检查：归它一人改（它会 --fixed / --redo），"
                                          "你不要另做一份；把问题写进 gaps.md 或等它结案后再看")}
        if not c or c.get("state") not in ("done", "built", "reviewing"):
            return {"ok": False, "next": f"P{n} 还没写完（{(c or {}).get('state', '未领取')}）：不用 redo，等它写完再检查"}
        if c.get("redo_count", 0) >= 1:
            return {"ok": False, "next": f"P{n} 已经 redo 过一次：保留当前版本，问题写进 gaps"}
        _reset_page_ledger(directory, [n])   # the rewrite starts with a fresh server-block budget
        claims[k] = {"who": who, "state": "doing", "t": time.time(), "since": time.time(), "written": 0, "redo": True,
                     "redo_note": str(note)[:200], "redo_count": c.get("redo_count", 0) + 1, "redo_by": who,
                     "built_by": c.get("built_by") or c.get("who")}
        _write(directory / "claims.json", claims)
    return {"ok": True, "page": n, "redo": True, "who": who,
            "next": (f"已退回 P{n} 给你（{who}，不算 finish --fix）：在你的脚本里只改这一处（{str(note)[:60]}），"
                     f"f.publish(..., page={n}, who=\"{who}\") / republish_xml(…, page={n}) 写入一次，然后运行 next --review；"
                     "写完前不会标 organizer_done")}


def _no_main(cwd):
    """True when no skill-guided MainAgent owns this deck (no / closed dispatch.json): the closing agent is a Lead."""
    d = _read(_dispatch_path(cwd)) if cwd else {}
    return not d or bool(d.get("closed"))


ORG_SHUTDOWN_NOTE = ("仅当 Organizer 还没 return 时 send_message 它 shutdown，然后 wait_agent(wait_timeout=120) 等它结束"
                     "（它要先停掉自己的子代理），不要 kill_agent；"
                     "已 return 的跳过——不发 shutdown、不 kill / interrupt")
ORG_RETURNED_NOTE = "Organizer 已 return：跳过 shutdown / kill_agent（已 return 的不再发任何消息）"
_LEAD_DELIVER = "用一次 present_files 同时交付链接与 PPTX，然后运行 lead-return（见下）生成 return 文本"


def _lead_return_cmd(pptx=None):
    return (f'python3 {Path(__file__).resolve()} lead-return --title "<标题>" --pages N --url "<url>" '
            f'--pptx "{pptx or "<PPTX 绝对路径>"}" [--notes-file notes.txt] [--gaps-file gaps.txt]'
            "（说明/缺口先写进文件再传 --notes-file/--gaps-file：双引号里的 $250K 会被 shell 吞成 50K）")


def _refreeze(directory, pages):
    """End of a finish --fix round: the fixed pages join frozen.lock / status frozen again."""
    pages = {int(p) for p in pages}
    st = _read(directory / "status.json")
    if st.get("frozen") is not None or (directory / FROZEN_LOCK).exists():
        st["frozen"] = sorted(set(st.get("frozen") or []) | pages)
        _write_frozen_lock(directory, _frozen_lock(directory) | pages)
    st.pop("fix_pages", None)
    _write(directory / "status.json", st)
    import fcntl
    with open(directory / "claims.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        claims = {k: _claim_state(v) for k, v in _read(directory / "claims.json").items()}
        for n in pages:
            if f"p{n:02d}" in claims:
                claims[f"p{n:02d}"].update(state="done", t=time.time())
        if claims:
            _write(directory / "claims.json", claims)


MAIN_SILENT = 480   # s without Main's wait / next / publish before the Organizer takes over P1–P3 and finish


def _touch_main(directory):
    try:
        (Path(directory) / "main_seen").write_text(str(time.time()), encoding="utf-8")
    except OSError:
        pass


def main_gone(directory):
    """Main ended its turn early (no wait / next / publish for MAIN_SILENT s after the plan was out): the Organizer
    builds P1–P3 and runs finish so the deck is still complete. Writes SYNC/main_gone once decided."""
    d = Path(directory)
    if (d / "main_gone").exists():
        return True
    seen = d / "main_seen"
    plan = d / "plan.py"
    if not plan.exists():
        return False
    last = max(seen.stat().st_mtime if seen.exists() else 0, plan.stat().st_mtime if not seen.exists() else 0)
    if time.time() - last > MAIN_SILENT:
        try:
            (d / "main_gone").write_text(str(time.time()), encoding="utf-8")
        except OSError:
            pass
        return True
    return False


def _organizer_blocked(cwd, who):
    """Organizer with a live (open, fresh) dispatch: Main owns finish / export / delivery."""
    if who != "organizer" or not cwd:
        return False
    d = _read(_dispatch_path(cwd))
    if any(main_gone(x) for x in (Path(cwd) / ".lark-slides" / "strategy").glob("*/sync")):
        return False
    return bool(d) and not d.get("closed") and time.time() - d.get("t", 0) <= DISPATCH_FRESH


_ORG_FINISH_MSG = "Main 在线：finish/导出/交付只由 Main 做；你写完 organizer_done 后 return"


FIX_BEFORE_EXPORT_MSG = (
    "finish --fix 只用于本轮导出之后的一次修正：这份 deck 本轮还没导出（SYNC 里没有 exported 标记），不能用它重置页面的"
    "写入/服务端拦截计数。某页被服务端拦满 4 次（硬停）时：① 换一种更简单的构造——f.publish(..., page={p}) 改成 row_table"
    "（Label + Bar/Text 列）版本写入（硬停后仍接受 2 次 row_table 提交），或删掉报错的标签/说话框；② 只改文字/删标签时直接改 "
    ".lark-slides/xml/{deck}/p{p:02d}.xml 再 republish_xml(路径, \"{deck}\", page={p}, cwd=CWD)（不受拦截次数限制）；"
    "③ 仍不行就保留该页现状、问题写进 gaps.md，继续 next / finish。导出前要退回已完成的页用 verdict --redo --note …；"
    "交付后的追问轮用 reopen，不用 --fix")


def fix_round(directory, deck, cwd=".", pages=None, why=None, who=None):
    """finish --fix N[,M] --why "…": the one legal way to change pages after export / freeze (Main / Lead only, once
    per task). Unfreezes just those pages, reopens their claims to the caller, clears the export marker; the caller
    republishes them and runs plain finish again (re-export)."""
    import fcntl
    directory, cwd = Path(directory), str(Path(cwd).resolve())
    if who is None:   # finish run without --who: the closing agent (Lead when no live dispatch, else Main)
        who = "lead" if _no_main(cwd) else "main"
    if who not in ("main", "lead"):
        return {"ok": False, "next": "finish --fix 只由 Main / Lead 运行（--who main 或 --who lead）；Organizer/Builder 不改已冻结的页"}
    if not why or not str(why).strip():
        return {"ok": False, "next": "finish --fix 需要 --why \"<要改的真实问题>\"（例如'P5 标题方向与图相反'）"}
    nums = _pages(pages or "")
    if not nums:
        return {"ok": False, "next": "finish --fix 需要页号：--fix 5 或 --fix 5,7（一次调用写全要改的页，含摘要页）"}
    st = _read(directory / "status.json")
    summ = _summary_page(directory)
    prev = st.get("fix_round")
    if not prev and not _exported_now(directory):   # the post-export correction round only — never a counter reset
        return {"ok": False, "not_exported": True, "next": FIX_BEFORE_EXPORT_MSG.format(deck=deck, p=nums[0])}
    add_on = False
    if prev:
        done_pages = set(prev.get("pages") or [])
        # the one exception: the first call left out the summary page and the deck has not been re-exported yet
        if (summ and summ not in done_pages and summ in nums and set(nums) <= done_pages | {summ}
                and not prev.get("summary_added") and not _exported_now(directory)):
            add_on = True
        else:
            why_no = ("已经重新导出过" if _exported_now(directory) else
                      f"第二次只能追加摘要页 P{summ}" if summ and summ not in done_pages and not prev.get("summary_added")
                      else "每个任务一次")
            return {"ok": False, "fix_round": prev,
                    "next": f"这个任务已经用过一次 finish --fix（{why_no}）：不再改页，按现有 PPTX 交付"}
    if add_on:
        new = sorted(set(nums) - set(prev.get("pages") or []))
        prev.update(pages=sorted(set(prev.get("pages") or []) | set(new)), summary_added=True)
        st["fix_round"] = prev
        st["fix_pages"] = sorted(set(st.get("fix_pages") or []) | set(new))
        nums = new
    else:
        st["fix_round"] = {"pages": nums, "why": str(why)[:200], "who": who, "t": time.time()}
        st["fix_pages"] = nums
    st["frozen"] = [p for p in (st.get("frozen") or []) if p not in nums]
    st["reopened"] = sorted(set(st.get("reopened") or []) | set(nums))
    st.pop("finished_at", None)
    _write(directory / "status.json", st)
    if (directory / FROZEN_LOCK).exists():
        _write_frozen_lock(directory, _frozen_lock(directory) - set(nums))
    (directory / "exported").unlink(missing_ok=True)
    with open(directory / "claims.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        claims = {k: _claim_state(v) for k, v in _read(directory / "claims.json").items()}
        for n in nums:
            claims[f"p{n:02d}"] = {"who": who, "state": "doing", "t": time.time(), "since": time.time(), "written": 0,
                                   "via": "fix"}
        _write(directory / "claims.json", claims)
    lsd = Path(cwd) / ".lark-slides"
    for kind in ("writes", "blocked"):   # the fix rewrite gets a fresh write / server-block budget for these pages
        f = lsd / f"{kind}-{deck}.json"
        d = _read(f)
        if d:
            for n in nums:
                d.pop(f"p{n:02d}", None)
                d.pop(f"p{n:02d}:rt", None)
            _write(f, d)
    _seal(directory)
    fixing = st["fix_pages"]
    out = {"ok": True, "fix": fixing, "next": (
        f"已解冻第 {fixing} 页（本任务的 --fix）：只改这些页——改 .lark-slides/xml/{deck}/pNN.xml 后 republish_xml(路径, deck, page=N, cwd=CWD)，"
        f"或重跑该页脚本 f.publish(..., page=N, who=\"{who}\")；改完运行同一条 finish（不带 --fix）重新导出，再用一次 present_files 交付。"
        "其余页不动、不截图全稿")}
    if add_on:
        out["summary_added"] = summ
    elif summ and summ not in nums and _feeds_summary(Path(cwd), summ, nums):
        out["hint"] = (f"摘要页引用了这些页的数字：一起写进 --fix（本次可加 P{summ}）——"
                       f"改完正文页后、重新导出前运行 finish --fix {summ} --why \"摘要页同步\"（只此一次追加）")
    return out


def _unit_numbers(text):
    unit = r"(?:亿|万|%|pct|pts|pp|bp|倍|家|店|GW|MW|tn|bn|mn|[mMbBkK]\b|x\b)"
    return {f"{m.group(1)}{m.group(2)}" for m in re.finditer(r"(\d+(?:\.\d+)?)\s*(" + unit + ")", text.replace(",", ""))
            if not (len(m.group(1)) == 4 and m.group(1).startswith("20"))}


def _feeds_summary(cwd, summ, pages):
    """True when the summary page shares a number-with-unit with any of these pages (or either XML is missing —
    then the hint is given anyway: the summary usually quotes every content page)."""
    xd = Path(cwd) / ".lark-slides" / "xml"
    txt = lambda n: re.sub(r"<[^>]+>", " ", _read_text(xd / f"p{n:02d}.xml"))
    s = txt(summ)
    texts = [txt(n) for n in pages]
    if not s.strip() or not any(t.strip() for t in texts):
        return True
    sn = _unit_numbers(s)
    return any(sn & _unit_numbers(t) for t in texts)


LINT_ROUNDS = 2   # finish blocks on read-back server-lint errors at most this many times per task (never deadlocks)


def _readback_bodies(res):
    """{slide_id: inner XML} from the +xml-get result finish already holds (no extra call)."""
    try:
        return dict(_pub()._deck_slides(res))
    except Exception:  # noqa: BLE001
        return {}


def _readback_noise(issue, body):
    """The same conversion-noise rule publish used at write time (_classify), applied to the read-back page XML: True
    when it still drops this issue (generated elements keep their marker on read-back)."""
    if not body or not isinstance(issue, dict):
        return False
    try:
        pub = _pub()
        is_generated_element = sys.modules[pub.__package__ + "._compose"].is_generated_element
        page = body if "<data" in body else f"<data>{body}</data>"
        page = f'<slide xmlns="{_SML}">{page}</slide>'
        kids = pub._children(page)
        gen = {i for i, el in enumerate(kids) if is_generated_element(el)}
        ignorable, _ = pub._classify(page, gen, [issue])
    except Exception:  # noqa: BLE001
        return False
    return bool(ignorable)


def _nolint_waives(rec, code, issue, body=None):
    """Does the write-time nolint record of a page cover this read-back issue? The page was written after publish
    judged its findings, so any read-back issue whose code was judged on that page then (author-waived, or dropped as
    conversion noise — `noise_codes`) passes and is only reported; issues of other codes block. Old ledgers (a list of
    codes) waive those codes; v2 ledgers without `noise_codes` fall back to re-running the noise rule."""
    if not rec:
        return False
    if isinstance(rec, list):
        return code in rec
    if not isinstance(rec, dict):
        return False
    if code in {w.get("code") for w in rec.get("waived") or []} or code in (rec.get("noise_codes") or []):
        return True
    return bool(rec.get("noise")) and _readback_noise(issue, body)


def _readback_lint(res, xml_text, registry, cwd, deck):
    """Server lint of the whole deck, read from the one +xml-get finish already made (its data.issues report — no extra
    call). Returns {"errors": {page: [codes]}, "waived": {page: [codes]}} or {"unavailable": why}. Codes that publish
    already judged on that page's last write (conversion noise / waive + screenshot, then sent without lint;
    .lark-slides/nolint-<deck>.json) are listed under waived, not blocked. Page 0 = document-level findings."""
    if not isinstance(res, dict) or not res.get("ok"):
        return {"unavailable": "回读失败"}
    try:
        here = str(Path(__file__).resolve().parent)
        if here not in sys.path:
            sys.path.insert(0, here)
        import lint_inspect
        ins = lint_inspect.Inspector(res)
    except Exception as e:  # noqa: BLE001
        return {"unavailable": f"lint 报告解析失败（{type(e).__name__}）"}
    if not ins.found:
        return {"unavailable": "回读响应里没有 lint 报告（data.issues）"}
    order = re.findall(r'<slide\b[^>]*?\bid=\\?"([^"\\]+)', xml_text or "")
    by_id = {v: int(k[1:]) for k, v in registry.items()}
    ledger = {int(k[1:]): v for k, v in _read(Path(cwd) / ".lark-slides" / f"nolint-{deck}.json").items()
              if re.fullmatch(r"p\d+", k)}
    bodies = {}
    errs, skip = {}, {}
    for r in ins.rows:
        if r.get("level") != "error":
            continue
        sid, num = r.get("slide_id"), r.get("slide_number")
        page = by_id.get(sid) if sid else None
        if page is None and isinstance(num, int) and num > 0:
            page = by_id.get(order[num - 1], num) if num <= len(order) else num
        page = page or 0
        code = r.get("code") or "unknown"
        rec = ledger.get(page)
        if rec and not bodies:
            bodies = _readback_bodies(res)
        ok = _nolint_waives(rec, code, r.get("issue"), bodies.get(registry.get(f"p{page:02d}")) if rec else None)
        (skip if ok else errs).setdefault(page, []).append(code)
    tidy = lambda d: {p: sorted(set(c)) for p, c in sorted(d.items())}
    return {"errors": tidy(errs), "waived": tidy(skip)}


def _lint_reopen(directory, pages, who):
    """finish found server-lint errors on these pages: unfreeze just them and hand them to the finisher (publish
    accepts its writes), so they can be fixed one page per command before finish runs again."""
    st = _read(directory / "status.json")
    st["lint_rounds"] = st.get("lint_rounds", 0) + 1
    _write(directory / "status.json", st)
    _reopen_to(directory, pages, who, "lint")


def _reopen_to(directory, pages, who, via):
    """Unfreeze these pages and hand them (state done, so finish still counts them) to `who` for a rewrite."""
    import fcntl
    st = _read(directory / "status.json")
    st["frozen"] = [p for p in (st.get("frozen") or []) if p not in pages]
    st["reopened"] = sorted(set(st.get("reopened") or []) | set(pages))
    _write(directory / "status.json", st)
    if (directory / FROZEN_LOCK).exists():
        _write_frozen_lock(directory, _frozen_lock(directory) - set(pages))
    _reset_page_ledger(directory, pages)   # the rewrite starts with a fresh server-block budget
    if not (directory / "claims.json").exists():
        return
    with open(directory / "claims.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        claims = {k: _claim_state(v) for k, v in _read(directory / "claims.json").items()}
        for p in pages:
            c = claims.get(f"p{p:02d}") or {}
            claims[f"p{p:02d}"] = {**c, "who": who, "state": "done", "t": time.time(), "via": via,
                                   "built_by": c.get("built_by") or c.get("who") or who}
        _write(directory / "claims.json", claims)


def finish(directory, deck, cwd=".", name=None, solo=False, who=None, fix=None, why=None, url=None, notes=None,
           gaps=None, accept_lint=None):
    """Main's whole closing in one call: read the deck back once, check every plan page is registered and the deck has
    exactly that many slides, then export PPTX into <cwd>. Builder pages still waiting for review pass unreviewed
    (no review tail). Prints a short verdict; no screenshots, no rework. fix="5,7" + why: see fix_round.
    After a successful export: still_running lists builders / researchers active in the last 10 min (shut them down
    first); for a Lead (who=lead or no live Main) the full lead-return text is written to
    <cwd>/.lark-slides/decks/<deck>/lead_return.txt and returned as final_reply (url from --url or deck.txt).
    Before exporting, the server lint report carried by that same read-back (data.issues) is checked: error-level
    findings on pages not written via an explicit waive / no-lint return ok=False with lint_errors {page: [codes]} and
    reopen just those pages to the finisher; accept_lint="<reason>" (or the LINT_ROUNDS-th round) exports anyway.
    A failed read-back blocks export; an absent lint report alone does not."""
    import re as _re
    if _organizer_blocked(cwd, who):
        return {"ok": False, "next": _ORG_FINISH_MSG}
    if fix:
        return fix_round(directory, deck, cwd, fix, why, who)
    directory, cwd = Path(directory), str(Path(cwd).resolve())
    directory.mkdir(parents=True, exist_ok=True)
    pub = _pub()
    deck = pub._deck_id(deck)
    with pub._deck_lock(cwd, deck):
        _, registry = pub._page_registry(cwd, deck)
        res = _cli(["slides", "+xml-get", "--presentation", deck], cwd)
        checked = pub._check_task_deck(cwd, deck, res, registry, directory=directory)
        if not checked["ok"] and pub.drop_duplicate_strangers(checked, res, registry, cwd, deck):
            res = _cli(["slides", "+xml-get", "--presentation", deck], cwd)
            checked = pub._check_task_deck(cwd, deck, res, registry, directory=directory)
        if not checked["ok"] and checked.get("code") == "deck_identity_mismatch" and not checked.get("unexpected_slide_ids") \
                and not checked.get("duplicates") and not checked.get("missing"):   # order only: put pages in page order
            pub.verify_order(deck, cwd, repair=True)
            res = _cli(["slides", "+xml-get", "--presentation", deck], cwd)
            checked = pub._check_task_deck(cwd, deck, res, registry, directory=directory)
        if not checked["ok"]:
            return checked
        if not isinstance(res, dict) or res.get("ok") is not True:
            return {"ok": False, "code": "deck_readback_invalid", "next": "本次完整回读失败：恢复 +xml-get 后再导出"}
        _stamp_deck(directory, deck)
        registry = {key: value for key, value in registry.items() if re.fullmatch(r"p\d+", key)}
    plan = _plan_pages(directory)
    want = sorted(set(plan) | set(range(1, min(plan)))) if plan else sorted(int(k[1:]) for k in registry)
    expected = len(want) or None
    if solo:   # pages written with +add-slide (cover, text pages) are not in the registry: check only registered ones
        want, expected = sorted(int(k[1:]) for k in registry), None
    xml = json.dumps(res.get("data") or {}, ensure_ascii=False)
    n = len(_re.findall(r"<slide\b", xml))
    ids = set(_re.findall(r'<slide\b[^>]*?\bid=\\?"([^"\\]+)', xml))
    left = [p for p in want if f"p{p:02d}" not in registry or (ids and registry[f"p{p:02d}"] not in ids)]
    bodies = dict(_re.findall(r'<slide\b[^>]*?\bid=\\?"([^"\\]+)\\?"(.*?)</slide>', xml, _re.S))
    for p_ in want:   # a page that reached the deck but carries (almost) nothing: written empty, build it again
        body = bodies.get(registry.get(f"p{p_:02d}", ""), None)
        text_ = _re.sub(r"\s+", " ", _re.sub(r"<[^>]+>", " ", body or "")).strip()
        if p_ not in left and body is not None and (len(_re.findall(r"<(?:shape|img|chart|line|table)\b", body)) < 3
                                                    or (p_ > 3 and len(text_) < 60)):   # empty or placeholder-only
            left.append(p_)
    left.sort()
    import fcntl
    with open(directory / "claims.lock", "w") as lock:   # no review tail: pages still waiting for review pass as is
        fcntl.flock(lock, fcntl.LOCK_EX)
        claims = {k: _claim_state(v) for k, v in _read(directory / "claims.json").items()}
        for v in claims.values():
            if v["state"] == "built":
                v.update(state="done", review="skipped")
        _rescue_reviews(claims)   # a review stuck > REVIEW_RESCUE (tool timeout) does not hold the export
        if claims:
            _write(directory / "claims.json", claims)
    fixing = sorted(int(k[1:]) for k, v in claims.items() if v["state"] == "reviewing"
                    or (v.get("redo") and v["state"] == "doing"))   # a verdict --redo page being rewritten
    out = {"ok": False, "pages": n, "expected": expected, "missing": left, "being_fixed": fixing}
    if fixing:
        out["next"] = ("第 %s 页正在被另一位检查人修改（≤3 分钟）：等 1 分钟再运行 finish，不要自己去查这些页" % fixing)
        return out
    if solo and want and n < max(want):
        left = sorted(set(left) | {p_ for p_ in want if p_ > n})
    if left or (expected and n != expected):
        if left:   # pages never written (or deleted in the deck): hand them out again
            with open(directory / "claims.lock", "w") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                claims = {k: _claim_state(v) for k, v in _read(directory / "claims.json").items()}
                for p_ in left:
                    if claims.get(f"p{p_:02d}", {}).get("state") == "done":
                        del claims[f"p{p_:02d}"]
                _write(directory / "claims.json", claims)
            st = _read(directory / "status.json")
            if st.get("frozen"):
                st["frozen"] = [p_ for p_ in st["frozen"] if p_ not in left]
            if (directory / FROZEN_LOCK).exists():
                _write_frozen_lock(directory, _frozen_lock(directory) - set(left))
            st["reopened"] = sorted(set(st.get("reopened") or []) | set(left))   # next must not close them from the registry
            _write(directory / "status.json", st)
        out["next"] = (("deck 里缺第 %s 页或该页为空（deck 共 %d 页，已登记 %s 页）：只重写这些页，其余页不动，做完再运行 finish"
                        if solo else
                        "deck 里缺第 %s 页（deck 共 %d 页，计划 %s 页）：只补这些页（运行 next --review，它会把缺的页发给你），其余页不动，做完再运行 finish")
                       % (left, n, expected))
        return out
    st0 = _read(directory / "status.json")
    sp = _summary_page(directory) or 3
    rounds = st0.get("consistency_rounds", 0)
    if not solo and rounds < 1 and not st0.get("consistency_checked"):   # one check only: a second round re-opens pages and loops
        missing_ = _summary_numbers(Path(cwd), sp)
        if missing_:   # a summary number not repeated in the body is often a derived figure: a note, never a reopen
            out["summary_note"] = f"P{sp} 这些数字在正文页没有出现（只提示，不阻塞）：" + "；".join(missing_[:6])
        # only a clash with plan.py F (≥ 2 %) reopens a page: page-vs-page clashes mixed subjects / scopes too often
        stale = [x for x in _front_stale(directory, want, bodies, registry) if _plan_clash(x)]
        st0.update(consistency_checked=True, consistency_at=time.time(), consistency_rounds=rounds + 1)
        if stale:   # let P2/P3 be rewritten: they are frozen by organizer_done
            fix = {x["page"] for x in stale}   # cross-chapter pages stay frozen
            st0["frozen"] = [n for n in (st0.get("frozen") or []) if n not in fix]
            st0["reopened"] = sorted(set(st0.get("reopened") or []) | fix)
            _write(directory / "status.json", st0)
            if (directory / FROZEN_LOCK).exists():
                _write_frozen_lock(directory, _frozen_lock(directory) - fix)
            parts = ["这些页的数字和 plan.py F 不一致（摘要先写后 plan 改了，或某页用了别的数）——" + "；".join(
                f"P{x['page']} {x['metric']} '{x['old']}' → 改成 '{x['new']}'（{x['where']}）" for x in stale[:8])]
            pg = "、".join(f"P{n}" for n in sorted(fix))
            out["next"] = ("导出前核对：" + "。".join(parts) + f"。只解冻了 {pg}：把这些页的数字改成和正文/plan.py 一致（改 "
                           f".lark-slides/xml/{deck}/pNN.xml 后 republish_xml(路径, deck, page=N, cwd=CWD) 最快；数字从 plan.py F 拼，"
                           "不手写），改完再运行 finish——不再复查，直接导出；其他页不动。确属不同口径（如全公司 vs 某品类）：不用改，"
                           "直接再运行同一条 finish 即可导出（不要绕开 finish 自己用 lark-cli 导出——没有那个子命令）")
            out["front_stale"] = stale[:6]
            return out
        _write(directory / "status.json", st0)
    try:
        by_page = {p_: bodies.get(registry.get(f"p{p_:02d}", ""), "") for p_ in want}
        xp = cross_page_conflicts(_slide_texts(by_page))
    except Exception:  # noqa: BLE001 — a hint only
        xp = []
    if xp:
        out["cross_page"] = CROSS_PAGE_MSG.format(items="；".join(xp))
    lint = _readback_lint(res, xml, registry, cwd, deck)
    if lint.get("unavailable"):
        out["lint"] = f"未做全稿 lint 核对：{lint['unavailable']}（不阻塞导出）"
    else:
        if lint["waived"]:
            out["lint_waived"] = {str(p): c for p, c in lint["waived"].items()}   # judged at write time (no-lint)
        if lint["errors"].get(0):   # document-level: no page to rewrite — reported, never blocks
            out["lint_document"] = lint["errors"].pop(0)
        if lint["errors"]:
            out["lint_errors"] = {str(p): c for p, c in lint["errors"].items()}
            rounds_ = _read(directory / "status.json").get("lint_rounds", 0)
            if (accept_lint and str(accept_lint).strip()) or rounds_ >= LINT_ROUNDS:
                why_ = str(accept_lint).strip()[:200] if accept_lint else f"已拦 {rounds_} 轮，不再阻塞"
                st0 = _read(directory / "status.json")
                st0["lint_accepted"] = {"why": why_, "errors": out["lint_errors"], "t": time.time()}
                _write(directory / "status.json", st0)
                out["lint"] = f"服务端 lint 仍有 error，已放行导出（{why_[:80]}）"
            else:
                fixer = who if who in ("main", "lead") else ("lead" if _no_main(cwd) else "main")
                _lint_reopen(directory, sorted(lint["errors"]), fixer)
                desc = "；".join(f"P{p} {'/'.join(c)}" for p, c in lint["errors"].items())
                out["next"] = (f"未导出：回读的服务端 lint 有 error——{desc}。已解冻这些页并交给你（{fixer}）：一条命令只改一页"
                               f"（改 .lark-slides/xml/{deck}/pNN.xml 后 republish_xml(路径, deck, page=N, cwd=CWD)，或重跑该页脚本 "
                               f"f.publish(..., page=N, who=\"{fixer}\")），按 publish 返回的 fix 改到写入成功；全部改完再运行同一条 finish。"
                               "确属误报、不值得改时，带 --accept-lint \"<理由>\" 重跑 finish 放行（会记进 status.json）")
                return out
    out.update(_export_pptx(deck, cwd, name))
    if out["ok"]:   # exported: the deck is frozen (Frame.publish refuses later writes — they would miss the PPTX)
        st = _read(directory / "status.json")
        st["finished_at"] = time.time()
        _write(directory / "status.json", st)
        (directory / "exported").write_text(str(out.get("pptx") or ""), encoding="utf-8")   # publish checks this too
        if st.get("fix_pages"):   # the fix round is over: its pages are frozen again with the rest
            _refreeze(directory, st["fix_pages"])
        _seal(directory)
        if _edit_dirs(cwd, deck):   # finish used to close a reopened edit turn: this deck's SYNC dirs are exported again
            _close_edit_turn(cwd, out.get("pptx"), deck)
    dispatched = _read(_dispatch_path(cwd))
    same_main = (who == "main" and dispatched.get("sync")
                 and Path(dispatched["sync"]).resolve() == directory.resolve())
    lead = who == "lead" or (not solo and not same_main and _no_main(cwd))
    if out["ok"] and lead:
        out["lead_return"] = _lead_return_cmd(out.get("pptx"))
    gone = (not solo and not lead and out["ok"]) and _organizer_gone(directory, cwd)
    if gone:
        out["organizer_returned"] = True
    out["next"] = (("present_files 交付 PPTX 与链接。" if solo else _LEAD_DELIVER + "。" if lead else
                    "用一次 present_files 同时交付 PPTX 与链接 → "
                    + ("dispatch --cwd <CWD> --close → " if not _no_main(cwd) else "")
                    + (ORG_RETURNED_NOTE if gone else ORG_SHUTDOWN_NOTE) + "。") +
                   "finish 已核对过页数与空白页：不再回读 lint、不再截图、不逐页回看、不修改任何页、不再导出第二份"
                   if out["ok"] else "导出失败：原样重跑 finish 一次")
    if out["ok"] and who in ("main", "lead", None):
        agents = _still_running(directory, with_ids=True)
        if agents and gone:   # the Organizer already returned: its subagents cannot be reached through it
            agents = []
        if agents:
            out["still_running"] = [a["who"] for a in agents]
            out["still_running_agents"] = agents
            out["still_running_next"] = STILL_RUNNING_MSG
            out["still_running_cmd"] = _shutdown_cmd(agents, lead=lead)
            out["next"] = f"{STILL_RUNNING_MSG}：{_running_text(agents)}（照做：{out['still_running_cmd']}）；然后 " + out["next"]
    url = url or (_deck_url(directory, cwd, deck) if out["ok"] else None)
    if url:
        out["url"] = url
        _remember_url(cwd, deck, url)
    if out["ok"] and lead:
        text = lead_return(name or (Path(out["pptx"]).stem if out.get("pptx") else deck), n or expected or len(want),
                           url, out.get("pptx") or "", notes, gaps,
                           who="lead" if who == "lead" or not _dispatch_path(cwd).exists() else "closer")
        fr = _write_final_reply(cwd, deck, text)   # the Lead cats this file as its last message (no self-summary)
        out["final_reply"] = text
        out["final_reply_file"] = str(fr)
        out["next"] = ((f"{STILL_RUNNING_MSG}：{_running_text(out['still_running_agents'])}（照做：{out['still_running_cmd']}）；然后 "
                        if out.get("still_running_agents") else "")
                       + FINAL_REPLY_NEXT + "（cat final_reply_file 给的路径）" + ("" if url else "（没找到 deck 链接，final_reply 里只有 PPTX：带 --url \"<+create 返回的 url>\" 重跑 finish 补上）")
                       + "。finish 已核对过页数与空白页：不再回读 lint、不再截图、不逐页回看、不修改任何页、不再导出第二份")
    return out


def _write_final_reply(cwd, deck, text):
    """FINAL_REPLY.md + lead_return.txt of this deck (.lark-slides/decks/<deck>/). Returns the FINAL_REPLY path — the
    Lead cats exactly this path (printed in final_reply_file), never a fixed per-folder file that an earlier deck of the
    same conversation may have left behind."""
    d = Path(cwd).resolve() / ".lark-slides" / "decks" / str(deck or "_")
    d.mkdir(parents=True, exist_ok=True)
    (d / "lead_return.txt").write_text(text, encoding="utf-8")
    fr = d / FINAL_REPLY_FILE
    fr.write_text(text, encoding="utf-8")
    return fr


def _export_pptx(deck, cwd, name=None):
    """drive +export the deck as PPTX into cwd: {ok, pptx (absolute), export (error text or None)}."""
    args = ["drive", "+export", "--token", deck, "--doc-type", "slides", "--file-extension", "pptx", "--output-dir", ".",
            "--overwrite"] + (["--file-name", name] if name else [])
    exp = _cli(args, cwd)
    path = next((v for v in re.findall(r'"([^"]+\.pptx)"', json.dumps(exp, ensure_ascii=False))), None)
    out = dict(ok=bool(exp.get("ok")) and bool(path), pptx=str(Path(cwd) / path) if path and not Path(path).is_absolute()
               else path, export=None if exp.get("ok") else str(exp)[:300])
    if out["ok"] and Path(out["pptx"]).is_file():
        try:
            out["native_chart_fonts"] = _normalize_native_chart_export(out["pptx"], cwd, deck)
        except (OSError, ValueError) as error:
            out.update(ok=False, export=f"Native chart export font mapping failed: {error}")
    return out


def _normalize_native_chart_export(path, cwd, deck):
    """Restore locally authored NativeChart fonts to their online point sizes, leaving other sources untouched."""
    from decimal import Decimal, InvalidOperation
    import posixpath
    import zipfile
    from xml.etree import ElementTree as ET

    source_directory = Path(cwd) / ".lark-slides" / "xml" / str(deck)
    sources = {}
    for source in source_directory.glob("p[0-9]*.xml"):
        charts = list(ET.parse(source).getroot().iter(f"{{{_SML}}}chart"))
        if any((chart.get("id") or "").startswith("exhibit-native-") for chart in charts):
            sources[int(source.stem[1:])] = charts
    if not sources:
        return {"charts": 0, "font_runs": 0}
    drawing = "http://schemas.openxmlformats.org/drawingml/2006/main"
    chart_namespace = "http://schemas.openxmlformats.org/drawingml/2006/chart"
    relation = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
    presentation = "http://schemas.openxmlformats.org/presentationml/2006/main"
    patches, chart_count, font_runs = {}, 0, 0

    def value_identity(value):
        try:
            return Decimal(value)
        except InvalidOperation:
            return value

    def cached_values(series, section, count):
        points = series.findall(f"{{{chart_namespace}}}{section}//{{{chart_namespace}}}pt")
        values = [""] * count
        for ordinal, point in enumerate(points):
            index = int(point.get("idx", ordinal))
            value = point.find(f"{{{chart_namespace}}}v")
            if index >= count or value is None:
                raise ValueError("Native chart data differs from local source")
            values[index] = value.text or ""
        return values

    def relationships(archive, part):
        rel_path = posixpath.join(posixpath.dirname(part), "_rels", posixpath.basename(part) + ".rels")
        return {node.get("Id"): posixpath.normpath(posixpath.join(posixpath.dirname(part), node.get("Target")))
                for node in ET.fromstring(archive.read(rel_path)) if node.get("TargetMode") != "External"}

    with zipfile.ZipFile(path) as archive:
        slide_targets = relationships(archive, "ppt/presentation.xml")
        slide_ids = ET.fromstring(archive.read("ppt/presentation.xml")).findall(f"{{{presentation}}}sldIdLst/{{{presentation}}}sldId")
        for page, charts in sources.items():
            if page > len(slide_ids):
                raise ValueError(f"Native chart page {page} is missing from export")
            slide_path = slide_targets[slide_ids[page - 1].get(f"{{{relation}}}id")]
            slide = ET.fromstring(archive.read(slide_path))
            exported = list(slide.iter(f"{{{chart_namespace}}}chart"))
            if len(exported) != len(charts):
                raise ValueError(f"Native chart count differs on page {page}")
            chart_targets = relationships(archive, slide_path)
            for source, reference in zip(charts, exported):
                if not (source.get("id") or "").startswith("exhibit-native-"):
                    continue
                target = chart_targets[reference.get(f"{{{relation}}}id")]
                raw = archive.read(target)
                tree = ET.fromstring(raw)
                categories = source.find(f"{{{_SML}}}chartData/{{{_SML}}}dim1/{{{_SML}}}chartField").text.split(",")
                fields = source.findall(f"{{{_SML}}}chartData/{{{_SML}}}dim2/{{{_SML}}}chartField")
                series = list(tree.iter(f"{{{chart_namespace}}}ser"))
                if len(fields) != len(series):
                    raise ValueError("Native chart series count differs from local source")
                for field, exported_series in zip(fields, series):
                    names = [node.text for node in exported_series.findall(f"{{{chart_namespace}}}tx//{{{chart_namespace}}}v")]
                    values = (field.text or "").split(",")
                    if (names != [field.get("name")] or cached_values(exported_series, "cat", len(categories)) != categories
                            or [value_identity(value) for value in cached_values(exported_series, "val", len(values))]
                            != [value_identity(value) for value in values]):
                        raise ValueError("Native chart data differs from local source")
                parents = {child: parent for parent in tree.iter() for child in parent}
                horizontal = source.find(f".//{{{_SML}}}chartPlot").get("type") == "bar"
                font_nodes = [node for node in tree.iter() if node.tag in {
                    f"{{{drawing}}}{tag}" for tag in ("defRPr", "rPr", "endParaRPr")} and node.get("sz")]
                replacements = []
                for node in font_nodes:
                    owner = node
                    while owner.tag not in {f"{{{chart_namespace}}}{tag}" for tag in ("dLbls", "catAx", "valAx", "legend")}:
                        if owner not in parents:
                            raise ValueError(f"Unrecognized native chart font role on page {page}")
                        owner = parents[owner]
                    role = owner.tag.rsplit("}", 1)[-1]
                    if role == "dLbls":
                        definition = source.find(f".//{{{_SML}}}chartLabels")
                    elif role == "legend":
                        definition = source.find(f"{{{_SML}}}chartLegend")
                    else:
                        axis_type = ("y" if horizontal else "x") if role == "catAx" else ("x" if horizontal else "y")
                        axes = source.findall(f".//{{{_SML}}}chartAxis[@type='{axis_type}']")
                        position = owner.find(f"{{{chart_namespace}}}axPos")
                        right = position is not None and position.get("val") == "r"
                        axis = next((axis for axis in axes if (axis.get("position") == "right") == right), None)
                        definition = axis.find(f"{{{_SML}}}chartLabel") if axis is not None else None
                    if definition is None or not definition.get("fontSize"):
                        raise ValueError(f"Native chart font definition is missing on page {page}")
                    actual = int(node.get("sz"))
                    service_size = float(definition.get("fontSize"))
                    desired = round(service_size * 150)
                    if service_size <= 1 or abs(actual - desired) <= 1:
                        replacements.append(actual)
                    elif abs(actual * 2 - desired) <= 1:
                        replacements.append(desired)
                    else:
                        raise ValueError(f"Unrecognized native chart font {actual} on page {page}")
                pattern = rb'(<(?:[\w.-]+:)?(?:defRPr|rPr|endParaRPr)\b[^>]*?\bsz=")(\d+)(")'
                matches = list(re.finditer(pattern, raw))
                if len(matches) != len(font_nodes):
                    raise ValueError("Native chart font serialization is ambiguous")
                sizes = iter(replacements)

                def replace_font(match):
                    nonlocal font_runs
                    old = int(match.group(2))
                    desired = next(sizes)
                    if old == desired:
                        return match.group(0)
                    font_runs += 1
                    return match.group(1) + str(desired).encode("ascii") + match.group(3)

                corrected = re.sub(pattern, replace_font, raw)
                chart_count += 1
                if corrected != raw:
                    if target in patches and patches[target] != corrected:
                        raise ValueError("Shared native chart has conflicting font definitions")
                    patches[target] = corrected
        if patches:
            descriptor, temporary = tempfile.mkstemp(suffix=".pptx", dir=Path(path).parent)
            os.close(descriptor)
            try:
                with zipfile.ZipFile(temporary, "w") as output:
                    output.comment = archive.comment
                    for member in archive.infolist():
                        output.writestr(member, patches.get(member.filename, archive.read(member.filename)))
                with zipfile.ZipFile(temporary) as output:
                    if output.testzip() is not None:
                        raise ValueError("Native chart font correction failed archive integrity")
                os.replace(temporary, path)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
    return {"charts": chart_count, "font_runs": font_runs}


TEMPLATE_CLOSE_WINDOW = 240   # s after the closing notice: a template Organizer not returned by then counts as timed out
TEMPLATE_GATE_MAX_AGE = 3 * 3600   # s: an open template dispatch older than this is a leftover (Main never closed it)


def _open_template_dispatch(cwd):
    """(path, record) of an open template-flow dispatch at cwd or up to 4 parents (Main may pass its WORK_DIR).
    Explicit assistance has its own file; the legacy global dispatch remains untouched."""
    for up in [Path(cwd).resolve(), *list(Path(cwd).resolve().parents)[:4]]:
        assist_path = _template_assist_dispatch_path(up)
        assist = _read(assist_path)
        if assist.get("flow") == "template" and assist.get("template_assist") and not assist.get("closed"):
            return assist_path, assist
        p = up / ".lark-slides" / "dispatch.json"
        if p.exists():
            d = _read(p)
            if d.get("flow") == "template" and not d.get("closed"):
                return p, d
            return None, {}
    return None, {}


def _template_work_dirs(root):
    """Template WORK_DIRs of this task (<root>/.lark-slides/template/*) plus root itself: where closing.json lives."""
    base = root / ".lark-slides" / "template"
    return [d for d in (sorted(base.iterdir()) if base.is_dir() else []) if d.is_dir()] + [root]


RETURN_SUMMARY = Path(".lark-slides") / "organizer" / "return-summary.md"


def _return_summary_paths(root):
    """Absolute paths where the template Organizer's return-summary.md is expected: <CWD>/.lark-slides/organizer/ and
    every <WORK_DIR>/.lark-slides/organizer/ (WORK_DIR = <CWD>/.lark-slides/template/<id>)."""
    return [str((d / RETURN_SUMMARY).resolve()) for d in [root] + _template_work_dirs(root)[:-1]]


def _return_summary(root, since):
    """Absolute path of a return-summary.md written after the dispatch — under <CWD>/.lark-slides/** (CWD itself and
    every WORK_DIR) or a parent's .lark-slides/organizer/ (dispatch run from a WORK_DIR) — else None."""
    found = list(root.glob(".lark-slides/**/organizer/return-summary.md"))
    found += [up / RETURN_SUMMARY for up in list(root.parents)[:3]]
    for f in found:
        try:
            if f.is_file() and f.stat().st_mtime >= since:
                return str(f.resolve())
        except OSError:
            continue
    return None


def _organizer_returned(root, since):
    """A return-summary.md (see _return_summary) written after the dispatch."""
    return _return_summary(root, since) is not None


def _summary_status(tg):
    paths = tg.get("expected") or []
    return ("Organizer 是否已 return：否（这些位置都还没有 return-summary.md："
            + "；".join(paths) + "）") if paths else ""


def _closing_since(dirs, since):
    """Earliest closing.json t (a notice already sent in this task) among the WORK_DIRs, or None."""
    ts = [float(_read(d / ".lark-slides" / CLOSING_FILE).get("t") or 0) for d in dirs]
    ts = [t for t in ts if t >= since - 5]
    return min(ts) if ts else None


def _template_export_gate(cwd, deck=None):
    """export by the template-flow Main while its Organizer has not returned. Returns None (export normally) or
    {"mode": "draft"|"wait"|"timeout", ...}. First export: allowed as the draft, and the closing notice (closing.json in
    every WORK_DIR, to everyone) is written if Main never ran notice. A later export within TEMPLATE_CLOSE_WINDOW of the
    notice is refused (wait_agent first); after it the Organizer counts as timed out and the export is the final.
    Explicit template_assist never drafts/times out: hand-off files must be current, and Main must independently
    confirm through the actual agent tools that all writers stopped before creating/accepting those files."""
    path, d = _open_template_dispatch(cwd)
    if not path:
        return None
    root, since = path.parent.parent, float(d.get("t") or 0)
    if d.get("template_assist"):
        # These files are a hand-off convention, not an agent API or a server
        # lock. New Main-owned requests invalidate a previous return summary.
        scopes = {}
        targets, unbound = set(), False
        for request in root.glob(".lark-slides/**/organizer/assignments/*.json"):
            try:
                stamp = request.stat().st_mtime
            except OSError:
                return {"mode": "assist_wait", "path": path, "rec": d,
                        "expected": _return_summary_paths(root)}
            if stamp >= since:
                # Explicit target identity keeps assistance for D from holding
                # another deck E. Unknown request identity remains fail closed.
                assignment = _read(request)
                target = assignment.get("deck_xml_presentation_id") if isinstance(assignment, dict) else None
                if isinstance(target, str) and target.strip():
                    targets.add(target)
                    if deck is not None and target != str(deck):
                        continue
                else:
                    unbound = True
                directory = request.parent.parent
                scopes[directory] = max(scopes.get(directory, since), stamp)
        if deck is not None and targets and str(deck) not in targets and not unbound:
            return None
        expected = [str((directory / "return-summary.md").resolve()) for directory in sorted(scopes)]
        if not scopes:
            expected = _return_summary_paths(root)
        summaries = []
        pending = []
        for filename in expected:
            summary = Path(filename)
            baseline = scopes.get(summary.parent, since)
            try:
                valid = summary.is_file() and summary.stat().st_mtime > baseline and bool(summary.read_text().strip())
            except (OSError, UnicodeError):
                valid = False
            if valid:
                summaries.append(filename)
            else:
                pending.append(filename)
        # Without requests, one current task summary is sufficient. With
        # requests, every assigned WORK_DIR must return after its latest request.
        if summaries and (not scopes or not pending):
            return {"mode": "returned", "path": path, "rec": d,
                    "summary": summaries[0], "summaries": summaries, "template_assist": True}
        return {"mode": "assist_wait", "path": path, "rec": d,
                "expected": pending or expected, "template_assist": True}
    if time.time() - since > TEMPLATE_GATE_MAX_AGE:   # legacy mode: a never-closed earlier turn
        return None
    summary = _return_summary(root, since)
    if summary:
        return {"mode": "returned", "path": path, "rec": d, "summary": summary}
    expected = _return_summary_paths(root)
    dirs = _template_work_dirs(root)
    closing = _closing_since(dirs, since)
    now = time.time()
    noticed = closing is None
    if noticed:   # Main skipped Step 6a: send the closing signal for it (the Organizer polls closing.json)
        for w in dirs:
            f = w / ".lark-slides" / CLOSING_FILE
            _write(f, {"to": _read(f).get("to") or [], "minutes": 3, "t": now})
        closing = now
    age = now - closing
    if age >= TEMPLATE_CLOSE_WINDOW:
        return {"mode": "timeout", "path": path, "rec": d, "expected": expected}
    if not d.get("draft_export"):
        return {"mode": "draft", "path": path, "rec": d, "noticed": noticed, "age": age, "expected": expected}
    return {"mode": "wait", "path": path, "rec": d, "left": int(TEMPLATE_CLOSE_WINDOW - age), "expected": expected}


def _keynote_bypass(cwd, deck, pptx):
    """Warning text when the deck is marked keynote (decks/<deck>/style) but keynote-shape.json (written by every
    publish_slide keynote write) records fewer pages than the exported PPTX has: pages went in via bare +add-slide."""
    d = Path(cwd) / ".lark-slides" / "decks" / str(deck)
    try:
        if (d / "style").read_text(encoding="utf-8").strip() != "keynote":
            return None
    except OSError:
        return None
    led = _read(d / "keynote-shape.json")
    seen = len([k for k in led if re.fullmatch(r"p\d+", k)]) if isinstance(led, dict) else 0
    try:
        import zipfile
        with zipfile.ZipFile(pptx) as z:
            total = len([n for n in z.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)])
    except Exception:  # noqa: BLE001
        total = None
    if total is None and seen:
        return None
    if total is not None and seen >= total:
        return None
    return (f"警告：页面绕过了 publish_slide keynote 检查（deck 标记为 keynote，keynote-shape.json 只记了 {seen} 页"
            + (f"，PPTX 有 {total} 页" if total is not None else "") + "）——这些页是裸 +add-slide 写的，没有过 keynote 门禁")


MUST_MISSING_HOLD = 3   # keynote BP / 招商 deck missing ≥ this many must-have items: export refused once (a hint alone gets ignored)


def _must_missing_hold(cwd, deck):
    """(message, gaps) the first time a keynote BP / 招商 deck is exported with ≥ MUST_MISSING_HOLD must-have items in no
    page; the same export run again goes through. None otherwise (any error: never blocks)."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from svg_lib.atomize_svg_to_slide._publish import _must_missing
        label, gaps = _must_missing(cwd, str(deck))
        mark = Path(cwd) / ".lark-slides" / "decks" / str(deck) / "held-must-missing"
        if len(gaps) < MUST_MISSING_HOLD or mark.exists():
            return None
        mark.parent.mkdir(parents=True, exist_ok=True)
        mark.write_text("1", encoding="utf-8")
    except Exception:  # noqa: BLE001
        return None
    return (f"未导出（只拦这一次）：{label}缺 {len(gaps)} 项必含内容：{'、'.join(gaps)}——每项补 1 页（publish_slide insert=True 插到"
            "相应位置），查不到的写成屏上'示例 / 待补充'页，不只写进讲稿；补完或确认不补后再运行同一条 export", gaps)


def _template_registry_gate(cwd, deck):
    """Check template write acknowledgements against a fresh remote page list.

    Other deck workflows are untouched. A matching template index or publisher
    ledger selects this contract; no file or remote page is mutated here.
    """
    root = Path(cwd).resolve()
    deck = str(deck)
    candidates = set()
    for path in root.rglob('template-index.json'):
        data = _read(path)
        if not isinstance(data, dict):
            continue
        binding = ((data.get('lark') or {}).get('deck') or {}).get('xml_presentation_id')
        if str(binding) == deck:
            candidates.add(path.parent.parent)
    for filename in ('published-pages.json', 'published-pages.pending.json'):
        for path in root.rglob(filename):
            data = _read(path)
            if not isinstance(data, dict) or not isinstance(data.get('presentation'), str) or not data['presentation'].strip():
                return {'ok': False, 'code': 'template_registry_invalid', 'path': str(path),
                        'next': 'Publisher state has no trustworthy deck identity. Reconcile this file from saved '
                                'write reports and remote readback; do not remove it to bypass export checks.'}
            if data['presentation'] == deck:
                candidates.add(path.parent)
    if not candidates:
        return None
    def failure(code, **detail):
        return {'ok': False, 'code': code, **detail,
                'next': 'Do not export or delete pages to bypass this check. Read the current deck, '
                        'reconcile pending writes, and publish each planned page with template_publish.py; '
                        'then rerun the same export.'}
    if len(candidates) != 1:
        return failure('template_registry_ambiguous', work_dirs=[str(p) for p in sorted(candidates)])
    work = next(iter(candidates))
    if (work / 'published-pages.pending.json').exists():
        return failure('template_publish_pending', work_dir=str(work))
    ledger = work / 'published-pages.json'
    if not ledger.exists():
        return failure('unregistered_pages', work_dir=str(work))
    try:
        try:
            from .template.template_publish import _registry
        except ImportError:
            from template.template_publish import _registry
        state = _registry(ledger, deck)
        rows = sorted(state['pages'], key=lambda r: r['page'])
        numbers = [r['page'] for r in rows]
        if not rows or numbers != list(range(1, len(rows) + 1)):
            return failure('template_plan_incomplete', registered_pages=numbers)
        plan = _read_text(work / 'page-plan.md')
        planned = sorted({int(n) for n in re.findall(r'(?m)^\|\s*P(\d+)\s*\|', plan)})
        if planned and planned != numbers:
            return failure('template_plan_incomplete', planned_pages=planned, registered_pages=numbers)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        return failure('template_registry_invalid', error=str(exc))
    result = _cli(['slides', '+xml-get', '--presentation', deck], str(root))
    if not isinstance(result, dict) or result.get('ok') is not True:
        return failure('template_readback_failed', response=result)
    returned_deck = (result.get('data') or {}).get('xml_presentation_id')
    if returned_deck and str(returned_deck) != deck:
        return failure('template_readback_wrong_deck', expected=deck, actual=returned_deck)
    try:
        actual = [sid for sid, _ in _pub()._deck_slides(result)]
    except Exception as exc:
        return failure('template_readback_failed', error=str(exc))
    expected = [r['slide_id'] for r in rows]
    if actual != expected:
        return failure('template_registry_mismatch', expected_slide_ids=expected,
                       actual_slide_ids=actual,
                       unregistered_slide_ids=[sid for sid in actual if sid not in expected],
                       missing_slide_ids=[sid for sid in expected if sid not in actual])
    return None


def export(deck, cwd=".", name=None, who=None, url=None, title=None, pages=None, notes=None, gaps=None, strict=False):
    """export --deck D --cwd C: the Lead's final export (single-agent / template / asset paths alike) — drive +export
    PPTX, then for a Lead (who=lead, or no live dispatch) write <cwd>/.lark-slides/decks/<deck>/FINAL_REPLY.md (= lead-return text)
    and return it as final_reply. Main (who=main with a live dispatch) only gets the PPTX path. Template-flow Main
    whose Organizer has not returned yet: see _template_export_gate (legacy draft/wait/timeout; optional assistance
    blocks until current hand-off evidence, regardless of the caller's who label).
    Template registry/plan/readback warnings permit a review draft by default;
    strict=True preserves the original registry blocking."""
    cwd = str(Path(cwd).resolve())
    registry_failure = _template_registry_gate(cwd, deck)
    if registry_failure and (strict or registry_failure.get('code') == 'template_readback_wrong_deck'):
        return registry_failure
    identity_diagnostic = None
    if registry_failure:
        # Metadata warnings may return before readback. A failed aggregate read
        # is diagnostic; only a proven wrong returned identity blocks export.
        response = registry_failure.get('response')
        if registry_failure.get('code') not in ('template_registry_mismatch', 'template_readback_failed'):
            response = _cli(['slides', '+xml-get', '--presentation', deck], cwd)
        if isinstance(response, dict):
            data = response.get('data')
            actual_deck = data.get('xml_presentation_id') if isinstance(data, dict) else None
            if actual_deck and str(actual_deck) != str(deck):
                return {'ok': False, 'code': 'template_readback_wrong_deck',
                        'expected': str(deck), 'actual': actual_deck, 'registry_advisory': registry_failure}
            if response.get('ok') is not True:
                identity_diagnostic = response

    def review_result(out):
        if registry_failure and out.get('ok'):
            out.update(registry_advisory=registry_failure, draft=True, needs_final_review=True)
            if identity_diagnostic is not None:
                out['identity_readback_advisory'] = identity_diagnostic
            note = '复核稿已导出；登记、计划或回读尚未核对，不能据此认定内容和视觉已完成。最终仍需核对实际页面。'
            out['next'] = note + (out.get('next', '') if tg else '')
        return out
    tg = _template_export_gate(cwd, deck)
    if who in ("lead", "solo") and tg and not tg.get("template_assist"):
        tg = None
    if tg and tg["mode"] == "assist_wait":
        return {"ok": False, "code": "template_assist_pending", "organizer_pending": True,
                "organizer_returned": False, "return_summary_expected": tg["expected"],
                "next": ("未导出：本轮模板专项派单尚无有效交回报告。先停止 Organizer 及其所有 draft writer，"
                         "用实际 wait_agent/return 确认停止并归还指定页，再 Read 最新 return-summary.md、处理未完成项后重跑。"
                         "报告须晚于当前 dispatch 和该 WORK_DIR 最新 assignments/*.json；这是交接证据，不是服务端锁。"
                         "首次导出也不算 draft，超时不放行；不提前 dispatch --close，不用 drive +export 绕过。")}
    if tg and tg["mode"] == "wait":
        return {"ok": False, "organizer_pending": True, "organizer_returned": False,
                "return_summary_expected": tg["expected"],
                "next": (f"未导出：Organizer 还没 return，收尾窗口还剩约 {tg['left']} 秒。{_summary_status(tg)}。"
                         "先 wait_agent(wait_timeout=120) 接住它的 return（至多两次；不要用 sleep / Wait 代替），"
                         "Read return-summary.md 做 Step 7 兜底后再运行同一条 export 出终稿；"
                         "不要用 drive +export 绕过，不要提前 shutdown / kill Organizer")}
    must = _must_missing_hold(cwd, deck)
    if must:
        return {"ok": False, "must_missing": must[1], "next": must[0]}
    out = _export_pptx(deck, cwd, name)
    if not out["ok"]:
        if registry_failure:
            out['registry_advisory'] = registry_failure
        out["next"] = "导出失败：原样重跑同一条 export 一次"
        return out
    bypass = _keynote_bypass(cwd, deck, out.get("pptx"))
    if bypass:
        out["keynote_bypass"] = bypass
        print(bypass, file=sys.stderr)
    if _edit_dirs(cwd, deck):   # end of a reopened edit turn: exported + seal again (the next follow-up needs reopen again)
        _close_edit_turn(cwd, out.get("pptx"), deck)
        out["edit_turn_closed"] = True
    lead = who == "lead" or (who not in ("main", "solo") and _no_main(cwd))
    url = url or _deck_url(None, cwd, deck)
    if url:
        out["url"] = url
        _remember_url(cwd, deck, url)
    _mark_deck_exported(cwd, deck, out.get("pptx"))
    if who == "solo":   # single-agent deck: PPTX in the CWD root + url.txt + exported marker; delivery per SKILL.md
        look = _final_look(deck, cwd)
        out.update(look)
        pages = look.get("look") or []
        head = (("终检已代做（一次回读）：只看 look 列出的 %d 页%s；真有问题改那一页后重跑一次本命令，否则" %
                 (len(pages), "（截图路径在 screenshots）" if look.get("screenshots") else ""))
                if pages else "终检已代做（一次回读），没有需要看的页：")
        if look.get("cross_page"):
            head = look["cross_page"] + "。" + head
        out["next"] = (head + "直接 present_files 同时交付链接与 PPTX" + (f"（链接 {url}）" if url else
                       "（没找到 deck 链接：带 --url \"<+create 返回的 url>\" 重跑一次，或交付时用 +create 返回的 url）")
                       + "，回复里附制作介绍。不解包、不查 verifier、不另行全量截图，不再另跑 drive +export")
        return review_result(out)
    if tg and tg["mode"] == "returned":
        out["organizer_returned"] = True
        out["return_summary"] = tg["summary"]
        out["return_summary_note"] = f"Organizer 已 return：先 Read {tg['summary']}，处理其中未修复的 P0 再交付"
        if tg.get("template_assist"):
            out["return_summaries"] = tg["summaries"]
            out["requires_writer_confirmation"] = True
            out["return_summary_note"] = ("已找到本轮交回报告（文件是交接证据，不是服务端锁）："
                                          "须已用实际 wait_agent/return 确认所有 writer 停止并归还页；"
                                          "先 Read " + "；".join(tg["summaries"]) + "，处理未完成项再交付")
    if tg and tg["mode"] == "draft":   # template Main's first export while the Organizer is still reviewing
        rec = dict(tg["rec"], draft_export=time.time())
        _write(tg["path"], rec)
        out["draft"] = True
        out["organizer_pending"] = True
        if tg.get("noticed"):
            out["closing_written"] = True
        out["organizer_returned"] = False
        out["return_summary_expected"] = tg["expected"]
        out["next"] = (("你没跑 notice：已代写 closing.json（Organizer 每轮 poll 读到即收尾）。" if tg.get("noticed") else "")
                       + "这份是初稿（Organizer 还没 return，它之后的修复不在这份 PPTX 里）：present_files 交付初稿"
                       + (f"（链接 {url}）" if url else "") + " → wait_agent(wait_timeout=120) 接住 Organizer 的 return"
                       "（至多两次）→ Read return-summary.md 做 Step 7 兜底 → 再运行同一条 export 出终稿并二次 present_files"
                       " → dispatch --cwd <CWD> --close。现在不 dispatch --close、不 shutdown / kill Organizer、不用 drive +export"
                       "、不用 sleep / Wait 代替 wait_agent。" + _summary_status(tg))
        return review_result(out)
    if tg and tg["mode"] == "timeout":
        out["organizer_timed_out"] = True
    if not lead:   # Main with a live dispatch: deliver, close the dispatch (only while it is open)
        open_ = bool(tg and tg.get("template_assist")) or not _no_main(cwd)
        close_command = ("dispatch --cwd <CWD> --flow template --template-assist --close"
                         if tg and tg.get("template_assist") else "dispatch --cwd <CWD> --close")
        out["next"] = ((out["return_summary_note"] + " → " if out.get("return_summary_note") else "")
                       + "用一次 present_files 同时交付 PPTX 与链接" + (f"（链接 {url}）" if url else "（链接用 +create 返回的 url）")
                       + (" → " + close_command if open_ else "")
                       + (" → Organizer 收尾超时仍没 return：send_message 它 shutdown（只这一次，不等回复）" if tg and tg["mode"] == "timeout" else ""))
        return review_result(out)
    if registry_failure:
        return review_result(out)
    if pages is None:
        reg = _read(Path(cwd) / ".lark-slides" / f"pages-{deck}.json")
        pages = len([k for k in reg if re.fullmatch(r"p\d+", k)]) or None
    role_ = "lead" if who == "lead" or not _dispatch_path(cwd).exists() else "closer"   # a Main once owned this deck
    text = lead_return(title or name or Path(out["pptx"]).stem, pages if pages is not None else "N",
                       url, out["pptx"], notes, gaps, who=role_)
    fr = _write_final_reply(cwd, deck, text)
    out.update(final_reply=text, final_reply_file=str(fr), next=FINAL_REPLY_NEXT + "（cat final_reply_file 给的路径）" + NOTES_RERUN
               + ("" if url else "（没找到 deck 链接，final_reply 里只有 PPTX：带 --url \"<+create 返回的 url>\" 重跑 export）"))
    return out


LOOK_SHOTS = 8   # one +screenshot call takes at most 8 slide ids


def _final_look(deck, cwd):
    """export --who solo's final check: one +xml-get read-back → pages worth a look (server lint errors / warnings not
    judged at write time, text laid over a picture, picture pages) plus pages whose last publish carried warnings
    (decks/<deck>/warned.json), and one +screenshot of up to LOOK_SHOTS of them. Read-back unavailable → the publish
    ledger alone. Returns {"look": [{page, slide_id, why}], "screenshots": [paths]} (keys only when non-empty)."""
    pub = _pub()
    _, registry = pub._page_registry(cwd, deck)
    by_id = {v: int(k[1:]) for k, v in registry.items() if re.fullmatch(r"p\d+", k)}
    warned = _read(Path(cwd) / ".lark-slides" / "decks" / str(deck) / "warned.json")
    why = {}   # page -> reasons
    xp = []
    for k, v in (warned.items() if isinstance(warned, dict) else []):
        if re.fullmatch(r"p\d+", k):
            why.setdefault(int(k[1:]), []).extend(v if isinstance(v, list) else [str(v)])
    sids = {p: registry.get(f"p{p:02d}") for p in why}
    res = _cli(["slides", "+xml-get", "--presentation", deck], cwd)
    slides = pub._deck_slides(res) if isinstance(res, dict) and res.get("ok") else []
    if slides:
        nolint = {int(k[1:]): v for k, v in _read(Path(cwd) / ".lark-slides" / f"nolint-{deck}.json").items()
                  if re.fullmatch(r"p\d+", k)}
        try:
            here = str(Path(__file__).resolve().parent)
            if here not in sys.path:
                sys.path.insert(0, here)
            import lint_inspect
            rows = lint_inspect.Inspector(res).rows
        except Exception:  # noqa: BLE001
            rows = []
        order = [sid for sid, _ in slides]
        for r in rows:
            if r.get("level") not in ("error", "warning"):
                continue
            sid, num = r.get("slide_id"), r.get("slide_number")
            if not sid and isinstance(num, int) and 0 < num <= len(order):
                sid = order[num - 1]
            if not sid:
                continue
            page = by_id.get(sid, order.index(sid) + 1 if sid in order else None)
            code = r.get("code") or "lint"
            if page is None or _nolint_waives(nolint.get(page), code, r.get("issue"), None):
                continue
            why.setdefault(page, []).append(f"{r['level']} {code}")
            sids[page] = sid
        try:
            xp = cross_page_conflicts(_slide_texts({by_id.get(sid, i): body for i, (sid, body) in enumerate(slides, 1)}))
        except Exception:  # noqa: BLE001 — a hint only
            xp = []
        if xp:
            out_xp = CROSS_PAGE_MSG.format(items="；".join(xp))
        for i, (sid, body) in enumerate(slides, 1):
            page = by_id.get(sid, i)
            kinds = _picture_kinds(body)
            if kinds:
                why.setdefault(page, []).extend(kinds)
                sids[page] = sid
    look = [{"page": p, "slide_id": sids.get(p) or registry.get(f"p{p:02d}") or "",
             "why": list(dict.fromkeys(why[p]))[:4]} for p in sorted(why)]
    out = {"look": look} if look else {}
    if slides and xp:
        out["cross_page"] = out_xp
    if not slides:
        out["look_source"] = "回读失败，只按 publish 台账（有 warning 的页）列出"
    ids = [x["slide_id"] for x in look if x["slide_id"]][:LOOK_SHOTS]
    if ids:
        args = ["slides", "+screenshot", "--as", "user", "--presentation", deck, "--output-dir",
                ".lark-slides/screenshots/final"]
        for sid in ids:
            args += ["--slide-id", sid]
        shot = _cli(args, cwd)
        found = re.findall(r'"([^"]+\.(?:png|jpe?g))"', json.dumps(shot.get("data") or {}, ensure_ascii=False)) \
            if isinstance(shot, dict) and shot.get("ok") else []
        if found:
            out["screenshots"] = [str(Path(cwd) / f) if not Path(f).is_absolute() else f for f in dict.fromkeys(found)]
    return out


def _picture_kinds(body):
    """["文字压图"] / ["图片页"] for a read-back slide body: an <img> ≥ 8% of the 960×540 canvas makes a picture page;
    a text box whose box intersects such a picture is text over the picture."""
    def box(attrs):
        try:
            return tuple(float(re.search(rf'\b{k}="(-?[\d.]+)"', attrs).group(1))
                         for k in ("topLeftX", "topLeftY", "width", "height"))
        except (AttributeError, ValueError):
            return None
    pics = [b for b in (box(a) for a in re.findall(r"<img\b([^>]*)", body or "")) if b and b[2] * b[3] >= 0.08 * 960 * 540]
    if not pics:
        return []
    texts = [b for a, inner in re.findall(r'<shape\b([^>]*)>(.*?)</shape>', body, re.S)
             if re.sub(r"<[^>]+>", "", inner).strip() and (b := box(a))]
    over = any(t[0] < p[0] + p[2] and p[0] < t[0] + t[2] and t[1] < p[1] + p[3] and p[1] < t[1] + t[3]
               for t in texts for p in pics)
    return ["文字压图"] if over else ["图片页"]


NOTES_RERUN = ("派单要求的额外字段（核心结论、验证方式等）写进 notes 文件，带 --notes-file 重跑 export / lead-return，"
               "不要自写回复")


FINAL_REPLY_NEXT = ("用一次 present_files 交付链接与 PPTX 后，把 final_reply 原样作为最后一条回复（前后不加字）——"
                    "final_reply 就是 lead-return 的完整输出（也存在 final_reply_file 那个路径），"
                    "不必再跑 lead-return。" + FINAL_REPLY_RULE)


URL_FILE = "url.txt"   # <cwd>/.lark-slides/decks/<deck>/url.txt: the deck's link, kept for follow-up turns


def _mark_deck_exported(cwd, deck, pptx):
    """<cwd>/.lark-slides/decks/<deck>/exported = the exported PPTX path (every export, solo decks included)."""
    try:
        d = Path(cwd).resolve() / ".lark-slides" / "decks" / str(deck)
        d.mkdir(parents=True, exist_ok=True)
        (d / "exported").write_text(str(pptx or ""), encoding="utf-8")
    except OSError:
        pass


def _deck_roots(cwd):
    """Dirs whose .lark-slides may hold this deck's records: cwd, its parents (a follow-up run from a subdir) and its
    children / grandchildren (a follow-up run from the parent)."""
    root = Path(cwd).resolve()
    out = [root] + list(root.parents)[:4]
    for pat in ("*/.lark-slides", "*/*/.lark-slides"):
        try:
            out += sorted(p.parent for p in root.glob(pat) if p.is_dir())
        except OSError:
            pass
    return list(dict.fromkeys(out))


def _url_ok(tok, deck=None):
    return tok.startswith("http") and (not deck or "/slides/" not in tok or _pub()._deck_id(tok) == str(deck))


def _remember_url(cwd, deck, url):
    """Persist the deck URL into <cwd>/.lark-slides/decks/<deck>/url.txt (best effort, never raises)."""
    if not (cwd and deck and url and str(url).startswith("http")):
        return
    try:
        d = Path(cwd).resolve() / ".lark-slides" / "decks" / str(deck)
        d.mkdir(parents=True, exist_ok=True)
        if _read_text(d / URL_FILE).strip() != str(url):
            (d / URL_FILE).write_text(str(url), encoding="utf-8")
    except OSError:
        pass


def _deck_url(directory, cwd, deck):
    """The URL of this deck, in order: a deck.txt (SYNC/deck.txt, <cwd>/.lark-slides/decks/<deck>/deck.txt or
    <cwd>/.lark-slides/deck.txt) whose first token is this deck and that also records an http URL; a url.txt /
    deck.txt of this deck under .lark-slides/decks/<deck>/ in cwd, its parents or children (follow-up turns run from
    another dir); else https://<domain>/slides/<deck> built from any other slides URL recorded there (same tenant).
    A URL found this way is persisted into <cwd>/.lark-slides/decks/<deck>/url.txt."""
    files = ([Path(directory) / "deck.txt"] if directory else []) + [
        Path(cwd) / ".lark-slides" / "decks" / str(deck) / "deck.txt", Path(cwd) / ".lark-slides" / "deck.txt"]
    for f in files:
        toks = _read_text(f).split()
        if toks and deck and toks[0] != str(deck) and not toks[0].rstrip("/").endswith(str(deck)):
            continue   # another deck's record
        for tok in toks:
            if _url_ok(tok, deck):
                _remember_url(cwd, deck, tok)
                return tok
    if not deck:
        return None
    roots = _deck_roots(cwd)
    for r in roots:
        dd = r / ".lark-slides" / "decks" / str(deck)
        for f in (dd / URL_FILE, dd / "deck.txt"):
            for tok in _read_text(f).split():
                if _url_ok(tok, deck):
                    _remember_url(cwd, deck, tok)
                    return tok
    for r in roots:   # same tenant: any recorded slides URL gives the domain
        lsd = r / ".lark-slides"
        for f in sorted(lsd.glob(f"decks/*/{URL_FILE}")) + sorted(lsd.glob("decks/*/deck.txt")) + [lsd / "deck.txt"]:
            for tok in _read_text(f).split():
                m = re.match(r"(https?://[^/\s]+)/slides/", tok)
                if m:
                    url = f"{m.group(1)}/slides/{deck}"
                    _remember_url(cwd, deck, url)
                    return url
    return None



def _front_stale(directory, want, bodies, registry):
    """finish, once: the contents / summary pages (Main pages after the cover) read back from the deck, checked against
    plan.py's F-filled titles (page 0) and every other page — front_page_fixes. [] on any error (a hint, never a block)."""
    try:
        front = tuple(sorted(set(_main_pages(directory)) | _nav_pages(directory)))   # cover KPIs, contents, summary, navs
        texts = _slide_texts({p_: bodies.get(registry.get(f"p{p_:02d}", ""), "") for p_ in want})
        plan_txt = _plan_fact_text(directory)
        if plan_txt:
            texts[0] = plan_txt
        out = front_page_fixes(texts, front) if front else []
        apx = {k for k, v in texts.items() if k and re.match(r"\s*(?:附录|Appendix)", v[:40], re.I)}
        return out + body_page_fixes({k: v for k, v in texts.items() if k not in apx}, skip=set(front))
    except Exception:  # noqa: BLE001
        return []


def _plan_clash(fix):
    """A front/body fix whose reference is plan.py F and whose number is ≥ 2 % away from it."""
    if not (fix.get("new") and str(fix.get("where", "")).startswith("plan.py")):
        return False
    num = lambda t: [float(v.replace(",", "")) for v in re.findall(r"\d[\d,]*(?:\.\d+)?", str(t))]   # noqa: E731
    a, b = num(fix.get("old")), num(fix.get("new"))
    if not a or not b:
        return False
    return abs(a[0] - b[0]) / max(abs(a[0]), abs(b[0]), 1e-12) >= 0.02


def _summary_numbers(cwd, page=3):
    """Numbers with a unit in the summary page XML that no other page carries: stale targets after plan_final."""
    xd = Path(cwd) / ".lark-slides" / "xml"
    p3 = xd / f"p{page:02d}.xml"
    if not p3.exists():
        return []
    txt = lambda f: re.sub(r"<[^>]+>", " ", f.read_text(encoding="utf-8")).replace(",", "")
    rest = " ".join(txt(f) for f in sorted(xd.glob("p*.xml")) if f.name not in {f"p{i:02d}.xml" for i in range(1, page + 1)})
    if not rest.strip():
        return []
    unit = r"(?:亿|万|%|pct|pts|pp|bp|倍|家|店|GW|MW|tn|bn|mn|[mMbBkK]\b|x\b)"
    out = []
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*(" + unit + ")", txt(p3)):
        num, u = m.group(1), m.group(2)
        if len(num) == 4 and num.startswith("20"):
            continue
        if not re.search(r"(?<![\d.])" + re.escape(num) + r"(?![\d])", rest):
            out.append(f"{num}{u}")
    return list(dict.fromkeys(out))


def cross_page_conflicts(pages, limit=6):
    """Warnings (never blocks): pages = {page: visible text} (page 0 = plan.py titles, see _plan_fact_text). The same
    metric + scope + period carrying different values on different pages, units converted (百万/亿/十亿/万) — ≥ 1 %
    apart (5 % when either says 约/超) and not equal at the precision either side is written in; a range conflicts only
    with a value outside it. Scope = the nearest deck name (a token standing alone on ≥ 2 pages — brand, segment,
    country — or a title subject "屈光：") before the number in its clause, else the page title's single name: two
    segments' 毛利率 or two brands' CAGR are different metrics. Plus a full-year forecast below a part-year actual."""
    out = [g["text"] for g in _xp_groups(pages)]
    return list(dict.fromkeys(out))[:limit]


def _xp_groups(pages):
    """Structured cross_page_conflicts: [{text, name, per, first: {page: mention}, bad: {pages}}] (forecast-vs-actual
    findings carry first/bad = {} — nothing to copy from one page to another)."""
    pages = {int(k): str(v or "") for k, v in pages.items()}
    vocab = _xp_vocab(pages)
    segs = _xp_segments(pages)
    subj = _xp_subjects(pages, [nm for nm in vocab if not any(nm in g or g in nm for g in segs)])
    seen, out = {}, []
    for pg, text in sorted(pages.items()):
        for mt in _xp_mentions(text, vocab, segs):
            if mt["scope"] in subj or mt["metric"] in _XP_STRICT:
                mt["scope"] = ""
            seen.setdefault((mt["metric"], mt["scope"], mt["kind"]), []).append(dict(mt, pg=pg))
    for (metric, scope, kind), hits in seen.items():
        name = (f"{scope}·" if scope else "") + metric + {"pct": "（%）", "x": "（倍）"}.get(kind, "")
        by_per = {}
        for h in hits:
            by_per.setdefault(h["per"], []).append(h)
        for per, hs in by_per.items():
            first = {}
            for h in hs:   # first mention per page; a page disagreeing with itself is its own table
                first.setdefault(h["pg"], h)
            ps = sorted(first)
            bad = set()
            for i, a in enumerate(ps):
                for b in ps[i + 1:]:
                    if _xp_differ(first[a], first[b]):
                        bad |= {a, b}
            if bad:
                out.append(dict(text=f"{name}{' ' + per if per else ''}：" + " vs ".join(
                    f"{_xp_page(p)} {first[p]['raw']}" for p in sorted(bad)), name=name, per=per, first=first, bad=bad))
        for per, hs in by_per.items():
            if not per.endswith("E") or kind in ("pct", "x"):
                continue
            for part in (k for k in by_per if k.startswith(per[:4]) and k[4:] in ("H1", "H2", "9M", "Q1", "Q2", "Q3", "Q4")):
                f_ = min(hs, key=lambda h: h["val"])
                a_ = max(by_per[part], key=lambda h: h["val"])
                if a_["val"] > f_["val"]:
                    out.append(dict(text=f"{name} 预测 {per} {f_['num']:g}（{_xp_page(f_['pg'])}）低于实绩 {part} "
                                         f"{a_['num']:g}（{_xp_page(a_['pg'])}）", name=name, per=per, first={}, bad=set()))
    return out


def front_page_fixes(pages, front=(2, 3)):
    """Executive summary / TOC pages (written first) still carrying a number the deck later changed: for each conflict
    group that involves a front page, the value the rest of the deck agrees on (plan.py's when it has one, else the
    value most body pages print). Returns [{page, metric, old, new, where}] — new is "" when the body itself disagrees."""
    import collections
    fixes = []
    for g in _xp_groups(pages):
        mine = [p for p in sorted(g["bad"]) if p in front]
        if not mine:
            continue
        rest = {p: h for p, h in g["first"].items() if p not in front}
        if not rest:
            continue
        if 0 in rest:
            ref = rest[0]
            where = ["plan.py"] + [_xp_page(p) for p, h in rest.items() if p and not _xp_differ(h, ref)]
        else:
            votes = collections.Counter(round(h["val"], 6) for h in rest.values())
            top, n = votes.most_common(1)[0]
            if n < 2 and len(rest) > 1:
                ref, where = None, []
            else:
                ref = next(h for h in rest.values() if round(h["val"], 6) == top)
                where = [_xp_page(p) for p, h in rest.items() if not _xp_differ(h, ref)]
        for p in mine:
            if ref is not None and not _xp_differ(g["first"][p], ref):
                continue
            fixes.append(dict(page=p, metric=g["name"] + (f" {g['per']}" if g["per"] else ""), old=g["first"][p]["raw"],
                              new=ref["raw"] if ref is not None else "", where="/".join(where[:4])))
    return fixes


def body_page_fixes(pages, skip=(), limit=4):
    """Body pages printing a number the rest of the deck disagrees with: for each conflict group, the value plan.py
    (page 0) gives, else the value ≥ 2 other pages agree on while this page is alone with its number. Pages in skip
    (front pages, handled by front_page_fixes) are left out. Returns [{page, metric, old, new, where}], ≤ limit pages."""
    import collections
    fixes, seen = [], set()
    for g in _xp_groups(pages):
        for p in sorted(g["bad"]):
            if p == 0 or p in skip or p in seen:
                continue
            mine = g["first"][p]
            rest = {q: h for q, h in g["first"].items() if q != p and q not in skip}
            if 0 in rest:
                ref, where = rest[0], ["plan.py"]
            else:
                votes = collections.Counter(round(h["val"], 6) for h in rest.values())
                if not votes:
                    continue
                top, n = votes.most_common(1)[0]
                same = sum(1 for h in rest.values() if not _xp_differ(h, mine))
                if same >= n or (n < 2 and p != max(g["bad"])):
                    continue   # no majority: only the last of the disagreeing pages is reopened, to pick one number
                ref = next(h for h in rest.values() if round(h["val"], 6) == top) if n >= 2 else None
                where = [_xp_page(q) for q, h in rest.items() if ref is not None and not _xp_differ(h, ref)]
            if ref is None:
                seen.add(p)
                fixes.append(dict(page=p, metric=g["name"] + (f" {g['per']}" if g["per"] else ""), old=mine["raw"], new="",
                                  where="/".join(f"{_xp_page(q)} {h['raw']}" for q, h in list(rest.items())[:3])))
                continue
            if not _xp_differ(mine, ref):
                continue
            seen.add(p)
            unscoped = "·" not in g["name"] and 0 not in rest   # no subject on the metric: it may be another company's
            fixes.append(dict(page=p, metric=g["name"] + (f" {g['per']}" if g["per"] else ""), old=mine["raw"],
                              new="" if unscoped else ref["raw"],
                              where="/".join(where[:4]) + ("（主体未写明：先核对两页说的是不是同一家/同一口径，是才改）"
                                                         if unscoped else "")))
    pages_ = []
    for f_ in fixes:
        if f_["page"] not in pages_:
            pages_.append(f_["page"])
    keep = set(pages_[:limit])
    return [f_ for f_ in fixes if f_["page"] in keep]


def _xp_page(p):
    return "plan.py" if int(p) == 0 else f"P{p}"


_XP_SCALE = {"万亿": 1e12, "十亿": 1e9, "亿": 1e8, "千万": 1e7, "百万": 1e6, "万": 1e4, "K": 1e3, "M": 1e6, "Mn": 1e6,
             "mn": 1e6, "B": 1e9, "bn": 1e9}
_XP_CUR = {"元": "CNY", "人民币": "CNY", "美元": "USD", "港元": "HKD", "欧元": "EUR", "日元": "JPY", "円": "JPY", "€": "EUR", "£": "GBP"}
_XP_NUM = re.compile(
    r"(?P<sign>[+\-−]?)(?P<num>\d[\d,]*(?:\.\d+)?)(?:\s*(?:%|亿|万)?\s*(?P<rng>[–~～])\s*(?P<num2>\d[\d,]*(?:\.\d+)?))?"
    r"\s*(?P<scale>万亿|十亿|千万|百万|亿|万|Mn|mn|bn|K(?![A-Za-z])|M(?![A-Za-z])|B(?![A-Za-z]))?\s*(?P<cur>人民币|美元|港元|欧元|日元|円|元)?"
    r"\s*(?P<unit>%|pct|pp|pt|个百分点|bps?|BPS?|倍|x(?![A-Za-z])|X(?![A-Za-z])|家|店|人次|台|架|杯|吨|例|个月|年(?![度化均内])|间|EFLOPS|PFLOPS|GWh|GW|MW|TWh)?")
_XP_HEADS = [("GMV", "GMV"), ("成交额", "GMV"), ("股价", "股价"), ("Share price", "股价"), ("share price", "股价"), ("spot", "股价"),
             ("单车净利润", "单车净利"), ("单车净利", "单车净利"), ("单车利润", "单车净利"), ("自供率", "自供率"), ("自给率", "自供率"),
             ("国产化率", "国产化率"), ("海外销量", "海外销量"), ("出口量", "海外销量"), ("销量", "销量"), ("出货量", "出货量"),
             ("研发费用率", "研发费用率"), ("研发投入", "研发投入"), ("复购率", "复购率"), ("流失率", "流失率"), ("退货率", "退货率"),
             ("市值", "市值"), ("股息率", "股息率"), ("PE", "PE"), ("市盈率", "PE"),
             ("单店投资", "单店投资"), ("单店投入", "单店投资"), ("开店投资", "单店投资"), ("回本期", "回本期"), ("回本周期", "回本期"),
             ("门店目标", "门店数"), ("门店数", "门店数"), ("开店数", "门店数"),
             ("gross margin", "毛利率"), ("operating margin", "经营利润率"), ("net margin", "净利率"), ("EBITDA margin", "EBITDA率"),
             ("service revenue", "服务收入"), ("Service revenue", "服务收入"), ("revenue", "收入"), ("Revenue", "收入"),
             ("net income", "净利"), ("Net income", "净利"), ("backlog", "订单储备"), ("Backlog", "订单储备"),
             ("bookings", "订单额"), ("Bookings", "订单额"), ("market share", "份额"), ("Market share", "份额"),
             ("price target", "目标价"), ("Price target", "目标价"), ("target price", "目标价"), ("Target price", "目标价"),
             ("损耗率", "损耗率"), ("费用率", "费用率"), ("坪效", "坪效"), ("日均销售", "日均销售"), ("同店", "同店增速"),
             ("LTV/CAC", "LTV/CAC"), ("LTV / CAC", "LTV/CAC"), ("ARPU", "ARPU"), ("CAC", "CAC"), ("NRR", "NRR"),
             ("ADR", "ADR"), ("RevPAR", "RevPAR"), ("入住率", "入住率"), ("出租率", "入住率"), ("Occ", "入住率"),
             ("NOI率", "NOI率"), ("NOI margin", "NOI率"), ("回收期", "回本期"), ("投资回收期", "回本期"), ("payback", "回本期"),
             ("恢复率", "恢复率"), ("收购金额", "收购对价"), ("收购对价", "收购对价"), ("交易对价", "收购对价"),
             ("IRR", "IRR"), ("内部收益率", "IRR"), ("EBITDA", "EBITDA"),
             ("capex", "资本开支"), ("Capex", "资本开支"), ("CapEx", "资本开支"), ("资本开支", "资本开支"),
             ("free cash flow", "自由现金流"), ("FCF", "自由现金流"), ("自由现金流", "自由现金流"),
             ("dividend yield", "股息率"), ("renewal rate", "续费率"), ("Renewal rate", "续费率"), ("续费率", "续费率"),
             ("单店年收入", "单店收入"), ("单店收入", "单店收入"), ("经营利润率", "经营利润率"), ("营业利润率", "经营利润率"),
             ("归母净利润", "归母净利"), ("归母净利", "归母净利"), ("扣非归母", "扣非归母"), ("营业收入", "收入"),
             ("总净收入", "收入"), ("营收", "收入"), ("收入", "收入"), ("净利润", "净利"), ("净利率", "净利率"),
             ("毛利率", "毛利率"), ("市场规模", "市场规模"), ("市场", "市场规模"), ("市占率", "份额"), ("份额", "份额"),
             ("渗透率", "渗透率"), ("客单价", "客单价"), ("累计融资", "累计融资"), ("目标价", "目标价"),
             ("EPS", "EPS"), ("CAGR", "CAGR"), ("算力规模", "算力规模"), ("智算规模", "算力规模"), ("装机", "装机"),
             ("AUM", "AUM"), ("管理资产", "AUM"), ("NIM", "净息差"), ("净息差", "净息差"), ("PB", "PB"), ("市净率", "PB"),
             ("首年投入", "投资额"), ("总投资", "投资额"), ("投资额", "投资额"), ("资金需求", "投资额"), ("溢价", "溢价"), ("均值", "均值"), ("平均值", "均值"), ("中位数", "均值"), ("合计", "合计"), ("总额", "总额")]
_XP_HEAD_RE = re.compile("|".join(re.escape(h) for h, _ in _XP_HEADS))
_XP_HEAD_MAP = dict(_XP_HEADS)
_XP_GROWTH = r"增速|同比|增长|增幅|yoy|YoY|环比"
_XP_PER = re.compile(r"FY\s?(?:20)?\d{2}(?:\s?Q[1-4]|\s?H[12])?|20\d{2}\s*年?\s*(?:E|F|H[12]|Q[1-4]|上半年|下半年|前三季度?)?"
                     r"|(?<![\d.])\d{2}\s?(?:Q[1-4]|H[12])(?!\d)")
_XP_SPAN = re.compile(r"(20\d{2})\s*[-–~至→]\s*(20\d{2})|([两二三四五\d])\s*年(?=\s*(?:CAGR|复合|年均))")
_XP_CN = {"两": 2, "二": 2, "三": 3, "四": 4, "五": 5}
_XP_ACRO = {"CAGR", "PE", "PB", "TTM", "EPS", "OPM", "GAAP", "ROE", "YOY", "SSS", "WACC", "BOM", "MRO", "DTC", "SOTP",
            "GMV", "ARPU", "EBITDA", "TC", "PC", "AC", "OC", "JV", "AI", "APP", "FY", "KPI", "WATCH", "CR", "ASP", "MOU",
            "AUM", "NIM", "BP", "BPS", "LF", "COE", "ROA", "ROIC", "EBIT", "NPL"}
_XP_NOT_NAME = (r"利润|规模|增速|占比|要点|附录|同比|预测|实绩|合计|单位|口径|来源|术语|含义|判断|结论|关键|说明|所以呢|测算|团队|示意|亿元|万元|美元"
                r"|现价|评级|买入|增持|减持|卖出|中性|全年|年化|半年|万亿|估值|指标|方法|敏感|催化|风险|配置|假设|情景|基准|乐观|悲观|目标|路径|摘要"
                r"|^万|^亿|^千|^百|辆$|台$|吨$|件$|人$|家$|店$|元$|个$|个月|年$|^[一二两三四五六七八九十半]+年|季度|月份")
_XP_BOUND = re.compile(r"[。；;！？!?\n]|关键要点|Watch|要点|(?<![A-Za-z\d])P\d{1,2}(?=\s)|(?<![\d.])0[1-9](?=\s+[一-鿿])")
_XP_GROUP = r"集团|公司|全公司|合并|整体|总|全年"   # scope words that mean "the whole company": same as no scope
_XP_SEG_STOP = r"^(?:年报|营业|主营|合计|单店|单季|累计|年度|当期|本期|上期|实际|预测|全年|半年|季度|同期|总|其中|整体|人均|平均|利息|净|毛|税前|经营)"


def _xp_name_ok(x):
    if not x or re.search(r"\d", x) or x in _XP_HEAD_MAP or any(h.startswith(x) for h in _XP_HEAD_MAP if len(h) > len(x)):
        return False   # a metric word or its stem ("毛利" of 毛利率) is never a scope
    if re.fullmatch(r"[一-鿿]{2,5}", x):
        return not (_XP_HEAD_RE.search(x) or re.search(_XP_GROWTH + "|" + _XP_NOT_NAME, x))
    return bool(re.fullmatch(r"[A-Z][A-Za-z]{2,11}", x)) and x.upper() not in _XP_ACRO


def _xp_vocab(pages):
    """Scope names: tokens standing alone on ≥ 2 pages plus each page's title subject ("屈光：…")."""
    import collections
    cnt, subj = collections.Counter(), set()
    for p_, t in pages.items():
        if int(p_) == 0:
            continue
        cnt.update({x for x in re.split(r"[\s、/+|,，；;：:（）()·“”\"'\[\]【】<>《》=≈~～—\-–→&]+", t) if _xp_name_ok(x)})
        m = re.match(r"\s*([一-鿿]{2,5})[：:]", t)
        if m and _xp_name_ok(m.group(1)):
            subj.add(m.group(1))
    segs = _xp_segments(pages)
    heads = "|".join(re.escape(h) for h, _ in _XP_HEADS if h not in ("市场", "合计", "总额", "均值", "平均值", "中位数", "溢价"))
    for t in pages.values():   # "电池自供率" / "IGBT 自供率": the word right before a metric names what it is about
        for m in re.finditer(r"([一-鿿]{2,4}|[A-Z][A-Za-z]{1,10})\s?(?=(?:" + heads + r"))", str(t)):
            tail = str(t)[m.start(1):m.end() + 8]
            if re.match(r"[年季月的和与及占第度]", m.group(1)) or any(re.match(heads, tail[k:]) for k in range(len(m.group(1)))):
                continue   # "2025 年海外销量": 海外销量 is the metric itself, not 年海外 + 销量
            if m.group(1) in _XP_HEAD_MAP or m.group(1).upper() in ("OPEX", "CAPEX") or any(
                    h.startswith(m.group(1)) and len(h) > len(m.group(1)) for h in _XP_HEAD_MAP):
                continue
            if _xp_name_ok(m.group(1)) or re.fullmatch(r"[A-Z]{2,6}", m.group(1)) and m.group(1) not in _XP_ACRO:
                cnt[m.group(1)] += 2
    names = {k for k, v in cnt.items() if v >= 2} | subj | segs
    return sorted(names, key=len, reverse=True)


def _xp_segments(pages):
    """Segments the deck itself names "X收入 / X营收" (楼宇科技收入, ToB收入, 消费电器营收): X is its own scope. For a
    Chinese run before 收入 the longest tail (4→2 chars) that also occurs elsewhere in the deck is X ("年楼宇收入" → 楼宇)."""
    allt = _xp_norm_text(" ".join(str(v) for v in pages.values()))
    segs = set()
    for m in re.finditer(r"([A-Za-z][A-Za-z]{1,10}|[一-鿿]{2,8})\s*(?:业务)?(?:收入|营收)", allt):
        run = m.group(1)
        cands = [run] if run.isascii() else [run[-k:] for k in (4, 3, 2) if len(run) >= k]
        for x in cands:
            if re.search(_XP_SEG_STOP, x) or re.search(r"单店|人均|年$|季$|月$|[的总合于非高低快慢]$|^[年季月的和与及占第]", x) \
                    or re.fullmatch(_XP_GROUP, x) or not _xp_name_ok(x) or x.upper() in _XP_ACRO:
                continue
            if allt.count(x) >= 2 and re.search(r"(?:^|[^一-鿿])" + re.escape(x), allt):   # stands alone somewhere
                segs.add(x)
                break
    return segs


def _xp_norm_text(text):
    text = str(text or "").replace("&gt;", ">").replace("&lt;", "<").replace("&amp;", "&")
    return re.sub(r"(?<=\b[A-Z][a-z])\s(?=[A-Z]\b)", "", text)   # "To B" → "ToB" (one segment name)


def _xp_subjects(pages, vocab):
    """The deck's own subject when it is a single one (招行 / 招商银行 — names on ≥ 30 % of pages that are aliases of each
    other): a mention scoped to it compares with an unscoped mention. Two subjects (星巴克 vs 瑞幸): none."""
    real = [t for p, t in pages.items() if int(p) != 0 and str(t).strip()]
    if len(real) < 5:
        return set()

    def alias(a, b):   # 招行 ⊂ 招商银行 as a subsequence, same first character
        it = iter(b)
        return a != b and a[0] == b[0] and all(ch in it for ch in a)
    groups = []
    for nm in vocab:   # a company name (…银行 / …集团 / …股份) and its short forms in the deck
        if not re.fullmatch(r"[一-鿿]{2,6}(?:银行|集团|股份|控股|证券|保险|医药|汽车|科技|电子|能源|电力)", nm) or nm[0] in "其他":
            continue
        als = {nm} | {o for o in vocab if alias(o, nm)}
        if sum(any(a in t for a in als) for t in real) >= 0.3 * len(real) and als not in groups:
            groups.append(als)
    return groups[0] if len(groups) == 1 else set()


def _xp_title_scope(text, vocab):
    m = re.match(r"\s*([一-鿿]{2,5})[：:]", text)
    if m and m.group(1) in vocab:
        return m.group(1)
    found = {nm for nm in vocab if nm in text[:30]}
    found = {nm for nm in found if not any(nm != o and nm in o for o in found)}
    return found.pop() if len(found) == 1 else ""


def _xp_scope_of(text, start, vocab, title_scope):
    sent_b = max([m.end() for m in _XP_BOUND.finditer(text, 0, start)] + [0])
    clause_b = max([sent_b] + [i + 1 for i in (text.rfind("，", 0, start), text.rfind(",", 0, start))])
    peer = re.search(r"(?:其余|其他|同业|行业|可比|对手|竞品|均值|平均|中位)[^，,。；;]{0,8}$", text[max(clause_b, start - 14):start])
    if peer:   # "其余 3 家 PB 0.27–0.47 倍": the peers' number, not the company's
        return "peer"
    for lo in (max(clause_b, start - 24), max(sent_b, start - 28)):
        best = None
        for nm in vocab:
            i = text.rfind(nm, lo, start)
            if i < 0 or re.match(r"\s*(?:占比|收入|营收|毛利率|份额|市场)\s*(?:约|为|达)?\s*(?!20\d{2})\d", text[i + len(nm):start]):
                continue   # "海外占比 约40% … 营收超4000亿": the name already has its own metric and number
            if best is None or i + len(nm) > best[0]:
                best = (i + len(nm), nm)
        if best:
            return best[1]
    return title_scope


def _xp_norm_per(tok):
    t = re.sub(r"\s|年", "", tok)
    m = re.fullmatch(r"FY(?:20)?(\d{2})(.*)", t) or re.fullmatch(r"(\d{2})(Q[1-4]|H[12])", t)
    if m:
        return f"20{m.group(1)}{m.group(2)}"
    return t[:4] + {"F": "E", "上半年": "H1", "下半年": "H2", "前三季度": "9M", "前三季": "9M"}.get(t[4:], t[4:])


def _xp_mentions(text, vocab, segs=None):
    out, prev = [], None
    text = _xp_norm_text(text)
    title_scope = _xp_title_scope(text, vocab)
    yrs = {_xp_norm_per(x.group(0)) for x in _XP_PER.finditer(text[:40])}
    title_per = yrs.pop() if len(yrs) == 1 and not _XP_SPAN.search(text[:40]) and not re.search(r"\d\s*[-–~→]\s*\d", text[:40]) else ""
    if not re.fullmatch(r"20\d{2}", title_per or ""):
        title_per = ""   # only a full-year actual in the title dates the page ("2025 分业务全景"); 2026E PE ≠ the page's year
    seg_names = set(segs or ())
    for m in _XP_NUM.finditer(text):
        s, e = m.start(), m.end()
        dollar = s > 0 and text[s - 1] in "$€£" and not (s > 1 and re.match(r"[A-Za-z]", text[s - 2]))   # "$550K" / "€980"
        pre_cur = "HKD" if text[max(0, s - 3):s] == "HK$" else "USD" if text[max(0, s - 3):s] == "US$" else ""
        dollar = dollar or bool(pre_cur)   # "HK$300" / "US$12.8B": the currency is written before the number
        if s > 0 and not dollar and (text[s - 1].isdigit() or text[s - 1] in ".$€£" or re.match(r"[A-Za-z]", text[s - 1])):
            continue
        unit, scale_s, cur = m.group("unit") or "", m.group("scale") or "", _XP_CUR.get(m.group("cur") or "", "")
        if dollar and not cur:
            cur = pre_cur or {"$": "USD", "€": "EUR", "£": "GBP"}[text[s - 1]]
        if scale_s in ("K", "M", "B") and not (dollar or cur):
            scale_s = ""   # "5M 用户" / "B 轮": a bare letter scales money only
        if unit in ("pp", "pt", "个百分点"):
            continue
        kind = "pct" if unit in ("%", "pct") else "x" if unit == "倍" else unit or ("money" if (cur or scale_s) else "")
        if not kind and re.search(r"LTV\s*/\s*CAC[^\d。；;]{0,8}$", text[max(0, s - 16):s]):
            kind = "x"   # "LTV/CAC 0.94": a bare multiple
        if not kind or re.fullmatch(r"20\d{2}", m.group("num")):
            continue
        own_per = re.search(r"(" + _XP_PER.pattern + r")\s*(?:实际|实绩|峰值|预测|目标|约)?\s*$", text[max(0, s - 14):s])
        if re.match(r"\s*/", text[e:e + 2]) or ((re.match(r"\s*→", text[e:e + 2]) or re.search(r"(→|从)\s*[约近]?\s*$", text[max(0, s - 3):s]))
                                                and not own_per):
            continue   # series endpoint (A→B, 从 A 升至 B) without its own period, or a ratio 元/人次
        if re.match(r"\s*(?:峰值|谷底|高点|低点)", text[e:e + 4]):
            continue   # a historical extreme, not the current level
        if re.search(r"(?:每|per)\s*$", text[max(0, s - 4):s], re.I) or re.search(r"每\s*\d[\d,.]*\s*[万亿]?\s*[A-Za-z一-鿿]{0,4}\s*[近约]?\s*$", text[max(0, s - 16):s]) or re.search(r"变动约?\s*(?:HK\$|US\$|\$)?$", text[max(0, s - 8):s]):
            continue   # "每 100 万 GMV" is a unit of account; "目标价变动约 HK$20" a sensitivity, not the level
        try:
            num = float(m.group("num").replace(",", ""))
            num2 = float(m.group("num2").replace(",", "")) if m.group("num2") else None
        except ValueError:
            continue
        scale = _XP_SCALE.get(scale_s, 1.0)
        approx = bool(re.search(r"(约|近|超过?|逾|≈|~|多|>|<|不足|突破)\s*$", text[max(0, s - 4):s]))
        bound = re.search(r"(超过?|逾|>|突破|不足|<|低于)\s*$", text[max(0, s - 4):s])
        sent_b = max([b.end() for b in _XP_BOUND.finditer(text, 0, s)] + [0])
        win = text[max(sent_b, s - 30):s]
        heads = list(_XP_HEAD_RE.finditer(win))
        metric, per, after_scope = None, "", ""
        if heads:
            h = heads[-1]
            gap = win[h.end():]
            core = _XP_PER.sub("", gap)
            if own_per:   # "欧美收入 2025 实际 82.6 亿 → 2028E 131 亿": the series start is not in the way
                core = re.sub(r"[约近]?\s*\d[\d,.]*\s*(?:万亿|亿元|亿|万元|万|%|美元|元)?\s*(?:→|->)", "", core)
            if not re.search(r"\d", core) and len(re.sub(r"\s|[（(][^）)]*[）)]", "", core)) <= 6:
                metric = _XP_HEAD_MAP[h.group(0)]
                if metric == "CAGR":
                    sp = None
                    for sm in _XP_SPAN.finditer(text[max(sent_b, s - 30):e + 14]):
                        sp = int(sm.group(2)) - int(sm.group(1)) if sm.group(1) else (
                            int(sm.group(3)) if sm.group(3).isdigit() else _XP_CN.get(sm.group(3)))
                    metric = f"{sp}年CAGR" if sp and kind == "pct" else None
                    per = "span"
                elif re.search(_XP_GROWTH, gap) or (kind == "pct" and m.group("sign") and not metric.endswith(("率", "份额"))):
                    metric += "增速"
                elif re.search(r"占|比重|比例", gap) or text[max(0, h.start() - 2):h.start()].endswith(("占", "占总")):
                    metric += "占比"   # "占营收约 43%" / "收入占比 18.5%": a share, not the revenue
        nxt = re.match(r"\s{0,2}(" + _XP_HEAD_RE.pattern + r")", text[e:e + 8])
        if metric and nxt and heads and not re.search(r"[为达至：:]|约|仅", win[heads[-1].end():]) and \
                _XP_HEAD_MAP[nxt.group(1)] not in ("CAGR", metric) and \
                not re.match(r"(?:\s|对应|为|达|约|仅|：|:|\(|（){0,4}[+\-−]?\d", text[e + nxt.end():e + nxt.end() + 8]):   # next label has its own number
            metric = None   # "PB溢价 0.96x PB(LF)": the number sits between two labels — cannot tell whose it is
            heads = []
        if metric is None and not heads or (metric is None and kind != "pct"):
            after = re.match(r"\s*(?:[（(]?\s*(" + _XP_PER.pattern + r")\s*[）)]?)?\s*(?:(?<=[E\d年])\s*[一-鿿A-Za-z]{2,4}?)?(" + _XP_HEAD_RE.pattern + r")(?![一-鿿]{0,1}率)",
                             text[e:e + 16])
            if after and _XP_HEAD_MAP.get(after.group(2)) not in ("CAGR", "合计", "总额", "回撤", "溢价", "均值") and \
                    not re.match(r"(?:\s|对应|为|达|约|仅|：|:|\(|（){0,4}[+\-−]?\d", text[e + after.end():e + after.end() + 8]) and \
                    not re.match(r"\s*(?:溢价|折价|差距|领先|落后|倍)", text[e + after.end():e + after.end() + 4]):
                metric = _XP_HEAD_MAP[after.group(2)]   # value first: "80 亿元 2028E 欧美收入目标" / "-57BP NIM较2022累计"
                after_scope = next((nm for nm in vocab if nm in after.group(0)), "")
                if after.group(1):
                    per = _xp_norm_per(after.group(1))
                if re.match(r"\s*(?:较|比)\s*20\d{2}|\s*累计", text[e + after.end():e + after.end() + 6]):
                    metric += "累计变动"
        if metric is None and prev and s - prev["end"] <= 16 and kind == prev["kind"] and re.fullmatch(
                r"[\s，,、]*(?:vs\.?|高于|低于|约为|对比)?\s*[一-鿿A-Za-z]{0,6}?\s*(?:约|仅|达|为)?\s*",
                text[prev["end"]:s]) and not re.search(r"较|比|现价|当前|股价|目标|预测|实际", text[prev["end"]:s]):
            metric, per = prev["metric"], prev["per"] or "span"   # "283 万 vs 瑞幸约 203 万": same metric and period
        if metric is None and re.search(r"(?:回撤|累计下降|累计降幅|累计变动)[^\d。；;]{0,8}$", text[max(sent_b, s - 14):s]):
            tm = _XP_HEAD_RE.search(text[:40])   # "本轮回撤：-61bp" on a page titled "NIM 降至…": the title metric's move
            if tm and _XP_HEAD_MAP[tm.group(0)] not in ("CAGR", "合计", "总额", "回撤", "溢价", "均值"):
                metric = _XP_HEAD_MAP[tm.group(0)] + "累计变动"
        if metric and not metric.endswith("累计变动") and kind in ("bp", "bps", "BP", "BPS", "pct") and re.match(
                r"\s*[A-Za-z一-鿿]{0,4}?\s*(?:较|比)\s*20\d{2}[^\d。；;]{0,4}累计", text[e:e + 18]):
            metric += "累计变动"   # "-57BP NIM较2022累计": a move since 2022, not the 2022 level
            per = "span"
        if metric in ("合计", "总额"):   # "ToB合计约 940 亿" / "To B 总额 1228 亿": revenue of a segment the deck names "X收入"
            sc = _xp_scope_of(text, s, vocab, "")
            metric = "收入" if sc in seg_names else None
        if metric == "均值" and kind != "x":
            metric = None
        if metric and kind != "pct" and (metric.endswith(("率", "占比", "份额")) or metric in ("CAGR",)):
            metric = None   # "毛利率 楼宇科技 358亿": a rate label cannot carry money — the number is someone else's
        if metric and kind != "money" and metric in ("GMV", "股价", "收入", "归母净利", "净利", "市场规模", "AUM", "目标价", "单店收入", "投资额", "单车净利", "市值",
                                                 "研发投入", "单店投资", "订单储备", "订单额", "资本开支",
                                                 "自由现金流", "收购对价", "EBITDA"):
            metric = None   # "4565亿营收与74%分红": a % under a money label is not that money
        if not metric and kind in ("money", "pct") and re.search(r"(?:^|[\s、，,；;：:])([一-鿿A-Za-z]{2,6})\s*[约为:：]?\s*$", text[max(sent_b, s - 10):s]):
            nm_ = re.search(r"([一-鿿A-Za-z]{2,6})\s*[约为:：]?\s*$", text[max(sent_b, s - 10):s]).group(1)
            ctx_ = text[max(0, sent_b - 60):s]   # "通威 -95.5 亿、天合 -69.9 亿" under "…合计亏 430 亿" / "归母净利润（亿元）"
            lead = None
            for rx_, mt_ in ((r"归母净利|净利润|亏损|亏(?!欠)|盈利", "归母净利"), (r"营收|收入", "收入"), (r"毛利率", "毛利率"),
                             (r"份额|市占率", "份额")):
                if re.search(rx_, ctx_) or re.search(rx_, text[:60]):
                    lead = mt_
                    break
            if lead and nm_ in vocab and (kind == "money") == (lead in ("归母净利", "收入")):
                metric = lead
                if lead == "归母净利" and re.search(r"亏", ctx_) and not m.group("sign"):
                    num = -num   # "亏 64 亿" is −64
        if not metric:
            prev = None
            continue
        if own_per and per != "span" and not per:
            per = _xp_norm_per(own_per.group(1))
        if per != "span" and not per:
            pers = {_xp_norm_per(x.group(0)) for x in _XP_PER.finditer(text[max(sent_b, s - 24):s])}
            if len(pers) > 1:
                prev = None
                continue
            per = pers.pop() if pers else ""
            if not per:
                after = re.match(r"\s*[（(]?\s*(" + _XP_PER.pattern + ")", text[e:e + 14])
                per = _xp_norm_per(after.group(1)) if after else ""
            if metric.endswith("增速") and not per:
                prev = None
                continue
            if not per and re.search(r"预测|预计|一致预期|预期", text[max(sent_b, s - 24):s]):
                per = "预测"   # a forecast without its year never compares with an actual
            if metric.endswith("累计变动") or metric in _XP_STRICT:
                per = ""   # a move over a span: its period is the span, compared across pages as one figure
            elif not per and title_per:
                per = title_per   # the page title's single year ("2025 分业务全景")
        cum = None if "累计" in metric or metric.endswith("CAGR") else _XP_CUM.search(text[max(sent_b, s - 16):s])
        if cum:   # "8 季累计营收 13.9 亿" vs "2025 年营收 7.10 亿" or a per-city 8 季 total vs the group's:
            prev = None   # a multi-period total has no single-period peer and its subject is often unstated — not compared
            continue
        v = (-1.0 if m.group("sign") in ("-", "−") else 1.0) * num * scale
        lo, hi = (min(num, num2) * scale, max(num, num2) * scale) if num2 is not None else (v, v)
        if bound and num2 is None:   # "突破 18 万亿" / "超 4000 亿": a bound, consistent with any value beyond it
            lo, hi = (v, float("inf")) if bound.group(1) in ("超", "超过", "逾", ">", "突破") else (float("-inf"), v)
        nd = len(m.group("num").split(".")[1]) if "." in m.group("num") else 0
        scope = after_scope or _xp_scope_of(text, s, vocab, title_scope)
        if re.fullmatch(_XP_GROUP, scope or ""):
            scope = ""
        if kind in ("bp", "bps", "BP", "BPS"):
            kind = "bp"
        elif kind in ("x", "X"):
            kind = "x"
        mt = dict(metric=metric, scope=scope, per="" if per == "span" else per,
                  kind=kind, cur=cur, val=v, lo=lo, hi=hi, approx=approx, raw=text[s:e].strip(), num=num,
                  prec=(10 ** -nd) * scale, end=e)
        out.append(mt)
        prev = mt
    return out


_XP_STRICT = {"目标价"}   # one figure per deck: 54 / 55 / 54.6 are three different answers, rounding or 约 aside
# a total over several periods written before the number: 累计 / 8 季 / 近 3 年 / 过去 12 个月 / cumulative / over 8 quarters
_XP_CUM = re.compile(r"(?<![\d.])(?:[1-9]\d?|[两二三四五六七八九十])\s*个?\s*(?:季度?|年|个?月)\s*(?:累计|合计)|(?<![\d.])(?:[2-9]|1\d)\s*季"
                     r"|(?:近|过去)\s*\d{1,2}\s*个?\s*(?:季度?|年|月)|累计|cumulative|(?:over|last|past)\s+\d{1,2}\s+(?:quarters?|years?|months?)"
                     r"|\d{1,2}-(?:quarter|year|month)\s+total", re.I)


def _xp_differ(a, b):
    if a["cur"] and b["cur"] and a["cur"] != b["cur"]:
        return False
    lo, hi = max(a["lo"], b["lo"]), min(a["hi"], b["hi"])
    if lo <= hi:
        return False
    gap = lo - hi
    if a["metric"] in _XP_STRICT and a["lo"] == a["hi"] and b["lo"] == b["hi"]:
        return gap / max(abs(a["val"]), abs(b["val"]), 1e-12) > 0.005
    tol = 0.02 if (a["approx"] or b["approx"]) else 0.01   # 157 vs 158 (0.6 %) passes, 4.7 vs 4.8 % does not
    return gap > 0.5 * max(a["prec"], b["prec"]) and gap / max(abs(a["val"]), abs(b["val"]), 1e-12) > tol


def _plan_fact_text(directory):
    """plan.py PAGES titles as rendered (f-strings from F filled in): page 0 of the cross-page check."""
    g = _load_plan(directory, "plan_facts")
    if not g:
        return ""
    return " 。".join(str(r.get("title") or "") for r in g.get("PAGES", []) or []
                      if isinstance(r, dict) and str(r.get("p", "")).isdigit() and int(r["p"]) > 3)


def _sync_plan_facts(directory):
    """Write page "0" (_plan_fact_text) into <cwd>/.lark-slides/pagetext-<deck>.json when plan.py changed, so
    Frame.publish's cross-page hold (it compares the page being written with every ledger entry) also checks the
    plan's numbers. No agent waits on it; no file the model writes."""
    d = Path(directory)
    plan, cwd = d / "plan.py", _task_cwd(d)
    if not plan.exists() or cwd is None:
        return
    stamp = f"{plan.stat().st_mtime:.3f}"
    mark = d / ".plan_facts"
    for deck in _task_decks(d, cwd):
        led = Path(cwd) / ".lark-slides" / f"pagetext-{deck}.json"
        if _read_text(mark) == stamp and "0" in _read(led):
            continue
        txt = _plan_fact_text(d)
        if not txt:
            continue
        texts = _read(led)
        texts["0"] = txt
        try:
            led.parent.mkdir(parents=True, exist_ok=True)
            _atomic_write(led, texts)
            mark.write_text(stamp, encoding="utf-8")
        except OSError:
            pass


CROSS_PAGE_MSG = ("跨页数字不一致（只提示）：{items}——先查这两个数各自来自哪个 research 变量：同一口径就两页都改成那个变量的值"
                  "（改页面脚本后重跑，不用 sed 批量替换 XML：替换会连带改掉别的年份 / 别的指标里相同的数）；"
                  "确实口径不同就在标题 / 脚注写明口径；两个数都找不到变量来源就以 research 里有的为准")


def _slide_texts(bodies_by_page):
    return {p: " ".join(re.sub(r"<[^>]+>", " ", b or "").replace("&amp;", "&").split())
            for p, b in bodies_by_page.items()}


def _strip_label(text, label):
    """'制作说明：制作说明：…': drop the label when the Lead's notes already start with it."""
    t = (text or "").strip()
    while t.startswith((label + "：", label + ":")):
        t = t[len(label) + 1:].lstrip()
    return t


def _artifacts_json(title, url, pptx):
    """Ready-to-copy present_files arguments: both items survive even if Main drops the instruction line (no online
    item when the deck URL is unknown — never a placeholder)."""
    p = Path(pptx).expanduser().resolve() if pptx else Path("<PPTX 绝对路径>")
    items = ([{"name": f"{title}（在线）", "source": url}] if url else []) + [
        {"name": p.name if pptx else f"{title}.pptx", "source": str(p)}]
    return json.dumps({"artifacts": items}, ensure_ascii=False)


def lead_return(title, pages, url, pptx, notes=None, gaps=None, who="lead"):
    """Final return message: link + PPTX in one present_files. who="lead" (default): a Lead's return that the
    dispatching agent forwards verbatim; who="main": the MainAgent's own closing (no Lead-only lines); who="closer":
    the closing agent of a deck a MainAgent once dispatched (Main or Lead — no "Lead 不运行 dispatch" line).
    url=None (unknown) leaves the link line out instead of printing a placeholder."""
    notes, gaps = _strip_label(notes, "制作说明"), _strip_label(gaps, "未完成/缺口")
    head = ("【本行不要念给用户；用一次 present_files 同时交付链接与 PPTX，然后把下面内容作为最后一条回复】\n" if who == "main" else
            "【主 agent：本行不要念给用户；把下面内容原样转告，并用一次 present_files 同时交付链接与 PPTX】\n")
    tail = ("（这段即最终回复，前后不要加别的文字）\n（之后若用户追问：先重读 SKILL.md 与 slides-editing.md）" if who == "main" else
            ("（这段即最终回复，前后不要加别的文字）\n" if who == "closer" else
             "（Lead 不运行 dispatch；这段即最终回复，前后不要加别的文字）\n")
            + "（主 agent：之后若用户追问，派单首句写'先重读 SKILL.md 与 slides-editing.md'）")
    return (head
            + f"已完成：{title}，共 {pages} 页。\n"
            + ("请用一次 present_files 同时交付下面两项（在线链接与本地文件都要给用户，缺一不可）：\n" if url else
               "请用一次 present_files 交付下面的文件：\n")
            + (f"- 飞书幻灯片链接：{url}\n" if url else "")
            + f"- 本地 PPTX：{Path(pptx).expanduser().resolve()}\n"
            f"制作说明：{notes or ''}\n"
            f"未完成/缺口：{gaps or '无'}\n"
            "不需要再修改幻灯片。\n"
            f"present_files 参数：{_artifacts_json(title, url, pptx)}\n"
            + tail)


def release(directory, who):
    """Free every page `who` is still 'doing' (e.g. right before kill_agent), so next hands them out again."""
    import fcntl
    directory = Path(directory)
    with open(directory / "claims.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        claims = _read(directory / "claims.json")
        freed = [k for k, v in claims.items() if _claim_state(v)["who"] == who and _claim_state(v)["state"] == "doing"]
        for k in freed:
            del claims[k]
        back = [k for k, v in claims.items() if _claim_state(v)["state"] == "reviewing"
                and _claim_state(v).get("reviewer") == who]
        for k in back:   # a reviewer that is killed mid-review hands the page back to the review queue
            claims[k]["state"] = "built"
        freed += back
        _write(directory / "claims.json", claims)
    return {"ok": True, "released": freed, "next": "已释放，运行 next 领取这些页" if freed else "没有未完成的页"}


def ready(deck, page, cwd="."):
    """In-order upload gate: page N may be published only after pages 1..N-1 are recorded by publish_slide(page=)."""
    registry = _read(Path(cwd) / ".lark-slides" / f"pages-{deck}.json")
    n = int(page)
    missing = [p for p in range(1, n) if f"p{p:02d}" not in registry]
    out = {"ok": not missing, "page": n, "missing": missing}
    if f"p{n:02d}" in registry:
        out["already"] = registry[f"p{n:02d}"]
    if missing:
        out["next"] = "前序页未上传：先做下一页，做完再检查一次；不要空等或循环检查"
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("status")
    s.add_argument("--dir", required=True)
    s.add_argument("--phase", required=True)
    s.add_argument("--done")
    s.add_argument("--note")
    w = sub.add_parser("wait")
    w.add_argument("--dir", required=True)
    w.add_argument("--phase", required=True, choices=PHASES)
    w.add_argument("--max", type=int, default=180)
    w.add_argument("--interval", type=int, default=10)
    c = sub.add_parser("next")
    c.add_argument("--dir", required=True)
    c.add_argument("--who", required=True)
    c.add_argument("--prefer", help="this agent's own pages from plan.py PAGES, e.g. 2,3,4,10-12")
    c.add_argument("--from-end", action="store_true", help="after own pages, take the last unclaimed page")
    c.add_argument("--review", action="store_true", help="main/organizer: take the next builder page to check")
    c.add_argument("--block", type=int, help="max seconds to wait inside the command when nothing is ready "
                   f"(default {NEXT_BLOCK} for builders / --review, 0 otherwise)")
    c.add_argument("--no-wait", action="store_true", help="return at once with the current state (ok:null carries "
                   "retry_after seconds) — use instead of wrapping next in sleep / timeout")
    c.add_argument("--agent-id", help="subagents: your create_agent id — finish lists it in still_running for shutdown")
    v = sub.add_parser("verdict")
    v.add_argument("--dir", required=True)
    v.add_argument("--page", required=True, type=int)
    v.add_argument("--who", required=True)
    g = v.add_mutually_exclusive_group(required=True)
    g.add_argument("--ok", action="store_true")
    g.add_argument("--fixed", action="store_true")
    g.add_argument("--redo", action="store_true", help="organizer/main/lead before export: reopen page N to yourself "
                   "for one rewrite (needs --note; not the one-time finish --fix)")
    v.add_argument("--note")
    fz = sub.add_parser("finish")
    fz.add_argument("--dir", required=True)
    fz.add_argument("--deck", required=True)
    fz.add_argument("--cwd", default=".")
    fz.add_argument("--name")
    fz.add_argument("--solo", action="store_true", help="single-agent deck (no Organizer): skip the exec-summary check")
    fz.add_argument("--who", help="main | lead (lead: no skill-guided Main; next text points to lead-return). "
                    "organizer is refused while Main's dispatch is open")
    fz.add_argument("--fix", help="after export: unfreeze these pages once per task (e.g. 5 or 5,7) — Main / Lead only")
    fz.add_argument("--why", help="with --fix: the real defect being fixed")
    fz.add_argument("--url", help="Lead: deck URL for final_reply (default: read from deck.txt)")
    fz.add_argument("--notes", help="Lead: 2–4 sentence production note for final_reply (text with $ or quotes: "
                    "use --notes-file)")
    fz.add_argument("--gaps", help="Lead: data gaps for final_reply (text with $: use --gaps-file)")
    fz.add_argument("--notes-file", help="read --notes from this file (no shell expansion of $250K etc.)")
    fz.add_argument("--gaps-file", help="read --gaps from this file (no shell expansion)")
    fz.add_argument("--accept-lint", help="export although the read-back server lint still reports errors "
                    "(the reason is recorded in status.json); without it finish reopens those pages first")
    rl = sub.add_parser("release")
    rl.add_argument("--dir", required=True)
    rl.add_argument("--who", required=True)
    dp = sub.add_parser("dispatch")
    dp.add_argument("--cwd", required=True)
    dp.add_argument("--flow", choices=FLOWS)
    dp.add_argument("--close", action="store_true", help="retire the dispatch record after delivery")
    dp.add_argument("--deck")
    dp.add_argument("--binding", choices=("edit", "resume"))
    dp.add_argument("--template-assist", action="store_true", help="仅 template：独立辅助派单记录，无 strategy SYNC；开启和 --close 都须带此标志")
    ro = sub.add_parser("role")
    ro.add_argument("--cwd", required=True)
    ro.add_argument("--marker", help="flow named in the dispatch message's [ppt-dispatch:<flow>] marker, if any")
    lr = sub.add_parser("lead-return", help="print Lead's final return message (plain text)")
    lr.add_argument("--title", required=True)
    lr.add_argument("--pages", required=True, type=int)
    lr.add_argument("--url", required=True)
    lr.add_argument("--pptx", required=True)
    lr.add_argument("--notes", help="2–4 sentence production note; the shell expands $ inside double quotes "
                    "(\"$250K\" → \"50K\") — write the text to a file and pass --notes-file, or use single quotes")
    lr.add_argument("--gaps", help="data gaps (same $ caveat: prefer --gaps-file)")
    lr.add_argument("--notes-file", help="read the notes text from this file (UTF-8; overrides --notes)")
    lr.add_argument("--gaps-file", help="read the gaps text from this file (UTF-8; overrides --gaps)")
    lr.add_argument("--cwd", help="task dir: the text is also written to <cwd>/.lark-slides/decks/<deck>/FINAL_REPLY.md "
                    "(default: current dir)")
    ex = sub.add_parser("export", help="Lead's final export: drive +export PPTX + write/print FINAL_REPLY.md")
    ex.add_argument("--deck", required=True)
    ex.add_argument("--strict", action="store_true", help="可选：模板内部登记/计划/回读诊断阻断导出；默认允许导出复核稿")
    ex.add_argument("--cwd", default=".")
    ex.add_argument("--name", help="PPTX file name (default: deck title)")
    ex.add_argument("--who", choices=("lead", "main", "solo"), help="default: lead unless a live dispatch exists; "
                    "solo = single-agent deck (no SYNC dir): PPTX into --cwd root + url.txt + exported marker, no FINAL_REPLY")
    ex.add_argument("--url", help="deck URL (default: read from this deck's deck.txt)")
    ex.add_argument("--title")
    ex.add_argument("--pages", type=int)
    ex.add_argument("--notes")
    ex.add_argument("--gaps")
    ex.add_argument("--notes-file", help="notes text file (dispatch-hint fields such as 核心结论/验证方式 go here)")
    ex.add_argument("--gaps-file")
    nt = sub.add_parser("notice", help="print the fixed closing notice for a review subagent (send it verbatim)")
    nt.add_argument("--to", required=True, help="recipient name / agent id (e.g. R1)")
    nt.add_argument("--flow", default="template", choices=FLOWS)
    nt.add_argument("--minutes", type=int, default=3)
    nt.add_argument("--cwd", default=".", help="task dir: also writes <cwd>/.lark-slides/closing.json (reviewers poll it)")
    rp = sub.add_parser("reopen", help="follow-up turn on a delivered multi-agent deck: archive exported/frozen.lock, "
                        "phase=edit, fresh budgets, reseal — then edit pages and run export")
    rp.add_argument("--cwd", required=True)
    rp.add_argument("--why", required=True, help="one-line summary of the user's follow-up request")
    rp.add_argument("--deck", help="xml_presentation_id of the deck to edit (needed when the folder holds several)")
    rp.add_argument("--readback", help="this turn's +xml-get output of the deck (source.xml or source-response.json); "
                    "without it reopen looks for a fresh one in the CWD tree and refuses when there is none")
    br = sub.add_parser("brief", help="print the full SubAgent rules (strategy R1–R5 / builders run this first)")
    br.add_argument("--dir", required=True)
    br.add_argument("--who", required=True)
    br.add_argument("--build", action="store_true", help="builder: skip the research stage")
    r = sub.add_parser("ready")
    r.add_argument("--deck", required=True)
    r.add_argument("--page", required=True, type=int)
    r.add_argument("--cwd", default=".")
    a = ap.parse_args(argv)
    for k in ("notes", "gaps"):   # --notes-file / --gaps-file: text read verbatim ($ never reaches the shell)
        fpath = getattr(a, f"{k}_file", None)
        if fpath:
            try:
                setattr(a, k, Path(fpath).read_text(encoding="utf-8").strip())
            except OSError as e:
                ap.error(f"--{k}-file {fpath}: {e}")
    if a.cmd == "status":
        out = set_status(a.dir, a.phase, a.done, a.note)
    elif a.cmd == "wait":
        out = wait(a.dir, a.phase, a.max, a.interval)
    elif a.cmd == "next":
        out = next_page(a.dir, a.who, a.prefer, a.from_end, a.review, a.block, agent_id=a.agent_id,
                        no_wait=a.no_wait)
    elif a.cmd == "verdict":
        out = verdict(a.dir, a.page, a.who, a.fixed, a.note, redo=a.redo)
    elif a.cmd == "finish":
        out = finish(a.dir, a.deck, a.cwd, a.name, a.solo, a.who, a.fix, a.why, a.url, a.notes, a.gaps,
                     accept_lint=a.accept_lint)
    elif a.cmd == "release":
        out = release(a.dir, a.who)
    elif a.cmd == "dispatch":
        if not a.close and not a.flow:
            ap.error("dispatch needs --flow (or --close)")
        out = dispatch(a.cwd, a.flow, a.close, a.deck, a.binding, a.template_assist)
    elif a.cmd == "role":
        out = role(a.cwd, a.marker)
    elif a.cmd == "lead-return":
        text = lead_return(a.title, a.pages, a.url, a.pptx, a.notes, a.gaps)
        deck = _pub()._deck_id(a.url) if "/slides/" in str(a.url) else None
        try:   # Lead's last message = cat this file (the deck's own FINAL_REPLY.md)
            fr = _write_final_reply(a.cwd or os.getcwd(), deck, text)
            _remember_url(a.cwd or os.getcwd(), deck, a.url)
            print(f"(已写入 {fr})", file=sys.stderr)
        except OSError as e:
            print(f"(FINAL_REPLY.md 未写入：{e})", file=sys.stderr)
        print(text)
        return 0
    elif a.cmd == "export":
        out = export(a.deck, a.cwd, a.name, a.who, a.url, a.title, a.pages, a.notes, a.gaps, strict=a.strict)
        if out.get("final_reply"):
            print(out["final_reply"])
            print(f"\n（已写入 {out['final_reply_file']}；{out['next']}）", file=sys.stderr)
            return 0
    elif a.cmd == "reopen":
        out = reopen(a.cwd, a.why, a.deck, a.readback)
    elif a.cmd == "brief":
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import subagent_brief
        d = Path(a.dir).resolve()
        cwd = _task_cwd(d) or d.parent
        deck = (d / "deck.txt").read_text(encoding="utf-8").split()[0] if (d / "deck.txt").exists() else ""
        print(subagent_brief.render(a.who, str(d), str(cwd), str(Path(__file__).resolve().parent.parent), deck,
                                    _query_text(d), build=a.build or not _is_researcher(a.who)))
        return 0
    elif a.cmd == "notice":
        write_closing(a.cwd, a.to, a.minutes)
        print(closing_notice(a.to, a.flow, a.minutes))
        return 0
    else:
        out = ready(a.deck, a.page, a.cwd)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0 if out.get("ok", True) is not False and out.get("reached", True) else 1


if __name__ == "__main__":
    sys.exit(main())
