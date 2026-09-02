import argparse
import json
import re
from pathlib import Path

import pdfplumber


# Garbage patterns that produce non-readable output when a PDF is scanned /
# uses unembedded fonts / has encoding issues.  This list covers the most
# common failure modes; new patterns can be added here without changing the
# scoring logic below.
_GARBAGE_PATTERNS: list[str] = [
    r'\(cid:\d+\)',             # Missing Unicode mapping  → (cid:12345)
    r'[\ue000-\uf8ff]',         # Private Use Area glyphs (custom font chars)
    r'\ufffd',                  # Unicode replacement character
    r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]',  # Non-printable control chars
]
_GARBAGE_RE = re.compile('|'.join(_GARBAGE_PATTERNS))

# Characters considered genuinely readable in any document language.
# Covers: CJK (Chinese/Japanese/Korean), Latin, digits, common punctuation.
_READABLE_RE = re.compile(
    r'['
    r'\u4e00-\u9fff'    # CJK Unified Ideographs
    r'\u3400-\u4dbf'    # CJK Extension A
    r'\uf900-\ufaff'    # CJK Compatibility Ideographs
    r'\u3040-\u30ff'    # Hiragana / Katakana
    r'\uac00-\ud7af'    # Hangul
    r'A-Za-z'           # Latin letters
    r'0-9'              # Digits
    r'\u00c0-\u024f'    # Latin Extended A/B (accented letters)
    r'\u0400-\u04ff'    # Cyrillic
    r'\u3000-\u303f'    # CJK Symbols & Punctuation (，。、etc.)
    r'\u2010-\u2027'    # Dashes, quotes, bullets
    r'\u2030-\u205f'    # General typographic punctuation
    r'!\-.,;:\'"@#%&*+=|~`_<>()\[\]{}/?\\^$'  # ASCII punctuation
    r']'
)


def _content_quality(text: str) -> float:
    """Return a readability score 0.0–1.0 for PDF-extracted page text.

    0.0 = pure garbage (scanned image, missing font maps, encoding errors, …)
    1.0 = clean, fully readable text

    Strategy
    --------
    1. Strip all known garbage character patterns.
    2. Measure *survival ratio*: what fraction of the original non-whitespace
       content remained after garbage removal.  A low ratio means most of the
       apparent 'content' was actually noise.
    3. Within the surviving text, measure *readability ratio*: what fraction
       of characters are actual word/punctuation chars (CJK, Latin, digits,
       common punctuation).  This catches punctuation-soup or symbol garbage
       that survives step 1.
    4. Final score = survival_ratio × readability_ratio.

    Using two multiplicative factors means either type of corruption alone
    is enough to produce a near-zero score.
    """
    original_non_ws = re.sub(r'\s+', '', text)
    if not original_non_ws:
        return 0.0

    cleaned_non_ws = re.sub(r'\s+', '', _GARBAGE_RE.sub('', text))

    survival_ratio = len(cleaned_non_ws) / len(original_non_ws)
    if not cleaned_non_ws:
        return 0.0

    readable_chars = len(_READABLE_RE.findall(cleaned_non_ws))
    readability_ratio = readable_chars / len(cleaned_non_ws)

    return survival_ratio * readability_ratio



def parse_pages(page_spec: str | None, total_pages: int) -> list[int]:
    if not page_spec:
        return list(range(1, total_pages + 1))

    pages: set[int] = set()
    for segment in page_spec.split(','):
        part = segment.strip()
        if not part:
            continue
        if '-' in part:
            start_text, end_text = part.split('-', 1)
            start = int(start_text)
            end = int(end_text)
            if start > end:
                raise ValueError(f'Invalid page range: {part}')
            pages.update(range(start, end + 1))
        else:
            pages.add(int(part))

    invalid_pages = [page for page in pages if page < 1 or page > total_pages]
    if invalid_pages:
        raise ValueError(f'Page numbers out of range: {sorted(invalid_pages)}')

    return sorted(pages)


def extract_text(input_pdf: str, output_txt: str, page_spec: str | None, preserve_layout: bool) -> dict:
    with pdfplumber.open(input_pdf) as pdf:
        selected_pages = parse_pages(page_spec, len(pdf.pages))
        chunks: list[str] = []
        empty_pages: list[int] = []

        corrupted_pages: list[int] = []

        for page_number in selected_pages:
            page = pdf.pages[page_number - 1]
            text = page.extract_text(layout=preserve_layout) or ''
            if not text.strip():
                empty_pages.append(page_number)
            elif _content_quality(text) < 0.5:
                # Has content but quality score is too low to be usable.
                # (cid tokens, private-use glyphs, encoding noise, etc.)
                corrupted_pages.append(page_number)
            chunks.append(text.rstrip())

    Path(output_txt).write_text('\n\n'.join(chunks) + '\n', encoding='utf-8')

    total_chars = sum(len(c.strip()) for c in chunks)
    bad_pages = empty_pages + corrupted_pages
    if len(bad_pages) == len(selected_pages):
        status = 'empty'
    elif bad_pages:
        status = 'partial'
    else:
        status = 'success'

    next_action = 'fadada-scanned-ocr' if status in ('empty', 'partial') else None

    return {
        'status': status,
        'next_action': next_action,
        'total_pages': len(selected_pages),
        'extracted_chars': total_chars,
        'empty_pages': empty_pages,
        'corrupted_pages': corrupted_pages,
        'output_file': output_txt,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description='Extract text from a PDF using Python.')
    parser.add_argument('input_pdf', help='Path to the input PDF')
    parser.add_argument('output_txt', help='Path to the output text file')
    parser.add_argument(
        '--pages',
        help='Comma-separated page numbers or ranges, e.g. "1-3,5,8-10"',
    )
    parser.add_argument(
        '--layout',
        action='store_true',
        help='Preserve layout as much as pdfplumber allows',
    )
    args = parser.parse_args()

    result = extract_text(
        input_pdf=args.input_pdf,
        output_txt=args.output_txt,
        page_spec=args.pages,
        preserve_layout=args.layout,
    )
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
