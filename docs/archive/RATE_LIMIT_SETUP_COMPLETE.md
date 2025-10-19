# ✅ Rate Limit Tracking System - Setup Complete

## What Was Added

### 1. **Automatic Request Logging** (`api_request_tracker.py`)
Every API call to ClearanceJobs, DVIDS, and SAM.gov is now automatically logged with:
- Timestamp
- API name and endpoint
- HTTP status code (especially 429 rate limit errors)
- Response time
- Error messages
- Request parameters (API keys are sanitized)

### 2. **Integration with AI Research** (`ai_research.py`)
All three search functions now log every request:
- `execute_clearancejobs_search()` - logs to tracker
- `execute_dvids_search()` - logs to tracker
- `execute_sam_search()` - logs to tracker (MOST IMPORTANT for rate limits)

### 3. **Statistics Viewer** (`api_request_tracker.py`)
Run anytime to see:
```bash
python3 api_request_tracker.py
```

Shows:
- Total requests per API
- How many rate limit hits (429 errors)
- Success rates
- Time between requests
- **Pattern analysis**: Shows how many requests were made before hitting rate limit

### 4. **Streamlit UI Integration** (`unified_search_app.py`)
Added "📈 API Usage Stats" in the sidebar showing:
- Total requests (last 24 hours)
- Rate limit hits
- Per-API breakdown with success rates
- Timestamps of when rate limits occurred

## How to Use

### During Normal Use
1. **Just use the app normally** - tracking happens automatically
2. **Check sidebar** for quick stats view
3. **Run `python3 api_request_tracker.py`** for detailed analysis

### When You Hit a Rate Limit
The tracker will capture:
- Exactly when it happened
- How many requests were made in the last 1 min / 5 min / 1 hour / 24 hours
- The error message from the API

### Example: Your SAM.gov 429 Error
Your error said:
```
You have exceeded your quota.
You can access API after 2025-Oct-19 00:00:00+0000 UTC
```

This tells us:
- ✅ SAM.gov has a **daily quota** (not per-minute or per-hour)
- ✅ Resets at **midnight UTC**
- ❓ **Unknown**: How many requests per day are allowed?

### Finding the SAM.gov Daily Limit

After midnight UTC tonight (Oct 19 00:00), the tracker will help determine the limit:

1. **Use the app normally** starting after midnight UTC
2. **Count how many SAM.gov requests** before hitting 429 again
3. **Run the tracker** to see the exact count:
   ```bash
   python3 api_request_tracker.py
   ```

The "Rate Limit Analysis" section will show:
```
SAM.gov Rate Limit Pattern:
  At 2025-10-19T15:30:00:
    Requests in last 24hrs: X  <-- This is your daily limit!
```

## Log File Location

**`api_requests.jsonl`** - JSON Lines format (one JSON object per line)

Example entry:
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

## Quick Commands

### View all stats:
```bash
python3 api_request_tracker.py
```

### Count SAM.gov requests today:
```bash
jq 'select(.api == "SAM.gov" and (.timestamp | startswith("2025-10-18")))' api_requests.jsonl | wc -l
```

### Find all rate limit errors:
```bash
jq 'select(.status_code == 429)' api_requests.jsonl
```

### View rate limit pattern for SAM.gov:
```bash
python3 api_request_tracker.py | grep -A 20 "SAM.gov Rate Limit Pattern"
```

## What We'll Learn

After a few days of tracking, we'll know:

1. **SAM.gov daily quota** (how many requests before 429)
2. **DVIDS limits** (if any)
3. **ClearanceJobs limits** (if any)
4. **Typical response times** for each API
5. **Best times to query** (if some times are faster)

## Next Steps

1. ✅ **Tracking is active** - just use the app
2. ⏳ **Wait for midnight UTC** (Oct 19 00:00) for SAM.gov reset
3. 📊 **Check stats regularly** via sidebar or command line
4. 📝 **Document the limits** once we determine them

## Files Added/Modified

### New Files:
- `api_request_tracker.py` - Logging and analysis system
- `test_tracker.py` - Test script
- `API_RATE_LIMIT_TRACKING.md` - Full documentation
- `RATE_LIMIT_SETUP_COMPLETE.md` - This file

### Modified Files:
- `ai_research.py` - Added tracking to all 3 search functions
- `unified_search_app.py` - Added stats viewer in sidebar

---

**Bottom Line:** All API requests are now being tracked. After using the app for a day or two, you'll have concrete data about SAM.gov's rate limits and can make informed decisions about caching, request spacing, etc.
