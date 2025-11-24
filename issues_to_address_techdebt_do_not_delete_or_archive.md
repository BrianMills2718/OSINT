# Technical Debt & Known Issues

**DO NOT DELETE OR ARCHIVE THIS FILE**

This file tracks ongoing technical issues, bugs, and tech debt that need to be addressed.

---

## High Priority

**No high priority issues currently open.**

---

## Medium Priority

### FBI Vault Integration - SeleniumBase Chrome Detection
**Discovered**: 2025-10-20
**Severity**: Medium (integration blocked but not critical for MVP)
**Status**: DEFERRED

**Symptoms**:
- SeleniumBase reports "Chrome not found!" despite Chrome binary existing
- Chrome installed at: `~/.cache/puppeteer/chrome/linux-131.0.6778.204/chrome-linux64/chrome`
- Code already passes `binary_location` parameter to SeleniumBase

**Impact**:
- FBI Vault integration non-functional
- FOIA documents unavailable
- Not critical for Phase 1 MVP

**Possible Causes**:
1. WSL2 environment detection issues
2. SeleniumBase expecting different Chrome path structure
3. Permissions issues with Puppeteer cache directory

**Investigation Steps** (when prioritized):
1. Try manual SeleniumBase installation: `playwright install chromium`
2. Test Chrome binary directly: `~/.cache/puppeteer/chrome/linux-131.0.6778.204/chrome-linux64/chrome --version`
3. Check SeleniumBase documentation for WSL2-specific configuration
4. Try alternative Chrome installation methods

**Files**:
- `integrations/government/fbi_vault.py` (lines 156-253: _scrape_fbi_vault_sync method)

---

## Low Priority

### NewsAPI 426 Upgrade Required Errors
**Discovered**: 2025-11-24
**Severity**: Low (news coverage affected but not critical)
**Status**: INVESTIGATING

**Symptoms**:
- HTTP 426 errors: "Upgrade Required" from NewsAPI
- Error observed in production research runs
- Previous fix (commit 3beaf75) may need review

**Impact**:
- Missing news coverage from NewsAPI source
- Other news sources (Brave Search) available as fallback
- Not blocking core research functionality

**Next Steps**:
1. Investigate NewsAPI response to understand 426 error
2. Check API tier limitations or required parameters
3. Review previous fix (commit 3beaf75) for completeness
4. Test with valid API key and different query patterns

**Files**:
- `integrations/news/newsapi_integration.py`

---

## Recently Resolved (2025-11-24)

**Federal Register Agency Validation** (commit 6c219fa)
- Invalid agency slugs causing 400 errors → Fixed with 3-layer validation
- Test: 3/3 passed

**SEC EDGAR Company Lookup** (commit 2ddc5f1)
- Major defense contractors not found → Fixed with name normalization + aliases
- Test: 6/6 passed (Northrop Grumman, Raytheon/RTX, etc.)

**ClearanceJobs Scraper** (commit ed54624)
- "Search not submitted" Playwright errors → Already fixed (HTTP scraper)
- Test: 5/5 passed - Documented working correctly

---

## How to Use This File

**Adding Issues**:
1. Add to appropriate priority section
2. Include: Discovered date, Severity, Status, Symptoms, Evidence, Impact, Possible Causes, Investigation Steps, Related Files
3. Use clear headings and code blocks for evidence

**Resolving Issues**:
1. When resolved, remove from this file completely (don't move to "Completed" section)
2. Document the fix in commit message or STATUS.md
3. If historically significant, archive details to `archive/YYYY-MM-DD/docs/`

**Prioritization**:
- **High**: Blocking core functionality, affects production
- **Medium**: Limits features but workarounds exist
- **Low**: Nice to have, future enhancements

---

**Last Updated**: 2025-11-24
