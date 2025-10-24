# crest_kg Integration Plan

**Date**: 2025-10-24
**Decision**: Adapt crest_kg to use gpt-5-mini (via llm_utils.py) instead of Google Gemini
**Status**: Planning - uncertainties to resolve before implementation

---

## Goals

1. **Better entity extraction**: Get entities WITH relationships and attributes (not just names)
2. **Single LLM vendor**: Use OpenAI gpt-5-mini for everything (no Google Gemini)
3. **Optional feature**: Enable via flag, don't slow down every investigation
4. **Reuse existing code**: Leverage crest_kg's proven extraction logic + llm_utils.py infrastructure

---

## Architecture Decision

**APPROVED**: Use gpt-5-mini via llm_utils.py (NOT Google Gemini)

**Why**:
- ✅ Single vendor (OpenAI) - simpler billing, fewer API keys
- ✅ Reuse llm_utils.py infrastructure (already handles gpt-5-mini + litellm)
- ✅ Consistent cost tracking across all LLM calls
- ✅ No Gemini API key needed (removed hardcoded key from crest_kg/kg_from_text2.py)
- ✅ Same JSON schema pattern already working in deep_research.py

**Implementation approach**:
```python
# Replace Google Gemini genai.Client calls
# OLD (crest_kg original):
from google import genai
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
response = client.models.generate_content(...)

# NEW (adapted):
from llm_utils import acompletion
response = await acompletion(
    model="gpt-5-mini",
    messages=[{"role": "user", "content": prompt}],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "strict": True,
            "name": "knowledge_graph",
            "schema": {...}
        }
    }
)
```

---

## Integration Options (Revisited)

**Option B** (Recommended): **Optional Deep KG Feature**

### What We'll Build
1. Keep current simple entity extraction (deep_research.py `_extract_entities()`)
2. Add new `enhanced_kg_extraction.py` module using adapted crest_kg logic
3. Add `enable_knowledge_graph: bool` parameter to Deep Investigation
4. Run enhanced KG extraction ONLY if enabled
5. Save as downloadable artifacts (JSON + optional PyVis HTML)

### File Structure
```
research/
  deep_research.py               # Existing (simple entity extraction)
  enhanced_kg_extraction.py      # NEW (crest_kg logic adapted to gpt-5-mini)

crest_kg/
  kg_from_text2.py              # Reference implementation (keep for comparison)
  pyvis2.py                     # Visualization code (reuse)
```

### Integration Points
```python
# In deep_research.py after research completes:
if enable_knowledge_graph:
    from research.enhanced_kg_extraction import extract_knowledge_graph
    kg = await extract_knowledge_graph(all_results)
    # Save to artifacts/kg_output.json
    # Generate visualization if requested
```

---

## Current Status

**Completed**:
- [x] Fixed hardcoded Gemini API key in crest_kg/kg_from_text2.py (now uses .env)
- [x] Researched llm_utils.py gpt-5-mini integration patterns
- [x] Confirmed litellm.responses() + JSON schema working for gpt-5-mini
- [x] Fixed Deep Investigation source attribution ("Unknown" → actual source names)

**Next**:
- [ ] Resolve remaining uncertainties (see below)
- [ ] Create enhanced_kg_extraction.py module
- [ ] Test extraction on sample Deep Investigation results
- [ ] Measure performance/cost vs current simple extraction
- [ ] Add optional flag to Deep Investigation UI

---

## Remaining Uncertainties

### 1. **Schema Compatibility**
**Question**: Does crest_kg's Wikibase schema work with gpt-5-mini JSON structured output?

**crest_kg schema** (complex):
```json
{
  "entities": [
    {
      "id": "unique_id",
      "name": "Entity Name",
      "type": "person|organization|location|event|concept",
      "attributes": {"key1": "value1", "key2": "value2"}
    }
  ],
  "relationships": [
    {
      "source": "entity_id",
      "target": "entity_id",
      "type": "relationship_type",
      "attributes": {"key1": "value1"}
    }
  ]
}
```

**Risk**: OpenAI strict JSON schema may reject nested arbitrary key-value pairs in `attributes`
**Test needed**: Try schema with gpt-5-mini, see if attributes work or need flattening

---

### 2. **Performance Impact**
**Question**: How much slower/expensive is enhanced KG vs current simple extraction?

**Current simple extraction**:
- Model: gpt-5-mini
- Input: 10 result snippets (~500 tokens)
- Output: List of 3-10 entity names (~50 tokens)
- Time: ~5 seconds
- Cost: ~$0.001

**Enhanced KG extraction** (estimated):
- Model: gpt-5-mini
- Input: 10 result snippets (~500 tokens)
- Output: Full KG with entities + relationships + attributes (~500 tokens)
- Time: ~10-15 seconds? (2-3x slower)
- Cost: ~$0.003? (3x more expensive due to larger output)

**For 9-task investigation**:
- Current: 9 × $0.001 = $0.009
- Enhanced: 9 × $0.003 = $0.027 (~3x increase)

**Acceptable?**: If optional (disabled by default), probably yes. User opts in to better quality.

**Test needed**: Run extraction on sample results, measure actual time/cost

---

### 3. **Quality vs Current System**
**Question**: Does enhanced KG actually extract BETTER entities than current simple prompt?

**Current prompt** (deep_research.py line 173):
```
Extract key entities (people, organizations, programs, operations) from these search results.

Return a JSON list of entity names (3-10 entities). Focus on named entities that could be researched further.
```

**Enhanced prompt** (crest_kg):
```
Analyze the following document and create a knowledge graph in JSON format.
Extract entities (people, organizations, locations, events, concepts) and their relationships.

For each entity:
- Give it a unique ID (preferably short and descriptive)
- Identify its type (person, organization, location, event, concept)
- Record any attributes mentioned (like roles, dates, descriptors)

For each relationship:
- Identify the source entity ID
- Identify the target entity ID
- Describe the relationship type (e.g., "works_for", "located_in", "participated_in")
```

**Hypothesis**: Enhanced prompt gets relationships + attributes (more data), but may also hallucinate more or miss simple entities

**Test needed**: Compare entity extraction quality on same results:
- Do both find the same core entities?
- Does enhanced find additional useful relationships?
- Are relationships accurate or inferred/hallucinated?

---

### 4. **Visualization Value**
**Question**: Will users actually USE PyVis graph visualizations?

**crest_kg produces**:
- 141KB HTML file with interactive graph
- Node colors by entity type
- Clickable nodes with tooltips
- Relationship edges with labels

**Alternative**: Just show JSON with entities/relationships in text format

**User perspective**:
- Journalist workflow: Search → read articles → write story
- Do they want to EXPLORE graph visually?
- Or just want LIST of entities to research further?

**Decision needed**: Build visualization feature or just JSON export?

**Recommendation**: Start with JSON only, add visualization later if users request it

---

### 5. **When to Run Extraction**
**Question**: Extract entities per-task (9 times) or once at end (1 time on all results)?

**Option A**: Per-task extraction (like current system)
- Extracts entities from each task's 10-20 results
- 9 tasks × 10s = 90 seconds overhead
- Can use entities for follow-up task generation
- More expensive (9 LLM calls)

**Option B**: End-of-investigation extraction
- Extracts entities from ALL results at once (100+ results)
- 1 task × 30s = 30 seconds overhead
- Cannot influence follow-up tasks
- Cheaper (1 LLM call)
- Better global entity relationships

**Recommendation**: Option B (end-of-investigation) if optional feature. Don't slow down every task.

---

### 6. **Storage & Retrieval**
**Question**: Save KG to file, database, or just return in memory?

**Options**:
- **File**: Save JSON to `data/investigations/{investigation_id}/knowledge_graph.json`
- **Database**: Store in PostgreSQL (Week 5-8 roadmap)
- **Memory only**: Return with investigation results, don't persist

**For Phase 1 validation**: File storage is simplest
**For Phase 3 (if valuable)**: PostgreSQL with Wikibase schema

---

## Recommendation: Phased Validation

### Phase 1: Quick Test (2-3 hours) - DO THIS FIRST
1. Create `enhanced_kg_extraction.py` with gpt-5-mini + crest_kg schema
2. Test schema compatibility with strict JSON mode
3. Run extraction on sample Deep Investigation results (10-20 items)
4. Compare with current simple extraction:
   - Entity count and quality
   - Relationship accuracy
   - Time and cost
5. **DECISION POINT**: Is it better? If NO → stop. If YES → Phase 2.

### Phase 2: Optional Integration (4-6 hours) - ONLY IF Phase 1 succeeds
1. Add `enable_knowledge_graph` parameter to Deep Investigation
2. Run enhanced extraction at end of investigation (Option B)
3. Save JSON to `data/investigations/{id}/kg.json`
4. Add "Download Knowledge Graph" button in UI
5. **DECISION POINT**: Do users enable it? If NO → remove feature.

### Phase 3: PostgreSQL Storage (Week 5-8) - ONLY IF Phase 2 used
1. Design Wikibase-compatible PostgreSQL schema
2. Auto-populate from investigations
3. Enable graph queries for intelligent follow-ups
4. Team collaboration features

---

## Next Actions

Before proceeding to implementation, need to:

1. **Schema test**: Try crest_kg schema with gpt-5-mini strict JSON mode (10 min)
2. **Decide on visualization**: Build PyVis graphs or just JSON? (5 min)
3. **Decide on timing**: Per-task or end-of-investigation extraction? (5 min)

**After resolving these 3 uncertainties** → proceed to Phase 1 implementation
