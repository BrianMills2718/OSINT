# Phase 2: Cross-Report Entity Linking

**Status**: In Progress
**Time Budget**: 2-3 hours
**Decision Gate**: GO / STOP

---

## Goal

Prove that linking entities across multiple investigative reports reveals cross-document patterns that single-report analysis cannot.

**Core Question**: "Does seeing Entity X mentioned in reports A, B, and C reveal connections I would miss reading each report separately?"

---

## Prerequisites

**Phase 1 completed**: ✅
- Single-report extraction validated
- Extraction quality meets 80%+ threshold
- Output format proven usable

**Test data available**: ✅
- `test_data/report1_bellingcat_mh17_origin.md` (24KB, Nov 2014)
- `test_data/report2_bellingcat_gru_disinformation.md` (25KB, Nov 2020)
- `test_data/report3_bellingcat_fsb_elbrus.md` (17KB, Apr 2020)

All 3 reports are thematically related (MH17 investigation, Russian intelligence operations).

---

## What We're Building

### 1. Multi-Report Entity Extraction
Extend Phase 1 script to process all 3 reports and extract entities from each.

### 2. Entity Canonicalization
Use LLM to identify when entities across reports refer to the same real-world entity:
- "Egorov" (report3) = "Col. Igor Egorov" (report1, if mentioned)
- "53rd Brigade" (report1) = "53rd Anti-Aircraft Missile Brigade" (report2)
- "MH17" (all reports) = same event

### 3. SQLite Database
Simple schema for storing entities and cross-report linkages:

```sql
-- Core entities table
CREATE TABLE entities (
    entity_id TEXT PRIMARY KEY,
    canonical_name TEXT NOT NULL,
    entity_type TEXT NOT NULL,  -- person, organization, location, unit, event, concept
    aliases TEXT,  -- JSON array of alternative names
    first_seen_report TEXT,
    reports_seen_in TEXT  -- JSON array of report_ids
);

-- Evidence snippets table
CREATE TABLE evidence (
    evidence_id TEXT PRIMARY KEY,
    report_id TEXT NOT NULL,
    report_title TEXT,
    report_url TEXT,
    snippet_text TEXT NOT NULL,
    context TEXT  -- What this snippet reveals
);

-- Many-to-many: entities <-> evidence
CREATE TABLE entity_mentions (
    entity_id TEXT,
    evidence_id TEXT,
    PRIMARY KEY (entity_id, evidence_id),
    FOREIGN KEY (entity_id) REFERENCES entities(entity_id),
    FOREIGN KEY (evidence_id) REFERENCES evidence(evidence_id)
);
```

### 4. Simple CLI Query Tool
Command-line interface to test cross-report pivoting:

```bash
# Show all mentions of an entity across all reports
python query.py --entity "Igor Egorov"

# List entities appearing in 2+ reports
python query.py --cross-report

# Show all evidence for an entity
python query.py --entity "MH17" --verbose
```

---

## Implementation Plan

### Step 1: Extend Extraction Script (30 min)

**File**: `poc/extract_all_reports.py`

**Changes from Phase 1**:
- Loop over all 3 report files
- Extract entities from each
- Save intermediate JSON for each report
- Combine into single dataset

**Output**:
- `poc/report1_entities.json`
- `poc/report2_entities.json`
- `poc/report3_entities.json` (already have from Phase 1)
- `poc/all_reports_raw.json` (combined, pre-canonicalization)

---

### Step 2: Entity Canonicalization (45 min)

**File**: `poc/canonicalize_entities.py`

**Challenge**: Identify when entities across reports are the same:
- "Igor Egorov" (report3) might be mentioned as "Egorov" or "Col. Egorov" in report1
- "53rd Anti-Aircraft Brigade" might appear as "53rd Brigade" or "the Brigade"

**Approach**: Use LLM with cross-report entity list:

**Prompt strategy**:
```
Given these entity lists from 3 different reports on the same topic,
identify which entities refer to the same real-world entity.

Report 1 entities: [list]
Report 2 entities: [list]
Report 3 entities: [list]

Return a mapping of canonical entities with their appearances across reports.
```

**Output schema**:
```json
{
  "canonical_entities": [
    {
      "canonical_id": "CANON_E1",
      "canonical_name": "Igor Anatolyevich Egorov",
      "entity_type": "person",
      "source_entities": [
        {"report_id": "report1", "entity_id": "E5", "name": "Col. Egorov"},
        {"report_id": "report3", "entity_id": "E3", "name": "Igor Egorov"}
      ],
      "all_aliases": ["Igor Egorov", "Col. Egorov", "Elbrus", "Igor Semyonov"]
    }
  ]
}
```

---

### Step 3: Build SQLite Database (30 min)

**File**: `poc/build_database.py`

**Process**:
1. Create SQLite database: `poc/entities.db`
2. Create tables (entities, evidence, entity_mentions)
3. Populate `entities` table from canonicalized entity list
4. Populate `evidence` table from all snippets across reports
5. Populate `entity_mentions` junction table

**Schema notes**:
- `entities.aliases`: Store as JSON array
- `entities.reports_seen_in`: Store as JSON array (e.g., `["report1", "report3"]`)
- `evidence.report_id`: One of `report1`, `report2`, `report3`

---

### Step 4: Build CLI Query Tool (30 min)

**File**: `poc/query.py`

**Commands**:

```bash
# Query 1: Single entity across all reports
python query.py --entity "Igor Egorov"
# Output:
#   Entity: Igor Anatolyevich Egorov (person)
#   Aliases: Igor Egorov, Col. Egorov, Elbrus, Igor Semyonov
#   Seen in: report1, report3 (2 reports)
#
#   Evidence from report1:
#   - "Col. Egorov traveled to Luhansk in July 2014..."
#
#   Evidence from report3:
#   - "Bellingcat identified Col. Igor Egorov as FSB Vympel officer..."
#   - "Egorov served as deputy chairman of Vympel Veterans Association..."

# Query 2: Cross-report entities (bridge entities)
python query.py --cross-report
# Output:
#   Entities appearing in 2+ reports:
#   - MH17 (event): 3 reports
#   - Igor Egorov (person): 2 reports
#   - 53rd Anti-Aircraft Brigade (unit): 2 reports
#   - Buk missile (concept): 3 reports

# Query 3: All entities of a type
python query.py --type person
# Output:
#   People mentioned across all reports:
#   - Igor Egorov (2 reports)
#   - Oleg Ivannikov (1 report)
#   - ...
```

**Implementation**: Simple SQLite queries with `argparse` CLI

---

## Success Criteria (Decision Gate)

### ✅ GO to Phase 3 if ALL true:

1. **Cross-report entity linking works**
   - [ ] At least 3 entities appear in 2+ reports
   - [ ] Canonicalization correctly identifies same entity across reports
   - [ ] No obvious missed linkages (e.g., "Egorov" and "Elbrus" correctly linked)

2. **Database queries reveal patterns**
   - [ ] Can answer "Which entities appear in multiple reports?" in <5 seconds
   - [ ] Can see all evidence for a single entity across reports
   - [ ] Cross-report view reveals at least ONE pattern not obvious from single-report reading

3. **CLI is usable**
   - [ ] User can run queries without reading code
   - [ ] Output is readable and informative
   - [ ] No crashes or database errors

### ❌ STOP if ANY true:

1. **Canonicalization fails**
   - Obvious duplicates not linked (e.g., "MH17" in report1 vs "MH17" in report2 treated as separate)
   - False positives (linking unrelated entities)

2. **No cross-report entities found**
   - <3 entities appear in multiple reports
   - Reports are too unrelated (data selection problem)

3. **No new insights from cross-report view**
   - Grouping by entity doesn't reveal anything flat reading didn't
   - Cross-report patterns feel trivial or obvious

---

## Expected Cross-Report Entities (Validation)

Based on report topics, we expect these entities to appear in multiple reports:

**Definitely cross-report**:
- **MH17** (event): All 3 reports focus on this investigation
- **Buk missile** (concept): Central to MH17 event
- **53rd Anti-Aircraft Brigade** (unit): Likely in report1 (origin), report2 (evidence)
- **Luhansk / Donetsk** (locations): Conflict zone in all reports

**Possibly cross-report**:
- **Igor Egorov / Elbrus** (person): Report3 subject, might be mentioned in report1/2
- **Oleg Ivannikov / Orion** (person): Report3 mentions, check if in earlier reports
- **GRU / FSB** (organizations): Intelligence services likely mentioned across reports

If we find <3 cross-report entities, something is wrong (either with canonicalization or report selection).

---

## Test Queries for Validation

After Phase 2 is built, run these queries to validate:

```bash
# Test 1: MH17 should appear in all 3 reports
python query.py --entity "MH17"
# Expected: 3 reports

# Test 2: Cross-report entities
python query.py --cross-report
# Expected: 5-10 entities in 2+ reports

# Test 3: 53rd Brigade cross-report
python query.py --entity "53rd Anti-Aircraft Brigade"
# Expected: 2-3 reports

# Test 4: People type
python query.py --type person
# Expected: 15-20 unique people across all reports
```

---

## Output Artifacts

**Files created**:
- `poc/extract_all_reports.py` - Multi-report extraction script
- `poc/canonicalize_entities.py` - Entity canonicalization
- `poc/build_database.py` - SQLite database builder
- `poc/query.py` - CLI query tool
- `poc/entities.db` - SQLite database with cross-report entities
- `poc/report1_entities.json` - Report 1 raw extraction
- `poc/report2_entities.json` - Report 2 raw extraction
- `poc/all_reports_raw.json` - Combined pre-canonicalization
- `poc/canonical_entities.json` - Canonicalized entity map
- `poc/phase2_results.md` - Results documentation

---

## Time Budget

| Task | Time |
|------|------|
| Extend extraction to 3 reports | 30 min |
| Entity canonicalization | 45 min |
| Build SQLite database | 30 min |
| Build CLI query tool | 30 min |
| Testing & validation | 30 min |
| **Total** | **~3 hours** |

If exceeds 4 hours → STOP, something is wrong.

---

## Next Steps

**If GO → Phase 3**:
- Build entity co-occurrence analysis
- Add "which entities appear together" queries
- Create simple network graph visualization (optional)
- Test if co-occurrence patterns surface investigative insights

**If STOP**:
- Document why cross-report linking failed
- Assess if issue is technical (canonicalization) or conceptual (reports too unrelated)
- Decide: fix and retry, or archive PoC
