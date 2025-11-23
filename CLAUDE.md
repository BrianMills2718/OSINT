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

**8 integrations** (via MCP + direct):
- Government: SAM.gov, DVIDS, USAJobs, ClearanceJobs
- Social: Twitter, Reddit, Discord
- Web: Brave Search

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

---

## TESTING

### Categories

1. **Unit**: Isolated, may mock, fast
2. **Integration**: Multiple components, real APIs
3. **E2E** (REQUIRED for success claims): User-facing entry points, no mocks

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

**Last Updated**: 2025-11-22
**Current Branch**: `master`
**Current Phase**: Maintenance and optimization
**Status**: Core research quality improvements complete

---

## CURRENT STATUS

**Recently Completed** (2025-11-22):
- ✅ Query saturation enhancement (LLM-based quality assessment)
- ✅ Hypothesis diversity enforcement (context-aware generation)
- ✅ Report synthesis improvements (inline citations, source grouping, verification context) - **VERIFIED WORKING**
- ✅ Discord parser robustness (0.14% error rate handled gracefully)
- ✅ Timeout configuration (45-min total research budget)
- ✅ Enhanced structured logging (source_skipped, time_breakdown) - **COMPLETE**
- ✅ CREST Selenium integration (bypasses Akamai Bot Manager) - **WORKING**
- ✅ Metadata-driven stealth selection (playwright/selenium per-source) - **COMPLETE**
- ✅ Source context documentation (comprehensive descriptions in hypothesis_generation.j2) - **COMPLETE**

---

## NEXT PLANNED WORK

### HIGH PRIORITY

**All high-priority quality improvements complete!**

### MEDIUM PRIORITY

**All medium-priority improvements complete!**

### LOW PRIORITY

**Time Budget Increase** 📋 **OPTIONAL**
- **Current**: 45 min total (user configured)
- **Proposal**: Increase to 240 min (4 hours) for exhaustive research mode
- **Note**: Current 45-min budget sufficient for most queries
- **User Decision**: Whether to increase default budget

---

## WHAT'S WORKING

**Core Research Engine**: `apps/ai_research.py`
- Task decomposition with angle-based queries (not entity permutations)
- Hypothesis generation (3-5 per task)
- **NEW**: Follow-up generation with global task context (prevents redundancy)
- Sequential hypothesis execution with coverage assessment
- LLM-powered follow-up generation (addresses info gaps)
- Manager LLM prioritizes pending tasks (P1-P10)
- Saturation detection (stops when research complete)

**Integrations**: 8 working
- Government: SAM.gov, DVIDS, USAJobs, ClearanceJobs
- Social: Twitter, Reddit, Discord
- Web: Brave Search

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
2. **ClearanceJobs**: Official API broken. Use clearancejobs_playwright.py
3. **USAJobs**: Requires headers: `User-Agent: email`, `Authorization-Key: [key]`
4. **Discord**: 14/9916 exports malformed (0.14%) - gracefully skipped with warnings
5. **SAM.gov**: Low rate limits - will be rate-limited early in research (handled gracefully)

---

## RECENT CHANGES (Last 7 Days)

**2025-11-22**: Source context documentation enhancement
- ✅ Added comprehensive source descriptions to hypothesis_generation.j2
- ✅ 15 integrations now have detailed "what this contains" explanations
- ✅ Enhanced source selection strategy with practical use cases
- Files modified: prompts/deep_research/hypothesis_generation.j2 (37 lines added)
- Impact: LLM can make better source selections when generating hypotheses by understanding source capabilities

**2025-11-22**: Reddit underutilization fix (commit 503b13d)
- ✅ Replaced hardcoded keyword filtering with LLM-based relevance check
- ✅ Reddit now returns True for contract queries (previously returned False)
- ✅ Consistent with Discord integration pattern
- Files modified: integrations/social/reddit_integration.py (60 lines), tests/test_reddit_fix.py (new)
- Impact: Reddit will now be queried proportionally to its relevance, capturing community discussions and insider perspectives

**2025-11-22**: Follow-up task redundancy fix
- ✅ Added global task context to follow-up generation
- ✅ Follow-up LLM now sees all completed + pending tasks
- ✅ Prevents creating duplicate follow-ups
- Files modified: research/deep_research.py (17 lines), prompts/deep_research/follow_up_generation.j2 (15 lines + documentation)
- Impact: Should eliminate near-duplicate follow-ups like Anduril Tasks 4-7

**2025-11-22**: Docker infrastructure created
- ✅ Dockerfile with Chrome + Playwright pre-installed
- ✅ docker-compose.yml for research CLI and web UI
- ✅ .dockerignore for optimized builds
- ✅ DOCKER.md documentation
- Impact: Solves WSL2 Chrome binary path issues permanently

**2025-11-21**: Phase 1 query saturation COMPLETE
- ✅ Multi-query saturation with LLM intelligence
- ✅ Three-tier exit strategy
- ✅ 54% more results than baseline (SpaceX test: 80 vs 52)
- Files modified: ~482 lines across research/deep_research.py, integrations/source_metadata.py, etc.

---

**END OF TEMPORARY SECTION**
