# Technical Debt Tracker

This file tracks deferred technical improvements that are not critical bugs but should be addressed for production hardening.

---

## Active Tech Debt

### 1. Global Evidence Index: Unbounded Memory Growth

**Component**: `research/recursive_agent.py` - ResearchRun dataclass (lines 85-99)

**Issue**:
The global evidence index (`ResearchRun.index` and `ResearchRun.evidence_store`) has no size limit and grows indefinitely during a research session.

**Current Impact**:
- **Low** for typical runs (50-100 evidence pieces)
- **Medium** for long sessions (500+ evidence)
- **High** for continuous operation (web API running 24/7)

**Why Deferred**:
Simple FIFO eviction (remove oldest entry) is too naive:
- Could discard valuable evidence that's still relevant
- No intelligence about evidence importance
- Doesn't account for evidence reuse patterns

**Better Solutions** (for future implementation):
1. **LRU (Least Recently Used)**: Evict evidence that hasn't been selected by LLM lately
2. **LLM-based eviction**: Ask LLM to score evidence importance when limit reached
3. **Importance scoring**: Track selection frequency + recency, evict lowest-scored
4. **Hybrid**: Combine recency, selection count, and source diversity

**Recommended Approach**:
- Add `max_index_size: int = 1000` to Constraints
- Implement LRU eviction with selection timestamp tracking
- Log eviction events to execution_log.jsonl for observability

**Estimated Effort**: 2-3 hours (design + implementation + testing)

**When to Address**:
- Before deploying as continuous service (web API, Streamlit server)
- When observing memory issues in production monitoring
- When adding metrics/observability for index size

**Workaround**:
For now, research sessions are finite (max_time_seconds) and agent instances are not reused, so memory is naturally bounded by session duration.

---

## Resolved Tech Debt

(None yet - this section will track items as they're addressed)

---

## Future Considerations

(Items to monitor but not yet actionable)

### Memory Usage Profiling
- Add metrics for ResearchRun size tracking
- Monitor evidence_store memory consumption
- Alert if index exceeds expected bounds (e.g., 500 items)

### Evidence Deduplication at Index Level
- Currently dedup happens at result level (URLs)
- Could benefit from content-based dedup at index level
- Lower priority - current approach works well
