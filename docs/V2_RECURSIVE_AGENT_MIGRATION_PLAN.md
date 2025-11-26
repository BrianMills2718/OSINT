# V2 Recursive Agent Migration Plan

**Created**: 2025-11-26
**Status**: In Progress
**Current Phase**: Phase 2 (CLI Entry Point)

---

## Overview

Migrate from v1 research system (`research/deep_research.py`, 4,392 lines) to v2 recursive agent (`research/recursive_agent.py`, ~1,200 lines).

### Why v2?

| Aspect | v1 | v2 |
|--------|----|----|
| **Architecture** | Fixed 5-phase pipeline | Single recursive abstraction |
| **Depth** | Fixed (task → hypothesis → query) | Variable (LLM decides) |
| **Complexity** | 4,392 lines, many special cases | ~1,200 lines, unified pattern |
| **Context** | Lost between phases | Full context at every level |
| **Decisions** | Hardcoded hierarchy | LLM-driven assessment |

---

## Migration Phases

### Phase 1: Validation ✅ COMPLETE
**Goal**: Confirm v2 works correctly with bug fixes

**Tasks**:
- [x] Build v2 recursive agent core (`research/recursive_agent.py`)
- [x] Fix 5 bugs from code review (commit 4fb5138)
  - [x] Status typo (COMPLETED → FAILED when no evidence)
  - [x] Wire up cost tracking
  - [x] Add concurrency semaphore
  - [x] Propagate child failures
  - [x] Remove unused import
- [x] Run validation test (simple query) - 20 results, status completed
- [x] Run validation test (complex query with decomposition) - 59 results, 3 sub-goals, depth 3
- [x] Verify cost tracking works - Fixed cost propagation bug (commit 1b95747), $0.0002 tracked

**Validation Results** (2025-11-26):
- **Simple query**: "Find federal AI contracts awarded in 2024" → 20 evidence pieces, 9.1s
- **Complex query**: "Palantir government contracts, lobbying, controversies" → 59 evidence, 3 sub-goals decomposed
- **Cost tracking**: $0.0002 (assessment LLM call), propagated correctly through result chain

**Success Criteria**: ✅ ALL MET
- ✅ Simple query returns results (20 pieces)
- ✅ Complex query triggers decomposition (3 sub-goals at depth 1)
- ✅ Cost is tracked (non-zero, $0.0002)
- ✅ Failed sub-goals propagate correctly (tested via code review)

---

### Phase 2: CLI Entry Point (Current)
**Goal**: Create user-facing CLI for v2

**Tasks**:
- [ ] Create `apps/recursive_research.py` CLI wrapper
- [ ] Support same arguments as v1 (`--max-tasks`, `--max-time-minutes`, etc.)
- [ ] Map v1 args to v2 Constraints
- [ ] Add output directory structure (same as v1)
- [ ] Test CLI end-to-end

**Success Criteria**:
- `python3 apps/recursive_research.py "query"` works
- Output saved to `data/research_v2/`
- Arguments respected

---

### Phase 3: Feature Parity
**Goal**: Add v1 features missing from v2

**Tasks**:
- [ ] **Query reformulation on API error** - Port `_reformulate_on_api_error()` pattern
- [ ] **Per-source query generation prompts** - Use existing Jinja2 templates
- [ ] **Result relevance filtering** - Add LLM filter step after API calls
- [ ] **Temporal context injection** - Add current_date to prompts
- [ ] **Execution logging** - Match v1 event types for debugging
- [ ] **Report generation** - Improve markdown output format

**Feature Comparison**:
| Feature | v1 | v2 |
|---------|----|----|
| Task decomposition | Yes | Yes (as goal decomposition) |
| Hypothesis generation | Yes | Yes (as sub-goal creation) |
| Query generation | Per-source prompts | Generic (needs enhancement) |
| Query reformulation | Yes | No (needs port) |
| Relevance filtering | Yes | No (needs port) |
| Temporal context | Yes | No (needs port) |
| Cost tracking | Yes | Yes (just wired up) |
| Execution logging | Rich events | Basic events |
| Report synthesis | Detailed | Basic |

**Success Criteria**:
- Same query produces similar quality results on v1 and v2
- API errors trigger reformulation
- Results are relevance-filtered

---

### Phase 4: Side-by-Side Comparison
**Goal**: Validate v2 produces equivalent or better results

**Tasks**:
- [ ] Create comparison test harness
- [ ] Run 5 test queries on both v1 and v2
- [ ] Compare: result count, quality, time, cost
- [ ] Document any v2 advantages/disadvantages
- [ ] Identify remaining gaps

**Test Queries**:
1. Simple: "Find federal AI contracts awarded in 2024"
2. Company: "Palantir government contracts and controversies"
3. Topic: "DoD cybersecurity spending trends"
4. Multi-source: "Federal contractor lobbying activities"
5. Complex: "Investigative report on defense AI programs"

**Success Criteria**:
- v2 results are >= v1 quality
- v2 is faster or comparable
- v2 cost is lower or comparable
- No critical gaps remain

---

### Phase 5: Full Migration
**Goal**: Replace v1 with v2 as primary system

**Tasks**:
- [ ] Update `apps/ai_research.py` to use v2 (or create v2 variant)
- [ ] Update Streamlit UI to support v2
- [ ] Archive v1 code (`research/deep_research.py` → archive)
- [ ] Update documentation (README, CLAUDE.md, STATUS.md)
- [ ] Create migration notes for any breaking changes

**Success Criteria**:
- v2 is default research system
- v1 archived but accessible
- All documentation updated
- No user-facing regressions

---

## Architecture Reference

### v2 Core Loop (Single Abstraction)

```
pursue_goal(goal, context):
    1. Check constraints (depth, time, cost, goals)
    2. Detect cycles
    3. Assess: directly executable or decompose?
    4. If executable → execute action
    5. If decompose → create sub-goals → pursue each
    6. Synthesize results
    7. Return GoalResult
```

### Key Files

| File | Purpose |
|------|---------|
| `research/recursive_agent.py` | v2 core implementation |
| `research/deep_research.py` | v1 implementation (to be archived) |
| `docs/RECURSIVE_AGENT_ARCHITECTURE.md` | Architecture documentation |
| `apps/ai_research.py` | Current CLI (v1) |
| `apps/recursive_research.py` | Future CLI (v2) - to be created |

---

## Risk Mitigation

1. **v2 produces worse results**: Keep v1 available, run comparison before migration
2. **Missing features break workflows**: Complete Phase 3 before Phase 5
3. **Integration complexity**: v2 uses same registry/integrations as v1
4. **Cost overruns**: Concurrency limit and cost tracking added

---

## Timeline

No fixed deadlines - proceed phase by phase, validate each before moving on.

**Completed**: Phase 1 - Validation (2025-11-26)
**Current**: Phase 2 - CLI Entry Point
