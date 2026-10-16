"""Finite affine arithmetic for matrix colour and position domains."""

from __future__ import annotations

import math


def stable_fraction(value, low, high):
    """Map a finite observation to [0, 1] without overflowing a wide span."""
    if not all(math.isfinite(v) for v in (value, low, high)):
        raise ValueError("affine mapping requires finite values")
    if high < low:
        raise ValueError("affine mapping requires low <= high")
    if high == low:
        return 0.5
    if value <= low:
        return 0.0
    if value >= high:
        return 1.0
    span = high - low
    if math.isfinite(span):
        return (value - low) / span
    # Only opposite-sign finite endpoints can overflow their subtraction.
    # Divide before subtracting, retaining the full finite input domain.
    scale = max(abs(low), abs(high))
    lower, upper = low / scale, high / scale
    return min(1.0, max(0.0, (value / scale - lower) / (upper - lower)))


def stable_lerp(low, high, fraction):
    """Interpolate finite endpoints; preserve constants and endpoint values."""
    if not all(math.isfinite(v) for v in (low, high, fraction)):
        raise ValueError("interpolation requires finite values")
    if fraction <= 0 or low == high:
        return low
    if fraction >= 1:
        return high
    if fraction == 0.5:
        total = low + high
        return total / 2 if math.isfinite(total) else low / 2 + high / 2
    span = high - low
    if math.isfinite(span):
        return low + span * fraction
    return low * (1 - fraction) + high * fraction
