#!/usr/bin/env python3
"""
慈善中国备案详情查询工具（alert-record-forms 显式链接路径）。

本模块仅由 run_record_ui.py 在用户已提供有效链接并明确选择查询时内部导入。
Agent 禁止通过 execute_command 单独运行本文件，也不得生成慈善中国结果中间文件。
LLM 视觉低置信度、字段缺失或识别不确定本身均不是查询条件。

下方 CLI 仅保留开发调试兼容，不属于 Skill 业务流程。

代码调用:
    from fetch_charity_record import fetch_and_parse, extract_page_id_from_url
    page_id = extract_page_id_from_url("https://cszg.mca.gov.cn/biz/ma/csmh/c/csmhcdetailmj.html?id=xxxx")
    result = fetch_and_parse(page_id)
"""

import json
import os
import re
import sys
import urllib.parse

import requests

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "_common")))
from mcp_client import CALLER_EXPERT_ID  # noqa: E402
from observe_bootstrap import observe_entrypoint  # noqa: E402

BASE_URL = "https://cszg.mca.gov.cn"
DETAIL_PATH = "/biz/ma/csmh/c/csmhcdetailmj.html"

MOBILE_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) "
        "Version/16.0 Mobile/15E148 Safari/604.1"
    ),
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
}

INPUT_MAP = {
    "aaex9103": "scheme_name",
    "aaex9102": "scheme_no",
    "aaex9104": "purpose_of_donation",
    "aaex9105": "start_date",
    "aaex9106": "end_date",
    "aaex9111": "recipient_scope",
    "aaex9171": "recipient_num",
    "aaex9172": "recipient_confirm_method",
    "aaex9173": "fundras_target",
    "aaex9112": "purpose_use",
    "aaex9174": "recipient_funding_desc",
    "aaex9175": "implement_desc",
    "aaex9176": "manage_cost_desc",
    "aaex9113": "fundraising_cost",
    "aaex9114": "remain_assets_desc",
    "aaex9150": "partner_name",
    "aaex9151": "partner_credit_code",
    # aaex9153/aaex9154 为合作方负责人姓名/身份证号，业务体不使用，禁止提取和输出。
    "aaex9167": "partner_type",
    "aaex9101": "org_name",
    "aaex9131": "filing_date",
    "aaex9116": "unified_social_credit_code",
    "aaex9115": "legal_representative",
}


def _build_session():
    s = requests.Session()
    s.headers.update(MOBILE_HEADERS)
    return s


def _fetch_detail_html(session: requests.Session, page_id: str) -> str:
    resp = session.get(
        BASE_URL + DETAIL_PATH,
        params={"id": page_id, "flag": "1"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.text


_SENSITIVE_INPUT_NAMES = {"aaex9153", "aaex9154"}


def _extract_inputs(html: str) -> dict:
    fields = {}
    for match in re.finditer(
        r'<(?:input|textarea|select)\s[^>]*\bname\s*=\s*"([^"]+)"'
        r'[^>]*\bvalue\s*=\s*"([^"]*)"',
        html, re.IGNORECASE,
    ):
        name = match.group(1)
        if name in _SENSITIVE_INPUT_NAMES:
            continue
        fields[name] = match.group(2).strip()
    return fields

_LABEL_KEYWORDS = [
    (("慈善组织名称", "慈善组织全称", "组织名称", "社会组织名称"), "org_name", "text"),
    (("统一社会信用代码", "组织机构代码"), "unified_social_credit_code", "text"),
    (("法定代表人",), "legal_representative", "text"),
]

# 占位值
_PLACEHOLDER_VALUES = {"-", "—", "无", "/", ""}

_LABEL_VAL_PAIR_RE = re.compile(
    r'<div[^>]*class\s*=\s*"[^"]*\btable-lable\b[^"]*"[^>]*>\s*'
    r'(?P<label>[^<]{1,80}?)\s*</div>'
    r'.*?'  # 跨过中间 </td><td> 等
    r'<div[^>]*class\s*=\s*"[^"]*\btable-val(?:-long)?\b[^"]*"[^>]*>'
    r'(?P<val>.*?)</div>',
    re.IGNORECASE | re.DOTALL,
)


def _clean_val(raw_val: str) -> str:
    if not raw_val:
        return ""
    m = re.search(
        r'<input[^>]*\bvalue\s*=\s*"([^"]*)"',
        raw_val,
        re.IGNORECASE,
    )
    if m:
        return m.group(1).strip()
    text = re.sub(r'<[^>]+>', '', raw_val)
    text = re.sub(r'\s+', '', text)
    return text.strip()


def _extract_text_fields(html: str) -> dict:
    out: dict = {}
    pairs = []
    for m in _LABEL_VAL_PAIR_RE.finditer(html):
        label = m.group("label").strip()
        val = _clean_val(m.group("val"))
        if not label or not val:
            continue
        if val in _PLACEHOLDER_VALUES:
            continue
        pairs.append((label, val))

    for keywords, form_key, _mode in _LABEL_KEYWORDS:
        if form_key in out:
            continue
        for label, val in pairs:
            if any(kw in label for kw in keywords):
                out[form_key] = val
                break

    if "org_name" not in out:
        for kw in ("慈善组织名称", "慈善组织全称", "社会组织名称"):
            plain = re.search(
                re.escape(kw) + r'\s*[:：]\s*([^\s<，,；;]{2,80})',
                html,
            )
            if plain:
                v = plain.group(1).strip()
                if v and v not in _PLACEHOLDER_VALUES:
                    out["org_name"] = v
                    break

    return out


def _extract_support_project(html: str) -> str:
    m = re.search(
        r'class="table-val-long"[^>]*>\s*'
        r'([\u4e00-\u9fa5a-zA-Z0-9]+[-_]\s*[\u4e00-\u9fa5].*?)'
        r'(&nbsp;|\s)*<input[^>]*name="aaex8102"',
        html, re.DOTALL,
    )
    if m:
        raw = m.group(1).strip()
        return re.sub(r'^[A-Za-z0-9]{22,24}[-_]\s*', '', raw)
    return ""


def _parse_offsite(html: str) -> int:
    m = re.search(
        r'<input[^>]*\bname\s*=\s*"aaex9132"[^>]*\bchecked[^>]*'
        r'\bvalue\s*=\s*"([^"]*)"',
        html, re.IGNORECASE,
    )
    if m:
        return 1 if m.group(1) == "1" else 2

    parts = re.split(r'<!--|-->', html)
    for i in range(0, len(parts), 2):
        if 'aaex9132' in parts[i] and 'checked' in parts[i].lower():
            m2 = re.search(r'value="([01])"[^>]*checked', parts[i], re.IGNORECASE)
            if m2:
                return 1 if m2.group(1) == "1" else 2

    return 2  # 默认否


def _parse_has_partner(inputs: dict) -> bool:
    keys = ["aaex9150", "aaex9151", "aaex9167"]
    return any(inputs.get(key, "") for key in keys)


def _normalize_partner_type(val: str):
    if val in ("1", "2"):
        return int(val)
    return None

def fetch_and_parse(page_id: str) -> dict:
    session = _build_session()
    html = _fetch_detail_html(session, page_id)
    inputs = _extract_inputs(html)

    result = {}
    for raw_name, form_name in INPUT_MAP.items():
        val = inputs.get(raw_name, "")
        if val:
            result[form_name] = val

    text_fields = _extract_text_fields(html)
    for k, v in text_fields.items():
        result.setdefault(k, v)

    result["support_project"] = _extract_support_project(html)
    result["offsite_fundraising"] = _parse_offsite(html)

    has_p = _parse_has_partner(inputs)
    result["has_partner"] = 1 if has_p else 2
    if has_p:
        raw_pt = result.pop("partner_type", "")
        pt = _normalize_partner_type(raw_pt)
        if pt is not None:
            result["partner_type"] = pt
    else:
        result.pop("partner_type", None)

    return result

def extract_page_id_from_url(url: str):
    if not url or not isinstance(url, str):
        return None
    try:
        parsed = urllib.parse.urlparse(url.strip())
        if parsed.scheme not in ("http", "https"):
            return None
        if (parsed.hostname or "").lower() != "cszg.mca.gov.cn":
            return None
        if "csmhcdetail" not in parsed.path.lower():
            return None
        qs = urllib.parse.parse_qs(parsed.query)
    except Exception:  # noqa: BLE001
        return None
    ids = qs.get("id") or []
    page_id = str(ids[0]).strip() if ids else ""
    return page_id or None


def merge_org_name_from_user_text(
    charity_data,
    user_text,
):
    if not user_text or not isinstance(user_text, str):
        return charity_data

    patterns = [
        r'慈善组织名称\s*[:：]\s*([^\s\n，,；;]{2,80})',
        r'慈善组织全称\s*[:：]\s*([^\s\n，,；;]{2,80})',
        r'社会组织名称\s*[:：]\s*([^\s\n，,；;]{2,80})',
        r'组织名称\s*[:：]\s*([^\s\n，,；;]{2,80})',
        r'机构名称\s*[:：]\s*([^\s\n，,；;]{2,80})',
    ]
    extracted = None
    for p in patterns:
        m = re.search(p, user_text)
        if m:
            extracted = m.group(1).strip()
            break

    if not extracted:
        return charity_data

    out = dict(charity_data) if isinstance(charity_data, dict) else {}
    if not out.get("org_name"):
        out["org_name"] = extracted

    if not out.get("unified_social_credit_code"):
        m_uscc = re.search(r'\b([0-9A-Z]{18})\b', user_text)
        if m_uscc:
            out["unified_social_credit_code"] = m_uscc.group(1)
    return out


def _main():
    # 取第一个非 -- 开头的参数作为入参（慈善中国详情页链接）
    positional = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not positional or not str(positional[0]).strip():
        print(json.dumps(
            {"success": False, "error_code": "missing_url",
             "message": "缺少慈善中国详情页链接入参"},
            ensure_ascii=False,
        ))
        sys.exit(1)

    url = str(positional[0]).strip()
    page_id = extract_page_id_from_url(url)
    if not page_id:
        print(json.dumps(
            {"success": False, "error_code": "invalid_url",
             "message": "无法从链接解析出页面ID，请确认是慈善中国详情页链接"},
            ensure_ascii=False,
        ))
        sys.exit(1)

    result = fetch_and_parse(page_id)
    result["success"] = True
    result["_source"] = "charity_china"
    result["_schema_version"] = "1.0"
    result["_page_id"] = page_id
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main():
    observe_entrypoint(CALLER_EXPERT_ID, "alert.fetch_charity_record", "fetch_charity_record", _main)


if __name__ == "__main__":
    main()
