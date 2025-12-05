# Error Handling Architecture

**Status**: Planning Phase
**Created**: 2025-12-01
**Priority**: P1 - Critical for reliability

---

## Problem Statement

**Current State** (Pattern Matching):
- Brittle text pattern matching for error classification
- Incomplete coverage (missing 401, 403, 404, 500-504)
- Mixed concerns (agent doing text parsing)
- No structured error information
- Inconsistent handling across integrations

**Issues Discovered**:
1. DVIDS integration sends string "null" for dates → HTTP 400
2. System attempts reformulation on HTTP 403 (should skip - auth/rate limit)
3. HTTP status codes not propagated from integrations
4. Text patterns miss many error categories

---

## Optimal Architecture: Structured Error Model

### Design Principles

1. **Separation of Concerns**
   - Error classification: Centralized in `ErrorClassifier`
   - Integration: Returns structured data
   - Agent: Simple decision logic based on flags

2. **HTTP Status Codes First, Patterns Second**
   - HTTP codes are reliable and standardized
   - Text patterns only for non-HTTP errors (timeouts, network)

3. **Configuration-Driven**
   - All error codes and patterns in config.yaml
   - Easy to extend without code changes

4. **Structured Data Over Strings**
   - `APIError` dataclass with categorization
   - Boolean flags for decision logic (`is_reformulable`, `is_retryable`)

---

## Architecture Layers

### Layer 1: Error Classification (`core/error_classifier.py`)

**Purpose**: Centralized error categorization logic

```python
@dataclass
class APIError:
    """Structured error representation."""
    http_code: Optional[int]          # HTTP status code (if HTTP error)
    category: ErrorCategory            # Semantic category
    message: str                       # Original error message
    is_retryable: bool                # Can we retry same query later?
    is_reformulable: bool             # Can we fix by changing query?
    source_id: str                    # Which integration failed

class ErrorCategory(Enum):
    """Semantic error categories."""
    AUTHENTICATION = "auth"      # 401, 403
    RATE_LIMIT = "rate_limit"    # 429
    VALIDATION = "validation"    # 400, 422 (fixable by reformulation)
    NOT_FOUND = "not_found"      # 404
    SERVER_ERROR = "server"      # 500, 502, 503, 504
    TIMEOUT = "timeout"          # Timeout patterns
    NETWORK = "network"          # Connection errors
    UNKNOWN = "unknown"          # Fallback
```

**Classification Logic**:
1. HTTP code-based (most reliable)
2. Text pattern fallback (for non-HTTP errors)
3. Conservative defaults for unknowns

### Layer 2: Integration Changes

**Add HTTP Code to QueryResult**:
```python
@dataclass
class QueryResult:
    source: str
    success: bool
    results: List[Dict]
    error: Optional[str] = None
    http_code: Optional[int] = None  # NEW FIELD
    metadata: Dict = field(default_factory=dict)
```

**Integration Pattern**:
```python
async def execute_search(...) -> QueryResult:
    try:
        response = await make_request(...)
        response.raise_for_status()
        # ... process results ...
    except requests.HTTPError as e:
        return QueryResult(
            source="integration_name",
            success=False,
            error=str(e),
            http_code=e.response.status_code,  # Extract HTTP code
            results=[]
        )
    except Exception as e:
        return QueryResult(
            source="integration_name",
            success=False,
            error=str(e),
            http_code=None,  # Non-HTTP error
            results=[]
        )
```

### Layer 3: Agent Simplification

**Before** (Complex):
```python
error_msg = str(result.error or "").lower()
patterns = config.get('research', {}).get('error_handling', {}).get('unfixable_error_patterns', [...])
is_unfixable = any(term.lower() in error_msg for term in patterns)

if is_unfixable:
    is_rate_limit = any(...)
    is_timeout = any(...)
    # Complex branching logic...
```

**After** (Simple):
```python
error = self.error_classifier.classify(
    result.error,
    result.http_code,
    source_id
)

if error.category == ErrorCategory.RATE_LIMIT:
    self.rate_limited_sources.add(source_id)
    return []

if error.is_reformulable and attempts < max_retries:
    reformulated = await self._reformulate_on_error(...)
else:
    return []
```

### Layer 4: Configuration

```yaml
research:
  error_handling:
    # HTTP Status Code Classification
    unfixable_http_codes:
      - 401  # Unauthorized
      - 403  # Forbidden
      - 404  # Not Found
      - 429  # Too Many Requests
      - 500  # Internal Server Error
      - 502  # Bad Gateway
      - 503  # Service Unavailable
      - 504  # Gateway Timeout

    fixable_http_codes:
      - 400  # Bad Request (validation)
      - 422  # Unprocessable Entity

    # Text Pattern Fallbacks (for non-HTTP errors)
    timeout_patterns:
      - "timed out"
      - "timeout"
      - "TimeoutError"
      - "ReadTimeoutError"
      - "ConnectTimeout"
      - "handshake operation timed out"

    rate_limit_patterns:
      - "rate limit"
      - "429"
      - "quota exceeded"
      - "too many requests"
      - "throttl"
      - "daily limit"

    # Retry Configuration
    max_reformulation_attempts: 2
    rate_limit_cooldown_seconds: 300  # 5 minutes
```

---

## Benefits

### 1. Testability
```python
def test_http_403_not_reformulable():
    classifier = ErrorClassifier(config)
    error = classifier.classify("Forbidden", 403, "dvids")
    assert error.is_reformulable == False
    assert error.category == ErrorCategory.AUTHENTICATION
```

### 2. Clarity
- No more ambiguous text pattern matching
- Boolean flags make intent explicit
- Categories enable better logging/metrics

### 3. Extensibility
- Add new HTTP codes → Update config
- Add new patterns → Update config
- Add new categories → Extend enum (rare)

### 4. Consistency
- All integrations use same error model
- All errors classified uniformly
- Same decision logic everywhere

---

## Implementation Plan

### Phase 1: Foundation (2 hours)
**Priority**: P0 - Blocking current bugs

1. **Task 1.1**: Add missing HTTP codes to config (15 min)
   - Add 401, 403, 404, 500-504 to unfixable_http_codes
   - Test: Verify 403 errors don't trigger reformulation

2. **Task 1.2**: Fix DVIDS "null" date bug (30 min)
   - Add validation in query generation prompt
   - Add validation in integration code
   - Test: Verify no more "nullT00:00:00Z" URLs

3. **Task 1.3**: Create ErrorClassifier skeleton (45 min)
   - Define APIError dataclass
   - Define ErrorCategory enum
   - Create ErrorClassifier class with classify() method
   - Unit tests for classification logic

4. **Task 1.4**: Update QueryResult dataclass (30 min)
   - Add http_code: Optional[int] field
   - Update base class documentation
   - Verify backward compatibility (default None)

### Phase 2: Integration Updates (4 hours)
**Priority**: P1 - High value, moderate effort

5. **Task 2.1**: Update 5 high-traffic integrations (2 hours)
   - SAM.gov, USAspending, Brave Search, NewsAPI, DVIDS
   - Extract HTTP codes in exception handlers
   - Return http_code in QueryResult
   - Test each integration with error scenarios

6. **Task 2.2**: Update remaining 24 integrations (2 hours)
   - Batch update in groups of 6
   - Use same pattern from Task 2.1
   - Smoke test each group

### Phase 3: Agent Refactor (3 hours)
**Priority**: P1 - Simplifies core logic

7. **Task 3.1**: Integrate ErrorClassifier into agent (1 hour)
   - Initialize classifier in __init__
   - Replace pattern matching with classifier.classify()
   - Update decision logic to use error.is_reformulable

8. **Task 3.2**: Simplify error handling logic (1 hour)
   - Remove complex pattern matching code
   - Use error.category for logging
   - Update rate limit handling

9. **Task 3.3**: Add structured error logging (1 hour)
   - Log APIError fields to execution log
   - Add error_classification event type
   - Update log schema documentation

### Phase 4: Testing & Validation (2 hours)
**Priority**: P1 - Ensure no regressions

10. **Task 4.1**: Unit tests for ErrorClassifier (45 min)
    - Test all HTTP codes
    - Test all text patterns
    - Test edge cases (None, empty string)

11. **Task 4.2**: Integration error tests (45 min)
    - Mock HTTP errors for each category
    - Verify correct QueryResult.http_code
    - Verify no reformulation on 403

12. **Task 4.3**: E2E error handling test (30 min)
    - Trigger rate limit → verify session blocklist
    - Trigger 403 → verify no reformulation
    - Trigger 422 → verify reformulation happens

### Phase 5: Documentation & Cleanup (1 hour)
**Priority**: P2 - Polish

13. **Task 5.1**: Update PATTERNS.md (20 min)
    - Document ErrorClassifier pattern
    - Document integration error handling pattern

14. **Task 5.2**: Update STATUS.md (20 min)
    - Mark error handling architecture as complete
    - Document new error categories

15. **Task 5.3**: Remove deprecated code (20 min)
    - Remove old pattern matching logic
    - Clean up config (keep patterns for backward compat)

---

## Total Effort: 12 hours

**Breakdown**:
- Phase 1 (Foundation): 2 hours
- Phase 2 (Integrations): 4 hours
- Phase 3 (Agent): 3 hours
- Phase 4 (Testing): 2 hours
- Phase 5 (Documentation): 1 hour

**Timeline**: 2-3 days of focused work

---

## Success Criteria

### Before Migration
- ❌ 403 errors trigger reformulation (waste LLM calls)
- ❌ DVIDS sends "nullT00:00:00Z" (malformed dates)
- ❌ No HTTP codes propagated (can't distinguish errors)
- ❌ 15 error patterns in config (incomplete)

### After Migration
- ✅ 403 errors skip reformulation immediately
- ✅ DVIDS validates dates before API call
- ✅ All integrations return HTTP codes
- ✅ 30+ HTTP codes + patterns classified
- ✅ Structured error logging with categories
- ✅ 100% test coverage for error classification

---

## Risk Assessment

### Low Risk ✅
- Adding http_code field (backward compatible - defaults to None)
- Creating ErrorClassifier (new code, doesn't break existing)
- Config updates (additive, no breaking changes)

### Medium Risk ⚠️
- Updating 29 integrations (tedious, but mechanical)
  - Mitigation: Update in batches, test each batch
- Agent refactor (touches core logic)
  - Mitigation: Keep old code commented until validated

### High Risk 🔴
- None identified

---

## Open Questions

1. **Rate limit cooldown**: Should we implement automatic retry after cooldown?
   - Current: Skip source for entire session
   - Proposed: Add to retry queue with 5-minute cooldown
   - Decision: Defer to Phase 6 (future enhancement)

2. **Error metrics**: Should we track error rates per integration?
   - Useful for identifying flaky integrations
   - Decision: Yes, add to execution log analysis

3. **User-facing errors**: Should we surface error categories to user?
   - Current: Generic "API error" in logs
   - Proposed: "Rate limited by SAM.gov" in report
   - Decision: Yes, improves transparency

---

## References

- **Current Implementation**: `research/recursive_agent.py` lines 1274-1340
- **Config**: `config_default.yaml` lines 353-378
- **Test Improvement Plan**: `docs/TEST_IMPROVEMENT_PLAN.md` Phase 2
- **DVIDS Integration**: `integrations/government/dvids_integration.py` lines 237-242

---

## Appendix: Error Category Decision Tree

```
API Error Occurs
    ↓
HTTP Code Available?
    ├─ YES → Classify by HTTP Code
    │   ├─ 401, 403 → AUTHENTICATION (not reformulable, not retryable)
    │   ├─ 404 → NOT_FOUND (not reformulable, not retryable)
    │   ├─ 429 → RATE_LIMIT (not reformulable, retryable with cooldown)
    │   ├─ 400, 422 → VALIDATION (reformulable, not retryable)
    │   ├─ 500-504 → SERVER_ERROR (not reformulable, retryable)
    │   └─ Other → UNKNOWN (conservative: not reformulable)
    │
    └─ NO → Classify by Text Pattern
        ├─ "timeout", "timed out" → TIMEOUT (not reformulable, retryable)
        ├─ "rate limit", "quota" → RATE_LIMIT (not reformulable, retryable)
        └─ Other → UNKNOWN (conservative: not reformulable)
```

---

## Appendix: HTTP Status Code Reference

**1xx Informational**: Not errors
**2xx Success**: Not errors
**3xx Redirection**: Usually handled by HTTP library

**4xx Client Errors**:
- **400 Bad Request**: Malformed request (fixable by reformulation)
- **401 Unauthorized**: Missing/invalid credentials (not fixable)
- **403 Forbidden**: Valid credentials but no permission (not fixable)
- **404 Not Found**: Resource doesn't exist (not fixable)
- **422 Unprocessable Entity**: Semantic validation error (fixable by reformulation)
- **429 Too Many Requests**: Rate limit (not fixable, retryable later)

**5xx Server Errors**:
- **500 Internal Server Error**: Server bug (not fixable, maybe retryable)
- **502 Bad Gateway**: Upstream server error (not fixable, retryable)
- **503 Service Unavailable**: Temporary overload (not fixable, retryable)
- **504 Gateway Timeout**: Upstream timeout (not fixable, retryable)
