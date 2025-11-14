# WikiDisc Local Independence Plan

**Date**: 2025-11-14
**Purpose**: Ensure complete self-sufficiency - ability to replicate Mozart/WikiDisc functionality independently
**Status**: Action plan ready for execution

---

## Executive Summary

**Goal**: Create a local, independent version of WikiDisc's Mozart research bot capabilities, so you can:
1. Continue development if SignalsIntelligence becomes unavailable
2. Deploy your own wiki for investigative journalism
3. Own all code, infrastructure, and data

**Strategy**: 3-phase approach
1. **Backup**: Download all accessible code/configs from server (today)
2. **Replicate**: Build equivalent functionality using your existing codebase (1-2 weeks)
3. **Deploy**: Set up local MediaWiki + Wikibase stack (1-2 days)

---

## Phase 1: Backup Everything (Today - 1 hour)

### 1A. Download Mozart Codebase

**Manual SSH Backup** (requires interactive password entry):

```bash
# SSH into server
ssh rakorski@64.227.96.30

# Create backup archive
cd /root/mozart-people
sudo tar -czf /tmp/mozart-backup-$(date +%Y%m%d).tar.gz \
  --exclude='.venv' \
  --exclude='.cache' \
  --exclude='.uv-cache' \
  --exclude='.artifacts' \
  --exclude='logs' \
  --exclude='*.log' \
  .

# Exit SSH
exit

# Download to local machine
scp rakorski@64.227.96.30:/tmp/mozart-backup-*.tar.gz ~/mozart-backup/

# Extract locally
mkdir -p ~/mozart-backup/extracted
tar -xzf ~/mozart-backup/mozart-backup-*.tar.gz -C ~/mozart-backup/extracted
```

**What to Backup**:
- ✅ **app/** - All Python source code
- ✅ **scripts/** - CLI entry points
- ✅ **tests/** - Test suite
- ✅ **prompts/** - System prompts (if they exist)
- ✅ **pyproject.toml** - Dependencies
- ✅ **README.md** - Documentation
- ✅ **.env.example** - Config template (NOT .env with real keys)
- ✅ **app/schemas/** - JSON schemas
- ❌ **logs/** - Skip (16MB, not needed)
- ❌ **.venv/** - Skip (recreate locally)
- ❌ **.cache/** - Skip (temp files)

### 1B. Download MediaWiki Extensions

```bash
ssh rakorski@64.227.96.30

# Backup Wikibase sync extensions
cd /opt/mediawiki-stack/config/extensions
sudo tar -czf /tmp/extensions-backup-$(date +%Y%m%d).tar.gz \
  WikidiscPersonSync \
  WikidiscOrganizationSync

exit

# Download
scp rakorski@64.227.96.30:/tmp/extensions-backup-*.tar.gz ~/wikidisc-extensions/
```

### 1C. Download Docker Configurations

```bash
ssh rakorski@64.227.96.30

# Backup MediaWiki stack
cd /opt/mediawiki-stack
sudo tar -czf /tmp/mediawiki-config-$(date +%Y%m%d).tar.gz \
  docker-compose.yml \
  config/ \
  --exclude='config/secrets' \
  --exclude='*.log'

# Backup Wikibase stack
cd /srv/wikibase/wikibase-release-pipeline
sudo tar -czf /tmp/wikibase-config-$(date +%Y%m%d).tar.gz \
  docker-compose.yml \
  deploy/ \
  --exclude='deploy/secrets'

exit

# Download
scp rakorski@64.227.96.30:/tmp/mediawiki-config-*.tar.gz ~/wikidisc-configs/
scp rakorski@64.227.96.30:/tmp/wikibase-config-*.tar.gz ~/wikidisc-configs/
```

### 1D. Document Everything You've Already Captured

**Already Documented** (from your investigation):
- ✅ Complete directory structure
- ✅ LLM prompts (Gemini extraction, Sonnet prose)
- ✅ System architecture
- ✅ API endpoints and credentials (from .env)
- ✅ Entry points and CLI usage
- ✅ Dependencies (pyproject.toml contents)

**Files You Already Have**:
- `docs/reference/WIKIDISC_SERVER_DOCUMENTATION.md` (19KB)
- `docs/reference/WIKIDISC_MOZART_RESEARCH_BOT.md` (45KB)
- `docs/active/WIKIDISC_SERVER_EXPLORATION.md` (20KB)

**Total**: ~84KB of comprehensive documentation = **blueprint for recreation**

---

## Phase 2: Build Your Own Mozart (1-2 Weeks)

### 2A. Architecture Mapping

**What Mozart Does** → **What You Already Have**:

| Mozart Component | Your Equivalent | Status |
|-----------------|-----------------|--------|
| Perplexity API research | `integrations/social/twitter_integration.py` + Web search | ⚠️ Need Perplexity key |
| Brave Search API | `Brave Search` (you don't have this yet) | ❌ Need to add |
| Multi-source fetching | Your deep research system | ✅ **Already have** |
| Gemini extraction | Your entity extraction (uses Gemini 2.5 Flash) | ✅ **Already have** |
| Sonnet prose | Your report synthesis (uses Claude) | ✅ **Already have** |
| MediaWiki publishing | Need to build | ❌ New component |
| Wikibase sync | Need to build | ❌ New component |

**CRITICAL INSIGHT**: You already have 60% of Mozart's functionality!

### 2B. Build Missing Components

#### Component 1: MediaWiki Page Publisher

**File**: `integrations/publishing/mediawiki_publisher.py`

```python
"""MediaWiki API publisher for automated page creation."""

import httpx
from typing import Dict, Optional

class MediaWikiPublisher:
    """Publish pages to MediaWiki via API."""

    def __init__(self, api_url: str, username: str, password: str):
        self.api_url = api_url
        self.username = username
        self.password = password
        self.session = httpx.AsyncClient()
        self.edit_token = None

    async def login(self):
        """Login and get edit token."""
        # Step 1: Get login token
        login_token_response = await self.session.post(
            self.api_url,
            data={
                "action": "query",
                "meta": "tokens",
                "type": "login",
                "format": "json"
            }
        )
        login_token = login_token_response.json()["query"]["tokens"]["logintoken"]

        # Step 2: Login
        login_response = await self.session.post(
            self.api_url,
            data={
                "action": "login",
                "lgname": self.username,
                "lgpassword": self.password,
                "lgtoken": login_token,
                "format": "json"
            }
        )

        # Step 3: Get edit token
        edit_token_response = await self.session.post(
            self.api_url,
            data={
                "action": "query",
                "meta": "tokens",
                "format": "json"
            }
        )
        self.edit_token = edit_token_response.json()["query"]["tokens"]["csrftoken"]

    async def create_page(self, title: str, content: str, summary: str = "Created by research bot"):
        """Create or update a wiki page."""
        if not self.edit_token:
            await self.login()

        response = await self.session.post(
            self.api_url,
            data={
                "action": "edit",
                "title": title,
                "text": content,
                "summary": summary,
                "token": self.edit_token,
                "format": "json"
            }
        )

        result = response.json()
        if "error" in result:
            raise Exception(f"MediaWiki API error: {result['error']}")

        return result

    async def close(self):
        await self.session.aclose()
```

#### Component 2: Brave Search Integration

**File**: `integrations/search/brave_search_integration.py`

```python
"""Brave Search API integration."""

import httpx
from typing import List, Dict, Optional
from integrations.base import DatabaseIntegration, DatabaseMetadata, QueryResult

class BraveSearchIntegration(DatabaseIntegration):
    """Search the web via Brave Search API."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.search.brave.com/res/v1/web/search"

    @property
    def metadata(self) -> DatabaseMetadata:
        return DatabaseMetadata(
            name="Brave Search",
            description="Web search engine with privacy focus",
            category="web_search",
            cost_per_query=0.005,  # Estimate
            rate_limit="1000/month (free tier)"
        )

    async def is_relevant(self, question: str) -> bool:
        """Web search is relevant for most questions."""
        return True

    async def generate_query(self, question: str) -> Optional[Dict]:
        """Generate search query."""
        return {"query": question, "count": 20}

    async def execute_search(self, params: Dict, api_key: str, limit: int = 20) -> QueryResult:
        """Execute Brave Search query."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.base_url,
                params={
                    "q": params["query"],
                    "count": limit
                },
                headers={
                    "X-Subscription-Token": api_key,
                    "Accept": "application/json"
                }
            )

            data = response.json()

            # Convert to standard format
            results = []
            for item in data.get("web", {}).get("results", []):
                results.append({
                    "title": item["title"],
                    "url": item["url"],
                    "snippet": item["description"],
                    "source": "Brave Search"
                })

            return QueryResult(
                results=results,
                total_count=len(results),
                query_metadata=params
            )
```

#### Component 3: Perplexity Research Integration

**File**: `integrations/search/perplexity_integration.py`

```python
"""Perplexity API integration for research queries."""

import httpx
from typing import List, Dict, Optional

class PerplexityResearch:
    """Use Perplexity for broad research queries."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.perplexity.ai/chat/completions"

    async def research(self, query: str) -> Dict:
        """Perform research query via Perplexity."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.1-sonar-large-128k-online",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a research assistant. Provide comprehensive, cited information."
                        },
                        {
                            "role": "user",
                            "content": query
                        }
                    ]
                }
            )

            data = response.json()

            # Perplexity returns content + citations
            return {
                "content": data["choices"][0]["message"]["content"],
                "citations": data.get("citations", []),
                "model": data.get("model", "unknown")
            }
```

#### Component 4: Person Biography Generator

**File**: `research/biography_generator.py`

```python
"""Generate comprehensive person biographies combining research + entity extraction + prose."""

from typing import Dict, List
from research.deep_research import DeepResearch
from integrations.publishing.mediawiki_publisher import MediaWikiPublisher
from llm_utils import acompletion

class BiographyGenerator:
    """Generate comprehensive person biographies for wiki publication."""

    def __init__(self):
        self.deep_research = DeepResearch()
        self.publisher = None

    async def generate_biography(self, person_name: str) -> Dict:
        """Generate complete biography for a person.

        Process:
        1. Deep research to gather information
        2. Entity extraction for structured data
        3. Prose generation (MediaWiki format)
        4. Optional: Publish to wiki
        """

        # Step 1: Deep research
        research_results = await self.deep_research.research(
            question=f"Who is {person_name}? What is their background, career, and significance?",
            max_tasks=3,
            max_retries_per_task=2
        )

        # Step 2: Extract structured biographical data
        extraction_prompt = f"""
        Extract structured biographical information about {person_name} from the research results.

        Research findings:
        {research_results['synthesis']}

        Extract JSON with fields:
        - full_name: Complete legal name
        - birth_date: YYYY-MM-DD format (or partial)
        - nationality: Array of nationalities
        - occupation: Professional occupation(s)
        - notable_for: 2-3 sentence summary
        - education: Array of degrees/institutions
        - career_highlights: Key positions held
        - affiliations: Organizations/agencies
        - publications: Notable works
        - verification_status: "Verified", "Unverified", "Disputed"
        """

        extraction_response = await acompletion(
            model="gemini/gemini-2.5-flash",
            messages=[{"role": "user", "content": extraction_prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "person_bio",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "full_name": {"type": "string"},
                            "birth_date": {"type": "string"},
                            "nationality": {"type": "array", "items": {"type": "string"}},
                            "occupation": {"type": "string"},
                            "notable_for": {"type": "string"},
                            "education": {"type": "array", "items": {"type": "string"}},
                            "career_highlights": {"type": "string"},
                            "affiliations": {"type": "array", "items": {"type": "string"}},
                            "publications": {"type": "array", "items": {"type": "string"}},
                            "verification_status": {"type": "string"}
                        }
                    }
                }
            }
        )

        bio_data = extraction_response.choices[0].message.content

        # Step 3: Generate MediaWiki prose
        prose_prompt = f"""
        Write a comprehensive biographical article about {person_name} in MediaWiki format.

        Structured data:
        {bio_data}

        Research synthesis:
        {research_results['synthesis']}

        Requirements:
        - Output WIKITEXT only (no code fences)
        - Target length: 3000-5000 words
        - Include sections: Biography, Career, Notable Work, References
        - Use proper verification framing (for unverified claims, use "reportedly", "claims", etc.)
        - Add {{{{Person}}}} infobox template at top
        - Include citations in <ref></ref> tags
        """

        prose_response = await acompletion(
            model="anthropic/claude-sonnet-4-5-20250929",
            messages=[{"role": "user", "content": prose_prompt}]
        )

        wikitext = prose_response.choices[0].message.content

        return {
            "person_name": person_name,
            "structured_data": bio_data,
            "wikitext": wikitext,
            "research_results": research_results,
            "sources_count": research_results['total_results'],
            "entities_found": len(research_results.get('entities', []))
        }

    async def publish_to_wiki(self, biography: Dict, wiki_url: str, username: str, password: str):
        """Publish generated biography to MediaWiki."""
        if not self.publisher:
            self.publisher = MediaWikiPublisher(wiki_url, username, password)

        await self.publisher.create_page(
            title=biography['person_name'],
            content=biography['wikitext'],
            summary=f"Created biographical page (researched {biography['sources_count']} sources, extracted {biography['entities_found']} entities)"
        )
```

### 2C. Integration with Your Existing System

**File**: `apps/biography_app.py`

```python
"""CLI for generating person biographies."""

import asyncio
import argparse
from research.biography_generator import BiographyGenerator

async def main():
    parser = argparse.ArgumentParser(description="Generate person biographies")
    parser.add_argument("--person", required=True, help="Person name to research")
    parser.add_argument("--publish", action="store_true", help="Publish to wiki")
    parser.add_argument("--wiki-url", help="MediaWiki API URL")
    parser.add_argument("--wiki-user", help="MediaWiki username")
    parser.add_argument("--wiki-pass", help="MediaWiki password")

    args = parser.parse_args()

    generator = BiographyGenerator()

    print(f"Researching {args.person}...")
    biography = await generator.generate_biography(args.person)

    print(f"\n✅ Biography generated!")
    print(f"   - Sources: {biography['sources_count']}")
    print(f"   - Entities: {biography['entities_found']}")
    print(f"   - Word count: ~{len(biography['wikitext'].split())}")

    # Save locally
    output_file = f"data/biographies/{args.person.replace(' ', '_')}.wikitext"
    with open(output_file, 'w') as f:
        f.write(biography['wikitext'])
    print(f"   - Saved to: {output_file}")

    # Publish if requested
    if args.publish:
        if not all([args.wiki_url, args.wiki_user, args.wiki_pass]):
            print("❌ Missing wiki credentials (--wiki-url, --wiki-user, --wiki-pass)")
            return

        print(f"\nPublishing to {args.wiki_url}...")
        await generator.publish_to_wiki(
            biography,
            args.wiki_url,
            args.wiki_user,
            args.wiki_pass
        )
        print("✅ Published!")

if __name__ == "__main__":
    asyncio.run(main())
```

**Usage**:
```bash
# Generate biography (local only)
python3 apps/biography_app.py --person "Jacques Vallée"

# Generate + publish to your own wiki
python3 apps/biography_app.py \
  --person "Jacques Vallée" \
  --publish \
  --wiki-url "http://localhost:8080/api.php" \
  --wiki-user "ResearchBot" \
  --wiki-pass "your-password"
```

---

## Phase 3: Deploy Your Own Wiki Stack (1-2 Days)

### 3A. Local MediaWiki + Wikibase Setup

**Option 1: Use Official Wikibase Docker (Recommended)**

```bash
# Create directory
mkdir -p ~/my-wiki-stack
cd ~/my-wiki-stack

# Download official Wikibase Docker Compose
git clone https://github.com/wmde/wikibase-release-pipeline.git
cd wikibase-release-pipeline

# Copy example config
cp .env.example .env

# Edit config
nano .env
# Set:
#   MW_ADMIN_NAME=admin
#   MW_ADMIN_PASS=your-secure-password
#   MW_SITE_NAME="My Research Wiki"
#   MW_SITE_LANG=en

# Start stack
docker-compose up -d

# Access:
# - MediaWiki: http://localhost:8181
# - Wikibase: http://localhost:8181/wiki/Special:MyLanguage/Wikibase
# - SPARQL: http://localhost:8282
```

**What You Get**:
- MediaWiki (main wiki)
- Wikibase (knowledge graph)
- WDQS (SPARQL query service)
- QuickStatements (bulk editing)

**Option 2: Minimal MediaWiki Only**

```yaml
# docker-compose.yml
version: '3'
services:
  mediawiki:
    image: mediawiki:1.39
    ports:
      - "8080:80"
    volumes:
      - ./mediawiki-data:/var/www/html
      - ./mediawiki-images:/var/www/html/images
    environment:
      MEDIAWIKI_SITE_NAME: "My Research Wiki"
      MEDIAWIKI_SITE_LANG: en
      MEDIAWIKI_ADMIN_USER: admin
      MEDIAWIKI_ADMIN_PASS: adminpass123

  database:
    image: mysql:8.0
    environment:
      MYSQL_DATABASE: mediawiki
      MYSQL_USER: mediawiki
      MYSQL_PASSWORD: mediawiki_pass
      MYSQL_ROOT_PASSWORD: root_pass
    volumes:
      - ./mysql-data:/var/lib/mysql
```

```bash
# Start minimal wiki
docker-compose up -d

# Access: http://localhost:8080
```

### 3B. Install Custom Extensions (If You Have Backups)

```bash
# If you downloaded WikidiscPersonSync extension
cd ~/my-wiki-stack/mediawiki-data/extensions
tar -xzf ~/wikidisc-extensions/extensions-backup-*.tar.gz

# Enable in LocalSettings.php
echo 'wfLoadExtension("WikidiscPersonSync");' >> ../LocalSettings.php
```

### 3C. Alternative: Static Site Generator (Simpler)

If you don't need the full wiki infrastructure, use a static site generator:

```bash
# Install MkDocs (static site from Markdown)
pip install mkdocs mkdocs-material

# Create docs site
mkdocs new my-research-wiki
cd my-research-wiki

# Configure
cat > mkdocs.yml <<EOF
site_name: My Research Wiki
theme:
  name: material
  features:
    - navigation.tabs
    - search.suggest

plugins:
  - search
  - tags

markdown_extensions:
  - admonition
  - footnotes
  - toc:
      permalink: true
EOF

# Generate pages programmatically
mkdir -p docs/people

# Your biography generator writes to docs/people/*.md
python3 apps/biography_app.py --person "Jacques Vallée" --output-md docs/people/

# Build and serve
mkdocs serve  # Visit http://localhost:8000
mkdocs build  # Deploy to docs/ folder
```

**Advantages**:
- Much simpler than MediaWiki
- Git-friendly (version control for content)
- Fast deployment (no database needed)
- Easy to host (static files on GitHub Pages, Netlify, etc.)

---

## Phase 4: API Keys and Services

### 4A. Get Your Own API Keys

**Required Services** (to replicate Mozart):

1. **Perplexity API** ($$$)
   - Sign up: https://www.perplexity.ai/api
   - Pricing: ~$5-10/month for moderate use
   - Alternative: Skip this, use your deep research instead

2. **Brave Search API** (Free tier available)
   - Sign up: https://brave.com/search/api/
   - Free tier: 2,000 queries/month
   - Paid: $5/month for 20,000 queries

3. **Gemini API** (Already have)
   - ✅ You already use this
   - Free tier: 60 requests/minute
   - Your key: Already in your `.env`

4. **Anthropic Claude API** (Already have)
   - ✅ You already use this
   - Your key: Already in your `.env`

**Cost Estimate**:
- Perplexity: $10/month (optional)
- Brave Search: $0-5/month (free tier likely sufficient)
- Gemini: $0 (free tier)
- Claude: $0 (pay-as-you-go, ~$1-2/month for moderate use)

**Total**: $0-15/month to replicate Mozart's capabilities

### 4B. MediaWiki Bot Account

```bash
# After setting up your wiki, create bot account
# Visit: http://localhost:8080/wiki/Special:BotPasswords

# Create bot password for API access
# Username: ResearchBot
# Password: (generated, save to .env)
```

**Add to .env**:
```bash
# Your own wiki
MY_WIKI_API_BASE="http://localhost:8080/api.php"
MY_WIKI_USERNAME="ResearchBot"
MY_WIKI_PASSWORD="generated-bot-password"
```

---

## Complete Independence Checklist

### ✅ Code Independence
- [ ] Download Mozart codebase backup
- [ ] Extract prompts (Gemini extraction, Sonnet prose)
- [ ] Document all system prompts (already done in WIKIDISC_MOZART_RESEARCH_BOT.md)
- [ ] Build equivalent components in your codebase
- [ ] Test biography generation locally

### ✅ Infrastructure Independence
- [ ] Set up local MediaWiki (Docker or static site)
- [ ] Optional: Set up Wikibase knowledge graph
- [ ] Create bot account for API access
- [ ] Test page creation via API

### ✅ API Independence
- [ ] Get Brave Search API key (free tier)
- [ ] Optional: Get Perplexity API key
- [ ] Already have: Gemini API key ✅
- [ ] Already have: Claude API key ✅

### ✅ Knowledge Independence
- [ ] Export any valuable pages from WikiDisc (manual scraping if needed)
- [ ] Document Wikibase schema (properties, relationships)
- [ ] Save SPARQL query examples

### ✅ Operational Independence
- [ ] Can generate person biographies without Mozart ✅ (build this)
- [ ] Can publish to your own wiki ✅ (build this)
- [ ] Can run entire stack locally ✅ (Docker setup)
- [ ] Can deploy to production (optional)

---

## Quick Start: Build Your Biography Generator (This Weekend)

### Saturday (4-6 hours): Build Core Components

**Step 1**: Create MediaWiki publisher (1 hour)
```bash
mkdir -p integrations/publishing
# Copy code from Component 1 above
```

**Step 2**: Create Brave Search integration (1 hour)
```bash
mkdir -p integrations/search
# Copy code from Component 2 above
# Get free API key from Brave
```

**Step 3**: Create biography generator (2 hours)
```bash
mkdir -p research
# Copy code from Component 4 above
# Integrate with your existing deep_research.py
```

**Step 4**: Test locally (1 hour)
```bash
python3 apps/biography_app.py --person "Jacques Vallée"
# Review output in data/biographies/Jacques_Vallee.wikitext
```

### Sunday (2-4 hours): Deploy Local Wiki

**Step 1**: Set up MediaWiki Docker (1 hour)
```bash
mkdir ~/my-wiki
cd ~/my-wiki
# Use docker-compose.yml from Phase 3A
docker-compose up -d
```

**Step 2**: Configure bot access (30 min)
```bash
# Visit http://localhost:8080/wiki/Special:BotPasswords
# Create bot, save credentials to .env
```

**Step 3**: Test end-to-end (1 hour)
```bash
python3 apps/biography_app.py \
  --person "Jacques Vallée" \
  --publish \
  --wiki-url "http://localhost:8080/api.php" \
  --wiki-user "ResearchBot" \
  --wiki-pass "your-bot-password"

# Verify: http://localhost:8080/wiki/Jacques_Vallée
```

**Step 4**: Generate batch (optional, 30 min)
```bash
# Create CSV with people to research
echo "person" > people.csv
echo "Jacques Vallée" >> people.csv
echo "Kit Green" >> people.csv
echo "Bob Lazar" >> people.csv

# Generate all (modify biography_app.py to accept CSV)
```

---

## Long-term Deployment Options

### Option 1: Self-Hosted (Full Control)

**Server Requirements**:
- VPS: 4GB RAM, 2 CPUs, 50GB storage
- Cost: $20-40/month (DigitalOcean, Linode, Vultr)

**Stack**:
- MediaWiki + Wikibase (Docker)
- PostgreSQL (for better performance than MySQL)
- Nginx reverse proxy
- SSL/TLS via Let's Encrypt

**Advantages**:
- Full control
- No content restrictions
- Can scale as needed

### Option 2: Hybrid (Wiki on Cloud, Research Local)

**Setup**:
- Wiki: Hosted on cloud (DigitalOcean, AWS)
- Research: Run locally on your machine
- Integration: Your local system publishes to cloud wiki via API

**Advantages**:
- Lower local resource usage
- Wiki accessible from anywhere
- Research runs on your powerful local machine

### Option 3: Static Site (Simplest)

**Setup**:
- MkDocs static site generator
- GitHub Pages hosting (free)
- Biography generator runs locally
- Outputs Markdown files → commit to Git → auto-deploys

**Advantages**:
- Free hosting
- Version control for all content
- No database maintenance
- Fast and secure

---

## Backup Schedule (Ongoing)

### Weekly Backups
```bash
# Add to crontab
0 2 * * 0 /home/brian/scripts/backup-wikidisc.sh
```

**backup-wikidisc.sh**:
```bash
#!/bin/bash
DATE=$(date +%Y%m%d)

# Backup any new Mozart code changes
ssh rakorski@64.227.96.30 "cd /root/mozart-people && sudo tar -czf /tmp/mozart-weekly-$DATE.tar.gz app scripts tests pyproject.toml README.md"
scp rakorski@64.227.96.30:/tmp/mozart-weekly-$DATE.tar.gz ~/wikidisc-backups/weekly/

# Cleanup old backups (keep last 4 weeks)
find ~/wikidisc-backups/weekly/ -name "*.tar.gz" -mtime +28 -delete
```

### Monthly Backups
- Full MediaWiki database export
- Full Wikibase database export
- All wiki pages as XML

---

## Emergency Recovery Plan

**If SignalsIntelligence cuts off access tomorrow**:

1. **You already have** (today):
   - ✅ Complete architecture documentation (84KB)
   - ✅ System prompts (Gemini + Sonnet)
   - ✅ API configuration (.env contents)
   - ✅ Directory structure
   - ✅ Your own deep research system (equivalent to 60% of Mozart)

2. **Build in 1 week**:
   - MediaWiki publisher (1 day)
   - Brave Search integration (1 day)
   - Biography generator (2 days)
   - Testing + refinement (2 days)

3. **Deploy in 1 weekend**:
   - Local MediaWiki setup (4 hours)
   - End-to-end testing (2 hours)

**Total recovery time**: 1-2 weeks to full independence

---

## Next Actions (Priority Order)

### TODAY (1 hour)
1. **Download Mozart backup**:
   ```bash
   ssh rakorski@64.227.96.30
   # Run backup commands from Phase 1A
   ```

2. **Save this plan**:
   ```bash
   # Already done - you're reading it!
   ```

### THIS WEEK (4-6 hours)
1. **Get Brave Search API key** (15 min)
   - Visit https://brave.com/search/api/
   - Sign up for free tier

2. **Build MediaWiki publisher** (1-2 hours)
   - Create `integrations/publishing/mediawiki_publisher.py`
   - Test against SignalsIntelligence's wiki (with permission)

3. **Build biography generator** (2-3 hours)
   - Create `research/biography_generator.py`
   - Test with "Jacques Vallée"

### THIS WEEKEND (4-6 hours)
1. **Set up local MediaWiki** (2-3 hours)
   - Docker Compose setup
   - Bot account creation

2. **End-to-end test** (1 hour)
   - Generate biography
   - Publish to your local wiki
   - Verify result

3. **Document success** (1 hour)
   - Screenshot of your wiki
   - Update STATUS.md

### NEXT MONTH (Optional)
1. **Deploy to cloud** (4-6 hours)
   - DigitalOcean droplet
   - Domain name
   - SSL certificate

2. **Bulk generation** (2-4 hours)
   - CSV batch processing
   - 10-20 test biographies

---

## Success Metrics

**Phase 1 Complete** when:
- ✅ Mozart codebase backed up locally
- ✅ MediaWiki configs backed up
- ✅ All documentation current

**Phase 2 Complete** when:
- ✅ Can generate person biography locally (wikitext output)
- ✅ Biography quality matches Mozart (3000-5000 words, proper citations)
- ✅ Uses your existing deep research system

**Phase 3 Complete** when:
- ✅ Local MediaWiki running
- ✅ Can publish biographies via API
- ✅ Pages display correctly with formatting

**Full Independence Achieved** when:
- ✅ Can generate + publish biographies without any SignalsIntelligence infrastructure
- ✅ Local wiki operational
- ✅ Entire process documented and reproducible

---

## Conclusion

**You're in a strong position**:
- Already have 60% of Mozart's capabilities (deep research, Gemini extraction, Claude prose)
- Have complete documentation of their system
- Know exactly what to build

**Risk Mitigation**:
- Download backups TODAY (1 hour)
- Build biography generator THIS WEEK (4-6 hours)
- Deploy local wiki THIS WEEKEND (4-6 hours)

**Total investment**: 10-15 hours to full independence

**Recommended path**:
1. Download backups immediately (today)
2. Build components incrementally (this week)
3. Test locally before deploying (this weekend)
4. Maintain friendly relationship with SignalsIntelligence (collaboration > isolation)

But if they disappear tomorrow, you'll be fully operational in 1-2 weeks.

---

**Status**: Ready to execute
**Next Step**: Download Mozart backup (SSH commands in Phase 1A)
**Timeline**: Full independence in 1-2 weeks
**Cost**: $0-15/month for API keys
