"""Versioned full-audio live policy. Never applied to videos or legacy sessions."""
import time
POLICY = 'lite_live_full_asr_v1'
INTERVAL_MS = 120000

def enabled(task):
    return task.get('kind','live') == 'live' and task.get('inspection_policy') in {POLICY, 'lite_live_realtime_v1', 'lite_live_realtime_v2'}

def speech_only_scope(task):
    return (enabled(task) and task.get('review_protocol') == 'lite_review_v2'
            and task.get('review_scope_version') == 1 and task.get('image_inspection') is False)

def speech_can_clear(task, segment):
    if task.get('inspection_policy')=='lite_live_realtime_v2':
        return segment['asr_status'] in {'success','no_audio'}
    return (segment['asr_status'] in {'success', 'no_audio'} or
            (speech_only_scope(task) and any(str(u.get('text', '')).strip() for u in segment.get('subtitles', []))))

def requires_frames(snapshot):
    needed=False
    for rule in snapshot['rules']:
        modalities=rule.get('modalities')
        if not isinstance(modalities,list) or not modalities or any(m not in {'speech','image'} for m in modalities):
            raise ValueError('rule requires valid modalities')
        if rule.get('enabled',True) and 'image' in modalities:needed=True
    return needed

def sample_times(task,start,end):
    if not requires_frames(task['rules_snapshot']) or speech_only_scope(task):return []
    origin=task.get('frame_sampling_origin_ms',0)
    first=origin+max(0,(start-origin+INTERVAL_MS-1)//INTERVAL_MS)*INTERVAL_MS
    return list(range(first,end,INTERVAL_MS))

def initialize_segment(task,data):
    data['full_live']=True
    required=requires_frames(task['rules_snapshot'])
    times=sample_times(task,data['start_ms'],data['end_ms'])
    data.update(frame_sample_times_ms=times,frame_expected_count=len(times),
                frame_status='pending' if times else 'not_scheduled' if required else 'not_required')
    if data['asr_status'] in {'success','no_audio','failed','timed_out','submission_unknown'}:
        data['asr_ready_at']=time.time()

def ready(task,segment):
    from runtime.store import ASR_DONE, FRAME_DONE
    return segment['asr_status'] in ASR_DONE and (enabled(task) or segment['frame_status'] in FRAME_DONE)

def advance(store,conn,task,now):
    # Full audio keeps all collected evidence until reviewed or explicitly cancelled.
    from runtime.finishing import advance_live
    return advance_live(store, conn, task, now)

def progress(task,segments):
    ready_rows=[s for s in segments if s['review_status']=='pending' and ready(task,s)]
    oldest=max([max(0,time.time()-s.get('asr_ready_at',time.time())) for s in ready_rows]+[0])
    required=requires_frames(task['rules_snapshot']) and not speech_only_scope(task)
    unavailable=any(s['frame_status'] in {'failed','unavailable'} for s in segments)
    from runtime.review_contract import enabled as protocol_v2
    from runtime.review_metrics import metrics
    return {**(metrics(task,segments,task.get('_review_batches',[])) if protocol_v2(task) else {}),'policy':task.get('inspection_policy', POLICY),'ready_segments':len(ready_rows),'oldest_wait_seconds':round(oldest,1),
            'recovering_speech_segments':sum(s['asr_status'] in {'pending','running','fallback_pending'} for s in segments),
            'mode':task.get('review_dispatch',{}).get('mode','serial'),
            'frame_required':required,'frame_interval_seconds':120 if required else None,
            'frame_message':'画面检测已关闭，仅判定字幕' if speech_only_scope(task) else '本任务无需画面检测' if not required else '画面暂不可用，语音检测继续' if unavailable else '每两分钟采样一次',
            'planned_frames':sum(len(s.get('frame_sample_times_ms',[])) for s in segments),
            'available_frames':sum(len(s.get('frames',[])) for s in segments)}
