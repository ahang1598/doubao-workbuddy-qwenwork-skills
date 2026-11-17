#!/usr/bin/env python3
"""
Test Semantic Scholar API without environment variable (for debugging)
"""
import sys

print("=== Testing Semantic Scholar API Access ===")
print()
print("Please provide your Semantic Scholar API key:")
print("(The key will be used only for this test and not stored)")
print()

api_key = input("Enter API Key: ").strip()

if not api_key:
    print("No API key provided. Exiting.")
    sys.exit(1)

print()
print("Testing API connection...")

from coze_workload_identity import requests
import time

headers = {
    "x-api-key": api_key,
    "Content-Type": "application/json"
}

# Test 1: Simple search
print("\n1. Testing simple search...")
try:
    response = requests.get(
        "https://api.semanticscholar.org/graph/v1/paper/search",
        headers=headers,
        params={"query": "topological flat bands", "limit": 3, "year": "2026"},
        timeout=30,
        verify=True
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✓ Success! Found {data.get('total', 0)} papers")
        print(f"   Retrieved: {len(data.get('data', []))} results")
    elif response.status_code == 401:
        print(f"   ✗ Authentication failed - Invalid API key")
    elif response.status_code == 429:
        print(f"   ✗ Rate limit exceeded")
    else:
        print(f"   ✗ Error: {response.text[:200]}")
except Exception as e:
    print(f"   ✗ Exception: {e}")
    sys.exit(1)

# Test 2: Test with rate limiting
print("\n2. Testing rate limiting (1.1 second delay)...")
time.sleep(1.1)

try:
    response = requests.get(
        "https://api.semanticscholar.org/graph/v1/paper/search",
        headers=headers,
        params={"query": "quantum computing", "limit": 1},
        timeout=30,
        verify=True
    )
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print(f"   ✓ Rate limiting works correctly")
except Exception as e:
    print(f"   ✗ Exception: {e}")

print()
print("=== Test Complete ===")
print()
print("If the tests passed, your API key is working correctly.")
print("However, the Skill cannot access the API key automatically.")
print()
print("Possible solutions:")
print("1. Set the environment variable manually:")
print("   export COZE_SEMANTIC_SCHOLAR_API_7610256945278271488='your-api-key'")
print()
print("2. Use PubMed as an alternative (already working)")
print("3. Contact support to ensure Skill credentials are properly configured")
