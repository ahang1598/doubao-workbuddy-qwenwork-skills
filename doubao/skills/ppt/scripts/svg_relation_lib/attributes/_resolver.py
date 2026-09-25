"""
Channel conflict resolver · 同一 channel 被多个 attribute 占用时的降级策略

规则：
1. 按 attrs 声明顺序 · 先声明的占默认 channel
2. 后声明的若与已占 channel 冲突 · 降级到 fallback_channel
3. 若 fallback 也被占 · 抛 error
"""
from __future__ import annotations
from typing import List, Dict


def resolve_channels(attrs: List) -> Dict[str, str]:
    """
    attrs: List[Attribute] instances
    return: dict {attribute_class_name: resolved_channel}
    """
    used = set()
    mapping: Dict[str, str] = {}
    for attr in attrs:
        name = attr.__class__.__name__
        chan = getattr(attr, "channel", None)
        fallback = getattr(attr, "fallback_channel", None)

        if chan is None:
            raise ValueError(f"{name} · missing `channel` attribute")

        # "none" fallback 表示没有降级选项 · 允许占用一次
        if chan not in used:
            mapping[name] = chan
            if chan != "none":
                used.add(chan)
        elif fallback and fallback != "none" and fallback not in used:
            mapping[name] = fallback
            used.add(fallback)
        else:
            raise ValueError(
                f"channel conflict · {name} wants '{chan}' or '{fallback}' · "
                f"both taken by {sorted(used)}"
            )
    return mapping
