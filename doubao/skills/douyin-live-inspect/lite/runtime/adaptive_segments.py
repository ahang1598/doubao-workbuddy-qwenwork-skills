"""Read compatibility for historical segmentation metadata; capture uses fixed slices."""
# 核心实现模块：负责本模块声明的检测、状态处理或交付边界；敏感输入和原始响应不进入日志。
PARAMETERS = {'version': 1, 'min_ms': 30000, 'max_ms': 60000, 'silence_ms': 500}


def enabled(task):
    return task.get('kind', 'live') == 'live' and task.get('segmentation') == PARAMETERS
