#!/usr/bin/env python3
"""
Debug Semantic Scholar API connection
"""
import os
import sys

skill_id = "7610256945278271488"
env_var = f"COZE_SEMANTIC_SCHOLAR_API_{skill_id}"

print("=== Semantic Scholar API Debug ===")
print(f"Skill ID: {skill_id}")
print(f"Expected Environment Variable: {env_var}")
print()

api_key = os.getenv(env_var)
if api_key:
    print(f"✓ API Key found: {api_key[:10]}...{api_key[-4:]}")
else:
    print(f"✗ API Key not found in environment")
    print()
    print("Current environment variables:")
    for key, value in os.environ.items():
        if 'SEMANTIC' in key.upper() or 'COZE' in key.upper():
            masked = value[:10] + '...' + value[-4:] if len(value) > 14 else '***'
            print(f"  {key} = {masked}")
    print()
    print("To set the API key manually:")
    print(f"  export {env_var}='your-api-key-here'")
    sys.exit(1)

# Test API connection
print()
print("Testing API connection...")
import urllib3
from coze_workload_identity import requests

headers = {
    "x-api-key": api_key,
    "Content-Type": "application/json"
}

try:
    response = requests.get(
        "https://api.semanticscholar.org/graph/v1/paper/search",
        headers=headers,
        params={"query": "test", "limit": 1},
        timeout=30,
        verify=True
    )
    print(f"✓ Connection successful!")
    print(f"  Status: {response.status_code}")
    print(f"  Response: {response.text[:200]}")
except Exception as e:
    print(f"✗ Connection failed: {e}")
    sys.exit(1)

print()
print("✓ All checks passed!")
