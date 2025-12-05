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

### 2. Schema Externalization: Inline JSON Schemas in 36 Files

**Component**: 36 integration and research files with inline JSON schemas (~3,500 lines)

**Issue**:
JSON schemas are defined inline in Python code using `schema = { "type": "object", ... }` pattern rather than externalized to a central `schemas/` directory.

**Files Affected**:
- `integrations/government/` (15 files: sam_integration.py, usaspending_integration.py, dvids_integration.py, fec_integration.py, sec_edgar/integration.py, govinfo_integration.py, federal_register.py, usajobs_integration.py, clearancejobs_integration.py, +6 more)
- `integrations/social/` (5 files: twitter_integration.py, telegram_integration.py, discord_integration.py, reddit_integration.py, brave_search_integration.py)
- `research/` (10 files: recursive_agent.py, deep_research.py, +8 more)

**Current Impact**:
- **Low** for schema stability - Schemas rarely change after initial implementation
- **Low** for maintainability - Inline schemas are colocated with usage, easy to understand
- **Medium** for version control - Schema changes mixed with code changes in git diffs
- **Medium** for reusability - Can't share schemas across integrations (though rarely needed)

**Why Deferred** (2025-11-30):
1. **Questionable value**: Schemas are edited infrequently (maybe once per quarter)
2. **High risk**: Refactoring 36 files with working structured output = high regression risk
3. **Large effort**: 8-9 days estimated (3 days schemas + testing burden)
4. **System stability**: Just completed Gemini 2.5 Flash migration - schemas are stable
5. **Opportunity cost**: Time better spent on new integrations or fixing SAM.gov timeouts

**Better Solutions** (for future implementation):
1. **Class-based schemas**: Create `schemas/` directory with schema classes
   ```python
   from schemas.recursive_agent import GlobalEvidenceSelectionSchema
   schema = GlobalEvidenceSelectionSchema.get_schema()
   ```
2. **Schema registry**: Central registry for validation and documentation
3. **Provider-specific schemas**: Separate schemas for OpenAI vs Gemini compatibility
4. **Schema validation**: pytest tests to validate all schemas independently

**Recommended Approach**:
- Create `schemas/` directory structure organized by module
- Migrate 10-15 files per batch with comprehensive testing
- Start with most-edited integrations (if we identify which those are)
- Add schema validation tests before migration

**Estimated Effort**: 8-9 days (3 days implementation + 5-6 days testing across 36 integrations)

**When to Address**:
- When we're editing the same schema across multiple files (copy-paste pain)
- When building a schema library for reusable patterns
- When onboarding new developers who need centralized schema documentation
- When we identify integrations with frequently-changing schemas

**Workaround**:
Inline schemas work fine for now. Use Ctrl+F to find schema definitions when editing. Git diffs show schema changes clearly in context with code changes.

**Decision Date**: 2025-11-30
**Decision Maker**: User approved deferral, prioritizing prompt refactoring instead

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
