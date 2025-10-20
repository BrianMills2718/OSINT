#!/usr/bin/env python3
"""API Request Tracker - Track API calls and rate limit hits to understand limits."""

import json
import os
from datetime import datetime
from pathlib import Path

# Log file location
LOG_FILE = Path(__file__).parent / "api_requests.jsonl"


def log_request(api_name, endpoint, status_code, response_time_ms=None, error_message=None,
                request_params=None, cost_usd=None, result_count=None, session_id=None):
    """
    Log an API request with timestamp and details.

    Args:
        api_name: Name of the API (e.g., "SAM.gov", "DVIDS", "ClearanceJobs")
        endpoint: The endpoint URL
        status_code: HTTP status code (200, 429, etc.)
        response_time_ms: Response time in milliseconds
        error_message: Error message if request failed
        request_params: Dict of request parameters (will be sanitized to remove API keys)
        cost_usd: Estimated cost in USD (for LLM calls)
        result_count: Number of results returned
        session_id: Session ID for grouping related requests
    """
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "api": api_name,
        "endpoint": endpoint,
        "status_code": status_code,
        "response_time_ms": response_time_ms,
        "error": error_message,
        "params": sanitize_params(request_params) if request_params else None,
        "cost_usd": cost_usd,
        "result_count": result_count,
        "session_id": session_id
    }

    # Append to JSONL file (one JSON object per line)
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(log_entry) + "\n")


def sanitize_params(params):
    """Remove sensitive data like API keys from parameters before logging."""
    if not params:
        return None

    sanitized = params.copy()

    # Remove or mask API keys
    if "api_key" in sanitized:
        # Keep first 8 chars for identification, mask the rest
        key = sanitized["api_key"]
        if len(key) > 12:
            sanitized["api_key"] = key[:8] + "***" + key[-4:]
        else:
            sanitized["api_key"] = "***"

    return sanitized


def get_request_stats(api_name=None, hours=24):
    """
    Get statistics about API requests.

    Args:
        api_name: Filter by specific API, or None for all APIs
        hours: Look back this many hours

    Returns:
        Dict with statistics
    """
    if not LOG_FILE.exists():
        return {"error": "No request log file found"}

    from datetime import timedelta

    cutoff_time = datetime.now() - timedelta(hours=hours)

    requests = []
    rate_limit_hits = []

    with open(LOG_FILE, "r") as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                entry_time = datetime.fromisoformat(entry["timestamp"])

                # Filter by time window
                if entry_time < cutoff_time:
                    continue

                # Filter by API name if specified
                if api_name and entry["api"] != api_name:
                    continue

                requests.append(entry)

                # Track rate limit hits (429) and failed requests (status 0 or 5xx)
                if entry["status_code"] == 429:
                    rate_limit_hits.append(entry)

            except (json.JSONDecodeError, KeyError):
                continue

    # Calculate statistics
    failed_requests = [r for r in requests if r["status_code"] in [0, 429] or r["status_code"] >= 500]
    successful_requests = [r for r in requests if r["status_code"] in [200, 201]]

    stats = {
        "total_requests": len(requests),
        "rate_limit_hits": len(rate_limit_hits),
        "failed_requests": len(failed_requests),
        "successful_requests": len(successful_requests),
        "success_rate": len(successful_requests) / len(requests) if requests else 0,
        "apis": {}
    }

    # Group by API
    api_groups = {}
    for req in requests:
        api = req["api"]
        if api not in api_groups:
            api_groups[api] = []
        api_groups[api].append(req)

    # Calculate per-API stats
    for api, api_reqs in api_groups.items():
        api_429s = [r for r in api_reqs if r["status_code"] == 429]
        api_failed = [r for r in api_reqs if r["status_code"] in [0, 429] or r["status_code"] >= 500]
        api_status_0 = [r for r in api_reqs if r["status_code"] == 0]
        api_successful = [r for r in api_reqs if r["status_code"] in [200, 201]]

        # Calculate time between requests
        api_reqs_sorted = sorted(api_reqs, key=lambda x: x["timestamp"])
        time_gaps = []
        for i in range(1, len(api_reqs_sorted)):
            t1 = datetime.fromisoformat(api_reqs_sorted[i-1]["timestamp"])
            t2 = datetime.fromisoformat(api_reqs_sorted[i]["timestamp"])
            gap_seconds = (t2 - t1).total_seconds()
            time_gaps.append(gap_seconds)

        stats["apis"][api] = {
            "total_requests": len(api_reqs),
            "successful_requests": len(api_successful),
            "failed_requests": len(api_failed),
            "rate_limit_hits": len(api_429s),
            "status_0_errors": len(api_status_0),
            "success_rate": len(api_successful) / len(api_reqs) if api_reqs else 0,
            "avg_time_between_requests_sec": sum(time_gaps) / len(time_gaps) if time_gaps else 0,
            "min_time_between_requests_sec": min(time_gaps) if time_gaps else 0,
            "rate_limit_timestamps": [r["timestamp"] for r in api_429s],
            "status_0_timestamps": [r["timestamp"] for r in api_status_0]
        }

    return stats


def analyze_rate_limits(api_name, hours=24):
    """
    Analyze rate limit patterns for a specific API.

    Args:
        api_name: Name of the API to analyze
        hours: Look back this many hours

    Returns:
        Dict with rate limit analysis
    """
    if not LOG_FILE.exists():
        return {"error": "No request log file found"}

    from datetime import timedelta

    cutoff_time = datetime.now() - timedelta(hours=hours)

    requests = []

    with open(LOG_FILE, "r") as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                entry_time = datetime.fromisoformat(entry["timestamp"])

                if entry_time < cutoff_time:
                    continue

                if entry["api"] != api_name:
                    continue

                requests.append(entry)

            except (json.JSONDecodeError, KeyError):
                continue

    if not requests:
        return {"error": f"No requests found for {api_name} in last {hours} hours"}

    # Sort by timestamp
    requests.sort(key=lambda x: x["timestamp"])

    # Find patterns before 429s
    rate_limit_analysis = []

    for i, req in enumerate(requests):
        if req["status_code"] == 429:
            # Look at the requests before this 429
            lookback = min(i, 20)  # Look at last 20 requests
            preceding_requests = requests[i-lookback:i]

            # Count requests in various time windows before the 429
            req_time = datetime.fromisoformat(req["timestamp"])

            counts = {
                "1min": 0,
                "5min": 0,
                "1hour": 0,
                "24hours": 0
            }

            for prev_req in preceding_requests:
                prev_time = datetime.fromisoformat(prev_req["timestamp"])
                gap = (req_time - prev_time).total_seconds()

                if gap <= 60:
                    counts["1min"] += 1
                if gap <= 300:
                    counts["5min"] += 1
                if gap <= 3600:
                    counts["1hour"] += 1
                if gap <= 86400:
                    counts["24hours"] += 1

            rate_limit_analysis.append({
                "timestamp": req["timestamp"],
                "error_message": req.get("error", ""),
                "requests_before_in_1min": counts["1min"],
                "requests_before_in_5min": counts["5min"],
                "requests_before_in_1hour": counts["1hour"],
                "requests_before_in_24hours": counts["24hours"]
            })

    return {
        "api": api_name,
        "analysis_period_hours": hours,
        "total_requests": len(requests),
        "rate_limit_hits": len(rate_limit_analysis),
        "rate_limit_events": rate_limit_analysis
    }


if __name__ == "__main__":
    # Display recent stats
    print("=" * 80)
    print("API REQUEST STATISTICS (Last 24 Hours)")
    print("=" * 80)
    print()

    stats = get_request_stats(hours=24)

    if "error" in stats:
        print(f"Error: {stats['error']}")
    else:
        print(f"Total Requests: {stats['total_requests']}")
        print(f"Rate Limit Hits: {stats['rate_limit_hits']}")
        print(f"Overall Success Rate: {stats['success_rate']:.1%}")
        print()

        for api, api_stats in stats["apis"].items():
            print(f"\n{api}:")
            print(f"  Total Requests: {api_stats['total_requests']}")
            print(f"  Rate Limits Hit: {api_stats['rate_limit_hits']}")
            print(f"  Success Rate: {api_stats['success_rate']:.1%}")
            if api_stats["avg_time_between_requests_sec"] > 0:
                print(f"  Avg Time Between Requests: {api_stats['avg_time_between_requests_sec']:.1f}s")
                print(f"  Min Time Between Requests: {api_stats['min_time_between_requests_sec']:.1f}s")

            if api_stats["rate_limit_timestamps"]:
                print(f"  Rate Limit Times:")
                for ts in api_stats["rate_limit_timestamps"]:
                    print(f"    - {ts}")

    print("\n" + "=" * 80)
    print("RATE LIMIT ANALYSIS")
    print("=" * 80)

    for api_name in ["SAM.gov", "DVIDS", "ClearanceJobs"]:
        analysis = analyze_rate_limits(api_name, hours=24)

        if "error" in analysis:
            continue

        if analysis["rate_limit_hits"] > 0:
            print(f"\n{api_name} Rate Limit Pattern:")
            print(f"  Hit rate limit {analysis['rate_limit_hits']} time(s)")

            for event in analysis["rate_limit_events"]:
                print(f"\n  At {event['timestamp']}:")
                print(f"    Requests in last 1min: {event['requests_before_in_1min']}")
                print(f"    Requests in last 5min: {event['requests_before_in_5min']}")
                print(f"    Requests in last 1hour: {event['requests_before_in_1hour']}")
                print(f"    Requests in last 24hrs: {event['requests_before_in_24hours']}")
                if event["error_message"]:
                    print(f"    Error: {event['error_message']}")


def get_cost_summary(hours=24):
    """
    Get cost summary for API and LLM usage.

    Args:
        hours: Look back this many hours

    Returns:
        Dict with cost breakdown
    """
    if not LOG_FILE.exists():
        return {"error": "No request log file found"}

    from datetime import timedelta

    cutoff_time = datetime.now() - timedelta(hours=hours)

    total_cost = 0
    cost_by_api = {}
    llm_calls = 0
    api_calls = 0

    with open(LOG_FILE, "r") as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                entry_time = datetime.fromisoformat(entry["timestamp"])

                if entry_time < cutoff_time:
                    continue

                cost = entry.get("cost_usd", 0) or 0
                total_cost += cost

                api = entry["api"]
                if api not in cost_by_api:
                    cost_by_api[api] = {"cost": 0, "calls": 0}

                cost_by_api[api]["cost"] += cost
                cost_by_api[api]["calls"] += 1

                if entry["endpoint"] == "LLM":
                    llm_calls += 1
                else:
                    api_calls += 1

            except (json.JSONDecodeError, KeyError):
                continue

    return {
        "period_hours": hours,
        "total_cost_usd": total_cost,
        "llm_calls": llm_calls,
        "api_calls": api_calls,
        "cost_per_call": total_cost / (llm_calls + api_calls) if (llm_calls + api_calls) > 0 else 0,
        "by_api": cost_by_api,
        "projected_monthly_cost": (total_cost / hours) * 24 * 30 if hours > 0 else 0
    }


def get_performance_summary(hours=24):
    """
    Get performance summary for all APIs.

    Args:
        hours: Look back this many hours

    Returns:
        Dict with performance metrics
    """
    if not LOG_FILE.exists():
        return {"error": "No request log file found"}

    from datetime import timedelta

    cutoff_time = datetime.now() - timedelta(hours=hours)

    perf_by_api = {}

    with open(LOG_FILE, "r") as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                entry_time = datetime.fromisoformat(entry["timestamp"])

                if entry_time < cutoff_time:
                    continue

                api = entry["api"]
                if api not in perf_by_api:
                    perf_by_api[api] = {
                        "response_times": [],
                        "successes": 0,
                        "failures": 0,
                        "results": []
                    }

                rt = entry.get("response_time_ms")
                if rt:
                    perf_by_api[api]["response_times"].append(rt)

                if entry["status_code"] in [200, 201]:
                    perf_by_api[api]["successes"] += 1
                else:
                    perf_by_api[api]["failures"] += 1

                result_count = entry.get("result_count", 0) or 0
                if result_count > 0:
                    perf_by_api[api]["results"].append(result_count)

            except (json.JSONDecodeError, KeyError):
                continue

    # Calculate statistics
    summary = {}
    for api, data in perf_by_api.items():
        rts = data["response_times"]
        results = data["results"]

        summary[api] = {
            "total_calls": data["successes"] + data["failures"],
            "success_rate": data["successes"] / (data["successes"] + data["failures"])
                if (data["successes"] + data["failures"]) > 0 else 0,
            "avg_response_time_ms": sum(rts) / len(rts) if rts else 0,
            "p50_response_time_ms": sorted(rts)[len(rts) // 2] if rts else 0,
            "p95_response_time_ms": sorted(rts)[int(len(rts) * 0.95)] if rts else 0,
            "avg_results": sum(results) / len(results) if results else 0,
            "total_results": sum(results)
        }

    return summary
