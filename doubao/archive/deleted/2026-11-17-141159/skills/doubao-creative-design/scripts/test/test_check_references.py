#!/usr/bin/env python3
import sys
sys.dont_write_bytecode = True
import importlib.util
import tempfile
from pathlib import Path
spec = importlib.util.spec_from_file_location('refs', Path(__file__).resolve().parents[1] / 'maintenance/check-references.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    (root / 'SKILL.md').write_text(
        '# Home\nSee [home](#home), `brief.md`, `prompt-log.md`, '
        '`references/rule.md#section`, and [explicit](references/rule.md#stable.id).\n'
    )
    (root / 'references').mkdir()
    (root / 'references/rule.md').write_text('# Section\n<a id="stable.id"></a>\n')
    assert module.check(root)['status'] == 'pass', module.check(root)
    (root / 'references/nested').mkdir()
    (root / 'references/nested/readme.md').write_text('See `references/rule.md#section`.\n')
    assert module.check(root)['status'] == 'pass', module.check(root)
    (root / 'references/nested/readme.md').unlink()
    (root / 'SKILL.md').write_text('See `nonexistent-guide.md` and [missing](references/missing.md).\n')
    assert len(module.check(root)['errors']) == 2
    (root / 'SKILL.md').write_text('[bad anchor](references/rule.md#missing).\n')
    assert module.check(root)['errors'][0]['kind'] == 'missing_anchor'
    (root / 'SKILL.md').write_text('```text\nunclosed\n')
    assert module.check(root)['errors'][0]['kind'] == 'unclosed_code_fence'
print('5 reference checks passed')
