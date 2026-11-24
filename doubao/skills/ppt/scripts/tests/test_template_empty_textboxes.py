import importlib.util
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET

from pptx import Presentation
from pptx.util import Inches
from pptx.dml.color import RGBColor


def api():
    path = Path(__file__).parents[1] / 'template/template_import_source.py'
    spec = importlib.util.spec_from_file_location('empty_text_import', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def source(path):
    prs = Presentation(); slide = prs.slides.add_slide(prs.slide_layouts[1])
    for i in range(2):
        slide.shapes.add_textbox(Inches(i), Inches(2), Inches(1), Inches(1))
    text = slide.shapes.add_textbox(Inches(2), Inches(2), Inches(1), Inches(1)); text.text = 'Keep this'
    painted = slide.shapes.add_textbox(Inches(3), Inches(2), Inches(1), Inches(1))
    painted.fill.solid(); painted.fill.fore_color.rgb = RGBColor(12, 34, 56)
    prs.save(path)
    return path.read_bytes()


def test_cleanup_removes_only_unpainted_textboxes_and_keeps_original_and_layout_slots(tmp_path):
    src = tmp_path/'source.pptx'; original = source(src); out = tmp_path/'clean.pptx'
    report = api().prepare_import_source(src, out, picture_fallbacks=False, empty_textboxes=True)
    assert report['empty_textboxes_removed_count'] == 2
    assert report['protected_content_unchanged'] and report['relationships_unchanged'] and report['media_unchanged']
    assert src.read_bytes() == original
    result = Presentation(out).slides[0]
    assert len(result.shapes) == 4  # two layout placeholders, real text, painted empty box
    assert any(getattr(s, 'text', '') == 'Keep this' for s in result.shapes)
    assert any(s.is_placeholder for s in result.shapes)


def test_default_keeps_source_textboxes_and_identical_package(tmp_path):
    src = tmp_path/'source.pptx'; original = source(src); out = tmp_path/'plain.pptx'
    report = api().prepare_import_source(src, out, picture_fallbacks=False)
    assert report['empty_textboxes_removed_count'] == 0
    assert out.read_bytes() == original


def test_cleanup_preserves_textbox_targeted_by_animation(tmp_path):
    src = tmp_path/'source.pptx'; source(src)
    with zipfile.ZipFile(src) as z: parts = {n:z.read(n) for n in z.namelist()}
    ns = {'p':'http://schemas.openxmlformats.org/presentationml/2006/main'}
    root = ET.fromstring(parts['ppt/slides/slide1.xml'])
    boxes = root.findall('.//p:sp',ns); target = boxes[2].find('p:nvSpPr/p:cNvPr',ns).get('id')
    timing = ET.SubElement(root, '{'+ns['p']+'}timing')
    ET.SubElement(timing, '{'+ns['p']+'}spTgt', {'spid':target})
    parts['ppt/slides/slide1.xml'] = ET.tostring(root)
    with zipfile.ZipFile(src,'w') as z:
        for n,data in parts.items(): z.writestr(n,data)
    report = api().prepare_import_source(src, tmp_path/'clean.pptx', picture_fallbacks=False, empty_textboxes=True)
    assert report['empty_textboxes_removed_count'] == 1
    assert target not in {x['shape_id'] for x in report['empty_textboxes_removed']}
