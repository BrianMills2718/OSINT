# Phase 5: Pure Qualitative Intelligence - Remove Quantitative Scores

**Branch**: `feature/phase5-pure-qualitative` (branched from Phase 4)
**Parent**: `feature/phase4-task-prioritization`
**Estimated Time**: 3-4 hours
**Status**: PLANNING
**Created**: 2025-11-20

---

## EXECUTIVE SUMMARY

**Goal**: Remove quantitative scores (coverage_score, incremental_gain_last) in favor of pure LLM qualitative intelligence

**Philosophy Alignment**:
- ❌ Derived metrics that LLM computes but system ignores
- ❌ Hardcoded thresholds that never trigger (95% coverage)
- ❌ Rule-based decisions (if score < 20% then stop)
- ✅ LLM natural language reasoning
- ✅ Manager sees context, not numbers
- ✅ Facts (counts) provided by system, not computed by LLM

---

## CURRENT PROBLEMS WITH QUANTITATIVE SCORES

### **Problem #1: coverage_score Is Useless**
- Threshold: 95% for skipping follow-ups
- Reality: ZERO tasks ever reach 95%
- **Effect**: Threshold never triggers, score does nothing

### **Problem #2: Scores Fluctuate Unpredictably**
- Task 1: 25% → 40% → 45% → 40% (went DOWN)
- After adding 50 NEW results, coverage decreased
- **Cause**: LLM recalibrates understanding of topic scope
- **Effect**: Unstable metric, can't optimize on it

### **Problem #3: Scores Don't Influence Decisions**
- Manager has coverage_score in data
- But Manager reasons from: gaps, results, context
- **Score is ignored** in actual decision-making

### **Problem #4: LLM Shouldn't Do Math**
```json
{"incremental_gain_last": 72.3}  // LLM computed 50/69
```
System already has: results_new=50, results_total=69
**Why ask LLM to calculate percentage?**

---

## WHAT TO REMOVE

### **From Coverage Assessment**:
```json
// REMOVE:
"coverage_score": 45,
"incremental_gain_last": 72.3,
"confidence": 85  // On decisions - rationale is enough

// KEEP:
"decision": "continue",
"rationale": "Strong policy coverage but missing humanitarian...",
"gaps_identified": ["humanitarian orgs", "Cuban govt"],

// AUTO-INJECT (system provides):
"facts": {
  "results_new": 50,
  "results_duplicate": 10,
  "entities_new": 5,
  "time_elapsed": 45
}
```

### **From Saturation Detection**:
```json
// REMOVE:
"recommended_additional_tasks": 3  // LLM suggests specific number

// KEEP:
"saturated": false,
"rationale": "Last 3 tasks 80-100% new results...",
"recommendation": "continue_full",  // Categorical, not numeric
"critical_gaps_remaining": ["humanitarian", "lobbying"]
```

### **From Config**:
```yaml
# REMOVE:
min_coverage_for_followups: 95  # Never used

# KEEP:
manager_agent.saturation_confidence_threshold: 70  # Used
```

---

## NEW SCHEMA DESIGN

### **Coverage Assessment (Per-Hypothesis)**

**Current** (quantitative):
```json
{
  "decision": "continue",
  "rationale": "...",
  "coverage_score": 45,
  "incremental_gain_last": 72.3,
  "gaps_identified": [...],
  "confidence": 85
}
```

**Phase 5** (qualitative):
```json
{
  "decision": "continue",
  "assessment": "After Hypothesis 2, we have strong economic impact coverage (50 new results from IMF, World Bank, academic sources). However, we're completely missing humanitarian organization perspectives (Amnesty, HRW, UN) and Cuban government official responses. These gaps are critical for balanced understanding. Continue to Hypothesis 3 which targets these angles.",
  "gaps_identified": [
    "Humanitarian organization perspectives (Amnesty, HRW, UN reports)",
    "Cuban government official responses and statements"
  ]
}

// System auto-injects (LLM never writes these):
{
  "facts": {
    "results_new": 50,
    "results_duplicate": 10,
    "entities_discovered": ["IMF", "World Bank", "WOLA", "Brookings", "CFR"],
    "entities_new": 5,
    "sources_used": ["Brave Search", "Twitter"],
    "time_elapsed_seconds": 45,
    "time_remaining_seconds": 555,
    "hypotheses_executed": 2,
    "hypotheses_remaining": 2
  }
}
```

**Key changes**:
1. `rationale` → `assessment` (more prose-friendly)
2. Remove coverage_score
3. Remove incremental_gain_last
4. Remove confidence
5. System injects all facts (LLM doesn't write them)

---

### **Saturation Assessment (Manager-Level)**

**Current**:
```json
{
  "saturated": false,
  "confidence": 85,
  "rationale": "...",
  "evidence": {
    "diminishing_returns": false,
    "coverage_completeness": false,
    "pending_queue_quality": "high",
    "topic_exhaustion": false
  },
  "recommendation": "continue_full",
  "recommended_additional_tasks": 3
}
```

**Phase 5**:
```json
{
  "saturated": false,
  "assessment": "After completing 6 tasks (140 results, 22 entities), we're still discovering new information efficiently. Last 3 tasks yielded 80%, 90%, 100% new results respectively - no diminishing returns yet. Pending queue contains 4 high-priority tasks (P1-P3) targeting critical gaps: humanitarian impact, business lobbying, and grassroots movements. Topic is NOT exhausted - continue full exploration.",
  "recommendation": "continue_full",
  "critical_gaps_remaining": [
    "Humanitarian impact on Cuban civilians",
    "US business lobbying efforts (agriculture, tech)",
    "Grassroots advocacy movements"
  ]
}

// System auto-injects:
{
  "facts": {
    "tasks_completed": 6,
    "total_results": 140,
    "total_entities": 22,
    "avg_new_results_last_3": 90,  // System calculates
    "pending_tasks_count": 4,
    "pending_priorities": [1, 2, 3, 4],
    "elapsed_minutes": 18
  }
}
```

**Key changes**:
1. Remove confidence (assessment prose is enough)
2. Remove evidence sub-object (folded into prose assessment)
3. Remove recommended_additional_tasks number
4. System calculates all averages/stats

---

## IMPLEMENTATION STEPS

### **Step 1: Update Coverage Assessment Schema** (1 hour)

**File**: `prompts/deep_research/coverage_assessment.j2`

**Changes**:
- Remove coverage_score field from schema
- Remove incremental_gain_last from schema
- Remove confidence from schema
- Rename rationale → assessment
- Add guidance: "Write 2-4 sentences explaining..."

**File**: `research/deep_research.py` `_assess_coverage()`

**Changes**:
- Update schema definition (remove fields)
- Auto-inject facts after LLM response
- Remove references to coverage_score in code

---

### **Step 2: Update Saturation Detection Schema** (1 hour)

**File**: `prompts/deep_research/saturation_detection.j2`

**Changes**:
- Remove evidence sub-object
- Remove recommended_additional_tasks
- Remove confidence
- Strengthen assessment prose guidance

**File**: `research/deep_research.py` `_is_saturated()`

**Changes**:
- Update schema
- Auto-inject facts (avg_new_results, pending_priorities)
- System calculates diminishing returns (don't ask LLM)

---

### **Step 3: Remove Coverage Threshold** (30 min)

**File**: `config_default.yaml`

**Remove**:
```yaml
min_coverage_for_followups: 95  # NEVER USED
```

**File**: `research/deep_research.py` `_should_create_follow_ups()`

**Remove**:
```python
# Lines 3177-3184 - coverage threshold check
if coverage_score >= 95:
    skip_follow_ups
```

**Replace with**: Always check gaps (LLM decides if follow-ups needed)

---

### **Step 4: Update Follow-Up Generation** (30 min)

**Currently**: Uses coverage_score to decide
**Phase 5**: Uses gaps only

**File**: `research/deep_research.py` `_create_follow_up_tasks()`

**Change**:
```python
# OLD:
coverage_score = latest_coverage.get("coverage_score", 0)
if coverage_score >= 95:
    return []

# NEW:
# Just get gaps, let LLM decide if follow-ups needed
gaps = get_all_gaps_from_coverage_decisions(task)
# LLM generates 0-N follow-ups based on gaps
```

---

### **Step 5: Update Manager Inputs** (30 min)

**Prioritization prompt**: Remove coverage_score references
**Saturation prompt**: Remove percentage-based guidance

**Both get**: Natural language summaries instead

---

### **Step 6: Testing** (30 min)

Test that:
- Coverage decisions still work (without scores)
- Saturation still detects (without percentages)
- Manager prioritization unaffected
- No crashes from missing fields

---

## AUTO-INJECTION ARCHITECTURE

**System calculates before LLM call**:
```python
# Before calling LLM for coverage assessment
facts = {
    "results_new": sum(run["delta_metrics"]["results_new"] for run in task.hypothesis_runs),
    "results_duplicate": sum(run["delta_metrics"]["results_duplicate"] for run in task.hypothesis_runs),
    "incremental_percentage": int(results_new / total * 100) if total > 0 else 0,
    "entities_new": len(new_entities),
    "entities_total": len(all_entities),
    "time_elapsed": int(time.time() - start_time),
    "time_remaining": max_time - time_elapsed
}

# LLM returns assessment + decision
llm_response = await llm_assess_coverage(prompt)

# System merges
final_result = {
    **llm_response,  # decision, assessment, gaps
    "facts": facts   # System-calculated
}
```

**Benefit**: LLM focuses on MEANING, system handles COUNTING

---

## EXPECTED OUTCOMES

**Simpler**:
- Fewer fields in schemas
- No percentage calculations in LLM
- No unused thresholds in config

**More Aligned**:
- Pure LLM intelligence for decisions
- No hardcoded rules (20%, 95%, etc.)
- Natural language > numeric scores

**More Stable**:
- Facts don't fluctuate (50 results = 50 results)
- Assessments can evolve (LLM recalibrates understanding)

---

## RISKS

**Risk #1: Parsing Complexity**
- Without coverage_score, how does follow-up generator know if coverage good?
- **Mitigation**: LLM explicitly states in assessment, or check gaps list length

**Risk #2: Backwards Compatibility**
- Old runs have coverage_score in metadata
- **Mitigation**: Phase 5 metadata just won't have it (additive change)

**Risk #3: Lost Signal**
- Maybe coverage_score conveys something assessment doesn't?
- **Mitigation**: Can always add back if needed

---

## BRANCH STRATEGY

**Recommended**:
```
master
  └─ feature/phase4-task-prioritization (Phase 4: Manager)
       └─ feature/phase5-pure-qualitative (Phase 5: Remove scores)
```

**Workflow**:
1. Phase 5 branches FROM Phase 4 (builds on manager architecture)
2. Implement Phase 5 aggressively (~3 hours)
3. When Cuba validation completes:
   - If Phase 4 good: Merge Phase 4 → master
   - If Phase 5 good: Merge Phase 5 → Phase 4, then Phase 4 → master
   - If issues: Iterate on branches

**Benefit**: Keep moving, don't block on validation

---

## READY TO PROCEED?

**Current status**:
- ✅ Phase 4 branch committed (11 commits, all clean)
- ✅ Logger bug fixed
- ⏳ Cuba validation running (~10-20 min remaining)

**Next**:
1. Create `feature/phase5-pure-qualitative` branch
2. Implement schema changes aggressively
3. Test while Cuba validation runs

**This is what you asked for - aggressive parallel development?**
