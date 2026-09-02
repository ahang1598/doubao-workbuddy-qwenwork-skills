#!/usr/bin/env python3
"""
下载风险清单脚本

下载合同风险清单文档。
环境变量:
  RICHEEAI_TOKEN    - 认证 Token（由 RicheeAI 自动注入）
  RICHEEAI_API_BASE - API 基础域名（由 RicheeAI 自动注入）
  HTTP_PROXY / HTTPS_PROXY - 代理设置（可选）
"""

import json
import os
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from proxy_utils import get_auth_token, get_api_base_url, make_request


def download_risk_list(contract_id: str, save_path: str) -> dict:
    """
    下载风险清单

    Args:
        contract_id: 合同ID
        save_path: 保存路径

    Returns:
        dict: 下载结果
    """
    token = get_auth_token()
    if not token:
        return {"success": False, "error": "未找到认证 Token"}

    base_url = get_api_base_url()
    endpoint = "/claw/contract/downloadResultRiskList"
    params = {"contractId": contract_id}
    url = f"{base_url}{endpoint}?{urllib.parse.urlencode(params)}"

    headers = {
        "richee-token": token,
        "User-Agent": "Mozilla/5.0 RicheeAI/1.0",
        "Accept": "*/*",
    }

    result = make_request(url, headers, method="GET", timeout=120, return_response=True)

    # 如果返回的是错误字典，直接返回
    if isinstance(result, dict):
        return result

    # result 是 (content, response) 元组
    content, response = result

    # 从响应头获取文件名和类型
    content_disp = response.headers.get("Content-Disposition", "")
    content_type = response.headers.get("Content-Type", "")

    # 尝试从 Content-Disposition 提取文件名
    filename = "风险清单"
    if "filename=" in content_disp:
        import re
        match = re.search(r'filename[*]?=["\']?([^"\';\s]+)', content_disp)
        if match:
            filename = match.group(1)
            # 处理 URL 编码的文件名
            if filename.startswith("UTF-8''"):
                filename = urllib.parse.unquote(filename[7:])

    # 如果文件名没有扩展名，根据 Content-Type 添加
    if "." not in filename:
        if "excel" in content_type or "spreadsheet" in content_type:
            filename += ".xlsx"
        elif "csv" in content_type:
            filename += ".csv"
        else:
            filename += ".xlsx"  # 默认 xlsx

    # 确定保存路径
    if os.path.isdir(save_path):
        save_path = os.path.join(save_path, filename)

    # 写入文件
    try:
        with open(save_path, "wb") as f:
            f.write(content)
        return {"success": True, "file": save_path, "size": len(content), "filename": filename}
    except Exception as e:
        return {"success": False, "error": f"写入文件失败: {str(e)}"}


def main():
    if len(sys.argv) < 3:
        print(json.dumps({
            "success": False,
            "error": "参数不足",
            "usage": "python download_risk_list.py <contractId> <保存路径>"
        }, ensure_ascii=False))
        sys.exit(1)

    contract_id = sys.argv[1].strip()
    save_path = sys.argv[2].strip()

    if not contract_id or not save_path:
        print(json.dumps({"success": False, "error": "参数不能为空"}, ensure_ascii=False))
        sys.exit(1)

    result = download_risk_list(contract_id, save_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
