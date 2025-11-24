#!/usr/bin/env python3
"""Debug SEC EDGAR integration."""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from integrations.government.sec_edgar_integration import SECEdgarIntegration
from dotenv import load_dotenv

load_dotenv()


async def test_debug():
    integration = SECEdgarIntegration()

    # Test with NO form filter to see what's available
    params = {
        "query_type": "company_filings",
        "company_name": "Lockheed Martin Corporation",
        "form_types": [],  # No filter - get all forms
        "keywords": "offshore",
        "limit": 10
    }

    print(f"Testing with params: {params}")
    print()

    result = await integration.execute_search(params, limit=10)

    print(f"Success: {result.success}")
    print(f"Total: {result.total}")
    print(f"Error: {result.error}")
    print()

    for i, doc in enumerate(result.results[:5], 1):
        print(f"{i}. {doc['title']}")
        print(f"   Form: {doc['metadata']['form_type']}")
        print(f"   Extracted: {'Yes' if doc['metadata'].get('extracted_content') else 'No'}")
        print()


if __name__ == "__main__":
    asyncio.run(test_debug())
