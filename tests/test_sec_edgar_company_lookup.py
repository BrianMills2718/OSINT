#!/usr/bin/env python3
"""
Test SEC EDGAR company name lookup improvements.

Verifies that fuzzy matching and alias lookup can find major defense contractors
that were previously failing.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from integrations.government.sec_edgar_integration import SECEdgarIntegration
from dotenv import load_dotenv

load_dotenv()


async def test_company_lookup(company_name: str, description: str):
    """Test a single company lookup."""
    print(f"\n[TEST] {description}")
    print(f"  Input: '{company_name}'")
    print("="*80)

    integration = SECEdgarIntegration()

    # Test CIK lookup
    cik = await integration._search_company_cik(company_name)

    if cik:
        print(f"  ✅ CIK Found: {cik}")

        # Try to get filings to verify CIK works
        query_params = {
            "query_type": "company_filings",
            "company_name": company_name,
            "form_types": ["10-K"],
            "keywords": None,
            "limit": 5
        }

        result = await integration.execute_search(query_params, limit=5)

        if result.success:
            print(f"  ✅ Filings Retrieved: {result.total} documents")
            if result.results:
                first_filing = result.results[0]
                print(f"  📄 Sample: {first_filing['title']}")
            return True
        else:
            print(f"  ❌ Filing retrieval failed: {result.error}")
            return False
    else:
        print(f"  ❌ CIK Not Found")
        return False


async def main():
    """Run all company lookup tests."""
    print("\n" + "="*80)
    print("SEC EDGAR COMPANY LOOKUP TESTS")
    print("="*80)

    results = []

    # Test cases from production errors
    test_cases = [
        ("Northrop Grumman Corporation", "Production Error Case 1"),
        ("Raytheon Technologies Corporation", "Production Error Case 2 (rebranded to RTX)"),
        ("Lockheed Martin Corporation", "Common Defense Contractor"),
        ("Boeing Company", "Common Defense Contractor"),
        ("General Dynamics Corporation", "Common Defense Contractor"),
        ("Palantir Technologies", "Tech Defense Contractor"),
    ]

    for company_name, description in test_cases:
        success = await test_company_lookup(company_name, description)
        results.append((company_name, success))

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    passed = sum(1 for _, success in results if success)
    total = len(results)
    print(f"Tests Passed: {passed}/{total}\n")

    for company_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status}: {company_name}")

    if passed == total:
        print("\n✅ All tests passed - Company lookup working correctly")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
