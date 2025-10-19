# API Rate Limit Tracking

## Overview

We've implemented automatic request tracking to help understand API rate limits, especially for SAM.gov which doesn't document their limits explicitly.

## How It Works

Every API call to ClearanceJobs, DVIDS, and SAM.gov is automatically logged to `api_requests.jsonl` with:
- Timestamp
- API name
- Endpoint
- HTTP status code (200, 429, etc.)
- Response time in milliseconds
- Error messages (if any)
- Request parameters (with API keys sanitized)

## Viewing Statistics

Run the tracker script to see statistics:

```bash
python3 api_request_tracker.py
```

This shows:
- **Total requests** to each API
- **Rate limit hits** (HTTP 429 errors)
- **Success rates**
- **Time between requests**
- **When rate limits occurred**

### For SAM.gov specifically, it analyzes:
- How many requests were made in the 1 minute before hitting rate limit
- How many requests were made in the 5 minutes before hitting rate limit
- How many requests were made in the 1 hour before hitting rate limit
- How many requests were made in the 24 hours before hitting rate limit

## Example Output

```
API REQUEST STATISTICS (Last 24 Hours)
================================================================================

Total Requests: 15
Rate Limit Hits: 2
Overall Success Rate: 86.7%

SAM.gov:
  Total Requests: 10
  Rate Limits Hit: 2
  Success Rate: 80.0%
  Avg Time Between Requests: 45.2s
  Min Time Between Requests: 2.1s
  Rate Limit Times:
    - 2025-10-18T13:45:22
    - 2025-10-18T14:02:15

RATE LIMIT ANALYSIS
================================================================================

SAM.gov Rate Limit Pattern:
  Hit rate limit 2 time(s)

  At 2025-10-18T13:45:22:
    Requests in last 1min: 0
    Requests in last 5min: 3
    Requests in last 1hour: 8
    Requests in last 24hrs: 10
    Error: 429 Client Error: Too Many Requests
```

## Understanding SAM.gov Rate Limits

Based on the error message you received:
```
Message throttled out. You have exceeded your quota.
You can access API after 2025-Oct-19 00:00:00+0000 UTC
```

This suggests SAM.gov has a **daily quota** that resets at midnight UTC.

The tracker will help us determine:
1. **How many requests per day** are allowed
2. **If there are additional per-minute or per-hour limits**
3. **When exactly the quota resets**

## Log File

All requests are logged to: **`api_requests.jsonl`**

This is a JSON Lines format (one JSON object per line), making it easy to:
- Parse with scripts
- Import into databases
- Analyze with tools like `jq`

Example log entry:
```json
{
  "timestamp": "2025-10-18T13:45:22.123456",
  "api": "SAM.gov",
  "endpoint": "https://api.sam.gov/opportunities/v2/search",
  "status_code": 429,
  "response_time_ms": 523.4,
  "error": "429 Client Error: Too Many Requests",
  "params": {
    "api_key": "SAM-db0e***2112",
    "keywords": "counterterrorism",
    "postedFrom": "08/19/2025",
    "postedTo": "10/18/2025"
  }
}
```

## Querying the Log Manually

You can analyze the log file using command-line tools:

### Count requests per API:
```bash
jq -r '.api' api_requests.jsonl | sort | uniq -c
```

### Find all 429 errors:
```bash
jq 'select(.status_code == 429)' api_requests.jsonl
```

### Count SAM.gov requests today:
```bash
jq 'select(.api == "SAM.gov" and (.timestamp | startswith("2025-10-18")))' api_requests.jsonl | wc -l
```

### Average response time per API:
```bash
jq -r 'select(.api == "SAM.gov") | .response_time_ms' api_requests.jsonl | awk '{sum+=$1; n++} END {print sum/n " ms"}'
```

## Next Steps for Determining Rate Limits

1. **Let the tracker run** as you use the application
2. **After hitting a 429**, run: `python3 api_request_tracker.py`
3. **Look at the analysis** to see how many requests preceded the rate limit
4. **Wait for reset** (midnight UTC for SAM.gov)
5. **Test again** to confirm the pattern

## Current Known Information

### SAM.gov
- ❓ Unknown requests per day limit (we need to track this!)
- ✅ Known reset time: Midnight UTC (00:00:00+0000)
- ⚠️ Already hit rate limit with your key today (resets Oct 19)

### DVIDS
- ✅ No rate limits encountered yet
- ℹ️ Public API, likely generous limits

### ClearanceJobs
- ✅ No rate limits encountered yet
- ℹ️ No authentication required

## Recommendations

1. **Continue using the app normally** - all requests are being tracked
2. **Check the tracker daily** to see patterns: `python3 api_request_tracker.py`
3. **After a few days**, we'll have enough data to determine SAM.gov's exact limits
4. **Consider caching** SAM.gov results if we hit limits frequently

## Preventing Rate Limit Issues

Once we understand the limits, we can implement:
- **Request caching** (don't re-query the same thing)
- **Request queuing** (space out requests if needed)
- **Smart scheduling** (spread queries across the day)
- **User warnings** when approaching limits
