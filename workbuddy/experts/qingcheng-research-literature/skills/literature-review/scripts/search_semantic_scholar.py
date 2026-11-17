#!/usr/bin/env python3
"""
Semantic Scholar Search Script
Searches the Semantic Scholar academic database for papers.

This script searches Semantic Scholar's 200M+ paper database and returns
results in a format compatible with the literature review workflow.

Rate Limit:
- Without API Key: 0.33 requests/second (100 requests/5 minutes)
- With API Key: 1 request/second

Usage:
    python search_semantic_scholar.py "CRISPR gene editing" --limit 20 --year 2020-2024
    python search_semantic_scholar.py "machine learning" --output results.json
"""

import os
import time
import json
import sys
import argparse
from typing import List, Dict, Optional
from coze_workload_identity import requests

# Skill ID for credential access
SKILL_ID = "7610342426410041378"
CREDENTIAL_KEY = f"COZE_SEMANTIC_SCHOLAR_API_KEY_{SKILL_ID}"

# Semantic Scholar API endpoint
API_BASE_URL = "https://api.semanticscholar.org/graph/v1"

# Default fields to retrieve
DEFAULT_FIELDS = [
    "paperId",
    "externalIds",
    "url",
    "title",
    "abstract",
    "venue",
    "year",
    "citationCount",
    "authors",
    "openAccessPdf",
    "publicationTypes"
]


def get_api_key() -> Optional[str]:
    """
    Get Semantic Scholar API key from environment.

    Returns:
        API key if configured, None otherwise
    """
    return os.getenv(CREDENTIAL_KEY)


def search_papers(
    query: str,
    limit: int = 20,
    year_range: Optional[str] = None,
    fields: Optional[List[str]] = None,
    offset: int = 0
) -> List[Dict]:
    """
    Search for papers on Semantic Scholar.

    Args:
        query: Search query string
        limit: Maximum number of results to return (default: 20, max: 100)
        year_range: Year range filter (e.g., "2020-2024")
        fields: List of fields to retrieve
        offset: Offset for pagination

    Returns:
        List of paper results
    """
    if fields is None:
        fields = DEFAULT_FIELDS

    # Get API key from environment
    api_key = get_api_key()

    # Build API request
    url = f"{API_BASE_URL}/paper/search"
    params = {
        "query": query,
        "limit": min(limit, 100),  # API limit
        "fields": ",".join(fields),
        "offset": offset
    }

    # Add year filter if specified
    if year_range:
        params["year"] = year_range

    # Build headers with API key
    headers = {}
    if api_key:
        headers["x-api-key"] = api_key

    try:
        print(f"Searching Semantic Scholar for: {query}")
        if api_key:
            print("✓ Using API key - Rate limit: 1 request/second")
        else:
            print("⚠ No API key - Rate limit: 0.33 request/second")

        response = requests.get(url, params=params, headers=headers, timeout=30)

        # Check HTTP status code
        if response.status_code >= 400:
            error_msg = f"HTTP {response.status_code}: {response.text}"
            if response.status_code == 429:
                error_msg = "Rate limit exceeded. Please configure an API key for higher limits (1 request/second)."
            raise Exception(error_msg)

        data = response.json()

        # Extract results
        results = data.get("data", [])
        total = data.get("total", 0)

        print(f"Found {total} papers, returning {len(results)} results")

        return results

    except requests.exceptions.RequestException as e:
        raise Exception(f"API request failed: {str(e)}")


def get_paper_details(paper_id: str) -> Dict:
    """
    Get detailed information about a specific paper.

    Args:
        paper_id: Semantic Scholar paper ID

    Returns:
        Paper details dictionary
    """
    url = f"{API_BASE_URL}/paper/{paper_id}"
    params = {"fields": ",".join(DEFAULT_FIELDS)}

    # Get API key from environment
    api_key = get_api_key()

    headers = {}
    if api_key:
        headers["x-api-key"] = api_key

    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)

        if response.status_code >= 400:
            raise Exception(f"HTTP {response.status_code}: {response.text}")

        return response.json()

    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to get paper details: {str(e)}")


def format_for_skill(raw_result: Dict) -> Dict:
    """
    Format raw API result to match the skill's standard format.

    Args:
        raw_result: Raw result from Semantic Scholar API

    Returns:
        Formatted result compatible with search_databases.py
    """
    # Extract authors
    authors_list = raw_result.get("authors", [])
    authors = ", ".join([author.get("name", "") for author in authors_list if author.get("name")])

    # Extract DOI from external IDs
    external_ids = raw_result.get("externalIds", {})
    doi = external_ids.get("DOI", external_ids.get("Doi", ""))

    # Get URL
    url = raw_result.get("url", "")
    if not url and raw_result.get("paperId"):
        url = f"https://semanticscholar.org/paper/{raw_result['paperId']}"

    # Get citation count
    citations = raw_result.get("citationCount", 0)

    # Get venue (journal/conference)
    venue = raw_result.get("venue", "")

    return {
        "title": raw_result.get("title", ""),
        "authors": authors,
        "year": str(raw_result.get("year", "")),
        "source": "Semantic Scholar",
        "abstract": raw_result.get("abstract", ""),
        "doi": doi,
        "url": url,
        "citations": citations,
        "venue": venue,
        "paper_id": raw_result.get("paperId", ""),
        "open_access_pdf": raw_result.get("openAccessPdf", {}).get("url", "")
    }


def save_results(results: List[Dict], output_file: str):
    """
    Save search results to a JSON file.

    Args:
        results: List of search results
        output_file: Path to output file
    """
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"Results saved to: {output_file}")


def main():
    """Command-line interface."""
    parser = argparse.ArgumentParser(
        description="Search Semantic Scholar for academic papers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic search
  python search_semantic_scholar.py "CRISPR gene editing"

  # Search with year filter
  python search_semantic_scholar.py "machine learning" --year 2020-2024

  # Save results to file
  python search_semantic_scholar.py "neural networks" --output results.json

  # Get more results
  python search_semantic_scholar.py "bioinformatics" --limit 50

  # Search with pagination
  python search_semantic_scholar.py "genomics" --offset 20
        """
    )

    parser.add_argument(
        "query",
        help="Search query string"
    )

    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=20,
        help="Maximum number of results (default: 20, max: 100)"
    )

    parser.add_argument(
        "--year", "-y",
        help="Year range filter (e.g., 2020-2024)"
    )

    parser.add_argument(
        "--output", "-o",
        help="Output JSON file path"
    )

    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Offset for pagination (default: 0)"
    )

    parser.add_argument(
        "--raw",
        action="store_true",
        help="Output raw API results without formatting"
    )

    args = parser.parse_args()

    try:
        # Search for papers
        raw_results = search_papers(
            query=args.query,
            limit=args.limit,
            year_range=args.year,
            offset=args.offset
        )

        if not raw_results:
            print("No results found.")
            return

        # Format results
        if args.raw:
            formatted_results = raw_results
        else:
            formatted_results = [format_for_skill(r) for r in raw_results]

        # Output results
        if args.output:
            save_results(formatted_results, args.output)
        else:
            print("\n" + "="*60)
            print("SEARCH RESULTS")
            print("="*60 + "\n")

            for i, result in enumerate(formatted_results, 1):
                print(f"{i}. {result.get('title', 'Untitled')}")
                print(f"   Authors: {result.get('authors', 'Unknown')}")
                print(f"   Year: {result.get('year', 'N/A')}")
                print(f"   Venue: {result.get('venue', 'N/A')}")
                print(f"   Citations: {result.get('citations', 0)}")
                if result.get('doi'):
                    print(f"   DOI: {result['doi']}")
                print(f"   URL: {result.get('url', '')}")
                if result.get('abstract'):
                    abstract = result['abstract'][:200] + "..." if len(result['abstract']) > 200 else result['abstract']
                    print(f"   Abstract: {abstract}")
                print()

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
