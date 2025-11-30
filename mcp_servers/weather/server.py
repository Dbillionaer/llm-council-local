#!/usr/bin/env python3
"""Weather MCP server for retrieving current weather and forecast using Open-Meteo API."""

import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional
from datetime import datetime


# Weather code mappings from WMO
WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail"
}


def get_weather_description(code: int) -> str:
    """Convert WMO weather code to description."""
    return WEATHER_CODES.get(code, f"Unknown weather (code {code})")


def get_coordinates_from_ip() -> Optional[Dict[str, float]]:
    """Get coordinates from IP geolocation."""
    try:
        req = urllib.request.Request(
            "https://ipinfo.io/json",
            headers={'User-Agent': 'Mozilla/5.0 (compatible; LLMCouncil/1.0)'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        loc = data.get('loc', '')
        if loc:
            lat, lon = loc.split(',')
            return {
                'latitude': float(lat),
                'longitude': float(lon),
                'city': data.get('city', 'Unknown'),
                'region': data.get('region', ''),
                'country': data.get('country', '')
            }
    except Exception:
        pass
    return None


def get_current_weather(latitude: Optional[float] = None, longitude: Optional[float] = None) -> Dict[str, Any]:
    """Get current weather for location.
    
    If lat/lon not provided, uses IP geolocation.
    Uses Open-Meteo API (free, no auth required).
    """
    try:
        location_info = {}
        
        # Get coordinates
        if latitude is None or longitude is None:
            geo = get_coordinates_from_ip()
            if not geo:
                return {"success": False, "error": "Could not determine location"}
            latitude = geo['latitude']
            longitude = geo['longitude']
            location_info = {
                'city': geo.get('city'),
                'region': geo.get('region'),
                'country': geo.get('country')
            }
        
        # Build API URL for current weather
        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={latitude}&longitude={longitude}"
            f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,"
            f"precipitation,rain,weather_code,wind_speed_10m,wind_gusts_10m"
            f"&hourly=temperature_2m,precipitation_probability,weather_code"
            f"&forecast_days=1"
            f"&temperature_unit=fahrenheit"
            f"&wind_speed_unit=mph"
            f"&precipitation_unit=inch"
            f"&timezone=auto"
        )
        
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (compatible; LLMCouncil/1.0)'}
        )
        
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode('utf-8'))
        
        current = data.get('current', {})
        hourly = data.get('hourly', {})
        
        # Get weather description
        weather_code = current.get('weather_code', 0)
        weather_desc = get_weather_description(weather_code)
        
        # Current conditions
        temp = current.get('temperature_2m')
        feels_like = current.get('apparent_temperature')
        humidity = current.get('relative_humidity_2m')
        wind_speed = current.get('wind_speed_10m')
        wind_gusts = current.get('wind_gusts_10m')
        precipitation = current.get('precipitation', 0)
        rain = current.get('rain', 0)
        
        # Determine upcoming conditions (next few hours)
        upcoming_rain = False
        rain_stops_soon = False
        if hourly:
            times = hourly.get('time', [])
            precip_probs = hourly.get('precipitation_probability', [])
            current_hour = datetime.now().hour
            
            # Check next 3 hours
            for i, time_str in enumerate(times[:current_hour + 4]):
                if i > current_hour:
                    prob = precip_probs[i] if i < len(precip_probs) else 0
                    if prob and prob > 50:
                        upcoming_rain = True
                        break
            
            # Check if currently raining but will stop
            if rain > 0 or precipitation > 0:
                for i, time_str in enumerate(times[current_hour:current_hour + 3]):
                    idx = current_hour + i
                    if idx < len(precip_probs):
                        if precip_probs[idx] < 30:
                            rain_stops_soon = True
                            break
        
        # Build human-friendly summary
        summary_parts = []
        
        # Location
        if location_info.get('city'):
            loc_str = location_info['city']
            if location_info.get('region'):
                loc_str += f", {location_info['region']}"
            summary_parts.append(f"Location: {loc_str}")
        
        # Current conditions
        summary_parts.append(f"Conditions: {weather_desc}")
        summary_parts.append(f"Temperature: {temp}°F (feels like {feels_like}°F)")
        summary_parts.append(f"Humidity: {humidity}%")
        summary_parts.append(f"Wind: {wind_speed} mph" + (f" (gusts up to {wind_gusts} mph)" if wind_gusts and wind_gusts > wind_speed + 5 else ""))
        
        # Precipitation status
        if rain > 0:
            summary_parts.append(f"Currently raining ({rain} inches)")
            if rain_stops_soon:
                summary_parts.append("Rain expected to stop soon")
        elif upcoming_rain:
            summary_parts.append("Rain expected in the next few hours")
        
        # Comfort/warnings
        warnings = []
        if temp is not None:
            if temp <= 32:
                warnings.append("Freezing temperatures - bundle up!")
            elif temp <= 45:
                warnings.append("Cold - dress warmly")
            elif temp >= 95:
                warnings.append("Extreme heat - stay hydrated")
            elif temp >= 85:
                warnings.append("Hot - stay cool")
        
        if wind_gusts and wind_gusts > 30:
            warnings.append("Strong winds - be careful")
        
        if warnings:
            summary_parts.append("Advisory: " + "; ".join(warnings))
        
        return {
            "success": True,
            "summary": "\n".join(summary_parts),
            "data": {
                "location": location_info,
                "conditions": weather_desc,
                "weather_code": weather_code,
                "temperature": temp,
                "feels_like": feels_like,
                "humidity": humidity,
                "wind_speed": wind_speed,
                "wind_gusts": wind_gusts,
                "precipitation": precipitation,
                "rain": rain,
                "upcoming_rain": upcoming_rain,
                "rain_stops_soon": rain_stops_soon,
                "warnings": warnings
            }
        }
        
    except urllib.error.URLError as e:
        return {"success": False, "error": f"Network error: {str(e)}"}
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Failed to parse response: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# Tool definitions
TOOLS = [
    {
        "name": "get-current-weather",
        "description": "Get current weather conditions including temperature, humidity, wind, precipitation, and forecast. Uses IP geolocation if coordinates not provided.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "latitude": {
                    "type": "number",
                    "description": "Latitude (optional - uses IP location if not provided)"
                },
                "longitude": {
                    "type": "number",
                    "description": "Longitude (optional - uses IP location if not provided)"
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
                    "name": "weather",
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
            
            if tool_name == "get-current-weather":
                result = get_current_weather(
                    latitude=arguments.get("latitude"),
                    longitude=arguments.get("longitude")
                )
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
    stdio_main(handle_request, "Weather MCP")


if __name__ == "__main__":
    main()
