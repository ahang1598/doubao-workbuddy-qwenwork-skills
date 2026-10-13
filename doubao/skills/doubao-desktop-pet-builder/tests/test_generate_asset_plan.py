from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_asset_plan.py"
SPEC = ROOT / "assets" / "electron-template" / "pet-spec.json"


class GenerateAssetPlanTest(unittest.TestCase):
    def test_plan_covers_every_frame_and_carries_negative_constraints(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "asset-plan.json"
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(SPEC), "--output", str(output)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            plan = json.loads(output.read_text(encoding="utf-8"))
            spec = json.loads(SPEC.read_text(encoding="utf-8"))
            planned_frames = [frame["file"] for state in plan["states"] for frame in state["frames"]]
            expected_frames = [frame for state in spec["states"] for frame in state["frames"]]
            self.assertEqual(planned_frames, expected_frames)
            self.assertIn("human hands", plan["prohibitedElements"])
            self.assertTrue(all("generous clear source margin" in frame["prompt"] for state in plan["states"] for frame in state["frames"]))
            self.assertTrue(all(state["generationMode"] == "single-state-sequence" for state in plan["states"]))
            self.assertTrue(all("one coherent" in state["sequencePrompt"] for state in plan["states"]))
            self.assertEqual(plan["generationOrder"][1], "pilot-idle-group")

    def test_photo_reference_defaults_to_light_cartoon_unless_realism_is_explicit(self) -> None:
        base_spec = json.loads(SPEC.read_text(encoding="utf-8"))
        base_spec["assetPipeline"]["subjectKind"] = "photo"
        with tempfile.TemporaryDirectory() as directory:
            directory_path = Path(directory)
            spec_path = directory_path / "pet-spec.json"
            output = directory_path / "asset-plan.json"

            base_spec["character"]["style"] = "balanced-cartoon"
            spec_path.write_text(json.dumps(base_spec, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(spec_path), "--output", str(output)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            plan = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(plan["character"]["generationStylePolicy"], "light-cartoon-sticker")
            self.assertTrue(all(
                "lightly cartoonized desktop-pet sticker style" in state["sequencePrompt"]
                for state in plan["states"]
            ))
            self.assertTrue(all(
                "do not render photorealistic action frames" in frame["prompt"]
                for state in plan["states"]
                for frame in state["frames"]
            ))

            base_spec["character"]["style"] = "preserve"
            spec_path.write_text(json.dumps(base_spec, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(spec_path), "--output", str(output)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            plan = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(plan["character"]["generationStylePolicy"], "explicit-realistic-preserve")
            self.assertTrue(all(
                "realistic rendering was explicitly selected" in state["sequencePrompt"]
                for state in plan["states"]
            ))


if __name__ == "__main__":
    unittest.main()
