# Twitter Integration Quick Start

**Goal**: Add Twitter search to SIGINT platform in 2-3 hours

---

## Prerequisites

1. **RAPIDAPI_KEY** environment variable set in `.env`
2. **Registry refactor complete** (see REGISTRY_COMPLETE.md)
3. **Python packages**: `requests`, `python-dotenv` already installed

---

## Step 1: Test API Client (5 minutes)

**Verify extracted API client works**:

```bash
cd /home/brian/sam_gov
python3 -c "
from twitterexplorer_sigint.api_client import execute_api_step
from dotenv import load_dotenv
import os

load_dotenv()

result = execute_api_step(
    {'endpoint': 'search.php', 'params': {'query': 'JTTF', 'search_type': 'Latest'}, 'max_pages': 1, 'reason': 'Test'},
    [],
    os.getenv('RAPIDAPI_KEY')
)

print('✅ API client working!' if 'error' not in result else f'❌ Error: {result.get(\"error\")}')
print(f'Results: {len(result.get(\"data\", {}).get(\"timeline\", []))} tweets')
"
```

**Expected Output**:
```
✅ API client working!
Results: [0-20] tweets
```

**If Error**: Check RAPIDAPI_KEY in `.env`, verify RapidAPI subscription active

---

## Step 2: Create TwitterIntegration Class (1-2 hours)

**File**: `integrations/social/twitter_integration.py`

**Copy from**: `integrations/sam_integration.py` (complete working example)

**Template**:
```python
from typing import Optional, Dict
from core.database_integration_base import DatabaseIntegration, DatabaseMetadata, QueryResult, DatabaseCategory
from twitterexplorer_sigint.api_client import execute_api_step
from llm_utils import acompletion
from dotenv import load_dotenv
import json
import time
import os

load_dotenv()

class TwitterIntegration(DatabaseIntegration):
    """Twitter search integration using RapidAPI twitter-api45"""

    @property
    def metadata(self) -> DatabaseMetadata:
        return DatabaseMetadata(
            name="Twitter",
            id="twitter",
            category=DatabaseCategory.SOCIAL_MEDIA,
            requires_api_key=True,
            cost_per_query_estimate=0.01,  # RapidAPI cost per search
            typical_response_time=3.0,  # Seconds for typical search
            description="Twitter search for tweets, users, and trending topics using RapidAPI"
        )

    async def is_relevant(self, research_question: str) -> bool:
        """Quick keyword check before expensive LLM call"""
        keywords = [
            "twitter", "tweet", "social media", "trending",
            "conversation", "discussion", "public opinion",
            # SIGINT-specific keywords
            "jttf", "counterterrorism", "extremism", "radicalization"
        ]
        question_lower = research_question.lower()
        return any(keyword in question_lower for keyword in keywords)

    async def generate_query(self, research_question: str) -> Optional[Dict]:
        """Use LLM to generate Twitter search parameters"""

        prompt = f"""Given this research question, generate Twitter search parameters.

Research Question: {research_question}

Return ONLY valid JSON with this exact structure:
{{
    "query": "search keywords (use OR/AND/NOT for Boolean)",
    "search_type": "Latest" or "Top" or "Media" or "People" (choose one),
    "max_pages": 1-5 (number of pages to fetch),
    "reasoning": "why these parameters"
}}

Available search_type values:
- "Latest": Most recent tweets
- "Top": Most popular/relevant tweets
- "Media": Tweets with images/videos
- "People": User profiles matching query

Tips:
- Use "Latest" for time-sensitive research
- Use "Top" for high-engagement content
- Use Boolean operators: "JTTF OR counterterrorism"
- Keep queries focused (Twitter search limitations)

Return ONLY the JSON, no other text."""

        try:
            response = await acompletion(
                model="gpt-5-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "strict": True,
                        "name": "twitter_query",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string"},
                                "search_type": {"type": "string", "enum": ["Latest", "Top", "Media", "People"]},
                                "max_pages": {"type": "integer", "minimum": 1, "maximum": 5},
                                "reasoning": {"type": "string"}
                            },
                            "required": ["query", "search_type", "max_pages", "reasoning"],
                            "additionalProperties": False
                        }
                    }
                }
            )

            result = json.loads(response.choices[0].message.content)
            print(f"[TwitterIntegration] Generated query: {result['query']}")
            print(f"[TwitterIntegration] Search type: {result['search_type']}")
            print(f"[TwitterIntegration] Reasoning: {result['reasoning']}")

            return result

        except Exception as e:
            print(f"[TwitterIntegration] LLM query generation failed: {e}")
            return None

    async def execute_search(self, query_params: Dict, api_key: Optional[str] = None, limit: int = 10) -> QueryResult:
        """Execute Twitter search using api_client"""

        start_time = time.time()

        try:
            # Prepare step plan for api_client
            step_plan = {
                "endpoint": "search.php",
                "params": {
                    "query": query_params.get("query", ""),
                    "search_type": query_params.get("search_type", "Latest")
                },
                "max_pages": query_params.get("max_pages", 1),
                "reason": query_params.get("reasoning", "Twitter search")
            }

            # Execute search using api_client
            result = execute_api_step(step_plan, [], api_key)

            response_time_ms = (time.time() - start_time) * 1000

            # Check for errors
            if "error" in result:
                return QueryResult(
                    success=False,
                    source="Twitter",
                    total=0,
                    results=[],
                    error=result["error"],
                    query_params=query_params,
                    response_time_ms=response_time_ms
                )

            # Extract timeline (list of tweets)
            data = result.get("data", {})
            timeline = data.get("timeline", [])

            # Transform Twitter API format to SIGINT common format
            standardized_results = []
            for tweet in timeline[:limit]:  # Respect limit
                standardized_results.append({
                    # Common SIGINT fields
                    "title": tweet.get("text", "")[:100] + ("..." if len(tweet.get("text", "")) > 100 else ""),
                    "url": f"https://twitter.com/{tweet.get('user_info', {}).get('screen_name', 'unknown')}/status/{tweet.get('tweet_id', '')}",
                    "date": tweet.get("created_at", ""),
                    "description": tweet.get("text", ""),

                    # Twitter-specific metadata
                    "author": tweet.get("user_info", {}).get("screen_name", ""),
                    "author_name": tweet.get("user_info", {}).get("name", ""),
                    "verified": tweet.get("user_info", {}).get("verified", False),
                    "favorites": tweet.get("favorites", 0),
                    "retweets": tweet.get("retweets", 0),
                    "replies": tweet.get("replies", 0),
                    "views": tweet.get("views", "0"),
                    "tweet_id": tweet.get("tweet_id", ""),
                    "conversation_id": tweet.get("conversation_id", "")
                })

            return QueryResult(
                success=True,
                source="Twitter",
                total=len(timeline),  # Total from current page(s)
                results=standardized_results,
                query_params=query_params,
                response_time_ms=response_time_ms
            )

        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            return QueryResult(
                success=False,
                source="Twitter",
                total=0,
                results=[],
                error=f"Twitter search failed: {str(e)}",
                query_params=query_params,
                response_time_ms=response_time_ms
            )
```

**Save to**: `integrations/social/twitter_integration.py`

---

## Step 3: Create social/ Directory (if doesn't exist)

```bash
mkdir -p integrations/social
touch integrations/social/__init__.py
```

---

## Step 4: Register in Registry (5 minutes)

**File**: `integrations/registry.py`

**Add at top**:
```python
from integrations.social.twitter_integration import TwitterIntegration
```

**Add in `_register_defaults()` method**:
```python
self.register(TwitterIntegration)
```

**Verify registration**:
```bash
python3 -c "from integrations.registry import registry; print(registry.list_ids())"
```

**Expected Output**:
```
['sam', 'dvids', 'usajobs', 'clearancejobs', 'fbi_vault', 'discord', 'twitter']
```

---

## Step 5: Test Integration (30 minutes)

### Test 1: Import Check
```bash
python3 -c "from integrations.social.twitter_integration import TwitterIntegration; print('✅ Import successful')"
```

### Test 2: Basic Functionality
```python
import asyncio
from integrations.social.twitter_integration import TwitterIntegration
from dotenv import load_dotenv
import os

load_dotenv()

async def test():
    integration = TwitterIntegration()

    # Test is_relevant
    print(f"Relevant: {await integration.is_relevant('JTTF counterterrorism activity')}")

    # Test generate_query
    query_params = await integration.generate_query("JTTF recent activity")
    print(f"Query params: {query_params}")

    # Test execute_search
    result = await integration.execute_search(query_params, os.getenv('RAPIDAPI_KEY'), limit=5)
    print(f"Success: {result.success}")
    print(f"Results: {result.total}")
    for i, tweet in enumerate(result.results[:3], 1):
        print(f"\n{i}. {tweet['author']}: {tweet['title']}")
        print(f"   URL: {tweet['url']}")
        print(f"   Engagement: {tweet['favorites']} likes, {tweet['retweets']} RTs")

asyncio.run(test())
```

### Test 3: End-to-End via AI Research
```bash
python3 apps/ai_research.py "JTTF recent counterterrorism operations"
```

**Expected**: LLM selects Twitter as relevant source, searches execute, results display

---

## Step 6: Update Documentation (30 minutes)

### Update STATUS.md
```markdown
| Component | Status | Evidence |
|-----------|--------|----------|
| Twitter Integration | [PASS] | python3 apps/ai_research.py "JTTF" returns Twitter results |
```

### Update REGISTRY_COMPLETE.md
Add Twitter to "Current Registry Contents":
```markdown
**7 Sources Registered**:
...
7. `twitter` - Twitter (social media intelligence) - Requires API key (RapidAPI)
```

---

## Common Issues & Fixes

### Issue 1: "No module named 'twitterexplorer_sigint'"
**Fix**: Ensure you're running from `/home/brian/sam_gov` directory

### Issue 2: "RAPIDAPI_KEY not found"
**Fix**: Add to `.env`:
```bash
RAPIDAPI_KEY=your-key-here
```

### Issue 3: "401 Unauthorized" from API
**Fix**: Verify RapidAPI subscription is active, check API key is correct

### Issue 4: Empty results
**Fix**: Twitter search has coverage limitations, try different keywords

### Issue 5: "gpt-5-mini not found"
**Fix**: Change to `gpt-4o-mini` in generate_query() if gpt-5-mini unavailable

---

## Success Criteria

**ALL must be true**:
- [ ] Registry lists 'twitter' in available sources
- [ ] `python3 -c "from integrations.social.twitter_integration import TwitterIntegration"` succeeds
- [ ] Test query via AI Research returns Twitter results
- [ ] Results display with proper formatting (author, URL, engagement)
- [ ] No errors or timeouts
- [ ] STATUS.md updated with [PASS]

---

## Time Estimate

| Step | Time | Cumulative |
|------|------|------------|
| 1. Test API client | 5 min | 5 min |
| 2. Create TwitterIntegration | 1-2 hours | 2 hours |
| 3. Create social/ directory | 2 min | 2 hours |
| 4. Register in registry | 5 min | 2h 5min |
| 5. Testing | 30 min | 2h 35min |
| 6. Documentation | 30 min | **3h 5min** |

**Total**: 2-3 hours to fully working Twitter integration

---

## Next Steps After Completion

1. **Boolean Monitors**: Add Twitter to monitoring capabilities
2. **Advanced Features**: User timeline tracking, conversation threading
3. **Additional Endpoints**: trends.php, followers.php for network mapping
4. **Cost Optimization**: Monitor RapidAPI usage, optimize pagination

---

## Questions?

- **API Client**: See `twitterexplorer_sigint/README.md`
- **Endpoint Docs**: See `twitterexplorer_sigint/merged_endpoints.json`
- **Integration Pattern**: See `integrations/sam_integration.py`
- **Registry Pattern**: See `REGISTRY_COMPLETE.md`
