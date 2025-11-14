# WikiDisc Server Documentation

**Last Updated**: 2025-11-14
**Server**: 64.227.96.30 (DigitalOcean Droplet)
**Collaborator**: SignalsIntelligence
**Project**: UFO/UAP Research Wiki with Knowledge Graph

---

## Table of Contents

1. [Quick Access](#quick-access)
2. [Server Overview](#server-overview)
3. [Infrastructure Stack](#infrastructure-stack)
4. [Directory Structure](#directory-structure)
5. [Automation Scripts](#automation-scripts)
6. [Docker Containers](#docker-containers)
7. [Cron Jobs](#cron-jobs)
8. [Key Findings](#key-findings)
9. [Integration Opportunities](#integration-opportunities)
10. [Next Steps](#next-steps)

---

## Quick Access

### SSH Connection
```bash
ssh rakorski@64.227.96.30
# Password: qebcys-Nuwzip-xadky0
```

### Live Sites
- **Main Wiki**: https://www.wikidisc.org
- **Wikibase**: https://data.wikidisc.org
- **Query Service**: https://query.wikidisc.org
- **QuickStatements**: https://qs.wikidisc.org

### Key Directories
- **Main Wiki**: `/opt/mediawiki-stack`
- **Wikibase**: `/srv/wikibase/wikibase-release-pipeline`
- **Wikibase Extensions**: `/var/www/html/extensions/Wikibase` (inside Docker container `wbs-deploy-wikibase-1`)
- **Backups**: `/home/rakorski/wikidisc-backup`

---

## Server Overview

### System Information
```
Platform: DigitalOcean Droplet
OS: Ubuntu 24.04.3 LTS
Kernel: 6.8.0-87-generic x86_64
RAM: 8GB (53% used)
Swap: 99% used (concerning - may need expansion)
CPU: 2 AMD CPUs
Disk:
  - /dev/vda1: 48GB (73% used)
  - /dev/sda: 49GB (50% used) - mounted at /mnt/wikidiscblock_1
System Load: 1.04
```

### Users
- **root**: System administrator (has Claude Code access at `/opt/mediawiki-stack/.claude/`)
- **rakorski**: Your account (admin access)
- **dev**: Development account (mostly empty, unused)

---

## Infrastructure Stack

### Docker Compose Services

Located at: `/opt/mediawiki-stack/docker-compose.yml`

#### Core Services
1. **nginx-proxy-manager** (jc21/nginx-proxy-manager:latest)
   - Reverse proxy and SSL certificate management
   - Ports: 80, 81, 443
   - Web UI: Port 81

2. **mariadb** (mariadb:10.11)
   - Main database for MediaWiki
   - Max connections: 100
   - Buffer pool: 256MB
   - Character set: utf8mb4

3. **redis** (redis:7-alpine)
   - Cache layer for MediaWiki
   - Max memory: 128MB
   - Eviction policy: allkeys-lru

4. **elasticsearch** (elasticsearch:7.10.2)
   - Search indexing
   - Heap size: 512MB
   - Single-node deployment

5. **mediawiki** (ufodocs-mediawiki:latest - custom built)
   - Main wiki application
   - PHP memory limit: 512MB
   - Max upload: 100MB
   - Port: 8080 (internal)
   - Key integrations:
     - Wikibase sync enabled
     - Turnstile CAPTCHA
     - SMTP email
     - Redis caching
     - Elasticsearch search

#### Monitoring Stack
6. **statsd-exporter** (prom/statsd-exporter:v0.26.0)
   - Metrics collection
   - Memory limit: 128MB

7. **prometheus** (prom/prometheus:v2.48.0)
   - Time-series database
   - Retention: 15 days
   - Memory limit: 1GB

8. **alertmanager** (prom/alertmanager:v0.26.0)
   - Alert routing and management
   - Memory limit: 128MB

9. **grafana** (grafana/grafana:10.2.2)
   - Monitoring dashboards
   - Memory limit: 256MB

### Wikibase Stack (Separate Compose)

Located at: `/srv/wikibase/wikibase-release-pipeline`

**Running Containers**:
1. **wbs-deploy-wikibase-1** (wikibase/wikibase:5)
   - Main Wikibase instance
   - Connected to main MediaWiki

2. **wbs-deploy-wikibase-jobrunner-1**
   - Background job processor

3. **wbs-deploy-wdqs-1** & **wbs-deploy-wdqs-updater-1** (wikibase/wdqs:2)
   - Wikidata Query Service
   - SPARQL endpoint

4. **wbs-deploy-quickstatements-1** (wikibase/quickstatements:1)
   - Bulk editing tool

5. **wbs-deploy-elasticsearch-1** (wikibase/elasticsearch:1)
   - Dedicated search for Wikibase

6. **wbs-deploy-wdqs-frontend-1** (wikibase/wdqs-frontend:2)
   - Query interface

7. **wbs-deploy-mysql-1** (mariadb:10.11)
   - Wikibase database

### Analytics
- **matomo-analytics** (matomo:latest)
  - Web analytics
  - Port: 8081 (localhost only)

---

## Directory Structure

### `/opt/mediawiki-stack/` (Main Wiki)

```
/opt/mediawiki-stack/
├── .claude/                      # Claude Code configuration
│   └── settings.local.json       # Claude settings
├── config/                       # MediaWiki configuration
│   ├── extra_localsettings.php   # Custom MW settings
│   ├── LocalSettings.d/          # Modular settings
│   ├── extensions/               # Custom extensions
│   ├── secrets/                  # API keys, passwords
│   ├── robots.txt                # SEO/crawler control
│   └── php-security.ini          # PHP security hardening
├── docker/
│   └── mediawiki/
│       └── Dockerfile            # Custom MediaWiki image
├── monitoring/                   # Prometheus/Grafana configs
│   ├── prometheus/
│   ├── grafana/
│   ├── alertmanager/
│   └── statsd/
├── scripts/                      # Automation scripts
│   ├── backup-*.sh               # Backup scripts
│   ├── deploy-*.sh               # Deployment scripts
│   ├── run-jobs.sh               # MediaWiki job runner
│   └── forms/                    # Form definitions
├── logs/                         # Application logs
├── docs/                         # Documentation
├── docker-compose.yml            # Main stack definition
└── *.py                          # Python automation scripts (~50 files)
```

### `/srv/wikibase/` (Knowledge Graph)

```
/srv/wikibase/
└── wikibase-release-pipeline/
    ├── deploy/
    │   ├── docker-compose.yml
    │   └── scripts/
    │       ├── backup-*.sh
    │       └── maintenance/
    └── config/
```

---

## Automation Scripts

### Page Creation Scripts (Python)

Located at: `/opt/mediawiki-stack/*.py`

**Pattern**: Simple template-based page creation using MediaWiki API

**Key Scripts**:
- `create_policy_pages.py` - Creates About, Privacy Policy, Disclaimer pages
- `create_category_pages.py` - Creates category pages
- `create_aaro_page.py` - Creates AARO (government office) page
- `create_aawsap_page.py` - Creates AAWSAP program page
- `create_lockheed_martin_page.py` - Creates Lockheed Martin organization page

**How They Work**:
1. Hardcoded page content using MediaWiki templates (e.g., `{{Org_Enhanced}}`, `{{Person_Enhanced}}`)
2. MediaWiki API authentication (WikiAdmin user)
3. Direct page creation via API

**Example Structure** (from `create_lockheed_martin_page.py`):
```python
PAGE_CONTENT = """{{Org_Enhanced
|org_name=Lockheed Martin Corporation
|org_acronym=LMT
|org_type=Private company
|country=United States
...
}}

== Overview ==
Content here...

== References ==
<references />
"""
```

**NOT AI-Powered**: These scripts use pre-written content, not automated research.

### CSS/Styling Scripts (Python)

**Purpose**: Update MediaWiki CSS and dark mode styling

**Examples**:
- `fix_common_css.py`
- `update_infobox_dark_mode.py`
- `add_dark_mode_th_background.py`
- `fix_template_inline_backgrounds.py`

### Deployment Scripts (Bash)

Located at: `/opt/mediawiki-stack/scripts/`

**Key Scripts**:
- `deploy-form-enhanced.sh` - Deploy MediaWiki forms
- `deploy-person-template.sh` - Deploy person template
- `deploy-case-v2.sh` - Deploy case template
- `backup-*.sh` - Various backup scripts

### Wikibase Integration

**File**: `/opt/mediawiki-stack/config/extra_localsettings.php`

**Integration Points**:
- Wikibase API endpoint: `$wgWikibaseAPIEndpoint`
- Wikibase site ID: `$wgWikibaseSiteId`
- Sync username/password: `$wgWikibaseSyncUsername`, `$wgWikibaseSyncPassword`
- Sync enabled flag: `$wgWikibaseSyncEnabled`

**How It Works**:
- MediaWiki pages can reference Wikibase items
- Automatic syncing of entities from wiki to knowledge graph
- ~130 people already synced to Wikibase

---

## Docker Containers

### Running Containers (19 total)

**MediaWiki Stack** (11 containers):
```
mediawiki                    (port 8080 → 80)
mediawiki-mariadb           (3306)
mediawiki-redis             (6379)
mediawiki-elasticsearch     (9200, 9300)
nginx-proxy-manager         (80, 81, 443)
mediawiki-prometheus        (9090)
mediawiki-grafana           (3000)
mediawiki-alertmanager      (9093)
mediawiki-statsd-exporter   (9102, 9125)
matomo-analytics            (127.0.0.1:8081)
matomo-db-1                 (3306)
```

**Wikibase Stack** (8 containers):
```
wbs-deploy-wikibase-1              (80)
wbs-deploy-wikibase-jobrunner-1    (80)
wbs-deploy-wdqs-1                  (9999)
wbs-deploy-wdqs-updater-1          (9999)
wbs-deploy-wdqs-frontend-1         (80)
wbs-deploy-quickstatements-1       (80)
wbs-deploy-elasticsearch-1         (9200, 9300)
wbs-deploy-mysql-1                 (3306)
```

### Custom Docker Images

**Built Images**:
- `ufodocs-mediawiki:latest` (1.48GB) - Custom MediaWiki with extensions
- `wikibase-custom:local` (2.01GB) - Customized Wikibase
- `wdqs-updater-patched:local` (460MB) - Patched WDQS updater

---

## Cron Jobs

Located at: `/etc/crontab` and root's crontab

### MediaWiki Jobs
```bash
# MediaWiki job queue (every 5 minutes)
*/5 * * * * /opt/mediawiki-stack/scripts/run-jobs.sh

# StopForumSpam anti-spam list (daily at 2am)
0 2 * * * /opt/mediawiki-stack/scripts/update-stopforumspam.sh
```

### Backups
```bash
# Daily MediaWiki backup (2am)
0 2 * * * /opt/mediawiki-stack/scripts/backup-all.sh

# Weekly XML backup (Sundays 3am)
0 3 * * 0 /opt/mediawiki-stack/scripts/backup-xml.sh

# Daily backup retention cleanup (6am)
0 6 * * * /opt/mediawiki-stack/scripts/backup-retention-b2.sh

# Daily Wikibase backup (2:30am - offset from main)
30 2 * * * /srv/wikibase/wikibase-release-pipeline/deploy/scripts/backup-all.sh

# Weekly Wikibase WDQS backup (Sundays 3:30am)
30 3 * * 0 /srv/wikibase/wikibase-release-pipeline/deploy/scripts/backup-wdqs.sh

# Weekly Wikibase volume backup (Sundays 3:30am)
30 3 * * 0 /srv/wikibase/wikibase-release-pipeline/deploy/scripts/backup-volumes.sh

# Daily Wikibase retention cleanup (6:30am)
30 6 * * * /srv/wikibase/wikibase-release-pipeline/deploy/scripts/backup-retention-b2.sh
```

---

## Key Findings

### ❌ AI Research Bot NOT Found on Server

**Expected**: Automated research bot that:
- Searches Wikipedia and other sources
- Uses Claude/GPT to analyze information
- Creates comprehensive wiki pages automatically
- Mentioned in your conversation with SignalsIntelligence

**Reality**:
- Only found simple template-based page creation scripts
- No OpenAI/Anthropic API calls in existing scripts
- No evidence of deep research automation
- Scripts use hardcoded content, not AI generation

**Possible Locations**:
1. **On their local machine** - Friend runs research bot locally, then manually uploads
2. **In .claude directory** - `/opt/mediawiki-stack/.claude/` (only has settings, need to check deeper)
3. **Separate repository** - Research bot might be in a different repo/server
4. **Development in progress** - Bot might not be deployed yet

### ✅ What IS Working

1. **Wikibase Integration**
   - ~130 people synced from wiki to knowledge graph
   - SPARQL query interface functional
   - Automatic entity creation from wiki pages

2. **Page Templates**
   - Structured data forms (Person, Organization, Case, Place)
   - `{{Person_Enhanced}}`, `{{Org_Enhanced}}`, `{{Case_Enhanced}}` templates
   - Custom infoboxes with dark mode support

3. **Monitoring & Analytics**
   - Prometheus + Grafana monitoring
   - Matomo analytics tracking
   - Health checks on all services

4. **Backups**
   - Daily automated backups to Backblaze B2
   - XML exports for disaster recovery
   - 15-day retention policy

### ⚠️ Issues Identified

1. **Swap Usage at 99%** - Memory pressure, may need investigation
2. **No AI Research Automation** - Expected feature not found
3. **Docker Permission** - rakorski user can't access Docker without sudo

---

## Integration Opportunities

### Your System → WikiDisc Integration

Based on your conversation, here's how your systems could integrate:

#### 1. Entity Extraction → Wikibase Population

**Your System** (`sam_gov/research/deep_research.py`):
```python
# After deep research completes
entities = deep_research.extract_entities()
# entities = ["NSA", "Prism Program", "Edward Snowden", ...]
```

**Integration Point** (new script):
```python
# wikidisc_sync.py
import requests

WIKIBASE_API = "https://data.wikidisc.org/w/api.php"

def create_wikibase_item(entity_name, entity_type, properties):
    """Create Wikibase item via API"""
    # Login to Wikibase
    # Create item with label
    # Add properties (instance_of, inception, etc.)
    # Return item ID (Q123)
    pass

def sync_research_to_wikidisc(research_results):
    """Push research findings to WikiDisc"""
    for entity in research_results['entities']:
        item_id = create_wikibase_item(
            name=entity['name'],
            type=entity['type'],
            properties=entity['properties']
        )
        print(f"Created {entity['name']} as {item_id}")
```

#### 2. Monitoring Integration

**Your System** (`monitoring/adaptive_boolean_monitor.py`):
```python
# Daily SAM.gov contract monitoring
new_contracts = monitor.search("NSA cybersecurity contracts")

# Push findings to WikiDisc
for contract in new_contracts:
    # Create wiki page: [[Contract:{contract_id}]]
    # Link to organizations: NSA, Palantir, etc.
    # Update Wikibase relationships
```

#### 3. Deep Research → Wiki Page Generation

**Your System** (deep research):
```python
# Research question: "What is AARO?"
report = deep_research.research("What is AARO?")
# report = {
#   "summary": "...",
#   "entities": [...],
#   "sources": [...]
# }
```

**Integration**:
```python
# Generate MediaWiki markup from research
wiki_content = convert_report_to_mediawiki(report)

# Create page via MediaWiki API
create_wiki_page(
    title="All-domain Anomaly Resolution Office",
    content=wiki_content,
    categories=["Government Agencies", "UAP Research"]
)
```

### API Documentation

**MediaWiki API**:
- Endpoint: `https://www.wikidisc.org/api.php`
- Authentication: OAuth or bot password
- Actions: `edit`, `create`, `query`, `upload`

**Wikibase API**:
- Endpoint: `https://data.wikidisc.org/w/api.php`
- Authentication: Bot credentials required
- Actions: `wbeditentity`, `wbcreateclaim`, `wbsetlabel`

**SPARQL Query Service**:
- Endpoint: `https://query.wikidisc.org/sparql`
- No auth required (read-only)
- Query language: SPARQL

---

## Next Steps

### Immediate Actions

1. **Ask SignalsIntelligence**:
   - Where is the AI research bot?
   - Is it on their local machine?
   - Can they share the repository?

2. **Investigate `.claude` directory**:
   ```bash
   sudo cat /opt/mediawiki-stack/.claude/settings.local.json
   # Check for references to research scripts
   ```

3. **Check for Git repositories**:
   ```bash
   find /opt /srv /home -name ".git" 2>/dev/null
   # See if there are other repos we missed
   ```

4. **Look for requirements.txt**:
   ```bash
   find /opt /srv /home -name "requirements.txt" 2>/dev/null
   # Python dependencies might reveal AI packages
   ```

### Future Integration Work

1. **Design API wrapper** for WikiDisc integration
2. **Create sync service** that runs daily
3. **Build entity mapper** (your entities → Wikibase items)
4. **Set up webhook** for real-time updates

---

## Notes from Conversation

**From your Discord chat with SignalsIntelligence**:

> "What I've been doing for non UI related stuff is having claude give me the plan for changes, then asking what codex thinks about it, then giving codex's thoughts to claude, and then giving claude's final plan to codex to implement it, and then asking claude to evaluate the implementation and suggest improvements. It works really well."

**Their Workflow**:
1. Claude (ChatGPT) generates plan
2. Codex (Claude Code) reviews plan
3. Claude refines plan based on Codex feedback
4. Codex implements
5. Claude evaluates implementation

**Page Creation Mentions**:
- Friend said bot creates Case pages, Person pages, Organization pages
- Mentioned "page creation to a pretty good place"
- Creates "See Also" links even if pages don't exist yet
- Bot crawls created pages for "See Also" links and creates those pages too

**Knowledge Graph**:
- ~130 people automatically added to knowledge graph
- Anyone added to wiki automatically synced to Wikibase
- Uses wikibase.org system (same as Wikidata)
- Can mirror to Neo4j for visualization

---

## Useful Commands

### Check Docker Logs
```bash
sudo docker logs mediawiki --tail 100
sudo docker logs wbs-deploy-wikibase-1 --tail 100
```

### Restart Services
```bash
cd /opt/mediawiki-stack
sudo docker-compose restart mediawiki

cd /srv/wikibase/wikibase-release-pipeline
sudo docker-compose restart wikibase
```

### Check Disk Usage
```bash
df -h
du -sh /opt/mediawiki-stack/*
du -sh /mnt/wikidiscblock_1/*
```

### View Recent Wiki Edits
```bash
# Via API
curl "https://www.wikidisc.org/api.php?action=query&list=recentchanges&format=json"
```

### Query Wikibase
```bash
# Example SPARQL query
curl -G "https://query.wikidisc.org/sparql" \
  --data-urlencode "query=SELECT ?person WHERE { ?person wdt:P1 wd:Q4 } LIMIT 10"
```

---

## Contact

**Server Owner**: SignalsIntelligence
**Your Access**: rakorski user
**Support**: Discord (see conversation history)

---

**End of Documentation**
