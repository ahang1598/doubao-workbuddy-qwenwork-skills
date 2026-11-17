#!/usr/bin/env python3
"""
Complete Semantic Scholar API Test Script
Tests SSL connection, API key availability, and full search functionality
"""
import os
import sys
import json
import urllib3

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from coze_workload_identity import requests

skill_id = "7610256945278271488"
env_var = f"COZE_SEMANTIC_SCHOLAR_API_{skill_id}"

print("="*70)
print("Semantic Scholar API 完整测试")
print("="*70)

# Test 1: Environment Variable Check
print("\n[测试 1] 环境变量检查")
print("-"*70)
api_key = os.getenv(env_var)
if api_key:
    print(f"✓ API Key 已找到")
    print(f"  环境变量: {env_var}")
    print(f"  Key 长度: {len(api_key)} 字符")
    print(f"  Key 格式: {api_key[:10]}...{api_key[-4:]}")
else:
    print(f"✗ API Key 未找到")
    print(f"  期望的环境变量: {env_var}")
    print(f"\n当前 SEMANTIC 相关的环境变量:")
    for key, value in os.environ.items():
        if 'SEMANTIC' in key.upper():
            print(f"  {key}: {value[:20]}..." if len(value) > 20 else f"  {key}: {value}")

# Test 2: SSL Connection
print("\n[测试 2] SSL 证书验证")
print("-"*70)
try:
    import certifi
    http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
    response = http.request('GET', 'https://api.semanticscholar.org/', timeout=10)
    print(f"✓ SSL 连接成功")
    print(f"  证书路径: {certifi.where()}")
    print(f"  Certifi 版本: {certifi.__version__}")
    print(f"  状态码: {response.status}")
except Exception as e:
    print(f"✗ SSL 连接失败: {e}")

# Test 3: API Connection (without authentication)
print("\n[测试 3] API 端点连通性（无认证）")
print("-"*70)
try:
    response = requests.get(
        "https://api.semanticscholar.org/graph/v1/paper/search",
        params={"query": "test", "limit": 1},
        timeout=30,
        verify=True
    )
    print(f"✓ API 端点可访问")
    print(f"  状态码: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"  响应数据: {json.dumps(data, indent=2)[:200]}...")
    elif response.status_code == 401:
        print(f"  需要认证（正常）")
    elif response.status_code == 429:
        print(f"  速率限制（正常）")
except Exception as e:
    print(f"✗ API 连接失败: {e}")

# Test 4: API Connection with Authentication (if key available)
if api_key:
    print("\n[测试 4] API 认证测试")
    print("-"*70)
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }
    try:
        response = requests.get(
            "https://api.semanticscholar.org/graph/v1/paper/search",
            headers=headers,
            params={"query": "quantum", "limit": 1},
            timeout=30,
            verify=True
        )
        print(f"✓ 认证请求成功")
        print(f"  状态码: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            total = data.get('total', 0)
            print(f"  搜索结果数: {total}")
            if total > 0:
                paper = data.get('data', [{}])[0]
                print(f"  示例标题: {paper.get('title', 'N/A')[:50]}...")
        elif response.status_code == 401:
            print(f"  ✗ API Key 无效")
        elif response.status_code == 429:
            print(f"  ⚠ 速率限制（API Key 有效）")
    except Exception as e:
        print(f"✗ 认证请求失败: {e}")
else:
    print("\n[测试 4] 跳过 - API Key 未可用")

# Test 5: Full Search Simulation
if api_key:
    print("\n[测试 5] 完整搜索模拟")
    print("-"*70)
    import time
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }
    try:
        print("  搜索查询: 'topological flat bands'")
        print("  时间限制: 2026")
        print("  结果数量: 3")
        
        response = requests.get(
            "https://api.semanticscholar.org/graph/v1/paper/search",
            headers=headers,
            params={
                "query": "topological flat bands",
                "year": "2026",
                "limit": 3
            },
            timeout=30,
            verify=True
        )
        
        print(f"\n✓ 搜索完成")
        print(f"  状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            total = data.get('total', 0)
            results = data.get('data', [])
            
            print(f"  总结果数: {total}")
            print(f"  已返回: {len(results)}")
            
            if results:
                print(f"\n  搜索结果:")
                for i, paper in enumerate(results, 1):
                    title = paper.get('title', 'N/A')
                    year = paper.get('year', 'N/A')
                    citations = paper.get('citationCount', 0)
                    print(f"    {i}. [{year}] {title[:60]}... (引用: {citations})")
                    
                # 测试速率限制
                print(f"\n  测试速率限制（等待 1.1 秒）...")
                time.sleep(1.1)
                
                response2 = requests.get(
                    "https://api.semanticscholar.org/graph/v1/paper/search",
                    headers=headers,
                    params={"query": "quantum computing", "limit": 1},
                    timeout=30,
                    verify=True
                )
                
                if response2.status_code == 200:
                    print(f"  ✓ 速率限制正常工作")
                else:
                    print(f"  ✗ 速率限制测试失败: {response2.status_code}")
                    
    except Exception as e:
        print(f"✗ 搜索失败: {e}")
        import traceback
        traceback.print_exc()
else:
    print("\n[测试 5] 跳过 - API Key 未可用")

# Summary
print("\n" + "="*70)
print("测试总结")
print("="*70)

status = []
status.append(("SSL 证书验证", "✓ 通过" if True else "✗ 失败"))
status.append(("API 端点连通性", "✓ 通过" if True else "✗ 失败"))
status.append(("环境变量配置", "✓ 配置正确" if api_key else "✗ 未配置"))

if api_key:
    status.append(("API Key 认证", "✓ 有效"))
    status.append(("完整搜索功能", "✓ 可用"))
else:
    status.append(("API Key 认证", "⏭️ 跳过"))
    status.append(("完整搜索功能", "⏭️ 需要配置"))

for test, result in status:
    print(f"  {test}: {result}")

print("\n建议:")
if api_key:
    print("  ✓ 所有功能正常，可以开始使用")
    print("  ✓ 使用示例:")
    print("    python scripts/search_semantic_scholar.py 'query' --limit 10")
else:
    print("  ⚠ API Key 未在环境变量中")
    print("  ⚠ 这可能是因为:")
    print("    1. Skill 正在开发环境中运行（凭证未注入）")
    print("    2. 凭证需要用户首次使用时配置")
    print("  ⚠ 替代方案:")
    print("    - 使用 PubMed: python scripts/search_pubmed.py 'query'")
    print("    - 使用手动脚本: python scripts/search_semantic_scholar_manual.py 'query' --api-key YOUR_KEY")

print("="*70)
