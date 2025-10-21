# Streamlit Deployment Guide

This guide covers deploying the Multi-Source Intelligence Research Platform to Streamlit Cloud.

---

## Quick Start (Local Development)

### Command to Run Streamlit Locally

```bash
# Activate virtual environment
source .venv/bin/activate

# Run Streamlit app
streamlit run apps/unified_search_app.py
```

The app will open automatically in your browser at **http://localhost:8501**

---

## Preparing for GitHub & Streamlit Cloud

### ✅ Already Done

1. **Secrets moved to `.streamlit/secrets.toml`** - All API keys now in gitignored file
2. **`.gitignore` updated** - Secrets won't be committed
3. **Template created** - `.streamlit/secrets.toml.example` shows required keys

### Files That Are Safe to Commit

✅ **Safe** (will be committed):
- All `.py` files (apps/, core/, integrations/, monitoring/, research/)
- `.streamlit/secrets.toml.example` (template with no real keys)
- `requirements.txt`
- `README.md`
- All markdown documentation
- `config_default.yaml` (no secrets)

🚫 **Never Committed** (gitignored):
- `.env` (old secrets file)
- `.streamlit/secrets.toml` (actual secrets)
- `.venv/` (virtual environment)
- `data/` (local data files)
- `*.log` files
- `api_requests.jsonl` (contains API calls)

---

## Step-by-Step Deployment to Streamlit Cloud

### 1. Push to GitHub

```bash
# Check what will be committed (secrets should NOT appear)
git status

# Add all files (secrets are gitignored automatically)
git add .

# Commit
git commit -m "Prepare for Streamlit Cloud deployment"

# Push to GitHub
git push origin main
```

**Verify**: Check GitHub repository - `.env` and `.streamlit/secrets.toml` should NOT be visible.

---

### 2. Deploy to Streamlit Cloud

#### A. Go to Streamlit Cloud

1. Visit **https://streamlit.io/cloud**
2. Sign in with GitHub
3. Click **"New app"**

#### B. Configure Deployment

**Repository**: Select your GitHub repo (e.g., `yourusername/sam_gov`)

**Branch**: `main` (or your default branch)

**Main file path**: `apps/unified_search_app.py`

**App URL**: Choose a custom URL (e.g., `osint-research` → https://osint-research.streamlit.app)

#### C. Add Secrets

1. Click **"Advanced settings"** (before deploying)
2. Go to **"Secrets"** section
3. Copy-paste **entire contents** of your local `.streamlit/secrets.toml` file:

```toml
# Copy everything from .streamlit/secrets.toml
OPENAI_API_KEY = "sk-your-actual-key-here"
DVIDS_API_KEY = "key-your-actual-key-here"
SAM_GOV_API_KEY = "SAM-your-actual-key-here"
USAJOBS_API_KEY = "your-actual-key-here"
BRAVE_SEARCH_API_KEY = "your-actual-key-here"
RAPIDAPI_KEY = "your-actual-key-here"
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = "your-email@gmail.com"
SMTP_PASSWORD = "your-app-password"
SMTP_FROM_EMAIL = "your-email@gmail.com"
SMTP_FROM_NAME = "OSINT Monitor"
ALERT_TO_EMAIL = "your-email@gmail.com"
```

4. Click **"Save"**

#### D. Deploy

1. Click **"Deploy!"**
2. Wait 2-5 minutes for deployment
3. App will be live at `https://your-app-name.streamlit.app`

---

### 3. Post-Deployment

#### Verify Everything Works

Visit your deployed app and test:
- ✅ **User Guide tab** - Should load documentation
- ✅ **AI Research tab** - Should show OpenAI API key configured
- ✅ **Deep Research tab** - Should accept research questions
- ✅ **Monitor Management tab** - Should load
- ✅ **Advanced Search tab** - All 4 database tabs should work

#### Update Secrets (if needed)

1. Go to your app on Streamlit Cloud
2. Click **⋮** (three dots) → **Settings**
3. Navigate to **"Secrets"**
4. Edit and save

**App will restart automatically** when secrets are updated.

---

## Requirements File

The app will use `requirements.txt` automatically. Current file should include:

```txt
streamlit>=1.50.0
python-dotenv
litellm
playwright
asyncio
aiohttp
requests
PyYAML
beautifulsoup4
# Add any other dependencies
```

**Verify** `requirements.txt` exists and is up-to-date:

```bash
pip freeze > requirements.txt
```

---

## Troubleshooting

### Error: "No module named 'X'"

**Solution**: Add missing module to `requirements.txt` and redeploy

```bash
# Add to requirements.txt locally
echo "module-name>=version" >> requirements.txt

# Commit and push
git add requirements.txt
git commit -m "Add missing dependency"
git push

# Streamlit Cloud will auto-redeploy
```

### Error: "API key not found"

**Solution**: Check secrets configuration

1. Go to app settings on Streamlit Cloud
2. Verify all keys are present in "Secrets"
3. Keys must match names in code (e.g., `OPENAI_API_KEY` not `OPENAI_KEY`)

### App Runs Locally but Not on Streamlit Cloud

**Common Issues**:

1. **Absolute file paths**: Change to relative paths
   ```python
   # ❌ Wrong
   with open("/home/user/data/file.txt")

   # ✅ Right
   with open("data/file.txt")
   ```

2. **Missing files in git**: Make sure all necessary files are committed
   ```bash
   git status  # Check for untracked files
   ```

3. **Environment-specific code**: Remove localhost references
   ```python
   # ❌ Wrong
   url = "http://localhost:8501"

   # ✅ Right
   url = st.get_option("server.headless")  # Auto-detects
   ```

### Monitor Management Tab Issues

**Note**: The Boolean Monitor system with email alerts is designed for local/server deployment. For Streamlit Cloud:

- Monitor **configuration** works (can view/edit monitors)
- Monitor **execution** may have limitations (no persistent scheduler on Streamlit Cloud)
- For full monitoring, deploy to your own server (see `MONITORING_SYSTEM_READY.md`)

---

## Local vs Cloud Differences

| Feature | Local Development | Streamlit Cloud |
|---------|------------------|-----------------|
| **Secrets** | `.streamlit/secrets.toml` | App settings → Secrets |
| **File storage** | `data/` directory | Ephemeral (resets on restart) |
| **Scheduled jobs** | Works (via systemd) | Limited (no persistent scheduler) |
| **Email alerts** | Works | Works (via SMTP secrets) |
| **Database searches** | Works | Works |
| **Deep research** | Works | Works |

**Recommendation for Production**:
- Use **Streamlit Cloud** for the web UI (read-only features)
- Use **your own server** for scheduled monitoring and email alerts

---

## Security Notes

### Public Deployment Considerations

If deploying publicly on Streamlit Cloud:

1. **API Costs**: OpenAI API will be used by anyone who visits
   - Consider adding password protection
   - Monitor API usage on OpenAI dashboard
   - Set usage limits

2. **Rate Limiting**: Multiple users can trigger rate limits
   - Most government APIs have daily limits
   - Consider caching results

3. **Data Privacy**:
   - Don't store sensitive data in app
   - Use Streamlit's authentication (paid feature)
   - Or deploy to private server instead

### Password Protection (Optional)

Add to `apps/unified_search_app.py`:

```python
import streamlit as st

# Simple password protection
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets.get("APP_PASSWORD", ""):
            st.session_state["password_correct"] = True
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        st.error("😕 Password incorrect")
        return False
    else:
        return True

if not check_password():
    st.stop()

# Rest of your app code...
```

Then add to secrets:
```toml
APP_PASSWORD = "your-secure-password"
```

---

## Deployment Checklist

Before pushing to GitHub:

- [ ] All API keys moved to `.streamlit/secrets.toml`
- [ ] `.streamlit/secrets.toml` is in `.gitignore`
- [ ] `.streamlit/secrets.toml.example` created (safe to commit)
- [ ] `.env` file in `.gitignore`
- [ ] `requirements.txt` is up-to-date
- [ ] No hardcoded API keys in code
- [ ] No absolute file paths
- [ ] Test locally with secrets.toml (not .env)

After deploying to Streamlit Cloud:

- [ ] All secrets configured in app settings
- [ ] App loads without errors
- [ ] All tabs functional
- [ ] Database searches work
- [ ] Deep research works
- [ ] No sensitive data exposed

---

## Alternative: Private Server Deployment

For full features (scheduled monitoring, persistent storage), deploy to your own server:

```bash
# On your server
git clone https://github.com/yourusername/sam_gov.git
cd sam_gov
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Copy secrets
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit .streamlit/secrets.toml with your keys

# Run Streamlit
streamlit run apps/unified_search_app.py --server.port 8501 --server.address 0.0.0.0

# Or run monitoring system (with scheduler)
python3 monitoring/scheduler.py --config-dir data/monitors/configs
```

See `MONITORING_SYSTEM_READY.md` for full server deployment guide.

---

## Getting Help

**Streamlit Cloud Issues**:
- Streamlit Community Forum: https://discuss.streamlit.io/
- Streamlit Docs: https://docs.streamlit.io/

**App-Specific Issues**:
- Check app logs in Streamlit Cloud dashboard
- Test locally first with same configuration
- Review error messages in browser console (F12)

---

## Summary

**To deploy to Streamlit Cloud**:

1. **Push to GitHub** (secrets are automatically excluded)
   ```bash
   git add .
   git commit -m "Deploy to Streamlit Cloud"
   git push
   ```

2. **Create app on Streamlit Cloud**:
   - Repository: Your GitHub repo
   - Main file: `apps/unified_search_app.py`
   - Secrets: Copy from `.streamlit/secrets.toml`

3. **Test deployed app** at `https://your-app.streamlit.app`

**To run locally**:
```bash
source .venv/bin/activate
streamlit run apps/unified_search_app.py
```

App will open at **http://localhost:8501**
