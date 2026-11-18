"""一次性浏览器候选交接文件，不进入任务 JSON、报告或遥测。"""
import json
import time
from urllib.parse import urlsplit
from runtime.store import atomic_json
from runtime.platform_support import file_lock
from runtime.xiaohongshu_live import XiaohongshuLiveError


DOUYIN_ROOM_HOSTS = {'live.douyin.com', 'www.douyin.com'}


def source_module(source):
    from runtime import bilibili_live, xiaohongshu_live
    return bilibili_live if urlsplit(source).hostname in bilibili_live.HOSTS else xiaohongshu_live


def prepare_candidate(source,value):
    if urlsplit(source).hostname in DOUYIN_ROOM_HOSTS:
        from runtime.douyin_live import validate_douyin_live_url, _candidate, DouyinLiveError
        try:
            page = validate_douyin_live_url(value['page_url'])
            now = time.time() * 1000
            at = value['captured_at']
            stream = value['stream_url']
            url = urlsplit(stream)
            if (page != validate_douyin_live_url(source) or type(at) is not int
                    or not now - 120000 <= at <= now + 5000
                    or not (url.hostname or '').endswith('.douyincdn.com')
                    or url.port not in (None, 80, 443) or not _candidate(stream, {}, now)):
                raise ValueError()
            return {'page_url':page, 'captured_at':at, 'stream_url':stream}
        except (KeyError, ValueError, TypeError, AttributeError, DouyinLiveError):
            raise XiaohongshuLiveError('INVALID_BROWSER_SOURCE') from None
    module=source_module(source)
    validate_url=module.validate_url
    validate_browser=module.validate_browser
    error_type=getattr(module,'BilibiliLiveError',XiaohongshuLiveError)
    validate_url(source)
    if not isinstance(value,dict):raise error_type('INVALID_BROWSER_SOURCE')
    page=validate_url(value.get('page_url'))
    if urlsplit(page).hostname not in {'www.xiaohongshu.com','live.bilibili.com'}:raise error_type('INVALID_BROWSER_SOURCE')
    # Short links are matched after the worker validates the actual redirect chain.
    if urlsplit(source).hostname not in {'xhslink.com','b23.tv'} and validate_url(source)!=page:raise error_type('INVALID_BROWSER_SOURCE')
    result=validate_browser(page,value)
    if result.get('status')=='not_live':return {'page_url':page,'captured_at':value['captured_at'],'status':'not_live'}
    return {k:value[k] for k in ('page_url','captured_at','stream_url')}


def save_candidate(store,value, *, ignore_finished=False):
    from runtime.stop_signal import read
    with file_lock(store.root/'.browser-source.lock',timeout=1):
        task=store.task()
        error_type=getattr(source_module(task['source']),'BilibiliLiveError',XiaohongshuLiveError)
        reason=(read(store.root) or {}).get('reason')
        finished=(task.get('live_ended_at')
                  or (task.get('stop_requested') and task.get('stop_reason') in {'duration_limit','execution_limit','user_request'})
                  or reason in {'user_request','execution_limit'}
                  or (task.get('capture_status') in {'ended','stopped'} and
                      task.get('source_end_reason') in {'offline','user_stop','duration_limit','execution_limit','end_requested'})
                  or (task.get('stop_audit') or {}).get('reason') in {'user_request','execution_limit'})
        if ignore_finished and task.get('kind')=='live' and task.get('capture_status')!='failed' and finished:
            return False
        if finished or task.get('kind')!='live' or task.get('stop_requested') or task.get('media_frozen') or task.get('capture_status') in {'ended','stopped','failed'}:
            raise error_type('BROWSER_SOURCE_TASK_CLOSED')
        if task.get('source_refresh_required') and time.time()>=task.get('source_refresh_deadline',0):raise error_type('BROWSER_SOURCE_TIMEOUT')
        atomic_json(store.root/'.browser-source.json',prepare_candidate(task['source'],value))
        return True


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


def refresh_due(store, task):
    if (not task.get('source_refresh_required') or task.get('stop_requested') or task.get('media_frozen')
            or task.get('capture_status') in {'ended','stopped','failed'}):return False
    return time.time()<task.get('source_refresh_deadline',0) and not (store.root/'.browser-source.json').exists()


def attach_refresh(store,data):
    task=store.task()
    if not refresh_due(store,task):return
    deadline=task['source_refresh_deadline']
    instruction=('立即复用本次已验证的取流方式和当前直播页取得新候选；宿主页面取流已成功时直接沿用，不重新探测 CDP。使用 CDP 时从 Inspect 根目录执行 python3 scripts/xiaohongshu-cdp-source.py --url <本次原直播链接> --output <私有browser-source.json>，'
                 '若返回 XHS_NOT_LIVE，将回执中的 browser_source 写入同名 JSON 字段，执行下方 command_argv 交回停播观察；其余情况通过已有本机 CDP 浏览器提取并探测 FLV；不要仅轮询 status，也不要另开录制或质检流程。'
                 'CDP 不可用时按 references/browser-stream-fallback.md 使用宿主页面执行能力。'
                 '在期限内执行 command_argv 交给原任务，不导出 Cookie。'
                 '两种浏览器路径均不可用时说明具体阻塞。')
    if urlsplit(task['source']).hostname in {'live.bilibili.com','b23.tv'}:
        instruction=('按 references/browser-stream-fallback.md 的 B 站补充取流，在宿主当前直播页执行 '
                     'scripts/bilibili-browser-observation.js，验证房间归属并取得 FLV。'
                     '观察返回 not_live 时提交含 page_url、captured_at、status 的 browser_source；在原期限内通过 command_argv 交给原任务。'
                     '浏览器不可用时说明具体阻塞。')
    if urlsplit(task['source']).hostname in DOUYIN_ROOM_HOSTS:
        instruction = ('按 references/browser-stream-fallback.md 的抖音取流步骤，从当前同一房间的直播页获取新 FLV。'
                       '把真实 page_url、captured_at 和 stream_url 写入私有 browser_source 文件，执行 command_argv 交回原任务。')
    instruction += '本轮期限届满后查原任务 status，按回执继续重连或收尾；补流超时不能确认停播。'
    data['source_refresh']={'next_action':'refresh-live-source','deadline':deadline,
        'command_argv':['resume','--task-dir',str(store.root),'--input-file','<browser-source.json>'],'instruction':instruction}
    target=data['next'] if isinstance(data.get('next'),dict) and data['next'].get('next_action') else data
    if target.get('next_action') in {'status','resume','refresh-live-source'}:
        target['next_action']=data['next_action']='refresh-live-source'
        target['continuation_instruction']=data['continuation_instruction']=instruction
        for result in (data,target):
            result.pop('poll_after_seconds',None)
            result.pop('wait_command_argv',None)
        target['message']=data['message']='直播源暂不可用，正在等待浏览器补流；尚未确认停播。'
    if data.get('after_delivery_next_action')=='status':data['after_delivery_next_action']='refresh-live-source'
