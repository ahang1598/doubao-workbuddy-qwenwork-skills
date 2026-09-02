#!/usr/bin/env python3
"""
法律在线检索脚本

调用内部 API 搜索相关法律案例。
环境变量:
  RICHEEAI_TOKEN - 认证 Token（由 RicheeAI 自动注入）
  RICHEEAI_API_BASE - API 基础域名（由 RicheeAI 自动注入）
  HTTP_PROXY / HTTPS_PROXY - 代理设置（可选）
"""

import json
import os
import ssl
import sys
import urllib.parse
import urllib.request
from urllib.error import HTTPError, URLError


def get_proxy_handler():
    """
    获取代理处理器，仅使用环境变量中的代理设置
    不读取系统代理，避免代理软件关闭后残留注册表配置导致 Connection Refused

    Returns:
        urllib.request.OpenerDirector: 配置好的 opener
    """
    http_proxy = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
    https_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")

    proxy_handlers = []
    if http_proxy:
        proxy_handlers.append(
            urllib.request.ProxyHandler({"http": http_proxy})
        )
    if https_proxy:
        proxy_handlers.append(
            urllib.request.ProxyHandler({"https": https_proxy})
        )

    if proxy_handlers:
        opener = urllib.request.build_opener(*proxy_handlers)
    else:
        opener = urllib.request.build_opener()

    return opener


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


def search_web(search_content, days=None):
    """
    调用法大大专用在线检索 API

    Args:
        search_content: 搜索关键词
        days: 时间范围（可选）。0=不限, 1=1天内, 7=1周内, 30=1个月内, 365=1年内

    Returns:
        dict: API 响应结果
    """
    base_url = get_api_base_url()

    token = get_auth_token()
    # 构建 API URL
    endpoint = "/claw/searchTool/web"
    params = {"searchContent": search_content}
    if days is not None and days != 0:
        params["days"] = days
    url = f"{base_url}{endpoint}?{urllib.parse.urlencode(params)}"

    # 创建请求
    headers = {
        "richee-token": token,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 RicheeAI/1.0",
        "Accept": "application/json",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    req = urllib.request.Request(url, headers=headers, method="POST")

    # 获取配置好代理的 opener
    opener = get_proxy_handler()

    # 配置 SSL
    ssl_context = ssl.create_default_context()

    try:
        # 使用 opener 发送请求
        https_handler = urllib.request.HTTPSHandler(context=ssl_context)
        opener.add_handler(https_handler)
        with opener.open(req, timeout=180) as response:
            data = response.read().decode("utf-8")
            result = json.loads(data)
            return result
    except HTTPError as e:
        error_body = e.read().decode("utf-8") if hasattr(e, "read") else str(e)
        return {
            "success": False,
            "error": f"HTTP 错误 {e.code}: {error_body}",
            "searchContent": search_content,
        }
    except URLError as e:
        return {
            "success": False,
            "error": f"请求失败: {str(e.reason)}",
            "searchContent": search_content,
        }
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "error": f"JSON 解析错误: {str(e)}",
            "searchContent": search_content,
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"未知错误: {str(e)}",
            "searchContent": search_content,
        }


def fetch_webpage_content(url: str) -> str:
    """
    使用 r.jina.ai 抓取网页内容

    Args:
        url: 网页URL

    Returns:
        网页内容的Markdown格式文本
    """
    jina_url = f"https://r.jina.ai/{url}"

    try:
        req = urllib.request.Request(
            jina_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            },
        )

        # 获取配置好代理的 opener
        opener = get_proxy_handler()
        ssl_context = ssl.create_default_context()
        https_handler = urllib.request.HTTPSHandler(context=ssl_context)
        opener.add_handler(https_handler)

        with opener.open(req, timeout=90) as response:
            return response.read().decode("utf-8")

    except URLError as e:
        return f"抓取失败: {str(e)}"
    except Exception as e:
        return f"抓取失败: {str(e)}"


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="法大大网络搜索工具")
    parser.add_argument("query", nargs="?", help="搜索查询字符串（使用--fetch时可选）")
    parser.add_argument("--fetch", metavar="URL", help="抓取指定URL的内容")
    parser.add_argument("--days", type=int, choices=[0, 1, 7, 30, 365],
                        help="时间范围过滤(0=不限, 1=1天内, 7=1周内, 30=1个月内, 365=1年内)")
    args = parser.parse_args()

    # 如果指定了抓取URL
    if args.fetch:
        content = fetch_webpage_content(args.fetch)
        print(content)
        return

    # 执行搜索（需要query参数）
    if not args.query:
        parser.error("需要提供查询字符串或使用 --fetch 参数")

    result = search_web(args.query, days=args.days)
    # 输出结果
    print(result)


if __name__ == "__main__":
    main()
