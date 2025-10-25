# Technical Debt & Known Issues

**DO NOT DELETE OR ARCHIVE THIS FILE**

This file tracks ongoing technical issues, bugs, and tech debt that need to be addressed.

---

## High Priority

### SAM.gov Integration - Search Execution Failure
**Discovered**: 2025-10-21
**Severity**: High (complete integration failure)
**Status**: Not started

**Symptoms**:
- All SAM.gov searches returning 0 results with 0ms response time
- Pattern seen in logs: ` SAM.gov: 0 results (0ms)`
- LLM query generation succeeds (queries are being created)
- API call appears to fail silently without executing

**Evidence**:
```
# From realistic_test_monitor.yaml test run (2025-10-21):
   DVIDS: Query generated
   SAM.gov: Query generated
   USAJobs: Query generated
 Generated 3 queries
Phase 3: Executing searches...
   DVIDS: 37 results (3501ms)
   SAM.gov: 0 results (0ms)          # <-- 0ms indicates no actual API call
   USAJobs: 0 results (967ms)
```

**Impact**:
- SAM.gov completely non-functional for all monitors
- Federal contract data unavailable
- Adaptive search missing critical government contracting insights

**Possible Causes**:
1. API key expired or invalid
2. SAM.gov API endpoint changed
3. Request format changed (headers, authentication)
4. Silent exception handling swallowing errors
5. Network/firewall blocking SAM.gov API specifically

**Investigation Steps**:
1. Check `.env` for valid `SAM_GOV_API_KEY`
2. Test SAM.gov integration directly: `python3 -c "from integrations.government.sam_integration import SAMIntegration; import asyncio; asyncio.run(SAMIntegration().execute_search({'keywords': 'cybersecurity'}, api_key='...', limit=5))"`
3. Check `integrations/government/sam_integration.py` execute_search() for silent error handling
4. Review SAM.gov API documentation for recent changes
5. Add verbose logging to SAM.gov integration
6. Test SAM.gov API directly with curl/httpie

**Files**:
- `integrations/government/sam_integration.py` (lines 195-346: execute_search method)
- `core/api_request_tracker.py` (check if errors are being logged)

**Related**:
- Integration relevance fix (2025-10-21): Fixed overly restrictive is_relevant() - now all integrations call LLM for query generation. SAM.gov query generation works, but execution fails.

---

## Medium Priority

### ClearanceJobs Integration - Playwright Not Available on Streamlit Cloud
**Discovered**: 2025-10-21
**Severity**: Medium (integration non-functional on Streamlit Cloud)
**Status**: Resolved

**Symptoms**:
- `ModuleNotFoundError` when importing `playwright.async_api` on Streamlit Cloud
- ClearanceJobs integration requires Playwright for web scraping
- Playwright browser binaries too large/resource-intensive for Streamlit Cloud free tier

**Evidence**:
```
ModuleNotFoundError: This app has encountered an error.
File "/mount/src/osint/apps/unified_search_app.py", line 274, in <module>
    from clearancejobs_search import render_clearancejobs_tab
File "/mount/src/osint/apps/clearancejobs_search.py", line 15, in <module>
    from integrations.government.clearancejobs_playwright import search_clearancejobs
File "/mount/src/osint/integrations/government/clearancejobs_playwright.py", line 17, in <module>
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
```

**Impact**:
- ClearanceJobs integration breaks entire Streamlit Cloud app
- App cannot load due to hard import dependency
- Security-cleared job data unavailable on cloud deployment

**Solution Implemented** (2025-10-21):
1. ✅ Wrapped ClearanceJobs import in try/except in `integrations/registry.py`
2. ✅ Only registers ClearanceJobsIntegration if Playwright available
3. ✅ Wrapped UI import in try/except in `apps/unified_search_app.py`
4. ✅ Shows helpful error message in ClearanceJobs tab when unavailable
5. ✅ App continues functioning with other 7 integrations (DVIDS, SAM.gov, USAJobs, Twitter, Discord, Federal Register, Brave Search)

**Files Modified**:
- `integrations/registry.py` - Added `CLEARANCEJOBS_AVAILABLE` flag and conditional registration
- `apps/unified_search_app.py` - Wrapped import in try/except with user-friendly error message

**Result**:
- App loads successfully on Streamlit Cloud even without Playwright
- ClearanceJobs tab shows helpful message explaining why it's unavailable
- All other features fully functional
- Works perfectly on local deployments that have Playwright installed

---

### FBI Vault Integration - SeleniumBase Chrome Detection
**Discovered**: 2025-10-20
**Severity**: Medium (integration blocked but not critical for MVP)
**Status**: DEFERRED

**Symptoms**:
- SeleniumBase reports "Chrome not found!" despite Chrome binary existing
- Chrome installed at: `~/.cache/puppeteer/chrome/linux-131.0.6778.204/chrome-linux64/chrome`
- Code already passes `binary_location` parameter to SeleniumBase

**Impact**:
- FBI Vault integration non-functional
- FOIA documents unavailable
- Not critical for Phase 1 MVP

**Possible Causes**:
1. WSL2 environment detection issues
2. SeleniumBase expecting different Chrome path structure
3. Permissions issues with Puppeteer cache directory

**Investigation Steps** (when prioritized):
1. Try manual SeleniumBase installation: `playwright install chromium`
2. Test Chrome binary directly: `~/.cache/puppeteer/chrome/linux-131.0.6778.204/chrome-linux64/chrome --version`
3. Check SeleniumBase documentation for WSL2-specific configuration
4. Try alternative Chrome installation methods

**Files**:
- `integrations/government/fbi_vault.py` (lines 156-253: _scrape_fbi_vault_sync method)

---

## Low Priority

### Enhanced Entity Extraction (crest_kg) - Performance Too Slow
**Discovered**: 2025-10-24
**Severity**: Low (optional feature, current simple extraction works)
**Status**: DEFERRED - NO-GO for now

**Issue**: Enhanced knowledge graph extraction with relationships + attributes is 4x slower than acceptable

**Evidence** (from validation tests):
```
Simple extraction:  12-14s per 5 results (2.8s per result)
Enhanced KG:        55-66s per 5 results (12s per result)
Time overhead:      3.9-4.7x (limit: 3.0x)

9-task investigation impact:
- Current:  126s (2 min)
- Enhanced: 540s (9 min overhead) ← UNACCEPTABLE
```

**Quality** (from validation):
- ✅ Entities: +77% more (16-20 vs 8-9)
- ✅ Relationships: 20-24 extracted (simple: 0)
- ✅ Attributes: Rich metadata on entities
- ⚠️ Accuracy: ~90% (10% inferred from context)

**Root Cause**:
- gpt-5-mini reasoning tokens scale exponentially with output complexity
- Complex JSON (entities + relationships + attributes) requires massive reasoning
- 10x more output tokens → 4x more total time

**Optimization Options** (not tested):
1. **gpt-4o-mini instead**: 50-60% faster, may hit 3x limit (30 min test)
2. **End-of-investigation only**: Run once on ALL results (2-3 min total acceptable)
3. **Simpler schema**: Remove attributes, keep just entities + relationships (20% faster)
4. **Hybrid approach**: Simple per-task + enhanced at end

**Reconsider if**:
- User demand validated (do they actually want graph visualizations?)
- End-of-investigation extraction acceptable (2-3 min)
- gpt-4o-mini testing shows <3x overhead
- Relationships prove critical for investigative value

**Don't reconsider if**:
- Need per-task extraction for follow-up tasks
- Need real-time response (<30s)
- Current simple extraction sufficient

**Files**:
- Validation results: `CREST_KG_VALIDATION_RESULTS.md`
- Test scripts: `tests/test_crest_kg_schema_validation.py`, `tests/test_crest_kg_quality_comparison.py`
- Reference: `crest_kg/kg_from_text2.py` (fixed hardcoded API key)
- Integration plan: `CREST_KG_INTEGRATION_PLAN.md`

**Decision**: NO-GO for current implementation. Keep simple extraction as-is. Revisit only if user demand or performance improves.

**Last Reviewed**: 2025-10-24

---

### Twitter Integration - Missing Dependency
**Discovered**: 2025-10-21
**Severity**: Low (optional Phase 3 integration)
**Status**: Resolved (gracefully handled)

**Issue**:
- `twitterexplorer_sigint` module not installed
- Caused import errors when loading integration registry

**Resolution**:
- Wrapped Twitter integration import in try/except in `integrations/registry.py`
- Integration only registered if dependency available
- System continues functioning without Twitter support

**Future Action**:
- Install `twitterexplorer_sigint` when Phase 3 social media integrations are prioritized

**Files**:
- `integrations/registry.py` (lines 16-21: conditional Twitter import)
- `integrations/social/twitter_integration.py` (requires twitterexplorer_sigint)

---

## Completed / Resolved

###  Integration Relevance False Negatives
**Discovered**: 2025-10-20
**Resolved**: 2025-10-21

**Issue**: Overly restrictive keyword matching in `is_relevant()` causing false negatives

**Solution**: Changed all integrations to return `True` from `is_relevant()`, letting smarter LLM in `generate_query()` handle all relevance decisions

**Files Modified**:
- `integrations/government/dvids_integration.py`
- `integrations/government/sam_integration.py`
- `integrations/government/usajobs_integration.py`
- `integrations/government/fbi_vault.py`

**Verification**: Tested with realistic_test_monitor.yaml - all integrations now properly evaluating keywords via LLM

---

## How to Use This File

**Adding Issues**:
1. Add to appropriate priority section
2. Include: Discovered date, Severity, Status, Symptoms, Evidence, Impact, Possible Causes, Investigation Steps, Related Files
3. Use clear headings and code blocks for evidence

**Resolving Issues**:
1. Move to "Completed / Resolved" section
2. Document solution and verification
3. DO NOT DELETE - keep for historical reference

**Prioritization**:
- **High**: Blocking core functionality, affects production
- **Medium**: Limits features but workarounds exist
- **Low**: Nice to have, future enhancements

---

**Last Updated**: 2025-10-24
