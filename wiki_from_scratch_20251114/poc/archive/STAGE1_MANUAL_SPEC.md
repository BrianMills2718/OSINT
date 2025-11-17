# Stage 1: Manual Entity Extraction Validation

**Status**: ARCHIVED - Replaced by phased automated approach (Phase 1-3)
**Date Archived**: 2025-11-16
**Reason**: User confirmed need for cross-document entity linking, decided to skip manual validation and proceed directly to automated extraction

**See instead**: `PHASE1_SINGLE_REPORT_EXTRACTION.md` (automated approach)

---

# Original Manual Spec (Archived for Reference)

**Original Status**: Not Started
**Time Budget**: 3 hours total
**Decision Gate**: GO / STOP / RETEST

---

## What Stage 1 Tests

> "Given 2-3 public investigative reports on related topics, does grouping snippets by entities across reports help me see connections and new leads that flat reading does not?"

**Key insight**: The value of entity-based organization is **cross-document pivoting**, not single-document analysis. Stage 1 tests this with manual extraction from public sources.

---

## Prerequisites

Before starting Stage 1:

1. ✅ You have 2-3 public investigative reports saved in `test_data/`
2. ✅ Topics are thematically related (same entities likely to recur across reports)
3. ✅ Each report has sufficient depth (10-15 entity-rich snippets available)

**Recommended sources** (see `test_data/README.md` for details):
- **Option A (Recommended)**: Bellingcat MH17 investigation series (3 reports)
- **Option B**: ProPublica Machine Bias series (3 reports)
- **Option C**: CIA/NSA FOIA documents on intelligence programs
- **Option D**: Long-form NYT/WaPo investigations (5000+ words each)

---

## Time Budget Breakdown

| Activity | Time |
|----------|------|
| Flat reading (baseline) | 30-45 min |
| Entity extraction | 60-90 min |
| Entity pivoting experiments | 30-45 min |
| Documentation | 30 min |
| **TOTAL** | **~3 hours** |

If you exceed 4 hours → STOP and document why. Something is wrong with the process.

---

## Data Scope (Avoid 4-Hour Hell)

**From each of 2-3 public reports, sample:**
- ~10-15 snippets that look **entity-rich** (mentions specific people, orgs, programs, offices)
- Prefer snippets with multiple entity types co-occurring
- Skip generic/low-information snippets

**Total target:**
- 30-40 snippets across all reports
- 20-50 entities (rough estimate)

**Selection criteria**:
- Contains specific named entities (not just generic terms like "the military" or "the investigation")
- Has potential for cross-snippet connections
- Representative of the report's key findings

**Snippet extraction tips**:
- Look for paragraphs mentioning multiple entities (people AND organizations AND programs)
- Prefer dense entity contexts (e.g., "Commander X of Unit Y testified about Program Z")
- Keep snippets ~100-200 words (enough context, not overwhelming)

---

## Minimal Spreadsheet Schema

Use Google Sheets / Excel / LibreOffice with **two sheets**:

### Sheet 1: Entities

| entity_id | entity_name | entity_type | reports_seen_in | notes |
|-----------|-------------|-------------|-----------------|-------|
| E1 | 53rd Anti-Aircraft Brigade | unit | report1, report2, report3 | Russian military unit |
| E2 | Buk missile system | equipment | report1, report2 | Surface-to-air missile |
| E3 | Oleg Ivannikov | person | report3 | GRU commander, code name "Orion" |

**Fields**:
- `entity_id`: Simple sequential ID (E1, E2, E3...)
- `entity_name`: Canonical name (most specific form you'll search for)
- `entity_type`: One of: `person`, `organization`, `office`, `program`, `unit`, `codeword`, `concept`, `location`, `equipment`
- `reports_seen_in`: Comma-separated list of report IDs (THIS IS KEY for cross-report testing)
- `notes`: Optional aliases, clarifications

### Sheet 2: Evidence

| evidence_id | report_id | source_url | snippet_text | entity_mentions |
|-------------|-----------|------------|--------------|-----------------|
| EV1 | report1 | https://bellingcat.com/... | "In 2014, the 53rd Anti-Aircraft Brigade..." | 53rd Anti-Aircraft Brigade; Buk missile system; Donetsk |
| EV2 | report3 | https://bellingcat.com/... | "Commander Oleg Ivannikov of the GRU..." | Oleg Ivannikov; GRU; 53rd Anti-Aircraft Brigade |

**Fields**:
- `evidence_id`: Simple sequential ID (EV1, EV2...)
- `report_id`: Which report this came from (report1, report2, report3)
- `source_url`: Original source URL of the report
- `snippet_text`: The actual text (keep it ~100-200 words for Stage 1)
- `entity_mentions`: Semicolon-separated list of entity_name values from Entities sheet

---

## Entity Extraction Rules

### What to extract as entities:

**Include**:
- ✅ Specific people (Col. Jane Doe, John Smith)
- ✅ Specific orgs (Joint Staff J-2, CIA, SOCOM)
- ✅ Offices/roles (Deputy Director for Intelligence, J-2, Undersecretary)
- ✅ Programs/operations (Operation NIGHTFIRE, Project ABC)
- ✅ Units/formations (4th PSYOP Group, JSOC)
- ✅ Codewords/codenames (if clearly used as proper nouns)
- ✅ Key concepts (psychological operations, information warfare) - **only if central to investigation**

**Skip**:
- ❌ Super generic nouns ("the report", "military operations", "the government")
- ❌ Single-use trivial terms
- ❌ Common verbs/adjectives

### Naming granularity:

Use the **most specific label that will actually show up in pivots**:
- Prefer: `Joint Staff J-2` (full formal name)
- Note shorter forms in `notes` column: "Also called J-2"

For Stage 1, don't create separate alias rows - just one canonical entity with aliases in notes.

### Entity types (for Stage 1):

1. **person** - Individuals (Col. Jane Doe)
2. **organization** - Institutions (CIA, Pentagon, think tanks)
3. **office** - Roles/positions (J-2, Deputy Director)
4. **program** - Named operations/projects (Operation NIGHTFIRE)
5. **unit** - Military formations (4th PSYOP Group, JSOC)
6. **codeword** - Classified program names (if clearly used as proper nouns)
7. **concept** - Core investigative topics (psychological operations, information warfare)
8. **location** - Places (countries, bases, regions)

Don't stress over perfect classification - "good enough to pivot" is the bar.

---

## Process: Comparison Baseline

**CRITICAL**: Do flat reading FIRST, then entity pivoting. This creates the comparison baseline.

### Step A: Flat Reading (30-45 min)

1. Read the same 30-40 snippets you'll extract (or the original reports)
2. Take notes as you normally would:
   - "Key findings about X"
   - "Interesting leads to follow up"
   - "Connections between Y and Z"
3. **Stop and save your notes** before moving to Step B

### Step B: Entity Extraction (60-90 min)

1. Create the two spreadsheet sheets (Entities, Evidence)
2. For each snippet:
   - Add row to Evidence sheet
   - Identify entities mentioned
   - Add new entities to Entities sheet (or link to existing)
   - Fill `entity_mentions` column
3. As you go, populate `runs_seen_in` for entities appearing in multiple runs

### Step C: Entity Pivoting (30-45 min)

Follow the three pivot experiments below. Take notes on what you discover.

---

## The Three Pivoting Experiments

### Pivot 1: Single-Entity Evidence Sweep

**Goal**: Does seeing all mentions of key entity together reveal patterns?

1. Pick 3-5 "important" entities (e.g., J-2, a program name, a person who appears multiple times)
2. For each entity:
   - Filter Evidence sheet where `entity_mentions` contains that entity
   - Read all those snippets together (ignore source/run)
3. Ask yourself:
   - "Does seeing all J-2 snippets together change how I understand its role?"
   - "Did I notice connections I missed during flat reading?"

**Document**: Specific examples of new insights (or lack thereof)

### Pivot 2: Co-occurrence / Bridge Entities

**Goal**: Find entities that connect different themes/subtopics

1. For each key entity from Pivot 1:
   - Look at all `entity_mentions` in those snippets
   - Note which OTHER entities keep showing up with it
2. You're looking for **bridge entities**:
   - "Person X keeps appearing with J-2 AND psyops AND contractor Y"
   - "Program Z links office A and concept B repeatedly"

**Document**: Examples of bridge entities that surfaced patterns

### Pivot 3: Cross-Report Recurrence

**Goal**: Do entities appearing in multiple reports reveal cross-document connections?

1. In Entities sheet, filter where `reports_seen_in` contains **2+ reports**
2. For each recurring entity:
   - Check its evidence snippets across reports
   - Compare: How is it discussed in report1 vs report2 vs report3?
3. Ask yourself:
   - "Is this entity connecting separate parts of the investigation in a way I didn't track during flat reading?"
   - "Did cross-report recurrence surface a pattern I would have missed?"

**Document**: Specific examples of cross-report insights

---

## Success Criteria (Hard Gates)

Call Stage 1 a **GO** ONLY if you can check ALL three boxes:

### ✅ Criterion 1: Specific New Connection
- [ ] I can point to **at least one concrete example** where:
  - "I realized X and Y are linked **because** I saw them grouped under entity Z across multiple snippets/runs"
  - This connection did NOT emerge during flat reading

**Example of what counts**:
> "I didn't notice Col. Doe's connection to Operation NIGHTFIRE during flat reading because they were mentioned 3 runs apart. Grouping by 'J-2' entity showed Doe held J-2 role when NIGHTFIRE launched."

### ✅ Criterion 2: New Lead/Question
- [ ] I identified **at least one new investigative lead or question** that:
  - I did NOT write down during flat reading (Step A)
  - Emerged specifically from entity pivoting (Step C)

**Example of what counts**:
> "Pivoting on 'psychological operations' entity revealed Contractor X appears in 3/3 runs but always tangentially. New question: What's Contractor X's actual role?"

### ✅ Criterion 3: Efficiency or Clarity Gain
- [ ] Entity pivoting either:
  - Saved me **~20+ minutes** I would have spent re-scanning/re-reading to answer a question like "Where have I seen Program X before?"
  - **OR** Made a complex investigation question (e.g., "Which J-2 directors touched psyops?") dramatically easier to answer

**Example of what counts**:
> "Answering 'Which J-2 directors are mentioned across all runs?' took 30 seconds with entity filter. Would have taken 15+ minutes scanning all snippets manually."

---

## Decision Gates

### GO → Proceed to Stage 2
**Requirements**: All 3 success criteria met with specific documented examples

Next step: Build Stage 2 (SQLite + CLI, 4-6 hours)

### STOP → Do not build entity infrastructure
**Triggers**:
- Cannot provide specific examples for Criteria 1 or 2
- Entity pivoting felt like busywork compared to flat reading
- Time spent extracting > value gained from pivoting

Next step: Document why in stage1_manual_test.md, archive this project

### RETEST → Unclear, need different test data
**Triggers**:
- Test runs weren't thematically related enough (low cross-run recurrence)
- Topics were too simple/straightforward (job research vs investigative journalism)
- Sample size too small (< 25 snippets total)

Next step: Generate 2-3 new runs on proper investigative topic, retry Stage 1

---

## Documentation Template

Save results to: `/home/brian/sam_gov/wiki_from_scratch_20251114/poc/stage1_manual_test.md`

```markdown
## Research Question(s)
- Topic: [brief description]
- Reports used:
  - report1: [title/URL]
  - report2: [title/URL]
  - report3: [title/URL]

## Source Material
- Number of reports: N
- Total snippets sampled: N
- Publication sources: [e.g., Bellingcat, ProPublica, NYT]

## Time Tracking
- Flat reading: X min
- Entity extraction: X min
- Entity pivoting: X min
- Documentation: X min
- **Total: X min**

## Entity Extraction Results
- Total entities: N
- Breakdown:
  - people: n
  - organizations: n
  - offices: n
  - programs: n
  - units: n
  - concepts: n
  - codewords: n
  - locations: n
- Entities appearing in 2+ runs: N (list key ones)

## Flat Reading Findings (Baseline)
**Notes taken during Step A (before entity extraction)**:

- [Bullet list of key findings from flat reading]
- [Leads/questions identified]
- [Connections noticed]

## Entity Pivoting Results

### Pivot 1: Single-Entity Evidence Sweep
**Entities tested**: [E1, E2, E3...]

**Findings**:
- Entity E1 (name): [What did grouping reveal? Any new insights?]
- Entity E2 (name): [Same]
- Entity E3 (name): [Same]

### Pivot 2: Co-occurrence / Bridge Entities
**Bridge entities discovered**:
- [Entity X linked Y and Z across N snippets]
- [Entity A appeared with B, C, D repeatedly]

**Specific examples**:
- [Concrete example of pattern surfaced by co-occurrence]

### Pivot 3: Cross-Report Recurrence
**Entities seen in 2+ reports**: [count, list key ones]

**Cross-report insights**:
- Entity X appeared in reports A and B:
  - In report A: [summary of how discussed]
  - In report B: [summary of how discussed]
  - New connection/angle: [what emerged from comparing]

## Comparison: Flat vs Entity-Based
**What flat reading gave me**:
- [Bullet list from Step A notes]

**What entity pivoting ADDITIONALLY gave me**:
- [New leads/questions NOT in flat reading notes]
- [Connections missed during flat reading]
- [Time saved or clarity gained]

**What entity pivoting did NOT help with**:
- [Honest assessment of where it felt like busywork]
- [Things flat reading handled just as well]

## Success Criteria Assessment

### Criterion 1: Specific New Connection
- [ ] YES / [ ] NO
- Example: [Concrete example or "N/A"]

### Criterion 2: New Lead/Question
- [ ] YES / [ ] NO
- Example: [Concrete example or "N/A"]

### Criterion 3: Efficiency/Clarity Gain
- [ ] YES / [ ] NO
- Example: [Concrete example or "N/A"]

## Decision: GO / STOP / RETEST

**Decision**: [GO / STOP / RETEST]

**Reasoning**:
- [Tie back to specific examples above]
- [If GO: why is Stage 2 worth building?]
- [If STOP: what would need to change to reconsider?]
- [If RETEST: what test data/approach would work better?]

**Confidence level**: [High / Medium / Low]

**Caveats**:
- [E.g., "Only tested 30 snippets from 3 reports - limited sample"]
- [E.g., "Reports were all from same source (Bellingcat) - may not generalize"]
- [E.g., "Entity types skewed toward military/equipment - different domains may differ"]

## Next Steps
- If GO: [Proceed to Stage 2 spec]
- If STOP: [Archive project, document lessons]
- If RETEST: [Specify new test queries/data needed]
```

---

## Notes and Caveats

**This is a validation test, not production**:
- Stage 1 is deliberately manual and small-scale
- Goal is to validate the HYPOTHESIS (does entity pivoting add value?), not build infrastructure
- Be brutally honest in assessment - false positives waste weeks of implementation time

**Data quality matters**:
- If test runs aren't thematically related, you'll get a false negative
- If topics are too simple (job research vs investigative journalism), entity value may be underestimated
- Document data limitations in stage1_manual_test.md

**Time budget is a hard constraint**:
- If you exceed 4 hours, something is wrong with the process
- Either scope is too large (reduce snippets) or the task is too tedious (red flag for automation)

**Honest assessment required**:
- Don't squint to find value that isn't there
- Document what DIDN'T work as thoroughly as what did
- A clear STOP is more valuable than a weak GO

---

## Quick Reference

**Files**:
- This spec: `/home/brian/sam_gov/wiki_from_scratch_20251114/poc/STAGE1_SPEC.md`
- Test data: `/home/brian/sam_gov/wiki_from_scratch_20251114/test_data/`
- Results doc: `/home/brian/sam_gov/wiki_from_scratch_20251114/poc/stage1_manual_test.md`

**Spreadsheet template**: (create manually in Google Sheets / Excel)
- Sheet 1: Entities (entity_id, entity_name, entity_type, runs_seen_in, notes)
- Sheet 2: Evidence (evidence_id, run_id, source_url, snippet_text, entity_mentions)

**Time budget**: 3 hours (hard stop at 4 hours)

**Success criteria**: All 3 must be met with specific examples

**Decision gates**: GO / STOP / RETEST (document reasoning)
