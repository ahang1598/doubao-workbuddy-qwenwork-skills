"""Visual migration must preserve inline meaning and resolved option labels."""
from pathlib import Path
import importlib.util

from lxml import etree as ET
import sys
import xml.etree.ElementTree as StdET


NS = 'https://www.larkoffice.com/sml/2.0'


def api():
    path = Path(__file__).parents[1] / 'template' / 'template_migration.py'
    spec = importlib.util.spec_from_file_location('migration_text_roles', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def frame():
    return f'<slide xmlns="{NS}"><data/></slide>'


def test_new_body_style_keeps_local_answer_emphasis_and_symbol_code_fonts():
    source = f'''<slide xmlns="{NS}"><data>
      <shape id="body" type="text" width="700" height="100">
        <content fontFamily="Arial" fontSize="20" color="rgb(0,0,0)" bold="false">
          <p><span id="plain">Ordinary text.</span></p>
          <p><span id="answer" color="rgb(180,0,0)" bold="true">Correct answer.</span></p>
          <p><span id="symbol" fontFamily="Symbol">x</span><span id="code" fontFamily="Consolas">  x = 1</span></p>
          <p><span id="footnote" fontSize="10">Source note.</span></p>
        </content>
      </shape></data><note><content><p>Original notes.</p></content></note></slide>'''
    result = api().compose_migration(source, frame(), target_region=[0,0,700,100],
        role_styles={'body': {'fontFamily':'Noto Serif SC','fontSize':24,
                             'color':'rgb(0,80,0)','bold':False}})
    root = ET.fromstring(result['xml'].encode())
    spans = {n.get('id'):n for n in root.iter() if ET.QName(n).localname=='span'}
    assert spans['plain'].get('fontFamily') == 'Noto Serif SC'
    assert spans['answer'].get('color') == 'rgb(180,0,0)'
    assert spans['answer'].get('bold') == 'true'
    assert spans['symbol'].get('fontFamily') == 'Symbol'
    assert spans['code'].get('fontFamily') == 'Consolas'
    assert float(spans['footnote'].get('fontSize')) == 12
    assert api().validate_migration(result['xml'], result['contract'])['ok']
    sys.path.insert(0, str(Path(__file__).parents[1]))
    try:
        import xml_lint
        assert xml_lint.validate_sxsd_document(result['xml'], StdET.fromstring(result['xml'])) == []
    finally:
        sys.path.pop(0)


def test_explicit_list_migration_keeps_abc_and_rejects_all_a():
    source = f'''<slide xmlns="{NS}"><data><shape id="choices" type="text" width="700" height="200">
      <content list="number" listStyle="alpha-uc-period"><ol>
        <li><p>First option</p></li><li><p>Second option</p></li><li><p>Third option</p></li>
      </ol></content></shape></data><note><content><p>Answer C.</p></content></note></slide>'''
    result = api().compose_migration(source, frame(), target_region=[0,0,700,200], explicit_numbering=True)
    root = ET.fromstring(result['xml'].encode())
    paragraphs = root.findall('.//{*}data//{*}p')
    assert [p.get('autoStartAt') for p in paragraphs] == ['1','2','3']
    assert api().validate_migration(result['xml'], result['contract'])['ok']
    for paragraph in paragraphs: paragraph.set('autoStartAt','1')
    changed = ET.tostring(root, encoding='unicode')
    assert not api().validate_migration(changed, result['contract'])['ok']


def test_code_font_on_span_still_protects_indentation():
    source=f'''<slide xmlns="{NS}"><data><shape id="code" type="text" width="700" height="100">
      <content fontFamily="Arial"><p><span fontFamily="Consolas">  return value</span></p></content>
      </shape></data><note><content/></note></slide>'''
    result=api().compose_migration(source,frame(),target_region=[0,0,700,100])
    root=ET.fromstring(result['xml'].encode())
    root.find('.//{*}span').text='return value'
    assert not api().validate_migration(ET.tostring(root,encoding='unicode'),result['contract'])['ok']


def test_icon_font_private_glyph_is_not_replaced_by_body_font():
    source=f'''<slide xmlns="{NS}"><data><shape id="body" type="text" width="700" height="100">
      <content fontFamily="Arial"><p><span id="icon" fontFamily="FontAwesome">\uf00b</span><span>Agenda</span></p></content>
      </shape></data><note><content/></note></slide>'''
    result=api().compose_migration(source,frame(),target_region=[0,0,700,100],role_styles={'body':{'fontFamily':'Noto Serif SC'}})
    icon=ET.fromstring(result['xml'].encode()).find('.//{*}span[@id="icon"]')
    assert icon.get('fontFamily')=='FontAwesome'


def test_body_tail_sets_primary_style_without_erasing_local_note_emphasis():
    source=f'''<slide xmlns="{NS}"><data><shape id="body" type="text" width="700" height="100">
      <content fontFamily="Arial" fontSize="20" color="rgb(0,0,0)" bold="false"><p><span id="note" fontSize="10" color="rgb(180,0,0)" bold="true">Note</span> Main paragraph body with more words.</p></content>
      </shape></data><note><content/></note></slide>'''
    result=api().compose_migration(source,frame(),target_region=[0,0,700,100],role_styles={'body':{'fontSize':24,'color':'rgb(0,80,0)','bold':False}})
    note=ET.fromstring(result['xml'].encode()).find('.//{*}span[@id="note"]')
    assert float(note.get('fontSize'))==12
    assert note.get('color')=='rgb(180,0,0)' and note.get('bold')=='true'


def test_long_small_print_does_not_replace_the_visible_default_size():
    source=f'''<slide xmlns="{NS}"><data><shape id="body" type="text" width="700" height="100">
      <content fontSize="20"><p>Key point</p><p><span id="small" fontSize="10">A much longer source annotation with many words that still belongs to the smaller text role.</span></p></content>
      </shape></data><note><content/></note></slide>'''
    result=api().compose_migration(source,frame(),target_region=[0,0,700,100],role_styles={'body':{'fontSize':24}})
    root=ET.fromstring(result['xml'].encode())
    assert float(root.find('.//{*}content').get('fontSize'))==24
    assert float(root.find('.//{*}span[@id="small"]').get('fontSize'))==12


def test_implicit_body_color_is_not_confused_with_explicit_answer_highlight():
    source=f'''<slide xmlns="{NS}"><data><shape id="body" type="text" width="700" height="100">
      <content fontSize="20"><p>Ordinary body text with no explicit color. <span id="answer" color="rgb(180,0,0)">Correct answer.</span></p></content>
      </shape></data><note><content/></note></slide>'''
    result=api().compose_migration(source,frame(),target_region=[0,0,700,100],role_styles={'body':{'color':'rgb(0,80,0)'}})
    answer=ET.fromstring(result['xml'].encode()).find('.//{*}span[@id="answer"]')
    assert answer.get('color')=='rgb(180,0,0)'
