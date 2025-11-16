# V1 Risk Analysis - Executive Summary

**Date**: 2025-11-15
**Analysis of**: v1_integrating_sigints_wiki_202511151134.md uncertainties/risks
**Method**: Comparative analysis using Mozart findings + existing deep_research.py architecture

---

## Quick Reference

| Risk | Severity | Category | V1 Mitigations | Our Additions | Priority |
|------|----------|----------|----------------|---------------|----------|
| **#1 Methodology** | CRITICAL | Epistemic | Good if implemented | Two-pass extraction, dual-mode design | P0 |
| **#6 Epistemic** | CRITICAL | Cognitive | Weak (needs strengthening) | Claim strength indicators, phrasing discipline | P0 |
| **#2 Extraction** | HIGH | Data Quality | Moderate | Deduplication, predicate typing | P1 |
| **#3 Coverage** | HIGH | Data Quality | Moderate | Coverage metadata, known unknowns tracking | P1 |
| **#4 Cost/Latency** | MEDIUM | Operational | Good | Cost budgeting, quick search mode | P1 |
| **#5 Implementation** | MEDIUM | Technical Debt | Good | Don't use external frameworks (diverge from V1 doc) | P1 |
| **#7 Unknown Unknowns** | META | Product Design | Correct approach | Instrumentation, post-mortems, 10-investigation commitment | Ongoing |

---

## Critical Risks (Must Address in V1)

### Risk #1: Methodology - Reports Wash Out Outliers

**The Problem**: Deep-research engines optimize for "good reports" not "weird outliers that are investigative gold"

**Why Critical**: If tool hides weird patterns, you won't know they exist → worse than no tool

**V1 Doc Mitigations** (Good):
- Store all raw evidence
- Exploration mode prompt
- Direct Boolean search bypass

**Our Additions** (Important):
- Two-pass LLM strategy (extraction mode + report mode)
- Configurable relevance threshold (transparency)
- Dual-mode design (report vs exploration from day 1)

**Implementation** (P0 - Must-Have):
- Evidence browser with full-text search (planned)
- Exploration mode prompt (2 hours)
- Relevance threshold logging (2 hours)

**Bottom Line**: This is THE risk to get right. If V1 only produces coherent reports without surfacing outliers, you're building a tool that makes you *less* effective as an investigator.

---

### Risk #6: Epistemic - Reports Feel Authoritative

**The Problem**: Neat reports + pretty graphs make weak patterns look stronger than they are

**Why Critical**: Corrupts investigative epistemology → you'll trust patterns that don't deserve trust → cite weak claims in published work

**V1 Doc Mitigations** (Weak):
- 1-click snippet links (good but insufficient)
- Visual confidence cues (good but vague)
- Philosophical stance (necessary but not sufficient)

**Our Additions** (Essential):
- Claim strength indicators (source count, domain diversity, confidence scores)
- Report phrasing discipline (hedged language for weak claims)
- Coverage metadata header (prominent "what we don't know")
- Entity disambiguation warnings

**Implementation** (P0 - Must-Have):
- Claim strength in database schema + UI (3 hours)
- Synthesis prompt phrasing rules (1 hour)
- Coverage metadata header (2 hours)

**Bottom Line**: Hardest risk to mitigate (fights human cognitive biases). Technical solutions help but aren't bulletproof. Real mitigation is **habits**: Never cite single-source claims, always check strength indicators, read "Limitations" section first.

**Practical Workflow Rule** (first 3 months):
> "Never cite a claim in external writing unless it has 3+ distinct sources OR I've manually verified the underlying evidence"

---

## High Risks (Should Address in V1)

### Risk #2: Extraction - Entity Conflation & Over-Assertion

**The Problem**: LLM merges different entities (conflation) or asserts strong claims from weak text (over-assertion)

**Severity**: HIGH (data quality matters) but VISIBLE (often obvious when it happens) and RECOVERABLE

**V1 Doc Mitigations** (Moderate):
- Design for ambiguity not correctness ✅
- 1-click snippet links ✅
- Text search bypass ✅
- Curated predicate list ✅

**Our Additions** (Important):
- Multi-pass entity deduplication
- Predicate strength typing (strong/weak/meta tiers)
- Disambiguation risk tracking

**Implementation** (P1 - Should-Have):
- Deduplication pipeline (4-5 hours)
- Predicate strength system (2-3 hours)

**Bottom Line**: Manageable with good engineering. Unlike methodology/epistemic risks (human biases), extraction risk is mostly technical (deduplication + confidence scores).

---

### Risk #3: Coverage - Silent Gaps

**The Problem**: Worldview depends on which search APIs hit, which sites are accessible. System rarely says "I couldn't search X"

**Severity**: HIGH (invisible bias) but TOLERABLE if transparent

**V1 Doc Mitigations** (Moderate):
- Query/domain logging ✅
- Manual seed URLs ✅
- Thin run flagging ✅

**Our Additions** (Important):
- Coverage metadata header (prominent in every report)
- Known unknowns tracking (database + UI)
- Coverage scoring per Lead

**Implementation** (P1 - Should-Have):
- Coverage metadata (2 hours)
- Known unknowns table (4 hours)

**Bottom Line**: Danger isn't incomplete coverage (all research is incomplete) - danger is SILENT incompleteness. If every report says "here's what we found AND here's what we couldn't access", you stay epistemically honest.

---

## Medium Risks (Monitor, Mitigate as Needed)

### Risk #4: Cost/Latency - Bill Shock & Slow Feedback

**The Problem**: LLM + search API costs add up; 3-minute latency kills investigative flow

**Severity**: MEDIUM (annoying but manageable, not existential)

**Real Costs** (from test data):
- Deep run: $1-2 per investigation
- Monthly (moderate use): $50-150
- Acceptable for serious investigative work

**Real Latency**:
- Deep run: 2-5 minutes (acceptable for batch work, annoying for quick lookups)

**V1 Doc Mitigations** (Good):
- Depth presets ✅
- URL caching ✅
- Parallelism limits ✅

**Our Additions** (Helpful):
- Cost budgeting + tracking
- Quick search mode (fast lookups bypass full deep research)

**Implementation** (P1):
- Cost tracking (4-5 hours)
- Quick search mode (6-8 hours)

**Bottom Line**: Operational not existential. Mitigate with transparency (show cost/time per run) and tiered performance (not every question needs deep research).

---

### Risk #5: Implementation - API Churn & Dependency Hell

**The Problem**: External frameworks change APIs, bring dependency conflicts

**Severity**: MEDIUM (time sink but manageable)

**V1 Doc Assumption**:
> "Wrap GPT-Researcher / Deep Research / DeerFlow as the engine"

**Our Analysis**: **This assumption is WRONG**
- You already have working deep_research.py (~2800 lines)
- Wrapping external framework would INCREASE complexity, not decrease
- Custom architecture = lower dependency risk

**Recommendation**: **DIVERGE from V1 doc**
- Use your existing deep_research.py as engine
- V1 wiki wraps YOUR engine, not third-party framework

**V1 Doc Mitigations** (Good for framework approach):
- Clean abstraction ✅
- Pin versions ✅
- Dumb fallback ✅

**Our Addition**: Don't use frameworks (better mitigation)

**Implementation** (P1):
- Update V1 design to reflect "use existing deep_research.py"
- Dumb fallback script (2-3 hours)

**Bottom Line**: Minimize external dependencies. Since you have working engine, don't add framework dependency.

---

### Risk #7: Unknown Unknowns - What Actually Feels Useful?

**The Problem**: Can't know which features you'll use until you try

**Severity**: META (not a risk to mitigate, a learning opportunity to embrace)

**V1 Doc Approach** (Correct):
- Treat V1 as instrumented notebook
- Log everything, keep legible, assume refactoring

**Our Additions** (Process):
- Commit to 10 investigations minimum
- Write post-mortem after each
- Weekly metrics review
- Explicit V1 → V2 cutover (after 10 investigations OR 3 months)

**Implementation** (Ongoing):
- Logging infrastructure (built-in)
- Post-mortem template (1 hour)
- Metrics dashboard (4-6 hours)

**Bottom Line**: This is how good tools get built - iterative refinement with domain expert in loop. V1 is probe, not product.

---

## Prioritized Mitigation Roadmap

### Phase 0: V1 Design Update (Before Implementation)

**Action**: Update v1_integrating_sigints_wiki_202511151134.md to reflect:
- Use existing deep_research.py (not GPT-Researcher/DeerFlow)
- Dual-mode design (report vs exploration) from day 1
- Claim strength indicators as core feature (not optional)

**Rationale**: Avoid building wrong thing based on outdated assumptions

---

### Phase 1: Core V1 Implementation (P0 - Must-Have)

**Epistemic & Methodology Fixes** (Critical):
1. Evidence browser + full-text search (already planned)
2. Exploration mode prompt (2 hours)
3. Claim strength indicators in schema + UI (3 hours)
4. Report synthesis phrasing discipline (1 hour)
5. Coverage metadata header (2 hours)
6. Relevance threshold logging (2 hours)

**Total**: ~10-12 hours (must complete before using V1 for real investigations)

---

### Phase 2: Data Quality Enhancements (P1 - Should-Have)

**Extraction & Coverage Fixes** (High):
1. Entity deduplication pipeline (4-5 hours)
2. Predicate strength typing (2-3 hours)
3. Known unknowns tracking (4 hours)
4. Manual seed URL UI (3 hours)
5. Thin run flagging (1 hour)

**Total**: ~14-16 hours (complete within first month of V1 usage)

---

### Phase 3: Operational Improvements (P1 - Nice-to-Have)

**Cost/Latency & Maintenance** (Medium):
1. Cost budgeting + tracking (4-5 hours)
2. Quick search mode (6-8 hours)
3. Dumb fallback script (2-3 hours)
4. Dependency monitoring setup (1 hour)

**Total**: ~13-17 hours (add as friction points emerge)

---

### Phase 4: Learning & Iteration (Ongoing)

**Unknown Unknowns** (Meta):
1. Instrumentation + logging (built-in)
2. Post-mortem after each investigation (30 min each)
3. Weekly metrics review (1 hour/week)
4. V1 → V2 cutover analysis (8-12 hours after 10 investigations)

**Total**: Ongoing (part of V1 usage workflow)

---

## Key Divergences from V1 Doc

### 1. Don't Wrap External Frameworks ⚠️ IMPORTANT

**V1 Doc Says**:
> "Reuse existing deep-research libraries (GPT-Researcher / Deep Research / DeerFlow) as the engine"

**Our Recommendation**: Use existing deep_research.py instead

**Rationale**:
- Already working (~2800 lines, proven in tests)
- Lower dependency risk
- Full control over investigative methodology
- Simpler architecture

**Impact**: Reduces Risk #5 (implementation/maintenance) significantly

---

### 2. Dual-Mode Design from Day 1 ⚠️ IMPORTANT

**V1 Doc Implies**: Single research flow (task decomposition → search → synthesize)

**Our Recommendation**: Two modes from start

| Mode | Use Case | Optimization |
|------|----------|--------------|
| **Report** | "Give me comprehensive overview" | Coherent synthesis, high relevance threshold |
| **Exploration** | "Show me weird stuff" | List outliers, low relevance threshold, no synthesis filtering |

**Rationale**: Addresses Risk #1 (methodology) without rebuilding later

**Impact**: Users can choose methodology per investigation (psychological warfare = exploration, job market analysis = report)

---

### 3. Claim Strength as Core Feature ⚠️ CRITICAL

**V1 Doc Implies**: Confidence/strength indicators are optional visual cues

**Our Recommendation**: Bake into data model + UI from start

**Database Schema**:
```sql
Claim
- confidence_score (0-1)
- source_count (computed)
- domain_diversity (computed)
- predicate_tier ("strong" | "weak" | "meta")
```

**Rationale**: Addresses Risk #6 (epistemic) - can't retrofit epistemic discipline later

**Impact**: Forces you to think about claim strength from day 1 (builds good habits)

---

## Success Metrics (How to Know if V1 Worked)

### After 10 Investigations, Ask:

**Epistemic Discipline** (Risk #6):
- ✅ Did I check claim strength before citing in external writing?
- ✅ Did I read "Coverage Limitations" section in every report?
- ❌ Did I cite any single-source claims?

**Outlier Discovery** (Risk #1):
- ✅ Did exploration mode surface leads I wouldn't have found manually?
- ❌ Did I skip using exploration mode (too much friction)?

**Data Quality** (Risk #2, #3):
- ✅ Did entity deduplication catch obvious duplicates?
- ✅ Did coverage metadata help me identify gaps?
- ❌ Did I encounter entity conflations that broke my investigation?

**Operational** (Risk #4, #5):
- ✅ Were costs predictable and acceptable?
- ✅ Did quick search mode preserve investigative flow?
- ❌ Did any dependencies break?

**Unknown Unknowns** (Risk #7):
- What features did I use most? (evidence browser, entity pages, claims table, patterns)
- What features did I ignore? (delete in V2)
- What's missing? (add in V2)

---

## Final Recommendations

### For V1 Implementation

1. **Address Critical Risks First** (Methodology + Epistemic)
   - These affect how you think (most dangerous)
   - Technical solutions exist (exploration mode, claim strength)
   - Habits matter more than features (build discipline from day 1)

2. **Use Your Existing Architecture** (Don't Add Framework Dependency)
   - deep_research.py already works
   - V1 wiki should wrap it, not replace it
   - Diverge from V1 doc assumption

3. **Design for Transparency** (Make Uncertainty Visible)
   - Coverage metadata in every report
   - Claim strength in every UI element
   - Known unknowns explicitly tracked

### For V1 Usage

1. **Commit to Learning Process** (10 investigations minimum)
   - Write post-mortems
   - Review metrics weekly
   - Explicit V1 → V2 cutover

2. **Build Epistemic Habits** (First 3 Months)
   - Never cite single-source claims
   - Always check claim strength
   - Read limitations before findings

3. **Embrace Unknown Unknowns** (Don't Over-Plan)
   - V1 is probe, not product
   - Refactor based on usage, not speculation
   - Simple implementations (avoid premature optimization)

---

## Bottom Line

**The Two Critical Risks** (#1 Methodology, #6 Epistemic) both boil down to:

> **"Will this tool make me a better investigator or will it give me false confidence in weak patterns?"**

**Technical mitigations exist** (exploration mode, claim strength, coverage metadata), but **habits matter more**:
- Always skeptical of first-pass synthesis
- Always check underlying evidence
- Always aware of what you DON'T know

**V1 should be designed to SUPPORT these habits**, not require superhuman discipline to overcome bad defaults.

**If V1 makes weird outliers easy to find AND weak claims obviously weak**, you've succeeded. Everything else (entity deduplication, cost optimization, etc.) is engineering detail.
