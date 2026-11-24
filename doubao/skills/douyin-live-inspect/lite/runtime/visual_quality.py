"""Bounded original-video sampling, independent of ASR and compliance judgments."""
import json
import math
import statistics
import subprocess
import time

VERSION = 1
WIDTH, HEIGHT, LIMIT = 320, 180, 60
SCOPE = ('原始视频每秒采样，单个源片段最多60秒；只反映已解码采样点。'
         '黑暗、过亮、细节不足和静止均为技术线索，不能证明违规、网络卡顿或经营损失；'
         '纯色背景、静态海报与正常转场须回看确认。未检测或失败不等于画质正常。')
ADVICE = {
    'black': ('采样画面接近全黑', '回看对应原片，检查镜头遮挡、场景切换和视频源。'),
    'dark': ('采样画面大面积偏暗', '确认商品是否看清，再调整补光或曝光。'),
    'bright': ('采样画面大面积过亮', '确认商品细节是否丢失，再降低曝光或调整灯光。'),
    'detail': ('疑似细节不足', '回看商品细节，区分失焦、压缩与原本平坦的背景。'),
    'static': ('连续采样画面近似静止', '回看是否本来就是海报或静物，确认异常后检查视频源。'),
}


def initialize(conn):
    conn.execute('CREATE TABLE IF NOT EXISTS visual_quality_checks '
                 '(session_id TEXT, source TEXT, data TEXT NOT NULL, PRIMARY KEY(session_id,source))')


def measures(frame):
    if len(frame) != WIDTH * HEIGHT:
        raise ValueError('incomplete quality frame')
    counts = [frame.count(i) for i in range(256)]
    n = len(frame)
    mean = sum(i*c for i,c in enumerate(counts))/n
    spread = math.sqrt(sum((i-mean)**2*c for i,c in enumerate(counts))/n)
    # Fixed analysis resolution; this is a detail indicator, not a calibrated blur score.
    edges = [abs(4*frame[i]-frame[i-1]-frame[i+1]-frame[i-WIDTH]-frame[i+WIDTH])
             for y in range(1, HEIGHT-1, 2) for x in range(1, WIDTH-1, 2)
             for i in [y*WIDTH+x]]
    return {'mean':round(mean,2), 'spread':round(spread,2),
            'dark_fraction':round(sum(counts[:24])/n,4),
            'black_fraction':round(sum(counts[:12])/n,4),
            'bright_fraction':round(sum(counts[240:])/n,4),
            'detail':round(sum(edges)/len(edges),2)}


def analyze(raw, start_ms, end_ms):
    size = WIDTH * HEIGHT
    if not raw or len(raw) % size:
        raise ValueError('missing quality frames')
    rows, previous, still = [], None, 0
    for index in range(min(len(raw)//size, LIMIT)):
        at = start_ms + index*1000
        if at >= end_ms:break
        frame = raw[index*size:(index+1)*size]
        metric = measures(frame)
        flags = []
        if metric['black_fraction'] >= .98:flags.append('black')
        elif metric['dark_fraction'] >= .9:flags.append('dark')
        if metric['bright_fraction'] >= .9:flags.append('bright')
        if not flags and metric['spread'] >= 8 and metric['detail'] < 1.5:flags.append('detail')
        delta = (sum(abs(a-b) for a,b in zip(frame,previous))/size) if previous is not None else None
        still = still+1 if delta is not None and delta < .2 else 0
        if still >= 5:flags.append('static')
        rows.append({'time_ms':at, 'metrics':metric, 'flags':flags})
        previous = frame
    if not rows:raise ValueError('missing quality frames')
    # Single-frame transitions are not reported as sustained problems.
    events = []
    for kind, (label, advice) in ADVICE.items():
        group = []
        for row in rows + [{'flags':[]}]:
            if kind in row['flags']:
                group.append(row)
            elif group:
                if len(group) >= (1 if kind == 'static' else 3):
                    events.append({'kind':kind, 'label':label, 'advice':advice,
                                   'start_ms':group[0]['time_ms']-(5000 if kind == 'static' else 0),
                                   'end_ms':min(end_ms,group[-1]['time_ms']+1000),
                                   'sample_count':len(group)+(5 if kind == 'static' else 0),
                                   'status':'candidate'})
                group = []
    return {'status':'sampled', 'samples':rows, 'events':events,
            'sampled_end_ms':min(end_ms,rows[-1]['time_ms']+1000)}


def decode(store, row, cancel):
    from runtime.mediakit import config
    from runtime.platform_support import media_popen, process_options, kill_tree
    path = store.local_path(row['media_file'])
    # Only closed original recording/video paths are supplied, never audio/asr-*.flv.
    command = [config(store.task(),'ffmpeg_bin','ffmpeg'), '-nostdin', '-v','error', '-threads','1', '-filter_threads','1',
               '-i',str(path), '-an', '-vf',f'setpts=PTS-STARTPTS,fps=1:start_time=0,scale={WIDTH}:{HEIGHT},format=gray',
               '-frames:v',str(LIMIT), '-f','rawvideo','pipe:1']
    with media_popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                     stderr=subprocess.DEVNULL, **process_options()) as process:
        started = time.monotonic()
        while True:
            if cancel.is_set() or time.monotonic()-started > 15:
                kill_tree(process);process.communicate()
                raise TimeoutError('quality decoding stopped')
            try:
                raw, _ = process.communicate(timeout=.2)
                if process.returncode:raise ValueError('quality decoding failed')
                return analyze(raw,row['start_ms'],row['end_ms'])
            except subprocess.TimeoutExpired:
                continue


def sources(store):
    from runtime.realtime import recording_segments
    # Full-live speech segments can be WAVs; use the original closed recordings.
    recordings = recording_segments(store)
    if recordings:return recordings
    return [s for s in store.segments() if s.get('media_file') and
            not s.get('full_live') and str(s['media_file']).lower().endswith(('.mp4','.flv','.mkv','.mov','.webm','.ts'))]


def stream_metrics(info):
    def number(value):
        try:
            result = float(value)
            return result if math.isfinite(result) and result > 0 else None
        except (TypeError, ValueError):
            return None
    video = next((s for s in info.get('streams', []) if s.get('codec_type') == 'video'), {})
    if not video:
        return {'status':'unavailable', 'reason':'no_video_stream'}
    fps, fps_basis = None, None
    for key in ('avg_frame_rate', 'r_frame_rate'):
        parts = str(video.get(key, '')).split('/')
        numerator, denominator = number(parts[0]), number(parts[1]) if len(parts) == 2 else 1
        if numerator and denominator:
            fps, fps_basis = round(numerator / denominator, 3), key
            break
    packets = []
    for packet in info.get('packets', []):
        try:
            at = float(packet['pts_time'])
        except (KeyError, TypeError, ValueError):
            continue
        size = number(packet.get('size'))
        if math.isfinite(at) and size:
            packets.append((at, size, number(packet.get('duration_time'))))
    packets.sort()
    intervals = [b[0]-a[0] for a,b in zip(packets, packets[1:]) if b[0] > a[0]]
    duration = packets[-1][0]-packets[0][0] + (packets[-1][2] or statistics.median(intervals)) if intervals else None
    bitrate = round(sum(p[1] for p in packets)*8/duration) if duration else number(video.get('bit_rate'))
    return {'status':'available', 'width':number(video.get('width')), 'height':number(video.get('height')),
            'fps':fps, 'fps_basis':fps_basis, 'video_bitrate_bps':bitrate,
            'bitrate_basis':'sampled_video_packets' if duration else 'stream_metadata' if bitrate else None,
            'sample_seconds':round(duration,3) if duration else None}


def inspect_stream(store, row):
    from runtime.media import media_command
    from runtime.mediakit import config
    try:
        result = media_command([config(store.task(),'ffprobe_bin','ffprobe'), '-v','error',
            '-select_streams','v:0', '-read_intervals','%+15', '-show_packets',
            '-show_entries','stream=codec_type,width,height,avg_frame_rate,r_frame_rate,bit_rate:packet=pts_time,duration_time,size',
            '-of','json',str(store.local_path(row['media_file']))],capture_output=True,text=True,timeout=5)
        if result.returncode:
            return {'status':'unavailable','reason':'probe_failed'}
        return stream_metrics(json.loads(result.stdout))
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
        return {'status':'unavailable','reason':'probe_unavailable'}


def prepare_one(store, cancel):
    rows = sources(store)
    with store.connection(True) as conn:
        initialize(conn)
        saved = {r[0]:json.loads(r[1]) for r in conn.execute(
            'SELECT source,data FROM visual_quality_checks WHERE session_id=?',(store.session_id,))}
    row = next((r for r in rows if r['media_file'] not in saved),None)
    if row is None:return False
    try:
        result = decode(store,row,cancel)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        reason = 'decoder_missing' if isinstance(error,FileNotFoundError) else 'decode_timeout' if isinstance(error,TimeoutError) else 'decode_failed'
        result = {'status':'unavailable', 'samples':[], 'events':[], 'reason':reason}
    if cancel.is_set():return False
    result['stream'] = inspect_stream(store, row)
    if cancel.is_set():return False
    data = {**result,'version':VERSION,'start_ms':row['start_ms'],'end_ms':row['end_ms']}
    with store.connection(True) as conn:
        conn.execute('INSERT OR IGNORE INTO visual_quality_checks VALUES(?,?,?)',
                     (store.session_id,row['media_file'],json.dumps(data,ensure_ascii=False)))
    return True


def run(store, done, cancel):
    if store.task().get('visual_quality_version') != VERSION:return
    from runtime.media_fallback import ensure
    try:
        store.update_task(visual_quality_state='preparing')
        if not ensure(store,cancel,'visual_quality'):
            store.update_task(visual_quality_state='unavailable')
            return
        store.update_task(visual_quality_state='running')
        while not done.is_set() and not cancel.is_set() and not store.task().get('media_frozen'):
            if not prepare_one(store,cancel):done.wait(1)
        store.update_task(visual_quality_state='stopped')
    except Exception:
        # Quality is supplementary; no ASR state, retry or lifecycle changes.
        try:store.update_task(visual_quality_state='unavailable')
        except Exception:pass
        return


def context(conn, task, segments):
    if task.get('visual_quality_version') != VERSION:return None
    exists = conn.execute("SELECT 1 FROM sqlite_master WHERE name='visual_quality_checks'").fetchone()
    checks = [json.loads(r[0]) for r in conn.execute(
        'SELECT data FROM visual_quality_checks WHERE session_id=?',(task['session_id'],))] if exists else []
    checks.sort(key=lambda r:r['start_ms'])
    events = [e for r in checks for e in r['events']]
    streams = [r['stream'] for r in checks if r.get('stream', {}).get('status') == 'available']
    fps = [s['fps'] for s in streams if s.get('fps')]
    rates = [s['video_bitrate_bps'] for s in streams if s.get('video_bitrate_bps')]
    stream_quality = {'resolutions':sorted({f"{int(s['width'])}×{int(s['height'])}" for s in streams if s.get('width') and s.get('height')}),
        'fps_min':min(fps) if fps else None, 'fps_max':max(fps) if fps else None,
        'video_bitrate_min':min(rates) if rates else None, 'video_bitrate_max':max(rates) if rates else None,
        'observed_sources':len(streams), 'unavailable_sources':len(checks)-len(streams)}
    return {'version':VERSION, 'scope':SCOPE, 'state':task.get('visual_quality_state','not_started'),
            'stream_quality':stream_quality,
            'sample_count':sum(len(r['samples']) for r in checks),
            'checked_sources':sum(r['status']=='sampled' for r in checks),
            'unavailable_sources':sum(r['status']=='unavailable' for r in checks),
            'sampled_ranges':[{'start_ms':r['start_ms'],'end_ms':r['sampled_end_ms']} for r in checks if r['status']=='sampled'],
            'observed_end_ms':max((s['end_ms'] for s in segments),default=0),
            'events':events[:80], 'omitted_events':max(0,len(events)-80)}
