#!/usr/bin/env python3
"""Routed requests may continue with the appropriate shipped skill."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_ROUTES = {
    "company-analysis-09": "investment-opportunity-screening",
    "company-analysis-10": "event-impact-analysis",
}


def main():
    cases = [
        case
        for case in json.loads((ROOT / "evals/evals.json").read_text(encoding="utf-8"))
        if case["id"] in EXPECTED_ROUTES
    ]
    assert len(cases) == len(EXPECTED_ROUTES)

    with tempfile.TemporaryDirectory() as directory:
        temp = Path(directory)
        responses = temp / "responses"
        responses.mkdir()
        evals = temp / "evals.json"
        evals.write_text(json.dumps(cases, ensure_ascii=False), encoding="utf-8")

        for case in cases:
            route = EXPECTED_ROUTES[case["id"]]
            assert {"type": "route_to", "value": route} in case["assertions"]
            (responses / f'{case["id"]}.json').write_text(
                json.dumps(
                    {"route": route, "text": "已转交相应能力继续处理。" + "分析内容。" * 200},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/eval_harness.py"),
                str(evals),
                "--responses-dir",
                str(responses),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr

    print("PASS routed requests continue without length or refusal gates")


if __name__ == "__main__":
    main()
