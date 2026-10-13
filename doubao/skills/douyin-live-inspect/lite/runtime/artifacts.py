"""Pinned HTTPS artifacts. No network manifests, global installs or executable install scripts."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import wave
import zipfile

from runtime.platform_support import file_lock, private_directory

CATALOG = Path(__file__).resolve().parents[1] / 'config/runtime-artifacts.json'
SUPPORTED = {'darwin-arm64', 'darwin-x64', 'linux-x64', 'win32-x64'}

class PreparationError(RuntimeError):
    def __init__(self, code, stage, retryable=False):
        self.code, self.stage, self.retryable = code, stage, retryable
        super().__init__(code)
    def public(self):
        return {'code':self.code, 'stage':self.stage, 'retryable':self.retryable}


def platform_key():
    machine = platform.machine().lower()
    arch = {'amd64':'x64','x86_64':'x64','aarch64':'arm64','arm64':'arm64'}.get(machine, machine)
    key = f'{sys.platform}-{arch}'
    if key not in SUPPORTED: raise PreparationError('ASR_PLATFORM_UNSUPPORTED','platform')
    return key


def cache_root():
    base = os.environ.get('INSPECT_MODEL_CACHE_DIR')
    if base: return Path(base).expanduser().resolve()
    if sys.platform == 'win32': base = Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'InspectLite/Cache'
    elif sys.platform == 'darwin': base = Path.home() / 'Library/Caches/InspectLite'
    else: base = Path(os.environ.get('XDG_CACHE_HOME', Path.home()/'.cache')) / 'inspect-lite'
    return Path(base).resolve()


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024), b''): h.update(chunk)
    return h.hexdigest()


def relative_path(value):
    if not isinstance(value,str) or not value or '\\' in value or ':' in value or '\x00' in value:
        raise PreparationError('ARTIFACT_PATH_INVALID','extract')
    p = PurePosixPath(value)
    if p.is_absolute() or any(x in ('..','.') for x in value.split('/')):
        raise PreparationError('ARTIFACT_PATH_INVALID','extract')
    # Windows reserved names and normalization must not alias different archive entries.
    if any(x.endswith((' ','.')) or re.fullmatch(r'(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?',x) for x in p.parts):
        raise PreparationError('ARTIFACT_PATH_INVALID','extract')
    return p


def validate_spec(spec):
    if not isinstance(spec,dict): raise PreparationError('ARTIFACT_NOT_CONFIGURED','manifest')
    if not re.fullmatch('[A-Za-z0-9._-]+',str(spec.get('version',''))) or spec.get('version') in ('.','..'):
        raise PreparationError('ARTIFACT_MANIFEST_INVALID','manifest')
    u = urllib.parse.urlsplit(spec.get('url',''))
    if u.scheme != 'https' or not u.hostname or u.username or u.password or u.query or u.fragment:
        raise PreparationError('ARTIFACT_URL_INVALID','manifest')
    if not re.fullmatch('[a-f0-9]{64}',str(spec.get('sha256',''))): raise PreparationError('ARTIFACT_MANIFEST_INVALID','manifest')
    for key in ('bytes','unpacked_bytes','max_files'):
        if type(spec.get(key)) is not int or spec[key]<=0: raise PreparationError('ARTIFACT_MANIFEST_INVALID','manifest')
    files=spec.get('files')
    if not isinstance(files,list) or not files or len(files)>spec['max_files']: raise PreparationError('ARTIFACT_MANIFEST_INVALID','manifest')
    seen=set()
    for f in files:
        name=str(relative_path(f['path']))
        if name.casefold() in seen or type(f.get('bytes')) is not int or f['bytes']<0 or not re.fullmatch('[a-f0-9]{64}',str(f.get('sha256',''))):
            raise PreparationError('ARTIFACT_MANIFEST_INVALID','manifest')
        seen.add(name.casefold())
    if sum(f['bytes'] for f in files)>spec['unpacked_bytes']: raise PreparationError('ARTIFACT_MANIFEST_INVALID','manifest')
    for name in spec.get('executables',[]):
        if str(relative_path(name)).casefold() not in seen: raise PreparationError('ARTIFACT_MANIFEST_INVALID','manifest')
    for entry in spec.get('entrypoints',{}).values():
        if str(relative_path(entry)).casefold() not in seen: raise PreparationError('ARTIFACT_MANIFEST_INVALID','manifest')
    return spec


def load_catalog():
    # An operator-supplied local catalog is a trust root, never downloaded from a URL.
    path=Path(os.environ.get('INSPECT_ARTIFACT_CATALOG',str(CATALOG)))
    try:
        if path.stat().st_size>2*1024*1024: raise ValueError('catalog too large')
        value=json.loads(path.read_text(encoding='utf-8'))
    except (OSError,ValueError): raise PreparationError('ARTIFACT_MANIFEST_INVALID','manifest') from None
    if value.get('schema_version')!=1: raise PreparationError('ARTIFACT_MANIFEST_INVALID','manifest')
    return value


def destination(component,key,spec):
    return cache_root()/component/spec['version']/key/spec['sha256']


def verify_files(root,spec):
    root=Path(root)
    if root.is_symlink(): raise PreparationError('ARTIFACT_CACHE_INVALID','verify')
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()} - {'.ready.json'}
    if actual!={f['path'] for f in spec['files']} or any(p.is_symlink() for p in root.rglob('*')):
        raise PreparationError('ARTIFACT_CACHE_INVALID','verify')
    for f in spec['files']:
        p=root.joinpath(*relative_path(f['path']).parts)
        if p.is_symlink() or root.resolve() not in p.resolve().parents or not p.is_file() or p.stat().st_size!=f['bytes'] or sha256(p)!=f['sha256']:
            raise PreparationError('ARTIFACT_FILE_INVALID','verify')
    for name in spec.get('executables',[]):
        if os.name!='nt' and not os.access(root/name,os.X_OK): raise PreparationError('ARTIFACT_FILE_INVALID','verify')


def cache_valid(root,spec):
    try:
        marker=json.loads((root/'.ready.json').read_text(encoding='utf-8'))
        if marker != {'version':spec['version'],'sha256':spec['sha256']}: return False
        verify_files(root,spec)
        return True
    except (OSError,ValueError,PreparationError): return False


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        target=urllib.parse.urlsplit(newurl)
        if target.scheme!='https' or target.hostname!=urllib.parse.urlsplit(req.full_url).hostname or target.username or target.password or target.query:
            raise PreparationError('ARTIFACT_REDIRECT_REJECTED','download')
        return super().redirect_request(req,fp,code,msg,headers,newurl)


def download(spec,path,progress=None):
    for attempt in range(3):
        try:
            deadline=time.monotonic()+600
            with urllib.request.build_opener(SafeRedirect()).open(spec['url'],timeout=30) as response, path.open('wb') as out:
                if response.status!=200: raise PreparationError('ARTIFACT_HTTP_ERROR','download')
                total=0
                while True:
                    chunk=response.read(1024*1024)
                    if not chunk: break
                    total+=len(chunk)
                    if total>spec['bytes']: raise PreparationError('ARTIFACT_SIZE_INVALID','download')
                    if time.monotonic()>deadline: raise TimeoutError()
                    out.write(chunk)
                    if progress: progress(stage='download',bytes_received=total,bytes_total=spec['bytes'],attempt=attempt+1)
            if total!=spec['bytes'] or sha256(path)!=spec['sha256']:
                raise PreparationError('ARTIFACT_HASH_INVALID','verify')
            return
        except urllib.error.HTTPError as e:
            retryable=e.code in (408,429,500,502,503,504)
            error=PreparationError('ARTIFACT_HTTP_ERROR','download',retryable)
        except (urllib.error.URLError,TimeoutError,ConnectionError):
            error=PreparationError('ARTIFACT_NETWORK_ERROR','download',True)
        except OSError:
            raise PreparationError('ARTIFACT_DISK_ERROR','download') from None
        path.unlink(missing_ok=True)
        if not error.retryable or attempt==2: raise error from None
        time.sleep(2**attempt)


def unpack(archive,root,spec):
    expected={f['path']:f for f in spec['files']}
    seen=set(); count=0; total=0
    def accept(name,size,directory,regular):
        nonlocal count,total
        p=relative_path(name.rstrip('/')); canonical=str(p)
        count+=1
        if count>spec['max_files'] or not regular: raise PreparationError('ARTIFACT_ARCHIVE_INVALID','extract')
        target=root.joinpath(*p.parts)
        if directory:
            target.mkdir(parents=True,exist_ok=True)
            return None
        if canonical not in expected or canonical.casefold() in seen or size!=expected[canonical]['bytes']:
            raise PreparationError('ARTIFACT_ARCHIVE_INVALID','extract')
        seen.add(canonical.casefold());total+=size
        if total>spec['unpacked_bytes']: raise PreparationError('ARTIFACT_ARCHIVE_INVALID','extract')
        target.parent.mkdir(parents=True,exist_ok=True)
        return target
    def write(source,target,size):
        with target.open('xb') as out:
            remaining=size
            while remaining:
                block=source.read(min(1024*1024,remaining))
                if not block: raise PreparationError('ARTIFACT_ARCHIVE_INVALID','extract')
                out.write(block);remaining-=len(block)
        target.chmod(0o755 if str(target.relative_to(root)).replace('\\','/') in spec.get('executables',[]) else 0o600)
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as z:
            for item in z.infolist():
                mode=item.external_attr>>16
                target=accept(item.filename,item.file_size,item.is_dir(),not stat.S_ISLNK(mode) and (stat.S_IFMT(mode) in (0,stat.S_IFREG,stat.S_IFDIR)))
                if target:
                    with z.open(item) as source: write(source,target,item.file_size)
    else:
        with tarfile.open(archive,'r:*') as tar:
            for item in tar:
                target=accept(item.name,item.size,item.isdir(),item.isfile() or item.isdir())
                if target:
                    with tar.extractfile(item) as source: write(source,target,item.size)
    if len(seen)!=len(expected): raise PreparationError('ARTIFACT_ARCHIVE_INVALID','extract')
    verify_files(root,spec)


def ensure_artifact(component,key,spec,smoke,progress=None):
    validate_spec(spec)
    root=destination(component,key,spec)
    private_directory(cache_root())
    lockdir=private_directory(cache_root()/'.locks')
    with file_lock(lockdir/(component+'-'+key+'-'+spec['sha256']+'.lock')):
        if cache_valid(root,spec): return root,'cache'
        root.parent.mkdir(parents=True,exist_ok=True)
        required=spec['bytes']+spec['unpacked_bytes']+16*1024*1024
        if shutil.disk_usage(root.parent).free<required: raise PreparationError('ARTIFACT_DISK_FULL','download')
        with tempfile.TemporaryDirectory(prefix='.prepare-',dir=root.parent) as tmp:
            temp=Path(tmp); archive=temp/'archive.part'; stage=temp/'runtime';stage.mkdir()
            if progress: progress(stage="download")
            if progress: download(spec,archive,progress=progress)
            else: download(spec,archive)
            if progress: progress(stage="verify_extract", download_completed_at=time.time(),
                                  download_completed_monotonic=time.monotonic())
            try: unpack(archive,stage,spec)
            except (tarfile.TarError,zipfile.BadZipFile,EOFError): raise PreparationError('ARTIFACT_ARCHIVE_INVALID','extract') from None
            if progress: progress(stage="smoke")
            smoke(stage,spec)
            (stage/'.ready.json').write_text(json.dumps({'version':spec['version'],'sha256':spec['sha256']}))
            if root.exists():
                # Only this exact corrupted version is replaced; other versions remain untouched.
                shutil.rmtree(root)
            stage.rename(root)
    return root,'download'


def binary_ok(path,name):
    try:
        p=subprocess.run([str(path), '-version'],capture_output=True,text=True,timeout=10)
        return p.returncode == 0
    except (OSError,ValueError,KeyError,PreparationError,subprocess.SubprocessError): return False


def runtime_smoke(root):
    from runtime.local_asr import LocalASR
    bridge=LocalASR()
    try:
        with tempfile.TemporaryDirectory(prefix='inspect-asr-smoke-') as temp:
            p=Path(temp)/'silence.wav'
            with wave.open(str(p),'wb') as audio:
                audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(16000);audio.writeframes(b'\0'*3200)
            metadata=bridge.request('initialize',runtime_root=str(root),task_root=temp,timeout=60)
            if metadata.get('asr_mode')!='single_pass': raise PreparationError('ASR_SINGLE_PASS_REQUIRED','smoke')
            result=bridge.request('transcribe',audio_path=str(p),timeout=60)
            if result.get('dropped_audio_ms')!=0 or result.get('subtitles')!=[]: raise PreparationError('ASR_SMOKE_FAILED','smoke')
    finally: bridge.close()


def prepare(*, task=None, install=True, common_only=False, model_only=False, progress=None):
    """Read-only when install=False. Frozen task specs take precedence over the current catalog."""
    result={'ready':False,'backend':'local','issues':[],'binaries':{},'artifacts':{},'next_action':'prepare-runtime'}
    task=task or {}
    try:
        key=platform_key();result['platform']=key
        catalog = {} if 'artifact_specs' in task else load_catalog()
        specs = task['artifact_specs'] if 'artifact_specs' in task else {**catalog.get('shared', {}), **catalog.get('platforms', {}).get(key, {})}
        specs = {k: v for k, v in specs.items() if k != 'node'}
        result['artifact_specs']=specs
        if model_only: result['binaries']=task.get('runtime_binaries',{})
        for component,names in ([] if model_only else [('ffmpeg',['ffmpeg','ffprobe'])]):
            paths={name:task.get('runtime_binaries',{}).get(name+'_bin',task.get(name+'_bin')) or shutil.which(name) for name in names}
            if not all(p and binary_ok(p,name) for name,p in paths.items()):
                spec=specs.get(component)
                if not spec: raise PreparationError('ARTIFACT_NOT_CONFIGURED',component)
                validate_spec(spec)
                def smoke(folder,spec):
                    if not all(binary_ok(folder/spec['entrypoints'][n],n) for n in names): raise PreparationError('ARTIFACT_SMOKE_FAILED',component)
                if install: root,source=ensure_artifact(component,key,spec,smoke)
                else:
                    root=destination(component,key,spec);source='cache'
                    if not cache_valid(root,spec): raise PreparationError('ARTIFACT_CACHE_MISSING',component)
                paths={n:str(root/spec['entrypoints'][n]) for n in names}
                result['artifacts'][component]={'version':spec['version'],'sha256':spec['sha256'],'source':source}
            result['binaries'].update({n+'_bin':str(p) for n,p in paths.items()})
        if common_only:
            result['ready']=True
            return result
        from runtime.asr_worker import dependencies
        from runtime.asr_model import ModelError
        try: dependencies()
        except ModelError as error: raise PreparationError(error.code, 'python-dependencies') from None
        explicit=task.get('asr_runtime_root') or os.environ.get('LOCAL_ASR_RUNTIME_ROOT')
        if explicit:
            root=Path(explicit)
            # A managed cache may be recreated from the task's frozen specification.
            spec=specs.get('asr')
            if spec and root==destination('asr',key,validate_spec(spec)) and not cache_valid(root,spec):
                if not install: raise PreparationError('ARTIFACT_CACHE_MISSING','asr')
                root,source=ensure_artifact('asr',key,spec,lambda r,s:runtime_smoke(r), **({'progress':progress} if progress else {}))
        else:
            spec=specs.get('asr')
            if not spec: raise PreparationError('ARTIFACT_NOT_CONFIGURED','asr')
            validate_spec(spec)
            if install: root,source=ensure_artifact('asr',key,spec,lambda r,s:runtime_smoke(r), **({'progress':progress} if progress else {}))
            else:
                root=destination('asr',key,spec);source='cache'
                result['asr_runtime_root']=str(root)
                if not cache_valid(root,spec): raise PreparationError('ARTIFACT_CACHE_MISSING','asr')
            result['artifacts']['asr']={'version':spec['version'],'sha256':spec['sha256'],'source':source}
        from runtime.local_asr import doctor
        checked=doctor(str(root),require_single_pass=True,binaries=result['binaries'], **({'model_only':True} if model_only else {}))
        result.update(runtime=checked['runtime'],asr_runtime_root=str(root),artifact_specs=specs)
        result['issues'].extend(checked['issues'])
        result['ready']=checked['ready']
        if task.get('asr_runtime') and task['asr_runtime']!=result['runtime']:
            result['ready']=False;result['issues'].append({'code':'ASR_RUNTIME_INCOMPATIBLE','stage':'identity','retryable':False})
    except PreparationError as e: result['issues'].append(e.public())
    except (OSError,ValueError,KeyError,TypeError,RuntimeError,subprocess.SubprocessError):
        result['issues'].append({'code':'RUNTIME_PREPARATION_FAILED','stage':'prepare','retryable':False})
    if result['ready']: result['next_action']='start'
    return result
