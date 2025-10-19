# Boolean Search System: Ultra-Thinking Analysis

## Executive Summary

This document provides a comprehensive analysis of two interconnected goals:
1. **Extracting relevant keywords** from your investigative journalism corpus (367 articles)
2. **Designing an automated Boolean search monitoring system** for investigative journalism

Your corpus contains national security/defense reporting from Ken Klippenstein (316 articles) and Bills Blackbox (51 articles), covering topics like domestic terrorism, intelligence agencies, defense policy, and government transparency.

---

## PART 1: KEYWORD EXTRACTION STRATEGY

### 1.1 Understanding the Keyword Landscape

From analyzing your corpus, I've identified **6 distinct keyword categories** that are valuable for Boolean searches:

#### Category 1: Domain-Specific Terminology & Jargon
**Examples from your corpus**:
- "Nihilistic violent extremism" / "NVE"
- "Domestic Violent Extremists" / "DVE"
- "Racially or Ethnically Motivated Violent Extremists" / "REMVE"
- "Accelerationism" / "Militant Accelerationism"
- "Transnational repression"
- "Critical infrastructure attacks"
- "Fusion centers"
- "Involuntary celibates" / "incels"

**Why these matter**: These are insider terms that won't appear in general news but ARE used in:
- Government documents
- Intelligence reports
- Academic research
- Congressional testimony
- FOIA releases

**Boolean search value**: HIGH - These are precise signal terms with low false-positive rates.

#### Category 2: Organization & Group Names
**Examples from your corpus**:
- Extremist groups: "Tempel ov Blood", "Order of Nine Angels", "764", "The Community"
- Government agencies: "Army Threat Integration Center", "Illinois Statewide Terrorism & Intelligence Center (STIC)", "NYPD Intelligence and Counterterrorism Bureau"
- Think tanks/NGOs: "Property of the People", "National Counterterrorism Innovation, Technology, and Education Center"

**Why these matter**: Organization names are highly specific identifiers. When they appear in documents, it's almost always substantive.

**Boolean search value**: VERY HIGH - Extremely low false-positive rate, high relevance.

#### Category 3: Acronyms & Abbreviations
**Examples from your corpus**:
- NVE, DVE, REMVE (extremism categories)
- FOIA, FVEY (Five Eyes)
- DHS, FBI, DOD
- STIC, BRIC, JRIC (fusion centers)

**Why these matter**: Acronyms are how insiders communicate. Government documents are FULL of them.

**Boolean search value**: MEDIUM-HIGH - Some acronyms are overloaded (e.g., "DHS" could be "Department of Health Services" in some contexts), but most are highly specific.

#### Category 4: Multi-Word Phrases (Collocations)
**Examples from your corpus**:
- "court-authorized search"
- "threat to critical infrastructure"
- "online platform suspension"
- "operational security"
- "pre-operational activities"
- "mass-casualty attacks"
- "violent extremist propaganda"

**Why these matter**: These phrases capture specific concepts that wouldn't be found with single keywords alone. "Operational security" is different from just "security".

**Boolean search value**: HIGH - These are contextual indicators that separate signal from noise.

#### Category 5: Named Entities (People, Places, Events)
**Examples from your corpus**:
- People: Luigi Mangione, Kash Patel, Shane Tamura
- Places: Tower 22, Midtown Manhattan, Buffalo (mass shooting)
- Events: January 6th, Roe v. Wade overturning

**Why these matter**: Named entities are how stories develop. If you're tracking "January 6th", you want all mentions across sources.

**Boolean search value**: VARIES - High for ongoing stories, lower for one-off mentions.

#### Category 6: Thematic Concept Clusters
**Examples from your corpus**:
- Power grid attacks: "targeting power grid", "attacks on electrical infrastructure", "electricity infrastructure", "substations"
- Foreign influence: "Russian meddling", "Beijing influence", "transnational repression"
- Technology threats: "attack drones", "UAS" (Unmanned Aircraft Systems), "cyber attacks"

**Why these matter**: Investigative journalists need to track THEMES across time. A story about "power grid attacks" might use different terminology in different sources.

**Boolean search value**: MEDIUM-HIGH - Requires careful query construction to avoid false positives.

---

### 1.2 Extraction Methodologies

#### Method A: N-Gram Analysis (Statistical Frequency)
**How it works**: Identify all 2-grams, 3-grams, 4-grams, 5-grams in your corpus and rank by frequency.

**Pros**:
- Catches phrases you might not notice manually
- Identifies what your sources actually talk about (not what you think they talk about)
- Quantitative ranking

**Cons**:
- High noise - will return lots of common phrases ("in the United States", "according to the")
- Needs filtering by stopwords and common phrases

**Best for**: Categories 3, 4, 6 (phrases, collocations, thematic clusters)

**Implementation**:
```python
from collections import Counter
import re

def extract_ngrams(text, n):
    words = re.findall(r'\b\w+\b', text.lower())
    ngrams = zip(*[words[i:] for i in range(n)])
    return [' '.join(ngram) for ngram in ngrams]

# Count all 3-grams across corpus
all_trigrams = Counter()
for article in articles:
    trigrams = extract_ngrams(article['content'], 3)
    all_trigrams.update(trigrams)

# Filter by frequency threshold
significant_trigrams = {phrase: count for phrase, count in all_trigrams.items()
                        if count >= 3}  # appears in 3+ articles
```

#### Method B: TF-IDF (Term Frequency-Inverse Document Frequency)
**How it works**: Identifies terms that are DISTINCTIVE to your corpus vs general language.

**Pros**:
- Automatically filters out common words
- Finds specialized terminology
- Works well for domain jargon

**Cons**:
- Misses proper nouns that might appear only once but are important
- Requires a reference corpus for comparison

**Best for**: Categories 1, 3 (domain terminology, acronyms)

**Implementation**:
```python
from sklearn.feature_extraction.text import TfidfVectorizer

# Extract distinctive terms
vectorizer = TfidfVectorizer(
    ngram_range=(1, 4),  # unigrams through 4-grams
    max_features=1000,
    stop_words='english'
)

# Fit on your corpus
tfidf_matrix = vectorizer.fit_transform([article['content'] for article in articles])
feature_names = vectorizer.get_feature_names_out()

# Get top scoring terms
scores = tfidf_matrix.sum(axis=0).A1
top_terms = sorted(zip(feature_names, scores), key=lambda x: x[1], reverse=True)
```

#### Method C: Named Entity Recognition (NER)
**How it works**: Use NLP models to identify people, organizations, locations, dates.

**Pros**:
- Automatically extracts proper nouns
- Catches entities you might miss manually
- Handles variations (e.g., "FBI" vs "Federal Bureau of Investigation")

**Cons**:
- Not always accurate on specialized text
- Misses domain-specific non-entity terms

**Best for**: Categories 2, 5 (organizations, named entities)

**Implementation**:
```python
import spacy

nlp = spacy.load("en_core_web_lg")

def extract_entities(text):
    doc = nlp(text)
    entities = {
        'persons': [ent.text for ent in doc.ents if ent.label_ == 'PERSON'],
        'orgs': [ent.text for ent in doc.ents if ent.label_ == 'ORG'],
        'locations': [ent.text for ent in doc.ents if ent.label_ in ['GPE', 'LOC']],
        'events': [ent.text for ent in doc.ents if ent.label_ == 'EVENT']
    }
    return entities

# Extract across corpus
all_entities = {'persons': Counter(), 'orgs': Counter(),
                'locations': Counter(), 'events': Counter()}

for article in articles:
    entities = extract_entities(article['content'])
    for category in entities:
        all_entities[category].update(entities[category])
```

#### Method D: Collocation Analysis (Statistical Co-occurrence)
**How it works**: Finds words that appear together more often than random chance would predict.

**Pros**:
- Identifies meaningful phrases (not just frequent phrases)
- Good for technical terminology
- Captures multi-word concepts

**Cons**:
- Computationally intensive
- May miss rare but important collocations

**Best for**: Categories 4, 6 (multi-word phrases, thematic clusters)

**Implementation**:
```python
from nltk.collocations import BigramCollocationFinder, TrigramCollocationFinder
from nltk.metrics import BigramAssocMeasures, TrigramAssocMeasures

# Bigram collocations
words = [word for article in articles for word in article['content'].split()]
bigram_finder = BigramCollocationFinder.from_words(words)
bigram_finder.apply_freq_filter(3)  # appears 3+ times
bigrams = bigram_finder.nbest(BigramAssocMeasures.pmi, 500)  # top 500 by PMI

# Trigram collocations
trigram_finder = TrigramCollocationFinder.from_words(words)
trigram_finder.apply_freq_filter(3)
trigrams = trigram_finder.nbest(TrigramAssocMeasures.pmi, 500)
```

#### Method E: LLM-Based Extraction (Semantic Understanding)
**How it works**: Use GPT-4/Claude to identify important terms and concepts.

**Pros**:
- Understands context and meaning
- Can identify implicit concepts
- Can categorize terms semantically

**Cons**:
- Expensive for full corpus
- May hallucinate terms not in corpus
- Not deterministic

**Best for**: ALL categories, but especially 1, 6 (domain jargon, thematic concepts)

**Implementation**:
```python
import anthropic

def extract_keywords_llm(article_text, existing_taxonomy):
    prompt = f"""Analyze this national security journalism article and extract:

1. Domain-specific terminology and jargon
2. Organization names (government agencies, extremist groups, NGOs)
3. Acronyms and abbreviations
4. Multi-word technical phrases
5. Named entities (people, places, events)
6. Thematic concepts

Article:
{article_text}

Return as JSON with categories."""

    # Call Claude API
    response = client.messages.create(...)
    return parse_keywords(response)
```

---

### 1.3 Hybrid Extraction Strategy (RECOMMENDED)

The most effective approach combines multiple methods:

**PHASE 1: Automated Broad Extraction**
1. Run TF-IDF to get distinctive terms → filters to top 1000 candidates
2. Run NER to extract all named entities → filters by frequency (3+ mentions)
3. Run n-gram analysis for 2-5 word phrases → filters by frequency (3+ mentions)
4. Run collocation analysis for statistically significant phrases

**PHASE 2: LLM-Based Refinement**
1. Feed top candidates from Phase 1 to Claude/GPT
2. Ask LLM to:
   - Remove false positives
   - Add missing important terms
   - Categorize terms by type
   - Identify variations and synonyms
   - Flag terms that need disambiguation

**PHASE 3: Manual Curation**
1. Review LLM output
2. Add domain expertise (terms you know are important but might not appear frequently)
3. Create synonym clusters (e.g., "NVE" = "nihilistic violent extremism" = "nihilist extremism")
4. Build hierarchies (e.g., "domestic terrorism" → "accelerationism" → "terrorgram")

---

### 1.4 Keyword Organization Structure

Once extracted, keywords should be organized for effective Boolean search construction:

```json
{
  "keyword_database": {
    "domestic_extremism": {
      "primary_terms": [
        "nihilistic violent extremism",
        "NVE",
        "domestic violent extremists",
        "DVE"
      ],
      "related_concepts": [
        "accelerationism",
        "militant accelerationism",
        "eco-fascism",
        "white supremacy"
      ],
      "organizations": [
        "Tempel ov Blood",
        "Order of Nine Angles",
        "764",
        "The Community"
      ],
      "indicators": [
        "critical infrastructure",
        "power grid",
        "operational security",
        "mass-casualty attacks"
      ],
      "monitoring_agencies": [
        "FBI",
        "DHS",
        "fusion centers",
        "STIC",
        "BRIC"
      ],
      "synonyms": {
        "NVE": ["nihilistic violent extremism", "nihilist extremism"],
        "DVE": ["domestic violent extremists", "domestic extremists"]
      },
      "boolean_queries": [
        "(\"nihilistic violent extremism\" OR NVE) AND (FBI OR \"Department of Homeland Security\")",
        "(accelerationism OR \"militant accelerationism\") AND (\"critical infrastructure\" OR \"power grid\")"
      ]
    },
    "intelligence_oversight": {
      "primary_terms": [
        "FOIA",
        "Freedom of Information Act",
        "transparency",
        "classified documents"
      ],
      "organizations": [
        "Property of the People",
        "Electronic Frontier Foundation",
        "ACLU"
      ],
      "document_types": [
        "intelligence reports",
        "threat assessments",
        "fusion center reports"
      ],
      "boolean_queries": [
        "(FOIA OR \"Freedom of Information\") AND (FBI OR DHS OR \"intelligence report\")"
      ]
    }
  }
}
```

**Key organizational principles**:
1. **Thematic grouping**: Keywords clustered by investigative topic
2. **Hierarchical structure**: Primary → Related → Specific
3. **Synonym mapping**: All variations linked
4. **Pre-built queries**: Common Boolean searches ready to use
5. **Metadata tagging**: Each keyword tagged with category, importance, disambiguation notes

---

### 1.5 Quality Control & Filtering

Not all extracted keywords are equally valuable. Apply these filters:

#### Filter 1: Frequency Threshold
- **Minimum**: Appears in 2+ articles (avoids one-off mentions)
- **Exception**: Named entities from major events (e.g., "Luigi Mangione" might appear once but is important)

#### Filter 2: Specificity Score
- Rate each term on specificity (1-10)
- HIGH specificity (9-10): "Army Threat Integration Center", "Terrorgram"
- MEDIUM specificity (5-8): "domestic terrorism", "power grid"
- LOW specificity (1-4): "government", "report", "attack"
- **Keep**: HIGH and MEDIUM

#### Filter 3: Disambiguation
- Flag terms with multiple meanings:
  - "DHS" → Department of Homeland Security vs Department of Health Services
  - "ICE" → Immigration and Customs Enforcement vs Intrusion Countermeasures Electronics
- **Action**: Add disambiguating context to Boolean queries

#### Filter 4: Signal-to-Noise Ratio
- Test each keyword in a sample search
- If >50% of results are irrelevant → add context terms
- Example: "Tower" (noisy) → "Tower 22" (signal)

#### Filter 5: Temporal Relevance
- Flag time-sensitive terms (e.g., "Biden administration" will become historical)
- Mark with lifecycle: emerging, active, declining, historical
- **Use**: Helps prioritize monitoring

---

## PART 2: BOOLEAN SEARCH MONITORING SYSTEM DESIGN

### 2.1 System Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      KEYWORD DATABASE                        │
│  (Organized by theme, with synonyms & Boolean templates)    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   QUERY BUILDER ENGINE                       │
│  • Expands synonyms                                          │
│  • Applies proximity operators                               │
│  • Generates source-specific queries                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  SEARCH EXECUTOR (Parallel)                  │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐  │
│  │ SAM.gov  │  DVIDS   │ USAJobs  │ Google   │  Twitter │  │
│  │ Scraper  │ Scraper  │ Scraper  │   API    │   API    │  │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              RESULT PROCESSOR & DEDUPLICATOR                 │
│  • Content hashing                                           │
│  • Similarity detection                                      │
│  • Source attribution                                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    RELEVANCE SCORER                          │
│  • Keyword match density                                     │
│  • Source credibility                                        │
│  • Recency weighting                                         │
│  • LLM relevance check (optional)                            │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   STORAGE & INDEXING                         │
│  • SQLite/PostgreSQL database                                │
│  • Full-text search index                                    │
│  • Tag/keyword indexing                                      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  ALERTING & REPORTING                        │
│  • Email digests                                             │
│  • Slack/Discord webhooks                                    │
│  • RSS feed generation                                       │
│  • Web dashboard                                             │
└─────────────────────────────────────────────────────────────┘
```

---

### 2.2 Query Construction Strategy

#### Challenge: Different sources support different query syntax

| Source | Boolean Support | Proximity | Wildcards | Notes |
|--------|----------------|-----------|-----------|-------|
| SAM.gov | Basic (AND/OR) | No | No | Exact phrase with quotes |
| DVIDS | Full | Yes (NEAR/n) | Yes (*) | Advanced military search |
| Google | Full | Yes (AROUND(n)) | Limited | Use site: operator |
| Twitter/X API | Limited | No | No | Hashtag + keyword combo |
| Academic DBs | Full | Yes (varies) | Yes | ProQuest, JSTOR style |

#### Solution: Query Templates by Source

**Template 1: SAM.gov (Simple Boolean)**
```
Base concept: Domestic extremism monitoring

Query:
("domestic extremism" OR "domestic terrorism" OR "violent extremism")
AND ("threat assessment" OR "intelligence" OR "fusion center")
```

**Template 2: Google Advanced (Proximity + Site)**
```
Base concept: FBI nihilism reporting

Query:
site:fbi.gov OR site:dhs.gov OR site:.mil
("nihilistic violent extremism" OR NVE)
AROUND(10) ("threat" OR "report" OR "assessment")
-site:recruitment  # exclude recruitment pages
```

**Template 3: DVIDS (Full Boolean + Proximity)**
```
Base concept: Critical infrastructure threats

Query:
("critical infrastructure" OR "power grid" OR "electrical grid")
NEAR/5 ("attack" OR "threat" OR "vulnerability")
AND (terrorism OR extremism OR "domestic threat")
NOT ("natural disaster" OR weather)
```

**Template 4: Academic/Research Databases**
```
Base concept: Accelerationism research

Query:
TI,AB((accelerationism OR "accelerationist" OR "militant accelerationism")
AND ("domestic extremism" OR "violent extremism" OR terrorism)
AND (United States OR America))
```

#### Synonym Expansion Engine

```python
def expand_query(base_term, keyword_db):
    """
    Expands a base term with all synonyms and variations
    """
    synonyms = keyword_db['synonyms'].get(base_term, [base_term])

    # Build OR clause with all variations
    or_clause = ' OR '.join([f'"{syn}"' for syn in synonyms])

    return f'({or_clause})'

# Example:
expand_query("NVE", keyword_db)
# Returns: ("nihilistic violent extremism" OR "NVE" OR "nihilist extremism")
```

---

### 2.3 Search Targets & Integration Points

#### Tier 1: Government Databases (High Signal)
1. **SAM.gov** - Contract opportunities, you already have integration
2. **DVIDS** - Military news and images, you already have integration
3. **USAJobs** - Job postings (signals new programs/priorities)
4. **Federal Register** - Proposed rules, notices
5. **Congress.gov** - Bills, hearings, reports
6. **FOIA portals** - Document releases (FBI Vault, CIA FOIA, etc.)

#### Tier 2: News & Media
1. **Google News API** - Broad news coverage
2. **NewsAPI** - Multi-source aggregation
3. **ProPublica** - Investigative journalism
4. **Associated Press API** - Wire service

#### Tier 3: Social Media & Forums
1. **Twitter/X API** - Real-time discussions
2. **Reddit API** - Community discussions (r/intelligence, r/nationalSecurity)
3. **Telegram** - Via scrapers (where extremist groups communicate)
4. **Discord** - You already monitor some servers

#### Tier 4: Academic & Research
1. **Google Scholar** - Academic papers
2. **SSRN** - Social science research
3. **arXiv** - Preprints

#### Tier 5: Specialized Sources
1. **Bellingcat** - Open source investigations
2. **OSINT Twitter lists** - Curated expert feeds
3. **Government accountability orgs** - POGO, GAP, etc.

---

### 2.4 Deduplication & Result Processing

#### Challenge: Same story appears across multiple sources

**Deduplication Strategy**:

1. **Content Hashing**
   - Extract first 500 chars, compute SHA-256
   - If hash exists → duplicate

2. **Title Similarity**
   - Use fuzzy matching (Levenshtein distance)
   - If >85% similar → likely duplicate

3. **URL Canonicalization**
   - Strip tracking parameters
   - Normalize URLs
   - Check if same page

4. **Content Similarity**
   - Use MinHash or simhash
   - If >90% similar → duplicate or reprint

5. **Source Attribution**
   - If duplicate detected, keep earliest source
   - Mark all sources in metadata

**Implementation**:
```python
from datasketch import MinHash, MinHashLSH
import hashlib

class ResultDeduplicator:
    def __init__(self):
        self.lsh = MinHashLSH(threshold=0.9, num_perm=128)
        self.seen_hashes = set()

    def is_duplicate(self, result):
        # Method 1: Exact hash
        content_hash = hashlib.sha256(result['content'][:500].encode()).hexdigest()
        if content_hash in self.seen_hashes:
            return True

        # Method 2: MinHash similarity
        m = MinHash(num_perm=128)
        for word in result['content'].split():
            m.update(word.encode('utf-8'))

        # Check if similar document exists
        similar = self.lsh.query(m)
        if similar:
            return True

        # Not duplicate - add to index
        self.seen_hashes.add(content_hash)
        self.lsh.insert(result['id'], m)
        return False
```

---

### 2.5 Relevance Scoring & Ranking

Not all results are equally important. Rank by:

**Factor 1: Keyword Match Density**
- How many of your keywords appear?
- Are they in the title vs body?
- Proximity of related keywords

**Factor 2: Source Credibility**
```
Tier 1 (10 points): Government sources, academic journals
Tier 2 (8 points): Major news outlets, established journalists
Tier 3 (6 points): Investigative orgs (Bellingcat, ProPublica)
Tier 4 (4 points): Local news, blogs
Tier 5 (2 points): Social media
```

**Factor 3: Recency**
```
< 24 hours: 10 points
< 1 week: 8 points
< 1 month: 6 points
< 6 months: 4 points
> 6 months: 2 points
```

**Factor 4: Exclusivity**
- First mention of a term? +5 points
- Exclusive document release? +10 points
- Breaking news? +8 points

**Factor 5: LLM Relevance Check (Optional)**
For borderline results, ask Claude:
```
"Is this article relevant to investigative journalism on: {topic}?
Rate 1-10 and explain."
```

**Final Score**:
```
score = (keyword_density * 0.3) +
        (source_credibility * 0.25) +
        (recency * 0.2) +
        (exclusivity * 0.15) +
        (llm_score * 0.1)
```

---

### 2.6 Storage Architecture

#### Database Schema

```sql
-- Main results table
CREATE TABLE search_results (
    id INTEGER PRIMARY KEY,
    query_id INTEGER,
    title TEXT,
    url TEXT UNIQUE,
    content TEXT,
    source TEXT,
    published_date DATETIME,
    discovered_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    relevance_score REAL,
    is_duplicate BOOLEAN DEFAULT FALSE,
    duplicate_of INTEGER REFERENCES search_results(id),

    -- Metadata
    keywords_matched TEXT,  -- JSON array
    content_hash TEXT,

    FOREIGN KEY (query_id) REFERENCES queries(id)
);

-- Queries table
CREATE TABLE queries (
    id INTEGER PRIMARY KEY,
    query_text TEXT,
    query_type TEXT,  -- boolean, proximity, etc.
    theme TEXT,  -- domestic_extremism, foia, etc.
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_run DATETIME,
    is_active BOOLEAN DEFAULT TRUE
);

-- Keywords table
CREATE TABLE keywords (
    id INTEGER PRIMARY KEY,
    keyword TEXT UNIQUE,
    category TEXT,
    importance INTEGER,  -- 1-10
    synonyms TEXT,  -- JSON array
    first_seen DATETIME,
    times_matched INTEGER DEFAULT 0
);

-- Result-Keyword mapping
CREATE TABLE result_keywords (
    result_id INTEGER,
    keyword_id INTEGER,
    match_type TEXT,  -- exact, synonym, partial
    PRIMARY KEY (result_id, keyword_id),
    FOREIGN KEY (result_id) REFERENCES search_results(id),
    FOREIGN KEY (keyword_id) REFERENCES keywords(id)
);

-- Full-text search index
CREATE VIRTUAL TABLE results_fts USING fts5(
    title, content, keywords_matched
);
```

---

### 2.7 Alerting & Notification System

#### Alert Triggers

**Immediate Alerts** (Slack/Email/SMS):
1. High-confidence match (score > 8.5) on priority keywords
2. First-time appearance of tracked term
3. Document release from FOIA source
4. Breaking news from Tier 1 source

**Daily Digest** (Email):
1. All new results grouped by theme
2. Top 10 by relevance score
3. New keywords discovered
4. Summary statistics

**Weekly Report** (Email/PDF):
1. Trending topics (increasing mentions)
2. New connections (keywords appearing together)
3. Source diversity analysis
4. Coverage gaps (queries returning no results)

**Dashboard** (Web UI):
1. Real-time result stream
2. Search by keyword/theme
3. Temporal analysis (timeline view)
4. Network graph (keyword co-occurrence)

#### Implementation

```python
class AlertManager:
    def __init__(self, config):
        self.slack_webhook = config['slack_webhook']
        self.email_config = config['email']

    def should_alert_immediate(self, result):
        return (
            result['relevance_score'] > 8.5 or
            result['is_first_mention'] or
            result['source'] in ['fbi.gov', 'dhs.gov'] or
            result['exclusivity_score'] > 8
        )

    def send_immediate_alert(self, result):
        message = f"""
        🚨 High-Priority Match

        **{result['title']}**
        Source: {result['source']}
        Score: {result['relevance_score']}/10
        Keywords: {', '.join(result['keywords_matched'])}

        {result['url']}
        """

        # Send to Slack
        requests.post(self.slack_webhook, json={'text': message})

        # Send email if configured
        if result['relevance_score'] > 9.0:
            self.send_email(subject=f"URGENT: {result['title']}", body=message)
```

---

### 2.8 Workflow: From Query to Alert

**Daily Cycle**:

```
06:00 AM - Scheduled queries run against all sources
06:30 AM - Results aggregated, deduplicated
07:00 AM - Relevance scoring completed
07:15 AM - Immediate alerts sent for high-priority matches
07:30 AM - Results added to database
08:00 AM - Daily digest email sent

12:00 PM - Midday query run (high-priority sources only)
12:30 PM - Immediate alerts if any

06:00 PM - Evening query run
06:30 PM - Immediate alerts if any

Sunday 9:00 AM - Weekly report generated and sent
```

**Manual Trigger**:
- User can trigger ad-hoc search via dashboard
- Custom query builder for one-off investigations

---

### 2.9 Integration with Existing Tag System

Your existing tag taxonomy (440 tags, 20 categories) is a PERFECT foundation:

**Keyword → Tag Mapping**:
```json
{
  "nihilistic violent extremism": {
    "existing_tag": "Domestic terrorism",
    "category": "National Security & Intelligence",
    "related_tags": ["FBI", "Trump Administration", "Civil liberties"]
  },
  "FOIA": {
    "existing_tag": "FOIA / transparency",
    "category": "Government Oversight & Accountability",
    "related_tags": ["Classified documents", "Whistleblowers"]
  }
}
```

**Auto-Tagging New Results**:
When a new article is discovered via Boolean search:
1. Extract keywords matched
2. Map to existing tags
3. Auto-tag article with matched tags
4. If no matching tag exists → flag for manual review
5. Update tag index with new article

**Feedback Loop**:
```
New Boolean Search Result
    ↓
Extract Keywords
    ↓
Map to Existing Tags
    ↓
Auto-Tag Article
    ↓
Add to tag_index_full.json
    ↓
Regenerate taxonomy_browse.html
    ↓
New article appears in your taxonomy browser!
```

---

### 2.10 Advanced Features (Phase 2)

Once basic system is running, consider:

#### Feature 1: Automated Query Refinement
- Track query performance (how many results? relevance?)
- Use LLM to suggest query improvements
- A/B test different query formulations

#### Feature 2: Network Analysis
- Build knowledge graph of keyword co-occurrence
- Identify emerging themes
- Detect topic drift over time

#### Feature 3: Predictive Alerts
- Use historical patterns to predict when new stories might emerge
- "The last 3 times 'NVE' spiked, an incident happened within 2 weeks"

#### Feature 4: Source Diversity Tracking
- Ensure you're not overly reliant on one source
- Alert if important story is only in one outlet (might be exclusive or might be unreliable)

#### Feature 5: Export to Investigations
- "Create investigation folder" button
- Exports all related articles, keywords, timeline
- Generates initial research briefing doc

---

## PART 3: IMPLEMENTATION ROADMAP

### Phase 1: Foundation (Weeks 1-2)
1. **Extract keywords from corpus**
   - Run automated extraction (TF-IDF, NER, n-grams)
   - LLM refinement
   - Manual curation
   - Output: `keyword_database.json`

2. **Design database schema**
   - Implement SQLite database
   - Create indexes
   - Test with sample data

3. **Build query builder**
   - Create templates for different sources
   - Synonym expansion
   - Test queries manually

### Phase 2: Core Functionality (Weeks 3-4)
1. **Implement search integrations**
   - SAM.gov (already have)
   - DVIDS (already have)
   - Google News API
   - One social media source (Twitter or Reddit)

2. **Build result processor**
   - Deduplication
   - Relevance scoring
   - Storage

3. **Basic alerting**
   - Email digest
   - Slack webhook

### Phase 3: Automation (Week 5)
1. **Scheduler**
   - Cron jobs for daily runs
   - Error handling and retries

2. **Dashboard**
   - Simple web UI to view results
   - Search and filter

3. **Tag integration**
   - Map keywords to existing tags
   - Auto-update taxonomy

### Phase 4: Refinement (Week 6+)
1. **Monitoring and tuning**
   - Track false positives
   - Refine queries
   - Adjust relevance scoring

2. **Advanced features**
   - Network analysis
   - Predictive alerts
   - Additional sources

---

## PART 4: TECHNICAL STACK RECOMMENDATIONS

### Option A: Lightweight (Fastest to implement)
- **Language**: Python (reuse your existing code)
- **Database**: SQLite (easy, portable)
- **Search**: Direct API calls + BeautifulSoup for scraping
- **Scheduler**: cron + Python scripts
- **Dashboard**: Streamlit (you're already using it!)
- **Alerts**: smtplib (email) + requests (Slack)

**Pros**: Minimal dependencies, fast setup, familiar tools
**Cons**: Scaling limitations, manual monitoring

### Option B: Production-Ready (More robust)
- **Language**: Python
- **Database**: PostgreSQL (better concurrency, full-text search)
- **Task Queue**: Celery + Redis (distributed task execution)
- **Search**: Elasticsearch (powerful full-text search)
- **Scheduler**: Celery Beat (robust scheduling)
- **Dashboard**: React + FastAPI backend
- **Alerts**: Twilio (SMS) + SendGrid (email) + Slack

**Pros**: Scales well, professional, maintainable
**Cons**: More complex, steeper learning curve

### Option C: Hybrid (Recommended)
Start with Option A, migrate to Option B components as needed:
- Phase 1-2: SQLite, cron, Streamlit
- Phase 3: Add PostgreSQL, Redis
- Phase 4: Add Celery, Elasticsearch

---

## PART 5: EXAMPLE: "NIHILISTIC VIOLENT EXTREMISM" MONITORING

Let's work through your example end-to-end:

### Step 1: Keyword Extraction
From your corpus, extract related terms:
```json
{
  "nve_monitoring": {
    "primary_terms": [
      "nihilistic violent extremism",
      "nihilistic violent extremist",
      "NVE"
    ],
    "synonyms": [
      "nihilist extremism",
      "nihilistic terrorism"
    ],
    "related_concepts": [
      "accelerationism",
      "mass casualty attacks",
      "incel",
      "misanthropic extremism"
    ],
    "organizations": [
      "Tempel ov Blood",
      "Order of Nine Angels",
      "764"
    ],
    "agencies": [
      "FBI",
      "DHS",
      "fusion center",
      "STIC"
    ],
    "indicators": [
      "operational security",
      "Telegram",
      "gore material",
      "mass casualty"
    ]
  }
}
```

### Step 2: Build Boolean Queries

**Query 1: Official Government Reporting**
```
site:(fbi.gov OR dhs.gov OR .mil OR .gov)
("nihilistic violent extremism" OR "NVE" OR "nihilistic violent extremist")
AND ("report" OR "assessment" OR "threat" OR "bulletin")
```

**Query 2: News Coverage**
```
("nihilistic violent extremism" OR "NVE")
AND (FBI OR "Department of Homeland Security" OR "threat assessment")
-site:reddit.com  # exclude social discussion
```

**Query 3: Extremist Activity Indicators**
```
("Tempel ov Blood" OR "Order of Nine Angles" OR "764")
AND (arrest OR investigation OR "law enforcement")
```

**Query 4: Critical Infrastructure Threats**
```
("nihilistic violent extremism" OR NVE OR accelerationism)
AND ("critical infrastructure" OR "power grid" OR "electrical grid")
NEAR/10 (attack OR threat OR plot)
```

### Step 3: Execute Searches
Run queries across:
- FBI.gov
- DHS.gov
- Google News
- Twitter (track #NVE, monitor FBI/DHS accounts)
- Academic databases (research on extremism)

### Step 4: Process Results
- Deduplicate (same story from multiple sources)
- Score by relevance:
  - Exact match "nihilistic violent extremism" in title: 10/10
  - Government source: +2
  - Recent (< 1 week): +1
  - Multiple keywords matched: +1

### Step 5: Alert
**Immediate alert if**:
- New FBI/DHS document mentions NVE
- Breaking news about NVE arrest/attack
- Congressional hearing on NVE

**Daily digest**:
- All new NVE mentions
- Related accelerationism stories
- New research papers

### Step 6: Tag & Index
Auto-tag results with:
- "Domestic terrorism"
- "FBI"
- "National Security & Intelligence"

Add to your existing taxonomy system.

---

## CONCLUSION & NEXT STEPS

You have TWO paths forward:

### Path 1: Start Simple (Recommended)
1. I build you a **keyword extraction script** that analyzes your 367 articles
2. We create a curated **keyword database** organized by theme
3. We build a **minimal Boolean search monitor** for 2-3 sources (SAM.gov, DVIDS, Google)
4. We set up **email alerts** for high-priority matches
5. We integrate with your **existing tag system**

**Timeline**: 1-2 weeks to working prototype
**Effort**: Low (mostly automated)
**Output**: Actionable monitoring system

### Path 2: Build Complete System
1. Full keyword extraction pipeline
2. Multi-source search integration (10+ sources)
3. Advanced deduplication and relevance scoring
4. Web dashboard
5. Automated tagging and taxonomy updates
6. Predictive analytics

**Timeline**: 4-6 weeks to production system
**Effort**: High
**Output**: Professional-grade OSINT monitoring platform

---

## MY RECOMMENDATION

**Start with Path 1, iterate based on what you learn.**

I can immediately:
1. Extract keywords from your corpus using hybrid approach
2. Organize them into a searchable database
3. Build query templates for your top 5 investigative themes
4. Create a simple monitoring script
5. Set up email/Slack alerts

Then we can expand based on which sources give you the best intel.

**Shall I start building the keyword extraction script?** I'll use:
- TF-IDF for distinctive terms
- NER for organizations and people
- N-gram analysis for phrases
- Your existing 440 tags as seed terms
- LLM refinement for quality

We can have a comprehensive keyword database ready within hours, then move to building the search monitor.

What do you think?
