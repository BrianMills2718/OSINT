# Production Deployment - OSINT Boolean Monitor

**Date**: 2025-10-19
**Status**: DEPLOYED ✅
**Service**: osint-monitor.service (systemd)

---

## Deployment Summary

**What's Running**:
- 6 production monitors scheduled for daily execution at 6:00 AM
- Automated email alerts to brianmills2718@gmail.com
- Systemd service with auto-restart on failure

**Monitor List**:
1. Domestic Extremism Classifications (8 keywords, 4 sources)
2. Immigration Enforcement Operations (9 keywords, 4 sources)
3. Inspector General & Oversight Reports (9 keywords, 4 sources)
4. NVE Monitoring (5 keywords, 4 sources)
5. Special Operations & Covert Programs (9 keywords, 4 sources)
6. Surveillance & FISA Programs (9 keywords, 4 sources)

**Total Searches Per Day**: ~192 searches (49 keywords × 4 sources)

**Expected Runtime**: ~20-30 minutes total for all 6 monitors

---

## Service Details

**Service File**: `/etc/systemd/system/osint-monitor.service`

**Working Directory**: `/home/brian/sam_gov`

**Python**: `/home/brian/sam_gov/.venv/bin/python3`

**Command**: `monitoring/scheduler.py --config-dir data/monitors/configs`

**User**: brian

**Auto-restart**: Yes (RestartSec=10)

**Logs**: `journalctl -u osint-monitor`

---

## Service Management Commands

### Check Status
```bash
sudo systemctl status osint-monitor
```

### View Live Logs
```bash
sudo journalctl -u osint-monitor -f
```

### View Logs from Today
```bash
sudo journalctl -u osint-monitor --since today
```

### View Logs from Last Run (6:00 AM)
```bash
sudo journalctl -u osint-monitor --since "06:00" --until "07:00"
```

### Restart Service
```bash
sudo systemctl restart osint-monitor
```

### Stop Service
```bash
sudo systemctl stop osint-monitor
```

### Start Service
```bash
sudo systemctl start osint-monitor
```

### Disable Service (prevent auto-start on boot)
```bash
sudo systemctl disable osint-monitor
```

---

## Monitor Configuration Files

**Location**: `data/monitors/configs/`

**Files** (gitignored, not in repository):
- `domestic_extremism_monitor.yaml`
- `immigration_enforcement_monitor.yaml`
- `oversight_whistleblower_monitor.yaml`
- `special_operations_monitor.yaml`
- `surveillance_fisa_monitor.yaml`
- `nve_monitor.yaml` (from earlier testing)

**Note**: Monitor configs are gitignored because they contain email addresses and potentially sensitive keywords.

---

## Expected Daily Workflow

### 6:00 AM PST - Monitors Execute

1. **Scheduler wakes up** at 6:00 AM
2. **All 6 monitors run in sequence**:
   - Each monitor searches 4 sources in parallel
   - LLM filters results for relevance (threshold >= 6/10)
   - New results trigger email alerts
3. **Email alerts sent** to brianmills2718@gmail.com
4. **Results saved** to `data/monitors/*_results.json`
5. **Scheduler returns to sleep** until next day

### What You'll Receive

**Email Format**:
- Subject: `[Monitor Name] - X new results`
- Body: HTML + plain text with:
  - Title, Source, Date
  - Matched keyword
  - Relevance score (0-10)
  - Reasoning from LLM
  - Link to full article

**Example**:
```
Subject: [Surveillance & FISA Programs] - 3 new results

1. FISA Court Releases New Opinion on Section 702
   Source: Federal Register | Date: 2025-10-19
   🔍 Matched keyword: "Section 702"
   Relevance: 10/10 — This document directly discusses Section 702
   surveillance authorities and FISA court oversight.
   
   [Read more...]
```

---

## Monitoring After Deployment

### Check if Monitors Ran Successfully

**Tomorrow at 7:00 AM**, check logs:

```bash
# View morning execution logs
sudo journalctl -u osint-monitor --since "06:00" --until "07:00"

# Look for successful email alerts
sudo journalctl -u osint-monitor --since "06:00" | grep "Email sent successfully"

# Look for errors
sudo journalctl -u osint-monitor --since "06:00" | grep -E "(ERROR|FAIL|Exception)"
```

### Check Email Delivery

1. Check inbox at brianmills2718@gmail.com
2. Look for subjects like `[Monitor Name] - X new results`
3. If no emails: Either no new results or all filtered out (check logs)

### Verify Results Saved

```bash
# Check result files were updated today
ls -lt data/monitors/*_results.json | head -6

# View result count
for f in data/monitors/*_results.json; do 
  echo "$f: $(jq '. | length' $f) results"
done
```

---

## Tuning After First Week

### Review Relevance Filtering

After 1 week of results, check if threshold is appropriate:

```bash
# Count how many results passed filter
sudo journalctl -u osint-monitor --since "7 days ago" | grep "RELEVANT" | wc -l

# Count how many were filtered out
sudo journalctl -u osint-monitor --since "7 days ago" | grep "FILTERED" | wc -l
```

**If too many false positives**: Increase threshold in `boolean_monitor.py`:
```python
# Line ~350: Change from 6.0 to 7.0 or 8.0
filtered_results = await self.filter_by_relevance(new_results, threshold=7.0)
```

**If too few results**: Decrease threshold to 5.0

### Review Keywords

After 1-2 weeks, review which keywords are finding relevant results:

```bash
# See which keywords triggered alerts
sudo journalctl -u osint-monitor --since "7 days ago" | grep "Matched keyword"
```

**Add keywords** that should be tracked
**Remove keywords** that only produce noise

---

## Troubleshooting

### Service Won't Start

**Check logs**:
```bash
sudo journalctl -u osint-monitor -n 50
```

**Common issues**:
- Python not found: Check path in service file
- Module not found: Check virtualenv is correct
- Config not found: Check `data/monitors/configs/` exists

**Test manually**:
```bash
cd /home/brian/sam_gov
.venv/bin/python3 monitoring/scheduler.py --config-dir data/monitors/configs
```

### No Email Alerts

**Check SMTP credentials** in `.env`:
```bash
grep SMTP .env
```

**Test email manually**:
```python
import smtplib
from email.mime.text import MIMEText

# Test SMTP connection
server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
server.login('brianmills2718@gmail.com', 'kzwv qnmu xqqr dyet')
server.quit()
print("SMTP working!")
```

### High CPU/Memory Usage

**Check resource usage**:
```bash
sudo systemctl status osint-monitor
```

**If CPU is high during execution**: Normal (LLM calls)
**If CPU is high when idle**: Problem - investigate

**Limit memory** (add to service file):
```ini
[Service]
MemoryMax=500M
```

---

## Cost Tracking

**LLM Calls Per Day**:
- Query generation: ~192 calls (1 per keyword×source)
- Relevance filtering: ~100-300 calls (varies by results)
- **Total**: ~300-500 gpt-5-nano calls/day

**Estimated Cost**: < $0.50/day (< $15/month)

**Check actual costs**:
```bash
# View LLM usage logs
sudo journalctl -u osint-monitor --since "24 hours ago" | grep "LiteLLM"
```

---

## Next Steps

### Week 1: Monitor and Observe
- Check email alerts daily
- Review log output
- Note any issues or unexpected behavior

### Week 2: Tune Keywords
- Add high-value keywords
- Remove noisy keywords
- Adjust relevance threshold if needed

### Week 3: Evaluate Expansion
- Consider adding more monitors
- Consider adding more sources (when available)
- Consider Phase 2 (Web UI) if manual management is tedious

---

## Backup and Recovery

### Backup Monitor Configs
```bash
# Create backup
tar -czf monitors-backup-$(date +%Y%m%d).tar.gz data/monitors/configs/

# Restore backup
tar -xzf monitors-backup-YYYYMMDD.tar.gz
```

### Backup Results
```bash
# Backup result files
cp -r data/monitors/ data/monitors-backup-$(date +%Y%m%d)/
```

### Recreate Service After System Update
```bash
# Service file should persist, but if needed:
sudo cp /tmp/osint-monitor.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable osint-monitor
sudo systemctl start osint-monitor
```

---

## System Information

**Deployed On**: 2025-10-19 21:14:10 PDT
**Hostname**: DESKTOP-79G7E9D
**OS**: Ubuntu/WSL2
**Python**: 3.12.3
**Scheduler**: APScheduler 3.11.0

**First Scheduled Run**: 2025-10-20 06:00:00 PDT (tomorrow morning)

---

**Status**: System is now in production. Monitors will execute daily at 6:00 AM automatically. 🎉
