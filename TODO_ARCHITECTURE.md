# TODO: Integration Architecture Improvements

**Created**: 2025-11-23
**Status**: Foundation complete, implementation pending
**Commits**: 3beaf75 (NewsAPI fix), 7407125 (generic fallback)

---

## **Context: What Was Done**

### **Session Goal**
Implement 3 architectural improvements:
1. ✅ **Generic fallback pattern** (search_fallback.py + metadata) - COMPLETE
2. ⏸️ **Registration structural validation** - PENDING
3. ⏸️ **Smoke test framework** - PENDING

### **Commits Made**

#### Commit 1: NewsAPI 426 Error Fix
- Fixed 426 errors by enforcing 30-day historical data limit
- 3-layer architecture: metadata → prompt → code enforcement
- Test suite: `tests/test_newsapi_date_enforcement.py` (all pass)
- Cleaned up 84k+ lines of old experimental code

#### Commit 2: Generic Search Fallback Architecture
- Created `core/search_fallback.py` (140 lines)
- Updated `integrations/source_metadata.py` with SEC EDGAR strategies
- Established reusable pattern (not integration-specific)

---

## **Architecture Pattern Established**

### **Generic Search Fallback**

**Pattern**: Metadata declares strategies → Generic helper executes → Integration provides methods

**Files**:
- `core/search_fallback.py`: Generic `execute_with_fallback()` function
- `integrations/source_metadata.py`: Strategy configuration per source

**Example Configuration** (SEC EDGAR):
```python
'SEC EDGAR': SourceMetadata(
    characteristics={
        'supports_fallback': True,
        'search_strategies': [
            {'method': 'cik', 'reliability': 'high', 'param': 'cik'},
            {'method': 'ticker', 'reliability': 'high', 'param': 'ticker'},
            {'method': 'name_exact', 'reliability': 'medium', 'param': 'company_name'},
            {'method': 'name_fuzzy', 'reliability': 'low', 'param': 'company_name'},
        ]
    }
)
```

**Example Usage** (in integration):
```python
from core.search_fallback import execute_with_fallback
from integrations.source_metadata import get_source_metadata

async def execute_search(self, query_params, api_key, limit):
    metadata = get_source_metadata("SEC EDGAR")

    if metadata.characteristics.get('supports_fallback'):
        search_methods = {
            'cik': self._search_by_cik,
            'ticker': self._search_by_ticker,
            'name_exact': self._search_by_name_exact,
            'name_fuzzy': self._search_by_name_fuzzy,
        }
        return await execute_with_fallback("SEC EDGAR", query_params, search_methods, metadata)
    else:
        # Fallback to old logic
        return await self._search_by_name_exact(query_params.get('company_name'))
```

---

## **Minor Issues to Fix**

### Issue 1: Type Annotation in search_fallback.py
**File**: `core/search_fallback.py:16`
**Problem**: `metadata: 'SourceMetadata'` uses forward reference but doesn't import
**Fix**:
```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from integrations.source_metadata import SourceMetadata
```

### Issue 2: Missing None Check
**File**: `core/search_fallback.py:60`
**Problem**: Doesn't validate metadata is not None
**Fix**:
```python
if not metadata:
    raise ValueError(f"{source_name}: No metadata provided")
```

### Issue 3: Optional Callable Validation
**File**: `core/search_fallback.py:86`
**Problem**: Doesn't verify search_func is callable
**Fix** (optional):
```python
if not callable(search_func):
    raise ValueError(f"{method_name} is not callable")
```

---

## **Remaining High-Priority Work**

### **1. Update SEC EDGAR Integration** ⏸️ NOT STARTED

**Goal**: Migrate SEC EDGAR to use generic fallback pattern

**Files to Modify**:
- `integrations/government/sec_edgar_integration.py`

**Steps**:
1. Read current implementation of `execute_search()`
2. Create helper methods:
   - `_search_by_cik(cik: str) -> QueryResult`
   - `_search_by_ticker(ticker: str) -> QueryResult`
   - `_search_by_name_exact(name: str) -> QueryResult`
   - `_search_by_name_fuzzy(name: str) -> QueryResult`
3. Update `execute_search()` to use `execute_with_fallback()`
4. Test with real query (e.g., "Lockheed Martin")
5. Verify fallback works (ticker fails → tries name)

**Estimated Time**: 1-2 hours

---

### **2. Add Registration Structural Validation** ⏸️ NOT STARTED

**Goal**: Enforce architectural consistency at registration time

**Files to Modify**:
- `integrations/registry.py`

**Implementation**:
```python
def register(self, integration_id: str, integration_class: Type[DatabaseIntegration]):
    """Register with architectural validation."""

    # Validation 1: Required methods exist
    required_methods = ['metadata', 'is_relevant', 'generate_query', 'execute_search']
    missing = [m for m in required_methods if not hasattr(integration_class, m)]
    if missing:
        raise ValueError(f"{integration_id} missing required methods: {missing}")

    # Validation 2: Source metadata exists
    from integrations.source_metadata import get_source_metadata
    temp = integration_class()
    metadata = get_source_metadata(temp.metadata.name)
    if not metadata:
        raise ValueError(f"{integration_id} missing source_metadata entry for '{temp.metadata.name}'")

    # Validation 3: Prompt template exists (warning only)
    prompt_path = f"prompts/integrations/{integration_id}_query_generation.j2"
    if not os.path.exists(prompt_path):
        print(f"⚠️  {integration_id}: No prompt template at {prompt_path}")

    # Validation 4: Metadata ID consistency
    if temp.metadata.id != integration_id:
        raise ValueError(
            f"{integration_id}: metadata.id ('{temp.metadata.id}') "
            f"doesn't match registration ID"
        )

    # All passed - register
    self._integration_classes[integration_id] = integration_class
    print(f"✅ {integration_id} registered with validation")
```

**Testing**:
1. Run existing system - verify all integrations still register
2. Create test integration with missing method - verify it fails
3. Create test integration with missing metadata - verify it fails

**Estimated Time**: 1 hour

---

### **3. Add Smoke Test Framework** ⏸️ NOT STARTED

**Goal**: Optional validation of all registered integrations

**Files to Modify**:
- `integrations/registry.py`

**Implementation**:
```python
def validate_integration(self, integration_id: str) -> Dict[str, bool]:
    """Run smoke tests on a registered integration."""
    results = {}

    try:
        integration = self.get_instance(integration_id)

        # Test 1: Can instantiate?
        results['instantiation'] = integration is not None

        # Test 2: Metadata valid?
        metadata = integration.metadata
        results['metadata_valid'] = bool(metadata.name and metadata.id and metadata.category)

        # Test 3: generate_query returns valid structure?
        try:
            query = await integration.generate_query("test query")
            results['query_generation'] = isinstance(query, (dict, type(None)))
        except Exception:
            results['query_generation'] = False

        # Test 4: execute_search handles errors gracefully?
        try:
            result = await integration.execute_search({}, None, 1)
            results['graceful_errors'] = isinstance(result, QueryResult)
        except Exception:
            results['graceful_errors'] = False

    except Exception as e:
        results['error'] = str(e)

    return results

def validate_all(self) -> Dict[str, Dict[str, bool]]:
    """Run smoke tests on ALL registered integrations."""
    results = {}
    for integration_id in self._integration_classes:
        results[integration_id] = self.validate_integration(integration_id)
    return results
```

**Usage**:
```python
# In development
registry = IntegrationRegistry()
results = registry.validate_all()

# Print report
for integration_id, tests in results.items():
    passed = sum(tests.values())
    total = len(tests)
    print(f"{integration_id}: {passed}/{total} tests passed")
```

**Estimated Time**: 1 hour

---

### **4. Write Tests for Fallback Helper** ⏸️ NOT STARTED

**Goal**: Test coverage for `core/search_fallback.py`

**File to Create**:
- `tests/test_search_fallback.py`

**Test Cases**:
1. First strategy succeeds (should return immediately)
2. First strategy fails, second succeeds (should fallback)
3. All strategies fail (should return comprehensive error)
4. Strategy skipped (param not in query_params)
5. Search method not implemented (should skip)
6. Metadata missing search_strategies (should raise ValueError)

**Estimated Time**: 30 minutes

---

## **Lower Priority Improvements**

### **5. Federal Register Parameter Validation** ⏸️ NOT STARTED

**Current Problem**: Federal Register may generate invalid API params

**Solution**: Apply NewsAPI pattern (3-layer validation)
1. Declare valid params in source_metadata.py
2. Update federal_register_query_generation.j2 prompt
3. Add param validation in execute_search()

**Estimated Time**: 30 minutes

---

## **Testing Checklist**

After completing remaining work:

**Unit Tests**:
- [ ] test_search_fallback.py created and passing
- [ ] test_newsapi_date_enforcement.py still passing
- [ ] All existing tests still pass

**Integration Tests**:
- [ ] SEC EDGAR search with fallback works
- [ ] All 22 integrations still register successfully
- [ ] registry.validate_all() shows all integrations healthy

**E2E Tests**:
- [ ] Run `python3 apps/ai_research.py "Lockheed Martin SEC filings"`
- [ ] Verify SEC EDGAR uses fallback (check execution_log.jsonl)
- [ ] No regressions in existing integrations

---

## **Architecture Quality Checklist**

**Before merging**:
- [ ] No hardcoded heuristics (all decisions LLM-driven or metadata-declared)
- [ ] No per-integration carve-outs (patterns are reusable)
- [ ] DRY principle followed (no duplicated logic)
- [ ] Separation of concerns maintained (data/execution/integration layers)
- [ ] Backward compatible (existing integrations unaffected)
- [ ] Well-documented (comments explain why, not just what)
- [ ] Clean commits (logical units with clear messages)

---

## **Session Handoff Notes**

**Token Usage**: 126k/200k used (substantial work requires fresh session)

**Git Status**: Clean (2 commits made, no uncommitted changes)

**What Works**:
- ✅ NewsAPI 426 errors fixed
- ✅ Generic fallback helper exists and is sound
- ✅ SEC EDGAR metadata configured for fallback

**What's Incomplete**:
- ⚠️ SEC EDGAR integration not migrated yet
- ⚠️ No registration validation
- ⚠️ No smoke tests
- ⚠️ Minor issues in search_fallback.py (see above)

**Architecture Established**:
- 3-layer pattern (NewsAPI proof-of-concept)
- Generic fallback pattern (foundation ready)
- Both are reusable, scalable, architecturally clean

**Next Session Should**:
1. Fix minor issues in search_fallback.py
2. Complete SEC EDGAR migration
3. Add registration validation
4. Add smoke tests
5. Comprehensive testing

**Estimated Time for Completion**: 4-5 hours of focused work

---

## **Quick Start for Next Session**

```bash
# Verify current state
git log --oneline -3
git status

# Read this document
cat TODO_ARCHITECTURE.md

# Read established patterns
cat core/search_fallback.py
grep -A20 "SEC EDGAR" integrations/source_metadata.py

# Start with SEC EDGAR migration
cat integrations/government/sec_edgar_integration.py | head -100

# Or start with registration validation
cat integrations/registry.py | grep -A30 "def register"
```

---

**End of TODO Document**
