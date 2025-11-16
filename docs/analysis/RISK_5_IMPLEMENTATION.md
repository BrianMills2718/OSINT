# Risk #5: Implementation / Maintenance Risk

**Severity**: MEDIUM
**Category**: Operational / Technical Debt
**Date**: 2025-11-15

---

## The Problem

Open-source deep-research repos:
- Change APIs
- May be less maintained
- Bring their own dependency stack

**Risks**:
1. **API churn**: Upgrading GPT Researcher or DeerFlow might break your adapter
2. **Dependency hell**: Each repo has opinions about Python version, libraries, etc.
3. **Over-commitment**: If you wire their internals directly into your database, you're stuck

---

## Real-World Evidence

### Your Current Architecture (deep_research.py)

**Dependency Analysis** (from requirements.txt + code review):
- **Core LLM**: litellm (abstraction over OpenAI/Anthropic/Gemini)
- **Search integrations**: Custom-built (SAM, USAJobs, ClearanceJobs, Twitter, Reddit, Discord, Brave)
- **No external research frameworks**: NOT using GPT-Researcher/DeerFlow/etc. (built your own)

**Architecture Strength**: Clean abstraction layers
- `DatabaseIntegration` base class (lines 25-80 in integrations/government/sam_integration.py)
- Registry pattern (`integrations/registry.py`)
- Each integration is self-contained module

**Observed Stability**:
- CLAUDE.md Known Issues (lines 1140-1160):
  - gpt-5 models: max_tokens breaks reasoning (workaround: use llm_utils.acompletion)
  - ClearanceJobs API broken (workaround: playwright scraper)
  - USAJobs requires specific headers (documented)

**Assessment**: You've already hit API churn issues (gpt-5 behavior, ClearanceJobs API deprecation) but handled them with workarounds

### From Mozart Investigation

**Mozart Dependencies** (from pyproject.toml in backup):
```toml
[dependencies]
httpx = "*"
pydantic = "*"
jinja2 = "*"
fastapi = "*"
uvicorn = "*"
trafilatura = "*"  # HTML to text
pdfminer = "*"
pytesseract = "*"
google-generativeai = "*"
anthropic = "*"
playwright = "*"
```

**Architecture**: No external frameworks, all custom-built
- Similar to your approach (build core logic, use API SDKs directly)

**Maintenance Status**:
- Last commit: Unknown (no git history in backup)
- Still operational (130+ pages on wikidisc.org)
- No evidence of major breakage

**Assessment**: Custom-built systems have LOWER dependency risk than framework-dependent systems

### V1 Design Proposal (Wrapping Existing Frameworks)

**V1 doc says** (lines 193-296):
> "Reuse existing deep-research libraries (GPT-Researcher / Deep Research / DeerFlow) as the engine."
> "Your system wraps these instead of re-implementing them."

**Dependency Implications**:
- GPT-Researcher dependencies: ~20 packages (langchain, requests, playwright, selenium, etc.)
- DeerFlow dependencies: Unknown (less mature project)
- Framework version lock: Upgrading framework might break your adapter

**Risk Assessment**: V1 design has HIGHER dependency risk than your current architecture

---

## Severity Assessment: MEDIUM

**Why Medium**:
- **Not immediate**: Dependencies don't break overnight (usually)
- **Manageable**: Pin versions, use virtual environments, document workarounds
- **Common problem**: All software has dependency management issues

**But Not Low Because**:
- **Time sink**: API churn requires maintenance (updating adapters, testing, workarounds)
- **Fragmentation risk**: Each framework upgrade is a potential breaking change
- **Unknown unknowns**: Don't know which dependencies will break until they do

**When This Becomes High/Critical**:
- Framework abandonment (author stops maintaining GPT-Researcher)
- Major API redesign (v1 → v2 breaking changes)
- Dependency conflicts (Framework A requires library v1, Framework B requires library v2, both needed)

---

## V1 Doc Proposed Mitigations

1. **Clean abstraction**: `DeepResearchClient` interface
   - Your app knows only: `run_research(query, params) -> ResearchResult`
   - Everything else is adapter-internal

2. **Pin versions**: requirements.txt or poetry/pipenv locks

3. **Dumb fallback**: Script that builds 3-5 Brave queries, fetches pages, asks LLM to summarize
   - If fancy engine breaks, you're not dead

---

## Additional Mitigations

### Mitigation A: Don't Use External Frameworks (Your Current Approach)

**Observation**: You've already built a working deep research system WITHOUT GPT-Researcher/DeerFlow

**Current Architecture** (research/deep_research.py):
- Task decomposition: Custom LLM prompt
- Source selection: Custom multi-source orchestration
- Search execution: Direct integration APIs (MCP tools + custom adapters)
- Synthesis: Custom Jinja2 templates + LLM calls

**Lines of Code**: ~2800 lines (manageable, understandable)

**Dependency Count**: ~15 packages (litellm, httpx, pydantic, jinja2, playwright, plus API SDKs)

**Comparison to Framework Approach**:
- GPT-Researcher: ~5000+ lines (framework code) + your adapter (~500 lines)
- Your current: ~2800 lines (all yours)

**Maintenance Burden**:
- Framework: Upgrade GPT-Researcher → test adapter → fix breaks
- Your current: Upgrade individual SDKs → fix breaks (but you control the logic)

**Recommendation**: **DON'T wrap external frameworks for V1**
- You already have working research engine
- Adding GPT-Researcher/DeerFlow would INCREASE complexity, not decrease it
- Custom architecture gives you full control

### Mitigation B: Adapter Pattern for Integrations (Already Implemented)

**Your Current Pattern** (integrations/government/sam_integration.py):
```python
class SAMIntegration(DatabaseIntegration):
    @property
    def metadata(self) -> DatabaseMetadata: ...
    async def is_relevant(self, question: str) -> bool: ...
    async def generate_query(self, question: str) -> Optional[Dict]: ...
    async def execute_search(self, params, key, limit) -> QueryResult: ...
```

**Benefit**: Each integration is isolated
- ClearanceJobs API breaks? Only affects clearancejobs_integration.py
- Can swap implementations (API → scraper) without touching core logic

**Already Proven**: ClearanceJobs API deprecated → swapped to Playwright scraper (clearancejobs_playwright_fixed.py) without breaking anything

### Mitigation C: Dependency Isolation (Virtual Environments)

**Current Practice** (from CLAUDE.md lines 860-880):
```bash
source .venv/bin/activate  # MANDATORY
python3 script.py
```

**Enhancement**: Per-integration virtual environments (overkill for V1, but possible)
- Core system: .venv/
- Heavy dependencies (Playwright): .venv-playwright/
- Allows upgrading Playwright without risking core deps

**Benefit**: Blast radius containment

### Mitigation D: Automated Dependency Checks

**Tool**: dependabot / pip-audit
**Workflow**: Monthly check for:
- Security vulnerabilities
- Deprecated packages
- Breaking changes in dependencies

**Action**: Create GitHub issue, test upgrades in branch, merge if safe

---

## Implementation Priority

### Must-Have (P0)
1. **Clean abstraction** (V1 doc #1) - ✅ Already implemented (DatabaseIntegration base class)
2. **Pin versions** (V1 doc #2) - ✅ Already doing (requirements.txt exists)

### Should-Have (P1)
3. **Dumb fallback** (V1 doc #3) - ~2-3 hours (simple Brave search → LLM summary script)
4. **Dependency monitoring** (Mitigation D) - ~1 hour setup (GitHub dependabot config)

### Nice-to-Have (P2)
5. **Per-integration venvs** (Mitigation C) - Overkill for V1
6. **Automated integration tests** - Good hygiene, but not specific to this risk

---

## Open Questions

1. **Should V1 use external frameworks at all?**
   - V1 doc assumes yes (wrap GPT-Researcher/DeerFlow)
   - Your current system says no (custom-built is working)
   - **Recommendation**: Stick with custom (lower dependency risk)

2. **How often will integrations break?**
   - Hypothesis: 1-2 per year (based on ClearanceJobs API deprecation as example)
   - Test: Track integration failures over first year

3. **Is dumb fallback actually useful?**
   - Idea: Simple Brave search → LLM summary (50 lines of code)
   - Reality: If deep_research.py breaks, might indicate larger system problem
   - Test: Implement fallback, see if it's ever used

---

## Recommended V1 Approach

**Diverge from V1 Doc on Framework Dependency**:

V1 doc proposes:
> "Wrap GPT-Researcher / Deep Research / DeerFlow as the engine"

**Alternative (based on your current architecture)**:
> "Use your existing deep_research.py as the engine, enhance it with V1 wiki features"

**Rationale**:
1. **Already working**: deep_research.py does task decomposition, multi-source search, synthesis
2. **Lower dependency risk**: No external framework to maintain
3. **Full control**: Can optimize for your specific use case (investigative journalism, not generic Q&A)
4. **Cleaner architecture**: V1 wiki wraps your engine, not a third-party engine

**V1 Integration Architecture**:
```
V1 Wiki (Lead/Evidence/Entity/Claim storage)
    ↓
deep_research.py (research engine)
    ↓
Integrations (SAM, USAJobs, ClearanceJobs, Twitter, Reddit, Brave, etc.)
```

**NOT**:
```
V1 Wiki
    ↓
GPT-Researcher (external framework)
    ↓
Tavily / Firecrawl (their integrations)
```

**Maintenance Story**:
- Upgrade litellm → test → fix if broken (infrequent, well-maintained library)
- Upgrade Anthropic SDK → test → fix if broken (stable API)
- Upgrade custom integrations → fix individually (isolated breakage)

**vs. Framework Approach**:
- Upgrade GPT-Researcher → breaks internal APIs → spend 8 hours debugging adapter logic
- Framework author abandons project → now you're maintaining fork OR rewriting from scratch

---

## Final Assessment

**Risk Severity**: MEDIUM (maintenance tax, not existential)

**V1 Mitigations Adequacy**: GOOD (if following V1 doc approach)
- Clean abstraction: ✅ Limits blast radius
- Pin versions: ✅ Prevents surprise breaks
- Dumb fallback: ✅ Emergency escape hatch

**Alternative Recommendation**: **REJECT framework dependency assumption**
- Your current architecture (custom deep_research.py) has LOWER risk than wrapping GPT-Researcher
- V1 wiki should build on your existing engine, not replace it with external framework

**Bottom Line**: This risk is **manageable with discipline** (pin versions, isolate dependencies, test upgrades). But the BEST mitigation is **minimizing external dependencies** in the first place. Since you already have a working research engine, don't add framework dependency just because V1 doc assumed you'd need one.

**Actionable**: Update V1 design doc to reflect "use existing deep_research.py" not "wrap GPT-Researcher"
