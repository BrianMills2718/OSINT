# DAG & ANALYZE Action Investigation
**Date**: 2025-11-30
**Branch**: feature/enable-dag-analysis
**Purpose**: Thoroughly investigate current state before implementing DAG/ANALYZE improvements

---

## Executive Summary

**Discovery**: DAG infrastructure is 90% complete but unused. The LLM doesn't declare dependencies, so all sub-goals execute in parallel.

**Goal**: Enable the existing DAG infrastructure to:
1. Make LLM declare explicit dependencies between sub-goals
2. Force dependent goals to choose ANALYZE (synthesize evidence from dependencies)
3. Validate cross-branch evidence sharing in real usage

---

## Current State Analysis

### ✅ What EXISTS (Already Implemented)

**1. SubGoal Data Structure** (line 287):
```python
@dataclass
class SubGoal:
    description: str
    rationale: str
    dependencies: List[int] = field(default_factory=list)  # ← Field exists!
    estimated_complexity: str = "moderate"
```

**2. Topological Sort** (lines 2390-2420):
- Full implementation of dependency-based grouping
- Returns execution groups where goals in same group run in parallel
- Waits for dependencies before executing next group
- Handles circular dependencies gracefully

**3. Execution Uses It** (line 914):
```python
goal_groups = self._group_by_dependency(sub_goals)
for group in goal_groups:
    # Run independent goals in parallel
    group_results = await asyncio.gather(*group_tasks)
```

**4. LLM Parsing** (lines 1500-1516):
- Reads `dependencies` field from LLM response
- Sanitizes to ensure integers
- Creates SubGoal objects with dependencies

**5. Prompt Asks for Dependencies** (line 1480):
```json
{
  "dependencies": [0, 1],  // Indices of sub-goals this depends on
}
```

### ❌ What's MISSING

**1. LLM Doesn't Declare Dependencies**
- Evidence: Execution log shows all sub-goals logged as strings only
- Hypothesis: LLM returns empty `dependencies: []` for all goals
- Result: All goals grouped into single parallel batch

**2. No Logging of Dependency Execution**
- Can't see which groups executed
- Can't see which goals waited for dependencies
- Can't validate DAG is working

**3. Weak Prompt Guidance**
- Prompt asks for dependencies but doesn't explain WHEN to use them
- No examples of comparative/analytical goals
- Missing: "If goal C compares A vs B → dependencies: [0, 1]"

**4. ANALYZE Action Never Chosen**
- 0 ANALYZE actions in 608-evidence E2E test
- LLM always chooses API_CALL or WEB_SEARCH
- assessment() prompt doesn't guide toward ANALYZE for synthesis goals

---

## Key Findings from Investigation

### Finding 1: Logging is Lossy
**File**: `research/recursive_agent.py`, line 892
```python
self.logger.log_goal_decomposed(
    goal, context.depth, parent_goal,
    sub_goals=[sg.description for sg in sub_goals],  # ← Only description!
    rationale=assessment.decomposition_rationale
)
```

**Impact**: Can't verify if LLM declared dependencies - they're not logged!

**Solution**: Log full SubGoal objects including dependencies field.

---

### Finding 2: DAG Works But Isn't Tested
**Evidence**:
- _group_by_dependency() exists and is called
- Topological sort is correct
- BUT: We have no test that validates multi-group execution

**Uncertainty**: Does it actually work end-to-end?

**Risk**: Changes to decomposition might break untested DAG code.

---

### Finding 3: Two Separate Problems

**Problem A**: LLM doesn't declare dependencies
**Solution**: Enhance decomposition prompt

**Problem B**: LLM doesn't choose ANALYZE
**Solution**: Enhance assessment prompt + add sibling awareness

**These are INDEPENDENT** - can fix separately or together.

---

## Uncertainties & Risks

### Uncertainties

1. **❓ Does LLM currently return dependencies?**
   - We don't know if it returns `[]` or actual indices
   - Logging doesn't capture this
   - **Need**: Add debug logging to _decompose()

2. **❓ Will Gemini consistently declare dependencies?**
   - Different from assessment (which it does well)
   - Requires understanding of goal relationships
   - **Need**: Test with explicit examples

3. **❓ How does LLM decide dependency indices?**
   - If sub-goals are reordered, indices break
   - Need to ensure stable ordering
   - **Risk**: Off-by-one errors

4. **❓ What if LLM declares circular dependencies?**
   - Code handles it (line 2412-2414) by grouping all
   - But this defeats the purpose
   - **Need**: Prompt guidance to avoid cycles

5. **❓ Will dependent goals automatically choose ANALYZE?**
   - Or do we need explicit guidance?
   - **Need**: Test if showing sibling results is enough

### Risks

1. **🔴 High: Breaking Existing Behavior**
   - Changes to decomposition prompt might reduce quality
   - LLM might over-decompose or under-decompose
   - **Mitigation**: A/B test with current vs new prompts

2. **🟡 Medium: Dependency Hell**
   - LLM might create overly complex dependency graphs
   - Could serialize execution (defeating parallelism)
   - **Mitigation**: Limit max dependencies per goal (e.g., 3)

3. **🟡 Medium: Increased LLM Costs**
   - More complex prompts = more tokens
   - Dependencies require reasoning = slower
   - **Mitigation**: Measure cost before/after

4. **🟢 Low: Backwards Compatibility**
   - Old code expects descriptions as strings in logs
   - Changing log format might break analysis scripts
   - **Mitigation**: Keep backward-compatible log format

5. **🟢 Low: Testing Coverage**
   - DAG execution not covered by tests
   - Changes could break silently
   - **Mitigation**: Add DAG-specific integration test

---

## Investigation Tasks

### ✅ Completed
- [x] Find SubGoal dataclass definition
- [x] Find _group_by_dependency implementation
- [x] Verify it's being called
- [x] Check LLM response parsing
- [x] Examine execution log format
- [x] Review prompt that asks for dependencies

### ⏳ In Progress
- [ ] Add debug logging to capture actual LLM responses
- [ ] Test _group_by_dependency with sample inputs
- [ ] Document all code touchpoints

### 📋 Pending
- [ ] Create test cases for DAG execution
- [ ] Design enhanced decomposition prompt
- [ ] Design enhanced assessment prompt
- [ ] Identify backward compatibility issues
- [ ] Plan rollout strategy (feature flag?)

---

## Questions to Answer Before Implementation

1. **Scope**: Option 1 (sibling awareness) or Option 2 (enable DAG) or both?
2. **Testing**: How do we validate DAG works without breaking existing tests?
3. **Rollback**: Can we feature-flag this for easy disable?
4. **Metrics**: How do we measure success? (ANALYZE action count? Dependency usage?)
5. **Cost**: What's acceptable LLM cost increase for better quality?

---

## Next Steps

1. **Add comprehensive logging**
   - Log full SubGoal objects (including dependencies)
   - Log dependency groups during execution
   - Log LLM's raw JSON response

2. **Create test suite**
   - Unit test: _group_by_dependency with various dependency graphs
   - Integration test: Force dependencies and verify execution order
   - E2E test: Query designed to trigger dependencies

3. **Design prompts**
   - Decomposition: When and how to declare dependencies
   - Assessment: When to choose ANALYZE vs API_CALL
   - Add concrete examples to both

4. **Implement incrementally**
   - Step 1: Logging only (no behavior change)
   - Step 2: Enhanced prompts (measure impact)
   - Step 3: Validation and refinement

5. **Document thoroughly**
   - Update CLAUDE.md with new behavior
   - Update STATUS.md with validation results
   - Create DAG_USAGE_GUIDE.md for future reference

---

## Files to Modify

| File | Purpose | Lines | Risk |
|------|---------|-------|------|
| research/recursive_agent.py | Add logging, enhance prompts | ~100 | Medium |
| research/execution_logger.py | Log dependency info | ~20 | Low |
| tests/test_dag_execution.py | New test file | ~150 | N/A (new) |
| CLAUDE.md | Document new behavior | ~50 | Low |
| STATUS.md | Update with validation | ~30 | Low |

**Total estimated changes**: ~350 lines across 5 files

---

## Success Criteria

Before merging to master, we MUST demonstrate:

1. ✅ LLM declares dependencies for comparative goals (logged and verified)
2. ✅ _group_by_dependency correctly orders execution (test coverage)
3. ✅ Dependent goals wait for dependencies to complete (timing logs)
4. ✅ At least 1 ANALYZE action in comparative E2E test (not 0)
5. ✅ Cross-branch evidence sharing validated (global_evidence_selection events > 0)
6. ✅ No regression in data collection quality (same or more evidence)
7. ✅ Cost increase < 20% for equivalent queries
8. ✅ All existing tests still pass

---

## Timeline Estimate

- **Investigation & Planning**: 2-3 hours ✅ (this document)
- **Logging Implementation**: 1-2 hours
- **Test Suite Creation**: 2-3 hours
- **Prompt Engineering**: 2-4 hours (iterative)
- **E2E Validation**: 1-2 hours
- **Documentation**: 1-2 hours
- **Buffer for Issues**: 2-3 hours

**Total**: 11-19 hours (1.5-2.5 days of focused work)

---

## Conclusion

The DAG infrastructure is **already 90% built**. We're not building new architecture - we're **enabling existing code** through better LLM guidance.

**Key Insight**: This is primarily a **prompt engineering challenge**, not a systems engineering challenge.

**Recommendation**: Proceed with caution, measure everything, validate thoroughly.
