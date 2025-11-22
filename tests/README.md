# Test Organization

**125 test files** organized into 4 categories for easier navigation.

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
├── test_verification.py                # ✅ Main comprehensive test (ALL sources)
│
├── integrations/ (59 files)            # Integration-specific tests
│   ├── test_sam_*.py                   # SAM.gov (4 files)
│   ├── test_dvids_*.py                 # DVIDS (22 files)
│   ├── test_clearancejobs_*.py         # ClearanceJobs (6 files)
│   ├── test_twitter_*.py               # Twitter (7 files)
│   ├── test_brave_*.py                 # Brave Search (5 files)
│   ├── test_usajobs_*.py               # USAJobs (2 files)
│   ├── test_discord_*.py               # Discord (2 files)
│   ├── test_crest_*.py                 # CREST/CIA (3 files)
│   ├── test_fbi_*.py                   # FBI Vault (5 files)
│   ├── test_reddit_*.py                # Reddit (2 files)
│   └── test_congress_live.py           # Congress.gov (1 file)
│
├── features/ (17 files)                # Feature/phase tests
│   ├── test_phase3a_*.py               # Phase 3A: Hypothesis generation (3 files)
│   ├── test_phase3b_*.py               # Phase 3B: Parallel execution (2 files)
│   ├── test_phase3c_*.py               # Phase 3C: Coverage assessment (6 files)
│   ├── test_deep_research_*.py         # Deep research workflows (5 files)
│   └── test_hypothesis_*.py            # Hypothesis testing (1 file)
│
├── system/ (6 files)                   # System-level tests
│   ├── test_all_*.py                   # Comprehensive multi-source (3 files)
│   ├── test_parallel_*.py              # Parallel execution (2 files)
│   └── test_query_*.py                 # Query generation (1 file)
│
└── archived/ (43 files)                # Diagnostic/deprecated tests
    ├── investigate_*.py                # Investigation scripts
    ├── test_*_diagnostic.py            # Diagnostic tests
    ├── test_ai_*.py                    # AI-specific tests
    └── test_*_fix.py                   # Fix validation tests
```

---

## Test Categories Explained

### 1. test_verification.py (Root)
**Purpose**: Main entry point for testing ALL integrations
**Use**: Run this to verify system health
**Auto-discovers**: All enabled integrations from registry

### 2. integrations/ (59 files)
**Purpose**: Test individual data source integrations
**Pattern**: `test_{source}_*.py`
**Tests**: Query generation, search execution, QueryResult format

**Key files**:
- `test_{source}_live.py` - Live API tests (requires API keys)
- `test_{source}_integration.py` - Integration tests
- `test_{source}_diagnostic.py` - Debugging/investigation

### 3. features/ (17 files)
**Purpose**: Test specific research system features

**Phase 3 (Hypothesis Branching)**:
- Phase 3A: Hypothesis generation (planning only)
- Phase 3B: Parallel hypothesis execution
- Phase 3C: Coverage-based adaptive stopping

**Deep Research**:
- Task decomposition
- Multi-hypothesis exploration
- Follow-up generation

### 4. system/ (6 files)
**Purpose**: System-level integration tests

**Tests**:
- Multi-source parallel execution
- Query generation across sources
- End-to-end research workflows

### 5. archived/ (43 files)
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
