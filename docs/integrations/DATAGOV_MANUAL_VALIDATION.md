# Data.gov Manual Validation Guide

**Purpose**: Validate data quality and relevance for investigative journalism use cases

**Estimated Time**: 20-30 minutes

---

## Manual Validation: Data Signal Test

This test cannot be automated - you need to manually assess dataset relevance.

### Step 1: Access Data.gov Catalog

Navigate to: https://catalog.data.gov/dataset

### Step 2: Test Investigative Journalism Queries

Run these searches and document findings for each:

#### Query 1: "intelligence operations"
- **Number of results**: _______
- **Relevant datasets** (list names of 3-5 most relevant):
  1.
  2.
  3.
- **Dataset types** (reports, APIs, raw data, metadata): _______
- **Recency** (updated in last 2 years?): _______
- **Assessment** (High/Medium/Low relevance): _______

#### Query 2: "JSOC" (Joint Special Operations Command)
- **Number of results**: _______
- **Relevant datasets**:
  1.
  2.
  3.
- **Dataset types**: _______
- **Recency**: _______
- **Assessment**: _______

#### Query 3: "classified programs"
- **Number of results**: _______
- **Relevant datasets**:
  1.
  2.
  3.
- **Dataset types**: _______
- **Recency**: _______
- **Assessment**: _______

#### Query 4: "SIGINT" (Signals Intelligence)
- **Number of results**: _______
- **Relevant datasets**:
  1.
  2.
  3.
- **Dataset types**: _______
- **Recency**: _______
- **Assessment**: _______

#### Query 5: "FISA surveillance"
- **Number of results**: _______
- **Relevant datasets**:
  1.
  2.
  3.
- **Dataset types**: _______
- **Recency**: _______
- **Assessment**: _______

### Step 3: Sample Dataset Deep Dive

Pick 1 dataset that looks most relevant and examine it:

**Dataset Name**: _______________________________

**Publisher**: _______________________________

**Description**:
_________________________________________________________________
_________________________________________________________________

**Last Updated**: _______________________________

**Data Format**: CSV / JSON / PDF / API / Other: _______

**Content Quality**:
- [ ] Contains actual investigative data
- [ ] Only metadata/catalog info
- [ ] Administrative/policy documents
- [ ] Raw data requiring analysis
- [ ] Pre-analyzed reports/summaries

**Usefulness for Investigative Journalism** (1-5 stars): ☆☆☆☆☆

**Notes**:
_________________________________________________________________
_________________________________________________________________

---

## Decision Criteria

Based on your manual testing, assess:

### Overall Data Quality Score

Count how many queries returned **relevant** datasets (High or Medium assessment):

- **5 of 5 queries**: Excellent signal - **STRONG GO**
- **3-4 of 5 queries**: Good signal - **GO**
- **1-2 of 5 queries**: Weak signal - **MAYBE** (proceed with low expectations)
- **0 of 5 queries**: No signal - **NO-GO** (defer to custom integration or skip)

### Expected Value Assessment

**HIGH VALUE** (proceed with integration):
- 10+ relevant datasets across queries
- Multiple recent updates (last 2 years)
- Mix of data types (not just metadata)
- Clear investigative journalism use cases

**MEDIUM VALUE** (proceed but with realistic expectations):
- 5-9 relevant datasets
- Some recent updates
- Mostly reports/summaries (not raw data)
- Supplementary to other sources

**LOW VALUE** (defer or skip):
- <5 relevant datasets
- Mostly stale data (5+ years old)
- Only metadata/catalog info
- No clear investigative use cases

---

## Integration Recommendation

Based on your findings, what should we do?

### Option A: Proceed with datagov-mcp-server (Recommended if HIGH or MEDIUM value)

**Conditions**:
- Automated validation passed (STDIO reliable)
- Manual validation shows MEDIUM or HIGH value
- Willing to invest 6-9 hours integration + 4-6 hours custom later

**Benefit**: Demonstrates third-party MCP integration, tests STDIO transport

### Option B: Build Custom Integration Only (Recommended if LOW value or STDIO unreliable)

**Conditions**:
- Manual validation shows LOW value OR
- Automated validation failed (STDIO unreliable) OR
- Want to avoid Node.js dependency

**Benefit**: Direct control, Python-native, no third-party dependency

**Estimated effort**: 4-6 hours

### Option C: Skip Data.gov Entirely (Recommended if NO signal)

**Conditions**:
- Manual validation shows 0 relevant datasets
- No investigative journalism use cases
- Better to focus on other features

**Benefit**: Focus effort on higher-value integrations (web search, document analysis)

---

## Report Your Findings

After completing manual validation, update:

1. **docs/DATAGOV_MCP_PREFLIGHT_ANALYSIS.md**
   - Add section: "Manual Validation Results"
   - Include query results, dataset quality assessment
   - Update final recommendation based on empirical data

2. **CLAUDE.md TEMPORARY section**
   - Update blocker status with validation results
   - Change status to GO / NO-GO / DEFER based on findings

3. **Discuss with Claude**
   - Share manual validation findings
   - Get updated recommendation incorporating both automated + manual validation results
   - Decide: Proceed, defer, or skip

---

## Example Manual Validation Report

```
MANUAL VALIDATION RESULTS (2025-10-24)

Query: "intelligence operations"
- Results: 47 datasets
- Relevant: 3 datasets (Congressional reports, GAO audits, DoD unclassified docs)
- Types: PDF reports, metadata catalogs
- Recency: 2 updated in last year, 1 from 2020
- Assessment: MEDIUM relevance

Query: "JSOC"
- Results: 0 datasets
- Assessment: NO relevance (expected - classified topic)

Query: "classified programs"
- Results: 12 datasets
- Relevant: 0 datasets (all about classification systems, not actual classified info)
- Assessment: LOW relevance

Query: "SIGINT"
- Results: 2 datasets
- Relevant: 1 dataset (NSA declassified documents catalog)
- Types: Metadata only (links to external archive)
- Assessment: LOW relevance (metadata, not content)

Query: "FISA surveillance"
- Results: 5 datasets
- Relevant: 2 datasets (FISA court statistics, DOJ transparency reports)
- Types: Annual reports (PDF)
- Recency: Updated annually
- Assessment: MEDIUM relevance

OVERALL ASSESSMENT:
- 2 of 5 queries returned relevant datasets = WEAK signal
- Most results are metadata/reports, not investigative content
- Value: LOW-MEDIUM (supplementary, not primary source)

RECOMMENDATION: DEFER
- Data.gov has some value but not enough to justify Node.js complexity
- Better to focus on web search (Brave Search already integrated)
- Consider custom integration later if Data.gov proves essential
```

---

**Next Steps**: Run automated validation (`python3 tests/test_datagov_validation.py`), then complete this manual validation, then report findings.
