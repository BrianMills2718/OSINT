# Risk #7: Unknown Unknowns - What Actually Feels Useful?

**Severity**: META (Can't assess until V1 used)
**Category**: Product-Market Fit / Usability
**Date**: 2025-11-15

---

## The Problem (V1 Doc)

> "The main thing we can't fully nail in advance is: Which interactions will actually make you go 'oh wow, this feels like a real investigative assistant'?"

**You'll only discover this by**:
- Wiring up v1
- Using it on a real messy topic (psychological warfare example)
- Noticing:
  - Which parts feel magical
  - Which parts feel like friction or fakery
  - What queries you wish you could express

**V1 Doc Recommendation**:
> "Treat v1 as an instrumented notebook for your own methodology, not a finished product. Log everything, keep it legible, and assume you'll refactor around your actual habits once you've lived with it a bit."

---

## Why This Is Different from Other Risks

**Risks 1-6**: Technical/methodological problems with known shape
- Methodology risk: "Reports wash out outliers" (we know what we're looking for)
- Epistemic risk: "Graphs feel authoritative" (we know the failure mode)
- Extraction risk: "Entity conflation" (we know how to test for it)

**Risk 7**: Product design uncertainty
- **Don't know**: Which features you'll actually use
- **Don't know**: Which workflows feel natural vs forced
- **Don't know**: What the killer interaction pattern is

**This is NORMAL for v1 products** - you're exploring problem space, not just solving known problems

---

## Real-World Analogues

### From Mozart Investigation

**What They Built**: Wikipedia-style person biographies + Wikibase knowledge graph

**What They Probably DIDN'T Predict** (speculation based on architecture):
1. **Verification framework became central**
   - Early architecture probably just extracted claims
   - Realized disputed claims needed explicit handling
   - Added "verified vs disputed vs rumored" tagging

2. **MediaWiki auto-sync mattered more than manual editing**
   - WikidiscPersonSync extension syncs to Wikibase automatically
   - Suggests manual graph editing was too tedious
   - Automation became killer feature

3. **SPARQL queries less used than expected?**
   - Full Wikibase stack deployed (WDQS, QuickStatements)
   - No evidence in docs of heavy query usage
   - Maybe browsing person pages is more natural than graph queries

**Inference**: They built infrastructure (Wikibase), discovered bottleneck (manual sync), added automation (extension). V1 → V2 evolution.

### From Your deep_research.py Evolution

**Looking at Git History** (CLAUDE.md TEMPORARY section, lines 50-315):

**Original Design** (implicit from current state):
- Single-pass relevance filtering
- All results stored (no per-result filtering)
- No retry logic

**Discovered Problems** (from committed fixes):
1. **Context pollution** (commit 0eb3ff3):
   - LLM said "2 relevant, 8 junk" → system stored all 10
   - Added `relevant_indices` to filter per-result

2. **No accumulation across retries** (commit 8443da5):
   - Retry overwrote previous results (data loss)
   - Added `accumulated_results` field

3. **Entity extraction noise** (commit 2025-11-13):
   - Extracted "defense contractor", "cybersecurity" (meta-terms)
   - Added LLM-based entity filtering

4. **ClearanceJobs missing data** (fix 2025-11-11):
   - 100% results filtered out (no snippets)
   - Added field normalization + clearance extraction

**Pattern**: Built core system → used it → discovered friction → fixed incrementally

**This is EXACTLY what V1 doc recommends** for unknown unknowns

---

## What Can't Be Known in Advance

### Interaction Patterns

**Hypothesis A**: "I'll mostly use graph queries to find connections"
**Alternative**: You end up using evidence full-text search 80% of the time (graph too noisy)

**Hypothesis B**: "I'll create lots of small Leads (one per thread)"
**Alternative**: You end up with 2-3 giant Leads (psychological warfare, corruption, UFOs) because context-switching is annoying

**Hypothesis C**: "I'll use search patterns heavily (Person×Topic, Office×Capability)"
**Alternative**: You end up typing free-form queries (patterns too rigid)

**Can't know which until you try**

### Feature Usage

**What V1 Includes** (from design doc):
- Leads (investigation threads)
- ResearchRuns (deep search operations)
- Evidence browser (snippet-level browsing)
- Entity pages (people/orgs/programs/concepts)
- Claims table (structured relationships)
- Search patterns (reusable query templates)
- Saved views (filtered evidence feeds)

**Which Will You Actually Use?**
- Maybe entity pages are killer feature (organize by person/org)
- Maybe evidence browser is 90% of usage (you mostly read snippets)
- Maybe claims table is too abstract (prefer full-text search)
- maybe search patterns never get used (too much friction to define)

**Can't predict without usage data**

### Workflow Bottlenecks

**Predicted Bottlenecks** (from other risks):
- Cost (too expensive per run)
- Latency (too slow for quick lookups)
- Coverage (not enough sources)
- Entity conflation (dirty data)

**Possible Surprise Bottlenecks**:
- **Lead management**: Creating/organizing Leads is tedious (need better tagging/hierarchy)
- **Evidence overload**: 500 snippets per Lead is unmanageable (need better filtering/ranking)
- **Graph navigation**: Clicking through entity relationships is disorienting (need better visualization)
- **Query formulation**: Deciding what to search for is cognitively hard (need better prompts/suggestions)

**Can't know which is the REAL bottleneck until you hit it**

---

## V1 Doc Proposed Approach (Correct)

**"Treat v1 as an instrumented notebook"**

**What This Means in Practice**:

1. **Log everything**:
   - Every search query
   - Every filter operation
   - Every click (which pages visited, which entities explored)
   - Time spent per activity

2. **Keep it legible**:
   - Execution logs in readable format (jsonl)
   - Database queries produce human-readable output
   - UI shows diagnostic info (not just polished results)

3. **Assume you'll refactor**:
   - Don't over-optimize v1 (will change anyway)
   - Use simple implementations (SQLite not distributed database)
   - Avoid premature abstraction

---

## Recommended V1 Instrumentation

### Logging Infrastructure

**What to Log** (automatically):

```python
# User actions
action_log:
  timestamp
  action_type  # "create_lead", "run_research", "view_entity", "filter_evidence", "create_claim"
  lead_id
  duration_seconds
  metadata  # action-specific details

# Research run diagnostics
research_run_log:
  run_id
  query_text
  depth_preset
  cost
  duration
  sources_found
  entities_extracted
  user_rating  # "useful" | "somewhat" | "not_useful" (optional feedback)

# Navigation patterns
navigation_log:
  session_id
  page_sequence  # ["lead_123", "entity_456", "evidence_789", ...]
  timestamps
```

**Weekly Self-Review Prompts**:
- Which Leads did I spend most time on?
- Which features did I use most? (evidence browser, entity pages, claims table, search patterns)
- Which research runs did I rate "not useful"? (why?)
- How often did I:
  - Click through to raw snippets? (epistemic discipline check)
  - Use full-text search vs. graph queries?
  - Create new search patterns vs. free-form queries?

### A/B Testing Your Own Usage

**Variant A (Week 1-2)**: Use graph-first workflow
- Start every investigation from entity pages
- Navigate via claims table
- Force yourself to use search patterns

**Variant B (Week 3-4)**: Use evidence-first workflow
- Start with full-text search
- Browse evidence table
- Only look at entities when snippets reference them

**Measure**:
- Which variant felt faster?
- Which variant found more leads?
- Which variant was more enjoyable?

**Result**: Discover your natural workflow (design v2 around it)

---

## Open Questions (By Design)

These SHOULD be open questions in v1:

1. **Is the Lead abstraction useful or friction?**
   - Useful: Organizes investigations, prevents mixing contexts
   - Friction: Too much admin overhead, want simpler "notebook" view

2. **Do search patterns actually save time?**
   - Useful: Encode expert tactics, reusable across investigations
   - Friction: Defining patterns is tedious, free-form queries faster

3. **Is the knowledge graph valuable or distracting?**
   - Valuable: Surfacing unexpected connections, pivot point discovery
   - Distracting: Noisy data, prefer simpler evidence browsing

4. **What's the right granularity for evidence?**
   - Too fine: Snippet-level (500 snippets = overwhelming)
   - Too coarse: Source-level (miss important details within documents)
   - Just right: ??? (discover through use)

5. **How much human review is tolerable?**
   - V1 includes optional claim review, entity deduplication review
   - Will you actually do this? Or is full automation required?

---

## Recommended V1 Posture

**Design Principles for Unknown Unknowns**:

1. **Simple defaults, optional power features**:
   - Default: Evidence browser + full-text search (simple, always works)
   - Optional: Graph queries, search patterns, saved views (test if useful)

2. **Escape hatches everywhere**:
   - Don't force graph usage (can always drop to text search)
   - Don't force Lead structure (can use single "scratch" Lead for unstructured work)
   - Don't force claim structure (can just store evidence and ignore graph)

3. **Rapid iteration over polish**:
   - Ugly UI acceptable (focus on functionality)
   - No premature optimization (SQLite fine, don't need Postgres until scale problems)
   - No feature locks (if search patterns unused, delete them in v2)

4. **Explicit experimentation**:
   - Run 5-10 investigations in v1
   - After each, write post-mortem: "What worked? What didn't? What's missing?"
   - Refactor based on patterns across investigations (not single experience)

---

## Success Criteria (How to Know If V1 Worked)

**Good Outcomes** (v1 → v2):
- "I used evidence browser constantly, claims table rarely" → Simplify v2 around evidence browsing
- "Search patterns saved me hours on person×topic queries" → Expand pattern library in v2
- "Entity conflation was annoying but not blocking" → Keep current fix, don't over-engineer
- "Lead structure helped organize month-long investigations" → Keep Leads, add better tagging

**Bad Outcomes** (v1 → rethink):
- "I never opened v1 after first week" → Fundamental workflow mismatch
- "I kept falling back to manual Google searches" → Not saving enough time
- "Reports felt authoritative, I cited weak claims" → Epistemic risk not mitigated
- "I only used v1 for quick lookups, not deep investigations" → Solving wrong problem

**The Point**: V1 is a **probe**, not a product. Success = learning what to build in v2.

---

## Final Assessment

**Risk Severity**: META (not a failure risk, a discovery process)

**Mitigation Approach**: **INSTRUMENTATION + ITERATION**

**V1 Doc Guidance**: ✅ Correct approach
- Log everything
- Keep legible
- Assume refactoring

**Additional Recommendations**:

1. **Commit to 10 investigations in v1** (minimum viable learning)
   - Don't judge after 1 investigation (might be atypical)
   - Don't use indefinitely without learning (defeats "v1 as probe" purpose)

2. **Write post-mortems** (after each investigation)
   - What worked well?
   - What was frustrating?
   - What's missing?
   - Would I use v1 again for this type of investigation?

3. **Weekly metrics review**:
   - Which features used most?
   - Which Leads got most activity?
   - Cost per investigation (sustainable?)
   - Time saved vs. manual research (positive ROI?)

4. **Explicit v1 → v2 cutover** (after 10 investigations OR 3 months)
   - Analyze logs + post-mortems
   - Identify top 3 friction points
   - Design v2 around actual usage patterns (not predicted)

**Bottom Line**: This isn't a risk to "mitigate" - it's a learning opportunity to **embrace**. The V1 doc is correct: Build instrumented prototype, use it seriously, learn from real usage, refactor. This is how good investigative tools get built (iterative refinement with domain expert in the loop).
