#!/usr/bin/env python3
"""
Test SSL connection to Semantic Scholar API
"""
import urllib3
import certifi
import sys

def test_ssl_connection():
    """Test SSL connection to Semantic Scholar."""
    print("Testing SSL connection to Semantic Scholar API...")
    print("-" * 50)
    
    # Test 1: Default SSL verification
    print("\n1. Testing with default SSL verification:")
    try:
        http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED')
        response = http.request('GET', 'https://api.semanticscholar.org/', timeout=10)
        print(f"   ✓ Success - Status: {response.status}")
    except urllib3.exceptions.SSLError as e:
        print(f"   ✗ SSL Error: {e}")
        return False
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    
    # Test 2: With certifi
    print("\n2. Testing with certifi bundle:")
    try:
        http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
        response = http.request('GET', 'https://api.semanticscholar.org/', timeout=10)
        print(f"   ✓ Success - Status: {response.status}")
        print(f"   ✓ Cert bundle: {certifi.where()}")
        certifi_version = certifi.__version__
        print(f"   ✓ Certifi version: {certifi_version}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    
    # Test 3: Test API endpoint (without API key)
    print("\n3. Testing API endpoint accessibility:")
    try:
        http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
        response = http.request('GET', 'https://api.semanticscholar.org/graph/v1/paper/search?query=test&limit=1', timeout=10)
        print(f"   ✓ API endpoint accessible - Status: {response.status}")
        if response.status == 200:
            print(f"   ✓ API responds correctly (even without API key for limited access)")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    
    print("\n" + "-" * 50)
    print("✓ All SSL tests passed!")
    print("\nThe Semantic Scholar API SSL connection is working correctly.")
    print("You can now use the search_semantic_scholar.py script normally.")
    return True

if __name__ == '__main__':
    success = test_ssl_connection()
    sys.exit(0 if success else 1)
