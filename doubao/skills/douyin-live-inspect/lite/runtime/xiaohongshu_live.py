"""小红书直播解析与短链展开，不导出浏览器认证材料。"""
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit, urljoin, parse_qs, urlunsplit
from runtime.http_fetch import safe_failure

HOSTS={'www.xiaohongshu.com','xhslink.com'}
ERRORS={'XHS_FETCH_FAILED','XHS_PAGE_UNAVAILABLE','XHS_AUTH_REQUIRED','XHS_STREAM_UNAVAILABLE','XHS_LIVE_STATE_UNKNOWN','BROWSER_SOURCE_TIMEOUT','BROWSER_SOURCE_TASK_CLOSED','INVALID_BROWSER_SOURCE'}


class XiaohongshuLiveError(Exception):
    def __init__(self,code,diagnostic=None):
        super().__init__('小红书直播来源暂不可用')
        self.code=code;self.retryable=code=='XHS_FETCH_FAILED';self.source_failure=safe_failure(diagnostic)


def validate_url(value):
    try:
        if not isinstance(value,str) or len(value)>8192 or re.search(r'[\x00-\x20]',value):raise ValueError()
        u=urlsplit(value)
        if u.hostname=='xhslink.com' and u.scheme=='http' and u.port in (None,80) and not u.username and not u.password:
            u=u._replace(scheme='https',netloc='xhslink.com');value=urlunsplit(u)
        if u.scheme!='https' or u.username or u.password or u.port not in (None,443):raise ValueError()
        if u.hostname=='www.xiaohongshu.com' and re.fullmatch(r'/livestream/[0-9]+/?',u.path):return 'https://www.xiaohongshu.com'+u.path.rstrip('/')
        if u.hostname=='xhslink.com' and re.fullmatch(r'/[A-Za-z0-9_/-]+',u.path):return value
    except ValueError:pass
    raise XiaohongshuLiveError('INVALID_INPUT')


def candidate(value,now=None):
    now=time.time()*1000 if now is None else now
    if not isinstance(value,str) or len(value)>8192 or re.search(r'[\x00-\x20]',value):return None
    try:
        u=urlsplit(value)
        if (u.scheme not in ('http','https') or u.username or u.password or not (u.hostname or '').endswith('.xhscdn.com')
                or not u.path.lower().endswith('.flv') or u.fragment or u.port not in (None,80,443)):return None
        for expiry in parse_qs(u.query,keep_blank_values=True).get('expire',[]):
            if not re.fullmatch('[0-9]+',expiry) or int(expiry)<now/1000+60:return None
        return value
    except ValueError:return None


def parse_room(payload,now=None):
    if not isinstance(payload,dict) or payload.get('success') is not True or payload.get('code')!=0:raise XiaohongshuLiveError('XHS_PAGE_UNAVAILABLE')
    data=payload.get('data')
    if not isinstance(data,dict):raise XiaohongshuLiveError('XHS_PAGE_UNAVAILABLE')
    room=data.get('room_info')
    if not isinstance(room,dict):raise XiaohongshuLiveError('XHS_PAGE_UNAVAILABLE')
    if room.get('status')==3:return {'status':'not_live','sourceType':'xiaohongshu'}
    if room.get('status')!=2:raise XiaohongshuLiveError('XHS_LIVE_STATE_UNKNOWN')
    try:
        config=room.get('pull_config');config=json.loads(config) if isinstance(config,str) else config
        streams=config['streams']
        if not isinstance(streams,list):raise ValueError()
    except (ValueError,TypeError,KeyError):raise XiaohongshuLiveError('XHS_STREAM_UNAVAILABLE') from None
    urls=[];seen=set()
    for stream in sorted((s for s in streams if isinstance(s,dict)),key=lambda s:s.get('codec_v2')!='EF4'):
        for url in [stream.get('master_url'),*(stream.get('backup_urls') if isinstance(stream.get('backup_urls'),list) else [])]:
            if candidate(url,now) and url not in seen:seen.add(url);urls.append(url)
    if not urls:raise XiaohongshuLiveError('XHS_STREAM_UNAVAILABLE')
    return {'status':'ready','sourceType':'xiaohongshu','streamUrl':urls[0],'candidates':urls}


def fetch(url, *, timeout=8, cancel=None, probe=False):
    args=[sys.executable,'-I',str(Path(__file__).with_name('xiaohongshu_http.py'))]
    payload=json.dumps({'url':url,'timeout':max(.1,timeout),'probe':probe}).encode()
    deadline=time.monotonic()+timeout
    with subprocess.Popen(args,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL) as process:
        try:
            while True:
                if cancel and cancel():raise XiaohongshuLiveError('SOURCE_CANCELLED')
                left=deadline-time.monotonic()
                if left<=0:raise XiaohongshuLiveError('XHS_FETCH_FAILED',{'kind':'network_timeout'})
                try:output,_=process.communicate(payload,timeout=min(.2,left));break
                except subprocess.TimeoutExpired:payload=None
            try:result=json.loads(output)
            except (ValueError,TypeError):raise XiaohongshuLiveError('XHS_FETCH_FAILED') from None
            if result.get('error'):raise XiaohongshuLiveError('XHS_FETCH_FAILED',result.get('diagnostic'))
            return result
        finally:
            if process.poll() is None:process.kill()
            process.communicate()


def resolve_page(value, *, transport=fetch, deadline=None, cancel=None):
    deadline=deadline or time.monotonic()+15
    page=validate_url(value)
    for _ in range(4):
        if urlsplit(page).hostname=='www.xiaohongshu.com':return page
        left=deadline-time.monotonic()
        if left<=0:raise XiaohongshuLiveError('XHS_FETCH_FAILED')
        result=transport(page,timeout=left,cancel=cancel)
        if result.get('status') not in (301,302,303,307,308) or not result.get('location'):raise XiaohongshuLiveError('XHS_PAGE_UNAVAILABLE')
        page=validate_url(urljoin(page,result['location']))
    raise XiaohongshuLiveError('XHS_PAGE_UNAVAILABLE')


def validate_browser(page,value,now=None):
    now=time.time()*1000 if now is None else now
    try:
        at=value['captured_at']
        if type(at) is not int or at>now+5000 or now-at>120000 or validate_url(value['page_url'])!=page:raise ValueError()
        url=candidate(value['stream_url'],now)
        if not url:raise ValueError()
        return {'status':'ready','streamUrl':url,'sourceType':'xiaohongshu','sourceMethod':'browser'}
    except (KeyError,TypeError,ValueError,XiaohongshuLiveError):raise XiaohongshuLiveError('INVALID_BROWSER_SOURCE') from None


def resolve_live(value, *, browser_source=None, transport=fetch, cancel=None, timeout_ms=15000):
    deadline=time.monotonic()+timeout_ms/1000
    page=resolve_page(value,transport=transport,deadline=deadline,cancel=cancel)
    try:
        room=page.rsplit('/',1)[-1]
        response=transport('https://live-room.xiaohongshu.com/api/sns/red/live/web/v1/room/current_room_info?room_id='+room+'&source=web_live&client_type=1',timeout=max(.1,deadline-time.monotonic()),cancel=cancel)
        if response.get('status')!=200:raise XiaohongshuLiveError('XHS_AUTH_REQUIRED' if response.get('status') in (401,403) else 'XHS_FETCH_FAILED',{'kind':'http_error','http_status':response.get('status')})
        try:payload=json.loads(response['body'])
        except (ValueError,KeyError):raise XiaohongshuLiveError('XHS_PAGE_UNAVAILABLE') from None
        source=parse_room(payload)
        if source['status']=='not_live':return source
        for url in source['candidates']:
            left=deadline-time.monotonic()
            if left<=0:break
            try:
                if transport(url,timeout=left,cancel=cancel,probe=True).get('ready'):
                    return {'status':'ready','streamUrl':url,'sourceType':'xiaohongshu','sourceMethod':'anonymous'}
            except XiaohongshuLiveError as error:
                if error.code=='SOURCE_CANCELLED':raise
        raise XiaohongshuLiveError('XHS_STREAM_UNAVAILABLE')
    except XiaohongshuLiveError as error:
        if browser_source is None or error.code in ('INVALID_INPUT','SOURCE_CANCELLED'):raise
    result=validate_browser(page,browser_source)
    left=deadline-time.monotonic()
    if left<=0:raise XiaohongshuLiveError('XHS_FETCH_FAILED',{'kind':'network_timeout'})
    if not transport(result['streamUrl'],timeout=min(8,left),cancel=cancel,probe=True).get('ready'):raise XiaohongshuLiveError('XHS_STREAM_UNAVAILABLE')
    return result
