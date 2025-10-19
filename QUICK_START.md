# Quick Start Guide

## 🚀 Run the Applications

### Streamlit Web UI

```bash
streamlit run apps/unified_search_app.py
```

Then open your browser to: http://localhost:8501

### AI Research CLI

```bash
python3 apps/ai_research.py "Your research question here"
```

---

## 📋 What You Can Search

| Source | What | Auth Required |
|--------|------|---------------|
| 🤖 **AI Research** | Natural language search across all databases | ✅ OpenAI API key |
| 📋 **SAM.gov** | Federal government contracts | ✅ API key |
| 📸 **DVIDS** | Military photos/videos/news | ✅ API key |
| 💼 **USAJobs** | Federal government jobs | ✅ API key |
| 🏢 **ClearanceJobs** | Security clearance jobs | ✅ Puppeteer MCP |

---

## 🔑 Get API Keys

**1. OpenAI (for AI Research):**
- Go to: https://platform.openai.com/api-keys
- Create an API key
- Add to `.env` file:
  ```bash
  cp .env.example .env
  # Edit .env and add: OPENAI_API_KEY=your-key-here
  ```

**2. SAM.gov:**
- Go to: https://sam.gov
- Log in → Account Details → Request API Key
- Add to `.env`: `SAM_API_KEY=your-key-here`

**3. DVIDS:**
- Go to: https://www.dvidshub.net/
- Sign up and request API key
- Default provided: `key-68f319e8dc377` (for testing)
- Add to `.env`: `DVIDS_API_KEY=your-key-here`

**4. USAJobs:**
- Go to: https://developer.usajobs.gov/APIRequest/Index
- Request API key
- Add to `.env`: `USAJOBS_API_KEY=your-key-here`

**5. ClearanceJobs (Puppeteer):**
- Requires Puppeteer MCP server (no API key)
- See: `ClearanceJobs/PUPPETEER_FIX.md`

---

## 👥 For Teams (3+ People)

**See archived guide:** `docs/archive/TEAM_DEPLOYMENT_GUIDE.md`

Quick team setup:
1. Each member creates their own `.env` file (never commit to Git!)
2. Share `config.yaml` for consistent model/timeout settings
3. For shared deployment, use environment variables
4. Monitor API usage with cost tracking (see `CONFIG.md`)

---

## 📁 Key Files

```
apps/unified_search_app.py     Main Streamlit UI (web interface)
apps/ai_research.py            AI Research CLI (command line)
core/intelligent_executor.py   Full AI research system
core/agentic_executor.py       Self-improving search executor
integrations/*.py              Database integrations (SAM, DVIDS, etc.)
config_default.yaml            Configuration settings
README.md                      Full documentation
CLAUDE.md                      Development tasks
```

---

## 🆘 Troubleshooting

**"No module named X"**
```bash
pip install -r requirements.txt
```

**Import errors (ModuleNotFoundError)**
```bash
# Make sure you're in the repository root
cd /home/brian/sam_gov

# Imports use new paths:
from core.agentic_executor import AgenticExecutor  # ✅ Correct
from agentic_executor import AgenticExecutor       # ❌ Wrong
```

**"No OpenAI API key"**
```bash
# Create .env file with your API key
echo "OPENAI_API_KEY=your-key-here" > .env
```

**Old Streamlit version running?**
```bash
# Kill any running instances
pkill -f "streamlit run"

# Run the new version
streamlit run apps/unified_search_app.py
```

**Tests failing?**
```bash
# Run from repository root
cd /home/brian/sam_gov
python3 tests/test_intelligent_research.py
```

---

## 🧪 Testing

```bash
# Test AI Research CLI
python3 apps/ai_research.py "test query"

# Test Streamlit app
streamlit run apps/unified_search_app.py

# Run integration tests
python3 tests/test_4_databases.py
python3 tests/test_agentic_executor.py
```

---

## 📖 More Info

- **Full Documentation:** `README.md`
- **Configuration Guide:** `CONFIG.md`
- **Directory Structure:** `DIRECTORY_STRUCTURE.md`
- **Development Tasks:** `CLAUDE.md`
- **Historical Docs:** `docs/archive/`
