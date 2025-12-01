# Testing Quick Reference

**Last Updated**: 2025-12-01

Quick reference guide for running tests and understanding test structure.

---

## Running Tests

### All Tests
```bash
source .venv/bin/activate
pytest
```

### By Category
```bash
pytest tests/integrations/     # Integration tests (API calls)
pytest tests/unit/             # Unit tests (fast, isolated)
pytest tests/system/           # System tests
pytest tests/performance/      # Performance tests
```

### By Marker (once pytest.ini created)
```bash
pytest -m unit                 # Only unit tests
pytest -m integration          # Only integration tests
pytest -m "not slow"           # Skip slow tests
```

### Specific Integration
```bash
pytest tests/integrations/test_usaspending_live.py -v
pytest tests/integrations/ -k "sam" -v  # All SAM.gov tests
```

### With Output
```bash
pytest -v                      # Verbose
pytest -s                      # Show print statements
pytest -vv                     # Very verbose
pytest --tb=short              # Short traceback
```

---

## Test Structure

### Current Organization
```
tests/
├── integrations/        # 68 tests (94% coverage)
│   ├── test_*_live.py   # Live API tests
│   └── conftest.py      # Shared fixtures
├── system/              # 16 tests
├── performance/         # 2 tests
├── features/            # Feature-specific tests
├── contracts/           # Contract tests (interface validation)
└── unit/                # ← NEW (Phase 1)
    ├── test_recursive_agent.py
    ├── test_prompts.py
    ├── test_result_builder.py
    └── test_error_handling.py
```

---

## Test Quality Standards

### Every Integration Test Should Have

1. **Metadata Test**
   ```python
   def test_metadata():
       metadata = integration.metadata
       assert metadata.name
       assert metadata.id
       assert metadata.description
   ```

2. **Relevance Test**
   ```python
   async def test_relevance():
       relevant = await integration.is_relevant("query about X")
       assert isinstance(relevant, bool)
   ```

3. **Query Generation Test**
   ```python
   async def test_query_generation():
       params = await integration.generate_query("query")
       assert params is not None or params is None  # Can return None
   ```

4. **Execution Test**
   ```python
   async def test_execution():
       result = await integration.execute_search(params, key, limit)
       assert isinstance(result, QueryResult)
       assert result.source == "integration_name"
   ```

5. **Error Handling**
   ```python
   async def test_error_handling():
       # Test with invalid params or no API key
       result = await integration.execute_search(invalid_params, None, 10)
       if not result.success:
           assert result.error is not None
   ```

---

## Common Patterns

### Async Test
```python
import pytest

@pytest.mark.asyncio
async def test_something():
    result = await async_function()
    assert result
```

### Fixtures
```python
@pytest.fixture
def integration():
    """Reusable integration instance."""
    return MyIntegration()

def test_with_fixture(integration):
    # Use integration here
    pass
```

### Mocking
```python
from unittest.mock import patch, Mock

@patch('module.function')
def test_with_mock(mock_func):
    mock_func.return_value = "mocked"
    result = function_that_calls_mock()
    assert result == "mocked"
```

### Parametrize
```python
@pytest.mark.parametrize("input,expected", [
    ("query1", True),
    ("query2", False),
])
async def test_multiple_cases(input, expected):
    result = await function(input)
    assert result == expected
```

---

## Creating New Tests

### New Integration Test

1. **Copy template**:
   ```bash
   cp tests/integrations/test_usaspending_live.py \
      tests/integrations/test_myintegration_live.py
   ```

2. **Update imports and class name**

3. **Add 5 standard tests** (see "Test Quality Standards" above)

4. **Run it**:
   ```bash
   pytest tests/integrations/test_myintegration_live.py -v
   ```

### New Unit Test

1. **Create file**:
   ```bash
   touch tests/unit/test_mymodule.py
   ```

2. **Add test class**:
   ```python
   import pytest

   class TestMyModule:
       def test_function_name(self):
           result = function()
           assert result == expected
   ```

3. **Run it**:
   ```bash
   pytest tests/unit/test_mymodule.py -v
   ```

---

## Debugging Failed Tests

### Run Single Test
```bash
pytest tests/integrations/test_sam_live.py::test_query_generation -v
```

### Show Print Statements
```bash
pytest -s tests/integrations/test_sam_live.py
```

### Drop into Debugger on Failure
```bash
pytest --pdb tests/integrations/test_sam_live.py
```

### Show Full Traceback
```bash
pytest --tb=long tests/integrations/test_sam_live.py
```

### Show Warnings
```bash
pytest -v --tb=short tests/integrations/test_sam_live.py
```

---

## Common Issues

### Issue: `ModuleNotFoundError`
**Solution**: Activate venv first
```bash
source .venv/bin/activate
pytest
```

### Issue: `fixture not found`
**Solution**: Check conftest.py exists in test directory

### Issue: API key errors
**Solution**: Check .env file has required keys
```bash
# Required for most government integrations
SAM_GOV_API_KEY=your_key
USAJOBS_API_KEY=your_key
OPENAI_API_KEY=your_key
```

### Issue: Rate limit errors
**Solution**: Expected for SAM.gov - test validates error handling
```python
if "429" in result.error:
    print("Rate limited (expected)")
```

### Issue: Slow tests
**Solution**: Use markers to skip slow tests
```bash
pytest -m "not slow"
```

---

## Test Metrics

### Current Status (2025-12-01)

| Metric | Value | Grade |
|--------|-------|-------|
| Total test files | 130 | A+ |
| Integration coverage | 94% (18/19) | A |
| Integration test quality | 100% (all have required tests) | A+ |
| Unit test coverage | 0% | F |
| CI/CD automation | None | F |

**Priority**: Add unit tests and CI/CD (see TEST_IMPROVEMENT_PLAN.md)

---

## Best Practices

### DO ✅
- Test metadata, relevance, query generation, execution, errors
- Use SearchResultBuilder for all integrations
- Handle None values gracefully
- Use async/await for async functions
- Add docstrings explaining what test validates
- Use fixtures for reusable setup
- Parametrize when testing multiple similar cases

### DON'T ❌
- Skip error handling tests
- Hardcode API keys in test files (use .env)
- Test implementation details (test behavior)
- Use `sleep()` to wait for results (use async)
- Ignore warnings (fix them)
- Commit failing tests (mark as xfail if needed)

---

## Future Enhancements

**Planned** (see TEST_IMPROVEMENT_PLAN.md):
1. ✅ pytest.ini configuration
2. ✅ GitHub Actions CI/CD
3. ✅ Unit tests for core logic
4. ✅ Prompt template validator
5. ✅ Error scenario tests
6. ✅ Code coverage tracking (pytest-cov)
7. ⏳ Property-based testing (hypothesis)
8. ⏳ Mutation testing (mutmut)
9. ⏳ Snapshot testing

---

## Resources

- **Main Plan**: `docs/TEST_IMPROVEMENT_PLAN.md`
- **Integration Template**: `tests/integrations/test_usaspending_live.py`
- **Pytest Docs**: https://docs.pytest.org/
- **Async Testing**: https://pytest-asyncio.readthedocs.io/

---

## Quick Commands Reference

```bash
# Setup
source .venv/bin/activate

# Run all tests
pytest

# Run fast tests only
pytest -m "not slow"

# Run with coverage
pytest --cov=research --cov=integrations

# Run specific test
pytest tests/integrations/test_sam_live.py::test_query_generation -v

# Debug failed test
pytest --pdb tests/integrations/test_sam_live.py

# Show print statements
pytest -s tests/integrations/test_sam_live.py

# Verbose output
pytest -vv tests/integrations/test_sam_live.py
```
