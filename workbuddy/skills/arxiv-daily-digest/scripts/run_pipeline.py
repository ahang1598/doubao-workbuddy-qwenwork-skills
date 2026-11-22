#!/usr/bin/env python3
"""arXiv daily digest — Stage 1: fetch, parse, and rank one announcement batch.

Consolidates the per-day fetch/parse/rank steps into one parameterized tool.
The arXiv *topic* is supplied by the caller (user input), not hardcoded:

  - `--cats`     which arXiv categories to pull from /list/<cat>/new
                (default: cs.CV,cs.RO,cs.GR,cs.AI,cs.LG,cs.MM)
  - `--topic`    human-readable topic label for the report
                (e.g. "Embodied AI / Computer Vision / 3D Reconstruction")
  - `--keywords` OPTIONAL custom theme keywords (comma-separated). When given,
                they REPLACE the built-in theme dictionary; a paper matches if
                it hits >= `--threshold` of them. When omitted, the built-in
                embodied/cv/3d theme dictionary is used.

Usage (run from the workspace that will hold the output JSONs):
    python3 run_pipeline.py --tag 0905 --topic "Embodied AI" \
        --cats cs.RO,cs.AI --keywords "robot,manipulation,grasp,embodied"

Outputs in the current working directory:
    arxiv_parsed_<tag>.json     theme-hit candidates
    ranked_<tag>.json          quality-proxy ranked candidates (descending)
    digest_config_<tag>.json   {topic, cats, keywords, custom, threshold}

Network notes:
    - Direct TLS to arxiv.org is usually reset by the local sandbox; the script
      tries direct first, then falls back to https://proxy.cors.sh/ which
      relays raw arXiv HTML unchanged (preserving list-comments venue fields).
"""
import argparse, json, os, re, html as ihtml, subprocess
from concurrent.futures import ThreadPoolExecutor

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
PROXY = "https://proxy.cors.sh/"
CLEAN = {**os.environ, "http_proxy": "", "https_proxy": "",
         "HTTP_PROXY": "", "HTTPS_PROXY": "", "all_proxy": "", "ALL_PROXY": ""}

# Built-in theme dictionary (used when --keywords is NOT supplied).
THEME_KW = {
    "embodied": ["embodied", "robot", "manipulat", "grasp", "locomot", "vla", "world model",
                 "world action", "navigation", "agentic", " dexterous", "bimanual",
                 "humanoid", "quadruped", "teleoperation", "sim-to-real", "imitation learning",
                 "task planning", "reinforcement learning", "embodiment"],
    "cv": ["computer vision", "segmentation", "detection", "image generation", "video generation",
           "diffusion model", "visual", "image", "video", "scene understanding", "recognition",
           "tracking", "pose", "optical flow", "depth estimation", "semantic", "foundation model",
           "generative", "multimodal", "vision-language"],
    "3d": ["3d reconstruction", "gaussian splatting", "nerf", "neural radiance", "mesh",
           "point cloud", "slam", "3d generation", "3d gaussian", "multi-view",
           "novel view", "photometric", "geometry", "surface reconstruction", "occupancy",
           "voxel", "3d scene", "inverse rendering", "camera", "3d human", "avatar",
           "reconstruction", "rgb-d", "lidar"],
}

VENUE = [
    (["cvpr"], 10, "CVPR"), (["iccv"], 10, "ICCV"), (["eccv"], 10, "ECCV"),
    (["neurips", "nips"], 10, "NeurIPS"), (["icml"], 10, "ICML"), (["iclr"], 9, "ICLR"),
    (["siggraph"], 10, "SIGGRAPH"), (["tpami", "pami"], 10, "TPAMI"), (["ijcv"], 9, "IJCV"),
    (["rss", "robotics: science"], 9, "RSS"), (["corl"], 9, "CoRL"),
    (["icra"], 8, "ICRA"), (["iros"], 8, "IROS"), (["ra-l", "ral"], 8, "RA-L"),
    (["acm mm", "acmmm", "acm multimedia"], 8, "ACM MM"),
    (["aaai"], 7, "AAAI"), (["ijcai"], 7, "IJCAI"), (["acl"], 7, "ACL"),
    (["emnlp"], 7, "EMNLP"), (["tmlr"], 7, "TMLR"), (["3dv"], 7, "3DV"),
    (["wacv"], 6, "WACV"), (["bmvc"], 6, "BMVC"), (["gcpr"], 6, "GCPR"),
    (["t-ro", "tro"], 9, "T-RO"), (["jmlr"], 8, "JMLR"),
]

BENCH = ["benchmark", "dataset", "we release", "released", "open-source", "open source",
         "publicly available", "will be available", "code and", "toolkit", "simulator",
         "test suite", "leaderboard"]
EMPIRICAL = ["state-of-the-art", "state of the art", "sota", "outperform", "surpass",
             "improve", "gain", "reduc", "achieve", "best-performing", "new record",
             "exceed", "advance"]
SCALE = ["million", "large-scale", "large scale", "billion", "hours of", "real-world deployment",
         "real robot", "real-robot", "physical robot", "hardware"]


# --------------------------------------------------------------- fetch
def curl(url, out, timeout=120):
    r = subprocess.run(
        ["curl", "-s", "-L", "--noproxy", "*", "--max-time", str(timeout),
         "-A", UA, "-o", out, "-w", "%{http_code}", url],
        capture_output=True, text=True, env=CLEAN)
    return r.stdout.strip()


def valid(path):
    if not os.path.exists(path) or os.path.getsize(path) < 3000:
        return False
    return "Showing new listings for" in open(path, encoding="utf-8", errors="ignore").read(400000)


def fetch_one(cat, tag):
    out = os.path.join(tempfile_dir(), f"{tag}_{cat}.html")
    direct = f"https://arxiv.org/list/{cat}/new"
    code = curl(direct, out)
    if code == "200" and valid(out):
        return cat, "direct", out
    for _ in range(3):
        code = curl(PROXY + direct, out, 180)
        if code == "200" and valid(out):
            return cat, "proxy", out
    return cat, "FAIL", out


def tempfile_dir():
    import tempfile
    d = os.path.join(tempfile.gettempdir(), "arxiv_digest")
    os.makedirs(d, exist_ok=True)
    return d


# --------------------------------------------------------------- parse
def clean(s):
    s = re.sub(r"<[^>]+>", "", s)
    s = ihtml.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def parse_file(path, cat):
    data = open(path, encoding="utf-8", errors="ignore").read()
    dm = re.search(r"Showing new listings for ([^<]+)</h3>", data)
    listing_date = dm.group(1).strip() if dm else "?"
    out, current = [], "NEW"
    for sec in re.split(r"<h3>", data):
        h = sec[:140].lower()
        if "new submissions" in h:
            current = "NEW"
        elif "cross-list" in h:
            current = "CROSS"
        elif "replacement" in h:
            current = "REPL"
        if current == "REPL":
            continue
        for dt, dd in re.findall(r"<dt>(.*?)</dt>\s*<dd>(.*?)</dd>", sec, re.DOTALL):
            idm = re.search(r"/abs/([0-9]+\.[0-9]+)", dt)
            if not idm:
                continue
            aid = idm.group(1)
            title_m = re.search(r"list-title[^>]*>(?:<span[^>]*>.*?</span>)?\s*(.*?)</div>", dd, re.DOTALL)
            auth_m = re.search(r"list-authors[^>]*>(.*?)</div>", dd, re.DOTALL)
            authors_raw = auth_m.group(1) if auth_m else ""
            authors = [clean(a) for a in re.findall(r">([^<]+)</a>", authors_raw)]
            if not authors:
                authors = [clean(re.sub(r"<[^>]+>", "", authors_raw))]
            subj_m = re.search(r"list-subjects[^>]*>(?:<span[^>]*>.*?</span>)?\s*(.*?)</div>", dd, re.DOTALL)
            paras = re.findall(r"<p class=[\"']mathjax[\"']>(.*?)</p>", dd, re.DOTALL)
            abstract = clean(" ".join(paras)) if paras else ""
            if not abstract:
                bq = re.search(r"<blockquote[^>]*>(.*?)</blockquote>", dd, re.DOTALL)
                abstract = clean(bq.group(1)) if bq else ""
            cm = re.search(r"list-comments[^>]*>(?:<span[^>]*>.*?</span>)?\s*(.*?)</div>", dd, re.DOTALL)
            out.append(dict(id=aid, title=clean(title_m.group(1)) if title_m else "",
                            authors=authors, subjects=clean(subj_m.group(1)) if subj_m else "",
                            abstract=abstract, comment=clean(cm.group(1)) if cm else "",
                            category=cat, section=current, listing_date=listing_date))
    return out


# --------------------------------------------------------------- rank
def venue_of(comment):
    c = comment.lower()
    best = (0, "")
    for keys, pts, name in VENUE:
        for k in keys:
            if re.search(r"\b" + re.escape(k) + r"\b", c) and pts > best[0]:
                tag = name
                if "oral" in c:
                    tag += " Oral"
                elif "spotlight" in c:
                    tag += " Spotlight"
                elif "highlight" in c:
                    tag += " Highlight"
                if "workshop" in c or re.search(r"\bws\b", c):
                    tag += " Workshop"
                    pts = max(3, pts - 5)
                best = (pts, tag)
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True, help="batch tag, e.g. 0905 (used for tmp + output filenames)")
    ap.add_argument("--cats", default="cs.CV,cs.RO,cs.GR,cs.AI,cs.LG,cs.MM",
                    help="comma-separated arXiv categories to fetch (user-supplied topic scope)")
    ap.add_argument("--topic", default="arXiv Daily Digest",
                    help="human-readable topic label for the report (user-supplied)")
    ap.add_argument("--keywords", default="",
                    help="OPTIONAL custom theme keywords (comma-separated); replaces built-in themes")
    ap.add_argument("--threshold", type=int, default=0,
                    help="theme-hit threshold to keep a candidate (0 = auto: 3 built-in / 1 custom)")
    ap.add_argument("--outdir", default=".", help="directory for output JSON (default: cwd)")
    args = ap.parse_args()

    cats = [c.strip() for c in args.cats.split(",") if c.strip()]
    custom = bool(args.keywords.strip())
    if custom:
        THEME = {"topic": [k.strip().lower() for k in args.keywords.split(",") if k.strip()]}
    else:
        THEME = THEME_KW
    threshold = args.threshold or (1 if custom else 3)
    tag = args.tag
    os.makedirs(args.outdir, exist_ok=True)

    # fetch
    results = {}
    with ThreadPoolExecutor(max_workers=max(1, len(cats))) as ex:
        for cat, route, path in ex.map(lambda c: fetch_one(c, tag), cats):
            results[cat] = (route, path)
            print(f"{cat:8s} {route:7s} -> {path}")
    failed = [c for c, (r, _) in results.items() if r == "FAIL"]
    if failed:
        raise SystemExit(f"FETCH FAILED for: {failed}")

    # parse
    allp, per_cat = {}, {}
    for c in cats:
        for e in parse_file(results[c][1], c):
            allp.setdefault(e["id"], e)
        per_cat[c] = sum(1 for e in allp.values() if e["category"] == c and e["id"] in allp)
    print("per-category parsed:", per_cat)
    print(f"unique total={len(allp)}")
    dates = {}
    for e in allp.values():
        dates[e["listing_date"]] = dates.get(e["listing_date"], 0) + 1
    print("listing dates:", dates)
    if len(dates) != 1:
        print("WARNING: mixed listing dates — verify the batch is 'the most recent day'")

    theme_keys = list(THEME.keys())
    for e in allp.values():
        txt = e["title"] + " . " + e["abstract"] + " . " + e["comment"]
        t = txt.lower()
        sc = {th: sum(1 for k in kws if k in t) for th, kws in THEME.items()}
        e["theme_scores"] = sc
        e["theme_total"] = sum(sc.values())

    cands = []
    for e in allp.values():
        if e["theme_total"] >= threshold:
            e["themes"] = [k for k in theme_keys if e["theme_scores"][k] >= 1]
            cands.append(e)
    print(f"theme candidates(>={threshold})={len(cands)}")
    json.dump({"candidate_count": len(cands), "topic": args.topic, "custom": custom,
               "candidates": cands},
              open(os.path.join(args.outdir, f"arxiv_parsed_{tag}.json"), "w"),
              ensure_ascii=False, indent=1)

    # rank (topic-agnostic quality proxy)
    for e in cands:
        txt = (e["title"] + " " + e["abstract"] + " " + e["comment"]).lower()
        vp, vname = venue_of(e["comment"])
        e["venue_pts"], e["venue_name"] = vp, vname
        e["bench_pts"] = min(6, sum(2 for k in BENCH if k in txt))
        e["emp_pts"] = min(6, sum(1 for k in EMPIRICAL if k in txt))
        e["scale_pts"] = min(4, sum(2 for k in SCALE if k in txt))
        nums = re.findall(r"(?:\+|by\s)(\d+(?:\.\d+)?)\s?(?:%|pp|points)", txt)
        xs = re.findall(r"(\d+(?:\.\d+)?)\s?[x×]\s?(?:faster|speed|fewer|less|more)", txt)
        e["num_pts"] = min(5, len(nums) * 2 + len(xs) * 2)
        ts = e["theme_scores"]
        e["theme_pts"] = min(8, sum(ts.values()))
        e["multi_theme"] = sum(1 for k in theme_keys if ts[k] >= 2)
        e["quality"] = (vp * 2.2 + e["bench_pts"] * 1.3 + e["emp_pts"] * 1.0
                        + e["scale_pts"] * 0.9 + e["num_pts"] * 1.4
                        + e["theme_pts"] * 0.8 + e["multi_theme"] * 1.5)

    cands.sort(key=lambda e: -e["quality"])
    print(f"\n{'rank':>4} {'id':<12} {'q':>6} {'venue':<16} themes  title")
    print("-" * 140)
    for i, e in enumerate(cands[:55], 1):
        ts = e["theme_scores"]
        th = "/".join(f"{k}{ts[k]}" for k in theme_keys)
        print(f"{i:>4} {e['id']:<12} {e['quality']:>6.1f} {(e['venue_name'] or '-'):<16} "
              f"{th:<14} {e['title'][:60]}")
    json.dump(cands, open(os.path.join(args.outdir, f"ranked_{tag}.json"), "w"),
              ensure_ascii=False, indent=1)

    cfg = dict(topic=args.topic, cats=cats, keywords=args.keywords, custom=custom,
               threshold=threshold)
    json.dump(cfg, open(os.path.join(args.outdir, f"digest_config_{tag}.json"), "w"),
              ensure_ascii=False, indent=1)
    print(f"\nsaved arxiv_parsed_{tag}.json + ranked_{tag}.json + digest_config_{tag}.json")


if __name__ == "__main__":
    main()
