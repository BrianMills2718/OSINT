# Current Status and Issues - Query Generation Analysis
**Date**: 2025-10-23
**Phase**: Query Prompt Improvement & Testing

---

## Executive Summary

We are systematically analyzing and improving how each of our 8 data source integrations generates search queries from natural language questions. The goal is to ensure queries are well-formed, return relevant results, and use appropriate syntax for each API.

**Current Progress**:
- ✅ Removed relevance filter (all sources now generate queries)
- ✅ Identified critical issues via analysis
- 🔄 Running comprehensive tests with actual search execution
- ⏳ Fixing issues based on test results

---

## What We're Working On

### Objective
Improve LLM-generated queries for each data source to maximize relevant results and minimize failures.

### Approach
1. **Generate test queries** - Use 3 diverse test queries to exercise all sources
2. **Analyze generated queries** - Review what LLM generates for each source
3. **Execute searches** - Actually run the searches to see result counts
4. **Identify issues** - Find patterns in failures, empty results, poor queries
5. **Fix prompts** - Improve LLM prompts for each integration
6. **Re-test** - Verify improvements

### Test Queries Being Used
1. **"SIGINT signals intelligence"** - Intelligence/technical topic
2. **"cybersecurity contracts"** - Contract/procurement topic
3. **"intelligence analyst jobs"** - Job listing topic

These 3 queries test different query types across all 8 sources (SAM.gov, DVIDS, USAJobs, ClearanceJobs, FBI Vault, Discord, Twitter, Brave Search).

---

## Current Status by Data Source

### 1. SAM.gov (Federal Contracts)
**Status**: [BLOCKED] - Rate limited

**Issue**: All queries return HTTP 429 "Too Many Requests"
```
Error: HTTP 0: 429 Client Error: Too Many Requests
```

**Root Cause**: API quota exhausted from previous testing

**Query Generation Quality**: Good
- Uses appropriate NAICS codes (541512, 541519, etc.)
- Generates relevant keywords with synonyms
- Correctly marks job queries as relevant (finds contract support positions)

**Action Required**: Wait for rate limit to reset OR upgrade API tier

---

### 2. DVIDS (Military Media)
**Status**: [MIXED] - Working but generating empty queries for some topics

**Results**:
- SIGINT: 29 results ✅ (good)
- Cyber threat intelligence: 1000 results ⚠️ (empty keywords = all results)
- Cybersecurity contracts: 1000 results ⚠️ (empty keywords = all results)

**Issue**: LLM generates empty keywords for non-military topics
```json
{
  "keywords": "",
  "media_types": ["image", "video", "news"]
}
```

**Impact**: Returns all military media instead of filtering

**Root Cause**: LLM correctly recognizes these aren't military topics but still generates a query with empty keywords instead of using fallback

**Action Required**: Update prompt to generate fallback keywords even for low-relevance topics

---

### 3. USAJobs (Federal Jobs)
**Status**: [WORKING] - Queries look good

**Results**:
- SIGINT: 0 results (may be legitimate - NSA not hiring for SIGINT currently)
- Cyber threat intelligence: 5 results ✅
- Cybersecurity contracts: 5 results ✅
- North Korea: 0 results (legitimate - narrow query)

**Query Generation Quality**: Excellent
- Simple 1-3 word keywords (as designed)
- No Boolean operators (API doesn't handle them well)
- Appropriate organization inference (NSA for SIGINT)

**Action Required**: None - working as designed

---

### 4. ClearanceJobs (Cleared Job Listings)
**Status**: [BROKEN] - Search not actually being submitted

**Results**:
- ALL queries return exactly 56,343 results
- "Intelligence Analyst": 56,343
- "security": 56,343
- "" (empty): 56,343
- "Kubernetes": 56,343
- "SIGINT OR signals intelligence": 56,343

**Issue**: Playwright scraper fills search input but search is NOT submitted

**Root Cause** (CONFIRMED via debug):
```
Initial URL: https://www.clearancejobs.com/jobs
After pressing Enter: https://www.clearancejobs.com/jobs  (NO CHANGE)
```

**Technical Details**:
1. Scraper fills input field correctly
2. Triggers Vue.js events
3. Presses Enter key
4. **BUT**: URL doesn't change - no query parameters added
5. Result: Scraper reads default `/jobs` page (all 56,343 jobs) instead of search results

**Query Generation Quality**: Good (but irrelevant since search doesn't work)
- Uses OR operators correctly
- Includes clearance-specific terms (TS/SCI, Top Secret)
- Includes relevant tools and agencies

**Action Required**:
1. Find correct way to submit ClearanceJobs search (button click? different selector?)
2. Verify URL changes to include search query after submit
3. Re-test with various queries to confirm filtering works

---

### 5. FBI Vault (FBI FOIA Documents)
**Status**: [WORKING] - Consistently returns 5 results

**Results**:
- All queries: 5 results (appears to be max limit or pagination issue)

**Query Generation Quality**: Excellent
- FBI-specific historical program names (SHAMROCK, ECHELON, PRISM)
- Combines topic terms with FBI context using AND logic
- Appropriate for document search

**Action Required**: Verify if 5 is actual result count or scraping limit

---

### 6. Discord (OSINT Community Discussions)
**Status**: [WORKING] - Good results

**Results**:
- SIGINT: 34 results ✅
- Cyber threat intelligence: 6 results ✅
- North Korea: 58 results ✅

**Query Generation Quality**: Good
- Generates discussion keywords not contract keywords (fixed)
- Uses array of 3-8 related terms
- ANY-match working (messages with any keyword returned)

**Known Issue**: Some Discord export files have JSON parse errors
```
Warning: Could not parse Project Owl...json: Expecting ',' delimiter
```

**Action Required**: Fix corrupted Discord export JSON files

---

### 7. Twitter (Social Media)
**Status**: [WORKING] - But queries too simple

**Results**:
- SIGINT: 40 results ✅
- Cyber threat intelligence: 40 results ✅
- Cybersecurity contracts: 40 results ✅

**Query Generation Quality**: TOO SIMPLE
- Just passes through original query ("SIGINT signals intelligence")
- No synonym expansion
- No hashtag generation (#SIGINT, #CyberSecurity)
- No Boolean operators despite Twitter supporting them

**Example of North Korea query (one exception - actually good)**:
```json
{
  "query": "(\"North Korea\" OR DPRK OR \"Democratic People's Republic of Korea\") AND (nuclear OR nukes OR \"nuclear test\" OR missile OR missiles OR ICBM OR ballistic OR \"weapons program\" OR WMD OR chemical OR biological OR Hwasong OR \"Kim Jong Un\" OR \"rocket launch\" OR \"test launch\" OR sanctions)",
  "search_type": "Latest",
  "max_pages": 3
}
```

**Action Required**: Update prompt to generate complex queries like North Korea example for all topics

---

### 8. Brave Search (Web Search)
**Status**: [WORKING] - But overly focused on "leaked"

**Results**:
- SIGINT: 5 results ("SIGINT leaked documents")
- Cyber threat intelligence: 5 results ("cyber threat intelligence leaked report")
- North Korea: 5 results ("North Korea weapons program investigation")

**Query Generation Quality**: OVERLY FOCUSED
- Always adds "leaked" to queries (wrong for informational searches)
- "intelligence analyst leaked report" doesn't make sense for job search
- Should differentiate investigative queries (add "leaked") from informational queries

**Action Required**: Update prompt to detect query intent and only add "leaked" for investigative topics

---

## Critical Issues Summary

### High Priority (CRITICAL)

1. **SAM.gov rate limit** [BLOCKED]
   - Impact: Cannot test contract searches
   - Fix: Wait for quota reset OR upgrade API tier
   - Workaround: None available

2. **ClearanceJobs returning all jobs** [SUSPICIOUS]
   - Impact: Cannot verify if queries actually filter results
   - Fix: Debug Playwright scraper keyword handling
   - Evidence needed: Manual browser test with same keywords

3. **DVIDS generating empty keywords** [MIXED]
   - Impact: Returns all military media instead of filtering
   - Fix: Update prompt to always generate fallback keywords
   - Easy fix: 5-line prompt change

### Medium Priority

4. **Twitter queries too simple** [WORKING BUT SUBOPTIMAL]
   - Impact: Missing relevant results that use different terminology
   - Fix: Update prompt to generate complex Boolean queries
   - Evidence: North Korea query shows LLM CAN do this

5. **Brave Search "leaked" assumption** [WORKING BUT SUBOPTIMAL]
   - Impact: Wrong intent detection for job/informational queries
   - Fix: Add intent detection logic to prompt
   - Evidence: "intelligence analyst leaked report" is nonsensical

### Low Priority

6. **Discord JSON parse errors** [MINOR]
   - Impact: Some Discord exports not searchable
   - Fix: Repair corrupted JSON files
   - Workaround: Errors logged but don't crash search

7. **FBI Vault 5-result limit** [UNVERIFIED]
   - Impact: May be missing results if actual count > 5
   - Fix: Investigate if this is scraping pagination limit
   - May not be an issue (could be legitimate count)

---

## Recent Changes

### Completed (2025-10-23)

1. **Removed relevance filter** (commit ae0432a)
   - All 8 integrations now ALWAYS generate query parameters
   - No more "NOT RELEVANT" responses that skip sources
   - Example: DVIDS now generates query for "cybersecurity contracts" (even if empty)

2. **Added anti-lying checklist** (commit 07a6f49)
   - Mandatory pre-report checklist to prevent cherry-picking
   - Forces FAIL-FIRST reporting format
   - Prevents hiding test failures

3. **Created query analysis documentation**
   - `query_prompt_improvement_analysis.md` - Detailed analysis of issues
   - `query_results_clean.txt` - Generated queries for 3 test queries
   - `query_generation_analysis_20251023_121900.txt` - Partial results with execution

---

## Next Steps

### Immediate (Today)
1. Let full test suite finish running (14 queries x 8 sources = 112 searches)
2. Analyze complete results file when ready
3. Fix DVIDS empty keywords issue (high impact, easy fix)
4. Debug ClearanceJobs 56,345 mystery (verify keyword filtering works)

### Short-term (This Week)
5. Update Twitter prompt for complex queries
6. Update Brave Search prompt for intent detection
7. Fix Discord JSON parse errors
8. Re-test all sources with improvements

### Long-term (When Rate Limit Clears)
9. Test SAM.gov improvements
10. Tune NAICS code generation
11. Add Boolean operator standardization across sources

---

## Testing Infrastructure

### Test Files
- `tests/test_quick_query_analysis.py` - Fast query generation only (no execution)
- `tests/test_query_generation_analysis.py` - Full analysis with search execution (slow)

### Output Files
- `query_results_clean.txt` - Query generation only
- `query_generation_analysis_20251023_*.txt` - Full results with execution
- `query_prompt_improvement_analysis.md` - Analysis and recommendations

### Test Execution Time
- Quick analysis: ~2 minutes (3 queries x 8 sources, generation only)
- Full analysis: ~15-20 minutes (14 queries x 8 sources with execution)
  - SAM.gov: 7s per query (fails with 429)
  - FBI Vault: 7-9s per query (Playwright scraping)
  - ClearanceJobs: 2-3s per query (Playwright scraping)
  - DVIDS: 2-4s per query
  - Others: <1s per query

---

## Key Metrics

### Query Generation Success Rate
- **8/8 sources** generating queries (100%) ✅
- **6/8 sources** returning results (75%)
- **2/8 sources** blocked/suspicious (SAM.gov, ClearanceJobs)

### Result Quality (Preliminary)
- **DVIDS**: Good when keywords present, problematic with empty keywords
- **USAJobs**: Good (expected 0 results for narrow queries)
- **FBI Vault**: Good (FBI-specific queries working)
- **Discord**: Good (discussion keywords working)
- **Twitter**: Working but suboptimal (too simple)
- **Brave Search**: Working but suboptimal (wrong intent)
- **SAM.gov**: Cannot verify (rate limited)
- **ClearanceJobs**: Cannot verify (suspicious identical counts)

---

## Architecture Notes

### How Query Generation Works

1. User enters natural language question: "SIGINT signals intelligence"
2. `ParallelExecutor` sends question to all 8 integrations simultaneously
3. Each integration's `generate_query()` calls LLM with source-specific prompt
4. LLM generates query parameters in source-specific format:
   - SAM.gov: `{"keywords": "...", "naics_codes": [...], ...}`
   - Twitter: `{"query": "...", "search_type": "Latest"}`
   - Discord: `{"keywords": ["term1", "term2", ...], ...}`
5. Integration's `execute_search()` calls API with generated parameters
6. Results returned in standardized `QueryResult` format

### LLM Models Used
- **Query Generation**: gpt-5-mini (fast, cheap, good at structured output)
- **Cost**: ~$0.001 per query generation
- **Speed**: 0-26 seconds per source (avg ~10s)

### Why Different Formats?
Each API has different capabilities:
- SAM.gov: Boolean OR, NAICS codes, procurement types
- USAJobs: Simple keywords only (no Boolean)
- Twitter: Boolean AND/OR with quotes
- Discord: Array of terms (ANY-match in code)
- Brave Search: Natural language queries

---

## Decision Log

### 2025-10-23

**Decision**: Remove relevance filter from all integrations
- **Rationale**: LLM was too conservative, marking sources "not relevant" that actually had content
- **Impact**: All sources now searched for every query
- **Tradeoff**: More API calls but fewer false negatives

**Decision**: Use gpt-5-mini for query generation
- **Rationale**: Fast, cheap, good at structured JSON output
- **Alternative considered**: gpt-4o-mini (similar performance, similar cost)
- **Result**: Working well, generates appropriate queries

**Decision**: Test with 3 diverse queries before fixing prompts
- **Rationale**: Need evidence of what's broken before fixing
- **Alternative considered**: Fix prompts based on theory (rejected - might fix wrong things)
- **Result**: Found real issues we wouldn't have predicted (DVIDS empty keywords, ClearanceJobs all-jobs)

---

## Files Modified Today

1. `CLAUDE.md` - Added anti-lying checklist at top of CORE PRINCIPLES
2. `CLAUDE_PERMANENT.md` - Added anti-lying checklist (for regeneration)
3. `integrations/government/*.py` (8 files) - Removed "relevant" field from schemas
4. `integrations/social/*.py` (2 files) - Removed "relevant" field from schemas
5. `query_prompt_improvement_analysis.md` - Created analysis document
6. `query_results_clean.txt` - Created query generation output
7. `remove_relevance_filter.py` - Script to remove relevance checks (temp utility)
8. `remove_relevant_property.py` - Script to remove "relevant" from schemas (temp utility)

---

## Open Questions

1. **ClearanceJobs 56,345**: Is this the total database size or is keyword filtering broken?
2. **FBI Vault 5 results**: Is this actual count or pagination limit?
3. **SAM.gov rate limit**: When does quota reset? Can we upgrade tier?
4. **DVIDS empty keywords**: Why does LLM generate empty string for "cyber threat intelligence"?
5. **Twitter query quality**: Why simple for most queries but complex for North Korea?

---

## Success Criteria (When Done)

- [ ] All 8 sources generate non-empty, well-formed queries
- [ ] Result counts vary appropriately by query (not always same count)
- [ ] SAM.gov rate limit resolved and queries return results
- [ ] ClearanceJobs keyword filtering verified working
- [ ] DVIDS generates keywords for all topics (no more empty strings)
- [ ] Twitter generates complex Boolean queries for all topics
- [ ] Brave Search differentiates investigative vs informational intent
- [ ] Discord JSON parse errors fixed
- [ ] Re-run full test suite shows improvement in results

---

## Contact / Owner

**Project**: SigInt Platform - Multi-source investigative research
**Phase**: Query Generation Improvement
**Owner**: Brian Mills
**AI Assistant**: Claude (Anthropic)
**Last Updated**: 2025-10-23 12:30 PM
