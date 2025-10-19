# Repository Reorganization Plan

## Proposed Directory Structure

```
sam_gov/
├── README.md                      # Main project README
├── QUICK_START.md                 # Quick start guide
├── CONFIG.md                      # Configuration documentation
├── requirements.txt               # Python dependencies
│
├── config_default.yaml            # Default configuration
├── config_loader.py               # Configuration loader
├── llm_utils.py                   # LLM utilities
│
├── core/                          # Core agentic search system
│   ├── __init__.py
│   ├── database_integration_base.py
│   ├── database_registry.py
│   ├── api_request_tracker.py
│   ├── parallel_executor.py
│   ├── agentic_executor.py
│   ├── intelligent_executor.py
│   ├── adaptive_analyzer.py
│   └── result_analyzer.py
│
├── integrations/                  # Database integrations (already organized)
│   ├── __init__.py
│   ├── sam_integration.py
│   ├── dvids_integration.py
│   ├── usajobs_integration.py
│   ├── clearancejobs_integration.py
│   └── clearancejobs_puppeteer.py
│
├── apps/                          # User-facing applications
│   ├── unified_search_app.py      # Streamlit app
│   └── ai_research.py             # CLI app
│
├── tests/                         # All test files
│   ├── test_intelligent_research.py
│   ├── test_agentic_executor.py
│   ├── test_4_databases.py
│   ├── test_new_architecture.py
│   ├── test_simple_queries.py
│   ├── test_refinement_direct.py
│   ├── test_apis_direct.py
│   ├── test_tracker.py
│   ├── test_clearancejobs_only.py
│   └── test_clearancejobs_puppeteer.py
│
├── scripts/                       # Utility scripts
│   ├── migrate_to_gpt5mini.sh
│   └── update_to_use_config.py
│
├── experiments/                   # Experimental/research code
│   ├── tag_management/            # Tag normalization experiments
│   │   ├── batch_tag_articles.py
│   │   ├── normalize_tags_2plus.py
│   │   ├── categorize_*.py
│   │   └── *.json (tag data)
│   │
│   ├── scrapers/                  # Standalone scrapers
│   │   ├── dvids.py
│   │   ├── sam_search.py
│   │   ├── dvids_search.py
│   │   ├── clearancejobs_search.py
│   │   ├── bills_blackbox_scraper.py
│   │   └── klippenstein_scraper.py
│   │
│   └── discord/                   # Discord-related tools
│       ├── discord_server_manager.py
│       ├── discord_servers.json
│       └── strip_discord_json.py
│
├── data/                          # Data files (gitignored)
│   ├── articles/
│   ├── exports/
│   ├── logs/
│   └── *.json (data files)
│
├── docs/                          # Historical documentation
│   ├── archive/
│   │   ├── *_SUMMARY.md
│   │   ├── *_GUIDE.md
│   │   ├── *_PLAN.md
│   │   └── *_WORKFLOW.md
│   └── examples/                  # LLM research examples
│       └── llm_research_examples/
│
├── ClearanceJobs/                 # External submodule (keep as-is)
│
└── .gitignore                     # Updated gitignore
```

## Migration Steps

1. Create new directory structure
2. Move files to appropriate locations
3. Update imports in Python files
4. Update .gitignore
5. Test that everything still works
6. Commit reorganization

## What Gets Moved Where

### Core System → `core/`
- database_integration_base.py
- database_registry.py
- api_request_tracker.py
- parallel_executor.py
- agentic_executor.py
- intelligent_executor.py
- adaptive_analyzer.py
- result_analyzer.py

### Applications → `apps/`
- unified_search_app.py
- ai_research.py

### Tests → `tests/`
- test_*.py files

### Scripts → `scripts/`
- migrate_to_gpt5mini.sh
- update_to_use_config.py

### Experiments → `experiments/`
- Tag management files → `experiments/tag_management/`
- Scrapers → `experiments/scrapers/`
- Discord tools → `experiments/discord/`

### Data → `data/` (gitignored)
- *.json (except config)
- *.log
- *_articles/
- exports/

### Docs → `docs/`
- Historical docs → `docs/archive/`
- LLM examples → `docs/examples/`

## Benefits

1. **Clear separation** - Core system vs experiments vs tests
2. **Easy navigation** - Know where to find things
3. **Clean imports** - `from core.agentic_executor import AgenticExecutor`
4. **Scalability** - Easy to add new components
5. **Git cleanliness** - Data files properly gitignored
