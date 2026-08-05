#!/usr/bin/env python3
"""客户画像数据查询 CLI 入口"""

import os
import sys
import argparse

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), '..', '..')))

from _auth import get_ak_from_env
from _output import make_output, print_output, print_error

from capabilities.get_customer_profile.service import get_customer_profile

COMMAND_NAME = "get_customer_profile"
COMMAND_DESC = "获取客户画像数据"

def main():
    ak_id, _ = get_ak_from_env()
    if not ak_id:
        print_output(make_output(
            success=False,
            markdown="❌ AK 未配置，无法查询客户画像。\n\n运行: `cli.py configure YOUR_AK`",
            data={"data": {}},
        ))
        return

    parser = argparse.ArgumentParser(description="客户画像数据查询")
    parser.add_argument("--date_type", "-d", default="RECENT_7",
                        choices=["RECENT_1", "RECENT_7", "RECENT_30"],
                        help="日期类型: RECENT_1(近1天) / RECENT_7(近7天,默认) / RECENT_30(近30天)")
    args = parser.parse_args()

    try:
        result = get_customer_profile(args.date_type)
        print_output(make_output(
            success=True,
            markdown="客户画像查询成功",
            data={"data": result},
        ))
    except Exception as e:
        print_error(e, {"data": {}})

if __name__ == "__main__":
    main()
