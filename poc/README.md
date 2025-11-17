# Wiki PoC - Ultra-Minimal Phased Approach

**Last Updated**: 2025-11-16
**Status**: Stage 1 Ready

---

## Overview

This directory contains the **phased proof-of-concept** for the investigative journalism wiki system.

**CRITICAL**: Do NOT build full system. Validate each stage before proceeding.

---

## Phasing Strategy

### Stage 1: Manual Proof (2 hours, ZERO code) ← **START HERE**

**Goal**: Validate core assumption with no automation

**File**: `stage1_manual_test.md`

**What You Do**:
1. Run deep_research.py on "J-2 psychological warfare since 2001"
2. Manually extract 10-15 entities to spreadsheet
3. Try pivoting (find all snippets mentioning each entity)
4. Answer: Does entity organization help vs. flat reading?

**Decision**:
- ✅ GO to Stage 2: Entity pivoting useful, automate it
- ❌ STOP: Entity organization doesn't help, no need to build

**Time**: 2 hours
**Code**: 0 lines

---

### Stage 2: SQLite + CLI (4-6 hours, ~100 lines)

**Prerequisite**: Stage 1 GO decision

**Goal**: Automate storage + browsing (manual data entry for now)

**Schema**: 3 tables only
- `evidence` (snippet_text, source_url)
- `entities` (name, entity_type)
- `evidence_entities` (junction table)

**Scripts**:
- `load_evidence.py` - Load CSV of snippets
- `load_entities.py` - Load CSV of entities
- `stage2.py` - CLI with 2 commands:
  - `list-entities` - Show all entities with mention counts
  - `evidence-for-entity "name"` - Show snippets for entity

**Decision**:
- ✅ GO to Stage 3: CLI useful, automate data entry
- ⏸️ MAINTAIN: CLI useful but manual entry acceptable
- ❌ STOP: CLI doesn't help vs. spreadsheet

**Time**: 4-6 hours
**Code**: ~100 lines

---

### Stage 3: LLM Extraction (4-6 hours, +50 lines)

**Prerequisite**: Stage 2 GO decision

**Goal**: Automate entity extraction (eliminate manual CSV creation)

**Add**:
- `entity_extractor.py` - LLM call with extraction prompt

**Modify**:
- Stage 2 scripts now call LLM instead of loading CSV

**Decision**:
- ✅ GO to Full PoC: Extraction works well
- 🔧 TUNE: Extraction quality needs prompt tuning
- ⏸️ STOP at Stage 3: Good enough for current needs

**Time**: 4-6 hours
**Code**: +50 lines

---

### Full PoC (4-6 hours)

**Prerequisite**: Stage 3 GO decision

**Goal**: Full automation (consultant's spec)

**Add Tables**:
- `leads`, `research_runs`, `sources`

**Add Scripts**:
- `deep_research_adapter.py`
- `poc.py run` command

**Decision**:
- ✅ GO to V1: Full automation validated
- ❌ Issues: Debug integration

**Time**: 4-6 hours

---

### V1 (20-25 hours)

**Prerequisite**: Full PoC GO decision

**Add Tables**:
- `predicates`, `claims`, `entity_aliases`

**Add Features**:
- Multi-lead management
- Claim extraction
- Web UI (Streamlit)

---

## Current Status

**Active Stage**: Stage 1 (Manual Proof)

**Next Step**: Complete `stage1_manual_test.md` template

**Timeline**:
- Stage 1: This week (2 hours)
- Decision: End of week
- Stage 2: Next week (if GO)

---

## Files

### Stage 1
- `stage1_manual_test.md` - Manual validation template ✅ CREATED

### Stage 2 (future)
- `schema_stage2.sql` - 3-table schema
- `load_evidence.py` - CSV loader
- `load_entities.py` - CSV loader
- `stage2.py` - CLI commands

### Stage 3 (future)
- `entity_extractor.py` - LLM extraction

### Full PoC (future)
- `schema_full.sql` - 6-table schema
- `deep_research_adapter.py` - Integration
- `poc.py` - Full CLI

---

## Decision Log

| Stage | Date | Decision | Rationale |
|-------|------|----------|-----------|
| Stage 1 | TBD | PENDING | Not yet executed |

---

## Notes

- Each stage has clear go/no-go criteria
- Can stop at any stage without sunk cost
- Total maximum: 20 hours to full PoC decision
- Can stop at 2, 8, or 14 hours if value unclear
