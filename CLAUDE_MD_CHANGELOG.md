# CLAUDE.md Changelog

## 2025-10-19 - Fixed CLAUDE_TEMP.md to Be True Schema + Added Essential Tests Section

### What Changed

1. **CLAUDE_TEMP.md Converted to True Schema/Template**:
   - Removed all actual data (dates, phase names, specific blockers)
   - Replaced with placeholders: `[YYYY-MM-DD]`, `[Phase Name]`, `[Component name]`
   - Now shows STRUCTURE only, not actual content

2. **CLAUDE_PERMANENT.md Archive Date Fixed**:
   - Changed `2025-10-19/` to `YYYY-MM-DD/` (timeless pattern)
   - Archive dates don't belong in PERMANENT section

3. **Added "ESSENTIAL TESTS & TOOLS" Section**:
   - Documents which tests/tools worth keeping in context window
   - Which to regenerate on-demand
   - Philosophy: LLM can recreate simple tools, only keep complex/non-obvious ones

### Why This Change

**CLAUDE_TEMP.md Was Misunderstood**:
- Was acting as actual temporary data instead of schema
- Should be blueprint showing HOW to fill TEMPORARY section, not actual data
- User clarification: "claude_temp should be a schema which shows how to populate the temp section"

**Archive Dates in PERMANENT Were Wrong**:
- Specific dates (2025-10-19) don't belong in timeless PERMANENT section
- Should use placeholders for patterns

**Missing Guidance on Tests/Tools**:
- With LLM assistance, most tests/tools should be regenerated on-demand
- Only keep complex integrations and non-obvious workarounds in context window
- Need explicit guidance on what's worth keeping vs regenerating

### Changes Made

**CLAUDE_TEMP.md**:
- All sections now use placeholders
- Shows structure: `[Phase Name]`, `[Component name]`, `[Command]`, `[Evidence]`
- Example format preserved but no actual data
- Acts as template that Claude Code reads to understand how to populate CLAUDE.md TEMPORARY

**CLAUDE_PERMANENT.md**:
- Archive directory: `2025-10-19/` → `YYYY-MM-DD/`
- Added "ESSENTIAL TESTS & TOOLS" section (before QUICK REFERENCE COMMANDS)
- Categorizes: tests to keep, tests to regenerate, tools to keep, tools to regenerate
- Entry points always kept

**QUICK REFERENCE COMMANDS**:
- Updated test paths: `python3 tests/test_*.py` (consolidated location)
- Added notes about which are essential vs on-demand

### Files Modified

- `CLAUDE_TEMP.md` - Complete rewrite as true schema/template
- `CLAUDE_PERMANENT.md` - Fixed archive date, added ESSENTIAL TESTS & TOOLS section, updated commands
- `CLAUDE.md` - Regenerated from updated source files
- `CLAUDE_MD_CHANGELOG.md` - This entry

### Philosophy Clarified

**PERMANENT** = Timeless principles, patterns, directory structure
- NO specific dates, phase names, or current status
- YES patterns, rules, permanent workarounds

**TEMP Schema** = Blueprint for temporary section structure
- NO actual data
- YES placeholders showing format

**TEMP Section in CLAUDE.md** = Actual current work
- Populated using TEMP schema as guide
- Updated frequently during work

---

## 2025-10-19 - Directory Structure Update & Cleanup

### What Changed

Updated CLAUDE_PERMANENT.md directory structure section to match actual repository structure after comprehensive cleanup.

### Why This Change

CLAUDE.md claimed incorrect directory structure:
- Missing subdirectories: `integrations/government/`, `integrations/social/`
- Missing directories: `data/`, `monitoring/`, `research/`, `utils/`, `experiments/`, `scripts/`
- Missing reference directories: `ClearanceJobs/`, `api-code-samples/`, article directories
- Test files were split between root and tests/ directory

### Changes Made

**Directory Structure Section**:
- Added `integrations/government/` and `integrations/social/` subdirectories
- Listed all core/ files (8 files total, not just 5)
- Added all missing directories with descriptions
- Documented reference repositories (ClearanceJobs/, api-code-samples/)
- Documented data directories (bills_blackbox/, klippenstein/)
- Updated tests/ section (now shows 18 files, all consolidated)

**File Finding Guide**:
- Updated integration example path: `integrations/government/sam_integration.py`
- Added regeneration instructions pointer: REGENERATE_CLAUDE.md
- Added archive lookup instructions: archive/YYYY-MM-DD/README.md

**Database Integration Pattern**:
- Updated save location to `integrations/government/` or `integrations/social/`
- Updated registry location to `integrations/registry.py`
- Updated test location to `tests/`

### Cleanup Actions Completed

**Phase 1 - Archived Files** (9 files to `archive/2025-10-19/`):
- 3 old CLAUDE.md variants (CLAUDE_v2.md, CLAUDE_OLD.md, CLAUDE_IMPROVED.md)
- 3 duplicate status reports (ACTUAL_STATUS.md, TESTED_INTEGRATIONS_REPORT.md, INTEGRATION_TEST_STATUS.md)
- 1 obsolete Puppeteer implementation (clearancejobs_puppeteer.py)
- 2 temp files (si_convo_temp.txt, keyword_extraction_raw_summary.txt)

**Phase 2 - Consolidated Tests** (6 files moved from root → `tests/`):
- test_all_four_databases.py
- test_clearancejobs_playwright.py
- test_cost_tracking.py
- test_live.py
- test_usajobs_live.py
- test_verification.py

**Phase 3 - Updated Documentation**:
- CLAUDE_PERMANENT.md directory structure
- CLAUDE.md regenerated with correct structure
- Created DIRECTORY_CLEANUP_SUMMARY.md
- Created PHASE1_ARCHIVE_MANIFEST.md

### Files Modified

- `CLAUDE_PERMANENT.md` - Updated directory structure, file finding guide, database integration pattern
- `CLAUDE.md` - Regenerated from updated CLAUDE_PERMANENT.md + CLAUDE_TEMP.md
- `CLAUDE_MD_CHANGELOG.md` - This file (updated)

### Total Impact

- **Files archived**: 9 (0 deleted - all preserved in archive/2025-10-19/)
- **Files moved**: 6 (consolidated tests to tests/ directory)
- **Root directory**: Reduced from 39 to 33 files (cleaner)
- **Directory structure**: Now accurately documented in CLAUDE.md
- **All imports verified**: Core and integration imports still work

### Verification

- ✅ Core imports work: `core.database_integration_base`, `integrations.registry`
- ✅ Integration imports work: `integrations.government.sam_integration`, `integrations.government.dvids_integration`
- ✅ Archive complete: All 9 files preserved in archive/2025-10-19/
- ✅ Tests consolidated: All 18 test files now in tests/ directory

---

## 2025-10-19 - Added Principle #8: Discovery Before Building

### What Changed

Added new Core Principle #8 to PERMANENT section: "DISCOVERY BEFORE BUILDING"

### Why This Change

User reported circular work pattern in parallel Claude Code session:
1. Agent built test scripts for DVIDS/USAJobs
2. Agent tested and claimed "EXCELLENT! Works perfectly!"
3. Agent wrote TESTED_INTEGRATIONS_REPORT.md
4. Agent then discovered apps/unified_search_app.py already existed
5. Agent wrote ACTUAL_STATUS.md apologizing
6. Agent went in circles instead of discovering first

### What Principle #8 Does

**Mandatory discovery steps at session start**:
1. Read STATUS.md - what's already [PASS]?
2. Read CLAUDE.md TEMPORARY section - what's the current task?
3. Check directory structure - does it already exist?
4. Test existing entry points FIRST - does it already work?

**Discovery checklist** (complete BEFORE starting work):
- [ ] Read STATUS.md for component status
- [ ] Read CLAUDE.md TEMPORARY section for current task
- [ ] Search for existing implementations
- [ ] Test existing user-facing entry points (apps/, not custom test scripts)
- [ ] Only build if discovery proves it doesn't exist or is broken

### Other Changes in This Update

1. **Enhanced Principle #1 examples**: Added real failure example from parallel session
2. **Enhanced Principle #3 forbidden phrases**: Added "EXCELLENT!", "PERFECT!", specific emoji bans

### Files Modified

- `CLAUDE_PERMANENT.md` - Added Principle #8, enhanced Principles #1 and #3
- `CLAUDE.md` - Regenerated from CLAUDE_PERMANENT.md + CLAUDE_TEMP.md
- `CLAUDE_MD_CHANGELOG.md` - This file (created)

### How to Apply

Already applied. Next Claude Code session will see updated CLAUDE.md with:
- 8 core principles (was 7)
- Discovery checklist
- Real examples from actual failures

### Validation

New principle addresses exact failure pattern:
- ✅ Agent would read STATUS.md first
- ✅ Agent would discover apps/unified_search_app.py exists
- ✅ Agent would test it via `streamlit run apps/unified_search_app.py`
- ✅ Agent would report what works/broken instead of rebuilding
- ✅ No circular "discover → apologize → rebuild" pattern

---

## 2025-10-19 - Initial CLAUDE.md Creation

Created permanent/temporary structure with 7 core principles:
1. Adversarial Testing Mentality
2. Evidence Hierarchy
3. Forbidden Claims & Required Language
4. Task Scope Declaration
5. Mandatory Checkpoints (Every 15 Minutes)
6. No Lazy Implementations
7. Fail-Fast and Loud

See `archive/2025-10-19/README.md` for details.
