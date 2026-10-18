# WebMCP

Browser notifications may list page-defined tools. Prefer WebMCP when one
covers the requested action:

```js
const webmcp = await tab.capabilities.get("webmcp");
let tools = await webmcp.fetchTools();
await tools.call("tool_name", input);
```

Before the first WebMCP call on each tab in every turn, call `webmcp.fetchTools()`
and use the returned tools object and tool names. Handles can expire between
turns even when the page is unchanged. Reuse handles during that turn; fetch
again after navigation, a notification that the available tools changed, or a
stale or invalid handle error. Replace the old tools object with the returned one.

If no current notification lists the tools, print `tools.description()`. Call
only listed tools.
