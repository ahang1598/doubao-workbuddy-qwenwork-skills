"""Optional sparse frame production; audio never waits on this worker."""
import time
import threading
import subprocess
from runtime import full_live

def validate_cloud_image(path):
    # Optional decoder: lack of it degrades pictures, never audio. Do not invoke ffmpeg.
    try:
        from PIL import Image
        if path.stat().st_size>8*1024*1024:return False
        with Image.open(path) as image:
            if image.format not in {'JPEG','PNG'} or image.width*image.height>16000000:return False
            image.verify()
        return True
    except Exception:return False

def prepare_one(store,cancel):
    from runtime.realtime import recording_segments
    from runtime.media import media_command,valid_frame
    from runtime.mediakit import config
    task=store.task()
    if task.get('image_inspection') is False:return
    if not full_live.enabled(task) or task.get('scenario_selection')=='pending' or not full_live.requires_frames(task['rules_snapshot']):return
    if cancel.is_set():return
    rows=[s for s in store.segments() if s['frame_status']=='pending' and s.get('frame_sample_times_ms')]
    if not rows:return
    row=rows[0]
    finished={f['time_ms'] for f in row.get('frames',[])}|set(row.get('frame_failed_times_ms',[]))
    at=next(t for t in row['frame_sample_times_ms'] if t not in finished)
    row={**row,'sample_at_ms':at}
    recording=next((s for s in recording_segments(store) if s['start_ms']<=at<s['end_ms']),None)
    if not recording:
        if task.get('capture_status') in {'ended','failed','stopped'}:
            store.update_segment(row['id'],frame_status='unavailable',frame_failure='recording_unavailable')
        return
    source=store.local_path(recording['media_file']);offset=(at-recording['start_ms'])/1000
    target=store.root/'frames'/f'live-{at}.jpg'
    state=dict(task.get('optional_frames',{}));ok=False
    remote_first=task.get('asr_policy')=='remote_first' and task.get('frames_policy')=='remote_first'
    if remote_first:
        from runtime.remote_frames import sample
        def local():
            try:
                result=media_command([config(task,'ffmpeg_bin','ffmpeg'),'-nostdin','-v','error','-y','-ss',str(offset),'-i',str(source),'-frames:v','1','-vf','scale=min(1280\\,iw):-2',str(target)],store=store,timeout=10)
                return result.returncode==0 and valid_frame(target,task,store)
            except (OSError,RuntimeError,subprocess.SubprocessError):return False
        ok=sample(store,row,source,offset,target,cancel,local)
        if ok is None:return
    elif not state.get('local_unavailable') and at not in row.get('frame_local_attempted_times_ms',[]):
        if not store.update_segment(row['id'],frame_local_attempted_times_ms=row.get('frame_local_attempted_times_ms',[])+[at]):return
        try:
            result=media_command([config(task,'ffmpeg_bin','ffmpeg'),'-nostdin','-v','error','-y','-ss',str(offset),'-i',str(source),'-frames:v','1','-vf','scale=min(1280\\,iw):-2',str(target)],store=store,timeout=10)
            ok=result.returncode==0 and valid_frame(target,task,store)
        except (OSError,RuntimeError,subprocess.SubprocessError):pass
        if not ok:
            state['local_unavailable']=True;store.update_task(optional_frames=state)
    elif at in row.get('frame_local_attempted_times_ms',[]) and target.is_file():
        ok=valid_frame(target,task,store)
    if not ok and task.get('asr_policy')=='local_first' and task.get('frames_policy')=='local_first' and not cancel.is_set():
        from runtime.asr_router import cloud_available
        if 'cloud_available' not in state:
            state['cloud_available']=cloud_available(store,capability='frames')['ready'];store.update_task(optional_frames=state)
        if state['cloud_available']:
            try:ok=cloud_frame(store,row,source,offset,target,cancel)
            except (OSError,ValueError,RuntimeError,subprocess.SubprocessError):ok=False
            if ok is None:return  # Saved remote task still running; query next heartbeat.
    if cancel.is_set():return
    failed=list(row.get('frame_failed_times_ms',[]));frames=list(row.get('frames',[]))
    if ok:
        target.chmod(0o600)
        frames.append({'id':f'live-frame-{at}','path':str(target.relative_to(store.root)),'time_ms':at})
    else:failed.append(at)
    remaining=set(row['frame_sample_times_ms'])-{f['time_ms'] for f in frames}-set(failed)
    fields={'frame_status':'pending' if remaining else 'unavailable' if failed else 'success',
            'frame_failure':'optional_frames_unavailable' if failed else None,'frame_failed_times_ms':failed}
    if ok:fields['frames']=frames
    store.update_segment(row['id'],**fields)

def cloud_frame(store,row,source,offset,target,cancel):
    from runtime import mediakit
    from runtime.frame_router import download_image
    task=store.task();records=dict(row.get('frame_remote_samples',{}));key=str(row['sample_at_ms']);record=dict(records.get(key,{}))
    try:env=mediakit.credentials_env(store)
    except (OSError,ValueError):raise mediakit.CommandFailure(None,category='credentials_unavailable') from None
    env={**env,'MEDIAKIT_SURFACE':'skill','MEDIAKIT_RUNTIME':env.get('MEDIAKIT_RUNTIME') or 'unknown'}
    binary=mediakit.config(task,'mediakit_bin','mediakit-cli')
    if record.get('status')=='unknown' and not record.get('task_id'):return False
    deadline=record.get('deadline_at',record.get('started_at',time.time())+180)
    if task.get('asr_policy')=='remote_first':
        # Leave time for one local extraction before a video window expires.
        if task.get('inspection_policy')=='lite_sample_v1':deadline=min(deadline,row.get('created_at',time.time())+110)
        deadline=min(deadline,task.get('finishing',{}).get('media_deadline_at',task.get('finishing',{}).get('deadline_at',float('inf'))))
    if time.time()>=deadline:return False
    if not record.get('task_id'):
        record={'status':'unknown','started_at':time.time(),'deadline_at':deadline}
        records[key]=record
        if not store.update_segment(row['id'],frame_remote_samples=records):return False
        result=mediakit.invoke(binary,['video','extract-frames','--video-url',str(source),
                '--snapshot-type','SpecifiedTime','--specified-time',__import__('json').dumps([offset])],env=env,timeout=min(10,max(.001,deadline-time.time())),store=store)
        remote_id=result.get('task_id')
        if not isinstance(remote_id,str) or not remote_id:return False
        record.update(status='submitted',task_id=remote_id)
        records[key]=record
        if not store.update_segment(row['id'],frame_remote_samples=records):return False
    if cancel.is_set():return False
    if time.time()>=deadline:return False
    result=mediakit.invoke(binary,['shared','query-task','--task-id',record['task_id']],env=env,timeout=min(10,deadline-time.time()),store=store)
    if result.get('status') in {'running','queued','pending','submitted','processing'}:return None
    snapshots=result.get('snapshots',[])
    if result.get('status')!='completed' or not isinstance(snapshots,list) or len(snapshots)!=1 or not isinstance(snapshots[0],dict):return False
    url=snapshots[0].get('image_url')
    if not isinstance(url,str):return False
    temporary=target.with_suffix('.download')
    try:
        download_image(url,temporary,store)
        if not validate_cloud_image(temporary):return False
        temporary.replace(target);return True
    finally:temporary.unlink(missing_ok=True)

def run(store,done,cancel):
    from runtime.local_asr import MediaCancellation
    token=MediaCancellation(store,cancel)
    while not done.is_set() and not token.is_set():
        try:prepare_one(store,token)
        except Exception:store.log('optional_frames','画面暂不可用，语音检测继续')
        done.wait(1)
