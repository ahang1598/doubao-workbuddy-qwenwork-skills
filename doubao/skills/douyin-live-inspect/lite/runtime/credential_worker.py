"""Resident Doubao credential worker; renewal scheduling stays in Python."""
import json
import time
import uuid
from datetime import datetime, timezone
from runtime.finishing import TERMINAL
from runtime.qa_worker import HOST_DISPATCH, capability, denial_evidence

# Host tokens last ten minutes; leave time for tool/agent scheduling delays.
REFRESH_SECONDS = 180
RECHECK_SECONDS = 60


def exit_deadline(task):
    duration = task.get('max_duration_seconds')
    if task.get('kind', 'live') != 'live' or duration is None:
        return None
    deadline = (task.get('asr_host_refresh') or {}).get('worker_exit_at')
    if deadline is not None:
        return deadline
    start = task.get('capture_epoch')
    if start is None:
        start = datetime.fromisoformat(task['created_at'].replace('Z', '+00:00')).timestamp()
    return start + duration


def eligible(task):
    if task.get('media_frozen') or task.get('asr_policy') not in {'remote_first','local_first'}:
        return False
    if task.get('kind', 'live') != 'live':
        return True
    if task.get('stop_requested') or task.get('live_ended_at') or task.get('capture_status') in TERMINAL:
        return False
    deadline = exit_deadline(task)
    return deadline is None or time.time() < deadline


def begin_cycle(request, *, trigger, now):
    return {**request, 'status':'pending', 'cycle':request.get('cycle',0)+1,
            'requested_at':now, 'trigger':trigger}


def dispatch_due(task):
    if not eligible(task):return False
    request = task.get('asr_host_refresh') or {}
    if request.get('worker_status') in {'starting','running'}:return False
    return not request or time.time() >= request.get('next_refresh_at',0)


def next_command(store, rid):
    return ['credential-worker','--task-dir',str(store.root),'--refresh-id',rid,
            '--action','next','--wait-seconds','30']


def attach(store, data):
    if data.get('workflow_complete') or not eligible(store.task()):return
    created=False
    with store.connection(True) as conn:
        task = store._task(conn)
        if not eligible(task):return
        request = task.get('asr_host_refresh') or {}
        worker = request.get('worker_status')
        if worker in {'unavailable','stopped'}:
            if time.time() < request.get('next_refresh_at',0):return
            request = {}  # Only a confirmed absent/exited child can be replaced.
        if not request.get('resident') and worker not in {'starting','running'}:
            request = {**request, 'resident':True, 'request_id':request.get('request_id') or uuid.uuid4().hex,
                       'cycle':request.get('cycle',0)+1, 'status':'pending',
                       'requested_at':request.get('requested_at',time.time()) if request.get('status')=='pending' else time.time(),
                       'trigger':'startup', 'next_refresh_at':time.time()}
            task['asr_host_refresh'] = request
            store._set_task(conn, task)
            created=True
    if created:
        try:store.log('mediakit_credential_refresh',json.dumps({'phase':'requested','refresh_id':request['request_id'],
            'cycle':request['cycle'],'trigger':'startup'}))
        except Exception:pass
    rid = request['request_id']
    argv = ['credential-worker','--task-dir',str(store.root),'--refresh-id',rid]
    worker = request.get('worker_status')
    data['credential_worker_action'] = {
        'request_id':rid, 'status':worker or 'pending', 'host_task_id':request.get('host_task_id'),
        'next_action':'observe-credential-subagent' if worker else 'prepare-credential-subagent',
        'command_argv':argv + ['--action','prepare'],
        'next_refresh_at':request.get('next_refresh_at'),
        'heartbeat_at':request.get('heartbeat_at'),
        'instruction':(HOST_DISPATCH+'任务启动就派发常驻凭证 subAgent，不等待 ASR 报错；它独立于评论提取。'
            '确认宿主允许后再执行 command_argv；收到 launch_allowed=true 立即调用宿主创建工具。'
            '同回执有 qa_worker_action 时，先准备凭证和 QA 的全部合同，在同一个 Organizer 委派中传入全部完整提示，优先启动凭证子任务。'
            '已有 OrganizerAgent 时沿其调度，不重复创建 Organizer 或绕过层级限制。'
            '创建结果未知或 starting/running 心跳停止时查询原子任务，禁止重复创建；确认从未启动才登记 unavailable，确认退出才登记 stopped。'
            '主 Agent 保留本回执继续 next_action，不等待刷新或 QA 完成。')}
    qa = data.get('qa_worker_action')
    if qa:
        qa['instruction'] = '同回执 credential_worker_action 必须先准备并一并传给 Organizer，优先启动常驻凭证子任务。' + qa.get('instruction','')


def control(store, *, refresh_id, action, host_task_id=None, reason_code=None, denial_source=None, evidence_ref=None, discovery_complete=False):
    allowed = False
    with store.connection(True) as conn:
        task = store._task(conn)
        request = task.get('asr_host_refresh') or {}
        if request.get('request_id') != refresh_id or (action != 'stopped' and not eligible(task)):
            raise ValueError('credential refresh binding expired')
        worker = request.get('worker_status')
        if not request.get('resident') and request.get('status') != 'pending' and action not in {'started','stopped'}:
            return {'status':request.get('status'),'launch_allowed':False}
        if action == 'prepare':
            if not worker:
                request = {**request,'worker_status':'starting'}
                deadline = exit_deadline(task)
                if deadline is not None:
                    request['worker_exit_at'] = deadline
                allowed = True
        elif action in {'started','stopped'}:
            if action == 'stopped' and worker == 'stopped' and host_task_id and host_task_id == request.get('host_task_id'):
                return {'status':'stopped','launch_allowed':False,'request_id':refresh_id}
            if worker not in {'starting','running'} or not host_task_id or len(host_task_id)>160:
                raise ValueError('observed credential subagent ID required')
            if request.get('host_task_id') not in (None,host_task_id):
                raise ValueError('credential subagent binding mismatch')
            request = {**request,'worker_status':'running' if action=='started' else 'stopped','host_task_id':host_task_id}
            if action=='stopped':request['next_refresh_at']=time.time()
        elif action == 'unavailable':
            if worker != 'starting' or reason_code not in {'capacity_limit','tool_unavailable','permission_denied','launch_failed'}:
                raise ValueError('confirm subagent never started before unavailable')
            if request.get('heartbeat_at'):
                raise ValueError('credential worker already sent a heartbeat; check the original child')
            if reason_code=='tool_unavailable' and (capability(task)['status']=='available' or
                    not (capability(task)['status']=='unavailable' or discovery_complete)):
                raise ValueError('complete host tool discovery before marking unavailable')
            evidence = denial_evidence(denial_source,evidence_ref) if reason_code=='permission_denied' else {}
            request = {**request,**evidence,'worker_status':'unavailable','status':'missing','reason_code':reason_code,
                       'next_refresh_at':time.time()+RECHECK_SECONDS}
            for segment in store._segments(conn):
                waiting = segment.get('asr_host_refresh') or {}
                if waiting.get('requested_at') == request['requested_at'] and waiting.get('status') == 'pending':
                    store._update_segment(conn, segment['id'], asr_host_refresh={**waiting,'status':'missing'})
        else:raise ValueError('unsupported credential worker action')
        task['asr_host_refresh'] = request
        store._set_task(conn, task)
    try:store.log('mediakit_credential_refresh', json.dumps({'phase':action,'refresh_id':refresh_id,
            **{key:request[key] for key in ('host_task_id','reason_code','denial_source','evidence_ref') if key in request}}))
    except Exception:pass
    if action == 'stopped':
        return {'status':'stopped','launch_allowed':False,'request_id':refresh_id}
    argv = next_command(store,refresh_id)
    schedule = ''
    if task.get('kind', 'live') == 'live':
        deadline = exit_deadline(task)
        if deadline is None:
            schedule = '本场直播采集到结束，无固定时长或钟点，最晚在采集结束时退出。'
        else:
            until = datetime.fromtimestamp(deadline, timezone.utc).isoformat(timespec='milliseconds')
            schedule = f'本场直播采集时长上限 {task["max_duration_seconds"]} 秒，最晚退出时间 {until}。到点立即退出。'
        schedule += '提前停采、下播或采集失败时，收到 finish-credential-subagent 立即退出，无需等待报告。'
    return {'status':request.get('worker_status'),'launch_allowed':allowed,'request_id':refresh_id,
            'control_command_argv':['credential-worker','--task-dir',str(store.root),'--refresh-id',refresh_id],
            'delegation_prompt':('你是豆包常驻凭证维护 subAgent。'+schedule+'立即执行原 Skill CLI，参数为 '+json.dumps(argv,ensure_ascii=False)+
                '。持续按回执 command_argv 执行，每次使用新的宿主工具调用及当次注入环境；不要使用持久 shell 或后台循环复制旧环境。'
                '程序决定何时刷新：启动立即导入，Token 变化后每3分钟更新，未变化或缺失则1分钟后重查；无需你计算时间。'
                'refresh-credentials 会原子写入任务 .mediakit-credentials.json；禁止读取或打印文件、环境值、认证响应。'
                '导入后继续执行回执中的 credential-worker next；收到 finish-credential-subagent 立即结束。'
                '只做凭证维护，不接管主任务 status、质检或 QA，不等待用户回复。导入不等于续期或 ASR 成功。'),
            'instruction':'仅 launch_allowed=true 时将完整 delegation_prompt 交给宿主子任务。创建成功后给 control_command_argv 加 --action started --host-task-id <真实ID>；确认未启动则加 --action unavailable --reason-code <capacity_limit/tool_unavailable/permission_denied/launch_failed> --not-started-confirmed；仅凭证任务确认完整发现且无创建工具时传 --discovery-complete；permission_denied 另传 --denial-source host_policy|tool_response 和 --evidence-ref 宿主规则标识或调用ID；确认已退出则加 --action stopped --host-task-id <真实ID> --exit-confirmed，未知结果先查询。'}


def tick(store, refresh_id, *, wait_seconds=0, sleep=time.sleep):
    deadline = time.monotonic()+wait_seconds
    while True:
        scheduled=False
        with store.connection(True) as conn:
            task = store._task(conn)
            request = task.get('asr_host_refresh') or {}
            if request.get('request_id') != refresh_id or not eligible(task) or request.get('worker_status') in {'stopped','unavailable'}:
                return {'next_action':'finish-credential-subagent','reason':'refresh_request_inactive'}
            if request.get('worker_status') not in {'starting','running'}:
                raise ValueError('prepare credential worker before maintenance')
            now=time.time()
            if request.get('status') != 'pending' and now >= request.get('next_refresh_at',0):
                request=begin_cycle(request,trigger='scheduled',now=now)
                scheduled=True
            if scheduled or now-request.get('heartbeat_at',0)>=15:
                request['heartbeat_at']=now
                task['asr_host_refresh']=request
                store._set_task(conn,task)
        if scheduled:
            try:store.log('mediakit_credential_refresh',json.dumps({'phase':'requested','refresh_id':refresh_id,
                'cycle':request['cycle'],'trigger':'scheduled'}))
            except Exception:pass
        if request['status']=='pending':
            return {'next_action':'refresh-credentials','cycle':request.get('cycle'),
                    'command_argv':['refresh-credentials','--task-dir',str(store.root),'--refresh-id',refresh_id,
                                    '--refresh-cycle',str(request.get('cycle',0))],
                    'instruction':'现在在新的宿主工具调用中执行 command_argv 导入当次环境；按返回命令继续常驻维护。'}
        if time.monotonic() >= deadline:
            return {'next_action':'credential-worker-next','next_refresh_at':request['next_refresh_at'],
                    'command_argv':next_command(store,refresh_id),
                    'instruction':'继续执行 command_argv；等待和刷新时机由程序控制，不另加 sleep，不结束子任务。'}
        wake_at = request['next_refresh_at']
        exit_at = exit_deadline(task)
        if exit_at is not None:
            wake_at = min(wake_at, exit_at)
        sleep(min(1,max(0,deadline-time.monotonic()),max(0,wake_at-time.time())))


def continuation(store, refresh_id, result):
    task = store.task()
    request=task.get('asr_host_refresh') or {}
    if (not eligible(task) or request.get('request_id') != refresh_id
            or not request.get('resident') or request.get('worker_status') in {'stopped','unavailable'}):
        result['next_action']='finish-credential-subagent'
        return
    result.update(next_action='credential-worker-next',command_argv=next_command(store,refresh_id),
                  next_refresh_at=request.get('next_refresh_at'),
                  continuation_instruction='本次导入结束，立即执行 command_argv 继续常驻凭证维护；不要结束子任务，不接管主流程。')
