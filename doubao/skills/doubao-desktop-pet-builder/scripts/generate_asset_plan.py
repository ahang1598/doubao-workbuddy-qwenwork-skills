#!/usr/bin/env python3
"""Generate deterministic per-frame image prompts from a validated pet spec."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from validate_pet_spec import validate


PROHIBITED_ELEMENTS = [
    "human hands",
    "additional characters",
    "unconfirmed props",
    "text or lettering",
    "logos or watermarks",
    "decorative borders",
    "scenery or rooms",
    "ground or platform",
    "cast shadows or contact shadows",
    "glow or background color blocks",
]


def generation_style_directive(spec: dict) -> tuple[str, str]:
    character = spec["character"]
    subject_kind = spec["assetPipeline"]["subjectKind"]
    if subject_kind == "photo" and character["style"] != "preserve":
        return (
            "light-cartoon-sticker",
            "Use a lightly cartoonized desktop-pet sticker style. Preserve identity-defining face shape, "
            "markings, colors, body proportions, and signature accessories, but do not pursue photographic "
            "realism and do not render photorealistic action frames.",
        )
    if subject_kind == "photo" and character["style"] == "preserve":
        return (
            "explicit-realistic-preserve",
            "Preserve the confirmed core IP's realistic visual treatment because realistic rendering was "
            "explicitly selected; still isolate the complete subject like a clean desktop-pet sticker.",
        )
    return (
        "preserve-established-art-style",
        "Keep the character's established non-photographic art style and level of stylization unchanged.",
    )


def frame_phase(index: int, count: int) -> str:
    if index == 0:
        return "准备姿势；与母版保持同一身体尺度和脚底基线"
    if index == count - 1:
        return "回到基态；能够无跳变衔接 idle"
    ratio = index / max(1, count - 1)
    if ratio < 0.4:
        return "动作开始；只改变完成动作所需的局部姿态"
    if ratio < 0.7:
        return "主动作或反馈峰值；保持身份、镜头和身体比例"
    return "回弹或回位过渡；逐步恢复基态"


def build_plan(spec: dict) -> dict:
    character = spec["character"]
    style_policy, style_directive = generation_style_directive(spec)
    plan_states = []
    for state in spec["states"]:
        frames = []
        count = len(state["frames"])
        trigger_text = ", ".join(state["triggers"])
        sequence_prompt = (
            f"Reference the confirmed core IP image {character['coreAsset']}. "
            f"Create one coherent {count}-frame sequence for state {state['id']} triggered by {trigger_text}. "
            "Generate the whole state as one sequence with a fixed camera, body scale, head center, and foot baseline. "
            "Keep the same face, colors, material, body proportions, and signature accessories in every frame. "
            f"Show the complete body with clear source margin. {style_directive} "
            "Use real alpha when supported; otherwise place the subject on one solid flat background color that "
            "differs clearly from the character (background only, do not restyle the character) without a "
            "checkerboard, gradient, scenery, ground, or shadow. "
            f"Do not include: {', '.join(PROHIBITED_ELEMENTS)}."
        )
        for index, filename in enumerate(state["frames"]):
            phase = frame_phase(index, count)
            prompt = (
                f"Reference the confirmed core IP image {character['coreAsset']}. "
                f"Within the same generation request for state {state['id']}, render frame {index + 1}/{count}. "
                f"{phase}. Keep the same face, colors, material, body proportions, signature accessories, "
                "camera, head center, body scale, and foot baseline. Show the complete body centered with "
                f"generous clear source margin on all four sides. {style_directive} "
                "Use the same flat background as the other frames. "
                f"Do not include: {', '.join(PROHIBITED_ELEMENTS)}."
            )
            frames.append({
                "file": filename,
                "index": index + 1,
                "count": count,
                "phase": phase,
                "prompt": prompt,
            })
        plan_states.append({
            "id": state["id"],
            "triggers": state["triggers"],
            "frameDurationMs": state["frameDurationMs"],
            "generationMode": "single-state-sequence",
            "sequencePrompt": sequence_prompt,
            "frames": frames,
        })
    return {
        "schemaVersion": spec["schemaVersion"],
        "coreIp": character["coreAsset"],
        "character": {
            "name": character["displayName"],
            "kind": character["archetype"],
            "preserve": character["preserveTraits"],
            "style": character["style"],
            "generationStylePolicy": style_policy,
        },
        "generationOrder": [
            "confirm-core-ip",
            "pilot-idle-group",
            "process-and-qa-pilot",
            "generate-each-remaining-state-as-one-sequence",
            "retry-only-failed-state-frames",
        ],
        "prohibitedElements": PROHIBITED_ELEMENTS,
        "states": plan_states,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("spec", type=Path)
    parser.add_argument("--output", type=Path, default=Path("asset-plan.json"))
    args = parser.parse_args()
    try:
        spec = json.loads(args.spec.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Cannot read spec: {exc}", file=sys.stderr)
        return 2
    errors = validate(spec)
    if errors:
        print("Spec validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 2
    plan = build_plan(spec)
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
