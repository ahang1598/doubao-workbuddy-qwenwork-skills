"""Direct capture adapter; closed files reuse the existing evidence queue."""
import json
from pathlib import Path
import os
import queue
import subprocess
import sys
import threading
import time

from runtime.flv import Slicer, Unsupported
from runtime.store import atomic_json

MAX_PENDING_BYTES = 256 * 1024 * 1024
MAX_PENDING_MS = 180000
MAX_RECORDING_BYTES = 2 * 1024 * 1024 * 1024
CAPTURE_STATE_POLL_SECONDS = 0.25


def enabled(task):
    return task.get('capture_route') == 'flv'


def recover(store, journals=None):
    if store.task().get('media_frozen'):return
    for path in journals if journals is not None else sorted((store.root/'media').glob('flv-*.json')):
        row = json.loads(path.read_text(encoding='utf-8'))
        if not store.local_path(row['media_file']).is_file():continue
        store.add_segment(row['index'], row['start_ms'], row['end_ms'], row['media_file'], evidence={
            'analysis_unit':'cloud_window', 'evidence_ready_at':row['closed_at'],
            'audio_file':row['media_file'], 'media_container':'flv', 'media_bytes':row['bytes'],
            'asr_status':'pending' if row['has_audio'] else 'no_audio',
            'asr_backend':'mediakit'})


def recordings(store):
    result=[]
    for path in sorted((store.root/'media').glob('flv-*.json')):
        row=json.loads(path.read_text(encoding='utf-8'))
        if store.local_path(row['media_file']).is_file():
            result.append({**row,'id':row['index']})
    return result


def session(store, source, base, index, cancel):
    from runtime.media import stop_requested, capture_errors
    from runtime.platform_support import media_popen, kill_tree, process_options
    def publish(number, start, end, path, audio, size):
        row=dict(index=number,start_ms=start,end_ms=end,media_file=str(path.relative_to(store.root)),
                 has_audio=audio,bytes=size,closed_at=time.time())
        journal=store.root/'media'/f'flv-{number:06d}.json'
        atomic_json(journal,row)
        recover(store,[journal])
        from runtime.realtime import recording_segments
        store.update_task(capture_spans=[{'start_ms':s['start_ms'],'end_ms':s['end_ms']}
                                         for s in recording_segments(store)])
        pending=[s for s in store.segments() if s.get('media_container')=='flv'
                 and s.get('review_status')!='skipped' and not s.get('asr_final') and s['asr_status'] not in {'success','failed','no_audio'}]
        # Bound queued upload data. Stop acquisition with an explicit gap instead of
        # deleting a file still owned by an in-flight command or silently dropping it.
        if (sum(s.get('media_bytes',0) for s in pending)>MAX_PENDING_BYTES or
                sum(s['end_ms']-s['start_ms'] for s in pending)>MAX_PENDING_MS or
                sum(s['bytes'] for s in recordings(store))>MAX_RECORDING_BYTES):
            store.update_task(capture_route_reason='queue_limit')
            raise RuntimeError('FLV_QUEUE_LIMIT')
    slicer=Slicer(store.root/'media',index,base,store.task().get('segment_seconds',30),publish)
    with capture_errors(store.root/'media'/f'flv-{index:06d}.stderr') as errors:
        process=media_popen([sys.executable,'-m','runtime.flv_capture'],cwd=Path(__file__).resolve().parents[1],stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,stderr=errors if errors is not None else subprocess.DEVNULL, capture_child=True, **process_options())
        chunks=queue.Queue(maxsize=2);done=threading.Event()
        def read():
            try:
                while not done.is_set():
                    chunk=process.stdout.read1(65536)
                    while not done.is_set():
                        try:chunks.put(chunk,timeout=.1);break
                        except queue.Full:pass
                    if not chunk:return
            except (OSError,ValueError):pass
        try:
            process.stdin.write(json.dumps({'url':source}).encode()+b'\n');process.stdin.flush()
            reader=threading.Thread(target=read,daemon=True);reader.start()
            started=last=time.monotonic();progress_at=0;timed_out=False
            received_bytes=0
            next_state_check = started
            while cancel is None or not cancel.is_set():
                now = time.monotonic()
                if now >= next_state_check:
                    if store.should_stop() or store.task().get('live_ended_at'):
                        break
                    next_state_check = now + CAPTURE_STATE_POLL_SECONDS
                try:chunk=chunks.get(timeout=.1)
                except queue.Empty:
                    if time.monotonic()-last>15:
                        timed_out=True
                        break
                    continue
                if not chunk:
                    process.wait(timeout=5)
                    break
                received_bytes+=len(chunk)
                slicer.feed(chunk);last=time.monotonic()
                if slicer.start is None and last-slicer.started_at>45:
                    raise Unsupported('keyframe_timeout')
                if slicer.latest is not None and last-progress_at>=1:
                    store.update_progress(capture_reconnecting=False, capture_last_input_at=time.time(),capture_observed_ms=
                                      base+max(0,(slicer.last or 0)-(slicer.origin or 0)))
                    progress_at=last
            ended=time.monotonic()
            slicer.close()
        except Unsupported:
            slicer.close()
            raise
        finally:
            done.set();slicer.abort()
            kill_tree(process);code=process.wait(timeout=5)
            process.stdin.close();process.stdout.close()
            if 'reader' in locals():reader.join(timeout=1)

        failure={}
        transport={}
        if not stop_requested(store,cancel) and not store.task().get('live_ended_at'):
            from runtime.http_fetch import safe_failure
            from runtime.capture_diagnostics import record_attempt
            if errors is not None:
                try:
                    errors.seek(0)
                    record=json.loads(errors.read(1024))
                    if isinstance(record,dict):
                        failure=safe_failure(record)
                        transport=record
                except (ValueError, UnicodeError):pass
                except OSError as error:
                    from runtime.diagnostics import log_failure
                    log_failure(error,stage='capture_diagnostic_read')
            category={'dns_error':'connection_error','invalid_response':'invalid_media'}.get(
                failure.get('kind'),failure.get('kind'))
            detail={'category':'network_timeout' if timed_out else ('process_exit' if category in {None,'unknown'} else category),'exit_code':code}
            if 'http_status' in failure:detail['http_status']=failure['http_status']
            record_attempt(store,detail)
            reason=transport.get('read_end')
            if reason not in ('body_eof','short_body','incomplete_read','connection_reset'):
                reason=failure.get('kind') or 'process_exit'
            if timed_out:reason='parent_idle_timeout'
            event=dict(route='flv',reason=reason,exit_code=code,start_index=index,
                       start_ms=base,received_bytes=received_bytes,elapsed_ms=round((ended-started)*1000),
                       last_byte_age_ms=round((ended-last)*1000) if received_bytes else None)
            if transport.get('stage') in ('dns','connect','body','output'):event['stage']=transport['stage']
            status=transport.get('http_status')
            if type(status) is int and 100<=status<=599:event['http_status']=status
            from runtime.diagnostics import log_failure
            try:store.log('capture_transport_end',json.dumps(event))
            except Exception as error:log_failure(error,stage='capture_diagnostic_log')
        return code, failure.get('http_status')==404


def fetch(observation=None):
    """Isolated streaming transport: host proxy support with public media destinations on every hop."""
    import socket
    observation={} if observation is None else observation
    from urllib.request import build_opener, Request, HTTPSHandler, ProxyHandler, getproxies, proxy_bypass
    from urllib.error import HTTPError
    from urllib.parse import urlsplit, urljoin
    from runtime.http_fetch import _NoRedirect, _https_context
    from runtime.media_network import resolve_addresses
    proxies={key:value for key,value in getproxies().items() if key in {'http','https','no'}}
    active_proxy=None
    original=socket.getaddrinfo
    def public_dns(host,*args,**kwargs):
        return resolve_addresses(host,*args,resolver=original,**kwargs)
    def connection_dns(host,port,*args,**kwargs):
        # Exempt only the proxy selected for this hop, never bypassed or unused proxies.
        resolver=original if (host.lower(),port)==active_proxy else public_dns
        return resolver(host,port,*args,**kwargs)
    socket.getaddrinfo=connection_dns
    request=json.loads(sys.stdin.buffer.readline(65537))
    url=request['url']
    # Parent death/stop closes stdin even while DNS or the socket is blocked.
    def parent_watch():
        os.read(sys.stdin.fileno(),1)
        os._exit(0)
    threading.Thread(target=parent_watch,daemon=True).start()
    opener=build_opener(ProxyHandler(proxies),_NoRedirect(),HTTPSHandler(context=_https_context()))
    for _ in range(6):
        target=urlsplit(url)
        if (len(url)>8192 or target.scheme not in {'http','https'} or not target.hostname
                or target.username or target.password or target.port not in {None,80,443}):
            raise ValueError('invalid_address')
        observation['stage']='dns'
        public_dns(target.hostname,target.port or (443 if target.scheme=='https' else 80),type=socket.SOCK_STREAM)
        active_proxy=None
        proxy=proxies.get(target.scheme)
        if proxy and not proxy_bypass(target.netloc):
            endpoint=urlsplit(proxy if '://' in proxy else 'http://'+proxy)
            if endpoint.hostname and endpoint.scheme in {'http','https'}:
                active_proxy=(endpoint.hostname,endpoint.port or (443 if endpoint.scheme=='https' else 80))
        observation['stage']='connect'
        try:response=opener.open(Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=10)
        except HTTPError as error:response=error
        with response:
            if response.status in {301,302,303,307,308}:
                location=response.headers.get('Location','')
                if not location or len(location)>8192:raise ValueError('invalid_redirect')
                url=urljoin(url,location);continue
            if response.status!=200:raise HTTPError(url,response.status,'',None,None)
            observation['http_status']=response.status
            while True:
                observation['stage']='body'
                data=response.read1(65536)
                if not data:
                    observation['read_end']='short_body' if response.length else 'body_eof'
                    return
                observation['stage']='output'
                sys.stdout.buffer.write(data);sys.stdout.buffer.flush()
    raise ValueError('redirect_limit')


def main():
    from urllib.error import HTTPError
    from runtime.http_fetch import failure_kind, safe_failure
    from http.client import IncompleteRead
    observation={}
    try:fetch(observation)
    except Exception as error:
        failure=({'kind':'http_error','http_status':error.code} if isinstance(error,HTTPError)
                 else {'kind':failure_kind(error)})
        if isinstance(error,IncompleteRead):observation['read_end']='incomplete_read'
        if isinstance(error,ConnectionResetError):observation['read_end']='connection_reset'
        sys.stderr.write(json.dumps({**observation,**safe_failure(failure)}))
        return 1
    sys.stderr.write(json.dumps(observation))
    return 0


if __name__=='__main__':
    sys.exit(main())
