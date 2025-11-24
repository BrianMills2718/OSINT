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

**No low priority issues currently open.**

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

**Last Updated**: 2025-11-23
