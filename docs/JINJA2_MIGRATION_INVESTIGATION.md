# Jinja2 Template Migration - Comprehensive Investigation

**Date**: 2025-11-01
**Investigator**: Claude Code
**Status**: INVESTIGATION ONLY - NO CHANGES MADE
**Requested By**: User

---

## Executive Summary

User wants to migrate from f-string prompts with manual `{{` `}}` escaping to Jinja2 templates for all LLM prompts containing JSON examples.

**Scope**: 18 prompt files across 13 Python modules (2,100+ lines total)
**Estimated Effort**: 12-16 hours (including testing)
**Risk Level**: MEDIUM-HIGH (touches 13 production files)
**Dependencies**: Jinja2 already installed (v3.1.6)

---

## Current State Analysis

### Files with Escaped JSON Prompts

**Count of `{{` occurrences per file** (indicates JSON examples in f-strings):

| File | `{{` Count | Prompt Functions | Priority |
|------|-----------|------------------|----------|
| research/deep_research.py | 8 | 7 | HIGH |
| integrations/social/brave_search_integration.py | 4 | 1 | HIGH |
| integrations/government/federal_register.py | 4 | 1 | MEDIUM |
| integrations/government/clearancejobs_integration.py | 1 | 1 | MEDIUM |
| integrations/government/dvids_integration.py | 1 | 1 | MEDIUM |
| integrations/government/fbi_vault.py | 1 | 1 | MEDIUM |
| integrations/government/sam_integration.py | 1 | 1 | MEDIUM |
| integrations/government/usajobs_integration.py | 1 | 1 | MEDIUM |
| integrations/social/discord_integration.py | 1 | 1 | MEDIUM |
| integrations/social/reddit_integration.py | 1 | 1 | MEDIUM |
| integrations/social/twitter_integration.py | 1 | 1 | MEDIUM |

**Total**: 25 escaped JSON blocks across 11 files

### Prompt Functions Identified

**research/deep_research.py** (7 prompts - 2,097 lines total):
1. Line 567: `_break_into_tasks()` - Task decomposition
2. Line 769: `_select_sources()` - Source selection
3. Line 1453: `_extract_entities()` - Entity extraction
4. Line 1547: `_evaluate_relevance()` - Relevance scoring
5. Line 1626: `_reformulate_for_relevance()` - Query reformulation (HAS JSON EXAMPLE)
6. Line 1721: `_reformulate_query_simple()` - Simple reformulation (HAS JSON EXAMPLE)
7. Line 1976: `_synthesize_report()` - Final report generation

**Integration Files** (10 files, ~200-400 lines each):
- Each has 1 `generate_query()` method with JSON schema example
- All follow same pattern: LLM generates query params + reasoning
- JSON examples show structure for source-specific parameters

---

## Proposed Architecture

### 1. Directory Structure

```
sam_gov/
├── prompts/                          # NEW: Template directory
│   ├── __init__.py                  # NEW: Jinja2 environment setup
│   ├── deep_research/               # NEW: Deep research prompts
│   │   ├── task_decomposition.j2
│   │   ├── source_selection.j2
│   │   ├── entity_extraction.j2
│   │   ├── relevance_evaluation.j2
│   │   ├── query_reformulation_relevance.j2
│   │   ├── query_reformulation_simple.j2
│   │   └── report_synthesis.j2
│   ├── integrations/                # NEW: Integration prompts
│   │   ├── government/
│   │   │   ├── sam_query.j2
│   │   │   ├── dvids_query.j2
│   │   │   ├── usajobs_query.j2
│   │   │   ├── clearancejobs_query.j2
│   │   │   ├── fbi_vault_query.j2
│   │   │   └── federal_register_query.j2
│   │   └── social/
│   │       ├── twitter_query.j2
│   │       ├── reddit_query.j2
│   │       ├── discord_query.j2
│   │       └── brave_search_query.j2
│   └── schemas/                     # NEW: JSON schema examples
│       ├── param_adjustments.json   # Example JSON structures
│       ├── reddit_params.json
│       └── usajobs_params.json
├── research/
│   └── deep_research.py             # MODIFY: Use template loader
├── integrations/
│   ├── government/                  # MODIFY: 6 files
│   └── social/                      # MODIFY: 4 files
└── core/
    └── prompt_loader.py             # NEW: Centralized template loader
```

### 2. Core Infrastructure

**NEW FILE**: `core/prompt_loader.py`
```python
"""
Centralized Jinja2 prompt template loader.

Provides consistent interface for loading and rendering
LLM prompts with JSON examples (no escaping needed).
"""
from pathlib import Path
from typing import Dict, Any
from jinja2 import Environment, FileSystemLoader, select_autoescape

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent

# Create Jinja2 environment
env = Environment(
    loader=FileSystemLoader(PROJECT_ROOT / "prompts"),
    autoescape=select_autoescape(),  # Auto-escape HTML (not needed for LLM prompts)
    trim_blocks=True,           # Remove first newline after block
    lstrip_blocks=True,         # Strip leading whitespace before block
    keep_trailing_newline=True  # Preserve final newline
)

def render_prompt(template_name: str, **kwargs: Any) -> str:
    """
    Render a Jinja2 prompt template.

    Args:
        template_name: Path to template relative to prompts/ dir
                      (e.g., "deep_research/task_decomposition.j2")
        **kwargs: Variables to pass to template

    Returns:
        Rendered prompt string

    Example:
        >>> prompt = render_prompt(
        ...     "deep_research/task_decomposition.j2",
        ...     research_question="What is X?",
        ...     max_tasks=5
        ... )
    """
    template = env.get_template(template_name)
    return template.render(**kwargs)

def validate_template(template_name: str) -> bool:
    """Check if template exists and is valid."""
    try:
        env.get_template(template_name)
        return True
    except Exception:
        return False
```

**NEW FILE**: `prompts/__init__.py`
```python
"""
LLM prompt templates using Jinja2.

All prompts are stored as .j2 files to avoid f-string/JSON conflicts.
No escaping needed - JSON examples are raw in template files.
"""
from core.prompt_loader import render_prompt, validate_template

__all__ = ["render_prompt", "validate_template"]
```

### 3. Template Example

**NEW FILE**: `prompts/deep_research/query_reformulation_relevance.j2`
```jinja2
The search query returned results that are OFF-TOPIC for the research question.

Research Question: {{ research_question }}
Original Query: {{ original_query }}
Results Count: {{ results_count }}

The results are not answering the research question. Reformulate the query to get MORE RELEVANT results.

Return JSON with:
{
  "query": "new query text",
  "param_adjustments": {
    "reddit": {"time_filter": "year"},
    "usajobs": {"keywords": "broad keyword"}
  }
}

IMPORTANT: Keep the query focused on the research question. Don't drift off-topic.
```

**Note**: NO ESCAPING NEEDED - `{` and `}` are literal in Jinja2 templates!

### 4. Code Migration Pattern

**BEFORE** (research/deep_research.py lines ~1626-1700):
```python
async def _reformulate_for_relevance(
    self,
    original_query: str,
    research_question: str,
    results_count: int
) -> Dict[str, Any]:
    prompt = f"""The search query returned results that are OFF-TOPIC.

Research Question: {research_question}
Original Query: {original_query}
Results Count: {results_count}

Return JSON with:
{{
  "query": "new query text",
  "param_adjustments": {{
    "reddit": {{"time_filter": "year"}},
    "usajobs": {{"keywords": "broad keyword"}}
  }}
}}
"""
    # ... rest of function
```

**AFTER** (with Jinja2):
```python
from core.prompt_loader import render_prompt

async def _reformulate_for_relevance(
    self,
    original_query: str,
    research_question: str,
    results_count: int
) -> Dict[str, Any]:
    prompt = render_prompt(
        "deep_research/query_reformulation_relevance.j2",
        research_question=research_question,
        original_query=original_query,
        results_count=results_count
    )
    # ... rest of function
```

**Benefits**:
- NO `{{` escaping
- Prompts version-controlled separately from code
- Easy to edit without touching Python
- Can validate JSON examples independently

---

## Files to Modify (13 Total)

### Tier 1: Core Infrastructure (NEW)
1. `core/prompt_loader.py` (NEW - 60 lines)
2. `prompts/__init__.py` (NEW - 10 lines)

### Tier 2: High Priority (Largest/Most Complex)
3. `research/deep_research.py` (MODIFY - 7 prompts, ~200 lines changed)
4. `integrations/social/brave_search_integration.py` (MODIFY - 1 prompt, ~50 lines)
5. `integrations/government/federal_register.py` (MODIFY - 1 prompt, ~50 lines)

### Tier 3: Medium Priority (Integration Files)
6. `integrations/government/sam_integration.py` (MODIFY - 1 prompt, ~50 lines)
7. `integrations/government/dvids_integration.py` (MODIFY - 1 prompt, ~50 lines)
8. `integrations/government/usajobs_integration.py` (MODIFY - 1 prompt, ~50 lines)
9. `integrations/government/clearancejobs_integration.py` (MODIFY - 1 prompt, ~50 lines)
10. `integrations/government/fbi_vault.py` (MODIFY - 1 prompt, ~50 lines)
11. `integrations/social/twitter_integration.py` (MODIFY - 1 prompt, ~50 lines)
12. `integrations/social/reddit_integration.py` (MODIFY - 1 prompt, ~50 lines)
13. `integrations/social/discord_integration.py` (MODIFY - 1 prompt, ~50 lines)

### Template Files to Create (18 Total)
14-20. 7 deep_research templates (.j2 files)
21-31. 11 integration templates (.j2 files)

---

## Dependencies

### Python Packages
- **Jinja2**: ✅ Already installed (v3.1.6)
- **MarkupSafe**: ✅ Already installed (required by Jinja2)

No new dependencies needed!

### File Dependencies
- `core/prompt_loader.py` → Must create FIRST
- All templates → Must create BEFORE modifying Python files
- Python files → Modified AFTER templates exist

---

## Implementation Plan

### Phase 1: Infrastructure (2 hours)
1. Create `prompts/` directory structure
2. Create `core/prompt_loader.py` with Jinja2 environment
3. Create `prompts/__init__.py`
4. Write unit tests for `prompt_loader.py`

### Phase 2: Template Creation (4-6 hours)
5. Extract 7 prompts from `deep_research.py` → `.j2` files
6. Extract 10 prompts from integration files → `.j2` files
7. Create JSON schema examples in `prompts/schemas/`
8. Validate all templates load correctly

### Phase 3: Code Migration (4-6 hours)
9. Modify `deep_research.py` (7 prompt call sites)
10. Modify 10 integration files (1 prompt each)
11. Update imports in all modified files
12. Remove `{{` `}}` escaping from all files

### Phase 4: Testing (2-3 hours)
13. Unit test: Each template renders correctly
14. Integration test: Each modified file works end-to-end
15. Regression test: Run existing test suite
16. Manual test: Smoke test research queries

### Phase 5: Documentation (1 hour)
17. Update `PATTERNS.md` with Jinja2 pattern
18. Update `docs/FSTRING_JSON_METHODOLOGY.md`
19. Add docstrings to new files
20. Update `CLAUDE.md` with new pattern

**Total Estimated Time**: 13-18 hours

---

## Risks and Mitigation

### Risk 1: Breaking Changes
**Impact**: HIGH - Modifies 13 production files
**Probability**: MEDIUM - Template rendering could fail silently

**Mitigation**:
- Create templates FIRST, validate they load
- Modify Python files ONE AT A TIME
- Test each file individually before moving to next
- Keep f-string versions in git history for rollback

**Circuit Breaker**: If >2 files break during migration, STOP and rollback

### Risk 2: Template Loading Failures
**Impact**: HIGH - Could break all prompts at runtime
**Probability**: LOW - Jinja2 is mature, well-tested

**Mitigation**:
- Add template existence validation at module load time
- Use `validate_template()` in each modified file's `__init__`
- Log template loading errors explicitly
- Fail fast with clear error messages

**Circuit Breaker**: If template not found, raise ImportError immediately

### Risk 3: Variable Name Mismatches
**Impact**: MEDIUM - Template expects `research_question`, code passes `query`
**Probability**: MEDIUM - Manual migration prone to typos

**Mitigation**:
- Create mapping document: Python var names → Template var names
- Use consistent naming convention across all templates
- Add type hints to `render_prompt()` calls
- Write unit test for each template with sample data

**Circuit Breaker**: If render fails, log full context and re-raise

### Risk 4: Whitespace/Formatting Changes
**Impact**: LOW - LLMs are robust to whitespace differences
**Probability**: HIGH - Jinja2 trim_blocks changes formatting

**Mitigation**:
- Configure Jinja2 with `trim_blocks=True`, `lstrip_blocks=True`
- Test with actual LLM calls to verify output quality unchanged
- Compare rendered prompts before/after migration
- Accept minor whitespace changes (LLMs don't care)

**Not a Circuit Breaker**: Whitespace differences acceptable

### Risk 5: Template Caching Issues
**Impact**: LOW - Changes to templates not reflected immediately
**Probability**: LOW - Only in development

**Mitigation**:
- Jinja2 auto-reloads templates in development
- No caching in production (templates loaded once at import)
- Document template reload behavior in `prompt_loader.py`

**Not a Circuit Breaker**: Dev-only issue

### Risk 6: Merge Conflicts
**Impact**: MEDIUM - Touches many files, conflicts likely
**Probability**: HIGH - If done over multiple days

**Mitigation**:
- Do migration in single focused session (1-2 days max)
- Create feature branch immediately
- Merge main → feature branch frequently
- Minimize WIP time

**Circuit Breaker**: If merge conflicts in >3 files, coordinate with team

### Risk 7: Test Breakage
**Impact**: HIGH - Existing tests may rely on exact prompt format
**Probability**: MEDIUM - Tests might mock prompts or validate strings

**Mitigation**:
- Run full test suite BEFORE migration (baseline)
- Identify tests that validate prompt strings
- Update test fixtures to use Jinja2 templates
- Accept minor test changes if behavior unchanged

**Circuit Breaker**: If >5 tests fail, investigate root cause before proceeding

---

## Uncertainties

### 1. Prompt Exact Match Requirements
**Question**: Do any tests or external systems rely on exact prompt string matching?

**Investigation Needed**:
- Search for hardcoded prompt strings in test files
- Check if any logging/monitoring compares prompts
- Review if any external tools parse prompt structure

**Impact if Unknown**: Tests may fail unexpectedly

**Resolution**: Grep test files for prompt substrings before migrating

---

### 2. Dynamic Prompt Construction
**Question**: Are any prompts built dynamically (not just variable interpolation)?

**Investigation Needed**:
- Review all `prompt = f"""` blocks for conditional logic
- Check if any prompts have if/else branches inline
- Identify prompts that loop over data structures

**Impact if Unknown**: Templates may need Jinja2 control structures (`{% if %}`, `{% for %}`)

**Resolution**: Read all 18 prompt functions to identify dynamic patterns

**Example Found**: In `_select_sources()` (line 769), prompt includes list of available sources
- **Solution**: Use Jinja2 `{% for source in sources %}` loop

---

### 3. JSON Schema Validation
**Question**: Are JSON examples in prompts validated anywhere?

**Investigation Needed**:
- Check if any tests parse JSON examples from prompts
- Review if schema validation uses prompt strings
- See if documentation generation extracts JSON from prompts

**Impact if Unknown**: May break schema documentation or validation

**Resolution**: Search for `json.loads()` on prompt strings

---

### 4. Internationalization (i18n)
**Question**: Will prompts ever need translation to other languages?

**Investigation Needed**:
- Review roadmap for multi-language support
- Check if Jinja2 templates support i18n extensions

**Impact if Unknown**: May need to restructure templates later

**Resolution**: Ask user about i18n requirements

**Note**: Jinja2 supports i18n via `babel` extension if needed later

---

### 5. Template Inheritance
**Question**: Do prompts share common sections that could be inherited?

**Investigation Needed**:
- Identify repeated boilerplate across prompts
- Check if all integration prompts follow same structure
- See if "Return JSON with" sections are identical

**Impact if Unknown**: Miss optimization opportunity for DRY templates

**Resolution**: After creating templates, look for common patterns

**Example**: All integration prompts end with "Return JSON: {...}" - could use `{% include "common/json_return.j2" %}`

---

### 6. Performance Impact
**Question**: Does Jinja2 rendering add measurable latency vs f-strings?

**Investigation Needed**:
- Benchmark: f-string rendering vs Jinja2 template rendering
- Measure overhead of template loading at module import
- Check if template caching improves performance

**Impact if Unknown**: May introduce latency in hot paths

**Resolution**: Run microbenchmark before migration

**Expected**: Jinja2 overhead negligible (<1ms) for prompt rendering

---

### 7. Error Messages
**Question**: Will Jinja2 template errors be clear enough for debugging?

**Investigation Needed**:
- Test what happens when template not found
- Test what happens when variable undefined in template
- Test what happens when template has syntax error

**Impact if Unknown**: Debugging may be harder than with f-strings

**Resolution**: Write unit tests for error cases, document error handling

---

### 8. IDE Support
**Question**: Will developers get syntax highlighting/autocomplete for .j2 files?

**Investigation Needed**:
- Check if VS Code has Jinja2 extensions
- Test if PyCharm recognizes .j2 files
- Verify if code review tools render .j2 files

**Impact if Unknown**: Developer experience may degrade

**Resolution**: Document recommended IDE extensions in README

**Recommendation**: Install "Better Jinja" extension for VS Code

---

## Testing Strategy

### Unit Tests
**NEW FILE**: `tests/test_prompt_loader.py`
```python
def test_render_prompt_basic():
    """Test basic template rendering."""
    prompt = render_prompt(
        "deep_research/task_decomposition.j2",
        research_question="What is X?",
        max_tasks=5
    )
    assert "What is X?" in prompt
    assert "5" in prompt or "five" in prompt

def test_render_prompt_json_no_escaping():
    """Verify JSON examples don't have escaped braces."""
    prompt = render_prompt(
        "deep_research/query_reformulation_relevance.j2",
        research_question="test",
        original_query="test",
        results_count=0
    )
    # Should have literal { } not {{ }}
    assert '{"query":' in prompt or '{ "query":' in prompt
    assert '{{' not in prompt  # No escaped braces

def test_template_not_found():
    """Test error handling for missing template."""
    with pytest.raises(TemplateNotFound):
        render_prompt("nonexistent/template.j2")

def test_validate_template():
    """Test template existence validation."""
    assert validate_template("deep_research/task_decomposition.j2")
    assert not validate_template("nonexistent.j2")
```

### Integration Tests
**Modify existing tests to use Jinja2**:
```python
# tests/test_deep_research.py
def test_reformulate_for_relevance():
    """Test query reformulation with Jinja2 templates."""
    engine = SimpleDeepResearch()
    result = await engine._reformulate_for_relevance(
        original_query="test query",
        research_question="What is X?",
        results_count=5
    )
    assert "query" in result
    assert "param_adjustments" in result
```

### Regression Tests
**Run full existing test suite**:
```bash
pytest tests/ -v
```

**Expected**: All tests pass (or minor failures in prompt string comparisons)

### Manual Smoke Tests
1. Run `python3 apps/ai_research.py "test query"` - should work unchanged
2. Check output logs - prompts should look correct (no `{{` in logs)
3. Verify LLM responses - quality should be unchanged

---

## Rollback Plan

### Scenario 1: Template Rendering Breaks
**Trigger**: ImportError, TemplateNotFound, or UndefinedError

**Action**:
1. Revert Python file changes (git checkout)
2. Keep templates (no harm in having extra files)
3. Document which template caused failure
4. Fix template, retry

**Estimated Time**: 5 minutes per file

### Scenario 2: LLM Output Quality Degrades
**Trigger**: Tests fail, user reports bad results, manual testing shows problems

**Action**:
1. Compare rendered prompts before/after (diff old vs new)
2. Identify whitespace or formatting changes
3. Adjust Jinja2 config (trim_blocks, lstrip_blocks)
4. If unfixable, revert to f-strings

**Estimated Time**: 30-60 minutes investigation

### Scenario 3: Performance Regression
**Trigger**: Measurable latency increase (>10ms per prompt)

**Action**:
1. Profile template rendering with cProfile
2. Enable Jinja2 template caching if not already
3. If still slow, revert to f-strings

**Estimated Time**: 1 hour investigation

### Scenario 4: Multiple Files Broken
**Trigger**: >3 files have issues during migration

**Action**:
1. STOP migration immediately
2. Revert all changes (git reset --hard)
3. Re-evaluate approach (maybe migrate incrementally)
4. Document lessons learned

**Estimated Time**: 15 minutes to revert

---

## Decision Points

### Decision 1: Migrate All at Once vs Incrementally?
**Option A**: Migrate all 18 prompts in single PR
- **Pro**: Consistent approach, faster completion
- **Con**: Higher risk, harder to debug

**Option B**: Migrate 1-2 files at a time, merge after each
- **Pro**: Lower risk, easier rollback
- **Con**: Slower, potential for inconsistency

**Recommendation**: Start with Option B (incremental), switch to A if no issues

---

### Decision 2: Keep f-strings in Archive?
**Option A**: Delete f-string prompts entirely
- **Pro**: Cleaner codebase
- **Con**: Can't easily compare old vs new

**Option B**: Comment out f-strings, leave in file
- **Pro**: Easy comparison, inline documentation
- **Con**: Code bloat

**Recommendation**: Option A (delete), rely on git history for comparison

---

### Decision 3: Validate Templates at Import vs Runtime?
**Option A**: Validate all templates when module imports
- **Pro**: Fail fast, catch errors early
- **Con**: Slower imports, breaks on missing templates

**Option B**: Validate templates lazily (first use)
- **Pro**: Faster imports
- **Con**: Runtime errors possible

**Recommendation**: Option A (import-time validation) for production files

---

### Decision 4: JSON Schema Files - Separate or Inline?
**Option A**: Extract JSON examples to `prompts/schemas/*.json`
- **Pro**: Reusable, parseable, testable
- **Con**: Extra files, indirection

**Option B**: Keep JSON inline in templates
- **Pro**: Simpler, everything in one place
- **Con**: No validation, no reuse

**Recommendation**: Option B (inline) unless >3 prompts share same schema

---

## Conclusion

**Migration is FEASIBLE** with following conditions:

✅ **Pros**:
- Jinja2 already installed (no new dependencies)
- Clean separation of prompts from code
- NO MORE `{{` `}}` escaping (permanent fix)
- Templates are testable, version-controlled, editable

⚠️ **Cons**:
- Touches 13 production files (high risk)
- 13-18 hour effort (non-trivial)
- Potential for test breakage
- Learning curve for team (Jinja2 syntax)

🔴 **Blockers**: NONE identified

**Recommendation**: **PROCEED** with incremental migration (2-3 files per session)

**First Target**: `research/deep_research.py` (highest value, most escaped braces)

---

## Next Steps (If Approved)

1. User reviews this investigation
2. User approves migration OR requests changes
3. If approved:
   - Create feature branch `feature/jinja2-prompts`
   - Start with Phase 1 (infrastructure)
   - Migrate `deep_research.py` first
   - Test thoroughly before proceeding
4. If rejected:
   - Keep current f-string approach
   - Update `docs/FSTRING_JSON_METHODOLOGY.md` as final standard

**Awaiting user decision.**
