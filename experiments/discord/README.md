# Discord Scraping Tools

Two Discord scraping tools for the SigInt platform:

## 1. Daily Scraper (`discord_daily_scrape.py`)

Scrapes yesterday's messages from all configured Discord servers.

**Purpose**: Incremental daily updates for ongoing monitoring

**Usage**:
```bash
cd /home/brian/sam_gov/experiments/discord
python3 discord_daily_scrape.py
```

**Setup Daily Automation** (runs every day at 2 AM):
```bash
bash setup_daily_scrape.sh
```

**Check if running**:
```bash
crontab -l | grep discord
```

**View logs**:
```bash
tail -f ../../data/logs/discord_daily_scrape_cron.log
tail -f ../../data/logs/daily_scrape_709752884257882135.log  # Bellingcat
tail -f ../../data/logs/daily_scrape_518979695702704132.log  # The OWL
```

---

## 2. Backfill Manager (`discord_backfill.py`)

Scrapes historical messages in 7-day chunks, working backwards from present.

**Purpose**: Get complete history without hitting rate limits

**Usage**:

**Start new backfill** (goes back 1 year by default):
```bash
python3 discord_backfill.py backfill <server_id> "<token>"
```

**Start from specific date, go back to 2020**:
```bash
python3 discord_backfill.py backfill <server_id> "<token>" --start 2024-01-01 --earliest 2020-01-01
```

**Check status**:
```bash
python3 discord_backfill.py status
python3 discord_backfill.py status <server_id>
```

**Retry failed chunks**:
```bash
python3 discord_backfill.py retry-failed <server_id> "<token>"
```

**Run in background** (for long backfills):
```bash
nohup python3 discord_backfill.py backfill <server_id> "<token>" > /tmp/backfill.log 2>&1 &
```

---

## Configuration

**File**: `discord_servers.json`

```json
{
  "servers": [
    {
      "id": "709752884257882135",
      "name": "Bellingcat",
      "enabled": true,
      "notes": "Bellingcat OSINT community"
    },
    {
      "id": "518979695702704132",
      "name": "The OWL",
      "enabled": true,
      "notes": "The OWL OSINT community"
    }
  ],
  "token": "YOUR_DISCORD_TOKEN_HERE"
}
```

**Getting Discord Token**:
1. Open Discord in browser
2. Open DevTools (F12) → Network tab
3. Click any channel
4. Find request with "Authorization" header
5. Copy token value (starts with "Nz...")

**Disabling a server**:
Set `"enabled": false` in `discord_servers.json`

---

## Current Status

**Bellingcat** (709752884257882135):
- ✅ 5 completed chunks (Sep 14 - Oct 19, 2025)
- Historical backfill: In progress to 2020-01-01

**The OWL** (518979695702704132):
- ⏳ 140 failed chunks (authentication issue - now fixed with new token)
- Next: Run `python3 discord_backfill.py retry-failed 518979695702704132 "<token>"`

---

## Output

**Exports**: `/home/brian/sam_gov/data/exports/`
- JSON files per channel
- Format: `<Server Name> - <Channel Name> [<channel_id>].json`

**Logs**: `/home/brian/sam_gov/data/logs/`
- `daily_scrape_<server_id>.log` - Daily scraper logs
- `backfill_<server_id>.log` - Backfill logs
- `discord_daily_scrape_cron.log` - Cron job output

**State**: `discord_backfill_state.json`
- Tracks backfill progress per server
- Stores completed/failed date ranges
- Safe to interrupt and resume

---

## Recommended Workflow

**For new servers**:
1. Add to `discord_servers.json` with `"enabled": true`
2. Run backfill to get historical data: `python3 discord_backfill.py backfill <id> "<token>" --earliest 2020-01-01`
3. Set up daily scraper: `bash setup_daily_scrape.sh`
4. Daily scraper handles ongoing updates

**For existing servers**:
1. Daily scraper already gets new messages
2. Use backfill only to fill gaps or get older history

---

## Tools

**DiscordChatExporter CLI**: `/home/brian/sam_gov/archive/reference/dce-cli/DiscordChatExporter.Cli`
- .NET tool for exporting Discord messages
- Supports date filtering, multiple formats
- Used by both scrapers
