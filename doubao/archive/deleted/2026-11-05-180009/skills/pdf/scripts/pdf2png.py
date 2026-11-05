import argparse
import math
from pathlib import Path

import pymupdf as fitz


PAGES_PER_IMAGE = 2
PAGE_GAP = 12
PAGE_LABEL_HEIGHT = 18
PAGE_LABEL_INSET = 4
PAGE_LABEL_FONT_SIZE = 7
PAGE_BACKGROUND = (0.84, 0.84, 0.84)
PAGE_COLOR = (1, 1, 1)
PAGE_SHADOW = (0.72, 0.72, 0.72)
PAGE_SHADOW_OFFSET = 1.5


def grid_size(page_count):
    columns = math.ceil(math.sqrt(page_count))
    rows = math.ceil(page_count / columns)
    return columns, rows


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


def merged_page_pixmap(document, page_numbers, dpi):
    page_numbers = list(page_numbers)
    page_rects = [document[index].rect for index in page_numbers]
    cell_width = max(rect.width for rect in page_rects)
    cell_height = max(rect.height for rect in page_rects)
    columns, rows = grid_size(len(page_numbers))
    width = columns * cell_width + (columns + 1) * PAGE_GAP
    cell_height_with_label = PAGE_LABEL_HEIGHT + cell_height
    height = rows * cell_height_with_label + (rows + 1) * PAGE_GAP

    merged = fitz.open()
    page = merged.new_page(width=width, height=height)
    page.draw_rect(page.rect, fill=PAGE_BACKGROUND, color=None)
    for position, page_number in enumerate(page_numbers):
        row, column = divmod(position, columns)
        source_rect = page_rects[position]
        cell_x = PAGE_GAP + column * (cell_width + PAGE_GAP)
        cell_y = PAGE_GAP + row * (cell_height_with_label + PAGE_GAP)
        x0 = cell_x + (cell_width - source_rect.width) / 2
        y0 = cell_y + PAGE_LABEL_HEIGHT + (cell_height - source_rect.height) / 2
        page_rect = fitz.Rect(
            x0,
            y0,
            x0 + source_rect.width,
            y0 + source_rect.height,
        )
        shadow_rect = fitz.Rect(
            page_rect.x0 + PAGE_SHADOW_OFFSET,
            page_rect.y0 + PAGE_SHADOW_OFFSET,
            page_rect.x1 + PAGE_SHADOW_OFFSET,
            page_rect.y1 + PAGE_SHADOW_OFFSET,
        )
        page.draw_rect(shadow_rect, fill=PAGE_SHADOW, color=None)
        page.draw_rect(page_rect, fill=PAGE_COLOR, color=None)
        page.insert_text(
            (x0 + PAGE_LABEL_INSET, cell_y + PAGE_LABEL_FONT_SIZE),
            f"page-{page_number + 1}",
            fontsize=PAGE_LABEL_FONT_SIZE,
            color=(0, 0, 0),
        )
        page.show_pdf_page(page_rect, document, page_number)

    pixmap = page.get_pixmap(dpi=dpi, alpha=False)
    merged.close()
    return pixmap


def png_name(start, end):
    if start == end:
        return f"page-{start:03d}.png"
    return f"page-{start:03d}-{end:03d}.png"


def pdf_to_png(pdf, output_dir, dpi, pages=None):
    output_dir.mkdir(parents=True, exist_ok=True)
    document = fitz.open(pdf)
    page_numbers = parse_pages(pages, len(document))
    output_files = []
    for start in range(0, len(page_numbers), PAGES_PER_IMAGE):
        group = page_numbers[start : start + PAGES_PER_IMAGE]
        page_indices = [page_number - 1 for page_number in group]
        if len(page_indices) == 1:
            pixmap = document[page_indices[0]].get_pixmap(
                dpi=dpi,
                alpha=False,
            )
        else:
            pixmap = merged_page_pixmap(document, page_indices, dpi)
        output_file = output_dir / png_name(group[0], group[-1])
        pixmap.save(output_file)
        output_files.append(output_file)
    document.close()
    return len(page_numbers), output_files


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf")
    parser.add_argument("--output", required=True)
    parser.add_argument("--pages", help="One-based pages, for example 1,3-5")
    parser.add_argument("--dpi", type=int, default=200)
    args = parser.parse_args()

    pdf = Path(args.pdf).resolve()
    output_dir = Path(args.output).resolve()
    page_count, output_files = pdf_to_png(
        pdf,
        output_dir,
        args.dpi,
        args.pages,
    )
    print(
        f"Wrote {len(output_files)} PNG files for {page_count} pages "
        f"to {output_dir}"
    )
    for output_file in output_files:
        print(output_file.name)


if __name__ == "__main__":
    main()
