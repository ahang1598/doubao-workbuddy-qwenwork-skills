"""Create thumbnail grids from PowerPoint presentation slides.

Creates a grid layout of slide thumbnails for quick visual analysis.
Labels each thumbnail with its XML filename (e.g., slide1.xml).
Hidden slides are shown with a placeholder pattern.

Usage:
    python contact_sheet.py input.pptx [output_prefix] [--cols N]
        [--tile-width PX] [--max-slides-per-grid N] [--slides LIST]

Examples:
    python contact_sheet.py presentation.pptx
    # Creates: thumbnails.jpg

    python contact_sheet.py template.pptx grid --cols 4
    # Creates: grid.jpg (or grid-1.jpg, grid-2.jpg for large decks)

    python contact_sheet.py presentation.pptx qa-overview --cols 3 \
        --tile-width 640 --max-slides-per-grid 6
    # Creates two readable 3x2 overview grids for a 12-slide deck.

    python contact_sheet.py presentation.pptx qa-detail --slides 1,5,7,8
    # Creates a grid containing only the selected slide positions.
"""

from __future__ import annotations

import argparse
import json
import posixpath
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import defusedxml.minidom
from defusedxml import ElementTree
from PIL import Image, ImageDraw, ImageFont

from _render_slides import render_pages_with_fallback
from _execution_route import BackendUnavailable
from oxml.kit import REL_SLIDE, resolve_part
from oxml.lo_bridge import launch_soffice


TILE_WIDTH = 300
RENDER_DPI = 100
MAX_COLS = 6
MIN_TILE_WIDTH = 160
MAX_TILE_WIDTH = 1200
DEFAULT_COLS = 3
JPEG_QUALITY = 95
PADDING = 20
BORDER_WIDTH = 2
FONT_SIZE_RATIO = 0.10
MAX_LABEL_FONT_SIZE = 36
LABEL_PADDING_RATIO = 0.4


def main():
    parser = argparse.ArgumentParser(
        description="Create thumbnail grids from PowerPoint slides."
    )
    parser.add_argument("input", help="Input PowerPoint file (.pptx)")
    parser.add_argument(
        "output_prefix",
        nargs="?",
        default="thumbnails",
        help="Output prefix for image files (default: thumbnails)",
    )
    parser.add_argument(
        "--cols",
        type=int,
        default=DEFAULT_COLS,
        help=f"Number of columns (default: {DEFAULT_COLS}, max: {MAX_COLS})",
    )
    parser.add_argument(
        "--tile-width",
        type=int,
        default=TILE_WIDTH,
        help=(
            f"Thumbnail width in pixels (default: {TILE_WIDTH}, "
            f"range: {MIN_TILE_WIDTH}-{MAX_TILE_WIDTH})"
        ),
    )
    parser.add_argument(
        "--max-slides-per-grid",
        type=int,
        default=None,
        help=(
            "Maximum slides per output grid. By default each grid uses "
            "cols * (cols + 1) slides."
        ),
    )
    parser.add_argument(
        "--slides",
        default=None,
        help="Comma-separated 1-based slide positions to include (for example: 1,5,7-9)",
    )

    args = parser.parse_args()

    cols = min(args.cols, MAX_COLS)
    if cols < 1:
        parser.error("--cols must be at least 1")
    if args.cols > MAX_COLS:
        print(f"Warning: Columns limited to {MAX_COLS}")
    if not MIN_TILE_WIDTH <= args.tile_width <= MAX_TILE_WIDTH:
        parser.error(
            f"--tile-width must be between {MIN_TILE_WIDTH} and {MAX_TILE_WIDTH}"
        )
    if args.max_slides_per_grid is not None and args.max_slides_per_grid < 1:
        parser.error("--max-slides-per-grid must be at least 1")
    try:
        selected_slides = parse_slide_selection(args.slides)
    except ValueError as exc:
        parser.error(str(exc))

    input_path = Path(args.input)
    if not input_path.exists() or input_path.suffix.lower() != ".pptx":
        print(f"Error: Invalid PowerPoint file: {args.input}", file=sys.stderr)
        sys.exit(1)

    output_path = Path(f"{args.output_prefix}.jpg")

    try:
        slide_info = read_slide_info(input_path)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            visible_count = sum(1 for info in slide_info if not info["hidden"])
            expected_page_counts = frozenset({visible_count, len(slide_info)})
            visible_images = render_pages(
                input_path, temp_path, expected_page_counts=expected_page_counts,
            )

            if not visible_images and not any(s["hidden"] for s in slide_info):
                print("Error: No slides found", file=sys.stderr)
                sys.exit(1)

            slides = assemble_slides(slide_info, visible_images, temp_path)
            slides = select_slides(slides, selected_slides)
            if not slides:
                parser.error("--slides did not select any slide")

            grid_files = build_grids(
                slides,
                cols,
                args.tile_width,
                output_path,
                max_slides_per_grid=args.max_slides_per_grid,
            )

            print(f"Created {len(grid_files)} grid(s):")
            for grid_file in grid_files:
                print(f"  {grid_file}")

    except BackendUnavailable as e:
        if e.code == "NO_EXECUTION_BACKEND_AVAILABLE":
            _emit_dependency_hint()
            sys.exit(3)
        print(f"Error: {e.code}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def parse_slide_selection(value: str | None) -> tuple[int, ...] | None:
    """Parse a compact 1-based slide selection while preserving caller order."""

    if value is None:
        return None
    selected: list[int] = []
    seen: set[int] = set()
    for token in value.split(","):
        token = token.strip()
        if not token:
            raise ValueError("--slides contains an empty item")
        if "-" in token:
            start_text, end_text = token.split("-", 1)
            if not start_text.isdigit() or not end_text.isdigit():
                raise ValueError("--slides accepts only positive positions and ranges")
            start, end = int(start_text), int(end_text)
            if start < 1 or end < start:
                raise ValueError("--slides ranges must be positive and ascending")
            values = range(start, end + 1)
        else:
            if not token.isdigit() or int(token) < 1:
                raise ValueError("--slides accepts only positive positions and ranges")
            values = (int(token),)
        for item in values:
            if item not in seen:
                selected.append(item)
                seen.add(item)
    return tuple(selected)


def select_slides(
    slides: list[tuple[Path, str]], selected: tuple[int, ...] | None,
) -> list[tuple[Path, str]]:
    """Select 1-based slide positions after rendering keeps labels stable."""

    if selected is None:
        return slides
    missing = [position for position in selected if position > len(slides)]
    if missing:
        raise ValueError(
            "selected slide position(s) exceed the deck length: "
            + ", ".join(str(position) for position in missing)
        )
    return [slides[position - 1] for position in selected]


def _emit_dependency_hint() -> None:
    missing = [tool for tool in ("soffice", "pdftoppm") if shutil.which(tool) is None]
    install = {
        "soffice": {
            "macos": "brew install --cask libreoffice",
            "debian": "apt-get install -y libreoffice",
        },
        "pdftoppm": {
            "macos": "brew install poppler",
            "debian": "apt-get install -y poppler-utils",
        },
    }
    print(
        json.dumps(
            {
                "ok": False,
                "reason": "missing_dependencies",
                "missing": missing,
                "install": {name: install[name] for name in missing},
                "recovery": (
                    "Cloud rendering is unavailable. Install only these fixed "
                    "dependencies in the task/workspace when rendering is required, "
                    "then retry."
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def _slide_hidden(zf: zipfile.ZipFile, part: str) -> bool:
    try:
        with zf.open(part) as f:
            for _, root in ElementTree.iterparse(f, events=("start",)):
                return root.get("show") in ("0", "false")
    except (KeyError, ElementTree.ParseError):
        return False
    return False


def read_slide_info(pptx_path: Path) -> list[dict]:
    with zipfile.ZipFile(pptx_path, "r") as zf:
        rels_content = zf.read("ppt/_rels/presentation.xml.rels").decode("utf-8")
        rels_dom = defusedxml.minidom.parseString(rels_content)

        rid_to_part = {}
        for rel in rels_dom.getElementsByTagName("Relationship"):
            if rel.getAttribute("Type") != REL_SLIDE:
                continue
            part = resolve_part(
                rel.getAttribute("Target"),
                "ppt/presentation.xml",
                rel.getAttribute("TargetMode"),
            )
            if part is not None:
                rid_to_part[rel.getAttribute("Id")] = part

        pres_content = zf.read("ppt/presentation.xml").decode("utf-8")
        pres_dom = defusedxml.minidom.parseString(pres_content)

        present = set(zf.namelist())

        slides = []
        for sld_id in pres_dom.getElementsByTagName("p:sldId"):
            part = rid_to_part.get(sld_id.getAttribute("r:id"))
            if part is not None and part in present:
                slides.append(
                    {"name": posixpath.basename(part), "hidden": _slide_hidden(zf, part)}
                )

        return slides


def assemble_slides(
    slide_info: list[dict],
    visible_images: list[Path],
    temp_dir: Path,
) -> list[tuple[Path, str]]:
    visible_count = sum(1 for info in slide_info if not info["hidden"])
    rendered_hidden = len(visible_images) == len(slide_info) != visible_count

    if not rendered_hidden and visible_count != len(visible_images):
        raise ValueError(
            f"renderer produced {len(visible_images)} page(s) for {visible_count} "
            f"visible slide(s) of {len(slide_info)}; thumbnails would be mislabeled"
        )

    if visible_images:
        with Image.open(visible_images[0]) as img:
            placeholder_size = img.size
    else:
        placeholder_size = (1920, 1080)

    slides = []
    visible_idx = 0

    for info in slide_info:
        if info["hidden"] and not rendered_hidden:
            placeholder_path = temp_dir / f"hidden-{info['name']}.jpg"
            placeholder_img = make_hidden_tile(placeholder_size)
            placeholder_img.save(placeholder_path, "JPEG")
            slides.append((placeholder_path, f"{info['name']} (hidden)"))
        else:
            label = f"{info['name']} (hidden)" if info["hidden"] else info["name"]
            slides.append((visible_images[visible_idx], label))
            visible_idx += 1

    return slides


def make_hidden_tile(size: tuple[int, int]) -> Image.Image:
    img = Image.new("RGB", size, color="#F0F0F0")
    draw = ImageDraw.Draw(img)
    line_width = max(5, min(size) // 100)
    draw.line([(0, 0), size], fill="#CCCCCC", width=line_width)
    draw.line([(size[0], 0), (0, size[1])], fill="#CCCCCC", width=line_width)
    return img


def _render_pages_local(pptx_path: Path, temp_dir: Path) -> list[Path]:
    pdf_path = temp_dir / f"{pptx_path.stem}.pdf"

    result = launch_soffice(
        ["--headless", "--convert-to", "pdf", "--outdir", str(temp_dir), str(pptx_path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not pdf_path.exists():
        detail = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(f"PDF conversion failed: {detail}" if detail else "PDF conversion failed")

    result = subprocess.run(
        [
            "pdftoppm",
            "-jpeg",
            "-r",
            str(RENDER_DPI),
            str(pdf_path),
            str(temp_dir / "slide"),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError("Image conversion failed")

    return sorted(temp_dir.glob("slide-*.jpg"))


def render_pages(
    pptx_path: Path,
    temp_dir: Path,
    *,
    expected_page_counts: frozenset[int] | None = None,
) -> list[Path]:
    """Render through cloud capabilities first, then the unchanged local path."""

    return render_pages_with_fallback(
        pptx_path,
        temp_dir,
        dpi=RENDER_DPI,
        local_renderer=_render_pages_local,
        expected_page_counts=expected_page_counts,
    )


def build_grids(
    slides: list[tuple[Path, str]],
    cols: int,
    width: int,
    output_path: Path,
    *,
    max_slides_per_grid: int | None = None,
) -> list[str]:
    max_per_grid = max_slides_per_grid or cols * (cols + 1)
    grid_files = []

    for chunk_idx, start_idx in enumerate(range(0, len(slides), max_per_grid)):
        end_idx = min(start_idx + max_per_grid, len(slides))
        chunk_slides = slides[start_idx:end_idx]

        grid = build_grid(chunk_slides, cols, width)

        if len(slides) <= max_per_grid:
            grid_filename = output_path
        else:
            stem = output_path.stem
            suffix = output_path.suffix
            grid_filename = output_path.parent / f"{stem}-{chunk_idx + 1}{suffix}"

        grid_filename.parent.mkdir(parents=True, exist_ok=True)
        grid.save(str(grid_filename), quality=JPEG_QUALITY)
        grid_files.append(str(grid_filename))

    return grid_files


def build_grid(
    slides: list[tuple[Path, str]],
    cols: int,
    width: int,
) -> Image.Image:
    font_size = min(int(width * FONT_SIZE_RATIO), MAX_LABEL_FONT_SIZE)
    label_padding = int(font_size * LABEL_PADDING_RATIO)

    with Image.open(slides[0][0]) as img:
        aspect = img.height / img.width
    height = int(width * aspect)

    rows = (len(slides) + cols - 1) // cols
    grid_w = cols * width + (cols + 1) * PADDING
    grid_h = rows * (height + font_size + label_padding * 2) + (rows + 1) * PADDING

    grid = Image.new("RGB", (grid_w, grid_h), "white")
    draw = ImageDraw.Draw(grid)

    try:
        font = ImageFont.load_default(size=font_size)
    except Exception:
        font = ImageFont.load_default()

    for i, (img_path, slide_name) in enumerate(slides):
        row, col = i // cols, i % cols
        x = col * width + (col + 1) * PADDING
        y_base = (
            row * (height + font_size + label_padding * 2) + (row + 1) * PADDING
        )

        label = slide_name
        bbox = draw.textbbox((0, 0), label, font=font)
        text_w = bbox[2] - bbox[0]
        draw.text(
            (x + (width - text_w) // 2, y_base + label_padding),
            label,
            fill="black",
            font=font,
        )

        y_thumbnail = y_base + label_padding + font_size + label_padding

        with Image.open(img_path) as img:
            img.thumbnail((width, height), Image.Resampling.LANCZOS)
            w, h = img.size
            tx = x + (width - w) // 2
            ty = y_thumbnail + (height - h) // 2
            grid.paste(img, (tx, ty))

            if BORDER_WIDTH > 0:
                draw.rectangle(
                    [
                        (tx - BORDER_WIDTH, ty - BORDER_WIDTH),
                        (tx + w + BORDER_WIDTH - 1, ty + h + BORDER_WIDTH - 1),
                    ],
                    outline="gray",
                    width=BORDER_WIDTH,
                )

    return grid


if __name__ == "__main__":
    main()
