# Tag Normalization Plan

## Overview
Normalize 1,709 unique tags → ~300-400 canonical tags using gpt-5-mini with structured output.

## Current State
- **Total articles**: 367 (all tagged)
- **Total tag instances**: 3,556
- **Unique tags**: 1,709
- **Tags with 2+ mentions**: 395
- **Tags with 1 mention**: 1,314

---

## Phase 1: Normalize High-Frequency Tags (395 tags with 2+ mentions)

### Step 1.1: Process in Batches
**Action**: Feed 395 tags to gpt-5-mini in batches of 20
**Duration**: ~20-30 minutes (20 batches × ~1 min each)

**Input**: Tags with counts from `tags_2plus_mentions.txt`
**Output**: `tag_normalization_2plus.json`

**What gpt-5-mini does for each tag**:
1. **Normalize format** per TAG_FORMATTING_STANDARDS.md
   - Fix capitalization (proper nouns vs common concepts)
   - Replace hyphens with spaces
   - Add/remove periods (U.S. vs FBI)
   - Singularize
   - Remove "The" prefix
   - Expand parenthetical abbreviations

2. **Assign primary category** (1 of 10):
   - National Security & Intelligence
   - Military & Defense
   - Civil Liberties & Surveillance
   - U.S. Politics & Government
   - Foreign Policy & Conflicts
   - Immigration & Border Security
   - Law Enforcement & Justice
   - Media & Journalism
   - Technology & Corporate Power
   - Healthcare

3. **Identify entity type**:
   - person
   - place
   - organization
   - event
   - concept
   - none

4. **Rate taxonomy fit**:
   - **good**: Fits cleanly into a category
   - **fair**: Borderline, overlaps categories
   - **poor**: Doesn't fit well, taxonomy needs expansion

5. **Add notes**: If fair/poor, explain why and suggest improvements

**Example output**:
```json
{
  "original": "national-security",
  "canonical_form": "national security",
  "primary_category": "National Security & Intelligence",
  "entity_type": "concept",
  "taxonomy_fit": "good",
  "notes": ""
}
```

### Step 1.2: Review Results
**Action**: Examine `taxonomy_issues.json` for poor/fair fits
**Output**: List of tags that don't fit current taxonomy well

**Likely findings**:
- "news roundup" - meta tag, doesn't fit topic categories
- Healthcare-specific tags might need subcategories
- Some media/journalism tags overlap with civil liberties

### Step 1.3: Generate Canonical Mapping
**Action**: Create simple lookup dictionary
**Output**: `canonical_mapping_2plus.json`

```json
{
  "national-security": "national security",
  "National security": "national security",
  "national security": "national security",
  "USA": "United States",
  "US": "United States",
  "DHS": "Department of Homeland Security",
  "Department of Homeland Security (DHS)": "Department of Homeland Security"
}
```

**Expected consolidation**:
- 395 tags → ~150-200 canonical tags (40-50% reduction)

---

## Phase 2: Aggregate Single-Use Tags (1,314 tags)

### Step 2.1: Identify Aggregation Candidates
**Action**: Use gpt-5-mini to analyze single-use tags

**For each single-use tag, gpt-5-mini determines**:
1. **Keep as-is**: Important specific concept worth navigating to
   - Example: "Civilian control of the military"
   - Example: "Heritage Foundation" (notable org)

2. **Aggregate to broader tag**: Roll up to existing tag
   - "Gaza (Rafah)" → "Gaza" (already exists, 17 uses)
   - "Congress (U.S.)" → "Congress" (already exists, 32 uses)
   - "526th Intelligence Squadron" → "military units" (new abstract tag)
   - "Online radicalization" → "radicalization" (broader)
   - "antisemitism policy" → "antisemitism" (already exists, 4 uses)

3. **Drop**: Too specific/ephemeral for navigation
   - Obscure military unit numbers
   - One-off operation names with no recurring relevance
   - Hyper-technical jargon

**Output**: `single_tag_aggregation.json`
```json
{
  "original": "Congress (U.S.)",
  "action": "aggregate",
  "aggregate_to": "Congress",
  "reason": "Parenthetical variant of existing tag"
}
```

### Step 2.2: Apply Aggregation
**Action**: Update the 1,314 singles based on gpt-5-mini recommendations

**Expected results**:
- **Keep**: ~100-150 important specific tags
- **Aggregate**: ~800-900 roll up to broader tags
- **Drop**: ~300-400 too specific/not useful

**After aggregation**:
- Total canonical tags: ~250-350 (down from 1,709)

---

## Phase 3: Apply Normalization to Tagged Articles

### Step 3.1: Load Canonical Mapping
**Input**: `canonical_mapping_complete.json` (Phase 1 + Phase 2 combined)

### Step 3.2: Update All 367 Tagged Files
**Action**: For each `*_tagged.json` file:
1. Load article
2. For each tag in `article['tagging']['tags']`:
   - Look up canonical form in mapping
   - Replace with canonical form
3. Save updated article

**Script**: `apply_normalization_to_articles.py`

### Step 3.3: Verification
**Action**: Re-count unique tags after normalization
**Expected**: ~250-350 unique canonical tags (down from 1,709)

---

## Phase 4: Assign Entity Types & Categories

### Step 4.1: Add Metadata to Articles
**Action**: For each canonical tag, add:
```json
{
  "tagging": {
    "tags": ["national security", "FBI", "United States"],
    "tag_metadata": {
      "national security": {
        "primary_category": "National Security & Intelligence",
        "entity_type": "concept"
      },
      "FBI": {
        "primary_category": "Law Enforcement & Justice",
        "entity_type": "organization"
      },
      "United States": {
        "primary_category": "U.S. Politics & Government",
        "entity_type": "place"
      }
    }
  }
}
```

### Step 4.2: Generate Tag Index
**Output**: `tag_index.json` - Complete list of all canonical tags with:
- Tag name
- Primary category
- Entity type
- Count (how many articles)
- Article IDs (which articles have this tag)

```json
{
  "national security": {
    "canonical_form": "national security",
    "primary_category": "National Security & Intelligence",
    "entity_type": "concept",
    "count": 125,
    "articles": ["2024_Article1.json", "2025_Article2.json", ...]
  }
}
```

---

## Phase 5: Review Taxonomy Gaps

### Step 5.1: Analyze Poor/Fair Fits
**Input**: `taxonomy_issues.json` from Phase 1

**Action**: Review tags that don't fit well
- Do we need new categories?
- Should we split existing categories?
- Are some tags cross-cutting (belong to multiple categories)?

### Step 5.2: Refine Taxonomy
**Potential additions**:
- Add "Disinformation & Influence Operations" as 11th category?
- Split "Media & Journalism" into two?
- Add subcategories within existing categories?

### Step 5.3: Re-categorize Problem Tags
**Action**: Manually or semi-automatically reassign tags flagged as poor fit

---

## Implementation Scripts

### Script 1: `normalize_tags_2plus.py` ✅ (already created, needs schema fix)
- Processes 395 tags with 2+ mentions
- Outputs normalization + categorization
- Flags taxonomy issues

### Script 2: `aggregate_single_tags.py` (TO CREATE)
- Processes 1,314 single-use tags
- Suggests keep/aggregate/drop
- Generates aggregation mapping

### Script 3: `apply_normalization_to_articles.py` (TO CREATE)
- Applies canonical mapping to all 367 articles
- Updates `*_tagged.json` files in place
- Adds tag metadata

### Script 4: `generate_tag_index.py` (TO CREATE)
- Builds complete tag index for website
- Counts articles per tag
- Cross-references tags to articles

---

## Success Metrics

### Before Normalization:
- 1,709 unique tags
- Many duplicates (national-security, National security, national security)
- No categorization
- No entity typing
- Hard to navigate

### After Normalization:
- ~250-350 canonical tags (85% reduction)
- Zero duplicates
- All tags categorized (10 topic categories)
- All tags typed (person/place/org/event/concept)
- Clear taxonomy fit ratings
- Website-ready navigation structure

---

## Timeline Estimate

- **Phase 1** (395 tags): 20-30 minutes processing + 30 min review = 1 hour
- **Phase 2** (1,314 tags): 60-90 minutes processing + 1 hour review = 2.5 hours
- **Phase 3** (apply to articles): 5 minutes
- **Phase 4** (generate index): 2 minutes
- **Phase 5** (review/refine): 1-2 hours

**Total**: ~5-6 hours (mostly LLM processing time, can run unattended)

---

## Next Immediate Action

Run Phase 1 with the fixed schema:
```bash
python3 /home/brian/sam_gov/normalize_tags_2plus.py
```

This will produce the first set of normalized tags and identify taxonomy gaps before proceeding to the full 1,709 tags.
