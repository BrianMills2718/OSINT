# Brave Search Integration - Comprehensive Plan

**Created**: 2025-10-21
**Purpose**: Add web search capability via Brave Search API
**Estimated Time**: 2-3 days
**API Key**: BSAlba0wYS4zpcWH1KfO-FhdfzpCZhH

---

## Executive Summary

**What**: Integrate Brave Search API as a new data source to cover open web content (news, analysis, leaked docs, court filings, advocacy reports)

**Why**: Existing sources are structured databases with narrow scopes. Brave fills gap between official government statements and actual investigative reporting/leaks/analysis.

**User Feedback**: "i think you have overbuilt the relevance filter. I only want it there to clearly exclude things which are clearly not relevant."

---

## Files to Create

### 1. Integration Class
**File**: `integrations/social/brave_search_integration.py`
**Lines**: ~400 (similar to federal_register.py)
**Purpose**: Brave Search API wrapper following DatabaseIntegration pattern

**Key Methods**:
```python
class BraveSearchIntegration(DatabaseIntegration):
    @property
    def metadata(self) -> DatabaseMetadata:
        # name="Brave Search", category=WEB_SEARCH, requires_api_key=True

    async def is_relevant(self, research_question: str) -> bool:
        # SIMPLIFIED: Always return True (let LLM decide in generate_query)
        # User wants minimal filtering, not overbuilt relevance checks

    async def generate_query(self, research_question: str) -> Optional[Dict]:
        # Use LLM to generate: query, count, freshness filter
        # Return None if LLM says not relevant

    async def execute_search(self, query_params, api_key, limit) -> QueryResult:
        # Call Brave Search API, return standardized results
```

**API Endpoint**: `https://api.search.brave.com/res/v1/web/search`

**Query Parameters** (from Brave API docs):
- `q`: Search query string (required)
- `count`: Number of results (1-20, default 10)
- `offset`: Pagination offset (0-9, default 0)
- `freshness`: Time filter (pd=past day, pw=past week, pm=past month, py=past year)
- `country`: Country code (default: all)
- `search_lang`: Search language (default: en)

**Response Fields** (to extract):
- `web.results[].title`: Page title
- `web.results[].url`: Page URL
- `web.results[].description`: Snippet
- `web.results[].age`: "X days ago" or publication date

---

## Files to Modify

### 1. Integration Registry
**File**: `integrations/registry.py`
**Changes**: Add Brave Search to registry
**Lines to add**: ~3

```python
from integrations.social.brave_search_integration import BraveSearchIntegration

# In registry dict:
"brave_search": BraveSearchIntegration,
```

### 2. Monitor Configs (Optional)
**Files**: `data/monitors/configs/*.yaml`
**Changes**: Add "brave_search" to sources list for monitors that need web coverage
**Which monitors**:
- surveillance_fisa_monitor.yaml (lots of news/analysis)
- special_operations_monitor.yaml (leaked docs, investigations)
- immigration_enforcement_monitor.yaml (news coverage)
- domestic_extremism_monitor.yaml (advocacy reports, analysis)

**Example**:
```yaml
sources:
  - dvids
  - federal_register
  - sam
  - usajobs
  - brave_search  # NEW
```

### 3. Environment Variables
**File**: `.env`
**Changes**: Add Brave API key
**Line to add**: `BRAVE_API_KEY=BSAlba0wYS4zpcWH1KfO-FhdfzpCZhH`

### 4. Requirements.txt (If needed)
**File**: `requirements.txt`
**Changes**: None required (uses `requests` which is already installed)

---

## Files to Create for Testing

### 1. Integration Test
**File**: `tests/test_brave_search_live.py`
**Lines**: ~80
**Purpose**: Test Brave Search integration with real API

```python
import asyncio
from integrations.social.brave_search_integration import BraveSearchIntegration

async def test_brave_search():
    integration = BraveSearchIntegration()

    # Test relevance check (should be True - simplified)
    relevant = await integration.is_relevant("NSA surveillance programs")
    assert relevant == True

    # Test query generation
    query_params = await integration.generate_query("NSA surveillance programs")
    assert query_params is not None

    # Test search execution
    result = await integration.execute_search(
        query_params,
        api_key="BSAlba0wYS4zpcWH1KfO-FhdfzpCZhH",
        limit=5
    )
    assert result.success
    assert len(result.results) > 0

    print(f"Found {len(result.results)} results")
    for item in result.results[:3]:
        print(f"  - {item['title']}")
        print(f"    {item['url']}")

asyncio.run(test_brave_search())
```

### 2. Monitor Test
**File**: `tests/test_brave_in_monitor.py`
**Lines**: ~50
**Purpose**: Test Brave Search through BooleanMonitor

```python
# Test that BooleanMonitor can use Brave Search
# Create temp monitor config with brave_search source
# Run monitor, verify Brave results included
```

---

## Brave Search API Details

### Rate Limits & Pricing
**Free Tier**: 2,000 queries/month
**Paid Tier**: $5 per 1,000 queries after free tier

**Current Usage Estimate** (with adaptive search):
- 5 monitors × 9 keywords avg × 3 phases × 30 days = ~4,050 queries/month
- Cost: ~$10-15/month if Brave enabled on all monitors

**Recommendation**: Enable selectively for monitors that need web coverage

### Authentication
**Header**: `X-Subscription-Token: <API_KEY>`
**No OAuth** - simple token-based auth

### Response Format
```json
{
  "query": {
    "original": "NSA surveillance",
    "show_strict_warning": false,
    "is_navigational": false,
    "spellcheck_off": false
  },
  "web": {
    "results": [
      {
        "title": "NSA Surveillance Programs - ACLU",
        "url": "https://www.aclu.org/issues/privacy/nsa",
        "description": "The NSA conducts several surveillance programs...",
        "age": "2 days ago",
        "language": "en",
        "profile": {
          "name": "ACLU",
          "url": "https://www.aclu.org",
          "img": "..."
        }
      }
    ],
    "type": "search"
  }
}
```

---

## Implementation Strategy

### Phase 1: Core Integration (Day 1)
**Time**: 4-6 hours

1. Create `brave_search_integration.py` following `federal_register.py` pattern
2. Implement simplified `is_relevant()` (always True per user feedback)
3. Implement `generate_query()` with LLM
4. Implement `execute_search()` with Brave API
5. Add to registry

**Success Criteria**:
- `test_brave_search_live.py` passes
- Returns 5-10 results for test query
- Results include title, URL, description

### Phase 2: Monitor Integration (Day 2)
**Time**: 2-3 hours

1. Add `BRAVE_API_KEY` to `.env`
2. Create test monitor config with Brave
3. Test through `BooleanMonitor`
4. Verify parallel execution works

**Success Criteria**:
- Monitor finds Brave results alongside other sources
- No crashes or import errors
- Results deduplicated correctly

### Phase 3: Production Deployment (Day 2-3)
**Time**: 2-4 hours

1. Add Brave to 2-3 production monitor configs (selective)
2. Test full adaptive search pipeline with Brave
3. Monitor first production run (check logs, costs, quality)
4. Adjust based on findings

**Success Criteria**:
- Production monitors run successfully
- Email alerts include Brave results
- API costs within expected range (~$0.50/day)
- Results quality good (not spam)

---

## Uncertainties & Risks

### 1. LLM Query Generation Quality
**Uncertainty**: Will LLM generate good web search queries vs database queries?
**Risk**: Overly specific queries → no results, or too broad → spam
**Mitigation**:
- Study successful web search query patterns
- Include examples in LLM prompt
- Test with diverse query types before production
**Test Plan**: Run 20 test queries covering different types (names, programs, concepts, acronyms)

### 2. Relevance Filter Simplification
**Uncertainty**: User wants simpler filtering - how simple is too simple?
**Risk**: Too loose → spam alerts, too strict → miss important results
**Mitigation**:
- Start with user's guidance: "clearly exclude things which are clearly not relevant"
- Use LLM relevance scoring but raise threshold from 6/10 to 8/10 for "clear" exclusion
- Monitor false positives in first week
**Test Plan**: Compare filtered results to user's manual review of sample

### 3. API Cost Overrun
**Uncertainty**: Will actual usage exceed estimates?
**Risk**: $10-15/month estimate could be $50+ if all monitors use Brave heavily
**Mitigation**:
- Start with Brave on 2 monitors only (surveillance, special ops)
- Track actual API call counts in first week
- Set up cost alerts via Brave dashboard
**Test Plan**: Log all Brave API calls for 7 days, calculate actual monthly cost

### 4. Result Quality vs Databases
**Uncertainty**: Will web results add value or just noise?
**Risk**: Too many low-quality blog posts, not enough primary sources
**Mitigation**:
- Use `freshness` filter (past month/week for timely results)
- LLM relevance filter scores authority/credibility
- User reviews first week of alerts, provides feedback
**Test Plan**: Side-by-side comparison - same query to Brave vs databases, manual quality assessment

### 5. Brave API Rate Limiting Behavior
**Uncertainty**: How does Brave handle rate limit violations?
**Risk**: 429 errors crash monitors, or silent failures lose data
**Mitigation**:
- Implement retry logic with exponential backoff
- Track rate limit headers (`x-ratelimit-remaining`)
- Log all 429 errors for analysis
**Test Plan**: Intentionally exceed rate limit in test, verify graceful handling

### 6. Duplicate Detection Across Sources
**Uncertainty**: Will Brave return URLs already found in Federal Register/DVIDS?
**Risk**: Same content counted twice (e.g., DVIDS press release + news article about it)
**Mitigation**:
- Existing deduplication by URL handles exact duplicates
- Consider content similarity detection (Phase 2 enhancement)
- Monitor duplicate rates in first week
**Test Plan**: Check if Brave returns federalregister.gov or dvidshub.net URLs

### 7. Stale/Outdated Content
**Uncertainty**: Will Brave return old content mixed with new?
**Risk**: Alerts for events from years ago
**Mitigation**:
- Use `freshness=pm` (past month) for most queries
- LLM extracts publication date from snippets
- Filter results older than monitor's date range
**Test Plan**: Test with historical query ("Iraq War 2003"), verify freshness filter works

---

## Concerns to Address

### 1. Relevance Filter Overbuild (User Feedback)
**User said**: "i think you have overbuilt the relevance filter. I only want it there to clearly exclude things which are clearly not relevant."

**Current Implementation**:
```python
# In boolean_monitor.py filter_by_relevance()
if score >= 6:  # CURRENT THRESHOLD
    relevant_results.append(result)
```

**Problem**: Threshold of 6/10 filters out marginal results that might be useful.

**Proposed Fix**:
```python
# Option A: Raise threshold (only exclude CLEARLY irrelevant)
if score >= 8:  # Only filter if clearly not relevant (0-7)
    relevant_results.append(result)

# Option B: Simplify prompt to focus on "clearly exclude"
prompt = """Is this result CLEARLY NOT RELEVANT to {keyword}?
Only respond "not relevant" if it's obviously spam or completely unrelated.
When in doubt, mark as relevant."""
```

**Recommendation**: Option A (raise threshold to 8/10) + simplify prompt

**Implementation**: Modify `boolean_monitor.py` lines 429-430:
```python
# OLD:
if score >= 6:

# NEW:
if score >= 8:  # User: "clearly exclude" = only exclude obvious mismatches
```

### 2. Web Search Spam/SEO Pollution
**Concern**: Web has more spam than structured databases
**Risk**: Brave returns SEO-optimized junk, ads, aggregator sites
**Mitigation**:
- LLM prompt includes "ignore SEO spam, aggregator sites, ads"
- Prioritize authoritative domains (news orgs, .gov, .edu, advocacy groups)
- Monitor first week for spam patterns
**Action Item**: Add domain authority hint to LLM prompt if spam appears

### 3. Cloudflare/Paywall Links
**Concern**: Brave may return links user can't access (paywalls, CF protection)
**Risk**: Alerts for content user can't read
**Mitigation**:
- Note accessibility in email alerts (flag paywalled sources)
- Focus on open-access journalism (ProPublica, Intercept, etc.)
- Archive.org fallback (Phase 2 enhancement)
**Action Item**: Log inaccessible URLs, analyze if problem emerges

### 4. International/Non-English Results
**Concern**: Brave might return non-English results
**Risk**: User can't read alerts
**Mitigation**:
- Set `search_lang=en` in API params
- LLM filters non-English results if any slip through
**Action Item**: Test with query that has international coverage (e.g., "Guantanamo Bay")

---

## Success Metrics

### Week 1 (Testing Phase)
- [ ] Integration passes all unit tests
- [ ] Brave results appear in monitor alerts
- [ ] No crashes or API errors
- [ ] Actual API cost < $5 for week
- [ ] User reviews sample alerts for quality

### Week 2-4 (Production Validation)
- [ ] At least 3 valuable results per week from Brave (user assessment)
- [ ] False positive rate < 20% (user feedback)
- [ ] API costs stable at ~$10-15/month
- [ ] No rate limit violations
- [ ] Duplicate rate < 10% (same content from Brave + other sources)

### Decision Point (End of Week 4)
**Keep Brave if**:
- User found valuable investigative leads from web search
- Cost justified by quality of results
- False positive rate acceptable

**Disable Brave if**:
- Mostly spam/low-quality results
- Cost too high vs value
- User not using Brave-found leads

---

## Rollback Plan

**If Brave integration fails or doesn't add value**:

1. **Remove from monitor configs** (30 seconds)
   ```bash
   # Edit each YAML, remove "brave_search" from sources list
   ```

2. **Comment out in registry** (10 seconds)
   ```python
   # "brave_search": BraveSearchIntegration,  # Disabled: not adding value
   ```

3. **Archive integration code** (preserve for future)
   ```bash
   mv integrations/social/brave_search_integration.py archive/2025-10-21/brave_search_integration.py
   ```

**No data loss** - Previous results still in monitors, system continues working

---

## Alternative Approaches Considered

### 1. Google Custom Search API
**Pros**: Broader coverage than Brave
**Cons**: More expensive ($5/1000 queries with 10k/day limit), tracking concerns
**Decision**: Brave chosen for privacy + cost

### 2. SerpAPI (aggregator)
**Pros**: Access to multiple search engines
**Cons**: Even more expensive ($50/month), adds complexity
**Decision**: Start simple with Brave, SerpAPI is overkill for MVP

### 3. DuckDuckGo Instant Answer API
**Pros**: Free, privacy-focused
**Cons**: Very limited (instant answers only, not full web search)
**Decision**: Not suitable for investigative research needs

### 4. Bing Web Search API
**Pros**: Robust, well-documented
**Cons**: Microsoft, similar cost to Brave, no privacy advantage
**Decision**: Brave preferred for privacy-focused journalism

---

## Open Questions for User

1. **Relevance threshold**: Change from 6/10 to 8/10 ("clearly exclude" interpretation)? Or different threshold?

2. **Which monitors get Brave**: All 5? Or selective (surveillance + special ops only)?

3. **Freshness filter**: Default to past month? Or past week for very timely topics?

4. **Cost limit**: What's max acceptable monthly cost for web search? ($10? $20? $50?)

5. **Quality bar**: Should LLM prioritize authoritative sources (.gov, major news) over blogs/small outlets?

---

## Next Steps

**After user review of this plan**:

1. Get answers to open questions
2. Implement relevance filter simplification (raise threshold)
3. Create `brave_search_integration.py` (Day 1)
4. Test with real API (Day 1)
5. Add to 1-2 monitors for pilot (Day 2)
6. Monitor first week, gather feedback (Week 1)
7. Expand or rollback based on results (Week 2)

---

## Summary Table

| Aspect | Detail |
|--------|--------|
| **Files to Create** | 1 integration class, 2 test files |
| **Files to Modify** | 1 registry, 4-5 monitor configs, 1 .env |
| **Time Estimate** | 2-3 days (6-8 hours coding + testing) |
| **Cost Estimate** | $10-15/month (selective deployment) |
| **Risk Level** | Low (easy rollback, no breaking changes) |
| **Uncertainties** | 7 identified (query quality, costs, spam) |
| **Mitigation** | Pilot on 2 monitors, monitor costs, week 1 review |
| **Success Metric** | User finds valuable leads from web search |

---

**Ready to proceed?** Address open questions above, then begin implementation.
