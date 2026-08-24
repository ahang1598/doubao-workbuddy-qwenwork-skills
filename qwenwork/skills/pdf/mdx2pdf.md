# mdx2pdf — designed/MDX-rendered PDF route

MDX source in → QwenWork-branded PDF out. **You author good MDX and invoke one semantic script. It uses a ready local md2pdf runtime or the cloud capability without changing user-visible parameters.**

## TL;DR runbook

```sh
python3 scripts/generate_mdx_pdf.py report.mdx --output report.pdf \
  --page-size A4 --title "Q2 Review"
# done. Read the PDF before delivering.
```

Write the MDX (palette in `references/components.md`), invoke the CLI, deliver the PDF. Everything else in this file is reference for steps you only sometimes need.

## When this is the right route

Pick MDX generation over the raw-Python alternates (reportlab / pypdf authoring) when ANY of:

- The user asks to **render**, **export**, **generate a PDF**, **convert a Markdown/MDX**, or wants a "report / briefing / whitepaper / deep-research output / long-form doc".
- Output should look **branded** (QwenWork wordmark, Inter + Noto CJK, qwenwork code theme).
- Content has any of: **math** ($x^2$, KaTeX), **code blocks** (Shiki highlighting), **Mermaid diagrams**, **citations**, **callouts**, **tables of contents**, **CJK text**.
- A4 / US Letter page size; multi-page with headers/footers.

Use reportlab instead only when the user explicitly wants pixel-precise programmatic layout, hand-positioned vector shapes, or a one-shot mail-merge style generator.

## Quick recipe

```sh
python3 scripts/generate_mdx_pdf.py path/to/source.mdx --output out.pdf \
  --page-size A4 --title "Report Title"
```

Key flags:
- `--output OUTPUT.pdf` — required local output path
- `--page-size A4` or `--page-size Letter` — page size (default `A4`)
- `--title "..."` — appears in PDF metadata + page header (falls back to frontmatter `title:` or filename)
- `--no-header` — drop the QwenWork brand header on page 1
- `--no-page-numbers` — drop the footer page counter
- `--base-dir DIR` — local `md2pdf` only; resolve relative image paths from DIR
- `--components PATH.tsx` — local `md2pdf` only; extend the component palette
- `--render-profile auto|plain|branded` — prefer the best compatible backend

The typed cloud service accepts one self-contained `.md` or `.mdx` file up to
5 MiB and does not accept caller-provided components or a base directory. These
are cloud-backend limits, not global Skill limits. When the source relies on
relative assets, custom components, or exceeds that upload limit, keep the
request on a compatible local `md2pdf` path. Use inline data URIs only when a
self-contained cloud render is desirable.

## Authoring guide

The payoff of this route is the **MDX component palette**: drop `<Cover>`, `<Callout>`, `<TOC>`, `<Mermaid>`, `<Cite>`/`<Bibliography>`, charts, etc. into an otherwise plain Markdown file. Full reference: `mdx2pdf/references/components.md`. Sketch:

```mdx
---
title: Quarterly Report
author: QwenWork Research
date: 2026-06-09
---

<Cover
  eyebrow="Quarterly Report"
  title="The Future of Knowledge Work"
  subtitle="How automation and augmentation reshape 2026"
  author="QwenWork Research"
  date="June 2026"
/>

## Table of contents
<TOC depth={3} />

## Executive summary

<Callout type="tip" title="Headline">
The two-line insight worth pulling out into a coloured card.
</Callout>

## Findings

A claim<Cite id="smith2024" /> backed by data.

| Domain   | Score |
| -------- | ----: |
| Research |   8.9 |
| Design   |   7.4 |

The integral $\int_0^\infty e^{-x}\,dx = 1$ and code:

```python
def f(x): return x + 1
```

<Mermaid>{`flowchart LR; A --> B --> C`}</Mermaid>

<Bibliography entries={{
  "smith2024": <>Smith, J. <em>Title</em>, Journal, 2024.</>,
}} />
```

Tables with ≥8 columns and oversized Mermaid SVGs are **auto-promoted** to landscape pages — you don't need to wrap them in `<Landscape>` yourself.

For wide content that should explicitly take a sideways page, use:

```mdx
<Landscape caption="optional caption below">
  <Mermaid>{`...big diagram...`}</Mermaid>
</Landscape>
```

## Component palette — one-line summary

Full reference in `mdx2pdf/references/components.md`; tokens (colour / type / margins) in `mdx2pdf/references/styling-tokens.md`.

| Component | Use for |
|---|---|
| `<Cover>` | Full-page report cover; first element of any multi-page report |
| `<TOC depth={3} />` | Table of contents (populated client-side from headings) |
| `<PageBreak />` | Force a page break — sparingly, e.g. before an Appendix |
| `<Landscape caption>` | Sideways page for wide content (auto-promoted for ≥8-col tables / wide Mermaid) |
| `<Two>` / `<Col>` | Two-column grid |
| `<Aside>` | Right-floated callout |
| `<Callout type="note|tip|warning|danger" title>` | Boxed annotation |
| `<Cite id>` / `<Bibliography entries={…}>` | In-text citations + bibliography list |
| `<Figure src caption credit width>` | Image with caption (local files embedded as data URIs) |
| `<Mermaid caption>{`...`}</Mermaid>` | Mermaid diagram (rendered in-browser before PDF capture) |
| `<BarChart>` / `<PieChart>` / `<LineChart>` / `<AreaChart>` | Server-side SVG charts (qwenwork palette, single or multi-series, grouped/stacked/horizontal) |

CommonMark features all work as expected: headings, GFM tables, fenced code (Shiki highlights it), `$inline$` / `$$display$$` math (KaTeX SSR), task lists, definition lists, footnotes, YAML frontmatter (`title:` becomes PDF metadata).

## When you write MDX for the user

1. Open with a `<Cover>` for any multi-page report.
2. Put `<TOC depth={3} />` as the second section if there are 4+ top-level sections.
3. Use `<Callout type="note|tip|warning|danger">` for emphasis, not bold-only sentences.
4. Use real Mermaid (`<Mermaid>{`...`}</Mermaid>`) for any flow or sequence. Wrap in `<Landscape>` if the diagram has ≥6 nodes in a row.
5. Cite sources with `<Cite id="...">` and end with `<Bibliography entries={{...}} />`.
6. Save the source as `report.mdx`, then call the semantic generation script.

## What NOT to do

- Don't embed raw HTML — use the MDX components instead.
- Don't hand-roll a TOC — `<TOC>` populates from headings client-side.
- Don't include screenshots of code blocks; use real fenced code so Shiki can highlight them.
- Don't manually paginate — let the engine break content; use `<PageBreak />` only when you genuinely want a break (e.g., before appendices).
- Don't reach for `reportlab` to draw a "branded" report — that's this route's job; reportlab is for raw, programmatic, pixel-positioned PDFs.

## QA — always read the PDF before delivering

```sh
python3 scripts/generate_mdx_pdf.py report.mdx --output report.pdf
# Then open report.pdf and scan every page. Common issues:
```

| Symptom | Fix |
|---|---|
| Tofu (□□□) where CJK text should be | The cloud rendering profile is missing or misconfiguring CJK fonts; report the operation ID for service diagnosis |
| Math renders as raw `$...$` | KaTeX failed — check the expression compiles standalone; escape `\` inside MDX (`\\`) |
| Mermaid diagram missing | Mermaid threw at runtime — simplify the source, or check the syntax in mermaid.live first |
| Wide table spills off page | Auto-landscape didn't trigger (column count < 8). Wrap the table in `<Landscape>` manually |
| Local image rejected | The cloud MVP accepts self-contained sources only; inline it as a data URI |
| Header / page numbers missing where you want them | `--no-header` / `--no-page-numbers` flags |

## Examples

Runnable samples to crib from (under `mdx2pdf/examples/`):

- `minimal.mdx` — bare-bones single-page doc; smoke test for the install
- `deep-research-sample.mdx` — full report shape: cover, TOC, callouts, math, code, tables, Mermaid, citations, CJK, definition list, bibliography

## Execution environment

The script prefers the typed cloud capability when the source and requested
features fit its contract. Otherwise it probes for an existing `md2pdf` command
and renders locally. Version 0.4.7+ receives `--brand qwenwork-cn`; an older detected
release receives `--no-header` so its legacy MuleRun mark cannot leak into the
output. An unrecognized version still receives the explicit QwenWork brand and
may use the cloud when the request is cloud-compatible. When `md2pdf` is absent,
an ordinary `.md` may use the packaged ReportLab converter locally if its
declared dependencies are already available. `plain` selects that raw local
layout; `branded` avoids silently degrading to ReportLab. It never installs
Node, React, Playwright, Chromium, Python packages, or md2pdf automatically.

Use `QWENWORK_DOCUMENT_EXECUTION_MODE=cloud_required` only for an explicit
cloud acceptance test and `local_required` only for a local-runtime test.
Normal tasks use `auto`. A retryable failure may switch backend once; cloud
401/403 authentication failures and 404 capability discovery failures are not
retried. The script validates the resulting PDF before reporting success.

## File map

```
pdf/                              ← skill root (where SKILL.md + mdx2pdf.md live)
├── SKILL.md                      ← pdf skill entry (route selection)
├── mdx2pdf.md                    ← this file (designed/MDX-rendered PDF route reference)
└── mdx2pdf/                      ← mdx2pdf route assets (sibling to this file)
    ├── references/
    │   ├── components.md         ← full MDX component palette
    │   └── styling-tokens.md     ← colour / typography / margin tokens
    └── examples/
        ├── minimal.mdx
        └── deep-research-sample.mdx
```
