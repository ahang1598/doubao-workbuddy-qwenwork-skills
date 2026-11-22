"""The actual parser CLI carries source-format preparation into import inputs."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from pptx import Presentation


def test_parser_cli_uses_and_records_the_distinct_prepared_source(tmp_path):
    source=tmp_path/'source.pptx'
    deck=Presentation()
    deck.slides.add_slide(deck.slide_layouts[1]).shapes.title.text='Original title'
    deck.save(source)
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    script=Path(__file__).parents[1]/ 'template' / 'parse_template.py'
    work=tmp_path/'work'
    result=subprocess.run([sys.executable,str(script),'--pptx',str(source),'--work-dir',str(work),
        '--prepare-import-source','--offline-only'],capture_output=True,text=True,timeout=45)
    assert result.returncode==0,result.stderr[-1500:]
    index=json.loads((work/'manifest/template-index.json').read_text())
    prepared=index['source_import_preparation']
    assert prepared['protected_content_unchanged']
    assert Path(prepared['output_pptx'])!=source
    assert index['source_input']['path']==str(source)
    assert Path(prepared['output_pptx']).read_bytes()==source.read_bytes()
    assert hashlib.sha256(source.read_bytes()).hexdigest()==digest
