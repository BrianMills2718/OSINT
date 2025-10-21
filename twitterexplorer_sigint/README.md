# Twitter API Integration Documentation

**Purpose**: Extracted components from broken twitterexplorer system for SIGINT platform integration.

**Extraction Date**: 2025-10-20
**Source**: `/home/brian/sam_gov/twitterexplorer` (autonomous investigation system - fundamentally broken)
**Status**: ✅ SALVAGED - API client and endpoint docs only, investigation engine abandoned

---

## Contents

This directory contains ONLY the useful Twitter API components, extracted from the complex (but broken) investigation system:

1. **`api_client.py`** - RapidAPI Twitter client with pagination, retries, rate limiting
2. **`twitter_config.py`** - API configuration constants
3. **`merged_endpoints.json`** - Complete documentation of 20+ Twitter API endpoints
4. **`README.md`** - This file

**What was NOT extracted** (too complex, not needed for simple integration):
- Investigation engine (`investigation_engine.py`)
- Graph visualization system (`graph_visualizer.py`)
- 6-node ontology (`investigation_graph.py`)
- LLM coordination system (`graph_aware_llm_coordinator.py`)

---

## Twitter API Details

**Provider**: RapidAPI (twitter-api45)
**Host**: `twitter-api45.p.rapidapi.com`
**Base URL**: `https://twitter-api45.p.rapidapi.com`
**Authentication**: Requires `RAPIDAPI_KEY` environment variable
**Rate Limits**: Handled automatically with exponential backoff
**Pagination**: Cursor-based using `next_cursor` field

---

## Available Endpoints (20+)

### Core Search & Content Endpoints (PRIORITY FOR SIGINT)

#### 1. **search.php** - General Tweet Search
**Most important for SIGINT platform**

**Required**: `query` (search keywords)
**Optional**:
- `cursor` - For pagination
- `search_type` - Enum: `Top`, `Latest`, `Media`, `People`, `Lists`

**Returns**:
```json
{
  "status": "ok",
  "timeline": [
    {
      "tweet_id": "123...",
      "text": "tweet content",
      "created_at": "2025-10-20T12:00:00Z",
      "user_info": {
        "screen_name": "username",
        "name": "Display Name",
        "verified": true,
        "followers_count": 1000
      },
      "favorites": 10,
      "retweets": 5,
      "replies": 3,
      "views": "1500"
    }
  ],
  "next_cursor": "..."
}
```

**SIGINT Use Cases**:
- Search for JTTF mentions
- Track counterterrorism discussions
- Monitor specific keywords across Twitter
- Filter by recency (use `search_type: "Latest"`)

---

#### 2. **timeline.php** - User Timeline
**Required**: `screenname` (Twitter handle)
**Optional**: `cursor`, `rest_id`

**Returns**: User's tweets, replies, retweets, and quoted tweets
**Includes**: Nested `retweeted_tweet` and `quoted` objects

**SIGINT Use Cases**:
- Monitor specific individuals' activity
- Track organization accounts
- Get historical timeline for user

---

#### 3. **tweet.php** - Individual Tweet Details
**Required**: `id` (tweet ID)
**Returns**: Full tweet details including media, entities, conversation metadata

**SIGINT Use Cases**:
- Get full context for specific tweets
- Extract media URLs
- Analyze conversation threads

---

#### 4. **latest_replies.php** - Conversation Threads
**Required**: `id` (tweet ID)
**Optional**: `cursor`

**Returns**: List of replies TO a specific tweet

**SIGINT Use Cases**:
- Track discussion threads
- Analyze community responses
- Monitor conversation evolution

---

### Social Graph Endpoints

#### 5. **screenname.php** - User Profile Info
**Required**: `screenname`
**Returns**: Profile details, follower/following counts, bio, location

#### 6. **followers.php** - User's Followers
**Required**: `screenname`
**Returns**: List of follower accounts with metadata

#### 7. **following.php** - Accounts User Follows
**Required**: `screenname`
**Returns**: List of accounts user follows

**SIGINT Use Cases**:
- Network mapping of targets
- Identify affiliations
- Track organizational connections

---

### Other Endpoints (Available but Lower Priority)

- **trends.php** - Trending topics by country
- **retweets.php** - Users who retweeted a tweet
- **usermedia.php** - User's media timeline (photos/videos)
- **tweet_thread.php** - Thread continuation
- **checkretweet.php** - Check if user retweeted
- **checkfollow.php** - Check if user follows another
- **listtimeline.php** - Timeline for Twitter lists
- **list_followers.php** - Followers of a list
- **list_members.php** - Members of a list
- **community_timeline.php** - Community posts
- **spaces.php** - Twitter Spaces metadata
- **affilates.php** - User affiliations
- **screennames.php** - Batch user lookups by rest_id

---

## API Client Features (api_client.py)

### Core Capabilities

1. **Pagination Handling**
   - Automatic cursor-based pagination
   - Configurable `max_pages` per request
   - Combines results across pages

2. **Rate Limiting & Retries**
   - Exponential backoff for 429 (rate limit) errors
   - Retry logic for 5xx server errors
   - Network timeout handling (30s default)

3. **Data Extraction**
   - Generic extraction from various response structures
   - Tries common keys: `timeline`, `followers`, `users`, `results`, `data`
   - Handles list responses and single-item dictionaries

4. **Parameter Resolution**
   - Supports dependencies between API steps (`$step1.field`)
   - Dictionary-based list dependencies with field extraction
   - Nested value access using dot notation

5. **Error Handling**
   - HTTP error codes with full context
   - JSON decode errors with response preview
   - Connection timeouts with retry

### Key Functions

**`get_nested_value(data, path_string)`**
- Safely access nested dict/list using dot notation
- Example: `get_nested_value(response, "timeline.0.user_info.screen_name")`

**`execute_api_step(step_plan, previous_results, rapidapi_key)`**
- Execute single API call with pagination
- Handles parameter dependencies
- Returns standardized response with `data`, `endpoint`, `executed_params`

### Usage Example

```python
import requests
from api_client import execute_api_step

step_plan = {
    "endpoint": "search.php",
    "params": {
        "query": "JTTF counterterrorism",
        "search_type": "Latest"
    },
    "max_pages": 3,
    "reason": "Search for JTTF mentions"
}

result = execute_api_step(step_plan, [], rapidapi_key="your-key-here")

if "error" not in result:
    tweets = result["data"].get("timeline", [])
    for tweet in tweets:
        print(f"{tweet['user_info']['screen_name']}: {tweet['text']}")
```

---

## Configuration (twitter_config.py)

```python
RAPIDAPI_TWITTER_HOST = "twitter-api45.p.rapidapi.com"
RAPIDAPI_BASE_URL = f"https://{RAPIDAPI_TWITTER_HOST}"
API_TIMEOUT_SECONDS = 30  # Requests take 10-13s regularly
DEFAULT_MAX_PAGES_FALLBACK = 3
```

---

## Integration with SIGINT Platform

### Recommended Approach

Create `integrations/social/twitter_integration.py` extending `DatabaseIntegration`:

```python
from core.database_integration_base import DatabaseIntegration, QueryResult
from twitterexplorer_sigint.api_client import execute_api_step

class TwitterIntegration(DatabaseIntegration):
    @property
    def metadata(self):
        return DatabaseMetadata(
            name="Twitter",
            id="twitter",
            category=DatabaseCategory.SOCIAL_MEDIA,
            requires_api_key=True,
            cost_per_query_estimate=0.01,
            typical_response_time=3.0,
            description="Twitter search for tweets, users, and trending topics"
        )

    async def generate_query(self, research_question: str) -> Optional[Dict]:
        # Use LLM to generate Twitter-specific query
        # Return: {"query": "keywords", "search_type": "Latest", "max_pages": 3}
        pass

    async def execute_search(self, query_params, api_key, limit) -> QueryResult:
        # Use api_client.execute_api_step() to call search.php
        # Extract timeline results
        # Return standardized QueryResult
        pass
```

### Field Mapping for Generic Display

Map Twitter API fields to SIGINT platform's common field names:

| SIGINT Field | Twitter API Field |
|-------------|-------------------|
| `title` | `timeline[].text[:100]` (truncated tweet text) |
| `url` | `https://twitter.com/{screen_name}/status/{tweet_id}` |
| `date` | `timeline[].created_at` |
| `description` | `timeline[].text` (full tweet text) |
| `author` | `timeline[].user_info.screen_name` |
| `metadata` | `{favorites, retweets, replies, views, verified}` |

---

## Known Limitations

### API Client Limitations
1. **No Authentication for Protected Tweets**: Cannot access private accounts
2. **Pagination Speed**: Cursor-based pagination requires sequential requests (not parallel)
3. **No Built-in Deduplication**: Same tweet may appear across pages if actively being retweeted

### RapidAPI Twitter-API45 Limitations
1. **Not Official Twitter API**: Third-party service, may have coverage gaps
2. **Rate Limits**: Unknown exact limits, handled via exponential backoff
3. **Cost**: Paid service (requires RapidAPI subscription)
4. **Search Limitations**: May not return all historical results (Twitter API restriction)

### Parameter Support
- **search.php**: Full Boolean operators NOT documented (test empirically)
- **Date Filtering**: No explicit date range parameters (use `search_type: "Latest"` for recency)
- **Location Filtering**: Not explicitly supported (check `user_info.location` post-fetch)

---

## Testing Checklist

Before integrating into SIGINT platform:

- [ ] Test `search.php` with simple keyword
- [ ] Test `search.php` with `search_type: "Latest"`
- [ ] Test pagination (request 3 pages, verify `next_cursor` handling)
- [ ] Test rate limit handling (make rapid requests, verify exponential backoff)
- [ ] Test error handling (invalid query, network timeout)
- [ ] Test `timeline.php` for user activity tracking
- [ ] Test `tweet.php` for individual tweet details
- [ ] Verify field mapping to SIGINT common fields

---

## Environment Setup

**Required**:
```bash
# .env file
RAPIDAPI_KEY=your-rapidapi-key-here
```

**Installation**:
```bash
pip install requests python-dotenv
```

**Imports**:
```python
from dotenv import load_dotenv
import os

load_dotenv()
rapidapi_key = os.getenv('RAPIDAPI_KEY')
```

---

## Next Steps

1. **Create TwitterIntegration class** in `integrations/social/twitter_integration.py`
2. **Register in registry** (`integrations/registry.py`)
3. **Test end-to-end** via `python3 apps/ai_research.py "JTTF recent activity"`
4. **Update STATUS.md** with Twitter integration status

---

## Comparison: What Was Abandoned vs Salvaged

### ✅ SALVAGED (This Directory)
- **api_client.py** - Robust API client with pagination/retries (309 lines)
- **merged_endpoints.json** - Complete endpoint documentation (787 lines)
- **twitter_config.py** - API configuration (18 lines)
- **Total**: ~1,114 lines of useful, tested code

### ❌ ABANDONED (Left in twitterexplorer/)
- **Investigation engine** - Complex autonomous system with 6-node ontology
- **Graph visualization** - D3.js visualization with dead-end nodes
- **LLM coordination** - Multi-step investigation orchestration
- **Bridge integration** - Emergent question detection
- **Why abandoned**: "Fundamentally broken on some level" (visualization dead-ends, overcomplexity)
- **Total**: ~2,000+ lines of complex, broken code

**Benefit**: We get production-ready Twitter API client without inheriting broken investigation architecture.

---

## Related Documentation

- **REGISTRY_COMPLETE.md** - Registry refactor documentation
- **INVESTIGATIVE_PLATFORM_VISION.md** - Full platform roadmap (Twitter in Phase 3)
- **CLAUDE.md** - Development principles and patterns
- **STATUS.md** - Current component status

---

## Questions?

Check the following before asking:

1. **Endpoint parameters**: See `merged_endpoints.json` for complete parameter lists
2. **Pagination**: See `api_client.py` lines 145-226 for cursor handling
3. **Error handling**: See `api_client.py` lines 228-266 for retry logic
4. **Rate limits**: See `api_client.py` lines 232-239 for exponential backoff
5. **Integration pattern**: See `integrations/sam_integration.py` for complete example

---

**Status**: Ready for TwitterIntegration class creation
