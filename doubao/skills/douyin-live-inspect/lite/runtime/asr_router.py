"""Explicit per-task local-first policy, with durable per-segment backend selection."""
import os
import shutil
import subprocess
import json
import time
import threading
import queue
import contextlib
import errno
from runtime import credentials, mediakit, backend_routing
from runtime.local_asr import Processor as LocalProcessor, LocalASR, ASRError


def cloud_available(store=None, *, capability="asr", probe_timeout=10):
    binary=shutil.which('mediakit-cli')
    if not binary: return {'ready':False,'code':'CLOUD_ASR_UNAVAILABLE'}
    if store is None:
        ready=all(os.environ.get(k) for k in credentials.ENV_KEYS)
    else:
        ready=credentials.status(store.workspace_root)['status']=='available'
    if not ready: return {'ready':False,'code':'CLOUD_ASR_AUTH_UNAVAILABLE'}
    try:
        operation = ('extract-frames', ('video-url','video_url')) if capability=='frames' else ('asr-subtitles', ('audio-url','audio_url'))
        from runtime.live_backlog import enabled
        # Capability-only callers may supply just a workspace, without a task.
        task=store.task() if hasattr(store,'task') else {}
        options={'store':store} if enabled(task) else {}
        for command,fields in [(['video',operation[0]],operation[1]),(['shared','query-task'],('task-id','task_id'))]:
            value=mediakit.invoke(binary,[*command,'--schema'],timeout=probe_timeout,**options)
            if not any(f in json.dumps(value).lower() for f in fields): return {'ready':False,'code':'CLOUD_ASR_UNAVAILABLE'}
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError):
        return {'ready':False,'code':'CLOUD_ASR_UNAVAILABLE'}
    return {'ready':True,'code':None}


def initialize_cloud(store):
    if store.task().get('asr_policy') not in {'remote_first','local_first'}: return
    from runtime.full_live import enabled as full
    if cloud_available()['ready'] or (not full(store.task()) and cloud_available(capability='frames')['ready']):
        credentials.refresh(store.workspace_root,initialize=True)


class Processor:
    def __init__(self,store):
        self.local=LocalProcessor(store)
        self.local_lock=threading.Lock()
        self.local_pool=threading.Condition()
        self.local_workers=[self.local]
        self.local_available=[self.local]
        self.local_limit=10
        self.ready_model=queue.Queue(maxsize=1)
        self.cache_stop=threading.Event()
        if store.task().get('pipeline_version')==2 and store.task().get('asr_primary_backend')=='mediakit':
            def check_cache():
                from runtime.artifacts import prepare
                # Read-only cache probe in parallel with cloud work; recovery
                # never waits for downloads or for this potentially slow check.
                while not self.cache_stop.is_set():
                    try:check=prepare(task=store.task(),install=False,model_only=True)
                    except Exception:check={'ready':False}
                    if check.get('ready'):
                        if self.cache_stop.is_set():return
                        self.ready_model.put(check)
                        if store.task().get('asr_policy')=='remote_first':store.update_task(local_backup_status='ready')
                        return
                    self.cache_stop.wait(2)
            threading.Thread(target=check_cache,daemon=True).start()
    def close(self):
        self.cache_stop.set()
        for worker in self.local_workers:worker.close()

    @contextlib.contextmanager
    def local_session(self,store,cancel=None):
        if store.task().get('inspection_policy')!='lite_live_realtime_v2':
            with self.local_lock:
                if self.local.bridge is None:
                    self.local.bridge=LocalASR(store)
                    self.local.bridge.initialize(cancel)
                yield self.local
            return
        while True:
            with self.local_pool:
                if cancel is not None and cancel.is_set():raise ASRError('ASR_CANCELLED')
                if self.local_available:
                    worker=self.local_available.pop()
                elif len(self.local_workers)<self.local_limit:
                    worker=LocalProcessor(store)
                    self.local_workers.append(worker)
                else:
                    self.local_pool.wait(.1)
                    continue
            if worker.bridge is None:
                try:
                    worker.bridge=LocalASR(store)
                    worker.bridge.initialize(cancel)
                except (OSError,MemoryError) as error:
                    worker.close()
                    with self.local_pool:
                        self.local_workers.remove(worker)
                        if isinstance(error,MemoryError) or error.errno in {errno.ENOMEM,errno.EAGAIN}:
                            self.local_limit=len(self.local_workers)
                            if self.local_limit:
                                self.local_pool.notify()
                                continue
                        self.local_pool.notify()
                    raise
                except Exception:
                    worker.close()
                    with self.local_pool:
                        self.local_available.append(worker)
                        self.local_pool.notify()
                    raise
            break
        try:yield worker
        finally:
            with self.local_pool:
                self.local_available.append(worker)
                self.local_pool.notify()

    def bind_ready_fallback(self,store):
        with self.local_lock:
            task=store.task()
            if task.get('asr_primary_backend')!='mediakit' or task.get('asr_fallback_runtime'):
                return True
            try:check=self.ready_model.get_nowait()
            except queue.Empty:check={'ready':False}
            return bool(check.get('ready')) and store.bind_fallback_model(check)
    def local_backup(self,store,segment,cancel):
        started=time.monotonic()
        try:
            return self._local_backup(store,segment,cancel)
        except (OSError,ValueError,KeyError,TypeError,RuntimeError,subprocess.SubprocessError):
            # Model setup errors are bounded evidence failures, not worker failures.
            store.skip_asr(segment['id'],'ASR_RUNTIME_UNAVAILABLE',asr_recovery_status='unavailable',
                           asr_recovery_error='ASR_RUNTIME_UNAVAILABLE',
                           asr_recovery_elapsed_ms=round((time.monotonic()-started)*1000))
            return True

    def _local_backup(self,store,segment,cancel):
        if cancel is not None and cancel.is_set(): return True
        task=store.task()
        if (task.get('asr_policy')!='local_first' or task.get('asr_primary_backend') not in {'local','mediakit'}
                or segment.get('asr_status') in {'success','no_audio'}
                or segment.get('review_status') in {'done','skipped'}):
            return False
        started=time.monotonic()
        def finish(result,code=None):
            fields={'asr_recovery_status':result,'asr_recovery_error':code,
                    'asr_recovery_elapsed_ms':round((time.monotonic()-started)*1000)}
            if result=='success':store.update_segment(segment['id'],**fields)
            else:store.skip_asr(segment['id'],code or 'ASR_RETRY_EXHAUSTED',**fields)
        if segment.get('asr_recovery_status') in {'failed','unavailable'}:
            store.skip_asr(segment['id'],segment.get('asr_recovery_error') or 'ASR_RETRY_EXHAUSTED')
            return True
        if segment.get('asr_recovery_attempts',0)>=1:
            finish('failed','ASR_RECOVERY_INTERRUPTED')
            return True
        # Own a durable local selection before any inference; keep remote IDs for audit.
        if not store.update_segment(segment['id'],asr_backend='local',asr_status='fallback_pending',
                                    asr_selection_reason='cloud_unavailable_local',
                                    asr_recovery_status='preparing',invalidate_review=True,_asr_recovery=True,
                                    asr_remote_diagnostic=segment.get('asr_remote_diagnostic') or segment.get('asr_diagnostic')):return True
        if task.get('asr_primary_backend')=='mediakit' and not task.get('asr_fallback_runtime'):
            from runtime.artifacts import prepare
            from runtime import model_preparation
            from runtime.realtime_policy import enabled
            if enabled(task):
                try:check=self.ready_model.get_nowait()
                except queue.Empty:check={'ready':False}
            else:check=prepare(task=task,install=False,model_only=True)
            if not enabled(task) and not check['ready'] and (check.get('issues') or [{}])[0].get('code')=='ARTIFACT_CACHE_MISSING':
                job_id=task.get('asr_fallback_preparation_id') or task.get('model_preparation_id')
                if not job_id:
                    state=model_preparation.ensure(task)
                    job_id=state['id']
                    store.update_task(asr_fallback_preparation_id=job_id)
                state=model_preparation.wait(job_id, cancel.is_set if cancel is not None else None)
                if state['status']=='cancelled':return True
                if state['status']=='ready':check=prepare(task=task,install=False,model_only=True)
            if not check['ready']:
                finish('unavailable','ASR_RUNTIME_UNAVAILABLE')
                return True
            if not store.bind_fallback_model(check):return True
        if cancel is not None and cancel.is_set():return True
        self.local.close()
        if not store.update_segment(segment['id'],asr_status='pending',asr_recovery_status='running',asr_diagnostic=None):return True
        segment=next(s for s in store.segments() if s['id']==segment['id'])
        self.local.process(store,segment,cancel=cancel,recovery=True,defer_failure=True)
        current=next(s for s in store.segments() if s['id']==segment['id'])
        if cancel is not None and cancel.is_set():return True
        if current['asr_status'] in {'success','no_audio'}:
            finish('success')
            backend_routing.promote(store,'asr','local',segment.get('asr_route_generation',0),
                                    task.get('asr_primary_backend','local'))
        else:
            finish('failed',(current.get('asr_diagnostic') or {}).get('category','ASR_RETRY_EXHAUSTED'))
        return True
    def process(self,store,segment,*,cancel=None):
        from runtime.realtime_policy import enabled
        if enabled(store.task()):
            from runtime.local_asr import MediaCancellation
            from runtime.live_backlog import Cancellation
            deadline=None
            if store.task().get('inspection_policy')=='lite_live_realtime_v1':
                deadline=segment.get('asr_execution_deadline_at',time.time()+60)
                if not store.update_segment(segment['id'],asr_execution_deadline_at=deadline):return
            cancel=MediaCancellation(store,Cancellation(store,cancel,segment['id']),deadline)
            if cancel.is_set():return
        if store.task().get('asr_policy')=='remote_first':
            from runtime.remote_asr import process
            return process(self,store,segment,cancel)
        from runtime.full_live import enabled as full
        if full(store.task()):
            from runtime.full_asr import process
            return process(self,store,segment,cancel)
        if cancel is not None and cancel.is_set(): return
        if segment.get('review_status') in {'done','skipped'} or segment.get('asr_final'):return
        # Also fence pending local content gaps persisted by older versions.
        reason=(segment.get('asr_diagnostic') or {}).get('category') or segment.get('local_failure')
        if (reason=='ASR_EMPTY_SPEECH' and segment.get('asr_backend')!='mediakit'
                and not segment.get('asr_task_id') and segment.get('asr_status') not in {'success','no_audio'}):
            store.update_segment(segment['id'],asr_status='failed',asr_final=True,
                                 asr_diagnostic={'category':reason})
            return
        task=store.task()
        if task.get('pipeline_version') == 2:
            return self.process_v2(store,segment,cancel)
        if segment.get('asr_recovery_attempts',0)>=1 and segment.get('asr_status') not in {'success','no_audio'}:
            self.local_backup(store,segment,cancel)
            return
        if task.get('asr_policy')=='local_only' and segment.get('asr_status') in {'failed','timed_out','submission_unknown'}:
            store.skip_asr(segment['id'],(segment.get('asr_diagnostic') or {}).get('category','ASR_RETRY_EXHAUSTED'))
            return
        unselected=not segment.get('asr_backend') and not segment.get('asr_task_id')
        route=backend_routing.choice(task,'asr',task.get('asr_primary_backend') or 'local')
        if task.get('asr_policy')=='local_first' and 'asr_route_generation' not in segment:
            backend=segment.get('asr_backend') or ('mediakit' if segment.get('asr_task_id') else route['backend'])
            store.update_segment(segment['id'],asr_backend=backend,asr_route_generation=route['generation'])
            segment=next(s for s in store.segments() if s['id']==segment['id'])
        # A durable local selection takes precedence over retained remote IDs.
        remote=segment.get('asr_backend')=='mediakit' or bool(segment.get('asr_task_id'))
        if segment.get('asr_status') in {'success','no_audio'}: return
        if segment.get('asr_selection_reason')=='cloud_unavailable_local':
            self.local_backup(store,segment,cancel)
            return
        if segment.get('asr_status') in {'failed','timed_out','submission_unknown','fallback_pending'} and remote:
            if self.local_backup(store,segment,cancel): return
        if segment.get('asr_status')=='submission_unknown': return
        if mediakit.unsubmitted_auth_failure(segment):
            store.update_segment(segment['id'],asr_status='pending',asr_diagnostic=None)
            segment=next(s for s in store.segments() if s['id']==segment['id'])
        if remote and (mediakit.submissions_paused(store) or task.get('asr_cloud_failure')) and self.local_backup(store,segment,cancel):
            return
        if unselected and remote and segment.get('asr_status')=='pending' and not segment.get('local_failure'):
            if task.get('asr_policy')!='local_first': return
            cloud=cloud_available(store)
            if not cloud['ready']:
                if self.local_backup(store,segment,cancel):return
                store.update_segment(segment['id'],asr_status='failed',asr_diagnostic={'category':cloud['code']})
                return
            store.update_segment(segment['id'],asr_backend='mediakit',asr_status='pending',
                                 asr_selection_reason=task.get('asr_selection_reason','preferred_cloud'))
            segment=next(s for s in store.segments() if s['id']==segment['id'])
            remote=True
        if not remote:
            if segment.get('asr_status')=='failed':
                self.local_backup(store,segment,cancel)
                return
            # A verified backup supersedes the startup failure, including after resume.
            recovered_model = task.get('asr_primary_backend')=='mediakit' and task.get('asr_fallback_runtime')
            if task.get('local_setup_error') and not recovered_model:
                reason=task['local_setup_error']
            else:
                self.local.process(store,segment,cancel=cancel,defer_failure=True)
                segment=next(s for s in store.segments() if s['id']==segment['id'])
                if segment.get('asr_final'):return
                if segment['asr_status'] not in {'failed','fallback_pending'}:
                    if segment['asr_status']=='success': store.update_segment(segment['id'],asr_backend='local')
                    return
                reason=(segment.get('asr_diagnostic') or {}).get('category','ASR_LOCAL_FAILED')
            if task.get('asr_policy')!='local_first':
                store.update_segment(segment['id'],asr_status='failed',asr_diagnostic={'category':reason})
                if task.get('asr_policy')=='local_only':store.skip_asr(segment['id'],reason)
                return
            cloud=cloud_available(store)
            if not cloud['ready']:
                store.update_segment(segment['id'],asr_status='failed',local_failure=reason,
                                     asr_diagnostic={'category':cloud['code']})
                self.local_backup(store,next(s for s in store.segments() if s['id']==segment['id']),cancel)
                return
            # Persist the remote choice before any side effect; recovery uses MediaKit's own submission journal.
            store.update_segment(segment['id'],asr_backend='mediakit',local_failure=reason,
                                 asr_status='pending',asr_diagnostic=None)
            segment=next(s for s in store.segments() if s['id']==segment['id'])
        if mediakit.submissions_paused(store) and not segment.get('asr_task_id'):
            store.update_segment(segment['id'],asr_status='fallback_pending',asr_diagnostic={'category':'CLOUD_ASR_AUTH_UNAVAILABLE'})
            self.local_backup(store,next(s for s in store.segments() if s['id']==segment['id']),cancel)
            return
        mediakit.process_asr(store,segment,cancel=cancel,
                             defer_failure=task.get('asr_policy')=='local_first'
                             and task.get('asr_primary_backend') in {'local','mediakit'})
        segment=next(s for s in store.segments() if s['id']==segment['id'])
        if segment.get('asr_status') in {'failed','timed_out','submission_unknown','fallback_pending'} or mediakit.submissions_paused(store):
            self.local_backup(store,segment,cancel)
        elif segment.get('asr_status')=='success' and segment.get('local_failure'):
            backend_routing.promote(store,'asr','mediakit',segment.get('asr_route_generation',0),
                                    task.get('asr_primary_backend') or 'local')

    def process_v2(self,store,segment,cancel):
        """One alternate backend; terminal speech gaps still admit visual review."""
        if segment.get('asr_final') or segment['asr_status'] in {'success','no_audio'}:return
        from runtime.local_asr import MediaCancellation
        from runtime.live_backlog import Cancellation, enabled
        if enabled(store.task()):cancel=Cancellation(store,cancel,segment['id'])
        cancellation=MediaCancellation(store,cancel)
        if cancellation.is_set():return
        task=store.task()
        sid=segment['id']
        def current():return next(s for s in store.segments() if s['id']==sid)
        def video_stopping():return task.get('kind','live')!='live' and store.should_stop()
        def fail(code):
            if cancellation.is_set():return
            latest=current()
            remote_history=({'asr_remote_status':latest['asr_status'],
                             'asr_remote_diagnostic':latest.get('asr_diagnostic')}
                            if latest.get('asr_backend')=='mediakit' else {})
            store.update_segment(sid,asr_status='failed',subtitles=latest.get('subtitles',[]),asr_final=True,
                asr_diagnostic={'category':code},asr_recovery_status='failed',**remote_history)
        remote=segment.get('asr_backend')=='mediakit' or bool(segment.get('asr_task_id'))
        if not remote:
            if segment.get('analysis_unit')=='segment' and not segment.get('local_failure'):
                # Whole-WAV recognition has not run in the capture thread. Share
                # the resident model with recovery, but never use it concurrently.
                with self.local_lock:
                    self.local.process(store,segment,cancel=cancellation,defer_failure=True)
                segment=current()
                if cancellation.is_set() or segment.get('asr_final') or segment['asr_status'] in {'success','no_audio','pending'}:
                    return
                reason=(segment.get('asr_diagnostic') or {}).get('category','ASR_LOCAL_FAILED')
                store.update_segment(sid,local_failure=reason)
                segment=current()
            # Legacy streaming units already tried this interval in capture.
            if task.get('asr_policy')!='local_first' or video_stopping() or not cloud_available(store)['ready']:
                fail(segment.get('local_failure') or 'CLOUD_ASR_UNAVAILABLE');return
            if cancellation.is_set():return
            store.update_segment(sid,asr_backend='mediakit',asr_status='pending')
            segment=current();remote=True
        if segment['asr_status'] not in {'failed','timed_out','submission_unknown','fallback_pending'} and not video_stopping():
            mediakit.process_asr(store,segment,cancel=cancel,defer_failure=True)
            segment=current()
            if segment['asr_status'] in {'pending','submitted','running'} and not video_stopping():return
            if segment['asr_status']=='success':
                backend_routing.promote(store,'asr','mediakit',segment.get('asr_route_generation',0),task.get('asr_primary_backend','local'))
                return
        if cancellation.is_set():return
        if segment.get('local_failure') or segment.get('asr_recovery_attempts',0):
            fail(segment.get('local_failure') or 'ASR_RETRY_EXHAUSTED');return
        if segment.get('asr_status') == 'submission_unknown':return  # Reconcile only; never repeat an unknown submission.
        # Never wait for model downloads when recovering a failed cloud interval.
        try:
            with self.local_lock:
                if cancellation.is_set():return
                # Concurrent failed windows share one readiness result and model.
                # Refresh after taking the lock: another window may have bound it.
                task=store.task()
                if task.get('asr_primary_backend')=='mediakit' and not task.get('asr_fallback_runtime'):
                    try:check=self.ready_model.get_nowait()
                    except queue.Empty:check={'ready':False}
                    if not check['ready']:
                        fail('ASR_RUNTIME_UNAVAILABLE');return
                    if not store.bind_fallback_model(check):return
                store.update_segment(sid,asr_status='pending',asr_backend='local',
                    asr_selection_reason='cloud_unavailable_local',asr_remote_diagnostic=segment.get('asr_diagnostic'))
                self.local.process(store,current(),cancel=cancel,recovery=True,defer_failure=True)
            result=current()
            if result['asr_status']=='success':
                backend_routing.promote(store,'asr','local',segment.get('asr_route_generation',0),task.get('asr_primary_backend','local'))
            elif not cancellation.is_set():
                fail((result.get('asr_diagnostic') or {}).get('category','ASR_RETRY_EXHAUSTED'))
        except (OSError,ValueError,RuntimeError,subprocess.SubprocessError):
            fail('ASR_RUNTIME_UNAVAILABLE')
