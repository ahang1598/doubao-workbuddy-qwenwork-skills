#!/usr/bin/env python3
"""Static preflight for publication-figure Python and R source files.

The validator is intentionally dependency-free. It checks portable source-level
requirements before the selected backend renders the figure; it does not claim
to validate statistics or replace visual inspection.

The rule structure incorporates and refactors ideas from the Apache-2.0
academic-figure-skill QA workflow without retaining its path-bound runners.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable, Iterable


LEVEL_ORDER = {"PASS": 0, "WARN": 1, "FAIL": 2}
PYTHON_SUFFIXES = {".py"}
R_SUFFIXES = {".r", ".rmd", ".qmd"}


@dataclass(frozen=True)
class Finding:
    check_id: str
    level: str
    message: str
    evidence: list[str]

    @property
    def passed(self) -> bool:
        return self.level == "PASS"


def finding(check_id: str, level: str, message: str, evidence: Iterable[str] = ()) -> Finding:
    if level not in LEVEL_ORDER:
        raise ValueError(f"unknown finding level: {level}")
    return Finding(check_id, level, message, list(evidence))


def detect_backend(path: Path, requested: str) -> str:
    if requested != "auto":
        return requested
    suffix = path.suffix.lower()
    if suffix in PYTHON_SUFFIXES:
        return "python"
    if suffix in R_SUFFIXES:
        return "r"
    raise ValueError(f"cannot infer backend from {path.name}; pass --backend python or --backend r")


def regex_hits(patterns: Iterable[str], source: str, flags: int = re.IGNORECASE) -> list[str]:
    hits: list[str] = []
    for pattern in patterns:
        match = re.search(pattern, source, flags)
        if match:
            hits.append(match.group(0).strip())
    return hits


def check_syntax(source: str, backend: str) -> Finding:
    if backend == "python":
        try:
            ast.parse(source)
        except SyntaxError as exc:
            location = f"line {exc.lineno}" if exc.lineno else "unknown line"
            return finding("SOURCE-SYNTAX", "FAIL", f"Python syntax error at {location}: {exc.msg}")
        return finding("SOURCE-SYNTAX", "PASS", "Python source parses successfully")

    pairs = {"(": ")", "[": "]", "{": "}"}
    stack: list[str] = []
    quote: str | None = None
    escaped = False
    for char in source:
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if quote:
            if char == quote:
                quote = None
            continue
        if char in {'"', "'"}:
            quote = char
        elif char in pairs:
            stack.append(char)
        elif char in pairs.values():
            if not stack or pairs[stack.pop()] != char:
                return finding("SOURCE-SYNTAX", "FAIL", "R source has unbalanced brackets")
    if stack or quote:
        return finding("SOURCE-SYNTAX", "FAIL", "R source has unbalanced brackets or quotes")
    return finding(
        "SOURCE-SYNTAX",
        "WARN",
        "Basic R delimiter check passed; run Rscript parse() when R is available",
    )


def check_font_family(source: str, backend: str) -> Finding:
    families = regex_hits(
        [r"Arial", r"Helvetica", r"Liberation Sans", r"sans-serif", r"base_family\s*=\s*['\"]sans['\"]"],
        source,
    )
    if families:
        return finding("FONT-FAMILY", "PASS", "A publication-safe sans-serif family is configured", families)
    label = "matplotlib rcParams" if backend == "python" else "ggplot/theme or graphics device"
    return finding("FONT-FAMILY", "FAIL", f"No explicit publication-safe font family found in {label}")


def explicit_font_sizes(source: str) -> list[float]:
    patterns = [
        r"(?:font\.size|fontsize|labelsize|titlesize|legend\.fontsize)\s*['\"]?\s*[:=]\s*(\d+(?:\.\d+)?)",
        r"base_size\s*=\s*(\d+(?:\.\d+)?)",
        r"element_text\s*\([^)]*?size\s*=\s*(\d+(?:\.\d+)?)",
    ]
    values: list[float] = []
    for pattern in patterns:
        values.extend(float(value) for value in re.findall(pattern, source, re.IGNORECASE | re.DOTALL))
    return values


def check_font_sizes(source: str, _backend: str) -> Finding:
    sizes = explicit_font_sizes(source)
    if not sizes:
        return finding("FONT-SIZE", "WARN", "No explicit text sizes found; verify readability at final physical size")
    minimum = min(sizes)
    if minimum < 5:
        return finding("FONT-SIZE", "FAIL", f"Explicit text size falls below the 5 pt floor: {minimum:g} pt")
    return finding("FONT-SIZE", "PASS", f"All detected text sizes are at least 5 pt (minimum {minimum:g} pt)")


def check_colormaps(source: str, _backend: str) -> Finding:
    hits = regex_hits(
        [
            r"(?:cmap|palette|colormap)\s*=\s*['\"](?:jet|rainbow|hsv)['\"]",
            r"plt\.cm\.(?:jet|rainbow|hsv)\b",
            r"scale_(?:color|fill)_(?:gradientn|distiller)\s*\([^)]*(?:rainbow|jet|hsv)",
            r"\brainbow\s*\(",
        ],
        source,
    )
    if hits:
        return finding("COLOR-MAP", "FAIL", "Rainbow/jet/hsv color mapping is not publication-safe", hits)
    return finding("COLOR-MAP", "PASS", "No rainbow/jet/hsv color mapping detected")


def check_editable_text(source: str, backend: str) -> Finding:
    if backend == "python":
        has_svg = bool(re.search(r"svg\.fonttype['\"]?\s*[:=]\s*['\"]none['\"]", source, re.IGNORECASE))
        has_pdf = bool(re.search(r"pdf\.fonttype['\"]?\s*[:=]\s*42\b", source, re.IGNORECASE))
        if has_svg and has_pdf:
            return finding("EDITABLE-TEXT", "PASS", "SVG and PDF editable-text settings are configured")
        missing = []
        if not has_svg:
            missing.append("svg.fonttype='none'")
        if not has_pdf:
            missing.append("pdf.fonttype=42")
        return finding("EDITABLE-TEXT", "FAIL", "Missing editable-text settings", missing)

    has_svg = bool(re.search(r"(?:svglite::)?svglite\s*\(", source))
    has_pdf = bool(re.search(r"(?:grDevices::)?cairo_pdf\s*\(", source))
    if has_svg and has_pdf:
        return finding("EDITABLE-TEXT", "PASS", "svglite and cairo_pdf editable-text devices are configured")
    missing = []
    if not has_svg:
        missing.append("svglite")
    if not has_pdf:
        missing.append("cairo_pdf")
    return finding("EDITABLE-TEXT", "FAIL", "Missing preferred editable-vector devices", missing)


def check_vector_exports(source: str, _backend: str) -> Finding:
    has_svg = bool(re.search(r"\.svg\b|svglite\s*\(", source, re.IGNORECASE))
    has_pdf = bool(re.search(r"\.pdf\b|cairo_pdf\s*\(|\bpdf\s*\(", source, re.IGNORECASE))
    if has_svg and has_pdf:
        return finding("EXPORT-VECTOR", "PASS", "Both SVG and PDF exports are present")
    missing = [name for name, present in (("SVG", has_svg), ("PDF", has_pdf)) if not present]
    return finding("EXPORT-VECTOR", "FAIL", f"Missing required vector export: {', '.join(missing)}")


def check_raster_exports(source: str, _backend: str) -> Finding:
    has_tiff = bool(re.search(r"\.tiff?\b|agg_tiff\s*\(|\btiff\s*\(", source, re.IGNORECASE))
    has_png = bool(re.search(r"\.png\b|agg_png\s*\(|\bpng\s*\(", source, re.IGNORECASE))
    if has_tiff:
        return finding("EXPORT-RASTER", "PASS", "TIFF raster export is present")
    if has_png:
        return finding("EXPORT-RASTER", "WARN", "PNG preview is present but no TIFF submission raster was found")
    return finding("EXPORT-RASTER", "FAIL", "No TIFF or PNG raster export found")


def check_resolution(source: str, _backend: str) -> Finding:
    values = [
        int(value)
        for value in re.findall(r"(?:dpi|res)\s*[:=]\s*(\d+)", source, re.IGNORECASE)
    ]
    if not values:
        return finding("RASTER-DPI", "WARN", "No explicit raster DPI/resolution found")
    below_minimum = sorted({value for value in values if value < 300})
    if below_minimum:
        return finding("RASTER-DPI", "FAIL", "Raster resolution below 300 dpi", [str(v) for v in below_minimum])
    if max(values) < 600:
        return finding("RASTER-DPI", "WARN", "Raster export meets the 300 dpi floor but not the 600 dpi default", [str(max(values))])
    return finding("RASTER-DPI", "PASS", "A raster export of at least 600 dpi is configured", [str(max(values))])


def candidate_widths_mm(source: str, backend: str) -> list[float]:
    widths: list[float] = []
    for value in re.findall(r"(?:fig_)?width_mm\s*[:=]\s*(\d+(?:\.\d+)?)", source, re.IGNORECASE):
        widths.append(float(value))
    if backend == "python":
        for value in re.findall(r"figsize\s*=\s*\(\s*(\d+(?:\.\d+)?)", source, re.IGNORECASE):
            widths.append(float(value) * 25.4)
    else:
        mm_calls = re.findall(
            r"(?:ggsave|agg_tiff|svglite|cairo_pdf)\s*\([^)]*?width\s*=\s*(\d+(?:\.\d+)?)[^)]*?units\s*=\s*['\"]mm['\"]",
            source,
            re.IGNORECASE | re.DOTALL,
        )
        widths.extend(float(value) for value in mm_calls)
    return widths


def check_dimensions(source: str, backend: str) -> Finding:
    widths = candidate_widths_mm(source, backend)
    if not widths:
        return finding("FINAL-WIDTH", "WARN", "No static final width detected; verify the target journal's current specification")
    width = widths[0]
    if abs(width - 89) <= 4 or abs(width - 183) <= 6:
        return finding("FINAL-WIDTH", "PASS", f"Detected width {width:.1f} mm matches a common journal column width")
    return finding(
        "FINAL-WIDTH",
        "WARN",
        f"Detected width {width:.1f} mm is not near the common 89/183 mm defaults; verify the target journal",
    )


def check_sampling(source: str, _backend: str) -> Finding:
    hits = regex_hits(
        [
            r"np\.random\.choice\s*\(",
            r"\.sample\s*\(",
            r"\bsample_n\s*\(",
            r"\bsample_frac\s*\(",
            r"\bslice_sample\s*\(",
        ],
        source,
    )
    if not hits:
        return finding("DATA-SAMPLING", "PASS", "No high-confidence row-sampling operation detected")
    documented = bool(re.search(r"sampling_(?:reason|rationale)|sampling\s+rationale|sample_size|random_state|set\.seed", source, re.IGNORECASE))
    if documented:
        return finding("DATA-SAMPLING", "WARN", "Sampling is present; confirm it is user-requested or scientifically justified and report its effect", hits)
    return finding("DATA-SAMPLING", "WARN", "Potential silent sampling detected; do not reduce data for rendering convenience", hits)


def check_exclusions(source: str, _backend: str) -> Finding:
    hits = regex_hits(
        [r"\.dropna\s*\(", r"\bna\.omit\s*\(", r"\bcomplete\.cases\s*\(", r"drop_na\s*\("],
        source,
    )
    if not hits:
        return finding("DATA-EXCLUSION", "PASS", "No high-confidence missing-data exclusion detected")
    reported = bool(re.search(r"n_before|n_after|before_count|after_count|excluded_count|dropped_count", source, re.IGNORECASE))
    if reported:
        return finding("DATA-EXCLUSION", "PASS", "Missing-data exclusion includes count-tracking markers", hits)
    return finding("DATA-EXCLUSION", "WARN", "Missing-data exclusion found without explicit before/after count tracking", hits)


def check_demo_data(source: str, _backend: str) -> Finding:
    hits = regex_hits(
        [
            r"np\.random\.(?:normal|uniform|rand|randn|poisson)\s*\(",
            r"(?:np\.random\.)?default_rng\s*\(",
            r"\brng\.(?:normal|uniform|poisson|choice)\s*\(",
            r"\b(?:rnorm|runif|rpois)\s*\(",
            r"make_(?:classification|regression|blobs)\s*\(",
        ],
        source,
    )
    if not hits:
        return finding("DEMO-DATA", "PASS", "No obvious simulated-data generator detected")
    isolated = bool(re.search(r"--demo|demo_mode|if\s*\([^)]*demo|if\s+.*demo", source, re.IGNORECASE))
    if isolated:
        return finding("DEMO-DATA", "WARN", "Simulated data is present behind an apparent demo path; keep it out of production runs", hits)
    return finding("DEMO-DATA", "WARN", "Simulated data appears in the plotting source without an explicit demo boundary", hits)


def check_log_guards(source: str, _backend: str) -> Finding:
    log_hits = regex_hits(
        [r"\bnp\.log(?:2|10)?\s*\(", r"\blog(?:2|10)?\s*\(", r"set_[xy]scale\s*\(\s*['\"]log", r"scale_[xy]_log10\s*\("],
        source,
    )
    if not log_hits:
        return finding("LOG-GUARD", "PASS", "No logarithmic transform or axis detected")
    guards = regex_hits(
        [
            r"clip\s*\([^)]*lower\s*=",
            r"pmax\s*\(",
            r"not\s+0\s*<[^\n]{0,80}",
            r"np\.any\s*\([^)]*<=\s*0",
            r"(?:padj|pval|p_value|pvalue)[^\n]{0,50}<=\s*0",
            r"non.?positive",
            r"strictly\s+positive|pseudocount|epsilon|eps\b",
        ],
        source,
    )
    if guards:
        return finding("LOG-GUARD", "PASS", "A logarithmic transform/axis and a positivity or pseudocount guard were both detected", guards)
    return finding("LOG-GUARD", "WARN", "Logarithmic operation found without an obvious positivity/pseudocount guard", log_hits)


def check_backend_exclusivity(source: str, backend: str) -> Finding:
    if backend == "python":
        hits = regex_hits([r"\bRscript\b", r"\brpy2\b", r"ggplot2|ComplexHeatmap|patchwork"], source)
    else:
        hits = regex_hits([r"matplotlib|seaborn|plotly|reticulate::py_run"], source)
    if hits:
        return finding("BACKEND-EXCLUSIVE", "WARN", f"Possible cross-backend plotting reference found in {backend} source", hits)
    return finding("BACKEND-EXCLUSIVE", "PASS", f"No obvious cross-backend plotting reference found for {backend}")


CHECKS: tuple[Callable[[str, str], Finding], ...] = (
    check_syntax,
    check_font_family,
    check_font_sizes,
    check_colormaps,
    check_editable_text,
    check_vector_exports,
    check_raster_exports,
    check_resolution,
    check_dimensions,
    check_sampling,
    check_exclusions,
    check_demo_data,
    check_log_guards,
    check_backend_exclusivity,
)


def validate_source(source: str, backend: str) -> list[Finding]:
    return [check(source, backend) for check in CHECKS]


def summarize(findings: Iterable[Finding], strict: bool = False) -> dict[str, object]:
    rows = list(findings)
    counts = {level: sum(row.level == level for row in rows) for level in ("PASS", "WARN", "FAIL")}
    ready = counts["FAIL"] == 0 and (not strict or counts["WARN"] == 0)
    return {"ready": ready, "strict": strict, "counts": counts}


def render_text(path: Path, backend: str, findings: list[Finding], strict: bool) -> str:
    summary = summarize(findings, strict)
    lines = [
        "Nature Figure Static Preflight",
        f"source: {path}",
        f"backend: {backend}",
        "",
    ]
    for row in findings:
        lines.append(f"[{row.level}] {row.check_id}: {row.message}")
        for item in row.evidence:
            lines.append(f"  - {item}")
    counts = summary["counts"]
    lines.extend(
        [
            "",
            f"summary: {counts['PASS']} pass, {counts['WARN']} warn, {counts['FAIL']} fail",
            f"verdict: {'READY FOR VISUAL QA' if summary['ready'] else 'FIX BEFORE DELIVERY'}",
            "note: static preflight does not validate statistics, source-data truth, or rendered appearance",
        ]
    )
    return "\n".join(lines)


def run_self_tests() -> None:
    good_python = '''
import matplotlib as mpl
import matplotlib.pyplot as plt
mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica"],
    "font.size": 7,
    "svg.fonttype": "none",
    "pdf.fonttype": 42,
})
width_mm = 183
values = values[values > 0]
fig, ax = plt.subplots(figsize=(width_mm / 25.4, 120 / 25.4))
ax.set_yscale("log")
fig.savefig("figure.svg", bbox_inches="tight")
fig.savefig("figure.pdf", bbox_inches="tight")
fig.savefig("figure.tiff", dpi=600, bbox_inches="tight")
'''
    good_r = '''
library(ggplot2)
width_mm <- 183
p <- ggplot(df, aes(x, y)) + theme_classic(base_size = 7, base_family = "Arial")
svglite::svglite("figure.svg", width = width_mm / 25.4, height = 4)
print(p)
dev.off()
grDevices::cairo_pdf("figure.pdf", width = width_mm / 25.4, height = 4, family = "Arial")
print(p)
dev.off()
ragg::agg_tiff("figure.tiff", width = width_mm / 25.4, height = 4, units = "in", res = 600)
print(p)
dev.off()
'''
    bad_python = '''
import numpy as np
import matplotlib.pyplot as plt
x = np.random.normal(size=100)
x = np.random.choice(x, 12)
fig, ax = plt.subplots(figsize=(4, 3))
ax.scatter(x, np.log(x), c=x, cmap="jet")
ax.tick_params(labelsize=4)
fig.savefig("figure.png", dpi=72)
'''

    good_py_findings = validate_source(good_python, "python")
    good_py_failures = [row for row in good_py_findings if row.level == "FAIL"]
    assert not good_py_failures, good_py_failures

    good_r_findings = validate_source(good_r, "r")
    good_r_failures = [row for row in good_r_findings if row.level == "FAIL"]
    assert not good_r_failures, good_r_failures

    bad = {row.check_id: row for row in validate_source(bad_python, "python")}
    for check_id in ("FONT-FAMILY", "FONT-SIZE", "COLOR-MAP", "EDITABLE-TEXT", "EXPORT-VECTOR", "RASTER-DPI"):
        assert bad[check_id].level == "FAIL", (check_id, bad[check_id])
    for check_id in ("DATA-SAMPLING", "DEMO-DATA", "LOG-GUARD"):
        assert bad[check_id].level == "WARN", (check_id, bad[check_id])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", nargs="?", type=Path, help="Python or R plotting source")
    parser.add_argument("--backend", choices=("auto", "python", "r"), default="auto")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument("--strict", action="store_true", help="treat warnings as not ready")
    parser.add_argument("--self-test", action="store_true", help="run dependency-free validator tests")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.self_test:
        run_self_tests()
        print("validate_figure.py self-test: PASS")
        return 0
    if args.source is None:
        build_parser().error("source is required unless --self-test is used")
    if not args.source.is_file():
        print(f"error: source file not found: {args.source}", file=sys.stderr)
        return 2
    try:
        backend = detect_backend(args.source, args.backend)
        source = args.source.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    findings = validate_source(source, backend)
    summary = summarize(findings, args.strict)
    if args.json:
        payload = {
            "source": str(args.source),
            "backend": backend,
            "summary": summary,
            "findings": [asdict(row) for row in findings],
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(render_text(args.source, backend, findings, args.strict))
    return 0 if summary["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
