# Review: Proposed V1 Spec Updates

**Date**: 2025-11-15
**Reviewer Role**: Objective Project Manager
**Context**: Another LLM suggested updates to v1_integrating_sigints_wiki_202511151134.md
**Assessment Framework**: Risk vs. Value, Alignment with Goals, Implementation Cost

---

## Executive Assessment

**Overall Recommendation**: ✅ **ACCEPT most updates with modifications**

**Rationale**:
- **Alignment**: 85% aligned with your existing architecture and risk mitigation priorities
- **Complexity**: Low (mostly clarifications + 3 small schema fields)
- **Risk**: Medium (introduces automation assumptions that may not match real workflow)

**Key Concerns**:
1. **Automation-first philosophy** may be premature (conflicts with Risk #7 - unknown unknowns)
2. **Timeline encoding** adds complexity without proven need
3. **Lead filters JSON** good idea but needs careful design

**Recommended Approach**: Accept conceptual improvements, defer automation until v1 usage proves it's needed

---

## Detailed Analysis by Section

### 1. Overview Updates

#### Proposal: Pluggable deep-research layer description

**Original**:
> "Uses a deep-research engine to gather sources"

**Proposed**:
> "Uses a pluggable deep-research layer (either an existing library or a simple Brave/Tavily + LLM summarizer adapter)"

**Assessment**: ✅ **ACCEPT**

**Why**:
- Aligns with Risk #5 mitigation (don't lock into external frameworks)
- Matches your existing deep_research.py architecture (already pluggable)
- Low complexity (just clarification)

**No concerns**

---

#### Proposal: Lead = notebook framing + timeline mention

**Proposed**:
> "Organizes everything into per-topic Leads (your notebooks / case files), each with its own graph, search history, and timeline. Automatically estimates time spans for evidence and orders each Lead on a timeline."

**Assessment**: ⚠️ **ACCEPT with caution**

**Why Accept**:
- "Lead = notebook" framing is clear and helpful
- Per-Lead graph/search history makes sense

**Concerns**:
1. **Timeline commitment**: "Automatically estimates time spans" promises feature before validating need
   - Risk #7 (unknown unknowns) says you won't know what interactions feel useful until you try
   - Timeline might be noise (dates in text are often vague, contradictory, or irrelevant)

2. **Implementation cost**: Timeline encoding adds 3 fields to Evidence schema + extraction logic + UI
   - Estimated: 6-8 hours implementation
   - Benefit: Unproven (might use it 10% of the time)

**Recommendation**:
- Accept "Lead = notebook" framing
- Make timeline **optional Phase 2 feature** (not core v1)
- Defer until you've done 5-10 investigations and noticed "I wish I could sort by date"

---

### 2. Automation-First Goal

#### Proposal: Add explicit automation goal

**Proposed**:
> "Automation-first: The system should be able to attach evidence to leads automatically, run pattern-based expansions, and build timelines/summaries without any mandatory manual review steps."

**Assessment**: ❌ **REJECT for v1** (defer to v2)

**Critical Concerns**:

1. **Conflicts with Risk #7 (unknown unknowns)**:
   - V1 doc correctly says: "Treat v1 as instrumented notebook, assume you'll refactor"
   - Adding automation commitments BEFORE knowing your workflow is premature optimization
   - You might discover manual attachment is better (gives you control + awareness)

2. **Conflicts with Risk #1 (methodology) mitigation**:
   - Automation needs good filters (what should auto-attach?)
   - Bad filters = noise pollution (everything attaches to everything)
   - Good filters require knowing your investigative patterns (which you don't yet)

3. **Implementation complexity**:
   - Auto-attachment requires:
     - Filter matching logic (which Evidence matches which Lead?)
     - Conflict resolution (Evidence matches multiple Leads - attach to all? none? prompt?)
     - Performance optimization (re-run filters on every new Evidence = expensive)
   - Estimated: 12-16 hours for basic version
   - Risk: Builds wrong thing (automation you don't want)

4. **Real-world evidence from your system**:
   - Your deep_research.py doesn't auto-attach results to Leads (you run targeted queries per Lead)
   - This suggests manual scoping works fine
   - No evidence of "I wish results auto-organized" pain point

**Counter-Argument** (why someone might propose this):
- Investigative journalism involves lots of documents (auto-org seems helpful)
- Some evidence IS clearly relevant to multiple Leads (Howard Hunt appears in Bay of Pigs + Watergate)

**Rebuttal**:
- True, but you don't know HOW you'll want to organize until you try
- Maybe you want manual control (see everything, decide what's relevant)
- Maybe you want tags instead of auto-attachment (Evidence can have tags, you search by tag)
- Maybe you want both (auto-suggest but manual confirm)

**Recommendation**:
- **Defer automation to v2** (after 10 investigations reveal actual workflow)
- For v1: Manual Lead scoping (run research FOR a specific Lead, results attach to that Lead only)
- Optional: Add "suggest related Leads" feature (LLM looks at Evidence, suggests which Leads it might belong to, you click to attach)

---

### 3. Data Model Updates

#### 3.1 Evidence Timeline Fields

**Proposed**:
```text
Evidence
+ timecode_start      # "2023", "20230711", "202307111215"
+ time_span_code      # "202307111215-202308?", "2023-2024", NULL
+ timecode_source     # "explicit_in_text" | "llm_estimate" | "document_date"
```

**Assessment**: ⚠️ **ACCEPT as optional** (Phase 1.5 or Phase 2)

**Why it's interesting**:
- Chronological sorting IS useful for investigations (narrative flow, program timelines)
- Compact encoding is clever (handles fuzzy dates like "summer 2003", "during Gulf War")

**Concerns**:

1. **Complexity cost**:
   - Extraction: LLM must parse dates from text (not trivial - "early 2000s" vs "2003" vs "Sept 11 attacks")
   - Storage: 3 extra fields per Evidence row
   - UI: Timeline visualization (x-axis = time, how to handle fuzzy dates?)
   - Estimated: 8-10 hours for basic implementation

2. **Data quality**:
   - Many Evidence snippets won't have dates ("The J-2 oversees psychological operations" - timeless statement)
   - LLM date estimation is error-prone (might infer "2003" from context when text is actually from 2015)
   - Creates illusion of chronological precision when dates are often fuzzy/wrong

3. **Risk #6 (epistemic) amplification**:
   - Timeline visualization feels authoritative ("here's what happened when")
   - Reality: Dates are LLM guesses + document metadata (not necessarily when events occurred)
   - Example: News article from 2010 describes program from 1985 - which date matters?

4. **Unknown value** (Risk #7):
   - You haven't done investigations yet - don't know if timeline view is useful or noise
   - Might discover: "I always sort by source domain, never by date"
   - Might discover: "Timeline is killer feature for program history investigations"

**Recommendation**:
- **Defer to Phase 1.5** (after 3-5 investigations)
- For v1: Store `fetched_at` (when you got the evidence) + manual tags (e.g., "1980s", "Gulf War era")
- After 5 investigations, if you're constantly thinking "I wish I could sort by era", add timeline fields
- If you rarely care about chronology, skip forever

---

#### 3.2 Lead Filters JSON

**Proposed**:
```text
Lead
+ lead_filters_json   # JSON with entities, keywords, domains, time ranges
```

**Assessment**: ✅ **ACCEPT concept, careful design needed**

**Why Accept**:
- Aligns with "Lead = notebook with rules" mental model
- Useful even without full automation (defines what BELONGS in a Lead)
- Low storage cost (1 field)

**Design Concerns**:

1. **What goes in the filter?**
   - Entities? (all Evidence mentioning "Operation NIGHTFIRE" → attach to NIGHTFIRE lead)
   - Keywords? (all Evidence with "psychological warfare" → attach to psywar lead)
   - Domains? (all .mil sources → attach to official-docs lead)
   - Boolean combos? ("J-2" AND "psyops" → attach to J2-psyops lead)

2. **Conflict resolution**:
   - Evidence matches multiple Leads (Howard Hunt in both Bay of Pigs + Watergate)
   - Attach to both? Attach to neither? Prompt user?

3. **Filter evolution**:
   - Lead starts with seed entities ["J-2", "psychological warfare"]
   - You discover new entity "Operation NIGHTFIRE"
   - Do you manually add to filter? Auto-add discovered entities? Never update?

**Recommended Design** (minimal v1):

```json
{
  "lead_filters": {
    "required_entities": ["E123"],  // entity IDs
    "required_keywords": ["psychological warfare", "J-2"],
    "allowed_domains": [".mil", ".gov"],
    "excluded_keywords": ["budget", "procurement"],  // negative filters
    "mode": "manual_review"  // "auto_attach" | "manual_review" | "suggest_only"
  }
}
```

**Usage in v1**:
- Mode = "manual_review" (don't auto-attach, just highlight matching Evidence in UI)
- "Unattached Evidence" view shows all Evidence that matches a Lead filter but isn't attached
- You click "Attach to Lead X" to confirm

**Automation in v2** (after workflow validated):
- Mode = "auto_attach" (if confident in filters)
- Mode = "suggest_only" (show suggestions in Lead dashboard)

**Implementation**: 2-3 hours (schema + basic matching logic)

---

#### 3.3 LeadRelation Table

**Proposed**:
```text
LeadRelation
- from_lead_id
- to_lead_id
- relation_type   # "related_to", "person_profile", "background_context"
- note
```

**Assessment**: ✅ **ACCEPT** (cheap, useful, no complexity)

**Why Accept**:
- Addresses real need (Bay of Pigs lead relates to Howard Hunt lead without full merge)
- Schema cost: negligible (simple join table)
- Implementation: 1 hour (table + basic UI)
- No forced usage (can ignore in v1, use heavily in v2)

**Use Case**:
- Lead A: "Bay of Pigs invasion"
- Lead B: "Howard Hunt career profile"
- Relation: Lead A → "person_profile" → Lead B ("Hunt played role, see his profile for full context")

**UI**: On Lead A page, show "Related Leads: Howard Hunt (person profile)"

**No concerns** - this is pure upside with minimal cost

---

### 4. Deep-Research Engine Abstraction

**Proposed**:
```text
DeepResearchClient interface:
  1. Adapter for GPT-Researcher/DeerFlow
  2. Builtin "direct search" (Brave + LLM summarizer)
```

**Assessment**: ✅ **STRONGLY ACCEPT**

**Why Strongly Accept**:

1. **Aligns perfectly with Risk #5 mitigation**:
   - Don't lock into external frameworks
   - Adapter pattern = easy replacement
   - Direct search = escape hatch if framework breaks

2. **Aligns with your existing architecture**:
   - deep_research.py is already the "direct search" path (Brave/Tavily + LLM)
   - You don't need GPT-Researcher adapter at all (just use what you have)

3. **Low complexity**:
   - Interface: 1 hour to define + document
   - Direct search: 0 hours (already built = deep_research.py)
   - Framework adapter: 0 hours (skip for v1)

**Recommended Implementation**:

```python
class DeepResearchClient(ABC):
    @abstractmethod
    async def run_research(self, query: str, params: Dict) -> ResearchResult:
        """Returns report_md + citations."""
        pass

class DirectSearchClient(DeepResearchClient):
    """Uses your existing deep_research.py"""
    async def run_research(self, query, params):
        # Call deep_research.py with query
        # Return results in ResearchResult format
        pass

# Optional (defer to v2):
class GPTResearcherAdapter(DeepResearchClient):
    """Wraps gpt-researcher library"""
    pass
```

**For v1**: Only implement DirectSearchClient (wraps your deep_research.py)

**No concerns** - this is exactly right

---

### 5. Workflow Updates (Automation-First)

**Proposed**:
- Leads have attached SearchPatterns
- Scheduler runs patterns automatically
- "automation-first" instead of button-driven

**Assessment**: ❌ **REJECT automation, ACCEPT patterns**

**What to Accept**:
- SearchPattern concept (reusable query templates)
- Lead can have multiple patterns attached
- Patterns can be instantiated into concrete queries

**What to Reject**:
- Automatic scheduling (defer to v2)
- "No UI buttons needed" philosophy

**Why Reject Automation**:

1. **Risk #7 (unknown unknowns)**:
   - You don't know if you'll WANT automated pattern running
   - Might discover: "I prefer manual trigger (gives me control)"
   - Might discover: "I want semi-auto (system suggests, I approve)"

2. **Automation failure modes**:
   - Pattern expands to 50 queries → launches 50 ResearchRuns → $50 cost surprise
   - Pattern finds 0 results → wastes time, no signal
   - Pattern finds 500 results → noise pollution

3. **Your existing behavior**:
   - deep_research.py requires manual invocation (you run specific queries)
   - No evidence you're frustrated by manual triggering
   - Suggests: Manual control is fine, maybe even preferred

**Recommended v1 Approach**:

**Manual Pattern Execution** (with easy buttons):

```
Lead Page: "J-2 & Psychological Warfare"

Search Patterns (3 attached):
  [ Run ] Person×Topic (5 entities × 1 topic = 5 queries)
  [ Run ] Office×Capability (2 offices × 3 capabilities = 6 queries)
  [ Run ] Program×Budget (8 programs = 8 queries)

[ Run All Patterns ] (confirmation: "Will launch 19 queries, cost ~$15-20")
```

**Benefits**:
- You control when patterns run (no surprise costs)
- You see what will happen (19 queries listed)
- Easy to trigger (1 click) but requires intent

**v2 Enhancement** (after discovering you want automation):
- Add "Auto-run on schedule" checkbox per pattern
- Add budget limits ("stop after $20 or 100 results")

---

### 6. Boolean Hard-Constraint Search

**Proposed**:
- For hard boolean searches, bypass deep-research engine
- Construct exact query from entities + pattern
- Call Brave/Tavily directly
- Treat as ResearchRun with "direct_search" engine type

**Assessment**: ✅ **STRONGLY ACCEPT**

**Why Strongly Accept**:

1. **Perfectly addresses Risk #1 (methodology)**:
   - V1 doc says: "For critical boolean tactics, don't rely on deep-research engine"
   - This codifies that as first-class path

2. **Aligns with your investigative style**:
   - You care about `(J-2) AND (psyops) AND site:.mil` precision
   - Deep-research engines soften boolean logic ("find info about J-2 and psyops")
   - Direct Brave call preserves your tactics

3. **Already implemented**:
   - deep_research.py can call Brave directly (via integrations)
   - Just needs UI trigger: "Run exact query" vs "Run deep research"

**Recommended Implementation**:

```
Lead Page: "J-2 & Psychological Warfare"

[ New Research Run ]
  Mode: ⚪ Deep Research (task decomposition, multi-source)
        ⚫ Direct Search (exact query, single source)

  Query: (J-2) AND (psychological operations) AND site:.mil
  Source: [ Brave Search ▼ ]

  [ Run Search ]
```

**Implementation**: 2-3 hours (UI + routing logic)

**No concerns** - this is essential for your use case

---

### 7. Cost/Latency Framing

**Proposed**:
- Change "explode in cost" → "explode in latency and LLM attention usage"
- Frame presets as "managing speed and cognitive load" not just money

**Assessment**: ✅ **ACCEPT**

**Why Accept**:
- Matches your "quality over cost" stance (from deep_research.py design)
- More honest about real concern (slow feedback kills flow)
- Better aligns with Risk #4 assessment (latency > cost for your use case)

**Minor Suggestion**:
- Keep cost mentioned (still matters, just not primary concern)
- Reframe as: "Latency (primary concern) + cost (secondary)"

**Implementation**: 30 minutes (text updates only)

**No concerns**

---

### 8. Wiki/Mozart Connection (Phase 2)

**Proposed**:
- Add Phase 2 bullet: "Auto-wiki generation from matured Leads"
- Mozart-style pipeline: verification-aware extraction → role-aware prose → publish
- Keeps Lead (working notebook) and wiki page (polished export) separate

**Assessment**: ✅ **ACCEPT**

**Why Accept**:
- Answers your earlier question: "isn't this covered by wiki pages?"
- Clarifies relationship: Lead = investigation, wiki page = publication
- Phase 2 framing = no v1 commitment

**Use Case**:
- Lead: "Bay of Pigs invasion" (200 Evidence snippets, 50 entities, 100 claims - messy)
- Wiki page: "Bay of Pigs invasion" (10-page polished narrative with citations - clean)

**Implementation**: Phase 2 only (0 hours for v1)

**No concerns**

---

## Summary: What to Accept vs. Reject

### ✅ ACCEPT (High Value, Low Risk)

1. **Pluggable deep-research layer** (matches your architecture)
2. **Lead = notebook framing** (clear mental model)
3. **DeepResearchClient abstraction** (Risk #5 mitigation)
4. **Boolean hard-search path** (Risk #1 mitigation, essential for your workflow)
5. **LeadRelation table** (cheap, useful, no downside)
6. **Cost/latency reframing** (matches your priorities)
7. **Wiki/Mozart Phase 2 note** (clarifies relationship)
8. **Lead filters JSON concept** (useful with careful design)

### ⚠️ ACCEPT WITH MODIFICATIONS

9. **Lead filters JSON implementation**:
   - Accept schema field
   - Implement as "manual review" mode (highlight matches, don't auto-attach)
   - Defer full automation to v2

10. **Timeline fields**:
    - Accept concept
    - Defer to Phase 1.5 (after 5 investigations prove need)
    - Don't commit in v1 spec

### ❌ REJECT (Premature or Misaligned)

11. **Automation-first goal**:
    - Conflicts with Risk #7 (unknown unknowns)
    - Premature optimization
    - Defer to v2 after workflow validated

12. **Automatic pattern scheduling**:
    - Unknown if you'll want this
    - Keep manual triggering for v1
    - Easy upgrade path to automation later

13. **Timeline commitment in Overview**:
    - "Automatically estimates time spans" overpromises
    - Make timeline optional feature, not core promise

---

## Revised Recommendation

### Accept These Updates to V1 Spec:

**High-Priority** (implement in v1):
1. DeepResearchClient abstraction + direct search path
2. Boolean hard-search as first-class path
3. LeadRelation table
4. Lead filters JSON (manual review mode)
5. Cost/latency reframing
6. "Lead = notebook" language throughout

**Medium-Priority** (evaluate after 3-5 investigations):
7. Timeline fields (defer decision)
8. Automation features (defer to v2)

**Low-Priority** (Phase 2):
9. Wiki/Mozart connection note

### Estimated Implementation Cost

**If accepting all high-priority items**:
- DeepResearchClient interface: 1 hour
- Boolean search UI: 2-3 hours
- LeadRelation table: 1 hour
- Lead filters (manual mode): 2-3 hours
- Text updates: 1 hour
- **Total**: ~7-9 hours

**If also adding deferred items** (NOT recommended for v1):
- Timeline fields + extraction: 8-10 hours
- Automation logic: 12-16 hours
- **Total**: 27-35 hours (too much for uncertain benefit)

---

## Key Concerns Summary

### 1. Automation Premature (CRITICAL CONCERN)

**Problem**: Proposing automation before validating workflow

**Risk**:
- Build wrong automation (you don't want it)
- Adds complexity (12-16 hours) for uncertain benefit
- Conflicts with "v1 = instrumented probe" philosophy

**Evidence**:
- Your deep_research.py requires manual invocation (works fine)
- Risk #7 says: Discover workflow through use, then automate
- No pain point evidence (you haven't complained about manual triggering)

**Recommendation**: Manual with easy buttons for v1, automation for v2

### 2. Timeline Complexity (MEDIUM CONCERN)

**Problem**: Adding 3 fields + extraction logic + UI before proving need

**Risk**:
- 8-10 hours implementation
- Data quality issues (LLM date guessing)
- Epistemic risk amplification (timeline feels authoritative)
- Might never use it (unknown unknowns)

**Evidence**:
- No evidence you're frustrated by lack of chronological sorting
- Your current system sorts by source/relevance (works fine)

**Recommendation**: Defer to Phase 1.5, revisit after 5 investigations

### 3. Filter Design Needs Care (MINOR CONCERN)

**Problem**: lead_filters_json is good idea but needs careful design

**Risk**:
- Bad filters = noise (everything matches)
- Conflict resolution unclear (Evidence matches multiple Leads)
- Evolution strategy unclear (how do filters update?)

**Evidence**:
- Common problem in investigative tools (tagging/categorization is hard)

**Recommendation**: Start with manual review mode, learn what works, then automate

---

## Final Recommendation

**ACCEPT**: 60% of proposals (conceptual improvements, low-risk additions)

**MODIFY**: 25% of proposals (good ideas but defer automation/timeline)

**REJECT**: 15% of proposals (automation-first goal conflicts with v1 philosophy)

**Overall**: Proposed updates are THOUGHTFUL and mostly aligned, but need moderation:
- Keep simplicity (don't add automation before validating workflow)
- Keep v1 as probe (don't commit to features before discovering needs)
- Keep implementation lean (7-9 hours for high-value items, not 27-35 hours for speculation)

**Action**: Update V1 spec with accepted items, explicitly mark timeline/automation as "Phase 1.5 / Phase 2 pending usage validation"
