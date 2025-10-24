#!/bin/bash
# Setup script for Discord daily scraping
# Adds a cron job to run discord_daily_scrape.py every day at 2 AM

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRAPER_SCRIPT="$SCRIPT_DIR/discord_daily_scrape.py"
VENV_PATH="/home/brian/sam_gov/.venv/bin/python3"

# Make the scraper executable
chmod +x "$SCRAPER_SCRIPT"

# Create cron job entry
CRON_ENTRY="0 2 * * * $VENV_PATH $SCRAPER_SCRIPT >> $SCRIPT_DIR/../../data/logs/discord_daily_scrape_cron.log 2>&1"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -F "$SCRAPER_SCRIPT" >/dev/null; then
    echo "Cron job already exists"
    echo ""
    echo "Current cron jobs:"
    crontab -l | grep -F "$SCRAPER_SCRIPT"
else
    # Add cron job
    (crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -
    echo "✓ Cron job added successfully"
    echo ""
    echo "The Discord daily scraper will run every day at 2:00 AM"
    echo ""
    echo "To check: crontab -l | grep discord"
    echo "To remove: crontab -e (then delete the line)"
fi

echo ""
echo "Test the scraper manually:"
echo "  cd $SCRIPT_DIR"
echo "  python3 discord_daily_scrape.py"
echo ""
echo "View logs:"
echo "  tail -f $SCRIPT_DIR/../../data/logs/discord_daily_scrape_cron.log"
