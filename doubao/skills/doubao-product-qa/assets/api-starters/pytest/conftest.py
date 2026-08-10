import json
import os
from pathlib import Path

import httpx
import pytest


@pytest.fixture(scope="session")
def manifest():
    return json.loads(Path("api-operations.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def base_url():
    value = os.getenv("QA_BASE_URL", "").rstrip("/")
    if not value:
        pytest.skip("未设置 QA_BASE_URL；不从接口文档自动连接未知环境")
    return value


@pytest.fixture(scope="session")
def client(base_url):
    verify = os.getenv("QA_TLS_VERIFY", "1") == "1"
    with httpx.Client(base_url=base_url, verify=verify, timeout=30.0, follow_redirects=False) as value:
        yield value
