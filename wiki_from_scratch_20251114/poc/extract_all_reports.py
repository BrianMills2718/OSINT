#!/usr/bin/env python3
"""
Phase 2: Multi-Report Entity Extraction

Extracts entities from all 3 Bellingcat reports and combines them.
"""

import asyncio
import json
import sys
from datetime import datetime, UTC
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv
from llm_helper import acompletion

# Load environment variables from parent sam_gov directory
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


async def extract_entities_from_report(report_path: Path) -> Dict:
    """
    Extract entities from a single investigative report.

    Args:
        report_path: Path to the markdown report file

    Returns:
        Dict with extracted entities and metadata
    """
    # Read the report
    with open(report_path, 'r', encoding='utf-8') as f:
        report_text = f.read()

    # Get report metadata from filename
    report_id = report_path.stem

    # Define the JSON schema for entity extraction
    entity_schema = {
        "type": "object",
        "properties": {
            "entities": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "entity_id": {
                            "type": "string",
                            "description": "Unique identifier (E1, E2, E3, etc.)"
                        },
                        "canonical_name": {
                            "type": "string",
                            "description": "Primary name for this entity"
                        },
                        "entity_type": {
                            "type": "string",
                            "enum": ["person", "organization", "location", "unit", "event", "concept"],
                            "description": "Category of entity"
                        },
                        "aliases": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Alternative names, codenames, abbreviations"
                        },
                        "mentions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "snippet": {
                                        "type": "string",
                                        "description": "Text excerpt mentioning this entity"
                                    },
                                    "context": {
                                        "type": "string",
                                        "description": "Brief description of what this mention reveals"
                                    }
                                },
                                "required": ["snippet", "context"],
                                "additionalProperties": False
                            },
                            "description": "All mentions of this entity in the report"
                        }
                    },
                    "required": ["entity_id", "canonical_name", "entity_type", "aliases", "mentions"],
                    "additionalProperties": False
                }
            },
            "metadata": {
                "type": "object",
                "properties": {
                    "report_id": {"type": "string"},
                    "total_entities_extracted": {"type": "integer"},
                    "extraction_timestamp": {"type": "string"}
                },
                "required": ["report_id", "total_entities_extracted", "extraction_timestamp"],
                "additionalProperties": False
            }
        },
        "required": ["entities", "metadata"],
        "additionalProperties": False
    }

    # Build the extraction prompt
    prompt = f"""You are an expert investigative journalism analyst. Extract ALL named entities from the following investigative report.

ENTITY TYPES:
1. **person** - Named individuals (e.g., "Col. Igor Egorov", "Adam Osmayev")
2. **organization** - Institutions, agencies (e.g., "FSB", "SBU", "Vympel")
3. **location** - Countries, cities, specific places (e.g., "Luhansk", "Hamburg", "Crimea")
4. **unit** - Military/intelligence formations (e.g., "53rd Anti-Aircraft Brigade", "Department V")
5. **event** - Named operations, incidents (e.g., "MH17", "annexation of Crimea")
6. **concept** - Key investigative topics (e.g., "Buk missile system", "disinformation campaign")

INSTRUCTIONS:
- Extract ALL entities that match the types above
- For each entity, capture its CANONICAL NAME (most complete/formal version)
- List ALL ALIASES (nicknames, codenames, abbreviations, alternative spellings)
- For each mention, include a SHORT SNIPPET (1-2 sentences) and CONTEXT (what this reveals about the entity)
- Link aliases to the same entity (e.g., "Egorov", "Elbrus", "Col. Egorov" are all the same person)
- Skip generic nouns ("the report", "the investigation", "military operations")
- Focus on PROPER NOUNS and named entities

REPORT TEXT:
---
{report_text}
---

Extract all entities following the schema. Be thorough - capture every named entity mentioned in the report.
"""

    # Call LLM with structured output
    print(f"[Phase 2] Extracting entities from {report_id}...")
    print(f"[Phase 2]   Report length: {len(report_text)} characters")

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
                "name": "entity_extraction",
                "strict": True,
                "schema": entity_schema
            }
        }
    )

    # Parse the response
    result = json.loads(response.choices[0].message.content)

    # Add report metadata
    result["metadata"]["report_id"] = report_id
    result["metadata"]["total_entities_extracted"] = len(result["entities"])
    result["metadata"]["extraction_timestamp"] = datetime.now(UTC).isoformat()

    print(f"[Phase 2]   ✓ Extracted {len(result['entities'])} entities")

    return result


async def main():
    """Main entry point for Phase 2 multi-report extraction."""

    print("[Phase 2] ===== Multi-Report Entity Extraction =====\n")

    # Define report paths
    test_data_dir = Path(__file__).parent.parent / "test_data"
    reports = [
        test_data_dir / "report1_bellingcat_mh17_origin.md",
        test_data_dir / "report2_bellingcat_gru_disinformation.md",
        test_data_dir / "report3_bellingcat_fsb_elbrus.md"
    ]

    # Check all reports exist
    for report_path in reports:
        if not report_path.exists():
            print(f"[ERROR] Report not found: {report_path}")
            return 1

    try:
        # Extract entities from each report
        all_results = []

        for report_path in reports:
            result = await extract_entities_from_report(report_path)
            all_results.append(result)

            # Save individual report JSON
            output_path = Path(__file__).parent / f"{report_path.stem}_entities.json"
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            print(f"[Phase 2]   Saved to: {output_path.name}\n")

        # Combine all results
        combined = {
            "reports": all_results,
            "summary": {
                "total_reports": len(all_results),
                "total_entities_across_reports": sum(r["metadata"]["total_entities_extracted"] for r in all_results),
                "extraction_timestamp": datetime.now(UTC).isoformat()
            }
        }

        # Save combined JSON
        combined_path = Path(__file__).parent / "all_reports_raw.json"
        with open(combined_path, 'w', encoding='utf-8') as f:
            json.dump(combined, f, indent=2, ensure_ascii=False)

        print(f"[Phase 2] ✓ Combined results saved to: {combined_path.name}")
        print(f"\n[Phase 2] ===== Summary =====")
        print(f"[Phase 2] Reports processed: {combined['summary']['total_reports']}")
        print(f"[Phase 2] Total entities: {combined['summary']['total_entities_across_reports']}")

        for result in all_results:
            report_id = result["metadata"]["report_id"]
            count = result["metadata"]["total_entities_extracted"]
            print(f"[Phase 2]   - {report_id}: {count} entities")

        print(f"\n[Phase 2] Next step: Run canonicalize_entities.py to link entities across reports")

        return 0

    except Exception as e:
        print(f"[ERROR] Extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
