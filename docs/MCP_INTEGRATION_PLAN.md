# MCP Integration Plan

**Date**: 2025-10-24
**Status**: APPROVED - Ready for implementation
**Priority**: HIGH - Foundational for product strategy

---

## Executive Summary

After investigation and POC testing, we've decided to adopt the Model Context Protocol (MCP) for our OSINT platform. This document outlines the rationale, architecture, and implementation plan.

## Background: What is MCP?

**Model Context Protocol (MCP)** is an open standard introduced by Anthropic in November 2024 for connecting AI applications to external data sources and tools. It has been adopted by:
- OpenAI (March 2025)
- Google DeepMind (April 2025)
- Major tools: Cursor IDE, Claude Desktop, Sourcegraph, Replit

**Key Concepts**:
- **MCP Host**: AI application that coordinates MCP clients (e.g., Claude Desktop, our Deep Research agent)
- **MCP Client**: Component that connects to MCP servers
- **MCP Server**: Program that exposes tools/resources/prompts to AI applications
- **Transport**: STDIO (local), HTTP/SSE (remote)

**Official Docs**: https://modelcontextprotocol.io

---

## Decision Rationale

### Investigation Timeline

1. **Initial Question**: Should we use the Data.gov MCP server that already exists?
2. **POC**: Refactored USAJobs integration to FastMCP, tested both approaches
3. **Discovery**: MCP provides value for product positioning and customer access
4. **Decision**: Adopt MCP with hybrid architecture

### Why MCP Makes Sense for Us

#### 1. Product Strategy (PRIMARY REASON)

We are planning to **sell access to this platform** as a product. MCP provides:

**Standardized Customer Integration**:
- Customers use standard MCP client (not custom REST API integration)
- Works with Claude Desktop, Cursor IDE, and any MCP-compatible AI app
- Auto-generated schemas from our docstrings
- Lower support burden (standard protocol)

**Market Positioning**:
- "MCP-compatible OSINT platform" = instant credibility
- Aligned with industry standard (OpenAI, Google DeepMind adoption)
- Competitive advantage: MCP-native platform

**Customer Use Cases**:
- Journalists use our integrations in Claude Desktop for research
- Developers integrate with their AI applications
- Teams mix our integrations with other MCP servers (Slack, GitHub, etc.)

#### 2. Third-Party Integration

**Problem**: Some data sources have existing MCP servers (Data.gov, Sentry, Slack).

**Without MCP**: Copy their API logic, rewrite as DatabaseIntegration, maintain separately
**With MCP**: Point MCP client at their server, it just works

**Value**: Access to growing ecosystem of MCP servers without custom integration work

#### 3. Internal Architecture Benefits

**Tool Discovery**: MCP provides standard `list_tools()` for dynamic discovery
**Uniform Interface**: All tools (ours + third-party) look the same to LLM
**Extensibility**: Add new tools without changing Deep Research agent code
**Composability**: Mount multiple MCP servers into one client

#### 4. Future-Proofing

**HTTP Deployment**: When we want remote access, MCP HTTP transport is ready
**Authentication**: FastMCP supports OAuth/JWT for secure access
**Distributed Architecture**: Can deploy integrations on different servers

### What We Considered and Rejected

❌ **Custom REST API**: More work, non-standard, higher customer integration burden
❌ **No protocol layer**: Works now, but limits product potential and third-party integration
❌ **GraphQL/gRPC**: Not AI-native, no LLM tool discovery built-in

---

## Architecture Design

### Hybrid Approach: DatabaseIntegration + MCP Wrappers

**Core Principle**: Keep DatabaseIntegration as implementation layer, add MCP exposure layer.

```
┌─────────────────────────────────────────────────────────────┐
│                    Customer Access Layer                     │
│  MCP Clients (Claude Desktop, Cursor, Custom AI Apps)       │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTPS + Auth
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                    MCP Server Layer (HTTP)                   │
│  FastMCP HTTP servers with OAuth/JWT authentication         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                 MCP Wrapper Layer (In-Memory)                │
│  @mcp.tool wrappers around DatabaseIntegration classes      │
│                                                              │
│  Example:                                                    │
│  @mcp.tool                                                   │
│  async def search_sam(query: str):                          │
│      integration = SAMIntegration()                          │
│      return await integration.execute_search(...)            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│            DatabaseIntegration Layer (Core Logic)            │
│  SAMIntegration, DVIDSIntegration, USAJobsIntegration...    │
│  (Unchanged - existing implementation)                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                    External APIs                             │
│  SAM.gov, DVIDS, USAJobs, FBI Vault, Discord, etc.         │
└─────────────────────────────────────────────────────────────┘


Internal Usage (CLI/Streamlit):
┌─────────────────────────────────────────────────────────────┐
│  CLI / Streamlit (apps/)                                    │
└────────────────────────┬────────────────────────────────────┘
                         │ Option A: Direct Python
                         ↓
┌─────────────────────────────────────────────────────────────┐
│  DatabaseIntegration classes (direct import)                │
└─────────────────────────────────────────────────────────────┘

                    OR

┌─────────────────────────────────────────────────────────────┐
│  CLI / Streamlit (apps/)                                    │
└────────────────────────┬────────────────────────────────────┘
                         │ Option B: MCP Client (in-memory)
                         ↓
┌─────────────────────────────────────────────────────────────┐
│  MCP Client (in-memory, no network overhead)                │
└─────────────────────────────────────────────────────────────┘
```

### Key Design Decisions

1. **Keep DatabaseIntegration Unchanged**
   - Existing integrations remain as-is
   - No breaking changes
   - Continue using for internal CLI/Streamlit

2. **Add MCP Wrapper Layer**
   - Thin FastMCP wrappers around each integration
   - One wrapper file per integration category (government, social, etc.)
   - Auto-generated tool schemas from docstrings

3. **Support Multiple Access Patterns**
   - **Internal**: Direct Python or in-memory MCP client
   - **External**: HTTP MCP servers with authentication
   - **Third-party**: MCP client can connect to external MCP servers (Data.gov, etc.)

4. **Deep Research Uses MCP Client**
   - Uniform interface for all tools (ours + third-party)
   - Dynamic tool discovery via `list_tools()`
   - Can mix DatabaseIntegration-based tools with third-party MCP servers

---

## Implementation Plan

### Phase 1: MCP Wrappers (Week 1)

**Goal**: Wrap existing integrations as MCP tools without changing core logic.

**Tasks**:
1. Create `integrations/mcp/government_mcp.py` - Wraps SAM, DVIDS, USAJobs, FBI Vault, ClearanceJobs
2. Create `integrations/mcp/social_mcp.py` - Wraps Discord, Twitter, Brave Search
3. Test in-memory usage (no network, direct Python)
4. Verify tool schemas auto-generated correctly

**Success Criteria**:
- [ ] All 8 integrations wrapped as MCP tools
- [ ] `client.list_tools()` returns all tools with schemas
- [ ] `client.call_tool(name, args)` executes correctly
- [ ] In-memory performance equivalent to direct Python calls

**Estimated Time**: 8-12 hours

**Files Created**:
- `integrations/mcp/government_mcp.py` (~200 lines)
- `integrations/mcp/social_mcp.py` (~150 lines)
- `tests/test_mcp_wrappers.py` (~200 lines)

---

### Phase 2: Deep Research Integration (Week 2)

**Goal**: Refactor Deep Research to use MCP client for all tool access.

**Current Code** (research/deep_research.py):
```python
# Hard-coded to AdaptiveSearchEngine
result = await self.adaptive_search.adaptive_search(task.query)
```

**New Code**:
```python
# MCP client with dynamic tool discovery
tools = await self.mcp_client.list_tools()
result = await self.mcp_client.call_tool(tool_name, args)
```

**Tasks**:
1. Add MCP client initialization to `SimpleDeepResearch.__init__()`
2. Replace `AdaptiveSearchEngine` with MCP tool calls
3. Implement tool selection logic (which tools to use for each task)
4. Update entity extraction to work with MCP results
5. Test with both DatabaseIntegration wrappers AND third-party MCP server (Data.gov)

**Success Criteria**:
- [ ] Deep Research uses MCP client for all searches
- [ ] Can use both our integrations and third-party MCP servers
- [ ] Tool discovery happens dynamically via `list_tools()`
- [ ] Performance comparable to current implementation

**Estimated Time**: 12-16 hours

**Files Modified**:
- `research/deep_research.py` (~50 lines changed)
- `tests/test_deep_research.py` (~100 lines)

---

### Phase 3: HTTP Deployment (Week 3-4)

**Goal**: Deploy MCP servers with HTTP transport for customer access.

**Tasks**:
1. Add FastMCP HTTP server configuration
2. Implement OAuth/JWT authentication
3. Add rate limiting and quota management
4. Deploy to cloud infrastructure (AWS/GCP/Azure)
5. Create customer onboarding documentation
6. Test with external MCP client (Claude Desktop)

**Success Criteria**:
- [ ] MCP servers accessible via HTTPS
- [ ] Authentication working (API keys or OAuth)
- [ ] Rate limiting prevents abuse
- [ ] Claude Desktop can connect and use tools
- [ ] Customer documentation complete

**Estimated Time**: 20-30 hours (includes infrastructure setup)

**Files Created**:
- `server/mcp_http_server.py` (~300 lines)
- `server/auth.py` (~200 lines)
- `server/rate_limiter.py` (~150 lines)
- `docs/customer/MCP_INTEGRATION_GUIDE.md`
- `docs/customer/API_AUTHENTICATION.md`

**Infrastructure**:
- Docker containers for MCP servers
- Nginx reverse proxy with SSL
- Redis for rate limiting
- PostgreSQL for auth/quota tracking

---

### Phase 4: Data.gov Integration (Week 5)

**Goal**: Add Data.gov integration using existing MCP server.

**Tasks**:
1. Test datagov-mcp-server locally
2. Configure Deep Research to connect to Data.gov MCP server
3. Add Data.gov to tool discovery
4. Test combined searches (our integrations + Data.gov)
5. Document Data.gov integration in customer docs

**Success Criteria**:
- [ ] Deep Research can query Data.gov via MCP
- [ ] Results combined with our integrations
- [ ] No custom API integration code needed
- [ ] Demonstrates third-party MCP server usage

**Estimated Time**: 4-6 hours

**Files Modified**:
- `research/deep_research.py` (add Data.gov MCP server config)
- `config_default.yaml` (add Data.gov server settings)

---

## Testing Strategy

### Unit Tests
- Test each MCP wrapper individually
- Verify tool schema generation
- Test error handling

### Integration Tests
- Test MCP client with all wrapped tools
- Test Deep Research with MCP client
- Test mixing our tools with third-party MCP servers

### End-to-End Tests
- Test customer workflow: Claude Desktop → Our MCP servers → Gov APIs
- Test authentication and rate limiting
- Test error messages and debugging

### Performance Tests
- Compare MCP wrapper performance vs direct Python calls
- Measure HTTP transport overhead
- Test with 50+ concurrent clients

---

## Migration Path (Backward Compatibility)

### For Internal Use (CLI/Streamlit)

**Option A: No Migration Required**
- Continue using DatabaseIntegration directly
- No code changes needed
- Direct Python imports work as before

**Option B: Gradual Migration**
- Update apps to use MCP client (in-memory, no network)
- Benefits: Uniform interface, easier to add third-party tools
- Cost: Slight performance overhead (minimal with in-memory transport)

### For Deep Research

**Required Migration**: Deep Research MUST use MCP client to support third-party servers.

**Rollback Plan**: Keep `AdaptiveSearchEngine` as fallback if MCP client has issues.

---

## Risks and Mitigations

### Risk 1: Performance Overhead

**Risk**: MCP adds abstraction layer, may slow down searches
**Mitigation**: Use in-memory transport for internal use (no network overhead)
**Measurement**: Performance tests comparing direct vs MCP (Phase 1)

### Risk 2: Complexity

**Risk**: MCP adds architectural complexity
**Mitigation**: Keep DatabaseIntegration layer unchanged, MCP is thin wrapper
**Rollback**: Can remove MCP wrappers without touching core integrations

### Risk 3: Authentication/Security

**Risk**: HTTP deployment exposes APIs to internet
**Mitigation**: OAuth/JWT auth, rate limiting, quota management (Phase 3)
**Monitoring**: Track authentication failures, rate limit hits, suspicious usage

### Risk 4: Third-Party MCP Server Reliability

**Risk**: External MCP servers may be unreliable or change
**Mitigation**: Cache third-party tool schemas, implement fallbacks
**Monitoring**: Track third-party server uptime, timeout errors

### Risk 5: Customer Integration Burden

**Risk**: Customers may struggle with MCP client setup
**Mitigation**: Comprehensive documentation, example code, support
**Measurement**: Track support tickets, onboarding success rate

---

## Success Metrics

### Technical Metrics
- **Performance**: MCP wrapper overhead < 50ms per call
- **Reliability**: 99.9% uptime for HTTP MCP servers
- **Compatibility**: Works with Claude Desktop, Cursor IDE, custom clients

### Product Metrics
- **Customer Adoption**: X customers using MCP integration in first month
- **Tool Usage**: Average tools per customer query
- **Support Burden**: < 5% of customers require MCP integration support

### Business Metrics
- **Market Positioning**: Listed on MCP ecosystem page
- **Competitive Advantage**: Only MCP-native OSINT platform
- **Sales Enablement**: "Works with Claude" as selling point

---

## Related Documents

- **POC Results**: `tests/test_usajobs_mcp_poc.py` - USAJobs FastMCP refactor
- **Investigation**: `docs/DATAGOV_MCP_INTEGRATION_ANALYSIS.md` - Initial analysis (outdated conclusion)
- **MCP Specification**: https://modelcontextprotocol.io/specification/latest
- **FastMCP Docs**: https://github.com/jlowin/fastmcp

---

## Decision Log

### 2025-10-24: APPROVED - Adopt MCP with hybrid architecture

**Attendees**: Brian, Claude (AI assistant)

**Key Discussion Points**:
1. Initially skeptical of MCP value for CLI/Streamlit-only usage
2. Realized product strategy (selling access) makes MCP essential
3. Recognized third-party integration value (Data.gov server exists)
4. Decided on hybrid approach: keep DatabaseIntegration, add MCP wrappers

**Decision**: Proceed with 4-phase implementation plan.

**Next Steps**:
1. Archive FastMCP POC with lessons learned
2. Begin Phase 1: MCP wrappers for existing integrations
3. Update ROADMAP.md with MCP phases

---

## Appendix A: MCP vs Alternatives

### Why Not Custom REST API?

**Pros of REST**:
- Familiar technology
- Lots of tooling

**Cons of REST**:
- No AI-native features (tool discovery, schema validation)
- Customers must write custom integration
- Not aligned with industry standard (MCP adoption by OpenAI, Google)

### Why Not GraphQL?

**Pros of GraphQL**:
- Flexible querying
- Schema introspection

**Cons of GraphQL**:
- Not AI-native (no LLM tool calling built-in)
- More complex than needed
- No industry adoption for AI tool access

### Why Not Function Calling APIs?

**Pros**:
- OpenAI function calling exists

**Cons**:
- Vendor-specific (only works with OpenAI)
- No standard protocol
- MCP supersedes this approach

---

## Appendix B: FastMCP vs MCP Python SDK

We chose **FastMCP** over the official MCP Python SDK because:

1. **Simpler API**: Decorator-based (`@mcp.tool`) vs class-based
2. **Better Documentation**: FastMCP has clearer examples
3. **Faster Development**: Less boilerplate code
4. **Full Compatibility**: Implements MCP specification correctly
5. **Active Maintenance**: Regular updates, responsive maintainer

**Note**: Can switch to official SDK later if needed (MCP protocol is standard).

---

## Questions & Answers

**Q: Do we have to refactor all integrations?**
A: No. DatabaseIntegration classes stay unchanged. We add thin MCP wrappers.

**Q: What if MCP doesn't work out?**
A: Remove wrapper layer, continue using DatabaseIntegration directly. No core changes needed.

**Q: How do customers authenticate?**
A: Phase 3 implements OAuth/JWT. Customers get API keys or OAuth tokens.

**Q: Can we still use CLI/Streamlit without MCP?**
A: Yes. Internal use can continue with direct DatabaseIntegration imports.

**Q: What about the Data.gov MCP server?**
A: Phase 4 adds it. Deep Research can use it alongside our integrations.

**Q: Is this a lot of work?**
A: Phase 1: 8-12 hours. Phase 2: 12-16 hours. Total: ~30-40 hours core work, ~50-60 hours with HTTP deployment.

---

**END OF DOCUMENT**

Last Updated: 2025-10-24
Status: APPROVED - Ready for Phase 1 implementation
Next Review: After Phase 1 completion
