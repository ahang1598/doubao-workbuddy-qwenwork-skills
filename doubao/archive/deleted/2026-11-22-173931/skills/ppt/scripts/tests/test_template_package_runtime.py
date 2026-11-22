"""Template CLIs and package imports work from a foreign task directory."""
import os
import json
from pathlib import Path
import subprocess
import sys

import pytest


SKILL = Path(__file__).resolve().parents[2]
MODULES = (
    'parse_template', 'initial_blank', 'template_authoring_plan',
    'template_chart_contract', 'template_chart_inventory', 'template_import_source',
    'template_layout_contract', 'template_layout_materialize', 'template_layouts',
    'template_lint_all', 'template_list_layout', 'template_metrics',
    'template_migration', 'template_migration_source', 'template_publish',
    'template_reference_assets', 'template_reuse', 'template_style_reference',
    'template_text_fit',
)


CLI_MODULES = [name for name in MODULES if name not in (
    'initial_blank', 'template_list_layout', 'template_migration_source',
)]


@pytest.mark.parametrize('module', CLI_MODULES)
def test_template_cli_from_foreign_cwd(tmp_path, module):
    env = os.environ.copy()
    env.pop('PYTHONPATH', None)
    result = subprocess.run(
        [sys.executable, str(SKILL / 'scripts/template' / (module + '.py')), '--help'],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert 'usage:' in result.stdout.lower()


def test_template_package_and_shared_publisher_import_from_foreign_cwd(tmp_path):
    env = os.environ.copy()
    env['PYTHONPATH'] = str(SKILL)
    source = (
        'import importlib\n'
        f'for name in {MODULES!r}:\n'
        '    importlib.import_module("scripts.template." + name)\n'
        'from scripts.svg_lib.atomize_svg_to_slide import publish_slide\n'
        'result = publish_slide("<slide><data/></slide>")\n'
        'assert result["ok"]\n'
    )
    result = subprocess.run(
        [sys.executable, '-c', source], cwd=tmp_path, env=env,
        capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr


def test_template_publisher_executes_real_preflight_from_foreign_cwd(tmp_path):
    from scripts.template import template_publish

    xml = tmp_path / 'page.xml'
    xml.write_text('<slide xmlns="https://www.larkoffice.com/sml/2.0"><data>'
        '<shape type="text" topLeftX="80" topLeftY="80" width="800" height="100">'
        '<content fontSize="24" fontFamily="Arial" color="rgb(0,0,0)"><p>Template content</p></content>'
        '</shape></data></slide>')
    commands = []
    def runner(command, **options):
        commands.append(command)
        if command[0] == 'lark-cli':
            assert command[2] == '+add-slide'
            return subprocess.CompletedProcess(command, 0, json.dumps({'ok': True,
                'data': {'slide_id': 'written', 'xml_presentation_id': 'D'}}), '')
        return subprocess.run(command, **options)
    result = template_publish.publish(presentation='D', xml=xml, page=2,
        mode='active_rebuild', work_dir=tmp_path, runner=runner)
    assert result['ok'] and result['slide_id'] == 'written'
    preflight = next(command for command in commands if command[0] != 'lark-cli')
    assert Path(preflight[1]).parent == SKILL / 'scripts/template'
    assert Path(preflight[preflight.index('--skill-root') + 1]) == SKILL
    report = json.loads(Path(result['report_path']).read_text())
    assert isinstance(report['preflight']['json'], dict)
    assert 'exception' not in report['preflight']
