#!/usr/bin/env python3
"""
Phase 2: Entity Canonicalization

Identifies when entities across different reports refer to the same real-world entity.
Uses LLM to link "Igor Egorov" (report3) with "Col. Egorov" (report1), etc.
"""

import asyncio
import json
import sys
from datetime import datetime, UTC
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv
from llm_helper import acompletion

# Load environment variables
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


async def canonicalize_entities(all_reports_data: Dict) -> Dict:
    """
    Use LLM to identify entities that appear across multiple reports.

    Args:
        all_reports_data: Combined extraction data from all reports

    Returns:
        Canonical entity mapping
    """
    # Build entity summaries for each report
    report_summaries = []

    for report_data in all_reports_data["reports"]:
        report_id = report_data["metadata"]["report_id"]
        entities_summary = []

        for entity in report_data["entities"]:
            entities_summary.append({
                "id": entity["entity_id"],
                "name": entity["canonical_name"],
                "type": entity["entity_type"],
                "aliases": entity["aliases"]
            })

        report_summaries.append({
            "report_id": report_id,
            "entity_count": len(entities_summary),
            "entities": entities_summary
        })

    # Define JSON schema for canonicalization output
    canon_schema = {
        "type": "object",
        "properties": {
            "canonical_entities": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "canonical_id": {
                            "type": "string",
                            "description": "Unique ID for canonical entity (CANON_E1, CANON_E2, etc.)"
                        },
                        "canonical_name": {
                            "type": "string",
                            "description": "Best/most complete name for this entity"
                        },
                        "entity_type": {
                            "type": "string",
                            "enum": ["person", "organization", "location", "unit", "event", "concept"]
                        },
                        "source_entities": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "report_id": {"type": "string"},
                                    "entity_id": {"type": "string"},
                                    "name": {"type": "string"}
                                },
                                "required": ["report_id", "entity_id", "name"],
                                "additionalProperties": False
                            },
                            "description": "All source entities from individual reports that map to this canonical entity"
                        },
                        "all_aliases": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Combined list of all aliases from all source entities"
                        }
                    },
                    "required": ["canonical_id", "canonical_name", "entity_type", "source_entities", "all_aliases"],
                    "additionalProperties": False
                }
            },
            "metadata": {
                "type": "object",
                "properties": {
                    "total_canonical_entities": {"type": "integer"},
                    "cross_report_entities": {"type": "integer"},
                    "canonicalization_timestamp": {"type": "string"}
                },
                "required": ["total_canonical_entities", "cross_report_entities", "canonicalization_timestamp"],
                "additionalProperties": False
            }
        },
        "required": ["canonical_entities", "metadata"],
        "additionalProperties": False
    }

    # Build canonicalization prompt
    prompt = f"""You are an expert investigative analyst. You have entity lists from 3 different investigative reports about the MH17 investigation and Russian intelligence operations.

Your task: Identify which entities across the 3 reports refer to the SAME real-world entity.

REPORT ENTITIES:
{json.dumps(report_summaries, indent=2)}

INSTRUCTIONS:
1. For each unique real-world entity, create ONE canonical entity
2. Link all mentions of that entity across reports to the canonical entity
3. Choose the most complete/formal name as the canonical_name
4. Combine all aliases from all source entities
5. If an entity appears in only ONE report, still create a canonical entity for it (with one source_entity)

EXAMPLES OF ENTITIES TO LINK:
- "MH17" in report1 + "MH17" in report2 + "MH17" in report3 = SAME event
- "53rd Anti-Aircraft Brigade" in report1 + "53rd Brigade" in report2 = SAME unit
- "Igor Egorov" in report3 + "Col. Egorov" in report1 (if mentioned) = SAME person
- "Buk missile" in report1 + "BUK" in report3 = SAME concept
- "FSB" in all reports = SAME organization

EXAMPLES OF ENTITIES TO KEEP SEPARATE:
- "Donetsk" (city) ≠ "Donetsk People's Republic" (organization)
- "Elbrus" (person/codename) ≠ "Mount Elbrus" (location)
- Different people with similar roles but different names

Return a complete canonical entity mapping following the schema.
"""

    print(f"[Phase 2] Canonicalizing {sum(r['entity_count'] for r in report_summaries)} entities across {len(report_summaries)} reports...")
    print(f"[Phase 2] Calling LLM for cross-report entity linking...")

    response = await acompletion(
        model="gpt-5-mini",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "entity_canonicalization",
                "strict": True,
                "schema": canon_schema
            }
        }
    )

    # Parse the response
    result = json.loads(response.choices[0].message.content)

    # Add metadata
    result["metadata"]["total_canonical_entities"] = len(result["canonical_entities"])
    result["metadata"]["cross_report_entities"] = sum(
        1 for e in result["canonical_entities"]
        if len(set(se["report_id"] for se in e["source_entities"])) > 1
    )
    result["metadata"]["canonicalization_timestamp"] = datetime.now(UTC).isoformat()

    print(f"[Phase 2] ✓ Created {result['metadata']['total_canonical_entities']} canonical entities")
    print(f"[Phase 2] ✓ Found {result['metadata']['cross_report_entities']} entities appearing in 2+ reports")

    return result


async def main():
    """Main entry point for canonicalization."""

    print("[Phase 2] ===== Entity Canonicalization =====\n")

    # Load combined extraction data
    combined_path = Path(__file__).parent / "all_reports_raw.json"

    if not combined_path.exists():
        print(f"[ERROR] Combined data not found: {combined_path}")
        print(f"[ERROR] Run extract_all_reports.py first")
        return 1

    try:
        with open(combined_path, 'r', encoding='utf-8') as f:
            all_reports_data = json.load(f)

        # Canonicalize entities
        canonical_data = await canonicalize_entities(all_reports_data)

        # Save canonical mapping
        output_path = Path(__file__).parent / "canonical_entities.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(canonical_data, f, indent=2, ensure_ascii=False)

        print(f"\n[Phase 2] ✓ Canonical mapping saved to: {output_path.name}")

        # Print cross-report entity examples
        cross_report = [
            e for e in canonical_data["canonical_entities"]
            if len(set(se["report_id"] for se in e["source_entities"])) > 1
        ]

        if cross_report:
            print(f"\n[Phase 2] ===== Cross-Report Entities (examples) =====")
            for entity in cross_report[:5]:  # Show first 5
                reports = set(se["report_id"] for se in entity["source_entities"])
                print(f"[Phase 2]   - {entity['canonical_name']} ({entity['entity_type']}): {len(reports)} reports")

        print(f"\n[Phase 2] Next step: Run build_database.py to create SQLite database")

        return 0

    except Exception as e:
        print(f"[ERROR] Canonicalization failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
