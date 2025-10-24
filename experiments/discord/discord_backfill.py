#!/usr/bin/env python3
"""
Discord Backfill Manager

Automatically scrapes Discord servers in safe date chunks,
working backwards from present to get complete history without
hitting rate limits or losing progress.
"""

import json
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List


CONFIG_FILE = Path("discord_backfill_state.json")
DCE_CLI = Path("../../archive/reference/dce-cli/DiscordChatExporter.Cli")
EXPORTS_DIR = Path("../../data/exports")
LOGS_DIR = Path("../../data/logs")

# Backfill settings
CHUNK_DAYS = 7  # Export in 7-day chunks to avoid rate limits
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 300  # 5 minutes between retries


def load_state():
    """Load backfill state."""
    if not CONFIG_FILE.exists():
        return {"servers": {}}

    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)


def save_state(state):
    """Save backfill state."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def get_server_state(state, server_id: str):
    """Get state for a specific server."""
    if server_id not in state["servers"]:
        state["servers"][server_id] = {
            "server_id": server_id,
            "completed_ranges": [],  # List of {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}
            "failed_ranges": [],
            "current_position": None,  # Date we're working back from
            "earliest_date": None,  # Stop when we hit this (optional)
            "status": "pending"  # pending, in_progress, completed, failed
        }
    return state["servers"][server_id]


def export_date_range(server_id: str, token: str, start_date: str, end_date: str,
                      log_file: Path) -> bool:
    """
    Export messages from a specific date range.

    Args:
        server_id: Discord server ID
        token: Discord token
        start_date: Start date (YYYY-MM-DD) - inclusive
        end_date: End date (YYYY-MM-DD) - exclusive
        log_file: Path to log file

    Returns:
        True if successful, False otherwise
    """
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

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

    print(f"  Exporting {start_date} to {end_date}...")

    try:
        with open(log_file, 'a') as log:
            log.write(f"\n{'='*80}\n")
            log.write(f"Export started: {datetime.now()}\n")
            log.write(f"Date range: {start_date} to {end_date}\n")
            log.write(f"{'='*80}\n\n")

            result = subprocess.run(
                cmd,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=3600  # 1 hour timeout per chunk
            )

            if result.returncode == 0:
                log.write(f"\n✓ Export completed successfully at {datetime.now()}\n")
                return True
            else:
                log.write(f"\n✗ Export failed with code {result.returncode} at {datetime.now()}\n")
                return False

    except subprocess.TimeoutExpired:
        print(f"  ✗ Export timed out after 1 hour")
        with open(log_file, 'a') as log:
            log.write(f"\n✗ Export timed out at {datetime.now()}\n")
        return False
    except Exception as e:
        print(f"  ✗ Export failed: {e}")
        with open(log_file, 'a') as log:
            log.write(f"\n✗ Export failed: {e}\n")
        return False


def backfill_server(server_id: str, token: str, start_from: Optional[str] = None,
                   earliest_date: Optional[str] = None):
    """
    Backfill a server's history in safe chunks.

    Args:
        server_id: Discord server ID
        token: Discord token
        start_from: Date to start from (default: today)
        earliest_date: Stop when reaching this date (default: go back 1 year)
    """
    state = load_state()
    server_state = get_server_state(state, server_id)

    # Set initial position
    if server_state["current_position"] is None:
        if start_from:
            server_state["current_position"] = start_from
        else:
            server_state["current_position"] = datetime.now().strftime("%Y-%m-%d")

    # Set earliest date if not set
    if server_state["earliest_date"] is None:
        if earliest_date:
            server_state["earliest_date"] = earliest_date
        else:
            # Default: go back 1 year
            one_year_ago = datetime.now() - timedelta(days=365)
            server_state["earliest_date"] = one_year_ago.strftime("%Y-%m-%d")

    server_state["status"] = "in_progress"
    save_state(state)

    print(f"\nBackfilling server {server_id}")
    print(f"  Current position: {server_state['current_position']}")
    print(f"  Target earliest: {server_state['earliest_date']}")
    print(f"  Chunk size: {CHUNK_DAYS} days")
    print(f"  Completed ranges: {len(server_state['completed_ranges'])}")

    log_file = LOGS_DIR / f"backfill_{server_id}.log"

    current = datetime.strptime(server_state["current_position"], "%Y-%m-%d")
    target = datetime.strptime(server_state["earliest_date"], "%Y-%m-%d")

    chunk_num = 1
    while current > target:
        # Calculate chunk range
        end_date = current
        start_date = max(current - timedelta(days=CHUNK_DAYS), target)

        end_str = end_date.strftime("%Y-%m-%d")
        start_str = start_date.strftime("%Y-%m-%d")

        print(f"\nChunk {chunk_num}: {start_str} to {end_str}")

        # Try export with retries
        success = False
        for attempt in range(1, MAX_RETRIES + 1):
            if attempt > 1:
                print(f"  Retry {attempt}/{MAX_RETRIES} after {RETRY_DELAY_SECONDS}s...")
                time.sleep(RETRY_DELAY_SECONDS)

            success = export_date_range(server_id, token, start_str, end_str, log_file)

            if success:
                break

        if success:
            # Record success
            server_state["completed_ranges"].append({
                "start": start_str,
                "end": end_str,
                "completed_at": datetime.now().isoformat()
            })
            server_state["current_position"] = start_str
            print(f"  ✓ Chunk {chunk_num} completed")
        else:
            # Record failure
            server_state["failed_ranges"].append({
                "start": start_str,
                "end": end_str,
                "failed_at": datetime.now().isoformat()
            })
            print(f"  ✗ Chunk {chunk_num} failed after {MAX_RETRIES} attempts")
            print(f"  Continuing to next chunk...")
            server_state["current_position"] = start_str

        save_state(state)
        current = start_date
        chunk_num += 1

    # Mark as completed
    server_state["status"] = "completed"
    save_state(state)

    print(f"\n{'='*80}")
    print(f"Backfill completed for server {server_id}")
    print(f"  Total chunks: {chunk_num - 1}")
    print(f"  Successful: {len(server_state['completed_ranges'])}")
    print(f"  Failed: {len(server_state['failed_ranges'])}")

    if server_state["failed_ranges"]:
        print(f"\n⚠️  Some chunks failed. Review log: {log_file}")
        for failed in server_state["failed_ranges"]:
            print(f"    - {failed['start']} to {failed['end']}")


def status(server_id: Optional[str] = None):
    """Show backfill status."""
    state = load_state()

    if not state["servers"]:
        print("No servers being backfilled.")
        return

    if server_id:
        servers = {server_id: state["servers"].get(server_id)}
        if not servers[server_id]:
            print(f"No backfill state for server {server_id}")
            return
    else:
        servers = state["servers"]

    for sid, sstate in servers.items():
        print(f"\nServer: {sid}")
        print(f"  Status: {sstate['status']}")
        print(f"  Current position: {sstate['current_position']}")
        print(f"  Target earliest: {sstate['earliest_date']}")
        print(f"  Completed chunks: {len(sstate['completed_ranges'])}")
        print(f"  Failed chunks: {len(sstate['failed_ranges'])}")

        if sstate['completed_ranges']:
            latest = sstate['completed_ranges'][-1]
            print(f"  Latest completed: {latest['start']} to {latest['end']}")


def retry_failed(server_id: str, token: str):
    """Retry failed chunks for a server."""
    state = load_state()
    server_state = get_server_state(state, server_id)

    if not server_state["failed_ranges"]:
        print(f"No failed chunks for server {server_id}")
        return

    print(f"\nRetrying {len(server_state['failed_ranges'])} failed chunks...")
    log_file = LOGS_DIR / f"backfill_{server_id}.log"

    failed = server_state["failed_ranges"].copy()
    server_state["failed_ranges"] = []

    for chunk in failed:
        print(f"\nRetrying: {chunk['start']} to {chunk['end']}")

        success = export_date_range(server_id, token, chunk['start'], chunk['end'], log_file)

        if success:
            server_state["completed_ranges"].append({
                "start": chunk['start'],
                "end": chunk['end'],
                "completed_at": datetime.now().isoformat()
            })
            print(f"  ✓ Retry successful")
        else:
            server_state["failed_ranges"].append(chunk)
            print(f"  ✗ Retry failed")

        save_state(state)

    print(f"\nRetry complete:")
    print(f"  Successful: {len([c for c in failed if c not in server_state['failed_ranges']])}")
    print(f"  Still failed: {len(server_state['failed_ranges'])}")


def main():
    if len(sys.argv) < 2:
        print("""
Discord Backfill Manager

Usage:
  discord_backfill.py backfill <server_id> <token> [--start YYYY-MM-DD] [--earliest YYYY-MM-DD]
  discord_backfill.py status [server_id]
  discord_backfill.py retry-failed <server_id> <token>

Examples:
  # Start backfill from today, go back 1 year
  discord_backfill.py backfill 709752884257882135 "YOUR_TOKEN"

  # Start from specific date, go back to 2020
  discord_backfill.py backfill 709752884257882135 "YOUR_TOKEN" --start 2024-01-01 --earliest 2020-01-01

  # Check status
  discord_backfill.py status 709752884257882135

  # Retry failed chunks
  discord_backfill.py retry-failed 709752884257882135 "YOUR_TOKEN"

Features:
  - Exports in 7-day chunks to avoid rate limits
  - Automatically retries failures
  - Resumes from where it left off
  - Tracks progress in discord_backfill_state.json
  - Logs everything to data/logs/backfill_<server_id>.log
        """)
        sys.exit(1)

    command = sys.argv[1]

    if command == "backfill":
        if len(sys.argv) < 4:
            print("Usage: backfill <server_id> <token> [--start YYYY-MM-DD] [--earliest YYYY-MM-DD]")
            sys.exit(1)

        server_id = sys.argv[2]
        token = sys.argv[3]

        # Parse optional args
        start_from = None
        earliest_date = None

        i = 4
        while i < len(sys.argv):
            if sys.argv[i] == "--start" and i + 1 < len(sys.argv):
                start_from = sys.argv[i + 1]
                i += 2
            elif sys.argv[i] == "--earliest" and i + 1 < len(sys.argv):
                earliest_date = sys.argv[i + 1]
                i += 2
            else:
                i += 1

        backfill_server(server_id, token, start_from, earliest_date)

    elif command == "status":
        server_id = sys.argv[2] if len(sys.argv) > 2 else None
        status(server_id)

    elif command == "retry-failed":
        if len(sys.argv) < 4:
            print("Usage: retry-failed <server_id> <token>")
            sys.exit(1)

        server_id = sys.argv[2]
        token = sys.argv[3]
        retry_failed(server_id, token)

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
