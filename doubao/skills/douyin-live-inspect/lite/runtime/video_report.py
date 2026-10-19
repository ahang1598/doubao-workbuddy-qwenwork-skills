"""Video report snapshots and user-visible delivery receipts are independent."""
import hashlib
import json
from pathlib import Path
from runtime.platform_support import file_lock
from runtime.store import atomic_json, encode, upgrade_guidance
from runtime.static_delivery import FrozenStore, safe_export, sanitize, media_file
from runtime.ui import build_report, _evidence
from runtime.review_errors import ReviewError


def snapshot_key(frozen, report):
    media = []
    for raw in [*_evidence(frozen).values(), frozen.task().get('playback_file')]:
        path = media_file(frozen, raw)
        stat = path.stat() if path else None
        media.append((raw,stat.st_size if stat else None,stat.st_mtime_ns if stat else None))
    return hashlib.sha256(encode([report,media]).encode()).hexdigest()


def read_receipt(store):
    path=store.root/'.video-report-delivery.json'
    return json.loads(path.read_text()) if path.exists() else None


def receipt_matches_run(receipt, frozen):
    # Legacy receipts have no provable generation and must be exported again.
    return bool(receipt and receipt.get('report_run') == frozen.task().get('video_report_run', 1))


def delivered_report(store):
    """A batch may advance only after the current snapshot was actually delivered."""
    receipt=read_receipt(store)
    if not receipt or receipt['delivery_status']!='delivered':return None
    frozen=FrozenStore(store)
    if not receipt_matches_run(receipt, frozen) or receipt['fingerprint']!=snapshot_key(frozen,build_report(frozen)):return None
    return receipt['result']


def video_report(store, *, allow_partial=False, mode=None, single_file=True):
    from runtime.cli import chat_report, inspection_continuation
    with file_lock(store.root/'.video-report.lock'):
        frozen=FrozenStore(store)
        status=frozen.status()
        if not status['report_ready'] and not allow_partial:
            return {'status':'not_ready',**status,**inspection_continuation(status),'artifacts':[]}
        from runtime.delivery_notice import effective_delivery_mode
        mode=effective_delivery_mode(mode or frozen.task().get('delivery_mode','local_dashboard'))
        report=build_report(frozen)
        key=snapshot_key(frozen,report)
        receipt=read_receipt(store)
        if (receipt_matches_run(receipt, frozen) and receipt['fingerprint']==key and receipt['result']['delivery_mode']==mode and receipt['result'].get('media_layout')==('embedded' if single_file else 'separate')
                and all(a['type'] != 'bundle' and Path(a['path']).is_file() for a in receipt['result'].get('artifacts',[]))):
            result=receipt['result']
            result.update(delivery_status=receipt['delivery_status'],delivery_required=receipt['delivery_status']!='delivered')
            from runtime.telemetry_funnel import observe_video_delivery
            observe_video_delivery(store, receipt, frozen)
            return result
        upgrade=upgrade_guidance(video=True)
        summary=sanitize(chat_report(frozen,status,report))
        common={'media_layout':'embedded' if single_file else 'separate','status':'ready','task_id':store.task_id,'delivery_mode':mode,'report':summary,
                'processing_complete':report['processing_complete'],'coverage_complete':report['coverage_complete'],
                'coverage':summary['coverage'],'evidence_gaps':status['evidence_gaps'],
                'upgrade':upgrade,'delivery_status':'pending','delivery_required':True,'report_url':None}
        if mode=='chat':
            version=(receipt or {}).get('result',{}).get('version',0)+1
            result={**common,'version':version,'artifacts':[],
                    'delivery':{'required':True,'type':'chat_report','message':'交付本次结构化视频报告、风险与覆盖缺口。'},
                    'next_action':'deliver-chat-report'}
        else:
            exported=safe_export(store,single_file=single_file,allow_partial=allow_partial,frozen_store=frozen)
            if exported['artifact_status']!='ready':return {**common,**exported,'delivery':{'type':'artifact_error','required':True}}
            # The alias remains on disk, but delivery binds an immutable version.
            quality=next(a for a in exported['artifacts'] if a['type']=='quality')
            url=Path(quality['path']).as_uri() if mode=='local_dashboard' else None
            result={**common,**exported,'report_url':url,
                    'delivery':{'required':True,'type':'report_url' if url else 'html_snapshot','url':url,
                                'path':quality['path'],'artifact_type':'quality','version':quality['version'],
                                'message':'直接交付独立 HTML 报告，已保存的视频内嵌，无需解压。旧附件为历史快照。'},
                    'next_action':'deliver-report'}
        result['version'] = max(result['version'], (receipt or {}).get('result', {}).get('version', 0) + 1)
        result['after_delivery_next_action']='report-delivery-ack'
        result['delivery_ack']={'version':result['version'],'status':'delivered'}
        result['complete']=report['processing_complete'] and report['coverage_complete']
        receipt = {'fingerprint':key,'report_run':frozen.task().get('video_report_run', 1),'delivery_status':'pending','result':result}
        atomic_json(store.root/'.video-report-delivery.json', receipt)
        from runtime.telemetry_funnel import observe_video_delivery
        observe_video_delivery(store, receipt, frozen)
        return result


def acknowledge_report(store, value):
    if store.task().get('kind')!='video':raise ReviewError('VIDEO_ONLY','command','此命令仅适用于视频。',retryable=False)
    if not isinstance(value,dict) or type(value.get('version')) is not int or value.get('status') not in {'delivered','failed'}:
        raise ReviewError('REPORT_RECEIPT_INVALID','receipt','提供报告版本及 delivered 或 failed 状态。')
    with file_lock(store.root/'.video-report.lock'):
        receipt=read_receipt(store)
        frozen=FrozenStore(store)
        if (not receipt_matches_run(receipt, frozen) or receipt['result']['version']!=value['version']
                or receipt['fingerprint']!=snapshot_key(frozen,build_report(frozen))):
            raise ReviewError('REPORT_VERSION_CHANGED','version','结果已更新，请读取并交付最新报告。',next_action='report --allow-partial')
        if any(not Path(a['path']).is_file() for a in receipt['result'].get('artifacts',[])):
            raise ReviewError('REPORT_ARTIFACT_MISSING','artifacts','报告文件缺失，请重新导出。',next_action='report --allow-partial')
        receipt['delivery_status']=value['status']
        atomic_json(store.root/'.video-report-delivery.json',receipt)
        from runtime.telemetry_funnel import observe_video_delivery
        observe_video_delivery(store, receipt, frozen)
        return {'status':value['status'],'delivery_status':value['status'],'version':value['version'],
                'next_action':'report --allow-partial' if value['status']=='failed' else 'delivery-complete',
                'artifacts':receipt['result'].get('artifacts',[])}
