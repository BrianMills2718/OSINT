# Boolean Monitoring System - Production Ready

**Date**: 2025-10-19
**Status**: Phase 1 Complete - 5 Production Monitors Configured
**Email Alerts**: Working (Gmail SMTP configured)

---

## What's Ready

### 5 Production Monitors Created

All monitors configured with:
- **Curated investigative keywords** (not generic news terms)
- **Parallel search execution** (32 searches in ~30-60s, was 5-6 min)
- **LLM relevance filtering** (score >= 6/10 to send alert)
- **Boolean query support** (quoted phrases, AND/OR/NOT operators)
- **4 data sources** (DVIDS, Federal Register, SAM.gov, USAJobs)
- **Daily execution** (6am daily)
- **Email alerts** to brianmills2718@gmail.com

#### Monitor 1: Domestic Extremism Classifications
**File**: `data/monitors/configs/domestic_extremism_monitor.yaml`

**Keywords**:
- "Nihilistic Violent Extremism" / "NVE"
- "Black Identity Extremists" / "BIE"
- "Domestic Violent Extremism" / "DVE"
- "extremism threat assessment"

**What it finds**: FBI/DHS threat classifications, controversial extremism designations

---

#### Monitor 2: Surveillance & FISA Programs
**File**: `data/monitors/configs/surveillance_fisa_monitor.yaml`

**Keywords**:
- "FISA warrant"
- "Section 702"
- "backdoor search"
- "mass surveillance"
- "warrantless surveillance"

**What it finds**: NSA/FBI surveillance programs, FISA court opinions, civil liberties violations

---

#### Monitor 3: Special Operations & Covert Programs
**File**: `data/monitors/configs/special_operations_monitor.yaml`

**Keywords**:
- "Joint Special Operations Command" / "JSOC"
- "covert operation"
- "classified program"
- "special operations forces"
- "special access program"

**What it finds**: JSOC operations, classified military programs, black operations

---

#### Monitor 4: Inspector General & Oversight Reports
**File**: `data/monitors/configs/oversight_whistleblower_monitor.yaml`

**Keywords**:
- "inspector general report" / "OIG report"
- "congressional oversight"
- "whistleblower complaint"
- "GAO report"
- "misconduct investigation"

**What it finds**: IG reports, oversight hearings, whistleblower revelations

---

#### Monitor 5: Immigration Enforcement Operations
**File**: `data/monitors/configs/immigration_enforcement_monitor.yaml`

**Keywords**:
- "ICE detention"
- "CBP misconduct"
- "immigration enforcement"
- "detention facility"
- "deportation operation"

**What it finds**: ICE/CBP operations, detention facility issues, enforcement abuses

---

## Test Results

### Domestic Extremism Monitor - TESTED ✅

**Test run** (2025-10-19 18:48):
- Searched for: "Nihilistic Violent Extremism", "NVE"
- Found: 4 results containing "NVE"
- **LLM Relevance Filter**:
  - Result 1: "Star Spangled Sailabration" → 0/10 (not relevant)
  - Result 2: "Star Spangled Sailabration" → 0/10 (not relevant)
  - Result 3: "War of 1812 Baltimore" → 0/10 (not relevant)
  - Result 4: "War of 1812 Baltimore" → 0/10 (not relevant)
- **Email sent**: NO (all filtered out - correct!)

**Validation**: ✅ System correctly filters false positives. These results contained "NVE" in event names, not related to Nihilistic Violent Extremism. LLM caught this and prevented false alert.

---

## How It Works

### Workflow (per monitor, daily at 6am)

```
1. Load keywords from YAML config
   ↓
2. **PARALLEL** search across all sources (asyncio.gather)
   - Creates task for each keyword+source combination
   - LLM generates source-specific query params (concurrent)
   - Execute API searches in parallel
   - 32 searches (8 keywords × 4 sources) complete in ~30-60s
   ↓
3. Deduplicate results (SHA256 hash of URLs)
   ↓
4. Compare vs previous run (detect NEW results only)
   ↓
5. LLM Relevance Filter (gpt-5-nano, sequential)
   - Score each result 0-10 for relevance to keyword
   - Provide reasoning
   - Keep only score >= 6
   - Note: This step is sequential (~4s per result)
   ↓
6. If relevant results found → Send email alert
   - HTML + plain text
   - Shows: Title, Source, Date, Keyword, Relevance Score, Reasoning
   ↓
7. Save result hashes for next run
```

### Email Alert Format

```
Subject: [Monitor Name] - X new results

1. Article Title
   Source: DVIDS | Date: 2025-10-19
   🔍 Matched keyword: "JSOC"
   Relevance: 9/10 — This article discusses Joint Special Operations
   Command operations in Yemen, revealing tactical details about
   classified special forces activities.

   [Article description...]
```

---

## How to Run Monitors

### Manual Run (Test a Monitor)

```bash
python3 -c "
import asyncio
from monitoring.boolean_monitor import BooleanMonitor
asyncio.run(BooleanMonitor('data/monitors/configs/domestic_extremism_monitor.yaml').run())
"
```

### Automated Scheduling (Production)

**Start the scheduler** (runs all enabled monitors at their scheduled times):
```bash
python3 monitoring/scheduler.py --config-dir data/monitors/configs
```

This will:
- Load all 5 monitors
- Schedule each for daily execution at 6am
- Run continuously (Ctrl+C to stop)

**Run all monitors once** (no scheduling):
```bash
python3 monitoring/scheduler.py --config-dir data/monitors/configs --run-once
```

---

## Configuration Details

### SMTP (Email) - CONFIGURED ✅

**Location**: `.env` file

```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=brianmills2718@gmail.com
SMTP_PASSWORD=kzwv qnmu xqqr dyet  # Gmail app password
SMTP_FROM_EMAIL=brianmills2718@gmail.com
SMTP_FROM_NAME=OSINT Monitor
```

**Status**: Tested and working (test email sent successfully 2025-10-19 17:50)

### Data Sources - ALL WORKING ✅

1. **DVIDS** - Military/DoD media (API key configured)
2. **Federal Register** - Government rules/notices (no key required)
3. **SAM.gov** - Federal contracts (API key configured)
4. **USAJobs** - Federal job postings (API key configured)

---

## What's Different from Generic Boolean Monitoring

### ❌ Generic Approach (What We're NOT Doing)
```yaml
keywords:
  - "Donald Trump"  # Returns news cycle
  - "Biden"         # Returns press releases
  - "Israel"        # Too broad
```

### ✅ Investigative Approach (What We ARE Doing)
```yaml
keywords:
  - "Nihilistic Violent Extremism"  # Specific FBI classification
  - "FISA warrant"                  # Specific legal process
  - "inspector general report"      # Specific document type
```

**Key Differences**:
1. **Specific program names** - Not generic topics
2. **Bureaucratic jargon** - Government terminology
3. **LLM relevance filtering** - Catches false positives
4. **Document-focused** - Not news articles

---

## Keyword Research Foundation

### Sources
- **1,101 articles** from Ken Klippenstein & Bill's Black Box
- **3,300 article tags** showing actual investigative focus
- **1,216 automated keywords** (TF-IDF/NER) - archived (quality issues)
- **~100 curated keywords** manually extracted

### What Ken & Bill Actually Write About
(From article tag analysis)

**Top Topics**:
- National security (130 mentions)
- Civil liberties (92 mentions)
- Surveillance (54 mentions)
- Domestic terrorism (29 mentions)
- Congressional oversight (8 mentions)
- Leaks & whistleblowers (8 mentions)

**NOT** generic political news, election coverage, or press releases.

### Curated Keywords Document
**Location**: `/home/brian/sam_gov/INVESTIGATIVE_KEYWORDS_CURATED.md`

Contains:
- Tier 1: High-value terms (FBI classifications, specific programs)
- Tier 2: Medium-value (agencies, concepts)
- Tier 3: Context-dependent (document types, combined terms)
- Tier 4: Acronyms
- Boolean query templates

---

## Files & Locations

### Active Monitors
```
data/monitors/configs/
├── domestic_extremism_monitor.yaml
├── surveillance_fisa_monitor.yaml
├── special_operations_monitor.yaml
├── oversight_whistleblower_monitor.yaml
├── immigration_enforcement_monitor.yaml
├── domestic_extremism_test.yaml (test version)
├── nve_monitor.yaml (original test)
└── test_monitor.yaml (simple test)
```

### Core System Files
```
monitoring/
├── boolean_monitor.py (565 lines) - Core monitor class
├── scheduler.py (290 lines) - APScheduler automation
└── README.md - System design documentation
```

### Supporting Documents
```
INVESTIGATIVE_KEYWORDS_CURATED.md - Curated keyword list
MONITORING_SYSTEM_READY.md - This file
STATUS.md - Component status tracker
```

### Archived
```
archive/2025-10-19/automated_keyword_extraction/
├── keyword_database.json (1,216 keywords - quality issues)
├── keyword_extraction_raw.json (18MB TF-IDF output)
└── README.md (Why archived)
```

---

## Next Steps (Optional)

### Production Deployment
1. **Run scheduler as systemd service** (continuous operation)
2. **Set up log rotation** (monitor logs can grow)
3. **Add Slack/Discord webhooks** (additional alert channels)

### Monitor Tuning
1. **Test each monitor** to verify results are investigative
2. **Adjust keywords** based on real results
3. **Fine-tune relevance threshold** (currently >= 6/10)

### Expansion
1. **Add more sources** (when available)
2. **Create topic-specific monitors** (e.g., specific agencies, programs)
3. **Historical analysis** (run monitors on past data)

---

## Cost Estimate

**Per monitor per day**:
- ~8 keywords × 4 sources = 32 searches (parallel execution)
- Each search: 1 LLM call (query generation) + API call
- Relevance filtering: ~10-30 results × 1 LLM call each (sequential)
- **Total**: ~42-62 LLM calls/day/monitor (gpt-5-nano = cheap)

**5 monitors**:
- ~210-310 LLM calls/day
- Using gpt-5-nano (cheapest model)
- **Estimated cost**: < $1/day

**Runtime per monitor**:
- Search phase: ~30-60s (parallel)
- Relevance filtering: ~40-120s (sequential, 10-30 results × 4s each)
- **Total**: ~1-3 minutes per monitor (acceptable for daily 6am execution)

---

## Status Summary

✅ **Phase 1 Boolean Monitoring MVP: COMPLETE**

**What works**:
- 5 production monitors configured with investigative keywords
- LLM relevance filtering (prevents false positives)
- Email alerts with SMTP (Gmail configured)
- Automated scheduling (APScheduler)
- 4 data sources integrated
- Deduplication and new result detection

**What's ready for production**:
- Run monitors manually anytime
- Start scheduler for automated daily execution
- Receive email alerts for relevant new results

**What's been tested**:
- Email delivery (✅ working)
- Monitor execution (✅ working)
- Relevance filtering (✅ correctly filtered false positives)
- Multi-source search (✅ tested earlier)

---

**Ready to monitor government documents for rare investigative diamonds! 💎**
