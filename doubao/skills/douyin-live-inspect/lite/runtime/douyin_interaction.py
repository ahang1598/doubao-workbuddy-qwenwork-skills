"""Anonymous Douyin room API and receive-only WebSocket adapter.

User IDs are transient inputs to task-local hashing; cookies and connection URLs stay in memory.
Protobuf wire fields follow the observed Douyin web messages, not a stable public API.
"""
import gzip
import http.cookiejar
import io
import json
import secrets
import time
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPCookieProcessor, HTTPSHandler

from runtime.http_fetch import _NoRedirect, _https_context
from runtime.vendor import websocket

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
MAX_MESSAGE = 2 * 1024 * 1024


class ProtocolError(ValueError):
    pass


def varint(data, pos):
    value = 0
    for shift in range(0, 70, 7):
        if pos >= len(data):
            raise ProtocolError('truncated protobuf')
        byte = data[pos]; pos += 1
        value |= (byte & 127) << shift
        if byte < 128:
            return value, pos
    raise ProtocolError('oversized varint')


def fields(data):
    if len(data) > MAX_MESSAGE:
        raise ProtocolError('oversized message')
    result, pos = {}, 0
    while pos < len(data):
        tag, pos = varint(data, pos)
        number, wire = tag >> 3, tag & 7
        if not number:
            raise ProtocolError('invalid field')
        if wire == 0:
            value, pos = varint(data, pos)
        elif wire in (1, 2, 5):
            if wire == 2:
                size, pos = varint(data, pos)
            else:
                size = 8 if wire == 1 else 4
            if size > len(data) - pos:
                raise ProtocolError('truncated field')
            value = data[pos:pos + size]; pos += size
        else:
            raise ProtocolError('unsupported wire type')
        result.setdefault(number, []).append(value)
    return result


def first(value, key, default=b''):
    return value.get(key, [default])[0]


def text(value, key):
    raw = first(value, key)
    if not isinstance(raw, bytes):
        raise ProtocolError('invalid text field')
    return raw.decode('utf-8', 'replace')


def integer(value):
    out = bytearray()
    while value > 127:
        out.append((value & 127) | 128); value >>= 7
    out.append(value)
    return bytes(out)


def encode(number, value):
    if isinstance(value, int):
        return integer(number << 3) + integer(value)
    if isinstance(value, str):
        value = value.encode()
    return integer((number << 3) | 2) + integer(len(value)) + value


def comment_role(raw, owner_id=None):
    """Derive staff roles only from platform fields, never from a nickname."""
    try:
        user = fields(raw)
        uid = first(user, 1, 0)
        if owner_id and type(uid) is int and uid > 0 and str(uid) == str(owner_id):
            return 'host'
        attr = fields(first(user, 32))
        if first(attr, 2, 0) == 1 or first(attr, 3, 0) == 1:
            return 'room_admin'
    except (ProtocolError, TypeError):
        pass
    return None


def decode(raw, *, owner_id=None):
    """Return sanitized business messages and an optional protocol ACK."""
    frame = fields(raw)
    payload = first(frame, 8)
    if payload[:2] == b'\x1f\x8b':
        with gzip.GzipFile(fileobj=io.BytesIO(payload)) as stream:
            payload = stream.read(MAX_MESSAGE + 1)
    if not payload:
        return [], None
    response = fields(payload)
    ack = (encode(2, first(frame, 2, 0)) + encode(7, 'ack') + encode(8, first(response, 5))) if first(response, 9, 0) else None
    messages = []
    for entry in response.get(1, []):
        message = fields(entry)
        method = text(message, 1)
        if method not in {'WebcastChatMessage', 'WebcastRoomUserSeqMessage'}:
            continue
        body = fields(first(message, 2))
        if method == 'WebcastChatMessage':
            common = fields(first(body, 1))
            content = text(body, 3).strip()
            message_id = first(message, 3, 0) or first(common, 2, 0)
            # Without an identity, replay duplicates cannot safely be distinguished.
            if content and isinstance(message_id, int) and message_id > 0:
                created = first(common, 4, 0)
                role = comment_role(first(body, 2), owner_id)
                author = {}
                try:
                    user = fields(first(body, 2))
                    uid = first(user, 1, 0)
                    if type(uid) is int and uid > 0:
                        author['raw_author_id'] = str(uid)
                    nickname = text(user, 3).strip()
                    if nickname:
                        author['author_nickname'] = nickname[:100]
                except (ProtocolError, TypeError):
                    pass  # A missing/malformed user must not discard the comment.
                messages.append({'kind':'comment', 'message_id':str(message_id), 'text':content[:2000],
                                 **author,
                                 **({'author_role':role} if role else {}),
                                 'server_created_at':created if isinstance(created, int) and created > 0 else None})
        else:
            count = first(body, 3, None)
            if type(count) is int and count >= 0:
                messages.append({'kind':'audience', 'count':count})
    return messages, ack


class Connection:
    def __init__(self, web_rid):
        self.web_rid, self.socket = web_rid, None
        self.client = build_opener(_NoRedirect(), HTTPCookieProcessor(http.cookiejar.CookieJar()),
                                   HTTPSHandler(context=_https_context()))
        self.client.addheaders = [('User-Agent', UA)]
        self.audience = None
        self.owner_id = None

    def open(self):
        with self.client.open('https://live.douyin.com/', timeout=8) as response:
            response.read(1024)  # Receive anonymous cookies; page content is not used.
        params = {'aid':'6383', 'app_name':'douyin_web', 'live_id':'1', 'device_platform':'web',
                  'language':'zh-CN', 'enter_from':'page_refresh', 'web_rid':self.web_rid}
        request = Request('https://live.douyin.com/webcast/room/web/enter/?' + urlencode(params),
                          headers={'Referer':'https://live.douyin.com/' + self.web_rid})
        with self.client.open(request, timeout=8) as response:
            raw = response.read(MAX_MESSAGE + 1)
        if len(raw) > MAX_MESSAGE:
            raise ProtocolError('oversized room response')
        result = json.loads(raw)
        if result.get('status_code') != 0:
            raise ProtocolError('room API failed')
        room = result['data']['data'][0]
        owner = room.get('owner') or {}
        self.owner_id = str(owner.get('id_str') or owner.get('id') or '')
        if room.get('status') != 2:
            raise ProtocolError('room unavailable')
        rid = str(room.get('id_str') or room.get('id', ''))
        if not rid.isascii() or not rid.isdigit():
            raise ProtocolError('invalid room identity')
        count = room.get('stats', {}).get('user_count_str')
        if str(count).isascii() and str(count).isdigit():
            self.audience = int(count)
        params = {'app_name':'douyin_web', 'version_code':'180800', 'webcast_sdk_version':'1.0.14-beta.0',
                  'update_version_code':'1.0.14-beta.0', 'compress':'gzip', 'device_platform':'web',
                  'cookie_enabled':'true', 'browser_language':'zh-CN', 'browser_platform':'Win32',
                  'browser_name':'Mozilla', 'browser_version':UA, 'browser_online':'true',
                  'tz_name':'Asia/Shanghai', 'host':'https://live.douyin.com', 'aid':'6383', 'live_id':'1',
                  'did_rule':'3', 'endpoint':'live_pc', 'support_wrds':'1',
                  'user_unique_id':str(7300000000000000000 + secrets.randbelow(10000000000000000)),
                  'im_path':'/webcast/im/fetch/', 'identity':'audience', 'need_persist_msg_count':'15',
                  'insert_task_id':'', 'live_reason':'', 'room_id':rid, 'heartbeatDuration':'0'}
        # Extract only a cookie issued by this opener. Never use host/browser auth.
        request = Request('https://live.douyin.com/')
        for handler in self.client.handlers:
            if isinstance(handler, HTTPCookieProcessor):
                handler.cookiejar.add_cookie_header(request)
        cookie = '; '.join(part.strip() for part in (request.get_header('Cookie') or '').split(';')
                           if part.strip().startswith('ttwid='))
        self.socket = websocket.create_connection(
            'wss://webcast100-ws-web-lq.douyin.com/webcast/im/push/v2/?' + urlencode(params),
            timeout=8, header={'User-Agent':UA}, cookie=cookie, origin='https://live.douyin.com',
            redirect_limit=0, sslopt={'context':_https_context()})
        if self.socket.getstatus() != 101:
            self.close()
            raise ProtocolError('unexpected handshake')
        self.socket.settimeout(2)
        self.last_ping = 0
        return self

    def receive(self):
        if time.monotonic() - self.last_ping >= 5:
            self.socket.ping(encode(7, 'hb')); self.last_ping = time.monotonic()
        try:
            raw = self.socket.recv()
        except websocket.WebSocketTimeoutException:
            return []
        if not raw:
            raise ConnectionError('closed')
        if not isinstance(raw, bytes):
            raise ProtocolError('unexpected frame')
        messages, ack = decode(raw, owner_id=self.owner_id)
        if ack:
            self.socket.send_binary(ack)
        return messages

    def close(self):
        if self.socket:
            self.socket.close(timeout=1)
