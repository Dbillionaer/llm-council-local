#!/usr/bin/env python3
"""System Date-Time MCP server for getting current date and time with timezone."""

import json
import urllib.request
from datetime import datetime
from typing import Dict, Any, Optional


def get_timezone_from_ip() -> Optional[Dict[str, Any]]:
    """Get timezone information based on IP address.
    
    Returns:
        Dictionary with timezone info or None on error
    """
    try:
        req = urllib.request.Request(
            "https://ipinfo.io/json",
            headers={'User-Agent': 'Mozilla/5.0 (compatible; LLMCouncil/1.0)'}
        )
        
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        return {
            'timezone': data.get('timezone', ''),
            'city': data.get('city', ''),
            'region': data.get('region', ''),
            'country': data.get('country', '')
        }
    except Exception:
        return None


def get_system_date_time(return_type: str = "both", include_timezone: bool = True) -> Dict[str, Any]:
    """Get current system date and/or time with optional timezone detection.
    
    Args:
        return_type: One of 'time', 'date', 'both', or 'unix'
        include_timezone: Whether to include timezone info from IP
    
    Returns:
        Dictionary with requested date/time information
    """
    now = datetime.now()
    
    # Get timezone info if requested
    tz_info = None
    if include_timezone:
        tz_info = get_timezone_from_ip()
    
    base_result = {}
    
    if return_type == "time":
        base_result = {
            "type": "time",
            "time": now.strftime("%I:%M:%S %p"),
            "time_24h": now.strftime("%H:%M:%S"),
            "hour": now.hour,
            "minute": now.minute,
            "second": now.second
        }
    elif return_type == "date":
        base_result = {
            "type": "date",
            "date": now.strftime("%Y-%m-%d"),
            "formatted_date": now.strftime("%B %d, %Y"),
            "year": now.year,
            "month": now.month,
            "day": now.day,
            "weekday": now.strftime("%A")
        }
    elif return_type == "unix":
        base_result = {
            "type": "unix",
            "timestamp": int(now.timestamp()),
            "timestamp_ms": int(now.timestamp() * 1000)
        }
    else:  # "both" or default
        base_result = {
            "type": "both",
            "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
            "formatted": now.strftime("%A, %B %d, %Y at %I:%M %p"),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%I:%M:%S %p"),
            "time_24h": now.strftime("%H:%M:%S"),
            "year": now.year,
            "month": now.month,
            "day": now.day,
            "hour": now.hour,
            "minute": now.minute,
            "second": now.second,
            "weekday": now.strftime("%A"),
            "iso": now.isoformat()
        }
    
    # Add timezone info if available
    if tz_info and tz_info.get('timezone'):
        base_result['timezone'] = tz_info['timezone']
        base_result['location'] = f"{tz_info.get('city', '')}, {tz_info.get('region', '')}, {tz_info.get('country', '')}"
        # Update formatted string to include timezone
        if 'formatted' in base_result:
            base_result['formatted'] = f"{base_result['formatted']} ({tz_info['timezone']})"
    else:
        base_result['timezone'] = 'local'
        base_result['timezone_note'] = 'Could not detect timezone from IP, showing local system time'
    
    return base_result


# Tool definitions
TOOLS = [
    {
        "name": "get-system-date-time",
        "description": "Get the current date and/or time with automatic timezone detection based on IP location",
        "inputSchema": {
            "type": "object",
            "properties": {
                "return_type": {
                    "type": "string",
                    "description": "What to return: 'time' (current time only), 'date' (current date only), 'both' (date and time), or 'unix' (Unix timestamp)",
                    "enum": ["time", "date", "both", "unix"],
                    "default": "both"
                },
                "include_timezone": {
                    "type": "boolean",
                    "description": "Whether to detect and include timezone from IP (default: true)",
                    "default": True
                }
            },
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
                    "name": "system-date-time",
                    "version": "1.1.0"
                }
            }
        
        elif method == "notifications/initialized":
            # This is a notification, no response needed
            return None
        
        elif method == "tools/list":
            response["result"] = {"tools": TOOLS}
        
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            if tool_name == "get-system-date-time":
                return_type = arguments.get("return_type", "both")
                include_tz = arguments.get("include_timezone", True)
                result = get_system_date_time(return_type, include_tz)
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
    stdio_main(handle_request, "System Date-Time MCP")


if __name__ == "__main__":
    main()
