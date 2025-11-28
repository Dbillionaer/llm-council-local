#!/usr/bin/env python3
"""System Timezone MCP server for retrieving timezone information."""

import json
import re
import urllib.request
import urllib.error
import time
from typing import Dict, Any, List, Optional

# Cache for timezone list (24 hour TTL)
_tz_cache: Optional[Dict[str, Any]] = None
_tz_cache_time: float = 0
_CACHE_TTL = 86400  # 24 hours


def get_page_from_url(url: str) -> str:
    """Fetch HTML content from a URL.
    
    Args:
        url: The URL to fetch
    
    Returns:
        HTML content as string, or empty string on error
    """
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (compatible; LLMCouncil/1.0)'}
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.read().decode('utf-8', errors='replace')
            
    except Exception:
        return ""


def parse_timezone_from_whatismyip(html: str) -> Optional[str]:
    """Extract timezone from whatismyip.com HTML.
    
    Args:
        html: HTML content from whatismyip.com
    
    Returns:
        Timezone string or None if not found
    """
    # whatismyip.com displays timezone in a table row
    patterns = [
        r'Timezone[:\s]*</[^>]+>\s*<[^>]+>([^<]+)',
        r'Time\s*Zone[:\s]*</[^>]+>\s*<[^>]+>([^<]+)',
        r'timezone["\']?\s*[:\=]\s*["\']?([A-Za-z_/]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            tz = match.group(1).strip()
            if tz and '/' in tz:  # Valid tz format like "America/New_York"
                return tz
    
    return None


def parse_timezone_table(html: str) -> List[str]:
    """Extract timezone entries from Wikipedia table.
    
    Args:
        html: HTML content from Wikipedia tz database page
    
    Returns:
        List of timezone names
    """
    timezones = set()
    
    # Look for timezone patterns like "America/New_York" in href or text
    # Wikipedia links to timezone articles with these patterns
    tz_pattern = r'(?:>|/)([A-Z][a-z]+(?:/[A-Z][a-z_]+)+)(?:<|")'
    matches = re.findall(tz_pattern, html)
    
    for tz in matches:
        # Validate it looks like a real timezone
        if '/' in tz and len(tz) > 5:
            timezones.add(tz)
    
    # Also look for title attributes and plain text patterns
    tz_pattern2 = r'([A-Z][a-z]+/[A-Z][a-z_]+(?:/[A-Z][a-z_]+)?)'
    matches2 = re.findall(tz_pattern2, html)
    
    for tz in matches2:
        if '/' in tz and len(tz) > 5:
            timezones.add(tz)
    
    return sorted(list(timezones))


def get_system_timezone() -> Optional[str]:
    """Get the system's timezone based on IP.
    
    Returns:
        Timezone string or None if not detected
    """
    html = get_page_from_url("https://www.whatismyip.com/")
    if html:
        return parse_timezone_from_whatismyip(html)
    return None


def get_timezone_list() -> Dict[str, Any]:
    """Get list of timezones from tz database.
    
    Returns:
        Dictionary with success status and timezone data
    """
    global _tz_cache, _tz_cache_time
    
    # Check cache
    if _tz_cache and (time.time() - _tz_cache_time) < _CACHE_TTL:
        return _tz_cache
    
    try:
        # Get system timezone first
        system_tz = get_system_timezone()
        
        # Fetch Wikipedia timezone list
        wiki_url = "https://en.wikipedia.org/wiki/List_of_tz_database_time_zones"
        html = get_page_from_url(wiki_url)
        
        timezones = []
        if html:
            timezones = parse_timezone_table(html)
        
        # If Wikipedia parsing fails, use a minimal fallback list
        if not timezones:
            timezones = [
                "Africa/Cairo", "Africa/Johannesburg", "Africa/Lagos",
                "America/Chicago", "America/Denver", "America/Los_Angeles",
                "America/New_York", "America/Sao_Paulo", "America/Toronto",
                "Asia/Dubai", "Asia/Hong_Kong", "Asia/Kolkata",
                "Asia/Shanghai", "Asia/Singapore", "Asia/Tokyo",
                "Australia/Melbourne", "Australia/Sydney",
                "Europe/Berlin", "Europe/London", "Europe/Moscow",
                "Europe/Paris", "Pacific/Auckland", "Pacific/Honolulu",
                "UTC"
            ]
        
        # Build result
        result_parts = []
        if system_tz:
            result_parts.append(f"System Timezone: {system_tz}")
            result_parts.append("")
        
        result_parts.append(f"Available Timezones ({len(timezones)} found):")
        for tz in timezones[:100]:  # Limit to first 100 for readability
            result_parts.append(f"- {tz}")
        
        if len(timezones) > 100:
            result_parts.append(f"... and {len(timezones) - 100} more")
        
        result = {
            "success": True,
            "system_timezone": system_tz,
            "timezone_count": len(timezones),
            "timezones": timezones,
            "formatted": "\n".join(result_parts)
        }
        
        # Cache the result
        _tz_cache = result
        _tz_cache_time = time.time()
        
        return result
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# Tool definitions
TOOLS = [
    {
        "name": "get-timezone-list",
        "description": "Returns list of time zones from the tz database, including the system's current timezone based on IP",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
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
                    "name": "system-timezone",
                    "version": "1.0.0"
                }
            }
        
        elif method == "notifications/initialized":
            return None
        
        elif method == "tools/list":
            response["result"] = {"tools": TOOLS}
        
        elif method == "tools/call":
            tool_name = params.get("name")
            
            if tool_name == "get-timezone-list":
                result = get_timezone_list()
            else:
                response["error"] = {
                    "code": -32601,
                    "message": f"Unknown tool: {tool_name}"
                }
                return response
            
            # Return formatted text for readability
            output_text = result.get("formatted", json.dumps(result, indent=2))
            
            response["result"] = {
                "content": [
                    {
                        "type": "text",
                        "text": output_text
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
    stdio_main(handle_request, "System Timezone MCP")


if __name__ == "__main__":
    main()
