#!/bin/bash
# Root Directory Cleanup Script
# Date: 2025-10-20
# Purpose: Archive all non-essential files from root following CLAUDE_PERMANENT.md discipline
# IRON RULE: NEVER DELETE, ALWAYS ARCHIVE

set -e  # Exit on error

echo "=== Root Directory Cleanup - 2025-10-20 ==="
echo "Following IRON RULE: NEVER DELETE, ALWAYS ARCHIVE"
echo ""

# Create archive structure
echo "Creating archive structure..."
mkdir -p archive/2025-10-20/docs
mkdir -p archive/2025-10-20/tests
mkdir -p archive/2025-10-20/temp
mkdir -p archive/2025-10-20/abandoned
mkdir -p archive/reference
mkdir -p archive/backups
mkdir -p data/logs

echo "✓ Archive directories created"
echo ""

# Move session completion docs
echo "Archiving session completion docs..."
mv -v *_COMPLETE.md archive/2025-10-20/docs/ 2>/dev/null || echo "  (no *_COMPLETE.md files)"
mv -v *_STATUS.md archive/2025-10-20/docs/ 2>/dev/null || echo "  (no *_STATUS.md files)"
mv -v *_SUMMARY.md archive/2025-10-20/docs/ 2>/dev/null || echo "  (no *_SUMMARY.md files)"
mv -v REGISTRY_COMPLETE.md archive/2025-10-20/docs/ 2>/dev/null || echo "  (no REGISTRY_COMPLETE.md)"

echo ""

# Move planning/implementation docs
echo "Archiving planning docs..."
mv -v *_PLAN.md archive/2025-10-20/docs/ 2>/dev/null || echo "  (no *_PLAN.md files)"
mv -v *_IMPLEMENTATION*.md archive/2025-10-20/docs/ 2>/dev/null || echo "  (no *_IMPLEMENTATION*.md files)"
mv -v QUICK_START.md archive/2025-10-20/docs/ 2>/dev/null || echo "  (no QUICK_START.md)"
mv -v *_QUICKSTART.md archive/2025-10-20/docs/ 2>/dev/null || echo "  (no *_QUICKSTART.md files)"
mv -v PRODUCTION_DEPLOYMENT.md archive/2025-10-20/docs/ 2>/dev/null || echo "  (no PRODUCTION_DEPLOYMENT.md)"
mv -v TECHNICAL_RISKS_AND_CONCERNS.md archive/2025-10-20/docs/ 2>/dev/null || echo "  (no TECHNICAL_RISKS_AND_CONCERNS.md)"
mv -v CONFIG.md archive/2025-10-20/docs/ 2>/dev/null || echo "  (no CONFIG.md)"
mv -v DIRECTORY_STRUCTURE.md archive/2025-10-20/docs/ 2>/dev/null || echo "  (no DIRECTORY_STRUCTURE.md)"

echo ""

# Move test scripts to tests/
echo "Moving test scripts to tests/..."
mv -v test_*.py tests/ 2>/dev/null || echo "  (no test_*.py files in root)"

echo ""

# Move temp/log files
echo "Archiving temp/log files..."
mv -v *.log archive/2025-10-20/temp/ 2>/dev/null || echo "  (no *.log files)"
mv -v *_output.txt archive/2025-10-20/temp/ 2>/dev/null || echo "  (no *_output.txt files)"
mv -v temp_*.txt archive/2025-10-20/temp/ 2>/dev/null || echo "  (no temp_*.txt files)"
mv -v *.jsonl archive/2025-10-20/temp/ 2>/dev/null || echo "  (no *.jsonl files)"

echo ""

# Move backup files
echo "Archiving backup files..."
mv -v *_backup_*.md archive/backups/ 2>/dev/null || echo "  (no backup files)"

echo ""

# Move reference code/libraries
echo "Archiving reference code..."
mv -v ClearanceJobs archive/reference/ 2>/dev/null || echo "  (ClearanceJobs already moved)"
mv -v api-code-samples archive/reference/ 2>/dev/null || echo "  (api-code-samples already moved)"
mv -v chromedriver-linux64 archive/reference/ 2>/dev/null || echo "  (chromedriver already moved)"
mv -v data.gov archive/reference/ 2>/dev/null || echo "  (data.gov already moved)"
mv -v dce-cli archive/reference/ 2>/dev/null || echo "  (dce-cli already moved)"
mv -v twitterexplorer archive/reference/ 2>/dev/null || echo "  (twitterexplorer already moved)"
mv -v twitterexplorer_sigint archive/reference/ 2>/dev/null || echo "  (twitterexplorer_sigint already moved)"
mv -v usa_jobs_api_info archive/reference/ 2>/dev/null || echo "  (usa_jobs_api_info already moved)"
mv -v downloaded_files archive/reference/ 2>/dev/null || echo "  (downloaded_files already moved)"

echo ""

# Move abandoned feature docs
echo "Archiving abandoned feature docs..."
mv -v PROPOSED_TAG_TAXONOMY.md archive/2025-10-20/abandoned/ 2>/dev/null || echo "  (no PROPOSED_TAG_TAXONOMY.md)"
mv -v TAG_SYSTEM_FILES.md archive/2025-10-20/abandoned/ 2>/dev/null || echo "  (no TAG_SYSTEM_FILES.md)"

echo ""

# Move other completed integration docs
echo "Archiving completed integration docs..."
mv -v TWITTER_*.md archive/2025-10-20/docs/ 2>/dev/null || echo "  (no TWITTER_*.md files)"
mv -v DISCORD_*.md archive/2025-10-20/docs/ 2>/dev/null || echo "  (no DISCORD_*.md files)"
mv -v CLOUDFLARE_*.md archive/2025-10-20/docs/ 2>/dev/null || echo "  (no CLOUDFLARE_*.md files)"
mv -v PLAYWRIGHT_MIGRATION.md archive/2025-10-20/docs/ 2>/dev/null || echo "  (no PLAYWRIGHT_MIGRATION.md)"
mv -v CLAUDE_MD_CHANGELOG.md archive/2025-10-20/docs/ 2>/dev/null || echo "  (no CLAUDE_MD_CHANGELOG.md)"

echo ""

# Move boolean search system docs (completed)
echo "Archiving Boolean search system docs..."
mv -v BOOLEAN_SEARCH_SYSTEM_ULTRATHINKING.md archive/2025-10-20/docs/ 2>/dev/null || echo "  (no BOOLEAN_SEARCH_SYSTEM_ULTRATHINKING.md)"

echo ""

# Move migration/cleanup docs
echo "Archiving migration/cleanup docs..."
mv -v DIRECTORY_CLEANUP_*.md archive/2025-10-20/docs/ 2>/dev/null || echo "  (no DIRECTORY_CLEANUP_*.md files)"
mv -v UNUSED_SUGGESTIONS.md archive/2025-10-20/docs/ 2>/dev/null || echo "  (no UNUSED_SUGGESTIONS.md)"

echo ""

# Move keyword/investigation docs to docs/
echo "Moving investigative docs to docs/..."
mv -v INVESTIGATIVE_KEYWORDS_CURATED.md docs/ 2>/dev/null || echo "  (INVESTIGATIVE_KEYWORDS_CURATED.md already in docs/)"

echo ""

# Move cost tracking doc to docs/
echo "Moving technical docs to docs/..."
mv -v COST_TRACKING_AND_GPT5_NANO.md docs/ 2>/dev/null || echo "  (COST_TRACKING_AND_GPT5_NANO.md already in docs/)"

echo ""

# Move utility scripts
echo "Moving utility scripts to scripts/..."
mv -v extract_keywords_for_boolean.py scripts/ 2>/dev/null || echo "  (extract_keywords_for_boolean.py already in scripts/)"
mv -v organize_keywords.py scripts/ 2>/dev/null || echo "  (organize_keywords_py already in scripts/)"
mv -v generate_relevance_descriptions.py scripts/ 2>/dev/null || echo "  (generate_relevance_descriptions.py already in scripts/)"

echo ""

# Move image files
echo "Archiving image files..."
mv -v image.png archive/2025-10-20/temp/ 2>/dev/null || echo "  (no image.png)"

echo ""

# Move exports_stripped
echo "Archiving exports_stripped..."
mv -v exports_stripped archive/reference/ 2>/dev/null || echo "  (exports_stripped already moved)"

echo ""

echo "=== Creating Archive README ==="

cat > archive/2025-10-20/README.md << 'EOF'
# Archive: 2025-10-20

## What Was Archived

### Session Completion Docs
- CLEANUP_COMPLETE.md - Directory cleanup session documentation
- REGISTRY_COMPLETE.md - Integration registry refactor completion
- TWITTER_INTEGRATION_COMPLETE.md - Twitter integration completion
- TWITTER_UI_TESTING_COMPLETE.md - Twitter UI testing completion
- TWITTER_INTEGRATION_FINAL_SUMMARY.md - Final Twitter integration summary
- TWITTER_BOOLEAN_MONITOR_COMPLETE.md - Twitter boolean monitor completion
- DISCORD_INTEGRATION_STATUS.md - Discord integration status

### Planning Docs (Completed)
- PHASE_1_IMPLEMENTATION_PLAN.md - Phase 1 Boolean Monitoring plan (now complete)
- DISCORD_INTEGRATION_PLAN.md - Discord integration planning
- DIRECTORY_CLEANUP_PLAN.md - Directory cleanup planning
- DIRECTORY_CLEANUP_SUMMARY.md - Directory cleanup summary
- QUICK_START.md - Quick start guide (replaced by README.md)
- KEYWORD_DATABASE_QUICKSTART.md - Keyword database quick start
- PRODUCTION_DEPLOYMENT.md - Production deployment notes
- TECHNICAL_RISKS_AND_CONCERNS.md - Technical risks documentation
- CONFIG.md - Configuration documentation
- DIRECTORY_STRUCTURE.md - Directory structure documentation
- BOOLEAN_SEARCH_SYSTEM_ULTRATHINKING.md - Boolean search system design
- REGISTRY_REFACTOR_PLAN.md - Registry refactor planning
- REGISTRY_REFACTOR_IMPLEMENTATION.md - Registry refactor implementation

### Technical Migration Docs
- PLAYWRIGHT_MIGRATION.md - Puppeteer to Playwright migration (moved to docs/)
- CLOUDFLARE_BYPASS_TEST_RESULTS.md - Cloudflare bypass testing results
- CLAUDE_MD_CHANGELOG.md - CLAUDE.md changelog

### Test Scripts (Moved to tests/)
- test_3_monitors.py - 3 monitor testing script
- test_ai_research_comprehensive.py - AI research comprehensive test
- test_ai_research_standalone.py - AI research standalone test
- test_discord_cli.py - Discord CLI test
- test_fbi_vault_integration.py - FBI Vault integration test
- test_fbi_vault_nodriver.py - FBI Vault nodriver test
- test_fbi_vault_seleniumbase.py - FBI Vault seleniumbase test
- test_fbi_vault_stealth.py - FBI Vault stealth test
- test_fbi_vault_undetected.py - FBI Vault undetected test
- test_parallel_search_only.py - Parallel search testing
- test_twitter_api_validation.py - Twitter API validation
- test_twitter_apikey_mapping.py - Twitter API key mapping test
- test_twitter_boolean_monitor.py - Twitter boolean monitor test
- test_twitter_boolean_simple.py - Twitter boolean simple test
- test_twitter_e2e.py - Twitter E2E test
- test_twitter_integration.py - Twitter integration test

### Temporary Files
- temp_boolean_log.txt - Boolean monitor debug log
- temp_ssh_output.txt - SSH output temp file
- test_output.log - Test output log
- test_output.txt - Test output text
- ai_research_test.log - AI research test log
- api_requests.jsonl - API requests log
- image.png - Temporary image

### Backup Files
- CLAUDE_md_backup_20251020.md - CLAUDE.md backup

### Abandoned Features
- PROPOSED_TAG_TAXONOMY.md - Tag taxonomy proposal (not implemented)
- TAG_SYSTEM_FILES.md - Tag system files documentation
- UNUSED_SUGGESTIONS.md - Unused feature suggestions

### Reference Code/Libraries
- ClearanceJobs/ - Official Python library (broken API, reference only)
- api-code-samples/ - Official DVIDS API examples
- chromedriver-linux64/ - ChromeDriver binary
- data.gov/ - Data.gov reference materials
- dce-cli/ - DCE CLI reference
- twitterexplorer/ - TwitterExplorer reference
- twitterexplorer_sigint/ - TwitterExplorer SIGINT fork
- usa_jobs_api_info/ - USAJobs API information
- downloaded_files/ - Downloaded reference files
- exports_stripped/ - Stripped export files

## Why Archived

Cleanup on 2025-10-20 after completing Phase 1.5 Week 1 (Adaptive Search).

Root directory had grown to 86+ items (38 markdown files, 16 test scripts, 7 temp files, 25 directories).

Cleaned to ~15 files following CLAUDE_PERMANENT.md "Root Directory Discipline" protocol.

## Preserved For

- Historical record of implementation decisions
- Reference if features need to be revisited
- Understanding evolution of the codebase
- Test scripts preserved in tests/ directory
- Reference code preserved for API pattern reference

## Root Directory After Cleanup

Should contain only:
- Core docs: CLAUDE.md, STATUS.md, ROADMAP.md, PATTERNS.md, INVESTIGATIVE_PLATFORM_VISION.md, README.md, REGENERATE_CLAUDE.md, CLAUDE_PERMANENT.md, CLAUDE_TEMP.md
- Config: .env, .gitignore, requirements.txt, config_default.yaml, config.yaml
- Core utils: llm_utils.py, config_loader.py
- Total: ~15 files

## Notes

- NEVER DELETE RULE: All files archived, nothing deleted
- Test scripts moved to tests/ (still accessible)
- Utility scripts moved to scripts/
- Technical docs moved to docs/
- Reference code preserved in archive/reference/
EOF

echo "✓ Archive README created"
echo ""

echo "=== Cleanup Complete ==="
echo ""
echo "Root directory cleaned following CLAUDE_PERMANENT.md protocol:"
echo "  - Session completion docs → archive/2025-10-20/docs/"
echo "  - Planning docs → archive/2025-10-20/docs/"
echo "  - Test scripts → tests/"
echo "  - Temp/log files → archive/2025-10-20/temp/"
echo "  - Backup files → archive/backups/"
echo "  - Reference code → archive/reference/"
echo "  - Abandoned features → archive/2025-10-20/abandoned/"
echo ""
echo "Archive README created at: archive/2025-10-20/README.md"
echo ""
echo "IRON RULE FOLLOWED: Nothing deleted, everything archived with explanation"
echo ""
echo "Review root directory:"
ls -1 | head -20
echo ""
echo "Total files in root:"
ls -1 | wc -l
echo ""
echo "Expected: ~15 files (Core docs + config + utils)"
