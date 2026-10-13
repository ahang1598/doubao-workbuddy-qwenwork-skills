"""Remote-first ASR with one durable local recovery and preserved evidence."""
from runtime import backend_routing, mediakit
from runtime.full_asr import RecoveryStore
from runtime.local_asr import MediaCancellation


class EvidenceStore(RecoveryStore):
    def update_segment(self, sid, **fields):
        if fields.get('asr_status') == 'success' and 'subtitles' in fields:
            fields['subtitles'] = [s for s in fields['subtitles'] if s['text'].strip()]
            if not fields['subtitles'] and self.segment.get('speech_detected'):
                fields.update(asr_status='fallback_pending',
                    speech_gaps=self.segment.get('speech_gaps') or [{'start_ms':self.segment['start_ms'],'end_ms':self.segment['end_ms']}],
                    asr_diagnostic={'category':'ASR_EMPTY_SPEECH'})
        return super().update_segment(sid, **fields)


def process(processor, store, segment, cancel=None):
    from runtime.asr_router import cloud_available
    from runtime.live_backlog import Cancellation, enabled
    if enabled(store.task()): cancel=Cancellation(store,cancel,segment['id'])
    cancel=MediaCancellation(store,cancel)
    sid=segment['id']
    def current(): return next(s for s in store.segments() if s['id']==sid)
    if cancel.is_set() or segment.get('asr_final') or segment['asr_status'] in {'success','no_audio'} or segment.get('review_status') in {'done','skipped'}: return
    selection=segment.get('remote_asr_selection')
    if selection is None:
        selection=backend_routing.remote_choice(store,'asr',sid,budget=90)
        if not store.update_segment(sid,remote_asr_selection=selection):return
    local_selected=segment.get('asr_selection_reason')=='cloud_unavailable_local'
    if selection['backend']=='mediakit' and not local_selected:
        # An unknown submission is not replayable, even if the worker died before
        # saving a diagnostic. Known IDs are resumed inside their original budget.
        submitted=bool(segment.get('asr_task_id'))
        unknown=segment.get('asr_remote_status')=='submission_unknown' or segment['asr_status']=='submission_unknown'
        terminal=segment['asr_status'] in {'failed','timed_out','fallback_pending'}
        if not unknown and not terminal:
            mediakit.recover_credentials(store)
            cloud={'ready':True} if submitted else cloud_available(store)
            if cloud['ready'] and not mediakit.submissions_paused(store):
                if not store.update_segment(sid,asr_backend='mediakit'):return
                mediakit.process_asr(EvidenceStore(store,current()),current(),cancel=cancel,defer_failure=True)
            else:
                store.update_segment(sid,asr_status='fallback_pending',asr_diagnostic={
                    'category':cloud.get('code') or 'CLOUD_ASR_AUTH_UNAVAILABLE'})
        if cancel.is_set():return
        segment=current()
        block=store.task().get('asr_credential_block')
        if block and segment['asr_status'] in {'pending','running','submitted'}:
            store.update_segment(sid,asr_status='fallback_pending',asr_diagnostic={'category':block['category']})
            segment=current()
        if segment['asr_status']=='success' and not segment.get('speech_gaps'):
            backend_routing.remote_result(store,'asr',selection,True)
            return
        if segment['asr_status'] in {'running','submitted','pending'}:return
        backend_routing.remote_result(store,'asr',selection,False,
            category=(segment.get('asr_diagnostic') or {}).get('category'))
    if cancel.is_set():return
    segment=current()
    if not store.update_segment(sid,asr_backend='local',asr_status='fallback_pending',
            asr_selection_reason='cloud_unavailable_local',
            asr_remote_diagnostic=segment.get('asr_remote_diagnostic') or segment.get('asr_diagnostic')):return
    def failed(code):
        latest=current()
        store.update_segment(sid,asr_status='failed',asr_final=True,asr_recovery_status='unavailable' if code=='ASR_RUNTIME_UNAVAILABLE' else 'failed',
            asr_diagnostic={'category':code},speech_gaps=latest.get('speech_gaps') or
            ([] if latest.get('subtitles') else [{'start_ms':latest['start_ms'],'end_ms':latest['end_ms']}]))
    if segment.get('asr_recovery_attempts',0):
        failed('ASR_RECOVERY_INTERRUPTED');return
    task=store.task()
    current_live=task.get('inspection_policy')=='lite_live_realtime_v2'
    if current_live and task.get('asr_primary_backend')=='mediakit' and not task.get('asr_fallback_runtime'):
        if not processor.bind_ready_fallback(store):
            failed('ASR_RUNTIME_UNAVAILABLE');return
    with (processor.local_session(store,cancel) if current_live else processor.local_lock) as local:
        if cancel.is_set():return
        if not current_live:
            local=processor.local
            if task.get('asr_primary_backend')=='mediakit' and not task.get('asr_fallback_runtime'):
                import queue
                try:check=processor.ready_model.get_nowait()
                except queue.Empty:check={'ready':False}
                if not check.get('ready'):
                    failed('ASR_RUNTIME_UNAVAILABLE');return
                if not store.bind_fallback_model(check):return
        if not store.update_segment(sid,asr_status='pending',asr_diagnostic=None):return
        segment=current()
        local.process(EvidenceStore(store,segment),segment,cancel=cancel,recovery=True,defer_failure=True)
        if not cancel.is_set():
            latest=current()
            if latest['asr_status']!='success' and not latest.get('asr_final'):
                failed((latest.get('asr_diagnostic') or {}).get('category','ASR_RETRY_EXHAUSTED'))
