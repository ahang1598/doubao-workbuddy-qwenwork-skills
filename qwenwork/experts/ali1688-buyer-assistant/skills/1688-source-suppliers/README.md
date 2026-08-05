# 1688 Source Suppliers

This skill uses the `ali1688-buyer` MCP connector for authentication and API calls.
Local Python code only post-processes MCP results.

## Usage

1. Call MCP tool `1688_source_suppliers`.
2. Save the raw MCP JSON result to a file or pipe it to stdin.
3. Run the post-processing CLI:

```bash
python3 cli.py ali_1688_source_suppliers \
  --query "不锈钢保温杯供应商" \
  --mcp-result-file /tmp/source_suppliers.json
```

or:

```bash
cat /tmp/source_suppliers.json | python3 cli.py ali_1688_source_suppliers -q "不锈钢保温杯供应商"
```

## Notes

- Do not configure AK in this skill.
- Do not call legacy HTTP scripts.
- Display the returned `markdown` field directly.
