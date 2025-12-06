# CLAUDE.md - Permanent Section (v2 - Condensed)

---

## **DESIGN PHILOSOPHY**

### **No hardcoded heuristics. Full LLM intelligence. Quality-first.**

**Core Principle**: Trust the LLM to make intelligent decisions based on full context, not programmatic rules.

**Anti-Patterns** (FORBIDDEN):
- ❌ Hardcoded thresholds ("drop source after 2 failures")
- ❌ Fixed sampling limits (top 5, first 10, etc.)
- ❌ Rule-based decision trees ("if X then Y")
- ❌ Premature optimization for cost/speed over quality
- ❌ **Artificial timeouts on tests** (`timeout 600`, Bash tool timeout parameter on research tasks)
- ❌ **FALLBACKS** - Silent source substitution that masks bugs and makes debugging impossible. If Brave fails, FAIL LOUDLY - don't secretly switch to Exa. Example of bug this caused: SEC EDGAR "fallback" code path ignored form_types parameter, returning wrong data for months.

**Correct Approach** (REQUIRED):
- ✅ Give LLM full context and ask for intelligent decisions
- ✅ Make ALL limits user-configurable (not hardcoded)
- ✅ Require LLM to justify all decisions with reasoning
- ✅ Optimize for quality - user configures budget upfront and walks away
- ✅ Use LLM's 1M token context fully (no artificial sampling)
- ✅ **Let tests run naturally** - System has built-in timeouts (LLM 180s, Max research budget). Trust them.

**User Workflow**: Configure parameters once → Run research → Walk away → Get comprehensive results
- No mid-run feedback required
- No manual intervention
- No stopping for user input
- All decisions automated via LLM intelligence

---

## PURPOSE

**CRITICAL**: This file guides EVERY Claude Code API call.

**Structure**:
- **PERMANENT**: Core principles (rarely changes)
- **TEMPORARY**: Current tasks (updated frequently)

**Source Files**: CLAUDE_PERMANENT_v2.md, CLAUDE_TEMP.md, REGENERATE_CLAUDE.md

**When to Update**:
- **TEMPORARY only**: Tasks complete, blockers change, next actions shift
- **PERMANENT**: Major architecture changes, new systematic failure patterns

**Maintenance Requirements** (CRITICAL):
- **REMOVE resolved issues** from P0/P1/P2 lists when fixed - stale issues cause confusion
- **Update STATUS.md** after completing significant work
- **Verify before claiming fixed**: Test the fix, don't just edit code and assume it works
- **Mark with commit hash**: When fixing issues, note the commit (e.g., "FIXED - commit abc123")

---

## VISION

**SigInt Platform** - AI-Powered Investigative Journalism
- 15+ government/social/document sources
- Automated Boolean monitoring + email alerts
- AI analysis (summaries, entity extraction, timelines)
- Team collaboration workspaces

**Current**: ~60% complete, 4 databases working
**Timeline**: 3-6 months to production

See: INVESTIGATIVE_PLATFORM_VISION.md (75 pages)

---

## CORE PRINCIPLES (MANDATORY)

### 1. ADVERSARIAL TESTING

**Assume all tests will fail. Prove they didn't.**

- Before claiming success, actively try to break it
- Look for what you CANNOT prove
- Document limitations > fabricate success

❌ WRONG: "Integration complete! Everything working!"
✅ RIGHT: "[PASS] Query gen: 5 jobs returned | [UNVERIFIED] Parallel execution, error handling | [LIMITATION] Slow on WSL2 (8s vs 5s)"

### 2. EVIDENCE HIERARCHY

**Only these count**:
1. **Command output** - Highest proof
2. **Error messages** - Proof of failure
3. **User execution** - Ultimate proof

**NOT evidence**:
- "Should work because..." (reasoning ≠ proof)
- "Code looks correct..." (existence ≠ proof)
- "Tests passed" without output (claim ≠ proof)

### 3. FORBIDDEN/REQUIRED LANGUAGE

**NEVER**: "Success!", "Done!", "EXCELLENT!", "Working!", "Perfect!", ✅🎉✨
**ALWAYS**: "[PASS]", "[FAIL]", "[BLOCKED]", "Test passed:", "Limitation found:", "Unverified:"

### 4. ANTI-LYING CHECKLIST (BEFORE REPORTING)

1. ❓ Read COMPLETE output, not just success messages?
2. ❓ Count failures AND successes?
3. ❓ About to use ✅ emoji? → Use [PASS]/[FAIL] instead
4. ❓ Ignoring/downplaying failures? → Lead with failures
5. ❓ Cherry-picking good parts? → Report failures first

**Format**: `[FAIL] X: error | [FAIL] Y: error | [PASS] Z: success`

### 5. DISCOVERY BEFORE BUILDING

**BEFORE building, check if it exists**:
1. Read STATUS.md - what's [PASS]?
2. Read CLAUDE.md TEMPORARY - current task?
3. Check directory - does it already exist?
4. Test existing entry points - does it work?

**Why**: Prevents rebuilding existing infrastructure

### 6. CIRCUIT BREAKERS (HARD STOP)

**STOP immediately when**:
1. Import errors on entry points
2. 3+ consecutive timeouts **from the system's built-in timeouts** (not artificial wrappers)
3. Scope drift (doing more than declared)
4. No evidence after 30 minutes
5. Circular work (repeating failed approach)
6. Config file not found
7. API quota/rate limit exceeded

**NEVER impose artificial timeouts**:
- ❌ Shell-level timeout wrappers (`timeout 600 python3 script.py`)
- ❌ Bash tool timeout parameter on research/test scripts
- ✅ Trust system's built-in protection:
  - LLM call timeout: 180s (3 min) - API failure protection
  - User-configured limits: max_queries_per_source, max_time_per_source_seconds
  - Total research budget: User-configured (e.g., 120 min) - Total cap
- ✅ User configured these upfront - let them work

### 7. FAIL-FAST AND LOUD

- Surface errors with full stack traces
- NEVER swallow exceptions
- Log: API calls, LLM queries, config loads, validation checks

### 8. NO LAZY IMPLEMENTATIONS

**Forbidden**: Mocks in production, fallbacks hiding errors, TODO pseudocode
**Required**: Real implementations or explicit documentation of gaps

### 9. DOCUMENTATION CREATION POLICY

**NEVER create documentation files without user directive or explicit assent**

**Forbidden**:
- ❌ Creating .md files "for organization" without asking
- ❌ Writing analysis/planning documents unprompted
- ❌ Generating README files without request
- ❌ Creating summary/review documents on your own initiative

**Required**:
- ✅ Ask user before creating any documentation file
- ✅ Only create docs when explicitly requested
- ✅ If user asks "organize X", ask WHERE and WHAT FORMAT before creating files

**Exception**: Files that ARE part of implementation (code comments, docstrings, inline docs) are always allowed.

**Project-Specific Locations**:
- Active docs: `/home/brian/sam_gov/docs/` (implementation guides, technical references)
- Archive: `/home/brian/sam_gov/archive/YYYY-MM-DD/` (completed work)

---

## DIRECTORY STRUCTURE

```
sam_gov/
├── CLAUDE.md, STATUS.md, PATTERNS.md
├── prompts/                 # Jinja2 LLM prompt templates
│   ├── __init__.py          # Template environment
│   ├── deep_research/       # Deep research prompts (.j2)
│   └── integrations/        # Integration prompts (.j2)
├── core/                    # Research engines + prompt_loader.py
├── integrations/            # Data source adapters
│   ├── government/          # SAM, DVIDS, USAJobs, ClearanceJobs
│   └── social/              # Twitter, Reddit, Discord
├── apps/                    # User entry points (ai_research.py, unified_search_app.py)
├── tests/                   # All test scripts
├── research/                # Deep research workflows
├── data/                    # Runtime storage (articles, exports, logs, monitors)
├── docs/                    # Documentation
├── archive/YYYY-MM-DD/      # Archived code/docs
├── .env, config.yaml        # Configuration (gitignored)
└── llm_utils.py, config_loader.py
```

### Root Directory Discipline

**Only in Root** (~15 files):
- Core docs (9): CLAUDE.md, STATUS.md, PATTERNS.md, etc.
- Config (4-5): .env, .gitignore, requirements.txt, config*.yaml
- Core utils (2): llm_utils.py, config_loader.py

**Archive immediately**:
- Test scripts → `tests/`
- *_COMPLETE.md, *_STATUS.md → `archive/YYYY-MM-DD/docs/`
- *_PLAN.md → `docs/` (active) or `archive/` (completed)
- *.log, temp_*.txt → `data/logs/`

**If root >20 files**: STOP, archive excess, create README

### File Finding

- Current task → CLAUDE.md TEMPORARY
- Is X working? → STATUS.md
- How to implement Y? → PATTERNS.md
- Why? → INVESTIGATIVE_PLATFORM_VISION.md
- Archived? → archive/YYYY-MM-DD/README.md

### Documentation Layers

1. **VISION** (INVESTIGATIVE_PLATFORM_VISION.md) - What we want
2. **ROADMAP** (ROADMAP.md) - How we plan it
3. **STATUS** (STATUS.md) - What actually works
4. **CLAUDE.md TEMPORARY** - What I'm doing now

**Before work**: Read TEMPORARY → STATUS → Test existing → Only build if missing/broken

---

## SYSTEM ARCHITECTURE

### Multi-Agent Research System

**Pattern**: Manager-Agent with Hypothesis Branching (evolved BabyAGI-like)
**Complexity**: 4,392 lines (research/deep_research.py)
**Philosophy**: No hardcoded heuristics, full LLM intelligence, quality-first

### Agent Hierarchy

```
User Query → [Task Decomposition LLM] → 3-5 research tasks
    ↓
[Manager LLM] → Prioritizes tasks (P1-P10)
    ↓
For each task:
    ├─ [Hypothesis Generation LLM] → 3-5 investigative hypotheses
    ├─ For each hypothesis:
    │   ├─ [Query Generation LLM] → Source-specific queries
    │   ├─ [Source Execution] → DVIDS, Brave, SAM.gov, etc.
    │   ├─ [Relevance Filter LLM] → Filter hypothesis results
    │   └─ [Coverage Assessment LLM] → Should we continue?
    └─ [Relevance Filter LLM] → Filter main task results (if no hypotheses)
        ↓
[Report Synthesis LLM] → Final markdown report
```

### Key Components

**research/deep_research.py** (4,392 lines):
- Main class: `SimpleDeepResearch` (misnomer - not simple!)
- Task decomposition, hypothesis generation, filtering, synthesis
- 5 phases implemented (see STATUS.md for details)

**research/execution_logger.py**:
- Structured logging to `execution_log.jsonl`
- All LLM decisions, API calls, filtering choices logged

**prompts/deep_research/** (Jinja2 templates):
- 8+ prompts for different LLM agents
- All prompts version-controlled separately from code

**23 integrations** (via registry):
- **Contracts** (2): SAM.gov, USAspending
- **Government** (7): Congress.gov, FBI Vault, Federal Register, CIA CREST, FEC, GovInfo, SEC EDGAR
- **Jobs** (2): ClearanceJobs, USAJobs
- **Media** (1): DVIDS
- **News** (1): NewsAPI
- **Research** (3): CourtListener, ICIJ Offshore Leaks, ProPublica
- **Social** (4): Discord, Telegram, Reddit, Twitter
- **Web Search** (2): Brave Search, Exa
- **Archive** (1): Wayback Machine

### Output Structure

```
data/research_output/YYYY-MM-DD_HH-MM-SS_query/
├─ execution_log.jsonl  # Structured event log (all LLM decisions)
├─ metadata.json        # Run metadata (config, stats, coverage decisions)
├─ report.md           # Final markdown report
├─ results.json        # All results with deduplication
└─ raw/                # Raw API responses
```

### Entry Points

**Primary**:
- `apps/ai_research.py` - Main CLI for deep research
- `apps/unified_search_app.py` - Streamlit web UI

**Testing**:
- `tests/test_deep_research_full.py` - E2E validation
- 160+ test files for all components

---

## ENVIRONMENT

### Python (.venv)

**MANDATORY**: ALL commands must activate `.venv` first

```bash
source .venv/bin/activate  # FIRST, EVERY TIME
python3 script.py          # Now uses .venv
```

**Circuit Breaker**: `ModuleNotFoundError: No module named 'playwright'`
→ STOP, activate `.venv`, rerun

### API Keys

**ALWAYS use python-dotenv**:

```python
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')
```

**NEVER**: Hardcode keys, commit .env, use os.environ without load_dotenv()

---

## CODE PATTERNS

### LLM Calls

```python
from llm_utils import acompletion
from dotenv import load_dotenv

load_dotenv()

response = await acompletion(
    model="gpt-5-mini",
    messages=[{"role": "user", "content": prompt}],
    response_format={"type": "json_schema", "json_schema": {...}}
)
```

**NEVER**: Call litellm directly, use max_tokens/max_output_tokens (breaks gpt-5)

### LLM Prompts with JSON Examples

**ALWAYS use Jinja2 templates** for prompts containing JSON examples.

**Pattern**:
```python
from core.prompt_loader import render_prompt

prompt = render_prompt(
    "deep_research/query_reformulation.j2",
    research_question=question,
    original_query=query,
    results_count=count
)
```

**Template Location**: `prompts/<module>/<prompt_name>.j2`

**Key Benefits**:
- NO `{{` `}}` escaping needed (JSON examples are literal)
- Prompts version-controlled separately from code
- Easy to edit without touching Python
- Templates are testable and parseable

**Reference**:
- docs/FSTRING_JSON_METHODOLOGY.md (comprehensive guide)
- docs/JINJA2_MIGRATION_INVESTIGATION.md (migration details)

**NEVER**:
- Use f-strings with `{{` `}}` escaping for JSON examples
- Mix JSON structure literals with Python f-string variables

### Database Integration

**Copy from**: `integrations/government/sam_integration.py`

**Required**:
```python
class NewIntegration(DatabaseIntegration):
    @property
    def metadata(self) -> DatabaseMetadata: ...
    async def is_relevant(self, question: str) -> bool: ...
    async def generate_query(self, question: str) -> Optional[Dict]: ...
    async def execute_search(self, params, key, limit) -> QueryResult: ...
```

**After creating**:
1. Save in `integrations/government/` or `social/`
2. Register in `integrations/registry.py`
3. Create `tests/test_newsource_live.py`
4. Test E2E: `python3 apps/ai_research.py "query"`
5. Update STATUS.md with [PASS]/[BLOCKED]

### Result Transformation (SearchResultBuilder)

**ALWAYS use SearchResultBuilder** for transforming API responses to standardized results.

**Pattern**:
```python
from core.result_builder import SearchResultBuilder

# In execute_search():
for item in api_results:
    result = (SearchResultBuilder()
        .title(item.get("name"), default="Untitled")
        .url(item.get("link"))
        .snippet(item.get("description"))
        .date(item.get("created_at"))
        .metadata({
            "source_id": item.get("id"),
            "amount": SearchResultBuilder.safe_amount(item.get("value"))
        })
        .build())
    results.append(result)
```

**Static helpers** (safe to use in f-strings):
- `SearchResultBuilder.safe_amount(value, default=0.0)` - Handle None/invalid numbers
- `SearchResultBuilder.format_amount(value)` - Format as "$1,234.56"
- `SearchResultBuilder.safe_text(value, default="", max_length=None)` - Handle None/truncate
- `SearchResultBuilder.safe_date(value)` - Handle None/datetime/date/string
- `SearchResultBuilder.safe_int(value, default=0)` - Handle None/floats/strings

**Why required**: Prevents TypeError crashes from null API response values. All 25+ integrations use this pattern.

**Reference**: `core/result_builder.py`, `integrations/_integration_template.py`

---

## TESTING

### Current State

**Coverage**: 94% integration coverage (18/19 integrations tested)
**Quality**: Excellent (100% have metadata, relevance, query gen, execution, error tests)
**Gaps**: Zero unit tests for core logic, no CI/CD automation

**See**: `docs/TEST_IMPROVEMENT_PLAN.md` for comprehensive improvement roadmap
**See**: `docs/TESTING_QUICK_REFERENCE.md` for developer guide

### Categories

1. **Unit**: Isolated, may mock, fast (MISSING - P0 priority)
2. **Integration**: Multiple components, real APIs (EXCELLENT - 68 tests)
3. **E2E** (REQUIRED for success claims): User-facing entry points, no mocks

### Test Structure

```
tests/
├── integrations/        # 68 tests (94% coverage) - EXCELLENT
├── system/              # 16 tests
├── unit/                # 0 tests - CRITICAL GAP
├── performance/         # 2 tests
└── features/            # Feature-specific tests
```

### Checklist (Before Claiming Success)

ALL must be true:
- [ ] Imports resolve
- [ ] Config loads from .env/config.yaml
- [ ] API calls succeed
- [ ] Results match format
- [ ] Errors handled gracefully
- [ ] User can execute without assistance
- [ ] No timeouts
- [ ] Logging works
- [ ] Cost tracking (if LLM)

**If ANY false → NOT succeeded**

### Priority Test Improvements

**P0 - Critical** (4-6 hours):
1. Create pytest.ini configuration
2. Set up GitHub Actions CI/CD
3. Add prompt template validator (59 .j2 files untested)
4. Add recursive agent unit tests (2,965-line file has zero tests)

**P1 - High Value** (6-8 hours):
5. Add SearchResultBuilder validation tests
6. Add error scenario tests (rate limits, timeouts)
7. Add code coverage tracking (pytest-cov)

**See docs/TEST_IMPROVEMENT_PLAN.md** for detailed implementation plan

---

## KNOWN ISSUES

1. **gpt-5 models**: NEVER use max_tokens (breaks reasoning). Use llm_utils.acompletion()
2. **ClearanceJobs**: Official API broken. Use clearancejobs_playwright.py (slower but accurate)
3. **USAJobs**: Requires headers: `User-Agent: email`, `Authorization-Key: [key]`

---

## ESSENTIAL TOOLS

**Keep** (complex/critical):
- prompts/ directory + all .j2 templates
- core/prompt_loader.py (Jinja2 infrastructure)
- tests/test_all_four_databases.py
- tests/test_verification.py
- llm_utils.py, config_loader.py
- integrations/government/sam_integration.py

**Regenerate on-demand** (simple):
- Unit tests, CLI scripts, utilities

**Entry Points** (always keep):
- apps/ai_research.py
- apps/unified_search_app.py

---

## QUICK REFERENCE

```bash
source .venv/bin/activate  # ALWAYS FIRST

# Test entry points
python3 apps/ai_research.py "query"
python3 tests/test_verification.py
streamlit run apps/unified_search_app.py

# Verify environment
which python3  # Should show .venv/bin/python3
pip list | grep playwright
```

---

**END OF PERMANENT SECTION**
# CLAUDE.md - Temporary Section (Condensed)

**Last Updated**: 2025-12-06
**Current Branch**: `master`
**Current Phase**: v2 Production-Ready
**Status**: All integrations configured, entity follow-up improved, rate limit optimization added

---

## V2 RECURSIVE AGENT MIGRATION

**Plan Document**: `docs/V2_RECURSIVE_AGENT_MIGRATION_PLAN.md`

### Migration Phases Overview

| Phase | Name | Status |
|-------|------|--------|
| 1 | Validation | **COMPLETE** |
| 2 | CLI Entry Point | **COMPLETE** |
| 3 | Feature Parity | **COMPLETE** |
| 4 | Side-by-Side Comparison | **COMPLETE** (partial - API issues) |
| 5 | Full Migration | **COMPLETE** |

**v2 is now the default research system!**

**CLI Entry Points** (both use v2 RecursiveResearchAgent):
- **Recommended**: `python3 run_research_cli.py "your query"` (consolidated, backward compatible)
- **Alternative**: `python3 apps/recursive_research.py "your query"` (original Phase 2 implementation)
- **Both are v2!** They use RecursiveResearchAgent, not v1 SimpleDeepResearch

**Important**: `depth=0` is valid v2 behavior! The LLM's `assess()` method may choose to execute a goal directly without decomposing it. This is not a bug - it's intelligent decision-making by the LLM.

- Streamlit: Deep Investigation tab uses v2
- v1 (SimpleDeepResearch) deprecated but available in `research/deep_research.py`

### Phase 1: Validation - COMPLETE

**Tasks**:
- [x] Build v2 recursive agent core (`research/recursive_agent.py`) - commit bc6f49a
- [x] Fix 5 bugs from code review - commit 4fb5138
- [x] Fix cost tracking propagation bug - commit 1b95747
- [x] Run validation test (simple query) - 20 results, 9.1s
- [x] Run validation test (complex query) - 59 results, 3 sub-goals decomposed
- [x] Verify cost tracking works - $0.0002 tracked correctly

**Validation Results**:
- Simple query: "Find federal AI contracts awarded in 2024" → 20 evidence, status completed
- Complex query: "Palantir contracts, lobbying, controversies" → 59 evidence, depth 3, synthesis generated
- Cost tracking: Assessment LLM call cost ($0.0002) propagated to result

### Phase 2: CLI Entry Point - COMPLETE

**Tasks**:
- [x] Create `apps/recursive_research.py` CLI wrapper (commit dc005dd)
- [x] Support v2 args: `--max-depth`, `--max-time`, `--max-goals`, `--max-cost`, `--max-concurrent`
- [x] Map CLI args to v2 Constraints dataclass
- [x] Add output directory structure: `data/research_v2/YYYY-MM-DD_HH-MM-SS_query/`
- [x] Test CLI end-to-end: 20 results, 10s, $0.0002 cost

**Output Files**: report.md, evidence.json, metadata.json, execution_log.jsonl, result.json

### Phase 3: Feature Parity - COMPLETE

**Tasks**:
- [x] Query reformulation on API error (`_reformulate_on_error()` method)
- [x] Per-source query generation prompts (uses `integration.generate_query()`)
- [x] Result relevance filtering (`_filter_results()` method with LLM)
- [x] Temporal context injection (`_get_temporal_context()` in all prompts)
- [x] Execution logging (15+ specialized event types, schema v2.0)
- [x] Report generation improvements (LLM synthesis with v2_report_synthesis.j2)
- [x] URL deduplication (seen_urls set, commit 8e19f4c)
- [x] Entity extraction (EntityAnalyzer integration)
- [x] Progressive summarization (replaces truncation with LLM summaries)

**Validation Results** (2025-11-26):
- E2E test: "Find federal cybersecurity contracts in 2024" → 20 results, 44s, $0.0004
- Entity extraction: 10 entities discovered with relationship graph
- All 9 feature tests pass in validation script
- Summarization index mismatch bug found and fixed (commit 8e19f4c)

---

## CURRENT STATUS

**System State**: Production-ready, v2 RecursiveResearchAgent is default
**Last Validated**: 2025-12-06 (Anduril test: 38 evidence, 0 false positives, $0.008)

### Key Milestones
- ✅ v2 Migration complete (5 phases)
- ✅ 23 integrations registered
- ✅ PDF extraction infrastructure (GovInfo, FBI Vault)
- ✅ Error handling with HTTP code classification
- ✅ Global evidence index for cross-branch sharing

### Pending Investigations
- **DAG/ANALYZE Infrastructure** (docs/DAG_ANALYSIS_INVESTIGATION.md)
  - DAG code 90% complete but LLM doesn't declare dependencies
  - Prompt engineering needed for comparative queries
  - Estimated: 11-19 hours

---

## OPEN ISSUES

### P2 - Medium Priority

**4. SAM.gov Rate Limit - No Retry Logic**
- **Problem**: SAM.gov rate limits immediately, skipped for entire session
- **Fix**: Queue rate-limited sources for retry after cooldown (5 min)
- **File**: research/recursive_agent.py (rate_limited_sources handling)

### P3 - Infrastructure

**5. Systematic API Documentation Storage**
- **Problem**: API docs discovered ad-hoc, knowledge lost between sessions
- **Solution**: Create `docs/api_reference/` with per-integration API notes
- **Effort**: 4-6 hours

**6. Add GAO.gov as Direct Source**
- **Problem**: GovInfo GAOREPORTS only has 1994-2008 data
- **Solution**: Create `integrations/government/gao_integration.py` for recent reports
- **Effort**: 4-6 hours

---

## RECENTLY FIXED (2025-12-06)

| Issue | Commit | Summary |
|-------|--------|---------|
| Field Name Mismatch | 68dc031 | Evidence content was empty - fixed snippet lookup |
| Filter Prompt Too Lenient | 414918d | Added strict entity matching rules |
| SEC EDGAR Fallback Bug | 66d25c2 | Removed broken fallback abstraction (~380 lines) |
| CourtListener Relative URLs | 2025-12-06 | Added base URL handling |
| FEC Generic URLs | (already impl) | Uses candidate_id, committee_id filters |
| Evidence Truncation Warning | (already impl) | Logs warning + emoji + JSON field |
| Overconfident Assessment | (already impl) | Synthesis prompt has confidence calibration |
| Date Metadata | (working) | 32% of evidence has dates (infrastructure exists) |
| Twitter API Crash | (already impl) | Defensive code handles list inputs |
| PDF Extraction | fbc1a84, eec649e | PyMuPDF extraction for GovInfo, FBI Vault |
| GovInfo 0 Results | 0dd7f40, c1ffb1e | Fixed search syntax + date filtering |
| API Integration Failures | c871605 | CourtListener "null" string filtering; NewsAPI/FedReg already working |
| Decomposition/Synthesis | (working) | Tested: "Compare X vs Y" creates 3 goals with deps: [0,1] |
| Achievement Check | (working) | Synthesis goal waits for dependencies before executing |

---

## EVIDENCE ARCHITECTURE REFACTOR

**Document**: `docs/EVIDENCE_ARCHITECTURE_PLAN.md`
**Status**: Phase 1-2 PARTIAL (raw_content field done, PDF extraction for 2 integrations)
**Priority**: P1 - Quality improvement (not blocking production use)
**Effort**: 18-26 hours remaining (2-3 days)
**Branch**: `master` (merged)

### Problem Summary

**Current Issues** (Verified 2025-12-05):
1. **Silent Truncation Chain** - Data truncated at 7 points without logging
2. **Dates Not Preserved** - 100% of date fields lost in saved output
3. **Metadata Discarded** - Rich API data lost in _result_to_dict()
4. **Evidence Count Capped** - Only 50 of 255+ evidence saved (80% loss)
5. **Overloaded snippet Field** - Raw + processed in same field

**Verified Truncation Points**:
| Location | Truncation | Line |
|----------|-----------|------|
| Pydantic validator | 500 chars | db_base.py:140-147 |
| Entity extraction | 300 chars | agent.py:1373 |
| Global index | 200 chars | agent.py:2101 |
| Assessment prompt | 100 chars | agent.py:1107 |
| Saved result | 500 chars, 50 items | agent.py:2345-2348 |

### Implementation Plan (6 Phases)

#### Phase 1: Data Model Refactor (4-6 hours) - PARTIAL PROGRESS

**Tasks**:
- [ ] 1.1: Create `core/raw_result.py` with RawResult dataclass
- [ ] 1.2: Create `core/processed_evidence.py` with ProcessedEvidence dataclass
- [ ] 1.3: Update Evidence class to compose RawResult + ProcessedEvidence
- [ ] 1.4: Add `Evidence.from_raw()` factory method
- [x] 1.5: Maintain backward compatibility - **DONE** (2025-12-06): Added `raw_content: Optional[str]` to SearchResult, fixed Evidence.from_search_result() regression

**Tests**:
- [ ] Test RawResult creation from sample API response
- [ ] Test ProcessedEvidence with extracted facts/entities
- [ ] Test Evidence backward compatibility (old code still works)
- [ ] Test serialization/deserialization roundtrip

**Files**:
- `core/raw_result.py` (NEW)
- `core/processed_evidence.py` (NEW)
- `core/database_integration_base.py` (MODIFY)

#### Phase 2: Integration Updates (6-8 hours) - PARTIAL PROGRESS

**Tasks**:
- [x] 2.1: Update SearchResultBuilder to preserve full content - **DONE**: `build_with_raw()` method exists
- [ ] 2.2: Update SAM.gov integration (high-traffic)
- [ ] 2.3: Update USAspending integration (already stores raw)
- [ ] 2.4: Update Brave Search integration
- [x] 2.5a: GovInfo integration - **DONE** (2025-12-06): PDF extraction with `extract_pdf=True` parameter
- [x] 2.5b: FBI Vault integration - **DONE** (2025-12-06): PDF extraction for document links
- [ ] 2.5c: Update remaining 18 integrations

**Tests**:
- [ ] Test SAM.gov returns complete api_response
- [ ] Test USAspending preserves full award data
- [ ] Test each integration returns RawResult with raw_content

**Files**:
- `core/result_builder.py` (MODIFY)
- All 23 integration files (MODIFY)

#### Phase 3: Agent Refactor (4-6 hours)

**Tasks**:
- [ ] 3.1: Update `_execute_api_call()` to create Evidence from RawResult
- [ ] 3.2: Implement `_extract_evidence()` LLM call for goal-focused extraction
- [ ] 3.3: Update `_add_to_run_index()` to store complete Evidence
- [ ] 3.4: Update `_result_to_dict()` to preserve all fields
- [ ] 3.5: Add date extraction from content (LLM-based)

**Tests**:
- [ ] Test Evidence creation preserves raw content
- [ ] Test extraction populates facts/entities/dates
- [ ] Test saved result.json has all fields

**Files**:
- `research/recursive_agent.py` (MODIFY)

#### Phase 4: Prompt Updates (2-3 hours)

**Tasks**:
- [ ] 4.1: Update filtering to use `.llm_context` for decisions
- [ ] 4.2: Create `evidence_extraction.j2` prompt
- [ ] 4.3: Update synthesis to use structured ProcessedEvidence

**Tests**:
- [ ] Test filtering uses summary not full content
- [ ] Test extraction prompt produces valid JSON
- [ ] Test synthesis uses extracted facts

**Files**:
- `prompts/recursive_agent/result_filtering.j2` (MODIFY)
- `prompts/recursive_agent/evidence_extraction.j2` (NEW)
- `prompts/deep_research/v2_report_synthesis.j2` (MODIFY)

#### Phase 5: Storage Refactor (2-3 hours)

**Tasks**:
- [ ] 5.1: Save raw responses to `raw_responses/` directory
- [ ] 5.2: Save processed evidence with full fields
- [ ] 5.3: Create both full and summary result files
- [ ] 5.4: Log data preservation metrics

**Tests**:
- [ ] Test raw_responses/ contains complete API data
- [ ] Test result.json has dates/metadata
- [ ] Test no silent truncation (warnings logged)

**Files**:
- `research/recursive_agent.py` (_save_result method)

#### Phase 6: Testing and Validation (4-6 hours)

**Tasks**:
- [ ] 6.1: Unit tests for new data models
- [ ] 6.2: Integration tests for each source
- [ ] 6.3: E2E test verifying no data loss
- [ ] 6.4: Regression test comparing output quality

**Tests**:
- [ ] 100% of collected evidence saved (not capped at 50)
- [ ] 100% of dates preserved
- [ ] 100% of metadata preserved
- [ ] Report quality unchanged or improved

**Files**:
- `tests/test_evidence_model.py` (NEW)
- `tests/test_evidence_storage.py` (NEW)

### Success Criteria

- [ ] 100% of collected evidence saved (not capped at 50)
- [ ] 100% of dates preserved (structured + extracted)
- [ ] 100% of metadata preserved (raw API responses)
- [ ] 0 silent truncations (all truncation logged with warning)
- [ ] All existing tests pass
- [ ] LLM prompt sizes unchanged (use summaries)
- [ ] Report quality unchanged or improved

---

## ERROR HANDLING ARCHITECTURE REFACTOR

**Document**: `docs/ERROR_HANDLING_ARCHITECTURE.md`
**Status**: Planning → Implementation
**Priority**: P1 - Critical for reliability
**Effort**: 12 hours (2-3 days)

### Problem Summary

**Current Issues**:
1. ❌ Brittle text pattern matching for error classification
2. ❌ Missing HTTP codes (401, 403, 404, 500-504) trigger reformulation wastefully
3. ❌ DVIDS sends "nullT00:00:00Z" (malformed dates from LLM string "null")
4. ❌ HTTP status codes not propagated from integrations
5. ❌ Agent does complex text parsing (mixed concerns)

**Discovered From**:
- E2E test showing DVIDS HTTP 400 → HTTP 403 reformulation attempt
- "Iteration 2/10" follow-up loop generating 14 goals from gaps

### Architecture Solution

**Structured Error Model** (4 layers):
1. **Layer 1**: `core/error_classifier.py` - Centralized classification
   - `APIError` dataclass with `is_reformulable`, `is_retryable` flags
   - `ErrorCategory` enum (AUTH, RATE_LIMIT, VALIDATION, TIMEOUT, etc.)
   - HTTP code-based classification (primary), text patterns (fallback)

2. **Layer 2**: Integration changes
   - Add `http_code: Optional[int]` to `QueryResult` dataclass
   - Extract HTTP codes in exception handlers
   - Return structured error data

3. **Layer 3**: Agent simplification
   - Replace pattern matching with `error_classifier.classify()`
   - Use boolean flags for decisions (`if error.is_reformulable`)
   - Structured error logging

4. **Layer 4**: Configuration
   - Add `unfixable_http_codes: [401, 403, 404, 429, 500-504]`
   - Add `fixable_http_codes: [400, 422]`
   - Keep text patterns for non-HTTP errors

### Implementation Plan (5 Phases)

**Phase 1: Foundation** (2 hours) - P0 Blocking
- Task 1.1: Add missing HTTP codes to config (15 min)
- Task 1.2: Fix DVIDS "null" date bug (30 min)
- Task 1.3: Create ErrorClassifier skeleton (45 min)
- Task 1.4: Update QueryResult dataclass (30 min)

**Phase 2: Integrations** (4 hours) - P1 High Value
- Task 2.1: Update 5 high-traffic integrations (2 hours)
- Task 2.2: Update remaining 24 integrations (2 hours)

**Phase 3: Agent Refactor** (3 hours) - P1 Simplifies Core
- Task 3.1: Integrate ErrorClassifier into agent (1 hour)
- Task 3.2: Simplify error handling logic (1 hour)
- Task 3.3: Add structured error logging (1 hour)

**Phase 4: Testing** (2 hours) - P1 No Regressions
- Task 4.1: Unit tests for ErrorClassifier (45 min)
- Task 4.2: Integration error tests (45 min)
- Task 4.3: E2E error handling test (30 min)

**Phase 5: Documentation** (1 hour) - P2 Polish
- Task 5.1: Update PATTERNS.md (20 min)
- Task 5.2: Update STATUS.md (20 min)
- Task 5.3: Remove deprecated code (20 min)

### Success Criteria

**Before**:
- ❌ 403 errors trigger reformulation
- ❌ DVIDS sends "nullT00:00:00Z"
- ❌ No HTTP codes in QueryResult

**After**:
- ✅ 403 errors skip reformulation immediately
- ✅ DVIDS validates dates before API call
- ✅ All integrations return HTTP codes
- ✅ 100% test coverage for error classification

**See**: `docs/ERROR_HANDLING_ARCHITECTURE.md` for full design

---

## CONFIGURATION ARCHITECTURE ISSUES

**Comprehensive Codebase Review** (2025-11-30)

**Executive Summary**:
- 36 files with inline JSON schemas (~3,500 lines should be externalized) - **DEFERRED**
- ~~9 hardcoded f-string prompts~~ - **RESOLVED** (2025-11-30)
- ~~7 missing Jinja2 templates~~ - **RESOLVED** (2025-11-30)
- schemas/ directory underutilized (only 2 files, expected 10-15) - **DEFERRED**
- ~~3 non-configurable magic numbers~~ - **RESOLVED** (already configurable via Constraints)

**Original Effort Estimate**: 8-9 days
**Actual Effort**: 2 days (prompts only, schemas deferred)
**Priority**: MEDIUM - Quality of life improvement, no critical bugs
**Impact**: 40% maintainability improvement for prompts, easier A/B testing, better version control

### Issue Summary

| Issue | Count | Severity | Status | Effort | Files Affected |
|-------|-------|----------|--------|--------|----------------|
| Inline JSON Schemas | 36 files | HIGH | **DEFERRED** | 3 days | integrations/*, research/* |
| Hardcoded F-String Prompts | 9 prompts | HIGH | **RESOLVED** | 2 days | research/recursive_agent.py |
| Missing Jinja2 Templates | 9 templates | MEDIUM | **RESOLVED** | 2 days | prompts/recursive_agent/* |
| Underutilized schemas/ Directory | Only 2/10+ files | MEDIUM | **DEFERRED** | 4 hrs | schemas/* |
| Non-Configurable Constants | 3 magic numbers | MEDIUM | **N/A** | 0 hrs | Already configurable |

### Problem 1: Inline JSON Schemas (36 Files, ~3,500 Lines)

**Current State**:
- JSON schemas defined inline in Python code using `schema = {` pattern
- Duplicated across 36 integration and research files
- Difficult to version control changes
- Hard to validate schema correctness independently

**Files with Inline Schemas**:
```
integrations/government/ (15 files):
- sam_integration.py (lines 123-185, 62 lines)
- usaspending_integration.py (lines 150-220, 70 lines)
- dvids_integration.py (lines 123-159, 36 lines)
- fec_integration.py (lines 140-180, 40 lines)
- sec_edgar/integration.py (lines 180-220, 40 lines)
- govinfo_integration.py (lines 175-230, 55 lines)
- federal_register.py (lines 160-210, 50 lines)
- usajobs_integration.py (lines 111-141, 30 lines)
- clearancejobs_integration.py (lines 90-120, 30 lines)
- [6 more files...]

integrations/social/ (5 files):
- twitter_integration.py (lines 180-250, 70 lines)
- telegram_integration.py (lines 140-200, 60 lines)
- discord_integration.py (lines 120-160, 40 lines)
- reddit_integration.py (lines 100-140, 40 lines)
- brave_search_integration.py (lines 130-153, 23 lines)

research/ (10 files):
- recursive_agent.py (line 2377-2388, 11 lines - global_evidence_selection schema)
- deep_research.py (~200 lines across multiple schemas)
- [8 more files...]
```

**Example** (research/recursive_agent.py:2377-2388):
```python
# CURRENT (inline, hard to change):
schema = {
    "type": "object",
    "properties": {
        "selected_evidence_ids": {
            "type": "array",
            "items": {"type": "integer"},
            "description": "IDs of evidence pieces to include"
        }
    },
    "required": ["selected_evidence_ids"],
    "additionalProperties": False
}

# SHOULD BE (externalized):
from schemas.recursive_agent import GlobalEvidenceSelectionSchema
schema = GlobalEvidenceSelectionSchema.get_schema()
```

**Recommended Fix**:
1. Create schema files in `schemas/` directory organized by module
2. Use class-based schema definitions with validation
3. Migrate schemas incrementally (10-15 files per batch)

**Effort**: 3 days (15-20 files per day, testing included)

### Problem 2: Hardcoded F-String Prompts - **RESOLVED** (2025-11-30)

**Previous State** (Before 2025-11-30):
- research/recursive_agent.py contained 9 prompts as f-strings directly in code
- Violated established pattern (50 Jinja2 templates exist in prompts/)
- Difficult to edit without touching Python code
- Couldn't A/B test prompt variations easily

**Resolution** (Commits 12968d6, d096af0):
- ✅ All 9 f-string prompts converted to Jinja2 templates
- ✅ Templates created in prompts/recursive_agent/ directory
- ✅ Code updated to use render_prompt() calls
- ✅ Import and rendering tests pass
- ⚠️ E2E validation with real research query not yet performed

**F-String Prompts in recursive_agent.py**:
1. **Line 37**: `_get_temporal_context()` - 150 chars
2. **Lines 1093-1153**: `_assess_goal_structure()` - ~1,200 chars
3. **Lines 1490-1588**: `_decompose_goal()` - ~1,500 chars
4. **Lines 1663-1700**: `_analyze_evidence()` - ~800 chars
5. **Lines 1759-1825**: `_check_goal_achievement()` - ~1,000 chars
6. **Lines 1930-1978**: `_generate_follow_ups()` - ~900 chars
7. **Lines 2029-2061**: `_synthesize_evidence()` - ~1,100 chars
8. **Lines 2144-2168**: `_filter_results()` - ~700 chars
9. **Lines 2234-2255**: `_summarize_results()` - ~400 chars
10. **Lines 2447-2483**: `_reformulate_on_error()` - ~600 chars

**Example** (Lines 1093-1153):
```python
# CURRENT (hardcoded f-string):
prompt = f"""You are a research agent assessing a goal.

Goal: {goal}
Evidence count: {len(evidence)}

Assess whether this goal can be addressed effectively by:
1. Calling APIs directly (API_CALL)
2. Searching the web (WEB_SEARCH)
3. Analyzing existing evidence (ANALYZE)
4. Decomposing into sub-goals (DECOMPOSE)

Return your decision..."""

# SHOULD BE (Jinja2 template):
from core.prompt_loader import render_prompt

prompt = render_prompt(
    "recursive_agent/goal_assessment.j2",
    goal=goal,
    evidence_count=len(evidence),
    available_actions=["API_CALL", "WEB_SEARCH", "ANALYZE", "DECOMPOSE"]
)
```

**Recommended Fix**:
1. Create 7 new Jinja2 templates in `prompts/recursive_agent/`
2. Convert f-strings to `render_prompt()` calls
3. Test each conversion independently

**Effort**: 2 days (3-4 prompts per day, careful testing)

### Problem 3: Missing Jinja2 Templates (7 Templates)

**Current State**:
- prompts/ directory has 50 templates for integrations and deep_research
- But recursive_agent.py (2,965 lines) still uses f-strings
- Inconsistent with established architecture pattern

**Missing Templates** (should exist in prompts/recursive_agent/):
1. `goal_assessment.j2` (for _assess_goal_structure, ~1,200 chars)
2. `goal_decomposition.j2` (for _decompose_goal, ~1,500 chars)
3. `evidence_analysis.j2` (for _analyze_evidence, ~800 chars)
4. `achievement_check.j2` (for _check_goal_achievement, ~1,000 chars)
5. `follow_up_generation.j2` (for _generate_follow_ups, ~900 chars)
6. `evidence_synthesis.j2` (for _synthesize_evidence, ~1,100 chars)
7. `result_filtering.j2` (for _filter_results, ~700 chars)

**Directory Structure Should Be**:
```
prompts/
├── __init__.py
├── deep_research/          # Existing (8+ templates)
├── integrations/           # Existing (40+ templates)
└── recursive_agent/        # NEW (7 templates needed)
    ├── goal_assessment.j2
    ├── goal_decomposition.j2
    ├── evidence_analysis.j2
    ├── achievement_check.j2
    ├── follow_up_generation.j2
    ├── evidence_synthesis.j2
    └── result_filtering.j2
```

**Effort**: 2 days (included in Problem 2 fix, as they're created during conversion)

### Problem 4: Underutilized schemas/ Directory (Only 2 Files)

**Current State**:
```
schemas/
├── __init__.py           # Empty
└── research_brief.py     # Single schema
```

**Expected State** (after refactoring):
```
schemas/
├── __init__.py                     # Schema registry
├── base.py                         # Base schema class with validation
├── integrations/
│   ├── __init__.py
│   ├── sam_gov.py                  # SAM.gov query schemas
│   ├── usaspending.py              # USAspending query schemas
│   ├── twitter.py                  # Twitter query schemas
│   └── [25+ more integration schemas]
├── recursive_agent/
│   ├── __init__.py
│   ├── assessment.py               # Goal assessment schemas
│   ├── decomposition.py            # Goal decomposition schemas
│   ├── evidence.py                 # Evidence analysis schemas
│   └── synthesis.py                # Report synthesis schemas
└── research_brief.py               # Existing
```

**Effort**: 4 hours (directory setup + migration infrastructure)

### Problem 5: Non-Configurable Magic Numbers (3 Occurrences)

**Current State**:
- Hardcoded constants in recursive_agent.py violate "no hardcoded heuristics" principle

**Magic Numbers**:
1. **Line 2236**: `max_evidence_in_saved_result: 50` - Truncates evidence silently
2. **Line unknown**: Default similarity threshold for deduplication
3. **Line unknown**: Default LLM temperature for various calls

**Recommended Fix**:
```python
# CURRENT:
max_evidence_in_saved_result = 50

# SHOULD BE:
from config_loader import config
max_evidence = config.get('recursive_agent.max_evidence_in_result', default=50)
```

**Effort**: 2 hours (identify all constants, add to config.yaml, update code)

### Recommended Refactoring Plan (Phased Approach)

**Phase 1: Extract Schemas** (3 days)
- Days 1-2: Create schemas/ directory structure + base classes
- Day 3: Migrate 15 high-priority integration schemas
- Validation: All tests pass, schemas loadable independently

**Phase 2: Convert Prompts to Jinja2** (2 days)
- Day 1: Create 7 Jinja2 templates in prompts/recursive_agent/
- Day 2: Convert f-strings to render_prompt() calls
- Validation: E2E research test produces same results

**Phase 3: Parameterize Constants** (1 day)
- Hours 1-4: Identify all magic numbers, add to config.yaml
- Hours 5-8: Update code to read from config, test overrides
- Validation: Config changes affect behavior correctly

**Phase 4: Documentation** (1 day)
- Hours 1-4: Update PATTERNS.md with new schema/prompt patterns
- Hours 5-8: Create SCHEMA_GUIDE.md and PROMPT_GUIDE.md
- Validation: New developers can add schemas/prompts easily

**Total Timeline**: 7 days (focused work) + 1-2 days buffer = 8-9 days

### Validation Checklist (Before Merging)

- [ ] All 36 inline schemas moved to schemas/ directory
- [ ] All 9 f-string prompts converted to Jinja2 templates
- [ ] 7 new templates exist in prompts/recursive_agent/
- [ ] All magic numbers configurable via config.yaml
- [ ] All existing tests still pass (no regressions)
- [ ] E2E research produces equivalent results
- [ ] Schema files independently testable (pytest schemas/)
- [ ] Prompts editable without touching Python code
- [ ] Documentation updated (PATTERNS.md, SCHEMA_GUIDE.md)
- [ ] Cost/quality metrics unchanged (within 5%)

### Benefits of Refactoring

**Maintainability** (+50%):
- Edit prompts without touching Python code
- Version control shows prompt changes clearly
- A/B test prompt variations easily

**Testability** (+40%):
- Validate schemas independently (pytest schemas/)
- Test prompt rendering separately from business logic
- Mock schemas for unit tests easily

**Collaboration** (+30%):
- Non-developers can edit prompts (Jinja2 is readable)
- Schema changes tracked in git history
- Easier code reviews (schema changes visible)

**Quality** (+20%):
- Catch schema errors at load time, not runtime
- Lint and validate prompts automatically
- Consistent formatting across all prompts

### Status: Identified, Not Started

**User Request**: "comprehensive review for any ways to improve the codebase. in particular it seems like the prompts might not have been fully made to be configurable here /home/brian/sam_gov/prompts as well as the schemas /home/brian/sam_gov/schemas"

**Findings Documented**: 2025-11-30 (this section)

**Next Steps** (if approved):
1. Create GitHub issue tracking refactoring phases
2. Start with Phase 1 (schemas) - lowest risk, highest value
3. Validate each phase independently before proceeding
4. Document learnings in PATTERNS.md as we go

---

### ARCHITECTURE NOTES

**Evidence Content Sources**:
| Source | Content Type | Full Text? | PDFs? |
|--------|-------------|-----------|-------|
| USAspending | Award metadata | No | N/A |
| Brave Search | Page excerpts | No | No |
| FBI Vault | Doc titles only | No | No (links only) |
| GovInfo | Report abstracts | No | No (links only) |
| CourtListener | Case summaries | No | No |
| NewsAPI | Article snippets | No | N/A |

---

## WHAT'S WORKING

**Core Research Engine**: `apps/ai_research.py`
- Task decomposition with angle-based queries (not entity permutations)
- Hypothesis generation (3-5 per task)
- **NEW**: Follow-up generation with global task context (prevents redundancy)
- Sequential hypothesis execution with coverage assessment
- LLM-powered follow-up generation (addresses info gaps)
- Manager LLM prioritizes pending tasks (P1-P10)
- **NEW**: Strategy-based saturation (tries different approaches when queries fail, not metrics-based stopping)

**Integrations**: 29 working
- Government (15): SAM.gov, USAspending, DVIDS, USAJobs, ClearanceJobs (HTTP, 10x faster), FBI Vault, Federal Register, Congress.gov, **GovInfo** (new), SEC EDGAR, FEC, CREST
- Social (4): Twitter (20 endpoints), Reddit, Discord, Telegram (4 patterns)
- News (1): NewsAPI
- Web (1): Brave Search
- Investigative (1): ICIJ Offshore Leaks (Panama Papers)
- Legal (1): CourtListener
- Nonprofit (1): ProPublica
- Archive (1): Wayback Machine
- Other (4): Additional sources

**Key Features**:
- Jinja2 prompt templates (no f-string JSON escaping)
- Cost tracking with fallback model chain
- Cross-attempt result accumulation
- Deduplication (60-80% typical)
- Entity extraction and relationship discovery
- **NEW**: Follow-up tasks see all existing tasks to avoid duplication

---

## KNOWN ISSUES

1. **gpt-5 models**: Never use max_tokens (breaks reasoning). Use llm_utils.acompletion()
2. **USAJobs**: Requires headers: `User-Agent: email`, `Authorization-Key: [key]`
3. **Discord**: 14/9916 exports malformed (0.14%) - gracefully skipped with warnings
4. **SAM.gov**: Low rate limits - will be rate-limited early in research (handled gracefully)

---

## RECENT CHANGES (Last 7 Days)

**2025-12-06**: PDF Extraction + Bug Fixes
- ✅ `core/pdf_extractor.py` - Async PDF extraction with PyMuPDF + caching
- ✅ GovInfo + FBI Vault integrations now support `extract_pdf=True`
- ✅ `raw_content` field added to SearchResult (preserves full text)
- ✅ Fixed Evidence.from_search_result() regression (duplicate kwarg)
- Commits: fbc1a84, eec649e

**2025-12-05**: GovInfo Integration Fix + Error Handling Complete
- ✅ Fixed GovInfo returning 0 results (wrong search syntax + date filter)
- ✅ All 23 integrations now extract HTTP status codes
- ✅ ErrorClassifier infrastructure complete (287 lines)
- Commits: 0dd7f40, c1ffb1e, 14a0044

**2025-12-01**: Error Handling Architecture Phase 2
- ✅ Updated all integrations with HTTP code extraction
- ✅ Fixed 15 syntax errors from batch update
- Commits: 103ccbe, 66213f9

**2025-11-30**: Global Evidence Index Complete
- ✅ Cross-branch evidence sharing infrastructure
- ✅ LLM-based evidence selection for ANALYZE actions
- ✅ Cost tracking fixed for selection calls
- Commits: 34719db, fc7ab72, ea15ac4

---

**END OF TEMPORARY SECTION**
