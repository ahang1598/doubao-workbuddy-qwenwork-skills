#!/usr/bin/env python3
"""Restore numbered scene frames through an isolated, atomic staging directory."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, BinaryIO, Callable
from urllib.request import urlopen


OpenUrl = Callable[[str], BinaryIO]
_MINIMUM_IMAGE_BYTES = 64


def _download_frames(
    frames: list[Any],
    staging_directory: Path,
    open_url: OpenUrl,
) -> None:
    for index, raw_frame in enumerate(frames, start=1):
        if not isinstance(raw_frame, dict) or raw_frame.get("n") != index:
            raise ValueError(f"frame {index} is invalid")
        if raw_frame.get("output_slot") != f"frame-{index:03d}":
            raise ValueError(f"frame {index} output_slot is invalid")
        frame_url = raw_frame.get("frame_url")
        if not isinstance(frame_url, str) or not frame_url.startswith(("http://", "https://")):
            raise ValueError(f"frame {index}.frame_url is required")
        destination = staging_directory / f"frame{index:03d}.png"
        with open_url(frame_url) as response, destination.open("wb") as output:
            shutil.copyfileobj(response, output)
            output.flush()
            os.fsync(output.fileno())
        if destination.stat().st_size < _MINIMUM_IMAGE_BYTES:
            raise ValueError(f"frame {index} download is empty or truncated")


def materialize_scene_frames(
    manifest: dict[str, Any],
    frames_directory: Path,
    open_url: OpenUrl = urlopen,
) -> int:
    frames = manifest.get("frames")
    if manifest.get("manifest_version") != 2 or not isinstance(frames, list) or not frames:
        raise ValueError("scene manifest must contain manifest_version 2 frames")

    frames_directory.parent.mkdir(parents=True, exist_ok=True)
    staging_directory = Path(
        tempfile.mkdtemp(
            prefix=f".{frames_directory.name}.staging-",
            dir=frames_directory.parent,
        )
    )
    backup_directory = frames_directory.with_name(f".{frames_directory.name}.backup")
    if backup_directory.exists():
        raise ValueError(f"stale recovery backup exists: {backup_directory}")
    moved_existing = False
    try:
        _download_frames(frames, staging_directory, open_url)
        if frames_directory.exists():
            frames_directory.replace(backup_directory)
            moved_existing = True
        staging_directory.replace(frames_directory)
        if moved_existing:
            shutil.rmtree(backup_directory)
        return len(frames)
    except Exception:
        if staging_directory.exists():
            shutil.rmtree(staging_directory)
        if moved_existing and backup_directory.exists() and not frames_directory.exists():
            backup_directory.replace(frames_directory)
        raise


def _main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--frames-dir", required=True, type=Path)
    arguments = parser.parse_args()
    manifest = json.loads(arguments.manifest.read_text(encoding="utf-8"))
    count = materialize_scene_frames(manifest, arguments.frames_dir)
    print(json.dumps({"valid": True, "frames": count}))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
