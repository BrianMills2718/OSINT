# Boolean Monitoring System - Design

**Created**: 2025-10-19
**Status**: Phase 1 - Design Complete
**Purpose**: Automated keyword-based monitoring with email alerts

---

## Overview

The Boolean Monitoring system enables automated, scheduled searches across multiple data sources using predefined keywords. When new matches are found, alerts are sent via email.

**Use Case**: Monitor for mentions of "domestic extremism", "nihilistic violent extremism (NVE)", or other investigative topics across government sources, with daily email digests.

---

## Architecture

### Components

```
MonitorConfig (YAML file)
    ↓
BooleanMonitor.run()
    ↓
┌─────────────────────────────┐
│ 1. Load keywords from config│
│ 2. Execute searches          │
│ 3. Deduplicate results       │
│ 4. Compare vs previous run   │
│ 5. Send alert if new results │
└─────────────────────────────┘
    ↓
ResultStorage (JSON)
```

### Data Flow

1. **Config Loading**: Read YAML file with monitor configuration
2. **Search Execution**: Call existing integrations (DVIDS, SAM, USAJobs, ClearanceJobs)
3. **Deduplication**: Remove duplicate results based on URL hash
4. **New Result Detection**: Compare current results against previous run
5. **Alert Delivery**: Send email with new results (if any)
6. **Storage Update**: Save current results for next comparison

---

## Class Design

### MonitorConfig (Dataclass)

```python
@dataclass
class MonitorConfig:
    """Configuration for a single monitor"""
    name: str                    # Monitor name (e.g., "NVE Monitoring")
    keywords: List[str]          # Keywords to search (e.g., ["nihilistic violent extremism", "NVE"])
    sources: List[str]           # Data sources to search (e.g., ["dvids", "sam", "usajobs"])
    schedule: str                # Schedule (e.g., "daily_6am", "hourly", "weekly")
    alert_email: str             # Email address for alerts
    enabled: bool = True         # Whether monitor is active
```

### BooleanMonitor (Main Class)

```python
class BooleanMonitor:
    """
    Boolean keyword monitor with alerting.

    Workflow:
    1. Load config from YAML file
    2. Execute searches across configured sources
    3. Deduplicate results
    4. Compare against previous results
    5. Send alert if new results found
    6. Save results for next run
    """

    def __init__(self, config_path: str):
        self.config: MonitorConfig = self.load_config(config_path)
        self.storage_path: str = f"data/monitors/{self.config.name}_results.json"
        self.previous_results: Set[str] = self._load_previous_results()

    def load_config(self, path: str) -> MonitorConfig:
        """Load monitor configuration from YAML file"""

    async def execute_search(self, keywords: List[str]) -> List[Dict]:
        """
        Execute searches across configured sources.

        Calls existing integrations:
        - DVIDSIntegration
        - SAMIntegration
        - USAJobsIntegration
        - search_clearancejobs (Playwright)

        Returns standardized results: [{"title": ..., "url": ..., "source": ..., "date": ...}]
        """

    def deduplicate_results(self, results: List[Dict]) -> List[Dict]:
        """
        Remove duplicate results based on URL hash.

        Strategy: Hash each result URL, keep only unique hashes
        """

    def check_for_new_results(self, current_results: List[Dict]) -> List[Dict]:
        """
        Compare current results against previous run.

        Returns only NEW results (not seen in previous run)
        """

    async def send_alert(self, new_results: List[Dict]):
        """
        Send email alert with new results.

        Email format:
        - Subject: "[Monitor Name] - X new results"
        - Body: List of new results with links
        """

    def _save_results(self, results: List[Dict]):
        """Save current results to JSON file for next comparison"""

    def _load_previous_results(self) -> Set[str]:
        """Load previous result hashes from JSON file"""

    async def run(self):
        """
        Main execution method.

        Steps:
        1. Execute searches for all keywords
        2. Deduplicate results
        3. Check for new results
        4. Send alert if new results found
        5. Save results for next run
        """
```

---

## Storage Strategy

**Format**: JSON file per monitor
**Location**: `data/monitors/{monitor_name}_results.json`

**Structure**:
```json
{
  "last_run": "2025-10-19T14:30:00Z",
  "result_hashes": [
    "abc123def456...",  // SHA256 hash of result URL
    "789ghi012jkl..."
  ],
  "result_count": 15
}
```

**Why JSON**:
- Simple, no database setup required
- Easy to inspect/debug
- Fast for small datasets (< 10k results per monitor)
- Can migrate to SQLite later if needed

---

## Configuration File Format

**Location**: `data/monitors/configs/{monitor_name}.yaml`

**Example** (NVE Monitor):
```yaml
name: "NVE Monitoring"
keywords:
  - "nihilistic violent extremism"
  - "NVE"
  - "domestic extremism"
sources:
  - "dvids"
  - "sam"
  - "usajobs"
  - "federal_register"  # Phase 1 - to be added
schedule: "daily_6am"
alert_email: "investigator@example.com"
enabled: true
```

---

## Integration with Existing Code

### Existing Integrations (Phase 0)

BooleanMonitor will call these existing classes:
- `integrations.government.dvids_integration.DVIDSIntegration`
- `integrations.government.sam_integration.SAMIntegration`
- `integrations.government.usajobs_integration.USAJobsIntegration`
- `integrations.government.clearancejobs_playwright.search_clearancejobs`

### New Integrations (Phase 1)

To be created following existing patterns:
- `integrations.government.federal_register.FederalRegisterIntegration`
- `integrations.government.congress_gov.CongressGovIntegration`
- FBI Vault (blocked by Cloudflare - defer)

---

## Scheduling Strategy

**Phase 1 MVP**: Manual execution (test before automating)
```bash
python3 -m monitoring.run_monitor data/monitors/configs/nve_monitor.yaml
```

**Phase 1 Final**: APScheduler for automated runs
```python
from apscheduler.schedulers.blocking import BlockingScheduler

scheduler = BlockingScheduler()
scheduler.add_job(run_monitor, 'cron', hour=6)  # Daily at 6am
scheduler.start()
```

**Future** (Phase 2+): Cron job or systemd timer for production

---

## Email Alert Strategy

**Phase 1 MVP**: Simple SMTP (smtplib)
```python
import smtplib
from email.mime.text import MIMEText

msg = MIMEText(f"Found {len(new_results)} new results...")
msg['Subject'] = f"[{monitor.name}] - {len(new_results)} new results"
msg['From'] = "alerts@investigative-platform.com"
msg['To'] = monitor.alert_email

smtp = smtplib.SMTP('localhost')
smtp.send_message(msg)
smtp.quit()
```

**Future**: SendGrid API for better deliverability

---

## Testing Strategy

**Unit Tests**:
- Test deduplication logic with sample results
- Test new result detection with mock previous results
- Test config loading from YAML

**Integration Tests**:
- Test search execution with real DVIDS API
- Test end-to-end flow with single keyword, single source
- Verify results are saved correctly

**E2E Test**:
- Create test monitor config
- Run monitor manually
- Verify email received (if alerts enabled)
- Run again, verify no duplicate alerts

---

## Success Criteria (Phase 1)

1. **BooleanMonitor class works**:
   - Loads config from YAML
   - Executes searches across 2+ sources
   - Deduplicates results
   - Detects new results correctly

2. **First production monitor running**:
   - NVE monitor configured
   - Searches DVIDS + SAM.gov + Federal Register
   - Sends daily email digest
   - No duplicate results in alerts

3. **Evidence**:
   - Command output showing successful search
   - Email received with new results
   - Results JSON file saved correctly
   - No errors or timeouts

---

## Next Steps After Design

1. **Implement BooleanMonitor skeleton** (Action 2):
   - Create monitoring/boolean_monitor.py
   - Implement class structure
   - Add method stubs

2. **Test simple search** (Action 3):
   - Implement execute_search() method
   - Call DVIDS integration
   - Verify results returned

3. **Implement deduplication** (Action 4):
   - Hash-based dedup logic
   - Test with duplicate results

4. **Add Federal Register integration** (Action 5):
   - Follow SAM.gov pattern
   - Create FederalRegisterIntegration class

5. **Implement email alerts** (Action 6):
   - Simple SMTP email
   - Format new results as HTML/plaintext

6. **Add scheduling** (Action 7):
   - APScheduler integration
   - Configure daily run at 6am

7. **Deploy first production monitor** (Action 8):
   - Create NVE monitor config
   - Test end-to-end
   - Verify alerts work
