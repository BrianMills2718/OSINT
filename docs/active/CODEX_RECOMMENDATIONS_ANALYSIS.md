# Codex Recommendations Analysis - Uncertainties & Concerns

**Date**: 2025-11-13
**Context**: Codex proposed 4 changes to improve deep research quality
**Status**: Analysis complete - ready for implementation decision

---

## Summary of Codex's Recommendations

1. ✅ **Increase default_result_limit** from 10 → 20
2. ⚠️  **Remove hardcoded entity filter** (lines 493-529)
3. ✅ **Normalize default prompt** (test-only contractor bias)
4. ⚠️  **Enable LLM pagination control** (param_hints expansion)

---

## Recommendation #1: Increase Per-Call Limits (10 → 20)

### What Codex Wants

Change `config_default.yaml:59` from:
```yaml
execution:
  default_result_limit: 10        # Default results per database
```

To:
```yaml
execution:
  default_result_limit: 20        # Default results per database
```

And update any per-integration overrides to match.

### My Investigation

**Current Usage** (grep results):
- `config_default.yaml:59`: `default_result_limit: 10`
- `config_loader.py:192-194`: Property returns this value
- `deep_research.py:633, 1084`: Brave Search hardcoded to `max_results=20` (already higher!)
- No per-integration overrides found in `config_default.yaml`

**Actual Usage in Deep Research**:
- `deep_research.py:585`: `limit=10` passed to MCP tools
- This is the **only** place `default_result_limit` affects deep research

### Uncertainties

1. **❓ Scope of Change**: Does Codex want ONLY config change, or also update line 585?
2. **❓ Brave Search Inconsistency**: Brave already uses 20, should we keep that or make it configurable?
3. **❓ Integration-Specific Limits**: Should we add per-integration overrides (e.g., ClearanceJobs: 20, USAJobs: 100)?

### Concerns

1. **🚨 Brave Search Already Higher**: Line 1084 already uses `max_results=20` - changing config to 20 won't affect it
2. **⚠️  No Evidence of 10 Being Too Low**: No test failures or quality issues documented
3. **💡 Recommendation**: Change to 20 but ALSO add per-integration config section:

```yaml
# Integration-Specific Result Limits
integration_limits:
  clearancejobs: 20      # 20 jobs per call
  usajobs: 100           # USAJobs API supports 100/page
  brave_search: 20       # Free tier limit
  sam: 10                # SAM.gov can be slow
  dvids: 50              # DVIDS max is 50
  # Default: use execution.default_result_limit
```

### Implementation Impact

- **Files to modify**:
  - `config_default.yaml` (1 line change + optional new section)
  - `deep_research.py:585` (use config value instead of hardcoded 10)
  - `deep_research.py:1084` (use config value instead of hardcoded 20)

- **Risk**: LOW - increasing limits improves coverage, no downside
- **Time**: 15 minutes
- **Testing**: Run existing test, verify more results returned

---

## Recommendation #2: Remove Hardcoded Entity Filter

### What Codex Wants

**Delete lines 493-529 in `research/deep_research.py`**:

```python
# Task 3: Filter entities incrementally (blacklist + multi-task confirmation)
META_TERMS_BLACKLIST = {
    "defense contractor", "cybersecurity", "clearance",
    "polygraph", "job", "federal government", "security clearance",
    "government", "contractor", "defense"
}

# Count entity occurrences across tasks
entity_task_counts = {}
for task in self.completed_tasks:
    task_entities = set(e.strip().lower() for e in task.entities_found if e.strip())
    for entity in task_entities:
        if entity not in entity_task_counts:
            entity_task_counts[entity] = 0
        entity_task_counts[entity] += 1

# Filter entities
filtered_entities = set()
for entity in all_entities:
    # Drop meta-terms
    if entity in META_TERMS_BLACKLIST:
        continue

    # Require 2+ task appearances (unless only 1 task completed)
    min_task_threshold = 2 if len(self.completed_tasks) > 1 else 1
    if entity_task_counts.get(entity, 0) < min_task_threshold:
        continue

    filtered_entities.add(entity)

# Log filtering stats
entities_filtered_out = len(all_entities) - len(filtered_entities)
if entities_filtered_out > 0:
    logging.info(f"Entity filtering: Removed {entities_filtered_out} entities ({len(all_entities)} → {len(filtered_entities)})")
    print(f"🔍 Entity filtering: Removed {entities_filtered_out} low-confidence entities ({len(all_entities)} → {len(filtered_entities)} kept)")

all_entities = filtered_entities  # Replace with filtered set
```

**Replace with**: LLM-driven filtering in `_extract_entities()` prompt

### My Investigation

**Current State**:
- Entity extraction happens at **line 414** (per-task, called AFTER task completion)
- Entity filtering happens at **line 493** (AFTER all tasks complete, before synthesis)
- **Two-stage process**: LLM extracts → Python filters → Synthesis uses filtered

**What Gets Filtered**:
1. **Meta-terms blacklist** (9 terms): "cybersecurity", "job", "clearance", etc.
2. **Low-confidence entities**: Entities appearing in only 1 task (when multiple tasks exist)

**Evidence from Test Output** (`test_polish_validation.py` - checking background bash):
<function_calls>
<invoke name="BashOutput">
<parameter name="bash_id">18bef3