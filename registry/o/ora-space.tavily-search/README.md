# ora-space.tavily-search

A **configuration-only MCP plugin** for Ora that describes Tavily's remote MCP
server. Ora installs and validates the package; an Agent plugin later turns the
installed descriptor into target-agent configuration. This package does not ship
`main.js` and does not start a Deno process.

## What it provides

- Remote MCP endpoint: `https://mcp.tavily.com/mcp` (MCP Streamable HTTP)
- One required setting: `apiKey` (string in Phase 1; stored in your local
  `store.json` after you save it in Ora settings)

## Setup in Ora

1. Sync the marketplace and install `official/ora-space.tavily-search`.
2. Enable the plugin in global settings.
3. Open plugin settings and paste your Tavily API key. The key is never baked
   into this package or the marketplace listing.

## Package layout

```text
orax.toml
README.md
logo.svg
assets/
  config.json
```

## License

Apache-2.0
