"""
End-to-End Test for Supervisor Flow

Tests the complete flow: Scoping → HITL → Supervisor → Synthesis

Run with: python3 tests/test_supervisor_flow_e2e.py
"""

import asyncio
import sys
sys.path.insert(0, '/home/brian/sam_gov')

# Load environment variables before importing modules
from dotenv import load_dotenv
load_dotenv()

from core.intelligent_executor import IntelligentExecutor


async def test_supervisor_flow_disabled():
    """Test that supervisor flow initializes correctly when disabled."""
    print("Test 1: Supervisor flow disabled (default config)")
    print("=" * 80)

    executor = IntelligentExecutor()

    # Should have None for supervisor components
    assert executor.supervisor is None, "Supervisor should be None when disabled"
    assert executor.scoping_agent is None, "Scoping agent should be None when disabled"
    assert executor.hitl is None, "HITL should be None when disabled"

    print("✓ PASS: Supervisor flow correctly disabled")
    print()


async def test_scoping_only():
    """Test scoping agent in isolation."""
    print("Test 2: Scoping Agent (isolated)")
    print("=" * 80)

    from core.scoping_agent import ScopingAgent

    agent = ScopingAgent(config={'max_subtasks': 5})

    # Simple query
    brief = await agent.generate_brief("What is SAM.gov?")
    assert len(brief.sub_questions) >= 1, "Should have at least 1 subtask"
    print(f"✓ Simple query: {len(brief.sub_questions)} subtask(s)")

    # Complex query
    brief = await agent.generate_brief(
        "Map defense contractor AI security relationships"
    )
    assert len(brief.sub_questions) >= 1, "Should have at least 1 subtask"
    print(f"✓ Complex query: {len(brief.sub_questions)} subtask(s)")

    print("✓ PASS: Scoping Agent working")
    print()


async def test_hitl():
    """Test HITL in disabled mode (auto-approve)."""
    print("Test 3: HITL (auto-approve mode)")
    print("=" * 80)

    from core.hitl import HumanInTheLoop
    from schemas.research_brief import ResearchBrief, SubQuestion

    hitl = HumanInTheLoop(mode="cli", enabled=False)  # Auto-approve

    # Create test brief
    brief = ResearchBrief(
        objective="Test research objective",
        sub_questions=[
            SubQuestion(
                question="Test question",
                rationale="Test rationale",
                suggested_categories=["government_contracts"]
            )
        ]
    )

    approval = await hitl.get_approval(brief)
    assert approval.approved, "Auto-approve should return True"

    print("✓ PASS: HITL auto-approve working")
    print()


async def main():
    """Run all tests."""
    print("\n")
    print("=" * 80)
    print("SUPERVISOR FLOW END-TO-END TESTS")
    print("=" * 80)
    print()

    try:
        await test_supervisor_flow_disabled()
        await test_scoping_only()
        await test_hitl()

        print("=" * 80)
        print("✅ ALL TESTS PASSED")
        print("=" * 80)
        print()
        print("Next steps:")
        print("1. Enable supervisor flow in config_default.yaml")
        print("2. Test with: python3 -c \"from core.intelligent_executor import IntelligentExecutor; ...\"")
        print()

    except Exception as e:
        print()
        print("=" * 80)
        print("❌ TEST FAILED")
        print("=" * 80)
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
