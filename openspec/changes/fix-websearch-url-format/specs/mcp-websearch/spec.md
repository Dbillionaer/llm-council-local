## MODIFIED Requirements
### Requirement: Web Search URL Format
The websearch MCP server SHALL construct search URLs using the format `http://127.0.0.1:8080/search?q=<query>` where spaces are replaced with `+` characters.

#### Scenario: Search query with spaces
- **WHEN** search is called with query "searxng mcp server"
- **THEN** the URL constructed is `http://127.0.0.1:8080/search?q=searxng+mcp+server`

#### Scenario: Search query with special characters
- **WHEN** search is called with query containing special characters
- **THEN** special characters (except spaces) are URL encoded
- **AND** spaces are replaced with `+`
