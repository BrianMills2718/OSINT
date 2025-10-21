# Documentation Strategy for SigInt Platform

**Date**: 2025-10-20
**Status**: Documentation audit & strategy
**Goal**: Clarify what documentation exists, what's redundant, what to consolidate

---

## Current Documentation State (What Exists Now)

### Layer 1: Vision & Philosophy (Permanent)

**File**: `CLAUDE_PERMANENT.md`
- **Purpose**: Source of truth for permanent principles
- **Contains**: Core principles, patterns, testing requirements, directory structure
- **Update frequency**: Rarely (only when architecture fundamentally changes)
- **Audience**: Any developer working on project, new team members

**File**: `INVESTIGATIVE_PLATFORM_VISION.md` (75 pages)
- **Purpose**: Long-term vision, complete requirements
- **Contains**: End-state architecture, all phases, full feature list
- **Update frequency**: Rarely (only when vision changes)
- **Audience**: Planning, stakeholders, architectural decisions

---

### Layer 2: Current Plans (Tactical)

**File**: `ROADMAP.md`
- **Purpose**: Phase-by-phase implementation plan
- **Contains**: Objectives, success criteria, deliverables per phase
- **Update frequency**: When phases complete or plans change
- **Audience**: Project planning, milestone tracking

**NEW - Integration Plans** (created today):

**File**: `INTEGRATION_PLAN.md` (990 lines)
- **Purpose**: Multi-LLM pipeline integration plan
- **Contains**: 4-phase plan for cost optimization (multi-LLM, quality metrics, caching, adaptive discovery)
- **Status**: **OBSOLETE** - You said you don't need multi-LLM, just adaptive search
- **Action**: Archive this file

**File**: `ADAPTIVE_SEARCH_INTEGRATION.md`
- **Purpose**: Mozart-style iterative search integration
- **Contains**: Complete implementation plan for adaptive search engine
- **Status**: **APPROVED** - This is what you want to build (Weeks 1-4)
- **Action**: Keep this, use as implementation guide

**File**: `AGENTIC_VS_ITERATIVE_ANALYSIS.md`
- **Purpose**: Comparison of BabyAGI vs Mozart approaches
- **Contains**: Decision analysis, when to use each, hybrid approach
- **Status**: **APPROVED** - Hybrid approach (Mozart daily, BabyAGI on-demand)
- **Action**: Keep as reference for future BabyAGI implementation

**File**: `KNOWLEDGE_BASE_OPTIONS.md`
- **Purpose**: Analysis of knowledge graph options
- **Contains**: PostgreSQL vs Wikibase vs Neo4j comparison
- **Status**: **APPROVED** - Option B (PostgreSQL with Wikibase-compatible schema)
- **Action**: Keep as implementation guide for Weeks 5-8

---

### Layer 3: Reality Check (Status)

**File**: `STATUS.md`
- **Purpose**: What's actually working vs planned
- **Contains**: Component status ([PASS]/[FAIL]/[BLOCKED]), evidence, limitations
- **Update frequency**: After every integration/feature completion
- **Audience**: Truth check - what can we use right now?

**File**: `MONITORING_SYSTEM_READY.md`
- **Purpose**: Phase 1 completion evidence
- **Contains**: Testing results, monitor configurations, deployment instructions
- **Update frequency**: One-time (Phase 1 completion)
- **Status**: Complete, reference document
- **Action**: Keep as historical record

---

### Layer 4: Current Work (Operational)

**File**: `CLAUDE.md` (TEMPORARY section)
- **Purpose**: This week's focus, next 3 actions
- **Contains**: Current task scope, next actions, immediate blockers
- **Update frequency**: Multiple times per session as tasks complete
- **Audience**: Active development guidance

**File**: `PATTERNS.md`
- **Purpose**: Code templates for current phase
- **Contains**: Reusable patterns (database integration, LLM calls, etc.)
- **Update frequency**: When new patterns emerge
- **Audience**: Copy-paste reference during coding

---

### Layer 5: Reference & Research

**SI_UFO_Wiki/** directory (Friend's wiki system analysis):
- `README.md` - Complete overview
- `MOZART_BOT_COMPLETE_ANALYSIS.md` - Code review
- `SETUP_MOZART_LOCALLY.md` - Setup guide
- `DOCKER_CONTAINERS.md` - Container specs
- `QUICK_REFERENCE.md` - Command cheat sheet
- etc. (10+ files)

**Status**: **Reference only** - Not part of your implementation
**Action**: Keep in `SI_UFO_Wiki/` directory for reference

---

## Documentation Problems (Current State)

### Problem 1: Redundant Integration Plans

**Issue**: Multiple integration plan documents created today, some obsolete

**Files**:
- ❌ `INTEGRATION_PLAN.md` - Multi-LLM optimization (you don't want this)
- ✅ `ADAPTIVE_SEARCH_INTEGRATION.md` - Adaptive search (you want this)
- ✅ `AGENTIC_VS_ITERATIVE_ANALYSIS.md` - Decision analysis (approved)
- ✅ `KNOWLEDGE_BASE_OPTIONS.md` - Knowledge graph options (approved)

**Solution**: Archive obsolete `INTEGRATION_PLAN.md`

---

### Problem 2: Vision vs Reality Drift

**Issue**: `INVESTIGATIVE_PLATFORM_VISION.md` is 75 pages of long-term vision, but current work is focused subset

**Example**:
- Vision: 15+ data sources, social media, full collaboration
- Reality: 5 government sources, boolean monitoring working, now adding adaptive search

**Solution**: This is OK - vision is aspirational, reality tracked in `STATUS.md`

---

### Problem 3: CLAUDE.md TEMPORARY Section May Be Stale

**Issue**: CLAUDE.md TEMPORARY section talks about Phase 1 (Boolean Monitoring) being complete, but doesn't reflect new approved work (adaptive search + knowledge graph)

**Current**: "Next phase: DECISION POINT - deploy scheduler or Phase 2 UI"
**Reality**: You've decided to build adaptive search + knowledge graph (Weeks 1-10)

**Solution**: Update CLAUDE.md TEMPORARY section to reflect new plan

---

## Proposed Documentation Strategy (Going Forward)

### Keep 4 Core Documents (Single Source of Truth for Each Layer)

#### 1. **CLAUDE.md** (Operational - Current Work)
**Purpose**: What am I working on RIGHT NOW?

**PERMANENT section**:
- Core principles (never skip testing, evidence hierarchy, etc.)
- Directory structure
- Essential patterns
- Update: Rarely

**TEMPORARY section** (UPDATE NOW):
- Current phase: "Adaptive Search + Knowledge Graph (Weeks 1-10)"
- Next 3 actions with prerequisites
- Immediate blockers
- Checkpoint questions
- Update: Every session as tasks complete

---

#### 2. **ROADMAP.md** (Tactical - Implementation Plan)
**Purpose**: What's the plan for next 3-6 months?

**Contents**:
- Phase breakdown (0, 1, 2, 3...)
- Current phase objectives
- Upcoming phase preview
- Timeline estimates
- Update: When phases complete

**Action**: Update ROADMAP.md to add new Phase 1.5:
```markdown
## Phase 1.5: Adaptive Search & Knowledge Graph (NEW)
**Timeline**: Weeks 1-10
**Objectives**:
- Week 1-4: Mozart-style adaptive search
- Week 5-8: PostgreSQL knowledge graph (Wikibase-compatible)
- Week 9-10: Evaluation & visualization

**Deliverables**:
- Adaptive search engine with iterative refinement
- BabyAGI on-demand deep investigations
- PostgreSQL knowledge graph
- Graph query interface
```

---

#### 3. **STATUS.md** (Reality - What Works)
**Purpose**: What actually works RIGHT NOW?

**Contents**:
- Component status with evidence
- [PASS] / [FAIL] / [BLOCKED]
- Known limitations
- Unverified claims
- Update: After completing features

**Action**: Update STATUS.md as you build adaptive search:
```markdown
## Adaptive Search (Phase 1.5)
- [IN PROGRESS] Adaptive search engine - Week 1-4
- [PENDING] BabyAGI investigations - Week 5-8
- [PENDING] Knowledge graph - Week 5-8
```

---

#### 4. **INVESTIGATIVE_PLATFORM_VISION.md** (Vision - Long-term)
**Purpose**: What's the eventual end state?

**Contents**:
- Complete architectural vision
- All planned features
- Full requirements
- Update: Rarely (only when vision changes)

**Action**: No changes needed - this is aspirational

---

### Implementation-Specific Documents (Reference, Not Single Source of Truth)

#### 5. **ADAPTIVE_SEARCH_INTEGRATION.md**
**Purpose**: Implementation guide for adaptive search (Weeks 1-4)
**Status**: Reference guide while building
**Location**: Keep in root (will archive to `docs/` when complete)

#### 6. **AGENTIC_VS_ITERATIVE_ANALYSIS.md**
**Purpose**: Decision analysis for BabyAGI vs Mozart
**Status**: Reference for future BabyAGI implementation
**Location**: Keep in root (move to `docs/` later)

#### 7. **KNOWLEDGE_BASE_OPTIONS.md**
**Purpose**: Implementation guide for knowledge graph (Weeks 5-8)
**Status**: Reference guide while building
**Location**: Keep in root (will archive to `docs/` when complete)

---

### Archive Strategy

**When implementation guides become obsolete** (feature completed):
```bash
# After Week 4 (adaptive search complete)
mkdir -p docs/archived/2025-10-20-adaptive-search/
mv ADAPTIVE_SEARCH_INTEGRATION.md docs/archived/2025-10-20-adaptive-search/
mv AGENTIC_VS_ITERATIVE_ANALYSIS.md docs/archived/2025-10-20-adaptive-search/

# Create archive README
cat > docs/archived/2025-10-20-adaptive-search/README.md << EOF
# Adaptive Search Integration (Completed)

**Completed**: 2025-11-XX
**Implementation**: See core/adaptive_search_engine.py

This directory contains planning documents for adaptive search integration.
Feature is now complete and in production.
EOF
```

---

## Information Flow (How to Use Documentation)

### Starting a New Task
**Read these in order**:
1. `CLAUDE.md` (TEMPORARY) → What's the current task?
2. `STATUS.md` → What's already built?
3. Implementation guide (e.g., `ADAPTIVE_SEARCH_INTEGRATION.md`) → How to build it?
4. `PATTERNS.md` → What patterns to follow?

### Completing a Task
**Update these**:
1. `STATUS.md` → Mark component [PASS] or [FAIL] with evidence
2. `CLAUDE.md` (TEMPORARY) → Update next actions, mark todo complete
3. Implementation guide → Mark sections complete

### Finishing a Phase
**Update these**:
1. `ROADMAP.md` → Mark phase complete, update timeline
2. `STATUS.md` → Comprehensive status update
3. `CLAUDE.md` (TEMPORARY) → Rewrite for next phase
4. Archive implementation guides → Move to `docs/archived/`

---

## File Organization (Clean Up)

### Current Root Directory (Messy)
```
sam_gov/
├── CLAUDE.md
├── ROADMAP.md
├── STATUS.md
├── INVESTIGATIVE_PLATFORM_VISION.md
├── INTEGRATION_PLAN.md              # OBSOLETE - archive
├── ADAPTIVE_SEARCH_INTEGRATION.md   # Active reference
├── AGENTIC_VS_ITERATIVE_ANALYSIS.md # Active reference
├── KNOWLEDGE_BASE_OPTIONS.md        # Active reference
├── MONITORING_SYSTEM_READY.md       # Historical
├── PATTERNS.md
├── ... (many more docs)
```

### Proposed Organization (Clean)
```
sam_gov/
├── CLAUDE.md                        # Operational (current work)
├── ROADMAP.md                       # Tactical (plan)
├── STATUS.md                        # Reality (what works)
├── INVESTIGATIVE_PLATFORM_VISION.md # Vision (long-term)
├── PATTERNS.md                      # Reference (code templates)
│
├── docs/                            # Reference documentation
│   ├── active/                      # Currently implementing
│   │   ├── ADAPTIVE_SEARCH_INTEGRATION.md
│   │   ├── AGENTIC_VS_ITERATIVE_ANALYSIS.md
│   │   └── KNOWLEDGE_BASE_OPTIONS.md
│   │
│   ├── archived/                    # Completed implementations
│   │   ├── 2025-10-19-phase1-boolean-monitoring/
│   │   │   ├── README.md
│   │   │   └── MONITORING_SYSTEM_READY.md
│   │   └── 2025-11-XX-adaptive-search/
│   │       └── ... (when complete)
│   │
│   └── reference/                   # External research
│       └── SI_UFO_Wiki/             # Friend's wiki analysis
│           ├── README.md
│           ├── MOZART_BOT_COMPLETE_ANALYSIS.md
│           └── ...
│
├── core/                            # Implementation
├── integrations/
├── monitoring/
└── ...
```

---

## Immediate Actions (Clean Up Now)

### Action 1: Archive Obsolete Multi-LLM Plan
```bash
mkdir -p docs/archived/2025-10-20-unused-plans/
mv INTEGRATION_PLAN.md docs/archived/2025-10-20-unused-plans/

cat > docs/archived/2025-10-20-unused-plans/README.md << EOF
# Unused Integration Plans

**Date**: 2025-10-20
**Status**: Not implemented

## INTEGRATION_PLAN.md
Multi-LLM optimization plan. Decision: Not needed (using gpt-5-mini for everything).
Replaced by: ADAPTIVE_SEARCH_INTEGRATION.md (focus on iterative search, not multi-LLM).
EOF
```

### Action 2: Organize Active Implementation Guides
```bash
mkdir -p docs/active/
mv ADAPTIVE_SEARCH_INTEGRATION.md docs/active/
mv AGENTIC_VS_ITERATIVE_ANALYSIS.md docs/active/
mv KNOWLEDGE_BASE_OPTIONS.md docs/active/
```

### Action 3: Archive Phase 1 Completion Docs
```bash
mkdir -p docs/archived/2025-10-19-phase1-boolean-monitoring/
mv MONITORING_SYSTEM_READY.md docs/archived/2025-10-19-phase1-boolean-monitoring/

cat > docs/archived/2025-10-19-phase1-boolean-monitoring/README.md << EOF
# Phase 1: Boolean Monitoring (Completed)

**Completed**: 2025-10-19
**Implementation**: See monitoring/boolean_monitor.py

Phase 1 delivered:
- BooleanMonitor class
- YAML-based config
- Email alerts
- LLM relevance filtering
- 5 production monitors

Evidence of completion in MONITORING_SYSTEM_READY.md.
EOF
```

### Action 4: Move Friend's Wiki Research
```bash
mkdir -p docs/reference/
mv SI_UFO_Wiki/ docs/reference/
```

### Action 5: Update CLAUDE.md TEMPORARY Section
(Will do this next)

---

## Documentation Maintenance Rules

### Rule 1: Single Source of Truth
**Each fact lives in ONE place**:
- Current task → `CLAUDE.md` (TEMPORARY)
- What works → `STATUS.md`
- Implementation plan → `ROADMAP.md`
- Long-term vision → `INVESTIGATIVE_PLATFORM_VISION.md`

**Never duplicate** - link instead:
```markdown
# CLAUDE.md
Current phase: Adaptive Search (see ROADMAP.md Phase 1.5)
Implementation guide: See docs/active/ADAPTIVE_SEARCH_INTEGRATION.md
```

---

### Rule 2: Update Frequency
- **CLAUDE.md**: Every session (as tasks complete)
- **STATUS.md**: After completing features (with evidence)
- **ROADMAP.md**: When phases complete or plans change
- **INVESTIGATIVE_PLATFORM_VISION.md**: Rarely (vision changes)

---

### Rule 3: Archive When Done
**When feature completes**:
1. Move implementation guide to `docs/archived/YYYY-MM-DD-feature/`
2. Create `README.md` in archive explaining what was built
3. Update `STATUS.md` to [PASS] with evidence
4. Update `ROADMAP.md` to mark phase complete

---

### Rule 4: Active Implementation Guides Stay Visible
**While building** (Weeks 1-10):
- Keep guides in `docs/active/`
- Easy to reference during coding
- Don't archive until complete

**After building**:
- Move to `docs/archived/`
- Keep implementation (code) in main codebase
- Archive is for historical reference

---

## Summary: 4-Layer Documentation System

```
┌─────────────────────────────────────────────────┐
│ Layer 1: VISION (Rarely changes)               │
│ - INVESTIGATIVE_PLATFORM_VISION.md             │
│ - CLAUDE_PERMANENT.md                          │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ Layer 2: PLAN (Changes per phase)              │
│ - ROADMAP.md                                   │
│ - docs/active/* (implementation guides)        │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ Layer 3: REALITY (Changes per feature)         │
│ - STATUS.md                                    │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│ Layer 4: CURRENT WORK (Changes per session)    │
│ - CLAUDE.md (TEMPORARY section)                │
│ - PATTERNS.md                                  │
└─────────────────────────────────────────────────┘
```

**Information flow**:
- Vision → Plan → Reality → Current Work
- Update flows upward as features complete
- Read flows downward as you start tasks

---

## Next Steps

1. ✅ **Now**: Reorganize files (archive obsolete, move active guides)
2. ✅ **Now**: Update CLAUDE.md TEMPORARY section with new plan
3. ✅ **Now**: Update ROADMAP.md with Phase 1.5
4. **Week 1-4**: Use `docs/active/ADAPTIVE_SEARCH_INTEGRATION.md` as guide
5. **Week 5-8**: Use `docs/active/KNOWLEDGE_BASE_OPTIONS.md` as guide
6. **After Week 10**: Archive completed guides

---

**Last Updated**: 2025-10-20
**Status**: Documentation strategy defined
**Action**: Reorganize files, update CLAUDE.md and ROADMAP.md
