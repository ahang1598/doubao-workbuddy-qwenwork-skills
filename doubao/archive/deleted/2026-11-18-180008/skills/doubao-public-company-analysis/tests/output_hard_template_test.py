#!/usr/bin/env python3
"""A focused company report passes without a fixed outline or audit labels."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent


def main():
    runtime=json.loads((ROOT/'config/runtime.json').read_text(encoding='utf-8'))
    assert all(not m['required_sections'] for m in runtime['modes'].values())
    with tempfile.TemporaryDirectory() as tmp:
        tmp=Path(tmp)
        facts=tmp/'facts.json'
        facts.write_text(json.dumps({'meta':{'mode':'聚焦分析'},'claims':[]},ensure_ascii=False),encoding='utf-8')
        report=tmp/'report.md'
        command=[sys.executable,str(ROOT/'scripts/lint_report.py'),str(report),str(facts)]
        report.write_text('# 现金转化\n\n应收款增长快于收入，先核实账龄和回款，再判断增长质量。',encoding='utf-8')
        result=subprocess.run(command,capture_output=True,text=True)
        assert result.returncode==0,result.stdout+result.stderr
        report.write_text('# 现金转化\n\n应收款增长快于收入[一手·财报·日期]。',encoding='utf-8')
        result=subprocess.run(command,capture_output=True,text=True)
        assert result.returncode!=0
        report.write_text('# 现金转化\n\nFCF等于经营利润加非现金项目再减资本开支。',encoding='utf-8')
        result=subprocess.run(command,capture_output=True,text=True)
        assert result.returncode!=0
    print('PASS flexible company report and financial safeguards')


if __name__=='__main__':
    raise SystemExit(main())
