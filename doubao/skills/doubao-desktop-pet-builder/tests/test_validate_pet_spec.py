from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_pet_spec import validate  # noqa: E402


class ValidatePetSpecTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.spec = json.loads((ROOT / "assets/electron-template/pet-spec.json").read_text(encoding="utf-8"))

    def test_template_spec_is_valid(self) -> None:
        self.assertEqual(validate(copy.deepcopy(self.spec)), [])

    def test_visible_action_requires_enough_frames(self) -> None:
        broken = copy.deepcopy(self.spec)
        broken["states"][2]["frames"] = broken["states"][2]["frames"][:3]
        errors = validate(broken)
        self.assertTrue(any("happy must have 5-6 frames" in error for error in errors), errors)

    def test_interaction_must_point_to_a_real_state(self) -> None:
        broken = copy.deepcopy(self.spec)
        broken["experience"]["interactions"][0]["stateId"] = "missing"
        errors = validate(broken)
        self.assertTrue(any("unknown interaction state" in error for error in errors), errors)

    def test_schema_rejects_missing_required_structure(self) -> None:
        broken = copy.deepcopy(self.spec)
        del broken["assetPipeline"]["backgroundMode"]
        errors = validate(broken)
        self.assertTrue(any("$.assetPipeline.backgroundMode: is required by schema" in error for error in errors), errors)

    def test_core_asset_must_not_be_a_runtime_frame(self) -> None:
        broken = copy.deepcopy(self.spec)
        broken["character"]["coreAsset"] = broken["states"][0]["frames"][0]
        errors = validate(broken)
        self.assertTrue(any("independent identity master" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
