# Phase 3: Entity Co-occurrence & Network Analysis

**Status**: In Progress
**Time Budget**: 2-3 hours
**Decision Gate**: GO / STOP

---

## Goal

Prove that entity co-occurrence patterns reveal investigative insights beyond what single-entity queries provide.

**Core Question**: "Do entities that frequently appear together reveal relationships, organizational structures, or investigative leads that aren't obvious from entity-alone queries?"

---

## Prerequisites

**Phase 2 completed**: ✅
- Cross-report entity linking validated
- 168 canonical entities in database
- 244 evidence snippets
- CLI query tool working

---

## What We're Building

### 1. Co-occurrence Analysis

Identify which entities appear together in the same evidence snippets:

**Example patterns we're looking for**:
- "Igor Egorov" + "FSB" + "Vympel" appear together → Organizational relationship
- "MH17" + "Buk" + "53rd Brigade" appear together → Operational relationship
- "GRU" + "Bonanza Media" + "disinformation" appear together → Campaign structure

### 2. Extended Database Schema

Add co-occurrence tracking:

```sql
-- Co-occurrence table: which entities appear in same evidence snippets
CREATE TABLE entity_cooccurrence (
    entity_id_1 TEXT,
    entity_id_2 TEXT,
    cooccurrence_count INTEGER,
    evidence_ids TEXT,  -- JSON array of evidence_id's where they co-occur
    PRIMARY KEY (entity_id_1, entity_id_2)
);

-- Bridge entities: entities that connect different topics
-- (appear with many different other entities)
CREATE VIEW bridge_entities AS
SELECT
    entity_id,
    canonical_name,
    COUNT(DISTINCT partner_entity_id) as connection_count
FROM (
    SELECT entity_id_1 as entity_id, entity_id_2 as partner_entity_id FROM entity_cooccurrence
    UNION ALL
    SELECT entity_id_2 as entity_id, entity_id_1 as partner_entity_id FROM entity_cooccurrence
)
GROUP BY entity_id
ORDER BY connection_count DESC;
```

### 3. Enhanced CLI Queries

Add new query types:

```bash
# Show entities that co-occur with a target entity
python query.py --cooccur "Igor Egorov"
# Output: FSB (5 times), Vympel (4 times), Department V (3 times)...

# Show "bridge entities" (entities connecting many others)
python query.py --bridges
# Output: MH17 (connects 15 entities), Bellingcat (connects 12 entities)...

# Show entity network for a specific entity
python query.py --network "MH17" --depth 2
# Output:
#   MH17 connects to:
#     - Buk missile (6 co-occurrences)
#       - Buk connects to: 53rd Brigade, Russia, Donetsk...
#     - Bellingcat (8 co-occurrences)
#       - Bellingcat connects to: Eliot Higgins, Twitter...
```

---

## Implementation Plan

### Step 1: Build Co-occurrence Analysis (45 min)

**File**: `poc/analyze_cooccurrence.py`

**Process**:
1. Read all evidence snippets from database
2. For each snippet, get all entities mentioned
3. Create pairs of entities that co-occur in same snippet
4. Count co-occurrence frequency
5. Store in new `entity_cooccurrence` table

**Algorithm**:
```python
for evidence_snippet in all_evidence:
    entities = get_entities_mentioned_in(evidence_snippet)

    # Create all pairs
    for entity1, entity2 in combinations(entities, 2):
        cooccurrence[(entity1, entity2)] += 1
        evidence_list[(entity1, entity2)].append(evidence_id)

# Store in database
for (e1, e2), count in cooccurrence.items():
    db.insert(entity_id_1=e1, entity_id_2=e2,
              cooccurrence_count=count,
              evidence_ids=json.dumps(evidence_list[(e1, e2)]))
```

---

### Step 2: Extend CLI with Co-occurrence Queries (30 min)

**File**: Update `poc/query.py`

**New commands**:

```python
# --cooccur: Show entities that appear with target entity
def query_cooccurrence(conn, entity_name):
    # Find target entity
    # Query entity_cooccurrence table
    # Show ranked list by co-occurrence count

# --bridges: Show entities with most connections
def query_bridge_entities(conn):
    # Use bridge_entities view
    # Show entities with highest connection_count

# --network: Show network around entity
def query_network(conn, entity_name, depth=1):
    # Recursive query up to depth N
    # Show entity → connected entities → their connections
```

---

### Step 3: Test Co-occurrence Insights (30 min)

**Test queries to validate value**:

```bash
# Test 1: MH17 network
python query.py --cooccur "MH17"
# Expected: Buk, 53rd Brigade, Bellingcat, etc.

# Test 2: Igor Egorov network
python query.py --cooccur "Igor Egorov"
# Expected: FSB, Vympel, Department V, Elbrus, etc.

# Test 3: Bridge entities
python query.py --bridges
# Expected: MH17, Bellingcat (appear across many contexts)

# Test 4: 53rd Brigade network
python query.py --network "53rd Brigade"
# Expected: Buk, MH17, Kursk, convoy...
```

---

### Step 4: Document Insights (30 min)

**File**: `poc/phase3_results.md`

**Questions to answer**:
1. Do co-occurrence patterns reveal organizational structures?
   - Example: FSB → Department V → Vympel → Egorov hierarchy

2. Do bridge entities surface investigative priorities?
   - Example: MH17 connects most entities → central to investigation

3. Does network view reveal non-obvious connections?
   - Example: Entity X connects topic A to topic B in unexpected way

---

## Success Criteria (Decision Gate)

### ✅ GO to Full PoC if ALL true:

1. **Co-occurrence patterns are meaningful**
   - [ ] At least 3 co-occurrence patterns reveal real-world relationships
   - [ ] Examples: FSB+Vympel, MH17+Buk+53rd, GRU+disinformation

2. **Bridge entities surface investigative insights**
   - [ ] Bridge entities match investigative importance (MH17, Bellingcat should rank high)
   - [ ] Low-bridge entities make sense (peripheral entities have fewer connections)

3. **Network view adds value beyond single-entity queries**
   - [ ] Can answer "How are X and Y connected?" questions
   - [ ] Network reveals paths between entities not obvious from reading

### ❌ STOP if ANY true:

1. **Co-occurrence patterns are noise**
   - Most co-occurrences are random/meaningless
   - No clear organizational or operational structures emerge

2. **Bridge entities don't match investigative importance**
   - High-bridge entities are trivial (e.g., "Russia", "Ukraine")
   - Important entities (MH17, Egorov) don't show up as bridges

3. **Network view is just "entities mentioned together"**
   - Doesn't reveal anything beyond what simple co-location already shows
   - No value over Phase 2 single-entity queries

---

## Expected Co-occurrence Patterns

Based on report content, we expect to find:

### Pattern 1: FSB Organizational Hierarchy
```
FSB (organization) co-occurs with:
  - Vympel (unit)
  - Department V (unit)
  - Igor Egorov (person)
  - Spetsnaz (unit)
```
**Insight**: Reveals organizational structure FSB → units → operatives

---

### Pattern 2: MH17 Investigation Network
```
MH17 (event) co-occurs with:
  - Buk missile (concept)
  - 53rd Brigade (unit)
  - Bellingcat (organization)
  - Joint Investigation Team (organization)
  - Donetsk/Luhansk (locations)
```
**Insight**: Central event connects evidence, investigators, perpetrators, locations

---

### Pattern 3: GRU Disinformation Campaign
```
GRU (organization) co-occurs with:
  - Bonanza Media (organization)
  - disinformation (concept)
  - Yana Yerlashova (person)
  - Twitter (organization)
```
**Insight**: Reveals disinformation campaign structure

---

### Pattern 4: 53rd Brigade Operational Link
```
53rd Brigade (unit) co-occurs with:
  - Buk missile (concept)
  - Kursk (location)
  - convoy (concept)
  - MH17 (event)
  - Russia (location)
```
**Insight**: Links military unit to weapon, origin, operation, and event

---

## Metrics to Track

1. **Total co-occurrence pairs**: How many unique entity pairs co-occur?
2. **Average co-occurrence count**: How often do pairs appear together?
3. **Bridge entity distribution**: How many entities are "hubs" vs "periphery"?
4. **Network diameter**: Maximum distance between connected entities

**Expected ranges** (estimated):
- Total pairs: 200-500
- Avg co-occurrence: 1-3 times
- Bridge entities (>5 connections): 10-20
- Network diameter: 3-5 hops

---

## Visualization (Optional)

If time permits, create simple network graph:

**File**: `poc/visualize_network.py`

**Tool**: NetworkX + Matplotlib

**Graph**:
- Nodes = entities (sized by report_count)
- Edges = co-occurrence (weighted by count)
- Layout = Force-directed (entities cluster by co-occurrence)

**Example**:
```python
import networkx as nx
import matplotlib.pyplot as plt

G = nx.Graph()
# Add nodes: entities
# Add edges: co-occurrences
nx.draw(G, with_labels=True, node_size=1000)
plt.savefig('poc/entity_network.png')
```

**This is OPTIONAL** - only if time allows and it adds clear value.

---

## Time Budget

| Task | Time |
|------|------|
| Build co-occurrence analysis | 45 min |
| Extend CLI with new queries | 30 min |
| Test co-occurrence insights | 30 min |
| Document findings | 30 min |
| **(Optional) Visualization** | *30 min* |
| **Total** | **~2.5 hours** |

If exceeds 4 hours → STOP, something is wrong.

---

## Output Artifacts

**Code**:
- `poc/analyze_cooccurrence.py` - Co-occurrence analysis script
- `poc/query.py` (updated) - Extended CLI with new queries

**Data**:
- `poc/entities.db` (updated) - Added entity_cooccurrence table
- `poc/cooccurrence_stats.json` - Analysis statistics

**Documentation**:
- `poc/phase3_results.md` - Co-occurrence findings and decision gate

**Optional**:
- `poc/visualize_network.py` - Network graph script
- `poc/entity_network.png` - Visual network diagram

---

## Next Steps

**If GO → Full PoC (Stage 4)**:
- Build multi-lead support (separate investigation notebooks)
- Add claim extraction (structured assertions with evidence)
- Build basic web UI
- Test on larger corpus (10+ reports)

**If STOP**:
- Phase 1-2 validated: Entity extraction + cross-report linking works
- Phase 3 failed: Co-occurrence doesn't add enough value
- Recommendation: Deploy Phase 2 system, skip co-occurrence features

---

## Key Question for Phase 3

**"Does seeing which entities appear together reveal insights that seeing entities alone does not?"**

This is the validation question. If co-occurrence is just "noise" or doesn't reveal patterns, we stop here. If it surfaces organizational structures, operational relationships, or investigative leads, we proceed to full PoC.
