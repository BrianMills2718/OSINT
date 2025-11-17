# Phase 3 Findings: Co-occurrence Sparsity Analysis

**Date**: 2025-11-16
**Status**: ⚠️ LIMITATION IDENTIFIED
**Issue**: Low co-occurrence density due to extraction methodology

---

## Problem Discovered

**Observed**: Only 55 entity pairs co-occur across 168 entities (sparse network)
**Expected**: Higher co-occurrence density given entity-rich source text

---

## Root Cause Analysis

### The Extraction Approach Creates Artificial Separation

**How Phase 1-2 extraction works**:
1. LLM extracts entities from report
2. For each entity, LLM provides separate "mentions" list with snippets
3. Each entity gets its own evidence snippets
4. Database stores these as separate evidence rows

**Result**: Even when 10 entities appear in the SAME paragraph, they end up in separate evidence rows.

**Example from report3_bellingcat_fsb_elbrus.md line 17**:

```
Original paragraph (single block of text):
"Bellingcat and The Insider had previously identified Col. Igor Anatolyevich Egorov
as a senior officer from FSB's elite Spetznaz force known as Department V, the
successor to the KGB's elite subversion and special operations unit Vympel. In our
previous investigations into the role of GRU undercover officers in supervising and
aiding Russian and Russia-backed militants in Eastern Ukraine, we had stumbled upon
this person, who in 2014 and 2015 had traveled extensively between Moscow and the
three control centers for Russia's military operations in the Donbass: Rostov,
Simferopol, and Krasnodar."

Entities in this single paragraph: 11+
- Bellingcat, The Insider, Igor Egorov, FSB, Department V, KGB, Vympel, GRU,
  Donbass, Moscow, Rostov, Simferopol, Krasnodar

How extraction stores it:
- Entity "Bellingcat": snippet "Bellingcat and The Insider had previously identified..."
- Entity "Igor Egorov": snippet "Bellingcat and The Insider had previously identified..."
- Entity "FSB": snippet "...as a senior officer from FSB's elite Spetznaz force..."
- Entity "Department V": snippet "...known as Department V, the successor to the KGB..."
- Entity "KGB": snippet "...Department V, the successor to the KGB's elite..."
- etc.

Result: Same source paragraph → 11 separate evidence rows
```

### Why Co-occurrence Analysis Fails

**Problem**: The evidence snippets are often truncated/reworded versions of the original paragraph, so exact text matching fails.

**Current co-occurrence logic**:
```sql
GROUP BY e.snippet_text, e.report_id
HAVING COUNT(em.entity_id) > 1
```

This only finds co-occurrence when **snippet_text is identical**.

But the LLM created slightly different snippets for each entity from the same source paragraph:
- "Bellingcat and The Insider had previously identified..."
- "...senior officer from FSB's elite Spetznaz force..."
- "...Department V, the successor to the KGB..."

**These don't match** even though they're from the same paragraph!

---

## Evidence of Entity-Dense Source Material

**Sample from actual reports**:

Line 9 of report3:
- Entities: SBU, Valeriy Shaytanov, Russia, Ukraine, FSB, Igor Egorov, KGB, Crimea (8 entities in one sentence)

Line 11:
- Entities: SBU, Shaytanov, Egorov, FSB, Adam Osmayev, Chechen, Kyiv, Ukraine, Russian (9 entities)

Line 17:
- Entities: Bellingcat, The Insider, Igor Egorov, FSB, Department V, KGB, Vympel, GRU, Moscow, Rostov, Simferopol, Krasnodar, Donbass (13+ entities)

**Conclusion**: Source material is VERY entity-dense. Sparsity is an artifact of extraction methodology.

---

## Proposed Solution: Synthetic Test Document

**Create a test document specifically designed for co-occurrence testing**:

```markdown
# Test Investigation Report

## Operation Overview

The FSB and GRU coordinated Operation Nightfall in Eastern Ukraine. Colonel Igor
Petrov (FSB) and Major Sergei Ivanov (GRU) led the operation from Moscow, with
support from the 53rd Brigade based in Kursk.

## Key Personnel

FSB operatives included Colonel Igor Petrov, Lieutenant Oleg Markov, and Agent
Anna Volkova. They worked alongside GRU officers Major Sergei Ivanov and
Captain Dmitri Sokolov from Unit 29155.

## Timeline

On July 15, 2014, Colonel Petrov and Major Ivanov traveled from Moscow to Rostov.
From Rostov, they coordinated with the 53rd Brigade and local commanders in Donetsk.
The operation involved the Buk missile system, which was transported from Kursk to
the Ukrainian border.

## Investigation

Bellingcat and The Insider investigated this operation. Eliot Higgins led the
Bellingcat team, while Christo Grozev led The Insider investigation. They used
social media evidence from Twitter and VKontakte to track the Buk convoy.
```

**Expected co-occurrence patterns**:
- FSB + GRU: 3+ times
- Igor Petrov + Sergei Ivanov: 3+ times
- Moscow + Rostov: 2+ times
- Bellingcat + The Insider: 2+ times
- Buk + 53rd Brigade: 2+ times

---

## Next Steps

### Option A: Fix Extraction Methodology

**Change**: Extract at paragraph level, not entity level

**New approach**:
1. Divide report into paragraphs
2. For each paragraph, extract ALL entities mentioned
3. Store paragraph as single evidence snippet
4. Link all entities to that evidence snippet

**Benefit**: Natural co-occurrence from source text preserved

**Cost**: Requires re-extraction of all 3 reports (~5 minutes)

---

### Option B: Test with Synthetic Document

**Create**: `test_data/synthetic_cooccurrence_test.md`
- 5-10 paragraphs
- Each paragraph mentions 5-8 entities
- Entities deliberately repeated across paragraphs
- Designed to test co-occurrence infrastructure

**Extract using current methodology**

**Validate**: Does co-occurrence analysis work when entities genuinely share snippets?

**Benefit**: Tests infrastructure without changing extraction logic

**Cost**: Doesn't fix the underlying issue, just validates the system works in principle

---

### Option C: Accept Limitation & Document

**Accept**: Current approach has sparse co-occurrence
**Document**: Known limitation in phase3_results.md
**Recommendation**: For production, use paragraph-level extraction

**Benefit**: No additional work required
**Cost**: Phase 3 validation incomplete

---

## Recommendation

**Do Option B (synthetic test) FIRST**, then decide:

1. Create synthetic test document (10 min)
2. Run extraction on synthetic doc (2 min)
3. Run co-occurrence analysis (1 min)
4. Test queries (2 min)

**Total time**: 15 minutes

**If synthetic test shows high co-occurrence**:
- Proves infrastructure works
- Identifies extraction methodology as bottleneck
- Can document as "known limitation, fixable via paragraph-level extraction"

**If synthetic test STILL shows low co-occurrence**:
- Identifies deeper infrastructure issue
- Needs investigation/fix

---

## Decision

**Recommendation**: Create synthetic test document to validate co-occurrence infrastructure works correctly when entities genuinely share snippets.

This will prove whether the issue is:
- ✅ Extraction methodology (fixable, documented limitation)
- ❌ Co-occurrence infrastructure (needs debugging)

**Time investment**: 15 minutes
**Value**: Validates Phase 3 infrastructure works in principle
