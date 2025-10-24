# Reddit Integration for SIGINT Platform

Two-phase Reddit integration: real-time search + daily scraper.

---

## Phase 1: Real-Time Search Integration ✅ COMPLETE

**Purpose**: Query-driven Reddit search integrated into multi-source research system.

**How It Works**:
- User asks: "What's the public discourse on JTTF operations?"
- LLM selects 2-5 relevant subreddits from 25 options
- PRAW searches Reddit in parallel with SAM.gov, DVIDS, Twitter, etc.
- Results returned in unified format

**Files**:
- `integrations/social/reddit_integration.py` - Main integration (360 lines)
- `integrations/registry.py` - Registered Reddit integration
- `config_default.yaml` - Reddit config (timeout, enabled flag)
- `.env` - Credentials (REDDIT_CLIENT_ID, etc.)

**Usage**:
```bash
# Via CLI
python3 apps/ai_research_cli.py "cybersecurity threat intelligence"

# Reddit will automatically be searched alongside other sources
```

**Test Results**:
```
Query: "cybersecurity"
Subreddits: Intelligence, natsec, OSINT (LLM-selected)
Results: 4 posts found
Response time: ~2 seconds
```

**Configuration** (`.env`):
```bash
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USERNAME=your_username
REDDIT_PASSWORD=your_password
```

---

## Phase 2: Daily Scraper ✅ COMPLETE

**Purpose**: Build historical Reddit database for offline analysis.

**How It Works**:
- Cron job runs daily at 3 AM (after Discord at 2 AM)
- Scrapes 25 curated subreddits for last 24 hours
- Saves to `data/reddit/YYYY-MM-DD/reddit_scrape_YYYY-MM-DD.json`
- Rate limited: 1.5s between subreddits, 0.5s between posts
- Comment depth: Top-level only (Codex recommendation)

**Files**:
- `reddit_daily_scrape.py` - Daily scraper script (280 lines)
- `reddit_config.json` - Subreddit list by category
- `setup_reddit_scraper.sh` - Cron job setup script

**Subreddits Monitored** (25 total):

| Category | Subreddits | Count |
|----------|------------|-------|
| Government | politics, NeutralPolitics, Ask_Politics, PoliticalDiscussion, geopolitics | 5 |
| Intelligence | Intelligence, natsec, NSA, CIA, FBI, military, SpecOpsArchive, security | 8 |
| OSINT | OSINT, geospatial, journalism, Whistleblowers, Leaks | 5 |
| Conflicts | UkrainianConflict, syriancivilwar, MiddleEastNews, afghanistan | 4 |
| News | news, worldnews | 2 |

**Setup**:
```bash
cd /home/brian/sam_gov/experiments/reddit

# Set up daily cron job (3 AM)
bash setup_reddit_scraper.sh

# Verify cron job
crontab -l | grep reddit
```

**Manual Test**:
```bash
cd /home/brian/sam_gov/experiments/reddit
python3 reddit_daily_scrape.py
```

**Expected Runtime**: ~12-15 minutes for 24 subreddits

**Output**:
- **Data**: `data/reddit/2025-10-24/reddit_scrape_2025-10-24.json`
- **Logs**: `data/logs/reddit_daily_scrape.log`
- **Cron Log**: `data/logs/reddit_daily_scrape_cron.log`

**Output Format**:
```json
{
  "scrape_date": "2025-10-24",
  "total_subreddits": 25,
  "successful": 25,
  "failed": 0,
  "total_posts": 150,
  "total_comments": 450,
  "results": [
    {
      "subreddit": "Intelligence",
      "post_count": 8,
      "comment_count": 24,
      "posts": [...]
    }
  ]
}
```

---

## Implementation Details

### Rate Limiting (Codex Recommendation)

- **Between subreddits**: 1.5 seconds
- **Between posts**: 0.5 seconds
- **Reddit API limit**: 60 requests/minute (PRAW handles automatically)
- **Total scrape time**: ~12-15 minutes (well under rate limits)

### Comment Depth (Codex Recommendation)

```python
# Limit to top-level comments only
submission.comments.replace_more(limit=0)
```

**Rationale**: For investigative journalism, top comments + context is sufficient. Reduces API load and runtime.

### Error Handling

- Per-subreddit try/except (one failure doesn't crash entire scrape)
- Private/quarantined subreddits gracefully skipped
- Detailed error logging

### Security (Codex Recommendation)

- ✅ Credentials in `.env` (gitignored)
- ✅ NO credentials in config files or code
- ✅ Config references env vars via `${VAR}` syntax

---

## Monitoring

**Check if scraper ran**:
```bash
tail -f /home/brian/sam_gov/data/logs/reddit_daily_scrape.log
```

**Check cron job status**:
```bash
crontab -l | grep reddit
```

**View latest scrape**:
```bash
cat /home/brian/sam_gov/data/reddit/$(date +%Y-%m-%d)/reddit_scrape_$(date +%Y-%m-%d).json | jq '.total_posts, .total_comments'
```

---

## Troubleshooting

**"Reddit credentials not found"**:
- Check `.env` has REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USERNAME, REDDIT_PASSWORD
- Run `source .venv/bin/activate` before testing

**"Config file not found"**:
- Ensure `experiments/reddit/reddit_config.json` exists
- Check file permissions

**"HTTP 401 error"**:
- Reddit credentials invalid
- Verify credentials at https://www.reddit.com/prefs/apps

**Cron job not running**:
- Check crontab: `crontab -l`
- Check logs: `tail -f /home/brian/sam_gov/data/logs/reddit_daily_scrape_cron.log`

---

## Storage Estimates

**Per Day**:
- ~150-300 posts across 24 subreddits
- ~500-1000 comments (top-level only)
- ~2-5 MB JSON per day

**Per Year**:
- ~55,000-110,000 posts
- ~180,000-365,000 comments
- ~750 MB - 2 GB total

**Cleanup Strategy** (if needed):
- Archive data older than 90 days
- Or index in Elasticsearch for fast search

---

## Future Enhancements

**Phase 3 (Optional)**:
- Elasticsearch indexing for fast search
- Sentiment analysis on comments
- Trending topic detection
- User network analysis
- Integration with knowledge graph

---

## Related Documentation

- **Integration Plan**: `REDDIT_INTEGRATION_PLAN.md`
- **Status**: `STATUS.md` (Reddit: [PASS])
- **Completed Tasks**: `RESOLVED_TASKS.md`

---

## Credentials

**Get Reddit API Credentials**:
1. Go to https://www.reddit.com/prefs/apps
2. Click "create app" or "create another app"
3. Choose "script" type
4. Name: "SIGINT Platform"
5. Redirect URI: http://localhost:8080
6. Copy client ID (under app name) and secret
7. Add to `.env` file

**Never commit credentials to git!**
