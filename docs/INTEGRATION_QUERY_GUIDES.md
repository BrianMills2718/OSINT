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
- REST API: `https://api.dvidshub.net/v1/`
- Official docs: (TODO: add link)

### Query Syntax

**Status**: Not yet tested empirically
**Documentation**: TODO - review official API docs

### Known Limitations

**Intermittent HTTP 403 errors** (documented in STATUS.md):
- Cause: Unknown (content filtering suspected but not proven)
- Frequency: ~2/3 queries for sensitive operational terms (JSOC, special operations)
- Mitigation: Query decomposition already implemented (dvids_integration.py:299)

### Recommendations

(TODO: Conduct systematic query syntax testing similar to Reddit)

---

## SAM.gov (System for Award Management)

### API Endpoint
- REST API: `https://api.sam.gov/opportunities/v2/search`
- Official docs: https://open.gsa.gov/api/opportunities-api/

### Query Syntax

**Status**: Not yet tested empirically
**Documentation**: Official API supports full Lucene query syntax

### Known Limitations

- **Rate limiting**: Aggressive rate limits, HTTP 429 common
- **Slow API**: 12s average response time
- Mitigation: Exponential backoff implemented (sam_integration.py:213-235)

### Recommendations

(TODO: Conduct systematic query syntax testing)

---

## USAJobs

### API Endpoint
- REST API: `https://data.usajobs.gov/api/search`
- Official docs: https://developer.usajobs.gov/

### Query Syntax

**Status**: Not yet tested empirically

### Known Limitations

- Requires specific headers: `User-Agent` (email) and `Authorization-Key` (NOT Bearer token)
- Fixed in usajobs_integration.py

### Recommendations

(TODO: Conduct systematic query syntax testing)

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
