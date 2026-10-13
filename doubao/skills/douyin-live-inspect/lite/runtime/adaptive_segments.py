"""Read compatibility for historical segmentation metadata; capture uses fixed slices."""
PARAMETERS = {'version': 1, 'min_ms': 30000, 'max_ms': 60000, 'silence_ms': 500}


def enabled(task):
    return task.get('kind', 'live') == 'live' and task.get('segmentation') == PARAMETERS
