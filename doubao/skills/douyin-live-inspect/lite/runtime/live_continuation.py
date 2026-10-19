"""Agent guidance follows the returned action, including temporary empty claims."""


def annotate(data, complete=False):
    """Add action-specific guidance without advancing the workflow."""
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
    if complete:
        instruction = '本次交付结果已确认完成，可以结束本轮。'
    elif action == 'status':
        target['poll_after_seconds'] = data['poll_after_seconds'] = 3
        instruction = ('本次尚未完成，最多等待 3 秒后执行 status，按返回的 next_action 自动续办。'
                       '空批次、用户未回复或阶段性播报都不是结束条件，不询问是否继续；'
                       '直播结束或断流后仍按原任务策略完成剩余判定与双报告交付。')
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
    data['continuation_instruction'] = target['continuation_instruction'] = instruction
