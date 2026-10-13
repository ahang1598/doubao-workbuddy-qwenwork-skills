#!/usr/bin/env python3
"""
Convert a slide JSON array into a PPTX by emitting temporary SVG files.
"""

import argparse
import json
import shutil
import tempfile
from pathlib import Path

from embed_svg_to_pptx import embed_svgs


def _extract_json_text(raw_text: str) -> str:
    text = raw_text.strip()
    if "```" not in text:
        return text

    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end < start:
        raise ValueError("could not find JSON array inside fenced block")
    return text[start : end + 1]


def _load_slides(json_path: Path) -> list[dict]:
    raw_text = json_path.read_text(encoding="utf-8")
    slides = json.loads(_extract_json_text(raw_text))
    if not isinstance(slides, list) or not slides:
        raise ValueError("slides JSON must be a non-empty array")

    for index, slide in enumerate(slides, start=1):
        if not isinstance(slide, dict):
            raise ValueError(f"slide {index} is not an object")
        title = slide.get("title")
        svg = slide.get("svg")
        if not isinstance(title, str) or not title.strip():
            raise ValueError(f"slide {index} is missing a non-empty title")
        if not isinstance(svg, str) or not svg.strip():
            raise ValueError(f"slide {index} is missing a non-empty svg")

    return slides


def _write_svgs(slides: list[dict], svg_dir: Path) -> list[Path]:
    svg_dir.mkdir(parents=True, exist_ok=True)
    svg_paths: list[Path] = []

    for index, slide in enumerate(slides, start=1):
        svg_path = svg_dir / f"slide_{index:03d}.svg"
        svg_path.write_text(slide["svg"], encoding="utf-8")
        svg_paths.append(svg_path)

    return svg_paths


def convert(json_path: Path, output_path: Path, write_svg_dir: Path | None = None) -> None:
    slides = _load_slides(json_path)

    with tempfile.TemporaryDirectory() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        generated_svg_dir = tmp_dir / "svgs"
        svg_paths = _write_svgs(slides, generated_svg_dir)
        embed_svgs(svg_paths, output_path)

        if write_svg_dir is not None:
            write_svg_dir.mkdir(parents=True, exist_ok=True)
            for svg_path in svg_paths:
                shutil.copyfile(svg_path, write_svg_dir / svg_path.name)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a PPTX from a JSON array of {title, svg} slide objects.",
    )
    parser.add_argument("slides_json", type=Path, help="Path to the JSON array file")
    parser.add_argument("-o", "--output", type=Path, default=Path("output.pptx"))
    parser.add_argument(
        "--write-svg-dir",
        type=Path,
        help="Optional output directory for exported intermediate SVG files",
    )
    args = parser.parse_args()

    convert(args.slides_json, args.output, args.write_svg_dir)


if __name__ == "__main__":
    main()
