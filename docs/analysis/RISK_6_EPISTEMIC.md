# Risk #6: Epistemic Risk - Authoritative Appearance

**Severity**: CRITICAL
**Category**: Cognitive/Epistemological
**Date**: 2025-11-15

---

## The Uncertainty (from V1 doc)

**Background**: You're an epistemological nihilist who cares about "what is claimed where" not "truth" in absolute sense.

**V1 Design Already Matches This**:
- Source = where
- Evidence = what text we saw
- Claim = structured annotation of that text

**BUT: Two Human-Cognition Risks Remain**:

1. **Reports feel authoritative**
   - Neatly written report with citations feels more grounded than it may be

2. **Graph structure feels like reality**
   - Seeing entity → relationship → entity makes weak patterns look stronger

---

## Real-World Evidence

### From Mozart Investigation

**What Mozart Produces**:
- Wikipedia-style person pages with authoritative tone
- Example structure (from WIKIDISC_MOZART_RESEARCH_BOT.md lines 180-220):
  ```
  ## Career
  Col. John Smith served as Director of J-2 from 2005-2008...

  ## Controversies
  Smith was named in several reports regarding...

  ## References
  [1] DoD Report 2006...
  [2] News article...
  ```

**Observed Pattern**: Professional encyclopedic tone
- Uses declarative statements ("served as", "was responsible for")
- Structured sections create appearance of comprehensive coverage
- Citations anchor text but don't convey claim strength
- Source: Actual WikiDisc pages at wikidisc.org

**Risk Manifestation**:
- No visible distinction between "mentioned once in one source" vs "confirmed across 10 sources"
- Verification framework exists (disputed vs verified) but presentation is still assertive
- Reader must actively click through to judge claim strength

### From Your Existing deep_research.py

**Report Output** (from test runs):
- Professional markdown with sections:
  - Executive Summary
  - Key Findings (bullet points with authoritative tone)
  - Detailed Analysis (narrative paragraphs)
  - Recommendations
- Source: `prompts/deep_research/report_synthesis.j2` lines 15-30

**Example Output Tone** (from validation test 2025-11-04):
```markdown
## Key Findings

- Federal cybersecurity jobs require active security clearances (Secret, Top Secret, TS/SCI)
- Primary hiring agencies include NSA, DIA, Cyber Command, FBI
- Salary ranges from GS-12 ($80K) to GS-15 ($140K+)
```

**What's Missing**:
- No indication that "Primary hiring agencies" is based on 12 results from 2 sources (USAJobs + ClearanceJobs)
- No signal that "Salary ranges" is aggregated from 8 job postings (small sample)
- Authoritative bullet points despite limited/noisy evidence base

**Risk Manifestation**:
- Reports READ like comprehensive research
- Actually based on whatever search APIs returned (could be 50 results, could be 500)
- No visual "confidence" or "coverage" indicators

---

## Severity Assessment: CRITICAL

**Why Critical**:
1. **Corrupts investigative epistemology**: You'll trust patterns that don't deserve trust
2. **Invisible degradation**: Unlike methodology risk (where you might notice missing outliers), this risk makes you FEEL confident when you shouldn't be
3. **Compounding effect**: Graph structure + authoritative reports = double illusion of knowledge

**Concrete Example** (realistic scenario):

**Investigation**: "Psychological warfare programs involving J-2 since 2001"

**What Actually Happened**:
- Brave Search returned 30 results (20 from one think tank, 5 from .mil, 5 from news)
- 3 results mentioned "Operation NIGHTFIRE" (all from same 2006 report)
- LLM extracted entities: "J-2", "Operation NIGHTFIRE", "Person X"
- LLM created claim: `J-2 → oversaw → Operation NIGHTFIRE`

**What V1 Shows**:
- Report: "The J-2 oversaw Operation NIGHTFIRE, a psychological operations initiative [1]"
- Graph: Node "J-2" connected to node "Operation NIGHTFIRE" with edge "oversaw"
- Evidence count: 3 snippets

**What You DON'T See** (without deliberate design):
- All 3 snippets are from same original document (just quoted in different places)
- No other sources mention this connection
- "Oversaw" is LLM interpretation of text that said "J-2 was briefed on"
- Search only covered 30 pages total (tiny sample of possible evidence space)

**Failure Mode**: You cite this in your investigative piece as "confirmed connection" when it's actually "single-source weak claim"

---

## V1 Doc Proposed Mitigations

**UX-Level Mitigations**:

1. **Always be able to drop back to raw snippets quickly**
   - Every claim has 1-click link to underlying evidence + source

2. **Visual cue for "confidence"**:
   - Number of evidence snippets supporting claim
   - Number of distinct domains

3. **Treat KG as "map of assertions people have made", not "the way the world is"**
   - Philosophical stance, not technical feature

---

## Additional Mitigations (from Mozart + Your Architecture)

### Mitigation A: Claim Strength Indicators (Visible Uncertainty)

**What to Show for Every Claim**:

| Indicator | What It Means | How to Compute |
|-----------|---------------|----------------|
| **Source count** | How many distinct sources? | `COUNT(DISTINCT source_id)` per claim |
| **Domain diversity** | How many distinct domains? | `COUNT(DISTINCT domain)` per claim |
| **Evidence snippets** | How many text passages? | `COUNT(evidence_id)` per claim |
| **Extraction confidence** | How confident was LLM? | Store confidence score from extraction |
| **Predicate strength** | Strong claim or weak? | `oversaw` vs `mentioned_with` |

**UI Presentation** (claim table):
```
J-2 → oversaw → Operation NIGHTFIRE
  ⚠️ 1 source, 3 snippets, same domain (.mil)
  [Click to see evidence]

Person X → held_role → Director of J-2
  ✓ 5 sources, 12 snippets, diverse domains (.mil, .gov, news)
  [Click to see evidence]
```

**Benefit**: Makes claim strength VISIBLE, not hidden

### Mitigation B: Report Phrasing Discipline (Mozart Pattern Inversion)

**Mozart Problem**: Uses declarative statements that feel authoritative
- "Smith served as Director..." (sounds definitive)

**V1 Solution**: Use hedged phrasing that signals provenance
- "According to [source], Smith served as Director..." (signals single source)
- "Multiple sources confirm Smith served as Director..." (signals multi-source)
- "One document mentions Smith in connection with..." (signals weak claim)

**Implementation**: Update synthesis prompt (`report_synthesis.j2`) to include phrasing rules:

```jinja2
For each claim you include in the report, ALWAYS indicate source strength:
- Single source: "According to [source], ..."
- 2-3 sources: "Several sources indicate..."
- 4+ sources: "Multiple sources confirm..."
- Weak evidence: "One document mentions...", "Some evidence suggests..."
```

**Benefit**: Report TONE matches claim strength (authoritative tone reserved for well-supported claims)

### Mitigation C: Coverage Metadata (Prominent Display)

**What to Show in Every Report Header**:

```markdown
## Research Coverage

**Search Scope**:
- Queries executed: 12
- Sources found: 47 URLs
- Domains: .mil (15), .gov (8), news outlets (12), think tanks (8), other (4)
- Date range: 2001-2025
- Geographic coverage: US-centric (45/47), international (2/47)

**Limitations**:
- Search APIs: Brave Search, Tavily
- No access to: classified databases, paywalled archives, non-indexed sites
- Low coverage: < 50 total sources (thin investigation)
```

**Benefit**: Makes "what we DON'T know" visible, not hidden

### Mitigation D: Entity Disambiguation Status (Graph Uncertainty)

**Problem**: Graph shows "J-2" as single node, but might refer to different offices/people in different contexts

**Solution**: Track disambiguation confidence per entity

| Entity | Canonical Name | Disambiguation Status | Evidence Count |
|--------|----------------|----------------------|----------------|
| E123 | Joint Staff J-2 | ✓ High confidence (consistent across 15 snippets) | 15 |
| E456 | J-2 | ⚠️ Ambiguous (might be 2 different offices) | 8 |
| E789 | Operation NIGHTFIRE | ? Low confidence (only 3 mentions, no confirmation) | 3 |

**UI Presentation**: Color-code nodes in graph view
- Green: High confidence (well-documented, consistent)
- Yellow: Ambiguous (possible conflation)
- Red: Low confidence (single-source, unconfirmed)

**Benefit**: Graph shows uncertainty visually, not just in data

---

## Implementation Priority for V1

### Must-Have (P0)

1. **1-click snippet links** (V1 doc mitigation #1)
   - Every claim/entity has immediate link to underlying evidence
   - **Status**: Core feature, planned

2. **Claim strength indicators** (Mitigation A)
   - Source count, domain diversity, snippet count
   - Shown in claims table + entity pages
   - **Status**: New, ~2-3 hours implementation

3. **Report phrasing discipline** (Mitigation B)
   - Synthesis prompt updated to hedge appropriately
   - **Status**: New, ~1 hour implementation

### Should-Have (P1)

4. **Coverage metadata in report header** (Mitigation C)
   - Show search scope + limitations prominently
   - **Status**: New, ~2 hours implementation

5. **Entity disambiguation confidence** (Mitigation D)
   - Track conflation risk per entity
   - Visual indicators in graph/table
   - **Status**: New, ~3-4 hours implementation

### Nice-to-Have (P2)

6. **Claim provenance visualization**
   - Timeline showing when claim was made by which sources
   - Helps spot "all from same timeframe = same original source" patterns
   - **Status**: Future enhancement

---

## Open Questions (Can't Know Until V1 Used)

1. **Will you actually check claim strength indicators?**
   - Hypothesis: You'll skim reports and trust them (human nature)
   - Test: Track how often you click through to evidence in first month of use

2. **Do hedged report phrasings annoy you or help you?**
   - Risk: Constant hedging makes reports tedious to read
   - Benefit: Hedging keeps you epistemically honest
   - Test: Compare "fully hedged" vs "confident tone" report variants

3. **What's the right balance between graph prettiness and uncertainty signaling?**
   - Pretty graphs are easier to read but feel more authoritative
   - Ugly graphs with confidence warnings are epistemically better but harder to use
   - Test: A/B test graph visualizations (clean vs annotated)

4. **Does this risk manifest differently for different investigation types?**
   - Structured data (budgets, org charts): Graphs probably fine (claims are clearer)
   - Fuzzy data (motivations, connections, rumors): Graphs dangerous (weak patterns look strong)
   - Test: Track false-confidence incidents across investigation types

---

## Comparison: Mozart vs Your System

| Aspect | Mozart | Your deep_research.py | V1 Wiki Design |
|--------|--------|----------------------|----------------|
| **Report tone** | Declarative/encyclopedic | Professional/authoritative | (Needs discipline) |
| **Claim strength** | Implicit (citations exist) | Not shown | Planned (source count, etc.) |
| **Coverage metadata** | Not shown | Shown in logs, not report | Planned (header) |
| **Graph confidence** | Not shown (nodes look equal) | N/A (no graph yet) | Proposed (color-coding) |
| **Escape hatch** | Full extraction JSON | Raw files + logs | Evidence browser |
| **Risk level** | Medium (biographies less consequential) | Medium (reports used but questioned) | High (investigative journalism stakes) |

---

## Recommended V1 Approach

**Design Principle**: "Make uncertainty visible, not hidden"

### Technical Implementations

1. **Claim Storage** (database schema):
   ```sql
   Claim
   - confidence_score (0-1, from LLM extraction)
   - source_count (computed from evidence)
   - domain_diversity (computed from sources)
   - disambiguation_risk ("high" | "medium" | "low")
   ```

2. **Report Template** (synthesis prompt):
   - Force hedged phrasing for weak claims
   - Require coverage metadata in header
   - Include "Limitations" section (what we don't know)

3. **UI Elements**:
   - Claims table with sortable confidence columns
   - Entity pages with disambiguation warnings
   - Graph nodes color-coded by confidence
   - Snippet browser with "how many claims rely on this?" indicator

### Philosophical Stance (from V1 doc)

**Treat KG as "map of assertions", not "map of reality"**

This isn't just a technical mitigation - it's a UX philosophy:
- Labels should say "Claimed connections" not "Connections"
- Buttons should say "Show evidence for claim" not "Show facts"
- Reports should say "Sources assert" not "It is true that"

**Language Matters**: If you consistently use "assertion" language instead of "fact" language, you'll train yourself to stay epistemically humble.

---

## Final Assessment

**Risk Severity**: CRITICAL (corrupts investigative epistemology)

**V1 Mitigations Adequacy**: WEAK (if only using V1 doc proposals)
- 1-click snippet links: ✅ Helps but insufficient (requires active skepticism)
- Visual confidence cues: ✅ Good but needs more detail than "number of snippets"
- Philosophical stance: ✅ Necessary but not sufficient (humans forget philosophy under deadline pressure)

**Additional Recommendations**: ESSENTIAL
- Claim strength indicators (P0)
- Report phrasing discipline (P0)
- Coverage metadata (P1)
- Entity disambiguation confidence (P1)

**Bottom Line**: This risk is HARDER to mitigate than methodology risk because it requires fighting human cognitive biases (we WANT to believe clean authoritative reports). Technical solutions (strength indicators, hedged language, prominent limitations) help but aren't bulletproof. The real mitigation is **habits**: Force yourself to check claim strength before citing, always read "Limitations" section first, never trust single-source claims no matter how confidently stated.

**Practical Recommendation**: For first 3 months of V1 use, adopt explicit workflow rule:
- "Never cite a claim in external writing unless it has 3+ distinct sources OR I've manually verified the underlying evidence"
- This forces you to use strength indicators and snippet browser, building good habits
