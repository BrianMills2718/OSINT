# Data.gov MCP Integration Roadmap

**Date**: 2025-10-24
**Status**: READY TO EXECUTE (pending manual validation completion)
**Prerequisite**: Automated validation PASSED ✅
**Estimated Time**: 4-6 hours

---

## Prerequisites (COMPLETE ✅)

- ✅ Node.js v22.16.0 installed
- ✅ npm v10.9.2 installed
- ✅ datagov-mcp-server installed (`npm install -g @melaodoidao/datagov-mcp-server`)
- ✅ STDIO transport validated (100% success, 4.95s avg latency)
- ⏳ Manual data quality validation (awaiting user completion)

---

## Phase 1: Core Integration (2-3 hours)

### Step 1.1: Add Data.gov Tool to Deep Research (30 minutes)

**File to modify**: `research/deep_research.py`

**Changes**:

1. Add STDIO imports at top:
```python
from mcp.client.stdio import stdio_client, StdioServerParameters
```

2. Add Data.gov server configuration (after line 170, in `__init__`):
```python
# Check if Node.js available for Data.gov MCP server
self.datagov_available = self._check_node_available()

if self.datagov_available:
    # Data.gov MCP server (STDIO transport)
    self.datagov_server = StdioServerParameters(
        command="datagov-mcp-server",
        args=[],
        env=None
    )
else:
    logging.warning("Node.js not available - Data.gov integration disabled")
    self.datagov_server = None
```

3. Add Node.js detection helper method:
```python
def _check_node_available(self) -> bool:
    """Check if Node.js is available for Data.gov integration."""
    try:
        import subprocess
        result = subprocess.run(
            ["node", "--version"],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False
```

4. Update `_search_mcp_tools()` to handle STDIO server alongside in-memory servers:
```python
async def _search_mcp_tools(self, query: str, limit: int = 10) -> List[Dict]:
    """Search using MCP tools (government + social sources + Data.gov)."""

    # Existing in-memory tools (7 tools)
    mcp_tasks = [call_mcp_tool(tool) for tool in self.mcp_tools]

    # Add Data.gov if available
    if self.datagov_available and self.datagov_server:
        mcp_tasks.append(self._search_datagov(query, limit))

    # Execute all in parallel
    results = await asyncio.gather(*mcp_tasks)

    # Combine and return
    all_results = []
    for result in results:
        if result["success"]:
            all_results.extend(result["results"])

    return all_results
```

5. Add Data.gov search method:
```python
async def _search_datagov(self, query: str, limit: int = 10) -> Dict:
    """Search Data.gov via STDIO MCP server."""
    try:
        async with stdio_client(self.datagov_server) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Call package_search tool
                result = await session.call_tool(
                    "package_search",
                    arguments={"q": query, "rows": limit}
                )

                # Parse result
                import json
                content = result.content[0].text if result.content else "{}"
                data = json.loads(content)

                # Extract datasets from CKAN response
                datasets = []
                if data.get("success") and data.get("result"):
                    for pkg in data["result"].get("results", []):
                        datasets.append({
                            "source": "Data.gov",
                            "title": pkg.get("title", ""),
                            "description": pkg.get("notes", "")[:500],
                            "url": f"https://catalog.data.gov/dataset/{pkg.get('name', '')}",
                            "organization": pkg.get("organization", {}).get("title", ""),
                            "metadata_modified": pkg.get("metadata_modified", "")
                        })

                return {
                    "tool": "search_datagov",
                    "success": True,
                    "results": datasets,
                    "total": len(datasets)
                }

    except Exception as e:
        logging.error(f"Data.gov search failed: {type(e).__name__}: {str(e)}")
        return {
            "tool": "search_datagov",
            "success": False,
            "results": [],
            "total": 0,
            "error": str(e)
        }
```

**Testing**:
```bash
source .venv/bin/activate
python3 tests/test_deep_research_mcp.py
# Should now include Data.gov results in output
```

---

### Step 1.2: Add Feature Flag (15 minutes)

**File to modify**: `config_default.yaml`

**Add**:
```yaml
databases:
  # ... existing integrations ...

  datagov:
    enabled: true  # Can be disabled without code changes
    description: "Data.gov datasets via MCP STDIO transport"
    requires_node: true  # Will be disabled automatically if Node.js not available
```

**File to modify**: `research/deep_research.py`

**Update `__init__`**:
```python
# Check config before enabling Data.gov
datagov_config = config.get("databases", {}).get("datagov", {})
datagov_enabled = datagov_config.get("enabled", True)

if datagov_enabled and self._check_node_available():
    self.datagov_available = True
    # ... setup datagov_server
else:
    self.datagov_available = False
    logging.info("Data.gov disabled via config or Node.js not available")
```

**Testing**:
```yaml
# Test disabling via config
databases:
  datagov:
    enabled: false
```

---

### Step 1.3: Add Graceful Degradation (15 minutes)

**File to modify**: `apps/deep_research_tab.py`

**Add info message** (if Data.gov unavailable):
```python
# After imports, add Node.js check
import subprocess

def check_datagov_available():
    try:
        result = subprocess.run(["node", "--version"], capture_output=True)
        return result.returncode == 0
    except:
        return False

# In UI
if not check_datagov_available():
    st.info("ℹ️ Data.gov integration requires Node.js (not available on Streamlit Cloud). "
            "Works on local installations. 7 of 8 integrations active.")
```

**Testing**: Deploy to Streamlit Cloud, verify graceful message appears

---

## Phase 2: Testing & Validation (1-2 hours)

### Step 2.1: Local Testing (30 minutes)

**Test 1: Simple Query**:
```bash
source .venv/bin/activate
cd /home/brian/sam_gov
python3 tests/test_deep_research_mcp.py
```

**Expected output**:
- Task decomposition working
- All 7 MCP tools + Data.gov called
- Data.gov results included in totals
- Entity extraction working
- Report synthesis complete

**Test 2: Verify Data.gov Results**:
```bash
# Add temporary debug logging to see Data.gov results
# Check that Data.gov datasets appear in combined results
```

**Success criteria**:
- ✅ Data.gov tool called successfully
- ✅ Datasets returned and parsed correctly
- ✅ Results combined with other MCP tools
- ✅ No crashes or errors

---

### Step 2.2: Performance Testing (30 minutes)

**Test latency impact**:

```python
# Before integration
avg_time_7_tools = ~3 minutes

# After integration
avg_time_8_tools = ~3-4 minutes  # Expected: +30-60s for Data.gov

# Acceptable: <5 minutes total
```

**Run**:
```bash
time python3 tests/test_deep_research_mcp.py
```

**If too slow** (>5 minutes):
- Consider making Data.gov fully async (don't wait for results)
- OR reduce Data.gov result limit (5 instead of 10)
- OR call Data.gov only for specific query types

---

### Step 2.3: Error Handling Testing (30 minutes)

**Test scenarios**:

1. **Node.js not available**:
```bash
# Rename node temporarily
sudo mv /usr/bin/node /usr/bin/node.bak
python3 tests/test_deep_research_mcp.py
# Should continue with 7 tools, no crash
sudo mv /usr/bin/node.bak /usr/bin/node
```

2. **Data.gov API down**:
```python
# Simulate by using invalid command in StdioServerParameters
# Should log error and continue with other tools
```

3. **Data.gov timeout**:
```python
# Test with very long query or increased load
# Should timeout gracefully and not block other tools
```

**Success criteria**:
- ✅ No crashes when Node.js unavailable
- ✅ Graceful error messages logged
- ✅ Other 7 tools continue working
- ✅ Deep Research completes successfully

---

## Phase 3: Documentation & Deployment (1-2 hours)

### Step 3.1: Update Documentation (30 minutes)

**Files to update**:

1. **README.md**:
```markdown
## Data.gov Integration (Optional)

Data.gov provides access to 200,000+ government datasets.

### Prerequisites

- Node.js 18+ (`node --version`)
- npm (`npm --version`)

### Installation

```bash
npm install -g @melaodoidao/datagov-mcp-server
```

### Usage

Data.gov is automatically enabled if Node.js is detected. To disable:

```yaml
# config.yaml
databases:
  datagov:
    enabled: false
```

### Deployment

- **Local**: Works if Node.js installed
- **Streamlit Cloud**: Disabled automatically (Node.js not available)
```

2. **STATUS.md**: Add Data.gov integration status
3. **CLAUDE.md**: Update Phase 3 complete
4. **MCP_INTEGRATION_PLAN.md**: Mark Phase 4 complete

---

### Step 3.2: Streamlit Cloud Testing (30 minutes)

**Deploy**:
```bash
git add .
git commit -m "Add Data.gov MCP integration (STDIO transport)"
git push origin master
```

**Test on Streamlit Cloud**:
1. Navigate to deployed app
2. Verify Data.gov info message appears (Node.js not available)
3. Test Deep Research with sample query
4. Verify 7 of 8 integrations working (no Data.gov)
5. Verify no errors in logs

**Expected result**: Graceful degradation working

---

### Step 3.3: Local Deployment Testing (30 minutes)

**Test on local machine**:
```bash
streamlit run apps/unified_search_app.py
```

**Verify**:
1. Data.gov integration active (no warning message)
2. Deep Research tab works
3. Results include Data.gov datasets
4. Performance acceptable (<5 min per query)

**Success criteria**:
- ✅ Local: Data.gov working
- ✅ Cloud: Graceful degradation working
- ✅ No errors in either environment

---

## Phase 4: Monitoring & Iteration (Ongoing)

### Step 4.1: Add Monitoring

**Metrics to track**:
- Data.gov call success rate
- Average latency per call
- Number of datasets returned per query
- User feedback on Data.gov result quality

**Implementation**:
```python
# In api_request_tracker.py
log_request(
    api_name="Data.gov (MCP STDIO)",
    endpoint="package_search",
    status_code=200 if success else 0,
    response_time_ms=latency,
    error_message=error if not success else None,
    request_params={"query": query, "limit": limit}
)
```

---

### Step 4.2: Future Optimizations

**If Data.gov proves valuable**:

1. **Build Custom Integration** (Phase 4 alternative - 4-6 hours):
   - Direct CKAN API access (Python requests)
   - No Node.js dependency
   - Full control over implementation
   - Python-native (easier maintenance)

2. **Add Caching**:
   - Cache Data.gov results per query (TTL: 24 hours)
   - Reduces latency for repeat queries

3. **Add LLM Relevance Filtering**:
   - Filter Data.gov results before including in Deep Research
   - Only keep datasets relevant to investigative journalism

4. **Add Dataset Type Filtering**:
   - Prefer: PDFs, CSVs, JSON (actual data)
   - Deprioritize: APIs, metadata-only, HTML pages

---

## Rollback Plan

### If Integration Fails

**Immediate rollback**:
```yaml
# config.yaml
databases:
  datagov:
    enabled: false
```

**No code changes needed** - feature flag handles disable.

### If Performance Unacceptable

**Option 1**: Make Data.gov async (don't wait for results)
**Option 2**: Reduce result limit (5 instead of 10)
**Option 3**: Disable for now, build custom integration later

### If Data Quality Poor

**Option 1**: Add aggressive LLM filtering
**Option 2**: Only call Data.gov for specific query types
**Option 3**: Disable and defer to Phase 4 custom integration

---

## Success Criteria Checklist

### Technical Success

- [ ] Data.gov tool integrated into Deep Research
- [ ] STDIO transport working reliably
- [ ] Feature flag implemented (can disable via config)
- [ ] Graceful degradation when Node.js unavailable
- [ ] Error handling robust (no crashes)
- [ ] Performance acceptable (<5 min per Deep Research query)

### Deployment Success

- [ ] Local deployment working (Data.gov active)
- [ ] Streamlit Cloud deployment working (Data.gov gracefully disabled)
- [ ] Documentation updated (README, STATUS, CLAUDE)
- [ ] Monitoring implemented (api_request_tracker)

### User Experience Success

- [ ] Results include Data.gov datasets
- [ ] Result quality acceptable (not too much noise)
- [ ] Performance impact acceptable
- [ ] Clear messaging when Data.gov unavailable

---

## Timeline Summary

**Phase 1**: Core Integration (2-3 hours)
- Step 1.1: Add Data.gov tool (30 min)
- Step 1.2: Add feature flag (15 min)
- Step 1.3: Add graceful degradation (15 min)
- Buffer for debugging (1-1.5 hours)

**Phase 2**: Testing & Validation (1-2 hours)
- Step 2.1: Local testing (30 min)
- Step 2.2: Performance testing (30 min)
- Step 2.3: Error handling testing (30 min)

**Phase 3**: Documentation & Deployment (1-2 hours)
- Step 3.1: Update documentation (30 min)
- Step 3.2: Streamlit Cloud testing (30 min)
- Step 3.3: Local deployment testing (30 min)

**Total**: 4-7 hours (with buffer)

---

## Next Steps (After Manual Validation)

1. **If HIGH/MEDIUM value** → Execute Phase 1 (core integration)
2. **If LOW value** → Discuss: proceed with caution or defer?
3. **If NO value** → Skip Data.gov or plan custom integration for later

**Awaiting**: User completion of `tests/DATAGOV_MANUAL_VALIDATION.md`

---

**Document Status**: READY TO EXECUTE
**Last Updated**: 2025-10-24
**Dependencies**: Manual validation findings
