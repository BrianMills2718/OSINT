# How the Deep Research System Works

**A conceptual guide to the architecture and intelligence behind coverage-based investigative research**

---

## OVERVIEW

This system performs **investigative research** using AI to intelligently explore a topic across multiple data sources. Unlike traditional search engines that return a single list of results, this system:

1. **Breaks down complex questions** into focused research angles
2. **Generates investigative hypotheses** for each angle
3. **Executes searches** across 12+ government, social, and web sources
4. **Analyzes coverage gaps** and creates intelligent follow-up tasks
5. **Synthesizes findings** into a comprehensive research report

**Philosophy**: Trust LLM intelligence over hardcoded rules. The system makes decisions based on context, not programmatic heuristics.

---

## THE RESEARCH FLOW

### Phase 1: Question Decomposition

**Input**: User's research question (e.g., "F-35 sales to Saudi Arabia")

**Process**:
1. LLM analyzes the question for **research angles** (not entity permutations)
2. Generates 3-5 **focused tasks**, each targeting a distinct aspect:
   - Government policy angle
   - Congressional oversight angle
   - Geopolitical implications angle
   - Official statements angle

**Key Intelligence**: The LLM understands that "US State Department policy" and "Congressional debate" are **different information dimensions**, not just different keyword combinations.

**Example Output**:
```
Task 0: US State Department F-35 fighter jet sale Saudi Arabia policy statements
Task 1: US Congress debate F-35 sale Saudi Arabia national security concerns
Task 2: F-35 sale Saudi Arabia impact Israel qualitative military edge
Task 3: Saudi Arabia official statements interest F-35 acquisition
```

**Why This Matters**: Traditional systems might create "F-35", "Saudi Arabia", "Israel" as separate queries (entity permutations). Our system creates **angle-based tasks** addressing policy, oversight, geopolitics, and official positions.

---

### Phase 2: Hypothesis Generation (Phase 3A)

**For each task**, the LLM generates **investigative hypotheses** - educated guesses about where information might exist and how to find it.

**Process**:
1. LLM analyzes the task and asks: "Where would this information realistically exist?"
2. Generates 1-5 hypotheses ranked by confidence and priority
3. Each hypothesis includes:
   - **Statement**: What we expect to find
   - **Reasoning**: Why this is likely
   - **Search Strategy**: Specific sources and search signals to use
   - **Expected Entities**: Who/what we expect to discover

**Example** (Task 1: Congressional debate):
```
Hypothesis 1 (90% confidence):
  Statement: Official congressional records will detail specific national security concerns
  Reasoning: Congressional debates on major arms sales are well-documented
  Search Strategy:
    - Sources: Brave Search, DVIDS
    - Signals: "F-35 Saudi Arabia Congress hearing", "Senate Foreign Relations Committee"
  Expected Entities: SFRC, House Foreign Affairs, DoD, State Department

Hypothesis 2 (80% confidence):
  Statement: Major news outlets will have reported on congressional debates
  Reasoning: Significant foreign policy issues get extensive media coverage
  Search Strategy:
    - Sources: Brave Search
    - Signals: "F-35 Saudi Arabia congressional opposition", "Senate debate arms sale"
  Expected Entities: NYT, WaPo, Reuters, Congressional members

Hypothesis 3 (65% confidence):
  Statement: Social media will contain real-time reactions and statements
  Reasoning: Twitter is a common platform for political commentary
  Search Strategy:
    - Sources: Twitter, Reddit, Discord
    - Signals: "#F35 Saudi Arabia Congress", "arms sale debate"
  Expected Entities: Congressional staffers, defense journalists, policy analysts
```

**Why This Matters**: Each hypothesis is a **different search strategy** targeting different types of sources (official records vs media vs social). This creates comprehensive coverage.

---

### Phase 3: Hypothesis Execution (Phase 3B/3C)

**Two execution modes**:

#### Mode 1: Parallel Execution (Phase 3B)
- Execute all hypotheses simultaneously
- Fast but may waste effort on low-yield hypotheses
- Used when: Speed matters more than efficiency

#### Mode 2: Sequential with Coverage Assessment (Phase 3C - Default)
- Execute hypotheses one at a time
- After each hypothesis, LLM analyzes coverage quality
- Stops early if coverage is sufficient
- Used when: Quality and efficiency matter

**Phase 3C Process** (Sequential with Coverage):
```
1. Execute Hypothesis 1
   → Found: 30 results, 5 new entities
   → LLM Assessment: Coverage 55%, incremental gain 100% (first hypothesis)
   → Decision: CONTINUE (significant gaps remain)

2. Execute Hypothesis 2
   → Found: 25 results, 8 new entities (3 duplicates from H1)
   → LLM Assessment: Coverage 75%, incremental gain 60%
   → Decision: CONTINUE (still finding new information efficiently)

3. Execute Hypothesis 3
   → Found: 15 results, 2 new entities (mostly duplicates)
   → LLM Assessment: Coverage 85%, incremental gain 20%
   → Decision: STOP (diminishing returns, sufficient coverage)

Final: 70 results from 3 hypotheses (saved 2 hypotheses)
```

**Coverage Metrics Analyzed**:
- **New vs duplicate results**: Are we still finding unique information?
- **New vs duplicate entities**: Are we discovering new actors/organizations?
- **Incremental gain**: How much did this hypothesis add beyond previous ones?
- **Time budget**: Do we have time for more exploration?

**Why This Matters**: The LLM makes **intelligent stopping decisions** based on actual coverage, not hardcoded limits like "always run 3 hypotheses" or "stop after 50 results."

---

### Phase 4: Source Selection & Execution

For each hypothesis, the LLM selects the **best sources** to query.

**Source Selection Process**:
1. LLM receives:
   - Hypothesis content
   - Available sources (12+ integrations)
   - Each source's capabilities and data types
2. LLM analyzes: "Which sources would have this type of information?"
3. Selects 2-5 sources with reasoning

**Example**:
```
Hypothesis: "Find official State Department policy statements"

LLM Selection:
  ✓ Brave Search - Official websites and news articles about policy
  ✓ Twitter - Real-time announcements from @StateDept
  ✓ Reddit - Community discussions linking to policy documents

  ✗ Discord - Unlikely to have official policy statements
  ✗ SAM.gov - Contract database, not policy statements
  ✗ ClearanceJobs - Job listings, not relevant

Reasoning: "Brave Search covers official government sites and news. Twitter
           captures real-time announcements. Reddit may have analysis linking
           to primary sources."
```

**Query Generation**:
Each selected source gets a **tailored query** optimized for that source's search syntax:
- **Brave Search**: Boolean query with site restrictions
- **Twitter**: Hashtags, accounts, and keywords
- **Reddit**: Subreddit-aware keyword combinations
- **Discord**: Exported message search (local)

**Parallel Execution**:
All selected sources execute **simultaneously** (asyncio), then results merge.

---

### Phase 5: Result Filtering & Relevance Scoring

**Problem**: Search APIs return noise. A query for "F-35 Saudi Arabia" might return articles about F-35 sales to UAE, or F-16 sales to Saudi Arabia.

**Solution**: LLM evaluates **each result individually** for relevance.

**Filtering Process**:
1. LLM receives batch of 20-60 results
2. For each result:
   - Reads title and snippet
   - Asks: "Does this directly address the research question?"
   - Decision: KEEP or REJECT with reasoning
3. Returns filtered results + interesting decision explanations

**Example Decisions**:
```
Result #7: "Congress Fails to Block Saudi Arms Sales"
  Snippet: "...air-to-air missiles approved despite opposition..."
  Decision: REJECT
  Reasoning: Mentions "air-to-air missiles" not F-35s specifically. Too generic.

Result #9: "US to sell F-35s to Saudi Arabia, Trump says"
  Snippet: "President announces largest defense sales agreement..."
  Decision: KEEP
  Reasoning: Title directly mentions F-35 and Saudi Arabia. Highly relevant.

Result #12: "India worried about F-35 sale to Saudi Arabia"
  Decision: REJECT
  Reasoning: About India's concerns, not US policy or congressional debate. Off-topic.
```

**Why This Matters**: Instead of getting 200 results with 80% noise, you get 40 highly relevant results. The LLM acts as an **intelligent filter**, not just a keyword matcher.

---

### Phase 6: Entity Extraction & Analysis

**Purpose**: Identify **who and what** appears in the results to understand the key actors and topics.

**Extraction Process**:
1. LLM reads all result titles/snippets
2. Extracts entities:
   - **People**: Donald Trump, Mohammed bin Salman, senators
   - **Organizations**: State Department, Lockheed Martin, Congress
   - **Locations**: Saudi Arabia, Israel, Washington DC
   - **Concepts**: Qualitative Military Edge, arms export control
3. Filters entities:
   - Keep: Specific actors directly involved
   - Remove: Generic terms ("United States"), unrelated entities

**Example** (F-35 Saudi Arabia):
```
Extracted (40 entities):
  People: Donald Trump, Mike Pompeo, MBS, Netanyahu, Lindsey Graham
  Orgs: State Dept, DSCA, Lockheed Martin, SFRC, AIPAC
  Locations: Saudi Arabia, Israel, Riyadh, Tel Aviv
  Concepts: QME, FMS, AECA, technology transfer

Filtered to (22 entities):
  ✓ Kept: Specific actors (Trump, Pompeo, specific senators)
  ✗ Removed: Generic ("United States", "Congress" without specificity)
```

**Why This Matters**: Entities inform **follow-up generation** - the LLM knows which actors are central to the story vs peripheral.

---

### Phase 7: Coverage Gap Analysis & Follow-Up Generation

**This is where the intelligence happens.**

After completing a task, the LLM analyzes:
1. **What did we find?** (results, entities, themes)
2. **What's missing?** (coverage gaps)
3. **Should we investigate further?** (if coverage < 95%)

**Coverage Gap Taxonomy** (7 types identified):

#### 1. Document Specificity Gaps
Pattern: General → Specific
```
Parent: "State Department policy statements"
Gap: We found statements, but not the actual authorization RECORDS
Follow-Up: "State Department F-35 Saudi Arabia Foreign Military Sales authorization records"
```

#### 2. Process/Timeline Gaps
Pattern: What → How
```
Parent: "Congressional debate on F-35 sale"
Gap: We know WHAT was debated, but not HOW authorization process works
Follow-Up: "F-35 Saudi Arabia authorization interagency review process Pentagon State Dept"
```

#### 3. Stakeholder Perspective Gaps
Pattern: Elite → Diverse voices
```
Parent: "Congressional debate" (government perspective)
Gap: Missing public sentiment and citizen voices
Follow-Up: "F-35 Saudi Arabia debate public sentiment social media"
```

#### 4. Hidden Influence Gaps
Pattern: Surface → Behind-the-scenes
```
Parent: "Congressional debate" (public discourse)
Gap: Missing lobbying efforts and commercial pressure
Follow-Up: "F-35 Saudi Arabia lobbying efforts defense contractors"
```

#### 5. Temporal Gaps
Pattern: Static → Dynamic
```
Parent: "Impact on Israel's military edge" (historical analysis)
Gap: Missing real-time speculation and future scenarios
Follow-Up: "F-35 Saudi Arabia social media reactions speculative scenarios"
```

#### 6. Framing Variation Gaps
Pattern: Narrow → Broad
```
Parent: "IMPACT of F-35 sale on Israel QME" (causal analysis)
Gap: Missing general discussions about QME without "impact" framing
Follow-Up: "F-35 sales Saudi Arabia Israel qualitative military edge"
```

#### 7. Strategic Depth Gaps
Pattern: What → Why
```
Parent: "Saudi Arabia statements of interest"
Gap: Missing deep analysis of WHY and strategic implications
Follow-Up: "F-35 Saudi Arabia sale detailed justifications strategic political implications"
```

**Follow-Up Generation Process**:
```
1. LLM receives:
   - Parent task query and results
   - Coverage score (e.g., 65%)
   - Entities discovered
   - Existing tasks (to avoid duplication)
   - Workload capacity

2. LLM analyzes coverage gaps:
   "We found State Department statements but not specific authorization records.
    We have congressional debate but not the procedural mechanics.
    We're missing public sentiment and lobbying influence.
    Coverage is 65% - significant gaps remain."

3. LLM generates 0-N follow-ups:
   Follow-Up 1: Authorization records (Document Specificity gap)
   Follow-Up 2: Interagency process (Process gap)
   Follow-Up 3: Public sentiment (Stakeholder gap)
   Follow-Up 4: Lobbying efforts (Hidden Influence gap)

4. Each follow-up gets hypotheses and executes (Phase 2-6 repeat)
```

**Why This Matters**: Follow-ups aren't **entity permutations** ("Donald Trump + parent query"). They're **intelligent gap-filling** based on what information is still missing.

---

### Phase 8: Deduplication

**Problem**: Different sources and hypotheses often return the same articles/documents.

**Solution**: URL-based deduplication across all tasks.

**Process**:
1. As results arrive, system tracks unique URLs
2. If URL seen before: Mark as duplicate, don't add to final results
3. Keep count for transparency

**Example**:
```
Total fetched: 3,052 results
Unique URLs: 637 results
Duplicates removed: 2,415 (79.1%)

Deduplication rate of 79% is normal and healthy - it means:
- Multiple hypotheses correctly identified the same important sources
- Different search strategies converged on key documents
```

**Why This Matters**: You get **comprehensive coverage** (12+ sources, 15 tasks) without overwhelming redundancy.

---

### Phase 9: Report Synthesis

**Process**:
1. LLM receives **all results** from all tasks
2. Groups by task for organization
3. For each task:
   - Summarizes key findings
   - Lists hypotheses explored
   - Shows results discovered
   - Notes entities extracted
4. Generates metadata:
   - Total tasks, results, entities
   - Coverage scores
   - Deduplication stats
   - Cost breakdown

**Output Format**:
```markdown
# Research Report: F-35 Sales to Saudi Arabia

**Summary**: Comprehensive investigation across 15 tasks, 637 unique results...

## Task 0: US State Department Policy Statements
**Hypotheses**: 3 explored
**Results**: 79 documents found
**Key Findings**: [LLM summary]

### Hypothesis 1: Official State Department releases (90% confidence)
- Strategy: Brave Search for official sites
- Results: 30 documents from state.gov, DSCA notifications
- Entities: Mike Pompeo, DSCA, State Department

[... continues for all tasks ...]

## Metadata
- Tasks: 15 (4 initial + 11 follow-ups)
- Results: 637 unique (79% deduplication)
- Entities: 22 discovered
- Cost: $0.23 (Gemini API)
- Duration: 47 minutes
```

---

## KEY ARCHITECTURAL DECISIONS

### 1. LLM Intelligence Over Hardcoded Rules

**Traditional Approach**:
```python
if entities_found >= 3 and total_results >= 5:
    skip_follow_ups = True
```

**Our Approach**:
```python
# LLM analyzes coverage gaps and decides
follow_ups = llm_analyze_coverage_and_generate_follow_ups(
    task_results, coverage_score, entities, workload
)
```

**Why**: Context matters. Sometimes 5 results is insufficient (complex topic). Sometimes 3 results is plenty (narrow question). Let the LLM judge based on **information quality**, not **arbitrary thresholds**.

---

### 2. Coverage-Based Follow-Ups (Not Entity Permutations)

**Old Bug**:
```python
# For each entity, create follow-up
for entity in entities:
    follow_up = f"{entity} {parent_task.query}"
# Result: "Donald Trump F-35 sales to Saudi Arabia" (useless)
```

**Fixed Approach**:
```python
# LLM identifies INFORMATION gaps
gaps = llm_analyze_coverage_gaps(task_results, coverage_score)
follow_ups = llm_generate_follow_ups_for_gaps(gaps)
# Result: "F-35 authorization interagency review process" (valuable)
```

**Why**: Adding entity names to queries adds **zero information value**. Identifying **missing information dimensions** (process, stakeholder perspectives, hidden influences) adds **high value**.

---

### 3. Hypothesis-Driven Search (Not Keyword Matching)

**Traditional Approach**:
```
Query: "F-35 Saudi Arabia"
Run on all sources
Hope for good results
```

**Our Approach**:
```
Hypothesis 1: "Congressional records will have official transcripts"
  → Query: Congressional hearing sites + specific committees
  → Sources: Brave Search (with site:congress.gov), DVIDS

Hypothesis 2: "Social media will have real-time reactions"
  → Query: Hashtags + official accounts + recent time filter
  → Sources: Twitter, Reddit

Hypothesis 3: "Think tanks will have strategic analysis"
  → Query: Policy analysis terms + think tank names
  → Sources: Brave Search (with site:csis.org, brookings.edu)
```

**Why**: Different information types exist in **different places** and require **different search strategies**. One-size-fits-all queries miss nuance.

---

### 4. Defense-in-Depth Timeouts

**Architecture**: 3 timeout layers

**Layer 1: LLM Call Timeout** (180s / 3 min)
```python
response = await llm_call(prompt, timeout=180)
```
- **Purpose**: Prevent hung API calls from consuming entire task time
- **Benefit**: If Gemini API hangs, timeout after 3 min and try fallback model

**Layer 2: Integration Timeout** (10-45s)
```python
results = await source.search(query, timeout=30)
```
- **Purpose**: Prevent slow data sources from blocking task
- **Benefit**: If SAM.gov is slow, timeout and continue with other sources

**Layer 3: Task Timeout** (1800s / 30 min)
```python
async with asyncio.timeout(1800):
    execute_task()
```
- **Purpose**: Catastrophic failure backstop (infinite retry loops)
- **Benefit**: Even if everything fails, task won't run forever

**Why**: **Defense-in-depth** - each layer catches different failure modes. Primary protection at LLM level (where hangs most likely), task timeout as last resort.

---

### 5. Jinja2 Prompt Templates (Not Inline Strings)

**Old Approach**:
```python
prompt = f"""
You are a research assistant analyzing {topic}.
Given these results: {json.dumps(results)}
Extract entities like {{"people": [...], "orgs": [...]}}
"""
```

**Problems**:
- JSON examples require escaping `{{` and `}}`
- Prompts mixed with code (hard to edit)
- No version control for prompt evolution

**Our Approach**:
```python
# Code
from core.prompt_loader import render_prompt
prompt = render_prompt("deep_research/entity_extraction.j2",
                       topic=topic, results=results)

# Template (prompts/deep_research/entity_extraction.j2)
You are a research assistant analyzing {{ topic }}.

Given these results:
{{ results | tojson(indent=2) }}

Extract entities in this format:
{"people": [...], "orgs": [...]}
```

**Benefits**:
- ✅ No escaping needed (JSON examples are literal)
- ✅ Prompts version-controlled separately
- ✅ Easy to edit (no Python knowledge required)
- ✅ Can A/B test prompts without code changes

---

## CONFIGURATION & EXTENSIBILITY

### All Limits Are Configurable

```yaml
# config_default.yaml
research:
  deep_research:
    max_tasks: 15                    # Maximum total tasks
    max_follow_ups_per_task: null    # null = unlimited, N = cap
    min_coverage_for_followups: 95   # Skip follow-ups if coverage >= %
    task_timeout_seconds: 1800       # Per-task timeout
    max_concurrent_tasks: 4          # Parallel execution limit

  hypothesis_branching:
    mode: "execution"                # off | planning | execution
    max_hypotheses_per_task: 5       # LLM decides 1-N, never exceeds this
    coverage_mode: true              # Sequential with coverage assessment

timeouts:
  llm_request: 180                   # LLM call timeout (3 min)
  api_request: 30                    # HTTP request timeout
```

**Philosophy**: User configures their quality/cost/speed preferences **upfront**, then walks away. System uses LLM intelligence **within** those constraints.

---

### Adding New Sources (5 Steps)

Want to add a new data source? Here's the complete workflow:

**1. Create Integration File**
```python
# integrations/government/newsource_integration.py
from core.database_integration_base import DatabaseIntegration

class NewSourceIntegration(DatabaseIntegration):
    @property
    def metadata(self):
        return DatabaseMetadata(
            id="newsource",
            name="New Source",
            category=DatabaseCategory.GOVERNMENT
        )

    async def is_relevant(self, question: str) -> bool:
        # LLM call: "Is this question relevant for New Source?"
        pass

    async def generate_query(self, question: str):
        # LLM call: "Generate query for New Source's search API"
        pass

    async def execute_search(self, params, api_key, limit):
        # HTTP request to New Source API
        # Return QueryResult with list of results
        pass
```

**2. Register in Registry**
```python
# integrations/registry.py
from integrations.government.newsource_integration import NewSourceIntegration

def _register_defaults(self):
    self._try_register("newsource", NewSourceIntegration)
```

**3. Add Configuration**
```yaml
# config_default.yaml
databases:
  newsource:
    enabled: true
    timeout: 30
```

**4. Add API Key** (if needed)
```bash
# .env
NEWSOURCE_API_KEY=your_key_here
```

**5. Test**
```python
# tests/test_newsource_live.py
import asyncio
from integrations.registry import registry

async def test():
    source = registry.get_instance("newsource")
    result = await source.execute_search({"query": "test"}, api_key, 10)
    print(f"Found {len(result.items)} results")

asyncio.run(test())
```

**That's it!** The source is now available to:
- LLM source selection (automatically considered)
- Hypothesis execution (used when relevant)
- Configuration system (can enable/disable, set timeouts)

---

## OBSERVABILITY

The system tracks **everything** for post-run analysis:

### Real-Time Output
```
[2025-11-19T09:34:13] RESEARCH_STARTED
[2025-11-19T09:34:18] TASK_CREATED: Task 0
[2025-11-19T09:34:18] TASK_CREATED: Task 1
🔬 Generating hypotheses for 2 tasks...
✓ Task 0: Generated 3 hypotheses
✓ Task 1: Generated 4 hypotheses
[2025-11-19T09:35:07] DECOMPOSITION_COMPLETE: 4 tasks
[2025-11-19T09:35:30] BATCH_STARTED: Executing 4 tasks in parallel
🔍 Searching 3 MCP sources: Twitter, Reddit, Discord
✓ Twitter: 15 results
📌 [FOLLOW_UP] Task 4 (parent: 0): US State Department F-35 authorization records
✓ Created 4 follow-up tasks for task 0
[2025-11-19T09:47:23] TASK_COMPLETED: Task 0 (79 results)
```

### Metadata Export
```json
{
  "research_question": "F-35 sales to Saudi Arabia",
  "execution_summary": {
    "tasks_executed": 14,
    "tasks_failed": 0,
    "total_results": 637,
    "total_entities": 22,
    "duration_minutes": 47.2
  },
  "hypotheses_by_task": {
    "0": [
      {"statement": "...", "confidence": 90, "priority": 1},
      {"statement": "...", "confidence": 75, "priority": 2}
    ]
  },
  "coverage_decisions_by_task": {
    "0": [
      {"coverage_score": 55, "incremental_gain": 100, "decision": "continue"},
      {"coverage_score": 75, "incremental_gain": 60, "decision": "continue"},
      {"coverage_score": 85, "incremental_gain": 20, "decision": "stop"}
    ]
  },
  "cost_breakdown": {
    "total_cost": 0.23,
    "by_model": {
      "gemini/gemini-2.5-flash": {"cost": 0.23, "calls": 47}
    }
  }
}
```

### Execution Log (JSONL)
```jsonl
{"event":"TASK_CREATED","task_id":0,"query":"...","timestamp":"..."}
{"event":"HYPOTHESIS_GENERATED","task_id":0,"hypotheses":4,"timestamp":"..."}
{"event":"SOURCE_SELECTION","sources":["Brave Search","Twitter"],"reasoning":"..."}
{"event":"TASK_COMPLETED","task_id":0,"results":79,"entities":12,"timestamp":"..."}
{"event":"FOLLOW_UP_CREATED","task_id":4,"parent":0,"query":"...","rationale":"..."}
```

**Use Cases**:
- **Debugging**: Why did Task 5 fail?
- **Optimization**: Which hypotheses yielded best results?
- **Cost Analysis**: Which LLM calls are most expensive?
- **Quality Review**: Did follow-ups address real gaps or create redundancy?

---

## DESIGN PHILOSOPHY PRINCIPLES

### 1. "No Hardcoded Heuristics"
❌ **Bad**: `if entities_found >= 3: skip_follow_ups()`
✅ **Good**: LLM analyzes coverage and decides based on information quality

### 2. "Full LLM Intelligence"
❌ **Bad**: Rule-based logic ("if X then Y")
✅ **Good**: Context-based decisions with reasoning

### 3. "Quality-First"
❌ **Bad**: Optimize for speed/cost by default
✅ **Good**: User configures quality/cost tradeoff, system optimizes within constraints

### 4. "User Configures Once, Walks Away"
❌ **Bad**: Require mid-run user input ("Continue? Yes/No")
✅ **Good**: All decisions automated within configured parameters

### 5. "Trust, But Verify"
❌ **Bad**: Blindly accept all search results
✅ **Good**: LLM evaluates each result for relevance, filters noise

---

## COMPARISON TO ALTERNATIVES

### Traditional Search Engines (Google, Bing)
**They give you**: Single query → List of 10 blue links
**We give you**: Multi-angle investigation → 15 tasks → 637 filtered results

**They use**: Keyword matching + PageRank
**We use**: Hypothesis generation + LLM filtering + Coverage analysis

**They stop**: After first page of results
**We stop**: When coverage is sufficient (LLM decision)

---

### Academic Research Tools (Google Scholar, ResearchGate)
**They focus on**: Academic papers and citations
**We focus on**: Government data, social media, news, AND academic sources

**They assume**: User knows exactly what to search for
**We assume**: User has a question and we decompose it intelligently

**They provide**: References
**We provide**: Synthesized research report

---

### Gemini Deep Research (Google)
**Similarity**: Both use LLM intelligence for iterative research
**Difference #1**: We integrate 12+ specialized sources (government DBs, social media)
**Difference #2**: We use hypothesis-driven search (not just web scraping)
**Difference #3**: We provide full observability (see every decision)
**Difference #4**: We're fully configurable (all limits adjustable)

---

## REAL-WORLD EXAMPLE WALKTHROUGH

**Query**: "F-35 sales to Saudi Arabia"

**Decomposition** → 4 tasks:
1. State Department policy
2. Congressional debate
3. Impact on Israel
4. Saudi official statements

**Task 1 Execution** (Congressional debate):
- **Hypothesis 1**: Congressional records (90% confidence)
  - Sources: Brave Search, DVIDS
  - Found: 33 results (hearing transcripts, committee reports)
  - Coverage: 55%

- **Hypothesis 2**: News media coverage (80% confidence)
  - Sources: Brave Search
  - Found: 25 results (NYT, WaPo, Reuters articles)
  - Coverage: 75% (+20% incremental)

- **Hypothesis 3**: Social media reactions (65% confidence)
  - Sources: Twitter, Reddit
  - Found: 15 results (senator tweets, Reddit discussions)
  - Coverage: 85% (+10% incremental)

- **Hypothesis 4**: Skipped (coverage sufficient at 85%)

**Coverage Gap Analysis**:
```
LLM Analysis:
"We found congressional debate records and media coverage, but we're missing:
 1. Specific HEARING TRANSCRIPTS (we have summaries, not verbatim records)
 2. PUBLIC SENTIMENT (we have elite discourse, not grassroots voices)
 3. LOBBYING EFFORTS (missing commercial pressure and advocacy groups)

 Coverage is 85% - several substantive gaps remain. Creating 3 follow-ups."
```

**Follow-Ups Generated**:
- **Task 6**: Congressional hearing transcripts (Document Specificity gap)
- **Task 7**: Public sentiment social media (Stakeholder Perspective gap)
- **Task 8**: Lobbying efforts defense contractors (Hidden Influence gap)

**Each follow-up** → Generates hypotheses → Executes → May create more follow-ups

**Final Output**:
- 15 tasks total (4 initial + 11 follow-ups)
- 637 unique results (79% deduplication)
- 22 entities discovered
- 47 minutes, $0.23 cost

---

## TECHNICAL STACK (High-Level)

**Language**: Python 3.12
**LLM**: Gemini 2.5 Flash (configurable, supports 100+ models via LiteLLM)
**Prompts**: Jinja2 templates (12 templates)
**Config**: YAML + Environment variables
**Integrations**: 12+ sources (government, social, web)
**Concurrency**: asyncio (parallel execution)
**Output**: Markdown report + JSON metadata + JSONL event log

---

## FUTURE ENHANCEMENTS (Not Yet Implemented)

### 1. Multi-Hop Reasoning
**Current**: Follow-ups based on parent task only
**Future**: Follow-ups analyze ALL previous tasks (cross-task synthesis)

### 2. Source Prioritization Learning
**Current**: LLM selects sources based on description
**Future**: Track which sources yield best results per query type, use historical data

### 3. Adaptive Timeout Adjustment
**Current**: Fixed timeouts (180s LLM, 1800s task)
**Future**: Adjust timeouts based on task complexity and historical performance

### 4. Result Ranking
**Current**: Results listed chronologically by task
**Future**: LLM ranks all results by relevance/importance, surfaces best first

### 5. Interactive Mode
**Current**: Fully automated (user walks away)
**Future**: Optional HITL checkpoints ("Before creating 8 follow-ups, confirm?")

---

## CONCLUSION

This system performs **investigative research** by combining:

1. **Intelligent decomposition** (angles, not entity permutations)
2. **Hypothesis-driven search** (targeted strategies per information type)
3. **Coverage-based follow-ups** (gap analysis, not hardcoded rules)
4. **LLM filtering** (relevance scoring, noise reduction)
5. **Defense-in-depth architecture** (timeouts, fallbacks, error handling)

**Core Philosophy**: Trust LLM intelligence to make context-aware decisions within user-configured constraints. No hardcoded heuristics.

**Result**: Comprehensive, multi-source research reports that would take human researchers hours or days to compile.

---

**For technical implementation details**, see:
- `prompts/deep_research/*.j2` - All LLM prompts
- `research/deep_research.py` - Core research engine (3800+ lines)
- `config_default.yaml` - All configurable parameters
- `integrations/` - Source integration implementations

**For architecture review**, see: `docs/archive/2025-11-19/architecture_review.md`
**For follow-up quality analysis**, see: `docs/archive/2025-11-19/followup_quality_analysis.md`

---

**END OF "HOW IT WORKS" GUIDE**
