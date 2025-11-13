# Documentation Organization Guide

**Last Updated**: 2025-11-12
**Purpose**: Navigate the `docs/` directory efficiently

---

## Quick Navigation

### 🎯 Current Work (Start Here)

**Active Planning**:
- `LLM_INTELLIGENCE_IMPLEMENTATION_PLAN.md` (56K) - **NEW** - 3-phase LLM intelligence plan (mentor reasoning, source re-selection, hypothesis branching)
- `FUTURE_CONSIDERATIONS.md` (401B) - Forward-looking enhancements

**Active Subdirectory** (`active/`):
- Contains ongoing planning docs from October 2025 work
- See: Adaptive search, agentic analysis, knowledge base options

---

## 📚 Official Standards & Methodologies

**Core Standards**:
- `FSTRING_JSON_METHODOLOGY.md` (11K) - **OFFICIAL STANDARD** - How to handle JSON in LLM prompts (Jinja2 vs f-strings)
- `JINJA2_MIGRATION_INVESTIGATION.md` (24K) - Investigation for migrating all prompts to Jinja2 templates

**Architecture Designs**:
- `SEARCH_CONFIGURATION_ARCHITECTURE.md` (18K) - Unified search configuration design (not yet implemented)

---

## 🔍 Reference Materials (Frequently Consulted)

**Query Guides & Testing**:
- `INTEGRATION_QUERY_GUIDES.md` (17K) - Empirical query syntax for each source (Reddit, Twitter, etc.)
- `SOURCE_VALIDATION_QUERIES.md` (9.8K) - Validation queries for all 8 data sources
- `INVESTIGATIVE_KEYWORDS_CURATED.md` (7.7K) - High-value investigative journalism keywords

**Research & Analysis**:
- `BABYAGI_ANALYSIS.md` (12K) - Investigation of BabyAGI agentic patterns
- `agentic_llm_deep_research.txt` (29K) - Academic research on agentic LLM architectures

---

## 📋 Implementation Plans

### ✅ Completed Plans (Historical Record)

**Implemented Features**:
- `BRAVE_SEARCH_INTEGRATION_PLAN.md` (17K) - **IMPLEMENTED** - Brave Search integration (see `integrations/social/brave_search_integration.py`)
- `COST_TRACKING_AND_GPT5_NANO.md` (6.3K) - **IMPLEMENTED** - Cost tracking + gpt-5-nano support
- `SOURCE_ATTRIBUTION_TEST_RESULTS.md` (2.4K) - Test results from 2025-10-25 fix (deep investigation source attribution)

### ⏳ Approved Plans (Pending Implementation)

**Data.gov Integration** (3 docs, 68K total):
- `DATAGOV_INTEGRATION_ROADMAP.md` (14K) - Status: "READY TO EXECUTE" (not yet implemented)
- `DATAGOV_MCP_INTEGRATION_ANALYSIS.md` (18K) - Technical analysis for Data.gov via MCP
- `DATAGOV_MCP_PREFLIGHT_ANALYSIS.md` (36K) - Risk assessment and GO/NO-GO analysis

**Infrastructure Plans**:
- `MCP_INTEGRATION_PLAN.md` (20K) - Status: APPROVED - Model Context Protocol adoption plan
- `DEEP_RESEARCH_IMPROVEMENTS.md` (26K) - Status: APPROVED - Scope→Plan→Execute→Synthesize workflow

### 🔮 Vision Documents (Future Concepts)

**Deferred Features**:
- `ULTRA_DEEP_RESEARCH_VISION.md` (16K) - Future concept (explicitly deferred) - Next-gen investigative research capabilities

---

## 📁 Directory Structure

```
docs/
├── README.md                        # This navigation guide
├── active/                          # Current work (7 files)
│   ├── LLM_INTELLIGENCE_IMPLEMENTATION_PLAN.md
│   ├── FUTURE_CONSIDERATIONS.md
│   └── [5 other active planning docs]
├── standards/                       # Official methodologies (3 files)
│   ├── FSTRING_JSON_METHODOLOGY.md
│   ├── JINJA2_MIGRATION_INVESTIGATION.md
│   └── SEARCH_CONFIGURATION_ARCHITECTURE.md
├── reference/                       # Frequently consulted (5 files)
│   ├── INTEGRATION_QUERY_GUIDES.md
│   ├── SOURCE_VALIDATION_QUERIES.md
│   ├── INVESTIGATIVE_KEYWORDS_CURATED.md
│   ├── BABYAGI_ANALYSIS.md
│   └── agentic_llm_deep_research.txt
├── plans/                           # Implementation plans
│   ├── implemented/                 # Completed (3 files)
│   ├── pending/                     # Approved, awaiting (5 files)
│   └── vision/                      # Future concepts (1 file)
├── archive/                         # Historical docs (33 files)
└── examples/                        # Example outputs
```

**File Count**: 53 total documentation files organized into 6 categories

---

## 📊 File Status Legend

| Status | Meaning | Action |
|--------|---------|--------|
| **OFFICIAL STANDARD** | Mandatory methodology | Follow always |
| **IMPLEMENTED** | Feature completed | Reference for maintenance |
| **READY TO EXECUTE** | Approved, not started | Implement when prioritized |
| **APPROVED** | Design approved | Awaiting implementation |
| **Vision/Deferred** | Future concept only | No immediate action |

---

## ✅ Reorganization Complete (2025-11-12)

The documentation has been reorganized into the structure shown above.

**What Changed**:
- ✅ Created `standards/` for official methodologies (3 files)
- ✅ Created `reference/` for frequently consulted docs (5 files)
- ✅ Created `plans/{implemented,pending,vision}/` for implementation tracking (9 files)
- ✅ Moved current work to `active/` (7 files)
- ✅ Merged `archived/` into `archive/` (consolidated old docs)
- ✅ No files deleted (all 19 root files preserved and organized)

**Benefits Achieved**:
- Clear separation of current vs historical work
- Easy to find standards vs references vs plans
- Scalable as new docs are added
- Visible status tracking (implemented vs pending vs vision)

---

## 🔎 Finding What You Need

**"What's the current plan?"**
→ `active/LLM_INTELLIGENCE_IMPLEMENTATION_PLAN.md` (3 phases: reasoning, source re-selection, hypothesis branching)

**"How do I write LLM prompts with JSON?"**
→ `standards/FSTRING_JSON_METHODOLOGY.md` (official standard)

**"What query syntax works for Reddit?"**
→ `reference/INTEGRATION_QUERY_GUIDES.md` (empirical testing results)

**"What sources are validated?"**
→ `reference/SOURCE_VALIDATION_QUERIES.md` (8 sources, 8 test queries)

**"What features are planned?"**
→ `plans/pending/` (5 approved plans awaiting implementation)

**"What's been implemented?"**
→ `plans/implemented/` (3 completed plans) + check `integrations/` directory

---

## 📝 Maintenance Notes

**When to Update This README**:
- New planning doc created → Add to "Current Work"
- Plan implemented → Move from "Pending" to "Completed"
- New official standard → Add to "Standards"
- Directory reorganization → Update structure diagrams

**Current State** (as of 2025-11-12):
- 53 total documentation files organized into 6 categories
- All files preserved (no deletions)
- Directory-based organization complete
- `archived/` merged into `archive/` (consolidated historical docs)

---

## 🚀 Quick Start for New Contributors

1. **Read current plan**: `active/LLM_INTELLIGENCE_IMPLEMENTATION_PLAN.md`
2. **Understand standards**: `standards/FSTRING_JSON_METHODOLOGY.md`
3. **Check integration guides**: `reference/INTEGRATION_QUERY_GUIDES.md`
4. **Review reference keywords**: `reference/INVESTIGATIVE_KEYWORDS_CURATED.md`
5. **Consult existing plans**: `plans/pending/` directory

---

**End of README**
