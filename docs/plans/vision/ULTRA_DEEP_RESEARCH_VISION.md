# Ultra Deep Research Vision

**Status**: Future concept (deferred)
**Created**: 2025-10-24
**Priority**: Low (after Phase 1.5 complete)

---

## Overview

**UltraDeepResearch** represents the next-generation investigative research system beyond SimpleDeepResearch. This document outlines advanced capabilities to be considered for future development.

**Important Note**: This is a **vision document**, not an implementation plan. Many of these features may never be implemented, or may be replaced by better approaches as AI capabilities evolve.

---

## Current Research System Hierarchy

### Level 1: Quick Search (apps/ai_research.py)
**Engine**: ParallelExecutor
**Speed**: 10-30 seconds
**Use case**: Fast multi-database queries

**Capabilities**:
- AI selects relevant databases from registry
- Parallel search across selected sources
- Basic summarization

**Limitations**:
- No iteration or refinement
- No entity tracking
- Single-pass execution

---

### Level 2: SimpleDeepResearch (research/deep_research.py) - CURRENT
**Engine**: Task decomposition + AdaptiveSearchEngine
**Speed**: 5-30 minutes (configurable)
**Use case**: Complex multi-part investigations

**Capabilities**:
- Task decomposition (3-5 subtasks)
- Multi-phase adaptive search per task
- Web search integration (Brave Search API)
- Entity discovery and co-occurrence tracking
- Follow-up task generation
- Retry logic with query reformulation
- Comprehensive report synthesis

**Limitations**:
- Sequential task execution (slow)
- Simple co-occurrence entity tracking (no semantic relationships)
- In-memory only (no persistent knowledge)
- No hypothesis testing
- No source credibility evaluation
- No contradiction detection

---

### Level 3: AdvancedDeepResearch (Phase 1.5 Week 5-8) - PLANNED
**Engine**: SimpleDeepResearch + PostgreSQL Knowledge Graph
**Speed**: 2-10 minutes (parallel tasks)
**Use case**: Investigations that build on accumulated knowledge

**Planned improvements**:
- **Parallel task execution** (5-10x faster)
- **PostgreSQL knowledge graph** (Wikibase-compatible schema)
- **Persistent entity relationships** (learn from previous investigations)
- **Semantic relationship extraction** (LLM identifies actual relationships, not just co-occurrence)
- **Knowledge reuse** ("What do we already know about entity X?")

**Still limited by**:
- No hypothesis testing
- No source credibility scoring
- No contradiction detection/resolution
- Uses standard LLMs (gpt-5-mini, gpt-4)

---

### Level 4: UltraDeepResearch - FUTURE VISION

**Deferred indefinitely** - SimpleDeepResearch and AdvancedDeepResearch are sufficient for investigative journalism use cases.

This section documents potential advanced features for future consideration.

---

## Potential Advanced Features

### 1. Hypothesis-Driven Investigation

**Concept**: Instead of open-ended search, generate testable hypotheses and design experiments to evaluate them.

**How it would work**:
```python
# Generate hypotheses from research question
hypotheses = llm.generate_hypotheses(question)
# Example hypotheses:
# - "JSOC and CIA collaborate on Title 50 operations"
# - "Title 50 authority allows JSOC to operate under CIA command"
# - "Overlap exists but agencies remain independent"

# For each hypothesis, design tests
for hypothesis in hypotheses:
    tests = llm.design_tests(hypothesis)
    # Example tests:
    # - Search for joint operations documents
    # - Look for congressional oversight reports mentioning both
    # - Find legal analyses of Title 50 authority

    results = execute_tests(tests)
    evidence = evaluate_evidence(results, hypothesis)

    # Update belief with confidence level
    update_belief(hypothesis, evidence)
    # Example: "JSOC/CIA collaboration: 85% confidence based on 12 sources"

# Synthesize final report with confidence levels
report = synthesize_with_uncertainty(hypotheses, evidence)
```

**Benefits**:
- More structured investigation
- Explicit uncertainty quantification
- Better handling of conflicting evidence

**Challenges**:
- Requires sophisticated LLM prompting
- May miss unexpected findings (hypothesis bias)
- Computationally expensive (many LLM calls)

---

### 2. Source Credibility Scoring

**Concept**: Evaluate reliability of different sources and weight results accordingly.

**How it would work**:
```python
source_credibility = {
    "sam.gov": 0.95,           # Official government database
    "dvids": 0.90,              # Official military media
    "usajobs": 0.95,            # Official federal jobs
    "clearancejobs": 0.70,      # Commercial job board
    "brave_search": 0.50,       # Open web (varies by domain)
    "reddit": 0.30,             # Social media (low credibility)
    "4chan": 0.10               # Anonymous forum (very low)
}

# For claims requiring high confidence, require corroboration
claim = "JSOC conducted operation X in country Y"
sources_supporting = find_sources_for_claim(claim)

if all(source.credibility < 0.5 for source in sources_supporting):
    flag_as_unverified(claim)
elif sum(source.credibility for source in sources_supporting) > 1.5:
    mark_as_verified(claim)
```

**Benefits**:
- Reduces misinformation
- Prioritizes authoritative sources
- Flags unverified claims

**Challenges**:
- Credibility is context-dependent
- Authoritative sources can be wrong
- May miss important open-source intelligence

---

### 3. Contradiction Detection & Resolution

**Concept**: Identify conflicting information and investigate to resolve contradictions.

**How it would work**:
```python
# Find contradictions across all results
contradictions = llm.find_contradictions(all_results)
# Example: Source A says "2015", Source B says "2016"

for contradiction in contradictions:
    # Investigate deeper
    clarification_tasks = llm.design_clarification_tasks(contradiction)
    # Example tasks:
    # - Search for official timeline
    # - Look for corrections or updates
    # - Check original source documents

    evidence = execute_tasks(clarification_tasks)

    # Try to resolve
    resolution = llm.resolve_contradiction(contradiction, evidence)
    # Outcomes:
    # - "Resolved: Event occurred in 2015, source B corrected in later update"
    # - "Unresolved: Conflicting accounts, cannot verify"
    # - "False contradiction: Sources refer to different events"
```

**Benefits**:
- Improves accuracy
- Identifies errors in sources
- Provides more reliable reporting

**Challenges**:
- Expensive (many additional searches)
- May not always be resolvable
- Can introduce investigation bias

---

### 4. Multi-Agent Collaboration

**Concept**: Specialized agents collaborate on different aspects of investigation.

**How it would work**:
```python
agents = {
    "Researcher": GeneralistAgent(),       # Broad search, task decomposition
    "Analyst": AnalyticalAgent(),          # Deep analysis of findings
    "Fact-Checker": VerificationAgent(),   # Cross-reference claims
    "Legal-Expert": LegalAgent(),          # Analyze legal documents
    "OSINT-Specialist": OSINTAgent(),      # Open-source intelligence
    "Synthesizer": ReportAgent()           # Final report generation
}

# Agents communicate and collaborate
findings = await agents["Researcher"].search(question)
osint_findings = await agents["OSINT-Specialist"].deep_dive(findings)
analysis = await agents["Analyst"].analyze(findings + osint_findings)
legal_context = await agents["Legal-Expert"].analyze_legal_aspects(analysis)
verified = await agents["Fact-Checker"].verify(analysis, legal_context)
report = await agents["Synthesizer"].synthesize(verified)
```

**Benefits**:
- Specialized expertise for different domains
- Parallel execution of different investigation types
- More thorough analysis

**Challenges**:
- Complex coordination logic required
- Expensive (multiple LLM instances)
- Risk of conflicting agent outputs

---

### 5. Iterative Self-Improvement

**Concept**: System critiques its own investigation and fills gaps.

**How it would work**:
```python
# Initial investigation
report_v1 = await engine.research(question)

# Self-critique
gaps = llm.identify_gaps(report_v1)
# Example gaps:
# - "No information about funding sources"
# - "Missing timeline of key events"
# - "Unclear relationship between entities A and B"

weaknesses = llm.identify_weaknesses(report_v1)
# Example weaknesses:
# - "Relies heavily on single source type"
# - "No verification of claim X"
# - "Contradictory statements not addressed"

# Fill gaps
additional_tasks = llm.design_gap_filling_tasks(gaps)
new_findings = execute_tasks(additional_tasks)

# Address weaknesses
verification_tasks = llm.design_verification_tasks(weaknesses)
verification_results = execute_tasks(verification_tasks)

# Re-synthesize with improvements
report_v2 = llm.re_synthesize(report_v1, new_findings, verification_results)

# Optional: Iterate until quality threshold met
if quality(report_v2) < threshold and iterations < max_iterations:
    report_v3 = self_improve(report_v2)
```

**Benefits**:
- Higher quality reports
- Systematic gap filling
- More thorough investigations

**Challenges**:
- Very expensive (multiple full investigation cycles)
- Diminishing returns after 1-2 iterations
- May overcomplicate simple questions

---

### 6. Tool Use / Actions

**Concept**: System can use tools beyond search (calculators, code execution, data analysis).

**How it would work**:
```python
tools = {
    "calculate": lambda expr: eval(expr),
    "code_execute": execute_python_safely,
    "data_analyze": analyze_csv,
    "timeline_build": build_timeline,
    "network_graph": build_network_graph,
    "statistical_test": run_statistical_test
}

# During research, agent decides when to use tools
if llm.detect_needs_calculation(text):
    result = tools["calculate"]("...")

if llm.detect_needs_timeline(findings):
    timeline = tools["timeline_build"](findings)

if llm.detect_needs_network_analysis(entities):
    graph = tools["network_graph"](entities)
```

**Benefits**:
- More accurate quantitative analysis
- Visual representations (timelines, graphs)
- Programmatic data processing

**Challenges**:
- Security risks (code execution)
- Complex tool selection logic
- Tool output may not integrate well with narrative

---

### 7. Vector Memory + Semantic Search

**Concept**: Store all findings in vector database for semantic similarity search.

**How it would work**:
```python
# During investigation, store everything
for result in findings:
    embedding = embed(result.text)
    vector_db.store(
        embedding=embedding,
        content=result,
        metadata={
            "source": result.source,
            "timestamp": result.timestamp,
            "investigation_id": investigation.id,
            "entities": result.entities
        }
    )

# Future investigations can search semantically
similar_findings = vector_db.search(
    query="NSA surveillance programs",
    k=10,
    filter={"source": "gov_db"}  # Optional filtering
)

# "What have we learned about X across all investigations?"
knowledge = vector_db.search(
    query="JSOC operations",
    k=50
)
```

**Benefits**:
- Reuse findings across investigations
- Semantic search (better than keyword)
- Build institutional knowledge over time

**Challenges**:
- Storage costs for large vector DBs
- Embedding quality varies by model
- Privacy concerns (storing sensitive research)

---

## Model Selection Strategy

### Current Approach (SimpleDeepResearch)
**Model**: gpt-5-mini
**Why**: Best balance of cost, speed, and quality

**Performance**:
- Cost: ~$0.50 per investigation
- Speed: 5-30 minutes
- Quality: Excellent for most investigative tasks

### Alternative: o1/o3 Models
**Status**: NOT RECOMMENDED
**Reason**: gpt-5-mini is better and cheaper

**Why o1/o3 are inferior to gpt-5-mini**:

| Feature | gpt-5-mini | o1/o3 |
|---------|-----------|-------|
| **Cost** | ~$0.50/investigation | ~$5-15/investigation (10-30x more expensive) |
| **Speed** | Fast | Slow (extended reasoning) |
| **Quality** | Excellent | Marginally better for some tasks |
| **API compatibility** | Full compatibility | Limited (no streaming, no function calling in o1) |
| **Use case** | General intelligence | Specialized reasoning (math, logic) |
| **Verdict** | **PREFERRED** | **NOT RECOMMENDED** |

**When o1/o3 might make sense**:
- Complex mathematical reasoning
- Formal logic problems
- Code verification/debugging
- Scientific hypothesis generation

**For investigative journalism**:
- gpt-5-mini is superior (general intelligence, speed, cost)
- o1/o3 extended reasoning doesn't add value for this use case
- Stick with gpt-5-mini for all investigation tasks

---

## Implementation Priority

**IF we ever implement UltraDeepResearch features** (unlikely), prioritize in this order:

1. **Parallel task execution** (Phase 1.5) - HIGHEST ROI
   - 5-10x speedup
   - Minimal complexity
   - **Status**: PLANNED for AdvancedDeepResearch

2. **Knowledge graph** (Phase 1.5) - HIGH ROI
   - Persistent entity relationships
   - Knowledge reuse across investigations
   - **Status**: PLANNED for AdvancedDeepResearch

3. **Source credibility scoring** - MEDIUM ROI
   - Improves accuracy
   - Reduces misinformation
   - Moderate complexity

4. **Contradiction detection** - MEDIUM ROI
   - Higher quality reports
   - Expensive (additional searches)

5. **Hypothesis testing** - LOW ROI
   - More structured, but may miss serendipitous findings
   - Complex to implement well

6. **Multi-agent collaboration** - LOW ROI
   - High complexity
   - Expensive
   - Unclear benefits over single sophisticated agent

7. **Tool use** - LOW ROI (for journalism)
   - Useful for quantitative analysis
   - Security concerns
   - Most journalism tasks don't need it

8. **Vector memory** - LOW ROI (for now)
   - PostgreSQL graph already provides knowledge persistence
   - Additional complexity
   - Consider only after graph DB proves insufficient

9. **Iterative self-improvement** - VERY LOW ROI
   - Expensive (multiple investigation cycles)
   - Diminishing returns
   - Human review is cheaper and better

---

## Decision: Defer UltraDeepResearch Indefinitely

**Recommendation**: DO NOT implement UltraDeepResearch features beyond what's already planned for AdvancedDeepResearch.

**Rationale**:

1. **SimpleDeepResearch is sufficient** for investigative journalism use cases
2. **AdvancedDeepResearch** (parallel + knowledge graph) addresses biggest limitations
3. **Cost/benefit ratio poor** for most UltraDeepResearch features
4. **gpt-5-mini already optimal** - no need for o1/o3 or other specialized models
5. **Complexity risk** - advanced features may reduce reliability

**What we're building instead**:
- Phase 1.5: AdvancedDeepResearch (parallel + knowledge graph)
- Focus on reliability, speed, and knowledge accumulation
- Human journalists remain in the loop for final synthesis and verification

---

## When to Revisit This Document

Consider UltraDeepResearch features only if:

1. **Team grows beyond 10 people** (institutional knowledge becomes critical)
2. **AI capabilities dramatically improve** (e.g., new reasoning paradigms)
3. **User feedback demands specific features** (e.g., "we need timeline generation")
4. **AdvancedDeepResearch proves insufficient** after 6+ months production use

Otherwise: **Keep it simple. SimpleDeepResearch + AdvancedDeepResearch are enough.**

---

## Conclusion

**UltraDeepResearch is a vision, not a plan.**

The current research system hierarchy is well-designed:
- **Quick Search**: Fast, parallel, good enough for most questions
- **SimpleDeepResearch**: Thorough, task decomposition, entity tracking
- **AdvancedDeepResearch** (coming): Parallel + knowledge graph

No need to go beyond this. Focus on:
1. Completing Phase 1.5 (adaptive search + knowledge graph)
2. Production deployment and user feedback
3. Reliability and operational stability

**Don't build UltraDeepResearch unless proven necessary.**
