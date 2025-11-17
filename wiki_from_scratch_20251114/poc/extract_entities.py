#!/usr/bin/env python3
"""
Phase 1: Entity Extraction from Single Report

Extracts entities from a single investigative report using LLM with structured output.
Outputs to JSON for manual quality review.
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from dotenv import load_dotenv
from llm_helper import acompletion

# Load environment variables from parent sam_gov directory
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


async def extract_entities_from_report(report_path: str) -> Dict:
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
                                        "description": "Text excerpt mentioning this entity (verbatim from source)"
                                    },
                                    "char_start": {
                                        "type": "integer",
                                        "description": "Character position where snippet starts in source text"
                                    },
                                    "char_end": {
                                        "type": "integer",
                                        "description": "Character position where snippet ends in source text"
                                    },
                                    "context": {
                                        "type": "string",
                                        "description": "Brief description of what this mention reveals"
                                    }
                                },
                                "required": ["snippet", "char_start", "char_end", "context"],
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
6. **concept** - Key investigative topics (e.g., "assassination", "disinformation campaign")

INSTRUCTIONS:
- Extract ALL entities that match the types above
- For each entity, capture its CANONICAL NAME (most complete/formal version)
- List ALL ALIASES (nicknames, codenames, abbreviations, alternative spellings)
- For each mention, include:
  * SNIPPET: Verbatim text excerpt (1-2 sentences) from the source
  * CHAR_START: Character position where the snippet begins in the source text
  * CHAR_END: Character position where the snippet ends in the source text
  * CONTEXT: Brief description of what this mention reveals about the entity
- To find character positions, count from the beginning of the document (character 0)
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
    print(f"[Phase 1] Extracting entities from {report_path}...")
    print(f"[Phase 1] Report length: {len(report_text)} characters")
    print(f"[Phase 1] Calling LLM with structured output schema...")

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

    # Fix character offsets by finding snippets in source text
    print(f"[Phase 1] Validating and correcting character offsets...")
    corrected_count = 0
    for entity in result["entities"]:
        for mention in entity["mentions"]:
            snippet = mention["snippet"]
            llm_start = mention.get("char_start", 0)
            llm_end = mention.get("char_end", 0)

            # Try to find snippet in source text
            # Search in a window around the LLM's guess
            search_start = max(0, llm_start - 100)
            search_end = min(len(report_text), llm_end + 100)
            search_region = report_text[search_start:search_end]

            # Find the snippet
            offset_in_region = search_region.find(snippet)

            if offset_in_region != -1:
                # Found it - update offsets
                actual_start = search_start + offset_in_region
                actual_end = actual_start + len(snippet)

                if actual_start != llm_start or actual_end != llm_end:
                    corrected_count += 1

                mention["char_start"] = actual_start
                mention["char_end"] = actual_end
            else:
                # Couldn't find exact match - keep LLM's guess
                print(f"  Warning: Couldn't find exact match for snippet in {entity['canonical_name']}")

    print(f"[Phase 1] Corrected {corrected_count} character offsets")

    # Add report metadata
    report_name = Path(report_path).stem
    result["metadata"]["report_id"] = report_name
    result["metadata"]["total_entities_extracted"] = len(result["entities"])
    result["metadata"]["extraction_timestamp"] = datetime.utcnow().isoformat() + "Z"

    print(f"[Phase 1] ✓ Extracted {len(result['entities'])} entities")

    # Print entity summary
    entity_types = {}
    for entity in result["entities"]:
        entity_type = entity["entity_type"]
        entity_types[entity_type] = entity_types.get(entity_type, 0) + 1

    print(f"[Phase 1] Entity breakdown:")
    for entity_type, count in sorted(entity_types.items()):
        print(f"  - {entity_type}: {count}")

    return result


async def main():
    """Main entry point for Phase 1 entity extraction."""

    print("[Phase 1] Starting entity extraction...")
    print(f"[Phase 1] Working directory: {Path.cwd()}")
    print(f"[Phase 1] Script location: {Path(__file__).parent}")

    # Check for command-line argument, default to report3 if not provided
    if len(sys.argv) > 1:
        report_path = Path(sys.argv[1])
        if not report_path.is_absolute():
            # Make relative paths relative to script location
            report_path = Path(__file__).parent.parent / report_path
    else:
        # Default to report3 (FSB Elbrus investigation)
        report_path = Path(__file__).parent.parent / "test_data" / "report3_bellingcat_fsb_elbrus.md"

    print(f"[Phase 1] Looking for report at: {report_path}")

    if not report_path.exists():
        print(f"[ERROR] Report not found: {report_path}")
        print(f"[ERROR] Current directory: {Path.cwd()}")
        return 1

    print(f"[Phase 1] Found report: {report_path}")

    try:
        # Extract entities
        result = await extract_entities_from_report(str(report_path))

        # Save to JSON
        output_path = Path(__file__).parent / "phase1_output.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"\n[Phase 1] ✓ Results saved to: {output_path}")
        print(f"[Phase 1] Next step: Review {output_path} for extraction quality")
        print(f"[Phase 1] Check: Did it catch 80%+ of key entities? Low noise?")

        return 0

    except Exception as e:
        print(f"[ERROR] Extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
