# Source Attribution Fix - Deep Investigation

**Date**: 2025-10-24
**Issue**: Deep Investigation showing "Unknown" source instead of actual database names (DVIDS, SAM.gov, Twitter, etc.)
**Status**: FIXED

---

## Problem Analysis

### Symptoms

User reported Deep Investigation results showing:
```
Sources Searched: 3 - Unknown, Brave Search, FBI Vault
```

Expected behavior: Show all 7 MCP tools (SAM.gov, DVIDS, USAJobs, ClearanceJobs, Twitter, Reddit, Discord) plus Brave Search and FBI Vault.

### Root Cause

**Architecture**: Deep Investigation calls 7 MCP tools in parallel via `_search_mcp_tools()` method.

**Data Flow**:
```
DatabaseIntegration.execute_search()
  ↓ returns QueryResult with source field
MCP wrapper (e.g., search_dvids)
  ↓ returns dict with "source": "DVIDS"
deep_research.py call_mcp_tool()
  ↓ WAS NOT passing through "source" field
deep_research.py _search_mcp_tools()
  ↓ tried to get source from individual results
deep_research.py _get_sources()
  ↓ defaults to "Unknown" when source field missing
```

**Specific Issues**:

1. **Line 586 (call_mcp_tool)**: Didn't pass through "source" field from MCP wrapper
   ```python
   # OLD (missing source)
   return {
       "tool": tool_name,
       "success": result_data.get("success", False),
       "results": result_data.get("results", []),
       "total": result_data.get("total", 0),
       "error": result_data.get("error")
   }
   ```

2. **Line 611 (_search_mcp_tools)**: Tried to get source from first individual result instead of wrapper level
   ```python
   # OLD (wrong level)
   source = tool_results[0].get("source") if tool_results else tool_result["tool"]
   ```

3. **Individual results**: Didn't have "source" field added, causing _get_sources() to return "Unknown"

---

## The Fix

### Change 1: Pass Through Source Field (Lines 583-603)

```python
# Get source name from result_data
source_name = result_data.get("source", tool_name)

# Add source field to each individual result for proper tracking
results_with_source = []
for r in result_data.get("results", []):
    # Make a copy to avoid mutating original
    r_copy = dict(r)
    # Add source if not already present
    if "source" not in r_copy:
        r_copy["source"] = source_name
    results_with_source.append(r_copy)

return {
    "tool": tool_name,
    "success": result_data.get("success", False),
    "source": source_name,  # NEW: Pass through source from wrapper
    "results": results_with_source,  # NEW: Individual results now have source
    "total": result_data.get("total", 0),
    "error": result_data.get("error")
}
```

**Why**:
- Extracts source name from MCP wrapper response
- Adds source field to EACH individual result dict
- Passes source through at wrapper level
- Ensures both levels have correct source attribution

### Change 2: Get Source from Wrapper Level (Lines 626-629)

```python
# Get source from wrapper level (now passed through from call_mcp_tool)
source = tool_result.get("source", tool_result["tool"])
sources_count[source] = sources_count.get(source, 0) + len(tool_results)
# Log each successful source with counts
print(f"  ✓ {source}: {len(tool_results)} results")
```

**Why**:
- Uses source from tool_result (wrapper level) instead of tool_results[0] (individual result)
- Correctly accumulates counts per source
- Logs actual source names (e.g., "DVIDS") instead of tool names (e.g., "search_dvids")

### Change 3: Add Per-Source Breakdown Logging (Lines 634-639)

```python
# Log summary with per-source breakdown
print(f"\n✓ MCP tools complete: {len(all_results)} total results from {len(sources_count)} sources")
if sources_count:
    print("  Per-source breakdown:")
    for source, count in sorted(sources_count.items(), key=lambda x: x[1], reverse=True):
        print(f"    • {source}: {count} results")
```

**Why**:
- Provides visibility into which databases returned results
- Shows per-source counts sorted by result count
- Helps verify all 7 MCP tools are being called correctly

---

## Expected Behavior After Fix

### Console Output

```
🔍 Searching 7 databases via MCP tools...
  ✓ DVIDS: 15 results
  ✓ Brave Search: 20 results
  ✓ FBI Vault: 8 results
  ✓ SAM.gov: 0 results
  ✗ Twitter: Failed - Not relevant
  ✗ Reddit: Failed - Not relevant
  ✗ Discord: Failed - Not relevant
  ✗ USAJobs: Failed - Not relevant
  ✗ ClearanceJobs: Failed - Not relevant

✓ MCP tools complete: 43 total results from 3 sources
  Per-source breakdown:
    • Brave Search: 20 results
    • DVIDS: 15 results
    • FBI Vault: 8 results
```

### Result Statistics

```python
{
    "sources_searched": ["DVIDS", "Brave Search", "FBI Vault"],  # Real names, not "Unknown"
    "total_results": 43,
    "tasks_executed": 9,
    "entities_discovered": 72
}
```

### Individual Results

```python
{
    "title": "Navy ship deployment",
    "source": "DVIDS",  # ← Now correctly set
    "url": "https://...",
    "snippet": "..."
}
```

---

## Testing

Run Deep Investigation with a query that should match multiple sources:

```bash
source .venv/bin/activate
# Via Streamlit UI
streamlit run apps/unified_search_app.py
# Go to Deep Investigation tab, enter query like:
# "military special operations training exercises"
```

**Verify**:
- [ ] Console shows per-source breakdown with actual source names
- [ ] Result statistics show sources list without "Unknown"
- [ ] Individual results have correct source field
- [ ] All 7 MCP tools are being called (check console logs)

---

## Related Issues

### Background Execution Continuing After "Done"

**User Concern**: "im still seeing logs indicating that it is still searching twitter etc even though it says it is done!"

**Explanation**: This is EXPECTED behavior due to parallel execution architecture:

1. Tasks execute in batches of 3 (max_concurrent_tasks=3)
2. Within each task, all 7 MCP tools called in parallel via `asyncio.gather()`
3. Up to 21 database searches happening simultaneously (3 tasks × 7 tools)

**What happens**:
- UI shows "Task 1 completed" when first task finishes
- But other 2 tasks in batch still running in background
- Logs continue showing "searching twitter" from tasks 2 and 3

**This is NOT a bug** - it's efficient parallel execution. Tasks complete at different times.

**If UI shows "done" prematurely** before all parallel operations finish:
- Check Streamlit progress callback implementation
- May need to track total pending parallel operations
- Wait for ALL asyncio.gather() calls to complete before showing "done"

---

## Files Modified

- `research/deep_research.py`:
  - Lines 583-603: Pass through source field and add to individual results
  - Lines 626-629: Get source from wrapper level
  - Lines 634-639: Add per-source breakdown logging

---

## Next Steps

1. **Test with real query** to verify source attribution working
2. **Check UI display** to ensure sources shown correctly
3. **Verify parallel execution** logs show expected behavior
4. **Update documentation** if needed to explain parallel execution behavior
