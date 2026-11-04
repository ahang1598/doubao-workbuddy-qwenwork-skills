"""一次性浏览器候选交接文件，不进入任务 JSON、报告或遥测。"""
import json
import time
from urllib.parse import urlsplit
from runtime.store import atomic_json
from runtime.platform_support import file_lock
from runtime.xiaohongshu_live import validate_url, validate_browser, XiaohongshuLiveError


def prepare_candidate(source,value):
    validate_url(source)
    if not isinstance(value,dict):raise XiaohongshuLiveError('INVALID_BROWSER_SOURCE')
    page=validate_url(value.get('page_url'))
    if urlsplit(page).hostname!='www.xiaohongshu.com':raise XiaohongshuLiveError('INVALID_BROWSER_SOURCE')
    # Short links are matched after the worker validates the actual redirect chain.
    if urlsplit(source).hostname!='xhslink.com' and validate_url(source)!=page:raise XiaohongshuLiveError('INVALID_BROWSER_SOURCE')
    validate_browser(page,value)
    return {k:value[k] for k in ('page_url','captured_at','stream_url')}


def save_candidate(store,value):
    task=store.task()
    if task.get('kind')!='live' or task.get('stop_requested') or task.get('media_frozen') or task.get('capture_status') in {'ended','stopped','failed'}:
        raise XiaohongshuLiveError('BROWSER_SOURCE_TASK_CLOSED')
    if task.get('source_refresh_required') and time.time()>=task.get('source_refresh_deadline',0):raise XiaohongshuLiveError('BROWSER_SOURCE_TIMEOUT')
    candidate=prepare_candidate(task['source'],value)
    with file_lock(store.root/'.browser-source.lock',timeout=1):
        atomic_json(store.root/'.browser-source.json',candidate)


def take_candidate(store):
    path=store.root/'.browser-source.json'
    try:
        with file_lock(store.root/'.browser-source.lock',timeout=1):
            with path.open('rb') as f:raw=f.read(65537)
            path.unlink(missing_ok=True)
        if len(raw)>65536:raise ValueError()
        return json.loads(raw)
    except FileNotFoundError:return None
    except (ValueError,TypeError):raise XiaohongshuLiveError('INVALID_BROWSER_SOURCE') from None
