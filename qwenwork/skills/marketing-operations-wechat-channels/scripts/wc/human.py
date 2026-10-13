"""人类行为模拟参数（延迟、滚动、悬停）。"""

import random
import time

# ========== 延迟范围（毫秒） ==========
HUMAN_DELAY = (300, 700)
REACTION_TIME = (300, 800)
HOVER_TIME = (100, 300)
READ_TIME = (500, 1200)
SHORT_READ = (600, 1200)
SCROLL_WAIT = (100, 200)
POST_SCROLL = (300, 500)


def sleep_random(min_ms: int, max_ms: int) -> None:
    """随机延迟。"""
    if max_ms <= min_ms:
        time.sleep(min_ms / 1000.0)
        return
    delay = random.randint(min_ms, max_ms) / 1000.0
    time.sleep(delay)


def navigation_delay() -> None:
    """页面导航后的随机等待，模拟人类阅读。"""
    sleep_random(1000, 2500)
