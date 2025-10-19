# Directory Structure

## Overview

The repository is now organized into clear, functional directories:

```
sam_gov/
├── 📚 Documentation
│   ├── README.md                   # Main project overview
│   ├── QUICK_START.md              # Quick start guide
│   ├── CONFIG.md                   # Configuration documentation
│   └── DIRECTORY_STRUCTURE.md      # This file
│
├── ⚙️  Configuration
│   ├── config_default.yaml         # Default configuration
│   ├── config_loader.py            # Configuration loader
│   └── llm_utils.py                # LLM utilities
│
├── 🔧 Core System (core/)
│   ├── database_integration_base.py   # Base class for integrations
│   ├── database_registry.py           # Database registry
│   ├── api_request_tracker.py         # API call tracking/logging
│   ├── parallel_executor.py           # Parallel search execution
│   ├── agentic_executor.py            # Self-improving executor
│   ├── intelligent_executor.py        # Full AI research assistant
│   ├── adaptive_analyzer.py           # Code-based analysis (Ditto-style)
│   └── result_analyzer.py             # Result analysis & synthesis
│
├── 🔌 Database Integrations (integrations/)
│   ├── sam_integration.py             # SAM.gov federal contracts
│   ├── dvids_integration.py           # Military media/news
│   ├── usajobs_integration.py         # Federal job listings
│   ├── clearancejobs_integration.py   # Security clearance jobs
│   └── clearancejobs_puppeteer.py     # ClearanceJobs scraper
│
├── 🖥️  Applications (apps/)
│   ├── unified_search_app.py          # Streamlit web UI
│   └── ai_research.py                 # CLI application
│
├── 🧪 Tests (tests/)
│   ├── test_intelligent_research.py   # Integration test
│   ├── test_agentic_executor.py       # Executor test
│   ├── test_4_databases.py            # Multi-database test
│   └── ...                            # Other tests
│
├── 🛠️  Scripts (scripts/)
│   ├── migrate_to_gpt5mini.sh         # Migration script
│   └── update_to_use_config.py        # Config migration
│
├── 🧬 Experiments (experiments/)
│   ├── tag_management/                # Tag normalization experiments
│   ├── scrapers/                      # Standalone scrapers
│   └── discord/                       # Discord tools
│
├── 💾 Data (data/ - gitignored)
│   ├── articles/                      # Article data
│   ├── exports/                       # Export files
│   └── logs/                          # Log files
│
├── 📖 Docs (docs/)
│   ├── archive/                       # Historical documentation
│   └── examples/                      # Code examples
│
└── 📦 Dependencies
    ├── requirements.txt               # Python dependencies
    ├── ClearanceJobs/                 # External library
    └── .gitignore                     # Git exclusions
```

## Key Directories

### Core System (`core/`)
The heart of the agentic search system. Contains:
- **Executors**: Parallel, agentic, and intelligent executors
- **Analyzers**: Adaptive code generation and result synthesis
- **Base classes**: Database integration interfaces
- **Utilities**: API tracking, logging

### Integrations (`integrations/`)
Database-specific implementations. Each integration:
- Extends `DatabaseIntegration` base class
- Implements `generate_query()` and `execute_search()`
- Uses config for models and timeouts
- Returns standardized `QueryResult`

### Applications (`apps/`)
User-facing applications:
- **Streamlit UI**: Web interface for searches
- **CLI**: Command-line research tool

### Tests (`tests/`)
All test files. Run with:
```bash
python3 tests/test_intelligent_research.py
```

### Experiments (`experiments/`)
Research code and experimental features. Not part of core system.

### Data (`data/`)
All data files (gitignored). Includes:
- Raw article data
- Export files
- Log files
- Generated results

## Import Paths

With the new structure, imports use module paths:

```python
# Core system
from core.agentic_executor import AgenticExecutor
from core.database_integration_base import DatabaseIntegration

# Integrations
from integrations.sam_integration import SAMIntegration

# Config
from config_loader import config

# LLM utilities
from llm_utils import acompletion
```

## Running the System

### From Repository Root
```bash
# Run tests
python3 tests/test_intelligent_research.py

# Run Streamlit app
streamlit run apps/unified_search_app.py

# Run CLI
python3 apps/ai_research.py
```

### Imports Work From Anywhere
Python path is set up so imports work from repo root:
```bash
cd /home/brian/sam_gov
python3 -c "from core.agentic_executor import AgenticExecutor"
```

## Benefits of New Structure

1. **Clear Separation**
   - Core system vs experiments
   - Tests vs production code
   - Data vs code

2. **Easy Navigation**
   - Know where every file belongs
   - Logical grouping of related code

3. **Scalable**
   - Easy to add new integrations
   - Easy to add new tests
   - Easy to add new experiments

4. **Clean Git**
   - Data files properly ignored
   - No clutter in root directory
   - Clear commit diffs

5. **Professional**
   - Industry-standard structure
   - Easy for others to understand
   - Ready for open source

## Migration Notes

If you have old code that uses old import paths:

**Old imports:**
```python
from database_integration_base import DatabaseIntegration
from agentic_executor import AgenticExecutor
```

**New imports:**
```python
from core.database_integration_base import DatabaseIntegration
from core.agentic_executor import AgenticExecutor
```

All existing code has been updated to use new paths.
