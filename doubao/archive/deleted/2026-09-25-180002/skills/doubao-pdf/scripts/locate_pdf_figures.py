"""Locate and crop figures from a PDF."""

from __future__ import annotations

import argparse
import json
import re
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

import pymupdf
from PIL import Image, ImageChops, ImageDraw, ImageFilter


CAPTION_RE = re.compile(
    r"^\s*(?:figure|fig\.?|table|图|表)\s*[0-9A-Za-z一二三四五六七八九十]",
    re.IGNORECASE,
)


def box_area(box):
    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])


def box_union(boxes):
    return [
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    ]


def box_intersection_area(left, right):
    width = max(0.0, min(left[2], right[2]) - max(left[0], right[0]))
    height = max(0.0, min(left[3], right[3]) - max(left[1], right[1]))
    return width * height


def box_coverage(outer, inner):
    inner_area = box_area(inner)
    return box_intersection_area(outer, inner) / inner_area if inner_area else 0.0


def box_clip(box, width, height):
    return [
        max(0.0, min(width, box[0])),
        max(0.0, min(height, box[1])),
        max(0.0, min(width, box[2])),
        max(0.0, min(height, box[3])),
    ]


def boxes_close(left, right, gap):
    return not (
        left[2] + gap < right[0]
        or right[2] + gap < left[0]
        or left[3] + gap < right[1]
        or right[3] + gap < left[1]
    )


def mapped_box(rect, matrix, page_width, page_height):
    mapped = pymupdf.Rect(rect) * matrix
    return box_clip(
        [mapped.x0, mapped.y0, mapped.x1, mapped.y1],
        page_width,
        page_height,
    )


def cluster_items(items, gap, group_gap=None):
    parents = list(range(len(items)))

    def root(index):
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    def join(left, right):
        left_root = root(left)
        right_root = root(right)
        if left_root != right_root:
            parents[right_root] = left_root

    order = sorted(range(len(items)), key=lambda index: items[index]["bbox"][0])
    for position, left_index in enumerate(order):
        left = items[left_index]["bbox"]
        for right_index in order[position + 1 :]:
            right = items[right_index]["bbox"]
            if right[0] > left[2] + gap:
                break
            if boxes_close(left, right, gap):
                join(left_index, right_index)

    groups = {}
    for index, item in enumerate(items):
        groups.setdefault(root(index), []).append(item)
    groups = list(groups.values())
    if group_gap is None:
        return groups

    while True:
        for left_index, left_group in enumerate(groups):
            left_box = box_union([item["bbox"] for item in left_group])
            for right_index in range(left_index + 1, len(groups)):
                right_box = box_union(
                    [item["bbox"] for item in groups[right_index]]
                )
                if boxes_close(left_box, right_box, group_gap):
                    left_group.extend(groups.pop(right_index))
                    break
            else:
                continue
            break
        else:
            return groups


def parse_pages(value, page_count):
    if not value:
        return list(range(1, page_count + 1))
    pages = set()
    for part in value.split(","):
        if "-" in part:
            start, end = (int(number) for number in part.split("-", 1))
            pages.update(range(start, end + 1))
        else:
            pages.add(int(part))
    return sorted(pages)


def parse_adjustments(values):
    adjustments = {}
    for value in values:
        candidate_id, left, top, right, bottom = value.split(",")
        adjustments[candidate_id.upper()] = [
            float(left),
            float(top),
            float(right),
            float(bottom),
        ]
    return adjustments


def collect_text_spans(page, page_width, page_height):
    matrix = page.rotation_matrix
    spans = []
    for block in page.get_text("dict")["blocks"]:
        if block["type"] != 0:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                text = span["text"].strip()
                if not text:
                    continue
                spans.append(
                    {
                        "bbox": mapped_box(
                            span["bbox"],
                            matrix,
                            page_width,
                            page_height,
                        ),
                        "text": text,
                        "size": float(span["size"]),
                        "caption_like": bool(CAPTION_RE.match(text)),
                    }
                )
    return spans


def collect_seed_atoms(page, page_width, page_height, min_ratio, max_ratio):
    matrix = page.rotation_matrix
    page_area = page_width * page_height
    atoms = []
    has_full_page_image = False

    for info in page.get_image_info(xrefs=True):
        bbox = mapped_box(info["bbox"], matrix, page_width, page_height)
        ratio = box_area(bbox) / page_area
        if ratio >= max_ratio:
            has_full_page_image = True
        elif ratio >= min_ratio:
            atoms.append({"kind": "image", "bbox": bbox})

    for drawing in page.get_drawings(extended=True):
        if "rect" not in drawing:
            continue
        bbox = mapped_box(drawing["rect"], matrix, page_width, page_height)
        stroke = max(0.5, float(drawing.get("width") or 0.5)) / 2
        bbox = box_clip(
            [
                bbox[0] - stroke,
                bbox[1] - stroke,
                bbox[2] + stroke,
                bbox[3] + stroke,
            ],
            page_width,
            page_height,
        )
        ratio = box_area(bbox) / page_area
        if ratio < max_ratio and max(bbox[2] - bbox[0], bbox[3] - bbox[1]) >= 2:
            atoms.append(
                {
                    "kind": "vector",
                    "bbox": bbox,
                }
            )

    return atoms, has_full_page_image


def structured_candidates(
    atoms,
    page_width,
    page_height,
    gap,
    adaptive_gap,
    min_ratio,
    max_ratio,
):
    page_area = page_width * page_height
    candidates = []
    for group in cluster_items(atoms, gap, adaptive_gap):
        bbox = box_union([item["bbox"] for item in group])
        ratio = box_area(bbox) / page_area
        image_count = sum(item["kind"] == "image" for item in group)
        vector_count = sum(item["kind"] == "vector" for item in group)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        useful_vector = vector_count >= 2 or ratio >= min_ratio * 2
        if (
            min_ratio <= ratio < max_ratio
            and min(width, height) >= 6
            and (image_count or useful_vector)
        ):
            candidates.append(
                {
                    "kind": "structured",
                    "bbox": bbox,
                }
            )
    return candidates


def foreground_mask(image):
    gray = image.convert("L")
    width, height = gray.size
    step = max(1, min(width, height) // 200)
    samples = []
    for x in range(0, width, step):
        samples.extend((gray.getpixel((x, 0)), gray.getpixel((x, height - 1))))
    for y in range(0, height, step):
        samples.extend((gray.getpixel((0, y)), gray.getpixel((width - 1, y))))
    background = int(median(samples))
    difference = ImageChops.difference(
        gray,
        Image.new("L", gray.size, color=background),
    )
    contrast = difference.point(lambda value: 255 if value >= 18 else 0)
    edges = gray.filter(ImageFilter.FIND_EDGES).point(
        lambda value: 255 if value >= 24 else 0
    )
    mask = ImageChops.lighter(contrast, edges)
    ImageDraw.Draw(mask).rectangle(
        (0, 0, width - 1, height - 1),
        outline=0,
        width=2,
    )
    return mask


def connected_components(mask):
    work = mask.copy()
    work.thumbnail((600, 900), Image.Resampling.LANCZOS)
    work = work.point(lambda value: 255 if value >= 64 else 0)
    work = work.filter(ImageFilter.MaxFilter(9))
    width, height = work.size
    pixels = work.tobytes()
    visited = bytearray(width * height)
    components = []

    for start in range(width * height):
        if visited[start] or pixels[start] == 0:
            continue
        visited[start] = 1
        queue = deque((start,))
        left = right = start % width
        top = bottom = start // width
        count = 0
        while queue:
            index = queue.popleft()
            x = index % width
            y = index // width
            left = min(left, x)
            right = max(right, x)
            top = min(top, y)
            bottom = max(bottom, y)
            count += 1
            neighbors = []
            if x:
                neighbors.append(index - 1)
            if x + 1 < width:
                neighbors.append(index + 1)
            if y:
                neighbors.append(index - width)
            if y + 1 < height:
                neighbors.append(index + width)
            for neighbor in neighbors:
                if not visited[neighbor] and pixels[neighbor]:
                    visited[neighbor] = 1
                    queue.append(neighbor)
        if count >= 20:
            components.append([left, top, right + 1, bottom + 1])
    return components, width, height


def raster_candidates(mask, page_width, page_height, existing):
    components, width, height = connected_components(mask)
    page_area = page_width * page_height
    regions = []
    for component in components:
        bbox = [
            component[0] * page_width / width,
            component[1] * page_height / height,
            component[2] * page_width / width,
            component[3] * page_height / height,
        ]
        ratio = box_area(bbox) / page_area
        if (
            0.0015 <= ratio <= 0.8
            and bbox[2] - bbox[0] >= page_width * 0.05
            and bbox[3] - bbox[1] >= page_height * 0.025
        ):
            regions.append({"bbox": bbox, "kind": "raster"})

    grouped = cluster_items(regions, 5)
    boxes = [box_union([item["bbox"] for item in group]) for group in grouped]
    boxes.sort(key=box_area, reverse=True)
    candidates = []
    for bbox in boxes:
        duplicate = any(
            box_intersection_area(bbox, candidate["bbox"])
            / min(box_area(bbox), box_area(candidate["bbox"]))
            >= 0.65
            for candidate in existing
        )
        if not duplicate:
            candidates.append(
                {
                    "kind": "raster",
                    "bbox": bbox,
                }
            )
        if len(candidates) == 12:
            break
    return candidates


def overlap_fraction_on_short_axis(left, right, horizontal):
    if horizontal:
        overlap = max(0.0, min(left[2], right[2]) - max(left[0], right[0]))
        return overlap / max(1.0, min(left[2] - left[0], right[2] - right[0]))
    overlap = max(0.0, min(left[3], right[3]) - max(left[1], right[1]))
    return overlap / max(1.0, min(left[3] - left[1], right[3] - right[1]))


def attach_text(candidate, spans, label_gap, body_font_size):
    bbox = candidate["bbox"]
    selected = []
    for span in spans:
        text_box = span["bbox"]
        inside = box_coverage(bbox, text_box) >= 0.65
        vertical_gap = max(bbox[1] - text_box[3], text_box[1] - bbox[3], 0.0)
        horizontal_gap = max(bbox[0] - text_box[2], text_box[0] - bbox[2], 0.0)
        near_vertical = (
            vertical_gap <= label_gap
            and overlap_fraction_on_short_axis(bbox, text_box, True) >= 0.25
        )
        near_horizontal = (
            horizontal_gap <= label_gap
            and overlap_fraction_on_short_axis(bbox, text_box, False) >= 0.25
        )
        short_label = (
            len(span["text"]) <= 120
            and span["size"] <= max(14.0, body_font_size * 1.5)
            and not span["caption_like"]
        )
        if inside or (short_label and (near_vertical or near_horizontal)):
            selected.append(span)

    if candidate["kind"] == "raster":
        return bbox
    if selected:
        bbox = box_union([bbox] + [span["bbox"] for span in selected])
    return bbox


def blank_distance(values, run_length, threshold):
    run = 0
    for index, value in enumerate(values):
        if value <= threshold:
            run += 1
            if run >= run_length:
                return index - run_length // 2 + 1
        else:
            run = 0
    return None


def projected_values(region, vertical, reverse=False):
    if not region.width or not region.height:
        return []
    size = (1, region.height) if vertical else (region.width, 1)
    values = list(region.resize(size, Image.Resampling.BOX).getdata())
    return values[::-1] if reverse else values


def snap_to_whitespace(
    bbox,
    mask,
    page_width,
    page_height,
    padding,
    max_search,
    blank_run,
    blank_ratio,
):
    width, height = mask.size
    x_scale = width / page_width
    y_scale = height / page_height
    left = max(0, min(width, int(bbox[0] * x_scale)))
    top = max(0, min(height, int(bbox[1] * y_scale)))
    right = max(0, min(width, int(bbox[2] * x_scale + 1)))
    bottom = max(0, min(height, int(bbox[3] * y_scale + 1)))
    pad_x = max(1, int(padding * x_scale))
    pad_y = max(1, int(padding * y_scale))
    search_x = max(pad_x, int(max_search * x_scale))
    search_y = max(pad_y, int(max_search * y_scale))
    threshold = int(255 * blank_ratio)
    band_left = max(0, left - pad_x)
    band_right = min(width, right + pad_x)
    band_top = max(0, top - pad_y)
    band_bottom = min(height, bottom + pad_y)

    top_region = mask.crop((band_left, max(0, top - search_y), band_right, top))
    top_values = projected_values(top_region, True, reverse=True)
    top_distance = blank_distance(top_values, blank_run, threshold)

    bottom_region = mask.crop(
        (band_left, bottom, band_right, min(height, bottom + search_y))
    )
    bottom_values = projected_values(bottom_region, True)
    bottom_distance = blank_distance(bottom_values, blank_run, threshold)

    left_region = mask.crop((max(0, left - search_x), band_top, left, band_bottom))
    left_values = projected_values(left_region, False, reverse=True)
    left_distance = blank_distance(left_values, blank_run, threshold)

    right_region = mask.crop(
        (right, band_top, min(width, right + search_x), band_bottom)
    )
    right_values = projected_values(right_region, False)
    right_distance = blank_distance(right_values, blank_run, threshold)

    left -= max(pad_x, left_distance or 0)
    top -= max(pad_y, top_distance or 0)
    right += max(pad_x, right_distance or 0)
    bottom += max(pad_y, bottom_distance or 0)
    return box_clip(
        [left / x_scale, top / y_scale, right / x_scale, bottom / y_scale],
        page_width,
        page_height,
    )


def apply_adjustment(bbox, adjustment, page_width, page_height):
    left, top, right, bottom = adjustment
    return box_clip(
        [
            bbox[0] - left,
            bbox[1] - top,
            bbox[2] + right,
            bbox[3] + bottom,
        ],
        page_width,
        page_height,
    )


def process_page(page, page_number, run_root, args, adjustments):
    page_width = float(page.rect.width)
    page_height = float(page.rect.height)
    matrix = pymupdf.Matrix(args.dpi / 72, args.dpi / 72)
    pixmap = page.get_pixmap(
        matrix=matrix,
        colorspace=pymupdf.csRGB,
        alpha=False,
    )
    image = Image.frombytes(
        "RGB",
        (pixmap.width, pixmap.height),
        pixmap.samples,
    )
    mask = foreground_mask(image)

    spans = collect_text_spans(page, page_width, page_height)
    body_font_size = median([span["size"] for span in spans]) if spans else 10.0
    atoms, has_full_page_image = collect_seed_atoms(
        page,
        page_width,
        page_height,
        args.min_area_ratio,
        args.max_area_ratio,
    )
    raw_candidates = structured_candidates(
        atoms,
        page_width,
        page_height,
        args.merge_gap_pt,
        args.adaptive_merge_gap_pt,
        args.min_area_ratio,
        args.max_area_ratio,
    )
    if has_full_page_image:
        raw_candidates.extend(
            raster_candidates(
                mask,
                page_width,
                page_height,
                raw_candidates,
            )
        )
    crop_boxes = []
    for candidate in raw_candidates:
        tight_bbox = attach_text(
            candidate,
            spans,
            args.label_gap_pt,
            body_font_size,
        )
        bbox = snap_to_whitespace(
            tight_bbox,
            mask,
            page_width,
            page_height,
            args.padding_pt,
            args.max_search_pt,
            args.blank_run_px,
            args.blank_ratio,
        )
        crop_boxes.append(bbox)
    crop_boxes.sort(key=lambda bbox: (bbox[1], bbox[0]))

    for index, bbox in enumerate(crop_boxes, start=1):
        image_id = f"page-{page_number:04d}-image-{index:02d}"
        adjustment = adjustments.get(
            image_id.upper(),
            [0.0, 0.0, 0.0, 0.0],
        )
        bbox = apply_adjustment(
            bbox,
            adjustment,
            page_width,
            page_height,
        )
        crop_path = run_root / f"{image_id}.png"
        crop = page.get_pixmap(
            matrix=matrix,
            clip=pymupdf.Rect(bbox),
            alpha=False,
        )
        crop.save(str(crop_path))
    return len(crop_boxes)


def main():
    parser = argparse.ArgumentParser(
        description="Locate PDF figures and save cropped images."
    )
    parser.add_argument("input_pdf")
    parser.add_argument("--output", dest="output_dir", required=True)
    parser.add_argument("--pages", help="One-based pages, for example 1,3-5")
    parser.add_argument("--run-id")
    parser.add_argument("--dpi", type=int, default=216)
    parser.add_argument("--merge-gap-pt", type=float, default=10.0)
    parser.add_argument(
        "--adaptive-merge-gap-pt",
        type=float,
        help="Second-pass gap for merging nearby vector groups.",
    )
    parser.add_argument("--label-gap-pt", type=float, default=12.0)
    parser.add_argument("--padding-pt", type=float, default=4.0)
    parser.add_argument("--max-search-pt", type=float, default=24.0)
    parser.add_argument("--min-area-ratio", type=float, default=0.0005)
    parser.add_argument("--max-area-ratio", type=float, default=0.85)
    parser.add_argument("--blank-run-px", type=int, default=10)
    parser.add_argument("--blank-ratio", type=float, default=0.004)
    parser.add_argument(
        "--adjust",
        action="append",
        default=[],
        metavar="PAGE-0001-IMAGE-01,LEFT,TOP,RIGHT,BOTTOM",
        help="Positive values expand a side; negative values contract it.",
    )
    args = parser.parse_args()

    run_id = args.run_id or datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%S%fZ"
    )
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    run_root = output_dir / run_id
    run_root.mkdir()

    adjustments = parse_adjustments(args.adjust)
    input_pdf = Path(args.input_pdf).resolve()
    with pymupdf.open(input_pdf) as document:
        pages = parse_pages(args.pages, document.page_count)
        image_count = sum(
            process_page(
                document[page_number - 1],
                page_number,
                run_root,
                args,
                adjustments,
            )
            for page_number in pages
        )

    print(
        json.dumps(
            {
                "ok": True,
                "output_dir": str(run_root),
                "images": image_count,
            }
        )
    )


if __name__ == "__main__":
    main()
