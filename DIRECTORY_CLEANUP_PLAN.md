# Directory Cleanup Plan

**Date**: 2025-10-19
**Issue**: CLAUDE.md claims incorrect directory structure

## Current Issues

### 1. CLAUDE.md Claims vs Reality

**CLAUDE.md claims**:
```
integrations/
├── sam_integration.py
├── dvids_integration.py
├── usajobs_integration.py
├── clearancejobs_integration.py
└── clearancejobs_playwright.py
```

**Reality**:
```
integrations/
├── __init__.py
├── registry.py
├── government/
│   ├── sam_integration.py
│   ├── dvids_integration.py
│   ├── usajobs_integration.py
│   ├── clearancejobs_integration.py
│   ├── clearancejobs_playwright.py
│   ├── clearancejobs_puppeteer.py  # ← OBSOLETE (replaced by Playwright)
│   └── fbi_vault.py
└── social/
    └── __init__.py
```

### 2. Test Files Scattered

**Root directory has test files** (should be in tests/):
- `test_all_four_databases.py`
- `test_clearancejobs_playwright.py`
- `test_cost_tracking.py`
- `test_live.py`
- `test_usajobs_live.py`
- `test_verification.py`

**tests/ directory also has tests**:
- `test_4_databases.py`
- `test_agentic_executor.py`
- `test_apis_direct.py`
- etc. (12 test files)

### 3. Documentation Clutter in Root

**Multiple CLAUDE.md variants**:
- `CLAUDE.md` (current)
- `CLAUDE_PERMANENT.md` (source - KEEP)
- `CLAUDE_TEMP.md` (source - KEEP)
- `CLAUDE_v2.md` (archive)
- `CLAUDE_OLD.md` (archive)
- `CLAUDE_IMPROVED.md` (archive)

**Multiple status/test reports**:
- `ACTUAL_STATUS.md` (from parallel session - duplicate work)
- `TESTED_INTEGRATIONS_REPORT.md` (from parallel session - duplicate work)
- `INTEGRATION_TEST_STATUS.md` (archive?)
- `STATUS.md` (current - KEEP)

**Misc files**:
- `DIRECTORY_STRUCTURE.md` (probably obsolete - we have CLAUDE.md)
- `si_convo_temp.txt` (temp file)
- `keyword_extraction_raw_summary.txt` (temp file)

### 4. Additional Directories Not in CLAUDE.md

**Actual directories**:
- `data/` - Contains articles, exports, logs, monitors
- `monitoring/` - Empty except __init__.py
- `research/` - Empty except __init__.py
- `utils/` - Empty except __init__.py
- `experiments/` - discord, scrapers, tag_management
- `scripts/` - update_to_use_config.py
- `ClearanceJobs/` - External git repo (should this be here?)
- `api-code-samples/` - External git repo (should this be here?)
- `bills_blackbox_articles_extracted/` - 20MB directory
- `klippenstein_articles_extracted/` - 90MB directory

## Cleanup Actions

### Phase 1: Archive Obsolete Files (Safe - No Breakage)

**Archive old CLAUDE.md variants**:
```bash
mkdir -p archive/2025-10-19/docs
mv CLAUDE_v2.md archive/2025-10-19/docs/
mv CLAUDE_OLD.md archive/2025-10-19/docs/
mv CLAUDE_IMPROVED.md archive/2025-10-19/docs/
```

**Archive duplicate status reports** (from parallel session):
```bash
mv ACTUAL_STATUS.md archive/2025-10-19/docs/
mv TESTED_INTEGRATIONS_REPORT.md archive/2025-10-19/docs/
mv INTEGRATION_TEST_STATUS.md archive/2025-10-19/docs/
```

**Archive obsolete Puppeteer implementation**:
```bash
mkdir -p archive/2025-10-19/integrations
mv integrations/government/clearancejobs_puppeteer.py archive/2025-10-19/integrations/
```

**Archive temp files**:
```bash
mkdir -p archive/2025-10-19/temp
mv si_convo_temp.txt archive/2025-10-19/temp/
mv keyword_extraction_raw_summary.txt archive/2025-10-19/temp/
```

### Phase 2: Consolidate Test Files (Moderate Risk)

**Option A: Move root tests to tests/** (recommended):
```bash
mv test_all_four_databases.py tests/
mv test_clearancejobs_playwright.py tests/
mv test_cost_tracking.py tests/
mv test_live.py tests/
mv test_usajobs_live.py tests/
mv test_verification.py tests/
```

**Option B: Keep root tests, archive tests/** (if root tests are newer):
- Need to check which are actually used
- Check git history to see which are maintained

### Phase 3: Update CLAUDE.md Directory Structure

Update PERMANENT section with actual structure:

```
integrations/
├── __init__.py
├── registry.py
├── government/
│   ├── sam_integration.py       # SAM.gov (federal contracts)
│   ├── dvids_integration.py     # DVIDS (military media)
│   ├── usajobs_integration.py   # USAJobs (federal jobs)
│   ├── clearancejobs_integration.py      # ClearanceJobs wrapper
│   ├── clearancejobs_playwright.py       # Playwright scraper
│   └── fbi_vault.py             # FBI Vault (blocked by Cloudflare)
└── social/
    └── __init__.py              # Placeholder for future social integrations
```

Add missing directories:
- `data/` - Runtime data storage
- `monitoring/` - Future: MonitorEngine, AlertManager
- `research/` - Future: Research workflows
- `utils/` - Utility functions
- `experiments/` - Experimental code
- `scripts/` - Maintenance scripts

### Phase 4: Decision Points (Need User Input)

**1. External repos in project directory**:
- `ClearanceJobs/` - External git repo, contains scraper code
- `api-code-samples/` - SAM.gov API examples
- **Question**: Move to archive? Keep for reference?

**2. Large extracted article directories**:
- `bills_blackbox_articles_extracted/` (20MB)
- `klippenstein_articles_extracted/` (90MB)
- **Question**: Move to archive/data? Keep in root?

**3. Empty placeholder directories**:
- `monitoring/`, `research/`, `utils/` - Empty except __init__.py
- **Question**: Keep for future use? Remove until needed?

**4. Obsolete documentation**:
- `DIRECTORY_STRUCTURE.md` - Likely obsolete (CLAUDE.md has this)
- **Question**: Archive or keep?

**5. Test consolidation**:
- Root has 6 test files
- tests/ has 12 test files
- **Question**: Which are current? Consolidate to tests/?

## Recommendations

### Immediate (Low Risk):
1. ✅ Archive old CLAUDE.md variants
2. ✅ Archive duplicate status reports from parallel session
3. ✅ Archive obsolete Puppeteer implementation
4. ✅ Archive temp files
5. ✅ Update CLAUDE.md directory structure to match reality

### With User Approval (Moderate Risk):
6. Move test files from root → tests/ (or vice versa based on which are current)
7. Archive or remove external repos (ClearanceJobs/, api-code-samples/)
8. Move or archive large extracted article directories
9. Remove empty placeholder directories (or document their purpose)

### After Testing (Post-Cleanup):
10. Update STATUS.md with cleaned structure
11. Update README.md with accurate structure
12. Verify all imports still work
13. Run tests to ensure nothing broken

## Next Steps

**User should decide**:
1. Which test files to keep (root or tests/)?
2. What to do with external repos?
3. What to do with large article directories?
4. Keep empty placeholder directories?

**Then execute**:
1. Phase 1 (safe archives)
2. Phase 2 (test consolidation based on decision)
3. Phase 3 (update CLAUDE.md)
4. Verify nothing broke
