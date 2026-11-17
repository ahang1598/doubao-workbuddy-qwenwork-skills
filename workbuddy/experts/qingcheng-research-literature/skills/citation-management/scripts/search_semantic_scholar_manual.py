#!/usr/bin/env python3
"""
Semantic Scholar Search Wrapper - Manual API Key Mode
This script allows you to use Semantic Scholar search by manually setting the API key.
"""
import sys
import os
import argparse

# Check for API key in command line argument
parser = argparse.ArgumentParser(
    description='Search Semantic Scholar with manual API key',
    epilog='Example: python search_semantic_scholar_manual.py "query" --api-key YOUR_KEY'
)
parser.add_argument('query', help='Search query')
parser.add_argument('--api-key', required=True, help='Your Semantic Scholar API key')
parser.add_argument('--limit', type=int, default=100, help='Max results')
parser.add_argument('--year-start', type=int, help='Start year')
parser.add_argument('--year-end', type=int, help='End year')
parser.add_argument('--output', help='Output file')
parser.add_argument('--format', choices=['json', 'bibtex'], default='json', help='Output format')

args = parser.parse_args()

# Set the environment variable
skill_id = "7610256945278271488"
os.environ[f"COZE_SEMANTIC_SCHOLAR_API_{skill_id}"] = args.api_key

print(f"API key set for {skill_id}")
print(f"Searching for: {args.query}")

# Import and call the main searcher
from scripts.search_semantic_scholar import SemanticScholarSearcher

try:
    searcher = SemanticScholarSearcher()
    results = searcher.search(
        query=args.query,
        max_results=args.limit,
        year_start=args.year_start,
        year_end=args.year_end
    )
    
    if args.format == 'bibtex':
        for result in results:
            bibtex = searcher.metadata_to_bibtex(result)
            print(bibtex)
            print()
    else:
        if args.output:
            import json
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"Results saved to {args.output}")
        else:
            print(json.dumps(results, indent=2, ensure_ascii=False))
    
    print(f"\nTotal results: {len(results)}")
    
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
