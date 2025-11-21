# Codebase Architecture Audit (2025-11-20)

## Core Architecture Pattern: Multi-Agent Research System

### System Overview
**Name**: SimpleDeepResearch (misnomer - not simple anymore!)  
**Size**: 4,392 lines (deep_research.py)  
**Pattern**: Manager-Agent with Hypothesis Branching (evolved BabyAGI-like)  
**Philosophy**: No hardcoded heuristics, full LLM intelligence, quality-first

---

## Agent Hierarchy

```
User Query
    ↓
[Task Decomposition LLM] → 3-5 research tasks
    ↓
[Manager LLM] → Prioritizes tasks (P1-P10)
    ↓
For each task:
    ├─ [Hypothesis Generation LLM] → 3-5 investigative hypotheses
    ├─ For each hypothesis:
    │   ├─ [Query Generation LLM] → Source-specific queries
    │   ├─ [Source Execution] → DVIDS, Brave, SAM.gov, etc.
    │   ├─ ❌ NO FILTERING (BUG IDENTIFIED)
    │   └─ [Coverage Assessment LLM] → Should we continue?
    └─ [Relevance Filter LLM] → Main task results only
        ↓
[Report Synthesis LLM] → Final markdown report
```

---

## Entry Points

### Primary
- `apps/ai_research.py` - Main CLI for deep research
- `apps/unified_search_app.py` - Streamlit web UI

### Testing
- `tests/test_deep_research_full.py` - E2E validation
- `tests/test_phase3c_validation.py` - Hypothesis validation
- `tests/test_phase4a_prioritization.py` - Manager validation

---

## Key Components

### research/deep_research.py (4,392 lines)
**Main class**: `SimpleDeepResearch`

**Key methods**:
- `research()` - Main entry point
- `_decompose_question()` - Task decomposition (Phase 1)
- `_prioritize_tasks()` - Manager prioritization (Phase 4A)
- `_generate_hypotheses()` - Hypothesis generation (Phase 3A)
- `_execute_hypotheses_sequential()` - Hypothesis execution (Phase 3B/C)
- `_execute_hypothesis()` - Single hypothesis with query gen
- `_assess_coverage()` - Coverage assessment (Phase 3C/5)
- `_is_saturated()` - Saturation detection (Phase 4B)
- `_synthesize_report()` - Final report

**Phases implemented**:
- Phase 1: Mentor-style reasoning
- Phase 2: Source re-selection on retry
- Phase 3A: Hypothesis generation
- Phase 3B: Parallel hypothesis execution
- Phase 3C: Sequential execution with coverage
- Phase 4A: Task prioritization (Manager LLM)
- Phase 4B: Saturation detection  
- Phase 5: Pure qualitative intelligence (no numeric scores)

### research/execution_logger.py
**Purpose**: Structured logging to execution_log.jsonl

**Key methods**:
- `log_run_start/complete()` - Run lifecycle
- `log_task_start/complete()` - Task lifecycle
- `log_source_selection()` - Which sources chosen
- `log_api_call()` - API request tracking
- `log_relevance_scoring()` - Filtering decisions
- `log_coverage_assessment()` - Phase 3C/5 decisions
- `log_saturation_assessment()` - Phase 4B decisions
- **MISSING**: `log_hypothesis_query_generation()` ← BUG

### prompts/ (Jinja2 templates)
**deep_research/**:
- `task_decomposition.j2` - Break question into tasks
- `hypothesis_generation.j2` - Generate investigative hypotheses
- `hypothesis_query_generation.j2` - Per-source query generation
- `coverage_assessment.j2` - Phase 3C/5 coverage evaluation
- `task_prioritization.j2` - Phase 4A manager decisions
- `saturation_detection.j2` - Phase 4B stopping criteria
- `relevance_evaluation.j2` - Result filtering
- `report_synthesis.j2` - Final report generation

---

## Data Flow

### Input
User question → config.yaml settings

### Task Execution
```
Task Queue (prioritized by Manager LLM)
    ↓
Task 0 (P1) executes:
    ├─ Generate 3-5 hypotheses
    ├─ Execute hypotheses sequentially
    │   └─ Each hypothesis:
    │       ├─ Generate source-specific queries
    │       ├─ Execute searches
    │       ├─ Accumulate results (NO FILTERING ❌)
    │       └─ Assess coverage
    └─ Filter main task results (YES FILTERING ✓)
        ↓
Task 1 (P2) executes...
```

### Output
```
data/research_output/YYYY-MM-DD_HH-MM-SS_query/
├─ execution_log.jsonl (structured events)
├─ metadata.json (run metadata)
├─ report.md (final markdown)
├─ results.json (all results)
└─ raw/ (API responses)
```

---

## Critical Bugs Identified

### Bug 1: Hypothesis Results Skip Filtering
**Location**: `research/deep_research.py:1356-1450` (`_execute_hypothesis`)  
**Problem**: Results go directly from source → deduplication → accumulation  
**Impact**: Junk results (GTMO military ops) pollute final report  
**Status**: UNRESOLVED

### Bug 2: Query Generation Reasoning Not Logged
**Location**: `research/deep_research.py:1349`  
**Problem**: Uses `logging.info()` instead of `self.logger`  
**Impact**: Cannot debug why LLM chose "Cuba sanctions Congress"  
**Status**: UNRESOLVED

### Bug 3: Relevance Reasoning Not in Structured Logs
**Location**: `research/execution_logger.py` (missing field)  
**Problem**: reasoning_breakdown requested but not logged to execution_log.jsonl  
**Impact**: Audit trail incomplete  
**Status**: UNRESOLVED

---

## Configuration Modes

### Mode 1: Expert Investigator (Run Until Saturated)
```yaml
manager_agent:
  allow_saturation_stop: true
deep_research:
  max_tasks: 100  # Safety net
```

### Mode 2: Budget-Constrained (Run to Limits)
```yaml
manager_agent:
  allow_saturation_stop: false
deep_research:
  max_tasks: 15  # Hard limit
```

---

## Integration Architecture

### MCP Tools (7 sources)
- `search_sam` - SAM.gov contracts
- `search_dvids` - DoD multimedia
- `search_usajobs` - Federal jobs
- `search_clearancejobs` - Defense contractor jobs
- `search_twitter` - Social media
- `search_reddit` - Community discussions
- `search_discord` - OSINT communities

### Non-MCP (1 source)
- `brave_search` - General web search

### Integration Flow
```
ParallelExecutor (core/parallel_executor.py)
    ↓
MCP Tool Wrapper (deep_research.py:_call_mcp_tool)
    ↓
MCP Server (external process)
    ↓
API (DVIDS, SAM.gov, etc.)
```

---

## Testing Infrastructure

**160+ test files** covering:
- Unit tests (individual components)
- Integration tests (multi-component)
- E2E tests (user-facing entry points)
- Phase validation tests (3A, 3B, 3C, 4A, 4B)
- Live API tests (require keys)

---

## Documentation Structure

### Core Docs (root)
- **CLAUDE.md** - AI agent instructions (NEEDS UPDATE)
- **STATUS.md** - Component status (accurate)
- **PATTERNS.md** - Code patterns

### Active Docs
- `docs/how_it_works.md` - System architecture
- `docs/PHASE4_TASK_PRIORITIZATION_PLAN.md`

### Archived
- `docs/archive/2025-11-20/` - Recent Phase 5 docs
- `docs/reference/BABYAGI_ANALYSIS.md` - Framework evaluation

---

## What CLAUDE.md Got Wrong

1. **Complexity**: Described as "simple" but actually 4,392 lines with 5 phases
2. **BabyAGI Pattern**: Didn't mention we evolved into manager-agent architecture
3. **Filtering**: Didn't document that hypothesis execution bypasses relevance filtering
4. **Logging**: Didn't mention execution_logger.py structured logging system
5. **Agent hierarchy**: No diagram showing multi-agent decision flow

---

## Recommendations

### Immediate (Logging Fix)
1. Add `log_hypothesis_query_generation()` to execution_logger.py
2. Update deep_research.py:1349 to use structured logging
3. Surface reasoning to stdout for real-time visibility

### Short-term (Filtering Fix)
1. Add relevance filtering to hypothesis execution
2. Decide: per-source vs per-hypothesis batch
3. Add central quality control agent (optional)

### Documentation (CLAUDE.md Update)
1. Add "Architecture" section with agent hierarchy diagram
2. Document multi-phase system (not "simple")
3. Add known bugs section (hypothesis filtering bypass)
4. Update complexity estimates (4,392 lines, not 150)

