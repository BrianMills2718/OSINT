#!/usr/bin/env python3
"""
Test the complete intelligent research assistant (all 7 phases).

Demonstrates:
- Phase 1-3: Search across databases
- Phase 4-5: Automatic refinement
- Phase 6: Quantitative + qualitative analysis
- Phase 7: Synthesized answer

Shows quantitative analysis including trend/surge detection.
"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")

from core.intelligent_executor import IntelligentExecutor
from database_registry import registry
from integrations.clearancejobs_integration import ClearanceJobsIntegration
from integrations.dvids_integration import DVIDSIntegration
from integrations.sam_integration import SAMIntegration


async def test_research_assistant():
    """Test complete intelligent research workflow."""

    print("=" * 80)
    print("INTELLIGENT RESEARCH ASSISTANT - Full Demo")
    print("All 7 Phases: Search → Refine → Analyze → Synthesize")
    print("=" * 80)

    # Register databases
    registry.register(ClearanceJobsIntegration())
    registry.register(DVIDSIntegration())
    registry.register(SAMIntegration())

    api_keys = {
        "dvids": os.getenv("DVIDS_API_KEY", ""),
        "sam": os.getenv("SAM_GOV_API_KEY", ""),
    }

    available = registry.list_available(api_keys)
    print(f"\n📚 Databases: {len(available)} available")
    for db in available:
        print(f"   • {db.metadata.name}")

    # Create intelligent executor
    executor = IntelligentExecutor(
        max_concurrent=5,
        max_refinements=2,
        llm_model="gpt-5-mini"
    )

    # Test with a research question
    research_question = "What cybersecurity positions are currently in demand?"

    print(f"\n🔬 Research Question:")
    print(f"   \"{research_question}\"")
    print()

    # Execute complete research
    response = await executor.research(
        research_question=research_question,
        databases=available,
        api_keys=api_keys,
        limit=10,
        analyze=True  # Include Phase 6-7
    )

    # Display results
    print("\n" + executor.format_answer(response))

    # Show quantitative analysis details
    if "analysis" in response:
        analysis = response["analysis"]

        if "distributions" in analysis["quantitative"]:
            print("\n" + "=" * 80)
            print("QUANTITATIVE ANALYSIS DETAILS")
            print("=" * 80)

            for db, dist in analysis["quantitative"]["distributions"].items():
                print(f"\n{db}:")
                for category, data in dist.items():
                    print(f"\n  {category.replace('_', ' ').title()}:")
                    print(f"    Total unique: {data['total_unique']}")
                    print(f"    Top values:")
                    for item in data["top_10"][:5]:
                        print(f"      • {item['value']}: {item['count']} ({item['count']/data['total_items']*100:.1f}%)")


async def test_trend_detection():
    """Test trend/surge detection capabilities."""

    print("\n\n" + "=" * 80)
    print("TREND DETECTION TEST")
    print("=" * 80)

    registry.register(ClearanceJobsIntegration())

    executor = IntelligentExecutor()

    # Question designed to reveal location/position trends
    question = "Where are most cybersecurity jobs being posted?"

    print(f"\nQuestion: {question}\n")

    response = await executor.research(
        research_question=question,
        databases=[ClearanceJobsIntegration()],
        api_keys={},
        limit=50,  # More results for better trend analysis
        analyze=True
    )

    # Display surge detection
    if "analysis" in response and "qualitative" in response["analysis"]:
        qual = response["analysis"]["qualitative"]

        if "surges" in qual and qual["surges"]:
            print("\n🔥 Detected Surges/Trends:")
            for surge in qual["surges"]:
                print(f"\n  Type: {surge['type']}")
                print(f"  Value: {surge['value']}")
                print(f"  Significance: {surge['significance']}")
        else:
            print("\n📊 No significant surges detected (data may be evenly distributed)")

    # Show distributions
    if "analysis" in response and "distributions" in response["analysis"]["quantitative"]:
        dists = response["analysis"]["quantitative"]["distributions"]

        for db, dist in dists.items():
            if "locations" in dist:
                print(f"\n📍 Location Distribution:")
                for loc in dist["locations"]["top_10"][:10]:
                    pct = (loc['count'] / dist["locations"]["total_items"]) * 100
                    print(f"   {loc['value']}: {loc['count']} ({pct:.1f}%)")


if __name__ == "__main__":
    import sys

    if "--trend" in sys.argv:
        asyncio.run(test_trend_detection())
    else:
        asyncio.run(test_research_assistant())
