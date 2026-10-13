"""PCM journal -> utterance evidence. Recording chunks never gate local inference.

The pipe reader only persists audio. Model calls and cloud recovery are owned by
separate threads, so a slow recognizer cannot apply backpressure to live capture.
"""
import os
from pathlib import Path
import shutil
import threading
import time
import wave

from runtime import backend_routing, live_backlog
from runtime.local_asr import LocalASR, ASRError, RETRYABLE, MediaCancellation
from runtime.store import Store, atomic_json

FRAME_PERIOD_MS = 500
FRAME_SYNC_SECONDS = 1.0


class CaptureStream:
    def __init__(self,store,session,index,bridge=None,cancel=None,has_audio=True):
        self.store=Store(store.root)
        self.session,self.index,self.bridge,self.cancel=session,index,bridge,cancel
        from runtime.sampling import enabled
        from runtime.full_live import enabled as full
        self.full_live=full(store.task())
        self.sampled=enabled(store.task()) or self.full_live
        self.progress=store.root/'media'/f'progress-{index:06d}.txt'
        self.has_audio=has_audio
        self.audio_gap=False
        self.base=session['base_ms']
        self.raw=store.root/'audio'/f'capture-{index:06d}.pcm'
        self.frames=store.root/'frames'/f'.capture-{index:06d}'
        self.frames.mkdir(mode=0o700,exist_ok=True)
        self.done=threading.Event()
        self.error=None
        self.offset=0
        self.committed=self.base
        self.partial_at=0
        self.last_partial=None
        self.reader=self.consumer=None
        self.stream_open=False
        self.restarts=0
        self.raw.touch(mode=0o600,exist_ok=True)
        # This checkpoint is independent of SQL insertion. Replaying the same
        # unit index after a crash is idempotent and never duplicates evidence.
        self.journal=self.raw.with_suffix('.json')
        if self.journal.exists():
            import json
            old=json.loads(self.journal.read_text())
            self.offset=old['byte_offset'];self.committed=old['committed_ms']
        existing=[s for s in store.segments() if s.get('capture_session')==index]
        if existing:
            self.committed=max(self.committed,max(s['end_ms'] for s in existing))
            last=max(existing,key=lambda s:s['end_ms'])
            self.offset=last.get('pcm_byte_end',(self.committed-self.base)*32)
        self.unit_index=max((s['index'] for s in store.segments()),default=-1)+1

    def outputs(self):
        args=[]
        duration=self.session.get('duration_ms')
        limit=['-t',str(duration/1000)] if duration is not None else []
        if self.has_audio:
            args+=limit+['-map','0:a:0','-vn','-ac','1','-ar','16000',
                   '-af','aresample=async=1:first_pts=0','-c:a','pcm_s16le','-f','s16le','pipe:1']
        if self.sampled or self.store.task().get('image_inspection') is False:return args
        vf='fps=2'
        vf+=',scale=min(1280\\,iw):-2'
        args+=limit+['-map','0:v:0?','-an','-vf',vf]
        args+=['-start_number','0','-atomic_writing','1',str(self.frames/'%09d.jpg')]
        return args

    def media_available_ms(self):
        # Sparse JPEG timestamps cannot be used as the media clock (silent input).
        if not self.sampled:return 0
        try:
            values=[int(line.split('=',1)[1])//1000 for line in self.progress.read_text().splitlines()
                    if line.startswith('out_time_us=') and line.split('=',1)[1].lstrip('-').isdigit()]
            elapsed=max(values,default=0)
            if self.done.is_set() and not self.has_audio and self.session.get('listing'):
                import csv
                try:
                    with (self.store.root/self.session['listing']).open() as stream:
                        elapsed=max([elapsed]+[round(float(row[2])*1000) for row in csv.reader(stream) if len(row)>=3])
                except (OSError,ValueError):pass
            duration=self.session.get('duration_ms')
            return min(elapsed,duration) if duration is not None else elapsed
        except OSError:return 0

    def start(self,process):
        def collect():
            try:
                with self.raw.open('ab',buffering=0) as out:
                    last_progress=0
                    while True:
                        data=process.stdout.read(3200)
                        if not data:break
                        out.write(data)
                        if time.monotonic()-last_progress>=1:
                            self.store.update_progress(capture_active_span={'start_ms':self.base,'end_ms':self.base+out.tell()//32})
                            last_progress=time.monotonic()
            except (OSError,ValueError):self.error='PCM_WRITE_FAILED'
            finally:self.done.set()
        self.reader=threading.Thread(target=collect,daemon=True)
        self.consumer=threading.Thread(target=self.consume,daemon=True)
        self.reader.start();self.consumer.start()

    def stopped(self):
        if self.cancel is not None and self.cancel.is_set():return True
        state=self.store.finish_tick()
        return bool(state and (state.get('phase')=='completed' or state.get('mode')=='immediate' or
            time.time()>=state.get('media_deadline_at',float('inf'))))

    def available(self):
        if self.has_audio:return self.raw.stat().st_size//2*2
        frames=list(self.frames.glob('*.jpg'))
        if self.sampled:return max(self.offset,self.media_available_ms()*32)
        if not frames:return self.offset
        end=(max(int(p.stem) for p in frames)+1)*FRAME_PERIOD_MS
        return end*32

    def skip_audio(self, end, code):
        # The durable row precedes the checkpoint so a crash cannot replay this gap.
        end = max(self.committed, end)
        if end <= self.committed:return
        fields = live_backlog.gap_fields(self.committed, end, code)
        fields.update(capture_session=self.index, analysis_unit='gap', frame_status='failed', audio_file=None)
        self.store.add_segment(self.unit_index,self.committed,end,
                              f'media/session-{self.index:06d}.json',evidence=fields)
        self.unit_index += 1
        self.committed = end
        self.offset = (end-self.base)*32
        atomic_json(self.journal,{'byte_offset':self.offset,'committed_ms':end})
        self.stream_open = False
        self.last_partial = None
        self.store.update_progress(live_subtitle=None,asr_consumed_ms=end)

    def catch_up(self, available):
        task = self.store.task()
        if not self.has_audio or not live_backlog.enabled(task):return
        draining = bool(task.get('finishing'))
        if task.get('capture_status') not in {'running','ended','stopped','failed'} and not draining:return
        limit = live_backlog.KEEP_MS if draining else live_backlog.MAX_BACKLOG_MS
        if task.get('local_asr_mode') == 'segment' and not draining and not self.done.is_set():
            # A configured WAV must fill once before it is eligible for inference.
            limit += task.get('segment_seconds',30)*1000
        if available-self.offset > limit*32:
            target = self.base+available//32-live_backlog.KEEP_MS
            self.skip_audio(target,live_backlog.BACKLOG)

    def start_local(self):
        if self.bridge is None:
            self.bridge=LocalASR(self.store)
            self.bridge.initialize(MediaCancellation(self.store,self.cancel))
        if not self.stream_open:
            self.bridge.request('stream-start',audio_path=str(self.raw),byte_offset=self.offset,
                                offset_ms=self.base+self.offset//32,timeout=max(.001,live_backlog.remaining(self.store.task(),3)),cancel=MediaCancellation(self.store,self.cancel))
            self.stream_open=True

    def _frame_candidates(self, start, end):
        return sorted((self.base + int(path.stem) * FRAME_PERIOD_MS, path)
                      for path in self.frames.glob('*.jpg')
                      if start <= self.base + int(path.stem) * FRAME_PERIOD_MS < end)

    def _wait_for_frames(self, start, end):
        """Let the sibling ffmpeg image muxer catch up with the PCM pipe.

        Audio reaches Python through a pipe while JPEGs are atomically renamed by
        another ffmpeg output.  A short utterance can therefore finalize before
        its already-decoded frame becomes visible.  Wait only while capture is
        active, and only until the image timeline reaches this utterance.
        """
        candidates = self._frame_candidates(start, end)
        if self.sampled:return candidates
        deadline = time.monotonic() + FRAME_SYNC_SECONDS
        while not candidates and not self.done.is_set() and time.monotonic() < deadline:
            latest = max((int(path.stem) for path in self.frames.glob('*.jpg')), default=-1)
            if self.base + (latest + 1) * FRAME_PERIOD_MS >= end:
                break
            self.done.wait(min(.02, max(0, deadline - time.monotonic())))
            candidates = self._frame_candidates(start, end)
        return candidates

    def publish(self,unit,backend):
        from runtime.media import valid_frame
        start,end=unit['start_ms'],unit['end_ms']
        # Decoder timestamps round samples; never ask for synthetic/sub-ms bytes.
        if self.has_audio and not self.audio_gap:
            size=self.raw.stat().st_size
            end=min(end,self.base+(size+31)//32 if 'pcm_byte_end' in unit else self.base+size//32)
        task=self.store.task()
        if task.get('kind')=='video':end=min(end,task.get('source_duration_ms',end))
        if end<=self.committed:return
        start=max(start,self.committed)
        audio=None
        if self.has_audio and not self.audio_gap:
            audio=self.store.root/'audio'/f'unit-{self.index:06d}-{start}.wav'
            with self.raw.open('rb') as source:
                byte_start=unit.get('pcm_byte_start',(start-self.base)*32)
                byte_end=unit.get('pcm_byte_end',(end-self.base)*32)
                source.seek(byte_start)
                pcm=source.read(byte_end-byte_start)
            if len(pcm)!=byte_end-byte_start:raise OSError('incomplete PCM journal')
            temp=audio.with_suffix('.tmp')
            with wave.open(str(temp),'wb') as wav:
                wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(16000);wav.writeframes(pcm)
            os.chmod(temp,0o600);os.replace(temp,audio)
        # Live images are published atomically by ffmpeg; only same-interval
        # images may be used. No borrowing a later/earlier frame as evidence.
        candidates=[] if self.store.task().get('image_inspection') is False else self._wait_for_frames(start,end)
        selected=[]
        interval=self.store.task().get('frame_interval_seconds',10)*1000
        for at,path in candidates:
            if not selected or at-selected[-1][0]>=interval:selected.append((at,path))
        if candidates and (not selected or selected[-1]!=candidates[-1]):selected.append(candidates[-1])
        frames=[]
        for n,(at,path) in enumerate(selected):
            if not valid_frame(path,self.store.task(),self.store):continue
            target=self.store.root/'frames'/f'unit-{self.index}-{start}-{n}.jpg'
            shutil.copyfile(path,target);os.chmod(target,0o600)
            frames.append({'id':f'frame-u-{self.index}-{start}-{n}','path':str(target.relative_to(self.store.root)),'time_ms':at})
        error=unit.get('error') or ('AUDIO_TIMELINE_GAP' if self.audio_gap else None)
        subtitles=[]
        if unit.get('text'):
            subtitles=[{'id':f'asr-u-{self.index}-{start}','text':unit['text'],'start_ms':start,'end_ms':end}]
        route=backend_routing.choice(self.store.task(),'asr',self.store.task().get('asr_primary_backend','local'))
        asr_status='no_audio' if not self.has_audio else 'pending' if backend=='mediakit' or unit.get('asr_pending') else 'failed' if self.audio_gap else 'fallback_pending' if error else 'success'
        fields={'analysis_unit':'segment' if unit.get('asr_pending') else 'cloud_window' if backend=='mediakit' else 'utterance' if subtitles or error else 'silence',
            'capture_session':self.index,'evidence_ready_at':time.time(),'frames':frames,'frame_status':'success' if frames else 'failed',
            'subtitles':subtitles,'asr_status':asr_status,'asr_backend':backend,
            'asr_route_generation':route['generation'],'continuation':unit.get('continuation',False),
            'speech_detected':unit.get('speech_detected',False),
            'audio_file':str(audio.relative_to(self.store.root)) if audio else None}
        if unit.get('cut_reason'):
            fields['cut_reason']=unit['cut_reason']
            fields['pcm_byte_end']=unit['pcm_byte_end']
        if self.audio_gap or (error=='ASR_EMPTY_SPEECH' and not self.full_live):
            # Missing words are an evidence gap, not a broken local backend.
            fields.update(asr_status='failed',asr_final=True)
        if error:fields.update(local_failure=error,asr_diagnostic={'category':error})
        self.store.add_segment(self.unit_index,start,end,
            f'media/session-{self.index:06d}.json',evidence=fields)
        self.unit_index+=1;self.committed=end
        atomic_json(self.journal,{'byte_offset':unit.get('pcm_byte_end',(end-self.base)*32),'committed_ms':end})
        for path in self.frames.glob('*.jpg'):
            if not self.sampled and self.base+int(path.stem)*500<end:path.unlink(missing_ok=True)

    def consume(self):
        try:
            while not self.stopped():
                available=self.available()
                self.catch_up(available)
                task=self.store.task()
                backend=backend_routing.choice(task,'asr',task.get('asr_primary_backend','local'))['backend']
                if not self.has_audio:backend='local'
                if backend=='mediakit' and self.stream_open:
                    for unit in self.bridge.request('stream-finish',timeout=max(.001,live_backlog.remaining(self.store.task(),5)),cancel=MediaCancellation(self.store,self.cancel))['finals']:self.publish(unit,'local')
                    self.stream_open=False
                if self.offset<available:
                    if backend=='local' and self.has_audio and task.get('local_asr_mode')!='segment' and not task.get('segmentation') and task.get('inspection_policy') not in {'lite_live_realtime_v1','lite_live_realtime_v2'}:
                        try:
                            self.start_local()
                            count=min(32000,available-self.offset)
                            response=self.bridge.request('stream-read',bytes=count,timeout=max(.001,live_backlog.remaining(task,5)),cancel=MediaCancellation(self.store,self.cancel))
                            self.offset+=response['bytes_read']
                            self.store.update_progress(asr_consumed_ms=self.base+self.offset//32)
                            if self.stopped():break
                            for unit in response['finals']:self.publish(unit,'local')
                            partial=response.get('partial','')
                            if partial!=self.last_partial and time.monotonic()-self.partial_at>=.5:
                                self.store.update_progress(live_subtitle={'text':partial,'final':False,
                                    'start_ms':response['start_ms'],'end_ms':response['end_ms']})
                                self.partial_at=time.monotonic();self.last_partial=partial
                        except (ASRError,OSError) as error:
                            code=getattr(error,'code','ASR_PROCESS_EXITED')
                            if self.bridge:self.bridge.close()
                            self.bridge=None;self.stream_open=False
                            self.offset=(self.committed-self.base)*32
                            if code in RETRYABLE and self.restarts<1:
                                self.restarts+=1;continue
                            if self.stopped():break
                            end=min(available,self.offset+640000)
                            self.publish({'start_ms':self.committed,'end_ms':self.base+end//32,'error':code},'local')
                            self.offset=end
                    else:
                        # Fixed WAV batches are independent of video keyframes.
                        # EOF also publishes the short tail; ASR runs in the worker pool.
                        step=(min(60,task.get('segment_seconds',30)) if self.has_audio else 10)*32000
                        if available-self.offset<step and not self.done.is_set():
                            self.done.wait(.05);continue
                        end=min(available,self.offset+step)
                        self.publish({'start_ms':self.base+self.offset//32,'end_ms':self.base+(end+31)//32,
                                      'pcm_byte_start':self.offset, 'pcm_byte_end':end, 'cut_reason':'fixed',
                                      'asr_pending':backend=='local' and self.has_audio},backend)
                        self.offset=end
                        self.store.update_progress(asr_consumed_ms=self.base+self.offset//32)
                elif self.done.is_set():
                    break
                else:self.done.wait(.05)
            if self.stream_open and self.bridge and not self.stopped():
                for unit in self.bridge.request('stream-finish',timeout=max(.001,live_backlog.remaining(self.store.task(),5)),cancel=MediaCancellation(self.store,self.cancel))['finals']:self.publish(unit,'local')
                self.stream_open=False
            if self.done.is_set() and not self.stopped():
                images=list(self.frames.glob('*.jpg'))
                visual_end=self.base+(max((int(p.stem) for p in images),default=-1)+1)*FRAME_PERIOD_MS
                if self.sampled and not self.has_audio:visual_end=self.base+self.media_available_ms()
                task=self.store.task()
                if task.get('kind')=='video':visual_end=min(visual_end,task.get('source_duration_ms',visual_end))
                if visual_end>self.committed:
                    self.audio_gap=self.has_audio
                    while self.committed<visual_end:
                        self.publish({'start_ms':self.committed,'end_ms':min(self.committed+10000,visual_end)},'local')
            task=self.store.task()
            if live_backlog.enabled(task) and self.has_audio and task.get('finishing',{}).get('phase')!='completed':
                if live_backlog.remaining(task,1)<=0:
                    self.skip_audio(self.base+self.available()//32,live_backlog.FINISH)
            self.store.update_progress(live_subtitle=None)
        except Exception as error:
            from runtime.diagnostics import failure_details
            self.diagnostic=failure_details(error)
            self.error='STREAM_PROCESSING_FAILED'

    def join(self):
        from runtime.diagnostics import cleanup_actions
        primary = None
        try:
            if self.reader:self.reader.join(timeout=5)
            if self.consumer:
                while self.consumer.is_alive():
                    self.consumer.join(.2)
                    if self.stopped():break
        except BaseException as error:
            primary = error
            # A failed DB stop check must not strand the consumer or ASR child.
            # Cancel only this consumer; setting the shared worker event would
            # misclassify a storage failure as a user-requested stop.
            self.cancel=threading.Event()
            self.cancel.set()
        finally:
            bridge, self.bridge = self.bridge, None
            actions = [('cleanup_asr_bridge', bridge.close)] if bridge else []
            if self.consumer:
                actions.append(('cleanup_pcm_consumer', lambda: self.consumer.join(timeout=5)))
            primary = cleanup_actions(actions, primary)
        if primary is not None:raise primary


def recording_segments(store):
    from runtime.media import closed_segments
    import json
    result=[]
    for path in sorted((store.root/'media').glob('session-*.json')):
        session=json.loads(path.read_text())
        for index,start,end,media in closed_segments(store,session):
            result.append({'id':index,'index':index,'start_ms':start,'end_ms':end,'media_file':media})
    return sorted(result,key=lambda s:s['start_ms'])


def recover_spools(store,cancel):
    """Replay only the uncommitted PCM tail; successful units remain immutable."""
    import json
    sessions=[]
    for path in sorted((store.root/'audio').glob('capture-*.pcm')):
        index=int(path.stem.split('-')[-1])
        session_path=store.root/'media'/f'session-{index:06d}.json'
        if session_path.exists():sessions.append((path,index,json.loads(session_path.read_text())))
    latest=max([live_backlog.captured_end(store.task())]+[s['base_ms']+p.stat().st_size//32 for p,_,s in sessions])
    for path,index,session in sessions:
        if cancel is not None and cancel.is_set():break
        if store.finish_tick().get('phase')=='completed':break
        stream=CaptureStream(store,session,index,cancel=cancel)
        if stream.offset>=path.stat().st_size:continue
        end=session['base_ms']+path.stat().st_size//32
        if live_backlog.enabled(store.task()) and latest-end>live_backlog.MAX_BACKLOG_MS:
            stream.skip_audio(end,live_backlog.BACKLOG)
            continue
        stream.done.set()
        stream.consume()
        stream.join()
