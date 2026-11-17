# Semantic Scholar Search

## Overview

Semantic Scholar is a free, AI-powered research tool for scientific literature. It uses natural language processing and machine learning to provide semantic search across millions of academic papers from computer science, biomedicine, and other fields.

**Key Features:**
- Semantic understanding of queries beyond keyword matching
- AI-powered paper recommendations
- Citation influence metrics (influential citations)
- Rapid publication indexing (preprints included)
- Open access PDF availability

**API Access:**
- Requires API key (free tier available)
- Rate limit: 1 request per second
- RESTful API with JSON responses
- Support for complex queries and filters

## API Endpoint

**Base URL**: `https://api.semanticscholar.org/graph/v1`

**Search Endpoint**: `/paper/search`

**Authentication**: Header `x-api-key: YOUR_API_KEY`

## Search Parameters

### Required Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `query` | string | Search query (supports natural language) |

### Optional Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `fields` | string | Comma-separated list of fields to retrieve |
| `limit` | integer | Maximum number of results (max 100 per request) |
| `offset` | integer | Number of results to skip (for pagination) |
| `year` | string | Year range filter (e.g., "2010-2020", "2010-", "-2020") |
| `publicationTypes` | string | Filter by publication type |
| `venue` | string | Filter by venue (journal/conference name) |
| `openAccessPdf` | boolean | Filter by open access availability |

### Publication Types

- `JournalArticle`: Peer-reviewed journal articles
- `Conference`: Conference papers
- `Book`: Books
- `BookChapter`: Book chapters
- `Preprint`: Preprints (arXiv, bioRxiv, etc.)

## Response Fields

### Default Fields

The script retrieves these fields by default:

| Field | Description |
|-------|-------------|
| `paperId` | Unique Semantic Scholar paper ID |
| `externalIds` | External identifiers (DOI, PMID, etc.) |
| `url` | Semantic Scholar paper URL |
| `title` | Paper title |
| `abstract` | Paper abstract |
| `venue` | Publication venue |
| `year` | Publication year |
| `publicationVenue` | Detailed venue information |
| `authors` | List of authors |
| `citationCount` | Total citation count |
| `influentialCitationCount` | Influential citation count |
| `publicationTypes` | Publication type(s) |
| `publicationDate` | Full publication date |
| `openAccessPdf` | Open access PDF URL (if available) |

### Citation Metrics

Semantic Scholar provides two citation metrics:

1. **Total Citations**: Total number of citations
2. **Influential Citations**: Citations that are themselves highly cited (AI-determined)

Higher influential citation counts indicate papers that have significantly impacted the field.

## Query Syntax

### Natural Language Queries

Semantic Scholar supports natural language queries:

```
# Search for a concept
machine learning protein folding

# Search for specific methods
attention mechanisms neural networks

# Search for applications
deep learning medical imaging diagnosis
```

### Year Filtering

```bash
# Papers from 2020 onwards
--year-start 2020

# Papers up to 2024
--year-end 2024

# Papers from 2010 to 2020
--year-start 2010 --year-end 2020
```

### Publication Type Filtering

```bash
# Only journal articles
--publication-type JournalArticle

# Only conference papers
--publication-type Conference
```

### Advanced Query Techniques

**Phrase Search**: Use quotes for exact phrases
```
"attention is all you need"
```

**Boolean Operators**: AND, OR, NOT
```
machine learning AND neural networks
machine learning OR deep learning
machine learning NOT "survey"
```

**Field-Specific Search**: (limited support)
```
Title:attention AND Abstract:transformers
```

## Usage Examples

### Basic Search

```bash
# Simple keyword search
python scripts/search_semantic_scholar.py "CRISPR gene editing"

# Natural language query
python scripts/search_semantic_scholar.py "how does CRISPR work"
```

### Filtered Search

```bash
# Recent papers
python scripts/search_semantic_scholar.py "transformers" \
  --year-start 2020 \
  --limit 50

# Journal articles only
python scripts/search_semantic_scholar.py "AlphaFold" \
  --publication-type JournalArticle \
  --year-start 2021 \
  --limit 100
```

### Save to File

```bash
# Save JSON output
python scripts/search_semantic_scholar.py "quantum computing" \
  --limit 100 \
  --output quantum_papers.json

# Export to BibTeX
python scripts/search_semantic_scholar.py "neural networks" \
  --limit 50 \
  --format bibtex \
  --output neural_networks.bib
```

### Complex Query

```bash
# Search for influential papers in a specific time range
python scripts/search_semantic_scholar.py \
  "deep learning medical imaging" \
  --year-start 2020 \
  --year-end 2024 \
  --publication-type JournalArticle \
  --limit 100 \
  --output medical_dl.json
```

### Disable SSL Verification (if needed)

If you encounter SSL certificate verification errors, you can disable SSL verification:

```bash
# Disable SSL verification (use only if necessary)
python scripts/search_semantic_scholar.py "topic" \
  --no-verify-ssl \
  --output results.json
```

**Warning**: Disabling SSL verification is not recommended for production use. If you experience persistent SSL errors, consider:
1. Updating your system's CA certificates
2. Using the `SEMANTIC_SCHOLAR_VERIFY_SSL=false` environment variable
3. Checking your network/proxy configuration

## Rate Limiting

**Constraint**: 1 request per second

The script automatically implements rate limiting with a 1.1-second delay between requests to ensure compliance.

**Important**:
- Do not remove or reduce the delay
- Multiple concurrent requests will exceed the limit
- Exceeding the limit will result in 429 errors

## Output Format

### JSON Format

Default output format. Each result includes:

```json
{
  "paper_id": "string",
  "title": "string",
  "authors": "string",
  "year": "string",
  "venue": "string",
  "abstract": "string",
  "citation_count": integer,
  "influential_citation_count": integer,
  "publication_types": ["string"],
  "publication_date": "string",
  "doi": "string",
  "pmid": "string",
  "url": "string",
  "open_access_pdf": "string"
}
```

### BibTeX Format

Converts search results to BibTeX entries. Entry type determined by publication type:

```bibtex
@article{LastnameYearkeyword,
  author = {Author names},
  title = {Paper title},
  journal = {Journal name},
  year = {2024},
  doi = {10.xxxx/xxxxxx},
  url = {https://doi.org/...}
}
```

## Best Practices

### Query Construction

1. **Use natural language**: Semantic Scholar understands context better than keywords
2. **Be specific**: Include relevant technical terms and concepts
3. **Include synonyms**: Use OR for alternative terms
4. **Use year filters**: Focus on recent or foundational work

### Leveraging Citations

**Finding Influential Papers**:
- Sort results by `influential_citation_count` (manually after export)
- High influential citation count indicates impactful research
- Cross-reference with citation count for context

**Finding Seminal Work**:
- Search for early papers with high influential citation counts
- Look for papers that many later works cite
- Check publication date and sustained citation growth

### Integration with Other Tools

**Extract Metadata**:
```bash
# Search and extract metadata in one step
python scripts/search_semantic_scholar.py "topic" --output results.json
python scripts/extract_metadata.py --input results.json --output references.bib
```

**Combine with PubMed**:
```bash
# Search both databases for comprehensive coverage
python scripts/search_pubmed.py "CRISPR" --output pubmed.json
python scripts/search_semantic_scholar.py "CRISPR" --output ss.json
# Merge and process results
```

## Comparison with Other Databases

| Feature | Semantic Scholar | PubMed | Google Scholar |
|---------|-----------------|--------|----------------|
| **Semantic Search** | ✅ Excellent | ⚠️ Limited | ❌ Keyword-based |
| **Coverage** | Multi-disciplinary | Biomedical | Comprehensive |
| **API Access** | ✅ Free with key | ✅ Free | ❌ Limited |
| **Rate Limit** | 1 req/sec | 3 req/sec | Variable |
| **Citation Metrics** | ✅ Influential citations | ❌ Basic | ✅ Basic |
| **Preprints** | ✅ Included | ⚠️ Some | ✅ Included |
| **Open Access** | ✅ PDF links | ❌ Varies | ❌ Varies |

## Common Issues

### API Key Not Found

**Error**: `Semantic Scholar API key not found`

**Solution**: Set the environment variable:
```bash
export COZE_SEMANTIC_SCHOLAR_API_7610256945278271488="your-api-key"
```

### SSL Certificate Verification Errors

**Error**: `SSL: CERTIFICATE_VERIFY_FAILED` or `SSLError`

**Causes**:
- Outdated CA certificates on your system
- Network proxy or firewall interfering with SSL
- Corporate network with custom certificates

**Solutions**:

**Option 1: Disable SSL verification (quick fix)**
```bash
python scripts/search_semantic_scholar.py "topic" --no-verify-ssl
```

**Option 2: Use environment variable**
```bash
export SEMANTIC_SCHOLAR_VERIFY_SSL=false
python scripts/search_semantic_scholar.py "topic"
```

**Option 3: Update CA certificates (recommended for Linux/Mac)**
```bash
# Ubuntu/Debian
sudo apt-get update && sudo apt-get install ca-certificates

# macOS (with Homebrew)
brew install ca-certificates
```

**Option 4: Use certifi (Python)**
```bash
pip install --upgrade certifi
```

**Note**: Disabling SSL verification is not secure. Use the `--no-verify-ssl` flag only in controlled environments or for troubleshooting.

### Rate Limit Exceeded

**Error**: HTTP 429 (Too Many Requests)

**Solution**: 
- Ensure script's rate limiting is active (1.1s delay)
- Wait before retrying
- Reduce number of concurrent requests

### Empty Results

**Issue**: Query returns no results

**Solution**:
- Check spelling and terminology
- Try broader search terms
- Remove filters
- Try alternative synonyms

## API Documentation

Official Semantic Scholar API documentation:
- https://api.semanticscholar.org/api-docs/
- https://www.semanticscholar.org/product/api/api-key

## License and Usage

Semantic Scholar API is free for academic and research use. Ensure compliance with their terms of service:
- https://www.semanticscholar.org/product/api/faq
