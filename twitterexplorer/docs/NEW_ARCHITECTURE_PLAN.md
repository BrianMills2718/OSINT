# New Architecture Plan: Twitter Explorer v2.0

## Executive Summary
Complete rewrite of Twitter Explorer system from 5000+ lines of overcomplicated code to <1000 lines of clean, functional code that actually works.

## Current State Analysis

### Critical Failures in Existing System
1. **Loop doesn't iterate**: Stops after 1 round due to counting bug
2. **No findings created**: 0 findings despite 85% acceptance rate  
3. **13+ abstraction layers**: Hides simple bugs in massive complexity
4. **Rejection feedback unusable**: Can't work if system doesn't iterate

### Root Cause
**Over-engineering**: Built complex enterprise architecture before proving basic functionality worked.

## New System Design

### Core Principles
- **LLM-Native**: Every decision via frontier LLM (no heuristics)
- **Simplicity First**: <1000 lines total
- **Quality Only**: No performance optimization, quality matters most
- **Full Traceability**: User sees all decisions and reasoning

### Architecture: 4-Layer Design

```
TwitterInvestigator (200 lines)
    ├── IntelligentStrategy (200 lines) 
    ├── ResultEvaluator (150 lines)
    ├── InvestigationGraph (150 lines)
    └── Logger (100 lines)
```

### Component Specifications

#### 1. TwitterInvestigator (`main.py`)
**Purpose**: Main orchestration loop
**Responsibilities**:
- Manages investigation lifecycle
- Coordinates components
- Handles configuration

**Core Method**:
```python
def investigate(query: str, max_rounds: int = 5, endpoints_per_round: int = 3)
    → Returns: {findings, graph, trace}
```

#### 2. IntelligentStrategy (`strategy.py`)
**Purpose**: LLM-based search planning
**Responsibilities**:
- Decides which endpoints to use
- Generates search queries
- Uses feedback from previous rounds

**Core Method**:
```python
def plan_searches(query, round_num, previous_feedback, graph_context, endpoints_per_round)
    → Returns: List[APICall]
```

#### 3. ResultEvaluator (`evaluator.py`)  
**Purpose**: LLM-based result evaluation
**Responsibilities**:
- Evaluates relevance to query
- Creates findings from good results
- Generates feedback for next round

**Core Methods**:
```python
def evaluate_results(results, query, graph_context)
    → Returns: (findings, rejected)
    
def generate_feedback(accepted, rejected, query)
    → Returns: FeedbackContext
```

#### 4. InvestigationGraph (`graph.py`)
**Purpose**: Knowledge graph storage
**Responsibilities**:
- Stores 6 node types (existing ontology)
- Manages relationships
- Provides context for decisions

**Node Types** (from existing system):
- AnalyticQuestion
- InvestigationQuestion  
- SearchQuery
- DataPoint
- Insight
- EmergentQuestion

#### 5. Logger (`logger.py`)
**Purpose**: Full investigation traceability
**Responsibilities**:
- Logs all decisions with reasoning
- Logs all API calls and results
- Provides complete investigation trace

### Data Flow

```
Round N:
    Query → Strategy(LLM) → API Calls → Results → Evaluator(LLM) → Findings + Feedback
                                                                            ↓
Round N+1:
    Query + Feedback → Strategy(LLM) → Better API Calls → ...
```

### Configuration

```python
InvestigationConfig:
    max_rounds: int = 5              # When to stop
    endpoints_per_round: int = 3     # Parallel API calls
    llm_model: str = "claude-3-opus" # Or GPT-4, etc.
    min_relevance_score: float = 0.5 # Threshold for findings
```

## Implementation Plan

### Phase 1: Core Loop (Days 1-5)
- [ ] Day 1-2: TwitterInvestigator with basic loop
- [ ] Day 3-4: IntelligentStrategy with LLM integration  
- [ ] Day 5: ResultEvaluator with feedback generation

### Phase 2: Integration (Days 6-10)
- [ ] Day 6-7: InvestigationGraph implementation
- [ ] Day 8: Logger with full traceability
- [ ] Day 9-10: Testing and refinement

### Phase 3: UI/API (Days 11-12)
- [ ] Day 11: Streamlit UI integration
- [ ] Day 12: Final testing and documentation

## Success Criteria

### Functional Requirements
- ✓ Runs multiple rounds (not just 1)
- ✓ Creates findings when relevance > threshold
- ✓ Uses feedback to improve queries
- ✓ Full investigation trace available

### Quality Requirements  
- ✓ Less than 1000 lines of code
- ✓ Any bug findable in <5 minutes
- ✓ New developer understands in <30 minutes
- ✓ No unnecessary abstractions

## Migration Strategy

### Approach: Clean Slate
1. Build new system in `v2/` directory
2. Reuse only:
   - `api_client.py` (Twitter API wrapper)
   - Graph node types (ontology)
   - Logging format (JSONL)
3. Once working, replace old system entirely

### What We're NOT Migrating
- 13+ class hierarchy
- Complex coordinators
- Satisfaction metrics system
- Abstract base classes
- Batch evaluation logic

## Risk Mitigation

### Risk: LLM API Costs
**Mitigation**: Accept higher costs for quality, optimize later if needed

### Risk: Missing Features
**Mitigation**: Build MVP first, add features only after core works

### Risk: Integration Issues
**Mitigation**: Clean slate approach, no legacy dependencies

## Testing Strategy

### Core Tests Required
```python
def test_multiple_rounds_execution()
    # Must execute 3+ rounds with max_rounds=5

def test_findings_creation()  
    # Must create findings when results are relevant

def test_feedback_usage()
    # Round 2 queries must differ from Round 1

def test_full_traceability()
    # Every decision must be logged with reasoning
```

## File Structure

```
twitterexplorer/
├── v2/                        # New clean implementation
│   ├── main.py               # TwitterInvestigator
│   ├── strategy.py           # IntelligentStrategy
│   ├── evaluator.py          # ResultEvaluator
│   ├── graph.py              # InvestigationGraph
│   ├── logger.py             # Logger
│   ├── config.py             # Configuration
│   └── tests/
│       ├── test_integration.py
│       └── test_components.py
├── api_client.py             # Reuse existing
└── [old system files]        # Delete after migration
```

## Next Steps

1. **Create v2/ directory structure**
2. **Implement TwitterInvestigator.investigate() method**
3. **Test basic loop with mock LLM responses**
4. **Add real LLM integration**
5. **Build out remaining components**

## Notes

- This is a complete rewrite, not a refactor
- Simplicity is the primary goal
- Every line of code must be justified
- If it takes >5 minutes to explain, it's too complex