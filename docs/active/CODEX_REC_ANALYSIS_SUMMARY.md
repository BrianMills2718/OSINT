# Codex Recommendations - Analysis Summary

**Date**: 2025-11-13
**Status**: Ready for decision

---

## Recommendation Summary & Concerns

### ✅ #1: Increase `default_result_limit` from 10 → 20

**Action**: Change `config_default.yaml:59` + update `deep_research.py:585, 1084`

**Concerns**:
- ⚠️  **Brave Search already uses 20** (line 1084) - config change won't affect it
- ❓ **No evidence 10 is too low** - no documented quality issues
- 💡 **Better approach**: Add per-integration limits:
  ```yaml
  integration_limits:
    clearancejobs: 20
    usajobs: 100  # API supports 100/page
    brave_search: 20
    sam: 10  # Can be slow
  ```

**Decision**: ✅ APPROVE but use per-integration config approach

**Risk**: LOW | **Time**: 30 min | **Impact**: More results per source

---

### ⚠️  #2: Remove Hardcoded Entity Filter (lines 493-529)

**Action**: Delete META_TERMS_BLACKLIST + multi-task threshold, move filtering to LLM prompt

**What Gets Removed**:
1. Blacklist: `["cybersecurity", "job", "clearance", "polygraph", "federal government", ...]` (9 terms)
2. Multi-task threshold: Entities must appear in 2+ tasks (or only 1 task if that's all we have)

**Test Evidence** (from `test_polish_validation.py` - just completed):
- **Before filtering**: 25 entities extracted
- **After filtering**: 16 entities kept (9 filtered out - 36% reduction)
- **Sample filtered**: Likely meta-terms ("cybersecurity", "job", etc.)

**MAJOR CONCERNS**:

1. **🚨 Dual-Stage Architecture**: Current system has TWO filtering stages:
   - **Stage 1 (LLM)**: `_extract_entities()` at line 414 - already asks LLM to extract "important entities"
   - **Stage 2 (Python)**: Lines 493-529 - programmatic filter

   **Codex's proposal**: Move Stage 2 filtering into Stage 1 LLM prompt

   **Problem**: Stage 1 is **per-task** (runs 3 times in test), Stage 2 is **cross-task** (runs once at end)

   **Question**: How does LLM filter entities it hasn't seen yet? Multi-task confirmation requires seeing ALL tasks' entities.

2. **❓ Prompt Location Unclear**: Where does Codex want the filter prompt?
   - Option A: `prompts/deep_research/entity_extraction.j2` (per-task, can't do cross-task filtering)
   - Option B: New synthesis-time prompt (all entities at once, loses per-task context)

3. **⚠️  Losing Multi-Task Confirmation**: Current system filters entities appearing in only 1 of 3 tasks
   - **Value**: Reduces noise from task-specific jargon
   - **Example**: Task 1 extracts "INFOSEC" (appears 1x) vs "2210 Series" (appears 3x) → keep "2210 Series"
   - **LLM cannot replicate this** without seeing all tasks' entities together

4. **⚠️  Meta-Terms Are Contextual**: "cybersecurity" is generic in most contexts BUT valuable when paired:
   - ❌ Generic: "cybersecurity" alone
   - ✅ Specific: "IT Specialist (Cybersecurity)" - this is an official job title!

   Current code filters lowercase "cybersecurity" but test kept "IT Specialist (Cybersecurity)" - **working as intended**

**CRITICAL UNCERTAINTY**:
- **❓ Does Codex understand the two-stage architecture?**
- **❓ How to do cross-task confirmation via LLM?** (each extraction call sees only 1 task's results)

**Recommendation**: ❌ **DO NOT IMPLEMENT** without clarification from Codex

**Alternative**: Keep current filter but make blacklist configurable:
```yaml
entity_filtering:
  enabled: true
  meta_terms_blacklist:
    - "cybersecurity"  # Generic unless part of job title
    - "job"
    - "clearance"
  min_task_threshold: 2  # Appear in N tasks to be kept
```

---

### ✅ #3: Normalize Default Prompt (Remove Contractor Bias)

**Action**: Verify `test_gemini_deep_research.py` uses neutral prompt, keep `test_clearancejobs_contractor_focused.py` as-is

**Investigation**:
- `test_gemini_deep_research.py:46`: Uses `"What are federal cybersecurity job opportunities?"` ✅ NEUTRAL
- `test_clearancejobs_contractor_focused.py:37`: Uses contractor-specific query ✅ TEST-ONLY

**Finding**: ✅ **NO BIAS IN DEFAULT FLOW** - contractor query is test-specific

**Decision**: ✅ APPROVE (no changes needed, already correct)

**Risk**: NONE | **Time**: 0 min | **Impact**: Documentation clarity

---

### ⚠️  #4: Enable LLM Pagination Control (param_hints expansion)

**Action**: Extend `param_hints` from Reddit/USAJobs to Twitter, expose pagination knobs to LLM

**Current State**:
- ✅ Reddit: `time_filter` adjustable via `param_hints` (lines 1167-1171)
- ✅ USAJobs: `keywords` adjustable via `param_hints` (lines 1176-1180)
- ❌ Twitter: No `param_hints` support (but has `max_pages`, `search_type` internally)

**What Codex Wants**:
```python
# Twitter integration accepts param_hints
param_hints = {
    "search_type": "Top" | "Latest" | "People",
    "max_pages": 1-5
}
```

**Concerns**:

1. **❓ Benefit Unclear**: When would LLM choose "Top" vs "Latest"?
   - **Theory**: Retry attempts could try different strategies
   - **Reality**: No data showing this helps vs just reformulating query

2. **⚠️  Prompt Complexity**: LLM must understand Twitter-specific options
   - Adds ~50 lines to `query_reformulation` prompt
   - Risk: LLM confusion, invalid combinations

3. **⚠️  Limited Applicability**: Only helps when:
   - Same source selected on retry
   - Different pagination strategy would help
   - **Estimate**: ~20% of retries? (most retries use different sources or different query)

4. **❓ Twitter API Constraints**: Free tier has strict limits
   - Adding page control might not matter if we're rate-limited anyway

**Codex's Note**: "For sources without native paging (ClearanceJobs, Brave), note that we can't do 'next page' until we extend the scraper/API. (Just document that limitation for now.)"

**Recommendation**: ⏸️  **DEFER** - needs data to justify complexity

**Alternative**: Phase 0 instrumentation (measure how often retries use same source, document in logs)

---

## Summary Recommendations

| # | Recommendation | Decision | Effort | Risk |
|---|----------------|----------|--------|------|
| 1 | Increase result limits | ✅ APPROVE (with per-integration config) | 30 min | LOW |
| 2 | Remove entity filter | ❌ BLOCK (needs Codex clarification) | ? | HIGH |
| 3 | Normalize prompt | ✅ APPROVE (already correct) | 0 min | NONE |
| 4 | LLM pagination control | ⏸️  DEFER (needs data/justification) | 2 hours | MED |

---

## Questions for Codex

### Re: Recommendation #2 (Entity Filter)

1. **Architecture Question**: Current system has two-stage filtering:
   - Stage 1 (LLM, per-task): Extract entities from task results
   - Stage 2 (Python, cross-task): Filter meta-terms + require 2+ task appearances

   How do you propose replicating **cross-task confirmation** via LLM when each extraction call sees only one task's results?

2. **Prompt Location**: Where should entity filtering logic go?
   - A) `entity_extraction.j2` (per-task, can't do cross-task filtering)
   - B) New synthesis-time prompt (loses per-task result context)

3. **Evidence Request**: What quality problem is the hardcoded filter causing? Test shows 16/25 entities kept (reasonable signal-to-noise)

### Re: Recommendation #4 (Pagination)

1. **Use Case Clarity**: Can you provide example where `search_type: "Top"` vs `"Latest"` would improve results on retry?

2. **Data Request**: Do you have evidence that pagination hints outperform simple query reformulation?

---

## Implementation Order (If All Approved)

1. **#3** (0 min) - Document that default prompt is already neutral
2. **#1** (30 min) - Add per-integration result limits
3. **#4** (2 hours) - Add Twitter param_hints (if data justifies)
4. **#2** (blocked) - Needs design clarity from Codex

---

**END OF ANALYSIS**
