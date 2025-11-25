# Test Organization

**173 test files** organized into 4 categories for easier navigation.

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
├── integrations/ (95 files)            # Integration-specific tests
│   ├── test_*_live.py                  # Live API tests (main test for each source)
│   ├── test_sam_*.py                   # SAM.gov
│   ├── test_dvids_*.py                 # DVIDS
│   ├── test_clearancejobs_*.py         # ClearanceJobs
│   ├── test_twitter_*.py               # Twitter
│   ├── test_brave_*.py                 # Brave Search
│   ├── test_usajobs_*.py               # USAJobs
│   ├── test_sec_edgar_*.py             # SEC EDGAR
│   ├── test_federal_register_*.py      # Federal Register
│   ├── test_newsapi_*.py               # NewsAPI
│   └── ...                             # Other integrations
│
├── features/ (18 files)                # Feature/phase tests
│   ├── test_phase3a_*.py               # Phase 3A: Hypothesis generation
│   ├── test_phase3b_*.py               # Phase 3B: Parallel execution
│   ├── test_phase3c_*.py               # Phase 3C: Coverage assessment
│   ├── test_deep_research_*.py         # Deep research workflows
│   └── test_synthesis_*.py             # Synthesis formatter tests
│
├── system/ (16 files)                  # System-level tests
│   ├── test_all_*.py                   # Comprehensive multi-source
│   ├── test_registry_*.py              # Registry validation
│   ├── test_architectural_*.py         # Architecture validation
│   ├── test_search_fallback_*.py       # Fallback behavior
│   └── test_http_client.py             # HTTP client tests
│
└── archived/ (42 files)                # Diagnostic/deprecated tests
    ├── investigate_*.py                # Investigation scripts
    ├── test_*_diagnostic.py            # Diagnostic tests
    └── verify_*.py                     # Verification scripts
```

---

## Test Categories Explained

### 1. test_verification.py (Root)
**Purpose**: Main entry point for testing ALL integrations
**Use**: Run this to verify system health
**Auto-discovers**: All enabled integrations from registry

### 2. integrations/ (95 files)
**Purpose**: Test individual data source integrations
**Pattern**: `test_{source}_*.py`
**Tests**: Query generation, search execution, QueryResult format

**Key files**:
- `test_{source}_live.py` - Live API tests (requires API keys)
- `test_{source}_integration.py` - Integration tests
- `test_{source}_e2e.py` - End-to-end tests

### 3. features/ (18 files)
**Purpose**: Test specific research system features

**Phase 3 (Hypothesis Branching)**:
- Phase 3A: Hypothesis generation (planning only)
- Phase 3B: Parallel hypothesis execution
- Phase 3C: Coverage-based adaptive stopping

**Other Features**:
- Deep research workflows
- Synthesis formatting

### 4. system/ (16 files)
**Purpose**: System-level integration tests

**Tests**:
- Registry validation
- Architectural validation
- Multi-source parallel execution
- Search fallback behavior
- HTTP client and rate limiting

### 5. archived/ (42 files)
**Purpose**: Obsolete, diagnostic, or investigative tests

**Contents**:
- One-off investigation scripts
- Deprecated test files
- Fix validation tests (after bugs resolved)

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

- **2025-11-25**: Reorganized 173 test files - moved all *_live.py to integrations/, system tests to system/
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
