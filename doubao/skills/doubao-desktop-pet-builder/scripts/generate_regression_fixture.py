#!/usr/bin/env python3
"""Generate a deterministic, dependency-free PNG fixture for scaffold regression tests."""

from __future__ import annotations

import binascii
import json
import math
import struct
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "assets" / "electron-template" / "pet-spec.json"
OUTPUT = ROOT / "assets" / "regression-fixture" / "synthetic-pet"
WIDTH = 512
HEIGHT = 512


def chunk(kind: bytes, payload: bytes) -> bytes:
    body = kind + payload
    return struct.pack(">I", len(payload)) + body + struct.pack(">I", binascii.crc32(body) & 0xFFFFFFFF)


def inside_ellipse(x: int, y: int, center_x: float, center_y: float, radius_x: float, radius_y: float) -> bool:
    return ((x - center_x) / radius_x) ** 2 + ((y - center_y) / radius_y) ** 2 <= 1


def frame_pixels(state: str, index: int) -> bytes:
    pixels = bytearray(WIDTH * HEIGHT * 4)
    phase = index * 0.8 + sum(ord(char) for char in state) * 0.03
    body_center_x = 256
    bottom = 486
    body_center_y = 326 + round(math.sin(phase) * 2)
    body_radius_x = 132
    body_radius_y = bottom - body_center_y
    head_center_y = 205 + round(math.sin(phase + 0.4) * 2)
    head_radius_x = 116
    head_radius_y = 105
    tail_side = -1 if state == "peek" else 1
    tail_center_x = 256 + tail_side * (130 + round(math.sin(phase) * 7))
    tail_center_y = 348 + round(math.cos(phase) * 5)
    eye_height = 14
    if state == "blink":
        eye_height = [14, 8, 3, 8, 14][index]

    for y in range(HEIGHT):
        for x in range(WIDTH):
            color: tuple[int, int, int, int] | None = None
            if inside_ellipse(x, y, tail_center_x, tail_center_y, 48, 112):
                color = (221, 111, 39, 255)
            if inside_ellipse(x, y, body_center_x, body_center_y, body_radius_x, body_radius_y):
                color = (181, 77, 24, 255) if x < body_center_x else (255, 184, 78, 255)
            if inside_ellipse(x, y, head_center_y * 0 + body_center_x, head_center_y, head_radius_x, head_radius_y):
                color = (244, 151, 62, 255)
            if inside_ellipse(x, y, 190, 127, 43, 61) or inside_ellipse(x, y, 322, 127, 43, 61):
                color = (235, 133, 52, 255)
            if inside_ellipse(x, y, 190, 139, 22, 33) or inside_ellipse(x, y, 322, 139, 22, 33):
                color = (255, 199, 176, 255)
            if inside_ellipse(x, y, 216, 202, 14, eye_height) or inside_ellipse(x, y, 296, 202, 14, eye_height):
                color = (63, 44, 37, 255)
            if inside_ellipse(x, y, 256, 232, 11, 8):
                color = (126, 70, 59, 255)

            if state == "happy" and inside_ellipse(x, y, 256, 253, 27 + index, 13):
                color = (112, 45, 45, 255)
            elif state == "notify" and inside_ellipse(x, y, 350, 116 + index * 2, 24, 24):
                color = (255, 214, 55, 255)
            elif state == "pet" and inside_ellipse(x, y, 256 + (index - 2) * 7, 92, 31, 24):
                color = (255, 105, 147, 255)
            elif state == "eat" and inside_ellipse(x, y, 256 + (index - 2) * 4, 275, 31, 17):
                color = (87, 161, 203, 255)
            elif state == "play" and inside_ellipse(x, y, 365 - index * 7, 245 + index * 4, 18, 46):
                color = (107, 192, 114, 255)
            elif state == "peek" and inside_ellipse(x, y, 390 + index * 2, 310, 25, 120):
                color = (137, 102, 81, 255)

            if color is not None:
                offset = (y * WIDTH + x) * 4
                pixels[offset : offset + 4] = bytes(color)
    return bytes(pixels)


def write_png(path: Path, rgba: bytes) -> None:
    scanlines = b"".join(
        b"\x00" + rgba[y * WIDTH * 4 : (y + 1) * WIDTH * 4]
        for y in range(HEIGHT)
    )
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", WIDTH, HEIGHT, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(scanlines, level=9))
        + chunk(b"IEND", b"")
    )
    path.write_bytes(png)


def main() -> int:
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    OUTPUT.mkdir(parents=True, exist_ok=True)
    generated: list[dict[str, object]] = []
    core_target = OUTPUT / spec["character"]["coreAsset"]
    core_target.parent.mkdir(parents=True, exist_ok=True)
    write_png(core_target, frame_pixels("idle", 0))
    generated.append({"state": "core-ip", "frame": spec["character"]["coreAsset"], "bytes": core_target.stat().st_size})
    for state in spec["states"]:
        for index, name in enumerate(state["frames"]):
            target = OUTPUT / name
            write_png(target, frame_pixels(state["id"], index))
            generated.append({"state": state["id"], "frame": name, "bytes": target.stat().st_size})

    manifest = {
        "schemaVersion": 1,
        "source": "deterministic synthetic regression fixture; not for user delivery",
        "specSchemaVersion": spec["schemaVersion"],
        "frameCount": len(generated),
        "frames": generated,
    }
    (OUTPUT / "fixture-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Generated {len(generated)} regression frames in {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
