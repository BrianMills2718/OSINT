# ClearanceJobs Playwright Migration

## Summary

Migrated ClearanceJobs integration from Puppeteer MCP to Playwright to enable:
- ✓ Standalone Python execution (no MCP dependency)
- ✓ Parallel execution with other database integrations
- ✓ Production deployment anywhere
- ✓ Same scraping functionality as Puppeteer version

## Files Created/Modified

### New Files

1. **`integrations/clearancejobs_playwright.py`**
   - Standalone Playwright scraper
   - Async function: `search_clearancejobs(keywords, limit, headless)`
   - Returns: `{"success": bool, "total": int, "jobs": List[Dict], "error": str}`
   - Features:
     - Browser automation (Chromium)
     - Vue.js event triggering for search form
     - Cookie popup dismissal
     - Clearance level parsing
     - Job data extraction

2. **`test_clearancejobs_playwright.py`**
   - Quick verification test for Playwright scraper
   - Tests 2 different search queries
   - Run immediately after installation completes

3. **`test_all_four_databases.py`**
   - Comprehensive test of all 4 database integrations
   - Tests parallel execution
   - Handles case where Playwright not installed yet
   - Tests:
     - ClearanceJobs standalone
     - 3 API databases in parallel (SAM, DVIDS, USAJobs)
     - All 4 databases in parallel

### Modified Files

1. **`integrations/clearancejobs_integration.py`**
   - Changed from Puppeteer MCP to Playwright
   - Updated `execute_search()` to call Playwright scraper
   - Added clearance level filtering
   - Updated metadata (response time: 5s for browser automation)

## Installation Status

**Current**: `pip install playwright` running (PID: 513643)

**Still needed**:
```bash
playwright install chromium
```

## Testing Steps (After Installation)

### Step 1: Quick ClearanceJobs Test
```bash
python3 test_clearancejobs_playwright.py
```

Expected output:
- ✓ Search successful for "cybersecurity analyst"
- ✓ Results include title, company, location, clearance level
- ✓ Search successful for "software engineer"

### Step 2: Comprehensive 4-Database Test
```bash
python3 test_all_four_databases.py
```

Expected output:
- ✓ ClearanceJobs: Playwright scraper working
- ✓ SAM.gov: API-based working
- ✓ DVIDS: API-based working
- ✓ USAJobs: API-based working
- ✓ Parallel execution: All 4 databases working

### Step 3: Integration Test
```bash
python3 test_verification.py
```

Should work with existing 3 databases. Update to include ClearanceJobs.

## Architecture

### Before (Puppeteer MCP)
```
ClearanceJobsIntegration
  └─> clearancejobs_puppeteer.py
      └─> Puppeteer MCP tools (Claude Code only)
          ❌ Cannot run standalone
          ❌ Cannot run in parallel with Python code
```

### After (Playwright)
```
ClearanceJobsIntegration
  └─> clearancejobs_playwright.py
      └─> Playwright library (pure Python)
          ✓ Runs standalone
          ✓ Runs in parallel with other integrations
          ✓ Can be deployed anywhere
```

## Parallel Execution Example

```python
# All 4 databases searched simultaneously
async def run_all():
    # API-based databases
    api_task = parallel_executor.execute_all(
        databases=[sam, dvids, usajobs],
        api_keys=keys
    )

    # Web scraping database
    cj_task = search_clearancejobs("keyword")

    # Run in parallel
    api_results, cj_results = await asyncio.gather(api_task, cj_task)
```

## Performance Comparison

| Database | Method | Typical Response Time |
|----------|--------|----------------------|
| SAM.gov | REST API | ~2-5s |
| DVIDS | REST API | ~1-2s |
| USAJobs | REST API | ~2-4s |
| ClearanceJobs | Playwright | ~5-8s (browser) |

All 4 running in parallel: ~8s total (limited by slowest)

## Next Steps

1. ⏳ Wait for Playwright installation to complete
2. ⏳ Run `playwright install chromium`
3. 🔜 Test ClearanceJobs Playwright scraper
4. 🔜 Run comprehensive 4-database test
5. 🔜 Update CLAUDE.md to mark Playwright migration complete
6. 🔜 Update README.md to document all 4 integrations

## Troubleshooting

### "ModuleNotFoundError: No module named 'playwright'"
```bash
pip install playwright
playwright install chromium
```

### "Executable doesn't exist at /path/to/chromium"
```bash
playwright install chromium
```

### Browser fails to launch
Check if WSL has required dependencies:
```bash
# Install WSL dependencies for Chromium
sudo apt-get update
sudo apt-get install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2
```

## Benefits of Playwright

1. **Pure Python**: No external dependencies or MCP servers
2. **Async/Await**: Native asyncio support for parallel execution
3. **Headless**: Runs without display (perfect for servers)
4. **Reliable**: Industry-standard browser automation
5. **Fast**: Optimized for performance
6. **Maintained**: Active development by Microsoft

## References

- Playwright Python: https://playwright.dev/python/
- ClearanceJobs: https://www.clearancejobs.com/jobs
- Original Puppeteer implementation: `integrations/clearancejobs_puppeteer.py`
