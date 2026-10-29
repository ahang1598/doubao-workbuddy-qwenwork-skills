#!/usr/bin/env python3
"""Reader-facing event reports accept natural structure and reject machine labels."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent


def main():
    runtime=json.loads((ROOT/'config/runtime.json').read_text(encoding='utf-8'))
    assert all(not mode['required_sections'] for mode in runtime['modes'].values())
    with tempfile.TemporaryDirectory() as raw:
        directory=Path(raw)
        facts=directory/'facts.json'
        facts.write_text(json.dumps({'meta':{'mode':'快速判断'},'claims':[]},ensure_ascii=False),encoding='utf-8')
        report=directory/'report.md'
        report.write_text('# 某项政策的影响\n\n政策仍在征求意见。若正式实施，相关企业的合规成本可能上升；目前不能据草案计算利润损失。',encoding='utf-8')
        command=[sys.executable,str(ROOT/'scripts/lint_report.py'),str(report),str(facts)]
        good=subprocess.run(command,capture_output=True,text=True)
        assert good.returncode==0,good.stdout+good.stderr
        report.write_text('# 某项政策的影响\n\n税率上升[一手·发布方·草案·2026-01-01]。',encoding='utf-8')
        bad=subprocess.run(command,capture_output=True,text=True)
        assert bad.returncode!=0
    print('PASS natural event report')


if __name__=='__main__':
    raise SystemExit(main())
