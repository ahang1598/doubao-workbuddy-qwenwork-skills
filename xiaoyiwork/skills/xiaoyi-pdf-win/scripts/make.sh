# 基于 MiniMax-AI/skills/minimax-pdf 修改，原项目协议：MIT License
# 原版权：Copyright (c) 2025 MiniMax AI
#!/usr/bin/env bash
# make.sh — xiaoyi-pdf unified CLI
# Usage: bash make.sh <command> [options]
#
# Commands:
#   check                          Verify all dependencies
#   init                           Create an isolated PDF job
#   session --session-id ID        Restore one explicit PDF job
#   run   --title T --type TYPE    Full pipeline → output.pdf
#         --out FILE               Output path (default: output.pdf)
#         --author A --date D
#         --subtitle S
#         --abstract A             Optional abstract text for cover
#         --cover-image URL        Optional cover image URL/path
#         --content FILE           Path to content.json (optional)
#   demo                           Build a full-featured demo to demo.pdf
#
# Document types:
#   report proposal resume portfolio academic general
#   minimal stripe diagonal frame editorial
#   magazine darkroom terminal poster
#
# Content block types:
#   h1 h2 h3 body bullet numbered callout table
#   image figure code math chart flowchart bibliography
#   divider caption pagebreak spacer
#
# Exit codes: 0 success, 1 usage error, 2 dep missing, 3 runtime error

set -euo pipefail
SCRIPTS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 小艺 Work 注入的解释器与后台安装 Skill 依赖时使用的 Python 一致，必须优先。
# 用数组保存命令，兼容 Windows 路径中的空格以及 `py -3` 这种多参数兜底。
PY_CMD=()
if [[ -n "${CLAW_PYTHON_EXE:-}" ]] && "$CLAW_PYTHON_EXE" -c "import sys" &>/dev/null; then
  PY_CMD=("$CLAW_PYTHON_EXE")
else
  for candidate in python3 python; do
    if command -v "$candidate" &>/dev/null && "$candidate" -c "import sys" &>/dev/null; then
      PY_CMD=("$candidate")
      break
    fi
  done
  if [[ ${#PY_CMD[@]} -eq 0 ]] && command -v py &>/dev/null && py -3 -c "import sys" &>/dev/null; then
    PY_CMD=(py -3)
  fi
fi

if [[ ${#PY_CMD[@]} -eq 0 ]]; then
  echo "ERROR: Python 3 not found" >&2
  exit 2
fi

run_py() {
  "${PY_CMD[@]}" "$@"
}

require_create_deps() {
  local missing
  missing=$(run_py -c '
import importlib.util
modules = {
    "reportlab": "reportlab",
    "pypdf": "pypdf",
    "playwright": "playwright",
    "matplotlib": "matplotlib",
    "Pillow": "PIL",
}
print(", ".join(name for name, module in modules.items()
                 if importlib.util.find_spec(module) is None))
')
  if [[ -n "$missing" ]]; then
    red "Missing PDF generation dependencies for ${PY_CMD[*]}: $missing"
    red "Wait for 小艺 Work background installation or retry from the skill page."
    exit 2
  fi
}

# ── Colour helpers ─────────────────────────────────────────────────────────────
red()    { printf '\033[0;31m%s\033[0m\n' "$*"; }
green()  { printf '\033[0;32m%s\033[0m\n' "$*"; }
yellow() { printf '\033[0;33m%s\033[0m\n' "$*"; }
bold()   { printf '\033[1m%s\033[0m\n' "$*"; }

validate_content_json() {
  local file="$1"
  # 文件路径作为 argv 传递，避免 Git Bash 的 /d/... 路径被嵌入 Python 源码后
  # 失去 MSYS 参数转换机会，也避免引号/反斜杠破坏 -c 代码。
  run_py -c '
import json, sys
path = sys.argv[1]
with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)
if not isinstance(data, list):
    print("ERROR: content.json must be a JSON array (list of blocks)", file=sys.stderr)
    sys.exit(1)
' "$file" || { red "Invalid JSON in $file"; exit 3; }
  green "  JSON validation passed"
}

snapshot_content_json() {
  local source_file="$1"
  local snapshot_file="$2"
  run_py -c '
import json, os, sys
source, destination = sys.argv[1:3]
with open(source, "r", encoding="utf-8") as stream:
    data = json.load(stream)
if not isinstance(data, list):
    raise ValueError("content.json must be a JSON array (list of blocks)")
os.makedirs(os.path.dirname(os.path.abspath(destination)), exist_ok=True)
tmp = destination + ".tmp"
with open(tmp, "w", encoding="utf-8") as stream:
    json.dump(data, stream, ensure_ascii=False, indent=2)
os.replace(tmp, destination)
' "$source_file" "$snapshot_file" || {
    red "Invalid or unreadable JSON in $source_file"
    exit 3
  }
}

# ── isolated job state ────────────────────────────────────────────────────────
cmd_init() {
  run_py "$SCRIPTS/session_state.py" init
}

cmd_session() {
  if [[ "${1:-}" != "--session-id" || -z "${2:-}" ]]; then
    echo "Usage: bash make.sh session --session-id <UUID>" >&2
    exit 1
  fi
  run_py "$SCRIPTS/session_state.py" load --session-id "$2"
}

# ── check ──────────────────────────────────────────────────────────────────────
cmd_check() {
  local ok=true
  bold "Checking dependencies..."

  # Python
  green "  ✓ Python $(run_py --version 2>&1 | awk '{print $2}') (${PY_CMD[*]})"

  # reportlab
  if run_py -c "import reportlab" 2>/dev/null; then
    green "  ✓ reportlab"
  else
    yellow "  ⚠ reportlab not installed — wait for 小艺 Work dependency installation"
    ok=false
  fi

  # pypdf
  if run_py -c "import pypdf" 2>/dev/null; then
    green "  ✓ pypdf"
  else
    yellow "  ⚠ pypdf not installed — wait for 小艺 Work dependency installation"
    ok=false
  fi

  # playwright (Python)
  if run_py -c "import playwright" 2>/dev/null; then
    green "  ✓ playwright"
  else
    yellow "  ⚠ playwright not installed — wait for 小艺 Work dependency installation"
    ok=false
  fi

  # matplotlib is required for math/chart/flowchart; never silently degrade a
  # formula document to source text.
  if run_py -c "import matplotlib" 2>/dev/null; then
    green "  ✓ matplotlib (math, chart, flowchart blocks enabled)"
  else
    yellow "  ⚠ matplotlib not installed — wait for 小艺 Work dependency installation"
    ok=false
  fi

  # Pillow
  if run_py -c "import PIL" 2>/dev/null; then
    green "  ✓ Pillow (image watermark support enabled)"
  else
    yellow "  ⚠ Pillow not installed — image watermarks will fail"
    ok=false
  fi

  # pdfplumber
  if run_py -c "import pdfplumber" 2>/dev/null; then
    green "  ✓ pdfplumber (table extraction enabled)"
  else
    yellow "  ⚠ pdfplumber not installed — table extraction will fail"
    ok=false
  fi

  # pandas
  if run_py -c "import pandas" 2>/dev/null; then
    green "  ✓ pandas (table data processing enabled)"
  else
    yellow "  ⚠ pandas not installed — table extraction will fail"
    ok=false
  fi

  # openpyxl
  if run_py -c "import openpyxl" 2>/dev/null; then
    green "  ✓ openpyxl (Excel output enabled)"
  else
    yellow "  ⚠ openpyxl not installed — Excel output will fail"
    ok=false
  fi

  if $ok; then
    green "\nAll dependencies satisfied."
    exit 0
  else
    yellow "\nSome dependencies are not ready. Wait for 小艺 Work background installation or retry from the skill page."
    exit 2
  fi
}

# ── run ────────────────────────────────────────────────────────────────────────
cmd_run() (
  local title="Untitled Document"
  local type="general"
  local author=""
  local date=""
  local subtitle=""
  local abstract=""
  local cover_image=""
  local accent=""
  local cover_bg=""
  local content_file=""
  local session_id=""
  local out=""
  local workdir=""
  local save_mask

  require_create_deps

  : ${TMPDIR:=/tmp}
  save_mask=$(umask)
  umask 077
  workdir=$(mktemp -d "${TMPDIR}/XXXXXXXXXXXXXXXXXX")
  if [[ $? -ne 0 ]]; then
    umask "${save_mask}"
    red "Failed to create temporary directory"
    exit 1
  fi
  umask "${save_mask}"
  trap 'rm -rf "'"${workdir}"'"' EXIT

  # Parse options
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --title)        title="$2";        shift 2 ;;
      --type)         type="$2";         shift 2 ;;
      --author)       author="$2";       shift 2 ;;
      --date)         date="$2";         shift 2 ;;
      --subtitle)     subtitle="$2";     shift 2 ;;
      --abstract)     abstract="$2";     shift 2 ;;
      --cover-image)  cover_image="$2";  shift 2 ;;
      --accent)       accent="$2";       shift 2 ;;
      --cover-bg)     cover_bg="$2";     shift 2 ;;
      --content)      content_file="$2"; shift 2 ;;
      --session-id)   session_id="$2";   shift 2 ;;
      --out)          out="$2";          shift 2 ;;
      *) echo "Unknown option: $1"; exit 1 ;;
    esac
  done

  if [[ -n "$session_id" ]]; then
    if [[ -n "$content_file" ]]; then
      red "Use either --session-id or --content, not both."
      exit 1
    fi
    eval "$(run_py "$SCRIPTS/session_state.py" load --session-id "$session_id")"
    content_file="$PDF_CONTENT_PATH"
    if [[ -z "$out" ]]; then
      out="$PDF_DELIVERY_DIR/output-${PDF_JOB_ID%%-*}.pdf"
    fi
  fi
  [[ -n "$out" ]] || out="$PWD/output.pdf"

  if [[ -n "$content_file" ]]; then
    # Freeze caller-owned content before any rendering starts. Later edits by
    # another exec cannot change this invocation's document.
    snapshot_content_json "$content_file" "$workdir/content.json"
    content_file="$workdir/content.json"
  fi

  bold "Building: $title"
  echo "  Type    : $type"
  echo "  Output  : $out"

  # Step 1: tokens
  echo ""
  bold "Step 1/4  Generating design tokens..."
  local accent_args=()
  [[ -n "$accent"   ]] && accent_args+=(--accent   "$accent")
  [[ -n "$cover_bg" ]] && accent_args+=(--cover-bg "$cover_bg")
  run_py "$SCRIPTS/palette.py" \
    --title "$title" --type "$type" \
    --author "$author" --date "$date" \
    --out "$workdir/tokens.json" \
    "${accent_args[@]+"${accent_args[@]}"}"

  # Inject optional cover fields into tokens.json
  if [[ -n "$abstract" || -n "$cover_image" ]]; then
    PDF_ABSTRACT="$abstract" PDF_COVER_IMAGE="$cover_image" PDF_TOKENS="$workdir/tokens.json" \
    run_py - <<'PYEOF'
import json, os
with open(os.environ["PDF_TOKENS"]) as f:
    t = json.load(f)
abstract = os.environ.get("PDF_ABSTRACT", "")
cover_image = os.environ.get("PDF_COVER_IMAGE", "")
if abstract:
    t["abstract"] = abstract
if cover_image:
    t["cover_image"] = cover_image
with open(os.environ["PDF_TOKENS"], "w") as f:
    json.dump(t, f, indent=2)
PYEOF
  fi

  run_py -c "
import json,sys
t=json.load(sys.stdin)
print(f'  Mood    : {t[\"mood\"]}')
print(f'  Pattern : {t[\"cover_pattern\"]}')
print(f'  Fonts   : {t[\"font_display\"]} / {t[\"font_body\"]}')" < "$workdir/tokens.json"

  # Step 2: cover HTML + render
  echo ""
  bold "Step 2/4  Rendering cover..."
  local subtitle_args=()
  [[ -n "$subtitle" ]] && subtitle_args=(--subtitle "$subtitle")
  run_py "$SCRIPTS/cover.py" \
    --tokens "$workdir/tokens.json" \
    --out "$workdir/cover.html" \
    "${subtitle_args[@]+"${subtitle_args[@]}"}"

  run_py "$SCRIPTS/render_cover.py" \
    --input "$workdir/cover.html" \
    --out   "$workdir/cover.pdf"
  green "  ✓ Cover rendered"

  # Step 3: body
  echo ""
  bold "Step 3/4  Rendering body pages..."
  if [[ -z "$content_file" ]]; then
    # Generate a minimal placeholder body
    cat > "$workdir/content.json" <<'JSON'
[
  {"type":"h1",   "text":"Document Body"},
  {"type":"body", "text":"Replace this with your content.json file using --content path/to/content.json"},
  {"type":"body", "text":"See the content.json schema in the skill README for the full list of supported block types: h1, h2, h3, body, bullet, callout, table, pagebreak, spacer."}
]
JSON
    content_file="$workdir/content.json"
    yellow "  No content file provided — using placeholder body."
  fi

  validate_content_json "$content_file"

  run_py "$SCRIPTS/render_body.py" \
    --tokens  "$workdir/tokens.json" \
    --content "$content_file" \
    --out     "$workdir/body.pdf"
  green "  ✓ Body rendered"

  # Step 4: merge
  echo ""
  bold "Step 4/4  Merging and QA..."
  run_py "$SCRIPTS/merge.py" \
    --cover "$workdir/cover.pdf" \
    --body  "$workdir/body.pdf" \
    --out   "$out" \
    --title "$title"

  # Cleanup handled by trap EXIT
)

# ── fill ──────────────────────────────────────────────────────────────────────
cmd_fill() {
  local input="" out="" values="" data_file="" inspect_only=false

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --input)   input="$2";     shift 2 ;;
      --out)     out="$2";       shift 2 ;;
      --values)  values="$2";    shift 2 ;;
      --data)    data_file="$2"; shift 2 ;;
      --inspect) inspect_only=true; shift ;;
      *) echo "Unknown option: $1"; exit 1 ;;
    esac
  done

  if [[ -z "$input" ]]; then
    echo "Usage: make.sh fill --input form.pdf [--out filled.pdf] [--values '{...}'] [--data values.json] [--inspect]"
    exit 1
  fi

  if $inspect_only || [[ -z "$out" && -z "$values" && -z "$data_file" ]]; then
    bold "Inspecting form fields in: $input"
    run_py "$SCRIPTS/fill_inspect.py" --input "$input"
    return
  fi

  bold "Filling form: $input → $out"

  # Write values to temp file to avoid shell quoting issues with JSON
  local val_file=""
  if [[ -n "$values" ]]; then
    val_file=$(mktemp "${TMPDIR:-/tmp}/minimax_values.XXXXXXXXXX")
    echo "$values" > "$val_file"
  fi

  local val_args=()
  if [[ -n "$val_file" ]];    then val_args+=(--data "$val_file"); fi
  if [[ -n "$data_file" ]];   then val_args+=(--data "$data_file"); fi

  run_py "$SCRIPTS/fill_write.py" --input "$input" --out "$out" "${val_args[@]}"

  # Cleanup temp file
  if [[ -n "$val_file" && -f "$val_file" ]]; then
    rm -f "$val_file"
  fi
}

# ── reformat ───────────────────────────────────────────────────────────────────
cmd_reformat() (
  local input="" title="Reformatted Document" type="general"
  local author="" date="" out="output.pdf" subtitle=""
  local tmpdir=""
  local save_mask

  : ${TMPDIR:=/tmp}
  save_mask=$(umask)
  umask 077
  tmpdir=$(mktemp -d "${TMPDIR}/XXXXXXXXXXXXXXXXXX")
  if [[ $? -ne 0 ]]; then
    umask "${save_mask}"
    red "Failed to create temporary directory"
    exit 1
  fi
  umask "${save_mask}"
  trap 'rm -rf "'"${tmpdir}"'"' EXIT

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --input)    input="$2";    shift 2 ;;
      --title)    title="$2";    shift 2 ;;
      --type)     type="$2";     shift 2 ;;
      --author)   author="$2";   shift 2 ;;
      --date)     date="$2";     shift 2 ;;
      --subtitle) subtitle="$2"; shift 2 ;;
      --out)      out="$2";      shift 2 ;;
      *) echo "Unknown option: $1"; exit 1 ;;
    esac
  done

  if [[ -z "$input" ]]; then
    echo "Usage: make.sh reformat --input source.md --title T --type TYPE --out output.pdf"
    exit 1
  fi

  bold "Parsing: $input"
  run_py "$SCRIPTS/reformat_parse.py" --input "$input" --out "$tmpdir/content.json"
  green "  ✓ Parsed to content.json"

  validate_content_json "$tmpdir/content.json"

  bold "Applying design and building PDF..."
  local sub_args=()
  [[ -n "$subtitle" ]] && sub_args=(--subtitle "$subtitle")

  cmd_run \
    --title "$title" --type "$type" \
    --author "$author" --date "$date" \
    --content "$tmpdir/content.json" \
    --out "$out" \
    "${sub_args[@]+"${sub_args[@]}"}"

  # Cleanup handled by trap EXIT
)

# ── demo ──────────────────────────────────────────────────────────────────────
cmd_demo() (
  local tmpdir=""
  local save_mask

  : ${TMPDIR:=/tmp}
  save_mask=$(umask)
  umask 077
  tmpdir=$(mktemp -d "${TMPDIR}/XXXXXXXXXXXXXXXXXX")
  if [[ $? -ne 0 ]]; then
    umask "${save_mask}"
    red "Failed to create temporary directory"
    exit 1
  fi
  umask "${save_mask}"
  trap 'rm -rf "'"${tmpdir}"'"' EXIT

  cat > "$tmpdir/content.json" <<'JSON'
[
  {"type":"h1",      "text":"Executive Summary"},
  {"type":"body",    "text":"This document was generated by xiaoyi-pdf — a skill for creating visually polished PDFs. Every design decision is rooted in the document type and content, not a generic template."},
  {"type":"callout", "text":"Key insight: design tokens flow from palette.py through every renderer, keeping cover and body visually consistent."},

  {"type":"h1",      "text":"How It Works"},
  {"type":"h2",      "text":"The Token Pipeline"},
  {"type":"body",    "text":"The palette.py script infers a color palette and typography pair from the document type. These tokens are written to tokens.json and consumed by every downstream script."},
  {"type":"numbered","text":"palette.py generates color tokens, font selection, and the cover pattern"},
  {"type":"numbered","text":"cover.py renders the cover HTML using the selected pattern"},
  {"type":"numbered","text":"render_cover.py uses Playwright to convert the HTML cover to PDF"},
  {"type":"numbered","text":"render_body.py builds inner pages from content.json using ReportLab"},
  {"type":"numbered","text":"merge.py combines cover + body and runs final QA checks"},

  {"type":"h2",      "text":"Cover Patterns"},
  {"type":"table",
    "headers": ["Pattern",      "Document type",    "Visual character"],
    "rows": [
      ["fullbleed",   "report, general",   "Deep background · dot-grid texture"],
      ["split",       "proposal",          "Left dark panel · right dot-grid"],
      ["typographic", "resume, academic",  "Oversized display type · first-word accent"],
      ["atmospheric", "portfolio",         "Dark bg · radial glow · dot-grid"],
      ["magazine",    "magazine",          "Cream bg · centered · hero image"],
      ["darkroom",    "darkroom",          "Navy bg · centered · grayscale image"],
      ["terminal",    "terminal",          "Near-black · grid lines · monospace"],
      ["poster",      "poster",            "White · thick sidebar · oversized title"]
    ]
  },

  {"type":"h1",      "text":"Data Visualisation"},
  {"type":"h2",      "text":"Performance Metrics (Chart)"},
  {"type":"body",    "text":"Charts are rendered natively using matplotlib with a color palette derived from the document accent. No external chart services or image files required."},
  {"type":"chart",
    "chart_type": "bar",
    "title":      "Quarterly Performance",
    "labels":     ["Q1", "Q2", "Q3", "Q4"],
    "datasets": [
      {"label": "Revenue",  "values": [120, 145, 132, 178]},
      {"label": "Expenses", "values": [95,  108, 99,  122]}
    ],
    "y_label": "USD (thousands)",
    "caption": "Quarterly revenue vs. expenses"
  },

  {"type":"h2",      "text":"Market Share (Pie Chart)"},
  {"type":"chart",
    "chart_type": "pie",
    "labels":     ["Product A", "Product B", "Product C", "Other"],
    "datasets":   [{"values": [42, 28, 18, 12]}],
    "caption":    "Annual market share by product line"
  },

  {"type":"pagebreak"},

  {"type":"h1",      "text":"Mathematics"},
  {"type":"body",    "text":"Display math is rendered via matplotlib mathtext — no LaTeX binary installation required. Inline references use standard [N] notation in body text."},
  {"type":"math",    "text":"E = mc^2",                              "label":"(1)"},
  {"type":"math",    "text":"\\int_0^\\infty e^{-x^2}\\,dx = \\frac{\\sqrt{\\pi}}{2}", "label":"(2)"},
  {"type":"math",    "text":"\\sum_{n=1}^{\\infty} \\frac{1}{n^2} = \\frac{\\pi^2}{6}", "caption":"Basel problem (Euler, 1734)"},

  {"type":"h1",      "text":"Process Flow"},
  {"type":"body",    "text":"Flowcharts are drawn directly using matplotlib patches — no Graphviz or external tools needed. Supported node shapes: rect, diamond, oval, parallelogram."},
  {"type":"flowchart",
    "nodes": [
      {"id":"start",  "label":"Start",             "shape":"oval"},
      {"id":"input",  "label":"Receive Input",      "shape":"parallelogram"},
      {"id":"valid",  "label":"Valid?",             "shape":"diamond"},
      {"id":"proc",   "label":"Process Data",       "shape":"rect"},
      {"id":"err",    "label":"Return Error",        "shape":"rect"},
      {"id":"out",    "label":"Return Result",       "shape":"parallelogram"},
      {"id":"end",    "label":"End",                "shape":"oval"}
    ],
    "edges": [
      {"from":"start", "to":"input"},
      {"from":"input", "to":"valid"},
      {"from":"valid", "to":"proc",  "label":"Yes"},
      {"from":"valid", "to":"err",   "label":"No"},
      {"from":"proc",  "to":"out"},
      {"from":"err",   "to":"end"},
      {"from":"out",   "to":"end"}
    ],
    "caption": "Data validation and processing flow"
  },

  {"type":"h1",      "text":"Code Example"},
  {"type":"code",    "language":"python",
    "text":"# Design token pipeline\ntokens = palette.build_tokens(\n    title=\"Annual Report\",\n    doc_type=\"report\",\n    author=\"J. Smith\",\n    date=\"March 2026\",\n)\nhtml = cover.render(tokens)\npdf  = render_cover(html)"},

  {"type":"h1",      "text":"Design Principles"},
  {"type":"body",    "text":"The aesthetic system is documented in design/design.md. The core rule: every design decision must be rooted in the document content and purpose. A color chosen because it fits the content will always outperform a color chosen because it seems safe."},
  {"type":"h2",      "text":"Restraint over decoration"},
  {"type":"body",    "text":"The page is done when there is nothing left to remove. Accent color appears on section rules only — not on headings, not on bullets. No card components, no drop shadows."},
  {"type":"callout", "text":"A PDF passes the quality bar when a designer would not be embarrassed to hand it to a client."},

  {"type":"pagebreak"},
  {"type":"bibliography",
    "title": "References",
    "items": [
      {"id":"1","text":"Bringhurst, R. (2004). The Elements of Typographic Style (3rd ed.). Hartley & Marks."},
      {"id":"2","text":"Cairo, A. (2016). The Truthful Art: Data, Charts, and Maps for Communication. New Riders."},
      {"id":"3","text":"Hochuli, J. & Kinross, R. (1996). Designing Books: Practice and Theory. Hyphen Press."}
    ]
  }
]
JSON

  validate_content_json "$tmpdir/content.json"

  cmd_run \
    --title   "xiaoyi-pdf demo" \
    --type    "report" \
    --author  "xiaoyi-pdf skill" \
    --date    "$(date '+%B %Y')" \
    --subtitle "A demonstration of the token-based design pipeline" \
    --content "$tmpdir/content.json" \
    --out     "demo.pdf"

  # Cleanup handled by trap EXIT
)

# ── watermark ──────────────────────────────────────────────────────────────────
cmd_watermark() {
  run_py "$SCRIPTS/watermark_cli.py" "$@"
}

# ── merge ──────────────────────────────────────────────────────────────────────
cmd_merge() {
  run_py "$SCRIPTS/pdf_merge.py" "$@"
}

# ── split ──────────────────────────────────────────────────────────────────────
cmd_split() {
  run_py "$SCRIPTS/pdf_split.py" "$@"
}

# ── encrypt ────────────────────────────────────────────────────────────────────
cmd_encrypt() {
  run_py "$SCRIPTS/pdf_encrypt.py" "$@"
}

# ── decrypt ────────────────────────────────────────────────────────────────────
cmd_decrypt() {
  run_py "$SCRIPTS/pdf_decrypt.py" "$@"
}

# ── extract-text ───────────────────────────────────────────────────────────────
cmd_extract_text() {
  run_py "$SCRIPTS/pdf_extract_text.py" "$@"
}

# ── extract-tables ─────────────────────────────────────────────────────────────
cmd_extract_tables() {
  run_py "$SCRIPTS/pdf_extract_tables.py" "$@"
}

# ── dispatch ───────────────────────────────────────────────────────────────────
main() {
  if [[ $# -lt 1 ]]; then
    bold "xiaoyi-pdf — make.sh"
    echo ""
    echo "Usage: bash make.sh <command> [options]"
    echo ""
    echo "Commands:"
    echo "  init                              Create an isolated PDF job"
    echo "  session --session-id ID           Restore one explicit PDF job"
    echo "  check                             Verify all dependencies"
    echo "  run    --title T --type TYPE      CREATE: full pipeline → PDF"
    echo "         [--author A] [--date D] [--subtitle S]"
    echo "         [--abstract A] [--cover-image URL]"
    echo "         [--accent #HEX] [--cover-bg #HEX]"
    echo "         [--session-id ID | --content content.json] [--out output.pdf]"
    echo "  fill   --input f.pdf              FILL: inspect or fill form fields"
    echo "  reformat --input doc.md           REFORMAT: parse doc → apply design → PDF"
    echo "  demo                              Build a full-featured demo PDF"
    echo "  watermark --input f.pdf --type text   WATERMARK: add text/image/pdf watermark"
    echo "  merge --inputs a.pdf b.pdf --out merged.pdf      Merge multiple PDFs"
    echo "  split --input doc.pdf --outdir dir/ [--ranges]   Split PDF into pages"
    echo "  encrypt --input doc.pdf --out e.pdf --password   Encrypt PDF with password"
    echo "  decrypt --input e.pdf --out d.pdf --password     Decrypt PDF with password"
    echo "  extract-text --input doc.pdf --out text.txt      Extract text to .txt"
    echo "  extract-tables --input doc.pdf --out tables.xlsx Extract tables to Excel/CSV"
    exit 0
  fi

  case "$1" in
    check)          cmd_check ;;
    init)           cmd_init ;;
    session)        shift; cmd_session        "$@" ;;
    run)            shift; cmd_run            "$@" ;;
    fill)           shift; cmd_fill           "$@" ;;
    reformat)       shift; cmd_reformat       "$@" ;;
    demo)           cmd_demo  ;;
    watermark)      shift; cmd_watermark      "$@" ;;
    merge)          shift; cmd_merge          "$@" ;;
    split)          shift; cmd_split          "$@" ;;
    encrypt)        shift; cmd_encrypt        "$@" ;;
    decrypt)        shift; cmd_decrypt        "$@" ;;
    extract-text)   shift; cmd_extract_text   "$@" ;;
    extract-tables) shift; cmd_extract_tables "$@" ;;
    *)              echo "Unknown command: $1"; exit 1 ;;
  esac
}

main "$@"
