#!/usr/bin/env python3
"""Check brand-bound files and review records; never claim automated visual QA."""
import argparse
import hashlib
import json
from pathlib import Path
import unicodedata

from profile_utils import BASE_REVIEW, load_profile


def normalize(text):
    return "".join(c.lower() for c in unicodedata.normalize("NFKC", text)
                   if not c.isspace() and not unicodedata.category(c).startswith("P"))


def validate(manifest, plan_only=False):
    manifest = Path(manifest).resolve()
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("requires schema_version 1; migrate legacy manifests explicitly")
    if not isinstance(data.get("brand_profile"), str) or not data["brand_profile"]:
        raise ValueError("brand_profile is required; no default brand")
    profile, fingerprint = load_profile(manifest.parent / data["brand_profile"], data.get("rule_overrides", []))
    errors, warnings, outputs = [], [], []
    if data.get("brand_id") != profile["id"]:
        errors.append("brand_id differs from the selected profile")
    if data.get("profile_fingerprint") != fingerprint:
        errors.append("profile_fingerprint missing or stale; review current brand rules/overrides")
    if data.get("stage") not in {"concept", "final"}:
        errors.append("stage must be concept or final")
    if not plan_only and data.get("stage") == "final":
        brief = data.get("brief", {})
        if profile["status"] != "ready":
            errors.append("final deliverables require a ready brand profile")
        if not isinstance(brief, dict) or brief.get("copy_status") not in {"confirmed", "authorized_draft"} or brief.get("spec_status") != "confirmed" or not isinstance(brief.get("source"), str) or not brief["source"].strip():
            errors.append("final requires confirmed specifications and confirmed/user-authorized copy with source")
    jobs = data.get("jobs")
    if not isinstance(jobs, list) or not jobs:
        raise ValueError("jobs must be a nonempty list")
    if type(data.get("expected_count")) is not int or data["expected_count"] != len(jobs):
        errors.append("expected_count must match the job count")
    if not isinstance(data.get("style_lock"), dict) or not data["style_lock"]:
        errors.append("style_lock is required")
    ids, paths, pixels_seen = set(), set(), {}
    constraints = profile.get("constraints", {})
    if not plan_only:
        from PIL import Image

    def review_checks(record, requirements, flags, label):
        if not isinstance(record, dict):
            record = {}
        for key, applies in requirements.items():
            applicable = applies == "always" or flags.get(applies, False)
            item = record.get(key, {})
            expected = "passed" if applicable else "not_applicable"
            if not isinstance(item, dict) or item.get("status") != expected or not isinstance(item.get("evidence"), str) or not item["evidence"].strip():
                errors.append(f"{label}.{key} requires {expected} and concrete evidence/reason")
        for key, item in record.items():
            if key not in requirements and (not isinstance(item, dict) or item.get("status") in {"failed", "pending"}):
                errors.append(f"{label}.{key}: unresolved additional review")

    for index, job in enumerate(jobs):
        if not isinstance(job, dict):
            errors.append(f"job[{index}]: must be an object")
            continue
        jid = job.get("id")
        label = jid if isinstance(jid, str) else f"job[{index}]"
        if not isinstance(jid, str) or not jid.strip() or jid in ids:
            errors.append(f"{label}: missing/duplicate id")
        else:
            ids.add(jid)
        copy = job.get("copy")
        if not isinstance(copy, dict) or any(not isinstance(v, str) for v in copy.values()):
            errors.append(f"{label}: copy must be an object with string values, empty object allowed")
            copy = {}
        flags = job.get("content_flags", {})
        if not isinstance(flags, dict) or any(type(flags.get(k)) is not bool for k in ("text", "cta", "logo", "visual")):
            errors.append(f"{label}: content_flags needs text/cta/logo/visual booleans")
            flags = {}
        if flags.get("text") != any(v.strip() for v in copy.values()):
            errors.append(f"{label}: text flag contradicts recorded copy")
        if flags.get("cta") != bool(copy.get("cta", "").strip()):
            errors.append(f"{label}: CTA flag contradicts copy.cta")
        if constraints.get("cta_required") and not flags.get("cta"):
            errors.append(f"{label}: selected brand/task requires CTA")
        primary = copy.get("headline", "")
        repeated = bool(normalize(primary)) and normalize(primary) == normalize(copy.get("support", ""))
        lines = [normalize(line) for line in primary.splitlines() if normalize(line)]
        repeated = repeated or len(lines) != len(set(lines))
        if repeated:
            (errors if constraints.get("unique_primary") else warnings).append(f"{label}: repeated copy; verify intentional use and record evidence")
        if constraints.get("forbid_terminal_comma") and primary.rstrip().endswith((",", "，", "、")):
            errors.append(f"{label}: selected brand forbids unapproved terminal comma")
        dims = [job.get("width"), job.get("height")]
        if any(type(n) is not int or n <= 0 for n in dims):
            errors.append(f"{label}: dimensions must be positive integers")
        name = job.get("output")
        if not isinstance(name, str) or not name.strip():
            errors.append(f"{label}: output path required")
            continue
        path = (manifest.parent / name).resolve()
        if path in paths:
            errors.append(f"{label}: duplicate output path")
        paths.add(path)
        if job.get("status") not in {"planned", "generated", "passed", "failed"}:
            errors.append(f"{label}: invalid status")
        if plan_only:
            continue
        if job.get("status") != "passed":
            errors.append(f"{label}: not complete")
        review_checks(job.get("review"), BASE_REVIEW, flags, label + ".review")
        review_checks(job.get("brand_review"), {r["id"]: r["applies_to"] for r in profile.get("review_rules", [])}, flags, label + ".brand_review")
        if not isinstance(job.get("tool"), str) or not job["tool"].strip():
            errors.append(f"{label}: actual production tool(s) missing")
        if not path.is_file():
            errors.append(f"{label}: output missing")
            continue
        try:
            file_hash = hashlib.sha256(path.read_bytes()).hexdigest()
            if job.get("reviewed_sha256") != file_hash:
                errors.append(f"{label}: file changed or review hash missing; re-review")
            with Image.open(path) as im:
                im.verify()
            with Image.open(path) as im:
                im.load()
                size = list(im.size)
                digest = hashlib.sha256(str(size).encode() + im.convert("RGBA").tobytes()).hexdigest()
            if size != dims or job.get("actual_size") != size:
                errors.append(f"{label}: actual/requested/recorded dimensions differ")
            if digest in pixels_seen and job.get("allow_identical") is not True:
                errors.append(f"{label}: duplicate image content with {pixels_seen[digest]}")
            pixels_seen.setdefault(digest, label)
            outputs.append({"id": jid, "file": str(path), "size": size, "sha256": file_hash})
        except Exception as exc:
            errors.append(f"{label}: image check failed: {exc}")
    return {"ok": not errors, "mode": "plan" if plan_only else "files", "brand_id": profile["id"],
            "stage": data.get("stage"), "planned": len(jobs), "decoded": len(outputs),
            "errors": errors, "warnings": warnings, "outputs": outputs,
            "scope": "File/config/record checks only. No automated visual/semantic or authorization verification."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args()
    try:
        result = validate(args.manifest, args.plan_only)
    except Exception as exc:
        result = {"ok": False, "errors": [str(exc)]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["ok"] else 1)
