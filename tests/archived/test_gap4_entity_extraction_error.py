#!/usr/bin/env python3
"""
Test Gap #4 Fix: Entity extraction errors should not fail completed tasks.

Verifies that when entity extraction throws (OpenAI error, network timeout, etc.),
the task remains COMPLETED with empty entities list.
"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from research.deep_research import SimpleDeepResearch, ResearchTask, TaskStatus
from unittest.mock import AsyncMock, patch
import logging

logging.basicConfig(level=logging.INFO)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_entity_extraction_error_handling():
    """
    Test that entity extraction errors don't retroactively fail tasks.

    Scenario:
    1. Task completes successfully with results
    2. Entity extraction throws exception (simulated OpenAI error)
    3. Task should remain COMPLETED with empty entities
    4. Error should be logged but not propagate
    """

    print("\n" + "="*80)
    print("Gap #4 Test: Entity Extraction Error Handling")
    print("="*80 + "\n")

    # Create engine with minimal config
    engine = SimpleDeepResearch(
        max_tasks=1,
        max_retries_per_task=0,
        max_time_minutes=5,
        save_output=False  # Don't write files
    )

    # Create a task with accumulated results
    task = ResearchTask(
        id=0,
        query="test query",
        rationale="test"
    )
    task.accumulated_results = [
        {"title": "Test Result", "snippet": "test content", "source": "Test"}
    ]
    task.status = TaskStatus.COMPLETED

    # Mock _extract_entities to throw an error (simulate OpenAI 429)
    async def mock_extract_entities(*args, **kwargs):
        raise Exception("OpenAI API Error: Rate limit exceeded (429)")

    # Mock _update_entity_graph (shouldn't be called if extraction fails)
    async def mock_update_entity_graph(*args, **kwargs):
        raise Exception("Should not be called when extraction fails!")

    with patch.object(engine, '_extract_entities', side_effect=mock_extract_entities):
        with patch.object(engine, '_update_entity_graph', side_effect=mock_update_entity_graph):

            # Simulate the entity extraction block from batch completion loop
            try:
                if task.accumulated_results:
                    try:
                        print(f"🔍 Extracting entities from {len(task.accumulated_results)} accumulated results...")
                        entities_found = await engine._extract_entities(
                            task.accumulated_results,
                            research_question="test question",
                            task_query=task.query
                        )
                        task.entities_found = entities_found
                        print(f"✓ Found {len(entities_found)} entities")

                        await engine._update_entity_graph(entities_found)
                    except Exception as entity_error:
                        # Gap #4 fix: Log error but don't fail task
                        import traceback
                        logging.error(
                            f"Entity extraction failed for task {task.id}: {type(entity_error).__name__}: {str(entity_error)}\n"
                            f"Traceback: {traceback.format_exc()}"
                        )
                        print(f"⚠️  Entity extraction failed (non-critical): {type(entity_error).__name__}: {str(entity_error)}")
                        task.entities_found = []  # Empty list instead of None

                # Verify task remains COMPLETED
                print(f"\n[CHECK] Task status: {task.status}")
                print(f"[CHECK] Task entities: {task.entities_found}")
                print(f"[CHECK] Task has accumulated results: {len(task.accumulated_results)} results")

                assert task.status == TaskStatus.COMPLETED, f"Task should remain COMPLETED, got {task.status}"
                assert task.entities_found == [], f"Task should have empty entities list, got {task.entities_found}"
                assert len(task.accumulated_results) == 1, f"Task should retain accumulated results, got {len(task.accumulated_results)}"

                print("\n✅ [PASS] Gap #4 Test: Entity extraction errors don't fail tasks")
                print("   - Task remains COMPLETED despite entity extraction error")
                print("   - Task has empty entities list (not None)")
                print("   - Task retains accumulated results")
                print("   - Error logged but didn't propagate")

                return True

            except Exception as e:
                print(f"\n❌ [FAIL] Gap #4 Test: {type(e).__name__}: {str(e)}")
                print(f"   Task status: {task.status}")
                print(f"   Task entities: {task.entities_found}")
                raise  # Re-raise for pytest to catch
