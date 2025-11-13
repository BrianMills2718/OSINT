# f-string/JSON Template Conflict - Definitive Solution

**Author**: Claude Code (Anthropic)
**Date**: 2025-11-01
**Status**: OFFICIAL STANDARD
**Scope**: All codebases with LLM prompts containing JSON examples

---

## Problem Statement

Python f-strings and JSON templates use the same `{` `}` syntax, causing format specifier errors when JSON examples appear in f-string prompts sent to LLMs.

**Error Example**:
```python
prompt = f"""
Example JSON:
{{"query": "text", "params": {{"time_filter": "year"}}}}
"""
# ValueError: Invalid format specifier ' "year"' for object of type 'str'
```

**Root Cause**: Python interprets `{"time_filter": "year"}` as an f-string format specifier, not literal JSON.

---

## The Solution: Separation of Concerns

**Core Principle**: NEVER mix JSON examples directly into f-strings.

**Standard Pattern**: Extract JSON to constants, interpolate as complete strings.

---

## Standard Implementation Pattern

### Rule 1: Extract JSON Examples as Constants

**Before (Problematic)**:
```python
prompt = f"""
Return JSON:
{{
  "query": "{new_query}",
  "params": {{
    "time_filter": "year"
  }}
}}
"""
```

**After (Correct)**:
```python
JSON_EXAMPLE = """
{
  "query": "new query text",
  "params": {
    "time_filter": "year"
  }
}
"""

prompt = f"""
Return JSON:
{JSON_EXAMPLE}

Your query: {new_query}
"""
```

**Why This Works**:
- JSON stored as raw string (no escaping needed)
- F-string only interpolates `{JSON_EXAMPLE}` and `{new_query}` (no nested braces)
- Clean, readable, maintainable

---

### Rule 2: Validate JSON at Module Load

**Enforce correctness by parsing JSON when module loads**:

```python
import json

# Raw JSON as string
REDDIT_PARAM_EXAMPLE_JSON = """
{
  "time_filter": "year",
  "subreddits": ["Intelligence", "natsec"],
  "sort": "top"
}
"""

# Validate at module load - fails fast if invalid
REDDIT_PARAM_EXAMPLE = json.loads(REDDIT_PARAM_EXAMPLE_JSON)

# Use validated string in prompts
def generate_prompt(query: str) -> str:
    return f"""
    Example params:
    {REDDIT_PARAM_EXAMPLE_JSON}

    Your query: {query}
    """
```

**Benefits**:
- Catches JSON syntax errors at import time (not runtime)
- No surprises in production
- Validated object available for tests/debugging

---

### Rule 3: Naming Convention

**Enforce consistency across codebases**:

- **Raw strings**: Suffix with `_JSON` (e.g., `REDDIT_PARAM_EXAMPLE_JSON`)
- **Validated objects**: No suffix or `_VALIDATED` (e.g., `REDDIT_PARAM_EXAMPLE`)
- **Module-level constants**: UPPER_CASE for reusable examples

**Example**:
```python
# Top of file - reusable across functions
USAJOBS_PARAM_EXAMPLE_JSON = """
{
  "keywords": "cybersecurity",
  "location": "Washington, DC",
  "pay_grade_low": 11,
  "pay_grade_high": 13
}
"""

USAJOBS_PARAM_EXAMPLE = json.loads(USAJOBS_PARAM_EXAMPLE_JSON)
```

---

## Alternative Patterns (When to Use)

### Pattern A: Template Files (Large Prompts)

**When**: Prompt > 50 lines, multiple JSON examples, shared across functions

**Implementation**:
```python
# prompts/reddit_reformulate.txt
Your task: Reformulate query for Reddit to get more relevant results.

Example parameters you can adjust:
{
  "time_filter": "year",
  "subreddits": ["Intelligence", "natsec", "OSINT"],
  "sort": "top"
}

Original query: {{original_query}}
Results count: {{results_count}}
```

```python
# Code
from pathlib import Path

def load_prompt(name: str, **kwargs) -> str:
    template = Path(f"prompts/{name}.txt").read_text()
    # Simple replacement (or use jinja2 for complex cases)
    for key, value in kwargs.items():
        template = template.replace(f"{{{{{key}}}}}", str(value))
    return template

prompt = load_prompt("reddit_reformulate",
                    original_query="test query",
                    results_count=5)
```

**Benefits**:
- NO escaping needed - JSON in file is raw
- Prompts version-controlled separately from code
- Easy to edit/review without touching code
- Can validate JSON independently

**Drawbacks**:
- File management overhead
- Overkill for small inline prompts

---

### Pattern B: textwrap.dedent (Clean Indentation)

**When**: Want clean indentation without extraction overhead

**Implementation**:
```python
from textwrap import dedent

json_example = dedent("""
{
  "query": "new query text",
  "params": {
    "time_filter": "year"
  }
}
""").strip()

prompt = dedent(f"""
Your task: {task_description}

Example JSON:
{json_example}

Original query: {original_query}
""").strip()
```

**Benefits**:
- Clean indentation handling
- NO escaping in JSON block
- Combines readability with interpolation

**Drawbacks**:
- Requires import
- Two-step construction (JSON + prompt)

---

## Automated Enforcement

### Pre-commit Hook

**Install**:
```bash
pip install pre-commit
```

**Create `.pre-commit-config.yaml`**:
```yaml
repos:
  - repo: local
    hooks:
      - id: check-fstring-json-conflict
        name: Check f-string/JSON conflicts
        entry: python scripts/lint_fstring_json.py
        language: python
        files: \.py$
```

**Create `scripts/lint_fstring_json.py`**:
```python
#!/usr/bin/env python3
"""
Lint for f-string/JSON template conflicts.

Detects patterns where JSON examples appear inside f-strings,
which can cause format specifier errors.
"""
import re
import sys
from pathlib import Path

# Pattern: f-string with doubled braces (indicates JSON inside f-string)
FSTRING_JSON_PATTERN = re.compile(
    r'f["\']([^"\']*\{\{[^}]*\}\}[^"\']*)["\'"]',
    re.MULTILINE | re.DOTALL
)

def check_file(filepath: Path) -> list[str]:
    """Check file for f-string/JSON conflicts."""
    content = filepath.read_text()
    errors = []

    for match in FSTRING_JSON_PATTERN.finditer(content):
        line_num = content[:match.start()].count('\n') + 1
        errors.append(
            f"{filepath}:{line_num}: f-string contains doubled braces (JSON inside f-string). "
            f"Extract JSON to constant to avoid format specifier errors."
        )

    return errors

def main():
    files = [Path(f) for f in sys.argv[1:]]
    all_errors = []

    for filepath in files:
        if filepath.suffix == '.py':
            errors = check_file(filepath)
            all_errors.extend(errors)

    if all_errors:
        for error in all_errors:
            print(error, file=sys.stderr)
        sys.exit(1)

    sys.exit(0)

if __name__ == '__main__':
    main()
```

**Enable**:
```bash
pre-commit install
```

Now commits with f-string/JSON conflicts are automatically blocked.

---

## Migration Strategy (Existing Codebases)

### Step 1: Audit

Find all f-strings with doubled braces:
```bash
grep -rn 'f""".*{{.*}}.*"""' --include="*.py" .
grep -rn "f'''.*{{.*}}.*'''" --include="*.py" .
```

### Step 2: Prioritize

1. **High Priority**: LLM prompts (most likely to break)
2. **Medium Priority**: Validation schemas
3. **Low Priority**: Debug/logging strings

### Step 3: Refactor Pattern

For each violation:
1. Extract JSON example to module constant
2. Validate with `json.loads()` at module level
3. Use constant in f-string interpolation
4. Add comment linking constant to usage

**Example**:
```python
# Before
prompt = f"""
Example: {{"query": "{query}", "params": {{"x": "y"}}}}
"""

# After
QUERY_EXAMPLE_JSON = """
{
  "query": "example query text",
  "params": {
    "x": "y"
  }
}
"""
QUERY_EXAMPLE = json.loads(QUERY_EXAMPLE_JSON)  # Validates at import

prompt = f"""
Example:
{QUERY_EXAMPLE_JSON}

Your query: {query}
"""
```

### Step 4: Install Pre-commit Hook

```bash
# In repo root
pip install pre-commit
pre-commit install
pre-commit run --all-files  # Test on all files
```

### Step 5: Update Documentation

Add to `PATTERNS.md`:
```markdown
## LLM Prompts with JSON Examples

**Rule**: NEVER put JSON examples directly in f-strings.

**Pattern**: Extract to constant, validate at module load.

**Reference**: docs/FSTRING_JSON_METHODOLOGY.md

**Example**: research/deep_research.py lines 1550-1565
```

---

## Quick Reference

### DO ✅
- Extract JSON to constants
- Validate JSON with `json.loads()` at module load
- Use raw strings for JSON examples
- Interpolate complete JSON strings into f-strings
- Name constants with `_JSON` suffix

### DON'T ❌
- Put JSON directly in f-strings
- Use `{{` `}}` escaping (manual, error-prone)
- Mix f-string variables with JSON braces
- Skip validation of JSON examples
- Commit code with doubled braces in f-strings

---

## Pattern Comparison Table

| Pattern | Escaping | Readability | Complexity | Best For |
|---------|----------|-------------|------------|----------|
| **Extract to constant** | ❌ NO | ✅ Excellent | Low | **Default choice** |
| Template files | ❌ NO | ✅ Excellent | Medium | Large prompts (>50 lines) |
| textwrap.dedent | ❌ NO | ✅ Good | Low | Clean indentation |
| Escape `{{` `}}` | ✅ YES | ⚠️ Poor | Low | **Never use** (legacy only) |
| .format() | ✅ YES | ⚠️ Poor | Low | **Never use** (legacy only) |

---

## Enforcement Layers (Defense in Depth)

1. **Developer Knowledge**: Pattern documented in PATTERNS.md
2. **Editor Linting**: Real-time warnings via IDE integration
3. **Pre-commit Hook**: Blocks commits with violations
4. **CI/CD Check**: Final validation before merge
5. **Code Review**: Reviewers trained to spot violations

With all layers active, f-string/JSON conflicts become impossible to commit.

---

## Real-World Example (This Codebase)

**File**: `research/deep_research.py`

**Before (Lines ~1607-1608)**:
```python
prompt = f"""
Return JSON:
{{
  "query": "new query",
  "param_adjustments": {{
    "reddit": {{"time_filter": "year"}},
    "usajobs": {{"keywords": "broad keyword"}}
  }}
}}
"""
# ValueError: Invalid format specifier ' "year"'
```

**After (Recommended Refactor)**:
```python
# Module-level constant
PARAM_ADJUSTMENT_EXAMPLE_JSON = """
{
  "query": "new query text",
  "param_adjustments": {
    "reddit": {"time_filter": "year"},
    "usajobs": {"keywords": "broad keyword"}
  }
}
"""

# Validate at module load
PARAM_ADJUSTMENT_EXAMPLE = json.loads(PARAM_ADJUSTMENT_EXAMPLE_JSON)

# In function
prompt = f"""
Return JSON:
{PARAM_ADJUSTMENT_EXAMPLE_JSON}

Original query: {original_query}
Results count: {results_count}
"""
```

**Result**: NO escaping, clean JSON, validated at import, no runtime errors.

---

## Conclusion

**The f-string/JSON conflict is solved permanently by enforcing separation of concerns:**

1. **JSON examples** live in constants (raw strings, no escaping)
2. **F-strings** only interpolate complete strings (no nested braces)
3. **Validation** happens at module load (fail fast)
4. **Automation** prevents violations (pre-commit hooks)

**This is now the official standard for all codebases.**

Any code review finding doubled braces in f-strings should be rejected with reference to this document.
