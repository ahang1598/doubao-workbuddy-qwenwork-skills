# 1688 Distribution

This skill uses the `ali1688-buyer` MCP connector for authentication and API calls.
Local Python code only post-processes MCP results.

## Pattern

1. Call the relevant MCP tool, such as `distribution_select_offer`,
   `distribution_offer_info`, `shop_and_tool_info`, `distribute_offer`,
   `fx_query_order`, `fx_send_ww`, `fx_ww_reply`, or
   `distribution_knowledge_tool`.
2. Save the raw MCP JSON result to a file or pipe it to stdin.
3. Run the corresponding Python post-processing command.

Example:

```bash
python3 scripts/cli.py product_search_helper search \
  --filters='[{"filterKey":"title","filterValue":["垃圾袋"],"queryType":"contains_any"}]' \
  --mcp-result-file /tmp/distribution_select_offer.json
```

## Notes

- Do not configure AK in this skill.
- Do not call legacy HTTP scripts.
- Display the returned `markdown` field directly.
