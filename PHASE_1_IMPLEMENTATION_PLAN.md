# Phase 1: Monitoring MVP - Implementation Plan

## Updated Risk Assessment

**GREAT NEWS**: You have 3rd party APIs for Twitter, Telegram, TikTok!

**New Risk Level: LOW-MEDIUM** (down from MEDIUM-HIGH)

### What This Changes:

✅ **Twitter**: 3rd party API solves cost problem
✅ **Telegram**: 3rd party API solves search/discovery problem
✅ **TikTok**: 3rd party API solves fragility problem
✅ **LLM Costs**: We'll build cost controls from day 1, monitor closely

**Key Insight**: The hard technical problems (API access, scraping, maintenance) are SOLVED. Now it's just integration work.

---

## Revised Phase Sequencing

### **Phase 1: Monitoring MVP** (Weeks 1-3) ← START HERE
- Automated Boolean monitoring
- Email/Slack alerts
- Government sources (FBI Vault, Federal Register, Congress.gov)
- Reddit (free, stable)

### **Phase 2: Streamlit UI** (Weeks 4-6)
- Natural language chat interface
- Result browser with export
- Basic cost tracking dashboard

### **DECISION POINT: Phase 3 Source Selection** (Week 7)

**After Phase 2 is working**, we'll decide which sources to add based on:
1. Your team's actual usage patterns from Phases 1-2
2. Which investigations need which sources
3. 3rd party API costs/capabilities

**Options for Phase 3** (we'll pick 3-5):
- Twitter (via your 3rd party API)
- Telegram (via your 3rd party API)
- TikTok (via your 3rd party API)
- 4chan (direct integration, free)
- Additional government sources
- News APIs (NewsAPI, Google News)
- Document repos (MuckRock, DocumentCloud)

---

## Phase 1: Detailed Implementation Plan

**Goal**: Automated monitoring with alerts working in 3 weeks

**Deliverable**: Daily email digest like this:
```
Subject: [SigInt] NVE Monitoring - 3 High-Priority Matches

🔴 GOVERNMENT (1 new)
FBI Vault: Domestic Terrorism Threat Assessment 2025
→ https://vault.fbi.gov/reports/dt-2025.pdf
Keywords matched: "nihilistic violent extremism", "threat assessment"
Published: Today, 6:32 AM

🟡 NEWS (2 new)
NYT: FBI Director Discusses NVE Threat
→ https://nytimes.com/...
Published: Yesterday

ProPublica: Fusion Centers Track Extremists
→ https://propublica.org/...
Published: 2 days ago

📊 REDDIT (4 discussions)
r/intelligence: FBI releases new extremism report
→ https://reddit.com/r/intelligence/...
47 upvotes, 12 comments
```

---

## Week-by-Week Breakdown

### **Week 1: Foundation & Refactoring**

#### Day 1-2: Code Organization
**Task**: Clean up existing codebase into proper structure

**Current structure** (messy):
```
sam_gov/
├── core/
│   ├── agentic_executor.py
│   ├── parallel_executor.py
│   └── ...
├── experiments/
│   ├── scrapers/
│   └── tag_management/
├── extract_keywords_for_boolean.py  # root level, messy
├── organize_keywords.py
└── ...
```

**New structure** (clean):
```
sam_gov/
├── core/
│   ├── __init__.py
│   ├── agentic_executor.py
│   ├── parallel_executor.py
│   ├── database_integration_base.py
│   └── api_request_tracker.py
│
├── integrations/                    # NEW: All source integrations
│   ├── __init__.py
│   ├── government/
│   │   ├── __init__.py
│   │   ├── fbi_vault.py
│   │   ├── federal_register.py
│   │   └── congress_gov.py
│   ├── social/
│   │   ├── __init__.py
│   │   └── reddit_integration.py
│   └── registry.py                  # Central source registry
│
├── monitoring/                      # NEW: Boolean monitoring system
│   ├── __init__.py
│   ├── monitor_engine.py
│   ├── scheduler.py
│   ├── alert_manager.py
│   └── deduplicator.py
│
├── research/                        # NEW: Natural language research
│   ├── __init__.py
│   ├── nl_router.py                # Natural language → intent
│   └── synthesizer.py              # Result synthesis
│
├── utils/
│   ├── __init__.py
│   ├── keyword_db.py               # Load keyword database
│   └── cost_tracker.py             # NEW: LLM cost tracking
│
├── data/
│   ├── keyword_database.json
│   ├── tag_taxonomy_complete.json
│   └── monitors/                   # Monitor configs
│       └── nve_monitor.yaml
│
├── api/                            # NEW: FastAPI backend
│   ├── __init__.py
│   └── main.py
│
├── ui/                             # NEW: Streamlit frontend
│   └── app.py
│
└── config.yaml
```

**Actions**:
1. Create new directory structure
2. Move files to proper locations
3. Fix imports
4. Run tests to ensure nothing broke

**Effort**: 1 day (tedious but necessary)

---

#### Day 3-5: Add Government Source Integrations

**Task**: Create 3 new source adapters using existing pattern

**1. FBI Vault Adapter**

```python
# integrations/government/fbi_vault.py

from core.database_integration_base import DatabaseIntegration, DatabaseMetadata, QueryResult
import httpx
from typing import Dict, List

class FBIVaultIntegration(DatabaseIntegration):
    """FBI FOIA Vault - Document releases"""

    def __init__(self):
        super().__init__(DatabaseMetadata(
            id="fbi_vault",
            name="FBI Vault",
            description="FBI FOIA document releases and investigations",
            category="government_foia",
            api_docs_url="https://vault.fbi.gov/api-docs"
        ))
        self.base_url = "https://vault.fbi.gov/api/v1"

    async def execute_search(self, params: Dict, api_key: str, limit: int) -> QueryResult:
        """
        Execute search against FBI Vault

        API Endpoint: GET /vault/v1/search
        Params: {
            "q": "search query",
            "page": 1,
            "per_page": 20
        }
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/search",
                    params={
                        "q": params.get("query", ""),
                        "page": params.get("page", 1),
                        "per_page": min(limit, 100)
                    },
                    timeout=30.0
                )

                response.raise_for_status()
                data = response.json()

                # Transform to standard format
                results = []
                for item in data.get("results", []):
                    results.append({
                        "title": item.get("title"),
                        "url": item.get("vault_url"),
                        "snippet": item.get("description", "")[:500],
                        "date": item.get("release_date"),
                        "source": "FBI Vault",
                        "metadata": {
                            "document_type": item.get("type"),
                            "file_url": item.get("pdf_url")
                        }
                    })

                return QueryResult(
                    source="FBI Vault",
                    success=True,
                    results=results,
                    total=len(results),
                    query_params=params,
                    error_message=None
                )

        except Exception as e:
            return QueryResult(
                source="FBI Vault",
                success=False,
                results=[],
                total=0,
                query_params=params,
                error_message=str(e)
            )
```

**2. Federal Register Adapter**

```python
# integrations/government/federal_register.py

class FederalRegisterIntegration(DatabaseIntegration):
    """Federal Register - Rules, notices, executive orders"""

    def __init__(self):
        super().__init__(DatabaseMetadata(
            id="federal_register",
            name="Federal Register",
            description="Federal rules, proposed rules, notices, executive orders",
            category="government_policy",
            api_docs_url="https://www.federalregister.gov/developers/documentation/api/v1"
        ))
        self.base_url = "https://www.federalregister.gov/api/v1"

    async def execute_search(self, params: Dict, api_key: str, limit: int) -> QueryResult:
        """
        API Endpoint: GET /documents.json
        Params: {
            "conditions[term]": "search query",
            "per_page": 20,
            "page": 1,
            "order": "newest"
        }
        """
        # Similar implementation to FBI Vault
        # Federal Register has excellent API docs
        pass
```

**3. Congress.gov Adapter**

```python
# integrations/government/congress_gov.py

class CongressGovIntegration(DatabaseIntegration):
    """Congress.gov - Bills, hearings, reports"""

    def __init__(self):
        super().__init__(DatabaseMetadata(
            id="congress_gov",
            name="Congress.gov",
            description="Bills, amendments, hearings, Congressional reports",
            category="government_legislative",
            api_docs_url="https://api.congress.gov/"
        ))
        self.base_url = "https://api.congress.gov/v3"
        # Requires API key (free, request at https://api.congress.gov/sign-up/)

    async def execute_search(self, params: Dict, api_key: str, limit: int) -> QueryResult:
        """
        API Endpoint: GET /bill
        Requires: X-API-Key header
        """
        # Implementation
        pass
```

**4. Reddit Adapter**

```python
# integrations/social/reddit_integration.py

import praw
from core.database_integration_base import DatabaseIntegration, DatabaseMetadata, QueryResult

class RedditIntegration(DatabaseIntegration):
    """Reddit - Subreddit monitoring and search"""

    def __init__(self):
        super().__init__(DatabaseMetadata(
            id="reddit",
            name="Reddit",
            description="Reddit posts and comments across subreddits",
            category="social_media",
            api_docs_url="https://praw.readthedocs.io/"
        ))

    async def execute_search(self, params: Dict, api_key: str, limit: int) -> QueryResult:
        """
        Search Reddit using PRAW

        Params: {
            "query": "search terms",
            "subreddit": "all" or specific subreddit,
            "time_filter": "day" | "week" | "month" | "year" | "all",
            "sort": "relevance" | "hot" | "top" | "new"
        }
        """
        try:
            # Initialize PRAW (requires Reddit API credentials)
            reddit = praw.Reddit(
                client_id=os.getenv("REDDIT_CLIENT_ID"),
                client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
                user_agent="SigInt Research Platform v1.0"
            )

            subreddit = reddit.subreddit(params.get("subreddit", "all"))

            results = []
            for submission in subreddit.search(
                query=params.get("query", ""),
                limit=limit,
                time_filter=params.get("time_filter", "week"),
                sort=params.get("sort", "relevance")
            ):
                results.append({
                    "title": submission.title,
                    "url": f"https://reddit.com{submission.permalink}",
                    "snippet": submission.selftext[:500] if submission.selftext else "",
                    "date": datetime.fromtimestamp(submission.created_utc).isoformat(),
                    "source": f"Reddit - r/{submission.subreddit}",
                    "metadata": {
                        "score": submission.score,
                        "num_comments": submission.num_comments,
                        "author": str(submission.author),
                        "subreddit": str(submission.subreddit)
                    }
                })

            return QueryResult(
                source="Reddit",
                success=True,
                results=results,
                total=len(results),
                query_params=params,
                error_message=None
            )

        except Exception as e:
            return QueryResult(
                source="Reddit",
                success=False,
                results=[],
                total=0,
                query_params=params,
                error_message=str(e)
            )
```

**5. Register All Sources**

```python
# integrations/registry.py

from core.database_registry import DatabaseRegistry
from integrations.government.fbi_vault import FBIVaultIntegration
from integrations.government.federal_register import FederalRegisterIntegration
from integrations.government.congress_gov import CongressGovIntegration
from integrations.social.reddit_integration import RedditIntegration

# Import existing integrations
from experiments.scrapers.sam_search import SAMGovIntegration
from experiments.scrapers.dvids_search import DVIDSIntegration

def get_all_sources():
    """Get all registered data sources"""
    registry = DatabaseRegistry()

    # Government sources
    registry.register(FBIVaultIntegration())
    registry.register(FederalRegisterIntegration())
    registry.register(CongressGovIntegration())
    registry.register(SAMGovIntegration())
    registry.register(DVIDSIntegration())

    # Social media
    registry.register(RedditIntegration())

    return registry
```

**Effort**: 2-3 days
**Result**: 4 new sources working, all testable

---

### **Week 2: Boolean Monitoring System**

#### Day 6-8: Monitor Engine

**Task**: Build core monitoring logic

```python
# monitoring/monitor_engine.py

import asyncio
from typing import List, Dict
from dataclasses import dataclass
from datetime import datetime
import yaml

from core.agentic_executor import AgenticExecutor
from integrations.registry import get_all_sources
from utils.keyword_db import KeywordDatabase

@dataclass
class MonitorConfig:
    """Configuration for a monitoring job"""
    id: str
    name: str
    keywords: List[str]  # Can be simple list or Boolean expression
    sources: List[str]   # List of source IDs
    schedule: str        # Cron expression or "daily", "hourly"
    alert_rules: Dict    # When to alert
    delivery: Dict       # Email, Slack, etc.
    enabled: bool = True
    created_at: datetime = None
    last_run: datetime = None

class MonitorEngine:
    """
    Core monitoring engine

    Loads monitor configs, executes searches, applies deduplication,
    scores results, triggers alerts.
    """

    def __init__(self, keyword_db_path: str, config_dir: str = "data/monitors"):
        self.keyword_db = KeywordDatabase(keyword_db_path)
        self.config_dir = config_dir
        self.monitors: Dict[str, MonitorConfig] = {}
        self.executor = AgenticExecutor()
        self.sources_registry = get_all_sources()

    def load_monitors(self):
        """Load all monitor configurations from YAML files"""
        import os
        from pathlib import Path

        config_path = Path(self.config_dir)
        config_path.mkdir(parents=True, exist_ok=True)

        for yaml_file in config_path.glob("*.yaml"):
            with open(yaml_file, 'r') as f:
                config_data = yaml.safe_load(f)
                monitor = MonitorConfig(**config_data)
                self.monitors[monitor.id] = monitor

        print(f"Loaded {len(self.monitors)} monitors")

    async def execute_monitor(self, monitor_id: str) -> Dict:
        """
        Execute a single monitor

        1. Build search query from keywords
        2. Execute across specified sources
        3. Deduplicate results
        4. Score by relevance
        5. Apply alert rules
        6. Return results for alerting
        """
        monitor = self.monitors[monitor_id]

        if not monitor.enabled:
            print(f"Monitor {monitor.name} is disabled, skipping")
            return None

        print(f"🔍 Executing monitor: {monitor.name}")

        # Step 1: Build query
        # If keywords are in keyword database, expand with synonyms
        query = self._build_query(monitor.keywords)

        # Step 2: Get sources
        sources = [
            self.sources_registry.get(source_id)
            for source_id in monitor.sources
        ]
        sources = [s for s in sources if s is not None]  # Filter out any that don't exist

        if not sources:
            print(f"  ⚠️  No valid sources for monitor {monitor.name}")
            return None

        # Step 3: Execute search using agentic executor
        results = await self.executor.execute_all(
            research_question=query,
            databases=sources,
            api_keys={},  # Load from config
            limit=20      # Per source
        )

        # Step 4: Deduplicate (implement in deduplicator.py)
        from monitoring.deduplicator import Deduplicator
        deduplicator = Deduplicator()

        all_results = []
        for source_id, result in results.items():
            if result.success:
                all_results.extend(result.results)

        deduplicated = deduplicator.deduplicate(all_results)

        # Step 5: Score and filter
        scored_results = self._score_results(deduplicated, monitor)

        # Step 6: Apply alert rules
        alerts = self._apply_alert_rules(scored_results, monitor)

        # Step 7: Update monitor metadata
        monitor.last_run = datetime.now()
        self._save_monitor_state(monitor)

        print(f"  ✓ Found {len(deduplicated)} results ({len(alerts)} trigger alerts)")

        return {
            "monitor_id": monitor_id,
            "monitor_name": monitor.name,
            "total_results": len(deduplicated),
            "alert_results": alerts,
            "executed_at": datetime.now().isoformat()
        }

    def _build_query(self, keywords: List[str]) -> str:
        """
        Build natural language query from keywords

        Can also expand using keyword database synonyms
        """
        # Simple version: just join keywords
        # Advanced: expand with synonyms from keyword_db
        return " OR ".join(keywords)

    def _score_results(self, results: List[Dict], monitor: MonitorConfig) -> List[Dict]:
        """
        Score results by relevance

        Factors:
        - Keyword match count
        - Source credibility
        - Recency
        """
        scored = []

        for result in results:
            score = 0.0

            # Keyword matching (simple version)
            content = (result.get("title", "") + " " + result.get("snippet", "")).lower()
            keyword_matches = sum(1 for kw in monitor.keywords if kw.lower() in content)
            score += keyword_matches * 2.0

            # Source credibility (government > news > social)
            if "fbi" in result.get("source", "").lower() or "gov" in result.get("source", "").lower():
                score += 3.0
            elif "reddit" in result.get("source", "").lower():
                score += 1.0
            else:
                score += 2.0

            # Recency (within 24 hours = bonus)
            try:
                pub_date = datetime.fromisoformat(result.get("date", ""))
                hours_old = (datetime.now() - pub_date).total_seconds() / 3600
                if hours_old < 24:
                    score += 2.0
                elif hours_old < 72:
                    score += 1.0
            except:
                pass

            result["relevance_score"] = score
            scored.append(result)

        # Sort by score
        scored.sort(key=lambda x: x["relevance_score"], reverse=True)

        return scored

    def _apply_alert_rules(self, results: List[Dict], monitor: MonitorConfig) -> List[Dict]:
        """
        Apply alert rules to determine which results trigger alerts

        Examples:
        - Immediate alert for government sources
        - Alert if >3 results in 24 hours
        - Alert for specific keywords
        """
        rules = monitor.alert_rules
        alerts = []

        for result in results:
            should_alert = False
            alert_reason = []

            # Rule: Immediate for government sources
            if rules.get("immediate_on_government", False):
                if any(term in result.get("source", "").lower()
                       for term in ["fbi", "dhs", ".gov", ".mil"]):
                    should_alert = True
                    alert_reason.append("Government source")

            # Rule: High relevance score
            if result.get("relevance_score", 0) >= rules.get("min_score", 5.0):
                should_alert = True
                alert_reason.append(f"High relevance ({result['relevance_score']:.1f})")

            # Rule: Specific keyword
            if "critical_keywords" in rules:
                content = (result.get("title", "") + " " + result.get("snippet", "")).lower()
                for critical_kw in rules["critical_keywords"]:
                    if critical_kw.lower() in content:
                        should_alert = True
                        alert_reason.append(f"Critical keyword: {critical_kw}")
                        break

            if should_alert:
                result["alert_reason"] = "; ".join(alert_reason)
                alerts.append(result)

        return alerts

    def _save_monitor_state(self, monitor: MonitorConfig):
        """Save monitor state (last_run, etc.)"""
        # Update YAML file with new state
        pass
```

**Effort**: 2 days

---

#### Day 9-10: Alert Manager

**Task**: Send email and Slack alerts

```python
# monitoring/alert_manager.py

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict
import requests
import os

class AlertManager:
    """Send alerts via email, Slack, webhooks"""

    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.slack_webhook = os.getenv("SLACK_WEBHOOK_URL")

    def send_email_alert(self, monitor_name: str, results: List[Dict], recipient: str):
        """
        Send email alert with results

        Format:
        Subject: [SigInt] {monitor_name} - {count} New Matches

        Body: HTML formatted results with links
        """
        if not results:
            return

        subject = f"[SigInt] {monitor_name} - {len(results)} New Matches"

        # Build HTML email
        html = self._build_email_html(monitor_name, results)

        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = self.smtp_user
        msg['To'] = recipient

        msg.attach(MIMEText(html, 'html'))

        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            print(f"  📧 Email sent to {recipient}")

        except Exception as e:
            print(f"  ⚠️  Email failed: {e}")

    def send_slack_alert(self, monitor_name: str, results: List[Dict]):
        """Send Slack notification"""
        if not results or not self.slack_webhook:
            return

        # Build Slack message (Markdown format)
        message = self._build_slack_message(monitor_name, results)

        try:
            response = requests.post(
                self.slack_webhook,
                json={"text": message},
                timeout=10
            )
            response.raise_for_status()

            print(f"  💬 Slack alert sent")

        except Exception as e:
            print(f"  ⚠️  Slack alert failed: {e}")

    def _build_email_html(self, monitor_name: str, results: List[Dict]) -> str:
        """Build HTML email body"""
        # Group by source
        by_source = {}
        for result in results:
            source = result.get("source", "Unknown")
            if source not in by_source:
                by_source[source] = []
            by_source[source].append(result)

        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 800px;">
            <h2 style="color: #333;">{monitor_name} - Alert</h2>
            <p style="color: #666;">Found {len(results)} new matches</p>
        """

        for source, source_results in by_source.items():
            # Priority indicator
            priority = "🔴" if "gov" in source.lower() else "🟡"

            html += f"""
            <h3 style="color: #555;">{priority} {source} ({len(source_results)} results)</h3>
            <ul>
            """

            for result in source_results[:5]:  # Show top 5 per source
                html += f"""
                <li style="margin-bottom: 15px;">
                    <strong><a href="{result.get('url', '#')}">{result.get('title', 'Untitled')}</a></strong><br>
                    <small style="color: #888;">{result.get('date', 'Unknown date')}</small><br>
                    <p style="color: #555; margin: 5px 0;">{result.get('snippet', '')[:200]}...</p>
                    {f'<small style="color: #e67e22;">Alert reason: {result.get("alert_reason", "")}</small>' if result.get('alert_reason') else ''}
                </li>
                """

            if len(source_results) > 5:
                html += f"<li><em>... and {len(source_results) - 5} more from {source}</em></li>"

            html += "</ul>"

        html += """
        </body>
        </html>
        """

        return html

    def _build_slack_message(self, monitor_name: str, results: List[Dict]) -> str:
        """Build Slack message (Markdown)"""
        message = f"🚨 *{monitor_name}* - {len(results)} New Matches\n\n"

        # Show top 3 results
        for i, result in enumerate(results[:3], 1):
            priority = "🔴" if "gov" in result.get("source", "").lower() else "🟡"
            message += f"{priority} *<{result.get('url', '#')}|{result.get('title', 'Untitled')}>*\n"
            message += f"   {result.get('source', 'Unknown source')} • {result.get('date', 'Unknown date')}\n"
            if result.get("alert_reason"):
                message += f"   _{result.get('alert_reason')}_\n"
            message += "\n"

        if len(results) > 3:
            message += f"_... and {len(results) - 3} more results_"

        return message
```

**Effort**: 1 day

---

### **Week 3: Scheduler, Deduplication, Testing**

#### Day 11-12: Scheduler

**Task**: Run monitors on schedule (cron-style)

```python
# monitoring/scheduler.py

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from monitoring.monitor_engine import MonitorEngine
from monitoring.alert_manager import AlertManager
import asyncio

class MonitorScheduler:
    """
    Schedule and execute monitors

    Uses APScheduler for cron-style scheduling
    """

    def __init__(self, monitor_engine: MonitorEngine, alert_manager: AlertManager):
        self.engine = monitor_engine
        self.alert_manager = alert_manager
        self.scheduler = AsyncIOScheduler()

    def start(self):
        """
        Start scheduler

        Loads all monitors and schedules them based on their cron expression
        """
        self.engine.load_monitors()

        for monitor_id, monitor in self.engine.monitors.items():
            self._schedule_monitor(monitor_id, monitor)

        self.scheduler.start()
        print(f"✓ Scheduler started with {len(self.engine.monitors)} monitors")

    def _schedule_monitor(self, monitor_id: str, monitor):
        """Schedule a single monitor"""
        schedule = monitor.schedule

        # Parse schedule string
        if schedule == "daily":
            # Run daily at 6 AM
            self.scheduler.add_job(
                self._execute_and_alert,
                'cron',
                hour=6,
                minute=0,
                args=[monitor_id],
                id=f"monitor_{monitor_id}"
            )
            print(f"  Scheduled {monitor.name}: daily at 6:00 AM")

        elif schedule == "hourly":
            self.scheduler.add_job(
                self._execute_and_alert,
                'interval',
                hours=1,
                args=[monitor_id],
                id=f"monitor_{monitor_id}"
            )
            print(f"  Scheduled {monitor.name}: every hour")

        elif schedule.startswith("cron:"):
            # Custom cron expression: "cron:0 6 * * *"
            cron_expr = schedule.replace("cron:", "").strip()
            # Parse cron (TODO: implement full cron parsing)
            pass

        else:
            # Every 15 minutes (default)
            self.scheduler.add_job(
                self._execute_and_alert,
                'interval',
                minutes=15,
                args=[monitor_id],
                id=f"monitor_{monitor_id}"
            )
            print(f"  Scheduled {monitor.name}: every 15 minutes")

    async def _execute_and_alert(self, monitor_id: str):
        """Execute monitor and send alerts"""
        try:
            result = await self.engine.execute_monitor(monitor_id)

            if not result:
                return

            alerts = result.get("alert_results", [])

            if not alerts:
                print(f"  No alerts for {result['monitor_name']}")
                return

            monitor = self.engine.monitors[monitor_id]
            delivery = monitor.delivery

            # Send email alerts
            if delivery.get("email"):
                for recipient in delivery["email"]:
                    self.alert_manager.send_email_alert(
                        monitor_name=result["monitor_name"],
                        results=alerts,
                        recipient=recipient
                    )

            # Send Slack alerts
            if delivery.get("slack", False):
                self.alert_manager.send_slack_alert(
                    monitor_name=result["monitor_name"],
                    results=alerts
                )

        except Exception as e:
            print(f"  ⚠️  Monitor {monitor_id} failed: {e}")
```

**Effort**: 1 day

---

#### Day 13-14: Deduplicator

**Task**: Implement MinHash deduplication

```python
# monitoring/deduplicator.py

from datasketch import MinHash, MinHashLSH
import hashlib
from typing import List, Dict

class Deduplicator:
    """
    Deduplicate results using MinHash + LSH

    Catches near-duplicates (90%+ similar content)
    """

    def __init__(self, threshold: float = 0.85):
        self.threshold = threshold
        self.lsh = MinHashLSH(threshold=threshold, num_perm=128)
        self.seen_hashes = set()
        self.seen_urls = set()

    def deduplicate(self, results: List[Dict]) -> List[Dict]:
        """
        Remove duplicates from results

        Approach:
        1. Exact URL match → duplicate
        2. Exact content hash → duplicate
        3. MinHash similarity > threshold → duplicate
        """
        unique_results = []

        for result in results:
            if self._is_duplicate(result):
                continue

            unique_results.append(result)

        print(f"  Deduplication: {len(results)} → {len(unique_results)}")
        return unique_results

    def _is_duplicate(self, result: Dict) -> bool:
        """Check if result is duplicate"""

        # Method 1: Exact URL match
        url = result.get("url", "")
        if url in self.seen_urls:
            return True

        # Method 2: Exact content hash
        content = result.get("title", "") + " " + result.get("snippet", "")
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        if content_hash in self.seen_hashes:
            return True

        # Method 3: MinHash similarity
        minhash = MinHash(num_perm=128)
        for word in content.split():
            minhash.update(word.encode())

        similar = self.lsh.query(minhash)
        if similar:
            return True  # Found similar document

        # Not duplicate - add to indexes
        self.seen_urls.add(url)
        self.seen_hashes.add(content_hash)
        self.lsh.insert(result.get("url", content_hash), minhash)

        return False
```

**Effort**: 1 day

---

#### Day 15: Create NVE Monitor Config

**Task**: Create your first monitor (NVE example)

```yaml
# data/monitors/nve_monitor.yaml

id: nve_monitoring
name: "Domestic Extremism - NVE"

keywords:
  - "nihilistic violent extremism"
  - "NVE"
  - "domestic terrorism"
  - "violent extremists"

sources:
  - fbi_vault
  - federal_register
  - reddit

schedule: "daily"  # Daily at 6 AM

alert_rules:
  immediate_on_government: true
  min_score: 5.0
  critical_keywords:
    - "threat assessment"
    - "FBI director"
    - "domestic terror"

delivery:
  email:
    - brian@example.com
  slack: true

enabled: true
```

**Effort**: 30 minutes

---

#### Day 16-21: Testing & Polish

**Tasks**:
1. **Test each source adapter** independently
2. **Test monitor engine** end-to-end
3. **Test email alerts** (send test emails)
4. **Test Slack alerts** (send test Slacks)
5. **Run NVE monitor** manually, verify results
6. **Fix bugs** that emerge
7. **Add cost tracking** (track LLM API calls, costs)

**Cost Tracker Implementation**:

```python
# utils/cost_tracker.py

import json
from datetime import datetime
from pathlib import Path

class CostTracker:
    """
    Track LLM API costs

    Log every LLM call with:
    - Model used
    - Tokens (input/output)
    - Cost
    - Timestamp
    """

    def __init__(self, log_file: str = "data/llm_costs.jsonl"):
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def log_call(self, model: str, input_tokens: int, output_tokens: int, cost: float):
        """Log an LLM API call"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": cost
        }

        with open(self.log_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')

    def get_daily_cost(self) -> float:
        """Get today's total cost"""
        # Parse log file, sum costs for today
        pass

    def get_monthly_cost(self) -> float:
        """Get this month's total cost"""
        # Parse log file, sum costs for this month
        pass

    def alert_if_over_budget(self, daily_limit: float = 10.0, monthly_limit: float = 200.0):
        """Send alert if over budget"""
        daily = self.get_daily_cost()
        monthly = self.get_monthly_cost()

        if daily > daily_limit:
            print(f"⚠️  Daily LLM cost (${daily:.2f}) exceeds limit (${daily_limit})")

        if monthly > monthly_limit:
            print(f"⚠️  Monthly LLM cost (${monthly:.2f}) exceeds limit (${monthly_limit})")
```

---

## Week 4+: Phase 2 (Streamlit UI)

**We'll design this after Phase 1 is working!**

---

## Dependencies to Install

```bash
# Phase 1 requirements
pip install httpx praw datasketch apscheduler pyyaml
```

---

## Environment Variables Needed

```bash
# .env file

# Reddit API
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_secret

# Congress.gov API
CONGRESS_API_KEY=your_api_key

# Email alerts
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password

# Slack alerts
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# LLM API
OPENAI_API_KEY=your_openai_key
# or ANTHROPIC_API_KEY for Claude
```

---

## Ready to Start?

**I can start building this TODAY.**

**Next Steps**:
1. I'll create the new directory structure
2. Move existing files to proper locations
3. Build FBI Vault adapter (first new source)
4. Test it works
5. Continue through Week 1-3 plan

**Should I start with the refactoring (Week 1, Day 1-2)?**
