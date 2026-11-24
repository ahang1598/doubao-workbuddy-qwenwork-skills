"""Independent host-model QA jobs; risk submissions never depend on these results."""
import copy
import hashlib
import json
import time
import uuid

from runtime import interactions, recap_asr, clarifications

MAX_FAILED_ATTEMPTS = 5


class ValidationErrors(ValueError):
    def __init__(self, errors):
        super().__init__("QA validation failed")
        self.errors = errors


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def enabled(task):
    from runtime.live_room import ANSWER_MATCHING_ENABLED
    return ANSWER_MATCHING_ENABLED and task.get('interaction_mode') == 'separate_v1'


def segment_source(segment):
    return {k:copy.deepcopy(segment.get(k)) for k in ('id','start_ms','end_ms','subtitles')} | {
        'sales_observation':copy.deepcopy((segment.get('review_result') or {}).get('sales_observation'))}


def valid(segment):
    return segment.get('qa_review_status') == 'done' and segment.get('qa_source_hash') == digest(segment_source(segment))


def active_jobs(task):
    return [job for job in task.get('qa_jobs', []) if isinstance(job, dict) and isinstance(job.get('id'), str)]


def remove_job(task, job):
    if (task.get('qa_job') or {}).get('id') == job.get('id'):
        task.pop('qa_job', None)
    else:
        task['qa_jobs'] = [item for item in active_jobs(task) if item['id'] != job.get('id')]
        if not task['qa_jobs']:task.pop('qa_jobs')


def own_job(store, conn, task, job, worker_id):
    from runtime.qa_worker import parallel, workers
    if parallel(task):
        owner=job.get('assigned_worker_id')
        running={row['worker_id'] for row in workers(task) if row.get('status') == 'running'}
        if owner and owner != worker_id and owner in running:
            return {'status':'waiting_qa','next_action':'qa-next --final','instruction':'收尾工作由其他 worker 执行，等待后重新领取。'}
        job['assigned_worker_id']=worker_id
        store._set_task(conn,task)
    result=response(store,job,worker_id=worker_id)
    return {**result,**repair_response(store,job,worker_id=worker_id)} if job.get('last_error') else result


def cross_page(segments, busy=()):
    questions=interactions.summarize(segments)
    by_id={s['id']:s for s in segments}
    for segment in sorted(segments,key=lambda s:(s['start_ms'],s['id'])):
        if segment['id'] in busy:continue
        missing=(segment.get('qa_receipt') or {}).get('pending_predecessors',[])
        if not valid(segment) or not missing or any(not valid(by_id[sid]) and by_id[sid].get('review_status') != 'skipped' for sid in missing if sid in by_id):continue
        checked=segment.get('qa_cross_checked',{})
        rows=[]
        for question in questions:
            if question.get('segment_id') not in missing or question['start_ms'] >= segment['end_ms']:continue
            signature=digest({k:question.get(k) for k in ('id','question','evidence_ids','start_ms','product','offer','question_detail')})
            if checked.get(question['id']) != signature:rows.append((question,signature))
        if rows:
            rows=rows[:8]
            return {'questions':[q for q,_ in rows],'segments':[segment_source(segment)]},segment['id'],{q['id']:signature for q,signature in rows}
    return None


def history_hash(segments):
    questions = interactions.summarize(segments)
    return digest({'segments':[segment_source(s) for s in segments],
                   'questions':[{k:q.get(k) for k in ('id','question','evidence_ids','start_ms','product','offer','question_detail')}
                                for q in questions]})


def history_ready(task, segments):
    if not interactions.summarize(segments):return True
    current = history_hash(segments)
    return any(receipt.get('history_hash') == current for receipt in task.get('qa_recheck_receipts',[]))


def final_ready(task, source=None):
    source = recap_asr.source(task) if source is None else source
    return source is not None and (task.get('qa_final') or {}).get('source_hash') == digest(source)


def progress(store):
    task, segments = store.task(), store.segments()
    if not enabled(task):return {'status':'legacy_inline'}
    from runtime import qa_pipeline
    if qa_pipeline.enabled(task):
        from runtime.qa_worker import parallel, contract
        worker=contract(store) if parallel(task) else None
        return {**qa_pipeline.progress(store), 'pipeline':'split_v1',
                **({'execution':'parallel','worker':worker} if worker else {'execution':'serial'}),
                'next_action':'qa-worker' if worker else 'qa-next',
                'instruction':'评论提问和字幕/运营回复匹配独立领取、保存与重试。晚入库问题自动回查已有证据。'}
    ready = [s for s in segments if s.get('review_status') == 'done']
    pending = sum(not valid(s) for s in ready)
    cross_pending = cross_page(segments) is not None
    from runtime.qa_worker import parallel, contract
    worker = contract(store) if parallel(task) else None
    jobs = active_jobs(task) + ([task['qa_job']] if isinstance(task.get('qa_job'),dict) else [])
    blocked = next((job for job in jobs if job.get('attempts',0) >= MAX_FAILED_ATTEMPTS), None)
    return {**({'execution':'parallel','worker':worker} if worker else {'execution':'serial'}), 'status':'blocked' if blocked else 'pending' if pending or cross_pending else 'caught_up', 'done':sum(valid(s) for s in ready),
            'pending':pending, 'cross_pending':cross_pending, 'waiting_review':sum(s.get('review_status') not in {'done','skipped'} for s in segments),
            'unavailable':sum(s.get('review_status') == 'skipped' for s in segments),
            'active_job_id':jobs[0]['id'] if jobs else None, 'active_job_ids':[job['id'] for job in jobs],
            'final_ready':final_ready(task) if task.get('asr_provider') == 'ark' else None,
            'next_action':'qa-worker' if worker else 'qa-next', 'argv':['qa-worker' if worker else 'qa-next','--task-dir',str(store.root)],
            'instruction':('按 worker 合同启动或观察独立问答 subAgent；主 Agent 继续风险，不转入串行问答。' if worker else '在独立问答模型上下文执行；风险提交与问答提交分别重试。')}


def interleave_due(store):
    """Prefer eligible QA between risk batches; a failed job never blocks risk."""
    task = store.task()
    from runtime.qa_worker import parallel
    if not enabled(task) or parallel(task) or (task.get('qa_job') or {}).get('last_error'):return False
    from runtime import qa_pipeline
    if qa_pipeline.enabled(task):return bool(qa_pipeline.progress(store)['pending'])
    pending = [s for s in store.segments() if s.get('review_status') != 'skipped' and not valid(s)]
    return bool(pending and min(pending,key=lambda s:(s['start_ms'],s['id'])).get('review_status') == 'done')


def repair_response(store, job, *, duplicate=False, worker_id=None):
    exhausted = job.get('attempts',0) >= MAX_FAILED_ATTEMPTS
    blocked = exhausted or duplicate or job.get('repeated_error_count',0) >= 3
    return {'status':'repair_blocked' if blocked else 'repair_required',
            'next_action':'report-qa-blocked' if exhausted else 'repair-qa-result' if blocked else 'qa-submit', 'retryable':not blocked,
            'attempts':job.get('attempts',0),'max_failed_attempts':MAX_FAILED_ATTEMPTS,'attempts_remaining':max(0,MAX_FAILED_ATTEMPTS-job.get('attempts',0)),
            'limit_reached':exhausted,'errors':copy.deepcopy(job.get('last_errors',[job['last_error']])),
            'error':copy.deepcopy(job['last_error']), 'duplicate':duplicate,
            'instruction':('累计失败已达上限，停止提交和重新领取；保留草稿与错误清单，报告问答阻塞，主流程仍可继续风险。不将未完成问答标为成功。' if exhausted else '一次核对 errors 中全部可独立检查的问题，再提交完整修正版；同一失败文件禁止原样重交。错误类型或字段变化不会重置累计失败次数。'),
            'risk_continue_argv':['review-next','--task-dir',str(store.root)],
            'submission_contract':response(store,job,worker_id=worker_id)['submission_contract']}


def record_failure(store, conn, task, job, result_hash, errors, *, worker_id=None):
    details = [{'code':'QA_VALIDATION_FAILED','field':getattr(error,'field',None) or ('questions/comment_checks' if job['kind']=='questions' else 'interaction_review' if job['kind']=='final' else 'clarification_checks' if job['kind']=='clarification' else 'qa_observations/qa_checks'),
        'reason':getattr(error,'diagnostic_reason','invalid_submission'),
        'message':str(error) if isinstance(error,ValueError) else 'invalid QA submission structure',
        **{k:getattr(error,k) for k in ('missing_qa_ids','allowed_qa_ids','allowed_statuses','allowed_evidence_ids') if hasattr(error,k)}} for error in errors]
    detail=details[0]
    signature=digest([{k:v for k,v in d.items() if k!='message'} for d in details])
    repeated=job.get('repeated_error_count',0)+1 if job.get('error_signature')==signature else 1
    job.update(last_error=detail,last_errors=details,attempts=job.get('attempts',0)+1,last_failed_hash=result_hash,
               error_signature=signature,repeated_error_count=repeated)
    store._set_task(conn,task)
    from runtime.store import now_iso
    conn.execute('INSERT INTO operation_logs(created_at,kind,message,segment_id) VALUES(?,?,?,?)',
        (now_iso(),'qa_review_validation',json.dumps({'job_id':job['id'],'phase':job['kind'],
         'code':detail['code'],'field':detail['field'],'reason':detail['reason'],'error_count':len(details),
         'attempt':job['attempts'],'max_failed_attempts':MAX_FAILED_ATTEMPTS,
         'limit_reached':job['attempts']>=MAX_FAILED_ATTEMPTS,'repeated_error_count':repeated,
         'repair_blocked':repeated>=3 or job['attempts']>=MAX_FAILED_ATTEMPTS}),job.get('segment_id')))
    return repair_response(store,job,worker_id=worker_id)


def prerequisite(store):
    from runtime import qa_pipeline
    if qa_pipeline.enabled(store.task()):
        state=qa_pipeline.progress(store)
        task=store.task()
        if state['pending'] or state['waiting_asr']:
            from runtime.qa_worker import parallel
            command='qa-worker' if parallel(task) else 'qa-next'
            return {'next_action':command,'argv':[command,'--task-dir',str(store.root)],
                    'instruction':'先完成评论提取与答案匹配的独立队列；阻塞只影响对应工作项，未完成检查不能算主播未回答。','progress':state}
        return clarification_prerequisite(store)
    state = progress(store)
    if state.get('status') == 'blocked':
        task=store.task()
        job=next(j for j in active_jobs(task)+([task['qa_job']] if task.get('qa_job') else []) if j.get('attempts',0)>=MAX_FAILED_ATTEMPTS)
        return repair_response(store,job,worker_id=job.get('assigned_worker_id'))
    if state.get('execution') == 'parallel' and (state.get('pending') or state.get('cross_pending') or (store.task().get('asr_provider') == 'ark' and not state.get('final_ready'))):
        return {'next_action':'qa-worker','argv':['qa-worker','--task-dir',str(store.root)],
                'instruction':'让已登记问答 subAgent 完成问答和整场校准；主 Agent 不执行问答。风险未完成时继续 review-next。'}
    if state.get('pending') or state.get('waiting_review'):
        return {'next_action':'qa-next' if state.get('pending') else 'review-next',
                'argv':['qa-next' if state.get('pending') else 'review-next','--task-dir',str(store.root)],
                'instruction':'先完成独立问答任务及剩余审核，再生成复盘；不重做已保存的风险结果。'}
    if not history_ready(store.task(), store.segments()):
        return {'next_action':'qa-next --recheck','argv':['qa-next','--task-dir',str(store.root),'--recheck'],
                'instruction':'逐项补查全部历史问题与全场分段字幕，不能只复核最近代表问题。'}
    if store.task().get('asr_provider') == 'ark' and not final_ready(store.task()):
        return {'next_action':'qa-next --final', 'argv':['qa-next','--task-dir',str(store.root),'--final'],
                'instruction':'在独立问答模型上下文完成全场分段 ASR 问答校准；复盘模型只读取校准结果。'}
    return clarification_prerequisite(store)


def clarification_prerequisite(store):
    task=store.task()
    if task.get('kind','live')!='live' or not clarifications.pending_page(store.segments()):return None
    job=task.get('qa_job')
    if job and job.get('kind')=='clarification' and job.get('last_error'):
        return repair_response(store,job)
    from runtime.qa_worker import parallel
    command='qa-worker' if parallel(task) else 'qa-next'
    return {'next_action':command if command=='qa-worker' else 'qa-next --clarifications',
            'argv':[command,'--task-dir',str(store.root)]+(['--clarifications'] if command=='qa-next' else []),
            'instruction':'执行 qa-next --clarifications 完成现场澄清分批补查；每批最多8项、4段、64条字幕，不重判风险，不执行问答匹配。'}


def response(store, job, *, worker_id=None):
    if job['kind'] in {'questions','answers'}:
        from runtime.qa_pipeline import response as split_response
        return split_response(store,job,worker_id)
    template = {'task_id':store.task_id, 'job_id':job['id']}
    if job['kind'] == 'clarification':
        template['segments']=[{'segment_id':s['id'],'clarification_observations':[],'clarification_checks':[]} for s in job['source']['segments']]
        instruction=clarifications.INSTRUCTION+clarifications.CHECK_INSTRUCTION+' 这是收尾补查，只更新已有疑点，不新增疑点，不重判原风险。每段清单都必须核对；本次字幕仅代表所列范围，不概括未提供的时段。'
        fields=None
    elif job['kind'] == 'recheck':
        template.update(segments=[], checked_question_ids=[])
        instruction = (interactions.INSTRUCTION +
            '复核本次冻结的全部问题与完整字幕。segments 每项填 segment_id、qa_observations；仅用 reply_to 补充有证据的回答，不新建、删除问题或重判风险。'
            'checked_question_ids 列出已逐项复核的全部问题ID；未找到可靠对应回答的保留原状态，不为了覆盖率猜测。每项回答必须来自该段字幕，保留否定和条件。')
        fields = {'segment_id':'回答所在片段', 'qa_observations':[{'reply_to':'原问题ID',
                  'answer_evidence_ids':['该段字幕ID'],'answer':'逐字原文','answer_complete':True}]}
    elif job['kind'] == 'final':
        template['interaction_review'] = []
        instruction = job['source']['instruction']
        fields = {'comment_id':'原评论 ID', 'is_question':True, 'reason':'具体核对结论',
                  'answer_evidence_ids':[], 'answer_complete':False, 'checked_evidence_ids':[],
                  'question_product':'已确认商品，未知留空','question_offer':'','question_detail':'一个具体疑问'}
    else:
        template.update(qa_observations=[], qa_checks=[])
        from runtime.live_room import INSTRUCTION as viewer_instruction
        instruction = viewer_instruction + interactions.INSTRUCTION + interactions.CHECK_INSTRUCTION_V2.replace('同批前段新提取的问题也要续查；','只检查本次冻结的 qa_checklist；') + interactions.FOCUS_INSTRUCTION_V2
        fields = None
    input_path = store.root / ('qa-result-'+job['id']+'.json')
    if not input_path.exists():
        from runtime.store import atomic_json
        atomic_json(input_path,template)
    path = str(input_path)
    source = copy.deepcopy(job['source'])
    if job['kind']=='clarification':
        source['clarification_context']=clarifications.model_context({'items':source.pop('items'),'omitted_count':0})
    if job.get('compact_history'):
        instruction = instruction.replace('related_questions 保留同组原始提问','related_questions 仅列同组原问题 ID 和提问时间').replace('并列的问题与候选原文','问题与候选索引，并按索引读取本段原文')
        source['qa_context'] = [{
            **{k:q[k] for k in ('id','product','offer','question_scope','start_ms','status','related_count','related_omitted_count') if k in q},
            'question':' '.join(q['question_detail'].split()),
            'related_questions':[{k:member[k] for k in ('id','start_ms')} for member in q.get('related_questions',[])]
        } for q in source['qa_context']]
        source['qa_focus'] = [{'question_id':row['question_id'],'candidates':[
            {'source':candidate['source'],'evidence':[{'id':e['id']} for e in candidate['evidence']]}
            for candidate in row['candidates']]} for row in source['qa_focus']]
        instruction += ('qa_context 只含 ASR 开始前的未解答问题，question 是保留商品、尺码、对象和限制条件的规范问题，不是评论原文。'
                        '同组 related_questions 仅列原问题 ID 与提问时间；归组不代表已经回答。qa_focus 仅为索引：问题按 question_id 查 qa_context 或 viewer_context.comments，候选原文按 evidence.id 查本段 subtitles。'
                        '新问题的 question_detail 必填规范问句，保留数字、规格、否定和条件；同商品同条件的同义问题复用相同规范问句，不能只填宽泛主题。')
    from runtime.qa_worker import parallel
    worker_args = ['--worker-id',worker_id] if parallel(store.task()) and worker_id else []
    guide={}
    if job['kind']=='live':
        frozen=job['source']
        candidates={row['question_id']:sorted({e['id'] for c in row['candidates'] for e in c['evidence']}) for row in frozen['qa_focus']}
        comments={c['id']:c for c in frozen.get('viewer_context',{}).get('comments',[])}
        known=interactions.context_questions(frozen['qa_context'])
        guide={'reply_to_ids':[q['id'] for q in known],
               'applies_to_options':{q['id']:interactions.applies_to_ids(q,known,frozen.get('sales_observation')) for q in known},
               'check_options':[{'id':key,'allowed_statuses':['unanswered'] if kind=='question' else ['not_question','unclear'],
                   'checked_evidence_ids':candidates.get(key,[]),
                   **({'question_template':{'question':comments[key]['text'],'question_evidence_ids':[key]},
                       'after_extraction_without_answer':['unanswered','unclear'] if candidates.get(key) else []} if key in comments else {})}
                   for key,kind in frozen['qa_checklist'].items()]}
        instruction+=(' 按 check_options 逐项处理：question_template 仅用于确认是问题的评论，补齐具体疑问和实际回答后提交；非问题不要提取。'
                      'allowed_statuses 用于未提取评论或历史问题；新评论已提取但无回答且有候选时改用 after_extraction_without_answer。'
                      '已关联回答的项不再填 qa_checks；已提取且无候选的新问题也不重复填 qa_checks。只复制给定 ID，checked_evidence_ids 仅表示核对过候选，不代表回答成立。')
        instruction+=(' applies_to 默认省略；需要共用回答时只能从 applies_to_options[reply_to] 选，空列表表示不可共用。'
                      '选项仅表示范围相同，仍须核对回答内容和时间；“怎么保存”“能否常温”“是否冷藏”是不同具体疑问，不能仅因同属保存主题就合并。'
                      '不同范围若各自有回答，分开写 reply_to 并逐题引用完整原文；未知商品不借关联补成已知。不要删掉未答问题来消除校验错误。')
    return {'status':'ready','next_action':'qa-submit','job_id':job['id'],'kind':job['kind'],
            'input':source, 'submission_contract':{
                **guide,
                'instruction':instruction+' 只完成本次检查合同，不判断风险或生成复盘。失败只修改本次结果。',
                'template':template, 'item_template':fields, 'input_path':path,
                'submit_command_argv':['qa-submit','--task-dir',str(store.root),'--input-file',path]+worker_args}}


def claim_live_parallel(store, worker_id):
    with store.connection(True) as conn:
        task=store._task(conn)
        from runtime.qa_worker import check, workers, record_first_claim
        check(store,worker_id,task=task)
        record_first_claim(store,conn,task,worker_id)
        segments=store._segments(conn)
        job=next((item for item in active_jobs(task) if item.get('assigned_worker_id') == worker_id),None)
        if not job:
            running={row['worker_id'] for row in workers(task) if row.get('status') == 'running'}
            job=next((item for item in active_jobs(task) if item.get('assigned_worker_id') not in running),None)
            if job:
                job['assigned_worker_id']=worker_id
                store._set_task(conn,task)
        if job:
            if job['kind']=='recheck':return own_job(store,conn,task,job,worker_id)
            segment=store._segment(conn,job['segment_id'])
            current=segment_source(segment) if segment.get('review_status') == 'done' else None
            if digest(current) == job['source_hash']:
                return own_job(store,conn,task,job,worker_id)
            remove_job(task,job);store._set_task(conn,task)
        legacy=task.get('qa_job')
        if legacy:
            return own_job(store,conn,task,legacy,worker_id)
        page=cross_page(segments,{item.get('cross_segment_id') for item in active_jobs(task)})
        if page:
            source,sid,signatures=page
            job={'id':uuid.uuid4().hex,'kind':'recheck','source':source,'source_hash':digest(source),
                 'cross_segment_id':sid,'cross_signatures':signatures,'assigned_worker_id':worker_id,'created_at':time.time()}
            task['qa_jobs']=active_jobs(task)+[job];store._set_task(conn,task)
            return response(store,job,worker_id=worker_id)
        ready=sorted((segment for segment in segments if segment.get('review_status') != 'skipped' and not valid(segment)),
                     key=lambda segment:(segment['start_ms'],segment['id']))
        if not ready:return {'status':'caught_up','next_action':'review-next' if task.get('capture_status') not in {'stopped','ended','failed'} else 'status'}
        busy={item.get('segment_id') for item in active_jobs(task)}
        segment=next((item for item in ready if item.get('review_status') == 'done' and item['id'] not in busy),None)
        if not segment:return {'status':'waiting_review','next_action':'status','instruction':'等待风险审核或其他 QA worker 完成已领取片段。'}
        from runtime.live_room import context
        source=segment_source(segment)
        source['viewer_context']=context(conn,store.session_id,segment) if task.get('live_room') else {}
        previous=interactions.context(segments,segment['start_ms'],lookahead=[source],pending_only=True)
        source['qa_context']=previous
        source['qa_checklist']=interactions.check_targets(previous,source,version=2)
        source['qa_focus']=interactions.focus(previous,source,version=2)
        job={'id':uuid.uuid4().hex,'kind':'live','segment_id':segment['id'],'source':source,
             'source_hash':digest(segment_source(segment)),'compact_history':True,
             'pending_predecessors':[s['id'] for s in segments if s['end_ms']<=segment['start_ms'] and s.get('review_status')!='skipped' and not valid(s)],
             'assigned_worker_id':worker_id,'created_at':time.time()}
        task['qa_jobs']=active_jobs(task)+[job]
        store._set_task(conn,task)
        return response(store,job,worker_id=worker_id)


def claim(store, *, final=False, recheck=False, clarifications_only=False, worker_id=None, lane=None):
    from runtime.live_room import ANSWER_MATCHING_ENABLED
    from runtime.live_room import extracts_comments
    if extracts_comments(store.task()) and not clarifications_only:
        from runtime.qa_pipeline import claim_comments
        if lane == 'answers' or recheck:return {'status':'disabled'}
        return claim_comments(store,worker_id)
    if not ANSWER_MATCHING_ENABLED and not clarifications_only:
        return {'status':'disabled','message':'问答匹配已下线；评论在复盘中总结。'}
    from runtime.qa_worker import check, parallel
    check(store,worker_id)
    if sum((final,recheck,clarifications_only))>1:raise ValueError('final, recheck and clarifications are mutually exclusive')
    from runtime import qa_pipeline
    if qa_pipeline.enabled(store.task()):
        return qa_pipeline.claim(store,worker_id,final=final or recheck or clarifications_only,lane=lane)
    if clarifications_only:
        with store.connection(True) as conn:
            task=store._task(conn);check(store,worker_id,task=task)
            if task.get('qa_job') and (ANSWER_MATCHING_ENABLED or task['qa_job'].get('kind') == 'clarification'):
                if not ANSWER_MATCHING_ENABLED:
                    task['qa_job'].pop('assigned_worker_id', None)
                    store._set_task(conn,task)
                return own_job(store,conn,task,task['qa_job'],worker_id)
            segments=store._segments(conn)
            if parallel(task) and (active_jobs(task) or cross_page(segments) or any(s.get('review_status')!='skipped' and not valid(s) for s in segments)):
                return {'status':'live_qa_required','next_action':'qa-next','instruction':'先完成逐段问答和跨段补查，再领取收尾工作。'}
            if (task.get('capture_status') not in {'ended','stopped','failed'} or task.get('worker_status') not in {'done','stopped','failed'}
                    or any(s.get('review_status') not in {'done','skipped'} for s in segments)):
                return {'status':'waiting_review','next_action':'review-next','instruction':'采集、媒体处理和逐段审核结束后再补查。'}
            source=clarifications.pending_page(segments)
            if not source:return {'status':'done','next_action':'recap-input --begin'}
            job={'id':uuid.uuid4().hex,'kind':'clarification','source':source,'source_hash':digest(source),'created_at':time.time()}
            if not ANSWER_MATCHING_ENABLED and task.get('qa_job'):
                task.setdefault('qa_jobs', []).append(task['qa_job'])
            task['qa_job']=job;store._set_task(conn,task)
            return own_job(store,conn,task,job,worker_id)
    if recheck:
        with store.connection(True) as conn:
            task = store._task(conn)
            check(store,worker_id,task=task)
            if task.get('qa_job'):
                return own_job(store,conn,task,task['qa_job'],worker_id)
            segments = store._segments(conn)
            if parallel(task) and (active_jobs(task) or cross_page(segments) or any(s.get('review_status')!='skipped' and not valid(s) for s in segments)):
                return {'status':'live_qa_required','next_action':'qa-next','instruction':'先完成逐段问答和跨段补查，再领取收尾工作。'}
            if parallel(task) and (task.get('capture_status') not in {'ended','stopped','failed'} or task.get('worker_status') not in {'done','stopped','failed'}):
                return {'status':'waiting_review','next_action':'review-next'}
            questions = interactions.summarize(segments)
            if not questions:return {'status':'no_questions','next_action':'status'}
            if parallel(task) and history_ready(task,segments):return {'status':'done','next_action':'qa-next --final'}
            source = {'questions':questions, 'segments':[segment_source(s) for s in segments
                if s.get('review_status') == 'done' and s.get('subtitles')]}
            job = {'id':uuid.uuid4().hex,'kind':'recheck','source':source,'source_hash':digest(source),'created_at':time.time()}
            task['qa_job'] = job;store._set_task(conn,task)
            return own_job(store,conn,task,job,worker_id)
    if not enabled(store.task()):return {'status':'legacy_inline','next_action':'review-next'}
    if parallel(store.task()) and not final:
        return claim_live_parallel(store,worker_id)
    if final:
        state = progress(store)
        if parallel(store.task()) and (state['cross_pending'] or state['pending']):
            return claim_live_parallel(store,worker_id)
        if state['pending'] or state['waiting_review']:
            return {'status':'live_qa_required', **prerequisite(store)}
        if parallel(store.task()) and (store.task().get('capture_status') not in {'ended','stopped','failed'} or store.task().get('worker_status') not in {'done','stopped','failed'}):
            return {'status':'waiting_review','next_action':'review-next'}
        if not history_ready(store.task(), store.segments()):
            return claim(store,recheck=True,worker_id=worker_id)
        if clarifications.pending_page(store.segments()):
            return claim(store,clarifications_only=True,worker_id=worker_id)
        if store.task().get('asr_provider') != 'ark':return {'status':'not_required','next_action':'recap-input --begin'}
        recap_asr.ensure(store, retry_failed=True)
        recap_asr.freeze_comments(store)
        store.update_task(recap_qa_check_version=2,recap_qa_scope_version=1)
    with store.connection(True) as conn:
        task = store._task(conn)
        check(store,worker_id,task=task)
        job = task.get('qa_job')
        if job:
            if job['kind'] in {'recheck','clarification'}:return own_job(store,conn,task,job,worker_id)
            if job['kind'] == 'final':current = recap_asr.source(task)
            else:
                segment = store._segment(conn,job['segment_id'])
                current = segment_source(segment) if segment.get('review_status') == 'done' else None
            if digest(current) == job['source_hash']:
                return own_job(store,conn,task,job,worker_id)
            task.pop('qa_job')
            store._set_task(conn,task)
        if final:
            if parallel(task) and active_jobs(task):return {'status':'live_qa_required','next_action':'qa-next'}
            source = recap_asr.source(task)
            if source is None:return {'status':'asr_unavailable','next_action':'qa-next --final','retryable':True}
            if final_ready(task,source):return {'status':'done','next_action':'recap-input --begin'}
            job = {'kind':'final', 'source':source, 'source_hash':digest(source)}
        else:
            segments = store._segments(conn)
            ready = [s for s in segments if s.get('review_status') != 'skipped' and not valid(s)]
            if not ready:return {'status':'caught_up','next_action':'review-next' if task.get('capture_status') not in {'stopped','ended','failed'} else 'status'}
            segment = min(ready,key=lambda s:(s['start_ms'],s['id']))
            if segment.get('review_status') != 'done':
                return {'status':'waiting_review','next_action':'status','instruction':'等待前段风险与商品结果，主流程继续审核；不要跳过前段提前关联后段问题。'}
            from runtime.live_room import context
            source = segment_source(segment)
            source['viewer_context'] = context(conn,store.session_id,segment) if task.get('live_room') else {}
            previous = interactions.context(segments,segment['start_ms'],lookahead=[source],pending_only=True)
            source['qa_context'] = previous
            source['qa_checklist'] = interactions.check_targets(previous,source,version=2)
            source['qa_focus'] = interactions.focus(previous,source,version=2)
            job = {'kind':'live','segment_id':segment['id'],'source':source,'source_hash':digest(segment_source(segment)),
                   'compact_history':True}
        job.update(id=uuid.uuid4().hex, created_at=time.time())
        task['qa_job'] = job
        store._set_task(conn,task)
        return own_job(store,conn,task,job,worker_id)


def submit(store, payload, *, worker_id=None):
    from runtime.live_room import ANSWER_MATCHING_ENABLED
    if not ANSWER_MATCHING_ENABLED:
        task = store.task()
        from runtime.live_room import extracts_comments
        if extracts_comments(task) and worker_id:
            from runtime import qa_pipeline
            if not isinstance(payload,dict) or payload.get('task_id') != store.task_id:raise ValueError('task binding mismatch')
            return qa_pipeline.submit(store,payload,worker_id)
        jobs = [task.get('qa_job') or {}] + task.get('qa_clarification_receipts', [])
        if not isinstance(payload, dict) or not any(j.get('kind') == 'clarification' and j.get('id', j.get('job_id')) == payload.get('job_id') for j in jobs):
            return {'status':'disabled','message':'问答匹配已下线；评论在复盘中总结。'}
    from runtime.qa_worker import check, parallel
    check(store,worker_id)
    if not isinstance(payload,dict) or payload.get('task_id') != store.task_id:raise ValueError('QA task binding mismatch')
    from runtime import qa_pipeline
    task=store.task()
    if qa_pipeline.enabled(task) and not ((task.get('qa_job') or {}).get('id')==payload.get('job_id') or any(r.get('job_id')==payload.get('job_id') for r in task.get('qa_clarification_receipts',[]))):
        return qa_pipeline.submit(store,payload,worker_id)
    result_hash = digest(payload)
    with store.connection(True) as conn:
        task = store._task(conn)
        check(store,worker_id,task=task)
        saved = [task.get('qa_final') or {}] + task.get('qa_recheck_receipts', []) + task.get('qa_clarification_receipts',[]) + [s.get('qa_receipt') or {} for s in store._segments(conn)]
        receipt = next((r for r in saved if r.get('job_id') == payload.get('job_id')),None)
        if receipt:
            if receipt['result_hash'] != result_hash:raise ValueError('QA conflicting replay')
            return {'status':'saved','duplicate':True,'next_action':('qa-next --final' if enabled(task) else 'qa-next --clarifications') if receipt.get('kind')=='clarification' else 'qa-next'}
        job = task.get('qa_job')
        if not job or job['id'] != payload.get('job_id'):
            job=next((item for item in active_jobs(task) if item['id'] == payload.get('job_id')),None)
        if not job or ((parallel(task) or job.get('assigned_worker_id')) and job.get('assigned_worker_id') != worker_id):raise ValueError('stale or missing QA job; claim it with the registered worker first')
        if job.get('attempts',0) >= MAX_FAILED_ATTEMPTS:return repair_response(store,job,worker_id=worker_id)
        if job['kind'] in {'recheck','clarification'}:
            if job.get('last_failed_hash') == result_hash:return repair_response(store,job,duplicate=True,worker_id=worker_id)
            try:
                return (submit_clarifications if job['kind']=='clarification' else submit_recheck)(store,conn,task,job,payload,result_hash)
            except (ValueError,TypeError,KeyError) as error:
                return record_failure(store,conn,task,job,result_hash,error.errors if isinstance(error,ValidationErrors) else [error],worker_id=worker_id)
        if not enabled(task):raise ValueError('independent QA not enabled')
        current = recap_asr.source(task) if job['kind'] == 'final' else segment_source(store._segment(conn,job['segment_id']))
        if digest(current) != job['source_hash'] or (job['kind'] == 'live' and store._segment(conn,job['segment_id']).get('review_status') != 'done'):
            remove_job(task,job);store._set_task(conn,task)
            return {'status':'stale','next_action':'qa-next','retryable':True}
        if job.get('last_failed_hash') == result_hash:return repair_response(store,job,duplicate=True,worker_id=worker_id)
        allowed = {'task_id','job_id'} | ({'interaction_review'} if job['kind']=='final' else {'qa_observations','qa_checks'})
        errors=[]
        try:
            if set(payload) != allowed:
                error=ValueError('invalid QA submission fields');error.field='submission';errors.append(error)
            if job['kind'] == 'final':
                result = recap_asr.validate(payload.get('interaction_review'),job['source'],errors=errors)
            else:
                source=job['source'];previous=source['qa_context']
                observations=interactions.normalize(payload.get('qa_observations'),source,[],previous,source['sales_observation'],errors=errors)
                checks=interactions.check_coverage(payload.get('qa_checks'),observations,previous,source,version=2,required_previous=previous,errors=errors)
                result={'qa_observations':observations,'qa_checks':checks}
        except (ValueError, TypeError, KeyError) as error:
            errors.append(error)
        if errors:return record_failure(store,conn,task,job,result_hash,errors,worker_id=worker_id)
        receipt={'job_id':job['id'],'result_hash':result_hash,'source_hash':job['source_hash'],'completed_at':time.time(),'attempts':job.get('attempts',0)+1,
                 **({'last_error':job['last_error'],'last_errors':job.get('last_errors',[job['last_error']])} if job.get('last_error') else {})}
        if job['kind']=='final':task['qa_final']={**receipt,'rows':result}
        else:
            segment=store._segment(conn,job['segment_id'])
            receipt['pending_predecessors']=job.get('pending_predecessors',[])
            segment.pop('qa_cross_checked',None)
            diagnostic=interactions.review_diagnostic(previous,source,observations,checks,source['qa_focus'],version=2)
            segment.update(qa_review_result=result,qa_review_status='done',qa_source_hash=job['source_hash'],qa_receipt=receipt,
                           qa_review_context=source,qa_review_diagnostic=diagnostic)
            # QA may finish after media/risk freeze; it never changes media or risk state.
            store._write_segment(conn,segment['id'],segment)
        from runtime.store import now_iso
        conn.execute('INSERT INTO operation_logs(created_at,kind,message,segment_id) VALUES(?,?,?,?)',
            (now_iso(),'qa_review',json.dumps({'job_id':job['id'],'execution':'independent','phase':job['kind'],
                'checked_count':len(result) if job['kind']=='final' else len(checks),'attempts':receipt['attempts']}),job.get('segment_id')))
        remove_job(task,job)
        task.pop('recap_viewer_context',None)
        store._set_task(conn,task)
        return {'status':'saved','job_id':job['id'],'next_action':'recap-input --begin' if job['kind']=='final' else 'qa-next'}


def submit_clarifications(store, conn, task, job, payload, result_hash):
    current={s['id']:s for s in store._segments(conn)}
    known={q['id']:q for q in clarifications.summarize(list(current.values()))}
    frozen={s['id']:s for s in job['source']['segments']}
    stale=any(q['id'] not in known or clarifications.issue_key(known[q['id']])!=clarifications.issue_key(q) for q in job['source']['items'])
    for sid, source in frozen.items():
        actual=current.get(sid,{})
        subtitles={u['id']:u for u in actual.get('subtitles',[])}
        stale=stale or any(subtitles.get(u['id'])!=u for u in source['subtitles']) or any(actual.get(k)!=source[k] for k in ('start_ms','end_ms'))
    if stale:
        task.pop('qa_job');store._set_task(conn,task)
        return {'status':'stale','next_action':'qa-next --clarifications','retryable':True}
    if set(payload)!={'task_id','job_id','segments'} or not isinstance(payload['segments'],list):
        raise ValueError('invalid clarification recheck fields')
    ids=[row.get('segment_id') for row in payload['segments'] if isinstance(row,dict)]
    if len(ids)!=len(payload['segments']) or any(type(sid) is not int for sid in ids) or len(set(ids))!=len(ids) or set(ids)!=set(frozen):
        raise ValueError('clarification recheck requires every frozen segment exactly once')
    errors, normalized=[], []
    for index,row in enumerate(payload['segments']):
        try:
            if set(row)!={'segment_id','clarification_observations','clarification_checks'}:
                raise ValueError('clarification observations and checks are required')
            source=frozen[row['segment_id']]
            if not isinstance(row['clarification_observations'],list) or any(not isinstance(o,dict) or 'clarification_id' not in o for o in row['clarification_observations']):
                raise ValueError('final clarification recheck only updates existing issues')
            required=[q for q in job['source']['items'] if q['id'] in source['clarification_checklist']]
            observations=clarifications.normalize(row['clarification_observations'],source,required)
            checks=clarifications.check_coverage(row['clarification_checks'],observations,required,source)
            normalized.append((row['segment_id'],observations,checks))
        except (ValueError,TypeError,KeyError) as error:
            error.field=f'segments[{index}].'+getattr(error,'field','clarification_checks');errors.append(error)
    if errors:raise ValidationErrors(errors)
    for sid, observations, checks in normalized:
        segment=current[sid]
        for key,values in (('clarification_supplements',observations),('clarification_rechecks',checks)):
            saved=segment.setdefault(key,[])
            saved.extend(value for value in values if value not in saved)
        store._write_segment(conn,sid,segment)
    receipt={'kind':'clarification','job_id':job['id'],'result_hash':result_hash,'source_hash':job['source_hash'],'completed_at':time.time(),
             'attempts':job.get('attempts',0)+1,'source':job['source'],'submitted':copy.deepcopy(payload)}
    task.setdefault('qa_clarification_receipts',[]).append(receipt)
    task.pop('qa_job');store._set_task(conn,task)
    from runtime.store import now_iso
    conn.execute('INSERT INTO operation_logs(created_at,kind,message,segment_id) VALUES(?,?,?,?)',
        (now_iso(),'qa_review',json.dumps({'job_id':job['id'],'execution':'independent','phase':'clarification',
         'checked_count':sum(len(checks) for _,_,checks in normalized),'attempts':receipt['attempts']}),None))
    return {'status':'saved','job_id':job['id'],'next_action':'qa-next --final' if enabled(task) else 'qa-next --clarifications'}


def submit_recheck(store, conn, task, job, payload, result_hash):
    """Append answers atomically; frozen quotes and risk decisions remain unchanged."""
    if set(payload) != {'task_id','job_id','segments','checked_question_ids'}:
        raise ValueError('invalid QA recheck fields')
    previous = job['source']['questions']
    ids = [q['id'] for q in previous]
    errors=[]
    checked = payload['checked_question_ids']
    if not isinstance(checked,list) or any(not isinstance(i,str) for i in checked) or len(checked)!=len(set(checked)) or set(checked)!=set(ids):
        error=ValueError('recheck requires every frozen question to be reviewed');error.field='checked_question_ids';errors.append(error)
    current = {s['id']:s for s in store._segments(conn)}
    frozen = {s['id']:s for s in job['source']['segments']}
    for sid, source in frozen.items():
        if sid not in current or digest(segment_source(current[sid])) != digest(source):
            remove_job(task,job);store._set_task(conn,task)
            return {'status':'stale','next_action':'qa-next --recheck','retryable':True}
    current_questions = {q['id']:q for q in interactions.summarize(list(current.values()))}
    for q in previous:
        actual = current_questions.get(q['id'])
        if not actual or any(actual.get(k)!=q.get(k) for k in ('question','evidence_ids','start_ms','product','offer','question_detail')):
            remove_job(task,job);store._set_task(conn,task)
            return {'status':'stale','next_action':'qa-next','retryable':True}
    rows = payload['segments']
    if not isinstance(rows,list):raise ValueError('recheck segments must be a list')
    normalized=[]
    for row_index,row in enumerate(rows):
        try:
            if not isinstance(row,dict) or set(row)!={'segment_id','qa_observations'} or type(row['segment_id']) is not int or row['segment_id'] not in frozen:
                raise ValueError('invalid recheck segment')
            observations=row['qa_observations']
            if not isinstance(observations,list) or any(not isinstance(q,dict) or not q.get('reply_to') for q in observations):
                raise ValueError('recheck only appends answers to existing questions')
            source=frozen[row['segment_id']]
            row_errors=[]
            result=interactions.normalize(observations,source,[],previous,source.get('sales_observation'),errors=row_errors)
            for error in row_errors:
                error.field=f'segments[{row_index}].'+getattr(error,'field','qa_observations');errors.append(error)
            normalized.extend((row['segment_id'],q) for q in result)
        except (ValueError,TypeError,KeyError) as error:
            error.field=f'segments[{row_index}]';errors.append(error)
    if errors:raise ValidationErrors(errors)
    added=0
    for sid, question in normalized:
        segment=current[sid]
        supplements=segment.setdefault('qa_answer_supplements',[])
        target=current_questions[question['id']]
        for answer in question['answers']:
            if any(a['segment_id']==sid and a['evidence_ids']==answer['evidence_ids'] for a in target['answers']):continue
            supplements.append({'job_id':job['id'],'source_hash':digest(frozen[sid]),
                                'question':{**question,'answers':[answer]}})
            target['answers'].append(answer);added+=1
    for sid in {sid for sid,_ in normalized}:store._write_segment(conn,sid,current[sid])
    receipt={'job_id':job['id'],'result_hash':result_hash,'source_hash':job['source_hash'],
             'completed_at':time.time(),'checked_count':len(checked),'added_answers':added}
    if 'cross_segment_id' in job:
        segment=current[job['cross_segment_id']]
        segment.setdefault('qa_cross_checked',{}).update(job['cross_signatures'])
        store._write_segment(conn,segment['id'],segment)
        receipt['cross_segment_id']=segment['id']
    else:receipt['history_hash']=history_hash(list(current.values()))
    task.setdefault('qa_recheck_receipts',[]).append(receipt)
    remove_job(task,job);task.pop('recap_viewer_context',None)
    if task.get('recap'):
        from runtime.live_room import recap_context
        from runtime.recap import evidence_input
        segments = list(current.values())
        viewer = recap_context(store,conn,task,segments,evidence_input(task,segments))
        if viewer is not None:task['recap_viewer_context'] = viewer
    store._set_task(conn,task)
    from runtime.store import now_iso
    conn.execute('INSERT INTO operation_logs(created_at,kind,message,segment_id) VALUES(?,?,?,?)',
        (now_iso(),'qa_review',json.dumps({'job_id':job['id'],'execution':'independent','phase':'recheck',
         'checked_count':len(checked),'added_answers':added}),None))
    return {'status':'saved','job_id':job['id'],'checked_count':len(checked),'added_answers':added,
            'next_action':'qa-next' if 'cross_segment_id' in job else 'qa-next --final' if enabled(task) else 'status'}
