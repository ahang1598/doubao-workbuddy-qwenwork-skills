#!/usr/bin/env python3
"""download_omics.py — ENCODE / GEO multi-omics downloader with integrity checks.

Part of the esc-aging-multiomics skill (Phase 0: Data Acquisition & Verification).

Features
--------
* ENCODE: download a single File (ENCFF...) or all files of an Experiment (ENCSR...),
  resolving download URL, MD5 and expected size from the ENCODE REST API.
* GEO: download a supplementary file by URL, or every supplementary file of a GSE
  series by deriving its NCBI FTP directory.
* Integrity verification: MD5 (when ENCODE provides it) and/or expected file size.
* Auto re-download: any file failing verification is deleted and fetched again;
  network failures retry up to --retries times.
* Manifest mode: batch a JSON list of items and re-verify an existing download set.

Environment contract: Python 3.13+ standard library only (urllib, hashlib, json,
argparse). No third-party packages required.

Examples
--------
  python download_omics.py encode-file  ENCFF000AAA  ./data
  python download_omics.py encode-exp    ENCSR000AAA  ./data --assembly GRCh38 --types fastq,bigWig
  python download_omics.py geo-file      https://ftp.ncbi.nlm.nih.gov/.../file.bed.gz  ./data
  python download_omics.py geo-series    GSE12345     ./data
  python download_omics.py manifest      manifest.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ENCODE_API = "https://www.encodeproject.org"
DEFAULT_RETRIES = 3
CHUNK = 1 << 20  # 1 MiB


# --------------------------------------------------------------------------- #
# Low-level download + verification
# --------------------------------------------------------------------------- #
def _progress(done: int, total: int) -> None:
    if total:
        pct = done * 100 // total
        sys.stderr.write(f"\r    {done:,}/{total:,} bytes ({pct}%)")
        sys.stderr.flush()
    else:
        sys.stderr.write(f"\r    {done:,} bytes")
        sys.stderr.flush()


def stream_to_file(url: str, dest: Path, expected_size: int | None = None) -> int:
    """Download *url* to *dest*, returning bytes written. Raises on HTTP error."""
    req = urllib.request.Request(url, headers={"User-Agent": "esc-aging-multiomics/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        total = int(resp.headers.get("Content-Length", 0) or 0)
        written = 0
        with open(dest, "wb") as fh:
            while True:
                buf = resp.read(CHUNK)
                if not buf:
                    break
                fh.write(buf)
                written += len(buf)
                _progress(written, total)
    sys.stderr.write("\n")
    if expected_size is not None and written != expected_size:
        raise ValueError(
            f"size mismatch: got {written:,} but expected {expected_size:,}"
        )
    return written


def md5_of(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def verified_download(
    url: str,
    dest: Path,
    expected_md5: str | None = None,
    expected_size: int | None = None,
    retries: int = DEFAULT_RETRIES,
) -> bool:
    """Download *url* into *dest* and verify. Returns True on success.

    On any failure (network or verification) the partial/incorrect file is removed
    and the download is retried. Re-download-on-failure is the core integrity loop.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            if dest.exists():
                dest.unlink()
            print(f"  attempt {attempt}/{retries}: {url}")
            stream_to_file(url, dest, expected_size=expected_size)
            if expected_md5 is not None:
                actual = md5_of(dest)
                if actual.lower() != expected_md5.lower():
                    raise ValueError(
                        f"md5 mismatch: got {actual} expected {expected_md5}"
                    )
            print(f"  OK  {dest.name}")
            return True
        except (urllib.error.URLError, ValueError, OSError) as exc:
            last_err = exc
            print(f"  ! failed: {exc}")
            if dest.exists():
                dest.unlink()
            time.sleep(2 * attempt)
    print(f"  FATAL after {retries} attempts: {last_err}")
    return False


# --------------------------------------------------------------------------- #
# ENCODE
# --------------------------------------------------------------------------- #
def _encode_get(path: str) -> dict:
    url = f"{ENCODE_API}{path}"
    req = urllib.request.Request(
        url, headers={"User-Agent": "esc-aging-multiomics/1.0", "Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


def encode_file(accession: str, outdir: Path, retries: int) -> bool:
    obj = _encode_get(f"/files/{accession}/?format=json&frame=object")
    href = obj.get("href") or obj.get("cloud_metadata", {}).get("url")
    if not href:
        print(f"  no download href for {accession}")
        return False
    if href.startswith("/"):
        href = ENCODE_API + href
    md5 = obj.get("md5sum")
    size = obj.get("file_size")
    fname = obj.get("filename", accession)
    return verified_download(href, outdir / fname, md5, size, retries)


def encode_experiment(
    accession: str,
    outdir: Path,
    assembly: str | None,
    types: list[str] | None,
    retries: int,
) -> int:
    search = (
        f"/search/?type=File&dataset={accession}"
        f"&format=json&frame=object&limit=1000"
    )
    data = _encode_get(search)
    ok = 0
    for fobj in data.get("@{graph}", []):
        ftype = fobj.get("file_type", "")
        fasm = fobj.get("assembly", "")
        if assembly and fasm and fasm != assembly:
            continue
        if types and ftype not in types:
            continue
        href = fobj.get("href") or fobj.get("cloud_metadata", {}).get("url")
        if not href:
            continue
        if href.startswith("/"):
            href = ENCODE_API + href
        fname = fobj.get("filename", fobj.get("accession", "file"))
        if verified_download(
            href, outdir / fname, fobj.get("md5sum"), fobj.get("file_size"), retries
        ):
            ok += 1
    return ok


# --------------------------------------------------------------------------- #
# GEO
# --------------------------------------------------------------------------- #
def _ncbi_listing(html: str) -> list[str]:
    """Parse an NCBI FTP/HTTPS directory HTML listing for file links."""
    return re.findall(r'href="([^"?]+\.(?:gz|bed|txt|csv|tab|fastq|bw|bigWig|tar))"', html)


def geo_file(url: str, outdir: Path, retries: int) -> bool:
    fname = urllib.parse.unquote(url.rstrip("/").split("/")[-1])
    return verified_download(url, outdir / fname, expected_size=None, retries=retries)


def geo_series(accession: str, outdir: Path, retries: int) -> int:
    acc = accession.upper()
    gse = re.match(r"GSE\d+", acc)
    if not gse:
        print(f"  not a GSE accession: {accession}")
        return 0
    num = gse.group(0)
    # NCBI GEO series dir prefixes the accession with its first (len-3) chars: GSE208300 -> GSE208nnn
    prefix = num[:-3]
    suppl_url = f"https://ftp.ncbi.nlm.nih.gov/geo/series/{prefix}nnn/{num}/suppl/"
    print(f"  listing {suppl_url}")
    req = urllib.request.Request(suppl_url, headers={"User-Agent": "esc-aging-multiomics/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            html = resp.read().decode("utf-8", "replace")
    except urllib.error.URLError as exc:
        print(f"  could not list GSE suppl dir: {exc}")
        return 0
    files = _ncbi_listing(html)
    ok = 0
    for fname in files:
        url = suppl_url + fname
        if verified_download(url, outdir / fname, retries=retries):
            ok += 1
    return ok


# --------------------------------------------------------------------------- #
# Manifest
# --------------------------------------------------------------------------- #
def run_manifest(path: Path, retries: int) -> int:
    items = json.loads(path.read_text(encoding="utf-8"))
    ok = 0
    for item in items:
        source = item.get("source")
        out = Path(item.get("outdir", "."))
        out.mkdir(parents=True, exist_ok=True)
        md5 = item.get("md5")
        size = item.get("size")
        if source == "encode-file":
            # Re-verify if already present, else download.
            local = out / item.get("filename", item["id"])
            if local.exists() and md5 and md5_of(local).lower() == md5.lower():
                print(f"  verified (skip) {local.name}")
                ok += 1
                continue
            if encode_file(item["id"], out, retries):
                ok += 1
        elif source == "geo-file":
            if geo_file(item["url"], out, retries):
                ok += 1
        else:
            print(f"  unknown manifest source: {source}")
    return ok


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="ENCODE/GEO multi-omics downloader with integrity checks.")
    p.add_argument("command", choices=["encode-file", "encode-exp", "geo-file", "geo-series", "manifest"])
    p.add_argument("target", help="accession (ENCFF/ENCSR/GSE), URL, or manifest JSON path")
    p.add_argument("outdir", nargs="?", default="./data", help="output directory")
    p.add_argument("--assembly", help="ENCODE assembly filter (e.g. GRCh38)")
    p.add_argument("--types", help="ENCODE file_type filter, comma-separated (e.g. fastq,bigWig)")
    p.add_argument("--retries", type=int, default=DEFAULT_RETRIES)
    args = p.parse_args(argv)

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    if args.command == "encode-file":
        return 0 if encode_file(args.target, outdir, args.retries) else 1
    if args.command == "encode-exp":
        types = args.types.split(",") if args.types else None
        n = encode_experiment(args.target, outdir, args.assembly, types, args.retries)
        print(f"downloaded {n} file(s)")
        return 0 if n else 1
    if args.command == "geo-file":
        return 0 if geo_file(args.target, outdir, args.retries) else 1
    if args.command == "geo-series":
        n = geo_series(args.target, outdir, args.retries)
        print(f"downloaded {n} file(s)")
        return 0 if n else 1
    if args.command == "manifest":
        n = run_manifest(Path(args.target), args.retries)
        print(f"manifest: {n} item(s) ok")
        return 0 if n else 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
