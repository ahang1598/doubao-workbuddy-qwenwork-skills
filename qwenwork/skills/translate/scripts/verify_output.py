#!/usr/bin/env python3
"""Deterministic post-write output verification for the translate skill.

Catches the cheap-but-common failure modes that pure prompt rules miss:
target-language diacritics absent, source-language characters leaked into
the translation, placeholders / SRT timecodes lost or duplicated, dates
dropped during restructuring, and user-specified "preserve as-is" tokens
dropped.

Pure regex — does NOT do semantic checks (term consistency, date drops,
register, accuracy). Those belong to the LLM review step.

Zero third-party deps. Python 3.8+.

Usage:
    python3 verify_output.py --to it --target path/to/translation.md
    python3 verify_output.py --to en --from zh --source src.md --target out.md \\
        --preserve "Boss,iPhone,IPG,Raycus"

    # stdin pipe:
    cat out.md | python3 verify_output.py --to it --target -

Output: JSON to stdout. Exit code 0 if no P0 findings, 1 otherwise.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Optional


# --------------------------------------------------------------------------- #
# Language profiles
# --------------------------------------------------------------------------- #

# Target language → (label, diacritic regex, minimum-output-len gate in chars)
# Output shorter than the gate is exempt from the diacritic check (1–2 sentence
# replies can legitimately lack accent marks).
DIACRITIC_PROFILES = {
    "it":    ("Italian",    re.compile(r"[àèéìòùÀÈÉÌÒÙ]"),                       80),
    "fr":    ("French",     re.compile(r"[àâçéèêëîïôûùüÿœæÀÂÇÉÈÊËÎÏÔÛÙÜŸŒÆ]"),  80),
    "de":    ("German",     re.compile(r"[äöüßÄÖÜ]"),                            60),
    "es":    ("Spanish",    re.compile(r"[áéíóúñ¿¡ÁÉÍÓÚÑ]"),                     80),
    "pt":    ("Portuguese", re.compile(r"[ãõçáéíóúâêôÃÕÇÁÉÍÓÚÂÊÔ]"),             80),
    "pt-BR": ("Portuguese", re.compile(r"[ãõçáéíóúâêôÃÕÇÁÉÍÓÚÂÊÔ]"),             80),
}

# Target language → set of source-language scripts that would indicate leakage.
# Only checked when target lang is in this map.
# Each entry is a list of (regex, label) tuples; any match counts as leakage.
SCRIPT_RANGES = {
    "cjk":       (re.compile(r"[一-鿿]"),                "CJK Han"),
    "kana":      (re.compile(r"[぀-ヿ]"),                "Japanese kana"),
    "hangul":    (re.compile(r"[가-힯]"),                "Korean Hangul"),
    "cyrillic":  (re.compile(r"[Ѐ-ӿ]"),                "Cyrillic"),
    "arabic":    (re.compile(r"[؀-ۿ]"),                "Arabic"),
    "thai":      (re.compile(r"[฀-๿]"),                "Thai"),
}

# Target lang → list of script-keys that should NOT appear in output.
# Default behavior: target lang's own script is allowed; everything CJK-family
# is flagged when target is a Western lang, and vice versa.
LEAKAGE_RULES = {
    "en":    ["cjk", "kana", "hangul", "cyrillic", "arabic", "thai"],
    "it":    ["cjk", "kana", "hangul", "cyrillic", "arabic", "thai"],
    "fr":    ["cjk", "kana", "hangul", "cyrillic", "arabic", "thai"],
    "de":    ["cjk", "kana", "hangul", "cyrillic", "arabic", "thai"],
    "es":    ["cjk", "kana", "hangul", "cyrillic", "arabic", "thai"],
    "pt":    ["cjk", "kana", "hangul", "cyrillic", "arabic", "thai"],
    "pt-BR": ["cjk", "kana", "hangul", "cyrillic", "arabic", "thai"],
    "ru":    ["cjk", "kana", "hangul", "arabic", "thai"],
    "ar":    ["cjk", "kana", "hangul", "cyrillic", "thai"],
    "ja":    ["hangul", "cyrillic", "arabic", "thai"],   # CJK Han is fine in JP
    "ko":    ["kana", "cyrillic", "arabic", "thai"],
    "zh":    ["kana", "hangul", "cyrillic", "arabic", "thai"],
    "zh-CN": ["kana", "hangul", "cyrillic", "arabic", "thai"],
    "zh-TW": ["kana", "hangul", "cyrillic", "arabic", "thai"],
}

# Source-language leakage tolerance: <= this % of total chars is treated as
# "incidental" (brand names, terms in original script, etc.) and downgraded
# to P1. > tolerance → P0.
LEAKAGE_TOLERANCE_PCT = 1.0


# --------------------------------------------------------------------------- #
# Placeholder patterns
# --------------------------------------------------------------------------- #

PLACEHOLDER_PATTERNS = [
    # (label, regex)
    ("printf/iOS %@ %d %s",     re.compile(r"%(?:\d+\$)?[@dsifluxXc]|%\d+\$[ds]")),
    ("ICU {0} {name}",          re.compile(r"\{[A-Za-z_][A-Za-z0-9_]*\}|\{\d+\}")),
    ("template {{var}}",        re.compile(r"\{\{[^{}]+\}\}")),
    ("dollar ${var}",           re.compile(r"\$\{[^{}]+\}")),
    ("escape \\n \\t \\r",      re.compile(r"\\[ntr]")),
    ("HTML <br/> &nbsp;",       re.compile(r"<br\s*/?>|&nbsp;")),
    ("xml-numbered <1>...</1>", re.compile(r"<\d+>[^<]*</\d+>")),
]

SRT_TIMECODE = re.compile(
    r"\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}"
)

# Full-date patterns. Each yields (year, month, day) after parsing.
# We intentionally do NOT try to disambiguate DD/MM vs MM/DD — the check only
# verifies that the year and the day-of-month *number* both reappear in the
# target somewhere, so the ambiguity cancels out.
DATE_PATTERNS = [
    # 24/04/2026, 24-04-2026, 24.04.2026  (D-M-Y or M-D-Y, can't tell)
    (re.compile(r"\b(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})\b"), "DMY-or-MDY"),
    # 2026-04-24, 2026/04/24  (Y-M-D, unambiguous because year is leftmost 4-digit)
    (re.compile(r"\b(\d{4})[/.\-](\d{1,2})[/.\-](\d{1,2})\b"), "YMD"),
    # 2026年4月24日 / 2026 年 4 月 24 日
    (re.compile(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日"), "ZH"),
]


# --------------------------------------------------------------------------- #
# Data structures
# --------------------------------------------------------------------------- #

@dataclass
class Finding:
    severity: str          # "P0" | "P1"
    check: str             # short check id
    msg: str               # human-readable description
    evidence: str = ""     # short excerpt or count


@dataclass
class Report:
    target_lang: str
    source_lang: Optional[str]
    target_char_count: int
    findings: List[Finding] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(f.severity == "P0" for f in self.findings)

    def to_json(self) -> str:
        return json.dumps(
            {
                "pass": self.passed,
                "target_lang": self.target_lang,
                "source_lang": self.source_lang,
                "target_char_count": self.target_char_count,
                "findings": [asdict(f) for f in self.findings],
            },
            ensure_ascii=False,
            indent=2,
        )


# --------------------------------------------------------------------------- #
# Checks
# --------------------------------------------------------------------------- #

def check_diacritics(target_text: str, target_lang: str) -> Optional[Finding]:
    profile = DIACRITIC_PROFILES.get(target_lang)
    if not profile:
        return None
    label, pattern, min_len = profile
    if len(target_text) < min_len:
        return None  # short reply, exempt
    hits = pattern.findall(target_text)
    if not hits:
        return Finding(
            severity="P0",
            check="target_diacritics_absent",
            msg=(
                f"Output is {len(target_text)} chars of {label} but contains "
                f"zero diacritic characters ({pattern.pattern}). Likely a "
                f"non-native rewrite. Introduce at least one — see SKILL.md "
                f"高频带重音意语词 / French / German list."
            ),
            evidence=f"len={len(target_text)} matches=0",
        )
    return None


def check_source_leakage(
    target_text: str, target_lang: str, source_lang: Optional[str]
) -> List[Finding]:
    findings: List[Finding] = []
    forbidden_scripts = LEAKAGE_RULES.get(target_lang)
    if not forbidden_scripts:
        return findings
    total = max(len(target_text), 1)
    for script_key in forbidden_scripts:
        pattern, label = SCRIPT_RANGES[script_key]
        hits = pattern.findall(target_text)
        if not hits:
            continue
        pct = len(hits) * 100.0 / total
        # If user told us source lang and it matches this script, that's the
        # primary leakage to flag. Otherwise still flag but as P1.
        is_source = source_lang is not None and source_lang.startswith(
            {"cjk": "zh", "kana": "ja", "hangul": "ko",
             "cyrillic": "ru", "arabic": "ar", "thai": "th"}[script_key]
        )
        severity = "P0" if (is_source or pct > LEAKAGE_TOLERANCE_PCT) else "P1"
        # Show first few offending characters for context
        sample = "".join(hits[:8])
        findings.append(Finding(
            severity=severity,
            check="source_lang_leakage",
            msg=(
                f"{label} characters appear in {target_lang} output "
                f"({len(hits)} / {total} = {pct:.1f}%). Either an unfinished "
                f"translation or the source itself leaked in. Brand names / "
                f"code identifiers should stay; prose should not."
            ),
            evidence=f"first: {sample!r}",
        ))
    return findings


def check_placeholders(
    source_text: Optional[str], target_text: str
) -> List[Finding]:
    if source_text is None:
        return []
    findings: List[Finding] = []
    for label, pattern in PLACEHOLDER_PATTERNS:
        src_hits = pattern.findall(source_text)
        tgt_hits = pattern.findall(target_text)
        if len(src_hits) == len(tgt_hits):
            continue
        # mismatch
        findings.append(Finding(
            severity="P0",
            check="placeholder_count_mismatch",
            msg=(
                f"Placeholder '{label}' count differs: "
                f"source has {len(src_hits)}, target has {len(tgt_hits)}. "
                f"Every placeholder must survive translation verbatim and "
                f"in the same count."
            ),
            evidence=(
                f"src={src_hits[:6]} tgt={tgt_hits[:6]}"
                if (src_hits or tgt_hits) else ""
            ),
        ))
    return findings


def check_srt_timecodes(
    source_text: Optional[str], target_text: str
) -> Optional[Finding]:
    if source_text is None:
        return None
    src_codes = SRT_TIMECODE.findall(source_text)
    if not src_codes:
        return None  # not an SRT
    tgt_codes = SRT_TIMECODE.findall(target_text)
    src_set = set(src_codes)
    tgt_set = set(tgt_codes)
    missing = src_set - tgt_set
    extra = tgt_set - src_set
    if not missing and not extra and len(src_codes) == len(tgt_codes):
        return None
    parts = []
    if missing:
        parts.append(f"missing: {sorted(missing)[:4]}")
    if extra:
        parts.append(f"extra: {sorted(extra)[:4]}")
    if len(src_codes) != len(tgt_codes):
        parts.append(f"count {len(src_codes)} → {len(tgt_codes)}")
    return Finding(
        severity="P0",
        check="srt_timecode_drift",
        msg=(
            "SRT timecodes must survive byte-for-byte (including comma in "
            "milliseconds). Any drift breaks subtitle sync."
        ),
        evidence="; ".join(parts),
    )


def _extract_dates(text: str):
    """Yield (year_str, day_str, label, original_match_str) tuples.

    Day-of-month is normalized to its leading-digit form for downstream
    literal matching (the "24" in "24/04/2026" — not "04" which is the
    ambiguous middle component)."""
    seen = set()
    for pattern, label in DATE_PATTERNS:
        for m in pattern.finditer(text):
            groups = m.groups()
            if label == "YMD" or label == "ZH":
                year, _, day = groups
            else:  # DMY-or-MDY ambiguous; the first 1-2 digit group is "day" by convention
                day, _, year = groups
            # Filter out implausible years to reduce noise (license numbers etc.)
            try:
                y = int(year)
            except ValueError:
                continue
            if y < 1900 or y > 2100:
                continue
            day = str(int(day))  # strip leading zeros: "04" → "4"
            key = (year, day)
            if key in seen:
                continue
            seen.add(key)
            yield year, day, label, m.group(0)


def check_dates_preserved(
    source_text: Optional[str], target_text: str
) -> List[Finding]:
    if source_text is None:
        return []
    findings: List[Finding] = []
    for year, day, _, original in _extract_dates(source_text):
        # Fast path: the source date string appears verbatim in target.
        if original in target_text:
            continue
        # Year must appear literally somewhere in target.
        if year not in target_text:
            findings.append(Finding(
                severity="P0",
                check="source_date_dropped",
                msg=(
                    f"Source date {original!r} (year={year}, day={day}) — year "
                    f"{year} is missing from the translation. Dates are facts; "
                    f"a reformat must still surface every date somewhere "
                    f"(header line, paragraph, table caption)."
                ),
                evidence=f"missing year={year}",
            ))
            continue
        # Day-of-month must appear as a standalone number. Accept both the
        # zero-stripped form ("24" → "24", "3" → "3") and the zero-padded
        # form ("3" → "03") so we don't false-positive when the target keeps
        # the source's leading-zero day format.
        day_int = int(day)
        day_padded = f"{day_int:02d}"
        forms = {day, day_padded}
        # (?<!\d)NN(?!\d) — match NN only when not surrounded by other digits,
        # so "24" doesn't accidentally hit "240" or "324".
        matched = any(
            re.search(rf"(?<!\d){re.escape(f)}(?!\d)", target_text)
            for f in forms
        )
        if not matched:
            findings.append(Finding(
                severity="P0",
                check="source_date_dropped",
                msg=(
                    f"Source date {original!r} (year={year}, day={day}) — year "
                    f"{year} is preserved but day-of-month {day} does not appear "
                    f"as a standalone number anywhere in the output. The date "
                    f"was likely dropped when restructuring."
                ),
                evidence=f"year-{year}-found day-{day}-missing",
            ))
    return findings


def check_preserve_list(
    preserve: List[str], target_text: str
) -> List[Finding]:
    findings: List[Finding] = []
    for token in preserve:
        token = token.strip()
        if not token:
            continue
        if token not in target_text:
            findings.append(Finding(
                severity="P0",
                check="preserve_token_missing",
                msg=(
                    f"User instructed to preserve {token!r} verbatim but the "
                    f"token does not appear in the output. Restore literal "
                    f"form — do not transliterate."
                ),
                evidence=f"needle={token!r}",
            ))
    return findings


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #

def read_input(spec: Optional[str]) -> Optional[str]:
    if spec is None:
        return None
    if spec == "-":
        return sys.stdin.read()
    return Path(spec).read_text(encoding="utf-8")


def verify(
    target_text: str,
    target_lang: str,
    source_text: Optional[str] = None,
    source_lang: Optional[str] = None,
    preserve: Optional[List[str]] = None,
) -> Report:
    report = Report(
        target_lang=target_lang,
        source_lang=source_lang,
        target_char_count=len(target_text),
    )
    if (f := check_diacritics(target_text, target_lang)) is not None:
        report.findings.append(f)
    report.findings.extend(
        check_source_leakage(target_text, target_lang, source_lang)
    )
    report.findings.extend(check_placeholders(source_text, target_text))
    if (f := check_srt_timecodes(source_text, target_text)) is not None:
        report.findings.append(f)
    report.findings.extend(check_dates_preserved(source_text, target_text))
    report.findings.extend(check_preserve_list(preserve or [], target_text))
    return report


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Deterministic post-write checks for translate output."
    )
    ap.add_argument("--to", dest="target_lang", required=True,
                    help="Target language code: en/it/fr/de/es/pt/ja/ko/zh/ru/ar")
    ap.add_argument("--from", dest="source_lang", default=None,
                    help="Source language code (optional, sharpens leakage check)")
    ap.add_argument("--target", default="-",
                    help="Path to translated text (default: stdin)")
    ap.add_argument("--source", default=None,
                    help="Path to source text (optional; needed for placeholder "
                         "and SRT timecode checks)")
    ap.add_argument("--preserve", default="",
                    help="Comma-separated list of tokens that must appear verbatim "
                         "in the target (mirrors user's 'preserve xxx' instructions)")
    args = ap.parse_args()

    target_text = read_input(args.target) or ""
    source_text = read_input(args.source)
    preserve = [t for t in args.preserve.split(",") if t.strip()]

    report = verify(
        target_text=target_text,
        target_lang=args.target_lang,
        source_text=source_text,
        source_lang=args.source_lang,
        preserve=preserve,
    )
    print(report.to_json())
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
