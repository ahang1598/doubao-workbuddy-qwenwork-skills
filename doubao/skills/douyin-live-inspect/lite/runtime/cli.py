"""Small content-only entrypoint; media workers never perform model judgment."""
import argparse
import sqlite3
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlsplit
from runtime.store import Store, encode, upgrade_guidance
from runtime.review_errors import review_error
from runtime.platform_support import process_options
from runtime.delivery_notice import attach_notice, acknowledge, is_doubao_cloud, effective_delivery_mode
from runtime.recap_submission import RecapInputError, read_submission

ROOT=Path(__file__).resolve().parents[1]
ENTRY=ROOT/'scripts/live_inspect.py'
DELIVERY_MODES={'local_dashboard','html_snapshot','chat'}


def dashboard_delivery(url, *, resumed=False):
    if not url:
        return {'required': True, 'type': 'artifact_error',
                'message': '质检任务已保留，工作台生成失败，请在原任务重试导出。'}
    return {
        'required': True,
        'type': 'dashboard_url',
        'url': url,
        'message': ('已请求恢复质检，正在准备。' if resumed else '质检任务已创建，正在准备。') +
                   '[打开实时质检工作台](<' + url + '>)。页面每 2 秒读取最新质检数据，不启动 HTTP 服务；请打开任务目录中的原文件，保留同目录 data.js。',
        'must_deliver_before': ['status', 'review-next'],
    }


def chat_delivery(*, resumed=False):
    state='已请求恢复，正在准备' if resumed else '任务已创建，正在准备'
    return {
        'required': True,
        'type': 'chat',
        'message': (f'质检{state}。当前采用云端 Chat 交付：Lite 将直接在本次对话中持续提供质检进度、'
                    '风险和最终结果，不生成仅本机可访问的实时工作台。桌面模式可使用本地实时工作台；'
                    '正式版支持可跨设备访问的远程工作台，以及更丰富灵活的规则和统一报告管理。'),
        'must_deliver_before': ['status', 'review-next'],
        'progress_policy': {
            'cadence_seconds': 60,
            'also_deliver_on': ['risk_detected', 'evidence_gap', 'blocked', 'completed'],
            'omit_unchanged_updates': True,
        },
    }


def video_delivery(*, resumed=False):
    return {
        'required': True,
        'type': 'video_progress',
        'message': ('已请求恢复视频质检，正在准备。' if resumed else '视频质检任务已创建，正在准备。') +
                   '取得媒体后分析语音和画面，完成后将直接交付视频质检报告。',
        'must_deliver_before': ['status', 'review-next'],
        'progress_policy': {'cadence_seconds': 60, 'omit_unchanged_updates': True,
                            'also_deliver_on': ['evidence_gap', 'blocked', 'completed']},
    }


def task_delivery_mode(store):
    return effective_delivery_mode(store.task().get('delivery_mode','local_dashboard'))


def chat_report(store,status,report=None):
    from runtime.sampling import report_store
    store=report_store(store)
    from runtime.ui import build_report
    report=build_report(store) if report is None else report
    rules=[];hits=[]
    for rule in report['rules']:
        rule_status='hit' if rule.get('status')==2 else 'no_hit' if rule.get('status')==1 else 'inconclusive'
        rules.append({'rule_id':rule['id'],'rule_name':rule['name'],'status':rule_status,
                      'result':rule['result'],'counts':rule['counts'],'judgments':rule['judgments'],
                      'assessment':rule['assessment'],'coverage_summary':rule['coverage_summary']})
        if rule.get('status')!=2:continue
        events=[{'start_seconds':item['start'],'end_seconds':item['end'],'kind':item['kind'],
                 'text':item.get('text',''),'reason':item.get('reason',''),'frame_ids':item.get('frame_ids',[])}
                for item in report['evidence'] if item['rule_id']==rule['id']]
        hits.append({'rule_id':rule['id'],'rule_name':rule['name'],'events':events})
    result = {
        **({'sampling':report['sampling']} if 'sampling' in report else {}),
        'duration_seconds': report['duration_seconds'],
        'segment_count': status['segment_count'],
        'reviewed_segment_count': report['coverage']['reviewed'],
        'skipped_segment_count': report['coverage'].get('skipped',0),
        'hit_rule_count': report['hit_rule_count'],
        'rules': rules,
        'hit_rules': hits,
        'rule_conclusions': report['rule_conclusions'],
        'evidence_gaps': status['evidence_gaps'],
        'coverage': report['coverage'] if report.get('report_kind')=='video' else status['coverage'],
        'conclusion': report['conclusion'],
        'hit_event_count':report['hit_event_count'], 'hit_count_basis':report['hit_count_basis'],
        'asr_sources': [{'segment_id':s['id'],'backend':s.get('asr_backend') or store.task().get('asr_backend','mediakit'),
                         'local_failure':s.get('local_failure'),'status':s['asr_status']} for s in store.segments()],
    }

    if store.task().get('kind','live')=='live':
        from runtime.report_delivery import public_live_report
        result=public_live_report(result)
    return result


def record_rule_load_gap(store, value, code=None):
    from runtime.rules import ALIASES
    bundle=ALIASES.get(value.get('bundle'),value.get('bundle')) if isinstance(value,dict) else None
    if bundle not in {'finance','ecommerce'}:return
    with store.connection(True) as conn:
        task=store._task(conn)
        if task.get('finishing',{}).get('phase')=='completed':return
        gaps=task.setdefault('rule_load_gaps',{})
        if code and bundle not in task.get('loaded_rule_bundles',[]):gaps[bundle]=code
        else:gaps.pop(bundle,None)
        store._set_task(conn,task)


def read_input():
    text=sys.stdin.read(2*1024*1024+1)
    if len(text.encode())>2*1024*1024:raise ValueError('input exceeds 2 MiB')
    value=json.loads(text)
    if not isinstance(value,dict):raise ValueError('JSON object required')
    return value


def read_review_input():
    try:return read_input()
    except (ValueError, TypeError):
        from runtime.review_errors import ReviewError
        raise ReviewError('REVIEW_JSON_INVALID','payload','通过 JSON 序列化提交一个合法对象，不回显原始输入。') from None


def validate_source(value):
    if not isinstance(value,str) or any(ord(c)<32 for c in value):raise ValueError('invalid source')
    u=urlsplit(value)
    if u.scheme not in ('http','https') or not u.hostname or u.username or u.password:raise ValueError('HTTP(S) live source required, without embedded credentials')
    return value


def launch(command,store):
    from runtime.credentials import background_env
    with open(store.root/f'{command}.log','ab') as log:
        proc=subprocess.Popen([sys.executable,str(ENTRY),command,'--task-dir',str(store.root)],
                              stdin=subprocess.DEVNULL,stdout=log,stderr=log,**process_options(),
                              env=background_env())
    return proc


def ensure_static(store):
    from runtime.static_delivery import safe_export
    result = safe_export(store)
    paths = {a['type']:Path(a['path']).as_uri() for a in result['artifacts']}
    return paths.get('monitor'), paths.get('quality')


def ensure_watcher(store):
    from runtime.platform_support import file_lock
    try:
        with file_lock(store.root/'.html-watch.lock', timeout=0):
            launch('watch', store)
    except (TimeoutError, OSError):
        pass  # Export failure never invalidates a durable inspection operation.


def snapshot_delivery():
    return {'required':True, 'type':'html_snapshot',
            'message':'质检工作台以 HTML 附件交付；此文件保留生成时的快照。云电脑运行期间每2分钟交付一次最新快照，发现新增风险和采集结束时也会立即交付新版本。',
            'must_deliver_before':['status','review-next']}


def start(args, value=None, *, kind="live", notice_batch=None):
    from runtime.telemetry_context import startup_stage
    startup_stage('task_create')
    from runtime.task_context import reserve
    folder=Path(args.task_dir).expanduser() if args.task_dir else Path(tempfile.mkdtemp(prefix='live-inspect-lite-'))/'task'
    task_id=reserve(folder)
    args.task_dir=str(folder)
    from runtime.local_asr import doctor, resolve_runtime_root
    from runtime.rules import load_rules
    startup_stage('input_validation')
    is_doubao_cloud()  # Validate explicit host context before creating a task.
    value=read_input() if value is None else value
    allowed={'source','name','scenario','max_duration_seconds','segment_seconds','frame_interval_seconds','delivery_mode','asr_policy','image_inspection'}
    if set(value)-allowed:raise ValueError('unsupported start field')
    image_inspection=value.get('image_inspection',False)
    if type(image_inspection) is not bool:raise ValueError('image_inspection must be boolean')
    policy=value.get('asr_policy','remote_first')
    if policy not in {'remote_first','local_first','local_only'}: raise ValueError('unsupported ASR policy')
    # Validate timing before performing downloads; invalid requests have no setup side effects.
    video_fields={}
    source=value.get('source') if kind=='video' else validate_source(value.get('source'))
    delivery_mode=effective_delivery_mode(value.get('delivery_mode','local_dashboard'))
    scene=value.get('scenario','通用');rules=load_rules(value.get('scenario','common'))
    options={k:value.get(k,d) for k,d in [('max_duration_seconds',None),('segment_seconds',30),('frame_interval_seconds',120 if kind=='live' else 10)]}
    for k,v in options.items():
        if k=='max_duration_seconds' and v is None:continue
        if type(v) is not int or v<=0:raise ValueError('positive integer timing required')
    if options['segment_seconds']>(60 if kind=='live' else 180):raise ValueError('duration exceeds supported limit')
    if kind!='live' and options['frame_interval_seconds']>options['segment_seconds']:raise ValueError('frame interval exceeds segment duration')
    if kind=='live':options['frame_interval_seconds']=120
    from runtime.telemetry_context import publish_metadata
    publish_metadata({'task_id':task_id,'kind':kind,'scenario':scene,'rules_mode':'dynamic' if 'scenario' not in value else 'fixed',
                      'delivery_mode':delivery_mode,'asr_policy':policy,'notice_batch':notice_batch})
    startup_stage('dependency_prepare')
    from runtime.artifacts import prepare
    from runtime.asr_router import cloud_available, initialize_cloud
    from runtime.model_preparation import start_check
    prepared=start_check(defer_model=True)
    binaries=prepared.get('binaries',{})
    if not all(binaries.get(n) for n in ('ffmpeg_bin','ffprobe_bin')):
        startup_stage('dependency_prepare', 'setup_pending')
        publish_metadata()
        return {'status':'setup_pending','doctor':prepared,'task_id':task_id,'task_dir':str(folder)}
    # The worker owns the full 15-second model budget and keeps its warmed process.
    primary,waiting,reason,setup_error,preparation_id='local',True,'preparing_local',None,None
    if policy=='remote_first': primary,reason='mediakit','preparing_remote'
    if kind=='video':
        from runtime.video import inspect_video
        source,video_fields=inspect_video(source,binaries['ffprobe_bin'])
    result={'runtime':prepared.get('runtime')}
    startup_stage('task_create')
    store=Store.create(folder,name=value.get('name') or ('视频内容质检' if kind=='video' else '直播内容质检'),scenario=scene,source=source,rules=rules,
                       delivery_mode=delivery_mode,kind=kind,asr_backend="local",notice_batch=notice_batch,
                       scenario_selection="confirmed", rules_mode="dynamic" if "scenario" not in value else "fixed",
                       loaded_rule_bundles=[],
                       asr_runtime_root=prepared.get('asr_runtime_root'),
                       image_inspection=image_inspection,asr_policy=policy,frames_policy=policy,artifact_specs=prepared.get('artifact_specs',{}),
                       asr_primary_backend=primary,asr_selection_reason=reason,
                       model_preparation_id=preparation_id,model_waiting=waiting,local_setup_error=setup_error,
                       **binaries,
                       asr_runtime=None,pipeline_version=2,local_asr_mode='segment',analysis_mode='full_asr' if kind=='live' else 'sample_window',
                       inspection_policy='lite_live_realtime_v2' if kind=='live' else 'lite_sample_v1',
                       **({'freeze_on_end':True,'review_protocol':'lite_review_v2','review_dispatch_version':2,'review_scope_version':1,'frame_sampling_origin_ms':0,'frame_required':image_inspection and __import__('runtime.full_live',fromlist=['requires_frames']).requires_frames(rules)} if kind=='live' else {}),
                       asr_startup={'status':'preparing','stage':'checking','deadline_at':None,
                                    'message':'正在检查远端处理能力' if policy=='remote_first' else '正在检查本地模型'},**video_fields,**options)
    startup_stage('credential_prepare')
    # Import only existing host authentication; capability discovery runs in the worker.
    if policy in {'remote_first','local_first'}:
        from runtime import credentials
        if all(os.environ.get(k) for k in credentials.ENV_KEYS):
            credentials.refresh(store.workspace_root,initialize=True)
    startup_stage('dashboard_prepare')
    dashboard=report=None
    if kind!='video' and delivery_mode=='local_dashboard':dashboard,report=ensure_static(store)
    startup_stage('worker_launch')
    proc=launch('worker',store)
    startup_stage('watcher_launch')
    ensure_watcher(store)
    delivery=video_delivery() if kind=='video' else dashboard_delivery(dashboard) if delivery_mode=='local_dashboard' else snapshot_delivery() if delivery_mode=='html_snapshot' else chat_delivery()
    delivery['message'] += ' 处理能力准备中，当前尚未采集。'
    if policy=='remote_first': delivery['message'] += ' 默认优先使用云端语音识别，会上传本次音频；开启画面检测时可能上传视频片段，异常时使用本地备用。'
    elif policy=='local_first': delivery['message'] += ' 优先本地识别，异常时可能上传音频或开启画面检测的视频片段使用云端备用。'
    else: delivery['message'] += ' 本次仅使用本地处理，不上传媒体。'
    delivery=attach_notice(store,delivery)
    next_action='deliver-video-progress' if kind=='video' else 'deliver-dashboard-url' if delivery_mode=='local_dashboard' else 'deliver-html-snapshot' if delivery_mode=='html_snapshot' else 'deliver-chat-start-message'
    startup_stage('completed', 'started')
    publish_metadata(store.task())
    return {'task_id':store.task_id,'task_dir':str(store.root),'dashboard_url':dashboard,
            'report_url':report,'worker_pid':proc.pid,'status':'preparing' if waiting else 'starting',
            'asr_primary_backend':primary,'asr_selection_reason':reason,
            'model_preparation':prepared.get('model_preparation',{'status':'ready'}),
            'delivery_mode':delivery_mode,'delivery_required':True,'delivery':delivery,
            'next_action':next_action,'after_delivery_next_action':delivery.get('after_delivery_command','status'),
            'note':'Deliver the returned delivery.message before any status or review command; process startup is not inspection completion'}


def resume_setup(store):
    task=store.task()
    if task.get('inspection_policy')=='lite_live_full_asr_v1':
        store.update_task(optional_frames={},full_asr_cloud_available=None)
    if task.get('pipeline_version')==2 and task.get('asr_startup',{}).get('status')!='selected':
        from runtime.artifacts import prepare
        common=prepare(task=task,common_only=True)
        if common['ready']:store.update_task(worker_status='preparing',setup_error=None)
        return common
    if task.get('asr_primary_backend'):
        from runtime.artifacts import prepare
        from runtime.asr_router import initialize_cloud, cloud_available
        from runtime.model_preparation import start_check
        initialize_cloud(store)
        common=prepare(task=task, common_only=True)
        if not common['ready']: return common
        store.update_task(runtime_binaries=common['binaries'])
        if task.get('asr_policy')=='remote_first':
            # The worker resumes the saved provider; local resources are optional.
            return {'ready':True,'backend':task['asr_primary_backend']}
        if task['asr_primary_backend']=='mediakit':
            return {'ready':True,'backend':'mediakit'}
        if task.get('model_waiting'):
            if task.get('stop_requested'): store.update_task(stop_requested=False)
            check=start_check(task)
            if check['ready']:
                store.bind_prepared_model(check)
            elif check.get('waiting'):
                store.update_task(setup_error=None)
                return {'ready':True,'waiting':True}
            return check
        check=prepare(task=task, install=False)
        if not check['ready'] and task['asr_policy']=='local_first' and cloud_available(store)['ready']:
            return {'ready':True,'backend':'local','fallback_available':True}
        return check
    if task.get('asr_policy') in {'local_first','local_only'}:
        from runtime.artifacts import prepare
        from runtime.asr_router import initialize_cloud, cloud_available
        initialize_cloud(store)
        check=prepare(task=task)
        if check.get('binaries'):
            store.update_task(runtime_binaries=check['binaries'])
        if not check['ready'] and task['asr_policy']=='local_first' and cloud_available(store)['ready']:
            if all(check.get('binaries',{}).get(n) for n in ('ffmpeg_bin','ffprobe_bin')):
                # Never change frozen model identity; router uses the original local setup failure or runtime failure.
                return {'ready':True,'backend':'mediakit'}
        return check
    if task.get('asr_backend')=='local':
        from runtime.local_asr import doctor
        check=doctor(task.get('asr_runtime_root'))
        return {**check,'ready':check['ready'] and check['runtime']==task.get('asr_runtime')}
    from runtime.mediakit import sync_credentials
    sync_credentials(store)
    return {'ready':True}



def inspection_continuation(status):
    """Route progress queries without polling a task that cannot advance."""
    task=status['task']
    from runtime.diagnostics import failure_label
    failure = failure_label(task)
    if status.get('report_blocked_reason'):
        return {'next_action':'deliver-inspection-result','delivery_required':True,'workflow_complete':False,
                'message':('未采集到内容，无法生成质检报告和内容复盘。' if status['report_blocked_reason']=='NO_CAPTURED_CONTENT' else '未检测到语音。' if status['report_blocked_reason']=='NO_SPEECH' else '未获得可用语音文字，无法生成质检报告和内容复盘。')+'请交付本次结果，结束轮询；不自动重建任务。'}
    if status['report_ready']:
        recap=status.get('recap') or {}
        if task.get('kind') != 'video' and task.get('review_protocol') == 'lite_review_v2':
            # Availability alone cannot choose which delivery is still missing.
            # The CLI applies completion(store)'s acknowledgement-based route.
            return {'next_action':'report', 'workflow_complete':False,
                    'message':(failure+'，采集已停止；' if failure else '')+
                              '检测已完成，按交付回执继续质检报告和复盘报告；两份实际交付确认前不结束，也不等待用户回复。'}
        complete=task.get('kind')!='video' and recap.get('available') is True
        return {'next_action':'recap-report' if complete else 'report',
                **({'workflow_complete':complete} if task.get('kind')!='video' else {}),
                'message':(failure+'，采集已停止；报告仅包含已采集并处理的内容，不代表直播正常结束。' if failure else '')+
                          ('质检已结束，请停止质检轮询，读取并交付质检报告。' if task.get('kind')=='video' else
                           '质检与复盘已就绪，请核验并交付复盘报告。' if complete else
                           '质检已结束，请停止质检轮询，立即执行 report 并按返回指引生成和交付复盘；不要等待新片段或再次确认。')}
    finish=status.get('finishing',{})
    if finish.get('phase')=='completed':
        return {'next_action':'deliver-inspection-result','delivery_required':True,'message':'质检已结束，未采集到内容，无法生成报告。请交付实际停止或失败状态，结束轮询；不自动重建任务。'}
    if task.get('recovery_state') == 'blocked':
        return {'next_action':'resume','message':'媒体处理自动恢复未成功；请在原任务执行 resume，保留已采集内容并继续判定。'}
    if task.get('recovery_state') == 'worker_unresponsive':
        return {'next_action':'status','message':'媒体 worker 无响应且仍持有独占锁；采集尚未确认停止，等待状态变化后再恢复。'}
    if task.get('kind')=='video':
        if finish.get('waiting_for_frames'):
            return {'next_action':'review-next' if status.get('review_ready_pending') else 'status',
                    'message':'采集已结束，正在补齐画面与语音证据；完成后继续判定并生成报告。'}
        if finish.get('waiting_for_asr'):
            return {'next_action':'review-next' if status.get('review_ready_pending') else 'status',
                    'message':'采集已结束，正在补齐语音识别；完成后继续判定并生成报告。'}
        if finish and finish.get('remaining_seconds',0)==0:
            return {'next_action':'status','message':'收尾时间已到，正在停止采集，不再领取片段。'}
    if finish and finish.get('mode')=='immediate':
        return {'next_action':'status','message':'已停止剩余检测，正在等待采集退出，随后生成部分报告。'}
    worker=task.get('worker_status')
    if task.get('kind')=='video' and not status.get('review_ready_pending') and (status.get('review_deferred') or worker in ('done','failed','stopped')):
        return {'next_action':'report --allow-partial','message':'请交付包含覆盖缺口的部分报告；保留原任务供续办。'}
    if worker=='setup_pending':
        return {'next_action':'resolve-setup',
                'message':'依赖准备受阻，请说明 setup_error；修复依赖后 resume 原任务，不自动循环重试。'}
    if task.get('kind')=='video' and finish and worker in ('done','failed','stopped') and status['segment_count']:
        return {'next_action':'review-next' if status['review_ready_pending'] else 'status'}
    if worker in ('done','failed','stopped'):
        if not status['segment_count']:
            return {'next_action':'deliver-inspection-result','delivery_required':True,
                    'message':'任务已结束，未获得可质检片段，无法生成质检报告。请交付实际停止或失败状态及证据缺口，结束轮询；不自动重建任务。'}
        if status['media_pending']:
            return {'next_action':'resume',
                    'message':(failure+'；' if failure else '')+'已有媒体尚需恢复处理，请 resume 原任务后继续判定，不重新 start。'}
    result={'next_action':'review-next' if status['review_ready_pending'] else 'status'}
    if task.get('review_protocol')=='lite_review_v2':
        result.update(workflow_complete=False,poll_after_seconds=3)
    if finish and task.get('kind','live')=='live':
        from runtime.finishing import message
        result['message']=message(task,finish,status['review_pending'])
    return result


def main(argv=None):
    from runtime import review_execution
    supplied = list(sys.argv[1:] if argv is None else argv)
    if supplied and (supplied[0] in {'review-state', 'review-recover'} or
                     (supplied[0] == 'result-page' and not any(a in ('-h','--help') for a in supplied)) or
                     (supplied[0] in review_execution.COMMANDS and any(a.split('=')[0] == '--request-id' for a in supplied))):
        return review_execution.supervise(supplied)
    from runtime.telemetry_context import publish_metadata, begin_command, record_command_error
    begin_command(supplied[0] if supplied else None)
    parser=argparse.ArgumentParser(description='Live ASR/frame content inspection; no room sync or audience collection')
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('doctor')
    sub.add_parser('prepare-runtime')
    sub.add_parser('review-state', help='Read-only request and batch reconciliation')
    for name in ('start','start-video','worker','serve','watch','snapshot','scene-confirm','review-defer','status','stop','resume','delivery-ack','refresh-credentials','asr-reconcile','review-next','rules-load','review-submit','report','recap-input','recap-submit','recap-report','report-delivery-ack','result-page'):
        p=sub.add_parser(name);p.add_argument('--task-dir',required=name not in ('start','start-video'))
        if name in ('review-next','review-submit'):
            p.add_argument('--request-id', help='Stable identity for one bounded command invocation')
            p.add_argument('--dispatcher-id',default='main')
            if name=='review-next':p.add_argument('--dispatch-input-file')
            p.add_argument('--known-rules-version');p.add_argument('--limit',type=int,default=None,choices=range(1,21),help='1..20 segments per batch for new live tasks')
        if name=='stop':
            p.add_argument('--immediate',action='store_true',help='Stop remaining live detection and deliver partial reports')
            p.add_argument('--confirm-discard',action='store_true',help='User confirmed discarding unfinished inspection')
            p.add_argument('--reason',choices=['user_request'],default='user_request')
            p.add_argument('--user-instruction',help='Explicit user stop instruction; never invent one')
        if name=='result-page':
            p.add_argument('--result-id',required=True)
            p.add_argument('--offset',type=int,default=0)
        if name=='recap-input':
            p.add_argument('--begin',action='store_true')
            p.add_argument('--offset',type=int,help='Read five recap segments starting at this offset')
        if name in ('recap-submit','review-submit','report-delivery-ack'):p.add_argument('--input-file',help='Submit an Agent-authored UTF-8 JSON file; stdin requires EOF within 5 seconds')
        if name in ('report','recap-report'):p.add_argument('--single-file',action='store_true',default=True,help='Standalone HTML with embedded video (default; retained for compatibility)')
        if name=='report':p.add_argument('--allow-partial',action='store_true')
        if name=='review-next':p.add_argument('--include-deferred',action='store_true')
        if name in ('review-submit','rules-load'):p.add_argument('--next',action='store_true',dest='claim_next')
        if name=='rules-load':p.add_argument('--dispatcher-id',default='main')
    for name in ('batch-create','batch-next','batch-status','batch-stop'):
        sub.add_parser(name).add_argument('--batch-dir',required=True)
    try:
        args=parser.parse_args(argv)
    except SystemExit as error:
        if error.code:publish_metadata(error_code='INVALID_INPUT',error_detail='ARGUMENT_PARSE_ERROR' if supplied[:1] in (['start'], ['stop']) else None)
        raise
    store=None
    if args.command=='stop' and not (args.user_instruction or '').strip():
        publish_metadata(error_code='INVALID_INPUT',error_detail='STOP_USER_INSTRUCTION_REQUIRED')
        print(encode({'ok':False,'command':'stop','error':{
            'code':'STOP_USER_INSTRUCTION_REQUIRED','missing_fields':['user_instruction'],
            'retryable':True,'next_action':'stop',
            'command_argv':['stop','--task-dir',args.task_dir,'--reason','user_request',
                            '--user-instruction','<当前用户的真实停止指令>'],
            'message':'使用当前用户已给出的停止原话补齐 --user-instruction 并立即重试；不要再次询问用户，不得编造授权或手工杀进程。'}}))
        return 1
    try:
        if args.command in ('doctor','prepare-runtime'):
            from runtime.model_preparation import inspect, prepare_runtime
            data=prepare_runtime() if args.command=='prepare-runtime' else inspect()
            if args.command=='doctor':
                from runtime.telemetry import capability
                data['telemetry']=capability()[0]
        elif args.command in ('start','start-video'):data=start(args,kind='video' if args.command=='start-video' else 'live')
        elif args.command.startswith('batch-'):
            from runtime.video_batch import dispatch
            data=dispatch(args.command,args.batch_dir,read_input() if args.command=='batch-create' else None)
        elif args.command=='result-page':
            from types import SimpleNamespace
            from runtime.report_delivery import result_page
            data=result_page(SimpleNamespace(root=Path(args.task_dir).expanduser().resolve()),args.result_id,args.offset)
        else:
            if args.command=='stop' and not args.immediate and args.reason=='user_request' and args.user_instruction:
                from runtime.stop_signal import request
                request(args.task_dir,origin='agent',reason=args.reason,instruction=args.user_instruction)
            store=Store(args.task_dir)
            publish_metadata(store.task())
            if args.command=='worker':
                from runtime.media import run_worker
                run_worker(store.root, supervised=True);return 0
            if args.command=='watch':
                from runtime.static_delivery import watch
                watch(store);return 0
            if args.command=='serve':
                data={'status':'retired','message':'本地服务已移除，请使用 snapshot、report 或 recap-report 导出静态 HTML。'}
            elif args.command=='snapshot':
                from runtime.static_delivery import safe_export, attach_snapshot_delivery
                data=safe_export(store,snapshot=True)
                attach_snapshot_delivery(data)
                data['next_action']='deliver-html-snapshot' if data.get('delivery_required') else 'retry-snapshot'
            elif args.command=='status':
                from runtime.recap import recap_report
                data=store.status()
                data['recap']={k:v for k,v in recap_report(store).items() if k in ('status','available','message','needs_resume','terminal_failure')}
            elif args.command=='recap-input':
                from runtime.recap import recap_input, submission_contract
                data=recap_input(store,args.begin)
                data={'next_action':'recap-report' if data['recap']['available'] else
                      'write-recap-result-and-submit' if args.begin else 'recap-input --begin',
                      'submission_contract':submission_contract(store,data),**data}
                if args.offset is not None or len(encode(data).encode()) > 24000:
                    from runtime.report_delivery import evidence_page
                    data=evidence_page(data,store.root,args.offset or 0)
                    data['next_action']=('recap-report' if data['recap']['available'] else
                        'recap-input --begin' if data['recap']['status'] != 'generating' else
                        'read-recap-evidence-pages' if data['next_offset'] is not None else 'write-recap-result-and-submit')
                if data['recap'].get('terminal_failure'):
                    data['next_action']='recap-report'
                    data.pop('submission_contract',None)
                if data['recap']['status']=='blocked':
                    data['next_action']='deliver-inspection-result'
                    data.pop('submission_contract',None)
            elif args.command=='recap-submit':
                from runtime.recap import recap_submit
                data=recap_submit(store,read_submission(args.input_file))
            elif args.command=='recap-report':
                from runtime.recap import recap_report
                from runtime.realtime_policy import current
                data=recap_report(store)
                final_failure = data['status']=='failed' and (data.get('terminal_failure') or not current(store.task()))
                if task_delivery_mode(store)!='chat' and (data['available'] or final_failure):
                    if data['available']:
                        from runtime.media import build_recording
                        build_recording(store)
                    from runtime.static_delivery import safe_export
                    result=safe_export(store,single_file=args.single_file)
                    data.update(result)
                    item=next((a for a in result['artifacts'] if a['type']=='review'),None)
                    data['report_url']=Path(item['path']).as_uri() if item and task_delivery_mode(store)=='local_dashboard' else None
                data.pop('video',None)
                for row in data.get('document',{}).get('content',{}).get('segments',[]):row.pop('frame_images',None)

            elif args.command=='delivery-ack':data=acknowledge(store)
            elif args.command=='stop':
                if args.immediate and store.task().get('review_protocol') == 'lite_review_v2' and not args.confirm_discard:
                    raise ValueError('immediate stop requires user confirmation')
                store.request_stop(immediate=args.immediate,origin='agent',reason=args.reason,user_instruction=args.user_instruction,confirm_discard=args.confirm_discard)
                if store.task().get('media_frozen'):
                    from runtime.static_delivery import safe_export
                    from runtime.platform_support import file_lock
                    try:
                        with file_lock(store.root/'.worker.lock',timeout=0):
                            store.update_task(capture_status='stopped',worker_status='stopped')
                    except TimeoutError:pass
                    safe_export(store)
                status=store.status()
                data={'status':'stop_requested','task_id':store.task_id,**status,**inspection_continuation(status)}
                if store.task().get('kind','live')=='live':
                    from runtime.finishing import message
                    data['message']=message(status['task'],status['finishing'],status['review_pending'])
            elif args.command=='review-next':
                if args.dispatch_input_file:
                    from runtime.review_dispatch import control
                    value=read_submission(args.dispatch_input_file)
                    if value.get('dispatcher_id')!=args.dispatcher_id:raise ValueError('dispatcher binding mismatch')
                    data=control(store,value)
                else:
                    data=store.claim(known_rules_version=args.known_rules_version,limit=args.limit or (20 if store.task().get('inspection_policy')=='lite_live_realtime_v2' else 4 if store.task().get('review_protocol')=='lite_review_v2' else 2 if store.task().get('inspection_policy')=='lite_live_full_asr_v1' else 1),include_deferred=getattr(args,"include_deferred",False),dispatcher_id=args.dispatcher_id)
            elif args.command=='review-defer':data=store.defer(read_review_input())
            elif args.command=='scene-confirm':data=store.confirm_scene(read_input())
            elif args.command=='rules-load':
                from runtime.review_errors import RULE_LOAD_ERRORS, ReviewError
                value=read_input()
                try:
                    data=store.load_rule_bundle(value)
                    record_rule_load_gap(store,value)
                    if args.claim_next:
                        data=store.claim(limit=20 if store.task().get('inspection_policy')=='lite_live_realtime_v2' else 4,dispatcher_id=args.dispatcher_id)
                except ValueError as error:
                    detail=RULE_LOAD_ERRORS.get(str(error))
                    if detail is None:raise
                    code,field,message,action=detail
                    record_rule_load_gap(store,value,code)
                    raise ReviewError(code,field,message,next_action=action,retryable=code!='RULE_SNAPSHOT_FIXED') from error
            elif args.command=='review-submit':
                if store.task().get('review_dispatch_version') == 2:
                    from runtime.review_dispatch import own
                    with store.connection(True) as conn:
                        task=store._task(conn)
                        dispatch=dict(task.get('review_dispatch',{}))
                        own(dispatch,args.dispatcher_id,time.time())
                        task['review_dispatch']=dispatch
                        store._set_task(conn,task)
                from runtime.review_contract import enabled as review_v2_enabled
                from runtime.review_metrics import record_attempt
                if review_v2_enabled(store.task()):
                    record_attempt(store, input_path=review_execution.source_input(args.input_file))
                try:
                    payload=read_review_input() if not store.task().get('inspection_policy') and not args.input_file else read_submission(args.input_file)
                except RecapInputError as error:
                    if review_v2_enabled(store.task()):
                        record_attempt(store, input_path=review_execution.source_input(args.input_file), error={
                            'code':error.code.replace('RECAP_', 'REVIEW_'),
                            **({ 'line':error.line, 'column':error.column } if error.line is not None else {})})
                    raise
                data=store.submit(payload)
                review_execution.phase('submission_returned')
                if review_v2_enabled(store.task()) and data.get('error_count'):
                    data['next_action']='review-submit'
                if args.claim_next and not (review_v2_enabled(store.task()) and data.get('error_count')):
                    # Submission is already durable. A next-claim failure must not look like a failed submission.
                    try:data['next']=store.claim(known_rules_version=args.known_rules_version,limit=args.limit or (20 if store.task().get('inspection_policy')=='lite_live_realtime_v2' else 4 if store.task().get('review_protocol')=='lite_review_v2' else 2 if store.task().get('inspection_policy')=='lite_live_full_asr_v1' else 1),include_deferred=getattr(args,"include_deferred",False),dispatcher_id=args.dispatcher_id,source_context=payload.get('context_id'))
                    except ValueError as error:
                        if str(error) == 'review context superseded':
                            data['next']={'status':'superseded','next_action':'review-state'}
                        else: data['next']={'status':'retry_review_next','next_action':'review-next'}
                    except Exception:data['next']={'status':'retry_review_next','next_action':'review-next'}
            elif args.command=='refresh-credentials':
                from runtime.mediakit import sync_credentials
                data={'status':'not_required','backend':'local'} if store.task().get('asr_backend')=='local' and store.task().get('asr_policy') not in {'remote_first','local_first'} else sync_credentials(store)
            elif args.command=='asr-reconcile':
                from runtime.mediakit import reconcile_submission
                data=reconcile_submission(store,read_input())
            elif args.command=='resume' and store.task().get('media_frozen'):
                ensure_watcher(store)
                status=store.status()
                data={**status,**inspection_continuation(status)}
            elif args.command=='resume' and store.finish_tick() and inspection_continuation(store.status())['next_action']!='resume' and not (
                    store.task().get('stop_requested') and
                    (store.task().get('capture_status') not in {'ended','stopped','failed'} or store.status()['media_pending'])):
                ensure_watcher(store)
                status=store.status()
                data={**status,**inspection_continuation(status),'status':'finishing' if status['finishing']['phase']!='completed' else 'inspection_finished'}
            elif args.command=='resume':
                if store.finish_tick():store.update_task(worker_mode='processing_only')
                from runtime.mediakit import sync_credentials
                check=resume_setup(store)
                if not check['ready']:
                    print(encode({'ok':True,'command':args.command,'data':{'status':'setup_pending','doctor':check}}));return 0
                delivery_mode=task_delivery_mode(store)
                dashboard=report=None
                is_video=store.task().get('kind')=='video'
                if not is_video and delivery_mode=='local_dashboard':dashboard,report=ensure_static(store)
                # Worker has an exclusive lock; concurrent launch cannot duplicate capture or ASR.
                proc=launch('worker',store)
                ensure_watcher(store)
                delivery=video_delivery(resumed=True) if is_video else dashboard_delivery(dashboard,resumed=True) if delivery_mode=='local_dashboard' else snapshot_delivery() if delivery_mode=='html_snapshot' else chat_delivery(resumed=True)
                if store.task().get('model_waiting'):
                    delivery['message']='处理能力准备中，完成后自动开始质检；当前尚未采集，等待期间的直播内容不在覆盖范围内。'
                delivery=attach_notice(store,delivery)
                next_action='deliver-video-progress' if is_video else 'deliver-dashboard-url' if delivery_mode=='local_dashboard' else 'deliver-html-snapshot' if delivery_mode=='html_snapshot' else 'deliver-chat-start-message'
                data={'status':'resume_requested','task_id':store.task_id,'worker_pid':proc.pid,
                      'dashboard_url':dashboard,'report_url':report,'delivery_mode':delivery_mode,
                      'delivery_required':True,'delivery':delivery,
                      'next_action':next_action,'after_delivery_next_action':delivery.get('after_delivery_command','status')}
            elif args.command=='report-delivery-ack':
                if store.task().get('kind')=='video':
                    from runtime.video_report import acknowledge_report
                    data=acknowledge_report(store,read_submission(args.input_file))
                else:
                    from runtime.report_completion import acknowledge as acknowledge_completion
                    data=acknowledge_completion(store,read_submission(args.input_file))
            elif args.command=='report' and store.task().get('kind')=='video':
                from runtime.video_report import video_report
                data=video_report(store,allow_partial=args.allow_partial,mode=task_delivery_mode(store),single_file=args.single_file)
            elif args.command=='report':
                status=store.status()
                if status.get('report_blocked_reason') and store.task().get('review_protocol')=='lite_review_v2':
                    data={'status':'failed','task_id':store.task_id,'code':status['report_blocked_reason'],
                          'message':'检测未完成，无法生成质检报告。','delivery_required':True,
                          'delivery':{'required':True,'type':'chat_report'},
                          'after_delivery_next_action':'recap-report','next_action':'recap-report'}
                elif not status['report_ready']:data={'status':'not_ready',**status,**inspection_continuation(status)}
                else:
                    # Freeze the recap projection before exporting the matching
                    # quality artifact and its evidence-bound delivery receipt.
                    from runtime.recap import recap_report, recap_input, submission_contract
                    recap=recap_report(store)
                    recap_source=None
                    if not recap['available'] and recap['status'] != 'blocked' and not recap.get('terminal_failure'):
                        try:
                            from runtime.realtime_policy import current
                            if current(store.task()):
                                recap_input(store,prepare=True)
                            else:
                                recap_source=recap_input(store,begin=True)
                        except (ValueError, OSError, sqlite3.OperationalError):
                            # Quality delivery must survive a recap preparation failure.
                            pass
                    delivery_mode=task_delivery_mode(store)
                    if store.task().get('kind')=='video':
                        # Report delivery must stand on its own, including the upgrade action.
                        upgrade=upgrade_guidance(video=True)
                        upgrade['message']='本次视频质检报告已就绪。正式版提供更丰富、可按业务场景配置的规则，并统一管理项目、任务和报告。\n\n'+upgrade['opening_guidance']
                        upgrade['edition_comparison']['lite']=['无需火山引擎账号即可体验核心视频质检']
                        status['upgrade']=upgrade
                    if delivery_mode=='chat':
                        data={'status':'ready','task_id':store.task_id,'delivery_mode':'chat','report_url':None,
                              'delivery_required':True,'delivery':{'required':True,'type':'chat_report',
                              'message':'请在当前对话中交付本次 Lite 质检结论、风险、证据缺口、覆盖范围和正式版开通入口。'},
                              'next_action':'deliver-chat-report','report':chat_report(store,status),
                              'coverage':status['coverage'],'evidence_gaps':status['evidence_gaps'],'upgrade':status['upgrade']}
                    else:
                        from runtime.media import build_recording
                        build_recording(store)
                        from runtime.static_delivery import safe_export
                        result=safe_export(store,single_file=args.single_file)
                        item=next((a for a in result['artifacts'] if a['type']=='quality'),None)
                        url=Path(item['path']).as_uri() if item and delivery_mode=='local_dashboard' else None
                        data={'status':'ready','task_id':store.task_id,'delivery_mode':delivery_mode,
                              **result,'report_url':url,'delivery_required':True,
                              'delivery':{'required':True,'type':'report_url' if url else 'html_snapshot' if item else 'chat_report','url':url,
                                          'message':'质检报告已就绪，请交付结论及证据缺口；直接交付独立 HTML 报告，已保存的视频内嵌，无需解压或同目录媒体文件。'},
                              'next_action':'deliver-report','report':chat_report(store,status),
                              'coverage':status['coverage'],'evidence_gaps':status['evidence_gaps'],'upgrade':status['upgrade']}
        if args.command=='status':
            if store.task().get('kind')!='video':data['workflow_complete']=False
            data.update(inspection_continuation(data))
        if args.command in ('review-next','review-submit'):
            try:
                continuation=data.get('next',data)
                if continuation.get('status') in ('dispatcher_updated','superseded'):
                    pass  # Lifecycle acknowledgement must never implicitly allocate business work.
                elif continuation.get('segment') or (isinstance(continuation.get('segments'),list) and continuation['segments']):
                    # Only the coordinator submits; child batches first require host dispatch.
                    continuation['next_action']='dispatch-review-batch' if continuation.get('executor')=='child' else 'review-submit'
                    if continuation.get('finishing'):
                        from runtime.finishing import message
                        continuation['message']=message(store.task(),continuation['finishing'],pending=1)
                elif (args.command=='review-next' or 'next' in data or
                      (data.get('status') in {'saved','already_saved','batch_saved'} and not data.get('error_count'))):
                    if continuation.get('status')!='retry_review_next':
                        progress=continuation.get('status')
                        if not isinstance(progress,dict):progress=store.status()
                        if progress.get('report_ready'):
                            from runtime.recap import recap_report
                            progress['recap']=recap_report(store)
                        continuation.update(inspection_continuation(progress))
            except Exception:
                # Post-commit routing is advisory; never turn a saved review into a retry.
                if args.command!='review-submit':raise
                if 'next' in data:
                    data['next']={'status':'retry_review_next','next_action':'review-next'}
                else:
                    data['next_action']='status'
            if isinstance(data.get('next'), dict) and data['next'].get('next_action'):
                data['next_action'] = data['next']['next_action']
                data['continuation_path'] = 'next'
        if args.command=='report':
            from runtime.recap import recap_report, recap_input, submission_contract
            recap=recap_report(store)
            if data.get('status')=='ready' and store.task().get('kind')!='video' and recap_source is not None:
                data['submission_contract']=submission_contract(store,recap_source)
                data['recap_input']=recap_source
            if data.get('status')=='ready' and store.task().get('kind')!='video' and recap_source is None and not recap['available'] and recap['status'] != 'blocked' and not recap.get('terminal_failure'):
                data['recap_retry']={'retryable':True,'next_action':'recap-input --begin',
                    'message':'质检报告已就绪；无需等待交付确认，执行 recap-input --begin 获取复盘证据与合同。导出或附件受阻先交付完整 Chat 正文并继续复盘；禁止猜测证据 ID，不要结束当前执行。'}
            data['recap']={k:v for k,v in recap.items() if k in ('status','available','message','needs_resume','terminal_failure')}
            data['workflow_complete']=bool(recap['available'])
            data['quality_report_status']=data.get('status') if data.get('status') in {'ready','failed'} else 'not_ready'
            review_artifact=next((a for a in data.get('artifacts',[]) if a['type']=='review' and a.get('status')=='ready'),None)
            data['review_report_url']=Path(review_artifact['path']).as_uri() if review_artifact and data.get('delivery_mode')=='local_dashboard' and recap['available'] else None
            data['after_delivery_next_action']=('recap-report' if recap['available'] or recap['status']=='blocked' or recap.get('terminal_failure') else 'write-recap-result-and-submit' if recap_source is not None else 'recap-input --begin') if data['quality_report_status']=='ready' and store.task().get('kind')!='video' else data.get('after_delivery_next_action')
            if data['quality_report_status']=='ready' and store.task().get('kind')!='video':
                data['next_action']=data['after_delivery_next_action']
                data['delivery']['message']+=' 用中间消息交付质检报告，并执行 next_action，生成或复用本次直播复盘并交付；质检导出或交付失败不能阻塞复盘生成，可用完整 Chat 正文降级交付；不得在仅交付质检报告时结束执行或要求用户再次确认。'
        if args.command=='recap-submit':
            data['next_action']='recap-input --begin' if data.get('status')=='failed' and not data.get('terminal_failure') else 'recap-report'
        if args.command=='recap-report' and store.task().get('kind')!='video':
            from runtime.realtime_policy import current
            data['workflow_complete']=bool(data.get('available') and store.status()['report_ready'])
            data['delivery_required']=bool(data.get('available') or data.get('status')=='blocked' or data.get('terminal_failure')
                or (data.get('status')=='failed' and not current(store.task())))
            data['next_action']=('deliver-recap-report' if data.get('available') else
                                 'deliver-inspection-result' if data.get('status')=='blocked' or data.get('terminal_failure') else
                                 'recap-input --begin' if data.get('status')=='failed' else 'report')
        if args.command in ('stop','status','resume','report','recap-input','recap-report','recap-submit','review-next','review-submit') and store.task().get('review_protocol') == 'lite_review_v2':
            from runtime.report_completion import completion
            data.update(completion(store))
            if args.command in {'report','recap-report'}:
                template=data['delivery_ack_contract']['template']
                template['kind']='recap' if args.command=='recap-report' else 'quality'
                if data.get('status') in {'failed','blocked'}:template.update(outcome='failed',channel='chat')
                elif data.get('delivery_mode')=='chat':template['channel']='chat'
                if args.command=='recap-report' and not data.get('delivery_required'):
                    data.pop('delivery_ack_contract',None)
            if args.command in ('stop','status') and (data.get('report_ready') or data.get('report_blocked_reason')):
                data['next_action']=data['completion_next_action']
            if args.command in ('review-next','review-submit'):
                continuation = data.get('next', data)
                # A ready recap cannot bypass a missing quality delivery acknowledgement.
                if continuation.get('next_action') in {'report','recap-report'}:
                    continuation['next_action'] = data['next_action'] = data['completion_next_action']
        if args.command=='report' and data.get('status')=='ready' and store.task().get('kind')=='video':
            upgrade=data['upgrade']
            data['delivery']['message']=(
                ('请交付视频质检报告的独立 HTML 附件、结论、风险证据及覆盖缺口，不交付实时工作台。' if data['delivery_mode']!='chat' else '请直接交付视频质检报告、结论、风险证据及覆盖缺口，不交付实时工作台。') +
                '\n\n正式版能力升级：正式版提供更丰富、可按业务需求配置的规则，统一管理项目、任务和报告。'
                '\n\n'+upgrade['markdown'])
        if args.command=='report' and data.get('status')=='ready':
            from runtime.report_delivery import compact_report
            data=compact_report(store,data)
        if args.command in ('report','status','recap-report'):
            # Keep continuation visible before large report/evidence payloads.
            first=('next_action','workflow_complete','after_delivery_next_action','recap','submission_contract')
            data={**{key:data[key] for key in first if key in data},
                  **{key:value for key,value in data.items() if key not in first}}
        # Start creates its store internally; all public commands expose real artifacts.
        if args.command in ('start','start-video') and data.get('task_dir') and (Path(data['task_dir'])/'inspection.db').is_file():
            store=Store(data['task_dir'])
        if (store is not None and review_execution.active() and store.task().get('kind','live')=='live'
                and task_delivery_mode(store)=='html_snapshot'):
            # Keep HTML outside the bounded review transaction, but never omit its delivery check.
            data['snapshot_check'] = {'before_next_action':True,
                'command_argv':['status', '--task-dir', str(store.root)],
                'argv':[sys.executable, str(ENTRY), 'status', '--task-dir', str(store.root)],
                'instruction':'先从当前 Lite 目录用同一 Python 环境执行 command_argv 检查工作台快照；有 snapshot_delivery 就实际交付附件，无快照则立即继续。'
                    '仅处理该检查的附件交付或导出错误，随后回到本次响应的 next/next_action；不要按检查结果重新领取或提交已处理批次。'}
        if (store is not None and not review_execution.active()
                and not (args.command=='recap-report' and not data.get('delivery_required'))):
            from runtime.static_delivery import attach_artifacts
            attach_artifacts(store, data, args.command)
            # Artifact failures are independent of durable inspection/recap results.
            if data.get('artifact_status') == 'failed' and args.command in ('report','recap-report') and store.task().get('kind','live')=='live':
                data['delivery']={'required':True,'type':'chat_report','message':'请直接交付当前报告正文；不等待或重试 HTML 导出。'}
                data['delivery_required']=True
                if data.get('delivery_ack_contract'):data['delivery_ack_contract']['template']['channel']='chat'
            elif data.get('artifact_status') == 'failed':
                retry = ('report --allow-partial' if args.command=='report' and args.allow_partial else args.command) if args.command in ('report','recap-report','snapshot') else 'snapshot'
                data['artifact_retry_command'] = retry
                data['delivery'] = {'required':True, 'type':'artifact_error',
                    'message':'HTML 生成失败；质检数据已保留，请在原任务重试导出。'}
                data['delivery_required'] = True
                if args.command in ('report','recap-report','snapshot'):
                    data['next_action'] = 'retry-artifact-export'
        if store is not None and store.task().get('kind','live')=='live' and args.command in ('report','recap-report'):
            from runtime.report_delivery import public_live_report, attach_report_delivery
            if args.command=='recap-report':data=public_live_report(data)
            attach_report_delivery(data, args.command)
        if (store is not None and store.task().get('kind','live') == 'live'
                and store.task().get('review_protocol') == 'lite_review_v2'
                and args.command in ('stop','status','resume','review-next','review-submit','rules-load',
                                     'report','recap-input','recap-submit','recap-report','report-delivery-ack')):
            from runtime.live_continuation import annotate
            annotate(data, data.get('workflow_complete', False))
        first=('snapshot_check','delivery_required','delivery','snapshot_delivery','snapshot_events','artifact_status','artifacts',
               'delivery_ack_contract','next_action','workflow_complete','poll_after_seconds','continuation_instruction','after_delivery_next_action')
        data={**{key:data[key] for key in first if key in data},
              **{key:value for key,value in data.items() if key not in first}}
        if store is not None:publish_metadata(store.task())
        from runtime.sampling import enabled
        from runtime.report_delivery import bounded_output
        envelope=bounded_output(store,args.command,data) if store is not None and enabled(store.task()) else {'ok':True,'command':args.command,'data':data}
        if store is None and (args.command.startswith('batch-') or args.command in ('start','start-video')):
            from types import SimpleNamespace
            result_root=getattr(args,'batch_dir',None) or data.get('task_dir')
            if result_root:envelope=bounded_output(SimpleNamespace(root=Path(result_root).expanduser().resolve()),args.command,data)
        print(encode(envelope));return 0
    except Exception as error:
        record_command_error(error)
        from runtime.diagnostics import is_memory_error
        if is_memory_error(error):
            publish_metadata(error_code='OUT_OF_MEMORY')
            print(encode({'ok':False,'command':args.command,'error':{
                'code':'OUT_OF_MEMORY','message':'内存不足，本次操作未完成；保留原任务及已生成报告，释放资源后沿原任务恢复。'}}))
            return 1
        context = {}
        if args.command in ('start','start-video') and args.task_dir:
            try:
                from runtime.task_context import read
                reserved=read(args.task_dir)
                if reserved: context={'data':{'task_id':reserved['task_id'],'task_dir':str(Path(args.task_dir).expanduser().resolve())}}
            except (OSError,ValueError):
                pass
        if args.command=='stop' and isinstance(error,sqlite3.OperationalError):
            from runtime.stop_signal import read as read_stop
            if read_stop(args.task_dir):
                publish_metadata(error_code='OPERATION_FAILED',error_detail='STOP_STATE_PENDING')
                print(encode({'ok':False,'command':'stop','error':{
                    'code':'STOP_STATE_PENDING','category':'OperationalError','retryable':True,
                    'stop_signal_recorded':True,'next_action':'stop',
                    'command_argv':['stop','--task-dir',args.task_dir,'--reason',args.reason,
                                    '--user-instruction',args.user_instruction],
                    'message':'停止信号已保存，采集进程将独立响应；在原任务重试 stop 同步状态并继续双报告，不重建任务、不手工杀进程。'}}))
                return 1
        from runtime.review_errors import ReviewError
        if isinstance(error,ReviewError):
            print(encode({'ok':False,'command':args.command,'error':error.detail}));return 1
        # Never echo URLs, subprocess args, malformed submitted evidence or credentials.
        if getattr(error,'code',None)=='NO_CAPTURED_CONTENT':
            print(encode({'ok':False,'command':args.command,'error':{'code':error.code,
                'message':'未采集到内容，无法生成质检报告和内容复盘。',
                'next_action':'deliver-inspection-result','retryable':False}}));return 1
        if isinstance(error,RecapInputError):
            if args.command=='review-submit':
                code=error.code.replace('RECAP_','REVIEW_')
                message=str(error).replace('recap-submit','review-submit').replace('复盘','判定')
                publish_metadata(error_code=code)
                print(encode({'ok':False,'command':args.command,'error':{'code':code,'message':message,'field':'input_file','next_action':'review-submit',**({'line':error.line,'column':error.column} if error.line is not None else {})}}));return 1
            publish_metadata(error_code=error.code)
            detail={'code':error.code,'message':str(error),'next_action':'write-recap-result-and-submit'}
            if args.command=='recap-submit':
                from runtime.recap import submission_recovery
                detail=submission_recovery(store,detail)
            print(encode({'ok':False,'command':args.command,'error':detail}));return 1
        if getattr(error,'code',None) in {'LOCAL_VIDEO_PATH_REQUIRED','VIDEO_SOURCE_UNAVAILABLE','VIDEO_SOURCE_CHANGED','VIDEO_INVALID'}:
            publish_metadata(error_code=error.code)
            print(encode({'ok':False,'command':args.command,**context,'error':{'code':error.code}}));return 1
        code='INVALID_INPUT' if isinstance(error,(ValueError,KeyError,TypeError)) else 'RUNTIME_UNAVAILABLE'
        detail=review_error(error, fallback=args.command=='review-submit' and isinstance(error,(ValueError,KeyError,TypeError)),protocol_v2=bool(store is not None and store.task().get("review_protocol")=="lite_review_v2"))
        if detail is not None:
            publish_metadata(error_code=detail['code'])
            print(encode({'ok':False,'command':args.command,'error':detail}));return 1
        if args.command=='recap-input' and (isinstance(error,(OSError,sqlite3.OperationalError)) or str(error)=='inspection not finished'):
            waiting = str(error) == 'inspection not finished'
            from runtime.realtime_policy import current
            blocked = not waiting and store is not None and current(store.task())
            print(encode({'ok':False,'command':args.command,'error':{
                'code':'RECAP_NOT_READY' if waiting else 'RECAP_INPUT_UNAVAILABLE',
                'retryable':not blocked,'next_action':'blocked' if blocked else 'report' if waiting else 'recap-input --begin',
                'message':('复盘证据读取重试耗尽，交付阻塞说明并保留原任务目录；工具恢复后沿原任务续办，不伪造报告。' if blocked else '沿原任务自动重试读取复盘证据；禁止猜测证据 ID，不能将本次失败视为工作流完成。')}}))
            return 1
        if args.command=='recap-submit' and isinstance(error,(ValueError,KeyError,TypeError)):
            from runtime.recap import submission_error, submission_recovery
            detail=submission_recovery(store,submission_error(error))
            publish_metadata(error_code=detail['code'])
            print(encode({'ok':False,'command':args.command,'error':detail}));return 1
        stop_details = {
            'task does not exist': 'STOP_TASK_NOT_FOUND',
            'immediate stop requires user confirmation': 'STOP_CONFIRM_DISCARD_REQUIRED',
            'immediate stop requires user confirmation to discard remaining content': 'STOP_CONFIRM_DISCARD_REQUIRED',
            'ordinary stop must drain; immediate stop requires explicit confirmation to discard remaining content': 'STOP_ORDINARY_REQUIRES_DRAIN',
            'immediate stop requires a live task': 'STOP_LIVE_TASK_REQUIRED',
            'agent stop requires user instruction': 'STOP_USER_INSTRUCTION_REQUIRED',
        }
        publish_metadata(error_code=code if isinstance(error,(ValueError,KeyError,TypeError)) else getattr(error,'code','OPERATION_FAILED'),
                         error_detail=stop_details.get(str(error)) if args.command=='stop' and isinstance(error,ValueError) else None)
        from runtime.diagnostics import failure_details
        print(encode({'ok':False,'command':args.command,**context,'error':{'code':code,'category':type(error).__name__,
            'diagnostic':failure_details(error),
            'message':'Operation failed; preserve task directory and check configuration or evidence input'}}))
        return 1
