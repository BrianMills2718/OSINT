# Query Prompt Improvement Analysis
Generated: 2025-10-23

This document analyzes current query generation for each data source and identifies improvements needed.

---

## Test Queries Used

1. **SIGINT signals intelligence** - Intelligence/technical topic
2. **cybersecurity contracts** - Contract/procurement topic
3. **intelligence analyst jobs** - Job listing topic

---

## SAM.gov (Federal Contracts)

### Current Query Generation

**Query 1: SIGINT signals intelligence**
```json
{
  "keywords": "SIGINT signals intelligence COMINT ELINT \"signals intelligence systems\" \"signals intelligence analysis\" electronic warfare sensors collection analytics",
  "procurement_types": ["Solicitation", "Presolicitation", "Combined Synopsis/Solicitation", "Sources Sought"],
  "set_aside": null,
  "naics_codes": ["541512", "541519", "518210", "334111"],
  "organization": null,
  "date_range_days": 180
}
```

**Query 2: cybersecurity contracts**
```json
{
  "keywords": "cybersecurity OR \"information security\" OR \"network security\" OR \"penetration testing\" OR \"incident response\" OR \"vulnerability assessment\"",
  "procurement_types": ["Solicitation", "Presolicitation", "Combined Synopsis/Solicitation", "Sources Sought"],
  "set_aside": null,
  "naics_codes": ["541512", "541519", "541513", "541511", "518210"],
  "organization": null,
  "date_range_days": 180
}
```

**Query 3: intelligence analyst jobs**
```
NOT RELEVANT (correctly marked)
```

### Issues Identified

1. **Inconsistent Boolean operators**: Query 1 uses spaces (AND), Query 2 uses "OR"
2. **SAM.gov API limitation**: Known to return HTTP 429 rate limits frequently
3. **Good**: Correctly marks job queries as not relevant
4. **Good**: Uses appropriate NAICS codes
5. **Good**: Includes synonyms and related terms

### Improvements Needed

- [ ] Standardize on "OR" operator (SAM.gov handles OR better than implicit AND)
- [ ] Add retry/backoff logic for HTTP 429 (already implemented)
- [ ] Consider reducing keyword count to avoid overly restrictive searches

---

## DVIDS (Military Media)

### Current Query Generation

**Query 1: SIGINT signals intelligence**
```json
{
  "keywords": "SIGINT OR \"signals intelligence\" OR COMINT OR ELINT OR \"electronic warfare\"",
  "media_types": ["image", "video", "news"],
  "branches": [],
  "country": null,
  "from_date": null,
  "to_date": null
}
```

**Query 2: cybersecurity contracts**
```
NOT RELEVANT (correctly marked)
```

**Query 3: intelligence analyst jobs**
```
NOT RELEVANT (correctly marked)
```

### Issues Identified

1. **Good**: Uses OR operators consistently
2. **Good**: Correctly marks non-military topics as not relevant
3. **Good**: Includes appropriate acronyms (SIGINT, COMINT, ELINT)
4. **Known issue**: Query decomposition needed when OR returns 0 results (already implemented)

### Improvements Needed

- [ ] None - DVIDS prompt appears well-tuned

---

## USAJobs (Federal Jobs)

### Current Query Generation

**Query 1: SIGINT signals intelligence**
```json
{
  "keywords": "signals intelligence",
  "location": null,
  "organization": "National Security Agency",
  "pay_grade_low": 7,
  "pay_grade_high": 15
}
```

**Query 2: cybersecurity contracts**
```json
{
  "keywords": "cybersecurity",
  "location": null,
  "organization": null,
  "pay_grade_low": 9,
  "pay_grade_high": 15
}
```

**Query 3: intelligence analyst jobs**
```json
{
  "keywords": "intelligence analyst",
  "location": null,
  "organization": null,
  "pay_grade_low": 5,
  "pay_grade_high": 13
}
```

### Issues Identified

1. **EXCELLENT**: Simple 1-3 word keywords (no Boolean operators)
2. **Good**: Appropriate organization inference (NSA for SIGINT)
3. **Good**: Reasonable pay grade ranges
4. **Fixed**: Previous issue with complex OR queries resolved

### Improvements Needed

- [ ] None - USAJobs prompt working well after fix

---

## ClearanceJobs (Cleared Jobs)

### Current Query Generation

**Query 1: SIGINT signals intelligence**
```json
{
  "keywords": "SIGINT OR \"signals intelligence\" OR COMINT OR ELINT OR \"signals analyst\" OR \"SIGINT analyst\" OR \"SIGINT engineer\" OR \"electronic warfare\" OR EW OR \"RF engineer\" OR \"signal processing\" OR DSP OR cryptologic OR \"cryptologic linguist\" OR \"collection manager\" OR collection OR \"signals operator\" OR \"COMINT analyst\" OR \"signals exploitation\" OR \"intelligence analyst\" OR ISR OR \"mission systems\" OR cyber"
}
```

**Query 2: cybersecurity contracts**
```json
{
  "keywords": "cybersecurity OR \"cyber security\" OR cyber OR infosec OR \"information assurance\" OR \"security engineer\" OR \"cybersecurity engineer\" OR \"cybersecurity analyst\" OR \"incident response\" OR \"SOC analyst\" OR \"threat intelligence\" OR \"penetration tester\" OR \"red team\" OR \"blue team\" OR vulnerability OR RMF OR ISSO OR ISSM OR \"federal contractor\" OR DoD OR NSA OR IC"
}
```

**Query 3: intelligence analyst jobs**
```json
{
  "keywords": "intelligence analyst, all-source intelligence analyst, SIGINT analyst, GEOINT analyst, HUMINT analyst, OSINT analyst, collection manager, targeting analyst, counterintelligence analyst, threat analyst, watch officer, \"intelligence analyst cleared\", \"TS/SCI intelligence analyst\", \"Top Secret intelligence analyst\", \"intelligence analyst contractor\", Palantir analyst, \"Analyst's Notebook\", i2, ArcGIS"
}
```

### Issues Identified

1. **PROBLEM**: Query 3 uses COMMAS instead of "OR" operators
2. **Good**: Comprehensive synonym lists
3. **Good**: Includes clearance-specific terms ("TS/SCI", "Top Secret")
4. **Good**: Includes tool names (Palantir, ArcGIS)
5. **Inconsistent**: Query 3 format differs from 1 and 2

### Improvements Needed

- [x] **CRITICAL**: Fix Query 3 to use "OR" instead of commas
- [ ] Consider if keyword lists are too long (may not matter for ClearanceJobs)

---

## FBI Vault (FBI FOIA Documents)

### Current Query Generation

**Query 1: SIGINT signals intelligence**
```json
{
  "query": "(SIGINT OR \"signals intelligence\" OR COMINT OR ELINT OR \"signals intercept\" OR \"intercepted communications\" OR \"electronic surveillance\" OR wiretap OR \"wire tap\" OR \"Project SHAMROCK\" OR ECHELON OR PRISM OR NSA OR \"National Security Agency\" OR FISA OR \"Foreign Intelligence Surveillance Act\" OR \"pen register\" OR \"section 702\" OR \"upstream collection\") AND (FBI OR \"Federal Bureau of Investigation\" OR \"intelligence sharing\" OR counterintelligence)"
}
```

**Query 2: cybersecurity contracts**
```json
{
  "query": "(\"cybersecurity contract\" OR \"cyber security contract\" OR \"cyber contract\" OR \"cybersecurity services\" OR \"cybersecurity vendor\" OR contractor OR procurement OR \"service agreement\" OR MOU OR \"memorandum of understanding\") AND (cyber OR cybersecurity OR \"information security\" OR \"network security\" OR intrusion OR \"incident response\" OR threat)"
}
```

**Query 3: intelligence analyst jobs**
```json
{
  "query": "\"intelligence analyst\" AND (job OR jobs OR hiring OR vacancy OR \"job announcement\" OR \"job description\" OR \"position description\" OR training OR \"personnel records\" OR \"organizational chart\" OR \"intelligence workforce\" OR \"analytical unit\" OR \"Intelligence Branch\")"
}
```

### Issues Identified

1. **EXCELLENT**: Uses FBI-specific historical program names (SHAMROCK, ECHELON, PRISM)
2. **Good**: Combines topic terms with FBI context (AND logic)
3. **Good**: Appropriate for document search (not web search)
4. **Good**: Query 3 correctly searches for FBI personnel records related to jobs

### Improvements Needed

- [ ] None - FBI Vault prompt appears well-tuned

---

## Discord (OSINT Community Discussions)

### Current Query Generation

**Query 1: SIGINT signals intelligence**
```json
{
  "keywords": ["sigint", "signals intelligence", "signal interception", "communication intelligence", "electronic surveillance", "data collection", "intelligence gathering", "surveillance technology"],
  "servers": null,
  "date_range": null
}
```

**Query 2: cybersecurity contracts**
```json
{
  "keywords": ["cybersecurity threats", "data breach discussions", "hacker tactics", "network security", "digital espionage", "cyber defense strategies", "information warfare", "privacy concerns"],
  "servers": null,
  "date_range": null
}
```

**Query 3: intelligence analyst jobs**
```json
{
  "keywords": ["intelligence community", "analyst insights", "geopolitical trends", "security analysis", "osint discussions", "intelligence operations", "data-driven decision", "threat assessment"],
  "servers": null,
  "date_range": null
}
```

### Issues Identified

1. **GOOD**: After fix, generates discussion keywords not contract keywords
2. **Good**: Uses array of 3-8 terms
3. **Good**: Preserves multi-word phrases
4. **Query 2 ISSUE**: Still somewhat generic ("cybersecurity threats" vs "cybersecurity contract discussions")

### Improvements Needed

- [ ] Consider tuning Query 2 to be more specific to contract discussions
- [ ] Verify ANY-match filtering is working (multiple keywords should increase recall)

---

## Twitter (Social Media)

### Current Query Generation

**Query 1: SIGINT signals intelligence**
```json
{
  "query": "SIGINT signals intelligence",
  "search_type": "Latest",
  "max_pages": 2,
  "reasoning": "Keyword search for: SIGINT signals intelligence"
}
```

**Query 2: cybersecurity contracts**
```json
{
  "query": "cybersecurity contracts",
  "search_type": "Latest",
  "max_pages": 2,
  "reasoning": "Keyword search for: cybersecurity contracts"
}
```

**Query 3: intelligence analyst jobs**
```json
{
  "query": "intelligence analyst jobs",
  "search_type": "Latest",
  "max_pages": 2,
  "reasoning": "Keyword search for: intelligence analyst jobs"
}
```

### Issues Identified

1. **TOO SIMPLE**: Just passes through the original query
2. **Missing**: No attempt to add synonyms or related terms
3. **Missing**: No hashtag generation (#SIGINT, #CyberSecurity, etc.)
4. **Missing**: No account targeting (@NSAGov, @CISAgov, etc.)

### Improvements Needed

- [x] **CRITICAL**: Add synonym expansion
- [x] **CRITICAL**: Add hashtag generation
- [ ] Consider adding account targeting for known sources
- [ ] Consider using search operators (OR, quotes)

---

## Brave Search (Web Search)

### Current Query Generation

**Query 1: SIGINT signals intelligence**
```json
{
  "query": "SIGINT leaked documents",
  "count": 20,
  "country": "us"
}
```

**Query 2: cybersecurity contracts**
```json
{
  "query": "cybersecurity contracts leaked investigation",
  "count": 20,
  "country": "us",
  "freshness": "py"
}
```

**Query 3: intelligence analyst jobs**
```json
{
  "query": "intelligence analyst leaked report",
  "count": 20,
  "country": "us",
  "freshness": "py"
}
```

### Issues Identified

1. **TOO FOCUSED**: Always adds "leaked" to queries
2. **Query 3 PROBLEM**: "intelligence analyst leaked report" doesn't make sense for job search
3. **Missing**: No consideration of query intent (investigative vs informational)
4. **Good**: Uses freshness filter appropriately

### Improvements Needed

- [x] **CRITICAL**: Don't always assume "leaked documents" intent
- [x] **CRITICAL**: Differentiate between investigative queries (add "leaked") and informational queries
- [ ] Add more sophisticated query construction based on topic type

---

## Summary: Priority Improvements

### High Priority (CRITICAL)

1. **ClearanceJobs**: Fix comma-separated keywords (should be OR-separated)
2. **Twitter**: Add synonym expansion and hashtag generation
3. **Brave Search**: Fix overly focused "leaked" assumption

### Medium Priority

4. **SAM.gov**: Standardize Boolean operators (prefer OR)
5. **Discord**: Tune cybersecurity contract query

### Low Priority (Working Well)

- DVIDS: No changes needed
- USAJobs: No changes needed
- FBI Vault: No changes needed

---

## Next Steps

1. Fix ClearanceJobs comma issue
2. Enhance Twitter query generation
3. Fix Brave Search query intent detection
4. Standardize SAM.gov Boolean operators
5. Re-run test_query_generation_analysis.py to verify improvements
