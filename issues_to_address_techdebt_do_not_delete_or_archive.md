# Technical Debt & Known Issues

**DO NOT DELETE OR ARCHIVE THIS FILE**

This file tracks ongoing technical issues, bugs, and tech debt that need to be addressed.

---

## High Priority

**No high priority issues currently open.**

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

### LiteLLM Async Logging Worker Timeout
**Discovered**: 2025-11-02
**Resolved**: 2025-11-02
**Severity**: Low (non-critical, appears in logs but doesn't affect functionality)
**Status**: ✅ **RESOLVED**

**Symptoms**:
```
LiteLLM:ERROR: logging_worker.py:73 - LoggingWorker error:
Traceback (most recent call last):
  File "/usr/lib/python3.12/asyncio/tasks.py", line 520, in wait_for
    return await fut
           ^^^^^^^^^
asyncio.exceptions.CancelledError
...
TimeoutError
```

**Context**:
- Appears during deep research execution when tasks timeout
- LiteLLM version: 1.74.14
- Our code uses `asyncio.wait_for()` with 180s timeout per task

**Root Cause** (CONFIRMED):
LiteLLM's logging worker has a race condition between task cancellation and logging completion:

1. **Our code** (`research/deep_research.py:427-433`):
   ```python
   results = await asyncio.gather(*[
       asyncio.wait_for(
           self._execute_task_with_retry(task),
           timeout=180  # 3-minute timeout
       )
       for task in batch
   ], return_exceptions=True)
   ```

2. **LiteLLM's logging worker** (`.venv/.../logging_worker.py:68-73`):
   ```python
   await asyncio.wait_for(
       task["context"].run(asyncio.create_task, task["coroutine"]),
       timeout=self.timeout  # 20 seconds
   )
   ```

3. **The race**:
   - When our 180s timeout fires → parent task gets cancelled → `CancelledError`
   - LiteLLM's logging worker is still processing the logging coroutine
   - The `CancelledError` propagates to logging worker's `asyncio.wait_for()`
   - This causes `TimeoutError` in logging worker exception handler (line 73)

**Why it's harmless**:
- LiteLLM logging worker catches and logs the exception (line 72-73)
- Exception handler uses `pass` - no crash, just error log
- Task cancellation is handled properly (line 76: `task_done()`)
- Research continues normally

**Impact**:
- **Functional**: None - logging is best-effort by design
- **Logs**: Scary-looking stack traces clutter error output
- **Debugging**: Makes real errors harder to spot in logs

**Tested Solutions**:
1. ✓ **Disable telemetry**: `litellm.telemetry = False` - Still occurs
2. ✓ **Suppress debug**: `litellm.suppress_debug_info = True` - Still occurs
3. ✗ **Suppress logging worker errors** - No config option exists
4. ✗ **Increase timeout** - Would slow down research unnecessarily

**Available Fixes**:

**Option 1: Suppress LiteLLM logging errors** (Easiest)
```python
# In llm_utils.py or research/deep_research.py
import logging
logging.getLogger('LiteLLM').setLevel(logging.CRITICAL)  # Only show critical errors
```
**Pros**: Simple, one-line fix
**Cons**: Might hide real LiteLLM errors

**Option 2: Increase logging worker timeout** (Not recommended)
```python
# Before any LiteLLM calls
import litellm
litellm.GLOBAL_LOGGING_WORKER.timeout = 300  # Match our task timeout
```
**Pros**: Prevents timeout race
**Cons**: Logging worker could block for 5 minutes (bad design)

**Option 3: Disable async logging callbacks** (Nuclear option)
```python
litellm.telemetry = False
litellm.turn_off_message_logging = True
```
**Pros**: Completely prevents logging worker from running
**Cons**: Lose all LiteLLM telemetry/logging features

**Option 4: Wait for LiteLLM fix** (Long-term)
- File issue on LiteLLM GitHub
- Request better cancellation handling in logging worker
- Upgrade when fixed

**Recommended Fix**: Option 1 (suppress LiteLLM logging errors)
- Minimal code change
- Preserves functionality
- Cleans up logs
- Can be reverted easily if needed

**Implementation Applied**:
```python
# llm_utils.py lines 29-33
# Suppress LiteLLM's async logging worker timeout errors
# These occur when our task timeouts cancel tasks before LiteLLM's logging completes
# This is harmless (logging is best-effort) but clutters error logs
logging.getLogger('LiteLLM').setLevel(logging.CRITICAL)
```

**Verification**:
```bash
$ python3 -c "import llm_utils; import logging; print(logging.getLogger('LiteLLM').level)"
50  # CRITICAL level (suppresses ERROR logs)
```

**Result**:
- ✅ LiteLLM ERROR logs suppressed
- ✅ Log output cleaned up
- ✅ Functionality preserved
- ✅ CRITICAL errors (if any) still shown

**Files Modified**:
- `llm_utils.py:29-33` (fix applied)
- `research/deep_research.py:427-433` (our timeout logic - unchanged)
- `.venv/lib/python3.12/site-packages/litellm/litellm_core_utils/logging_worker.py:68-73` (LiteLLM race condition - unchanged)

---

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

### SAM.gov Integration - Search Execution Failure
**Discovered**: 2025-10-21
**Resolved**: 2025-11-20 (Phase 4/5 implementation)

**Original Issue**: All SAM.gov searches returning 0 results with 0ms response time

**Solution**: Fixed during Phase 4/5 implementation - likely related to config integration and async improvements

**Verification** (2025-11-20): Test query returned 3 results successfully

---

### Hypothesis Execution Quality Bugs - Filtering and Logging
**Discovered**: 2025-11-20 (Codebase audit)
**Resolved**: 2025-11-20 (Commit 2cdee01)

**Original Issues**:
1. **Bug #1**: Hypothesis results bypassing relevance filtering entirely
   - Symptom: DVIDS returned 50 junk results (Guantanamo Bay military ops) for "Cuba sanctions" query
   - Root cause: `_execute_hypothesis()` went directly from source → deduplication → accumulation (no filtering)
   - Impact: Off-topic results polluting final reports

2. **Bug #2**: Hypothesis query generation reasoning not logged
   - Symptom: Query "Cuba sanctions Congress" appeared with no LLM reasoning explaining why
   - Root cause: Used `logging.info()` instead of `self.logger.log_hypothesis_query_generation()`
   - Impact: Cannot debug why LLM chose generic queries that flood results

3. **Bug #3**: No structured logging for hypothesis query decisions
   - Symptom: Missing `hypothesis_query_generation` action_type in execution_log.jsonl
   - Root cause: ExecutionLogger missing the log method entirely
   - Impact: Incomplete audit trail, can't trace LLM decision-making

**Solution**:
1. Added per-hypothesis relevance filtering (lines 1449-1472 in deep_research.py)
   - Calls `_validate_result_relevance()` after all hypothesis searches complete
   - Filters results before deduplication using same LLM evaluation as main task
   - Prints filtering decisions to stdout and logs to execution_log.jsonl

2. Added structured logging for query generation (lines 1349-1364 in deep_research.py)
   - Replaced `logging.info()` with `self.logger.log_hypothesis_query_generation()`
   - Logs to both stdout (real-time visibility) and execution_log.jsonl (audit trail)
   - Captures query + reasoning for every hypothesis-source pair

3. Added `log_hypothesis_query_generation()` method (lines 402-425 in execution_logger.py)
   - New action_type: "hypothesis_query_generation"
   - Schema: task_id, hypothesis_id, source_name, query, reasoning

**Verification**:
- Validation tests passed: log method exists and callable
- Filtering integration verified: _validate_result_relevance callable on hypothesis results
- Next research run will show: "🔍 Validating relevance of X hypothesis results..." + filtering decisions

**Files Modified**:
- `research/deep_research.py` (added filtering logic + structured logging)
- `research/execution_logger.py` (added log method)
- `CLAUDE.md` (added multi-agent architecture diagram)

**Expected Impact**:
- DVIDS junk results will be rejected at hypothesis level
- Can debug query generation decisions via execution_log.jsonl
- Full observability into hypothesis execution pipeline

---

### Configuration Hardcoding - No Centralized Config System
**Discovered**: 2025-11-02
**Resolved**: 2025-11-20 (Phase 4/5 implementation)

**Original Issue**: Critical configuration values hardcoded in Python files instead of centralized config

**Solution**: deep_research.py now reads from config.yaml for all settings (max_tasks, timeouts, etc.)

**Verification**: Lines 163-170 in research/deep_research.py show full config integration with fallbacks

**Files Modified**:
- `research/deep_research.py` (lines 163-170: config loading)
- `config_default.yaml` (comprehensive configuration)

---


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

**Last Updated**: 2025-11-20
