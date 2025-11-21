# Timeout Architecture - Simplified Approach

**Last Updated**: 2025-11-21
**Philosophy**: LLM intelligence decides when to stop, not arbitrary time limits

---

## Design Principles

1. **LLM decides saturation** (primary exit condition)
2. **User configures limits upfront** (not hardcoded)
3. **Simple, layered protection** (not complex decision trees)

---

## Architecture Layers

### **Layer 1: LLM Call Timeout (180s)**
**Purpose**: API failure protection
**When it triggers**: Individual LLM API call hangs or runs too long
**Action**: Fail fast, log error, retry or skip

**Example**:
```python
# In llm_utils.py
response = await acompletion(
    model="gpt-4",
    messages=[...],
    timeout=180  # 3 minutes
)
```

**Why 180s?**:
- Most LLM calls complete in 5-30s
- 180s catches genuine API hangs
- Prevents single call from blocking research

---

### **Layer 2: User-Configured Source Limits**
**Purpose**: Prevent individual source from running forever
**When they trigger**: Source saturation loop hits user-defined limits
**Action**: Log limit reached, move to next source

**Configuration**:
```python
engine = SimpleDeepResearch(
    max_queries_per_source={
        'SAM.gov': 10,      # Government: detailed, allow more queries
        'DVIDS': 5,         # Military news: moderate
        'Twitter': 3,       # Social: noisy, fewer queries
        'Reddit': 3,
        'Brave Search': 5
    },
    max_time_per_source_seconds=300  # 5 min per source max
)
```

**Primary Exit**: LLM saturation decision ("SATURATED")
**Secondary Exit**: Reach max_queries limit
**Tertiary Exit**: Reach time limit

**Example Loop**:
```python
while True:  # No hardcoded loop count
    query = await generate_query(history)
    results = await execute_query(source, query)
    filtered = await filter_results(results)

    # PRIMARY: LLM decides
    saturation = await check_saturation(filtered, history)
    if saturation['decision'] == 'SATURATED':
        logger.info(f"Source saturated: {saturation['reasoning']}")
        break

    # SECONDARY: User-configured limit
    if len(history) >= config.max_queries_per_source[source]:
        logger.warning(f"Reached max_queries limit: {max_queries}")
        break

    # TERTIARY: User-configured time limit
    if elapsed_time > config.max_time_per_source_seconds:
        logger.warning(f"Reached time limit: {max_time}s")
        break
```

---

### **Layer 3: Total Research Budget**
**Purpose**: Cap entire research run
**When it triggers**: Total elapsed time exceeds user budget
**Action**: Graceful shutdown, save results collected so far

**Configuration**:
```python
engine = SimpleDeepResearch(
    max_time_minutes=120  # 2 hours total
)
```

**Checked**: Between tasks, between hypotheses
**Granularity**: Won't interrupt mid-query, waits for natural breakpoints

---

## What We DON'T Have (Intentionally)

### ❌ Task-Level Timeout (Removed)
**Why removed**: Redundant middle layer without clear value

**Protection already provided by**:
- Source-level limits (prevent individual source runaway)
- Total budget (prevent research runaway)
- LLM saturation (intelligent task completion)

**Example showing redundancy**:
- Task has 5 hypotheses × 8 sources = 40 source executions
- Each source limited to 10 queries or 5 min = max 200 min possible
- But total budget is 120 min, so stops at 120 min anyway
- Task timeout at 30 min would artificially cut off investigation

**Philosophy violation**: If Task 1 is high priority and needs 60 minutes to properly saturate, why stop at 30? LLM should decide task completion via saturation, not arbitrary time limit.

---

## Decision Flow

```
User Configures Budget
├─ max_time_minutes: 120
├─ max_queries_per_source: {SAM.gov: 10, Twitter: 3, ...}
└─ max_time_per_source_seconds: 300

↓

Research Begins
└─ For each hypothesis:
   └─ For each source (parallel):
      └─ Query Loop:
         ├─ Generate query (LLM with history)
         ├─ Execute query
         ├─ Filter results
         │
         ├─ Check: LLM says SATURATED?
         │  └─ YES → Exit (INTELLIGENT)
         │
         ├─ Check: Reached max_queries?
         │  └─ YES → Exit (SAFETY NET)
         │
         ├─ Check: Exceeded time limit?
         │  └─ YES → Exit (SAFETY NET)
         │
         └─ CONTINUE (generate next query)

↓

Between tasks, check total budget
├─ Exceeded max_time_minutes?
└─ YES → Stop research, save results
```

---

## Logging & Transparency

**When limits trigger, we log**:
```json
{
    "event": "source_saturation_complete",
    "source": "SAM.gov",
    "exit_reason": "max_queries_reached",
    "queries_executed": 10,
    "results_found": 85,
    "saturation_decision": "CONTINUE",
    "note": "Reached user-configured max_queries limit (10) before LLM saturation"
}
```

**This enables**:
- Debugging ("Why did we stop?")
- Tuning ("Should I increase max_queries for SAM.gov?")
- Transparency (User sees when safety nets trigger vs intelligent exit)

---

## Configuration Guidelines

### **Query Limits by Source Type**

**Government Sources** (high signal, detailed):
- SAM.gov: 10 queries (contracts have rich metadata)
- DVIDS: 5 queries (military news, moderate depth)
- USAJobs: 5 queries (job listings)
- ClearanceJobs: 5 queries

**Social Sources** (noisy, shallow):
- Twitter: 3 queries (quick saturation, lots of noise)
- Reddit: 3 queries (similar to Twitter)
- Discord: 3 queries

**Web Search**:
- Brave Search: 5 queries (general web search)

### **Time Limits**

**Per-source**: 300s (5 min)
- Enough for 10 queries at ~30s each
- Prevents stuck sources

**Total budget**: 120 min (2 hours)
- User decision: "How long am I willing to wait?"
- Production: 60-120 min
- Testing: 10-30 min
- Deep investigation: 180+ min

---

## Comparison: Old vs New

### **Old (3-Layer) Architecture**
```
LLM timeout (180s)
  └─ Task timeout (1800s / 30 min)
     └─ Max research (120 min)

Issues:
- Task timeout arbitrarily cuts off investigations
- Middle layer doesn't add value
- Violates "LLM decides" philosophy
```

### **New (2-Layer) Architecture**
```
LLM timeout (180s) - API protection
  └─ Source limits (user-configured) - Per-source caps
     └─ Max research (user-configured) - Total cap

Benefits:
- LLM decides when source/task is complete
- User configures all limits upfront
- Simpler, fewer layers
- Aligns with "no hardcoded heuristics" philosophy
```

---

## Edge Cases

### **What if LLM never says SATURATED?**
**Protection**: User-configured max_queries and max_time_per_source_seconds

**Example**:
- Source keeps saying "CONTINUE"
- Reaches max_queries (10) → stops
- Or reaches time limit (5 min) → stops
- Logs: "Reached limit before saturation"

### **What if source is very rich?**
**Protection**: User can configure higher limits for specific sources

**Example**:
```python
max_queries_per_source={
    'SAM.gov': 15,  # Increased for thorough contract research
    'Twitter': 3    # Keep social sources low
}
```

### **What if research question is simple?**
**Intelligence**: LLM saturates quickly

**Example**:
- Query: "What is DARPA?"
- Source: Wikipedia via Brave
- Query 1: "DARPA" → 10 results, clear answer
- LLM: "SATURATED - Found comprehensive definition, no gaps"
- Exit after 1 query (not forced to do 5)

---

## Implementation Status

**Implemented**:
- ✅ LLM call timeout (180s)
- ✅ Max research budget (user-configured)

**In Progress** (query saturation refactor):
- 🚧 Source-level saturation loop
- 🚧 User-configured max_queries_per_source
- 🚧 User-configured max_time_per_source_seconds

**Removed**:
- ❌ Task-level timeout (redundant, violated philosophy)

---

## Summary

**Timeout philosophy**:
1. **LLM intelligence** decides when research is complete (primary)
2. **User configuration** sets budget and safety limits (not hardcoded)
3. **Simple layers** protect against edge cases (not complex rules)

**Result**: System that respects LLM intelligence while protecting against infinite loops and runaway costs through user-configured, transparent limits.
