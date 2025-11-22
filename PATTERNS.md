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

**Copy from**: `integrations/government/federal_register.py` (best example)

### Required Result Format (CRITICAL!)

**ALL integrations must return results with these fields**:
- `title` (str, required): Human-readable title/name
- `url` (str, required): Link to full result
- `snippet` (str, optional): Brief excerpt (max 500 chars)
- `metadata` (dict, optional): Source-specific data

**Results are validated using Pydantic** - missing fields will raise ValueError!

### Field Transformation Pattern

**ALWAYS transform API responses to standardized format**:

```python
# CORRECT - Transform raw API response to standardized format
transformed_results = []
for doc in raw_api_response[:limit]:
    transformed = {
        "title": doc.get("api_title_field", "Untitled"),
        "url": doc.get("api_url_field", ""),
        "snippet": doc.get("api_summary_field", "")[:500],
        "metadata": {
            "api_specific_field1": doc.get("field1"),
            "api_specific_field2": doc.get("field2")
        }
    }
    transformed_results.append(transformed)

return QueryResult(
    success=True,
    source="NewSource",
    total=total,
    results=transformed_results,  # ← Transformed, not raw!
    query_params=query_params,
    response_time_ms=response_time_ms
)
```

**WRONG - Returning raw API response**:
```python
# WRONG - This will fail Pydantic validation!
return QueryResult(
    success=True,
    source="NewSource",
    total=total,
    results=raw_api_data,  # ← Missing title/url/snippet fields!
    ...
)
```

### Full Integration Example

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
            category=DatabaseCategory.GOV_GENERAL,
            requires_api_key=True,
            cost_per_query_estimate=0.001,
            typical_response_time=2.0,
            rate_limit_daily=None,
            description="Brief description"
        )

    async def is_relevant(self, research_question: str) -> bool:
        """
        LLM-based relevance check.

        Uses LLM to determine if this source is relevant for the research question,
        considering source strengths and limitations.
        """
        from llm_utils import acompletion
        from dotenv import load_dotenv

        load_dotenv()

        prompt = f"""Is [SourceName] relevant for researching this question?

RESEARCH QUESTION:
{research_question}

[SOURCENAME] CHARACTERISTICS:
Strengths:
- [List source strengths]

Limitations:
- [List source limitations]

DECISION CRITERIA:
- Is relevant: If [source capabilities] could provide valuable information
- NOT relevant: If ONLY seeking [things this source doesn't have]

Return JSON:
{{
  "relevant": true/false,
  "reasoning": "1-2 sentences explaining why"
}}"""

        try:
            response = await acompletion(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            return result.get("relevant", True)  # Default to True on parsing failure

        except Exception as e:
            # On error, default to True (let query generation handle filtering)
            print(f"[WARN] Relevance check failed: {e}, defaulting to True")
            return True

    async def generate_query(self, research_question: str) -> Optional[Dict]:
        """Use LLM to generate query parameters."""
        # See federal_register.py for full example
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

            # Parse raw API response
            raw_data = response.json()
            raw_results = raw_data.get("results", [])
            total = raw_data.get("total_count", len(raw_results))

            # CRITICAL: Transform to standardized format
            transformed_results = []
            for doc in raw_results[:limit]:
                transformed = {
                    "title": doc.get("doc_title", "Untitled"),
                    "url": doc.get("permalink", ""),
                    "snippet": doc.get("abstract", "")[:500],
                    "metadata": {
                        "doc_id": doc.get("id"),
                        "date": doc.get("publish_date"),
                        "author": doc.get("author")
                    }
                }
                transformed_results.append(transformed)

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
                total=total,
                results=transformed_results,  # ← Transformed format
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
                response_time_ms=(datetime.now() - start_time).total_seconds() * 1000
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
