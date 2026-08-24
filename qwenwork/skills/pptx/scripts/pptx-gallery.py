"""Component gallery: one slide per component, deterministic content.

This is the *offline* test we run ourselves (no LLM in the loop) to surface
rendering bugs in the components/ package before we ask an agent to use it.

Output:
  /tmp/pptx-gallery/gallery.pptx   ← the deck
  /tmp/pptx-gallery/slide-*.jpg    ← per-slide JPGs for visual review

Run:
  python3 pptx-gallery.py                # builds + renders
  python3 pptx-gallery.py --build-only   # skip soffice/pdftoppm

We deliberately use realistic content (CJK + Latin, varying lengths) so we
catch overflow, alignment, and contrast bugs the agent would hit.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = Path(tempfile.gettempdir()) / "pptx-gallery"


def build_deck(out_path: Path) -> int:
    """Create one slide per component. Returns slide count."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(SKILL_ROOT))
    # invalidate stale cached imports if rerun
    for k in [k for k in sys.modules if k.startswith(("helpers", "components"))]:
        del sys.modules[k]

    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.util import Emu, Inches

    from helpers import Palette, FontPair, Style, save_pptx
    from components import (
        add_metric_card,
        add_quote_block,
        add_allocation_bars,
        add_layered_diagram,
        add_flywheel,
        add_radar,
        add_swot,
        add_comparison,
        add_gantt,
        add_funnel,
        add_timeline,
        add_flow_matrix,
    )

    # Brand-y palette (Alibaba orange + ink) — gives accent/primary real contrast.
    pal = Palette(
        primary=RGBColor(0x14, 0x3C, 0x6E),     # deep navy
        secondary=RGBColor(0x35, 0x6B, 0xB8),
        accent=RGBColor(0xFF, 0x6A, 0x00),      # vivid orange
        muted=RGBColor(0x5B, 0x67, 0x7A),
        bg=RGBColor(0xFF, 0xFF, 0xFF),
        on_bg=RGBColor(0x16, 0x1B, 0x26),
    )
    fonts = FontPair(header="Inter", body="Inter")
    style = Style(palette=pal, fonts=fonts)

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank = prs.slide_layouts[6]

    margin = Emu(457200)
    title_h = Emu(457200)
    origin = (margin, margin + title_h)
    body_size = (Emu(int(prs.slide_width) - 2 * int(margin)),
                 Emu(int(prs.slide_height) - 2 * int(margin) - int(title_h)))

    def add_title(slide, text: str) -> None:
        from helpers import set_text
        from pptx.enum.text import PP_ALIGN
        tb = slide.shapes.add_textbox(margin, margin, prs.slide_width - 2 * margin, title_h)
        set_text(tb, text, size=18, bold=True, color=pal.on_bg,
                 font=fonts.header, align=PP_ALIGN.LEFT)

    # ───────── 1. metric_card (3 across, to test small-box variant) ─────────
    s = prs.slides.add_slide(blank)
    add_title(s, "metric_card · 3 KPIs (tech / primary / tech)")
    card_w = (int(body_size[0]) - Emu(457200) * 2) // 3
    card_h = Emu(2200000)
    cy = int(origin[1])
    add_metric_card(s, (int(origin[0]), cy), (card_w, card_h),
                    {"kicker": "GMV", "value": "¥12.4B", "desc": "+18% YoY"}, style)
    add_metric_card(s, (int(origin[0]) + card_w + Emu(457200), cy), (card_w, card_h),
                    {"kicker": "NPS", "value": "72", "desc": "increase 4 pts QoQ"},
                    style, variant="primary")
    add_metric_card(s, (int(origin[0]) + 2 * (card_w + Emu(457200)), cy), (card_w, card_h),
                    {"kicker": "Churn", "value": "2.1%", "desc": "下降 0.4 pts"}, style)

    # ───────── 2. quote_block · line variant ─────────
    s = prs.slides.add_slide(blank)
    add_title(s, "quote_block · line variant + attribution")
    add_quote_block(s, origin, (int(body_size[0]), Emu(2800000)),
                    {"kicker": "CEO MESSAGE",
                     "title": "Why we are doubling down on enterprise AI",
                     "copy": "We are betting that domain-specialised models will out-perform general "
                             "frontier models inside large organisations within twelve months — and "
                             "that the data pipelines we build now will compound for a decade.",
                     "author": "Jane Smith", "role": "CEO, Lakeside AI"},
                    style, variant="line")

    # ───────── 3. quote_block · dark + CJK ─────────
    s = prs.slides.add_slide(blank)
    add_title(s, "quote_block · dark variant + CJK")
    add_quote_block(s, origin, (int(body_size[0]), Emu(2800000)),
                    {"kicker": "战略宣言",
                     "title": "做难而正确的事",
                     "copy": "我们坚持把复杂留给自己，把简单交给客户。" * 3,
                     "author": "陈炳材", "role": "首席架构师"},
                    style, variant="dark")

    # ───────── 4. allocation_bars ─────────
    s = prs.slides.add_slide(blank)
    add_title(s, "allocation_bars · 5 lines, mixed tones")
    add_allocation_bars(s, origin, body_size, [
        {"label": "Engineering", "value": "$4.2M", "percent": 42, "tone": "primary"},
        {"label": "Go-to-market", "value": "$2.8M", "percent": 28, "tone": "accent"},
        {"label": "Operations", "value": "$1.6M", "percent": 16, "tone": "soft"},
        {"label": "R&D",      "value": "$0.8M", "percent":  8, "tone": "green"},
        {"label": "Reserve",  "value": "$0.6M", "percent":  6, "tone": "muted"},
    ], style, title="FY26 budget allocation",
       subtitle="Total $10M · USD",
       note="Reserve allocated to compliance audit")

    # ───────── 5. layered_diagram (concentric) ─────────
    s = prs.slides.add_slide(blank)
    add_title(s, "layered_diagram · 4 concentric layers")
    add_layered_diagram(s, origin, body_size, [
        {"title": "User Experience", "desc": "Web · Mobile · API"},
        {"title": "Application Services", "desc": "Auth · Billing · Orchestration"},
        {"title": "Data Platform", "desc": "Lakehouse · Feature store"},
        {"title": "Foundation Models", "desc": "Embedded · Fine-tuned", "tone": "strong"},
    ], style)

    # ───────── 6. flywheel ─────────
    s = prs.slides.add_slide(blank)
    add_title(s, "flywheel · 5-node growth loop")
    add_flywheel(s, origin, body_size,
                 {"title": "Growth\nLoop", "label": "CORE ASSET"},
                 [
                     {"label": "ACQUIRE",  "title": "New users",  "desc": "SEO + paid"},
                     {"label": "ACTIVATE", "title": "First value", "desc": "Onboarding"},
                     {"label": "RETAIN",   "title": "Recurring",  "desc": "Habit loops"},
                     {"label": "MONETIZE", "title": "Expansion",  "desc": "Upsell"},
                     {"label": "REFER",    "title": "Word of mouth", "desc": "Sharing"},
                 ], style)

    # ───────── 7. radar ─────────
    s = prs.slides.add_slide(blank)
    add_title(s, "radar · 6 dimensions, side notes")
    add_radar(s, origin, body_size, [
        {"name": "Speed",       "score": 82, "desc": "p95 < 200ms"},
        {"name": "Cost",        "score": 64, "desc": "Within budget envelope"},
        {"name": "Quality",     "score": 91, "desc": "0 P0 incidents last quarter"},
        {"name": "Coverage",    "score": 73, "desc": "73% line coverage"},
        {"name": "Reliability", "score": 88, "desc": "99.95% rolling uptime"},
        {"name": "Security",    "score": 70, "desc": "SOC2 in-progress"},
    ], style)

    # ───────── 8. swot ─────────
    s = prs.slides.add_slide(blank)
    add_title(s, "swot · 2×2 strategic matrix")
    add_swot(s, origin, body_size, {
        "strengths":     ["Strong brand recognition", "Loyal user base", "Tech moat in inference"],
        "weaknesses":    ["Slow mobile UX", "Concentrated revenue"],
        "opportunities": ["APAC expansion", "Vertical SaaS partnerships"],
        "threats":       ["New entrants with cheaper inference", "Regulatory uncertainty"],
    }, style)

    # ───────── 9. comparison (featured-right) ─────────
    s = prs.slides.add_slide(blank)
    add_title(s, "comparison · 2 panels, featured=right")
    add_comparison(s, origin, body_size, [
        {"kicker": "Today", "title": "Monolith stack",
         "tagline": "Single deploy, growing pain",
         "items": [
             {"title": "Slow releases", "desc": "Weekly cadence at best"},
             {"title": "Coupled teams", "desc": "Cross-domain conflicts"},
         ]},
        {"kicker": "Recommended", "title": "Service mesh", "featured": True,
         "tagline": "Independent, observable, scalable",
         "items": [
             {"title": "Daily deploys",   "desc": "Per-service pipelines"},
             {"title": "Independent SLOs", "desc": "Per-domain ownership"},
         ],
         "scale": {"value": "5×", "unit": "release velocity"}},
    ], style)

    # ───────── 10. gantt (grouped) ─────────
    s = prs.slides.add_slide(blank)
    add_title(s, "gantt · grouped, 6 months, planned vs actual")
    add_gantt(s, origin, body_size, style,
              columns=[f"{m}月" for m in range(1, 7)],
              groups=[
                  {"label": "Backend", "tasks": [
                      {"label": "API redesign", "plannedStart": 1, "plannedEnd": 3,
                       "actualStart": 1, "actualEnd": 4, "value": "v2"},
                      {"label": "Migration",    "plannedStart": 3, "plannedEnd": 5,
                       "actualStart": 4, "actualEnd": 6, "tone": "dark"},
                  ]},
                  {"label": "Frontend", "tasks": [
                      {"label": "Redesign",     "plannedStart": 2, "plannedEnd": 5,
                       "actualStart": 2, "actualEnd": 5},
                  ]},
                  {"label": "Platform", "tasks": [
                      {"label": "Observability", "plannedStart": 1, "plannedEnd": 6,
                       "actualStart": 1, "actualEnd": 6, "tone": "soft"},
                  ]},
              ])

    # ───────── 11. funnel ─────────
    s = prs.slides.add_slide(blank)
    add_title(s, "funnel · 5 steps, narrow-top")
    add_funnel(s, origin, body_size, [
        {"label": "Awareness", "value": "1.2M visitors", "width": "100%"},
        {"label": "Interest",  "value": "340K signups",  "width": "62%"},
        {"label": "Trial",     "value": "78K activated", "width": "38%"},
        {"label": "Purchase",  "value": "22K customers", "width": "22%"},
        {"label": "Retention", "value": "18K @ 90 days", "width": "16%"},
    ], style, title="Conversion funnel", note="Last 30 days, all channels")

    # ───────── 12. timeline ─────────
    s = prs.slides.add_slide(blank)
    add_title(s, "timeline · 4 phases, boundary dates")
    add_timeline(s, origin, body_size, [
        {"label": "PHASE 1", "title": "Discovery", "duration": "2 weeks",
         "deliverables": ["Stakeholder interviews", "Requirements doc", "Risk register"],
         "exit_gate": "PRD signed"},
        {"label": "PHASE 2", "title": "Build MVP", "duration": "8 weeks", "tone": "strong",
         "deliverables": ["Backend services", "Frontend prototype", "Data pipelines"],
         "exit_gate": "QA accepted"},
        {"label": "PHASE 3", "title": "Pilot", "duration": "4 weeks",
         "deliverables": ["5 design partners", "Feedback loop", "Iteration backlog"],
         "exit_gate": "NPS > 30"},
        {"label": "PHASE 4", "title": "GA Launch", "duration": "2 weeks", "tone": "dark",
         "deliverables": ["Marketing push", "Sales enablement", "Support readiness"],
         "exit_gate": "Public launch"},
    ], style, boundary_dates=["Jan 1", "Jan 15", "Mar 15", "Apr 15", "May 1"])

    # ───────── 13. flow_matrix ─────────
    s = prs.slides.add_slide(blank)
    add_title(s, "flow_matrix · 4 layers + platform strip")
    add_flow_matrix(s, origin, body_size, [
        {"leftLabel": "Input Layer", "nodes": [
            {"title": "User query",     "desc": "Natural language"},
            {"title": "Context",        "desc": "Session history"},
            {"title": "Documents",      "desc": "RAG sources"},
        ]},
        {"leftLabel": "Understanding", "nodes": [
            {"title": "Intent",         "desc": "Classify"},
            {"title": "Entities",       "desc": "Extract NER"},
            {"title": "Routing",        "desc": "Pick tool"},
        ]},
        {"leftLabel": "Generation", "nodes": [
            {"title": "Retrieval",      "desc": "Embed + search"},
            {"title": "Composition",    "desc": "LLM call"},
        ]},
        {"leftLabel": "Output", "nodes": [
            {"title": "Response",       "desc": "Stream tokens"},
            {"title": "Attribution",    "desc": "Cite sources"},
        ]},
    ], style, title="Multi-layer architecture",
       platform={"label": "Foundation Models · Embeddings · Vector store",
                 "desc": "Shared infrastructure across all reasoning paths"})

    save_pptx(prs, out_path)
    return len(prs.slides)


def render_to_jpgs(pptx_path: Path, out_dir: Path) -> int:
    """Convert PPTX → PDF (soffice) → JPGs (pdftoppm). Returns JPG count."""
    pdf_path = out_dir / (pptx_path.stem + ".pdf")
    if pdf_path.exists():
        pdf_path.unlink()
    # 1) PPTX → PDF
    r = subprocess.run(
        ["soffice", "--headless", "--convert-to", "pdf",
         "--outdir", str(out_dir), str(pptx_path)],
        check=True, capture_output=True,
    )
    if not pdf_path.exists():
        print("soffice stdout:", r.stdout.decode(errors="ignore"))
        print("soffice stderr:", r.stderr.decode(errors="ignore"))
        raise SystemExit("soffice did not produce a PDF")
    # 2) PDF → JPGs
    for old in out_dir.glob("slide-*.jpg"):
        old.unlink()
    subprocess.run(
        ["pdftoppm", "-jpeg", "-r", "144", str(pdf_path),
         str(out_dir / "slide")],
        check=True,
    )
    return len(list(out_dir.glob("slide-*.jpg")))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build-only", action="store_true",
                    help="skip soffice/pdftoppm rendering")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    deck = OUT_DIR / "gallery.pptx"
    n = build_deck(deck)
    print(f"built {deck} ({n} slides)")

    # always run the validator
    val = subprocess.run(
        ["python3", str(SKILL_ROOT / "scripts" / "view_issues.py"),
         str(deck)],
        capture_output=True,
    )
    import json
    issues = json.loads(val.stdout or b"[]")
    print(f"view_issues: {len(issues)} findings (exit {val.returncode})")
    summary = {}
    for i in issues:
        key = (i["check"], i["severity"])
        summary[key] = summary.get(key, 0) + 1
    for k, v in sorted(summary.items()):
        print(f"  {k[1]:8s} {k[0]:24s} ×{v}")

    if args.build_only:
        return
    if not shutil.which("soffice"):
        print("soffice not on PATH — skipping render")
        return
    if not shutil.which("pdftoppm"):
        print("pdftoppm not on PATH — skipping render")
        return
    n_jpg = render_to_jpgs(deck, OUT_DIR)
    print(f"rendered {n_jpg} jpgs into {OUT_DIR}")


if __name__ == "__main__":
    main()
