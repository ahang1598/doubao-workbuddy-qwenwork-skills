#!/usr/bin/env python3
"""事件纳入判定 + 单期净收益计算（确定性，无随机、无联网、不写文件）。

输入：事件列表 JSON（数组）。每个事件的字段：

    name         str    事件标识，必填
    in_universe  bool   信号日是否在**历史**股票池内（不是当前池），必填
    buy_open     num    买入价，必须 > 0
    sell_close   num    卖出价，必须 >= 0
    buyable      bool   买入日是否可成交，缺省 true

输出：与输入等长的数组，逐事件给出

    included=false 时  reason ∈ {not_in_point_in_time_universe, buy_open_unavailable}
    included=true  时  buy_cost / sell_proceeds / net_return

成本口径**二选一，必须给且只能给一个**：

    --cost R            单边成本，买入侧加 R、卖出侧扣 R，一次往返实际收 2R
    --round-trip-cost R 一次往返合计成本，内部按 R/2 分摊到两侧

    两者都取 [0, 1)，换算关系 `--round-trip-cost` = 2 × `--cost`。
    题设给「双边合计」用前者，给「单边」用后者，结果等价。
    ⚠ 把「双边合计」直接传给 `--cost` 会把成本收成两倍——这正是
    references/backtest-contract.md 点名的成本口径错误。

空数组合法，输出 `[]`。

    python3 event_backtest.py events.json --cost 0.01
    python3 event_backtest.py events.json --round-trip-cost 0.02   # 与上一行等价
"""
from __future__ import annotations
import argparse
import json
import math
from dataclasses import dataclass

FIELDS = {"name", "in_universe", "buy_open", "sell_close", "buyable"}
REQUIRED = {"name", "in_universe", "buy_open", "sell_close"}


@dataclass
class Event:
    name: str
    in_universe: bool
    buy_open: float
    sell_close: float
    buyable: bool = True


def _num(v, where, *, positive=False):
    """取一个有限实数。NaN/inf 一律拒绝——它们会一路算到净收益里不报错。"""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise ValueError(f"{where} 必须是数字，收到 {type(v).__name__}")
    v = float(v)
    if not math.isfinite(v):
        raise ValueError(f"{where} 必须是有限数值，收到 {v}")
    if positive and v <= 0:
        raise ValueError(f"{where} 必须 > 0，收到 {v}")
    if not positive and v < 0:
        raise ValueError(f"{where} 不能为负，收到 {v}")
    return v


def parse_events(data) -> list[Event]:
    if not isinstance(data, list):
        raise ValueError(f"输入必须是事件数组，收到 {type(data).__name__}")
    out = []
    for i, x in enumerate(data):
        where = f"第 {i} 个事件"
        if not isinstance(x, dict):
            raise ValueError(f"{where} 必须是对象，收到 {type(x).__name__}")
        missing = REQUIRED - set(x)
        if missing:
            raise ValueError(f"{where} 缺字段 {sorted(missing)}")
        unknown = set(x) - FIELDS
        if unknown:
            raise ValueError(f"{where} 有未知字段 {sorted(unknown)}；已知字段 {sorted(FIELDS)}")
        for k in ("in_universe", "buyable"):
            if k in x and not isinstance(x[k], bool):
                raise ValueError(f"{where} 的 {k} 必须是 true/false，收到 {x[k]!r}")
        out.append(Event(
            name=str(x["name"]),
            in_universe=x["in_universe"],
            # 买入价为 0 会让净收益除零；卖出价可以是 0（退市清零），但不能为负
            buy_open=_num(x["buy_open"], f"{where} 的 buy_open", positive=True),
            sell_close=_num(x["sell_close"], f"{where} 的 sell_close"),
            buyable=x.get("buyable", True)))
    return out


def evaluate(events: list[Event], one_way_cost: float) -> list[dict]:
    rows = []
    for e in events:
        if not e.in_universe:
            rows.append({"name": e.name, "included": False,
                         "reason": "not_in_point_in_time_universe"})
            continue
        if not e.buyable:
            rows.append({"name": e.name, "included": False,
                         "reason": "buy_open_unavailable"})
            continue
        gross_buy = e.buy_open * (1 + one_way_cost)
        net_sell = e.sell_close * (1 - one_way_cost)
        rows.append({"name": e.name, "included": True, "buy_cost": gross_buy,
                     "sell_proceeds": net_sell, "net_return": net_sell / gross_buy - 1})
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("input", help="事件列表 JSON 文件")
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--cost", type=float,
                   help="单边成本，取 [0, 1)：买入侧加、卖出侧扣，一次往返实际收 2 倍")
    g.add_argument("--round-trip-cost", type=float, dest="round_trip_cost",
                   help="一次往返合计成本，取 [0, 1)，内部按一半分摊到两侧。"
                        "题设写「双边合计」用这个")
    a = p.parse_args()
    # 题设的「双边合计」是一次往返的总数，折到单边要除以 2。
    # 直接把它当单边传会把成本收成两倍——backtest-contract.md 点名的那个错。
    if a.round_trip_cost is not None:
        if not (math.isfinite(a.round_trip_cost) and 0 <= a.round_trip_cost < 1):
            p.error(f"--round-trip-cost 必须在 [0, 1) 内，收到 {a.round_trip_cost}")
        a.cost = a.round_trip_cost / 2
    # 负成本会让买价变低、卖价变高，凭空造出收益；>=1 则卖出所得归零或为负
    elif not (math.isfinite(a.cost) and 0 <= a.cost < 1):
        p.error(f"--cost 必须在 [0, 1) 内，收到 {a.cost}")
    try:
        with open(a.input, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        p.error(f"找不到输入文件 {a.input}")
    except json.JSONDecodeError as e:
        p.error(f"{a.input} 不是合法 JSON：第 {e.lineno} 行第 {e.colno} 列 {e.msg}")
    try:
        events = parse_events(data)
    except ValueError as e:
        p.error(str(e))
    print(json.dumps(evaluate(events, a.cost), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
