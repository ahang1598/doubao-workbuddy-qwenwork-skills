"""Offline segment-ASR snapshots and recalibration for historical ARK tasks."""
import copy
import json
import time


SEGMENT_SOURCE = 'segment_concat_v1'


def _segment_evidence(segments):
    evidence = []
    for segment in sorted(segments, key=lambda item:(item['start_ms'], item['id'])):
        for subtitle in segment.get('subtitles', []):
            if not isinstance(subtitle, dict) or not isinstance(subtitle.get('id'), str) or not isinstance(subtitle.get('text'), str):
                continue
            start, end = subtitle.get('start_ms'), subtitle.get('end_ms')
            if not isinstance(start, int) or not isinstance(end, int):
                continue
            start, end = max(segment['start_ms'], start), min(segment['end_ms'], end)
            if end > start and subtitle['text'].strip():
                evidence.append({'id':subtitle['id'], 'kind':'speech', 'text':subtitle['text'],
                                 'start_ms':start, 'end_ms':end, 'segment_id':segment['id']})
    return sorted(evidence, key=lambda item:(item['start_ms'], item['end_ms'], item['id']))


def ensure(store, *, retry_failed=False):
    task = store.task()
    if task.get('asr_provider') != 'ark':return
    if task.get('capture_status') not in {'ended','stopped','failed'} or task.get('worker_status') not in {'done','stopped','failed'}:
        raise ValueError('分段 ASR 需等待录制和媒体处理结束')
    from runtime.platform_support import file_lock
    with file_lock(store.root/'.recap-asr.lock', timeout=1):
        job = store.task().get('recap_asr')
        if job and job.get('asr_status') == 'success' and job.get('source') == SEGMENT_SOURCE:return
        evidence = _segment_evidence(store.segments())
        store.update_task(recap_asr={'id':'recap-segments','source':SEGMENT_SOURCE,
                                     'asr_status':'success','evidence':evidence,
                                     'created_at':time.time()})


def source(task):
    job = task.get('recap_asr') or {}
    if job.get('asr_status') != 'success':return None
    if job.get('source') == SEGMENT_SOURCE:
        evidence = copy.deepcopy(job.get('evidence', []))
        if not isinstance(evidence, list):return None
        data = {'status':'success', 'evidence':evidence,
                'comments':copy.deepcopy(task.get('recap_comments', [])),
                'instruction':'逐条检查所有 comments，不沿用旧问答状态。提问须核对按时间拼接的分段 ASR 证据及主播/助播评论回答。'
                              '分段 ASR 仅覆盖已成功识别的片段；未识别回答不代表主播没有回答。公共问题不要求点名，核对商品、链接、时间和否定词；不要把不同商品的回答拼接。'
                              '只提供证据引用，程序提取原文；无法确认完整回答则 answer_complete=false。旧 viewer_context 的问答和统计仅供对照，互动结论以本次校准为准。'}
        return _with_scope(task, data)

    return None


def _with_scope(task, data):
    if task.get('recap_product_context'):
        data['product_context'] = copy.deepcopy(task['recap_product_context'])
    if task.get('recap_qa_scope_version',0) >= 1:
        data['instruction'] += ('每个问题填写 question_product、question_offer、question_detail（商品或条件不明留空）；明确提及其他商品时单独归属，结合 product_context 核对切换时点。'
                            '商品名和具体疑问复用已确认的规范名称；不能把正在介绍的商品套到所有评论。链接回答不能解答尺码、弹性、颜色或库存问题；派克羽绒服的尺码不能回答早先毛衣，当前品牌不能回答骆驼返场。')
    if task.get('recap_qa_check_version',1) >= 2:
        from runtime.interactions import answer_candidates, question_like
        for comment in data['comments']:
            comment['answer_candidates'] = answer_candidates({'question':comment['text'],'start_ms':comment['start_ms']},
                {'subtitles':data['evidence']}) if question_like(comment['text']) else []
        for comment in data['comments']:
            for candidate in comment['answer_candidates']:
                candidate['evidence'] = [{'id':e['id']} for e in candidate['evidence']]
        data['instruction'] += ('answer_candidates 仅提供ID，原文从 evidence 按ID读取。有 answer_candidates 却不关联回答时，附 checked_evidence_ids 列出全部候选ID，并逐题说明商品或条件不匹配原因。'
                                '相同商品、规格及条件的相似问题用 similar_to 引用先前评论ID归组；保留每条提问及独立回答状态，不能仅按含糖/加糖等相关词合并。')
    return data


def freeze_comments(store):
    from runtime.live_room import exists
    with store.connection() as conn:
        comments = [json.loads(r[0]) for r in conn.execute(
            "SELECT data FROM live_room_events WHERE session_id=? AND kind='comment' ORDER BY time_ms,id",
            (store.session_id,))] if exists(conn) else []
    from runtime.interactions import summarize
    by_id = {c['id']:c for c in comments}
    for question in summarize(store.segments()):
        metadata = {k:question[k] for k in ('question_scope','question_category','topic','topic_key',
                    'group_id','group_question','product','offer','question_detail') if k in question}
        if question.get('source') == 'viewer_comment':
            for ref in question.get('evidence_ids', []):
                if ref in by_id:by_id[ref]['question_metadata'] = metadata
        else:
            comments.append({'id':'question:'+question['id'], 'text':question['question'],
                'start_ms':question['start_ms'], 'end_ms':question['end_ms'], 'source':'host_question'})
    store.update_task(recap_comments=comments,recap_product_context=[
        {'start_ms':s['start_ms'],'end_ms':s['end_ms'],'product':s['review_result']['sales_observation']['product'],
         'offer':s['review_result']['sales_observation'].get('offer','')} for s in store.segments()
        if s.get('review_status')=='done' and (s.get('review_result') or {}).get('sales_observation',{}).get('product')])


def question_metadata(comment, row):
    return {**comment.get('question_metadata',{}),
            **{target:row[field].strip() for field,target in (('question_product','product'),('question_offer','offer'),('question_detail','question_detail')) if field in row}}


def validate(rows, data, *, errors=None):
    if not isinstance(rows,list):
        error=ValueError('interaction_review required');error.field='interaction_review'
        if errors is None:raise error
        errors.append(error);return []
    comments = {c['id']:c for c in data['comments']}
    speech = {e['id']:e for e in data['evidence']}
    supplied=[r.get('comment_id') for r in rows if isinstance(r,dict) and isinstance(r.get('comment_id'),str)]
    if len(rows)!=len(comments) or len(supplied)!=len(set(supplied)) or set(supplied)!=set(comments):
        error=ValueError('interaction_review must cover every comment exactly once');error.field='interaction_review'
        error.missing_qa_ids=sorted(set(comments)-set(supplied))
        if errors is None:raise error
        errors.append(error)
    result = []
    for row_index,row in enumerate(rows):
        try:
            if not isinstance(row, dict) or (set(row)-{'comment_id','is_question','reason','answer_evidence_ids','answer_complete','checked_evidence_ids','similar_to','question_product','question_offer','question_detail'} or not {'comment_id','is_question','reason','answer_evidence_ids','answer_complete'} <= set(row)):
                raise ValueError('invalid interaction_review fields')
            if type(row['is_question']) is not bool or type(row['answer_complete']) is not bool:
                raise ValueError('invalid interaction_review status')
            if not isinstance(row['reason'], str) or not row['reason'].strip() or len(row['reason']) > 1000:
                raise ValueError('interaction_review reason required')
            for field in ('question_product','question_offer','question_detail'):
                if field in row and (not isinstance(row[field],str) or len(row[field])>240):
                    raise ValueError('invalid interaction question scope')
            ids = row['answer_evidence_ids']
            if not isinstance(ids, list) or any(not isinstance(i,str) for i in ids) or len(set(ids)) != len(ids):
                raise ValueError('invalid interaction answer evidence')
            if (not row['is_question'] and ids) or (row['answer_complete'] and (not row['is_question'] or not ids)):
                raise ValueError('answer status contradicts evidence')
            question = comments[row['comment_id']]
            if not ids and question.get('answer_candidates'):
                from runtime.interactions import generic_unanswered
                expected = {e['id'] for candidate in question['answer_candidates'] for e in candidate['evidence']}
                checked = row.get('checked_evidence_ids',[])
                if (generic_unanswered(row['reason']) or not isinstance(checked,list) or any(not isinstance(i,str) for i in checked)
                        or set(checked)!=expected or len(checked)!=len(expected)):
                    raise ValueError('interaction answer candidates require individual evidence check: '+row['comment_id'])
            for ref in ids:
                evidence = speech.get(ref) or comments.get(ref)
                if not evidence or evidence.get('end_ms',evidence['start_ms']) < question['start_ms']:
                    raise ValueError('answer evidence missing or before question')
                if ref in comments and (comments[ref].get('author_role') not in {'host','room_admin'} or comments[ref].get('source') == 'host_question'):
                    raise ValueError('viewer comment cannot prove host answer')
            if 'similar_to' in row:
                target = next((r for r in result if r['comment_id']==row['similar_to']), None)
                if not row['is_question'] or not target or not target['is_question']:
                    raise ValueError('interaction similar_to requires preceding question')
                left=question_metadata(question,row);right=question_metadata(comments[target['comment_id']],target)
                if left.get('question_scope')=='personalized' or right.get('question_scope')=='personalized' or any(left.get(k) and right.get(k) and left[k]!=right[k] for k in ('product','offer','question_detail')):
                    raise ValueError('interaction similar_to crosses question scope')
            result.append(copy.deepcopy(row))
        except (ValueError,TypeError,KeyError) as error:
            if errors is None:raise
            error.field=f'interaction_review[{row_index}]'
            errors.append(error)
    return result


def viewer_context(context, rows, data, segments=()):
    from runtime.interactions import question_status, questioner_counts, interaction_optimization, _question_metadata
    output = copy.deepcopy(context or {})
    comments = {c['id']:c for c in data['comments']}
    evidence = {e['id']:e for e in data['evidence']}
    from runtime import interactions, qa_workflow
    # Explicit historical rechecks remain authoritative supplements after final calibration.
    current = {ref:q for q in interactions.summarize(segments) for ref in q.get('evidence_ids',[])}
    supplements = {}
    for segment in segments:
        for entry in segment.get('qa_answer_supplements',[]):
            if entry.get('source_hash') != qa_workflow.digest(qa_workflow.segment_source(segment)):continue
            checked = entry['question']
            for ref in checked.get('evidence_ids',[]):
                actual = current.get(ref)
                if actual and all(actual.get(k)==checked.get(k) for k in ('question','product','offer','question_detail')):
                    supplements.setdefault(ref,[]).extend(copy.deepcopy(checked['answers']))
    questions = []
    for row in rows:
        if not row['is_question']:continue
        c = comments[row['comment_id']]
        answers = []
        for ref in row['answer_evidence_ids']:
            e = evidence.get(ref) or comments[ref]
            answers.append({'segment_id':next((s['id'] for s in segments if s['start_ms'] <= e['start_ms'] < s['end_ms']), None), 'text':e['text'], 'start_ms':e['start_ms'], 'end_ms':e.get('end_ms',e['start_ms']),
                'evidence_ids':[ref], 'answer_complete':row['answer_complete'],
                'source':'room_comment' if ref in comments else 'speech',
                **{k:e[k] for k in ('author_nickname','author_role') if k in e}})
        q = {**{k:c[k] for k in ('author_id','author_nickname','author_role') if k in c},
             'id':c['id'], 'question':c['text'], 'source':'host_question' if c.get('source') == 'host_question' else 'viewer_comment',
             'start_ms':c['start_ms'], 'end_ms':c.get('end_ms',c['start_ms']),
             'evidence_ids':[c['id']], 'answers':answers, 'answers_omitted':0,
             **question_metadata(c,row),
             **_question_metadata(question_metadata(c,row), c['text'])}
        if c['id'] in current:
            explicit = {'product':'question_product','offer':'question_offer','question_detail':'question_detail'}
            q.update({k:current[c['id']][k] for k in explicit if k in current[c['id']] and explicit[k] not in row})
        if row.get('similar_to'):
            target = next(q for q in questions if q['id']==row['similar_to'])
            compatible = not any(q.get(k) and target.get(k) and q[k] != target[k] for k in ('product','offer','question_detail'))
            if compatible:q.update(group_id=target.get('group_id',target['id']),group_question=target.get('group_question',target['question']))
            for key in ('topic','topic_key','question_category'):
                if compatible and key in target:q[key]=target[key]
        if c['id'] in supplements and all(q.get(k)==current[c['id']].get(k) for k in ('product','offer','question_detail')):
            q['answers'].extend(supplements[c['id']])
        for answer in q['answers']:
            answer.update(product=q.get('product',''), offer=q.get('offer',''))
        q['status'] = question_status(q)
        questions.append(q)
    from runtime.interactions import project_topics
    project_topics(questions)
    questions.sort(key=lambda q:(q['start_ms'],q['id']))
    output.update(qa=questions, qa_total=len(questions), omitted_qa_count=0,
        qa_summary={'total':len(questions), **{s:sum(question_status(q)==s for q in questions)
                   for s in ('answered','reply_detected','pending')}, **questioner_counts(questions)},
        interaction_optimization=interaction_optimization(questions),
        calibration={'status':'completed','comment_count':len(rows),'asr':'segment_concat'},
        scope='评论问题已逐条依据全场分段 ASR 和主播/助播评论校准；已提取的语音问题一并重新核对。未识别回答不代表未回答；人数变化不作话术归因，不推断成交效果。')
    from runtime.customer_service import build as service_reference
    output['customer_service'] = service_reference(segments, questions, output.get('live_room', {}))
    return output
