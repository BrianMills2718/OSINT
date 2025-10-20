# PATTERNS.md - Code Templates for Current Phase

## LLM Call Pattern (CRITICAL)

**ALWAYS use this pattern - NEVER call litellm directly**:

```python
from llm_utils import acompletion
import json

# Generate query with structured output
response = await acompletion(
    model="gpt-5-mini",  # or gpt-5-nano for cost savings
    messages=[{"role": "user", "content": prompt}],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "strict": True,
            "name": "query_schema",
            "schema": {
                "type": "object",
                "properties": {
                    "relevant": {"type": "boolean"},
                    "param1": {"type": "string"},
                    "param2": {"type": ["string", "null"]},
                    "reasoning": {"type": "string"}
                },
                "required": ["relevant", "param1", "param2", "reasoning"],
                "additionalProperties": False
            }
        }
    }
)

result = json.loads(response.choices[0].message.content)
```

**NEVER DO THIS**:
```python
# WRONG - don't call litellm directly
response = await litellm.acompletion(...)

# WRONG - BREAKS gpt-5 models!
response = await acompletion(
    model="gpt-5-mini",
    max_tokens=500  # ← Exhausts reasoning tokens, returns empty!
)
```

---

## Database Integration Pattern

**Copy from**: `integrations/sam_integration.py`

```python
from typing import Dict, Optional
from datetime import datetime
from core.database_integration_base import (
    DatabaseIntegration,
    DatabaseMetadata,
    DatabaseCategory,
    QueryResult
)
from core.api_request_tracker import log_request
from llm_utils import acompletion
from config_loader import config

class NewSourceIntegration(DatabaseIntegration):
    @property
    def metadata(self) -> DatabaseMetadata:
        return DatabaseMetadata(
            id="newsource",
            name="New Source",
            category=DatabaseCategory.GOVERNMENT,
            requires_api_key=True,
            cost_per_query_estimate=0.001,
            typical_response_time=2.0,
            description="Brief description"
        )

    async def is_relevant(self, research_question: str) -> bool:
        """Quick keyword check BEFORE expensive LLM call."""
        keywords = ["keyword1", "keyword2"]
        question_lower = research_question.lower()
        return any(kw in question_lower for kw in keywords)

    async def generate_query(self, research_question: str) -> Optional[Dict]:
        """Use LLM to generate query parameters."""
        # See sam_integration.py for full example
        pass

    async def execute_search(
        self,
        query_params: Dict,
        api_key: Optional[str],
        limit: int
    ) -> QueryResult:
        """Execute API call, return standardized QueryResult."""
        start_time = datetime.now()

        try:
            # Make API call
            response = requests.get(url, params, headers, timeout=30)
            response.raise_for_status()

            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000

            # Log success
            log_request(
                api_name="NewSource",
                endpoint=url,
                status_code=response.status_code,
                response_time_ms=response_time_ms,
                error_message=None,
                request_params=query_params
            )

            return QueryResult(
                success=True,
                source="NewSource",
                total=response.json().get("total", 0),
                results=response.json().get("results", []),
                query_params=query_params,
                response_time_ms=response_time_ms
            )

        except Exception as e:
            # Log failure
            log_request(
                api_name="NewSource",
                endpoint=url,
                status_code=0,
                response_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                error_message=str(e),
                request_params=query_params
            )

            return QueryResult(
                success=False,
                source="NewSource",
                total=0,
                results=[],
                query_params=query_params,
                error=str(e),
                response_time_ms=response_time_ms
            )
```

---

## Testing Pattern

**Unit Test** (isolated component):
```python
import asyncio
from integrations.newsource_integration import NewSourceIntegration

async def test_newsource():
    integration = NewSourceIntegration()

    # Test relevance check
    assert await integration.is_relevant("test query") == True

    # Test query generation
    query = await integration.generate_query("test query")
    assert query is not None
    assert "param1" in query

    # Test search (requires API key)
    result = await integration.execute_search(query, api_key="...", limit=5)
    assert result.success == True
    assert result.total > 0

if __name__ == "__main__":
    asyncio.run(test_newsource())
```

**Integration Test** (multiple components):
```python
from core.parallel_executor import ParallelExecutor
from integrations.newsource_integration import NewSourceIntegration

async def test_with_executor():
    executor = ParallelExecutor()
    results = await executor.execute_all(
        research_question="test query",
        databases=[NewSourceIntegration()],
        api_keys={"newsource": "..."},
        limit=5
    )
    assert "newsource" in results
    assert results["newsource"].success == True
```

---

## Cost Tracking Pattern

```python
from llm_utils import get_cost_summary, reset_cost_tracking

# Before operation
reset_cost_tracking()

# ... perform LLM-heavy operation ...

# After operation
print(get_cost_summary())
```

**Output**:
```
============================================================
LLM COST SUMMARY
============================================================
Total Cost: $0.0234
Total Calls: 12

By Model:
------------------------------------------------------------
  gpt-5-mini                     $0.0234  (  12 calls, $0.0020/call)
============================================================
```

---

## API Request Logging Pattern

```python
from core.api_request_tracker import log_request

# Log successful request
log_request(
    api_name="NewSource",
    endpoint="https://api.newsource.gov/search",
    status_code=200,
    response_time_ms=1234.5,
    error_message=None,
    request_params={"query": "test"}
)

# Log failed request
log_request(
    api_name="NewSource",
    endpoint="https://api.newsource.gov/search",
    status_code=500,
    response_time_ms=2345.6,
    error_message="Connection timeout",
    request_params={"query": "test"}
)
```

---

## Configuration Pattern

```python
from config_loader import config

# Get model for specific operation
model = config.get_model("query_generation")  # Returns "gpt-5-mini"

# Get database config
db_config = config.get_database_config("newsource")
timeout = db_config["timeout"]  # Returns 30

# Get execution config
max_concurrent = config.get_execution_config("max_concurrent")  # Returns 10
```

---

**For complete examples, see**:
- `integrations/sam_integration.py` - Full database integration
- `integrations/usajobs_integration.py` - API with custom headers
- `test_verification.py` - Integration testing
- `test_cost_tracking.py` - Cost tracking usage
