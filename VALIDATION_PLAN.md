# Validation Plan - Before Implementation

**Date**: 2025-10-24
**Purpose**: Validate assumptions BEFORE building features (per Codex review feedback)
**Status**: Ready to execute

---

## Philosophy

**ADVERSARIAL TESTING**: Assume features will fail. Prove they work with evidence BEFORE investing implementation time.

**Validation BEFORE Implementation**:
- ✅ 50 min validation → discover feature is useless → save 4-6 hours
- ❌ 4-6 hours implementation → discover feature is useless → waste 4-6 hours

---

## Two Features Needing Validation

### 1. Context7 MCP Integration (Library Documentation)
**Claimed benefit**: Better library docs than web search
**Risk**: Node.js dependency, third-party maintenance, unknown data quality
**Validation time**: 1 hour

### 2. crest_kg Integration (Enhanced Entity Extraction)
**Claimed benefit**: Entities with relationships + attributes vs just names
**Risk**: Performance cost, quality unknown, schema compatibility
**Validation time**: 50 minutes

---

## Validation 1: Context7 MCP (1 hour)

### Step 1: Local STDIO Test (30 min)

**What to test**:
```bash
# Setup
cd /tmp
git clone https://github.com/context7/context7-mcp-server
cd context7-mcp-server
npm install

# Test 1: Startup time
time npx tsx src/index.ts
# Expected: <5 seconds
# If >10 seconds: TOO SLOW for real-time use

# Test 2: Error handling
# Remove npm packages, see what error message looks like
# Do errors surface clearly or silently fail?

# Test 3: MCP client call
# Create simple Python MCP client test
# Call resolve-library-id + get-library-docs
# Measure end-to-end time
```

**Evidence to collect**:
- Startup time: X seconds
- Query time: Y seconds
- Error behavior: Clear/Silent
- Total overhead: X+Y seconds acceptable? YES/NO

**Success criteria**:
- Startup: <5 seconds
- Query: <3 seconds
- Errors: Clear and actionable
- **If ANY fail → NO-GO**

---

### Step 2: Data Quality Test (15 min)

**Test queries** (investigative journalism use cases):
```python
# Query 1: Next.js (popular library)
resolve_library_id("Next.js")
get_library_docs("/vercel/next.js", topic="server components")

# Query 2: PostgreSQL (database docs)
resolve_library_id("PostgreSQL")
get_library_docs("/postgres/postgres", topic="JSON queries")

# Query 3: FastAPI (Python framework)
resolve_library_id("FastAPI")
get_library_docs("/tiangolo/fastapi", topic="async endpoints")
```

**Evidence to collect**:
For each query, check:
- **Relevance**: Docs match topic? (1-10 score)
- **Currency**: Docs from 2024-2025? (YES/NO)
- **Completeness**: Enough info to answer question? (YES/NO)
- **vs Brave Search**: Better than web search? (BETTER/SAME/WORSE)

**Success criteria**:
- Relevance: ≥7/10 average
- Currency: 100% current docs
- Completeness: ≥80% answer question
- vs Brave: BETTER or SAME
- **If ANY fail → NO-GO**

---

### Step 3: Streamlit Cloud Compatibility (5 min)

**Test**: Check Streamlit Cloud documentation

**Questions**:
- Can Streamlit Cloud run Node.js processes? (YES/NO)
- Can it execute subprocess.Popen? (YES/NO)
- Any workarounds available? (YES/NO/UNKNOWN)

**Expected result**: NO (Python-only environment)

**Implication**: Context7 MCP is **desktop-only** for Phase 1

**Decision needed**: Is desktop-only acceptable?

---

### Step 4: Document Findings (10 min)

**Create**: `/home/brian/sam_gov/CONTEXT7_VALIDATION_RESULTS.md`

**Format**:
```markdown
# Context7 MCP Validation Results

## Test Environment
- Date: 2025-10-24
- Node.js version: X.X.X
- MCP server version: X.X.X

## Performance Test
- Startup time: X.X seconds
- Query time: Y.Y seconds
- Error handling: Clear/Silent
- **VERDICT**: PASS/FAIL

## Data Quality Test
Query 1 (Next.js):
- Relevance: X/10
- Currency: YES/NO
- Completeness: YES/NO
- vs Brave Search: BETTER/SAME/WORSE

Query 2 (PostgreSQL):
[same format]

Query 3 (FastAPI):
[same format]

**AVERAGE SCORES**:
- Relevance: X/10
- **VERDICT**: PASS/FAIL

## Streamlit Cloud Compatibility
- Node.js available: NO
- Workaround: None found
- **VERDICT**: Desktop-only feature

## FINAL DECISION
- [ ] GO - Proceed with hybrid plan (desktop-only Phase 1)
- [ ] NO-GO - Data quality/performance insufficient
- [ ] DEFER - Re-evaluate when Streamlit Cloud supports Node.js

**Recommendation**: [GO/NO-GO/DEFER]
**Rationale**: [Why]
```

---

## Validation 2: crest_kg Integration (50 min)

### Step 1: Schema Compatibility Test (10 min)

**What to test**:
```python
# Test crest_kg schema with gpt-5-mini strict JSON mode
from llm_utils import acompletion
import json

schema = {
    "type": "object",
    "properties": {
        "entities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "name": {"type": "string"},
                    "type": {"type": "string", "enum": ["person", "organization", "location", "event", "concept"]},
                    "attributes": {"type": "object"}  # <-- CRITICAL: arbitrary key-value pairs
                },
                "required": ["id", "name", "type"],
                "additionalProperties": False
            }
        },
        "relationships": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "source": {"type": "string"},
                    "target": {"type": "string"},
                    "type": {"type": "string"},
                    "attributes": {"type": "object"}
                },
                "required": ["source", "target", "type"],
                "additionalProperties": False
            }
        }
    },
    "required": ["entities", "relationships"],
    "additionalProperties": False
}

response = await acompletion(
    model="gpt-5-mini",
    messages=[{"role": "user", "content": "Extract entities from: 'JSOC works with CIA on Title 50 operations in Afghanistan.'"}],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "strict": True,
            "name": "knowledge_graph",
            "schema": schema
        }
    }
)

# Check: Does it work? Do attributes get populated?
result = json.loads(response.choices[0].message.content)
print(f"Entities: {len(result['entities'])}")
print(f"Relationships: {len(result['relationships'])}")
print(f"Sample entity: {result['entities'][0]}")
```

**Evidence to collect**:
- Schema accepted: YES/NO
- Attributes populated: YES/NO
- Error messages (if any): [text]

**Success criteria**:
- Schema works with strict mode
- Attributes can contain arbitrary keys
- **If FAIL → simplify schema (remove attributes)**

---

### Step 2: Sample Extraction Test (20 min)

**What to test**:
```python
# Get sample results from recent Deep Investigation
# (Or create synthetic sample)
sample_results = [
    {"title": "JSOC Title 50 Operations", "snippet": "Joint Special Operations Command conducts..."},
    {"title": "CIA Covert Programs", "snippet": "The CIA manages Title 50 covert action authority..."},
    # ... 10 total results
]

# Test 1: Current simple extraction
from research.deep_research import SimpleDeepResearch
engine = SimpleDeepResearch()
simple_entities = await engine._extract_entities(sample_results)

# Test 2: Enhanced KG extraction
# (Create minimal enhanced_kg_extraction.py first)
from research.enhanced_kg_extraction import extract_knowledge_graph
enhanced_kg = await extract_knowledge_graph(sample_results)

# Compare
print("=== CURRENT SIMPLE EXTRACTION ===")
print(f"Entities: {simple_entities}")

print("\n=== ENHANCED KG EXTRACTION ===")
print(f"Entities: {len(enhanced_kg['entities'])}")
print(f"Relationships: {len(enhanced_kg['relationships'])}")
print(f"Sample: {enhanced_kg['entities'][0]}")
```

**Evidence to collect**:
- Simple entity count: X
- Enhanced entity count: Y
- Relationship count: Z
- Quality comparison (manual review):
  - Did enhanced find all entities from simple? YES/NO
  - Did enhanced find additional useful entities? YES/NO
  - Are relationships accurate or hallucinated? ACCURATE/MIXED/HALLUCINATED

**Success criteria**:
- Enhanced finds ≥ simple entity count
- Relationships are ≥70% accurate
- **If FAIL → enhanced extraction not worth the cost**

---

### Step 3: Performance/Cost Measurement (10 min)

**What to measure**:
```python
import time
from llm_utils import get_cost_breakdown, reset_cost_tracking

# Test 1: Current simple extraction
reset_cost_tracking()
start = time.time()
simple_entities = await engine._extract_entities(sample_results)
simple_time = time.time() - start
simple_cost = get_cost_breakdown()['total_cost']

# Test 2: Enhanced KG extraction
reset_cost_tracking()
start = time.time()
enhanced_kg = await extract_knowledge_graph(sample_results)
enhanced_time = time.time() - start
enhanced_cost = get_cost_breakdown()['total_cost']

# Report
print(f"Simple: {simple_time:.1f}s, ${simple_cost:.4f}")
print(f"Enhanced: {enhanced_time:.1f}s, ${enhanced_cost:.4f}")
print(f"Overhead: {enhanced_time/simple_time:.1f}x time, {enhanced_cost/simple_cost:.1f}x cost")
```

**Evidence to collect**:
- Simple time: X.X seconds
- Enhanced time: Y.Y seconds
- Simple cost: $X.XXXX
- Enhanced cost: $Y.YYYY
- Time multiplier: Xx
- Cost multiplier: Xx

**Success criteria**:
- Time overhead: <3x (if 5s → <15s acceptable)
- Cost overhead: <5x (if $0.001 → <$0.005 acceptable)
- **If FAIL → too expensive for optional feature**

---

### Step 4: Document Findings (10 min)

**Create**: `/home/brian/sam_gov/CREST_KG_VALIDATION_RESULTS.md`

**Format**:
```markdown
# crest_kg Integration Validation Results

## Test Environment
- Date: 2025-10-24
- Model: gpt-5-mini
- Sample size: 10 results

## Schema Compatibility
- Strict JSON mode: PASS/FAIL
- Attributes support: YES/NO
- **VERDICT**: PASS/FAIL

## Quality Comparison
| Metric | Simple | Enhanced | Winner |
|--------|--------|----------|--------|
| Entity count | X | Y | Enhanced/Simple |
| Relationships | 0 | Z | Enhanced |
| Accuracy | N/A | XX% | N/A |

Manual quality review:
- Enhanced found all simple entities: YES/NO
- Enhanced found additional useful entities: YES/NO
- Relationships accurate: XX% (PASS ≥70%)
- **VERDICT**: PASS/FAIL

## Performance/Cost
| Metric | Simple | Enhanced | Multiplier |
|--------|--------|----------|------------|
| Time | X.Xs | Y.Ys | X.Xx |
| Cost | $X.XXXX | $Y.YYYY | X.Xx |

- Time overhead acceptable (<3x): YES/NO
- Cost overhead acceptable (<5x): YES/NO
- **VERDICT**: PASS/FAIL

## FINAL DECISION
- [ ] GO - Enhanced extraction adds clear value
- [ ] NO-GO - Quality/performance insufficient
- [ ] DEFER - Revisit after optimizing prompts

**Recommendation**: [GO/NO-GO/DEFER]
**Rationale**: [Why]
```

---

## Execution Plan

### Option 1: Both Validations (2 hours)
1. Context7 validation (1 hour)
2. crest_kg validation (50 min)
3. Decision on both features (10 min)

### Option 2: Prioritize One (1 hour)
**Recommend crest_kg first** because:
- No external dependencies (pure Python)
- No Streamlit Cloud compatibility issues
- Direct integration with existing deep_research.py
- Higher confidence in success

**Then Context7** if time/interest remains

---

## Success Criteria Summary

### Context7 MCP
- [x] Startup <5s
- [x] Query <3s
- [x] Clear errors
- [x] Relevance ≥7/10
- [x] Current docs (2024-2025)
- [x] Better than or equal to Brave Search

**If ALL pass → GO (desktop-only Phase 1)**
**If ANY fail → NO-GO**

### crest_kg Integration
- [x] Schema works with strict JSON
- [x] Finds ≥ simple entity count
- [x] Relationships ≥70% accurate
- [x] Time overhead <3x
- [x] Cost overhead <5x

**If ALL pass → GO (optional feature)**
**If ANY fail → NO-GO**

---

## Next Action

**Awaiting user decision**:
- Run Context7 validation (1 hour)?
- Run crest_kg validation (50 min)?
- Both in sequence (2 hours)?

Ready to execute when approved.
