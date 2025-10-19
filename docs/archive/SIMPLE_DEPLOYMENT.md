# Simple Deployment Guide

**You handle the setup. Your team just gets a URL.**

---

## 📋 What You Need

1. ✅ OpenAI API key - Get at: https://platform.openai.com/api-keys
2. ✅ GitHub account - Create at: https://github.com/signup
3. ✅ Streamlit Cloud account - Sign up at: https://share.streamlit.io/

Optional (for full functionality):
- DVIDS API key (military media search)
- SAM.gov API key (government contracts)

---

## 🚀 Deployment in 5 Steps

### Step 1: Test Locally (5 minutes)

```bash
# Create .env file
cp .env.example .env

# Edit .env and add your OpenAI key
nano .env
# Add: OPENAI_API_KEY=sk-proj-your-key-here

# Install and run
pip install -r requirements.txt
cd ClearanceJobs && pip install -e . && cd ..
streamlit run unified_search_app.py

# Test it works → then Ctrl+C to stop
```

### Step 2: Push to GitHub (2 minutes)

```bash
# Create repo on GitHub.com (click "New repository")
# Then push your code:

git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR-USERNAME/REPO-NAME.git
git push -u origin main
```

### Step 3: Deploy to Streamlit Cloud (3 minutes)

1. Go to: https://share.streamlit.io/
2. Sign in with GitHub
3. Click "New app"
4. Select your repository
5. Set **Main file:** `unified_search_app.py`
6. Click "Deploy"

### Step 4: Add API Keys to Streamlit Secrets (2 minutes)

While app is deploying:

1. Click "Advanced settings" → "Secrets"
2. Add your API keys:
   ```toml
   # Required for AI Research
   OPENAI_API_KEY = "sk-proj-your-actual-key-here"

   # Recommended for full functionality (both FREE)
   DVIDS_API_KEY = "your-dvids-key-here"
   SAM_GOV_API_KEY = "your-sam-gov-key-here"
   ```
3. Click "Save"

**Note:** Only OpenAI is required. DVIDS and SAM.gov are FREE but require registration. If you don't add them now, your team can still use ClearanceJobs and AI Research (limited).

### Step 5: Test & Share (2 minutes)

1. Wait for deployment to complete
2. You'll get a URL: `https://your-app-name.streamlit.app`
3. Test it works
4. Send your teammates:
   - ✅ The URL
   - ✅ The file: `END_USER_GUIDE.md`

**Done! 🎉**

---

## 👥 What Your Teammates Do

**Nothing!** They just:
1. Click the URL you send them
2. Start searching

No installation, no setup, no API keys on their end.

---

## 💰 Cost Estimate

**OpenAI API:**
- ~$0.01-0.05 per AI Research query
- For 3 people doing 10-20 queries/day: ~$15-60/month
- Set spending limits at: https://platform.openai.com/account/billing/limits

**Streamlit Cloud:**
- FREE! (for public apps)

**DVIDS & SAM.gov:**
- FREE!

---

## 📖 Full Documentation

**For you (technical owner):**
- `DEPLOYMENT_OWNER_GUIDE.md` - Complete deployment guide with troubleshooting

**For your teammates (non-technical users):**
- `END_USER_GUIDE.md` - How to use the application (no technical stuff)

---

## 🔧 Quick Troubleshooting

**"OpenAI API Key Required" on deployed app:**
1. Streamlit Cloud → Your App → Settings → Secrets
2. Add `OPENAI_API_KEY = "your-key"`
3. Save (app restarts automatically)

**App won't deploy:**
1. Check Streamlit Cloud logs
2. Verify `requirements.txt` includes all dependencies
3. Make sure main file is `unified_search_app.py`

**Want to update the app:**
```bash
git add .
git commit -m "Your changes"
git push
# Streamlit auto-redeploys!
```

---

## ✅ Pre-Flight Checklist

Before sharing with your team:

- [ ] App deployed to Streamlit Cloud
- [ ] OpenAI API key added to secrets
- [ ] Tested all 4 tabs work
- [ ] AI Research returns results
- [ ] No errors visible
- [ ] URL accessible from incognito/different browser
- [ ] Spending limits set on OpenAI account

---

## 🎯 Next Steps

1. **Complete deployment** (Steps 1-5 above)
2. **Test thoroughly** (all tabs, AI Research, export features)
3. **Send to team:**
   - App URL
   - `END_USER_GUIDE.md` file
4. **Monitor usage** occasionally at: https://platform.openai.com/usage

That's it! Your team has a working unified search application.
