#!/usr/bin/env python3
"""
Entity analysis service for deep research.

Provides entity extraction and relationship graph management.
Extracted from EntityAnalysisMixin to enable composition over inheritance.

This service owns its state (entity_graph) and manages concurrent access
internally, rather than relying on external locks.
"""

import asyncio
import json
import logging
from typing import Any, Callable, Dict, List, Optional

from core.prompt_loader import render_prompt
from config_loader import config
from llm_utils import acompletion

logger = logging.getLogger(__name__)


class EntityAnalyzer:
    """
    Service for entity extraction and relationship tracking.

    Owns its state (entity_graph) and manages concurrent access internally.
    Can emit progress events via optional callback.
    """

    # JSON schema for entity extraction (with source evidence)
    EXTRACTION_SCHEMA = {
        "type": "object",
        "properties": {
            "entities": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Entity name (standardized form)"
                        },
                        "source_indices": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "Which result indices mention this entity"
                        },
                        "evidence": {
                            "type": "string",
                            "description": "Brief quote or paraphrase proving entity exists in results"
                        }
                    },
                    "required": ["name", "source_indices", "evidence"],
                    "additionalProperties": False
                },
                "minItems": 0,
                "maxItems": 10
            }
        },
        "required": ["entities"],
        "additionalProperties": False
    }

    def __init__(
        self,
        progress_callback: Optional[Callable[[str, str], None]] = None
    ):
        """
        Initialize entity analyzer.

        Args:
            progress_callback: Optional callback(event_type, message) for progress updates
        """
        # Entity graph: entity_name -> {related_entities: [...], evidence: [...], source_count: int}
        self.entity_graph: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        self._progress_callback = progress_callback

    def _emit_progress(self, event_type: str, message: str):
        """Emit progress event if callback is set."""
        if self._progress_callback:
            self._progress_callback(event_type, message)

    def get_entity_graph(self) -> Dict[str, Dict[str, Any]]:
        """Get the current entity relationship graph."""
        return self.entity_graph

    def get_all_entities(self) -> List[str]:
        """Get all unique entities discovered."""
        return list(self.entity_graph.keys())

    def get_related_entities(self, entity: str) -> List[str]:
        """Get entities related to a given entity."""
        normalized = entity.strip().lower()
        entity_data = self.entity_graph.get(normalized, {})
        return entity_data.get("related_entities", [])

    def get_entity_evidence(self, entity: str) -> List[str]:
        """Get evidence for a specific entity."""
        normalized = entity.strip().lower()
        entity_data = self.entity_graph.get(normalized, {})
        return entity_data.get("evidence", [])

    async def extract_entities(
        self,
        results: List[Dict],
        research_question: str,
        task_query: str
    ) -> List[Dict]:
        """
        Extract entities from search results using LLM.

        Args:
            results: List of search results
            research_question: Original research question (for context)
            task_query: Task query that generated these results

        Returns:
            List of entity dicts with keys: name, source_indices, evidence
        """
        if not results:
            return []

        # Use ALL results for entity extraction
        # (LLM has 1M token context, will prioritize most important)
        sample = results

        # Build prompt with result titles and snippets (numbered for reference)
        results_text = "\n\n".join([
            f"Result #{i}:\nTitle: {r.get('title', '')}\nSnippet: {r.get('snippet', r.get('description', ''))[:200]}"
            for i, r in enumerate(sample)
        ])

        prompt = render_prompt(
            "deep_research/entity_extraction.j2",
            research_question=research_question,
            task_query=task_query,
            results_text=results_text
        )

        try:
            response = await acompletion(
                model=config.get_model("query_generation"),
                messages=[{"role": "user", "content": prompt}],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "strict": True,
                        "name": "entity_extraction",
                        "schema": self.EXTRACTION_SCHEMA
                    }
                }
            )

            result = json.loads(response.choices[0].message.content)
            entities = result.get("entities", [])

            # Log evidence for transparency
            for entity in entities:
                logger.info(
                    f"Entity extracted: {entity.get('name')} "
                    f"(sources: {entity.get('source_indices')}, "
                    f"evidence: {entity.get('evidence', '')[:50]}...)"
                )

            return entities

        except Exception as e:
            logger.error(f"Entity extraction failed: {type(e).__name__}: {str(e)}", exc_info=True)
            return []

    async def update_entity_graph(self, entities: List[Dict]):
        """
        Update entity relationship graph with evidence.

        Uses internal lock to prevent concurrent modification races.
        Normalizes entity names to lowercase to prevent case-variant duplicates.

        Args:
            entities: List of entity dicts with keys: name, source_indices, evidence
        """
        async with self._lock:
            # Extract entity names and evidence
            entity_data_list = []
            for entity in entities:
                if isinstance(entity, dict):
                    name = entity.get("name", "").strip().lower()
                    evidence = entity.get("evidence", "")
                    source_indices = entity.get("source_indices", [])
                    if name:
                        entity_data_list.append({
                            "name": name,
                            "evidence": evidence,
                            "source_indices": source_indices
                        })
                elif isinstance(entity, str):
                    # Backward compatibility: handle legacy string format
                    name = entity.strip().lower()
                    if name:
                        entity_data_list.append({
                            "name": name,
                            "evidence": "",
                            "source_indices": []
                        })

            # Update entity graph with evidence
            for entity_data in entity_data_list:
                name = entity_data["name"]
                evidence = entity_data["evidence"]

                if name not in self.entity_graph:
                    self.entity_graph[name] = {
                        "related_entities": [],
                        "evidence": [],
                        "source_count": 0
                    }

                # Add evidence if not already present
                if evidence and evidence not in self.entity_graph[name]["evidence"]:
                    self.entity_graph[name]["evidence"].append(evidence)

                # Increment source count
                self.entity_graph[name]["source_count"] += len(entity_data["source_indices"])

            # Co-occurrence tracking: entities appearing in the same batch are related
            entity_names = [e["name"] for e in entity_data_list]
            for i, entity1 in enumerate(entity_names):
                for entity2 in entity_names[i+1:]:
                    if entity2 not in self.entity_graph[entity1]["related_entities"]:
                        self.entity_graph[entity1]["related_entities"].append(entity2)
                        self._emit_progress(
                            "relationship_discovered",
                            f"Connected: {entity1} <-> {entity2}"
                        )

    async def extract_and_update(
        self,
        results: List[Dict],
        research_question: str,
        task_query: str
    ) -> List[str]:
        """
        Convenience method to extract entities and update graph in one call.

        Args:
            results: List of search results
            research_question: Original research question (for context)
            task_query: Task query that generated these results

        Returns:
            List of entity names found (strings for backward compatibility)
        """
        entities = await self.extract_entities(results, research_question, task_query)
        if entities:
            await self.update_entity_graph(entities)

        # Return entity names for backward compatibility
        return [
            e.get("name", "") if isinstance(e, dict) else str(e)
            for e in entities
        ]
