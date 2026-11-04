"""Agent guidance follows the returned action, including temporary empty claims."""


def annotate(data, complete=False, *, store=None):
    """Add action-specific guidance without advancing the workflow."""
    from runtime.delivery_notice import is_doubao_cloud
    from runtime.realtime_policy import cloud_limited, CLOUD_COMMAND_LIMIT
    task=store.task() if store is not None else {}
    if task and task.get('kind', 'live') == 'live':
        from runtime.diagnostics import capture_status_text
        data.update(source_end_reason=task.get('source_end_reason', 'unknown'),
                    live_source_status=task.get('live_source_status', 'unknown'),
                    capture_status_text=capture_status_text(task))
    cloud=store is not None and (is_doubao_cloud() or cloud_limited(task))
    next_result = data.get('next')
    nested = isinstance(next_result, dict) and bool(next_result.get('next_action'))
    target = next_result if nested else data
    action = target.get('next_action')
    data['workflow_complete'] = target['workflow_complete'] = complete
    if not action:
        return
    if nested:
        data.update(next_action=action, continuation_path='next')
    target.pop('poll_after_seconds', None)
    data.pop('poll_after_seconds', None)
    target.pop('wait_command_argv', None)
    data.pop('wait_command_argv', None)
    if complete:
        instruction = '本次交付结果已确认完成，可以结束本轮。'
    elif action == 'status':
        target['poll_after_seconds'] = data['poll_after_seconds'] = 3
        instruction = ('本次尚未完成，最多等待 3 秒后执行 status，按返回的 next_action 自动续办。'
                       '空批次、用户未回复或阶段性播报都不是结束条件，不询问是否继续；'
                       '直播结束或断流后仍按原任务策略完成剩余判定与双报告交付。')
        if cloud:
            target['poll_after_seconds'] = data['poll_after_seconds'] = 0
            target['wait_command_argv'] = data['wait_command_argv'] = ['status','--task-dir',str(store.root),'--wait-seconds','30']
            instruction = ('立即执行 wait_command_argv，由运行时等待最多30秒，有内容或状态变化提前返回；不要另加 sleep 或短轮询。'
                           '用户未回复不影响续办，按返回动作继续判定和双报告交付。')
    elif action == 'review-next':
        instruction = '立即以新的 request-id 执行 review-next；不重放已保存提交，不等待用户回复。'
    elif action == 'review-submit':
        instruction = ('按合同提交；勿重领。' if target.get('segments') else
                       '按本批证据与提交合同完成判定；校验失败时仅修复失败项并使用重试合同。')
    elif action == 'report':
        instruction = '立即执行 report，先实际交付质检报告，再按回执完成复盘和双报告交付确认；不等待用户回复。'
    elif action in {'recap-report', 'recap-input --begin', 'write-recap-result-and-submit',
                    'read-recap-evidence-pages', 'deliver-recap-report', 'deliver-report', 'deliver-chat-report'}:
        instruction = '按 next_action 继续生成或实际交付报告，完成对应交付确认；两份报告确认前不能结束或要求用户再次授权。'
    elif action == 'deliver-inspection-result':
        instruction = '交付已核实的无有效内容或失败结果，保留原任务信息；不得伪造报告或成功交付确认。'
    elif action in {'review-state', 'read-request-result', 'read-recovery-result', 'observe-original-command',
                    'observe-review-worker'}:
        instruction = '核对原请求并读取保存回执，沿返回动作续办；未知执行不得重复提交或领取。'
    elif action in {'resume', 'resolve-setup', 'blocked'}:
        instruction = '沿原任务处理已核实的恢复动作；工具不可用时如实说明阻塞并保留续办信息，不声称后台继续判定。'
    else:
        instruction = '按 next_action 继续当前任务；未完成双报告交付确认前不把阶段性结果视为完成。'
    if not complete:
        if (cloud and task.get('inspection_policy')=='lite_live_realtime_v2'
                and not task.get('stop_requested') and task.get('capture_status') not in {'ended','stopped','failed'}):
            if cloud_limited(task):
                instruction += f' 云端采集/判定调度已用{task["cloud_live_command_count"]}/{CLOUD_COMMAND_LIMIT}次；该计数不含宿主文件和附件工具。'
            instruction += (' 本轮宿主工具调用达到100步，或宿主更早提示额度/上下文不足时，先核对并提交已完成判断，随后沿原 task_dir 执行 '
                            'stop --reason execution_limit，停止新增采集并继续收尾和双报告；不要耗尽最后一步才收尾，不伪造用户停止指令。')
    if task.get('source_end_reason') == 'offline' and task.get('live_source_status') == 'not_live':
        instruction += ' 本任务已确认直播结束；按实际已采集内容说明报告结果，无内容时明确说明直播结束导致未取得内容、无法生成双报告。'
    elif not complete:
        instruction += (' 采集停止或进入收尾不代表直播停播；只有 source_end_reason=offline 且 live_source_status=not_live 才能称“直播已结束”。'
                        '来源解析失败应称“采集中断，未确认停播”，仍沿原 next_action 继续。')
    data['continuation_instruction'] = target['continuation_instruction'] = instruction
