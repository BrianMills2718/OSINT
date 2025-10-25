# RESOLVED_TASKS.md

**Purpose**: Chronological log of completed tasks with one-line summaries for historical reference.

**Format**: `YYYY-MM-DD: [Task description] - [Status] - [Commit hash or evidence]`

---

## 2025-10-25

- 2025-10-25: Reddit query syntax empirical testing - BEST: Unquoted AND (43% accuracy). AVOID: Quoted phrases + Boolean (0%). Created docs/INTEGRATION_QUERY_GUIDES.md with evidence-based recommendations. - [COMPLETE] - c049e6f
- 2025-10-25: AGENT2 - DVIDS 403 investigation COMPLETE - Root cause: DVIDS API limits queries with quoted phrases to max 2 OR terms. Systematic isolation testing (25+ queries) proved 100% reproducible pattern. NOT content filtering (tested with innocent terms). Query decomposition mitigation already exists. Documented in docs/INTEGRATION_QUERY_GUIDES.md. - [COMPLETE] - tests/test_dvids_isolate_403.py, tests/test_dvids_final_isolation.py
- 2025-10-25: DVIDS LLM prompt updated with empirical query syntax guidance - Added tested syntax rules: prefer unquoted keywords (unlimited OR), avoid quoted phrases (2-term limit). References docs/INTEGRATION_QUERY_GUIDES.md for evidence. Prevents LLM from generating queries that trigger HTTP 403. - [COMPLETE] - dvids_integration.py:110-131
- 2025-10-25: SAM.gov query syntax testing - Unable to test empirically (15/15 queries HTTP 429 rate limited). Documented rate limiting severity and accepted official Lucene syntax claims without validation. Recommendations: keep queries simple, avoid test suites. - [BLOCKED BY RATE LIMITS] - tests/test_sam_query_syntax.py, docs/INTEGRATION_QUERY_GUIDES.md
- 2025-10-25: USAJobs query syntax empirical testing - FINDING: Single Boolean operators work (AND/OR/NOT), complex queries return 0 results. Updated LLM prompt to allow simple Boolean, forbid complexity (multiple OR, parentheses, mixed syntax). Previous prompt guidance "DO NOT use OR" was incorrect. - [COMPLETE] - tests/test_usajobs_query_syntax.py, docs/INTEGRATION_QUERY_GUIDES.md, usajobs_integration.py:100-124

## 2025-10-24

- 2025-10-24: Reddit integration BOTH phases complete - [COMPLETE] - Real-time + daily scraper
- 2025-10-24: Reddit Phase 1 - Real-time search (360 lines, tested, 4 results) - [COMPLETE] - reddit_integration.py
- 2025-10-24: Reddit Phase 2 - Daily scraper (280 lines, 24 subreddits, rate limited) - [COMPLETE] - reddit_daily_scrape.py
- 2025-10-24: Reddit config created (24 subreddits across 5 categories) - [COMPLETE] - reddit_config.json
- 2025-10-24: Reddit cron setup script created (3 AM daily) - [COMPLETE] - setup_reddit_scraper.sh
- 2025-10-24: Reddit documentation complete (setup, usage, troubleshooting) - [COMPLETE] - experiments/reddit/README.md
- 2025-10-24: Discord daily scraping setup (cron job at 2 AM, both servers) - [COMPLETE] - Cron configured
- 2025-10-24: The OWL Discord backfill started (140 chunks, ~18-20 hours) - [IN PROGRESS] - PID 3045417
- 2025-10-24: Fix Discord DiscordChatExporter CLI path (archive/reference/dce-cli/) - [COMPLETE] - discord_backfill.py:20
- 2025-10-24: Update Discord token for verified account - [COMPLETE] - discord_servers.json
- 2025-10-24: Create discord_daily_scrape.py (daily incremental scraper) - [COMPLETE] - New file
- 2025-10-24: Create Discord scraping documentation (README.md) - [COMPLETE] - experiments/discord/README.md
- 2025-10-24: Week 2-4 Refactoring - Integration tests (10 scenarios, 2 files) - [COMPLETE] - 64d63a6
- 2025-10-24: Week 2-4 Refactoring - Performance tests (9 scenarios, 2 files, registry tests PASSED) - [COMPLETE] - 77371fc
- 2025-10-24: Week 2-4 Refactoring - Fix Trio event loop failures (34 failures → 16 passing) - [COMPLETE] - 824b31d
- 2025-10-24: Week 2-4 Refactoring - pytest markers (5 markers, selective execution) - [COMPLETE] - 852476d
- 2025-10-24: Update CLAUDE.md TEMPORARY section - Week 2-4 complete - [COMPLETE] - Direct edit
- 2025-10-24: Condense CLAUDE.md Environment Setup section (598→607 lines) - [COMPLETE] - Direct edit
- 2025-10-24: Add RESOLVED_TASKS.md organizational plan to CLAUDE.md - [COMPLETE] - Direct edit
- 2025-10-24: Create RESOLVED_TASKS.md file with initial entries - [COMPLETE] - This file

## 2025-10-23

- 2025-10-23: Contract tests for query generation (DVIDS, Discord, ClearanceJobs) - [COMPLETE] - bc31f9a
- 2025-10-23: Feature flags + lazy instantiation for all 8 integrations - [COMPLETE] - 7809666
- 2025-10-23: Import isolation + status tracking in registry - [COMPLETE] - 7809666
- 2025-10-23: Monitor None returns in ParallelExecutor with ERROR logging - [COMPLETE] - 7809666
- 2025-10-23: Add disclaimer to COMPREHENSIVE_STATUS_REPORT.md about point-in-time evidence - [COMPLETE] - Direct edit
- 2025-10-23: Codex review fixes (6 issues addressed with verified evidence) - [COMPLETE] - c012c9a

## 2025-10-22

- 2025-10-22: Deep Research diagnosis on Streamlit Cloud (0 tasks executed, 4 failed) - [BLOCKED] - Pending Brave Search integration
- 2025-10-22: Enhanced error logging deployed to Streamlit Cloud - [COMPLETE] - Deployment
- 2025-10-22: User tested and confirmed diagnosis (government DBs don't have classified docs) - [VERIFIED] - User feedback

## Earlier (Before RESOLVED_TASKS.md)

- 2025-10-20: Fix SAM.gov rate limit handling (exponential backoff, 3 retries) - [COMPLETE] - b3946ec
- 2025-10-20: Fix Discord integration (ANY-match vs ALL-match) - [COMPLETE] - b3946ec
- 2025-10-20: Fix DVIDS integration (query decomposition) - [COMPLETE] - b3946ec
- 2025-10-18: ClearanceJobs Playwright scraper (replaced broken API) - [COMPLETE] - Previous commit
- 2025-10-15: Phase 1 Boolean Monitoring deployment (6 monitors, daily scheduler) - [COMPLETE] - Multiple commits
- 2025-10-10: Phase 1.5 Week 1 Adaptive Search implementation - [COMPLETE] - Multiple commits

---

**Note**: This file starts 2025-10-24. Earlier tasks reconstructed from commit history and CLAUDE.md references.
