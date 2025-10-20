# Knowledge Base Options for SigInt Platform

**Date**: 2025-10-20
**Goal**: Store investigative research findings in queryable, structured format
**Question**: Wiki (Wikibase) vs Alternatives?

---

## What You Want

Based on your needs:

1. **Store findings from investigations**:
   - Government contracts discovered
   - Surveillance programs identified
   - Entities extracted (people, organizations, programs)
   - Connections discovered (X works for Y, Y runs program Z)

2. **Query across investigations**:
   - "Show me all programs related to NSA"
   - "What contracts did Palantir win?"
   - "Who are the whistleblowers in our database?"
   - "Find all FISA-related entities"

3. **Build knowledge over time**:
   - Monday: Find NSA contract
   - Tuesday: Find Prism program
   - Wednesday: Discover NSA runs Prism
   - System: Auto-link them together

4. **Team collaboration**:
   - Multiple journalists researching
   - Shared knowledge base
   - Annotation and notes
   - Track provenance (where did we learn this?)

---

## Options Analysis

### Option 1: PostgreSQL (Relational Database)

**What it is**: Traditional SQL database with tables/foreign keys

**Schema example**:
```sql
CREATE TABLE entities (
    id SERIAL PRIMARY KEY,
    name TEXT,
    type TEXT,  -- 'person', 'organization', 'program', 'document'
    description TEXT,
    created_at TIMESTAMP
);

CREATE TABLE relationships (
    id SERIAL PRIMARY KEY,
    source_entity_id INTEGER REFERENCES entities(id),
    target_entity_id INTEGER REFERENCES entities(id),
    relationship_type TEXT,  -- 'works_for', 'operates', 'mentioned_in'
    confidence FLOAT,
    source_document TEXT
);

CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    title TEXT,
    url TEXT,
    source TEXT,  -- 'SAM.gov', 'FBI Vault', etc.
    found_date TIMESTAMP,
    monitor_name TEXT
);
```

**Queries**:
```sql
-- Find all NSA programs
SELECT e.name, r.relationship_type
FROM entities e
JOIN relationships r ON e.id = r.target_entity_id
JOIN entities source ON source.id = r.source_entity_id
WHERE source.name = 'NSA' AND r.relationship_type = 'operates';

-- Find Palantir contracts
SELECT d.*
FROM documents d
JOIN entity_mentions em ON d.id = em.document_id
JOIN entities e ON em.entity_id = e.id
WHERE e.name = 'Palantir';
```

**Pros**:
- ✅ You already have PostgreSQL setup
- ✅ Simple to implement (just add tables)
- ✅ Fast queries
- ✅ Easy to backup/export
- ✅ No new infrastructure

**Cons**:
- ❌ Schema changes are painful (add new relationship type = alter table)
- ❌ Graph queries awkward (lots of JOINs)
- ❌ No built-in visualization
- ❌ Manual entity resolution ("NSA" vs "National Security Agency")

**Effort**: 1-2 weeks
**Cost**: $0 (already have PostgreSQL)

---

### Option 2: Wikibase (Knowledge Graph)

**What it is**: Same system your friend uses - full semantic wiki

**Example entities**:
```
Q1: National Security Agency (NSA)
  - instance of: Government agency (Q5)
  - country: United States (Q10)
  - inception: 1952
  - operates: Prism (Q15), XKEYSCORE (Q22)

Q15: Prism
  - instance of: Surveillance program (Q7)
  - operated by: NSA (Q1)
  - inception: 2007
  - mentioned in: [Document D101], [Document D205]

Q30: Edward Snowden
  - instance of: Person (Q4)
  - role: Whistleblower (Q8)
  - employer: NSA (Q1), Booz Allen Hamilton (Q42)
  - disclosed: Prism (Q15), XKEYSCORE (Q22)
```

**Queries (SPARQL)**:
```sparql
# Find all programs operated by NSA
SELECT ?program ?programLabel WHERE {
  ?program wdt:P12 wd:Q1 .  # operated by NSA
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}

# Find all whistleblowers who worked at NSA
SELECT ?person ?personLabel WHERE {
  ?person wdt:P1 wd:Q4 .     # instance of Person
  ?person wdt:P3 wd:Q8 .     # role: Whistleblower
  ?person wdt:P4 wd:Q1 .     # employer: NSA
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}

# Find connection path between two entities
SELECT ?entity ?entityLabel ?relation WHERE {
  wd:Q1 wdt:P12* ?entity .   # NSA → any path → entity
  ?entity wdt:P20 wd:Q30 .   # entity → about → Snowden
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
```

**Pros**:
- ✅ Built for knowledge graphs (entities + relationships)
- ✅ SPARQL is powerful for graph queries
- ✅ Automatic entity pages (Q1, Q2, Q3...)
- ✅ Web UI for browsing/editing
- ✅ Proven technology (Wikimedia uses it)
- ✅ Auto-links entities
- ✅ Version history (who added what, when)
- ✅ Collaborative (multiple users)

**Cons**:
- ❌ Complex setup (13+ Docker containers)
- ❌ Steep learning curve (SPARQL, Wikibase API)
- ❌ Resource-heavy (needs 4GB+ RAM)
- ❌ Overkill for single user
- ❌ Maintenance burden

**Effort**: 4-6 weeks (setup + learning)
**Cost**: $20-40/month (VPS hosting)

---

### Option 3: Neo4j (Graph Database)

**What it is**: Purpose-built graph database (like Wikibase but simpler)

**Example data**:
```cypher
// Create entities
CREATE (nsa:Organization {name: "NSA", type: "Government Agency", inception: 1952})
CREATE (prism:Program {name: "Prism", inception: 2007})
CREATE (snowden:Person {name: "Edward Snowden", role: "Whistleblower"})

// Create relationships
CREATE (nsa)-[:OPERATES]->(prism)
CREATE (snowden)-[:DISCLOSED]->(prism)
CREATE (snowden)-[:WORKED_AT]->(nsa)
```

**Queries (Cypher)**:
```cypher
// Find all NSA programs
MATCH (nsa:Organization {name: "NSA"})-[:OPERATES]->(program)
RETURN program.name

// Find whistleblowers who worked at NSA
MATCH (person:Person {role: "Whistleblower"})-[:WORKED_AT]->(nsa:Organization {name: "NSA"})
RETURN person.name

// Find connection path
MATCH path = (nsa:Organization {name: "NSA"})-[*]-(snowden:Person {name: "Edward Snowden"})
RETURN path
```

**Pros**:
- ✅ Built for graphs (like Wikibase)
- ✅ Simpler than Wikibase (1 Docker container)
- ✅ Cypher is easier than SPARQL
- ✅ Great visualization (Neo4j Browser)
- ✅ Fast graph queries
- ✅ Good Python library (neo4j driver)

**Cons**:
- ❌ No web UI for editing (only viewing)
- ❌ No collaborative features
- ❌ Requires learning Cypher
- ❌ Paid for production (Community Edition free)

**Effort**: 2-3 weeks
**Cost**: $0 (Community Edition) or $50+/month (Enterprise)

---

### Option 4: Obsidian + Dataview (Markdown Wiki)

**What it is**: Local markdown files with graph view

**Example files**:
```markdown
# NSA.md
---
type: organization
inception: 1952
country: United States
---

The National Security Agency operates several surveillance programs:
- [[Prism]]
- [[XKEYSCORE]]

## Related People
- [[Edward Snowden]] (whistleblower)
```

```markdown
# Prism.md
---
type: program
inception: 2007
operated_by: [[NSA]]
---

Prism is a surveillance program operated by the [[NSA]].

Disclosed by [[Edward Snowden]] in 2013.
```

**Queries (Dataview)**:
```dataview
# All programs operated by NSA
LIST
FROM "entities"
WHERE type = "program" AND operated_by = [[NSA]]

# Whistleblowers who worked at NSA
TABLE role, worked_at
FROM "entities"
WHERE type = "person" AND role = "whistleblower" AND worked_at = [[NSA]]
```

**Pros**:
- ✅ Super simple (just markdown files)
- ✅ No infrastructure (local files)
- ✅ Beautiful graph view
- ✅ Easy to edit (any text editor)
- ✅ Git-friendly (commit history)
- ✅ Free and offline

**Cons**:
- ❌ Local only (no team collaboration without sync)
- ❌ No API (hard to auto-populate from code)
- ❌ Manual linking (no auto-entity-resolution)
- ❌ Limited querying vs SQL/SPARQL

**Effort**: 1 week
**Cost**: $0

---

### Option 5: Hybrid - PostgreSQL + Simple Graph Layer

**What it is**: Use PostgreSQL for storage, build simple graph query layer on top

**Schema**:
```sql
-- Entities table
CREATE TABLE entities (
    id SERIAL PRIMARY KEY,
    type TEXT,  -- 'person', 'organization', 'program', 'document'
    name TEXT UNIQUE,
    aliases JSONB,  -- ["NSA", "National Security Agency"]
    properties JSONB,  -- Flexible key-value
    created_at TIMESTAMP
);

-- Relationships table
CREATE TABLE relationships (
    id SERIAL PRIMARY KEY,
    source_id INTEGER REFERENCES entities(id),
    target_id INTEGER REFERENCES entities(id),
    rel_type TEXT,  -- 'works_for', 'operates', 'disclosed'
    properties JSONB,  -- Metadata about relationship
    source_doc TEXT,  -- Provenance
    confidence FLOAT,  -- 0-1
    created_at TIMESTAMP
);

-- Documents table (from monitors)
CREATE TABLE investigation_documents (
    id SERIAL PRIMARY KEY,
    title TEXT,
    url TEXT,
    source TEXT,
    content JSONB,
    monitor_name TEXT,
    found_date TIMESTAMP
);

-- Entity mentions (link documents to entities)
CREATE TABLE entity_mentions (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES investigation_documents(id),
    entity_id INTEGER REFERENCES entities(id),
    mention_count INTEGER,
    context TEXT
);
```

**Python query layer**:
```python
class KnowledgeGraph:
    """Simple graph query layer over PostgreSQL."""

    def find_entity(self, name: str) -> Entity:
        """Find entity by name or alias."""
        # Handles "NSA" vs "National Security Agency"

    def get_relationships(self, entity: Entity, rel_type: str = None):
        """Get all relationships for entity."""

    def find_path(self, source: Entity, target: Entity) -> List[Entity]:
        """Find connection path between entities."""
        # Uses recursive CTE in PostgreSQL

    def search_entities(self, query: str) -> List[Entity]:
        """Full-text search across entities."""

    def add_entity(self, name: str, type: str, properties: Dict):
        """Add new entity."""

    def link_entities(self, source: str, target: str, rel_type: str):
        """Create relationship."""
```

**Usage**:
```python
# After BabyAGI investigation discovers entities
entities = ["NSA", "Prism program", "Edward Snowden"]

kg = KnowledgeGraph()

# Add entities
kg.add_entity("NSA", type="organization", properties={"inception": 1952})
kg.add_entity("Prism", type="program", properties={"inception": 2007})
kg.add_entity("Edward Snowden", type="person", properties={"role": "whistleblower"})

# Link them
kg.link_entities("NSA", "Prism", rel_type="operates")
kg.link_entities("Edward Snowden", "Prism", rel_type="disclosed")
kg.link_entities("Edward Snowden", "NSA", rel_type="worked_at")

# Query
nsa = kg.find_entity("NSA")
programs = kg.get_relationships(nsa, rel_type="operates")
# Returns: [Prism, XKEYSCORE, ...]

# Find connections
path = kg.find_path("NSA", "Edward Snowden")
# Returns: [NSA] → operates → [Prism] → disclosed_by → [Edward Snowden]
```

**Pros**:
- ✅ Uses existing PostgreSQL
- ✅ Simple to implement (just tables + Python layer)
- ✅ Flexible (JSONB for properties)
- ✅ Fast (PostgreSQL recursive CTEs for graph queries)
- ✅ No new infrastructure
- ✅ Can add web UI later

**Cons**:
- ❌ Build it yourself (no existing UI)
- ❌ Manual entity resolution
- ❌ No visualization (until you build it)

**Effort**: 2-3 weeks
**Cost**: $0 (uses existing PostgreSQL)

---

## Recommendation for Your Use Case

### Phase 1 (Now): PostgreSQL + Simple Graph Layer

**Why**:
1. **You already have PostgreSQL** - no new infrastructure
2. **Simplest to integrate** with existing monitors
3. **Fastest to implement** - 2-3 weeks vs 6 weeks for Wikibase
4. **Flexible** - JSONB lets you evolve schema easily
5. **Good enough** for single user / small team

**What you get**:
- Entity storage (people, orgs, programs, documents)
- Relationship tracking (X works for Y, Y operates Z)
- Graph queries (find connections, paths)
- Provenance (track where info came from)
- Auto-populated from BabyAGI investigations

**Implementation**:
```python
# monitoring/adaptive_boolean_monitor.py

async def run(self):
    """Execute monitor with knowledge graph integration."""

    # Run adaptive search
    results = await self.execute_search(self.config.keywords)

    # Extract entities using BabyAGI
    entities = await self.extract_entities(results)

    # Store in knowledge graph
    kg = KnowledgeGraph()
    for entity in entities:
        kg.add_entity(entity['name'], entity['type'], entity['properties'])

    # Link entities based on co-occurrence
    for doc in results:
        mentioned = [e for e in entities if e['name'] in doc['title'] or e['name'] in doc.get('description', '')]
        # Auto-link entities mentioned together
        for e1, e2 in combinations(mentioned, 2):
            kg.link_entities(e1['name'], e2['name'], rel_type="co-mentioned", source_doc=doc['url'])

    # Send alert with knowledge graph insights
    await self.send_alert(results, entities=entities)
```

---

### Phase 2 (Later): Add Visualization

**Options**:
1. **Simple web UI** (Streamlit):
   ```python
   # Show entity graph
   import networkx as nx
   import plotly

   G = kg.as_networkx_graph()
   # Render interactive graph
   ```

2. **Export to existing tools**:
   - Export to Gephi (graph visualization)
   - Export to Obsidian (markdown wiki)
   - Export to Neo4j (if you want better visualization)

---

### Phase 3 (Maybe): Upgrade to Wikibase

**When to upgrade**:
- Team grows to 3+ people
- Need collaborative editing
- Want public wiki interface
- Have budget for hosting ($40/month)
- Have time for complex setup (4-6 weeks)

**Migration path**:
```python
# Export PostgreSQL graph to Wikibase
for entity in kg.all_entities():
    wikibase_client.create_item(
        label=entity.name,
        description=entity.properties.get('description'),
        properties=entity.properties
    )

for rel in kg.all_relationships():
    wikibase_client.add_claim(
        item_id=rel.source_id,
        property_id=rel.rel_type,
        target_id=rel.target_id
    )
```

---

## Implementation Plan (PostgreSQL + Graph Layer)

### Week 1: Database Schema
- Create entities, relationships, entity_mentions tables
- Create indexes for fast queries
- Test with sample data

### Week 2: Knowledge Graph Python Layer
- Build `KnowledgeGraph` class
- Entity CRUD operations
- Relationship operations
- Graph queries (find path, get connected entities)

### Week 3: Integration with Monitors
- Auto-extract entities from search results
- Auto-populate knowledge graph
- Link entities based on co-occurrence
- Track provenance (which monitor found what)

### Week 4: Queries & Reporting
- Add knowledge graph insights to email alerts
- Build simple query interface
- Export capabilities (JSON, CSV, Markdown)

**Total**: 4 weeks part-time

---

## Comparison Table

| Feature | PostgreSQL + Graph | Wikibase | Neo4j | Obsidian |
|---------|-------------------|----------|-------|----------|
| **Effort** | 2-3 weeks | 4-6 weeks | 2-3 weeks | 1 week |
| **Cost** | $0 | $40/month | $0-50/month | $0 |
| **Graph queries** | Good (CTEs) | Excellent (SPARQL) | Excellent (Cypher) | Limited |
| **Visualization** | DIY | Built-in | Excellent | Beautiful |
| **Collaboration** | Possible | Excellent | Limited | Sync needed |
| **Learning curve** | Low | High | Medium | Very low |
| **Integration** | Easy | Medium | Easy | Hard |
| **Scalability** | Good | Excellent | Excellent | Poor |

---

## Final Recommendation

**Start with PostgreSQL + Graph Layer**:

1. **Weeks 1-4**: Build Mozart adaptive search + BabyAGI
2. **Weeks 5-8**: Add PostgreSQL knowledge graph
   - Entities, relationships, provenance
   - Auto-populated from investigations
   - Simple Python query layer

3. **Weeks 9-10**: Add visualization
   - Streamlit graph viewer
   - Entity detail pages
   - Relationship explorer

4. **Later**: Consider upgrade to Wikibase if:
   - Team grows
   - Need collaboration
   - Want public wiki

**Why this order**:
- Get search improvements working first (immediate value)
- Knowledge graph builds on search results (natural flow)
- Can migrate to Wikibase later if needed (not locked in)
- PostgreSQL keeps it simple for now

**Total effort**: 8-10 weeks for search + knowledge graph

**Total cost**: $0 (uses existing PostgreSQL)

---

## Sample Knowledge Graph Queries

Once implemented, you could query:

```python
kg = KnowledgeGraph()

# "Show me everything we know about NSA"
nsa = kg.find_entity("NSA")
programs = kg.get_relationships(nsa, rel_type="operates")
people = kg.get_relationships(nsa, rel_type="employed")
documents = kg.get_documents_mentioning(nsa)

# "Find all surveillance programs"
programs = kg.search_entities(type="program", properties={"domain": "surveillance"})

# "How is Palantir connected to NSA?"
path = kg.find_path("Palantir", "NSA")
# Returns: [Palantir] → won_contract → [Contract #123] → awarded_by → [NSA]

# "What have we learned this week?"
recent = kg.recent_entities(days=7)

# "Show network around FISA"
network = kg.get_network("FISA", depth=2)
# Returns all entities within 2 hops of FISA
```

---

**Last Updated**: 2025-10-20
**Recommendation**: PostgreSQL + Graph Layer (Weeks 5-8, after search improvements)
**Migration Path**: Can upgrade to Wikibase later if team/budget grows
