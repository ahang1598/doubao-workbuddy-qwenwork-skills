# -*- coding: utf-8 -*-
"""Augment authors_meta.json with affiliation / email / corresponding-author
data extracted from the PDF first page (full-text fallback).

Why this exists: in this sandbox the arXiv e-print LaTeX source (.tgz) is
unreachable (direct TLS reset; proxy.cors.sh rejects /e-print/) and the
arXiv HTML render strips author affiliations.  The PDF is reliably
downloadable via the CORS proxy and carries exactly what the report needs:
institution lines (shared / unnumbered / numbered), contact e-mails, and
corresponding-author markers (dagger, "*", "Corresponding author(s): ...").
enrich_authors.py is still run first (as required); this script only *fills
gaps* it could not cover.

Usage:  python3 augment_authors.py <id1> <id2> ...
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import unicodedata

# authors_meta.json is read/written in the current working directory by default;
# override with --meta <path>.
META = os.path.join(os.getcwd(), "authors_meta.json")
UA = "Mozilla/5.0 (compatible; arxiv-digest/1.0)"
CORS = "https://proxy.cors.sh/"
PDFCACHE = os.path.join(tempfile.gettempdir(), "arxiv_pdf_cache")
os.makedirs(PDFCACHE, exist_ok=True)

AFF_HINT = re.compile(
    r"(Universit|Universidad|Universität|Institut|Laborator|Academy|College|School|"
    r"Department|Dept\.|Center|Centre|Research|\bInc\b|\bLtd\b|\bCorp\b|\bLab\b|"
    r"Technolog|Polytech|Politecnico|\bCNRS\b|\bINRIA\b|\bETH\b|\bEPFL\b|\bKAIST\b|"
    r"Fraunhofer|"
    r"Hessian|Google|Meta\b|Microsoft|NVIDIA|Amazon|Tencent|Alibaba|Huawei|Baidu|"
    r"ByteDance|Apple\b|Adobe|Samsung|Sony|Bosch|Toyota|Honda|Hyundai|\bCASIA\b|"
    r"Ant Group|BigAI|POSTECH|\bAI\b|MIT|Berkeley|Stanford|Oxford|Cambridge)", re.I)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
MARK = "†‡*∗⋆§¶#◇•✉✦☨"
# A new numbered affiliation starts with a 1-2 digit marker followed by an
# uppercase letter ("1 KAIST", "1KAIST,", "2Sony Group Corporation").
# Capping at 2 digits stops continuation lines like "63000 Clermont-Ferrand..."
# from being mistaken for a new numbered entry.
NEW_ENTRY_RE = re.compile(r"^(\d{1,2})\s*(?=[A-Z])")
# Strong single-token institutions (accepted even though only one word)
STRONG1 = re.compile(r"^(?:KAIST|POSTECH|ETH|EPFL|MIT|CMU|INRIA|CNRS|MPI|JHU|NYU|UCLA|"
                     r"NTU|NUS|HKU|THU|SYSU|Ant\s+Group|BIGAI|Sony|Samsung|Huawei|"
                     r"Tencent|Alibaba|Baidu|ByteDance|NVIDIA|Google|Microsoft|Adobe|"
                     r"Amazon|Bosch|Toyota|Meta)$", re.I)
# A line that is nothing but e-mail address(es) (possibly in {..} groups)
EMAIL_ONLY = re.compile(
    r"^[\{\<\(]?\s*[A-Za-z0-9._%+\-\s,@;]*@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}[\}\>\)]?[\s,;.]*$")
NOTE_RE = re.compile(r"[\u2020\u2021†‡∗⋆§¶#◇•]+\s*(Equal\s+contribut|Equal\s+advis|Corresponding|correspond|co-?author)", re.I)
VENUE_NOISE = re.compile(
    r"(proceedings|human language technolog|conference|workshop|https?|vol\.|"
    r"art\. no|fig\.|rather than|equal contribution|correspond|doi:|"
    r"arxiv:|we propose|in this paper|the authors|license|is a structural|"
    r"supported by|this work was|funding|grant|acknowledg|received |index terms|"
    r"keywords?:|abstract)", re.I)


def _curl(url, out, timeout=120):
    env = {**os.environ, "http_proxy": "", "https_proxy": "",
           "HTTP_PROXY": "", "HTTPS_PROXY": "", "ALL_PROXY": "", "all_proxy": ""}
    r = subprocess.run(
        ["curl", "-s", "-L", "--max-time", str(timeout), "-A", UA,
         "-o", out, "-w", "%{http_code}", CORS + url],
        capture_output=True, text=True, timeout=timeout + 30, env=env)
    return r.stdout.strip()


def _pdf_text(pid, page=0):
    """page=0 -> first page only; page=-1 -> all pages."""
    p = os.path.join(PDFCACHE, f"{pid}.pdf")
    if not (os.path.exists(p) and os.path.getsize(p) > 20000):
        if _curl(f"https://arxiv.org/pdf/{pid}", p) != "200" or os.path.getsize(p) < 20000:
            return ""
    try:
        from pypdf import PdfReader
        rd = PdfReader(p)
        if page == 0:
            txt = rd.pages[0].extract_text() or ""
        else:
            txt = "\n".join((pg.extract_text() or "") for pg in rd.pages)
    except Exception:
        txt = ""
    # Fallback to PyMuPDF when pypdf fails (e.g. "EOF marker not found") or
    # yields nothing — pypdf can silently return empty on some arXiv PDFs.
    if not txt:
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(p)
            if page == 0:
                txt = doc[0].get_text() or ""
            else:
                txt = "\n".join(pg.get_text() or "" for pg in doc)
        except Exception:
            txt = ""
    return txt


def pdf_page1(pid):
    return _pdf_text(pid, 0)


def pdf_full_text(pid):
    return _pdf_text(pid, -1)


# --------------------------------------------------------------------------
# author-name cleaning (drop leaked affiliation / note entries)
# --------------------------------------------------------------------------
GEO = re.compile(r"\b(Hong Kong|Singapore|China|USA|America|Korea|Japan|France|Germany|"
                 r"Canada|Australia|SAR|UK|England|Switzerland|Italy|Spain|India|Taiwan)\b", re.I)
BAD_AUTHOR = re.compile(r"(affiliation|correspond|contribut|equal|advising|university|"
                        r"institut|laborator|college|school|company|corp|ltd|inc\b|research|"
                        r"department|academy|centre|center|group|email|http|footnotemark)", re.I)


def clean_authors(authors):
    out = []
    for a in authors:
        nm = a.get("name", "").strip()
        if not nm:
            continue
        nm = re.sub(r"footnotemark:\s*$", "", nm).strip()
        if BAD_AUTHOR.search(nm):
            continue
        toks = nm.split()
        if GEO.search(nm) and len(toks) <= 4:
            continue
        if len(toks) == 1 and re.fullmatch(r"[A-Z0-9]{2,}", toks[0]):
            continue
        if len(toks) > 5:
            continue
        a = dict(a)
        a["name"] = nm
        out.append(a)
    return out


# --------------------------------------------------------------------------
# institution string cleaning / validation
# --------------------------------------------------------------------------
def clean_inst(v):
    v = unicodedata.normalize("NFC", v)
    v = v.replace("´", "")                                   # spacing acute (Universit´e)
    v = re.sub(r"[\u0300-\u036f]", "", v)                    # combining accents
    v = re.sub(r"\{[^}]*\}", " ", v)                         # {jihun1998,...} email groups
    v = re.sub(r"\S*@\S*", " ", v)                           # emails
    v = re.sub(r"[\u2020\u2021†‡∗⋆§¶#◇•]+\s*(Equal\s+contribut|Equal\s+advis|"
               r"Corresponding|correspond|co-?author).*$", " ", v, flags=re.I)
    v = re.sub(r"[\u2020\u2021†‡∗⋆§¶#◇•]", " ", v)            # stray markers
    v = re.sub(r"[.;,]?\s*(Correspondence|Corresponding author).*$", "", v, flags=re.I)
    v = re.sub(r"\b([A-Z])\s+(?=[a-z])", r"\1", v)          # fix "Y eungnam"
    v = re.sub(r"(?<=\w)\s+([eé])(?=\s)", r"\1", v)         # "Universit e" -> "Universite"
    v = re.sub(r"\s+", " ", v).strip(" .,;")
    v = re.sub(r"^[\d\s]+", "", v)                           # leading digit/space
    v = re.sub(r"[\s,;.]+\d+$", "", v)                       # trailing orphan digit
    return v


def norm_accents(s):
    """Fold detached spacing accents: "Aufr `ere" -> "Aufrere"."""
    return re.sub(r"\s*[`´]\s*", "", unicodedata.normalize("NFC", s))


def pat_for(tok):
    """Regex for a token, tolerant of accented variants (Aufrère -> Aufr[èe]re)."""
    out = []
    for ch in tok:
        if ord(ch) < 128:
            out.append(re.escape(ch))
            continue
        d = unicodedata.normalize("NFD", ch)
        out.append("[" + re.escape(ch + d[0]) + "]" if len(d) > 1 else re.escape(ch))
    return "".join(out)


def sur_re_for(surnames):
    return re.compile(
        r"(?<!\w)(" + "|".join(pat_for(s) for s in sorted(set(surnames), key=len, reverse=True))
        + r")(?=[\d\s,.*" + re.escape(MARK) + r"]|$)")


def is_good_aff(v):
    if not v or "@" in v:
        return False
    if VENUE_NOISE.search(v):
        return False
    if not AFF_HINT.search(v):
        return False
    w = len(v.split())
    if w < 1 or w > 20:
        return False
    if w == 1 and not STRONG1.search(v):
        return False
    return True


# --------------------------------------------------------------------------
# numbered-affiliation block parser (handles glued / mid-line / multi-line)
# --------------------------------------------------------------------------
def split_numbered_line(s):
    """Split "1Aaa, 2Bbb, 3Ccc" into ["1Aaa,", "2Bbb,", "3Ccc"].

    Only 1-2 digit markers followed by an uppercase letter count, so
    continuation lines such as "63000 Clermont-Ferrand, France" are untouched.
    """
    segs, pos = [], 0
    for m in re.finditer(r"(?<![\d\w])(\d{1,2})\s*(?=[A-Z])", s):
        if m.start() > pos:
            segs.append(s[pos:m.start()])
        pos = m.start()
    segs.append(s[pos:])
    return [x.strip() for x in segs if x.strip()]


BLOCK_STOP = re.compile(
    r"^(abstract|correspond|index terms|keywords|received |we propose|in this|"
    r"this paper|license|doi|figure|fig\.|table|introduction|equal contribut|"
    r"references|acknowledg)", re.I)


def parse_numbered(text):
    """Accumulate numbered affiliation entries line by line.

    Robust against: glued markers ("1KAIST"), e-mail lines sitting between two
    numbered entries, blank lines inside the block, and continuation lines that
    begin with a multi-digit number ("63000 Clermont-Ferrand, France").
    """
    if not text:
        return {}
    lines = [re.sub(r"\s+", " ", l).strip() for l in text.split("\n")]
    n = len(lines)

    start = None
    for i in range(n):
        l = lines[i]
        if NEW_ENTRY_RE.match(l) and (
                AFF_HINT.search(l) or (i + 1 < n and AFF_HINT.search(lines[i + 1]))):
            start = i
            break
    if start is None:
        return {}

    raw, cur, i = {}, None, start
    while i < n and i < start + 60:
        s = lines[i]
        if BLOCK_STOP.match(s):
            break
        if not s:
            # a blank line ends the block unless another numbered entry follows
            j = i + 1
            while j < n and not lines[j]:
                j += 1
            if j < n and NEW_ENTRY_RE.match(lines[j]):
                i = j
                continue
            break
        if EMAIL_ONLY.match(s) or (EMAIL_RE.search(s) and not AFF_HINT.search(s)):
            i += 1
            continue
        segs = split_numbered_line(s)     # also splits mid-line ".. Korea 2Graduate School"
        for s2 in segs:
            m = NEW_ENTRY_RE.match(s2)
            if m:
                cur = m.group(1)
                raw[cur] = [s2[m.end():].strip()]
            elif cur is not None:
                prev = raw[cur][-1] if raw[cur] else ""
                if prev.endswith("-"):                # hyphenated line break
                    raw[cur][-1] = prev + s2
                else:
                    raw[cur].append(s2)
        i += 1
        if len(raw) >= 12:
            break

    entries = {}
    for d, parts in raw.items():
        val = clean_inst(" ".join(parts))
        if is_good_aff(val):
            entries[d] = val[:180]
    return entries


# --------------------------------------------------------------------------
# shared (single unnumbered) affiliation
# --------------------------------------------------------------------------
def parse_shared(text, authors):
    lines = [l.rstrip() for l in text.split("\n")]
    surnames = [a["name"].split()[-1] for a in authors if a["name"].split()]
    if not surnames:
        return {}
    sur_re = sur_re_for(surnames)
    last_al, abs_i = -1, -1
    for k, l in enumerate(lines[:45]):
        low = l.lower().lstrip()
        if abs_i < 0 and low.startswith("abstract"):
            abs_i = k
        if sur_re.search(l):
            last_al = k
    if last_al < 0:
        return {}
    hi = abs_i if abs_i > 0 else last_al + 12
    for l in lines[last_al + 1: hi]:
        v = clean_inst(l)
        if is_good_aff(v) and not re.match(r"^\d+\b", v):
            return {"1": v[:160]}
    return {}


# --------------------------------------------------------------------------
# per-author blocks:  Name\nInstitution\n(email)
# --------------------------------------------------------------------------
def parse_per_author(text, authors):
    lines = [l.rstrip() for l in text.split("\n")]
    surnames = [a["name"].split()[-1] for a in authors if a["name"].split()]
    if not surnames:
        return {}, {}
    sur_re = sur_re_for(surnames)
    # locate author region (title .. abstract)
    abs_i = next((k for k, l in enumerate(lines[:45]) if l.lower().lstrip().startswith("abstract")), 45)
    region = lines[1: abs_i]

    # candidate indices where a surname appears
    hits = [k for k, l in enumerate(region) if sur_re.search(l)]
    if len(hits) < 2:
        return {}, {}
    name_aff = {}
    insts = []
    for idx, k in enumerate(hits):
        # pick the author whose surname actually occurs on this line (longest match)
        nm, best = None, ""
        for a in authors:
            sur = a["name"].split()[-1]
            if re.search(r"(?<!\w)" + pat_for(sur)
                         + r"(?=[\s,.*" + re.escape(MARK) + r"]|$)", region[k]):
                if len(sur) > len(best):
                    nm, best = a["name"], sur
        if not nm:
            continue
        nxt = hits[idx + 1] if idx + 1 < len(hits) else abs_i
        aff_lines = []
        for l in region[k + 1: nxt]:
            v = clean_inst(l)
            if EMAIL_RE.search(l) or l.startswith("{") or not v:
                continue
            if is_good_aff(v):
                aff_lines.append(v)
            elif aff_lines:
                break
        if aff_lines:
            inst = " ".join(aff_lines)[:160]
            if inst not in insts:
                insts.append(inst)
            name_aff[nm] = [str(insts.index(inst) + 1)]
    affs = {str(i + 1): s for i, s in enumerate(insts)}
    return affs, name_aff


# --------------------------------------------------------------------------
# corresponding authors
# --------------------------------------------------------------------------
EQ_NOTE = re.compile(r"(equal(ly)?\s+contribut|共同(第一|一)作者)", re.I)
ADV_NOTE = re.compile(r"equal\s+advis", re.I)
EQ_MARK = "*∗✦"
CORR_MARK = "✉†‡\u2020\u2021§¶"


MARK_CH = "†‡*∗⋆§¶#◇•✉✦☨\u2020\u2021"


def markers_for(region, fullname):
    """Markers attached to an author, allowing digits/spaces in between
    ("Zaibin Zhang1∗" -> ['∗']).

    Prefers a full-name match so that same-surname authors are not confused
    (otherwise every "Zhang" would inherit the ∗ of another "Zhang").
    """
    tail = r"[\d\s,.]*([" + MARK_CH + r"]?)"
    m_full = list(re.finditer(pat_for(fullname) + tail, region))
    if m_full:
        return [m.group(1) for m in m_full if m.group(1)]
    return [m.group(1) for m in re.finditer(
        r"\b" + pat_for(fullname.split()[-1]) + tail, region) if m.group(1)]


def get_equal(text, authors):
    """Authors marked as equal contribution (∗ / * / ✦).

    Accepted when the paper states so explicitly, or — by near-universal
    convention — when two or more authors carry the asterisk.
    """
    lines = [l.rstrip() for l in text.split("\n")]
    abs_i = next((k for k, l in enumerate(lines[:45]) if l.lower().lstrip().startswith("abstract")), 45)
    region = norm_accents("\n".join(lines[:abs_i]))
    marked = {a["name"] for a in authors
              if any(mk in EQ_MARK for mk in markers_for(region, a["name"]))}
    if not marked:
        return set()
    if EQ_NOTE.search(text[:5000]) or len(marked) >= 2:
        return marked
    return set()


def get_corr(text, html_authors, authors):
    corr = set()
    for m in re.finditer(r"(?:correspond(?:ence|ing\s+authors?)|通讯作者)\s*[:：]?\s*([^\n@<]{2,200})", text, re.I):
        for nm in split_names(m.group(1)):
            if not BAD_AUTHOR.search(nm) and 1 <= len(nm.split()) <= 4:
                corr.add(nm)
    for m in re.finditer(r"correspond(?:ence|ing)\s+to\s*:?\s*([^\n@<]{2,120})", text, re.I):
        for nm in split_names(m.group(1)):
            if not BAD_AUTHOR.search(nm) and 1 <= len(nm.split()) <= 4:
                corr.add(nm)
    for a in html_authors:
        if a.get("corr"):
            corr.add(a["name"])
    # Markers attached to surnames, honouring the paper's own footnote legend:
    #   ✉ / † / ‡  -> corresponding, unless the legend redefines † as "equal advising"
    #   ∗ / * / ✦   -> equal contribution (NOT corresponding) when such a note exists
    has_eq = bool(EQ_NOTE.search(text[:5000]))
    has_adv = bool(ADV_NOTE.search(text[:5000]))
    lines = [l.rstrip() for l in text.split("\n")]
    abs_i = next((k for k, l in enumerate(lines[:45]) if l.lower().lstrip().startswith("abstract")), 45)
    region = norm_accents("\n".join(lines[:abs_i]))
    for a in authors:
        for mk in markers_for(region, a["name"]):
            if mk in EQ_MARK and has_eq:
                continue                      # equal contribution, not corresponding
            if mk in "†‡\u2020\u2021" and has_adv:
                continue                      # legend says "equal advising"
            if mk in CORR_MARK:
                corr.add(a["name"])
                break
    return corr


def split_names(block):
    out = []
    for t in re.split(r",|\band\b| and |&|;", block):
        t = t.strip(" .,\n")
        t = re.sub(r"[\d" + re.escape(MARK) + r"]+$", "", t).strip()
        if 1 <= len(t.split()) <= 4 and re.search(r"[A-Za-z]", t) and not AFF_HINT.search(t):
            out.append(t)
    return out


# --------------------------------------------------------------------------
# author -> affiliation digit mapping from the name region (numbered case)
# --------------------------------------------------------------------------
def map_numbered(text, authors, affs):
    if not affs:
        return {}
    lines = [l.rstrip() for l in text.split("\n")]
    abs_i = next((k for k, l in enumerate(lines[:45]) if l.lower().lstrip().startswith("abstract")), 45)
    region = norm_accents("\n".join(lines[:abs_i]))

    inst_by_dig = dict(affs)
    name_aff = {}
    for a in authors:
        nm = a["name"]
        sur = pat_for(nm.split()[-1])
        digs = re.findall(r"\b" + sur + r"[\s" + re.escape(MARK)
                          + r"*†‡]*(?:(\d+))", region)
        found = [d for d in digs if d in inst_by_dig]
        if found:
            name_aff[nm] = list(dict.fromkeys(found))        # dedupe, keep order
        else:
            # surname-only match (first digit after that surname)
            m = re.search(r"\b" + sur + r"[\s" + re.escape(MARK)
                          + r"*†‡]*(\d)", region)
            if m and m.group(1) in inst_by_dig:
                name_aff[nm] = [m.group(1)]
    return name_aff


def extract(pid, html_authors):
    txt = pdf_page1(pid)
    if not txt:
        return None
    authors = clean_authors(html_authors)
    if not authors:
        authors = [dict(a) for a in html_authors]
    ftxt = pdf_full_text(pid)
    emails = sorted(set(EMAIL_RE.findall(txt)))
    if not emails:                        # e-mails sometimes live further in
        ft = ftxt.split("References")[0] if "References" in ftxt else ftxt
        emails = sorted(set(EMAIL_RE.findall(ft)))[:8]

    # cascade: numbered -> per-author blocks -> single shared affiliation
    name_aff = {}
    affs = parse_numbered(txt) or parse_numbered(ftxt)
    if affs:
        name_aff = map_numbered(txt, authors, affs)
    if not affs:
        paffs, pname = parse_per_author(txt, authors)
        if not paffs:
            paffs, pname = parse_per_author(ftxt, authors)
        if paffs:
            affs, name_aff = paffs, pname
    if not affs:
        affs = parse_shared(txt, authors)
        if affs:
            name_aff = {a["name"]: ["1"] for a in authors}

    corr = get_corr(txt, html_authors, authors)
    equal = get_equal(txt, authors) - corr
    return dict(emails=emails, affs=affs, name_aff=name_aff,
                corr=corr, equal=equal, cleaned=authors)


def main():
    ap = argparse.ArgumentParser(description="Augment authors_meta.json from PDF first pages.")
    ap.add_argument("ids", nargs="*", help="arXiv IDs to augment (defaults to none)")
    ap.add_argument("--meta", default=META, help="path to authors_meta.json (default: ./authors_meta.json)")
    args = ap.parse_args()
    if not args.ids:
        print("no IDs given; nothing to do")
        return
    meta = json.load(open(args.meta, encoding="utf-8"))
    for pid in args.ids:
        rec = meta.get(pid)
        if not rec or not rec.get("authors"):
            print("SKIP", pid, "(no author records)")
            continue
        ex = extract(pid, rec["authors"])
        if not ex:
            print("XX  ", pid, "PDF empty")
            continue
        authors = ex["cleaned"]
        affs = ex.get("affs", {})

        # preserve first / equal flags from the HTML-derived record
        old = {a.get("name"): a for a in rec.get("authors", [])}
        for i, a in enumerate(authors):
            o = old.get(a["name"], {})
            a["first"] = bool(o.get("first")) or (i == 0)
            a["equal"] = bool(o.get("equal"))
            a["affs"] = []

        # assign affiliations
        only_one = len(affs) == 1
        for a in authors:
            aids = ex.get("name_aff", {}).get(a["name"])
            if aids and all(x in affs for x in aids):
                a["affs"] = sorted(int(x) for x in aids)
            elif not aids and only_one:
                a["affs"] = [int(next(iter(affs)))]
            elif not aids and affs:
                # no linkage: leave blank (renderer shows warning) — do not guess
                a["affs"] = []
        # corresponding / equal-contribution flags
        for a in authors:
            a["corr"] = a["name"] in ex.get("corr", set())
            a["equal"] = a["name"] in ex.get("equal", set())

        rec["authors"] = authors
        rec["affiliations"] = affs
        rec["emails"] = ex["emails"]
        rec["ok"] = True
        src = rec.get("source", "")
        if "pdfaug" not in src:
            rec["source"] = (src + "+pdfaug").strip("+")
        warns = []
        if not affs:
            warns.append("PDF 仍未解析到单位")
        if affs and not any(a.get("affs") for a in authors):
            warns.append("作者未关联到机构（仅机构列表可见）")
        rec["warn"] = "；".join(warns)
        meta[pid] = rec
        print(f"OK  {pid} n={len(authors)} affs={len(affs)} "
              f"emails={len(ex['emails'])} corr={[a['name'] for a in authors if a['corr']]} "
              f"linked={sum(1 for a in authors if a['affs'])}")

    json.dump(meta, open(args.meta, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("wrote", args.meta)


if __name__ == "__main__":
    main()
