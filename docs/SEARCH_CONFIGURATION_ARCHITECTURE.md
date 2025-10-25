# Search Configuration Architecture - Methodical Approach

**Date**: 2025-10-25
**Status**: Design document for unified search configuration across codebase

---

## Problem Statement

We have multiple search entry points with different configuration needs:
- **Quick Search** (apps/ai_research.py) - User-facing, needs simple UI controls
- **Deep Research** (research/deep_research.py) - Task-based, needs programmatic config
- **Boolean Monitors** (monitoring/) - Scheduled, needs stored config
- **CLI** (apps/ai_research_cli.py) - Command-line, needs flags/args

**Current issue**: Configuration logic scattered, inconsistent behavior across entry points

---

## Design Principles

### 1. Separation of Concerns

**Three Layers**:
```
┌─────────────────────────────────────┐
│  UI Layer (Streamlit/CLI/API)      │  ← User-facing controls
├─────────────────────────────────────┤
│  Configuration Layer               │  ← Unified config object
├─────────────────────────────────────┤
│  Execution Layer (core/)           │  ← Consumes config, executes
└─────────────────────────────────────┘
```

**Key insight**: UI controls → Config object → Execution engine

### 2. Single Source of Truth

**SearchConfig dataclass** (core/search_config.py):
```python
@dataclass
class SearchConfig:
    """Unified search configuration for all entry points."""

    # Source Selection
    comprehensive_mode: bool = True  # If True, select ALL relevant sources

    # Filtering (currently disabled, kept for future)
    apply_relevance_filter: bool = False  # If True, call is_relevant() before search

    # Execution
    max_results_per_source: int = 10
    timeout_seconds: int = 30
    enable_parallel: bool = True

    # Cost Control
    max_llm_calls: Optional[int] = None
    max_api_calls: Optional[int] = None

    # Debugging
    verbose_logging: bool = False
    log_query_params: bool = True
```

### 3. UI Simplicity Principle

**User sees**: Minimal controls (1-2 checkboxes max)
**System uses**: Full configuration object internally

**Example** (current Quick Search):
```
User sees:
  [ ] 🎯 Focused Search (faster, selective)

System translates to:
  SearchConfig(
    comprehensive_mode = not focused_search,
    apply_relevance_filter = False
  )
```

---

## Architecture Layers

### Layer 1: UI Controls (Entry Points)

Each entry point provides **simple user-facing controls**, translated to SearchConfig:

#### A. Quick Search (apps/ai_research.py)

**Current (GOOD - keep this)**:
```python
# Single checkbox
focused_search = st.checkbox(
    "🎯 Focused Search (faster, selective)",
    value=False  # Default: comprehensive mode
)

# Translate to config
config = SearchConfig(
    comprehensive_mode=not focused_search,
    apply_relevance_filter=False,  # Hardcoded OFF
    max_results_per_source=results_per_db
)
```

**Why this works**:
- ✅ Simple (1 checkbox)
- ✅ Clear default (unchecked = comprehensive)
- ✅ Future-proof (apply_relevance_filter hidden but available)

#### B. Deep Research (research/deep_research.py)

**Should use**:
```python
# Programmatic config, no UI needed
config = SearchConfig(
    comprehensive_mode=True,  # Always comprehensive for multi-task
    apply_relevance_filter=False,
    max_results_per_source=10,
    verbose_logging=True  # More logging for debugging
)
```

**Why different from Quick Search**:
- Deep Research is multi-task (5+ tasks), needs comprehensive coverage
- No user interaction mid-execution

#### C. Boolean Monitors (monitoring/)

**Should use**:
```python
# Load from monitor config file
monitor_config = load_monitor("jsoc_operations.yaml")

config = SearchConfig(
    comprehensive_mode=monitor_config.get("comprehensive", True),
    apply_relevance_filter=False,
    max_results_per_source=monitor_config.get("max_results", 10)
)
```

**Why different**:
- Stored configuration (YAML files)
- No user interaction
- May want different settings per monitor

#### D. CLI (apps/ai_research_cli.py)

**Should use**:
```python
# Command-line flags
parser.add_argument("--focused", action="store_true",
                   help="Focused search (faster, selective)")

config = SearchConfig(
    comprehensive_mode=not args.focused,
    apply_relevance_filter=False,
    max_results_per_source=args.limit
)
```

**Why different**:
- CLI flags instead of checkboxes
- Same logic as UI, different interface

---

### Layer 2: Configuration Object (core/search_config.py)

**Single canonical configuration class**:

```python
from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class SearchConfig:
    """
    Unified search configuration for all execution engines.

    This class is the single source of truth for search behavior.
    All entry points (UI, CLI, API, monitors) create this object.
    All execution engines (ParallelExecutor, DeepResearch) consume it.
    """

    # === SOURCE SELECTION ===
    comprehensive_mode: bool = True
    """
    If True: AI selects ALL relevant sources (wide net)
    If False: AI selects 2-3 most relevant sources (focused)

    Used by: generate_search_queries() LLM prompt
    Default: True (comprehensive coverage)
    """

    # === RELEVANCE FILTERING ===
    apply_relevance_filter: bool = False
    """
    If True: Call is_relevant() before each search, skip if not relevant
    If False: Always search selected sources (no pre-filtering)

    Used by: execute_search_via_registry()
    Default: False (no filtering - maximum transparency)
    Status: Currently disabled in UI, kept for future use
    """

    # === EXECUTION PARAMETERS ===
    max_results_per_source: int = 10
    """Max results to retrieve from each source"""

    timeout_seconds: int = 30
    """Max time to wait for each source"""

    enable_parallel: bool = True
    """Execute sources in parallel vs sequentially"""

    # === COST CONTROL ===
    max_llm_calls: Optional[int] = None
    """Max LLM calls (for generate_query). None = unlimited"""

    max_api_calls: Optional[int] = None
    """Max API calls to external sources. None = unlimited"""

    # === DEBUGGING ===
    verbose_logging: bool = False
    """Enable DEBUG level logging"""

    log_query_params: bool = True
    """Log generated query parameters to file"""

    # === FUTURE OPTIONS (not exposed in UI yet) ===
    enable_caching: bool = False
    """Cache query results (future)"""

    cache_ttl_hours: int = 24
    """Cache time-to-live in hours (future)"""

    def __post_init__(self):
        """Validate configuration."""
        if self.max_results_per_source < 1:
            raise ValueError("max_results_per_source must be >= 1")
        if self.timeout_seconds < 1:
            raise ValueError("timeout_seconds must be >= 1")

    @classmethod
    def from_ui(cls, focused_search: bool, results_per_db: int) -> 'SearchConfig':
        """Create config from Quick Search UI controls."""
        return cls(
            comprehensive_mode=not focused_search,
            apply_relevance_filter=False,
            max_results_per_source=results_per_db
        )

    @classmethod
    def from_cli(cls, args) -> 'SearchConfig':
        """Create config from CLI arguments."""
        return cls(
            comprehensive_mode=not args.focused,
            apply_relevance_filter=False,
            max_results_per_source=args.limit,
            verbose_logging=args.verbose
        )

    @classmethod
    def from_monitor(cls, monitor_config: dict) -> 'SearchConfig':
        """Create config from monitor YAML."""
        return cls(
            comprehensive_mode=monitor_config.get("comprehensive", True),
            apply_relevance_filter=False,
            max_results_per_source=monitor_config.get("max_results", 10)
        )

    @classmethod
    def for_deep_research(cls, **overrides) -> 'SearchConfig':
        """Create config optimized for Deep Research."""
        defaults = {
            "comprehensive_mode": True,  # Always comprehensive
            "apply_relevance_filter": False,
            "max_results_per_source": 10,
            "verbose_logging": True,
            "enable_parallel": True
        }
        defaults.update(overrides)
        return cls(**defaults)
```

---

### Layer 3: Execution Engines (core/)

**Execution engines consume SearchConfig, never create it**:

#### ParallelExecutor (core/parallel_executor.py)

```python
async def execute_parallel_search(
    research_question: str,
    selected_sources: List[str],
    api_keys: dict,
    config: SearchConfig  # ← Receives config, doesn't create it
) -> Dict[str, QueryResult]:
    """
    Execute searches across multiple sources in parallel.

    Args:
        research_question: User's question
        selected_sources: List of source IDs to search
        api_keys: API keys for each source
        config: SearchConfig object controlling behavior
    """

    # Use config to control behavior
    if config.apply_relevance_filter:
        # Filter sources via is_relevant()
        pass

    # Execute with config parameters
    tasks = []
    for source_id in selected_sources:
        task = execute_single_source(
            source_id,
            research_question,
            api_keys,
            limit=config.max_results_per_source,
            timeout=config.timeout_seconds
        )
        tasks.append(task)

    if config.enable_parallel:
        results = await asyncio.gather(*tasks)
    else:
        results = [await task for task in tasks]

    return results
```

#### Deep Research (research/deep_research.py)

```python
class SimpleDeepResearch:
    def __init__(
        self,
        config: SearchConfig,  # ← Receives config
        max_tasks: int = 10,
        # ... other Deep Research specific params
    ):
        self.config = config
        # ...

    async def _search_mcp_tools(self, query: str) -> List[Dict]:
        """Search using MCP tools, respecting config."""
        # Use self.config.max_results_per_source
        # Use self.config.comprehensive_mode
        # etc.
```

---

## Migration Plan

### Phase 1: Create SearchConfig (1 hour)

**Files to create**:
1. `core/search_config.py` - SearchConfig dataclass

**Implementation**:
```python
# See full implementation above
```

**Testing**:
```python
# tests/test_search_config.py
def test_search_config_defaults():
    config = SearchConfig()
    assert config.comprehensive_mode == True
    assert config.apply_relevance_filter == False

def test_search_config_from_ui():
    config = SearchConfig.from_ui(focused_search=False, results_per_db=10)
    assert config.comprehensive_mode == True
```

---

### Phase 2: Update Quick Search (30 min)

**File**: `apps/ai_research.py`

**Changes**:
```python
# Line ~56: Add import
from core.search_config import SearchConfig

# Lines 463-473: Replace inline config with SearchConfig
focused_search = st.checkbox(...)
results_per_db = st.number_input(...)

# Create config object
config = SearchConfig.from_ui(focused_search, results_per_db)

# Pass to functions
queries = generate_search_queries(research_question, config.comprehensive_mode)
result = await execute_search_via_registry(..., config)  # New signature
```

**Benefits**:
- UI code stays simple (1 checkbox)
- Configuration centralized
- Easy to add new options later (just update SearchConfig, UI unchanged)

---

### Phase 3: Update Execution Engines (1-2 hours)

**Files to update**:
1. `apps/ai_research.py` - execute_search_via_registry()
2. `core/parallel_executor.py` (if used)
3. `research/deep_research.py`

**Changes**:
```python
# Before:
async def execute_search_via_registry(
    source_id, research_question, api_keys, limit, apply_relevance_filter
):
    # 5 parameters, scattered logic

# After:
async def execute_search_via_registry(
    source_id: str,
    research_question: str,
    api_keys: dict,
    config: SearchConfig
) -> dict:
    # 4 parameters, unified config

    # Use config throughout
    if config.apply_relevance_filter:
        is_relevant = await integration.is_relevant(...)

    result = await integration.execute_search(..., config.max_results_per_source)
```

---

### Phase 4: Update Other Entry Points (1 hour each)

**Files**:
1. `apps/ai_research_cli.py` - Use SearchConfig.from_cli()
2. `research/deep_research.py` - Use SearchConfig.for_deep_research()
3. `monitoring/` - Use SearchConfig.from_monitor()

---

## Benefits of This Architecture

### 1. Consistency Across Entry Points

**Same behavior** whether user uses:
- Quick Search UI (checkbox)
- CLI (--focused flag)
- Deep Research (programmatic)
- Monitors (YAML config)

### 2. Easy to Add New Options

**Example**: Add caching support

```python
# 1. Update SearchConfig (core/search_config.py)
@dataclass
class SearchConfig:
    enable_caching: bool = False  # Add this
    cache_ttl_hours: int = 24

# 2. UI stays simple (don't expose it yet)
# No UI changes needed!

# 3. Execution engines can use it
if config.enable_caching:
    cached_result = check_cache(query)
```

**User impact**: Zero (new option hidden until UI updated)

### 3. Testing Simplified

**Before**: Mock UI controls, CLI args, YAML files
**After**: Just create SearchConfig objects

```python
def test_comprehensive_search():
    config = SearchConfig(comprehensive_mode=True)
    results = execute_search(..., config)
    assert len(results) > 0

def test_focused_search():
    config = SearchConfig(comprehensive_mode=False)
    results = execute_search(..., config)
    # Different behavior
```

### 4. Documentation

**Single place to document all options**: SearchConfig class docstrings

**Before**: Options scattered across UI code, function signatures, YAML schemas
**After**: `core/search_config.py` documents everything

---

## Implementation Status

**Current State**:
- ✅ Quick Search UI simplified (1 checkbox, commit e17973c)
- ❌ SearchConfig class not created yet
- ❌ Execution engines still use scattered parameters
- ❌ Other entry points not using unified config

**Recommended Next Steps**:
1. Create `core/search_config.py` (1 hour)
2. Update Quick Search to use SearchConfig (30 min)
3. Update execute_search_via_registry() (30 min)
4. Test and validate (30 min)
5. Update other entry points as needed (1 hour each)

**Total effort**: 3-4 hours for full migration

---

## Future Extensions

### Option 1: Advanced UI Mode (Hidden)

```python
# Only show if user enables "Advanced Options"
with st.expander("⚙️ Advanced Options", expanded=False):
    enable_caching = st.checkbox("Enable result caching")
    cache_hours = st.number_input("Cache TTL (hours)", 1, 168, 24)

    config = SearchConfig.from_ui(
        focused_search,
        results_per_db,
        enable_caching=enable_caching,
        cache_ttl_hours=cache_hours
    )
```

### Option 2: Profiles

```python
class SearchConfig:
    @classmethod
    def fast_profile(cls) -> 'SearchConfig':
        """Quick search, minimal sources."""
        return cls(comprehensive_mode=False, max_results_per_source=5)

    @classmethod
    def thorough_profile(cls) -> 'SearchConfig':
        """Comprehensive search, all sources."""
        return cls(comprehensive_mode=True, max_results_per_source=20)

    @classmethod
    def investigative_profile(cls) -> 'SearchConfig':
        """Optimized for investigative journalism."""
        return cls(
            comprehensive_mode=True,
            max_results_per_source=50,
            enable_caching=True
        )
```

### Option 3: Per-Source Configuration

```python
@dataclass
class SourceConfig:
    """Override config for specific sources."""
    source_id: str
    max_results: int
    timeout: int
    enabled: bool = True

@dataclass
class SearchConfig:
    # ... existing fields
    source_overrides: List[SourceConfig] = field(default_factory=list)

    def get_config_for_source(self, source_id: str) -> SourceConfig:
        """Get config for specific source, falling back to defaults."""
        for override in self.source_overrides:
            if override.source_id == source_id:
                return override
        return SourceConfig(source_id, self.max_results_per_source, self.timeout_seconds)
```

---

## Summary: Methodical Approach

**Problem**: Scattered configuration logic
**Solution**: Three-layer architecture (UI → Config → Execution)

**Key Components**:
1. **SearchConfig**: Single source of truth (core/search_config.py)
2. **Factory methods**: from_ui(), from_cli(), from_monitor(), for_deep_research()
3. **Execution engines**: Consume config, never create it
4. **UI simplicity**: Translate simple controls to config objects

**Benefits**:
- Consistency across entry points
- Easy to add options (update SearchConfig, UI stays simple)
- Testable (mock config, not UI)
- Documented (one class to understand)

**Implementation**: 3-4 hours total for full migration

**Status**: Design complete, ready to implement
