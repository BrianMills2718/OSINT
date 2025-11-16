# Risk #4: Cost, Latency, and Scale Risk

**Severity**: MEDIUM
**Category**: Operational
**Date**: 2025-11-15

---

## The Problem

Deep research workflows:
- Call LLM many times
- Call search APIs many times
- May explode in cost if run aggressively

**Risks**:
1. **Bill shock**: High depth/breadth on many leads → $$$$
2. **Slow feedback**: Kills investigative flow (you're in the zone, system feels sluggish)

---

## Real-World Evidence

### Your deep_research.py Costs (Actual Data)

**Test Run** (test_clearancejobs_contractor_focused.py, 2025-11-13):
- Query: "federal cybersecurity contractor job opportunities"
- Duration: ~3 minutes
- Tasks: 3 completed
- Results: 69 total
- LLM calls: ~15-20 (task decomposition, source selection, relevance filtering, entity extraction, synthesis)

**Estimated Costs** (using Gemini 2.5 Flash + Sonnet 4):
- Gemini 2.5 Flash: $0.10-0.20 per run (extraction + source selection)
- Claude Sonnet 4: $0.50-1.00 per run (synthesis)
- Search APIs: $0 (Brave free tier, USAJobs free, ClearanceJobs scraped)
- **Total**: ~$0.60-1.20 per research run

**Extrapolated**:
- 10 investigations/month × 3 runs/investigation × $1/run = **$30/month**
- 50 investigations/month (heavy use) = **$150/month**

**Assessment**: Costs are REASONABLE for individual use, but could become painful at scale

### Latency Observations

**Test Run Timings** (from execution logs):
- Task decomposition: 10-15s
- Source selection (per task): 5-10s
- Query generation: 2-5s
- Search execution: 5-30s (varies by source, timeouts)
- Relevance filtering: 10-20s
- Entity extraction: 10-15s
- Synthesis: 10-20s

**Total**: 2-5 minutes per run (acceptable for deep research, NOT acceptable for quick lookup)

**Flow-Killer Example**:
- You're investigating "J-2 psychological warfare", find interesting mention of "Operation NIGHTFIRE"
- Want to quickly check: "What else mentions NIGHTFIRE?"
- Launch new research run: 3-minute wait
- **Cognitive cost**: You've lost the thread by the time results return

### From Mozart Investigation

**Mozart Costs** (inferred from architecture):
- Perplexity API: ~$0.10-0.30 per search
- Brave Search: Free tier (2,000 queries/month)
- Gemini 2.5 Flash: ~$0.05-0.15 per person extraction
- Claude Sonnet 4.5: ~$0.50-1.00 per biography prose

**Per-Biography Cost**: ~$1-2

**At Scale** (130 biographies):
- 130 × $1.50 = **$195** total (one-time)
- Ongoing: ~5-10 new biographies/month = **$10-15/month**

**Assessment**: Mozart's costs are SUSTAINABLE (not running hundreds of queries/day)

---

## Severity Assessment: MEDIUM

**Why Medium (Not High)**:
- **Predictable**: Costs are roughly linear with usage (not exponential surprise)
- **Controllable**: Can limit depth/breadth, cache results
- **Acceptable**: $50-150/month is reasonable for serious investigative work (compare to Lexis-Nexis subscriptions)

**But Not Low Because**:
- **Flow disruption**: 3-minute latency breaks investigative rhythm
- **Scaling ceiling**: 100 investigations/month = $300+, could limit usage

**When This Becomes Critical**:
- Newsroom with 10 journalists sharing system (10x usage = $1500/month)
- Real-time monitoring (hundreds of queries/day)
- Bulk historical analysis (re-run 1000 old investigations)

---

## V1 Doc Proposed Mitigations

1. **Depth/breadth presets**:
   - "quick scan", "standard", "deep dive"
   - Make knobs very visible per run

2. **Cache by URL**:
   - If source already in evidence table, don't re-summarize

3. **Limit parallelism**:
   - Don't run 20 deep dives at once; start with 1-2 concurrent

---

## Additional Mitigations

### Mitigation A: Cost Budgeting (Proactive)

**Per Lead / Per Run Configuration**:
```yaml
research_run:
  cost_budget: 2.00  # max $ per run
  time_budget: 300   # max 5 minutes
  depth_preset: "standard"  # quick | standard | deep
```

**Runtime Behavior**:
- Track LLM token usage + API calls
- Estimate running cost
- If approaching budget, warn user OR auto-downgrade (fewer tasks, shallower search)

**UI Display**:
```
Research Run #17
  Status: Running (2:14 elapsed)
  Cost so far: $1.23 / $2.00 budget
  [ Abort ] [ Extend budget ]
```

**Benefit**: No surprise bills, users learn cost/quality tradeoffs

### Mitigation B: Two-Tier Search Strategy (Fast + Deep)

**Problem**: 3-minute latency kills quick lookups

**Solution**: Dual-mode search

| Mode | Use Case | Latency | Cost | Depth |
|------|----------|---------|------|-------|
| **Quick** | "Does NIGHTFIRE appear anywhere?" | 10-30s | $0.10 | Simple keyword search → LLM summary |
| **Deep** | "Comprehensive investigation of NIGHTFIRE" | 3-5min | $1.00 | Full task decomposition → multi-source → synthesis |

**Quick Mode Implementation** (new):
```python
async def quick_search(query: str, max_results: int = 20):
    """Fast keyword search across existing evidence + one Brave API call."""
    # 1. Search existing evidence table (near-instant)
    local_results = db.query(f"SELECT * FROM evidence WHERE snippet_text ILIKE '%{query}%'")

    # 2. ONE Brave search (5-10s)
    web_results = await brave_search(query, limit=20)

    # 3. Simple LLM summary (10s)
    summary = await llm_summarize(local_results + web_results)

    return summary  # Total: 15-20 seconds
```

**Benefit**: Keeps investigative flow alive (quick checks don't require full research runs)

### Mitigation C: Aggressive Caching (Your Architecture Already Has Some)

**Current**: Raw file persistence saves results per task
**Enhancement**: URL-level caching with TTL

```python
@dataclass
class CachedSource:
    url: str
    content_hash: str
    fetched_at: datetime
    ttl_days: int = 30  # configurable
    extracted_entities: List[Dict]
    extracted_evidence: List[Dict]

# On new search:
if url in cache and cache[url].age < ttl_days:
    reuse_extraction()  # Skip LLM call
else:
    fetch_and_extract()
```

**Cost Savings**:
- Repeated searches for same sources: ~50% LLM cost reduction
- Entity extraction reuse: ~30% cost reduction

**Trade-off**: Stale data (30-day old extraction might miss new context)

---

## Implementation Priority

### Must-Have (P0)
1. **Depth presets** (V1 doc #1) - Already planned, simple config
2. **URL caching** (V1 doc #2) - ~3-4 hours implementation

### Should-Have (P1)
3. **Cost tracking + budget limits** (Mitigation A) - ~4-5 hours
4. **Quick search mode** (Mitigation B) - ~6-8 hours (new feature)

### Nice-to-Have (P2)
5. **Parallelism limits** (V1 doc #3) - Config-level, trivial
6. **Advanced caching** (Mitigation C) - Phase 2 optimization

---

## Open Questions

1. **What's the right cost/quality tradeoff?**
   - Hypothesis: $1-2 per deep run is acceptable, >$5 feels expensive
   - Test: Track user behavior (do they use "deep" preset or avoid it?)

2. **Does quick search mode satisfy 80% of lookups?**
   - Hypothesis: Most "I wonder if..." questions don't need full deep research
   - Test: Log quick vs deep mode usage ratio

3. **How much does caching actually save?**
   - Depends on source overlap across investigations
   - Test: Measure cache hit rate after 1 month of use

4. **What's the latency tolerance for investigative work?**
   - 3 minutes might be fine if you batch runs (start 3, go get coffee, review results)
   - Test: User feedback on flow disruption

---

## Recommended V1 Approach

**Design for Cost Transparency + Tiered Performance**:

1. **Every Research Run Shows**:
   ```
   Run #17: "Operation NIGHTFIRE investigation"
   Duration: 3:24
   Cost: $1.67 (Gemini: $0.42, Sonnet: $1.25, APIs: $0)
   Results: 47 sources, 12 entities
   ```

2. **Preset Configurations** (user-visible):
   - **Quick** ($0.25, 1min): Keyword search + summary (for lookups)
   - **Standard** ($1.00, 3min): 3-5 tasks, moderate depth (default)
   - **Deep** ($3.00, 10min): 8-10 tasks, high depth (comprehensive)

3. **Budget Alerts**:
   - Lead dashboard shows monthly spend
   - Warning if approaching monthly budget
   - Option to set hard limits

4. **Caching Strategy**:
   - Cache evidence extraction (30-day TTL)
   - Cache entity extraction (30-day TTL)
   - Always re-run synthesis (context-dependent)

**Benefit**: Users understand cost/performance tradeoffs, system stays responsive for common cases

---

## Final Assessment

**Risk Severity**: MEDIUM (annoying but manageable)

**V1 Mitigations Adequacy**: GOOD (if implemented)
- Presets: ✅ Address cost control
- Caching: ✅ Address repeated work
- Parallelism limits: ✅ Prevent runaway costs

**Additional Recommendations**: HELPFUL (P1)
- Cost budgeting + tracking
- Quick search mode (for flow preservation)

**Bottom Line**: This risk is **operational not existential**. Unlike methodology/epistemic/extraction risks (which corrupt your investigative process), cost/latency risks just make the tool more expensive/slower. Acceptable mitigations:
- **For cost**: Set budgets, track spending, use presets
- **For latency**: Quick search mode for lookups, batch deep runs, aggressive caching

The key is **transparency** (show cost/time per run) and **tiered performance** (not every question needs deep research).
