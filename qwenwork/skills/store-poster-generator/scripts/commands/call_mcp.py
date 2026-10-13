#!/usr/bin/env python3
"""
盒创社生图 MCP 工具调用脚本

用法：
    uv run python call_mcp.py <*subskillname> list
    uv run python call_mcp.py <*subskillname> call <tool_name> --params '{"key": "value"}'
"""

import argparse
import json
import os
import sys
import uuid
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

DISABLED = False

def load_mcp_config():
    """从技能目录加载 mcp-config.json，返回完整配置字典"""
    config_path = Path(__file__).parent.parent.parent / "mcp-config.json"
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def get_mcp_url_by_subskillname(subskillname, key=None):
    """根据 subskillname 从 AGENT_WORK_ROOT/workspace/.runtime-config/{subskillname}/mcp-config.json 加载配置，返回指定 key 或第一个有 url 的服务地址"""
    agent_work_root = os.environ.get("AGENT_WORK_ROOT")
    if not agent_work_root:
        raise EnvironmentError("AGENT_WORK_ROOT environment variable is not set")
    config_path = Path(agent_work_root) / "workspace" / ".runtime-config" / subskillname / "mcp-config.json"
    if not config_path.exists():
        print(f"❌ 未找到 MCP 配置文件：{config_path}", file=sys.stderr)
        print(f"   请确认技能目录 .skills/{subskillname}/ 和配置文件是否存在", file=sys.stderr)
        sys.exit(1)

    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)

    if key is not None:
        if key not in config:
            print(f"❌ 配置文件中不存在指定的 key：{key}", file=sys.stderr)
            sys.exit(1)
        entry = config[key]
        if isinstance(entry, dict) and "url" in entry:
            return entry["url"]
        print(f"❌ 配置文件中 key '{key}' 没有包含 url", file=sys.stderr)
        sys.exit(1)

    for config_key, value in config.items():
        if isinstance(value, dict) and "url" in value:
            return value["url"]

    print(f"❌ 配置文件中没有包含 url 的 MCP 服务：{config_path}", file=sys.stderr)
    sys.exit(1)


def get_first_mcp_url():
    """获取配置中第一个 MCP 服务的 URL（兼容独立运行模式）"""
    config = load_mcp_config()
    for key, value in config.items():
        if isinstance(value, dict) and "url" in value:
            return value["url"], key
    return None, None


def resolve_url(url_or_var):
    """解析 URL：支持直接 URL 或 $ENV_VAR 格式"""
    if not url_or_var:
        print("❌ MCP URL 未配置", file=sys.stderr)
        print("   请先读取 mcp-config.json 确认服务 URL", file=sys.stderr)
        sys.exit(1)
    
    if url_or_var.startswith("$"):
        var_name = url_or_var[1:]
        value = os.environ.get(var_name)
        if not value:
            print(f"❌ 环境变量未设置：{var_name}", file=sys.stderr)
            sys.exit(1)
        return value
    return url_or_var


def make_jsonrpc_request(method, params=None):
    """构造 JSON-RPC 2.0 请求体"""
    request_body = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": method,
    }
    if params is not None:
        request_body["params"] = params
    return request_body


def send_mcp_request(server_url, method, params=None):
    """向 MCP Server 发送 JSON-RPC 请求"""
    body = make_jsonrpc_request(method, params)
    data = json.dumps(body).encode("utf-8")

    request = Request(
        server_url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=180) as response:
            content_type = response.headers.get("Content-Type", "")
            raw = response.read().decode("utf-8")

            if "text/event-stream" in content_type:
                return parse_sse_response(raw)
            else:
                result = json.loads(raw)
                if "error" in result:
                    print(f"❌ MCP 错误：{result['error']}", file=sys.stderr)
                    return None
                return result.get("result")
    except HTTPError as error:
        error_body = error.read().decode("utf-8", errors="replace")
        print(f"❌ HTTP {error.code} 错误：{error_body}", file=sys.stderr)
        return None
    except URLError as error:
        print(f"❌ 网络错误：{error.reason}", file=sys.stderr)
        return None
    except json.JSONDecodeError as error:
        print(f"❌ JSON 解析失败：{error}", file=sys.stderr)
        return None


def parse_sse_response(raw_text):
    """解析 SSE 格式的响应"""
    for line in raw_text.strip().split("\n"):
        line = line.strip()
        if line.startswith("data:"):
            data_str = line[5:].strip()
            if not data_str:
                continue
            try:
                data = json.loads(data_str)
                if "result" in data:
                    return data["result"]
                if "error" in data:
                    print(f"❌ MCP 错误：{data['error']}", file=sys.stderr)
                    return None
            except json.JSONDecodeError:
                continue
    print("❌ 未能从 SSE 响应中解析到结果", file=sys.stderr)
    return None


def list_tools(subskillname, server_url):
    """列出 MCP Server 的所有可用工具"""
    print(f"🔍 正在获取工具列表...  { server_url }")
    
    result = send_mcp_request(server_url, "tools/list")
    if result is None:
        return False

    tools = result.get("tools", [])
    if not tools:
        print("⚠️  该 MCP Server 没有可用的工具")
        return True
    
    print('')
    print("# 必须通过 read_file 理解 skills/<subskillname>/SKILL.md 再使用下列工具")
    print('')

    print(f"📋 共 {len(tools)} 个工具：\n")
    for tool in tools:
        name = tool.get("name", "未知")
        description = tool.get("description", "无描述")
        print(f"  🔧 {name}")
        if len(description) > 120:
            description = description[:117] + "..."
        print(f"     {description}")

        input_schema = tool.get("inputSchema", {})
        properties = input_schema.get("properties", {})
        required = input_schema.get("required", [])
        if properties:
            param_parts = []
            for param_name, param_info in properties.items():
                param_type = param_info.get("type", "any")
                is_required = "必填" if param_name in required else "可选"
                param_parts.append(f"{param_name}({param_type}, {is_required})")
            print(f"     参数: {', '.join(param_parts)}")
        print()

    return True


def call_tool(server_url, tool_name, params=None):
    """调用 MCP Server 的指定工具"""
    print(f"🚀 正在调用工具: {tool_name}")
    if params:
        print(f"   参数: {json.dumps(params, ensure_ascii=False)}")
    print()

    call_params = {
        "name": tool_name,
        "arguments": params or {},
    }

    result = send_mcp_request(server_url, "tools/call", call_params)
    if result is None:
        return False

    content_items = result.get("content", [])
    if not content_items:
        print("⚠️  工具返回了空结果")
        return True

    print("✅ 调用结果：\n")
    for item in content_items:
        item_type = item.get("type", "text")
        if item_type == "text":
            text = item.get("text", "")
            try:
                parsed = json.loads(text)
                print(json.dumps(parsed, ensure_ascii=False, indent=2))
            except (json.JSONDecodeError, TypeError):
                print(text)
        elif item_type == "image":
            print(f"[图片: {item.get('mimeType', 'unknown')}]")
        elif item_type == "resource":
            print(f"[资源: {item.get('uri', 'unknown')}]")
        else:
            print(f"[{item_type}]: {json.dumps(item, ensure_ascii=False)}")

    is_error = result.get("isError", False)
    if is_error:
        print("\n⚠️  工具执行报告了错误（见上方内容）")

    return not is_error


def register(subparsers) -> None:
    """Register the mcp subcommand into the CLI."""
    parser = subparsers.add_parser(
        "mcp",
        help="调用 subskill 的 MCP Server 工具",
        description=("""
description:
  必须通过 read_file 理解 skills/<subskillname>/SKILL.md 后使用。
  支持调用 subskill 的 MCP Server 工具（list / call）

  示例：
    uv run python scripts/cli.py mcp creative-poster-generator list
    uv run python scripts/cli.py mcp creative-poster-generator call generation_poster_by_text --params <json>"""
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "subskillname",
        help="子技能名称, 如 creative-poster-generator",
    )
    parser.add_argument(
        "action",
        choices=["list", "call"],
        help="操作类型：list 列出工具，call 调用工具",
    )
    parser.add_argument("tool", nargs="?", default=None, help="要调用的工具名称（仅 call 时需要）")
    parser.add_argument(
        "--params",
        default="{}",
        help='工具参数（JSON 格式）',
    )
    parser.set_defaults(handler=run)

def run(args) -> None:
    """Execute the call-mcp command."""
    url = get_mcp_url_by_subskillname(args.subskillname)
    resolved_url = resolve_url(url)

    if args.action == "list":
        success = list_tools(args.subskillname, resolved_url)
    elif args.action == "call":
        if not args.tool:
            print("❌ call 操作需要指定工具名称", file=sys.stderr)
            sys.exit(1)
        try:
            params = json.loads(args.params)
        except json.JSONDecodeError as error:
            print(f"❌ 参数 JSON 格式错误：{error}", file=sys.stderr)
            sys.exit(1)
        success = call_tool(resolved_url, args.tool, params)
    else:
        print("❌ 未知操作", file=sys.stderr)
        sys.exit(1)

    sys.exit(0 if success else 1)


def main():
    """独立运行入口：自动使用配置中的第一个 MCP 服务"""
    url, _ = get_first_mcp_url()

    parser = argparse.ArgumentParser(
        description="MCP 工具调用脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="action", help="操作类型")

    subparsers.add_parser("list", help="列出所有可用工具")

    call_parser = subparsers.add_parser("call", help="调用指定工具")
    call_parser.add_argument("tool", help="要调用的工具名称")
    call_parser.add_argument(
        "--params",
        default="{}",
        help='工具参数（JSON 格式）',
    )

    args = parser.parse_args()

    if not args.action:
        parser.print_help()
        sys.exit(1)

    resolved_url = resolve_url(url)

    if args.action == "list":
        success = list_tools(resolved_url)
    elif args.action == "call":
        try:
            params = json.loads(args.params)
        except json.JSONDecodeError as error:
            print(f"❌ 参数 JSON 格式错误：{error}", file=sys.stderr)
            sys.exit(1)
        success = call_tool(resolved_url, args.tool, params)
    else:
        parser.print_help()
        sys.exit(1)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()