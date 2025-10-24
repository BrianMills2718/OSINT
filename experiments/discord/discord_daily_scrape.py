#!/usr/bin/env python3
"""
Discord Daily Scraper

Scrapes yesterday's messages from configured Discord servers.
Designed to run daily via cron job.
"""

import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path


# Configuration
CONFIG_FILE = Path(__file__).parent / "discord_servers.json"
DCE_CLI = Path(__file__).parent / "../../archive/reference/dce-cli/DiscordChatExporter.Cli"
EXPORTS_DIR = Path(__file__).parent / "../../data/exports"
LOGS_DIR = Path(__file__).parent / "../../data/logs"


def load_config():
    """Load server configuration."""
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)


def scrape_server(server_id: str, server_name: str, token: str, start_date: str, end_date: str):
    """
    Scrape messages from a Discord server for a specific date range.

    Args:
        server_id: Discord server ID
        server_name: Human-readable server name
        token: Discord authentication token
        start_date: Start date (YYYY-MM-DD) - inclusive
        end_date: End date (YYYY-MM-DD) - exclusive

    Returns:
        True if successful, False otherwise
    """
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    log_file = LOGS_DIR / f"daily_scrape_{server_id}.log"

    cmd = [
        str(DCE_CLI),
        "exportguild",
        "-t", token,
        "-g", server_id,
        "-f", "Json",
        "-o", str(EXPORTS_DIR) + "/",
        "--after", start_date,
        "--before", end_date
    ]

    print(f"\nScraping {server_name} (ID: {server_id})")
    print(f"  Date range: {start_date} to {end_date}")

    try:
        with open(log_file, 'a') as log:
            log.write(f"\n{'='*80}\n")
            log.write(f"Daily scrape started: {datetime.now()}\n")
            log.write(f"Server: {server_name} ({server_id})\n")
            log.write(f"Date range: {start_date} to {end_date}\n")
            log.write(f"{'='*80}\n\n")

            result = subprocess.run(
                cmd,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=1800  # 30 minute timeout
            )

            if result.returncode == 0:
                log.write(f"\n✓ Daily scrape completed successfully at {datetime.now()}\n")
                print(f"  ✓ Success")
                return True
            else:
                log.write(f"\n✗ Daily scrape failed with code {result.returncode} at {datetime.now()}\n")
                print(f"  ✗ Failed with exit code {result.returncode}")
                return False

    except subprocess.TimeoutExpired:
        print(f"  ✗ Timeout after 30 minutes")
        with open(log_file, 'a') as log:
            log.write(f"\n✗ Daily scrape timed out at {datetime.now()}\n")
        return False

    except Exception as e:
        print(f"  ✗ Error: {e}")
        with open(log_file, 'a') as log:
            log.write(f"\n✗ Daily scrape failed: {e}\n")
        return False


def main():
    """Run daily scrape for all enabled servers."""
    config = load_config()
    token = config.get('token')

    if not token:
        print("ERROR: No token found in discord_servers.json")
        sys.exit(1)

    # Calculate yesterday's date range
    yesterday = datetime.now() - timedelta(days=1)
    today = datetime.now()

    start_date = yesterday.strftime("%Y-%m-%d")
    end_date = today.strftime("%Y-%m-%d")

    print(f"Discord Daily Scraper")
    print(f"Date range: {start_date} to {end_date}")
    print(f"Servers: {len(config['servers'])}")

    # Track results
    successes = []
    failures = []

    # Scrape each enabled server
    for server in config['servers']:
        if not server.get('enabled', True):
            print(f"\nSkipping {server['name']} (disabled)")
            continue

        success = scrape_server(
            server['id'],
            server['name'],
            token,
            start_date,
            end_date
        )

        if success:
            successes.append(server['name'])
        else:
            failures.append(server['name'])

    # Print summary
    print(f"\n{'='*80}")
    print(f"Daily Scrape Summary")
    print(f"  Successful: {len(successes)}")
    print(f"  Failed: {len(failures)}")

    if successes:
        print(f"\n  ✓ Successful servers:")
        for name in successes:
            print(f"    - {name}")

    if failures:
        print(f"\n  ✗ Failed servers:")
        for name in failures:
            print(f"    - {name}")

    # Exit with error code if any failed
    if failures:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
