# SigInt Platform - AI-Powered Investigative Research

An advanced multi-source intelligence platform for investigative journalism and research. Uses LLM-driven hypothesis generation, 29 data source integrations, and automated report synthesis.

## Features

### Deep Research Engine
- **Natural language queries** - Ask complex investigative questions in plain English
- **Hypothesis branching** - LLM generates 3-5 investigative hypotheses per task
- **Multi-source orchestration** - Automatically queries relevant sources from 29 integrations
- **Entity extraction** - Identifies people, organizations, and relationships
- **Report synthesis** - Generates comprehensive markdown reports with citations
- **Cost tracking** - Monitors LLM API usage and costs

### 29 Data Source Integrations

**Government (15)**:
- SAM.gov - Federal contract opportunities
- USAspending.gov - Awarded federal contracts and spending
- DVIDS - U.S. military photos, videos, and news
- USAJobs - Federal government job listings
- ClearanceJobs - Security clearance job search (HTTP scraper)
- Federal Register - Federal regulations and notices
- Congress.gov - Bills, laws, and congressional activity
- GovInfo - GAO reports, IG audits, congressional hearings
- SEC EDGAR - Corporate filings and financial data
- FEC - Campaign finance and political donations
- CREST - CIA declassified documents
- FBI Vault - FBI declassified records
- CourtListener - Federal court opinions
- ProPublica Nonprofit - Tax-exempt organization data
- ICIJ Offshore Leaks - Panama Papers, offshore entities

**Social Media (4)**:
- Twitter - 20 API endpoints (search, timelines, followers, etc.)
- Reddit - Subreddit search and posts
- Discord - Local export search
- Telegram - Channel search and messages

**News & Web (2)**:
- NewsAPI - 80,000+ news sources worldwide
- Brave Search - Web search with freshness filtering

**Archive (1)**:
- Wayback Machine - Historical web page snapshots

## Quick Start

### 1. Install Dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure API Keys

```bash
cp .env.example .env
# Edit .env with your API keys
```

Required keys:
- `OPENAI_API_KEY` - For LLM query generation and synthesis
- `SAM_API_KEY` - SAM.gov contracts
- `USAJOBS_API_KEY` - Federal jobs

Optional keys for additional sources:
- `DVIDS_API_KEY`, `NEWSAPI_KEY`, `BRAVE_API_KEY`
- `FEC_API_KEY`, `DATA_GOV_API_KEY`
- `REDDIT_CLIENT_ID/SECRET`, `RAPIDAPI_KEY` (Twitter)

### 3. Run Research

**CLI (Recommended)**:
```bash
source .venv/bin/activate
python3 run_research_cli.py "What defense contracts were awarded for AI in 2024?"
```

**With options**:
```bash
python3 run_research_cli.py \
  --max-tasks 5 \
  --max-time-minutes 30 \
  "Investigate Lockheed Martin lobbying and campaign contributions"
```

**Streamlit Web UI**:
```bash
streamlit run apps/unified_search_app.py
```

## Configuration

Edit `config.yaml` to customize:

```yaml
research:
  max_tasks: 5                    # Max research tasks per query
  max_time_minutes: 45            # Total time budget
  max_queries_per_source: 5       # Queries before saturation
  hypothesis_branching: true      # Enable investigative hypotheses

llm:
  model: "gpt-4o-mini"           # Primary model
  fallback_model: "gemini-2.5-flash"
  timeout: 180                    # LLM call timeout (seconds)
```

## Output

Research results are saved to `data/research_output/`:

```
data/research_output/YYYY-MM-DD_HH-MM-SS_query/
├── report.md           # Final markdown report with citations
├── results.json        # All results with metadata
├── metadata.json       # Run configuration and statistics
├── execution_log.jsonl # Detailed execution trace
└── raw/                # Raw API responses
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User Query                                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Task Decomposition LLM                          │
│         Breaks query into 3-5 research tasks                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              For each task:                                  │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Hypothesis Generation LLM → 3-5 investigative angles   │ │
│  └────────────────────────────────────────────────────────┘ │
│                            │                                 │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Source Selection LLM → Choose relevant databases        │ │
│  └────────────────────────────────────────────────────────┘ │
│                            │                                 │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Query Generation LLM → Source-specific queries          │ │
│  └────────────────────────────────────────────────────────┘ │
│                            │                                 │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Source Execution → Parallel API calls to databases      │ │
│  └────────────────────────────────────────────────────────┘ │
│                            │                                 │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Relevance Filter LLM → Keep only relevant results       │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Report Synthesis LLM                            │
│    Entity extraction, relationship mapping, citations        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Markdown Report with Sources                    │
└─────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
sam_gov/
├── apps/                    # User entry points
│   ├── ai_research.py       # Legacy CLI
│   └── unified_search_app.py # Streamlit web UI
├── run_research_cli.py      # Primary CLI entry point
├── research/                # Deep research engine
│   ├── deep_research.py     # Main orchestrator (4,392 lines)
│   └── mixins/              # Modular components
├── integrations/            # 29 data source adapters
│   ├── government/          # SAM, DVIDS, USAJobs, etc.
│   ├── social/              # Twitter, Reddit, Discord
│   └── registry.py          # Integration registry
├── prompts/                 # Jinja2 LLM prompt templates
│   ├── deep_research/       # Research prompts
│   └── integrations/        # Source-specific prompts
├── core/                    # Shared utilities
│   └── prompt_loader.py     # Jinja2 template engine
├── data/                    # Runtime data
│   ├── research_output/     # Generated reports
│   └── exports/             # Discord/Telegram exports
├── tests/                   # Test suites
├── config.yaml              # User configuration
├── .env                     # API keys (gitignored)
└── llm_utils.py             # LLM call wrapper
```

## Example Queries

**Defense Contracting**:
```bash
python3 run_research_cli.py "What AI contracts has the Pentagon awarded in 2024?"
```

**Campaign Finance**:
```bash
python3 run_research_cli.py "Track Lockheed Martin campaign contributions and lobbying"
```

**Investigative Lead Generation**:
```bash
python3 run_research_cli.py \
  --max-tasks 8 \
  --max-time-minutes 60 \
  "Find patterns of no-bid contracts or revolving door hires in defense AI"
```

## Development

**Run tests**:
```bash
source .venv/bin/activate
python3 tests/test_deep_research_full.py
```

**Add a new integration**:
1. Copy `integrations/_integration_template.py`
2. Implement required methods (`is_relevant`, `generate_query`, `execute_search`)
3. Create prompt template in `prompts/integrations/`
4. Register in `integrations/registry.py`
5. Test with `python3 tests/test_<source>_live.py`

## Documentation

- **CLAUDE.md** - Development guide and principles
- **STATUS.md** - Current system status and recent changes
- **ROADMAP.md** - Implementation roadmap
- **PATTERNS.md** - Code patterns and conventions
- **INVESTIGATIVE_PLATFORM_VISION.md** - Long-term vision (75 pages)

## Known Limitations

1. **Brave Search** - Rate limited (429 errors on heavy use)
2. **SAM.gov** - Low rate limits, handled gracefully
3. **NewsAPI Free Tier** - 30-day article limit
4. **Some sources** - Require specific API keys

## License

For legitimate research purposes only. Respect all API terms of service.
