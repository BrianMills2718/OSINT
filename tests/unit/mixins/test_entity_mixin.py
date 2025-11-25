#!/usr/bin/env python3
"""
Unit tests for EntityAnalysisMixin.

Tests:
- _extract_entities (mocked LLM)
- _update_entity_graph (pure logic with async lock)
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestExtractEntities:
    """Test _extract_entities method (mocked LLM)."""

    def setup_method(self):
        """Create mixin instance with mocked dependencies."""
        from research.mixins.entity_mixin import EntityAnalysisMixin

        class MockHost(EntityAnalysisMixin):
            entity_graph = {}

        self.host = MockHost()

    @pytest.mark.asyncio
    async def test_empty_results_returns_empty_list(self):
        """Empty results input returns empty list."""
        result = await self.host._extract_entities(
            results=[],
            research_question="What are defense contracts?",
            task_query="F-35 contracts"
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_extracts_entities_from_results(self):
        """LLM extracts entities from result titles and snippets."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "entities": ["Lockheed Martin", "F-35 Lightning II", "Department of Defense"]
        })

        with patch("research.mixins.entity_mixin.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            results = [
                {"title": "Lockheed Martin Wins F-35 Contract", "snippet": "DoD awards $1B"},
                {"title": "F-35 Lightning II Program Update", "description": "New capabilities"}
            ]

            entities = await self.host._extract_entities(
                results=results,
                research_question="What are F-35 contracts?",
                task_query="F-35 procurement"
            )

            assert len(entities) == 3
            assert "Lockheed Martin" in entities
            assert "F-35 Lightning II" in entities

    @pytest.mark.asyncio
    async def test_llm_error_returns_empty_list(self):
        """LLM errors return empty list (graceful degradation)."""
        with patch("research.mixins.entity_mixin.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = Exception("API Error")

            results = [{"title": "Test", "snippet": "Content"}]

            entities = await self.host._extract_entities(
                results=results,
                research_question="test",
                task_query="test"
            )

            assert entities == []

    @pytest.mark.asyncio
    async def test_handles_missing_entities_key(self):
        """Handles malformed LLM response gracefully."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "other_field": "no entities here"
        })

        with patch("research.mixins.entity_mixin.acompletion", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_response

            results = [{"title": "Test", "snippet": "Content"}]

            entities = await self.host._extract_entities(
                results=results,
                research_question="test",
                task_query="test"
            )

            # Should return empty list when key missing
            assert entities == []


class TestUpdateEntityGraph:
    """Test _update_entity_graph method (async lock handling)."""

    def setup_method(self):
        """Create mixin instance with mocked dependencies."""
        from research.mixins.entity_mixin import EntityAnalysisMixin

        class MockResourceManager:
            def __init__(self):
                self.entity_graph_lock = asyncio.Lock()

        class MockHost(EntityAnalysisMixin):
            entity_graph = {}
            resource_manager = MockResourceManager()

            def _emit_progress(self, event_type, message, task_id=None, data=None):
                self.progress_events = getattr(self, "progress_events", [])
                self.progress_events.append((event_type, message))

        self.host = MockHost()

    @pytest.mark.asyncio
    async def test_adds_entities_to_graph(self):
        """Entities are added to graph with relationships."""
        await self.host._update_entity_graph(["Lockheed Martin", "F-35", "DoD"])

        assert "lockheed martin" in self.host.entity_graph
        assert "f-35" in self.host.entity_graph
        assert "dod" in self.host.entity_graph

    @pytest.mark.asyncio
    async def test_creates_co_occurrence_relationships(self):
        """Entities appearing together are linked."""
        await self.host._update_entity_graph(["Entity A", "Entity B", "Entity C"])

        # Entity A should be connected to B and C
        assert "entity b" in self.host.entity_graph["entity a"]
        assert "entity c" in self.host.entity_graph["entity a"]

        # Entity B should be connected to C
        assert "entity c" in self.host.entity_graph["entity b"]

    @pytest.mark.asyncio
    async def test_normalizes_entity_names(self):
        """Entity names are normalized to lowercase."""
        await self.host._update_entity_graph(["LOCKHEED MARTIN", "Lockheed Martin", "lockheed martin"])

        # All should be same key (normalized)
        assert "lockheed martin" in self.host.entity_graph
        # Only one entry despite different cases
        assert len(self.host.entity_graph) == 1

    @pytest.mark.asyncio
    async def test_empty_entities_no_op(self):
        """Empty entity list is a no-op."""
        await self.host._update_entity_graph([])
        assert self.host.entity_graph == {}

    @pytest.mark.asyncio
    async def test_strips_whitespace(self):
        """Entity names are stripped of whitespace."""
        await self.host._update_entity_graph(["  Lockheed  ", "  F-35  "])

        assert "lockheed" in self.host.entity_graph
        assert "f-35" in self.host.entity_graph

    @pytest.mark.asyncio
    async def test_emits_relationship_events(self):
        """Progress events are emitted for new relationships."""
        await self.host._update_entity_graph(["Entity A", "Entity B"])

        # Should have emitted relationship_discovered events
        assert hasattr(self.host, "progress_events")
        assert len(self.host.progress_events) > 0
        assert self.host.progress_events[0][0] == "relationship_discovered"

    @pytest.mark.asyncio
    async def test_no_duplicate_relationships(self):
        """Same entity pair doesn't create duplicate relationships."""
        await self.host._update_entity_graph(["A", "B"])
        await self.host._update_entity_graph(["A", "B"])

        # Should only have one relationship
        assert len(self.host.entity_graph["a"]) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
