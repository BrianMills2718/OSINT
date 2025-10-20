# Discord Integration Plan

**Date**: 2025-10-19
**Purpose**: Integrate Discord search capability into the SigInt investigative platform
**Status**: PLANNING

---

## Executive Summary

Discord represents a **major intelligence source** for investigative journalism:
- **Live discussions** happening in real-time on sensitive topics
- **Closed communities** (Bellingcat, Project OWL) with expert analysis
- **Historical data** going back years with searchable message archives
- **No official API** for message search - requires scraping exported data

**Value Proposition**: Add Discord as a searchable data source alongside government databases (SAM.gov, DVIDS, Federal Register, etc.) to enable cross-source investigative queries.

---

## Current State Analysis

### What We Have Built (Discord Side)

**Location**: `/home/brian/sam_gov/experiments/discord/`

**Components**:
1. **discord_backfill.py** - Automated historical scraper
   - Exports Discord servers in 7-day chunks
   - Resume capability (tracks progress in JSON)
   - Retries failed chunks automatically
   - Working backwards from present to configurable earliest date

2. **discord_server_manager.py** - Multi-server management
   - Tracks multiple servers (Bellingcat, Project OWL, etc.)
   - Manages tokens and server configs
   - Incremental daily updates (--after flag)

3. **strip_discord_json.py** - Bloat removal
   - Reduces export size by 93% (665MB → 46MB)
   - Keeps: message content, author, timestamp, attachments
   - Removes: avatars, role details, user discriminators

**Exported Data**:
- **Format**: JSON files per channel per time period
- **Location**: `/home/brian/sam_gov/data/exports/`
- **Current Size**: ~16 MB (Bellingcat, 479 files, 35 days of history)
- **Structure**:
  ```json
  {
    "guild": {"id": "...", "name": "Bellingcat"},
    "channel": {"id": "...", "name": "announcements", "category": "Server Info"},
    "messages": [
      {
        "id": "...",
        "timestamp": "2025-10-18T12:00:00-07:00",
        "content": "Message text here...",
        "author": {"id": "...", "name": "username", "nickname": "..."},
        "attachments": [],
        "embeds": []
      }
    ]
  }
  ```

### What We Have Built (Platform Side)

**Database Integration Architecture**:
- **Base Class**: `core/database_integration_base.py`
  - `DatabaseCategory` enum (includes `SOCIAL_GENERAL` for Discord)
  - `DatabaseIntegration` abstract class with 3 methods:
    1. `is_relevant()` - Fast keyword check
    2. `generate_query()` - LLM generates query params
    3. `execute_search()` - API call, returns `QueryResult`

**Existing Social Categories**:
- `SOCIAL_REDDIT` - Not implemented
- `SOCIAL_TWITTER` - Not implemented
- `SOCIAL_TELEGRAM` - Not implemented
- `SOCIAL_GENERAL` - Discord would go here

**Integration Registry**:
- Government sources: SAM.gov, DVIDS, USAJobs, ClearanceJobs, Federal Register
- Social sources: **None yet** (Discord would be first)

---

## Architecture Design

### Discord Integration Class

**File**: `integrations/social/discord_integration.py`

**Implementation Strategy**:
Since Discord has no real-time API we can use, this integration will **search local exported JSON files** (offline search).

```python
class DiscordIntegration(DatabaseIntegration):
    """
    Discord integration that searches exported message history.

    Unlike other integrations, this searches local JSON files rather than
    calling an external API. Discord exports are generated via the backfill
    system and stored in data/exports/.
    """

    def __init__(self, exports_dir: str = "data/exports"):
        self.exports_dir = Path(exports_dir)
        self._index = None  # Lazy-loaded message index

    @property
    def metadata(self) -> DatabaseMetadata:
        return DatabaseMetadata(
            name="Discord",
            id="discord",
            category=DatabaseCategory.SOCIAL_GENERAL,
            requires_api_key=False,  # Searches local exports
            cost_per_query_estimate=0.0,  # Free (local search)
            typical_response_time=0.5,  # Fast (local files)
            rate_limit_daily=None,  # No limits (local)
            description="Discord community discussions (Bellingcat, Project OWL, etc.)"
        )

    async def is_relevant(self, research_question: str) -> bool:
        """
        Quick check: Is this question about something Discord would have?

        Discord is relevant for:
        - OSINT discussions (Bellingcat)
        - Geopolitical analysis (Project OWL)
        - Real-time breaking news reactions
        - Expert community discussions

        NOT relevant for:
        - Government contracts (use SAM.gov)
        - Official government statements (use Federal Register)
        - Jobs (use ClearanceJobs/USAJobs)
        """
        # Always return True for MVP - let LLM decide in generate_query()
        return True

    async def generate_query(self, research_question: str) -> Optional[Dict]:
        """
        Use LLM to extract keywords for Discord message search.

        Returns:
          {
            "keywords": ["keyword1", "keyword2", ...],
            "servers": ["bellingcat", "project_owl"],  # Optional filter
            "date_range": {  # Optional
              "after": "2024-01-01",
              "before": "2025-10-19"
            }
          }
        """
        # LLM prompt to extract search keywords
        # Use llm_utils.acompletion() with JSON schema
        pass

    async def execute_search(self, query_params: Dict, api_key: Optional[str] = None, limit: int = 10) -> QueryResult:
        """
        Search local Discord exports for messages matching keywords.

        Algorithm:
        1. Load all exported JSON files from data/exports/
        2. Filter by servers if specified in query_params
        3. Filter by date_range if specified
        4. Search message content for keywords (case-insensitive)
        5. Rank by relevance (keyword density, recency)
        6. Return top N results
        """
        pass

    def _build_index(self):
        """
        Build in-memory index of all Discord messages.

        Format:
        {
          "bellingcat": {
            "announcements": [
              {"message_id": "...", "timestamp": "...", "content": "...", "author": "..."},
              ...
            ]
          }
        }

        This runs once on first query, then cached for subsequent searches.
        """
        pass

    def _search_messages(self, keywords: List[str], servers: Optional[List[str]] = None,
                        date_range: Optional[Dict] = None) -> List[Dict]:
        """
        Search indexed messages for keywords.

        Returns list of matching messages with:
        - message content
        - author
        - timestamp
        - server + channel context
        - match score (0-1)
        """
        pass
```

### Search Algorithm Options

**Option A: Simple Keyword Matching** (MVP)
```python
def _search_messages(keywords):
    matches = []
    for file in glob("data/exports/*.json"):
        data = json.load(file)
        for msg in data["messages"]:
            if any(kw.lower() in msg["content"].lower() for kw in keywords):
                matches.append({
                    "content": msg["content"],
                    "author": msg["author"]["name"],
                    "timestamp": msg["timestamp"],
                    "server": data["guild"]["name"],
                    "channel": data["channel"]["name"],
                    "score": calculate_score(msg, keywords)
                })
    return sorted(matches, key=lambda x: x["score"], reverse=True)
```

**Option B: Full-Text Index** (Future optimization)
- Use SQLite FTS5 or Elasticsearch
- Index all messages on startup or background task
- Much faster for large datasets (1M+ messages)
- Supports advanced queries (phrases, proximity, fuzzy)

**Option C: Hybrid** (Recommended)
- Start with Option A (simple keyword matching)
- Add SQLite FTS5 when message count > 100k
- Keep same API, swap implementation

### Integration with Existing System

**1. Register Discord Integration**

**File**: `integrations/registry.py` (or similar)

```python
from integrations.social.discord_integration import DiscordIntegration

def get_all_integrations():
    return [
        # Government sources
        SAMIntegration(),
        DVIDSIntegration(),
        USAJobsIntegration(),
        ClearanceJobsIntegration(),
        FederalRegisterIntegration(),

        # Social sources (NEW)
        DiscordIntegration(),
    ]
```

**2. Add to Agentic Executor**

No changes needed! The agentic executor already:
- Calls `is_relevant()` on all registered integrations
- Calls `generate_query()` via LLM for relevant ones
- Calls `execute_search()` in parallel
- Aggregates results

**3. Add to Boolean Monitors**

Discord can be added as a source in monitor YAML configs:

```yaml
name: "Ukraine OSINT Monitor"
keywords:
  - "Ukraine"
  - "Kyiv"
  - "Russian invasion"
sources:
  - dvids
  - federal_register
  - discord  # NEW - searches Bellingcat Discord
schedule: daily
alerts:
  email: brianmills2718@gmail.com
```

**4. Add to Streamlit UI**

Add new tab: `apps/discord_search.py`

```python
import streamlit as st
from integrations.social.discord_integration import DiscordIntegration

st.title("Discord Search")
query = st.text_input("Search Discord messages")

if query:
    integration = DiscordIntegration()
    results = await integration.execute_search({"keywords": [query]})

    for r in results.results:
        st.write(f"**{r['author']}** in #{r['channel']} ({r['server']})")
        st.write(r['content'])
        st.caption(r['timestamp'])
```

---

## Implementation Phases

### Phase A: Core Integration (Week 1)

**Deliverables**:
- [ ] `integrations/social/discord_integration.py` created
- [ ] Simple keyword search working (no index)
- [ ] Returns QueryResult in standard format
- [ ] Registered with platform
- [ ] Tested via CLI: `python3 apps/ai_research.py "ukraine"`

**Success Criteria**:
- Search query "ukraine" returns Discord messages from Bellingcat exports
- Results include server, channel, author, timestamp
- Integration works alongside existing sources (parallel execution)

**Effort**: 8-12 hours

### Phase B: Optimization (Week 2)

**Deliverables**:
- [ ] SQLite FTS5 index for fast search
- [ ] Background indexing task (rebuilds index when new exports added)
- [ ] Advanced query support (phrases, date filters)
- [ ] Result ranking by relevance

**Success Criteria**:
- Search returns in < 100ms (was ~500ms)
- Phrase search works: `"special operation"`
- Date filtering works: `after:2024-01-01`

**Effort**: 10-15 hours

### Phase C: Production Features (Week 3)

**Deliverables**:
- [ ] Streamlit UI tab for Discord search
- [ ] Discord added to Boolean monitors
- [ ] Auto-indexing of new exports (backfill integration)
- [ ] Export management (archive old exports, manage disk space)

**Success Criteria**:
- User can search Discord via web UI
- Boolean monitors include Discord results in alerts
- New Discord exports automatically indexed

**Effort**: 12-18 hours

---

## Data Management

### Storage Strategy

**Current**:
- Raw exports: `/home/brian/sam_gov/data/exports/` (16 MB, growing)
- Stripped exports: `/home/brian/sam_gov/exports_stripped/` (if we use strip tool)

**Proposed**:
- **Raw exports**: Keep for 90 days, then archive to S3/cold storage
- **Indexed data**: SQLite FTS5 database (`data/discord_index.db`)
  - Contains: message content, author, timestamp, server, channel
  - Omits: avatars, role data, edit history
  - Size estimate: ~10-20% of raw exports
- **Backfill state**: `experiments/discord/discord_backfill_state.json` (tracks progress)

**Disk Usage Projection**:
- Bellingcat (5 years): ~16 MB × (5 years / 35 days) = ~830 MB raw
- Project OWL (5 years): Estimate ~1 GB raw
- Total (2-3 servers): ~2-3 GB raw, ~300-500 MB indexed

### Automatic Backfill Integration

**Goal**: New Discord exports are automatically indexed for search

```python
# monitoring/discord_sync.py
class DiscordSyncTask:
    """
    Background task that:
    1. Runs discord_backfill.py daily for configured servers
    2. Detects new export files
    3. Indexes new messages into SQLite FTS5
    4. Archives old raw exports to S3
    """

    async def sync_all_servers(self):
        # Run daily backfill for each server
        for server in get_discord_servers():
            run_backfill(server.id, since=server.last_sync_date)

        # Index new exports
        new_files = find_new_exports(since=last_index_time)
        index_exports(new_files)

        # Archive old exports
        archive_exports(older_than_days=90)
```

**Scheduler Integration**:
Add to `monitoring/scheduler.py`:
```python
scheduler.add_job(
    DiscordSyncTask().sync_all_servers,
    trigger="cron",
    hour=2,  # 2 AM daily
    id="discord_sync"
)
```

---

## Testing Strategy

### Unit Tests

```python
# tests/test_discord_integration.py

async def test_keyword_search():
    """Test basic keyword search returns relevant messages."""
    integration = DiscordIntegration()
    result = await integration.execute_search({"keywords": ["ukraine"]})

    assert result.success
    assert result.total > 0
    assert all("ukraine" in r["content"].lower() for r in result.results)

async def test_date_filtering():
    """Test date range filtering works."""
    result = await integration.execute_search({
        "keywords": ["ukraine"],
        "date_range": {"after": "2024-01-01", "before": "2024-12-31"}
    })

    for r in result.results:
        timestamp = datetime.fromisoformat(r["timestamp"])
        assert datetime(2024, 1, 1) <= timestamp <= datetime(2024, 12, 31)

async def test_server_filtering():
    """Test server-specific searches."""
    result = await integration.execute_search({
        "keywords": ["osint"],
        "servers": ["bellingcat"]
    })

    assert all(r["server"] == "Bellingcat" for r in result.results)
```

### Integration Tests

```python
# tests/test_discord_end_to_end.py

async def test_agentic_executor_includes_discord():
    """Test Discord results appear in multi-source queries."""
    executor = AgenticExecutor()
    results = await executor.research("What are experts saying about Ukraine?")

    sources = [r.source for r in results]
    assert "Discord" in sources  # Discord should be queried

async def test_boolean_monitor_with_discord():
    """Test Boolean monitor can search Discord."""
    monitor = BooleanMonitor("test_monitor_with_discord.yaml")
    await monitor.run()

    # Check that Discord was searched
    assert any(r["source"] == "Discord" for r in monitor.latest_results)
```

---

## Roadmap Alignment

### Where Discord Fits

**Phase 3: Social Media Integration** (Current roadmap target: Weeks 6-7)
- Original plan: Reddit, 4chan, Twitter
- **Updated plan**: Discord (first), then Reddit, 4chan, Twitter

**Rationale for Priority**:
1. **Data already available**: Bellingcat exports complete, no new scraping needed
2. **High value**: Bellingcat/Project OWL are top-tier OSINT sources
3. **Low complexity**: Local file search vs API integration
4. **Faster MVP**: Can ship in 1-2 weeks vs 4-6 weeks for Reddit/Twitter

### Updated Phase 3 Plan

**Week 1-2**: Discord Integration (Phase A + B)
- Core integration working
- Fast indexed search
- Added to platform

**Week 3-4**: Reddit Integration
- PRAW library
- Subreddit search
- Added to monitors

**Week 5-6**: Optional (Twitter or 4chan)
- Evaluate need based on Discord/Reddit usage
- Twitter ($100/month) vs 4chan (free)

---

## Risks & Mitigations

### Risk 1: Large Data Volume

**Risk**: Discord exports could grow to 10+ GB for active servers
**Impact**: Slow searches, high disk usage, expensive S3 storage
**Mitigation**:
- Implement FTS5 indexing early (Phase B)
- Archive old raw exports to S3 (keep index only)
- Add server/channel filtering to reduce search space
**Probability**: HIGH
**Severity**: MEDIUM

### Risk 2: Stale Data

**Risk**: Discord search only finds old messages if backfill not running
**Impact**: Missing recent discussions, alerts delayed
**Mitigation**:
- Daily automated backfill via scheduler
- Monitor backfill health (alert if no new data in 48h)
- Manual trigger option in UI
**Probability**: MEDIUM
**Severity**: HIGH

### Risk 3: Token Expiration

**Risk**: Discord token expires, backfill stops working
**Impact**: No new Discord data, search becomes stale
**Mitigation**:
- Document token refresh process
- Add token validation check to scheduler
- Alert on repeated backfill failures
**Probability**: MEDIUM
**Severity**: HIGH

### Risk 4: Relevance Quality

**Risk**: Discord results too noisy (off-topic chat, memes)
**Impact**: Poor signal-to-noise ratio, user frustration
**Mitigation**:
- Add LLM relevance scoring (like Boolean monitors)
- Filter by channel (exclude #off-topic, #memes)
- Threshold on message length (skip one-word replies)
**Probability**: MEDIUM
**Severity**: MEDIUM

---

## Success Metrics

### Phase A (Core Integration)

**Technical**:
- [ ] Search returns results in < 1 second
- [ ] Results match keyword query accurately (100% precision on manual sample)
- [ ] Integration passes all unit tests
- [ ] Works in parallel with other sources (no slowdown)

**User-Facing**:
- [ ] Query "ukraine intelligence" returns relevant Discord messages
- [ ] Results show server/channel context
- [ ] User can click through to see full message thread (future enhancement)

### Phase B (Optimization)

**Performance**:
- [ ] Search returns results in < 100ms (10x faster than Phase A)
- [ ] Indexing completes in < 5 minutes for 1 GB of exports
- [ ] Phrase search works correctly

### Phase C (Production)

**Adoption**:
- [ ] At least 1 Boolean monitor uses Discord as a source
- [ ] Discord results appear in 10+ email alerts
- [ ] User searches Discord via Streamlit UI at least weekly

**Reliability**:
- [ ] Daily backfill succeeds 95% of the time
- [ ] Index stays up-to-date (< 24h lag)
- [ ] No user-reported bugs for 2 weeks

---

## Next Actions

### Immediate (This Session)

1. **Create directory structure**:
   ```bash
   mkdir -p integrations/social
   touch integrations/social/__init__.py
   ```

2. **Create skeleton** (`integrations/social/discord_integration.py`):
   - Implement `DiscordIntegration` class
   - Stub out all 3 required methods
   - Add basic metadata

3. **Write tests** (`tests/test_discord_integration.py`):
   - Test imports work
   - Test metadata returns correctly

### Short-term (Next Session)

4. **Implement simple keyword search** (Phase A):
   - Load JSON files from `data/exports/`
   - Search message content for keywords
   - Return top 10 matches

5. **Test end-to-end**:
   - Add Discord to registry
   - Run: `python3 apps/ai_research.py "ukraine"`
   - Verify Discord results appear alongside other sources

6. **Update documentation**:
   - Add Discord to STATUS.md
   - Update ROADMAP.md (Phase 3 now starts with Discord)
   - Update CLAUDE.md TEMPORARY section

### Medium-term (Week 2)

7. **Implement FTS5 indexing** (Phase B)
8. **Add to Boolean monitors**
9. **Build Streamlit UI tab**

---

## Open Questions

1. **Server Selection**: Should Discord search all exported servers or allow filtering?
   - **Recommendation**: Search all by default, add server filter as optional param

2. **Message Context**: Should results include thread context (replies, quoted messages)?
   - **Recommendation**: Phase A: just message content. Phase B: add thread context

3. **Real-time vs Batch**: Should we support real-time Discord monitoring (via bot)?
   - **Recommendation**: Defer to Phase 4+. Batch exports are sufficient for now.

4. **Multi-language**: Do we need to support non-English Discord messages?
   - **Recommendation**: Not needed yet (Bellingcat/Project OWL are English-dominant)

5. **Access Control**: Should some Discord servers be restricted (admin-only search)?
   - **Recommendation**: Not needed for MVP (single-user tool). Add in Phase 5 (team collaboration)

---

## Appendix: File Locations

**Discord Tools** (already built):
- `experiments/discord/discord_backfill.py` - Historical scraper
- `experiments/discord/discord_server_manager.py` - Multi-server management
- `experiments/discord/strip_discord_json.py` - Bloat removal
- `experiments/discord/discord_servers.json` - Server registry
- `experiments/discord/discord_backfill_state.json` - Backfill progress

**Discord Data**:
- `data/exports/*.json` - Raw Discord exports (479 files, 16 MB)
- `data/logs/backfill_*.log` - Backfill logs

**Integration Code** (to be built):
- `integrations/social/discord_integration.py` - Main integration class
- `integrations/social/__init__.py` - Module init
- `tests/test_discord_integration.py` - Unit tests
- `apps/discord_search.py` - Streamlit UI tab (Phase C)
- `monitoring/discord_sync.py` - Auto-indexing task (Phase C)

**Platform Files** (already exist):
- `core/database_integration_base.py` - Base class Discord will extend
- `integrations/registry.py` - Where Discord gets registered
- `monitoring/boolean_monitor.py` - Can use Discord as source
- `apps/ai_research.py` - CLI that will include Discord results
- `apps/unified_search_app.py` - Streamlit UI that will add Discord tab

---

## Conclusion

**Recommendation**: Proceed with Discord integration as **Phase 3A** (before Reddit/Twitter)

**Why Now**:
- Data already available (Bellingcat exports complete)
- High-value source (top-tier OSINT community)
- Low complexity (local file search, no API integration)
- Fast to ship (1-2 weeks vs 4-6 weeks for full Phase 3)

**Why Not Later**:
- Discord data is time-sensitive (want to search recent discussions)
- Other social sources (Reddit, Twitter) require API setup/costs
- Discord validates social media integration pattern for other sources

**Next Step**: User decision on priority (Discord now vs continue Phase 1 deployment vs begin Phase 2 UI)
