#!/usr/bin/env python3
"""
crawl_catalog.py — reactbits-advisor catalog crawler (real implementation).

Pulls the canonical component list from the react-bits GitHub repo's
src/constants/Categories.js, then for each component:
  1. derives slug + PascalName + install alias + live demo URL
  2. fetches the TS-TW source from ts-tailwind/<Category>/<Pascal>/<Pascal>.tsx
  3. parses imports to detect engine (motion / gsap / three / ogl) and heavy flag
  4. asserts OSS guarantees (URL + alias whitelist)
  5. emits one row to visual-index.md (or quarantines on failure)

Hand-curated fields (tone, one-line visual, analogy) are NOT touched here —
they live in references/visual-index-handcurated.json and are merged by
the table writer. Crawler only owns the structural / verifiable columns.

Usage:
  python3 crawl_catalog.py [--dry-run] [--category text-animations]

Hard guarantees:
  - Only reactbits.dev domain in URLs
  - Only @react-bits/ install aliases (never @react-bits-pro/)
  - Existing visual-index.md is backed up before overwrite
  - Any record that fails an assertion goes to .crawl-quarantine.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
REFS_DIR = SKILL_DIR / "references"
INDEX_FILE = REFS_DIR / "visual-index.md"
HANDCURATED_FILE = REFS_DIR / "visual-index-handcurated.json"
QUARANTINE_FILE = REFS_DIR / ".crawl-quarantine.json"

GH_RAW = "https://raw.githubusercontent.com/DavidHDev/react-bits/main"
SITE_BASE = "https://reactbits.dev"

# Source-of-truth files in the upstream repo
CATEGORIES_JS_URL = f"{GH_RAW}/src/constants/Categories.js"
TS_TW_TREE = "src/ts-tailwind"

CATEGORY_NORMALIZE = {
    # display name → URL slug (matches reactbits.dev routes)
    "Text Animations": "text-animations",
    "Animations": "animations",
    "Components": "components",
    "Backgrounds": "backgrounds",
}

# Map URL slug → PascalCase folder name in src/ts-tailwind/
CATEGORY_DIR = {
    "text-animations": "TextAnimations",
    "animations": "Animations",
    "components": "Components",
    "backgrounds": "Backgrounds",
}

# Engine detection rules — order matters (most specific first)
ENGINE_RULES = [
    # (regex, engine, heavy?)
    (r"^@react-three/fiber|^three(['/]|$)", "three", True),
    (r"^ogl(['/]|$)", "ogl", True),
    (r"^@gsap/react|^gsap(['/]|$)", "gsap", False),  # not heavy by bundle, but engine-coexistence concern
    (r"^motion(['/]|$)|^framer-motion(['/]|$)", "motion", False),
]


def fetch(url: str, retries: int = 2, backoff: float = 1.5) -> str:
    """Fetch a URL with simple retry. Returns text body."""
    last_exc = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "reactbits-advisor-crawler/0.1"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.read().decode("utf-8")
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            last_exc = e
            if attempt < retries:
                time.sleep(backoff ** attempt)
    raise RuntimeError(f"fetch failed after {retries + 1} tries: {url} :: {last_exc}")


def parse_categories(js_text: str) -> dict[str, list[str]]:
    """Parse Categories.js → {category_display_name: [component_display_name, ...]}.
    The file is JS but easy to regex since it's a flat array literal."""
    out: dict[str, list[str]] = {}
    # find each top-level category block: name: '...', subcategories: [ ... ]
    blocks = re.finditer(
        r"name:\s*['\"]([^'\"]+)['\"]\s*,\s*subcategories:\s*\[([^\]]+)\]",
        js_text,
    )
    for m in blocks:
        cat = m.group(1)
        if cat not in CATEGORY_NORMALIZE:
            continue  # skip "Get Started" etc
        items = re.findall(r"['\"]([^'\"]+)['\"]", m.group(2))
        out[cat] = items
    return out


def display_to_slug(name: str) -> str:
    """'Blur Text' → 'blur-text'."""
    return re.sub(r"\s+", "-", name.strip().lower())


def display_to_pascal(name: str) -> str:
    """'Blur Text' → 'BlurText'. 'ASCII Text' → 'ASCIIText'."""
    return re.sub(r"\s+", "", name.strip())


def assert_oss(url: str, install_alias: str, name: str) -> tuple[bool, str]:
    """Returns (ok, reason). reason is empty on ok."""
    if not url.startswith(SITE_BASE + "/"):
        return False, f"non-OSS domain: {url}"
    if "pro.reactbits.dev" in url:
        return False, f"pro subdomain leak: {url}"
    if re.search(r"/(pro|premium|locked)/", url):
        return False, f"pro path segment: {url}"
    if not install_alias.startswith("@react-bits/"):
        return False, f"non-OSS alias: {install_alias}"
    if install_alias.startswith("@react-bits-pro/"):
        return False, f"pro alias leak: {install_alias}"
    return True, ""


def detect_engine(source: str) -> tuple[str, bool, list[str]]:
    """Parse imports to detect engine + heavy flag + raw deps list.
    Returns (engine, heavy, raw_imports).
    engine ∈ {motion, gsap, three, ogl, none}.
    heavy = True if any heavy dep present."""
    imports = re.findall(r"^\s*import[^'\"]*from\s*['\"]([^'\"]+)['\"]", source, re.MULTILINE)
    detected_engines: list[str] = []
    heavy = False
    for imp in imports:
        for pattern, engine, is_heavy in ENGINE_RULES:
            if re.match(pattern, imp):
                if engine not in detected_engines:
                    detected_engines.append(engine)
                if is_heavy:
                    heavy = True
                break
    if not detected_engines:
        return "none", heavy, imports
    # primary engine is first detected (rules ordered)
    return detected_engines[0], heavy, imports


def fetch_component_source(category_slug: str, pascal: str) -> str | None:
    """Try ts-tailwind first; some components may live only under ts-default."""
    cat_dir = CATEGORY_DIR[category_slug]
    candidates = [
        f"{GH_RAW}/{TS_TW_TREE}/{cat_dir}/{pascal}/{pascal}.tsx",
        f"{GH_RAW}/src/ts-default/{cat_dir}/{pascal}/{pascal}.tsx",
    ]
    for url in candidates:
        try:
            return fetch(url)
        except RuntimeError:
            continue
    return None


def load_handcurated() -> dict[str, dict[str, str]]:
    if HANDCURATED_FILE.exists():
        return json.loads(HANDCURATED_FILE.read_text())
    return {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="don't write output files")
    ap.add_argument("--category", help="restrict to one category (URL slug)")
    ap.add_argument("--limit", type=int, help="cap components per category (debug)")
    ap.add_argument("--no-source", action="store_true", help="skip fetching component source (faster smoke test)")
    args = ap.parse_args()

    print("==> Fetching Categories.js …", file=sys.stderr)
    cats_js = fetch(CATEGORIES_JS_URL)
    cats = parse_categories(cats_js)
    print(f"    parsed {sum(len(v) for v in cats.values())} components across {len(cats)} categories", file=sys.stderr)

    handcurated = load_handcurated()
    records: list[dict] = []
    quarantined: list[dict] = []

    for cat_display, items in cats.items():
        cat_slug = CATEGORY_NORMALIZE[cat_display]
        if args.category and args.category != cat_slug:
            continue
        if args.limit:
            items = items[: args.limit]
        print(f"\n--- {cat_display} ({len(items)}) ---", file=sys.stderr)
        for name in items:
            slug = display_to_slug(name)
            pascal = display_to_pascal(name)
            install_alias = f"@react-bits/{pascal}-TS-TW"
            live_demo = f"{SITE_BASE}/{cat_slug}/{slug}"

            ok, reason = assert_oss(live_demo, install_alias, name)
            if not ok:
                quarantined.append({"name": name, "reason": reason, "live_demo": live_demo, "alias": install_alias})
                print(f"  ✗ QUARANTINE {name}: {reason}", file=sys.stderr)
                continue

            engine = "?"
            heavy = False
            raw_imports: list[str] = []
            if not args.no_source:
                src = fetch_component_source(cat_slug, pascal)
                if src is None:
                    quarantined.append({"name": name, "reason": "source not found in ts-tailwind or ts-default", "pascal": pascal, "category": cat_slug})
                    print(f"  ✗ QUARANTINE {name}: source not found", file=sys.stderr)
                    continue
                engine, heavy, raw_imports = detect_engine(src)

            hc = handcurated.get(slug, {})
            records.append({
                "category": cat_slug,
                "category_display": cat_display,
                "name": name,
                "slug": slug,
                "pascal": pascal,
                "install_alias": install_alias,
                "live_demo": live_demo,
                "engine": engine,
                "heavy": heavy,
                "license": "OSS (MIT + Commons Clause)",
                "tone": hc.get("tone", "TODO"),
                "visual": hc.get("visual", "TODO"),
                "analogy": hc.get("analogy", "TODO"),
                "raw_imports_sample": raw_imports[:5],
            })
            engine_marker = engine + ("⚠" if heavy else "")
            print(f"  ✓ {name:24} → {pascal:24} [{engine_marker}]", file=sys.stderr)

    print(f"\n==> {len(records)} records, {len(quarantined)} quarantined", file=sys.stderr)

    if args.dry_run:
        print("(dry-run, not writing files)", file=sys.stderr)
        return 0

    # write quarantine
    QUARANTINE_FILE.write_text(json.dumps({
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "count": len(quarantined),
        "items": quarantined,
    }, indent=2))

    # backup existing index
    if INDEX_FILE.exists():
        bak = REFS_DIR / f"visual-index.md.bak.{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        bak.write_bytes(INDEX_FILE.read_bytes())
        print(f"    backup: {bak.name}", file=sys.stderr)

    # write index.md
    write_index_md(records, quarantined)
    print(f"==> Wrote {INDEX_FILE} ({INDEX_FILE.stat().st_size} bytes)", file=sys.stderr)
    return 0


def write_index_md(records: list[dict], quarantined: list[dict]) -> None:
    lines: list[str] = []
    lines.append("# React Bits — Visual Index")
    lines.append("")
    lines.append(f"> **STATUS: AUTO-GENERATED** by `scripts/crawl_catalog.py` on `{datetime.utcnow().isoformat()}Z`.")
    lines.append("> ")
    lines.append("> Hand-edits to component rows will be **overwritten** on next crawl.")
    lines.append("> To customize tone/visual/analogy, edit `references/visual-index-handcurated.json` instead — those fields are merged in.")
    lines.append("")
    lines.append("## Schema")
    lines.append("")
    lines.append("- **Slug**: kebab-case, matches reactbits.dev URL")
    lines.append("- **Pascal**: install alias suffix (e.g. `BlurText` → `@react-bits/BlurText-TS-TW`)")
    lines.append("- **Engine**: primary animation engine (motion / gsap / three / ogl / none)")
    lines.append("- **Heavy**: ⚠ if uses `three` / `ogl` / `@react-three/fiber` (require user confirmation per LOCKED #5)")
    lines.append("- **Tone / Visual / Analogy**: hand-curated AI-value-add fields (default `TODO`)")
    lines.append("- **License**: always OSS (MIT + Commons Clause) — Pro components are filtered out by `assert_oss`")
    lines.append("")
    lines.append(f"**Total**: {len(records)} components · **Quarantined**: {len(quarantined)}")
    lines.append("")

    # group by category, in canonical order
    cat_order = ["text-animations", "animations", "components", "backgrounds"]
    by_cat: dict[str, list[dict]] = {c: [] for c in cat_order}
    for r in records:
        by_cat.setdefault(r["category"], []).append(r)

    for cat_slug in cat_order:
        items = by_cat.get(cat_slug, [])
        if not items:
            continue
        # heading
        display = next((k for k, v in CATEGORY_NORMALIZE.items() if v == cat_slug), cat_slug)
        lines.append(f"## {display} ({len(items)})")
        lines.append("")
        lines.append("| Name | Slug | Engine | Heavy | Install | Tone | Visual | Analogy |")
        lines.append("|------|------|--------|-------|---------|------|--------|---------|")
        for r in items:
            heavy_mark = "⚠" if r["heavy"] else ""
            install_short = f"`{r['install_alias']}`"
            demo_link = f"[{r['slug']}]({r['live_demo']})"
            lines.append(
                f"| {r['name']} | {demo_link} | {r['engine']} | {heavy_mark} | {install_short} | {r['tone']} | {r['visual']} | {r['analogy']} |"
            )
        lines.append("")

    if quarantined:
        lines.append("## Quarantined")
        lines.append("")
        lines.append("Records that failed OSS assertions or had missing source. See `.crawl-quarantine.json` for full payload.")
        lines.append("")
        for q in quarantined:
            lines.append(f"- **{q.get('name', '?')}**: {q.get('reason', '?')}")
        lines.append("")

    lines.append("## Crawler refresh")
    lines.append("")
    lines.append("```bash")
    lines.append("# from skill root")
    lines.append("python3 scripts/crawl_catalog.py            # full refresh")
    lines.append("python3 scripts/crawl_catalog.py --category text-animations")
    lines.append("python3 scripts/crawl_catalog.py --dry-run  # preview without writing")
    lines.append("```")
    lines.append("")
    lines.append("Hand-curated tone/visual/analogy fields live in `references/visual-index-handcurated.json` and survive across crawls.")
    lines.append("")

    INDEX_FILE.write_text("\n".join(lines))


if __name__ == "__main__":
    sys.exit(main())
