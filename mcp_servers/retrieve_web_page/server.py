#!/usr/bin/env python3
"""Retrieve Web Page MCP server for fetching HTML content from URLs."""

import json
import urllib.request
import urllib.error
from typing import Dict, Any


def get_page_from_url(url: str) -> Dict[str, Any]:
    """Fetch HTML content from a URL.
    
    Args:
        url: The URL to fetch
    
    Returns:
        Dictionary with success status, URL, and content or error
    """
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (compatible; LLMCouncil/1.0)'}
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            content = response.read().decode('utf-8', errors='replace')
            return {
                "success": True,
                "url": url,
                "content": content,
                "status_code": response.status
            }
            
    except urllib.error.HTTPError as e:
        return {
            "success": False,
            "url": url,
            "error": f"HTTP Error {e.code}: {e.reason}"
        }
    except urllib.error.URLError as e:
        return {
            "success": False,
            "url": url,
            "error": f"URL Error: {str(e.reason)}"
        }
    except Exception as e:
        return {
            "success": False,
            "url": url,
            "error": str(e)
        }


# Tool definitions
TOOLS = [
    {
        "name": "get-page-from-url",
        "description": "Returns the webpage's HTML content from the specified URL",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL of the webpage to retrieve"
                }
            },
            "required": ["url"]
        }
    }
]


def handle_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """Handle a JSON-RPC request."""
    method = request.get("method")
    params = request.get("params", {})
    request_id = request.get("id")
    
    response = {"jsonrpc": "2.0", "id": request_id}
    
    try:
        if method == "initialize":
            response["result"] = {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "serverInfo": {
                    "name": "retrieve-web-page",
                    "version": "1.0.0"
                }
            }
        
        elif method == "notifications/initialized":
            return None
        
        elif method == "tools/list":
            response["result"] = {"tools": TOOLS}
        
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            if tool_name == "get-page-from-url":
                url = arguments.get("url", "")
                result = get_page_from_url(url)
            else:
                response["error"] = {
                    "code": -32601,
                    "message": f"Unknown tool: {tool_name}"
                }
                return response
            
            response["result"] = {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, indent=2)
                    }
                ]
            }
        
        else:
            response["error"] = {
                "code": -32601,
                "message": f"Unknown method: {method}"
            }
    
    except Exception as e:
        response["error"] = {
            "code": -32000,
            "message": str(e)
        }
    
    return response


def main():
    """Main entry point for the MCP server."""
    from mcp_servers.http_wrapper import stdio_main
    stdio_main(handle_request, "Retrieve Web Page MCP")


if __name__ == "__main__":
    main()
