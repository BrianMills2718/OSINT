# Mozart Backup Inventory

**Date**: 2025-11-14
**Backup Location**: `~/mozart-backup/mozart-people-extracted/mozart-people/`
**Backup Size**: 728MB
**Status**: ✅ Complete - Full codebase successfully backed up

---

## What You Have

### ✅ Complete Source Code
- **app/** - All 19 Python modules
  - `compose/` - Prose generation (Claude Sonnet)
  - `extraction/` - Data extraction (Gemini)
  - `ingestion/` - Fetching (Perplexity, Brave Search, web scraping)
  - `normalize/` - Data normalization
  - `publish/` - MediaWiki API integration
  - `intake/` - CSV loader, CLI
  - `orchestrator/` - Main pipeline
  - `schemas/` - JSON schemas
  - `templates/` - MediaWiki templates
  - `web/` - FastAPI web UI

### ✅ API Credentials (from .env)
```bash
PPLX_API_KEY="***REMOVED***"
BRAVE_API_KEY="REDACTED_BRAVE_KEY"
GEMINI_API_KEY="REDACTED_GEMINI_KEY"
ANTHROPIC_API_KEY="***REMOVED***"
MEDIAWIKI_API_BASE="https://www.wikidisc.org/api.php"
MEDIAWIKI_USERNAME="Mozart"
MEDIAWIKI_PASSWORD="REDACTED_PASSWORD"
EXTRACTION_MODEL="gemini-2.5-flash"
PROSE_MODEL="claude-sonnet-4-5-20250929"
MAX_URLS_PER_TOPIC="40"
FETCH_CONCURRENCY="4"
```

**IMPORTANT**: These are SignalsIntelligence's API keys. You'll need to get your own for independent operation.

### ✅ Dependencies (pyproject.toml)
- httpx, pydantic, jinja2, fastapi, uvicorn
- trafilatura (HTML to text)
- pdfminer, pdf2image, pytesseract (PDF + OCR)
- google-generativeai (Gemini)
- anthropic (Claude)
- playwright (browser automation)

### ✅ Scripts
- `scripts/run_topic.py` - Single person biography
- `scripts/run_csv.py` - Batch CSV processing

### ✅ Documentation
- `README.md` - Quickstart guide
- `IMPROVEMENTS.md` - Enhancement ideas
- `SESSION_SUMMARY.md` - Development notes
- `WEB_IMPROVEMENTS_IMPLEMENTED.md` - Web UI changes
- `PHASE2_GAP_ANALYSIS.md` - Gap analysis

### ✅ Configuration
- `docker-compose.yml` - Docker setup
- `Makefile` - Build commands
- `.env` - API keys and settings

### ✅ Logs and Artifacts (729MB includes these)
- `logs/` - 12MB execution logs
- `.artifacts/` - 12MB build artifacts
- `.venv/` - Python virtual environment
- `.cache/`, `.uv-cache/` - Package caches

---

## How to Use This Backup

### Option 1: Run Mozart Directly (Use Their Keys)

**WARNING**: This uses SignalsIntelligence's API keys. Only for testing/learning.

```bash
cd ~/mozart-backup/mozart-people-extracted/mozart-people

# Install uv package manager (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment
uv venv
source .venv/bin/activate

# Install dependencies
uv sync

# Test with dry-run (doesn't publish, saves to .out/)
uv run python scripts/run_topic.py --topic "Jacques Vallée"

# Check output
cat .out/Jacques_Vallée.wikitext
```

### Option 2: Study and Replicate (Recommended)

**Extract key components to your codebase**:

1. **Read the prompts**:
   ```bash
   # Gemini extraction prompt
   grep -A 100 "SYSTEM (Gemini extraction" app/extraction/gemini_extractor.py

   # Sonnet prose prompt
   grep -A 100 "SYSTEM (Sonnet prose" app/compose/prose_sonnet.py
   ```

2. **Study the architecture**:
   - `app/ingestion/fetchers.py` - How they call Perplexity + Brave
   - `app/extraction/gemini_extractor.py` - Gemini extraction with schemas
   - `app/compose/prose_sonnet.py` - Claude prose generation
   - `app/publish/` - MediaWiki API integration

3. **Copy useful patterns**:
   - Verification-aware extraction (disputed claims handling)
   - Role-aware prose generation (different structures per person type)
   - Multi-LLM pipeline (best model for each task)

### Option 3: Get Your Own API Keys and Run Independently

**Required API Keys** (for full independence):

1. **Perplexity API** ($10/month)
   - Sign up: https://www.perplexity.ai/api
   - Alternative: Skip this, use your deep research system

2. **Brave Search API** (Free tier: 2,000 queries/month)
   - Sign up: https://brave.com/search/api/

3. **Your own Gemini key** (Already have)
4. **Your own Claude key** (Already have)

**Create your own .env**:
```bash
cd ~/mozart-backup/mozart-people-extracted/mozart-people
cp .env .env.backup
nano .env

# Replace with YOUR keys:
PPLX_API_KEY="your-perplexity-key"
BRAVE_API_KEY="your-brave-key"
GEMINI_API_KEY="your-gemini-key"
ANTHROPIC_API_KEY="your-claude-key"
MEDIAWIKI_API_BASE="http://localhost:8080/api.php"  # Your local wiki
MEDIAWIKI_USERNAME="YourBot"
MEDIAWIKI_PASSWORD="your-bot-password"
```

---

## Key Files to Study

### 1. Gemini Extraction (`app/extraction/gemini_extractor.py`)

**What to learn**:
- System prompt for verification-aware extraction
- JSON schema structure
- Safety settings for UAP/UFO topics
- Field extraction logic

**Line to read from**:
```bash
head -200 ~/mozart-backup/mozart-people-extracted/mozart-people/app/extraction/gemini_extractor.py
```

### 2. Sonnet Prose (`app/compose/prose_sonnet.py`)

**What to learn**:
- System prompt for role-aware prose
- Section structure variations (scientist vs whistleblower vs government official)
- Verification framing language
- MediaWiki formatting

**Line to read from**:
```bash
head -300 ~/mozart-backup/mozart-people-extracted/mozart-people/app/compose/prose_sonnet.py
```

### 3. Fetchers (`app/ingestion/fetchers.py`)

**What to learn**:
- How to call Perplexity API
- How to call Brave Search API
- Source ranking logic

**Read**:
```bash
cat ~/mozart-backup/mozart-people-extracted/mozart-people/app/ingestion/fetchers.py | head -200
```

### 4. Person Schema (`app/schemas/person.schema.json`)

**What to learn**:
- Complete field structure for person entities
- Validation rules
- Required vs optional fields

**Read**:
```bash
cat ~/mozart-backup/mozart-people-extracted/mozart-people/app/schemas/person.schema.json
```

### 5. MediaWiki Publisher (`app/publish/`)

**What to learn**:
- MediaWiki API authentication
- Page creation logic
- Edit token management

**Read**:
```bash
ls -la ~/mozart-backup/mozart-people-extracted/mozart-people/app/publish/
cat ~/mozart-backup/mozart-people-extracted/mozart-people/app/publish/*.py
```

---

## What to Build for Your System

Based on this backup, here's what you should build:

### 1. MediaWiki Publisher (2 hours)
**Copy from**: `app/publish/`
**Your file**: `integrations/publishing/mediawiki_publisher.py`

### 2. Brave Search Integration (1 hour)
**Copy from**: `app/ingestion/fetchers.py`
**Your file**: `integrations/search/brave_search_integration.py`

### 3. Biography Generator (4 hours)
**Pattern from**: Mozart's pipeline flow
**Your file**: `research/biography_generator.py`
**Combines**: Your deep_research + Gemini extraction + Sonnet prose

### 4. Person Schema (30 min)
**Copy from**: `app/schemas/person.schema.json`
**Your file**: `schemas/person_biography.schema.json`

---

## Next Steps

### TODAY (30 min)
1. ✅ Backup downloaded and extracted
2. **Read key files**:
   ```bash
   cd ~/mozart-backup/mozart-people-extracted/mozart-people
   cat README.md
   cat app/extraction/gemini_extractor.py | head -200
   cat app/compose/prose_sonnet.py | head -200
   ```

### THIS WEEKEND (8 hours)
1. **Study Mozart's architecture** (2 hours)
   - Read extraction, composition, publishing code
   - Understand multi-LLM pipeline flow

2. **Build MediaWiki publisher** (2 hours)
   - Adapt `app/publish/` to your system
   - Test against local MediaWiki

3. **Build biography generator** (4 hours)
   - Combine your deep research + Mozart's patterns
   - Test with "Jacques Vallée"

### NEXT WEEK (Optional)
1. Get your own API keys
2. Set up local MediaWiki
3. Full end-to-end test

---

## Files You Don't Need

**Safe to ignore** (bloat from backup):
- `.venv/` - Virtual environment (recreate with `uv venv`)
- `.cache/`, `.uv-cache/` - Package caches
- `.artifacts/` - Build artifacts
- `logs/` - Execution logs (interesting to read, but not needed)
- `*.log` - Log files

**To create a clean backup** (exclude bloat):
```bash
cd ~/mozart-backup/mozart-people-extracted
tar -czf ~/mozart-backup/mozart-people-clean.tar.gz \
  --exclude='mozart-people/.venv' \
  --exclude='mozart-people/.cache' \
  --exclude='mozart-people/.uv-cache' \
  --exclude='mozart-people/.artifacts' \
  --exclude='mozart-people/logs' \
  --exclude='mozart-people/*.log' \
  mozart-people

# Result: ~100MB instead of 728MB
```

---

## API Key Independence

**SignalsIntelligence's Keys** (from backup):
- Perplexity: `***REMOVED***`
- Brave Search: `REDACTED_BRAVE_KEY`
- Gemini: `REDACTED_GEMINI_KEY`
- Claude: `***REMOVED***`

**Your Keys** (for independence):
- ✅ Gemini: You already have your own
- ✅ Claude: You already have your own
- ❌ Perplexity: Need to get ($10/month or skip)
- ❌ Brave Search: Need to get (free tier available)

**Cost to replicate**: $0-10/month (Brave is free, Perplexity optional)

---

## Security Note

**IMPORTANT**: The .env file contains SignalsIntelligence's API keys. These should be:
1. **Kept confidential** - Don't share publicly
2. **Not used for production** - Get your own keys
3. **Used only for learning** - Study how they're configured

**For your own system**:
- Get your own API keys
- Create your own .env
- Never commit .env to git

---

## Success Metrics

**Backup Complete** ✅:
- 728MB Mozart codebase downloaded
- All source code present
- API keys documented
- Dependencies listed

**Next: Build Your Own** (1-2 weeks):
- Study Mozart's patterns
- Build equivalent components
- Deploy local MediaWiki
- Full independence achieved

---

**Status**: Backup complete, ready for study and replication
**Location**: `~/mozart-backup/mozart-people-extracted/mozart-people/`
**Next Step**: Study key files (extraction, composition, publishing)
**Timeline**: 1-2 weeks to full independence
