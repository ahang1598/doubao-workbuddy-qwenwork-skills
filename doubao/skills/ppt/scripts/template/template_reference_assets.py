#!/usr/bin/env python3
"""Extract original embedded raster payloads from an immutable PDF reference.

API: extract_pdf_assets(pdf_path, output_dir, pages=None, min_edge=256).
Pages are one-based. Payloads returned by PyMuPDF.extract_image are written
unchanged; JPEG streams remain original JPEG bytes. PDF soft masks are separate
original payloads. Actual paint occurrences are counted once; image digests
identify resource candidates, not exact xref bindings. Ambiguous masks are never
applied to previews, which then show the raw base payload explicitly.

This inventory is separate from the text-free visual-style schema. It extracts
no PDF text or metadata and does not determine whether an image is a background,
contains baked text, or suits the new topic. Those decisions need visual review.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys


def _selected_pages(page_count, pages):
    if pages is None:
        return list(range(1, page_count + 1))
    if isinstance(pages, (str, bytes)):
        raise ValueError('pages must be a non-empty sequence of one-based integers')
    try:
        selected = list(pages)
    except TypeError as exc:
        raise ValueError('pages must be a sequence of one-based integers') from exc
    if not selected or any(isinstance(n, bool) or not isinstance(n, int) or
                           n < 1 or n > page_count for n in selected):
        raise ValueError('page selection is empty or outside the PDF page range')
    return sorted(set(selected))


def _page_spec(value):
    selected = []
    for token in value.split(','):
        match = re.fullmatch(r'\s*(\d+)(?:\s*-\s*(\d+))?\s*', token)
        if not match:
            raise ValueError('pages must use comma-separated numbers or ranges, such as 1,4-6')
        start, end = int(match.group(1)), int(match.group(2) or match.group(1))
        if start < 1 or end < start:
            raise ValueError('page ranges must be positive and ascending')
        selected.extend(range(start, end + 1))
    return sorted(set(selected))


def _write_payload(directory, prefix, payload, extension):
    digest = hashlib.sha256(payload).hexdigest()
    if not re.fullmatch(r'[A-Za-z0-9]+', extension):
        raise ValueError('unsupported image extension returned by PDF extractor')
    path = directory / ('%s-%s.%s' % (prefix, digest, extension))
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError('existing asset path contains different bytes: %s' % path)
    else:
        path.write_bytes(payload)
    return path, digest


def _overview(assets, masks, output_dir):
    """Small selection previews only; original image files are not re-encoded."""
    from PIL import Image, ImageDraw
    mask_paths = {xref: mask['path'] for mask in masks for xref in mask['xrefs']}
    paths, errors, items = [], [], []
    for start in range(0, len(assets), 24):
        subset = assets[start:start + 24]
        rows = math.ceil(len(subset) / 4)
        canvas = Image.new('RGB', (4 * 324 + 12, rows * 224 + 12), '#E7EAEE')
        draw = ImageDraw.Draw(canvas)
        for offset, asset in enumerate(subset):
            x, y = 12 + (offset % 4) * 324, 12 + (offset // 4) * 224
            uses = asset['uses'] or asset['candidate_uses']
            use = uses[0] if uses else {'mask_association': 'unavailable', 'soft_mask_xref': None}
            mask_association = use['mask_association']
            mask_applied = False
            try:
                image = Image.open(asset['path']).convert('RGBA')
                # Only a consistent candidate mask is usable. A digest alone
                # cannot choose between distinct masks on identical images.
                mask_xref = use['soft_mask_xref']
                if mask_xref and mask_association == 'consistent_candidates':
                    mask = Image.open(mask_paths[mask_xref]).convert('L')
                    if mask.size != image.size:
                        mask = mask.resize(image.size)
                    image.putalpha(mask)
                    mask_applied = True
                image.thumbnail((312, 180))
                tile = Image.new('RGBA', (312, 180), 'white')
                tile.alpha_composite(image, ((312 - image.width) // 2,
                                             (180 - image.height) // 2))
                canvas.paste(tile.convert('RGB'), (x, y))
            except (OSError, ValueError, KeyError) as exc:
                errors.append({'asset_id': asset['asset_id'], 'error': str(exc)})
                draw.rectangle((x, y, x + 312, y + 180), fill='#D1D6DD')
                draw.text((x + 8, y + 75), 'Preview unavailable; inspect original', fill='black')
            pages = ','.join(str(n) for n in sorted({u['page'] for u in uses}))
            label = '%s | %sx%s %s | p%s' % (asset['sha256'][:10], asset['width'],
                                            asset['height'], asset['ext'], pages)
            draw.text((x, y + 187), label, fill='#25282D')
            note = ('Mask unresolved: raw base only' if mask_association in
                    ('ambiguous', 'unavailable') else 'Visual role / baked text: inspect image')
            draw.text((x, y + 204), note, fill='#555A63')
            items.append({'asset_id': asset['asset_id'], 'mask_association': mask_association,
                          'soft_mask_applied': mask_applied, 'preview_note': note})
        path = output_dir / ('assets-overview-%d.jpg' % (start // 24 + 1))
        canvas.save(path, quality=88)
        paths.append(str(path))
    return {'paths': paths, 'items': items, 'preview_errors': errors,
            'basis': 'original payload previews; only consistent candidate masks are composited'}


def extract_pdf_assets(pdf_path, output_dir, pages=None, min_edge=256):
    """Export deduplicated original raster payloads and their actual page uses.

    ``min_edge`` filters on the smaller original pixel dimension, not displayed
    geometry. Zero includes small assets. Bboxes use PyMuPDF's unrotated page
    coordinates, in points; page rotation is recorded for consumers.
    """
    if isinstance(min_edge, bool) or not isinstance(min_edge, int) or min_edge < 0:
        raise ValueError('min_edge must be a non-negative integer')
    try:
        import fitz
    except ImportError as exc:
        raise ValueError('PDF raster extraction needs existing PyMuPDF; nothing is installed automatically') from exc
    source_path = Path(pdf_path).resolve()
    source_bytes = source_path.read_bytes()
    output = Path(output_dir).resolve()
    result = {'schema_version': 1, 'reference_type': 'pdf_raster_assets',
              'source_pdf': {'path': str(source_path),
                             'sha256': hashlib.sha256(source_bytes).hexdigest()},
              'coordinate_unit': 'pt', 'coordinate_space': 'unrotated_page',
              'min_edge': min_edge, 'assets': [], 'soft_masks': [], 'pages': [],
              'unresolved_occurrences': [],
              'limitations': ['embedded_rasters_only_not_vector_backgrounds',
                              'original_payloads_are_extract_image_bytes_not_page_renders',
                              'digests_identify_resource_candidates_not_exact_xref_bindings',
                              'soft_masks_are_separate_ambiguous_associations_are_not_applied',
                              'large_bbox_coverage_is_only_geometry_not_background_classification',
                              'occurrence_bbox_does_not_prove_visibility_or_z_order',
                              'text_baked_into_images_is_unknown_requires_visual_review',
                              'semantic_suitability_requires_visual_selection',
                              'no_pdf_text_or_metadata_enters_this_inventory']}
    by_sha, mask_by_sha, extracted, pixel_keys, pixel_alpha = {}, {}, {}, {}, {}
    painted_count = 0
    with fitz.open(stream=source_bytes, filetype='pdf') as document:
        if document.needs_pass:
            raise ValueError('encrypted PDF references are not supported')
        selected = _selected_pages(len(document), pages)
        result['source_pdf']['page_count'] = len(document)
        result['selected_pages'] = selected
        output.mkdir(parents=True, exist_ok=True)
        for number in selected:
            page = document[number - 1]
            width, height = page.cropbox.width, page.cropbox.height
            result['pages'].append({'page': number, 'width_pt': round(width, 3),
                                    'height_pt': round(height, 3), 'rotation': page.rotation})
            # This API reports each actual image paint once, unlike the
            # content-hash matching returned by get_image_rects(xref).
            paints = [p for p in page.get_image_info(hashes=True)
                      if min(p['width'], p['height']) >= min_edge]
            active_keys = {(p['digest'], p['width'], p['height']) for p in paints}
            resources = {}
            seen = set()
            for reference in page.get_images(full=True):
                xref, soft_mask_xref = reference[0], reference[1]
                if xref in seen:
                    continue
                seen.add(xref)
                if xref not in extracted:
                    extracted[xref] = document.extract_image(xref)
                info = extracted[xref]
                if not info or min(info['width'], info['height']) < min_edge:
                    continue
                if xref not in pixel_keys:
                    pixmap = fitz.Pixmap(document, xref)
                    pixel_keys[xref] = (pixmap.digest, info['width'], info['height'])
                    pixel_alpha[xref] = bool(pixmap.alpha)
                    del pixmap
                key = pixel_keys[xref]
                if key not in active_keys:  # Unpainted resources are not uses.
                    continue
                path, digest = _write_payload(output, 'image', info['image'], info['ext'])
                if digest not in by_sha:
                    asset = {'asset_id': 'raster-' + digest, 'sha256': digest,
                             'path': str(path), 'width': info['width'], 'height': info['height'],
                             'ext': info['ext'], 'bytes': len(info['image']),
                             'xrefs': [], 'uses': [], 'candidate_uses': [], 'soft_mask_xrefs': [],
                             'visual_role': 'unclassified', 'text_baked_in': 'unknown',
                             'max_bbox_page_coverage': 0.0}
                    by_sha[digest] = asset
                    result['assets'].append(asset)
                asset = by_sha[digest]
                if xref not in asset['xrefs']:
                    asset['xrefs'].append(xref)
                if soft_mask_xref:
                    if soft_mask_xref not in extracted:
                        extracted[soft_mask_xref] = document.extract_image(soft_mask_xref)
                    mask_info = extracted[soft_mask_xref]
                    if not mask_info:
                        raise ValueError('PDF soft mask could not be extracted: %s' % soft_mask_xref)
                    mask_path, mask_digest = _write_payload(output, 'mask', mask_info['image'], mask_info['ext'])
                    if mask_digest not in mask_by_sha:
                        mask = {'xref': soft_mask_xref, 'xrefs': [], 'sha256': mask_digest,
                                'path': str(mask_path), 'width': mask_info['width'],
                                'height': mask_info['height'], 'ext': mask_info['ext'],
                                'bytes': len(mask_info['image']), 'kind': 'pdf_soft_mask'}
                        mask_by_sha[mask_digest] = mask
                        result['soft_masks'].append(mask)
                    mask = mask_by_sha[mask_digest]
                    if soft_mask_xref not in mask['xrefs']:
                        mask['xrefs'].append(soft_mask_xref)
                    if soft_mask_xref not in asset['soft_mask_xrefs']:
                        asset['soft_mask_xrefs'].append(soft_mask_xref)
                mask_type = document.xref_get_key(xref, 'Mask')[0]
                resources.setdefault(key, []).append({'xref': xref, 'asset': asset,
                                                       'soft_mask_xref': soft_mask_xref,
                                                       'has_mask': bool(soft_mask_xref or mask_type != 'null'
                                                                        or pixel_alpha[xref])})
            for occurrence, paint in enumerate(paints, 1):
                painted_count += 1
                key = (paint['digest'], paint['width'], paint['height'])
                candidates = resources.get(key, [])
                if 'has-mask' in paint:
                    candidates = [r for r in candidates if r['has_mask'] == paint['has-mask']]
                xrefs = sorted({r['xref'] for r in candidates})
                masks = sorted({r['soft_mask_xref'] for r in candidates})
                asset_ids = sorted({r['asset']['asset_id'] for r in candidates})
                mask_consistent = len(masks) == 1 and not (paint.get('has-mask') and masks == [0])
                rectangle = fitz.Rect(paint['bbox'])
                clipped = rectangle & fitz.Rect(0, 0, width, height)
                coverage = (max(0, clipped.width) * max(0, clipped.height)) / (width * height)
                use = {'page': number, 'occurrence': occurrence,
                       'bbox': [round(float(v), 3) for v in rectangle],
                       'transform': [round(float(v), 6) for v in paint['transform']],
                       'xref': xrefs[0] if len(xrefs) == 1 else None,
                       'xref_candidates': xrefs, 'xref_exact': False,
                       'resource_association': 'unique_candidate' if len(xrefs) == 1 else
                                               'ambiguous' if xrefs else 'unavailable',
                       'soft_mask_xref': masks[0] if mask_consistent else None,
                       'soft_mask_candidates': masks,
                       'mask_association': 'consistent_candidates' if mask_consistent else
                                           'ambiguous' if len(masks) > 1 else 'unavailable',
                       'bbox_page_coverage': round(coverage, 5)}
                if len(asset_ids) == 1:
                    asset = by_sha[next(r['asset']['sha256'] for r in candidates)]
                    asset['uses'].append(use)
                    asset['max_bbox_page_coverage'] = max(asset['max_bbox_page_coverage'],
                                                          round(coverage, 5))
                else:
                    # Identical decoded pixels can have different encoded
                    # payloads, or no xref (inline image). Keep this occurrence
                    # once, without inventing a payload/resource association.
                    use['asset_candidates'] = asset_ids
                    result['unresolved_occurrences'].append(use)
                    for asset_id in asset_ids:
                        next(a for a in result['assets'] if a['asset_id'] == asset_id)['candidate_uses'].append(use)
    for asset in result['assets']:
        asset['xrefs'].sort(); asset['soft_mask_xrefs'].sort()
    for mask in result['soft_masks']:
        mask['xrefs'].sort()
    result['overview'] = _overview(result['assets'], result['soft_masks'], output)
    result['summary'] = {'asset_count': len(result['assets']),
                         'painted_uses': painted_count,
                         'unresolved_payload_uses': len(result['unresolved_occurrences']),
                         'soft_mask_count': len(result['soft_masks'])}
    return result


def render_pdf_overview(pdf_path, output_dir, pages=None, long_edge=1440):
    """Render full reference pages and numbered selection sheets, without cropping.

    Full pages retain the PDF's visible rotation and aspect. Sheets are only a
    browsing aid; each tile points to a separate full-page image for inspection.
    Originals and existing output images are never overwritten.
    """
    if isinstance(long_edge, bool) or not isinstance(long_edge, int) or not 256 <= long_edge <= 3800:
        raise ValueError('long_edge must be an integer between 256 and 3800 pixels')
    try:
        import fitz
        from PIL import Image, ImageDraw
    except ImportError as exc:
        raise ValueError('PDF overview needs existing PyMuPDF and Pillow') from exc
    source = Path(pdf_path).resolve()
    source_bytes = source.read_bytes()
    if len(source_bytes) > 100 * 1024 * 1024:
        raise ValueError('PDF exceeds the 100 MiB reference limit')
    digest = hashlib.sha256(source_bytes).hexdigest()
    output = Path(output_dir).resolve()
    result = {'schema_version': 1, 'reference_type': 'pdf_page_overview',
              'source_pdf': {'path': str(source), 'sha256': digest}, 'pages': [],
              'overview': {'paths': [], 'sheets': []},
              'purpose': 'reference selection; inspect full pages for visual details'}
    with fitz.open(stream=source_bytes, filetype='pdf') as document:
        if document.needs_pass:
            raise ValueError('encrypted PDF references are not supported')
        if len(document) > 500:
            raise ValueError('PDF exceeds the 500-page reference limit')
        selected = _selected_pages(len(document), pages)
        result['source_pdf']['page_count'] = len(document)
        result['selected_pages'] = selected
        page_dir, sheet_dir = output / 'pages', output / 'overview'
        page_dir.mkdir(parents=True, exist_ok=True)
        sheet_dir.mkdir(parents=True, exist_ok=True)
        for start in range(0, len(selected), 20):
            numbers = selected[start:start + 20]
            canvas = Image.new('RGB', (4 * 324 + 12, math.ceil(len(numbers) / 4) * 250 + 12), '#E7EAEE')
            draw = ImageDraw.Draw(canvas)
            for index, number in enumerate(numbers):
                page = document[number - 1]
                scale = long_edge / max(page.rect.width, page.rect.height)
                pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), colorspace=fitz.csRGB, alpha=False)
                image = Image.frombytes('RGB', (pixmap.width, pixmap.height), pixmap.samples)
                path = page_dir / ('page-%04d.jpg' % number)
                with path.open('xb') as stream:
                    image.save(stream, format='JPEG', quality=90)
                result['pages'].append({'page': number, 'path': str(path),
                                        'width_px': image.width, 'height_px': image.height,
                                        'rotation': page.rotation})
                image.thumbnail((312, 218), Image.Resampling.LANCZOS)
                x, y = 12 + index % 4 * 324, 12 + index // 4 * 250
                draw.rectangle((x, y, x + 312, y + 218), fill='white')
                canvas.paste(image, (x + (312 - image.width) // 2, y + (218 - image.height) // 2))
                draw.text((x, y + 224), 'Page %d' % number, fill='#25282D')
            path = sheet_dir / ('reference-overview-%03d.jpg' % (start // 20 + 1))
            with path.open('xb') as stream:
                canvas.save(stream, format='JPEG', quality=88)
            result['overview']['paths'].append(str(path))
            result['overview']['sheets'].append({'path': str(path), 'pages': numbers})
    result['input_unchanged'] = hashlib.sha256(source.read_bytes()).hexdigest() == digest
    result['summary'] = {'source_pages': result['source_pdf']['page_count'],
                         'rendered_pages': len(result['pages']),
                         'overview_sheets': len(result['overview']['paths'])}
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    extract = commands.add_parser('extract', help='export original embedded raster assets')
    extract.add_argument('--pdf', required=True)
    extract.add_argument('--pages', help='one-based comma/ranges, such as 1,4-6')
    extract.add_argument('--output-dir', required=True)
    extract.add_argument('--manifest')
    extract.add_argument('--min-edge', type=int, default=256)
    overview = commands.add_parser('overview', help='render complete reference pages and numbered selection sheets')
    overview.add_argument('--pdf', required=True)
    overview.add_argument('--pages', help='one-based comma/ranges; default all pages')
    overview.add_argument('--output-dir', required=True)
    overview.add_argument('--manifest')
    overview.add_argument('--long-edge', type=int, default=1440)
    args = parser.parse_args(argv)
    try:
        default_manifest = 'reference-overview.json' if args.command == 'overview' else 'reference-assets.json'
        manifest = Path(args.manifest or str(Path(args.output_dir) / default_manifest)).resolve()
        if manifest == Path(args.pdf).resolve():
            raise ValueError('manifest must not overwrite the reference PDF')
        if args.command == 'overview':
            result = render_pdf_overview(args.pdf, args.output_dir,
                                         pages=_page_spec(args.pages) if args.pages else None,
                                         long_edge=args.long_edge)
        else:
            result = extract_pdf_assets(args.pdf, args.output_dir,
                                        pages=_page_spec(args.pages) if args.pages else None,
                                        min_edge=args.min_edge)
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({'ok': True, 'manifest': str(manifest), **result['summary'],
                          'selected_pages': result['selected_pages'], 'overview': result['overview']},
                         ensure_ascii=False))
        return 0
    except (ValueError, OSError) as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
