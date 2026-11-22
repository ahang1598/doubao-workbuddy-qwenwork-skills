#!/usr/bin/env python3
"""arXiv daily digest — Stage 3 TEMPLATE: build the HTML report.

This is a TEMPLATE, not a one-shot script. The agent copies it into the
workspace as `build_<tag>.py`, fills the SELECTIONS block with the chosen
papers' Chinese annotations, then runs it.  Nothing here is hardcoded to a
person, machine, or fixed URL.

Style is a SHIPPED DEFAULT, not a machine-locked template:
  - By default the report uses report_style.DEFAULT_STYLE (the bundled light
    theme, also available as assets/default_style.css).
  - Pass --style <path.css> to render with a custom stylesheet instead.
  - Do NOT inline CSS; always call report_style.render(cards, ctx).

Cloudflare Pages publishing is OPTIONAL:
  - Only supply --url when the report should be published. When --url is given,
    the URL is written into the footer and publish/index.html is produced for
    deployment. When omitted, a local outputs/arxiv_email_<date>.html is still
    generated but no publish/ directory is written and no deploy happens.

Usage:
    # local report only (no Cloudflare publish):
    python3 build_report.py --tag 0905

    # with publishing URL (footer + publish/index.html):
    python3 build_report.py --tag 0905 --url https://your-project.pages.dev

    # custom style:
    python3 build_report.py --tag 0905 --style /path/to/my_style.css

It reads, from the current directory:
    digest_config_<tag>.json   (topic, custom flag)  — written by run_pipeline.py
    authors_meta.json          (author/affiliation/email) — Stage 2
    submit_dates_<tag>.json    (v1 submission dates) — Stage 2
    arxiv_parsed_<tag>.json    (titles/abstracts) — Stage 1

Outputs:
    outputs/arxiv_email_<date>.html
    publish/index.html         (ONLY when --url is supplied)
"""
import argparse, json, os, re

import report_style


# --------------------------------------------------------------------------
# >>> FILL THIS BLOCK for each selected paper (order = ranking) <<<
# keys per id: topic(str), innovations(list[str]), content(str)
# title / authors / abstract / link are pulled automatically from arxiv_parsed.
SELECTIONS = {
    # "0000.00000": {
    #     "topic": "一句话定位本篇主题",
    #     "innovations": ["创新点 1", "创新点 2", "创新点 3"],
    #     "content": "对主要内容的连贯中文转述（基于摘要但不逐句翻译）",
    # },
}
# --------------------------------------------------------------------------


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True, help="batch tag, e.g. 0905")
    ap.add_argument("--url", default="",
                    help="OPTIONAL published Cloudflare Pages URL. If omitted, no "
                         "publish/ is written and no deployment happens.")
    ap.add_argument("--style", default="",
                    help="OPTIONAL path to a custom stylesheet (.css). If omitted, "
                         "the bundled default light theme is used.")
    ap.add_argument("--date", default="", help="batch public-date label, e.g. 2026-09-03")
    ap.add_argument("--outdir", default=".", help="workspace root (default: cwd)")
    args = ap.parse_args()
    ws = args.outdir
    tag = args.tag

    cfg = json.load(open(os.path.join(ws, f"digest_config_{tag}.json"), encoding="utf-8"))
    meta = json.load(open(os.path.join(ws, "authors_meta.json"), encoding="utf-8"))
    try:
        dates = json.load(open(os.path.join(ws, f"submit_dates_{tag}.json"), encoding="utf-8"))
    except FileNotFoundError:
        dates = {}
    parsed = {e["id"]: e for e in
              json.load(open(os.path.join(ws, f"arxiv_parsed_{tag}.json"), encoding="utf-8"))["candidates"]}

    if not SELECTIONS:
        raise SystemExit("SELECTIONS is empty — fill in the chosen papers first.")

    cards = []
    for pid, ann in SELECTIONS.items():
        p = parsed.get(pid)
        if not p:
            raise SystemExit(f"{pid} not found in arxiv_parsed_{tag}.json")
        cards.append(dict(
            id=pid,
            title=p["title"],
            authors=", ".join(p["authors"]),
            link=f"https://arxiv.org/abs/{pid}",
            pdf=f"https://arxiv.org/pdf/{pid}",
            abstract=p["abstract"],
            venue=p.get("venue_name") or "预印本 (Preprint)",
            themes=p.get("themes", []),
            date=dates.get(pid, ""),
            authors_detail=meta.get(pid),
            topic=ann.get("topic", ""),
            innovations=ann.get("innovations", []),
            content=ann.get("content", ""),
        ))

    # Optional custom stylesheet override (None -> bundled default).
    css = report_style.load_css(args.style) if args.style else None

    custom = cfg.get("custom")
    foot = "自动生成 · 数据来源 arXiv.org"
    if args.url:
        foot += f" · 固定访问地址 {args.url}"
    ctx = dict(
        title=cfg.get("topic", "arXiv 每日精选"),
        hero_title=cfg.get("topic", "arXiv 每日精选"),
        date_label=args.date,
        batch=args.date or f"arXiv 每日精选 · {tag}",
        scope=" · ".join(cfg.get("cats", [])),
        note=("按质量代理混合排序（venue 层级 × 2.2、基准/数据集、量化实证、规模、主题中心度、"
              "跨主题加权），无领域配额；已人工剔除离题条目后取前 %d 篇。主题范围：%s。"
              % (len(cards), cfg.get("topic", ""))),
        foot=foot,
    )
    if css is not None:
        ctx["css"] = css
    if custom:
        ctx["custom_theme"] = {"label": cfg.get("topic", "主题"), "color": "#1f6feb"}

    html = report_style.render(cards, ctx)

    # Sanity assertions. When a custom --style is used, only structural checks
    # apply (gradient / exact color checks are skipped because the style is the
    # user's to define).
    assert html.count("<style>") == 1, "expected exactly one <style> block"
    assert html.count('<div class="card">') == len(cards), "card count mismatch"
    if args.url:
        assert args.url in html, "footer URL missing"
    if css is None:
        # Default theme: enforce the bundled light theme signature.
        assert "linear-gradient(135deg,#0d1117,#1f6feb)" in html, "hero gradient missing"
        assert "background:#f4f5f7" in html, "light theme bg missing"

    os.makedirs(os.path.join(ws, "outputs"), exist_ok=True)
    out_html = os.path.join(ws, "outputs", f"arxiv_email_{args.date or tag}.html")
    open(out_html, "w", encoding="utf-8").write(html)

    if args.url:
        pub = os.path.join(ws, "publish")
        os.system(f"rm -rf {pub}")  # reset: publish/ holds ONLY index.html
        os.makedirs(pub, exist_ok=True)
        open(os.path.join(pub, "index.html"), "w", encoding="utf-8").write(html)
        print(f"wrote {out_html} ({len(html)} bytes) + publish/index.html ({len(cards)} cards)")
    else:
        print(f"wrote {out_html} ({len(html)} bytes) — no --url, skipped publish/")


if __name__ == "__main__":
    main()
