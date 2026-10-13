"""Nonblocking remote-first samples shared by live and video windows."""
import subprocess
from runtime import backend_routing, mediakit


def sample(store, row, source, offset, target, cancel, local):
    from runtime.asr_router import cloud_available
    from runtime.live_frames import cloud_frame
    key=str(row['sample_at_ms'])
    selections=dict(row.get('remote_frame_selections',{}))
    selection=selections.get(key)
    if selection is None:
        selection=backend_routing.remote_choice(store,'frames',f"{row['id']}:{key}",budget=240)
        selections[key]=selection
        if not store.update_segment(row['id'],remote_frame_selections=selections):return False
        row['remote_frame_selections']=selections
    if selection['backend']=='mediakit' and not selection.get('local_takeover'):
        category=None
        try:
            record=row.get('frame_remote_samples',{}).get(key,{})
            capability={'ready':True} if record else cloud_available(store,capability='frames')
            if not capability['ready']:
                category=capability.get('code')
                ok=False
            else:
                ok=cloud_frame(store,row,source,offset,target,cancel)
        except (OSError,ValueError,TypeError,RuntimeError,subprocess.SubprocessError) as error:
            category=getattr(error,'diagnostic',{}).get('category')
            ok=False
        if cancel.is_set():return False
        if ok is None:return None
        if not store.update_segment(row['id'],remote_frame_selections=selections):return False
        backend_routing.remote_result(store,'frames',selection,ok,category=category)
        if ok:return True
        selections[key]={**selection,'local_takeover':True}
        if not store.update_segment(row['id'],remote_frame_selections=selections):return False
    if cancel.is_set():return False
    # Mark before local work: a restart never loops on an unavailable decoder.
    attempted=row.get('frame_local_attempted_times_ms',[])
    if row['sample_at_ms'] in attempted:
        from runtime.media import valid_frame
        return valid_frame(target,store.task(),store)
    if not store.update_segment(row['id'],frame_local_attempted_times_ms=attempted+[row['sample_at_ms']]):return False
    return local()


class WindowStore:
    """Journal remote requests on the sampled window, guarded by its work lease."""
    def __init__(self, store, row, token):
        self.store, self.row, self.token = store, row, token

    def __getattr__(self, name): return getattr(self.store, name)

    def update_segment(self, sid, **fields):
        import time
        from runtime.sampling import windows, save, tick
        with self.store.connection(True) as conn:
            tick(self.store,conn)
            current=next((r for r in windows(conn,self.session_id) if r['id']==sid),None)
            if (not current or current['review_status']!='pending' or current.get('review_started_at') is not None
                    or current.get('frame_lease_token')!=self.token or current.get('frame_lease_until',0)<=time.time()):return False
            current.update(fields)
            save(conn,self.session_id,current)
            self.row.update(fields)
            return True


def prepare_windows(store):
    import time
    import uuid
    import subprocess
    from runtime.sampling import windows, save, tick
    from runtime.realtime import recording_segments
    from runtime.local_asr import MediaCancellation
    from runtime.media import media_command, valid_frame
    store.finish_tick()
    task=store.task()
    cancel=MediaCancellation(store,None)
    if task.get('image_inspection') is False or cancel.is_set():return
    with store.connection(True) as conn:
        rows=[r for r in windows(conn,store.session_id) if r['review_status']=='pending' and r.get('window_sealed')
              and r.get('review_started_at') is None and (r.get('frame_preparation') in {None,'remote_pending'}
              or (r.get('frame_preparation')=='running' and r.get('frame_lease_until',0)<=time.time()))]
        if not rows:return
        row=rows[0];token=uuid.uuid4().hex
        row.update(frame_preparation='running',frame_lease_token=token,frame_lease_until=time.time()+90)
        save(conn,store.session_id,row)
    journal=WindowStore(store,row,token)
    frames=list(row.get('prepared_frames',[]));pending=False
    recordings=recording_segments(store)
    try:
        for n,fraction in enumerate((.25,.75)):
            if cancel.is_set():break
            at=row['start_ms']+round((row['end_ms']-row['start_ms'])*fraction)
            if any(f['time_ms']==at for f in frames):continue
            recording=next((s for s in recordings if s['start_ms']<=at<s['end_ms']),None)
            if not recording:
                pending=store.task().get('capture_status') not in {'ended','failed','stopped'}
                continue
            source=store.local_path(recording['media_file']);offset=(at-recording['start_ms'])/1000
            target=store.root/'frames'/f"sample-{row['index']:06d}-{n}.jpg"
            def local():
                try:
                    result=media_command([mediakit.config(task,'ffmpeg_bin','ffmpeg'),'-nostdin','-v','error','-y',
                        '-ss',str(offset),'-i',str(source),'-frames:v','1','-vf','scale=min(1280\\,iw):-2',
                        '-q:v','10',str(target)],store=store,timeout=10)
                    return result.returncode==0 and valid_frame(target,task,store)
                except (OSError,RuntimeError,subprocess.SubprocessError):return False
            ok=sample(journal,{**row,'sample_at_ms':at},source,offset,target,cancel,local)
            if ok is None:
                pending=True;break
            if ok:
                target.chmod(0o600)
                frames.append({'id':f"sample-{row['index']}-{n}",'path':str(target.relative_to(store.root)),'time_ms':at})
                if not journal.update_segment(row['id'],prepared_frames=frames):return
    finally:
        journal.update_segment(row['id'],prepared_frames=frames,
            frame_preparation='remote_pending' if pending else 'success' if len(frames)==2 else 'failed')
        with store.connection(True) as conn:tick(store,conn)
