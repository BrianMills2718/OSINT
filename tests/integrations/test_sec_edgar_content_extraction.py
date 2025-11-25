#!/usr/bin/env python3
"""
Test SEC EDGAR content extraction enhancement.

Validates that the integration now extracts actual document content
instead of just metadata.
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from integrations.government.sec_edgar import SECEdgarIntegration
from dotenv import load_dotenv

load_dotenv()


async def test_content_extraction():
    """Test SEC EDGAR with content extraction for Lockheed Martin offshore structures."""

    integration = SECEdgarIntegration()

    print("=" * 80)
    print("SEC EDGAR CONTENT EXTRACTION TEST")
    print("=" * 80)
    print()

    # Test query similar to the research question
    query = "Lockheed Martin foreign subsidiaries and offshore financial structures"

    print(f"Query: {query}")
    print()

    # Step 1: Generate query parameters
    print("[1/3] Generating query parameters...")
    params = await integration.generate_query(query)

    if not params:
        print("❌ FAIL: Integration determined query not relevant")
        return False

    print(f"✅ Query parameters generated:")
    print(f"  - Query type: {params.get('query_type')}")
    print(f"  - Company: {params.get('company_name')}")
    print(f"  - Form types: {params.get('form_types')}")
    print(f"  - Keywords: {params.get('keywords')}")
    print()

    # Step 2: Execute search with content extraction
    print("[2/3] Executing search with content extraction...")
    result = await integration.execute_search(params, limit=3)

    if not result.success:
        print(f"❌ FAIL: Search failed - {result.error}")
        return False

    print(f"✅ Search successful: {result.total} results")
    print()

    # Step 3: Validate content extraction
    print("[3/3] Validating extracted content...")
    print()

    extraction_found = False

    for i, doc in enumerate(result.results, 1):
        print(f"--- Document {i}: {doc['title']} ---")
        print(f"URL: {doc['url']}")
        print(f"Date: {doc['date']}")
        print()

        extracted = doc['metadata'].get('extracted_content')

        if extracted:
            extraction_found = True
            print("✅ Content extracted successfully!")
            print()
            print("Extracted Sections (preview):")
            print(extracted[:500] + "..." if len(extracted) > 500 else extracted)
            print()
        else:
            print("⚠️  No content extracted (may have failed to fetch)")
            print(f"Snippet: {doc['snippet']}")
            print()

        print("-" * 80)
        print()

    if extraction_found:
        print()
        print("=" * 80)
        print("✅ SUCCESS: Content extraction working!")
        print("=" * 80)
        print()
        print("Enhancement validated:")
        print("  - Integration fetches actual SEC documents")
        print("  - Parses HTML content")
        print("  - Extracts relevant sections based on keywords")
        print("  - Includes extracted content in metadata")
        print()
        return True
    else:
        print()
        print("=" * 80)
        print("⚠️  PARTIAL: Integration running but content extraction failed")
        print("=" * 80)
        print()
        print("Possible issues:")
        print("  - Document fetch timeout")
        print("  - HTML parsing failed")
        print("  - Section patterns didn't match")
        print()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_content_extraction())
    sys.exit(0 if success else 1)
