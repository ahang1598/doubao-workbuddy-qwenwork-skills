"""The plan executor composes real pages; only publishing's CLI boundary is fake."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

from lxml import etree as ET
import pytest


SCRIPT = Path(__file__).parents[1] / 'template' / 'template_authoring_plan.py'
NS = 'https://www.larkoffice.com/sml/2.0'


def test_plan_preserves_and_forwards_reviewed_source_visual(tmp_path):
    plan = ready_pages(tmp_path, 1)
    image = tmp_path/'source.png'; image.write_bytes(b'reviewed source')
    plan['pages'][0]['source_visual'] = 'source.png'
    result = api().prepare_plan(plan, tmp_path)
    assert result['ok']
    row = result['pages'][0]
    assert row['source_visual'] == [str(image)]
    command = api()._publisher_command(plan['pages'][0], row, tmp_path, 'D')
    assert command[command.index('--source-visual')+1] == str(image)


def test_plan_can_forward_direct_lint_override_without_a_waiver_file(tmp_path):
    plan = ready_pages(tmp_path, 1)
    plan['pages'][0].update(no_lint=True, reason='Known visual false positive')
    result = api().prepare_plan(plan, tmp_path)
    assert result['ok']
    command = api()._publisher_command(plan['pages'][0], result['pages'][0], tmp_path, 'D')
    assert '--no-lint' in command
    assert command[command.index('--reason')+1] == 'Known visual false positive'
    assert '--exception-file' not in command


def test_ready_recipe_prepares_selected_text_and_stable_list_labels(tmp_path):
    source=tmp_path/'source.xml'
    source.write_text(f'<slide xmlns="{NS}"><data>'
        '<shape id="circle" type="ellipse" topLeftX="50" topLeftY="50" width="56" height="56">'
        '<content fontFamily="Source Han Sans" fontSize="15" bold="true"><p>开放</p><p>台账</p></content></shape>'
        '<shape id="options" type="text" width="600" height="200"><content><ol listStyle="alpha-uc-period">'
        '<li><p>One</p></li><li><p>Two</p></li><li><p>Three</p></li></ol></content></shape>'
        '</data><note><content><p>Original note.</p></content></note></slide>')
    original=source.read_bytes()
    result=api().prepare_plan({'pages':[{'page':1,'link':'L7','mode':'component_reuse','operation':'ready',
        'xml':'source.xml','explicit_numbering':True,'text_fit_ids':['circle']}]},tmp_path)
    assert result['ok']
    root=ET.parse(result['pages'][0]['xml_path']).getroot()
    circle=root.find('.//{*}shape[@id="circle"]/{*}content')
    assert circle.get('paddingLeft') == '0' and circle.get('paddingRight') == '0'
    assert [p.get('autoStartAt') for p in root.findall('.//{*}ol/{*}li/{*}p')] == ['1','2','3']
    assert source.read_bytes() == original


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def api():
    assert SCRIPT.exists(), 'deterministic authoring-plan executor is missing'
    return load(SCRIPT, 'authoring_plan_test')


def source_pages(work):
    inputs = work / 'inputs'
    inputs.mkdir()
    frame = inputs / 'frame.xml'
    frame.write_text(f'<slide xmlns="{NS}" width="960" height="540"><data>'
        '<shape id="background" type="rect" width="960" height="540"><fill><fillColor color="#fff"/></fill></shape>'
        '<shape id="example" type="text" width="200" height="40"><content><p>Target example words</p></content></shape>'
        '</data><note><content><p>Target example notes</p></content></note></slide>', encoding='utf-8')
    sources = []
    for index, (value, note) in enumerate([('167', 'First source notes'), ('173', 'Second source notes')], 1):
        source = inputs / f'source-{index}.xml'
        source.write_text(f'<slide xmlns="{NS}" id="source-{index}"><data>'
            '<shape id="title" type="text" topLeftX="10" topLeftY="10" width="300" height="50">'
            f'<content fontFamily="Calibri" fontSize="28"><p><span bold="true">Source {value}</span></p></content></shape>'
            '<table id="facts" topLeftX="10" topLeftY="80" width="300" height="60"><tr>'
            f'<td><content><p>{value}</p></content></td><td><content><p>53</p></content></td></tr></table>'
            '<img id="picture" src="original-pixels" rotate="270" topLeftX="350" topLeftY="80" width="100" height="60">'
            '<crop anchor="top"/></img></data>'
            f'<note><content><p>{note}</p><p xml:space="preserve">    code  spacing</p></content></note></slide>', encoding='utf-8')
        sources.append(source)
    return sources, frame


def migration_plan(work):
    sources, frame = source_pages(work)
    pages = [{'page': i, 'link': 'L8', 'mode': 'component_reuse', 'operation': 'migration',
              'source': str(source.relative_to(work)), 'frame': str(frame.relative_to(work)),
              'content_ids': ['title', 'facts', 'picture'], 'frame_ids': ['background'],
              'target_region': [40, 100, 880, 390],
              'bindings': {'ids': {'title': f'title-{i}'}, 'media': {}}}
             for i, source in enumerate(sources, 1)]
    return {'schema_version': 1, 'pages': pages}, sources, frame


def fill_page(work, page=1):
    source = work / 'component.xml'
    if not source.exists():
        source.write_text(f'<slide xmlns="{NS}" id="component-source"><data>'
            '<shape id="a" type="text" topLeftX="40" topLeftY="100" width="200" height="80">'
            '<content fontFamily="Calibri"><p><span bold="true">Legacy</span> | 2023</p></content></shape>'
            '<shape id="b" type="text" topLeftX="350" topLeftY="100" width="200" height="80">'
            '<content><p>Old body</p></content></shape><line id="ab" startShapeId="a" endShapeId="b"/>'
            '</data><note><content><p>Old template lecture</p></content></note></slide>', encoding='utf-8')
    reuse = load(SCRIPT.with_name('template_reuse.py'), 'fill_plan_fixture')
    field_plan = reuse.prepare_component_fill(source, ['a', 'b', 'ab'])
    replacements = {'Legacy': '规模{{lines}}', ' | 2023': ' · {{year}}', 'Old body': '分母{{denom}}'}
    for field in field_plan['fields']:
        field.update(action='replace', new_text=replacements[field['source_text']])
    return {'page': page, 'link': 'L4', 'mode': 'component_reuse', 'operation': 'fill',
            'source': str(source.relative_to(work)), 'ids': ['a', 'b', 'ab'], 'fill_plan': field_plan,
            'notes': ['站点{{lines}}；订单{{denom}}。', '年度{{year}} <核对> & 保留']}, source


def ready_pages(work, count=3):
    inputs = work / 'ready'
    inputs.mkdir(exist_ok=True)
    pages = []
    for i in range(1, count + 1):
        path = inputs / f'page-{i}.xml'
        path.write_text(f'<slide xmlns="{NS}"><data><shape type="text"><content><p>Page {i}</p></content></shape></data></slide>')
        pages.append({'page': i, 'link': 'L4', 'mode': 'component_reuse', 'operation': 'ready',
                      'xml': str(path.relative_to(work))})
    return {'pages': pages}


class PublishingCLI:
    def __init__(self, failed_page=None):
        self.failed_page = failed_page
        self.commands = []

    def __call__(self, argv, **kwargs):
        self.commands.append(argv)
        page = int(argv[argv.index('--page') + 1])
        if page == self.failed_page:
            result = {'ok': False, 'status': 'preflight_blocked', 'error': 'Actual lint failure',
                      'report_path': str(Path(kwargs['cwd']) / 'publisher-failed.json')}
            return subprocess.CompletedProcess(argv, 1, json.dumps(result), 'full diagnostic ' + 'x' * 12000)
        return subprocess.CompletedProcess(argv, 0,
            json.dumps({'ok': True, 'status': 'published', 'slide_id': f'S{page}'}), '')


def test_prepare_two_explicit_migrations_copies_each_source_facts_and_notes(tmp_path):
    # Break caught: reusing one source page for all pages, dropping notes/cells,
    # or failing to produce the real publisher's contract/bindings paths.
    plan, sources, frame = migration_plan(tmp_path)
    original = {p: p.read_bytes() for p in [*sources, frame]}
    result = api().prepare_plan(plan, tmp_path)
    assert result['ok'] and result['prepared_pages'] == [1, 2]
    for row, value, note in zip(result['pages'], ['167', '173'], ['First source notes', 'Second source notes']):
        root = ET.parse(row['xml_path']).getroot()
        assert root.find('.//{*}td/{*}content/{*}p').text == value
        assert root.find('{*}note/{*}content/{*}p').text == note
        assert root.find('{*}note/{*}content/{*}p[2]').text == '    code  spacing'
        assert root.find('{*}data/{*}img').get('rotate') == '270'
        assert root.find('{*}data/{*}img/{*}crop').get('anchor') == 'top'
        assert 'Target example' not in Path(row['xml_path']).read_text()
        contract = json.loads(Path(row['migration_contract']).read_text())
        assert contract['content_ids'] == ['title', 'facts', 'picture']
        assert contract['source']['sha256'] == hashlib.sha256(original[sources[row['page'] - 1]]).hexdigest()
        assert Path(row['migration_bindings']).is_file()
        assert any(Path(item['snapshot']).read_bytes() == original[sources[row['page'] - 1]]
                   for item in row['source_snapshots'])
    assert all(p.read_bytes() == raw for p, raw in original.items())
    assert json.loads(Path(result['plan_snapshot']).read_text()) == plan


def test_fill_shared_display_values_resolve_in_text_and_real_note_paragraphs(tmp_path):
    # Break caught: independently retyping notes, changing source_text bindings,
    # flattening source rich runs, or failing to escape XML punctuation.
    page, source = fill_page(tmp_path)
    original = source.read_bytes()
    values = tmp_path / 'display-values.json'
    values.write_text(json.dumps({'lines': '15', 'denom': '62000', 'year': '2027'}))
    plan = {'pages': [page], 'values_file': 'display-values.json'}
    before = copy.deepcopy(plan)
    result = api().prepare_plan(plan, tmp_path)
    assert result['ok']
    root = ET.parse(result['pages'][0]['xml_path']).getroot()
    span = root.find('{*}data/{*}shape/{*}content/{*}p/{*}span')
    assert span.text == '规模15' and span.get('bold') == 'true'
    assert span.tail == ' · 2027'
    assert root.find('{*}data/{*}line').get('endShapeId') == 'b'
    notes = [p.text for p in root.findall('{*}note/{*}content/{*}p')]
    assert notes == ['站点15；订单62000。', '年度2027 <核对> & 保留']
    assert source.read_bytes() == original and plan == before
    assert json.loads(Path(result['values_snapshot']).read_text())['lines'] == '15'


def test_missing_fill_decision_stops_at_page_without_partial_xml(tmp_path):
    # Break caught: accepting an incomplete field plan as a prepared deliverable.
    page, _ = fill_page(tmp_path, page=2)
    page['fill_plan']['fields'].pop()
    plan = ready_pages(tmp_path, count=1)
    plan['pages'].append(page)
    plan['values'] = {'lines': '15', 'denom': '62000', 'year': '2027'}
    result = api().prepare_plan(plan, tmp_path)
    assert not result['ok'] and result['next_page'] == 2
    assert result['prepared_pages'] == [1]
    assert not (tmp_path / 'authoring/slide-02.xml').exists()


def test_unknown_shared_value_key_fails_before_current_page_output(tmp_path):
    # Break caught: leaving unresolved factual placeholders in notes or silently
    # substituting an unknown fact with an empty/default value.
    page, _ = fill_page(tmp_path)
    page['notes'] = ['{{missing_fact}}']
    result = api().prepare_plan({'pages': [page], 'values': {'lines': '15', 'denom': '62000', 'year': '2027'}}, tmp_path)
    assert not result['ok'] and result['next_page'] == 1
    assert 'missing_fact' in result['error']
    assert not (tmp_path / 'authoring/slide-01.xml').exists()


def test_publish_failure_stops_and_explicit_cursor_resumes_remaining_pages(tmp_path):
    # Break caught: continuing after a failed write/lint, reporting whole-deck
    # success, dropping full diagnostics, or rerunning earlier successful pages.
    plan = ready_pages(tmp_path)
    first = PublishingCLI(failed_page=2)
    result = api().run_plan(plan, tmp_path, 'D', runner=first)
    assert not result['ok'] and result['next_page'] == 2
    assert result['published_pages'] == [1]
    assert [int(c[c.index('--page') + 1]) for c in first.commands] == [1, 2]
    assert 'x' * 12000 in Path(result['pages'][-1]['execution_report_path']).read_text()
    resumed = PublishingCLI()
    result = api().run_plan(plan, tmp_path, 'D', start_page=2, runner=resumed)
    assert result['ok'] and result['published_pages'] == [2, 3]
    assert [int(c[c.index('--page') + 1]) for c in resumed.commands] == [2, 3]
    assert '--no-lint' not in [v for c in resumed.commands for v in c]


@pytest.mark.parametrize('response', [[], None])
def test_nonobject_publisher_response_stops_with_the_actual_page_cursor(tmp_path, response):
    # Break caught: malformed external CLI output escaping as a traceback,
    # continuing to later pages, or being treated as an acknowledged write.
    plan = ready_pages(tmp_path)
    commands = []
    def malformed(argv, **kwargs):
        commands.append(argv)
        return subprocess.CompletedProcess(argv, 0, json.dumps(response), '')
    result = api().run_plan(plan, tmp_path, 'D', runner=malformed)
    assert not result['ok'] and result['next_page'] == 1
    assert result['published_pages'] == [] and len(commands) == 1


def test_ready_forwards_existing_contracts_and_exception_without_custom_commands(tmp_path):
    # Break caught: executing JSON-supplied commands or arbitrary publish args,
    # or omitting the actual per-page contract/binding/exception CLI arguments.
    plan = ready_pages(tmp_path, 1)
    paths = {}
    for key in ['chart_contract', 'chart_bindings', 'exception_file']:
        path = tmp_path / f'{key}.json'; path.write_text('{}'); paths[key] = str(path)
    plan['pages'][0].update(paths)
    sentinel = tmp_path / 'arbitrary-command-ran'
    plan['pages'][0]['command'] = ['touch', str(sentinel)]
    plan['pages'][0]['publish_args'] = ['--no-lint']
    cli = PublishingCLI()
    result = api().run_plan(plan, tmp_path, 'D', runner=cli)
    assert result['ok'] and not sentinel.exists()
    command = cli.commands[0]
    assert command[1] == str(SCRIPT.with_name('template_publish.py'))
    for key, value in paths.items():
        assert command[command.index('--' + key.replace('_', '-')) + 1] == value
    assert command[command.index('--link') + 1] == 'L4'
    assert '--no-lint' not in command


def test_existing_publisher_registry_reuses_ids_instead_of_readding_pages(tmp_path):
    # Break caught: replacing the single-page publisher/registry with a custom
    # batch writer, or ignoring its existing registered target slide IDs.
    plan = ready_pages(tmp_path, 2)
    fixtures = load(Path(__file__).with_name('test_template_publish.py'), 'publisher_fixtures')
    publisher = fixtures.module()
    writes = []

    def real_publisher_boundary(argv, **kwargs):
        flags = dict(zip(argv[2::2], argv[3::2]))
        page = int(flags['--page'])
        inner = fixtures.Runner(fixtures.READY,
            {'ok': True, 'data': {'slide_id': f'S{page}', 'xml_presentation_id': 'D'}})
        result = publisher.publish(presentation=flags['--presentation'], xml=flags['--xml'],
            page=page, mode=flags['--mode'], work_dir=flags['--work-dir'], link=flags['--link'], runner=inner)
        writes.extend(args for args, _ in inner.calls if 'lark-cli' in args)
        return subprocess.CompletedProcess(argv, 0 if result['ok'] else 1, json.dumps(result), '')

    assert api().run_plan(plan, tmp_path, 'D', runner=real_publisher_boundary)['ok']
    assert api().run_plan(plan, tmp_path, 'D', start_page=2, runner=real_publisher_boundary)['ok']
    assert sum('+add-slide' in c for c in writes) == 2
    updates = [c for c in writes if '+update-slide' in c]
    assert len(updates) == 1 and updates[0][updates[0].index('--slide-id') + 1] == 'S2'
    registry = json.loads((tmp_path / 'published-pages.json').read_text())
    assert [(r['page'], r['slide_id']) for r in registry['pages']] == [(1, 'S1'), (2, 'S2')]


def test_migration_does_not_override_original_notes_from_plan(tmp_path):
    # Break caught: letting new lecture text silently overwrite factual original
    # notes in a visual-only migration.
    plan, _, _ = migration_plan(tmp_path)
    plan['pages'][0]['notes'] = ['Different lecture']
    result = api().prepare_plan(plan, tmp_path)
    assert not result['ok'] and result['next_page'] == 1
    assert not (tmp_path / 'authoring/slide-01.xml').exists()


def test_prepare_never_overwrites_different_existing_output_or_outside_work(tmp_path):
    # Break caught: destructive regeneration during resume or writing to a
    # source/external location through a JSON output field.
    plan = ready_pages(tmp_path, 1)
    out = tmp_path / 'authoring/slide-01.xml'; out.parent.mkdir(); out.write_text('Existing original')
    result = api().prepare_plan(plan, tmp_path)
    assert not result['ok'] and out.read_text() == 'Existing original'
    plan['pages'][0]['output'] = '../must-not-create.xml'
    result = api().prepare_plan(plan, tmp_path)
    assert not result['ok'] and not (tmp_path.parent / 'must-not-create.xml').exists()


@pytest.mark.parametrize('field_plan', [None, []])
def test_malformed_fill_plan_returns_current_stop_cursor(tmp_path, field_plan):
    # Break caught: a non-object authored field plan escaping as a traceback
    # instead of the same prepare stop/result used for actual composition errors.
    page, _ = fill_page(tmp_path)
    page['fill_plan'] = field_plan
    result = api().prepare_plan({'pages': [page]}, tmp_path)
    assert not result['ok'] and result['next_page'] == 1
    assert not (tmp_path / 'authoring/slide-01.xml').exists()


def test_xml_and_generated_contract_cannot_replace_each_other(tmp_path):
    # Break caught: a dictionary of outputs silently losing the contract when
    # an authored migration contract path aliases the XML path.
    plan, _, _ = migration_plan(tmp_path)
    plan['pages'][0]['migration_contract'] = 'authoring/slide-01.xml'
    result = api().prepare_plan(plan, tmp_path)
    assert not result['ok'] and result['next_page'] == 1
    assert not (tmp_path / 'authoring/slide-01.xml').exists()


def test_cli_prepare_emits_real_page_artifacts_without_publishing(tmp_path):
    # Break caught: CLI wiring that does not run the real local preparation, or
    # a prepare command unexpectedly crossing the publishing boundary.
    plan = ready_pages(tmp_path, 1)
    path = tmp_path / 'plan.json'; path.write_text(json.dumps(plan))
    api()
    process = subprocess.run([sys.executable, str(SCRIPT), 'prepare', '--plan', str(path),
                              '--work-dir', str(tmp_path)], capture_output=True, text=True)
    assert process.returncode == 0, process.stderr
    result = json.loads(process.stdout)
    assert result['ok'] and result['prepared_pages'] == [1]
    assert ET.parse(result['pages'][0]['xml_path']).find('.//{*}p').text == 'Page 1'
    assert not (tmp_path / 'published-pages.json').exists()
