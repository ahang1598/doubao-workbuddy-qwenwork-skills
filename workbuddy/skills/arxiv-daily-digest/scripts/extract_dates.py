#!/usr/bin/env python3
"""arXiv daily digest — Stage 2 helper: extract v1 submission dates from arXiv stamps.

Reads /tmp/aug_<id>.pdf (downloaded by augment_authors.py) or downloads the
missing PDFs via proxy.cors.sh, then extracts the arXiv side stamp
"arXiv:<id>v1 [cat] D Mon YYYY" from the first pages using PyMuPDF (pypdf is
unreliable on some arXiv PDFs: "EOF marker not found").

Usage:
    python3 extract_dates.py <id1> <id2> ... --out submit_dates_<tag>.json
"""
import argparse, json, os, re, subprocess

import fitz  # PyMuPDF

MON = dict(Jan=1, Feb=2, Mar=3, Apr=4, May=5, Jun=6,
           Jul=7, Aug=8, Sep=9, Oct=10, Nov=11, Dec=12)
CLEAN = {**os.environ, "http_proxy": "", "https_proxy": "",
         "HTTP_PROXY": "", "HTTPS_PROXY": "", "all_proxy": "", "ALL_PROXY": ""}


def pdf_text(pid, max_pages=3):
    p = f"/tmp/aug_{pid}.pdf"
    if not os.path.exists(p) or os.path.getsize(p) < 10000:
        subprocess.run(["curl", "-s", "-L", "--noproxy", "*", "--max-time", "180",
                        "-A", "Mozilla/5.0", "-o", p,
                        f"https://proxy.cors.sh/https://arxiv.org/pdf/{pid}"], env=CLEAN)
    d = fitz.open(p)
    return [d[i].get_text() for i in range(min(max_pages, len(d)))]


def stamp_date(pid):
    for txt in pdf_text(pid):
        m = re.search(r"arXiv:" + re.escape(pid) +
                      r"v1\s*\[[^\]]*\]\s*(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})", txt or "")
        if m:
            return f"{m.group(3)}-{MON[m.group(2)]:02d}-{int(m.group(1)):02d}"
    return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="+")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    dates = {}
    for pid in args.ids:
        d = stamp_date(pid)
        if not d:
            print(f"WARNING {pid}: no stamp found — fetch https://arxiv.org/abs/{pid} "
                  f"and read the [Submitted on ...] line manually")
        dates[pid] = d
        print(pid, "->", d or "NOT FOUND")
    json.dump(dates, open(args.out, "w"), indent=1)
    print("saved", args.out)


if __name__ == "__main__":
    main()
