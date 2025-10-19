# Keyword Database Quick Start Guide

## What You Have Now

✅ **1,216 keywords** extracted from your 1,101 articles
✅ **24 investigative themes** (National Security, Domestic Terrorism, FOIA, etc.)
✅ **40 ready-to-use Boolean queries**
✅ **697 acronyms** (FBI, CIA, DHS, NVE, DVE, etc.)
✅ **Synonym mappings** for common variations

## Files Created

1. **`keyword_database.json`** - Complete structured keyword database
2. **`keyword_database_summary.txt`** - Human-readable summary
3. **`keyword_extraction_raw.json`** - Raw extraction data (for reference)
4. **`BOOLEAN_SEARCH_SYSTEM_ULTRATHINKING.md`** - Complete system design document

---

## How to Use the Keyword Database

### Example 1: Monitoring "Nihilistic Violent Extremism" (Your Example)

**Step 1: Find related keywords in database**

```bash
cat keyword_database.json | jq '.themes["Terrorism & Counterterrorism"]'
```

**You'll find**:
- Primary terms: "domestic terrorism" (213 mentions)
- Related: "violent extremists", "domestic violent extremists"
- Acronyms: ISIS
- Multi-word phrases: "violent extremist", "war on terrorism"

**Step 2: Build Boolean query**

From the database, example queries are:

```
# Government Documents
site:(.gov OR .mil) ("ISIS") AND ("report" OR "assessment" OR "memo")

# News Coverage
("domestic terrorism" OR "violent extremists") AND (news OR investigation OR report)
```

**Step 3: Expand for NVE specifically**

Since "nihilistic violent extremism" appears in your corpus, add it:

```
("nihilistic violent extremism" OR "NVE" OR "domestic terrorism" OR "violent extremists")
AND (FBI OR DHS OR "threat assessment")
```

**Step 4: Run search**

Use this query on:
- Google: `site:(fbi.gov OR dhs.gov) "nihilistic violent extremism" OR "NVE"`
- DVIDS: Already integrated in your code
- NewsAPI: `("nihilistic violent extremism" OR NVE) AND (FBI OR DHS)`

---

### Example 2: FOIA Document Releases

**Keywords from database**:
- Theme: "Government Oversight & Accountability"
- Related: "FOIA / transparency", "Whistleblowers", "Freedom of Information Act", "classified documents"

**Boolean Query**:
```
("FOIA" OR "Freedom of Information Act")
AND ("document release" OR "declassified" OR "unredacted")
AND (FBI OR CIA OR DHS OR Pentagon)
```

**Sources to monitor**:
- FBI Vault: `site:vault.fbi.gov`
- CIA FOIA: `site:cia.gov/readingroom`
- Property of the People: `site:propertyofthepeople.org`

---

### Example 3: Critical Infrastructure Threats

**Keywords from database**:
- From "National Security" theme: "critical infrastructure", "power grid"
- From "Domestic Terrorism": "violent extremists", "domestic terrorism"

**Boolean Query**:
```
("critical infrastructure" OR "power grid" OR "electrical grid")
NEAR/5 ("attack" OR "threat" OR "vulnerability")
AND ("domestic terrorism" OR "extremism" OR NVE)
```

This uses **proximity operators** (NEAR/5) to find phrases where the terms appear within 5 words of each other.

---

## Top Investigative Themes & Keywords

### 1. National Security & Intelligence (102 keywords)

**Top Phrases**:
- "national security" (1,686 mentions)
- "intelligence community" (363 mentions)
- "national security state" (357 mentions)

**Key Acronyms**: NSA, CIA, DHS

**Boolean Query**:
```
site:(.gov OR .mil) ("NSA" OR "CIA" OR "DHS")
AND ("report" OR "assessment" OR "memo")
```

### 2. Law Enforcement & Justice (37 keywords)

**Top Phrases**:
- "law enforcement" (546 mentions)
- "fbi director" (171 mentions)
- "justice department" (159 mentions)

**Boolean Query**:
```
site:(.gov OR .mil) ("FBI" OR "DOJ")
AND ("report" OR "assessment" OR "memo")
```

### 3. Terrorism & Counterterrorism (20 keywords)

**Top Phrases**:
- "domestic terrorism" (213 mentions)
- "violent extremists" (126 mentions)
- "domestic violent extremists" (63 mentions)

**Boolean Query**:
```
("domestic terrorism" OR "violent extremists")
AND (news OR investigation OR report)
```

### 4. Military & Defense (81 keywords)

**Top Phrases**:
- "secretary of defense" (189 mentions)
- "pentagon" (162 mentions)
- "defense department" (132 mentions)

**Boolean Query**:
```
site:(.mil OR .gov) "Department of Defense"
AND ("contract" OR "award" OR "procurement")
```

---

## Using Keywords with Your Existing Code

### Integration Point 1: SAM.gov Search

Your existing `sam_search.py` can use these keywords:

```python
import json

# Load keyword database
with open('keyword_database.json', 'r') as f:
    keywords_db = json.load(f)

# Get keywords for a theme
theme = "National Security & Intelligence"
theme_data = keywords_db['themes'][theme]

# Build search terms
search_terms = []
search_terms.extend(theme_data['acronyms'])  # FBI, CIA, NSA
search_terms.extend([p['phrase'] for p in theme_data['multi_word_phrases'][:5]])

# Search SAM.gov for each term
for term in search_terms:
    results = search_sam_gov(term)
    # Process results...
```

### Integration Point 2: DVIDS Search

```python
# Get military-related keywords
military_keywords = keywords_db['themes']['Military & Defense']

# Search DVIDS
for phrase in military_keywords['multi_word_phrases'][:10]:
    search_query = phrase['phrase']
    results = search_dvids(search_query)
```

### Integration Point 3: Google News API

```python
# Get terrorism keywords
terrorism_keywords = keywords_db['themes']['Terrorism & Counterterrorism']

# Build Boolean query
or_terms = ' OR '.join([f'"{p["phrase"]}"'
                        for p in terrorism_keywords['multi_word_phrases'][:5]])
query = f'({or_terms}) AND (FBI OR DHS)'

# Search Google News
results = newsapi.get_everything(q=query, language='en')
```

---

## Advanced: Synonym Expansion

The database includes synonym mappings for common acronyms:

```json
{
  "FBI": ["Federal Bureau of Investigation", "FBI", "Bureau"],
  "CIA": ["Central Intelligence Agency", "CIA", "Agency"],
  "FOIA": ["Freedom of Information Act", "FOIA"],
  "ISIS": ["Islamic State", "ISIS", "ISIL", "Daesh"]
}
```

**Use this to expand queries**:

```python
def expand_query(term, synonyms_dict):
    """Expand a term with all its synonyms"""
    if term in synonyms_dict:
        variations = synonyms_dict[term]
        return '(' + ' OR '.join([f'"{v}"' for v in variations]) + ')'
    return f'"{term}"'

# Example
query = expand_query("FBI", keywords_db['synonyms'])
# Returns: '("Federal Bureau of Investigation" OR "FBI" OR "Bureau")'
```

---

## Source-Specific Query Syntax

Different sources support different Boolean operators:

### Google / Google News
```
# Basic
("domestic terrorism" OR "violent extremism") AND FBI

# With site filter
site:gov.uk "domestic terrorism"

# Exclude terms
"domestic terrorism" -Wikipedia

# Proximity (AROUND)
"domestic terrorism" AROUND(10) "threat assessment"
```

### SAM.gov
```
# Basic AND/OR
(intelligence OR counterterrorism) AND "threat assessment"

# Exact phrase
"operational security"
```

### DVIDS (Military)
```
# Full Boolean with proximity
("domestic terrorism" OR extremism) NEAR/5 (assessment OR report)

# Wildcards
terror* extremis*

# Field-specific
title:(domestic terrorism)
```

### Academic Databases (ProQuest, JSTOR)
```
# Title/Abstract search
TI,AB(("domestic terrorism" OR "violent extremism") AND "United States")

# Date range
("domestic terrorism") AND yr(2020-2025)
```

---

## Next Steps

### Option A: Manual Use (Start Today)
1. Open `keyword_database_summary.txt`
2. Pick a theme relevant to your current investigation
3. Copy a Boolean query
4. Paste into Google / your search source
5. Review results

### Option B: Build Automated Monitor (1-2 weeks)
1. Create search script that loads `keyword_database.json`
2. Run queries against multiple sources (SAM.gov, DVIDS, Google News)
3. Deduplicate and score results
4. Send daily email digest
5. Store in SQLite database

**I can build Option B for you if you want!**

---

## Tips for Effective Boolean Searches

### 1. Start Broad, Then Narrow
```
# Start with
"domestic terrorism"

# If too many results, add context
"domestic terrorism" AND (FBI OR "threat assessment")

# If still too broad, add more specificity
"domestic terrorism" AND FBI AND ("fusion center" OR STIC)
```

### 2. Use Proximity Operators
Instead of:
```
"critical infrastructure" AND "attack"
```

Use:
```
"critical infrastructure" NEAR/5 "attack"
```

This finds terms within 5 words of each other, reducing false positives.

### 3. Combine with Site Filters
```
site:(fbi.gov OR dhs.gov OR justice.gov) "domestic terrorism"
```

This limits results to government sources only.

### 4. Use Wildcards for Variations
```
terror* # matches: terrorism, terrorist, terrorists
extrem* # matches: extremism, extremist, extremists, extreme
```

### 5. Exclude Noise
```
"domestic terrorism" -Wikipedia -definition -"what is"
```

---

## Example: Weekly Monitoring Routine

**Monday - Government Documents**
```
site:(.gov OR .mil)
("FOIA" OR "classified documents" OR "declassified")
AND ("FBI" OR "CIA" OR "NSA")
```
Sources: Google, FBI Vault, CIA FOIA

**Tuesday - Domestic Extremism**
```
("domestic terrorism" OR "violent extremism" OR "NVE")
AND ("threat assessment" OR "intelligence report")
```
Sources: Google News, DHS, fusion centers

**Wednesday - Critical Infrastructure**
```
("critical infrastructure" OR "power grid")
NEAR/5 ("attack" OR "threat" OR "vulnerability")
```
Sources: DVIDS, DHS, NewsAPI

**Thursday - FOIA Releases**
```
"FOIA release" OR "newly declassified" OR "document dump"
```
Sources: Property of the People, MuckRock, news outlets

**Friday - Catch-All**
```
("intelligence community" OR "national security")
AND (investigation OR scandal OR whistleblower)
```
Sources: ProPublica, Intercept, Ken Klippenstein, Bills Blackbox

---

## Questions?

The keyword database is **ready to use right now**. You can:

1. **Start manually** - Copy queries from `keyword_database_summary.txt` and search
2. **Build automation** - Use `keyword_database.json` programmatically
3. **Refine keywords** - Add your own terms to the JSON file
4. **Request features** - Ask me to build the monitoring system!

**Your "nihilistic violent extremism" example is ready to monitor - just use the Terrorism & Counterterrorism queries and add "NVE" specifically.**
