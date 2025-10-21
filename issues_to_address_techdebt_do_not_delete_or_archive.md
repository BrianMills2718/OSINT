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

**Last Updated**: 2025-10-21
