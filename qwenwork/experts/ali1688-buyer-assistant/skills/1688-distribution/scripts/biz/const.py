#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
业务常量配置

此文件包含用户可修改的配置项。
"""

import os

# ── API 网关地址 ─────────────────────────────────────────────────────────────

# 优先从环境变量读取，读不到则使用默认值
BASE_URL = os.environ.get("BASE_URL", "https://skills-gateway.1688.com")

# 备选网关地址：
# 站内网关（需连接内网）
#   生产: https://1688gateway.alibaba-inc.com
# 站外网关（公网可访问）
#   生产: https://skills-gateway.1688.com
