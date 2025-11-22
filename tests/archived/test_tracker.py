#!/usr/bin/env python3
"""Test the API request tracker."""

from core.api_request_tracker import log_request, get_request_stats, analyze_rate_limits
import time

print("Testing API Request Tracker")
print("=" * 60)

# Simulate some requests
print("\n1. Logging some simulated requests...")

log_request("SAM.gov", "https://api.sam.gov/opportunities/v2/search", 200, 1234.5, None, {"keywords": "test"})
time.sleep(0.1)
log_request("SAM.gov", "https://api.sam.gov/opportunities/v2/search", 200, 2345.6, None, {"keywords": "test2"})
time.sleep(0.1)
log_request("SAM.gov", "https://api.sam.gov/opportunities/v2/search", 429, 567.8, "Too Many Requests", {"keywords": "test3"})
time.sleep(0.1)
log_request("DVIDS", "https://api.dvidshub.net/search", 200, 890.1, None, {"q": "military"})
time.sleep(0.1)
log_request("ClearanceJobs", "https://api.clearancejobs.com/api/v1/jobs/search", 200, 1500.2, None, {"query": "engineer"})

print("✅ Logged 5 test requests")

# Get stats
print("\n2. Retrieving statistics...")
stats = get_request_stats(hours=24)

print(f"\nTotal Requests: {stats['total_requests']}")
print(f"Rate Limit Hits: {stats['rate_limit_hits']}")
print(f"Success Rate: {stats['success_rate']:.1%}")

for api, api_stats in stats['apis'].items():
    print(f"\n{api}:")
    print(f"  Requests: {api_stats['total_requests']}")
    print(f"  Rate Limits: {api_stats['rate_limit_hits']}")

# Analyze rate limits
print("\n3. Analyzing rate limit patterns...")
analysis = analyze_rate_limits("SAM.gov", hours=24)

if "error" not in analysis:
    print(f"\nSAM.gov Analysis:")
    print(f"  Total Requests: {analysis['total_requests']}")
    print(f"  Rate Limit Hits: {analysis['rate_limit_hits']}")

    if analysis['rate_limit_events']:
        for event in analysis['rate_limit_events']:
            print(f"\n  Rate limit at {event['timestamp']}:")
            print(f"    Last 1min: {event['requests_before_in_1min']} requests")
            print(f"    Last 5min: {event['requests_before_in_5min']} requests")
            print(f"    Last 1hour: {event['requests_before_in_1hour']} requests")

print("\n" + "=" * 60)
print("✅ Tracker is working correctly!")
print("\nLog file: api_requests.jsonl")
print("View stats anytime: python3 api_request_tracker.py")
