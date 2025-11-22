#!/usr/bin/env python3
"""
Data.gov MCP Server Validation Test

Pre-flight validation for datagov-mcp-server integration.
Tests STDIO transport reliability, latency, and error handling.

Prerequisites:
1. Node.js 18+ installed: node --version
2. datagov-mcp-server installed: npm install -g @melaodoidao/datagov-mcp-server
3. Verify installation: which datagov-mcp-server

Usage:
    python3 tests/test_datagov_validation.py

Expected runtime: 2-3 minutes
Expected output: STDIO reliability metrics, latency measurements, error handling verification
"""

import asyncio
import sys
import os
import time
import subprocess
from typing import Dict, List, Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Check if FastMCP is available
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError:
    print("❌ ERROR: FastMCP not installed")
    print("Install: pip install mcp")
    sys.exit(1)


class ValidationResult:
    """Track validation test results."""
    def __init__(self):
        self.tests_run = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.latencies = []
        self.errors = []
        self.warnings = []

    def add_pass(self, test_name: str, latency_ms: Optional[float] = None):
        self.tests_run += 1
        self.tests_passed += 1
        if latency_ms is not None:
            self.latencies.append(latency_ms)
        print(f"✅ PASS: {test_name}" + (f" ({latency_ms:.0f}ms)" if latency_ms else ""))

    def add_fail(self, test_name: str, error: str):
        self.tests_run += 1
        self.tests_failed += 1
        self.errors.append(f"{test_name}: {error}")
        print(f"❌ FAIL: {test_name}")
        print(f"   Error: {error}")

    def add_warning(self, message: str):
        self.warnings.append(message)
        print(f"⚠️  WARNING: {message}")

    def summary(self) -> Dict:
        avg_latency = sum(self.latencies) / len(self.latencies) if self.latencies else 0
        max_latency = max(self.latencies) if self.latencies else 0
        return {
            "tests_run": self.tests_run,
            "tests_passed": self.tests_passed,
            "tests_failed": self.tests_failed,
            "success_rate": f"{(self.tests_passed/self.tests_run*100):.1f}%" if self.tests_run > 0 else "0%",
            "avg_latency_ms": f"{avg_latency:.0f}",
            "max_latency_ms": f"{max_latency:.0f}",
            "errors": self.errors,
            "warnings": self.warnings
        }


async def check_prerequisites() -> bool:
    """Check if Node.js and datagov-mcp-server are available."""
    print("\n" + "="*80)
    print("PREREQUISITE CHECKS")
    print("="*80 + "\n")

    # Check Node.js
    try:
        result = subprocess.run(
            ["node", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"✅ Node.js installed: {version}")
        else:
            print("❌ Node.js not working")
            return False
    except FileNotFoundError:
        print("❌ Node.js not found")
        print("   Install: https://nodejs.org/")
        return False
    except Exception as e:
        print(f"❌ Node.js check failed: {e}")
        return False

    # Check npm
    try:
        result = subprocess.run(
            ["npm", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"✅ npm installed: {version}")
        else:
            print("❌ npm not working")
            return False
    except FileNotFoundError:
        print("❌ npm not found")
        return False

    # Check datagov-mcp-server
    try:
        result = subprocess.run(
            ["which", "datagov-mcp-server"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            path = result.stdout.strip()
            print(f"✅ datagov-mcp-server installed: {path}")
        else:
            print("❌ datagov-mcp-server not found")
            print("   Install: npm install -g @melaodoidao/datagov-mcp-server")
            return False
    except Exception as e:
        print(f"❌ datagov-mcp-server check failed: {e}")
        return False

    print("\n✅ All prerequisites met")
    return True


async def test_stdio_connection(result: ValidationResult) -> bool:
    """Test basic STDIO connection to datagov-mcp-server."""
    print("\n" + "="*80)
    print("TEST 1: STDIO CONNECTION")
    print("="*80 + "\n")

    try:
        # Create STDIO server parameters
        server_params = StdioServerParameters(
            command="datagov-mcp-server",
            args=[],
            env=None
        )

        start_time = time.time()

        # Connect to server
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize connection
                await session.initialize()

                connection_time = (time.time() - start_time) * 1000
                result.add_pass("STDIO connection established", connection_time)
                return True

    except Exception as e:
        result.add_fail("STDIO connection", str(e))
        return False


async def test_list_tools(result: ValidationResult) -> Optional[List[str]]:
    """Test listing available tools."""
    print("\n" + "="*80)
    print("TEST 2: LIST TOOLS")
    print("="*80 + "\n")

    try:
        server_params = StdioServerParameters(
            command="datagov-mcp-server",
            args=[],
            env=None
        )

        start_time = time.time()

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # List tools
                tools_response = await session.list_tools()
                latency = (time.time() - start_time) * 1000

                tools = [tool.name for tool in tools_response.tools]

                print(f"   Found {len(tools)} tools:")
                for tool_name in tools:
                    print(f"      - {tool_name}")

                result.add_pass(f"List tools ({len(tools)} tools found)", latency)
                return tools

    except Exception as e:
        result.add_fail("List tools", str(e))
        return None


async def test_package_search(result: ValidationResult, query: str = "intelligence operations") -> bool:
    """Test package_search tool with a query."""
    print("\n" + "="*80)
    print(f"TEST 3: PACKAGE SEARCH - '{query}'")
    print("="*80 + "\n")

    try:
        server_params = StdioServerParameters(
            command="datagov-mcp-server",
            args=[],
            env=None
        )

        start_time = time.time()

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Call package_search tool
                search_result = await session.call_tool(
                    "package_search",
                    arguments={"q": query, "rows": 5}
                )

                latency = (time.time() - start_time) * 1000

                # Parse result
                if search_result and search_result.content:
                    content = search_result.content[0].text if search_result.content else ""
                    print(f"   Result preview (first 500 chars):")
                    print(f"   {content[:500]}")

                    # Check if results returned
                    if "count" in content or "results" in content:
                        result.add_pass(f"package_search('{query}')", latency)
                        return True
                    else:
                        result.add_warning(f"package_search returned data but format unclear")
                        result.add_pass(f"package_search('{query}') - returned data", latency)
                        return True
                else:
                    result.add_fail(f"package_search('{query}')", "No content returned")
                    return False

    except Exception as e:
        result.add_fail(f"package_search('{query}')", str(e))
        return False


async def test_consecutive_calls(result: ValidationResult, num_calls: int = 5) -> List[bool]:
    """Test multiple consecutive calls to check reliability."""
    print("\n" + "="*80)
    print(f"TEST 4: CONSECUTIVE CALLS ({num_calls} calls)")
    print("="*80 + "\n")

    queries = [
        "intelligence",
        "cybersecurity",
        "SIGINT",
        "classified",
        "operations"
    ]

    successes = []

    for i, query in enumerate(queries[:num_calls], 1):
        print(f"\n   Call {i}/{num_calls}: '{query}'")
        try:
            server_params = StdioServerParameters(
                command="datagov-mcp-server",
                args=[],
                env=None
            )

            start_time = time.time()

            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    search_result = await session.call_tool(
                        "package_search",
                        arguments={"q": query, "rows": 3}
                    )

                    latency = (time.time() - start_time) * 1000

                    if search_result and search_result.content:
                        result.add_pass(f"   Call {i}: '{query}'", latency)
                        successes.append(True)
                    else:
                        result.add_fail(f"   Call {i}: '{query}'", "No content")
                        successes.append(False)

        except Exception as e:
            result.add_fail(f"   Call {i}: '{query}'", str(e))
            successes.append(False)

    success_count = sum(successes)
    print(f"\n   Consecutive calls: {success_count}/{num_calls} succeeded")

    if success_count >= 4:
        result.add_pass(f"Reliability check ({success_count}/{num_calls})")
    elif success_count >= 3:
        result.add_warning(f"Moderate reliability: {success_count}/{num_calls} calls succeeded")
    else:
        result.add_fail(f"Reliability check", f"Only {success_count}/{num_calls} calls succeeded")

    return successes


async def test_error_handling(result: ValidationResult) -> bool:
    """Test error handling with invalid input."""
    print("\n" + "="*80)
    print("TEST 5: ERROR HANDLING")
    print("="*80 + "\n")

    try:
        server_params = StdioServerParameters(
            command="datagov-mcp-server",
            args=[],
            env=None
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Test 1: Empty query
                print("   Test 1: Empty query")
                try:
                    search_result = await session.call_tool(
                        "package_search",
                        arguments={"q": "", "rows": 5}
                    )
                    print("      Server handled empty query gracefully")
                    result.add_pass("   Empty query handling")
                except Exception as e:
                    print(f"      Server error on empty query: {e}")
                    result.add_warning(f"Empty query caused error: {str(e)[:100]}")

                # Test 2: Invalid tool name
                print("   Test 2: Invalid tool name")
                try:
                    search_result = await session.call_tool(
                        "nonexistent_tool",
                        arguments={"q": "test"}
                    )
                    print("      Server returned response for invalid tool (unexpected)")
                    result.add_warning("Server accepted invalid tool name")
                except Exception as e:
                    print(f"      Server rejected invalid tool (expected): {str(e)[:100]}")
                    result.add_pass("   Invalid tool rejection")

                return True

    except Exception as e:
        result.add_fail("Error handling test", str(e))
        return False


async def main():
    """Run all validation tests."""
    print("\n" + "="*80)
    print("DATA.GOV MCP SERVER VALIDATION TEST")
    print("="*80)
    print("\nPurpose: Validate datagov-mcp-server for MCP integration")
    print("Expected runtime: 2-3 minutes")
    print("="*80)

    result = ValidationResult()

    # Check prerequisites
    if not await check_prerequisites():
        print("\n" + "="*80)
        print("❌ VALIDATION FAILED - Prerequisites not met")
        print("="*80 + "\n")
        sys.exit(1)

    # Run tests
    connection_ok = await test_stdio_connection(result)
    if not connection_ok:
        print("\n" + "="*80)
        print("❌ VALIDATION FAILED - Cannot connect to datagov-mcp-server")
        print("="*80 + "\n")
        sys.exit(1)

    tools = await test_list_tools(result)
    if not tools:
        print("\n⚠️  WARNING: Could not list tools, but will continue testing")

    await test_package_search(result)
    await test_consecutive_calls(result, num_calls=5)
    await test_error_handling(result)

    # Summary
    print("\n" + "="*80)
    print("VALIDATION SUMMARY")
    print("="*80 + "\n")

    summary = result.summary()

    print(f"Tests Run: {summary['tests_run']}")
    print(f"Tests Passed: {summary['tests_passed']}")
    print(f"Tests Failed: {summary['tests_failed']}")
    print(f"Success Rate: {summary['success_rate']}")
    print(f"\nPerformance:")
    print(f"  Average Latency: {summary['avg_latency_ms']}ms")
    print(f"  Max Latency: {summary['max_latency_ms']}ms")

    if summary['warnings']:
        print(f"\nWarnings ({len(summary['warnings'])}):")
        for warning in summary['warnings']:
            print(f"  ⚠️  {warning}")

    if summary['errors']:
        print(f"\nErrors ({len(summary['errors'])}):")
        for error in summary['errors']:
            print(f"  ❌ {error}")

    # GO/NO-GO Decision
    print("\n" + "="*80)
    print("GO/NO-GO DECISION CRITERIA")
    print("="*80 + "\n")

    passed = result.tests_passed
    total = result.tests_run
    avg_latency = float(summary['avg_latency_ms'])
    max_latency = float(summary['max_latency_ms'])

    print("Criteria:")
    print(f"  - Success rate >= 80% (8/10 calls): {'✅' if passed/total >= 0.8 else '❌'} ({passed}/{total} = {summary['success_rate']})")
    print(f"  - Average latency < 5000ms: {'✅' if avg_latency < 5000 else '❌'} ({avg_latency:.0f}ms)")
    print(f"  - Max latency < 10000ms: {'✅' if max_latency < 10000 else '❌'} ({max_latency:.0f}ms)")

    # Decision
    go_criteria = (
        passed / total >= 0.8 and
        avg_latency < 5000 and
        max_latency < 10000
    )

    maybe_criteria = (
        passed / total >= 0.6 and
        avg_latency < 8000
    )

    print("\n" + "="*80)
    if go_criteria:
        print("✅ RECOMMENDATION: GO")
        print("="*80)
        print("\nSTDIO transport is reliable and performant.")
        print("Proceed with datagov-mcp-server integration (Phase 3).")
        print("\nNext steps:")
        print("1. Update DATAGOV_MCP_PREFLIGHT_ANALYSIS.md with validation results")
        print("2. Begin Phase 1: POC Testing (2-3 hours)")
        print("3. Implement Data.gov integration (3-4 hours)")
    elif maybe_criteria:
        print("⚠️  RECOMMENDATION: MAYBE (Needs Work)")
        print("="*80)
        print("\nSTDIO transport works but reliability or performance is marginal.")
        print("Consider adding retry logic and timeout handling.")
        print("\nOptions:")
        print("1. Proceed with extra error handling and monitoring")
        print("2. Build custom integration instead (4-6 hours)")
    else:
        print("❌ RECOMMENDATION: NO-GO")
        print("="*80)
        print("\nSTDIO transport is too unreliable or slow.")
        print("Do NOT proceed with datagov-mcp-server integration.")
        print("\nRecommendation: Build custom DataGovIntegration (4-6 hours)")
        print("  - Direct CKAN API access (Python requests)")
        print("  - No Node.js dependency")
        print("  - Full control over implementation")

    print("\n" + "="*80)
    print("VALIDATION COMPLETE")
    print("="*80 + "\n")

    # Exit code
    if go_criteria:
        sys.exit(0)  # Success
    else:
        sys.exit(1)  # Failure (NO-GO or MAYBE)


if __name__ == "__main__":
    asyncio.run(main())
