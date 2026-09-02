#!/usr/bin/env python3
"""
ATP (Available-to-Promise) calculator for multi-channel shared inventory.

ATP = on_hand
    + inbound_usable          # inbound * alpha
    - committed               # unshipped orders
    - reserves                # wholesale / pre-order / promo
    - quality_hold
    - fba_dedicated           # ring-fenced FBA + FBA in-transit
    - central_buffer

Optional channel publish qty = floor(ATP * (1 - buffer_pct)) capped by optional cap.

Examples:
  python atp_calculate.py --on-hand 1000 --committed 120 --reserves 80 \\
      --quality-hold 30 --fba-dedicated 200 --central-buffer 50

  python atp_calculate.py --on-hand 1000 --inbound 500 --inbound-alpha 0 \\
      --committed 120 --channel amazon_mfn=0.12,shopify=0.05,tiktok=0.15
"""

from __future__ import annotations

import argparse
import math
from typing import Dict


def compute_atp(
    on_hand: float,
    inbound: float,
    inbound_alpha: float,
    committed: float,
    reserves: float,
    quality_hold: float,
    fba_dedicated: float,
    central_buffer: float,
) -> dict:
    inbound_usable = max(0.0, inbound) * max(0.0, min(1.0, inbound_alpha))
    deductions = {
        "committed": max(0.0, committed),
        "reserves": max(0.0, reserves),
        "quality_hold": max(0.0, quality_hold),
        "fba_dedicated": max(0.0, fba_dedicated),
        "central_buffer": max(0.0, central_buffer),
    }
    gross = max(0.0, on_hand) + inbound_usable
    total_deduct = sum(deductions.values())
    atp = max(0.0, gross - total_deduct)
    return {
        "on_hand": max(0.0, on_hand),
        "inbound": max(0.0, inbound),
        "inbound_alpha": inbound_alpha,
        "inbound_usable": inbound_usable,
        "gross_available": gross,
        "deductions": deductions,
        "total_deduct": total_deduct,
        "atp": atp,
    }


def parse_channels(spec: str | None) -> Dict[str, float]:
    """Parse 'amazon_mfn=0.12,shopify=0.05' → {name: buffer_pct}."""
    if not spec:
        return {}
    out: Dict[str, float] = {}
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            raise ValueError(f"Channel buffer must be name=pct, got: {part}")
        name, pct = part.split("=", 1)
        out[name.strip()] = float(pct.strip())
    return out


def channel_publish(atp: float, buffers: Dict[str, float], caps: Dict[str, float] | None = None) -> Dict[str, float]:
    caps = caps or {}
    pub = {}
    for name, buf in buffers.items():
        buf = max(0.0, min(0.95, buf))
        qty = math.floor(max(0.0, atp) * (1.0 - buf))
        if name in caps:
            qty = min(qty, int(caps[name]))
        pub[name] = float(qty)
    return pub


def main():
    p = argparse.ArgumentParser(description="ATP calculator for shared multi-channel inventory")
    p.add_argument("--on-hand", type=float, required=True, help="Sellable on-hand at hub/local warehouse")
    p.add_argument("--inbound", type=float, default=0.0, help="In-transit units")
    p.add_argument(
        "--inbound-alpha",
        type=float,
        default=0.0,
        help="Fraction of inbound counted as usable (0–1, default 0 = exclude)",
    )
    p.add_argument("--committed", type=float, default=0.0, help="Unshipped committed orders")
    p.add_argument("--reserves", type=float, default=0.0, help="Wholesale/pre-order/promo reserves")
    p.add_argument("--quality-hold", type=float, default=0.0, help="QC / quarantine units")
    p.add_argument(
        "--fba-dedicated",
        type=float,
        default=0.0,
        help="Ring-fenced FBA stock + FBA inbound (not shareable)",
    )
    p.add_argument("--central-buffer", type=float, default=0.0, help="Central safety buffer held from all channels")
    p.add_argument(
        "--channel",
        default=None,
        help="Channel buffers name=pct comma list, e.g. amazon_mfn=0.12,shopify=0.05,tiktok=0.15",
    )
    args = p.parse_args()

    result = compute_atp(
        on_hand=args.on_hand,
        inbound=args.inbound,
        inbound_alpha=args.inbound_alpha,
        committed=args.committed,
        reserves=args.reserves,
        quality_hold=args.quality_hold,
        fba_dedicated=args.fba_dedicated,
        central_buffer=args.central_buffer,
    )

    print("=" * 56)
    print("ATP CALCULATOR (shared pool)")
    print("=" * 56)
    print(f"On-hand:           {result['on_hand']:,.1f}")
    print(f"Inbound:           {result['inbound']:,.1f}  (alpha={result['inbound_alpha']:.2f})")
    print(f"Inbound usable:    {result['inbound_usable']:,.1f}")
    print(f"Gross available:   {result['gross_available']:,.1f}")
    print("-" * 56)
    for k, v in result["deductions"].items():
        print(f"  − {k:<16} {v:,.1f}")
    print(f"  − {'TOTAL':<16} {result['total_deduct']:,.1f}")
    print("-" * 56)
    print(f"ATP:               {result['atp']:,.1f}")
    print("=" * 56)

    buffers = parse_channels(args.channel)
    if buffers:
        pub = channel_publish(result["atp"], buffers)
        print("Channel publish suggestions (floor ATP × (1−buffer)):")
        for name, qty in pub.items():
            print(f"  {name:<16} buffer={buffers[name]:.0%}  →  {qty:,.0f}")
        print("=" * 56)
        print("Note: publish quantities may overlap across channels;")
        print("real-time center deduct + buffers prevent oversell.")
    else:
        print("Tip: pass --channel amazon_mfn=0.12,shopify=0.05 to see publish qty")


if __name__ == "__main__":
    main()
