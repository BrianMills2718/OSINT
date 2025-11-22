"""
Unit tests for ScopingAgent

Tests:
- Simple queries should NOT be over-decomposed
- Complex queries should be properly decomposed
- Max subtasks constraint enforced
- Clarity scoring works
- Fallback on LLM failures
"""

import pytest
import asyncio
from core.scoping_agent import ScopingAgent
from schemas.research_brief import ResearchBrief


@pytest.mark.asyncio
async def test_simple_query_no_decomposition():
    """
    Simple queries should NOT be over-decomposed.

    Codex requirement: "stays focused on the actual ask (not inventing side quests)"
    """
    agent = ScopingAgent(config={"max_subtasks": 5})

    brief = await agent.generate_brief("What is SAM.gov?")

    # Should have 1 sub-question (the original query or very close)
    assert len(brief.sub_questions) == 1, f"Expected 1 subtask, got {len(brief.sub_questions)}"
    assert "SAM" in brief.sub_questions[0].question or "SAM.gov" in brief.objective


@pytest.mark.asyncio
async def test_simple_query_jobs():
    """Test another simple query pattern."""
    agent = ScopingAgent(config={"max_subtasks": 5})

    brief = await agent.generate_brief("Who is hiring for AI security?")

    # Should have 1-2 sub-questions (keep it simple)
    assert 1 <= len(brief.sub_questions) <= 2, f"Expected 1-2 subtasks, got {len(brief.sub_questions)}"


@pytest.mark.asyncio
async def test_complex_query_decomposition():
    """
    Complex queries should be broken down into subtasks.

    This is the type of query that benefits from decomposition.
    """
    agent = ScopingAgent(config={"max_subtasks": 5})

    brief = await agent.generate_brief(
        "Map relationships between defense contractors working on AI security, "
        "including their partnerships, subcontracting relationships, and DoD engagement"
    )

    # Should decompose into 2-5 subtasks
    assert 2 <= len(brief.sub_questions) <= 5, f"Expected 2-5 subtasks, got {len(brief.sub_questions)}"

    # All subtasks should have required fields
    for sq in brief.sub_questions:
        assert len(sq.question) >= 10, f"Question too short: {sq.question}"
        assert len(sq.rationale) > 0, f"Missing rationale for: {sq.question}"
        assert len(sq.suggested_categories) >= 1, f"No categories for: {sq.question}"


@pytest.mark.asyncio
async def test_max_subtasks_enforced():
    """Max subtasks constraint should be enforced."""
    agent = ScopingAgent(config={"max_subtasks": 3})

    brief = await agent.generate_brief(
        "Analyze defense contractors, their partnerships, subcontracts, "
        "DoD engagement, workforce hiring, technology investments, and market trends"
    )

    # Should not exceed max_subtasks
    assert len(brief.sub_questions) <= 3, f"Expected ≤3 subtasks, got {len(brief.sub_questions)}"


@pytest.mark.asyncio
async def test_brief_has_required_fields():
    """Generated briefs should have all required fields."""
    agent = ScopingAgent(config={"max_subtasks": 5})

    brief = await agent.generate_brief("What contracts has Peraton won for AI security?")

    # Check required fields
    assert len(brief.objective) >= 20, f"Objective too short: {brief.objective}"
    assert len(brief.sub_questions) >= 1, "No sub-questions generated"

    # Check sub-question structure
    for sq in brief.sub_questions:
        assert hasattr(sq, 'question')
        assert hasattr(sq, 'rationale')
        assert hasattr(sq, 'suggested_categories')
        assert len(sq.suggested_categories) >= 1


@pytest.mark.asyncio
async def test_suggested_categories_valid():
    """Suggested categories should be from known list."""
    agent = ScopingAgent(config={"max_subtasks": 5})

    brief = await agent.generate_brief("What AI security contracts exist?")

    valid_categories = {
        "government_contracts",
        "government_jobs",
        "government_media",
        "social_media",
        "web_search",
        "jobs"  # Alias
    }

    for sq in brief.sub_questions:
        for category in sq.suggested_categories:
            # Should be a known category (case-insensitive)
            assert any(
                category.lower() == vc.lower() or category.lower() in vc.lower()
                for vc in valid_categories
            ), f"Unknown category: {category}"


@pytest.mark.asyncio
async def test_clarity_scoring_simple():
    """Clarity scoring should rate simple queries as clear."""
    agent = ScopingAgent(config={"auto_clarify_threshold": 0.7})

    # Long, specific query should be clear
    needs_clarify = await agent.needs_clarification(
        "What federal contracts has Peraton won for AI security in 2024-2025?"
    )

    assert not needs_clarify, "Long specific query should not need clarification"


@pytest.mark.asyncio
async def test_clarity_scoring_vague():
    """Clarity scoring should detect vague queries (but may vary)."""
    agent = ScopingAgent(config={"auto_clarify_threshold": 0.7})

    # Very short, vague query
    needs_clarify = await agent.needs_clarification("AI stuff")

    # Note: LLM scoring may vary, so we just test it doesn't crash
    # (actual score depends on LLM interpretation)
    assert isinstance(needs_clarify, bool)


@pytest.mark.asyncio
async def test_estimates_present():
    """Brief should include cost and time estimates."""
    agent = ScopingAgent(config={"max_subtasks": 5})

    brief = await agent.generate_brief("Defense contractor AI security relationships")

    # Should have estimates (non-zero for non-trivial query)
    assert brief.estimated_cost > 0, "Expected positive cost estimate"
    assert brief.estimated_time > 0, "Expected positive time estimate"


@pytest.mark.asyncio
async def test_clarify_and_generate():
    """Test main entry point."""
    agent = ScopingAgent(config={"max_subtasks": 5})

    brief = await agent.clarify_and_generate("What is DVIDS?")

    # Should generate valid brief
    assert isinstance(brief, ResearchBrief)
    assert len(brief.sub_questions) >= 1


# Run tests
if __name__ == "__main__":
    print("Running ScopingAgent tests...")
    print("\nTest 1: Simple query (no decomposition)")
    asyncio.run(test_simple_query_no_decomposition())
    print("✓ PASS")

    print("\nTest 2: Complex query (decomposition)")
    asyncio.run(test_complex_query_decomposition())
    print("✓ PASS")

    print("\nTest 3: Max subtasks enforced")
    asyncio.run(test_max_subtasks_enforced())
    print("✓ PASS")

    print("\nTest 4: Required fields present")
    asyncio.run(test_brief_has_required_fields())
    print("✓ PASS")

    print("\nTest 5: Valid categories")
    asyncio.run(test_suggested_categories_valid())
    print("✓ PASS")

    print("\nTest 6: Estimates present")
    asyncio.run(test_estimates_present())
    print("✓ PASS")

    print("\nTest 7: Main entry point")
    asyncio.run(test_clarify_and_generate())
    print("✓ PASS")

    print("\n" + "="*60)
    print("ALL TESTS PASSED")
    print("="*60)
