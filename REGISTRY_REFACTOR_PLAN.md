# Registry Refactor Plan

**Date**: 2025-10-19
**Goal**: Make adding new sources require ZERO code changes (just add integration class)
**Rollback**: `git reset --hard 97138e3` (Discord integration commit)

---

## Problem Statement

Currently, adding a new source requires changes in 3+ places:
1. `apps/ai_research.py` - Update LLM prompt with source description
2. `apps/ai_research.py` - Add source-specific execute function
3. `apps/ai_research.py` - Add source-specific result display logic
4. `monitoring/boolean_monitor.py` - Add elif block for source
5. `apps/unified_search_app.py` - Add new tab (optional)

**With 15+ sources planned**, this becomes unmaintainable.

---

## Solution: Registry-Driven Architecture

**After refactor**, adding a source only requires:
1. Create integration class extending `DatabaseIntegration`
2. Register in `integrations/registry.py`
3. **That's it** - AI Research, Boolean monitors auto-discover it

---

## Phase 1: AI Research Tab (2-3 hours)

### Current Architecture
```python
# Hardcoded prompt
prompt = """Search these 3 databases:
1. ClearanceJobs - job postings
2. DVIDS - military media
3. SAM.gov - contracts
"""

# Hardcoded schema
query_schema = {
    "properties": {
        "clearancejobs": {...},  # Source-specific fields
        "dvids": {...},
        "sam_gov": {...}
    }
}

# Hardcoded execution
execute_clearancejobs_search(...)
execute_dvids_search(...)
execute_sam_search(...)
```

### Target Architecture
```python
from integrations.registry import registry

# Auto-discover sources
sources = registry.get_all()

# Dynamic prompt with metadata
source_list = []
for source_id, source_class in sources.items():
    meta = source_class().metadata
    source_list.append({
        "id": source_id,
        "name": meta.name,
        "category": meta.category.value,
        "description": meta.description
    })

prompt = f"""Available databases:
{json.dumps(source_list, indent=2)}

Select 2-3 most relevant databases and generate keywords for each.
"""

# Generic schema
query_schema = {
    "type": "object",
    "properties": {
        "selected_sources": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "source_id": {"type": "string"},
                    "keywords": {"type": "string"},
                    "reasoning": {"type": "string"}
                }
            }
        }
    }
}

# Generic execution via registry
for selected in response["selected_sources"]:
    integration_class = registry.get(selected["source_id"])
    integration = integration_class()
    query_params = await integration.generate_query(selected["keywords"])
    result = await integration.execute_search(query_params, api_key, limit=10)
```

### Changes Required

**File**: `apps/ai_research.py`

1. **Import registry** (line 13):
```python
from integrations.registry import registry
import asyncio
```

2. **Replace `generate_search_queries()`** (lines 37-139):
   - Build source list from registry
   - Create generic schema (not source-specific)
   - LLM returns `{selected_sources: [{source_id, keywords, reasoning}]}`

3. **Replace execute functions** (lines 142-354):
   - Delete `execute_clearancejobs_search()`
   - Delete `execute_dvids_search()`
   - Delete `execute_sam_search()`
   - Create single `execute_search(source_id, keywords, api_key, limit)`

4. **Update result display** (lines 599-643):
   - Generic display (works for all sources)
   - Use `QueryResult` standard format

### Risks

1. **Source-specific parameters lost**: Current schema has clearance levels, NAICS codes, date formats per source. Generic schema loses this.
   - **Mitigation**: Use `integration.generate_query()` to let each integration define its own parameters from keywords

2. **LLM selects all sources**: Might return 6 sources for every query
   - **Mitigation**: Prompt instructs "Select 2-3 MOST relevant"

3. **Breaking existing queries**: Users might have saved workflows
   - **Mitigation**: Rollback commit exists

---

## Phase 2: Boolean Monitors (1 hour)

### Current Architecture
```python
if source == "dvids":
    from integrations.government.dvids_integration import DVIDSIntegration
    dvids = DVIDSIntegration()
    ...
elif source == "sam":
    from integrations.government.sam_integration import SAMIntegration
    sam = SAMIntegration()
    ...
# 100 more lines of elif blocks
```

### Target Architecture
```python
from integrations.registry import registry

integration_class = registry.get(source)
if not integration_class:
    logger.warning(f"Unknown source: {source}")
    return []

integration = integration_class()
api_key = None
if integration.metadata.requires_api_key:
    api_key = os.getenv(f"{source.upper()}_API_KEY")

query_params = await integration.generate_query(keyword)
result = await integration.execute_search(query_params, api_key, limit=10)
return result.results  # Already standardized
```

### Changes Required

**File**: `monitoring/boolean_monitor.py`

1. **Replace `_search_single_source()`** (lines 173-290):
   - Delete entire if/elif chain
   - Use registry lookup
   - All sources return `QueryResult` with standardized format

2. **Benefits**:
   - Adding Discord = add "discord" to monitor YAML, zero code changes
   - Consistent error handling
   - No more field mapping bugs

---

## Testing Plan

### Phase 1 Testing (AI Research)

```bash
# Test with existing sources
streamlit run apps/unified_search_app.py
# Go to AI Research tab
# Query: "cybersecurity jobs and contracts"
# Expected: LLM selects ClearanceJobs, SAM.gov (not DVIDS)
# Verify results display correctly

# Test with Discord
# Query: "Ukraine OSINT analysis"
# Expected: LLM selects Discord, DVIDS
# Verify Discord results appear

# Test with all sources
# Query: "federal government surveillance programs"
# Expected: LLM selects Federal Register, SAM.gov, maybe DVIDS
# Verify results from all selected sources
```

### Phase 2 Testing (Boolean Monitors)

```bash
# Create test monitor with Discord
cat > data/monitors/configs/test_discord_monitor.yaml << 'YAML'
name: Test Discord Monitor
keywords:
  - "ukraine"
sources:
  - discord
  - dvids
schedule: manual
alert_email: test@example.com
enabled: true
YAML

# Run monitor
python3 monitoring/boolean_monitor.py

# Expected: Results from both Discord and DVIDS
# Verify no errors, results formatted correctly
```

---

## Rollback Plan

If anything breaks:

```bash
# Rollback to Discord integration commit
git reset --hard 97138e3

# Or rollback specific files
git checkout 97138e3 apps/ai_research.py
git checkout 97138e3 monitoring/boolean_monitor.py
```

---

## Success Criteria

**Phase 1 Complete**:
- [ ] AI Research uses registry for source discovery
- [ ] LLM sees all 6 sources automatically
- [ ] Adding 7th source requires NO changes to ai_research.py
- [ ] All existing queries still work

**Phase 2 Complete**:
- [ ] Boolean monitors use registry
- [ ] Can add Discord to monitor via YAML only
- [ ] All 6 sources work in monitors
- [ ] No elif blocks remain

---

## Estimated Timeline

- **Phase 1** (AI Research): 2-3 hours
  - 1 hour: Refactor generate_search_queries()
  - 30 min: Refactor execute functions
  - 30 min: Update result display
  - 1 hour: Testing and bug fixes

- **Phase 2** (Boolean Monitors): 1 hour
  - 30 min: Refactor _search_single_source()
  - 30 min: Testing

**Total**: 3-4 hours

---

## Next Action

Start Phase 1: Refactor `apps/ai_research.py` to use registry.
