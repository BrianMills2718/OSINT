#!/usr/bin/env python3
"""
Test: Verify diverse sampling fix works correctly.

Demonstrates that LLM now sees results from ALL sources, not just the first source.

Background:
- Old behavior: LLM only saw first 10 results (often all from same source)
- New behavior: LLM sees 3 results from each source (diverse sampling)

Expected outcome:
- Sample should include results from multiple sources
- DHS Secretary tweet should be in sample (Twitter results now included)
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from research.deep_research import SimpleDeepResearch


def test_diverse_sampling():
    """Test that _sample_diverse_results provides diversity across sources."""

    # Create engine
    engine = SimpleDeepResearch()

    # Simulate 42 results from mixed sources (like Task 1 had)
    all_results = []

    # 10 DVIDS results (conferences, exercises - off-topic)
    for i in range(10):
        all_results.append({
            'source': 'DVIDS',
            'title': f'Military IT conference {i}',
            'snippet': 'Defense Health Agency IT teams...'
        })

    # 10 Twitter results (including DHS Secretary speech - RELEVANT!)
    for i in range(10):
        if i == 2:
            # This is the DHS Secretary speech that was missed
            all_results.append({
                'source': 'Twitter',
                'title': 'DHS Secretary Kristi Noem spoke about federal cybersecurity careers',
                'snippet': 'careers in federal service, whether in defense, cybersecurity, disaster response'
            })
        else:
            all_results.append({
                'source': 'Twitter',
                'title': f'Tweet {i}',
                'snippet': 'Some tweet content...'
            })

    # 2 Discord results
    for i in range(2):
        all_results.append({
            'source': 'Discord',
            'title': f'Discord post {i}',
            'snippet': 'OSINT discussion...'
        })

    # 10 USAJobs results
    for i in range(10):
        all_results.append({
            'source': 'USAJobs',
            'title': f'Cybersecurity Specialist {i}',
            'snippet': 'Federal job posting...'
        })

    # 10 ClearanceJobs results
    for i in range(10):
        all_results.append({
            'source': 'ClearanceJobs',
            'title': f'Security Engineer {i}',
            'snippet': 'Contractor job posting...'
        })

    print(f"Total results: {len(all_results)}")
    print(f"Sources: DVIDS (10), Twitter (10), Discord (2), USAJobs (10), ClearanceJobs (10)")

    # OLD BEHAVIOR: First 10 results
    old_sample = all_results[:10]
    old_sources = {}
    for r in old_sample:
        source = r['source']
        old_sources[source] = old_sources.get(source, 0) + 1

    print(f"\n❌ OLD BEHAVIOR (first 10 results):")
    print(f"   Sample sources: {dict(old_sources)}")
    print(f"   DHS Secretary tweet included? {'Yes' if any('DHS Secretary' in r['title'] for r in old_sample) else 'No'}")

    # NEW BEHAVIOR: Diverse sampling
    new_sample = engine._sample_diverse_results(all_results, max_per_source=3, max_total=20)
    new_sources = {}
    for r in new_sample:
        source = r['source']
        new_sources[source] = new_sources.get(source, 0) + 1

    print(f"\n✅ NEW BEHAVIOR (diverse sampling):")
    print(f"   Sample size: {len(new_sample)}")
    print(f"   Sample sources: {dict(new_sources)}")
    print(f"   DHS Secretary tweet included? {'Yes' if any('DHS Secretary' in r['title'] for r in new_sample) else 'No'}")

    # Verify diversity
    assert len(new_sources) >= 4, f"Expected at least 4 sources in sample, got {len(new_sources)}"
    assert 'DVIDS' in new_sources, "DVIDS should be in sample"
    assert 'Twitter' in new_sources, "Twitter should be in sample"
    assert 'USAJobs' in new_sources or 'ClearanceJobs' in new_sources, "At least one job source should be in sample"

    # Verify DHS Secretary tweet is now included
    dhs_tweet_in_sample = any('DHS Secretary' in r['title'] for r in new_sample)
    assert dhs_tweet_in_sample, "DHS Secretary tweet should be in diverse sample"

    print(f"\n✅ All assertions passed! Diverse sampling is working correctly.")
    print(f"\nConclusion:")
    print(f"  - Old behavior: Only saw {len(old_sources)} source(s) ({list(old_sources.keys())})")
    print(f"  - New behavior: Sees {len(new_sources)} sources ({list(new_sources.keys())})")
    print(f"  - DHS Secretary tweet: Was missed → Now included ✓")


if __name__ == "__main__":
    test_diverse_sampling()
