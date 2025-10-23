# Integration Bugs Investigation Report

## Summary
User is correct: Both DVIDS and Discord have SIGINT content but integrations return 0 results.

## Evidence

### DVIDS - Has Content, Integration Returns 0
**Direct API Test** (all return 10 results):
```bash
curl "https://api.dvidshub.net/search?api_key=KEY&q=SIGINT&max_results=10"
curl "https://api.dvidshub.net/search?api_key=KEY&q=signals+intelligence&max_results=10"
curl "https://api.dvidshub.net/search?api_key=KEY&q=cryptologic&max_results=10"
```

**Integration Test** (returns 0):
```python
integration = DVIDSIntegration()
query_params = await integration.generate_query("SIGINT signals intelligence")
# Returns: {'keywords': 'SIGINT OR signals intelligence OR electronic warfare OR COMINT OR ELINT', ...}

result = await integration.execute_search(query_params, api_key=api_key)
# Returns: success=True, total=0 ❌
```

### Discord - Has Content, Integration Returns 0
**Grep Test** (20+ matches):
```bash
cd data/exports
grep -i "sigint" *.json | wc -l
# Returns: 20+ matches across Bellingcat and Project Owl channels
```

**Sample Discord Content**:
- Bellingcat aviation: "Italy deploys Beech B350ER SPYDR sigint platform"
- Project Owl military: "tactical SIGINT arrays to automatically classify"
- Project Owl Ukraine/Russia: "SIGINT/ELINT help in this endeavour"

**Integration Test** (returns 0):
```python
integration = DiscordIntegration()
query_params = await integration.generate_query("SIGINT signals intelligence")
# Returns: {'keywords': ['sigint', 'signals intelligence', ...], ...}

result = await integration.execute_search(query_params)
# Returns: success=True, total=0 ❌
```

## Root Cause Analysis Needed

### DVIDS Integration Bug
**File**: `integrations/government/dvids_integration.py`

**Suspected Issue**:
- Line 243: `params["q"] = query_params["keywords"]`
- Line 247: `params["type[]"] = query_params["media_types"]`
- Line 262-265: Date filters

**Hypothesis**:
1. Media type filter might be too restrictive
2. Date filters might be excluding results
3. Some other parameter is breaking the query

**Need to test**: Execute same query with/without each parameter to find which one breaks it.

### Discord Integration Bug
**File**: `integrations/social/discord_integration.py`

**Code at line 203** (keyword matching):
```python
if all(kw in content for kw in keywords):
```

**Suspected Issue**:
- LLM generates: `['sigint', 'signals intelligence', 'electronic surveillance', ...]`
- Code requires ALL keywords to match
- Discord messages have "sigint" OR "signals intelligence" but not both
- ALL-match is too restrictive - should be ANY-match

**Hypothesis**: Changing `all(kw in content for kw in keywords)` to `any(kw in content for kw in keywords)` would find results.

## Files to Investigate

1. `integrations/government/dvids_integration.py` - Lines 233-269 (execute_search)
2. `integrations/social/discord_integration.py` - Lines 170-233 (_search_messages)
3. Test with minimal parameters to isolate bug

## Next Steps

1. **DVIDS**: Test execute_search with ONLY `q` parameter (no type[], no dates) to see if it finds results
2. **Discord**: Change keyword matching from ALL to ANY
3. Verify fixes with actual data
4. Stop making assumptions about what content exists
