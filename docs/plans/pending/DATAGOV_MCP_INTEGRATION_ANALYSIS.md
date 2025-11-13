# Data.gov MCP Server Integration Analysis

**Date**: 2025-10-24
**Purpose**: Evaluate datagov-mcp-server for integration into SAM.gov Intelligence Platform
**Repository**: https://github.com/melaodoidao/datagov-mcp-server

---

## Executive Summary

**Recommendation**: **YES** - Integrate datagov-mcp-server, but **NOT via MCP protocol** for CLI/Streamlit usage.

**Key Finding**: The datagov-mcp-server is a **Node.js/TypeScript** MCP server that wraps the Data.gov CKAN API. While valuable for AI assistants (Claude Desktop, Cline), it's **not directly usable** from Python CLI or Streamlit apps.

**Solution**: **Extract and adapt the Data.gov API integration logic** into a native Python `DatabaseIntegration`, following our existing pattern (SAM.gov, DVIDS, USAJobs, etc.). Use FastMCP Python framework if we later want MCP capabilities.

---

## Analysis

### 1. What is datagov-mcp-server?

**Technology Stack**:
- Language: TypeScript/Node.js
- Framework: @modelcontextprotocol/sdk (official MCP SDK)
- API Target: Data.gov CKAN API (https://catalog.data.gov/api/3)
- Transport: STDIO (designed for desktop AI assistants)

**Capabilities**:
- `package_search`: Search for datasets on Data.gov
- `package_show`: Get dataset details by ID
- `group_list`: List dataset groups/categories
- `tag_list`: List dataset tags
- Resource template: `datagov://resource/{url}` for accessing dataset resources

**Target Use Case**: AI assistants (Claude Desktop, Cline) needing access to government datasets during conversations.

### 2. MCP Protocol Overview (from FastMCP docs)

**What MCP is**:
- Model Context Protocol - Anthropic's standardized protocol for connecting LLMs to external tools/data
- Client-server architecture: AI assistant (client) → MCP server (tools/resources)
- Transport options: STDIO (desktop), HTTP/SSE (web)

**MCP Use Cases**:
1. **Desktop AI Assistants** (Claude Desktop, Cline, VS Code extensions)
   - Server runs as subprocess (STDIO transport)
   - AI can call tools/read resources during conversation
   - Example: datagov-mcp-server running in Claude Desktop

2. **Web Services** (FastMCP HTTP/SSE)
   - Server runs as HTTP endpoint
   - Remote clients connect over network
   - Example: FastMCP server deployed to cloud

3. **Python Applications** (FastMCP Python)
   - Direct in-memory integration (Client → FastMCP instance)
   - No network overhead, no subprocess
   - Example: Testing, local tools

### 3. FastMCP Python Framework

**Key Capabilities**:
```python
from fastmcp import FastMCP, Client

# Create server
mcp = FastMCP("MyServer")

@mcp.tool
def search_data(query: str) -> dict:
    """Search for data"""
    return {"results": [...]}

# Option 1: In-memory usage (testing, local apps)
async with Client(mcp) as client:
    result = await client.call_tool("search_data", {"query": "test"})

# Option 2: HTTP deployment (web services)
if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)

# Option 3: STDIO (desktop AI assistants)
if __name__ == "__main__":
    mcp.run()  # STDIO by default
```

**Advantages**:
- Pythonic API (decorators, async/await)
- Multiple transports (STDIO, HTTP/SSE)
- OAuth/JWT authentication support
- Server composition (mount multiple servers)
- Testing utilities (in-memory clients)

---

## Integration Options

### Option A: Native Python Integration (RECOMMENDED)

**Approach**: Create `integrations/government/datagov_integration.py` following our `DatabaseIntegration` pattern.

**Why This is Best**:
1. ✅ **Consistent with existing architecture** (SAM.gov, DVIDS, USAJobs all use this pattern)
2. ✅ **No MCP overhead** for CLI/Streamlit (direct API calls)
3. ✅ **Works with existing `ParallelExecutor`** and registry
4. ✅ **Contract tests apply automatically** (via existing test infrastructure)
5. ✅ **Simple to implement** (extract CKAN API logic from TypeScript server)

**Implementation**:
```python
# integrations/government/datagov_integration.py
from core.database_integration_base import DatabaseIntegration, QueryResult
from llm_utils import acompletion
import aiohttp

class DataGovIntegration(DatabaseIntegration):
    BASE_URL = "https://catalog.data.gov/api/3"

    @property
    def metadata(self) -> DatabaseMetadata:
        return DatabaseMetadata(
            id="datagov",
            name="Data.gov",
            category=DatabaseCategory.GOV_GENERAL,
            description="Federal government open data portal",
            requires_api_key=False,
            cost_per_query_estimate=0.0,
            typical_response_time=2.0
        )

    async def is_relevant(self, research_question: str) -> bool:
        # Quick keyword check
        keywords = ["dataset", "data", "government data", "open data", "statistics"]
        return any(kw in research_question.lower() for kw in keywords)

    async def generate_query(self, research_question: str) -> Optional[Dict]:
        # Use LLM to extract search terms and filters
        prompt = f"""Extract Data.gov search parameters for: "{research_question}"

        Return JSON with:
        - q: search query string
        - tags: list of relevant tags (e.g., ["health", "education"])
        - groups: list of relevant groups (e.g., ["federal-agency-123"])
        """

        response = await acompletion(
            model="gpt-5-nano",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_schema", ...}
        )

        return json.loads(response.choices[0].message.content)

    async def execute_search(self, query_params, api_key, limit) -> QueryResult:
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{self.BASE_URL}/action/package_search"
                params = {
                    "q": query_params.get("q", ""),
                    "rows": limit,
                    "start": 0
                }

                # Add tag filters if present
                if query_params.get("tags"):
                    params["fq"] = f"tags:({' OR '.join(query_params['tags'])})"

                async with session.get(url, params=params) as resp:
                    data = await resp.json()

                    if not data.get("success"):
                        return QueryResult(
                            success=False,
                            source="Data.gov",
                            error=data.get("error", {}).get("message", "Unknown error"),
                            total=0,
                            results=[]
                        )

                    results = []
                    for pkg in data["result"]["results"]:
                        results.append({
                            "title": pkg["title"],
                            "url": f"https://catalog.data.gov/dataset/{pkg['name']}",
                            "description": pkg.get("notes", ""),
                            "organization": pkg.get("organization", {}).get("title", ""),
                            "tags": [tag["name"] for tag in pkg.get("tags", [])],
                            "metadata_modified": pkg.get("metadata_modified")
                        })

                    return QueryResult(
                        success=True,
                        source="Data.gov",
                        total=data["result"]["count"],
                        results=results
                    )

        except Exception as e:
            return QueryResult(
                success=False,
                source="Data.gov",
                error=str(e),
                total=0,
                results=[]
            )
```

**Register in registry**:
```python
# integrations/registry.py
from integrations.government.datagov_integration import DataGovIntegration

registry = IntegrationRegistry()
registry.register("datagov", DataGovIntegration)
```

**Immediate Benefits**:
- Works with `python3 apps/ai_research.py "find datasets about cybersecurity"`
- Works with Streamlit UI (already integrated via registry)
- Parallel execution with other sources
- Contract tests validate interface compliance
- Feature flags enable/disable via `config_default.yaml`

**Estimated Time**: 2-3 hours (copy CKAN API logic from TypeScript, adapt to Python, add LLM query generation, test)

---

### Option B: FastMCP Python Server (FUTURE ENHANCEMENT)

**Approach**: Later, if we want MCP capabilities, create a FastMCP server that **mounts** our existing integrations.

**When This is Useful**:
1. Want to expose our platform to **Claude Desktop** or other AI assistants
2. Want to deploy as **HTTP API** for remote clients
3. Want **OAuth authentication** for multi-user access
4. Want to **compose multiple MCP servers** into one

**Implementation** (FUTURE):
```python
# mcp_server.py (NEW FILE - not needed now)
from fastmcp import FastMCP
from integrations.registry import registry

# Create MCP server
mcp = FastMCP(
    name="SAM.gov Intelligence Platform",
    instructions="Search government databases for OSINT research"
)

# Register our integrations as MCP tools
@mcp.tool
async def search_databases(
    research_question: str,
    databases: list[str] = None,
    limit: int = 10
) -> dict:
    """Search government databases with natural language query."""
    from core.parallel_executor import ParallelExecutor

    executor = ParallelExecutor()

    # Get integrations from registry
    if databases:
        integrations = [registry.get_instance(db) for db in databases]
    else:
        integrations = list(registry.get_all_enabled().values())

    # Execute search
    results = await executor.execute_all(
        research_question=research_question,
        databases=integrations,
        api_keys={
            "sam": os.getenv("SAM_GOV_API_KEY"),
            "usajobs": os.getenv("USAJOBS_API_KEY"),
            # ... other keys
        },
        limit=limit
    )

    return {
        "research_question": research_question,
        "total_sources": len(results),
        "results": {
            db_id: {
                "success": result.success,
                "total": result.total,
                "results": result.results[:5]  # Top 5 per source
            }
            for db_id, result in results.items()
        }
    }

@mcp.tool
async def list_available_databases() -> dict:
    """List all available government database integrations."""
    return {
        db_id: {
            "name": db.metadata.name,
            "category": db.metadata.category.value,
            "description": db.metadata.description,
            "requires_api_key": db.metadata.requires_api_key
        }
        for db_id, db in registry.get_all_enabled().items()
    }

if __name__ == "__main__":
    # Option 1: STDIO (for Claude Desktop)
    mcp.run()

    # Option 2: HTTP (for web deployment)
    # mcp.run(transport="http", host="0.0.0.0", port=8000)
```

**Usage from Claude Desktop**:
```json
// claude_desktop_config.json
{
  "mcpServers": {
    "sam-gov-intel": {
      "command": "python",
      "args": ["/home/brian/sam_gov/mcp_server.py"],
      "env": {
        "SAM_GOV_API_KEY": "...",
        "DVIDS_API_KEY": "...",
        "USAJOBS_API_KEY": "..."
      }
    }
  }
}
```

**Why Defer This**:
- Our CLI/Streamlit don't need MCP protocol (direct Python integration is simpler)
- MCP adds complexity without immediate benefit for our use case
- Can add later without changing existing integrations
- Focus on core functionality first (more data sources, better search quality)

---

### Option C: Proxy datagov-mcp-server via FastMCP (NOT RECOMMENDED)

**Approach**: Run the Node.js datagov-mcp-server as subprocess, proxy through FastMCP Python.

**Why NOT Recommended**:
1. ❌ **Unnecessary complexity** (Node.js dependency, subprocess management)
2. ❌ **Performance overhead** (Python → Node.js IPC → API)
3. ❌ **Harder to debug** (cross-language issues)
4. ❌ **Doesn't fit our architecture** (all integrations are native Python)
5. ❌ **No benefit over Option A** (same API access, more complexity)

**When This Would Make Sense**:
- If we needed 50+ MCP servers and couldn't rewrite them all
- If datagov-mcp-server had complex logic we couldn't replicate
- Neither applies here (simple CKAN API, only 1 server)

---

## Recommended Implementation Plan

### Phase 1: Native Integration (Week 1)

**Action 1**: Create `DataGovIntegration` class
- File: `integrations/government/datagov_integration.py`
- Copy CKAN API logic from TypeScript server
- Adapt to Python + async/await
- Follow `DatabaseIntegration` interface

**Action 2**: Add LLM query generation
- Use gpt-5-nano for cost savings
- Extract search terms, tags, groups from research question
- Return structured query parameters

**Action 3**: Register and test
- Add to `integrations/registry.py`
- Add to `config_default.yaml` (disabled by default until tested)
- Create `tests/test_datagov_live.py`
- Run contract tests: `pytest tests/contracts/ -k datagov`

**Action 4**: End-to-end testing
- CLI: `python3 apps/ai_research.py "find datasets about military spending"`
- Streamlit: Enable in UI, test searches
- Parallel execution: Verify works with other sources

**Success Criteria**:
- [x] DataGovIntegration passes all contract tests
- [x] Returns relevant results for test queries
- [x] Works in CLI and Streamlit
- [x] Executes in parallel with other sources
- [x] Response time < 5s for typical queries

**Estimated Time**: 2-3 hours

---

### Phase 2: Enhanced Features (Week 2-3)

**Action 1**: Advanced query features
- Support tag filtering
- Support organization filtering
- Support resource format filtering (CSV, JSON, XML)
- Date range filtering (datasets updated recently)

**Action 2**: Result enrichment
- Include dataset metadata (update frequency, data quality)
- Include resource links (direct download URLs)
- Include organization info (agency, department)

**Action 3**: Caching
- Cache search results (TTL: 24 hours)
- Cache dataset details (TTL: 7 days)
- Use Redis or local SQLite

**Success Criteria**:
- [x] Advanced filters working
- [x] Rich result metadata included
- [x] Cache improves performance (2nd query <500ms)

**Estimated Time**: 3-4 hours

---

### Phase 3: MCP Server (FUTURE - Optional)

**Only if needed for**:
- Claude Desktop integration
- Remote API deployment
- Multi-user OAuth access

**Action 1**: Create FastMCP wrapper
- File: `mcp_server.py`
- Wrap existing integrations as MCP tools
- Support STDIO and HTTP transports

**Action 2**: Authentication (if HTTP deployment)
- Add OAuth provider (Google/GitHub)
- JWT token validation
- Rate limiting per user

**Action 3**: Deployment
- Docker container
- HTTPS endpoint
- Monitoring/logging

**Success Criteria**:
- [x] Works in Claude Desktop
- [x] HTTP endpoint accessible remotely
- [x] Authentication working
- [x] Rate limits enforced

**Estimated Time**: 4-6 hours (only if needed)

---

## Key Takeaways

### What to Do NOW

1. ✅ **Implement Option A** (Native Python Integration)
   - Fastest path to value
   - Consistent with existing architecture
   - Works immediately in CLI and Streamlit
   - No new dependencies (TypeScript, Node.js, MCP complexity)

2. ✅ **Extract CKAN API logic** from datagov-mcp-server TypeScript code
   - Package search endpoint
   - Package details endpoint
   - Tag/group filtering
   - Error handling patterns

3. ✅ **Add to integration registry** following existing patterns
   - DatabaseIntegration interface
   - Contract tests validate automatically
   - Feature flags in config

### What to Do LATER

1. ⏳ **FastMCP wrapper** (Phase 3) - only if:
   - Need Claude Desktop integration
   - Want to expose as public API
   - Need OAuth/multi-user support

2. ⏳ **Advanced features** (Phase 2):
   - Caching
   - Advanced filters
   - Result enrichment

### What NOT to Do

1. ❌ **Don't proxy Node.js server** (Option C)
   - Unnecessary complexity
   - Performance overhead
   - Harder to debug
   - No architectural benefit

2. ❌ **Don't use MCP protocol for CLI/Streamlit**
   - MCP is for AI assistants, not our Python apps
   - Direct Python integration is simpler and faster
   - Can add MCP layer later without changing integrations

---

## Technical References

### Data.gov CKAN API Endpoints

**Base URL**: `https://catalog.data.gov/api/3`

**Package Search**:
```
GET /action/package_search?q=query&rows=10&start=0
GET /action/package_search?q=query&fq=tags:(health OR education)
```

**Package Details**:
```
GET /action/package_show?id=package-id-or-name
```

**Groups/Tags**:
```
GET /action/group_list?all_fields=true
GET /action/tag_list?query=search
```

**Documentation**: https://docs.ckan.org/en/2.10/api/

### FastMCP Python Resources

**Installation**:
```bash
pip install fastmcp
```

**Documentation**:
- Getting Started: https://gofastmcp.com/docs/getting-started/quickstart
- Python SDK: https://gofastmcp.com/docs/python-sdk/fastmcp-server-server
- Client Usage: https://gofastmcp.com/docs/clients/client
- Deployment: https://gofastmcp.com/docs/deployment/running-server

**GitHub**: https://github.com/jlowin/fastmcp

---

## Conclusion

**Go with Option A (Native Python Integration)** for immediate value. The datagov-mcp-server TypeScript code is a **reference implementation** showing how to structure CKAN API calls, but we should adapt it to native Python following our existing `DatabaseIntegration` pattern.

**Reserve FastMCP** (Option B) for future enhancements when we want to expose our platform to AI assistants or deploy as a remote API. It's powerful but adds complexity we don't need yet.

**Estimated total time to working integration**: 2-3 hours (Phase 1 only)

**Next step**: Implement `DataGovIntegration` class, test via CLI, then enable in Streamlit.
