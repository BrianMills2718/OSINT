#!/usr/bin/env python3
"""Quick test to verify saturation configuration is working."""

from research.deep_research import SimpleDeepResearch

def test_config():
    engine = SimpleDeepResearch()
    print(f"Query saturation enabled: {engine.query_saturation_enabled}")
    print(f"Max queries for SAM.gov: {engine.max_queries_per_source.get('SAM.gov')}")
    print(f"Max time per source: {engine.max_time_per_source_seconds}s")

if __name__ == "__main__":
    test_config()
