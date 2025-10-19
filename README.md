# Unified Multi-Source Search Application

A comprehensive agentic search system with both Streamlit UI and CLI interfaces that integrates four powerful data sources:
- **SAM.gov** - Federal government contract opportunities
- **DVIDS** - U.S. military photos, videos, and news
- **USAJobs** - Federal government job listings
- **ClearanceJobs** - Security clearance job search (via Puppeteer)

## Features

### 🤖 AI Research Assistant (NEW)
- **Natural language queries** - Ask questions in plain English
- **Multi-database search** - Automatically searches all relevant databases
- **Agentic refinement** - Self-improves queries based on results
- **Result synthesis** - Combines results into coherent answers
- **Configurable LLM** - Uses gpt-5-mini by default, supports 100+ models via LiteLLM
- **Cost tracking** - Monitors API usage and costs

### 📋 SAM.gov
- Search federal government contract opportunities
- **Required**: Posted date range (max 1 year)
- Filter by procurement type (solicitation, presolicitation, etc.)
- 18 set-aside types (Small Business, 8(a), SDVOSB, etc.)
- NAICS and PSC classification codes
- Organization, state, and ZIP code filters
- Response deadline filtering
- CSV/JSON export

### 📸 DVIDS
- Search U.S. military photos, videos, news, and media
- Filter by military branch, country, state, city
- Date range filtering
- Media type selection (image, video, audio, news, etc.)
- Advanced filters: aspect ratio, HD quality, captions
- Combatant command and unit filters
- CSV/JSON export with image thumbnails

### 💼 USAJobs
- Search official federal government job listings
- Filter by keywords, location, organization
- GS pay grade filtering (1-15)
- All federal agencies and departments
- CSV/JSON export

### 🏢 ClearanceJobs (Puppeteer-based)
- Search by keywords for security clearance jobs
- **Note**: Uses Puppeteer web scraping (API is broken)
- Requires Puppeteer MCP server
- Returns relevant results (vs 57k irrelevant from API)

## Installation

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure API keys:**

   Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

   Edit `.env` and add your API keys:
   ```bash
   OPENAI_API_KEY=your-openai-key-here
   SAM_API_KEY=your-sam-gov-key
   DVIDS_API_KEY=your-dvids-key
   USAJOBS_API_KEY=your-usajobs-key
   ```

3. **(Optional) Customize configuration:**
   ```bash
   cp config_default.yaml config.yaml
   # Edit config.yaml to change models, timeouts, etc.
   ```

## Running the Applications

### Streamlit Web UI

```bash
streamlit run apps/unified_search_app.py
```

The app will open in your browser at `http://localhost:8501`

### AI Research CLI

```bash
# Natural language research query
python3 apps/ai_research.py "What cybersecurity contracts are available from DoD?"

# With custom config
python3 apps/ai_research.py "Recent data science jobs in DC" --config config.yaml
```

## API Keys

### OpenAI (for AI Research)
- **Required**: Yes (for AI Research features)
- **Get your key**: https://platform.openai.com/api-keys
- **Used for**: Query generation, refinement, result synthesis
- **Default model**: gpt-5-mini (configurable)

### SAM.gov
- **Required**: Yes (for contract searches)
- **Get your key**: https://sam.gov
  - Log in to your account
  - Go to Account Details
  - Request API Key

### DVIDS
- **Required**: Yes (for military media searches)
- **Get your key**: https://www.dvidshub.net/
- **Default key provided**: `key-68f319e8dc377` (for testing)

### USAJobs
- **Required**: Yes (for federal job searches)
- **Get your key**: https://developer.usajobs.gov/APIRequest/Index
- **Requires**: Email in User-Agent header

### ClearanceJobs
- **Required**: No (Puppeteer MCP server required instead)
- **Note**: Python API library is broken, use Puppeteer integration
- **See**: `ClearanceJobs/PUPPETEER_FIX.md`

## Usage

### Search Tips

**ClearanceJobs:**
- Use specific keywords: "cybersecurity analyst", "network engineer"
- Combine clearance filters for targeted results
- Filter by major defense hubs: Maryland, Virginia, DC, California, Colorado

**DVIDS:**
- Search is optional - leave blank to browse all recent media
- Combine media types to get photos + videos
- Use date ranges for recent operations or historical content
- HD filter works best with videos

**SAM.gov:**
- **Date range is MANDATORY** (max 1 year)
- Use NAICS codes for specific industries (e.g., 541512 = Computer Systems Design)
- Set-aside filter helps small businesses find targeted opportunities
- Response deadline filters show upcoming opportunities

### Advanced Features

**Pagination:**
- All sources support pagination
- ClearanceJobs: No limit
- DVIDS: Max 1000 results (20 pages @ 50/page)
- SAM.gov: No limit (1000/page max)

**Export Options:**
- CSV: Tabular data for Excel/analysis
- JSON: Complete API responses with all fields

**Rate Limiting:**
- Enable in sidebar to avoid hitting API limits
- 1 second delay between ClearanceJobs/SAM.gov searches
- 0.5 second delay for DVIDS

## Directory Structure

```
sam_gov/
├── 📚 Documentation
│   ├── README.md                   # This file
│   ├── QUICK_START.md              # Quick start guide
│   ├── CONFIG.md                   # Configuration guide
│   ├── DIRECTORY_STRUCTURE.md      # Directory layout
│   └── CLAUDE.md                   # Development tasks
│
├── ⚙️  Configuration
│   ├── config_default.yaml         # Default configuration
│   ├── config_loader.py            # Configuration loader
│   └── llm_utils.py                # LLM utilities
│
├── 🔧 Core System (core/)
│   ├── database_integration_base.py   # Base class for integrations
│   ├── database_registry.py           # Database registry
│   ├── parallel_executor.py           # Parallel search execution
│   ├── agentic_executor.py            # Self-improving executor
│   ├── intelligent_executor.py        # Full AI research assistant
│   ├── adaptive_analyzer.py           # Code-based analysis
│   └── result_analyzer.py             # Result synthesis
│
├── 🔌 Database Integrations (integrations/)
│   ├── sam_integration.py             # SAM.gov federal contracts
│   ├── dvids_integration.py           # Military media/news
│   ├── usajobs_integration.py         # Federal job listings
│   ├── clearancejobs_integration.py   # Security clearance jobs (API)
│   └── clearancejobs_puppeteer.py     # ClearanceJobs scraper (working)
│
├── 🖥️  Applications (apps/)
│   ├── unified_search_app.py          # Streamlit web UI
│   └── ai_research.py                 # CLI application
│
├── 🧪 Tests (tests/)
│   ├── test_intelligent_research.py   # Full integration test
│   ├── test_agentic_executor.py       # Executor tests
│   ├── test_4_databases.py            # Multi-database test
│   └── test_clearancejobs_puppeteer.py # Puppeteer test
│
├── 🛠️  Scripts (scripts/)
│   └── migrate_to_gpt5mini.sh         # Model migration
│
└── 🧬 Experiments (experiments/)
    ├── tag_management/                # Tag experiments
    ├── scrapers/                      # Standalone scrapers
    └── discord/                       # Discord tools
```

**Import Paths:**
```python
# Core system
from core.agentic_executor import AgenticExecutor
from core.intelligent_executor import IntelligentExecutor

# Integrations
from integrations.sam_integration import SAMIntegration

# Config and utilities
from config_loader import config
from llm_utils import acompletion
```

## Troubleshooting

### "No module named X"
```bash
pip install -r requirements.txt
```

### Import errors after reorganization
Make sure you're using new import paths:
```python
# Old (broken)
from agentic_executor import AgenticExecutor

# New (correct)
from core.agentic_executor import AgenticExecutor
```

### AI Research returns "No OpenAI API key"
Create `.env` file with your key:
```bash
echo "OPENAI_API_KEY=your-key-here" > .env
```

### SAM.gov returns "PostedFrom and PostedTo are mandatory"
- SAM.gov requires a date range (max 1 year)
- Make sure both date fields are filled

### Configuration not loading
- Check `config_default.yaml` exists
- Custom config should be `config.yaml` (not tracked by git)
- Environment variables override config file

### Tests failing
Run tests from repository root:
```bash
cd /home/brian/sam_gov
python3 tests/test_intelligent_research.py
```

## API Limits

| API | Max Results/Page | Total Limit | Rate Limit | Cost |
|-----|------------------|-------------|------------|------|
| SAM.gov | 1000 | None | Unknown (strict) | Free |
| DVIDS | 50 | 1000 | Unknown | Free |
| USAJobs | 500 | None | Unknown | Free |
| ClearanceJobs | N/A (Puppeteer) | Unlimited | Manual scraping | Free |
| OpenAI (gpt-5-mini) | N/A | Usage-based | Standard API | ~$0.001-0.01/query |

## Configuration

The system is fully configurable via `config.yaml`:

- **LLM Models**: Change query generation, analysis, synthesis models
- **Timeouts**: Adjust API and LLM request timeouts
- **Execution**: Max concurrent searches, refinement iterations
- **Provider Fallback**: Auto-retry with alternative models
- **Cost Management**: Set budget limits and cost tracking

See `CONFIG.md` for detailed configuration guide.

## Testing

```bash
# Run full integration test
python3 tests/test_intelligent_research.py

# Test specific database
python3 tests/test_4_databases.py

# Test agentic refinement
python3 tests/test_agentic_executor.py

# Test Puppeteer integration
python3 tests/test_clearancejobs_puppeteer.py
```

## Known Limitations

1. **ClearanceJobs**: Python API broken, requires Puppeteer MCP server
2. **DVIDS**: Maximum 1000 total results per search
3. **SAM.gov**: Date range limited to 1 year, strict rate limits
4. **USAJobs**: Requires specific User-Agent header format

## Documentation

- **Quick Start**: `QUICK_START.md` - Get up and running fast
- **Configuration**: `CONFIG.md` - Configure models and providers
- **Directory Layout**: `DIRECTORY_STRUCTURE.md` - Understand the codebase
- **Development Tasks**: `CLAUDE.md` - Ongoing development work
- **Historical Docs**: `docs/archive/` - Previous documentation

## Credits

- **SAM.gov API**: https://open.gsa.gov/api/get-opportunities-public-api/
- **DVIDS API**: https://api.dvidshub.net/docs
- **USAJobs API**: https://developer.usajobs.gov/
- **ClearanceJobs**: https://www.clearancejobs.com/
- **LiteLLM**: https://github.com/BerriAI/litellm

## License

This tool is for legitimate research purposes only. Respect all API terms of service and rate limits. Do not use for unauthorized scraping or commercial purposes without proper authorization.
