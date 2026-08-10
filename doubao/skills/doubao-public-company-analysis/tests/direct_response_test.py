#!/usr/bin/env python3
import subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
def run(path,*extra):return subprocess.run([sys.executable,str(ROOT/"scripts/lint_direct_response.py"),str(path),*extra],capture_output=True,text=True)
def main():
    with tempfile.TemporaryDirectory() as temp:
        temp=Path(temp)
        good=temp/"good.md";good.write_text("依据公司公告，收入为100亿元（https://example.com/filing）。\n\n本内容仅供研究，不构成投资建议。",encoding="utf-8")
        assert run(good).returncode==0
        marker=temp/"marker.md";marker.write_text("收入增长 {fact:revenue}。",encoding="utf-8")
        assert run(marker).returncode!=0
        number=temp/"number.md";number.write_text("毛利率为35%，没有来源。",encoding="utf-8")
        assert run(number).returncode!=0
        route=temp/"route.md";route.write_text("当前请求不适用，请使用相邻任务。\n"+"扩写"*500,encoding="utf-8")
        assert run(route,"--route-only").returncode!=0
    print("PASS company-analysis direct response");return 0
if __name__=="__main__":raise SystemExit(main())
