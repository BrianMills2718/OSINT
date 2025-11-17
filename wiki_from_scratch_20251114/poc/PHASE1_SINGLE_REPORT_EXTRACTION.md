# Phase 1: Single-Report Entity Extraction

**Status**: In Progress
**Time Budget**: 1-2 hours
**Decision Gate**: GO / STOP

---

## Goal

Prove that LLM can reliably extract entities from a single investigative report before scaling to cross-report linking.

**Core Question**: "Can LLM entity extraction catch 80%+ of important entities without excessive noise?"

---

## What We're Building

A simple Python script that:
1. Reads ONE test report (`test_data/report3_bellingcat_fsb_elbrus.md`)
2. Sends full text to LLM with entity extraction prompt
3. LLM returns structured JSON with entities and their mentions
4. Outputs to `poc/phase1_output.json`
5. Human reviews extraction quality

**No database, no complex infrastructure** - just extraction + JSON output.

---

## Test Report

**File**: `test_data/report3_bellingcat_fsb_elbrus.md`
**Source**: Bellingcat, April 24, 2020
**Title**: "Identifying FSB's Elusive 'Elbrus': From MH17 To Assassinations In Europe"
**Size**: ~17KB, 70 lines

**Why this report**:
- Rich entity set (people, organizations, locations, units, operations)
- Mix of Russian and Western entities
- Contains aliases (Igor Egorov = "Elbrus", Igor Semyonov)
- Real-world investigative journalism complexity

**Expected key entities** (for validation):
- **People**: Igor Egorov/Elbrus, Valeriy Shaytanov, Adam Osmayev, Zelimkhan Khangoshvili, Oleg Ivannikov
- **Organizations**: FSB, SBU, GRU, Vympel, Department V
- **Locations**: Luhansk, Hamburg, Crimea, Germany, Ukraine, Moscow
- **Units**: 53rd Anti-Aircraft Brigade (if mentioned)
- **Operations/Concepts**: MH17, annexation of Crimea

---

## Entity Types (Phase 1)

Start simple with 6 core types:

1. **person** - Named individuals
2. **organization** - Institutions, agencies, companies
3. **location** - Countries, cities, regions, specific places
4. **unit** - Military/intelligence formations
5. **event** - Named operations, incidents (MH17, Crimea annexation)
6. **concept** - Key investigative topics (assassination, espionage)

**Notes**:
- Don't worry about perfect classification yet
- Focus on recall (catching entities) over precision
- Allow LLM to suggest additional types if needed

---

## LLM Prompt Strategy

**Approach**: Single-pass extraction with structured output

**Key prompt elements**:
1. Full report text as context
2. Entity type definitions with examples
3. Instructions to capture aliases/alternative names
4. Request for snippet context (where entity was mentioned)
5. JSON schema for structured output

**Output schema**:
```json
{
  "entities": [
    {
      "entity_id": "E1",
      "canonical_name": "Igor Egorov",
      "entity_type": "person",
      "aliases": ["Elbrus", "Igor Semyonov", "Col. Egorov"],
      "mentions": [
        {
          "snippet": "Col. Igor Egorov, deputy chairman of Vympel...",
          "context": "Describes Egorov's role in FSB"
        }
      ]
    }
  ],
  "metadata": {
    "report_id": "report3_bellingcat_fsb_elbrus",
    "total_entities_extracted": 0,
    "extraction_timestamp": "2025-11-16T..."
  }
}
```

---

## Success Criteria (Decision Gate)

### ✅ GO to Phase 2 if ALL true:

1. **Recall**: Captured 80%+ of "obvious" key entities
   - All major people mentioned (Egorov, Shaytanov, Osmayev, etc.)
   - Key organizations (FSB, SBU, GRU, Vympel)
   - Important locations (Luhansk, Hamburg, Crimea)

2. **Alias handling**: Captured entity name variations
   - "Egorov" and "Elbrus" linked to same entity
   - "Col. Egorov" and "Igor Egorov" recognized as same person

3. **Low noise**: < 20% obvious false positives
   - Didn't extract common nouns as entities ("the report", "the investigation")
   - Didn't create separate entities for obvious duplicates

4. **Actionable output**: JSON is well-formed and usable
   - Valid JSON syntax
   - Entity IDs unique
   - Snippet context provides useful provenance

### ❌ STOP if ANY true:

1. Missed >30% of major entities (low recall)
2. Failed to link obvious aliases (Egorov ≠ Elbrus)
3. >30% noise (extracting generic nouns)
4. JSON malformed or missing key fields
5. Took >30 minutes to extract (latency too high)

---

## Implementation Plan

### Step 1: Create extraction script (30 min)
- `poc/extract_entities.py`
- Imports: `llm_utils.acompletion`, `dotenv`, `json`, `asyncio`
- Read report markdown file
- Build extraction prompt
- Call LLM with JSON schema
- Save output to `poc/phase1_output.json`

### Step 2: Test extraction (15 min)
- Run script on report3
- Review JSON output for completeness
- Compare against expected entities list

### Step 3: Iterate on prompt if needed (30 min)
- If recall too low: adjust prompt to be more inclusive
- If noise too high: tighten entity type definitions
- Re-run and compare

### Step 4: Document results (15 min)
- Update this file with results
- Make GO/STOP decision
- If GO: create Phase 2 spec
- If STOP: document why and archive

---

## Output Artifacts

**Files created**:
- `poc/extract_entities.py` - Extraction script
- `poc/phase1_output.json` - Extracted entities from report3
- `poc/phase1_results.md` - Human review of extraction quality

---

## Notes

**This is a validation test, not production**:
- Single report only (report3)
- JSON file output (no database)
- Manual quality review (no automated metrics yet)
- Goal: Validate extraction quality before building infrastructure

**Key insight**: If entity extraction quality is poor on a single report, cross-report linking won't add value. Must prove this works first.

---

## Next Steps

**If GO → Phase 2**:
- Create `PHASE2_CROSS_REPORT_LINKING.md`
- Extend script to process all 3 reports
- Build SQLite database with entity linking
- Test cross-report entity queries

**If STOP**:
- Document why extraction failed
- Archive this PoC approach
- Consider alternative methods (rule-based NER, different LLM, etc.)
