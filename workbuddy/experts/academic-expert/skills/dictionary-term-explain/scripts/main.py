#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run.py
术语释义助手 - 多场景术语拆解释义工具（生产级实现）

功能概述：
    1. 在本地内置知识库中查找术语，返回结构化解释。
    2. 支持按场景（技术/业务/日常/学术）拆解术语含义。
    3. 本地未命中时，可尝试调用维基百科 API 获取信息（需网络）。
    4. 提供 --selftest 离线自检模式，使用内置硬编码样例验证核心逻辑。
    5. 支持批量处理 JSON/纯文本文件，支持 --dry-run 预览模式。

错误码说明：
    E1001: 输入为空
    E1002: 输入超长（>100字符）
    E1003: 批量文件不存在或格式错误
    E1004: 知识库未命中且外部API失败
    E1005: 批量文件编码无法识别
"""

import argparse
import json
import os
import sys
import re
import time
import urllib.request
import urllib.error
import urllib.parse
import concurrent.futures
from functools import lru_cache
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

# ============ 常量定义 ============
MAX_TERM_LENGTH = 100
CACHE_SIZE = 1024
TIMEOUT_SECONDS = 5
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2
VERSION = "3.0.0"

# ============ 错误码定义 ============
ERROR_CODES = {
    "E1001": "输入为空",
    "E1002": "输入超长（>100字符）",
    "E1003": "批量文件不存在或格式错误",
    "E1004": "知识库未命中且外部API失败",
    "E1005": "批量文件编码无法识别"
}

# ============ 内置默认知识库 ============
DEFAULT_KNOWLEDGE_BASE = {
    "微服务": {
        "core": "将单一应用拆分为一组小型独立服务，每个服务围绕业务能力构建，可独立部署和扩展。",
        "scenes": {
            "技术": "服务间通过HTTP/RPC轻量通信，每个服务拥有独立数据库，支持独立部署与水平扩展。",
            "业务": "团队可按业务域拆分，独立迭代发布，提升交付效率，降低单点故障影响。",
            "日常": "就像一家餐厅分成多个档口，每个档口独立出菜，互不干扰。",
            "学术": "一种软件架构风格，强调服务粒度、独立部署和去中心化治理。"
        },
        "boundary": "微服务 ≠ 微架构；微服务是架构风格，微架构是单体应用内部模块化设计。",
        "misuse": "误以为微服务一定比单体好——团队规模小、业务简单时，单体反而更高效。"
    },
    "区块链": {
        "core": "一种去中心化的分布式账本技术，通过密码学保证数据不可篡改。",
        "scenes": {
            "技术": "一种由密码学保障的分布式数据存储结构。技术实现上包含区块头（版本、时间戳、Merkle根）与区块体（交易列表）；共识机制包括PoW、PoS、PBFT等；典型应用包括以太坊智能合约平台、Hyperledger Fabric联盟链。",
            "业务": "一种用于构建可信商业协作网络的技术基础设施。供应链金融：实现应收账款确权与流转；数字资产：NFT确权与交易；跨境支付：降低中间环节成本。",
            "日常": "可理解为'全民共同记账的公共账本'，每个人手中都有一份完整的账本副本。",
            "学术": "一种结合密码学、分布式系统和博弈论的交叉学科研究领域。"
        },
        "boundary": "区块链不等于比特币，比特币只是区块链的一种应用；区块链并非绝对安全，智能合约漏洞仍可能导致资产损失。",
        "misuse": "误以为区块链数据完全无法修改（实际上在特定条件下可通过分叉或51%攻击改变）；误以为所有区块链都需要挖矿（联盟链、私有链不依赖工作量证明）。"
    },
    "容器化": {
        "core": "将应用及其依赖打包到标准化的容器镜像中，实现一次构建、随处运行。",
        "scenes": {
            "技术": "基于Linux内核的Namespace和Cgroups实现资源隔离与限制；Docker是最流行的容器运行时；Kubernetes用于容器编排。",
            "业务": "提升开发到部署的一致性，减少环境差异问题；支持微服务架构的快速迭代。",
            "日常": "就像标准化的集装箱，无论里面装什么，都能用统一的工具搬运和堆放。",
            "学术": "操作系统级虚拟化的一种实现方式，比虚拟机更轻量，启动速度更快。"
        },
        "boundary": "容器 ≠ 虚拟机；容器共享宿主机内核，虚拟机包含完整操作系统。",
        "misuse": "误以为容器是安全边界——容器逃逸漏洞可能导致宿主机被攻陷。"
    },
    "API": {
        "core": "应用程序编程接口，定义软件组件之间的交互协议。",
        "scenes": {
            "技术": "RESTful API基于HTTP方法（GET/POST/PUT/DELETE）操作资源；GraphQL提供更灵活的查询；gRPC基于HTTP/2和Protocol Buffers。",
            "业务": "开放API可构建合作伙伴生态，如微信开放平台、支付宝开放平台。",
            "日常": "就像餐厅的菜单，你只需要点菜（调用接口），不需要知道厨房怎么运作。",
            "学术": "一种形式化接口契约，描述可用操作、输入参数和返回结果。"
        },
        "boundary": "API ≠ 函数调用；API是跨进程/跨网络的接口，函数调用是进程内调用。",
        "misuse": "误以为API设计只是URL设计——实际上还包括认证、限流、版本管理、错误处理等。"
    },
    "DevOps": {
        "core": "开发（Development）与运维（Operations）的融合，强调自动化、协作和持续交付。",
        "scenes": {
            "技术": "CI/CD流水线自动化构建、测试和部署；基础设施即代码（IaC）如Terraform；监控告警如Prometheus。",
            "业务": "缩短交付周期，提升部署频率，降低变更失败率。",
            "日常": "就像厨师和服务员紧密配合，确保菜品快速上桌且质量稳定。",
            "学术": "一种软件工程实践，强调文化、自动化、精益和度量。"
        },
        "boundary": "DevOps ≠ 工具链；工具只是辅助，核心是文化和流程变革。",
        "misuse": "误以为引入Jenkins就是DevOps——没有文化变革，工具只是摆设。"
    }
}

# ============ 全局状态 ============
dry_run = False  # 模块级 dry-run 标志


# ============ 工具函数 ============

def log_debug(message: str, verbose: bool = False) -> None:
    """输出调试信息到 stderr。"""
    if verbose:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        print(f"[DEBUG {timestamp}] {message}", file=sys.stderr)


def log_warning(message: str) -> None:
    """输出警告信息到 stderr。"""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[WARN {timestamp}] {message}", file=sys.stderr)


def log_error(message: str) -> None:
    """输出错误信息到 stderr。"""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[ERROR {timestamp}] {message}", file=sys.stderr)


def validate_term(term: str) -> Tuple[bool, Optional[str]]:
    """
    校验术语输入。
    
    返回: (是否有效, 错误码或None)
    """
    if not term or not term.strip():
        return False, "E1001"
    if len(term.strip()) > MAX_TERM_LENGTH:
        return False, "E1002"
    return True, None


def validate_scene(scene: str) -> bool:
    """校验场景参数是否合法。"""
    valid_scenes = {"技术", "业务", "日常", "学术", "all"}
    return scene in valid_scenes


def read_file_with_encoding(filepath: str) -> Optional[str]:
    """
    读取文件内容，支持多编码（utf-8 → gbk → gb18030 三级 fallback）。
    
    返回: 文件内容字符串，失败返回 None
    """
    encodings = ["utf-8", "gbk", "gb18030"]
    for enc in encodings:
        try:
            with open(filepath, "r", encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
        except FileNotFoundError:
            log_error(f"文件不存在: {filepath}")
            return None
        except Exception as e:
            log_error(f"读取文件失败: {filepath}, 错误: {e}")
            return None
    log_error(f"无法识别文件编码: {filepath}")
    return None


def parse_batch_file(filepath: str) -> Optional[List[str]]:
    """
    解析批量文件（JSON 或纯文本）。
    
    JSON 格式: {"terms": ["术语1", "术语2"]}
    纯文本格式: 每行一个术语
    
    返回: 术语列表，失败返回 None
    """
    content = read_file_with_encoding(filepath)
    if content is None:
        return None
    
    # 尝试 JSON 解析
    try:
        data = json.loads(content)
        if isinstance(data, dict) and "terms" in data:
            terms = data["terms"]
            if isinstance(terms, list) and all(isinstance(t, str) for t in terms):
                return terms
            else:
                log_error(f"JSON 格式错误: 'terms' 必须是字符串列表")
                return None
        else:
            log_error(f"JSON 格式错误: 必须包含 'terms' 键")
            return None
    except json.JSONDecodeError:
        # 不是 JSON，按纯文本处理
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        if lines:
            return lines
        else:
            log_error(f"纯文本文件为空: {filepath}")
            return None
    except Exception as e:
        log_error(f"解析文件失败: {filepath}, 错误: {e}")
        return None


# ============ 知识库查询 ============

@lru_cache(maxsize=CACHE_SIZE)
def query_knowledge_base(term: str) -> Optional[Dict]:
    """
    查询内置知识库。
    
    返回: 术语解释字典，未命中返回 None
    """
    term_lower = term.strip().lower()
    for key, value in DEFAULT_KNOWLEDGE_BASE.items():
        if key.lower() == term_lower:
            return value
    return None


def query_wikipedia(term: str, timeout: int = TIMEOUT_SECONDS, max_retries: int = MAX_RETRIES) -> Optional[Dict]:
    """
    查询维基百科 API 获取术语解释。
    
    使用指数退避重试策略。
    
    返回: 解释字典，失败返回 None
    """
    url = "https://zh.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "titles": term,
        "prop": "extracts",
        "exintro": True,
        "explaintext": True,
        "format": "json",
        "redirects": 1
    }
    
    full_url = f"{url}?{urllib.parse.urlencode(params)}"
    
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(full_url, headers={"User-Agent": "TermExplainer/3.0"})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
            
            pages = data.get("query", {}).get("pages", {})
            for page_id, page in pages.items():
                if page_id == "-1":
                    # 页面不存在
                    return None
                extract = page.get("extract", "")
                if extract:
                    return {
                        "core": extract[:500],  # 限制长度
                        "scenes": {
                            "学术": extract[:300]
                        },
                        "boundary": "来自维基百科的外部解释，仅供参考。",
                        "misuse": "外部解释未提供常见误用分析。"
                    }
            return None
            
        except urllib.error.URLError as e:
            log_warning(f"维基百科请求失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                # 指数退避
                wait_time = RETRY_BACKOFF_BASE ** attempt
                time.sleep(wait_time)
        except json.JSONDecodeError as e:
            log_error(f"维基百科响应解析失败: {e}")
            return None
        except Exception as e:
            log_error(f"维基百科查询异常: {e}")
            return None
    
    return None


def get_term_explanation(term: str, scene: str = "all", verbose: bool = False) -> Dict:
    """
    获取术语解释（知识库优先，外部 API 兜底）。
    
    返回: 解释字典
    """
    # 校验输入
    valid, error_code = validate_term(term)
    if not valid:
        return {
            "term": term,
            "error": error_code,
            "error_message": ERROR_CODES.get(error_code, "未知错误")
        }
    
    # 查询知识库
    kb_result = query_knowledge_base(term)
    if kb_result:
        log_debug(f"知识库命中: {term}", verbose)
        return {
            "term": term,
            "core": kb_result["core"],
            "scenes": kb_result["scenes"],
            "boundary": kb_result["boundary"],
            "misuse": kb_result["misuse"],
            "source": "knowledge_base"
        }
    
    # 外部 API 兜底
    log_debug(f"知识库未命中，尝试维基百科: {term}", verbose)
    wiki_result = query_wikipedia(term)
    if wiki_result:
        log_debug(f"维基百科命中: {term}", verbose)
        return {
            "term": term,
            "core": wiki_result["core"],
            "scenes": wiki_result["scenes"],
            "boundary": wiki_result["boundary"],
            "misuse": wiki_result["misuse"],
            "source": "wikipedia"
        }
    
    # 全部失败
    return {
        "term": term,
        "error": "E1004",
        "error_message": ERROR_CODES["E1004"]
    }


# ============ 输出格式化 ============

def format_explanation(explanation: Dict, scene: str = "all") -> str:
    """
    格式化术语解释输出。
    """
    if "error" in explanation:
        return f"【{explanation['term']}】\n错误: {explanation['error']} - {explanation['error_message']}"
    
    lines = []
    term = explanation["term"]
    
    # 核心定义
    lines.append(f"【{term}】核心定义")
    lines.append(explanation["core"])
    lines.append("")
    
    # 场景拆解
    scenes = explanation.get("scenes", {})
    if scene == "all":
        for scene_name in ["技术", "业务", "日常", "学术"]:
            if scene_name in scenes:
                lines.append(f"【{scene_name}场景】")
                lines.append(scenes[scene_name])
                lines.append("")
    elif scene in scenes:
        lines.append(f"【{scene}场景】")
        lines.append(scenes[scene])
        lines.append("")
    
    # 概念边界
    if "boundary" in explanation:
        lines.append("【概念边界】")
        lines.append(explanation["boundary"])
        lines.append("")
    
    # 常见误用
    if "misuse" in explanation:
        lines.append("【常见误用】")
        lines.append(explanation["misuse"])
    
    return "\n".join(lines)


# ============ 批量处理 ============

def process_batch(terms: List[str], scene: str, dry_run: bool, verbose: bool) -> int:
    """
    批量处理术语列表。
    
    返回: 成功处理的术语数量
    """
    success_count = 0
    total = len(terms)
    
    for i, term in enumerate(terms, 1):
        print(f"========== {i}/{total} ==========")
        
        if dry_run:
            print(f"[DRY-RUN] 将查询术语: {term}")
            continue
        
        explanation = get_term_explanation(term, scene, verbose)
        output = format_explanation(explanation, scene)
        print(output)
        print()
        
        if "error" not in explanation:
            success_count += 1
    
    return success_count


# ============ 自测模式 ============

def run_selftest() -> int:
    """
    运行自测，验证核心功能。
    
    返回: 0 表示全部通过，非 0 表示失败
    """
    print("=== 术语释义助手自测 ===")
    failures = 0
    
    # 测试 1: 知识库查询
    print("\n[测试 1] 知识库查询")
    try:
        result = query_knowledge_base("微服务")
        assert result is not None, "知识库应命中'微服务'"
        assert "core" in result, "结果应包含核心定义"
        assert "scenes" in result, "结果应包含场景拆解"
        assert "技术" in result["scenes"], "结果应包含技术场景"
        print("  ✓ 知识库查询正常")
    except AssertionError as e:
        print(f"  ✗ 知识库查询失败: {e}")
        failures += 1
    
    # 测试 2: 输入校验
    print("\n[测试 2] 输入校验")
    try:
        valid, code = validate_term("")
        assert not valid and code == "E1001", "空输入应返回 E1001"
        
        valid, code = validate_term(" " * 10)
        assert not valid and code == "E1001", "空白输入应返回 E1001"
        
        valid, code = validate_term("x" * 101)
        assert not valid and code == "E1002", "超长输入应返回 E1002"
        
        valid, code = validate_term("正常术语")
        assert valid and code is None, "正常输入应通过校验"
        print("  ✓ 输入校验正常")
    except AssertionError as e:
        print(f"  ✗ 输入校验失败: {e}")
        failures += 1
    
    # 测试 3: 场景校验
    print("\n[测试 3] 场景校验")
    try:
        assert validate_scene("技术"), "技术场景应合法"
        assert validate_scene("业务"), "业务场景应合法"
        assert validate_scene("日常"), "日常场景应合法"
        assert validate_scene("学术"), "学术场景应合法"
        assert validate_scene("all"), "all 场景应合法"
        assert not validate_scene("非法场景"), "非法场景应不合法"
        print("  ✓ 场景校验正常")
    except AssertionError as e:
        print(f"  ✗ 场景校验失败: {e}")
        failures += 1
    
    # 测试 4: 完整解释流程
    print("\n[测试 4] 完整解释流程")
    try:
        explanation = get_term_explanation("区块链")
        assert "error" not in explanation, "区块链应能成功解释"
        assert "core" in explanation, "应包含核心定义"
        assert "scenes" in explanation, "应包含场景拆解"
        assert "boundary" in explanation, "应包含概念边界"
        assert "misuse" in explanation, "应包含常见误用"
        print("  ✓ 完整解释流程正常")
    except AssertionError as e:
        print(f"  ✗ 完整解释流程失败: {e}")
        failures += 1
    
    # 测试 5: 输出格式化
    print("\n[测试 5] 输出格式化")
    try:
        explanation = get_term_explanation("微服务")
        output = format_explanation(explanation, "技术")
        assert "微服务" in output, "输出应包含术语名"
        assert "核心定义" in output, "输出应包含核心定义标题"
        assert "技术场景" in output, "输出应包含技术场景标题"
        assert "概念边界" in output, "输出应包含概念边界标题"
        assert "常见误用" in output, "输出应包含常见误用标题"
        print("  ✓ 输出格式化正常")
    except AssertionError as e:
        print(f"  ✗ 输出格式化失败: {e}")
        failures += 1
    
    # 测试 6: 批量文件解析
    print("\n[测试 6] 批量文件解析")
    try:
        # 创建临时测试文件
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump({"terms": ["微服务", "区块链"]}, f)
            temp_path = f.name
        
        terms = parse_batch_file(temp_path)
        assert terms is not None, "JSON 文件应能解析"
        assert len(terms) == 2, "应解析出 2 个术语"
        assert terms[0] == "微服务", "第一个术语应为微服务"
        
        os.unlink(temp_path)
        print("  ✓ 批量文件解析正常")
    except AssertionError as e:
        print(f"  ✗ 批量文件解析失败: {e}")
        failures += 1
    
    # 测试 7: 错误处理
    print("\n[测试 7] 错误处理")
    try:
        explanation = get_term_explanation("")
        assert "error" in explanation, "空输入应返回错误"
        assert explanation["error"] == "E1001", "错误码应为 E1001"
        
        explanation = get_term_explanation("x" * 101)
        assert "error" in explanation, "超长输入应返回错误"
        assert explanation["error"] == "E1002", "错误码应为 E1002"
        print("  ✓ 错误处理正常")
    except AssertionError as e:
        print(f"  ✗ 错误处理失败: {e}")
        failures += 1
    
    # 测试 8: 外部 API 兜底（不实际调用，只验证函数存在）
    print("\n[测试 8] 外部 API 兜底")
    try:
        assert callable(query_wikipedia), "query_wikipedia 应为可调用函数"
        print("  ✓ 外部 API 兜底函数存在")
    except AssertionError as e:
        print(f"  ✗ 外部 API 兜底检查失败: {e}")
        failures += 1
    
    # 汇总
    print(f"\n=== 自测完成: {'全部通过' if failures == 0 else f'{failures} 项失败'} ===")
    return 0 if failures == 0 else 1


# ============ 主入口 ============

def main() -> int:
    """主入口函数。"""
    global dry_run
    
    parser = argparse.ArgumentParser(
        description="术语释义助手 - 按场景拆解术语含义，给出边界清晰、可落地的概念解释。",
        epilog="示例: python run.py 微服务 --scene 技术"
    )
    
    parser.add_argument(
        "--term",
        nargs="?",
        help="要解释的术语"
    )
    parser.add_argument(
        "--scene",
        choices=["技术", "业务", "日常", "学术", "all"],
        default="all",
        help="指定解释场景（默认: all）"
    )
    parser.add_argument(
        "--batch",
        metavar="FILE",
        help="批量处理文件（JSON 或纯文本）"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览模式：不执行查询，只显示将处理的术语"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="输出详细调试信息"
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="运行自测"
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="显示版本信息"
    )
    
    args = parser.parse_args()
    
    # 设置全局 dry_run
    dry_run = args.dry_run
    
    # 版本信息
    if args.version:
        print(f"术语释义助手 v{VERSION}")
        return 0
    
    # 自测模式
    if args.selftest:
        return run_selftest()
    
    # 批量处理
    if args.batch:
        if not os.path.exists(args.batch):
            log_error(f"批量文件不存在: {args.batch}")
            print(f"错误: E1003 - {ERROR_CODES['E1003']}")
            return 1
        
        terms = parse_batch_file(args.batch)
        if terms is None:
            print(f"错误: E1003 - {ERROR_CODES['E1003']}")
            return 1
        
        if args.dry_run:
            print(f"[DRY-RUN] 将处理 {len(terms)} 个术语:")
            for i, term in enumerate(terms, 1):
                print(f"  {i}. {term}")
            return 0
        
        success_count = process_batch(terms, args.scene, args.dry_run, args.verbose)
        print(f"\n处理完成: {success_count}/{len(terms)} 个术语成功")
        return 0 if success_count == len(terms) else 1
    
    # 单个术语
    if not args.term:
        parser.print_help()
        return 1
    
    explanation = get_term_explanation(args.term, args.scene, args.verbose)
    output = format_explanation(explanation, args.scene)
    print(output)
    
    if "error" in explanation:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
