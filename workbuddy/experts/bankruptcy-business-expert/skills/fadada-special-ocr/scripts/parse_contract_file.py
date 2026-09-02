#!/usr/bin/env python3
"""
合同文件解析脚本

上传本地 PDF 或图片文件到服务端进行 OCR 解析。
支持多文件同时上传。
环境变量:
  RICHEEAI_TOKEN    - 认证 Token（由 RicheeAI 自动注入）
  RICHEEAI_API_BASE  - API 基础域名（由 RicheeAI 自动注入）
"""

import json
import os
import ssl
import sys
import urllib.request


def get_auth_token():
    """从环境变量获取认证 Token"""
    token = os.environ.get("RICHEEAI_TOKEN")
    if not token:
        print(
            json.dumps(
                {
                    "success": False,
                    "error": "未找到认证 Token。请确保在 RicheeAI cowork 会话中运行此脚本。",
                },
                ensure_ascii=False,
            )
        )
        sys.exit(1)
    return token


def get_api_base_url():
    """从环境变量获取 API 基础域名，默认使用生产环境"""
    return os.environ.get("RICHEEAI_API_BASE", "https://claw.richee.cn/claw-api")


def get_file_type(file_path: str) -> str:
    """根据文件扩展名判断文件类型"""
    ext = os.path.splitext(file_path)[1].lower()
    type_map = {".pdf": "pdf", ".png": "png", ".jpg": "jpg", ".jpeg": "jpeg"}
    return type_map.get(ext, "pdf")


def parse_file(file_path: str) -> dict:
    """
    上传单个文件并解析

    Args:
        file_path: 待解析文件的本地路径

    Returns:
        dict: API 响应结果
    """

    base_url = get_api_base_url()
    if base_url.find("https://claw.richee.cn") == -1:
        print(f"请求内部地址{base_url}")

    token = get_auth_token()
    endpoint = "/claw/contractFile/parseFile"
    url = f"{base_url}{endpoint}"
    headers = {
        "richee-token": token,
        "User-Agent": "RicheeAI-FadadaSearch/1.0",
    }

    # 读取文件内容
    try:
        with open(file_path, "rb") as f:
            file_content = f.read()
    except FileNotFoundError:
        return {
            "success": False,
            "error": f"文件不存在: {file_path}",
            "file": file_path,
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"读取文件失败: {str(e)}",
            "file": file_path,
        }

    file_name = os.path.basename(file_path)
    file_type = get_file_type(file_path)

    # 构造 multipart/form-data 请求体
    boundary = "----FormBoundary7MA4YWxkTrZu0gW"
    body_parts = []

    # 文件字段（二进制文件内容）
    body_parts.append(
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="files"; filename="{file_name}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    )
    body_parts.append(file_content)
    body_parts.append(b"\r\n")

    # 其他字段（fileType）
    body_parts.append(
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="fileType"\r\n\r\n'
        f"{file_type}\r\n"
    )

    body_parts.append(f"--{boundary}--\r\n")

    # 合并 body（先将字符串部分编码为 bytes）
    merged = []
    for part in body_parts:
        if isinstance(part, str):
            merged.append(part.encode("utf-8"))
        else:
            merged.append(part)
    body = b"".join(merged)

    req = urllib.request.Request(
        url,
        data=body,
        headers=headers,
        method="POST",
    )
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")

    # 配置 SSL
    ssl_context = ssl.create_default_context()

    try:
        with urllib.request.urlopen(req, context=ssl_context, timeout=300) as response:
            data = response.read().decode("utf-8")
            result = json.loads(data)
            return {
                "success": True,
                "file": file_path,
                "data": result,
            }
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if hasattr(e, "read") else str(e)
        return {
            "success": False,
            "error": f"HTTP 错误 {e.code}: {error_body}",
            "file": file_path,
        }
    except urllib.error.URLError as e:
        return {
            "success": False,
            "error": f"请求失败: {str(e.reason)}",
            "file": file_path,
        }
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "error": f"响应 JSON 解析错误: {str(e)}",
            "file": file_path,
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"未知错误: {str(e)}",
            "file": file_path,
        }


def parse_files(file_paths: list) -> dict:
    """
    上传多个文件并解析

    Args:
        file_paths: 待解析文件的本地路径列表

    Returns:
        dict: 汇总结果
    """
    results = []
    all_success = True

    for file_path in file_paths:
        result = parse_file(file_path)
        results.append(result)
        if not result.get("success", False):
            all_success = False

    return {
        "success": all_success,
        "total": len(file_paths),
        "results": results,
    }


def main():
    if len(sys.argv) < 2:
        print(
            json.dumps(
                {
                    "success": False,
                    "error": "请提供待解析的文件路径。用法: python parse_contract_file.py <file1.pdf> [file2.png ...]",
                },
                ensure_ascii=False,
            )
        )
        sys.exit(1)

    file_paths = [p.strip() for p in sys.argv[1:] if p.strip()]
    if not file_paths:
        print(
            json.dumps(
                {"success": False, "error": "文件路径不能为空"},
                ensure_ascii=False,
            )
        )
        sys.exit(1)

    # 单文件直接返回结构，多文件返回汇总
    if len(file_paths) == 1:
        result = parse_file(file_paths[0])
    else:
        result = parse_files(file_paths)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
