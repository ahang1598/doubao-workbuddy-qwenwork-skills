# -*- coding: utf-8 -*-
r"""
enrich_authors.py  (v3)
-----------------------
Extract per-author affiliation / first-author / corresponding-author metadata
for a list of arXiv IDs.

WHY THIS EXISTS
  arXiv listing pages and the arXiv API do NOT carry affiliation or
  corresponding-author fields (<arxiv:affiliation> is virtually never
  populated). The only machine-readable source is the LaTeX-rendered paper
  HTML at https://arxiv.org/html/<id>v<n>, with a PDF first-page fallback and
  a LaTeX e-print tarball fallback (last resort, most complete).

AUTHOR-BLOCK DIALECTS HANDLED
  A. AAAI      : <sup>1,2</sup> + \equalcontrib / \corresponding LaTeX macros
  B. LLNCS/ECCV: "Ninstitutetext: X" footnotes, one ltx_creator per author,
                 MathML \ast / \dagger markers
  C. IEEE      : no superscripts; "A, B and C are with <inst> (e-mail:...)"
                 + "Corresponding author: NAME."
  D. IROS/ICRA : affiliations inside <span class="ltx_author_notes">
  E. CVPR      : "<sup>N</sup>Institution" lines inside ltx_personname
  F. Simple    : one shared affiliation line, no numbering
  G. Envelope  : U+1F4E7 / U+2709 / 🖂 glyph inside a superscript = corresponding
  H. LaTeX src : \institute{.. \and ..} / \affiliation[1]{..} / \inst{n}
                 / \email{..} / \correspondingauthor{..}

OUTPUT -> authors_meta.json
"""
import json
import re
import html as H
import os
import subprocess
import unicodedata
import tarfile  # noqa: F401  (used by fetch_eprint)

UA = "Mozilla/5.0 (compatible; arxiv-digest/1.0)"
CORS = "https://proxy.cors.sh/"   # pass-through for arxiv.org direct TLS reset
CACHE = "/tmp/arxiv_html_cache"
PDFCACHE = "/tmp/arxiv_pdf_cache"
TEXCACHE = "/tmp/arxiv_tex_cache"
os.makedirs(CACHE, exist_ok=True)
os.makedirs(PDFCACHE, exist_ok=True)
os.makedirs(TEXCACHE, exist_ok=True)

LATEX_GLYPH = {
    r"\dagger": "†", r"\ddagger": "‡", r"\ast": "∗", r"\star": "⋆",
    r"\S": "§", r"\P": "¶", r"\bullet": "•", r"\diamond": "◇", r"\sharp": "#",
}
MARK_CHARS = "†‡*∗⋆§¶#◇•"
ENVELOPE = "\U0001F4E7\u2709\U0001F582\U0001F583\u2712"  # mail glyphs = corresponding

# NOTE: every alternative must be anchored with \b on the LEFT where it could
# occur inside a personal name.  A bare `AI\b` silently swallowed authors named
# "Shuai"/"Zhai" (both end in ...ai) and dropped them from the list.
AFF_HINT = re.compile(
    r"(Universit|Universidad|Universität|Institut|Laborator|Academy|College|School|"
    r"Department|Dept\.|Center|Centre|Research|\bInc\b|\bLtd\b|\bCorp\b|\bLab\b|"
    r"Technolog|Polytech|Politecnico|\bCNRS\b|\bINRIA\b|\bETH\b|\bEPFL\b|\bKAIST\b|"
    r"Hessian|Google|Meta\b|Microsoft|NVIDIA|Amazon|Tencent|Alibaba|Huawei|Baidu|"
    r"ByteDance|Apple\b|Adobe|Samsung|Sony|Bosch|Toyota|\bCASIA\b|\bAI\b)", re.I)

# Phrases that are *notes* (corresponding-author note, project page, etc.),
# never real author names. They survive the name tokenizer because they start
# with a capital letter, so they must be filtered explicitly.
NOTE_RE = re.compile(
    r"(authors?|correspond|contribut|manuscript|pre-?print|project page|"
    r"supplementary|equal contrib|these authors|email|https?|github|"
    r"\bpage\b|\bwebsite\b|\bcode\b|\bsource\b|data availability|preprint link)",
    re.I)


def clean_aff(v, key=None):
    """Strip LaTeXML leftovers ('institutetext:', duplicated index) from a value."""
    v = " ".join(v.split())
    v = re.sub(r"^\s*\d*\s*institutetext\s*:\s*", "", v, flags=re.I)
    v = re.sub(r"^\{\{.*?\}\}\s*", "", v)
    if key:
        v = re.sub(r"^%s(?=[A-Z])" % re.escape(str(key)), "", v)
    return v.strip(" .,;")


NOISE = re.compile(r"(funding|grant|acknowledg|this (study|work|manuscript|research)|"
                   r"reflects only|European Union|project reference|copyright)", re.I)


# ------------------------------------------------------------------ fetching
def _curl(url, out, timeout=60):
    """Fetch url -> out, returning the HTTP code. arxiv.org direct TLS is reset
    in this sandbox, so fall back to the proxy.cors.sh pass-through when direct
    fails (the pass-through returns authentic arXiv HTML incl. ltx_authors)."""
    env = {**os.environ, "http_proxy": "", "https_proxy": "",
           "HTTP_PROXY": "", "HTTPS_PROXY": "", "ALL_PROXY": "", "all_proxy": ""}
    try:
        r = subprocess.run(
            ["curl", "-s", "-L", "--max-time", str(timeout), "-A", UA,
             "-o", out, "-w", "%{http_code}", url],
            capture_output=True, text=True, timeout=timeout + 15, env=env)
        code = r.stdout.strip()
        if code == "200" and os.path.getsize(out) > 1000:
            return code
        # direct failed/blocked -> retry through CORS pass-through
        r2 = subprocess.run(
            ["curl", "-s", "-L", "--max-time", str(timeout + 60), "-A", UA,
             "-o", out, "-w", "%{http_code}", CORS + url],
            capture_output=True, text=True, timeout=timeout + 90, env=env)
        return r2.stdout.strip()
    except Exception:
        return "000"


def fetch_html(pid):
    for v in ("v1", "v2", "v3"):
        p = os.path.join(CACHE, f"{pid}{v}.html")
        if os.path.exists(p) and os.path.getsize(p) > 5000:
            return open(p, encoding="utf-8", errors="ignore").read(), f"html:{v}"
    for v in ("v1", "v2", "v3"):
        p = os.path.join(CACHE, f"{pid}{v}.html")
        if _curl(f"https://arxiv.org/html/{pid}{v}", p) == "200" and os.path.getsize(p) > 5000:
            return open(p, encoding="utf-8", errors="ignore").read(), f"html:{v}"
        if os.path.exists(p):
            os.remove(p)
    return None, None


def fetch_pdf_page1(pid):
    p = os.path.join(PDFCACHE, f"{pid}.pdf")
    if not (os.path.exists(p) and os.path.getsize(p) > 20000):
        if _curl(f"https://arxiv.org/pdf/{pid}", p, 90) != "200":
            return ""
    try:
        from pypdf import PdfReader
        return PdfReader(p).pages[0].extract_text() or ""
    except Exception:
        return ""


# --------------------------------------------------- LaTeX e-print fallback
def _read_tex_from_tgz(tgz):
    """Extract and concatenate all .tex files from a tarball."""
    chunks = []
    with tarfile.open(tgz, "r:*") as tf:
        for m in tf.getmembers():
            if m.name.endswith(".tex") and m.isfile() and m.size < 2_000_000:
                f = tf.extractfile(m)
                if f:
                    chunks.append(f.read().decode("utf-8", "ignore"))
    return "\n".join(chunks)


def fetch_eprint(pid):
    """Download the arXiv e-print LaTeX source tarball and return joined .tex text.

    Retries on transient network failures and validates the gzip payload so a
    truncated/partial download is never mistaken for "no data"."""
    import gzip
    tgz = os.path.join(TEXCACHE, f"{pid}.tar.gz")
    if os.path.exists(tgz) and os.path.getsize(tgz) > 1000:
        try:
            with gzip.open(tgz) as g:
                g.read(1)
            return _read_tex_from_tgz(tgz)
        except Exception:
            try:
                os.remove(tgz)
            except Exception:
                pass
    for _ in range(3):
        if _curl(f"https://arxiv.org/e-print/{pid}", tgz, 120) == "200" \
                and os.path.getsize(tgz) > 1000:
            try:
                with gzip.open(tgz) as g:
                    g.read(1)
                return _read_tex_from_tgz(tgz)
            except Exception:
                try:
                    os.remove(tgz)
                except Exception:
                    pass
    return ""


def _balanced_brace(s, start):
    """start = index of the opening '{'. Return inner text between matching braces."""
    k = s.find("{", start)
    if k < 0:
        return ""
    depth, i = 1, k + 1
    while i < len(s):
        if s[i] == "{":
            depth += 1
        elif s[i] == "}":
            depth -= 1
            if depth == 0:
                return s[k + 1:i]
        i += 1
    return s[k + 1:]


def _grab_braced(tex, cmd):
    r"""Return inner-contents of every `\cmd{...}` (balanced braces)."""
    out = []
    for m in re.finditer(r"\\" + cmd + r"(?:\s*\[[^\]]*\])?\s*\{", tex):
        out.append(_balanced_brace(tex, m.start()))
    return out


def _tex_inst_to_aff(val, key, affs):
    r"""Map an \institute/\affiliation value into affs under key (LLNCS \and split)."""
    parts = re.split(r"\\and\s*", val)
    if len(parts) > 1:
        for i, p in enumerate(parts, 1):
            p = re.sub(r"\\(email|thanks|inst|thanksref)\b.*", "", p, flags=re.S)
            p = re.sub(r"[\\{}]", "", p)
            p = " ".join(p.split())
            if p and (AFF_HINT.search(p) or len(p.split()) >= 2):
                affs[str(i)] = p[:160]
        return
    v = re.sub(r"\\(email|thanks|inst|thanksref)\b.*", "", val, flags=re.S)
    v = re.sub(r"[\\{}]", "", v)
    v = " ".join(v.split())
    if v and (AFF_HINT.search(v) or len(v.split()) >= 2):
        affs[key] = v[:160]


def _superscript_to_token(s):
    """Convert LaTeX superscript markers to {{MARKER}} tokens.

    Handles \\textsuperscript{\\rm 1,}, $^{1}$, $^1$, $^{1,2}$,
    and symbolic markers ($^\\dagger$, $^\\ddagger$) mapped to ordinals so they
    align with affiliation keys."""
    def repl(m):
        txt = m.group(1).strip().lower()
        if txt in ("dagger",):
            return "{{1}}"
        if txt in ("ddagger",):
            return "{{2}}"
        if txt in ("ast", "star"):
            return "{{3}}"
        return "{{%s}}" % txt
    s = re.sub(r"\\textsuperscript\s*\{([^{}]*)\}", repl, s)
    s = re.sub(r"\$\^\{([^{}]*)\}\$", repl, s)
    s = re.sub(r"\$\^(\w)\$", lambda m: "{{%s}}" % m.group(1), s)
    return s


# Institution keywords used to recognise affiliation lines (broader than names).
AFF_RE_TEX = re.compile(
    r"universit|institut|laborator|college|academy|dept|school|research|"
    r"technolog|polytech|center|centre|nvidia|google|meta|microsoft|amazon|"
    r"tencent|alibaba|huawei|baidu|bytedance|apple|adobe|samsung|sony|bosch|"
    r"toyota|\binc\b|\bltd\b|\bcorp\b", re.I)

# Anonymised / placeholder author names to suppress (double-blind drafts).
PLACEHOLDER_NAMES = {
    "author name", "first author", "second author", "third author",
    "fourth author", "last author", "anonymous authors", "anonymous",
}


# --------------------------------------------------- modern conference styles
def _normalize_markers(s):
    """Convert every superscript dialect to @@N@@ / @@N,M@@ / @@#@@ / @@CORR@@
    sentinels (brace-free, so the later junk-strip will not destroy them)."""
    s = re.sub(r"\\textsuperscript\s*\{\\rm\s*(\d+)\}", r"@@\1@@", s)
    s = re.sub(r"\\textsuperscript\s*\{(\\?#|\#)\}", r"@@#@@", s)
    s = re.sub(r"\\textsuperscript\s*\{(\d+(?:,\d+)*)\}", r"@@\1@@", s)
    s = re.sub(r"\$\^\\?(?:dagger)\s*\$", "@@1@@", s)
    s = re.sub(r"\$\^\\?(?:ddagger)\s*\$", "@@2@@", s)
    s = re.sub(r"\$\^\\?(?:ast|star)\s*\$", "@@3@@", s)
    s = re.sub(r"\$\^(\w)\$", r"@@\1@@", s)
    s = re.sub(r"\\correspondingicon|\\Letter", "@@CORR@@", s)
    return s


def _strip_junk(s):
    """Remove LaTeX macros/structure, leaving only names, affiliation text and
    the @@N@@ marker sentinels."""
    s = re.sub(r"\\href\s*\{[^}]*\}\s*\{[^}]*\}", " ", s)
    s = re.sub(r"\\url\s*\{[^}]*\}", " ", s)
    s = re.sub(r"\\footnotemark\s*\[[^\]]*\]", " ", s)
    s = re.sub(r"\\setcounter\s*\{[^}]*\}\s*\{[^}]*\}", " ", s)
    s = re.sub(r"\\thanks\s*\{[^{}]*\}", " ", s)
    s = re.sub(r"\\textbf\s*\{", " ", s)
    s = re.sub(r"\\footnotesize|\\small|\\large|\\bfseries|\\itshape|\\ttfamily", " ", s)
    s = re.sub(r"\\(?:text|rm|it|sf|tt|bf|emph|textrm|textit|texttt|textsf)\b", " ", s)
    s = re.sub(r"\\hspace\s*\{[^}]*\}", " ", s)
    s = re.sub(r"\\quad|\\qquad", " ", s)
    s = re.sub(r"\\\\\s*(?:\[[^\]]*\])?", " ", s)
    s = re.sub(r"\\[a-zA-Z]+\s*\{[^}]*\}", " ", s)
    s = re.sub(r"\\[a-zA-Z]+", " ", s)
    s = s.replace("~", " ")
    s = s.replace("{", " ").replace("}", " ")
    s = re.sub(r"@@(\d+(?:,\d+)*|#|CORR)@@", r"{{\1}}", s)
    s = re.sub(r"\s+", " ", s)
    return s


_SINGLE_ORG = re.compile(
    r"^(NVIDIA|GigaAI|Google|Meta|Microsoft|Amazon|Apple|Adobe|Samsung|Sony|"
    r"Bosch|Toyota|Tencent|Alibaba|Huawei|Baidu|ByteDance|HKUST|NIO|CASIA|MIT|ETH|EPFL|KAIST)$")


def _looks_aff(inst):
    inst = inst.strip(" ,;.")
    if not inst:
        return False
    if AFF_HINT.search(inst):
        return True
    words = inst.split()
    if len(words) >= 2:
        return True
    if len(words) == 1 and _SINGLE_ORG.match(words[0]) and len(words[0]) >= 3:
        return True
    return False


def _looks_real_aff(inst):
    """Stricter than _looks_aff: an affiliation must carry an affiliation
    keyword (University/Institute/Corporation/...) or be a known single-org.
    This rejects spurious captures where a name marker is glued to the *next*
    name (e.g. ADEPT '{{2}} Jessica Yin') — those have no affiliation signal."""
    inst = inst.strip(" ,;.")
    if not inst:
        return False
    if AFF_HINT.search(inst):
        return True
    words = inst.split()
    if len(words) == 1 and _SINGLE_ORG.match(words[0]) and len(words[0]) >= 3:
        return True
    return False


def _aff_dirty(v):
    """True if an affiliation string still carries unparsed LaTeX / math."""
    return bool(v) and any(ch in v for ch in ("$", "\\", "†", "‡", "↕"))


def _last_name_before(text):
    """Return the last capitalised name-like run in *text* (used to attribute
    a \\thanks / \\footnotemark to the author that immediately precedes it,
    even when macros sit between the name and the marker)."""
    cand = re.findall(r"[A-Z][\w.\-' ]{1,40}", text)
    if cand:
        nm = " ".join(cand[-1].split()).strip(" ,;.%")
        if looks_like_name(nm):
            return nm
    return None


def parse_aaai_affiliations(val):
    """AAAI \\affiliations{\\textsuperscript{\\rm 1}NIO \\qquad ...} -> {num: inst}."""
    out = {}
    for mm in re.finditer(
            r"\\textsuperscript\s*\{\\rm\s*(\d+)\}\s*(.*?)"
            r"(?=\\textsuperscript\s*\{\\rm|\s*\\qquad|\\\\|$)", val, re.S):
        inst = re.sub(r"\\(?:text|rm|it|sf|tt|bf)\b", " ", mm.group(2))
        inst = re.sub(r"\\[a-zA-Z]+\s*\{[^}]*\}", " ", inst)
        inst = re.sub(r"\\[a-zA-Z]+", " ", inst)
        inst = " ".join(inst.split()).strip(" ,;.")
        if inst and _looks_aff(inst):
            out.setdefault(mm.group(1), inst[:160])
    return out


def _scan_author_block(inner):
    """Robust name/affiliation/corresponding extraction for modern conference
    author blocks (AAAI, NeurIPS/corl, ivgpaper, generic comma lists).

    Returns (names, name_aff, affs, corr)."""
    names, name_aff, affs, corr = [], {}, {}, set()

    # ---- corresponding flags carried by macros (RoboEdit / USR-Drive) ----
    for m in re.finditer(
            r"([A-Z][\w.\-' ]{1,40}?)\s*\\textsuperscript\{[^}]*\}\s*"
            r"(?:\\correspondingicon|\\Letter|"
            r"\\thanks\s*\{[^{}]*correspond[^{}]*\})", inner):
        nm = " ".join(m.group(1).split()).strip()
        if looks_like_name(nm):
            corr.add(nm)
    for m in re.finditer(r"\\thanks\s*\{[^{}]*correspond[^{}]*\}", inner):
        nm = _last_name_before(inner[:m.start()])
        if nm:
            corr.add(nm)
    corr_fn = None
    for m in re.finditer(r"\\setcounter\s*\{footnote\}\s*\{(\d+)\}", inner):
        corr_fn = int(m.group(1)) + 1
    for m in re.finditer(r"\\footnotemark\s*\[(\d+)\]", inner):
        if corr_fn is not None and m.group(1) == str(corr_fn):
            nm = _last_name_before(inner[:m.start()])
            if nm:
                corr.add(nm)

    # ---- inline numbered affiliations  {{N}}Institution  (NeurIPS / ivg) ----
    # The (?<![A-Za-z]) lookbehind ensures we only treat a marker as an
    # affiliation prefix when it is NOT glued to a preceding name word (in the
    # name region markers are suffixed to names, e.g. "Yuhan Gong{{2}}").
    s = _normalize_markers(inner)
    s2 = _strip_junk(s)
    for mm in re.finditer(
            r"(?<![A-Za-z])\{\{(\d+)\}\}\s*([A-Za-z0-9].*?)(?=\s*\{\{\d|#\}\}|\s*\{\{#\}\}|$)", s2):
        inst = " ".join(mm.group(2).split()).strip(" ,;.")
        if _looks_real_aff(inst):
            affs.setdefault(mm.group(1), inst[:160])

    # ---- names + per-name affiliation numbers / corresponding flags ----
    # First word must be capitalised so conjunctions like "and"/"&" and
    # lowercase fragments never start a name token.
    toks = re.findall(r"\{\{[^}]+\}\}|[A-Z][\w.\-]*(?:\s+[A-Za-z][\w.\-]*)*", s2)
    cur = None
    seen = set()
    last_group = None          # set when a merged name was split into parts
    for tok in toks:
        if tok.startswith("{{"):
            im = re.search(r"\{\{([^}]+)\}\}", tok)
            val = im.group(1) if im else ""
            nums = re.findall(r"\d+", val)
            is_corr = ("#" in val) or ("CORR" in val)
            targets = last_group if last_group else ([cur] if cur else [])
            for tgt in targets:
                if nums:
                    name_aff.setdefault(tgt, [])
                    for n in nums:
                        if n not in name_aff[tgt]:
                            name_aff[tgt].append(n)
            if is_corr and cur:
                corr.add(cur)
            last_group = None
        else:
            cand = " ".join(tok.split())
            if not (looks_like_name(cand) and cand.lower() not in PLACEHOLDER_NAMES
                    and not NOTE_RE.search(cand)):
                cur = None
                last_group = None
                continue
            parts = cand.split()
            # A pinyin name block written as one token with a single trailing
            # marker (e.g. "Zheng Zhu Jiwen Lu") is really two people. Split
            # even-sized runs of capitalised syllables into "Given Surname" pairs.
            if len(parts) >= 4 and len(parts) % 2 == 0 and all(p[:1].isupper() for p in parts):
                subs = [" ".join(parts[i:i + 2]) for i in range(0, len(parts), 2)]
                last_group = subs
                for sub in subs:
                    if sub not in seen:
                        seen.add(sub)
                        names.append(sub)
                cur = subs[-1]
            else:
                if cand not in seen:
                    seen.add(cand)
                    names.append(cand)
                cur = cand
                last_group = None
    return names, name_aff, affs, corr


def tex_parse(tex):
    """Best-effort extraction of author names / affiliations / emails / corr from LaTeX.

    Handles the dialects actually seen on arXiv:
      - LLNCS  : \\institute{.. \\and ..}, \\inst{n}, \\name X \\email Y, \\addr Z
      - IEEE   : \\affiliation[1]{..}, \\authorblockA{INST}, \\thanks{.. are with INST}
      - custom : \\author{Name\\textsuperscript{1} \\qquad ... \\\\ \\textsuperscript{1}INST}
      - symbols: $^\\dagger$ / $^\\ddagger$ mapped to ordinals 1 / 2
      - emails : plain name@domain, bracket [a,b]@domain, \\email{..}
      - corr   : \\thanks{*Corresponding author}, \\correspondingauthor{..}, * marker
    Scans the whole source (some classes put \\author after \\begin{document})."""
    res = {"affs": {}, "emails": [], "corr": set(), "names": [], "name_aff": {}}
    if not tex:
        return res

    # Strip LaTeX line comments first: templates embed literal "\iffalse,\fi"
    # inside % comments, which would otherwise make the \iffalse..\fi strip
    # match across a real example block and leave it behind.
    tex = re.sub(r"(?m)(?<!\\)%.*$", "", tex)
    # Drop LaTeX \iffalse .. \fi comment blocks. arXiv templates ship example
    # author/affiliation blocks inside them (e.g. RoboEdit's AAAI examples) that
    # would otherwise be parsed as real metadata and pollute the output.
    tex = re.sub(r"\\iffalse.*?\\fi", "", tex, flags=re.S)
    tex = tex.replace("~", " ")

    # ---------- emails (global + bracket form [a,b]@domain + \\email{..}) ----------
    emails = set(re.findall(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", tex))
    for m in re.finditer(r"\[([^\]]*)\]@([A-Za-z0-9.-]+\.[A-Za-z]{2,})", tex):
        for local in re.split(r"[,\s&]+", m.group(1)):
            local = local.strip()
            if local and re.match(r"[A-Za-z0-9._%+-]+$", local):
                emails.add(f"{local}@{m.group(2)}")
    for m in re.finditer(r"\\email\s*\{([^\}]*)\}", tex):
        for e in re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", m.group(1)):
            emails.add(e)
    res["emails"] = sorted(emails)

    # ---------- \institute / \affiliation / \address (LLNCS/IEEE) ----------
    for val in _grab_braced(tex, "institute"):
        _tex_inst_to_aff(val, str(len(res["affs"]) + 1), res["affs"])
    for val in _grab_braced(tex, "affiliation"):
        _tex_inst_to_aff(val, str(len(res["affs"]) + 1), res["affs"])
    for val in _grab_braced(tex, "address"):
        _tex_inst_to_aff(val, str(len(res["affs"]) + 1), res["affs"])
    # AAAI-style \affiliations{...} with \textsuperscript{\rm N} numbering
    # (handles the plural \affiliations command the singular grab above misses).
    for cmd in ("affiliation", "affiliations", "address"):
        for val in _grab_braced(tex, cmd):
            for k, v in parse_aaai_affiliations(val).items():
                res["affs"].setdefault(k, v)

    # ---------- \addr (LLNCS-style affiliation line) ----------
    for m in re.finditer(r"\\addr\s+(.+?)(?:\\\\|\n|\\end|\\begin|\\author|$)", tex, re.S):
        val = re.sub(r"\\[a-zA-Z]+\s*\{[^}]*\}", "", m.group(1))
        val = " ".join(val.split()).strip(" ,;.")
        if AFF_HINT.search(val) and val not in res["affs"].values():
            res["affs"][str(len(res["affs"]) + 1)] = val[:160]

    # ---------- \name <Name> \email <email> (LLNCS / jmlr style) ----------
    for m in re.finditer(
            r"\\name\s+(.+?)\s*(?:\\textnormal\s*\{[^}]*\})?\s*\\email\s+(\S+?@\S+?)(?=\s|\\|$)",
            tex, re.S):
        nm = re.sub(r"\\[a-zA-Z]+\s*\{[^}]*\}", "", m.group(1))
        nm = " ".join(nm.split()).strip()
        if looks_like_name(nm) and nm.lower() not in PLACEHOLDER_NAMES:
            res["names"].append(nm)
            if "correspond" in m.group(1).lower():
                res["corr"].add(nm)

    # ---------- corresponding-author macros ----------
    for m in re.finditer(r"\\correspondingauthor\s*\{?([^}\\\n]{3,80})", tex):
        nm = m.group(1).strip().strip("{}")
        if looks_like_name(nm):
            res["corr"].add(nm)

    # ---------- \thanks blocks: affiliation (X are with INST) + correspondence ----------
    for m in re.finditer(r"\\thanks\s*\{", tex):
        blk = _balanced_brace(tex, m.start())
        nm = re.search(r"correspond(?:ing)?\s+author\s*[:：]?\s*([A-Z][\w\.\-' ]{2,60})",
                       blk, re.I)
        if nm and looks_like_name(nm.group(1).strip()):
            res["corr"].add(nm.group(1).strip())
        mk = re.search(r"\^\{(\d+)\}", blk)
        txt = re.sub(r"\\[a-zA-Z]+\s*\{[^}]*\}", " ", blk)
        txt = re.sub(r"[\{\}\\]", " ", txt)
        txt = " ".join(txt.split())
        for seg in re.split(r"(?<=[a-z])\.\s+", txt):
            seg = seg.strip(" ,;.")
            if AFF_HINT.search(seg) and not NOISE.search(seg) \
                    and 2 <= len(seg.split()) <= 25 and len(seg) < 200:
                key = mk.group(1) if mk else str(len(res["affs"]) + 1)
                if key not in res["affs"]:
                    res["affs"][key] = seg[:160]

    # ---------- author blocks: names + superscript-tagged affiliations ----------
    for m in re.finditer(r"\\author\s*(?:\[[^\]]*\])?\s*\{", tex):
        inner = _balanced_brace(tex, m.start())
        s = _superscript_to_token(inner)
        # affiliation lines (institution keyword present) -> capture before name split
        if AFF_RE_TEX.search(s):
            for seg in re.split(r"\\\\|\n", s):
                seg = seg.strip()
                if not seg or not AFF_RE_TEX.search(seg):
                    continue
                lm = re.match(r"\{\{(\d+)\}\}\s*(.*)$", seg)
                num = lm.group(1) if lm else str(len(res["affs"]) + 1)
                inst = re.sub(r"\{\{.*?\}\}", "", seg)
                inst = re.sub(r"\\(?:hspace|vspace)\s*\{[^}]*\}", " ", inst)
                inst = re.sub(r"\\[a-zA-Z]+\s*\{[^}]*\}", " ", inst)
                inst = " ".join(inst.split()).strip(" ,;.")
                if AFF_HINT.search(inst) and inst not in res["affs"].values():
                    res["affs"][num] = inst[:160]
        # name extraction: split on marker boundaries so space-joined names separate
        s_names = re.sub(r"\\thanks\s*\{[^{}]*\}", "", s)
        s_sep = re.sub(r"\{\{", "\u0001{{", s_names)
        for seg in re.split(r"\\\\|\n|\u0001", s_sep):
            seg = seg.strip()
            if not seg:
                continue
            for chunk in re.split(r",|\s*\band\b\s*|\s*&\s*", seg, flags=re.I):
                chunk = chunk.strip()
                if not chunk:
                    continue
                marks = re.findall(r"\{\{([^{}]*)\}\}", chunk)
                body = re.sub(r"\{\{.*?\}\}", "", chunk)
                body = re.sub(r"\\[a-zA-Z]+", " ", body)
                body = re.sub(r"[{}]", "", body)
                body = " ".join(body.split()).strip(" ,;.")
                if looks_like_name(body) and body.lower() not in PLACEHOLDER_NAMES:
                    res["names"].append(body)
                    if marks:
                        res["name_aff"].setdefault(body, [])
                        for mk2 in marks:
                            for num in re.findall(r"\d+", mk2):
                                if num not in res["name_aff"][body]:
                                    res["name_aff"][body].append(num)
                            if "*" in mk2:
                                res["corr"].add(body)

    # ---------- modern conference styles (AAAI / NeurIPS / ivgpaper / ...) ----------
    # Sits alongside the generic pass above and fills gaps the latter cannot
    # reach: AAAI \affiliations, NeurIPS $^\dagger$ markers, ivgpaper \ivgauthor,
    # and corresponding-author detection via \correspondingicon / \thanks /
    # \footnotemark.
    for cmd in ("author", "authors", "ivgauthor"):
        for m in re.finditer(r"\\" + cmd + r"(?:\s*\[[^\]]*\])?\s*\{", tex):
            inner = _balanced_brace(tex, m.start())
            sn, sa, saffs, sc = _scan_author_block(inner)
            for n in sn:
                if n not in res["names"]:
                    res["names"].append(n)
            for n, nums in sa.items():
                res["name_aff"].setdefault(n, [])
                for x in nums:
                    if x not in res["name_aff"][n]:
                        res["name_aff"][n].append(x)
            for k, v in saffs.items():
                if k not in res["affs"] or _aff_dirty(res["affs"][k]):
                    res["affs"][k] = v
            for c in sc:
                res["corr"].add(c)

    # dedupe names
    seen, uniq = set(), []
    for nm in res["names"]:
        if nm not in seen:
            seen.add(nm)
            uniq.append(nm)
    res["names"] = uniq

    # final sweep: strip residual LaTeX macros (e.g. \addr, \inst) left in
    # affiliation values by the LLNCS/IEEE \addr handler or HTML fallbacks.
    # Values are cleaned in place (no renumber) so author->aff key linkage holds.
    for k in list(res["affs"].keys()):
        cv = res["affs"][k]
        cv = re.sub(r"\\addr\b", "", cv)
        cv = re.sub(r"\\[a-zA-Z]+\s*\{[^}]*\}", "", cv)
        cv = re.sub(r"\\[a-zA-Z]+", "", cv)
        cv = " ".join(cv.split()).strip(" ,;.")
        res["affs"][k] = cv
    return res


def pdf_affiliations(pid, author_names):
    """Read numbered affiliations off the PDF title page.

    The affiliation band sits between the author line and the e-mail /
    Abstract line.  Scoping to that band matters: an author line such as
    'Changqing Zhou1 Yueru Luo2 ...' also matches '<digit><Capital>' and
    would otherwise be mistaken for an affiliation list.
    """
    txt = fetch_pdf_page1(pid)
    if not txt:
        return {}
    lines = [l.rstrip() for l in txt.split("\n")]
    surnames = {n.split()[-1] for n in author_names if n.split()}
    # Match a surname as a token: not preceded by a word char, and followed by
    # a digit/marker (PDF glues "Fu2"), a separator, or end-of-line.
    # Bare substring (short surname inside a longer word) mis-fires and pushes
    # the author-line scan past the affiliation band; a naive \b also fails
    # because "2" is a word char.
    surname_re = re.compile(
        r"(?<!\w)(" + "|".join(re.escape(s) for s in sorted(surnames, key=len, reverse=True))
        + r")(?=[\d\s,.*†‡\u2020\u2021]|$)")
    last_author_line = -1
    for k, l in enumerate(lines[:25]):
        if surname_re.search(l):
            last_author_line = k
    if last_author_line < 0:
        return {}
    band = []
    for l in lines[last_author_line + 1: last_author_line + 9]:
        low = l.lower().strip()
        if not low:
            continue
        if "@" in l or low.startswith(("abstract", "code:", "http", "project page",
                                       "keywords", "index terms")):
            break
        band.append(l)
    out = {}
    for m in re.finditer(r"(\d)\s*([A-Z][^\n\d]{4,110})", "\n".join(band)):
        v = clean_aff(m.group(2), m.group(1))
        if v and (AFF_HINT.search(v) or len(v.split()) >= 3):
            out.setdefault(m.group(1), v[:150])
    return out


# ------------------------------------------------------------- normalisation
def normalize(block):
    """HTML -> text where superscripts/markers become {{...}} tokens."""
    # MathML markers -> glyph
    def mathrepl(m):
        alt = m.group(1)
        return LATEX_GLYPH.get(alt.strip(), alt.strip().lstrip("\\"))
    block = re.sub(r'<math[^>]*alttext="([^"]*)"[^>]*>.*?</math>', mathrepl, block, flags=re.S)
    # LaTeX macros LaTeXML failed to expand
    block = re.sub(r'<span[^>]*class="ltx_ERROR undefined"[^>]*>\s*\\(equalcontrib|equal|thanks)\s*</span>',
                   "{{EQ}}", block)
    block = re.sub(r'<span[^>]*class="ltx_ERROR undefined"[^>]*>\s*\\(corresponding\w*)\s*</span>',
                   "{{CORR}}", block)
    # superscripts
    block = re.sub(r"<sup[^>]*>(.*?)</sup>",
                   lambda m: "{{%s}}" % " ".join(re.sub(r"<[^>]+>", "", m.group(1)).split()),
                   block, flags=re.S)
    block = re.sub(r"<br[^>]*>", "\n", block)
    block = re.sub(r"<[^>]+>", "", block)
    block = H.unescape(block).replace("\u00a0", " ")
    for k, v in LATEX_GLYPH.items():
        block = block.replace("$%s$" % k, v).replace(k, v)
    return block


def balanced_span(s, open_idx):
    """Given index of a '<span' that opens a block, return its inner HTML.
    LaTeXML nests <span> freely, so a non-greedy '(.*?)</span>' truncates."""
    i = s.find(">", open_idx)
    if i < 0:
        return ""
    depth, k = 1, i + 1
    while k < len(s) and depth:
        m = re.compile(r"</?span\b", re.I).search(s, k)
        if not m:
            return s[i + 1:]
        depth += -1 if m.group(0).startswith("</") else 1
        k = s.find(">", m.end())
        if k < 0:
            return s[i + 1:]
        k += 1
    return s[i + 1:k - len("</span>")]


def find_block(s, cls):
    """Return list of inner-HTML strings for every <span class="cls" ...>."""
    out = []
    for m in re.finditer(r'<span[^>]*class="%s"' % re.escape(cls), s):
        out.append(balanced_span(s, m.start()))
    return out


def looks_like_name(t):
    t = " ".join(t.split()).strip(" ,;.%")
    if not t or len(t) > 60 or "@" in t or any(ch.isdigit() for ch in t):
        return False
    if AFF_HINT.search(t) or NOISE.search(t):
        return False
    w = t.split()
    if not (1 < len(w) <= 6):
        return False
    return sum(1 for x in w if x[:1].isupper()) >= 2


def parse_marks(raw):
    raw = raw.strip()
    marks = []
    for tok in re.split(r"[,\s]+", raw):
        tok = tok.strip().strip(".")
        if tok:
            marks.append(tok)
    return marks


def split_names(line):
    """Return [(name, [marks])] from a normalised author line."""
    line = re.sub(r"\s+and\s+", ", ", line)
    line = re.sub(r"(?<=\}\})\s+(?=[A-ZÀ-Þ])", ", ", line)   # 'A{{1}} B{{2}}'
    # protect commas inside {{...}} so they survive the name split
    line = re.sub(r"\{\{(.*?)\}\}", lambda m: "{{%s}}" % m.group(1).replace(",", "\x01"), line)
    out = []
    for chunk in line.split(","):
        chunk = chunk.replace("\x01", ",")
        chunk = chunk.strip()
        if not chunk:
            continue
        marks = [m for m in re.findall(r"\{\{(.*?)\}\}", chunk)]
        name = re.sub(r"\{\{.*?\}\}", "", chunk).strip(" ,;.")
        # Per-author <ltx_personname> blocks can carry the list conjunction
        # ("and Yongseok Lee"); the \s+and\s+ split above cannot see it because
        # there is no leading whitespace at start-of-string.
        name = re.sub(r"^(?:and|&)\s+", "", name, flags=re.I).strip()
        if looks_like_name(name):
            flat = []
            for m in marks:
                flat.extend(parse_marks(m))
            out.append((name, flat))
    return out


# --------------------------------------------------------------- main parser
def parse_paper(pid):
    rec = {"ok": False, "source": "none", "authors": [], "affiliations": {},
           "corr_markers": [], "equal_markers": [], "emails": [], "warn": ""}
    doc, tag = fetch_html(pid)

    if not doc:
        rec["warn"] = "无 arXiv HTML 渲染版本；尝试从 LaTeX 源码提取"
    else:
        rec["source"] = tag

    adiv_ok = bool(doc) and doc.find('<div class="ltx_authors">') >= 0
    if adiv_ok:
        i = doc.find('<div class="ltx_authors">')
        j = doc.find('<div id="abstract', i)
        if j < 0:
            j = doc.find('class="ltx_abstract"', i)
        if j < 0:
            j = i + 30000
        adiv = doc[i:j]

        # ---------- notes: footnotes + author_notes ----------
        notes = []
        for m in re.finditer(r'class="ltx_note_content">(.*?)</span></span>', doc[:i + 60000], re.S):
            notes.append(normalize(m.group(1)).strip())
        for blk in find_block(adiv, "ltx_author_notes"):
            notes.append(normalize(blk).strip())

        affs = {}          # "1" -> institution
        name_aff = {}      # explicit name -> institution (IEEE style)
        corr_marks, equal_marks, corr_names = set(), set(), set()

        for n in notes:
            # (B) LLNCS: "1institutetext: Beihang University"  /  "{{1}}institutetext: ..."
            for mm in re.finditer(r"\{?\{?(\d+)\}?\}?\s*institutetext\s*:\s*([^\n]+)", n):
                affs[mm.group(1)] = clean_aff(mm.group(2), mm.group(1))[:160]
            if "institutetext" in n:   # sibling institutes may follow on later lines
                for mm in re.finditer(r"(?m)^\s*\{?\{?(\d+)\}?\}?\s*([A-Z][^\n]{3,110})$", n):
                    affs.setdefault(mm.group(1), clean_aff(mm.group(2), mm.group(1))[:160])
            # (D/E) "{{N}}Institution."  — also catches the IEEE variant
            #       "{{1}}X and Y are with the <Inst>." where the institution is
            #       everything *after* "are with" (strip the leading name phrase).
            for mm in re.finditer(r"\{\{(\d+)\}\}\s*([^{\n]{4,160})", n):
                txt = mm.group(2).strip()
                m2 = re.search(r"are\s+with\s+(?:the\s+)?(.+)", txt, re.I)
                if m2:
                    txt = m2.group(1)
                txt = re.split(r"(?<=[a-z])\.\s+(?=[A-Z])", txt.strip())[0]
                txt = clean_aff(txt, mm.group(1))
                if txt and not NOISE.search(txt) and (AFF_HINT.search(txt) or "," in txt):
                    affs.setdefault(mm.group(1), txt[:160])
            # (C) IEEE "A, B and C are with the <inst> (e-mail: ...)"
            for mm in re.finditer(
                    r"([A-ZÀ-Þ][\w\.\-'’]*(?:\s+[\w\.\-'’]+)*?(?:,\s*[A-ZÀ-Þ][\w\.\-'’ ]+)*"
                    r"(?:\s+and\s+[A-ZÀ-Þ][\w\.\-'’ ]+)?)\s+(?:are|is)\s+with\s+(?:the\s+)?"
                    r"(.+?)(?:\s*\(e-?mail|\.\s*[A-ZÀ-Þ][a-z]+\s+[A-ZÀ-Þ]|$)", n, re.S):
                who, inst = mm.group(1), clean_aff(mm.group(2))
                # accept a non-keyword institution if it still reads like an org name
                if not inst or not (AFF_HINT.search(inst) or len(inst.split()) >= 3):
                    continue
                for nm in re.split(r",|\s+and\s+", who):
                    nm = nm.strip()
                    if looks_like_name(nm):
                        name_aff[nm] = inst[:150]
            # corresponding-by-name
            for mm in re.finditer(r"[Cc]orresponding\s+authors?\s*[:：]\s*([^\.\n]+)", n):
                for nm in re.split(r",|\s+and\s+", mm.group(1)):
                    nm = nm.strip()
                    if looks_like_name(nm):
                        corr_names.add(nm)
            # marker semantics: glyph followed by explanatory text
            seq = re.sub(r"([%s])\1+" % re.escape(MARK_CHARS), r"\1", n)
            hits = [(m.start(), m.group(0)) for m in re.finditer("[%s]" % re.escape(MARK_CHARS), seq)]
            for k, (pos, g) in enumerate(hits):
                end = hits[k + 1][0] if k + 1 < len(hits) else len(seq)
                seg = seq[pos + 1:end].lower()
                if "correspond" in seg:
                    corr_marks.add(g)
                if "equal" in seg or "co-first" in seg or "equally" in seg:
                    equal_marks.add(g)
            low = n.lower()
            if "correspond" in low and not any(g in n for g in MARK_CHARS) and not corr_names:
                corr_marks.add("__unmarked__")

        # ---------- names from ltx_creator spans ----------
        creators = find_block(adiv, "ltx_creator ltx_role_author") or [adiv]

        authors = []
        for cb in creators:
            pn = find_block(cb, "ltx_personname")
            txt = normalize(pn[0] if pn else cb)
            prev_aff = None
            for line in txt.split("\n"):
                line = " ".join(line.split())
                if not line or "@" in line or line.startswith("{"):
                    continue
                am = re.match(r"^\{\{(\d+)\}\}\s*(.+)$", line)      # (E) inline affiliation
                if am:
                    prev_aff = am.group(1)
                    affs.setdefault(prev_aff, am.group(2).strip(" .,")[:160])
                    continue
                got = split_names(line)
                if got:
                    prev_aff = None
                    authors.extend(got)
                elif prev_aff and AFF_HINT.search(line) and "{{" not in line:
                    # continuation of the previous numbered affiliation (wrapped line)
                    affs[prev_aff] = (affs[prev_aff] + " " + line.strip(" .,"))[:190]
                elif AFF_HINT.search(line) and "{{" not in line:     # (F) shared affiliation
                    affs.setdefault("_shared", line.strip(" .,")[:160])
            # explicit affiliation span (ACM/IEEE) — nested <span> need balanced parse
            for m in re.finditer(r'<span[^>]*class="ltx_role_affiliation"', cb):
                inner = normalize(balanced_span(cb, m.start()))
                a = re.sub(r"^\s*Affiliation\s*:\s*", "", inner, flags=re.I).strip(" .,")
                a = " ".join(a.split())
                if a and a not in affs.values():
                    affs[str(len([k for k in affs if k.isdigit()]) + 1)] = a[:160]

        # dedupe, keep order
        seen, uniq = set(), []
        for nm, mk in authors:
            if nm not in seen:
                seen.add(nm)
                uniq.append((nm, mk))
        authors = uniq
        if not authors:
            rec["warn"] = "作者行解析失败；尝试从 LaTeX 源码提取"
        else:
            # ---------- emails from HTML (ltx_role_email) ----------
            emails_html = []
            for eb in find_block(doc, "ltx_role_email"):
                emails_html += re.findall(
                    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", normalize(eb))
            # ---------- PDF fallback for missing affiliations ----------
            numbered = {int(m) for _, mk in authors for m in mk if m.isdigit()}
            have = {int(k) for k in affs if k.isdigit()}
            if (numbered and not numbered.issubset(have)) or (not numbered and not have):
                got = pdf_affiliations(pid, [n for n, _ in authors])
                for k, v in got.items():
                    affs.setdefault(k, v)
                if got:
                    rec["source"] += "+pdf"
            # single unnumbered shared affiliation
            shared = affs.pop("_shared", None)
            if shared and not any(k.isdigit() for k in affs):
                affs["1"] = clean_aff(shared)
            # ---------- assemble ----------
            numeric_affs = sorted(int(k) for k in affs if k.isdigit())
            only_one_aff = len(numeric_affs) == 1
            out = []
            for k, (nm, mk) in enumerate(authors):
                aff_ids = [int(x) for x in mk if x.isdigit() and x in affs]
                # a single institution applies to everyone who carries no numeric marker
                if not aff_ids and only_one_aff and not any(x.isdigit() for x in mk):
                    aff_ids = [numeric_affs[0]]
                if not aff_ids and nm in name_aff:
                    key = next((kk for kk, vv in affs.items() if vv == name_aff[nm]), None)
                    if key is None:
                        key = str(max([int(x) for x in affs if x.isdigit()] + [0]) + 1)
                        affs[key] = name_aff[nm]
                    aff_ids = [int(key)]
                is_corr = (nm in corr_names) or any(m in corr_marks for m in mk) \
                          or any(c in "".join(mk) for c in ENVELOPE) or ("CORR" in mk)
                is_eq = any(m in equal_marks for m in mk) or ("EQ" in mk)
                out.append({"name": nm, "marks": [m for m in mk if m not in ("EQ", "CORR")],
                            "affs": sorted(aff_ids), "first": k == 0,
                            "equal": bool(is_eq), "corr": bool(is_corr)})
            rec["ok"] = True
            rec["authors"] = out
            rec["affiliations"] = {k: v for k, v in sorted(affs.items(), key=lambda x: int(x[0]))
                                   if k.isdigit()}
            rec["corr_markers"] = sorted(corr_marks)
            rec["equal_markers"] = sorted(equal_marks)
            rec["_emails_html"] = emails_html
            warns = []
            if not rec["affiliations"]:
                warns.append("该论文的 arXiv 渲染版本未提供作者单位信息")
            if "__unmarked__" in corr_marks and not any(a["corr"] for a in out):
                warns.append("论文标注了通讯作者，但渲染版本未保留其归属")
            rec["warn"] = "；".join(warns)

    # ---------- LaTeX e-print fallback (supplementary source) ----------
    if not rec.get("affiliations") or not rec.get("_emails_html"):
        tex = fetch_eprint(pid)
        tp = tex_parse(tex)
        # Prefer TeX affiliations when the HTML ones are unparsed (still carry
        # raw $^\dagger$ / \textsuperscript LaTeX, or missing entirely).
        html_affs = rec.get("affiliations") or {}
        dirty = any(("$" in v) or ("\\" in v) or ("†" in v) or ("‡" in v)
                    for v in html_affs.values())
        if tp["affs"] and (not html_affs or dirty):
            rec["affiliations"] = tp["affs"]
            rec["source"] += "+tex"
        if tp["emails"]:
            rec["_emails_html"] = sorted(set(rec.get("_emails_html", []) + tp["emails"]))
        if tp["corr"] and rec.get("authors"):
            for a in rec["authors"]:
                if a["name"] in tp["corr"]:
                    a["corr"] = True
        if tp.get("name_aff") and rec.get("authors") and rec.get("affiliations"):
            for a in rec["authors"]:
                if a["name"] in tp["name_aff"]:
                    tex_affs = [int(x) for x in tp["name_aff"][a["name"]]
                               if str(x).isdigit() and str(x) in rec["affiliations"]]
                    if tex_affs:
                        a["affs"] = sorted(tex_affs)
        if not rec.get("authors") and tp.get("names"):
            out = []
            for k, nm in enumerate(tp["names"]):
                aff_ids = [int(x) for x in tp["name_aff"].get(nm, [])
                           if str(x).isdigit() and str(x) in tp["affs"]]
                out.append({"name": nm, "marks": [], "affs": sorted(aff_ids), "first": k == 0,
                            "equal": False, "corr": nm in tp["corr"]})
            rec["authors"] = out
            rec["ok"] = True
            if not rec.get("affiliations"):
                rec["affiliations"] = tp["affs"]
            rec["source"] += "+tex"

    rec["emails"] = sorted(set(rec.get("_emails_html", [])))
    return rec


def enrich(ids, out_path):
    meta = {}
    for pid in ids:
        r = parse_paper(pid)
        meta[pid] = r
        print(f"{'OK ' if r['ok'] else 'XX '}{pid} n={len(r['authors'])} affs={len(r['affiliations'])} "
              f"corr={[a['name'] for a in r['authors'] if a['corr']]} "
              f"eq={[a['name'] for a in r['authors'] if a['equal']]} "
              f"emails={len(r['emails'])} "
              f"src={r['source']} {r['warn']}")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    print("wrote", out_path)
    return meta


if __name__ == "__main__":
    import argparse
    import os as _os
    ap = argparse.ArgumentParser(description="Enrich authors_meta.json from arXiv HTML/E-print.")
    ap.add_argument("ids", nargs="*", help="arXiv IDs to enrich")
    ap.add_argument("--out", default=_os.path.join(_os.getcwd(), "authors_meta.json"),
                    help="output path for authors_meta.json (default: ./authors_meta.json)")
    args = ap.parse_args()
    # No baked-in ID defaults: an implicit fallback list would both run on stale
    # papers and leak whatever batch the skill happened to be packaged from.
    if not args.ids:
        ap.error("no arXiv IDs given — pass them explicitly, e.g.\n"
                 "  enrich_authors.py 0000.00001 0000.00002 --out authors_meta.json")
    enrich(args.ids, args.out)
