"""The raster inventory must reuse embedded bytes, not rendered PDF text."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys

import pytest

fitz = pytest.importorskip('fitz')
Image = pytest.importorskip('PIL.Image')
SCRIPT = Path(__file__).parents[1] / 'template' / 'template_reference_assets.py'


def api():
    if not SCRIPT.exists():
        pytest.fail('the original embedded raster extraction API is not implemented')
    spec = importlib.util.spec_from_file_location('template_reference_assets', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def jpeg_bytes(size=(768, 512)):
    image = Image.new('RGB', size, (17, 31, 47))
    stream = io.BytesIO()
    image.save(stream, 'JPEG', quality=91)
    return stream.getvalue()


def make_pdf(tmp_path, *, count=2, distinct_xrefs=False, tiny=False):
    data = jpeg_bytes()
    document = fitz.open()
    for _ in range(count):
        document.new_page(width=600, height=400)
    first = document[0].insert_image(fitz.Rect(0, 0, 600, 400), stream=data)
    xrefs = [first]
    for index in range(1, count):
        xref = first
        if distinct_xrefs:
            xref = document.get_new_xref()
            document.update_object(xref, '<<>>')
            document.xref_copy(first, xref)
        document[index].insert_image(fitz.Rect(0, 0, 600, 400), xref=xref)
        xrefs.append(xref)
    if tiny:
        document[0].insert_image(fitz.Rect(10, 10, 45, 45), stream=jpeg_bytes((64, 64)))
    for index in range(count):
        document[index].insert_text((40, 80), 'SOURCE_OVERLAY_%d' % index, fontsize=22)
    document.set_metadata({'title': 'SOURCE_METADATA_NOT_FACTS'})
    path = tmp_path / 'reference.pdf'
    document.save(path)
    document.close()
    return path, data, xrefs


def test_exports_exact_jpeg_without_baking_separate_pdf_text(tmp_path):
    # Rendering the page or re-encoding the image must break this assertion.
    path, original_jpeg, _ = make_pdf(tmp_path)
    source_bytes = path.read_bytes()
    result = api().extract_pdf_assets(path, tmp_path / 'assets')
    assert Path(result['assets'][0]['path']).read_bytes() == original_jpeg
    assert result['assets'][0]['sha256'] == hashlib.sha256(original_jpeg).hexdigest()
    assert path.read_bytes() == source_bytes
    serialized = json.dumps(result)
    assert 'SOURCE_OVERLAY' not in serialized
    assert 'SOURCE_METADATA_NOT_FACTS' not in serialized
    assert result['reference_type'] == 'pdf_raster_assets'


def test_identical_bytes_at_distinct_xrefs_are_emitted_once_with_both_uses(tmp_path):
    # Dedupe by xref alone would emit two files and lose this contract.
    path, _, xrefs = make_pdf(tmp_path, distinct_xrefs=True)
    assert xrefs[0] != xrefs[1]
    result = api().extract_pdf_assets(path, tmp_path / 'assets')
    assert len(result['assets']) == 1
    asset = result['assets'][0]
    assert asset['xrefs'] == sorted(xrefs)
    assert [(use['page'], use['bbox']) for use in asset['uses']] == [
        (1, [0.0, 0.0, 600.0, 400.0]), (2, [0.0, 0.0, 600.0, 400.0])]
    assert asset['width'] == 768 and asset['height'] == 512
    assert asset['visual_role'] == 'unclassified'
    assert asset['text_baked_in'] == 'unknown'


def test_page_scope_uses_only_selected_one_based_pages(tmp_path):
    path, original_jpeg, _ = make_pdf(tmp_path, count=3)
    result = api().extract_pdf_assets(path, tmp_path / 'scoped', pages=[2])
    assert result['selected_pages'] == [2]
    assert [use['page'] for use in result['assets'][0]['uses']] == [2]
    assert Path(result['assets'][0]['path']).read_bytes() == original_jpeg


def test_minimum_edge_filters_tiny_embedded_images_not_the_page_geometry(tmp_path):
    path, _, _ = make_pdf(tmp_path, tiny=True)
    result = api().extract_pdf_assets(path, tmp_path / 'assets', min_edge=256)
    assert len(result['assets']) == 1
    assert result['assets'][0]['width'] == 768
    all_sizes = api().extract_pdf_assets(path, tmp_path / 'all', min_edge=0)
    assert sorted((a['width'], a['height']) for a in all_sizes['assets']) == [(64, 64), (768, 512)]


def test_soft_mask_is_preserved_separately_without_reencoding_base_image(tmp_path):
    # A base RGB extraction alone would lose actual PDF transparency.
    rgba = Image.new('RGBA', (300, 300), (190, 30, 20, 0))
    for x in range(100, 200):
        for y in range(300):
            rgba.putpixel((x, y), (190, 30, 20, 128))
    for x in range(200, 300):
        for y in range(300):
            rgba.putpixel((x, y), (190, 30, 20, 255))
    stream = io.BytesIO(); rgba.save(stream, 'PNG')
    document = fitz.open(); page = document.new_page(width=300, height=300)
    xref = page.insert_image(page.rect, stream=stream.getvalue())
    path = tmp_path / 'alpha.pdf'; document.save(path); document.close()
    with fitz.open(path) as source:
        expected_base = source.extract_image(xref)['image']
        mask_xref = source[0].get_images(full=True)[0][1]
        expected_mask = source.extract_image(mask_xref)['image']
    before = path.read_bytes()
    result = api().extract_pdf_assets(path, tmp_path / 'assets')
    asset = result['assets'][0]
    assert Path(asset['path']).read_bytes() == expected_base
    assert asset['uses'][0]['soft_mask_xref'] == mask_xref
    mask = result['soft_masks'][0]
    assert mask['xref'] == mask_xref
    assert Path(mask['path']).read_bytes() == expected_mask
    reconstructed = Image.open(asset['path']).convert('RGBA')
    reconstructed.putalpha(Image.open(mask['path']).convert('L'))
    assert [reconstructed.getpixel((x, 150))[3] for x in (50, 150, 250)] == [0, 128, 255]
    assert path.read_bytes() == before


def test_cli_selects_comma_and_range_pages_and_writes_external_manifest(tmp_path):
    path, _, _ = make_pdf(tmp_path, count=4)
    api()  # Feature absence is a test failure, not a subprocess/file error.
    output = tmp_path / 'assets'; manifest = tmp_path / 'manifest' / 'raster.json'
    result = subprocess.run([sys.executable, str(SCRIPT), 'extract', '--pdf', str(path),
                             '--pages', '1,3-4', '--output-dir', str(output),
                             '--manifest', str(manifest)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    inventory = json.loads(manifest.read_text())
    assert inventory['selected_pages'] == [1, 3, 4]
    assert [u['page'] for u in inventory['assets'][0]['uses']] == [1, 3, 4]
    assert inventory['overview']['paths']
    assert all(Path(p).exists() for p in inventory['overview']['paths'])


@pytest.mark.parametrize('pages', [[0], [3], [], [True]])
def test_invalid_page_scope_fails_before_asset_output(tmp_path, pages):
    path, _, _ = make_pdf(tmp_path)
    output = tmp_path / 'bad'
    with pytest.raises(ValueError):
        api().extract_pdf_assets(path, output, pages=pages)
    assert not output.exists()


def test_cli_cannot_overwrite_the_reference_pdf_with_its_manifest(tmp_path):
    path, _, _ = make_pdf(tmp_path)
    original = path.read_bytes(); api()
    result = subprocess.run([sys.executable, str(SCRIPT), 'extract', '--pdf', str(path),
                             '--output-dir', str(tmp_path / 'assets'), '--manifest', str(path)],
                            capture_output=True, text=True)
    assert result.returncode != 0
    assert path.read_bytes() == original


def same_page_repeated_jpeg(tmp_path, *, different_masks=False):
    """Two actual Do operations, same JPEG payload, distinct image resources."""
    jpeg = jpeg_bytes((300, 300))
    document = fitz.open(); page = document.new_page(width=700, height=400)
    first = page.insert_image(fitz.Rect(0, 0, 300, 300), stream=jpeg)
    second = document.get_new_xref(); document.update_object(second, '<<>>')
    document.xref_copy(first, second)
    masks = []
    if different_masks:
        for image_xref, opacity in [(first, 64), (second, 192)]:
            mask = document.get_new_xref()
            document.update_object(mask, '<< /Type /XObject /Subtype /Image /Width 300 '
                                   '/Height 300 /BitsPerComponent 8 /ColorSpace /DeviceGray >>')
            document.update_stream(mask, bytes([opacity]) * (300 * 300))
            document.xref_set_key(image_xref, 'SMask', '%d 0 R' % mask)
            masks.append(mask)
    page.insert_image(fitz.Rect(350, 0, 650, 300), xref=second)
    path = tmp_path / 'same-page.pdf'; document.save(path); document.close()
    with fitz.open(path) as source:
        assert len(source[0].get_image_info()) == 2
        assert source.extract_image(first)['image'] == jpeg
        assert source.extract_image(second)['image'] == jpeg
    return path, jpeg, [first, second], masks


def test_same_page_duplicate_payload_counts_real_paints_once(tmp_path):
    # Calling get_image_rects once per xref duplicates these two real uses.
    path, jpeg, xrefs, _ = same_page_repeated_jpeg(tmp_path)
    result = api().extract_pdf_assets(path, tmp_path / 'assets')
    assert result['summary']['painted_uses'] == 2
    assert len(result['assets']) == 1
    asset = result['assets'][0]
    assert Path(asset['path']).read_bytes() == jpeg
    assert len(asset['uses']) == 2
    assert [u['bbox'] for u in asset['uses']] == [
        [0.0, 0.0, 300.0, 300.0], [350.0, 0.0, 650.0, 300.0]]
    for use, exact_xref in zip(asset['uses'], xrefs):
        if use['xref'] is not None:
            assert use['xref'] == exact_xref
        else:
            assert use['resource_association'] == 'ambiguous'
            assert use['xref_candidates'] == xrefs


def test_shared_base_jpeg_with_two_masks_never_cross_binds_transparency(tmp_path):
    # The left mask is 64, the right is 192. Hash lookup alone cannot bind them.
    path, jpeg, xrefs, masks = same_page_repeated_jpeg(tmp_path, different_masks=True)
    original_pdf = path.read_bytes()
    result = api().extract_pdf_assets(path, tmp_path / 'assets')
    assert result['summary']['painted_uses'] == 2
    asset = result['assets'][0]
    assert Path(asset['path']).read_bytes() == jpeg
    assert len(asset['uses']) == 2
    for use, image_xref, mask_xref in zip(asset['uses'], xrefs, masks):
        if use['soft_mask_xref'] is not None:
            assert use['xref'] == image_xref
            assert use['soft_mask_xref'] == mask_xref
        else:
            assert use['mask_association'] == 'ambiguous'
            assert use['soft_mask_candidates'] == masks
    ambiguous = any(u['soft_mask_xref'] is None for u in asset['uses'])
    if ambiguous:
        preview = result['overview']['items'][0]
        assert preview['soft_mask_applied'] is False
        assert preview['mask_association'] == 'ambiguous'
        # The preview must show the raw base, not a guessed alpha blended white.
        pixel = Image.open(result['overview']['paths'][0]).convert('RGB').getpixel((168, 102))
        assert max(pixel) < 80
    assert path.read_bytes() == original_pdf
