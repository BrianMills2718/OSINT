# Mozart Technical README - Complete Codebase Documentation

**Version**: 0.1.0
**License**: MIT
**Python**: >=3.11
**Purpose**: Automated research and wiki publishing pipeline for UFO/UAP person biographies
**Location**: `~/mozart-backup/mozart-people-extracted/mozart-people/`

---

## Executive Summary

Mozart is a **multi-LLM automated research pipeline** that:
1. Takes a person's name as input
2. Researches them using Perplexity API + Brave Search
3. Extracts structured biographical data using Gemini 2.5 Flash
4. Generates comprehensive wiki prose using Claude Sonnet 4.5
5. Publishes to MediaWiki with automatic Wikibase knowledge graph sync

**Production Status**: Active, 130+ person pages created at https://www.wikidisc.org

---

## Architecture Overview

### Pipeline Flow

```
Person Name Input
    ↓
[1] DISCOVERY - Web search via Perplexity + Brave Search
    ↓
[2] INGESTION - Fetch URLs, extract text (HTML/PDF/OCR)
    ↓
[3] RANKING - Score sources by relevance/authority
    ↓
[4] EXTRACTION - Gemini extracts structured biographical data
    ↓
[5] NORMALIZATION - Validate fields, geocode locations, enrich metadata
    ↓
[6] COMPOSITION - Claude Sonnet generates MediaWiki prose
    ↓
[7] PUBLISHING - Push to MediaWiki API, auto-sync to Wikibase
```

### Multi-LLM Strategy ("Best Model for Each Task")

| Task | Model | Why |
|------|-------|-----|
| Research | Perplexity API | Real-time web access, citation tracking |
| Extraction | Gemini 2.5 Flash | Fast, reliable JSON mode, cheap |
| Prose | Claude Sonnet 4.5 | Best prose quality, nuanced understanding |

**Cost**: ~$0.10-0.50 per biography (mostly Perplexity + Claude)

---

## Directory Structure

```
mozart-people/
├── app/                         # Main application code
│   ├── common/                  # Shared utilities
│   │   ├── exceptions.py        # Custom exceptions
│   │   ├── http.py              # HTTP client wrapper
│   │   ├── logging.py           # Structured logging
│   │   ├── models.py            # Pydantic data models
│   │   └── schema.py            # JSON schema utilities
│   │
│   ├── discovery/               # Step 1: Web search
│   │   ├── perplexity_client.py # Perplexity API client
│   │   ├── brave_client.py      # Brave Search API client
│   │   ├── discover.py          # Main discovery orchestrator
│   │   ├── analysis_agent.py    # LLM-based relevance analysis
│   │   ├── content_analyzer.py  # Content quality scoring
│   │   ├── user_urls.py         # User-provided URL handling
│   │   └── wikipedia_extractor.py # Wikipedia-specific logic
│   │
│   ├── ingestion/               # Step 2: Fetch and parse
│   │   ├── fetch.py             # HTTP fetching with retries
│   │   ├── fetchers.py          # Fetch orchestrator
│   │   ├── html_to_text.py      # HTML → clean text (trafilatura)
│   │   ├── pdf_to_text.py       # PDF → text (pdfminer + OCR)
│   │   ├── playwright_fetch.py  # Browser rendering for JS sites
│   │   ├── evidence_cards.py    # Structure fetched content
│   │   └── mime.py              # Content-type detection
│   │
│   ├── ranking/                 # Step 3: Source ranking
│   │   ├── rank.py              # Ranking algorithm
│   │   └── scoring.py           # Quality scoring
│   │
│   ├── extraction/              # Step 4: LLM extraction
│   │   ├── gemini_extractor.py  # MAIN: Gemini biographical extraction
│   │   ├── gemini.py            # Gemini API wrapper
│   │   └── witness_encounter_extractor.py # Specialized extraction
│   │
│   ├── normalize/               # Step 5: Data validation
│   │   ├── pipeline.py          # Normalization orchestrator
│   │   ├── fields.py            # Field normalization
│   │   ├── validators.py        # Validation rules
│   │   ├── datetime_format.py   # Date/time formatting
│   │   ├── datetime_utils.py    # Date parsing utilities
│   │   ├── geo.py               # Geocoding (Nominatim)
│   │   ├── geonames.py          # GeoNames API client
│   │   ├── regions.py           # Geographic regions
│   │   ├── enrich.py            # Extract metadata from prose
│   │   ├── role_cleanup.py      # Role field cleanup
│   │   └── arbitration.py       # Conflict resolution
│   │
│   ├── compose/                 # Step 6: Prose generation
│   │   ├── prose_sonnet.py      # MAIN: Claude Sonnet prose writer
│   │   ├── builder.py           # Page assembly
│   │   └── template_renderer.py # Jinja2 template rendering
│   │
│   ├── publish/                 # Step 7: MediaWiki publishing
│   │   └── mediawiki.py         # MediaWiki API client
│   │
│   ├── orchestrator/            # Pipeline coordination
│   │   ├── __main__.py          # CLI entry point
│   │   ├── run_topic.py         # MAIN: Full pipeline orchestrator
│   │   ├── pipeline.py          # Pipeline base class
│   │   └── source_filter.py     # Source filtering logic
│   │
│   ├── intake/                  # Input handling
│   │   ├── cli.py               # CLI argument parsing
│   │   ├── csv.py               # CSV file handling
│   │   └── csv_loader.py        # CSV batch processing
│   │
│   ├── qa/                      # Quality assurance
│   │   └── consistency.py       # Data consistency checks
│   │
│   ├── storage/                 # Data persistence
│   │   ├── sqlite.py            # SQLite job storage
│   │   └── artifacts.py         # File artifact storage
│   │
│   ├── llm/                     # LLM utilities
│   │   └── gemini_json.py       # Gemini JSON mode helper
│   │
│   ├── schemas/                 # JSON schemas
│   │   └── person.schema.json   # Person extraction schema
│   │
│   ├── templates/               # MediaWiki templates
│   │   └── person_enhanced.j2   # Person_Enhanced template
│   │
│   ├── web/                     # Web UI (FastAPI)
│   │   ├── main.py              # FastAPI app
│   │   ├── taskrunner.py        # Background task runner
│   │   ├── static/              # CSS/JS assets
│   │   └── templates/           # HTML templates
│   │
│   └── config.py                # Configuration management
│
├── scripts/                     # Utility scripts
│   ├── run_topic.py             # MAIN: Single person CLI
│   └── run_csv.py               # Batch CSV processing
│
├── tests/                       # Test suite
│   └── (pytest tests)
│
├── logs/                        # Execution logs (JSONL)
├── .out/                        # Dry-run output (wikitext)
│
├── pyproject.toml               # Dependencies
├── uv.lock                      # Lockfile
├── .env                         # API keys (SENSITIVE)
├── .env.example                 # Example config
├── Dockerfile                   # Docker build
├── docker-compose.yml           # Docker compose
├── Makefile                     # Build commands
└── README.md                    # User documentation
```

---

## Key Components Deep Dive

### 1. Discovery (`app/discovery/`)

**Purpose**: Find relevant sources about the person

**Main File**: `discover.py` (10KB)

**Process**:
1. Call Perplexity API with person's name
2. Call Brave Search API with refined queries
3. Analyze content relevance using LLM
4. Return ranked list of URLs

**Key Files**:
- `perplexity_client.py` (18KB) - Perplexity API integration
- `brave_client.py` (9KB) - Brave Search API integration
- `analysis_agent.py` (11KB) - LLM relevance analysis
- `content_analyzer.py` (9KB) - Content quality scoring

**Configuration**:
```python
MAX_URLS_PER_TOPIC = 40  # From .env
FETCH_CONCURRENCY = 4
```

### 2. Ingestion (`app/ingestion/`)

**Purpose**: Fetch URLs and extract text content

**Main File**: `fetch.py` (9KB)

**Process**:
1. Fetch URL with retries (httpx)
2. Detect content type (HTML/PDF/other)
3. Extract text:
   - HTML → trafilatura (clean text)
   - PDF → pdfminer.six + pytesseract OCR
   - JavaScript sites → Playwright rendering
4. Structure as "evidence cards"

**Key Files**:
- `fetch.py` (9KB) - HTTP fetching with retries
- `html_to_text.py` (2KB) - HTML extraction
- `pdf_to_text.py` (4KB) - PDF + OCR extraction
- `playwright_fetch.py` (5KB) - Browser automation
- `evidence_cards.py` (8KB) - Structure fetched content

**Capabilities**:
- ✅ HTML parsing (trafilatura)
- ✅ PDF text extraction (pdfminer.six)
- ✅ OCR for scanned PDFs (pytesseract)
- ✅ JavaScript rendering (Playwright)
- ✅ Retry logic with exponential backoff
- ✅ Concurrent fetching (4 parallel)

### 3. Ranking (`app/ranking/`)

**Purpose**: Score sources by relevance and authority

**Main File**: `rank.py` (7KB)

**Scoring Factors**:
- Domain authority (.gov, .mil, .edu higher)
- Content length (longer = more substantial)
- Keyword matches
- Publication date (recent preferred)
- Source diversity

**Output**: Sorted list of sources with scores

### 4. Extraction (`app/extraction/`)

**CRITICAL FILE**: `gemini_extractor.py` (46KB)

**Purpose**: Extract structured biographical data using Gemini 2.5 Flash

**System Prompt** (lines 20-400):
```
SYSTEM (Gemini extraction - Person Biography with Verification Awareness)

You are a biographical information extraction worker. Produce STRICT JSON matching the provided JSON Schema.
- Output JSON only (no code fences, comments, or prose).
- Do not invent data. Leave fields empty ("" or []) when information is absent.
- CRITICAL: Distinguish between VERIFIED FACTS and UNVERIFIED CLAIMS throughout extraction.
```

**Key Features**:
- **Verification-aware**: Distinguishes verified vs. disputed claims
- **Role-specific fields**: Military, congressional, witness-specific
- **Comprehensive extraction**: 50+ biographical fields
- **JSON Schema validation**: Strict schema adherence
- **Safety settings**: Permissive for UAP/UFO topics

**Fields Extracted** (from schema):
```json
{
  "full_name": "string",
  "birth_date": "YYYY-MM-DD or YYYY or YYYY-MM",
  "death_date": "YYYY-MM-DD or YYYY or YYYY-MM",
  "nationality": ["American", "British"],
  "birthplace": "City, State, Country",
  "primary_role": "Scientist/Academic | Witness (Military) | Government Official | ...",
  "roles": ["array of roles"],
  "occupation": "Professional occupation",
  "current_status": "Active | Retired | Deceased | Unknown",
  "current_location": "City, State",
  "notable_for": "2-3 sentence summary",
  "testimony_status": "Congressional testimony | Sworn affidavit | ...",
  "disclosure_stance": "Pro-disclosure advocate | Supports disclosure | ...",
  "key_claims": "* Bullet list of major claims",
  "program_involvement": "Worked on official UAP program | ...",
  "affiliations": ["Organizations", "Agencies"],
  "credentials_verification": "Verified | Unverified | Disputed | Fabricated",
  "education": ["Ph.D.|Physics|MIT|1985", "B.S.|Engineering|Stanford|1980"],
  "professional_background": "Career history",
  "publications": ["Title|Year|Type"],
  "media_appearances": "Podcast episodes, documentaries, conferences",
  "awards": "Recognition and honors",
  "website": "https://...",
  "twitter_url": "https://x.com/...",
  "instagram_url": "https://instagram.com/...",
  "linkedin_url": "https://linkedin.com/in/...",

  // Military-specific
  "rank_position": "Captain | Lieutenant | ...",
  "branch_of_service": "U.S. Air Force | U.S. Navy | ...",
  "security_clearance": "Top Secret/SCI | Secret | ...",
  "years_of_service": "1964-1971",
  "unit_command": "Oscar Flight | 509th Squadron | ...",

  // Congressional-specific
  "congressional_chamber": "U.S. Senate | U.S. House",
  "congressional_start": "YYYY-MM-DD",
  "congressional_end": "YYYY-MM-DD",
  "congressional_status": "Active | Retired | Deceased"
}
```

**Configuration**:
```python
EXTRACTION_MODEL = "gemini-2.5-flash"  # From .env
MAX_CHARS_PER_SOURCE = 4000  # Excerpt size
```

### 5. Normalization (`app/normalize/`)

**Purpose**: Validate, clean, and enrich extracted data

**Main File**: `pipeline.py` (1KB orchestrator)

**Steps**:
1. **Field normalization** (`fields.py`, 10KB)
   - Standardize date formats
   - Clean text fields
   - Validate enums

2. **Geocoding** (`geo.py`, 18KB)
   - Convert locations → coordinates
   - Uses Nominatim API
   - Fallback to GeoNames API

3. **Metadata enrichment** (`enrich.py`, 15KB)
   - Extract person names from prose (regex)
   - Extract organizations (FBI, CIA, etc.)
   - Extract document references
   - Extract duration mentions
   - Fill missing fields

4. **Validation** (`validators.py`, 8KB)
   - Validate required fields
   - Check field formats
   - Flag inconsistencies

**Enrichment Patterns** (from `enrich.py`):
```python
# Person names with ranks
r'\b(Lt\.|Capt\.|Maj\.|Col\.|Gen\.|Dr\.|Prof\.)\s+\w+\s+\w+'

# Organizations
r'\b(FBI|CIA|NSA|DIA|Air Force|Navy|Pentagon|Project Blue Book)\b'

# Documents
r'\b(DIA Report|FOIA Files|Declassified|Memorandum)\b'

# Duration
r'\b(\d+)\s+(hours?|minutes?|seconds?)\b'
```

### 6. Composition (`app/compose/`)

**CRITICAL FILE**: `prose_sonnet.py` (38KB)

**Purpose**: Generate comprehensive MediaWiki prose using Claude Sonnet 4.5

**System Prompt** (lines 15-400):
```
SYSTEM (Sonnet prose - Person Biography with Verification Awareness)

You are drafting a biographical page for a person in UFO phenomena. Output WIKITEXT only.
- DO NOT include the {{Person Enhanced}} template - it will be added separately.
- TARGET LENGTH: Under 5000 words total (comprehensive but focused).
- Build every paragraph from the provided SOURCE BRIEFS with proper verification framing.

CRITICAL VERIFICATION RULES:
- For UNVERIFIED claims: Use "claims", "reportedly", "according to [person]", "states that"
- For DISPUTED credentials: Use "disputed", "contested", "no records found to verify"
- For VERIFIED facts: Use standard declarative statements
- Never present unverified claims as established facts
```

**Role-Aware Section Structure**:

**Scientists/Academics**:
```
[Lead paragraphs - no heading]
== UAP Research and Investigations == (60% of content)
== Scientific Background and Credentials == (20%)
== Public Statements and Media Presence == (20%)
== Affiliations ==
== See Also == | == References ==
```

**Government Officials**:
```
[Lead paragraphs - no heading]
== Background and Credentials == (15-20%)
== UAP-Related Legislative Work == (50-60% PRIMARY)
== UAP-Related Public Statements == (20-25%)
```

**Whistleblowers/Witnesses/Military**:
```
[Lead paragraphs - no heading]
== Early Life and Education ==
== Career ==
== UFO-Related Activities ==
== Claims and Controversies == (REQUIRED if disputed)
== Credentials Verification ==
== Reception and Analysis ==
== Media and Publications ==
```

**Configuration**:
```python
PROSE_MODEL = "claude-sonnet-4-5-20250929"  # From .env
MAX_TOKENS = 8000  # Increased from 2000
TARGET_LENGTH = "Under 5000 words"
```

**Template Rendering** (`template_renderer.py`, 1KB):
- Uses Jinja2
- Renders `Person_Enhanced` infobox
- Inserts structured data

### 7. Publishing (`app/publish/`)

**Main File**: `mediawiki.py` (9KB)

**Purpose**: Publish to MediaWiki via API

**Process**:
1. Login to MediaWiki (get login token)
2. Get edit token (CSRF protection)
3. Create/update page via `action=edit`
4. Auto-triggers Wikibase sync extension

**MediaWiki API Flow**:
```python
# Step 1: Get login token
POST /api.php?action=query&meta=tokens&type=login

# Step 2: Login
POST /api.php?action=login
  lgname=Mozart
  lgpassword=...
  lgtoken=...

# Step 3: Get edit token
POST /api.php?action=query&meta=tokens

# Step 4: Create page
POST /api.php?action=edit
  title=Person_Name
  text=wikitext_content
  summary="Created by Mozart bot"
  token=...
```

**Configuration**:
```python
MEDIAWIKI_API_BASE = "https://www.wikidisc.org/api.php"
MEDIAWIKI_USERNAME = "Mozart"
MEDIAWIKI_PASSWORD = "..."
DRY_RUN = "false"  # If true, saves to .out/ instead
```

### 8. Orchestrator (`app/orchestrator/`)

**CRITICAL FILE**: `run_topic.py` (39KB)

**Purpose**: Coordinate entire pipeline for a single person

**Main Function** (lines 100-300):
```python
async def run_person_biography(person_name: str):
    # Step 1: Discovery
    urls = await discover_sources(person_name)

    # Step 2: Ingestion
    sources = await fetch_sources(urls)

    # Step 3: Ranking
    ranked_sources = rank_sources(sources)

    # Step 4: Extraction (Gemini)
    bio_data = await extract_biography(ranked_sources, person_name)

    # Step 5: Normalization
    bio_data = normalize_and_enrich(bio_data)

    # Step 6: Composition (Sonnet)
    wikitext = await generate_prose(bio_data, sources)

    # Step 7: Publishing
    if not DRY_RUN:
        await publish_to_mediawiki(person_name, wikitext)
    else:
        save_to_file(f".out/{person_name}.wikitext", wikitext)

    return bio_data
```

**Job Storage**: SQLite database (`app/storage/sqlite.py`, 24KB)
- Tracks job status (pending, running, completed, failed)
- Stores intermediate results
- Enables web UI progress tracking

---

## Entry Points

### 1. CLI: Single Person

**File**: `scripts/run_topic.py`

**Usage**:
```bash
cd ~/mozart-backup/mozart-people-extracted/mozart-people

# Dry-run (saves to .out/)
uv run python scripts/run_topic.py --topic "Jacques Vallée"

# Publish to wiki
uv run python scripts/run_topic.py --topic "Jacques Vallée" --publish
```

### 2. CLI: CSV Batch

**File**: `scripts/run_csv.py`

**Usage**:
```bash
# CSV format: topic,notes
# Example:
# Jacques Vallée,French-American ufologist
# Kit Green,CIA scientist

uv run python scripts/run_csv.py --csv people.csv --limit 5
uv run python scripts/run_csv.py --csv people.csv --publish
```

### 3. Web UI (FastAPI)

**File**: `app/web/main.py` (12KB)

**Usage**:
```bash
# Start server
make serve
# OR
uv run uvicorn app.web.main:app --host 0.0.0.0 --port 8001

# Visit: http://localhost:8001
```

**Features**:
- Dashboard with job stats
- Submit single person or CSV batch
- Real-time progress tracking
- Pipeline visualization (6 stages)
- Direct wiki links
- Error display

---

## Configuration

### Environment Variables (.env)

**Required**:
```bash
# LLM APIs
PPLX_API_KEY="pplx-..."              # Perplexity API key
BRAVE_API_KEY="BSA..."                # Brave Search API key
GEMINI_API_KEY="AIza..."              # Google Gemini API key
ANTHROPIC_API_KEY="sk-ant-..."        # Anthropic Claude API key

# MediaWiki
MEDIAWIKI_API_BASE="https://www.wikidisc.org/api.php"
MEDIAWIKI_USERNAME="Mozart"
MEDIAWIKI_PASSWORD="..."
MEDIAWIKI_OAUTH_TOKEN=""              # Optional

# Model Selection
EXTRACTION_MODEL="gemini-2.5-flash"
PROSE_MODEL="claude-sonnet-4-5-20250929"

# External Services
NOMINATIM_BASE="https://nominatim.openstreetmap.org"
GEONAMES_USERNAME="wikidiscorg"
CONTACT_EMAIL="ops@example.com"

# Pipeline Configuration
MAX_URLS_PER_TOPIC="40"
FETCH_CONCURRENCY="4"
DRY_RUN="false"                       # If true, saves to .out/ instead of publishing
```

### Dependencies (pyproject.toml)

**Core**:
- `httpx>=0.26` - HTTP client
- `pydantic>=2.6` - Data validation
- `jinja2>=3.1` - Template rendering
- `fastapi>=0.115` - Web framework
- `uvicorn>=0.30` - ASGI server
- `click>=8.1` - CLI framework

**Content Processing**:
- `trafilatura>=1.6` - HTML to text
- `pdfminer.six>=20231228` - PDF extraction
- `pdf2image>=1.17` - PDF to images
- `pillow>=10.0` - Image processing
- `pytesseract>=0.3.10` - OCR
- `playwright>=1.40` - Browser automation

**LLM APIs**:
- `google-generativeai>=0.5.3` - Gemini
- `anthropic>=0.25.9` - Claude

**Development**:
- `pytest>=7.4` - Testing
- `black>=24.3` - Formatting
- `ruff>=0.3` - Linting
- `mypy>=1.8` - Type checking

---

## Data Flow Example

### Input: "Jacques Vallée"

**Step 1: Discovery**
```python
# Perplexity query: "Who is Jacques Vallée? UFO researcher"
# Brave Search: "Jacques Vallée biography", "Jacques Vallée Wikipedia"
# Returns: 40 URLs (Wikipedia, news articles, interviews, books)
```

**Step 2: Ingestion**
```python
# Fetch 40 URLs concurrently (4 at a time)
# Extract text from each
# Result: 40 "evidence cards" with clean text
```

**Step 3: Ranking**
```python
# Score each source
# Wikipedia: 95/100 (authoritative, comprehensive)
# Personal website: 85/100 (primary source)
# Blog post: 60/100 (secondary source)
# Result: Sorted list of 40 sources
```

**Step 4: Extraction (Gemini)**
```python
# Send top 20 sources (4000 chars each) to Gemini
# Prompt: "Extract biographical information about Jacques Vallée"
# Result: JSON with 50+ fields
{
  "full_name": "Jacques Fabrice Vallée",
  "birth_date": "1939-09-24",
  "nationality": ["French", "American"],
  "primary_role": "Scientist/Academic",
  "occupation": "Computer scientist, ufologist, venture capitalist",
  "notable_for": "French-American computer scientist and prominent UFO researcher...",
  "credentials_verification": "Verified - Independently confirmed",
  "education": [
    "Ph.D.|Computer Science|Northwestern University|1967",
    "M.S.|Astrophysics|University of Lille|1962"
  ],
  "affiliations": ["NASA", "Stanford Research Institute", "SRI International"],
  "publications": [
    "Passport to Magonia|1969|Book",
    "Dimensions|1988|Book",
    "The Invisible College|1975|Book"
  ],
  ...
}
```

**Step 5: Normalization**
```python
# Validate dates: "1939-09-24" ✓
# Geocode birthplace: "Pontoise, France" → "49.0514, 2.0970"
# Enrich: Extract organizations from prose (NASA, SRI)
# Result: Validated and enriched JSON
```

**Step 6: Composition (Sonnet)**
```python
# Send bio_data + sources to Claude Sonnet
# Prompt: "Write comprehensive MediaWiki biography"
# Result: 4000-word wikitext with sections:
#   - Lead paragraphs
#   - == Early Life and Education ==
#   - == Career in Computer Science ==
#   - == UFO Research and Investigations ==
#   - == Publications ==
#   - == See Also ==
#   - == References ==
```

**Step 7: Publishing**
```python
# If DRY_RUN=false:
#   POST to MediaWiki API → create page
#   MediaWiki extension auto-creates Wikibase item (Q142)
# If DRY_RUN=true:
#   Save to .out/Jacques_Vallée.wikitext
```

**Output**: https://www.wikidisc.org/wiki/Jacques_Vallée

---

## Key Design Patterns

### 1. Verification-Aware Data Handling

**Problem**: UFO/UAP field has disputed claims and credentials

**Solution**: Explicit verification field + framing language

**Example**:
```json
// Extraction
{
  "credentials_verification": "Disputed - Claims challenged",
  "professional_background": "Claims to have worked at S-4 facility..."
}
```

```markdown
// Prose
Lazar **claims** to have worked at a facility called S-4...
His educational credentials have been **disputed**, with investigators
unable to verify attendance at MIT or Caltech.
```

### 2. Role-Aware Generation

**Problem**: Different person types need different article structures

**Solution**: Template selection based on `primary_role`

**Examples**:
- Scientists: Focus on research (60% of content)
- Government officials: Focus on legislation (50-60%)
- Whistleblowers: Require "Claims and Controversies" section

### 3. Multi-LLM Pipeline

**Problem**: Single model not optimal for all tasks

**Solution**: Use best model for each step
- Perplexity for research (real-time web)
- Gemini for extraction (fast, reliable JSON)
- Sonnet for prose (best quality)

### 4. Incremental Enrichment

**Problem**: LLM extraction may miss metadata

**Solution**: Post-extraction enrichment
1. Gemini extracts from sources
2. Regex extracts from generated prose
3. Geocoding enriches locations
4. Fallback fills gaps

### 5. Dry-Run Mode

**Problem**: Don't want to publish every test

**Solution**: `DRY_RUN` environment variable
- `true`: Save to `.out/*.wikitext` (local inspection)
- `false`: Publish to MediaWiki

---

## Integration Points for Your System

### What You Can Reuse Directly

**1. MediaWiki Publisher** (`app/publish/mediawiki.py`)
```python
# Copy to: integrations/publishing/mediawiki_publisher.py
# Zero changes needed - already production-ready
```

**2. Gemini Extraction Prompt** (`app/extraction/gemini_extractor.py`, lines 20-400)
```python
# Copy to: prompts/biography/person_extraction.j2
# Customize: Add your government database fields
```

**3. Sonnet Prose Prompt** (`app/compose/prose_sonnet.py`, lines 15-400)
```python
# Copy to: prompts/biography/person_prose.j2
# Customize: Adjust sections for your use case
```

**4. Person Schema** (`app/schemas/person.schema.json`)
```python
# Copy to: schemas/person_biography.schema.json
# Customize: Add/remove fields
```

### What You Can Skip (Already Have Equivalent)

**1. Discovery** - You have `deep_research.py`
- Mozart: Perplexity + Brave Search
- You: 15+ database integrations (better!)

**2. Extraction** - You have Gemini integration
- Mozart: Gemini 2.5 Flash
- You: Gemini 2.5 Flash (same!)

**3. Prose** - You have Claude integration
- Mozart: Claude Sonnet 4.5
- You: Claude Sonnet (same!)

### Integration Architecture

```python
# Your new biography_generator.py

from research.deep_research import DeepResearch
from integrations.publishing.mediawiki_publisher import MediaWikiPublisher
from llm_utils import acompletion
from core.prompt_loader import render_prompt

class BiographyGenerator:
    async def generate(self, person_name: str):
        # Step 1: Use YOUR deep research (better than Perplexity)
        results = await DeepResearch().research(
            question=f"Who is {person_name}?",
            max_tasks=3
        )

        # Step 2: Use MOZART's extraction prompt
        extraction_prompt = render_prompt(
            "biography/person_extraction.j2",  # COPIED from Mozart
            person_name=person_name,
            sources=results['synthesis']
        )

        bio_data = await acompletion(
            model="gemini/gemini-2.5-flash",
            messages=[{"role": "user", "content": extraction_prompt}],
            response_format={"type": "json_schema", ...}  # COPIED from Mozart
        )

        # Step 3: Use MOZART's prose prompt
        prose_prompt = render_prompt(
            "biography/person_prose.j2",  # COPIED from Mozart
            bio_data=bio_data,
            sources=results['synthesis']
        )

        wikitext = await acompletion(
            model="anthropic/claude-sonnet-4-5-20250929",
            messages=[{"role": "user", "content": prose_prompt}]
        )

        # Step 4: Use MOZART's publisher
        publisher = MediaWikiPublisher(...)  # COPIED from Mozart
        await publisher.create_page(person_name, wikitext)

        return bio_data
```

---

## Known Limitations

**From IMPROVEMENTS.md and SESSION_SUMMARY.md**:

1. **No human review** - LLM output published directly
2. **Source quality** - Heavy Wikipedia reliance
3. **OCR best-effort** - Failures fall back to plain text
4. **OAuth stubbed** - Uses bot passwords only
5. **Credentials verification** - Based on sources, needs manual fact-checking
6. **Positive bias** - LLMs tend toward positive tone
7. **Token limits** - 8000 max (increased from 2000, still constraining)

---

## Recent Improvements (October 2025)

**From IMPROVEMENTS.md**:

1. ✅ Fixed empty references (created `Template:Cite_web`)
2. ✅ Enhanced metadata extraction (Gemini prompts)
3. ✅ Added auto-geocoding (Nominatim)
4. ✅ Added metadata enrichment (regex extraction from prose)
5. ✅ Increased token limits (2000 → 8000)
6. ✅ Enhanced prose prompts (comprehensive sections)
7. ✅ Overhauled web UI (modern dashboard, pipeline visualization)

---

## Cost Analysis

**Per Biography** (~$0.10-0.50):
- Perplexity API: $0.05-0.15 (research)
- Brave Search API: $0.00 (free tier)
- Gemini 2.5 Flash: $0.01 (extraction)
- Claude Sonnet 4.5: $0.05-0.30 (prose)
- Nominatim: $0.00 (free)

**Monthly** (100 biographies/month): ~$10-50

---

## Usage Examples

### Example 1: Test Locally (Dry-Run)

```bash
cd ~/mozart-backup/mozart-people-extracted/mozart-people

# Install dependencies
uv venv
uv sync

# Test with dry-run
uv run python scripts/run_topic.py --topic "Jacques Vallée"

# Check output
cat .out/Jacques_Vallée.wikitext
```

### Example 2: Publish to Wiki

```bash
# Set environment
export DRY_RUN=false

# Publish
uv run python scripts/run_topic.py --topic "Jacques Vallée" --publish

# Check wiki
# Visit: https://www.wikidisc.org/wiki/Jacques_Vallée
```

### Example 3: Batch Processing

```bash
# Create CSV
cat > people.csv <<EOF
topic,notes
Jacques Vallée,French-American ufologist
Kit Green,CIA scientist
Bob Lazar,Controversial whistleblower
EOF

# Process batch
uv run python scripts/run_csv.py --csv people.csv --limit 3 --publish
```

### Example 4: Web UI

```bash
# Start server
make serve

# Visit http://localhost:8001
# Submit person name
# Watch real-time progress
# Click to view on wiki
```

---

## Security Notes

**SENSITIVE FILES**:
- `.env` - Contains API keys (DO NOT COMMIT)
- `logs/` - May contain PII
- `.out/` - Generated content (safe)

**API Keys in Backup**:
- Perplexity: `***REMOVED***`
- Brave: `REDACTED_BRAVE_KEY`
- Gemini: `REDACTED_GEMINI_KEY`
- Claude: `***REMOVED***`

**WARNING**: These are SignalsIntelligence's keys. For production:
1. Get your own API keys
2. Create your own `.env`
3. Never commit `.env` to git

---

## Summary for External LLM Planning

**What This System Does**:
- Automated person biography generation
- Multi-LLM pipeline (Perplexity → Gemini → Sonnet)
- MediaWiki publishing with Wikibase sync
- Production-ready (130+ pages created)

**What You Can Extract**:
- MediaWiki publisher (9KB, ready to copy)
- Gemini extraction prompt (verification-aware)
- Sonnet prose prompt (role-aware)
- Person JSON schema (50+ fields)

**What You Already Have**:
- Deep research system (better than Perplexity)
- Gemini integration (same model)
- Claude integration (same model)
- Knowledge graph generation

**Integration Effort**:
- Copy MediaWiki publisher: 2 hours
- Adapt prompts: 4 hours
- Build biography generator: 4 hours
- Total: ~10 hours

**Outcome**: Complete biography generation system using 60% existing code + 40% Mozart components.

---

**END OF TECHNICAL README**
