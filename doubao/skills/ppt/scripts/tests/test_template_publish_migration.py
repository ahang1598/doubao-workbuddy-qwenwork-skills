"""Migration conservation runs before the existing external publishing boundary."""
import importlib.util
import json
from pathlib import Path

import pytest
from lxml import etree as ET


def helper(name):
    path = Path(__file__).with_name(name+'.py')
    spec = importlib.util.spec_from_file_location('migration_fixture_'+name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def migration_inputs(tmp_path):
    mf = helper('test_template_migration')
    source, frame = mf.inputs(tmp_path)
    result = mf.api().compose_migration(source, frame,
        frame_ids=['background'], target_region=[40, 100, 880, 390])
    authored = tmp_path/'authoring/slide-01.xml'; authored.parent.mkdir()
    authored.write_text(result['xml'])
    contract = tmp_path/'manifest/migration-contracts/page-01.json'
    contract.parent.mkdir(parents=True); contract.write_text(json.dumps(result['contract']))
    return authored, contract


def test_l8_without_a_source_bound_migration_contract_never_publishes(tmp_path):
    pf = helper('test_template_publish')
    runner = pf.Runner(pf.READY, pf.SUCCESS)
    result = pf.invoke(tmp_path, runner, link='L8')
    assert result['status'] == 'migration_contract_blocked'
    assert not runner.calls
    assert not (tmp_path/'published-pages.pending.json').exists()


def test_valid_migration_contract_is_bound_to_payload_report_intent_and_registry(tmp_path):
    pf = helper('test_template_publish')
    authored, contract = migration_inputs(tmp_path)
    def written(args, kwargs):
        intent = json.loads((tmp_path/'published-pages.pending.json').read_text())
        assert intent.get('migration_contract', {}).get('path') == str(contract)
        assert '167 out of 173' in kwargs['input']
        assert 'Bahrain; Benin; Burundi (30)' in kwargs['input']
        return pf.SUCCESS
    result = pf.module().publish(validation_policy='strict', presentation='D', xml=authored, page=1,
        mode='component_reuse', work_dir=tmp_path, link='L8',
        runner=pf.Runner(pf.READY, written))
    assert result['ok']
    report = json.loads(Path(result['report_path']).read_text())
    assert report['migration_contract']['ok']
    row = json.loads((tmp_path/'published-pages.json').read_text())['pages'][0]
    assert row['migration_contract']['path'] == str(contract)
    assert row['migration_contract']['source_sha256'] == json.loads(contract.read_text())['source']['sha256']


@pytest.mark.parametrize('change', ['number', 'rows', 'note'])
def test_l8_mutated_statistics_country_rows_and_blank_notes_stop_before_write(tmp_path, change):
    pf = helper('test_template_publish')
    authored, _ = migration_inputs(tmp_path)
    root = ET.fromstring(authored.read_bytes())
    if change == 'number':
        authored.write_text(authored.read_text().replace('167 out of 173', '168 out of 173'))
    elif change == 'rows':
        table = root.find('{*}data/{*}table')
        for row in list(table): table.remove(row)
        for i in range(12):
            tr = ET.SubElement(table, '{https://www.larkoffice.com/sml/2.0}tr')
            ET.SubElement(tr, '{https://www.larkoffice.com/sml/2.0}td').text = 'Different country '+str(i)
        authored.write_bytes(ET.tostring(root))
    else:
        ET.SubElement(root.find('{*}note'), '{https://www.larkoffice.com/sml/2.0}content').text = 'New target lecture script'
        authored.write_bytes(ET.tostring(root))
    runner = pf.Runner(pf.READY, pf.SUCCESS)
    result = pf.module().publish(validation_policy='strict', presentation='D', xml=authored, page=1,
        mode='component_reuse', work_dir=tmp_path, link='L8', runner=runner)
    assert result['status'] == 'migration_contract_blocked'
    assert not runner.calls
    assert not (tmp_path/'published-pages.pending.json').exists()
    report = json.loads(Path(result['report_path']).read_text())
    assert report['migration_contract']['errors']
