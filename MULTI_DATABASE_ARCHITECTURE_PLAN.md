# Multi-Database Architecture Plan

**Goal:** Scale from 3 databases to 10+ databases using parallel, specialized LLMs for each database.

**Status:** Planning Phase
**Target Completion:** Phase 1-3 complete within this session

---

## Architecture Overview

### Current State (Monolithic)
```
Research Question
    ↓
Single LLM (generates 3 database queries)
    ↓
Sequential execution: ClearanceJobs → DVIDS → SAM.gov
    ↓
Combine results → Summarize
```

**Problems:**
- Single prompt handles all databases (doesn't scale)
- Sequential execution (slow)
- Adding databases requires rewriting prompt
- No per-database cost tracking

### Target State (Plugin-Based)
```
Research Question
    ↓
Parallel LLM calls → [ClearanceJobs LLM] [DVIDS LLM] [SAM.gov LLM] [USAJobs LLM] ...
    ↓
Parallel execution → [Execute queries in parallel]
    ↓
Combine results → Summarize
```

**Benefits:**
- Each database has specialized LLM prompt
- True parallel execution (3-4x faster)
- Add databases without touching existing code
- Per-database metrics and cost tracking
- Can disable underperforming databases

---

## Phase 1: Core Architecture (Current Session)

### 1.1 Create Base Abstraction

**File:** `database_integration_base.py`

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

class DatabaseCategory(Enum):
    """Category of database for relevance filtering"""
    JOBS = "jobs"
    CONTRACTS = "contracts"
    NEWS = "news"
    RESEARCH = "research"
    GENERAL = "general"

@dataclass
class DatabaseMetadata:
    """Metadata about a database integration"""
    name: str                          # Display name
    id: str                           # Unique identifier
    category: DatabaseCategory
    requires_api_key: bool
    cost_per_query_estimate: float   # USD
    typical_response_time: float     # seconds
    rate_limit_daily: Optional[int]  # None if unknown
    description: str

class QueryResult:
    """Standardized result from any database"""
    def __init__(self,
                 success: bool,
                 source: str,
                 total: int,
                 results: List[Dict],
                 query_params: Dict,
                 error: Optional[str] = None,
                 response_time_ms: float = 0,
                 metadata: Optional[Dict] = None):
        self.success = success
        self.source = source
        self.total = total
        self.results = results
        self.query_params = query_params
        self.error = error
        self.response_time_ms = response_time_ms
        self.metadata = metadata or {}

class DatabaseIntegration(ABC):
    """Base class for all database integrations"""

    @property
    @abstractmethod
    def metadata(self) -> DatabaseMetadata:
        """Return metadata about this database"""
        pass

    @abstractmethod
    async def is_relevant(self, research_question: str) -> bool:
        """
        Quick check if this database is relevant to the question.
        Can use simple rules or lightweight LLM call.
        Return False to skip this database entirely.
        """
        pass

    @abstractmethod
    async def generate_query(self, research_question: str) -> Optional[Dict]:
        """
        Use LLM to generate query parameters for this specific database.
        Returns None if database is not relevant.
        Returns Dict of query parameters if relevant.
        """
        pass

    @abstractmethod
    async def execute_search(self,
                           query_params: Dict,
                           api_key: Optional[str] = None,
                           limit: int = 10) -> QueryResult:
        """
        Execute the actual API call using query parameters.
        Returns standardized QueryResult.
        """
        pass

    def get_llm_prompt_template(self) -> str:
        """
        Return the LLM prompt template for query generation.
        Override this to customize the prompt.
        """
        return f"""You are a search query generator for {self.metadata.name}.

Database: {self.metadata.name}
Description: {self.metadata.description}
Category: {self.metadata.category.value}

Research Question: {{research_question}}

Your task: Generate optimal search parameters for this database.
If this database is not relevant to the research question, indicate that.

{{database_specific_instructions}}

Return your response as JSON following this schema:
{{response_schema}}
"""
```

**Decision Points:**
- ✅ Use abstract base class (flexibility + type safety)
- ✅ Standardize response format via QueryResult
- ✅ Support both sync and async (start async-first)
- ✅ Include cost tracking in metadata
- ✅ Two-phase: is_relevant() then generate_query()

### 1.2 Create Database Registry

**File:** `database_registry.py`

```python
from typing import Dict, List, Type
from database_integration_base import DatabaseIntegration, DatabaseCategory

class DatabaseRegistry:
    """Central registry for all database integrations"""

    def __init__(self):
        self._databases: Dict[str, DatabaseIntegration] = {}

    def register(self, database: DatabaseIntegration):
        """Register a new database integration"""
        db_id = database.metadata.id
        if db_id in self._databases:
            raise ValueError(f"Database {db_id} already registered")
        self._databases[db_id] = database
        print(f"✓ Registered database: {database.metadata.name}")

    def get(self, db_id: str) -> DatabaseIntegration:
        """Get a specific database by ID"""
        return self._databases.get(db_id)

    def get_all(self) -> List[DatabaseIntegration]:
        """Get all registered databases"""
        return list(self._databases.values())

    def get_by_category(self, category: DatabaseCategory) -> List[DatabaseIntegration]:
        """Get all databases in a category"""
        return [db for db in self._databases.values()
                if db.metadata.category == category]

    def list_available(self, api_keys: Dict[str, str]) -> List[DatabaseIntegration]:
        """List databases that have required API keys"""
        available = []
        for db in self._databases.values():
            if not db.metadata.requires_api_key:
                available.append(db)
            elif db.metadata.id in api_keys:
                available.append(db)
        return available

# Global registry instance
registry = DatabaseRegistry()
```

### 1.3 Create Parallel Executor

**File:** `parallel_executor.py`

```python
import asyncio
from typing import List, Dict, Optional
from datetime import datetime
from database_integration_base import DatabaseIntegration, QueryResult
from api_request_tracker import log_request

class ParallelExecutor:
    """Execute database queries in parallel"""

    def __init__(self, max_concurrent: int = 10):
        self.max_concurrent = max_concurrent

    async def execute_all(self,
                          research_question: str,
                          databases: List[DatabaseIntegration],
                          api_keys: Dict[str, str],
                          limit: int = 10) -> Dict[str, QueryResult]:
        """
        Execute queries across all databases in parallel.

        Returns dict mapping database ID to QueryResult.
        """

        # Phase 1: Relevance check (parallel)
        print(f"🔍 Checking relevance across {len(databases)} databases...")
        relevance_tasks = [
            self._check_relevance(db, research_question)
            for db in databases
        ]
        relevance_results = await asyncio.gather(*relevance_tasks)

        relevant_dbs = [
            db for db, is_rel in zip(databases, relevance_results)
            if is_rel
        ]

        print(f"✓ {len(relevant_dbs)} databases are relevant")

        # Phase 2: Generate queries (parallel)
        print(f"🤖 Generating queries for {len(relevant_dbs)} databases...")
        query_gen_tasks = [
            self._generate_query(db, research_question)
            for db in relevant_dbs
        ]
        query_params_list = await asyncio.gather(*query_gen_tasks)

        # Filter out None results (databases that declined after deeper analysis)
        db_query_pairs = [
            (db, params) for db, params in zip(relevant_dbs, query_params_list)
            if params is not None
        ]

        print(f"✓ Generated {len(db_query_pairs)} queries")

        # Phase 3: Execute searches (parallel with semaphore)
        print(f"🔎 Executing {len(db_query_pairs)} searches...")
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def execute_with_semaphore(db, params):
            async with semaphore:
                return await self._execute_search(db, params, api_keys, limit)

        search_tasks = [
            execute_with_semaphore(db, params)
            for db, params in db_query_pairs
        ]

        results = await asyncio.gather(*search_tasks, return_exceptions=True)

        # Build result dict
        result_dict = {}
        for (db, _), result in zip(db_query_pairs, results):
            if isinstance(result, Exception):
                # Create error result
                result_dict[db.metadata.id] = QueryResult(
                    success=False,
                    source=db.metadata.name,
                    total=0,
                    results=[],
                    query_params={},
                    error=str(result)
                )
            else:
                result_dict[db.metadata.id] = result

        return result_dict

    async def _check_relevance(self, db: DatabaseIntegration, question: str) -> bool:
        """Check if database is relevant"""
        try:
            return await db.is_relevant(question)
        except Exception as e:
            print(f"⚠️ Relevance check failed for {db.metadata.name}: {e}")
            return False

    async def _generate_query(self, db: DatabaseIntegration, question: str) -> Optional[Dict]:
        """Generate query for database"""
        try:
            start = datetime.now()
            params = await db.generate_query(question)
            duration = (datetime.now() - start).total_seconds() * 1000

            # Log LLM call (for cost tracking)
            log_request(
                f"{db.metadata.name}_QueryGen",
                "LLM",
                200,
                duration,
                None,
                {"question_length": len(question)}
            )

            return params
        except Exception as e:
            print(f"⚠️ Query generation failed for {db.metadata.name}: {e}")
            return None

    async def _execute_search(self,
                             db: DatabaseIntegration,
                             params: Dict,
                             api_keys: Dict[str, str],
                             limit: int) -> QueryResult:
        """Execute search for database"""
        api_key = api_keys.get(db.metadata.id)
        return await db.execute_search(params, api_key, limit)
```

**Design Decisions:**
- ✅ Three phases: relevance → query generation → execution
- ✅ Use semaphore to limit concurrent API calls
- ✅ Continue on error (don't let one database failure break all)
- ✅ Log all LLM calls for cost tracking
- ✅ Return structured results dict

---

## Phase 2: Refactor Existing Databases (Current Session)

### 2.1 Refactor ClearanceJobs

**File:** `integrations/clearancejobs_integration.py`

```python
from database_integration_base import (
    DatabaseIntegration, DatabaseMetadata, DatabaseCategory, QueryResult
)
from ClearanceJobs import ClearanceJobs
import litellm
from datetime import datetime

class ClearanceJobsIntegration(DatabaseIntegration):

    @property
    def metadata(self) -> DatabaseMetadata:
        return DatabaseMetadata(
            name="ClearanceJobs",
            id="clearancejobs",
            category=DatabaseCategory.JOBS,
            requires_api_key=False,
            cost_per_query_estimate=0.001,  # LLM cost only
            typical_response_time=2.0,
            rate_limit_daily=None,  # Unknown
            description="U.S. security clearance job listings"
        )

    async def is_relevant(self, research_question: str) -> bool:
        """Quick relevance check - does question relate to jobs?"""
        job_keywords = ["job", "career", "employment", "hiring", "position",
                       "vacancy", "work", "contractor"]
        question_lower = research_question.lower()
        return any(keyword in question_lower for keyword in job_keywords)

    async def generate_query(self, research_question: str) -> Optional[Dict]:
        """Generate ClearanceJobs query using LLM"""

        prompt = f"""You are a search query generator for ClearanceJobs, a U.S. security clearance job board.

Research Question: {research_question}

Generate search parameters for ClearanceJobs API:
- keywords: Search terms (string)
- clearances: Security clearance levels (array of strings from: "Unspecified", "Confidential", "Secret", "Top Secret", "TS/SCI", "Q Clearance")
- posted_days_ago: How recent (0-365, 0 = any time)

Return JSON with these exact fields. Use empty arrays/0 for not applicable.

Example:
{{
  "relevant": true,
  "keywords": "cybersecurity analyst",
  "clearances": ["TS/SCI", "Top Secret"],
  "posted_days_ago": 30,
  "reasoning": "Looking for recent cybersecurity jobs requiring high clearances"
}}
"""

        schema = {
            "type": "object",
            "properties": {
                "relevant": {"type": "boolean"},
                "keywords": {"type": "string"},
                "clearances": {"type": "array", "items": {"type": "string"}},
                "posted_days_ago": {"type": "integer"},
                "reasoning": {"type": "string"}
            },
            "required": ["relevant", "keywords", "clearances", "posted_days_ago", "reasoning"],
            "additionalProperties": False
        }

        response = await litellm.acompletion(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_schema", "json_schema": {"strict": True, "schema": schema}}
        )

        result = json.loads(response.choices[0].message.content)

        if not result["relevant"]:
            return None

        return {
            "keywords": result["keywords"],
            "clearances": result["clearances"],
            "posted_days_ago": result["posted_days_ago"]
        }

    async def execute_search(self, query_params: Dict, api_key: Optional[str] = None, limit: int = 10) -> QueryResult:
        """Execute ClearanceJobs search"""
        start_time = datetime.now()

        try:
            cj = ClearanceJobs()

            body = {
                "pagination": {"page": 1, "size": limit},
                "query": query_params.get("keywords", "")
            }

            if query_params.get("clearances"):
                body["filters"] = {"clearance": query_params["clearances"]}

            if query_params.get("posted_days_ago"):
                body.setdefault("filters", {})["posted"] = query_params["posted_days_ago"]

            response = cj.post("/jobs/search", body)
            data = response.json()

            jobs = data.get("data", [])
            meta = data.get("meta", {})
            pagination = meta.get("pagination", {})
            total = pagination.get("total", len(jobs))

            response_time = (datetime.now() - start_time).total_seconds() * 1000

            # Log to tracker
            log_request("ClearanceJobs", "https://api.clearancejobs.com/api/v1/jobs/search",
                       response.status_code, response_time, None, body)

            return QueryResult(
                success=True,
                source="ClearanceJobs",
                total=total,
                results=jobs[:limit],
                query_params=query_params,
                response_time_ms=response_time
            )

        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            log_request("ClearanceJobs", "https://api.clearancejobs.com/api/v1/jobs/search",
                       0, response_time, str(e), query_params)

            return QueryResult(
                success=False,
                source="ClearanceJobs",
                total=0,
                results=[],
                query_params=query_params,
                error=str(e),
                response_time_ms=response_time
            )
```

### 2.2 Refactor DVIDS & SAM.gov

Similar pattern for DVIDS and SAM.gov (create `integrations/dvids_integration.py` and `integrations/sam_integration.py`)

---

## Phase 3: Add New Database (Pilot)

### 3.1 USAJobs Integration

**Why USAJobs?**
- Free API (no key required for basic)
- Well-documented
- Complementary to ClearanceJobs
- Good test of architecture

**File:** `integrations/usajobs_integration.py`

```python
class USAJobsIntegration(DatabaseIntegration):

    @property
    def metadata(self) -> DatabaseMetadata:
        return DatabaseMetadata(
            name="USAJobs",
            id="usajobs",
            category=DatabaseCategory.JOBS,
            requires_api_key=False,
            cost_per_query_estimate=0.001,
            typical_response_time=3.0,
            rate_limit_daily=None,
            description="Official U.S. government job listings"
        )

    async def is_relevant(self, research_question: str) -> bool:
        """Relevant for government/federal job questions"""
        gov_keywords = ["government", "federal", "agency", "civil service",
                       "gs-", "usajobs"]
        question_lower = research_question.lower()
        return any(keyword in question_lower for keyword in gov_keywords) or \
               any(keyword in question_lower for keyword in ["job", "career", "employment"])

    async def generate_query(self, research_question: str) -> Optional[Dict]:
        """Generate USAJobs API parameters"""
        # Similar LLM prompt pattern as ClearanceJobs
        # USAJobs uses different parameters: keyword, location, organization, etc.
        pass

    async def execute_search(self, query_params: Dict, api_key: Optional[str] = None, limit: int = 10) -> QueryResult:
        """Execute USAJobs API call"""
        # Use requests to call https://data.usajobs.gov/api/search
        pass
```

---

## Phase 4: Update AI Research Module

### 4.1 New Main Function

**File:** `ai_research_v2.py`

```python
from database_registry import registry
from parallel_executor import ParallelExecutor
from integrations.clearancejobs_integration import ClearanceJobsIntegration
from integrations.dvids_integration import DVIDSIntegration
from integrations.sam_integration import SAMIntegration
from integrations.usajobs_integration import USAJobsIntegration

# Register all databases
registry.register(ClearanceJobsIntegration())
registry.register(DVIDSIntegration())
registry.register(SAMIntegration())
registry.register(USAJobsIntegration())

async def conduct_research(research_question: str, api_keys: Dict[str, str]) -> Dict:
    """
    New research function using parallel multi-database architecture.

    Args:
        research_question: The research question
        api_keys: Dict mapping database IDs to API keys

    Returns:
        Dict with results from all databases
    """

    # Get available databases
    available_dbs = registry.list_available(api_keys)

    print(f"🔍 Researching across {len(available_dbs)} databases...")

    # Execute in parallel
    executor = ParallelExecutor(max_concurrent=5)
    results = await executor.execute_all(
        research_question=research_question,
        databases=available_dbs,
        api_keys=api_keys,
        limit=10
    )

    # Summarize results
    summary = await summarize_results(research_question, results)

    return {
        "question": research_question,
        "databases_searched": len(results),
        "results": results,
        "summary": summary
    }
```

### 4.2 Cost Tracking

**File:** `cost_tracker.py`

```python
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import json

class CostTracker:
    """Track costs per database"""

    def __init__(self, log_file: Path = Path("database_costs.jsonl")):
        self.log_file = log_file
        self.daily_costs = defaultdict(float)

    def log_query(self, database_id: str, cost: float):
        """Log a query cost"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "database": database_id,
            "cost": cost
        }

        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

        self.daily_costs[database_id] += cost

    def get_total_cost(self, database_id: Optional[str] = None) -> float:
        """Get total cost for a database or all databases"""
        if database_id:
            return self._sum_costs(database_id)
        return sum(self._sum_costs(db) for db in self.daily_costs.keys())

    def get_cost_report(self) -> Dict:
        """Generate cost report"""
        return {
            "total": self.get_total_cost(),
            "by_database": dict(self.daily_costs)
        }
```

---

## Phase 5: Testing & Validation

### 5.1 Test Script

**File:** `test_multi_db.py`

```python
import asyncio
from ai_research_v2 import conduct_research

async def test_architecture():
    """Test the new multi-database architecture"""

    api_keys = {
        "dvids": "key-68f319e8dc377",
        "sam": "SAM-db0e8074-ef7f-41b2-8456-b0f79a0a2112"
    }

    test_questions = [
        "What cybersecurity jobs are available?",
        "What government contracts relate to AI?",
        "What has the military been doing recently?",
        "Federal jobs in intelligence analysis"
    ]

    for question in test_questions:
        print(f"\n{'='*80}")
        print(f"Question: {question}")
        print('='*80)

        result = await conduct_research(question, api_keys)

        print(f"\nDatabases searched: {result['databases_searched']}")
        for db_id, db_result in result['results'].items():
            status = "✓" if db_result.success else "✗"
            print(f"  {status} {db_result.source}: {db_result.total} results")

        print(f"\nSummary:\n{result['summary']}")

if __name__ == "__main__":
    asyncio.run(test_architecture())
```

### 5.2 Performance Benchmarks

Compare old vs new:
- Query generation time (sequential vs parallel)
- Total execution time
- Cost per research question
- Result quality

**Expected improvements:**
- 3-4x faster (parallel execution)
- Same or better quality (specialized prompts)
- Easier to add new databases

---

## Phase 6: Documentation

### 6.1 Developer Guide

**File:** `DATABASE_INTEGRATION_GUIDE.md`

```markdown
# Adding a New Database Integration

## Step 1: Create Integration Class

Create `integrations/yourdb_integration.py`:

```python
from database_integration_base import DatabaseIntegration, DatabaseMetadata

class YourDBIntegration(DatabaseIntegration):
    @property
    def metadata(self) -> DatabaseMetadata:
        return DatabaseMetadata(
            name="YourDB",
            id="yourdb",
            category=DatabaseCategory.JOBS,  # or CONTRACTS, NEWS, etc.
            requires_api_key=True,
            cost_per_query_estimate=0.002,
            typical_response_time=2.5,
            rate_limit_daily=1000,
            description="Your database description"
        )

    async def is_relevant(self, research_question: str) -> bool:
        # Quick keyword check
        return "keyword" in research_question.lower()

    async def generate_query(self, research_question: str) -> Optional[Dict]:
        # Use LLM to generate query parameters
        # Return None if not relevant
        pass

    async def execute_search(self, query_params: Dict, ...) -> QueryResult:
        # Call your API
        # Return standardized QueryResult
        pass
```

## Step 2: Register Database

In `ai_research_v2.py`:

```python
from integrations.yourdb_integration import YourDBIntegration

registry.register(YourDBIntegration())
```

## Step 3: Test

```bash
python test_multi_db.py
```

Done! Your database is now integrated.
```

---

## Implementation Order

### Session 1 (Now):
1. ✅ Create architecture plan (this document)
2. Create `database_integration_base.py`
3. Create `database_registry.py`
4. Create `parallel_executor.py`
5. Refactor ClearanceJobs to new architecture
6. Test with 1 database

### Session 2:
7. Refactor DVIDS and SAM.gov
8. Add USAJobs integration
9. Test with 4 databases in parallel
10. Measure performance improvements

### Session 3:
11. Add cost tracking
12. Update Streamlit UI
13. Write developer guide
14. Add 2-3 more databases

---

## Success Metrics

**Phase 1 Complete When:**
- [x] Base architecture designed
- [ ] Can register and query 1 database via new system
- [ ] Parallel execution works

**Phase 2 Complete When:**
- [ ] All 3 existing databases refactored
- [ ] Performance is >= current system
- [ ] No regressions in result quality

**Phase 3 Complete When:**
- [ ] USAJobs integrated successfully
- [ ] Can add new database in < 100 lines of code
- [ ] Developer guide written

---

## Open Questions

1. **Router LLM:** Do we need a router to pre-filter databases, or is the two-phase (is_relevant → generate_query) sufficient?
   - **Recommendation:** Start without router, add later if needed

2. **Caching:** Should we cache LLM-generated queries?
   - **Recommendation:** Not initially, add in Phase 4

3. **Async vs Sync:** Start with async or hybrid?
   - **Decision:** Async-first for parallelism

4. **Error Recovery:** Retry failed databases?
   - **Decision:** No retries initially, just log failures

---

## Next Step

Proceed with implementing `database_integration_base.py`?
