# BabyAGI Analysis - What We Found

**Date**: 2025-10-21
**Task**: Clone BabyAGI repo to understand if it's simpler than LangGraph

---

## What BabyAGI Actually Is (2024 Version)

**Downloaded from**: https://github.com/yoheinakajima/babyagi

**What I Expected** (based on original 2023 concept):
- Simple ~300 line Python script
- Task queue with prioritization
- Basic loop: execute task → create new tasks → repeat

**What It Actually Is Now** (2024):
- Full Flask web framework with dashboard
- Complex function registration system ("Functionz")
- Database abstraction layer (multiple DB backends)
- Plugin architecture (Airtable, E2B, Firecrawl, etc.)
- Blueprint-based API system
- **139+ lines just in the core module**
- **Multiple modules**: `core/`, `db/`, `packs/`, `api/`, `dashboard/`

**Complexity**: Similar to or MORE complex than LangGraph

---

## Key Finding: Original BabyAGI No Longer Exists

The original simple BabyAGI (the famous 2023 version) has been **completely replaced** with a complex framework.

**What happened:**
1. Original BabyAGI (2023): Simple task queue loop
2. BabyAGI v2024: Full application framework with web UI

The simple version you were thinking of doesn't exist in the current repo.

---

## Your Concerns Were Right

You asked:
> "i feel like langgraph might be a little overpowered? are you sure the juice is worth the squeeze on this? would cloning the babyagi repo not be simpler?"

**Answer**: No, cloning BabyAGI repo would NOT be simpler. It's now just as complex (or more) than LangGraph.

**Evidence**:
- LangGraph: Single orchestration framework
- BabyAGI 2024: Flask + Functionz + DB layer + Plugin system + Dashboard

Both are "frameworks" not "simple scripts."

---

## What You Actually Need

Based on your questions and current system:

**Current System (Working)**:
- 7 database integrations (100% success)
- Adaptive search with entity extraction (Mozart pattern)
- Daily monitors with email alerts
- Brave Search integration (in progress)

**What Adaptive Search Already Does**:
```python
# This is essentially BabyAGI's task loop
Phase 1: Broad search (initial task)
  ↓
Extract entities (create new tasks)
  ↓
Phase 2: Targeted searches for each entity (execute new tasks)
  ↓
Quality check (should we create more tasks?)
  ↓
Phase 3: More targeted searches (if quality < threshold)
```

**You're already doing iterative task decomposition!**

---

## Recommendation: Build Simple Deep Research (No Framework)

**Don't use BabyAGI repo** - it's too complex
**Don't use LangGraph yet** - wait until you need its features

**Build this instead** (~150 lines):

```python
# research/deep_research.py

class SimpleDeepResearch:
    """
    Task-based deep research without external frameworks.
    Builds on existing AdaptiveSearchEngine.
    """

    def __init__(self):
        self.adaptive_search = AdaptiveSearchEngine()  # Existing!
        self.brave_search = BraveSearchIntegration()   # Coming!
        self.task_queue = []
        self.completed_tasks = []
        self.results_by_task = {}

    async def research(self, question: str, max_tasks: int = 10):
        """
        Deep research via task decomposition.

        Flow:
        1. LLM breaks question into 3-5 research tasks
        2. Execute each task with adaptive_search
        3. Analyze results, maybe create follow-up tasks
        4. Continue until max_tasks or no more tasks
        5. Synthesize final report
        """

        # Step 1: Decompose question into tasks
        self.task_queue = await self._decompose_question(question)

        # Step 2: Execute tasks
        while self.task_queue and len(self.completed_tasks) < max_tasks:
            task = self.task_queue.pop(0)

            # Execute with adaptive search (your existing code!)
            result = await self.adaptive_search.adaptive_search(task['query'])

            self.results_by_task[task['id']] = result
            self.completed_tasks.append(task)

            # Step 3: Should we dig deeper?
            if self._should_create_follow_ups(result, task):
                follow_ups = await self._create_follow_up_tasks(result, task)
                self.task_queue.extend(follow_ups)

        # Step 4: Synthesize report
        report = await self._synthesize_report(self.results_by_task)
        return report

    async def _decompose_question(self, question: str):
        """Use LLM to break question into 3-5 research tasks."""
        prompt = f"""Break this research question into 3-5 specific search tasks:

        Question: {question}

        Return tasks that can be searched in databases or web search.
        Each task should be a clear, focused query.
        """

        # Use your existing llm_utils
        response = await acompletion(
            model="gpt-5-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "strict": True,
                    "name": "research_tasks",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "tasks": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "id": {"type": "integer"},
                                        "query": {"type": "string"},
                                        "rationale": {"type": "string"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        )

        return json.loads(response.choices[0].message.content)["tasks"]

    def _should_create_follow_ups(self, result, task):
        """Decide if we need follow-up tasks."""
        # Simple heuristic: create follow-ups if we found interesting entities
        return (
            result.total_results > 5 and  # Found enough results
            len(result.entities_discovered) > 3  # Discovered new entities
        )

    async def _create_follow_up_tasks(self, result, parent_task):
        """Create follow-up tasks based on results."""
        # Pick top 2 entities that weren't in original query
        new_entities = [
            e for e in result.entities_discovered[:3]
            if e.lower() not in parent_task['query'].lower()
        ]

        follow_ups = []
        for i, entity in enumerate(new_entities[:2]):  # Max 2 follow-ups per task
            follow_ups.append({
                "id": len(self.completed_tasks) + len(self.task_queue) + i,
                "query": f"{parent_task['query']} AND {entity}",
                "rationale": f"Deep dive on entity: {entity}",
                "parent_task_id": parent_task['id']
            })

        return follow_ups

    async def _synthesize_report(self, results_by_task):
        """Synthesize all results into final report using LLM."""
        # Collect all results
        all_results = []
        for task_id, result in results_by_task.items():
            all_results.extend(result.results[:5])  # Top 5 from each task

        # Use LLM to synthesize
        prompt = f"""Synthesize these research results into a comprehensive report:

        Total sources: {len(all_results)}

        Results:
        {json.dumps([
            {
                'title': r.get('title', ''),
                'source': r.get('source', ''),
                'snippet': r.get('snippet', r.get('description', ''))[:200]
            }
            for r in all_results[:20]  # Limit to avoid token limits
        ], indent=2)}

        Create a structured report with:
        1. Executive Summary (3-5 sentences)
        2. Key Findings (bullet points)
        3. Detailed Analysis (2-3 paragraphs)
        4. Sources (list unique sources used)
        """

        response = await acompletion(
            model="gpt-5-mini",  # Or gpt-4 for better synthesis
            messages=[{"role": "user", "content": prompt}]
        )

        return {
            "report": response.choices[0].message.content,
            "total_tasks": len(self.completed_tasks),
            "total_results": len(all_results),
            "sources_searched": list(set(r.get('source') for r in all_results))
        }


# Usage
async def test_deep_research():
    """Test deep research on complex question."""
    engine = SimpleDeepResearch()

    result = await engine.research(
        "What is the relationship between JSOC and CIA Title 50 operations?",
        max_tasks=10
    )

    print(result['report'])
    print(f"\nSearched: {result['total_tasks']} tasks")
    print(f"Found: {result['total_results']} results")
    print(f"Sources: {', '.join(result['sources_searched'])}")
```

---

## Why This Approach Is Better

**Advantages over BabyAGI repo:**
- ✅ No external framework dependencies
- ✅ ~150 lines you can understand completely
- ✅ Builds on your existing AdaptiveSearchEngine
- ✅ Uses your existing llm_utils and integrations
- ✅ Can build in 1-2 days, not weeks

**Advantages over LangGraph:**
- ✅ Simpler - just a task queue
- ✅ No learning curve
- ✅ Easy to debug
- ✅ Can add LangGraph later if needed

**What it provides:**
- ✅ Task decomposition (LLM breaks question into searches)
- ✅ Iterative refinement (creates follow-up tasks based on results)
- ✅ Synthesis (LLM creates final report)
- ✅ Uses all your existing integrations

**What it doesn't provide (yet):**
- ❌ Retry logic (if search fails, just continues)
- ❌ State persistence (can't pause/resume)
- ❌ Parallel task execution (runs sequentially)
- ❌ Human-in-the-loop approval

**But**: You can add these features incrementally as you need them.

---

## When to Upgrade to LangGraph

**Add LangGraph when you hit these problems:**

1. **Need retry logic**: Tasks failing and need automatic retry with different strategy
2. **Need state persistence**: Investigations take hours, need to pause/resume
3. **Need conditional branching**: Complex "if X fails, try Y, else try Z" logic
4. **Need parallel execution**: Want to run multiple searches simultaneously with coordination
5. **Need human-in-the-loop**: Want approval gates before expensive operations

**Until then**: Keep it simple. The simple version will teach you what you actually need.

---

## Recommended Next Steps

1. **This Week**: Build SimpleDeepResearch (~150 lines)
2. **Test with**: "Investigate JSOC and Title 50 operations"
3. **Evaluate**: Does it solve your problem?
4. **If yes**: You're done, no framework needed
5. **If no**: Now you know what features you need, can choose framework intelligently

**Don't prematurely optimize for problems you don't have yet.**

---

## Answer to Your Questions

> "i feel like langgraph might be a little overpowered?"

**Yes.** For your current needs, LangGraph is overpowered.

> "are you sure the juice is worth the squeeze on this?"

**No.** Not until you hit problems that require its features.

> "would cloning the babyagi repo not be simpler?"

**No.** The BabyAGI repo is now MORE complex than LangGraph - it's a full framework.

> "what uncertainties and concerns do you have?"

**My concerns:**
1. I don't know if you actually need task decomposition (adaptive search might be enough)
2. I don't know your failure rate (how often do searches fail?)
3. I don't know your investigation workflow (autonomous or human-guided?)
4. I don't know your time constraints (5min or 5 hours per investigation?)

**My recommendation**: Build the simple version first. It will answer all these questions.

---

## Code Status

**Downloaded**: BabyAGI repo structure analyzed
**Conclusion**: Too complex to use as-is
**Recommendation**: Build simple deep research without framework
**Estimated effort**: 1-2 days for basic version
**File to create**: `research/deep_research.py` (~150 lines)

**Next step**: Get your answers to the 4 questions above, then I'll build the simple version.
