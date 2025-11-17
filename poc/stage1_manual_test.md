# Stage 1: Manual Entity Extraction Test

**Date**: 2025-11-16
**Status**: NOT STARTED
**Goal**: Validate "entity-pivotable memory" concept with ZERO automation

---

## Overview

This is a **2-hour manual exercise** to validate the core assumption before writing any code:

> "Does organizing research by entities (people, orgs, programs, concepts) help investigative work vs. just reading flat reports?"

**If NO → STOP** - No need to build automation.
**If YES → Proceed to Stage 2** - Build minimal CLI.

---

## Research Question

**Topic**: J-2 psychological warfare since 2001

**Why this topic**: Complex, messy, spans multiple entities (offices, programs, people, concepts) - good test for entity-based organization.

---

## Step 1: Run deep_research.py (30-45 minutes)

### Command
```bash
cd /home/brian/sam_gov
source .venv/bin/activate
python research/deep_research.py "J-2 psychological warfare since 2001"
```

### Output Location
- Directory: [Fill in: data/research_output/YYYY-MM-DD_HH-MM-SS_j2_psychological_warfare/]
- Main report: [Fill in: results.json or report.md]
- Duration: [Fill in: X minutes]
- Total results: [Fill in: X snippets from Y sources]

---

## Step 2: Manual Entity Extraction (30 minutes)

**Instructions**: Read through deep_research.py output and manually identify 10-20 important entities.

**Entity Types** (use these categories):
- `person` - Named individuals
- `organization` - Companies, agencies, groups
- `office` - Offices, roles, positions (e.g., "Joint Staff J-2")
- `program` - Operations, programs, initiatives, projects
- `concept` - Doctrines, topics, terms (e.g., "psychological warfare")

### Extracted Entities

| # | Entity Name | Type | Snippet (where you first saw it) | Source URL |
|---|-------------|------|----------------------------------|------------|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |
| 4 | | | | |
| 5 | | | | |
| 6 | | | | |
| 7 | | | | |
| 8 | | | | |
| 9 | | | | |
| 10 | | | | |
| 11 | | | | |
| 12 | | | | |
| 13 | | | | |
| 14 | | | | |
| 15 | | | | |

*(Add more rows as needed)*

---

## Step 3: Manual Pivoting Exercise (30 minutes)

**Instructions**: Pick 3-5 interesting entities from your list above. For each, scan through ALL snippets and note everywhere that entity appears.

### Entity Pivot #1: [Entity Name]

**Entity**: _____________________
**Type**: _____________________

**Appearances**:
1. **Snippet**: "[Quote from snippet...]"
   **Source**: [URL]

2. **Snippet**: "[Quote from snippet...]"
   **Source**: [URL]

3. **Snippet**: "[Quote from snippet...]"
   **Source**: [URL]

*(Continue for all appearances)*

**Patterns Noticed**:
- [What patterns/connections emerged from seeing all mentions together?]

---

### Entity Pivot #2: [Entity Name]

**Entity**: _____________________
**Type**: _____________________

**Appearances**:
1. **Snippet**: "[Quote...]"
   **Source**: [URL]

2. **Snippet**: "[Quote...]"
   **Source**: [URL]

*(Continue...)*

**Patterns Noticed**:
- [What patterns/connections emerged?]

---

### Entity Pivot #3: [Entity Name]

**Entity**: _____________________
**Type**: _____________________

**Appearances**:
1. **Snippet**: "[Quote...]"
   **Source**: [URL]

*(Continue...)*

**Patterns Noticed**:
- [What patterns/connections emerged?]

---

*(Add Entity Pivot #4 and #5 if you have time)*

---

## Step 4: Validation & Decision (15 minutes)

### Success Criteria Checklist

**Did manual entity pivoting help?**
- [ ] YES - Discovered patterns I wouldn't have seen reading linearly
- [ ] NO - Just reading the report would have been as effective

**Entities discovered through pivoting** (list any entities you noticed ONLY because you systematically searched for mentions):
1. [Entity name] - [Why you wouldn't have noticed it otherwise]
2. [Entity name] - [Why interesting]
3. [Entity name] - [Why interesting]

**New investigative angles** (list any new questions/leads that emerged from entity-based organization):
1. [New angle/question]
2. [New angle/question]
3. [New angle/question]

**Would automating this be valuable?**
- [ ] YES - Manual pivoting was tedious but clearly useful
- [ ] NO - The manual process is fine for my workflow
- [ ] MAYBE - Unclear if automation would help

---

## Decision

**Based on the above validation**:

- [ ] **GO to Stage 2** - Entity pivoting is useful, automate with CLI + database
- [ ] **STOP** - Entity organization doesn't add value over flat reading

**Reasoning**:
[Write 2-3 sentences explaining your decision]

---

## Notes & Observations

**What worked well?**
- [Free-form notes]

**What was frustrating?**
- [Free-form notes]

**Surprises?**
- [Free-form notes]

**Time breakdown**:
- deep_research.py run: ____ minutes
- Manual entity extraction: ____ minutes
- Pivoting exercise: ____ minutes
- Total: ____ minutes

---

## Next Steps

**If GO to Stage 2**:
1. Review Stage 2 spec (to be provided after this decision)
2. Create 3-table SQLite schema
3. Build minimal CLI for entity browsing

**If STOP**:
1. Document why entity-based organization didn't help
2. Consider alternative improvements to deep_research.py reporting
3. Archive this PoC directory
