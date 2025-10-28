# Deep Research Architectural Improvements

**Created**: 2025-10-28
**Status**: APPROVED - Ready for Implementation
**Branch**: `feature/supervisor-flow`
**Estimated Time**: 8-12 hours over 2 weeks

---

## Executive Summary

This document outlines architectural improvements to the SigInt deep research system based on analysis of leading open-source frameworks (GPT Researcher, Open Deep Research, DeerFlow) and validation by Codex LLM.

**Core Problem**: Current architecture lacks formal planning stages, leading to inefficient API usage and inability to handle complex multi-faceted queries.

**Solution**: Implement industry-standard `Scope → Plan → Execute → Synthesize` workflow with conservative defaults and graceful fallbacks.

**Key Principles** (Codex-Validated):
1. Don't break existing functionality (config-driven rollout)
2. Conservative scoping (don't nag users with clear queries)
3. Deterministic schemas (Pydantic models, strict JSON)
4. Single workflow with fallback (no parallel code paths)
5. Incremental rollout (CLI first, Streamlit later)

---

## Current Architecture (As-Is)

```
User Query → IntelligentExecutor → ParallelExecutor → [All 8 Sources] → Results
```

**Limitations**:
- No query clarification (vague queries waste API calls)
- No task decomposition (complex queries get shallow results)
- No user approval (expensive queries run without confirmation)
- No source routing (all sources always called, even when irrelevant)
- Single model for all tasks (no cost optimization)

**Example**: Query "Map relationships between defense contractors working on AI security" currently:
1. Fires all 8 sources in parallel (some irrelevant)
2. Gets shallow results (no subtask decomposition)
3. No opportunity to refine scope before execution
4. Costs $0.50-$2.00 without user knowledge

---

## Target Architecture (To-Be)

```
User Query
    ↓
ScopingAgent (clarify if needed, generate research brief)
    ↓
HumanInTheLoop (CLI approval: y/n/edit)
    ↓
ResearchSupervisor
    ↓
[Task Decomposition]
    ↓
Worker 1 (Contracts) → [SAM.gov, USAJobs, ClearanceJobs]
Worker 2 (Intel) → [DVIDS, FBI Vault]
Worker 3 (Social) → [Twitter, Discord, Reddit]
    ↓
[Synthesis] → Final Report
```

**Improvements**:
- ✅ Query clarification (only when needed)
- ✅ Structured planning (deterministic brief schema)
- ✅ User approval (cost/time estimates before execution)
- ✅ Smart routing (category-based source selection)
- ✅ Parallel subtasks (independent workers)
- ✅ Cost optimization (role-based models ready)

---

## Architectural Components

### 1. ScopingAgent

**Purpose**: Transform user query into structured research brief

**Key Features**:
- Conservative clarification (only for vague queries)
- Deterministic brief schema (Pydantic validation)
- Prevents scope creep (max 5 subtasks)
- Direct passthrough for simple queries

**Schema**:
```python
class ResearchBrief(BaseModel):
    objective: str              # 1-2 sentence research goal
    sub_questions: List[SubQuestion]  # 1-5 decomposed questions
    constraints: Dict[str, str] # timeframe, geography, etc.
    estimated_cost: float       # LLM token cost estimate
    estimated_time: int         # Execution time estimate (seconds)

class SubQuestion(BaseModel):
    question: str                    # Specific sub-question
    rationale: str                   # Why this subtask matters
    suggested_categories: List[str]  # Source routing hints
```

**Behavior**:
```python
# Simple query (no decomposition)
query = "What is SAM.gov?"
brief = await scoping_agent.generate_brief(query)
# Returns: 1 sub_question (original query verbatim)

# Complex query (decomposition)
query = "Map defense contractor AI security relationships"
brief = await scoping_agent.generate_brief(query)
# Returns: 3-5 sub_questions (partnerships, contracts, events, etc.)
```

**Configuration**:
```yaml
research:
  max_subtasks: 5                # Max decomposition depth
  auto_clarify_threshold: 0.7    # Confidence score to skip clarification
```

---

### 2. ResearchSupervisor

**Purpose**: Execute research brief via task delegation and source routing

**Key Features**:
- Category-based source routing (uses `DatabaseMetadata.category`)
- Parallel subtask execution (independent workers)
- Graceful degradation (fallback to shotgun if routing fails)
- Result synthesis (aggregate findings)

**Routing Logic**:
```python
# Example routing for sub-question
sub_question = SubQuestion(
    question="What contracts has Peraton won for AI security?",
    suggested_categories=["government_contracts", "jobs"]
)

# Maps to sources:
# - SAM.gov (category: "government_contracts")
# - USAJobs (category: "government_jobs")
# - ClearanceJobs (category: "government_jobs")

# Does NOT call: Twitter, Discord, Reddit, FBI Vault
```

**Edge Case Handling**:
```python
# If no sources match categories → fallback to all sources
if not matched_sources:
    logging.warning(f"No matches for {categories}, using all sources")
    matched_sources = registry.list_enabled_ids()
```

**Metadata Extension** (for edge cases):
```python
# Add optional tags to DatabaseMetadata
class DatabaseMetadata:
    name: str
    category: str
    tags: List[str] = []  # NEW: fine-grained routing

# Example: SAM.gov
metadata = DatabaseMetadata(
    name="SAM.gov",
    category="government_contracts",
    tags=["procurement", "federal_spending", "awards"]
)

# Now sub-questions can route via tags:
suggested_categories = ["procurement"]  # Matches SAM.gov via tags
```

---

### 3. HumanInTheLoop (HITL)

**Purpose**: Get user approval before executing expensive research plans

**Phase 1: CLI Only**
```
RESEARCH PLAN
================================================================================
Objective: Map defense contractor AI security relationships

Sub-questions (4):
  1. What partnerships exist between defense contractors and AI labs?
     → Sources: government_contracts, social_media
  2. What subcontracting relationships are documented?
     → Sources: government_contracts
  3. What DoD engagement events have occurred?
     → Sources: government_media
  4. What workforce hiring patterns exist?
     → Sources: jobs

Estimated cost: $1.20
Estimated time: 45s
================================================================================

Approve plan? [y/n/edit]:
```

**User Options**:
- `y`: Proceed with execution
- `n`: Abort research
- `edit`: Provide feedback, regenerate plan

**Phase 2: Streamlit** (Future Work)
- Non-blocking approval UI
- Plan visualization (graph view)
- Interactive editing (add/remove subtasks)

**Configuration**:
```yaml
research:
  enable_hitl: true  # Enable/disable approval flow
```

---

### 4. Model Role Specialization

**Purpose**: Optimize cost/quality by using appropriate models for each task

**Phase 1: Stub API (Single Model)**
```python
# All roles use same model initially
async def acompletion_with_role(role: str, messages: List[Dict], **kwargs):
    model = "gpt-5-mini"  # Same for all roles
    return await acompletion(model=model, messages=messages, **kwargs)
```

**Phase 2: Cost Optimization** (After Validation)
```python
MODEL_ROLES = {
    "scoping": "gpt-5-mini",        # Requires reasoning
    "research": "gpt-5-mini",        # Core intelligence
    "summarization": "gpt-5-nano",   # Bulk text processing (70% cheaper)
    "synthesis": "gpt-5-mini",       # Final report quality
}

# Example savings:
# 100 searches × 8 sources = 800 API calls
# If 60% are summarization (480 calls):
#   - Before: 480 × $0.10 = $48
#   - After: 480 × $0.03 = $14.40
#   - Savings: $33.60 per research run (70% reduction)
```

**Configuration**:
```yaml
research:
  model_roles:
    scoping: "gpt-5-mini"
    research: "gpt-5-mini"
    summarization: "gpt-5-mini"  # Change to gpt-5-nano after validation
    synthesis: "gpt-5-mini"
```

---

## Implementation Plan

### Phase 1A: Foundations (2-3 hours)

**Goal**: Add scaffolding without breaking existing code

**Files to Create**:
```
core/
  scoping_agent.py       # Brief generation + clarification
  research_supervisor.py # Task decomposition + delegation
  hitl.py               # Plan approval (CLI only)

schemas/
  research_brief.py     # Pydantic models for deterministic schema
```

**Files to Modify**:
```
core/intelligent_executor.py  # Add supervisor path
core/parallel_executor.py     # Add execute_with_sources() method
config_default.yaml           # Add research.* settings
llm_utils.py                  # Add acompletion_with_role() stub
```

**Success Criteria**:
- [ ] All existing tests pass (no regressions)
- [ ] New features disabled by default (config-driven)
- [ ] Can generate research brief from query (unit test)

**Testing**:
```bash
# Verify no regressions
pytest tests/ -v

# Verify new code exists but inactive
python3 -c "from core.scoping_agent import ScopingAgent; print('OK')"
```

---

### Phase 1B: Scoping Agent (1-2 hours)

**Implementation**: `core/scoping_agent.py`

**Key Methods**:
```python
class ScopingAgent:
    async def needs_clarification(self, query: str) -> bool:
        """Conservative: only clarify if query is vague"""
        # Heuristics: short query, no entities, pronouns
        # LLM confidence scoring (0-1 scale)

    async def generate_brief(self, query: str) -> ResearchBrief:
        """Generate structured research brief with strict schema"""
        # Prompt constraints:
        # - Only decompose complex queries
        # - Stay focused on actual ask
        # - No side quests
        # - Simple queries → 1 sub-question (original query)
```

**Prompt Engineering** (Critical - Prevents Scope Creep):
```python
system_prompt = """Generate a research brief with 1-5 sub-questions.

CRITICAL CONSTRAINTS:
- Only decompose if query is genuinely complex (NOT "what is X?")
- Sub-questions must be DIRECTLY related to objective
- Do NOT invent side quests or expand scope
- Simple queries should have 1 sub-question (the original query)

If query is simple (< 15 words, single topic), return:
{
    "objective": "[restate query]",
    "sub_questions": [{
        "question": "[original query verbatim]",
        "rationale": "Direct answer to user query",
        "suggested_categories": ["relevant"]
    }]
}
"""
```

**Success Criteria**:
- [ ] Simple queries NOT over-decomposed (1 sub-question)
- [ ] Complex queries properly decomposed (2-5 sub-questions)
- [ ] Strict schema validation (Pydantic)
- [ ] Max subtasks enforced (config-driven)

**Testing**:
```python
# tests/test_scoping_agent.py
async def test_simple_query_no_decomposition():
    """Simple queries should NOT be over-decomposed"""
    agent = ScopingAgent(config={"max_subtasks": 5})
    brief = await agent.generate_brief("What is SAM.gov?")
    assert len(brief.sub_questions) == 1
    assert "SAM.gov" in brief.sub_questions[0].question

async def test_complex_query_decomposition():
    """Complex queries should be broken down"""
    agent = ScopingAgent(config={"max_subtasks": 5})
    brief = await agent.generate_brief(
        "Map relationships between defense contractors working on AI security"
    )
    assert 2 <= len(brief.sub_questions) <= 5
```

---

### Phase 1C: Research Supervisor (2-3 hours)

**Implementation**: `core/research_supervisor.py`

**Key Methods**:
```python
class ResearchSupervisor:
    async def execute(self, brief: ResearchBrief) -> Dict:
        """Execute research brief via task delegation"""
        # For each sub-question:
        # 1. Route to appropriate sources (category matching)
        # 2. Execute subtask in parallel
        # 3. Aggregate results

    def _route_to_sources(self, categories: List[str]) -> List[str]:
        """Map categories to source IDs using DatabaseMetadata.category"""
        # Match on category field
        # Match on tags (if present)
        # Fallback: all sources if no matches

    async def _execute_subtask(self, question: str, source_ids: List[str]) -> Dict:
        """Execute single subtask using parallel executor"""
        return await self.parallel_executor.execute_with_sources(
            research_question=question,
            source_ids=source_ids,
            limit=10
        )

    async def _synthesize_results(self, brief: ResearchBrief, results: List[Dict]) -> Dict:
        """Aggregate subtask results into final report"""
        # Use LLM to synthesize findings
```

**ParallelExecutor Extension**:
```python
# core/parallel_executor.py - ADD THIS METHOD
async def execute_with_sources(
    self,
    research_question: str,
    source_ids: List[str],  # NEW: selective execution
    limit: int = 10
) -> Dict:
    """Execute research using only specified sources"""
    enabled_integrations = [
        (id, self.registry.get_instance(id))
        for id in source_ids
        if self.registry.is_enabled(id)
    ]
    # Rest of logic same as existing execute()
```

**Success Criteria**:
- [ ] Source routing works (category matching)
- [ ] Parallel subtask execution
- [ ] Fallback to all sources if no matches
- [ ] Result synthesis produces coherent report

**Testing**:
```python
# tests/test_research_supervisor.py
async def test_source_routing():
    """Verify category-based routing"""
    supervisor = ResearchSupervisor(parallel_executor, registry)

    categories = ["government_contracts"]
    sources = supervisor._route_to_sources(categories)

    # Should include SAM.gov, exclude Twitter
    assert "sam_gov" in sources
    assert "twitter" not in sources

async def test_fallback_routing():
    """Verify fallback when no matches"""
    supervisor = ResearchSupervisor(parallel_executor, registry)

    categories = ["nonexistent_category"]
    sources = supervisor._route_to_sources(categories)

    # Should fallback to all sources
    assert len(sources) == 8  # All enabled sources
```

---

### Phase 1D: HITL Integration (1 hour)

**Implementation**: `core/hitl.py`

**CLI Approval Flow**:
```python
class HumanInTheLoop:
    def __init__(self, mode: str = "cli", enabled: bool = True):
        self.mode = mode
        self.enabled = enabled

    async def get_approval(self, brief: ResearchBrief) -> Dict:
        """Get user approval for research plan"""
        if not self.enabled:
            return {"approved": True, "feedback": None}

        if self.mode == "cli":
            return await self._cli_approval(brief)
        else:
            raise NotImplementedError("Streamlit HITL pending")

    async def _cli_approval(self, brief: ResearchBrief) -> Dict:
        """CLI-based approval flow"""
        # Display plan
        # Get user input: y/n/edit
        # Return approval status + optional feedback
```

**Success Criteria**:
- [ ] Plan display shows all key info (objective, subtasks, cost, time)
- [ ] User can approve (y), reject (n), or edit (feedback)
- [ ] Disabled when `enable_hitl: false`

**Testing**:
```python
# tests/test_hitl.py
async def test_hitl_disabled():
    """When disabled, auto-approves"""
    hitl = HumanInTheLoop(enabled=False)
    approval = await hitl.get_approval(mock_brief)
    assert approval["approved"] is True

async def test_hitl_cli_approval():
    """Manual testing required - interactive CLI"""
    # Run: python3 -c "from core.hitl import HumanInTheLoop; ..."
```

---

### Phase 1E: Wire Everything Together (1 hour)

**Modify**: `core/intelligent_executor.py`

**Integration**:
```python
class IntelligentExecutor:
    def __init__(self, ...):
        # Existing initialization
        ...

        # NEW: Add components
        self.scoping_agent = ScopingAgent(config=self.config.get('research', {}))
        self.supervisor = ResearchSupervisor(self.parallel_executor, self.registry)
        self.hitl = HumanInTheLoop(
            mode="cli",
            enabled=self.config.get('research', {}).get('enable_hitl', False)
        )

    async def execute_research(self, query: str) -> Dict:
        """Main entry point with supervisor support"""
        use_supervisor = self.config.get('research', {}).get('enable_supervisor', False)

        if not use_supervisor:
            # Fallback: existing shotgun execution
            return await self.parallel_executor.execute(query)

        try:
            # Phase 1: Scoping
            brief = await self.scoping_agent.generate_brief(query)

            # Phase 2: HITL approval
            approval = await self.hitl.get_approval(brief)
            if not approval["approved"]:
                return {
                    "error": "Research plan rejected",
                    "feedback": approval["feedback"]
                }

            # Phase 3: Supervised execution
            return await self.supervisor.execute(brief)

        except Exception as e:
            logging.error(f"Supervisor execution failed: {e}", exc_info=True)
            logging.warning("Falling back to shotgun execution")
            return await self.parallel_executor.execute(query)
```

**Success Criteria**:
- [ ] Config-driven feature flags work
- [ ] Graceful fallback on exceptions
- [ ] All entry points (CLI, Streamlit) route through unified flow

**Testing**:
```python
# tests/test_intelligent_executor.py
async def test_supervisor_disabled():
    """When disabled, uses existing shotgun path"""
    executor = IntelligentExecutor(config={"research": {"enable_supervisor": False}})
    result = await executor.execute_research("test query")
    # Should use parallel_executor directly

async def test_supervisor_enabled():
    """When enabled, uses scoping → HITL → supervisor"""
    executor = IntelligentExecutor(config={"research": {"enable_supervisor": True}})
    result = await executor.execute_research("test query")
    # Should go through full flow

async def test_supervisor_fallback():
    """On exception, falls back to shotgun"""
    executor = IntelligentExecutor(config={"research": {"enable_supervisor": True}})
    with patch.object(executor.supervisor, 'execute', side_effect=Exception("Test")):
        result = await executor.execute_research("test query")
    # Should still return results via fallback
```

---

## Configuration

```yaml
# config_default.yaml - ADD THIS SECTION

research:
  # Feature flags (start disabled, flip when ready)
  enable_scoping: false
  enable_supervisor: false
  enable_hitl: false

  # Scoping parameters
  max_subtasks: 5
  auto_clarify_threshold: 0.7  # 0-1 scale, higher = more clarification

  # Model roles (all use same model initially)
  model_roles:
    scoping: "gpt-5-mini"
    research: "gpt-5-mini"
    summarization: "gpt-5-mini"  # Change to gpt-5-nano after validation
    synthesis: "gpt-5-mini"
```

---

## Rollout Plan

### Week 1: Implementation
- Implement Phase 1A-E on `feature/supervisor-flow` branch
- All features disabled by default
- Run existing test suite: `pytest tests/ -v`
- Verify no regressions

### Week 2: Scoping Validation
- Enable `enable_scoping: true`
- Test with 20+ queries (simple + complex)
- Validate no over-decomposition
- Measure brief generation accuracy

### Week 3: Supervisor Validation
- Enable `enable_supervisor: true`
- Test source routing logic
- Verify parallel subtask execution
- Measure result quality vs. shotgun mode

### Week 4: HITL Validation
- Enable `enable_hitl: true`
- Test CLI approval flow
- Gather user feedback on UX
- Measure approval/rejection rates

### Week 5: Integration Testing
- Enable all features together
- Run end-to-end tests
- Compare cost/quality vs. baseline
- Load testing (50+ queries)

### Week 6: Production Merge
- Code review
- Documentation update
- Merge to main
- Deploy to Streamlit Cloud

---

## Success Metrics

### Baseline (Current System)
- Average cost per query: $0.50-$2.00
- Average time per query: 30-60s
- Sources called per query: 8 (all sources)
- User satisfaction: N/A (no surveys)

### Target (New System)
- Average cost per query: $0.30-$1.50 (25-40% reduction)
- Average time per query: 25-50s (10-20% reduction via routing)
- Sources called per query: 3-5 (selective routing)
- User satisfaction: ≥80% approval rate (HITL feedback)

### Quality Metrics
- Brief generation accuracy: ≥90% (manual review)
- Routing accuracy: ≥85% (correct sources selected)
- Synthesis quality: ≥4/5 (user ratings)
- Fallback rate: ≤5% (supervisor failures)

---

## Risks & Mitigations

### Risk 1: Scoping Agent Over-Decomposes Simple Queries
**Impact**: Users frustrated by unnecessary clarifications
**Likelihood**: MEDIUM
**Mitigation**:
- Conservative clarity threshold (0.7)
- Strict prompt constraints ("only decompose if complex")
- Max subtasks cap (5)
- User testing with 50+ queries

### Risk 2: Source Routing Misses Relevant Sources
**Impact**: Poor result quality
**Likelihood**: LOW
**Mitigation**:
- Fallback to all sources if no matches
- Optional tags for edge cases
- Routing accuracy testing (85% threshold)
- User feedback loop (edit plan)

### Risk 3: HITL Approval Slows Research Flow
**Impact**: Users abandon research due to friction
**Likelihood**: LOW
**Mitigation**:
- Make HITL optional (config flag)
- Fast approval path (press 'y')
- Display cost/time estimates (informed decision)
- Auto-approval for trusted users (future)

### Risk 4: Supervisor Failures Break Research
**Impact**: No results returned
**Likelihood**: LOW
**Mitigation**:
- Graceful fallback to shotgun mode
- Exception logging with full context
- Fallback rate monitoring (≤5% target)
- Circuit breaker pattern (future)

### Risk 5: Model Role Specialization Hurts Quality
**Impact**: Cheaper models produce poor summaries
**Likelihood**: MEDIUM
**Mitigation**:
- Start with single model (no specialization)
- A/B testing before rollout
- Quality metrics (F1, user ratings)
- Easy rollback (config change)

---

## Future Work (Out of Scope)

### Iterative Depth Control
**Description**: Recursive deep-dives into subtopics
**Timeline**: 3-6 months after base flow stable
**Complexity**: HIGH (exponential query growth)

### Streamlit HITL
**Description**: Non-blocking approval UI with visualization
**Timeline**: 1-2 months after CLI validation
**Complexity**: MEDIUM (async state management)

### Adaptive Source Selection
**Description**: ML-based routing (learn from feedback)
**Timeline**: 6-12 months
**Complexity**: HIGH (requires training data)

### Cost-Effectiveness Benchmarking
**Description**: Systematic cost vs. quality optimization
**Timeline**: 3-6 months
**Complexity**: MEDIUM (metrics infrastructure)

---

## Appendices

### Appendix A: Research Brief Example

```json
{
  "objective": "Map relationships between defense contractors working on AI security",
  "sub_questions": [
    {
      "question": "What partnerships exist between defense contractors and commercial AI labs?",
      "rationale": "Identify collaboration networks",
      "suggested_categories": ["government_contracts", "social_media"]
    },
    {
      "question": "What subcontracting relationships are documented in federal procurement data?",
      "rationale": "Track formal contractual relationships",
      "suggested_categories": ["government_contracts"]
    },
    {
      "question": "What DoD engagement events and programs connect contractors to AI security?",
      "rationale": "Identify networking venues and capacity-building programs",
      "suggested_categories": ["government_media"]
    },
    {
      "question": "What workforce hiring patterns indicate AI security focus?",
      "rationale": "Reveal investment priorities via job postings",
      "suggested_categories": ["jobs"]
    }
  ],
  "constraints": {
    "timeframe": "2024-2025",
    "geography": "US-based contractors"
  },
  "estimated_cost": 1.20,
  "estimated_time": 45
}
```

### Appendix B: Source Routing Matrix

| Category | Sources | Example Queries |
|----------|---------|-----------------|
| `government_contracts` | SAM.gov, USAJobs | "What contracts has X won?", "Federal procurement for Y" |
| `government_jobs` | USAJobs, ClearanceJobs | "Who is hiring for AI security?", "Job market trends" |
| `government_media` | DVIDS, FBI Vault | "What events occurred?", "DoD announcements" |
| `social_media` | Twitter, Discord, Reddit | "What are people saying about X?", "Community discussions" |

### Appendix C: LLM Cost Comparison

| Model | Cost per 1M tokens | Use Case | Quality |
|-------|-------------------|----------|---------|
| `gpt-5-mini` | $0.10 | Research, synthesis, scoping | High |
| `gpt-5-nano` | $0.03 | Bulk summarization | Medium |

**Typical Research Run**:
- 4 subtasks × 5 sources = 20 queries
- Each query: 1 generation + 3 summaries = 80 LLM calls
- If 60 are summarization (75%):
  - Before: 80 × $0.10 = $8.00
  - After: (20 × $0.10) + (60 × $0.03) = $3.80
  - **Savings: $4.20 (52.5%)**

---

## References

1. **GPT Researcher** - https://github.com/assafelovic/gpt-researcher
   - Planner/executor pattern, MCP integration, 20+ sources

2. **Open Deep Research (LangGraph)** - https://github.com/dzhng/deep-research
   - Scope/Research/Write phases, depth/breadth control, <500 LoC

3. **DeerFlow (ByteDance)** - https://github.com/bytedance/deer-flow
   - Coordinator→Planner→Research Team, HITL, MCP integration

4. **OTS Deep Research Overview** (local analysis)
   - CrewAI vs AutoGen vs LangGraph comparison
   - Model role specialization, cost-effectiveness benchmarking

5. **Codex LLM Feedback** (2025-10-28)
   - Conservative scoping, deterministic schemas, single workflow

---

## Document History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2025-10-28 | 1.0 | Claude + Codex | Initial plan based on framework analysis |

---

**Status**: ✅ APPROVED - Ready for implementation on `feature/supervisor-flow` branch
