# Change: Fix Web Search URL Format

## Why
The websearch MCP server uses incorrect URL format `http://127.0.0.1:8080?q="{query}"` instead of the correct SearXNG format `http://127.0.0.1:8080/search?q=<query>` with `+` replacing spaces.

## What Changes
- Fix URL construction in websearch server to use `/search?q=` path
- Replace spaces with `+` instead of URL encoding
- Remove quotes around query string

## Impact
- Affected specs: mcp-websearch
- Affected code: `mcp_servers/websearch/server.py`
