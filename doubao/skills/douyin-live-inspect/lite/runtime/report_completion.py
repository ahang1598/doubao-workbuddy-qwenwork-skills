"""Report availability is not proof of delivery to the user."""
import time


def completion(store):
    task = store.task()
    from runtime.recap import recap_report
    recap = recap_report(store)
    version = recap.get('evidence_version')
    deliveries = task.get('report_deliveries', {})
    complete = (recap.get('status') in {'ready', 'insufficient', 'blocked'} and version is not None
                and all(deliveries.get(k, {}).get('evidence_version') == version
                        and (deliveries.get(k, {}).get('outcome', 'ready') == 'ready' or recap.get('status') == 'blocked')
                        for k in ('quality', 'recap')))
    if complete and task.get('review_dispatch_version') == 2 and not task.get('media_frozen'):
        from runtime.live_review import initialize, rows, ACTIVE
        with store.connection() as conn:
            initialize(conn)
            complete = not any(b.get('executor') == 'child' and b['status'] in ACTIVE
                               for b in rows(conn, store.session_id))
    pending = [kind for kind in ('quality', 'recap')
               if version is None or deliveries.get(kind, {}).get('evidence_version') != version
               or (kind == 'recap' and recap.get('status') != 'blocked'
                   and (not recap.get('available') or deliveries.get(kind, {}).get('outcome', 'ready') != 'ready'))]
    action = ('status' if complete or not pending else 'report' if pending[0] == 'quality' else
              'recap-report' if recap.get('status') in {'ready','insufficient','blocked'} else 'recap-input --begin')
    return {'workflow_complete': complete, 'report_deliveries': deliveries,
            'pending_reports': pending, 'completion_next_action': action,
            'delivery_ack_contract': {'command': 'report-delivery-ack',
                'task_dir': str(store.root),
                'template': {'kind': 'quality', 'evidence_version': version, 'channel':'file', 'outcome':'ready'},
                'instruction': '实际展示后确认；kind 为 quality 或 recap。成功 outcome=ready；交付失败结果用 outcome=failed、channel=chat。两项都确认前继续交付。'}}


def exported(store,version,kinds):
    import json
    try:
        manifest=json.loads((store.root/'html/manifest.json').read_text())
        found={a['type'] for a in manifest['artifacts'] if a.get('status')=='ready'
               and store.local_path(a['path']).is_file()}
        return manifest.get('evidence_version')==version and kinds <= found
    except (OSError,ValueError,KeyError,TypeError):return False


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
    available = status['report_ready'] if value['kind'] == 'quality' else report.get('available')
    failed = bool(status.get('report_blocked_reason')) if value['kind'] == 'quality' else report['status'] in {'failed','blocked'}
    if (outcome == 'ready' and not available) or (outcome == 'failed' and not failed):
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
