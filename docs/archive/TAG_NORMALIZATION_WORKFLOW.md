# Tag Normalization Workflow - Complete Pipeline

## Overview

Comprehensive tag normalization system for 367 articles across Klippenstein and Bills Blackbox collections.

**Goal:** Transform 1,709 unique tags → ~250-350 canonical tags with proper formatting and taxonomy categorization.

---

## Phases

### ✅ Phase 1: Normalize High-Frequency Tags (COMPLETE)
**Script:** `normalize_tags_2plus.py`

**Input:**
- 395 tags appearing 2+ times
- 10-category taxonomy system
- Formatting standards (capitalization, spaces, periods)

**Process:**
- gpt-5-mini with structured JSON output
- 20 batches of 20 tags each
- Each tag assigned: canonical form, category, entity type, taxonomy fit rating

**Output:**
- `tag_normalization_2plus.json` - Full results
- `canonical_mapping_2plus.json` - Original → canonical lookup
- `taxonomy_issues.json` - Poor/fair fit tags
- `PHASE1_NORMALIZATION_SUMMARY.md` - Analysis

**Results:**
- ✅ Good fit: 301 tags (76%)
- ⚠️ Fair fit: 89 tags (23%) - cross-category tags
- ❌ Poor fit: 6 tags (2%) - taxonomy gaps identified

---

### 🔄 Phase 2: Aggregate Single-Use Tags (IN PROGRESS)
**Script:** `aggregate_single_tags.py`

**Input:**
- 1,314 tags appearing exactly 1 time
- Canonical tags from Phase 1 for reference

**Process:**
- gpt-5-mini analyzes each tag
- Decision: keep, aggregate to broader tag, or drop
- 44 batches of 30 tags each
- ~1-2 hours processing time

**Output:**
- `single_tag_aggregation.json` - All decisions with reasons
- `aggregation_mapping.json` - Original → aggregated tag mapping
- `kept_single_tags.json` - List of preserved single-use tags

**Expected Results:**
- Keep: ~100-150 important specific tags
- Aggregate: ~800-900 tags rolled into broader concepts
- Drop: ~300-400 too specific/ephemeral tags

**Status:** Currently running (batch 3/44 as of last check)

---

### ⏳ Phase 3: Apply Normalization to Articles (READY)
**Script:** `apply_normalization_to_articles.py`

**Input:**
- 367 tagged articles (*_tagged.json files)
- Canonical mappings from Phase 1 and Phase 2

**Process:**
- For each article, normalize all tags using combined mapping
- Remove duplicate tags after normalization
- Preserve original tags for reference

**Output:**
- 367 normalized article files (*_normalized.json)
- `normalized_tag_frequency.json` - Tag counts after normalization
- `normalized_tag_frequency.txt` - Human-readable version

**Expected Results:**
- Tag consolidation: ~40-50% reduction in unique tags per article
- All tags in canonical form with proper capitalization

**Status:** Script ready, waiting for Phase 2 completion

---

### ⏳ Phase 4: Generate Tag Index for Website (READY)
**Script:** `generate_tag_index.py`

**Input:**
- 367 normalized articles
- Taxonomy categories from Phase 1

**Process:**
- Collect all tags from normalized articles
- Build tag → articles mapping
- Organize by taxonomy category
- Generate JSON and HTML outputs

**Output:**
- `tag_index_full.json` - Complete index with article lists
- `tag_index_by_category.json` - Tags organized by 10 categories
- `tag_index_preview.html` - Visual preview for browser

**Provides:**
- Website navigation structure
- Tag clouds by category
- Article discovery by tag

**Status:** Script ready, waiting for Phase 3 completion

---

## Execution Sequence

```bash
# Phase 1 (COMPLETE)
python3 normalize_tags_2plus.py
# Time: ~17 minutes
# Output: Normalized 395 high-frequency tags

# Phase 2 (IN PROGRESS)
python3 aggregate_single_tags.py
# Time: ~1-2 hours
# Output: Keep/aggregate/drop decisions for 1,314 single-use tags

# Phase 3 (PENDING - run after Phase 2)
python3 apply_normalization_to_articles.py
# Time: ~1-2 minutes
# Output: 367 normalized article files

# Phase 4 (PENDING - run after Phase 3)
python3 generate_tag_index.py
# Time: ~30 seconds
# Output: Tag index for website integration
```

---

## File Structure

### Source Files
```
klippenstein_articles/
  ├── article1.json              # Original extracted text
  ├── article1_tagged.json       # GPT-tagged version
  └── article1_normalized.json   # Normalized tags (Phase 3)

bills_blackbox/
  ├── article1.json
  ├── article1_tagged.json
  └── article1_normalized.json
```

### Normalization Outputs
```
tag_normalization_2plus.json      # Phase 1: Full normalization results
canonical_mapping_2plus.json      # Phase 1: Simple lookup
taxonomy_issues.json              # Phase 1: Poor/fair fits
single_tag_aggregation.json       # Phase 2: Keep/aggregate/drop
aggregation_mapping.json          # Phase 2: Aggregation lookup
kept_single_tags.json             # Phase 2: Preserved tags
normalized_tag_frequency.json     # Phase 3: Final tag counts
tag_index_full.json               # Phase 4: Complete index
tag_index_by_category.json        # Phase 4: Organized by category
tag_index_preview.html            # Phase 4: Browser preview
```

### Documentation
```
TAG_FORMATTING_STANDARDS.md       # Capitalization and formatting rules
PROPOSED_TAG_TAXONOMY.md          # 10-category system
TAG_NORMALIZATION_PLAN.md         # Original 5-phase plan
PHASE1_NORMALIZATION_SUMMARY.md   # Phase 1 results analysis
TAG_NORMALIZATION_WORKFLOW.md     # This file
```

---

## Formatting Standards

### Capitalization
- **Common concepts:** all lowercase
  - Examples: `national security`, `surveillance`, `privacy`
- **Proper nouns:** Title Case
  - Examples: `United States`, `Donald Trump`, `FBI`
- **Mixed tags:** Capitalize only proper noun parts
  - Example: `anti Immigration and Customs Enforcement protest`

### Spacing and Punctuation
- **Spaces not hyphens:** `national security` (not `national-security`)
- **Periods in abbreviations:** `U.S.`, `U.K.`, `U.N.`
- **No periods in acronyms:** `FBI`, `CIA`, `NSA`, `DOJ`
- **Singular form preferred:** `protest` (not `protests`)
- **No "The" prefix:** `Pentagon` (not `The Pentagon`)

---

## Taxonomy Categories

1. **National Security & Intelligence**
2. **Military & Defense**
3. **Civil Liberties & Surveillance**
4. **Law Enforcement & Justice**
5. **Foreign Policy & Conflicts**
6. **Immigration & Border Security**
7. **Technology & Corporate Power**
8. **Media & Journalism**
9. **U.S. Politics & Government**
10. **Economic & Political Ideology**

---

## Entity Types

- **person** - Individuals (Donald Trump, Joe Biden)
- **place** - Geographic locations (United States, Iran, Los Angeles)
- **organization** - Agencies, companies (FBI, Pentagon, CIA)
- **event** - Specific occurrences (9/11, Super Bowl)
- **concept** - Abstract ideas (surveillance, civil liberties, privacy)
- **none** - Uncategorized

---

## Monitoring Phase 2 Progress

```bash
# Check current batch
tail -20 phase2_aggregation.log

# Check if running
ps aux | grep aggregate_single_tags.py

# Monitor continuously
watch -n 30 'tail -20 phase2_aggregation.log'
```

---

## Expected Timeline

| Phase | Duration | Status |
|-------|----------|--------|
| Phase 1 | ~17 min | ✅ Complete |
| Phase 2 | ~1-2 hrs | 🔄 In Progress (batch 3/44) |
| Phase 3 | ~1-2 min | ⏳ Ready |
| Phase 4 | ~30 sec | ⏳ Ready |

**Total:** ~1.5-2.5 hours from start to finish

---

## Next Steps After Completion

1. **Review Phase 2 results**
   - Analyze keep/aggregate/drop decisions
   - Verify aggregation mappings are sensible

2. **Run Phase 3**
   - Apply all normalizations to 367 articles
   - Check tag reduction statistics

3. **Run Phase 4**
   - Generate website tag index
   - Review HTML preview in browser

4. **Website Integration**
   - Use `tag_index_full.json` for tag pages
   - Use `tag_index_by_category.json` for navigation
   - Implement tag filtering and search

5. **Ongoing Maintenance**
   - When new articles are added, tag them with gpt-5-mini
   - Run normalization against existing canonical mapping
   - Periodically review and update taxonomy as needed

---

## Success Metrics

- ✅ Reduced tag count: 1,709 → ~250-350 (85% reduction)
- ✅ Consistent formatting: All tags follow capitalization rules
- ✅ Taxonomy coverage: 76%+ good fit, <25% fair fit
- ✅ Navigation readiness: Tags organized by category for website
- ✅ Duplicate elimination: Consolidate variants (USA → United States)

---

## Technical Details

**Model:** gpt-5-mini (OpenAI's newest model via litellm)
**API Method:** `litellm.responses()` with structured JSON output
**Schema Validation:** Strict JSON schema with `additionalProperties: False`
**Batch Processing:** Parallel processing where possible, sequential for dependencies
**Error Handling:** Graceful failure with continued processing on errors
