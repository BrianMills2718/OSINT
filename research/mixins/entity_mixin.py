#!/usr/bin/env python3
"""
Entity analysis mixin for deep research.

Provides entity extraction and relationship graph management capabilities.
Extracted from SimpleDeepResearch to reduce god class complexity.
"""

import json
import logging
from typing import Dict, List, TYPE_CHECKING

from core.prompt_loader import render_prompt
from config_loader import config
from llm_utils import acompletion

if TYPE_CHECKING:
    from research.deep_research import SimpleDeepResearch

logger = logging.getLogger(__name__)


class EntityAnalysisMixin:
    """
    Mixin providing entity extraction and relationship tracking.

    Requires host class to have:
        - self.entity_graph: Dict[str, List[str]]
        - self.resource_manager.entity_graph_lock: asyncio.Lock
        - self._emit_progress(event_type: str, message: str): method
    """

    # Type hints for attributes from host class (for IDE support)
    entity_graph: Dict[str, List[str]]

    async def _extract_entities(
        self: "SimpleDeepResearch",
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

        # Use ALL results for entity extraction (LLM has 1M token context, will prioritize most important)
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

        try:
            response = await acompletion(
                model=config.get_model("query_generation"),
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

        # Exception caught - error logged, execution continues
        except Exception as e:
            logger.error(f"Entity extraction failed: {type(e).__name__}: {str(e)}", exc_info=True)
            return []

    async def _update_entity_graph(self: "SimpleDeepResearch", entities: List[str]):
        """
        Update entity relationship graph.

        Uses ResourceManager lock to prevent concurrent modification races.
        Normalizes entity names to lowercase to prevent case-variant duplicates.
        """
        async with self.resource_manager.entity_graph_lock:
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
