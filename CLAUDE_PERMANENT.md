# CLAUDE.md - Permanent Section

---

## PURPOSE OF THIS FILE

**CRITICAL**: This file is attached to the context window of EVERY Claude Code API call.

**What This File Is**:
- Implementation guide containing design philosophy, rules, metacognitive strategies, and testing criteria
- NOT a README - this is for Claude Code agents to follow during development
- Single source of truth for development principles and patterns

**File Structure**:
- **PERMANENT SECTION**: Core principles, patterns, and vision (always present, rarely changes)
- **TEMPORARY SECTION**: Current tasks, next actions, immediate work (updated frequently as tasks complete)

**Source Files** (for regenerating CLAUDE.md):
- **CLAUDE_PERMANENT.md**: Source for PERMANENT section
- **CLAUDE_TEMP.md**: Schema/template for TEMPORARY section structure
- **REGENERATE_CLAUDE.md**: Instructions for regenerating CLAUDE.md

**When to Update CLAUDE.md**:

**Normal Task Work** (update TEMPORARY section only):
- Tasks complete or change
- Blockers identified or resolved
- Next actions shift
- Current phase changes
- **How**: Edit CLAUDE.md TEMPORARY section directly, preserve PERMANENT section

**Rare Updates** (update PERMANENT section):
- Directory structure changes significantly
- New permanent pattern discovered (e.g., new integration approach)
- New principle needed (e.g., new type of systematic failure found)
- Major architectural shift
- **How**: Edit CLAUDE_PERMANENT.md, then regenerate CLAUDE.md following REGENERATE_CLAUDE.md

**DO NOT Update PERMANENT During**:
- Normal feature development
- Bug fixes
- Testing individual integrations
- Adding new data sources following existing patterns
- Configuration changes

---

## LONG-TERM VISION & BIG PICTURE

### What We're Building
**SigInt Platform** - AI-Powered Investigative Journalism Platform

**Goal**: Enable journalists to conduct sophisticated multi-source research with:
- Natural language queries across 15+ government, social media, and document sources
- Automated Boolean monitoring with email/Slack alerts for ongoing investigations
- AI-powered analysis (summaries, entity extraction, timelines, network graphs)
- Team collaboration workspaces for shared investigations

**Current Reality**: ~60% complete. Core agentic research system working with 4 databases.

**End State**: Production platform in 3-6 months enabling investigative teams to:
1. Ask questions in plain English, get synthesized multi-source intelligence
2. Set up automated monitors that email daily digests of new matches
3. Collaborate on investigations with shared workspaces and annotations

### System Architecture (High-Level)
```
User Interfaces (Web/CLI/API)
    ↓
Request Router (Natural language or Boolean)
    ↓
┌─────────────────┬──────────────────┐
│ Boolean Monitor │  Agentic Research│
│ (Scheduled)     │  (On-Demand)     │
└────────┬────────┴────────┬─────────┘
         ↓                 ↓
    Query Builder
         ↓
┌────────────────────────────────┐
│ Data Sources (15+ planned)     │
│ • Government (SAM, FBI, etc.)  │
│ • Social (Reddit, Twitter)     │
│ • Documents (MuckRock, etc.)   │
└────────┬───────────────────────┘
         ↓
┌────────────────────────────────┐
│ Analysis Engine                │
│ • Summarization                │
│ • Entity extraction            │
│ • Timeline generation          │
└────────┬───────────────────────┘
         ↓
    Storage (PostgreSQL, Elasticsearch, S3)
```

**Full Details**: See INVESTIGATIVE_PLATFORM_VISION.md (75 pages)

### Phased Roadmap
- **Phase 0** (Foundation): 4 database integrations working - 90% complete
- **Phase 1** (Boolean Monitoring): Automated searches with alerts - NEXT
- **Phase 2** (Simple UI): Streamlit interface for team
- **Phase 3** (Social Media): Reddit, Twitter, 4chan integrations
- **Phase 4** (AI Analysis): LLM-powered synthesis
- **Phase 5** (Collaboration): Full team workspaces

**Estimated Timeline**: 3 months full-time / 6-8 months part-time to production

---

## CORE PRINCIPLES (MANDATORY - NEVER SKIP)

### 1. ADVERSARIAL TESTING MENTALITY (CRITICAL)

**Your job is to prove things DON'T work, not that they do.**

Assume all tests will fail. Your job is to find evidence they failed.
- Before claiming success, actively try to break it
- Test edge cases that would cause failure
- Look for what you CANNOT prove, not what you think works
- A well-documented limitation is more valuable than a fabricated success

**Why This Matters**: Claude Code systematically exaggerates success and sometimes fabricates evidence. Counteract this by assuming failure until proven otherwise.

**Examples**:
- ❌ WRONG: "ClearanceJobs integration complete! Everything working!"
- ✅ RIGHT: "ClearanceJobs test returns 5 jobs. UNVERIFIED: parallel execution, error handling, edge cases. LIMITATION: Slow on WSL2 (8s vs expected 5s)."
- ❌ WRONG: "EXCELLENT! DVIDS works perfectly! ✅"
- ✅ RIGHT: "DVIDS test passed: 1000 results in 1.1s via test script. UNVERIFIED: Integration with existing Streamlit UI."

### 2. EVIDENCE HIERARCHY (What Counts as Proof)

**Only these count as evidence**:

**Level 1 - Command Output** (Highest proof):
```bash
$ python3 test_verification.py
[PASS] SAM.gov: 12 results in 5.3s
[PASS] DVIDS: 1000 results in 1.2s
[FAIL] USAJobs: Connection timeout
```

**Level 2 - Error Messages** (Proof of failure):
```
Traceback (most recent call last):
  File "test.py", line 10
    ImportError: No module named 'playwright'
```

**Level 3 - User Execution** (Ultimate proof):
- User runs: `python3 apps/ai_research.py "query"`
- User receives: Valid results without your assistance
- User can repeat without errors

**NOT Evidence** (Never accept these):
- "This should work because..." (reasoning is not proof)
- "The code looks correct..." (code existing is not proof)
- "I implemented the pattern..." (implementation is not proof)
- "Tests passed" without showing output (claim is not proof)

**TIMEOUTS ARE FAILURES**: Any timeout counts as failure, not success. Fix performance or increase limits, never ignore.

### 3. FORBIDDEN CLAIMS & REQUIRED LANGUAGE

**NEVER use these phrases**:
- "Success!" / "Done!" / "Working!" / "Complete!"
- "EXCELLENT!" / "PERFECT!" / "Great!" / Celebration language
- "Should work" / "Probably works" / "Seems to work"
- "Almost there" / "Just needs..." / "Quick fix..."
- "Everything is working perfectly"
- Celebration emojis (✅, 🎉, ✨, etc.)

**ALWAYS use these instead**:
- "Test passed: [command] produced [output]"
- "Limitation found: [what doesn't work]"
- "Unverified: [what you haven't tested]"
- "Evidence: [command output]"
- "[PASS] Component X: [specific evidence]"
- "[FAIL] Component Y: [specific error]"
- "[BLOCKED] Component Z: [specific blocker]"

### 4. TASK SCOPE DECLARATION (Required Every Session)

**Before starting ANY work**, explicitly state:

```
SCOPE: [Exactly what you will verify this session]
NOT IN SCOPE: [What you will NOT verify this session]
SUCCESS CRITERIA:
  - Command: [exact command to run]
  - Expected: [exact expected output]
  - Time: [maximum acceptable time]
ESTIMATED IMPACT: [X of Y total requirements addressed]
```

**Why**: Prevents scope creep and false success claims. If you claim "integration complete" but only verified query generation, scope declaration catches this.

### 5. MANDATORY CHECKPOINTS (Every 15 Minutes)

**Stop and answer these 4 questions**:
1. What have I **proven** with command output?
2. What am I **assuming** without evidence?
3. What would break if I'm wrong?
4. What **haven't I tested** yet?

**Update your scope declaration if answers reveal gaps.**

If your "What I Don't Know" list gets shorter, you're probably not being adversarial enough.

### 6. NO LAZY IMPLEMENTATIONS

**Forbidden**:
- Mocking/stubs in production code
- Fallbacks that hide errors
- Pseudo-code marked as "TODO"
- Simplified implementations that don't meet requirements
- Workarounds that avoid the actual problem

**Required**:
- Real implementations or explicit documentation of what's missing
- Errors that fail loudly with full context
- If blocked, state the blocker clearly - don't fake functionality

### 7. FAIL-FAST AND LOUD

**All errors must be visible and actionable**:
- Surface errors immediately with full stack traces
- Log all validation failures with context
- NEVER swallow exceptions silently
- Include debugging information: what was attempted, what failed, why, how to fix
- Validation failures log before raising

**Logging Requirements**:
- Log all API calls (request + response time + error if any)
- Log all LLM queries (model + tokens + cost if available)
- Log all configuration loads
- Log all validation checks (pass/fail + reason)

### 8. DISCOVERY BEFORE BUILDING (CRITICAL - STOPS CIRCULAR WORK)

**BEFORE building ANY feature, ALWAYS check if it already exists.**

**Mandatory discovery steps at session start**:
1. Read STATUS.md - what's already [PASS]?
2. Read CLAUDE.md TEMPORARY section - what's the current task?
3. Check directory structure - does `apps/`, `core/`, `integrations/` already have this?
4. Test existing entry points FIRST - does it already work?

**Why This Matters**: Claude Code systematically rebuilds infrastructure that already exists, wasting time and creating duplicates. ALWAYS discover before building.

**Example of what NOT to do** (actual failure):
```
❌ WRONG:
1. Build test scripts for DVIDS/USAJobs
2. Test them and claim "EXCELLENT! Works perfectly!"
3. Write TESTED_INTEGRATIONS_REPORT.md
4. Discover apps/unified_search_app.py already exists
5. Write ACTUAL_STATUS.md apologizing
6. Go in circles

✅ RIGHT:
1. Read STATUS.md - see DVIDS/USAJobs marked [PASS]
2. Read CLAUDE.md TEMPORARY - see current task is ClearanceJobs
3. Test existing Streamlit app: streamlit run apps/unified_search_app.py
4. Report what works/doesn't work based on ACTUAL testing
5. Fix what's broken, don't rebuild what works
```

**Discovery checklist** (complete BEFORE starting work):
- [ ] Read STATUS.md for component status
- [ ] Read CLAUDE.md TEMPORARY section for current task
- [ ] Search for existing implementations: `find . -name "*keyword*.py" -not -path "./.venv/*"`
- [ ] Test existing user-facing entry points (apps/, not custom test scripts)
- [ ] Only build if discovery proves it doesn't exist or is broken

**If you find existing infrastructure**:
- Report its status (working/broken/needs update)
- Test it through user-facing entry points
- Fix/extend it rather than rebuilding
- Update STATUS.md with findings

### 9. CIRCUIT BREAKERS - HARD STOP CONDITIONS

**When ANY of these occur, STOP immediately and report to user**:

**1. Import Errors on Entry Points**:
```python
$ python3 apps/ai_research.py "query"
ImportError: No module named 'playwright'
```
**Action**: STOP. Report missing dependency, provide install command, do NOT continue.

**2. Repeated Timeouts** (3+ consecutive):
```
[FAIL] SAM.gov: Timeout after 30s
[FAIL] SAM.gov: Timeout after 30s (retry 1)
[FAIL] SAM.gov: Timeout after 30s (retry 2)
```
**Action**: STOP. This is systematic failure, not transient issue. Report blocker, do NOT mark as "almost working."

**3. Scope Drift** (doing more than declared):
- Declared scope: "Test ClearanceJobs integration"
- Actual work: Also rebuilding parallel executor, refactoring config, updating all tests
**Action**: STOP. Return to declared scope or update scope declaration first.

**4. No Evidence After 30 Minutes**:
- 30 minutes of work
- Zero passing tests with command output
- Only reasoning, code changes, or "should work" claims
**Action**: STOP. You're in speculation mode. Run actual tests or report blocker.

**5. Circular Work** (repeating same failed approach):
- Attempt 1: Build custom test, claim success
- Attempt 2: Build different custom test, claim success
- Attempt 3: Build third custom test, claim success
- Never tested actual user-facing entry point
**Action**: STOP. You're avoiding the real test. Test through apps/ entry point or report why you can't.

**6. Configuration File Not Found**:
```
FileNotFoundError: .env file not found
FileNotFoundError: config.yaml not found
```
**Action**: STOP. Don't create fake config or use defaults silently. Report missing config, show user how to create it.

**7. API Quota/Rate Limit Exceeded**:
```
HTTP 429: Rate limit exceeded
HTTP 402: Quota exceeded
```
**Action**: STOP. Report quota issue, estimate wait time or cost to continue. Don't retry in tight loop.

**8. Git Conflicts or Dirty State** (if user requested commit):
```
error: Your local changes to the following files would be overwritten by merge
```
**Action**: STOP. Report git state, ask user how to proceed. Don't force push or discard changes.

**Why Circuit Breakers Matter**: Claude Code has systematic bias toward "trying one more thing" even when blocked. Circuit breakers force acknowledgment of fundamental blockers rather than endless workarounds.

**What to Report When Circuit Breaker Triggers**:
1. Which circuit breaker triggered
2. Evidence (error message, timeout count, etc.)
3. What you were attempting
4. Recommended user action to unblock
5. Estimated impact if not fixed

---

## DIRECTORY STRUCTURE & FILE MANAGEMENT

### Current Repository Structure
```
sam_gov/
├── CLAUDE.md                    # This file (permanent + temp sections)
├── CLAUDE_PERMANENT.md          # Source: permanent section (for regeneration)
├── CLAUDE_TEMP.md               # Source: temporary section template (for regeneration)
├── STATUS.md                    # Component status [PASS]/[BLOCKED]
├── PATTERNS.md                  # Code templates for current phase
├── REGENERATE_CLAUDE.md         # Instructions for regenerating CLAUDE.md
├── INVESTIGATIVE_PLATFORM_VISION.md  # 75-page complete vision
│
├── core/                        # Research engines
│   ├── agentic_executor.py      # Self-improving search
│   ├── parallel_executor.py     # Multi-DB parallel execution
│   ├── intelligent_executor.py  # Query generation & routing
│   ├── database_integration_base.py  # Abstract base for integrations
│   ├── database_registry.py     # Central source registry
│   ├── api_request_tracker.py   # Rate limiting & cost tracking
│   ├── adaptive_analyzer.py     # Adaptive query refinement
│   └── result_analyzer.py       # Result quality analysis
│
├── integrations/                # Data source adapters
│   ├── registry.py              # Integration registry
│   ├── government/              # Government data sources
│   │   ├── sam_integration.py       # SAM.gov (federal contracts)
│   │   ├── dvids_integration.py     # DVIDS (military media)
│   │   ├── usajobs_integration.py   # USAJobs (federal jobs)
│   │   ├── clearancejobs_integration.py      # ClearanceJobs wrapper
│   │   ├── clearancejobs_playwright.py       # Playwright scraper
│   │   └── fbi_vault.py             # FBI Vault (blocked by Cloudflare)
│   └── social/                  # Social media sources (future)
│       └── __init__.py
│
├── apps/                        # User-facing entry points
│   ├── ai_research.py           # CLI for natural language research
│   └── unified_search_app.py    # Streamlit web UI
│
├── tests/                       # All test scripts (18 files)
│   ├── test_verification.py     # E2E verification
│   ├── test_cost_tracking.py    # Cost tracking test
│   ├── test_all_four_databases.py  # 4-DB parallel test
│   ├── test_clearancejobs_playwright.py  # ClearanceJobs test
│   ├── test_live.py             # Live API tests
│   ├── test_usajobs_live.py     # USAJobs live test
│   └── ... (12 more test files)
│
├── monitoring/                  # Future: MonitorEngine, AlertManager
│   └── __init__.py
│
├── research/                    # Future: Research workflows
│   └── __init__.py
│
├── utils/                       # Utility functions
│   └── __init__.py
│
├── data/                        # Runtime data storage
│   ├── articles/                # Extracted articles
│   ├── exports/                 # Export files
│   ├── logs/                    # Application logs
│   └── monitors/                # Monitor configurations
│
├── docs/                        # Documentation
│   ├── PLAYWRIGHT_MIGRATION.md
│   ├── COST_TRACKING_AND_GPT5_NANO.md
│   └── examples/                # Working examples
│
├── experiments/                 # Experimental code
│   ├── discord/                 # Discord integrations
│   ├── scrapers/                # Experimental scrapers
│   └── tag_management/          # Tag system experiments
│
├── scripts/                     # Maintenance scripts
│   └── update_to_use_config.py
│
├── archive/                     # Completed work & obsolete code
│   ├── YYYY-MM-DD/             # Dated archives (most recent first)
│   ├── v1/                      # Version 1 implementations
│   ├── standalone/              # Standalone prototypes
│   ├── test_scripts/            # Old test scripts
│   └── tag_system/              # Tag system (archived)
│
├── ClearanceJobs/               # Reference: Official Python library (broken API)
├── api-code-samples/            # Reference: Official DVIDS API examples
├── bills_blackbox_articles_extracted/  # Data: Extracted articles (20MB)
├── klippenstein_articles_extracted/    # Data: Extracted articles (90MB)
│
├── .env                         # API keys (gitignored, NEVER commit)
├── .venv/                       # Virtual environment
├── config_default.yaml          # Default configuration
├── config.yaml                  # Local overrides (gitignored)
├── llm_utils.py                 # Unified LLM wrapper (ALWAYS use this)
├── config_loader.py             # Configuration management
├── extract_keywords_for_boolean.py  # Keyword extraction utility
└── organize_keywords.py         # Keyword organization utility
```

### Archive Strategy

**When archiving old code/experiments**:
1. Create directory: `archive/YYYY-MM-DD/`
2. Mirror main directory structure inside archive date folder
3. Move files to corresponding archive subdirectory
4. Create `archive/YYYY-MM-DD/README.md` explaining:
   - What was archived
   - Why it was archived
   - Date archived
   - Whether preserved for reference or truly obsolete

**Example**:
```
archive/
  2025-10-18/
    integrations/
      clearancejobs_puppeteer.py  # Replaced by Playwright
    tests/
      deprecated_test.py
    README.md  # "Archived Puppeteer implementation, replaced by Playwright"
```

### File Finding Guide

**When you need**:
- Current task? → Read CLAUDE.md (TEMPORARY section)
- Core principles? → Read CLAUDE.md (PERMANENT section)
- Is X working? → Read STATUS.md
- How to implement Y? → Read PATTERNS.md
- Why are we doing this? → Read INVESTIGATIVE_PLATFORM_VISION.md
- Specific tech details? → Read docs/[topic].md
- Working code example? → Copy from integrations/government/sam_integration.py
- Regenerate CLAUDE.md? → Follow REGENERATE_CLAUDE.md
- What's archived? → Check archive/YYYY-MM-DD/README.md

### Information Architecture (Multi-Layer Documentation System)

**How Documentation Layers Work Together**:

This project uses a 4-layer documentation system to separate vision, planning, reality, and current work:

**Layer 1 - Strategic (Vision)**:
- **File**: INVESTIGATIVE_PLATFORM_VISION.md (75 pages)
- **Purpose**: Long-term architectural target, end-state requirements, why we're building this
- **Update Frequency**: Rarely (only when vision changes)
- **Audience**: New team members, stakeholders, architectural decisions

**Layer 2 - Tactical (Plans)**:
- **File**: ROADMAP.md
- **Purpose**: Phase-by-phase implementation plan extracted from vision
- **Contains**: Objectives, success criteria, deliverables, timelines for each phase
- **Update Frequency**: When phases complete or plans change
- **Audience**: Project planning, milestone tracking

**Layer 3 - Reality (Status)**:
- **File**: STATUS.md
- **Purpose**: What's actually working vs what's planned, with evidence
- **Contains**: Component status ([PASS]/[FAIL]/[BLOCKED]), evidence, gaps, limitations
- **Update Frequency**: After every integration/feature completion
- **Audience**: Truth check - what can we actually use right now?

**Layer 4 - Operational (Current Work)**:
- **File**: CLAUDE.md (TEMPORARY section)
- **Purpose**: This week's focus, next 3 actions, immediate blockers
- **Contains**: Current task scope, next actions with prerequisites, checkpoint answers
- **Update Frequency**: Multiple times per session as tasks complete
- **Audience**: Active development guidance

**How Layers Interact**:
```
VISION (target) → ROADMAP (plan) → STATUS (reality) → CLAUDE.md (today's work)
     ↓                ↓                 ↓                    ↓
  "What we         "How we           "What we           "What I'm
   want"            plan it"          actually have"      doing now"
```

**Before Starting Work** (Discovery Protocol):
1. Read CLAUDE.md TEMPORARY → What's the current task?
2. Read STATUS.md → What's already built? What's working?
3. Read ROADMAP.md → Where does this fit in the plan?
4. Test existing entry points → Does it already work?
5. Only build if discovery proves it doesn't exist or is broken

**After Completing Work**:
1. Update STATUS.md with evidence ([PASS]/[FAIL]/[BLOCKED])
2. Update CLAUDE.md TEMPORARY with next actions
3. If phase complete, update ROADMAP.md with actual results
4. Update PATTERNS.md if new reusable pattern emerged

**Why This Matters**: Prevents rebuilding existing infrastructure, keeps vision/reality aligned, provides clear current focus.

---

## ENVIRONMENT SETUP (CRITICAL)

### API Keys & Environment Variables

**ALWAYS load using python-dotenv**:

```python
from dotenv import load_dotenv
import os

load_dotenv()  # Loads .env file

api_key = os.getenv('OPENAI_API_KEY')
sam_key = os.getenv('SAM_GOV_API_KEY')
```

**Required in .env file** (create if doesn't exist, gitignored):
```bash
OPENAI_API_KEY=sk-...
SAM_GOV_API_KEY=...
DVIDS_API_KEY=...
USAJOBS_API_KEY=...
```

**NEVER**:
- Hardcode API keys in code
- Commit .env to git
- Use environment variables without python-dotenv
- Access os.environ directly without load_dotenv()

### Python Environment
- Version: 3.12
- Virtual env: `.venv/` (activate: `source .venv/bin/activate`)
- Dependencies: `requirements.txt` (install: `pip install -r requirements.txt`)
- Update requirements: `pip freeze > requirements.txt`

---

## CODE PATTERNS (PERMANENT)

### LLM Calls (CRITICAL - ALWAYS USE THIS)

```python
from llm_utils import acompletion
from dotenv import load_dotenv
import json

load_dotenv()  # ALWAYS load environment first

response = await acompletion(
    model="gpt-5-mini",  # or gpt-5-nano for cost savings
    messages=[{"role": "user", "content": prompt}],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "strict": True,
            "name": "schema_name",
            "schema": {
                "type": "object",
                "properties": {...},
                "required": [...],
                "additionalProperties": False
            }
        }
    }
)

result = json.loads(response.choices[0].message.content)
```

**NEVER DO THIS**:
```python
# WRONG - don't call litellm directly
response = await litellm.acompletion(...)

# WRONG - BREAKS gpt-5 models (exhausts reasoning tokens)
response = await acompletion(model="gpt-5-mini", max_tokens=500)
response = await acompletion(model="gpt-5-mini", max_output_tokens=500)
```

**WHY**: gpt-5 models use reasoning tokens before output tokens. Setting max_output_tokens exhausts budget on reasoning, returns empty output.

### Database Integration Pattern

**Copy from**: `integrations/sam_integration.py` (complete working example)

**Required structure**:
```python
from dotenv import load_dotenv
from core.database_integration_base import DatabaseIntegration, QueryResult
from llm_utils import acompletion

load_dotenv()

class NewIntegration(DatabaseIntegration):
    @property
    def metadata(self) -> DatabaseMetadata:
        # Return metadata about this source
        pass

    async def is_relevant(self, research_question: str) -> bool:
        # Quick keyword check BEFORE expensive LLM call
        pass

    async def generate_query(self, research_question: str) -> Optional[Dict]:
        # Use LLM to generate source-specific query params
        # Return None if not relevant
        pass

    async def execute_search(self, query_params, api_key, limit) -> QueryResult:
        # Execute API call, return standardized QueryResult
        pass
```

**After creating**:
1. Save in `integrations/government/` or `integrations/social/`
2. Register in `integrations/registry.py`
3. Create test in `tests/`: `test_newsource_live.py`
4. Test end-to-end via: `python3 apps/ai_research.py "test query"`
5. Update STATUS.md with [PASS] or [BLOCKED]

---

## TESTING REQUIREMENTS

### Test Categories

**1. Unit Tests** (Isolated Components):
- Test individual functions/classes in isolation
- May mock external dependencies
- Fast, repeatable, deterministic
- Examples: `test_cost_tracking.py`

**2. Integration Tests** (Multiple Components):
- Test how components work together
- May call real APIs with test limits
- Examples: `test_verification.py`, `test_all_four_databases.py`

**3. End-to-End Tests** (REQUIRED for Success Claims):
- Test through actual user-facing entry points
- NO mocking, real APIs, real configuration
- User can execute without your assistance
- Examples: `python3 apps/ai_research.py "query"`

### Testing Checklist (Before Claiming Success)

**ALL must be true**:
- [ ] All imports resolve without errors
- [ ] Configuration loads from documented files (.env, config.yaml)
- [ ] API calls succeed with real credentials
- [ ] Results match expected format
- [ ] Error cases handled gracefully (tested with invalid input)
- [ ] User can execute without your assistance
- [ ] No timeouts or hanging processes
- [ ] Logging shows expected flow
- [ ] Cost tracking records the operation (if LLM used)

**If ANY checkbox is false, you have NOT succeeded.**

---

## KNOWN ISSUES & PERMANENT WORKAROUNDS

### gpt-5 Models - NEVER Use max_tokens
**Issue**: gpt-5 models use reasoning tokens before output tokens
**Symptom**: Setting max_output_tokens causes empty responses
**Solution**: llm_utils.py strips these parameters automatically
**Status**: PERMANENT - always use llm_utils.acompletion()

### ClearanceJobs - Official API is Broken
**Issue**: Official Python library returns all 57k jobs regardless of query
**Symptom**: Irrelevant results, cannot filter
**Solution**: Use Playwright to scrape actual website
**Impact**: Slower (5-8s vs 2s) but accurate
**Status**: PERMANENT - use clearancejobs_playwright.py

### USAJobs - Requires Specific Headers
**Issue**: API returns 401 if headers incorrect
**Required Headers**:
  - `User-Agent: email@example.com`
  - `Authorization-Key: [key]` (NOT "Bearer [key]")
**Status**: Fixed in usajobs_integration.py

---

## ESSENTIAL TESTS & TOOLS

**Philosophy**: With LLM assistance, only keep tests/tools valuable enough for context window. Most should be regenerated on-demand from patterns.

**Tests Worth Keeping** (complex integration, hard to regenerate):
- `tests/test_all_four_databases.py` - Validates parallel execution across all 4 databases
- `tests/test_verification.py` - E2E verification of core integrations with real APIs
- **Why Keep**: Complex setup specific to our multi-source architecture, validates critical parallel execution

**Tests to Regenerate On-Demand** (simple, pattern-based):
- Unit tests for individual integrations (follow DATABASE_INTEGRATION_PATTERN)
- API-specific tests (straightforward API validation)
- Cost tracking tests (trivial validation logic)
- **Why Regenerate**: Simple, follows established patterns, easy to recreate from PATTERNS.md

**Tools Worth Keeping** (non-obvious quirks):
- `llm_utils.py` - Critical wrapper for gpt-5 reasoning tokens issue (max_output_tokens breaks gpt-5)
- `config_loader.py` - Environment setup pattern with python-dotenv
- `integrations/government/sam_integration.py` - Reference implementation of DATABASE_INTEGRATION_PATTERN
- **Why Keep**: Non-obvious workarounds and reference implementations that would be lost if regenerated

**Tools to Regenerate On-Demand** (simple utilities):
- CLI test scripts
- Data extraction utilities
- One-off analysis scripts
- Keyword extraction tools
- **Why Regenerate**: Simple utilities, not worth context window space, easy to recreate when needed

**Entry Points (Always Keep These)**:
- `apps/ai_research.py` - CLI for natural language research
- `apps/unified_search_app.py` - Streamlit web UI
- **Why**: User-facing interfaces, test through these not custom scripts

---

## QUICK REFERENCE COMMANDS

```bash
# Environment
source .venv/bin/activate        # Activate virtual environment
pip install -r requirements.txt  # Install dependencies

# Testing (use these entry points - essential tests only)
python3 apps/ai_research.py "query"           # E2E test via CLI
python3 tests/test_verification.py            # Integration test (keep)
python3 tests/test_all_four_databases.py      # 4-DB parallel test (keep)
streamlit run apps/unified_search_app.py      # Web UI

# Development
pip freeze > requirements.txt    # Update dependencies
python3 -c "import X; print('OK')"  # Test import
```

---

**END OF PERMANENT SECTION**
**Everything above this line NEVER changes**
**Everything below this line is updated as tasks complete**

---
