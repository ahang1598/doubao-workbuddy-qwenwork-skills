"""Bind a bounded pool of host QA children; never launch models locally."""
import time
import re
import uuid
import json
from datetime import datetime, timezone
from pathlib import Path
import sys
from runtime.live_room import ended, extracts_comments


LEGACY_WORKERS = 3
LANES = {'questions':'评论分类与问题提取', 'answers':'ASR 回答匹配'}
RETRY_SECONDS = 60
COMMENT_DRAIN_SECONDS = 600
FAILURE_CODES = {'capacity_limit','tool_unavailable','permission_denied','launch_failed','unknown'}


def parallel(task):
    from runtime.live_room import ANSWER_MATCHING_ENABLED
    return ANSWER_MATCHING_ENABLED and task.get('qa_execution') == 'parallel_v1'


def workers(task):
    rows = task.get('qa_workers')
    if isinstance(rows, list):
        return [dict(row) for row in rows if isinstance(row, dict) and isinstance(row.get('worker_id'), str)]
    legacy = task.get('qa_worker')
    return [dict(legacy)] if isinstance(legacy, dict) and isinstance(legacy.get('worker_id'), str) else []


def capability(task):
    # A confirmed running child also proves capability for pre-upgrade tasks.
    if any(row.get('status') == 'running' and row.get('host_task_id') for row in workers(task)):
        return {'status':'available', 'source':'running_worker'}
    host = task.get('qa_host_capability') or {'status':'unknown'}
    if host['status']=='unavailable' and host.get('checked_tools'):
        return {**host,'status':'unknown'}
    return host


def execution_block(task, lane=None):
    rows=[row for row in workers(task) if not lane or row.get('lane') in (None,lane)]
    if not parallel(task) or any(row.get('status') == 'running' for row in rows):return None
    state=capability(task)['status']
    if state == 'unknown':return 'capability_pending'
    if state == 'unavailable':return 'worker_unavailable'
    return 'worker_starting' if any(row.get('status') == 'starting' for row in rows) else 'worker_unavailable' if rows else 'worker_not_started'


def covered_lanes(rows):
    # Do not duplicate or change the ownership of already running pre-upgrade children.
    return set(LANES) if any(not row.get('lane') for row in rows) else {row['lane'] for row in rows}


def task_lane(task, worker_id, requested=None):
    row=next((r for r in workers(task) if r['worker_id']==worker_id),{})
    assigned=row.get('lane')
    if assigned and requested and requested != assigned:raise ValueError('QA worker lane mismatch')
    return assigned or requested


HOST_DISPATCH = ('启动 Lite 直播时按回执派发子任务。先实际发现宿主创建工具并读取权限与配额说明；'
                 '发现可创建工具即登记 available，在宿主允许时立即调用。用户没有复述“启动子任务”不能作为拒绝依据。'
                 '工具权限未核实登记 unknown；宿主明确要求单独授权时提示具体要求。'
                 'checked_tools 只列已发现的委派工具；完整发现且没有委派工具才可登记 unavailable。'
                 '同一轮只允许创建 Organizer 时，一次交付所有待启动合同，由其分别创建执行者并返回真实 ID。'
                 '创建回执不明先查询原调用。permission_denied 需给出 denial_source=host_policy 或 tool_response，'
                 '以及 evidence_ref（宿主规则标识或调用 ID，不含凭证）。')


def denial_evidence(source, reference):
    if source not in ('host_policy', 'tool_response') or not isinstance(reference, str) or not re.fullmatch(
            r'[A-Za-z0-9_.:-]{1,128}', reference):
        raise ValueError('permission_denied requires denial_source and evidence_ref from host policy or tool response; verify host tool before dispatch')
    return {'denial_source': source, 'evidence_ref': reference}


def validate_capability(value):
    if not isinstance(value,dict):raise ValueError('host capability check required')
    status=value.get('status');names=value.get('checked_tools');reason=value.get('reason');complete=value.get('discovery_complete')
    if status not in {'available','unavailable','unknown'} or type(complete) is not bool:
        raise ValueError('invalid host capability status or discovery_complete')
    if not isinstance(names,list) or len(names)>20 or any(not isinstance(n,str) or not n.strip() or len(n)>120 for n in names):
        raise ValueError('checked_tools must list observed tool names')
    if not isinstance(reason,str) or not 8<=len(reason.strip())<=240:
        raise ValueError('host capability requires a specific sanitized reason (8-240 characters)')
    if status=='unavailable' and not complete:raise ValueError('incomplete tool discovery cannot prove unavailable')
    if status=='unavailable' and names:
        raise ValueError('delegation tool observed: register available; unresolved permissions are unknown, not unavailable')
    if status=='available' and not names:raise ValueError('available capability requires an observed child-task tool')
    return {'status':status,'checked_tools':names,'discovery_complete':complete,'reason':reason.strip()}


def _write_workers(task, rows):
    task['qa_workers'] = rows
    task['qa_worker'] = next((row for row in rows if row.get('status') == 'running'), rows[0] if rows else {})


def check(store, worker_id, *, task=None):
    task = store.task() if task is None else task
    if not parallel(task) and not (worker_id and extracts_comments(task)):
        if worker_id:raise ValueError('QA worker not enabled')
        return
    if not any(row.get('status') == 'running' and row.get('worker_id') == worker_id for row in workers(task)):
        raise ValueError('QA requires a registered running subAgent; use qa-worker to inspect host bindings')


def record_first_claim(store, conn, task, worker_id):
    if not worker_id:
        return
    rows = workers(task)
    for row in rows:
        if row['worker_id'] == worker_id and not row.get('first_claim_at'):
            row['first_claim_at'] = time.time()
            _write_workers(task, rows)
            store._set_task(conn, task)
            return


def comment_window(task):
    """Return extraction phase and absolute exit time, including an earlier observed stop."""
    ends = []
    duration = task.get('max_duration_seconds')
    if duration is not None:
        start = task.get('capture_epoch')
        if start is None:
            start = datetime.fromisoformat(task['created_at'].replace('Z', '+00:00')).timestamp()
        ends.append(start + duration)
    if ended(task):
        for value in (task.get('stop_requested_at'), task.get('live_ended_at'), task.get('monitor_ended_at'),
                      (task.get('finishing') or {}).get('started_at'), task.get('media_frozen_at'), task.get('finished_at')):
            if isinstance(value, str) and value:
                value = datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()
            if isinstance(value, (int, float)):
                ends.append(value)
    deadline = None
    if ends:
        end = min(ends)
        deadline = end + COMMENT_DRAIN_SECONDS
        now = time.time()
        if now >= deadline:
            return 'expired', deadline
        if now >= end:
            return 'draining', deadline
    return ('draining' if ended(task) else 'collecting'), deadline


def needed(store, *, task=None, segments=None):
    task=store.task() if task is None else task
    from runtime import qa_pipeline
    if extracts_comments(task):
        phase, _ = comment_window(task)
        return phase == 'collecting' or (phase == 'draining' and bool(task.get('qa_jobs') or qa_pipeline.pending_comments(store,include_deferred=True)))
    if task.get('capture_status') not in {'ended','stopped','failed'} or task.get('worker_status') not in {'done','stopped','failed'}:return True
    segments=store.segments() if segments is None else segments
    if qa_pipeline.enabled(task):
        from runtime import clarifications
        state=qa_pipeline.progress(store)
        return bool(state['pending'] or state['waiting_asr'] or task.get('qa_job') or clarifications.pending_page(segments))
    from runtime import qa_workflow, clarifications
    segments=store.segments() if segments is None else segments
    return bool(task.get('qa_job') or qa_workflow.active_jobs(task)
        or any(s.get('review_status')!='skipped' and not qa_workflow.valid(s) for s in segments)
        or qa_workflow.cross_page(segments) or not qa_workflow.history_ready(task,segments)
        or clarifications.pending_page(segments)
        or task.get('asr_provider')=='ark' and not qa_workflow.final_ready(task))


def delegation_prompt(store, rows):
    """One complete handoff, including both lanes, for a host organizer."""
    pending=[r for r in rows if r.get('status') in {'starting','stopped'} and r.get('lane') in LANES]
    if not pending:return ''
    lite=Path(__file__).resolve().parents[1]
    lines=[f'在原任务 {store.root} 启动互动问答，不能另建采集任务。',
        f'Lite 工作目录：{lite}；先读 SKILL.md 和 references/live-review.md 的独立互动问答部分。',
        f'使用 Python：{sys.executable}；继承原执行环境，INSPECT_USAGE_CONTEXT_DIR 指向原任务目录。',
        '若主回执同时提供 credential_worker_action，先准备其合同，将凭证 delegation_prompt 与本说明一并交给同一个 Organizer，优先启动常驻凭证维护；不能耗尽唯一顶层创建机会后才补凭证任务。',
        '这是一次完整的两路问答委派。先核查当前宿主工具的角色、单次调用、本轮创建次数及并发限制。',
        '如果主 Agent 只能创建一个 OrganizerAgent 且该角色支持再委派，将本说明和全部待启动任务一次性交给它；不能把唯一一次委派只用于评论提取。',
        '豆包主 Agent 的 create_agent 仅接受 OrganizerAgent 时，把本说明完整放入 hint；不要对 questions 和 answers 分别调用顶层 create_agent。hint 只传给组织者，下级任务的 subtask 必须再次携带各自完整上下文，不能假定继承聊天。',
        'OrganizerAgent 须按其实际工具说明分别启动下列独立执行者；不支持再委派时如实报告限制，不递归创建来绕过额度，不由主 Agent 串行代做。',
        '组织者负责启动登记：每创建一个实际执行者并确认运行，就立即调用 qa-worker 的 action=started，传对应 worker_id、真实下级 host_task_id、running_confirmed=true，再通知该执行者领取；不要等两路都建好或等子任务先处理。组织者的接收或排队回执不是两路运行成功。',
        '已运行任务保持原绑定，启动结果未知的先查询原宿主任务，不重复创建。待启动任务：']
    task = store.task()
    comments_only = extracts_comments(task)
    if comments_only:
        lines = [f'在原任务 {store.root} 委派一个评论提取执行者，提取观众问题和对其他商品的明确求购意向。不要匹配主播回答。',
                 f'工作目录 {lite}。组织者确认执行者已运行后，按 qa-worker 合同登记 started 和真实 host_task_id。']
        _, deadline = comment_window(task)
        if deadline is not None:
            cutoff = datetime.fromtimestamp(deadline, timezone.utc).isoformat(timespec='seconds')
            lines.append(f'本场采集时长上限 {task["max_duration_seconds"]} 秒。' if task.get('max_duration_seconds') is not None else '本场已停采。')
            lines.append(f'评论提取预计最晚退出时间为 {cutoff}。采集起点确定或提前停采后，以领取回执的截止时间为准。')
        else:
            lines.append('本场未设固定采集时长，以下播或停采时间起算收尾。')
    for row in pending:
        argv=[sys.executable,str(lite/'scripts/live_inspect.py'),*row['claim_argv']]
        lines.append(f"- {row['task_name']}：worker_id={row['worker_id']}，lane={row['lane']}；领取参数（按当前宿主执行环境调用）：{json.dumps(argv,ensure_ascii=False)}")
        if row.get('host_task_id'):
            lines.append(f"  已有宿主执行者 {row['host_task_id']}：先用宿主 send_message/续办工具唤醒原任务并确认运行，再沿原 worker_id/host_task_id 登记 started；不要新建 Organizer 或拼造主 Agent ID 代替执行者。确认原任务已退出且无法续办时，逐 worker 登记 unavailable 和具体原因后再补位，不能假装运行。")
    for row in rows:
        if row.get('status')=='running':
            lines.append(f"已运行，不能重复创建：{row.get('task_name', '原问答任务')}，worker_id={row['worker_id']}，host_task_id={row.get('host_task_id', '')}。")
    lines += ['执行者先确认自己的 worker 为 running；若仍 starting，向组织者报告待登记并等待，不能反复执行领取、搜索环境或阅读源码绕过校验。',
        '每个执行者读完上述指引后立即沿自己的 lane 使用 qa-next/qa-submit，完整读取本次合同和模板再提交，不为正常领取反复阅读实现源码；成功提交带 --next 时直接处理返回的下一份合同，不再重复 qa-next。不得改写另一任务结果或调用风险审核、停止采集、复盘命令。',
        ('采集期间 caught_up 仅表示暂时无评论，继续等待新评论。达到采集截止或提前停采后，队列清空即退出；'
         '有积压最多续做10分钟。收到 finish-comment-extraction 或达到最晚退出时间立即结束，组织者确认退出后登记 stopped。'
         if comments_only else 'caught_up/waiting_* 不是任务结束；按回执等待并继续。采集、媒体与风险结束后沿 qa-next --final 完成收尾，直到 done/not_required 指向复盘。'),
        '启动失败逐 worker 登记 unavailable、not_started_confirmed=true、reason_code 和具体脱敏 reason；区分工具明示限制、实际调用拒绝和未核实推测。不得借用别的执行者 ID。']
    return '\n'.join(lines)


def contract(store):
    task=store.task()
    lanes = {'questions':'观众提问与其他商品求购提取'} if extracts_comments(task) else LANES
    host=capability(task)
    rows = workers(task)
    starting = [row for row in rows if row.get('status') == 'starting']
    resumable = [row for row in rows if row.get('status') == 'stopped' and row.get('host_task_id') and row.get('lane') in lanes]
    running = [row for row in rows if row.get('status') == 'running']
    failed=[row for row in rows if row.get('status')=='unavailable']
    cooling=[row for row in failed if row.get('retry_after',0)>time.time()]
    required=needed(store)
    split=task.get('qa_pipeline') in {'split_v1','comments_v1'}
    capacity=len(lanes) if split else LEGACY_WORKERS
    missing=len(set(lanes)-covered_lanes(running+starting)) if split else capacity-len(running)-len(starting)
    refill=bool(set(lanes)-covered_lanes(running+starting+cooling)) if split else missing>len(cooling)
    missing_running=len(set(lanes)-covered_lanes(running)) if split else max(0,capacity-len(running))
    display_rows=[{**row, **({'task_name':lanes[row['lane']],
        'claim_argv':['qa-next','--task-dir',str(store.root),'--worker-id',row['worker_id'],'--lane',row['lane']]}
        if row.get('lane') in lanes else {})} for row in rows]
    status = 'complete' if not required else 'degraded' if running and missing_running else 'running' if running else 'starting' if starting else 'unavailable' if failed else 'not_started'
    action=('stop-qa-subagents' if not required else 'resume-qa-subagents' if resumable else 'spawn-qa-subagents' if starting else
            'start-qa-subagents' if refill else 'retry-qa-subagents' if missing else 'observe-qa-subagents')
    if required and host['status'] != 'available':
        status='capability_pending' if host['status']=='unknown' else 'unavailable'
        action='check-host-capability'
    result = {'status':status, 'host_capability':host, 'worker_id':running[0]['worker_id'] if running else (starting[0]['worker_id'] if starting else None),
            'workers':display_rows, 'capacity':capacity, 'running_count':len(running),
            **({'delegation_prompt':delegation_prompt(store,display_rows) if required else ''} if split else {}),
            'missing_count':missing_running, 'next_action':action,
            'retry_after':min((row['retry_after'] for row in cooling),default=None),
            'control_argv':['qa-worker','--task-dir',str(store.root)],
            'input_path':str(store.root/'qa-worker-control.json'),
            'control_submit_argv':['qa-worker','--task-dir',str(store.root),'--input-file',str(store.root/'qa-worker-control.json')],
            'prepare_template':{'action':'prepare'},
            'capability_template':{'action':'capability','capability_check':{'status':'unknown','checked_tools':[],
                'discovery_complete':False,'reason':'填写实际核查范围、发现的工具及尚不能确认的原因'}},
            'instruction':'check-host-capability 时先检查当前宿主可用工具及按需工具发现入口，按子任务/委派/并行执行能力搜索并读取候选工具说明，不只匹配 subAgent 名字。'
                '将实际核查结果用 capability_template 提交；发现可创建子任务的工具标 available 并填准确工具名，未完成发现或权限受阻只能标 unknown，完整核查确认无工具才标 unavailable。'
                '不可用、未知和启动失败须披露 QA 尚未启动，不能称槽位已登记即已完成；不能复制占位原因或假造核查。'
                '新任务按两个独立任务调度：questions 评论分类与问题提取、answers ASR 回答匹配；不是三个通用 worker，不要求凑齐固定并发数才开始处理。'
                'start-qa-subagents 执行 prepare；spawn-qa-subagents 先读 delegation_prompt，核查创建次数与组织者再委派能力后再决定调用方式，不能先耗掉唯一委派机会只创建一路。'
                '宿主允许直接创建多个执行者时按 workers 分别委派；只能创建一个 OrganizerAgent 且支持下级委派时，一次传入完整 delegation_prompt，由其分别创建两路实际执行者。已运行的一路立即处理，不等待另一路。'
                'worker_id 通过子任务提示传给 CLI，不是宿主创建工具必须支持的参数。豆包顶层 create_agent 仅接受 OrganizerAgent 时，一次 hint 必须包含全部待启动任务；hint 不自动传给下级，组织者再按自身工具参数把完整上下文交给实际执行者。'
                '登记的是实际执行者 agent_id，不是 Organizer 的接收回执；同一请求的 Organizer 创建次数限制不能转述成整个任务的执行者并发上限。'
                '已 running/starting 不重复创建；分别确认运行或记录真实失败，创建结果未知先查询原宿主任务。'
                'observe/resume 时先查询已绑定宿主任务；idle-resumable 或 waiting_review 后退出的先唤醒原执行者，不消耗新的 Organizer 创建额度。resume-qa-subagents 按 delegation_prompt 续办，确认运行后沿原绑定登记 started；不能把主 Agent 或拼接 ID 登记为独立执行者。'
                'retry-qa-subagents 在 retry_after 后再 prepare；期间继续风险，不循环等待。stop-qa-subagents 确认子任务退出后登记 stopped，不再补位。'
                '每个子任务使用自己 worker_id，只调用 qa-next/qa-submit，按合同修复当前工作项；SQLite 事务会分配不同片段。'
                'qa_pipeline=split_v1 时 questions 只提取评论问题，answers 只匹配 ASR 或已确认运营回复，分别保存、重试；不要跨合同提交。'
                '每个任务只领取绑定 lane 的合同，不能交替代做另一任务；一个流程阻塞时另一个继续领取、提交。旧无 lane 的已运行者沿原冻结合同处理，不强行改绑。'
                'caught_up/waiting_review/waiting_qa 时短暂等待再领取，不结束子任务；recheck 也可能是实时跨段补查，按冻结清单执行。'
                '采集、媒体与风险全部结束后，空闲 worker 调用 qa-next --final；收尾唯一执行者由合同绑定，其余等待，直到 done/not_required 且指向复盘。'
                '子任务不得执行 review-next、停止采集或生成复盘。确认退出后分别提交 action=stopped；启动失败逐 worker 提交 action=unavailable、not_started_confirmed=true、reason_code 和 reason。'
                'reason 仅写具体脱敏事实（如宿主允许的并发数或缺失的工具名称），不得复制原始工具输出、凭证、签名URL；原因未知也写明已核对的事实，不猜额度。',
            'failure_reason_codes':sorted(FAILURE_CODES),
            'input_fields':['action','worker_id','host_task_id','running_confirmed','exit_confirmed','not_started_confirmed','reason_code','reason','capability_check']}
    if extracts_comments(task):
        result['instruction'] = ('评论提取已结束；确认执行者退出后沿原绑定登记 stopped，勿补位。' if not required else
                                 '核查宿主实际委派能力并提交 capability。可用时 prepare，仅委派 questions，按 delegation_prompt 登记实际执行者。'
                                 '若同时需凭证维护，将两份提示交给同一组织者。失败按合同登记，已启动的勿重复创建。')
    result['instruction'] = HOST_DISPATCH + result['instruction']
    result['input_fields'].extend(['denial_source','evidence_ref'])
    return result


def control(store, value):
    if not isinstance(value,dict):raise ValueError('invalid QA worker control')
    launch=[]
    with store.connection(True) as conn:
        task=store._task(conn)
        lanes = {'questions'} if extracts_comments(task) else LANES
        if not extracts_comments(task) and task.get('interaction_mode') != 'separate_v1':raise ValueError('independent QA required')
        rows=workers(task)
        action=value.get('action')
        changed=[]
        if action=='capability':
            checked=validate_capability(value.get('capability_check'))
            if any(row.get('status')=='running' for row in rows) and checked['status']=='unavailable':
                raise ValueError('running QA child contradicts unavailable capability')
            previous=task.get('qa_host_capability') or {}
            if any(previous.get(k)!=v for k,v in checked.items()):
                task['qa_host_capability']={**checked,'checked_at':time.time()}
                changed.append({'status':checked['status'],'capability_check':checked})
        elif action=='prepare':
            if capability(task)['status'] != 'available':return contract(store)
            if not extracts_comments(task) and not parallel(task) and task.get('qa_job'):raise ValueError('finish existing serial QA job before enabling parallel')
            if not needed(store,task=task,segments=store._segments(conn)):return contract(store)
            rows=[row for row in rows if row.get('status') in {'starting','running'} or row.get('status')=='unavailable' and row.get('retry_after',0)>time.time()
                  or task.get('qa_pipeline') in {'split_v1','comments_v1'} and row.get('lane') in lanes and row.get('status')=='stopped' and row.get('host_task_id')]
            if task.get('qa_pipeline') in {'split_v1','comments_v1'}:
                # Old failed generic slots are not evidence that either new task is running.
                rows=[row for row in rows if row.get('lane') in lanes or row.get('status') in {'starting','running'}]
                targets=[lane for lane in lanes if lane not in covered_lanes(rows)]
            else:targets=[None]*max(0,LEGACY_WORKERS-len(rows))
            for lane in targets:
                row={'status':'starting','worker_id':uuid.uuid4().hex,'prepared_at':time.time()}
                if lane:row['lane']=lane
                rows.append(row);launch.append(row['worker_id']);changed.append(row)
            task['qa_execution']='parallel_v1'
        elif action=='unavailable':
            target=value.get('worker_id')
            candidates=[row for row in rows if row.get('worker_id') == target] if target else [row for row in rows if row.get('status') == 'starting']
            if not candidates or any(row.get('status') not in {'starting','unavailable'} and not
                    (task.get('qa_pipeline') in {'split_v1','comments_v1'} and row.get('lane') in lanes and row.get('status')=='stopped')
                    for row in candidates) or value.get('not_started_confirmed') is not True:raise ValueError('confirm failed launch before marking unavailable')
            code,reason=value.get('reason_code'),value.get('reason')
            if not target or code not in FAILURE_CODES or not isinstance(reason,str) or not 8<=len(reason.strip())<=240:
                raise ValueError('each failed worker requires reason_code and a specific sanitized reason (8-240 characters)')
            evidence = denial_evidence(value.get('denial_source'), value.get('evidence_ref')) if code=='permission_denied' else {}
            if code=='tool_unavailable' and capability(task)['status']!='unavailable':
                raise ValueError('tool_unavailable requires completed host capability discovery; use action=capability first')
            for row in candidates:
                if row.get('status')=='unavailable' and row.get('reason'):
                    if row.get('reason_code')!=code or row['reason']!=reason.strip():raise ValueError('conflicting failed launch replay')
                    continue
                row.update(status='unavailable',reason_code=code,reason=reason.strip(),failed_at=time.time(),retry_after=time.time()+RETRY_SECONDS,**evidence)
                changed.append(row)
            task['qa_execution']='parallel_v1'
        elif action in {'started','stopped'}:
            worker_id=value.get('worker_id')
            row=next((row for row in rows if row.get('worker_id') == worker_id),None)
            if not row:raise ValueError('QA worker binding mismatch')
            host=value.get('host_task_id')
            if not isinstance(host,str) or not host.strip():raise ValueError('observed host task ID required')
            if row.get('host_task_id') not in (None,host):raise ValueError('QA host binding mismatch')
            if action=='started':
                if any(other.get('worker_id') != worker_id and other.get('host_task_id') == host and other.get('status') in {'starting','running'} for other in rows):
                    raise ValueError('QA host binding already registered')
                allowed={'starting','running','stopped'} if task.get('qa_pipeline') in {'split_v1','comments_v1'} and row.get('lane') in lanes else {'starting','running'}
                if row.get('status') not in allowed or value.get('running_confirmed') is not True:
                    raise ValueError('host running confirmation required')
                row.update(status='running',host_task_id=host,started_at=row.get('started_at',time.time()))
                if row not in workers(task):changed.append(row)
            else:
                if value.get('exit_confirmed') is not True:raise ValueError('host exit confirmation required')
                if row.get('status')!='stopped':
                    row.update(status='stopped',host_task_id=host,stopped_at=time.time())
                    changed.append(row)
        else:raise ValueError('unsupported QA worker action')
        _write_workers(task,rows)
        store._set_task(conn,task)
        from runtime.store import now_iso
        for row in changed:
            detail={'action':action,**{k:row[k] for k in ('worker_id','host_task_id','status','reason_code','reason','retry_after','capability_check','lane','denial_source','evidence_ref') if k in row}}
            conn.execute('INSERT INTO operation_logs(created_at,kind,message,segment_id) VALUES(?,?,?,?)',
                         (now_iso(),'qa_worker',json.dumps(detail,ensure_ascii=False),None))
    result=contract(store)
    if launch and result['status'] != 'complete':
        result['launch_worker_ids']=launch
        result['next_action']='spawn-qa-subagents'
    return result
