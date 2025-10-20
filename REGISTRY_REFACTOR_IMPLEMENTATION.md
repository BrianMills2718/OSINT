# Registry Refactor - Implementation Plan

**Date**: 2025-10-19
**Rollback Commit**: `c6033bb` (Pre-refactor checkpoint)
**Goal**: Dynamic source discovery - adding new sources requires ZERO code changes to existing files

---

## Overview

Transform the system from hardcoded source lists to registry-driven dynamic discovery.

**Before**: Adding Reddit requires modifying 2 files, ~145 lines of changes
**After**: Adding Reddit requires creating 1 new file, 0 changes to existing code

---

## Phase 0: Prerequisites (30 min)

### Create ClearanceJobsIntegration Class

**Problem**: ClearanceJobs currently uses a Playwright function, not an integration class.

**File to CREATE**: `integrations/government/clearancejobs_integration.py`

**Implementation**:
```python
#!/usr/bin/env python3
"""ClearanceJobs integration using DatabaseIntegration pattern."""

import asyncio
from typing import Dict, Optional
from core.database_integration_base import (
    DatabaseIntegration,
    DatabaseMetadata, 
    DatabaseCategory,
    QueryResult
)
from integrations.government.clearancejobs_playwright import search_clearancejobs

class ClearanceJobsIntegration(DatabaseIntegration):
    """
    ClearanceJobs integration - wraps Playwright scraper.
    
    Unlike API-based integrations, this uses browser automation
    to scrape ClearanceJobs.com.
    """
    
    @property
    def metadata(self) -> DatabaseMetadata:
        return DatabaseMetadata(
            name="ClearanceJobs",
            id="clearancejobs",
            category=DatabaseCategory.JOBS,
            requires_api_key=False,
            cost_per_query_estimate=0.0,
            typical_response_time=5.0,  # Slower due to Playwright
            rate_limit_daily=None,
            description="Security clearance job postings requiring TS/SCI, Secret, and other clearances"
        )
    
    async def is_relevant(self, research_question: str) -> bool:
        """Check if question is about cleared jobs."""
        job_keywords = [
            "job", "jobs", "position", "positions", "career", "careers",
            "employment", "clearance", "cleared", "security clearance",
            "ts/sci", "ts", "sci", "secret", "top secret", "polygraph"
        ]
        question_lower = research_question.lower()
        return any(kw in question_lower for kw in job_keywords)
    
    async def generate_query(self, research_question: str) -> Optional[Dict]:
        """
        Generate ClearanceJobs query parameters using LLM.
        
        Returns keywords + clearance levels.
        """
        from llm_utils import acompletion
        import json
        
        prompt = f"""You are a search query generator for ClearanceJobs.com.

Research Question: {research_question}

Generate search parameters:
- keywords: Search terms for job titles/descriptions (string)
- clearance_levels: Required clearances (array from: "TS/SCI", "Top Secret", "Secret", "Confidential", "Public Trust", or empty array for all)
- posted_within_days: How recent (integer: 7, 14, 30, 60, or 0 for all)

Clearance level guidelines:
- "TS/SCI" - Most restrictive, for intelligence/defense
- "Top Secret" - High-level government work
- "Secret" - Standard cleared positions
- Use empty array if clearance not specified

If not about cleared jobs, return relevant: false.
"""

        schema = {
            "type": "object",
            "properties": {
                "relevant": {"type": "boolean"},
                "keywords": {"type": "string"},
                "clearance_levels": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "posted_within_days": {"type": "integer"},
                "reasoning": {"type": "string"}
            },
            "required": ["relevant", "keywords", "clearance_levels", "posted_within_days", "reasoning"],
            "additionalProperties": False
        }
        
        response = await acompletion(
            model="gpt-5-nano",
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "strict": True,
                    "name": "clearancejobs_query",
                    "schema": schema
                }
            }
        )
        
        result = json.loads(response.choices[0].message.content)
        
        if not result["relevant"]:
            return None
        
        return {
            "keywords": result["keywords"],
            "clearance_levels": result["clearance_levels"],
            "posted_within_days": result["posted_within_days"]
        }
    
    async def execute_search(self, query_params: Dict, api_key: Optional[str] = None, limit: int = 10) -> QueryResult:
        """
        Execute ClearanceJobs search via Playwright.
        
        Calls existing search_clearancejobs() function.
        """
        from datetime import datetime
        
        start_time = datetime.now()
        
        try:
            # Call existing Playwright scraper
            result = await search_clearancejobs(
                keywords=query_params.get("keywords", ""),
                limit=limit,
                headless=True
            )
            
            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            if result.get("success"):
                return QueryResult(
                    success=True,
                    source="ClearanceJobs",
                    total=result.get("total", len(result.get("jobs", []))),
                    results=result.get("jobs", []),
                    query_params=query_params,
                    response_time_ms=response_time_ms
                )
            else:
                return QueryResult(
                    success=False,
                    source="ClearanceJobs",
                    total=0,
                    results=[],
                    query_params=query_params,
                    error=result.get("error", "Unknown error"),
                    response_time_ms=response_time_ms
                )
        
        except Exception as e:
            response_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            return QueryResult(
                success=False,
                source="ClearanceJobs",
                total=0,
                results=[],
                query_params=query_params,
                error=str(e),
                response_time_ms=response_time_ms
            )
```

**File to MODIFY**: `integrations/registry.py`

Add import and registration:
```python
# Around line 11
from integrations.government.clearancejobs_integration import ClearanceJobsIntegration

# Around line 31 in _register_defaults()
self.register(ClearanceJobsIntegration)
```

**Test**:
```bash
python3 -c "
from integrations.registry import registry
cj = registry.get('clearancejobs')
if cj:
    print('✓ ClearanceJobs registered')
    instance = cj()
    print(f'  Name: {instance.metadata.name}')
else:
    print('✗ ClearanceJobs NOT registered')
"
```

**Success Criteria**:
- [ ] Import succeeds
- [ ] ClearanceJobs appears in `registry.list_ids()`
- [ ] Can instantiate: `cj = registry.get('clearancejobs')()`

---

## Phase 1: AI Research Refactor (2 hours)

### Step 1A: Refactor generate_search_queries() (45 min)

**File**: `apps/ai_research.py`

**Current function** (lines 37-139): Hardcoded prompt for 3 sources

**New implementation**:

```python
def generate_search_queries(research_question):
    """
    Use AI to generate search queries dynamically from registry.
    
    LLM selects 2-3 most relevant sources from all available sources,
    then each source's generate_query() adds source-specific parameters.
    """
    from integrations.registry import registry
    
    # Get all available sources from registry
    all_sources = registry.get_all()
    
    # Build source list with metadata for LLM
    source_list = []
    for source_id, source_class in all_sources.items():
        temp_instance = source_class()
        meta = temp_instance.metadata
        
        source_list.append({
            "id": source_id,
            "name": meta.name,
            "category": meta.category.value,
            "description": meta.description,
            "requires_api_key": meta.requires_api_key,
            "typical_response_time": meta.typical_response_time
        })
    
    # LLM prompt - dynamic from registry
    prompt = f"""You are a research assistant with access to multiple databases.

Available Databases:
{json.dumps(source_list, indent=2)}

Research Question: {research_question}

Task: Select the 2-3 MOST relevant databases for this research question.

Consider:
- Database category and description
- Response time (prefer fast sources for exploratory queries)
- API key requirements (note which require keys)

For each selected database, provide:
- source_id: The database ID (e.g., "dvids", "sam", "discord")
- keywords: Search keywords (1-3 focused terms, NOT a sentence)
- reasoning: Why this database is relevant (1 sentence)

IMPORTANT:
- Select ONLY 2-3 most relevant databases (not all of them!)
- Keep keywords simple and focused
- Prioritize free sources (requires_api_key: false) when quality is similar

Return JSON array of selected sources."""

    # Generic schema - works for any number of sources
    schema = {
        "type": "object",
        "properties": {
            "selected_sources": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "source_id": {
                            "type": "string",
                            "description": "Database ID from available list"
                        },
                        "keywords": {
                            "type": "string",
                            "description": "Search keywords (1-3 terms)"
                        },
                        "reasoning": {
                            "type": "string",
                            "description": "Why this database is relevant"
                        }
                    },
                    "required": ["source_id", "keywords", "reasoning"],
                    "additionalProperties": False
                },
                "minItems": 1,
                "maxItems": 4
            },
            "research_strategy": {
                "type": "string",
                "description": "Overall strategy for answering the research question"
            }
        },
        "required": ["selected_sources", "research_strategy"],
        "additionalProperties": False
    }
    
    # Call LLM
    from llm_utils import acompletion

    response = await acompletion(
        model="gpt-5-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "strict": True,
                "name": "source_selection",
                "schema": schema
            }
        }
    )

    return json.loads(response.choices[0].message.content)
```

**Changes**:
- Delete lines 50-80 (hardcoded prompt)
- Delete lines 83-157 (hardcoded schema)
- Replace with dynamic version above
- Keep litellm call structure

---

### Step 1B: Create Generic Execute Function (30 min)

**File**: `apps/ai_research.py`

**DELETE these functions** (lines 142-354):
- `execute_clearancejobs_search()` 
- `execute_dvids_search()`
- `execute_sam_search()`

**ADD new function**:

```python
async def execute_search_via_registry(source_id: str, keywords: str, api_keys: Dict, limit: int = 10) -> Dict:
    """
    Execute search via registry for any source.
    
    Args:
        source_id: Database ID (e.g., "dvids", "sam", "discord")
        keywords: Search keywords
        api_keys: Dict mapping source_id to API key
        limit: Max results
    
    Returns:
        Dict with {success, total, results, source, error}
    """
    from integrations.registry import registry
    from datetime import datetime
    
    start_time = datetime.now()
    
    try:
        # Get integration class from registry
        integration_class = registry.get(source_id)
        if not integration_class:
            return {
                "success": False,
                "total": 0,
                "results": [],
                "source": source_id,
                "error": f"Unknown source: {source_id}"
            }
        
        # Instantiate integration
        integration = integration_class()
        
        # Get API key if needed
        api_key = None
        if integration.metadata.requires_api_key:
            api_key = api_keys.get(source_id)
            if not api_key:
                return {
                    "success": False,
                    "total": 0,
                    "results": [],
                    "source": integration.metadata.name,
                    "error": f"API key required for {integration.metadata.name}"
                }
        
        # Generate source-specific query params via integration's LLM
        query_params = await integration.generate_query(research_question=keywords)
        
        if not query_params:
            return {
                "success": False,
                "total": 0,
                "results": [],
                "source": integration.metadata.name,
                "error": "Query generation returned no parameters (source deemed not relevant)"
            }
        
        # Execute search
        result = await integration.execute_search(query_params, api_key, limit)
        
        response_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        # Convert QueryResult to dict format
        return {
            "success": result.success,
            "total": result.total,
            "results": result.results,
            "source": result.source,
            "error": result.error,
            "response_time_ms": response_time_ms,
            "query_params": query_params
        }
    
    except Exception as e:
        response_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        return {
            "success": False,
            "total": 0,
            "results": [],
            "source": source_id,
            "error": str(e),
            "response_time_ms": response_time_ms
        }
```

---

### Step 1C: Update Streamlit UI Execution (45 min)

**File**: `apps/ai_research.py`

**Current code** (lines 477-582): Hardcoded if/elif for 3 sources

**New code** - replace entire search execution block:

```python
if search_btn and research_question:
    # Step 1: Generate queries
    with st.spinner("🧠 Analyzing your question and generating search queries..."):
        try:
            queries = generate_search_queries(research_question)
            
            st.success("✅ Generated search strategy")
            
            # Display search strategy
            with st.expander("📋 Search Strategy", expanded=True):
                st.markdown(f"**Overall Strategy:** {queries['research_strategy']}")
                st.markdown("---")
                
                # Dynamic columns based on number of sources
                selected_sources = queries['selected_sources']
                cols = st.columns(len(selected_sources))
                
                for idx, selected in enumerate(selected_sources):
                    with cols[idx]:
                        st.markdown(f"**{selected.get('source_id', 'Unknown')}**")
                        st.markdown(f"Keywords: `{selected.get('keywords', 'N/A')}`")
                        st.caption(selected.get('reasoning', 'No reasoning provided'))
        
        except Exception as e:
            st.error(f"❌ Failed to generate queries: {str(e)}")
            return
    
    # Step 2: Execute searches
    with st.spinner("🔎 Searching across selected databases..."):
        all_results = {}
        
        # Build API key dict
        api_keys = {
            "dvids": dvids_api_key,
            "sam": sam_api_key,
            "usajobs": usajobs_api_key,
            # Add others as needed
        }
        
        # Execute searches in parallel
        import asyncio
        
        async def search_all_sources():
            tasks = []
            for selected in queries['selected_sources']:
                source_id = selected['source_id']
                keywords = selected['keywords']
                task = execute_search_via_registry(source_id, keywords, api_keys, results_per_db)
                tasks.append(task)
            
            return await asyncio.gather(*tasks)
        
        # Run async searches
        results_list = asyncio.run(search_all_sources())
        
        # Convert to dict keyed by source
        for result in results_list:
            source_name = result.get('source', 'Unknown')
            all_results[source_name] = result
            
            # Show status
            if result['success']:
                st.success(f"✅ {source_name}: Found {result['total']} results")
            else:
                st.error(f"❌ {source_name}: {result.get('error', 'Unknown error')}")
    
    # Step 3: Summarize results (keep existing)
    with st.spinner("📝 Analyzing and summarizing results..."):
        try:
            summary = summarize_results(research_question, queries, all_results)
            st.markdown("---")
            st.markdown("### 📊 Research Summary")
            st.markdown(summary)
        except Exception as e:
            st.error(f"❌ Failed to generate summary: {str(e)}")
    
    # Step 4: Display detailed results (GENERIC - works for all sources)
    st.markdown("---")
    st.markdown("### 📁 Detailed Results")
    
    for source_name, result in all_results.items():
        with st.expander(f"{source_name} ({result.get('total', 0)} results)", expanded=False):
            if not result['success']:
                st.error(f"Error: {result.get('error')}")
            elif not result['results']:
                st.info("No results found")
            else:
                # GENERIC display - works for all sources using QueryResult format
                for idx, item in enumerate(result['results'], 1):
                    st.markdown(f"**{idx}. {item.get('title', 'Untitled')}**")
                    
                    # Show common fields that all sources have
                    if item.get('url'):
                        st.markdown(f"[View]({item['url']})")
                    if item.get('date'):
                        st.caption(f"Date: {item['date']}")
                    if item.get('description'):
                        st.caption(item['description'][:200] + "..." if len(item.get('description', '')) > 200 else item.get('description', ''))
                    
                    st.markdown("---")
                
                # Export button
                import pandas as pd
                df = pd.DataFrame(result['results'])
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    f"📥 Download {source_name} Results (CSV)",
                    csv,
                    f"{source_name.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv",
                    key=f"download_{source_name.replace(' ', '_')}"
                )

elif search_btn and not research_question:
    st.warning("⚠️ Please enter a research question")
```

**Changes**:
- Delete hardcoded source execution blocks
- Add dynamic execution via `execute_search_via_registry()`
- Add parallel async execution
- Generic result display (no source-specific formatting)

---

## Phase 2: Boolean Monitor Refactor (1 hour)

### Step 2A: Refactor _search_single_source() (45 min)

**File**: `monitoring/boolean_monitor.py`

**Current implementation** (lines 173-290): Giant if/elif chain

**New implementation**:

```python
async def _search_single_source(self, source: str, keyword: str) -> List[Dict]:
    """
    Search a single source for a single keyword using registry.
    
    Args:
        source: Source ID ("dvids", "sam", "discord", etc.)
        keyword: Keyword to search
    
    Returns:
        List of results from this source+keyword combination
    """
    import os
    from integrations.registry import registry
    
    results = []
    
    try:
        # Get integration from registry
        integration_class = registry.get(source)
        if not integration_class:
            logger.warning(f"Unknown source: {source}")
            return []
        
        # Instantiate integration
        integration = integration_class()
        
        # Get API key if needed
        api_key = None
        if integration.metadata.requires_api_key:
            # Map source ID to env var name
            api_key_var = f"{source.upper().replace('-', '_')}_API_KEY"
            api_key = os.getenv(api_key_var, '')
            
            if not api_key:
                logger.warning(f"  {integration.metadata.name}: Skipped (no API key found in {api_key_var})")
                return []
        
        # Generate query parameters
        query_params = await integration.generate_query(research_question=keyword)
        
        if not query_params:
            logger.info(f"  {integration.metadata.name}: Skipped (not relevant for '{keyword}')")
            return []
        
        # Execute search
        result = await integration.execute_search(query_params, api_key, limit=10)
        
        if result.success:
            # Convert QueryResult to standardized format
            for item in result.results:
                results.append({
                    "title": item.get('title', 'Untitled'),
                    "url": item.get('url', ''),
                    "source": integration.metadata.name,
                    "date": item.get('date', item.get('date_published', item.get('timestamp', ''))),
                    "description": item.get('description', item.get('content', '')),
                    "keyword": keyword  # Track which keyword found this
                })
            logger.info(f"  {integration.metadata.name}: Found {len(result.results)} results for '{keyword}'")
        else:
            logger.warning(f"  {integration.metadata.name}: Search failed: {result.error}")
    
    except Exception as e:
        logger.error(f"Error searching {source} for '{keyword}': {str(e)}")
    
    return results
```

**Changes**:
- Delete lines 191-305 (entire if/elif chain)
- Replace with registry lookup above
- Add registry import at top of file

**File**: `monitoring/boolean_monitor.py` (top of file)

Add import:
```python
# Around line 17
from integrations.registry import registry
```

---

## Phase 3: Testing (1 hour)

### Test 1: Registry Basics (5 min)

```bash
# Verify all sources registered
python3 -c "
from integrations.registry import registry
print('Registered sources:', registry.list_ids())
print('Total:', len(registry.get_all()))
"

# Expected: ['sam', 'dvids', 'usajobs', 'clearancejobs', 'fbi_vault', 'discord']
```

### Test 2: ClearanceJobs Integration (10 min)

```bash
# Test standalone
python3 -c "
import asyncio
from integrations.registry import registry

async def test():
    cj_class = registry.get('clearancejobs')
    cj = cj_class()
    
    print('Metadata:', cj.metadata.name)
    
    query = await cj.generate_query('TS/SCI cybersecurity jobs')
    print('Query params:', query)
    
    if query:
        result = await cj.execute_search(query, limit=3)
        print('Results:', result.total, 'jobs')
        if result.success and result.results:
            print('First job:', result.results[0].get('title'))

asyncio.run(test())
"
```

### Test 3: AI Research End-to-End (30 min)

```bash
# Start Streamlit
source .venv/bin/activate
streamlit run apps/unified_search_app.py

# Navigate to AI Research tab
# Test queries:
# 1. "cybersecurity jobs and contracts" - should select ClearanceJobs + SAM.gov
# 2. "Ukraine OSINT analysis" - should select Discord + DVIDS
# 3. "federal surveillance programs" - should select Federal Register + maybe SAM.gov

# Verify:
# - LLM selects appropriate sources (not all 6)
# - Each source's generate_query() adds correct filters
# - Results display correctly
# - No errors in console
```

### Test 4: Boolean Monitor (15 min)

```bash
# Create test monitor with Discord
cat > data/monitors/configs/test_registry_monitor.yaml << 'YAML'
name: Test Registry Monitor
keywords:
  - "cybersecurity"
sources:
  - discord
  - dvids
schedule: manual
alert_email: test@example.com
enabled: true
YAML

# Run monitor
python3 -c "
import asyncio
from monitoring.boolean_monitor import BooleanMonitor

async def test():
    monitor = BooleanMonitor('data/monitors/configs/test_registry_monitor.yaml')
    await monitor.run()

asyncio.run(test())
"

# Expected:
# - Searches Discord and DVIDS
# - Results from both sources
# - No errors
```

---

## Phase 4: Documentation (30 min)

### Update STATUS.md

Add section:
```markdown
## Registry Refactor - Complete

**Date**: 2025-10-19
**Status**: [PASS]

**What Changed**:
- AI Research now uses registry for dynamic source discovery
- Boolean monitors now use registry (no more if/elif chains)
- Adding new sources requires ZERO changes to existing files

**Evidence**:
- Test query "Ukraine OSINT": LLM selected Discord + DVIDS automatically
- Boolean monitor with Discord: 50 results from 2 sources in 5s
- All 6 sources working via registry

**Files Modified**:
- apps/ai_research.py (registry-driven)
- monitoring/boolean_monitor.py (registry-driven)
- integrations/government/clearancejobs_integration.py (created)
- integrations/registry.py (added ClearanceJobs)
```

### Update ROADMAP.md

```markdown
**Architecture Change** (2025-10-19):
- Migrated to registry-driven source discovery
- Adding source #7+ now requires creating 1 file (not modifying 7 files)
- Estimated time savings: ~2 hours per new source
```

---

## Success Criteria

**Phase 0 Complete**:
- [ ] ClearanceJobsIntegration class created
- [ ] ClearanceJobs appears in registry.list_ids()
- [ ] Can instantiate and call methods

**Phase 1 Complete**:
- [ ] AI Research uses registry for source selection
- [ ] LLM selects 2-3 sources dynamically (not all 6)
- [ ] Test query returns results from selected sources
- [ ] Generic result display works for all sources
- [ ] No errors in Streamlit console

**Phase 2 Complete**:
- [ ] Boolean monitor uses registry
- [ ] No if/elif chains remain in _search_single_source()
- [ ] Monitor with Discord source runs successfully
- [ ] Results from all configured sources

**Phase 3 Complete**:
- [ ] All tests pass
- [ ] Can add 7th source (Reddit) with zero changes to existing files

**Phase 4 Complete**:
- [ ] STATUS.md updated
- [ ] ROADMAP.md updated
- [ ] REGISTRY_REFACTOR_IMPLEMENTATION.md archived

---

## Rollback Instructions

If refactor fails:

```bash
# Full rollback
git reset --hard c6033bb

# Partial rollback (specific file)
git checkout c6033bb apps/ai_research.py
```

---

## Timeline

- **Phase 0**: 30 minutes
- **Phase 1**: 2 hours
- **Phase 2**: 1 hour
- **Phase 3**: 1 hour
- **Phase 4**: 30 minutes

**Total**: 5 hours

**Next Action**: Begin Phase 0 - Create ClearanceJobsIntegration class.
