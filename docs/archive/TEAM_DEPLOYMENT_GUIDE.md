# Team Deployment Guide

**For team members deploying and using the unified search application**

---

## 🎯 Overview

This application provides unified search across:
- **ClearanceJobs** - Security clearance job postings (no API key needed)
- **DVIDS** - Military media (photos, videos, news)
- **SAM.gov** - Government contract opportunities
- **AI Research** - Natural language research across all databases

---

## 👥 Team Setup (3 Options)

### Option 1: Local Development (.env file) ⭐ **Recommended for Development**

Each team member creates their own `.env` file:

**Setup:**
```bash
# 1. Navigate to project directory
cd /path/to/sam_gov

# 2. Create .env file from example
cp .env.example .env

# 3. Edit .env and add your API keys
nano .env
```

**Your `.env` file should contain:**
```bash
OPENAI_API_KEY=sk-proj-your-actual-key-here
```

**Advantages:**
- ✅ Each team member has their own keys
- ✅ Keys never committed to Git (in .gitignore)
- ✅ Easy to update keys locally
- ✅ Works offline

**Usage:**
```bash
streamlit run unified_search_app.py
```

---

### Option 2: Streamlit Secrets (Local) ⭐ **Recommended for Consistency**

Use Streamlit's native secrets management:

**Setup:**
```bash
# 1. Navigate to project directory
cd /path/to/sam_gov

# 2. Create secrets file from example
cp .streamlit/secrets.toml.example .streamlit/secrets.toml

# 3. Edit secrets and add your API keys
nano .streamlit/secrets.toml
```

**Your `.streamlit/secrets.toml` file should contain:**
```toml
OPENAI_API_KEY = "sk-proj-your-actual-key-here"

# Optional: Add other API keys
# DVIDS_API_KEY = "your-dvids-key"
# SAM_GOV_API_KEY = "your-sam-gov-key"
```

**Advantages:**
- ✅ Consistent with Streamlit Cloud deployment
- ✅ Never committed to Git (in .gitignore)
- ✅ Can store all API keys in one place
- ✅ Native Streamlit integration

**Usage:**
```bash
streamlit run unified_search_app.py
```

---

### Option 3: UI Input (No Configuration Files)

Enter API keys directly in the application sidebar:

**Setup:**
1. Run the app: `streamlit run unified_search_app.py`
2. Open sidebar (top-left corner)
3. Expand "🔑 API Keys"
4. Enter your OpenAI API key

**Advantages:**
- ✅ No file configuration needed
- ✅ Quick testing
- ✅ Can override .env or secrets

**Disadvantages:**
- ❌ Need to re-enter keys every time you restart the app
- ❌ Keys stored in browser session only

---

## 🔑 Getting API Keys

### OpenAI API Key (Required for AI Research)

1. Go to: https://platform.openai.com/api-keys
2. Sign in or create an account
3. Click "Create new secret key"
4. Copy the key (starts with `sk-proj-...`)
5. Add to your `.env` or `.streamlit/secrets.toml`

**Cost Estimate:**
- ~$0.01-0.05 per AI research query
- Uses gpt-5-mini model (economical)

### DVIDS API Key (Optional - for military media)

1. Go to: https://www.dvidshub.net/
2. Sign up for an account
3. Request an API key
4. Add to your configuration

**Default:** `key-68f319e8dc377` (public demo key)

### SAM.gov API Key (Optional - for government contracts)

1. Go to: https://sam.gov
2. Log in to your account
3. Navigate to: Account Details → API Key
4. Request an API key
5. Add to your configuration

---

## 🚀 Deployment to Streamlit Cloud

**For production deployment (accessible to all team members):**

### Step 1: Push to GitHub

```bash
# Make sure secrets are NOT committed
git status  # Should NOT show .env or secrets.toml

# Commit and push
git add .
git commit -m "Add unified search app with AI research"
git push origin main
```

### Step 2: Deploy to Streamlit Cloud

1. Go to: https://share.streamlit.io/
2. Sign in with GitHub
3. Click "New app"
4. Select your repository
5. Set:
   - **Main file path:** `unified_search_app.py`
   - **Python version:** 3.9 or higher

### Step 3: Configure Secrets in Streamlit Cloud

1. In Streamlit Cloud dashboard, click your app
2. Click "Settings" (⚙️) → "Secrets"
3. Add your secrets in TOML format:

```toml
OPENAI_API_KEY = "sk-proj-your-actual-key-here"

# Optional: Add shared team keys
# DVIDS_API_KEY = "your-dvids-key"
# SAM_GOV_API_KEY = "your-sam-gov-key"
```

4. Click "Save"
5. App will automatically restart with secrets

### Step 4: Share with Team

Share the Streamlit Cloud URL with your team:
```
https://your-app-name.streamlit.app
```

**Important:**
- ⚠️ One set of API keys for all team members
- ⚠️ Monitor OpenAI usage (all team queries use same key)
- ⚠️ Consider usage limits and costs

---

## 🔒 Security Best Practices

### ✅ DO:
- Use `.env` or `.streamlit/secrets.toml` for local development
- Keep API keys private (never commit to Git)
- Use separate API keys for dev/prod if possible
- Monitor API usage regularly
- Rotate keys periodically

### ❌ DON'T:
- Never commit `.env` or `secrets.toml` to Git
- Never share API keys in Slack/email/docs
- Never hardcode API keys in Python files
- Don't use production keys for testing

---

## 📁 File Organization

**Configuration files** (each team member creates their own):
```
sam_gov/
├── .env                          # Your local API keys (gitignored)
├── .streamlit/
│   ├── secrets.toml              # Alternative to .env (gitignored)
│   └── secrets.toml.example      # Template (committed)
└── .env.example                  # Template (committed)
```

**What's in Git:**
- ✅ `.env.example` - Template for .env
- ✅ `.streamlit/secrets.toml.example` - Template for secrets
- ✅ All Python code
- ✅ Documentation
- ✅ `requirements.txt`

**What's NOT in Git** (gitignored):
- ❌ `.env` - Your actual API keys
- ❌ `.streamlit/secrets.toml` - Your actual secrets
- ❌ `*.log` - Log files
- ❌ `__pycache__/` - Python cache

---

## 🧪 Testing Your Setup

### Test 1: Check API Key Loading

```python
# Create a test file: test_keys.py
import os
from dotenv import load_dotenv

load_dotenv()

openai_key = os.getenv("OPENAI_API_KEY")
print(f"OpenAI key loaded: {'✅ Yes' if openai_key else '❌ No'}")
print(f"Key starts with: {openai_key[:10]}..." if openai_key else "")
```

Run:
```bash
python test_keys.py
```

### Test 2: Run the App

```bash
streamlit run unified_search_app.py
```

1. Navigate to **🤖 AI Research** tab
2. If you see "⚠️ OpenAI API Key Required" → check your configuration
3. If you can enter a research question → ✅ working!

### Test 3: Try a Simple Query

**Example question:**
```
What cybersecurity jobs are available?
```

Expected result:
- ✅ Search strategy displayed
- ✅ ClearanceJobs results shown
- ✅ AI summary generated

---

## 🐛 Troubleshooting

### Issue: "OpenAI API Key Required" Error

**Cause:** API key not found in any of the checked locations.

**Solutions:**
1. **Check .env file exists:**
   ```bash
   ls -la .env
   ```

2. **Check .env contains key:**
   ```bash
   grep OPENAI_API_KEY .env
   ```

3. **Verify key format:**
   - Should start with `sk-proj-` or `sk-`
   - No quotes needed in `.env` file
   - No spaces around `=`

   ```bash
   # ✅ Correct
   OPENAI_API_KEY=sk-proj-abc123...

   # ❌ Wrong
   OPENAI_API_KEY="sk-proj-abc123..."
   OPENAI_API_KEY = sk-proj-abc123...
   ```

4. **Try Streamlit secrets instead:**
   ```bash
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml
   # Edit .streamlit/secrets.toml
   ```

5. **Use UI input as temporary workaround:**
   - Sidebar → 🔑 API Keys → OpenAI API Key

### Issue: "No module named 'litellm'"

**Cause:** Missing dependencies.

**Solution:**
```bash
pip install -r requirements.txt
```

### Issue: "No module named 'ClearanceJobs'"

**Cause:** ClearanceJobs library not installed.

**Solution:**
```bash
cd ClearanceJobs
pip install -e .
cd ..
```

### Issue: API Key Works Locally but Not on Streamlit Cloud

**Cause:** Secrets not configured in Streamlit Cloud.

**Solution:**
1. Go to Streamlit Cloud dashboard
2. Click your app → Settings → Secrets
3. Add your `OPENAI_API_KEY`
4. Click Save (app will restart)

### Issue: High OpenAI Costs

**Causes:**
- Large result sets (many results per database)
- Complex research questions
- Frequent queries

**Solutions:**
1. Reduce "Results per database" (5-10 instead of 25-50)
2. Use more specific research questions
3. Monitor usage at: https://platform.openai.com/usage
4. Set spending limits in OpenAI dashboard

---

## 💰 Cost Management (Team)

### OpenAI API Usage

**Per Query Estimate:**
- Query generation: ~500-1000 tokens (~$0.005-0.01)
- Result summarization: ~2000-5000 tokens (~$0.01-0.025)
- **Total per query:** ~$0.01-0.05

**Monthly Estimates (team of 3):**
- Light usage (10 queries/person/day): ~$15-45/month
- Medium usage (50 queries/person/day): ~$75-225/month
- Heavy usage (100 queries/person/day): ~$150-450/month

### Cost Optimization Tips

1. **Start with small result sets:**
   - Use 5-10 results per database initially
   - Increase only if needed

2. **Be specific with questions:**
   - Reduces token usage
   - Gets better results faster

3. **Use manual search tabs for simple queries:**
   - ClearanceJobs tab for job searches
   - DVIDS tab for media searches
   - SAM.gov tab for contract searches
   - Reserve AI Research for complex multi-database queries

4. **Set OpenAI spending limits:**
   - Go to: https://platform.openai.com/account/billing/limits
   - Set monthly budget cap

---

## 📊 Team Workflow Recommendations

### Development Workflow

1. **Each developer:**
   - Clone repo
   - Create own `.env` or `.streamlit/secrets.toml`
   - Use own API keys for testing
   - Never commit secrets

2. **Code changes:**
   - Test locally first
   - Create pull requests
   - Review before merging

3. **Deployment:**
   - Merge to main branch
   - Streamlit Cloud auto-deploys
   - Test on production URL

### Production Usage

1. **Shared deployment:**
   - Single Streamlit Cloud app
   - Shared API keys in Streamlit secrets
   - Monitor usage together

2. **Access control:**
   - Share production URL only with team
   - Consider adding authentication if needed
   - Monitor API usage regularly

---

## 📞 Getting Help

**Documentation:**
- `README.md` - Full user guide
- `AI_RESEARCH_GUIDE.md` - AI Research feature guide
- `QUICK_START.md` - Quick reference
- `AI_INTEGRATION_SUMMARY.md` - Technical details

**Common Issues:**
- Check troubleshooting section above
- Review Streamlit Cloud logs (if deployed)
- Check OpenAI API status: https://status.openai.com/

---

## ✅ Checklist for New Team Members

### Local Setup
- [ ] Clone the repository
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Install ClearanceJobs: `cd ClearanceJobs && pip install -e . && cd ..`
- [ ] Get OpenAI API key from https://platform.openai.com/api-keys
- [ ] Create `.env` file and add `OPENAI_API_KEY`
- [ ] Test app: `streamlit run unified_search_app.py`
- [ ] Try AI Research tab with sample query

### Streamlit Cloud Access
- [ ] Get added to GitHub repository
- [ ] Access Streamlit Cloud dashboard
- [ ] Verify production deployment works
- [ ] Test all tabs (ClearanceJobs, DVIDS, SAM.gov, AI Research)

### Best Practices
- [ ] Never commit `.env` or `secrets.toml`
- [ ] Monitor OpenAI usage regularly
- [ ] Start with small result sets
- [ ] Use specific research questions
- [ ] Report bugs and issues to team

---

## 🎉 You're Ready!

Your team is now set up to use the unified search application with AI-powered research capabilities.

**Next Steps:**
1. Each team member completes local setup
2. Test AI Research with sample queries
3. Deploy to Streamlit Cloud for shared access
4. Monitor usage and costs
5. Provide feedback for improvements

**Questions?** See documentation or ask your team lead.
