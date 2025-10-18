# Quick Start Guide

## 🚀 Run the App

```bash
streamlit run unified_search_app.py
```

Then open your browser to: http://localhost:8501

---

## 📋 What You Can Search

| Source | What | Auth Required |
|--------|------|---------------|
| 🏢 **ClearanceJobs** | Security clearance jobs | ❌ No |
| 📸 **DVIDS** | Military photos/videos/news | ✅ API key |
| 📋 **SAM.gov** | Government contracts | ✅ API key |
| 🤖 **AI Research** | Natural language search across all databases | ✅ OpenAI API key |

---

## 🔑 Get API Keys

**DVIDS:**
- Go to: https://www.dvidshub.net/
- Sign up and request API key
- Default provided: `key-68f319e8dc377`

**SAM.gov:**
- Go to: https://sam.gov
- Log in → Account Details → Request API Key

**OpenAI (for AI Research):**
- Go to: https://platform.openai.com/api-keys
- Create an API key
- **Option 1:** Create `.env` file:
  ```bash
  cp .env.example .env
  # Edit .env and add your key
  ```
- **Option 2:** Use Streamlit secrets:
  ```bash
  cp .streamlit/secrets.toml.example .streamlit/secrets.toml
  # Edit secrets.toml and add your key
  ```
- **Option 3:** Enter in sidebar (⚙️ Configuration → 🔑 API Keys)

---

## 👥 For Teams (3+ People)

**See the complete guide:** `TEAM_DEPLOYMENT_GUIDE.md`

Quick team setup:
1. Each member creates their own `.env` file (never commit to Git!)
2. For shared deployment, use Streamlit Cloud with secrets
3. Monitor API usage together

---

## 📁 Key Files

```
unified_search_app.py          Main app (run this!)
clearancejobs_search.py        CJ search logic
dvids_search.py                DVIDS search logic
sam_search.py                  SAM search logic
ai_research.py                 AI-powered research assistant
README.md                      Full documentation
```

---

## 🆘 Troubleshooting

**"No module named streamlit"**
```bash
pip install -r requirements.txt
```

**"No module named ClearanceJobs"**
```bash
cd ClearanceJobs && pip install -e . && cd ..
```

**Old version running?**
```bash
# Kill any running instances
pkill -f "streamlit run"

# Run the new version
streamlit run unified_search_app.py
```

**AI Research tab shows error about OpenAI API key?**
```bash
# Create .env file with your OpenAI API key
echo "OPENAI_API_KEY=your-key-here" > .env
```

---

## 📖 More Info

- **User Guide:** `README.md`
- **Technical Docs:** `INTEGRATION_ANALYSIS.md`
- **UX Improvements:** `UI_IMPROVEMENTS.md`
- **Cleanup Details:** `CLEANUP_SUMMARY.md`
