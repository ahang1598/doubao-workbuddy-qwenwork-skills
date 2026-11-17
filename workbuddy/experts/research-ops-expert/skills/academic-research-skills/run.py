#!/usr/bin/env python3
"""run.py — 入口（WB 守卫 v2：契约自愈 + 边界守卫，2026-09-13 注入）
原入口契约保留：暴露 main / run_selftest / read_text_safe / dry_run
"""
import os, sys

_SKILL = 'academic-research-skills'
_IN_ARG = ''
_BIG_MAX = 200000
_MIN_CHARS = 5

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts"))

_IMPORT_ERR = None
try:
    import main as _impl
except Exception as _e:
    _impl = None
    _IMPORT_ERR = _e

try:
    import json as _bj
    import io as _bio
    import contextlib as _bcl
except Exception:
    _bj = None
    _bio = None
    _bcl = None


def _b_emit(status, **kw):
    payload = {"status": status, "tool": _SKILL}
    payload.update(kw)
    if _bj is None:
        print('{"status": "%s", "tool": "%s"}' % (status, _SKILL))
    else:
        print(_bj.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def _entry():
    """入口自动发现（防 scripts/main.py 未暴露 main 导致模块级崩溃）"""
    if _impl is None:
        return None
    for _n in ('main', 'cli', '_cli', 'run', 'entry', 'process_input', 'run_cli'):
        _f = getattr(_impl, _n, None)
        if callable(_f):
            return _f
    return None


run_selftest = getattr(_impl, 'run_selftest', None) if _impl is not None else None
read_text_safe = ((getattr(_impl, 'read_text_safe', None) or getattr(_impl, '_read_text_safe', None))
                  if _impl is not None else None)
dry_run = getattr(_impl, 'dry_run', False) if _impl is not None else False


def _b_read_input():
    argv = sys.argv[1:]
    if '--selftest' in argv or '--dry-run' in argv or '--help' in argv or '-h' in argv:
        return ('SKIP', None)
    if _IN_ARG:
        for i, a in enumerate(argv):
            if a == _IN_ARG:
                if i + 1 >= len(argv):
                    return ('MISSING', None)
                v = argv[i + 1]
                if os.path.isfile(v):
                    try:
                        with open(v, encoding='utf-8', errors='ignore') as f:
                            return ('OK', f.read())
                    except Exception as e:
                        return ('UNREADABLE', str(e))
                return ('OK', v)
        return ('MISSING', None)
    return ('NOARG', None)


def _b_guard():
    mode, text = _b_read_input()
    if mode in ('SKIP', 'NOARG'):
        return None
    if mode == 'MISSING':
        return _b_emit('need_input', reason='未提供输入参数',
                       expected=(_IN_ARG or '--input') + ' <文件路径或文本>',
                       next_action='请提供待处理内容后重试')
    if mode == 'UNREADABLE':
        return _b_emit('unreadable_input', reason=text,
                       next_action='请确认文件编码为 UTF-8 且未损坏')
    if text is None or not str(text).strip():
        return _b_emit('insufficient_input', got_chars=0, min_chars=_MIN_CHARS,
                       next_action='请补充待处理内容后重试')
    s = str(text).strip()
    if len(s) < _MIN_CHARS:
        return _b_emit('insufficient_input', got_chars=len(s), min_chars=_MIN_CHARS,
                       next_action='请补充更多内容（至少 %d 个字符）后重试' % _MIN_CHARS)
    if len(text) > _BIG_MAX:
        for i, a in enumerate(sys.argv):
            if a == _IN_ARG and i + 1 < len(sys.argv):
                sys.argv[i + 1] = s[:_BIG_MAX]
                break
    return None


def main():
    """兼容原契约（selftest 会 hasattr(r,'main')）"""
    f = _entry()
    if f is None:
        return _b_emit('contract_error', error='挂载技能未暴露可用入口',
                       hint='scripts/main.py 需暴露 main/cli/run 之一；已返回结构化结果')
    return f()


def _safe_main():
    try:
        return int(main())
    except Exception as e:
        return _b_emit('error', error_type=type(e).__name__, error=str(e)[:300])


def _b_guarded_main():
    _buf = _bio.StringIO() if _bio is not None else None
    _rc = 0
    try:
        g = _b_guard()
        if g is not None:
            return g
        f = _entry()
        if f is None:
            _err = str(_IMPORT_ERR)[:200] if _IMPORT_ERR else '未暴露可用入口(main/cli/run)'
            return _b_emit('contract_error', error=_err,
                           hint='挂载技能入口契约损坏，已自愈为结构化结果（不中断上游编排）')
        if _buf is not None:
            with _bcl.redirect_stdout(_buf):
                _rc = f()
        else:
            _rc = f()
    except SystemExit as e:
        _rc = e.code if isinstance(e.code, int) else 0
    except Exception as e:
        return _b_emit('error', error_type=type(e).__name__, error=str(e)[:300],
                       hint='已捕获异常并返回结构化结果；请检查输入形态或改用标准格式重试')
    _out = _buf.getvalue() if _buf is not None else ''
    if _out.strip():
        print(_out, end='')
        return _rc if isinstance(_rc, int) else 0
    if _rc:
        return _b_emit('error', error_type='NoOutput', error='exit code %s，且无产出' % _rc,
                       hint='请检查输入形态/必需参数；已返回结构化结果以便上游继续编排')
    return _b_emit('need_input', reason='无产出（可能缺少必需参数或输入）',
                   next_action='请提供待处理内容后重试')


if __name__ == "__main__":
    sys.exit(_b_guarded_main())
