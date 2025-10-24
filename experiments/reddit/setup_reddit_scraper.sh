#!/bin/bash
# Setup script for Reddit daily scraping
# Adds a cron job to run reddit_daily_scrape.py every day at 3 AM (after Discord at 2 AM)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRAPER_SCRIPT="$SCRIPT_DIR/reddit_daily_scrape.py"
VENV_PATH="/home/brian/sam_gov/.venv/bin/python3"

# Make the scraper executable
chmod +x "$SCRAPER_SCRIPT"

# Create cron job entry (3 AM daily)
CRON_ENTRY="0 3 * * * $VENV_PATH $SCRAPER_SCRIPT >> $SCRIPT_DIR/../../data/logs/reddit_daily_scrape_cron.log 2>&1"

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
    echo "The Reddit daily scraper will run every day at 3:00 AM"
    echo ""
    echo "To check: crontab -l | grep reddit"
    echo "To remove: crontab -e (then delete the line)"
fi

echo ""
echo "Test the scraper manually:"
echo "  cd $SCRIPT_DIR"
echo "  python3 reddit_daily_scrape.py"
echo ""
echo "View logs:"
echo "  tail -f $SCRIPT_DIR/../../data/logs/reddit_daily_scrape_cron.log"
echo "  tail -f $SCRIPT_DIR/../../data/logs/reddit_daily_scrape.log"
