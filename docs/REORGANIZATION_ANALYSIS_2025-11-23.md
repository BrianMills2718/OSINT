# Codebase Reorganization Analysis
**Date**: 2025-11-23
**Status**: Review Only - No Actions Taken

## Current State Summary

### Root Directory Status
- **Total Python/MD files**: 14 files
- **Target per CLAUDE.md**: ~15 files (within range ✅)
- **Configuration files**: 4-5 (.env, config.yaml, requirements.txt, etc.)
- **Core docs**: 8 markdown files
- **Core utils**: 2 Python files (llm_utils.py, config_loader.py)

### Directory Sizes
```
data/exports:         1.7GB  (Discord/Reddit/Telegram exports)
data/research_output: 696MB  (181 research runs, 74 >7 days old)
data/reddit:          158MB  (Reddit data cache)
data/articles:        82MB   (Archived articles)
data/logs:            23MB   (Application logs)
```

---

## REORGANIZATION SUGGESTIONS

### 🔴 HIGH PRIORITY - Structural Issues

#### 1. Nested Test Directory (Bug)
**Issue**: `/tests/tests/` exists with duplicate subdirectories
```
tests/tests/
├── archived/
├── features/
├── integrations/
└── system/
```
**Problem**: Accidental nesting - duplicates parent structure
**Recommendation**: Flatten or move contents to parent `/tests/` directory
**Impact**: Confusing structure, potential import issues

#### 2. Duplicate Test Directories
**Issue**: Both `/tests/integration/` AND `/tests/integrations/` exist
```
tests/integration/    - 2 files (parallel testing)
tests/integrations/   - 30+ files (database integration tests)
```
**Recommendation**: Consolidate to single `/tests/integrations/` directory
**Rationale**: "integrations" is more accurate (plural, matches /integrations/ structure)
**Impact**: Clearer organization, eliminates confusion

---

### 🟡 MEDIUM PRIORITY - Cleanup Opportunities

#### 3. Old Research Output (Disk Space)
**Issue**: 181 research run directories, 74 older than 7 days
**Size**: 696MB total
**Recommendation**: Create archive policy
```bash
# Archive runs >30 days to compressed format
# Keep only last 20 runs in active directory
# Move to data/archives/research_YYYY-MM/
```
**Impact**: Reduce working directory clutter, save ~400-500MB

#### 4. Root Scripts Migration
**Current Root Scripts**:
- `analyze_performance.py` - Should move to `/scripts/`
- `run_research.py` - Entry point (KEEP)
- `run_research_cli.py` - Entry point (KEEP)

**Recommendation**: Move `analyze_performance.py` to `/scripts/`
**Impact**: Cleaner root, utilities consolidated

#### 5. Test Documentation Files
**Current**: 4 markdown files in `/tests/`
```
tests/DATAGOV_MANUAL_VALIDATION.md
tests/README.md
tests/TWITTER_INTEGRATION_FINAL_STATUS.md
tests/TWITTER_INTEGRATION_TEST_SUMMARY.md
```
**Recommendation**: Move integration docs to `/docs/integrations/`
**Keep**: tests/README.md (it's the directory index)
**Impact**: Better documentation organization

---

### 🟢 LOW PRIORITY - Nice to Have

#### 6. Experiments Directory Organization
**Current Contents**:
```
experiments/
├── crest_kg/              (Knowledge graph extraction - 9MB)
├── discord/               (Discord experiments)
├── reddit/                (Reddit experiments)
├── scrapers/              (Web scraping experiments)
├── tag_management/        (Tag system experiments)
└── twitterexplorer_sigint/ (Twitter API client - USED IN PRODUCTION!)
```

**Issue**: `twitterexplorer_sigint` is ACTIVE PRODUCTION CODE (used by Twitter integration)
**Recommendation**: Consider moving back to root or creating `/lib/` directory for shared libraries
**Alternative**: Keep in experiments but add README explaining it's production-critical
**Impact**: Clarifies which experiments are active vs deprecated

#### 7. Downloaded Files Directory
**Location**: `/downloaded_files/`
**Contents**: 3 lock files (Playwright cache)
**Recommendation**: Move to `.cache/` or add to `.gitignore` list
**Impact**: Cleaner root directory listing

#### 8. LLM Research Examples
**Location**: `/llm_research_examples/` (documentation/examples, not code)
**Size**: Moderate (7 subdirectories with investigations/examples)
**Recommendation**: Move to `/docs/examples/` or keep as-is
**Impact**: Minor - already well-organized, just categorization

---

## DISK SPACE OPTIMIZATION

### Quick Wins (No Risk)
1. **Archive old research runs** (>30 days): ~400-500MB saved
2. **Compress Discord/Telegram exports**: 1.7GB → ~400-500MB (75% reduction)
3. **Archive old logs** (>90 days): ~10-15MB saved

### Compression Strategy
```bash
# Discord exports (1.7GB)
tar -czf data/exports_archive_2024.tar.gz data/exports/*_20241*.json
# Expected: 1.7GB → 400-500MB

# Old research runs
tar -czf data/archives/research_2024-10.tar.gz data/research_output/2024-10-*
```

**Total Potential Savings**: ~1.5-1.8GB

---

## CRITICAL FILES - DO NOT MOVE

### Production Entry Points
- `apps/ai_research.py` - Main CLI
- `apps/unified_search_app.py` - Streamlit UI
- `run_research.py` - Legacy entry point
- `run_research_cli.py` - CLI wrapper

### Core Infrastructure
- `llm_utils.py` - LLM utilities (imported everywhere)
- `config_loader.py` - Configuration system
- `core/` - Database integration base classes
- `prompts/` - Jinja2 template directory
- `integrations/` - All database integrations
- `research/` - Deep research engine

### Shared Production Library (Currently Mislabeled)
- `experiments/twitterexplorer_sigint/` - **ACTIVE PRODUCTION CODE**
  - Used by `integrations/social/twitter_integration.py`
  - Should NOT be treated as experimental

---

## PROPOSED ACTIONS (In Priority Order)

### Phase 1: Fix Structural Issues (15 min)
1. Flatten `/tests/tests/` nested directory
2. Merge `/tests/integration/` into `/tests/integrations/`

### Phase 2: Root Cleanup (10 min)
3. Move `analyze_performance.py` to `/scripts/`
4. Move test docs to `/docs/integrations/`

### Phase 3: Disk Space (30 min)
5. Archive old research runs (>30 days)
6. Compress Discord/Telegram exports
7. Create archive policy script

### Phase 4: Documentation (5 min)
8. Add `/experiments/README.md` explaining directory purpose
9. Add note that `twitterexplorer_sigint` is production-critical

**Total Time**: ~60 minutes
**Disk Saved**: 1.5-1.8GB
**Risk Level**: Low (mostly moves, well-tested)

---

## FILES TO REVIEW (Possible Duplicates)

Check for duplicate functionality:
- `/tests/integration/` vs `/tests/integrations/`
- `/experiments/discord/` vs `/integrations/social/discord_integration.py`
- `/experiments/reddit/` vs `/integrations/social/reddit_integration.py`

May reveal dead code or superseded experiments.

