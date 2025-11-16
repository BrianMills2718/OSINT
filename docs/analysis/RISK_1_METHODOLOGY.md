# Risk #1: Methodology Risk - Reports vs Outliers

**Severity**: CRITICAL
**Category**: Epistemic/Methodological
**Date**: 2025-11-15

---

## The Uncertainty (from V1 doc)

**Problem**: Deep-research libraries (GPT Researcher, DeerFlow, etc.) are optimized for:
- "Give me a good report"
- "Summarize many sources nicely"

**NOT optimized for**:
- Surfacing weird outliers
- Preserving fragile leads
- Building "search strategies" (Boolean-style investigative work)

**Stated Risks**:
1. May over-summarize the interesting weird bits
2. LLM tries to be coherent and "balanced" → washes out odd/disturbing/low-frequency clues
3. May not respect your search tactics (turns "J-2 AND psychological operations AND site:.mil" into softer "find info about J-2 and psyops")
4. Report-first, not lead-first (you care about lead generation at least as much as nice write-ups)

---

## Real-World Evidence

### From Mozart Investigation

**Architecture**: Multi-LLM pipeline with verification-aware extraction
- Perplexity API → Brave Search → Gemini 2.5 Flash (extraction) → Claude Sonnet 4.5 (prose)

**Key Finding**: Mozart IS report-first (creates polished Wikipedia-style biographies)
- Example output: Professional person pages with sections like "Career", "Contributions", "Controversies"
- 130+ person pages created, all follow same coherent narrative structure
- Source: `docs/reference/WIKIDISC_MOZART_RESEARCH_BOT.md` lines 180-220

**Relevant Pattern**: "Verification-aware extraction"
- Gemini extraction prompt explicitly handles disputed claims
- Marks claims as "verified" vs "disputed" vs "rumored"
- Source: Mozart `app/extraction/gemini_extractor.py` (documented in MOZART_TECHNICAL_README.md)

**What This Tells Us**:
- Even with verification awareness, Mozart's goal is "authoritative-looking biography"
- Outliers preserved ONLY IF they're disputed claims (not low-frequency weird patterns)
- No evidence of "lead generation" mode - everything flows to final coherent narrative

### From Your Existing deep_research.py

**Architecture**: Task decomposition → Multi-source search → Relevance filtering → Report synthesis
- Uses GPT-5-mini for planning, Gemini 2.5 Flash for extraction, Claude Sonnet 4 for synthesis

**Key Behaviors** (observed from test runs):
1. **Task decomposition** (lines 232-272): Breaks question into 3-5 subtasks
   - Optimized for "comprehensive coverage" of question
   - NOT optimized for "weird outlier discovery"

2. **Relevance filtering** (lines 1319-1399): LLM scores results 0-10
   - Per-result filtering with `relevant_indices` (committed fix 0eb3ff3)
   - Filters OUT off-topic junk
   - BUT: "off-topic" defined by alignment with research question
   - **Risk**: Weird outliers that don't fit neat categories may score low

3. **Report synthesis** (lines 1966-2132): Creates coherent markdown report
   - Structured sections (Summary, Key Findings, Analysis, Recommendations)
   - Optimized for readability and authority
   - Source: `prompts/deep_research/report_synthesis.j2`

**What This Tells Us**:
- Your system ALSO leans report-first (by design, per user request)
- Relevance filtering is double-edged: removes junk BUT may remove weird gold
- No "exploration mode" or "outlier detection" currently exists

---

## Severity Assessment: CRITICAL

**Why Critical**:
1. **Affects how you think**: If the tool hides weird patterns, you won't know they exist
2. **Investigative journalism core need**: Outliers are often the story ("why does this person keep appearing in unrelated contexts?")
3. **Silent failure mode**: You won't KNOW something was filtered out (no "we discarded 10 weird results" warning)

**Concrete Example** (hypothetical but realistic):
- Research question: "Psychological warfare programs involving J-2 since 2001"
- Deep research finds:
  - 50 results about official psyops doctrine (high relevance: 9/10)
  - 5 results about budget anomalies in J-2 IT procurement (low relevance: 3/10)
  - 2 results mentioning J-2 + offshore contractors + "perception management" (medium relevance: 6/10)
- **Risk**: The 2 offshore contractor results might be THE lead, but they're:
  - Outnumbered 25:1 by "normal" results
  - Lower relevance scores (odd phrasing, indirect connections)
  - May get dropped or buried in synthesis ("mentioned in passing")

---

## V1 Doc Proposed Mitigations

1. **Always store all evidence** + expose:
   - Raw snippet browser per lead
   - Full-text search over evidence.snippet_text

2. **Add "exploration mode" prompt** that explicitly says:
   - "List unusual entities, codewords, units, offices, phrases that look like potential leads"
   - "Don't collapse into narrative; just list them"

3. **For critical Boolean tactics, bypass deep-research engine**:
   - Build simple `build_query_from_entities_and_keywords(...)`
   - Call Brave search directly
   - Save as separate ResearchRun
   - Use engine mainly to read & summarize targeted search results

---

## Additional Mitigations (from Mozart + Your Architecture)

### Mitigation A: Two-Pass LLM Strategy (Mozart Pattern)

**What Mozart Does**:
- Pass 1 (Gemini): Extract ALL entities/claims (even disputed/weak ones)
- Pass 2 (Sonnet): Generate coherent prose (but raw extraction preserved)

**Adaptation for V1**:
- Pass 1: "Extraction mode" - ask LLM to identify:
  - All entities (even low-confidence)
  - All unusual phrases/codewords
  - All anomalies (co-occurrences, unexpected sources, outliers)
- Pass 2: "Report mode" - create coherent narrative
- **Key**: Store Pass 1 output separately (don't let Pass 2 filter it)

**Implementation** (research/deep_research.py):
- Add `_extract_outliers()` method after relevance filtering (line ~1400)
- Store outliers in `ResearchTask.outliers_found: List[Dict]`
- Display outliers in separate report section or UI table

**Benefit**: Report stays coherent, BUT you have escape hatch to see "weird stuff LLM noticed but didn't emphasize"

### Mitigation B: Configurable Relevance Threshold (Your CLAUDE.md Philosophy)

**Current Behavior**: Relevance filtering uses LLM judgment + `relevant_indices`
- No explicit threshold (LLM decides accept/reject per batch)

**Enhancement** (align with "no hardcoded heuristics" but make transparent):
- Add `min_relevance_threshold` config option (default: 0, keeps everything)
- Log distribution of relevance scores per task
- Show "X results filtered out (scores 0-5), Y results kept (scores 6-10)" in report

**Benefit**: User can tune conservatism ("keep more weird stuff" = threshold 0, "high-quality only" = threshold 7)

### Mitigation C: Anomaly Detection Prompt (New)

**What It Does**: Dedicated LLM call after synthesis asking:
- "Given these results, what patterns are SURPRISING?"
- "What co-occurrences are UNEXPECTED?"
- "Which entities appear in unusual combinations?"

**Output**: Separate "Anomalies & Leads" section in report
- Not filtered through "does this fit the question" lens
- Explicitly looking for "things that don't fit"

**Implementation**: Add to `_synthesize_report()` as optional Pass 3

---

## Implementation Priority for V1

### Must-Have (P0)
1. **Store all raw evidence** (already in V1 design)
   - Every snippet preserved in `evidence` table
   - Full-text search functional
   - **Status**: Planned, straightforward

2. **Separate "exploration mode" prompt** (V1 doc mitigation #2)
   - Dedicated LLM call to list unusual entities/phrases
   - Store in separate field (not collapsed into report)
   - **Status**: Planned, ~1-2 hours implementation

### Should-Have (P1)
3. **Two-pass extraction** (Mozart pattern adaptation)
   - Pass 1: Extract everything (including outliers)
   - Pass 2: Synthesize coherent report
   - **Status**: New, ~3-4 hours implementation

4. **Relevance threshold transparency** (alignment with CLAUDE.md)
   - Log score distributions
   - Show "what was filtered" counts
   - Make threshold configurable
   - **Status**: Enhancement, ~2 hours implementation

### Nice-to-Have (P2)
5. **Anomaly detection prompt** (new Pass 3)
   - Dedicated "what's surprising?" LLM call
   - Separate report section
   - **Status**: New, ~2-3 hours implementation

6. **Direct Boolean search bypass** (V1 doc mitigation #3)
   - Build query from KG entities
   - Call Brave directly (skip deep-research engine)
   - **Status**: Planned for later (Phase 2 feature)

---

## Open Questions (Can't Know Until V1 Used)

1. **What % of valuable leads are actually outliers?**
   - Hypothesis: 10-30% of real investigative gold is low-frequency weird stuff
   - Test: Run V1 on known case (e.g., your psychological warfare example) and see what gets filtered

2. **Will "exploration mode" prompt actually surface useful leads?**
   - Risk: LLM may still over-filter or generate noise
   - Test: Compare "exploration mode" output to manual review of raw evidence

3. **Does synthesis really wash out outliers, or is raw evidence enough?**
   - Hypothesis: If evidence browser is good, synthesis quality matters less
   - Test: Use V1 without reading reports (only browse evidence/entities) and see if workflow works

4. **How much does this matter for different investigation types?**
   - Structured topics (job opportunities, budget data): Reports probably fine
   - Conspiratorial/weird topics (UFOs, classified programs, corruption): Outliers critical
   - Test: Run V1 on both types and measure "lead discovery" rate

---

## Comparison: Mozart vs Your System

| Aspect | Mozart | Your deep_research.py | V1 Wiki Design |
|--------|--------|----------------------|----------------|
| **Goal** | Polished biographies | Comprehensive reports | Lead generation + reports |
| **Outlier handling** | Disputed claims preserved | Filtered by relevance | Raw evidence always stored |
| **Exploration mode** | No (narrative-first) | No (report-first) | Planned (exploration prompt) |
| **Escape hatch** | Full extraction JSON saved | Execution logs + raw files | Evidence browser + full-text search |
| **Risk level** | Medium (biographies less sensitive to outliers) | Medium-High (depends on use case) | High (investigative journalism needs outliers) |

---

## Recommended V1 Approach

**Design for Dual Mode from Day 1**:

1. **Report Mode** (default for most queries):
   - Task decomposition → Search → Filter → Synthesize
   - Optimized for "give me comprehensive overview"
   - Current deep_research.py behavior

2. **Exploration Mode** (toggle for weird topics):
   - Task decomposition → Search → **Skip aggressive filtering** → Extract outliers → List leads
   - Optimized for "show me weird stuff I should investigate"
   - New prompt + lower relevance threshold

**UI/Config**:
```yaml
research:
  mode: "report"  # or "exploration"
  relevance_threshold: 6  # 0-10, lower = keep more weird stuff
  extract_outliers: true  # always run exploration prompt alongside report
```

**Report Sections**:
- Main report (coherent narrative)
- Anomalies & Leads (weird stuff from exploration mode)
- Evidence browser (raw escape hatch)

**Benefit**: Addresses methodology risk without building two separate systems

---

## Final Assessment

**Risk Severity**: CRITICAL (affects investigative epistemology)

**V1 Mitigations Adequacy**: GOOD (if fully implemented)
- Raw evidence storage: ✅ Addresses "you can always go back to snippets"
- Exploration mode: ✅ Addresses "don't collapse weird stuff"
- Direct search bypass: ✅ Addresses "respect my Boolean tactics"

**Additional Recommendations**: IMPORTANT
- Two-pass extraction (Mozart pattern)
- Relevance threshold transparency
- Dual-mode design (report vs exploration)

**Bottom Line**: This is THE risk to get right in V1. If you get this wrong, you're building a tool that makes you *less* effective as an investigator (coherent but misleading reports). If you get it right, you have a power tool that augments human pattern-matching instead of replacing it.
