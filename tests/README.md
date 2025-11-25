# Test Organization

**112 active test files** organized into 5 categories (72 archived).

## Quick Start

```bash
# Run comprehensive test (tests ALL integrations)
python3 test_verification.py

# Run individual integration test
python3 integrations/test_congress_live.py
python3 integrations/test_crest_live.py

# Run all integration tests
pytest integrations/

# Run specific category
pytest features/test_phase3c_*.py
```

---

## Directory Structure

```
tests/
├── README.md                           # This file
├── test_verification.py                # Main comprehensive test (ALL sources)
├── test_config_schema.py               # Core config validation tests
│
├── integrations/ (68 files)            # Integration-specific tests
│   ├── test_*_live.py                  # Live API tests (main test for each source)
│   ├── test_dvids_*.py                 # DVIDS (11 files)
│   ├── test_twitter_*.py               # Twitter (9 files)
│   ├── test_sec_edgar_*.py             # SEC EDGAR (5 files)
│   ├── test_clearancejobs_*.py         # ClearanceJobs (3 files)
│   └── ...                             # Other integrations
│
├── features/ (15 files)                # Feature/phase tests
│   ├── test_phase3a_*.py               # Phase 3A: Hypothesis generation
│   ├── test_phase3b_*.py               # Phase 3B: Parallel execution
│   ├── test_phase3c_*.py               # Phase 3C: Coverage assessment
│   └── test_deep_research_*.py         # Deep research workflows
│
├── system/ (16 files)                  # System-level tests
│   ├── test_all_*.py                   # Comprehensive multi-source
│   ├── test_registry_*.py              # Registry validation
│   ├── test_architectural_*.py         # Architecture validation
│   └── test_search_fallback_*.py       # Fallback behavior
│
├── unit/ (11 files)                    # Unit tests for core components
│   └── mixins/                         # Research mixin tests (95 tests)
│
└── archived/ (72 files)                # Diagnostic/deprecated tests
    ├── test_dvids_*_diagnostic.py      # DVIDS 403 investigation (12 files)
    ├── test_fbi_vault_*.py             # FBI Vault bypass tests (3 files)
    ├── test_clearancejobs_*.py         # Obsolete Playwright/Puppeteer (4 files)
    └── test_*_fix.py                   # Fix validation tests
```

---

## Test Categories Explained

### 1. test_verification.py (Root)
**Purpose**: Main entry point for testing ALL integrations
**Use**: Run this to verify system health
**Auto-discovers**: All enabled integrations from registry

### 2. integrations/ (68 files)
**Purpose**: Test individual data source integrations
**Pattern**: `test_{source}_*.py`
**Tests**: Query generation, search execution, QueryResult format

**Key files**:
- `test_{source}_live.py` - Live API tests (requires API keys)
- `test_{source}_integration.py` - Integration tests

### 3. features/ (15 files)
**Purpose**: Test specific research system features

**Phase 3 (Hypothesis Branching)**:
- Phase 3A: Hypothesis generation (planning only)
- Phase 3B: Parallel hypothesis execution
- Phase 3C: Coverage-based adaptive stopping

### 4. system/ (16 files)
**Purpose**: System-level integration tests

**Tests**:
- Registry validation
- Architectural validation
- Multi-source parallel execution
- Search fallback behavior

### 5. unit/ (11 files)
**Purpose**: Unit tests for core components using mocks

**Coverage**:
- 10 mixin test files covering research/mixins/*.py
- 95 individual test cases
- Tests isolation, error handling, edge cases

**Key files**:
- `test_entity_mixin.py` - Entity extraction
- `test_hypothesis_mixin.py` - Hypothesis generation/coverage
- `test_source_executor_mixin.py` - Parallel/sequential execution

### 6. archived/ (72 files)
**Purpose**: Obsolete, diagnostic, or investigative tests

**Contents**:
- DVIDS 403 investigation tests (12 files)
- FBI Vault stealth bypass experiments (3 files)
- ClearanceJobs Playwright/Puppeteer (4 files, obsoleted by HTTP)
- One-off fix validation tests

---

## Testing Best Practices

### Adding New Tests

**New integration**:
```bash
cp integrations/test_usajobs_live.py integrations/test_newsource_live.py
# Edit to test new integration
```

**New feature**:
```bash
# Add to features/ directory
# Name: test_{feature}_*.py
```

### Running Tests

**By category**:
```bash
pytest integrations/  # All integration tests
pytest features/      # All feature tests
pytest system/        # All system tests
```

**By source**:
```bash
pytest integrations/test_dvids_*.py  # All DVIDS tests
pytest integrations/test_sam_*.py    # All SAM tests
```

**Individual test**:
```bash
python3 integrations/test_congress_live.py
```

### Test Naming Convention

- `test_{source}_live.py` - Live API test (main test for each integration)
- `test_{source}_integration.py` - Integration test
- `test_{source}_diagnostic.py` - Debugging/investigation
- `test_{feature}_{variant}.py` - Feature test
- `test_all_{description}.py` - System test

---

## API Keys Required

Most integration tests require API keys in `.env`:

```bash
# Government sources
SAM_GOV_API_KEY=...
DVIDS_API_KEY=...
USAJOBS_API_KEY=...
CONGRESS_API_KEY=...

# Social sources
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
REDDIT_USERNAME=...
REDDIT_PASSWORD=...
TWITTER_BEARER_TOKEN=...

# Web search
BRAVE_API_KEY=...
```

---

## Recent Changes

- **2025-11-25**: Added 95 unit tests for research mixins (tests/unit/mixins/)
- **2025-11-25**: Archived 30 obsolete tests (DVIDS 403 investigation, ClearanceJobs Playwright, FBI Vault bypass experiments, fix validation tests)
- **2025-11-25**: Reorganized test files - moved all *_live.py to integrations/, system tests to system/
- **2025-11-25**: Moved documentation files (*.txt) to data/docs/
- **2025-11-21**: Organized 125 test files into 4 categories
- **2025-11-21**: Added `test_congress_live.py` and `test_crest_live.py`
- **2025-11-21**: Rewrote `test_verification.py` to use integration registry

---

## Maintenance

**When to archive**:
- Test is obsolete (feature removed/changed)
- Test was for one-time investigation
- Test validates a bug fix that's been resolved

**When to delete**:
- Test has been archived for >6 months
- Test is duplicate of another test
- Test no longer runs (dependencies removed)
