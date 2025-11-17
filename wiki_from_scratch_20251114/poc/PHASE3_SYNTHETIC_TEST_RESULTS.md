# Phase 3 Synthetic Test Results

**Date**: 2025-11-17
**Purpose**: Validate co-occurrence infrastructure with deliberately high entity density
**Status**: ✅ **INFRASTRUCTURE VALIDATED**

---

## Test Design

**Created**: `test_data/synthetic_cooccurrence_test.md`

**Approach**: Synthetic investigative report with:
- Fictional "Operation Nightfall" investigation
- 72 lines of narrative text
- Deliberately high entity density (5-10 entities per paragraph)
- Key entities repeated across multiple paragraphs

**Example paragraph** (lines 9-11, 72 lines total):
```
The FSB and GRU coordinated Operation Nightfall in Eastern Ukraine during July 2014.
Colonel Igor Petrov (FSB) and Major Sergei Ivanov (GRU) led the operation from Moscow,
with direct support from the 53rd Anti-Aircraft Brigade based in Kursk. The operation
utilized a Buk missile system, which was transported from Russia to Ukraine to support
separatist forces in Donetsk.
```

**Entities in this paragraph**: 13+
- FSB, GRU, Operation Nightfall, Eastern Ukraine, Colonel Igor Petrov, Major Sergei Ivanov
- Moscow, 53rd Anti-Aircraft Brigade, Kursk, Buk missile system, Russia, Ukraine
- separatist forces, Donetsk

---

## Extraction Results

**Command**:
```bash
python3 poc/extract_entities.py test_data/synthetic_cooccurrence_test.md
```

**Output**: `poc/synthetic_cooccurrence_test_entities.json`

**Extraction statistics**:
- Report length: 6,311 characters
- Entities extracted: **27**
- Entity breakdown:
  - person: 7 (Igor Petrov, Sergei Ivanov, Oleg Markov, Anna Volkova, Dmitri Sokolov, Eliot Higgins, Christo Grozev)
  - organization: 7 (FSB, GRU, 53rd Brigade, Bellingcat, The Insider, Twitter, VKontakte)
  - location: 6 (Moscow, Kursk, Rostov, Donetsk, Russia, Ukraine)
  - concept: 4 (Buk missile system, separatist forces, OSINT, geotagging)
  - unit: 2 (Unit 29155, 53rd Anti-Aircraft Brigade)
  - event: 1 (Operation Nightfall)

**Evidence snippets**: 53 (average 1.96 snippets per entity)

---

## Co-occurrence Analysis Results

**Command**:
```bash
python3 poc/analyze_cooccurrence.py
```

**Overall database statistics** (after adding synthetic):
- Total entity pairs: **78** (was 55 before synthetic)
- Average co-occurrence: 1.0
- Snippets with 2+ entities: 42 (10 from synthetic)

**Synthetic-specific co-occurrence**:
```
Snippets with 2-3 entities from synthetic document:

3 entities: "The FSB and GRU coordinated Operation Nightfall in Eastern Ukraine during July 2014."
  Entity IDs: E1, E2, E3
  Entities: Operation Nightfall, Federal Security Service, Main Intelligence Directorate

3 entities: "Colonel Igor Petrov (FSB) and Major Sergei Ivanov (GRU) led the operation from Moscow..."
  Entity IDs: E4, E5, E16
  Entities: Colonel Igor Petrov, Major Sergei Ivanov, Moscow

3 entities: "The Buk missile system, accompanied by Lieutenant Markov and Captain Sokolov, crossed from Russia into Ukraine near Donetsk."
  Entity IDs: E6, E8, E19
  Entities: Lieutenant Oleg Markov, Captain Dmitri Sokolov, Donetsk

3 entities: "Eliot Higgins led the Bellingcat investigation team, focusing on open-source intelligence analysis."
  Entity IDs: E12, E14, E26
  Entities: Bellingcat, Eliot Higgins, open-source intelligence

3 entities: "Christo Grozev identified key VKontakte accounts linked to the 53rd Anti-Aircraft Brigade and Unit 29155."
  Entity IDs: E9, E15, E23
  Entities: Unit 29155, Christo Grozev, VKontakte

3 entities: "Eliot Higgins pioneered techniques for tracking the Buk missile system through Twitter geotagging."
  Entity IDs: E14, E22, E27
  Entities: Eliot Higgins, Twitter, geotagging

2 entities: "Bellingcat and The Insider conducted parallel investigations into Operation Nightfall."
  Entity IDs: E12, E13
  Entities: Bellingcat, The Insider

2 entities: "Agent Anna Volkova provided intelligence support from a forward position in Rostov."
  Entity IDs: E7, E18
  Entities: Agent Anna Volkova, Rostov-on-Don

2 entities: "Christo Grozev directed The Insider's efforts, specializing in Russian intelligence operations."
  Entity IDs: E13, E15
  Entities: The Insider, Christo Grozev

2 entities: "Major Ivanov coordinated with local separatist commanders in Donetsk."
  Entity IDs: E5, E24
  Entities: Major Sergei Ivanov, separatist forces
```

**Total**: 10 snippets with 2-3 entities each from synthetic document

---

## Query Validation

### Test 1: Entity Co-occurrence Query

**Command**:
```bash
python3 poc/query.py --cooccur "Federal Security Service"
```

**Result**:
```
Entities that co-occur with: Federal Security Service (organization)

  - Main Intelligence Directorate (organization): 1 time
  - Operation Nightfall (event): 1 time
```

✅ **PASS**: Co-occurrence correctly identifies FSB appears with GRU and Operation Nightfall

---

### Test 2: Bridge Entities Query

**Command**:
```bash
python3 poc/query.py --bridges
```

**Result** (showing synthetic entities):
```
Bridge Entities (top 15 by connection count):

  Major Sergei Ivanov (person)
    Connects to: 3 entities
    Total co-occurrences: 3

  Christo Grozev (person)
    Connects to: 3 entities
    Total co-occurrences: 3
```

✅ **PASS**: Bridge entities query correctly identifies entities with multiple connections

---

### Test 3: Cross-Report Entities

**Command**:
```bash
python3 poc/query.py --cross-report
```

**Result**: Synthetic entities show as 1 report only (correct)

✅ **PASS**: Synthetic entities correctly isolated from real reports

---

## Critical Finding: Extraction Methodology Limitation

### The Problem

**Source text** (synthetic document, line 9):
```
The FSB and GRU coordinated Operation Nightfall in Eastern Ukraine during July 2014.
```

**Entities in this sentence**: 4+
- FSB, GRU, Operation Nightfall, Eastern Ukraine

**How LLM extracted it**:
- Entity E1 (Operation Nightfall): snippet "The FSB and GRU coordinated Operation Nightfall in Eastern Ukraine during July 2014."
- Entity E2 (FSB): snippet "The FSB and GRU coordinated Operation Nightfall in Eastern Ukraine during July 2014."
- Entity E3 (GRU): snippet "The FSB and GRU coordinated Operation Nightfall in Eastern Ukraine during July 2014."

**Database storage**:
```
evidence table:
  E1_m1: "The FSB and GRU coordinated Operation Nightfall..."
  E2_m1: "The FSB and GRU coordinated Operation Nightfall..."
  E3_m1: "The FSB and GRU coordinated Operation Nightfall..."

entity_mentions table:
  E1 -> E1_m1
  E2 -> E2_m1
  E3 -> E3_m1
```

**Result**: 3 separate evidence_id rows with identical snippet_text

**Co-occurrence query**:
```sql
SELECT e.snippet_text, GROUP_CONCAT(em.entity_id) as entities
FROM evidence e
JOIN entity_mentions em ON e.evidence_id = em.evidence_id
GROUP BY e.snippet_text
HAVING COUNT(em.entity_id) > 1
```

**This finds**: 3 entities (E1, E2, E3) sharing the snippet ✅

**But**: Only because the LLM happened to extract the EXACT same text for all three entities.

---

## Conclusion: Infrastructure WORKS, Extraction Has Limitations

### ✅ **VALIDATED**: Co-occurrence Infrastructure Works

**Evidence**:
1. **10 snippets** in synthetic document have 2-3 entities each
2. **Co-occurrence queries** correctly identify shared entities
3. **Bridge entity queries** correctly rank entities by connection count
4. **SQLite schema** correctly groups entities by snippet_text

**Conclusion**: The co-occurrence infrastructure (database schema, SQL queries, CLI tool) **works correctly** when entities share exact snippet text.

---

### ⚠️ **LIMITATION**: Extraction Methodology

**Issue**: LLM creates mostly unique snippets per entity, even from the same source paragraph

**Why sparsity occurs**:
1. Entity extraction prompts LLM: "For each entity, provide snippets"
2. LLM creates separate snippets per entity
3. Even when entities are in the same paragraph, LLM often extracts different excerpts
4. Co-occurrence only triggers when snippet_text is **exactly identical**

**Example from synthetic (paragraph with 13+ entities)**:
```
Source: "The FSB and GRU coordinated Operation Nightfall in Eastern Ukraine during
July 2014. Colonel Igor Petrov (FSB) and Major Sergei Ivanov (GRU) led the operation
from Moscow, with direct support from the 53rd Anti-Aircraft Brigade based in Kursk."

Expected co-occurrence: 13+ entities in one snippet

Actual result:
- E1, E2, E3 share "The FSB and GRU coordinated Operation Nightfall..." (3 entities)
- E4, E5, E16 share "Colonel Igor Petrov (FSB) and Major Sergei Ivanov (GRU) led..." (3 entities)

Total: 2 snippets with 3 entities each = 6 entities co-occurring (not 13+)
```

**Why**: LLM extracted two different snippets from the same 2-sentence paragraph

---

## Recommendations

### Option A: Accept Current Approach (Documented Limitation)

**Status quo**:
- Infrastructure works correctly
- Co-occurrence exists but is sparse
- Limitation is well-understood

**Use case**: Cross-report entity linking works great (17 entities across 3 reports). Co-occurrence is a nice-to-have bonus when it occurs.

**Documentation**: Update phase3_results.md with:
```
Co-occurrence Analysis:
- 78 entity pairs identified across 4 reports
- 10 snippets in synthetic test with 2-3 entities each
- Limitation: LLM creates mostly unique snippets per entity
- Recommendation: For production, use paragraph-level extraction (see Option B)
```

---

### Option B: Re-extract at Paragraph Level (Future Work)

**New extraction approach**:
1. Divide reports into paragraphs
2. For each paragraph, extract ALL entities mentioned
3. Store paragraph as single evidence snippet
4. Link all entities to that evidence snippet

**Expected result**: Natural co-occurrence from source text preserved

**Example**:
```
evidence table:
  para_17: "The FSB and GRU coordinated Operation Nightfall in Eastern Ukraine..."

entity_mentions table:
  E1 -> para_17
  E2 -> para_17
  E3 -> para_17
  E4 -> para_17
  E5 -> para_17
  ...
  E13 -> para_17
```

**Benefit**: Co-occurrence reflects actual entity proximity in source text

**Cost**: Requires re-extraction of all reports (~10 minutes for 4 reports)

---

## Phase 3 Decision

**Status**: ✅ **GO TO PRODUCTION**

**Rationale**:
1. ✅ Co-occurrence infrastructure validated and working
2. ✅ Cross-report entity linking works (17 entities)
3. ✅ CLI queries functional and performant (<0.03s)
4. ✅ Database schema solid (168 entities, 297 evidence snippets, 78 co-occurrence pairs)
5. ⚠️ Extraction methodology creates sparse co-occurrence (known limitation, fixable in future)

**Deliverables**:
- `poc/entities.db` - SQLite database with 168 canonical entities, 297 evidence snippets
- `poc/query.py` - CLI tool for entity queries, cross-report pivoting, co-occurrence analysis
- `poc/PHASE3_FINDINGS.md` - Root cause analysis of sparsity
- `poc/PHASE3_SYNTHETIC_TEST_RESULTS.md` - Infrastructure validation results (this document)

**Next steps**:
- Update `phase3_results.md` with final decision
- Archive POC work
- (Future) Implement paragraph-level extraction for dense co-occurrence

---

## Test Reproducibility

### Setup
```bash
cd /home/brian/sam_gov/wiki_from_scratch_20251114
source /home/brian/sam_gov/.venv/bin/activate
```

### Extract Entities from Synthetic
```bash
python3 poc/extract_entities.py test_data/synthetic_cooccurrence_test.md
# Output: poc/phase1_output.json (27 entities, 53 evidence snippets)
```

### Add to Database
```bash
# Manually copy phase1_output.json to synthetic_cooccurrence_test_entities.json
# Run Python script to insert into entities.db
```

### Run Co-occurrence Analysis
```bash
python3 poc/analyze_cooccurrence.py
# Output: 78 entity pairs, 10 snippets with 2+ entities from synthetic
```

### Query Examples
```bash
python3 poc/query.py --cooccur "Federal Security Service"
python3 poc/query.py --cooccur "Operation Nightfall"
python3 poc/query.py --bridges
python3 poc/query.py --stats
```

---

**End of synthetic test validation**
