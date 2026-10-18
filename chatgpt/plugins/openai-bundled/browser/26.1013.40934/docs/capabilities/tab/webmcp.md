# Tab Capability: webmcp
Fetches document-bound WebMCP tools for a single tab.

```ts
const capability = await tab.capabilities.get("webmcp");

interface TabWebMcpCapability {
  fetchTools(): Promise<WebMcpTools>; // Fetch tools registered in the tab's current document. The returned object remains bound to those exact registrations.
}
```
