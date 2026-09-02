#!/usr/bin/env python3
"""Test aggregate_competition.py with and without Keepa data."""
import json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
from aggregate_competition import aggregate

# Test 1: Pure SERP data (no Keepa) - should produce 6 dimensions
products_serp = [
    {"asin": "B001", "title": "Test Product 1", "extractedPrice": 19.99, "rating": 4.5, "ratings": 500, "monthlySalesUnits": 1000, "page": 1, "position": 1, "sponsored": False},
    {"asin": "B002", "title": "Test Product 2", "extractedPrice": 29.99, "rating": 4.0, "ratings": 200, "monthlySalesUnits": 500, "page": 1, "position": 2, "sponsored": False},
    {"asin": "B003", "title": "Test Product 3", "extractedPrice": 9.99, "rating": 4.8, "ratings": 50, "monthlySalesUnits": None, "page": 1, "position": 3, "sponsored": False},
]

result = aggregate(products_serp)
print("=== Test 1: Pure SERP (no Keepa) ===")
print(f"Dimensions: {len(result['dimensions'])}")
print(f"Keepa available: {result['meta']['keepaAvailable']}")
print(f"Keepa coverage: {result['meta']['keepaCoverage']}%")
print(f"Disclaimer: {result['meta']['disclaimer'][:80]}...")
print()

# Test 2: With Keepa data - should produce 38 dimensions
products_keepa = [
    {"asin": "B001", "title": "Test 1", "extractedPrice": 19.99, "rating": 4.5, "ratings": 500, "monthlySalesUnits": 1000, "page": 1, "position": 1, "sponsored": False,
     "keepa_available": True, "brand": "Anker", "fulfillment": "FBA", "salesRank": 150, "salesRank30": 140, "salesRank90": 160, "salesRank180": 180,
     "profit": 25.5, "fbaFees": 4.5, "referralFeePercentage": 15.0, "sellerNum": 3, "variationNum": 5, "buyBoxSellerId": "A123",
     "availableDate": "2025-06-15 00:00:00", "isHazmat": False, "isAdultProduct": False,
     "monthlySalesUnits6MonthsAgo": 800, "monthlySalesUnits3MonthsAgo": 900, "monthlySalesUnits1MonthAgo": 950, "monthlySalesUnits12MonthsAgo": 600,
     "subcategories": [{"label": "Flags", "rank": 25}], "categoryTree": "Patio:Decor:Flags"},
    {"asin": "B002", "title": "Test 2", "extractedPrice": 29.99, "rating": 4.0, "ratings": 200, "monthlySalesUnits": 500, "page": 1, "position": 2, "sponsored": False,
     "keepa_available": True, "brand": "Anker", "fulfillment": "FBM", "salesRank": 300, "salesRank30": 290, "salesRank90": 310, "salesRank180": 350,
     "profit": 15.0, "fbaFees": 6.0, "referralFeePercentage": 15.0, "sellerNum": 1, "variationNum": 0, "buyBoxSellerId": "A456",
     "availableDate": "2026-03-01 00:00:00", "isHazmat": True, "isAdultProduct": False,
     "monthlySalesUnits6MonthsAgo": 300, "monthlySalesUnits3MonthsAgo": 400, "monthlySalesUnits1MonthAgo": 450, "monthlySalesUnits12MonthsAgo": 200,
     "subcategories": [{"label": "Flags", "rank": 50}], "categoryTree": "Patio:Decor:Flags"},
    {"asin": "B003", "title": "Test 3", "extractedPrice": 9.99, "rating": 4.8, "ratings": 50, "monthlySalesUnits": None, "page": 1, "position": 3, "sponsored": False,
     "keepa_available": True, "brand": "Belkin", "fulfillment": "FBA", "salesRank": 500, "salesRank30": 480, "salesRank90": 520, "salesRank180": 550,
     "profit": 30.0, "fbaFees": 3.0, "referralFeePercentage": 15.0, "sellerNum": 2, "variationNum": 2, "buyBoxSellerId": "A789",
     "availableDate": "2026-06-01 00:00:00", "isHazmat": False, "isAdultProduct": False,
     "monthlySalesUnits6MonthsAgo": None, "monthlySalesUnits3MonthsAgo": 100, "monthlySalesUnits1MonthAgo": 150, "monthlySalesUnits12MonthsAgo": None,
     "subcategories": [{"label": "Flags", "rank": 75}], "categoryTree": "Patio:Decor:Flags"},
]

result2 = aggregate(products_keepa)
print("=== Test 2: With Keepa data ===")
print(f"Dimensions: {len(result2['dimensions'])}")
print(f"Keepa available: {result2['meta']['keepaAvailable']}")
print(f"Keepa coverage: {result2['meta']['keepaCoverage']}%")
print(f"Disclaimer: {result2['meta']['disclaimer'][:80]}...")
print()
for d in result2["dimensions"]:
    print(f"  [{d['dimension']:2d}] {d['name']} ({d['type']})")
print()
print(f"Appendix rule: {result2['appendix']['data']['rule']}")
print(f"Appendix count: {result2['appendix']['data']['count']}")
print()

# Verify dimension count
assert len(result["dimensions"]) == 6, f"Expected 6 dimensions without Keepa, got {len(result['dimensions'])}"
assert len(result2["dimensions"]) == 38, f"Expected 38 dimensions with Keepa, got {len(result2['dimensions'])}"
assert result["meta"]["keepaAvailable"] == False
assert result2["meta"]["keepaAvailable"] == True
print("=== ALL TESTS PASSED ===")
