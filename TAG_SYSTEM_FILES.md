# Tag System Files Reference

This document describes all files related to the tag normalization and taxonomy system for Ken Klippenstein and Bills Blackbox articles.

## Active Files Location

**All active tag system files are in: `experiments/tag_management/`**

## Active Files

### Core Data Files
These are the essential outputs of the tag system that should be kept and maintained:

- **`tag_taxonomy_complete.json`** (104K)
  - Final taxonomy with 440 tags across 20 categories
  - Each tag has: category, entity_type, taxonomy_fit, notes
  - Metadata: total_tags, good_fit, fair_fit, poor_fit counts
  - **Status**: CURRENT - This is the master taxonomy file

- **`tag_index_full.json`** (980K)
  - Complete index mapping tags to articles
  - Each tag entry includes: tag name, count, list of articles
  - Article info: title, url, year, tags
  - **Status**: CURRENT - Used by taxonomy_browse.html

- **`tag_normalization_2plus.json`** (112K)
  - Normalization mappings for tags with 2+ mentions
  - Maps original tag → canonical form
  - **Status**: CURRENT - Used for ongoing normalization

- **`canonical_mapping_2plus.json`** (112K)
  - Canonical tag mappings from Phase 2
  - Maps variations to standard forms
  - **Status**: CURRENT - Reference for normalization

- **`taxonomy_browse.html`** (882K)
  - Interactive web interface for browsing the taxonomy
  - Shows 440 tags sorted by count (high to low)
  - Click tags to see articles
  - **Status**: CURRENT - Main user interface

### Python Scripts

#### Generation Scripts (Keep - Core Functionality)
- **`generate_taxonomy_html.py`** (20K)
  - Generates taxonomy_browse.html from JSON data
  - Combines tag_taxonomy_complete.json + tag_index_full.json
  - **Usage**: `python3 generate_taxonomy_html.py`

- **`generate_tag_index.py`** (8.3K)
  - Creates tag_index_full.json from normalized articles
  - Maps tags → articles with metadata
  - **Usage**: `python3 generate_tag_index.py`

#### Phase Scripts (Archive - Historical Reference Only)
These were used for the multi-phase normalization process but are no longer needed for day-to-day operations:

- **`normalize_and_categorize_tags.py`** (9.4K)
  - Phase 1: Normalized and categorized high-frequency tags (2+ mentions)
  - Used gpt-5-mini for initial taxonomy creation
  - **Status**: HISTORICAL - Phase 1 complete

- **`aggregate_single_tags.py`** (8.7K)
  - Phase 2: Aggregated single-use tags into canonical forms
  - Created keep/aggregate/drop decisions
  - **Status**: HISTORICAL - Phase 2 complete

- **`apply_normalization_to_articles.py`** (6.9K)
  - Phase 3: Applied normalization to all articles
  - Updated article JSON files with canonical tags
  - **Status**: HISTORICAL - Phase 3 complete

- **`enforce_drop_decisions.py`** (5.0K)
  - Phase 3B: Removed 140 tags marked "drop" in Phase 2
  - Cleaned articles of dropped tags
  - **Status**: HISTORICAL - Phase 3B complete

- **`categorize_remaining_tags.py`** (12K)
  - Phase 5: Categorized 492 uncategorized tags
  - Fixed duplicate tag issue with "(X mentions)" suffix
  - **Status**: HISTORICAL - Phase 5 complete

- **`categorize_missing_52.py`** (6.2K)
  - Phase 5 cleanup: Removed 52 duplicate tags
  - Fixed bug where tags got "(X mentions)" appended
  - **Status**: HISTORICAL - Cleanup complete

#### Article Tagging Scripts (Keep - May Be Reused)
- **`batch_tag_articles.py`** (7.7K)
  - Batch tags articles using gpt-5-mini
  - Used for Ken Klippenstein articles
  - **Status**: REUSABLE - May be used for new articles

- **`unified_batch_tag_articles.py`** (9.1K)
  - Unified tagging script for multiple sources
  - Used for Bills Blackbox articles
  - **Status**: REUSABLE - May be used for new articles

- **`normalize_tags_2plus.py`** (8.2K)
  - Normalizes tags with 2+ mentions
  - Creates canonical mappings
  - **Status**: REUSABLE - May be used for new data

#### Test Scripts (Keep - Useful for Validation)
- **`test_article_tagging.py`** (5.8K)
  - Tests article tagging functionality
  - **Status**: ACTIVE - Useful for testing

- **`test_tags_5.json`** (250 bytes)
  - Test data for tagging
  - **Status**: ACTIVE - Test fixture

## Archived Files

### Location: `archive/tag_system/`

The following files have been moved to organized archive directories:

#### `intermediate_data/`
Files created during the normalization process but no longer needed:
- `all_tags_with_counts.json` (108K) - Initial tag frequency analysis
- `all_tags_with_counts.txt` (45K) - Human-readable tag counts
- `tags_2plus_mentions.txt` (9.3K) - List of tags with 2+ mentions
- `single_tag_aggregation.json` (308K) - Phase 2 single-tag analysis
- `aggregation_mapping.json` (32K) - Phase 2 aggregation decisions
- `kept_single_tags.json` (11K) - Single tags marked "keep" in Phase 2

#### `phase_outputs/`
Intermediate outputs from each phase:
- `tag_index_by_category.json` (94K) - Early category-organized index
- `tag_taxonomy_phase5.json` (124K) - Pre-cleanup taxonomy (before removing single-mention tags)
- `taxonomy_issues.json` (33K) - Tags flagged as poor fit (all resolved)
- `normalized_tag_frequency.json` (51K) - Tag frequencies after normalization
- `normalized_tag_frequency.txt` (20K) - Human-readable frequencies
- `taxonomy_full_report.txt` (82K) - Detailed taxonomy analysis report
- `tag_index_preview.html` (51K) - Early HTML preview (replaced by taxonomy_browse.html)

#### `backups/`
Backup copies of files before modifications:
- `tag_normalization_2plus_BACKUP.json` (112K)
- `canonical_mapping_2plus_BACKUP.json` (112K)
- `taxonomy_issues_BACKUP.json` (31K)

#### `logs/`
Processing logs from various phases:
- `normalize_tags_2plus.log` (0 bytes) - Phase 2 normalization log
- `phase2_aggregation.log` (8.1K) - Phase 2 aggregation decisions log

## Tag System Workflow

### Current State (All Phases Complete)
1. ✅ **Phase 1**: Normalized 395 high-frequency tags with taxonomy
2. ✅ **Phase 2**: Aggregated 1,314 single-use tags (493 keep, 680 aggregate, 141 drop)
3. ✅ **Phase 3**: Applied normalization to 367 articles
4. ✅ **Phase 3B**: Enforced drop decisions (removed 140 tags)
5. ✅ **Phase 4**: Generated tag index
6. ✅ **Phase 5**: Categorized remaining 492 tags, fixed duplicates, removed single-mention tags

### Final Statistics
- **440 tags** in taxonomy (all with 2+ mentions)
- **20 categories** (including Education/Academia, Entertainment/Culture)
- **81.4% good fit** (359 tags)
- **18.6% fair fit** (81 tags)
- **0% poor fit** (0 tags)
- **367 articles** (316 Ken Klippenstein + 51 Bills Blackbox)

### To Add New Articles
1. Tag articles using `experiments/tag_management/batch_tag_articles.py` or `unified_batch_tag_articles.py`
2. Run `python3 experiments/tag_management/generate_tag_index.py` to update tag_index_full.json
3. Run `python3 experiments/tag_management/generate_taxonomy_html.py` to update taxonomy_browse.html
4. Review new tags - categorize any uncategorized tags manually or via gpt-5-mini

### To View the Taxonomy
Open `experiments/tag_management/taxonomy_browse.html` in your browser

## Related Documentation

### Phase Documentation (Historical Reference)
- `PHASE1_NORMALIZATION_SUMMARY.md` - Phase 1 details
- `PHASE1_COMPLETE_SUMMARY.md` - Phase 1 completion report
- `PHASE2_COMPLETE_SUMMARY.md` - Phase 2 completion report

### Planning Documentation (Historical Reference)
- `TAG_NORMALIZATION_PLAN.md` - Original normalization plan
- `TAG_NORMALIZATION_WORKFLOW.md` - Workflow documentation
- `PROPOSED_TAG_TAXONOMY.md` - Initial taxonomy proposal
- `TAG_FORMATTING_STANDARDS.md` - Tag formatting guidelines

These documentation files can also be archived if desired, as the system is now complete and stable.

## Cleanup Summary

**Files Moved to Archive**: 19 files
**Disk Space in Archive**: ~1.3 MB
**Active Files Remaining**: 13 core files + 9 scripts

The tag system is now clean and organized with only essential active files in the root directory.
