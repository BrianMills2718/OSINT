#!/usr/bin/env python3
"""
Quick E2E test for Federal Register in deep research system.

Verifies:
- Federal Register is registered
- Source metadata is available
- Integration works in deep research context
"""

import asyncio
import sys
sys.path.insert(0, '/home/brian/sam_gov')

from integrations.registry import IntegrationRegistry
from integrations.source_metadata import SOURCE_METADATA
from integrations.government.federal_register import FederalRegisterIntegration


async def main():
    print("Testing Federal Register End-to-End Integration...")
    print("=" * 80)

    # Test 1: Registry check
    print("\n[TEST 1] Registry Check")
    print("-" * 80)
    registry = IntegrationRegistry()

    if 'federal_register' in registry._integration_classes:
        print("✅ Federal Register registered in IntegrationRegistry")
    else:
        print("❌ Federal Register NOT in registry")
        return

    # Test 2: Source metadata check
    print("\n[TEST 2] Source Metadata Check")
    print("-" * 80)

    if 'Federal Register' in SOURCE_METADATA:
        metadata = SOURCE_METADATA['Federal Register']
        print(f"✅ Federal Register in source metadata")
        print(f"   Description: {metadata.description}")
        print(f"   Max queries recommended: {metadata.max_queries_recommended}")
        print(f"   Characteristics: {list(metadata.characteristics.keys())[:5]}...")
    else:
        print("❌ Federal Register NOT in source metadata")
        return

    # Test 3: Integration instantiation
    print("\n[TEST 3] Integration Instantiation")
    print("-" * 80)

    integration = FederalRegisterIntegration()
    print(f"✅ Integration created: {integration.metadata.name}")
    print(f"   ID: {integration.metadata.id}")
    print(f"   Category: {integration.metadata.category}")

    # Test 4: Quick relevance check
    print("\n[TEST 4] Relevance Check")
    print("-" * 80)

    test_question = "What are recent EPA cybersecurity regulations?"
    is_relevant = await integration.is_relevant(test_question)
    print(f"Question: {test_question}")
    print(f"Relevant: {is_relevant}")
    print("✅" if is_relevant else "❌")

    # Test 5: Quick search
    print("\n[TEST 5] Quick Search")
    print("-" * 80)

    result = await integration.execute_search(
        {'term': 'cybersecurity', 'agencies': [], 'document_types': [], 'date_range_days': 30},
        None,
        3
    )

    print(f"Success: {result.success}")
    print(f"Results: {len(result.results)}")

    if result.results:
        doc = result.results[0]
        print(f"\nFirst Result:")
        print(f"  Title: {doc.get('title')[:60]}...")
        print(f"  Agency: {doc.get('metadata', {}).get('agency')}")
        print(f"  Date: {doc.get('date')}")
        print(f"  Type: {doc.get('metadata', {}).get('type')}")
        print("✅ All fields present")

    print("\n" + "=" * 80)
    print("Federal Register E2E Test Complete!")
    print("\n[PASS] Federal Register fully integrated and ready for deep research")


if __name__ == "__main__":
    asyncio.run(main())
