#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""自动打开脱敏工具页面（调用系统默认浏览器）。

仅执行"启动浏览器加载本地页面"这一个动作：
不读取、不解析、不输出任何用户文件内容；无网络请求。
在云端/无桌面环境运行时打开会失败并明确报错，此时 agent 应改为把工具路径交给用户手动打开。
"""
import os
import sys
import webbrowser
from pathlib import Path

def main():
    here = os.path.dirname(os.path.abspath(__file__))
    page = os.path.abspath(os.path.join(here, "..", "assets", "redaction-studio.html"))
    if not os.path.isfile(page):
        print(f"[FAIL] 工具页面不存在: {page}")
        return 3
    url = Path(page).as_uri()  # 中文/空格路径必须百分号编码，否则部分浏览器打不开
    try:
        ok = webbrowser.open(url, new=2, autoraise=True)
    except Exception as e:
        print(f"[FAIL] 无法调用浏览器（{e}）。请让用户手动打开: {page}")
        return 3
    if ok:
        print(f"[OK] 已尝试在默认浏览器打开工具页面: {page}")
        print("若用户表示页面没有弹出（常见于云端/无桌面环境），请把上面的路径交给用户手动打开。")
        return 0
    print(f"[FAIL] 系统未返回成功。请让用户手动打开: {page}")
    return 3

if __name__ == "__main__":
    sys.exit(main())
