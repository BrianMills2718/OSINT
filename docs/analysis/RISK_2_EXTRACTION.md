# Risk #2: Extraction Risk - Entity Conflation & Over-Assertion

**Severity**: HIGH
**Category**: Data Quality
**Date**: 2025-11-15

---

## The Uncertainty (from V1 doc)

**Problem**: Asking LLM to:
- Recognize entities
- Map them to existing list
- Express relationships as claims

This is powerful but imperfect.

**Stated Risks**:

1. **Entity conflation**: Different people/orgs with similar names get merged
   - "J-2" might refer to slightly different offices in different contexts

2. **Over-asserted structure**: LLM creates clean claim like `J-2 → runs_program → X` even if text only said "J-2 was briefed on X"

3. **Schema drift**: Predicates sprawl and become inconsistent as you add "reported_on", "involved_in", "rumored_connection_with"

---

## Real-World Evidence

### From Mozart Investigation

**Entity Extraction Architecture** (MOZART_TECHNICAL_README.md lines 180-240):
- Uses Gemini 2.5 Flash with JSON schema
- Schema: 50+ fields (name, aliases, birth_date, roles, organizations, etc.)
- Extraction prompt is "verification-aware" (handles disputed vs verified claims)

**Observed Strength**: Schema-driven extraction is robust
- 130+ person entities created with consistent structure
- Aliases properly tracked (e.g., "John Smith", "J. Smith", "Col. Smith")

**Observed Weakness**: No visible disambiguation mechanism
- How does Mozart handle "John Smith" (common name) appearing in multiple contexts?
- Source documents don't show disambiguation warnings or confidence scores
- **Inference**: Likely relies on LLM context window to disambiguate (risky at scale)

**Over-Assertion Evidence**: Mozart's person pages use strong predicates
- "served as", "held position", "worked on" (definitive language)
- Unclear if these map to strong evidence or LLM interpretation
- Source: wikidisc.org person pages

### From Your Existing deep_research.py

**Entity Extraction** (lines 408-421, 1198-1211):
- Uses Gemini 2.5 Flash
- Extracts from accumulated results after task completion
- Stores in `entity_graph` (simple dict structure)

**Current Implementation** (from code review):
```python
# Line 408-421: Entity extraction call
entities_found = await self._extract_entities(
    combined_text=accumulated_text,
    research_question=self.research_question,
    task_description=task.query
)
```

**What's Missing**:
- No entity deduplication across tasks
- No disambiguation tracking
- No confidence scores
- Simple predicate set (relationships not strongly typed)

**Observed Behavior** (from test runs):
- Entity list sometimes includes noise: "defense contractor", "cybersecurity" (meta-terms not entities)
- Fixed via LLM-based filtering (commit 2025-11-13), but shows extraction imperfection

---

## Severity Assessment: HIGH

**Why High (not Critical)**:
- **Visible**: Unlike epistemic risk, entity problems are often obvious (duplicate names, weird claims)
- **Recoverable**: Can fix via manual review or re-extraction
- **Bounded impact**: Affects data quality but doesn't corrupt investigative thinking as deeply as methodology/epistemic risks

**But Still Serious Because**:
- **Scale amplification**: Small conflation errors multiply across investigation
- **False connections**: Over-asserted claims create phantom leads

**Concrete Examples**:

### Example 1: Entity Conflation
**Scenario**: Investigating "J-2 involvement in psychological warfare"

**What Happens**:
- Document A: "Joint Staff J-2 oversaw program X in 2005"
- Document B: "DIA J-2 Directorate reviewed program Y in 2010"
- LLM conflates into single entity "J-2"

**Graph Shows**: "J-2" connected to both Program X and Program Y
**Reality**: Two different organizations (Joint Staff vs DIA), different contexts

**Failure Mode**: You cite "J-2's history with psychological warfare programs X and Y" when it's actually two unrelated offices

### Example 2: Over-Assertion
**Text**: "The J-2 was briefed on Operation NIGHTFIRE's psychological operations component..."

**LLM Extracts**: `J-2 → oversaw → Operation NIGHTFIRE` (confidence: 0.7)

**Reality**: "Was briefed on" ≠ "oversaw"

**Failure Mode**: Graph shows strong operational connection when evidence only shows informational briefing

### Example 3: Schema Drift
**Month 1 predicates**: `held_role`, `part_of`, `worked_on`
**Month 3 predicates**: `held_role`, `part_of`, `worked_on`, `associated_with`, `mentioned_with`, `linked_to`, `connected_to`, `involved_in`

**Problem**: Last 5 predicates are semantically overlapping
- Is `associated_with` stronger or weaker than `connected_to`?
- Queries become ambiguous ("show all connections" - which predicates?)

---

## V1 Doc Proposed Mitigations

1. **Design for ambiguity, not correctness**:
   - Claims = "one plausible reading of that snippet"
   - You stay in charge of what you trust

2. **Expose "show me the snippet" everywhere**:
   - Every claim has 1-click link to underlying evidence + source

3. **Support text search alongside KG search**:
   - If you suspect conflation, bypass entity layer entirely
   - Search `evidence.snippet_text` for raw string

4. **Keep predicates small and curated in v1**:
   - Start with handful: `held_role`, `part_of`, `reported_on`, `mentioned_with`, `associated_with`
   - Add more only when you really feel the gap

---

## Additional Mitigations (from Mozart + Your Architecture)

### Mitigation A: Entity Deduplication Pipeline (Multi-Pass)

**What Mozart Does** (inferred from 130+ clean person pages):
- Likely uses entity linking/deduplication logic
- Stores aliases systematically

**V1 Implementation**:

**Pass 1**: Extract entities from each Evidence snippet (as-is)
**Pass 2**: After all extraction, run deduplication:
```python
async def _deduplicate_entities(entities: List[Dict]) -> List[Dict]:
    """Use LLM to identify duplicates and merge."""
    prompt = f"""
    Given this list of entities, identify which ones refer to the same real-world entity:
    {json.dumps(entities, indent=2)}

    For each duplicate set:
    - Choose canonical name
    - List aliases
    - Note disambiguation risk (LOW/MEDIUM/HIGH)
    """
```

**Pass 3**: Store merged entities with:
- `canonical_name`
- `aliases` (list)
- `disambiguation_risk` (LOW/MEDIUM/HIGH)
- `confidence_score` (from LLM)

**Benefit**: Catches obvious duplicates ("John Smith" vs "J. Smith") while flagging ambiguous cases

### Mitigation B: Predicate Strength Typing (Schema Discipline)

**Problem**: V1 doc says "keep predicates small" but doesn't specify HOW to keep them disciplined

**Solution**: Three-tier predicate system

| Tier | Strength | Examples | Extraction Rule |
|------|----------|----------|-----------------|
| **Strong** | High-confidence, clear action | `held_role`, `employed_by`, `created`, `oversaw` | Text uses explicit verbs |
| **Weak** | Low-confidence, associative | `mentioned_with`, `associated_with`, `related_to` | Text shows co-occurrence only |
| **Meta** | Provenance/tracking | `reported_on`, `cited_by`, `claimed_by` | Source-level relationships |

**Extraction Prompt Enhancement**:
```jinja2
When extracting claims, classify predicate strength:
- STRONG predicates: Only use when text explicitly states action/relationship
  - Good: "Smith served as Director" → held_role
  - Bad: "Smith was mentioned in connection with program" → held_role (WRONG)

- WEAK predicates: Use for co-occurrence or vague association
  - Good: "Smith appeared at event with Jones" → mentioned_with
  - Good: "Document discusses Smith and Program X" → associated_with

- META predicates: Use for source attribution
  - Good: "Report by Smith describes Program X" → reported_on
  - Good: "Smith claimed involvement in Project Y" → claimed_by
```

**UI Presentation**: Display tier in claims table
```
J-2 → oversaw [STRONG] → Operation NIGHTFIRE (1 source)
  ⚠️ Predicate strength exceeds evidence (text said "briefed on")

Person X → mentioned_with [WEAK] → Program Y (3 sources)
  ✓ Appropriate strength for co-occurrence evidence
```

**Benefit**: Prevents over-assertion, makes claim strength explicit

### Mitigation C: Disambiguation Workflow (Human-in-Loop Optional)

**For v1**: Make disambiguation review OPTIONAL but easy

**UI Element**: "Entities needing review" dashboard
- Shows entities with HIGH disambiguation risk
- Groups suspected duplicates
- Allows merge/split/confirm actions

**Example**:
```
Entity E123: "J-2"
  Disambiguation risk: HIGH
  Appears in 15 contexts:
    - 10 mentions: Joint Staff J-2 (2001-2010)
    - 5 mentions: DIA J-2 Directorate (2010-2015)

  Suggested action: Split into 2 entities
  [ Split ] [ Keep merged ] [ Review later ]
```

**Benefit**: Catches conflation without forcing review of every entity

---

## Implementation Priority for V1

### Must-Have (P0)

1. **1-click snippet links** (V1 doc #2) - Already planned
2. **Text search alongside KG** (V1 doc #3) - Already planned
3. **Curated predicate list** (V1 doc #4) - Need to define, ~1 hour

### Should-Have (P1)

4. **Predicate strength typing** (Mitigation B) - ~2-3 hours implementation
5. **Entity deduplication pipeline** (Mitigation A) - ~4-5 hours implementation
6. **Disambiguation risk tracking** (part of Mitigation A) - Included above

### Nice-to-Have (P2)

7. **Disambiguation review UI** (Mitigation C) - Phase 2 feature
8. **Alias management system** - Phase 2 feature

---

## Open Questions

1. **How often does entity conflation actually happen?**
   - Hypothesis: 10-20% of entities have some ambiguity
   - Test: Run V1 on psychological warfare example, manually count conflations

2. **Is three-tier predicate system too rigid?**
   - Risk: Forces false dichotomies (some relationships are genuinely ambiguous)
   - Test: Track how often you wish you had intermediate tier

3. **Will you actually use text search bypass?**
   - Hypothesis: KG is easier/prettier, so you'll forget text search exists
   - Test: Log usage of KG queries vs text queries in first month

4. **Does LLM deduplication work well enough?**
   - Risk: LLM might merge too aggressively OR miss obvious duplicates
   - Test: Compare LLM dedup to manual review on sample dataset

---

## Recommended V1 Approach

### Database Schema (Minimal Addition)

```sql
Entity
- id
- canonical_name
- entity_type
- disambiguation_risk  -- "low" | "medium" | "high"
- created_at

EntityAlias
- id
- entity_id
- alias_text
- source_evidence_id  -- where this alias was first seen

Claim
- id
- subject_entity_id
- predicate
- predicate_tier      -- "strong" | "weak" | "meta"  (NEW)
- object_entity_id
- evidence_id
- confidence_score    -- 0-1 from LLM
- created_at
```

### Extraction Workflow

1. **Per Evidence snippet**: Extract entities + claims (with tiers)
2. **Per ResearchRun**: Deduplicate entities, flag high-risk
3. **On Lead view**: Show disambiguation warnings
4. **Optional**: Human review of high-risk entities

### Predicate Starter List (Curated for v1)

**Strong**:
- `held_role` (Person → Office)
- `employed_by` (Person → Organization)
- `oversaw` (Office → Program)
- `created` (Person/Org → Document/Program)

**Weak**:
- `mentioned_with` (Any → Any, co-occurrence)
- `associated_with` (Any → Any, vague connection)
- `related_to` (Any → Any, generic)

**Meta**:
- `reported_on` (Person/Source → Event/Topic)
- `cited_by` (Entity → Source)
- `claimed_by` (Claim → Source)

Total: 10 predicates (room to add 5-10 more as needed)

---

## Final Assessment

**Risk Severity**: HIGH (data quality matters)

**V1 Mitigations Adequacy**: MODERATE
- Snippet links + text search: ✅ Good escape hatches
- Curated predicate list: ✅ Good discipline
- Design for ambiguity: ✅ Right philosophy
- Missing: Deduplication, predicate strength typing, disambiguation tracking

**Additional Recommendations**: IMPORTANT (P1)
- Entity deduplication pipeline (4-5 hours)
- Predicate strength typing (2-3 hours)
- Disambiguation risk scoring

**Bottom Line**: This risk is MANAGEABLE with good engineering. Unlike methodology/epistemic risks (which require fighting human biases), extraction risk can be largely solved with:
1. Multi-pass deduplication
2. Structured predicate tiers
3. Confidence/risk scores stored in data

The key is **not trusting first-pass LLM extraction** - always run cleanup/dedup passes and expose quality signals in the UI.
