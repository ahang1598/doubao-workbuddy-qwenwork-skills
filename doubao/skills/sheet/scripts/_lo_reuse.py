"""Conservative reuse of a previously produced local LibreOffice output.

Receipts live beside outputs; no global workbook cache. A receipt describes only
one unchanged source, request, engine and output. Failures are never cached.
"""
from contextlib import contextmanager, nullcontext
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile
import time
import uuid
import zipfile
from xml.etree import ElementTree

# Only known deterministic formulas qualify. Unknown/add-in functions and volatile
# functions must be executed again; false misses cost time, false hits cost data.
FUNCTIONS = set("ABS AND AVERAGE AVERAGEIF AVERAGEIFS CEILING CHOOSE CLEAN CONCAT CONCATENATE "
                "COUNT COUNTA COUNTBLANK COUNTIF COUNTIFS DATE DAY DAYS EDATE EOMONTH "
                "EXACT FIND FLOOR HLOOKUP HOUR IF IFERROR IFNA IFS INDEX INT IRR ISBLANK "
                "ISERROR ISNA ISNUMBER ISTEXT LEFT LEN LN LOG LOWER MATCH MAX MAXIFS "
                "MEDIAN MID MIN MINIFS MINUTE MOD MONTH NA NOT NPER NPV OR PMT PPMT IPMT POWER PV "
                "RATE REPLACE RIGHT ROUND ROUNDDOWN ROUNDUP ROW SEARCH SECOND SIGN SQRT "
                "STDEV STDEV.P STDEV.S SUBSTITUTE SUM SUMIF SUMIFS SUMPRODUCT TEXT "
                "TIME TRIM UPPER VALUE VLOOKUP XIRR XLOOKUP XNPV YEAR".split())


def digest_file(path):
    result = hashlib.sha256()
    context = nullcontext(path) if hasattr(path, 'read') else Path(path).open('rb')
    with context as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()


def _file_identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


@contextmanager
def output_file(destination, mode=0o666):
    destination = Path(destination)
    temporary_flag = getattr(os, 'O_TMPFILE', None)
    directory_flag = getattr(os, 'O_DIRECTORY', None)
    directory, descriptor = None, None
    if temporary_flag is not None and directory_flag is not None and Path('/proc/self/fd').is_dir():
        directory = os.open(str(destination.parent), os.O_RDONLY | directory_flag)
        try:
            descriptor = os.open('.', os.O_RDWR | temporary_flag, mode, dir_fd=directory)
        except OSError as exc:
            os.close(directory)
            directory = None
            if exc.errno not in (errno.ENOTSUP, errno.EOPNOTSUPP, errno.EINVAL, errno.ENOSYS):
                raise
    if descriptor is None:
        with _private_output_file(destination, mode) as output:
            yield output
        return
    try:
        with os.fdopen(descriptor, 'w+b') as stream:
            yield stream, directory
    finally:
        os.close(directory)


def _owns_path(path, identity):
    try:
        current = path.lstat()
        return (current.st_dev, current.st_ino, stat.S_IFMT(current.st_mode)) == (
            identity.st_dev, identity.st_ino, stat.S_IFMT(identity.st_mode))
    except FileNotFoundError:
        return False


@contextmanager
def _private_output_file(destination, mode):
    directory = Path(tempfile.mkdtemp(prefix='.sheet-private-', dir=str(destination.parent)))
    directory_identity = directory.lstat()
    path = directory / 'output'
    identity = None
    try:
        descriptor = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_RDWR | getattr(os, 'O_NOFOLLOW', 0), mode)
        with os.fdopen(descriptor, 'w+b') as stream:
            identity = os.fstat(descriptor)
            if not _owns_path(directory, directory_identity):
                raise OSError('private output directory was replaced')
            yield stream, (directory, directory_identity, identity)
    finally:
        if _owns_path(directory, directory_identity):
            if identity is not None and _owns_path(path, identity):
                path.unlink()
            try:
                directory.rmdir()
            except OSError:
                pass


def publish_output(stream, directory, destination, overwrite=False):
    destination = Path(destination)
    stream.flush()
    os.fsync(stream.fileno())
    if isinstance(directory, tuple):
        private, directory_identity, identity = directory
        path = private / 'output'
        if not _owns_path(private, directory_identity) or not _owns_path(path, identity):
            raise OSError('private output staging was replaced; no file was published')
        stream.close()
        if overwrite:
            os.replace(str(path), str(destination))
        else:
            os.link(str(path), str(destination))
        return
    source = '/proc/self/fd/{}'.format(stream.fileno())
    if not overwrite:
        os.link(source, destination.name, dst_dir_fd=directory, follow_symlinks=True)
        return
    staging_name = '.sheet-publish-' + uuid.uuid4().hex
    os.mkdir(staging_name, 0o700, dir_fd=directory)
    staging = os.open(staging_name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
    identity = os.fstat(stream.fileno())
    staging_identity = os.fstat(staging)
    try:
        os.link(source, 'output', dst_dir_fd=staging, follow_symlinks=True)
        current = os.stat('output', dir_fd=staging, follow_symlinks=False)
        if (current.st_dev, current.st_ino) != (identity.st_dev, identity.st_ino):
            raise OSError('private output staging was replaced; no file was published')
        os.replace('output', destination.name, src_dir_fd=staging, dst_dir_fd=directory)
    finally:
        try:
            current = os.stat('output', dir_fd=staging, follow_symlinks=False)
            if (current.st_dev, current.st_ino) == (identity.st_dev, identity.st_ino):
                os.unlink('output', dir_fd=staging)
        except FileNotFoundError:
            pass
        finally:
            os.close(staging)
        try:
            current = os.stat(staging_name, dir_fd=directory, follow_symlinks=False)
            if (current.st_dev, current.st_ino) == (staging_identity.st_dev, staging_identity.st_ino):
                os.rmdir(staging_name, dir_fd=directory)
        except OSError:
            pass


def publish_new_output(source, destination):
    with output_file(destination) as (stream, directory):
        with Path(source).open('rb') as data:
            shutil.copyfileobj(data, stream)
        publish_output(stream, directory, destination)


class FingerprintUnavailable(RuntimeError):
    def __init__(self, reason):
        self.reason = reason
        super().__init__(reason)


def _loader_roots(roots, environment):
    for name in ('DYLD_LIBRARY_PATH', 'DYLD_INSERT_LIBRARIES', 'URE_BOOTSTRAP'):
        if environment.get(name):
            raise FingerprintUnavailable('loader_configuration_unsupported')
    search_path = environment.get('LD_LIBRARY_PATH')
    if search_path:
        for value in re.split(r'[:;]', search_path):
            if not value or '$' in value or not Path(value).is_absolute():
                raise FingerprintUnavailable('loader_search_path_unsupported')
            roots.append(Path(value))
    preload = environment.get('LD_PRELOAD')
    if preload:
        from excel_lo_runtime import _SHIM_SO, _needs_shim
        if not _needs_shim() or preload != str(_SHIM_SO):
            raise FingerprintUnavailable('loader_preload_unsupported')
        roots.append(_SHIM_SO)


def _runtime_entries(root, ancestors=(), registry=False):
    resolved = root.resolve()
    if resolved in ancestors:
        raise FingerprintUnavailable('engine_symlink_cycle')
    if not root.exists():
        if root.is_symlink():
            raise FingerprintUnavailable('engine_broken_symlink')
        yield root, None
    elif root.is_dir():
        yield root, None
        for child in sorted(root.iterdir()):
            if registry and child.suffix != '.xcd' and child.name not in ('schema', 'data', 'res'):
                continue
            yield from _runtime_entries(child, ancestors + (resolved,))
    else:
        yield root, root.stat()


def engine_fingerprint(engine, diagnostics=None):
    details = diagnostics if diagnostics is not None else {}
    started = time.monotonic()
    details.update(engine_files=0, engine_bytes=0)
    try:
        return _engine_fingerprint(engine, details)
    except FingerprintUnavailable as exc:
        details['reason'] = exc.reason
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
        details['reason'] = 'engine_read_failed'
    finally:
        details['engine_fingerprint_ms'] = round((time.monotonic() - started) * 1000, 3)
    return None


def _engine_fingerprint(engine, details):
    from excel_lo_runtime import get_soffice_env

    executable = Path(engine).resolve()
    directory = executable.parent
    if directory.name == 'program' and (directory / 'soffice.bin').is_file():
        registry = directory.parent / 'share' / 'registry'
        roots = [directory, registry]
    elif directory.name == 'MacOS' and (directory.parent / 'Frameworks').is_dir():
        registry = directory.parent / 'Resources' / 'registry'
        roots = [directory, directory.parent / 'Frameworks', registry]
    else:
        raise FingerprintUnavailable('engine_layout_unsupported')
    registry_index = roots.index(registry)
    environment = get_soffice_env()
    _loader_roots(roots, environment)
    fingerprint = hashlib.sha256(str(executable).encode('utf-8'))
    loader_names = ('LD_LIBRARY_PATH', 'LD_PRELOAD', 'DYLD_LIBRARY_PATH', 'DYLD_INSERT_LIBRARIES', 'URE_BOOTSTRAP')
    fingerprint.update(json.dumps([environment.get(name) for name in loader_names]).encode('utf-8'))
    total_size = 0
    total_files = 0
    total_entries = 0
    hashed = {}
    for root_index, root in enumerate(roots):
        fingerprint.update(json.dumps([str(root), str(root.resolve())]).encode('utf-8') + b'\0')
        for path, before in _runtime_entries(root, registry=root_index == registry_index):
            total_entries += 1
            if total_entries > 20000:
                raise FingerprintUnavailable('engine_scan_limit')
            metadata = path.stat() if path.exists() else None
            fingerprint.update(json.dumps([str(path), str(path.resolve()),
                                           [metadata.st_mode, metadata.st_uid, metadata.st_gid] if metadata else None]
                                          ).encode('utf-8') + b'\0')
            if before is None:
                continue
            identity = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns,
                        before.st_mode, before.st_uid, before.st_gid)
            if identity in hashed:
                fingerprint.update(hashed[identity].encode('ascii'))
                continue
            total_files += 1
            total_size += before.st_size
            details.update(engine_files=total_files, engine_bytes=total_size)
            if not stat.S_ISREG(before.st_mode) or total_size > 512 * 1024 * 1024 or total_files > 10000:
                raise FingerprintUnavailable('engine_scan_limit')
            content_hash = digest_file(path)
            after = path.stat()
            fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns', 'st_mode', 'st_uid', 'st_gid')
            if any(getattr(before, field) != getattr(after, field) for field in fields):
                raise FingerprintUnavailable('engine_changed_during_scan')
            hashed[identity] = content_hash
            fingerprint.update(content_hash.encode('ascii'))
    return fingerprint.hexdigest()


def reuse_result(result, cache=None, reason='disabled'):
    return dict(result, cached=False, cache_reason=cache.reason if cache is not None else reason,
                **(cache.metrics if cache is not None else {}))


def reusable_workbook(source):
    if source.suffix.lower() != '.xlsx':
        return False
    try:
        with zipfile.ZipFile(source) as book:
            names = book.namelist()
            if any(n.startswith(('xl/externalLinks/', 'xl/queryTables/', 'xl/embeddings/', 'xl/tables/',
                                 'xl/webExtensions/', 'xl/macrosheets/', 'customXml/')) or n in (
                                     'xl/connections.xml', 'xl/vbaProject.bin') for n in names):
                return False
            for name in names:
                if name.endswith('.rels'):
                    if book.getinfo(name).file_size > 1024 * 1024:
                        return False
                    raw = book.read(name)
                    if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
                        return False
                    if any(n.get('TargetMode') == 'External' for n in ElementTree.fromstring(raw)):
                        return False
                if not (name == 'xl/workbook.xml' or name.startswith('xl/worksheets/') and name.endswith('.xml')):
                    continue
                # Avoid turning reuse into a second full-memory spreadsheet engine.
                if book.getinfo(name).file_size > 32 * 1024 * 1024:
                    return False
                raw = book.read(name)
                if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
                    return False
                root = ElementTree.fromstring(raw)
                for node in root.iter():
                    local = node.tag.rsplit('}', 1)[-1]
                    if local not in ('f', 'definedName', 'formula', 'formula1', 'formula2'):
                        continue
                    if node.get('t') not in (None, 'normal', 'shared') or node.get('ca') in ('1', 'true'):
                        return False
                    formula = node.text or ''
                    if '[' in formula or '://' in formula or '|' in formula:
                        return False
                    calls = re.findall(r'([A-Za-z_][A-Za-z0-9_.]*)\s*\(', formula)
                    if any(call.upper().replace('_XLFN.', '') not in FUNCTIONS for call in calls):
                        return False
            # Formula evaluation/formatting may also depend on conditional formats
            # and validation formulas, handled above rather than only <f> cells.
        return True
    except (OSError, ValueError, KeyError, RuntimeError, zipfile.BadZipFile, ElementTree.ParseError):
        return False


class OutputReuse:
    def __init__(self, source, output, request, engine, managed=False):
        self.source, self.output = Path(source).resolve(), Path(output).absolute()
        self.receipt = self.output.parent / ('.' + self.output.name + '.sheet-reuse.json')
        self.key = None
        self.reason = 'fingerprint_unavailable'
        self.engine = engine
        self.metrics = {}
        started = time.monotonic()
        phase = 'source_read_failed'
        try:
            source_hash = digest_file(self.source)
            if self.output.is_symlink():
                self.reason = 'unsafe_output'
                return
            phase = 'engine_read_failed'
            diagnostics = {}
            engine_hash = engine_fingerprint(engine, diagnostics)
            self.metrics.update({name: value for name, value in diagnostics.items() if name != 'reason'})
            if engine_hash is None:
                self.reason = diagnostics.get('reason', 'fingerprint_unavailable')
                return
            phase = 'implementation_read_failed'
            scripts = Path(__file__).resolve().parent
            self.key = dict(source=str(self.source), source_sha256=source_hash,
                            output=str(self.output), request=request, engine=engine_hash,
                            environment={key:os.environ.get(key) for key in (
                                'LANG', 'LANGUAGE', 'LC_ALL', 'LC_NUMERIC', 'LC_TIME', 'LC_CTYPE',
                                'LC_COLLATE', 'LC_MONETARY', 'TZ')},
                            implementation={n:digest_file(scripts/n) for n in (
                                '_lo_reuse.py', 'excel_lo_runtime.py', 'excel_lo_convert.py', 'excel_recalculate.py')})
            if managed:
                identity = {name: value for name, value in self.key.items() if name != 'output'}
                suffix = hashlib.sha256(json.dumps(identity, sort_keys=True).encode('utf-8')).hexdigest()
                self.retarget(self.output.with_name(suffix + self.source.suffix))
            # A matching successful receipt already classified these exact
            # source bytes under this implementation. Reusing that decision
            # avoids decompressing and parsing every worksheet on each hit.
            saved = self._read_receipt()
            known = saved.get('key') == self.key and saved.get('eligible') is True
            if not known:
                if not reusable_workbook(self.source):
                    self.key = None
                    self.reason = 'unsupported_workbook'
                elif digest_file(self.source) != source_hash:
                    self.key = None
                    self.reason = 'source_changed'
        except (OSError, ValueError, TypeError, RuntimeError):
            self.key = None
            self.reason = phase
        finally:
            self.metrics['cache_init_ms'] = round((time.monotonic() - started) * 1000, 3)

    def retarget(self, output):
        self.output = Path(output).absolute()
        self.receipt = self.output.parent / ('.' + self.output.name + '.sheet-reuse.json')
        if self.key is not None:
            self.key['output'] = str(self.output)

    def _read_receipt(self):
        self.reason = 'receipt_invalid'
        try:
            if self.receipt.is_symlink() or self.receipt.stat().st_size > 65536:
                return {}
            saved = json.loads(self.receipt.read_text(encoding='utf-8'))
            return saved if isinstance(saved, dict) else {}
        except FileNotFoundError:
            self.reason = 'receipt_missing'
            return {}
        except (OSError, ValueError):
            return {}

    def lookup(self):
        if self.key is None:
            return None
        try:
            if self.output.is_symlink():
                self.reason = 'unsafe_output'
                return None
            saved = self._read_receipt()
            if not saved:
                return None
            previous_key = saved.get('key')
            if not isinstance(previous_key, dict):
                return None
            for field, reason in (
                    ('source', 'source_changed'), ('source_sha256', 'source_changed'),
                    ('output', 'request_changed'), ('request', 'request_changed'),
                    ('engine', 'engine_changed'), ('environment', 'environment_changed'),
                    ('implementation', 'implementation_changed')):
                if previous_key.get(field) != self.key[field]:
                    self.reason = reason
                    return None
            if saved.get('eligible') is not True or previous_key != self.key:
                return None
            self.reason = 'output_missing'
            if not self.output.is_file():
                return None
            with self.output.open('rb') as output, self.source.open('rb') as source:
                identities = [(self.output, output, _file_identity(os.fstat(output.fileno())), 'output_changed'),
                              (self.source, source, _file_identity(os.fstat(source.fileno())), 'source_changed')]
                self.reason = 'output_changed'
                if digest_file(output) != saved.get('output_sha256'):
                    return None
                self.reason = 'source_changed'
                if digest_file(source) != self.key['source_sha256']:
                    return None
                self.reason = 'receipt_invalid'
                result = saved['result']
                if not isinstance(result, dict):
                    return None
                if result.get('status') not in ('success', 'recalculated') or Path(result['output']).absolute() != self.output:
                    return None
                for path, stream, identity, reason in identities:
                    self.reason = reason
                    if identity != _file_identity(os.fstat(stream.fileno())) or identity != _file_identity(path.lstat()):
                        return None
                self.reason = 'hit'
                return dict(result, cached=True, cache_reason='hit', attempts=0, engine_elapsed_ms=0, **self.metrics)
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            return None

    def remember(self, result, produced_sha256=None):
        if self.key is None or result.get('status') not in ('success', 'recalculated'):
            return
        try:
            if (self.output.is_symlink() or digest_file(self.source) != self.key['source_sha256']
                    or engine_fingerprint(self.engine) != self.key['engine']):
                return
            output_hash = digest_file(self.output)
            if produced_sha256 is None or output_hash != produced_sha256:
                return
            saved = dict(key=self.key, eligible=True, output_sha256=produced_sha256, result=result)
            with output_file(self.receipt, mode=0o600) as (stream, directory):
                stream.write(json.dumps(saved, ensure_ascii=False).encode('utf-8'))
                publish_output(stream, directory, self.receipt, overwrite=True)
        except (OSError, ValueError, TypeError, RuntimeError):
            pass  # Reuse metadata is optional; successful conversion remains usable.
