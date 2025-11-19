#!/bin/bash
# Setup anacron for Discord and Reddit daily scraping
# This ensures scrapes run even if computer was off at scheduled time

set -e  # Exit on error

echo "==================================================================="
echo "Setting up anacron for Discord/Reddit daily scrapes"
echo "==================================================================="
echo ""

# Step 1: Install anacron
echo "Step 1: Installing anacron..."
sudo apt-get update
sudo apt-get install -y anacron
echo "✓ anacron installed"
echo ""

# Step 2: Create daily script wrapper
echo "Step 2: Creating daily scrape wrapper..."
sudo tee /etc/cron.daily/discord-reddit-scrape > /dev/null << 'EOF'
#!/bin/bash
# Daily Discord and Reddit scraping (runs via anacron)
# Created: 2025-11-18

VENV_PYTHON="/home/brian/sam_gov/.venv/bin/python3"
DISCORD_SCRIPT="/home/brian/sam_gov/experiments/discord/discord_daily_scrape.py"
REDDIT_SCRIPT="/home/brian/sam_gov/experiments/reddit/reddit_daily_scrape.py"
LOG_DIR="/home/brian/sam_gov/data/logs"

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Run Discord scrape
echo "=== Discord scrape started: $(date) ===" >> "$LOG_DIR/discord_daily_scrape_anacron.log"
"$VENV_PYTHON" "$DISCORD_SCRIPT" >> "$LOG_DIR/discord_daily_scrape_anacron.log" 2>&1
echo "=== Discord scrape finished: $(date) ===" >> "$LOG_DIR/discord_daily_scrape_anacron.log"
echo "" >> "$LOG_DIR/discord_daily_scrape_anacron.log"

# Run Reddit scrape
echo "=== Reddit scrape started: $(date) ===" >> "$LOG_DIR/reddit_daily_scrape_anacron.log"
"$VENV_PYTHON" "$REDDIT_SCRIPT" >> "$LOG_DIR/reddit_daily_scrape_anacron.log" 2>&1
echo "=== Reddit scrape finished: $(date) ===" >> "$LOG_DIR/reddit_daily_scrape_anacron.log"
echo "" >> "$LOG_DIR/reddit_daily_scrape_anacron.log"
EOF

sudo chmod +x /etc/cron.daily/discord-reddit-scrape
echo "✓ Daily scrape wrapper created: /etc/cron.daily/discord-reddit-scrape"
echo ""

# Step 3: Remove old cron entries
echo "Step 3: Removing old cron entries..."
crontab -l 2>/dev/null | grep -v discord_daily_scrape.py | grep -v reddit_daily_scrape.py | crontab -
echo "✓ Old cron entries removed"
echo ""

# Step 4: Verify anacron configuration
echo "Step 4: Verifying anacron configuration..."
if [ -f /etc/anacrontab ]; then
    echo "✓ /etc/anacrontab exists"
    echo ""
    echo "Anacron will run daily scripts when system is on (respects delays):"
    grep "^[0-9]" /etc/anacrontab | head -3
else
    echo "✗ /etc/anacrontab not found"
    exit 1
fi
echo ""

echo "==================================================================="
echo "Setup complete!"
echo "==================================================================="
echo ""
echo "What changed:"
echo "  - anacron installed (runs missed jobs when system restarts)"
echo "  - Daily script: /etc/cron.daily/discord-reddit-scrape"
echo "  - Old cron entries removed (2am Discord, 3am Reddit)"
echo "  - New logs: discord_daily_scrape_anacron.log, reddit_daily_scrape_anacron.log"
echo ""
echo "How it works:"
echo "  - anacron runs /etc/cron.daily/ scripts once per day"
echo "  - If computer was off, it runs when you turn it back on"
echo "  - Typical run time: between 6am-8am if computer is on"
echo ""
echo "To test manually:"
echo "  sudo /etc/cron.daily/discord-reddit-scrape"
echo ""
