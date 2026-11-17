#!/usr/bin/env python3
"""
Fixed Semantic Scholar API Script for Coze Environment
Handles both standard and Coze proxy environments
"""
import os
import sys
import argparse
import json
import time
import urllib3
from typing import List, Dict, Optional

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from coze_workload_identity import requests

class SemanticScholarSearcher:
    """Search Semantic Scholar using official API."""
    
    def __init__(self):
        """Initialize searcher with API key."""
        skill_id = "7610256945278271488"
        self.api_key = os.getenv(f"COZE_SEMANTIC_SCHOLAR_API_{skill_id}")
        
        if not self.api_key:
            raise ValueError(
                "Semantic Scholar API key not found. "
                f"Please set COZE_SEMANTIC_SCHOLAR_API_{skill_id} environment variable."
            )
        
        self.base_url = "https://api.semanticscholar.org/graph/v1"
        self.headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        
        # SSL configuration
        self.verify_ssl = os.getenv('SEMANTIC_SCHOLAR_VERIFY_SSL', 'true').lower() == 'true'
        if not self.verify_ssl:
            print("Warning: SSL certificate verification is disabled.", file=sys.stderr)
        
        # Rate limiting: 1 request per second
        self.min_delay = 1.1
        
        # Session for connection pooling
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def search(self, query: str, max_results: int = 100,
               year_start: Optional[int] = None, year_end: Optional[int] = None,
               fields: Optional[List[str]] = None, publication_type: Optional[str] = None) -> List[Dict]:
        """Search Semantic Scholar."""
        if not query:
            print("Error: Query cannot be empty", file=sys.stderr)
            return []
        
        # Default fields
        if fields is None:
            fields = [
                "paperId", "externalIds", "url", "title", "abstract",
                "venue", "year", "publicationVenue", "authors",
                "citationCount", "influentialCitationCount",
                "publicationTypes", "publicationDate", "openAccessPdf"
            ]
        
        print(f'Searching Semantic Scholar: {query}', file=sys.stderr)
        print(f'Max results: {max_results}', file=sys.stderr)
        
        results = []
        offset = 0
        batch_size = 100
        
        while len(results) < max_results:
            params = {
                "query": query,
                "fields": ",".join(fields),
                "limit": min(batch_size, max_results - len(results)),
                "offset": offset
            }
            
            # Add year filter
            if year_start or year_end:
                year_filter = []
                if year_start:
                    year_filter.append(str(year_start))
                if year_end:
                    year_filter.append(str(year_end))
                params["year"] = "-".join(year_filter)
            
            # Add publication type filter
            if publication_type:
                params["publicationTypes"] = publication_type
            
            try:
                response = self.session.get(
                    f"{self.base_url}/paper/search",
                    params=params,
                    timeout=30,
                    verify=self.verify_ssl
                )
                
                if response.status_code >= 400:
                    print(f"HTTP request failed: Status {response.status_code}, Response: {response.text[:200]}", file=sys.stderr)
                    if response.status_code == 401:
                        print("Error: Invalid API key. Please check your credential configuration.", file=sys.stderr)
                    break
                
                data = response.json()
                batch_results = data.get("data", [])
                
                if not batch_results:
                    break
                
                for paper in batch_results:
                    processed = self._process_paper(paper)
                    results.append(processed)
                    print(f'Retrieved {len(results)}/{max_results}', file=sys.stderr)
                
                if len(batch_results) < params["limit"]:
                    break
                
                offset += batch_results
                
                if len(results) < max_results:
                    time.sleep(self.min_delay)
                    
            except requests.exceptions.ProxyError as e:
                print(f"Proxy error: {e}", file=sys.stderr)
                print("Attempting to continue without proxy...", file=sys.stderr)
                # Try without session (no proxy)
                response = requests.get(
                    f"{self.base_url}/paper/search",
                    headers=self.headers,
                    params=params,
                    timeout=30,
                    verify=self.verify_ssl
                )
                if response.status_code == 200:
                    data = response.json()
                    batch_results = data.get("data", [])
                    for paper in batch_results:
                        results.append(self._process_paper(paper))
                    print(f'  Retrieved {len(results)} results', file=sys.stderr)
                break
            except Exception as e:
                print(f"Error during search: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc()
                break
        
        print(f"Total results retrieved: {len(results)}", file=sys.stderr)
        return results
    
    def _process_paper(self, paper: Dict) -> Dict:
        """Process paper data."""
        external_ids = paper.get("externalIds", {})
        authors = paper.get("authors", [])
        author_names = [author.get("name", "") for author in authors if author.get("name")]
        pub_venue = paper.get("publicationVenue", {})
        venue_name = pub_venue.get("name", "") or paper.get("venue", "")
        doi = external_ids.get("DOI", "")
        pmid = external_ids.get("PubMed", "")
        url = paper.get("url", "")
        if not url and doi:
            url = f"https://doi.org/{doi}"
        
        return {
            "paper_id": paper.get("paperId", ""),
            "title": paper.get("title", ""),
            "authors": ", ".join(author_names),
            "year": str(paper.get("year", "")),
            "venue": venue_name,
            "abstract": paper.get("abstract", ""),
            "citation_count": paper.get("citationCount", 0),
            "influential_citation_count": paper.get("influentialCitationCount", 0),
            "publication_types": paper.get("publicationTypes", []),
            "publication_date": paper.get("publicationDate", ""),
            "doi": doi,
            "pmid": pmid,
            "url": url,
            "open_access_pdf": paper.get("openAccessPdf", {}).get("url", "")
        }
    
    def metadata_to_bibtex(self, metadata: Dict) -> str:
        """Convert metadata to BibTeX format."""
        if metadata.get("authors"):
            first_author = metadata["authors"].split(",")[0].strip()
            last_name = first_author.split()[-1] if first_author else "Unknown"
        else:
            last_name = "Unknown"
        
        year = metadata.get("year", "XXXX")
        
        import re
        title = metadata.get("title", "")
        words = re.findall(r'\b[a-zA-Z]{4,}\b', title)
        keyword = words[0].lower() if words else "paper"
        
        citation_key = f'{last_name}{year}{keyword}'
        
        pub_types = metadata.get("publication_types", [])
        venue = metadata.get("venue", "").lower()
        
        if "JournalArticle" in pub_types:
            entry_type = "article"
            venue_field = "journal"
        elif "Conference" in pub_types or "proceedings" in venue:
            entry_type = "inproceedings"
            venue_field = "booktitle"
        else:
            entry_type = "misc"
            venue_field = "note"
        
        lines = [f'@{entry_type}{{{citation_key},']
        
        if metadata.get("authors"):
            authors = metadata["authors"].replace(",", " and")
            lines.append(f'  author  = {{{authors}}},')
        
        if metadata.get("title"):
            lines.append(f'  title   = {{{metadata["title"]}}},')
        
        if metadata.get("venue") and entry_type != "misc":
            lines.append(f'  {venue_field} = {{{metadata["venue"]}}},')
        
        if metadata.get("year"):
            lines.append(f'  year    = {{{metadata["year"]}}},')
        
        if metadata.get("doi"):
            lines.append(f'  doi     = {{{metadata["doi"]}}},')
        
        if metadata.get("url"):
            lines.append(f'  url     = {{{metadata["url"]}}},')
        
        if lines[-1].endswith(','):
            lines[-1] = lines[-1][:-1]
        
        lines.append('}')
        
        return '\n'.join(lines)


def main():
    """Command-line interface."""
    parser = argparse.ArgumentParser(
        description='Search Semantic Scholar (requires API key)',
        epilog='Example: python search_semantic_scholar.py "machine learning" --limit 50'
    )
    
    parser.add_argument('query', help='Search query')
    parser.add_argument('--limit', type=int, default=100, help='Maximum number of results')
    parser.add_argument('--year-start', type=int, help='Start year filter')
    parser.add_argument('--year-end', type=int, help='End year filter')
    parser.add_argument('--publication-type', help='Filter by publication type')
    parser.add_argument('--output', help='Output file path (JSON format)')
    parser.add_argument('--format', choices=['json', 'bibtex'], default='json', help='Output format')
    parser.add_argument('--no-verify-ssl', action='store_true', help='Disable SSL verification')
    
    args = parser.parse_args()
    
    if args.no_verify_ssl:
        os.environ['SEMANTIC_SCHOLAR_VERIFY_SSL'] = 'false'
    
    try:
        searcher = SemanticScholarSearcher()
        
        results = searcher.search(
            query=args.query,
            max_results=args.limit,
            year_start=args.year_start,
            year_end=args.year_end,
            publication_type=args.publication_type
        )
        
        if args.format == 'bibtex':
            for result in results:
                bibtex = searcher.metadata_to_bibtex(result)
                print(bibtex)
                print()
        else:
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False)
                print(f'Results saved to {args.output}', file=sys.stderr)
            else:
                print(json.dumps(results, indent=2, ensure_ascii=False))
        
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
