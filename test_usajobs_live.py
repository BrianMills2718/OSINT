#!/usr/bin/env python3
"""
Test USAJobs integration with live API.
"""

import asyncio
import os
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Test imports
from integrations.usajobs_integration import USAJobsIntegration


async def main():
    print("🧪 USAJobs Live API Test")
    print("=" * 80)

    # Get API key
    api_key = os.getenv('USAJOBS_API_KEY')

    if not api_key:
        print("✗ No USAJOBS_API_KEY found in .env")
        return

    print(f"✓ API key loaded: {api_key[:10]}...")
    print()

    # Test 1: Generate query for data science jobs
    print("Test 1: Data Science Jobs in DC")
    print("-" * 80)

    usajobs = USAJobsIntegration()
    query = await usajobs.generate_query("data science jobs in Washington DC")

    if query:
        print(f"✓ Query generated:")
        print(f"  Keywords: {query.get('keywords')}")
        print(f"  Location: {query.get('location')}")
        print(f"  Organization: {query.get('organization')}")
        print(f"  Pay grade: {query.get('pay_grade_low')} - {query.get('pay_grade_high')}")

        result = await usajobs.execute_search(query, api_key=api_key, limit=5)

        if result.success:
            print(f"✓ Search successful: {result.total:,} results found")
            print(f"  Response time: {result.response_time_ms:.0f}ms")

            if result.results:
                print(f"\n  First result:")
                first = result.results[0]
                print(f"    Position Title: {first.get('PositionTitle', 'N/A')}")
                print(f"    Organization: {first.get('OrganizationName', 'N/A')}")
                print(f"    Location: {first.get('PositionLocationDisplay', 'N/A')[:60]}...")
                print(f"    Grade: {first.get('JobGrade', [{}])[0].get('Code', 'N/A') if first.get('JobGrade') else 'N/A'}")
        else:
            print(f"✗ Search failed: {result.error}")
    else:
        print("✗ Query generation failed (not relevant)")

    print()

    # Test 2: Cybersecurity jobs
    print("Test 2: Cybersecurity Jobs")
    print("-" * 80)

    query2 = await usajobs.generate_query("cybersecurity jobs requiring clearance")

    if query2:
        print(f"✓ Query generated:")
        print(f"  Keywords: {query2.get('keywords')}")

        result2 = await usajobs.execute_search(query2, api_key=api_key, limit=3)

        if result2.success:
            print(f"✓ Search successful: {result2.total:,} results found")
            print(f"  Response time: {result2.response_time_ms:.0f}ms")
        else:
            print(f"✗ Search failed: {result2.error}")
    else:
        print("✗ Query generation failed")

    print()
    print("=" * 80)
    print("✅ USAJobs API test complete!")


if __name__ == "__main__":
    asyncio.run(main())
