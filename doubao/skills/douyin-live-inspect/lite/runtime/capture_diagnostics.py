"""Offline capture diagnosis and portable, allowlisted evidence (no source or logs)."""
import hashlib
import html
import json
import re
import sys
import sqlite3

CODES = {'XHS_FETCH_FAILED','XHS_PAGE_UNAVAILABLE','XHS_AUTH_REQUIRED','XHS_STREAM_UNAVAILABLE','XHS_LIVE_STATE_UNKNOWN','BROWSER_SOURCE_TIMEOUT','BROWSER_SOURCE_TASK_CLOSED','INVALID_BROWSER_SOURCE','STREAM_RETRY_EXHAUSTED','DOUYIN_FETCH_FAILED','DOUYIN_PAGE_UNAVAILABLE',
         'DOUYIN_FLV_UNAVAILABLE','DOUYIN_RESOLVER_UNAVAILABLE','SOURCE_CANCELLED','none'}
REASONS = {'stream_retry_exhausted','source_resolution_failed','capture_failed','offline',
           'unknown','user_stop','duration_limit','execution_limit'}
CATEGORIES = {'http_error','process_exit','encoder_unavailable','permission_denied','tls_error',
              'network_timeout','connection_error','invalid_media','stream_missing'}
EXCEPTIONS = {'SourceError','XiaohongshuResolveError','DouyinResolveError','PermissionError','OSError','RuntimeError',
              'OperationalError','MemoryError','TimeoutError','FileNotFoundError','ValueError'}
FILES = {'xiaohongshu_live.py','xiaohongshu_source.py','media.py','realtime.py','platform_support.py','douyin_live.py','store.py','video.py'}
FUNCTIONS = {'resolve_xiaohongshu','resolve_live','fetch','capture','capture_session','resolve_with_retry','resolve_douyin','collect','consume',
             'join','start','guarded_capture','media_popen','connection','nofollow_open','capture_video'}
MESSAGES = {
    'out_of_memory':'运行时明确报告内存不足，保留已检测内容并按原任务收尾。',
    'storage_error':'运行时明确报告本地存储异常，保留原任务及已有证据，按安全错误码排查。',
    'source_resolution_failed':'最终失败发生在来源解析阶段；历史拉流错误仅作为此前尝试的证据。',
    'cause_unknown':'采集失败；现有证据不足以确定具体原因，不能据此判断停播、登录限制或排除网络/TLS/编码器故障。',
    'http_error':'采集进程报告 HTTP 错误；状态码只能证明该次请求结果，不能单凭它判断停播或需要登录。',
    'encoder_unavailable':'采集进程报告编码器不可用，请核对实际执行环境的 FFmpeg 编码器支持。',
    'permission_denied':'采集发生访问拒绝，请按安全调用帧核对实际执行环境的文件或进程权限，不扩大权限或另建任务。',
    'tls_error':'采集进程报告证书校验错误，请核对实际执行环境的受信任证书，保持 TLS 校验。',
    'network_timeout':'采集进程报告网络超时，请核对实际执行环境的网络连通性；不能推断直播已结束。',
    'connection_error':'采集进程报告连接错误，请核对实际执行环境的 DNS 与网络连接。',
    'invalid_media':'采集进程报告媒体格式无效，需核对该次输入是否为可解码的媒体流。',
    'stream_missing':'采集进程报告所需媒体轨道缺失，需核对音视频轨道与采集参数。',
}


def _integer(value):
    return type(value) is int and abs(value) <= 2**53-1


def _allowed(value, choices):
    return isinstance(value,str) and value in choices


def record_attempt(store, detail):
    previous=store.task().get('capture_process_attempts')
    attempts=[safe_process(v) for v in previous[-2:]] if isinstance(previous,list) else []
    store.update_task(capture_process_diagnostic=safe_process(detail),
                      capture_process_attempts=attempts+[safe_process(detail)],
                      capture_execution_platform=sys.platform if sys.platform in {'win32','darwin','linux'} else 'unknown')


def safe_process(value):
    if not isinstance(value, dict):return {}
    result={}
    if _allowed(value.get('category'),CATEGORIES):result['category']=value['category']
    if _integer(value.get('exit_code')):result['exit_code']=value['exit_code']
    if type(value.get('http_status')) is int and 400<=value['http_status']<=599:
        result['http_status']=value['http_status']
    return result


def safe_exception(value):
    if not isinstance(value,dict):return {}
    result={}
    from runtime.http_fetch import safe_failure
    source = safe_failure(value.get('source_failure'))
    if source:result['source_failure'] = source
    if _allowed(value.get('category'),EXCEPTIONS):result['category']=value['category']
    if value.get('code')=='OUT_OF_MEMORY':result['code']='OUT_OF_MEMORY'
    for key in ('errno','winerror','sqlite_errorcode'):
        if _integer(value.get(key)):result[key]=value[key]
    frames=[]
    for frame in (value.get('frames') if isinstance(value.get('frames'),list) else [])[-8:]:
        if not isinstance(frame,dict) or not _allowed(frame.get('file'),FILES):continue
        item={'file':frame['file']}
        if _allowed(frame.get('function'),FUNCTIONS):item['function']=frame['function']
        if type(frame.get('line')) is int and 0<frame['line']<100000:item['line']=frame['line']
        frames.append(item)
    if frames:result['frames']=frames
    return result


def summarize(task):
    if task.get('kind','live')!='live' or task.get('capture_status')!='failed':return None
    process=safe_process(task.get('capture_process_diagnostic'))
    exception=safe_exception(task.get('capture_diagnostic'))
    stream=safe_exception(task.get('stream_diagnostic'))
    code=task.get('source_error_code') or task.get('capture_error')
    assessment='cause_unknown'
    # The final runtime exception outranks earlier FFmpeg attempts. A process
    # category is evidence of the final attempt only when no later layer failed.
    if exception.get('code')=='OUT_OF_MEMORY' or exception.get('category')=='MemoryError':
        assessment='out_of_memory'
    elif 'sqlite_errorcode' in exception:
        assessment='storage_error'
    elif exception.get('category')=='PermissionError':
        assessment='permission_denied'
    elif exception.get('category')=='DouyinResolveError' or _allowed(code,CODES-{'STREAM_RETRY_EXHAUSTED','SOURCE_CANCELLED','none'}):
        assessment='source_resolution_failed'
    elif exception.get('category') in {None,'SourceError'} and code in (None,'none','STREAM_RETRY_EXHAUSTED'):
        assessment=process.get('category','cause_unknown')
        if assessment=='process_exit':assessment='cause_unknown'
    result={'schema_version':1,'assessment':assessment,
        'offline_confirmed':False,
        'source_error_code':code if _allowed(code,CODES) else 'unknown',
        'source_end_reason':task.get('source_end_reason') if _allowed(task.get('source_end_reason'),REASONS) else 'unknown',
        'live_source_status':task.get('live_source_status') if _allowed(task.get('live_source_status'),{'live','not_live','unknown'}) else 'unknown',
        'execution_platform':task.get('capture_execution_platform') if _allowed(task.get('capture_execution_platform'),{'win32','darwin','linux'}) else 'unknown',
        'missing_evidence':[] if process else ['capture_process_diagnostic'],
        'attempts':[safe_process(v) for v in (task.get('capture_process_attempts') or [])[-3:] if isinstance(v,dict)]
            if isinstance(task.get('capture_process_attempts',[]),list) else []}
    if process:result['capture_process_diagnostic']=process
    identity=task.get('task_id') or task.get('id')
    if isinstance(identity,str) and re.fullmatch('[0-9a-fA-F]{32}',identity):result['task_id']=identity
    for key,value in (('capture_diagnostic',exception),('stream_diagnostic',stream)):
        if value:result[key]=value
    result['message']=('浏览器补流交接超时，未确认直播停播或流地址不可读。' if code=='BROWSER_SOURCE_TIMEOUT' else MESSAGES[assessment])
    result['instruction']='已自动核对原任务保存的采集诊断；source_ended 是收尾信号，不是停播证据。仅在用户明确要求排查时展示本摘要和诊断附件，沿原 next_action 收尾；不重启、不新建任务、不自动重试拉流。执行平台指采集进程所在系统，不从客户端系统推断。'
    return result


def section(summary):
    raw=json.dumps(summary,ensure_ascii=False,indent=2,allow_nan=False)
    return '<section aria-label="采集失败诊断"><h2>采集失败诊断</h2><p>'+html.escape(summary['message'])+'</p><details><summary>查看脱敏证据与排查说明</summary><pre style="white-space:pre-wrap;overflow-wrap:anywhere">'+html.escape(raw)+'</pre></details></section>'


def public_summary(task):
    """User-facing impact only; process evidence remains in the original task."""
    if task.get('kind','live') != 'live' or task.get('capture_status') != 'failed':return None
    reason = ('浏览器补流等待超时' if task.get('source_error_code')=='BROWSER_SOURCE_TIMEOUT' else '来源暂不可解析' if task.get('source_end_reason') == 'source_resolution_failed'
              else '采集异常')
    return {'message':reason+'，采集已中断，未确认直播停播。已采集内容继续处理，缺失范围以报告覆盖情况为准。',
            'offline_confirmed':False,
            'instruction':'只向用户说明缺失范围和原因，不交付内部诊断、错误堆栈或诊断附件；不得将解析失败称为直播结束。沿原 next_action 继续。'}


def attach(store,data, *, include_diagnostics=False):
    try:
        summary=(summarize if include_diagnostics else public_summary)(store.task())
    except (OSError, ValueError, sqlite3.Error):
        if include_diagnostics:
            data['diagnostic_delivery']={'type':'chat','status':'unavailable',
                'message':'附加诊断暂不可读取，请继续原 next_action。'}
        return
    if summary is None:return
    data['capture_failure']=summary
    if not include_diagnostics:return
    # No subprocess or POSIX-specific path construction: the private task root
    # already establishes access; new children inherit its Windows DACL.
    from runtime.static_delivery import atomic
    content='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>采集失败诊断</title><body>'+section(summary)+'</body></html>'
    digest=hashlib.sha256(content.encode('utf-8')).hexdigest()[:24]
    folder=store.root/'diagnostics'
    path=folder/('capture-'+digest+'.html')
    try:
        for candidate in (folder,path):
            if candidate.is_symlink() or (candidate.exists() and getattr(candidate.lstat(),'st_file_attributes',0)&0x400):
                raise ValueError('diagnostic path must not be a link')
        folder.mkdir(mode=0o700,exist_ok=True)
        if not path.exists() or path.read_bytes()!=content.encode('utf-8'):atomic(path,content)
        data['diagnostic_delivery']={'type':'html_attachment','status':'ready','path':str(path.resolve()),
            'message':'请通过宿主附件能力交付此独立诊断 HTML，并展示实际附件入口；本地 Windows 同样交付附件，不只发送路径。已交付相同路径则无需重复。诊断附件不是质检报告，不确认报告成功。'}
    except (OSError,ValueError):
        data['diagnostic_delivery']={'type':'chat','status':'unavailable',
            'message':'诊断附件无法写入或被占用，请在对话完整交付 capture_failure；保留原任务和失败原因，不重启采集、不扩大权限。'}
