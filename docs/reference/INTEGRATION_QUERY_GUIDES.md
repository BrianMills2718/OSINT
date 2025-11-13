# Integration Query Guides

**Purpose**: Document source-specific query syntax, limitations, and best practices discovered through empirical testing.

**Last Updated**: 2025-10-25

---

## Reddit Search

### API Endpoint
- Uses PRAW (Python Reddit API Wrapper)
- Endpoint: `/r/{subreddit}/search`
- Official docs provide NO query syntax documentation (only says `q: string no longer than 512 characters`)

### Query Syntax (Empirically Tested)

**Testing Date**: 2025-10-25
**Test Subreddits**: security, Intelligence, natsec, OSINT
**Test Query Intent**: Find posts about "threat intelligence AND contracts"

#### What Works (Evidence-Based)

| Syntax | Example | Results | Accuracy | Notes |
|--------|---------|---------|----------|-------|
| **Unquoted AND** | `threat intelligence AND contract` | 7 | **43%** | BEST option |
| Simple keywords | `threat intelligence contract` | 20 | 15% | More results, lower accuracy |
| Simple OR | `JTTF OR counterterrorism` | Varies | ~15% | Works for alternatives |

#### What Doesn't Work (Evidence-Based)

| Syntax | Example | Results | Accuracy | Issue |
|--------|---------|---------|----------|-------|
| **Quoted + Boolean** | `"threat intelligence" AND contract` | 1 | **0%** | Returns wrong results |
| **Parentheses** | `(contract OR procurement)` | 1 | 0% | Breaks query |
| Quoted + nested | `"threat intelligence" AND (contract OR procurement)` | 1 | 0% | Combines both problems |

#### Test Evidence

**Accuracy Calculation Method**:
- Retrieved 7-20 results per query
- Manually verified if result contains ALL required terms
- Accuracy = (correct matches / total results) × 100%

**Unquoted AND Test**:
```
Query: threat intelligence AND contract
Results: 7 posts
Manual verification:
  - 3 contained "threat" + "intelligence"/"intel" + "contract"/"procurement" ✓
  - 4 did not contain all terms ✗
Accuracy: 3/7 = 43%
```

**Quoted + Boolean Test**:
```
Query: "threat intelligence" AND contract
Results: 1 post
Manual verification:
  - Title: "OSINT consulting?"
  - Contains: "threat" ✓, "intel" ✓, "contract" ✗
  - Verdict: WRONG result
Accuracy: 0/1 = 0%
```

### Recommendations

1. **Use unquoted keywords with AND**: Best accuracy (~40%)
2. **Avoid quoted phrases with Boolean**: Breaks queries (0% accuracy)
3. **Avoid parentheses**: Reddit ignores or misprocesses them
4. **Keep queries simple**: 2-3 keywords maximum
5. **Accept fuzzy matching**: Even best syntax only gets ~40% accuracy

### Known Limitations

- Reddit search uses fuzzy/relevance matching, not strict Boolean logic
- No official documentation of query syntax
- Quoted phrases break Boolean operators
- Parentheses not supported for grouping
- Best achievable accuracy is ~40-45%

---

## DVIDS (Defense Visual Information Distribution Service)

### API Endpoint
- REST API: `https://api.dvidshub.net/search`
- Official docs: https://www.dvidshub.net/api

### Query Syntax (Empirically Tested)

**Testing Date**: 2025-10-25
**Test Method**: Systematic isolation testing with 25+ queries
**Evidence Files**:
- `tests/test_dvids_isolate_403.py`
- `tests/test_dvids_final_isolation.py`
- `tests/test_dvids_quotes_only.py`

#### What Works (Evidence-Based)

| Syntax | Example | Status | Notes |
|--------|---------|--------|-------|
| **Simple keywords** | `JSOC` | ✅ 200 | Single terms work |
| **Multiple keywords** | `JSOC Delta Force DEVGRU` | ✅ 200 | No quotes needed |
| **OR operator (unquoted)** | `JSOC OR Delta OR DEVGRU` | ✅ 200 | Up to 12+ OR terms work |
| **1 quoted phrase** | `"Joint Special Operations Command"` | ✅ 200 | Single phrase OK |
| **2 quoted phrases** | `"hello world" OR "foo bar"` | ✅ 200 | Max 2 phrases work |
| **Long URLs** | 757 char URL with dummy terms | ✅ 200 | Length not the issue |

#### What Doesn't Work (Evidence-Based)

| Syntax | Example | Status | Issue |
|--------|---------|--------|-------|
| **3+ quoted phrases** | `"phrase1" OR "phrase2" OR "phrase3"` | ❌ 403 | **HARD LIMIT** |
| **Complex quoted queries** | `JSOC OR "Joint Special Operations Command" OR "special operations"` | ❌ 403 | 3rd quoted phrase triggers block |

#### Test Evidence

**Critical Finding**: DVIDS API limits queries with quoted phrases to maximum 2 OR terms total.

**The Rule**:
- If query has NO quoted phrases → unlimited OR terms allowed
- If query has ANY quoted phrases → maximum 2 TOTAL OR terms allowed (quoted or unquoted)

**Verification Testing (2025-10-25)**:

**No Quotes - Unlimited OR Terms Allowed**:
```
✅ PASS | 2 terms:  one OR two
✅ PASS | 3 terms:  one OR two OR three
✅ PASS | 5 terms:  one OR two OR three OR four OR five
✅ PASS | 10 terms: one OR two OR three OR four OR five OR six OR seven OR eight OR nine OR ten
```

**With Quotes - Maximum 2 TOTAL OR Terms**:
```
At Limit (2 terms) - PASS:
✅ PASS | 1 quoted alone:        "one two"
✅ PASS | 1 quoted + 1 unquoted: "one two" OR three
✅ PASS | 2 quoted + 0 unquoted: "one two" OR "three four"

Over Limit (3+ terms) - FAIL:
❌ FAIL | 1 quoted + 2 unquoted: "one two" OR three OR four
❌ FAIL | 2 quoted + 1 unquoted: "one two" OR "three four" OR five
❌ FAIL | 3 quoted + 0 unquoted: "one two" OR "three four" OR "five six"
```

**Content-agnostic**: Works with innocent terms ("hello", "world") and military terms (JSOC, Delta Force) equally.

**Not content filtering**:
- `JSOC` alone: ✅ 200
- `Delta Force` alone: ✅ 200
- `JSOC OR Delta OR DEVGRU` (unquoted): ✅ 200 (no limit without quotes)
- `JSOC OR "Delta Force" OR DEVGRU`: ❌ 403 (3 terms with 1 quoted)

**Not URL length**:
- 757 char URL: ✅ 200 (with unquoted terms)
- 116 char URL: ❌ 403 (with 3 OR terms + quotes)

### Known Limitations

**Maximum 2 OR terms when quotes are used**:
- Root cause: API security measure (likely prevents query injection or abuse)
- Trigger: Any query containing quoted phrases + 3 or more OR terms
- Workaround: Remove quotes OR limit to 2 total OR terms
- Status: API limitation, cannot be changed
- Note: Unlimited OR terms allowed if NO quotes used

**Query decomposition mitigation**:
- Implementation: `dvids_integration.py:299`
- Behavior: Breaks complex OR queries into individual term searches
- Effectiveness: Helps avoid 3+ phrase limit by searching terms separately
- Result: Combines results from multiple simple queries

### Recommendations

1. **Limit quoted phrases to 2 maximum**: Hard API limit
2. **Prefer unquoted keywords**: `JSOC Delta Force` instead of `"JSOC" OR "Delta Force" OR "DEVGRU"`
3. **Use query decomposition**: Already implemented for OR queries
4. **Single complex phrase OK**: `"Joint Special Operations Command"` works alone
5. **Avoid LLM-generated complex queries**: LLMs tend to create queries with 3+ quoted phrases

### Implementation Notes

**Current LLM prompt** (dvids_integration.py:200):
- May generate queries with 3+ quoted phrases
- Should be updated to limit quoted phrases to 2 maximum
- Consider instructing LLM to prefer unquoted keywords

**Mitigation already exists**:
- Query decomposition at line 299 handles OR queries
- Breaks complex queries into simple terms
- Combines results from multiple API calls

---

## SAM.gov (System for Award Management)

### API Endpoint
- REST API: `https://api.sam.gov/opportunities/v2/search`
- Official docs: https://open.gsa.gov/api/opportunities-api/

### Query Syntax

**Status**: Unable to test empirically due to strict rate limits
**Documentation**: Official API claims to support full Lucene query syntax
**Testing Date**: 2025-10-25

### Query Syntax (Documented)

**SAM.gov Official Documentation** claims full Lucene support:
- Boolean operators: AND, OR, NOT
- Quoted phrases: "exact phrase"
- Parentheses: (term1 OR term2) AND term3
- Character limit: ~200 characters maximum for keywords parameter

**Cannot Verify**: Empirical testing blocked by aggressive rate limiting (HTTP 429)

### Known Limitations

**Rate Limiting (Critical Issue)**:
- **Severity**: SEVERE - blocks empirical testing entirely
- **Test Evidence** (2025-10-25): 15/15 test queries returned HTTP 429 (100% rate limited)
- **Timing**: Even with 2-second delays between requests, all queries rate limited
- **Impact**: Cannot validate query syntax, Boolean operators, or character limits empirically
- **Mitigation**: Exponential backoff implemented (sam_integration.py:293-314)
  - Retries: 3 attempts with 2s, 4s, 8s delays
  - Not sufficient for testing workload
- **Production Status**: Working with retry logic, but unreliable for high-volume queries

**Slow API**:
- Average response time: 12s (when not rate limited)
- Timeout configured: 15s (sam_integration.py:298)

### Recommendations

**For Query Generation** (LLM Prompt):
1. **Assume Lucene syntax works** per official documentation
2. **Keep queries simple** - prefer 2-3 keywords over complex Boolean
3. **Limit length** - stay under 200 characters
4. **Avoid over-optimization** - rate limits make complex queries impractical

**For Testing**:
1. **Cannot conduct systematic syntax testing** due to rate limits
2. **Test with production queries only** - avoid test suites that trigger 429
3. **Accept official documentation** without empirical validation

**For Production**:
1. **Use exponential backoff** (already implemented)
2. **Limit SAM.gov queries** - only use when specifically needed
3. **Cache results aggressively** - avoid repeated queries
4. **Consider SAM.gov unreliable** for high-volume applications

---

## USAJobs

### API Endpoint
- REST API: `https://data.usajobs.gov/api/search`
- Official docs: https://developer.usajobs.gov/

### Query Syntax (Empirically Tested)

**Testing Date**: 2025-10-25
**Test Method**: 11 query variations tested against live API
**Test File**: tests/test_usajobs_query_syntax.py

#### What Works (Evidence-Based)

| Syntax | Example | Results | Notes |
|--------|---------|---------|-------|
| **Simple keywords** | `intelligence` | 10 | BEST - most results |
| **Two keywords (space)** | `intelligence analyst` | 3 | Works, fewer results than single keyword |
| **Boolean AND** | `intelligence AND analyst` | 2 | Works, but more restrictive than space |
| **Boolean OR** | `intelligence OR security` | 10 | Works well, similar to simple keyword |
| **Boolean NOT** | `intelligence NOT classified` | 4 | Works as expected |
| **Quoted phrase** | `"intelligence analyst"` | 1 | Works for exact matching |

#### What Doesn't Work (Evidence-Based)

| Syntax | Example | Results | Issue |
|--------|---------|---------|-------|
| **Three keywords (space)** | `intelligence analyst senior` | 0 | Too specific - no matches |
| **Quoted phrase with AND** | `"intelligence analyst" AND senior` | 0 | Complexity breaks query |
| **Parentheses** | `(intelligence OR security) AND analyst` | 0 | Grouping not supported |
| **Complex Boolean** | `intelligence OR security OR analyst OR investigator` | 0 | Multiple OR terms break query |
| **Mixed quotes + OR** | `"intelligence analyst" OR cybersecurity` | 0 | Mixing syntax breaks query |

#### Test Evidence

**Key Finding**: Simple Boolean operators (AND, OR, NOT) work individually, but COMPLEX queries with multiple operators or parentheses return 0 results.

**Simple Keywords Performance**:
```
✅ "intelligence" → 10 results (BEST)
✅ "intelligence analyst" → 3 results (Good)
✅ "intelligence analyst senior" → 0 results (Too specific)
```

**Boolean Operators Performance**:
```
✅ "intelligence AND analyst" → 2 results (Works, but fewer than space-separated)
✅ "intelligence OR security" → 10 results (Works well, similar to simple)
✅ "intelligence NOT classified" → 4 results (Works as expected)
```

**Complex Queries Performance**:
```
❌ "intelligence OR security OR analyst OR investigator" → 0 results (Multiple OR breaks)
❌ "(intelligence OR security) AND analyst" → 0 results (Parentheses not supported)
❌ '"intelligence analyst" OR cybersecurity' → 0 results (Mixed syntax breaks)
```

**Accuracy Comparison**:
- Simple queries: 4.3 results average (3 tests)
- Boolean queries: 5.3 results average (3 tests)
- Conclusion: Single Boolean operators work as well or better than simple keywords

### Recommendations

**For Query Generation** (LLM Prompt):

**✅ DO USE**:
1. **Single keyword** - Best for broad searches: `intelligence`
2. **Two keywords (space)** - Good for focused searches: `intelligence analyst`
3. **Single Boolean operator** - AND/OR/NOT work individually: `intelligence OR security`
4. **Quoted phrases** - For exact matches: `"intelligence analyst"`

**❌ DO NOT USE**:
1. **Three or more keywords** - Too specific, likely 0 results
2. **Multiple OR terms** - `term1 OR term2 OR term3` breaks query
3. **Parentheses** - Grouping not supported
4. **Mixed syntax** - Don't combine quotes + Boolean
5. **Complex Boolean** - Stick to simple single-operator queries

**Strategy**:
- **Prefer**: Simple 1-2 keyword queries
- **Allow**: Single Boolean operator if needed (AND/OR/NOT)
- **Avoid**: Complexity - USAJobs API breaks with complex queries

### Known Limitations

**Query Complexity Intolerance**:
- Single Boolean operators work
- Multiple Boolean operators return 0 results
- Parentheses not supported for grouping
- Mixing quoted phrases with Boolean breaks queries

**API Headers**:
- Requires specific headers: `User-Agent` (email) and `Authorization-Key` (NOT Bearer token)
- Fixed in usajobs_integration.py

### Implementation Notes

**Current LLM Prompt** (usajobs_integration.py:102-104):
- States: "DO NOT use OR operators or complex Boolean queries"
- **Evidence**: Partially incorrect - single OR works fine, complex queries don't
- **Recommendation**: Update to allow single Boolean operators, disallow complexity

---

## ClearanceJobs

### API Endpoint
- Scraped via Playwright (official Python API broken)
- Website: https://www.clearancejobs.com/

### Query Syntax

**Status**: Uses web form, not API query syntax

### Known Limitations

- Official Python library broken (returns all 57k jobs regardless of query)
- Workaround: Playwright scraping (slower but accurate)
- Performance: 5-8s vs 2s for API

### Recommendations

- Use Playwright implementation (clearancejobs_playwright.py)
- Accept slower performance for accuracy

---

## Twitter/X

### API Endpoint
- Via RapidAPI proxy
- Endpoint: (TODO: document)

### Query Syntax

**Status**: Not yet tested empirically

### Known Limitations

(TODO: Document known issues)

### Recommendations

(TODO: Conduct systematic query syntax testing)

---

## Discord

### API Endpoint
- Local JSON export search (not live API)
- Searches exported Discord archive files

### Query Syntax

**Status**: Local text search, not API-dependent

### Known Limitations

- 4 corrupted JSON files skipped in test data
- Only searches local exports, not live Discord

### Recommendations

- Works for local archive analysis
- Not suitable for real-time monitoring

---

## Testing Methodology

### How to Test Query Syntax for a New Source

1. **Choose test intent**: Define what you're trying to find (e.g., "posts about X AND Y")

2. **Test variations systematically**:
   - Simple keywords: `keyword1 keyword2`
   - Quoted phrases: `"exact phrase"`
   - Boolean AND: `keyword1 AND keyword2`
   - Boolean OR: `keyword1 OR keyword2`
   - Nested: `keyword1 AND (keyword2 OR keyword3)`
   - Combinations of above

3. **Collect metrics**:
   - Number of results returned
   - Manual verification: Do results actually match intent?
   - Calculate accuracy: (correct results / total results) × 100%

4. **Document findings**:
   - What syntax works best (highest accuracy)
   - What syntax doesn't work (breaks queries or returns wrong results)
   - Example queries with expected behavior
   - Known limitations

5. **Update this document** with evidence-based recommendations

### Template for New Source

```markdown
## [Source Name]

### API Endpoint
- Base URL:
- Official docs:

### Query Syntax

**Testing Date**: YYYY-MM-DD
**Test Scenario**: [Describe what you tested]

#### What Works

| Syntax | Example | Results | Accuracy | Notes |
|--------|---------|---------|----------|-------|
| | | | | |

#### What Doesn't Work

| Syntax | Example | Results | Accuracy | Issue |
|--------|---------|---------|----------|-------|
| | | | | |

### Known Limitations

- [List discovered limitations]

### Recommendations

1. [Specific recommendations based on testing]
```

---

## Contributing

When you discover query syntax quirks through testing:

1. **Document the test**: Date, method, sample size
2. **Provide evidence**: Actual queries tested and results
3. **Calculate metrics**: Accuracy percentages when possible
4. **Update this file**: Add findings to appropriate section
5. **Update integration code**: Update LLM prompts with tested guidance
