# Amazon Operations Assistant

Using OpenBoost data, this suite connects category research, product opportunity screening, ranking validation, keyword research, traffic analysis and ASIN diagnosis into one traceable Amazon workflow.

## Included skills

1. Amazon Category Market Analysis
2. Amazon Product Opportunity Screening
3. Amazon Ranking Opportunity Scout
4. Amazon Keyword Research
5. Amazon Traffic Structure Analysis
6. Amazon ASIN Diagnosis

The assistant uses `proboost-Amazon-mcp` first. If the connector is unavailable, it may analyze user-provided CSV, XLSX, JSON, screenshots or platform exports and must label the result as user-provided/offline fallback data. If neither source is available, it returns an input template and does not invent results.
