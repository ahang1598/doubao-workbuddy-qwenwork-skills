"""Generate synthetic guide fixtures and verify the actual CLI output, without a website."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent/'scripts'))
from run_text_format_smoke import create
from test_text_guide import make_pos, replace_parts
from test_uof_marker import make_uof_sample, EXTENSIONS as UOF_EXTENSIONS
from decorators.uof_decorator import UOF2, UOF3
from decorators.pos_decorator import inspect_pos_visible

# Literal list from guide 5.1; kept separate from the production dispatch table.
EXTENSIONS = ('docx','pptx','xlsx','dotx','xltx','potx','uot','uott','uos','uost','uop','uopt','pdf','ofd','md','xmind','posm','posf')


def cli(skill_root, path, flag=None):
    command = [sys.executable, str(skill_root/'scripts/main.py'), str(path)]
    if flag: command.append(flag)
    return subprocess.run(command,
                          capture_output=True, text=True, encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output_dir',type=Path)
    parser.add_argument('--skill-root',type=Path,default=HERE.parent)
    parser.add_argument('--with-visible',action='store_true',help='Add visible marks to all eighteen formats')
    args=parser.parse_args()
    output=args.output_dir.resolve();output.mkdir(parents=True,exist_ok=True)
    target=args.skill_root.resolve()
    cases=[]
    for extension in EXTENSIONS:
        path=output/('guide.'+extension)
        make_pos(path) if extension in ('posm','posf') else create(path)
        cases.append((path, 'guide-5.1'))
    for extension in UOF_EXTENSIONS:
        path=make_uof_sample(output/('uof-2021'+extension))
        with zipfile.ZipFile(path) as z:parts={n:z.read(n) for n in z.namelist()}
        for name,data in parts.items():
            if name.endswith('.xml'):
                for key,namespace in UOF2.items():data=data.replace(namespace.encode(),UOF3[key].encode())
                parts[name]=data
        replace_parts(path,parts)
        cases.append((path, 'uof-2021-structural-variant'))
    rows=[]
    for path,kind in cases:
        visible = args.with_visible
        marked=cli(target,path,None if visible else '--skip-visible')
        before=hashlib.sha256(path.read_bytes()).hexdigest()
        checked=cli(target,path,'--verify')
        after=hashlib.sha256(path.read_bytes()).hexdigest()
        records=[json.loads(line) for line in checked.stdout.splitlines() if line.startswith('{')]
        metadata=records[0] if records else None
        passed=(marked.returncode==0 and checked.returncode==0 and before==after
                and metadata and metadata.get('guide_storage_verified') is True)
        visible_check = None
        if visible and path.suffix.lower() in ('.posm', '.posf'):
            try:
                visible_check = inspect_pos_visible(path)
            except Exception as error:
                visible_check = {'visible_storage_verified': False, 'error': str(error)}
                passed = False
        rows.append({'file':path.name,'fixture':kind,'sha256':after,'passed':bool(passed),
                     'visible_mark_requested':visible,'pos_visible_check':visible_check,'storage_check':metadata,'mark_stdout':marked.stdout,'mark_stderr':marked.stderr,
                     'verify_stdout':checked.stdout,'verify_stderr':checked.stderr})
    version=subprocess.run([sys.executable,str(target/'scripts/main.py'),'--version'],capture_output=True,text=True)
    report={'scope':'TC260-PG-20258A V1.0-202508 hidden text metadata storage',
            'skill_version':version.stdout.strip(),'format_count':len(EXTENSIONS),
            'fixture_count':len(rows),'passed':all(r['passed'] for r in rows),'results':rows,
            'limits':['Synthetic container/structure fixtures; not native editor rendering validation.',
                      'POSM/POSF visible checks inspect native properties and text; no editor rendering claim.',
                      'No GCMark or other online acceptance claim.',
                      'No verification of provider registration or ReservedCode signatures.']}
    (output/'guide-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='results'},ensure_ascii=False,indent=2))
    if not report['passed']:raise SystemExit(1)


if __name__=='__main__':main()
