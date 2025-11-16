# Automation-First V1 Spec Revision

**Date**: 2025-11-15
**User Directive**: "This is automation-first code. I don't want any human review we don't need."
**Timeline**: User doesn't want timelines
**Task**: Revise recommendations to match automation-first philosophy

---

## Corrected Assessment

I was WRONG in my previous review. I incorrectly prioritized "unknown unknowns" risk over your explicit design goal: **automation-first**.

### What I Got Wrong

**My Error**: Recommended manual review + defer automation because "you don't know your workflow yet"

**Reality**:
- You already HAVE a working automated system (deep_research.py)
- It runs end-to-end without human intervention
- Your CLAUDE.md explicitly says: "User configures parameters once → Run research → Walk away → Get comprehensive results"
- No mid-run feedback required, no manual intervention, all decisions automated via LLM

**This is NOT a prototype to explore workflows** - this is production automation infrastructure.

---

## Revised Recommendations: ACCEPT Automation Proposals

### ✅ ACCEPT: Automation-First Goal

**Proposed**:
> "The system should attach evidence to leads automatically, run pattern-based expansions, and build timelines/summaries without any mandatory manual review steps."

**New Assessment**: ✅ **STRONGLY ACCEPT**

**Why**:
1. **Matches your existing architecture**: deep_research.py already does this
2. **Matches your design philosophy**: CLAUDE.md line 47: "User configures once → walks away → gets results"
3. **Matches your risk mitigation strategy**: "No hardcoded heuristics. Full LLM intelligence."

**Implementation**: Already mostly built (deep_research.py pattern)

---

### ✅ ACCEPT: Lead Auto-Attachment via Filters

**Proposed**:
```text
Lead
+ lead_filters_json   # Entities, keywords, domains, time ranges
```

**New Assessment**: ✅ **ACCEPT for auto-attachment**

**How It Should Work** (automation-first):

```python
# After any ResearchRun completes:
for evidence in new_evidence:
    matching_leads = []

    for lead in all_leads:
        filters = lead.lead_filters_json
        if evidence_matches_filters(evidence, filters):
            matching_leads.append(lead)

    # AUTO-ATTACH (no human review)
    for lead in matching_leads:
        lead.attach_evidence(evidence.id)

    # Log for transparency (not approval)
    log_attachment(evidence.id, matching_leads)
```

**Conflict Resolution** (Evidence matches multiple Leads):
- **Attach to ALL matching Leads** (evidence can belong to multiple investigations)
- Example: Howard Hunt evidence → attaches to both "Bay of Pigs" Lead AND "Watergate" Lead
- No human decision needed

**Filter Evolution**:
- LLM updates filters as it discovers new entities
- Example: Lead starts with ["J-2", "psychological warfare"]
- After finding "Operation NIGHTFIRE" repeatedly, LLM adds it to filter
- Prompt: "Given this Lead's current filters and newly discovered entities, should any be added to auto-capture future relevant evidence?"

**Implementation**: 4-6 hours (auto-attachment logic + LLM filter evolution)

---

### ✅ ACCEPT: Automatic Pattern Scheduling

**Proposed**:
- SearchPatterns run automatically (scheduler or trigger-based)
- No manual "Run pattern X" buttons needed

**New Assessment**: ✅ **ACCEPT with smart triggers**

**How It Should Work**:

```python
# Trigger 1: New entity discovered
@event_handler("entity_extracted")
async def on_new_entity(entity, lead):
    patterns = lead.get_patterns_for_entity_type(entity.type)
    for pattern in patterns:
        if pattern.should_trigger(entity, lead):
            await run_pattern_expansion(pattern, entity, lead)

# Trigger 2: Lead stagnation (no new results in N runs)
@scheduled("daily")
async def check_stale_leads():
    for lead in active_leads:
        if lead.last_new_results_at < 7.days.ago:
            # Try broader search
            await run_exploration_mode(lead)

# Trigger 3: Evidence threshold reached
@event_handler("evidence_attached")
async def on_evidence_threshold(lead):
    if lead.evidence_count % 50 == 0:  # Every 50 evidence pieces
        # Re-extract entities, update filters
        await refresh_lead_entities(lead)
```

**Budget Controls** (to prevent runaway costs):
```yaml
lead_config:
  max_auto_runs_per_day: 10
  max_cost_per_day: 20.00
  stop_on_no_new_results: 3  # Stop after 3 consecutive runs with 0 new findings
```

**Implementation**: 8-10 hours (trigger logic + budget controls)

---

### ❌ REJECT: Timelines (Per User Request)

**User said**: "I don't want timelines"

**Assessment**: ✅ **Correctly rejected by user**

**Why user is right**:
- Adds complexity (3 fields, extraction logic, UI)
- Date extraction is error-prone
- Not needed for your investigative style (you care about connections, not chronology)

**Alternative** (if chronology matters later):
- Just search evidence.snippet_text for date patterns ("2003", "Gulf War", "post-9/11")
- No schema changes needed
- LLM can synthesize timeline on-demand from evidence if you ask

**Implementation**: 0 hours (skip entirely)

---

## Better Alternative to Timelines: Context Tags

If you occasionally care about time context but don't want full timeline infrastructure:

### Lightweight Context Tagging (LLM-Driven)

**Concept**: When extracting entities, LLM also tags evidence with context markers

```python
@dataclass
class Evidence:
    # ... existing fields
    context_tags: List[str]  # ["1980s", "Cold War", "Reagan administration"]
```

**Extraction Prompt Addition**:
```
When extracting entities from this evidence, also identify:
- Time period references (if any): "1980s", "post-9/11", "during Obama admin"
- Event context (if any): "Cold War", "Iraq War", "Watergate scandal"
- Geographic context (if any): "Cuba", "Middle East", "domestic"

Return as simple string tags for filtering/grouping later.
```

**Usage**:
- Filter evidence by tag: "Show all 1980s evidence in this Lead"
- Group entities by era: "Which J-2 directors appear in Cold War context?"
- No chronological sorting needed (just grouping)

**Benefits over timelines**:
- No date parsing complexity (just tags)
- Fuzzy by design ("1980s" not "1985-03-15")
- Supports non-temporal context ("Cold War", "domestic programs")
- LLM generates tags (no new extraction logic)

**Implementation**: 1-2 hours (add field + update extraction prompt)

**Recommendation**: Consider this IF you find yourself manually noting "this is Cold War stuff" during investigations

---

## Revised Implementation Priorities

### Must-Have for V1 (Automation Core)

1. **DeepResearchClient abstraction** (1 hour)
2. **Boolean hard-search path** (2-3 hours)
3. **Lead filters JSON + auto-attachment** (4-6 hours)
4. **Automatic pattern triggers** (8-10 hours)
5. **Budget controls** (2-3 hours)
6. **LeadRelation table** (1 hour)

**Total**: 18-24 hours

### Optional Enhancements

7. **Context tags** (if chronology matters): 1-2 hours
8. **Filter evolution (LLM-driven)**: 2-3 hours

**Total with optional**: 21-29 hours

---

## Automation Architecture Pattern

Based on your deep_research.py design, here's the V1 wiki automation flow:

### Fully Automated Investigation Cycle

```
User Action (one-time):
  ↓
  Create Lead("J-2 psychological warfare since 2001")
  ↓
  Configure filters: {entities: ["J-2"], keywords: ["psyops", "psychological warfare"]}
  ↓
  Attach patterns: [Person×Topic, Office×Capability]
  ↓
  Set budget: {max_runs_per_day: 10, max_cost: $20}
  ↓
  Click "Start Investigation"

--- AUTOMATION TAKES OVER ---

System (continuous):
  ↓
  Run initial deep research (task decomposition → search → filter → extract → synthesize)
  ↓
  Extract entities: ["J-2", "Operation NIGHTFIRE", "Person X"]
  ↓
  Auto-attach evidence to Lead (matches filters)
  ↓
  Trigger pattern: Person×Topic for "Person X" × "psychological warfare"
  ↓
  Run new research → extract → attach → trigger patterns...
  ↓
  Stop when: Budget reached OR no new results for 3 consecutive runs
  ↓
  Generate final report (synthesis of all evidence)
  ↓
  Email user: "Investigation complete. 127 evidence pieces, 23 entities, 45 claims. Cost: $18.50. View report: [link]"

User returns (hours/days later):
  ↓
  Reviews final report
  ↓
  Optionally: Adjusts filters, adds new patterns, increases budget, clicks "Resume Investigation"
```

### Key Automation Decisions (LLM-Driven)

**No human decisions needed for**:
1. Task decomposition (LLM breaks question into subtasks)
2. Source selection (LLM picks which databases to query)
3. Relevance filtering (LLM scores results, keeps relevant ones)
4. Entity extraction (LLM identifies people/orgs/programs/concepts)
5. Claim extraction (LLM structures relationships)
6. Evidence attachment (automatic based on filters)
7. Pattern triggering (automatic based on new entities)
8. Stop condition (automatic based on diminishing returns)

**User configures upfront**:
1. Lead filters (what evidence belongs here)
2. SearchPatterns (how to expand investigation)
3. Budget limits (max cost, max runs)
4. Quality thresholds (min relevance score, min source count for claims)

**User reviews afterward** (optional):
1. Final report
2. Execution logs (what was tried, what worked, what failed)
3. Cost breakdown
4. Coverage gaps (what couldn't be searched)

This matches your CLAUDE.md philosophy: **"User configures parameters once → Run research → Walk away → Get comprehensive results"**

---

## Addressing Previous Concerns (Why They Don't Apply)

### Concern 1: "You don't know your workflow yet"

**Rebuttal**: You DO know your workflow - it's already in deep_research.py:
- Automated task decomposition ✓
- Automated source selection ✓
- Automated relevance filtering ✓
- Automated entity extraction ✓
- Automated synthesis ✓

V1 wiki just adds:
- Multi-Lead organization (instead of single-run)
- Pattern-based expansion (instead of one-shot)
- Persistent storage (instead of files)

The automation pattern is PROVEN, not speculative.

---

### Concern 2: "Automation might build wrong thing"

**Rebuttal**: Budget controls prevent runaway costs:
- Max runs per day: 10
- Max cost per day: $20
- Stop on diminishing returns: 3 consecutive runs with 0 new findings

If automation does the wrong thing, you've lost $20, not $200. Acceptable experimentation cost.

---

### Concern 3: "Need manual control for investigative work"

**Rebuttal**: You HAVE manual control - at configuration time:
- Lead filters define scope
- Patterns define expansion strategy
- Budget defines limits

You don't need manual control at EXECUTION time (clicking buttons, approving results). That's busywork.

Your investigative intelligence goes into:
1. **Formulating the question** (Lead title + initial filters)
2. **Choosing expansion tactics** (which SearchPatterns to use)
3. **Interpreting results** (reading final report, deciding next investigation)

NOT into:
1. Clicking "Run pattern X" 50 times
2. Reviewing each Evidence piece for attachment
3. Approving each entity extraction

---

## Final Corrected Recommendation

### Accept ALL Automation Proposals ✅

1. ✅ Automation-first goal (matches your architecture)
2. ✅ Lead filters JSON with auto-attachment (4-6 hours)
3. ✅ Automatic pattern scheduling (8-10 hours)
4. ✅ Budget controls (2-3 hours)
5. ✅ DeepResearchClient abstraction (1 hour)
6. ✅ Boolean hard-search path (2-3 hours)
7. ✅ LeadRelation table (1 hour)
8. ❌ Timelines (per your request - skip)

**Total Implementation**: 18-24 hours

### Optional: Context Tags (If Needed)

If you find yourself caring about era/context during investigations:
- Add `context_tags: List[str]` to Evidence (1 hour)
- LLM extracts tags during entity extraction (1 hour)
- Filter/group by tags in UI (no sorting needed)

**This is better than timelines because**:
- No date parsing (just fuzzy tags like "1980s", "Cold War")
- Supports non-temporal context ("domestic", "Middle East")
- No chronological precision illusion (epistemic risk)

---

## Apology

I apologize for my previous review. I incorrectly imposed "unknown unknowns" caution on a system that:
1. Already has proven automation patterns
2. Explicitly designed for hands-off operation
3. Has budget controls to limit experimentation risk

The automation proposals are CORRECT for your use case. Accept them all (except timelines per your request).
