"""B 站直播解析；候选仅来自播放响应，传输复用有界隔离 HTTP。"""
import json
import re
import time
from urllib.parse import urlsplit, urljoin, parse_qs
from runtime.http_fetch import safe_failure
from runtime.xiaohongshu_live import fetch as fetch_platform, XiaohongshuLiveError, probe_failure

HOSTS = {'live.bilibili.com', 'b23.tv'}
ERRORS = {'BILI_FETCH_FAILED', 'BILI_PAGE_UNAVAILABLE', 'BILI_AUTH_REQUIRED',
          'BILI_STREAM_UNAVAILABLE', 'BILI_LIVE_STATE_UNKNOWN', 'BILI_ROOM_UNAVAILABLE',
          'BILI_REPLAY_UNSUPPORTED', 'BROWSER_SOURCE_TIMEOUT', 'BROWSER_SOURCE_TASK_CLOSED', 'INVALID_BROWSER_SOURCE'}


class BilibiliLiveError(Exception):
    def __init__(self, code, diagnostic=None):
        super().__init__('B 站直播来源暂不可用')
        self.code = code
        self.retryable = code == 'BILI_FETCH_FAILED'
        self.source_failure = safe_failure(diagnostic)


def validate_url(value):
    try:
        if not isinstance(value, str) or len(value) > 8192 or re.search(r'[\x00-\x20]', value):
            raise ValueError()
        u = urlsplit(value)
        if u.scheme != 'https' or u.username or u.password or u.port not in (None, 443):
            raise ValueError()
        room = re.fullmatch(r'/([1-9][0-9]*)/?', u.path)
        if u.hostname == 'live.bilibili.com' and room:
            return 'https://live.bilibili.com/' + room[1]
        if u.hostname == 'b23.tv' and re.fullmatch(r'/[A-Za-z0-9]+/?', u.path):
            return value
    except ValueError:
        pass
    raise BilibiliLiveError('INVALID_INPUT')


def candidate(value, now=None):
    now = time.time() * 1000 if now is None else now
    if not isinstance(value, str) or len(value) > 8192 or re.search(r'[\x00-\x20]', value):
        return None
    try:
        u = urlsplit(value)
        if (u.scheme not in ('http', 'https') or u.username or u.password or u.fragment
                or u.port not in (None, 80, 443) or not (u.hostname or '').endswith('.bilivideo.com')
                or not u.path.lower().endswith('.flv')):
            return None
        for expiry in parse_qs(u.query, keep_blank_values=True).get('expires', []):
            if not re.fullmatch('[0-9]+', expiry) or int(expiry) < now / 1000 + 60:
                return None
        return value
    except ValueError:
        return None


def room_data(payload):
    if not isinstance(payload, dict):
        raise BilibiliLiveError('BILI_PAGE_UNAVAILABLE')
    if payload.get('code') in (-101, -111, -352, -412):
        raise BilibiliLiveError('BILI_AUTH_REQUIRED')
    room = payload.get('data')
    if type(payload.get('code')) is not int or payload.get('code') != 0 or not isinstance(room, dict):
        raise BilibiliLiveError('BILI_PAGE_UNAVAILABLE')
    rid = room.get('room_id')
    if not ((type(rid) is int and 0 < rid <= 2**53-1) or (isinstance(rid, str) and re.fullmatch('[1-9][0-9]*', rid))):
        raise BilibiliLiveError('BILI_PAGE_UNAVAILABLE')
    if room.get('is_hidden') or room.get('is_locked') or room.get('encrypted'):
        raise BilibiliLiveError('BILI_ROOM_UNAVAILABLE')
    status = room.get('live_status')
    if status == 2:
        raise BilibiliLiveError('BILI_REPLAY_UNSUPPORTED')
    if type(status) is not int or status not in (0, 1):
        raise BilibiliLiveError('BILI_LIVE_STATE_UNKNOWN')
    return room


def records(value):
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def parse_room(payload, now=None, expected_room=None):
    room = room_data(payload)
    if expected_room is not None and str(room['room_id']) != str(expected_room):
        raise BilibiliLiveError('BILI_PAGE_UNAVAILABLE')
    if room['live_status'] == 0:
        return {'status': 'not_live', 'sourceType': 'bilibili'}
    info = room.get('playurl_info')
    play = info.get('playurl') if isinstance(info, dict) else None
    urls = []
    for stream in records(play.get('stream') if isinstance(play, dict) else None):
        if stream.get('protocol_name') != 'http_stream':
            continue
        for fmt in records(stream.get('format')):
            if fmt.get('format_name') != 'flv':
                continue
            for codec in records(fmt.get('codec')):
                base = codec.get('base_url')
                if codec.get('codec_name') != 'avc' or codec.get('drm') or not isinstance(base, str) or not base.startswith('/'):
                    continue
                for item in records(codec.get('url_info')):
                    if not isinstance(item.get('host'), str) or not isinstance(item.get('extra'), str):
                        continue
                    url = item['host'] + base + item['extra']
                    if candidate(url, now) and url not in urls:
                        urls.append(url)
    if not urls:
        raise BilibiliLiveError('BILI_STREAM_UNAVAILABLE')
    return {'status': 'ready', 'sourceType': 'bilibili', 'streamUrl': urls[0], 'candidates': urls}


def fetch(url, **kwargs):
    try:
        return fetch_platform(url, platform='bilibili', **kwargs)
    except XiaohongshuLiveError as error:
        raise BilibiliLiveError('SOURCE_CANCELLED' if error.code == 'SOURCE_CANCELLED' else 'BILI_FETCH_FAILED', error.source_failure) from None


def resolve_page(value, *, transport=fetch, deadline=None, cancel=None):
    deadline = time.monotonic() + 15 if deadline is None else deadline
    page = validate_url(value)
    for hop in range(5):
        if cancel and cancel():
            raise BilibiliLiveError('SOURCE_CANCELLED')
        if urlsplit(page).hostname == 'live.bilibili.com':
            return page
        if hop == 4:
            break
        left = deadline - time.monotonic()
        if left <= 0:
            raise BilibiliLiveError('BILI_FETCH_FAILED')
        result = transport(page, timeout=left, cancel=cancel)
        if result.get('status') not in (301, 302, 303, 307, 308) or not result.get('location'):
            raise BilibiliLiveError('BILI_PAGE_UNAVAILABLE')
        page = validate_url(urljoin(page, result['location']))
    raise BilibiliLiveError('BILI_PAGE_UNAVAILABLE')


def validate_browser(page, value, now=None):
    now = time.time() * 1000 if now is None else now
    try:
        at = value['captured_at']
        if type(at) is not int or at > now + 5000 or now - at > 120000 or validate_url(value['page_url']) != page:
            raise ValueError()
        if value.get('status') == 'not_live' and set(value) == {'status', 'page_url', 'captured_at'}:
            return {'status': 'not_live', 'sourceType': 'bilibili', 'sourceMethod': 'browser'}
        url = candidate(value['stream_url'], now)
        if not url:
            raise ValueError()
        return {'status': 'ready', 'streamUrl': url, 'sourceType': 'bilibili', 'sourceMethod': 'browser'}
    except (KeyError, TypeError, ValueError, BilibiliLiveError):
        raise BilibiliLiveError('INVALID_BROWSER_SOURCE') from None


def resolve_live(value, *, browser_source=None, transport=fetch, cancel=None, timeout_ms=15000):
    deadline = time.monotonic() + timeout_ms / 1000
    page = resolve_page(value, transport=transport, deadline=deadline, cancel=cancel)

    def remaining():
        if cancel and cancel():
            raise BilibiliLiveError('SOURCE_CANCELLED')
        left = deadline - time.monotonic()
        if left <= 0:
            raise BilibiliLiveError('BILI_FETCH_FAILED', {'kind': 'network_timeout'})
        return left

    def request_json(path):
        response = transport('https://api.live.bilibili.com' + path, timeout=remaining(), cancel=cancel)
        if response.get('status') != 200:
            raise BilibiliLiveError('BILI_AUTH_REQUIRED' if response.get('status') in (401, 403, 412) else 'BILI_FETCH_FAILED',
                                    {'kind': 'http_error', 'http_status': response.get('status')})
        try:
            return json.loads(response['body'])
        except (ValueError, KeyError, TypeError):
            raise BilibiliLiveError('BILI_PAGE_UNAVAILABLE') from None

    if browser_source is not None:
        source = validate_browser(page, browser_source)
        if source['status'] == 'not_live':
            return source
        urls = [source['streamUrl']]
    else:
        room = room_data(request_json('/room/v1/Room/room_init?id=' + page.rsplit('/', 1)[-1]))
        if room['live_status'] == 0:
            return {'status': 'not_live', 'sourceType': 'bilibili'}
        source = parse_room(request_json('/xlive/web-room/v2/index/getRoomPlayInfo?room_id=' + str(room['room_id'])
                            + '&protocol=0&format=0&codec=0&qn=250&platform=web&ptype=8'), expected_room=room['room_id'])
        if source['status'] == 'not_live':
            return source
        urls = source['candidates']
    diagnostic = None
    for url in urls:
        if time.monotonic() >= deadline:
            break
        try:
            response = transport(url, timeout=min(5, remaining()), cancel=cancel, probe=True)
            if response.get('ready'):
                return {'status': 'ready', 'streamUrl': url, 'sourceType': 'bilibili',
                        'sourceMethod': 'browser' if browser_source is not None else 'anonymous'}
            diagnostic = probe_failure(response)
        except BilibiliLiveError as error:
            if error.code == 'SOURCE_CANCELLED':
                raise
            diagnostic = error.source_failure
    raise BilibiliLiveError('BILI_STREAM_UNAVAILABLE', diagnostic)
