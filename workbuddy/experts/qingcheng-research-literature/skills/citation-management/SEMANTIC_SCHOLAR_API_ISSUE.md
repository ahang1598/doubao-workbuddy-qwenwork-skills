# Semantic Scholar API Configuration Issue

## Problem Description

The Semantic Scholar API key has been configured in the Skill credentials system, but it is not being automatically injected into the environment variables when the scripts run.

## Current Status

- ✅ API credential created: `semantic_scholar_api`
- ✅ SSL certificate verification: Working (certifi 2026.2.25)
- ✅ API connection: Can be established with manual API key
- ❌ Environment variable injection: Not working automatically

## Error Message

```
Error: Semantic Scholar API key not found.
Please set COZE_SEMANTIC_SCHOLAR_API_7610256945278271488 environment variable.
```

## Workaround Solutions

### Option 1: Manual Environment Variable (Temporary)

```bash
export COZE_SEMANTIC_SCHOLAR_API_7610256945278271488="your-api-key-here"
python scripts/search_semantic_scholar.py "query"
```

### Option 2: Use Manual Script (Recommended for Testing)

Use the wrapper script that accepts API key as argument:

```bash
python scripts/search_semantic_scholar_manual.py \
  "topological flat bands" \
  --api-key "your-api-key" \
  --year-start 2026 \
  --limit 10 \
  --output results.json
```

### Option 3: Use PubMed (Alternative, Already Working)

PubMed search is fully functional and provides excellent results for biomedical and interdisciplinary topics:

```bash
python scripts/search_pubmed.py "topological flat bands" \
  --date-start 2024-01-01 \
  --date-end 2026-03-04 \
  --limit 50 \
  --output results.json
```

## API Connection Test

If you want to verify your API key is working, run the debug script:

```bash
python scripts/debug_semantic_scholar.py
```

This will show:
- Whether the environment variable is set
- Whether the API key is valid
- Whether the SSL connection works

## Root Cause Analysis

The Skill credential system (`skill_credentials`) creates credentials that should be available to the Skill when it runs, but in this environment:

1. The credential `semantic_scholar_api` was successfully created
2. However, the environment variable `COZE_SEMANTIC_SCHOLAR_API_7610256945278271488` is not being set automatically
3. This may be due to:
   - Skill runtime environment configuration
   - Credential injection mechanism not activated
   - Requires Skill to be deployed/activated in a different context

## Recommended Action

1. **For immediate use**: Use PubMed as the primary search source (already working perfectly)
2. **For Semantic Scholar**: Use the manual script with `--api-key` parameter
3. **For long-term**: Contact the platform support to ensure Skill credentials are properly injected at runtime

## Current Search Results

Using PubMed, we successfully retrieved 50 recent papers on "topological flat bands" (2024-2026):

- **Total papers**: 50
- **Top journals**:
  - Physical Review Letters: 13 papers
  - Nature Communications: 5 papers
  - Journal of Physics: Condensed Matter: 5 papers
  - Advanced Materials: 4 papers
  - National Science Review: 3 papers

Results saved to: `topological_flat_bands.json` and `topological_flat_bands.bib`

## Files Created

- `topological_flat_bands.json` - PubMed search results in JSON format
- `topological_flat_bands.bib` - Bibliography in BibTeX format
- `scripts/debug_semantic_scholar.py` - Debug script for API connection
- `scripts/test_api_key.py` - Interactive API key test
- `scripts/search_semantic_scholar_manual.py` - Manual API key wrapper
