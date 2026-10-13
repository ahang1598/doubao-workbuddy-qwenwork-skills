# Adapted from skills_live_inspect_lite/runtime/douyin_live.py; content-only migration.
"""Douyin live page resolution using only Python's standard library.

Transport injection accepts ``transport(url, timeout=seconds, headers=dict)``
returning an HTTP response with status, headers, read(size), and close(). A
transport must not follow redirects: only validated share redirects are followed.
All ``now`` values are Unix epoch milliseconds; signed stream URLs remain intact.
"""
import base64
import html as html_module
import io
import ipaddress
import json
import math
import os
import re
import socket
import subprocess
import sys
from pathlib import Path
import time
from urllib.parse import parse_qs, unquote, urljoin, urlsplit, urlunsplit

DOUYIN_PAGE_MAX_BYTES = 2 * 1024 * 1024
DOUYIN_PAGE_TIMEOUT_MS = 15_000
_BLOCKED = tuple(ipaddress.ip_network(n) for n in (
    '0.0.0.0/8', '10.0.0.0/8', '100.64.0.0/10', '127.0.0.0/8', '169.254.0.0/16',
    '172.16.0.0/12', '192.0.0.0/24', '192.0.2.0/24', '192.31.196.0/24', '192.52.193.0/24',
    '192.88.99.0/24', '192.168.0.0/16', '192.175.48.0/24', '198.18.0.0/15',
    '198.51.100.0/24', '203.0.113.0/24', '224.0.0.0/4', '240.0.0.0/4',
    '::/128', '::1/128', '64:ff9b:1::/48', '100::/64', '2001::/32', '2001:2::/48',
    '2001:10::/28', '2001:20::/28', '2001:db8::/32', 'fc00::/7', 'fe80::/10', 'ff00::/8'))


class DouyinLiveError(Exception):
    def __init__(self, message, code, retryable=False):
        super().__init__(message)
        self.code = code
        self.retryable = retryable


def _unavailable(retryable=False):
    return DouyinLiveError('Douyin live page is unavailable', 'DOUYIN_PAGE_UNAVAILABLE', retryable)


def validate_douyin_live_url(value):
    try:
        url = urlsplit(str(value or '').strip())
        if (url.scheme != 'https' or url.hostname not in ('live.douyin.com', 'www.douyin.com', 'v.douyin.com')
                or url.username or url.password or url.port not in (None, 443)):
            raise ValueError()
        if url.hostname == 'v.douyin.com':
            match = re.fullmatch(r'/([A-Za-z0-9_-]{4,128})/?', url.path)
            if match:
                return 'https://v.douyin.com/' + match[1] + '/'
        else:
            match = re.fullmatch(r'/(\d+)/?' if url.hostname == 'live.douyin.com' else r'/follow/live/(\d+)/?', url.path, re.ASCII)
            # Explicit identity is independent of navigation paths, but must not conflict with a room path.
            query = parse_qs(url.query, keep_blank_values=True)
            if 'live_web_rid' in query:
                room_ids = query['live_web_rid']
                if (len(room_ids) != 1 or not re.fullmatch(r'[0-9]+', room_ids[0])
                        or (match and match[1] != room_ids[0])):
                    raise ValueError()
                return 'https://live.douyin.com/' + room_ids[0]
            if match:
                return 'https://live.douyin.com/' + match[1]
    except (ValueError, TypeError):
        pass
    raise DouyinLiveError('douyin_url must use an official Douyin live or share URL without credentials or a custom port', 'INVALID_INPUT')


def _container(value):
    if isinstance(value, str) and value.lstrip().startswith(('{', '[')):
        try:
            value = json.loads(value)
        except (ValueError, RecursionError):
            return None
    return value if isinstance(value, (dict, list)) else None


def _get(value, *keys):
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def _first(*values):
    return next((v for v in values if v is not None), None)


def _address_blocked(host):
    host = unquote(host or '').lower().strip('[]').split('%')[0]
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        try:
            # inet_aton also recognizes WHATWG-style integer/hex/short IPv4.
            addr = ipaddress.ip_address(socket.inet_aton(host))
        except (OSError, ValueError):
            return False
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped:
        addr = addr.ipv4_mapped
    return any(addr.version == net.version and addr in net for net in _BLOCKED)


def extract_douyin_stream_key(value):
    try:
        url = urlsplit(value)
        unique = parse_qs(url.query).get('unique_id', [''])[0]
        match = re.search(r'(?:^|[/_-])stream-(\d{8,})(?=$|[\s/_.-])', unquote(url.path) + ' ' + unquote(unique), re.I | re.ASCII)
        return match[1] if match else None
    except (TypeError, ValueError):
        return None


def _quality(value):
    normalized = str(value or '').lower().removesuffix('5')
    return normalized if normalized in ('ld', 'sd', 'hd', 'uhd', 'origin') else None


def _candidate(value, context, now):
    if not isinstance(value, str) or len(value) > 8192:
        return None
    try:
        url = urlsplit(value)
        if (url.scheme not in ('http', 'https') or not url.hostname or url.username or url.password
                or _address_blocked(url.hostname) or re.search(r'(?:^|[.-])admin(?:[.-]|$)', unquote(url.hostname), re.I)
                or not url.path.lower().endswith('.flv')):
            return None
        url.port  # Reject malformed port syntax.
        query = parse_qs(url.query, keep_blank_values=True)
        if 'auth_key' in query:
            match = re.fullmatch(r'(\d+)-[A-Za-z0-9]+-\d+-[\da-fA-F]{32}', query.get('auth_key', [''])[0])
            timestamps = [int(match[1])] if match else []
            valid = any(math.floor(now / 1000) + 60 <= stamp <= 2 ** 53 - 1 for stamp in timestamps)
        else:
            explicit = _first(query.get('expire'), query.get('t'))
            if explicit is not None:
                raw = explicit[0]
                timestamps = []
                if re.fullmatch(r'[0-9]+', raw):
                    timestamps.append(int(raw))
                if re.fullmatch(r'[0-9a-fA-F]{8}', raw):
                    timestamps.append(int(raw, 16))
                valid = any(math.floor(now / 1000) + 60 <= stamp <= 2 ** 53 - 1 for stamp in timestamps)
            else:
                valid = bool(re.fullmatch(r'[0-9a-fA-F]{8}', query.get('wsTime', [''])[0])
                             and re.fullmatch(r'[0-9a-fA-F]{32}', query.get('wsSecret', [''])[0]))
        key = extract_douyin_stream_key(value)
        if not key or not valid:
            return None
        bitrate = context.get('bitrate')
        try:
            bitrate = float(bitrate) if bitrate is not None else None
            if bitrate is not None and not math.isfinite(bitrate):
                bitrate = None
        except (ValueError, TypeError):
            bitrate = None
        return dict(url=value, streamKey=key, codec=context.get('codec'), quality=_quality(context.get('quality')),
                    route=context.get('route'), bitrate=bitrate, resolution=context.get('resolution'), secure=url.scheme == 'https')
    except (ValueError, TypeError):
        return None


def _collect(root, codec, now):
    output = []
    def visit(raw, context, depth=0):
        if depth > 14:
            return
        value = _container(raw)
        if isinstance(value, list):
            for item in value:
                visit(item, context, depth + 1)
        elif isinstance(value, dict):
            sdk = _container(_first(value.get('sdk_params'), value.get('sdkParams'))) or {}
            inherited = dict(context, bitrate=_first(_get(sdk, 'vbitrate'), _get(sdk, 'bitrate'), _get(sdk, 'bitrateKbps'), context.get('bitrate')),
                             resolution=_first(_get(sdk, 'resolution'), context.get('resolution')))
            for key, item in value.items():
                lower = key.lower()
                next_context = dict(inherited, quality=_first(_quality(lower), inherited.get('quality')),
                                    route=lower if lower in ('main', 'backup') else inherited.get('route'))
                if lower == 'flv':
                    candidate = _candidate(item, dict(next_context, codec=codec), now)
                    if candidate:
                        output.append(candidate)
                elif lower not in ('sdk_params', 'sdkparams'):
                    visit(item, next_context, depth + 1)
    visit(root, {})
    return output


def select_douyin_flv_candidate(candidates):
    def rank(item, fallback):
        area = re.fullmatch(r'(\d+)x(\d+)', str(item.get('resolution') or ''), re.I)
        return (not item.get('secure'),
                _first(item.get('bitrate'), math.inf) if fallback else 0,
                int(area[1]) * int(area[2]) if fallback and area else (math.inf if fallback else 0),
                {'main': 0, 'backup': 1}.get(item.get('route'), 2))
    for codec, quality in [('h264', 'ld'), ('h265', 'ld'), ('h264', None), ('h265', None)]:
        pool = [i for i in candidates if i.get('codec') == codec and (quality is None or i.get('quality') == quality)]
        if pool:
            return min(pool, key=lambda item: rank(item, quality is None))
    return None


def _decode_script(value):
    decoded = html_module.unescape(str(value or ''))
    for _ in range(2):
        decoded = re.sub(r'\\u([\da-f]{4})', lambda m: chr(int(m[1], 16)), decoded, flags=re.I)
        decoded = re.sub(r'\\x([\da-f]{2})', lambda m: chr(int(m[1], 16)), decoded, flags=re.I)
        decoded = decoded.replace(r'\/', '/').replace(r'\"', '"')
    return decoded


def _config(html):
    match = re.search(r'<script\b[^>]*\bdata-config="([^"]*)"[^>]*>', str(html), re.I)
    if not match:
        raise _unavailable(True)
    try:
        return json.loads(html_module.unescape(match[1]))
    except (ValueError, RecursionError):
        raise _unavailable() from None


def _broadcast_status(config):
    raw = _first(_get(config, 'roomInfo', 'room', 'status'), _get(config, 'room', 'status'), _get(config, 'roomInfo', 'status'))
    ended = _get(config, 'basicPlayerProps', 'logOptions', 'is_live_end')
    if str(raw) == '4' or str(ended) == '1':
        return 'ended'
    return 'live' if str(raw) == '2' or str(ended) == '0' else 'unknown'


def _now(value):
    return time.time() * 1000 if value is None else value() if callable(value) else value


def parse_douyin_live_page(html, *, now=None):
    try:
        config = _config(html)
    except DouyinLiveError:
        config = None
    if config is not None and _broadcast_status(config) == 'ended':
        return dict(status='not_live')
    stream_data = None
    if config is not None:
        stream_data = _first(_get(config, 'playerConfig', 'pluginsConfig', 'liveStream', 'streamData'),
                             _get(config, 'basicPlayerProps', 'pluginsConfig', 'liveStream', 'streamData'),
                             _get(config, 'basicPlayerProps', 'pluginsConfigInternal', 'liveStream', 'streamData'))
    candidates = []
    if isinstance(stream_data, (dict, list)):
        for codec in ('h264', 'h265'):
            pull = _get(stream_data, codec + 'PullData')
            candidates.extend(_collect(_first(_get(pull, 'stream_data'), pull), codec, _now(now)))
    if not candidates:
        if config is not None:
            status = _first(_get(config, 'roomInfo', 'room', 'status'), _get(config, 'room', 'status'), _get(config, 'roomInfo', 'status'))
            if str(status) == '4':
                return dict(status='not_live')
        # Fallback: extract FLV URLs directly from HTML (dynamic-rendered pages or empty streamData in data-config)
        decoded = _decode_script(html)
        seen = set()
        flv_pattern = r"https?://[^\s\"\'<>\\]+?\.flv(?:\?[^\s\"\'<>\\]+)?"
        for value in re.findall(flv_pattern, decoded, re.I):
            if value in seen:
                continue
            seen.add(value)
            try:
                url = urlsplit(value)
            except ValueError:
                continue
            quality = re.search(r'(?:^|[/_-])(ld|sd|hd|uhd|origin)(?=$|[/_.-])', url.path, re.I)
            context = dict(codec='h265' if re.search('h265|hevc', url.path + ' ' + url.query, re.I) else 'h264', quality=quality[1] if quality else None)
            candidate = _candidate(value, context, _now(now))
            if candidate:
                candidates.append(candidate)
    selected = select_douyin_flv_candidate(candidates)
    if not selected:
        if isinstance(stream_data, (dict, list)) and stream_data:
            raise DouyinLiveError('No supported FLV stream is available for this Douyin live room', 'DOUYIN_FLV_UNAVAILABLE')
        raise DouyinLiveError('No confirmed live state', 'DOUYIN_PAGE_UNAVAILABLE', True)
    return dict(status='ready', streamUrl=selected['url'], streamKey=selected['streamKey'])


def parse_douyin_reflow_page(html, *, now=None):
    decoded = _decode_script(html)
    candidates = []
    seen = set()
    for value in re.findall(r'https?://[^\s"\'<>\\]+?\.flv(?:\?[^\s"\'<>\\]+)?', decoded, re.I):
        if value in seen:
            continue
        seen.add(value)
        try:
            url = urlsplit(value)
        except ValueError:
            continue
        quality = re.search(r'(?:^|[/_-])(ld|sd|hd|uhd|origin)(?=$|[/_.-])', url.path, re.I)
        context = dict(codec='h265' if re.search('h265|hevc', url.path + ' ' + url.query, re.I) else 'h264', quality=quality[1] if quality else None)
        candidate = _candidate(value, context, _now(now))
        if candidate:
            candidates.append(candidate)
    selected = select_douyin_flv_candidate(candidates)
    if selected:
        return dict(status='ready', streamUrl=selected['url'], streamKey=selected['streamKey'])
    if re.search(r'streamData|stream_data|room[_-]?id', decoded, re.I):
        raise DouyinLiveError('No supported FLV stream is available for this Douyin live room', 'DOUYIN_FLV_UNAVAILABLE')
    raise DouyinLiveError('No confirmed live state', 'DOUYIN_PAGE_UNAVAILABLE', True)


class _BufferedResponse(io.BytesIO):
    def __init__(self, body, status, headers):
        super().__init__(body)
        self.status = status
        self.headers = headers


def _transport(url, *, timeout, headers, maximum_bytes=DOUYIN_PAGE_MAX_BYTES):
    """Resolve DNS, headers and body inside one killable Python process.

    subprocess.run kills and reaps its child on timeout. The worker bounds its
    input, selected headers and body; stdout is at most base64(2 MiB) + 150 KiB.
    """
    payload = json.dumps(dict(url=url, timeout=timeout, headers=headers,
                              maximum_bytes=maximum_bytes)).encode('utf-8')
    if len(payload) > 65_536:
        raise _unavailable()
    try:
        result = subprocess.run(
            [sys.executable, '-I', str(Path(__file__).with_name('http_fetch.py').resolve())],
            input=payload, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            timeout=timeout, check=False)
        if result.returncode != 0 or len(result.stdout) > 3 * 1024 * 1024:
            raise ValueError('invalid HTTP worker response')
        envelope = json.loads(result.stdout)
        if envelope.get('error') == 'DOUYIN_PAGE_UNAVAILABLE':
            raise _unavailable()
        if envelope.get('error'):
            raise ValueError('HTTP worker failed')
        body = base64.b64decode(envelope['body'], validate=True)
        if len(body) > min(maximum_bytes, DOUYIN_PAGE_MAX_BYTES):
            raise _unavailable()
        return _BufferedResponse(body, envelope['status'], envelope['headers'])
    except DouyinLiveError:
        raise
    except Exception:
        raise DouyinLiveError('Douyin live page fetch failed', 'DOUYIN_FETCH_FAILED', True) from None


def _fetch(url, transport, timeout_ms, maximum_bytes, *, redirect=False):
    response = None
    started = time.monotonic()
    try:
        options = {'maximum_bytes': maximum_bytes} if transport is _transport else {}
        request_headers = {
            'accept': 'text/html,application/xhtml+xml', 'accept-language': 'zh-CN,zh;q=0.9',
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126 Safari/537.36'}
        response = transport(url, timeout=timeout_ms / 1000, **options, headers=request_headers)
        status = response.status
        headers = {key.lower(): value for key, value in response.headers.items()}
        if status >= 500:
            raise DouyinLiveError('Douyin live page fetch failed', 'DOUYIN_FETCH_FAILED', True)
        if redirect:
            return status, headers.get('location', '')
        if not 200 <= status < 300:
            raise _unavailable()
        content_type = headers.get('content-type', '').lower()
        if 'text/html' not in content_type and 'application/xhtml+xml' not in content_type:
            raise _unavailable()
        try:
            declared = int(headers.get('content-length', 0))
        except (TypeError, ValueError):
            declared = 0
        if declared > maximum_bytes:
            raise _unavailable()
        chunks, size = [], 0
        while True:
            remaining = timeout_ms / 1000 - (time.monotonic() - started)
            if remaining <= 0:
                raise TimeoutError('Douyin page read deadline exceeded')
            # HTTPResponse.read1 performs at most one raw read, so a peer that
            # trickles bytes cannot keep a full-buffer read alive indefinitely.
            sock = getattr(getattr(getattr(response, 'fp', None), 'raw', None), '_sock', None)
            if sock is not None:
                sock.settimeout(remaining)
            read = getattr(response, 'read1', response.read)
            chunk = read(min(65536, maximum_bytes + 1 - size))
            if not chunk:
                break
            size += len(chunk)
            if size > maximum_bytes:
                raise _unavailable()
            chunks.append(chunk)
        return b''.join(chunks).decode('utf-8', errors='replace')
    except DouyinLiveError:
        raise
    except Exception as cause:
        raise DouyinLiveError('Douyin live page fetch failed', 'DOUYIN_FETCH_FAILED', True) from cause
    finally:
        if response is not None:
            response.close()


def resolve_douyin_live(value, *, transport=None, now=None, timeout_ms=DOUYIN_PAGE_TIMEOUT_MS, maximum_bytes=DOUYIN_PAGE_MAX_BYTES):
    page_url = validate_douyin_live_url(value)
    transport = transport or _transport
    def fetch(url, **kwargs):
        return _fetch(url, transport, timeout_ms, maximum_bytes, **kwargs)
    if urlsplit(page_url).hostname == 'v.douyin.com':
        status, location = fetch(page_url, redirect=True)
        try:
            landing = urlsplit(urljoin(page_url, location))
            if (status not in (301, 302, 303, 307, 308) or landing.scheme != 'https'
                    or landing.hostname != 'webcast.amemv.com' or landing.username or landing.password
                    or landing.port not in (None, 443) or not re.fullmatch(r'/douyin/webcast/reflow/[0-9]{8,}/?', landing.path)):
                raise ValueError()
        except ValueError:
            raise _unavailable() from None
        return parse_douyin_reflow_page(fetch(urlunsplit(landing._replace(fragment=''))), now=_now(now))
    html = fetch(page_url)
    try:
        return parse_douyin_live_page(html, now=_now(now))
    except DouyinLiveError as cause:
        if cause.code != 'DOUYIN_FLV_UNAVAILABLE':
            raise
    return parse_douyin_reflow_page(fetch('https://webcast.amemv.com/douyin/webcast/reflow/' + urlsplit(page_url).path[1:]), now=_now(now))
