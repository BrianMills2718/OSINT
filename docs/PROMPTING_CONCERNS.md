# Prompting Concerns - Potential LLM Execution Issues

**Created**: 2025-12-05
**Status**: ✅ E2E Validated (2025-12-05)
**Purpose**: Track cases where prompts are correctly designed but LLM may not be following guidance

---

## E2E Test Results Summary (2025-12-05)

**Query**: "Compare federal AI and cybersecurity contracts awarded to Palantir vs Anduril in 2024. Which company is winning more defense technology work?"

**Test Duration**: ~54 minutes (note: --max-time 300s not enforced - potential bug)

### Key Metrics
| Metric | Count | Status |
|--------|-------|--------|
| Goals Completed | 176 | ✅ Excellent |
| Synthesis Events | 35 | ✅ Synthesis IS happening |
| Cross-Branch Evidence Selection | 5 | ✅ ANALYZE being used |
| Filter Decisions | 78 | ✅ Active filtering |
| Entities Extracted | 406 | ✅ Rich entity graph |
| Relationships Discovered | 1,056 | ✅ Comprehensive connections |

### Concerns Status After E2E Test
- **Concern #1 (Decomposition)**: ✅ RESOLVED - Synthesis goals ARE being created
- **Concern #2 (Filter Overlap)**: ⚠️ INCONCLUSIVE - Need to review specific filter decisions
- **Concern #3 (Early Achievement)**: ✅ RESOLVED - Synthesis events appear throughout
- **Concern #4 (No ANALYZE)**: ✅ RESOLVED - 5 `global_evidence_selection` events observed

### Notable Findings
The E2E test discovered significant journalistic leads:
- **Palantir-Anduril AI Consortium** - Major news story about joint consortium
- **Palmer Luckey FEC contributions** to Trump 47 Committee, RNC
- **Palantir lawsuit** against former engineers (Percepta AI)
- **ROADRUNNER, ANVIL, QUASAR** - Anduril product portfolio
- **MAVEN Smart System**, **Army Vantage** - Palantir contracts
- Connections to **OpenAI, SpaceX, Scale AI, Anthropic** in DoD context

### New Bug Found
**HTTP Code Extraction Issue**: SAM.gov and CourtListener returning `HTTP 0` instead of actual status codes (500, 403). This causes ErrorClassifier to misclassify as UNKNOWN instead of SERVER_ERROR/AUTHENTICATION.

---

## Overview

These are potential issues where the prompt engineering is sound, but the LLM's actual behavior may not match the intended guidance. Each requires E2E testing to verify if it's a real problem.

---

## Concern #1: Decomposition Not Creating Synthesis Goals

**Prompt**: `prompts/recursive_agent/goal_decomposition.j2`
**Status**: ⚠️ Unverified - Needs E2E test with comparative query

### What the Prompt Says (Lines 64-71)
```
DEPENDENT goals (dependencies: [0, 1, ...]):
- COMPARATIVE analysis: "Compare X vs Y" requires both X and Y data first
  Example: Goal 0: "Find Palantir contracts", Goal 1: "Find Anduril contracts",
           Goal 2 (depends on [0,1]): "Compare contract portfolios and identify competitive positioning"

- SYNTHESIS/INTEGRATION: Combining findings from multiple sub-goals
  Example: Goal 0: "Government contracts", Goal 1: "Legal issues",
           Goal 2 (depends on [0,1]): "Identify patterns between contract awards and legal problems"
```

### What May Be Happening
- LLM decomposes "Compare X vs Y" into only "Get X" + "Get Y" without creating a synthesis goal
- The `raw_dependencies` array in execution logs may be empty even for comparative queries
- Research completes after data collection without actual comparison/synthesis

### How to Verify
1. Run E2E test with explicit comparative query: "Compare Palantir and Anduril defense contracts"
2. Check execution_log.jsonl for `decomposition` events
3. Look for `raw_dependencies` field - should have Goal 2 depending on [0, 1]
4. Verify a synthesis goal exists (not just data collection goals)

### Potential Prompt Improvements (If Verified)
- Add more explicit examples of synthesis goals
- Make the "CRITICAL" guidance more prominent
- Add negative examples showing what NOT to do
- Consider adding a post-decomposition validation step

---

## Concern #2: Filter Passing Irrelevant Results (Keyword Overlap)

**Prompt**: `prompts/recursive_agent/result_filtering.j2`
**Status**: ⚠️ Unverified - Single incident reported, may be isolated

### What the Prompt Says (Lines 23-24)
```
- Keyword overlap alone is not relevance. Results about different entities
  that happen to share common terms are not relevant.
- Be thoughtful about what "relevant" means in the context of the specific
  goal and original objective.
```

### What Was Reported
- Goal: "Find key executives of Anduril Industries Inc."
- Filter passed: "Consumer Reports executive director Sara Enright..."
- Reasoning: Both mention "executive" → LLM interpreted as relevant

### Current Assessment
The prompt explicitly says keyword overlap is NOT sufficient. This may be:
1. An isolated LLM judgment error (not systemic)
2. A case where the LLM's reasoning was actually different
3. A real pattern that needs stronger prompt language

### How to Verify
1. Run E2E test with company-specific executive query
2. Review filter reasoning in execution logs
3. Check if pattern repeats or was isolated incident

### Potential Prompt Improvements (If Verified)
- Add explicit company-matching requirement for company-specific goals
- Include negative examples: "Consumer Reports executives" is NOT relevant to "Anduril executives"
- Strengthen the "different entities" language

---

## Concern #3: Achievement Declared Before Synthesis Completes

**Prompt**: `prompts/recursive_agent/achievement_check.j2`
**Status**: ⚠️ Unverified - Needs E2E test

### What the Prompt Says
```
Has this goal been SUFFICIENTLY achieved to stop pursuing more sub-goals?

Consider:
- Do we have enough evidence to answer the goal?
- Are there obvious critical gaps?
- Is continuing likely to add significant new value?
```

### What May Be Happening
- For comparative queries, system declares "achieved" after collecting data
- Synthesis goal never executes because parent goal is marked complete
- Result: "Compare X vs Y" returns data about X and Y but no actual comparison

### How to Verify
1. Run comparative E2E test
2. Check achievement_check events in execution log
3. Verify if synthesis goals execute or are skipped

### Potential Prompt Improvements (If Verified)
- Add check: "For comparative/synthesis goals, has the actual comparison been performed?"
- Include guidance that data collection alone doesn't satisfy comparative goals
- Add explicit check for dependent goals completion

---

## Concern #4: ANALYZE Action Never Chosen

**Prompt**: `prompts/recursive_agent/goal_assessment.j2`
**Status**: ⚠️ Documented in DAG_ANALYSIS_INVESTIGATION.md

### What the Prompt Offers
Actions available: API_CALL, WEB_SEARCH, ANALYZE, DECOMPOSE

### What May Be Happening
- LLM consistently chooses API_CALL and WEB_SEARCH
- ANALYZE action (which uses cross-branch evidence) rarely/never selected
- Global evidence index not being utilized

### Evidence from Previous Investigation
- DAG test showed 0 ANALYZE actions, 59 API_CALL, 9 WEB_SEARCH
- LLM correctly prioritized data collection for investigative query
- ANALYZE may only be appropriate for synthesis/reasoning queries

### How to Verify
1. Run E2E test with analysis-focused query: "What patterns emerge from federal AI spending?"
2. Check assessment events for action selection
3. Count ANALYZE vs other actions

### Potential Prompt Improvements (If Verified)
- Provide clearer guidance on when ANALYZE is appropriate
- Add examples of queries that should trigger ANALYZE
- Consider making ANALYZE more prominent for synthesis goals

---

## E2E Test Recommendations

### Test Query Options (Journalistic Significance)

1. **Comparative Investigation**:
   "Compare federal contracts awarded to Palantir vs Anduril in 2024 - which company is winning more defense AI work?"

2. **Pattern Analysis**:
   "Investigate the relationship between defense contractor lobbying spending and contract awards in 2024"

3. **Executive/Entity Focus**:
   "Find key executives and board members of major defense AI contractors and their government connections"

4. **Multi-Source Synthesis**:
   "What do federal contracts, court records, and news reports reveal about SpaceX's government relationship?"

### What to Check in Results

1. **Decomposition Quality**:
   - Does it create synthesis goals with dependencies?
   - Are comparative goals properly structured?

2. **Filter Quality**:
   - Are irrelevant results being passed?
   - Is the reasoning sound?

3. **Achievement Timing**:
   - Does synthesis execute before achievement?
   - Are all dependent goals completing?

4. **Action Selection**:
   - Is ANALYZE being chosen when appropriate?
   - Is evidence being shared across branches?

---

## Monitoring Checklist

After each E2E test, check:

- [ ] `decomposition` events have `raw_dependencies` populated for comparative goals
- [ ] `filter_results` events show semantic reasoning (not just keyword matching)
- [ ] `achievement_check` events occur AFTER synthesis goals complete
- [ ] `global_evidence_selection` events appear (if ANALYZE chosen)
- [ ] Final report contains actual analysis (not just data summaries)

---

## Resolution Status

| Concern | Verified? | Action Taken | Date |
|---------|-----------|--------------|------|
| #1 Decomposition | ✅ Not an issue | Synthesis goals created (35 events) | 2025-12-05 |
| #2 Filter Overlap | ⚠️ Inconclusive | Need targeted test | - |
| #3 Early Achievement | ✅ Not an issue | Synthesis throughout execution | 2025-12-05 |
| #4 No ANALYZE | ✅ Not an issue | 5 global_evidence_selection events | 2025-12-05 |

### New Issues Discovered

| Issue | Severity | Description | Date | Status |
|-------|----------|-------------|------|--------|
| HTTP Code Extraction | P1 | SAM.gov/CourtListener return HTTP 0 | 2025-12-05 | ✅ FIXED |
| max_time not enforced | P2 | 300s limit ignored, ran 54+ minutes | 2025-12-05 | ✅ FIXED (CLI alias) |

### Fixes Applied (2025-12-05)

**HTTP Code Extraction Bug (P1)**:
- **Root Cause**: When `e.response` was None, integrations set `http_code=0` but error messages still contained the actual code (e.g., "500 Server Error")
- **Fix 1**: ErrorClassifier now treats `http_code=0` as None and extracts HTTP code from error message text
- **Fix 2**: Added `_extract_http_code_from_message()` method that parses patterns like "500 Server Error", "429 Too Many Requests", "Forbidden"
- **Fix 3**: CourtListener integration now passes `http_code=None` instead of `http_code=0` when `e.response` is None
- **Files**: `core/error_classifier.py` (+65 lines), `integrations/legal/courtlistener_integration.py`
- **Validation**: All 30 E2E error handling tests pass, manual verification with test cases

**max_time Not Enforced (P2)**:
- **Root Cause**: Not a bug - test was run with `--max-time 300` but CLI only accepted `--max-time-minutes`
- **Fix**: Added `--max-time` alias for `--max-time-minutes` for better usability
- **File**: `run_research_cli.py`
- **Note**: Time enforcement logic in recursive_agent.py was already correct (checks at iteration start and before each follow-up goal)

---

## Related Documentation

- `docs/DAG_ANALYSIS_INVESTIGATION.md` - Full DAG infrastructure analysis
- `docs/ERROR_HANDLING_ARCHITECTURE.md` - Error classification system
- `CLAUDE.md` - Current task tracking and P0 bugs list
- `STATUS.md` - Component status and recent updates
