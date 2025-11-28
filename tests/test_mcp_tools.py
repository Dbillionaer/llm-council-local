#!/usr/bin/env -S uv run python
"""
Quick MCP Tool Tests for LLM Council

This script tests MCP tool functionality directly without going through
the full council process. It's much faster for validating tool setup.

Usage:
    uv run tests/test_mcp_tools.py
"""

import asyncio
import json
import os
import signal
import subprocess
import sys
import time
import httpx
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class MCPTestResult:
    """Result of a single MCP tool test."""
    tool_name: str
    passed: bool
    input_args: Dict[str, Any]
    expected: Any
    actual: Any
    error: Optional[str] = None


class MCPTestRunner:
    """Test runner for direct MCP tool calls."""
    
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30.0)
        self.project_root = Path(__file__).parent.parent
        self.backend_process = None
    
    async def is_server_running(self) -> bool:
        """Check if server is running."""
        try:
            response = await self.client.get(f"{self.base_url}/")
            return response.status_code == 200
        except Exception:
            return False
    
    async def start_server(self, timeout: int = 120) -> bool:
        """Start the backend server."""
        if await self.is_server_running():
            print("ℹ️  Server already running")
            return True
        
        print("🚀 Starting backend server...")
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        
        self.backend_process = subprocess.Popen(
            ["uv", "run", "uvicorn", "backend.main:app",
             "--host", "0.0.0.0", "--port", "8001", "--log-level", "warning"],
            cwd=str(self.project_root),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            preexec_fn=os.setsid if sys.platform != "win32" else None
        )
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            if await self.is_server_running():
                print(f"✅ Server started ({time.time() - start_time:.1f}s)")
                return True
            if self.backend_process.poll() is not None:
                print("❌ Server process died")
                return False
            await asyncio.sleep(1)
        
        print(f"❌ Server startup timeout ({timeout}s)")
        return False
    
    async def stop_server(self):
        """Stop the backend server."""
        if self.backend_process:
            print("🛑 Stopping server...")
            try:
                if sys.platform != "win32":
                    os.killpg(os.getpgid(self.backend_process.pid), signal.SIGTERM)
                else:
                    self.backend_process.terminate()
                self.backend_process.wait(timeout=10)
            except:
                if sys.platform != "win32":
                    os.killpg(os.getpgid(self.backend_process.pid), signal.SIGKILL)
            self.backend_process = None
            print("✅ Server stopped")
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP tool directly."""
        response = await self.client.post(
            f"{self.base_url}/api/mcp/call",
            params={"tool_name": tool_name},
            json=arguments
        )
        return response.json()
    
    async def run_tests(self) -> List[MCPTestResult]:
        """Run all MCP tool tests."""
        tests = [
            # Calculator tests
            {
                "tool": "calculator.add",
                "args": {"a": 47, "b": 83},
                "check": lambda r: r.get("output", {}).get("content", [{}])[0].get("text", "").find('"result": 130') != -1,
                "desc": "47 + 83 = 130"
            },
            {
                "tool": "calculator.multiply",
                "args": {"a": 15, "b": 7},
                "check": lambda r: '"result": 105' in r.get("output", {}).get("content", [{}])[0].get("text", ""),
                "desc": "15 * 7 = 105"
            },
            {
                "tool": "calculator.subtract",
                "args": {"a": 100, "b": 42},
                "check": lambda r: '"result": 58' in r.get("output", {}).get("content", [{}])[0].get("text", ""),
                "desc": "100 - 42 = 58"
            },
            {
                "tool": "calculator.divide",
                "args": {"a": 144, "b": 12},
                "check": lambda r: '"result": 12' in r.get("output", {}).get("content", [{}])[0].get("text", ""),
                "desc": "144 / 12 = 12"
            },
            # DateTime tests
            {
                "tool": "system-date-time.get-system-date-time",
                "args": {"type": "date"},
                "check": lambda r: "2025" in r.get("output", {}).get("content", [{}])[0].get("text", ""),
                "desc": "Date includes year 2025"
            },
            {
                "tool": "system-date-time.get-system-date-time",
                "args": {"type": "both"},
                "check": lambda r: all(k in r.get("output", {}).get("content", [{}])[0].get("text", "") 
                                      for k in ["year", "month", "day", "hour", "minute"]),
                "desc": "Both mode returns all fields"
            },
            # Geolocation test
            {
                "tool": "system-geo-location.get-system-geo-location",
                "args": {},
                "check": lambda r: r.get("success") == True,
                "desc": "Geolocation returns success"
            },
            # Timezone test
            {
                "tool": "system-timezone.get-timezone-list",
                "args": {},
                "check": lambda r: r.get("success") == True and "America" in str(r.get("output", {})),
                "desc": "Timezone list includes America"
            },
        ]
        
        results = []
        print(f"\n{'='*60}")
        print(f"Running {len(tests)} MCP tool tests")
        print(f"{'='*60}\n")
        
        for i, test in enumerate(tests, 1):
            tool = test["tool"]
            args = test["args"]
            desc = test["desc"]
            
            print(f"[{i}/{len(tests)}] {tool}: {desc}")
            
            try:
                response = await self.call_tool(tool, args)
                passed = test["check"](response)
                
                status = "✅ PASS" if passed else "❌ FAIL"
                print(f"    {status}")
                
                if not passed:
                    print(f"    Response: {json.dumps(response)[:200]}...")
                
                results.append(MCPTestResult(
                    tool_name=tool,
                    passed=passed,
                    input_args=args,
                    expected=desc,
                    actual=response
                ))
            except Exception as e:
                print(f"    ❌ ERROR: {e}")
                results.append(MCPTestResult(
                    tool_name=tool,
                    passed=False,
                    input_args=args,
                    expected=desc,
                    actual=None,
                    error=str(e)
                ))
        
        return results
    
    def print_summary(self, results: List[MCPTestResult]):
        """Print test summary."""
        total = len(results)
        passed = sum(1 for r in results if r.passed)
        failed = total - passed
        
        print(f"\n{'='*60}")
        print(f"MCP TOOL TEST SUMMARY")
        print(f"{'='*60}")
        print(f"Total: {total} | Passed: {passed} | Failed: {failed}")
        print(f"Pass Rate: {passed/total*100:.1f}%")
        
        if failed > 0:
            print(f"\nFailed tests:")
            for r in results:
                if not r.passed:
                    print(f"  ❌ {r.tool_name}: {r.error or 'Check failed'}")
        
        print(f"{'='*60}\n")
    
    async def close(self):
        """Clean up resources."""
        await self.client.aclose()


async def main():
    """Main entry point."""
    runner = MCPTestRunner()
    server_started_by_us = False
    
    try:
        # Start server if needed
        if not await runner.is_server_running():
            if await runner.start_server():
                server_started_by_us = True
            else:
                print("Failed to start server")
                sys.exit(1)
        
        # Run tests
        results = await runner.run_tests()
        runner.print_summary(results)
        
        # Exit code based on results
        sys.exit(0 if all(r.passed for r in results) else 1)
        
    finally:
        if server_started_by_us:
            await runner.stop_server()
        await runner.close()


if __name__ == "__main__":
    asyncio.run(main())
