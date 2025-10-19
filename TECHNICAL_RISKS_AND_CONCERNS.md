# Technical Risks, Uncertainties & Difficult Challenges

## Executive Summary

**Overall Risk Level**: MEDIUM-HIGH

**Biggest Concerns**:
1. Social media APIs are expensive, fragile, or hostile to scraping
2. LLM costs could spiral out of control with heavy usage
3. Deduplication across 15+ sources is genuinely hard
4. Real-time monitoring at scale requires complex infrastructure
5. Your team is 2 non-technical people - support burden will be high

**Good News**: Your existing agentic executor is solid. The core research capability works. The risks are mainly in **scaling, cost control, and specific integrations**.

---

## PART 1: Uncertainties & Unknowns

### Uncertainty 1: Social Media API Viability

**Problem**: Social media platforms are actively hostile to data access

#### Twitter/X - VERY EXPENSIVE

**Current Reality** (as of 2025):
```
Free tier: GONE (Elon killed it in 2023)

Basic tier: $100/month
- 10,000 tweets/month (read)
- 3,200 tweets/month (post)
- 50 requests/15min
- NO streaming
- NO archive search

Pro tier: $5,000/month
- 1M tweets/month
- Streaming API
- Archive search (full history)

Enterprise: $42,000+/month
- Unlimited (with rate limits)
- Full firehose
```

**Risk**: Your Boolean monitoring could EASILY exceed 10k tweets/month
- Example: Monitoring "domestic terrorism" OR "extremism" = thousands of matches daily
- You'd hit the 10k limit in days

**Mitigation Options**:
1. **Skip Twitter** - Expensive, maybe not worth it
2. **Use free alternatives**:
   - Nitter instances (unofficial Twitter scrapers, often get blocked)
   - ScrapeHero Cloud (3rd party, $50-200/month, also risky)
3. **Focus on specific accounts** - Only monitor high-value accounts (Ken Klippenstein, agencies, journalists)
4. **Wait for API policy changes** - Elon is unpredictable

**My Concern**: Twitter was your example for social media monitoring, but it might be **economically infeasible** for comprehensive monitoring.

**Recommendation**: START WITHOUT TWITTER. Add later if budget allows and use case is proven.

---

#### Telegram - TECHNICALLY HARD

**Problem**: No official search API exists

**Current Reality**:
- Telegram has Bot API (good for sending/receiving)
- Telegram has Client API (Telethon library - lets you act as a user)
- **But**: No way to search across all public channels
- **But**: Must JOIN each channel you want to monitor
- **But**: Rate limits on joining channels (20-30 per day max)

**What This Means**:
- You can monitor channels/groups you KNOW about
- You CANNOT search Telegram like you search Twitter
- You must manually curate a list of channels

**Example Workflow**:
1. Identify 50 extremist Telegram channels (manual research)
2. Join them (takes 2-3 days due to rate limits)
3. Monitor new messages (Telethon can do this)
4. Keyword match locally
5. Alert on matches

**Risk**: Discovery is manual. You won't find NEW channels automatically.

**Mitigation**:
- Start with known high-value channels
- Use external tools (TGStat.com, Combot) to discover channels
- Crowd-source channel lists from OSINT community

**My Concern**: Telegram monitoring is **HIGH-VALUE** (where extremism/leaks happen) but **requires manual channel curation**, not automated discovery.

**Recommendation**: Build Telegram monitoring, but accept that channel discovery is manual. Create a curated watchlist.

---

#### TikTok - EXTREMELY FRAGILE

**Problem**: No official API for search, unofficial APIs break constantly

**Current Reality**:
- TikTok has NO public API for content search
- Unofficial libraries (TikTok-Api, TikTokPy) exist but break every 2-3 months when TikTok changes their app
- Requires reverse-engineering mobile app
- High risk of IP bans if detected

**Risk**: You build it, it works for a month, then TikTok updates and it breaks. You're constantly fixing it.

**Mitigation**:
- Use paid 3rd party services (Apify, Bright Data) - $100-500/month
- Accept that this integration is fragile
- Have fallback plan when it breaks

**My Concern**: TikTok monitoring is **HIGH-MAINTENANCE** and probably **not worth it** unless you have specific TikTok-focused investigations.

**Recommendation**: SKIP TikTok initially. Only add if you have a specific TikTok investigation need.

---

#### Reddit - ACTUALLY GOOD (surprisingly)

**Good News**: Reddit API is FREE and well-maintained

**Current Reality**:
- PRAW library (Python Reddit API Wrapper) is excellent
- Free tier: 60 requests/minute (generous!)
- Can search subreddits, users, posts, comments
- Rate limits are reasonable
- No cost

**Risk**: LOW. Reddit is one of the EASIEST integrations.

**Recommendation**: BUILD THIS FIRST for social media. Reddit is investigative gold (insider discussions, leaks) and technically easy.

---

#### 4chan - EASY BUT LIMITED

**Good News**: Read-only JSON API exists

**Current Reality**:
- Boards have public JSON endpoints (boards.4chan.org/pol/catalog.json)
- No authentication needed
- No rate limits (but be respectful)
- Can monitor threads, posts

**Limitations**:
- No search API (must download all threads and search locally)
- Threads 404 quickly (prune after ~200 threads)
- Must poll frequently (every 5-10 minutes) or miss content
- VERY high volume on /pol/ (hundreds of posts per hour)

**Risk**: MEDIUM. Easy to access, but need robust polling + storage to not miss content.

**Recommendation**: Build if you research extremism (4chan/pol is source of white nationalist activity). Accept that you'll miss some content.

---

### Uncertainty 2: LLM Cost Spiraling

**Problem**: Your platform uses LLMs for multiple functions, costs add up FAST

#### Where You Use LLMs (from your existing code + planned features):

1. **Query generation** (agentic executor) - 1 call per database per search
2. **Query refinement** (agentic executor) - Up to 3 calls per database if results are poor
3. **Natural language parsing** (new feature) - 1 call per user question
4. **Result synthesis** (new feature) - 1 call per search (processes all results)
5. **Entity extraction** (new feature) - 1 call per document
6. **Timeline generation** (new feature) - 1 call per investigation
7. **Theme identification** (new feature) - 1 call per result set

**Example Scenario**: User asks "What FBI documents mention domestic terrorism?"

```
LLM Calls Required:
1. Parse question (1 call) - gpt-4o-mini
2. Generate queries for FBI Vault, DHS, Federal Register (3 calls) - gpt-4o-mini
3. Refine poor results (assume 1 database needs 2 refinements) (2 calls) - gpt-4o-mini
4. Synthesize results (1 call, processes 50 documents) - gpt-4o (need powerful model)
5. Extract entities (1 call) - gpt-4o
6. Generate timeline (1 call) - gpt-4o

Total: 9 LLM calls per search
```

**Cost Calculation**:

```
gpt-4o-mini: $0.15 per 1M input tokens, $0.60 per 1M output
gpt-4o: $5.00 per 1M input tokens, $15.00 per 1M output

Assumptions:
- Query gen/refinement: ~500 tokens input, 200 tokens output (cheap calls)
- Synthesis: ~50k tokens input (50 documents), 2k tokens output (expensive!)
- Entity extraction: ~10k tokens input, 1k tokens output
- Timeline: ~10k tokens input, 1k tokens output

Per-search cost:
- 6x gpt-4o-mini calls: ~$0.001 each = $0.006
- 3x gpt-4o calls: ~$0.30 each = $0.90

Total per search: ~$0.91
```

**Risk Assessment**:

```
If you run 10 searches/day: $9/day = $270/month
If you run 50 searches/day: $45/day = $1,350/month
If you run automated monitoring (100 searches/day): $90/day = $2,700/month
```

**THIS COULD GET EXPENSIVE VERY QUICKLY.**

**Mitigation Strategies**:

1. **Cache aggressively**:
   - Don't re-synthesize same results
   - Store LLM outputs in database
   - Only re-run if results change

2. **Use cheaper models where possible**:
   - Query generation: gpt-4o-mini (cheap)
   - Synthesis: gpt-4o-mini FIRST, only use gpt-4o if critical
   - Consider Claude Haiku ($0.80 per 1M) for some tasks

3. **Batch processing**:
   - Don't synthesize 50 documents separately
   - Send all 50 in ONE call (cheaper than 50 calls)

4. **User controls**:
   - "Generate summary" is OPTIONAL, not automatic
   - Let user decide if they want expensive analysis

5. **Rate limits**:
   - Max 10 AI analyses per day per user
   - Budget alerts when costs exceed $X

**My Concern**: Without careful cost controls, LLM expenses could be **$1000-3000/month** easily.

**Recommendation**:
- Build cost tracking from day 1
- Make AI analysis opt-in, not automatic
- Start with gpt-4o-mini for EVERYTHING
- Only upgrade to gpt-4o when quality is insufficient

---

### Uncertainty 3: Deduplication Quality

**Problem**: Same story appears across 15 sources with different titles, formatting, dates

#### Challenge Examples:

**Example 1: Same FBI Document**
```
Source 1 (FBI Vault):
  Title: "Domestic Terrorism Threat Assessment 2025"
  URL: vault.fbi.gov/reports/dt-2025.pdf
  Date: 2025-01-15

Source 2 (MuckRock):
  Title: "FBI Releases Domestic Terror Report"
  URL: muckrock.com/news/fbi-terror-report
  Date: 2025-01-16 (news article ABOUT the report)

Source 3 (Google News):
  Title: "FBI: Domestic Extremism Threat Rising"
  URL: nytimes.com/2025/01/16/us/fbi-extremism
  Date: 2025-01-16

Source 4 (Reddit):
  Title: "New FBI report on domestic terrorism (link in comments)"
  URL: reddit.com/r/intelligence/comments/abc123
  Date: 2025-01-16
```

**These are 4 different items about THE SAME underlying document.**

**Question**: Should they be:
- A) Grouped as 1 item (with 4 sources)?
- B) Kept separate (primary source + 3 secondary articles about it)?
- C) Deduplicated to just the primary source?

**There's no single right answer - depends on use case.**

#### Deduplication Approaches:

**Approach 1: Content Hashing** (Simple, Fast, Brittle)
```python
# Hash first 500 characters
content_hash = hashlib.sha256(content[:500].encode()).hexdigest()

# If hash exists in database, it's a duplicate
if content_hash in seen_hashes:
    mark_as_duplicate()
```

**Pros**: Fast, cheap, simple
**Cons**: Misses duplicates with different formatting, paraphrases

---

**Approach 2: MinHash/SimHash** (Better, More Expensive)
```python
from datasketch import MinHash

# Create signature for each document
m = MinHash()
for word in document.split():
    m.update(word.encode())

# Check similarity
if lsh.query(m):  # LSH = Locality-Sensitive Hashing
    mark_as_duplicate()
```

**Pros**: Catches near-duplicates (90%+ similar)
**Cons**: Slower, requires more memory

---

**Approach 3: Embedding Similarity** (Best Quality, EXPENSIVE)
```python
# Get embeddings for each document
embedding1 = openai.embeddings.create(model="text-embedding-3-small", input=doc1)
embedding2 = openai.embeddings.create(model="text-embedding-3-small", input=doc2)

# Compute cosine similarity
similarity = cosine_similarity(embedding1, embedding2)

if similarity > 0.85:
    mark_as_duplicate()
```

**Pros**: Semantic similarity (catches paraphrases)
**Cons**:
- Costs $0.02 per 1M tokens (adds up!)
- Slow (API calls)
- Need vector database (Pinecone, Weaviate, or pgvector)

---

**Approach 4: Hybrid** (Recommended)
```python
1. Fast filter: Content hash on first 500 chars
   → If exact match, it's duplicate (99% confidence)

2. Medium filter: MinHash on full content
   → If >90% similar, probably duplicate (check manually or with LLM)

3. Slow filter: For borderline cases, use LLM to decide
   → "Are these two articles about the same underlying event?"
```

**My Concern**:
- Perfect deduplication is IMPOSSIBLE
- Tradeoff between precision/recall and cost/speed
- You WILL have duplicates slip through OR false positives

**Recommendation**:
- Start with MinHash (good balance)
- Accept ~5-10% duplicate rate initially
- Add embedding search later if needed
- Let users manually mark duplicates to improve over time

---

### Uncertainty 4: Real-Time vs Scheduled Monitoring

**Problem**: "Real-time" monitoring is HARD and expensive

#### What Users Expect:

"I want to be alerted immediately when FBI publishes a new document on extremism"

**Reality Check**:

**Option A: Polling** (What you can actually build)
```python
# Check every 5-30 minutes
schedule.every(5).minutes.do(check_fbi_vault)

# If new results, send alert
if new_results:
    send_slack_alert()
```

**Pros**: Simple, cheap, works
**Cons**: Not "real-time" (5-30 min delay)

---

**Option B: Webhooks** (Rarely Available)
```python
# Ideal: FBI Vault calls YOUR webhook when new doc is published
@app.post("/webhook/fbi_vault")
def handle_new_document(payload):
    send_instant_alert()
```

**Pros**: True real-time, no polling
**Cons**: **Most sources don't offer webhooks** (FBI Vault doesn't, Twitter charges $5k/month for it)

---

**Option C: RSS Feeds** (When Available)
```python
# Some sources have RSS feeds
feed = feedparser.parse("https://vault.fbi.gov/rss")

# Check for new entries every 5 min
```

**Pros**: Lightweight, standardized
**Cons**: Not all sources have RSS (diminishing in 2025)

---

**Option D: Streaming APIs** (Expensive)
```python
# Twitter streaming API (requires $5k/month Pro tier)
stream.filter(track=["domestic terrorism"])

# Get tweets instantly as they're posted
```

**Pros**: True real-time
**Cons**: **Only available on expensive tiers** or not at all

---

**Reality**: You'll be doing **scheduled polling** (every 5-30 minutes) for 90% of sources.

**Risk**: Users expect "instant" alerts but won't get them (5-30 min lag)

**Mitigation**:
- Set expectations clearly: "Checks every 15 minutes"
- Use RSS/webhooks where available
- For critical sources (FBI, DHS), poll every 5 min
- For lower-priority (news), poll every 30-60 min

**My Concern**: "Real-time monitoring" sounds simple but requires infrastructure (job queues, workers, scaling) if you have 50 monitors checking 15 sources each.

**Recommendation**: Start with simple cron jobs (every 15-30 min). Upgrade to Celery/Redis task queue when you have 10+ concurrent monitors.

---

## PART 2: Most Difficult Technical Achievements

### Difficulty Level 1: HARD (But Doable)

#### 1. Cross-Source Entity Resolution

**Problem**: "Elon Musk" in one source, "Musk" in another, "@elonmusk" in third, "CEO of Tesla" in fourth

**Challenge**: Identifying that these all refer to the SAME entity

**Current State-of-the-Art**:
- Named Entity Recognition (spaCy, Stanza) gets ~85-90% accuracy
- Entity linking (DBpedia, Wikidata) adds another layer
- Still requires manual review for edge cases

**Why It's Hard**:
- Abbreviations (FBI vs Federal Bureau of Investigation)
- Nicknames (Bill vs William Arkin)
- Titles change (Kash Patel was "Acting Attorney General" then "FBI Director")
- Disambiguation (Jordan vs Michael Jordan vs Jordan Peterson vs country Jordan)

**Approach**:
```python
1. Use spaCy NER to identify entities
2. Normalize names (Title Case, strip punctuation)
3. Create canonical mapping:
   {
     "canonical": "Elon Musk",
     "aliases": ["Elon", "Musk", "@elonmusk", "Tesla CEO"],
     "type": "person",
     "wikidata_id": "Q317521"
   }
4. Fuzzy match new entities against canonical list
5. LLM verification for borderline cases:
   "Are 'Elon' and 'Tesla CEO' referring to the same person?"
```

**Effort**: 2-3 weeks
**Success Rate**: ~85% automatic, 15% manual review

**My Concern**: You'll have entity duplicates (Elon Musk and Musk shown as separate). Require manual cleanup.

---

#### 2. Timeline Generation from Unstructured Text

**Problem**: Extract events and dates from articles, order chronologically

**Example Input**:
```
"The FBI raid occurred on March 15, just two weeks after the initial complaint
was filed. Documents show that investigators had been tracking the suspect
since last summer."
```

**Desired Output**:
```
Timeline:
- Summer 2024: FBI begins tracking suspect
- March 1, 2025: Initial complaint filed
- March 15, 2025: FBI raid conducted
```

**Why It's Hard**:
- Relative dates ("two weeks after", "last summer")
- Implicit dates ("the raid" - when?)
- Conflicting dates across sources
- Incomplete dates ("in early 2024")

**Approach**:
```python
1. Use spaCy's date parser + dateparser library
2. LLM extracts events with dates:
   Prompt: "Extract all events and their dates from this article. Return JSON."
3. Resolve relative dates (anchor to article publish date)
4. Deduplicate events (same event mentioned in multiple sources)
5. Sort chronologically
```

**Effort**: 2-3 weeks
**Success Rate**: ~70% automatic, 30% requires manual review

**My Concern**: Timeline quality depends on article quality. Vague articles produce vague timelines.

---

#### 3. Network Graph Generation (Entity Relationships)

**Problem**: Who's connected to whom? What organizations are linked?

**Example**:
```
"Elon Musk's SpaceX received a $800M contract from the Space Force,
which was approved by Defense Secretary Lloyd Austin."

Desired Graph:
Elon Musk ──CEO──> SpaceX
SpaceX ──received──> $800M Contract
Contract ──awarded by──> Space Force
Lloyd Austin ──heads──> Department of Defense
DoD ──branch──> Space Force
```

**Why It's Hard**:
- Relationship extraction requires sophisticated NLP
- Relationships can be implicit ("Space Force" is part of "DoD" - not stated)
- Relationship types vary (employed by, owns, awarded, approved, etc.)
- Temporal changes (Kash Patel WAS Attorney General, NOW FBI Director)

**Approach**:
```python
1. Use dependency parsing (spaCy) to find subject-verb-object relationships
2. Use LLM for relationship extraction:
   Prompt: "Identify all relationships between entities.
            Return as JSON: [{source: X, relationship: Y, target: Z}]"
3. Build NetworkX graph
4. Visualize with D3.js or Cytoscape.js
```

**Effort**: 3-4 weeks (relationship extraction is hard)
**Success Rate**: ~60% automatic, 40% requires manual curation

**My Concern**: Auto-generated networks will be messy. Requires human curation to be publication-quality.

---

### Difficulty Level 2: VERY HARD (Risky)

#### 4. Automated Relevance Scoring at Scale

**Problem**: You get 1,000 results from Boolean search. Which 10 should you show first?

**Why It's Hard**:
- Relevance is subjective (what's relevant to me vs you?)
- Depends on user intent (researching vs monitoring vs investigating)
- Must be FAST (can't LLM-score 1,000 results - too slow/expensive)
- Needs to learn from feedback

**Naive Approach** (Fast but Crude):
```python
score = (
    keyword_match_count * 0.3 +
    source_credibility * 0.25 +
    recency_score * 0.2 +
    content_length_score * 0.15 +
    exclusivity_score * 0.1
)
```

**Better Approach** (Slower but Smarter):
```python
1. Fast filter: Use naive scoring to get top 100
2. Slow filter: Use embedding similarity to user query
   - Embed user query: "domestic terrorism FBI documents"
   - Embed each result title + snippet
   - Compute cosine similarity
   - Re-rank based on semantic relevance
3. Learn from user clicks:
   - Track which results users click
   - Train ranking model (LambdaMART, XGBoost)
   - Improve over time
```

**Best Approach** (Expensive):
```python
Use LLM to score top 50:
  Prompt: "Rate this result's relevance to the query from 1-10:
           Query: {query}
           Result: {title} - {snippet}
           Score: "
```

**Tradeoff**:
- Naive scoring: Fast, cheap, ~60% accuracy
- Embedding similarity: Medium speed, cheap, ~75% accuracy
- LLM scoring: Slow, expensive, ~85% accuracy

**My Concern**: You'll show irrelevant results prominently. Requires tuning and user feedback.

**Recommendation**: Start with embedding similarity (good balance). Add LLM scoring only for top 10 results.

---

#### 5. Handling Source API Changes / Breakage

**Problem**: You build integration with TikTok. Next week, TikTok changes their app and your integration breaks.

**Why It's Hard**:
- Social media platforms change frequently (especially unofficial APIs)
- No warning when changes happen
- Requires constant maintenance
- Different errors for each source (Twitter rate limit vs Telegram flood wait vs Reddit server error)

**Approach**:
```python
1. Build robust error handling:
   - Retry with exponential backoff
   - Circuit breaker pattern (stop calling broken API)
   - Graceful degradation (if Twitter breaks, continue with other sources)

2. Monitor health:
   - Track success rate per source
   - Alert when success rate drops below 80%
   - Auto-disable source if broken for 24 hours

3. Version integrations:
   - Keep old version while building new
   - A/B test new version
   - Rollback if new version breaks

4. Have fallbacks:
   - If Twitter API fails, try Nitter scraper
   - If TikTok API fails, use paid service (Apify)
```

**Effort**: Ongoing maintenance burden
**Risk**: High for unofficial APIs (TikTok, Telegram), Low for official APIs (FBI Vault, Federal Register)

**My Concern**: You'll spend 10-20% of your time fixing broken integrations.

**Recommendation**:
- Prioritize stable sources (government APIs, Reddit)
- Avoid fragile sources (TikTok) unless absolutely needed
- Build health monitoring from day 1

---

### Difficulty Level 3: EXTREMELY HARD (May Not Be Worth It)

#### 6. Content Understanding / Summarization at Scale

**Problem**: Summarize 1,000 documents accurately

**Why This is MUCH Harder Than It Seems**:

**Naive Approach**:
```python
# Summarize each document separately
for doc in documents:
    summary = llm_summarize(doc)
```

**Problems**:
- 1,000 LLM calls = $100-500 in API costs
- Takes 30-60 minutes (slow)
- Summaries are isolated (no cross-document synthesis)
- Misses connections between documents

**Better Approach**:
```python
# Batch summarization
batch_1 = documents[:50]
summary_1 = llm_summarize(batch_1)

batch_2 = documents[50:100]
summary_2 = llm_summarize(batch_2)

# ... 20 batches later ...

# Meta-summary
final_summary = llm_summarize([summary_1, summary_2, ..., summary_20])
```

**Problems**:
- Still expensive
- Lossy (important details may be dropped in first round)
- Requires careful prompt engineering

**Best Approach** (Map-Reduce + Embeddings):
```python
1. Embed all documents
2. Cluster by semantic similarity (k-means on embeddings)
3. Extract representative doc from each cluster
4. Summarize representatives (10-20 summaries instead of 1,000)
5. Synthesize cluster summaries into final summary
```

**Still Problems**:
- Requires vector database (Pinecone, $70/month)
- Clustering is an art (how many clusters? which algorithm?)
- Quality depends on prompt engineering

**My Concern**: Large-scale summarization (100+ documents) is EXPENSIVE and HARD. You'll spend a lot of time tuning prompts and managing costs.

**Recommendation**:
- Start with simple summarization (10-20 docs max)
- Show all docs to user, let them decide what to read
- Only do large-scale summarization on request (not automatic)
- Budget for this feature carefully

---

## PART 3: Risks

### Risk 1: Scope Creep → Never Ships

**Scenario**: You keep adding "just one more feature" and never launch

**Why This Happens**:
- Platform vision is HUGE (natural language, monitoring, analysis, collaboration, 15 sources)
- Each feature seems necessary
- Perfectionism

**Result**: 6 months later, still not usable by your team

**Mitigation**:
- **Ship Phase 1 in 3 weeks** (monitoring MVP)
- Get team using it ASAP
- Add features based on ACTUAL usage, not speculation

---

### Risk 2: LLM Costs Spiral Out of Control

**Scenario**: You launch, team uses it heavily, $3,000 bill arrives

**Why This Happens**:
- LLM calls in multiple places (query gen, refinement, synthesis, analysis)
- No cost tracking
- No rate limits
- Auto-analysis on every search

**Result**: Unsustainable costs, must shut down features

**Mitigation**:
- Build cost tracking from DAY 1
- Set monthly budget alerts ($50, $100, $200)
- Make expensive features opt-in (click "Analyze" vs automatic)
- Use cheapest models first (gpt-4o-mini everywhere)
- Cache aggressively

---

### Risk 3: API Rate Limits Hit During Critical Investigation

**Scenario**: Breaking news, you need to search NOW, hit rate limit, can't access data for 15 minutes

**Why This Happens**:
- Most APIs have rate limits (Twitter: 50/15min, Reddit: 60/min, FBI Vault: unknown)
- Monitoring uses up quota
- No quota management

**Result**: Can't access data when you need it most

**Mitigation**:
- Track quota usage per source
- Prioritize manual searches over automated monitors when quota is low
- Implement backoff when approaching limit
- Have multiple API keys if possible (distribute load)

---

### Risk 4: Brittle Integrations Break During Investigation

**Scenario**: Working on time-sensitive story, Telegram integration breaks, lose access to critical channels

**Why This Happens**:
- Unofficial APIs break
- Platform policy changes
- Your IP gets blocked

**Result**: Gaps in coverage, missed data

**Mitigation**:
- Monitor integration health
- Have fallback scrapers (if API fails, try web scraping)
- Manual data collection process as backup
- Don't rely on single source for critical intelligence

---

### Risk 5: Data Quality Issues (Duplicates, False Positives)

**Scenario**: User searches "domestic terrorism", gets 500 results, 200 are duplicates, 150 are irrelevant

**Why This Happens**:
- Deduplication is imperfect
- Relevance scoring is crude
- Boolean queries too broad

**Result**: Users lose trust in platform, manual filtering burden

**Mitigation**:
- Accept 5-10% duplicate rate initially
- Let users report duplicates (feedback loop)
- Tighten Boolean queries
- Add manual review step for critical investigations

---

### Risk 6: Support Burden for Non-Technical Team

**Scenario**: Team member can't figure out how to set up monitor, asks you for help, takes 30 minutes

**Why This Happens**:
- UI isn't intuitive enough
- Documentation is lacking
- Complex features hard to explain

**Result**: You become full-time support, can't build new features

**Mitigation**:
- Build EXTREMELY simple UI (Streamlit is good for this)
- Video walkthroughs for common tasks
- Office hours (1 hour/week for support questions)
- Templatized monitors (just click "Use NVE Template")

---

### Risk 7: Security / Privacy Issues

**Scenario**: Investigative document with classified info gets accidentally shared publicly

**Why This Happens**:
- No access controls
- Share links are public
- Export feature has no warnings

**Result**: Legal liability, source exposure

**Mitigation**:
- Add authentication from day 1 (even if just password)
- Mark investigations as private/team/public
- Watermark exports with user info
- Warn before exporting sensitive content

---

### Risk 8: Scalability Issues

**Scenario**: You have 100 monitors running every 15 minutes = 400 searches/hour. System becomes slow/unstable.

**Why This Happens**:
- Simple cron jobs don't scale
- Database becomes bottleneck
- No caching
- Sequential processing

**Result**: Monitors take hours to run, miss time-sensitive intel

**Mitigation**:
- Use task queue (Celery + Redis) when >10 monitors
- Parallel execution (you already have this!)
- Cache search results (don't re-search same query)
- Database indexing (critical for large result sets)

---

## PART 4: My Honest Recommendations

### What I'm CONFIDENT Will Work:

1. **Automated Boolean monitoring** with email alerts
   - Technical risk: LOW
   - Value: HIGH
   - Build this first ✅

2. **Government source integrations** (FBI Vault, Federal Register, Congress.gov)
   - Technical risk: LOW
   - Value: HIGH
   - APIs are stable, documented, free ✅

3. **Reddit integration**
   - Technical risk: LOW
   - Value: HIGH
   - PRAW library is excellent, free, stable ✅

4. **Natural language chat interface** (Streamlit)
   - Technical risk: LOW
   - Value: HIGH
   - Streamlit makes this easy ✅

5. **Basic LLM analysis** (summarize 10-20 docs)
   - Technical risk: LOW
   - Value: MEDIUM
   - Doable with cost controls ✅

---

### What I'm UNCERTAIN About:

1. **Twitter integration**
   - Technical risk: LOW (API works)
   - **Cost risk: VERY HIGH** ($100-5000/month)
   - **Value: Depends on budget and use case**
   - Recommendation: **START WITHOUT IT**, add later if justified

2. **Large-scale summarization** (100+ documents)
   - Technical risk: MEDIUM
   - **Cost risk: HIGH** ($50-200 per analysis)
   - Value: MEDIUM (nice-to-have, not essential)
   - Recommendation: **BUILD SIMPLE VERSION FIRST** (10-20 docs), scale later

3. **Entity network graphs**
   - Technical risk: MEDIUM
   - Cost risk: MEDIUM
   - **Quality risk: HIGH** (auto-generated graphs are messy)
   - Recommendation: **BUILD PROTOTYPE**, but expect manual curation needed

---

### What I'm CONCERNED About:

1. **Telegram integration**
   - Technical risk: HIGH (fragile, no search API)
   - Cost risk: LOW (free)
   - **Maintenance risk: HIGH** (breaks often)
   - Value: HIGH (where leaks/extremism happen)
   - Recommendation: **BUILD IT** but allocate time for maintenance

2. **TikTok integration**
   - Technical risk: VERY HIGH (unofficial API)
   - Cost risk: MEDIUM ($100-500/month for paid service)
   - **Maintenance risk: VERY HIGH** (breaks constantly)
   - Value: LOW (unless TikTok-specific investigation)
   - Recommendation: **SKIP IT** unless absolutely needed

3. **Real-time monitoring**
   - Technical risk: MEDIUM (need task queue)
   - Cost risk: MEDIUM (more infrastructure)
   - **Expectation risk: HIGH** (users expect instant, you deliver 5-15 min lag)
   - Recommendation: **START WITH 15-MIN POLLING**, upgrade to real-time later if needed

---

## FINAL RISK ASSESSMENT

### Overall Platform Viability: **HIGH** ✅

**Why I'm Optimistic**:
- Your existing agentic executor is SOLID
- Government APIs are stable and free
- Reddit is easy and valuable
- Core monitoring feature is technically straightforward
- Real investigative value (not a toy project)

**Why I'm Cautious**:
- Social media integrations are expensive or fragile
- LLM costs could spiral
- Scale requires infrastructure investment
- Non-technical team means support burden

### **My Recommendation**: Build in phases, validate at each step

**Phase 1** (Weeks 1-3): Monitoring MVP
- Risk: LOW
- Cost: $50-100/month
- Value: Immediate (automated intel emails)
- **Decision**: BUILD THIS NOW ✅

**Phase 2** (Weeks 4-6): Streamlit UI
- Risk: LOW
- Cost: $0 (free tier)
- Value: HIGH (enables team self-service)
- **Decision**: BUILD THIS NEXT ✅

**Phase 3** (Weeks 7-9): Reddit + Government APIs
- Risk: LOW
- Cost: $0
- Value: HIGH
- **Decision**: BUILD THIS ✅

**DECISION POINT**: After Phase 3, evaluate usage and decide:

**Phase 4a** (Weeks 10-12): Twitter integration
- **IF**: Budget allows ($100-5000/month)
- **IF**: Team actually needs Twitter data
- **IF**: Can't get data other ways (Nitter, etc.)
- **ELSE**: Skip and go to Phase 4b

**Phase 4b** (Weeks 10-12): AI analysis + Telegram
- Risk: MEDIUM
- Cost: $100-200/month
- Value: HIGH
- **Decision**: BUILD IF Phase 4a is skipped ✅

**Phase 5** (Months 4-5): Team UI
- Risk: MEDIUM
- Cost: $100-200/month
- Value: HIGH (if team is actually using platform)
- **Decision**: BUILD ONLY IF Phases 1-4 are heavily used

---

## Questions I Need Answered:

1. **What's your monthly budget for this platform?**
   - <$100/month? Skip Twitter, use free sources only
   - $200-500/month? Twitter Basic tier feasible
   - $1000+/month? All features possible

2. **Is Twitter critical to your investigations?**
   - If YES: Budget for $100-5000/month
   - If NO: Use Reddit, skip Twitter

3. **How many searches per day will your team run?**
   - <10/day: LLM costs ~$50/month
   - 50/day: LLM costs ~$300/month
   - 100+/day: LLM costs $500-1000/month

4. **What's your tolerance for maintenance?**
   - High: Build Telegram, TikTok (expect weekly fixes)
   - Low: Stick to stable APIs (government, Reddit)

5. **Timeline pressure?**
   - Need it in 1 month: Build Phase 1-2 only
   - Have 3-6 months: Build through Phase 4
   - Long-term project: Full vision feasible

---

**Should I proceed with building Phase 1 (monitoring MVP) given these risks?**

Or do you want to adjust the plan based on these concerns?
