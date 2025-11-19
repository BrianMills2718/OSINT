# Next Steps Investigation - 2025-11-18

**Purpose**: Thorough investigation of potential next tasks, documenting uncertainties and concerns

**Current State**:
- Phase 3C complete and production validated (2 artifacts)
- Root directory cleanup complete (40 → 33 items)
- feature/jinja2-prompts branch clean, 87 commits ahead of master
- All entry point smoke tests passing

---

## Option 1: Merge feature/jinja2-prompts to master

### What This Involves

**Branch Comparison**:
- feature/jinja2-prompts: 87 commits ahead of master
- 233 files changed
- Master branch last updated: 2025-10-22 (Query syntax testing for SAM.gov/USAJobs)
- Feature branch last updated: 2025-11-18 (Root cleanup + Phase 3C validation)

**Major Changes in Feature Branch** (from git diff):
- ✅ Phase 3C implementation (hypothesis generation + sequential coverage assessment)
- ✅ Phase 3B implementation (parallel hypothesis execution)
- ✅ Phase 3A implementation (LLM hypothesis generation)
- ✅ Jinja2 migration (all prompts migrated to templates)
- ✅ Config migration (deep_research.py reads config.yaml)
- ✅ Infrastructure cleanup (wiki extraction, POC removal)
- ✅ New test suite (test_phase3c_validation.py, test_entry_points.py)
- ✅ Comprehensive documentation (Phase 3A/3B/3C validation docs)

### Uncertainties and Concerns

**UNCERTAINTY #1**: Master branch stability
- **Question**: Is master branch currently working/stable?
- **Risk**: Merging 87 commits might introduce regressions
- **Investigation needed**: Test master branch independently before merge
- **Action**: Run smoke tests on master branch first

**UNCERTAINTY #2**: Merge conflicts
- **Question**: How many merge conflicts will there be?
- **Risk**: Large divergence (87 commits) likely has conflicts
- **Investigation needed**: Run test merge to see conflict count
- **Action**: `git merge --no-commit --no-ff master` to preview conflicts

**UNCERTAINTY #3**: Breaking changes
- **Question**: Does feature branch break anything that works on master?
- **Risk**: Config migration, prompt migration might affect existing workflows
- **Investigation needed**: Cross-test both branches
- **Concern**: Master has query syntax fixes (Reddit, DVIDS) that feature branch might not have

**UNCERTAINTY #4**: Production deployment impact
- **Question**: Will merge affect deployed Streamlit app?
- **Risk**: ROADMAP says "Streamlit deployed to cloud" but unclear if using master or feature branch
- **Investigation needed**: Check which branch is currently deployed
- **Concern**: Merge might break production deployment

**CONCERN #1**: Large diff makes review difficult
- 233 files changed is substantial
- Hard to verify all changes are intentional
- Recommend: Create detailed changelog before merge

**CONCERN #2**: Documentation divergence
- CLAUDE.md drastically different between branches
- Master: Full detailed temporary section
- Feature: Condensed, updated with Phase 3C completion
- Need to preserve important context from both

### Recommendation

**DO NOT MERGE YET** - Too many uncertainties

**Safer path**:
1. Test master branch independently (smoke tests)
2. Run test merge to preview conflicts
3. Create detailed changelog of all 233 changed files
4. Cross-test both branches for regressions
5. Verify production deployment status
6. THEN merge with full understanding

---

## Option 2: Start Phase 4 (Analysis Engine)

### What This Involves

**From ROADMAP.md**:
- Build AnalysisEngine class
- Result summarization (3 paragraphs + key findings)
- Entity extraction (people, orgs, locations, events)
- Timeline generation (chronological events)
- Theme identification (recurring topics)
- Add UI buttons in Streamlit

**Estimated Effort**: 30-40 hours, Medium complexity

### Uncertainties and Concerns

**UNCERTAINTY #1**: Is Phase 4 already partially implemented?
- **Question**: Deep Research already does entity extraction and reporting
- **Evidence**: research/deep_research.py has entity tracking, report_synthesis.j2 generates markdown reports
- **Risk**: Might be rebuilding existing functionality
- **Investigation needed**: Compare Phase 4 requirements to existing deep_research.py features
- **Concern**: Unclear what "AnalysisEngine" adds beyond deep_research.py

**UNCERTAINTY #2**: Where does AnalysisEngine fit?
- **Question**: Separate module or extension of deep_research.py?
- **Question**: Does it analyze Quick Search results, Deep Research results, or both?
- **Risk**: Architecture unclear, might create redundant code
- **Investigation needed**: Define scope and integration points

**UNCERTAINTY #3**: UI integration unclear
- **Question**: "Summarize results" button - which tab?
- **Evidence**: Deep Research tab already shows final report with entities
- **Question**: Is this for Quick Search tab (ai_research.py)?
- **Risk**: Might duplicate Deep Research functionality

**CONCERN #1**: ROADMAP is outdated
- Last updated: 2025-11-18 (today)
- But Phase 4 description written before Phase 3C existed
- Phase 4 might not account for new Phase 3C capabilities
- **Evidence**: Phase 4 says "Entity extraction" but Phase 3C already does this comprehensively

**CONCERN #2**: Deep Research already covers most Phase 4 goals
- ✅ Summarization: report_synthesis.j2 creates comprehensive markdown reports
- ✅ Entity extraction: research/deep_research.py tracks entities across tasks
- ✅ Timeline generation: Phase 3C includes timeline in reports (line 34-40 of report_synthesis.j2)
- ✅ Theme identification: "Key Findings" and "Detailed Analysis" sections
- ❓ Only gap: Interactive UI buttons for ad-hoc analysis (not pre-generated)

**CONCERN #3**: Dependencies unclear
- ROADMAP says "Phase 2 complete (UI deployed)" as dependency
- But Phase 2 is only "PARTIALLY COMPLETE"
- Deep Research tab has known issue (needs Brave Search)
- Should we fix Phase 2 blocker before starting Phase 4?

### Recommendation

**DO NOT START PHASE 4 YET** - Too much overlap with existing features

**Better path**:
1. Audit deep_research.py and report_synthesis.j2 to document what's already built
2. Compare against Phase 4 requirements
3. Define UNIQUE value Phase 4 adds (likely: interactive analysis UI, not pre-generated reports)
4. Update ROADMAP Phase 4 to reflect Phase 3C capabilities
5. THEN decide if Phase 4 is still needed or redundant

---

## Option 3: Fix Streamlit Deep Research (Add Brave Search)

### What This Involves

**From ROADMAP.md**:
- BLOCKER: "Deep Research returns results ❌ (0 results for classified topics)"
- Root cause: Government DBs don't have classified/sensitive documents
- Solution: Add Brave Search integration for web search
- Status: Enhanced error logging deployed, fix in progress

**Current Evidence**:
- apps/deep_research_tab.py exists (511 lines)
- Uses research/deep_research.py (SimpleDeepResearch)
- Deep Research mentions "Web search integration (Brave Search for open web results)" in UI (line 72)

### Uncertainties and Concerns

**UNCERTAINTY #1**: Is Brave Search already integrated?
- **Question**: Deep Research tab says "Web search integration (Brave Search)" - is this working?
- **Evidence**: Line 72 of apps/deep_research_tab.py mentions Brave Search
- **Investigation needed**: Check if research/deep_research.py already has Brave integration
- **Risk**: Might already be fixed, just needs testing

**UNCERTAINTY #2**: What causes "0 results for classified topics"?
- **Question**: Is problem missing Brave Search OR query formulation?
- **Evidence**: ROADMAP says "Government DBs don't have classified/sensitive documents"
- **Question**: Would Brave Search actually return better results for "JSOC and CIA Title 50 operations"?
- **Concern**: Might be unrealistic expectations, not technical blocker

**UNCERTAINTY #3**: Is this a real blocker or user education issue?
- **Question**: Should Deep Research work for all topics or acknowledge limitations?
- **Evidence**: Government databases factually don't contain classified operational details
- **Question**: Would Brave Search return quality investigative journalism on classified programs?
- **Concern**: Might set wrong expectations - even web search won't reveal actual classified ops

**CONCERN #1**: API key requirements
- Brave Search API requires API key
- Unclear if free tier exists
- User would need to configure BRAVE_API_KEY
- Adds deployment complexity

**CONCERN #2**: ROADMAP diagnosis might be wrong
- Says "Deep Research: [FAIL] - 0 tasks executed, 4 tasks failed"
- "0 tasks executed" sounds like initialization error, not missing web search
- Might be config issue, not feature gap
- Need to reproduce error first

**CONCERN #3**: Feature branch might already have fix
- Master branch diagnosis from 2025-10-22
- Feature branch has 87 commits since then
- Brave Search integration might already be in feature branch
- Investigation needed: Check if research/deep_research.py has Brave integration

### Recommendation

**INVESTIGATE FIRST, DON'T BUILD YET**

**Investigation plan**:
1. Check if research/deep_research.py already has Brave Search integration
2. Reproduce "0 tasks executed" error on current feature branch
3. Test Deep Research tab with simple query (not classified topics)
4. If working: Update ROADMAP to remove blocker
5. If broken: Diagnose actual root cause (might not be Brave Search)

---

## Option 4: Add More Social Integrations (Reddit, 4chan, Twitter)

### What This Involves

**From ROADMAP Phase 3**:
- Reddit adapter (PRAW library) - subreddit search, post/comment tracking
- 4chan adapter (JSON API) - board monitoring, thread tracking
- Twitter adapter (optional, $100/month) - keyword search, timeline tracking
- Add social sources to Boolean monitors
- Estimated: 30-40 hours remaining

### Uncertainties and Concerns

**UNCERTAINTY #1**: Which integrations already exist?
- **Evidence**: experiments/reddit/reddit_daily_scrape.py exists (270 lines)
- **Evidence**: Master branch has Reddit integration fixes (commit c049e6f, 0961851)
- **Question**: Is Reddit adapter already built, just not registered?
- **Investigation needed**: Check integrations/social/ directory for reddit_integration.py

**UNCERTAINTY #2**: Do we have Reddit API credentials?
- Reddit API requires OAuth credentials
- Unclear if .env has REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET
- Need to verify before starting implementation

**UNCERTAINTY #3**: What's the use case priority?
- **Question**: Are social media integrations high priority?
- **Evidence**: User wanted "Discord scraping to work daily" in cleanup conversation
- **Question**: Is Reddit/4chan/Twitter more important than fixing Deep Research or merging feature branch?
- **Concern**: Might be lower priority than completing existing work

**CONCERN #1**: experiments/ already has working Reddit scraper
- experiments/reddit/reddit_daily_scrape.py (270 lines)
- Follows Codex recommendations (1-2s rate limiting)
- Might just need to integrate into integrations/social/
- Risk: Rebuilding what already exists

**CONCERN #2**: Twitter cost unclear
- $100/month for Basic tier (10k tweets/month)
- ROADMAP says "optional, budget-dependent"
- Need user approval before starting Twitter integration
- Might want to do Reddit/4chan first (free)

**CONCERN #3**: 4chan technical complexity
- 4chan has aggressive rate limiting
- Boards are ephemeral (threads 404 quickly)
- Might need archival system, not just search integration
- Complexity might exceed estimated 30-40 hours

### Recommendation

**DO NOT START SOCIAL INTEGRATIONS YET**

**Better path**:
1. Audit experiments/ directory for existing scrapers
2. Check if Reddit integration already exists (check master branch commits)
3. Verify API credentials availability (.env)
4. Ask user for priority: Social integrations vs. feature branch merge vs. Deep Research fix
5. THEN start with highest priority item (likely Reddit, since scraper exists)

---

## Option 5: Something Else

### Potential Alternatives

**Alternative 1: Test and validate feature branch thoroughly**
- Run comprehensive test suite
- Test all integrations E2E
- Verify Phase 3C production readiness
- Document any limitations found
- **Benefit**: Ensures quality before merge

**Alternative 2: Update ROADMAP to reflect current state**
- ROADMAP says "Phase 3: Social Media Integration (Weeks 6-7)"
- But Phase 3 now includes Phase 3A/3B/3C (hypothesis generation)
- ROADMAP might confuse future developers
- **Benefit**: Accurate project documentation

**Alternative 3: Fix known issues**
- SAM.gov quota handling (recently added)
- Pydantic/LiteLLM warnings (cosmetic, deferred)
- Config migration edge cases
- **Benefit**: Polish existing features

**Alternative 4: Create user documentation**
- How to use Deep Research
- How to configure monitors
- How to add new integrations
- **Benefit**: Enables user independence

---

## FINAL RECOMMENDATIONS

### Immediate Next Steps (Prioritized)

**1. INVESTIGATE CURRENT STATE (1-2 hours)**
- [ ] Test master branch smoke tests
- [ ] Check if research/deep_research.py has Brave Search
- [ ] Check if Reddit integration exists in master
- [ ] Verify production deployment status (which branch?)
- [ ] Run test merge to preview conflicts

**2. CHOOSE PATH BASED ON INVESTIGATION**

**Path A: If feature branch is stable and master is testable**
→ Create detailed merge plan with changelog
→ Test merge in separate branch first
→ Get user approval before merging to master

**Path B: If Deep Research is actually broken**
→ Reproduce error
→ Diagnose root cause
→ Fix (might not be Brave Search)

**Path C: If Reddit integration is mostly done**
→ Complete Reddit integration
→ Add to registry
→ Test E2E

**Path D: If none of above are clear**
→ Ask user for priority guidance
→ Focus on highest value task

### What NOT to Do

❌ **DO NOT merge feature branch to master without investigation**
- Too many unknowns, too much risk

❌ **DO NOT start Phase 4 without auditing existing features**
- Likely duplicates Phase 3C capabilities

❌ **DO NOT add Brave Search without reproducing the error**
- Might be wrong diagnosis

❌ **DO NOT start Twitter integration without user approval**
- Costs $100/month, need budget confirmation

---

## QUESTIONS FOR USER

1. **Priority**: Which matters most right now?
   - Merging feature branch to master (consolidate work)
   - Fixing Streamlit Deep Research (if actually broken)
   - Adding social integrations (Reddit, 4chan)
   - Something else entirely

2. **Production**: Is Streamlit app deployed? Which branch is it using?

3. **Budget**: Is $100/month Twitter API approved or should we skip it?

4. **Merge**: Are you comfortable merging 87 commits / 233 files to master, or want more testing first?

5. **Phase 4**: Given Phase 3C already does entity extraction, timelines, and reports - what would Phase 4 add that's unique?

---

---

## CRITICAL FINDING: Integration Self-Rejection Without Reformulation

**Investigation Added**: 2025-11-18 17:30

### The Problem

**User's Question**:
> "if they failed we need tracability on why they failed, if they returned zero results we need to know whether our guidance on how to query is bad and in either case why the llm chose not to reformulate the query which it should be able to do"

### Root Cause Analysis

**Flow of Integration Rejection** (No Reformulation):

1. **Deep Research** selects sources via LLM using MCP tool descriptions
   - Example: SAM.gov selected 18/32 times for F-35 query
   - Selection reasoning: "SAM.gov can provide official contracting data related to F-35 sales"

2. **MCP Tool Wrapper** calls integration's `generate_query()` method
   - File: `integrations/mcp/government_mcp.py` (lines 133-144)
   - Code:
     ```python
     query_params = await integration.generate_query(research_question)

     if query_params is None:
         # LLM determined not relevant
         return {
             "success": False,
             "source": "SAM.gov",
             "total": 0,
             "results": [],
             "error": "Research question not relevant for SAM.gov"
         }
     ```

3. **Integration's `generate_query()`** uses LLM to assess relevance
   - File: `integrations/government/sam_integration.py` (lines 149-196)
   - Schema includes `"relevant": {"type": "boolean"}`
   - Code (lines 185-187):
     ```python
     # RELEVANCE FILTER RESTORED - Skip SAM for job-only queries
     if not result["relevant"]:
         return None
     ```

4. **Result**: Error returned to Deep Research WITHOUT reformulation attempt
   - Logged as: `{"success": false, "error": "Research question not relevant for SAM.gov"}`
   - No query retry, no reformulation, no fallback
   - Source effectively "dead" for this task

### Architectural Gap

**The Issue**: Integration rejection happens BEFORE any reformulation logic can trigger.

**Current Flow**:
```
Deep Research → MCP Tool → Integration generate_query() → [RELEVANCE CHECK]
                                                           ↓ (if false)
                                                         return None
                                                           ↓
                                         MCP Tool returns error
                                                           ↓
                                         Deep Research receives failure
                                                           ↓
                                         [NO REFORMULATION TRIGGERED]
```

**Where Reformulation COULD Happen** (but doesn't):
- Option A: Deep Research could detect `"error": "not relevant"` pattern and retry with reformulated query
- Option B: MCP tools could catch `None` from `generate_query()` and trigger reformulation
- Option C: Integrations could attempt reformulation before returning `None`

**Current Behavior**: NONE of the above are implemented.

### Evidence from F-35 Query

**SAM.gov Lifecycle** (from execution_log.jsonl):

```json
// Selection event (Task 0)
{
  "action_type": "source_selection",
  "selected_sources": ["Brave Search", "Twitter", "SAM.gov", "Reddit", "Discord"],
  "selection_reasoning": "SAM.gov can provide official contracting data related to F-35 sales..."
}

// API call event (Task 0)
{
  "action_type": "raw_response",
  "source_name": "SAM.gov",
  "success": false,
  "total_results": 0,
  "error": "Research question not relevant for SAM.gov"
}
```

**Result**: SAM.gov selected 18/32 times, returned 0 results every time, never reformulated.

### Affected Integrations

**All integrations with LLM-based relevance checks**:

1. **Government Sources** (`integrations/mcp/government_mcp.py`):
   - SAM.gov (line 143)
   - DVIDS (line 239)
   - USAJobs (line 337)
   - ClearanceJobs (line 431)
   - FBI Vault (line 526)

2. **Social Sources** (`integrations/mcp/social_mcp.py`):
   - Twitter (line 147)
   - Brave Search (line 251)
   - Discord (line 348)
   - Reddit (line 453)

**All follow the same pattern**: `if query_params is None → return error without reformulation`

### Impact Assessment

**Severity**: HIGH - Quality Gap

**Why This Matters**:
1. **False Negatives**: LLM may incorrectly reject relevant queries (too conservative)
2. **Wasted Selections**: Deep Research wastes LLM calls selecting sources that self-reject
3. **Lost Opportunities**: Reformulation could salvage rejected queries (e.g., broader keywords)
4. **No Traceability**: User can't see WHY integration rejected query or WHAT would make it relevant

**Example False Negative**:
- Query: "F-35 sales to Saudi Arabia"
- SAM.gov LLM thinks: "This is about arms sales, not contracting opportunities" → irrelevant
- Reality: SAM.gov COULD have results for "F-35 maintenance contracts" or "F-35 supply chain solicitations"
- Reformulation COULD try: "F-35 contracting opportunities" or "fighter aircraft contracts Saudi Arabia"

---

### DESIGN PHILOSOPHY VIOLATION

**From CLAUDE.md**:
> ❌ Hardcoded thresholds ("drop source after 2 failures")
> ❌ Fixed sampling limits (top 5, first 10, etc.)
> ❌ Rule-based decision trees ("if X then Y")
> ✅ Give LLM full context and ask for intelligent decisions
> ✅ Make ALL limits user-configurable (not hardcoded)
> ✅ Require LLM to justify all decisions with reasoning

**Current Issue**: Integration relevance checks are BINARY (relevant=true/false) with NO reasoning exposed and NO reformulation opportunity.

**Better Approach**: LLM should receive rejection reasoning and decide whether to reformulate, skip, or escalate.

---

### PROPOSED FIX OPTIONS

#### Option A: Deep Research Reformulation Loop (Least Invasive)

**Change**: Detect "not relevant" errors in Deep Research and trigger reformulation.

**Implementation**:
```python
# In research/deep_research.py (execute_task method)

if not result.success and "not relevant" in result.error:
    # Integration rejected query - attempt reformulation
    reformulated_query = await self._reformulate_for_integration(
        source_name=source_name,
        original_query=query,
        rejection_reason=result.error
    )

    if reformulated_query:
        # Retry with reformulated query
        result = await self._call_mcp_tool(tool_name, reformulated_query, limit)
```

**Pros**:
- No changes to integration layer
- Centralized reformulation logic
- Easy to add traceability (log rejection + reformulation)

**Cons**:
- Deep Research becomes more complex
- Reformulation happens AFTER initial LLM call (wastes one call)

---

#### Option B: MCP Tool Layer Reformulation (Medium Invasiveness)

**Change**: MCP tools detect `None` from `generate_query()` and trigger reformulation before returning error.

**Implementation**:
```python
# In integrations/mcp/government_mcp.py (search_sam function)

query_params = await integration.generate_query(research_question)

if query_params is None:
    # LLM rejected query - attempt reformulation
    reformulated_query_params = await reformulate_for_sam(research_question)

    if reformulated_query_params:
        query_params = reformulated_query_params
    else:
        # Reformulation failed - return error with reasoning
        return {
            "success": False,
            "source": "SAM.gov",
            "total": 0,
            "results": [],
            "error": "Research question not relevant for SAM.gov after reformulation attempt"
        }
```

**Pros**:
- Catches rejection closer to source
- Can use integration-specific reformulation strategies
- Deep Research doesn't need to know about reformulation

**Cons**:
- Need to implement reformulation for 9 MCP tools
- Reformulation logic duplicated across tools

---

#### Option C: Expose Rejection Reasoning (Most Transparent, RECOMMENDED)

**Change**: Instead of returning `None`, integrations return rejection reasoning. Let Deep Research LLM decide whether to reformulate.

**Implementation**:
```python
# In integrations/government/sam_integration.py (generate_query)

if not result["relevant"]:
    return {
        "relevant": False,
        "rejection_reason": result["reasoning"],  # LLM's explanation
        "suggested_reformulation": "Try broader keywords like 'contracting' instead of 'sales'"
    }

# In integrations/mcp/government_mcp.py (search_sam)

if not query_params.get("relevant", True):
    return {
        "success": False,
        "source": "SAM.gov",
        "total": 0,
        "results": [],
        "error": f"Not relevant: {query_params['rejection_reason']}",
        "metadata": {
            "rejection_reasoning": query_params["rejection_reason"],
            "suggested_reformulation": query_params.get("suggested_reformulation")
        }
    }

# In research/deep_research.py (execute_task)

if not result.success and result.metadata.get("rejection_reasoning"):
    # LLM decides: reformulate, skip, or try different source
    decision = await self._handle_rejection(
        source=source_name,
        query=query,
        rejection_reasoning=result.metadata["rejection_reasoning"],
        suggestion=result.metadata.get("suggested_reformulation")
    )
```

**Pros**:
- Maximum transparency (user sees WHY rejected)
- LLM makes intelligent decision (not hardcoded reformulation rules)
- Aligns with Design Philosophy (LLM decides, not rules)
- Best traceability

**Cons**:
- Most invasive change (touches integrations, MCP tools, Deep Research)
- Requires schema changes for all 9 integrations

---

### RECOMMENDATION

**Option C: Expose Rejection Reasoning** (Most aligned with Design Philosophy)

**Why**:
1. Aligns with "Give LLM full context and ask for intelligent decisions"
2. Provides traceability user is asking for
3. Prevents false negatives from overly conservative relevance checks
4. Future-proof (LLM can learn when to reformulate vs skip)

**Implementation Plan**:
1. Phase 1: Modify integration schemas to return rejection reasoning (instead of `None`)
2. Phase 2: Update MCP tools to pass rejection metadata through
3. Phase 3: Add Deep Research logic to handle rejections intelligently
4. Phase 4: Add logging/traceability for rejection → reformulation → retry lifecycle

**Expected Impact**:
- Reduce "unused source" confusion (user sees WHY source skipped)
- Improve result coverage (reformulation salvages false negatives)
- Better LLM cost efficiency (avoid selecting sources that will self-reject)

---

**Investigation Complete**: Ready for user guidance on priorities
