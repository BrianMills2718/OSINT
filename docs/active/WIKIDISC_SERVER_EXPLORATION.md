# WikiDisc Server Exploration - 2025-11-14

**Server**: 64.227.96.30 (DigitalOcean VPS)
**SSH Access**: `ssh rakorski@64.227.96.30`
**Password**: (Verify with SignalsIntelligence - may have changed)

## Executive Summary

Explored SignalsIntelligence's WikiDisc production server to understand the architecture and identify integration opportunities with your research platform. The server runs a sophisticated MediaWiki + Wikibase stack with 18+ Docker containers for knowledge graph functionality.

---

## Server Infrastructure

### System Resources
- **OS**: Ubuntu 24.04.3 LTS
- **CPU**: 2 AMD vCPUs
- **RAM**: 8GB (53% usage)
- **Disk**:
  - `/`: 48GB (73% used - 35GB used)
  - `/mnt/wikidiscblock_1`: 49GB (50% used - 23GB used)
- **Swap**: 99% used (potential performance issue)

### Key Directories
```
/opt/mediawiki-stack/          # Main MediaWiki installation + automation scripts
/srv/wikibase/                 # Wikibase knowledge graph installation
/home/rakorski/wikidisc-backup # Backup storage
/home/dev/                     # Developer user (possible location of AI research bot)
```

---

## Docker Infrastructure (18 Containers)

### Core MediaWiki Stack (6 containers)
1. **mediawiki** (`ufodocs-mediawiki:latest`) - Main wiki application
   - Port: 8080 → 80
   - Custom built image (1.48GB)
   - Integrated with Wikibase sync

2. **mediawiki-mariadb** (`mariadb:10.11`) - Database
   - MySQL for wiki content
   - Character set: utf8mb4

3. **mediawiki-redis** (`redis:7-alpine`) - Caching
   - Password protected
   - 128MB max memory with LRU eviction

4. **mediawiki-elasticsearch** (`elasticsearch:7.10.2`) - Search
   - Single node cluster
   - 512MB Java heap

5. **nginx-proxy-manager** - Reverse proxy
   - Ports: 80, 81, 443
   - SSL/TLS termination
   - Manages: www.wikidisc.org

6. **matomo-analytics** - Web analytics
   - Port: 127.0.0.1:8081

### Wikibase Knowledge Graph Stack (6 containers)
7. **wbs-deploy-wikibase-1** (`wikibase/wikibase:5`) - Main Wikibase instance
   - Syncs with MediaWiki pages
   - API endpoint: (configured via env)

8. **wbs-deploy-wikibase-jobrunner-1** - Background job processor

9. **wbs-deploy-mysql-1** (`mariadb:10.11`) - Wikibase database

10. **wbs-deploy-elasticsearch-1** (`wikibase/elasticsearch:1`) - Wikibase search

11. **wbs-deploy-wdqs-1** (`wikibase/wdqs:2`) - SPARQL query service
    - Enables graph queries
    - Healthy status

12. **wbs-deploy-wdqs-updater-1** - SPARQL data updater

13. **wbs-deploy-wdqs-frontend-1** (`wikibase/wdqs-frontend:2`) - Query UI
    - Accessible at query.wikidisc.org

14. **wbs-deploy-quickstatements-1** (`wikibase/quickstatements:1`) - Batch editing tool
    - Accessible at qs.wikidisc.org

### Monitoring Stack (5 containers)
15. **mediawiki-prometheus** - Metrics collection
    - 15-day retention
    - 1GB memory limit

16. **mediawiki-grafana** - Metrics visualization
    - Admin access configured

17. **mediawiki-alertmanager** - Alert routing

18. **mediawiki-statsd-exporter** - StatsD → Prometheus bridge

19. **matomo-db-1** - Analytics database

---

## Automation Scripts

### Location: `/opt/mediawiki-stack/`

### Page Creation Scripts (AI-powered?)
```python
create_aaro_page.py              # Creates AARO organization page
create_aawsap_page.py            # Creates AAWSAP program page
create_category_pages.py         # Creates category pages
create_lockheed_martin_page.py   # Creates Lockheed Martin page
create_policy_pages.py           # Creates policy pages (About, Privacy)
```

**Pattern observed**:
- Scripts use MediaWiki API
- Basic template-based content (not deep research)
- Username: WikiAdmin
- Password from env: `MEDIAWIKI_ADMIN_PASS`

**Example from `create_policy_pages.py`**:
```python
WIKI_URL = "https://www.wikidisc.org"
API = f"{WIKI_URL}/api.php"
USERNAME = "WikiAdmin"
PASSWORD = os.environ.get('MEDIAWIKI_ADMIN_PASS')
```

### Template Deployment Scripts
```bash
deploy-case-v2.sh
deploy-form-enhanced.sh
deploy-person-template.sh
deploy-photo-organization.sh
deploy-place-enhanced.sh
```

### CSS/Styling Scripts (30+ files)
```python
add_badge_dark_mode.py
add_collapsible_video_css.py
add_dark_mode_th_background.py
fix_common_css.py
fix_dark_th_background_v2.py
update_infobox_dark_mode.py
# ... many more
```

### Backup Scripts
```bash
backup-all.sh
backup-config.sh
backup-database.sh
backup-retention-b2.sh
backup-uploads.sh
backup-xml.sh
```

### Maintenance Scripts
```bash
run-jobs.sh                      # MediaWiki job queue
update-stopforumspam.sh          # Anti-spam updates
```

---

## Configuration Files

### Location: `/opt/mediawiki-stack/config/`

### Key Files
```
extra_localsettings.php          # MediaWiki configuration overrides
php-security.ini                 # PHP security settings
robots.txt                       # Search engine crawling rules

# Templates (Semantic MediaWiki forms)
Form_Case_Enhanced.wiki
Form_Person_Enhanced.wiki
Template_Case_Enhanced.wiki
Template_Person_Enhanced.wiki
Template_Org_Enhanced.wiki
Template_Place_Enhanced.wiki

# Custom JavaScript
PF_custom_upload.js              # Page Forms upload customization

# CSS
MediaWiki_Vector-2022.css        # Main skin CSS (73KB)
Infobox_Dark_Mode_Fixes.css

# Category definitions
Category_Person_Photos.wiki
Category_Document_Files.wiki
Category_Fair_Use_Files.wiki
# ... more categories
```

### Extensions Directory
```
config/extensions/               # Custom MediaWiki extensions
  LocalSettings.d/               # Modular configuration
```

---

## Wikibase Integration

### Sync Configuration (from docker-compose.yml)
```yaml
WIKIBASE_API_ENDPOINT: ${WIKIBASE_API_ENDPOINT}
WIKIBASE_SITE_ID: ${WIKIBASE_SITE_ID}
WIKIBASE_SYNC_USERNAME: ${WIKIBASE_SYNC_USERNAME}
WIKIBASE_SYNC_PASSWORD: ${WIKIBASE_SYNC_PASSWORD}
WIKIBASE_SYNC_ENABLED: ${WIKIBASE_SYNC_ENABLED}
```

**How it works**:
1. User creates/edits page on MediaWiki (www.wikidisc.org)
2. Sync process creates Wikibase item (data.wikidisc.org)
3. Properties and relationships stored in knowledge graph
4. SPARQL queries enabled via query.wikidisc.org

### Wikibase Directory Structure
```
/srv/wikibase/wikibase-release-pipeline/
  (Docker compose configuration for Wikibase stack)
```

---

## Monitoring Setup

### Prometheus Configuration
```
monitoring/prometheus/
  prometheus.yml                 # Scrape configs
  alerts.yml                     # Alert rules
```

### Grafana Dashboards
```
monitoring/grafana/
  provisioning/                  # Data source configs
  dashboards/                    # Pre-built dashboards
```

### AlertManager
```
monitoring/alertmanager/
  alertmanager.yml               # Alert routing rules
```

### StatsD Mapping
```
monitoring/statsd/
  statsd-mapping.yml             # Metric name mappings
```

---

## Notable Findings

### 1. No Deep Research Bot Found (Yet)
**Searched for**:
- Python scripts with "research", "openai", "anthropic", "claude"
- Agent-based automation
- LLM integration code

**Possible locations not yet explored**:
- `/home/dev/` directory (requires sudo)
- `.claude/` directory in `/opt/mediawiki-stack/` (requires sudo)
- Separate repository on SignalsIntelligence's local machine
- Inside MediaWiki container at `/var/www/html/`

**Your friend mentioned**: "I've gotten the page creation to a pretty good place" and showed examples like:
- Malmstrom UFO Incident page with citations
- Person pages with structured data
- See Also sections auto-generated

This suggests the AI research bot exists but may be:
1. Running on their local machine (not deployed to server yet)
2. In the `/home/dev/` directory
3. In a private repo they haven't pushed to the server

### 2. Wikibase Fully Operational
- 130+ people already in knowledge graph (per your conversation)
- SPARQL query interface working
- Auto-linking from wiki pages to Wikibase items functional

**Example your friend shared**:
```sparql
SELECT ?person ?personLabel ?org ?orgLabel
WHERE {
  ?person wdt:P1 wd:Q4 .      # instance of Person
  ?person wdt:P5 ?org .       # affiliated with org
  ?person schema:label ?personLabel .
  ?org schema:label ?orgLabel .
}
```

### 3. Production Quality Infrastructure
- Comprehensive monitoring (Prometheus + Grafana)
- Automated backups to B2 cloud storage
- SSL via nginx-proxy-manager
- Analytics via Matomo
- Anti-spam measures (StopForumSpam)

### 4. Swap Usage at 99%
**Concern**: Server may be memory constrained
- 8GB RAM, 53% used
- Swap at 99% indicates memory pressure
- May affect performance during heavy operations

---

## Integration Opportunities with Your Platform

### 1. Auto-Populate WikiDisc from Your Deep Research

**Your System → WikiDisc**:
```python
# After deep research completes
results = await deep_research.research("What are federal cybersecurity jobs?")

# Extract entities
entities = results['entities']  # 25 entities extracted

# For each entity, create WikiDisc page via API
for entity in entities:
    if entity['type'] == 'person':
        create_person_page(
            name=entity['name'],
            description=entity['properties']['description'],
            affiliations=entity['properties']['agencies'],
            sources=entity['sources']
        )
```

### 2. Feed Wikibase Knowledge Graph

**Direct Wikibase API integration**:
```python
from wikibase_api import WikibaseClient

client = WikibaseClient(
    api_url="https://data.wikidisc.org/w/api.php",
    username=os.getenv('WIKIBASE_SYNC_USERNAME'),
    password=os.getenv('WIKIBASE_SYNC_PASSWORD')
)

# Create item
item = client.create_item(
    label="NSA",
    description="National Security Agency",
    properties={
        "P1": "Q5",  # instance of: Government Agency
        "P12": ["Q15", "Q22"]  # operates: [Prism, XKEYSCORE]
    }
)
```

### 3. Use WikiDisc as Research Source

**WikiDisc → Your System**:
```python
# Add WikiDisc to your integrations
class WikiDiscIntegration(DatabaseIntegration):
    async def execute_search(self, params):
        # Query MediaWiki API
        results = await search_mediawiki(
            api_url="https://www.wikidisc.org/api.php",
            query=params['query']
        )

        # Or query Wikibase SPARQL
        sparql_results = await query_wikibase(
            endpoint="https://query.wikidisc.org/sparql",
            query=params['sparql_query']
        )

        return results
```

### 4. Shared Entity Resolution

**Problem**: Your system finds "NSA", WikiDisc has "National Security Agency"

**Solution**: Bidirectional entity linking
```python
# Your research finds entity
entity = extract_entity("NSA mentioned in contract")

# Check if exists in WikiDisc
wikidisc_item = await search_wikibase_entity("NSA")

if wikidisc_item:
    # Link to existing entity
    entity['wikibase_id'] = wikidisc_item['id']
    entity['canonical_name'] = wikidisc_item['label']
else:
    # Create new item in WikiDisc
    new_item = await create_wikibase_item(entity)
    entity['wikibase_id'] = new_item['id']
```

---

## NEW FINDINGS - Session 2 (2025-11-14)

### Git Repositories Discovered ✅

```bash
# Main Wikibase repo
/srv/wikibase/wikibase-release-pipeline/.git

# MediaWiki extension
/opt/mediawiki-stack/config/extensions/EmbedVideo/.git

# Wikibase extensions
/srv/wikibase/wikibase-release-pipeline/deploy/config/extensions/CentralAuth/.git
/srv/wikibase/wikibase-release-pipeline/deploy/config/extensions/AntiSpoof/.git
```

**ACTION NEEDED**: Explore wikibase Git repo for custom automation code

### Claude Code Configuration Discovered ✅

**File**: `/opt/mediawiki-stack/.claude/settings.local.json`

**Key Permissions Granted**:
- Docker operations (`docker-compose`, `docker exec`, `docker logs`)
- MediaWiki API access (`curl` to `www.wikidisc.org`)
- Web fetching from research sources:
  - `en.wikipedia.org`
  - `majesticdocuments.com` (MJ-12 UFO documents)
  - `vault.fbi.gov` (FBI declassified files)
  - `github.com`
  - `discord.gg`
  - Various UFO research sites

**Hypothesis**: **Claude Code IS the "research bot"**

**Evidence**:
1. Extensive web fetching permissions for research sources
2. No standalone AI bot code found in 44 Python files
3. Friend's workflow: "having claude give me the plan...then giving claude's final plan to codex to implement"
4. Claude can run Python scripts, access MediaWiki API, fetch from research sites

**Possible Workflow**:
```
User: "Create a page about Lockheed Martin"
  ↓
Claude Code:
  1. Fetches Wikipedia page (allowed: en.wikipedia.org)
  2. Fetches FBI Vault documents (allowed: vault.fbi.gov)
  3. Fetches MJ-12 documents (allowed: majesticdocuments.com)
  4. Synthesizes information
  5. Generates page content with citations
  6. Creates page via MediaWiki API (curl allowed)
  ↓
Result: Comprehensive wiki page
```

### Archive Directories Found

```bash
/opt/mediawiki-backups/
/opt/mediawiki-stack-archive-20241004/
/opt/mediawiki-stack-archive-20241004-2/
```

**ACTION NEEDED**: Check archives for older research bot code

### No LLM Imports Found ❌

```bash
grep -r "import openai|import anthropic" /opt /srv /home
# Result: No matches
```

**Conclusion**: If AI research exists, it either:
1. Uses Claude Code interactively (most likely)
2. Uses different LLM library (litellm, langchain)
3. Runs on friend's local machine

### Log Files Available

```bash
/opt/mediawiki-stack/logs/patrol.log
/opt/mediawiki-stack/logs/alerts.log
/opt/mediawiki-stack/logs/suspicious.log
/opt/mediawiki-stack/logs/runjobs.log
/opt/mediawiki-stack/logs/autorevert.log
/opt/mediawiki-stack/logs/stopforumspam.log
/opt/mediawiki-stack/logs/maintenance.log
```

---

## Next Steps

### Priority 1: Investigate Git Repos
```bash
cd /srv/wikibase/wikibase-release-pipeline
sudo git log --oneline | head -20
sudo git status
sudo ls -la
```

### Priority 2: Check Archives
```bash
sudo ls -la /opt/mediawiki-stack-archive-20241004/
sudo find /opt/mediawiki-stack-archive-20241004/ -name "*.py" | head -10
```

### Priority 3: Search for Other LLM Libraries
```bash
grep -r "litellm\|langchain\|llama" /opt /srv 2>/dev/null
```

### Priority 4: Examine Logs
```bash
sudo tail -50 /opt/mediawiki-stack/logs/maintenance.log
sudo tail -50 /opt/mediawiki-stack/logs/runjobs.log
```

### Immediate Actions
1. ~~**Confirm SSH password** with SignalsIntelligence~~ ✅ Working
2. **Explore Wikibase Git repo** for automation code
3. ~~**Check `.claude/`** directory for automation configs~~ ✅ Done - found extensive permissions
4. **Ask SignalsIntelligence** about:
   - Is Claude Code the "research bot"?
   - How does the See Also link crawler work?
   - Is it interactive or automated?

### Medium Term
1. **Design integration architecture** between your research platform and WikiDisc
2. **Test Wikibase API** for automated entity creation
3. **Prototype**: Deep research → WikiDisc page creation pipeline
4. **Consider**: Using WikiDisc as a research source (curated knowledge graph)

### Long Term
1. **Collaborative knowledge graph**: Your automated research + community curation
2. **Shared entity resolution**: Cross-platform entity linking
3. **Source attribution**: Track which research came from which platform
4. **Public wiki option**: Make your research findings publicly searchable via WikiDisc

---

## Technical Questions for SignalsIntelligence

1. **Where is the AI research bot code?**
   - Local machine or server?
   - Which LLM (Claude, GPT, etc.)?
   - How does it decide what pages to create?

2. **How does Wikibase sync work?**
   - Automatic or manual?
   - Which fields map to which Wikibase properties?
   - How do you handle conflicts?

3. **What's the workflow for creating a new page?**
   - Manual research → Bot generates page → Human reviews?
   - Fully automated?
   - What triggers page creation?

4. **Integration preferences**:
   - Would you want our research findings auto-imported?
   - Prefer manual review first?
   - Which entity types are priority (people, orgs, programs)?

---

## Files Referenced in This Document

- `docker-compose.yml` - Main stack orchestration
- `create_policy_pages.py` - Example page creation script
- `config/extra_localsettings.php` - MediaWiki configuration
- `monitoring/` - Prometheus/Grafana configs
- `/srv/wikibase/` - Knowledge graph installation

---

**Last Updated**: 2025-11-14 (Second Session)
**Server Access**: ✅ Active
**New Findings**: Git repos found, Claude Code config discovered, hypothesis: Claude Code IS the research bot
