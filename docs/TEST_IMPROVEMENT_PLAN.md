# Test Improvement Plan

**Date**: 2025-12-01
**Author**: Claude Code Analysis
**Status**: Planning Phase
**Estimated Effort**: 12-16 hours over 2-3 days

---

## Executive Summary

The codebase has excellent integration test coverage (94%) but critical gaps in unit testing, automation, and validation. This plan addresses:

1. **Zero unit tests** for 2,965-line recursive agent
2. **Zero prompt template tests** for 59 Jinja2 templates
3. **No CI/CD automation** (manual testing only)
4. **Missing validation** for SearchResultBuilder usage
5. **No error scenario tests** (rate limits, timeouts, etc.)

**Risk Level**: MEDIUM (integration tests catch most bugs, but core logic bugs slip through)
**Investment**: 1-2 days → Production-ready test maturity

---

## Current State Analysis

### Test Coverage Metrics

```
Total Test Files:        130
Integration Tests:       68 (excellent)
System Tests:           16
E2E Tests:               5
Performance Tests:       2
Unit Tests:              0 ← CRITICAL GAP
```

### Integration Test Quality (Audit Results)

| Metric | Coverage | Grade |
|--------|----------|-------|
| Has query generation tests | 23/23 (100%) | A+ |
| Has execution tests | 23/23 (100%) | A+ |
| Has error handling | 23/23 (100%) | A+ |
| Checks result format | 23/23 (100%) | A+ |
| Tests metadata | 22/23 (96%) | A |
| Tests relevance | 21/23 (91%) | A- |
| Multiple test cases | 18/23 (78%) | B+ |

**Overall Integration Test Grade**: **A** (excellent structure and coverage)

### Infrastructure Gaps

```
✅ pytest available
✅ Test fixtures (conftest.py)
✅ .venv with dependencies

❌ pytest.ini configuration
❌ GitHub Actions CI/CD
❌ Code coverage tracking (pytest-cov)
❌ Test isolation/mocking utilities
❌ Property-based testing (hypothesis)
❌ Snapshot testing
```

---

## Critical Gaps Detailed Analysis

### Gap 1: No Unit Tests for Core Logic

**Severity**: 🔴 HIGH
**Impact**: Can't catch regressions in core research algorithms
**Effort**: 4-6 hours

**Files Without Unit Tests**:

1. **`research/recursive_agent.py` (2,965 lines)**
   - Complex goal pursuit algorithm
   - LLM-driven decision making
   - Global evidence index management
   - Filter logic (recently fixed bug here)
   - Decomposition logic (DAG dependency handling)

2. **`research/services/entity_analyzer.py`**
   - Entity extraction from results
   - Relationship graph building
   - Mention counting and importance scoring

3. **`core/prompt_loader.py`**
   - Jinja2 template rendering
   - Temporal context injection
   - Variable substitution

4. **`core/result_builder.py`**
   - SearchResultBuilder pattern
   - Safe type conversions
   - Default value handling

**Why This Matters**:
- Filter prompt bug (commit 37ccef9) wasn't caught until user reported it
- No way to test edge cases without full E2E runs
- Changes to core logic require manual validation
- Can't use TDD for new features

**Example Bug That Would Be Caught**:
```python
# Bug: Filter passes "Consumer Reports executives" for "Anduril executives"
# Unit test would catch this:
def test_filter_rejects_different_entities():
    goal = "Key executives of Anduril Industries Inc."
    evidence = [
        Evidence(title="Consumer Reports executive director Sara Enright..."),
        Evidence(title="Palmer Luckey, Anduril founder...")
    ]
    filtered = await agent._filter_results(goal, evidence, context)

    titles = [e.title for e in filtered]
    assert "Consumer Reports" not in str(titles)  # Should reject different entity
    assert "Palmer Luckey" in str(titles)         # Should keep Anduril entity
```

---

### Gap 2: No Prompt Template Tests

**Severity**: 🔴 HIGH
**Impact**: Broken prompts not detected until runtime
**Effort**: 2-3 hours

**Files Without Tests**:
- 59 Jinja2 templates in `prompts/`
- Recently fixed: `prompts/recursive_agent/result_filtering.j2` (no test exists)
- No validation of temporal_context injection
- No testing of JSON example escaping

**Template Categories**:
```
prompts/
├── deep_research/           (8 templates)
│   ├── task_decomposition.j2
│   ├── hypothesis_generation.j2
│   ├── source_saturation.j2
│   └── ...
├── recursive_agent/         (7 templates needed, 1 exists)
│   └── result_filtering.j2  ← Just fixed, no test
└── integrations/            (44 templates)
    ├── sam_query_generation.j2
    ├── usaspending_relevance.j2
    └── ...
```

**Why This Matters**:
- Filter prompt bug went undetected for weeks
- No way to validate prompt changes before deployment
- Can't test temporal_context injection works
- JSON example escaping errors not caught

**Test Cases Needed**:

1. **Syntax Validation**
   ```python
   def test_all_templates_render_without_errors():
       """All .j2 files should render with mock context."""
       for template_path in prompts_dir.rglob("*.j2"):
           result = render_prompt(template_path, **mock_context)
           assert result is not None
           assert len(result) > 0
   ```

2. **Temporal Context Injection**
   ```python
   def test_temporal_context_injected():
       """Templates with {# temporal_context: true #} get date info."""
       result = render_prompt("recursive_agent/result_filtering.j2",
                             goal="test", evidence_text="test")
       assert "Today's date:" in result or "current_date" in result
   ```

3. **JSON Example Escaping**
   ```python
   def test_json_examples_not_interpreted():
       """JSON examples in {% raw %} blocks not processed as Jinja."""
       result = render_prompt("deep_research/task_decomposition.j2", ...)
       assert '{"example": "value"}' in result  # Literal JSON preserved
   ```

4. **Variable Substitution**
   ```python
   def test_variables_substituted_correctly():
       """Template variables replaced with actual values."""
       result = render_prompt("recursive_agent/result_filtering.j2",
                             goal="Find Anduril contracts",
                             evidence_text="[evidence here]")
       assert "Find Anduril contracts" in result
       assert "[evidence here]" in result
       assert "{{ goal }}" not in result  # Should be substituted
   ```

---

### Gap 3: No CI/CD Automation

**Severity**: 🟡 MEDIUM
**Impact**: Regressions can slip into production
**Effort**: 1-2 hours

**Current Workflow**:
```
Developer → Manual testing → Git commit → Git push → Production
               ↑
          (If they remember)
```

**Desired Workflow**:
```
Developer → Git commit → Git push → GitHub Actions
                           ↓
                      Run all tests
                           ↓
                   Pass ✅ / Fail ❌
                           ↓
                   Update PR status
                           ↓
                   Deploy if passing
```

**Infrastructure Needed**:

1. **pytest.ini Configuration**
   ```ini
   [pytest]
   testpaths = tests
   python_files = test_*.py
   python_classes = Test*
   python_functions = test_*

   markers =
       unit: Unit tests (fast, no external calls)
       integration: Integration tests (API calls allowed)
       e2e: End-to-end tests (full system)
       slow: Slow tests (>5s runtime)

   addopts =
       --strict-markers
       --tb=short
       --disable-warnings
   ```

2. **GitHub Actions Workflow**
   ```yaml
   # .github/workflows/tests.yml
   name: Tests
   on: [push, pull_request]

   jobs:
     test:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v3
         - uses: actions/setup-python@v4
           with:
             python-version: '3.12'
         - name: Install dependencies
           run: |
             python -m pip install --upgrade pip
             pip install -r requirements.txt
             pip install pytest pytest-cov pytest-asyncio
         - name: Run unit tests
           run: pytest tests/unit -v
         - name: Run integration tests
           run: pytest tests/integrations -m "not slow" -v
           env:
             SAM_GOV_API_KEY: ${{ secrets.SAM_GOV_API_KEY }}
             OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
   ```

3. **Coverage Reporting**
   ```yaml
   - name: Generate coverage report
     run: pytest --cov=research --cov=integrations --cov-report=html
   - name: Upload coverage
     uses: codecov/codecov-action@v3
   ```

**Benefits**:
- Catch regressions before merge
- No manual test execution needed
- Coverage tracking over time
- Confidence in refactoring

---

### Gap 4: Missing SearchResultBuilder Validation

**Severity**: 🟡 MEDIUM
**Impact**: TypeError crashes from None values not caught
**Effort**: 2-3 hours

**Problem**: Integration tests call `execute_search()` but don't validate internal implementation uses SearchResultBuilder correctly.

**Real-World Bug Example** (commit 34b89bf):
```python
# FEC integration had this bug:
"amount": item.get("contribution_receipt_amount")  # Could be None

# User query → TypeError: unsupported operand type(s) for +: 'NoneType' and 'float'

# Should have been:
"amount": SearchResultBuilder.safe_amount(item.get("contribution_receipt_amount"))
```

**Test Cases Needed**:

1. **Builder Usage Validation**
   ```python
   def test_integration_uses_search_result_builder():
       """Verify integration uses SearchResultBuilder, not direct dict."""
       # Inspect integration source code
       source = inspect.getsource(integration.execute_search)
       assert "SearchResultBuilder()" in source
       assert ".build()" in source
   ```

2. **None Handling**
   ```python
   @pytest.mark.parametrize("integration_name", ["sam", "usaspending", "fec"])
   async def test_integration_handles_none_values(integration_name):
       """Execute search should not raise TypeError on None API values."""
       integration = registry.get_instance(integration_name)

       # Mock API to return results with None values
       with patch.object(integration, '_fetch_from_api') as mock:
           mock.return_value = [
               {"title": None, "url": None, "amount": None, "date": None}
           ]

           result = await integration.execute_search(params, key, limit)

           # Should not raise TypeError
           assert result.success
           for item in result.results:
               assert isinstance(item.get("title"), str)  # Should have default
               assert item.get("amount") == 0.0          # Should have default
   ```

3. **Safe Method Usage**
   ```python
   def test_safe_amount_in_all_financial_integrations():
       """Financial integrations must use safe_amount() for numeric fields."""
       financial_integrations = ["sam", "usaspending", "fec"]

       for name in financial_integrations:
           integration = registry.get_instance(name)
           source = inspect.getsource(integration.execute_search)

           # If handling amounts, must use safe_amount
           if "amount" in source.lower():
               assert "safe_amount" in source, \
                   f"{name} handles amounts but doesn't use safe_amount()"
   ```

---

### Gap 5: No Error Scenario Tests

**Severity**: 🟡 MEDIUM
**Impact**: Error handling logic not validated
**Effort**: 3-4 hours

**Problem**: Tests only verify happy path. Error scenarios (rate limits, timeouts, auth failures) not tested.

**Recent Example**: Timeout detection fix (commit 7ef7b9e) has no automated test to verify it works.

**Error Patterns to Test**:

1. **Rate Limits (HTTP 429)**
   ```python
   async def test_rate_limit_skips_reformulation():
       """Rate limit errors should not attempt LLM reformulation."""
       integration = SAMIntegration()

       # Mock API to return rate limit error
       with patch.object(integration, 'execute_search') as mock:
           mock.return_value = QueryResult(
               success=False,
               error="HTTP 429: Rate limit exceeded",
               source="sam",
               results=[],
               total=0
           )

           # Agent should detect unfixable error
           agent = RecursiveResearchAgent()
           result = await agent._execute_api_call("sam", goal, params, context)

           # Should skip reformulation (check logs or internal state)
           assert "sam" in agent.rate_limited_sources
   ```

2. **Timeouts**
   ```python
   async def test_timeout_skips_reformulation():
       """Timeout errors should not attempt LLM reformulation."""
       error = "ReadTimeoutError: HTTPSConnectionPool read timed out"

       agent = RecursiveResearchAgent()
       is_unfixable = agent._is_unfixable_error(error)

       assert is_unfixable == True
   ```

3. **Auth Failures (HTTP 401/403)**
   ```python
   async def test_auth_failure_reported_clearly():
       """Auth failures should give clear error message."""
       integration = SAMIntegration()

       result = await integration.execute_search(params, api_key="invalid", limit=10)

       assert result.success == False
       assert "401" in result.error or "authentication" in result.error.lower()
   ```

4. **Validation Errors (HTTP 422)**
   ```python
   async def test_validation_error_triggers_reformulation():
       """Validation errors (422) should trigger reformulation, not skip."""
       error = "HTTP 422: Parameter 'keywords' must be at least 3 characters"

       agent = RecursiveResearchAgent()
       is_unfixable = agent._is_unfixable_error(error)

       assert is_unfixable == False  # Should attempt reformulation
   ```

5. **Network Errors**
   ```python
   async def test_connection_error_handled_gracefully():
       """Network errors should not crash, return error QueryResult."""
       integration = SAMIntegration()

       with patch('requests.get', side_effect=ConnectionError("Network unreachable")):
           result = await integration.execute_search(params, key, limit)

           assert result.success == False
           assert "connection" in result.error.lower()
   ```

---

## Implementation Plan

### Phase 1: Critical Foundation (4-6 hours)

**Goal**: Get basic automation and unit test infrastructure in place

#### Task 1.1: Create pytest.ini (15 min)
```bash
# Create pytest.ini in project root
[pytest]
testpaths = tests
python_files = test_*.py
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    slow: Slow tests (>5s)
```

**Validation**: Run `pytest --markers` to verify markers registered

#### Task 1.2: Set up GitHub Actions (30 min)
1. Create `.github/workflows/tests.yml`
2. Configure secrets (API keys)
3. Test workflow with dummy commit

**Validation**: Push commit, verify workflow runs

#### Task 1.3: Create Unit Test Structure (15 min)
```bash
tests/
├── unit/
│   ├── __init__.py
│   ├── test_recursive_agent.py
│   ├── test_prompt_loader.py
│   ├── test_result_builder.py
│   └── test_error_handling.py
└── ...
```

**Validation**: `pytest tests/unit -v` should run (even if empty)

#### Task 1.4: Add Prompt Template Validator (2 hours)
Create `tests/unit/test_prompts.py`:

```python
#!/usr/bin/env python3
"""
Unit tests for Jinja2 prompt templates.

Validates:
- All templates render without syntax errors
- Temporal context injection works
- JSON examples not interpreted as Jinja
- Variables substituted correctly
"""

import pytest
from pathlib import Path
from core.prompt_loader import render_prompt

PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"

@pytest.fixture
def mock_context():
    """Standard mock context for template rendering."""
    return {
        "goal": "Test goal",
        "evidence_text": "Test evidence",
        "original_objective": "Test objective",
        "temporal_context": "Today's date: 2025-12-01",
        "research_question": "Test question",
        "available_sources": ["source1", "source2"],
    }

class TestPromptTemplates:
    """Test suite for all Jinja2 templates."""

    def test_all_templates_render(self, mock_context):
        """All .j2 files should render without syntax errors."""
        templates = list(PROMPTS_DIR.rglob("*.j2"))
        assert len(templates) > 50, "Should find 50+ templates"

        errors = []
        for template_path in templates:
            try:
                # Attempt to render with mock context
                result = render_prompt(
                    str(template_path.relative_to(PROMPTS_DIR)),
                    **mock_context
                )
                assert result is not None
                assert len(result) > 0
            except Exception as e:
                errors.append(f"{template_path.name}: {e}")

        if errors:
            pytest.fail(f"Template rendering errors:\n" + "\n".join(errors))

    def test_temporal_context_injected(self, mock_context):
        """Templates with temporal_context directive get date info."""
        # Test filter prompt (has temporal_context: true)
        result = render_prompt(
            "recursive_agent/result_filtering.j2",
            goal="test",
            evidence_text="test",
            original_objective="test"
        )

        assert "Today's date:" in result or "2025" in result

    def test_json_examples_preserved(self, mock_context):
        """JSON in {% raw %} blocks should not be interpreted."""
        # Test any template with JSON examples
        result = render_prompt(
            "recursive_agent/result_filtering.j2",
            **mock_context
        )

        # Should contain literal JSON structure
        assert "{" in result and "}" in result
        # Should not have unsubstituted variables
        assert "{{" not in result or "{%" not in result

    def test_variables_substituted(self, mock_context):
        """Template variables should be replaced with values."""
        result = render_prompt(
            "recursive_agent/result_filtering.j2",
            goal="Find Anduril contracts",
            evidence_text="[evidence]",
            original_objective="Research defense contractors"
        )

        assert "Find Anduril contracts" in result
        assert "[evidence]" in result
        # Should not have unsubstituted placeholders
        assert "{{ goal }}" not in result
        assert "{{ evidence_text }}" not in result
```

**Validation**:
```bash
pytest tests/unit/test_prompts.py -v
# Should see 4 tests pass, validating all 59 templates
```

#### Task 1.5: Add Core Unit Tests (3 hours)
Create `tests/unit/test_recursive_agent.py`:

```python
#!/usr/bin/env python3
"""
Unit tests for RecursiveResearchAgent core logic.

Tests critical methods in isolation without API calls.
"""

import pytest
from research.recursive_agent import RecursiveResearchAgent, Evidence, GoalContext, Constraints
from datetime import datetime

@pytest.fixture
def agent():
    """Create agent with test constraints."""
    return RecursiveResearchAgent(
        constraints=Constraints(max_depth=2, max_time_seconds=60)
    )

@pytest.fixture
def context():
    """Create mock goal context."""
    return GoalContext(
        original_objective="Test objective",
        available_sources=[],
        constraints=Constraints(),
        start_time=datetime.now()
    )

class TestFilterResults:
    """Test _filter_results() method."""

    async def test_filter_rejects_different_entities(self, agent, context):
        """Filter should reject results about different entities."""
        goal = "Key executives of Anduril Industries Inc."
        evidence = [
            Evidence(
                title="Consumer Reports executive director Sara Enright",
                content="Sara Enright serves as executive director of Consumer Reports...",
                url="http://example.com/1",
                source="test"
            ),
            Evidence(
                title="Palmer Luckey, Anduril founder and executive",
                content="Palmer Luckey founded Anduril Industries and serves as...",
                url="http://example.com/2",
                source="test"
            )
        ]

        filtered = await agent._filter_results(goal, evidence, context)

        titles = [e.title for e in filtered]
        # Should reject Consumer Reports (different entity)
        assert not any("Consumer Reports" in title for title in titles)
        # Should keep Anduril (correct entity)
        assert any("Palmer Luckey" in title for title in titles)

    async def test_filter_handles_empty_input(self, agent, context):
        """Filter should handle empty evidence gracefully."""
        goal = "Test goal"
        evidence = []

        filtered = await agent._filter_results(goal, evidence, context)

        assert filtered == []

    async def test_filter_keeps_relevant_results(self, agent, context):
        """Filter should keep clearly relevant results."""
        goal = "SpaceX contracts with NASA"
        evidence = [
            Evidence(
                title="NASA awards $2.9B contract to SpaceX for lunar lander",
                content="NASA has selected SpaceX to develop...",
                url="http://example.com/1",
                source="test"
            )
        ]

        filtered = await agent._filter_results(goal, evidence, context)

        assert len(filtered) == 1
        assert "SpaceX" in filtered[0].title

class TestUnfixableErrorDetection:
    """Test error pattern detection."""

    def test_timeout_errors_are_unfixable(self, agent):
        """Timeout errors should be detected as unfixable."""
        errors = [
            "ReadTimeoutError: HTTPSConnectionPool read timed out",
            "Connection timeout after 60 seconds",
            "The handshake operation timed out",
        ]

        for error in errors:
            is_unfixable = agent._is_unfixable_error(error)
            assert is_unfixable, f"Should detect timeout: {error}"

    def test_rate_limit_errors_are_unfixable(self, agent):
        """Rate limit errors should be detected as unfixable."""
        errors = [
            "HTTP 429: Too Many Requests",
            "Rate limit exceeded",
            "Daily quota exceeded",
        ]

        for error in errors:
            is_unfixable = agent._is_unfixable_error(error)
            assert is_unfixable, f"Should detect rate limit: {error}"

    def test_validation_errors_are_fixable(self, agent):
        """Validation errors (422) should be fixable via reformulation."""
        errors = [
            "HTTP 422: Parameter 'keywords' must be at least 3 characters",
            "Invalid parameter value",
        ]

        for error in errors:
            is_unfixable = agent._is_unfixable_error(error)
            assert not is_unfixable, f"Should attempt reformulation: {error}"
```

Create `tests/unit/test_result_builder.py`:

```python
#!/usr/bin/env python3
"""
Unit tests for SearchResultBuilder.

Validates safe type conversion and default handling.
"""

import pytest
from core.result_builder import SearchResultBuilder

class TestSearchResultBuilder:
    """Test SearchResultBuilder safe methods."""

    def test_safe_amount_handles_none(self):
        """safe_amount() should return default for None."""
        result = SearchResultBuilder.safe_amount(None, default=0.0)
        assert result == 0.0

    def test_safe_amount_handles_valid_number(self):
        """safe_amount() should preserve valid numbers."""
        result = SearchResultBuilder.safe_amount(123.45)
        assert result == 123.45

    def test_safe_amount_handles_string(self):
        """safe_amount() should parse numeric strings."""
        result = SearchResultBuilder.safe_amount("123.45")
        assert result == 123.45

    def test_safe_text_handles_none(self):
        """safe_text() should return default for None."""
        result = SearchResultBuilder.safe_text(None, default="N/A")
        assert result == "N/A"

    def test_safe_text_handles_empty_string(self):
        """safe_text() should return default for empty string after stripping."""
        result = SearchResultBuilder.safe_text("   ", default="N/A")
        assert result == "N/A"

    def test_builder_no_typeerror_on_none(self):
        """Builder should not raise TypeError when all fields are None."""
        result = (SearchResultBuilder()
            .title(None)
            .url(None)
            .snippet(None)
            .date(None)
            .metadata({"amount": None})
            .build())

        # Should not raise, should have defaults
        assert result["title"] == "Untitled"
        assert result["url"] is None
        assert result["snippet"] == ""
        assert result["metadata"]["amount"] is None  # Preserved in metadata
```

**Validation**:
```bash
pytest tests/unit/ -v
# Should see ~15 tests pass
```

---

### Phase 2: Error Handling Tests (3-4 hours)

**Goal**: Validate error detection and handling logic

#### Task 2.1: Create Error Scenario Tests (3 hours)
Create `tests/unit/test_error_handling.py` (see Gap 5 for test cases)

#### Task 2.2: Add Integration Error Mocking (1 hour)
Update 5 key integration tests to mock error scenarios:
- `test_sam_live.py`: Add rate limit mock
- `test_usaspending_live.py`: Add timeout mock
- `test_fec_live.py`: Add validation error mock
- `test_newsapi_live.py`: Add auth failure mock
- `test_dvids_live.py`: Add connection error mock

**Validation**:
```bash
pytest tests/unit/test_error_handling.py -v
pytest tests/integrations/ -k "error" -v
```

---

### Phase 3: SearchResultBuilder Validation (2-3 hours)

**Goal**: Ensure all integrations use builder pattern correctly

#### Task 3.1: Add Builder Usage Tests (2 hours)
See Gap 4 for test cases

#### Task 3.2: Add Integration Audits (1 hour)
Create automated check that scans integration source code for:
- `SearchResultBuilder()` usage
- `.build()` pattern
- `safe_amount()`, `safe_text()`, `safe_date()` usage

**Validation**:
```bash
pytest tests/unit/test_result_builder.py -v
pytest tests/contracts/test_integration_contracts.py -v
```

---

### Phase 4: Coverage & Polish (2-3 hours)

**Goal**: Add coverage tracking and missing tests

#### Task 4.1: Add pytest-cov (30 min)
```bash
pip install pytest-cov
pytest --cov=research --cov=integrations --cov-report=html
```

Update GitHub Actions to track coverage.

#### Task 4.2: Add Missing Integration Test (30 min)
Create `tests/integrations/test_telegram_live.py` (only missing integration)

#### Task 4.3: Add Benchmark Tests (1 hour)
Create `tests/performance/test_benchmarks.py`:
- Query generation latency (<2s)
- Filter latency (<5s)
- Entity extraction latency (<3s)

#### Task 4.4: Documentation (1 hour)
Update `docs/TESTING.md` with:
- How to run tests
- How to add new tests
- Test markers explanation
- Coverage requirements

**Validation**:
```bash
pytest --cov=. --cov-report=term
# Should see >60% coverage
```

---

## Success Criteria

### Phase 1 Complete
- [ ] pytest.ini created and working
- [ ] GitHub Actions running on every push
- [ ] All 59 prompt templates validated
- [ ] 15+ unit tests for recursive agent core logic
- [ ] No template rendering errors

### Phase 2 Complete
- [ ] Error scenario tests for all unfixable error patterns
- [ ] 5 integration tests have mocked error scenarios
- [ ] Timeout detection logic has test coverage

### Phase 3 Complete
- [ ] SearchResultBuilder usage validated across all integrations
- [ ] No direct dict construction in integrations
- [ ] All financial integrations use `safe_amount()`

### Phase 4 Complete
- [ ] Code coverage >60% overall
- [ ] Telegram integration test added (100% coverage)
- [ ] Benchmark tests for performance regression detection
- [ ] Documentation updated

---

## Rollout Strategy

### Week 1: Foundation
- **Day 1 (4 hours)**: Phase 1 Tasks 1.1-1.3 + CI setup
- **Day 2 (4 hours)**: Phase 1 Tasks 1.4-1.5 (prompt & unit tests)
- **Checkpoint**: All phase 1 tests passing, CI running

### Week 2: Hardening
- **Day 3 (4 hours)**: Phase 2 (error handling tests)
- **Day 4 (3 hours)**: Phase 3 (SearchResultBuilder validation)
- **Checkpoint**: >60% code coverage, error handling validated

### Week 3: Polish
- **Day 5 (3 hours)**: Phase 4 (coverage, benchmarks, docs)
- **Final Review**: All success criteria met

---

## Risk Assessment

### Low Risk Items
- ✅ Adding pytest.ini (can't break anything)
- ✅ Adding unit tests (isolated from production)
- ✅ GitHub Actions (runs in parallel to manual testing)

### Medium Risk Items
- ⚠️ Refactoring integrations for testability
  - Mitigation: Add tests first, then refactor
- ⚠️ Mocking external APIs
  - Mitigation: Use integration tests as smoke tests

### High Risk Items
- 🔴 None identified (all additions, no changes to production code)

---

## Cost-Benefit Analysis

### Investment
- **Time**: 12-16 hours over 2-3 days
- **Effort**: 1 developer
- **Cost**: ~$0 (no new tools needed)

### Benefits

**Immediate** (Week 1):
- ✅ Catch template syntax errors before deployment
- ✅ Validate core filtering logic works correctly
- ✅ Automated testing on every commit

**Short-term** (Month 1):
- ✅ Prevent regressions in core research logic
- ✅ Faster debugging (unit tests pinpoint issues)
- ✅ Confidence in refactoring

**Long-term** (Quarter 1):
- ✅ 80%+ code coverage
- ✅ Performance regression detection
- ✅ New developer onboarding (tests as documentation)
- ✅ Production-ready test maturity

### ROI
**Conservative estimate**: 3x return in first month
- Prevents 1-2 production bugs (4-8 hours saved debugging)
- Enables safe refactoring (saves 2-4 hours per feature)
- Faster code reviews (tests validate correctness)

---

## Open Questions

1. **Q**: Should we mock all LLM calls in unit tests?
   **A**: Yes for true unit tests, no for integration tests. Use `@pytest.mark.unit` to distinguish.

2. **Q**: What coverage percentage should we target?
   **A**: Start with 60%, aim for 80% over 3 months. Focus on core logic first.

3. **Q**: Should we test prompt quality (LLM output correctness)?
   **A**: Out of scope for this plan. Focus on structural validation first.

4. **Q**: How do we handle flaky tests (external API dependency)?
   **A**: Use `@pytest.mark.flaky` and retry logic. If consistently flaky, mock instead.

5. **Q**: Should we add mutation testing (mutmut)?
   **A**: Nice to have, but defer until after basic coverage established.

---

## Next Steps

**Immediate** (Today):
1. Review this plan with team
2. Decide on phasing (all at once or incremental?)
3. Set up GitHub repository secrets for CI

**This Week**:
1. Create pytest.ini
2. Set up GitHub Actions
3. Add prompt template validator

**Follow-up**:
- Schedule weekly check-ins during implementation
- Update STATUS.md as phases complete
- Celebrate when hitting 60% coverage milestone!

---

## References

- Test audit results: `/tmp/test_quality_audit.py`
- Missing tests analysis: `/tmp/missing_tests_analysis.py`
- Current test coverage: 94% integrations, 0% unit tests
- Recent filter bug: commit 37ccef9
- Timeout fix: commit 7ef7b9e
- SearchResultBuilder migration: commits 34b89bf, 3e7df84

---

**Document Status**: ✅ READY FOR REVIEW
**Next Action**: Team review and approval to proceed with Phase 1
