# V1 Design Risk Analysis - Index

**Date**: 2025-11-15
**Context**: Analysis of uncertainties/risks from v1_integrating_sigints_wiki_202511151134.md
**Method**: Comparative analysis using Mozart investigation findings + existing deep_research.py architecture

---

## Risk Documents (Priority Order)

1. **[RISK_1_METHODOLOGY.md](./RISK_1_METHODOLOGY.md)** - CRITICAL
   - Problem: Deep-research engines optimize for "good reports" not outliers/leads
   - Impact: May wash out weird/disturbing clues that are investigative gold
   - Status: Analysis complete

2. **[RISK_6_EPISTEMIC.md](./RISK_6_EPISTEMIC.md)** - CRITICAL
   - Problem: Reports feel authoritative, graphs look like reality
   - Impact: Weak patterns appear stronger than warranted
   - Status: Analysis pending

3. **[RISK_2_EXTRACTION.md](./RISK_2_EXTRACTION.md)** - HIGH
   - Problem: Entity conflation, over-asserted structure
   - Impact: Different entities merged, weak claims stated as strong
   - Status: Analysis pending

4. **[RISK_3_COVERAGE.md](./RISK_3_COVERAGE.md)** - HIGH
   - Problem: Search API bias, silent gaps
   - Impact: Worldview depends on opaque ranking algorithms
   - Status: Analysis pending

5. **[RISK_4_COST_LATENCY.md](./RISK_4_COST_LATENCY.md)** - MEDIUM
   - Problem: Bill shock, slow feedback killing investigative flow
   - Impact: Financial risk + UX degradation
   - Status: Analysis pending

6. **[RISK_5_IMPLEMENTATION.md](./RISK_5_IMPLEMENTATION.md)** - MEDIUM
   - Problem: API churn, dependency hell
   - Impact: Maintenance burden, framework lock-in
   - Status: Analysis pending

7. **[RISK_7_UNKNOWN_UNKNOWNS.md](./RISK_7_UNKNOWN_UNKNOWNS.md)** - META
   - Problem: Which interactions feel like real investigative assistant?
   - Impact: Can only discover through use
   - Status: Analysis pending

---

## Key Resources

**V1 Design Document**:
- `/home/brian/sam_gov/wiki_from_scratch_20251114/v1_integrating_sigints_wiki_202511151134.md`

**Mozart Investigation Findings**:
- `docs/reference/WIKIDISC_MOZART_RESEARCH_BOT.md` (45KB architecture doc)
- `docs/reference/MOZART_TECHNICAL_README.md` (35KB technical reference)
- `~/mozart-backup/mozart-people-extracted/mozart-people/` (728MB codebase)

**Existing Architecture**:
- `research/deep_research.py` (2800+ lines, working system)
- `CLAUDE.md` (design philosophy: "No hardcoded heuristics. Full LLM intelligence.")
- `STATUS.md` (what actually works)

---

## Analysis Approach

For each risk:

1. **Restate the uncertainty** (from V1 doc)
2. **Real-world evidence** (Mozart findings, your deep_research.py behavior)
3. **Severity assessment** (Critical/High/Medium/Low)
4. **V1 doc mitigations** (what's already proposed)
5. **Additional mitigations** (from Mozart patterns or your architecture)
6. **Implementation priority** (Must-have/Should-have/Nice-to-have for v1)
7. **Open questions** (what you can't know until you build/use it)

---

## Priority Ranking Rationale

**Critical (Risks 1 & 6)**: These are **epistemic/methodological** risks that affect *how you think* with the tool. Getting these wrong means building a tool that misleads you, which is worse than no tool.

**High (Risks 2 & 3)**: These are **data quality** risks. Dirty data → bad insights, but at least you can *see* the data and judge it.

**Medium (Risks 4 & 5)**: These are **operational** risks. Annoying/expensive, but they don't corrupt your investigation process itself.

**Meta (Risk 7)**: Can't fully address until you use v1 in anger. Treat v1 as instrumented experiment.

---

## Next Steps

1. Analyze each risk (one document per risk)
2. Create executive summary with prioritized mitigation roadmap
3. Commit all analysis documents
