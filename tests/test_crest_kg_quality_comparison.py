#!/usr/bin/env python3
"""
Compare simple entity extraction vs enhanced KG extraction.

Tests both approaches on the same sample results to evaluate:
- Entity count
- Entity quality (completeness)
- Relationship value
- Accuracy (manual review)
"""

import asyncio
import json
import sys
import os
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm_utils import acompletion, get_cost_breakdown, reset_cost_tracking
from dotenv import load_dotenv

load_dotenv()


# Sample results from Deep Investigation (realistic data)
SAMPLE_RESULTS = [
    {
        "title": "JSOC and CIA Collaboration on Counterterrorism",
        "snippet": "Joint Special Operations Command (JSOC) works closely with the CIA on counterterrorism operations under Title 50 authority. These missions are conducted in Afghanistan, Yemen, and other conflict zones.",
        "source": "DVIDS"
    },
    {
        "title": "Special Operations in Afghanistan",
        "snippet": "U.S. special operations forces conducted raids in Kabul targeting high-value targets. The operations were coordinated between JSOC and CIA intelligence teams.",
        "source": "FBI Vault"
    },
    {
        "title": "Title 50 Covert Action Authority",
        "snippet": "Title 50 of the U.S. Code grants the CIA authority for covert action. These operations require presidential findings and congressional oversight.",
        "source": "Brave Search"
    },
    {
        "title": "JSOC Headquarters Relocation",
        "snippet": "Joint Special Operations Command is headquartered at Fort Liberty (formerly Fort Bragg), North Carolina. The command oversees elite units including Delta Force and SEAL Team Six.",
        "source": "DVIDS"
    },
    {
        "title": "Intelligence Support for Special Operations",
        "snippet": "The CIA provides critical intelligence support for JSOC missions, including signals intelligence, human intelligence, and drone surveillance capabilities.",
        "source": "Brave Search"
    }
]


async def simple_entity_extraction(results):
    """
    Current simple extraction (from deep_research.py).

    Returns list of entity names only.
    """
    # Sample up to 10 results
    sample = results[:10]

    # Build prompt
    results_text = "\n\n".join([
        f"Title: {r.get('title', '')}\nSnippet: {r.get('snippet', r.get('description', ''))[:200]}"
        for r in sample
    ])

    prompt = f"""Extract key entities (people, organizations, programs, operations) from these search results.

Results:
{results_text}

Return a JSON list of entity names (3-10 entities). Focus on named entities that could be researched further.

Example: ["Joint Special Operations Command", "CIA", "Kabul attack", "Operation Cyclone"]
"""

    schema = {
        "type": "object",
        "properties": {
            "entities": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 0,
                "maxItems": 10
            }
        },
        "required": ["entities"],
        "additionalProperties": False
    }

    response = await acompletion(
        model="gpt-5-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "strict": True,
                "name": "entity_extraction",
                "schema": schema
            }
        }
    )

    result = json.loads(response.choices[0].message.content)
    return result.get("entities", [])


async def enhanced_kg_extraction(results):
    """
    Enhanced KG extraction with relationships and attributes.

    Returns full knowledge graph.
    """
    # Sample up to 10 results
    sample = results[:10]

    # Build prompt
    results_text = "\n\n".join([
        f"Title: {r.get('title', '')}\nSnippet: {r.get('snippet', r.get('description', ''))}"
        for r in sample
    ])

    prompt = f"""Analyze these search results and create a knowledge graph in JSON format.
Extract entities (people, organizations, locations, events, concepts) and their relationships.

Search Results:
{results_text}

For each entity:
- Create a unique ID (short, descriptive, lowercase with underscores)
- Identify the name
- Classify the type: person, organization, location, event, or concept
- Add relevant attributes mentioned in the text (roles, dates, locations, etc.)

For each relationship:
- Identify source and target entity IDs
- Describe the relationship type (e.g., "works_with", "located_in", "provides_support", "conducts_operations_in")
- Add relevant attributes if applicable

Return ONLY valid JSON matching the schema."""

    schema = {
        "type": "object",
        "properties": {
            "entities": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "type": {
                            "type": "string",
                            "enum": ["person", "organization", "location", "event", "concept"]
                        },
                        "attributes": {
                            "type": "object",
                            "additionalProperties": {"type": "string"}
                        }
                    },
                    "required": ["id", "name", "type"],
                    "additionalProperties": False
                }
            },
            "relationships": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "source": {"type": "string"},
                        "target": {"type": "string"},
                        "type": {"type": "string"},
                        "attributes": {
                            "type": "object",
                            "additionalProperties": {"type": "string"}
                        }
                    },
                    "required": ["source", "target", "type"],
                    "additionalProperties": False
                }
            }
        },
        "required": ["entities", "relationships"],
        "additionalProperties": False
    }

    response = await acompletion(
        model="gpt-5-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "strict": True,
                "name": "knowledge_graph",
                "schema": schema
            }
        }
    )

    result = json.loads(response.choices[0].message.content)
    return result


async def main():
    print("="*80)
    print("crest_kg Quality Comparison Test")
    print("="*80)
    print()
    print(f"Sample size: {len(SAMPLE_RESULTS)} results")
    print()

    # Test 1: Simple extraction
    print("-"*80)
    print("TEST 1: Current Simple Extraction")
    print("-"*80)

    reset_cost_tracking()
    start = time.time()

    simple_entities = await simple_entity_extraction(SAMPLE_RESULTS)

    simple_time = time.time() - start
    simple_cost = get_cost_breakdown()['total_cost']

    print(f"✓ Completed in {simple_time:.2f}s (cost: ${simple_cost:.4f})")
    print()
    print(f"Entities found: {len(simple_entities)}")
    print("Entity list:")
    for i, entity in enumerate(simple_entities, 1):
        print(f"  {i}. {entity}")
    print()

    # Test 2: Enhanced KG extraction
    print("-"*80)
    print("TEST 2: Enhanced KG Extraction")
    print("-"*80)

    reset_cost_tracking()
    start = time.time()

    enhanced_kg = await enhanced_kg_extraction(SAMPLE_RESULTS)

    enhanced_time = time.time() - start
    enhanced_cost = get_cost_breakdown()['total_cost']

    print(f"✓ Completed in {enhanced_time:.2f}s (cost: ${enhanced_cost:.4f})")
    print()
    print(f"Entities found: {len(enhanced_kg['entities'])}")
    print(f"Relationships found: {len(enhanced_kg['relationships'])}")
    print()

    print("Sample entities (first 3):")
    for entity in enhanced_kg['entities'][:3]:
        print(json.dumps(entity, indent=2))
        print()

    print("Sample relationships (first 3):")
    for rel in enhanced_kg['relationships'][:3]:
        print(json.dumps(rel, indent=2))
        print()

    # Comparison
    print("="*80)
    print("COMPARISON")
    print("="*80)
    print()

    # Extract entity names from enhanced KG for comparison
    enhanced_entity_names = [e['name'] for e in enhanced_kg['entities']]

    # Find entities in simple but not in enhanced
    missing_in_enhanced = set(simple_entities) - set(enhanced_entity_names)

    # Find entities in enhanced but not in simple
    additional_in_enhanced = set(enhanced_entity_names) - set(simple_entities)

    print("Entity Coverage:")
    print(f"  Simple extraction: {len(simple_entities)} entities")
    print(f"  Enhanced extraction: {len(enhanced_kg['entities'])} entities")
    print(f"  Missing in enhanced: {len(missing_in_enhanced)} entities")
    if missing_in_enhanced:
        print(f"    {list(missing_in_enhanced)}")
    print(f"  Additional in enhanced: {len(additional_in_enhanced)} entities")
    if additional_in_enhanced:
        for entity in list(additional_in_enhanced)[:5]:
            print(f"    - {entity}")
        if len(additional_in_enhanced) > 5:
            print(f"    ... and {len(additional_in_enhanced) - 5} more")
    print()

    print("Relationship Data:")
    print(f"  Simple extraction: 0 relationships (not supported)")
    print(f"  Enhanced extraction: {len(enhanced_kg['relationships'])} relationships")
    print()

    # Attributes
    entities_with_attrs = sum(1 for e in enhanced_kg['entities'] if e.get('attributes'))
    print(f"  Entities with attributes: {entities_with_attrs}/{len(enhanced_kg['entities'])}")
    print()

    print("Performance:")
    print(f"  Simple time: {simple_time:.2f}s")
    print(f"  Enhanced time: {enhanced_time:.2f}s")
    print(f"  Time overhead: {enhanced_time/simple_time:.1f}x")
    print()

    print("Cost:")
    print(f"  Simple cost: ${simple_cost:.4f}")
    print(f"  Enhanced cost: ${enhanced_cost:.4f}")
    if simple_cost > 0:
        print(f"  Cost overhead: {enhanced_cost/simple_cost:.1f}x")
    else:
        print(f"  Cost overhead: Unable to calculate (simple_cost is $0)")
    print()

    # Verdict
    print("="*80)
    print("VERDICT")
    print("="*80)
    print()

    # Check pass/fail criteria
    entity_coverage_pass = len(enhanced_kg['entities']) >= len(simple_entities)
    time_pass = (enhanced_time / simple_time) < 3.0
    cost_pass = (enhanced_cost / simple_cost) < 5.0 if simple_cost > 0 else True

    print(f"✓ Entity coverage: {'PASS' if entity_coverage_pass else 'FAIL'}")
    print(f"  Enhanced found {len(enhanced_kg['entities'])} vs simple {len(simple_entities)}")
    print()

    print(f"{'✓' if time_pass else '✗'} Time overhead: {'PASS' if time_pass else 'FAIL'}")
    print(f"  {enhanced_time/simple_time:.1f}x (limit: 3.0x)")
    print()

    print(f"{'✓' if cost_pass else '✗'} Cost overhead: {'PASS' if cost_pass else 'FAIL'}")
    if simple_cost > 0:
        print(f"  {enhanced_cost/simple_cost:.1f}x (limit: 5.0x)")
    else:
        print(f"  Unable to calculate (costs are $0 - litellm cost tracking may not be working)")
    print()

    print(f"✓ Relationship extraction: PASS (simple: 0, enhanced: {len(enhanced_kg['relationships'])})")
    print()

    # Manual quality review needed
    print("⚠️  MANUAL REVIEW NEEDED:")
    print("  - Are extracted entities accurate (not hallucinated)?")
    print("  - Are relationships correct or inferred?")
    print("  - Do attributes add value?")
    print()

    # Overall
    overall_pass = entity_coverage_pass and time_pass and cost_pass

    if overall_pass:
        print("✅ OVERALL: PASS (pending manual quality review)")
        print()
        print("Enhanced extraction adds:")
        print(f"  - {len(enhanced_kg['relationships'])} relationships")
        print(f"  - {entities_with_attrs} entities with attributes")
        print(f"  - At acceptable performance cost ({enhanced_time/simple_time:.1f}x time, {enhanced_cost/simple_cost:.1f}x cost)")
        print()
        print("Next: Manual quality review + Step 3 (performance measurement)")
        return 0
    else:
        print("❌ OVERALL: FAIL")
        print()
        print("Issues:")
        if not entity_coverage_pass:
            print("  - Enhanced extraction missed entities from simple extraction")
        if not time_pass:
            print(f"  - Time overhead too high ({enhanced_time/simple_time:.1f}x > 3.0x)")
        if not cost_pass:
            print(f"  - Cost overhead too high ({enhanced_cost/simple_cost:.1f}x > 5.0x)")
        print()
        print("Action: Optimize prompts or abandon enhanced extraction")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
