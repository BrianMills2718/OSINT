# Deployment Guide for Owner

**For the technical owner who will deploy and configure the application**

Your non-technical team members will just need a URL - no setup required on their end!

---

## 🎯 Your Goal

Deploy the app to Streamlit Cloud so your 2 non-technical teammates can:
1. Visit a URL
2. Start searching immediately
3. No installation, no configuration, no API keys needed on their end

---

## 📋 Prerequisites

Before you start:
- [ ] OpenAI API key (required for AI Research)
- [ ] DVIDS API key (optional)
- [ ] SAM.gov API key (optional)
- [ ] GitHub account
- [ ] Streamlit Cloud account (free)

---

## 🚀 Deployment Steps

### Step 1: Test Locally First (Recommended)

```bash
# 1. Create your local .env for testing
cp .env.example .env
nano .env
# Add: OPENAI_API_KEY=your-actual-key-here

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install ClearanceJobs library
cd ClearanceJobs && pip install -e . && cd ..

# 4. Run the app
streamlit run unified_search_app.py

# 5. Test all features:
#    - ClearanceJobs tab (should work without API key)
#    - DVIDS tab (needs API key)
#    - SAM.gov tab (needs API key)
#    - AI Research tab (needs OpenAI key)
```

### Step 2: Push to GitHub

```bash
# 1. Initialize git (if not already done)
git init

# 2. Add all files
git add .

# 3. Check that secrets are NOT included
git status
# Should NOT show .env or .streamlit/secrets.toml

# 4. Commit
git commit -m "Add unified search app with AI research"

# 5. Create GitHub repository (via GitHub website)
#    - Go to github.com
#    - Click "New repository"
#    - Name it (e.g., "unified-search-app")
#    - Don't initialize with README (you already have one)

# 6. Push to GitHub
git remote add origin https://github.com/YOUR-USERNAME/unified-search-app.git
git branch -M main
git push -u origin main
```

### Step 3: Deploy to Streamlit Cloud

**3.1 Sign Up/Login:**
1. Go to: https://share.streamlit.io/
2. Sign in with your GitHub account

**3.2 Create New App:**
1. Click "New app"
2. Select your repository
3. Configure:
   - **Repository:** `YOUR-USERNAME/unified-search-app`
   - **Branch:** `main`
   - **Main file path:** `unified_search_app.py`
   - **Python version:** 3.9 or higher
4. Click "Deploy"

**3.3 Configure Secrets (IMPORTANT!):**

While the app is deploying:

1. Click "Advanced settings" → "Secrets"
2. Add your API keys in TOML format:

```toml
# Required for AI Research feature
OPENAI_API_KEY = "sk-proj-your-actual-key-here"

# Recommended for full functionality (both are FREE)
DVIDS_API_KEY = "your-dvids-key-here"
SAM_GOV_API_KEY = "your-sam-gov-key-here"
```

3. Click "Save"
4. App will restart with secrets loaded

**Important:**
- OpenAI key is REQUIRED for AI Research tab
- DVIDS and SAM.gov keys are FREE - just need to register
- Without DVIDS/SAM.gov keys, those tabs will show "API Key Required" warnings
- ClearanceJobs works without any API key
- Your teammates won't need to enter keys - they're loaded automatically from secrets

**3.4 Wait for Deployment:**
- Initial deployment takes 2-5 minutes
- You'll see logs in real-time
- When complete, you'll get a URL like: `https://your-app-name.streamlit.app`

### Step 4: Test the Deployed App

1. Visit your app URL
2. Test all tabs:
   - ✅ ClearanceJobs (should work - no API key needed)
   - ✅ DVIDS (should work if you added DVIDS_API_KEY to secrets)
   - ✅ SAM.gov (should work if you added SAM_GOV_API_KEY to secrets)
   - ✅ AI Research (should work with OPENAI_API_KEY)

3. Try a test AI Research query:
   ```
   What cybersecurity jobs are available for cleared professionals?
   ```

### Step 5: Share with Your Team

Send your teammates:
1. **The URL:** `https://your-app-name.streamlit.app`
2. **User guide:** `END_USER_GUIDE.md` (I'll create this)

That's it! They just click the URL and start using it.

---

## ⚙️ Configuration Details

### What API Keys Are Used For

| API Key | Feature | Cost | Required? |
|---------|---------|------|-----------|
| OpenAI | AI Research tab | ~$0.01-0.05/query | ✅ Yes (for AI Research) |
| DVIDS | DVIDS military media search | Free | ❌ No (optional) |
| SAM.gov | Government contract search | Free | ❌ No (optional) |

**Note:** ClearanceJobs works without any API key!

### Cost Management

**OpenAI Usage:**
- Each AI Research query costs ~$0.01-0.05
- Uses gpt-5-mini (economical model)
- All 3 users share the same API key

**Estimated Monthly Cost (3 users):**
- Light usage (5 queries/day/person): ~$7-23/month
- Medium usage (20 queries/day/person): ~$30-90/month
- Heavy usage (50 queries/day/person): ~$75-225/month

**Set Spending Limits:**
1. Go to: https://platform.openai.com/account/billing/limits
2. Set a monthly budget cap (e.g., $50/month)
3. You'll get alerts when approaching limit

---

## 🔒 Security Best Practices

### ✅ DO:
- Store API keys in Streamlit Cloud secrets
- Set spending limits on OpenAI account
- Monitor usage regularly
- Share only the app URL with your team (not API keys)

### ❌ DON'T:
- Never commit `.env` or `secrets.toml` to GitHub
- Never share API keys via email/Slack
- Don't use production keys for local testing (use separate keys if possible)

---

## 📊 Monitoring & Maintenance

### Check OpenAI Usage
1. Go to: https://platform.openai.com/usage
2. View daily usage and costs
3. Download usage reports if needed

### Check App Status
1. Streamlit Cloud dashboard: https://share.streamlit.io/
2. View logs if issues occur
3. Restart app if needed (Settings → Reboot)

### Update the App
When you make changes:
```bash
git add .
git commit -m "Description of changes"
git push origin main
```

Streamlit Cloud will automatically redeploy!

---

## 🔧 Troubleshooting

### Issue: "OpenAI API Key Required" on deployed app

**Cause:** Secrets not configured correctly.

**Fix:**
1. Go to Streamlit Cloud dashboard
2. Click your app → Settings → Secrets
3. Verify `OPENAI_API_KEY` is present and correct
4. Click "Save" (app will restart)

### Issue: App won't deploy - "No module named 'litellm'"

**Cause:** Missing dependencies in requirements.txt.

**Fix:**
```bash
# Check requirements.txt includes:
cat requirements.txt
# Should show litellm>=1.0.0

# If missing, add it:
echo "litellm>=1.0.0" >> requirements.txt
git add requirements.txt
git commit -m "Add litellm dependency"
git push
```

### Issue: ClearanceJobs library not found

**Cause:** ClearanceJobs library not installed.

**Fix:**
Create `packages.txt` in root directory:
```bash
# This file tells Streamlit Cloud what system packages to install
# (Not needed for this app, but good to know)
```

Actually, for Python packages installed with `pip install -e .`, you need to add the library to requirements.txt:
```bash
# Add to requirements.txt:
-e ./ClearanceJobs
```

### Issue: High OpenAI costs

**Solutions:**
1. Reduce default "Results per database" in AI Research
2. Set OpenAI spending limits
3. Monitor usage daily
4. Educate users to use specific queries (reduces token usage)

---

## 🎉 You're Done!

Your app is now deployed and ready for your team to use!

**What your teammates need:**
1. ✅ The app URL
2. ✅ The user guide (`END_USER_GUIDE.md`)
3. ✅ Nothing else - no installation, no setup!

**What you need to do:**
1. ✅ Monitor OpenAI usage periodically
2. ✅ Update app when needed (just git push)
3. ✅ Check Streamlit Cloud if issues reported

---

## 📞 Need Help?

**Streamlit Cloud Issues:**
- Docs: https://docs.streamlit.io/streamlit-community-cloud
- Forum: https://discuss.streamlit.io/

**OpenAI Issues:**
- Status: https://status.openai.com/
- Docs: https://platform.openai.com/docs

**App Issues:**
- Check Streamlit Cloud logs
- Review error messages
- Test locally first before blaming deployment

---

## ✅ Pre-Launch Checklist

Before sharing with your team:

### Testing
- [ ] Tested all 4 tabs locally
- [ ] AI Research returns results
- [ ] No errors in console
- [ ] Export features work (CSV downloads)

### Deployment
- [ ] Code pushed to GitHub
- [ ] Streamlit Cloud app deployed
- [ ] Secrets configured correctly
- [ ] App URL accessible

### Security
- [ ] API keys in Streamlit secrets (not in code)
- [ ] OpenAI spending limits set
- [ ] No secrets committed to GitHub
- [ ] `.gitignore` includes `.env` and `secrets.toml`

### Monitoring
- [ ] OpenAI dashboard bookmarked
- [ ] Streamlit Cloud dashboard bookmarked
- [ ] Know how to view logs
- [ ] Know how to restart app

### Team Handoff
- [ ] App URL ready to share
- [ ] END_USER_GUIDE.md ready to share
- [ ] Tested from non-owner account (incognito mode)

---

## 🚀 Quick Reference

**App URL:** `https://your-app-name.streamlit.app`

**Streamlit Dashboard:** https://share.streamlit.io/

**OpenAI Usage:** https://platform.openai.com/usage

**Update App:**
```bash
git add .
git commit -m "Update message"
git push origin main
# App auto-redeploys
```

**Restart App:**
- Streamlit Cloud → Your App → Settings → Reboot

**Check Logs:**
- Streamlit Cloud → Your App → Manage app → View logs
