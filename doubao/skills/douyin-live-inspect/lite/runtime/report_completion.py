"""Report availability is not proof of delivery to the user."""
import time


def has_active_review_child(connection, session_id):
    from runtime.live_review import rows, ACTIVE
    if not connection.execute("SELECT 1 FROM sqlite_master WHERE name='review_batches'").fetchone():
        return False
    return any(b.get('executor') == 'child' and b['status'] in ACTIVE
               for b in rows(connection, session_id))


def completion(store):
    task = store.task()
    from runtime.recap import recap_report
    recap = recap_report(store)
    version = recap.get('evidence_version')
    deliveries = task.get('report_deliveries', {})
    failed_recap = recap.get('status') == 'blocked' or recap.get('terminal_failure', False)
    def delivered(kind):
        receipt = deliveries.get(kind, {})
        if version is None or receipt.get('evidence_version') != version:return False
        if receipt.get('outcome', 'ready') == 'failed':
            return failed_recap if kind == 'recap' else bool(store.status().get('report_blocked_reason'))
        return bool(recap.get('available')) if kind == 'recap' else True
    complete = all(delivered(k) for k in ('quality', 'recap'))
    if complete and task.get('review_dispatch_version') == 2 and not task.get('media_frozen'):
        complete = not store._read_with_retry(lambda conn: has_active_review_child(conn, store.session_id))
    pending = [kind for kind in ('quality', 'recap') if not delivered(kind)]
    action = ('status' if complete or not pending else 'report' if pending[0] == 'quality' else
              'recap-report' if recap.get('available') or failed_recap else 'status')
    # A host delivery failure must not gate independent report generation.
    generation = ('recap-input --begin' if not complete and not recap.get('available')
                  and not failed_recap and store.status().get('report_ready') else 'status')
    if recap.get('recovery_blocked'): generation = 'blocked'
    return {'workflow_complete': complete, 'workflow_outcome': ('failed' if failed_recap else 'ready') if complete else 'pending', 'report_deliveries': deliveries,
            'pending_reports': pending, 'completion_next_action': generation if generation != 'status' else action,
            'generation_next_action': generation, 'delivery_next_action': action,
            'delivery_ack_contract': {'command': 'report-delivery-ack',
                'task_dir': str(store.root),
                'template': {'kind': 'quality', 'evidence_version': version, 'channel':'file', 'outcome':'ready'},
                'instruction': '实际展示后确认；kind 为 quality 或 recap。成功 outcome=ready；交付失败结果用 outcome=failed、channel=chat。两项都确认前继续交付。'}}


def exported(store,version,kinds):
    import json
    try:
        manifest=json.loads((store.root/'html/manifest.json').read_text())
        if manifest.get('artifact_status', 'ready') != 'ready':return False
        found={a['type'] for a in manifest['artifacts'] if a.get('status')=='ready'
               and store.local_path(a['path']).is_file()}
        return manifest.get('evidence_version')==version and kinds <= found
    except (OSError,ValueError,KeyError,TypeError):return False


def outcome_available(task, kind, outcome, status, recap):
    """判断现有报告结果是否可交付；回执确认和遥测读取使用同一业务规则。"""
    if kind == 'quality':
        return bool(status['report_ready'] if outcome == 'ready' else status.get('report_blocked_reason'))
    if outcome == 'ready':return bool(recap.get('available'))
    from runtime.realtime_policy import current
    return (recap['status'] == 'blocked' or recap.get('terminal_failure', False)
            or (not current(task) and recap['status'] == 'failed'))


def acknowledge(store, value):
    if store.task().get('review_protocol') != 'lite_review_v2':
        raise ValueError('delivery acknowledgement requires current live review protocol')
    if value.get('kind') not in {'quality', 'recap'}:
        raise ValueError('report kind must be quality or recap')
    if value.get('channel', 'file') not in {'file','chat'}:raise ValueError('invalid delivery channel')
    outcome = value.get('outcome', 'ready')
    if outcome not in {'ready','failed'}:raise ValueError('invalid delivery outcome')
    if outcome == 'failed' and value.get('channel') != 'chat':raise ValueError('failure must be delivered in chat')
    if outcome == 'ready' and value.get('channel') != 'chat' and store.task().get('media_frozen') and store.task().get('delivery_mode') != 'chat':
        kind='review' if value['kind']=='recap' else 'quality'
        if not exported(store,value.get('evidence_version'),{kind}):raise ValueError('report artifact not exported')
    status = store.status()
    from runtime.recap import recap_report
    report = recap_report(store)
    if value.get('evidence_version') is None or value['evidence_version'] != report.get('evidence_version'):
        raise ValueError('report not ready or evidence version changed')
    if not outcome_available(store.task(), value['kind'], outcome, status, report):
        raise ValueError('report outcome not available')
    with store.connection(True) as conn:
        task = store._task(conn)
        from runtime.recap import evidence_input
        if evidence_input(task, store._segments(conn))['evidence_version'] != value['evidence_version']:
            raise ValueError('report evidence changed')
        deliveries = task.setdefault('report_deliveries', {})
        previous = deliveries.get(value['kind'], {})
        channel = value.get('channel', 'file')
        if (previous.get('evidence_version') != value['evidence_version'] or previous.get('outcome','ready') != outcome
                or previous.get('channel') != channel):
            deliveries[value['kind']] = {'evidence_version': value['evidence_version'], 'delivered_at': time.time(),
                                        'outcome':outcome, 'channel':channel}
        store._set_task(conn, task)
    result = completion(store)
    return {'status': 'acknowledged', **result, 'next_action': result['completion_next_action']}
