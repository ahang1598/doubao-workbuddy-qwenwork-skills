# artifact-preview hub

Render workspace deliverables (pdf / pptx / docx / xlsx / html / images / zip)
into text dumps + page screenshots + collages so a multimodal LLM can
visually inspect its own output via `Read`.

Packaged as a **superskill** hub: the model discovers it via the
standard catalog and invokes it through `Bash` + `Read`. See
`SKILL.md` for the model-facing usage doc.

## Hub layout (verifier-hub-style)

```
artifact-preview/
├── SKILL.md                model-facing skill description (frontmatter + body)
├── README.md               human-facing notes (you are here)
├── requirements.txt        third-party deps (informational; VM image owns install)
├── bin/preview             python3 entrypoint (sets sys.path → lib/, dispatches CLI)
├── lib/
│   ├── _common.py          ok/err/emit/lazy_import, logical paths, file:// URIs,
│   │                       cross-platform binary lookup, install hints
│   ├── _types.py           dataclasses + kind constants
│   ├── cache.py            content-hash output dir resolution
│   ├── manifest.py         manifest.json read/write
│   ├── dispatch.py         kind detection + render() entry
│   ├── cli.py              argparse subcommand layer
│   ├── pdf.py              IO wrapper → render.pdf
│   ├── pptx.py             IO wrapper → render.pptx
│   ├── docx.py             IO wrapper → render.docx
│   ├── xlsx.py             IO wrapper → render.xlsx
│   ├── html.py             IO wrapper → render.html
│   ├── image.py            plain image passthrough + thumbnail
│   ├── text.py             plain text copy
│   ├── zip_.py             entry list dump
│   ├── collage.py          IO wrapper → render.collage + thumbnail
│   └── render/             ▼ shared rendering primitives ▼
│       ├── __init__.py     exports + lazy-import contract
│       ├── constants.py    DPI / page caps / collage tile params
│       ├── types.py        PageImage / CollageResult dataclasses
│       ├── pdf.py          PyMuPDF text + per-page PNG
│       ├── pptx.py         python-pptx text + LibreOffice→PDF screenshots
│       ├── docx.py         python-docx paragraphs + tables
│       ├── xlsx.py         openpyxl full-workbook dump
│       ├── html.py         Playwright full-page + segmented screenshots
│       └── collage.py      multi-page tiling
└── tests/                  pytest fixtures (synthetic, no binary blobs)
```

## Why two layers?

* **`lib/render/`** — pure primitives (bytes in, bytes/PIL out).
  Single source of truth shared with the host-side
  `swalm.core.utils.artifact_render` module (which re-exports from
  here so `trace_llm_judge.py` keeps working without a code copy).
* **`lib/<kind>.py`** — IO wrappers: read source bytes from disk,
  call the matching `render.<kind>` primitive, write artifacts
  (PNG/JPG/text.md) into the deterministic `.preview/<hash>/` cache,
  populate the JSON manifest.

This is the same layering verifier-hub uses (`bin/verifier` →
`lib/_common.py` → `lib/<family>.py`).

## Local development

Run the CLI directly without installation:

```bash
./bin/preview render path/to/file.pptx --max-pages 5
```

Run the test suite:

```bash
pytest tests/ -v
```

The test suite generates fixture files programmatically (PIL.Image,
openpyxl.Workbook, python-pptx.Presentation, etc.) so the repo carries
no binary blobs.

## Dependencies

`requirements.txt` lists the optional Python deps. The `superskill`
delivery model assumes the VM image already has them installed (same
contract as verifier-hub); if any are missing the skill degrades
gracefully:

* PyMuPDF (`fitz`) → PDF text + screenshots disabled
* python-pptx → PPTX text disabled
* python-docx → DOCX text disabled
* openpyxl → XLSX text disabled
* Pillow → collage + thumbnail disabled
* (no playwright dependency — HTML rendering uses the system
  `chromium-browser` CLI directly; see `System-level deps` below.)

In every case, missing deps surface as a JSON `warnings` entry rather
than an exception, so callers (NotifyHuman flows, judges) don't fail
on capability gaps.

System-level deps:

* LibreOffice — required for PPTX → PDF → PNG conversion.
* A Chromium-family browser — required for HTML page screenshots.
  On the rollout VM image the system `chromium-browser` package provides
  this, so no Playwright install step is needed.

Both are looked up on `$PATH` and, because the macOS and Windows installers
do not add themselves to `PATH`, at the standard install locations for the
platform. `--soffice` / `--chromium` and the `ARTIFACT_PREVIEW_SOFFICE` /
`ARTIFACT_PREVIEW_CHROMIUM` environment variables override both.

## Programmatic API

```python
import sys
sys.path.insert(0, "/path/to/skills/artifact-preview")
from lib import dispatch_render as render, RenderOptions

m = render("./report.pptx", options=RenderOptions(max_pages=5, collage=True))
print(m.thumbnail_relpath, m.collages, m.text_relpath)
```

## Relationship to host-side `swalm.core.utils.artifact_render`

The host-side module at
`packages/swalm-core/src/swalm/core/utils/artifact_render/` is a
**thin re-export** from this hub:

```python
# swalm.core.utils.artifact_render/__init__.py
from superskill.hub_skills.artifact_preview.lib.render import *  # noqa
```

This keeps the canonical implementation here in the hub (single
source of truth) while letting `trace_llm_judge.py` and other
host-side judge code keep their existing `from
swalm.core.utils.artifact_render import extract_pdf` imports.

## Invariants worth keeping

* **One JSON object on stdout per invocation**, including argument errors
  (`BAD_ARGS`). Only `--help` prints prose. Errors never go to stderr and never
  leak a traceback.
* **`ok` means the tool ran**; a missing optional dependency is `ok: true` plus
  a `warnings` entry, not an error.
* **Collages cover every rendered page.** `render/collage.py` balances pages
  across tiles rather than filling greedily, because a greedy split can leave a
  one-page remainder that used to be dropped silently. `lib/collage.py` also
  emits a warning if any page still ends up uncovered.
* **`--text-only` never deletes images** an earlier full render produced; it
  carries them forward and says so in `warnings`.
* **`file://` URLs are built with `Path.as_uri()`**, never by string
  concatenation. Concatenation breaks on Windows (the drive letter is parsed as
  the URL host) and leaves spaces and non-ASCII characters unescaped everywhere.
* **A screenshot existing is not proof the right page was captured.** The HTML
  renderer stages the document with a sentinel and confirms it via `--dump-dom`,
  because a browser that fails to load a file still writes a perfectly valid
  screenshot of its own start page.
* **Reported paths keep the caller's prefix.** `_common.logical_abspath` avoids
  `resolve()` so the workspace symlink and the sandbox bind mount are not
  collapsed into a path the agent never typed.

## Platform support

Linux and macOS. Windows is not supported: `bin/preview` is an extension-less
shebang script, so `cmd.exe` and PowerShell cannot execute it directly. The
Python code itself is portable, so `python bin/preview ...` does work.

## Packaging

The zip published to TOS contains `bin/`, `lib/`, `SKILL.md`,
`requirements.txt` and `README.md` at the top level — no wrapper directory,
because the installer creates the per-skill directory from the zip name.
`__pycache__` and the test suite are excluded: the VM runs Python 3.10 and
would ignore bytecode compiled elsewhere anyway.
