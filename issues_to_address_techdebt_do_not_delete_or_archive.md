# Technical Debt & Known Issues

**DO NOT DELETE OR ARCHIVE THIS FILE**

This file tracks ongoing technical issues, bugs, and tech debt that need to be addressed.

---

## High Priority

**No high priority issues currently open.**

---

## Medium Priority

**No medium priority issues currently open.**

---

## Low Priority

### Dead Code: v1 Research System (~6,000 lines)
**Discovered**: 2025-11-26
**Severity**: Low (not blocking, but significant code bloat)
**Status**: DEFERRED - Intentionally kept for test backward compatibility

**What**: The entire v1 research system (`research/deep_research.py` + `research/mixins/`) is deprecated and not used in production. Production uses v2 `RecursiveResearchAgent`.

**Evidence**:
- `run_research_cli.py` line 14: `from research.recursive_agent import RecursiveResearchAgent`
- `apps/deep_research_tab.py` line 19: uses v2
- `apps/recursive_research.py` line 25: uses v2
- `deep_research.py` lines 5-17: Explicit deprecation notice

**Dead Code Locations**:
| File | Lines | Content |
|------|-------|---------|
| `research/deep_research.py` | 4,392 | v1 SimpleDeepResearch class |
| `research/mixins/source_executor_mixin.py` | ~600 | Only used by v1 |
| `research/mixins/hypothesis_mixin.py` | ~300 | Only used by v1 |
| `research/mixins/query_generation_mixin.py` | ~200 | Only used by v1 |
| `research/mixins/result_filter_mixin.py` | ~200 | Only used by v1 |
| `research/mixins/report_synthesizer_mixin.py` | ~200 | Only used by v1 |
| **TOTAL** | ~6,000 | Dead in production |

**Why Kept**:
- Tests import v1 directly for backward compatibility
- `tests/compare_v1_v2.py` explicitly compares both systems
- Useful as reference during v2 stabilization

**Future Cleanup** (when v2 fully stable):
1. Move v1 to `archive/` directory
2. Update tests to use v2 exclusively
3. Remove mixin files that only serve v1

---

### Dead Code: Old Brave/Exa Search Methods (~150 lines)
**Discovered**: 2025-11-26
**Severity**: Low (cosmetic, no functional impact)
**Status**: DEFERRED
**Note**: This is **doubly dead** code:
1. It's unreachable even within v1 (the `elif brave_search` branch can never execute because brave_search is always in mcp_tools)
2. v1 itself is dead in production (superseded by v2 RecursiveResearchAgent)
If v1 is archived, this goes with it automatically.

**What**: Legacy `_search_brave()` and `_search_exa_fallback()` methods that are never executed due to architecture change.

**Why Dead**:
- All integrations now have `server=None` (deep_research.py:381)
- This routes ALL searches through `_call_mcp_tool()` → `BraveSearchIntegration.execute_search()`
- The `elif tool_name == "brave_search"` branches in source_executor_mixin.py are unreachable
- Brave is always in `mcp_tools` list, so the first `if` condition is always True

**Dead Code Locations**:
| File | Lines | Content |
|------|-------|---------|
| `research/deep_research.py` | 1418-1507 | `_search_brave()` method (~90 lines) |
| `research/deep_research.py` | 1509-1570 | `_search_exa_fallback()` method (~60 lines) |
| `research/mixins/source_executor_mixin.py` | 311-313 | Unreachable `elif brave_search` branch |
| `research/mixins/source_executor_mixin.py` | 502-504 | Unreachable `elif brave_search` branch |

**Related Test File**:
- `tests/integrations/test_deep_research_brave.py` - Tests the dead code path directly (should be removed when code is removed)

**Historical Context**:
- Old design: Brave→Exa automatic failover (if Brave 429, use Exa)
- New design: Brave and Exa are separate independent integrations selected by LLM
- This is an intentional architecture change, not a bug

**Cleanup Action** (when prioritized):
1. Delete `_search_brave()` and `_search_exa_fallback()` from deep_research.py
2. Delete unreachable `elif` branches from source_executor_mixin.py
3. Delete or update `tests/integrations/test_deep_research_brave.py`
4. Verify `_brave_lock` attribute can also be removed if unused elsewhere

**Impact of NOT cleaning up**:
- Minor code bloat (~150 lines)
- Potential confusion for future developers
- Misleading test coverage

---

## Recently Resolved (2025-11-26)

**FBI Vault SeleniumBase Chrome Detection** (verified 2025-11-26)
- "Chrome not found!" errors → Now working with xvfb fallback
- Test: 10 results returned in ~11s for "organized crime" query
- Resolution: Environment/SeleniumBase matured; xvfb fallback handles X11 issues

---

## Previously Resolved (2025-11-24)

**Federal Register Agency Validation** (commit 6c219fa)
- Invalid agency slugs causing 400 errors → Fixed with 3-layer validation
- Test: 3/3 passed

**SEC EDGAR Company Lookup** (commit 2ddc5f1)
- Major defense contractors not found → Fixed with name normalization + aliases
- Test: 6/6 passed (Northrop Grumman, Raytheon/RTX, etc.)

**ClearanceJobs Scraper** (commit ed54624)
- "Search not submitted" Playwright errors → Already fixed (HTTP scraper)
- Test: 5/5 passed - Documented working correctly

**NewsAPI 426 Errors** (commit 3beaf75)
- HTTP 426 "Upgrade Required" errors → Already fixed (30-day limit enforcement)
- Constraint enforcement working: Old dates automatically adjusted
- Test: 2/2 passed (90-day and 7-day queries both succeed)

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

**Last Updated**: 2025-11-26
