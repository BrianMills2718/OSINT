# Risk #3: Coverage & Bias Risk - Silent Gaps

**Severity**: HIGH
**Category**: Data Quality / Completeness
**Date**: 2025-11-15

---

## The Problem

Your system's worldview depends on:
- Which search API hits (Brave, Tavily, Firecrawl)
- Which countries/languages it's good at
- Which sites block bots

**Risks**:
1. **Search API bias**: Under-represent certain languages, regions, fringe sites; opaque ranking
2. **Robots/anti-bot**: Some important sources unreachable
3. **Silent gaps**: System rarely says "I failed to search in this direction" - just shows report

---

## Real-World Evidence

### Your deep_research.py Test Runs

**Observed Pattern** (from test_clearancejobs_contractor_focused.py, 2025-11-13):
- Query: "federal cybersecurity contractor job opportunities"
- Results: 69 total (USAJobs: ~20, ClearanceJobs: ~40, Brave Search: ~9)

**Coverage Gaps Visible in Test Output**:
- **Geographic**: 100% US-centric (no international results despite "federal" being ambiguous)
- **Source diversity**: 2 job databases + web search (no LinkedIn, Glassdoor, Indeed direct APIs)
- **Language**: 100% English (no Spanish, Arabic, etc. despite federal linguist jobs existing)

**Silent Gap Example**:
- SAM.gov integration exists but wasn't selected for "job opportunities" query
- No indication in report that contract data was available but not used
- User wouldn't know unless they read execution logs

### From Mozart Investigation

**Mozart's Search Strategy** (MOZART_TECHNICAL_README.md lines 120-160):
- **Primary**: Perplexity API (LLM-enhanced search)
- **Secondary**: Brave Search API (fallback/augmentation)
- **Tertiary**: Web scraping with Playwright (for specific pages)

**Observed Coverage**:
- 130+ person biographies created (all English, all US/UK focused)
- No evidence of non-English sources
- Heavy reliance on .mil, .gov, mainstream news

**Inference**: Mozart has same coverage bias (but it's acceptable for their use case - English-language UFO/disclosure community is predominantly US/UK)

---

## Severity Assessment: HIGH

**Why High**:
- **Invisible failure mode**: You won't know what you don't know
- **Systematic bias**: Same gaps appear across all investigations (e.g., always missing non-English sources)
- **Compounding with other risks**: If methodology risk makes you miss outliers AND coverage risk means outliers aren't even searched for... double failure

**But Not Critical Because**:
- **Detective work inherently incomplete**: You expect gaps (unlike epistemic risk where you're fooled into false confidence)
- **Partially mitigatable**: Can add manual seed URLs, expand APIs

**Concrete Example**:

**Investigation**: "J-2 psychological warfare programs"

**What Search APIs Return**:
- 80% US official sources (.mil, .gov, think tanks)
- 15% mainstream news
- 5% academic papers

**What's Missing** (silently):
- Foreign government reports (Russian, Chinese assessments of US psyops)
- Whistleblower forums (vet/intel community discussions)
- Paywalled archives (JSTOR, ProQuest full-text)
- Dark web / leaked documents (WikiLeaks, DocumentCloud)

**Report Appears Complete**: "Based on 50 sources, J-2 involvement in psyops is well-documented..."

**Reality**: Based on 50 PUBLIC, ENGLISH, BOT-ACCESSIBLE sources. Actual evidence space is 100x larger.

---

## V1 Doc Proposed Mitigations

1. **Log and display search queries + source counts**:
   - Per ResearchRun: list of queries, counts per query, domains found

2. **Manual seed URLs**:
   - Lead UI accepts "Also crawl these 3 specific URLs"

3. **Flag thin runs**:
   - If run yields < N sources, mark "low coverage"

---

## Additional Mitigations

### Mitigation A: Coverage Metadata Dashboard (Prominent)

**Every Report Header Shows**:
```markdown
## Research Coverage

**Search Executed**:
- APIs used: Brave Search, Tavily
- Queries: 12 distinct queries
- Total results: 127 URLs
- Domains: .mil (45), .gov (22), news (30), think tanks (18), other (12)

**Coverage Limitations**:
- Geographic: 95% US-centric
- Language: 100% English
- Access: Public web only (no paywalled archives, leaked docs, closed forums)
- Time range: 2001-2025 (weighted toward recent, limited pre-2001 indexing)

**Gaps Identified** (by topic):
- Foreign assessments: LOW (2 sources, both secondhand)
- Classified program references: MEDIUM (18 sources, mostly oblique)
- Whistleblower accounts: LOW (0 sources)

**Confidence**: MODERATE (sufficient for overview, insufficient for comprehensive investigation)
```

**Benefit**: Makes gaps VISIBLE instead of hidden

### Mitigation B: Multi-API Strategy (Your Architecture Already Has This)

**Your deep_research.py** (lines 820-900):
- Already queries multiple sources per task (USAJobs, ClearanceJobs, Twitter, Reddit, Discord, Brave)
- Integration registry allows easy addition of new sources

**Enhancement**: Add coverage-based source selection
- Task decomposition suggests which sources matter for each subtask
- If critical source unavailable (rate limited, API down), flag it prominently

**Example**:
```
Task 3: "Find leaked documents mentioning J-2 psychological warfare"
  Selected sources: DocumentCloud, WikiLeaks, Brave Search
  Status: DocumentCloud API unavailable ❌ → Coverage gap for leaked docs
  Fallback: Manual URL seeds recommended
```

### Mitigation C: "Known Unknowns" Tracking

**Store in Database**:
```sql
CoverageGap
- research_run_id
- gap_type         -- "paywalled", "foreign_language", "bot_blocked", "api_unavailable"
- description      -- "No access to JSTOR full-text"
- estimated_impact -- "low" | "medium" | "high"
- mitigation_suggestion  -- "Add manual seed URLs for key papers"
```

**Report Section**:
```markdown
## Known Coverage Gaps

1. **Paywalled archives** (Impact: MEDIUM)
   - JSTOR, ProQuest, LexisNexis not accessible
   - Mitigation: Manual search via university library access

2. **Foreign language sources** (Impact: LOW for this query)
   - Russian/Chinese assessments of US psyops not searched
   - Mitigation: Use Google Translate + manual review if needed

3. **Bot-blocked forums** (Impact: HIGH)
   - Reddit's new API restrictions blocked 3 relevant subreddits
   - Mitigation: Manual browsing OR Playwright scraper (slow)
```

**Benefit**: Turns silent gaps into explicit "todo" list

---

## Implementation Priority

### Must-Have (P0)
1. **Coverage metadata in report** (Mitigation A) - ~2 hours
2. **Query/domain logging** (V1 doc #1) - Already planned

### Should-Have (P1)
3. **Manual seed URL UI** (V1 doc #2) - ~3 hours
4. **Flag thin runs** (V1 doc #3) - ~1 hour
5. **Known unknowns tracking** (Mitigation C) - ~4 hours

### Nice-to-Have (P2)
6. **Multi-API orchestration** (Mitigation B) - Partially exists, enhancement deferred

---

## Open Questions

1. **How much coverage is "enough"?**
   - Varies by investigation type (structured data: low threshold, deep dive: high threshold)
   - Test: Define heuristics per investigation category

2. **Will you actually use manual seed URLs?**
   - Hypothesis: You'll forget unless workflow prompts you
   - Test: Track manual seed usage in first 3 months

3. **Can LLM identify coverage gaps automatically?**
   - Idea: Ask synthesis LLM "what evidence sources are missing?"
   - Test: Compare LLM-generated gap list to your manual assessment

---

## Recommended V1 Approach

**Make Coverage Transparency Core Feature** (not afterthought):

1. **Every Report**: Coverage metadata header (mandatory, not optional)
2. **Every ResearchRun**: Store coverage diagnostics (domains, counts, gaps)
3. **Lead Dashboard**: Show coverage score (GREEN: 100+ sources, YELLOW: 30-100, RED: <30)
4. **Manual Seed Workflow**: Prominent "Add seed URLs" button on every Lead page

**Habit Building**: For first 10 investigations, force yourself to:
- Read "Coverage Limitations" BEFORE reading findings
- Add ≥3 manual seed URLs per investigation
- Document at least 1 known gap in "Known Unknowns" section

**This builds skepticism habit** (counteracts epistemic risk)

---

## Final Assessment

**Risk Severity**: HIGH (invisible bias/gaps)

**V1 Mitigations Adequacy**: MODERATE
- Query logging: ✅ Helps with transparency
- Manual seeds: ✅ Good escape hatch
- Thin run flagging: ✅ Simple signal
- Missing: Known unknowns tracking, coverage scoring, prominent gap warnings

**Additional Recommendations**: IMPORTANT (P1)
- Coverage metadata header (must-have)
- Known unknowns database + UI
- Coverage scoring per Lead

**Bottom Line**: This risk is TOLERABLE if transparent. The danger isn't that coverage is incomplete (all research is incomplete) - the danger is SILENT incompleteness. If every report says "here's what we found AND here's what we couldn't access", you stay epistemically honest. The V1 mitigations are good if fully implemented + made prominent (not buried in appendix).
