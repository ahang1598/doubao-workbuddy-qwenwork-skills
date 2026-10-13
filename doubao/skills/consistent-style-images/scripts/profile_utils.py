#!/usr/bin/env python3
"""Load exactly one brand profile and fingerprint its local rules and task exceptions."""
import argparse
import copy
import hashlib
import json
from pathlib import Path

APPLIES = {"always", "text", "cta", "logo", "visual"}
BASE_REVIEW = {
    "content_accuracy": "always", "message_fit": "always", "copy_integrity": "text",
    "readability": "text", "visual_integrity": "always", "brand_consistency": "always",
    "asset_fidelity": "logo", "cta_integrity": "cta", "delivery": "always",
}
CONSTRAINT_KEYS = {
    "palette_options", "require_all_palette_colors", "max_text_levels", "allowed_alignments",
    "allowed_button_shapes", "cta_required", "unique_primary", "forbid_terminal_comma",
}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_profile(path, overrides=None):
    path = Path(path).resolve()
    profile = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(profile, dict) or not isinstance(profile.get("id"), str) or not profile["id"].strip():
        raise ValueError("brand profile needs a nonempty id")
    if profile.get("status") not in {"draft", "ready"}:
        raise ValueError("profile status must be draft or ready")
    rules = profile.get("review_rules", [])
    if not isinstance(rules, list):
        raise ValueError("review_rules must be a list")
    ids = set()
    for rule in rules:
        if not isinstance(rule, dict) or not isinstance(rule.get("id"), str) or not rule["id"] or rule["id"] in ids:
            raise ValueError("brand review rules need unique nonempty ids")
        if rule.get("applies_to") not in APPLIES or not isinstance(rule.get("criterion"), str) or not rule["criterion"].strip():
            raise ValueError("brand rule needs supported applies_to and criterion")
        ids.add(rule["id"])
    overrides = [] if overrides is None else overrides
    if not isinstance(overrides, list):
        raise ValueError("rule_overrides must be a list")
    effective = copy.deepcopy(profile)
    constraints = effective.setdefault("constraints", {})
    if not isinstance(constraints, dict) or set(constraints) - CONSTRAINT_KEYS:
        raise ValueError("unknown or malformed constraints")
    seen = set()
    for change in overrides:
        if not isinstance(change, dict) or any(not isinstance(change.get(k), str) or not change[k].strip() for k in ("path", "reason", "source")):
            raise ValueError("each override needs path, reason and actual user/project source")
        key = change["path"]
        if key in seen:
            raise ValueError("duplicate override path")
        seen.add(key)
        if key in CONSTRAINT_KEYS:
            if "value" not in change:
                raise ValueError("constraint override needs value")
            constraints[key] = change["value"]
        elif key not in ids:
            raise ValueError(f"unknown override {key}")
    for key in ("require_all_palette_colors", "cta_required", "unique_primary", "forbid_terminal_comma"):
        if key in constraints and type(constraints[key]) is not bool:
            raise ValueError(f"{key} must be boolean")
    maximum = constraints.get("max_text_levels")
    if maximum is not None and (type(maximum) is not int or maximum < 1):
        raise ValueError("max_text_levels must be null or positive integer")
    for key in ("allowed_alignments", "allowed_button_shapes"):
        value = constraints.get(key)
        if value is not None and (not isinstance(value, list) or not value or any(not isinstance(x, str) or not x for x in value)):
            raise ValueError(f"{key} must be null or nonempty string list")
    options = constraints.get("palette_options")
    if options is not None and (not isinstance(options, list) or not options or any(not isinstance(o, list) or not o or any(not isinstance(x, str) or not x for x in o) for o in options)):
        raise ValueError("palette_options must be null or lists of palette role names")
    references = profile.get("references", [])
    if not isinstance(references, list) or any(not isinstance(x, str) or not x for x in references):
        raise ValueError("references must be local path strings")
    evidence = {ref: sha256(path.parent / ref) for ref in references}
    serialized = json.dumps({"profile": profile, "references": evidence, "overrides": overrides}, sort_keys=True, ensure_ascii=False)
    fingerprint = hashlib.sha256(serialized.encode()).hexdigest()
    return effective, fingerprint


def asset_file(profile, profile_path, collection, key):
    item = profile.get(collection, {}).get(key)
    if not isinstance(item, dict) or not isinstance(item.get("file"), str) or not item["file"]:
        raise ValueError(f"missing {collection}.{key} file; no cross-brand fallback")
    path = (Path(profile_path).resolve().parent / item["file"]).resolve()
    digest = sha256(path)
    if item.get("sha256") and item["sha256"] != digest:
        raise ValueError(f"{collection}.{key} checksum mismatch")
    return path, digest, item


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", type=Path)
    parser.add_argument("--overrides", type=Path)
    args = parser.parse_args()
    try:
        changes = json.loads(args.overrides.read_text()) if args.overrides else []
        profile, fingerprint = load_profile(args.profile, changes)
        print(json.dumps({"brand_id": profile["id"], "profile_fingerprint": fingerprint}, ensure_ascii=False, indent=2))
    except Exception as exc:
        parser.exit(1, f"Profile error: {exc}\n")
