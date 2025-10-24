#!/usr/bin/env python3
"""
Test crest_kg schema compatibility with gpt-5-mini strict JSON mode.

This validates that the Wikibase-compatible schema works with OpenAI's
strict JSON schema validation before implementing full integration.
"""

import asyncio
import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm_utils import acompletion
from dotenv import load_dotenv

load_dotenv()


async def test_crest_kg_schema():
    """Test if crest_kg schema works with gpt-5-mini strict JSON mode."""

    print("="*80)
    print("crest_kg Schema Validation Test")
    print("="*80)
    print()

    # Define crest_kg schema (Wikibase-compatible)
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

    # Test text with clear entities and relationships
    test_text = """
    Joint Special Operations Command (JSOC) works closely with the CIA on Title 50 covert operations.
    These operations are conducted in Afghanistan and other conflict zones.
    JSOC is headquartered at Fort Bragg, North Carolina.
    The CIA provides intelligence support for JSOC missions under Title 50 authority.
    """

    prompt = f"""Extract entities and relationships from this text in JSON format:

{test_text}

For each entity:
- Create a unique ID (e.g., "jsoc", "cia", "afghanistan")
- Identify the name
- Classify the type: person, organization, location, event, or concept
- Add relevant attributes (e.g., "headquarters": "Fort Bragg", "authority": "Title 50")

For each relationship:
- Identify source and target entity IDs
- Describe the relationship type (e.g., "works_with", "located_in", "provides_support")
- Add relevant attributes if applicable

Return ONLY valid JSON matching the schema."""

    print("Testing schema with gpt-5-mini...")
    print()

    try:
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

        # Parse response
        content = response.choices[0].message.content
        result = json.loads(content)

        print("✅ SCHEMA VALIDATION: PASS")
        print()
        print("Response structure:")
        print(f"  Entities: {len(result['entities'])}")
        print(f"  Relationships: {len(result['relationships'])}")
        print()

        # Show sample entity
        if result['entities']:
            print("Sample entity:")
            print(json.dumps(result['entities'][0], indent=2))
            print()

        # Show sample relationship
        if result['relationships']:
            print("Sample relationship:")
            print(json.dumps(result['relationships'][0], indent=2))
            print()

        # Check if attributes were populated
        entities_with_attrs = sum(1 for e in result['entities'] if e.get('attributes'))
        relationships_with_attrs = sum(1 for r in result['relationships'] if r.get('attributes'))

        print(f"Entities with attributes: {entities_with_attrs}/{len(result['entities'])}")
        print(f"Relationships with attributes: {relationships_with_attrs}/{len(result['relationships'])}")
        print()

        # Full result
        print("="*80)
        print("Full extraction result:")
        print("="*80)
        print(json.dumps(result, indent=2))

        return {
            "success": True,
            "entities_count": len(result['entities']),
            "relationships_count": len(result['relationships']),
            "entities_with_attrs": entities_with_attrs,
            "relationships_with_attrs": relationships_with_attrs,
            "result": result
        }

    except Exception as e:
        print(f"❌ SCHEMA VALIDATION: FAIL")
        print()
        print(f"Error: {type(e).__name__}: {str(e)}")
        import traceback
        print()
        print("Traceback:")
        print(traceback.format_exc())

        return {
            "success": False,
            "error": str(e)
        }


async def main():
    result = await test_crest_kg_schema()

    print()
    print("="*80)
    print("VERDICT")
    print("="*80)

    if result["success"]:
        print("✅ PASS - crest_kg schema is compatible with gpt-5-mini strict JSON mode")
        print()
        print("Evidence:")
        print(f"  - Schema accepted by OpenAI API")
        print(f"  - Entities extracted: {result['entities_count']}")
        print(f"  - Relationships extracted: {result['relationships_count']}")
        print(f"  - Attributes supported: {result['entities_with_attrs']} entities, {result['relationships_with_attrs']} relationships")
        print()
        print("Next: Proceed to Step 2 (quality comparison)")
        return 0
    else:
        print("❌ FAIL - Schema incompatible or other error")
        print()
        print(f"Error: {result['error']}")
        print()
        print("Action: Simplify schema (remove attributes?) or investigate error")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
