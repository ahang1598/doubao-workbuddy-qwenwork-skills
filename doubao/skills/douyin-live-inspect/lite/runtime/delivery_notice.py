"""Local-computer recommendation, acknowledged only after user-visible delivery."""
import os
from pathlib import Path
from runtime.input_errors import ConfigurationError, InputValidationError

RECOMMENDATION = ('建议优先切换到豆包工作「工作任务 · 本地电脑」体验 Lite，'
    '可在直播实时质检工作台查看检测进度、质检结果及报告，也便于访问视频素材。'
    '当前任务会继续执行，切换电脑不是本次报告交付的前提。')
NOTICE_ID = 'local-computer-recommendation-v1'


def is_doubao_cloud(env=None):
    env = os.environ if env is None else env
    # Explicit context supplied by the Agent must come from the host, never media.
    context = env.get('BYTEDLIVE_INSPECT_HOST')
    if context is not None:
        if context not in {'doubao_cloud', 'local', 'other', 'unknown'}:
            raise ConfigurationError('HOST_CONTEXT_INVALID', '宿主配置 BYTEDLIVE_INSPECT_HOST 无效；根据实际运行环境设置为 doubao_cloud、local、other 或 unknown。')
    # A local desktop can run commands in a sandbox; host evidence wins over
    # Agent-supplied context and generic container markers.
    if env.get('CUA_USE_ISOLATED_ENV') == '0':
        return False
    # A definite Agent-supplied host decision wins. "unknown" means the Agent
    # had no evidence and must not suppress stronger runtime host markers.
    if context in {'doubao_cloud', 'local', 'other'}:
        return context == 'doubao_cloud'
    doubao = any(k.startswith('DOUBAO_OFFICE_') for k in env) or bool(env.get('DOUBAO_SANDBOX_TYPE'))
    # CUA_USE_ISOLATED_ENV=1 is the strongest marker when present. Some Doubao
    # SaaS runtimes do not expose it, so an explicit SaaS sandbox marker is also
    # accepted; generic workspace/container paths are deliberately ignored.
    cloud = env.get('CUA_USE_ISOLATED_ENV') == '1' or env.get('DOUBAO_SANDBOX_TYPE') == 'SaaS'
    return doubao and cloud


def acknowledged(store):
    task = store.task()
    if task.get('local_computer_notice_acknowledged'):
        return True
    scope = task.get('notice_batch')
    if scope:
        from runtime.store import Store
        for path in (Path(scope['root']) / 'tasks').glob('*/inspection.db'):
            sibling = Store(path.parent).task()
            if sibling.get('notice_batch') == scope and sibling.get('local_computer_notice_acknowledged'):
                return True
    return False


def effective_delivery_mode(mode):
    """Cloud attachments must be self-contained, even for older local tasks."""
    if not isinstance(mode, str) or mode not in {'local_dashboard', 'html_snapshot', 'chat'}:
        raise InputValidationError('START_DELIVERY_MODE_INVALID', 'delivery_mode 必须是 local_dashboard、html_snapshot 或 chat。')
    return 'html_snapshot' if mode == 'local_dashboard' and is_doubao_cloud() else mode


def attach_notice(store, delivery):
    if not is_doubao_cloud() or acknowledged(store):
        return delivery
    store.update_task(local_computer_notice_pending=True)
    delivery['message'] += '\n\n当前使用的是云电脑。\n\n**' + RECOMMENDATION + '**'
    delivery['notice_id'] = NOTICE_ID
    delivery['after_delivery_command'] = 'delivery-ack'
    return delivery


def acknowledge(store):
    if not store.task().get('local_computer_notice_pending'):
        raise ValueError('no recommendation awaiting delivery acknowledgement')
    store.update_task(local_computer_notice_acknowledged=True)
    return {'status': 'acknowledged', 'notice_id': NOTICE_ID, 'next_action': 'status'}
