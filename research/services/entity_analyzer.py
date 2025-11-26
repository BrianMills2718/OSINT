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

    # JSON schema for entity extraction
    EXTRACTION_SCHEMA = {
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

    def __init__(
        self,
        progress_callback: Optional[Callable[[str, str], None]] = None
    ):
        """
        Initialize entity analyzer.

        Args:
            progress_callback: Optional callback(event_type, message) for progress updates
        """
        self.entity_graph: Dict[str, List[str]] = {}
        self._lock = asyncio.Lock()
        self._progress_callback = progress_callback

    def _emit_progress(self, event_type: str, message: str):
        """Emit progress event if callback is set."""
        if self._progress_callback:
            self._progress_callback(event_type, message)

    def get_entity_graph(self) -> Dict[str, List[str]]:
        """Get the current entity relationship graph."""
        return self.entity_graph

    def get_all_entities(self) -> List[str]:
        """Get all unique entities discovered."""
        return list(self.entity_graph.keys())

    def get_related_entities(self, entity: str) -> List[str]:
        """Get entities related to a given entity."""
        normalized = entity.strip().lower()
        return self.entity_graph.get(normalized, [])

    async def extract_entities(
        self,
        results: List[Dict],
        research_question: str,
        task_query: str
    ) -> List[str]:
        """
        Extract entities from search results using LLM.

        Args:
            results: List of search results
            research_question: Original research question (for context)
            task_query: Task query that generated these results

        Returns:
            List of entity names found
        """
        if not results:
            return []

        # Use ALL results for entity extraction
        # (LLM has 1M token context, will prioritize most important)
        sample = results

        # Build prompt with result titles and snippets
        results_text = "\n\n".join([
            f"Title: {r.get('title', '')}\nSnippet: {r.get('snippet', r.get('description', ''))[:200]}"
            for r in sample
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
            return result.get("entities", [])

        except Exception as e:
            logger.error(f"Entity extraction failed: {type(e).__name__}: {str(e)}", exc_info=True)
            return []

    async def update_entity_graph(self, entities: List[str]):
        """
        Update entity relationship graph.

        Uses internal lock to prevent concurrent modification races.
        Normalizes entity names to lowercase to prevent case-variant duplicates.

        Args:
            entities: List of entity names discovered together
        """
        async with self._lock:
            # Normalize entity names to lowercase to prevent duplicates
            # Convert "2210 Series" and "2210 series" to the same key
            normalized_entities = [e.strip().lower() for e in entities if e.strip()]

            # Co-occurrence tracking: entities appearing in the same result are related.
            # This is a fast heuristic that works well for investigative research.
            # Future enhancement: LLM-based relationship extraction for richer semantics
            # (e.g., "contractor for", "acquired by", "subsidiary of").
            for i, entity1 in enumerate(normalized_entities):
                if entity1 not in self.entity_graph:
                    self.entity_graph[entity1] = []

                for entity2 in normalized_entities[i+1:]:
                    if entity2 not in self.entity_graph[entity1]:
                        self.entity_graph[entity1].append(entity2)
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
            List of entity names found
        """
        entities = await self.extract_entities(results, research_question, task_query)
        if entities:
            await self.update_entity_graph(entities)
        return entities
