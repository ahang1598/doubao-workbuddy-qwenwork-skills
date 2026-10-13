"""Bounded, durable recovery of speech gaps without erasing valid transcripts."""
import time
from runtime.local_asr import LocalASR, ASRError, MediaCancellation, normalize_subtitles

def clipped_gaps(gaps,segment,relative=False):
    offset=segment['start_ms'] if relative else 0
    spans=[]
    for gap in gaps:
        a=max(segment['start_ms'],round(gap['start_ms']+offset))
        b=min(segment['end_ms'],round(gap['end_ms']+offset))
        if b>a:spans.append((a,b))
    merged=[]
    for a,b in sorted(spans):
        if merged and a<=merged[-1][1]:merged[-1][1]=max(b,merged[-1][1])
        else:merged.append([a,b])
    return [{'start_ms':a,'end_ms':b} for a,b in merged]

def merge(existing,incoming,gaps,segment):
    # Recovery contributes only to still-missing intervals, never replaces good text.
    result=list(existing);remaining=list(gaps)
    for subtitle in incoming:
        for gap in gaps:
            a=max(subtitle['start_ms'],gap['start_ms']);b=min(subtitle['end_ms'],gap['end_ms'])
            if b<=a:continue
            result.append({**subtitle,'id':f"asr-{segment['id']}-recovered-{subtitle['start_ms']}-{subtitle['end_ms']}"})
            next_gaps=[]
            for g in remaining:
                if b<=g['start_ms'] or a>=g['end_ms']:next_gaps.append(g);continue
                if g['start_ms']<a:next_gaps.append({'start_ms':g['start_ms'],'end_ms':a})
                if b<g['end_ms']:next_gaps.append({'start_ms':b,'end_ms':g['end_ms']})
            remaining=next_gaps
    unique={(s['start_ms'],s['end_ms'],s['text']):s for s in result}
    return sorted(unique.values(),key=lambda s:(s['start_ms'],s['end_ms'])),remaining

class RecoveryStore:
    def __init__(self,store,segment):self.store,self.segment=store,segment
    def __getattr__(self,name):return getattr(self.store,name)
    def update_segment(self,sid,**fields):
        previous=self.segment
        if 'subtitles' in fields:
            if previous.get('speech_gaps'):
                fields['subtitles'],fields['speech_gaps']=merge(previous.get('subtitles',[]),fields['subtitles'],previous['speech_gaps'],previous)
            elif not fields['subtitles'] and previous.get('subtitles'):
                fields['subtitles']=previous['subtitles']
        if fields.get('asr_status')=='success' and fields.get('speech_gaps'):
            fields.update(asr_status='failed',asr_diagnostic={'category':'ASR_EMPTY_SPEECH'})
        return self.store.update_segment(sid,**fields)

def process(processor,store,segment,cancel=None):
    cancel=MediaCancellation(store,cancel);sid=segment['id']
    def current():return next(s for s in store.segments() if s['id']==sid)
    if segment.get('asr_final') or segment['asr_status'] in {'success','no_audio'}:return
    # A persisted remote ID is authoritative: resume its query, never probe/re-upload.
    if store.task().get('asr_policy')=='local_first' and (segment.get('asr_task_id') or (segment.get('asr_backend')=='mediakit' and not segment.get('full_asr_local_attempts'))):
        from runtime import mediakit
        if segment['asr_status'] in {'pending','running','submitted','timed_out'}:
            store.update_segment(sid,full_asr_cloud_started=True)
            mediakit.process_asr(RecoveryStore(store,segment),segment,cancel=cancel)
            segment=current()
            if segment['asr_status'] in {'pending','running','submitted','success','timed_out'}:return
        if segment['asr_status']=='submission_unknown':return
    # Counts are written before invoking any backend; interrupted work consumes an attempt.
    while segment.get('full_asr_local_attempts',0)<2 and not cancel.is_set():
        attempt=segment.get('full_asr_local_attempts',0)+1
        if not store.update_segment(sid,asr_status='running',full_asr_local_attempts=attempt):return
        try:
            if store.task().get('inspection_policy')=='lite_live_realtime_v2':
                with processor.local_session(store,cancel) as local:
                    if cancel.is_set():return
                    try:
                        raw=local.bridge.request('transcribe',audio_path=str(store.local_path(segment['audio_file'])),
                            timeout=(segment['end_ms']-segment['start_ms'])/1000+90,cancel=cancel)
                    except (ASRError,OSError):
                        local.close()
                        raise
            else:
                with processor.local_lock:
                    if cancel.is_set():return
                    if processor.local.bridge is None:
                        processor.local.bridge=LocalASR(store);processor.local.bridge.initialize(cancel)
                    raw=processor.local.bridge.request('transcribe',audio_path=str(store.local_path(segment['audio_file'])),
                        timeout=(segment['end_ms']-segment['start_ms'])/1000+90,cancel=cancel)
            incoming=normalize_subtitles(raw,segment)
            gaps=clipped_gaps(raw.get('speech_gaps',[]),segment,relative=True)
            if segment.get('speech_gaps'):
                subtitles,gaps=merge(segment.get('subtitles',[]),incoming,segment['speech_gaps'],segment)
            else:subtitles=incoming
            fields={'subtitles':subtitles,'speech_gaps':gaps,'asr_status':'fallback_pending' if gaps else 'success',
                'asr_diagnostic':{'category':'ASR_EMPTY_SPEECH'} if gaps else None,
                'asr_metrics':{k:raw.get(k) for k in ('duration_ms','processing_ms','dropped_audio_ms')}}
            store.update_segment(sid,**fields)
            if not gaps:return
        except (ASRError,OSError,RuntimeError,ValueError,TypeError) as error:
            code=getattr(error,'code','ASR_LOCAL_FAILED')
            if code=='ASR_CANCELLED' or cancel.is_set():return
            if store.task().get('inspection_policy')!='lite_live_realtime_v2':processor.local.close()
            fields={'asr_status':'fallback_pending','asr_diagnostic':{'category':code},'local_failure':segment.get('local_failure') or code}
            if code=='ASR_EMPTY_SPEECH' and not segment.get('speech_gaps'):
                fields['speech_gaps']=[{'start_ms':segment['start_ms'],'end_ms':segment['end_ms']}]
            store.update_segment(sid,**fields)
        segment=current()
    if cancel.is_set():return
    from runtime.asr_router import cloud_available
    from runtime import mediakit
    task=store.task();segment=current()
    if task.get('asr_policy')=='local_first' and not (segment.get('full_asr_cloud_started') and segment['asr_status'] in {'failed','timed_out','submission_unknown','fallback_pending'}):
        capability=task.get('full_asr_cloud_available')
        if capability is None:
            capability=cloud_available(store)['ready'];store.update_task(full_asr_cloud_available=capability)
        if capability:
            if not segment.get('full_asr_cloud_started'):
                if not store.update_segment(sid,full_asr_cloud_started=True,asr_backend='mediakit',asr_status='pending'):return
                segment=current()
            # Existing remote ID is queried. Unknown submissions are never replayed.
            if segment['asr_status'] not in {'failed','timed_out','submission_unknown','fallback_pending'}:
                mediakit.process_asr(RecoveryStore(store,segment),segment,cancel=cancel)
                segment=current()
                if segment['asr_status'] in {'pending','running','submitted'}:return
                if segment['asr_status']=='success':return
    if segment['asr_status'] in {'submission_unknown','timed_out'}:return
    if not cancel.is_set():
        store.update_segment(sid,asr_status='failed',asr_final=True,asr_recovery_status='exhausted',
                             asr_diagnostic=segment.get('asr_diagnostic') or {'category':'ASR_RECOVERY_EXHAUSTED'})
