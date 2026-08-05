#!/usr/bin/env python3
"""店铺核心指标同行对比及趋势数据查询 CLI 入口"""

import os
import sys
import argparse

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..')))

from _auth import get_ak_from_env
from _output import make_output, print_output, print_error

from capabilities.get_core_metrics.service import get_core_metrics

COMMAND_NAME = "get_core_metrics"
COMMAND_DESC = "获取店铺核心指标同行对比及趋势数据"

def main():
    ak_id, _ = get_ak_from_env()
    if not ak_id:
        print_output(make_output(
            success=False,
            markdown="❌ AK 未配置，无法查询核心指标。\n\n运行: `cli.py configure YOUR_AK`",
            data={"data": {}},
        ))
        return

    parser = argparse.ArgumentParser(description="店铺核心指标同行对比及趋势数据查询")
    parser.add_argument("--date_type", "-d", default="RECENT_7",
                        choices=["RECENT_1", "RECENT_7", "RECENT_30"],
                        help="日期类型: RECENT_1(近1天) / RECENT_7(近7天,默认) / RECENT_30(近30天)")
    args = parser.parse_args()

    try:
        result = get_core_metrics(args.date_type)
        print_output(make_output(
            success=True,
            markdown="核心指标查询成功",
            data={"data": result},
        ))
    except Exception as e:
        print_error(e, {"data": {}})

if __name__ == "__main__":
    main()
