# Deep Research - Source-Specific Validation Queries

**Purpose**: Validate that each of the 8 integrated sources adds value in its domain.

**Critical Constraint**: Queries must use natural language WITHOUT hardcoding source names. The LLM should intelligently select appropriate sources based on query content and source descriptions.

---

## Validation Query Design

Each query is designed to naturally map to a specific source's domain expertise based on the source descriptions in `research/deep_research.py:196-205`.

### 1. SAM.gov - Federal Contracting

**Source Description**: "U.S. federal contracting opportunities and solicitations. Use when: researching government contracts, procurement, awards, RFPs."

**Validation Query**:
```
"What federal cybersecurity contracts were awarded to defense contractors in 2024?"
```

**Expected Behavior**:
- LLM should identify keywords: "federal", "contracts", "awarded"
- Should select SAM.gov as primary source (matches "government contracts, procurement, awards")
- May also select Brave Search as supplementary

**Success Criteria**:
- SAM.gov selected by LLM (check source selection logs)
- Returns results about federal contract awards
- Results relevant to procurement/contracting domain

---

### 2. DVIDS - Military Multimedia

**Source Description**: "Military multimedia archive - returns EVENT MEDIA (photos/videos of military operations, ceremonies, exercises). Use when: seeking examples of military visual content."

**Validation Query**:
```
"What recent Joint Special Operations Command military exercises have been documented with photos or videos?"
```

**Expected Behavior**:
- LLM should identify keywords: "military exercises", "documented", "photos or videos"
- Should select DVIDS as primary source (matches "military visual content", "operations, ceremonies, exercises")
- May also select Brave Search for context

**Success Criteria**:
- DVIDS selected by LLM
- Returns results about military events with media assets
- Results relevant to operational/exercise documentation

---

### 3. USAJobs - Federal Employment

**Source Description**: "Official U.S. federal civilian job listings. Use when: researching government employment, positions, hiring."

**Validation Query**:
```
"What federal cybersecurity analyst positions are currently open in Washington DC?"
```

**Expected Behavior**:
- LLM should identify keywords: "federal", "positions", "currently open"
- Should select USAJobs as primary source (matches "government employment, positions, hiring")
- Should NOT select ClearanceJobs (federal civilian jobs, not clearance jobs)

**Success Criteria**:
- USAJobs selected by LLM
- Returns results about active federal job postings
- Results relevant to government employment

---

### 4. ClearanceJobs - Security Clearance Jobs

**Source Description**: "Private-sector security clearance jobs. Use when: researching cleared positions, defense contractor hiring."

**Validation Query**:
```
"What TS/SCI cleared intelligence analyst positions are available at defense contractors?"
```

**Expected Behavior**:
- LLM should identify keywords: "TS/SCI cleared", "defense contractors"
- Should select ClearanceJobs as primary source (matches "cleared positions, defense contractor hiring")
- Should NOT select USAJobs (private sector, not federal)

**Success Criteria**:
- ClearanceJobs selected by LLM
- Returns results about clearance-required private sector jobs
- Results relevant to defense contractor hiring

---

### 5. Twitter - Social Media Announcements

**Source Description**: "Social media posts and announcements. Use when: seeking official accounts, public announcements, real-time updates, community sentiment."

**Validation Query**:
```
"What have government agencies recently announced about new cybersecurity threats?"
```

**Expected Behavior**:
- LLM should identify keywords: "announced", "recently" (real-time updates)
- Should select Twitter as primary source (matches "official accounts, public announcements, real-time updates")
- May also select Brave Search for news articles

**Success Criteria**:
- Twitter selected by LLM
- Returns results about official announcements and public statements
- Results relevant to real-time government communication

---

### 6. Reddit - Community Discussion

**Source Description**: "Community discussions and OSINT analysis. Use when: seeking community insights, investigative threads, technical discussions."

**Validation Query**:
```
"What is the OSINT community discussing about Palantir's government contracts and capabilities?"
```

**Expected Behavior**:
- LLM should identify keywords: "OSINT community", "discussing"
- Should select Reddit as primary source (matches "community insights, investigative threads, technical discussions")
- May also select Twitter for public sentiment

**Success Criteria**:
- Reddit selected by LLM
- Returns results about community analysis and discussion
- Results relevant to investigative journalism/OSINT techniques

---

### 7. Discord - OSINT Community Knowledge

**Source Description**: "OSINT community server archives. Use when: seeking specialized OSINT community knowledge, technical tips."

**Validation Query**:
```
"What OSINT techniques are being shared by the community for analyzing satellite imagery of military installations?"
```

**Expected Behavior**:
- LLM should identify keywords: "OSINT techniques", "shared by the community"
- Should select Discord as primary source (matches "specialized OSINT community knowledge, technical tips")
- May also select Reddit as supplementary

**Success Criteria**:
- Discord selected by LLM
- Returns results about community-shared OSINT techniques
- Results relevant to technical analysis methods

---

### 8. Brave Search - Web Search

**Source Description**: "General web search engine. Use when: seeking official documentation, help pages, reference articles, Wikipedia entries, news articles. Ideal for: definitional queries (what is X?), how-to guides, background information."

**Validation Query**:
```
"What is the Defense Visual Information Distribution Service and what is its official mission?"
```

**Expected Behavior**:
- LLM should identify keywords: "what is", "official mission" (definitional query)
- Should select Brave Search as primary source (matches "definitional queries, official documentation, reference articles")
- Should NOT select DVIDS (asking about DVIDS, not asking for DVIDS content)

**Success Criteria**:
- Brave Search selected by LLM
- Returns results about documentation and background information
- Results relevant to reference/educational content

---

## Test Execution Plan

### Phase 1: Individual Source Tests (8 tests × 5 min = 40 min)

Run each validation query individually with Deep Research:

```python
engine = SimpleDeepResearch(
    max_tasks=3,                    # Fewer tasks for focused test
    max_retries_per_task=1,         # Fewer retries
    max_time_minutes=5,             # Short timeout
    min_results_per_task=3,         # Standard threshold
    max_concurrent_tasks=2          # Moderate parallelism
)

result = await engine.research("[validation query]")
```

**For each test, capture**:
1. Which sources were selected by LLM (check source selection logs)
2. How many results returned from target source
3. Sample of results (verify relevance to domain)
4. Total results from all sources

### Phase 2: Comparative Analysis

**Create summary table**:

| Source | Query | LLM Selected? | Results Count | Domain Relevance | Notes |
|--------|-------|---------------|---------------|------------------|-------|
| SAM.gov | Federal contracts query | ✅ / ❌ | X results | High / Med / Low | ... |
| DVIDS | Military exercises query | ✅ / ❌ | X results | High / Med / Low | ... |
| ... | ... | ... | ... | ... | ... |

### Phase 3: Findings & Recommendations

**Success Criteria** (per source):
- ✅ **PASS**: LLM selected source + returned >10 relevant results
- ⚠️ **PARTIAL**: LLM selected source + returned 3-10 results OR not selected but could have added value
- ❌ **FAIL**: LLM did not select source OR selected but returned <3 results OR results not relevant

**If source fails**:
1. Review source description - is it clear enough for LLM?
2. Review validation query - does it naturally match source's domain?
3. Consider if source adds value OR should be deprecated

---

## Expected Outcomes

**Hypothesis**: All 8 sources should add value in their respective domains when queries naturally match their expertise.

**Alternative Outcomes**:
1. **Source always selected, high quality** → ✅ KEEP (high value)
2. **Source never selected, but should be** → Fix source description
3. **Source selected, low quality results** → Investigate integration or API issues
4. **Source rarely selected, niche use case** → ✅ KEEP (valuable for edge cases)
5. **Source never selected, never needed** → Consider deprecating

---

## Notes on Natural Language Design

**Key Principles**:
1. **Use domain terminology** - Let LLM infer source from keywords (e.g., "contracts awarded" → SAM.gov)
2. **Specify content type** - Visual media → DVIDS, discussions → Reddit, jobs → USAJobs
3. **Avoid source names** - Never say "on SAM.gov" or "from DVIDS"
4. **Match source descriptions** - Queries use same terminology as source descriptions (lines 196-205)

**Anti-Patterns** (DO NOT DO):
- ❌ "Recent cybersecurity contract awards on SAM.gov" (hardcoded source name)
- ❌ "Search DVIDS for JSOC operations" (explicit source instruction)
- ❌ "What does SAM.gov show about contracts?" (source as subject, not query domain)

**Good Patterns**:
- ✅ "What federal contracts were awarded?" (domain keywords trigger SAM.gov)
- ✅ "What military exercises have been documented?" (media keywords trigger DVIDS)
- ✅ "What is the OSINT community discussing?" (community keywords trigger Reddit/Discord)
