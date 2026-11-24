"""POTX normalization preserves a complete source package for the import pipeline."""
import hashlib
import importlib.util
from pathlib import Path
import sys
import zipfile

import pytest
from pptx import Presentation


TEMPLATE_TYPE = b'application/vnd.openxmlformats-officedocument.presentationml.template.main+xml'
PRESENTATION_TYPE = b'application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml'


def api():
    path = Path(__file__).parents[1] / 'template' / 'parse_template.py'
    spec = importlib.util.spec_from_file_location('potx_input_api', path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


def source_template(tmp_path):
    source = tmp_path / 'complete.potx'
    deck = Presentation()
    slide = deck.slides.add_slide(deck.slide_layouts[1])
    slide.shapes.title.text = 'Original title'
    slide.placeholders[1].text = 'First item\nSecond item'
    slide.notes_slide.notes_text_frame.text = 'Original speaker notes'
    deck.slides.add_slide(deck.slide_layouts[5]).shapes.title.text = 'Original closing'
    presentation = tmp_path / 'complete.pptx'
    deck.save(presentation)
    with zipfile.ZipFile(presentation) as z, zipfile.ZipFile(source, 'w') as out:
        for info in z.infolist():
            data = z.read(info.filename)
            if info.filename == '[Content_Types].xml':
                data = data.replace(PRESENTATION_TYPE, TEMPLATE_TYPE)
            out.writestr(info, data)
    return source


def test_complete_potx_becomes_importable_without_changing_source_parts(tmp_path):
    source = source_template(tmp_path)
    original_digest = hashlib.sha256(source.read_bytes()).hexdigest()
    normalized = api().prepare_template_input(source, tmp_path / 'work')
    assert normalized.suffix == '.pptx'
    assert len(Presentation(normalized).slides) == 2
    with zipfile.ZipFile(source) as before, zipfile.ZipFile(normalized) as after:
        assert before.namelist() == after.namelist()
        for name in before.namelist():
            if name != '[Content_Types].xml':
                assert before.read(name) == after.read(name), name
        assert PRESENTATION_TYPE in after.read('[Content_Types].xml')
        assert TEMPLATE_TYPE not in after.read('[Content_Types].xml')
    assert hashlib.sha256(source.read_bytes()).hexdigest() == original_digest


def test_pptx_uses_original_without_a_repacked_copy(tmp_path):
    source = tmp_path / 'existing.pptx'
    Presentation().save(source)
    original = source.read_bytes()
    assert api().prepare_template_input(source, tmp_path / 'work') == source.resolve()
    assert source.read_bytes() == original


def test_normalization_reuses_same_copy_and_preserves_unrelated_output(tmp_path):
    source = source_template(tmp_path)
    module = api()
    output = module.prepare_template_input(source, tmp_path / 'work')
    assert module.prepare_template_input(source, tmp_path / 'work') == output
    output.write_bytes(b'unrelated existing output')
    with pytest.raises(FileExistsError):
        module.prepare_template_input(source, tmp_path / 'work')
    assert output.read_bytes() == b'unrelated existing output'
