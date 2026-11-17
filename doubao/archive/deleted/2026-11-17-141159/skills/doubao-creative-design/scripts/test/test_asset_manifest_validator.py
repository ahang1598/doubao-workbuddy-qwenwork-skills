#!/usr/bin/env python3
"""Exercise the lightweight AI + Coding asset manifest validator."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runtime"))
from validate_asset_manifest import validate


def fixture() -> dict:
    return {
        "brief_snapshot": {"path": "brief.md", "version": "v1", "status": "frozen"},
        "assets": [{
            "asset_id": "hero",
            "purpose": "首屏主视觉",
            "production_method": "image_edit",
            "reference_inputs": ["core-product-v1"],
            "identity_source": "core-product-v1；保持包装轮廓、Logo 和标签",
            "prompt": "保持商品身份并重建场景",
            "target": {"ratio": "4:3", "width": 1600, "height": 1200, "safe_area": "商品完整可见"},
            "consumers": ["首屏主视觉"],
            "acceptance": ["身份一致"],
            "status": "planned",
        }],
        "unresolved_blockers": [],
    }


def main() -> int:
    for field, code in (("production_method", "ASSET_MANIFEST_METHOD"), ("status", "ASSET_MANIFEST_STATUS")):
        for value in ([], {}, None, 1, False, "unknown"):
            malformed = fixture()
            malformed["assets"][0][field] = value
            errors = validate(malformed)
            assert any(code in error and field in error for error in errors), (field, value, errors)
    planned = fixture()
    assert not validate(planned)
    assert any("ASSET_MANIFEST_READY" in item for item in validate(planned, True))
    ready = deepcopy(planned)
    ready["assets"][0].update(status="ready", output={
        "uri": "https://example.invalid/hero.png", "width": 1600, "height": 1200,
        "version": "v1", "alpha": False,
    })
    assert not validate(ready, True)
    local_output = deepcopy(ready)
    local_output["assets"][0]["output"]["uri"] = "assets/hero.png"
    assert any("ASSET_MANIFEST_OUTPUT" in item for item in validate(local_output, True))
    data_output = deepcopy(ready)
    data_output["assets"][0]["output"]["uri"] = "data:image/png;base64,AAAA"
    assert any("ASSET_MANIFEST_OUTPUT" in item for item in validate(data_output, True))
    ratio_mismatch = fixture()
    ratio_mismatch["assets"][0]["target"].update(width=1600, height=900)
    assert any("ASSET_MANIFEST_RATIO" in item for item in validate(ratio_mismatch))
    missing_reference = fixture()
    missing_reference["assets"][0]["reference_inputs"] = []
    assert any("ASSET_MANIFEST_REFERENCE" in item for item in validate(missing_reference))
    missing_target = fixture()
    missing_target["assets"][0]["target"]["safe_area"] = ""
    assert any("ASSET_MANIFEST_TARGET" in item for item in validate(missing_target))
    missing_identity = fixture()
    missing_identity["assets"][0]["identity_source"] = ""
    assert any("ASSET_MANIFEST_IDENTITY" in item for item in validate(missing_identity))
    implementation_projection = fixture()
    implementation_projection["assets"][0]["geometry"] = {"x": 0, "y": 0}
    assert any("ASSET_MANIFEST_FIELDS" in item for item in validate(implementation_projection))
    print("Asset manifest fixtures: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
