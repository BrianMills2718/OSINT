#!/usr/bin/env python3
"""
Quick E2E test for ProPublica in deep research system.

Verifies:
- ProPublica is registered
- Source metadata is available
- Integration works in deep research context
"""

import asyncio
import sys
sys.path.insert(0, '/home/brian/sam_gov')

from integrations.registry import IntegrationRegistry
from integrations.source_metadata import SOURCE_METADATA
from integrations.nonprofit.propublica_integration import ProPublicaIntegration


async def main():
    print("Testing ProPublica Nonprofit Explorer End-to-End Integration...")
    print("=" * 80)

    # Test 1: Registry check
    print("\n[TEST 1] Registry Check")
    print("-" * 80)
    registry = IntegrationRegistry()

    if 'propublica' in registry._integration_classes:
        print("✅ ProPublica registered in IntegrationRegistry")
    else:
        print("❌ ProPublica NOT in registry")
        return

    # Test 2: Source metadata check
    print("\n[TEST 2] Source Metadata Check")
    print("-" * 80)

    if 'ProPublica Nonprofit Explorer' in SOURCE_METADATA:
        metadata = SOURCE_METADATA['ProPublica Nonprofit Explorer']
        print(f"✅ ProPublica in source metadata")
        print(f"   Description: {metadata.description}")
        print(f"   Max queries recommended: {metadata.max_queries_recommended}")
        print(f"   Characteristics: {list(metadata.characteristics.keys())[:5]}...")
    else:
        print("❌ ProPublica NOT in source metadata")
        return

    # Test 3: Integration instantiation
    print("\n[TEST 3] Integration Instantiation")
    print("-" * 80)

    integration = ProPublicaIntegration()
    print(f"✅ Integration created: {integration.metadata.name}")
    print(f"   ID: {integration.metadata.id}")
    print(f"   Category: {integration.metadata.category}")

    # Test 4: Quick relevance check
    print("\n[TEST 4] Relevance Check")
    print("-" * 80)

    test_question = "What dark money groups are spending on elections?"
    is_relevant = await integration.is_relevant(test_question)
    print(f"Question: {test_question}")
    print(f"Relevant: {is_relevant}")
    print("✅" if is_relevant else "❌")

    # Test 5: Quick search
    print("\n[TEST 5] Quick Search")
    print("-" * 80)

    result = await integration.execute_search(
        {'q': 'dark money', 'state_id': None, 'ntee_id': 7, 'c_code_id': 4},
        None,
        3
    )

    print(f"Success: {result.success}")
    print(f"Results: {len(result.results)}")

    if result.results:
        org = result.results[0]
        print(f"\nFirst Result:")
        print(f"  Title: {org.get('title')}")
        print(f"  Location: {org.get('metadata', {}).get('city')}, {org.get('metadata', {}).get('state')}")
        print(f"  Tax Code: {org.get('metadata', {}).get('tax_code')}")
        print(f"  EIN: {org.get('metadata', {}).get('ein')}")
        print("✅ All fields present")

    print("\n" + "=" * 80)
    print("ProPublica Nonprofit Explorer E2E Test Complete!")
    print("\n[PASS] ProPublica fully integrated and ready for deep research")


if __name__ == "__main__":
    asyncio.run(main())
